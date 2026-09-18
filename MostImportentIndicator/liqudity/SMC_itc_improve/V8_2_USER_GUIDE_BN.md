# SMC / ICT / CRT Suite v8.2.1 — ইউজার ম্যানুয়াল

**ফাইল:** `SMC_Suite_v8.2.1.pine` (ইন্ডিকেটর) · `SMC_Suite_v8.2.1_strategy.pine` (ব্যাকটেস্ট)
**প্ল্যাটফর্ম:** TradingView · Pine v6

---

## ০. এক নজরে — ৫ মিনিটে শুরু

1. TradingView → **Pine Editor** → `SMC_Suite_v8.2.1.pine`-এর সব কোড কপি-পেস্ট → **Add to chart**
2. সেটিংসে হাত দেবেন না। ডিফল্ট ইচ্ছে করেই রক্ষণশীল।
3. চার্টে দেখবেন:
   - **রঙিন লেবেল** (▲▲ / ▲ / ·) = ট্রেড সিগন্যাল
   - **বক্স / অনুভূমিক ব্যান্ড** = জোন (OB, KL, RJB, RCB, QM)
   - **ডটেড লাইন** = লিকুইডিটি লেভেল
   - **নিচে-ডানে টেবিল** = ইনফো প্যানেল (মার্কেটের বর্তমান অবস্থা)
4. লেবেলে **মাউস রাখলে** পুরো ট্রেড প্ল্যান দেখাবে — এন্ট্রি, SL, TP1/TP2/TP3 (R সহ), স্কোর।
5. প্রথম দিন কোনো ট্রেড নেবেন না। শুধু দেখুন সিগন্যালগুলো কোথায় আসে।

> **সতর্কতা:** এটা অটো-ট্রেডিং সিস্টেম না। এটা একটা **পড়ার যন্ত্র** — কোথায় লিকুইডিটি আছে, স্ট্রাকচার কী বলছে, জোন কোথায়। সিদ্ধান্ত আপনার।

---

## ১. ইনস্টল

| ধাপ | কাজ |
|---|---|
| ১ | চার্ট খুলুন → নিচে **Pine Editor** ট্যাব |
| ২ | **Open → New blank indicator** |
| ৩ | ভেতরের সব মুছে `SMC_Suite_v8.2.1.pine`-এর পুরো কনটেন্ট পেস্ট করুন |
| ৪ | **Save** (একটা নাম দিন) → **Add to chart** |
| ৫ | চার্টের উপরে ইন্ডিকেটরের নামের পাশে **⚙ (গিয়ার)** = সেটিংস |

**টাইমফ্রেম:** ১ মিনিট থেকে ডেইলি — সবখানে চলে। HTF নিজে থেকে বেছে নেয় (§৬.৭)।

---

## ২. চার্টে কী দেখছেন — ভিজ্যুয়াল অভিধান

> চার্টের উপরের লেজেন্ড টেবিলটা **ডিফল্টে বন্ধ** (প্রাইস অ্যাকশন ঢেকে ফেলত)। দরকার হলে
> **`10 · Show` → Legend** টিক দিন। নিচের টেবিলটাই সেই লেজেন্ডের পূর্ণ রূপ।

### ২.১ সিগন্যাল লেবেল

```
▲▲ M37 A+8 · 3.2R
│  │   │  │    └─ TP1 পর্যন্ত রিস্ক-রিওয়ার্ড
│  │   │  └────── কনফ্লুয়েন্স স্কোর (সংখ্যা)
│  │   └───────── গ্রেড: A+ (≥6) · A (4–5) · B (<4)
│  └───────────── কোন মডিউল সিগন্যাল দিল
└──────────────── ▲▲ = A+ লং · ▲ = A লং · · = B লং
                  ▼▼ / ▼ = শর্ট (ক্যান্ডেলের উপরে বসে)
```

- **ধূসর রঙের লেবেল** = HTF বা ট্রেন্ডের বিপরীতে (⚠ চিহ্নিত) — সাবধান
- লেবেলে **হোভার** করলে টুলটিপে: নোট, এন্ট্রি, SL, TP1/2/3 (প্রতিটা R সহ), স্কোর

### ২.২ স্ট্রাকচার মার্কার

| চিহ্ন | মানে |
|---|---|
| `BOS▲ ·2FVG` | Break of Structure, ভেতরে ২টা imbalance — **শক্তিশালী** |
| `BOS▲ weak` | BOS কিন্তু imbalance নেই — **ট্রেড করার মতো না** |
| `CHoCH▲` | Change of Character — ট্রেন্ড উল্টাচ্ছে (ভেতরে FVG আছে = আসল) |
| `CHoCH?▲` | FVG নেই — **ভুয়া CHoCH, ট্রেড করবেন না** |
| `CHoCH✕▲` | ✕ = ঠিক আগে লিকুইডিটি সুইপ হয়েছে — **শক্তিশালী ভ্যারিয়েন্ট** |
| `CISD▲` | Change in State of Delivery — আগাম রিভার্সাল সংকেত |
| `CISD▲★` | ★ = ≥২টা নির্ভরযোগ্যতা শর্ত মিলেছে — উঁচু মানের |
| `SWEEP✕ BSL` | লিকুইডিটি সুইপ হলো — রিভার্সাল কনটেক্সট |
| `RUN — avoid` | লেভেল ভেঙে **চলে গেছে**, সুইপ না — ফেড করবেন না |
| `PB✓` | বৈধ পুলব্যাক কনফার্ম (ডিফল্টে বন্ধ) |

**লাইনের ভাষা:** সলিড = বৈধ · ড্যাশড ধূসর = দুর্বল/ভুয়া/সুইপ · ডটেড = CISD

### ২.৩ জোন (বক্স)

| ট্যাগ | কী |
|---|---|
| `OB▲` / `OB▼` | Order Block (সাপ্লাই/ডিমান্ড) |
| `OB▲★` | ★ = হাই-প্রবাবিলিটি — তৈরির আগে লিকুইডিটি হান্ট হয়েছে |
| `OB▲ T1/T2/G1/G2` | OB-এর গঠন-ধরন |
| `BRK▲` | Breaker Block — ভাঙা OB উল্টো দিকে কাজ করছে |
| `RCB▲` | Reclaimed Block |
| `RJB▲` | Rejection Block (উইক জোন) |
| `QM▲` | Quasimodo |
| `KL` / `KL★` | Key Level — স্কোর ৩ / ৪+ |
| `S` / `R` | আনস্কোরড পিভট উইক জোন (ডিফল্টে আঁকা হয় না) |

