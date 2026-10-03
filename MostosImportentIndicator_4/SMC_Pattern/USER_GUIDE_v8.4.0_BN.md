# SMC / ICT Suite v8.4.0 — ব্যবহারকারী গাইড (বাংলা)

ফাইল: `SMC_v8.4.0.txt` · Pine v6 · TradingView overlay indicator

এই গাইড তিন ভাগে: (১) ইনস্টল ও chart পড়া, (২) প্রতিটি setting-এর কাজ ও প্রস্তাবিত মান, (৩) trade নেওয়ার ধাপ ও সমস্যা সমাধান।

---

## ১. ইনস্টল

1. TradingView → Pine Editor → সব মুছে (Ctrl+A, Delete) `SMC_v8.4.0.txt`-এর পুরো কোড paste → Save → Add to chart।
2. Chart timeframe: 5m বা 15m (forex / gold), 5m (crypto)। 1m-এ noise বেশি, 1h+-এ signal কম।
3. প্রথমবার default setting-ই রাখুন। শুধু নিচের তিনটি দেখুন:
   - **9a · Session timezone** = America/New_York (default) — forex-এ ঠিক।
   - **9a · Killzone filter auto-on for forex** = ON — forex symbol-এ শুধু London/NY window-এ signal।
   - **8 · Zone entry trigger** = CONFIRMED (default) — কম কিন্তু ভালো signal।

---

## ২. Chart-এ কী দেখছেন

### Signal label (candle-এর নিচে ▲ long, উপরে ▼ short)

| Label | অর্থ |
| --- | --- |
| `▲▲ M37 A+12 · 3.1R` | A+ grade (score ≥ 11), module M37, score 12, TP1 = 3.1R |
| `▲ M42 A9 · 2.4R` | A grade (score 8–10) |
| `· M08 B7 · 2.0R` | B grade (min score-এর নিচে হলে দেখায় না) |
| ধূসর (grey) signal | HTF bias-এর বিপরীতে (⚠ counter), সাবধানে |
| Label-এ hover | tooltip: কেন signal, entry / SL / TP1 / TP2 / TP3, R multiple, `LIMIT @` থাকলে limit order |

### Trade lines
নীল solid = entry · লাল dashed = SL · সবুজ dashed = TP1 / TP2 / TP3 (হালকা হতে হতে)।

### Zone box
| Text | Zone |
| --- | --- |
| `OB▲ T1` / `OB▼★` | Order Block (★ = sweep-এর পর তৈরি, high-probability) |
| `BRK▲` | Breaker (ভাঙা OB উল্টো দিকে) |
| `RCB▲` | Reclaimed block (CHoCH leg origin) |
| `RJB▲` | Rejection block (wick zone) |
| `QM▲` | Quasimodo |
| `KL` / `KL★` | Key level (score 3 / 4+) |
| ` ⚠SWEEP REQ` | 2 বার touched, sweep ছাড়া trade নয় |
| ` IDM✓` | inducement swept, ভালো |
| ` ⇈PROP` | Propulsion block, পরের 50% tap = entry |
| ধূসর dashed | weak / invalid, trade নয় |

### Line
- `BOS▲ ·2FVG` solid = displacement সহ structure break · `BOS▲ weak` dotted · `iBOS` = internal (trend বদল নয়)
- `CHoCH▲` solid = real (FVG সহ) · dashed `CHoCH?` = fake
- `SWEEP✕ PDL` = PDL sweep (reversal context) · `RUN — avoid` = level ভেঙে গেছে, fade নয়
- Orange dashed মোটা line = POOL / EQH / EQL · dotted = BSL/SSL · grey = PDH/PDL/PWH/PWL · SESH/SESL = Asia range
- নীল lines = HTF candle O/H/L/C
- Background হালকা সবুজ/লাল = HTF bias BULL/BEAR

