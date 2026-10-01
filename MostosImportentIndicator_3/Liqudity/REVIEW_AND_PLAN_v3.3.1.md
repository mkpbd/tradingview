# OPERATOR REVIEW & IMPROVEMENT PLAN — LQ-SD-PA v3.3.1

Target file: `liqudity_trap_trading.txt` (5,065 lines, Pine v6, indicator).
Read date: 2026-09-29. **No code changed.** Line numbers refer to the file as read.
Evidence: full source read + 4 live M5 charts (XAUUSD / BTCUSDT / NAS100USD / USOIL, ~06:00 UTC+6, Asia · SB off-window).

Review stance: a discretionary desk operator who has to trade *this* screen, not a code reviewer. The question at every point is "would I take this trade, and does the tool tell me the truth about why not?"

---

## 1. WHAT THE TOOL ACTUALLY IS

A single-file, closed-bar, non-repainting ICT/SMC engine built around **one state machine per direction**:

`IDLE → SWEPT → AT POI → SHIFTED → (retest) → ACTIVE`

with everything else feeding it:

| Layer | Module | What it produces |
|---|---|---|
| Pivots / EQ pools / trendlines | M4 (956–1049) | `lastRes/lastSup`, EQH/EQL arrays, TL anchors |
| Session clock + SB windows | M4B (1050–1161) | `inAsia/inLon/inNY`, `sbCtx`, `sbWinNow`, window close edges |
| Liquidity | M5 (1162–1457) | sweep events, `QualRaw`/`QualEff`, pool `kind` 1–4, `sslInPlay/bslInPlay` |
| Structure | M6 (1458–1606) | internal + external BOS/CHoCH, MSS, protected swings |
| HTF bias | M7 (1607–1700) | `emaBias` + `hsDir` → `htfB` → `biasOkL/biasOkS` |
| HTF engines | M9 (1720–1940) | HTF CRT/TBS, 3-slot HTF FVG POI registry, ADR |
| Dealing range | M10 (1941–2036) | `pdPos`, OTE, SB frozen range |
| Regime | M11 (2037–2110) | TRENDING / TRANSITION / RANGING / CHOP |
| FVG + zones | M12/M13 (2111–2686) | FVG registry + IFVG flip, S/D · OB · RB · BRK/MIT zones, NEXT buy/sell |
| Engines | M14/M15 (2687–2936) | CRT, turtle soup, trendline, inside bar, doji, FEM |
| Score / tiers | M16 (2937–3057) | 0–100 alignment score, C/B/A/A+ |
| Trap engine | M16B (3098–3527) | LT-1…LT-7 + confidence score |
| Machine | M17 (3528–3877) | the primary path, SB overlay |
| Gates | M18/18B (3878–4148) | bias · lock · killzone · news · chop · score · tier · cooldown · risk cap · min RR |
| Execution / tracking | M19 (4149–4467) | plan price, TP ladder, BE/trail, counters |
| Visuals / dash / alerts | M20–23 (4468–5065) | |

The engineering quality is high: four prior audit passes, every fix documented in the header, raw-vs-effective sweep grades separated, plan price separated from bar close, per-engine stops, non-repainting HTF idiom (`expr[1]` + `lookahead_off`) correctly defended in the header. **The defects below are not sloppiness — they are the next layer of them.**

---

## 2. WHAT THE FOUR LIVE CHARTS SAY

