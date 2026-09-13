# AUDIT v7.0 — ICT FORENSIC UPGRADE · CRT / TBS REMOVED

**Deliverable:** `20.liquidty+supply-v7.0-ict.pine` (new file, from `19.liquidty+supply-v6.4-ctt-htf.pine`).
Files 1–19 untouched on disk.

**Measured budget.** v6.4 = 31 873 source tokens ≈ **99 467** compiled of 100 256 (789 spare).
v7.0 = 31 566 source tokens ≈ **98 418** compiled (**≈ 1 838 spare**), with the whole ICT layer added.
Main body 1 863 statements vs the 2 034 the lineage is known to accept (CE10295 not in play).
Model: `compiled ≈ 3.418 × source_tokens − 9 475`, fitted on the two real TradingView results in the
lineage (v6.0 = 99 740, v6.2 = 108 630) and cross-checked against v6.4's measured 100 451 (error 53).

---

## A · FORENSIC AUDIT REPORT

Ordered by impact on entry quality. Each row: what was wrong · why it was wrong · where · what it did
to entries · the fix.

### A1 — TIER 1 WAS AWARDED FROM UNRELATED GLOBAL EVENTS **(the most serious defect in the file)**

| | |
|---|---|
| **Problem** | `f_gradeZone` graded a new zone T1 from `bslInPlay` / `sslInPlay` ("a raid exists *somewhere* on this side") and `recentMssDn` / `recentMssUp` ("*some* shift happened within ten bars"). |
| **Why wrong** | Neither flag had to be anywhere near the zone, and neither had to be in the right ORDER relative to the other. This is precisely the failure §2 names: confluence substituted for causality. |
| **Where** | MODULE 9, `f_gradeZone`. |
| **Impact** | Severe and systemic. Tier 1 is what `minTier`, `hTierL/S`, the A-rung (`tier <= 2`) and the A+ rung (`tier == 1`) are all built on, and the machine re-reads the live tier every bar. A supply zone could print T1 off a raid hundreds of points away plus a shift that pre-dated it — so the highest-confidence label in the system was being handed out on evidence that belonged to a different market event. Every grade above B was mis-priced. |
| **Fix** | The raid must sit AT the zone (within `poiBindAtr × ATR`, the same binding tolerance the setup machine uses for its own POI) and still be live; the shift must come strictly AFTER that raid. The zone now records `srcPoolId`, `srcRaidBar`, `srcMssBar`, `srcDispBar` so the claim is auditable in the debug panel rather than asserted. |

### A2 — CISD WAS TREATED AS IDENTICAL TO A STRUCTURE SHIFT

| | |
|---|---|
| **Problem** | `mssUp = chochUp or cisdUp`. |
| **Why wrong** | A CISD is a close through the ORIGIN OPEN of the last directional run — an order-flow statement. A CHoCH is a displaced close through the PROTECTED SWING — a structural one. Collapsing them means "MSS" fires on candles where no level was broken at all (§5). |
| **Where** | MODULE 4. Consumed by the machine's stage 5, the pool reaction promotion, the TWS resolution and the run-reversal test. |
| **Impact** | Manufactured shifts. The machine's stage 4→5 gate is the causal hinge of the whole narrative; a CISD-only "MSS" let a setup advance to displacement and FVG with no structural break behind it. |
| **Fix** | Four separate vocabularies (`bosBull/Bear`, `chochBull/Bear`, `cisdBull/Bear`, `mssBull/Bear`). A CISD is promoted to MSS only when the same candle also displaces (`mssNeedDisp`, default ON). A third, looser reading (`shiftUp/shiftDn`) is used *only* where a directional hint genuinely suffices — the pool reaction promotion and the run engine — and never as a setup's stage-5 MSS. |

### A3 — LIQUIDITY TARGETING WAS A PROXIMITY TEST

| | |
|---|---|
| **Problem** | Target selection kept the pool with the smallest price distance (`p.px < tgtBuy`). |
| **Why wrong** | §7 asks for ranked selection over type, age, touches, confluence and external-vs-internal. Nearest is the one criterion that has nothing to do with where liquidity actually rests. |
| **Where** | MODULE 7, the intent loop. |
| **Impact** | A three-bar-old minor swing outranked a previous-week high standing four ATR away, so the machine locked trivial targets and the entire narrative that followed was built on hunting something no one was hunting. |
| **Fix** | A ranking: `kindPri×10 + confluence×5 + min(touches,4)×4 + legs×2 − distance_in_ATR × tgtDistW`, with a hard `tgtMaxAtr` reachability cap. Setting `tgtDistW` high reproduces the v6.4 behaviour. |

