# FORENSIC AUDIT — SMC / ICT / CRT Suite v8.2.1 (`SMC.txt`, 3417 lines, Pine v6)

Discovery → trace → audit → root cause → plan. **No code was modified.**
Line numbers refer to `SMC.txt` as read on 2026-09-26.

---

## 1. INDICATOR OVERVIEW

Single-file, overlay indicator. Layered "feature-vector" architecture: every layer runs once per bar, writes flags into one `Feat` object (`ft`), and ~60 setup modules (M01…M73) are each one boolean over `cd` (candle), `st` (structure), `ft` (features). Modules bid a base score into one accumulator per side (`bL` / `bS`); the winner per side becomes a `Sig` with entry / SL / TP1-3 / confluence score, filtered by HTF gate, premium-discount gate, killzone, min score, min/max R:R, and a 10-bar one-signal-at-a-time gap.

What it actually is: **a reversal-candle-at-POI pattern matcher with a large module library**, plus a swing-pivot structure engine, liquidity level tracker, FVG tracker, zone tracker (SR / KL / OB / BRK / RCB / RJB / QM / PROP), one HTF security call, sessions, PD array and a trade-line / alert layer.

What it is not (despite the name): no CRT, no TBS/TWS, no OTE, no IFVG, no mitigation block, no true MSS, no dealing-range PD array, no trailing / BE / partial exit, no position sizing.

---

## 2. COMPLETE FEATURE INVENTORY (verified from code)

### Layer map

| Layer | Function | Lines | Output |
|---|---|---|---|
| L0 candle | `f_candle` | 785-816 | `Cndl cd` |
| L1 structure | `f_structure` | 819-961 | `Struct st` + Ctx swing state |
| L2 FVG | `f_fvg`, `f_fvgNear` | 970-1030 | `ctx.fvgs`, `ft.newBullFvg/newBearFvg` |
| L2 strength | `f_moveStrength` | 1033-1066 | `Move mv` (BOS/CHoCH/arrival) |
| L3 liquidity | `f_addLevel`, `f_liq`, `f_resolve` | 1084-1275 | `ctx.lv`, `ft.swept*/run*/hidden*` |
| L4 zones | `f_zAdd`, `f_zones`, `f_zReset` | 1310-1776 | `ctx.zones`, `ft.at*/z*` |
| L5 HTF | `f_htfAuto`, `request.security`, `f_htf`, `f_gate` | 1779-1846 | `ft.htfBias/htfSweep*/htfManip*/htfRej*`, `ft.gateUp/Dn` |
| Orchestration | global | 1874-2305 | PD, sessions, arrival, counters, break state, M41-M54 latches, trendlines, M71 |
| L6 setups A–I | globals `s01…p6b` | 2307-2562 | bids into `bL/bS` |
| L6 setups J–R | `s39…s54b` | 2564-2685 | bids |
| L6 setups S–AB | `s58…s73b` | 2687-2868 | bids |
| L7 trade | `f_nearestOpp`, `f_nearestLiq`, `f_conf`, `f_stop`, `f_sig` | 2870-3105 | `sigL/sigS` |
| Draw | `f_lbl`, `f_add`, `f_evLine`, `f_panel`, `f_legend` | 3107-3369 | labels/lines/boxes/tables |
| Alerts | `alert()`, `alertcondition()` | 3371-3397 | |

### Market structure
| Feature | Exists | Where | Notes |
|---|---|---|---|
| Swing high / low | YES | `ta.pivothigh/low(5,5)` 1850-1851 | confirmed 5 bars late |
| BOS | YES | 826-827 | close beyond last confirmed pivot, one-shot per pivot (`hiBroken/loBroken`) |
| CHoCH | YES (nominal) | 860-861 | close beyond `majorHigh/Low` while trend opposite. Mostly unreachable (see §8) |
| MSS | NO | — | not distinguished from BOS/CHoCH |
| Internal vs external structure | NO | — | every pivot break is BOS; no hierarchy |
| Trend | YES | 851/858/863/875/885 | = direction of last BOS/CHoCH; RANGE after 20 bars without event |
| Displacement | PARTIAL | `mv.strong` 1064, `ft.dispScore` 1913 | measured, labelled, scored — **not required for BOS to change state** |
| Sweep of swing (wick) | YES | 828-829 `st.bullSweep/bearSweep` | wick beyond pivot, close back |
| Pullback validity | YES | 903-918 | price trades through low of the high-maker candle |
| CISD | YES (non-standard) | 932-951 | see §8 |
| Move phase | YES | 955 | close beyond last swing = IMPULSIVE else RETRACEMENT |
| Wyckoff phase | YES (cosmetic) | 957-960 | trend × range-width label only |

### Liquidity
| Feature | Exists | Where | Notes |
|---|---|---|---|
| BSL / SSL | YES | 1125-1127 | every confirmed pivot becomes a level |
| EQH / EQL (pool) | YES | 1087-1111 | merge within 0.10 ATR, `touches>=2` → POOL |
| External (`ext`) | YES | 1125 `swH >= extHi` | at 50-bar extreme |
| Internal liquidity | YES | 2215-2224 `intLowB/intHighB` | swing inside leg, used by M49 only |
| PDH / PDL | YES | 1862, 1128-1135 | security "D", `[1]`, expire on new day |
| PWH / PWL | YES | 1863, 1136-1143 | |
| Session H/L (Asia) | YES | 1920-1937 SESH/SESL | added at London open |
| Sweep | YES | 1161-1196 → `"SWEEP"` | wick through, close back (immediate or within 2-bar pend) |
| Run (grab through) | YES | `"RUN"` | body ≥0.6, close ≥0.25 ATR beyond |
| Stop hunt | = SWEEP | | no separate concept |
| Hidden liquidity | YES | 1262-1275 | 3 consecutive long-wick candles with stepping lows/highs |
| Touch counting | YES | 1176-1178 | ±0.15 ATR, 3-bar cooldown |
| Liquidity targets near price | YES | 1237-1240 `bslAbove/sslBelow` | within 3 ATR |
| Draw on liquidity | PARTIAL | TP2/TP3 `f_nearestLiq` | target only, not bias |

### ICT / SMC
| Feature | Exists | Where | Notes |
|---|---|---|---|
| FVG | YES | 977-989 | 3-candle, min 0.10 ATR, confirmed-bar gated |
| FVG mitigation | YES | 990-1014 | TOUCH / 50% / FULL modes |
| IFVG | NO | | |
| Order Block | YES | 1408-1472 | at BOS, from pivot candle; needs FVG within 3 bars; T1/T2/G1/G2 types; HP if sweep within 10 bars before |
| Breaker | YES | 1592-1604, 1663-1675 | OB closed through → BRK opposite side |
| Mitigation block | NO | | |
| Reclaimed block (RCB) | YES | 1477-1496 | at CHoCH, from the low/high leg with 50% fib gate |
| Rejection block (RJB) | YES | 1516-1535 | wick ≥0.5 candle, needs FVG within 2 bars + BOS within 15 |
| Quasimodo (QM) | YES (non-standard) | 1500-1513 | zone created when price breaks below `curLow` AFTER a bull CHoCH |
| Propulsion (PROP) | YES | 1631-1640, 1700-1709 | re-armed zone after tapped-50% + re-departure with FVG |
| Premium / Discount | YES (non-standard) | 1958-1969 | range = last `curLow..curHigh`; outside = neutral |
| Equilibrium | label only | 3336 | |
| OTE | NO | | |
| Dealing range | NO | tooltip 696 says majorLow..majorHigh, code uses curLow..curHigh (stale tooltip) | |
| Inducement (IDM) | YES | 1571-1575 | swing low above a demand zone swept before tap |
| Near-miss then sweep (★★) | YES | 1576-1580 | |
| Key Level score (KL) | YES | 1386-1403 | 1 + FVG + strong + hidden-interest + (vol) |

