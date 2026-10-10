# SMC / ICT Suite v8.4.0 — Review রিপোর্ট ও v8.4.1 পরিকল্পনা

তারিখ: 2026-10-09 · ফাইল: `SMC_v8.4.0.txt` → `SMC_v8.4.1.txt`

## সংক্ষেপে

- **Compile-level crash path পাওয়া যায়নি।** সব `request.security` call `[1]` offset + `lookahead_on` → history আর live একই (repaint নেই)। সব array loop guard করা। `max_bars_back = 500`-এর ভেতরে সব `[k]` index clamp করা (`f_xb`, `f_legOrigin` span ≤ 490, `obOff + 1` ≤ 490)।
- **Token budget-ই আসল ঝুঁকি।** v8.4.0 header নিজেই বলছে build 101,975 / 100,256-এ landed হয়ে M21-M25 কেটে নামানো হয়েছে। মানে এখন limit-এর খুব কাছে। **নতুন কিছু যোগ করলে আগে কাটতে হবে।** v8.4.0 header-এ পরের cut list দেওয়া আছে: M44 / M47 / M48 / M49 / M50 / M52 / M53 (সব default-OFF, tier 1 = rank 10)। Tier-1 module-এর score = 2 + confluence; min score 8 পেতে +6 confluence লাগে, যা কার্যত কখনো হয় না → এগুলো "dead weight"।
- **Trading logic-এ ৩টা HIGH আর ২টা MEDIUM সমস্যা পাওয়া গেছে** (নিচে)। তিনটা HIGH-ই v8.3.x / v8.4.0-এ যোগ হওয়া নতুন path-এ (R2 CHoCH rule, CONFIRMED entry, zone-based SL)।
- **v8.4.1-এ**: ৭টা module cut (≈ −2,000 token আনুমানিক) → ৫টা fix + ১টা ছোট ICT confluence (≈ +550 token আনুমানিক)। Net ≈ −1,400 → limit-এর নিচে থাকার কথা। **Local Pine compiler নেই — TradingView-এ paste করে compile দেখতে হবে।** স্বাধীন static review (diff) কোনো compile/runtime সমস্যা পায়নি।

## যা ঠিক আছে (যাচাই করা)

| বিষয় | ফল |
|---|---|
| `request.security` ×4 (HTF tuple, D, W) | `[1]` + `lookahead_on` → non-repainting |
| FVG detection | `barstate.isconfirmed` gated (C2) |
| Alerts (dynamic + 11 alertcondition) | সব `barstate.isconfirmed` gated |
| Session / killzone | America/New_York, Asia 20-00 · London 02-05 · NY 07-10 — ICT standard, DST TradingView সামলায় |
| PDH/PDL/PWH/PWL | forex daily boundary (17:00 NY) OANDA-তে ঠিক |
| Long/Short mirror | setup line, f_bid, f_stop, f_sig, f_conf — line-by-line মেলে |
| Score ladder | tier×2 + conf: tier 4 → 9 (একটা confluence-এই দেখায়), tier 3 → +1 লাগে, tier 2 → +3 — ঠিক gradient |
| Drawing budget | labels 230/500 · lines ~200/500 · boxes 100/500 — safe |
| UDT element cap | Ctx 254-এর কাছে, তাই Sx আলাদা — v8.4.1-এ Ctx থেকে ১৬টা field কমছে, margin বাড়ছে |

## পাওয়া সমস্যা

### HIGH

**H1. R2 CHoCH (LH/HL form) ভুল level record করে।** `f_structure`-এ `chUp = ... or (brkUp and loType == "HL")` — এই form-এ price `curHigh` (শেষ LH pivot) ভেঙেছে, `majorHigh` না। কিন্তু তিন জায়গায় `majorHigh` ব্যবহার হয়:
- `f_pend(sx, 1, 2, cx.majorHigh, ...)` — displacement ছাড়া HL-form CHoCH pending হয় `majorHigh`-তে (অনেক দূরে / na) → follow-through close কখনো আসে না → setup চুপচাপ হারিয়ে যায়।
- `sx.stBrkLvl := majorHigh` — পরের bar-এই `close < stBrkLvl` সত্য (majorHigh উপরে) → ভুয়া "failed follow-through" count → পরের একটা genuine fail হলেই RANGE।
- CHoCH line `ctx.majorHigh`-এ আঁকা হয় — chart-এ ভুল level।

**Fix:** `chUpMaj`/`chDnMaj` আলাদা করে `chUpLvl`/`chUpIdx` = আসলে যে level ভাঙল। নতুন `Struct.chLvl`/`chIdx` field; pending, stBrkLvl, leg-origin আর line সবাই সেটা পড়ে। **Side effect (ইচ্ছাকৃত):** HL-form-এ protected swing এখন HL (shift যে swing থেকে হলো), আগে LL হতো। ICT-তে HL-ই protected low।

