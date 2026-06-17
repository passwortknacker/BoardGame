# Red Dragon — Godot 4 build (shipping target)

This is the **foundation** of the commercial game (Phase 2 of [`../docs/GAME_PLAN.md`](../docs/GAME_PLAN.md)):
a **headless, deterministic, data-driven rules engine** in GDScript, ported from the validated
Python sim (`../sim/`). Presentation (the real board UI) comes next — this pass delivers the engine
the UI will render.

## Requirements
Godot **4.3+** (standard, GDScript — no C#/.NET needed).

## Run it
- **Editor:** open `godot/project.godot` in Godot and press Play. The main scene (`game/Demo.tscn`)
  is an interactive **vertical-slice demo** driven by the real engine — a full co-op turn:
  - You control hero 0 (Cleric); play cards from a fanned, animated hand (hover-lift, play-fly,
    floating combat numbers, screenshake, SFX).
  - **Mana is a real resource** — play Mana cards to fill the pool, spend it via the **Market**
    drawer (buy cards, slots refill), **Raise Affinity**, **Use Ability**, or **Buy Slot**.
  - **Drag a card upward to play it** (Hearthstone-style), or click it; drop low to cancel.
  - Equip Artifacts into slots (they fire at the start of your next turn).
  - **End Turn** → the AI ally (Paladin) takes its turn, then the Red Dragon responds (boss card +
    Anger/Disaster + minion attacks), with a tweened boss HP bar + telegraph and a running log.

  It's the presentation reference the full board UI grows from (target/choice pickers, multi-hotseat,
  and the art/audio pass are next).
- **Headless tests** (the analogue of `python -m sim.validate` + `run_sim.py`):
  ```
  godot --headless --path godot --import                       # first run only: builds the class cache
  godot --headless --path godot --script res://tests/run_headless.gd    # smoke + determinism + balance
  godot --headless --path godot --script res://tests/test_effects.gd    # behavioural assertions
  godot --headless --path godot --script res://tests/rank_combos.gd     # rank class comps (engine balance)
  ```
  **Verified on Godot 4.3** — `run_headless` passes (coverage, determinism, 200 smoke games, **all
  effect ops implemented**; role-comp win rates ≈ 2p 20% / 3p 56% / 4p 45%, consistent with the
  Python sim's randomized market). `test_effects` passes 40 behavioural assertions (combat,
  targeting, prevention, discard cap, market, abilities, boss ops, deferred ops, win/lose).

## Presentation target: Hearthstone-tier
The finished game targets Hearthstone-comparable graphics, animation, and sound. The scaffold is
built for that from the start — see [`assets/ART_DIRECTION.md`](assets/ART_DIRECTION.md):
- `game/Events.gd` — global signal bus; the engine stays pure, juice/audio just listen.
- `game/AudioManager.gd` + `assets/audio/default_bus_layout.tres` — pooled SFX on a Master→Music/SFX
  bus layout (placeholder SFX via `python tools/gen_placeholder_sfx.py`).
- `game/Juice.gd` — motion primitives (hover, pop, shake, floating text, fly-to).
- `game/cards/CardView.gd` — procedural card frame (swap in real art by binding textures later).

## Architecture (clean separation — content & balance stay data-driven)
```
godot/
  data/cards.json        ← single content source (generated; do NOT hand-edit)
  engine/                ← AUTHORITATIVE headless rules (no rendering, deterministic)
    CardDB.gd            ← loads cards.json into static lookups (name -> data)
    RNG.gd               ← seeded RNG; the determinism contract (seed -> identical game)
    Game.gd              ← state + models (Player/Minion/Equip/Ctx), market, combat, turn/round loop
    Effects.gd           ← data-driven fx resolver (player cards) + bfx resolver (boss/minion/disaster)
    Abilities.gd         ← class abilities + ultimates
    AI.gd                ← heuristic policy (drives headless sims; "suggested move" baseline for UI)
  game/                  ← PRESENTATION (renders engine state, sends intents)
    Demo.tscn/.gd        ← interactive feel demo (real engine + animation + SFX)
    Events.gd            ← global signal bus (autoload) — decouples juice from rules
    AudioManager.gd      ← pooled SFX / music (autoload)
    Juice.gd             ← motion primitives (hover, pop, shake, float-text, fly-to)
    cards/CardView.gd    ← animated card visual (procedural frame; art-ready)
  assets/                ← art/ (folders ready) + audio/ (bus layout + placeholder SFX)
  tests/run_headless.gd  ← headless self-test + balance sample
```
- **Engine is headless and authoritative.** The UI will only render state and send intents
  (play/buy/equip/endTurn). Balance sweeps run many headless `Game` instances — same code, zero drift.
- **Cards are data.** Adding/changing a card = edit `Cards_Data.xlsx` → regenerate `cards.json`,
  never touch engine code.

## Regenerating data after a card change
From the repo root:
```
python tools/export_godot_data.py     # Cards_Data.xlsx -> godot/data/cards.json
```
`cards.json` carries, per card: category/cost/tier/class/text plus a structured **fx** op list
(player cards) or **bfx** op list (boss/minion/disaster). The op vocabulary is documented at the top
of `tools/export_godot_data.py`; `engine/Effects.gd` interprets it.

## Foundation scope (what's here vs. the vertical slice)
**Implemented:** deterministic engine, all 9 classes + starters, randomized 15-slot tier market,
affinity, abilities/ultimates, the full Red Dragon boss/minion/disaster loop, win/lose, and the
common card-effect ops (mana, damage, AoE, heal, village heal, prevention, draw, affinity, slots,
mana-scaling, dmg-scaling, discard retrieval with the 1×/turn cap, tutors, refire).

**All player + boss effect ops are now implemented** (bloodRitual, divineFavor, triggerVillage,
villageReduce, optional destroy, pass-wisp, fate/genesis, pacifier, etc.) — `run_headless` reports
zero approximated ops. `g.warnings` remains as a guard for any future unmapped op.

**Presentation scaffold (this pass):** event bus, audio manager + bus layout + placeholder SFX,
juice helpers, an animated `CardView`, and an engine-driven feel demo. Real art/audio, the full
board UI, drag-to-play & target/choice pickers, meta (shop/progression/saves), localization, and
Steam/mobile export are still ahead — see `assets/ART_DIRECTION.md` and `../docs/GAME_PLAN.md`
Phases 2–5.

## Engine balance snapshot (30 games/combo, `rank_combos.gd`)
Top comps the **Godot engine** itself produces (Cleric is near-mandatory; 2p is hardest — matching
the design and the Python sim's qualitative picture):
- **2p:** Cleric+Wizard ~67% · Ranger+Cleric ~57% (all-combo avg ~22%)
- **3p:** Cleric+Wizard+Bard ~97% · Ranger+Cleric+Wizard ~97% (avg ~51%)
- **4p:** Ranger+Cleric+Wizard+Bard ~100% (avg ~46%)

## Parity note
The Python `sim/` remains the historical reference. Per the game plan, the Godot engine is now the
go-forward authority for the product; regenerate balance numbers here rather than parity-gating
against Python (RNG differs, so exact win rates differ — the *rules* match).