### Supply / Demand
| Feature | Exists | Notes |
|---|---|---|
| Supply / Demand zones | YES | = OB / BRK / RCB / RJB / QM (`atDemand/atSupply`) and SR/KL (`atSupport/atResist`) |
| Creation | YES | event-driven (BOS, CHoCH, wick candle, pivot) |
| Strength | YES | `depStrong`, `kl`, `hp`, `prop`, `nearSwept` |
| Freshness | YES | `touches`, `tapped`, `fiftyHit` |
| Mitigation | PARTIAL | touched → `tapped`; ≥2 touches → `sweepReq`; no depth-of-mitigation concept |
| Invalidation | YES | close through → `broken` (or FLIP for SR, BRK for OB) |
| Retest | YES | touch = `low <= z.top` (bull) |

### Price action
Breakout / breakdown (`breakUp/Dn` = BOS or RUN, 2029-2030) · fake break (2041) · inside bar (805, M03) · pin bar (800-801) · engulfing (803-804) · doji (802) · harami (806) · long-wick rejection (807) · shooting star (808-809) · IFC (812-813) · manipulative candle (814-815) · impulse / consolidation (`inRange` 2082, M72 `consolOk` 2812) · trendline auto (2241-2296, M64) · trendline break (2283-2289) · support / resistance (SR wick zones) · double top/bottom (2708-2717, M58) · FOMO run (M25) · wick-dominance (2052-2061).

### Trap trading
Bull/bear trap: M01, M02, M07, M24, M25, M29, M38-P2/P3/P5/P7, M62 (fakeout), M72 (operator trap), M53 (range trap), M54 (S&D trap), M48 (fake CHoCH). Failed retest: none explicit. Liquidity trap: M02 (name only — it is a continuation pattern).

### CRT / TBS / TWS
**NONE.** "CRT" appears only in the title (lines 3, 73). No candle-range-theory logic, no TBS/TWS.

### Timeframe
```
Current TF : chart
HTF        : f_htfAuto() → 1m→15, 3m→30, 5m→60 (aggr 30), 15m→240 (aggr 60), 30m→240, ≤4h→D, D→W, else M; or manual
LTF        : none (no request.security_lower_tf)
HTF data   : one request.security tuple (1792): O/H/L/C of HTF bar[1] and [2], pivothigh/low(3,3)[1], lookahead_on
             + "D" high[1]/low[1], "W" high[1]/low[1] (1862-1863), lookahead_on
HTF used   : hTrend (BOS-based), HTF sweep (3-bar validity), HTF manip candle, HTF rejection candle, HTF candle level lines
LTF data   : none
MTF dashboard: panel rows only (LTF trend / HTF bias / mismatch ⚠)
```

### Sessions
Asia 0000-0800, London 0700-1000, NY 1200-1500 via `time(timeframe.period, sess)` (1869-1871). **No timezone argument** → exchange timezone. No DST logic. Overlap 0700-0800 in defaults. Killzone hard filter default OFF, scoring +1 default ON. Asia H/L → SESH/SESL levels at London open.

### Entry models (traced chains)
All entries fire on the close of the current bar (`g.entry := close`), except M10 RETEST/BOTH (limit at swept level).

```
Group 1 — "at POI + reversal candle" (the dominant form, ~35 modules)
  zone touched this bar (ft.zKind != "")  →  zone-quality gate (sweepReq / 50%)  →  revBull/revBear candle  →  bid
  M04 M06 M08 M09 M12 M21 M23 M33 M36 M37 M39 M40 M42 M44 M51 M70 M73 (+ armed variants M41 M45 M46 M48 M49 M50 M52 M54 M68)

Group 2 — "post-break trap / continuation" (breakDir latched by BOS or RUN)
  break  →  1..8 bars  →  wick sequence / pin / inside bar / consolidation  →  bid
  M01 M02 M03 M05 M14 M15 M22 M24 M62 M63 M72 M38-P1..P7

Group 3 — sweep-immediate
  level resolved as SWEEP this bar  →  wick ≥ 0.40  →  close back beyond level  →  bid (M10)
  M47: st.bullSweep wick in trend (counter-trend fade)

Group 4 — pattern
  M58 double top/bottom neckline close · M65 trendline+level+counter-line break · M69 IFC candle close-through · M25 FOMO · M29 no-FVG BOS

Sequence modules (closest to ICT causal chain)
  M41: sweep → BOS strong w/ FVG (armed 30 bars) → at zone/FVG → reversal candle
  M45: sweep → BOS (or rare CHoCH) → at OB/BRK → reversal candle
  M54: demand touch → sweep low → BOS up → at zone → reversal candle
  M68: HTF sweep → LTF CHoCH → at zone/FVG → reversal candle
  M46: CISD + reliability → at zone/FVG → reversal candle or harami
```

### Exit / risk
| Item | Exists | How |
|---|---|---|
| SL | YES | `f_stop` 2958-2979: own-side zone edge → sweep extreme → major HL/LH (≤2 ATR) → candle extreme; ±0.15 ATR buffer; sanity ≤ 4 ATR |
| TP1 | YES | nearest opposite zone/FVG at ≥ minRR (2) and ≤ maxRR (6) × risk; or synthetic; or signal dropped if `rrReal` |
| TP2/TP3 | YES | nearest unresolved liquidity ≥ 1R beyond previous target, else +1R |
| Fixed-R mode | YES | TP1 = 2R, TP2 +1R, TP3 +1R |
| BE / trailing / partial | NO | text only in M47 note |
| Min RR / Max RR | YES | used (drop signal) |
| Risk % / sizing | NO | |
| Risk filter that blocks | YES | `rrReal`, `minScore`, `gate==0`, `sbSessOk`, `sigGap` |

### Signals
One `Sig` per side per bar. Grade A+ ≥6, A ≥4, B else (`f_gradeTxt`). Score = `f_conf` (2935-2955) **not** the module base score. Early vs confirmation: M10 IMMEDIATE = early; everything else = "confirmation" by one candle only. No "aggressive/conservative" model beyond M10 entry mode.

