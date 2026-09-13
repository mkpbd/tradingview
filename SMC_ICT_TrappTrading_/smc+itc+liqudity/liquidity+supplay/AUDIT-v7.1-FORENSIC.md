# FORENSIC AUDIT — `21.liquidty+supply-v7.1-ict.pine`

**Method:** the executable Pine is the source of truth. Every claim below was read out of the code,
not out of the comment above it. 6 028 lines / 3 459 non-comment code lines / 32 029 source tokens.

**Verification toolchain rebuilt and re-validated first** (`pinecheck.py`): the token model
reproduces both real TradingView compile errors exactly —
file 14 → 99 792 predicted vs **99 740** real · file 17 → 108 682 vs **108 630** real (constant +52 bias).

> ## THE BUDGET IS THE BINDING CONSTRAINT
> **File 21 = 32 029 tok → ≈ 99 948 compiled of the CE10117 cap of 100 256. ≈ 308 compiled tokens spare
> (≈ 95 source tokens).** Main body 1 753 (my counter runs ~162 low vs the measured CE10295 anchors →
> real ≈ 1 915 of ~2 030). Bracket balance 0, no orphan continuations, no unused inputs, no dead
> identifiers except the two deliberate call-once sinks `tlN` / `poolFlush`.
>
> Every fix in §18 is therefore priced. A fix that cannot be paid for is listed as deferred, not
> silently dropped.

---

## 1 · ARCHITECTURE MAP

### 1.1 Actual dependency order (as executed, not as documented)

```
M1 inputs → M2 constants/helpers → M3 core series + candle anatomy (CISD, IFC)
  → M4 structure (internal sInt @pivLen · external sExt @extPiv, one shared f_structUpdate)
  → M5 sessions / killzones / SB / news / 00:00 + 08:30 opens / session H-L freeze
  → M6 HTF context  [6 request.security calls, all lookahead_on]
        f_bias ×5 (5/15/60/240/D) · f_htfCtx(htfCtxTf) · D high/low · W high/low
        · f_htfStruct(htfTf) · f_htfPoi(htfTf)
  → M7 LIQUIDITY REGISTRY  (Pool UDT · f_qPush queue → f_qFlush → f_poolScan)
        producers: EQH/EQL, swing, external swing, session H/L, PDH/PDL, PWH/PWL,
                   HTF swing (PK_HTF), trendline (PK_TL, registered ONLY on the sweep bar)
  → M8 dealing range · premium/discount · global OTE
  → M8B liquidity marking (display, last bar only)
  → M9 SUPPLY/DEMAND + FVG + OB + BPR + IFVG + breaker/mitigation + rejection blocks
  → M11 pattern producers (trap engine ① / ②) + f_atHtfPoi
  → M11B TWS · liquidity run · congestion · regime · AMD/Judas · descriptor tagging
  → M12 SETUP STATE MACHINE  (one Setup per direction: upS / dnS)
  → M13 alignment score (soft) → M14 base gates + dedupe → M14B SL / TP / opposing-liquidity
  → M15 TRADE ENGINE: f_prod (producer ladder) → risk → score → grade → 12 hard gates
        → arbitration → consumption → reason string
  → M16 emitted risk → M17 visuals → M18 dashboard → M19 debug → M20 alerts
```

### 1.2 Does the code follow the intended chronology?

**For the machine producer (`PR_FEM` / `PR_MACH`) — YES, and it is genuinely enforced.**
`f_setupAdvance` is a nine-state machine with one instance per direction, and `f_narrOk` re-derives
the whole chain independently at the gate:

```
liqId == tgtId                      ← the raid is ON the pool the setup declared as its target
liqBar  > bornBar                   ← nothing retroactive
tgtBar >= ctxBar · liqBar > tgtBar · poiBar >= liqBar
mssBar  > liqBar · mssBar  > poiBar
dispBar > mssBar · fvgBar >= dispBar · fvgBar - dispBar <= FVG_OWN_MAX
retestBar > fvgBar
```

Because there is exactly **one Setup object per direction**, cross-setup event theft is impossible
by construction on this path. That is the strongest part of the file and it should be preserved.

**For the confluence and trap producers — NO.** See §4. `hNarr` is explicitly bypassed
(`hNarrL = prodL > PR_MACH or narrLong`) and the substitute is `confGateLong`, which is a pure
time-ordering test over **global** flags with no spatial binding whatsoever.

---

## 2 · CRITICAL BUGS

---

### BUG-01 · FUTURE DATA THROUGH A LOWER-TIMEFRAME `request.security` — **P0**

| | |
|---|---|
| **Module** | 6 (HTF context) — and every consumer downstream |
| **Lines** | 2141–2142, 2157–2172, 2191, 2240, 2288 |

**Current behaviour.** Six `request.security` calls all use `lookahead = barmerge.lookahead_on`.
For a genuinely *higher* timeframe every one of them is correctly written — each returns a
`[1]`-indexed expression off already-closed HTF state, which is the canonical non-repainting idiom:

```pine
f_biasSrc()   => ... _v[1]
f_htfCtx()    => [_dir[1], _pd[1]]
f_htfStruct() => [_hi[1], _lo[1], _d[1], time[1]]
f_htfPoi()    => [bTop[1], bBot[1], sTop[1], sBot[1], bIn[1], sIn[1]]
pdh/pdl, pwh/pwl => [high[1], low[1]]
```

**Nothing in the file constrains the requested timeframe to be ≥ the chart timeframe.**

* `f_bias` is called unconditionally at `"5"`, `"15"`, `"60"`, `"240"`, `"D"`. On a 4H chart, `b5`,
  `b15` and `b60` are *lower*-timeframe requests. `lookahead_on` on a lower timeframe returns the
  value from the **end** of the current chart bar. The `[1]` inside `f_biasSrc` steps back one *5-minute*
  bar — on a 4H chart that still leaves ~47 bars of intrabar future data.