### A4 — OTE WAS COMPUTED FROM AN UNRELATED GLOBAL RANGE

| | |
|---|---|
| **Problem** | `inOTEbuy` / `inOTEsell` measured the 62–79 % band of the CHART's dealing range and handed the same answer to every setup on the bar. |
| **Why wrong** | A retracement is a property of ONE impulse leg (§11). |
| **Where** | MODULE 8; consumed by `f_score` and `f_gradeZone`. |
| **Impact** | The OTE score term and the OTE ingredient of T1 were noise with respect to the setup being judged. |
| **Fix** | `f_inOte` on the setup's own leg — raid extreme → displacement extreme, tracked while `ST_RAID ≤ st ≤ ST_DISP` and frozen at displacement so the band cannot drift under the entry it is judging. A+ requires it (`oteNeedAp`). `oteLegMode` OFF restores the v6.4 reading. |

### A5 — NO LATE-ENTRY REJECTION

| | |
|---|---|
| **Problem** | The FVG retest could fire anywhere inside `retestWin` (default 25 bars). |
| **Why wrong** | §48: an array that price entered many candles ago is mitigated, the RR has decayed, and the move has usually already run. |
| **Where** | MODULE 12, stage 7→8. |
| **Impact** | Late entries at collapsed RR, indistinguishable in the output from immediate ones. |
| **Fix** | `s.fvgTouch` stamps the FIRST entry into the gap; the entry must arrive within `lateBars` (default 6). Beyond that the setup is killed with the reason `LATE — n bars since the first FVG touch`. PREMATURE / VALID / LATE is reported per side in the debug panel. |

### A6 — EVERY VIOLATED ZONE WAS A "BREAKER" OR A "MITIGATION"

| | |
|---|---|
| **Problem** | `f_zoneFlip` captioned by the causal chain only (`isBrk`), never by what the object had been. |
| **Why wrong** | An FVG that is closed through and then holds from the other side is an INVERSION (§13), a distinct execution array. |
| **Where** | MODULE 9. |
| **Impact** | Three different institutional concepts collapsed into two labels, so the POI stage could not prefer between them. |
| **Fix** | `z.pa := z.isFvg ? PA_IFVG : isBrk ? PA_BRK : PA_MIT`, and the POI stage now ranks the PD array (`f_paRank`) as a tiebreak after tier (§40). |

### A7 — REVERSALS DID NOT REQUIRE PREMIUM / DISCOUNT

| | |
|---|---|
| **Problem** | `revOk = not rev or (mssCh and tier == 1 and rq == RQ_A)`. |
| **Why wrong** | §10: the whole point of the dealing range is that a counter-trend entry taken at equilibrium is the trade to refuse. |
| **Where** | `f_grade`. |
| **Impact** | Counter-HTF trades from mid-range graded normally. |
| **Fix** | `pdExt` (`inDiscExt` / `inPremExt`) added as a fourth reversal precondition. Note these two globals had become dead when the CRT location filter was removed — they are now load-bearing. |

### A8 — NO INDUCEMENT, NO HTF LIQUIDITY, NO TRENDLINE LIQUIDITY

Three of the brief's liquidity sources were simply absent (§38, §7/§25, §22). All three now enter
through the ordinary registry so they inherit raid grading, the sweep/break split, the lifecycle,
the marking layer and target selection rather than being bolted on. See §B.

### A9 — DEAD CODE LEFT BY THE REMOVAL

`raidExtLo / raidEqLo / raidExtHi / raidEqHi` and their derived `engLoRaid / engHiRaid / extLoRaid /
extHiRaid` existed only to feed the ⑫⑬ location filter. With CRT/TBS gone nothing read them; they are
deleted. `cisdBull` / `cisdBear` in MODULE 3 were renamed `cisdSeqUp` / `cisdSeqDn` — they mark a
candle that *continues a run*, which is the input to the CISD test, not the CISD itself, and §5 needs
those two names for the flip.

### A10 — NOT CHANGED, AND WHY

