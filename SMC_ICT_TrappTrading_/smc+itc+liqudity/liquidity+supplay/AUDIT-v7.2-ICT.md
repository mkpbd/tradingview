# AUDIT v7.2 — FORENSIC FIX PASS

**Deliverable:** `22.liquidty+supply-v7.2-ict.pine` (new file, from `21.liquidty+supply-v7.1-ict.pine`).
Files 1–21 untouched on disk. The audit that produced it is `AUDIT-v7.1-FORENSIC.md`.

**Scope.** Pure defect repair. No module added, none removed. **No input added, none removed** —
one input (`needSweep`) retitled and re-defaulted. Every UDT, every state machine, every hard gate,
`f_setupAdvance` / `f_narrOk` / `f_prod` / `f_grade` / `f_score` / `f_sl` / `f_tp` structure preserved.

**Measured budget.**

| | source tok | predicted | true (−52 bias) | spare of 100 256 |
|---|---|---|---|---|
| v7.1 (file 21) | 32 029 | 100 000 | 99 948 | 308 |
| v7.2 after fixes, before reclaim | 32 120 | 100 311 | **100 259** | **−3 · would not compile** |
| **v7.2 shipped** | **32 052** | **100 079** | **≈ 100 027** | **≈ 229** |

Model `compiled ≈ 3.418 × tok − 9 475`, re-validated this session against both real TradingView
errors (file 14 → 99 792 vs 99 740 · file 17 → 108 682 vs 108 630; constant +52).
Main body 1 741 — CE10295 not in play.

Verification after every patch: whole-file bracket balance (net 0, never negative) · orphan
continuation-line scan · dead-identifier scan · unused-input scan · full comment-stripped diff
reviewed hunk by hunk (46 hunks, all intended). **All clean.**

> **Pine cannot be compiled locally.** These are measurements against a model validated on three
> real TradingView errors, not a compile. The one construct I cannot verify offline is the
> qualifier inference on `f_tfUp` — see §D.

---

## A · THE EIGHT FIXES

### A1 · BUG-01 — FUTURE DATA THROUGH A LOWER-TIMEFRAME REQUEST · **P0**

**Was.** Six `request.security` calls, all `lookahead = barmerge.lookahead_on`, all correctly
returning `[1]`-indexed expressions — and **nothing constraining the requested timeframe to be at or
above the chart timeframe.** `f_bias` is called unconditionally at 5/15/60/240/D; `htfSel` and
`htfCtxSel` offer 15/30/60/240/D with no relation check.

`lookahead_on` is only safe on a series already fixed at the chart bar's open. That is true of a
closed *higher* bar. On a *lower* timeframe it returns the value from the **end** of the current
chart bar, and the `[1]` inside the requested expression steps back one bar of the **requested**
series, not one chart bar. On a 4H chart, `b5` leaks ~47 five-minute bars of intrabar future.

This is not cosmetic: `biasFilter` → `filtBias` → `baseLongOK`/`baseShortOK` is a **hard gate**, and
`htfTf`/`htfCtxTf` drive HTF structure, HTF liquidity registration (`PK_HTF`), the FEM POI and the
state machine's stage-1 context gate.

**Is.**

```pine
f_tfUp(simple string tf) => timeframe.in_seconds(tf) < timeframe.in_seconds() ? timeframe.period : tf
htfTf    = f_tfUp(htfSel    == "Auto" ? f_autoHtf() : htfSel)
htfCtxTf = f_tfUp(htfCtxSel == "Auto" ? f_autoHtf() : htfCtxSel)
f_bias(simple string tf) =>
    request.security(syminfo.tickerid, f_tfUp(tf), f_biasSrc(), lookahead = barmerge.lookahead_on)
```

One helper, three application points, and every one of the ten timeframe requests in the file is
covered. `f_autoHtf()` was already always ≥ the chart, so **Auto behaviour is bit-identical to v7.1**.
A dashboard row below the chart timeframe now reports the chart's own bias instead of a leaked one —
honest, and the row is labelled with the timeframe the user asked for, which is the one cosmetic
compromise in this pass.

### A2 · BUG-02 — THE CONFLUENCE PRODUCER'S POI IS NOW BOUND TO ITS RAID · **P0**

