# Forensic Audit · `liqudity_trap_trading.v3.8.1.txt`

Date: 2026-10-14 · Auditor: Claude (Fable 5.1) · Scope: full source read, 5,607 lines, Pine v6 `indicator()`.
No source file was modified. Every line number below is from this file. Nothing was compiled or backtested locally (no Pine compiler, no strategy twin in the folder).

Legend: **CONFIRMED** = code evidence quoted · **DESIGN** = code does what it says, trading logic is weak · **HYPOTHESIS** = plausible, not proven from code alone · **UNVERIFIED** = needs TradingView.

---

## Report 1 — Executive Summary

### 1.0 সংক্ষেপ (Bangla)

- **সবচেয়ে বড় finding: ফাইলের নাম `v3.8.1`, কিন্তু ভিতরের কোড `v3.6.1`।** লাইন 2-এর BUILD stamp `v3.6.1-b1`, `indicator()` title `v3.6.1`, dashboard header `v3.6.1`। `git show HEAD:…v3.6.1.txt` এর সাথে byte-for-byte (CRLF বাদে) **identical**। অর্থাৎ v3.7-এর FIX-Z1…Z13 (১৩টা defect repair) আর v3.8-এর FIX-A1…A3 (P1 তিনটা) — **এই ফাইলে নেই**। যে বাগগুলো আগের দুই review-তে ঠিক করা হয়েছিল, সেগুলো সব এখানে ফিরে এসেছে।
- **Repaint নেই।** সাতটা `request.security` সবই `[1]` + `lookahead_on`; প্রতিটা state write `confirmed` guard-এ। Pivot delay (5/12 bar) আর HTF close delay (1 LTF bar) স্বাভাবিক, repaint নয়।
- **Runtime crash-এর path পাওয়া যায়নি।** Array loop সব descending, `na` guard আছে।
- **Trading logic-এ 2টা P1 class সমস্যা** (stop ছাড়া ৪টা engine, body-blind break latch) + **১টা P1 process সমস্যা** (version regression) + **১টা P1 accounting bug** (break-even stop hit = loss গোনা হয়, daily loss limit ভুল ট্রিগার করে)।
- **ICT model-এর structural gap:** default setting-এ ordinary machine শুধু reversal করে। External uptrend-এ pullback → sweep → BOS continuation long কখনো machine থেকে আসে না (shift = external CHoCH লাগে, যেটা বাই ডেফিনিশন bearish external structure থেকেই আসে)।
- **সুপারিশ:** এই ফাইল থেকে কাজ শুরু না করে `v3.8.txt` (v3.7 Z-fixes + v3.8 A-fixes) এর উপর D1–D4 cleanup বসিয়ে `v3.8.2` বানানো। তারপর এই রিপোর্টের P1 → P2 ক্রমে। প্রতিটা ধাপে compile check + journal-line diff।

### 1.1 Condition

| Area | Verdict |
|---|---|
| Version integrity | **FAILED** — file is v3.6.1 code under a v3.8.1 name; 16 previously applied fixes absent |
| Repainting / lookahead | **PASS** — none found |
| Runtime safety | **PASS** — no crash path found |
| Signal correctness | **CORRECTION NEEDED** — 4 engines ship a structure-less stop; structure latch misses displaced BOS; BE-stop counted as loss |
| Entry quality | **MIXED** — machine path is well-specified (sweep → shift → FVG CE → confirmation); engine candidates are weaker and mostly muted at defaults |
| Risk management | **CORRECTION NEEDED** — stop anchors (D1, D5, Z11, Z13), reward clamp (D8, D21) |
| Validation | **ABSENT** — strategy twin referenced in header (line 643) does not exist; nothing has been measured |

### 1.2 Strongest features (verified)

- One-sweep-per-level latch (FIX-W1, 1526–1547) and multi-bar reclaim (1540–1547).
- Raw vs effective sweep grade separation (1588–1591, 1983–1984).
- Setup state machine with explicit invalidation reasons and stage clocks (4066–4360).
- Shift-leg FVG anchor must be cut at/after the shift bar (4175, 4180).
- CE limit fill tested at ask (`loA <= ceL`, 4208) and confirmation candle must close past CE in outer 30 % (4225).
- Two-stop fallback (raid wick → anchor) before the risk cap (4242–4244).
- Viability gate: slippage, risk cap, TP2 clamp to opposing POI, net-of-cost RR (4579–4622), deferred engine fill re-validated at the open (4728–4747).
- Machine-readable journal line per signal (5555–5569).

### 1.3 Major risks

1. Working from a mislabeled file silently reverts 16 fixes (Report 3 §A).
2. Four engines (HTF CRT, HTF TBS, inside bar, doji) send a `min(low, low[1]) - pad` stop (4580–4583) with no structure behind it.
3. Break-even stop-outs increment `lossToday` (4775–4777) → governance halts the day after two scratch trades.
4. Ordinary machine cannot produce continuation entries in an external trend (Report 4 §5).

### 1.4 Top recommendations (ordered)

1. Re-base: `v3.8.txt` + D1–D4 dead-code cleanup → `v3.8.2`. Compile. Diff journal lines vs v3.8.
2. Apply Z10 fix (BE stop ≠ loss) — 5 tokens, immediate governance correctness.
3. Apply Z11 (track deeper wick before shift) and D5 (LT stop over raid wick).
4. Build the validation harness before touching `minScore`, `minRR`, `maxRiskAtr`, profiles.

---

## Report 2 — Complete Feature Inventory

Architecture: 23 modules, linear flow. Inputs (656–1134, 3595–3655, 5553) → candle anatomy / CISD / IFC (1208–1289) → pivots + EQ + trendline anchors (1294–1391) → session clock + SB windows (1404–1501) → liquidity engine (1526–1887) → structure internal/external + MSS (1897–2044) → HTF bias / structure / CRT-TBS / POI / ADR (2049–2376) → dealing range + SB lock (2409–2471) → regime (2483–2545) → FVG registry (2552–2705) → zone engine (2714–3104) → engine candidates (3110–3281) → FEM (3288–3354) → machine state decl + direction lock (3363–3394) → score + tier (3415–3558) → LT engine (3595–3958) → setup machine (3972–4360) → final gate (4367–4547) → viability gate (4568–4651) → tracker (4675–5012) → drawings (5017–5357) → dashboard/debug (5374–5494) → alerts (5500–5607).