Examined and found correct; left alone deliberately: the pool lifecycle and raid grading, the
raid-vs-break split, `f_narrOk` chronology re-derivation, the FVG ownership rule (`FVG_OWN_MAX`), the
dedupe trio plus the V5.5-E7 price-and-recency guard, `f_sl`'s hierarchy and risk clamp, `f_tp`'s
measured TP2 and wall clamp, the V5.2-B3 transient-block return to state 7, and the whole
`confirmed`-gating discipline. These are the parts of v6.4 that were already doing what the brief
asks, and §1 says to preserve them.

---

## B · ICT IMPLEMENTATION REPORT

How each component interacts with the master engine. "Context" = enables/scores, never triggers.

| Component | Implementation | Role in the engine |
|---|---|---|
| **BOS** | `bosBull/bosBear` — displaced close through the latest pivot in trend | Context; arms the trap watch |
| **CHoCH** | `chochBull/chochBear` — displaced close through the PROTECTED swing | Machine stage 5; `mssCh` is an A+ precondition on reversals |
| **MSS** | `mssBull/mssBear` = CHoCH, or CISD **carrying displacement** | Machine stage 5, the causal hinge |
| **CISD** | `cisdBull/cisdBear` — close through the origin open of the last run | Independent trigger evidence in the score; MSS only via §5 promotion |
| **Internal vs external** | Two independent `Struct` instances (`pivLen` / `extPiv`) | External = context and dealing range; internal = execution timing only |
| **HTF → LTF** | `f_autoHtf` map + `f_htfStruct` publishing the HTF's own pivot-derived direction | Hierarchy is explicit and displayed; an LTF shift cannot overturn it |
| **Liquidity registry** | 8 pool kinds incl. new `PK_HTF`, `PK_TL` | One pool = one event = one id |
| **HTF liquidity** | HTF swing extremes registered as `PK_HTF`, highest `f_kindPri` | Real external targets on an intraday chart |
| **Trendline liquidity** | Confirmed anchors → correct slope → touch count → **swept** → registered | Enters only as a swept pool; a break alone does nothing |
| **Sweep / break / test** | Existing: penetration ≥ `raidMinAtr` + rejection → graded A/B/C; close beyond = BREAK; shallow = TEST | Raid grade is a hard A+ requirement |
| **Inducement** | Most recent INTERNAL pool raid per side, before the setup's own external raid | Scored (out of the liquidity block's own 5 pts) + A+ ingredient |
| **Premium / discount** | Dealing range + `PD_EXTREME` | Reversal precondition (§A7) + score |
| **OTE** | `f_inOte` on the setup's own impulse leg | Score + A+ precondition |
| **FVG** | Existing displacement-owned gap, `FVG_OWN_MAX` ownership | Machine stage 7 |
| **IFVG** | An FVG closed through, flipped, re-armed | PD array, ranked above raw FVG |
| **Order block** | Last opposing candle of a displacement leg that also broke structure and left an FVG | PD array, ranked highest |
| **Breaker** | Non-FVG zone violated with the full causal chain | PD array |
| **Mitigation** | Non-FVG zone violated without it | PD array, ranked lowest |
| **BPR** | New FVG overlapping a live opposing FVG | Overlap re-tagged, promoted to T2 |
| **Displacement** | Body ≥ `dispFactor × ATR` + close in outer 30 % + must clear the MSS level + must leave the POI | Machine stage 6 |
| **Trap** | v5.5-E6 engine: crowded pool broken → failure → reclaim, graded A/B/C | Producer `PR_TRAP`, tier 2 only when graded ≥ B |
| **TWS** | Three-wave manipulation lifecycle | Descriptor only; cannot emit |
| **AMD / PO3 / Judas** | `amdTxt` phase + `judasL/judasS` | Context; attaches a `JUDAS` descriptor |
| **Session narrative** | `sesStoryL/S` (London takes Asia, NY takes London) | Context score |
| **Silver Bullet** | Filter or score, never a signal | Unchanged |
| **Market regime** | TREND / RANGE / EXPANSION / CHOP | Reported + scored; **adds no gate** (see §46 note below) |

**On §46 (do not overfit).** No oscillator, no candlestick library, and no second gate resting on
evidence an existing gate already reads. The regime classifier is deliberately *not* a gate:
congestion — the same evidence — is already wired as one, and adding a second would be double-counting
dressed as rigour. Likewise inducement is scored out of the liquidity block's existing five points
rather than added on top, and the HTF-array bonus comes out of the POI block's existing six.

