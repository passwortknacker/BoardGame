"""Class abilities + ultimates (FINAL table, HANDOVER.md).

Normal usable from start; Ultimate when the acting player is at Affinity 3.
Cost 3 Mana when actively used (AI deducts); free when triggered by a card.
The Village ability uses the *triggering* player's Affinity for its ultimate.
"""
from __future__ import annotations

from .engine import PLAYER_HP

ABILITY_COST = 3


def use_ability(g, p, x, free=False):
    ult = p.ultimate
    cls = p.cls
    if cls == "Ranger":
        g.heal_village(3 if ult else 2); g.attack_target(p, 3 if ult else 2, prefer_minion=False)
    elif cls == "Paladin":
        tgt = _lowest(g, p); g.heal_player(tgt, 3 if ult else 2); g.attack_target(p, 3 if ult else 2, prefer_minion=False)
    elif cls == "Druid":
        g.heal_player(_lowest(g, p), 3 if ult else 2); g.heal_village(3 if ult else 2)
    elif cls == "Cleric":
        if ult:
            for q in _n_lowest(g, 2): g.heal_player(q, 4)
        else:
            g.heal_player(_lowest(g, p), 4)
    elif cls == "Wizard":
        _refire_artifacts(g, p, x, 2 if ult else 1)
    elif cls == "Weaponmaster":
        _play_weapons_from_discard(g, p, x, 2 if ult else 1)
    elif cls == "Enchanter":
        if ult: _tutor_supply(g, p, "Artifact", 6)
        else: _tutor_hand(g, p, "Artifact", 4)
    elif cls == "Blacksmith":
        if ult: _tutor_supply(g, p, "Weapon", 6)
        else: _from_discard(g, p, "Weapon")
    elif cls == "Bard":
        if ult: g.heal_player(_lowest(g, p), 3)
        _draw(g, p, 1)
    g.stats[f"ability:{cls}"] += 1


def _lowest(g, p):
    return g.lowest_heal_target()

def _n_lowest(g, n):
    targets = sorted((q for q in g.players if q.hp < PLAYER_HP), key=lambda q: q.hp)
    return targets[:n] if targets else sorted(g.players, key=lambda q: q.hp)[:n]

def _draw(g, p, n):
    for _ in range(n):
        c = p.draw_one()
        if c is None: break
        p.hand.append(c)

def _from_discard(g, p, cat):
    from .effects import from_discard
    from_discard(g, p, cat)   # human picks which (CLI); sims auto-pick first

def _tutor_hand(g, p, cat, maxcost):
    from .effects import tutor_to_hand
    tutor_to_hand(g, p, cat, maxcost)

def _tutor_supply(g, p, cat, maxcost):
    opts = g.supply_choices(p, maxcost, cat)
    if opts:
        p.discard.append(max(opts, key=lambda c: (c.cost or 0)))

def _play_weapons_from_discard(g, p, x, n):
    from .effects import EFFECTS
    played = 0
    for _ in range(n):
        c = next((c for c in p.discard if c.category == "Weapon"), None)
        if c is None:
            break
        p.discard.remove(c); x.weapons_played += 1; EFFECTS[c.name](g, p, x); played += 1
    return played

def _refire_artifacts(g, p, x, n):
    from .effects import refire
    refire(g, p, x, n)   # human picks which (CLI); sims auto-pick
