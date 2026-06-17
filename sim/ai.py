"""Heuristic, pluggable player policy. Profiles differ mainly in what they BUY.

The core arc every profile follows: build economy for a couple of turns, then PIVOT to
spending mana on damage (weapons) or an artifact slot-engine. Buying is supply-aware
(ranks the cards actually available). 'mana_greedy' invests in Mana longer (and leverages
big single-turn mana like Greater Mana into expensive weapons); 'caster' builds the
artifact engine; 'weapons' converts early; 'affinity_rush' races to Affinity 3.
"""
from __future__ import annotations
import re
from .abilities import use_ability, ABILITY_COST

PROFILES = {
    "mana_greedy":   {"dmg_cat": ["Weapon"],             "econ_target": 7, "mana_turns": 6, "aff_target": 2, "want_engine": False},
    "affinity_rush": {"dmg_cat": ["Weapon"],             "econ_target": 4, "mana_turns": 2, "aff_target": 3, "want_engine": False},
    "weapons":       {"dmg_cat": ["Weapon"],             "econ_target": 5, "mana_turns": 2, "aff_target": 2, "want_engine": False},
    "caster":        {"dmg_cat": ["Artifact", "Weapon"], "econ_target": 5, "mana_turns": 2, "aff_target": 2, "want_engine": True},
    "balanced":      {"dmg_cat": ["Weapon", "Artifact"], "econ_target": 5, "mana_turns": 2, "aff_target": 2, "want_engine": True},
    # role strategies for team comps
    "healer":        {"dmg_cat": ["Weapon"],             "econ_target": 5, "mana_turns": 2, "aff_target": 3, "want_engine": False, "heal_focus": True},
    "support":       {"dmg_cat": ["Support", "Weapon"],  "econ_target": 5, "mana_turns": 2, "aff_target": 3, "want_engine": False, "heal_focus": True},
}


def mana_left(p, ctx):
    return ctx.mana - ctx.mana_spent


def _arts_owned(p):
    """Artifacts the player owns anywhere (equipped + in deck/hand/discard), excluding Wisp."""
    zones = p.deck + p.hand + p.discard
    loose = sum(1 for c in zones if c.category == "Artifact" and c.name != "Wandering Wisp")
    return loose + len(p.equipped)


def est_mana(card) -> int:
    m = re.search(r"\+\s*(\d+)\s*Mana", card.text)
    return int(m.group(1)) if m else 1


def est_damage(g, p, card) -> float:
    """Estimate a card's damage IN CONTEXT for this player (not its mana cost).
    Context-sensitive scalers (Artificer's Fury etc.) are evaluated against current state,
    so a 1-DMG-with-no-artifacts card is correctly valued as ~1, not 'cost 7'."""
    n = card.name
    eq = len(p.equipped)
    aff = p.affinity
    special = {
        "Artificer's Fury": 1 + 2 * eq,
        "Rupture Relic": 2 * max(1, eq),
        "Power Cube": max(5, eq),
        "Affinity Beacon": min(8, max(4, 2 + 2 * aff)),
        "Mana Cannon": 5 + 2 * aff,
        "Multiplier Maul": 2 * 2 + aff,            # assume ~2 weapons played
        "Ethereal Fragment": 3,
        "Pacifier": max(0, 10 - p.hp),
        "Crimson Scythe": 8,
        "Thunderstrike": 2, "Volley": 2,           # AoE; counts once here
        "Alliance Amulet": 1,
        "Bloodfire Charm": 6,
    }
    if n in special:
        return special[n]
    m = re.search(r"(\d+)\s*DMG", card.text)
    base = int(m.group(1)) if m else 0
    if "every enemy" in card.text or "all enemies" in card.text:
        base += 1                                   # small AoE bonus
    return base


def buy_value(g, p, card, prof, ctx) -> float:
    """How much this card is worth to THIS player right now (higher = buy first)."""
    early = p.turn_no <= prof["mana_turns"]
    if card.category == "Mana":
        if card.name == "Mana Crystal":
            return 0.0                               # basic starter mana — rebuying just dilutes
        # Economy is valuable only until 'enough'; afterwards heavily discounted.
        need = early or ctx.mana < prof["econ_target"]
        v = est_mana(card) + (1 if "Affinity" in card.text and p.affinity < prof["aff_target"] else 0)
        return v * (2.2 if need else 0.25)
    if card.category == "Weapon":
        return est_damage(g, p, card) * 1.2          # weapons recur -> slight premium
    if card.category == "Artifact":
        # only worth it if we can actually field an engine (slots now or will build them)
        can_engine = prof["want_engine"] or p.slots > 0
        if _arts_owned(p) >= min(5, p.slots + 1) + (1 if prof["want_engine"] else 0):
            return 0.0                               # pipeline already full
        per_fire = est_damage(g, p, card)
        return per_fire * (3.0 if can_engine else 0.6)   # ~3 fires of value if engine-capable
    if card.category == "Support":
        t = card.text
        v = 1.5
        if "draw" in t.lower() or "Draw" in t:
            v += 2.5                                  # card draw is premium
        if "Prevent" in t or "heal" in t.lower() or "Village" in t:
            v += 1.5 if prof.get("heal_focus") else 0.5
        return v
    return 0.0