| Chart | Dashboard | Symptom |
|---|---|---|
| XAUUSD M5 | `RANGING` · Bias ▼ all rows · Prem 89% · Setup `idle / ◉ AT POI` · **Align L 17 (C) S 42 (C)** · Verdict "SHORT narrative live · longs locked · AT POI · ADR 10%" | A short setup is at POI, tier **C**, score **42** — it will be refused at the final gate (`minScore 50`), but the verdict never says so. The operator reads "narrative live" as "a trade is coming". |
| BTCUSDT M5 | `RANGING` · Verdict "NO · score 22 < 50" · both machines idle | A full trade plan (E 82890.02 / SL 83128.41 / TP1 82651.63 / TP2 82413.24) is still painted on the chart although the tracker is flat. Six overlapping labels inside 300 points of price. |
| NAS100USD M5 | `CHOP` · Verdict "NO · chop" · Next demand **30325.8–30349.2**, Next supply **30367.8–30381.3** | The two opposing POIs are ~19 pts apart — well inside one M5 ATR. `poiConflict` zeroes POI points on **both** sides, so even out of chop this chart cannot reach `minScore`. |
| USOIL M5 | `RANGING` · Prem 82% · Trigger `CISD▼ · FVG locked` · Verdict "NO · score 34 < 50" | Same picture: engine has a locked FVG and a CISD and still scores 34. |

Three of four charts show the same end state: **the engine is permanently at "almost", and the dashboard's stated reason is not the operative one.** That is the headline problem, and it is a *scoring/plumbing* problem, not a doctrine problem.

Second visible problem across all four: **the right third of the chart is unreadable.** Zones, OB companions, RBs, IFVGs, FVG boxes, HTF POI boxes, NEXT BUY/SELL boxes+lines+labels, SB window boxes, flow boxes, OTE box and a stale trade ladder all draw at once.

---

## 3. FINDINGS

### P0 — these change which trades fire

**OP-1 · Sweep events have no once-per-level latch.**
`sslSweep = low < lastSup and close > lastSup` (1170–1171) is re-evaluated every bar, and `lastSup` only changes when a new pivot confirms. The engineered stamps (PDH/PDL 1290–1305, session 1385–1420) are the same. Consequences:
- `lastSslBar := bar_index` is rewritten on *every* qualifying bar → the sweep is eternally "fresh", `sslInPlay` (1447) never ages out, `liqLong` keeps its 10 points indefinitely.
- The "once per sweep" arm guards are defeated: `stdGraceL` / `sbGraceL` test `nz(armedSslBar,-1) != lastSslBar` (3583–3588, 3712) — since `lastSslBar` moves forward, the test is true again on the next bar. The FIX-T3/SB-9 guarantee does not hold.
- `QualRaw` is re-earned each bar; a weak re-poke can print grade 3 on a bar where the real raid was two bars ago.
Structure already has the correct pattern (`resBroken` / `supBroken`, 1454–1455). Liquidity needs the mirror.
**Fix:** per-level `sslSpentLvl` latch. A level may produce one sweep event; it re-arms only when the pivot changes, or when price has left by > `SWEEP_CTX_ATR × ATR` and come back.

**OP-2 · The score grades a different POI from the one the setup is standing on.**
`poiLong/poiShort` (2978–2979) and `retestLong/retestShort` (2991–2992) are computed from `nbTop/nsBot` — the **NEXT unspent zone marker**. The machine's actual anchor is `suLAnchorT/B` (3720–3736), which after FIX-V14 `fastShift` (3699) is a **shift-leg FVG that is not in the `zones` registry at all**. So on exactly the entries v3.3.1 was written to enable:
- `inDemand` false → POI 0–5 instead of 15
- `retestLong` false → exec 0–5 instead of 10
- up to **20 points** lost on the entry bar → `minScore 50` refuses it → FIX-V8 returns the stage to SHIFTED → it dies at the retest clock.
This is the most likely single cause of the "score 22 / 34 / 42 < 50" readings on three of the four charts.
**Fix:** when `suL/suS >= 2`, score POI and retest from the setup's own anchor; fall back to `nbTop/nsBot` only when idle.

**OP-3 · `poiConflict` is a mutual kill on charts where the two POIs are naturally close.**
`poiConflict = … nsBot - nbTop <= atr` (2967) → both `poiLong` and `poiShort` become 0 (2978–2979), the machine may not tap (3739, 3853), and the verdict reports it. On the NAS100 chart the gap is ~19 pts on an ATR of roughly the same size — a permanent mute on any ranging index. A demand and a supply one ATR apart is *normal* inside a balanced range; it is only a problem when price is *between* them with no direction.
**Fix:** resolve, don't kill. Keep the side that agrees with `htfB` / `dirLock` and mute only the other. Retain the mutual kill for the genuinely ambiguous case (price inside the gap **and** `htfB == 0`).

