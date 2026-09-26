# v3.2.2 — তৃতীয় পাস অডিটের ফিক্স প্রয়োগ (implementation log)

| ফাইল | কী |
|---|---|
| `version_03_v3.2.2.pine` | ইন্ডিকেটর (চার্ট + অ্যালার্ট) — 4,999 লাইন |
| `version_03_strategy_v3.2.2.pine` | স্ট্র্যাটেজি টুইন (Strategy Tester) — 5,066 লাইন |
| বেস | `Liqudity_supply_demain_improv/version_02_fixed.pine` (v3.2.1) |

দুই ফাইলের diff = **৬৭ লাইন**: `strategy()` হেডার + ড্যাশবোর্ড টাইটেল + MODULE 19S। ডিটেকশনের প্রতিটা লাইন এক — তাই Strategy Tester ঠিক ওই সিগন্যালই মাপে যেগুলো চার্টে দেখো।

---

## ১. কী কী প্রয়োগ হলো

| আইডি | সমস্যা | কোডে যা বদলালো |
|---|---|---|
| **FIX-T1** | যেকোনো zone ভাঙলে setup মরত (`zoneInvalidatedUp/Dn` গ্লোবাল) | মেশিন এখন **নিজের anchor** (`suLAnchorB` / `suSAnchorT`) চেক করে। reason = "POI violated (own anchor)"। গ্লোবাল ফ্ল্যাগ দুটো এখন শুধু debug রো-তে (`·zInv▲/▼`) |
| **FIX-T2** | আটকে থাকা ট্রেড পরের সব entry গিলত | `maxTrdBars` (default 80) = trade expiry → `cntExp` · untracked entry এখন **ACTIVE-ই থাকে** (stage রিসেট হয় না), শুধু `cntUntracked` বাড়ে · `nonSbTp3` দিলে non-SB ট্রেডেও TP3 runner |
| **FIX-T3** | non-SB arming শুধু সুইপের ঠিক ওই বারে | `armGrace` (default 3 বার) — সুইপ in-play থাকতে হবে, প্রতি সুইপে **একবারই** (`armedSslBar/armedBslBar`) |
| **FIX-T4** | খালি CISD = "structure shift" | `shiftSrc` ইনপুট, default **"MSS / external CHoCH"** → `shiftUpOk / shiftDnOk` |
| **FIX-T5** | OTE ব্যান্ড একাই POI tap | `poiSrc` ইনপুট, default **"Zone / HTF POI only"** |
| **FIX-T6** | `hsProtLo/hsProtHi` আনা হতো, ব্যবহার হতো না | `htfProtInval` (default ON): HTF protected swing ভাঙলে setup মরে ("HTF protected low/high broken") |
| **FIX-T7** | engine সিগন্যালের entry = bar close | `engFillMode` (default **"Next bar open (realistic)"**) → pending order (`pendDir/pendSL`), পরের বারের open-এ ফিল, পুরো TP ল্যাডার ওই দামে নতুন করে মাপা। মেশিন entry একই বারেই ফিল (ওটা resting order) · একই বারে মেশিন সিগন্যাল এলে pending বাতিল (SB-13 hierarchy) |
| **FIX-T8** | CE fill retroactive → survivorship bias | `sbFillMode` (default **"Limit touch (realistic)"**) — CE ছোঁয়া মানেই ফিল। `slipGuard` এখন CE-limit ফিলে **প্রযোজ্য নয়** (ছোঁয়াটাই প্রমাণ) |
| **FIX-T9** | `sbPdPos` unclamped | clamp 0–1 + রেঞ্জের ১৫% বাইরে গেলে লাইভ `pdPos`-এ fallback (`sbPdOut`) |
| **FIX-T10** | chop bypass EFF grade পড়ত (circular) | `instSweepL/S = lastSslQualRaw >= 3 and recentMssUp` — RAW সুইপ **এবং** MSS, দুইটাই লাগবে |
| **FIX-T11** | ছোটখাটো | `f_pickPoi`-তে freshness শুধু ৩ ATR জানালার ভেতরে জেতে · leg < 2 ATR হলে A+-এর premium/discount শর্ত মওকুফ · LT-7 এখন HTF POI-কে supply zone ধরে না · `relVol` floor = 1 |