---

## C · CRT / TBS REMOVAL REPORT

**Verified mechanically: zero identifiers matching `crt|tbs|ctt|Crt|Tbs|Ctt|turtle` remain outside
prose comments.**

Removed in full:

- 15 inputs: `showCRT`, `showTBS`, `tbsLen`, `crtRangeAtr`, `crtDispAtr`, `tbsAgeMin`, `sigCooldown`,
  `crtLife`, `tbsConfMode`, `crtNeedLoc`, `cttWin`, `cttShowRng`, `cttMaxRng`, `cttSrc`, `cttLocOnly`,
  plus `useHtfCrt`.
- `type Crt` + `f_crtAdvance` (5-stage lifecycle, instantiated twice) and `crtUp` / `crtDn`.
- `type Tbs` + `f_tbsAdvance` (likewise), `tbsUp` / `tbsDn`, and the four `tbsLen` extreme series.
- `f_crtTbsHtf` and its `request.security` (slot reused by `f_htfStruct` — no new HTF call).
- `f_ctt_crtCand`, `f_ctt_tbsCand`, `f_ctt_htfCand`, `f_ctt_loc` (reduced to `f_atHtfPoi`).
- The entire CTT marking layer: `type Ctt`, `f_cttTxt`, `f_cttMark` (inlined 4×), `f_cttLvl`,
  `f_ctt_chart`, `f_ctt_htfMark`, `cttUp/cttDn/cttHUp/cttHDn`.
- Cooldown state `lastCrtLongBar/…` and `crtLongCd/…`.
- Producer ranks `PR_CRT` / `PR_TBS`, both `f_prod` branches, both consumption branches.
- Dashboard row 15 (`CRT·TS·TWS`) → now `TWS · AMD · regime`.
- 5 alerts: `[SIGNAL] ⑫ CRT entry`, `[SIGNAL] ⑬ Turtle soup entry`, `[SIGNAL] HTF CRT / Turtle soup`,
  `[TRIG] CRT confirmed`, `[TRIG] Turtle soup confirmed`.
- Event descriptors `"CRT"` and `"TSOUP"`.

**Nothing depends on them for any entry, score, gate, state transition or confirmation.** The
producer ladder is now `PR_FEM(1) → PR_MACH(2) → PR_SD(3) → PR_TRAP(4)`.

**Why nothing replaced them in kind.** The evidence CRT and turtle soup were standing in for — a
range extreme taken and reclaimed with displacement — is exactly what the liquidity registry's raid
grading plus the machine's MSS and displacement stages already measure, with ownership and
chronology. A pattern match cannot supply either.

---

## D · ENTRY ENGINE REPORT

Order of business (unchanged in shape, stricter in content):

```
producer selection → SL / TP / RR / opposing liquidity → HARD GATES →
soft score → grade → arbitration → consumption
```

### Hard gates — all must pass; a high score can never buy past any of them

`prod > 0` · `baseOK` (bias / killzone / volatility window / SB / structure filter / cooldown) ·
`hNarr` (`f_narrOk` re-derives the full causal chain independently of the transitions that produced
it) · `hSl` (a stop exists inside `[minRiskAtr, maxRiskAtr]`) · `hTgt` (TP2 came from a real level,
never `rrMult`) · `hRr` (`rr ≥ rrB`, and `rrB` now has **minval 1.5** per §32, so the floor cannot be
configured away) · `hRoom` · `hDedup` (pool / POI / MSS, plus price-and-recency) · `hTier` ·
`hCong` · `hRun` · `hGrade` · `hScore`.

Additionally enforced *inside* the machine, which kills the setup rather than muting it: LATE timing
(§A5), POI invalidated / spent / re-graded below `minTier`, raid reclaimed, raid stale, MSS before
raid, MSS on an unrelated level, displacement that did not clear the MSS level or leave the POI, FVG
traded fully through.

### Grades

- **A+** — machine producer, `f_narrOk` true, live tier-1 POI, grade-A raid, `rr ≥ rrAplus` (2.0),
  **and the entry inside its own leg's OTE** (`oteNeedAp`). If it is a REVERSAL it additionally needs
  a CHoCH-grade MSS, tier 1, a grade-A raid **and** a premium/discount extreme.
