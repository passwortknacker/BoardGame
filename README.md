# Red Dragon — Marvin's Co-op Deckbuilding Boss-Battler

**Version: v0.5.0** — *prototype / pre-alpha* (2026-06-17)

A cooperative deckbuilding boss-battler: 2–4 heroes plus a shared **Village** fight the **Red
Dragon**. Built on the Aeon's End → Astro Knights chassis (randomized turn order, supply market,
artifact engine). The rules are **designed, simulated, and playtestable today**; the shippable
game targets **Godot 4** (see [`docs/GAME_PLAN.md`](docs/GAME_PLAN.md)).

> The Python simulation in [`sim/`](sim/) is the **rules authority**. The web build is a
> feel-prototype that mirrors it and may drift — on any disagreement, **`sim/` wins**.

---

## Quick start

All commands run **from the repository root**.

```bash
pip install openpyxl                 # only hard dependency for the sim

python -m sim.validate               # confirm engine: 141/141 handlers + 300 smoke games
python tools/run_sim.py --n 1000     # win-rate race report @ 2/3/4 players
python tools/play.py                 # hotseat text playtest (you control all heroes)
```

Play the browser prototype: open [`web/index.html`](web/index.html) directly, or
`python -m http.server 8123 --directory web` → http://localhost:8123

---

## Repository layout

```
.
├── README.md              ← you are here (current state + version)
├── sim/                   ← RULES ENGINE (authoritative Python package)
│   ├── cards.py engine.py effects.py abilities.py boss.py ai.py game.py validate.py
├── tools/                 ← batch sims, exports & playtest entry points
│   ├── run_sim.py rank_combos.py trace_game.py calibrate_boss.py winrate_topcombos.py
│   ├── export_web_cards.py export_top_combos.py export_godot_data.py audit_web_fx.py play.py
│   ├── gen_placeholder_sfx.py
│   └── legacy/            ← archived data-build / OCR / macro-model scripts (reference only)
├── godot/                 ← GODOT 4 BUILD (shipping target): headless engine + presentation
│   ├── engine/  data/cards.json  game/  assets/  tests/   (see godot/README.md)
├── web/                   ← browser feel-prototype (index.html, game.js, generated *_data.js)
├── data/                  ← source-of-truth + generated data
│   ├── Cards_Data.xlsx    ← ★ master card data (edit in place; never auto-regenerate)
│   ├── top_combos.json    ← sim-ranked default parties
│   ├── backups/           ← dated xlsx backups
│   └── caches/            ← OCR caches (git-ignored)
├── docs/                  ← design & state docs (HANDOVER, Design_Plan, SIM_STATE, GAME_PLAN, …)
├── assets/                ← card art + source docx/pdf (git-ignored — see "Assets")
└── logs/                  ← generated game traces (git-ignored)
```

**Path note:** scripts resolve files relative to the repo root via `__file__`, so they run from
anywhere, but the documented invocations assume root. After moving files, the import bootstrap in
each `tools/` script keeps `import sim` working.

---

## Current state (v0.4.0)

### Mechanics (locked, implemented in `sim/` + `web/`)
No-shuffle decks with optional discard · Action→Draw phases, no mana banking · 8-card class
starters · artifacts equip into slots 0→5 (cost 1/2/3/4/5, charge 1 turn, then fire every turn) ·
Affinity 1→3 (Tier-2 buys @2, Ultimate abilities @3) · 3-Mana once-per-turn class ability · Red
Dragon with telegraphed deck, Anger→Disaster pile, Level-Up on deck cycle, minions, Joker turn at
odd player counts.