**H2. CONFIRMED / MSS mode-এ §6.2 sweep-required zone কখনো fire করে না।** `zoneOkBull` প্রতি bar-এ `ft.sweptLow` চায়। Tap bar-এ sweep + reversal candle হলো, POI armed হলো। Confirm bar-এ (২-৮ bar পরে) `ft.sweptLow` false → `zoneOkBull` false → M08/M36/M37/M42/M39/M40/M45/M51/M54/M70/M73 সব চুপ। v8.4.0-এ CONFIRMED default হওয়ায় এটা এখন default path-এর bug।

**Fix:** `poiArmL` = POI armed **এবং** slot-এর zone সেই armed zone-ই (top/bottom মেলে) → sweep rule pass (tap bar-এ একবার pass করেছিল)। অন্য sweep-required zone-এ leak হয় না।

**H3. Zone-based SL reaction candle-এর wick ধরে না।** `f_stop`: `sl = zone.bottom − buf`। Reaction candle zone-এর নিচে wick দিলে (খুব common), SL বাজারের already-printed low-এর ভেতরে বসে। CONFIRMED mode-এ tap → confirm-এর মাঝের bar-গুলোর low-ও ধরা হয় না।

**Fix:** নতুন `setLoL` / `setHiS` = IMMEDIATE-এ এই candle-এর low/high, CONFIRMED-এ tap bar থেকে confirm bar পর্যন্ত `ta.lowest`/`ta.highest`। `f_stop(..., x)` → `min(zone.bottom, x) − buf`; major-swing আর fallback branch-ও `x` ধরে।

### MEDIUM

**M1. Min-risk floor tick-এ (default 20)।** EURUSD mintick 0.00001 → 20 tick = 0.2 pip; XAUUSD 0.01 → $0.20। Spread-sized stop আটকায় না। **Fix:** নতুন input `… or × ATR` (default 0.3) → `minR = max(ticks × mintick, 0.3 × ATR)`।

**M2. Alert message-এ R:R, TP2, grade, TP1 type নেই।** Telegram/webhook-এ trade নিতে এগুলো লাগে। **Fix:** `GRADE+score | Entry SL TP1 TP2 | risk · R | TF | HTF | TP1 type`।

### LOW / cosmetic

- M10 note সবসময় "(IMMEDIATE)" বলে, RETEST mode-এও।
- `f_pathBlock` comment বলে "zone or FVG", code শুধু zone দেখে। STRICT default-এ FVG যোগ করলে signal আরও কমবে — এখন ইচ্ছাকৃত বাদ, পরে WARN-level হিসেবে ভাবা যায়।
- Data-window label "M22/M71" — M22 নেই।

## Forex-expert দৃষ্টিতে যা যোগ হলো (ছোট)

**ICT true-day open (00:00 New York)।** Bullish দিনে midnight open-এর নিচে কেনা / bearish-এ উপরে বেচা — সবচেয়ে সস্তা আর repeatable ICT intraday filter। `f_conf`-এ +1 (gate না), panel-এর Session row-এ `>00:00 open` / `<00:00 open`। Input `Score NY midnight open`, default on, শুধু intraday।

## v8.4.1 পরিবর্তন তালিকা

| # | কী | কোথায় | Token |
|---|---|---|---|
| CUT | M44 M47 M48 M49 M50 M52 M53 + i_m53Alt + Ctx 16 field + Feat 3 field + M48/M52 arming + §M49 block + range-break block + `rngLr` | inputs, Ctx, Feat, orchestration, setups, f_bid ×14 | ≈ −2,000 |
| H1 | CHoCH level record | f_structure, Struct, drawing | ≈ +150 |
| H2 | poiArmL/S | zoneOkBull/Bear | ≈ +40 |
| H3 | setLoL/setHiS → f_stop(x) | global, f_stop, f_sig | ≈ +150 |
| M1 | i_minRiskA | input, f_sig | ≈ +40 |
| M2 | alert message | f_alertMsg | ≈ +60 |
| NEW | NY midnight open | input, global, f_conf, panel | ≈ +120 |

Token সংখ্যা আনুমানিক (Pine compiler comment গোনে না, inline-করা function body প্রতি call site-এ গোনে)। `f_stop` ২ জায়গায় inline হয়, `f_sig` ২ জায়গায় — তাই ওদের ভেতরের বদল ×2।

## TradingView-এ paste করার পর যা দেখবেন

1. Compile error এলে প্রথম লাইন নম্বর দিন — সবচেয়ে সম্ভাব্য: `math.max` ৩ argument (v6-এ valid), `ta.lowest(low, poiNL)` series length (v6-এ valid)।
2. Token error (`script is too large`) এলে পরের cut: M63 / M65 (default-OFF, tier 1 / 2), তারপর M03 M04 M06 M07 M11 M14 M29 (সব default-OFF tier 1)।
3. XAUUSD / EURUSD 5m-এ: CHoCH line এখন ভাঙা pivot-এ বসে কি না; CONFIRMED mode-এ `⚠SWEEP REQ` zone-এ signal আসে কি না; SL reaction wick-এর নিচে কি না।