**Was.** v7.1 tightened POI binding to containment in three places — the machine's stage 3→4,
`f_gradeZone`, `f_atHtfPoi` — and left the fourth. The S/D producer took the *global* most-recent
raid on its side (`anyExt`, `anyRq`, `anyId`) and attached it to a zone chosen with **no spatial
reference to that raid at all**. The only link was `confGateLong`, a time-ordering of global flags.
And this is the one producer whose narrative gate is disabled: `hNarrL = prodL > PR_MACH or narrLong`.

Consequences: the stop (`psl := anyExt`) was written at an unrelated raid's wick whenever it happened
to fall inside the risk clamp; the grade-A rung was reachable on an unrelated raid's grade
(`(not mach or narr) … rq >= RQ_B`); and the printed reason asserted a causal chain nobody checked.

**Is.** Containment required at the one site both sides pass through:

```pine
else if allowConf and sdC and cg and (not needSweep or (not na(sdZ)
     and anyExt <= sdZ.top + poiBindAtr * atr and anyExt >= sdZ.bot - poiBindAtr * atr))
```

Same test, same slack (`poiBindAtr`, 0.15 ATR outside the array) as the machine's stage 3→4. The
existing `needSweep` input is repurposed as the switch and re-defaulted **ON**:
*"S/D producer: the zone must CONTAIN the raid extreme."* `needSweep = false` reproduces v7.1 exactly.
No second input was added — the budget forbade it and the existing one was the right name for the job.

**This is the largest behavioural change in v7.2 and the largest expected reduction in signal count.**

### A3 · BUG-03 — ZONE TIER 1 NO LONGER BUYS THE GLOBAL CHART OTE · **P1**

`f_gradeZone`'s tier-1 rung read `(ote or (isSupply ? premOK : discOK))` where
`ote = isSupply ? inOTEsell : inOTEbuy` — the **chart-wide** dealing-range OTE, exactly what §15
forbids. It was also *dead as a disjunct*: the OTE band is a subset of the half `premOK`/`discOK`
already requires, so it could only fire when the alternative had already fired.

Removed, along with its declaration. Tier 1 now needs liquidity containment + displacement + an
ordered MSS + HTF agreement + the correct half of the range. **Token-negative.**

### A4 · BUG-04 — `retBeforeFail` WAS TRUE ON THE VERY BAR THAT READ IT · **P1**

```pine
if high >= bot            // any touch — including the breaking bar
    z.retBeforeFail := true
...
if close > top            // the break
    f_zoneFlip(z, false, z.retBeforeFail and z.liqBeforeFail and dispUpBar and …)
```

A bar closing above `top` necessarily has `high >= bot`. The flag was **unconditionally true** at
every flip, so BREAKER classification had two live requirements instead of three, and zones never
revisited before being run through were promoted to BREAKER (tier 2, PD-array rank 1) instead of
MITIGATION (tier 3, rank 5).

**Is.** `z.touchBar` already records the *first* touch and only the first (`if z.state == 0`), and it
is reset by `f_zoneFlip`. The test is now `z.touchBar >= 0 and z.touchBar < bar_index` — price
entered the zone on an **earlier** bar. The field, its two assignments and its reset were deleted.

### A5 · BUG-05 — AN UNOWNED DISPLACEMENT NO LONGER UPGRADES THE RAID GRADE · **P1**

`f_poolScan`'s reaction branch promoted `p.rq` from `RQ_C` to `RQ_B` on a **global**
displacement/structure flag inside `reactWin`. `rq` is supposed to describe the raid candle itself
(depth × rejection), and `rq >= RQ_B` is the grade-A rung's own requirement. A one-tick wick that
closed back weakly became grade-A eligible because an unrelated bar displaced within six bars — and
its LIQUIDITY score block went from 4 points to 8.

The line is deleted. The pool still advances to `PS_REACT` on that evidence — *state* is a statement
about what happened after the raid; *grade* is a statement about the raid. **Token-negative.**

### A6 · BUG-06 — THE ELITE TRAP'S A+ PATH WAS UNREACHABLE, THEN INVERTED · **P1**

