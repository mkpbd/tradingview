# SMC / ICT Suite v8.3.0 — ব্যবহার নির্দেশিকা (User Manual)

এই ইন্ডিকেটরটি Smart Money Concept (SMC) / ICT পদ্ধতিতে চার্ট পড়ে: মার্কেট স্ট্রাকচার (BOS / CHoCH), লিকুইডিটি লেভেল ও সুইপ, FVG, Order Block ও অন্যান্য জোন, HTF বায়াস, আর এসব মিলিয়ে BUY / SELL সিগন্যাল দেয় — সাথে Entry / SL / TP লাইন ও অ্যালার্ট।

---

## ১. ইনস্টল

1. TradingView → Pine Editor খুলুন।
2. `SMC.txt`-এর পুরো কোড কপি করে পেস্ট করুন।
3. **Add to chart** চাপুন। স্ক্রিপ্টের নাম: **SMC Suite**।
4. প্রথমবার চার্টে প্রায় ২০-৩০ ক্যান্ডেল পর থেকে স্ট্রাকচার / সিগন্যাল আসা শুরু হবে (পিভট কনফার্ম হতে ৫ বার লাগে)।

**কোন চার্টে চলে:** Forex, Gold, Silver, Crypto, Index — যেকোনো। **টাইমফ্রেম:** ১m থেকে D পর্যন্ত। সবচেয়ে ভালো কাজ করে ৫m / ১৫m ইন্ট্রাডে-তে।

---

## ২. চার্টে কী কী দেখবেন

### ২.১ স্ট্রাকচার লেবেল ও লাইন

| চার্টে | মানে | কী করবেন |
|---|---|---|
| **BOS▲ ·2FVG** (সবুজ) | ট্রেন্ডের দিকে স্ট্রাকচার ব্রেক, ডিসপ্লেসমেন্ট সহ, লেগে ২টা FVG | ট্রেন্ড কন্টিনিউয়েশন — পুলব্যাকে এন্ট্রি খুঁজুন |
| **BOS▲** (ধূসর) | ব্রেক হয়েছে, ক্যান্ডেল শক্ত, কিন্তু লেগে FVG নেই | দুর্বল, সাবধান |
| **BOS▲ weak** (ধূসর, শুধু "Label weak BOS" অন থাকলে) | ক্লোজ ব্রেক করেছে কিন্তু ক্যান্ডেলে ডিসপ্লেসমেন্ট নেই | স্ট্রাকচার বদলায়নি; ৩ বারের মধ্যে দ্বিতীয় ক্লোজ লাগবে |
| **iBOS▲** (ধূসর, শুধু "All events") | বেয়ার ট্রেন্ডের ভেতরে একটা Lower High ভাঙল — ইন্টারনাল ব্রেক | ট্রেন্ড বদলায়নি, এটা ট্র্যাপ হতে পারে |
| **CHoCH▲ / CHoCH✕▲** (সবুজ) | ট্রেন্ডের বিপরীতে protected swing ক্লোজ ব্রেক = ট্রেন্ড রিভার্সাল। ✕ = আগে লিকুইডিটি সুইপ হয়েছিল (শক্তিশালী) | রিভার্সাল সেটআপ খুঁজুন (RCB / QM / M45★ / M68) |
| **CHoCH?▲** (ধূসর) | CHoCH হয়েছে কিন্তু লেগে FVG নেই (fake) | ট্রেড করবেন না |
| **CISD▲★** | ক্যান্ডেল সিরিজের ওপেন ক্লোজ করে ভেঙেছে, আগে সুইপ হয়েছে — আর্লি রিভার্সাল | ★ = ২+ reliability, M46 সেটআপের ভিত্তি |
| ড্যাশ লাল/সবুজ লাইন | Major High / Major Low = **protected swing** — এটা ভাঙলে CHoCH | SL এর রেফারেন্স |
| **SWEEP✕ PDH** | PDH (আগের দিনের হাই) সুইপ হয়ে ক্লোজ ফিরে এসেছে | রিভার্সাল কনটেক্সট |
| **RUN — avoid** | লেভেল সোজা ভেঙে চলে গেছে (acceptance) | ফেড করবেন না |