**জোনের সাফিক্স:**

| সাফিক্স | মানে |
|---|---|
| ` FLIP` | সাপোর্ট↔রেজিস্ট্যান্স উল্টে গেছে |
| ` ⚠SWEEP REQ` | ২+ বার টাচ — **সরাসরি রিভার্সাল নিষিদ্ধ**, আগে সুইপ লাগবে |
| ` weak` | নিশ্চিতকারী ক্যান্ডেল জোন ছাড়াতে পারেনি |
| ` ?` | এখনো কনফার্ম হয়নি |
| ` IDM✓` | Inducement (ভেতরের লিকুইডিটি) সুইপ হয়ে গেছে — ভালো লক্ষণ |
| ` ⇈PROP` | Propulsion Block — জোনটা দু'বার নিজের আগ্রহ প্রমাণ করেছে |
| ` ★★` | near-miss তারপর সুইপ — সবচেয়ে শক্তিশালী রূপ |

> **বর্ডার মোটা** = KL স্কোর যত বেশি। **ড্যাশড ধূসর বক্স** = দুর্বল/ভাঙা — এড়িয়ে যান।

### ২.৪ লিকুইডিটি লাইন

| চেহারা | কী |
|---|---|
| পাতলা ডটেড | BSL / SSL (সাধারণ সুইং হাই/লো) |
| মোটা ড্যাশড কমলা | `POOL·` — ২+ বার টাচ, EQH/EQL |
| ধূসর | PDH/PDL (আগের দিন) · PWH/PWL (আগের সপ্তাহ) |
| `SESH` / `SESL` | এশিয়া সেশনের হাই/লো — লন্ডন ওপেনে বসে |
| `·ext` | রেঞ্জের প্রান্তে (external liquidity) |

### ২.৫ FVG ও ট্রেড লাইন

- **বর্ডারহীন হালকা বক্স** = Fair Value Gap (imbalance)
- **ধূসর FVG** = mitigated (ডিফল্টে মুছে যায়)
- সিগন্যালের সাথে: **নীল সলিড** = এন্ট্রি · **লাল ড্যাশড** = SL · **সবুজ ড্যাশড ×৩** = TP1/TP2/TP3
- **নীল লাইন সেট** (সলিড/ডটেড/ড্যাশড) = HTF ক্যান্ডেলের High/Open/Close/Low
- **ব্যাকগ্রাউন্ড হালকা সবুজ/লাল** = HTF বায়াস

---

## ৩. ইনফো প্যানেল — সারি ধরে ধরে

নিচে-ডানে ১৪ সারির টেবিল। **এটাই আপনার ড্যাশবোর্ড।**

| সারি | কী বলছে | কীভাবে ব্যবহার করবেন |
|---|---|---|
| **Chart / HTF** | `1 → 15` = ১ মিনিট চার্ট, ১৫ মিনিট HTF | HTF ঠিক আছে কিনা দেখুন |
| **LTF structure** | BULLISH / BEARISH / RANGE | RANGE-এ ট্রেন্ড-ফলোয়িং সেটআপ কাজ করে না |
| **HTF bias** | BULL / BEAR / NEUTRAL · `⚠` = LTF-এর সাথে বিরোধ | ⚠ থাকলে সাইজ কমান |
| **Wyckoff** | MARKUP / MARKDOWN / ACCUMULATION / DISTRIBUTION / MANIPULATION | প্রেক্ষাপট |
| **Last event** | শেষ স্ট্রাকচারাল ঘটনা + কত বার আগে | তাজা ঘটনার পরে সেটআপ বেশি বিশ্বাসযোগ্য |
| **Move phase** | IMPULSIVE / RETRACEMENT | RETRACEMENT = পুলব্যাক এন্ট্রির সময় |
| **Active zone** | এখন প্রাইস কোন জোনে · fresh / touched N · ⚠SWEEP REQ | `—` মানে কোনো জোনে নেই |
| **Arrival** | WEAK ✅ / STRONG ❌ | **দুর্বল আগমন = ভালো রিভার্সাল**। STRONG মানে জোন ভাঙার সম্ভাবনা |
| **Nearest BSL** | উপরের নিকটতম বাই-সাইড লিকুইডিটি | লং-এর স্বাভাবিক টার্গেট |
| **Nearest SSL** | নিচের নিকটতম সেল-সাইড লিকুইডিটি | শর্টের স্বাভাবিক টার্গেট |
| **4-factor** | `✅✅✅❌` = HTF · trend · departure/arrival · liquidity | ৪টাই ✅ = সেরা মানের |
| **Signal** | এই বারে কোন মডিউল + স্কোর + গ্রেড | `—` = এখন কিছু নেই |
| **PD array** | রেঞ্জে প্রাইসের অবস্থান — premium / discount / equilibrium / outside swing | **discount-এ কিনুন, premium-এ বেচুন** |
| **Session** | Asia / London / NY / — | কিলজোনে সিগন্যালের মান বেশি |

**"outside swing (expansion)"** মানে প্রাইস সর্বশেষ সম্পূর্ণ সুইং-এর বাইরে — মানে এক্সপ্যানশন
চলছে, premium/discount-এর হিসাব এখন অর্থহীন, তাই স্কোরে কোনো প্রভাব পড়ছে না।

---

## ৪. সেটিংস — গ্রুপ ধরে ধরে

> **নোট:** গ্রুপের নম্বর আর TradingView-তে দেখানোর ক্রম এক না। **`14 · Trade (L7)`**
> তালিকার একদম **শেষে** আসে (`16 · S–AB parameters`-এর পরে)। খুঁজে না পেলে নিচে স্ক্রল করুন।

### `1 · General`