### Filters
HTF bias gate (OFF/WARN/STRICT, default WARN → −1 point) · LTF trend gate (same call) · PD gate (default off) · PD score (on) · killzone gate (off) / score (on) · min score 3 · min RR 2 / max RR 6 · real-target requirement · arrival-strength suppressor (M19) · corrective-pullback (M26) · retest body rule (M31, off) · sweep-required at touch≥2 (§6.2) · 50% rule (§6.6) · level-rejected-≥2× for M01/M02 · volume (M21/M22/M23/KL) · 4-factor INCOMPLETE −1 · both-sides tie → higher score · sigGap 10.

### Visuals
Signal labels (priority chain `f_add` 3196-3222, 12/13 ranks per side, cooldown & stacking) · structure lines (BOS/sweep/CHoCH/CISD) · live major H/L · liquidity lines + labels · FVG boxes · zone boxes with text · trendlines · HTF O/H/L/C lines · trade lines (entry/SL/TP1-3, 20 bars) · HTF bias background · info panel (14 rows) · legend · 18 data-window plots.

### Alerts
`alert()` dynamic per signal at `barstate.isconfirmed` (3378-3381) — same logic as label ✓.
`alertcondition` ×12 (3386-3397): 4 signal alerts gated on `isconfirmed`; **8 structure/liquidity/zone alerts NOT gated** (BOS, CHoCH real, CISD, sweep, hidden liq, new HP OB, PROP, OB 50%).

---

## 3. FEATURE STATUS MATRIX

Repaint column = risk of historical ≠ realtime (see §7). Status = audit verdict.

| Feature | Exists | Location | Active (default) | Used for entry | MTF | Repaint | Status |
|---|---|---|---|---|---|---|---|
| Swing H/L (5,5) | YES | 1850 | YES | indirect | NO | LOW (5-bar lag, honest) | KEEP |
| BOS | YES | 826 | YES | YES (break state, M41/45/51/54, zones) | NO | LOW | **IMPROVE** (no hierarchy, no displacement requirement) |
| CHoCH | YES | 860 | YES | M45★/M48/M52/M68/RCB/QM | NO | LOW | **REBUILD** (mostly unreachable) |
| MSS | NO | — | — | — | — | — | ADD (as part of structure rebuild) |
| Trend | YES | 851… | YES | gate, f_conf, many modules | NO | LOW | REBUILD with structure |
| Displacement | PARTIAL | 1033, 1913 | YES | M41, M42, M51, KL, OB | NO | LOW | IMPROVE (make it a state gate) |
| CISD | YES | 932 | YES | M46 | NO | LOW | REBUILD (not ICT CISD) |
| Pullback PB✓ | YES | 903 | YES | leg counters only | NO | LOW | KEEP |
| Move phase | YES | 955 | YES | M06/M07/M23 | NO | LOW | IMPROVE |
| Wyckoff | YES | 957 | panel | NO | NO | — | REMOVE / rename |
| BSL/SSL/EQH/EQL | YES | 1084 | YES | M10, f_conf, TP2/3 | NO | LOW | KEEP |
| PDH/PDL/PWH/PWL | YES | 1862 | YES | sweptMajor, TP | YES | LOW (`[1]`+lookahead_on = safe) | KEEP (detach from Show toggle) |
| SESH/SESL | YES | 1930 | YES | sweep kind | NO | LOW | IMPROVE (timezone) |
| Sweep / Run classifier | YES | 1161 | YES | M10, M41, M45, M54, f_conf | NO | LOW | KEEP |
| Hidden liquidity | YES | 1262 | YES (label tier All) | M38-P4, M43 (off) | NO | LOW | KEEP (low value) |
| Internal liquidity | YES | 2215 | YES | M49 (off) | NO | LOW | KEEP |
| FVG | YES | 977 | YES | OB validity, strength, reactBull, TP1, f_conf | NO | LOW (confirmed-gated) | KEEP |
| OB | YES | 1408 | YES | M36/37/42/45/48 | NO | LOW | **IMPROVE** (origin index bug, pivot-candle heuristic) |
| Breaker | YES | 1592 | YES | M36/37/45/48 | NO | LOW | KEEP |
| RCB | YES | 1477 | YES | M39 | NO | LOW | IMPROVE (CHoCH-dependent) |
| RJB | YES | 1516 | YES | M40 | NO | LOW | KEEP |
| QM | YES | 1500 | YES | M70 | NO | LOW | REBUILD (concept mismatch) |
| PROP | YES | 1631 | YES | M73 (base 7) | NO | LOW | KEEP |
| KL score | YES | 1386 | YES | M12/M44/M58/f_conf | NO | LOW | KEEP |
| SR wick zones | YES | 1369 | detection always, draw off | slot only if KL≥3 | NO | LOW | KEEP |
| Zone lifecycle (touch/flip/broken/sweepReq/50%) | YES | 1538-1757 | YES | all zone modules | NO | LOW | IMPROVE (single-slot) |
| HTF bias | YES | 1798 | YES | gate, f_conf, M33, M48 | YES | LOW | IMPROVE (lag, any-BOS flip) |
| HTF sweep / manip / rej | YES | 1801, 1836 | YES | M46, M68 | YES | LOW | KEEP |
| PD array | YES | 1958 | score on / gate off | f_conf | NO | LOW | IMPROVE (range definition) |
| Sessions | YES | 1869 | score on / gate off | f_conf, sbSessOk | NO | LOW | IMPROVE (timezone) |
| Trendlines M64 | YES | 2241 | YES (draw) | M12/M65 (off) | NO | LOW | KEEP |
| Break state / fakeBreak | YES | 2029 | YES | M01-05, M14, M15, M22, M24, M62, M63, M72, M38 | NO | LOW | KEEP |
| Arrival strength | YES | 1976 | YES | M19/M26/M33/M36/M42/f_conf | NO | LOW | KEEP |
| Setup library M01-M73 | YES | 2307-2868 | 27 on / 26 off by default | YES | — | LOW | IMPROVE (prune, unify scoring) |
| f_conf score | YES | 2935 | YES | grade, minScore, tie-break | — | — | REBUILD (merge with base score) |
| SL engine | YES | 2958 | YES | YES | — | — | KEEP |
| TP engine | YES | 2893, 2920 | YES | YES | — | — | IMPROVE (target quality filter) |
| Min/Max RR, real target | YES | 3010-3034 | YES | YES | — | — | KEEP |
| sigGap / both-sides | YES | 3087-3105 | YES | YES | — | — | KEEP |
| Labels / lines / boxes | YES | 3107+ | YES | NO | — | LOW (all confirmed-gated) | KEEP |
| alert() | YES | 3378 | YES | — | — | LOW | KEEP |
| alertcondition (signal) | YES | 3386-3389 | YES | — | — | LOW | KEEP |
| alertcondition (events) | YES | 3390-3397 | YES | — | — | **HIGH** (unconfirmed) | FIX |
| CRT / TBS / TWS / OTE / IFVG / BE / trail / sizing | NO | — | — | — | — | — | not present (title is misleading) |

---

## 4. ARCHITECTURE MAP (as discovered)