### ২.২ জোন (বক্স)

| জোন | মানে |
|---|---|
| **OB▲ / OB▼** | Order Block — ডিসপ্লেসমেন্ট ক্যান্ডেলের আগের শেষ বিপরীত ক্যান্ডেল। **★** = তার আগে লিকুইডিটি সুইপ হয়েছে (high-probability)। T1/T1b/T2/G2 = ক্যান্ডেল টাইপ |
| **BRK▲ / BRK▼** (বেগুনি) | Breaker — OB ক্লোজ করে ভাঙার পর উল্টো দিকে কাজ করে |
| **RCB** (নীল-সবুজ) | Reclaimed Block — CHoCH লেগের অরিজিন ক্যান্ডেল |
| **RJB** (কমলা) | Rejection Block — বড় উইক |
| **QM** (গোলাপি) | Quasimodo |
| **KL / KL★** (ধূসর) | Key Level — স্কোর করা পিভট জোন (KL★ = ৪+ ক্রাইটেরিয়া) |
| **⇈PROP** | Propulsion Block — জোন দুইবার কাজ করেছে, তৃতীয় ট্যাপ = এন্ট্রি |
| **⚠SWEEP REQ** | জোন ২+ বার টাচ হয়েছে — সুইপ ছাড়া সরাসরি রিভার্সাল নিষেধ |
| **IDM✓** | Inducement সুইপ হয়ে গেছে — জোন এখন "ক্লিন" |
| **★★** | near-miss তারপর সুইপ — সবচেয়ে শক্তিশালী ফর্ম |
| ড্যাশ ধূসর বক্স | weak / invalid / broken |
| **FVG বক্স** (বর্ডারহীন) | Fair Value Gap; ধূসর = mitigated |

### ২.৩ লিকুইডিটি লাইন

| লাইন | মানে |
|---|---|
| ডটেড লাল / সবুজ | BSL / SSL — সুইং হাই / লো এর লিকুইডিটি |
| মোটা ড্যাশ কমলা **POOL·EQH** | Equal Highs / Lows — ২+ টাচ, সবচেয়ে গুরুত্বপূর্ণ |
| ধূসর **PDH / PDL / PWH / PWL** | আগের দিন / সপ্তাহের হাই-লো |
| **SESH / SESL** | Asia সেশনের হাই-লো (London-এ সুইপ হওয়ার টার্গেট) |

### ২.৪ সিগন্যাল লেবেল

```
▲▲ M37 A+12 · 2.8R
```

| অংশ | মানে |
|---|---|
| **▲▲ / ▲ / ·** | গ্রেড A+ / A / B |
| **M37** | কোন মডিউল ফায়ার করেছে (লেবেলে মাউস রাখলে tooltip-এ পুরো ব্যাখ্যা) |
| **A+12** | গ্রেড + স্কোর (tier×2 + confluence) |
| **2.8R** | TP1 পর্যন্ত Risk:Reward |
| **ধূসর লেবেল** | HTF / ট্রেন্ডের বিপরীতে সিগন্যাল (⚠) — সাবধান |

সিগন্যাল আসলে সাথে **ট্রেড লাইন** আঁকে: নীল = Entry, লাল ড্যাশ = SL, সবুজ ড্যাশ = TP1 / TP2 / TP3।

### ২.৫ ইনফো প্যানেল (নিচে ডানে)

| সারি | কী দেখায় |
|---|---|
| Chart / HTF | চার্ট TF → HTF TF |
| LTF structure | BULLISH / BEARISH / RANGE |
| HTF bias | BULL / BEAR / NEUTRAL; ⚠ = LTF-HTF মিসম্যাচ |
| Regime | ট্রেন্ড + range কিনা |
| Last event | শেষ BOS / CHoCH / CISD / SWEEP, কত বার আগে |
| Move phase | IMPULSIVE / RETRACEMENT / RANGE |
| Active zone | এখন প্রাইস কোন জোনে (Bull ও Bear আলাদা) |
| Arrival | জোনে আসার মুভ WEAK ✅ (ভালো) না STRONG ❌ (রিভার্সাল সন্দেহজনক) |
| Nearest BSL / SSL | ওপরে / নিচে সবচেয়ে কাছের লিকুইডিটি |
| 4-factor | HTF · trend · departure/arrival · liquidity — ✅❌ |
| Signal | বর্তমান সেরা সিগন্যাল |
| PD array | লেগের কত % — premium (sell) / discount (buy) / beyond leg |
| Session | London / NY / Asia / বাইরে |

