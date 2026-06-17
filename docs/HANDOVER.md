# Handover — Marvin's Board Game

> **⚠ Repo reorganized in v0.4.0 (2026-06-17).** Files now live in thematic folders
> (`sim/ tools/ web/ data/ docs/ assets/ logs/`). See [`../README.md`](../README.md) for the
> authoritative file map + version. Command paths below that read `python run_sim.py` are now
> **`python tools/run_sim.py`** (run from repo root); `Cards_Data.xlsx`/`top_combos.json` →
> `data/`; the web prototype `game/` → `web/`; design docs → `docs/`. The market model also
> changed to a randomized tier-slot market — see README "Current state".

**Last updated:** 2026-06-17

Co-op deckbuilding boss-battler: heroes + a shared **Village** vs. the **Red Dragon**. Built on
the Aeon's End → Astro Knights chassis (randomized turn order, supply market, artifact engine).
The rules are **designed, simulated, and playtestable today**; the shippable game is planned for
**Godot 4** (see `GAME_PLAN.md`).

---

## Start here (new session checklist)

1. Read **this file** for current state and file map.
2. Skim **`Design_Plan.md`** for *why* the rules are what they are (design spine; some numbers
   there are superseded — see **Balance** below).
3. Open **`Cards_Data.xlsx`** only if you are editing cards — it is the content source of truth.
4. Run **`python -m sim.validate`** — confirms effect handlers + smoke games pass.
5. Play something:
   - **Browser:** open `game/index.html` or `python -m http.server 8123 --directory game`
   - **Terminal:** `python play.py` (hotseat text playtest with choices)
6. Check **`Bugs.txt`** for the latest fix pass and where to log new findings.

---

## What exists today

| Layer | Status | Purpose |
|-------|--------|---------|
| **Design + card data** | Done, iterating | `Cards_Data.xlsx`, `Design_Plan.md`, `Content_Rework.md` |
| **Rules engine (`sim/`)** | **Authoritative** | Headless Python sim — balance, validation, AI games |
| **Batch tools** | Done | `run_sim.py`, `rank_combos.py`, `trace_game.py`, `calibrate_boss.py` |
| **Text playtest** | Done | `play.py` — human hotseat, market, choices |
| **Web prototype (`game/`)** | Phase 1 done | Feel-prototype / interactive spec (throwaway before Godot) |
| **Commercial game** | Not started | Target Godot 4 — see `GAME_PLAN.md` |

**Bottom line:** You can change cards in the xlsx, regenerate exports, validate in `sim/`, and
play in browser or terminal. Do **not** treat the web prototype as the rules authority — it mirrors
`sim/` but can drift; **`sim/` wins on disputes.**

---

## Repository map — where to find what

### Source of truth (edit these)

| File | What it is |
|------|------------|
| **`Cards_Data.xlsx`** | All ~142 cards: names, categories, tiers, costs, class, text. **Edit in place.** Do not regenerate from build scripts (would wipe manual edits). |
| **`sim/effects.py`** | Name → effect handler for every player card. **Authoritative card behavior.** |
| **`sim/abilities.py`** | Class abilities + ultimates (3 Mana; Ultimate @ Affinity 3). |
| **`sim/engine.py`** | Game state: decks, slots, affinity, damage/heal, prevention, supply, win/lose. |
| **`sim/boss.py`** | Boss deck, disasters, anger, level-up. |
| **`sim/ai.py`** | AI buy/play policy (simple heuristics). |
| **`sim/game.py`** | Full game loop, turn order, team building, starters. |
| **`sim/cards.py`** | Loads xlsx into `Card` objects. |

### Playtest surfaces

| File | What it is |
|------|------------|
| **`game/index.html`** + **`game/game.js`** | Browser UI: board, hand, market, boss telegraph, animations. |
| **`game/cards_data.js`** | Generated player cards + starters — **do not hand-edit**; run `export_web_cards.py`. |
| **`game/top_combos.js`** | Generated default parties — run `export_top_combos.py`. |
| **`play.py`** | CLI hotseat playtest; loads `top_combos.json` for party pick. |

### Data export pipeline (run from repo root)