**OP-4 · The verdict names the wrong gate when a setup is live.**
In `noTrade` (4891–4900) the `dirLock != 0` branch is tested **before** the score / gate branches. The XAUUSD chart therefore prints "SHORT narrative live · longs locked · AT POI" while the actual blocker for that short is score 42 < 50. FIX-P1-10 set out to make the verdict honest; this ordering undoes it for the exact case the operator cares about most.
**Fix:** report the *active* side's own blocker first (`gateKillL/S`, then score, then tier), and append the lock as context: `"S: score 42 < 50 · AT POI · longs locked"`.

**OP-5 · The MSS institutional upgrade is not bound to the sweep it belongs to.**
`lastSslQual := mssUp and confirmed ? 4 : lastSslQual` (1544). `mssUp` only requires `sslInPlay`, and inside an SB context `sslInPlay` reaches back `sweepLook + 5` bars (1440–1445). A CHoCH 17 bars after a marginal poke promotes that poke to grade 4 — which then unlocks `minArmQual`, `sbMinQual` and the chop bypass through `instSweepL` (2105, which does read RAW — good) but also `sbCtxLong`'s window-gate point and the arming test `lastSslQual >= minArmQual` (3711).
**Fix:** require the MSS bar to be within `TRIG_LOOK` bars of `lastSslBar` **and** the break to be on the same side of `lastSslLvl` before the grade-4 write.

### P1 — accuracy and honesty of the numbers

**OP-6 · The standard machine path still prices its fill at the anchor edge on the signal bar.**
`mcPlanLong := sbCeFillL ? ceL : math.min(close, suLAnchorT)` (3792). The standard entry (`stdEnterL`, 3788) requires `zoneBullConf`, i.e. a *closed* confirmation candle — so the earliest real fill is the next bar's open, exactly the reasoning FIX-T7 applied to the engines (4129). The SB CE limit is genuinely a resting order and is correctly exempt; the standard path is not.
**Fix:** extend `engFillMode` to the non-SB machine path, or add `mcFillMode` with the same default.

**OP-7 · Tracker statistics are biased in two places.**
(a) A deferred engine order cancelled at 4198 (`pendDir := 0` when the tracker is busy or the stop gapped) is counted as tracked at 4451 (`trackNew` was true) — outcome never recorded, `cntUntracked` never incremented.
(b) One tracked trade at a time (by design, FIX-P0-6) means the counters are a biased sample of the signal set, not of the strategy. The header already says so; the dashboard does not.
**Fix:** increment `cntUntracked` on pending cancellation; label the counter row "sample, not backtest" in the debug table.

**OP-8 · Trap engine can arm on a `na` level.**
`_ltBrkLvlNow = … : lastRes` (3437). Before the first external/internal pivot, or after the pivot is consumed, `lastRes` can be `na` → `_ltSLevel := na` → the retest test `close < _ltSLevel` (3497) is never true → the short machine sits in state 1 until `ltWaitBars` expires, and `_ltSDoneLvl` (FIX-V6b) cannot latch.
**Fix:** refuse to arm when the level is `na`.

**OP-9 · EQ pools never age.** `eqhLvls/eqlLvls` (990–1030) are removed only when swept or when `MAX_EQ_POOLS` overflows. A pool built four hours ago still counts as engineered liquidity (kind 2), which is what `sbPoolPref` gates Silver Bullet on.
**Fix:** drop a pool on `fvgMaxAge`-style bar age, or when an external BOS through it makes it history.