def _is_wisp(c):
    return c.name == "Wandering Wisp"


def play_hand(g, p, ctx, prof=None):
    """Loop the hand so drawn cards are playable immediately (draw chains work):
    play all Mana (scaling last), use the ability once, play all Support, then all Weapons
    (+ slotless Wandering Wisp; Multiplier Maul last). Re-scans after every card so a 'draw N'
    effect's new cards get played this turn too."""
    from .effects import EFFECTS
    prof = prof or PROFILES[getattr(p, "strategy", "balanced")]
    foc = g.focused(p)

    def play(c, kind):
        mb, hand_b, aff_b = ctx.mana, len(p.hand), p.affinity
        g._dmg_accum = 0; g._heal_accum = 0; ctx.consumed = False
        p.hand.remove(c)
        if kind == "mana":
            ctx.mana_cards_used += 1
        elif kind == "support":
            ctx.support_used += 1
        elif kind == "weapon":
            ctx.weapons_played += 1
        EFFECTS[c.name](g, p, ctx)
        g.stats[f"play:{c.name}"] += 1
        if not _is_wisp(c) and not ctx.consumed:   # consumed = destroyed (e.g. Hexcores), not discarded
            p.discard.append(c)
        if foc:
            parts = []
            if ctx.mana - mb:
                parts.append(f"+{ctx.mana - mb} mana")
            if g._dmg_accum:
                parts.append(f"{g._dmg_accum} dmg to enemies")
            if g._heal_accum:
                parts.append(f"{g._heal_accum} healed")
            if p.affinity != aff_b:
                parts.append(f"affinity {aff_b}->{p.affinity}")
            drew = len(p.hand) - (hand_b - 1)
            if drew > 0:
                parts.append(f"DREW {drew}")
            g.vlog(f"    PLAY {c.name} ({c.category}): {', '.join(parts) or 'utility'}")

    played_ability = False
    guard = 0
    while True:
        guard += 1
        if guard > 300 or g.check_end():
            return
        manas = [c for c in p.hand if c.category == "Mana"]
        if manas:
            manas.sort(key=lambda c: ("for every" in c.text or "Increase by" in c.text))
            play(manas[0], "mana")
            continue
        if not played_ability:
            played_ability = True
            _maybe_ability(g, p, ctx, prof)
            continue
        sup = [c for c in p.hand if c.category == "Support"]
        if sup:
            play(sup[0], "support")
            continue
        weps = [c for c in p.hand if c.category == "Weapon" or _is_wisp(c)]
        if weps:
            weps.sort(key=lambda c: c.name == "Multiplier Maul")
            play(weps[0], "weapon" if not _is_wisp(weps[0]) else "wisp")
            continue
        return


def _maybe_ability(g, p, ctx, prof=None):
    if mana_left(p, ctx) < ABILITY_COST:
        return
    cls = p.cls
    low = min((q.hp for q in g.players), default=10)
    healer = cls in ("Ranger", "Paladin", "Druid", "Cleric", "Bard")
    heal_focus = (prof or {}).get("heal_focus", False)
    useful = False
    # healers heal proactively; heal-focused roles heal even earlier and protect the Village
    hp_thresh, vil_thresh = (8, 26) if heal_focus else (5, 14)
    if healer and (low <= hp_thresh or g.village <= vil_thresh):
        useful = True
    elif cls == "Wizard" and any(eq.fires_from_turn <= p.turn_no for eq in p.equipped):
        useful = True
    elif cls == "Weaponmaster" and any(c.category == "Weapon" for c in p.discard):
        useful = True
    elif cls == "Enchanter":
        useful = p.ultimate or len(p.equipped) < p.slots
    elif cls == "Blacksmith":
        useful = any(c.category == "Weapon" for c in p.discard) or p.ultimate
    if useful:
        ctx.mana_spent += ABILITY_COST
        if g.focused(p):
            g.vlog(f"    ABILITY {p.cls}{' (ULTIMATE)' if p.ultimate else ''} for 3 mana")
        use_ability(g, p, ctx)
        ctx.used_ability = True


