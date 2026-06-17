> **Note (durable copy of the "tingly deer" plan).** This is the original design-decision record.
> Later simulation work — see **`HANDOVER.md`** — superseded several balance numbers below
> (Boss HP, Village HP, Player HP, Affinity cap, and the Ultimate threshold). Where this doc and
> `HANDOVER.md` disagree on numbers, **`HANDOVER.md` is current.** The design *decisions* and
> rationale here remain the reference.

# Marvin's Board Game — Design Decisions & Roadmap

## Context
A cooperative deckbuilding boss-battler (heroes + a shared **Village** vs. the **Red Dragon**),
built on the Aeon's End → Astro Knights chassis (randomized turn-order deck, supply market,
homeworld/village to defend). The current materials (`Cards.docx`, `Cards.pdf`, `Image Cards.*`)
have drifted into version conflicts, and two core systems (weapons vs artifacts; deck cycling)
were under-differentiated. This document records the agreed redesign so we can rebuild the card
data, rebalance, and then write the rulebook against a settled game.

Goal: make the game **better than Aeon's End**, not just different — by fixing its known wrinkles
(blind nemesis, multiplayer-solitaire, flat progression) while keeping its strength (turn-order tension).

---

## Locked design decisions

### Core loop
- **No-shuffle decks.** Players never shuffle. Stack/sequence your deck; when it runs out, flip the
  discard back into a draw deck *in order*. Deck sequencing is a skill.
- **Turn phases:** **Action → Draw.** (Old Attack and Equip phases both cut.) Equipping an artifact
  is just an Action; the artifact's one-turn charge delay handles same-turn double-dip. Weapons are
  played-and-discarded, never "equipped" — so "equipped" now means **artifacts only**, and the
  "equipped Weapon" scaling cards (Multiplier Maul, Blacksmith's Pride, Martial Focus, Bladesurge
  Stone, Artificer's Fury) need rework (part of the content wave).
- **Draw (optional discard):** start of game draw 5 from the 8-card deck; each Draw Phase discard
  **only the cards you want to**, then redraw **up to 5**. Keeping cards lets you control the
  no-shuffle sequence (hold/sequence good cards), which **smooths the feast/famine income swings**
  that mandatory full-discard + no-shuffle produced in simulation, and is the core no-shuffle skill.
  (Reverses the earlier mandatory-full-discard plan.)
- **Buying:** pay Mana; place the bought card **under the draw deck** (not the discard) so it cycles
  in fast and predictably.
- **Mana:** no banking — generate and spend within the turn.
- **Start deck (current):** 8 cards = 4× Mana Crystal + 1 Special Mana + 1 Special Support +
  2 Special Weapon. (The "54 / 6-special" text in old docs is stale — ignore.)

### Weapons vs Artifacts (the differentiation)
- **Weapons:** immediate normal actions, **consumed on use** (burst; single-target/high value).
- **Artifacts:** occupy a **personal slot**; **private engine** owned by the caster.
  - Equip = "charging" (tap sideways); cannot fire the turn equipped.
  - From the owner's **next turn** it is "ready": fire **once per your turn, every turn**, stays equipped.
  - Tracking = tap/untap state; only you fire only your own artifacts on your own turn.
  - **Sharing is opt-in only** via cards (e.g. Magic Veil, Encourage) — never the default,
    so casters stay damage engines, not support bots.
- Class identity follows the split: Wizard/Enchanter/Cleric = artifact engines;
  Weaponmaster/Blacksmith/Ranger = weapon burst; Paladin/Druid/Bard = hybrids.
- **Slots (locked):** start at **0**, **cap 5**, buy +1 per action for **(current slots + 1) Mana**
  (so 1/2/3/4/5; 15 total to max) — cheap first slot makes the first artifact reachable ~turn 2-3,
  escalating cost gates going wide. (was: Mana price TBD by economy
  model). Artifacts are a universal buy-in. Caster basic damage cards convert **artifact -> weapon**
  (Grimoire/Wizard, Wand/Enchanter, Clergy Staff/Cleric) so every class opens weapon-based and has
  no dead starter cards. Wizard/Enchanter open generic, bloom into the artifact engine mid-game via
  their ability/Ultimate. Keep boss strip effects (Gear Purge, Material Damage) meaningful; 5 firing
  artifacts at cap is a strong late engine to balance.

### Signature pillars (the "better than Aeon's End" identity)
- **P1 — Telegraph the boss.** The boss's **next card is revealed face-up**; planning beats luck.
  The **Anger → Disaster** deck stays **hidden** as the controlled-chaos valve. This is also the
  primary teamwork engine: visible threats + random turn order force the team to sequence each round.
- **P3 — Affinity is THE central scaling/progression mechanic (locked).** Affinity **starts at 1,
  range 1-3 (cap 3)** — two meaningful upgrades, no dead levels. Raised by paying 3 Mana (action),
  never resets. Jobs: (1) **scaling** — fuels Sorcerous Affinity, Affinity Beacon, Mana Cannon,
  Multiplier Maul, Slayer's Relic (rescaled to a 1-3 range; bump per-level values so the archetype
  stays worth it); (2) **Tier-2 gate @ Affinity 2** — unlocks Greater ("strong") Mana + Heavy
  Weapons + Ancient Artifacts all at once; (3) **Ultimate @ Affinity 3** — ability upgrades into its
  Ultimate version (no longer Charge-gated). **Mana NOT gated** at base/Moderate (preserves the
  buy-Mana-rounds-1-2 opening); only Greater Mana sits behind the Tier-2 gate. Tier gates per-player.
  WATCH: Affinity 2 is a cheap all-at-once power spike (progression compressed to ~turn 3); Ultimates
  now arrive mid-game (~turn 3-4) and repeat every turn -> repeatable-Ultimate rebalance is the key task.