| ইনপুট | ডিফল্ট | কী করে · কখন বদলাবেন |
|---|---|---|
| ATR length | 14 | সব দূরত্বের মাপকাঠি। হাত দেওয়ার দরকার নেই |
| Swing length (each side) | 5 | পিভট কত কড়া। **বাড়ালে** কম কিন্তু বড় স্ট্রাকচার। নয়েজি মার্কেটে 7–8 |
| Max labels / Max lines | 200 / 100 | ড্রয়িং বাজেট। চার্ট ভারী লাগলে কমান |
| Min bars between labels | 6 | একই পাশে পরপর লেবেলের ফাঁক। লেবেল ওভারল্যাপ করলে বাড়ান |
| **Label density** | Signals only | `Signals only` = শুধু সেটআপ · `Key events` = + আসল CHoCH, শক্ত BOS, বড় সুইপ · `All events` = সব (১ মিনিটে অপাঠ্য) |
| **Setup master mode** | Custom (toggles) | `Core only` = কিউরেটেড ডিফল্ট, টগল উপেক্ষা করে · `All on` = ৫০টা মডিউল (ভীষণ ভিড়) · `All off` = শুধু লেয়ার, সিগন্যাল নেই |

> **পরামর্শ:** শুরুতে **`Core only`** দিন। নিজের এজ বোঝার পরে `Custom`-এ ফিরুন।

### `2 · Candle (L0)` — ক্যান্ডেল প্যাটার্ন সংজ্ঞা

পিন বার, ডোজি, এনগাল্ফিং, IFC, ম্যানিপুলেটিভ ক্যান্ডেল — সবের থ্রেশহোল্ড।
**সাধারণত হাত দেবেন না।** খুব কম/বেশি রিভার্সাল ক্যান্ডেল ধরা পড়লে:

- `Pin bar wick ≥ N × body` **2.0** → বাড়ালে কম কিন্তু খাঁটি পিন বার
- `Pin bar wick/range min` **0.55** → একই প্রভাব
- `Large range × ATR` **1.5** → কোন ক্যান্ডেলকে "বড়" বলবে

### `3 · Structure (L1)`

| ইনপুট | ডিফল্ট | মানে |
|---|---|---|
| Bars without BOS/CHoCH → RANGE | 20 | এতবার কিছু না হলে ট্রেন্ড = RANGE |
| Wyckoff range lookback / width | 30 / 1.5 | Wyckoff ফেজ নির্ণয় |

### `4 · FVG / Strength (L2)`

| ইনপুট | ডিফল্ট | মানে |
|---|---|---|
| Min FVG height × ATR | 0.10 | এর চেয়ে ছোট গ্যাপ গোনা হয় না। **বাড়ালে** কম কিন্তু অর্থপূর্ণ FVG |
| FVG mitigation mode | TOUCH | `TOUCH` = ছুঁলেই শেষ · `50%` = অর্ধেক · `FULL` = পুরো ভরাট |
| Max FVGs tracked | 40 | মেমোরি বাজেট |
| Drop mitigated FVG after N bars | 300 | পুরনো ভরাট গ্যাপ মুছে ফেলা |
| **STRONG** min body efficiency | 0.55 | মুভকে "শক্তিশালী" বলার শর্ত |
| STRONG max mixed ratio | 0.35 | কত বার রঙ বদলেছে (কম = পরিষ্কার মুভ) |
| STRONG min speed | 0.35 | প্রতি বারে কত ATR এগিয়েছে |

> এই তিনটা মিলে ঠিক করে কোন BOS "displacement" আর কোনটা দুর্বল। **সব OB এখান থেকেই জন্মায়** —
> কড়া করলে OB কমবে কিন্তু মান বাড়বে।

### `5 · Liquidity (L3)`

| ইনপুট | ডিফল্ট | মানে |
|---|---|---|
| Equal H/L tolerance × ATR | 0.10 | কতটা কাছে হলে EQH/EQL ধরে মিলিয়ে দেবে |
| Touch tolerance × ATR | 0.15 | লেভেল "ছোঁয়া" হয়েছে ধরার দূরত্ব |
| Touch cooldown (bars) | 3 | একই টাচ বারবার গোনা আটকায় |
| External liquidity lookback | 50 | `·ext` ট্যাগের রেঞ্জ |
| **PDH/PDL · PWH/PWL** | দুটোই চালু | আগের দিন / সপ্তাহের হাই-লো |
| RUN min body ratio / close beyond | 0.60 / 0.25 | "ভেঙে চলে গেছে" বনাম "সুইপ" আলাদা করে |
| SWEEP min wick ratio | 0.40 | সুইপ ক্যান্ডেলের উইক কত লম্বা লাগবে |
| Failed-close window | 2 | ব্রেকের পর কত বার অপেক্ষা করে রায় দেবে |
| Hidden liquidity: candles / wick | 3 / 0.35 | পরপর একই দিকের লম্বা উইক = লুকানো লিকুইডিটি |
| Max liquidity levels | 30 | বাজেট। ভরে গেলে **পুল/PD/PW/সেশন লেভেল শেষে বাদ যায়** |

### `6 · Zones (L4)`

| ইনপুট | ডিফল্ট | মানে |
|---|---|---|
| Max zones tracked | 30 | SR-এর আলাদা বাজেট (মোট ৬০ পর্যন্ত) |
| Drop untouched zone after N bars | 500 | কখনো ছোঁয়া হয়নি এমন জোন মুছে ফেলা |
| Zone max height × ATR | 3.0 | ফ্ল্যাশ-উইক থেকে বিশাল জোন হওয়া আটকায় |
| OB V5: sweep within N bars | 10 | OB-এর আগে লিকুইডিটি হান্ট হয়েছে কিনা (★ পাওয়ার শর্ত) |
| Rejection block wick / confirm bars | 0.50 / 15 | RJB তৈরির শর্ত |
| QM max bars after CHoCH | 60 | Quasimodo গঠনের সময়সীমা |
| Key level lookback / **min criteria** | 50 / **3** | KL স্কোরিং। **৩ = KL, ৪ = KL★** |
| Count UNSCORED pivot wick zones | **বন্ধ** | চালু করলে প্রতিটা পিভট "জোন" হয়ে যায় → প্রায় প্রতি বারে সিগন্যাল। **বন্ধ রাখুন** |
| OB: high-probability only | বন্ধ | চালু করলে শুধু লিকুইডিটি-হান্ট OB তৈরি হবে (সংখ্যা অনেক কমবে) |
| Reclaimed: enforce 50% fib | চালু | RCB-র মান রক্ষা করে |
| Key level volume criterion | বন্ধ | চালু করলে ভলিউমও KL স্কোরে গোনা হবে (ফরেক্সে ভলিউম অনির্ভরযোগ্য) |
| Trendline zone ± × ATR | 0.30 | ট্রেন্ডলাইনের কাছাকাছি গণ্য হওয়ার ব্যান্ড |
| Trendline anchor | Wick | `Body` দিলে স্পাইক উইক উপেক্ষা করবে |
| Bars spent at level before break | 5 | IDM-1 / আসল ব্রেকআউট নিয়ম (M22) |
| **Propulsion** window / size | 10 / 0.8 | জোন থেকে আবার imbalance নিয়ে বেরোনোর শর্ত |
| M64: trendline needs confirming touch | বন্ধ | চালু করলে ট্রেন্ডলাইন কম কিন্তু নির্ভরযোগ্য |

