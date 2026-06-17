"""Orchestrate one full game and return a result record."""
from __future__ import annotations
import random
from .cards import Card
from .engine import Game, Player, EffectContext, ROUND_CAP
from .effects import EFFECTS
from . import ai, boss as bossmod

CLASSES = ["Ranger", "Paladin", "Druid", "Cleric", "Wizard",
           "Weaponmaster", "Enchanter", "Blacksmith", "Bard"]

# role -> candidate classes, and role -> buy-strategy
ROLE_CLASSES = {
    "caster":  ["Wizard", "Enchanter"],
    "fighter": ["Weaponmaster", "Blacksmith", "Paladin", "Ranger"],
    "healer":  ["Cleric", "Bard", "Druid"],          # Cleric = full healer
    "village": ["Druid", "Ranger"],                  # heal the Village
}
ROLE_STRAT = {"caster": "caster", "fighter": "weapons", "healer": "healer", "village": "support"}

# class -> the strategy that fits its identity (design_plan.md class roles)
CLASS_STRAT = {
    "Wizard": "caster", "Enchanter": "caster",
    "Cleric": "healer", "Bard": "healer", "Druid": "support",
    "Ranger": "support", "Paladin": "weapons",
    "Weaponmaster": "weapons", "Blacksmith": "weapons",
}

# preset comps by player count (the user's "caster+fighter+healer+village protector")
DEFAULT_ROLES = {
    2: ["fighter", "village"],          # 2p is survival-bound -> a defensive comp fits best
    3: ["caster", "fighter", "healer"],
    4: ["caster", "fighter", "healer", "village"],
}


def build_team(P, rng, roles=None) -> list[tuple[str, str]]:
    roles = roles or DEFAULT_ROLES[P]
    used, team = set(), []
    for role in roles:
        cands = [c for c in ROLE_CLASSES[role] if c not in used] or ROLE_CLASSES[role]
        cls = rng.choice(cands); used.add(cls)
        team.append((cls, ROLE_STRAT[role]))
    return team


def build_starter(cards: dict[str, Card], cls: str) -> list[Card]:
    """Design's 8-card starter: 4 Mana Crystal + 1 class Mana + 1 class Support + 2 class Weapon.
    Falls back to Mana Crystal for any class slot that has no such 0-cost card."""
    zero = [c for c in cards.values()
            if c.cls == cls and c.cost == 0 and c.is_player_card and c.name != "Wandering Wisp"]
    crystal = cards["Mana Crystal"]

    def pick(cat, n):
        got = [c for c in zero if c.category == cat][:n]
        return got + [crystal] * (n - len(got))

    deck = [crystal] * 4 + pick("Mana", 1) + pick("Support", 1) + pick("Weapon", 2)
    return deck[:8]


