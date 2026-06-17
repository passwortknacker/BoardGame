# Content Rework — single-pass review

All proposals reflect the locked design (Charge struck; Affinity 1–3 spine; slots 0–5; weapons
consumed/not-equipped; artifacts = slot engine; optional discard; light prevention) and the
economy anchor (~3 Mana T1 → ~5.5/turn steady; ~1 DMG/Mana; **draw is premium**).

**Review per group; mark ✅ / ✏️ (tweak) / ❌ per row.**

---

## 0. Structural recommendations (bigger knobs — decide first, they shape the rest)
| Knob | Current | Proposed | Why (from sim) |
|---|---|---|---|
| Boss HP | 40 + 10×players | **50 + 15×players** (80 @2p) | Team out-ramps 60 HP → 100% win. ~80 makes a ~round-7–8 race. |
| Village HP | 40 | **30** (or push boss→village dmg up) | At 40 the Village is never the threat (losses are ~all player deaths); at 30 it becomes a real second clock. |
| Healing | scattered | keep **scarce** | Heal 2 vs 3/round swings win rate ~10–15% — the offense/defense tension lives here. |

---

## A. Strike Charge — conversions (Charge no longer exists)
| Card | Current | Proposed | Why |
|---|---|---|---|
| **Mystic Infusion** (Mana, 3) | +2 Mana, Gain 1 Charge | **+2 Mana. 1 Player heals 2 HP** | Charge→a scarce heal; keeps it a strong utility Mana card. |
| **Encourage** (Support, 5) | +1 Charge; 1 player use Wpn/Art free | **1 Player may use 1 equipped Artifact again this turn, or play a Weapon from their Discard Pile** | Reuse was the real value; drop Charge. |
| **Worthy Sacrifice** (Support, 4) | destroy 1 hand card, +1 Charge / draw | **Up to 2 Players each destroy 1 Card (Hand or Discard), then draw 1 Card** | Deck-thinning (valuable under no-shuffle) + draw. |
| **Blessing of Faith** (Support, 0, Cleric) | +1 Charge for you +2 players | **You and up to 2 chosen Players each heal 2 HP** | Team heal fits the faith theme; heal is scarce. |
| **Faithful Brew** (Mana, 4) | +3 Mana, +1 Village Charge | **+3 Mana. +3 Village HP** | Village support replaces village charge. |
| **Well Prepared** (Support, 4) | +3 Village HP, +1 Village Charge | **+5 Village HP. Prevent the next 3 damage to the Village this round** | Becomes a Village-defense/prevention card (group F). |
| **Armed Militia** (Support, 4) | trigger Village skill, +2 Charges | **Trigger the Village ability — it deals 5 DMG this turn instead of 2** | Village has no Charge now; a buffed Village attack. |
| **Slayer's Relic** (Artifact, 4) | 3 DMG; +Charge & Affinity on kill | **3 DMG. If this defeats a Minion, +1 Affinity Level** | Clean; Affinity is the new reward — nice spine synergy. |
| **Secret Technique** (Support, 6) | use a player's Ultimate, drop Charges | **A chosen Player immediately uses their ability again (Ultimate version if Affinity 3+), free** | Re-points to the new Affinity-gated Ultimate. |
| **Absorb Mana** (Boss) | 1 lose Affinity, 2 lose Charge | **2 Players each lose 1 Affinity Level** | Affinity loss now meaningfully sets back progression. |
| **Threatening Glare** (Boss) | 3 take 2 DMG, 2 lose Charge | **3 Players take 2 DMG. 2 Players each discard 1 Card** | HP + disruption. |
| **Dragon Cultist** (Minion 6) | 1 takes 3, 2 lose Charge | **1 Player takes 3 DMG. 1 Player loses 1 Affinity** | — |
| **Kobold Shaman** (Minion 5) | 1 DMG/player, lose Aff + Charge | **1 DMG per Player collectively. 1 Player loses 1 Affinity** | — |
| **Power Anomaly** (Disaster) | Reset all Charges to 0 | **All Players lose 1 Affinity Level** | A progression-setback disaster — thematically a magic anomaly. |

---

## B. "Equipped Weapon" scaling (weapons aren't equipped now — only artifacts are)
| Card | Current | Proposed | Why |
|---|---|---|---|
| **Blacksmith's Pride** (Mana, 0) | +1; +1/2/3 if 1/3/5 Weapons equipped | **+1 Mana; +1/2/3 if you have 1/3/5 Weapons in Hand** | Count Hand instead of "equipped." |
| **Martial Focus** (Mana, 0) | +1; +1/2/3 if 1/3/5 Weapons equipped | **+1 Mana; +1/2/3 if you have 1/3/5 Weapons in Hand** | Same. |
| **Bladesurge Stone** (Mana G, 3) | +1; +1/2/3 if 1/3/5 Weapons equipped | **+1 Mana; +1/2/3 if you have 1/3/5 Weapons in Hand** | Same. |
| **Multiplier Maul** (Weapon H, 6) | 2 DMG/equipped Wpn + 1/unused Affinity | **2 DMG for every Weapon you've played this turn (incl. this) + 1 DMG per Affinity Level** | Rewards a weapon-heavy turn; Affinity ties to spine. |
| **Artificer's Fury** (Artifact A, 7) | 3 DMG; +2/other Wpn or Art equipped | **3 DMG. +2 for every other equipped Artifact** | Only artifacts are equipped — clean artifact-engine payoff. |

