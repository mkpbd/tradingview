# 01 — Feature Inventory · LQ-SD-PA v3.7

ফাইল: `Liqudity/liqudity_trap_trading.v3.7.txt` (5596 লাইন, Pine v6, `indicator()`, overlay)
তারিখ: 2026-10-10 · পদ্ধতি: পুরো source লাইন-বাই-লাইন পড়া হয়েছে। নাম দেখে কিছু ধরা হয়নি; প্রতিটা feature-এর পেছনে logic আছে কি না যাচাই করা হয়েছে।

## 1. Architecture (module map)

| Module | লাইন | কাজ |
|---|---|---|
| 1 Inputs | 670–1115 | ~150 input, 4 symbol profile (`profIdx`) |
| 2 Constants | 1116–1180 | ATR-scaled constants, profile override |
| 3 Candle anatomy | 1182–1267 | ATR cap (FIX-Y4), spread (`hiA/loA`), pin/engulf, CISD, IFC |
| 4 Pivot engine | 1269–1369 | `pivLen`=5 internal pivot, EQH/EQL pools, trendline anchors |
| 4B Session clock | 1371–1479 | NY-time sessions, SB windows, news windows |
| 5 Liquidity | 1481–1868 | swing sweep (1-bar + multi-bar), quality grade, EQ/PD/PW/session pool stamps, `sslInPlay` |
| 6 Structure | 1870–2025 | protected-swing engine ×2 (internal `pivLen`, external `extPiv`=12), BOS/CHoCH, MSS |
| 7 HTF bias | 2027–2120 | EMA-50 bias + HTF structure (`request.security`), `htfB`, `biasOkL/S` |
| 8 Eng. memory | 2122–2139 | engineered-pool score memory |
| 9 HTF engines | 2141–2358 | auto HTF, HTF CRT/TBS, HTF FVG registry (3/side), ADR |
| 10 Dealing range | 2360–2453 | running-leg range, `pdPos`, OTE, SB range lock |
| 11 Regime | 2455–2527 | TRENDING / TRANSITION / RANGING / CHOP |
| 12 FVG registry | 2529–2687 | chart-TF FVG, IFVG flip, latest-FVG tracker |
| 13 Zones | 2689–3092 | S/D (FVG geometry) + OB companion + RB + IFVG, lifecycle, NEXT buy/sell |
| 14 Trigger engines | 3094–3269 | CRT, Turtle soup, trendline sweep, inside bar, doji |
| 15 FEM | 3271–3342 | HTF POI → LTF shift → locked FVG → retest |
| 15A Direction lock | 3344–3387 | machine + tracker state declared, `dirLock` |
| 16 Score / tier | 3389–3546 | 100-pt alignment score, C/B/A/A+ tier |
| 16B LT engine | 3549–3948 | 7 breakout-trap patterns, 2 state machines |
| 17 Master machine | 3950–4348 | IDLE→SWEPT→AT POI→SHIFTED→ACTIVE, ordinary + SB path |
| 18 Finalize | 4350–4537 | gates, tier floor, conflict hierarchy, LT veto |
| 18B Viability | 4539–4626 | plan price, stop select, slippage guard, risk cap, TP2 clamp, min RR |
| 19 Trade tracker | 4661–5002 | deferred fill, TP/SL/BE/trail, counters, governance |
| 20 Visuals | 5004–5347 | plots, labels, trade ladder, POI boxes, NEXT level |
| 21/22 Dashboard, Debug | 5349–5484 | tables |
| 23 Alerts | 5486–5596 | 30 alertcondition + alert() feed + journal line |

Output budget: plot 8 + plotchar 12 + bgcolor 3 + alertcondition 30 = 53/64। `request.security` 10 call। Compiled token: ~100k সীমার কাছে (prior builds CE10117)।

## 2. Feature inventory

