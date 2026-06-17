"""Coverage + sanity checks. Run: python -m sim.validate"""
from __future__ import annotations
from .cards import load_cards
from .effects import EFFECTS
from .game import play_game

NON_EFFECT = {"Village"}   # the Village is an ability, not a played card


def coverage():
    cards = load_cards()
    missing = [n for n, c in cards.items() if n not in NON_EFFECT and n not in EFFECTS]
    extra = [n for n in EFFECTS if n not in cards]
    print(f"coverage: {len(cards) - len(missing) - len(NON_EFFECT)}/{len(cards) - len(NON_EFFECT)} "
          f"player+boss cards have handlers")
    if missing:
        print("  MISSING handlers:", missing)
    if extra:
        print("  registry names not in xlsx:", extra)
    return not missing


def smoke():
    """Run a spread of games across player counts/strategies; assert no exceptions."""
    cards = load_cards()
    profiles = ["mana_greedy", "affinity_rush", "weapons", "caster", "balanced"]
    n = 0
    for P in (2, 3, 4):
        for s in profiles:
            for seed in range(20):
                play_game(cards, P=P, strategies=[s] * P, seed=seed)
                n += 1
    print(f"smoke: {n} games ran with no exceptions")
    return True


if __name__ == "__main__":
    ok = coverage()
    smoke()
    print("OK" if ok else "INCOMPLETE COVERAGE")