### `7 · HTF (L5)`

| ইনপুট | ডিফল্ট | মানে |
|---|---|---|
| **HTF pairing** | Conservative | `Conservative`: 5m→1h, 15m→4h · `Aggressive`: 5m→30m, 15m→1h · `Manual`: নিজে দিন |
| Manual HTF | 60 | উপরেরটা Manual হলে কার্যকর |
| **HTF bias gate** | **WARN** | `OFF` = ফিল্টার নেই · `WARN` = সিগন্যাল আসবে কিন্তু ⚠ + ১ স্কোর কাটা · `STRICT` = বিপরীত সিগন্যাল পুরো ব্লক |
| **Trend the gate reads** | Entering bar | `Entering bar` = বার শুরুর ট্রেন্ড (সঠিক) · `This bar` = পুরনো আচরণ, BOS বারে ফিল্টার কাজ করত না |
| HTF pivot length | 3 | HTF স্ট্রাকচারের সংবেদনশীলতা |
| HTF sweep valid for N HTF bars | 3 | HTF সুইপ কত HTF বার পর্যন্ত "তাজা" |
| HTF candle levels shown | 3 | কয়টা HTF ক্যান্ডেলের O/H/L/C আঁকবে |

> **কেন STRICT ডিফল্ট না:** LTF BEARISH + HTF BULL হলে STRICT **দুই দিকই** ব্লক করে
> (লং ট্রেন্ডে আটকায়, শর্ট বায়াসে আটকায়) — ইঞ্জিন পুরো চুপ হয়ে যায় ঠিক তখনই যখন
> বিরোধটা সবচেয়ে বেশি তথ্যবহুল। WARN সিগন্যাল দেখায়, ⚠ দেয়, স্কোর কাটে।

### `8 · Setup filters (L6)`

| ইনপুট | ডিফল্ট | মানে |
|---|---|---|
| Volume SMA length / volHigh / volLow | 20 / 2.0 / 0.7 | ভলিউম স্পাইক ও শুকিয়ে যাওয়ার সংজ্ঞা |
| Pin bars in leg (M06/M07) | 2 | এক লেগে কয়টা পিন বার লাগবে |
| Dojis in leg (M04) | 2 | একই ধরনের |
| Retest body ratio (M31) | 0.7 | রিটেস্ট ক্যান্ডেল কত ছোট হতে হবে |
| Liquidity scan distance × ATR (M09) | 3.0 | কত দূর পর্যন্ত লিকুইডিটি টার্গেট গুনবে |
| Range detection length / max width | 20 / 3.0 | রেঞ্জ শনাক্তকরণ |
| **Armed setup stays valid N bars** | 30 | মাল্টি-স্টেপ সেটআপ (M41/45/46/48/52/54) কত বার সক্রিয় থাকবে |
| M53 alternative entry | বন্ধ | কম উইন-রেট, ইচ্ছাকৃতভাবে বন্ধ |

### `9a · Premium / Discount + Sessions` ⭐ নতুন

| ইনপুট | ডিফল্ট | মানে |
|---|---|---|
| **Score premium/discount** | চালু | discount-এ লং / premium-এ শর্ট = +১ স্কোর। গভীর প্রান্তে উল্টোটা −১ |
| **Block longs in premium / shorts in discount** | **বন্ধ** | কড়া ফিল্টার। নিজের সিম্বলে যাচাই করে তারপর চালু করুন |
| Deep threshold | 0.75 | কত উপরে/নিচে গেলে "গভীর" ধরবে |
| **Only signal inside a killzone** | **বন্ধ** | চালু করলে Asia/London/NY-এর বাইরে কোনো সিগন্যাল আসবে না |
| **Score London / NY sessions** | চালু | লন্ডন বা NY-তে হলে +১ স্কোর |
| Asia / London / NY | 0000-0800 / 0700-1000 / 1200-1500 | **চার্টের টাইমজোনে** — নিজের ব্রোকার অনুযায়ী ঠিক করুন |
| **Asia high/low as SESH/SESL** | চালু | লন্ডন ওপেনে এশিয়া রেঞ্জের হাই-লো লিকুইডিটি লেভেল হিসেবে বসে |

> **এশিয়া রেঞ্জ সুইপ → লন্ডন রিভার্সাল** — ICT-র সবচেয়ে পুনরাবৃত্ত প্যাটার্ন।
> `SESH`/`SESL` লেভেলে সুইপ দেখলে বিশেষ মনোযোগ দিন।

### `9 · Visual · Colors`

রঙ, স্বচ্ছতা, লেবেল সাইজ। কার্যকারিতায় কোনো প্রভাব নেই।

- `Filled label` বন্ধ করলে লেবেল টেক্সট-অনলি হয় (থিম-নিরপেক্ষ, পরিষ্কার)
- `Zone / level text size` — জোনের ভেতরের লেখার আকার
- `Label offset × ATR` — লেবেল ক্যান্ডেল থেকে কত দূরে বসবে

### `10 · Show` — কী দেখাবে ⭐ এখানেই সব চালু/বন্ধ

