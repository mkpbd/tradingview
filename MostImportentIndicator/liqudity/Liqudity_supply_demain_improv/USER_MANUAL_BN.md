# LQ-SD-PA v3.2.0 — ইউজার ম্যানুয়াল (বাংলা)

> ফাইল: `version_02_fixed.pine`
> টাইমফ্রেম: **M5 / M15** (এটাই ডিজাইন)
> অ্যালার্ট: **Once per bar close** — অন্য কিছু নয়
> ⚠️ এটা শিক্ষামূলক টুল। সিগন্যাল = narrative alignment, win probability নয়।

---

## ১. ৫ মিনিটে শুরু

1. TradingView → Pine Editor → পুরো `version_02_fixed.pine` পেস্ট → **Add to chart**
2. চার্ট **XAUUSD / BTCUSDT / EURUSD** যেকোনো একটা, **5m** টাইমফ্রেম
3. Settings (⚙) খোলো → **Signal quality / state machine** → **Min alignment score = 0** ← ⚠️ **প্রথম দিনেই এটা করো**
4. Settings → **Dashboard / Debug** → **Debug mode = ON**
5. কয়েকদিন শুধু **দেখো**, ট্রেড নয়। Debug টেবিলে স্কোর কত আসে নোট করো।
6. এক সপ্তাহ পর `Min alignment score` সেই গড়ের সামান্য নিচে সেট করো (সাধারণত ৪০–৫৫)।

**কেন step 3 দরকার:** ডিফল্ট ৬০ খুব কড়া। লাইভ চার্টে স্কোর সাধারণত ৩৫–৪৫ আসে। ৬০ রাখলে চার্ট নীরব থাকবে, তুমি ভাববে ইন্ডিকেটর নষ্ট — আসলে নষ্ট নয়, দরজা বন্ধ।

---

## ২. চার্টে কী কী দেখবে

### লিকুইডিটি চিহ্ন
| চিহ্ন | অর্থ |
|---|---|
| **◆** (নিচে/উপরে) | Swing sweep — pivot লেভেল নেওয়া হয়েছে |
| **◈** | EQH/EQL pool নেওয়া হয়েছে (engineered liquidity — বেশি গুরুত্বপূর্ণ) |
| **◇** | PDH/PDL (গতকালের হাই/লো) নেওয়া হয়েছে |
| **▿ / ▵** | Session high/low **raided** (wick নিয়ে ফিরে এসেছে) |
| **⇡ / ⇣** | Session high/low **broken** (ক্লোজ ভেদ করেছে — raid নয়) |
| **✕** | Trendline ভেঙেছে |

**Raid ≠ Break।** Raid = wick নিয়ে ফিরল → reversal fuel। Break = ক্লোজ ভেদ করল → continuation।

### স্ট্রাকচার চিপ
| চিপ | অর্থ | শক্তি |
|---|---|---|
| **MSS** | সুইপ চলাকালীন protected swing ভাঙা | সবচেয়ে শক্তিশালী |
| **CHoCH** | protected swing-এ displaced ক্লোজ | মাঝারি |
| **BOS** | ট্রেন্ড চলমান রাখার ব্রেক | দুর্বলতম |
| **iCHoCH / ibos** | internal (ছোট) — ধূসর, কম গুরুত্ব | তথ্যমাত্র |
| **CISD** | ২+ বিপরীত ক্যান্ডেলের origin open ভেদ করে displacement ক্লোজ | delivery বদল |
| **IFC** | Institutional funding candle — pool নিয়ে midpoint ভেদ | শক্তিশালী ক্যান্ডেল |

### জোন (বক্স)
| লেবেল | অর্থ |
|---|---|
| **DEMAND / SUPPLY** | FVG-imbalance জোন। `★HP` = সুইপ-ভিত্তিক, উচ্চ মানের |
| **OB ▲ / OB ▼** | Order Block — displacement leg-এর আগের বিপরীত ক্যান্ডেল (পাতলা বক্স) |
| **REJECTION ▲/▼** | Rejection block — swept pivot wick |
| **BREAKER ▲/▼** | ভাঙা জোন যা সুইপ + structure break নিয়ে ফ্লিপ হয়েছে (ভালো) |
| **MITIGATION ▲/▼** | ভাঙা জোন, কিন্তু সুইপ/ব্রেক ছাড়া ফ্লিপ (দুর্বল) |
| **·tested** | দাম একবার ছুঁয়েছে |
| **·spent** | বারবার টেস্ট হয়ে শেষ — আর POI নয় |