- **A** — narrative intact or a confluence producer with full chronology, tier ≤ 2, raid ≥ B,
  `rr ≥ rrA` (1.5).
- **B** — a graded raid (≥ C) and `rr ≥ rrB` (1.5). Below B is not a grade and does not trade.
- **Downgrades** (one step each, and one step below B is NO TRADE): insufficient opposing-liquidity
  room in soft mode, congestion in soft mode, fading an unexhausted liquidity run.

### NO TRADE

Any hard gate failing, or any machine-level invalidation above. The exact reason is reported per
direction in the debug panel (`f_blockReason`), including the new `LATE`, the new reversal reason
naming the premium/discount requirement, and every pre-existing reason.

---

## E · REPAINT AUDIT

| Risk | Finding |
|---|---|
| `request.security` | **6 call sites / 10 instances — identical to v6.4.** `f_bias` (inlined at 5 TFs), HTF context, PDH/PDL, PWH/PWL, HTF structure, HTF FVG POI. The HTF structure feed took over the slot the CRT/TBS pair vacated, so the ICT layer added **zero** new HTF series. |
| Lookahead | Every call uses `lookahead_on` **with the expression indexed `[1]` INSIDE the request**. This is the only combination that is both leak-free (only a closed HTF bar is ever read) and stable (the value does not change as the HTF candle forms). No bare-expression `lookahead_on` anywhere. |
| Pivots | `ta.pivothigh/low(n, n)` throughout — confirmed `n` bars late by construction. The new HTF structure uses `(2,2)` *inside* the request and then `[1]` again, so a level is visible only after the HTF candle that confirmed it has closed. Trendline anchors are confirmed external pivots only, and `bornBar` is back-dated to the pivot without any forward reference. |
| New HTF series | `hSwHi`, `hSwLo`, `hStrDir`, `hT` — all `[1]`-indexed inside the request. `newHtfBar` fires on the first *confirmed chart bar* after the HTF candle closed. |
| State mutation | Every latch, every registry write, every machine transition, the trendline engine and the zone loop are inside `if confirmed`. The `confirmed` guard is *inside* `f_poolScan`, `f_trendline` and `f_setupAdvance` rather than on the call, because Pine evaluates both branches of a ternary. |
| `ta.*` in conditional branches | `f_twsRun` (renamed from `f_ctt_twsRun`) is still called **unconditionally at global scope**, so its two `ta.*` references advance every bar. `ta.sma(atr, 50)` for the regime is a top-level global. No `ta.*` call was moved into a conditional branch. |
| Variable history offsets | The order-block reads use **constant** offsets (`high[2]/[3]/[4]` selected by ternary), not a series-int offset, so no `max_bars_back` hazard was introduced. |
| Historical vs realtime | No intrabar-only condition feeds state or a signal. The dim `⋯` developing preview is the only intrabar drawing, is explicitly provisional, raises no alert and changes no state. |
| Duplicate signals | Unchanged and intact: `setupId`, pool `spent`, `bound`, zone `signaled`, the dedupe trio, per-direction cooldowns, and terminal states clearing one bar later. |

---

## F · CHANGE LOG

**Added** — `PK_TL`, `PK_HTF`, `PA_*` (7 PD-array classes), `RG_*`, `TM_*`; `f_rgTxt`, `f_tmTxt`,
`f_paTxt`, `f_paRank`, `f_inOte`, `f_htfStruct`, `f_trendline`, `f_atHtfPoi`; Zone fields `pa`,
`srcPoolId`, `srcRaidBar`, `srcMssBar`, `srcDispBar`; Setup fields `legLo`, `legHi`, `induced`,
`oteOk`, `fvgTouch`, `poiPa`; globals `bosBull/Bear`, `chochBull/Bear`, `cisdBull/Bear`,
`mssBull/Bear`, `cisdMssUp/Dn`, `shiftUp/Dn`, `indLoBar/indHiBar/indLoId/indHiId`, `hSwHi/hSwLo/
hStrDir`, `atrRel`, `regime`, `amdKz/amdSes/amdManip/amdDist/amdTxt`, `judasL/judasS`, `sesTag`,
`indHitL/S`, `oteHitL/S`; inputs `useInduce`, `induceLook`, `mssNeedDisp`, `htfLiqReg`, `showTL`,
`tlMinTouch`, `tgtDistW`, `tgtMaxAtr`, `showOB`, `showBPR`, `oteLegMode`, `oteNeedAp`, `lateBars`;
alerts `[SIGNAL] A LONG`, `[SIGNAL] A SHORT`, `[TRIG] MSS`.