```
                       GLOBAL SERIES (1849-1872)
        atr · pivots(5,5) · ext 50 · vol sma/linreg · range hi/lo · PDH/PDL "D" · PWH/PWL "W" · sessions
                                       │
   ┌───────────────┬───────────────────┼───────────────────┬────────────────────┐
   │               │                   │                   │                    │
 L0 f_candle    L2 f_fvg           L1 f_structure       L5 request.security   Asia H/L → SESH/SESL
 (cd)           (ctx.fvgs)         (st, ctx.cur/prev/    (HTF OHLC[1],[2],     (into ctx.lv)
   │               │                 major, trend)         pivots[1])
   │               │                   │                   │
   │               │        L2 f_moveStrength (mv)         │
   │               │        only on BOS / CHoCH bar        │
   │               │                   │                   │
   │               └──────► L3 f_liq (ctx.lv) ◄────────────┼─ PDH/PDL/PWH/PWL
   │                            │  sweep / run / touches   │
   │                            ▼                          │
   │                   L4 f_zones (ctx.zones)              │
   │                   SR@pivot · KL@BOS · OB@BOS · RCB/QM@CHoCH · RJB@wick
   │                   per-bar: touch / 50% / IDM / near-miss / flip / BRK / PROP / broken
   │                   → single best-zone slot in ft (zKind, at*, z*)
   │                            │                          │
   │                            ▼                          ▼
   │                   L5 f_htf → ft.htfBias, htfSweep, htfManip, htfRej
   │                   f_gate(bias, preTrend) → ft.gateUp/gateDn (2 pass · 1 warn · 0 block)
   │                   PD array (curLow..curHigh) → ft.pdPct, optional gate
   │                            │
   └────────────────────────────┼─────────── orchestration features (1971-2305):
                                │            arrival strength · leg counters · wick sequences · break state
                                │            · wick dominance · range · at-FVG · M41/45/46/48/52/54 latches
                                │            · internal liq · brkTouches · trendlines · M71 time-at-level
                                ▼
                   L6 SETUPS  s01…s73b  (≈60 booleans over cd/st/ft/ctx/sx)
                   f_bid(bL|bS, cond, name, baseScore, note)   ← strictly-greater, declaration order on ties
                                │
                                ▼
                   L7 f_sig  (per side, if bL.n != "" and gate>0 and session ok)
                     entry=close (M10: swept level) → f_stop → TP1 f_nearestOpp(minRR..maxRR) → TP2/3 f_nearestLiq
                     score = f_conf(ft, preTrend, dir)  [base score discarded]
                     − gate WARN −1 · − INCOMPLETE −1 · < minScore → drop · rrReal & no target → drop
                                │
                   both sides same bar → higher score wins · sigGap 10 (opposite stronger overrides)
                                │
              ┌─────────────────┼─────────────────┐
           labels (f_add      trade lines        alert() + alertcondition
           priority chain)    entry/SL/TP1-3     (signal ones confirmed; event ones NOT)
```

Execution-order dependencies that matter:
1. `f_structure` shifts `cur→prev` pivots **before** `f_zones` reads `cx.curLowIdx` (1379) → see §5-B1.
2. `mv` is refreshed only on a confirmed BOS/CHoCH bar; every other reader (`ft.dispBull`, `p1/p2`, `w29/w51`, KL score) sees the last BOS's value.
3. `preTrend` (trend as bar opened) feeds the gate and `f_conf`; `st.trend` feeds modules (`bullTrend`) → a BOS bar's modules see the flipped trend while the gate sees the old one (intended, M9).
4. `ft.zKind` is one slot: the highest-priority zone touched, either side.

---

## 5. CODE FORENSIC FINDINGS

### B1 — Leg-origin index inconsistent (P1)
`f_moveStrength` on a BOS bar uses `preLowIdx/preHighIdx` (1897-1899, deliberately the pre-shift pivot). `f_zones` on the same bar uses `cx.curLowIdx/curHighIdx` (1379) **after** `f_structure` may have shifted them (886-897), and so do RCB (1478/1490), QM head (1487/1498) and arrival strength (1977). When a BOS bar is also a pivot-confirmation bar (common in fast legs: the origin low confirms as a pivot exactly 5 bars after it printed while price closes through the prior high), the two engines measure two different legs. Neither definition is correct in general: the origin of a bull BOS leg is the lowest low between the broken swing high and the break bar, not whichever pivot the bookkeeping holds.
*Impact:* OB placed on the wrong candle (and therefore FVG-alignment test on the wrong window → T3/T5 false verdicts), KL score written to the wrong SR zone (`z.idx == oIdx`), `dispBull` measured over the wrong leg.

### B2 — Structure hierarchy absent; CHoCH mostly unreachable (P1)
`bullBOS` (826) fires on any close above the last confirmed pivot high, including a lower high inside a downtrend, and immediately sets `trend := BULLISH` (858). `bullCHoCH` (860) requires `trend == BEARISH and close > majorHigh`, but `majorHigh ≥ curHigh` is an invariant after every `bearBOS` (843-852), so any close above `majorHigh` is also a close above `curHigh` → `bullBOS` runs first and flips the trend → CHoCH is false. CHoCH can only fire when (a) `hiBroken` was still latched from an earlier break (the whipsaw case), or (b) a pivot high formed above `majorHigh` by wick and price later closes between them. The authors' own note (2125-2128, 3177-3178) confirms "a BOS flips the trend before the CHoCH test runs".
*Consequence:* the ICT CHoCH (close through the last LH in a downtrend) is emitted as **"BOS▲" with a trend flip**; the "CHoCH" label is an accidental residual; the RANGE state (20 bars without an event) is rarely reached in chop because chop produces pivot breaks; every CHoCH-dependent module (M45★, M48, M52, M68, RCB, QM) is starved or fed the wrong event.

### B3 — Displacement is measured, never enforced (P1)
`mv.strong` is computed on BOS (1899) and only annotates ("BOS weak", `dispScore`, KL, OB validity). A weak BOS still flips `trend`, re-anchors `majorHigh/Low`, arms `breakDir` and re-anchors the pullback makers (924-930). Market structure changes on wick-noise closes.

### B4 — Event `alertcondition`s fire on unconfirmed intrabar state (P1)
Lines 3390-3397 (`BOS`, `CHoCH real`, `CISD`, `Sweep`, `Hidden liquidity`, `New HP OB`, `PROP`, `OB 50%`) have no `barstate.isconfirmed`. `st.*`, `f_liq` resolutions, `newProp`, `enteredOb50` are computed on every tick and rolled back; a "once per bar" alert fires on the first tick that satisfies them and cannot be un-fired when the close invalidates the condition. `ft.chochReal` is additionally stale intrabar because `mc` is only computed at `isconfirmed` (1903). Signal alerts (3378-3389) are correct.

### B5 — Sessions in exchange timezone, no DST, overlapping defaults (P2)
`time(timeframe.period, i_ssn*)` (1869-1871) without a timezone argument. "0700-1000 London" is only London when the exchange is UTC (Binance). On broker-TZ forex feeds (e.g. `America/New_York`) the windows shift by 4-5 h and drift with DST. Defaults Asia 0000-0800 and London 0700-1000 overlap → `lonOpen` fires at 07:00 while Asia is still accumulating, so SESH/SESL are placed from a partial Asia range (1930-1937).