v7.1's headline claim was that an elite trap reaches tier 1, fires in every entry mode, **and is A+
eligible**. The first two were true in the code. The third was not:

```pine
oteQL = prodL <= PR_MACH ? upS.oteQ : inOTEbuy ? 2 : 0        // trap ⇒ oteQ ∈ {0, 2}
… and (oteNeedAp ? oteQ == 1 : oteQ <= 1)
```

Class 1 is only ever written by `f_inOte` on a setup's own impulse leg, which a trap does not have.
So with `oteNeedAp` **ON (the default) an elite trap could never be A+**; with it OFF the test became
`oteQ <= 1`, which **disqualified a trap that was in the OTE and admitted one that was not** —
backwards.

**Is:** `(elite ? oteQ >= 1 : oteNeedAp ? oteQ == 1 : oteQ <= 1)`. An elite trap must sit in the
chart OTE — the only OTE statement available to a producer with no leg — rather than being punished
for it. The machine path is untouched in both switch positions.

### A7 · BUG-07 — THE TRAP'S "TRACKED LIQUIDITY" TEST NOW TESTS THE BROKEN LEVEL · **P1**

`trapNeedPool` promises *"the broken level must be TRACKED liquidity"*. v7.1 tested `poolBrkUp` —
"**some** buy-side pool closed through on this bar" — and never compared it with `brkUpLvl`, the
structure level that actually armed the trap. `wPool` is the first of the five ingredients in both
`f_trapQual` and `f_trapElite`, and `f_trapElite` grants tier 1, admission in `Narrative only`, and
A+ eligibility.

**Is.** The registry loop already writes `brkUpKind`/`brkDnKind`; it now also writes the price, and
two globals say it properly at registry tolerance:

```pine
tPoolU = poolBrkUp and math.abs(brkUpPx - brkUpLvl) <= lqTol
tPoolD = poolBrkDn and math.abs(brkDnPx - brkDnLvl) <= lqTol
```

Both the arming gate and `wPool` read these. (`na` guards are unnecessary: `math.abs(na − x)` is `na`
and `na <= lqTol` is `false`, so the test fails safe.)

### A8 · BUG-10 — DUPLICATE ALERTS REMOVED · **P3**

`[SIGNAL] Trade Engine LONG` had the identical condition to `[SIGNAL] Any LONG` (`finalLong`); same
for SHORT. Two alerts fired for one event. Removed — **token-negative**, and it helped pay for A1.

---

## B · THE RECLAIM — 68 SOURCE TOKENS, ZERO BEHAVIOUR

The eight fixes landed at **−3 spare**, i.e. the file would not have compiled. Rather than drop a
fix, seven groups of **pure aliases** were eliminated. Every name removed was a second spelling of an
expression already in scope; every call site now names the original. Nothing was removed, nothing
merged, no feature touched.

| # | Removed | Replaced by | Sites |
|---|---|---|---|
| R1 | `bosBull` `bosBear` `chochBull` `chochBear` `cisdBull` `cisdBear` | `bosUp` `bosDn` `chochUp` `chochDn` `cisdUp` `cisdDn` | 3 alertconditions |
| R2 | `mssUp` `mssDn` | `mssBull` `mssBear` | TWS resolution, run reversal |
| R3 | `rrBn` (was literally `= rrB`) | `rrB` | 8 |
| R4 | `allowMach` (was literally `= true`) | dropped from `if allowMach and mach` | 1 |
| R5 | `lvlPoiL` `lvlPoiS` | `poiBotL` `poiTopS` | 2 `f_sl` calls |
| R6 | `hSlL` `hSlS` | `slOkL` `slOkS` | `okLong`/`okShort` + both `f_blockReason` calls |
| R7 | redundant `na` guards in `tPoolU`/`tPoolD` | — | 2 |

`rrAn` and `rrAPn` are **not** aliases (they are real `math.max` clamps) and were left alone.

---

## C · RE-AUDIT OF THE NEW CODE (§38)