### Charge mechanic — STRUCK (locked)
The Charge track (0-3) is removed: playtests showed the ability fires only ~1-5x/game, so the
"build to one Ultimate" meter rarely paid off. The Ultimate is now unlocked permanently at
**Affinity 3** (the ability becomes its Ultimate version), making Ultimates **repeatable** (once/turn
for 3 Mana). Consequences to rework: (a) ~15 cards reference Charge — grant (Mystic Infusion,
Encourage, Worthy Sacrifice, Blessing of Faith), Village Charge (Faithful Brew, Well Prepared, Armed
Militia + the Village card's charge-gated Ultimate), drain (Absorb Mana, Threatening Glare, Dragon
Cultist, Kobold Shaman), reset (Power Anomaly), trigger (Secret Technique), Slayer's Relic. Convert
"+Charge" to Mana/draw/heal (NOT +Affinity); re-point boss drains to Affinity/Mana/discard.
(b) Repeatable Ultimates need a balance pass (e.g. Cleric/Druid heals).

### Damage prevention — light & card-based (locked)
Add **damage prevention as scarce card effects, not a new stat/track** — e.g. "prevent up to N
damage to a player or the Village this round" / "negate the next Boss card" (extends the existing
**Timeless Talisman** "skip next Boss turn"). Rationale: makes the telegraph (P1) *actionable*
proactively, and answers the boss's **non-HP** attacks (discards, Affinity/Charge drain, gear-strip)
that healing can't touch. Keep them costed/scarce so they're clutch saves, not default defense
(preserves time pressure). Design a small set during the content/balance pass.
- **(Rejected) Shared artifact battery** — would turn casters into charge-bots; replaced by the
  private-engine model above. Teamwork comes from P1 + the shared Village + opt-in enabler cards.

### Trackers, Village, Boss
- **HP** players (start value tuned later), **Affinity** 1–3 (cap, no reset). (Charge removed.)
- **Abilities:** Use Ability costs 3 M, **once per turn**, may target **own or Village** ability.
- **Village:** HP **40**; ability **deal 2 DMG**. Never takes its own turn — a player spends their
  one ability use on it. (Charge-gated village Ultimate removed with the Charge mechanic.)