### NEXT BUY / NEXT SELL লাইন
```
NEXT BUY T3 • 4332.945-4340.095 (0.09% below) ·fresh
NEXT SELL T2 MIT • 4357.720-4361.370 (price INSIDE)
```
- `T2 / T3` = জোনের গ্রেড (T3 = সুইপ-ভিত্তিক, ভালো)
- `MIT / BRK / OB / RB` = জোনের ধরন (SD হলে দেখায় না)
- `·fresh` = এখনো টাচ হয়নি
- `(price INSIDE)` = দাম এই মুহূর্তে জোনের ভেতরে

⚠️ **এটা সিগন্যাল নয় — লোকেশন মার্কার।** ইঞ্জিন পরের POI tap-এর জন্য এখানে অপেক্ষা করছে।

### অন্যান্য
- **নীল/কমলা/বেগুনি লাইন** — Asia / London / NY সেশনের high-low
- **রূপালি লাইন** — PDH/PDL/PWH/PWL
- **সবুজ/লাল ছায়া** — Discount (buy flow) / Premium (sell flow)
- **OTE 62–79% বক্স** — optimal trade entry অঞ্চল
- **টিল ব্যান্ড** — Silver Bullet উইন্ডো চলছে
- **লাল ব্যান্ড** — volatility window (entry ব্লকড)
- **◬ TRAP LONG/SHORT** — Liquidity Trap ইঞ্জিনের সিগন্যাল

---

## ৩. ড্যাশবোর্ড পড়ার নিয়ম (উপর → নিচ)

| সারি | কী দেখায় | কীভাবে পড়বে |
|---|---|---|
| **হেডার** | Regime | TRENDING ভালো · TRANSITION ঠিক আছে · RANGING সাবধান · **CHOP = বসে থাকো** |
| **HTF bias** | ৫ টাইমফ্রেমের bias | যত বেশি একদিকে, তত ভালো। 1H+4H একমত না হলে সাবধান |
| **Structure** | int / ext দিক | **ext**-টাই আসল। int = ছোট নয়েজ |
| **Sweep in play** | SSL/BSL + গ্রেড | `none` = কোনো লিকুইডিটি ইভেন্ট নেই → ট্রেড নেই |
| **Range pos** | Premium/Discount % | **BUY = Discount (<50%) · SELL = Premium (≥50%)**। `·tight` মানে leg খুব সরু, বিশ্বাস করো না |
| **Next demand** | `T3 4332.9–4340.1 ·0.09% ·fresh` | নিচের নিকটতম POI |
| **Next supply** | একইভাবে | উপরের নিকটতম POI |
| **Trigger** | MSS/CHoCH/BOS/CISD | শেষ ১০ বারে কী ঘটেছে |
| **◉ Setup long** | idle → SWEPT → AT POI → SHIFTED → ACTIVE | চেইন কতদূর এগিয়েছে |
| **◉ Setup short** | একইভাবে | |
| **◎ FEM** | Fractal entry model অবস্থা | HTF POI → LTF shift → FVG lock |
| **Alignment** | `L 41 (B) S 22 (C)` | স্কোর + tier। **tier গুরুত্বপূর্ণ, স্কোর নয়** |
| **Session** | Asia/London/NY/Silver Bullet | |
| **Volatility win** | clear / ⚠ WINDOW | WINDOW = entry ব্লকড |
| **Active trade** | flat / LONG 4359 SL 4348 | ট্র্যাক করা ট্রেড |
| **Verdict** | সিগন্যাল বা **কেন নেই** | ⭐ সবচেয়ে গুরুত্বপূর্ণ সারি |
| **◆ Silver Bullet** | off-window / pre-window / ACTIVE 23m left | |
| **◆ SB setup** | SB-tagged সেটআপের অবস্থা | |