* `htfSel` and `htfCtxSel` offer `"15"`, `"30"`, `"60"`, `"240"`, `"D"` with **no relation check to
  the chart**. Set `htfSel = "15"` on a 4H chart and `f_htfStruct` / `f_htfPoi` leak the same way.

**Why it is logically wrong.** `lookahead_on` is only safe on a series whose value is already fixed
at the chart bar's open. That is true of a *closed higher* bar. It is false of a lower timeframe,
where the requested series is still being written inside the current chart bar.

**Trading consequence.**
* Historical chart: the MTF bias row and the HTF structure/POI look uncannily correct.
* Realtime: they change under the operator as the bar forms.
* At the close: they settle to a different value than the one the backtest showed.
* This is not cosmetic. `biasFilter` feeds `filtBias`, and `filtBias` is inside `baseLongOK` /
  `baseShortOK` — a **hard gate**. `htfTf` drives `f_htfStruct` (HTF liquidity pool registration
  `PK_HTF`), `f_htfPoi` (the FEM POI, `hTap`, `f_atHtfPoi`) and `htfCtxTf` drives `htfDir` / `htfPd`
  → `htfCtxLong/Short` → the state machine's stage-1 gate. Future data reaches every one of them.

**Recommended fix.** Clamp every requested timeframe up to the chart timeframe:
`f_tfUp(tf) => timeframe.in_seconds(tf) < timeframe.in_seconds() ? timeframe.period : tf`,
applied inside `f_bias` (covers all five rows and the filter) and to `htfTf` / `htfCtxTf`.

---

### BUG-02 · THE CONFLUENCE PRODUCER'S POI IS NOT BOUND TO ITS RAID — **P0**

| | |
|---|---|
| **Module** | 9 (candidate selection) + 15 (`f_prod`) |
| **Lines** | 3537–3544, 3574–3581, 5238–5246, 5260–5270, 5370 |

**Current behaviour.** The S/D producer fires when a zone gets a 50 % tap, a confirmation candle
inside `confirmWin`, and `tier <= minTier`. It is then handed the *global* liquidity event:

```pine
else if allowConf and sdC and cg
    pr   := PR_SD
    psl  := anyExt        // the raid wick of the most recent raid on this side — ANYWHERE
    zid  := f_zoneId(sdZ) // a zone selected with no reference to that raid
...
if pr > PR_MACH
    rqv := anyRq · rk := anyKind · pid := anyId · mb := cMssBar · dbr := dispBar2
```

The only link between the two is `cg = confGateLong`:

```pine
confGateLong = sslInPlay and cMssBarL > anyLoBar and nz(dispUpBar2,-1) >= cMssBarL
               and f_recent(cMssBarL, TRIG_LOOK) and recentDispUp
```

— **ordering of global flags, and nothing else.** `needSweep` (default **OFF**) only asks whether
`sslInPlay` is true at all, i.e. whether *a* raid exists somewhere.

**Why it is logically wrong.** This is precisely the `old sweep + new MSS + unrelated displacement =
BUY` construction. v7.1 fixed containment in three places — the machine's stage 3→4, `f_gradeZone`,
`f_atHtfPoi` — and left the fourth, which is the one producer whose narrative gate is disabled
(`hNarrL = prodL > PR_MACH or narrLong`).

**Trading consequence.** A demand zone anywhere on the chart inherits a sell-side raid that may be
many ATR away, and then:
* `f_sl(1, close, prodSlL = anyExt, …)` writes the stop at **that unrelated raid's wick** whenever
  it happens to fall inside the `minRiskN … maxRiskN` clamp — a stop that invalidates a different
  trade's thesis;
* `f_grade` reads `rq = anyRq` — the unrelated raid's grade — and `not mach` makes the grade-A rung
  reachable (`g == GR_B and (not mach or narr) and tier <= 2 and rq >= RQ_B`);
* the printed reason line asserts `EVENT #n SSL RAID A (PDL) → DEMAND T2 → …`, a causal chain that
  was never checked.

**Recommended fix.** Require containment inside `f_prod`'s `PR_SD` branch — one site, both sides —
reusing `poiBindAtr`, and repurpose the existing `needSweep` input as the escape hatch with its
default flipped to ON.

---

### BUG-03 · ZONE TIER 1 IS BOUGHT WITH THE **GLOBAL CHART** OTE — **P1**

| | |
|---|---|
| **Module** | 9 (`f_gradeZone`) · lines 3356, 3360 |

```pine
bool ote = isSupply ? inOTEsell : inOTEbuy       // ← chart-wide dealing-range OTE
if liq and disp and mss and htfA and (ote or (isSupply ? premOK : discOK))
    t := 1
```

`inOTEbuy` / `inOTEsell` are computed at 3017–3018 from `rngHi` / `rngLo`, the **chart's** external
swing range — exactly the "global chart range distorting OTE" §15 forbids. A zone therefore earns
tier 1 partly because price happened to sit inside the chart-wide OTE box at the moment the zone was
created. Tier 1 then propagates into `minTier` (a hard gate), `f_score`'s POI block (+5) and
`f_grade`'s A+ rung (`tier == 1`).

The `ote or …` is also *redundant with its own alternative*: `premOK` / `discOK` already require the
correct half of the same range, and the OTE band is a subset of that half. So the term can only ever
fire when the alternative already did — it is **dead as a disjunct** and harmful as a concept.

**Fix (token-negative).** Delete the `ote` term and its declaration.

---

### BUG-04 · `retBeforeFail` IS UNCONDITIONALLY TRUE AT FLIP TIME — **P1**

