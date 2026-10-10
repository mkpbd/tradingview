# 04 — Improvement Roadmap · v3.7 → v3.8

তারিখ: 2026-10-10। Production script-এ কোনো change করা হয়নি। Approve হলে **নতুন ফাইল** `liqudity_trap_trading.v3.8.txt`-এ incremental patch। Token ceiling ~100k: প্রতিটা item-এর খরচ আর cut-source দেওয়া।

## P0 — Critical
**কিছু নেই।** Repaint নেই, direction reversal নেই, state corruption নেই, runtime-crash path নেই।

## P1 — High

| ID | সমস্যা | Fix | Token | Validation |
|---|---|---|---|---|
| D1 | HTF CRT/TBS, IB, Doji stop নেই (4558–4573) | `slHCrt/slHTbs/sl3/sl4` + chain; HTF tuple-এ `low[1]`,`high[1]` export | +90 | এই 4 signal-এর SL distance diff; বাকি unchanged |
| D2 | Body-blind break latch (1863–1868, 1941–1944) | দ্বিতীয় latch `resBosDone/supBosDone` (displaced) → `f_structure` input; `brokeUp/Dn` sweep logic unchanged | +40 | BOS/CHoCH chip count v3.7 vs v3.8; regime distribution; LT-1 arm count |
| D3 | Harness নেই | রিপোর্ট 05 (indicator অপরিবর্তিত) | 0 | — |
| D10 | Neutral deadlock (2119/4115) | arm gate: `htfB >= 0` যখন neutral+Follow; final gate অপরিবর্তিত | +10 | neutral bar-এ arm count; signal count |

## P2 — Medium

| ID | সমস্যা | Fix | Token |
|---|---|---|---|
| D18 | Pool sweep grade floor 2 (1589) | `qPoolLo` → 1 যদি `pen < 0.125 ATR and not firm` | +30 |
| D19 | CE pre-fill alert | stage-3 lock edge → `alert("LQCE\|L\|ce\|sl")` | +50 |
| D20 | Trigger decay ≠ retest clock | `useAnchL` হলে decay base = `suLBar`, window `sbRetWL`, floor 0.5 | +25 |
| D8 | Opposing liquidity শুধু POI | 18B clamp-এ session H/L + PDH/PWH (reuse `f_nearAbove`) | +40 |
| D21 | TP2 clamp grade-blind | শুধু `score >= 3` বা HTF clamp করে; input `tpClampMin` | +20 |
| D4 | `showZones/OB/RB` detection gate | display → transparency only | +20 |
| D5 | LT stop wick cover | `_ltSHiMax/_ltLLoMin` since arm | +30 |
| D6 | LT veto 25 bar | invalidation body শর্ত বাদ, বা veto cap | +5 |
| D7 | HTF FVG min height | `f_htfPoi`-এ HTF ATR gate | +20 |
| D9 | Engine trigger = internal CHoCH/CISD | `hasTrig` → MSS / ext CHoCH (`lastEChUpBar` reuse) | +15 |
| N1 | Ordinary CE anchor incidental FVG | `sbFvgOkL`-এর মতো `cFvgBDisp` ordinary path-এও (input `mcFvgDisp`) | +15 |

## P3 — Enhancement / doc

| ID | কাজ | Token |
|---|---|---|
| D12 | SB-11 comment ঠিক | −20 |
| D13 | FEM exec CE-past close | +15 |
| D11 | Asia killzone আলাদা | +10 |
| D15 | cancelled pending → `trdToday` ফেরত | +5 |
| D22 | idle double-touch | +5 |
| D14, D16, D17 | document only | 0 |
| D-OB | OB = last opposing candle in ≤3 bars before displacement | +60 (v3.9) |
| Model D | continuation path: sweep of pullback low + BOS shift (`shiftSrc` option "+ BOS in HTF trend") | +80 (v3.9, separate test) |

## Token budget (v3.8 সব P1 + P2): ≈ +430

**Cut sources (default-OFF বা redundant, detection অপরিবর্তিত):**
1. `useHtfCrt` HTF CRT/TBS engine পুরো সরানো (D1 fix-এর বদলে): −250। Tier-A pass প্রায় শূন্য, 1-LTF-bar late। **Recommended** — কিন্তু measure করে।
2. Inside-bar + doji engine সরানো: −500। D1-এ stop নেই, continuation chase, tier A প্রায় অসম্ভব। **Decision: harness run-এর পর।**
3. `nonSbTp3` runner branch (default OFF): −80।
4. `riskMoney`/`tp1Pct` label text: −40।
5. বাকি tooltips: −100।
6. `tlSweepEnt` trendline engine: −300 (low-quality, 5-bar line) — শেষ option।

নিয়ম: cut-এর আগে harness-এ ওই engine-এর fired-count আর outcome দেখা। শূন্য/negative হলে কাটা justified।

## Order of work (approve হলে)

1. v3.8-a: D1 (stop vars) + D2 (second latch) + D10 → compile check → signal diff।
2. v3.8-b: D18, D19, D20, D9, N1 → diff।
3. v3.8-c: D8, D21, D4, D5, D6, D7 → diff।
4. v3.8-d: P3 doc/cuts।
প্রতিটা ধাপে v3.7 baseline-এর সাথে journal-line diff (05 §4)।

## Regression tests (প্রতি ধাপে)

- EURUSD M5, XAUUSD M5, NAS100 M15, BTCUSDT M15 — 3 মাস।
- Compare: signal count/side, tier distribution, SL distance median, reject reasons (`planKill`), stage-expiry reasons।
- Invariants: কোনো same-bar long+short; কোনো entry-bar stop hit; `[SIGNAL]` alert ↔ label 1:1; A+ count ≤ A count population।
- D2-এর জন্য আলাদা: BOS/CHoCH count বাড়বে — প্রতিটা নতুন BOS manual check (10 sample)।

## যা করা হবে না

- Pine version বদল নেই; `indicator()` থাকবে; নতুন output slot নেই।
- Confluence বাড়াতে নতুন indicator নেই।
- Win-rate বা accuracy-র কোনো দাবি নেই যতক্ষণ 05-এর protocol না চলে।