### Verdict কী বলতে পারে
| বার্তা | মানে | কী করবে |
|---|---|---|
| `LONG signal` / `SHORT signal` | সিগন্যাল ফায়ার করেছে | প্ল্যান দেখো |
| `NO TRADE · score 41 < 60` | স্কোর কম | `minScore` কমাও |
| `NO TRADE · chop` | CHOP regime | বসে থাকো |
| `NO TRADE · no liquidity event` | কোনো সুইপ নেই | অপেক্ষা |
| `NO TRADE · volatility window` | নিউজ স্লট | অপেক্ষা |
| `NO TRADE · risk 2.4 ATR exceeds the cap` | stop খুব চওড়া | দেরি হয়ে গেছে, ছেড়ে দাও |
| `NO TRADE · reward blocked — only 0.9R...` | সামনে বিপরীত POI | RR নেই |
| `NO TRADE · entry slipped (1.2 ATR...)` | দাম প্ল্যান প্রাইস ছেড়ে দূরে | fill বাস্তবসম্মত নয় |
| `NO TRADE · outside the SB windows` | SB-only mode চালু | |
| `waiting` | সব ঠিক, চেইন এগোচ্ছে | ধৈর্য |

---

## ৪. সিগন্যাল লেবেল পড়ার নিয়ম

```
A · 62
◉ SETUP A
Demand 50%
```
- **প্রথম লাইন** = tier (`A+` / `A` / `B` / `C`) + alignment স্কোর
- **◉ SETUP** = master state machine (প্রধান পথ — সবচেয়ে নির্ভরযোগ্য)
- **◆ SB NY AM · CE A** = Silver Bullet entry, CE-তে fill, A tier
- বাকি লাইন = কোন কোন ইঞ্জিন একমত (Demand 50% / CRT / TSoup / IB break / TL sweep / ◎ FEM)

**একাধিক লাইন = বেশি confluence = ভালো।**

### Entry / SL / TP লাইন
```
E 4359.71 · RR 2.0 (plan, not promise)
SL 4348.20
TP1 4371.22   ← 1R
TP2 4382.73   ← rrMult R, বিপরীত POI-তে clamp হতে পারে
TP3 4394.24   ← liquidity target বা 3R
```

---

## ৫. ট্রেড নেওয়ার নিয়ম — ধাপে ধাপে

সিগন্যাল এলে ড্যাশবোর্ডে **এই ক্রমে** চেক করো:

1. **Regime** ≠ CHOP
2. **HTF bias** সিগন্যালের দিকে
3. **Range pos** সঠিক দিকে — BUY হলে Discount, SELL হলে Premium (`·tight` থাকলে বাদ)
4. **Sweep in play** আছে এবং গ্রেড ≥ valid
5. **Setup** সারিতে `ACTIVE` (মানে পুরো চেইন চলেছে)
6. **Alignment tier** = A বা A+
7. **Verdict** = LONG/SHORT signal
8. চার্টে **E / SL / TP** লাইন দেখে RR যাচাই

**৮টার মধ্যে একটাও না মিললে ট্রেড নেই।**

### ⭐ A+ সেটআপ — সর্বোচ্চ মানের (দিনে ০–২টা)
```
Raw sweep quality ≥ 3   (Debug টেবিলে raw3/eff4 এর মতো দেখাবে)
Pool kind ≥ 3           (PDH/PDL বা prior session H/L)
HTF bias একমত
Regime TRENDING/TRANSITION
P/D সঠিক দিকে
POI = fresh HTF FVG বা untested OB
Shift = MSS (শুধু CHoCH নয়)
Anchor = shift leg-এর clean displacement FVG
Entry = CE fill
Risk ≤ 1.5 ATR · RR ≥ 2
Session = London বা NY AM
```

---

## ৬. সেটিংস — সম্পূর্ণ গাইড

### 🔴 প্রথমে যে ৩টা ছোঁবে

| গ্রুপ | ইনপুট | ডিফল্ট | কী করবে |
|---|---|---|---|
| Signal quality | **Min alignment score** | 60 | **০ করো**, তারপর ধীরে বাড়াও |
| Signal quality | **Show signal tiers** | A and above | রাখো। কম সিগন্যাল = ভালো |
| Dashboard / Debug | **Debug mode** | OFF | শেখার সময় **ON** |

