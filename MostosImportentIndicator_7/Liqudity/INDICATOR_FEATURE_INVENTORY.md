# INDICATOR FEATURE INVENTORY — `liqudity_trap_trading.v3.8.3.txt`

> Scope: discovery only. Every item below was verified in the source code (not in comments or names).
> No bug audit, no recommendations, no code changes.
> Line numbers refer to `liqudity_trap_trading.v3.8.3.txt` (5,706 lines). Lines 1–705 are the changelog comment block and are **not** counted as code.

---

## 1. Indicator Overview

| Item | Value |
|---|---|
| Language | Pine Script v6 (`//@version=6`, L1) |
| Declaration | `indicator("Liquidity + S/D + Price Action [MTF] v3.8.3", "LQ-SD-PA v3.8.3", overlay = true, max_boxes_count = 500, max_lines_count = 500, max_labels_count = 500)` — L708 |
| Build tag | `BUILD v3.8.3-b1 · 2026-10-15` (L2) |
| Type | Overlay, non-strategy (no `strategy()` / order calls) |
| Trading doctrine | SMC / ICT: Liquidity → POI → Structure shift → Retest → Execution |
| Primary signal path | Per-direction **setup state machine** (`suL` / `suS`): IDLE → SWEPT → AT POI → SHIFTED → ACTIVE |
| Secondary signal paths | Engine "trigger candidates": S/D 50% tap, CRT, Turtle Soup, HTF CRT, HTF Turtle Soup, Inside Bar, Doji Reversal, Trendline sweep, Fractal Entry Model (FEM), Liquidity Trap engine (LT-1…LT-7) |
| Special module | ICT **Silver Bullet** (London 03–04, NY AM 10–11, NY PM 14–15 NY time) with its own arming, entry and exit engine |
| Inputs | 224 `input.*` declarations in ~30 groups (L714–L1204, plus `ltXxx` inputs ~L3682–3740 and `jrnlEnable` L5653) |
| `request.security` calls | 7 (L1718, L1719, L2105 via `f_bias` ×2, L2182, L2268, L2383, L2430) |
| Outputs | 8 `plot` + 12 `plotchar` + 3 `bgcolor` + 30 `alertcondition` = 53 |
| Tables | Dashboard (2×12, top-right) + Debug (2×5, bottom-right) |
| alert() feeds | LQJRNL journal, LQCE pre-fill, LT BUY/SELL, Silver Bullet lifecycle feed |

### Module map (code)

| Module | Lines | Content |
|---|---|---|
| Inputs / constants / profile | 708–1223 | `indicator()`, all input groups, symbol profile, fixed constants, UI helpers |
| MODULE 3 Core calcs | 1225–1310 | Capped ATR, spread, candle anatomy, volume, pins/engulf/doji, CISD, IFC, confirmations |
| MODULE 4 Pivots / EQ / trendline anchors | 1312–1416 | Internal pivots, EQH/EQL pools, trendline anchors |
| MODULE 4B Session clock / SB windows | 1418–1526 | Sessions, killzones, volatility windows, Silver Bullet windows, SB boxes |
| MODULE 5 Liquidity engine | 1528–1934 | Swing sweeps, sweep quality, EQ / PD / PW / session raids, sweep-in-play, break latches |
| MODULE 6 Structure | 1936–2099 | Internal + external BOS / CHoCH, MSS, trigger memory, structure chips |
| MODULE 7 HTF bias | 2101–2201 | EMA bias, HTF structure, combined bias / permissions |
| MODULE 8/9 HTF engines | 2203–2446 | Engineered-liquidity memory, auto HTF, HTF CRT/TBS, HTF FVG POI registry, ADR |
| MODULE 10 Dealing range | 2448–2541 | Premium/discount, OTE, SB range lock, SB tags |
| MODULE 11 Regime | 2543–2615 | TRENDING / TRANSITION / RANGING / CHOP |
| MODULE 12 FVG | 2617–2775 | FVG registry, IFVG, latest FVG |
| MODULE 13 Zones | 2777–3174 | S/D, OB, RB, IFVG zones, breaker/mitigation, NEXT BUY/SELL |
| MODULE 14 Engines | 3176–3359 | CRT, Turtle Soup, Trendline, Inside Bar, Doji |
| MODULE 15 FEM | 3361–3432 | Fractal Entry Model |
| MODULE 15A State | 3434–3472 | Machine / trade state, direction lock |
| MODULE 16 Score / Tier | 3479–3645 | Confluence score, decay, SB bonus, tier grader |
| MODULE 16B Liquidity Trap | 3648–4047 | LT-1…LT-7 trap engine |
| MODULE 17 State machine | 4049–4447 | Long / short setup machines, SB path |
| MODULE 18 Final gate | 4449–4636 | Gates, machine tier, gate-kill retry, engine gate, conflict hierarchy, LT veto |
| MODULE 18B Viability | 4638–4761 | Stop selection, plan price, slippage, risk cap, min RR |
| MODULE 19 Trade tracker | 4763–5104 | Fills, TP ladder, BE, trail, SB exits, counters, daily book |
| MODULE 20 Drawings | 5106–5449 | Plots, plotchars, bgcolor, labels, trade plan, POI boxes, NEXT level, focus mode |
| MODULE 21 Dashboard | 5451–5556 | Context dashboard |
| MODULE 22 Debug | 5558–5586 | Debug table |
| MODULE 23 Alerts | 5588–5706 | alertconditions + alert() feeds |

---

## 2. Status Legend

| Status | Meaning |
|---|---|
| **Fully implemented** | Logic exists and its output is consumed by gates, signals, trade tracking or alerts |
| **Partially implemented** | Logic exists but only part of the described behaviour is performed |
| **Visual only** | Only draws / prints; no effect on signals |
| **Configured but unused** | Declared or returned but never read |

---

## 3. Feature Status Summary