```text
Cards_Data.xlsx
    ├─► python export_web_cards.py  → game/cards_data.js
    ├─► python audit_web_fx.py      → compare web fx vs sim (sanity)
    └─► (sim loads xlsx directly via sim/cards.py)

top_combos.json
    └─► python export_top_combos.py → game/top_combos.js
```

After **any xlsx card change:** `python export_web_cards.py` then hard-refresh the browser (`Ctrl+F5`).

### Simulation & balance tools

| Script | Command | Purpose |
|--------|---------|---------|
| Validate | `python -m sim.validate` | 141/141 handlers + 300 smoke games |
| Batch sim | `python run_sim.py [--n 3000] [--strategy team\|mixed\|caster\|…] [--locked] [--cards] [--trace P]` | Win rates @ 2/3/4 players |
| Trace one game | `python trace_game.py [--p 2] [--seed 0] [--out game_log.txt]` | Full play-by-play log |
| Rank comps | `python rank_combos.py` | All class combos, top 10 per P (40 games each in script) |
| Calibrate | `python calibrate_boss.py` | Boss HP sweep (if rebalancing) |

### Saved playtest defaults

| File | Purpose |
|------|---------|
| **`top_combos.json`** | Top 10 class lineups per player count (1000-game confirmed win rates, TUNED config). |
| **`export_top_combos.py`** | Regenerates `game/top_combos.js` from JSON. |

Web setup defaults to **#1 combo** per player count (e.g. 2p: Cleric+Druid 86%, 3p: Bard+Cleric+Druid 98.6%).

### Design & planning docs

| Doc | Read when… |
|-----|------------|
| **`Design_Plan.md`** | You need design *rationale* and locked mechanics (original “tingly deer” record). Numbers may be stale — check **Balance** here. |
| **`SIM_STATE.md`** | Deep dive on sim architecture, correctness fixes, AI quirks, accepted balance narrative. |
| **`GAME_PLAN.md`** | Shipping path: Godot 4, phases, why web is throwaway, architecture for product. |
| **`Content_Rework.md`** | Historical rework proposal (A–H groups); applied 2026-06-16. Reference only unless doing another content pass. |
| **`Bugs.txt`** | Fixed bugs by pass; add new playtest findings at the bottom. |
| **`game/README.md`** | How to run the web prototype only. |

### Legacy / analysis scripts (reference, not daily drivers)

`build_card_data.py`, `build_costs_ocr.py`, `full_game.py`, `sim_strategies.py`, `sanity_pass.py`,
`corrections.py`, `verify_bossdeck.py` — used to build/analyze the original xlsx and macro model.
**`full_game.py` is an abstract macro model, not the real deck sim** — use `sim/` instead.

---

## Locked rules (current implementation)

These match **`sim/`**, **`play.py`**, and **`game/`** (modulo known web gaps below).

### Core loop
- **No-shuffle decks.** Discard recycles in order. **Optional discard:** keep chosen cards, redraw to 5.
- **Phases:** Action → Draw. **No banking** — generate and spend mana in the same turn.
- **Start deck:** 8 cards = 4× Mana Crystal + 1 class Mana + 1 class Support + 2 class Weapon.
- **Buys** go **under the draw deck** (not discard). **Play mana from hand first** — turn mana starts at 0.

