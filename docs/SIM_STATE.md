# Simulation — state of development & insights (2026-06-16)

A headless, full-game simulation of Marvin's board game lives in `sim/`. It plays the real
142-card deck with the locked mechanics and is the tool we now use to validate balance.
This doc captures where it stands and what we've learned. See also `HANDOVER.md` (design spine)
and `design_plan.md` (original decisions).

## How to run
- `python -m sim.validate` — asserts 142/142 cards have effect handlers + a smoke test (no crashes).
- `python run_sim.py [--n 1000] [--strategy team|by_class|mixed|<profile>] [--locked] [--cards]`
  — batch win-rate report for P=2/3/4.
- `python trace_game.py [--p 2] [--seed 0] [--focal 0] [--roles ...] [--out game_log.txt]`
  — full play-by-play of ONE game (draws, plays with deltas, buys, equips, ability, boss/anger,
  minions). Use this to verify the rules are followed.
- `python rank_combos.py` — ranks every class combination by win rate (40 games each), top 10 per P.

## Package map (`sim/`)
- `cards.py` loads `Cards_Data.xlsx`. `engine.py` = game state, no-shuffle decks, slot engine,
  affinity, prevention, damage/heal, supply (market = **"All"-class cards only**). `effects.py` =
  name→handler registry for all cards. `abilities.py` = class abilities/ultimates. `boss.py` =
  Red Dragon engine (below). `ai.py` = pluggable player policy. `game.py` = orchestration + turn
  order + team building. `run_sim.py` / `trace_game.py` / `rank_combos.py` = entry points.

## Mechanics modeled (faithful to design_plan.md + the Red Dragon card)
- No-shuffle decks; draw to 5; buys go under the deck; recycle discard in order. Start deck = 8
  (4 Mana Crystal + 1 class Mana + 1 class Support + 2 class Weapon).
- Weapons play-and-discard (recur via cycling). Artifacts = slot engine: slots 0→5, cost
  (current+1) = 1/2/3/4/5; equip is an Action (no 1/turn cap), charges one turn, then fires every
  turn. Wandering Wisp is slotless.
- Affinity 1→3 (Tier-2 buys @2; Ultimate @3). Abilities cost 3 Mana, once/turn (card-granted uses
  are extra). Village ability deal 2 / deal 6 if the triggering player is Affinity 3.
- **Red Dragon:** one telegraphed card per boss turn; boss deck = **Boss + Minion cards only**.
  **Disasters are a separate hidden pile**, drawn when **Anger ≥ players+2** (then Anger resets to 1).
  **Level Up** on deck cycle: minions enter with +2 HP per level, Anger rises +1 faster/turn.
  Minions attack at END OF ROUND. Boss turns = ceil(P/2). **Joker** = one extra player turn at odd
  P (carry seat). Lose if Village ≤0 or all players down.

## Correctness fixes made (the sim was wrong before these)
1. Macro model (`full_game.py`) was **~10× too generous on team damage** — abandoned for the real sim.
2. **Draw was wasted** — `play_hand` iterated a hand snapshot, so cards drawn mid-turn were never
   played. Now it loops, so `draw N` chains play immediately.
3. **Equip throttle** — AI equipped only 1 artifact/turn; now equips all that fit (no 1/turn cap).
4. **Class-card minting bug** — `supply_choices` let players BUY their own 0-cost class cards
   (Volley, Bow…), minting infinite copies and inflating offense. Market is now **"All"-class only**;
   class cards are starters/abilities, never bought.