| # | Feature | Key identifiers | Lines | Status |
|---|---|---|---|---|
| 1 | Symbol profile presets | `symProfile`, `profIdx`, `profMan` | 727–735, 811, 823, 1179–1201 | Fully implemented |
| 2 | ATR shock cap | `atrRaw`, `atrAvg50`, `atr`, `atrCapIn` | 1229–1231 | Fully implemented |
| 3 | Spread-aware prices | `spr`, `hiA`, `loA`, `spreadIn` | 1234–1236 | Fully implemented |
| 4 | Candle anatomy / pins / engulf / doji | `bullPin`, `bearEngulf`, `doji` | 1237–1259 | Fully implemented |
| 5 | Relative volume confirmation | `relVol`, `volOK`, `volHot`, `useVol` | 1248–1250 | Fully implemented (OFF by default) |
| 6 | CISD | `f_cisd`, `cisdUp`, `cisdDn` | 1265–1296 | Fully implemented |
| 7 | IFC (institutional funding candle) | `ifcBull`, `ifcBear` | 1302–1306 | Fully implemented |
| 8 | Execution confirmation aggregate | `zoneBullConf`, `zoneBearConf` | 1309–1310 | Fully implemented |
| 9 | Internal pivots / swing levels | `ph`, `pl`, `lastRes`, `lastSup` | 1315–1416 | Fully implemented |
| 10 | EQH / EQL pools | `eqhLvls`, `eqlLvls`, `eqhSwept`, `eqlSwept` | 1344–1399, 1669–1714 | Fully implemented |
| 11 | Trendline anchors + sweep/break | `tlUp*`, `tlDn*`, `sigTLLong/Short` | 1333–1410, 3210–3273 | Fully implemented |
| 12 | Sessions / killzones | `f_inSes`, `inAsia`, `inLon`, `inNY`, `kzOK` | 1429–1440 | Fully implemented (gate OFF by default) |
| 13 | Scheduled volatility windows | `inNews`, `newsOK` | 1442, 1483–1484 | Fully implemented |
| 14 | Silver Bullet window engine | `sbWinNow`, `sbCtx`, `sbEnd*Evt` | 1450–1498 | Fully implemented |
| 15 | SB window range boxes | `sbBoxes` | 1501–1526 | Visual only |
| 16 | Swing sweeps (single + multi-bar reclaim) | `sslSweep`, `bslSweep`, `reclaimBars` | 1551–1572, 1649–1666 | Fully implemented |
| 17 | Sweep quality grades 1–4 | `f_sweepQual`, `lastSslQualRaw`, `lastSslQual` | 1574–1620 | Fully implemented |
| 18 | Engineered-pool grade | `f_poolQ` | 1636–1642 | Fully implemented |
| 19 | PDH/PDL/PWH/PWL liquidity | `pdh`, `pwl`, `pdhSweep` … | 1718–1759 | Fully implemented |
| 20 | Session high/low raids | `f_sesTrack`, `sesHiSwept`, `sesLoSwept` | 1771–1888 | Fully implemented |
| 21 | Sweep-in-play | `sslInPlay`, `bslInPlay` | 1901–1918 | Fully implemented |
| 22 | Break latches | `brokeUp`, `brokeUpS`, `resBosDone` | 1921–1934 | Fully implemented |
| 23 | Internal structure BOS / CHoCH | `f_structure`, `bosUp`, `chochUp`, `msDir` | 1944–1988 | Fully implemented |
| 24 | External structure | `extDir`, `eBosUp`, `eChochUp`, `protLowE` | 1991–2019 | Fully implemented |
| 25 | MSS + institutional sweep upgrade | `mssUp`, `mssDn` | 2024–2039 | Fully implemented |
| 26 | Trigger memory | `f_trigMem`, `recentMssUp` … | 2044–2079 | Fully implemented |
| 27 | Structure chips (BOS/CHoCH/MSS labels) | `f_structMarks` | 2086–2099 | Visual only |
| 28 | HTF EMA bias | `f_bias`, `emaBias`, `bD` | 2104–2114 | Fully implemented (`bD` visual only) |
| 29 | HTF structure | `f_htfStruct`, `hsDir`, `hsProtLo/Hi` | 2121–2184 | Fully implemented |
| 30 | Combined bias / neutral handling | `htfB`, `biasOkL/S`, `armBiasL/S` | 2188–2201 | Fully implemented |
| 31 | Engineered-liquidity score memory | `recentEngLo/Hi` | 2211–2217 | Fully implemented |
| 32 | Auto HTF selection | `f_autoHtf`, `htfTf`, `htfLive` | 2225–2239 | Fully implemented |
| 33 | HTF CRT + HTF Turtle Soup | `f_crtTbsHtf`, `sigHCrt*`, `sigHTbs*` | 2246–2279 | Fully implemented |
| 34 | HTF FVG POI registry (3/side) | `f_htfPoi`, `f_pickPoi`, `hPoiB*`, `hPoiS*` | 2291–2424 | Fully implemented |
| 35 | ADR exhaustion | `adrVal`, `adrPct`, `adrChaseL/S` | 2430–2446 | Fully implemented |
| 36 | Dealing range / premium-discount | `pdPos`, `rangeOK`, `rangeHolds` | 2479–2496 | Fully implemented |
| 37 | OTE 62–79 % | `inOTEbuy`, `inOTEsell` | 2497–2502 | Fully implemented (score/label flag) |
| 38 | SB dealing-range lock | `sbPdPos`, `sbPdOK`, `sbSetLive` | 2513–2541 | Fully implemented |
| 39 | Market regime classifier | `f_regimeMem`, `regime` | 2553–2604 | Fully implemented |
| 40 | CHOP exemption (institutional sweep) | `instSweepL/S`, `structDir` | 2611–2615 | Fully implemented |
| 41 | FVG registry + IFVG inversion | `Fvg`, `f_fvgRegistry`, `bullFvgs` | 2622–2739 | Fully implemented |
| 42 | Latest FVG per side | `f_latestFvg`, `cFvgB*`, `cFvgS*` | 2744–2775 | Fully implemented |
| 43 | Zone engine (S/D, OB, RB, IFVG, ★HP) | `Zone`, `f_zoneCreate`, `f_newZone` | 2784–3124 | Fully implemented |
| 44 | Breaker / mitigation flip | `f_flipZone` | 2845–2862, 2887–2919 | Fully implemented |
| 45 | Zone 50 % tap signal | `f_zoneUpdate`, `sigSDLong/Short` | 2868–2952 | Fully implemented |
| 46 | NEXT BUY / NEXT SELL level | `f_nextZones`, `nbTop`, `nsBot` | 3128–3174, 5352–5411 | Fully implemented |
| 47 | Engine cooldowns | `sigCooldown`, `crt*Cd`, `tbs*Cd` | 3180–3187 | Fully implemented |
| 48 | CRT (chart TF) | `crtBullSetup`, `sigCRTLong/Short` | 3190–3196 | Fully implemented |
| 49 | Turtle Soup (chart TF) | `sigTBSLong/Short` | 3200–3207 | Fully implemented |
| 50 | Inside Bar breakout | `f_insideBar`, `sig3Long/Short` | 3277–3331 | Fully implemented |
| 51 | Doji reversal | `f_dojiRev`, `sig4Long/Short` | 3334–3359 | Fully implemented |
| 52 | Fractal Entry Model (FEM) | `femL`, `femS`, `sigFEMLong/Short` | 3366–3432 | Fully implemented |
| 53 | Direction lock (one direction) | `dirLock`, `lockOkL/S` | 3441–3472 | Fully implemented |
| 54 | Confluence score (5 layers) | `scoreBaseL/S` | 3493–3592 | Fully implemented |
| 55 | POI conflict resolution | `poiConflict`, `poiBlockL/S` | 3543–3549 | Fully implemented |
| 56 | SB context score bonus | `sbCtxLong/Short`, `scoreLong/Short` | 3602–3611 | Fully implemented (display/label/journal only; gate reads base) |
| 57 | Tier grader C/B/A/A+ | `f_tier`, `tierLong/Short`, `minRank` | 3619–3645 | Fully implemented |
| 58 | Liquidity Trap engine LT-1…LT-7 | `f_ltMachines`, `sigLTLong/Short` | 3682–4040 | Fully implemented |
| 59 | LT-4 pool high export | `p4PoolHi` | 3847 | **Configured but unused** |
| 60 | Setup state machine (long/short) | `suL`, `suS`, `sigMCLong/Short` | 4151–4447 | Fully implemented |
| 61 | Silver Bullet arming / entry path | `sbArmOkL`, `sbTagL`, `sbSigLong` | 4073–4148, 4270–4332 | Fully implemented |
| 62 | Final gate | `longOK`, `shortOK` | 4454–4501 | Fully implemented |
| 63 | Daily risk governance | `govOK`, `trdToday`, `lossToday` | 4477–4484 | Fully implemented |
| 64 | Day-of-week filter | `dowOK`, `tradeDays` | 4486 | Fully implemented |
| 65 | Machine tier A/A+ | `f_mcTier`, `mcTierL/S` | 4511–4531 | Fully implemented |
| 66 | Gate-kill retry | `f_gateKill` | 4548–4560 | Fully implemented |
| 67 | Engine gate / SB suppression | `engOKL/S`, `engRank`, `engMute` | 4566–4592 | Fully implemented |
| 68 | Conflict hierarchy (SB > MC > engine) | `anyLong`, `anyShort` | 4594–4624 | Fully implemented |
| 69 | LT veto | — | 4635–4636 | Fully implemented |
| 70 | Viability gate (stop, slippage, risk cap, min RR) | `planEntry`, `planSL`, `planOK` | 4638–4728 | Fully implemented |
| 71 | Deferred next-open fill | `pendDir`, `pendFilled` | 4742–4743, 4809–4856 | Fully implemented |
| 72 | Non-SB exit engine (SL/TP1/TP2/TP3/BE) | — | 4858–4912 | Fully implemented |
| 73 | SB exit engine (BE, trail, time exit, structure exit) | `sbTimeExitEvt`, `sbStructExitEvt` | 4913–4985 | Partially implemented (partial time-exit moves stop only; no size reduction) |
| 74 | Trade max life | `maxTrdBars`, `cntExp` | 4991–4993 | Fully implemented |
| 75 | TP ladder + liquidity target TP3 | `tpMode`, `sbLiqTgt`, `trdLiqTgt` | 5017–5104 | Fully implemented |
| 76 | Validation counters | `cntA`, `cntAp`, `cntTP1` … | 4767–4792 | Fully implemented (shown in debug only) |
| 77 | Plotted levels / sweep marks | 8 plots, 12 plotchars | 4042–4043, 5109–5141 | Visual only |
| 78 | Background washes | 3 `bgcolor` | 5146–5152 | Visual only |
| 79 | Merged signal labels | `f_sigLabels` | 5155–5203 | Visual only |
| 80 | Trade plan drawing | `f_tradePlan` | 5206–5259 | Visual only |
| 81 | POI / FEM / anchor boxes | `f_drawPoi` | 5262–5335 | Visual only |
| 82 | Focus mode / box extension | `f_extendDraw` | 5414–5449 | Visual only |
| 83 | Dashboard | `f_dash` | 5454–5556 | Visual only |
| 84 | Debug table | `f_dbg` | 5562–5586 | Visual only |
| 85 | alertconditions (30) | — | 5592–5681 | Fully implemented |
| 86 | LQCE / LQJRNL / LT / SB alert() feeds | `ceMsg`, `f_sbAlertFeed` | 5648–5706 | Fully implemented |
| 87 | Internal protected swings | `protLowI`, `protHighI` | 1988 | **Configured but unused** |
| 88 | `riskMoney`, `tp1Pct` inputs | — | 1083–1084 | Visual only (label text) |

