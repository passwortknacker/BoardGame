"""Export card data from Cards_Data.xlsx to game/cards_data.js for the web prototype.

Run:  python export_web_cards.py
Regenerate after xlsx changes. Fx ops mirror sim/effects.py where possible.
"""
from __future__ import annotations
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # repo root on path
from sim.cards import load_cards, TIER2
from sim.game import build_starter, CLASSES

OUT = os.path.join(ROOT, "web", "cards_data.js")

# Explicit fx overrides for cards that text parsing can't capture.
FX = {
    "Mana Crystal": [{"mana": 1}],
    "Arcane Secrets": [{"mana": 1}, {"scaleMana": {"b": 0, "per": 1, "stat": "otherMana"}}],
    "Multiplier Maul": [{"dmgWeapons": {"per": 2, "aff": 1}}],
    "Mana Cannon": [{"dmgAff": {"b": 5, "per": 2}}],
    "Artificer's Fury": [{"dmgArt": {"b": 1, "per": 2}}],
    "Affinity Beacon": [{"dmgAff": {"b": 2, "per": 2, "min": 4, "max": 8}}],
    "Rupture Relic": [{"dmgArt": {"b": 0, "per": 2}}],
    "Slayer's Relic": [{"dmg": 2, "slayer": True}],
    "Blood Ritual": [{"bloodRitual": True}],
    "Natural Selection": [{"draw": 2}, {"discard": 1}],
    "Aegis Ward": [{"prevent": 5, "who": "choose"}],
    "Well Prepared": [{"prevent": 6, "who": "choose"}],
    "Helping Hand": [{"helpingHand": True}],
    "Ring of Arms": [{"dmg": 2}, {"fromDiscard": {"cat": "Weapon"}}],
    "Relic Reclaimer": [{"dmg": 2}, {"tutorHand": {"cat": "Artifact", "max": 5}}],
    "Improvised Strike": [{"fromDiscard": {"cat": "Weapon"}}],
    "Cycle of Life": [{"fromDiscard": {"cat": "Support"}}],
    "Arsenal Enforcer": [{"dmg": 2}, {"fromDiscard": {"cat": "Weapon"}}],
    "Magic Veil": [{"refire": 1}],
    "Arcane Retrieval": [{"refire": 1}],
    "Encourage": [{"encourage": True}],
    "Blessing of Faith": [{"heal": 2, "who": "lowest"}, {"heal": 2, "who": "lowest2"}],
    "Make A Wish": [{"tutor": {"cat": None, "max": 10}}],
  "Artifact Hexcore": [{"mana": 2}, {"optionalTutor": {"cat": "Artifact", "max": 5, "self": True}}],
  "Support Hexcore": [{"mana": 2}, {"optionalTutor": {"cat": "Support", "max": 5, "self": True}}],
  "Weapon Hexcore": [{"mana": 2}, {"optionalTutor": {"cat": "Weapon", "max": 5, "self": True}}],
  "Swapsteel Dirk": [{"dmg": 2}, {"optionalTutor": {"cat": "Weapon", "max": 5, "self": True}}],
  "Bounty Bringer": [{"dmg": 3}, {"optionalTutor": {"cat": None, "max": 8, "self": True}}],
    "Mystic Offering": [{"dmg": 2}, {"optionalTutor": {"cat": "Artifact", "max": 5, "self": True}}],
    "Sacrificial Scepter": [{"dmg": 2}, {"optionalTutor": {"cat": None, "max": 8, "self": True}}],
    "Timeless Talisman": [{"postponeBoss": True}],
    "Armed Militia": [{"villageStrike": 5}],
    "Wandering Wisp": [{"dmg": 2}, {"passWisp": True}],
    "Mana Resonator": [{"scaleMana": {"b": 1, "per": 1, "stat": "artifactsEq", "step": [1, 3, 5]}}],
    "Drain the Horde": [{"mana": 1}, {"scaleMana": {"b": 0, "per": 1, "stat": "minions"}}],
    "Attuned Elixir": [{"mana": 1}, {"slot": 1}],
    "Mana Conduit": [{"mana": 2}, {"affinity": 1}],
    "Wild Magic Flux": [{"mana": 3}, {"reshuffleMarket": True}],
    # --- cards text parser misses (mirror sim/effects.py) ---
    "Mana Converter": [{"mana": 1}, {"optionalDestroy": {"cat": "Mana"}}],
    "Spellshard": [{"dmg": 2}, {"tryAbility": True}],
    "Ethereal Catalyst": [{"mana": 2}, {"tryAbility": True}],
    "Celestial Slicer": [{"dmgOrDraw": {"dmg": 7, "drawTotal": 3, "maxPerPlayer": 2}}],
    "Composter": [{"destroyDraw": True}],
    "Worthy Sacrifice": [{"destroyDraw": True}],
    "Secret Technique": [{"secretTechnique": True}],
    "Pocket Arsenal": [{"replayWeapon": True}],
    "Call of Nature": [{"mana": 1}, {"scaleMana": {"b": 0, "per": 1, "stat": "supportHand"}}],
    "Aid the Weak": [{"mana": 1}, {"scaleMana": {"b": 0, "stat": "missingHp", "step": [1, 4, 7]}}],
    "Bardic Inspiration": [{"mana": 1}, {"scaleMana": {"b": 0, "stat": "anger", "step": [1, 3, 5]}}],
    "Blacksmith's Pride": [{"mana": 1}, {"scaleMana": {"b": 0, "stat": "weaponsHand", "step": [1, 3, 4]}}],
    "Bladesurge Stone": [{"mana": 1}, {"scaleMana": {"b": 0, "stat": "weaponsHand", "step": [1, 3, 5]}}],
    "Divine Favor": [{"divineFavor": True}],
    "Martial Focus": [{"mana": 1}, {"scaleMana": {"b": 0, "stat": "weaponsDiscard", "step": [1, 3, 5]}}],
    "Mana Resonance": [{"mana": 1}, {"scaleMana": {"b": 0, "stat": "maxArts", "step": [1, 3, 5]}}],
    "Spellblade Energon": [{"mana": 1}, {"bonusIf": {"stat": "weaponsHand", "min": 1, "add": 1}}],
    "Source Dynamo": [{"mana": 1}, {"bonusIf": {"stat": "artifactsEq", "min": 1, "add": 1}}],
    "Arcane Chalice": [{"dmg": 3}, {"vhealOrHeal": True}],
    "Bloodfire Charm": [{"bloodfire": True}],
    "Eternal Charm": [{"dmg": 2}, {"refire": 1}],
    "Mystic Purifier": [{"dmg": 2}, {"optionalDestroy": {}}],
    "Power Cube": [{"dmgScaleArts": {"min": 5}}],
    "Sustaining Sigil": [{"dmg": 2}, {"fromDiscard": {"cat": "Mana"}}],
    "Fate's Arbiter": [{"fateArbiter": True}],
    "Genesis Edge": [{"genesisEdge": True}],
    "Mace of Renewal": [{"dmg": 3}, {"draw": 1}],
    "Pacifier": [{"pacifier": True}],
    "Purification Spear": [{"dmg": 4}, {"optionalDestroy": {}}],
    "Townsaver": [{"dmg": 3}, {"triggerVillage": True}],
    "Tinblade": [{"dmg": 2}, {"optionalSelfDestroy": True}],
    # parser-only gaps (must match sim/effects.py)
    "Aegis Elixir": [{"mana": 2}, {"vheal": 2}],
    "Alliance Amulet": [{"dmgSupport": {"b": 1, "per": 2}}],
    "Arcane Tome": [{"dmg": 1}, {"draw": 1}],
    "Collateral Carnage": [{"dmg": 9}, {"villageReduce": 1}],
    "Crimson Scythe": [{"dmg": 8}, {"selfdmg": 1}],
    "Druidic Tonic": [{"mana": 2}, {"heal": 2, "who": "self"}],
    "Elemental Surge": [{"mana": 1}, {"dmg": 1}],
    "Mystic Infusion": [{"mana": 2}, {"heal": 2, "who": "self"}],
    "Mystical Arcanum": [{"mana": 2}, {"draw": 1}],
    "Sorcerous Affinity": [{"mana": 1}, {"scaleMana": {"b": 0, "per": 1, "stat": "aff"}}],
    "Vital Essence": [{"mana": 1}, {"heal": 1, "who": "self"}],
    "Lifedrain Blade": [{"dmg": 2}, {"heal": 2, "who": "self"}],
}


