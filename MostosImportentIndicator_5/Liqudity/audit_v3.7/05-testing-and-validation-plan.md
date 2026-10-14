# 05 — Testing & Validation Plan

তারিখ: 2026-10-10। Script `indicator()`; label দেখে performance দাবি করা যায় না। নিচের harness **production ফাইল না বদলে** চলে।

## 1. Harness: strategy twin (regenerate, hand-edit নয়)

Repo-তে twin নেই (D3)। বানানোর নিয়ম:

1. `scripts/mktwin.py` (নতুন): v3.x ফাইল পড়ে →
   - লাইন 667 `indicator(...)` → `strategy("LQ-SD-PA twin", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1, commission_type=strategy.commission.cash_per_contract, commission_value=<input>, slippage=<ticks>, process_orders_on_close=true, calc_on_every_tick=false)`
   - MODULE 19-এর শেষে (লাইন ~5002-এর পরে) module 19S append:
     ```
     // 19S — broker emulator mirror of the tracker
     if trackNew and not deferFill
         strategy.entry(anyLong ? "L" : "S", anyLong ? strategy.long : strategy.short, limit = entryP)
     if trackNew and deferFill
         strategy.entry(anyLong ? "L" : "S", anyLong ? strategy.long : strategy.short)   // next open
     if trdDir != 0
         strategy.exit("x1", from_entry = trdDir == 1 ? "L" : "S", stop = trdSL, limit = trdTP1, qty_percent = 50)
         strategy.exit("x2", from_entry = trdDir == 1 ? "L" : "S", stop = trdSL, limit = trdIsSb or nonSbTp3 ? trdTP3 : trdTP2)
     if trdDir == 0 and strategy.position_size != 0
         strategy.close_all("flat")
     ```
   - Detection code byte-identical (diff দিয়ে প্রমাণ)।
2. Output: `Liqudity/twin/liqudity_trap_strategy.v3.x.txt`। প্রতিটা indicator change-এর পর re-run।
3. Twin **সংখ্যার জন্য**, chart/alert-এর জন্য production ফাইল।

সীমাবদ্ধতা: `process_orders_on_close` + CE limit = emulator intrabar touch ধরে, indicator bar-close ধরে — ছোট mismatch; journal diff-এ দেখা যাবে।

## 2. বিকল্প / পরিপূরক: journal-line export

Production ফাইল-ই `LQJRNL|…` alert() লাইন দেয় (5544)। "Any alert() function call" → webhook/CSV → বাইরে R-multiple হিসাব। Entry/SL/TP2 আছে; outcome নেই — twin বা manual mark লাগে। Strategy Tester-এর চেয়ে কম নির্ভরযোগ্য, কিন্তু v3.7 ↔ v3.8 **signal diff**-এর জন্য যথেষ্ট।

## 3. Metrics (প্রতি run)

- Eligible setups (stage ≥ 3 reached) · executed trades · reject reasons histogram (`planKill`, `gateKill`, `suLReason`)।
- Win rate · avg R · realized R/trade · expectancy · profit factor · max DD (R) · longest losing streak।
- False-signal rate: SL before TP1 / total।
- Entry delay: shift bar → entry bar (bars) distribution।
- Missed: stage 3 expired without entry।
- Breakdown: symbol × TF × session (Asia/London/NY/SB) × regime × pathway (MC/SB/ENG/LT) × tier × score bucket।

## 4. Protocol

1. **Baseline:** v3.7 defaults, Manual profile, spread/cost per symbol table (REVIEW_v3.6_BN.md §Symbol)।
2. **Data split:** 2025-01 → 2025-09 in-sample; 2025-10 → 2026-03 out-of-sample (TradingView deep backtest, M5 সীমা মাথায়)।
3. **Instruments:** EURUSD, GBPUSD, XAUUSD (M5); NAS100, BTCUSDT (M15)।
4. **Costs:** spread = live London/NY quote ÷ tick; commission broker-specific; slippage 1 tick FX / 2 ticks XAU-index।
5. **One change at a time:** v3.8-a → b → c; প্রতিটা vs baseline।
6. **No curve fit:** `minScore`, `minRR`, `maxRiskAtr`, `sbQualAM` শুধু in-sample-এ tune; OOS-এ freeze।
7. **Forward:** 4 সপ্তাহ paper, alert-driven, journal CSV।
8. **Report:** 06-results.md — সংখ্যা, নমুনা trade (bar time + reason), যা কাজ করেনি।

## 5. Regression (signal diff)

- দুই version একই chart, একই bars → journal line set A, B।
- A−B (হারানো signal), B−A (নতুন signal) — প্রতিটা manual review: কারণ কি documented fix?
- Invariants (04 §Regression)।

## 6. Score calibration (Phase 8)

Harness চললে: প্রতিটা trade-এর 5 component (C/L/P/T/E) + outcome → bucket-wise expectancy। যদি score ↑ ⇏ expectancy ↑, threshold-কে গেট না রেখে শুধু display রাখা। Correlation দেখা: MSS↔sweep-in-play, raw≥3↔SB quality, conf↔strongRej। প্রস্তাবিত 6-factor (সবই আলাদা মাপা): direction context · liquidity event · structural shift · entry location (P/D + anchor) · stop validity (structure behind) · room (RR net to next pool) · session। যতক্ষণ test নেই, বর্তমান score **narrative alignment** হিসেবেই থাকবে (header 462 ঠিক বলে)।

## 7. Compile check (v3.7 এখনো unverified)

TradingView Pine Editor-এ paste → প্রথম লাইনে `BUILD v3.7-b1` → Add to chart। CE10117 হলে token সংখ্যা জানান। Suspect লাইন: 2038, 1520, 2158।