---

## 4. Feature Details

### 4.1 Settings & Symbol Profile

**Symbol profile** — `symProfile` (L727), `profIdx` (L733), `profMan` (L734). Options: Manual / FX majors / Metals / XAU / Indices / Crypto. It presets 9 ATR-scaled constants:

| Constant | Line | Manual | FX | XAU | Indices | Crypto |
|---|---|---|---|---|---|---|
| `extPiv` | 735 | `extPivIn` | 12 | 12 | 10 | 12 |
| `dispFactor` | 811 | `dispFactIn` | 1.2 | 1.2 | 1.1 | 1.2 |
| `minZoneAtr` | 823 | `minZoneIn` | 0.15 | 0.20 | 0.20 | 0.25 |
| `NEAR_LVL_ATR` | 1179 | `nearLvlIn` | 0.25 | 0.30 | 0.30 | 0.35 |
| `SL_PAD_ATR` | 1180 | `slPadIn` | 0.25 | 0.35 | 0.30 | 0.40 |
| `SWEEP_CTX_ATR` | 1181 | `sweepCtxIn` | 3.0 | 4.0 | 4.0 | 5.0 |
| `POI_NEAR_ATR` | 1182 | `poiNearIn` | 1.5 | 1.75 | 1.75 | 2.0 |
| `TRIG_LOOK` | 1183 | `trigLookIn` | 10 | 10 | 8 | 12 |
| `CHOP_RANGE_ATR` | 1201 | `chopRngIn` | 6.0 | 6.0 | 7.0 | 7.0 |

The raw inputs `extPivIn`, `dispFactIn`, `minZoneIn`, `nearLvlIn`, `slPadIn`, `sweepCtxIn`, `poiNearIn`, `trigLookIn`, `chopRngIn` take effect only when the profile is **Manual**. `atrCapIn` (L1175) and `REGIME_LOOK` (L1197) are in the Advanced group but are always active.

**Fixed constants** (L1184–1207): `STRONG_CLOSE_PCT` 0.30, `CISD_NEUTRAL_PCT` 0.10, `IFC_LOOK` 3, `BRK_BODY_ATR` 0.5, `IB_WAIT_BARS` 4, `TRADE_BARS` 15, `DOJI_WINDOW` 5, `MAX_EQ_POOLS` 8, `OTE_1`/`OTE_2` 0.62/0.79, `SB_ARM_GRACE` 5, `SB_MEM_EXTRA` 5, `SB_BE_TP1_PCT` 0.15, `COL_BULL` #089981, `COL_BEAR` #f23645.

**UI helpers**: `f_size` (L1211), `drawSize`/`sigSize`/`dashSize` (L1212–1214), `mkSize` (L1209), `f_chip` (L1217, pill label), `f_recent` (L1223, recency test used at 34 call sites).

### 4.2 Input Groups (all verified as read in code)

| Group var | Title | Lines | Inputs |
|---|---|---|---|
| `grpG` | General | 714–735 | `pivLen` 5, `extPivIn` 12, `atrLen` 14, `biasLen` 50, `showLevels`, `symProfile` |
| `grpH` | HTF context | 737–765 | `biasFilter` "60", `biasMode` "Structure + EMA", `htfStructPiv` 5, `htfProtInval`, `neutralMode` "Follow chart structure", `useHtfCrt`, `htfSel` "Auto", `hPoiMaxAge` 40, `hPoiMaxTouch` 2 |
| `grpL` | Liquidity | 768–783 | `showSweeps`, `sweepLook` 12, `showEq`, `eqTol` 0.15, `eqMaxAge` 240, `minArmQual` 2, `reclaimBars` 4, `showPdwl` |
| `grpM` | Structure | 785–794 | `showStruct`, `structDisp` 0.5, `showProt`, `mssNeedExt` |
| `grpF` | FVG | 796–806 | `showFvg`, `fvgMaxKeep` 4, `fvgMaxAge` 120, `useIfvg` |
| `grpZ` | Supply / Demand / Order blocks | 808–824 | `showZones`, `dispFactIn` 1.2, `maxZoneAtr` 2.0, `maxZones` 6, `showOB`, `confirmWin` 5, `showFlip`, `showRB`, `minZoneIn` 0.15, `zoneMaxTests` 2 |
| `grpNX` | Next buy / sell level | 826–842 | `showNextLvl`, `nextLvlAnchor`, `nextLvlBox`, `nextLvlPct`, `nextLvlBack` 60, `nextInclHtf`, `hPoiNextMaxAtr` 4.0 |
| `grpC` | CRT / Turtle soup / CISD / IFC | 844–856 | `showCRT`, `crtRangeAtr` 1.2, `crtDispAtr` 0.5, `showTBS`, `tbsLen` 20, `tbsAgeMin` 4, `tbsAgeMax` 60, `cisdAsConf`, `sigCooldown` 10 |
| `grpB` | Inside bar / Doji | 858–864 | `showS3`, `ibBodyAtr` 1.0, `showS4`, `dojiPct` 25, `dojiMin` 3, `minWickAtr` 0.3 |
| `grpTL` | Trendlines | 866–871 | `showTL`, `tlSweepEnt`, `tlNeedConf`, `tlTouchMin` 0, `tlMaxAge` 150 |
| `grpFE` | Fractal entry model | 873–876 | `useFEM`, `femWait` 40, `showPoi` |
| `grpO` | Dealing range / OTE | 878–879 | `rangeSrc` "External" |
| `grpK` | Sessions (NY time) | 881–890 | `useKZ` false, `paintKZ` false, `showSesHL`, `asiaSes` 2000-0000, `lonSes` 0200-0500, `nySes` 0700-1000, `sbSesLO` 0300-0400, `sbSesAM` 1000-1100, `sbSesPM` 1400-1500 |
| `grpSB` | Silver Bullet — setup | 892–919 | `sbEnable`, `sbUseLO/AM/PM`, `sbPreMin` 15, `sbQualLO` 3, `sbQualAM` 2, `sbQualPM` 3, `sbPoolPref`, `sbAsiaPool`, `sbChopBypass`, `sbKillAtEnd`, `sbLiqWait` 12, `sbPoiWait` 8, `sbRetWait` 10, `sbFvgMinAtr` 0.10, `sbDispAtr` 0.8, `sbReqMss` false |
| `grpSBe` | Silver Bullet — entry | 921–934 | `sbEntryMode`, `sbReqHtf`, `sbReqPD`, `sbMinTier` "A and above", `sbSuppress` "Down-weight", `sbOnly` false |
| `grpSBx` | Silver Bullet — exits | 936–942 | `sbTimeExit`, `sbTimeMode` "Full", `sbLiqTgt`, `sbStructEx`, `sbBeBuf` 0.15, `sbTrail` |
| `grpSBv` | Silver Bullet — visuals / alerts | 944–949 | `sbPaint`, `sbShowBox`, `sbBoxKeep` 2, `sbShowPlan`, `sbDynAlert` |
| `grpN` | Scheduled volatility windows | 952–962 | `useNews`, `paintNews`, `newsAllowSb`, `news1Ses` 0825-0845, `news2Ses` 0955-1010, `news3Ses` 1355-1435 (Wed) |
| `grpQ` | Signal quality / state machine | 964–1038 | `tierMode` "A and above", `minScore` 50, `masterCd` 15, `useRegime`, `liqWait` 20, `poiWait` 15, `retWait` 20, `armGrace` 3, `shiftSrc` "MSS / external CHoCH", `poiSrc` "Zone / HTF POI only", `armNeedHtf`, `oneDir`, `fastShift`, `mcEntryMode` "CE preferred + confirmation fallback", `mcFvgDisp`, `mcStrictCnf`, `mcReqPD`, `mcPdWaive` false |
| `grpR` | Risk / TP / SL | 1041–1096 | `showTrade`, `tpMode` "Liquidity target", `rrMult` 2.0, `maxRiskAtr` 1.5, `riskMode` "Reject the signal", `stopTier`, `minRR` 1.5, `costTicks` 0, `spreadIn` 0, `riskMoney` 0, `tp1Pct` 50, `slipGuard` 0.5, `maxTrdBars` 80, `nonSbTp3` false |
| `grpV` | Volume confirmation | 1105–1109 | `useVol` false, `volLen` 20, `volMult` 1.3, `volQual` |
| `grpADR` | ADR exhaustion | 1116–1120 | `useAdr`, `adrLen` 10, `adrMax` 1.2 |
| `grpGov` | Risk governance (per day) | 1129–1136 | `useGov`, `maxTrdDay` 4, `maxLossDay` 2, `tradeDays` "23456" |
| `grpD` | Dashboard / Debug | 1138–1140, 5653 | `showDash`, `showDbg` false, `jrnlEnable` |
| `grpU` | UI / style | 1142–1157 | `uiSizeOpt`, `uiTrans` 25, `uiMicroBig`, `uiDrawOpt`, `uiDashOpt`, `focusMode`, `focusAtr` 4.0 |
| `grpADV` | Advanced tuning | 1166–1201 | `nearLvlIn`, `slPadIn`, `sweepCtxIn`, `poiNearIn`, `trigLookIn`, `atrCapIn` 1.5, `REGIME_LOOK` 40, `chopRngIn` |
| LT group | Liquidity trap engine | ~3682–3740 | `ltEnable`, `ltCtxGate`, `ltMinCls`, `ltVeto`, `ltP1`…`ltP7`, sensitivity inputs, `ltReqRetest`, `ltReqSweep`, `ltReqMtf`, `ltScoreMed/High/VHigh` (50/70/85), `ltShowMarks`, `ltShowSig`, `ltDynAlert` |