| | |
|---|---|
| **Module** | 9 · lines 3277, 3425, 3508, 3528, 3552, 3566 |

For a supply zone the loop runs, in order:

```pine
if high >= bot                       // any touch, including the breaking bar itself
    z.retBeforeFail := true
...
if close > top                       // the break
    f_zoneFlip(z, false, z.retBeforeFail and z.liqBeforeFail and dispUpBar and (recentIChUp or …))
```

A bar that closes **above** `top` necessarily has `high >= bot`, because `top > bot`. So
`retBeforeFail` is set to `true` on the very bar that reads it, every time.

**Consequence.** The documented three-part causal chain for a BREAKER ("the zone was created, price
returned into it, a liquidity event happened AT it, displacement broke it and structure shifted")
has only **two** live requirements. `isBrk` is easier to satisfy than intended, so zones that were
never revisited before being run through are promoted to BREAKER (tier 2, `PA_BRK`, PD-array rank 1
— second only to an order block) instead of MITIGATION (tier 3, rank 5).

**Fix.** `z.touchBar` already records the *first* touch and only the first (`if z.state == 0`).
Test `z.touchBar >= 0 and z.touchBar < bar_index` and delete the now-unused field.

---

### BUG-05 · RAID GRADE IS INFLATED BY AN UNOWNED DISPLACEMENT — **P1**

| | |
|---|---|
| **Module** | 7 (`f_poolScan`) · lines 2650–2663 |

```pine
else if bar_index > p.raidBar and (p.buySide ? (dispDnBar or shiftDn) : (dispUpBar or shiftUp))
    p.state := PS_REACT
    p.rq    := p.rq == RQ_C ? RQ_B : p.rq        // ← grade promotion
```

The reaction test is a **global** displacement / structure-shift flag inside `reactWin` bars. Nothing
ties that candle to this pool. Promoting the *state* to `PS_REACT` on that evidence is defensible —
"something happened after the raid". Promoting the **grade** is not: `rq` is supposed to describe the
raid candle itself (depth × rejection), and it is consumed as a hard requirement.

**Consequence.** `RQ_B` is the grade-A rung's requirement (`rq >= RQ_B`). A one-tick wick that closed
back weakly (`RQ_C`) becomes `RQ_B` because an unrelated bar displaced within six bars, and the
setup becomes grade-A eligible. It also lifts the LIQUIDITY score block from 4 to 8 points.

**Fix (token-negative).** Delete the promotion line.

---

### BUG-06 · THE ELITE-TRAP A+ PATH IS UNREACHABLE, AND ITS OTE TEST IS INVERTED — **P1**

| | |
|---|---|
| **Module** | 15 · lines 5159, 5346–5347 |

v7.1's stated headline change is "an ELITE trap reaches tier 1, is admitted in every entry mode, and
is A+ eligible". The first two are true in the code. **The third is not.**

```pine
oteQL = prodL <= PR_MACH ? upS.oteQ : inOTEbuy ? 2 : 0      // trap ⇒ oteQ ∈ {0, 2}
...
if g == GR_A and ((mach and narr) or elite) and tier == 1 and rq == RQ_A
   and f_geq(rr, rrAPn) and apTouch and (oteNeedAp ? oteQ == 1 : oteQ <= 1)
```

A non-machine producer can never produce `oteQ == 1` — class 1 is only ever written by
`f_inOte` on a setup's own impulse leg. Therefore:

* with `oteNeedAp = true` (**the default**) an elite trap can **never** be A+;
* with `oteNeedAp = false` the test becomes `oteQ <= 1`, so a trap that **is** in the OTE (`oteQ == 2`)
  is *disqualified* while one that is **not** in the OTE (`oteQ == 0`) is *admitted*. **Backwards.**

**Consequence.** A documented capability does not exist, and the switch that is supposed to *relax*
the OTE requirement instead applies it upside-down to one whole producer class.

**Fix.** Give the elite path its own clause: `elite ? oteQ >= 1 : oteNeedAp ? oteQ == 1 : oteQ <= 1`
— an elite trap must sit in the chart OTE (the only OTE statement available to it) rather than being
punished for it.

---

### BUG-07 · THE TRAP'S "TRACKED LIQUIDITY" TEST DOES NOT TEST THE BROKEN LEVEL — **P1**

| | |
|---|---|
| **Module** | 11 · lines 2925–2932, 3817–3831 |

```pine
if wState == 0 and brokeUp and … and (not trapNeedPool or poolBrkUp)
    wLevel := brkUpLvl        // a STRUCTURE swing level (sInt/sExt evLvlUp)
    wPool  := poolBrkUp       // "SOME buy-side pool closed through THIS BAR"
```

`poolBrkUp` is set by the registry loop for *any* pool of that side whose `brkBar == bar_index`. It
is never compared with `brkUpLvl`. So `trapNeedPool` ("the broken level must be TRACKED liquidity")
is satisfied by a coincidence of timing rather than of price.

`wPool` is then the first of the five ingredients in both `f_trapQual` and `f_trapElite`, and
`f_trapElite` grants tier 1, admission in `Narrative only`, and A+ eligibility.

**Fix.** Capture the broken pool's price alongside `brkUpKind` / `brkDnKind` (which already exist and
are already written in that loop) and require `|brkPx − brkLvl| <= lqTol`.

---

### BUG-08 · CONGESTION IS COUNTED THREE TIMES — **P2**

| | |
|---|---|
| **Module** | 11B / 13 / 15 · lines 4118, 4130, 4858, 5169, 5381 |

One reading (`congN >= 2`) produces:

1. `regime := RG_CHOP` (4130) — and, note, `RG_CHOP` is *unreachable* when `congGate == "Off"`,
   because `congested` carries the gate switch inside it;