### Info panel (নিচে ডানে)
| Row | অর্থ |
| --- | --- |
| Chart / HTF | কোন HTF ব্যবহার হচ্ছে (5m → 60) |
| LTF structure | BULLISH / BEARISH / RANGE |
| HTF bias | BULL / BEAR / NEUTRAL, ⚠ = LTF-এর সাথে conflict |
| Last event | শেষ BOS / CHoCH / CISD / SWEEP কত bar আগে |
| Move phase | IMPULSIVE / RETRACEMENT (retracement-এ entry খোঁজা) |
| Active zone | price এখন কোন zone-এ, fresh না ×N |
| Arrival | zone-এ WEAK ✅ (ভালো) / STRONG ❌ (zone ভাঙতে পারে) |
| Nearest BSL / SSL | পরের liquidity target |
| 4-factor | ✅/❌ × 4 = HTF · trend · departure/arrival · liquidity target |
| Signal | বর্তমান signal ও grade |
| PD array | leg-এর কত % এ price; discount = buy side, premium = sell side |
| Session | London / NY / Asia / outside; ⛔ = killzone filter block করছে |
| TP1 / gate | REAL (structural target) / SYNTH · HTF aligned বা ⚠ counter |

---

## ৩. Settings — গ্রুপ ধরে

> নিয়ম: ★ = সাধারণ user বদলাবেন। বাকি advanced, default রাখুন।

### 1 · General
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| ATR length | সব threshold-এর scale | 14 |
| Swing length | pivot সনাক্তকরণ; কম = বেশি structure, বেশি noise | 5 (1m-এ 7, 1h-এ 4) |
| Max labels / lines | drawing budget | 200 / 100 |
| Min bars between labels | label ভিড় কমায় | 6 |
| ★ Label density | Signals only (পরিষ্কার) / Key events / All events (debug) | Signals only |
| ★ Setup master mode | Custom = নিচের toggle · Core only = curated · All on · All off | Custom |

### 2 · Candle (L0)
Pin bar, doji, engulfing, IFC, manipulative candle-এর সংজ্ঞা। Default ICT-standard; বদলানোর দরকার নেই।

### 3 · Structure (L1)
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| Bars without BOS/CHoCH → RANGE | কত bar event না হলে RANGE | 20 |
| Structure needs displacement | break-এর candle শক্ত হতে হবে (body ≥ 0.5, range ≥ 0.6 ATR) | Candle |
| …or close beyond level ≥ × ATR | level থেকে 0.3 ATR দূরে close-ও displacement | 0.3 |
| Weak break follow-through window | displacement ছাড়া break কত bar-এ confirm | 3 |
| Failed follow-throughs → RANGE | পরপর কত failed break-এ RANGE | 2 |
| CISD only after qualified sweep | CISD শুধু sweep-এর পরে | ON |

### 4 · FVG / Strength (L2)
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| Min FVG height × ATR | ছোট gap বাদ | 0.10 |
| FVG mitigation mode | TOUCH / 50% / FULL কখন FVG শেষ | TOUCH |
| Max FVGs tracked | memory | 40 |
| STRONG min body efficiency / max mixed / min speed | "strong move" সংজ্ঞা | 0.55 / 0.35 / 0.35 |

### 5 · Liquidity (L3)
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| Equal H/L tolerance | EQH/EQL pool tolerance | 0.10 ATR |
| PDH/PDL · PWH/PWL | previous day / week level | ON |
| RUN min body / close beyond | sweep বনাম run আলাদা | 0.60 / 0.25 |
| ★ SWEEP min wick ratio | sweep candle-এর wick কত বড় লাগবে | 0.50 (v8.4) |
| Sweep arms setups when level is | Major only = pool/PD/PW/SES · Include external = 50-bar extreme-ও | Major only |
| Max liquidity levels | memory | 30 |