**OP-10 · A session level can only be raided once, ever.** `hiSwept/loSwept` in `f_sesTrack` (1335–1380) latch at the first touch and reset only at the next session close. Asia H raided at 09:00 and again at 14:00 produces one pool event; the second (often the NY-AM one that matters) is invisible to kind 4.
**Fix:** reset the latch on a confirmed structural break in the opposite direction, or count a second raid after price has left by > 1 ATR.

**OP-11 · `regThrust` measures the leg with the ATR that leg inflated.** (2095) Documented and accepted in FIX-T16; keep, but note that on a slow grind `CHOP_RANGE_ATR = 6` over 40 bars is a high bar, and on a spike-and-die it over-fires. Candidate for per-symbol profiles (OP-18) rather than a code change.

### P2 — the chart is not readable (loudest problem in the screenshots)

**OP-12 · No drawing budget.** Concurrent objects near price at default settings: zones ≤ 6/side + OB companions + RB ≤ 2/side + IFVG + FVG boxes ≤ 4/side + 2 HTF POI boxes + 2 NEXT boxes + 2 NEXT lines + 2 NEXT labels + SB window boxes + 2 flow boxes + OTE box + label + 5 trade lines + 5 trade labels + chips. All four screenshots are illegible in the last 40 bars.
**Fix:** a "Focus mode" input that draws only: the live setup's anchor, NEXT buy/sell, zones within `N × ATR` of price, and the active trade. Everything else off unless the operator is studying.

**OP-13 · NEXT BUY and NEXT SELL labels share an x.** `xLb = x1 + 2` for both sides (4782). When the two zones are close (the NAS/BTC case) the labels overlap each other *and* the candles. The line also runs `nextLvlBack = 60` bars back, straight across historical price.
**Fix:** stagger x per side (buy at `x1+2`, sell at `x1+14`), shorten the line to ~15 bars with `extend.right`, and compress the text (`BUY T2 ·fresh · 4125.2 (0.04%)`).

**OP-14 · A closed trade's ladder stays on the chart.** The BTCUSDT screenshot shows E/SL/TP1/TP2 lines and labels from a trade the tracker has already closed (Trade row = flat). `f_tradeDraw` redraws on the last bar from `entryP/slP/...`, which persist.
**Fix:** clear or grey the ladder when `trdDir == 0` and no signal on this bar.

**OP-15 · Triple reporting of the same fact.** Dashboard rows 4/5, the on-chart NEXT labels, and the zone boxes all state the next demand/supply. Pick one primary (the chart) and reduce the dashboard rows to a distance figure.

**OP-16 · ADR% is misleading early in the day.** `adrPct` (1932) is today's range ÷ ADR; at 06:00 UTC+6 the charts read 2 %–16 %, which looks like "huge room left" when it actually means "the day just started". Print `ADR 10% (early)` while less than ~25 % of the session has elapsed.

### P3 — missing for professional operation

**OP-17 · No risk governance.** No daily loss limit, no max trades per day, no max consecutive losses, no per-symbol risk %, no equity curve. A 20-year operator's first filter is "how many times have I been wrong today", and this engine has no concept of it.

**OP-18 · No symbol profile.** The six advanced constants (`NEAR_LVL_ATR`, `SL_PAD_ATR`, `SWEEP_CTX_ATR`, `POI_NEAR_ATR`, `TRIG_LOOK`, `CHOP_RANGE_ATR`) plus `extPiv`, `minZoneAtr` and `dispFactor` are M5-FX defaults. XAU, NAS and BTC each need different ones — visible in the screenshots, where identical settings produce CHOP on NAS and RANGING on BTC at the same hour.

**OP-19 · No cost model.** RR, `minRR 1.5` and the TP ladder ignore spread and commission. On XAU M5 a 0.2–0.3 ATR spread turns a nominal 1.5R into ~1.2R.

**OP-20 · Alerts are not journal-grade.** No machine-readable payload with setup id, pool kind, sweep grade raw/eff, shift grade, window tag, score components, anchor range. Without it there is no way to reconcile the chart with the broker statement.