**Modified** — `f_gradeZone` (causal + provenance, returns 5), `f_zoneFlip` (IFVG/breaker/mitigation),
zone creation (provenance, OB, BPR), target selection (ranking), `f_score` (+3 params, points
reallocated not inflated), `f_grade` (+2 params: OTE, PD extreme), `f_reason` (+3 params),
`f_prod` (−8 params), machine stages 3/4/5/8, `f_kindPri`, `f_kindTxt`, `f_poolCol`, `f_poolVisible`,
`f_blockReason`, dashboard rows 6 and 15, debug rows 13 and 16, entry labels, `rrB` default
1.2 → **1.5** with minval 1.5, `maxZones` default 6 → **8**.

**Removed** — all CRT/TBS/CTT (see §C); `CP_TINY/CP_MEAN/CP_DEEP`; the dead raid-class globals (§A9).

**Preserved byte-for-byte** — the pool registry and lifecycle, `f_poolPush` and the registration
queue, EQH/EQL construction, clustering and MODULE 8B marking, the session engine, `f_narrOk`,
`f_setupReset`, the dedupe layer, `f_sl` / `f_tp` / `f_oppLiq` / `f_nextPool` / `f_nextZone`, the trap
engine, TWS, the liquidity-run engine, the congestion filter, the risk ladder, the visual engine and
every surviving alert name.

---

## G · TEST REPORT

**Method and its limits, stated plainly.** These are **static traces**: for each scenario the gate
chain, the state machine and the score/grade path were followed by hand through the source, using the
default input set. They verify *logic reachability and refusal* — that a scenario reaches the state it
should and is refused for the reason it should be. They are **not** backtest results, and no claim is
made here about win rate or profitability. Rows marked ⚠ could not be fully determined statically and
need chart verification.