---

### General
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Internal pivot length | 5 | ছোট সুইং। কমালে বেশি নয়েজ |
| External pivot length | 12 | বড় সুইং — structure, regime, dealing range সব এর উপর |
| ATR length | 14 | রাখো |
| Bias EMA length | 50 | MTF টেবিলের bias EMA |
| Show last swing high/low | ON | |

**পরামর্শ:** M15-এ `extPiv` 12 ঠিক। M5-এ নয়েজ বেশি মনে হলে 15 করো।

---

### HTF context
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| **HTF bias filter** | 60 | ⭐ counter-trend entry ব্লক করে। `Off` = ব্লক করবে না (শুধু স্কোর) |
| HTF CRT + Turtle-soup | ON | HTF trigger candidate |
| HTF for CRT/TBS/POI | Auto | 5m → 60m, 15m → 240m |
| HTF POI max age | 40 | HTF ক্যান্ডেলে POI-র বয়স |
| HTF POI max touch | 3 | কতবার ঢোকার পর spent |

**পরামর্শ:** 5m চার্টে `60` রাখো। খুব কম সিগন্যাল পেলে `15` করে দেখো। `Off` করবে না — এটাই সবচেয়ে সস্তা ফিল্টার।

---

### Liquidity
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Mark liquidity sweeps | ON | |
| **Sweep stays in play** | 12 | কত বার পর্যন্ত সুইপ "লাইভ"। reclaim হারালে এমনিতেই শেষ |
| Track EQH/EQL | ON | **বন্ধ করলেও detection চলে** (শুধু লাইন লুকায়) |
| Equal level tolerance | 0.15 ATR | দুটো pivot কত কাছে হলে "equal" |
| **Min sweep quality to arm** | 2 | 1 weak · 2 valid · 3 strong · 4 institutional |
| Prev day/week lines | ON | |

**পরামর্শ:** কড়া করতে চাইলে `Min sweep quality = 3`। তখন শুধু outer-half close + displacement body সুইপ setup arm করবে।

---

### Structure
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Label BOS/CHoCH/MSS | ON | |
| **Structural break body ≥ ATR ×** | 0.5 | ব্রেক ক্যান্ডেলের ন্যূনতম বডি। 0 = যেকোনো ক্লোজ |
| Plot protected swing | ON | trail-এর ভিত্তি |
| Order-flow zigzag | OFF | চার্ট এলোমেলো করে |

---

### FVG
| ইনপুট | ডিফল্ট |
|---|---|
| Draw live FVGs | ON |
| Max live FVGs per side | 4 |
| FVG max age | 120 bars |

---

### Supply / Demand / Order blocks
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Show zones | ON | **বন্ধ করলে POI-ই থাকবে না → চেইন ভাঙবে** |
| **Displacement body ≥ ATR ×** | 1.2 | জোন তৈরির শর্ত। বাড়ালে কম কিন্তু ভালো জোন |
| Max zone height | 2.0 ATR | এর চেয়ে লম্বা জোনে precision নেই |
| Max zones per side | 6 | |
| Mark ORDER BLOCK origin | ON | |
| Max bars 50% tap → confirm | 5 | |
| Flip violated zones | ON | Breaker/Mitigation |
| Rejection blocks | ON | |
| **Zone spent after N tests** | 2 | ২ বার টেস্ট হলে জোন মৃত |

---

### Next buy / sell level
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Show NEXT BUY/SELL | ON | |
| **Line sits on** | Proximal edge | অথবা `Zone 50% (CE)` — মেশিনের limit লজিক এখান থেকে কাজ করে |
| Shade the zone band | ON | |
| Show distance (%) | ON | |
| Line extends back | 60 bars | |
| **Label position** | Middle of the line | `Right edge` করলে ড্যাশবোর্ডের সাথে ওভারল্যাপ করবে |

---

### CRT / Turtle soup / CISD / IFC
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| CRT trigger | ON | Range → Raid → Reclaim → Delivery |
| CRT min candle-1 range | 1.2 ATR | |
| CRT min candle-3 body | 0.5 ATR | |
| Turtle soup trigger | ON | |
| Turtle soup lookback | 20 | |
| Swept extreme min age | 4 | খুব নতুন extreme = turtle soup নয় |
| Swept extreme max age | 60 | খুব পুরোনো = বাসি লিকুইডিটি |
| Label CISD | ON | |
| **Accept CISD as confirmation** | ON | |
| Mark IFC candles | ON | |
| **Engine cooldown per direction** | 10 bars | স্প্যাম কমায় |