### 6 · Zones (L4)
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| Max zones / Drop untouched after | memory | 30 / 500 |
| Zone max height × ATR | লম্বা zone clip | 3.0 |
| OB V5: sweep within N bars | OB★ (high-probability) সংজ্ঞা | 10 |
| Rejection block wick / confirm bars | RJB সংজ্ঞা | 0.50 / 15 |
| QM max bars after CHoCH | Quasimodo window | 60 |
| Key level min criteria | KL দেখাতে কত criteria | 3 |
| Count UNSCORED pivot wick zones as tradable | ON = প্রতিটি pivot zone tradable (signal flood) | OFF |
| ★ OB: high-probability only | ON = শুধু OB★ (sweep-এর পর) trade; signal কম, quality বেশি | OFF (conservative চাইলে ON) |
| Reclaimed: enforce 50% fib | RCB fib gate | ON |
| Key level volume criterion | forex-এ অবিশ্বস্ত | OFF |
| Trendline zone / anchor / confirm | M64 trendline | 0.30 / Wick / OFF |
| Propulsion window / size | M73 | 10 / 0.8 |

### 7 · HTF (L5)
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| ★ HTF pairing | Conservative 5m→1h, 15m→4h · Aggressive 5m→30m · Manual | Conservative |
| ★ HTF bias gate | OFF / WARN (counter signal ধূসর, −1) / STRICT (block) | WARN; শুধু trend-following চাইলে STRICT |
| Trend the gate reads | Entering bar (সঠিক) / This bar | Entering bar |
| HTF pivot length · sweep valid bars | HTF structure | 3 / 3 |

v8.4.0: continuation module (M02 M05 M08 M15 M33 M36 M42 M51 M73) WARN-এও counter-HTF হলে block। শুধু sweep-reversal module (M10 M37 M41 M45 M46 M54 M68) counter-HTF-এ দেখায়, ধূসর।

### 8 · Setup filters (L6)
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| Volume SMA length | KL volume criterion-এর জন্য | 20 |
| Pin bars / Dojis in leg | M06 / M07 / M04 | 2 |
| Liquidity scan distance | M09 target count | 3 ATR |
| Range detection length / max width | M50 / M53 | 20 / 3 |
| Armed setup stays valid N bars | multi-step setup window | 30 |
| ★ **Zone entry trigger** | IMMEDIATE = POI-তে প্রথম reversal candle-এই entry (আক্রমণাত্মক) · CONFIRMED = reversal candle, তারপর তার high পার close বা FVG (default) · MSS = 5 bar-এর high পার close (সবচেয়ে conservative) | CONFIRMED |
| confirm within (bars) | CONFIRMED/MSS window | 8 (MSS হলে 12) |

### 9a · Premium / Discount + Sessions
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| Score premium/discount | discount-এ long +1, premium-এ short +1; OTE (62–79%) +1 | ON |
| Block longs in premium | hard filter | OFF (test করে ON) |
| Deep threshold | 75%-এর উপরে long −1 | 0.75 |
| ★ Only signal inside a killzone | hard session filter | OFF (forex-এ auto-on নিচে) |
| Score London / NY | killzone-এ +1 | ON |
| ★ Session timezone | window কোন timezone-এ লেখা | America/New_York |
| Asia / London / NY | 2000-0000 / 0200-0500 / 0700-1000 NY time (ICT killzone) | default |
| ★ Killzone filter auto-on for forex / CFD | forex ও CFD (OANDA XAUUSD, NAS100) symbol-এ filter নিজে ON; crypto নয় | ON |
| Asia session high/low as liquidity | SESH / SESL level | ON |

Crypto 24h trade করলে: auto-on প্রভাব নেই (syminfo.type = crypto)। Index/stock-ও একই।

### 9 · Visual · Colors / 10 · Show
রঙ, label size, কোন layer দেখাবেন। সব ON রাখলে ভিড়; প্রস্তাব: S/R wick zones OFF, Legend OFF, Candle tags OFF (default)।

### 11 / 13 / 15 · Setups (module toggle)
Default ON = ২২টি curated module। নিচে কোনটা কী:

| Module | কী খোঁজে | Tier |
| --- | --- | --- |
| M01 Breakout rejection trap | breakout-এর পর wick বাড়ছে, close ফিরে এল | 2 |
| M02 Pin bar liquidity trap | breakout-এর পর wick কমছে + pin continuation | 2 |
| M05 Pin bar after breakout | break-এর পরের candle pin | 2 |
| M08 Pin bar on retracement | trend + zone + reversal | 2 |
| M09 Pin bar + liquidity | strong pin + ≥2 liquidity target | 3 |
| M10 Sweep reversal | PDH/PDL/pool sweep + close back | 2–3 |
| M15 Breakout with pin bar | break candle নিজেই pin | 2 |
| M33 Zone flip model | S→R flip + weak retest, HTF aligned | 3 |
| M36 Weak retracement on OB | OB + weak arrival + reversal | 3 |
| M37 Inducement block | EQL swept আগে, OB tap + reversal | 4 |
| M39 Reclaimed block retest | RCB retest | 3 |
| M40 Rejection block retest | RJB retest | 2 |
| M41 Sweep + FVG confluence | sweep → strong move FVG → retrace | 4 |
| M42 High-probability S&D | OB strong departure, 50%, weak arrival | 4 |
| M45 Sweep-based CHoCH retest | sweep → CHoCH → breaker/OB retest | 3–4 |
| M46 CISD setup | CISD + reliability → zone | 3 |
| M51 Smart BOS model | strong BOS → OB retest | 3 |
| M54 Smart S&D trap | demand → stop hunt → BOS → retrace | 4 |
| M58 Double top/bottom | neckline break | 2 |
| M62 Fakeout trap | failed break → level tap | 2 |
| M64 Auto trendline | শুধু draw | — |
| M68 HTF sweep → LTF entry | HTF sweep + LTF CHoCH → zone | 4 |
| M69 IFC candle | IFC break | 1 |
| M70 Quasimodo | QM zone | 2 |
| M72 Operator trap | breakout → consolidation → fail | 2 |
| M73 Propulsion Block | PROP zone 50% tap | 4 |

Tier 4 একাই দেখায় (score 9); tier 3-এ ১টি, tier 2-এ ৩টি confluence লাগে। M21–M25, M38 v8.4.0-এ বাদ (token)।

### 12 · Setup filters
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| M19 suppress reversal after STRONG arrival | displacement দিয়ে zone-এ এলে reversal নয় | ON |
| M26 pullback must be corrective | pullback mixed candle হতে হবে | ON |
| §6.2 block reversal at touch≥2 unless swept | দ্বিতীয় touch-এ sweep লাগবে | ON |
| §6.6 S&D 50% rule | OB-এর 50% tap লাগবে | ON |
| M01/M02 level rejected ≥2× | breakout level আগে ≥2 বার reject | ON |
| ★ Zone reversal must close beyond | Off / 50% / Top — reversal candle zone-এর কত উপরে close করবে | 50% (Top = আরও strict) |

### 14 · Trade (L7)
| Setting | কাজ | প্রস্তাব |
| --- | --- | --- |
| SL buffer × ATR | zone/sweep-এর নিচে বাড়তি | 0.15 |
| Max SL distance × ATR | major HL/LH SL cap | 2.0 |
| ★ Min R:R | এর নিচে signal লুকানো | 2.0 |
| Max R:R | এর বেশি দূরের target গোনা হয় না | 6.0 |
| Fixed-R mode | TP = fixed multiple (structural target নয়) | OFF |
| Require a REAL target | TP1 বাস্তব zone/FVG/liquidity-তে লাগবে | ON |
| ★ TP1 path check | entry–TP1 মাঝে opposing zone: OFF / WARN (−1) / STRICT (reject) | STRICT |
| ★ Min score to show | 8 = tier 3 + 1 confluence | 8 (বেশি signal চাইলে 7, কম চাইলে 9) |
| A+ ≥ / A ≥ | grade threshold | 11 / 8 |
| Min bars between signals | দুই signal-এর gap | 5 |
| Suppress SAME setup N bars | একই zone-এ একই module repeat নয় | 50 |
| M10 entry mode | IMMEDIATE / RETEST (swept level limit) / BOTH | IMMEDIATE |
| ★ **Entry price** | CLOSE = confirm candle close-এ market · CANDLE 50% = candle মাঝে limit · ZONE EDGE = zone top-এ limit (fill না-ও হতে পারে, R:R ভালো) | CLOSE শুরুতে; অভিজ্ঞ হলে CANDLE 50% |
| Min risk (ticks) | spread-এর চেয়ে ছোট SL বড় করা | 20 (gold 20, EURUSD 20 = 2 pip) |
| Draw entry/SL/TP lines · length | | ON / 20 |

