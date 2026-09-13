# AUDIT v7.1 — ENTRY-ACCURACY PASS

**Deliverable:** `21.liquidty+supply-v7.1-ict.pine` (new file, from `20.liquidty+supply-v7.0-ict.pine`).
Files 1–20 untouched on disk. Architecture, module order, UDTs, `f_setupAdvance` / `f_grade` /
`f_score` / `f_prod` structure and every existing hard gate preserved.

**Measured budget.** v7.0 = 31 578 source tokens ≈ 98 459 compiled.
v7.1 = **32 029 source tokens ≈ 100 000 compiled** of the 100 256 CE10117 cap (**256 predicted spare**).
Model `compiled ≈ 3.418 × tok − 9 475`, which over-predicts by a consistent +52 on all three real
TradingView results (file 14 → 99 792 vs 99 740 · file 17 → 108 682 vs 108 630 · file 19 → 100 504 vs
100 451), so the expected true figure is **≈ 99 948, about 308 spare**.
Main body 1 762 statements — CE10295 not in play.

Verification run after every patch: whole-file bracket balance (net 0, never negative), orphan
continuation-line scan, dead-identifier scan, unused-input scan. All clean.

---

## A · SECTIONS MODIFIED

| # | Section / function | Change |
|---|---|---|
| 1 | Header, `indicator()` | v7.0 → v7.1 |
| 2 | MODULE 1 inputs · `grpE` | `poiBindAtr` re-defaulted + re-read as containment · **new:** `poiMaxAge`, `dispBodyAtr`, `apMaxTouch` |
| 3 | MODULE 1 inputs · `grpS` | **new:** `trapElite` |
| 4 | MODULE 1 inputs · `grpMaster` | **removed:** `confirmOnly` (dead in v7.0 — see A9) |
| 5 | Constants | **new:** `OTE_M`, `DISP_HOLD_FRAC` · `POI_LEAVE_ATR` 0.00 → 0.10 · **removed:** none |
| 6 | `type Setup` | **new fields:** `oteQ`, `fvgTouches`, `inGap`, `dispOutRng` · **removed:** `oteOk` (was a second name for `oteQ > 0`) |
| 7 | `f_setupReset` | four new clears, one removed |
| 8 | `f_inOte` | returns an OTE **band class** (int) instead of a bool |
| 9 | `f_setupAdvance` · invalidation | **new:** displacement-reversal kill |
| 10 | `f_setupAdvance` · stage 3→4 | binding is containment · zone age filter · three-key POI ranking |
| 11 | `f_setupAdvance` · stage 5→6 | four displacement requirements · dealing-range flag |
| 12 | `f_setupAdvance` · stage 6→7 | `dispOutRng` cleared with the displacement it described |
| 13 | `f_setupAdvance` · stage 7→8 | discrete FVG touch counter · graded OTE |
| 14 | `f_trapQual` | unchanged · **new sibling** `f_trapElite` |
| 15 | Trap engine globals + both fire sites | **new:** `trapEl` |
| 16 | `f_prod` · trap branch | elite trap → tier 1, admitted in every entry mode, `+` suffix on the tag |
| 17 | `f_grade` | signature `bool oteOk` → `int oteQ` + `bool apTouch` + `bool elite`; A+ rung rewritten |
| 18 | `f_score` | signature `bool oteHit` → `int oteQ` + `bool dispOut`; OTE and displacement terms re-graded |
| 19 | MODULE 15 ingredients + both `f_score` / `f_grade` / `f_reason` call sites | band class, touch cap, elite flag |
| 20 | MODULE 19 debug panel | prints `oteQ/touches` instead of a bare OTE tick |

---

## B · THE FOUR FIXES

### B1 — POI BINDING IS CONTAINMENT (highest priority)

**Was.** `s.liqExt <= zt + poiBindAtr * atr and s.liqExt >= zb - poiBindAtr * atr`, with
`poiBindAtr` defaulting to **2.0**. That is a proximity test: any array whose nearest edge fell
within two ATR of the raid wick could be bound as "the POI at the raid". Two ATR from the wick is a
different trade wearing this one's reason — the exact confluence-for-causality substitution §2 names,
surviving one level below where v7.0 fixed it in `f_gradeZone`.

**Is.** `poiBindAtr` is re-titled and re-defaulted to **0.15** as the slack allowed *outside* the
array, so the zone effectively has to hold the wick that took the pool. 0.0 = literal containment;
setting it back to 2.0 reproduces v7.0 exactly. One input rather than two, and the same tightening
propagates to the three other places that were proximity tests for the same reason
(`f_gradeZone`, `f_atHtfPoi`, the zone-creation provenance stamp).