---

### Inside bar / Doji
| ইনপুট | ডিফল্ট |
|---|---|
| Inside Bar Breakout | ON |
| Min mother-candle body | 1.0 ATR |
| Doji Reversal | ON |
| Doji body ≤ % of range | 25 |
| Min dojis in window | 3 |
| Min significant wick | 0.3 ATR |

**পরামর্শ:** এ দুটো সবচেয়ে দুর্বল ইঞ্জিন। নয়েজ বেশি মনে হলে দুটোই OFF করো — machine path ক্ষতিগ্রস্ত হবে না।

---

### Trendlines
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Draw trendlines | ON | |
| Trendline sweep trigger | ON | |
| Require confirmation at line | ON | |
| **Extra touches before trigger** | 0 | touch = এক approach (দাম দূরে গিয়ে ফিরে আসা) |
| **Trendline expires after** | 150 bars | পুরোনো লাইন আর tradable নয় |

---

### Fractal entry model (FEM)
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Enable FEM | ON | HTF POI → LTF shift → locked FVG → retest |
| Max bars POI tap → execution | 40 | |
| Draw HTF FVG POI boxes | ON | |

---

### Dealing range / OTE
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Show range EQ + OTE box | ON | |
| Shade premium/discount | ON | |
| **Dealing range swings** | External | `Internal` = দ্রুত re-anchor, বেশি সংবেদনশীল |

**নোট:** range এখন anchor swing থেকে বর্তমান বার পর্যন্ত running high-low। দাম সবসময় ভেতরে থাকে।

---

### Sessions (New York time)
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| **Only signal inside killzones** | OFF | ON করলে killzone-এর বাইরে কিছুই ফায়ার করবে না |
| Shade killzones | OFF | |
| **Session high/low lines** | ON | **বন্ধ করলেও detection চলে** |
| Asia | 2000-0000 | |
| London | 0200-0500 | |
| New York AM | 0700-1000 | |
| SB London open | 0300-0400 | |
| SB NY AM | 1000-1100 | priority window |
| SB NY PM | 1400-1500 | |
| 00:00 + 08:30 open lines | ON | |

⚠️ **সব সময় New York টাইম।** তোমার ব্রোকারের টাইম আলাদা হলেও ইন্ডিকেটর নিজেই NY-তে কনভার্ট করে — হাত দিও না।

---

### ◆ Silver Bullet — setup
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| **Enable SB module** | ON | OFF = শুধু সাধারণ ইঞ্জিন |
| London / NY AM / NY PM | সব ON | |
| **Arm from N min BEFORE window** | 15 | raid প্রায়ই উইন্ডোর ঠিক আগে হয় |
| London min sweep quality | 3 | সবচেয়ে কড়া উইন্ডো |
| NY AM min sweep quality | 2 | |
| NY PM min sweep quality | 3 | |
| **Require a preferred pool** | ON | ⭐ doctrine: SB raid engineered liquidity নেয় |
| Count Asia H/L as SB pool | ON | NY AM-এর ক্লাসিক pool |
| **SB may arm in CHOP** | ON | SB উইন্ডো scheduled delivery slot |
| Kill unfilled SB at window close | ON | |
| SB clock: sweep → POI tap | 12 bars | |
| SB clock: POI tap → shift | 8 bars | |
| SB clock: shift → entry | 10 bars | |
| SB FVG min height | 0.10 ATR | এক-টিকের গ্যাপ নয় |
| **Require a true MSS** | OFF | **M15+ এ ON করার সুপারিশ** |

---

### ◆ Silver Bullet — entry
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| **SB entry rule** | CE preferred + proximal on strong rejection | `CE (50%) only` = আরও কড়া |
| CE tolerance | 0.10 ATR | |
| Require HTF bias alignment | ON | |
| Require correct premium/discount | ON | |
| **Min tier for SB entry** | A and above | `A+ only` = খুব কড়া |
| Non-SB signals while SB live | Down-weight | `Suppress` = SB চলাকালীন বাকি সব মিউট |
| **SB-only mode** | OFF | ON = শুধু SB উইন্ডোতে ট্রেড |

