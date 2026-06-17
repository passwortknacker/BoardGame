"""Effect registry: card name -> handler(game, player, ctx).

Player cards resolve on play/fire (player p, ctx = this-turn scratch).
Boss/Disaster cards resolve on flip; Minion cards resolve as their per-round attack.
For boss-deck cards p and ctx are unused (pass None).
"""
from __future__ import annotations
from .engine import Game, Player, EffectContext, Minion, PLAYER_HP, SLOT_CAP, Equipped

EFFECTS: dict[str, callable] = {}


def effect(*names):
    def deco(fn):
        for n in names:
            EFFECTS[n] = fn
        return fn
    return deco


# ============================ helpers ============================
def wpn_in_hand(p):       return sum(1 for c in p.hand if c.category == "Weapon")
def mana_in_hand(p):      return sum(1 for c in p.hand if c.category == "Mana")
def support_in_hand(p):   return sum(1 for c in p.hand if c.category == "Support")
def equipped_arts(p):     return len(p.equipped)
def step(count, a, b, c, t1, t2, t3):
    """+a/b/c when count reaches thresholds t1/t2/t3."""
    if count >= t3: return c
    if count >= t2: return b
    if count >= t1: return a
    return 0

def living(g):            return [pl for pl in g.players if pl.alive]
def heal_lowest(g, amount, exclude=None):
    g.heal_player(g.lowest_heal_target(exclude), amount)
def defeat_minion(g, attacker, m):
    """Remove a minion and send its card to boss discard."""
    g.minions.remove(m)
    g.log(f"  minion {m.card.name} defeated")
    g._on_minion_killed(attacker, m)
def minion_hp(g, card):
    return (card.minion_hp or 0) + 2 * g.boss_level
def rand_players(g, n):   return g.rng.sample(living(g), min(n, len(living(g))))
def discard_n(g, p, n):
    for _ in range(min(n, len(p.hand))):
        p.discard.append(p.hand.pop())
def discard_collective(g, n):
    pls = living(g)
    for i in range(n):
        if not pls: break
        p = pls[i % len(pls)]
        if p.hand: p.discard.append(p.hand.pop())
def lose_aff(pl):         pl.affinity = max(1, pl.affinity - 1)
def from_discard(g, p, cat, *, optional=False, equip_ok=False):
    """Move 1 card of category cat from Discard to Hand (or equip Artifacts if equip_ok).
    Human picks which; sims auto-pick the first. A card may be pulled back at most ONCE per turn
    (g.ctx.replayed_from_discard) — otherwise two mutual retrievers (e.g. 2× Arsenal Enforcer)
    ping-pong forever."""
    opts = [c for c in p.discard if c.category == cat and id(c) not in g.ctx.replayed_from_discard]
    if not opts:
        return False
    if optional:
        pick = g.choose(f"Move an {cat} from your Discard to your Hand?",
                        opts + [None], default=None,
                        labeler=lambda c: c.name if c else "(skip)")
        if pick is None:
            return False
        chosen = pick
    else:
        chosen = g.choose(f"Move which {cat} from your Discard to your Hand?",
                          opts, default=opts[0], labeler=lambda c: c.name)
    p.discard.remove(chosen)
    g.ctx.replayed_from_discard.add(id(chosen))   # this card can't be pulled back again this turn
    if equip_ok and cat == "Artifact" and len(p.equipped) < p.slots:
        mode = g.choose("Add to hand or equip now?", ["equip", "hand"], default="equip",
                        labeler=lambda m: "Equip into a slot" if m == "equip" else "Add to hand")
        if mode == "equip":
            p.equipped.append(Equipped(chosen, p.turn_no + 1))
            return True
    p.hand.append(chosen)
    return True

def tutor_to_discard(g, p, cat, max_cost):
    """Move 1 'All'-class card (of category cat, or any if None) worth <= max_cost
    from the Supply to this player's Discard pile. Human picks; sims auto-pick best."""
    opts = [c for c in g.cards.values()
            if c.cls == "All" and c.is_player_card and c.cost is not None and c.cost <= max_cost
            and (cat is None or c.category == cat)]
    if not opts:
        return False
    opts.sort(key=lambda c: -(c.cost or 0))
    chosen = g.choose(f"Fetch which {cat or 'card'} (<= {max_cost} Mana) into your discard?",
                      opts, default=opts[0], labeler=lambda c: f"{c.name} ({c.category}, {c.cost})")
    p.discard.append(chosen)
    return True