---

## ২. নতুন ইনপুট (সব default সহ)

| গ্রুপ | ইনপুট | Default | ভূমিকা |
|---|---|---|---|
| HTF context | `HTF protected swing invalidates a setup` | ON | FIX-T6 |
| Signal quality | `Machine: bars after the sweep a setup may still arm` | 3 | FIX-T3 (0 = পুরোনো আচরণ) |
| Signal quality | `Machine: what counts as the SHIFT` | MSS / external CHoCH | FIX-T4 (`+ CISD` = পুরোনো) |
| Signal quality | `Machine: what counts as the POI TAP` | Zone / HTF POI only | FIX-T5 |
| Risk / TP / SL | `Engine signal fill price` | Next bar open (realistic) | FIX-T7 (`Bar close` = পুরোনো) |
| Risk / TP / SL | `Tracked trade max life (bars)` | 80 | FIX-T2 (0 = off) |
| Risk / TP / SL | `Non-SB trades: keep a runner to TP3` | OFF | FIX-T2 |
| SB entry | `CE fill model` | Limit touch (realistic) | FIX-T8 (`Touch + hold` = পুরোনো) |

> **v3.2.1-এ ফেরত যেতে চাইলে:** armGrace = 0 · shiftSrc = "+ CISD" · poiSrc = "+ OTE" · htfProtInval OFF · engFillMode = "Bar close" · sbFillMode = "Touch + hold" · maxTrdBars = 0। বাকি ফিক্সগুলো (T1, T9, T10, T11) ডিফেক্ট রিপেয়ার — টগল নেই।

---

## ৩. কী বদলাবে চার্টে (প্রত্যাশা)

**বাড়বে:** setup সংখ্যা — T1 (ভুল kill বন্ধ), T3 (grace), T2 (stage আর মুছে যায় না)।
**কমবে:** দুর্বল entry — T4 (CISD আর shift নয়), T5 (OTE একা POI নয়), T6 (HTF কাঠামো ভাঙলে বাদ), T10 (chop আর সহজে খোলে না)।
**বদলাবে সংখ্যা:** RR আর counter — T7 + T8। **আগের TP1/SL কাউন্ট নতুনটার সাথে তুলনীয় নয়** — T8 আগে হেরে যাওয়া ফিল লুকাত, এখন দেখায়। সংখ্যা খারাপ দেখালে সেটা রিগ্রেশন নয়, সেটা **সত্য**।

Debug টেবিলের Outcomes রো এখন: `TP1 · TP2 · TP3 · SL · exp · untrk · pending fill`।

---

## ৩ক. লাইভ চার্ট থেকে পাওয়া ৪টা ফিক্স (T12–T15)

চার চার্ট (GBPUSD · XAUUSD · BTCUSDT · ETHUSD, M5) দেখে:

| আইডি | চার্টে যা দেখা গেল | ফিক্স |
|---|---|---|
| **T12** | XAU 4,250→4,400 ডেলিভার করছে, Bias Bull, `L 64 (A)` — তবু **regime CHOP**, verdict "NO · chop"। A-tier লং মারা গেল | CHOP-এর জন্য এখন **তিনটা শর্ত একসাথে**: external pivot range সরু · **current leg-ও সরু** · দাম pivot range-এর **ভিতরে**। দাম রেঞ্জের বাইরে = structure নেওয়া হচ্ছে, সেটা chop নয়। `REGIME_LOOK` ইনপুট (30 → **40**) — M5-এ extPiv 12 হলে ৩০ বার খুব কম |
| **T13** | BTC/ETH চার্ট `CISD` / `IFC` / `LT setup` চিপে ঢাকা, 500-label বাজেট শেষ | `showCisd` · `showIFC` · `ltShowSetup` → **default OFF** (শুধু ডিসপ্লে; confirmed TRAP আর signal লেবেল থাকছে) |
| **T14** | XAU: Bias **Bull**, অথচ `Setup L/S = idle / AT POI` — শর্ট চেইন চলছে যেটা শেষ গেটে নিশ্চিত মরবে | `armNeedHtf` (default ON): বায়াসের বিরুদ্ধে setup **arm-ই হবে না**। ড্যাশবোর্ড আর মিথ্যা আশা দেখাবে না |
| **T15** | NEXT BUY/SELL লেবেল ড্যাশবোর্ডের নিচে পড়ছে | লেবেল এখন লাইনের **বাম প্রান্তে** (`Left end of the line`, default) |

