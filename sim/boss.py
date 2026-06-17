"""Red Dragon boss engine — modeled to design_plan.md + the Red Dragon card.

- Boss deck = Boss + Minion cards only; one card per boss turn; next card telegraphed.
- Disasters are a SEPARATE hidden pile, drawn only when Anger triggers.
- End of each boss turn: Anger += anger_step. If Anger >= players + 2: reset Anger to 1 and
  activate (draw + resolve) a Disaster.
- Level Up: when the boss deck is used up it reshuffles; each cycle -> boss_level += 1, so new
  minions enter with +2 HP per level and Anger rises +1 faster per boss turn (anger_step += 1).
- Minions enter the field on flip and attack at END OF ROUND (not on the boss turn).
"""
from __future__ import annotations
import random
from .engine import Game, Minion
from .effects import EFFECTS


def build_boss_deck(cards, rng: random.Random, n_boss=12, n_minion=8) -> list:
    boss = [c for c in cards.values() if c.category == "Boss"]
    minion = [c for c in cards.values() if c.category == "Minion"]
    deck = (rng.sample(boss, min(n_boss, len(boss)))
            + rng.sample(minion, min(n_minion, len(minion))))
    rng.shuffle(deck)
    return deck


def build_disaster_pile(cards, rng: random.Random, n=6) -> list:
    disasters = [c for c in cards.values() if c.category == "Disaster"]
    pile = rng.sample(disasters, min(n, len(disasters)))
    rng.shuffle(pile)
    return pile


def _flip(g: Game):
    if not g.boss_deck:
        # Level Up: the boss deck cycled
        g.boss_level += 1
        g.anger_step += 1
        g.boss_deck = g.boss_discard
        g.boss_discard = []
        g.rng.shuffle(g.boss_deck)
        g.log(f"LEVEL UP {g.boss_level}: minions +{2*g.boss_level} HP, anger +{g.anger_step}/turn")
    return g.boss_deck.pop(0) if g.boss_deck else None


def _trigger_disaster(g: Game):
    if not g.disaster_pile:
        if not g.disaster_discard:
            return
        g.disaster_pile = g.disaster_discard
        g.disaster_discard = []
        g.rng.shuffle(g.disaster_pile)
    card = g.disaster_pile.pop(0)
    g.log(f"  ANGER -> DISASTER: {card.name}")
    EFFECTS[card.name](g, None, None)
    g.disaster_discard.append(card)


def boss_turn(g: Game):
    # Timeless Talisman: shuffle the telegraphed card back, resolve the following one.
    if getattr(g, "_postpone_boss", False) and g.boss_deck:
        g._postpone_boss = False
        nxt = g.boss_deck.pop(0)
        g.boss_deck.insert(g.rng.randrange(1, len(g.boss_deck) + 1) if g.boss_deck else 0, nxt)
        g.log("Talisman postpones the next Boss card")

    card = _flip(g)
    if card is None:
        return
    g.log(f"BOSS flips {card.category}:{card.name}")
    if card.category == "Minion":
        hp = card.minion_hp + 2 * g.boss_level     # Level Up: minions enter with +2 HP per level
        g.minions.append(Minion(card, hp))
        g.log(f"  minion {card.name} enters (hp {hp})")
    else:
        EFFECTS[card.name](g, None, None)
        g.boss_discard.append(card)

    # End of boss turn: Anger, and the P+2 -> Disaster trigger
    g.anger += g.anger_step
    if g.anger >= len(g.players) + 2:
        g.anger = 1
        _trigger_disaster(g)


def minions_attack(g: Game):
    for m in list(g.minions):
        if g.result:
            break
        EFFECTS[m.card.name](g, None, None)
        g.check_end()