---

### ◆ Silver Bullet — exits
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Force exit at window close if TP1 unhit | ON | |
| Window-close exit | Full | অথবা `Partial (rest to break-even)` |
| TP3 = nearest opposing pool | ON | |
| Exit remainder on opposing MSS/CISD | ON | |
| Break-even buffer after TP1 | 0.15 ATR | |
| Trail behind protected swing after TP2 | ON | |

---

### Scheduled volatility windows
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Block entries inside windows | ON | |
| Shade the windows | ON | |
| **Allow NY AM SB through window #2** | ON | না হলে SB-র সেরা ১০ মিনিট সেন্সরড |
| Window #1 | 0825-0845 | 08:30 US data |
| Window #2 | 0955-1010 | 10:00 US data |
| Window #3 | 1355-1435:4 | বুধবার FOMC |

⚠️ **এটা লাইভ নিউজ ক্যালেন্ডার নয়** — ফিক্সড ঘড়ি। সপ্তাহের আসল রিলিজ অনুযায়ী নিজে এডিট করো।

---

### Signal quality / state machine
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| **Show signal tiers** | A and above | `B and above` = নয়েজ · `A+ only` = দিনে ০–১টা |
| **Min alignment score** | 60 | ⭐ **শুরুতে ০ করো** |
| **Global same-direction cooldown** | 15 bars | একই narrative থেকে দুবার এন্ট্রি নয় |
| Suppress entries in CHOP | ON | ব্যতিক্রম: quality-4 সুইপ |
| Machine: sweep → POI tap | 20 bars | |
| Machine: POI tap → shift | 15 bars | |
| Machine: shift → entry | 20 bars | |

---

### Risk / TP / SL
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Show entry/SL/TP lines | ON | |
| **TP3 mode** | Liquidity target | অথবা `R multiple` |
| **TP2 R multiple** | 2.0 | |
| **Max risk (ATR ×)** | 1.5 | ⭐ এর চেয়ে চওড়া stop = দেরি হয়ে গেছে |
| **When stop wider than cap** | Reject the signal | অথবা `Clamp the stop` |
| **Min RR to TP2** | 1.5 | সামনে বিপরীত POI থাকলে reward কমে যায় |
| **Max distance close → plan entry** | 0.5 ATR | slippage guard |

**পরামর্শ:** এই ৪টা নতুন ফিল্টার সবচেয়ে বেশি খারাপ ট্রেড কাটে। শুরুতে ডিফল্ট রাখো। সিগন্যাল খুব কম মনে হলে `Max risk` 2.0 করো, তারপরও কম হলে `Min RR` 1.0।

---

### ◬ Liquidity Trap Engine
| ইনপুট | ডিফল্ট | ব্যাখ্যা |
|---|---|---|
| Enable LT engine | ON | ৭টা breakout-trap প্যাটার্ন |
| **Apply context gates** | ON | killzone/volatility/chop/HTF ফিল্টার প্রয়োগ |
| **Minimum trap confidence** | HIGH and above | `MEDIUM` = অনেক বেশি সিগন্যাল |
| **Trap veto** | ON | একদিকে trap অপেক্ষারত → বিপরীত দিক মিউট |
| LT-1 … LT-7 | সব ON | আলাদা করে বন্ধ করা যায় |

**LT সিগন্যাল = আলাদা লেয়ার।** `◬ TRAP` লেবেল main সিগন্যাল নয়। Main সিগন্যালের সাথে একমত হলে confluence, বিপরীত হলে সতর্কতা।

---

### Dashboard / Debug / UI
| ইনপুট | ডিফল্ট |
|---|---|
| Show context dashboard | ON |
| **Debug mode** | OFF → শেখার সময় ON |
| Label / box / dashboard text size | Normal |

---

## ৭. তিনটা প্রস্তুত প্রোফাইল