| টগল | ডিফল্ট | কী দেখায় |
|---|---|---|
| Structure: BOS/CHoCH/CISD + major H/L | চালু | স্ট্রাকচার লেবেল ও লাইন |
| Structure: valid pullback PB✓ | বন্ধ | পুলব্যাক কনফার্মেশন |
| Label weak BOS | বন্ধ | দুর্বল BOS-এর লেবেল (লাইন সবসময় আঁকে) |
| Label every CISD | বন্ধ | বন্ধ = শুধু কাউন্টার-ট্রেন্ড CISD |
| **FVG boxes** | চালু | imbalance বক্স |
| Keep mitigated FVG | বন্ধ | ভরাট গ্যাপ ধূসর হয়ে থাকবে |
| **Liquidity lines** | চালু | BSL/SSL/POOL/PDH/PWH |
| Sweep / run / hidden events | চালু | সুইপ ও রান লেবেল |
| Label every BSL/SSL sweep | বন্ধ | বন্ধ = শুধু POOL/ext/PD/PW |
| OB diagnostics (T5/T3) | বন্ধ | কেন OB তৈরি হলো না, তার কারণ |
| **OB / S&D · Breaker · Key levels** | তিনটাই চালু | প্রধান জোন |
| S/R wick zones | বন্ধ | কাঁচামাল — চালু করলে চার্ট ভরে যাবে |
| Reclaimed · Rejection · QM | তিনটাই চালু | ICT ব্লক |
| HTF candle levels · sweep events · bias tint | তিনটাই চালু | HTF কনটেক্সট |
| Candle pattern tags | বন্ধ | L0 ডিবাগ |
| **Info panel** | চালু | নিচে-ডানের টেবিল |
| **Legend** | **বন্ধ** | উপরে-ডানের কী-টেবিল (প্রাইস ঢেকে ফেলে) |
| **Setup signals (L6)** | চালু | ট্রেড সিগন্যাল লেবেল |

> ⚠ **গুরুত্বপূর্ণ:** এই টগলগুলো **শুধু আঁকা** নিয়ন্ত্রণ করে। OB বক্স বন্ধ করলেও
> OB-নির্ভর সব সেটআপ (M36/M37/M42/M45/M48) আগের মতোই কাজ করে। v8.2.0-এর আগে
> এটা ভাঙা ছিল — বক্স বন্ধ করলে মডিউলও মরে যেত।

### `11 · Setups A–I` · `13 · Setups J–R` · `15 · Setups S–AB`

৫০টা মডিউলের অন/অফ। **ডিফল্টে ২৪টা চালু** (কিউরেটেড কোর)।

**চালু (ডিফল্ট):**
`M01 M02 M05 M08 M09 M10 M15 M33 M36 M37` ·
`M39 M40 M41 M42 M45 M46 M51 M54` ·
`M58 M62 M64 M68 M69 M70 M72 M73`

**বন্ধ (ডিফল্ট):** `M03 M04 M06 M07 M11 M12 M14 M21 M22 M23 M24 M25 M29 M38` ·
`M43 M44 M47 M48 M49 M50 M52 M53` · `M63 M65`

> **পরামর্শ:** একসাথে অনেকগুলো চালু করবেন না। একটা করে চালু করে
> `14 · Trade → Min confluence score` দিয়ে যাচাই করুন সেটা আসলে কিছু দেয় কিনা।

### `12 · Setup filters` — মান নিয়ন্ত্রণ

| ফিল্টার | ডিফল্ট | কী করে |
|---|---|---|
| M19 suppress reversal after STRONG arrival | চালু | জোরে এসে জোনে ঢুকলে রিভার্সাল খুঁজবে না (জোন ভাঙার সম্ভাবনা) |
| M26 pullback must be corrective | চালু | পুলব্যাক এলোমেলো হতে হবে, সোজা না |
| M31 retest body-size rule | বন্ধ | রিটেস্ট ক্যান্ডেল ছোট হতে হবে |
| **§6.2 block reversal at touch≥2 unless swept** | চালু | ২+ বার ছোঁয়া জোনে সরাসরি রিভার্সাল নিষিদ্ধ |
| **§6.6 S&D 50% rule** | চালু | জোনের ৫০% ছুঁতে হবে |
| M01/M02 level rejected ≥2× | চালু | ভাঙা লেভেলটা আগে ২বার রিজেক্ট হতে হবে |

> এগুলো **বন্ধ করলে সিগন্যাল বাড়বে, মান কমবে**। ডিফল্ট রাখাই ভালো।

### `16 · S–AB parameters`

Double top টলারেন্স (0.15 ATR), M72 কনসলিডেশন (৪ বার / 1.5 ATR), M63 no-retest উইন্ডো (৮ বার)।

### `14 · Trade (L7)` ⭐ সবচেয়ে গুরুত্বপূর্ণ গ্রুপ

> তালিকার **একদম শেষে** পাবেন।

| ইনপুট | ডিফল্ট | কী করে |
|---|---|---|
| SL buffer × ATR | 0.15 | জোন/সুইপের বাইরে কতটা জায়গা |
| Max SL distance × ATR | 2.0 | এর বেশি হলে ক্যান্ডেল এক্সট্রিমে ফিরে যায় |
| **Min R:R** | **2.0** | এর নিচে সিগন্যাল লুকানো থাকে |
| **Max R:R** ⭐নতুন | **6.0** | এর চেয়ে দূরের টার্গেট গণ্য হয় না (মাঝে ফাঁকা জায়গা) |
| Fixed-R mode | বন্ধ | চালু করলে TP সবসময় নির্দিষ্ট R-এ বসবে, আসল লেভেল খুঁজবে না |
| **Require a REAL target** | চালু | সত্যিকারের জোন/FVG/লিকুইডিটি না পেলে সিগন্যাল দেখাবে না |
| **Min confluence score** | **3** | সিগন্যাল দেখানোর সর্বনিম্ন স্কোর। **৪–৫ করলে অনেক কম কিন্তু ভালো সিগন্যাল** |
| **Min bars between signals** | **10** | দুই সিগন্যালের ফাঁক। বেশি সিগন্যাল এলে ২০–৩০ করুন |
| M10 entry mode | IMMEDIATE | `IMMEDIATE` = সুইপ ক্যান্ডেলের ক্লোজে · `RETEST` = সুইপ লেভেলে লিমিট · `BOTH` |
| Draw entry / SL / TP lines | চালু | ট্রেড লাইন |
| Trade line length | 20 | কত বার সামনে টানবে |

