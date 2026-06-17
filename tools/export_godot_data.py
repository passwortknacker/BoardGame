"""Export Cards_Data.xlsx -> godot/data/cards.json: the single content source for the Godot build.

Emits ALL cards as data:
  - player cards: cat/cost/tier/cls/text + a structured `fx` op list (reuses the web exporter's
    parse_fx so sim, web, and Godot share one effect vocabulary).
  - boss / minion / disaster cards: a structured `bfx` op list mirroring sim/effects.py exactly
    (so the Godot boss engine resolves them from data, not hand-written handlers).
  - starter decks per class, and the balance config defaults.

Run:  python tools/export_godot_data.py
Re-run after any xlsx change. The Godot engine (godot/engine/CardDB.gd) loads the JSON directly.
"""
from __future__ import annotations
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # repo root on path
sys.path.insert(0, os.path.join(ROOT, "tools"))  # reuse the web exporter's fx vocabulary
from sim.cards import load_cards, TIER2
from sim.game import build_starter, CLASSES
from export_web_cards import parse_fx

OUT = os.path.join(ROOT, "godot", "data", "cards.json")

# Boss / Minion / Disaster effects as structured ops — a faithful 1:1 of sim/effects.py.
# Ops (resolved in godot/engine/Boss.gd):
#   {"vdmg": n}                                  village takes n
#   {"vdmgScaleMinions": {"b","per"}}            village takes b + per*minionCount
#   {"pdmg": {"amt", "who", "k"?}}               heroes take amt; who = rand|all|highHp|lowHp|highAff|lowAff
#                                                amt may be "livingHalf" (max(1, living//2))
#   {"manaDmg": {"who":"highMana"}}              target takes (its mana-cards-in-hand) damage
#   {"discard": {"who":"rand","n","k"}}          k random heroes each discard n
#   {"discardCollective": n | "living"}          n discards spread round-robin across living heroes
#   {"discardEach": n}                           every living hero discards n
#   {"drawAll": n}                               every living hero draws n
#   {"loseAff": {"who":"rand"|"all","k"?}}       lose 1 Affinity
#   {"unequip": {"who":"rand"|"all","k"?}}       move 1 equipped artifact to discard
#   {"anger": n} / {"noBuy": true}
#   {"minionsAttack": true}                      every minion resolves its attack again
#   {"reviveMinion": {"n"}}                       revive newest n minions from boss discard
#   {"tacticalRetreat": true}                     revive (2 if a field minion retreats, else 1)
BFX = {
    # ---- BOSS ----
    "Absorb Mana":       [{"loseAff": {"who": "rand", "k": 2}}],
    "Claw Swipe":        [{"vdmg": 5}],
    "Tail Attack":       [{"vdmg": 6}],
    "Cutting Wind":      [{"pdmg": {"amt": 2, "who": "rand", "k": 2}}, {"discard": {"who": "rand", "n": 2, "k": 1}}],
    "Demand Tribute":    [{"discardCollective": 5}, {"vdmg": 3}],
    "Fire Breath":       [{"pdmg": {"amt": 2, "who": "all"}}, {"discardCollective": 2}],
    "Flammable Tools":   [{"discardCollective": 2}, {"drawAll": 1}, {"vdmg": 3}],
    "Mana Dominance":    [{"pdmg": {"amt": 5, "who": "highAff"}}],
    "Mana Ignition":     [{"manaDmg": {"who": "highMana"}}],
    "Minion Onslaught":  [{"vdmgScaleMinions": {"b": 1, "per": 2}}],
    "Predatory Strike":  [{"pdmg": {"amt": 5, "who": "highHp"}}],
    "Rising Hostility":  [{"vdmg": 3}, {"anger": 2}],
    "Scorching Gaze":    [{"pdmg": {"amt": 3, "who": "rand", "k": 1}}, {"discard": {"who": "rand", "n": 1, "k": 2}}],
    "Shared Sacrifice":  [{"discardCollective": "living"}, {"vdmg": 3}],
    "Threatening Glare": [{"pdmg": {"amt": 2, "who": "rand", "k": 3}}, {"discard": {"who": "rand", "n": 1, "k": 2}}],
    "Bully the Weak":    [{"pdmg": {"amt": 5, "who": "lowAff"}}],
    "Material Damage":   [{"unequip": {"who": "rand", "k": 2}}],
    "Wide Swing":        [{"pdmg": {"amt": 2, "who": "all"}}],
    # ---- MINIONS (per-round attack) ----
    "Dragon Cultist":    [{"pdmg": {"amt": 3, "who": "rand", "k": 1}}, {"loseAff": {"who": "rand", "k": 1}}],
    "Dragon Lancer":     [{"manaDmg": {"who": "highMana"}}],
    "Fire Breather":     [{"vdmg": 5}],
    "Kobold Archer":     [{"pdmg": {"amt": 2, "who": "rand", "k": 1}}, {"vdmg": 2}],
    "Kobold Defender":   [{"vdmg": 1}],
    "Kobold Horde":      [{"vdmg": 5}, {"discard": {"who": "rand", "n": 1, "k": 1}}],
    "Kobold Marauder":   [{"vdmg": 4}],
    "Kobold Shaman":     [{"pdmg": {"amt": "livingHalf", "who": "rand", "k": 1}}, {"loseAff": {"who": "rand", "k": 1}}],
    "Kobold Thief":      [{"discardCollective": 3}],
    "Wyrm":              [{"pdmg": {"amt": 5, "who": "highHp"}}],
    "Wyrmling":          [{"pdmg": {"amt": 4, "who": "rand", "k": 1}}, {"discard": {"who": "rand", "n": 1, "k": 1}}],
    "Kobold":            [{"vdmg": 3}, {"discard": {"who": "rand", "n": 1, "k": 1}}],
    # ---- DISASTERS ----
    "Power Anomaly":     [{"loseAff": {"who": "all"}}],
    "Fiery Explosion":   [{"pdmg": {"amt": 3, "who": "all"}}, {"vdmg": 3}],
    "Gear Purge":        [{"unequip": {"who": "all"}}],
    "Minion Frenzy":     [{"minionsAttack": True}],
    "Reawakening":       [{"reviveMinion": {"n": 1}}],
    "Supply Depletion":  [{"discardEach": 2}],
    "Trade Block":       [{"noBuy": True}],
    "Unnatural Disaster":[{"vdmg": 8}],
    "Critical Hit":      [{"pdmg": {"amt": 5, "who": "lowHp"}}],
    "Tactical Retreat":  [{"tacticalRetreat": True}],
}