def boss_turns_for(P: int, rng: random.Random) -> int:
    """Boss turns per round = ceil(players / 2) (design_plan.md turn order)."""
    return -(-P // 2)


def player_turn(g: Game, p: Player):
    if not p.alive:
        return
    p.turn_no += 1
    ctx = EffectContext()
    g.ctx = ctx
    foc = g.focused(p)
    if foc:
        eqd = [e.card.name + ("(charging)" if e.fires_from_turn > p.turn_no else "") for e in p.equipped]
        g.vlog(f"\n--- ROUND {g.round} | P{p.pid} {p.cls}/{p.strategy} | personal turn {p.turn_no} ---")
        g.vlog(f"    state: hp={p.hp} affinity={p.affinity} slots={len(p.equipped)}/{p.slots} "
               f"village={g.village} boss={g.boss} anger={g.anger}")
        g.vlog(f"    deck={len(p.deck)} discard={len(p.discard)} equipped={eqd}")
        g.vlog(f"    HAND DRAWN: {[c.name for c in p.hand]}")
    # fire artifacts that have finished charging
    for eq in list(p.equipped):
        if eq not in p.equipped:        # already consumed via a refire earlier this loop
            continue
        if eq.fires_from_turn <= p.turn_no:
            b = g.boss
            ctx.consumed = False
            ctx.artifacts_fired += 1
            EFFECTS[eq.card.name](g, p, ctx)
            ctx.fired_artifact_eqs.add(id(eq))
            if ctx.consumed and eq in p.equipped:
                p.equipped.remove(eq)
            g.stats[f"fire:{eq.card.name}"] += 1
            if foc:
                msg = f"    FIRE artifact '{eq.card.name}': boss {b}->{g.boss}"
                if ctx.consumed:
                    msg += " (destroyed)"
                g.vlog(msg)
            if g.check_end():
                return
    prof = ai.PROFILES[p.strategy]
    ai.play_hand(g, p, ctx)
    if g.check_end():
        return
    ai.do_buys(g, p, ctx, prof)
    ai.do_equip(g, p, ctx, prof)
    if foc:
        g.vlog(f"    mana this turn: {ctx.mana} generated, {ctx.mana_spent} spent, "
               f"{max(0, ctx.mana - ctx.mana_spent)} wasted")
    # draw phase: optional discard (AI keeps Mana/Artifacts), then refill to 5
    ai.draw_phase(g, p)
    if foc:
        g.vlog(f"    HAND AFTER DRAW: {[c.name for c in p.hand]}")


def play_game(cards, P=2, strategies=None, seed=0, trace=False,
              boss_base=40, boss_slope=10, boss_comp=(12, 7), disaster_n=6,
              slot_cost=None, charge_turns=1, player_hp=None,
              team=None, roles=None, village_base=20, village_slope=10,
              verbose=False, focal=0) -> dict:
    rng = random.Random(seed)

    def random_classes():
        return rng.sample(CLASSES, P) if P <= len(CLASSES) else [rng.choice(CLASSES) for _ in range(P)]

    if strategies == "by_class":
        chosen = random_classes()                       # random classes, class-fitting strategies
        strategies = [CLASS_STRAT[c] for c in chosen]
    elif team is not None:
        chosen = [t[0] for t in team]
        strategies = [t[1] for t in team]
    elif roles is not None or strategies is None:
        team = build_team(P, rng, roles)                # role-based comp
        chosen = [t[0] for t in team]
        strategies = [t[1] for t in team]
    else:
        chosen = random_classes()                       # explicit strategies, random classes
        if not isinstance(strategies, list):
            strategies = [strategies] * P
    players = []
    for i in range(P):
        pl = Player(i, chosen[i], build_starter(cards, chosen[i]))
        pl.strategy = strategies[i % len(strategies)]
        if player_hp:
            pl.hp = player_hp
        pl.draw_to_full()
        players.append(pl)

    deck = bossmod.build_boss_deck(cards, rng, *boss_comp)
    g = Game(players, deck, cards, rng, trace=trace)
    g.disaster_pile = bossmod.build_disaster_pile(cards, rng, disaster_n)
    g.boss = boss_base + boss_slope * P
    g.village = village_base + village_slope * P
    g.village_max = g.village
    if slot_cost:
        g.slot_cost = slot_cost
    g.charge_turns = charge_turns
    g.verbose = verbose
    g.focal = focal
    if verbose:
        g.vlog("=" * 72)
        g.vlog(f"GAME — {P} players | Boss HP {g.boss} | Village HP {g.village} | seed {seed}")
        g.vlog(f"Boss deck: {len(g.boss_deck)} Boss+Minion cards | Disaster pile: {len(g.disaster_pile)} | "
               f"Anger triggers a Disaster at >= {P + 2}")
        for pl in players:
            g.vlog(f"  P{pl.pid}: {pl.cls} ({pl.strategy}) hp{pl.hp} — "
                   f"start deck: {sorted(c.name for c in pl.deck + pl.hand)}")
        g.vlog(f"FOCAL (full detail) = P{focal} {players[focal].cls}")
        g.vlog("=" * 72)

    for rnd in range(1, ROUND_CAP + 1):
        g.round = rnd
        g.village_prevent = 0
        for pl in players:
            pl.prevent = 0
        g.no_buy = False
        order = [("P", pl) for pl in players if pl.alive]
        # Joker turn for odd player counts: one player takes an extra turn (carry/hypercarry).
        # Design: any player may take it; model it as the best-engine player (most artifacts,
        # then highest affinity) to capture the intended carry.
        if P % 2 == 1:
            alive = [pl for pl in players if pl.alive]
            if alive:
                joker = max(alive, key=lambda q: (len(q.equipped), q.affinity, q.hp))
                order.append(("P", joker))
        order += [("B", None)] * boss_turns_for(P, rng)
        rng.shuffle(order)
        if g.verbose:
            seq = ["BOSS" if k == "B" else f"P{pl.pid}" for k, pl in order]
            g.vlog(f"\n========== ROUND {rnd} == turn order: {seq} | "
                   f"village={g.village} boss={g.boss} anger={g.anger} minions={len(g.minions)} ==========")
        for kind, pl in order:
            if g.result:
                break
            if kind == "P":
                if g.verbose and not g.focused(pl):
                    g.vlog(f"  (P{pl.pid} {pl.cls} takes a turn)")
                player_turn(g, pl)
            else:
                g.vlog("  BOSS TURN:")
                bossmod.boss_turn(g)
            g.check_end()
            if g.result:
                break
        if g.result:
            break
        if g.verbose and g.minions:
            g.vlog(f"  END OF ROUND: {len(g.minions)} minion(s) attack")
        bossmod.minions_attack(g)
        if g.check_end():
            break
    if g.result is None:
        g.result = "timeout"
    if verbose:
        g.vlog("=" * 72)
        g.vlog(f"RESULT: {g.result.upper()} on round {g.round} | "
               f"boss {g.boss} | village {g.village} | players alive "
               f"{sum(1 for pl in players if pl.alive)}/{P}")
        g.vlog("=" * 72)

    return {
        "result": g.result, "round": g.round, "village": g.village,
        "boss": g.boss, "P": P, "stats": g.stats,
        "alive": sum(1 for pl in players if pl.alive),
        "vlines": g.vlines,
    }