| Check | Result |
|---|---|
| **Logic** | No contradictions introduced. Each fix either deletes a condition that was provably always-true/always-dead, or adds a test that is a copy of one already applied elsewhere in the same file. |
| **Causality** | The confluence producer now requires spatial containment in addition to `cg`'s ordering. The machine path is unchanged and still re-derives its whole chain in `f_narrOk`. Event ownership for `PR_TRAP` improved via A7; it still reads the global raid for `rq`/`kind` — **stated limitation, see §F**. |
| **Repainting** | The only defect (A1) is closed. All six `request.security` calls keep the `[1]` + `lookahead_on` idiom and are now guaranteed to be at or above the chart timeframe. No new `request.security`, no new historical reference, no new `[n]` on a forward-looking series. Every added read is on a confirmed bar off already-closed data. |
| **Structure** | BOS / CHoCH / MSS / CISD remain fully separate. R1/R2 removed *alias names only*; `mssBull = chochUp or cisdMssUp` and the `mssNeedDisp` promotion gate are byte-identical. |
| **Liquidity** | The raid belongs to its pool as before; A5 stops the grade being written by anything other than the raid candle. Registration, fusion, lifecycle, pruning, trendline-on-sweep-only: untouched. |
| **POI** | Containment now holds on **all four** paths — machine stage 3→4, `f_gradeZone`, `f_atHtfPoi`, and (new) the S/D producer. |
| **Entry** | Entry location logic unchanged. The S/D producer fires strictly less often and only where its zone holds its raid. |
| **Timing** | `lateBars`, `fvgTouches`/`inGap`, `apMaxTouch`, `retestWin`, the ST_ENTRY→ST_FVG retry with `fvgTouch` preserved: all untouched. No stale or late entry becomes reachable. |
| **Risk** | `f_sl`'s hierarchy and clamps are untouched; A2 improves *what is fed to it* on the S/D path (the raid is now at the zone). R5 is a rename only. |
| **Target** | `f_tp` and `f_oppLiq` untouched. R3 is a rename only — `rrBn` was `rrB`. |
| **Performance** | Net **−14 code lines**, two fewer global series, two fewer alertconditions, one new tiny function and two new global bools. No new loop, no new object, no new `request.security`. |
| **Alerts** | Two duplicates removed. Every surviving alert still corresponds to the same chart condition it did in v7.1; the three retargeted `[TRIG]` alerts fire on the identical expressions under their original names. |
| **Scanners** | brackets 0 · orphan continuations 0 · dead identifiers 0 (excluding the two deliberate call-once sinks `tlN`, `poolFlush`) · unused inputs 0. |

---

## D · THE ONE THING I CANNOT VERIFY OFFLINE

`f_tfUp(simple string tf) => …` must return a **`simple string`** for `request.security`'s
`timeframe` argument. The inference chain is: `timeframe.in_seconds(simple string) → simple int`;
comparison of two simples → simple bool; ternary over `timeframe.period` (simple string) and `tf`
(simple string) → simple string. This is the standard pattern and should be accepted.

**If TradingView rejects the qualifier**, the one-line fallback is to drop the `f_bias` wrap (leaving
the two `htfTf`/`htfCtxTf` clamps, which are evaluated once at global scope from input-qualified
values) and instead neutralise the bias filter when it points below the chart:
`filtBias := timeframe.in_seconds(biasFilter) < timeframe.in_seconds() ? 0 : filtBias`. That closes
the hard-gate leak and leaves only the dashboard rows cosmetic. It costs about the same.

---

## E · CHANGELOG (§39)

