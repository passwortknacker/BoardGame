"""Write a full, detailed play-by-play of one simulated game to a file.

Usage:
  python trace_game.py [--p 2] [--seed 0] [--focal 0] [--out game_log.txt] [--roles caster,village]

Logs, for the FOCAL player: every hand drawn, every card played (with its effect deltas:
mana gained, damage dealt, draws, heals), every buy, slot purchase, equip, ability use, and the
draw phase. Logs boss turns, Anger/Disaster triggers, minion attacks, and round structure globally.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # repo root on path
from sim.cards import load_cards
from sim.game import play_game

ap = argparse.ArgumentParser()
ap.add_argument("--p", type=int, default=2)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--focal", type=int, default=0)
ap.add_argument("--roles", default=None, help="comma list e.g. caster,village")
ap.add_argument("--out", default=os.path.join(ROOT, "logs", "game_log.txt"))
args = ap.parse_args()

roles = args.roles.split(",") if args.roles else None
cards = load_cards()
# original-value config (Boss 40+10P, Village 20+10P) so the log reflects the real game
r = play_game(cards, P=args.p, seed=args.seed, focal=args.focal, verbose=True, roles=roles,
              boss_base=40, boss_slope=10, boss_comp=(12, 7), disaster_n=6,
              village_base=20, village_slope=10)

with open(args.out, "w", encoding="utf-8") as f:
    f.write("\n".join(r["vlines"]) + "\n")

print(f"wrote {len(r['vlines'])} lines to {args.out}  (result: {r['result']} round {r['round']})")
