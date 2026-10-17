# SMC / ICT Suite v8.5.2 — ব্যবহার নির্দেশিকা (User Guide)

> কার জন্য: যিনি TradingView-এ 5m / 15m চার্টে ICT / Smart Money স্টাইলে forex, gold, index, crypto ট্রেড করেন।
> এক লাইনে: indicator **লিকুইডিটি → structure → POI → confirmation** এই ক্রম খুঁজে entry দেয়; আপনি শুধু Panel + Label পড়বেন আর risk ম্যানেজ করবেন।

---

## ১. সেটআপ (২ মিনিট)

1. TradingView → Pine Editor → `SMC_v8.5.2.txt` paste → **Add to chart**।
2. Chart timeframe **5m** (1m–15m কাজ করে; 5m সবচেয়ে টিউন করা)।
3. Settings কিছু না বদলেই শুরু করুন। Default = review-চার্টে টিউন করা।
4. যদি 100k token error / "Calculation timed out" আসে → settings → `10 · Show` → **Info panel** off করে আবার চেষ্টা; তারপর জানান।

**Forex / Gold / Index (OANDA, FOREX.com):** killzone filter নিজে থেকেই on থাকে — শুধু Asia 20:00–00:00, London 02:00–05:00, NY 07:00–10:00 (New York সময়) এ signal আসবে।
**Crypto / Stocks:** 24h signal।

---

## ২. চার্টে কী কী দেখবেন

| চার্টে যা দেখছেন | মানে | আপনি কী করবেন |
|---|---|---|
| `▲▲ M74 A+13 · 6.4R` (সবুজ label, নিচে) | **LONG signal**। Module M74, Grade A+, score 13, TP1 = 6.4R | Label-এ hover → tooltip-এ entry / SL / TP1-3 / note। Trade line নীল = entry, লাল dashed = SL, সবুজ dashed = TP |
| `▼▼ M10 A9 · 2.1R` (লাল label, উপরে) | **SHORT signal** | একই |
| `· M69 B8 · 2.3R` | Grade **B** (score 8 = minimum)। দুর্বল | Skip করতে পারেন, অথবা half size |
| ধূসর (grey) signal label | **⚠ counter** — HTF বা LTF trend-এর বিপরীতে | Score −1 ইতিমধ্যে কাটা। সাবধান |
| `⏳ M74 limit @ 82072.12` (নীল label) | **Pending limit order**। এখনও trade নয়। Price এই দামে এলে signal print হবে | Broker-এ limit বসাতে পারেন: entry = label দাম, SL/TP tooltip-এ (fill হলে label আসবে) |
| `CHoCH✕▲`, `BOS▲ ·2FVG` | Structure event। `✕` = আগে sweep ছিল, `·2FVG` = displacement-এ ২টা FVG | Context; trade না |
| `SWEEP✕ EQL` | লিকুইডিটি sweep | Reversal context |
| Box `OB▲ T1 IDM✓ ★★` | Demand zone। `IDM✓` = inducement sweep হয়েছে, `★★` = near-miss then sweep (strongest) | এখানে reaction আশা করুন |
| Box `RJB▲ ?` | Rejection block, **unconfirmed** (BOS অপেক্ষায়) | শুধু M10 sweep reversal এখানে trade করে |
| Box `RCB▼ ⚠SWEEP REQ` | Supply, ২+ বার touched → sweep ছাড়া direct reversal নিষেধ | Sweep + confirmation অপেক্ষা |
| Dashed line `POOL·EQL`, `PDH`, `SESH` | লিকুইডিটি pool / previous day high / Asia high | Target বা sweep candidate |
| Background হালকা সবুজ / লাল | HTF bias BULL / BEAR | সবসময় এই দিকে ট্রেড প্রাধান্য |

---

## ৩. Panel (নিচে-ডানে) — প্রতিটি সারি কীভাবে পড়বেন

স্ক্রিনশট (BTCUSDT 5m) ধরে:

| সারি | স্ক্রিনশটে | পড়ার নিয়ম |
|---|---|---|
| **Chart / HTF** | `5 → 60` | 5m চার্ট, bias 1h থেকে |
| **LTF structure** | `BULLISH` | 5m structure |
| **HTF bias** | `BEAR ⚠` | 1h bias। ⚠ = LTF আর HTF মিলছে না (pullback চলছে অথবা reversal হচ্ছে) |
| **Regime** | `BULLISH` | trend / range |
| **Last event** | `SWEEP BSL · 8b ago` | শেষ structure/liquidity event, কত bar আগে |
| **Move phase** | `RETRACEMENT` | IMPULSIVE = chase করবেন না; RETRACEMENT = POI-তে entry খুঁজুন |
| **Active zone** | `—` | Price এখন কোন zone-এ। `Bull OB (fresh)` হলে long entry প্রস্তুতি |
| **Arrival** | `—` | Zone-এ price **কীভাবে** এল। `WEAK ✅` = ভালো (corrective pullback)। `STRONG ❌` = displacement দিয়ে এসেছে, zone ভাঙার সম্ভাবনা, reversal module বন্ধ |
| **Nearest BSL / SSL** | `81796 / 81561` | উপরে/নিচে পরবর্তী লিকুইডিটি। Target এবং "আগে কোনটা sweep হবে" |
| **4-factor** | `watch ✅❌❌❌` | HTF · LTF trend · departure/arrival · liquidity। `watch` = signal নেই, HTF দিকের live চেক। ৩–৪ ✅ = A setup |
| **Signal** | `—` | এই bar-এর best signal, score, grade |
| **PD array** | `96% of leg · premium · 60 45%` | 5m leg-এর 96% = premium (sell side) কিন্তু 1h leg-এর 45% = discount। দুটো মিললে ভালো; না মিললে ছোট TF premium-এ long = late |
| **Session** | `— (outside killzones) · <00:00 open` | killzone বাইরে। `<00:00 open` = price NY midnight open-এর নিচে (long bias point) |
| **TP1 / gate** | `REAL · HTF aligned` / `⚠ LTF counter (pullback)` | TP1 REAL = আসল zone/FVG/liquidity। FAR = Max R:R-এর বাইরে। gate কোন half disagree করছে |
| **Watch** | `SHORT · RJB▼ 82000–82094 · sweep BSL 81796 first · CONFIRMED` | **পরবর্তী HTF-aligned entry plan**: দিক · POI · আগে কোন liquidity sweep হবে · trigger mode। Signal না থাকলেও এটা পড়ুন |

---

## ৪. একটা signal এলে ৬০ সেকেন্ডে সিদ্ধান্ত

1. **Label রং**: সবুজ/লাল = aligned; ধূসর = counter → size অর্ধেক বা skip।
2. **Grade**: A+ (≥11) পুরো size · A (≥9) normal · B (8) skip/half।
3. **Tooltip note পড়ুন** (label-এ hover):
   - `⚠vs HTF` → HTF bias-এর বিপরীত। High risk।
   - `⚠ LTF counter (pullback)` → HTF ঠিক আছে, শুধু 5m pullback। **এটা স্বাভাবিক**, ভালো entry প্রায়ই এভাবেই আসে।
   - `INCOMPLETE (no POI)` → zone/FVG ছাড়া entry। M74-এ এটা দেখা যায় কারণ limit FVG-তে, note close-এ মাপা (score-এ compensate করা আছে)।
   - `⚠ TP1 = FAR` → target 6R-এর বেশি দূরে। TP1 আংশিক নিন, বাকি TP2/TP3।
   - `⚠ opposing zone/FVG between entry and TP1` → path-এ বাধা। STRICT mode-এ এটা আসবে না।
4. **Panel 4-factor**: ৩+ ✅ চাই। `dep/arr ❌` মানে arrival strong → zone fail হতে পারে।
5. **PD array**: long হলে discount (<50%) চাই, অন্তত HTF leg-এ।
6. **Entry / SL / TP**: tooltip থেকে। SL কখনো টাইট করবেন না — SL zone + sweep wick-এর বাইরে বসানো।

---

## ৫. ⏳ Pending limit (M74 + RETRACE) কীভাবে ব্যবহার করবেন

স্ক্রিনশটে অনেকগুলো `⏳ M74 limit @ …` — এগুলো **order, trade নয়**।