Outputs: plot 8 + plotchar 12 + bgcolor 3 + alertcondition 30 = **53 / 64** (matches header line 99). `request.security` calls: 7 distinct sites (1686, 1687, 2050×2 call sites, 2126, 2202, 2313, 2360) = 8 runtime calls. Inputs: 219. Drawing caps 500/500/500.

Status key: **W** working as intended · **F** implemented but potentially flawed · **P** partial · **U** UI exists, logic missing · **D** duplicate/conflicting · **N** not implemented · **?** unable to verify.

### A. Liquidity

| Feature | Impl | Location | Actual logic | St | Findings |
|---|---|---|---|---|---|
| BSL / SSL (swing) | Yes | 1294–1295, 1361, 1389 | `ta.pivothigh/low(pivLen)` → `lastRes/lastSup`, confirmed only | W | pivLen-bar delay (normal) |
| Swing sweep | Yes | 1546–1547 | wick through + close back, OR multi-bar reclaim; one event per level (`sslSpentLvl`) | F | Z1: no `not supBroken` on single-bar path → poke after accepted break counts; grade 2 cheap (1553–1558) |
| Multi-bar sweep | Yes | 1540–1545 | close back through within `reclaimBars` of latched break; extreme = lowest since break | F | Z3: penetration measured from multi-bar extreme, not reclaim candle |
| Sweep quality 1–4 | Yes | 1549–1572, 1983–1984 | firm/pen → 2; +outer30 % & 0.5 ATR body → 3; MSS within TRIG_LOOK → 4 (eff only) | W | raw/eff split correct |
| EQH / EQL | Yes | 1334–1345, 1364–1375 | consecutive pivot pair within `eqTol` ATR; pool array max 8; expires `eqMaxAge` | F | D17: only consecutive pivots |
| EQ sweep | Yes | 1641–1682 | wick through + close back → stamp kind 2 grade `qPoolHi/Lo` | F | D18: grade floor 2 (1611–1612), 1-tick poke = valid |
| PDH/PDL/PWH/PWL | Yes | 1686–1724 | `[1]`+lookahead_on; one raid per level per day/week | F | Z2: acceptance (close through) does not spend the level |
| Session H/L (Asia/Lon/NY) | Yes | 1736–1849 | tracked always; raid vs break split; re-raid after 1 ATR walk-off | W | Asia stamps only inside SB ctx (1835) |
| Liquidity pools (wick clusters) | Yes | 3688–3762 | LT-3 lower-wick cluster pool, LT-4 upper-wick cluster | W | LT engine only |
| Pool clustering / confluence | No | — | no count of overlapping pools | N | improvement candidate |
| Engineered-liquidity memory | Yes | 2148–2154 | EQ/session/PD raid within `sweepLook` → +5 score | W | |
| Inducement detection | Partial | 1892–1893 comment; LT-2/LT-6 | "minor pullback runs = inducement" is comment only; LT-2/6 weak-poke patterns | P | no explicit inducement object |

### B. Structure

| Feature | Impl | Location | Actual logic | St | Findings |
|---|---|---|---|---|---|
| BOS / CHoCH internal | Yes | 1897–1941 | protected-swing engine, body ≥ `structDisp` ATR | F | D2: break latch 1882–1887 is body-blind, engine is body-aware → displaced BOS lost |
| BOS / CHoCH external | Yes | 1944–1964 | same engine, `extPiv` pivots | F | same D2 |
| MSS | Yes | 1969–1970 | external CHoCH + `sslInPlay` + qual ≥ 2; upgrade bound to raid within TRIG_LOOK | W | |
| HTF structure | Yes | 2065–2128 | same engine inside `request.security`, `[1]` | W | Z5: `biasTf` may be below chart TF |
| Order block | Yes | 2938–2943, 2963–2968 | opposing candle at bar[2] beside S/D imbalance | F | only bar[2]; not tied to the break |
| Breaker / mitigation | Yes | 2775–2792, 2816–2826 | violated zone flips; breaker needs `recentSsl and recentStructUp` | W | two flips on one bar → only last claims band (2805–2807, 2877) |
| FVG chart-TF | Yes | 2552–2669 | registry with partial/inversion/age | F | Z6: no min height; D7 HTF twin |
| IFVG | Yes | 2616–2634, 3013–3034 | close through → flips, re-registered as zone kind IFVG | W | |
| Premium / discount | Yes | 2409–2432 | running leg extremes since older anchor swing; clamped | W | known pdPos step on new pivot (comment 2402) |
| OTE | Yes | 2427–2432 | 0.62–0.79 of leg | W | |
| Displacement | Yes | 2009–2010, 2913–2914, 1909, 4045 | three thresholds: `dispFactor` 1.2, `structDisp` 0.5, `sbDispAtr` 0.8 | F | D14: capped ATR loosens body tests |
| Regime | Yes | 2483–2534 | TRENDING / TRANSITION / CHOP / RANGING with thrust vote | W | |

### C. Trap / false-breakout

| Feature | Impl | Location | Actual logic | St | Findings |
|---|---|---|---|---|---|
| Sweep-and-reversal (machine) | Yes | 4127–4246 | SWEPT → (POI) → SHIFTED → CE/confirmation | W | reversal-only (Report 4 §5) |
| Turtle soup chart-TF | Yes | 3130–3137 | 20-bar extreme age 4–60, close back, upper half | F | no min penetration; tier rarely A (Report 5) |
| CRT chart-TF | Yes | 3120–3126 | 3-candle range/raid/reclaim/deliver | W | candle-1 range only, no liquidity test |
| HTF CRT / TBS | Yes | 2185–2209 | computed on HTF, 1-LTF-bar late | F | D1: no own stop |
| Trendline sweep | Yes | 3140–3203 | edge-triggered touches ≥ 2, wick below + close above + conf | W | 5-bar pivot lines, low quality |
| LT-1…LT-7 | Yes | 3764–3955 | 7 patterns, per-direction machines, score ≥ class floor | F | D5 stop, D6 veto; 2 long vs 5 short patterns |
| Equal-high / session trap | Partial | via pool kinds 2/4 | sweep memory only | P | no dedicated trap object |
| Sweep + displacement | Yes | 3541–3542, 1969 | `instSweepL` = raw ≥ 3 + MSS | W | |

### D. Entry / risk