---

## ৩. একটা ট্রেড কীভাবে নেবেন (ওয়ার্কফ্লো)

1. **HTF bias দেখুন** (প্যানেল বা ব্যাকগ্রাউন্ড টিন্ট)। BULL হলে লং-এ ফোকাস, BEAR হলে শর্ট। NEUTRAL হলে দুই দিকই খোলা।
2. **লিকুইডিটি ম্যাপ দেখুন**: প্রাইসের ওপরে-নিচে POOL / PDH / PDL / SESH কোথায়।
3. **সুইপের অপেক্ষা করুন**: `SWEEP✕` লেবেল — বিশেষ করে POOL / PD / SES লেভেলে।
4. **স্ট্রাকচার কনফার্ম**: সুইপের পর `CHoCH✕` (রিভার্সাল) বা `BOS ·nFVG` (কন্টিনিউয়েশন)।
5. **POI-তে রিট্রেস**: OB★ / BRK / RCB / FVG-এ প্রাইস ফিরলে সিগন্যাল লেবেল আসবে।
6. **সিগন্যাল যাচাই**:
   - গ্রেড A বা A+ (স্কোর ≥ 8)
   - লেবেল ধূসর নয় (HTF সাথে আছে)
   - 4-factor-এ ৩-৪টা ✅
   - PD array: লং-এ discount, শর্ট-এ premium
   - Session: London / NY
7. **এন্ট্রি**: সিগন্যাল ক্যান্ডেলের ক্লোজে (IMMEDIATE) বা কনফার্মেশনের পর (CONFIRMED মোড, নিচে দেখুন)।
8. **SL / TP**: ট্রেড লাইন অনুযায়ী। TP1-এ আংশিক প্রফিট, TP2 / TP3 লিকুইডিটি লেভেল।

**যা এড়িয়ে চলবেন:** `RUN — avoid`, `⚠M41 NO TRADE`, `⚠SWEEP REQ` জোনে সুইপ ছাড়া রিভার্সাল, `CHoCH?` (fake), Arrival = STRONG ❌।

---

## ৪. সেটিংস — গ্রুপ অনুযায়ী

### 1 · General
- **Swing length** (5): পিভট সাইজ। ১m-এ 5, ১৫m+ এ 3-5।
- **Label density**: `Signals only` (পরিষ্কার চার্ট) / `Key events` (+ CHoCH, BOS, major sweep) / `All events` (সব, ডিবাগ)।
- **Setup master mode**: `Core only` = কিউরেটেড ডিফল্ট মডিউল; `Custom` = নিজে টগল।

### 3 · Structure (L1)  ← v8.3 নতুন
- **Structure needs displacement**: `Candle` (ডিফল্ট) — ব্রেকিং ক্যান্ডেলের body ≥ 50% ও রেঞ্জ ≥ 0.8 ATR না হলে স্ট্রাকচার বদলাবে না। `Off` = পুরোনো আচরণ।
- **Weak break follow-through window** (3): ডিসপ্লেসমেন্ট ছাড়া ব্রেক কত বারের মধ্যে দ্বিতীয় ক্লোজ পেলে BOS হবে।
- **Failed follow-throughs → RANGE** (2): পরপর কয়টা ব্রেক ফেল করলে RANGE ধরবে।
- **CISD only after a qualified sweep**: অন রাখুন; বন্ধ করলে অনেক CISD আসবে।