> **যা যাচাই হলো ✅:** কম্পাইল · ১২-রো ড্যাশবোর্ড · verdict gate-naming ("NO · chop", "NO · score 47 < 60") · FIX-F6 HTF POI NEXT লেভেলে (`NEXT BUY T3 HTF`) · FIX-P1-13 "(price INSIDE)" · IFVG / MITIGATION / SD ·spent বক্স · FIX-T7-এর "engine fill = next open" লেবেল · ADR রো · SB উইন্ডো ব্যান্ড ও session।

> **এখনো ক্যালিব্রেশনের অপেক্ষায়:** চার চার্টে alignment 22 / 64 / 47 / 27 — `minScore = 60` প্রায় সব ব্লক করছে। এটা কোডের দোষ নয়, থ্রেশহোল্ডের। Strategy Tester-এ 0 → 40 → 60 চালিয়ে **মেপে** সেট করো (নিচের ধাপ ৪)।

---

## ৩খ. দ্বিতীয় লাইভ পাস — ৫টা ফিক্স (T16–T20)

চার চার্ট (XAUUSD · BTCUSDT · USTEC · ETHUSD, M5) — ইঞ্জিন পুরো নীরব, verdict দুটোয় "chop", দুটোয় "score < 60":

| আইডি | চার্টে যা দেখা গেল | ফিক্স |
|---|---|---|
| **T16** | USTEC নতুন হাই বানাচ্ছে, BTC 76k→85k — তবু **CHOP** | `regThrust`: REGIME_LOOK বারে নেট মুভ ≥ CHOP_RANGE_ATR × ATR হলে **কখনোই chop নয়**। M5-এ external pivot কনফার্ম হতে দেরি, তাই দামকেও ভোট দিতে দেওয়া হলো |
| **T17** | BTC/USTEC: `Setup = SWEPT` অথচ chop-এ ওই entry কোনোদিনই হতো না | arming পড়ত **EFF** গ্রেড (MSS নিজেই 4 বানায়), শেষ গেট চাইত RAW+MSS। এখন দুই জায়গায় **একই `instSweepL/S`** |
| **T18** | XAU: structure ▲Bull vs EMA ▼Bear → বায়াস **"—"**, ctx থেকে ১০ পয়েন্ট গায়েব; সিলিং ~৮০, বাস্তব signal bar ৫৫–৭০ | neutral বায়াস এখন **৫** পয়েন্ট (০ নয়) · `minScore` default **৬০ → ৫০** |
| **T19** | ETH: `NEXT BUY 2731.89–2732.25` = **0.05 ATR** পুরু | `minZoneAtr` (default 0.15 ATR) — এর চেয়ে পাতলা zone তৈরিই হয় না (SD · OB · IFVG) |
| **T20** | XAU: demand top == supply bottom == 4356.675 → এক ব্যান্ডে BUY আর SELL মার্কার, `inDemand` ও `inSupply` একসাথে true | `f_trimOpp`: নতুন zone বিতর্কিত ব্যান্ড জেতে, পুরোনো উল্টো-সাইড zone নিজের দিকটুকু রাখে, খুব কম বাকি থাকলে ডিলিট |

> টোকেন ফেরত: intrabar (repainting) LT preview + তার ইনপুট বাদ — সব LT স্টেট ক্লোজেই কমিট হয়। আনুমানিক **~৯৭.৩k / ১০০,২৫৬**।