CONFIG = {
    "boss_base": 40, "boss_slope": 10, "village_base": 20, "village_slope": 10,
    "player_hp": 10, "boss_n": 12, "minion_n": 7, "disaster_n": 6,
    "slot_cost": [1, 2, 3, 4, 5], "charge_turns": 1, "hand_size": 5, "round_cap": 16,
    # randomized 15-slot tier market (mirrors sim + web)
    "market_spec": [
        ["Mana", "Moderate"], ["Mana", "Moderate"], ["Mana", "Greater"], ["Mana", "Greater"],
        ["Weapon", "Light"], ["Weapon", "Light"], ["Weapon", "Heavy"], ["Weapon", "Heavy"],
        ["Artifact", "Ancient"], ["Artifact", "Ancient"], ["Artifact", "Common"], ["Artifact", "Common"],
        ["Support", None], ["Support", None], ["Support", None],
    ],
    "tier2": sorted(TIER2),
}


def main():
    cards = load_cards()
    players, boss = {}, {}
    for c in cards.values():
        if c.category in ("Mana", "Weapon", "Artifact", "Support") and c.is_player_card:
            tier = c.tier if c.tier in TIER2 or c.tier in ("Moderate", "Light", "Common") else (c.tier or None)
            players[c.name] = {
                "cat": c.category, "cost": c.cost or 0, "tier": tier,
                "cls": c.cls, "text": c.text, "fx": parse_fx(c),
            }
        elif c.category in ("Boss", "Minion", "Disaster"):
            entry = {"cat": c.category, "text": c.text, "bfx": BFX.get(c.name, [])}
            if c.category == "Minion":
                entry["hp"] = c.minion_hp or 0
            boss[c.name] = entry

    starters = {cls: [c.name for c in build_starter(cards, cls)] for cls in CLASSES}
    data = {
        "version": "0.5.0-godot-foundation",
        "config": CONFIG,
        "classes": CLASSES,
        "players": players,
        "boss": boss,
        "starters": starters,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    missing = [n for n, e in boss.items() if not e["bfx"]]
    print(f"wrote {OUT}")
    print(f"  player cards: {len(players)}  |  boss-deck cards: {len(boss)}  |  classes: {len(starters)}")
    if missing:
        print(f"  WARNING: boss-deck cards with no bfx encoding: {missing}")
    else:
        print("  all boss/minion/disaster cards have a structured effect encoding")


if __name__ == "__main__":
    main()
