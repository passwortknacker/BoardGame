"""Rudimentary hotseat text playtest for Marvin's board game (built on sim/).

You choose the player count and party (defaults to #1 sim-ranked combo); you control all heroes.
Real-deck rules: no-shuffle decks, slot engine, affinity, abilities/ultimates, the Red Dragon
boss with telegraph + Anger->Disaster + Level Up, Village, minions. Buy from a limited market
(reshuffle a category for 1 Mana). Targeting for attacks/heals is automatic (rudimentary v1).

Run:  python play.py
"""
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root on path
from sim.cards import load_cards
from sim.engine import Game, Player, EffectContext, Equipped, PLAYER_HP
from sim.effects import EFFECTS
from sim import boss as bossmod
from sim.game import build_starter, boss_turns_for, CLASS_STRAT
from sim.abilities import use_ability, ABILITY_COST

TOP_COMBOS_PATH = Path(__file__).resolve().parents[1] / "data" / "top_combos.json"


def load_top_combos():
    with open(TOP_COMBOS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {int(k): v for k, v in data.items() if k.isdigit()}

MARKET_SIZE = {"Mana": 5, "Weapon": 5, "Artifact": 4, "Support": 4}
ABILITY_TEXT = {
    "Ranger": "Village heal 2 + 2 DMG  (Ult: 3 + 3)",
    "Paladin": "Heal a player 2 + 2 DMG  (Ult: 3 + 3)",
    "Druid": "Heal player 2 + Village 2  (Ult: 3 + 3)",
    "Cleric": "Heal a player 4  (Ult: heal 2 players 4)",
    "Wizard": "Fire 1 equipped Artifact extra  (Ult: 2)",
    "Weaponmaster": "Play 1 Weapon from Discard  (Ult: 2)",
    "Enchanter": "Take an Artifact Discard->Hand  (Ult: Supply->Discard)",
    "Blacksmith": "Take a Weapon Discard->Hand  (Ult: Supply->Discard)",
    "Bard": "1 Player draws 1 card  (Ult: heal 3 + draw)",
}


def ask_int(prompt, lo, hi):
    while True:
        try:
            v = int(input(prompt).strip())
            if lo <= v <= hi:
                return v
        except (ValueError, EOFError):
            pass
        print(f"  enter a number {lo}-{hi}")


def ask_int_default(prompt, lo, hi, default):
    while True:
        try:
            raw = input(prompt).strip()
            if not raw:
                return default
            v = int(raw)
            if lo <= v <= hi:
                return v
        except (ValueError, EOFError):
            pass
        print(f"  enter a number {lo}-{hi}, or Enter for {default}")


class Market:
    """Limited buyable market of 'All'-class cards; reshuffle a category for 1 Mana."""
    def __init__(self, cards, rng):
        self.rng = rng
        self.pools = {}
        for cat in MARKET_SIZE:
            self.pools[cat] = [c for c in cards.values()
                               if c.cls == "All" and c.category == cat
                               and c.cost is not None and c.cost > 0]   # 0-cost = starters, not buyable
        self.offered = {cat: self._draw(cat) for cat in MARKET_SIZE}

    def _draw(self, cat):
        pool = self.pools[cat]
        k = min(MARKET_SIZE[cat], len(pool))
        return self.rng.sample(pool, k)

    def reshuffle(self, cat):
        self.offered[cat] = self._draw(cat)

    def replace(self, card):
        """After a buy, swap the bought card out for a fresh one (refill the slot)."""
        for cat, lst in self.offered.items():
            if card in lst:
                pool = [c for c in self.pools[cat] if c not in lst]
                if pool:
                    lst[lst.index(card)] = self.rng.choice(pool)
                return

    def buyable(self, p, mana):
        out = []
        for cat in MARKET_SIZE:
            for c in self.offered[cat]:
                if c.cost <= mana and not (c.tier2 and p.affinity < 2):
                    out.append(c)
        return out


def cli_chooser(prompt, options, labeler):
    """Interactive picker used by effects (which artifact to re-fire, which card to fetch)."""
    print(f"    {prompt}")
    for i, o in enumerate(options):
        print(f"      {i}: {labeler(o)}")
    k = ask_int("    choose # (0 = best/default): ", 0, len(options) - 1)
    return options[k]


def line(ch="-", n=64):
    print(ch * n)


def show_state(g):
    nxt = g.boss_deck[0].name if g.boss_deck else "(reshuffle)"
    line("=")
    print(f"ROUND {g.round}  |  Red Dragon HP {g.boss}  |  Anger {g.anger}/{len(g.players)+2}  "
          f"|  Level {g.boss_level}")
    print(f"Village HP {g.village}  |  Next boss card (telegraphed): {nxt}")
    if g.minions:
        print("Minions: " + ", ".join(f"{m.card.name}({m.hp}hp)" for m in g.minions))
    for q in g.players:
        eq = ",".join(e.card.name + ("*" if e.fires_from_turn > q.turn_no + 1 else "") for e in q.equipped)
        print(f"  P{q.pid} {q.cls:12} HP {q.hp:2}  Aff {q.affinity}  Slots {len(q.equipped)}/{q.slots}"
              + (f"  [{eq}]" if eq else ""))
    line("=")


def show_market(g, p, market, mana):
    print(f"  -- MARKET (you have {mana} Mana;  [x] = can't afford / * = needs Affinity 2) --")
    for cat in MARKET_SIZE:
        print(f"   {cat}:")
        for c in market.offered[cat]:
            gate = c.tier2 and p.affinity < 2
            flag = "x" if (c.cost > mana or gate) else " "
            tier = f"/{c.tier}" if c.tier else ""
            print(f"     [{flag}] {c.name} ({c.cost}{'*' if gate else ''}{tier}) : {c.text}")


def human_turn(g, p, market):
    p.turn_no += 1
    ctx = EffectContext()
    g.ctx = ctx
    # fire charged artifacts
    for e in list(p.equipped):
        if e.fires_from_turn <= p.turn_no:
            g._dmg_accum = 0
            EFFECTS[e.card.name](g, p, ctx)
            print(f"  >> {e.card.name} fires (artifact engine)")
            if g.check_end():
                return
    print(f"\n*** P{p.pid} {p.cls} - your turn ***   Ability: {ABILITY_TEXT[p.cls]}")
    used_ability = False
    turn_finished = False
    while not turn_finished:
        while True:
            mana = ctx.mana - ctx.mana_spent
            hand = p.hand
            print(f"\n  Mana: {mana}   Hand:")
            for i, c in enumerate(hand):
                print(f"    {i}: {c.name} ({c.category}{'/'+c.tier if c.tier else ''}) : {c.text}")
            print("  commands: play <i> | equip <i> | ability | affinity | buy | reshuffle | slot | state | done")
            cmd = input("  > ").strip().lower().split()
            if not cmd:
                continue
            op = cmd[0]
            if op == "done":
                break
            elif op == "state":
                show_state(g)
            elif op == "affinity":
                if p.affinity >= 3:
                    print("    already at Affinity 3")
                elif ctx.mana - ctx.mana_spent < 3:
                    print("    need 3 Mana to raise Affinity")
                else:
                    ctx.mana_spent += 3; p.affinity += 1
                    print(f"    Affinity raised -> {p.affinity}")
            elif op == "play" and len(cmd) > 1 and cmd[1].isdigit():
                i = int(cmd[1])
                if 0 <= i < len(hand):
                    if hand[i].category == "Artifact" and hand[i].name != "Wandering Wisp":
                        print("    artifacts can't be played - use 'equip' to slot them (they fire each turn)")
                        continue
                    c = hand.pop(i)
                    g._dmg_accum = 0; g._heal_accum = 0; ctx.consumed = False
                    mb, affb = ctx.mana, p.affinity
                    if c.category == "Mana":
                        ctx.mana_cards_used += 1
                    elif c.category == "Support":
                        ctx.support_used += 1
                    elif c.category == "Weapon" or c.name == "Wandering Wisp":
                        ctx.weapons_played += 1 if c.name != "Wandering Wisp" else 0
                    EFFECTS[c.name](g, p, ctx)
                    if c.name != "Wandering Wisp" and not ctx.consumed:
                        p.discard.append(c)
                    deltas = []
                    if ctx.mana - mb: deltas.append(f"+{ctx.mana-mb} mana")
                    if g._dmg_accum: deltas.append(f"{g._dmg_accum} dmg")
                    if g._heal_accum: deltas.append(f"{g._heal_accum} heal")
                    if p.affinity != affb: deltas.append(f"affinity->{p.affinity}")
                    if ctx.consumed: deltas.append("destroyed/thinned")
                    print(f"    played {c.name}: {', '.join(deltas) or 'resolved'}")
                    if g.check_end():
                        return
            elif op == "ability":
                if used_ability:
                    print("    already used your ability this turn")
                elif ctx.mana - ctx.mana_spent < ABILITY_COST:
                    print(f"    need {ABILITY_COST} Mana")
                else:
                    ctx.mana_spent += ABILITY_COST
                    used_ability = True
                    use_ability(g, p, ctx)
                    print(f"    used {p.cls} ability"
                          + (" (ULTIMATE)" if p.ultimate else ""))
                    if g.check_end():
                        return
            elif op == "reshuffle":
                if ctx.mana - ctx.mana_spent < 1:
                    print("    need 1 Mana")
                else:
                    cats = list(MARKET_SIZE)
                    for j, cat in enumerate(cats):
                        print(f"      {j}: {cat}")
                    k = ask_int("    reshuffle which category #: ", 0, len(cats) - 1)
                    ctx.mana_spent += 1
                    market.reshuffle(cats[k])
                    print(f"    reshuffled {cats[k]} (-1 Mana)")
            elif op == "buy":
                show_market(g, p, market, ctx.mana - ctx.mana_spent)
                opts = market.buyable(p, ctx.mana - ctx.mana_spent)
                if not opts:
                    print("    nothing affordable")
                    continue
                print("    affordable now:")
                for j, c in enumerate(opts):
                    tier = f"/{c.tier}" if c.tier else ""
                    print(f"      {j}: {c.name} ({c.category}{tier}, {c.cost}) : {c.text}")
                k = ask_int("    buy # (or -1 cancel): ", -1, len(opts) - 1)
                if k >= 0:
                    c = opts[k]
                    ctx.mana_spent += c.cost
                    p.gain_card(c)
                    market.replace(c)               # refill the market slot with a fresh card
                    print(f"    bought {c.name} -> under your deck (market refilled)")
            elif op == "slot":
                if p.slots >= 5:
                    print("    already at 5 slots")
                else:
                    cost = g.slot_cost[p.slots]
                    if ctx.mana - ctx.mana_spent < cost:
                        print(f"    next slot costs {cost} Mana")
                    else:
                        ctx.mana_spent += cost; p.slots += 1
                        print(f"    bought artifact slot #{p.slots} (-{cost} Mana)")
            elif op == "equip" and len(cmd) > 1 and cmd[1].isdigit():
                i = int(cmd[1])
                if 0 <= i < len(hand) and hand[i].category == "Artifact" and hand[i].name != "Wandering Wisp":
                    if p.free_slots() <= 0:
                        print("    no free slot - buy one with 'slot' first (or it can't be equipped)")
                    else:
                        c = hand.pop(i)
                        p.equipped.append(Equipped(c, p.turn_no + g.charge_turns))
                        print(f"    equipped {c.name} (charging; fires next turn)")
                else:
                    print("    that card isn't an equippable artifact")
            else:
                print("    ?")
        # draw phase: optionally keep some cards, then redraw to 5
        if not p.hand:
            p.draw_to_full()
            turn_finished = True
            continue
        print(f"\n  DRAW PHASE — hand: {[c.name for c in p.hand]}")
        print("  Keep cards by index (e.g. '0 2'), Enter to discard all and redraw to 5,")
        print("  or type cancel to keep playing:")
        raw = input("  keep> ").strip()
        if raw.lower() in ("cancel", "abort", "back"):
            print("  (draw phase cancelled — continue your turn)")
            continue
        if raw:
            try:
                keep_idx = {int(x) for x in raw.split() if x.isdigit()}
                kept = [c for i, c in enumerate(p.hand) if i in keep_idx]
                for c in p.hand:
                    if c not in kept:
                        p.discard.append(c)
                p.hand = kept
            except ValueError:
                for c in p.hand:
                    p.discard.append(c)
                p.hand = []
        else:
            for c in p.hand:
                p.discard.append(c)
            p.hand = []
        p.draw_to_full()
        turn_finished = True


def main():
    cards = load_cards()
    rng = random.Random()
    print("=== Marvin's Board Game - text playtest ===")
    top = load_top_combos()
    P = ask_int("Players (2-4): ", 2, 4)
    combos = top[P]
    print("Sim-ranked parties:")
    for i, entry in enumerate(combos):
        cls = " + ".join(entry["classes"])
        print(f"  {i + 1}. {cls}  ({entry['winrate']}% win)")
    pick = ask_int_default(f"Combo # (1-{len(combos)}, Enter = #1): ", 1, len(combos), 1)
    entry = combos[pick - 1]
    combo = tuple(entry["classes"])
    print(f"Party: {' + '.join(combo)}  ({entry['winrate']}% sim win)")
    players = []
    for i, cls in enumerate(combo):
        pl = Player(i, cls, build_starter(cards, cls))
        pl.strategy = CLASS_STRAT[cls]
        pl.draw_to_full()
        players.append(pl)
    deck = bossmod.build_boss_deck(cards, rng, 12, 7)
    g = Game(players, deck, cards, rng, trace=True)
    g.disaster_pile = bossmod.build_disaster_pile(cards, rng, 6)
    g.boss = 40 + 10 * P
    g.village = 20 + 10 * P
    g.village_max = g.village
    g.chooser = cli_chooser            # let the human pick re-fire targets / tutored cards
    market = Market(cards, rng)

    for rnd in range(1, 17):
        g.round = rnd
        g.village_prevent = 0
        for pl in players:
            pl.prevent = 0
        g.no_buy = False
        order = [("P", pl) for pl in players if pl.alive]
        if P % 2 == 1:
            joker = max((pl for pl in players if pl.alive),
                        key=lambda q: (len(q.equipped), q.affinity, q.hp))
            order.append(("J", joker))
        order += [("B", None)] * boss_turns_for(P, rng)
        rng.shuffle(order)
        show_state(g)
        seq = ["BOSS" if k == "B" else (f"P{pl.pid}*joker" if k == "J" else f"P{pl.pid}") for k, pl in order]
        print("Turn order this round: " + " -> ".join(seq))
        for kind, pl in order:
            if g.result:
                break
            if kind in ("P", "J"):
                if kind == "J":
                    print(f"\n[JOKER extra turn -> P{pl.pid}]")
                human_turn(g, pl, market)
            else:
                print("\n[BOSS TURN]")
                bossmod.boss_turn(g)
            if g.check_end():
                break
        if g.result:
            break
        if g.minions:
            print("\n[END OF ROUND - minions attack]")
            bossmod.minions_attack(g)
        if g.check_end():
            break
    print()
    line("=")
    res = {"win": "VICTORY - the Red Dragon is slain!", "village": "DEFEAT - the Village fell.",
           "players": "DEFEAT - all heroes are down.", "timeout": "DRAW - ran out of rounds."}
    print(res.get(g.result, g.result))
    line("=")


if __name__ == "__main__":
    main()