> ⚠️ **ড্যাশবোর্ডের স্কোর দেখে থ্রেশহোল্ড ঠিক কোরো না** — ওটা ওই আইডল বারের কনটেক্সট, সিগন্যাল বারের নয়। `minScore` কেবল Strategy Tester-এ মাপা যায়।

---

## ৪. টেস্ট চেকলিস্ট (ক্রম মেনে)

1. **কম্পাইল** — দুই ফাইলই TradingView-তে paste করে Save। এরর হলে লাইন নম্বর সহ জানাও।
2. **Replay, ২ দিন M5** — দেখো:
   - `◉ Setup` রো আগের চেয়ে বেশি arm হচ্ছে (T1/T3), কিন্তু reason-এ "POI violated (own anchor)" শুধু নিজের zone ভাঙলে আসছে;
   - debug-এ `untrk` বাড়ে কিনা — বাড়লে `maxTrdBars` কমাও;
   - engine সিগন্যালের লেবেলে "engine fill = next open" আসছে, আর Active trade রো এক বার "order pending" দেখাচ্ছে।
3. **SB উইন্ডো** — NY AM-এ একটা tagged setup ধরো: CE ছোঁয়া মাত্র ফিল হচ্ছে কিনা (T8), আর `slipGuard` সেটা মারছে না।
4. **Strategy Tester** (`version_03_strategy_v3.2.2.pine`): `minScore = 0`, tierMode = "B and above" → বেসলাইন নাও। তারপর একে একে minScore 40 / 60 / 75 আর tier A / A+ — **কোথায় expectancy সর্বোচ্চ সেটা মাপো, অনুমান কোরো না**।
5. প্রতি সিম্বল × TF আলাদা করে ধাপ ৪ — FX-এ `useVol` OFF, index/crypto-তে ON।

---

## ৪ক. ⚠ টোকেন বাজেট (CE10117) — কী কাটা হলো

প্রথম বিল্ড কম্পাইল করেনি: **102,145 টোকেন, সীমা 100,256**। কমেন্ট গোনা হয় না, আর **ইউজার-ফাংশন প্রতিটা call site-এ আলাদা করে expand হয়** — তাই ছোট helper ১০ বার ডাকলে ১০ বার গোনা হয়।

ইঞ্জিন থেকে **একটা লাইনও কাটা হয়নি**। বাজেট এসেছে presentation + ডুপ্লিকেট helper থেকে:

| কাটা | কেন নিরাপদ | আনুমানিক লাভ |
|---|---|---|
| ড্যাশবোর্ড ১৯ → **১২ রো** (তথ্য একই, রো merge) | শুধু ডিসপ্লে | ~1,500 |
| ডিবাগ টেবিল ১৬ → **৯ রো** | শুধু ডিসপ্লে | ~800 |
| HTF bias **৫ → ২** security কল (নির্বাচিত TF + D) | বাকি ৩টা শুধু ড্যাশবোর্ডে দেখাত, কোনো গেট পড়ত না | ~600 |
| zone-এর ৫০% **কম্প্যানিয়ন লাইন** বাদ (৮ call site) | ৫০% **tap লজিক অপরিবর্তিত** — লাইনটা শুধু আঁকা হতো | ~1,200 |
| session-minute parser উইন্ডোপ্রতি **১ কল** (ছিল ২) | একই মান | ~600 |
| SB alert() মেসেজ ছোট | সব ইভেন্ট আছে, কম শব্দ | ~700 |
| **order-flow zigzag** (`showOF`, ডিফল্ট OFF) বাদ | ডিফল্টে বন্ধই ছিল | ~350 |
| **00:00 / 08:30 opening lines** বাদ | কোনো লজিক এটা পড়ত না | ~600 |

আনুমানিক মোট ≈ **−5,800 টোকেন → ~96.3k** (≈4% হেডরুম)। এগুলো আনুমান — আসল সংখ্যা TradingView-ই বলবে।