def tutor_to_hand(g, p, cat, max_cost, *, equip_ok=True):
    """Fetch 1 Supply card (All-class, category cat) worth <= max_cost to Hand (optionally equip Artifacts)."""
    opts = [c for c in g.cards.values()
            if c.cls == "All" and c.is_player_card and c.cost is not None and c.cost <= max_cost
            and (cat is None or c.category == cat)]
    if not opts:
        return False
    opts.sort(key=lambda c: -(c.cost or 0))
    chosen = g.choose(f"Fetch which {cat or 'card'} (<= {max_cost} Mana) to your hand?",
                      opts, default=opts[0], labeler=lambda c: f"{c.name} ({c.category}, {c.cost})")
    if equip_ok and chosen.category == "Artifact" and len(p.equipped) < p.slots:
        mode = g.choose("Add to hand or equip now?", ["equip", "hand"], default="equip",
                        labeler=lambda m: "Equip into a slot" if m == "equip" else "Add to hand")
        if mode == "equip":
            p.equipped.append(Equipped(chosen, p.turn_no + 1))
            return True
    p.hand.append(chosen)
    return True

def destroy_one(g, p, only_cat=None, force=False):
    """Destroy (remove from game) 1 card from this player's Hand or Discard. Human chooses which
    (incl. an option to keep all); sims auto-pick a Mana Crystal (deck-thinning) or skip."""
    cands = [c for c in (p.hand + p.discard) if only_cat is None or c.category == only_cat]
    if not cands:
        return None
    crystal = next((c for c in cands if c.name == "Mana Crystal"), None)
    default = crystal if crystal else (cands[0] if force else None)
    options = list(cands) + ([] if force else [None])     # None = "don't destroy"
    chosen = g.choose("Destroy which card? (removed from your deck permanently)",
                      options, default, lambda c: (c.name if c else "(keep all - destroy nothing)"))
    if chosen is None:
        return None
    (p.hand if chosen in p.hand else p.discard).remove(chosen)
    return chosen

def refire(g, p, x, n=1):
    """Trigger up to n equipped artifacts again (after their normal turn fire).
    Each piece can be re-triggered at most once per turn; Timeless Talisman cannot."""
    refired = getattr(x, "refired_artifact_eqs", None)
    if refired is None:
        x.refired_artifact_eqs = set()
        refired = x.refired_artifact_eqs
    ready = [eq for eq in p.equipped if eq.fires_from_turn <= p.turn_no
             and eq.card.name != "Timeless Talisman" and id(eq) not in refired]
    count = 0
    while count < n and ready:
        eq = g.choose("Trigger which equipped Artifact again?", ready,
                      default=ready[0], labeler=lambda e: e.card.name)
        x.consumed = False
        refired.add(id(eq))          # mark BEFORE firing so a self-refiring artifact (Eternal
        EFFECTS[eq.card.name](g, p, x)  # Charm) can't recurse into itself forever
        if x.consumed and eq in p.equipped:
            p.equipped.remove(eq)
        ready = [e for e in ready if id(e) != id(eq)]
        count += 1
    return count

def replay_weapon_from_discard(g, p, x):
    c = next((c for c in p.discard if c.category == "Weapon"
              and id(c) not in x.replayed_from_discard), None)
    if c:
        x.replayed_from_discard.add(id(c))   # 1×/turn cap (no infinite replay chains)
        p.discard.remove(c); x.weapons_played += 1; EFFECTS[c.name](g, p, x); return True
    return False


