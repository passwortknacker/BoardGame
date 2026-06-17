"""Batch runner + report for the full game simulation.

Usage:
  python run_sim.py                 # race report across P=2,3,4 (mixed strategies)
  python run_sim.py --n 5000        # games per cell
  python run_sim.py --strategy caster
  python run_sim.py --cards         # also print per-card usage (dead/OP scan)
  python run_sim.py --trace 1       # one verbose game (P=2)
"""
import argparse
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root on path
from sim.cards import load_cards
from sim.game import play_game, CLASSES, DEFAULT_ROLES
from sim.ai import PROFILES

TARGET = {2: 60, 3: 62, 4: 70}   # tense-race target band

# Original design numbers: Red Dragon HP 40+10P, Village 20+10P. boss_comp=(n_boss,n_minion).
TUNED = dict(boss_base=40, boss_slope=10, boss_comp=(12, 7), disaster_n=6,
             village_base=20, village_slope=10)
LOCKED = dict(boss_base=50, boss_slope=15, boss_comp=(14, 10), disaster_n=8,
              village_base=20, village_slope=10)


def run_cell(cards, P, n, strategies, cfg, base_seed=0):
    res = Counter(); rounds = 0.0; vsum = 0.0; agg = Counter()
    for i in range(n):
        kw = dict(cfg)
        if strategies is None:
            kw["roles"] = DEFAULT_ROLES[P]          # role-based team comp
        else:
            kw["strategies"] = strategies
        r = play_game(cards, P=P, seed=base_seed + i, **kw)
        res[r["result"]] += 1
        rounds += r["round"]; vsum += max(0, r["village"])
        agg.update(r["stats"])
    wins = res["win"]
    return {
        "win": 100 * wins / n, "round": rounds / n, "village": vsum / n,
        "loss_village": 100 * res["village"] / n, "loss_players": 100 * res["players"] / n,
        "loss_timeout": 100 * res["timeout"] / n, "stats": agg,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--strategy", default="team",
                    help="'team' (role-based comp), 'mixed', or one of %s" % list(PROFILES))
    ap.add_argument("--locked", action="store_true", help="use the locked design numbers (50+15P)")
    ap.add_argument("--cards", action="store_true")
    ap.add_argument("--trace", type=int, default=0, metavar="P")
    args = ap.parse_args()
    cards = load_cards()
    cfg = LOCKED if args.locked else TUNED

    if args.trace:
        play_game(cards, P=args.trace, seed=1, trace=True, **cfg)
        return

    label = "LOCKED design numbers" if args.locked else "TUNED config"
    print(f"=== Full-deck simulation ({args.n} games/cell, {label}, strategy={args.strategy}) ===")
    print(f"{'P':>2} {'bossHP':>6} {'vilHP':>5} {'win%':>6} {'target':>6} {'~round':>7} "
          f"{'Vend':>5} {'loseV%':>7} {'loseP%':>7} {'timeout%':>8}")
    all_stats = Counter()
    for P in (2, 3, 4):
        if args.strategy == "team":
            strat = None                            # role-based team comp
        elif args.strategy == "by_class":
            strat = "by_class"                      # random classes, class-fitting strategies
        elif args.strategy == "mixed":
            strat = list(PROFILES)
        else:
            strat = [args.strategy] * P
        c = run_cell(cards, P, args.n, strat, cfg)
        all_stats.update(c["stats"])
        bhp = cfg["boss_base"] + cfg["boss_slope"] * P
        vhp = cfg["village_base"] + cfg["village_slope"] * P
        print(f"{P:>2} {bhp:>6} {vhp:>5} {c['win']:>6.0f} {TARGET[P]:>6} {c['round']:>7.1f} "
              f"{c['village']:>5.1f} {c['loss_village']:>7.0f} {c['loss_players']:>7.0f} "
              f"{c['loss_timeout']:>8.0f}")

    if args.cards:
        print("\n=== Per-card usage (buy/play/fire counts, all cells) ===")
        buys = {k[4:]: v for k, v in all_stats.items() if k.startswith("buy:") and k != "buy:slot"}
        for name in sorted(buys, key=buys.get, reverse=True):
            plays = all_stats.get(f"play:{name}", 0) + all_stats.get(f"fire:{name}", 0)
            print(f"  {name:24} bought {buys[name]:6}  used {plays:6}")
        never = [c.name for c in cards.values() if c.is_player_card
                 and c.name not in buys and all_stats.get(f"play:{c.name}", 0) == 0]
        if never:
            print("\n  NEVER bought/played (dead or starter-only):")
            for n in never:
                print("   ", n)


if __name__ == "__main__":
    main()