### 5 · Liquidity (L3)
- **Sweep arms setups when the level is**: `Major only` (ডিফল্ট: POOL / PD / PW / SES) বা `Include external` (৫০-বার হাই/লো-ও ধরবে — ১m-এ বেশি সিগন্যাল)।
- **PDH/PDL, PWH/PWL**: অন রাখুন।

### 6 · Zones (L4)
- **OB: high-probability only**: অন করলে শুধু সুইপের পরের OB★ থাকবে (কম, ভালো)।
- **Count UNSCORED pivot wick zones as tradable**: অফ রাখুন।

### 7 · HTF (L5)
- **HTF pairing**: `Conservative` (5m→1h, 15m→4h) / `Aggressive` / `Manual`।
- **HTF bias gate**: `WARN` (ডিফল্ট: বিপরীত সিগন্যাল ধূসর হয়, −1 পয়েন্ট) / `STRICT` (ব্লক) / `OFF`।

### 8 · Setup filters (L6)  ← v8.3 নতুন
- **Zone entry trigger**:
  - `IMMEDIATE` — জোনে রিভার্সাল ক্যান্ডেল হলেই সিগন্যাল (বেশি সিগন্যাল, আগে এন্ট্রি)।
  - `CONFIRMED` — রিভার্সাল ক্যান্ডেলের হাই ক্লোজ করে ভাঙলে বা জোন থেকে দূরে নতুন FVG হলে সিগন্যাল (কম সিগন্যাল, বেশি নির্ভরযোগ্য)। **নতুন ব্যবহারকারীর জন্য এটা সুপারিশ।**
  - **confirm within** (8): কত বারের মধ্যে কনফার্ম হতে হবে।

### 9a · Premium / Discount + Sessions
- **Session timezone**: `UTC` ডিফল্ট। Binance / crypto = UTC ঠিক আছে। Forex ব্রোকারে London/NY ঠিকমতো না মিললে `Europe/London` দিন।
- Asia 0000-0700, London 0700-1000, NY 1200-1500 (UTC)।
- **Only signal inside a killzone**: অন করলে London / NY-র বাইরে সিগন্যাল আসবে না।
- **Block longs in premium / shorts in discount**: হার্ড ফিল্টার, ডিফল্ট অফ।

### 14 · Trade (L7)
- **Min R:R** (2.0) / **Max R:R** (6.0): TP1 এই রেঞ্জে না থাকলে সিগন্যাল হাইড।
- **Require a REAL target**: অন — TP1 আসল জোন / FVG / লিকুইডিটিতে হতে হবে।
- **Min score to show** (6), **A+ ≥** (11), **A ≥** (8): গ্রেড থ্রেশহোল্ড। কম সিগন্যাল চাইলে Min score 8 করুন।
- **Min bars between signals** (10): একই মুভে বারবার সিগন্যাল আটকায়।
- **M10 entry mode**: `IMMEDIATE` / `RETEST` (সুইপ লেভেলে লিমিট) / `BOTH`।

### 11 / 13 / 15 · Setups (মডিউল টগল)
সবচেয়ে গুরুত্বপূর্ণ (tier 4): **M37** Inducement block, **M41** Sweep + FVG, **M42** HP S&D, **M45★** Sweep→CHoCH→OB, **M54** Smart S&D trap, **M68** HTF sweep → LTF CHoCH, **M73** Propulsion Block।
Tier 3: M10 Sweep reversal, M36, M39, M46 CISD, M33, M51, M09।
বাকিগুলো tier 1-2 — ডিফল্টে অনেকগুলো অফ।

---

## ৫. সুপারিশকৃত সেটিংস

| উদ্দেশ্য | সেটিং |
|---|---|
| **স্ক্যাল্প ১m-৫m ক্রিপ্টো** | Swing 5 · HTF Conservative · Zone entry CONFIRMED · Min score 7 · Sweep = Major only · Timezone UTC |
| **১৫m-১h ফরেক্স / গোল্ড** | Swing 4 · HTF Conservative · Zone entry IMMEDIATE বা CONFIRMED · Min score 8 · Timezone Europe/London · Only signal inside killzone = ON |
| **কম সিগন্যাল, উচ্চ মান** | Setup master = Core only · OB high-probability only = ON · HTF gate = STRICT · Min score 9 |
| **শেখার জন্য / সব দেখতে** | Label density = All events · Candle pattern tags = ON · Legend = ON |