# ============================ MANA ============================
@effect("Mana Crystal")
def _(g, p, x): x.mana += 1
@effect("Mana Orb")
def _(g, p, x): x.mana += 3
@effect("Elemental Surge")
def _(g, p, x): x.mana += 1; g.attack_target(p, 1)
@effect("Vital Essence")
def _(g, p, x): x.mana += 1; g.heal_player(p, 1)
@effect("Mana Converter")
def _(g, p, x): x.mana += 1; destroy_one(g, p, only_cat="Mana")
@effect("Source Dynamo")
def _(g, p, x): x.mana += 1 + (1 if equipped_arts(p) else 0)
@effect("Spellblade Energon")
def _(g, p, x): x.mana += 1 + (1 if wpn_in_hand(p) else 0)
@effect("Attuned Elixir")
def _(g, p, x): x.mana += 1; p.slots = min(SLOT_CAP, p.slots + 1)
@effect("Mana Conduit")
def _(g, p, x): x.mana += 2; p.affinity = min(3, p.affinity + 1)
@effect("Aegis Elixir")
def _(g, p, x): x.mana += 2; g.heal_village(2)
@effect("Druidic Tonic")
def _(g, p, x): x.mana += 2; g.heal_player(p, 2)
@effect("Faithful Brew")
def _(g, p, x): x.mana += 3; g.heal_village(2)
@effect("Mystic Infusion")
def _(g, p, x): x.mana += 2; g.heal_player(p, 2)
@effect("Mystical Arcanum")
def _(g, p, x): x.mana += 2; _draw(g, p, 1)
@effect("Sorcerous Affinity")
def _(g, p, x): x.mana += 1 + p.affinity
@effect("Resupply Rune")
def _(g, p, x): x.mana += 3; p._top_next_buy = True
@effect("Wild Magic Flux")
def _(g, p, x): x.mana += 3                       # supply reshuffle is a no-op here
@effect("Ethereal Catalyst")
def _(g, p, x): x.mana += 2; _try_ability(g, p, x)
@effect("Mana Resonator")
def _(g, p, x): x.mana += 1 + step(equipped_arts(p), 1, 2, 3, 1, 3, 5)
@effect("Aid the Weak")
def _(g, p, x): x.mana += 1 + step(PLAYER_HP - p.hp, 1, 2, 3, 1, 4, 7)   # hp<=9/6/3 missing>=1/4/7
@effect("Arcane Secrets")
def _(g, p, x): x.mana += max(0, x.mana_cards_used - 1)   # +1 per OTHER mana card used this turn
@effect("Bardic Inspiration")
def _(g, p, x): x.mana += 1 + step(g.anger, 1, 2, 3, 1, 3, 5)
@effect("Blacksmith's Pride")
def _(g, p, x): x.mana += 1 + step(wpn_in_hand(p), 1, 2, 3, 1, 3, 4)
@effect("Divine Favor")
def _(g, p, x):
    w = wpn_in_hand(p) > 0; a = equipped_arts(p) > 0
    x.mana += 1 + (1 if (w or a) else 0) + (1 if (w and a) else 0)
@effect("Martial Focus")
def _(g, p, x):
    wd = sum(1 for c in p.discard if c.category == "Weapon")
    x.mana += 1 + step(wd, 1, 2, 3, 1, 3, 5)
@effect("Bladesurge Stone")
def _(g, p, x): x.mana += 1 + step(wpn_in_hand(p), 1, 2, 3, 1, 3, 5)
@effect("Mana Resonance")
def _(g, p, x): x.mana += 1 + step(max(equipped_arts(pl) for pl in g.players), 1, 2, 3, 1, 3, 5)
@effect("Drain the Horde")
def _(g, p, x): x.mana += 1 + len(g.minions)
@effect("Call of Nature")
def _(g, p, x): x.mana += 1 + support_in_hand(p)
@effect("Magic Veil")
def _(g, p, x): refire(g, p, x, 1)                # use 1 Artifact again without discarding
@effect("Pocket Arsenal")
def _(g, p, x): replay_weapon_from_discard(g, p, x)
def _optional_destroy_tutor(g, p, x, cat, max_cost, card_label):
    do = g.choose(
        f"Destroy {card_label} to fetch a {cat or 'card'} (≤{max_cost} Mana) to your discard?",
        [True, False],
        default=True,
        labeler=lambda b: "Yes — tutor to discard" if b else "No — keep card",
    )
    if do and tutor_to_discard(g, p, cat, max_cost):
        x.consumed = True

def _hexcore(g, p, x, cat):
    """+2 Mana; optionally destroy this card to tutor a Supply card to discard."""
    x.mana += 2
    do_tutor = g.choose(
        f"Destroy this Hexcore to fetch a {cat} (<=5 Mana) to your discard?",
        [True, False],
        default=True,
        labeler=lambda b: "Yes — tutor to discard" if b else "No — keep Hexcore",
    )
    if do_tutor and tutor_to_discard(g, p, cat, 5):
        x.consumed = True

@effect("Artifact Hexcore")
def _(g, p, x): _hexcore(g, p, x, "Artifact")
@effect("Support Hexcore")
def _(g, p, x): _hexcore(g, p, x, "Support")
@effect("Weapon Hexcore")
def _(g, p, x): _hexcore(g, p, x, "Weapon")


