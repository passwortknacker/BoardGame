"""Rank class combinations by win rate (each class plays its fitting strategy),
then report the top 10 per player count and the win rate restricted to those combos."""
import itertools
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root on path
from sim.cards import load_cards
from sim.game import play_game, CLASSES, CLASS_STRAT

cards = load_cards()
CFG = dict(boss_base=40, boss_slope=10, boss_comp=(12, 7), disaster_n=6,
           village_base=20, village_slope=10)
G = 40   # games per combo


def winrate(P, combo, g=G):
    team = [(c, CLASS_STRAT[c]) for c in combo]
    wins = 0
    for s in range(g):
        r = play_game(cards, P=P, seed=s, team=team, **CFG)
        if r["result"] == "win":
            wins += 1
    return 100 * wins / g


for P in (2, 3, 4):
    combos = list(itertools.combinations(sorted(CLASSES), P))
    scored = sorted(((winrate(P, c), c) for c in combos), reverse=True)
    print(f"\n===== {P} players (Boss {40+10*P}, Village {20+10*P}) — {len(combos)} combos, {G} games each =====")
    print("TOP 10:")
    for wr, c in scored[:10]:
        print(f"  {wr:5.0f}%  {' + '.join(c)}")
    top10 = scored[:10]
    avg = sum(wr for wr, _ in top10) / len(top10)
    allavg = sum(wr for wr, _ in scored) / len(scored)
    print(f"  -- top-10 avg win {avg:.0f}%  |  all-combo avg {allavg:.0f}%  |  worst: "
          f"{scored[-1][0]:.0f}% ({' + '.join(scored[-1][1])})")