Input-level result: every `input.*` is read in code. Only the 9 profile-overridden raw inputs are conditional (Manual profile only).

### 4.3 Core Calculations (MODULE 3, L1225–1310)

| Feature | Identifiers | Lines | Description | Status |
|---|---|---|---|---|
| Capped ATR | `atrRaw`, `atrAvg50`, `atr` | 1229–1231 | ATR(`atrLen`) capped at `atrCapIn` × 50-bar ATR average; all distances use `atr` | Fully implemented |
| Spread | `spr`, `hiA`, `loA` | 1234–1236 | `spreadIn` ticks added to high/low to model ask-side fills/stops | Fully implemented |
| Candle anatomy | `body`, `rng`, `upWick`, `dnWick` | 1237–1247 | Base candle measurements | Fully implemented |
| Relative volume | `relVol`, `volOK`, `volHot` | 1248–1250 | Displacement volume gate (`useVol`) and sweep-grade bump (`volQual`) | Fully implemented |
| Pin / engulf / doji | `bullPin`, `bearPin`, `bullEngulf`, `bearEngulf`, `doji` | 1253–1259 | Pin = wick ≥ 2× body and ≥ `minWickAtr`; doji = body ≤ `dojiPct` % of range | Fully implemented |
| CISD | `f_cisd`, `cisdUp`, `cisdDn` | 1265–1296 | Run of ≥ 2 opposite candles, then displacement body (≥ `BRK_BODY_ATR`) closing through the run's origin open with an outer-range close; once per run | Fully implemented |
| IFC | `ifcBull`, `ifcBear` | 1302–1306 | Takes the prior `IFC_LOOK` extreme, closes past the prior mid with displacement and strong close | Fully implemented |
| Execution confirmation | `zoneBullConf`, `zoneBearConf` | 1309–1310 | Pin/engulf OR IFC OR (CISD if `cisdAsConf`) | Fully implemented |

### 4.4 Liquidity Concepts (MODULE 4 / 5)

| Feature | Identifiers | Lines | Description | Status |
|---|---|---|---|---|
| Internal swing levels | `ph`, `pl`, `lastRes`, `lastSup`, `resBroken`, `supBroken` | 1315–1329, 1382–1416 | Confirmed pivots set last swing high/low and reset break latches | Fully implemented |
| EQH / EQL pools | `eqhLvls`, `eqlLvls`, `eqhLns`, `eqhSwept`, `eqlSwept`, `eqMaxAge` | 1344–1399, 1669–1714 | Two pivots within `eqTol`×ATR form a pool; wick-through + close back = pool sweep (kind 2); trade-through or age removes the pool; dotted lines if `showEq` | Fully implemented |
| Swing sweeps | `sslSweep`, `bslSweep`, `sslRecl`, `sslExt`, `sslSpentLvl` | 1551–1572, 1649–1666 | Wick through + close back (or close back within `reclaimBars` after a break); one event per level until a new pivot or `SWEEP_CTX_ATR` travel | Fully implemented |
| Sweep quality | `f_sweepQual` | 1574–1597 | 1 WEAK · 2 VALID (firm close or ≥ 0.3 ATR penetration) · 3 STRONG (+ outer-30 % close + displacement body) | Fully implemented |
| Sweep memory | `lastSslBar`, `lastSslLvl`, `lastSslExt`, `lastSslQual`, `lastSslQualRaw`, `lastSslKind` | 1599–1620 | Raw vs effective grade; pool kind 1 swing · 2 EQ · 3 PD/PW · 4 session | Fully implemented |
| Engineered-pool grade | `f_poolQ`, `qPoolLo`, `qPoolHi` | 1636–1642 | Grade for EQ/PD/PW/session raids; grade 1 unless the pool's own level is firmly reclaimed or penetrated | Fully implemented |
| PDH/PDL · PWH/PWL | `pdh`, `pdl`, `pwh`, `pwl`, `pdhSweep`, `pdlSweep`, `pwhSweep`, `pwlSweep` | 1718–1759 | `request.security` D/W `[1]` + `lookahead_on`; one raid per level; spent once traded through; kind 3 | Fully implemented |
| Session H/L | `f_sesTrack`, `asiaHiLvl`, `lonLoLvl`, `nyHiSw`, `sesHiSwept`, `sesLoSwept` | 1771–1888 | Tracks Asia/London/NY H/L, raid vs break; London/NY raids stamp kind 4; Asia raid stamps only in SB context with `sbAsiaPool`; lines/labels if `showSesHL` | Fully implemented |
| Sweep in play | `sslInPlay`, `bslInPlay`, `recentSsl`, `sbMemLook` | 1901–1918 | Recent sweep, reclaim still holding, price within `SWEEP_CTX_ATR`; memory +5 bars in SB context | Fully implemented |
| Break latches | `brokeUp`, `brokeDn`, `brokeUpS`, `brokeDnS`, `resBosDone` | 1921–1934 | Liquidity-side latch and displaced structure-side latch | Fully implemented |
| Engineered-liquidity memory | `recentEngLo`, `recentEngHi` | 2211–2217 | Bar stamp of any EQ / session / PD / PW raid (score input) | Fully implemented |

