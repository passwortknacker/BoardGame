"""Re-measure win rates for the saved top-10 class combos under the NEW randomized tier-slot
market (mirrors the online test game). 1000 games per combo, TUNED config.

Old win rates in top_combos.json came from the OLD open-supply model (AI could buy any affordable
card every turn). This reports the new win rate + the delta."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # repo root on path
from sim.cards import load_cards
from sim.game import play_game, CLASS_STRAT

CFG = dict(boss_base=40, boss_slope=10, boss_comp=(12, 7), disaster_n=6,
           village_base=20, village_slope=10)
G = 1000

cards = load_cards()
top = json.load(open(os.path.join(ROOT, "data", "top_combos.json"), encoding="utf-8"))


def winrate(P, combo, g=G):
    team = [(c, CLASS_STRAT[c]) for c in combo]
    wins = sum(1 for s in range(g)
               if play_game(cards, P=P, seed=s, team=team, **CFG)["result"] == "win")
    return 100 * wins / g


for P in ("2", "3", "4"):
    print(f"\n===== {P} players — {G} games/combo (randomized market) =====")
    print(f"  {'combo':38} {'new':>6}  {'old':>6}  {'delta':>6}")
    rows = []
    for e in top[P]:
        combo = e["classes"]
        wr = winrate(int(P), combo)
        rows.append((wr, combo, e["winrate"]))
    for wr, combo, old in sorted(rows, reverse=True):
        print(f"  {' + '.join(combo):38} {wr:5.1f}%  {old:5.1f}%  {wr-old:+5.1f}")
    avg = sum(wr for wr, _, _ in rows) / len(rows)
    print(f"  -- top-10 avg (new market): {avg:.1f}%")