def draw_phase(g, p):
    """Optional discard (design rule): keep Mana/Artifacts for deck sequencing; discard rest; draw to 5."""
    if not p.hand:
        p.draw_to_full()
        return
    keep = [c for c in p.hand if c.category in ("Mana", "Artifact")]
    if len(keep) > 5:
        keep = keep[:5]
    discarded = [c.name for c in p.hand if c not in keep]
    for c in list(p.hand):
        if c not in keep:
            p.discard.append(c)
    p.hand = keep
    p.draw_to_full()
    if g.focused(p) and discarded:
        g.vlog(f"    DRAW PHASE: kept {[c.name for c in p.hand]}; discarded {discarded}")


def do_equip(g, p, ctx, prof):
    """Equip as many artifacts from hand as fit (equipping is just an Action — no 1/turn cap).
    Buy slots as affordable to make room; swap out a weaker equipped artifact if full."""
    from .engine import Equipped
    while True:
        arts = [c for c in p.hand if c.category == "Artifact" and c.name != "Wandering Wisp"]
        if not arts:
            return
        art = max(arts, key=lambda c: est_damage(g, p, c))   # equip the strongest engine piece first
        if p.free_slots() == 0:
            nxt = g.slot_cost[p.slots] if p.slots < 5 else 99
            if p.slots < 5 and mana_left(p, ctx) >= nxt and not g.no_buy:
                ctx.mana_spent += nxt; p.slots += 1; g.stats["buy:slot"] += 1
                if g.focused(p):
                    g.vlog(f"    BUY artifact slot #{p.slots} (cost {nxt})")
            elif p.equipped and est_damage(g, p, art) > min(est_damage(g, p, e.card) for e in p.equipped):
                worst = min(p.equipped, key=lambda e: est_damage(g, p, e.card))
                p.equipped.remove(worst); p.discard.append(worst.card)
                if g.focused(p):
                    g.vlog(f"    UNEQUIP {worst.card.name} (swap for {art.name})")
            else:
                return
        p.hand.remove(art)
        p.equipped.append(Equipped(art, p.turn_no + g.charge_turns))
        g.stats[f"equip:{art.name}"] += 1
        if g.focused(p):
            g.vlog(f"    EQUIP {art.name} (charging; fires from turn {p.turn_no + g.charge_turns})")


def do_buys(g, p, ctx, prof):
    if g.no_buy:
        return
    # engine builders: buy slots aggressively (toward 5) whenever there are artifacts waiting
    # to fill them, so the engine actually matures instead of hoarding un-equippable artifacts.
    if prof["want_engine"] and p.turn_no >= prof["mana_turns"]:
        while p.slots < 5:
            cost = g.slot_cost[p.slots]
            waiting = _arts_owned(p) - p.slots          # artifacts that have nowhere to sit yet
            want = p.slots == 0 or waiting >= 1
            if want and mana_left(p, ctx) >= cost:
                ctx.mana_spent += cost; p.slots += 1; g.stats["buy:slot"] += 1
                if g.focused(p):
                    g.vlog(f"    BUY artifact slot #{p.slots} (cost {cost})")
            else:
                break
    # value-based buying: each turn buy the highest-value affordable card for THIS player,
    # affinity bump first if still below target, until mana runs out.
    guard = 0
    while guard < 6:
        guard += 1
        m = mana_left(p, ctx)
        if m <= 0:
            break
        # affinity progression while below target. Affinity-bump Mana cards are bought only if
        # currently ON OFFER in the market; otherwise raise Affinity directly for 3 Mana.
        slot = None
        if p.affinity < prof["aff_target"]:
            affs = [s for s in g.market_choices(p, m, "Mana") if "Affinity" in s.card.text]
            if affs:
                slot = min(affs, key=lambda s: s.card.cost)
            elif m >= 3:
                ctx.mana_spent += 3
                p.affinity += 1
                g.stats["raise:affinity"] += 1
                if g.focused(p):
                    g.vlog(f"    RAISE Affinity -> {p.affinity} (-3 Mana)")
                continue
        if slot is None:
            opts = g.market_choices(p, m)            # only cards currently on offer in the market
            if not opts:
                break
            best = max(opts, key=lambda s: buy_value(g, p, s.card, prof, ctx))
            if buy_value(g, p, best.card, prof, ctx) <= 0:
                break
            slot = best
        pick = slot.card
        ctx.mana_spent += pick.cost
        top = getattr(p, "_top_next_buy", False)
        p.gain_card(pick, to_deck_top=top)
        p._top_next_buy = False
        g.stats[f"buy:{pick.name}"] += 1
        if g.focused(p):
            g.vlog(f"    BUY {pick.name} ({pick.category}, cost {pick.cost}, "
                   f"value {buy_value(g, p, pick, prof, ctx):.1f}) -> {'deck top' if top else 'under deck'}")
        g.replace_market_slot(slot)                  # refill the emptied slot (online-game behavior)
        if pick.cost == 0:
            break                                    # at most one free (0-cost) buy per turn