# ============================ WEAPONS ============================
def _basic_dmg(n):
    def h(g, p, x): g.attack_target(p, n)
    return h
for _nm in ["Anger Management", "Bow", "Forge Hammer", "Longsword", "Sickle",
            "Warhammer", "Zither", "Clergy Staff", "Grimoire", "Wand"]:
    EFFECTS[_nm] = _basic_dmg(1)

@effect("Tinblade")
def _(g, p, x):
    g.attack_target(p, 2)
    do = g.choose("Destroy Tinblade after use? (removed permanently, not discarded)",
                  [True, False], default=False,
                  labeler=lambda b: "Yes — destroy" if b else "No — discard normally")
    if do:
        x.consumed = True
@effect("Lifedrain Blade")
def _(g, p, x): g.attack_target(p, 2); g.heal_player(p, 2)
@effect("Swapsteel Dirk")
def _(g, p, x):
    g.attack_target(p, 2)
    _optional_destroy_tutor(g, p, x, "Weapon", 5, "Swapsteel Dirk")
@effect("Groveguard Knuckles")
def _(g, p, x): g.attack_target(p, 2); g.heal_village(2)
@effect("Spellshard")
def _(g, p, x): g.attack_target(p, 2); _try_ability(g, p, x)
@effect("Thunderstrike", "Volley")
def _(g, p, x): g.aoe(p, 2)
@effect("Arsenal Enforcer")
def _(g, p, x): g.attack_target(p, 2); from_discard(g, p,"Weapon")
@effect("Relic Reclaimer")
def _(g, p, x): g.attack_target(p, 2); tutor_to_hand(g, p, "Artifact", 5)
@effect("Purification Spear")
def _(g, p, x): g.attack_target(p, 4); destroy_one(g, p)
@effect("Townsaver")
def _(g, p, x): g.attack_target(p, 3); _trigger_village(g, p)
@effect("Bounty Bringer")
def _(g, p, x):
    g.attack_target(p, 3)
    _optional_destroy_tutor(g, p, x, None, 8, "Bounty Bringer")
@effect("Crimson Scythe")
def _(g, p, x): g.attack_target(p, 8); p.hp = max(0, p.hp - 1)
@effect("Mace of Renewal")
def _(g, p, x): g.attack_target(p, 3); _draw(g, p, 1)
@effect("Celestial Slicer")
def _(g, p, x): g.attack_target(p, 7)             # AI picks dmg mode; draw mode handled by AI flag
@effect("Collateral Carnage")
def _(g, p, x): g.attack_target(p, 9); g.village -= 1
@effect("Fate's Arbiter")
def _(g, p, x):
    if g.minions:
        m = max(g.minions, key=lambda m: m.hp)
        g._dmg_accum += m.hp
        g.log(f"P{p.pid} defeats minion {m.card.name}")
        defeat_minion(g, p, m)
    else:
        _draw(g, p, 1)
@effect("Genesis Edge")
def _(g, p, x):
    if g.minions: g.minions.clear()
    else:
        for pl in living(g): _draw(g, pl, 1)
@effect("Pacifier")
def _(g, p, x): g.attack_target(p, max(0, PLAYER_HP - p.hp)); g.anger = max(0, g.anger - 2)
@effect("Multiplier Maul")
def _(g, p, x): g.attack_target(p, 2 * (x.weapons_played) + p.affinity)   # incl. this (already counted)
@effect("Mana Cannon")
def _(g, p, x): g.attack_target(p, 5 + 2 * p.affinity, prefer_minion=False)
@effect("Artificer's Fury")
def _(g, p, x): g.attack_target(p, 1 + 2 * equipped_arts(p))
@effect("Helping Hand")
def _(g, p, x):
    if not from_discard(g, p, "Weapon"):
        tutor_to_hand(g, p, "Artifact", 4)


# ============================ ARTIFACTS (fire each turn) ============================
@effect("Ethereal Fragment")
def _(g, p, x): g.attack_target(p, 3)
@effect("Mystic Purifier")
def _(g, p, x): g.attack_target(p, 2); destroy_one(g, p)   # 2 DMG + may destroy a chosen card
@effect("Arcane Chalice")
def _(g, p, x):
    g.attack_target(p, 3)
    if g.village < g.village_max // 2:
        g.heal_village(2)
    else:
        heal_lowest(g, 2)