---

## ৫. টাইমফ্রেম অনুযায়ী প্রিসেট

### স্ক্যাল্প (১–৫ মিনিট)
```
1 · General    → Setup master mode = Core only
               → Label density     = Signals only
               → Min bars between labels = 8
7 · HTF        → HTF pairing = Conservative · gate = WARN
9a             → Only signal inside a killzone = ON  ← গুরুত্বপূর্ণ
14 · Trade     → Min confluence score = 4
               → Min bars between signals = 20
               → Min R:R 2.0 · Max R:R 5.0
```
১ মিনিটে নয়েজ সবচেয়ে বেশি। **কিলজোন ফিল্টার চালু করাই আসল পার্থক্য।**

### ইন্ট্রাডে (১৫ মিনিট – ১ ঘণ্টা)
```
1 · General    → Setup master mode = Core only
               → Label density = Key events
7 · HTF        → Conservative · WARN
14 · Trade     → Min confluence score = 3
               → Min bars between signals = 10
               → Min R:R 2.0 · Max R:R 6.0
```
ডিফল্টের সবচেয়ে কাছে। এখানেই ইঞ্জিনটা সবচেয়ে ভালো কাজ করে।

### সুইং (৪ ঘণ্টা – ডেইলি)
```
1 · General    → Swing length = 5
6 · Zones      → Drop untouched zone after N bars = 800
7 · HTF        → Conservative (4h→D, D→W)
9a             → killzone ফিল্টার বন্ধ (ডেইলিতে অর্থহীন)
14 · Trade     → Min R:R 2.5 · Max R:R 8.0
               → Min bars between signals = 5
```

---

## ৬. ট্রেড ওয়ার্কফ্লো — চেকলিস্ট

সিগন্যাল লেবেল দেখার পরে **প্যানেল পড়ুন, তারপর সিদ্ধান্ত:**

```
১. Signal সারিতে মডিউল + স্কোর আছে?          → না হলে থামুন
২. গ্রেড A+ (▲▲) নাকি B (·)?                → B হলে সাইজ কমান
৩. 4-factor কয়টা ✅?                        → ২টার কম হলে এড়িয়ে যান
৪. HTF bias-এ ⚠ আছে?                        → থাকলে কাউন্টার-ট্রেন্ড, সাবধান
৫. Arrival = WEAK ✅?                        → STRONG ❌ হলে জোন ভাঙতে পারে
৬. Active zone-এ ⚠SWEEP REQ আছে?            → থাকলে আগে সুইপের অপেক্ষা করুন
৭. PD array — লং হলে discount? শর্ট হলে premium?
৮. Session = London / NY?                    → হ্যাঁ হলে মান বেশি
৯. লেবেলে হোভার → R:R দেখুন                 → ২R-এর নিচে হলে বাদ
১০. Nearest BSL/SSL — TP সেখানেই তো?
```

**এন্ট্রি/SL/TP** লেবেলের টুলটিপে আছে, আর চার্টে লাইন হিসেবেও আঁকা:
নীল = এন্ট্রি · লাল = SL · সবুজ ৩টা = TP1/TP2/TP3।

---

## ৭. অ্যালার্ট সেটআপ

চার্টে ডান-ক্লিক → **Add alert** → Condition-এ ইন্ডিকেটরের নাম বেছে নিন।

**ডায়নামিক অ্যালার্ট (স্বয়ংক্রিয়, বার্তায় বিস্তারিত থাকে):**
প্রতিটা সিগন্যালে নিজে থেকেই ফায়ার করে, বার্তা হবে —
```
BTCUSDT | M37 LONG | Score 8 | Entry 77565.9 SL 77510.2 TP 77680.0 | TF 1 | HTF BULL
```
এটা পেতে Condition = ইন্ডিকেটর, তারপর **"Any alert() function call"** বেছে নিন।

**স্ট্যাটিক অ্যালার্ট (আলাদা করে বেছে নেওয়া যায়):**

| নাম | কখন |
|---|---|
| Setup: LONG signal / SHORT signal | যেকোনো সিগন্যাল |
| **Setup: Any A+ signal** | শুধু স্কোর ≥৬ — **এটাই সবচেয়ে কাজের** |
| Warning: Counter-HTF signal | HTF-বিরোধী সিগন্যাল |
| Structure: BOS / CHoCH (Real) / CISD | স্ট্রাকচার ঘটনা |
| Liquidity: Sweep detected | সুইপ |
| Liquidity: Hidden liquidity building | লুকানো লিকুইডিটি |
| Zone: New high-probability OB | নতুন OB★ |
| Zone: Propulsion Block formed | নতুন ⇈PROP |
| Zone: Price entered OB / S&D (50% tapped) | জোনের ৫০% ছোঁয়া |

সব অ্যালার্ট **বার ক্লোজে** ফায়ার করে — ইন্ট্রাবার ফলস অ্যালার্ট হবে না।

---

## ৮. ব্যাকটেস্ট — স্ট্র্যাটেজি ফাইল

`SMC_Suite_v8.2.1_strategy.pine` = হুবহু একই ডিটেকশন + `strategy.entry`।

**কীভাবে:**
1. আলাদা করে চার্টে অ্যাড করুন (ইন্ডিকেটরটা বন্ধ রাখতে পারেন)
2. `1 · General → Setup master mode = Core only`
3. নিচে **Strategy Tester** ট্যাব → Performance Summary

**`17 · Strategy (validation)` গ্রুপ:**

| ইনপুট | কাজ |
|---|---|
| Take LONG / SHORT signals | এক দিক বন্ধ করে আলাদা করে পরীক্ষা |
| Extra minimum score | ইন্ডিকেটরের minScore-এর উপরে আরও কড়াকড়ি |
| Scale out: half at TP1, rest at TP2 | আংশিক এক্সিট |
| **Count signals from module** | মডিউলের নাম লিখুন (`M37`, `M42`) → Data Window-তে কতবার ফায়ার করেছে দেখাবে |