- **Boss (Red Dragon):** HP scales with players (formula tuned later). **One boss card per boss
  turn**, resolve effect. **Minions** are a boss-card type: they take the field and **attack at end
  of ROUND** (not on the boss turn). **Anger** +1 each boss turn; at ≥5, −3 and trigger a hidden
  **Disaster** card (repeat). **Level Up** when the boss deck cycles: minions +2 HP, anger faster.
- **Defeat:** Village hits 0 **or** all players down. A downed player can't act but can be healed back.

### Turn order
- **4 players max** (>4 removed — made games too long).
- Pair cards **[1/2]** and **[3/4]**: first matching card, either of the pair takes a turn; next
  matching card, the other must. **Boss turns = ceil(players / 2)**.
- **Joker** = a flexible extra turn used for odd player counts; **any player may take it (can go twice)**.
  Designer wants this to enable carry/hypercarry turns. (Watch in playtest for the "quarterback"
  problem — one seat doing the majority of damage.)
- If **3 BOSS turn-order cards** come up in a row, reshuffle the remaining turn-order deck and redraw.

---

## Known data problems to fix (single source of truth)
- Every card duplicated (front/back) in the docx; stale component counts (the "54").
- Category mismatches across copies (e.g. **Arsenal Enforcer** = Support vs Weapons 1).
- Conflicting costs (e.g. **Composter** cost 2 vs 3).
- Duplicated/incorrect effects (e.g. one **Mana Resonance** copy carries Blacksmith's Pride's text).
- Name vs art drift (e.g. "Groveguard Bow" vs *knuckles* image; "Maul of Renewal" vs "Mace of Renewal").

---

## Roadmap (agreed order)
1. **Consolidate the data** into one structured source of truth (spreadsheet/CSV/JSON):
   one row per card — `Name, Type, Subtype/Tier, Cost, Effect, Class, Copies, Version/Status`.
   All printable docs + the rulebook component list + balance math derive from this.
2. **Lock remaining parameters:** slot economy, Affinity tier thresholds + Ultimate upgrades,
   mana-economy baseline, telegraph edge cases.
3. **Rebalance** on the clean data (damage-per-mana curve, Affinity payoff, swing cards, boss
   damage-per-round vs Village HP and expected healing).
4. **Write the rulebook** against the settled, consistent game.

## Balance parameters (from sim + review — SUPERSEDED in part; see HANDOVER.md for current)
- Original locked: **Boss HP = 50 + 15×players**, **Village HP = 30**, **Player HP = 10.**
  (Later full simulation overturned these — current values live in `HANDOVER.md`.)
- **Balance target: 2-4 players** (tune ~2, spot-check 4). **Healing kept scarce** (offense/defense tension).
- **Economy model confirmed:** Cost = price to *buy* from supply; playing a card from hand is *free*.
- **Damage baseline ~1 DMG/Mana**; **conditional/scaling payoffs target ~2 DMG/Mana** at full investment
  (more is good for reward cards). **Block/prevention ~1.5 Mana per point prevented.**
- **Prevention = shield tokens** on a player/Village, removed before HP, **last until end of round**
  (played on your turn in anticipation of the telegraphed Boss hit; no new track).
- **"Equipped Weapon" scaling counts Weapons in your Hand** (snapshot, no turn-tracking).
- **Weaponmaster** reworked to weapon recursion (play Weapons from Discard). **Secret Technique**:
  chosen player uses their ability (Ultimate if Affinity 3+) free — no "again" in the wording.
- **Ultimates** are Affinity-3-gated and repeatable each turn (3 Mana) — toned to ~6 value/turn;
  watch Cleric / Wizard / Bard / Enchanter+Blacksmith (final ability table is in `HANDOVER.md`).
- Deferred to later sim: card-draw costing, the new prevention card, per-card copy counts.

## Verification
- Card data: every card has a unique row, no conflicting copies; counts reconcile with the
  intended physical deck sizes.
- Design: a dry-run round (telegraphed boss card + a player turn + end-of-round minion attack)
  resolves unambiguously using these rules.
- Rulebook: a reader can set up and play a first round without external clarification.