@effect("Power Cube")
def _(g, p, x): g.attack_target(p, max(5, equipped_arts(p)))
@effect("Sacrificial Scepter")
def _(g, p, x):
    g.attack_target(p, 2)
    do = g.choose(
        "Destroy Sacrificial Scepter to fetch a card (≤8 Mana) to your discard?",
        [True, False], default=True,
        labeler=lambda b: "Yes — tutor + destroy" if b else "No — keep artifact",
    )
    if do and tutor_to_discard(g, p, None, 8):
        x.consumed = True
@effect("Soulfire Brazier")
def _(g, p, x): g.attack_target(p, 4)
@effect("Affinity Beacon")
def _(g, p, x): g.attack_target(p, min(8, max(4, 2 + 2 * p.affinity)))
@effect("Rupture Relic")
def _(g, p, x): g.attack_target(p, 2 * max(1, equipped_arts(p)))
@effect("Alliance Amulet")
def _(g, p, x): g.attack_target(p, 1 + 2 * x.support_used)
@effect("Arcane Tome")
def _(g, p, x): g.attack_target(p, 1); _draw(g, p, 1)
@effect("Bloodfire Charm")
def _(g, p, x):
    max_spend = min(3, max(0, p.hp - 1))
    if max_spend <= 0:
        g.attack_target(p, 2)
        return
    spend = g.choose(
        "Bloodfire Charm: sacrifice HP for +2 DMG each? (base 2 DMG)",
        list(range(0, max_spend + 1)), default=min(2, max_spend),
        labeler=lambda n: f"Sacrifice {n} HP → {2 + 2 * n} DMG" if n else "No sacrifice → 2 DMG",
    )
    p.hp -= spend
    g.attack_target(p, 2 + 2 * spend)
@effect("Eternal Charm")
def _(g, p, x): g.attack_target(p, 2); refire(g, p, x, 1)
@effect("Mystic Offering")
def _(g, p, x):
    g.attack_target(p, 2)
    do = g.choose(
        "Destroy Mystic Offering to fetch an Artifact (≤5 Mana) to your discard?",
        [True, False], default=True,
        labeler=lambda b: "Yes — tutor + destroy" if b else "No — keep artifact",
    )
    if do and tutor_to_discard(g, p, "Artifact", 5):
        x.consumed = True
@effect("Ring of Arms")
def _(g, p, x): g.attack_target(p, 2); from_discard(g, p,"Weapon")
@effect("Slayer's Relic")
def _(g, p, x):
    before = len(g.minions)
    g.attack_target(p, 2)
    if len(g.minions) < before and p.slots < SLOT_CAP:
        p.slots += 1                              # gain a slot on minion kill
@effect("Sustaining Sigil")
def _(g, p, x): g.attack_target(p, 2); from_discard(g, p,"Mana")
@effect("Wandering Wisp")
def _(g, p, x):                                   # slotless: played from hand, passes right
    g.attack_target(p, 2)
    nb = g.players[(p.pid + 1) % len(g.players)]
    nb.discard.append(g.cards["Wandering Wisp"])
@effect("Mystic Seer's Lens")
def _(g, p, x): _draw(g, p, 2)
@effect("Timeless Talisman")
def _(g, p, x):
    g._postpone_boss = True
    x.consumed = True                              # skip telegraphed boss card, then remove artifact


# ============================ SUPPORT ============================
@effect("Cycle of Life")
def _(g, p, x): from_discard(g, p,"Support")
@effect("Arcane Retrieval")
def _(g, p, x): refire(g, p, x, 1)                # Wizard: trigger 1 equipped Artifact again
@effect("Improvised Strike")
def _(g, p, x): from_discard(g, p,"Weapon")
@effect("Blessing of Faith")
def _(g, p, x):
    targets = sorted((q for q in g.players if q.hp < PLAYER_HP), key=lambda q: q.hp)[:2]
    if not targets:
        targets = sorted(g.players, key=lambda q: q.hp)[:2]
    for q in targets:
        g.heal_player(q, 2)
@effect("Volley")  # also weapon-class for Ranger; safe duplicate
def _(g, p, x): g.aoe(p, 2)
@effect("Armed Militia")
def _(g, p, x): _trigger_village(g, p, bonus=3)
@effect("Blood Ritual")
def _(g, p, x):
    p.hp -= 2
    if g.minions:
        m = max(g.minions, key=lambda m: m.hp)
        g._dmg_accum += m.hp
        g.log(f"P{p.pid} sacrifices HP to defeat {m.card.name}")
        defeat_minion(g, p, m)
    else:
        g.aoe(p, 4)