### B6 — PD array is not a dealing range (P2)
`pdHi/pdLo = ctx.curHigh/curLow` (1958-1959): the last two confirmed pivots, which are consecutive and often not the leg's extremes. Outside them (most of a trend) `pdPct = 0.5` → neutral. The tooltip (696) still says "majorLow..majorHigh". Neither is the ICT dealing range (external low to external high of the current leg / last sweep-to-sweep).

### B7 — Two scoring systems, base score discarded (P2)
Module base score (2-9) only selects the candidate via strictly-greater `f_bid` (2491). The displayed score, grade, `minScore`, both-sides tie and sigGap override all use `f_conf` (3042), which is module-agnostic. M37 (base 7) and M03 (base 3) can show identical "A5". Equal base scores resolve by declaration order (acknowledged "M13 still open").

### B8 — TP1 accepts junk targets (P2)
`f_nearestOpp` (2893) ignores `srOk`, `z.weak`, `z.confirmed`, `z.kl`: an unscored pivot wick zone or an unconfirmed RJB is a "real target". Combined with 30-60 zones retained, a real-looking 2R target is almost always found, defeating `rrReal`.

### B9 — QM zone created on CHoCH failure (P2)
After `bullCHoCH`, a `low < cx.qmBullLL` (1503) — price trading below the low that the CHoCH was measured from — creates a **bullish** QM zone at that new low. With the 5-bar pivot lag `curLow` is usually the shoulder, so sometimes this is the QM level; but when it is the head, the code turns a failed CHoCH into a demand zone. No structural check distinguishes the two.

### B10 — Single zone slot hides the tradable zone (P2)
1720-1747: `ft.zKind/at*` describe one zone (highest priority, any side). Price inside an overlapping supply OB (priority 6) and a demand RCB (4) reports only supply → `atDemand` false → every long module is silently off there. `f_stop` works around it (2964) but modules do not.

### B11 — `mv` stale for RUN-driven breaks (P3)
`breakUp` = BOS **or** RUN (2029). `p1/p2` (2467-2468) and M22/M24 read `mv.strong` which was last computed on a BOS, not on this RUN.

### B12 — Liquidity eviction fallback (P3)
1245-1257: if no `done` or unpooled BSL/SSL is found, `wIdx = 0` evicts index 0, which may be a PDH/PWH/SESH.

### B13 — Detection tied to Show toggles (P3, same class as fixed C3)
`newDay = i_showPD and …` (1864), `newWeek = i_showPW and …` (1865): turning off PD/PW lines also removes the levels from `sweptMajor`, TP2/3 and M10's pool test.

### B14 — M10 wick test on the wrong candle (P3)
When the sweep resolves through the 2-bar `pend` path (1162-1168), `cd.dnWickRatio` (2397) is the resolving candle's wick, not the sweep candle's.

### B15 — Visual anchoring implies knowledge before it existed (P3)
Zone boxes / liquidity lines start at the pivot bar (`f_xb(idx)`), 5 bars before the pivot could be known; `f_xb` also pins anything older than 495 bars to the buffer edge (967), giving wrong start points on long charts. Signals themselves are anchored at the current bar (honest).

### Verified clean
- `request.security(..., lookahead_on)` with `[1]`/`[2]` offsets (1792-1795, 1862-1863): standard non-leaking pattern. HTF pivot lag = `i_htfSwing + 1` HTF bars (honest, but late).
- Pine rollback covers `var` UDTs, arrays and drawings, so intrabar state mutation in `f_structure/f_liq/f_zones` recommits identically at the close; historical and realtime final state agree. All drawing creation is `isconfirmed`-gated.
- Array removal inside reverse loops (`f_fvg`, `f_liq`, `f_zones`) is safe. `max_bars_back=500` covers all variable-offset history reads (`off < 500/490`).
- Object caps FIFO everywhere; `label.all/line.all/box.all` plotted for verification.
- `na` handling is defensive throughout (`nz`, `not na` guards).

---

## 6. TRADING LOGIC FINDINGS (market-operator view)

| # | Finding | Why it matters |
|---|---|---|
| T1 | "BOS" = any pivot-close break; trend = last break direction | Every corrective LH break in a downtrend reads as BULLISH bias → longs authorised into a bear leg; trend flips 3-6× inside one consolidation |
| T2 | No internal/external structure | Internal liquidity runs are counted as structure; external liquidity (50-bar extreme) is tracked only as a level flag (`ext`), not as structure |
| T3 | Sweep does not require prior liquidity significance | Any pivot becomes a level; `sweptMajor` (touches≥2 or PD/PW/SES) is used only for labels and `runMajor`; M10 still accepts a plain pivot sweep if price is in any zone |
| T4 | Displacement not required for BOS/CHoCH | "Break on close by 1 tick" changes the whole state; the ICT requirement (energetic candle + FVG) is only a score/annotation |
| T5 | Entry trigger = one reversal candle (pin/engulf/IFC/manip) at a zone | Institutional entry model wants: sweep → displacement → MSS on LTF → return to POI. Most modules skip the MSS step; the candle is the only confirmation |
| T6 | PD array from last pivot pair | In a trend the range is a few bars wide and price sits "outside" → PD contributes nothing exactly when it should (buying premium in an up-leg) |
| T7 | HTF bias = HTF "last BOS direction", lag 4 HTF bars | 5m chart on 1h HTF: bias flips 4h after the fact and on any 1h pivot break; "NEUTRAL" until first HTF BOS makes the gate open by default |
| T8 | Zone freshness = touch count with 3-bar cooldown | A zone tapped once for 10 bars counts as fresh (1 touch); a zone tapped twice 4 bars apart is "sweep required". Mitigation depth (how far into the zone, whether the 50% was consumed) is only a boolean |
| T9 | SR wick zones at every pivot as raw material | Correct that they are gated by KL≥3 for the slot, but they still serve as TP1 targets and count in `f_hiddenInterest` |
| T10 | QM / RCB derived from CHoCH events that mostly don't occur | Their supply of zones is accidental (see B2) |
| T11 | CISD = close through the open of the first green candle after the last valid pullback | This is a leg-invalidation, not ICT CISD (close through the opening price of the last up-close series that delivered the high, after a sweep). It fires late in extended legs and early on any pullback |
| T12 | Killzone score in exchange TZ | +1 to the wrong hours on most forex feeds |
| T13 | M02 named "liquidity trap" but is a continuation breakout pattern; M45 named "sweep CHoCH" but is sweep+BOS continuation (documented) | Names mislead the operator reading the label |
| T14 | Wyckoff label = trend × range-width | Not Wyckoff; "ACCUMULATION" prints on any tight range in a bear trend |

---

## 7. REPAINTING AUDIT