2. a score debit: `ev := math.max(cong ? ev - 4 : ev, 0)` (4858);
3. a **grade downgrade**: `if cong and not congHard: g := AP→A→B→NONE` (5169);
4. plus the hard-block variant `hCongL` (5381) when `congGate == "Block"`.

The score debit and the grade downgrade are two independent penalties for the same evidence, applied
to the same candidate in the same bar. §19 and §23 both forbid this.

**Fix.** Keep the grade downgrade (it is the load-bearing one, and it is a *step*, not a number) and
drop the score debit; decouple `regime` from the gate switch so `RG_CHOP` survives `congGate = Off`.
**Deferred in this pass — see §18** (it changes published score semantics and the budget is spent on
P0/P1).

---

### BUG-09 · EQH / EQL AND SWING POOLS ARE REGISTERED `pivLen` BARS LATE, AND THE REGISTRY NEVER LOOKS BACK — **P2**

`f_qPush` is called on pivot confirmation, i.e. `pivLen` (default 5) bars after the pivot formed.
`f_qFlush()` (2866) then runs immediately before `f_poolScan()` (2867), and `f_poolScan` only ever
examines the **current** bar's `high` / `low`. A raid that occurred during the pivot's own
confirmation window is therefore invisible: the pool is born already-swept and is registered as
`PS_VAL`, resting.

**Consequence.** Missed liquidity events (fewer signals), and — worse — a level that has already
been taken is displayed and targeted as if it were still resting. Not a false-signal source; a
false-context source. **Deferred** (a backfill scan is not affordable at 95 spare source tokens).

---

### BUG-10 · TWO ALERT PAIRS ARE LITERAL DUPLICATES — **P3**

Lines 5989/5991 and 5990/5992: `[SIGNAL] Any LONG` and `[SIGNAL] Trade Engine LONG` have the
identical condition `finalLong` (same for SHORT). Two alerts fire for one event.
**Fix:** delete the redundant pair — and it pays for part of BUG-01.

---

## 3 · REPAINTING / FUTURE-DATA FINDINGS

| Call | Expression | Historical | Realtime | Close | HTF transition | Verdict |
|---|---|---|---|---|---|---|
| `f_bias` ×5 | `_v[1]` | fixed **iff tf ≥ chart** | stable iff tf ≥ chart | same | steps one HTF bar late | **BUG-01 when tf < chart** |
| `f_htfCtx(htfCtxTf)` | `[_dir[1], _pd[1]]` | fixed | stable | same | one bar late | safe iff tf ≥ chart |
| `D`, `W` high/low | `[high[1], low[1]]` | fixed | stable | same | n/a | **safe** |
| `f_htfStruct(htfTf)` | `[_hi[1],_lo[1],_d[1],time[1]]` | fixed | stable | same | `newHtfBar` fires one bar late by design | safe iff tf ≥ chart |
| `f_htfPoi(htfTf)` | all six `[1]` | fixed | stable | same | one bar late | safe iff tf ≥ chart |

Everything else is confirmed-bar gated. `barstate.isconfirmed` is used unconditionally
(`confirmed = barstate.isconfirmed`) and every state mutation in M4, M7, M9, M11, M11B, M12 sits
behind it. `showDev` draws on the unconfirmed bar but writes no state and raises no alert — correct.
Session extremes track live inside the session (that is live data, not future data) and freeze on the
first bar after the session on a confirmed bar.

**Only one repainting defect exists in this file, and it is BUG-01.** Everything the header claims
about non-repainting is true *provided the requested timeframe is above the chart timeframe*, which
nothing enforces.

---

## 4 · EVENT-OWNERSHIP PROBLEMS

| Path | Pool ID | Raid bar | POI containment | MSS bar | Disp bar | Verdict |
|---|---|---|---|---|---|---|
| `PR_FEM` / `PR_MACH` | `liqId == tgtId` ✓ | owned, `> tgtBar` ✓ | **`liqExt` inside the array ± 0.15 ATR** ✓ | `> liqBar` and `> poiBar`, level origin recent ✓ | `> mssBar`, past MSS, out of POI, holds ✓ | **sound** |
| `PR_SD` | global `anyId` | global `anyLoBar` | **none** ✗ | global `cMssBar` | global `dispBar2` | **BUG-02** |
| `PR_TRAP` | global `anyId` | global `anyLoBar` | reclaimed level ≈ break level, **unchecked** ✗ | global | global | **BUG-07** |
| zone provenance (`f_gradeZone`) | stamped `srcPoolId` ✓ | stamped, containment ✓ | ✓ | global `iChDnBar/cisdDnBar`, ordered | global `dispDnBar[1..2]` | ordered, not owned |

The stamps `srcPoolId` / `srcRaidBar` / `srcMssBar` / `srcDispBar` exist on every Zone and are
written at creation — **and are then never read by any consumer.** They are the correct mechanism
for BUG-02 and they are already paid for; the confluence producer simply does not consult them.

---

## 5 · SMC PROBLEMS

* External and internal structure are genuinely separated: two `Struct` instances over two pivot
  lengths through one `f_structUpdate`, and `structDir = extDir != 0 ? extDir : msDir` prefers
  external. An internal MSS never masquerades as an external reversal — `f_grade`'s reversal rung
  demands `mssCh` (a CHoCH), and the state machine's stage-5 `ch` is `chochUp/chochDn` from `sInt`
  with a separate `mssNeedChoch` switch. **Correct.**
* **Double-counted break (P2).** In `f_structUpdate`, the CHoCH-through-`protLo` branch (1789) sets
  `s.loBroken := false`, so on a subsequent bar the BOS-down branch (1825) can fire again on the same
  leg if `close < s.swLo`. One structural failure, two events, two `evLvl`/`evBar` writes.
