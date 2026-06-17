# From text sim to commercial video game — plan

## What we already have (the head start — we are NOT starting from 0)
- **A complete, balance-tested rules engine** in `sim/` (Python): turn loop, no-shuffle decks,
  slot/artifact engine, affinity, class abilities/ultimates, the Red Dragon boss (telegraph, Anger
  → Disaster, Level Up), minions, village, prevention, win/lose. Validated over tens of thousands
  of simulated games.
- **142 cards** with effects + costs in `Cards_Data.xlsx` (single source of truth) and a working
  effect registry (`sim/effects.py`).
- **Balance numbers** that are accepted/known (`SIM_STATE.md`) and a **playtested text game**
  (`play.py`) with market, choices, targeting.

So the *design, rules, and content are done and proven*. The remaining ~80% of "video game" work is
**presentation** (graphics, animation, audio, UX), **meta-systems** (shop, progression, unlocks,
saves), **content scaling** (more enemies/cards/runs), and **shipping** (stores).

## Tech decision (revised after critical review — see "Review incorporated" below)

### Recommended for the SHIPPING game: Godot 4 (GDScript)
- **Why (shipping risk, where solo devs die):** **Steamworks** (overlay, achievements, cloud saves,
  rich presence) is a documented, solved problem via **GodotSteam**; mobile export (iOS/Android) is
  first-class and this exact genre ships on Godot regularly. Free, MIT, no royalties; one project →
  Win/Mac/Linux/iOS/Android/Web; built-in Tween/AnimationPlayer/particles; editor-driven.
- **Cost is small:** re-porting the rules (~1,400 lines of pure logic) to GDScript is days, and the
  store/runtime integration it saves dwarfs that.

### Web stack (TypeScript + PixiJS + Vite) — use ONLY for the feel-prototype & browser demo
- Great for *fast iteration and an instantly-runnable prototype* (and a wishlist browser demo).
- **Shipping via Tauri+Capacitor is the immature path** for this game: Steamworks would be hand-rolled
  FFI with flaky WebView overlays, and a dense card board in a mobile WebView risks drag/scroll
  interception, tween jank on mid Android, and audio latency. If a browser demo is needed for
  wishlists, **export it from Godot** instead of maintaining a separate web ship target.

### Rejected
- **Unity** — heavier than needed for 2D; 2023 runtime-fee trust hit; only if you already know it.
- **Custom engine** — never.

