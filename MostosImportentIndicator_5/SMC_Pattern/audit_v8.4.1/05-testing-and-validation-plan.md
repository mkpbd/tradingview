# 05 — Testing & Validation Plan · SMC / ICT Suite v8.4.1 → v8.5.0

তারিখ: 2026-10-10। **বর্তমান অবস্থা:** script `indicator()`; header (198) যে `SMC_Suite_v8.2.1_strategy.pine` twin-এর কথা বলে সেটা repo-তে নেই। তাই **কোনো win-rate / expectancy / drawdown সংখ্যা এই audit-এ নেই, এবং থাকতে পারে না।** Min score 8, A+ 11, minRR 2, maxRR 6, tier rank — সব live-chart review থেকে hand-set, একটাও measured নয়। Production script অপরিবর্তিত থাকবে; harness আলাদা ফাইল।

## 1. Metrics (Phase 7)

প্রতি signal: module, side, tier, score, grade, entry, SL, TP1/2/3, risk (ATR unit), rr, tgt (REAL/SYNTH/FIXED-R/FAR), gate (aligned/warn), session, pdPct, htfBias, trend, bar index, reject code (যদি না দেখায়)।
Outcome (bar-by-bar after entry, max 200 bar বা opposite signal): hit SL / hit TP1 / hit TP2 / timeout; MAE/MFE (R unit); bars to outcome।
Aggregate: N eligible / N shown / N filled (RETRACE) · win% (TP1) · avg R realized (TP1 exit, TP1→BE+TP2 variant) · expectancy/trade · profit factor · max DD (R) · max losing streak · false-signal rate (SL before +1R MFE) · entry delay (bars tap→signal) · missed (armed POI expired)। **Slice:** instrument, TF, module, tier, score bucket, session, HTF aligned/warn, pdPct bucket, regime (trend/range), year।

## 2. Harness — দুটো option (production অপরিবর্তিত)

### Option A — Strategy twin (TradingView Strategy Tester)
- `SMC_v8.5.0_strategy.txt`: একই source, `indicator(...)` → `strategy("...", overlay=true, pyramiding=0, default_qty_type=strategy.percent_of_equity, default_qty_value=1, commission_type=strategy.commission.percent, commission_value=0.0, slippage=2)`; শেষে:
  ```pine
  if barstate.isconfirmed and hasL
      strategy.entry("L", strategy.long, comment = sigL.name)
      strategy.exit("Lx", "L", stop = sigL.sl, limit = sigL.tp1)
  ```
  (short mirror)। RETRACE mode-এ `strategy.entry(..., limit = armedPx)` + cancel on expiry।
- Spread: `slippage` ticks দিয়ে approximate (EURUSD 1 pip = 10 tick ≈ 5+5 round trip); XAUUSD 20–30 tick; indices broker-specific।
- Risk: token — twin-ও 100k limit-এ; `d_*` drawing block আর panel/legend/alert cut করলে ~3–4k ফাঁকা হয়। Pine-এ strategy label/box চলে, কিন্তু twin-এ drawing অপ্রয়োজনীয়।
- Pro: TradingView-এই result, per-module filter `comment`-এ। Con: slice analysis কষ্টকর (export → spreadsheet)।