### Card types
- **Weapons** — play from hand, immediate effect, discard (unless destroyed/consumed).
- **Artifacts** — equip into **slots 0→5** (slot cost = 1/2/3/4/5 Mana). Charge **1 turn**, then **fire every turn**. **Wandering Wisp** is slotless (plays from hand, passes to next player's discard).
- **Class cards** (Volley, Bow, Grimoire, …) are **starters only** — never in the market.

### Affinity & abilities
- **Affinity 1→3** (3 Mana to raise). @2 unlocks Tier-2 buys (Greater Mana, Heavy Weapons, Ancient Artifacts). **Mana is never tier-gated.**
- **Ability:** 3 Mana, once per turn. @ Affinity 3 = **Ultimate** version (same cost, repeatable).

| Class | Normal | Ultimate (@ Aff 3) |
|-------|--------|---------------------|
| Ranger | Village heal 2 + 2 DMG | Village heal 3 + 3 DMG |
| Paladin | Heal a player 2 + 2 DMG | Heal 3 + 3 DMG |
| Druid | Heal player 2 + Village 2 | Heal player 3 + Village 3 |
| Cleric | Heal a player 4 | Heal 2 players 4 each |
| Wizard | Re-fire 1 equipped Artifact | Re-fire 2 equipped Artifacts |
| Weaponmaster | Replay 1 Weapon from discard | Replay up to 2 Weapons from discard |
| Enchanter | Tutor Artifact ≤4 Mana to **hand** | Tutor Artifact ≤6 Mana to **discard** |
| Blacksmith | Move 1 Weapon from discard to hand | Tutor Weapon ≤6 Mana to discard |
| Bard | Draw 1 | Heal 3 + draw 1 |

### Red Dragon
- **Telegraphed** next boss-deck card. **Disasters** = separate hidden pile when **Anger ≥ players+2** (Anger resets to 1).
- **Level Up** on boss deck cycle: minions +2 HP/level, anger rises faster.
- Minions attack **end of round**. Boss turns per round = **ceil(players/2)**. **Joker** extra player turn at odd player counts.

### Win / lose
- **Win:** boss HP ≤ 0.
- **Lose:** Village ≤ 0 **or** all heroes down (0 HP; heals revive downed heroes).

### Targeting (sim + web v1)
- Attacks: lowest-HP minion when finishing/crowded, else boss (some cards force boss).
- Heals: lowest HP including **downed** heroes first (`lowest_heal_target`).

---

## Balance — accepted numbers (TUNED config)

**Do not retune boss/village/HP without a fresh design decision.** Designer signed off on these
(see `SIM_STATE.md` for history of calibration).

| Parameter | Value |
|-----------|-------|
| Boss HP | **40 + 10×P** (60 / 70 / 80 @ 2/3/4p) |
| Village HP | **20 + 10×P** (40 / 50 / 60) |
| Player HP | **10** |
| Boss deck per game | **12 Boss + 7 Minion** cards sampled from xlsx |
| Disaster pile | **6** cards |
| Slot costs | 1, 2, 3, 4, 5 Mana |
| Artifact charge | 1 turn |

`run_sim.py` defaults to **TUNED**. Pass **`--locked`** for old design numbers (50+15P boss, etc.).

### Win-rate expectations (important for playtesters)

| Context | 2p | 3p | 4p | Notes |
|---------|----|----|-----|-------|
| Random classes + AI | ~19–24% | ~50–53% | ~39–47% | `run_sim.py --strategy by_class` or mixed |
| Top-10 comps + AI | ~48–86% | ~83–99% | ~62–97% | See `top_combos.json`; **Cleric** in almost every top lineup |
| **Web prototype, human** | Lower early | Lower early | Lower early | Limited 15-slot market vs sim's **full open supply**; bought cards cycle slowly |

**Losing in the first 3–5 rounds on the web client is normal** even with good choices: boss/minion
village pressure is front-loaded, and market purchases sit under the deck for several turns.

---

## `sim/` package quick reference

```text
sim/
  cards.py      — load Cards_Data.xlsx
  engine.py     — Game, Player, EffectContext, supply_choices(), combat, prevention
  effects.py    — @effect handlers for every card name
  abilities.py  — class abilities
  boss.py       — build boss deck, disasters
  ai.py         — play_hand, do_buys, do_equip, draw_phase
  game.py       — play_game(), turn order, DEFAULT_ROLES, CLASS_STRAT, build_starter()
  validate.py   — coverage + smoke test (python -m sim.validate)
```

**Market in sim:** AI buys from **`supply_choices()`** — all affordable `"All"`-class cards each turn
(no slot limit). **`play.py`** uses random slots per category (5/5/4/4). **`game/`** uses **15 fixed
tier slots** (Astro Knights style) — stricter than sim; tier pools verified against xlsx.

---

## Web prototype (`game/`) — scope & gaps

**Run:** `game/index.html` or `python -m http.server 8123 --directory game`

**Implemented:** setup (player count + sim-ranked party picker), full turn loop, equip/fire artifacts,
affinity, abilities, tier-gated market, boss telegraph/anger/disasters/level-up, minions, joker,
prevention, animated damage, end-turn keep/discard with **cancel**, hotseat multi-hero.

**Not full parity with sim:**
- Boss/minion/disaster tables are a **curated subset** in `game.js` (not full xlsx boss deck).
- Market is **15 tier slots**, not open supply — harder than sim AI games.
- Complex cards rely on `export_web_cards.py` **FX overrides** + text parser; run `audit_web_fx.py` after changes.
- No meta, saves, audio, or targeting UI (auto-target only).

**Key web files:** `game.js` (logic + fx resolver + boss tables), `cards_data.js` (generated),
`top_combos.js` (generated), `index.html` (UI).

---

## Text playtest (`play.py`)

```text
python play.py
```

Pick player count → pick sim-ranked party (Enter = #1) → hotseat commands:

`play <i> | equip <i> | ability | affinity | buy | reshuffle | slot | state | done`

Draw phase: keep by index, Enter = discard all, **`cancel`** = abort end-turn and keep playing.

Uses **`top_combos.json`**. Market model matches **`play.py` Market class** (random per category, not web tier slots).

---

## Common workflows

### Change a card's text, cost, or tier
1. Edit row in **`Cards_Data.xlsx`**
2. Update handler in **`sim/effects.py`** if behavior changed
3. Add/adjust entry in **`export_web_cards.py`** `FX` dict if web needs an explicit override
4. `python export_web_cards.py`
5. `python -m sim.validate`
6. `python audit_web_fx.py` (optional)
7. Playtest in browser or `play.py`; log issues in **`Bugs.txt`**

### Rebalance boss or village
1. Change knobs in **`run_sim.py`** `TUNED` dict and/or **`sim/engine.py`** constants
2. `python run_sim.py --n 1000`
3. Optionally `python rank_combos.py` / `calibrate_boss.py`
4. Update **`SIM_STATE.md`** and this file if accepted

### Refresh default playtest parties
1. `python rank_combos.py` (long run) — review output
2. Manually update **`top_combos.json`** with confirmed results
3. `python export_top_combos.py`

---

## Watch items / open questions

- **Timeless Talisman + same-turn refire:** rules must block re-firing it the same turn it postponed
  (partially enforced in sim + web).
- **Class balance:** Cleric dominates top comps; Blacksmith/Enchanter anchor weak comps — partly AI
  underuse of tutor abilities, partly card power. Verify with human play before nerfs.
- **2p is structurally hardest** (no Joker, fewer seats) — by design for now.
- **Web vs sim market:** intentional difference; consider aligning web to `play.py` market or adding
  a “full supply” test mode if playtesters expect sim-like win rates.
- **Dual codebase drift:** `GAME_PLAN.md` calls for porting rules once to Godot and retiring `sim/`;
  until then, **`sim/` is law**, web is best-effort mirror.
- **Three interpretation calls** from Content_Rework apply (see old handover notes): Blessing of Faith
  targeting, Martial Focus counts weapons in discard, Aegis Ward pricing — confirm in rulebook pass.

---

## Doc index (one line each)

| Document | One-line summary |
|----------|------------------|
| **HANDOVER.md** (this file) | Start here: map, state, workflows. |
| **Design_Plan.md** | Original locked design decisions + rationale. |
| **SIM_STATE.md** | Sim deep-dive, fixes, balance acceptance, AI caveats. |
| **GAME_PLAN.md** | Path to commercial Godot game. |
| **Content_Rework.md** | Applied 2026-06-16 content rework checklist. |
| **Bugs.txt** | Fixed bugs; add new findings here. |
| **game/README.md** | Web prototype run instructions. |

---

## Python environment

Requires **Python 3.10+** with **`openpyxl`** (loads xlsx). No pinned `requirements.txt` in repo —
install with `pip install openpyxl` if validate fails on import.

---

*When this file and `SIM_STATE.md` disagree on fine-grained sim history, prefer **`SIM_STATE.md`**
for sim-specific detail and **this file** for onboarding and repo navigation.*