5. **Buy valuation** — was by mana cost (bought a 1-damage Artificer's Fury for "cost 7"). Now
   `est_damage`/`buy_value` value cards by real effect in context; no mana hoarding; don't buy
   artifact-scalers without artifacts; don't re-buy basic Mana Crystal; ≤1 free buy/turn.
6. **Accurate boss/Anger/Joker** as above (was a placeholder with invented anger spikes).

## Key insights
- **Engines need ~10-round games to mature**; survivability gates them. With beefy boss HP the game
  lasts ~8–10 rounds and weapon/artifact engines come online (the intended late game).
- **Skill/comp dependence is huge.** Random classes → 36/75/52% (2/3/4p). **Reasonable (top-10)
  comps → 72/98/94%.** So for *good* groups the boss is too soft; for random groups too hard. Tune
  to the assumed skill level (decision: target ~70% with good comps).
- **Class balance is very uneven.** Cleric (full healer) is in nearly every top combo — survival is
  king. Blacksmith + Enchanter anchor every *worst* combo. Caveat: tutor/recursion classes
  (Enchanter, Blacksmith, Weaponmaster) may rank low partly because the **AI underuses their
  abilities** — some gap is agent skill, not card power. Verify before nerf/buff decisions.
- **2p is the tightest count** (no Joker, fewer seats) — most demanding even with a good comp.

## Current config (run_sim TUNED) & balance knobs
Boss HP `40 + 10×P` (60/70/80); Village `20 + 10×P` (40/50/60); boss deck 12 Boss + 7 Minion,
6-card disaster pile. Knobs in code: `boss_base/slope`, `boss_comp=(n_boss,n_minion)`, `disaster_n`,
`village_base/slope`, `slot_cost`, `charge_turns`, `PLAYER_HP`; team via `DEFAULT_ROLES`/`build_team`
/`CLASS_STRAT`; `--locked` shows the old 50+15P numbers.

## ACCEPTED balance (2026-06-16) — designer signed off; do not retune the boss
Reverted the "easy mode" softening back to design values: **Player HP 10** (was 13) and the
single-target 5-damage boss spikes (Predatory Strike, Mana Dominance, Bully the Weak, Wyrm,
Critical Hit) back to **5** (was 4). Final numbers: **Boss HP 40+10×P** (60/70/80), **Village
20+10×P** (40/50/60), boss deck 12 Boss + 7 Minion, 6-card disaster pile.

**Accepted win rates (top-10 class combos, 40 games each):**
| P | top-10 avg | best combo | all-combo avg |
|---|---|---|---|
| 2 | 48% | Cleric+Wizard 70% | 25% |
| 3 | 83% | Cleric+Druid+Wizard 88% | 54% |
| 4 | 62% | Cleric+Druid+Paladin+Ranger 72% | 28% |

The designer likes this spread (good comps rewarded, bad comps punished; 2p hardest). We did NOT
force 3/4p to a flat ~70% — this gradient is intended. `run_sim.py` TUNED config matches these values.

## Playtest bug-fix pass 1 (2026-06-16, from Bugs.txt)
Fixed: Arcane Secrets (+1 per *other* mana card, was double-counting); destroy-to-tutor cards now
work (Artifact/Support/Weapon Hexcore, Bounty Bringer, Swapsteel Dirk — tutor a Supply card to
discard + self-destroy via `ctx.consumed`); market refills the bought slot (`Market.replace`);
**affinity-up action added to the CLI** (3 Mana, the missing way to raise Affinity — also unlocked
Tier-2 buys); Arcane Retrieval reworked to "trigger an equipped Artifact again" (artifacts aren't
discarded); Spellblade Energon text "equipped"→"in your Hand"; artifacts can no longer be `play`ed
(must `equip`); Mystic Purifier now thins a card; Spellshard / Wizard ability fire equipped
artifacts correctly. Bug #7 (only 3 cards drawn) was NOT a bug — boss/Disaster discard effects
trim the hand between your turns (cards return next cycle); the sim always draws to 5 absent
disruption.

Interactive choice (CLI): a `g.chooser` hook lets the human pick **which equipped Artifact to
re-fire**, **which Supply card to fetch** (Hexcores, Bounty Bringer, Swapsteel Dirk), and **which
card to move from Discard to Hand** (Ring of Arms, Relic Reclaimer, Improvised Strike, Helping Hand,
Eternal Charm, Sustaining Sigil, Cycle of Life, Enchanter/Blacksmith abilities). Sims leave
`chooser=None` (auto-pick, deterministic).

Damage auto-targeting rule: hit the **lowest-HP minion** when minions pile up (>=2) or one is
finishable this hit, otherwise pressure the **boss** (the win condition); `prefer_minion=False`
cards always hit the boss. Rationale (sim-confirmed): minion attacks accumulate and are the main
**Village** threat (clearing them cut Village losses ~21%->~9%), but the boss is the only win
condition, so pure minion-focus stalls the kill and the team grinds down (players die). This rule
balances both.

**Balance note (2026-06-16):** after the Bugs.txt correctness fixes (esp. Arcane Secrets now "+1 per
*other* mana card", consuming tutors) team offense is lower, so by_class win rates fell from
~36/75/52 to **~24/53/39** (2/3/4p). The designer is **keeping this as-is** — the AI is deliberately
simple and real players are expected to outplay it; will playtest before any re-tune. Do NOT
re-tune the boss without a fresh decision.

Remaining v1 simplifications: heal *targeting* stays automatic in sim (lowest hero / Village — designer OK).

## Open items (not blocking; balance is accepted)
- Class balance is uneven (Cleric near-mandatory; Blacksmith/Enchanter weakest). Confirm whether
  it's card power or agent skill before card changes.
- 2p is structurally the hardest count (no Joker, fewer seats) — by design for now.
- Web boss/minion/disaster deck is still a curated subset (player cards are full xlsx port).
- `calibrate_boss.py` / `rank_combos.py` are reusable analysis scripts if balance is revisited.
</content>