| Feature | Impl | Location | Actual logic | St | Findings |
|---|---|---|---|---|---|
| Machine entry CE | Yes | 4208, 4217, 4231 | `loA <= ceL` limit touch; plan price = CE | W | gap-through-CE fills at CE (optimistic, P3) |
| Machine entry confirmation | Yes | 4225–4227 | close ≥ CE and outer-30 % | W | |
| SB entry | Yes | 4193–4212 | tagged, window-bound, HTF + P/D on locked range | W | |
| Engine entries (10) | Yes | 4484–4503 | gated by `engOKL/S` = longOK + tier ≥ engRank | F | tier reads global context, not the engine's level |
| Stop selection | Yes | 4568–4583 | per-engine stop, highest conviction first, fallback | F | **D1**: sig3/sig4/sigHCrt/sigHTbs have no stop var |
| Risk cap / reject / clamp | Yes | 4595–4602 | `maxRiskAtr`, reject or clamp | W | |
| Slippage guard | Yes | 4591–4593 | waived for CE limit | F | Z12: stale `sbCeFillL` after mute |
| TP1 / TP2 / TP3 | Yes | 4937–4960 | 1R / rrMult clamped to POI / max(3, rr+1) or liquidity | F | D8, D21 |
| Min RR net of cost | Yes | 4615–4619 | `(reward − cost)/(risk + cost)` | W | |
| Partial / BE / trail | Yes | 4780–4786, 4836–4849 | BE after TP1; SB trail after TP2 | F | Z10: BE stop-out booked as loss |
| Duplicate signals | Yes | 4516–4535 | SB-13 rank hierarchy | W | |
| Direction lock | Yes | 3392–3394 | open trade or stage ≥ 2 owns chart | W | |
| Governance | Yes | 4390–4397, 5010 | daily count + loss count | F | N-D: counts untracked signals, tooltip says tracked; Z10 |
| Trade-state reset | Yes | 4909–4917 | ACTIVE ends with tracker | W | N-C: 18B kill → stage 0, gate kill → stage 3 (inconsistent) |

### E. Advanced

| Feature | Impl | Location | Actual logic | St | Findings |
|---|---|---|---|---|---|
| MTF bias EMA + structure | Yes | 2049–2138 | agreement or neutral | W | Z5 |
| Neutral-bias policy | Yes | 700–702, 2137–2138 | block / follow / allow | F | **D10** arm/shift deadlock in Follow |
| Killzones | Yes | 1407–1415 | `useKZ` default **off** | F | D11: Asia counted as killzone |
| News windows | Yes | 1417, 1458–1459 | fixed clocks | W | not a calendar (documented) |
| Volume filter | Yes | 1227–1229, 1570 | optional relVol | W | |
| ATR cap | Yes | 1208–1210 | min(raw, 1.5 × avg50) | F | D14 |
| ADR exhaustion | Yes | 2360–2376 | closed-day ADR | W | D16 day boundary |
| Alerts | Yes | 5502–5607 | 30 alertconditions + alert() feed | F | FEM alert bypasses 18B (5509); D19 no CE pre-fill |
| Repaint protection | Yes | `confirmed` ×~90; `[1]`+lookahead_on ×7 | | W | |
| Drawing management | Yes | 3040–3053, 5321–5357 | caps, focus mode | W | |
| Symbol profiles | Yes | 669–677, 758, 772, 1158–1162, 1180 | integer-resolved presets | ? | values are opinions (header 646–649) |
| Strategy twin / harness | No | header 433–442, 643–645 claim it | `find` → no such file | N | **D3** |

---

## Report 3 — Forensic Bug Report

### A. Version integrity (process)

**V-1 · P1 · CONFIRMED — the file is v3.6.1, not v3.8.1**

- Evidence: line 2 `// BUILD v3.6.1-b1 · 2026-10-14 · Phase-1 dead-code pass`; line 650 `indicator("… v3.6.1", "LQ-SD-PA v3.6.1"`; line 5379 dashboard `"LQ-SD-PA v3.6.1"`. `diff --strip-trailing-cr` against `git show HEAD:…v3.6.1.txt` → identical. `diff v3.6.txt v3.8.1.txt` → 98 lines, all D1–D4 cleanup. `grep -c slHCrt|resBosDone|armBiasL|FIX-A1` → 0 in this file, 4/5/2/8 in `v3.8.txt`.
- Root cause: file copied/renamed from v3.6.1, not from v3.8.
- Impact: FIX-Z1…Z13 (v3.7) and FIX-A1…A3 (v3.8) are absent. Every defect those fixed is live again (Z1–Z13 and D1/D2/D10 below).
- Fix: do not patch this file. Start from `v3.8.txt`, apply the D1–D4 cleanup, stamp `v3.8.2`. Keep `v3.8.1.txt` as-is for the record or delete it.
- Regression: `grep` the 16 FIX markers; `diff v3.8.txt v3.8.2.txt` must show only D1–D4 + stamp lines.

### B. Repainting / future data — none found

| Test | Result | Evidence |
|---|---|---|
| `request.security` ×7 | all `expr[1]` + `lookahead_on` | 1686, 1687, 2050, 2126, 2202, 2313, 2360; function exports `[_x[1]]` at 2124, 2200, 2309 |
| HTF signal timing | first chart bar after HTF close (`newHtfBar`, 2205) | 1-LTF-bar delay, legitimate |
| Pivot confirmation | `pivLen`/`extPiv` right bars | drawings back-shifted (1339, 2988), signals not |
| State writes | every `var` write under `confirmed` or Pine rollback | e.g. 1261, 1619, 1816, 2000, 2594, 2918, 3217, 3270, 3300, 3710, 3855, 4066, 4249, 4579, 4717, 4932 |
| Intrabar | dashboard/NEXT/POI redraw on `barstate.islast` | display only (5181, 5277, 5323) |
| Alerts ↔ labels | both read final `anyLong/anyShort`, `finalTierL/S` | 5097–5104, 5502–5508 |
| Day/session | NY timezone, `time("D")` exchange day | 1405, 1441, 2361, 4399 |

Config hazards (not repaint, but wrong data): **Z4** `htfLive = htfTf != timeframe.period` (2176) is a string compare, so `htfSel="15"` on a 60-min chart requests a LOWER TF; **Z5** `biasTf` (2056) has no floor vs chart TF. Both return last-sub-bar values under lookahead_on. P3.

### C. Confirmed trading-logic defects

Format: ID · severity · location · excerpt · root cause · impact · reproduce · fix · regression.