@effect("Composter")
def _(g, p, x):
    if destroy_one(g, p):                         # destroy a chosen card, then draw
        _draw(g, p, 1)
@effect("Encourage")
def _(g, p, x):
    if not refire(g, p, x, 1):                    # use an equipped Artifact again, else replay a Weapon
        replay_weapon_from_discard(g, p, x)
@effect("Fresh Supplies")
def _(g, p, x):
    for pl in living(g): _draw(g, pl, 1)
@effect("Make A Wish")
def _(g, p, x): tutor_to_discard(g, p, None, 10)
@effect("Natural Selection")
def _(g, p, x): _draw(g, p, 2); discard_n(g, p, 1)
@effect("Secret Technique")
def _(g, p, x):
    tgt = min(living(g), key=lambda q: q.hp) if g.village >= 15 else p
    _use_ability(g, tgt, x, free=True)
@effect("Well Prepared")
def _(g, p, x):
    default = "village" if g.village < g.village_max // 2 else "self"
    tgt = g.choose("Apply 6 prevention to:", ["village", "self"], default=default,
                   labeler=lambda t: "Village" if t == "village" else f"P{p.pid} ({p.cls})")
    if tgt == "village":
        g.village_prevent += 6
    else:
        p.prevent += 6

@effect("Aegis Ward")
def _(g, p, x):
    default = "village" if g.village < g.village_max // 2 else "self"
    tgt = g.choose("Apply 5 prevention to:", ["village", "self"], default=default,
                   labeler=lambda t: "Village" if t == "village" else f"P{p.pid} ({p.cls})")
    if tgt == "village":
        g.village_prevent += 5
    else:
        p.prevent += 5
@effect("Worthy Sacrifice")
def _(g, p, x):
    if destroy_one(g, p):                         # destroy a chosen card, draw if you did
        _draw(g, p, 1)


# ============================ BOSS ============================
@effect("Absorb Mana")
def _(g, p, x):
    for pl in rand_players(g, 2): lose_aff(pl)
@effect("Claw Swipe")
def _(g, p, x): g.damage_village(5)
@effect("Tail Attack")
def _(g, p, x): g.damage_village(6)
@effect("Cutting Wind")
def _(g, p, x):
    for pl in rand_players(g, 2): g.damage_player(pl, 2)
    for pl in rand_players(g, 1): discard_n(g, pl, 2)
@effect("Demand Tribute")
def _(g, p, x): discard_collective(g, 5); g.damage_village(3)
@effect("Fire Breath")
def _(g, p, x):
    for pl in living(g): g.damage_player(pl, 2)
    discard_collective(g, 2)
@effect("Flammable Tools")
def _(g, p, x):
    discard_collective(g, 2)
    for pl in living(g): _draw(g, pl, 1)
    g.damage_village(3)
@effect("Mana Dominance")
def _(g, p, x):
    t = max(living(g), key=lambda q: q.affinity, default=None)
    if t: g.damage_player(t, 5)
@effect("Mana Ignition")
def _(g, p, x):
    t = max(living(g), key=lambda q: mana_in_hand(q), default=None)
    if t: g.damage_player(t, mana_in_hand(t))
@effect("Minion Onslaught")
def _(g, p, x): g.damage_village(1 + 2 * len(g.minions))
@effect("Predatory Strike")
def _(g, p, x):
    t = max(living(g), key=lambda q: q.hp, default=None)
    if t: g.damage_player(t, 5)
@effect("Rising Hostility")
def _(g, p, x): g.damage_village(3); g.anger += 2
@effect("Scorching Gaze")
def _(g, p, x):
    for pl in rand_players(g, 1): g.damage_player(pl, 3)
    for pl in rand_players(g, 2): discard_n(g, pl, 1)
@effect("Shared Sacrifice")
def _(g, p, x): discard_collective(g, len(living(g))); g.damage_village(3)
@effect("Threatening Glare")
def _(g, p, x):
    for pl in rand_players(g, 3): g.damage_player(pl, 2)
    for pl in rand_players(g, 2): discard_n(g, pl, 1)
@effect("Bully the Weak")
def _(g, p, x):
    t = min(living(g), key=lambda q: q.affinity, default=None)
    if t: g.damage_player(t, 5)