* HTF structure is genuinely derived from HTF data (`f_htfStruct` on `htfTf`), not reconstructed —
  subject to BUG-01.
* `protLo` / `protHi` are the originating pivot of the BOS leg, as documented. **Correct.**

---

## 6 · ICT PROBLEMS

* **BOS / CHoCH / MSS / CISD are properly separated.** `bosUp` ≠ `chochUp` ≠ `cisdUp`, and the
  promotion is explicit and gated: `cisdMssUp = cisdUp and (not mssNeedDisp or dispUpBar or strongUp)`,
  `mssBull = chochUp or cisdMssUp`. `mssNeedDisp` defaults ON. **Correct.**
* CISD itself is a real delivery-flip: a run of ≥ 2 same-direction non-neutral bodies, then a close
  through that run's opening price with `body >= 0.5 ATR` and a strong close, one-shot per run
  (`cisdUpDone`). **Correct — this is one of the better modules.**
* `strongUp` uses `close >= high − 0.30 × range`, i.e. a genuine close-at-the-extreme test. A
  `cisdMssUp` can be paid for by `strongUp` alone when `dispUpBar` is false — a strong close with a
  small body. Marginal; documented as the intent of `mssNeedDisp`.
* **OTE:** the machine's OTE is leg-based and correctly oriented
  (`f_inOte(isL, legLo, legHi, deep, close)`, raid extreme → displacement extreme, banded
  1 = 62–70 · 2 = 70–79 · 3 = > 79). It is never a standalone trigger. **Correct.** But the *zone
  tiering* and the *non-machine producers* still use the global range OTE — BUG-03, and `oteQ = 2`
  at 5346.
* **Premium/discount:** `discOK`/`premOK` from `pdPos` on the external dealing range; the reversal
  rung additionally requires the `PD_EXTREME` (25 %) band. Continuation and reversal do **not** share
  the same PD logic — correct. When `rangeOK` is false both `discOK` and `premOK` return true, so the
  PD gate is inert rather than blocking; acceptable, worth knowing.
* `legHi`/`legLo` keep extending through `ST_RAID … ST_DISP`, so a pre-MSS spike inflates the leg and
  makes the retracement read *shallower* than it is. Minor, conservative in the wrong direction.

---

## 7 · LIQUIDITY PROBLEMS

**Registry is the strongest module in the file.** One `Pool` UDT, one queue, one scan, fusion by
`lqTol = max(eqTol × ATR, eqTickMin × mintick)`, per-kind priority, confluence mask, cluster pass,
lifecycle `NEW → VAL → RAID → REACT → DONE`, priority-aware pruning.

Verified working: external (PDH/PDL, PWH/PWL, external swings, HTF swings `PK_HTF`), internal
(swings, EQH/EQL with `eqMinSep` + both-leg reaction requirement + `eqScanN`-deep pivot memory),
session (Asia/London/NY, frozen on session close, retired on sweep), trendline.

**Sweep definition is correct and is *not* a weak-touch classifier:**

```pine
if sg*(pex - p.px) > 0            // wick beyond the level
    if sg*(close - p.px) < 0      // AND closed back inside
        pen >= raidMinAtr         // AND minimum depth   → RAID
        rej = close back by raidRejFrac × range (+ optional absolute raidBackAtr)
        rq  = deep&rej ? A : deep|rej ? B : C
    else                          // closed beyond → the pool is BROKEN, not raided
```

Wick penetration, close-back, depth, rejection fraction and grading are all present and all correct.
A shallow touch below `raidMinAtr` is recorded as a *test* (`f_poolTouchInc`), which raises quality —
the right treatment. **Weak touches are not classified as raids.**

Problems: **BUG-05** (grade inflation), **BUG-09** (registration lag).

**Trendline liquidity is correct.** `PK_TL` is pushed **only** on the bar the line is swept
(`high > tlHy and close < tlHy and tlHn >= tlMinTouch`) — a break alone never creates a pool, and the
pool is created and raided on the same bar because `f_qFlush` precedes `f_poolScan`. This is exactly
what §20 asks for. Two notes: the touch branch and the sweep branch are `if / else if` on the same
bar, so a sweep whose overshoot is under `NEAR_LVL_ATR` is counted as a touch instead — conservative;
and `tlHn` resets on every new external pivot, so touches must accumulate between two `extPiv`
pivots.

**Inducement** (`s.induced`) is correctly defined: an *internal* (`PK_SWING`) pool on the same side,
raided **before** this setup's raid, different pool id, inside `induceLook`. Scored +2 out of the
liquidity block's own allowance, never a gate. **Correct.**

---

## 8 · TRAP PROBLEMS

Bull trap and bear trap are correctly mirrored and correctly sequenced: structure break with a
`BRK_BODY_ATR` body → wick-series evolution over ≤ `maxAfterBrk` bars → reclaim close back through
`wLevel` with a body → fire. Runaway abort at 3 ATR. One fire per arming (`wFired`).

* **BUG-07** — "the broken level must be tracked liquidity" is not actually tested against the level.
* **BUG-06** — the elite trap's advertised A+ eligibility is unreachable.
* **P2:** producer ② (`pa2Long` / `pa2Short`) never writes `trapQ` and never writes `paSl`, so a ②
  entry carries `trapQ = RQ_NONE`, `ti = 3` and `psl = na`. At the default `minTier = 2` it can never
  pass `hTier`, so ② is **dead at default settings** — and if `minTier` is raised to 3 it trades with
  no trap-specific stop, silently falling through `f_sl` to the protected swing. Its alert
  (`emitPA2`) is correspondingly dead. Honest, but it should be said out loud.