| Source | Verdict | Detail |
|---|---|---|
| `request.security` HTF tuple, lookahead_on | **SAFE** | all expressions offset `[1]`/`[2]` inside the call; `timeframe.change` drives one-shot processing |
| `request.security` D/W, lookahead_on | SAFE | `high[1], low[1]` |
| `ta.pivothigh/low(5,5)` | SAFE, lagged | detection on confirmation bar; anchors drawn back 5 bars (visual only) |
| HTF `ta.pivothigh(3,3)[1]` inside security | SAFE, lagged | 4 HTF bars |
| Intrabar state mutation (`f_structure`, `f_liq`, `f_zones` maintenance) | SAFE | Pine rollback recommits from last confirmed bar each tick; final tick has `isconfirmed=true` so the realtime close == historical bar |
| `barstate.isconfirmed` gating asymmetry (FVG, OB/KL, RCB, QM, RJB, arrival, SESH) | SAFE | historical bars are always confirmed; realtime last tick is confirmed → same result |
| Labels / lines / boxes / trade lines | SAFE | all creation gated on `isconfirmed` |
| `alert()` | SAFE | gated |
| `alertcondition` signals (×4) | SAFE | gated |
| `alertcondition` events (×8) | **REPAINTS** | fire intrabar; condition may not exist at close (B4) |
| `bgcolor(htfBias)` | SAFE | derived from confirmed HTF state |
| `barstate.islast` panel | n/a | display only |
| `f_xb` clamp | visual | anchors pinned to buffer edge on old objects |

Historical Signal == Realtime-Knowable: **YES for chart signals, labels, trade lines, alert(); NO for the eight event alertconditions.**

---

## 8. MARKET STRUCTURE AUDIT

- **Swing definition**: symmetric 5/5 pivots. OK for a base, but the same length feeds structure, liquidity, SR zones, trendlines and double tops — no minor/major swing distinction.
- **BOS**: `close > curHigh`, one-shot per pivot. No displacement, no minimum break distance, no requirement that the broken high be structural (HH/LH). Re-arms on every new pivot even when the new pivot is below the last broken level → internal-range breaks emitted as BOS with trend flips.
- **CHoCH**: defined against `majorHigh/Low` (anchored on BOS/CHoCH), but pre-empted by BOS in virtually all cases (B2). Reachable only in whipsaw/wick-pivot edge cases. The label "CHoCH? / CHoCH✕" on the review charts comes from those edge cases.
- **MSS**: absent.
- **Trend**: last event direction; RANGE only after 20 quiet bars. Not a swing-sequence (HH/HL vs LH/LL) model.
- **CISD**: see T11; reset by `pbValid*` and by its own trigger; mother-candle rule is a reasonable touch.
- **Pullback**: valid when price trades through the extreme-maker candle's opposite side. Reasonable one-shot.
- **Move phase**: `close >= curHigh` → IMPULSIVE. Every bar inside the last swing range = RETRACEMENT, including the first bars of a fresh impulse.
- **HTF structure**: same BOS-only model with 4-bar lag; `hMajor*` only re-anchors on LH/HL, so `hTrend` flip via "CHoCH" (1817-1820) is possible there but late.

Verdict: **REBUILD** the structure engine (swing classification → BOS only in trend direction on a structural swing with displacement → CHoCH/MSS = close through the last protected swing against trend with displacement → RANGE = failed follow-through, not a bar count).

---

## 9. LIQUIDITY AUDIT

- Levels: every pivot; EQH/EQL merge (0.10 ATR) → POOL; PD/PW/SES; `ext` flag at 50-bar extreme. Good coverage.
- Sweep classifier (1161-1196): wick-through + close-back = SWEEP; body ≥0.6 & close ≥0.25 ATR beyond = RUN; else 2-bar pend. Sound and consistent with "sweep = rejection, run = acceptance".
- Weaknesses:
  - Sweep quality (pool / external / PD / session) is not required by M10 when price is in any zone (2397: `sweptPool or zKind != ""`), and the zone slot is filled easily on low TFs.
  - `sweptHighBar/LowBar` are set both by level sweeps and by `st.bullSweep/bearSweep` (1888-1891) — a wick beyond the *last pivot* (not a liquidity level) arms OB-HP, M41, M45, M54, the `✕` CHoCH marker and `f_conf` sweep credit. Pivot wicks are the most common event on a 1m chart.
  - Hidden liquidity: ok as a label; as a setup (M43/M38-P4, off by default) it is just "3 wicks".
  - Internal liquidity (M49) exists but `intLowB` is refreshed on every swing inside the leg, so "internal" = "most recent swing" in practice.
  - Draw-on-liquidity is not a bias input; only a TP.
- Verdict: **KEEP** the level engine; **IMPROVE** by separating "pivot wick" from "liquidity sweep", and requiring a significant level (pool / ext / PD / PW / SES / HTF) for sweep-based arming.

---

## 10. FVG / OB / S&D AUDIT

**FVG**: correct 3-candle definition, confirmed-gated, min height, three mitigation modes, FIFO 40, age-out 300 bars after mitigation. TOUCH mode marks a bull FVG mitigated on any touch of its top — aggressive but consistent. No IFVG. No "FVG inside displacement leg only" filter (any gap counts). **KEEP.**

**OB**: created only on BOS with `mv.strong` and an FVG within 3 bars of the OB candle (1441) — this is the right ICT gate. Candle selection = the pivot candle (G1 always resolves to it via T2; the "last opposite candle before displacement" is not searched). Origin index bug B1. HP = sweep within 10 bars before. **IMPROVE**: fix origin, select the last opposite-colour candle before the displacement candle, keep the FVG gate.

**Breaker**: OB closed through → opposite side, state reset (M11 fix). **KEEP.**

**RCB / QM**: CHoCH-driven → starved (B2), QM concept issue (B9). **REBUILD after structure.**

**RJB**: wick ≥0.5 candle, FVG within 2 bars, BOS within 15 bars else dropped; `weak` if next candle re-enters. Sensible. **KEEP.**

**PROP**: needs 50% hit, re-departure 0.8-2.4 ATR with FVG inside 10 bars. **KEEP.**

**Zone lifecycle**: touch → tapped; 50% → fiftyHit; ≥2 touches → sweepReq; close through → broken / FLIP / BRK; broken zones deleted after 20 bars; untouched after 500; overlap refresh (R7); SR cap and 2×max cap. Solid. Gaps: single slot (B10); no mitigation-depth; `lastTouch` initialised to creation bar so the first touch inside 3 bars of creation is not counted (RJB at `bar_index-1` can be tapped immediately).

**S&D**: there is no separate S&D engine; "demand/supply" = the ICT zones above, "support/resistance" = KL-scored pivot wick zones. Fine, but the labels and legend suggest more.

---

## 11. ENTRY ENGINE AUDIT (BUY chain; SELL is the mirror)

| Step | Status | Where |
|---|---|---|
| HTF context | PARTIAL | `htfBias` from HTF BOS model, WARN gate (−1) not block; NEUTRAL passes |
| Liquidity map | IMPLEMENTED | `ctx.lv` |
| Liquidity event (sweep) | IMPLEMENTED but under-qualified | any pivot wick counts as swept (§9) |
| Displacement | PARTIAL | measured; required only in M41/M42/M51/OB creation |
| Structure confirmation (MSS/CHoCH) | INCORRECT / MISSING | B2 — BOS-with-flip stands in for it |
| POI | IMPLEMENTED | OB/BRK/RCB/RJB/QM/PROP/KL/FVG |
| Retracement into POI | IMPLEMENTED (touch) | `ft.zKind`, `atBullFvg`; 50% rule optional |
| Entry trigger | IMPLEMENTED (weak) | single reversal candle at close; no LTF MSS |
| Risk validation | IMPLEMENTED | minRR/maxRR/real target/minScore/gap |
| SL | IMPLEMENTED | zone → sweep → major → candle |
| TP | IMPLEMENTED | zone/FVG then liquidity ladder |
| Alert | IMPLEMENTED | same as chart |