### 🟢 শেখার / পর্যবেক্ষণ প্রোফাইল
```
Min alignment score      = 0
Show signal tiers        = B and above
Debug mode               = ON
Max risk (ATR ×)         = 2.0
Min RR to TP2            = 1.0
```
বেশি সিগন্যাল দেখবে, বুঝবে ইঞ্জিন কীভাবে ভাবে। **ট্রেড নয়, শুধু নোট।**

### 🟡 ব্যালান্সড (দৈনিক ব্যবহার)
```
Min alignment score      = 45
Show signal tiers        = A and above
HTF bias filter          = 60
Min sweep quality to arm = 2
Max risk (ATR ×)         = 1.5
Min RR to TP2            = 1.5
Global cooldown          = 15
```

### 🔴 কড়া / A+ শিকার
```
Min alignment score      = 60
Show signal tiers        = A+ only
Min sweep quality to arm = 3
Require a preferred pool = ON
Require a true MSS       = ON
Inside Bar + Doji        = OFF
Min RR to TP2            = 2.0
```
দিনে ০–২টা সিগন্যাল। এটাই ডকট্রিন।

### ◆ Silver Bullet-only
```
SB-only mode             = ON
SB entry rule            = CE (50%) only
Require a true MSS       = ON
Min tier for SB entry    = A+ only
Min alignment score      = 0   ← SB নিজের গেট নিজে রাখে
```
শুধু London 03–04 · NY AM 10–11 · NY PM 14–15 (NY time)।

---

## ৮. অ্যালার্ট সেটআপ

### কোনটা লাগাবে
| অ্যালার্ট | কখন |
|---|---|
| `[SIGNAL] A+ LONG` / `A+ SHORT` | সর্বোচ্চ মানের সিগন্যাল |
| `[SIGNAL] A LONG` / `A SHORT` | A-tier |
| `[SIGNAL] ◉ Setup machine entry` | মূল state machine entry |
| `[SETUP] Armed (quality sweep)` | চেইন শুরু — প্রস্তুত হও |
| `[SETUP] POI tapped` | POI-তে পৌঁছেছে |
| `[SETUP] Structure shifted` | shift হয়েছে, retest-এর অপেক্ষা |
| `[TRADE] TP1/TP2/SL hit` | ট্রেড ম্যানেজমেন্ট |
| `[SB] ◆ Silver Bullet entry` | SB entry |

### ⚠️ বাধ্যতামূলক সেটিং
- **Condition:** `Once per bar close` — অন্য কিছু নয়, নইলে repaint হবে
- **আলাদা করে একটা:** `Any alert() function call` → এতে Silver Bullet আর Liquidity Trap-এর বিস্তারিত বার্তা আসে (window, CE-vs-edge, tier, score, পুরো exit plan)

---

## ৯. Debug টেবিল দিয়ে সমস্যা খোঁজা

`Debug mode = ON` করলে নিচে-ডানে দ্বিতীয় টেবিল আসে:

| সারি | কী পড়বে |
|---|---|
| **SSL / BSL** | `bar 1234 lvl 4340.1 raw3/eff4 k3 ·in play` → raw = ক্যান্ডেলের অর্জিত গ্রেড, eff = MSS upgrade সহ, k = pool kind (1 swing · 2 EQ · 3 PD · 4 session) |
| **Machine L / S** | বর্তমান stage + **শেষ কেন মরেছে** ⭐ |
| **FEM** | L/S stage নম্বর |
| **CISD runs** | চলমান run length |
| **Regime in** | regime + external range কত ATR |
| **Score L / S** | `C12 L20 P10 T8 E5` → Context/Liquidity/POI/Trigger/Execution ভাঙা |
| **Counters** | A · A+ · Long · Short সংখ্যা |
| **Outcomes** | TP1 · TP2 · SL — **পরিসংখ্যান নয়, শুধু touch count** |
| **◬ LT machine** | trap state |
| **◆ SB state** | window, tag, pool kind, FVG ok |

**সবচেয়ে কাজের সারি: `Machine L` / `Machine S`।** ওখানে লেখা থাকে সেটআপ কেন মরল —
`sweep undone` · `opposing displacement` · `POI violated` · `sweep expired (no POI tap)` · `retest window expired` · `risk 2.4 ATR exceeds the cap` · ইত্যাদি।