**OP-21 · The strategy twin referenced by FIX-F9 (`version_02_strategy.pine`) does not exist in this repo.** Every calibration instruction in the header ("measure `minScore` in the Strategy Tester") is currently un-executable.

---

## 4. IMPROVEMENT PLAN

Ordered so that each phase is independently shippable and testable. **Token budget warning:** v3.2.2 already hit the Pine compile ceiling (CE10117). Phase C *frees* tokens by deleting duplicate visuals, so run it before Phase D adds anything.

### Phase A — restore signal flow (P0)
| # | Change | Where | Acceptance test |
|---|---|---|---|
| A1 | Per-level sweep latch (`sslSpentLvl` / `bslSpentLvl`), mirroring `resBroken/supBroken` | M5 1170–1305 | Debug "Sweeps" row shows one event per level; `·live` turns `·stale` after `sweepLook` bars of chop above the level |
| A2 | Score POI/exec from the live setup's own anchor when `suL/suS >= 2` | M16 2978–2999 | A `fastShift` long at its FVG retest scores ≥ 50 on the XAU chart's conditions |
| A3 | `poiConflict` resolves by bias instead of muting both | M16 2967–2979, M17 3739/3853 | NAS100 with 19-pt spaced POIs still produces a bias-aligned tap |
| A4 | Verdict reports the active side's own blocker first | M21 4891–4900 | XAU chart prints `S: score 42 < 50 · AT POI` |
| A5 | Bind the MSS grade-4 upgrade to the sweep it belongs to | M6 1544 | `QualEff` no longer jumps to 4 when the MSS is > `TRIG_LOOK` bars from the raid |

Regression guard for the whole phase: with `fastShift = off`, `armGrace = 0` and `minScore = 0`, the signal set must be identical to v3.3.1.

### Phase B — execution realism (P1)
- B1 `mcFillMode` for the standard machine path (OP-6).
- B2 Fix `cntUntracked` on pending cancellation; relabel the counters (OP-7).
- B3 Trap engine refuses a `na` level (OP-8).
- B4 EQ pool age-out + session-raid re-arm (OP-9, OP-10).
- B5 **Rebuild the strategy twin** (OP-21) — this is the prerequisite for calibrating `minScore`, `minRR`, `maxRiskAtr` and `rrMult` with numbers instead of opinion.

### Phase C — make the chart tradable (P2, frees tokens)
- C1 `Focus mode` drawing budget (OP-12).
- C2 NEXT label/line geometry (OP-13).
- C3 Clear the stale trade ladder (OP-14).
- C4 Collapse the duplicated dashboard rows (OP-15), add the `(early)` ADR qualifier (OP-16).

### Phase D — operator features (P3)
- D1 Session risk module: trades today · consecutive losses · daily stop · "no more trades today" verdict (OP-17).
- D2 `Symbol profile` dropdown (FX · Metals · Indices · Crypto) presetting the nine sensitive constants (OP-18).
- D3 Spread/commission input folded into RR and `minRR` (OP-19).
- D4 One JSON-shaped `alert()` line per signal for the journal (OP-20).

### Calibration protocol (after B5, before trusting any default)
1. `minScore = 0`, `tierMode = All`, run the twin on 6 months M5 per symbol → record the score distribution of winners vs losers.
2. Raise `minScore` to the 40th percentile of winners, not to a round number.
3. Re-run with `fastShift` on/off and `armGrace 0/3` — four cells, pick per symbol.
4. Only then set `tierMode` and `sbMinTier`.

---

## 5. DO NOT TOUCH

Verified correct; previously "fixed" by mistake or at risk of being:
- `expr[1]` + `lookahead_off` in every `request.security` (header RETRACTED BUG-N2). Removing the `[1]` introduces lookahead on history and repainting live.
- Turtle-soup age math `-ta.lowestbars(...)[1] + 1` (1743, 2712).
- `QualRaw` vs `QualEff` separation (FIX-P1-1) — the A+ tier and liquidity bonus must keep reading RAW.
- `sslInPlay` requiring the reclaim to hold (FIX-P0-1, 1447–1450). This is the single most valuable gate in the file.
- Per-engine stops (FIX-P0-5) and the plan-price entry (FIX-P0-4).
- `f_claimBand` at every zone creation site (FIX-V3).