> ফেরত চাইলে সবচেয়ে সস্তা: opening lines আর zigzag আলাদা ছোট ইন্ডিকেটরে রাখো, মূল স্ক্রিপ্টে নয়।

---

## ৪খ. ⚠ CE10235 — কিছু না কেটে অপ্টিমাইজ (স্ট্রাকচার পাস)

`CE10235`-এর মানে TradingView প্রকাশ করে না, কিন্তু **ক্লু পরিষ্কার**: patch8 পর্যন্ত ফাইল কম্পাইল হয়েছিল (৪-চার্টের স্ক্রিনশট), ভাঙল **patch9 (T16–T20)**-এর পরে। আর মেপে দেখা গেল স্ক্রিপ্টটা টোকেনে নয়, **স্ট্রাকচারে** সিলিংয়ের কাছে — Pine প্রতিটা `if / else / for / while / function` কে একটা **local scope** ধরে, আর ফাংশন **প্রতিটা call site-এ আলাদা করে expand** হয়।

**একটা ফিচারও বাদ দেওয়া হয়নি।** যা করা হলো:

| কী | কেন |
|---|---|
| `f_trimOpp` (FIX-T20) **inline** করা হলো দুই call site-এ | patch9-এ যোগ করা একমাত্র নতুন ফাংশন, আর সেটা **অন্য ফাংশনের ভেতর থেকে** ডাকা হচ্ছিল এবং গ্লোবাল array মিউটেট করছিল — CE10235-এর সবচেয়ে সম্ভাব্য উৎস |
| `regThrust` এখন `ta.mom(close, REGIME_LOOK)` | `close[REGIME_LOOK]` = variable history offset, buffer-নির্ধারণে সমস্যা করে |
| ~২৩০টা `if` → **ternary / assignment** | একই লজিক, শূন্য scope: `f_cisd` · `f_trigMem` · `f_regimeMem` · `f_structMarks` · `f_sigLabels` (২০টা if → ২টা চেইন) · sweep latch · cooldown stamps · LT veto · কাউন্টার · মেশিনের stage expiry |
| read-only লুপে `for x in array` | `if array.size() > 0` গার্ড আর লাগে না — `for in` খালি array-তে নিরাপদ (`f_nextZones` · `f_ltObNear` · `f_extendDraw` · RB/IFVG dup scan · zone census) |
| zone cap: census + দুইটা `while` drain → **একটা descending pass** | একই ফল (প্রতি সাইডে নতুন `maxZones` থাকে), ~৭ scope কম |
| `f_sesTrack` (×৩ call) আর `f_structure` (×২ call)-এর branch → ternary | call site যত, scope তত — এখানে প্রতিটা কাটা ৩ গুণ / ২ গুণ ফেরত দেয় |

**ফল:** scope **740 → 506** (−32%) · টোকেন **~96.5k / 100,256**।

> ⚠ ইনলাইন করার সময় একটা বাগ ধরা পড়ে নিজের কোডেই: খালি array-তে `for k = size-1 to 0` মানে `-1 → 0`, অর্থাৎ `array.get(zones, -1)` — রানটাইম এরর। দুই জায়গায় `if array.size(zones) > 0` গার্ড ফেরত দেওয়া হয়েছে।

---

## ৫. পরের ধাপ (এখনো বাকি)

- **ফেজ 4 ক্যালিব্রেশন** — উপরের ধাপ ৪/৫-এর ফল থেকে ডিফল্ট সেট করা। এটা ডেটার কাজ, কোডের নয়।
- যে engine নেগেটিভ expectancy দেখায় (সন্দেহ: inside bar, doji, trendline) — ডিফল্ট OFF করে দেওয়া।
- সিম্বল-প্রোফাইল প্রিসেট (FX / index / crypto) — ইনপুট প্রিসেট হিসেবে, কোড নয়।
- `USER_MANUAL_BN.md` v3.2.2-এ আপডেট (নতুন ৮টা ইনপুট + বদলানো counter semantics)।