- **কখন আসে:** real CHoCH বা strong BOS (FVG সহ), HTF দিকে। Indicator leg-এর FVG-র মাঝখানে (CE) limit বসায়; FVG না থাকলে leg-এর 50%।
- **কী করবেন:** broker-এ limit order: entry = label দাম। SL = leg origin-এর নিচে/উপরে (fill হলে tooltip-এ exact)। Window: 20 bar (settings `M74: limit valid`)। Fill না হলে বাতিল।
- **Fill হলে:** `▲▲ M74 A+13 · 6.4R` label + trade lines + alert আসবে।
- **Cancel হয়:** 20 bar পার হলে, অথবা close SL-এর ওপারে গেলে।
- **একসাথে একটা:** একদিকে একটা limit pending থাকলে নতুন M74 আসবে না।
- স্ক্রিনশটে `M74 A+11 · 7.8R`, `M74 A+13 · 6.4R` = fill হওয়া limit, দুটোই কাজ করেছে।

**Tip:** `Entry price = RETRACE` করলে সব module-ই limit হিসেবে arm হবে (risk ছোট, R:R বড়, কিন্তু কিছু fill হবে না)। Default CLOSE-এ শুধু বড় candle (≥1.5 ATR) হলে auto-limit।

---

## ৬. Module গুলো এক নজরে (কোনটা কী)

| Tier | Module | কী | কখন বিশ্বাস করবেন |
|---|---|---|---|
| 4 | **M37** Inducement block | EQL sweep → OB tap → reversal | সবচেয়ে ভালো |
| 4 | **M41** Sweep + FVG | sweep → strong move + FVG → retrace | ICT classic |
| 4 | **M42** HP S&D | OB, strong departure, 50% tap, weak arrival | ★★ হলে A+ |
| 4 | **M45** Sweep → CHoCH → breaker | reversal sequence | tier 4 শুধু real CHoCH হলে |
| 4 | **M54** Smart S&D trap | demand reject → stop hunt → BOS → retrace | |
| 4 | **M68** HTF sweep → LTF CHoCH | 1h sweep + 5m shift | |
| 3-4 | **M74** MSS → FVG retrace | CHoCH/BOS → leg FVG-তে limit | tier 4 যদি আগে sweep |
| 3-4 | **M39** Reclaimed block | CHoCH origin candle retest | tier 4 sweep→real CHoCH |
| 3 | **M09, M33, M36, M46, M51, M73** | pin+liquidity, zone flip, OB weak retrace, CISD, smart BOS, propulsion | A+ হতে confluence লাগবে |
| 2 | **M10** Sweep reversal | POOL/PD/PW/SES sweep + close back | PD/PW/SES হলে tier 3 |
| 2 | M01, M02, M05, M08, M15, M40, M58, M62, M69, M70, M72 | pattern / break / trap | শুধু ভালো confluence-এ |

Score = tier × 2 + confluence (HTF, trend, zone quality, liquidity target, sweep, discount/OTE, HTF FVG, HTF discount, session)।

---

## ৭. দৈনিক workflow (operator style)

1. **Session শুরুতে** (London 02:00 / NY 07:00 NY time): Panel পড়ুন — HTF bias, PD array (দুই leg), Nearest BSL/SSL, **Watch** row।
2. Watch row যা বলে (যেমন `LONG · OB▲ 4169–4173 · sweep SSL 4172.7 first · CONFIRMED`) → সেই zone-এ alert বসান, sweep অপেক্ষা।
3. Price zone-এ এলে: Active zone + Arrival দেখুন। `WEAK ✅` হলে প্রস্তুত।
4. Signal label বা ⏳ limit এলে §৪ checklist।
5. Impulsive candle-এ **chase করবেন না** — Move phase IMPULSIVE + PD premium হলে M74 limit অপেক্ষা।
6. Trade নেওয়ার পর: TP1-এ অর্ধেক, SL breakeven, বাকি TP2 (liquidity)।

---

## ৮. Alerts

Alert → Condition: `SMC Suite` →
- `Setup: LONG signal` / `SHORT signal` / `Any A+ signal` — webhook message-এ entry, SL, TP1, TP2, risk, R:R, grade সব থাকে।
- `Warning: Counter-HTF signal`
- Event: BOS, real CHoCH, CISD, Sweep, HP OB, Propulsion, OB 50% tapped।
Pending ⏳ limit fill হলে normal LONG/SHORT alert-ই আসে।