> **কীভাবে পড়বেন:** ১০টার কম ট্রেড থাকলে কোনো পরিসংখ্যান নেই — ওটা দেখে টিউন করবেন না।
> মডিউল কাউন্টার দিয়ে খুঁজুন কোনগুলো আসলে কখনো ফায়ারই করে না — সেগুলো বন্ধ করে দিন।

সেটিংস: এন্ট্রি সিগন্যাল বারের ক্লোজে, SL/TP ট্রেড ইঞ্জিনের হিসাব মতো,
কমিশন 0.02%, ইকুইটির ১০%, একসাথে একটাই পজিশন।

---

## ৯. যা বিশ্বাস করবেন না

| জিনিস | কেন |
|---|---|
| `BOS weak` · `CHoCH?` | imbalance নেই — ইঞ্জিন নিজেই বলছে এটা দুর্বল |
| `RUN — avoid` | লেভেল ভেঙে চলে গেছে, ফেরেনি। ফেড করবেন না |
| `M41 NO TRADE (no FVG)` | সুইপের পরে মুভে FVG নেই |
| `⚠M51 weak BOS` | কনসলিডেশনের ঝুঁকি |
| গ্রেড `B` (·) সিগন্যাল | স্কোর ৪-এর নিচে — সেরাটার জন্য অপেক্ষা করুন |
| `INCOMPLETE (4-factor)` নোট | ৪-ফ্যাক্টরের সব মেলেনি, ১ স্কোর কাটা হয়েছে |
| ধূসর লেবেল | HTF/ট্রেন্ডের বিপরীত |

### সীমাবদ্ধতা যা জেনে রাখা দরকার

- **এটা ব্যাকটেস্ট করা সিস্টেম না।** ৫০টা মডিউলের কোনোটার যাচাই করা উইন-রেট নেই।
  স্কোর ৭ বনাম ৩ — এটা ডিজাইনারের মত, প্রমাণ না। স্ট্র্যাটেজি ফাইল দিয়ে **নিজের
  সিম্বলে মেপে নিন**।
- **দুটো আলাদা স্কোরিং সিস্টেম** চলছে: base score ক্যান্ডিডেট বাছে, `f_conf` চূড়ান্ত
  স্কোর দেয়। লেবেলে যেটা দেখেন সেটা `f_conf`-এর। তাই "M37 base 7" হলেও লেবেলে
  "A 4" দেখাতে পারে।
- সমান স্কোর হলে **কোড ঘোষণার ক্রমে** বিজয়ী ঠিক হয়, যোগ্যতায় না।
- HTF ডেটা `lookahead_on` + `[1]` অফসেটে — এটা সঠিক নন-রিপেইন্টিং পদ্ধতি,
  কিন্তু HTF তথ্য **HTF বার বন্ধ হলে** আপডেট হয়, তার আগে না।

---

## ১০. সমস্যা সমাধান (Troubleshooting)

| সমস্যা | সমাধান |
|---|---|
| **সিগন্যাল অনেক বেশি** | `14 · Trade → Min confluence score` ৪–৫ · `Min bars between signals` ২০–৩০ · `1 · General → Core only` |
| **সিগন্যাল আসেই না** | `7 · HTF → gate = WARN বা OFF` · `9a → killzone filter` বন্ধ · `Min R:R` ১.৫ · `Max R:R` ৮ |
| **চার্ট ভীষণ ভিড়** | `10 · Show` থেকে S/R, HTF levels, FVG বন্ধ · `Label density = Signals only` · `Legend` বন্ধ |
| **লেবেল একটার উপর আরেকটা** | `1 · General → Min bars between labels` ১০–১২ |
| **প্যানেল দেখা যাচ্ছে না** | `10 · Show → Info panel` টিক · চার্ট জুম আউট করুন |
| **লেজেন্ড প্রাইস ঢেকে ফেলছে** | `10 · Show → Legend` আনটিক (ডিফল্টেই বন্ধ) |
| **জোন বক্স নেই** | `10 · Show → OB / S&D · Key levels` টিক দিন |
| **PD array সবসময় "outside swing"** | স্বাভাবিক — ট্রেন্ডিং মার্কেটে প্রাইস সুইং রেঞ্জের বাইরে থাকে |
| **R:R খুব বড় দেখাচ্ছে** | `Max R:R` কমান (৪–৫) |
| **স্ক্রিপ্ট ধীর** | `Max FVGs` ২০ · `Max zones` ২০ · `Max liquidity levels` ২০ |

---

## ১১. সেটিংস ডায়ালগ — কোথায় কি

চার্টে ইন্ডিকেটরের নামের পাশে **⚙** → **Settings** → **Inputs** ট্যাব।
গ্রুপগুলো এই ক্রমে থাকে (নম্বর আর ক্রম এক না — `14` সবশেষে):

```
┌─ SMC / ICT / CRT Suite v8.2.1 ─────────────────── Inputs │ Style ─┐
│                                                                    │
│  ▸ 1 · General            ← Core only / Label density / ATR       │
│  ▸ 2 · Candle (L0)        ← pin bar, doji, engulfing থ্রেশহোল্ড    │
│  ▸ 3 · Structure (L1)                                              │
│  ▸ 4 · FVG / Strength (L2)  ← STRONG move-এর সংজ্ঞা                │
│  ▸ 5 · Liquidity (L3)     ← PDH/PDL, EQH/EQL, sweep vs run        │
│  ▸ 6 · Zones (L4)         ← OB, KL, RJB, PROP-এর কড়াকড়ি          │
│  ▸ 7 · HTF (L5)           ← ★ HTF bias gate (WARN)                │
│  ▸ 8 · Setup filters (L6) ← volume, armBars                       │
│  ▸ 9a · Premium/Discount + Sessions  ← ★ killzone ফিল্টার         │
│  ▸ 9 · Visual · Colors                                             │
│  ▸ 10 · Show              ← ★★ কী দেখাবে / লুকাবে — সব এখানে      │
│  ▸ 11 · Setups A–I (toggle)    M01…M38                            │
│  ▸ 12 · Setup filters          মান নিয়ন্ত্রণ                      │
│  ▸ 13 · Setups J–R (toggle)    M39…M54                            │
│  ▸ 15 · Setups S–AB (toggle)   M58…M73                            │
│  ▸ 16 · S–AB parameters                                            │
│  ▸ 14 · Trade (L7)        ← ★★★ Min score, Min/Max R:R, sigGap    │
│     (শুধু strategy ফাইলে)                                          │
│  ▸ 17 · Strategy (validation)                                      │
│                                                                    │
│                          [ Defaults ▾ ]   [ Cancel ]   [ OK ]     │
└────────────────────────────────────────────────────────────────────┘
```