| Feature | আছে? | Logic | সম্ভাব্য দুর্বলতা |
|---|---|---|---|
| BUY/SELL signal (11 pathway) | ✅ | `anyLong/anyShort` 4495–4496 | 4টা engine-এর নিজস্ব stop নেই (D1) |
| Master state machine | ✅ | 4052–4348 | default shift শুধু external CHoCH → continuation অসম্ভব; neutral-bias deadlock (D10) |
| SB (Silver Bullet) path | ✅ | tag + window clocks, CE limit | NY AM min quality 2 (default) |
| Market structure (int + ext) | ✅ | `f_structure` 1878–1920 | break latch body-blind (D2) |
| HTF structure bias | ✅ | `f_htfStruct` 2047–2110 | — |
| BOS / CHoCH / MSS | ✅ | 1950–1951, chips 2012–2025 | MSS default external-only |
| CISD / IFC | ✅ | 1228–1263 | execution confirmation only (ঠিক) |
| Swing sweep + grade 1–4 | ✅ | 1518–1550 | grade 2 সস্তা (`firm` OR 0.25 ATR pen) |
| Multi-bar sweep (reclaim ≤4 bar) | ✅ | 1518–1523 | — |
| EQH/EQL pools | ✅ | 1312–1323, 1617–1660 | শুধু consecutive pivot pair (D17) |
| PDH/PDL/PWH/PWL | ✅ | 1664–1703 | pool grade min 2 (D18); exchange-day boundary (D16) |
| Session H/L raids | ✅ | 1715–1830 | — |
| Supply/Demand zones | ✅ | 2898–2957 | detection `showZones` দিয়ে gated (D4) |
| Order block | ⚠️ আংশিক | 2926–2931 | শুধু bar[2]; "last opposing candle before displacement" খোঁজা হয় না |
| Rejection block | ✅ | 2959–2990 | `showRB` gated (D4) |
| Breaker / Mitigation flip | ✅ | `f_flipZone` 2757 | breaker test zone-specific নয় |
| FVG (3-candle, min height) | ✅ | 2546–2547 | — |
| IFVG | ✅ | 2598–2616 | — |
| HTF FVG POI (3/side) | ✅ | 2203–2296 | min height নেই (D7) |
| Premium / Discount + OTE | ✅ | 2391–2414 | running-leg range; pivot confirm হলে step করে (documented) |
| Dealing-range lock (SB) | ✅ | 2425–2453 | — |
| Regime | ✅ | 2491–2516 | — |
| Killzone filter | ✅ | 1392–1393 | Asia-কে killzone ধরা হয় (D11); default OFF |
| News windows | ⚠️ fixed clock | 919–921 | calendar নয় (documented) |
| Day-of-week mask | ✅ | 4387 | NY day vs exchange day mismatch |
| SL / TP / RR | ✅ | 18B + 19 | engine fallback stop (D1); opposing liquidity শুধু POI zone (D8) |
| Risk cap + min RR net of cost | ✅ | 4586–4609 | — |
| Spread model | ✅ | 1191–1193, fills | default 0 |
| Trade tracker (1 trade) | ✅ | 4707–4891 | mechanical counts, backtest নয় |
| Daily governance | ✅ | 4378–4385 | cancelled pending order-ও গোনা হয় (D15) |
| Alerts | ✅ | 5490–5596 | CE price-সহ pre-fill alert নেই (D19) |
| Journal line | ✅ | 5544–5558 | engine fill-এ `entryP` = close, fill নয় |
| Repaint protection | ✅ | `[1]`+`lookahead_on` ×10, `confirmed` guards | কোনো repaint পাওয়া যায়নি (রিপোর্ট 02) |
| Strategy twin / validation harness | ❌ **নেই** | header 450–459, 660–662 দাবি করে | repo-তে `liqudity_trap_strategy.txt` বা `scripts/mktwin.py` নেই (D3) |

## 3. Signal pathways (11 long + 11 short)

| # | Signal | জন্ম | Stop var | Fill |
|---|---|---|---|---|
| 1 | `sigMCLong` machine (ordinary) | 4219 | `slMCLong` 4231 | CE touch (limit) বা next open (confirmation) |
| 2 | `sigMCLong` + `sbSigLong` (SB) | 4219 | `slMCLong` | CE touch / proximal rejection, same bar |
| 3 | `sigFEMLong` | 3313 | `slFEMLong` | next open |
| 4 | `sigSDLong` zone 50% | 2859 | `slSDLong` | next open |
| 5 | `sigCRTLong` | 3111 | `slCRTLong` | next open |
| 6 | `sigTBSLong` | 3122 | `slTBSLong` | next open |
| 7 | `sigHCrtLong` HTF CRT | 2188 | **নেই** → fallback | next open |
| 8 | `sigHTbsLong` HTF TBS | 2190 | **নেই** → fallback | next open |
| 9 | `sigTLLong` trendline | 3158 | `slTLLong` | next open |
| 10 | `sig3Long` inside bar | 3215 | **নেই** → fallback | next open |
| 11 | `sig4Long` doji | 3265 | **নেই** → fallback | next open |
| 12 | `sigLTLong` trap | 3879 | `slLTLong` | next open |

সব pathway MODULE 18 (bias · lock · KZ · news · day · cooldown · chop · SB-only · governance · P/D · minScore · tier) এবং 18B (slip · risk cap · TP2 clamp · min RR) পার হয়। Engine candidate (3–12) `tierLong >= minRank` (default A) লাগে; machine (1–2) tier floor A, `f_mcTier` দিয়ে A+।

## 4. State / persistence inventory

- `var` scalars ~140; arrays: `zones` (Zone UDT), `bullFvgs/bearFvgs` (Fvg UDT), EQ arrays ×6, `sbBoxes`, HTF POI arrays (security scope)।
- Loops ১৪টা, সব descending বা `for in`; remove শুধু descending loop-এ → index-safe।
- Drawing objects: box/line/label 500 cap; last-bar redraw pattern (`barstate.islast`)।
- Alert: 30 `alertcondition` + 6 `alert()` call site।

## 5. ইনপুট default যা signal সংখ্যা ঠিক করে

`tierMode`=A, `minScore`=50, `minArmQual`=2, `shiftSrc`=MSS/ext CHoCH, `fastShift`=on, `mcEntryMode`=CE preferred, `mcReqPD`=on, `mcPdWaive`=off, `maxRiskAtr`=1.5 (reject), `minRR`=1.5, `oneDir`=on, `armNeedHtf`=on, `biasFilter`=60, `neutralMode`=Follow chart structure, `useRegime`=on, `useGov`=on (4 trades / 2 losses), `tradeDays`=Mon–Fri।