* An elite trap **cannot** bypass structural requirements: `cg` (chronology), `rq == RQ_A` on the raid,
  RR, room, dedupe and the consumption block all still apply. The one thing it does bypass is
  `hNarr`, which every non-machine producer bypasses — BUG-02's blast radius.

---

## 9 · SUPPLY / DEMAND PROBLEMS

Zone creation requires a **3-candle FVG plus a displacement body on the middle candle**
(`newDemand = bullFVG and zDispUp`, `zDispUp = bullBar[1] and body[1] >= dispFactor × atr`). It is
therefore *not* "every opposite candle = order block" and *not* "every small reaction = S/D".
Order blocks are only created when `tD <= 2`, i.e. the demand zone itself already graded — the last
opposing candle of a leg that broke structure and left an imbalance. **Correct and well done.**

* **BUG-04** — breaker/mitigation classification is missing one of its three requirements.
* `z.liqBeforeFail` is set by *any* raid near the zone regardless of side (3499). For a supply zone
  being run upward, the relevant event is a buy-side raid; a sell-side raid at the same price also
  arms it. **P2.**
* `raidNearPx` uses the **pool price** (`anyLoPx`), while `f_gradeZone` uses the **raid wick**
  (`anyLoExt`) for the identical purpose. Inconsistent. **P3.**
* Zone-count control: `maxZones = 8` per side, oldest-first pruning, overlap dedupe on creation.
  One flaw — when an overlapping *better* zone sets `dupD := true`, the loop keeps running and still
  *deletes* other overlapping worse zones, so the net effect is to lose a zone rather than replace
  one. **P3.**
* `f_regrade` re-tiers every bar on HTF/structure agreement and monotonically on state. A bound POI's
  tier is re-read each bar (`s.poiTier := f_zoneTier(s.poiZone)`), so a mid-setup HTF flip can kill a
  live setup via `f_zoneDead`. Defensible, worth knowing.

---

## 10 · FVG / IFVG / OB / BPR PROBLEMS

* **FVG definition is the correct 3-candle one** — `bullFVG = low > high[2]`, `bearFVG = high < low[2]`
  — with a minimum height (`fvgMinAtr`) on the machine's execution gap and a `dispFactor` body on the
  creating candle. Fill tracking uses a running `deepest`, giving true partial-fill states
  (0 fresh / 1 touched / 2 ≥ 50 % / 3 filled), and `fvgFillDead` retires a filled gap as a POI while
  keeping the box for context. **Correct.**
* The machine's execution gap orientation is correct on both sides
  (`ft = isL ? low : low[2]`, `fb = isL ? high[2] : high`).
* **IFVG:** created by `f_zoneFlip` when an FVG zone is closed through — `z.pa := z.isFvg ? PA_IFVG : …`.
  "What failed" is the original FVG and "why it inverted" is the close through it. Correct in
  principle; inherits BUG-04's weakened `isBrk`.
* **BPR:** a new FVG overlapping a live opposite-polarity FVG (`state < 3`, `not flipped`) re-tags the
  survivor and promotes it to tier 2. Genuine opposing overlap. **Correct.** One asymmetry: only the
  *existing* zone is re-tagged; the *new* zone is created as a plain FVG, so the BPR is represented
  once rather than as the overlap region.
* **PD-array ranking** (`f_paRank`: OB 0 · BRK 1 · IFVG 2 · BPR 3 · FVG 4 · MIT 5) is applied in the
  machine's POI selection as `zw = tier×100 + paRank×10 + state`, tier first, then array class, then
  how little has been eaten. Array-iteration order can no longer decide a tie. **v7.1 fixed this
  properly.** It is *not* applied to the S/D producer, which picks by `z.tier < sdTierS` and then by
  iteration order — **P2**, and a direct consequence of BUG-02's design.

---

## 11 · TRENDLINE PROBLEMS

Covered in §7. The sequence the brief asks for — validated line → touches → sweep/false break →
reclaim close → registry → raid → the normal machine — is **exactly what the code does**. A
trendline break alone creates nothing. No changes needed.

---

## 12 · TIMEFRAME PROBLEMS

| Chart TF | `f_autoHtf()` HTF | Setup TF | Execution TF |
|---|---|---|---|
| 1m | 15m | chart | chart |
| 2m / 3m | 30m | chart | chart |
| 5m | 1H | chart | chart |
| 10m | 2H | chart | chart |
| 15m | 4H | chart | chart |
| 30m | 4H | chart | chart |
| 1H / 2H / 4H | D | chart | chart |
| D and above | D | chart | chart |

* **Auto is always ≥ the chart** — safe.
* **Manual is not.** `htfSel` / `htfCtxSel` / `biasFilter` accept values below the chart timeframe
  with no relation check → **BUG-01**.
* On a Daily chart, `f_autoHtf()` returns `"D"`, so `htfLive = false`, `newHtfBar` never fires and
  `PK_HTF` pools are never registered. The HTF POI is still requested at `"D"` on a `"D"` chart —
  `request.security` to the same timeframe returns the chart series with a one-bar lag, which is
  degenerate but harmless. Weekly/Monthly charts behave the same way.
* `timeframe.isintraday` correctly disables sessions, killzones, news windows, PDH/PDL registration
  and AMD on non-intraday charts.
* LTF structure is never used as HTF structure — `hStrDir` comes only from `f_htfStruct`.

---

## 13 · SESSION PROBLEMS

* All sessions are evaluated in `"America/New_York"` via `time(timeframe.period, ses, tz)`, which is
  DST-correct because the exchange calendar does the conversion. **Correct — not a hardcoded UTC offset.**
* Session extremes track live and freeze on the first bar after the session, on a confirmed bar, then
  register as `PK_SES` pools and are retired with a `✓ SWEPT` / `⇡ BROKEN` annotation once taken.
  **Correct, and the retire-on-sweep behaviour is right.**