### 4.5 Market Structure (MODULE 6)

| Feature | Identifiers | Lines | Description | Status |
|---|---|---|---|---|
| Internal BOS / CHoCH | `f_structure`, `msDir`, `bosUp`, `bosDn`, `chochUp`, `chochDn` | 1944–1988 | Displaced break with trend = BOS (sets protected swing); close through protected swing = CHoCH | Fully implemented |
| Internal protected swings | `protLowI`, `protHighI` | 1988 | Returned from `f_structure`; never read | **Configured but unused** |
| External structure | `extDir`, `extRes`, `extSup`, `eBosUp`, `eChochUp`, `protLowE`, `protHighE` | 1991–2019 | Second `f_structure` instance on `extPiv` swings | Fully implemented |
| MSS | `mssUp`, `mssDn` | 2024–2039 | External CHoCH (internal if `mssNeedExt` off) with a grade ≥ 2 sweep in play; within `TRIG_LOOK` writes grade 4 (INSTITUTIONAL) to the effective grade | Fully implemented |
| Trigger memory | `f_trigMem`, `lastChUpBar`, `lastMssUpBar`, `recentCisdUp`, `recentDispUp`, `recentStructUp` | 2044–2079 | Bar stamps / recency for CHoCH, BOS, MSS, CISD, displacement | Fully implemented |
| Structure chips | `f_structMarks` | 2086–2099 | One label per side: MSS > CHoCH > BOS > iCHoCH > iBOS (`showStruct`) | Visual only |

### 4.6 Higher-Timeframe Context (MODULE 7 / 8 / 9)

| Feature | Identifiers | Lines | Description | Status |
|---|---|---|---|---|
| HTF EMA bias | `f_bias`, `biasTf`, `emaBias`, `bD` | 2104–2114 | Close vs EMA(`biasLen`) on closed HTF bar; `bD` (daily) is dashboard-only | Fully implemented / `bD` visual |
| HTF structure | `f_htfStruct`, `hsDir`, `hsProtLo`, `hsProtHi` | 2121–2184 | Own BOS/CHoCH engine on `biasTf`; protected swing can invalidate setups (`htfProtInval`) | Fully implemented |
| Combined bias | `htfB`, `biasOkL`, `biasOkS`, `armBiasL`, `armBiasS` | 2188–2201 | `biasMode` (EMA / Structure / both) + `neutralMode` resolve to one permission per side | Fully implemented |
| Auto HTF | `f_autoHtf`, `htfTf`, `htfLive` | 2225–2239 | Maps chart TF to HTF; live only when HTF > chart TF | Fully implemented |
| HTF CRT / Turtle Soup | `f_crtTbsHtf`, `sigHCrtLong/Short`, `sigHTbsLong/Short`, `slHCrt*`, `slHTbs*` | 2246–2279 | HTF 3-candle CRT and HTF turtle soup, once per new HTF bar, own stops (`useHtfCrt`) | Fully implemented |
| HTF FVG POI registry | `f_htfPoi`, `f_pickPoi`, `hPoiBTop/Bot/In`, `hPoiSTop/Bot/In` | 2291–2424 | 3 bull + 3 bear HTF FVGs, visit counting, age/touch expiry; picks nearest untested within range, else nearest | Fully implemented |
| ADR exhaustion | `adrVal`, `adrPct`, `adrExh`, `adrChaseL`, `adrChaseS` | 2430–2446 | Day range ÷ daily ADR; chasing top/bottom 30 % of an exhausted day costs score / A+ | Fully implemented |

### 4.7 Dealing Range, OTE, Regime (MODULE 10 / 11)

| Feature | Identifiers | Lines | Description | Status |
|---|---|---|---|---|
| Premium / discount | `pdPos`, `rngHi`, `rngLo`, `rangeOK`, `rangeHolds` | 2479–2496 | Running high/low from older anchoring swing (`rangeSrc`); `pdPos` clamped 0–1 | Fully implemented |
| OTE | `inOTEbuy`, `inOTEsell` | 2497–2502 | 62–79 % retracement band of the current leg | Fully implemented (score/label flag; no drawing) |
| SB range lock | `sbRngHi`, `sbRngLo`, `sbPdPos`, `sbPdOK`, `sbSetLive` | 2513–2541 | Range frozen at SB window open for SB-tagged setups | Fully implemented |
| Regime | `f_regimeMem`, `regime`, `regThrust` | 2553–2604 | TRENDING / TRANSITION / RANGING / CHOP from external event recency, range widths and net thrust | Fully implemented |
| CHOP exemption | `instSweepL`, `instSweepS` | 2611–2615 | Raw grade ≥ 3 sweep + recent MSS exempts CHOP | Fully implemented |

### 4.8 FVG, Zones, POI (MODULE 12 / 13)

| Feature | Identifiers | Lines | Description | Status |
|---|---|---|---|---|
| FVG registry | `type Fvg`, `bullFvgs`, `bearFvgs`, `f_newFvg`, `f_fvgRegistry` | 2622–2739 | Gaps ≥ `minZoneAtr`, capped `fvgMaxKeep`, partial-fill "tested", deleted on fill/age; boxes if `showFvg` | Fully implemented |
| IFVG inversion | `useIfvg`, `ifvgSupTop/Bot`, `ifvgDemTop/Bot` | 2686–2739 | Close-through flips gap into IFVG (opposite array) and hands it to the zone engine | Fully implemented |
| Latest FVG | `f_latestFvg`, `cFvgBTop/Bot/Bar/Disp`, `cFvgSTop/...` | 2744–2775 | Newest respected FVG per side + displacement flag (machine anchor, FEM, LT score) | Fully implemented |
| Zone type / helpers | `type Zone`, `zones`, `f_pushZone`, `f_claimBand`, `f_newZone` | 2784–2841 | Zone object with kind, tests, tap state; newer zone claims overlapping band | Fully implemented |
| S/D zones (★HP) | `f_zoneCreate` | 2983–3032 | FVG + displacement candle; score 3 "★HP" when the leg broke structure, else 2 | Fully implemented |
| Order block | `showOB` | 3008–3038 | Opposite-colour origin candle, kind "OB", created with a new S/D zone | Fully implemented |
| Rejection block | `showRB` | 3041–3072 | Swept pivot wick + displacement away, kind "RB", max 2/side | Fully implemented |
| IFVG zones | `useIfvg` | 3083–3104 | Inverted FVGs added as kind "IFVG" zones | Fully implemented |
| Zone cap | `maxZones` | 3110–3123 | Keeps newest N per side | Fully implemented |
| Breaker / Mitigation | `f_flipZone`, `showFlip` | 2845–2862, 2887–2919 | Violated zone flips: BRK (sweep + structure) score 3, else MIT score 2 | Fully implemented |
| Zone lifecycle + 50 % tap | `f_zoneUpdate`, `sigSDLong`, `sigSDShort`, `slSDLong/Short` | 2868–2963 | Separate-visit test count (`zoneMaxTests` → spent); edge-triggered 50 % tap + confirmation within `confirmWin` = S/D signal | Fully implemented |
| NEXT BUY / SELL | `f_nextZones`, `nbTop`, `nbBot`, `nsTop`, `nsBot`, `nbScore`, `nbKind`, `touchNextBuy`, `touchNextSell` | 3128–3174 | Nearest unspent demand below / supply above; HTF POI competes (`nextInclHtf`, height ≤ `hPoiNextMaxAtr`) | Fully implemented |

### 4.9 Trigger Engines (MODULE 14 / 15)