def parse_fx(card) -> list:
    if card.name in FX:
        return FX[card.name]
    t = card.text
    fx: list = []
    m = re.search(r"\+(\d+)\s*Mana", t)
    if m:
        fx.append({"mana": int(m.group(1))})
    if "Affinity Level by 1" in t or "Affinity Level by1" in t:
        fx.append({"affinity": 1})
    if "Artifact slot" in t or "Charge" in t and "slot" in t.lower():
        fx.append({"slot": 1})
    dm = re.search(r"(\d+)\s*DMG", t)
    if dm:
        n = int(dm.group(1))
        if "every enemy" in t.lower() or "all enemies" in t.lower():
            fx.append({"aoe": n})
        elif card.category in ("Weapon", "Support") or card.cost == 0:
            fx.append({"dmg": n})
        elif card.category == "Artifact":
            fx.append({"dmg": n})
    if "draw" in t.lower() and "Draw" in t:
        dm2 = re.search(r"[Dd]raw\s*(\d+)", t)
        if dm2:
            fx.append({"draw": int(dm2.group(1))})
    if "Village HP" in t or "+2 Village" in t:
        vm = re.search(r"(\d+)\s*Village HP", t) or re.search(r"\+(\d+)\s*Village", t)
        if vm:
            fx.append({"vheal": int(vm.group(1))})
    if "heals" in t.lower() or "Heal" in t:
        hm = re.search(r"heals?\s*(\d+)", t, re.I)
        if hm:
            fx.append({"heal": int(hm.group(1)), "who": "lowest"})
    if "Prevent" in t:
        pm = re.search(r"(\d+)\s*damage", t, re.I) or re.search(r"Prevent up to (\d+)", t)
        if pm:
            who = "choose" if "hero or Village" in t or "Village or" in t else "village"
            fx.append({"prevent": int(pm.group(1)), "who": who})
    if "Every Player draws" in t or "All Players draw" in t or "Every hero draws" in t:
        fx.append({"drawAll": 1})
    if not fx and card.category == "Weapon":
        fx.append({"dmg": 1})
    if not fx and card.category == "Mana":
        fx.append({"mana": 1})
    return fx


def main():
    cards = load_cards()
    out: dict = {}
    for c in cards.values():
        if c.category not in ("Mana", "Weapon", "Artifact", "Support"):
            continue
        if not c.is_player_card:
            continue
        tier = c.tier if c.tier in TIER2 or c.tier in ("Moderate", "Light", "Common") else (c.tier or None)
        out[c.name] = {
            "cat": c.category,
            "cost": c.cost if c.cost is not None else 0,
            "tier": tier,
            "cls": c.cls,
            "text": c.text,
            "fx": parse_fx(c),
        }
    js = "// AUTO-GENERATED by export_web_cards.py — do not edit by hand\n"
    js += "const CARDS_DATA=" + json.dumps(out, indent=2) + ";\n"
    starters = {cls: [c.name for c in build_starter(cards, cls)] for cls in CLASSES}
    js += "const STARTER_DECKS=" + json.dumps(starters, indent=2) + ";\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(js)
    buyable = sum(1 for v in out.values() if v["cls"] == "All" and v["cost"] > 0)
    print(f"wrote {OUT}: {len(out)} player cards ({buyable} All-class buyable)")


if __name__ == "__main__":
    main()