* Sessions are **context, not triggers**: `kzOK`, `sbGate`, `volOK` are permission filters (default
  `useKZ = false`, `sbOnlyIn = false`), `sbRole` defaults to "Filter only", and `sesPts` / `sesStory`
  are score only, capped inside the CONTEXT block. **Exactly what §18 asks for.**
* AMD/Judas is descriptive only (`amdTxt`, `f_evTag`), never a gate. **Correct.**
* The news windows are honestly labelled a *scheduled volatility filter*, not a calendar. Good.
* Minor: `f_inSes` is called 11 times, each a separate `time()` call. Cost, not correctness.

---

## 14 · PATTERN PROBLEMS

There is **no candlestick-pattern library**, and none should be added. What exists is:
pin bar / engulfing (used only as a *confirmation* candle at a zone or an FVG retest), IFC, CISD,
TWS, and the two trap producers. Every one of them is contextual — none can override HTF bias,
liquidity, structure, POI or invalidation, because all of them still pass through the same twelve
hard gates. **No change needed. Resist the temptation.**

---

## 15 · ENTRY PROBLEMS

**Hard requirements (a signal cannot exist without all of them):**
`prod > 0` · `baseOK` (bias filter, killzone, volatility window, SB, cooldown, structure filter) ·
`hNarr` **(machine only)** · `hSl` · `hTgt` (a real structural TP2, never synthetic) · `hRr ≥ rrB` ·
`hRoom` (only when `oppLiqHard`) · `hDedup` · `hTier` · `hCong` (only when `Block`) · `hRun` (only
when `Block`) · `hGrade` · `hScore` (off by default) · arbitration.

**Scoring only:** the whole of `f_score`. It cannot create a signal — `minScore = 0` by default and
`hScore` is a floor, never a substitute. **§23 is satisfied: the score ranks, it does not rescue.**

**Where scoring substitutes for causality:** nowhere in the score. It happens one level up, in
`f_grade`, via `(not mach or narr)` on the grade-A rung combined with BUG-02 — a *producer identity*
substituting for a *narrative check*.

**Timing.** `lateBars = 6` from the first FVG touch is a hard kill (`kill := true`, the setup dies,
not just downgrades). Discrete re-entries are counted (`fvgTouches` via the `inGap` edge detector) and
`apMaxTouch = 2` caps A+ at the unmitigated touches. `retestWin = 25` bounds the wait. A setup
**cannot** become valid after its window: `bar_index - s.fvgBar > retestWin` kills it, and a close
fully through the gap kills it. **§24 is satisfied.**

One resurrection path exists and is correctly fenced: lines 5485–5492 return a blocked `ST_ENTRY`
setup to `ST_FVG`. `s.fvgTouch` is deliberately **not** reset, so the `late` clock keeps running and
the setup cannot retry forever. **Correct.**

---

## 16 · SL / TP PROBLEMS

**SL hierarchy** is raid wick → protected swing → FVG invalidation → POI edge → ATR fallback, each
padded by `SL_PAD_ATR` and each validated by `f_slOk` (correct side, `minRiskN ≤ distance ≤ maxRiskN`).
`slOk` is a **hard gate**, so an ATR-fallback stop outside the clamp blocks the trade rather than
being used. Long/short symmetry is exact. **Sound.**

The defect is *what is fed in*: for `PR_SD` and `PR_TRAP`, `lvlRaid = anyExt` (BUG-02) — a stop that
may invalidate a different trade's thesis. And for producer ②, `paSl = na`, so the trap's own
invalidation is simply absent.

**TP hierarchy**: TP1 internal pool ≥ 1R → TP2 = nearest of {opposing zone, external pool} ≥ `rrB × risk`,
falling back to internal → TP3 external ≥ max(2R, 3R). All three clamped short of the nearest
un-raided opposing pool **or** opposing POI by `NEAR_LVL_ATR` when `tpClamp` is on, then ordered.
`tgtSrc == 0` (synthetic) is a **hard block**. RR is measured to the *clamped* TP2, before emission.
**This is correct, and it does not target through an opposing wall.** No changes needed.

---

## 17 · PERFORMANCE PROBLEMS

* **6 `request.security` calls** returning 15 series. Reasonable; `f_bias`'s five are the expensive
  cosmetic ones (dashboard rows) but they also feed `filtBias`.
* Per-bar loops over `pools` (≤ 28) and `zones` (≤ 16): the registry scan, the target/inducement scan,
  `f_findRaid` ×2, `f_nextPool` ×4, `f_nextZone` ×2, `f_oppLiq` ×4 (two of them called with
  `go = needRisk` which is true on `barstate.islast` even with no producer). Bounded and cheap.
* `f_lqCluster` is `O(n log n)` and runs **only on `barstate.islast`**. Correct.
* `f_maskAdd` / `f_maskN` use `math.pow` in a loop — a bit-mask over 8 kinds via floating-point
  exponentiation. Works, but it is the one genuinely wasteful primitive in the file. **P3.**
* Object budgets: `max_boxes_count`/`max_lines_count`/`max_labels_count` all 500. Pool lines ≤ 28,
  zone boxes ≤ 16 + mid lines, zigzag ≤ 40, `lqLbs` ≤ 12 + `lqBxs` ≤ 6 (cleared each last bar),
  trade lines 5 (cleared), chips one per event. **No object explosion.** Two tables reused, not
  recreated.
* `f_chip` label growth is the only unbounded producer — one label per marked event, forever. At 500
  labels TradingView drops the oldest, which is the intended behaviour.

---

## 18 · PRIORITISED FIX ROADMAP

Priced against **≈ 308 compiled tokens spare**. `1 source token ≈ 3.418 compiled`.