**D1 · P1 — four engines have no stop**
- 4568–4571 chain: `sigMCLong ? slMCLong : sigFEMLong ? slFEMLong : sigSDLong ? slSDLong : sigCRTLong ? … : sigTLLong ? slTLLong : sigLTLong ? slLTLong : na`. No branch for `sig3Long`, `sig4Long`, `sigHCrtLong`, `sigHTbsLong` (2206–2209, 3256–3257, 3280–3281). Fallback 4580: `math.min(low, low[1]) - SL_PAD_ATR * atr`.
- Root cause: FIX-P0-5 added per-engine stops for 6 of 10 engines.
- Impact: HTF turtle soup on M5/H1 gets a stop under the last two M5 bars, far above the H1 sweep wick. Doji reversal stop sits under the doji, not under the raided `lastSup`. Risk cap passes these (small distance) so they look "safe" and get run.
- Reproduce: M5, HTF=60, H1 candle sweeps 20-bar low and reclaims → `sigHTbsLong` on next M5 bar → label SL = last-two-M5-bar low − pad.
- Fix: v3.8 FIX-A1 (HTF tuple exports `low[2]`/`low[1]`; IB `(ibLow+mLow)/2`; doji `min(lastSup, lowest(low,5)) − pad`). ~90 tokens.
- Regression: SL distance of these 4 signals before/after; all other engines unchanged.

**D2 · P1 — body-blind break latch eats the displaced BOS**
- 1882 `brokeUp = not na(lastRes) and not resBroken and close > lastRes`; 1884 `resBroken := brokeUp and confirmed ? true : resBroken`; 1909 `if confirmed and body >= structDisp * atr` gates `f_structure`.
- Root cause: latch fires on any close; engine ignores sub-threshold bodies; next bar `brokeUp` is false.
- Impact: BOS under-count → regime reads CHOP/RANGING more, `regEBosUp` false, ★HP demand not awarded (2921), `trigLong` loses 5.
- Reproduce: bar A closes 0.3 ATR body above `lastRes`; bar B 1.6 ATR body higher. No BOS chip.
- Fix: v3.8 FIX-A2 second latch `resBosDone/supBosDone` for structure only. ~40 tokens. Changes structure engine behaviour → separate regression (BOS count, 10 manual samples).

**D10 · P1 — neutral bias + "Follow chart structure" deadlocks the ordinary machine**
- 2137 `biasOkL = … (htfB == 0 and (… or (neutralMode == "Follow chart structure" and extDir >= 0)))`; arm 4128 `(not armNeedHtf or biasOkL)`; shift 4035–4036 = `mssUp or eChochUp`; `eChochUp` only from `dir == -1` branch 1919–1927.
- Root cause: arm needs `extDir >= 0`, shift needs `extDir == -1`.
- Impact: at structure/EMA disagreement (turning points, exactly where sweep + CHoCH land) no ordinary long/short arms and shifts. SB path survives (internal CHoCH/CISD).
- Fix: v3.8 FIX-A3 `armBiasL` ignores `extDir` at the arm gate. ~10 tokens.

**Z10 · P1 — break-even stop-out is booked as a loss**
- 4775–4777 `if low <= trdSL → cntSL += 1; lossToday += 1` (also 4801–4804, 4824–4827, 4863–4866). After TP1, 4786 raises `trdSL` above entry.
- Impact: two scratch trades → `govLossOK` false (4396) → day closed. Counters report losses that were ≥ 0 R.
- Fix: `lossToday += trdSL < trdEntry ? 1 : 0` for longs (mirror for shorts); optionally `cntBE` counter. ~10 tokens.
- Regression: day with TP1 then BE-stop must not decrement `govLossOK`.

**Z11 · P2 — stage 1–2 deeper wick does not move the sweep extreme**
- `suLSweepExt` written only at 4134; invalidation 4071 `close < suLSweepExt`; stop 4243 `nz(suLSweepExt, low)`.
- Impact: a second, deeper wick (close holds) before the shift leaves the stop inside the real raid wick.
- Fix: at stage 1–2, `suLSweepExt := math.min(suLSweepExt, low)` after the invalidation block (v3.7 FIX-Z11). ~10 tokens.

**D5 · P2 — LT stop ignores the raid wick between arm and confirmation**
- 3895 `_ltSlL := math.min(low, _ltLLevel) - pad`; 3938 mirror. Arm-bar high (the poke) is not tracked.
- Fix: track `_ltSHiMax` since arm; SL = `max(that, level) + pad`. ~30 tokens.

**Z13 · P2 — short stop and spread**
- 4357 `slRaidS = max(high, anchorT, ext) + pad` (bid prices); tracker 4801 `hiA >= trdSL` where `hiA = high + spr`. Effective bid distance = pad − spr. With `spreadIn` > `SL_PAD_ATR` × ATR the stop sits inside the wick.
- Fix: `+ spr` on the short stop anchors (MC, SD, CRT, TBS, TL, LT, fallback). ~20 tokens.

**Z1 · P2 — sweep from the wrong side of an accepted break**
- 1546 `sslSweep = … ((low < lastSup and close > lastSup) or sslRecl) and sslLvlFresh` — no `not supBroken` on the single-bar path.
- Reproduce: close below `lastSup` (latched), later price climbs back above, pokes below, closes above → "sweep", arms machine on a level already accepted through.
- Fix: `(not supBroken and low < lastSup and close > lastSup) or sslRecl`. ~5 tokens.

**Z2 · P2 — PDH/PDL/PWH/PWL not spent on acceptance**
- 1703 `pdhSweep = … high > pdh and close < pdh and not pdhDone`; `pdhDone` set only on sweep (1707).
- Fix: `pdhDone := pdhSweep or (close > pdh) ? true : pdhDone`. ~10 tokens.

**Z6 · P2 — chart-TF FVG has no minimum height**
- 2564 `bullFVG = low > high[2]`; registry push 2594; latest-FVG 2686; machine anchor 4175/4180; SB floor 4062 reads `sbFvgMinAtr` (0.10) only.
- Impact: 1-tick gap becomes the retest anchor; CE = distal edge; stop under it is noise. D7 is the HTF twin (2264, 2276).
- Fix: `bullFVG = low - high[2] >= minZoneAtr * atr` (v3.7 FIX-Z6); HTF: same with HTF ATR inside `f_htfPoi`. ~20 + 20 tokens.

**Z7 · P2 — ★HP demand on any old close above a pivot**
- 2921 `bs = not na(lastRes) and close[1] > lastRes` — the displacement candle just needs to be above the last pivot, not to have broken it.
- Fix: `bs = resBrkBar == bar_index - 1` (the leg itself broke). ~10 tokens.