একই কারণ বারবার এলে সেই ইনপুটটাই টিউন করার জায়গা।

---

## ১০. সাধারণ সমস্যা ও সমাধান

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| **কোনো সিগন্যাল আসছে না** | `minScore 60` | ০ করো। Verdict সারি কারণ বলবে |
| Verdict বলছে `score 41 < 60` | স্কোর কম | `minScore` ৪০ করো |
| Verdict বলছে `chop` | CHOP regime | স্বাভাবিক। অপেক্ষা করো বা `Suppress in CHOP` OFF |
| Verdict বলছে `no liquidity event` | সুইপ নেই | এটাই ঠিক — লিকুইডিটি ছাড়া ট্রেড নেই |
| Verdict বলছে `risk ... exceeds the cap` | দেরিতে সিগন্যাল | `Max risk` 2.0 করো, বা ছেড়ে দাও |
| **Range pos-এ `·tight`** | leg ২ ATR-এর কম | premium/discount বিশ্বাস করো না |
| **Next demand/supply `none`** | দাম সব জোন ছাড়িয়ে গেছে | নতুন জোন তৈরির অপেক্ষা |
| Silver Bullet কখনো arm হয় না | pool kind < 2 | `Require a preferred pool` OFF করে দেখো |
| চার্ট খুব ভিড় | সব ইঞ্জিন ON | Inside Bar, Doji, Trendline, LT — বন্ধ করো |
| লেবেল ওভারল্যাপ | | `Label position = Middle`, text size `Small` |
| **Daily/Weekly চার্টে অদ্ভুত** | এটা M5/M15-এর টুল | M5/M15-এ ফিরে যাও |
| SB সারি বলছে `—` | non-intraday চার্ট | SB শুধু intraday-তে চলে |

---

## ১১. যা করবে না

- ❌ **M1-এ চালাবে না** — শুধু নয়েজ
- ❌ **H1/H4/Daily-তে SB আশা করবে না** — উইন্ডোতে ১টাই বার
- ❌ `Show zones` OFF করবে না — POI ছাড়া চেইন ভাঙবে
- ❌ অ্যালার্টে `Once per bar` ব্যবহার করবে না — `Once per bar **close**`
- ❌ Debug টেবিলের `Outcomes` সংখ্যাকে backtest ভাববে না — ওটা শুধু মেকানিক্যাল touch count
- ❌ **RR "plan, not promise"** — লেখাটা আক্ষরিক
- ❌ নতুন কোনো `plot` / `plotchar` / `bgcolor` / `alertcondition` যোগ করবে না — **৬৪ output বাজেট পূর্ণ** (8+14+5+37)
- ❌ `◬ TRAP` লেবেলকে main সিগন্যাল ভাববে না — ওটা আলাদা লেয়ার

---

## ১২. এক নজরে দৈনিক রুটিন

**সেশনের আগে (London বা NY খোলার ১৫ মিনিট আগে):**
1. HTF bias সারি দেখো — 1H + 4H কী বলছে
2. Regime দেখো — CHOP হলে আজ হালকা দিন
3. Next demand / Next supply নোট করো — আজ কোথায় অপেক্ষা

**সেশন চলাকালীন:**
4. `[SETUP] Armed` অ্যালার্ট এলে চার্ট খোলো
5. Setup সারি SWEPT → AT POI → SHIFTED এগোচ্ছে কি না দেখো
6. `SHIFTED·await retest` এলে CE লেভেল নোট করো (চার্টে টিল লাইন)
7. সিগন্যাল এলে ৫ নম্বর সেকশনের ৮টা চেক করো
8. Entry নিলে TP1-এ break-even, TP2-এ trail

**দিনের শেষে:**
9. Debug টেবিলে `Machine L/S` এর শেষ kill reason পড়ো
10. একই কারণ বারবার এলে সেই ইনপুট টিউন করো

---

**মনে রাখো:** কম সিগন্যাল = ভালো ইন্ডিকেটর। লিকুইডিটি-ভিত্তিক ট্রেডিং-এ দিনে ২টা A+ সেটআপই যথেষ্ট। ইঞ্জিন দিনে ২০টা দিলে সে তোমাকে সাহায্য করছে না — ব্যস্ত রাখছে।