| # | Fix | Bug | Pri | Δ compiled |
|---|---|---|---|---|
| 1 | `f_tfUp` clamp on `f_bias`, `htfTf`, `htfCtxTf` | BUG-01 | **P0** | **+106** |
| 2 | S/D producer must CONTAIN its raid (`f_prod`, one site, both sides); `needSweep` repurposed + default ON | BUG-02 | **P0** | **+89** |
| 3 | Delete the global-OTE term from `f_gradeZone`'s tier-1 rung | BUG-03 | P1 | **−48** |
| 4 | `retBeforeFail` → `touchBar < bar_index`; delete the field | BUG-04 | P1 | **+17** |
| 5 | Delete the `RQ_C → RQ_B` promotion in `f_poolScan` | BUG-05 | P1 | **−34** |
| 6 | Elite trap gets its own OTE clause on the A+ rung | BUG-06 | P1 | **+27** |
| 7 | Capture `brkUpPx`/`brkDnPx`; `wPool` must be the level that armed the trap | BUG-07 | P1 | **+120** |
| 8 | Delete the duplicate `Trade Engine LONG/SHORT` alertconditions | BUG-10 | P3 | **−58** |
| | **NET** | | | **≈ +219 of 308** |

**Deferred, with reasons — not dropped:**

| Bug | Why deferred |
|---|---|
| BUG-08 congestion triple-count | Changes published score semantics; the grade downgrade already carries the penalty, so the defect is over-punishment, not a false signal. Needs its own pass. |
| BUG-09 pivot-lag registration | A retroactive raid backfill is ~200+ source tokens. Not affordable. |
| §5 double-counted structural break | Cosmetic on the event stream; no gate reads `evBar` twice. |
| ② trap has no stop and no quality | Dead at the default `minTier`. Fixing it costs more than the capability is worth at this budget. |
| `f_maskAdd`/`f_maskN` `math.pow` | Pure performance, zero behavioural change, and any rewrite risks the mask semantics. |
| PD-array ranking for the S/D producer | Subsumed by BUG-02's fix at the containment level; full ranking parity needs the zone loop restructured. |

---

## 19 · MODULE CLASSIFICATION

| Module | Verdict | Reason |
|---|---|---|
| 1 Inputs | **KEEP + IMPROVE** | Retitle `needSweep`; no input removed, none added — the budget forbids it |
| 2 Constants / helpers | **KEEP** | Clean, amortised, no dead entries |
| 3 Core series · CISD · IFC | **KEEP** | CISD is correctly a delivery flip, one-shot per run |
| 4 Structure | **KEEP + IMPROVE** | Internal/external separation is right; the double-break at 1789/1825 is a P2 |
| 5 Sessions | **KEEP** | Exchange-tz, DST-correct, context-only |
| 6 HTF context | **REFACTOR** | Correct `[1]` discipline, but nothing constrains the TF — BUG-01 |
| 7 Liquidity registry | **KEEP + IMPROVE** | Best module in the file; remove the grade promotion (BUG-05) |
| 8 Dealing range / OTE | **KEEP** | Correct; the misuse is downstream, not here |
| 8B Liquidity marking | **KEEP** | Last-bar only, no leak, no object growth |
| 9 S/D · FVG · OB · BPR | **KEEP + IMPROVE** | Creation discipline is genuinely good; BUG-03, BUG-04 |
| 11 Trap engine | **KEEP + IMPROVE** | Sequence correct; BUG-06, BUG-07 |
| 11B TWS · run · congestion · regime | **KEEP + IMPROVE** | BUG-08 deferred; TWS and run are correctly context-only |
| 12 Setup state machine | **KEEP** | The causal core. Nine states, single instance per direction, independent re-derivation at the gate. Do not touch beyond the listed fixes |
| 13 Score | **KEEP + IMPROVE** | Cannot create a signal; the one real defect is the congestion debit (deferred) |
| 14 Gates + dedupe | **KEEP** | ID + price + recency dedupe, correctly triple-keyed |
| 14B SL / TP | **KEEP** | Hierarchies and clamps are correct; only the *inputs* to them are wrong (BUG-02) |
| 15 Trade engine | **KEEP + IMPROVE** | BUG-02, BUG-06 |
| 16–19 Risk / visual / dash / debug | **KEEP** | Display only, bounded, honest |
| 20 Alerts | **KEEP + IMPROVE** | One duplicate pair (BUG-10) |

**Nothing is classified REMOVE.** Nothing in this file was found to be harmful-and-redundant except
one duplicate alert pair, one dead disjunct (`ote` in `f_gradeZone`), one dead condition
(`retBeforeFail`) and one grade promotion — all four of which are *deletions that fix a bug*, which is
also how the budget gets paid.

---

## 20 · WHAT IS ALREADY RIGHT — DO NOT "FIX" IT

Stated plainly because the brief warns against churn:

1. The nine-state machine with per-direction instances and independent narrative re-derivation.
2. The raid definition — wick beyond **and** close back inside **and** minimum depth **and** graded
   rejection. Close-beyond correctly retires the pool as *broken*, not *raided*.
3. Trendline liquidity registered only on the sweep.
4. The `[1]`-indexed HTF idiom in all six security calls.
5. FVG as a true 3-candle imbalance with a displacement body and running-fill lifecycle.
6. Order blocks only from legs that broke structure and left a gap.
7. The four-part displacement test (body · past MSS · out of POI · holds into the close) and the
   displacement-reversal kill.
8. Leg-based banded OTE, never a standalone trigger.
9. `lateBars` as a hard kill with `fvgTouch` preserved across the ST_ENTRY→ST_FVG retry.
10. RR measured to a real, clamped TP2 before emission, with synthetic targets hard-blocked.