**Z8 · P2 — FEM does not reset on close through the HTF POI**
- 3301 `if femL >= 1 and (na(hPoiBTop) or bar_index - femLBar > femWait)` — a close below `hPoiBBot` at stage 1–2 is not tested; HTF registry deletes only at HTF close (2242).
- Fix: `or close < hPoiBBot` at stage 1–2. ~10 tokens.

**Z9 / D22 · P2 — anchor touch scored twice**
- 3445 `inDemand = useAnchL ? (low <= dmdTop and close >= dmdBot)` (+10, +5 fresh); 3496 `retestLong = not na(dmdTop) and low <= dmdTop and close >= dmdBot` (+5). Same test, 20 points.
- Fix: `retestLong := useAnchL ? false : retestLong` or drop the exec 5 when anchored. Expect stage-3 scores ~5 lower; re-check `minScore`.

**Z12 · P2 — stale SB CE flag waives the slippage guard for an engine signal**
- 4445–4450 clears `sbSigLong` and `mcCeFillL` but not `sbCeFillL`; 4590 `ceLimitFill = sbCeFillL or …` read for whichever signal survived.
- Fix: add `sbCeFillL := false` in the same block. ~5 tokens.

**F-ALERT · P2 — FEM alert fires on a rejected signal**
- 5509 `alertcondition(sigFEMLong or sigFEMShort, …)`; 18B rollback 4631–4636 clears `anyLong`, `sigMC*`, `sbSig*` only.
- Fix: `(sigFEMLong and anyLong) or (sigFEMShort and anyShort)` (as LT does at 5545). 0 net tokens.

**D6 · P2 — LT veto mutes opposing engines up to 25 bars; invalidation needs a displacement body**
- 3904 `close > _ltSLevel + ltInvAtr * atr and bullBar and body >= dispFactor * atr`; veto 4546–4547; `ltWaitBars` 25 (3635).
- Fix: drop the body condition, or cap veto at `ltWaitBars / 2`.

**D8 · P2 — TP2 clamp sees POI zones only**
- 4609–4612 clamp to `nsBot`/`nbTop`; 4968–4981 liquidity chain also uses session H/L, PDH/PWH but only for SB TP3.
- Fix: reuse `f_nearAbove` chain in 18B. Signal count will fall; measure.

**D21 · P2 — clamp is grade-blind** (4609): a score-2 RB/MIT 0.8 ATR above blocks reward. Fix: clamp only `score >= 3` or HTF kind.

**D18 · P2 — pool raid grade floor 2** (1611–1612): no `firm`/`pen` test as swing sweeps have (1553–1557). Fix: grade 1 when `pen < NEAR_LVL_ATR*0.5*atr and not firm`.

**D20 · P2 — trigger decay clock ≠ retest clock** (3491–3494 `TRIG_LOOK`=10 vs 946 `retWait`=20): anchored retest 11–20 bars after the shift scores `trigLong`=0 → `minScore` fail → FIX-V8 bounce. Fix: when `useAnchL`, decay from `suLBar` over `sbRetWL`, floor 50 %.

**D9 · P2 — engine tier trigger accepts internal CHoCH / bare CISD** (3538) while the machine's default shift does not (4035–4036). Fix: `hasTrig = recentMssUp or f_recent(lastEChUpBar, TRIG_LOOK)`.

**D4 · P2 — display toggles gate detection** (2915–2916 `newDemand = showZones and …`, 2938 `showOB`, 2976 `showRB`). `showZones` off → no NEXT level, no `tapZone`, no TP2 clamp, LT-7 dead. Fix: toggle → transparency only.

**D7 · P2 — HTF FVG no min height** (2264, 2276). See Z6.

**N-C · P3 — 18B rejection resets stage to 0, gate rejection to 3**
- 4625–4627 `suL := 0; suLReason := planKill` vs 4468 `suL := gateKillL != "" ? 3 : suL`.
- A "reward blocked" by a zone that gets spent next bar loses the whole setup; a "score 48 < 50" keeps it. Fix: `suL := 3` for slip/reward kills, keep 0 for risk-cap ("you are late").

**N-D · P3 — `trdToday` counts untracked signals** (5010 increments on every signal bar; tooltip 1107 says "counts what this indicator fired", comment 1103 says "TRACKED entries only"). Doc fix, or move increment under `trackNew`.

**D15 · P3 — cancelled pending order not refunded** (5010 vs 4763–4764).

**D12 · P3 — SB-11 comment vs code** (4194–4198 says touch + confirmation; 4208 is touch only; FIX-T8 overrode). Fix comment.

**D13 · P3 — FEM execution lacks FIX-X9** (3324 `low <= femLTop and close > femLBot and zoneBullConf`, no CE/outer-30 %).

**D11 · P3 — Asia inside `inKZ`** (1414).

**D14 · P3 — ATR cap loosens body thresholds** (1210). Document.

**D16 · P3 — day boundary** (`time("D")` 2361 vs NY `dayofweek` 4399).

**D17 · P3 — EQH consecutive pivots only** (1335).

**D19 · P2 (usability) — no CE pre-fill alert** (5513 fires "Structure shifted" without price; SB feed lost "FVG locked" in v3.6).

**Z3 · P3** (1552 `pen` from multi-bar `ext`), **Z4/Z5 · P3** (2176, 2056).

### D. Runtime / Pine

- Arrays: every mutating loop is descending (`for i = size-1 to 0`) or `for in` + `break`; removes only in descending loops. **No index risk found.**
- `na`: `line.delete(na)`, `box.delete(na)` are no-ops; `nz()` on tuple ints; `f_pickPoi` na-guarded.
- `var`/`varip`: no `varip`; per-call-site `var` in functions (`f_structure`, `f_sesTrack`, `f_bias`) — Pine instantiates separately per call. Correct.
- Drawings: zones capped `maxZones`/side + RB ≤ 2 (3040–3053); FVG `fvgMaxKeep`; EQ 8; SB boxes `sbBoxKeep`; trade plan reuses 10 objects; labels per signal/structure event rely on the 500 cap (oldest auto-dropped). No leak.
- Series-length `ta.lowest/highest` (1542–1543, 2413–2416): allowed in v6; existed in compiled v3.6-b2. **Compile of this exact file: UNVERIFIED** (v3.6.1 = deletions only, low risk).
- Alerts: all `alertcondition` edge/once-per-bar-close; journal `alert()` `freq_once_per_bar_close`. No repeat-fire found.
- Performance: 7 security calls, ~15 array loops per bar over ≤ 20 elements. Fine.

