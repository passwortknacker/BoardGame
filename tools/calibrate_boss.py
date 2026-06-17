"""Find the Boss HP that puts each count's TOP-10 class combos near a target win rate."""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root on path
from sim.cards import load_cards
from sim.game import play_game, CLASSES, CLASS_STRAT

cards = load_cards()
BASE = dict(boss_comp=(12, 7), disaster_n=6, village_base=20, village_slope=10)


def win_avg(P, combos, hp, g=30):
    tot = 0
    for combo in combos:
        team = [(c, CLASS_STRAT[c]) for c in combo]
        w = sum(play_game(cards, P=P, seed=s, team=team, boss_base=hp, boss_slope=0, **BASE)["result"] == "win"
                for s in range(g))
        tot += 100 * w / g
    return tot / len(combos)


def top10(P, g=40):
    combos = list(itertools.combinations(sorted(CLASSES), P))
    scored = []
    for combo in combos:
        team = [(c, CLASS_STRAT[c]) for c in combo]
        w = sum(play_game(cards, P=P, seed=s, team=team, boss_base=40, boss_slope=10, **BASE)["result"] == "win"
                for s in range(g))
        scored.append((w, combo))
    scored.sort(reverse=True)
    return [c for _, c in scored[:10]]


for P, hps in [(3, [70, 85, 100, 115]), (4, [55, 65, 75, 85])]:
    combos = top10(P)
    print(f"\n=== {P}p top-10 combos vs Boss HP (Village {20+10*P}, target ~70%) ===")
    for hp in hps:
        print(f"  Boss HP {hp:>3}: top-10 avg win {win_avg(P, combos, hp):.0f}%", flush=True)