### Option B — Signal export + Python evaluator (recommended for slicing)
- Production script-এ **শুধু** 6টা `display.data_window` plot যোগ (প্রায় 0 token, কোনো logic বদল নেই): `sigDir`, `entry`, `sl`, `tp1`, `tp2`, `moduleCode` (M## → int), `scorePacked` (score×100 + tier×10 + gate)। অথবা আলাদা thin "exporter" copy।
- TradingView → Export chart data (CSV, bars + plots) → `scripts/smc_eval.py`: fill model (CLOSE = next bar open; limit = touch), spread/commission/slippage per symbol config, outcome scan, metrics + slices → markdown/CSV।
- Pro: ঠিক slicing, A/B diff, OOS split script-এ। Con: export per chart manual (5m: 20k bar ≈ 70 দিন per export; TradingView Premium deep history দরকার)।

**সুপারিশ:** B primary (slicing), A sanity cross-check (একই period-এ trade count/win% মিলতে হবে)।

## 3. Baseline protocol

1. v8.4.1 (unchanged) default input → export: EURUSD 5m, 15m · XAUUSD 5m, 15m · NAS100 5m · BTCUSDT 15m (killzone filter off) · GBPUSD 15m। Period: শেষ 12 মাস যতটা export-এ আসে।
2. Development set = প্রথম 60% (সময়ে), OOS = শেষ 40%। Forward = audit date-এর পরের data (v8.5.0 চলার 4–8 সপ্তাহ)।
3. Record: signal list + metrics per slice = **baseline table**।
4. Expected baseline sanity (indicator নিজেই বলে): reject code distribution — code 4 (R:R/path) আর 5 (score) ভাগ; code 1 (no candidate) majority।

## 4. Per-change A/B (04-এর order)

প্রতিটা change আলাদা input বা আলাদা build → একই export period → diff vs baseline:

| Change | যা মাপব | Pass criterion (dev set) | OOS check |
|---|---|---|---|
| D1 | M41/M46/M68 count, win%, R | count ↑; expectancy ≥ baseline module avg | same sign |
| D2 | sweep signal risk (ATR), SL-hit-by-1-tick rate | wick-stop rate ↓; expectancy ↑ or flat | same |
| D3 | M05/M15/M62/M72 count after CHoCH | count ↑; expectancy ≥ module avg | same |
| D4 | HTF flip bar list; counter-HTF signal count | flips earlier; WARN share ↓ | — |
| D5 | counter-context signal count/score | shown count ↑; expectancy of added signals ≥ 0 | same sign |
| D6 | STRONG BOS count, chochReal ratio | — (behaviour report) | — |
| W1 RETRACE | fill %, avg R, expectancy vs CLOSE | expectancy per **armed** setup ≥ CLOSE | same |
| W2 | continuation signals by pdPct | removed bucket expectancy < kept | same |
| W3 | M54 count, win% | fewer, better | same |
| W4 | FAR-target count/outcome | TP1-FAR hit rate reported | — |
| W5 | path-blocked count/outcome | blocked set expectancy < passed | same |
| W6 | trend-state share, CHoCH count | RANGE share ↓; signal count ± | — |
| W7 | qualified sweep/day; M10 count | fewer, expectancy ↑ | same |
| W8/W10 | M10/zone confirm variants | best variant by expectancy, not count | same |
| W9 + threshold | score vs win% monotonic? | if not monotonic, re-set `i_minScore` on dev, confirm OOS | required |

Rule: **একবারে একটা input**। Parameter tuning শুধু threshold-level (`i_minScore`, `i_minRR`), tier rank নয়, dev-set-এ; OOS-এ confirm না হলে revert।

## 5. Timeframe / instrument matrix

| Chart | HTF (Conservative) | Note |
|---|---|---|
| 5m | 1h | primary ICT intraday |
| 15m | 4h | swing-intraday |
| 1m | 15m | noise check (expect worse) |
| 1h | 4h | D4 impact largest |

Instruments: EURUSD, GBPUSD, XAUUSD, NAS100, BTC। Session filter: forex/cfd auto-on, crypto off। Regime split: `ft.inRange` / trend।

## 6. Regression checklist (প্রতিটা build)

- [ ] Compile (token count লিখে রাখা)
- [ ] 50%-mode FVG flags identical (D1 guard)
- [ ] Long/short mirror: same chart flipped (e.g., invert symbol) → signal count symmetric ±10%
- [ ] `reject code` distribution vs baseline
- [ ] Label count = alert count = `hasL/hasS` count (3589, 3819)
- [ ] No new `na` SL/TP (geometry gate 3420)
- [ ] Drawing budgets ≤ 500
- [ ] Realtime: 1 session live, label at close only, no disappearing labels

## 7. Forward test

v8.5.0 default on 2 chart (EURUSD 5m, XAUUSD 5m) 4–8 সপ্তাহ; alert → log; weekly metrics vs OOS। Decision: OOS আর forward দুটোই baseline-এর চেয়ে expectancy ≥ 0 এবং DD ≤ baseline হলে default হিসেবে রাখা; নয়তো input-gated।

## 8. যা claim করা যাবে না

- কোনো "institutional entry" / "90% accuracy"। Score ↑ = win% ↑ **প্রমাণ না হওয়া পর্যন্ত** grade শুধু ordering, probability নয় (panel/tooltip-এ এই ভাষা রাখা)।
- Label-এর R:R = realized R নয়; TP1 REAL মানে level আছে, hit হবে তা নয়।