### E. Verified correct (no action)

Spread geometry (4208, 4239, 4726, 4801, 4806, 4863, 4868) · same-bar SL before TP (4775, 4780) · entry-bar stop-out impossible for CE fills (4243 includes `low`) · FIX-P1-3 anchor-after-shift (4175, 4180) · direction lock reads previous bar (3392) · SB-13 hierarchy (4516–4535) · FIX-V8 rollback order (4466–4471 before 18B) · OTE math (2427–2432) · session parse and overnight Asia (1425–1435, 1747–1749) · `sbSetLive` one-bar-late read documented (2440–2442, 4906).

---

## Report 4 — Institutional-Style Footprint Assessment

Limitation: OHLC cannot show orders, dealers or participants. Everything below is price-action evidence labelled "institutional-style" by convention.

| Stage | Detected now | Code | Missing / too permissive / too restrictive | Real-time? | False-positive reduction |
|---|---|---|---|---|---|
| 1 Liquidity formation | swing pivots, EQH/EQL (consecutive), PDH/PDL/PWH/PWL, session H/L, wick-cluster pools, trendlines | 1294, 1334, 1686, 1736, 3688, 1348 | EQ across non-adjacent pivots (D17); no pool confluence count (EQH == session H == PDH is three stamps, not one stronger pool); no prior-session open | yes, pivot-delayed | rank pools by confluence; prefer kind ≥ 2 (already in `sbPoolPref`) |
| 2 Interaction / reclaim | single-bar and multi-bar sweep, pool raids, one event per level | 1540–1547, 1619–1636 | Z1 wrong-side sweep; Z2 acceptance not spending PD levels; D18 pool grade floor; grade 2 = 0.125 ATR firm **or** 0.25 ATR pen (cheap) | yes | require `firm and pen` for grade 2 on the machine arm, or `minArmQual` 3 per profile |
| 3 Rejection evidence | outer-30 % close, 0.5 ATR body (grade 3); pin/engulf/IFC; volume optional | 1553–1571, 1232–1237, 1284–1285 | sweep candle wick ratio not graded; Z3 pen from the wrong candle | yes | add `dnWick >= 2*body` to grade 3 as alternative to disp |
| 4 Displacement | 1.2 ATR body (zones, LT), 0.5 (structure), 0.8 (SB); single candle only | 2913, 1909, 4045 | no multi-candle leg displacement (3 bars × 0.6 ATR net is displacement too); D14 cap loosens | yes | `ta.change(close,3) >= dispFactor*atr` as alt |
| 5 Structure | internal/external BOS-CHoCH, MSS = ext CHoCH + sweep in play | 1897–1984 | D2 latch; **continuation gap**: `shiftUpOk` = `mssUp or eChochUp`; `eChochUp` exists only when external dir is −1 (1919–1927). In an external uptrend no long shift can exist → ordinary machine cannot take pullback → sweep → BOS longs (Model D). `+ internal CHoCH` option partially fills this | yes | add shift source "BOS in HTF trend" (eBosUp while `htfB > 0`) |
| 6 Imbalance | FVG registry, latest FVG, shift-leg lock after shift bar | 2552–2705, 4175 | Z6 no min height (chart), D7 (HTF); `cFvgBDisp` only enforced for SB (4062), ordinary anchor can be an incidental gap | yes | `cFvgBDisp` for ordinary anchor too (input) |
| 7 Retest / mitigation | stage 3, CE touch at ask, close-through-anchor invalidates, FIX-X6 | 4179–4246 | Z11 deeper wick; D20 trigger decay kills late retests; retest within `retWait` 20 | yes | fix Z11, D20 |
| 8 Entry confirmation | CE limit or confirmation candle past CE outer-30 %; tier A floor; minScore; P/D side | 4208–4244, 4405–4444 | D9 tier trigger inconsistency; N-C 18B kill; SB proximal path accepts a pin without CE close (4209) | yes | — |
| 9 Management | raid/anchor stop, risk cap, TP1 1R, TP2 clamp, TP3 liquidity, BE, SB trail/time/structure exits | 4242–4244, 4595–4619, 4937–4983, 4766–4893 | D1, D5, Z13 stops; D8/D21 clamp; Z10 loss accounting; non-SB has no structure exit | yes | — |

**Mandatory vs optional (as the code stands):** mandatory for a machine entry = quality sweep in play + shift (+ POI tap unless fastShift) + anchor + retest + tier A + base score ≥ 50 + RR ≥ 1.5 net. Optional = HTF alignment (scored, blocks only when `biasFilter` set), session (scored, `useKZ` off), volume (off), P/D (`mcReqPD` on, waivable), ADR (score/A+ only).

---

## Report 5 — Entry-Quality Assessment

### Long machine entry (4127–4246)

| Question | Answer | Evidence |
|---|---|---|
| Target liquidity | `lastSslLvl` (swing / EQ / PD / session) | 4133 |
| Sweep occurred | yes, reclaim must hold until shift | 4071, 4081 |
| Reversal evidence | shift = MSS / ext CHoCH (displaced close through protected swing) | 4035, 1909 |
| Structure consistent | at entry `extDir` has flipped to +1 by the CHoCH | f_structure 1925 |
| Timing | CE limit = retest entry; confirmation = retest + 1 bar; never on shift bar | 4191, 4208, 4225 |
| Zone proximity | anchor = shift-leg FVG or tapped zone | 4159, 4176 |
| Invalidation | close < anchor bottom; sweep undone; HTF prot low; SB window | 4228, 4071, 4113, 4116 |
| Target | TP2 = min(rrMult×R, next supply bottom); TP3 liquidity | 4608–4613, 4945–4960 |
| RR | net ≥ `minRR` 1.5 to TP2 | 4616–4619 |
| Duplicate | one arm per sweep, cooldown 15, direction lock | 4140, 4369, 3392 |

Classification: this path is a **retest/mitigation entry** (CE) with a **confirmation entry** fallback. Early/aggressive entry does not exist in the machine (by design). Weaknesses: D20 (late retests under-scored), Z11, Z6, continuation gap.

### Short machine entry (4280–4360) — mirror of long, same findings. Verified line-by-line: 4253/4071, 4256/4081, 4260/4092, 4264/4098, 4267/4108, 4270/4113, 4296/4145, 4312/4164, 4334/4208, 4342/4225, 4357/4243. One asymmetry: short plan price has no spread term (4354) while long adds `spr` (4239) — correct, the short sells the bid.