| Engine | Signal vars | Stop vars | Lines | Logic summary | Status |
|---|---|---|---|---|---|
| Engine cooldowns | — | — | 3180–3187 | `sigCooldown` bars between same-engine signals | Fully implemented |
| CRT | `sigCRTLong/Short` | `slCRTLong/Short` | 3190–3196 | Big candle 1 (`crtRangeAtr`), candle 2 sweeps & closes inside, candle 3 displacement close (`crtDispAtr`) | Fully implemented |
| Turtle Soup | `sigTBSLong/Short` | `slTBSLong/Short` | 3200–3207 | Raid of `tbsLen` extreme with close back, age window `tbsAgeMin`–`tbsAgeMax` | Fully implemented |
| Trendline sweep | `sigTLLong/Short`, `tlUpBreak`, `tlDnBreak` | `slTLLong/Short` | 3210–3273 | Edge-triggered touches; wick through line with ≥ 2 touches (+ `tlTouchMin`), optional confirmation; close through = break; expiry `tlMaxAge` | Fully implemented |
| Inside Bar | `sig3Long/Short` | `sl3Long/Short` | 3277–3331 | Structure-breaking mother bar → inside bar in correct half → breakout within `IB_WAIT_BARS` with structure + bias agreement | Fully implemented |
| Doji Reversal | `sig4Long/Short` | `sl4Long/Short` | 3334–3359 | ≥ `dojiMin` dojis, compression, raid of swing level, displacement confirm, context bias | Fully implemented |
| FEM | `sigFEMLong/Short`, `femL`, `femS` | `slFEMLong/Short` | 3366–3432 | HTF POI tap → LTF shift → lock first FVG → retest + confirmation; resets on violation / exit / `femWait` | Fully implemented |

### 4.10 Confluence Score & Tiers (MODULE 16)

**Score layers** (`scoreBaseL/S`, L3554–3592):

| Layer | Points |
|---|---|
| Context | HTF bias aligned 10 / neutral 5; external structure aligned +10; session `sesPts` (5 SB/NY/London, 2 Asia, 3 non-intraday); correct P/D side +5; ADR chase −10 |
| Liquidity | Sweep in play 10; recent engineered pool +5; raw grade ≥ 3 +5 |
| POI | In zone 10 or near 5; fresh +5; in OTE +5; 0 if POI-conflict blocked |
| Trigger (cap 20) | Max of decayed MSS 12 / CHoCH 9 / BOS 5, plus decayed CISD 8 (separate bar); stage-3 floor 50 % over retest clock (`f_decay` L3569) |
| Execution | Retest +5 (not when on own anchor); confirmation candle +5 |

- **POI source switch** (L3509–3526): from stage 2 the score reads the setup's own anchor (`suLAnchorT/B`), else the NEXT zone.
- **POI conflict** (L3543–3549): demand and supply within 1 ATR → side agreeing with `htfB` → `dirLock` → `extDir` keeps points.
- **SB context bonus** (L3602–3611): 0–15 points inside SB window; `scoreLong = min(100, base + bonus)` used for display/label/journal; gate uses base.
- **Tier grader** `f_tier` (L3619–3645): C(1) default · B(2) trigger + (liq ≥ 10 or POI ≥ 5) · A(3) liq ≥ 10 + POI ≥ 10 + trigger + exec ≥ 5 · A+(4) A + HTF aligned + session + raw grade ≥ 3 + P/D OK. `minRank` from `tierMode`.

### 4.11 Liquidity Trap Engine (MODULE 16B, L3648–4047)

| Item | Lines | Description | Status |
|---|---|---|---|
| Context gate | 3682–3759 | `ltCtxBase` = killzone + news + not CHOP; adds bias; blocks counter-trend in TRENDING without raw strong raid; `ltLowVol` | Fully implemented |
| Wick bars / compression | 3762–3770 | `ltLoWickBar`, `ltHiWickBar`, `ltCmp` (low body, tight range, mixed candles) | Fully implemented |
| Wick cluster | 3773–3784 | `f_wickClusterLow` — clustered lower wicks within `ltClusterTol` | Fully implemented |
| Pools / breakout memory | 3789–3847 | `f_ltPools` → `p3PoolLow`, `p4Lvl`, `ltBrkUpLvl`, `ltBrkUpBar`, `p4Arm` | Fully implemented |
| `p4PoolHi` | 3847 | Returned from `f_ltPools`, never read | **Configured but unused** |
| OB interaction | 3866–3877 | `f_ltObNear` — touch of OB-kind zone (score only) | Fully implemented |
| Trap score | 3883–3901 | `f_ltScore` 0–100 (see below); classes VERY HIGH ≥ 85, HIGH ≥ 70, MEDIUM ≥ 50 | Fully implemented |
| Trap state machines | 3906–4040 | `f_ltMachines` — idle / waiting / active-cooldown per direction; arm → retest → confirmation → signal; outputs `sigLTLong/Short`, `slLTLong/Short` | Fully implemented |
| LT marks | 4042–4043 | `◦` retest / failed-break plotchars (`ltShowMarks`) | Visual only |

**Patterns** (arm conditions L3850–3862):

| Pattern | Direction | Condition |
|---|---|---|
| LT-1 | Long | Compression primed below resistance, then strong bull breakout (`ltExpSens`) |
| LT-2 | Short | Weak breakout poke, down-displacement, compression, after a rise |
| LT-3 | Short | Breakout while a lower-wick cluster pool is live nearby |
| LT-4 | Long | Strong breakout followed by an upper-wick cluster (`p4Arm`) |
| LT-5 | Short | Breakout on a significant upper wick, or repeated weak upper wicks after a breakout |
| LT-6 | Short | Weak poke in bearish external context with compression; confirmation needs close below level |
| LT-7 | Short | Breakout into a chart-TF supply zone (arming counts as retest) |

**Trap score** (`f_ltScore`): base +10, sweep in play +20, strong rejection +15, recent MSS/CHoCH +20, S/D zone +10, FVG +10, OB +10, displacement +10, retest +10, HTF agrees +15; CHOP −10, counter-trend −20, opposite OTE −15, low vol −5, no pool −10, both machines armed −15.

**Invalidations**: "expired (no confirmation)" (`ltWaitBars`), "breakout failed (bear displacement below level)", "breakout accepted (bull displacement above level)"; cooldown `ltCd`.

### 4.12 Setup State Machine (MODULE 17, L4049–4447)

| Stage | Name | Transition rule | Lines |
|---|---|---|---|
| 0 → 1 | SWEPT | SSL/BSL in play, arm bar (sweep bar / grace), grade ≥ `minArmQual` or SB arm OK, HTF bias (`armNeedHtf`), direction lock, CHOP block unless institutional or SB bypass | 4213–4228 |
| 1 → 3 | SHIFTED (fast) | SB: MSS / `sbShiftUp`; non-SB: `fastShift` + `shiftUpOk` | 4231–4237 |
| 1 → 2 | AT POI | Zone tap (anchor lock), OTE (if `poiSrc`), or HTF POI tap | 4238–4246 |
| 2 → 3 | SHIFTED | Shift per `shiftSrc`; locks shift-leg FVG (`mcFvgDisp` / `sbFvgOkL`) | 4250–4266 |
| 3 → 4 | ACTIVE (entry) | SB: CE touch or proximal edge + rejection; non-SB: CE limit (`mcCeOn`) or proximal + confirmation (`mcStrictCnf`); plan price + stop (`stopTier`) | 4270–4332 |

- Short machine mirrors at L4335–4447.
- **SB path** (L4073–4148): `sbArmOkL/S`, `SB_ARM_GRACE`, `armGrace`, `sbTagL/S` window tag, shorter clocks (`sbLiqWait`/`sbPoiWait`/`sbRetWait`), window-close kill `sbKillL/S`, clean FVG `sbFvgOkL/S`, one entry per window (`sbDoneWinL/S`).
- **Shift definitions** (L4120–4132): `shiftUpOk` widens with `shiftSrc` (MSS → + ext CHoCH → + int CHoCH → + CISD); SB shift may use displaced internal CHoCH/CISD (`sbDispAtr`).