---

## ৯. দরকারি settings (কখন বদলাবেন)

| Setting | Default | কখন বদলাবেন |
|---|---|---|
| `14 · Trade` → Entry price | CLOSE | **RETRACE** = সব entry limit-এ (কম risk, কম fill) |
| Auto-RETRACE when candle ≥ × ATR | 1.5 | 0 = off; 1.0 = আরও আগ্রাসী limit |
| Min score to show | 8 | বেশি signal চাইলে 7; কম কিন্তু ভালো চাইলে 9 |
| Min R:R / Max R:R | 2 / 6 | scalp হলে 1.5 / 4 |
| `7 · HTF` → HTF pairing | Conservative (5m→1h) | Aggressive = 5m→30m, দ্রুত bias flip |
| HTF bias gate | WARN | STRICT = counter signal একেবারে বন্ধ |
| LTF-only trend flip = pullback | on | off = v8.5.1 আচরণ (pullback-এ continuation বন্ধ) |
| `5 · Liquidity` → Sweep arms setups | Major only | "Include external" = 50-bar extreme sweep-ও গণনা (বেশি M41/M45) |
| Internal sweep qualifies at zone (E-3) | on | বেশি noise লাগলে off |
| `9a` → Only signal inside a killzone | off (forex auto-on) | crypto-তেও শুধু session চাইলে on |
| HTF dealing range (E-7) | on | |
| `6 · Zones` → M10 may trade unconfirmed RJB | on | noise লাগলে off |
| `10 · Show` → Label density | Signals only | শেখার সময় "Key events" |
| `1 · General` → Setup master mode | Custom | "Core only" = curated default, toggle উপেক্ষা |

---

## ১০. "Signal আসছে না কেন?" — Data Window দিয়ে

Chart → Data Window (ডান sidebar) → `reject code (long x10 + short)`:

| Code | কারণ | করণীয় |
|---|---|---|
| 1 | কোনো candidate নেই | স্বাভাবিক |
| 2 | HTF/PD gate block | counter-HTF continuation বা deep premium |
| 3 | killzone বাইরে | session অপেক্ষা |
| 4 | R:R / geometry / TP path fail | Min R:R কমান বা TP path WARN |
| 5 | score < minimum | Min score 7 করে দেখুন |
| 6 | both sides conflict | |
| 7 | signal gap (5 bar) | |
| 8 | একই setup repeat | |
| 9 | ⏳ limit armed | chart-এ ⏳ label দেখুন |

উদাহরণ: `42` = long reject 4 (R:R), short reject 2 (gate)।

---

## ১১. ভুল যেগুলো সবাই করে

- ধূসর (counter) A+ দেখে full size নেওয়া।
- `STRONG ❌` arrival-এ zone reversal ধরা।
- 5m PD 90%+ premium-এ long chase (HTF leg discount হলেও 5m-এ retrace অপেক্ষা করুন → M74 limit দেবে)।
- ⏳ label-কে trade ভাবা। Fill না হলে trade নেই।
- TP1 FAR হলে পুরো position ধরে রাখা।
- Killzone বাইরে crypto-তে সব signal নেওয়া — Session row দেখুন।

---

## ১২. স্ক্রিনশট পড়া (BTCUSDT 5m, 17 Oct)

- HTF **BEAR**, LTF BULLISH → 5m-এ counter-trend bounce চলছে। PD: 5m 96% premium, 1h 45%।
- Watch row: `SHORT · RJB▼ 82000–82094 · sweep BSL 81796 first · CONFIRMED` → HTF দিকের plan: price 81796 BSL sweep করে 82000–82094 supply-তে ঢুকলে, CONFIRMED trigger-এ short।
- আগের `M74 A+13 · 6.4R` long (entry 82072, SL 81825, TP1 83654): note `⚠ LTF counter (pullback)` + `TP1 FAR`। কাজ করেছে (price 83,900+)।
- Session `outside killzones`: crypto, তাই signal এসেছে; forex হলে আসত না।
- অনেক ⏳ M74 label পুরনো (fill/cancel হয়ে গেছে) — label history থাকে, trade line ২০ bar।

---

*v8.5.2 · 2026-10-17 · Changelog header-এ · Review: REVIEW_v8.5.1_ENTRY_BN.md*