### Engine candidates (10 per side)

| Engine | Level targeted | Sweep proven | Confirmation | Own stop | Tier reality at defaults |
|---|---|---|---|---|---|
| Demand/Supply 50 % | zone CE | no (zone tap) | pin/engulf/IFC/CISD within 5 bars | yes (distal edge) | A only when `sslInPlay` + in zone + recent shift — plausible |
| CRT | candle-1 range | yes (wick + close inside) | candle-3 close beyond | yes (candle-2 wick) | A rarely: `sslInPlay` needs a pivot sweep, CRT range ≠ pivot |
| Turtle soup | 20-bar extreme | yes, 1-tick allowed | close in upper half | yes (wick) | same as CRT |
| HTF CRT / TBS | HTF candle range / 20-HTF-bar extreme | yes | HTF close | **no (D1)** | 1 LTF bar late; A rarely |
| Trendline | 5-bar pivot line | wick below + close above | optional conf | yes (wick) | low quality line |
| Inside bar | mother candle | no | strong close break | **no (D1)** | continuation, A ≈ impossible (needs `sslInPlay`) |
| Doji | `lastRes/lastSup` raid | yes (5-bar window) | pin/engulf + 0.5 ATR body | **no (D1)** | A rare |
| FEM | HTF FVG → LTF shift → LTF FVG | no (POI tap) | conf at FVG | yes | D13 weaker than machine; Z8 |
| LT-1/LT-4 (long) | broken resistance retest | breakout | conf after retest | yes, D5 | HIGH ≥ 70 floor |
| LT-2/3/5/6/7 (short) | failed breakout | yes (weak poke) | close back below + conf | yes, D5 | 5 short vs 2 long patterns → short-biased engine |

Conclusion: at `tierMode = "A and above"` the engine layer effectively reduces to zone-50 %, FEM and LT; CRT/TBS/IB/doji/HTF are near-dead because `f_tier` reads the global sweep memory, not the engine's own level. Either grade engines against their own level or accept that they are display context.

---

## Report 6 — False-Signal and Market-Condition Analysis

| Condition | Behaviour (code) | Likely false signals | Would a filter help? |
|---|---|---|---|
| Trending (external) | machine reversal-only → shorts in uptrend when a sweep + CHoCH lands (`biasOkL` blocks if HTF agrees); continuation longs only via engines | counter-trend machine shorts at neutral bias; `ctxLong` +10 for `extDir > 0` is paid to engines only | HTF bias already blocks; the gap is missing continuation logic, not a filter |
| Ranging | best fit: sweeps of range edges, CHoCH inside range | D21 clamp blocks reward against the opposite range POI; POI conflict resolution (3465–3471) | none; fix D21 |
| Chop | suppressed unless raw ≥ 3 + MSS (2541) | few | correct |
| High-vol news | fixed windows block; ATR cap (1210) loosens body tests for 14 bars after | post-news "displacement" everywhere → zones, shifts | body tests on `atrRaw` (D14), or widen window #1/#2 by profile |
| Low vol | ATR-relative → same signal count; LT −5 | thin-range "sweeps" of 0.25 ATR | `minArmQual` 3 when `atr < 0.7×avg50` (reuse `ltLowVol`) — measurable |
| London / NY | `useKZ` default off → 24h signals; Asia scores 2 | Asia session machine entries | enable `useKZ` with D11 fix; measure Asia vs London/NY win rate from journal |
| Session opens / prior extremes | session H/L raids kind 4; PD levels kind 3 | Z2: PDH broken at 09:00 "swept" at 11:00 | Z2 fix |
| Strong continuation | regime thrust vote keeps TRENDING | LT short patterns (5 of them) arm against every weak-looking breakout; veto mutes longs (D6) | D6 fix; `ltCtxOKShort` already needs raw ≥ 3 when TRENDING up |
| Failed breakouts / sharp reversals | the model's home case; multi-bar reclaim covers 2–4 bar failures | Z1 wrong-side sweeps after acceptance | Z1 fix |

Every proposed filter above names the defect it addresses and the journal field that measures it (`LQJRNL` regime / kind / grade columns, 5556–5568). No filter is proposed without a measurement.

---

## Report 7 — Prioritized Improvement Roadmap

Rule: new versioned file per step, compile on TradingView, journal-line diff vs previous build, no new `if` scopes, no new output slot, token cuts from presentation only. Token estimates assume the v3.8 base.

### Priority 1 — Critical

| Improvement | Existing problem | Proposed logic | Expected benefit | Trade-off | Validation |
|---|---|---|---|---|---|
| V-1 re-base | file is v3.6.1 under v3.8.1 name | `v3.8.txt` + D1–D4 cleanup → `v3.8.2` | restores 16 fixes | compile unverified for v3.8 | `grep` markers; diff = D1–D4 + stamp only |
| Z10 | BE stop = loss | loss only if `trdSL < trdEntry` (short mirror) | governance correct | +10 tokens | day with TP1→BE must not close the day |
| D1 | 4 engines no stop | FIX-A1 (in v3.8) | structural stops | +90 | SL distance diff for 4 signals |
| D2 | displaced BOS lost | FIX-A2 (in v3.8) | BOS count, regime, ★HP | +40, behaviour change | 10 manual BOS checks, regime distribution |
| D10 | neutral deadlock | FIX-A3 (in v3.8) | ordinary machine alive at turning points | +10 | arm count at `htfB == 0` |
| F-ALERT | FEM alert on rejected signal | `sigFEM and any` | alert ↔ label 1:1 | 0 | alert count == label count |

### Priority 2 — High

| ID | Fix | Tokens |
|---|---|---|
| Z1, Z2 | wrong-side sweep; PD acceptance spends level | +15 |
| Z6, D7 | FVG min height chart/HTF | +40 |
| Z11, D5, Z13 | stop anchors (deeper wick, LT raid wick, short spread) | +60 |
| Z9 | anchor touch scored once (expect −5 at stage 3; re-check `minScore`) | +5 |
| Z12 | clear `sbCeFillL` on mute | +5 |
| Z7, Z8 | ★HP tied to the leg; FEM reset on POI violation | +20 |
| D18, D20, D9 | pool grade 1; decay from shift over retest window; engine trigger = MSS/ext CHoCH | +70 |
| D8, D21 | reward clamp sees session/PD levels; grade-aware | +60 (signal count falls — measure) |
| D4, D6 | display ≠ detection; LT invalidation without body / veto cap | +25 |
| N-C | slip/reward kill → stage 3, risk-cap kill → 0 | +5 |
| D19 | `alert("LQCE\|L\|ce\|sl")` on stage-3 lock | +50 |