**Verdict:** **commit to Godot 4 for the product.** Build the immediate playable prototype in **web**
(it's the fastest thing to put in your hands and doubles as the interactive design spec), but treat
it as throwaway/validation — the shippable codebase is Godot.

## Review incorporated (a senior game-tech architect critiqued this plan)
1. **Engine → Godot 4, not Tauri+Capacitor** (above). The runtime/store tax outweighs the rules-port cost.
2. **Kill the dual-codebase "Python oracle."** Two rule implementations drift the instant you tune a
   card (RNG seeding, draw order, auto-target tie-breaks are already fiddly). **Port the rules ONCE
   into the game engine, regenerate balance numbers there, and retire `sim/`.** For fast balance
   sweeps, run **headless instances of the shipping engine** — same code, zero drift. Keep the Python
   sweep scripts only as throwaway analysis, never as a CI parity gate. (Pyodide is worse than both.)
3. **Decide ART DIRECTION + budget NOW** — it's the single biggest cost and the real moat to a
   *sellable* product; engine choice and art direction are the two decisions expensive to reverse.
4. **Add a seeded-determinism contract + replay/undo** to the engine (for bug reports and "undo last
   card") from the start.

## Architecture (clean separation so content & balance stay data-driven)
```
data/        cards.json  (built from Cards_Data.xlsx) — single content source
engine/      pure TS rules port of sim/ (no rendering; deterministic; unit-tested vs Python sim)
game/        PixiJS presentation: scenes, board, cards, animations, input, audio
meta/        run/shop/progression/save (localStorage now; cloud later)
platform/    Tauri (desktop/Steam) + Capacitor (mobile) configs
```
- **Engine is headless and authoritative** — UI only renders state + sends intents (playCard,
  buy, equip, endTurn). This is what lets us cross-check against the Python sim and swap the
  renderer (or even reuse the engine in a Godot port) later.
- **Cards are data**, effects are small composable handlers (mirroring `sim/effects.py`), so adding
  cards/enemies = editing data + a handler, never touching the renderer.

## Roadmap (realistic: ~12–24 months solo to a polished store launch)
- **Phase 0 — DONE:** rules, 142 cards, balance, text game.
- **Phase 1 — Web feel-prototype (THIS PASS):** self-contained web app (no build step) — board (boss
  w/ HP + Anger + telegraphed next card, Village, heroes, hand, market, slots), animated card plays /
  damage numbers / HP-bar tweens / boss reveal, core loop for a representative card subset, hotseat,
  win/lose. Goal: *feel* the game; serves as the interactive design spec for the Godot build.
- **Decision gate:** confirm **Godot 4** + **art direction/budget** before writing shipping presentation code.
- **Phase 2 — Vertical slice (Godot):** port rules once to GDScript (retire `sim/`), all 142 cards
  from `data/cards.json`, full UI (drag-to-play, target/choice picking), polished animation + SFX,
  one full run. Externalize ALL strings for localization from day one. Seeded determinism + replay.
- **Phase 3 — Meta & content:** shop + currency, unlock/upgrade cards, multiple bosses & enemy sets,
  class unlocks, run/map structure, **save system with schema versioning + migration** (saves WILL
  break when card data changes — design migration now, not at ship).
- **Phase 4 — Polish & juice:** art pass, particles/screenshake/audio, tutorial/onboarding, settings,
  accessibility, **telemetry/analytics** (you cannot balance a live deckbuilder blind), in-house
  **content tooling** (card/encounter editor reading the data), balance sweeps via headless engine.
- **Phase 5 — Ship:** GodotSteam → **Steam** (achievements, cloud saves, store page, demo, wishlists);
  Godot mobile export → **App Store / Google Play**. Decide **monetization** (premium vs IAP) early —
  it affects store approval and architecture.

## Risks & mitigations (per review)
- **Biggest ship risk = art & "commercial polish," not the rules** (design is done). → Decide art
  direction + budget up front; prototype with placeholder art; line up asset packs/contractor.
- *Engine + art are the only hard-to-reverse decisions* → lock both before Phase 2.
- *Save/version breakage in a progression game* → schema version + migration from Phase 3.
- *Scope creep* → tight vertical slice first; content stays data-driven so it scales without re-eng.
- *iOS needs a Mac* (Xcode signing) — plan the hardware.
- *Localization/telemetry retrofits are expensive* → bake string-externalization + analytics in early.

## This pass delivers
A runnable, animated **web feel-prototype** in `web/` (open `web/index.html`) implementing the core
battle loop with graphics for a subset of cards — the interactive reference the Godot build follows.
Shipping engine = Godot 4 (your confirmation needed at the decision gate).

## Phase 2 foundation — BUILT (2026-06-17, v0.5.0)
The Godot 4 build foundation now exists in `godot/` (see `godot/README.md`):
- **Authoritative headless engine** ported to GDScript (`godot/engine/`): deterministic seeded RNG,
  data models, randomized tier market, affinity, abilities/ultimates, full boss/minion/disaster
  loop, win/lose, and a **data-driven** effect resolver (common card ops; a few exotic ops deferred
  and tallied at runtime).
- **Single content source** `godot/data/cards.json` generated from the xlsx via
  `tools/export_godot_data.py` (all 101 player cards + 40 boss-deck cards as structured ops).
- **Headless self-test** `godot/tests/run_headless.gd` (coverage + determinism + smoke + win-rate
  sample) — the GDScript analogue of `sim.validate`/`run_sim`.
- **Presentation scaffold built for the Hearthstone-tier target** (`godot/game/`): event bus,
  audio manager + Master→Music/SFX bus layout + procedural placeholder SFX
  (`tools/gen_placeholder_sfx.py`), `Juice.gd` motion primitives, an animated `CardView`, and an
  **engine-driven feel demo** (`Demo.tscn`: fanned animated hand, click-to-play with floating combat
  text + screenshake + tweened boss bar + SFX). Art direction + asset pipeline in
  `godot/assets/ART_DIRECTION.md`.

**Decided:** art/animation/audio target = **Hearthstone-comparable**; scaffold reflects it. Still
open: art budget/sourcing (see ART_DIRECTION) and confirming the per-card art pipeline before
scaling to all 142 cards.

### Verified & expanded (v0.5.1–v0.6.6, Godot 4.3 installed)
The engine + slice are **run and verified on Godot 4.3** (one command: `pwsh tools/run_godot_tests.ps1`):
- **Engine:** all effect ops implemented (zero deferred); **68 behavioural assertions** +
  smoke/determinism (`tests/run_headless.gd`, `tests/test_effects.gd`); engine combo ranking
  (`tests/rank_combos.gd`); **schema-versioned save/restore** (RNG-exact, JSON-roundtrip deterministic).
- **Vertical-slice battle:** menu → N-hero battle, real co-op **turn loop** (mana economy, market
  drawer, affinity/ability/slot buys, End Turn → AI allies + boss phase), **drag-to-play** cards,
  on-board minions + Anger meter, **Undo Turn** (save/restore-backed), win/lose overlay, procedural SFX.

**Next (in priority order):** target/choice pickers (which hero to heal, which artifact to refire,
tutor picks — needs an async intent/choice layer); art pass (card frames + Red Dragon, per
ART_DIRECTION) and audio; then meta (Phase 3: shop/progression + save migration); localization +
telemetry; Steam/mobile export (Phase 5).
