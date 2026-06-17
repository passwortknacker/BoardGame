"""Compare web card fx export vs sim handlers — run: python audit_web_fx.py"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root on path
from sim.cards import load_cards
from sim.effects import EFFECTS
from export_web_cards import parse_fx, FX

def main():
    cards = load_cards()
    missing_sim = []
    parser_only = []
    explicit = []
    for name, c in sorted(cards.items()):
        if c.category not in ("Mana", "Weapon", "Artifact", "Support") or not c.is_player_card:
            continue
        if name not in EFFECTS:
            missing_sim.append(name)
        if name in FX:
            explicit.append(name)
        else:
            parser_only.append(name)
    print(f"player cards: {len(explicit) + len(parser_only)}")
    print(f"explicit FX overrides: {len(explicit)}")
    print(f"text-parser only: {len(parser_only)}")
    if missing_sim:
        print("MISSING sim handlers:", missing_sim)
    if parser_only:
        print("\nParser-only (simple cards — verify text matches):")
        for n in parser_only:
            c = cards[n]
            print(f"  {n}: {parse_fx(c)}")

if __name__ == "__main__":
    main()