---

## 6. ONE-LINE SUMMARY

The doctrine layer is sound and well audited; what is failing on live charts is **plumbing between the setup and its own score** (OP-2), **liquidity events that never expire** (OP-1), **a conflict rule that mutes both sides** (OP-3) and **a verdict that names the wrong gate** (OP-4) — plus a chart too crowded to trade from. Phase A is roughly a day's work and should move three of the four screenshots from "NO · score < 50" to real, gradeable decisions.

---

## 7. APPLIED — v3.4 (2026-09-29)

Every finding below was implemented in `liqudity_trap_trading.txt`, which is now **v3.4**. The pre-change file is kept as `liqudity_trap_trading.v3.3.1.backup.txt`. Code marks carry the tag `FIX-Wn` and name their `OP-n`.

| Finding | Tag | Status | What changed |
|---|---|---|---|
| OP-1 sweep has no per-level latch | FIX-W1 / W1b | **applied** | `sslSpentLvl` / `bslSpentLvl` + `pdhDone` / `pdlDone`. One event per level; re-arms on a new pivot or after price travels `SWEEP_CTX_ATR × ATR` away |
| OP-2 score grades the wrong POI | FIX-W2 | **applied** | Machine-state block moved to MODULE **15A** (above the score). From stage 2 the score reads `suLAnchorT/B`; the anchor test is wick-in / close-held, not close-inside |
| OP-3 `poiConflict` mutual kill | FIX-W3 | **applied** | `poiBlockL/S` resolve by `htfB` → `dirLock` → `extDir`; mutual kill only on a true tie; a setup on its own anchor is immune |
| OP-4 verdict names the wrong gate | FIX-W4 | **applied** | Active side's own `gateKill` / score first, `f_suTxt` stage attached, lock demoted to a suffix |
| OP-5 MSS upgrade unbound | FIX-W5 | **applied** | Grade 4 needs the shift within `TRIG_LOOK` bars of the raid |
| OP-6 machine fill price | FIX-W6 | **applied** | `mcFillMode` (default next open). SB CE limit untouched |
| OP-7 counter bias | FIX-W7 | **applied** | Cancelled pending order books `cntUntracked` |
| OP-8 trap arms on `na` | FIX-W8 | **applied** | Both trap machines refuse a `na` level |
| OP-9 EQ pools never age | FIX-W9 | **applied** | `eqMaxAge` (240) + parallel `eqhBars` / `eqlBars` |
| OP-10 one raid per session level | FIX-W10 | **applied** | Latch clears once price walks 1 ATR off the level |
| OP-11 `regThrust` self-referential ATR | — | **accepted, no change** | Documented in FIX-T16; now addressed per symbol by the profiles instead |
| OP-12 no drawing budget | FIX-W13 | **applied** | `focusMode` (ON): boxes beyond `focusAtr` × ATR go transparent, flow + OTE washes off. Display only |
| OP-13 NEXT labels collide | FIX-W12 | **applied** | Sell label staggered +12 bars, line shortened to ≤18 bars |
| OP-14 stale trade ladder | FIX-W11 | **applied** | Cleared when the tracker is flat and no signal fired |
| OP-15 triple reporting | FIX-W14 | **applied** | Dashboard NEXT rows show grade + **ATR distance**, not the price range |
| OP-16 ADR misleading early | FIX-W15 | **applied** | `(early)` before 25% of the day has elapsed |
| OP-17 no risk governance | FIX-W16 | **applied** | `maxTrdDay` (4) / `maxLossDay` (2), reset daily, enforced at the final gate and named in the verdict |
| OP-18 no symbol profile | FIX-W17 | **applied** | `symProfile` FX / Metals / Indices / Crypto presets nine constants. **Starting points, not measurements** |
| OP-19 no cost model | FIX-W18 | **applied** | `costTicks` enters the min-RR gate and the printed RR; drawn levels unmoved |
| OP-20 alerts not journal-grade | FIX-W19 | **applied** | One `LQJRNL\|…` pipe-separated line per signal on the `alert()` feed |
| OP-21 no strategy twin | — | **applied** | `liqudity_trap_strategy.txt`, **generated** by `scripts/mktwin.py` |