Modules closest to the full chain: M41, M54, M68, M45. Modules that are pure "candle at zone": M08, M36, M37, M39, M40, M42, M70, M73 (and the top-scored ones are among them).

---

## 12. FEATURE INTERACTION AUDIT

| Interaction | Finding |
|---|---|
| Liquidity + BOS | `sweepBosBull` (2130) is the continuation shape; used to arm M45 — the module text says "CHoCH retest". Works, mislabelled. |
| Liquidity + CHoCH | Intended reversal chain; CHoCH mostly does not occur → M45★ (+1), M68, M52, M48 rarely fire. |
| Liquidity + FVG | `reactBull = zoneOkBull or atBullFvg` (2585): FVG counts as POI for the armed modules only; fine. |
| Liquidity + OB | HP OB = sweep within 10 bars before OB candle; sweep source includes plain pivot wicks → HP★ inflated on low TFs. |
| BOS + FVG | OB requires FVG near the origin; `dispBull` requires strong; but state (trend) ignores both. |
| MSS + OB | not possible (no MSS). |
| HTF bias + LTF entry | WARN gate: counter-HTF signals allowed with −1. With `minScore=3` and base 1 + easy points (fresh zone +1, session +1, liquidity target +1) counter-trend signals pass routinely. Intentional per R9, but the conflict is not resolved — it is priced at 1 point. |
| Trend + gate | `preTrend` for gate/f_conf vs `st.trend` for modules: on a BOS bar the module thinks the trend flipped while the gate docks it. Documented; produces "⚠vs HTF/trend" on the very signals that are structurally best (first pullback after a real CHoCH). |
| Supply + Liquidity | `zSweepReq and not swept` → −2; ok. `zIdm` side-agnostic in f_conf (2942) — a supply zone's IDM credits a long. |
| Trap + Structure | M62/M72/M01/M24 latch on `breakDir`, which is set by BOS **or** RUN; a RUN through a level that is not structure still becomes "the level" for trap modules — acceptable, but mv is stale (B11). |
| Zone slot + opposite zones | B10. |
| Score vs base | B7: the module that won may not be the one the score describes. |
| sigGap + sides | ok; the opposite-stronger override uses f_conf, so a weaker module with more feature points overrides a stronger module. |
| PD + gate | gate only inside the tiny pivot range; harmless because off by default, useless because of B6. |
| Session + everything | B5. |
| Show toggles + detection | PD/PW (B13). Everything else decoupled (C3 fix verified). |

---

## 13. ROOT CAUSE ANALYSIS

```
RC1  Symptom : trend flips constantly; CHoCH labels rare and odd; RANGE seldom in chop; CHoCH-dependent
              modules starve; counter-trend "BOS▲" longs in bear legs.
     Code    : bullBOS = close > last pivot high, sets trend; CHoCH tested after; majorHigh ≥ curHigh invariant.
     Logic   : no swing classification, no protected swing, no displacement requirement for state change.
     Root    : structure engine is a "last pivot break" detector, not a market-structure model.
     Impact  : bias, gate, f_conf (+1 trend), M33/M48/M51/M53/M06/M08 direction, majors for SL, PD range.
     Fix     : rebuild L1 (see §14).

RC2  Symptom : A5 label on a weak module; declaration order decides ties; "▲▲ A+" common after KL/PROP inflation.
     Code    : f_bid strictly-greater base score; f_sig overwrites score with f_conf.
     Root    : two scoring systems, no priority tiers.
     Fix     : one score = tier(module) + confluence; ties by tier then by sequence completeness.

RC3  Symptom : OB on the wrong candle; T3/T5 verdicts on good moves; KL score lost.
     Code    : f_zones reads cx.curLowIdx after pivot shift (1379); moveStrength uses pre-shift (1899).
     Root    : leg origin defined by pivot bookkeeping instead of by price (lowest low since broken high).
     Fix     : compute origin = bar of lowest low/highest high between broken swing idx and bar_index; use everywhere.

RC4  Symptom : many signals at every zone tap, best-scored modules are "candle at zone".
     Code    : zoneOkBull + revBull is the trigger for ~25 modules.
     Root    : entry model lacks the confirmation step (LTF MSS / displacement away from POI); the candle is the only proof.
     Fix     : introduce a POI-reaction state machine: tap → displacement away (FVG) or micro-MSS → entry on retrace or on the confirming close; keep IMMEDIATE as an explicit aggressive mode.

RC5  Symptom : event alerts fire and no matching label/line appears.
     Code    : alertcondition on unconfirmed st/ft flags.
     Root    : alert path not unified with draw path.
     Fix     : gate all alertconditions on barstate.isconfirmed (or build them from the same confirmed Tag).

RC6  Symptom : killzone score wrong on forex; SESH placed from partial Asia range.
     Code    : time() without timezone; overlapping defaults.
     Root    : session semantics not pinned to a timezone.
     Fix     : add timezone input (default "UTC" or "Europe/London"/"America/New_York" per window), non-overlapping defaults.

RC7  Symptom : "real target" found almost always; 2R labels pointing at pivot wicks.
     Code    : f_nearestOpp ignores zone quality.
     Root    : target quality not modelled.
     Fix     : targets = scored KL, unmitigated OB/BRK/RCB/FVG, POOL/PD/PW/SES/HTF levels only.
```

---

## 14. PRIORITY MATRIX

| Prio | Item |
|---|---|
| **P0** | none of the classic P0s (no lookahead leak, no future data, drawings & signals confirmed). Closest to P0: **B4** event alertconditions repaint (treated as P1 because chart signals are unaffected). |
| **P1** | B2/RC1 structure hierarchy & CHoCH · B1/RC3 leg origin · B3 displacement not enforced · B4 event alerts · RC4 entry confirmation missing |
| **P2** | B5/RC6 sessions TZ · B6 PD range · B7/RC2 scoring split · B8/RC7 TP targets · B9 QM · B10 zone slot · T3 sweep qualification · T7 HTF lag/NEUTRAL · CISD definition |
| **P3** | B11 stale mv on RUN · B12 eviction fallback · B13 PD/PW show-toggle · B14 M10 wick candle · B15 anchors · Wyckoff label · stale tooltip 696 · module naming (M02, M45) · legend/labels |

---

## 15. KEEP / IMPROVE / REBUILD / REMOVE / ADD

**KEEP** — candle anatomy; pivots; FVG engine; liquidity level engine & sweep/run classifier; PD/PW/SES levels; breaker conversion; RJB; PROP; KL scoring; zone lifecycle mechanics; arrival strength; break-state & trap modules (M01/02/05/62/72); SL engine; min/max RR & real-target rule; sigGap & both-sides rule; label priority chain; trade lines; signal alerts; data-window diagnostics; object budgeting; feature-vector architecture itself.