---

## ৪. Trade নেওয়ার ধাপ (checklist)

1. **Panel দেখুন**: HTF bias ও LTF structure একই দিকে? ⚠ থাকলে শুধু tier-4 (M37 M41 M42 M54 M68 M73) নিন।
2. **Session**: London বা NY? outside killzone-এ (forex) signal এমনিতেই আসবে না।
3. **Signal label**: A+ বা A। B দেখা যায় না (min 8)। ধূসর label = counter-HTF, size অর্ধেক।
4. **Tooltip পড়ুন**: entry, SL, TP1 (R), `[structural]` লেখা আছে কি না। `LIMIT @` থাকলে ওই দামে limit order; 8 bar-এ fill না হলে বাতিল।
5. **Active zone / Arrival**: Arrival WEAK ✅ হলে ভালো। STRONG ❌ হলে zone ভাঙার ঝুঁকি।
6. **PD array**: long-এ discount (< 50%) ভালো; 75%+ premium-এ long এড়ান।
7. **Order**: entry নীল line, SL লাল, TP1 সবুজ। TP1-এ অর্ধেক close, SL breakeven; TP2/TP3 বাকি।
8. **একই zone আবার signal দিলে** (50 bar পর) দ্বিতীয়বার সাবধান: `⚠SWEEP REQ` দেখুন।

---

## ৫. Alerts

- Create Alert → Condition: SMC Suite → **Any alert() function call** = প্রতিটি signal-এ message: `XAUUSD | M42 LONG | Score 11 | Entry … SL … TP … | TF 5 | HTF BULL`।
- আলাদা condition: LONG signal, SHORT signal, Any A+ signal, Counter-HTF warning, BOS, CHoCH (Real), CISD, Sweep, New HP OB, Propulsion block, OB 50% tapped।
- সব alert bar close-এ, repaint নেই।

---

## ৬. সমস্যা সমাধান

| সমস্যা | কারণ ও সমাধান |
| --- | --- |
| Signal আসছে না | Data window-এ `reject code` দেখুন: 1 = candidate নেই · 2 = HTF/PD gate · 3 = killzone বাইরে · 4 = R:R / path / geometry · 5 = score < 8 · 6 = conflict · 7 = gap · 8 = duplicate। code 3 হলে session-এর বাইরে; code 4 হলে TP path STRICT → WARN করে দেখুন; code 5 হলে min score 7 |
| খুব বেশি signal | Zone entry trigger MSS · OB high-probability only ON · min score 9 |
| Crypto-তে session filter দরকার | "Only signal inside a killzone" ON, timezone UTC, window নিজে set |
| Label overlap | Label density = Signals only, Min bars between labels 8 |
| "Script is too large" compile error | editor-এ পুরনো code রয়ে গেছে, Ctrl+A → Delete → paste; তাও হলে M44 M47 M48 M49 M50 M52 M53 মুছুন |
| HTF bias ভুল মনে হচ্ছে | HTF pairing Manual করে 240 বা D দিন |
| Zone box text দেখা যাচ্ছে না | Zone / level text size = normal |

---

## ৭. v8.3.2 → v8.4.0 কী বদলেছে (সংক্ষেপে)

- Entry trigger default CONFIRMED (+ MSS mode); M08 M09 M36 trigger মানে
- Reversal candle zone-এর 50% উপরে close করতে হবে
- TP1 path check STRICT
- Killzone NY time (DST-safe), forex-এ auto-on
- M10: sweep candle উপরের অর্ধে close, wick 0.50
- Entry price option (limit at candle 50% / zone edge)
- HTF FVG-র ভেতরে থাকলে +1 score; OTE band +1
- Continuation module counter-HTF হলে block
- Signal gap 5, min risk 20 tick
- M21–M25, M38 বাদ (token budget)