| Module | Old problem | Fix | Trading impact | Pri |
|---|---|---|---|---|
| 6 HTF context | `request.security` + `lookahead_on` to a timeframe **below** the chart leaked intrabar future data into a hard gate | `f_tfUp` clamps every requested tf up to the chart | Removes the class of backtest-only signals that cannot exist live. Auto mode unchanged | **P0** |
| 15 `f_prod` · 1 inputs | S/D producer inherited the most recent raid on its side with no spatial relation to the zone it traded | Containment required (`poiBindAtr` slack); `needSweep` retitled + defaulted ON | **Largest reduction in signal count.** Kills the confluence entry whose stated reason, stop and grade came from an unrelated raid | **P0** |
| 9 `f_gradeZone` | Tier 1 partly bought with the global chart OTE (also a dead disjunct) | Term and declaration deleted | Fewer, better tier-1 zones; `minTier`, POI score and the A+ `tier == 1` rung all get cleaner input | P1 |
| 9 zone lifecycle | `retBeforeFail` was true on the bar that read it | `touchBar >= 0 and touchBar < bar_index`; field deleted | BREAKER stops being handed to zones never revisited before the break. More MITIGATION, fewer false rank-1 arrays | P1 |
| 7 `f_poolScan` | Unowned displacement promoted a grade-C raid to grade B | Promotion deleted; state still advances | Removes a route by which a one-tick wick reached grade A and +4 liquidity score | P1 |
| 15 `f_grade` | Elite-trap A+ unreachable at default, inverted when `oteNeedAp` was off | `elite ? oteQ >= 1 : …` | The advertised capability now exists, and requires the trap to be in the OTE rather than punishing it for being there | P1 |
| 11 trap arming | `trapNeedPool` never compared the broken pool with the level that armed the trap | `tPoolU`/`tPoolD` at registry tolerance | Elite traps get materially rarer and genuinely sit on crowded liquidity | P1 |
| 20 alerts | Two alertconditions duplicated "Any LONG"/"Any SHORT" | Deleted | One event, one alert | P3 |

### PRESERVED

Every hard gate, in the same order: `baseOK` `hNarr` `slOk` `hTgt` `hRr` `hRoom` `hDedup` `hTier`
`hCong` `hRun` `hGrade` `hScore`, arbitration, consumption. `f_narrOk`'s chronology re-derivation.
The nine-state machine and its single-instance-per-direction design. The pool lifecycle, raid
definition and grading. Trendline-liquidity-on-sweep-only. `FVG_OWN_MAX` ownership. The dedupe trio
plus the V5.5-E7 price/recency guard. `f_sl` / `f_tp` and the opposing-liquidity clamp. The four-part
displacement test and the displacement-reversal kill. Leg-based banded OTE. `lateBars` /
`apMaxTouch`. The `confirmed` gating discipline. Dashboard, debug panel and every remaining alert.

### REMOVED

Four always-true / always-dead expressions (`ote` disjunct, `retBeforeFail`, the `RQ_C→RQ_B`
promotion, the duplicate alert pair) and thirteen pure aliases. **No feature, no module, no input.**

### ADDED

`f_tfUp` (1 line) · `brkUpPx` / `brkDnPx` (2 declarations, 2 writes inside an existing loop) ·
`tPoolU` / `tPoolD` (2 lines). Six lines of new executable code in total.

### REMAINING LIMITATIONS — stated honestly

1. **Congestion is still counted twice** (score debit in `f_score` *and* a grade downgrade in
   `f_grade`), and `RG_CHOP` is still unreachable when `congGate = "Off"` because `congested`
   carries the gate switch inside it. Over-punishment, not a false signal. Deferred: it changes
   published score semantics and needs its own pass.
2. **EQH/EQL and swing pools are registered `pivLen` bars late** and the registry never looks back,
   so a raid inside the pivot's own confirmation window is invisible and the level is displayed as
   resting after it has been taken. A backfill scan is ~200+ source tokens; not affordable at 229.
3. **`PR_TRAP` and `PR_SD` still read `rq` / `rkind` / `mssBar` / `dispBar` from the global
   most-recent values.** A2 fixes the *spatial* hole on the S/D path; the *grade* still comes from
   the pool's own raid record, which is now at least the pool the zone holds. The trap path's raid
   is still the global one.
4. **Trap producer ② is dead at the default `minTier = 2`** — it never writes `trapQ` or `paSl`, so
   it is capped at tier 3 and carries no trap-specific stop. Honest, and left alone deliberately.
5. **A structural break can be double-counted** in `f_structUpdate` (the CHoCH-through-`protLo`
   branch leaves `loBroken = false`, so a later BOS-down can fire on the same leg). No gate reads
   `evBar` twice, so the impact is on the event stream, not on entries.
6. **PD-array ranking is applied to the machine's POI selection only**, not to the S/D producer,
   which still picks by tier then array order.
7. A dashboard bias row for a timeframe below the chart now shows the **chart's** bias under the
   requested row's label. Honest data, slightly misleading label.