### Priority 3 — Medium

D11 (Asia killzone separate), D12 comment, D13 FEM CE close, D15/N-D governance count, D14/D16/D17 document, Z3/Z4/Z5 guards. ≈ +40.

### Priority 4 — Optional (strategy changes, separate test)

- **Model D continuation**: `shiftSrc` option "+ BOS with HTF trend" (`eBosUp and htfB > 0`), anchor = BOS-leg FVG. +80. This changes what the indicator is; test as its own population.
- Engine tier graded against the engine's own level (`liq` from the engine's sweep, not global). +120.
- `cFvgBDisp` for ordinary anchors (input). +15.
- Setup-quality grading string in the journal (pool confluence count, wick ratio). +40.
- Low-vol arm floor (`minArmQual` 3 when `ltLowVol`). +10.

### Token budget

P1 ≈ +150 (v3.8 already carries A1–A3), P2 ≈ +355, P3 ≈ +40. v3.6 hit 100,751/100,256; v3.7 cut 42 tooltips; v3.8 added ~140 untested. Cut sources in order: remaining tooltips (−100), `riskMoney`/`tp1Pct` label text (−40), `nonSbTp3` branch (−80), HTF CRT/TBS engine (−250, only after harness shows ~zero A-tier fires), IB + doji engines (−500, same condition), trendline engine (−300, last).

Bug fixes = P1 + P2 + P3. New features/strategy = P4 only.

---

## Report 8 — Test and Validation Plan

### 8.1 Harness (prerequisite)

No strategy twin exists (`find` → none; header 433–442 and 643–645 are stale). Two options:
1. **Journal export (now):** one TradingView alert on "Any alert() function call", webhook → sheet. `LQJRNL` carries side, source, tier, score, pool kind, raw grade, shift grade, window, regime, E/SL/TP2, day count. Outcomes come from the `[TRADE]` alerts (5517–5519) plus `trdExp`. This measures the indicator's own tracker (one trade at a time, pessimistic same-bar SL).
2. **Strategy twin (proper):** copy with `strategy()` + `strategy.entry` at `trdEntry`, `strategy.exit` with `trdSL`/`trdTP2` re-issued every bar, `close_all` on non-price flatten; `commission` + `slippage` set per symbol. Detection code must be byte-identical; regenerate after every change.

### 8.2 Scenarios

| # | Scenario | Expected | Check |
|---|---|---|---|
| T1 | Historical vs realtime | same signal set after replay (Bar Replay, 200 bars) | label count, journal lines equal |
| T2 | Pivot delay | `◆` sweep marks appear only on close; BOS chip `pivLen` bars after the pivot | visual |
| T3 | HTF timing | `sigHTbs*` on first LTF bar after HTF close; never inside | compare `hT` change bar |
| T4 | Z1 | accepted break then poke → no `◆` | replay case |
| T5 | Z10 | TP1 → BE → stop → `lossToday` unchanged, `cntSL` or `cntBE` | debug row |
| T6 | D1 | HTF TBS / doji / IB SL ≠ `min(low,low[1]) − pad` | label |
| T7 | D2 | weak close then displaced close → BOS chip on second bar | replay |
| T8 | D10 | `htfB == 0`, Follow: setup arms and shifts | debug Machine row |
| T9 | Duplicate | no same-bar long+short; one arm per `lastSslBar` | journal |
| T10 | Entry-bar stop | no SL hit on the entry bar for CE fills | tracker |
| T11 | Alerts ↔ labels | every `[SIGNAL]` alert has a label; FEM alert only with label | counts |
| T12 | Governance | 4th signal blocked; 2 real losses block; 2 BE stops do not | dashboard verdict |
| T13 | Display toggles | `showZones` off must not change signal count (after D4) | journal diff |
| T14 | Regression per step | journal diff vs previous build: only the intended rows change | automated diff |

Symbols/timeframes: EURUSD M5, XAUUSD M5, NAS100 M15, BTCUSDT M15; 3 months each; split London / NY / Asia; regime from the journal column.

### 8.3 Metrics (from the harness only)

Win rate, avg win / avg loss, expectancy per trade, profit factor, max drawdown, RR distribution (planned vs realised), trade frequency per day, all by symbol × TF × session × regime × source (SB/MC/LT/ENG) × tier. Costs: spread from the live panel (header 1049–1052), commission in `costTicks`, slippage 1 tick FX / 2 ticks index / 5 ticks XAU. Out-of-sample: calibrate `minScore`/`minRR` on months 1–2, verify on month 3.

### 8.4 What remains unverified

Compile status of this file and of v3.7/v3.8; every win-rate or accuracy statement; the four symbol profiles; `minScore` 50, `minRR` 1.5, `maxRiskAtr` 1.5 (header 646–649 says so itself).

---

## Report 9 — Final Verdict

| Category | Components |
|---|---|
| **Reliable** | HTF data idiom; closed-bar discipline; sweep latch and quality split; MSS binding; setup machine stages, clocks, invalidation reasons; CE limit at ask; confirmation past CE; two-stop fallback; viability gate; deferred-fill re-validation; SB-13 hierarchy; direction lock; drawing caps; journal line |
| **Requires correction** | stops for 4 engines (D1); break latch (D2); neutral arm gate (D10); loss accounting (Z10); sweep-from-wrong-side (Z1); PD spend (Z2); FVG min height (Z6/D7); deeper-wick ext (Z11); LT stop (D5); short spread (Z13); double-scored touch (Z9); stale CE flag (Z12); FEM alert; ★HP test (Z7); FEM reset (Z8); reward clamp (D8/D21); pool grade (D18); decay clock (D20); engine trigger (D9); display gating (D4); LT veto (D6); 18B stage reset (N-C) |
| **Requires redesign** | continuation path for the ordinary machine (Model D); engine tier grading against the engine's own level; LT long/short pattern asymmetry |
| **Cannot be verified** | compile of this file; any performance number; profile presets; strategy twin (absent) |
| **Recommended for next version** | `v3.8.2` = v3.8 + D1–D4 cleanup + Z10 + F-ALERT (P1), then P2 in three batches with journal diffs, then harness before any threshold change |

**Process note:** the first action is to stop treating `liqudity_trap_trading.v3.8.1.txt` as the latest code. It is not.