**Invalidation reasons** (`suLReason` / `suSReason`):

| Reason | Line |
|---|---|
| sweep undone | 4158 |
| sweep reclaim lost | 4168 |
| opposing displacement | 4180 |
| range swept both ways | 4185 |
| POI violated (own anchor) | 4196 |
| HTF protected low / high broken | 4201 |
| SB window closed | 4204 |
| sweep expired / POI tap expired / retest window expired | 4208 |
| SB FVG violated / anchor FVG violated | 4316 |
| conflict — higher-rank long/short won the bar | 4594–4624 |

### 4.13 Final Gate & Signal Composition (MODULE 18 / 18B)

**Gates** (`longOK` / `shortOK`, L4454–4501): bias (`biasOkL/S`), direction lock (`lockOkL/S`), killzone (`kzOK`), volatility window (`newsOK`), day of week (`dowOK`, L4486), master cooldown (`masterCd`, L4456), CHOP (`chopOKL/S`, L4468), SB-only mode (`sbOnlyOK`, L4473), daily governance (`govOK`, L4477–4484), premium/discount (`mcPdOKL/S`, L4494), min score on base (`gateScoreL ≥ minScore`, L4492). SB entries bypass cooldown and P/D (L4500–4501).

| Feature | Identifiers | Lines | Description |
|---|---|---|---|
| Machine tier | `f_mcTier`, `mcTierL/S`, `sbTierMin` | 4511–4531 | A by default; A+ needs raw grade ≥ 3, HTF aligned, true MSS, P/D OK, engineered pool, session, no ADR chase |
| Gate-kill retry | `f_gateKill`, `gateKillL/S` | 4548–4560 | Blocked stage-4 setup returns to stage 3 with the blocking gate named |
| Engine gate | `engOKL/S`, `engRank`, `engMute` | 4566–4592 | Engine candidates need `minRank`; while SB live: down-weight or suppress (`sbSuppress`) |
| Signal composition | `anyLong`, `anyShort` | 4594–4595 | `sigMCLong or sigSDLong or sig3Long or sig4Long or sigTLLong or sigCRTLong or sigTBSLong or sigHCrtLong or sigHTbsLong or sigFEMLong or sigLTLong` |
| Conflict hierarchy | — | 4596–4624 | Both sides fire: SB machine (3) > ordinary machine (2) > engine (1); tie mutes both |
| LT veto | — | 4635–4636 | Waiting opposite trap mutes non-machine signals |
| Stop selection | `selSLLong/Short` | 4658–4663 | MC > FEM > SD > CRT > TBS > HTF CRT > HTF TBS > IB > Doji > TL > LT; fallback 2-bar extreme ± pad |
| Plan entry | `planEntry` | 4666 | Machine plan price, else close |
| Slippage guard | `slipGuard` | 4683 | Rejects plan far from close (CE limit exempt) |
| Risk cap | `maxRiskAtr`, `riskMode` | 4688–4694 | Clamp or reject |
| Min RR | `rrMult`, `minRR`, `costTicks` | 4699–4711 | TP2 = `rrMult`R clamped to next opposing zone; net RR ≥ `minRR` |
| Final flags | `sbFireL/S`, `finalTierL/S` | 4730–4752 | SB fire flags; one tier per signal |
| Deferred fill class | `mcFillNext`, `engFillNext` | 4742–4743 | Engine / non-CE machine fills at next open |
| Cooldown stamps | `lastLongSigBar` … | 4756–4761 | Stamped from final signals only |

**Final BUY / SELL signals**: `anyLong` / `anyShort` after gate → engine gate → hierarchy → LT veto → viability. Sub-flavours: `sigMCLong/Short` (machine), `sbFireL/S` (Silver Bullet), `sigLTLong/Short` (trap), `sigFEMLong/Short` (FEM), engine signals.

### 4.14 Trade Tracker & Exits (MODULE 19, L4763–5104)

| Feature | Lines | Description | Status |
|---|---|---|---|
| Tracker state / counters | 3441–3472, 4767–4792 | `trdEntry`, `trdSL`, `trdTP1-3`, `trdDir`, `trdIsSb`, `trdLiqTgt`; counters `cntA`, `cntAp`, `cntLong`, `cntShort`, `cntTP1`, `cntTP2`, `cntTP3`, `cntSL`, `cntSbEnt`, `cntExp`, `cntUntracked` | Fully implemented |
| Deferred next-open fill | 4809–4856 | Re-validates slippage, risk cap, min RR and gap-through at `open` | Fully implemented |
| Non-SB exits | 4858–4912 | SL first; TP1 → break-even + buffer; TP2 close or lock 1R + runner (`nonSbTp3`); TP3 | Fully implemented |
| SB exits | 4913–4985 | Adaptive BE after TP1; TP2 counted; protected-swing trail (`sbTrail`); TP3; structure exit (`sbStructEx`); window-close time exit (`sbTimeExit`, `sbTimeMode`) | Partially implemented — "Partial" time-exit mode moves the stop to entry; no position-size reduction is tracked |
| Max trade life | 4991–4993 | `maxTrdBars` expiry, `cntExp` | Fully implemented |
| SB range lock feed | 4998 | `sbSetLive` | Fully implemented |
| Stage release | 5001–5009 | Stage 4 → 0 when flat; "tracker busy" reason | Fully implemented |
| TP ladder | 5017–5104 | TP1 = 1R, TP2 = plan TP2, TP3 = max(3, `rrMult`+1)R; `tpMode` "Liquidity target"; SB `sbLiqTgt` → nearest pool (session H/L, PDH/PDL, PWH/PWL, opposite POI) | Fully implemented |
| Daily book | 4869–4957, 5102 | `trdToday`, `lossToday` feed `govOK` | Fully implemented |

### 4.15 Drawings (MODULE 20)

| Feature | Function / toggle | Lines | Description | Status |
|---|---|---|---|---|
| Swing levels | `showLevels` | 5109–5111 | Last swing high / low plots | Visual only |
| Protected swings | `showStruct` + `showProt` | 5113–5115 | External protected high / low | Visual only |
| PDH/PDL/PWH/PWL | `showPdwl` | 5117–5120 | Previous day / week lines | Visual only |
| Sweep marks | `showSweeps` | 5123–5133 | ◆ swing, ◈ EQ, ◇ PD/PW | Visual only |
| TL break marks | `showTL` | 5135–5137 | ✕ | Visual only |
| Session raid marks | `showSesHL` | 5139–5141 | ▿ / ▵ | Visual only |
| Killzone wash | `paintKZ` | 5146 | Asia purple, London blue, NY orange | Visual only |
| SB band | `paintKZ` / `sbPaint` | 5151 | Teal band per SB window | Visual only |
| Volatility wash | `paintNews` | 5152 | Red | Visual only |
| Signal labels | `f_sigLabels`, `f_join` | 5155–5197 | One merged label per side: tier · score (+ base), SB / SETUP / Demand 50% / IB / Doji / TL / CRT / TSoup / HTF CRT / HTF TSoup / FEM / TRAP parts | Visual only |
| SB exit chips | `f_chip` | 5200–5203 | "◆ SB time exit", "◆ SB structure exit" | Visual only |
| Trade plan | `f_tradePlan`, `showTrade` | 5206–5259 | E / SL / TP1 / TP2 / TP3 lines + labels; RR net; ≈ units (`riskMoney`); TP1 % (`tp1Pct`) | Visual only |
| POI boxes | `f_drawPoi`, `showPoi`, `sbShowPlan` | 5262–5335 | HTF demand/supply boxes, FEM FVG, machine anchor / CE, SB CE line, SB target | Visual only |
| NEXT level | `f_drawNextLvl`, `f_nextLvlTxt` | 5352–5411 | Box + line + label "BUY/SELL T<score> [kind] lo-hi (dist %) ·fresh" | Visual only |
| Extend / focus | `f_extendDraw`, `focusMode`, `focusAtr` | 5414–5449 | Extends boxes/lines; hides far objects | Visual only |
| Other drawn objects | `showEq`, `showTL`, `showSesHL`, `showFvg`, `showZones`, `sbShowBox` | 1362, 1379, 1799, 2641, 2836, 1517 | EQ lines, trendlines, session lines/labels, FVG boxes, zone boxes, SB boxes | Visual only |