---

## C. Caster basics: artifact → weapon (so casters open weapon-based)
| Card | Current | Proposed |
|---|---|---|
| **Grimoire** (Wizard) | Artifact, Deal 1 DMG, 0 | **Weapon**, Deal 1 DMG, 0 |
| **Wand** (Enchanter) | Artifact, Deal 1 DMG, 0 | **Weapon**, Deal 1 DMG, 0 |
| **Clergy Staff** (Cleric) | Artifact, Deal 1 DMG, 0 | **Weapon**, Deal 1 DMG, 0 |

---

## D. Ultimates — repeatable-safe (now Affinity-3 gated, usable every turn for 3 Mana)
Tone the burst-balanced ones down so they're fair *repeated*. (Normal ability shown for reference.)
| Class | Normal ability | Ultimate (old, one-shot) | Ultimate (new, repeatable) |
|---|---|---|---|
| Ranger | Village 2 + 2 DMG | Village 5 + 5 DMG | **Village 3 + 3 DMG** |
| Paladin | Heal 2 + 2 DMG | Heal 5 + 5 DMG | **Heal 3 + 3 DMG** |
| Cleric | Heal 1 player 4 | Heal 2 players to full | **Heal 2 players 4 each** |
| Druid | Heal 2 + Village 2 | Heal 5 + Village 5 | **Heal 3 + Village 3** |
| Bard | Heal 3, 3 DMG, +1 Anger | +2 Anger; per Anger heal 2/deal 2 | **+1 Anger. Heal 1 player 4, deal 4 DMG** |
| Wizard | Use 1 equipped Artifact free | Use ALL equipped Artifacts free | **Use 2 equipped Artifacts free** |
| Enchanter | Take Artifact Discard→Hand | Take Artifact Supply→Discard | keep (costed by 3 Mana/turn) |
| Blacksmith | Take Weapon Discard→Hand | Take Weapon Supply→Discard | keep (costed by 3 Mana/turn) |
| **Weaponmaster** ⚠️ | "use 1 equipped Weapon" — **broken (weapons aren't equipped)** | "use all equipped Weapons" | N: **Play 1 Weapon from your Discard Pile**; U: **Play up to 2 Weapons from your Discard Pile** |

---

## E. Affinity-scaling — rescale to the 1–3 range (bump per-level so it stays worth it)
| Card | Current (scaled to ~5) | Proposed (scaled to 3) |
|---|---|---|
| **Affinity Beacon** (Artifact A, 6) | 2 DMG/Affinity (max 10) | **3 DMG per Affinity Level** (max 9) |
| **Sorcerous Affinity** (Mana G, 4) | +1 Mana/Affinity (max 5) | keep **+1/level** (max 3) — fine for cost 4 |
| **Mana Cannon** (Weapon H, 9) | 5 + Affinity to one enemy | **5 DMG + 2 per Affinity Level** to one enemy |
| **Multiplier Maul** | (see B) | +1 DMG per Affinity Level |

---

## F. Damage prevention — the new light lever (no new stat)
| Card | Effect |
|---|---|
| **Well Prepared** (Support, 4) | +5 Village HP; **prevent next 3 dmg to the Village this round** (from group A) |
| **Timeless Talisman** (Artifact A, 10) | **keep** — "Skip the next Boss turn" (the heavy prevention) |
| **NEW — Aegis Ward** (Support, ~4) | **Prevent up to 4 damage to a player or the Village this round** (proposed new card, or convert a weak Support) |

---

## G. Boss → Village damage (macro; pairs with §0)
The Boss deck deals only ~0.7 Village dmg/attack (mostly disruption), so the Village clock is slow.
If you keep Village at 40, bump village damage on a few cards; if you drop Village to 30, current
numbers roughly work. Candidates to hit Village harder: **Tail Attack 5→6**, **Claw Swipe 4→5**,
**add a "Village takes N" rider** to 2–3 currently pure-disruption Boss cards.

---

## H. Cost outliers — draw is premium (full cost-pass is next; these are the clear ones)
| Card | Current | Note |
|---|---|---|
| Mystic Seer's Lens | Draw 2 @ 6 | Underpriced (you said leave at 6 for now) — flagged. |
| Arcane Tome | 1 DMG + draw @ 4 | Borderline; watch. |
| Mystical Arcanum | +2 Mana + draw @ 5 | OK. |
| Celestial Slicer | 7 DMG **or** draw 3 @ 8 | The draw-3 mode is the strong half — verify vs 7 DMG. |
| Fresh Supplies | draw 3 collectively @ 8 | OK-ish; recheck after Boss-clock sim. |