### The twin
`python scripts/mktwin.py` regenerates `liqudity_trap_strategy.txt` from the indicator. Verified: the 4,966 lines between the declaration and MODULE 19S are byte-identical to the indicator, so the tester measures the same signals. **Re-run it after every indicator change; never hand-edit the twin.**

### Verification done
- Full-file paren / bracket / string balance: clean (indicator and twin).
- No duplicate or orphaned declarations after the 15A move; every new identifier is referenced.
- `scoreLong/Short` are floats (`math.round`) — the verdict's `actScore` is typed accordingly.
- **Not done: compilation.** There is no Pine compiler here. Paste into TradingView before trading it. If `CE10117` (token ceiling) appears, the cheapest cuts are `showOF`-style display features, not engine code.

### Behaviour that deliberately changed
These are not silent: `focusMode`, `mcFillMode`, `useGov`, `costTicks` and the POI/conflict rewiring all change what you see or what fires. To get v3.3.1 back for an A/B: `focusMode` off, `mcFillMode = "Plan price (v3.3)"`, `useGov` off, `costTicks = 0`, `symProfile = Manual`, `eqMaxAge` high. FIX-W1 to W5 have no off switch — they are defect repairs.

### Still on you (cannot be done from here)
The calibration protocol in §4. Until the twin has run, `minScore = 50`, `minRR = 1.5`, `maxRiskAtr = 1.5`, the governance limits and the four symbol profiles are **reasoned defaults, not measurements**.

---

## 8. CE10117 — token-budget pass (2026-09-29)

The first v3.4 build compiled to **104,324 tokens of 100,256**. Same wall v3.2.2 hit; same answer — the budget came out of presentation.

**Cut, no behaviour change:** journal / SB / LT alert payloads (same facts, far fewer concatenations) · symbol profile resolved through one `profIdx` integer instead of ~45 option-string comparisons · debug table lost the Context row and merged LT + SB + day book · ~47 tooltips cut to the sentence that decides something · box captions shortened · three dead variables dropped (`hPoiBCnt`, `hPoiSCnt`, `eqLvl`).

**Drawings removed** (the math behind each is untouched and still drives the engine):

| Removed | What still works |
|---|---|
| Premium / discount wash | `pdPos`, `rangeHolds` → context score, A+ P/D test, SB entry rule, dashboard "Range pos" row |
| OTE 62–79% box + EQ line | `inOTEbuy` / `inOTEsell` → POI score points, trap score, `poiSrc` OTE tap |
| Two wick-cluster pool lines | `p3PoolLow` / `p4PoolHi` → LT-3 and LT-4 arming, trap score |

Inputs gone with them: `showFlow`, `showRange`, `ltShowPools`, `focusHideFlow`.

**A warning about this file's history:** a regex used during this pass joined ~60 unrelated line pairs. It was caught by the paren/string scanner, and the file was rebuilt from the generated twin (which predated the damage) and the cuts re-applied cleanly. Verified after rebuild: balance clean, twin body identical again at 4,856 lines, 0 diffs. **Lesson recorded: never run a whitespace-spanning regex over this file.** Edit by anchored string replacement only.

**Still not compiled here** — no Pine compiler in this environment. If CE10117 returns, the next cuts in priority order, all still presentation:
1. the debug table entirely (~5 rows of string building),
2. the HTF POI boxes (the POIs still work, they just stop being drawn),
3. the prev-week high/low plots plus their `request.security` call,
4. the LT engine's 7 pattern arms, which is the first cut that would cost an actual signal source.