| # | Scenario | Expected | Actual (static trace) | Verdict |
|---|---|---|---|---|
| 1 | Bullish reversal: PDL raided → CHoCH + displacement → FVG → 70 % retrace | A/A+ LONG, `oteOk` true | Target ranks PDL (kindPri 5); stage 3 binds; leg opens at raid low; stage 5 CHoCH; stage 6 displacement clears MSS level and leaves POI; stage 7 FVG; stage 8 `f_inOte` true, timing VALID → grade A, A+ if raid A + T1 + RR ≥ 2 | **PASS** |
| 2 | Bearish reversal: PWH raided → CHoCH down → displacement → FVG retest | A/A+ SHORT | Mirror of 1; `PK_PW` kindPri 6 outranks nearby swings | **PASS** |
| 3 | Bullish continuation in HTF uptrend, discount POI | Continuation, `htfContLong` | `htfDir > 0` and `htfPd ≤ 0.5` → `htfContLong`; `reversal` false; no PD-extreme requirement | **PASS** |
| 4 | Bearish continuation, premium POI | Continuation | Mirror | **PASS** |
| 5 | London raids Asia low → MSS → displacement | LONG with session story + JUDAS + MANIP | `sesStoryL` true (`inLon` + tag "Asia"); `amdManip` true → `judasL` → `JUDAS` descriptor; label carries `· LONDON` | **PASS** |
| 6 | NY raids London high → bearish MSS | SHORT with session story | Mirror via `inNY` + tag "Lon" | **PASS** |
| 7 | Asia range → no killzone, no shift | NO TRADE | `amdTxt` = ACCUM; no raid binding → `"no liquidity target"` / `"target not yet raided"` | **PASS** |
| 8 | False breakout (buy-side taken, reclaimed, trapped longs) | Trap producer, tier ≤ 2 | Pool BROKEN arms watch (`trapNeedPool`), growing wicks + reclaim close → `pa1Short`, `f_trapQual` grades; tier 2 only if ≥ B, else T3 = display-only at default `minTier` | **PASS** |
| 9 | False breakdown | Mirror | Mirror | **PASS** |
| 10 | FVG retest, entry on the 2nd bar after first touch | VALID entry | `fvgTouch` set, `2 ≤ lateBars(6)` → allowed | **PASS** |
| 11 | FVG retest, rejection only on the 9th bar after first touch | **Refused as LATE** | `9 > 6` → `blk = "LATE — 9 bars since the first FVG touch"`, setup killed | **PASS** |
| 12 | OB retest at a raid | OB preferred over an overlapping raw FVG | Both contain the raid; `zw = tier×10 + f_paRank` → OB rank 0 beats FVG rank 4 | **PASS** |
| 13 | Breaker retest | Tradable at T2 | `f_zoneFlip` with full causal chain → `PA_BRK`, tier 2 | **PASS** |
| 14 | IFVG retest | Labelled IFVG, not BREAKER | `z.isFvg` → `PA_IFVG`, caption "IFVG ▲/▼" | **PASS** |
| 15 | OTE: entry at 45 % retracement | Not A+ | `f_inOte` false (needs ≤ 62 %) → A+ rung refused, A still available | **PASS** |
| 16 | No-liquidity environment (no live pools) | NO TRADE | `tgtSellPool`/`tgtBuyPool` na → `"no liquidity target"`; machine cannot pass stage 2 | **PASS** |
| 17 | Choppy market, 3/4 chop readings | Downgrade (default) / block | `congested` true → `f_grade` one step down; `congGate = "Block"` → `hCong` false | **PASS** |
| 18 | High-volatility spike, no structure | No displacement-grade MSS | `regime = EXPANSION`; a large candle alone fails stage 6's "clear the MSS level + leave the POI" | **PASS** |
| 19 | Trendline break, no prior touches | Nothing registered | `tlHn < tlMinTouch(2)` → no `PK_TL` push, no pool, no target | **PASS** |
| 20 | Trendline swept after 3 touches → MSS → FVG | Tradable via the normal chain | `PK_TL` pool registered at the swept projection; must still be locked, raided, POI'd, MSS'd | **PASS** |
| 21 | Counter-HTF setup at range equilibrium | NO TRADE | `revOk` false (`pdExt` false) → `GR_NONE` → reason names the premium/discount requirement | **PASS** |
| 22 | CISD with no displacement used as MSS | Refused | `mssNeedDisp` ON → `cisdMssUp` false → `"MSS / CHoCH missing"` | **PASS** |
| 23 | Two setups on the same pool | One entry only | `pool.spent` + `f_dedupeOk` price-and-recency guard | **PASS** |
| 24 | Opposing pool 0.8R away, `oppLiqHard` off | One-grade downgrade | `room < oppLiqMult` → A+→A→B→none | **PASS** |
| 25 | RR 1.3 on an otherwise perfect A+ | NO TRADE | `rrB` minval 1.5 → `hRr` false → `"RR 1.30 below the absolute floor 1.50"` | **PASS** |
| 26 | Object budget under OB + BPR + trendline load | Within limits | zones ≤ 8/side = 16 boxes + 16 mid-lines; pools ≤ 28 lines; MODULE 8B ≤ 12 labels + 6 boxes; all far under the 500 caps | **PASS** |
| 27 | Compile | Under both caps | 31 566 tokens ≈ 98 418 / 100 256; main body 1 863 / ~2 034 | ⚠ **predicted — needs TradingView** |
| 28 | Signal frequency vs v6.4 | Materially fewer, higher quality | Two producers removed; T1 now causal; CISD-MSS restricted; LATE refused; RR floor raised; A+ needs OTE. Direction is unambiguous; the magnitude cannot be derived statically | ⚠ **needs chart verification** |

**Rows 27 and 28 are the honest gaps.** I cannot compile Pine or run a chart from here, so the token
figure is a prediction from a model with 53-token error on the last measured build, and the frequency
claim is directional reasoning, not a measurement.

---

## H · IF TRADINGVIEW RETURNS AN ERROR

- **CE10117 (token cap)** — predicted margin is ~1 838, but in order: turn `showTL` off (costs only
  the trendline engine, ~620 compiled, no other system depends on it); then delete MODULE 8B's
  liquidity marking (≈ 3 960); then the debug panel (≈ 3 680). The first is a setting, the other two
  are feature removals.
- **CE10295 (main body)** — 1 863 vs the 2 034 known-good. If it appears, the two zone-creation blocks
  (`if newDemand` / `if newSupply`, ~70 statements together) are the obvious candidates to fold into
  one function, exactly as v6.2 did for MODULE 11C.
