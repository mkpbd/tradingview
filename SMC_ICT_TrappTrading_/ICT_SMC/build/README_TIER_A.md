# SMC + ICT Engine — Tier A (Phase 1–16)

File: `SMC_ICT_Engine.pine` — Pine Script **v6**, single `indicator()`.

## Phase → code map

| Phase | Section in file | কী আছে |
|---|---|---|
| 1 Swing Structure | `05 LAYER 1` | `ta.pivothigh/low(swingLen)` → HH/HL/LH/LL, cap 100 |
| 2 Liquidity | `05 LAYER 1` | BSL/SSL/EQH/EQL/PDH/PDL/PWH/PWL, ATR-normalized EQ tolerance, cluster strength, cap 50 |
| 3 BOS / CHoCH | `06 LAYER 2` | Close/Wick mode, `trendDir` flip, level consumed flag |
| 4 Displacement | `06 LAYER 2` | ATR size **এবং** body ratio — দুইটাই লাগে |
| 5 Sweep + MSS | `06 LAYER 2` | penetrate + close-back + rejection wick; MSS = displacement + internal break |
| 6 FVG + lifecycle | `06 LAYER 2` | middle candle displacement বাধ্যতামূলক, min gap = ATR×, NEW→ACTIVE→TOUCHED→MITIGATED→FILLED |
| 7 OB / BB / IFVG | `06 LAYER 2` | OB শুধু displacement+MSS validate হলে; FILLED হলে inverse zone (IFVG/BB) |
| 8 Premium/Discount/OTE | `05 LAYER 1` | dealing range = শেষ confirmed swing H/L, EQ, OTE 0.618–0.786 |
| 9 HTF Context | `05 LAYER 1` | `request.security(... [1], lookahead_off)` + auto TF map |
| 10 Session / Kill Zone | `05 LAYER 1` | timezone input, Asia/London/NY |
| 11 Entry State Machine | `07 LAYER 3` | IDLE→CONTEXT→SWEPT→DISP→MSS→POI→RETRACE→ENTRY→TRADE, প্রতি step-এ timeout |
| 12 Score + SL/TP/RR | `07 LAYER 3` | score v1 (max 12, contradiction −3), SL = sweep ± ATR buffer, TP = next liquidity, `rr < minRR` → no trade |
| 13 Visuals + Settings | `09 DRAWING` | ১০টা input group, প্রতি module আলাদা toggle |
| 14 Alerts | `11 ALERTS` | trade / BOS / CHoCH / sweep / zone, `freq_once_per_bar_close` |
| 15 Repaint audit | পুরো ফাইল | নিচে checklist |
| 16 Integration tests | — | নিচে matrix |

## Hard rules যা code-এ enforce করা আছে

- Signal শুধু **একটাই দরজা** — Layer 3 state machine। কোনো module একা signal দেয় না।
- সব state transition `barstate.isconfirmed`-এ।
- এক setup = এক signal (`signalEmitted`), POI `consumed := true`।
- একই bar-এ LONG + SHORT trigger → **দুইটাই reject**।
- Array cap: swings 100 · liquidity 50 · zones 100। মোছার **আগে** `box.delete` / `line.delete`।
- সব array loop backward, এবং size>0 guard (`for i = size-1 to 0` size 0 হলে index −1 → runtime error, তাই guard)।
- সব division `math.max(x, syminfo.mintick)` দিয়ে সুরক্ষিত।
- `request.security` মোট ৩টা, সবগুলোতে `[1]` + `lookahead_off`।

## Repaint checklist (Phase 15)

- [ ] Chart reload (F5) → history হুবহু এক
- [ ] Realtime signal → bar close → signal টিকল
- [ ] HTF বদলে ফেরত → signal অপরিবর্তিত
- [ ] Bar replay → একই signal একই জায়গায়
- [ ] শেষ `swingLen` bar-এ swing label নেই (এটা সঠিক)

## Integration test matrix (Phase 16)

| # | Test | প্রত্যাশিত |
|---|---|---|
| 1 | SSL sweep → disp → MSS → FVG → retrace | ঠিক ১টা LONG |
| 2 | BSL sweep → disp → MSS → FVG → retrace | ঠিক ১টা SHORT |
| 3 | Wick ভাঙল, ভেতরে close | Close mode-এ BOS নেই |
| 4 | Sweep আছে, displacement নেই | trade নেই (10 bar পরে INVALIDATED) |
| 5 | RR < 1.5 | trade নেই |
| 6 | একই FVG-তে ৫ touch | ১টা signal |
| 7 | Reload / realtime তুলনা | consistent |
| 8 | Weekend gap | swing ভাঙে না |
| 9 | একই bar-এ LONG + SHORT | দুইটাই reject |
| 10 | 5000 bar history | hang নেই, object error নেই |

**Sanity:** 15M chart, ১ মাস → ১০–৪০টা signal। ২০০+ = logic ঢিলা। ০ = কোনো transition আটকে (Debug table চালু করো: Visuals → Show Debug)।

## Tuning যদি signal ০ হয়

1. `Require HTF Alignment` off করো — HTF bias `NEUTRAL` হলে সব block হয়।
2. `Min Score to Trade` 7 → 5।
3. `Min RR` 1.5 → 1.2।
4. `Sweep -> MSS timeout` 10 → 15।
5. Debug table-এ LONG/SHORT state দেখো — কোন step-এ আটকে আছে।

## পরের ধাপ

Tier B (Phase 17–34) — Trendline engine, CISD, SMT, AMD/PO3, Trap, BPR, Silver Bullet, Score v2।
Tier B-র প্রতিটা module-এর toggle **default `false`** হবে (plan-এর নিয়ম ২)।