**Age.** `bar_index - z.bornBar <= poiMaxAge` (default 80) joins the `live` predicate. A zone that has
sat on the chart for hundreds of bars has been traded through and re-priced many times over, whatever
its live tier still reads.

**Ranking.** `zw = z.tier * 10 + f_paRank(z.pa)` → `z.tier * 100 + f_paRank(z.pa) * 10 + z.state`.
Tier first, then the PD-array ladder (`f_paRank`: OB 0 · breaker 1 · IFVG 2 · BPR 3 · **raw FVG 4** ·
mitigation 5), then how little of the array has been eaten. v7.0 ranked the first two and broke every
remaining tie on array order.

**Leaving it.** `POI_LEAVE_ATR` 0.00 → 0.10, so "the displacement left the POI" means it cleared the
edge rather than closed on it.

### B2 — DISPLACEMENT HAS FOUR REQUIREMENTS

**Was.** `dsp and past and away` — the chart-wide displacement marker, a close past the MSS level, a
close outside the POI (by zero).

**Is.**

| Requirement | Code | Control |
|---|---|---|
| Body | `body >= dispBodyAtr * atr` | **`dispBodyAtr`, new input, default 1.3** |
| Beyond the MSS level | `past` | unchanged |
| Outside the POI | `away` | `POI_LEAVE_ATR` 0.10 |
| Holds into the close | `(close - low)/range >= DISP_HOLD_FRAC` | `DISP_HOLD_FRAC` = 0.55 |

`dispBodyAtr` sits on top of the chart-wide `dispFactor` (1.2) — it is the stage-6 requirement, not
the marker. `hold` is what rejects the candle that expands and hands it straight back inside the same
bar: a bullish "displacement" closing in the lower half of its own range is a liquidity grab wearing
a big body. Its own block reason is reported: `weak displacement — closed back inside its own range`.

**Reversal.** New invalidation: while the setup is at `ST_DISP` waiting for its gap, a close back
through `s.mssLvl` kills it (`displacement reversed back through the MSS level`). v7.0 let that setup
carry on and hand its FVG to the entry stage.

**Dealing range.** `s.dispOutRng := rangeOK and (isL ? close > rngHi : close < rngLo)` — *preferred*,
never required, and paid out of the **same six trigger points** as a double-size body, so the TRIGGER
block stays capped at 20 and no confluence is double-counted.

### B3 — THE TRAP ENGINE CAN REACH TIER 1

**Was.** `ti := pa1 and trapQ >= RQ_B ? 2 : 3`, behind `allowAll`. A trap could never clear the
default `minTier = 2` into a live tier-1 POI, could never reach the A+ rung (`f_grade` demanded
`mach and narr`), and did not exist at all in the two stricter entry modes.

**Is.** `f_trapElite` — all five ingredients at once: tracked liquidity broken (`wPool`), a shallow
overshoot (`pen <= 1.0`), a reclaim inside `trapReclMax` bars, a decisive reclaim close, and a
displacement body. That set forces `f_trapQual` to `RQ_A` and is a complete causal chain — raid,
failure, reclaim, delivery — so an elite trap gets:

- **tier 1** (`ti := pa1 and trapEl ? 1 : …`),
- **admission in every entry mode**, `Narrative only` included
  (`else if (allowAll or (trapEl and pa1)) and (pa1 or pa2) and cg`),
- **A+ eligibility** (`((mach and narr) or elite)` in `f_grade`),
- a `+` suffix on its chart tag so an elite trap is visually distinct.

Everything else still applies: the confluence chronology gate `cg` (raid < MSS ≤ displacement, all
live), the grade-A **raid** requirement on the A+ rung, RR, room, dedupe. Ordinary ① traps and ②
are unchanged and still need `All engines`. `trapElite` OFF restores v7.0 exactly.

### B4 — LATE ENTRY AND OTE ARE GRADED

**Touches.** `s.fvgTouch` stamped only the first entry. `s.fvgTouches` now counts **discrete**
entries — inside the gap this bar having been fully outside last bar — via `s.inGap`. `lateBars`
still runs off the first touch (unchanged hard gate); the *count* is what the A+ rung reads:
`prodX > PR_MACH or Xs.fvgTouches <= apMaxTouch` (**`apMaxTouch`, new input, default 2**). Third touch
onward the entry still prints, capped at grade A.

**OTE.** `f_inOte` returned a bool, so a 63 % retracement and a 92 % one paid the same 4 points and
were equally A+ eligible. It now returns a band class:

| Class | Band | Score | Grade |
|---|---|---|---|
| 1 | 62–70 % | **4** | A+ eligible |
| 2 | 70–79 % | **2** | **A max** |
| 3 | > 79 % | **1** | **never A+** |
| 0 | < 62 %, or the leg origin is broken | 0 | A+ only if `oteNeedAp` is OFF |