### 4.16 Dashboard (`f_dash`, L5454–5556 · 2×12 · top-right · `showDash`)

| Row | Label | Content |
|---|---|---|
| 0 | LQ-SD-PA v3.8.3 | Regime |
| 1 | Bias <tf> | EMA bias · D bias · HTF structure → combined `htfB` |
| 2 | Struct · sweep | Internal / external direction · SSL / BSL quality |
| 3 | Range pos | Premium / Discount % · tight · OTE |
| 4 | Next demand | T<score> [kind] · ATR distance · fresh |
| 5 | Next supply | Same for supply |
| 6 | Trigger · FEM | Recent MSS / CHoCH / BOS / CISD · FEM state |
| 7 | ◉ Setup L / S | Machine stage text (`f_suTxt`) |
| 8 | Alignment | Long / short score and tier |
| 9 | Session | Session name · volatility warning · SB status / minutes left |
| 10 | Trade | Flat / pending / LONG-SHORT entry SL · TP1✓ TP2✓ · SB |
| 11 | Verdict | Signal, or the blocking reason (16-step precedence: plan kill → gate kill → score → stage → day closed → trade live → POI conflict → neutral bias → outside SB → day filter → chop → volatility → best score → no liquidity → waiting) + ADR % |

### 4.17 Debug Table (`f_dbg`, L5562–5586 · 2×5 · bottom-right · `showDbg`)

| Row | Label | Content |
|---|---|---|
| 0 | Sweeps raw/eff k | SSL / BSL raw & effective grade, kind, live/stale |
| 1 | Machine L / S | Stage · reason |
| 2 | Score C/L/P/T/E | Context / liquidity / POI / trigger / execution sub-scores |
| 3 | Counts · untrk | A, A+, L, S, TP1, TP2, TP3, SL, expired, untracked |
| 4 | ◬ LT · ◆ SB · day | LT machine state / last event, SB window/tag/entries, day signals / losses, spread |

### 4.18 Alerts (MODULE 23)

**alertconditions (30)**

| Line | Title | Condition |
|---|---|---|
| 5594 | [SIGNAL] A+ LONG | `anyLong` and tier ≥ 4 |
| 5595 | [SIGNAL] A+ SHORT | `anyShort` and tier ≥ 4 |
| 5596 | [SIGNAL] A LONG | `anyLong` and tier = 3 |
| 5597 | [SIGNAL] A SHORT | `anyShort` and tier = 3 |
| 5598 | [SIGNAL] ◉ Setup machine entry | `sigMCLong or sigMCShort` |
| 5599 | [SIGNAL] Any LONG | `anyLong` |
| 5600 | [SIGNAL] Any SHORT | `anyShort` |
| 5601 | [SIGNAL] ◎ Fractal entry model | FEM signal surviving gates |
| 5603 | [SETUP] Armed (quality sweep) | stage → 1 |
| 5604 | [SETUP] POI tapped | stage → 2 |
| 5605 | [SETUP] Structure shifted | stage → 3 |
| 5606 | [SETUP] Invalidated / expired | stage 1–3 → 0 |
| 5609 | [TRADE] TP1 hit | `cntTP1` up |
| 5610 | [TRADE] TP2 hit | `cntTP2` up |
| 5611 | [TRADE] SL hit | `cntSL` up |
| 5616 | [TRIG] MSS | `mssUp or mssDn` |
| 5617 | [TRIG] External CHoCH | `eChochUp or eChochDn` |
| 5619 | [LIQ] Swing sweep | `sslSweep or bslSweep` |
| 5620 | [LIQ] EQH/EQL pool swept | `eqhSwept or eqlSwept` |
| 5621 | [LIQ] Prev-day / week level swept | PD / PW sweeps |
| 5622 | [LIQ] Session level raided | `sesHiSwept or sesLoSwept` |
| 5624 | [POI] Price entered next demand | `touchNextBuy` |
| 5625 | [POI] Price entered next supply | `touchNextSell` |
| 5626 | [POI] FEM FVG locked | FEM stage → 3 |
| 5628 | [CTX] Volatility window started | `inNews` rising |
| 5629 | [CTX] Volatility window ended | `inNews` falling |
| 5636 | [LT] Trap setup detected | `ltArmEvt` |
| 5637 | [LT] Bullish trap entry | `sigLTLong and anyLong` |
| 5638 | [LT] Bearish trap entry | `sigLTShort and anyShort` |
| 5681 | [SB] ◆ Silver Bullet entry | `sbFireL or sbFireS` |

**alert() feeds** (all `alert.freq_once_per_bar_close`)

| Line | Toggle | Format |
|---|---|---|
| 5655 | `jrnlEnable` | `LQCE|ticker|tf|L/S|CE<p>|SLa<anchor stop>|SLr<raid stop>` — on FVG anchor lock, no signal |
| 5655 | `jrnlEnable` | `LQJRNL|ticker|tf|L/S|SB/MC/LT/ENG|tier|sc<score>|k<kind>q<grade>sh<shift>w<win>|regime|E|SL|T2|d<trades>/<losses>` |
| 5672 / 5674 | `ltDynAlert` | `◬ LT BUY/SELL ticker · patterns · score · E … SL …` |
| 5687 | `sbDynAlert` | `◆ SB BUY/SELL ticker · window · CE/edge · tier · SL TP1 TP2` |
| 5697 | `sbDynAlert` | `◆ SB TP1 · stop to BE · SL …` |
| 5699 | `sbDynAlert` | `◆ SB TIME EXIT · close / reduce, rest to BE` |
| 5701 | `sbDynAlert` | `◆ SB STRUCTURE EXIT · close the remainder` |
| 5705 | `sbDynAlert` | `◆ SB setup gone · <reason>` |

---

## 5. request.security Calls

| Line | TF | Data |
|---|---|---|
| 1718 | D | `high[1]`, `low[1]` → PDH / PDL (`lookahead_on`) |
| 1719 | W | `high[1]`, `low[1]` → PWH / PWL (`lookahead_on`) |
| 2105 | `biasTf`, D (via `f_bias` at 2113–2114) | EMA bias |
| 2182 | `biasTf` | `f_htfStruct` → direction + protected swings |
| 2268 | `htfTf` | `f_crtTbsHtf` → HTF CRT / TBS flags + stop anchors |
| 2383 | `htfTf` | `f_htfPoi` → 3+3 HTF FVG slots |
| 2430 | D | ADR (`ta.sma(high-low, adrLen)[1]`) |

---

## 6. Configured but Unused / Visual-Only Items

| Item | Line | Classification |
|---|---|---|
| `p4PoolHi` (returned by `f_ltPools`) | 3847 | Configured but unused |
| `protLowI`, `protHighI` (returned by internal `f_structure`) | 1988 | Configured but unused |
| `sbBoxes` SB window range boxes | 1501–1526 | Visual only |
| `bD` daily EMA bias | 2114 | Visual only (dashboard) |
| `sbRemMin`, `sbWinTxt`, `recentBosUp/Dn` (direct use) | 1450–1498, 2044–2079 | Visual only (dashboard) |
| `scoreLong/Short` SB bonus part | 3602–3611 | Display / label / journal only (gate reads base score) |
| `riskMoney`, `tp1Pct` | 1083–1084 | Visual only (trade-plan label text) |
| `cntTP3`, `cntExp`, `cntSbEnt`, `cntUntracked` | 4767–4792 | Debug-table display only |
| Structure chips, trade plan, POI boxes, NEXT level, dashboard, debug | see §4.15–4.17 | Visual only |