@effect("Material Damage")
def _(g, p, x):
    for pl in rand_players(g, 2):
        if pl.equipped: pl.discard.append(pl.equipped.pop().card)
@effect("Wide Swing")
def _(g, p, x):
    for pl in living(g): g.damage_player(pl, 2)


# ============================ MINIONS (per-round attack) ============================
@effect("Dragon Cultist")
def _(g, p, x):
    for pl in rand_players(g, 1): g.damage_player(pl, 3)
    for pl in rand_players(g, 1): lose_aff(pl)
@effect("Dragon Lancer")
def _(g, p, x):
    t = max(living(g), key=lambda q: mana_in_hand(q), default=None)
    if t: g.damage_player(t, mana_in_hand(t))
@effect("Fire Breather")
def _(g, p, x): g.damage_village(5)
@effect("Kobold Archer")
def _(g, p, x):
    for pl in rand_players(g, 1): g.damage_player(pl, 2)
    g.damage_village(2)
@effect("Kobold Defender")
def _(g, p, x): g.damage_village(1)
@effect("Kobold Horde")
def _(g, p, x):
    g.damage_village(5)
    for pl in rand_players(g, 1): discard_n(g, pl, 1)
@effect("Kobold Marauder")
def _(g, p, x): g.damage_village(4)
@effect("Kobold Shaman")
def _(g, p, x):
    tot = len(living(g))
    for pl in rand_players(g, 1): g.damage_player(pl, max(1, tot // 2 or 1))
    for pl in rand_players(g, 1): lose_aff(pl)
@effect("Kobold Thief")
def _(g, p, x): discard_collective(g, 3)
@effect("Wyrm")
def _(g, p, x):
    t = max(living(g), key=lambda q: q.hp, default=None)
    if t: g.damage_player(t, 5)
@effect("Wyrmling")
def _(g, p, x):
    for pl in rand_players(g, 1): g.damage_player(pl, 4)
    for pl in rand_players(g, 1): discard_n(g, pl, 1)
@effect("Kobold")
def _(g, p, x):
    g.damage_village(3)
    for pl in rand_players(g, 1): discard_n(g, pl, 1)


# ============================ DISASTERS ============================
@effect("Power Anomaly")
def _(g, p, x):
    for pl in living(g): lose_aff(pl)
@effect("Fiery Explosion")
def _(g, p, x):
    for pl in living(g): g.damage_player(pl, 3)
    g.damage_village(3)
@effect("Gear Purge")
def _(g, p, x):
    for pl in living(g):
        if pl.equipped: pl.discard.append(pl.equipped.pop().card)
@effect("Minion Frenzy")
def _(g, p, x):
    for m in list(g.minions): EFFECTS[m.card.name](g, None, None)
@effect("Reawakening")
def _(g, p, x):
    for c in reversed(g.boss_discard):
        if c.category == "Minion":
            g.minions.append(Minion(c, minion_hp(g, c)))
            g.boss_discard.remove(c)
            break
@effect("Supply Depletion")
def _(g, p, x):
    for pl in living(g):
        discard_n(g, pl, 2)
@effect("Trade Block")
def _(g, p, x): g.no_buy = True
@effect("Unnatural Disaster")
def _(g, p, x): g.damage_village(8)
@effect("Critical Hit")
def _(g, p, x):
    t = min(living(g), key=lambda q: q.hp, default=None)
    if t: g.damage_player(t, 5)
@effect("Tactical Retreat")
def _(g, p, x):
    if g.minions:
        m = min(g.minions, key=lambda x: x.hp); g.minions.remove(m); g.boss_discard.append(m.card)
        revived = 2
    else:
        revived = 1
    mins = [c for c in g.boss_discard if c.category == "Minion"]
    for c in mins[:revived]:
        g.minions.append(Minion(c, minion_hp(g, c)))
        g.boss_discard.remove(c)


# ============================ shared internals ============================
def _draw(g, p, n):
    for _ in range(n):
        c = p.draw_one()
        if c is None: break
        p.hand.append(c)

def _trigger_village(g, p, bonus=0):
    dmg = (6 if p.ultimate else 2) + bonus
    g.attack_target(p, dmg, prefer_minion=False)

def _try_ability(g, p, x):
    """'You may use your ability' rider - free, no extra mana."""
    _use_ability(g, p, x, free=True)

def _use_ability(g, p, x, free=False):
    from .abilities import use_ability
    use_ability(g, p, x, free=free)