---

## ৬. অ্যালার্ট

চার্টে ⏰ → Condition: **SMC Suite** → নিচের যেকোনোটি:

| অ্যালার্ট | কখন |
|---|---|
| Setup: LONG signal / SHORT signal | সিগন্যাল লেবেল আসলে (বার ক্লোজে) |
| Setup: Any A+ signal | শুধু A+ |
| Warning: Counter-HTF signal | HTF-এর বিপরীতে সিগন্যাল |
| Structure: BOS / CHoCH (Real) / CISD | স্ট্রাকচার ইভেন্ট |
| Liquidity: Sweep detected | সুইপ |
| Zone: New HP OB / Propulsion Block / OB 50% tapped | জোন ইভেন্ট |

সব অ্যালার্ট **বার ক্লোজে** কনফার্ম হয় — চার্টে লেবেল যা, অ্যালার্ট তাই। "Once per bar close" ফ্রিকোয়েন্সি দিন।

ডায়নামিক মেসেজ (alert() function) চাইলে অ্যালার্ট তৈরির সময় "Any alert() function call" বাছুন — মেসেজে Entry / SL / TP / Score থাকবে।

---

## ৭. ডেটা উইন্ডো (ডিবাগ)

Data Window-এ (চার্টের ডানে) দেখা যায়: long / short score, zones, liq levels, labels/lines/boxes drawn (৫০০-র নিচে থাকতে হবে), `S4 · internal break`, `S4 · weak break`, `S4 · failed follow-throughs`, `S2 · leg origin`, PD %, displacement quality।

---

## ৮. সাধারণ সমস্যা

| সমস্যা | কারণ / সমাধান |
|---|---|
| সিগন্যাল আসছে না | Min score কমান (6) · HTF gate WARN করুন · Zone entry IMMEDIATE করুন · "Only signal inside killzone" অফ করুন · Setup master = Custom |
| খুব বেশি সিগন্যাল | Zone entry CONFIRMED · Min score 8+ · OB high-probability only ON · Sweep = Major only |
| HTF bias সবসময় NEUTRAL | HTF-এ এখনো প্রথম BOS হয়নি — চার্টে আরও হিস্টরি লোড হতে দিন, বা HTF Aggressive করুন |
| Session ভুল দেখাচ্ছে | Session timezone বদলান (Forex → Europe/London) |
| "beyond leg (expansion)" বেশি | ট্রেন্ডে নতুন হাই/লো হলে স্বাভাবিক — PD স্কোর নিউট্রাল থাকে |
| লেবেল ওভারল্যাপ | Label density = Signals only · Min bars between labels বাড়ান |
| Object limit / স্লো | Max labels / lines কমান · FVG boxes বা S/R wick zones অফ |

---

## ৯. মনে রাখার নিয়ম

- **সুইপ → ডিসপ্লেসমেন্ট → স্ট্রাকচার → POI → এন্ট্রি** — এই ক্রম ছাড়া সিগন্যাল দুর্বল।
- ধূসর লেবেল = কনটেক্সট বিপরীত। A+ হলেও অর্ধেক সাইজ।
- `⚠SWEEP REQ` জোনে সুইপ না হলে ঢুকবেন না।
- একই মুভে দুইবার এন্ট্রি না — `Min bars between signals` সে জন্যই।
- ইন্ডিকেটর সিদ্ধান্ত সাপোর্ট করে, সিদ্ধান্ত নেয় না। ব্যাকটেস্ট ও রিপ্লে করে নিজের পেয়ারে যাচাই করুন।

---

সংস্করণ: v8.3.0 · কোড: `SMC.txt` · পরিবর্তনের বিবরণ: `IMPROVEMENT_PLAN_v8.3.md`, অডিট: `FORENSIC_AUDIT_SMC_v8.2.1.md`
