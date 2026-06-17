# Red Dragon — web feel-prototype (Phase 1)

A playable, animated browser prototype of the game, built on the validated `sim/` rules.
**This is the throwaway feel-prototype / interactive design spec** — the shippable game targets
**Godot 4** (see `../docs/GAME_PLAN.md`). Use this to feel the gameplay and UX.

## Run it
- **Easiest:** double-click `index.html` (runs from `file://`, no server — card data is embedded).
- **Or** serve the folder: `python -m http.server 8123 --directory web` → open http://localhost:8123

## What's implemented
- Setup → pick 2–4 heroes → a random top-tier party is rolled; you control all heroes (hotseat).
- Full battle loop: draw, play cards (mana/weapons/support), **equip artifacts into slots** (they
  fire every turn), **raise Affinity** (3 Mana, unlocks Tier-2 buys + Ultimates), **use class
  ability** (3 Mana), **buy from a market** (limited piles, reshuffle a category for 1 Mana, with
  affinity/affordability gating), end turn.
- Red Dragon: scaling HP, **telegraphed next card**, **Anger → Disaster** at players+2 (separate
  hidden disaster pile), **Level Up** on deck cycle (minions +HP, faster anger), minions that attack
  at end of round, the **Joker** extra turn at odd player counts.
- Damage auto-targets the lowest minion first (clears threats) else the boss; prevention tokens;
  win (Dragon slain) / lose (Village or all heroes fall).
- Animated: card plays, floating damage/heal numbers, HP/anger bar tweens, hit shakes.

## Scope / not yet (vs the full game in GAME_PLAN.md)
- Boss/minion/disaster deck uses a curated subset in `game.js` (full boss deck is in xlsx).
- Complex card text may parse generically; re-run `python tools/export_web_cards.py` after xlsx edits.
- No meta yet (shop/currency/unlocks/saves), no audio, placeholder CSS art.

## Extend
Player cards live in `cards_data.js` (generated from xlsx). Run `python tools/export_web_cards.py` from the repo root after card changes. Boss/disaster tables remain in `game.js`. The fx resolver mirrors `sim/effects.py` patterns.