8. **Pine cannot be compiled locally.** The budget is a validated model, not a compile. Predicted
   ≈ 100 027 of 100 256.

---

## F · FINAL OPERATOR REVIEW (§40)

### TOP 10 LOGICAL WEAKNESSES (of v7.1; ✅ = fixed in v7.2)

1. ✅ Lower-timeframe `request.security` + `lookahead_on` feeding a hard gate.
2. ✅ Confluence producer's zone had no spatial relation to the raid it claimed.
3. ✅ `retBeforeFail` always true at the bar that read it.
4. ✅ Raid grade promoted by an unowned displacement.
5. ✅ Zone tier 1 partly bought with the global chart OTE.
6. ✅ Elite-trap A+ unreachable, and inverted with `oteNeedAp` off.
7. ✅ `trapNeedPool` never tested the level that armed the trap.
8. ⬜ Congestion penalised twice, and `RG_CHOP` coupled to the gate switch.
9. ⬜ Pool registration lags the pivot by `pivLen`; no retroactive raid scan.
10. ⬜ `hNarr` is structurally bypassed for every non-machine producer — by design, but it means the
    whole causal burden on those paths rests on `cg` plus (now) containment.

### TOP 10 FALSE-SIGNAL SOURCES

1. ✅ Unrelated raid → unrelated zone → "DEMAND T2" confluence entry (the big one).
2. ✅ Grade-C wick inflated to grade B, then to grade A.
3. ✅ BREAKER promotion of a zone never revisited before the break.
4. ✅ Elite trap armed on a coincidental pool break elsewhere on the bar.
5. ✅ Tier-1 zones minted because price sat in the chart-wide OTE box.
6. ✅ Backtest-only signals from leaked lower-timeframe bias.
7. ⬜ Chop double-penalty makes the *grade* the effective filter, so `minGrade` is doing more work
    than the operator thinks.
8. ⬜ A level already taken during a pivot's confirmation window is still shown and targeted as
    resting liquidity.
9. ⬜ `strongUp`/`strongDn` alone can pay for a CISD→MSS promotion when `dispUpBar` is false.
10. ⬜ `legHi`/`legLo` extend through `ST_RAID…ST_DISP`, so a pre-MSS spike makes OTE read shallower
    than it is (conservative — it costs signals, it does not create them).

### TOP 10 ENTRY-QUALITY IMPROVEMENTS IN THIS PASS

1. The confluence entry must now stand in the array that holds its raid.
2. `needSweep` ON by default — the confluence path is no longer the loose one.
3. Tier 1 means liquidity + displacement + ordered MSS + HTF + correct half of the range. Nothing else.
4. BREAKER now requires an actual prior return into the zone.
5. Raid grade means what the raid candle did.
6. The elite trap must stand on the level it broke.
7. The elite trap's A+ requires the OTE instead of forbidding it.
8. HTF context, HTF POI and HTF liquidity can no longer be built from future data.
9. The bias filter can no longer gate entries on future data.
10. One event, one alert.

### TOP 5 REPAINTING RISKS — after v7.2

1. ~~Lower-timeframe request with `lookahead_on`~~ — **closed**.
2. `newHtfBar` fires one HTF bar late by design (`hT = time[1]`); HTF pools register one HTF bar
   after the swing is confirmed. Correct, but the operator should know the lag exists.
3. Session extremes track live inside a session. That is live data, not future data, but the drawn
   line moves until the session closes.
4. `barstate.islast` blocks (marking layer, dashboard, HTF POI boxes, OTE box, next-zone labels)
   redraw every tick. Display only, no state, no alert.
5. `showDev`'s `⋯` preview is deliberately unconfirmed and can vanish. Intended; no alert attached.

### TOP 5 LIQUIDITY IMPROVEMENTS STILL AVAILABLE

1. Retroactive raid scan over the `pivLen` confirmation window at registration (limitation 2).
2. Let the machine's `f_findRaid` prefer a pool whose `srcPoolId` a live zone already stamps.
3. Read the four `src*` provenance fields on `Zone` — they are written and never consulted.
4. Give session pools the same `PS_REACT` reaction grading the swing pools get.
5. Give `PK_TL` a slope-quality term so a near-vertical two-pivot line cannot become liquidity.