Both caps hold even with `oteNeedAp` OFF — that switch forgives *not reaching* the OTE, it does not
promote a retracement that ran too deep (`oteNeedAp ? oteQ == 1 : oteQ <= 1`). A non-machine producer
has no impulse leg, so the chart reading enters at class 2: fully tradable and fully scored, never on
its own the basis of an A+.

---

## C · PRESERVED

Every hard gate is untouched and still evaluated in the same order: `hNarr` `hSl` `hTgt` `hRr`
`hRoom` `hDedup` `hTier` `hCong` `hRun` `hGrade` `hScore`, arbitration, and the consumption block.
`f_narrOk`'s chronology re-derivation, the pool lifecycle and raid grading, `FVG_OWN_MAX` ownership,
the dedupe trio + V5.5-E7 price/recency guard, `f_sl` / `f_tp`, the reversal preconditions, the
`confirmed` gating discipline and the V5.6-L12 single-reset discipline are all as shipped in v7.0.
Every new read is on a confirmed bar, off already-closed data — nothing added repaints.

---

## D · UNRELATED EXISTING ISSUE — FOUND AND REMOVED

`confirmOnly` (grpMaster) was **declared and never read** in v7.0: `confirmed = barstate.isconfirmed`
is unconditional, and the preview its tooltip described is the separate `showDev` toggle. It was
removed rather than wired, because wiring it would mean permitting intrabar state — which the brief
forbids. The behaviour it claimed to control is, and always was, the behaviour. This is the only
v7.0 element removed in v7.1.

---

## E · EXPECTED EFFECT

Fewer signals, materially better ones. The four changes attack the same defect from four sides —
each one removes a way for a setup to *look* complete without *being* caused.

| Change | Effect on signal count | Effect on quality |
|---|---|---|
| POI containment (2.0 → 0.15 ATR) | **Largest single reduction.** Kills the POI stage for every raid that had no array actually at it | Removes the class where the whole narrative downstream was built on a borrowed POI |
| Zone age ≤ 80 bars | Small | Stops stale, many-times-mitigated arrays being bound |
| Displacement body 1.3 × + hold 0.55 + reversal kill | Moderate | Removes the "big candle that gave it straight back" false stage 6 — the most common source of an entry into a gap that never gets respected |
| A+ ≤ 2 touches · OTE band caps | **No change to count** | Pure re-labelling: A+ stops being handed to late, deep, mitigated entries. The A+ population shrinks and gets cleaner; those entries print as A |
| Elite trap → T1 / A+ / all modes | **Adds** signals, especially in `Narrative only` | Adds only the five-ingredient trap, which carries a complete causal chain of its own |

Net: expect the machine producer to fire noticeably less often, with the surviving entries far more
often sitting in an array that genuinely holds the raid; expect the A+ label to become rare and to
mean what it says; and expect the trap engine to contribute a small number of high-conviction signals
in modes where it previously contributed none.

**Tuning back toward v7.0** if the count is too thin: `poiBindAtr` 0.15 → 0.5–2.0 first (largest
lever), then `dispBodyAtr` 1.3 → 1.2, then `poiMaxAge` up, then `apMaxTouch` up. `trapElite` OFF
removes the one addition.

---

## F · TEST MATRIX

| # | Check | Expect |
|---|---|---|
| 1 | Compiles on TradingView | ≈ 99 950 of 100 256 |
| 2 | Debug panel row 16 | `…×ATR n ago · <band>/<touches> · ✓/✗ · VALID` |
| 3 | Set `poiBindAtr` 0.15 → 2.0 | Signal count returns toward v7.0 |
| 4 | Set `dispBodyAtr` to 0.5 | Displacement gate inert (chart-wide `dispFactor` binds) |
| 5 | Force a weak displacement | Block reason `weak displacement — closed back inside its own range` |
| 6 | Displacement then close back through MSS | Setup dies, reason `displacement reversed back through the MSS level` |
| 7 | Third touch of the execution FVG | Entry prints as **A**, never A+ |
| 8 | Retest at 75 % of the leg | POI score 2 not 4, grade capped at A |
| 9 | Retest at 85 % of the leg | POI score 1, never A+ |
| 10 | `Narrative only` + an elite trap | Trap prints with a `+` tag, tier 1 |
| 11 | `Narrative only` + an ordinary trap | Nothing (unchanged) |
| 12 | `trapElite` OFF | Trap behaviour identical to v7.0 |
| 13 | Alignment score | Still ≤ 100; TRIGGER ≤ 20 and POI ≤ 20 with the new terms |