**IMPROVE** — OB candle selection & origin (B1); displacement as a gate (B3); sweep qualification (pivot wick ≠ liquidity sweep); HTF engine (structure rules, NEUTRAL handling, lag awareness); PD array (dealing range = leg extremes / sweep-to-sweep); sessions (timezone, defaults); TP target quality; zone slot (per-side best zone); event alerts (confirm); move phase; module names; PD/PW toggles.

**REBUILD** — L1 structure (swing classification, BOS/CHoCH/MSS with displacement, protected swings, range by failed follow-through); CISD; QM/RCB derivation (after structure); scoring (single tiered score).

**REMOVE** — Wyckoff label (or rename "Regime"); "CRT" from title until implemented; M43/M38-P4 hidden-liquidity setups (3-wick pattern, off by default, low value); duplicate mirror text noise in notes; stale tooltip text.

**ADD (only what the findings need)** — MSS/CHoCH proper; leg-origin helper; POI-reaction state (tap → displacement/micro-MSS → entry); timezone input; target-quality filter; confirmed alert conditions. Not CRT/TBS/TWS/OTE — nothing in the audit requires them.

---

## 16. IMPROVEMENT ROADMAP (implementation order)

1. **Alerts** (B4): gate 8 alertconditions on `barstate.isconfirmed`. Zero risk, immediate.
2. **Leg origin helper** (B1): `f_legOrigin(isBull, fromIdx)` = index of lowest low / highest high in `[fromIdx, bar_index]`; use in `f_moveStrength`, OB block, KL lookup, RCB, arrival.
3. **Sessions** (B5): timezone input(s), non-overlapping defaults, SESH/SESL placed at Asia *end* not London open.
4. **Structure rebuild** (B2/B3): 
   - classify each confirmed pivot HH/HL/LH/LL against the previous same-side pivot;
   - BOS = close beyond the last HH (bull trend) / LL (bear trend) **with** `mv.strong` (or dispScore ≥ 1) → trend continues, protected swing = last HL/LH;
   - CHoCH/MSS = close beyond the protected swing against trend with displacement → trend flips; without displacement → "weak break" flag only, no state change;
   - RANGE = two consecutive failed follow-throughs (break then close back) or N bars, whichever first;
   - keep `st` field names so L6 is untouched; add `st.internalBOS` for the demoted breaks.
   - Re-derive `majorHigh/Low` = protected swings; RCB/QM off the new CHoCH.
5. **Sweep qualification**: `sweptHighBar/LowBar` only from level sweeps whose level is POOL / ext / PD / PW / SES / HTF; pivot wicks (`st.*Sweep`) become `internalSweepBar` for M47/M53 only.
6. **Scoring unification** (B7): `score = tier(module) [1..4] + f_conf`; drop base-score bidding; ties → sequence completeness (sweep→disp→MSS→POI count).
7. **PD array** (B6): range = leg origin ↔ leg extreme (from step 4's protected swing to current extreme); expansion beyond = 1.0/0.0 clamp with a "beyond range" flag, not neutral.
8. **TP quality** (B8): filter in `f_nearestOpp` (`srOk`, `confirmed`, `not weak`), add HTF levels.
9. **Zone slot** (B10): compute best bull zone and best bear zone separately; `ft.atDemand` from the bull slot.
10. **CISD rebuild**: reference = open of the first candle of the last same-colour series into the swing extreme; valid only after a qualified sweep; consumed on trigger.
11. **POI reaction state** (RC4): optional "CONFIRMED" entry mode: zone tap → wait for displacement away (new FVG in trade direction) or micro-MSS (close beyond the reaction candle's extreme) → entry on next retrace into FVG or at the confirming close.
12. Cosmetics: Wyckoff → Regime, module names, tooltip, title.

Token budget note: the header says the compiler is at the 100k limit; steps 4, 6, 11 add code — offset by removing M43, M38-P4, Wyckoff, and merging the mirrored `f_bid` blocks into a table-driven loop.

---

## 17. VALIDATION PLAN

For every step:
1. **Replay test** (Pine): bar-replay on 1m/5m/15m BTCUSDT, EURUSD, XAUUSD, XAGUSD; confirm every label/line/alert that appears in replay also exists after reload (historical == realtime).
2. **Alert parity**: create all 12 alerts, run 1 session live, diff alert log vs labels at close → must be 1:1 after step 1.
3. **Structure unit charts**: hand-picked ranges (trend day, chop day, V-reversal, news spike) — count BOS/CHoCH per 100 bars before/after step 4; expect CHoCH ≥ 1 per real reversal, BOS count down ≥50% in chop, RANGE declared inside chop.
4. **OB placement**: sample 30 BOS events, verify OB candle = last opposite candle before displacement and origin index = leg low (step 2).
5. **Session**: EURUSD on OANDA and FXCM feeds, verify London window aligns with 07:00-10:00 London local across a DST change.
6. **Signal quality**: use the companion strategy port; metrics per module: count, win%, avg R, expectancy; before/after steps 5-6; kill modules with expectancy < 0 over ≥50 trades on ≥3 symbols.
7. **Regimes**: London, NY, Asia; high/low ATR percentile (top/bottom quartile) — expectancy per regime.
8. **Object limits**: `labels/lines/boxes drawn` plots must stay < 500 on 1m over 20k bars.
9. **Compile budget**: token count after each step.

Acceptance: no historical/realtime divergence; CHoCH fires on real reversals; per-module expectancy ≥ 0 for every default-ON module; signals/100 bars on 1m reduced without losing the sweep→displacement→MSS→POI signals.

---

## 18. FINAL RECOMMENDED FLOW

```
DISCOVER (done: 3417 lines, 8 layers, ~60 modules, 12 alerts)
   ↓
UNDERSTAND (done: architecture map §4)
   ↓
TRACE (done: entry chains §2, §11)
   ↓
AUDIT (done: §5-§12)
   ↓
ROOT CAUSE (done: RC1-RC7)
   ↓
PRIORITIZE (done: §14)
   ↓
DESIGN FIX (§16 order 1→12)
   ↓
VALIDATE (§17 per step)
   ↓
ONLY THEN CODE
```

Target architecture after the roadmap:

```
HTF CONTEXT (structure-classified HTF, lag-aware)
   ↓
LIQUIDITY MAP (levels with significance class)
   ↓
LIQUIDITY EVENT (qualified sweep only)
   ↓
DISPLACEMENT (mv.strong / dispScore as a GATE)
   ↓
STRUCTURE CONFIRMATION (CHoCH/MSS through protected swing)
   ↓
POI (OB from true leg origin · BRK · RCB/QM from real CHoCH · FVG · KL)
   ↓
RETRACEMENT (PD array = leg range; per-side zone slot)
   ↓
ENTRY (IMMEDIATE | CONFIRMED via micro-MSS/displacement)
   ↓
RISK VALIDATION (single tiered score · minRR · quality targets)
   ↓
SL / TP (unchanged engine, filtered targets)
   ↓
ALERT (all confirmed)
```