### TOP 5 SMC / ICT IMPROVEMENTS STILL AVAILABLE

1. Stop the double-counted structural break in `f_structUpdate` (limitation 5).
2. Freeze `legHi`/`legLo` at the MSS bar so the impulse leg is the displacement leg only.
3. Require `dispUpBar` (not `strongUp`) for the CISD→MSS promotion when `mssNeedDisp` is on.
4. Apply the PD-array ranking to the S/D producer's zone choice.
5. Represent a BPR as the overlap region rather than re-tagging the survivor.

### TOP 5 TRAP IMPROVEMENTS STILL AVAILABLE

1. Give producer ② a quality grade and a stop, or retire it explicitly.
2. Let the trap re-arm on a new break instead of waiting for `maxAfterBrk`.
3. Grade the reclaim by *how far past* the level it closed, not just `NEAR_LVL_ATR`.
4. Make the trap's `rq` its own `trapQ`, not the global pool's raid grade.
5. Require the reclaimed level to be the *same pool* the raid was on.

### TOP 5 SUPPLY / DEMAND IMPROVEMENTS STILL AVAILABLE

1. Make `liqBeforeFail` side-aware (a supply zone run upward wants a **buy**-side raid).
2. Use the raid **wick** (`anyLoExt`), not the pool price (`anyLoPx`), for `raidNearPx` — the rest of
   the file uses the wick.
3. On a creation-time overlap, replace the worse zone instead of losing both.
4. Age zones out of the *registry*, not just out of *binding* (`poiMaxAge` gates binding only).
5. Let an OB inherit its FVG's `state`, so a mitigated leg does not leave a "fresh" OB behind.

### TOP 5 PERFORMANCE IMPROVEMENTS STILL AVAILABLE

1. Replace `math.pow` in `f_maskAdd`/`f_maskN` with a constant lookup — the only genuinely wasteful
   primitive in the file.
2. Collapse the five `f_bias` `request.security` calls into one tuple request.
3. `f_inSes` is called 11 times; several results are only read once.
4. `f_oppLiq` runs twice per side (once for `room`, once inside `f_tp`) over the same arrays.
5. Cache `array.size(pools)` / `array.size(zones)` per bar instead of re-reading them in every guard.

---

## G · TEST MATRIX

| # | Check | Expect |
|---|---|---|
| 1 | Compiles on TradingView | ≈ 100 027 of 100 256 |
| 2 | 4H chart, `Bias filter = 5` | Behaves as the 4H bias — no signal that only exists in history |
| 3 | 4H chart, `HTF = 15` | Clamped to 4H; `htfLive` false; no `PK_HTF` pools; **no repaint** |
| 4 | Any chart, `HTF = Auto` | Bit-identical to v7.1 |
| 5 | `needSweep` OFF | S/D producer behaves exactly as v7.1 |
| 6 | `needSweep` ON (default) | S/D entries only where the zone brackets the raid wick ±0.15 ATR |
| 7 | Zone broken with no prior visit | Flips to **MITIGATION**, not BREAKER |
| 8 | Shallow wick raid + later unrelated displacement | Pool reaches `SWEPT✓REV`, raid grade stays **C** |
| 9 | Tier-1 zone count | Lower than v7.1; no tier 1 minted by the chart OTE box alone |
| 10 | Elite trap in the chart OTE, `oteNeedAp` ON | Can now print **A+** |
| 11 | Elite trap outside the chart OTE | Prints **A**, never A+ |
| 12 | `trapElite` OFF | Trap behaviour as v7.1 apart from the `tPoolU/D` tightening |
| 13 | Trap armed by a structure break with a pool broken elsewhere on the bar | Does **not** arm when `trapNeedPool` is ON |
| 14 | Alert list | Two fewer entries; "Any LONG"/"Any SHORT" remain |
| 15 | `[TRIG] Internal BOS / CHoCH / CISD` | Fire on exactly the same bars as v7.1 |
| 16 | Machine (`Narrative only`) entries | Unchanged except where a leaked HTF context previously admitted them |