### Market model — **randomized tier slots (v0.4.0 change)**
The shared market is now **15 fixed tier slots** seeded with **random** cards (mirrors the online
test build's `web/game.js`): 4 Mana · 4 Weapon · 4 Artifact · 3 Support. Buying a card refills
only that slot. **Players buy only what is currently on offer** — the old "pick any affordable
card from the whole supply" model is gone. Tutor abilities (Enchanter/Blacksmith) still fetch from
the open pool. This made the game markedly harder.

### Balance (TUNED config — do not retune without a fresh design decision)
Boss HP `40 + 10×P` · Village `20 + 10×P` · Player HP `10` · boss deck 12 Boss + 7 Minion · 6
disasters.

**Top-10 class-combo win rates under the new randomized market** (1000 games/combo,
`python tools/winrate_topcombos.py`):

| Players | Top-10 avg | Best combo |
|--------:|:----------:|------------|
| 2p | ~25% | Cleric + Wizard (51%) |
| 3p | ~72% | Bard + Cleric + Ranger (90%) |
| 4p | ~59% | Bard + Cleric + Ranger + Wizard (85%) |

(Old open-supply model averaged ~70 / 94 / 93%.) Cleric anchors nearly every strong lineup; 2p is
structurally hardest by design. `data/top_combos.json` still holds the *old* numbers as a baseline.

---

## Changelog

- **v0.5.5** (2026-06-17) — Godot: schema-versioned save/restore (`snapshot`/`restore`/file I/O),
  RNG-state-exact, deterministic resume verified through a JSON round-trip.
- **v0.5.4** — Godot: Hearthstone-style drag-to-play cards; assertion suite expanded.
- **v0.5.3** — Godot combo-ranking tool (`rank_combos.gd`); `.gitattributes` LF normalization.
- **v0.5.2** — Godot vertical-slice demo: real co-op turn loop (mana economy, market drawer,
  affinity/ability/slots, End Turn → AI ally + boss response).
- **v0.5.1** — Godot: all deferred effect ops implemented; 52-assert behavioural test suite.
  Installed Godot 4.3 and **verified the engine end-to-end** (smoke/determinism/assertions pass).
- **v0.5.0** (2026-06-17) — **Godot 4 build foundation** (`godot/`): authoritative headless rules
  engine ported to GDScript (deterministic RNG, randomized market, abilities, full boss loop,
  data-driven effects), single content source `godot/data/cards.json` (`tools/export_godot_data.py`),
  a headless self-test, and a **Hearthstone-tier presentation scaffold** (event bus, audio
  manager + bus layout + procedural SFX, juice helpers, animated `CardView`, engine-driven feel
  demo). See `godot/README.md` and `godot/assets/ART_DIRECTION.md`.
- **v0.4.1** (2026-06-17) — Fixed the infinite discard-replay loop (two mutual Weapon retrievers,
  e.g. 2× Arsenal Enforcer): a card may now be pulled back from discard at most once per turn.
- **v0.4.0** (2026-06-17) — Sim market aligned to the online test build: **randomized 15-slot tier
  market** replaces open supply (`sim/engine.py` `build_market`/`market_choices`/`replace_market_slot`,
  `sim/ai.py` `do_buys`). Fixed two latent crashes (self-refiring artifact recursion; double-remove
  on consumed refire). Re-measured top-10 win rates at 1000 games. **Repository reorganized** into
  thematic folders (`sim/ tools/ web/ data/ docs/ assets/ logs/`) and put under Git.
- **v0.3.x** (2026-06-16) — A–H content rework + artifact ½·cost balance pass applied to the xlsx;
  hotseat `play.py` CLI; bug-fix pass (see [`docs/Bugs.txt`](docs/Bugs.txt)).
- **v0.2.x** — Faithful headless simulation built in `sim/`; abstract macro model retired for
  balance; TUNED boss/village numbers accepted (see [`docs/SIM_STATE.md`](docs/SIM_STATE.md)).
- **v0.1.x** — Card data extracted from the source PDFs/docx into `Cards_Data.xlsx`; design spine
  locked (see [`docs/Design_Plan.md`](docs/Design_Plan.md)).

---

## Documentation

| Doc | Read when… |
|-----|------------|
| [`docs/HANDOVER.md`](docs/HANDOVER.md) | Resuming work — full file map, workflows, watch-items. |
| [`docs/Design_Plan.md`](docs/Design_Plan.md) | You need design rationale + locked mechanics. |
| [`docs/SIM_STATE.md`](docs/SIM_STATE.md) | Sim deep-dive: architecture, fixes, balance history. |
| [`docs/GAME_PLAN.md`](docs/GAME_PLAN.md) | The path to the commercial Godot 4 game. |
| [`docs/Content_Rework.md`](docs/Content_Rework.md) | The applied A–H content rework (reference). |
| [`docs/Bugs.txt`](docs/Bugs.txt) | Fixed bugs; log new playtest findings here. |
| [`web/README.md`](web/README.md) | Running/extending the browser prototype. |

## Assets

Card art and source documents (`assets/`, plus two ~97 MiB `Image Cards.*` files) are **excluded
from Git** (`.gitignore`) to keep the repo small — they live locally only. The sim and web build
do not need them; they are inputs to the archived `tools/legacy/` data-build scripts. The
authoritative, lightweight card data lives in [`data/Cards_Data.xlsx`](data/Cards_Data.xlsx),
which **is** committed.

## Requirements

Python 3.10+ with `openpyxl`. The browser prototype needs only a modern browser. The
`tools/legacy/` OCR scripts additionally need `PyMuPDF`, `pytesseract`, and `Pillow` (not required
for normal use).