### `10 · Show` ভেতরে যা দেখবেন

```
10 · Show
  ☑ Structure: BOS/CHoCH/CISD labels + major H/L   ☐ Structure: valid pullback PB✓
  ☐ Label weak BOS                                  ☐ Label every CISD
  ☑ FVG boxes                                       ☐ Keep mitigated FVG (faded)
  ☑ Liquidity lines                                 ☑ Sweep / run / hidden events
  ☐ Label every BSL/SSL sweep/run
  ☐ OB diagnostics labels (T5 no-FVG / T3 invalid)
  ☑ OB / S&D        ☑ Breaker        ☑ Key levels
  ☐ S/R wick zones  ☑ Reclaimed      ☑ Rejection    ☑ QM
  ☑ HTF candle levels   ☑ HTF sweep / manip events   ☑ HTF bias tint
  ☐ Candle pattern tags (L0 debug)   ☑ Info panel   ☐ Legend   ← এটাই লেজেন্ড
  ☑ Setup signals (L6)
```

### `14 · Trade (L7)` ভেতরে যা দেখবেন

```
14 · Trade (L7)
  SL buffer × ATR            [0.15]   Max SL distance × ATR      [2.0]
  Min R:R                    [2.0]    Fixed-R mode  ☐   Fixed R  [2.0]
  Max R:R                    [6.0]    ← v8.2.1 নতুন
  ☑ Require a REAL target (zone / FVG / liquidity) at Min R:R
  Min confluence score       [3]      M10 entry mode  [IMMEDIATE ▾]
  Min bars between signals   [10]
  ☑ Draw entry / SL / TP lines        Trade line length  [20]
```

---

## ১২. চার্ট অ্যানাটমি — কোনটা কোথায় বসে

```
        ┌──────────────────────────────────────────── Legend (ডিফল্টে বন্ধ)
        │
   ═════╪═══════════════════════════ ← HTF candle High (নীল সলিড)
        │              ╭─────────╮
  ┈┈┈┈┈┈┼┈┈┈┈┈┈┈┈┈┈┈┈┈┈│ POOL·EQH│┈┈┈┈  ← মোটা ড্যাশড কমলা = লিকুইডিটি পুল
        │              ╰─────────╯
        │      ▼▼ M37 A+8 · 3.2R   ← শর্ট সিগন্যাল (ক্যান্ডেলের উপরে)
        │         ┃
        │      ╻  ┃  ╻                  ← ক্যান্ডেল
        │      ┃  ╹  ┃
   ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁  ← ─── এন্ট্রি (নীল সলিড)
   ░░░░░ OB▲★ T1 IDM✓ ░░░░░░░░░░░  ← জোন বক্স (extend right) + ট্যাগ
   ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔  ← ╌╌╌ SL (লাল ড্যাশড)
        │      ▲ M42 A5 · 2.4R     ← লং সিগন্যাল (ক্যান্ডেলের নিচে)
        │                                ╌╌╌ TP1/TP2/TP3 (সবুজ ড্যাশড)
   ┈┈┈┈┈┼┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈  ← পাতলা ডটেড = BSL/SSL
        │
        │                       ┌──────────────┬──────────────────┐
        │                       │ Chart / HTF  │ 1 → 15           │
        │                       │ LTF structure│ BULLISH          │
        │                       │ HTF bias     │ BULL             │
        │                       │ Wyckoff      │ MARKUP           │
        │                       │ Last event   │ CISD▲ · 2b ago   │
        │                       │ Move phase   │ RETRACEMENT      │
        │                       │ Active zone  │ Bull OB (fresh)  │
        │                       │ Arrival      │ WEAK ✅          │
        │                       │ Nearest BSL  │ 77639.7          │
        │                       │ Nearest SSL  │ 77416.8          │
        │                       │ 4-factor     │ ✅✅✅❌          │
        │                       │ Signal       │ M42 5 (A)        │
        │                       │ PD array     │ 38% · discount   │
        │                       │ Session      │ London           │
        └───────────────────────┴──────────────┴──────────────────┘
                                         ↑ Info panel (নিচে-ডানে)
```

**লেবেলে হোভার করলে টুলটিপ:**

```
┌─────────────────────────────────────────────────────┐
│ High-probability demand: strong departure · 50%     │
│ tapped · weak arrival · ★★ near-miss then sweep     │
│                                                     │
│ entry 77565.9 · SL 77510.2                          │
│ TP1 77680.0  (2.1R)                                 │
│ TP2 77745.5  (3.2R)                                 │
│ TP3 77820.0  (4.6R)                                 │
│ score 5 (A)                                         │
└─────────────────────────────────────────────────────┘
```

---

## ১৩. দ্রুত রেফারেন্স — কোন সেটিং কোথায়

| যা করতে চান | কোথায় |
|---|---|
| সিগন্যাল কম/বেশি করা | `14 · Trade` → Min confluence score |
| কিছু লুকানো/দেখানো | `10 · Show` |
| মডিউল অন/অফ | `11` / `13` / `15 · Setups` |
| HTF ফিল্টার শিথিল/কড়া | `7 · HTF` → HTF bias gate |
| সেশন ফিল্টার | `9a` → Only signal inside a killzone |
| SL/TP-এর হিসাব | `14 · Trade` |
| রঙ ও আকার | `9 · Visual · Colors` |
| জোনের মান কড়া করা | `6 · Zones` → Key level min criteria, OB high-probability only |

---

**ভার্সন:** v8.2.1 · ৫০টা মডিউল · ৭ লেয়ার
**সহগামী নথি:** `FORENSIC_AUDIT_BN.md` (কোড অডিট ও কী কী ঠিক করা হয়েছে)
