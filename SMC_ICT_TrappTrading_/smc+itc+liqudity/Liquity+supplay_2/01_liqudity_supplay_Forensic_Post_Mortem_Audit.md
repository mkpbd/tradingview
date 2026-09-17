# ফরেনসিক পোস্ট-মর্টেম অডিট — `01.liqudity_supplay.pine` (ICT-TE v7.6)

**অডিটর ভূমিকা:** ৩০ বছরের প্রপ-ডেস্ক অপারেটর + Pine v6 সিস্টেম ইঞ্জিনিয়ার
**ফাইল:** `01.liqudity_supplay.pine` · 6601 লাইন · 430 KB · `//@version=6`
**স্কোপ:** শুধু এই একটি ফাইল। বাইরের কোনো ফাইল/কম্প্যানিয়ন ডক পড়া হয়নি।
**পদ্ধতি:** পুরো ফাইল লাইন-বাই-লাইন পড়া হয়েছে (Module 1 → 20), প্রতিটি স্টেট মেশিন, রেজিস্ট্রি লাইফসাইকেল, গ্রেড ল্যাডার আর রিস্ক ল্যাডার আলাদা করে ট্রেস করা হয়েছে।

---

## ✅ স্ট্যাটাস — v7.7-এ প্রয়োগ করা হয়েছে

এই অডিটের রোডম্যাপের **১-৮ ও ১০ নম্বর ধাপ** কোডে বসানো হয়েছে। ফাইলটি এখন **v7.7 · LIFECYCLE FIX PASS**; v7.6-এর কপি `01.liqudity_supplay.v7.6.backup.pine`-এ রাখা আছে।

| রোডম্যাপ ধাপ | অডিট § | কোডে যে নামে | অবস্থা |
|---|---|---|---|
| 1 | §3.1 | `F-01` — `reactWin`/`sweepLook` আলাদা ক্লক | ✅ |
| 2 | §3.2 | `F-02` — `Zone.bound`, prune-এ গার্ড, violation-এ dead-স্ট্যাম্প | ✅ |
| 3 | §3.3 | `F-03` — দুই-পাস ডিডুপ | ✅ |
| 4 | §3.4 | `F-04` — HTF POI sequence id + invalidation | ✅ |
| 5 | §3.5 | `F-05` — `f_raidAtZone()`, pool object provenance-এ | ✅ |
| 6 | §3.6 | `F-06` — `congMeasured` / `congested` আলাদা | ✅ |
| 7 | §4.2 | `F-07` — ডিডুপে `lqTol` | ✅ |
| 8 | §4.1 | `F-08` — trendline touch carry | ✅ |
| 9 | §4.3 | `strictSeq` — **বদলানো হয়নি**, tooltip ইতিমধ্যেই সত্য ছিল | ⏭ |
| 9 | §4.4 | `entryMode` tooltip-এ ELITE trap লেখা হয়েছে (আচরণ v7.1-এর সিদ্ধান্ত, অপরিবর্তিত) | ✅ |
| 10 | §4.6 | `F-09` — `TGT_HYST` হিস্টেরেসিস | ✅ |

**বাকি আছে:** §4.5 (`filtBias = Off` হলেও `request.security` চলে — শুধু পারফরম্যান্স) এবং §৫-এর P2 আইটেমগুলো।

**সতর্কতা:** পরিবর্তনগুলো স্ট্যাটিকভাবে যাচাই করা হয়েছে (ডিক্লারেশন অর্ডার, টিউপল arity, na-safe UDT অ্যাক্সেস, ইন্ডেন্টেশন/continuation স্টাইল)। **TradingView-এ কম্পাইল করা হয়নি** — এখানে সেই সুযোগ নেই। চার্টে বসিয়ে §৮-এর যাচাই ধাপগুলো চালান।

---

## 🔁 দ্বিতীয় পাস — v7.7-এ আরও যা পাওয়া গেল

প্রথম রাউন্ডের ফিক্স বসানোর পর আরেকটা গভীর পাস চালানো হয়েছে।

### 🔴 F-10 · নিচু র‍্যাঙ্কের producer উঁচু র‍্যাঙ্কের narrative ধ্বংস করতে পারত — **ফিক্সড**

v7.6-এর `machFirst` S/D producer-কে থামাত শুধু তখন, যখন মেশিন **একই POOL**-এ mid-narrative:

```pine
not (machFirst and s.st >= ST_POI and s.st < ST_ENTRY and s.liqId == sdPid)
```

কিন্তু যে সংঘর্ষটা আসলে ট্রেড খায় সেটা **একই ARRAY**-এর। মেশিন pool P-এর raid থেকে তার POI বাঁধে; ওই zone-এর নিজের stamped chain-এ থাকতে পারে **অন্য pool Q**। তখন `s.liqId != sdPid` → guard খোলা → S/D producer Q-এর চেইন দিয়ে ওই zone-এ ফায়ার করে, `signaled := true` বসায়, আর stage 4-7-এ থাকা মেশিন সেটআপ `f_zoneDead` দিয়ে মরে (`"POI spent or re-graded below the minimum tier"`)।

F-02-এর `Zone.bound` ইতিমধ্যেই holder রেকর্ড করে, তাই ফিক্সটা একটা তুলনা মাত্র — **একই pool অথবা একই array**, যেকোনোটাই producer-কে দাঁড় করিয়ে দেয়।

### 🧹 ডেড স্টেট সরানো হয়েছে (ফাইলের নিজস্ব V5.5-E6 হাউসকিপিং রুল)

| আইটেম | অবস্থা |
|---|---|
| `ny830Open` | প্রতি 08:30 open-এ লেখা হয়, **কোথাও পড়া হয় না** (লাইন/লেবেল সরাসরি `open` থেকে আঁকা) |
| `rbNew` | দুই rejection-block সাইটে `true` সেট হয়, **পড়া হয় না** |
| `f_zoneId()` | ডিফাইনড, **কখনো কল হয় না** |
| `Zone.cluHi` / `cluLo` | প্রতি render-এ লেখা হয়, v7.4 reclaim R4 cluster box মুছে দেওয়ার পর থেকে **পড়া হয় না** |

এগুলো সরানোর টোকেন দিয়েই নিচের MTF ফিচারের দাম দেওয়া হয়েছে।

### ✅ যাচাই করা হয়েছে, সমস্যা নেই

- **১৬৬টা ইনপুটের প্রতিটাই** অন্তত একবার পড়া হয় — কোনো orphan/unwired সেটিং নেই।
- `Zone.bound` লিক নেই: `f_setupReset` রিলিজ করে, flip ক্লিয়ার করে, আর stage 3→4 ছাড়া কোথাও `poiZone` ওভাররাইট হয় না।
- Trap engine-এর side mapping ঠিক (`trapU` → SHORT, `trapD` → LONG), consumption-ও ঠিক সাইডের watch রিসেট করে।
- `f_bias("5")` যখন চার্ট TF-এর নিচে, `f_tfUp` সেটাকে চার্ট TF-এ ক্ল্যাম্প করে → কোনো lookahead leak নেই; ড্যাশবোর্ডে সেটা `·` দেখায়।

### 📊 ড্যাশবোর্ডে MTF ল্যাডার ফিরেছে (আপনার অনুরোধ)

নতুন **row 3 — `MTF 5·15·1H·4H`**:

```
MTF 5·15·1H·4H  |  5m ▲  15m ▲  1H ▼  4H ▲   3▲/1▼
```

- প্রতিটা rung ওই টাইমফ্রেমের **শেষ CLOSED ক্যান্ডেল** থেকে পড়া — `expr[1]` ভেতরে + `lookahead_on`, ফাইলের নিজের নন-রিপেইন্টিং কনস্ট্রাকশন।
- ডান পাশের কাউন্ট = কয়টা **usable** rung একমত। সব একমত হলে সারিটা সবুজ/লাল হয়।
- চার্ট TF-এর সমান বা নিচের rung `·` দেখায় এবং কাউন্ট থেকে বাদ যায় — চার্ট নিজেকে দেখলে সেটা context নয়।
- **শুধু ডিসপ্লে।** কোনো gate/grade/score/tier/stop/target/dedupe/state transition এটা পড়ে না। counter-trend bias **FILTER** আলাদা সেটিং, আলাদা রিড — তাই BUG-16 ফিক্সড-ই থাকে।
- খরচ: `request.security` ইনস্ট্যান্স ৬ → ১০ (TradingView লিমিট ৪০)।

### ⚠️ যা এখনো নেই (ইচ্ছাকৃত, ফিক্স করা হয়নি)

| অনুপস্থিত | প্রভাব |
|---|---|
| **ট্রেড ম্যানেজমেন্ট** | ইঞ্জিন **entry-only**। TP1/TP2/TP3 আর SL আঁকে, তারপর কোনো মতামত নেই — break-even নেই, trail নেই, partial নেই, আর কোনো rung ছোঁয়ার alert নেই |
| **পজিশন সাইজিং** | রিস্ক শুধু R আর দামে; lot/account-% হিসাব নেই |
| **`strategy()` বিল্ড** | নেই, তাই TradingView-তে নেটিভ ব্যাকটেস্ট করা যায় না |
| **`filtBias` খরচ** | bias filter "Off" থাকলেও একটা `request.security` চলে (Pine টার্নারির দুই ব্রাঞ্চই ইভ্যালুয়েট করে) — শুধু পারফরম্যান্স |

এর মধ্যে সবচেয়ে বেশি মূল্য দেবে **TP/SL hit alert + break-even**। ✅ **v7.8-এ করা হয়েছে — নিচে দেখুন।**

---

## 🟢 v7.8 — এন্ট্রির পরে কী হলো (MODULE 16C)

ফাইলটা এখন **v7.8**। v7.7-এর কপি `01.liqudity_supplay.v7.7.backup.pine`-এ।

**কোনো ইঞ্জিন, producer, gate, grade, score, tier, stop, target, dedupe বা state machine ছোঁয়া হয়নি** — v7.8 ঠিক সেই ট্রেডগুলোই emit করে যেগুলো v7.7 করত, একই ক্রমে, একই দামে।

### যা যোগ হলো

| জিনিস | বিবরণ |
|---|---|
| **MODULE 16C** | শেষ emit হওয়া সিগন্যাল ট্র্যাক করে: কোন rung ছোঁয়া হলো, stop লেগেছে কিনা, সেরা excursion (R-এ), আর break-even মুভ |
| **৪টা ইনপুট** (⑰ Risk) | `trackTrade` · `beAfter` (Off/TP1/TP2) · `beOffset` (ATR ×, + = প্রফিট লক) · `tradeLife` (0 = কখনো না) |
| **৫টা অ্যালার্ট** | `[TRADE] TP1 / TP2 / TP3 reached` · `Stop hit` · `Break-even` |
| **ড্যাশবোর্ড row 17** | `LONG TP1 · BE  · MFE 2.3R` / `stopped` / `break-even stop` / `TP3 ✓` / `abandoned` |
| **চার্ট মার্ক** | প্রতি ইভেন্টে একটা chip — target প্রফিট সাইডে, stop লস সাইডে |
| **BE লাইন** | break-even হলে আঁকা SL লাইন ও লেবেল সেই নতুন stop-এ সরে যায় |

### যে তিনটা নিয়ম এটাকে সৎ রাখে

1. **সিগন্যাল বার কখনো ইভ্যালুয়েট হয় না।** ট্র্যাকিং শুরু এন্ট্রির **পরের** বার থেকে। সিগন্যাল ক্যান্ডেলের নিজের রেঞ্জই তো সেই rejection যেটার উপর এন্ট্রি নেওয়া — সেটাকে target ছুঁতে দিলে সেটা হবে V4-BUG-6/7 শ্রেণির ভুল: *একটা ইভেন্ট নিজেকে কনফার্ম করছে*।
2. **এক ক্যান্ডেলে দুটোই থাকলে stop জেতে।** OHLC থেকে কোনটা আগে লেগেছে বলা অসম্ভব, তাই হতাশাবাদী পাঠটাই নেওয়া হয় — একমাত্র ওটাই নিজের ফলাফলকে ফোলাতে পারে না।
3. **Break-even কখনো রিস্ক বাড়াতে পারে না।** মুভটা তখনই হয় যখন stop **উন্নত** হয়; R সবসময় **আসল** stop থেকে মাপা; আর পরে stop লাগলে সেটা loss নয়, **break-even stop** হিসেবে রিপোর্ট হয়।

**একসাথে একটাই ট্রেড** — নতুন সিগন্যাল আগেরটাকে রিপ্লেস করে।

### 🧹 সাথে একটা reclaim

`f_prod`-এর `tc` স্লট আর `touchL` / `touchS` গ্লোবাল দুটো বাদ। v7.6-এর F-12-এর পর call site এমনিতেই pool-টা identity দিয়ে resolve করছিল, আর `prodX > 0 ? f_poolTouch(evPoolX) : 0` **চারটা কেসই হুবহু** রিপ্রোডিউস করে (machine · S/D · trap · no producer)। একটা field, একটা write, একটা tuple slot আর একটা global গেল — এমন একটা ফাংশন থেকে যেটা দুবার inline হয়।

### ⚠️ টোকেন বাজেট — সোজা কথায়, এটা টাইট

v7.6 মেপেছিল ≈ **98 627** / 100 256 (≈ 1 630 স্পেয়ার)। v7.7 + v7.8 মিলে অনুমানে তার বেশি খরচ:

| আইটেম | আনুমানিক compiled |
|---|---|
| v7.7-এর ৯টা ফিক্স | +855 |
| MTF ladder | +510 |
| MODULE 16C | +1 010 |
| dead state + `tc` reclaim | −405 |
| **মোট** | **≈ 100 600 → ক্যাপের উপরে** |

**TradingView-এ কম্পাইল করা হয়নি** (এই lineage-এর স্থায়ী caveat), আর estimator আগে **দুই দিকেই** ভুল করেছে — তাই এঁটেও যেতে পারে। `CE10117` এলে এই ক্রমে কাটুন (সবচেয়ে কম ক্ষতি আগে, প্রতিটাই self-contained):

1. `tradeLife` ইনপুট + যে ৩ লাইন পড়ে (≈ 35)
2. `Trade.mfe` — field, আপডেট লাইন, আর row 17-এর `· MFE nR` টেক্সট (≈ 90)
3. MODULE 17-এর break-even SL লাইন/লেবেল redraw (≈ 80) — stop তবু সরে, ড্যাশবোর্ড তবু BE বলে
4. MODULE 17-এর v7.8 ইভেন্ট মার্ক (≈ 140) — অ্যালার্ট তবু ফায়ার করে
5. MODULE 8B লিকুইডিটি মার্কিং লেয়ার (≈ 3 960) — lineage-এর নিজস্ব প্রথম lever, একাই যথেষ্টের বেশি

**ডিবাগ প্যানেল কখনোই নয়** — উপরের প্রতিটা দাবি ওটাই auditable করে, আর lineage-এর নিয়ম বরাবর একটাই: ওটা currency না।

---

## 🔴 v7.11 — সঠিক মেট্রিক, কঠিন পথে পাওয়া

তৃতীয়বার `CE10117` — **102 483**, ক্যাপ **100 256**, **2 227 বেশি**।

### 📊 তিনটা মাপা পয়েন্ট অবশেষে বাজেটটা ব্যাখ্যা করল

| build | raw source | compiled | Δraw | Δcompiled |
|---|---|---|---|---|
| v7.8 | 35 426 | 100 677 | — | — |
| v7.9 | 35 080 | 103 567 | −346 | **+2 890** |
| v7.10 | 33 116 | 102 483 | −1 964 | **−1 084** |

v7.10 MODULE 8B সরিয়েছিল — **1 964 raw টোকেন**, যেটাকে v6.0 থেকে প্রতিটা হেডার ≈ 3 960 compiled বলে ধরেছে — আর ফেরত পেল **1 084**। অর্থাৎ **0.55 compiled per raw**, v6.3 থেকে ধরে আসা 2.27–3.25 নয়।

কারণটা v5.6-এর নিজের **L11** নোটে লেখা ছিল, তারপর L12 ওটাকে ভুল বলে বাতিল করে দেয় আর পাঁচটা রিলিজ ধরে ভুলে থাকা হয়:

> **Pine প্রতিটা call site-এ ইউজার ফাংশন INLINE করে, তারপর compiled টোকেন গোনে। একটা টোকেনের দাম = তার ফাংশনের call-site সংখ্যা।**

MODULE 8B ছিল **একবার** কল হওয়া annotation — মানে source টোকেন হিসেবে ফাইলের সবচেয়ে সস্তা কোড, আর মোছার জন্য সবচেয়ে খারাপ পছন্দ। দামি কোড হলো যেটা দু-বার বা বিশ-বার inline হয়।

পুরো ফাইলে `body × call-sites` মেপে পাওয়া গেল: **33 000 source টোকেনের উপরে আরও ~33 000 টোকেনের inline expansion**। এই রিলিজ সেটাই খরচ করে — **কপি সরিয়ে, ফিচার নয়।**

### ♻️ Reclaim — একটাও engine / gate / grade / input / default / alert নয়

| # | কী | ≈ টোকেন | কীভাবে |
|---|---|---|---|
| **R10** | **স্টেট মেশিন একবার কম্পাইল হয়** | **2 490** | `f_setupAdvance` 2 504 টোকেন, দুটো call site → compiled প্রোগ্রামে **দুটো পূর্ণ কপি**, ফাইলের সবচেয়ে বড় এন্ট্রি। এখন `for` লুপ থেকে চলে (এক call site), ফল দুটো দু-স্লট array-তে |
| **R5** | zone creation একবার | 1 960 | `f_mkZone` (544) নিজে inline করে `f_gradeZone` (346), `f_newZone` (289) **দুবার**, `f_zoneProv` (139) |
| **R6** | ডিবাগ প্যানেলের ১৪টা ownership row | 1 365 | `f_dbgTxt` তিনটা cell লেখে, ১৪ বার inline হতো → এক array + এক লুপ। v7.6-এর R2, যে row-গুলোতে পৌঁছায়নি সেখানে |
| **R7** | পাঁচটা chip জোড়া → পাঁচটা single | 810 | `f_chip` প্রতি site 135। CISD / IFC / external / internal structure — প্রতিটা জোড়া **গঠনগতভাবে পারস্পরিক-বর্জনশীল** |
| **R9** | trap watch একবার | 430 | একই লুপ, একই array, একই threshold |
| **R8** | `f_oppLiq` প্রতি সাইডে একবার | 430 | `f_tp` দুবার inline হয় আর ভিতরে নিজেই 216-টোকেনের scan ডাকত → **চার কপি**, অথচ উত্তরটা per-side আর call site এক লাইন পরেই সেটা বের করে |

**R10-এর নিরাপত্তা, স্পষ্ট করে** (কারণ এটা engine): একটা function body এক bar-এ দুবার চললে বিপদ **শুধু তখনই** যখন তার নিজের STATE থাকে — `var`, `ta.*`, বা ফাংশনের **ভিতরে হিসাব করা** মানের history। ৪৭০ লাইন যান্ত্রিকভাবে যাচাই: **শূন্য** `var`, **শূন্য** `ta.*`, **শূন্য** `request.*`, **শূন্য** `barstate.*`; আর একমাত্র ছয়টা history রেফারেন্স (`bullFVG[1]`, `bearFVG[1]`, `low[1..3]`, `high[1..3]`) হলো **GLOBAL series-এর constant-offset indexed read** — ওগুলো ওই series-এর নিজের bar history-তে resolve হয়, body যতবারই চলুক একই পড়ে। মেশিনের সব state থাকে যে `Setup` অবজেক্ট হাতে দেওয়া হয় তার ভিতরে, আর Pine UDT **reference-এ** পাঠায়।

### ✂️ কাটা — দুটো, দুটোই এমন কিছুর পুনরাবৃত্তি যা থেকে যাচ্ছে

**9 ·** `f_reason` + entry লেবেলের reason line (≈ 585; 292 টোকেন দুবার inline)। এর প্রতিটা clause ডিবাগ প্যানেলের একটা row-ই আবার বলে: event + graded raid, PD array + tier, MSS kind, displacement, gap/OTE/IDM, narrative verdict, producer + grade, RR + room, descriptor, run + chop। **entry লেবেলের নিজের দুই লাইন থাকে** — grade, direction, score, RR, producer tag, tier, raid grade, REVERSAL, session।

**10 ·** দুটো `run` chip (≈ 270)। ডিফল্টে **OFF** ছিল। run এখনো classify হয়, fade gate করে, ড্যাশবোর্ডের Run row-তে ছাপে, `[LIQ]` অ্যালার্ট দেয়।

### 🧮 হিসাব

**≈ 7 800 টোকেনের inline expansion সরানো হয়েছে।** v7.9→v7.10-এর মাপা 0.55-এ ≈ **4 300 compiled**, ঘাটতি 2 227-এর বিপরীতে। ইচ্ছাকৃত হতাশাবাদী 0.35-এও ≈ **2 730** — তাও পার হয়। Main body **951** statement (lineage-এর গ্রহণযোগ্য 2 034-এর অনেক নিচে), তাই CE10295 প্রশ্নই ওঠে না — উপরের প্রতিটা লুপ main body-কে statement **ফেরত দেয়**।

**ইঞ্জিন অক্ষত, এবং এবার সবচেয়ে কড়া অর্থে:** কোনো threshold, gate, grade, score term, tier, stop, target, dedupe rule, producer rank বা state transition সম্পাদনা করা হয়নি। শুধু **একই কোড কতবার compiled প্রোগ্রামে কপি হয়** সেটা বদলেছে।

### ⚠️ এখনো `CE10117` এলে

আগে ডিস্ক থেকে ফাইল নতুন করে কপি করুন। এই build **32 960 raw**, **29 130 inline-expanded function weight** (v7.10: 33 116 ও ≈ 36 900)। তারপর একই মেট্রিক এই ক্রমে — সবই কপি, কোনোটাই ফিচার নয়:

| # | লিভার | ≈ টোকেন |
|---|---|---|
| R11 | `f_dRow` 71 × 17 ড্যাশবোর্ড row — R6-এর মতো array + loop | 1 207 |
| R12 | `f_qPush` 68 × 20 registration site — আটটা স্বাভাবিক জোড়া (PDH/PDL, PWH/PWL, HTF, TL, EXT, session) | 1 360 |
| R13 | `f_newZone` 289 × 4 — rejection block-এর দুটো site mirror, এক লুপে মেলে | 1 156 |
| R14 | `f_prod` (552×2), `f_score` (503×2), `f_structUpdate` (479×2), `f_grade` (314×2) — R10-এর চিকিৎসা। `f_structUpdate`-এ সাবধান: `pvLen` **simple**, লুপে simple-ই রাখতে হবে | ~3 700 |

**ডিবাগ প্যানেল কখনোই নয়, আর ফিচার কখনোই নয়** — 0.55 compiled per source token-এ, annotation মোছা compiled বাজেট কেনার সবচেয়ে দামি উপায়।

---

## 🟣 v7.10 — দ্বিতীয় `CE10117`, এবং যে মডেলটা ভেঙে গেল

TradingView দ্বিতীয়বার একই এরর দিল:

> `CE10117` — compiled code contains too many tokens: **103 567**. The limit is **100 256**. → **3 311 বেশি।**

### 🚨 প্রথমে সংখ্যাটা সৎভাবে পড়া দরকার — কারণ এটা মডেল ভেঙে দেয়

| build | raw source token | compiled (মাপা) |
|---|---|---|
| v7.8 | 35 426 | **100 677** |
| v7.9 | **35 080** (৩৪৬ কম) | **103 567** (২ ৮৯০ বেশি) |

রॉ টোকেন **কমেছে**, compiled **বেড়েছে**। v6.3 থেকে এই lineage-এর প্রতিটা হেডার যে সরলরেখায় বাজেট হিসাব করে এসেছে, এই দুটো তথ্য সেই রেখায় একসাথে বসে না। তাই এই রিলিজ ওই রেখাকে আর বিশ্বাস করে না।

দুটো ব্যাখ্যা সম্ভব, এখান থেকে কোনোটাই প্রমাণ করা যায় না:

1. **compiled খরচ কেবল raw source টোকেনের ফাংশন নয়।** যুক্তিসঙ্গত — v7.9-এর R1 পাঁচটা ভ্যালুকে দুবার-inlined একটা ফাংশনের **ভিতর থেকে বের করে** আটটা **global series declaration**-এ বসিয়েছে। inlined body-র ভিতরের tuple slot আর global series এক জিনিস নয়; global series কম্পাইলারের কাছে first-class entity।
2. **103 567 সংখ্যাটা ডিস্কের v7.9-এর নয়** — অন্য কিছু পেস্ট হয়েছিল।

কাটার আগে ফাইল যাচাই করা হয়েছে: প্রতিটা module-এর একটাই কপি, `f_prod` tuple arity 21 ↔ 21, কোনো duplicate block নেই, CRLF অক্ষত।

### ✅ তাই এই রিলিজ আর আন্দাজ করে না

সরানো হয়েছে **1 964 raw টোকেন**। lineage-এর **সবচেয়ে কম** observed অনুপাতেও (2.27, v6.3-এর মাপা পয়েন্ট থেকে) এটা ≈ **4 460 compiled** — ঘাটতি 3 311-এর চেয়ে অর্ধেকের বেশি বড়। v7.8-এর মাপা 2.842-এ ≈ **5 580**। অনুপাত **1.7-এর উপরে হলেই** ফিট করে।

| build | raw | মন্তব্য |
|---|---|---|
| v7.8 | 35 426 | 100 677 compiled (মাপা) |
| v7.9 | 35 080 | 103 567 compiled (মাপা) |
| **v7.10** | **33 116** | **−1 964 raw v7.9 থেকে** |

### ✂️ যা খরচ হয়েছে — পুরোটাই annotation, কিছুই engine নয়

| # | কাটা | কী যায় | কী থাকে |
|---|---|---|---|
| **5** | **MODULE 8B · liquidity marking layer** (≈ 3 960 compiled, v6.3-এ মাপা; v6.0 থেকে lineage-এর নিজস্ব প্রথম lever) | BSL/SSL লেবেল, strength ★, EXT/INT ট্যাগ, cluster টেক্সট, lifecycle শব্দ; `f_lqIsExt` · `f_lqScore` · `f_lqClass` · `f_lqState` · `f_lqCluster` · `f_lqClear` · `f_lqSideCol` · `f_lsStars` · `f_lsMin` · `LQ_EXT_PAD` · `LS_*` · ④b-র ১২টা ইনপুট · `Pool.lstr/lscore/cluN/cluRep/isExt` | **পুরো registry (MODULE 7)** — প্রতিটা pool-এর লাইন, kind অনুযায়ী রং, style, width, lifecycle (raid = dashed, break = dotted), raid grading, descriptor। `kmask` ও `legs` **থাকে** — target ranking আর prune ওগুলো পড়ে |
| **6** | developing-setup `⋯` preview + `showDev` / `devBar` | মাত্র চলতি bar-এর ম্লান ইঙ্গিত | ডিবাগ প্যানেল একই stage একই bar-এ বলে — ওটাই ওর কাজ |
| **7** | ◂ target BSL / SSL লেবেল | ডানপাশের দুটো লেবেল | ড্যাশবোর্ডের **"Liquidity"** row একই দুটো ranked লেভেল ট্যাগসহ ছাপে |
| **8** | premium/discount shading + dealing-range EQ + OTE box, সাথে `showFlow` / `showRange` | দুটো বক্স আর একটা লাইন | **ইঞ্জিন অক্ষত**: `rangeOK` · `eqLvl` · `pdPos` · `premOK/discOK` · `inDiscExt/inPremExt` · OTE band সব MODULE 8-এ, আগের মতোই gate ও score করে। ড্যাশবোর্ডের **PD** row সংখ্যাটা ছাপে |

### 🟢 যা এখনো আছে — এটাই আসল কথা

প্রতিটা engine, producer, gate, grade, score block, tier, stop, target, dedupe rule, state machine। pool registry ও তার লাইন। zones, FVG lifecycle, breaker / mitigation / IFVG / BPR, order block, rejection block। HTF POI box, locked-FVG box, NEXT BUY/SELL লেবেল, reason line সহ entry লেবেল, entry/SL/TP ladder, প্রতিটা sweep ও raid মার্ক, session ও volatility shade। **MTF 5m · 15m · 1H · 4H ড্যাশবোর্ড ল্যাডার (v7.7)।** **MODULE 16C trade management ও পাঁচটা `[TRADE]` অ্যালার্ট (v7.8)।** প্রতিটা ইনপুট ডিফল্ট, প্রতিটা অ্যালার্ট **নাম**, আর **ডিবাগ প্যানেল** — যেটা কখনোই currency নয়।

**ইঞ্জিন অক্ষত:** v7.10 ঠিক সেই ট্রেডগুলোই emit করে যা v7.9 করত — একই দামে, একই bar-এ।

### ⚠️ এখনো `CE10117` এলে

**আগে ডিস্ক থেকে ফাইলটা নতুন করে কপি করুন।** v7.9-এর ফলটা এই ফাইলের কোনো মডেলেই বসে না, আর stale paste সবচেয়ে সস্তা ব্যাখ্যা — সেটা আগে বাদ দিন। এই build **33 116 raw** (v7.9 = 35 080, v7.8 = 35 426)।

তারপর এই ক্রমে, কোনোটাই engine নয়:

| # | কাটা | ≈ raw |
|---|---|---|
| 9 | NEXT BUY / SELL POI লেবেল + zone-border highlight | ≈ 200 |
| 10 | `f_reason` ও entry লেবেলের reason line | ≈ 250 |
| 11 | HTF POI box + locked-FVG box + `f_ctxBox` | ≈ 150 |

**ডিবাগ প্যানেল কখনোই নয়।**

---

## 🔵 v7.9 — কম্পাইল ফিক্স (মাপা হয়েছে, আন্দাজ নয়)

TradingView v7.8-এর উত্তর দিয়েছে একটা সংখ্যা দিয়ে:

> `CE10117` — compiled code contains too many tokens: **100 677**. The limit is **100 256**. → **421 বেশি।**

v7.8-এর হেডার আন্দাজ করেছিল ≈ 100 600 এবং স্পষ্ট বলেছিল যে এটা ক্যাপের উপরে। **সেটা ৭৭ টোকেনের ব্যবধানে সঠিক ছিল** — তাই সেখানে ছাপানো cut order-টাই এই রিলিজে প্রয়োগ করা হয়েছে। দ্বিতীয়বার আন্দাজ করতে হয়নি।

### 📐 যে ক্যালিব্রেশনটা এটা দিল (লিখে রাখার মতো)

**v7.8 = 35 426 raw source টোকেন → 100 677 compiled, মাপা।**

গড়ে **2.842 compiled per raw token**। আর এই lineage-এর প্রতিটা fit-এর intercept **নেগেটিভ**, তাই **marginal রেট গড়ের চেয়ে বেশি** — একটা টোকেন সরালে অন্তত 2.842 পাওয়া যায়, কম নয়।

v7.9 সরিয়েছে **346 raw টোকেন** → ≈ **980 compiled** → নামার কথা **≈ 99 700**, ক্যাপের **≈ 550 নিচে**। ইচ্ছাকৃতভাবে হতাশাবাদী 2.0 ধরলেও ≈ 99 985 — তাও ফিট করে।

### ♻️ Reclaim — কোনো আচরণ বদলায়নি, কিছু হারায়নি

| # | কী | কেন নিরাপদ |
|---|---|---|
| **R1** | `f_prod`-এর **৫টা স্লট** (`hp` · `mo` · `rtq` · `fvgE` · `poiE`) বাদ, tuple 26 → 21 | প্রতিটাই `prod` থেকেই derive করা যায়: `hp` **হলো** `pr == PR_FEM` (pr আসেই `poiIsHtf` থেকে), `mo` = `pr > 0 and pr < PR_TRAP`, বাকি তিনটা সরাসরি যে অবজেক্ট লিখেছিল তার থেকেই পড়া। `f_prod` **দুবার inline** হয়, তাই প্রতিটা স্লটের দাম দ্বিগুণ ছিল |
| **R2** | MTF ল্যাডারের agreement অঙ্ক — bull count + bear count + total (৩টা চার-টার্ম এক্সপ্রেশন) → **একটা net** | প্রতিটা usable rung নিজের ±1 দেয়, তাই `mtfNet == mtfN` = সর্বসম্মত bull, `−mtfN` = সর্বসম্মত bear। **চারটা rung (5m·15m·1H·4H) অক্ষত** |
| **R3** | `f_score`-এর **৫টা block sub-total** বাদ (`ctxL/S`, `liqL/S`, `poiL/S`, `trgL/S`, `exeL/S`) | ১০টা গ্লোবাল, **কোথাও পড়া হতো না** — V5.5-E6 রুল। অঙ্ক অপরিবর্তিত, প্রতিটা পয়েন্ট total-এ আছেই। `ev` রাখা হয়েছে (ডিবাগ প্যানেল ছাপে) |
| **R4** | `Trade.sl0` বাদ | `mfe` চলে যাওয়ার পর এটার একমাত্র reader ছিল না — write-only হয়ে গিয়েছিল |

### ✂️ কাটা হয়েছে — v7.8-এর ছাপানো ক্রমেই

1. **`tradeLife`** ইনপুট — ট্রেড TP3 বা stop পর্যন্ত ফলো হয়, যা ডিফল্টে এমনিতেই হতো
2. **`Trade.mfe`** — ড্যাশবোর্ড আর best excursion (R-এ) দেখায় না
3. **BE হলে আঁকা SL লাইনের redraw** — ⚠️ **stop তবু সরে**; ট্র্যাকিং, ড্যাশবোর্ডের BE ট্যাগ আর `[TRADE] Break-even` অ্যালার্ট সবই অপরিবর্তিত, শুধু চার্টের লাইনটা আর অনুসরণ করে না
4. **চার্টের TP/SL/BE চিপ** (+ `tdDirE`) — **পাঁচটা `[TRADE]` অ্যালার্টই ফায়ার করে**, row 17-ও state দেখায়

১-৪ ছিল v7.8-এর পুরো **সুবিধা-স্তর**। **ইঞ্জিন অক্ষত** — v7.9 ঠিক সেই ট্রেডগুলোই emit করে যা v7.8 করত, একই দামে।

### ⚠️ এখনো `CE10117` এলে

পরের lever lineage-এর নিজস্ব স্থায়ী প্রথমটা, আর উপরের সবকিছুর চেয়ে অনেক বড়:

**MODULE 8B — লিকুইডিটি মার্কিং লেয়ার (≈ 3 960 compiled)।** এটা **বিশুদ্ধ annotation** — BSL/SSL লেবেল, strength star, EXT/INT ট্যাগ, cluster টেক্সট। পুল **লাইন**, রেজিস্ট্রি, লাইফসাইকেল আর প্রতিটা সিগন্যাল MODULE 7-এ, ওগুলো ছোঁয়াই হয় না। `LQ_EXT_PAD = 0.15` থেকে `shown += 1`-এ শেষ হওয়া render ব্লক পর্যন্ত মুছুন, সাথে `lqMark` … `lqRaidChar` ইনপুট গ্রুপ।

**ডিবাগ প্যানেল কখনোই নয়।**

---

## ০. এক লাইনে রায়

এই ফাইলটা **ইন্ডিকেটর না, একটা ট্রেড ইঞ্জিন** — এবং এটা আমার দেখা Pine কোডের উপরের ৫%-এ পড়ে। কজ্যালিটি (causality), ইভেন্ট ওনারশিপ, নন-রিপেইন্টিং HTF রিড, হার্ড গেট বনাম সফট স্কোরের বিভাজন — সবই ঠিকভাবে করা।

**কিন্তু** ১৪টা আসল ডিফেক্ট আছে, যার মধ্যে **৪টা সরাসরি ট্রেড বদলে দেয়** এবং **২টা নীরবে ভালো সেটআপ মেরে ফেলে**। মূল প্যাটার্ন একটাই: *যে ইনপুটগুলো ডকুমেন্টে একটা জিনিস প্রতিশ্রুতি দেয়, কোডে অন্য একটা ছোট কনস্ট্রেইন্ট তার আগেই কার্যকর হয়ে যায়।*

---

## ১. আর্কিটেকচার ম্যাপ (যা আছে)

| Module | কাজ | রায় |
|---|---|---|
| 1 | Inputs (১৯ গ্রুপ) | ✅ সুসংগঠিত, tooltip-এ কারণ লেখা |
| 2 | Constants + helpers | ✅ magic number নেই |
| 3 | Candle anatomy · CISD · IFC | ✅ `confirmed`-gated |
| 4 | Structure (internal + external, দুটো আলাদা instance) | ✅ BOS/CHoCH/MSS/CISD আলাদা শব্দভাণ্ডার |
| 5 | Sessions · Killzone · Silver Bullet | ✅ display আর state আলাদা |
| 6 | HTF context engine | ✅ `expr[1] + lookahead_on` — নন-রিপেইন্টিং |
| 7 | Liquidity registry (Pool UDT + lifecycle) | ⚠️ §3.1 দেখুন |
| 8 / 8B | Dealing range · PD · OTE · marking layer | ✅ display-only আলাদা |
| 9 | Supply/Demand · FVG · OB · BPR · IFVG · tier | ⚠️ §3.2, §3.3, §3.5 |
| 11 / 11B | Trap engine · Run · Congestion · Regime · AMD | ⚠️ §3.6, §4.1 |
| 12 | Setup state machine (0→9) | ⚠️ §3.4, §4.6 |
| 13 | Alignment score (soft, 0-100) | ✅ সব ingredient owned |
| 14 / 14B | Base gates · dedupe · SL/TP/RR primitives | ⚠️ §4.2 |
| 15 | Trade engine (একমাত্র কর্তৃপক্ষ) | ✅ producer rank → risk → hard gate → grade → arbitration |
| 16-20 | Visual · Dashboard · Debug · Alerts | ✅ কিছুই decide করে না |

**কজ্যাল চেইন যেটা এনফোর্স হয়:**

```
HTF context → liquidity target LOCK → সেই pool-ই RAID → raid-এর গায়ে POI
→ post-raid MSS → displacement → সেই displacement-এর FVG → FVG retest = ENTRY
```

প্রতিটা স্টেজে bar stamp আছে, `f_narrOk()` এন্ট্রির মুহূর্তে পুরো চেইন আবার স্বাধীনভাবে যাচাই করে। এটা ঠিক আছে।

---

## ২. যা ভালো করা হয়েছে (রেখে দিন, ভাঙবেন না)

1. **নন-রিপেইন্টিং HTF** — প্রতিটা `request.security`-এ `[1]` ভেতরে + `lookahead_on` বাইরে। এটাই একমাত্র leak-free + stable কম্বিনেশন। `f_tfUp()` চার্টের নিচের TF-এ কল ব্লক করে (v7.2 BUG-01)। **৬টা call site**, TV লিমিটের অনেক নিচে।
2. **ইভেন্ট আইডেন্টিটি** — এক ফিজিক্যাল লিকুইডিটি ইভেন্ট = এক `Pool` = এক `id`। JUDAS / RUN EXH / TRAP সব শুধু **descriptor**, আলাদা কনফার্মেশন না। স্কোরে এদের জন্য capped ৬ পয়েন্ট, যা LIQUIDITY ব্লক (২৫) ছুঁতে পারে না। ইনফ্লেশন-প্রতিরোধ স্ট্রাকচারাল।
3. **`f_geq()` float hygiene** — `rrMult == rrAplus == 2.0`-এ `1.9999999997` বাগ ধরা পড়েছে ও ঠিক হয়েছে।
4. **`rrAn / rrAPn / minRiskN / maxRiskN` নরমালাইজেশন** — ইউজার উল্টো ভ্যালু দিলেও ল্যাডার ভাঙে না।
5. **TP2 কখনো synthetic না** (`s2 == 0` → হার্ড ব্লক)। এটা v5-এর সবচেয়ে বড় বাগ ছিল, ঠিক আছে।
6. **`array.size() > 0` গার্ড** — ৩৫টা লুপের প্রতিটাতে আছে। Pine-এ `for i = 0 to -1` উল্টো চলে ও crash করে; এখানে সেই ঝুঁকি নেই। ✅ verified।
7. **V7.6 F-02 (CE entry)** — zone midpoint শুধু তখনই এন্ট্রি প্রাইস হয় যখন `ceRaw >= low and ceRaw <= high`। RR স্ফীতি বন্ধ।
8. **ডিবাগ প্যানেলের `f_blockReason`** — `go` দিয়ে short-circuit, শুধু last bar-এ বিল্ড হয়।

---

## ৩. P0 — যে ডিফেক্টগুলো সরাসরি ট্রেড বদলায়

### 3.1 🔴 `reactWin` নীরবে `sweepLook` ও `mssWin` বাতিল করে দেয়

**কোথায়:** `f_poolScan()` — লাইন ~3040-3060

```pine
if p.state == PS_RAID or p.state == PS_REACT
    if sg * (close - p.px) > 0
        p.state := PS_DONE                     // reclaim = break
    else if p.state == PS_RAID
        if bar_index - p.raidBar > reactWin     // ← reactWin = 6 (default)
            p.state := PS_DONE                  // stale
        else if ... dispDn/shiftDn ...
            p.state := PS_REACT
    else if bar_index - p.raidBar > sweepLook or ...   // ← এই লাইনে শুধু PS_REACT পৌঁছায়
        p.state := PS_DONE
```

**সমস্যা:** শেষ `else if` (যেখানে `sweepLook = 15` আছে) শুধুমাত্র `PS_REACT` স্টেটের pool-এর জন্য reachable। একটা raid যদি ৬ বারের মধ্যে **চার্ট-ওয়াইড** displacement/shift না দেখে, সেটা `PS_DONE` হয়ে যায়।

**ফলাফল (ট্রেড-চেঞ্জিং):**

- `sweepLook` tooltip বলে "A liquidity raid can seed a setup for this many bars" (১৫) — বাস্তবে **৬**।
- `mssWin = 12` বলে "raid→POI ১২ বার পর্যন্ত" — বাস্তবে ৬ বারের পর pool মরে যায় এবং মেশিন stage 2→3-এ `"target pool broken or expired"` দিয়ে kill হয়।
- সবচেয়ে বাজে: raid → **রিট্রেসমেন্ট → তারপর** POI → MSS — ICT-র সবচেয়ে ক্লাসিক দেরিতে আসা সেটআপ — কখনোই বাঁচে না।

**ফিক্স:**

```pine
// PS_RAID staleness-এর জন্য দুটো আলাদা ক্লক:
//   reactWin  = "এতবারের মধ্যে reaction না এলে grade আর ওঠে না"
//   sweepLook = "এতবার পর্যন্ত setup এটা claim করতে পারে"
else if p.state == PS_RAID
    if bar_index - p.raidBar > math.max(reactWin, sweepLook)
        p.state := PS_DONE
    else if bar_index > p.raidBar and (p.buySide ? (dispDnBar or shiftDn) : (dispUpBar or shiftUp))
        p.state := PS_REACT
```

অথবা `reactWin`-এর minval/default `sweepLook`-এর সাথে টাই করে দিন এবং tooltip-এ সত্যিটা লিখুন।

---

### 3.2 🔴 Zone prune একটা লাইভ সেটআপের বাউন্ড POI মুছে ফেলে — tier জমে যায়

**কোথায়:** Module 9, লাইন ~3965-3995 (`while cnt > maxZones`)

```pine
if confirmed
    for side = 0 to 1
        ...
        while cnt > maxZones                  // maxZones default = 8
            // সবচেয়ে পুরনো zone খোঁজে — bound কিনা দেখে না
            Zone o = array.get(zones, oldIx)
            box.delete(o.bx)
            line.delete(o.mid)
            array.remove(zones, oldIx)        // ← s.poiZone এখনো এটাকে ধরে আছে
```

**সমস্যা:** Pine-এ `array.remove` অবজেক্ট ডিলিট করে না — `upS.poiZone` রেফারেন্স বেঁচে থাকে। কিন্তু `f_regrade(z)` **শুধু `zones` অ্যারের উপর লুপে** চলে। তাই:

- `s.poiTier := f_zoneTier(s.poiZone)` চিরকাল **পুরনো, আশাবাদী tier** ফেরত দেয়।
- `f_zoneDead(z)` = `z.signaled or z.tier > minTier` — tier ফ্রোজেন, তাই এটা কখনো true হবে না।
- `z.state`, `z.mitN` আপডেট হয় না → "50% mitigated → T2" ল্যাডার কাজ করে না।
- চার্টে বক্স মুছে গেছে, কিন্তু মেশিন সেই POI-তেই ট্রেড করছে।

**প্রভাব:** `maxZones = 8` ডিফল্টে intraday-তে এটা প্রায়ই ঘটে (OB + FVG + REJECTION + BPR সব এক সাইডে জমে)। একটা T1 সেটআপ এমন একটা array-তে এক্সিকিউট হতে পারে যেটা আসলে ইতিমধ্যে full-fill হয়ে গেছে।

**ফিক্স (দুটোর যেকোনো একটা):**

```pine
// A · bound zone কখনো prune করবেন না
bool bound = (not na(upS.poiZone) and upS.poiZone.id == z.id) or
             (not na(dnS.poiZone) and dnS.poiZone.id == z.id)
if z.isSupply == sup and not bound and (oldIx == -1 or nz(z.bornBar,0) < oldBar)
```

```pine
// B · prune করলে সাথে সাথে সেটআপ kill করুন
if not na(upS.poiZone) and upS.poiZone.id == o.id
    upS.poiTier := 3          // f_zoneDead পরের বারে ধরবে
```

**A ই সঠিক** — ওটা ওই সেটআপের evidence, সবচেয়ে পুরনো বলে ফেলে দেওয়ার জিনিস না।

---

### 3.3 🔴 `f_mkZone` ডিডুপ লুপ — ভালো zone মুছে ফেলে, রিপ্লেসমেন্ট বানায় না

**কোথায়:** লাইন 4173-4194

```pine
for i = array.size(zones) - 1 to 0
    Zone z = array.get(zones, i)
    bool ov = not (zBot > z.top or zTop < z.bot)
    ...
    if z.isSupply == isSupply and ov
        if z.signaled or z.tier <= tZ
            dup := true                 // ← break নেই
        else
            box.delete(z.bx)
            line.delete(z.mid)
            array.remove(zones, i)      // ← dup true হয়ে গেলেও এটা চলে
if not dup
    ... নতুন zone বানানো হয় ...
```

**সমস্যা:** নতুন গ্যাপ যদি **একাধিক** same-side zone-এর সাথে ওভারল্যাপ করে (দাম কম্প্রেসড থাকলে খুব সাধারণ) এবং —

- index `i` বড়-তে একটা দুর্বল zone (tier > tZ) → **মুছে ফেলা হলো**,
- তারপর index `i` ছোট-তে একটা শক্তিশালী zone (tier ≤ tZ) → `dup := true`,
- ফলে নতুন zone **তৈরি হয় না**,
- নেট ফলাফল: একটা লাইভ POI হারিয়ে গেল, বিনিময়ে কিছুই আসেনি।

**ফিক্স:** দুই পাসে করুন — আগে সিদ্ধান্ত, পরে মুছুন।

```pine
// পাস ১ — শুধু সিদ্ধান্ত
for i = 0 to array.size(zones) - 1
    Zone z = array.get(zones, i)
    if z.isSupply == isSupply and not (zBot > z.top or zTop < z.bot)
        if z.signaled or z.tier <= tZ
            dup := true
            break
// পাস ২ — শুধু dup না হলে দুর্বলগুলো সরান
if not dup
    for i = array.size(zones) - 1 to 0
        ...
```

---

### 3.4 🔴 HTF POI-এর কোনো identity নেই — FEM-এর tier decay নীরবে রিসেট হয়

**কোথায়:** `f_htfPoi()` (লাইন ~2580) + `f_htfTier()` (লাইন 4844)

```pine
f_htfTier(bool isL, int in0) =>
    int(math.min(1 + math.max(nz(isL ? hPoiBIn : hPoiSIn, 0) - in0 - 1, 0)
        + ((isL ? htfDir >= 0 : htfDir <= 0) ? 0 : 1), 3))
```

`f_htfPoi()`-এর ভেতরে নতুন HTF gap তৈরি হলে:

```pine
if low > high[2] and _dU and (not hPoiNeedDir or _dir > 0)
    bTop := low
    bBot := high[2]
    bIn  := 0          // ← কাউন্টার রিসেট
    bInZ := false
```

**সমস্যা:** সেটআপ `s.poiTop/s.poiBot`-এ **পুরনো** array-র কোঅর্ডিনেট ধরে রেখেছে, কিন্তু `s.poiIn0` তুলনা করছে **নতুন** array-র `bIn`-এর সাথে। নতুন `bIn = 0`, `in0` ছিল ধরুন 2 → `math.max(0 - 2 - 1, 0) = 0` → **tier আবার 1**।

**ফলাফল:** P1-2 ফিক্স ("HTF POI tier ডাইনামিক, শুধু খারাপ হতে পারে") নীরবে উল্টে যায়। একটা মিটিগেটেড HTF array-তে বসা FEM সেটআপ আবার T1 / A+ eligible হয়ে যায়। FEM `PR_FEM = 1` — সর্বোচ্চ র‍্যাঙ্কের producer, তাই এই ভুল tier সব কিছুকে হারিয়ে দেয়।

**ফিক্স:** HTF POI-কে একটা identity দিন এবং সেটাও feed-এ পাবলিশ করুন।

```pine
// f_htfPoi() ভেতরে
var int bSeq = 0
if low > high[2] and _dU and ...
    bSeq += 1                 // নতুন array = নতুন id
    ...
[bTop[1], bBot[1], sTop[1], sBot[1], bIn[1], sIn[1], bSeq[1], sSeq[1]]
```

```pine
// Setup UDT-তে: int poiHtfSeq = 0
// invalidation-এ:
else if s.st >= ST_POI and s.poiIsHtf and s.poiHtfSeq != (isL ? hPoiBSeq : hPoiSSeq)
    blk  := "HTF POI replaced — the array this setup bound no longer exists"
    kill := true
```

---

### 3.5 🟠 `f_gradeZone` শুধু "সবচেয়ে টাটকা" raid দেখে — সত্যিকারের owner raid মিস করে

**কোথায়:** লাইন ~3770

```pine
float rpx  = isSupply ? anyHiExt  : anyLoExt      // f_findRaid → সবচেয়ে fresh raid
bool  liq  = not na(rpx) and free and f_recent(rbar, sweepLook) and
     (isSupply ? rpx <= zTop + sdRaidAtr*atr and rpx >= zBot - poiBindAtr*atr : ...)
```

`f_findRaid()` ওই সাইডের **একমাত্র সবচেয়ে নতুন** raid ফেরত দেয়। কিন্তু একই সাইডে একাধিক live raid থাকতে পারে (PS_RAID + PS_REACT)। যে raid আসলে এই zone-এর গায়ে বসে আছে সেটা যদি সবচেয়ে fresh না হয়, `liq` **false** হবে।

**ফলাফল:** zone T1 না পেয়ে T3-তে জন্মায়। এবং v7.6-এর `tierW` র‍্যাচেটের কারণে (F-05) **এটা আর কখনো উন্নত হতে পারে না**। একটা সত্যিকার A+ array চিরকালের জন্য untradeable।

**ফিক্স:** zone-এর জ্যামিতির ভেতরে থাকা **সেরা** raid খুঁজুন, fresh-তমটা না।

```pine
f_raidAtZone(bool isSupply, float zTop, float zBot) =>
    Pool best = na
    if array.size(pools) > 0
        for i = 0 to array.size(pools) - 1
            Pool p = array.get(pools, i)
            if (isSupply ? p.buySide : not p.buySide) and (p.state == PS_RAID or p.state == PS_REACT)
                 and p.bound == 0 and not p.spent and f_recent(p.raidBar, sweepLook) and not na(p.raidExt)
                bool inside = isSupply
                     ? p.raidExt <= zTop + sdRaidAtr*atr and p.raidExt >= zBot - poiBindAtr*atr
                     : p.raidExt <= zTop + poiBindAtr*atr and p.raidExt >= zBot - sdRaidAtr*atr
                if inside and (na(best) or p.rq > best.rq or (p.rq == best.rq and p.raidBar > best.raidBar))
                    best := p
    best
```

তারপর `f_gradeZone` ও `f_zoneProv` দুটোই এই অবজেক্ট থেকে পড়ুক।

---

### 3.6 🟠 `regime` classifier একটা ফিল্টার সুইচের উপর নির্ভরশীল

**কোথায়:** লাইন 4573-4586

```pine
congested = congGate != "Off" and congN >= 2
regime    = congested ? RG_CHOP : atrRel >= 1.4 ? RG_EXP : ...
```

`congGate = "Off"` করলে:

- `regime` **কখনো `RG_CHOP`** হয় না → ড্যাশবোর্ড চপি মার্কেটে "TREND"/"RANGE" দেখায়,
- `regDownL/S` ভুল পলিসি প্রয়োগ করে (চপ-এ RANGE policy),
- `f_score`-এর `ev` ডেবিট (-4) উধাও হয়ে স্কোর ফুলে যায়।

একটা **পরিমাপ** (congN) আর একটা **নীতি** (congGate) মিশে গেছে।

**ফিক্স:**

```pine
congMeasured = congN >= 2                          // পরিমাপ — সবসময়
congested    = congGate != "Off" and congMeasured  // নীতি — শুধু gate/grade-এর জন্য
regime       = congMeasured ? RG_CHOP : atrRel >= 1.4 ? RG_EXP : ...
```

এবং `f_score`-এ `cong` হিসেবে `congMeasured` পাঠান।

---

## ৪. P1 — অর্থবহ, কিন্তু P0 নয়

### 4.1 🟡 ট্রেন্ডলাইন লিকুইডিটি (§22) ডিফল্টে কার্যত মৃত

**কোথায়:** `f_trendline()`, লাইন 3209-3245

```pine
if not na(eph)
    tlHp2 := tlHp1 ; tlHb2 := tlHb1
    tlHp1 := eph   ; tlHb1 := bar_index - extPiv
    tlHn  := 0                 // ← প্রতিটা নতুন external pivot-এ touch কাউন্টার রিসেট
    tlHhit := false
```

`extPiv = 12` ডিফল্টে নতুন external pivot ঘন ঘন প্রিন্ট হয়। `tlMinTouch = 2` ছোঁয়ার আগেই কাউন্টার রিসেট হয়ে যায়। ফলে `PK_TL` pool প্রায় কখনোই রেজিস্টার হয় না — অথচ `f_kindPri(PK_TL) = 4` এবং স্কোরে ৫ পয়েন্ট বরাদ্দ।

**ফিক্স:** নতুন pivot এলে লাইনের **anchor** বদলান, কিন্তু touch history কেরি করুন যদি নতুন লাইনটা একই ঢালের হয়:

```pine
if not na(eph)
    bool sameSlope = not na(tlHp1) and eph < tlHp1        // এখনো descending highs
    tlHp2 := tlHp1 ; tlHb2 := tlHb1
    tlHp1 := eph   ; tlHb1 := bar_index - extPiv
    tlHn  := sameSlope ? tlHn : 0
    tlHhit := false
```

### 4.2 🟡 `f_dedupeOk` প্রাইস-ডিডুপ `lqTol` ব্যবহার করে না

```pine
ok := ok and math.abs(poolPx - lpx) > eqTol * atr      // ← eqTickMin floor নেই
```

কিন্তু রেজিস্ট্রি ফিউশন ব্যবহার করে `lqTol = math.max(eqTol * atr, eqTickMin * syminfo.mintick)`।

**প্রভাব:** tick-quantised ইনস্ট্রুমেন্টে (index, crypto perp) যেখানে `eqTickMin > 0` সেট করা, রেজিস্ট্রি দুটো লেভেলকে এক pool ধরে কিন্তু ডিডুপ ধরে না → **একই ফিজিক্যাল লেভেল দুবার ট্রেড হতে পারে**, যা `dedupePool` ঠিক এটাই আটকাতে চায়।

**ফিক্স:** `eqTol * atr` → `lqTol`।

### 4.3 🟡 `strictSeq` ইনপুট প্রায় নিষ্ক্রিয়, কিন্তু tooltip পুরো চেইনের দাবি করে

Tooltip: `ctxBar < tgtBar < raidBar ≤ poiBar < mssBar < dispBar ≤ fvgBar < retestBar`

বাস্তবে পুরো ফাইলে `strictSeq` মাত্র **২ জায়গায়**:

- লাইন 4943 — ctx armed হওয়া বারে target lock আটকানো,
- লাইন 4975 — raid lock bar-এর সমান হতে পারবে কি না।

বাকি পুরো চেইন `moved` ল্যাচ দিয়ে **সবসময়** এনফোর্সড। অর্থাৎ `strictSeq = false` করলে শুধু একটাই আসল লুজেনিং হয়: **lock bar-এর raid claim করা যায়** — যেটা ঠিক সেই retroactive claim যা V4-BUG-2 বন্ধ করেছিল।

**ফিক্স:** tooltip সত্য করুন, অথবা `strictSeq` সরিয়ে দিন এবং behaviour সবসময় strict রাখুন। নিষ্ক্রিয় ইনপুট মানে ইউজার ভাবে সে কিছু নিয়ন্ত্রণ করছে — করছে না।

### 4.4 🟡 `"Narrative only (A+)"` মোডে ELITE trap ঢুকে যায়

```pine
else if (allowAll or tel) and pa1          // tel = trapElite verdict
```

`allowAll` false হলেও `tel` true হলে trap producer চালু। v7.1-এ এটা ইচ্ছাকৃত ছিল (ELITE trap-এর নিজস্ব চেইন আছে), কিন্তু মোডের **নামটাই** "Narrative only"। একজন অপারেটর যে সবচেয়ে কড়া সেটিং বেছে নিয়েছে তার পাওয়া উচিত শুধু state machine।

**ফিক্স:** ড্রপডাউনে অপশনের নাম বদলান → `"Narrative only (+ elite trap)"`, অথবা `entryMode == "Narrative only (A+)"` হলে `tel` উপেক্ষা করুন।

### 4.5 🟡 `filtBias = "Off"` হলেও `request.security` চলে

```pine
biasTf   = biasFilter == "Off" ? timeframe.period : biasFilter
filtBias = biasFilter == "Off" ? 0 : nz(f_bias(biasTf), 0)
```

Pine টার্নারির **দুটো ব্রাঞ্চই** ইভ্যালুয়েট করে, তাই ফিল্টার বন্ধ থাকলেও একটা HTF সিরিজ খরচ হয়। শুধু পারফরম্যান্স, কারেক্টনেস না — কিন্তু এই ফাইলের টোকেন বাজেট টাইট, তাই গুনতে হয়।

### 4.6 🟡 Stage 2-এ target re-selection ঘড়ি রিসেট করে — jitter-এ সেটআপ অনাহারে মরে

```pine
Pool tp3 = isL ? tgtSellPool : tgtBuyPool
if not na(tp3) and tp3.id != s.tgtId
    s.tgtId  := tp3.id
    s.tgtBar := bar_index            // ← lock clock আবার শূন্য থেকে
```

`tgtDistW = 1.5` দূরত্ব পেনাল্টির কারণে দুটো কাছাকাছি ওজনের pool-এর মধ্যে র‍্যাঙ্কিং দাম নড়লেই উল্টাপাল্টা হতে পারে। প্রতিবার `tgtBar` রিসেট হলে `raidBar > tgtBar` শর্ত কখনো পূরণ হয় না।

**ফিক্স:** hysteresis দিন — নতুন pool-এর ওজন বর্তমানটির চেয়ে অন্তত একটা মার্জিন বেশি না হলে সুইচ করবেন না (Setup UDT-তে `float tgtW` রাখুন)।

---

## ৫. P2 — ছোট / ডকুমেন্টেশন

| # | বিষয় | ফিক্স |
|---|---|---|
| 5.1 | REJECTION block zone-এ `f_zoneProv` কল হয় না → `srcPoolId = 0` → S/D producer কখনো ট্রেড করতে পারে না, কিন্তু মেশিন bind করতে পারে। অসামঞ্জস্যপূর্ণ কিন্তু নিরাপদ। | ডকে লিখুন, অথবা provenance দিন |
| 5.2 | `f_zoneFlip`-এ `z.tier := isBrk and not z.isFvg ? 2 : 3` — FVG থেকে জন্মানো breaker কখনো T2 পায় না, শুধু IFVG প্রোমোশন পথে | ইচ্ছাকৃত হলে কমেন্টে স্পষ্ট করুন |
| 5.3 | `hPoiBIn`/`hPoiSIn` ড্যাশবোর্ডে "tested ×n" দেখায় কিন্তু এটা edge-triggered mitigation, dwell না — লেবেলটা বিভ্রান্তিকর | `"mitigated ×n"` |
| 5.4 | `POOL_CONSUME_ATR = 4.0` শুধু `PS_REACT` pool-এ প্রযোজ্য (`else if` চেইনের অবস্থানের কারণে) | ইচ্ছাকৃত কিনা যাচাই করুন |
| 5.5 | `f_lqCluster()` `p.isExt` / `p.lscore` শুধু `barstate.islast`-এ লেখে, কিন্তু ফিল্ডগুলো UDT-তে persist করে — history bar-এ stale মান থাকে। কেউ পড়ে না, তাই নিরাপদ। | কমেন্টে লিখুন |
| 5.6 | `eqNeedReact`-এর `phMin` পুশ হয় `ta.lowest(low, pivLen)` দিয়ে — এটা pivot-পরবর্তী বারগুলোও ধরে, তাই "reaction since that pivot" আসলে "reaction around that pivot" | সঠিক করতে হলে pivot bar থেকে গণনা |
| 5.7 | ফাইলের প্রথম ~১৪১৫ লাইন হেডার চেঞ্জলগ (৬৬০১-এর ২১%)। কম্পাইল টোকেন খায় না, কিন্তু মানুষের রিভিউ ক্ষমতা খায়। | চেঞ্জলগ আলাদা `.md`-তে সরান |

---

## ৬. পারফরম্যান্স ও বাজেট

- **Drawing objects:** `max_boxes/lines/labels = 500` — ঠিক আছে। `pools ≤ 60` লাইন + `zones ≤ 16` বক্স+লাইন + liquidity লেবেল ≤ 30 + trade লাইন 5। মার্জিন আছে।
- **`request.security`:** ৬টা call site। TV লিমিট ৪০। ✅
- **সবচেয়ে ভারী লুপ:** `f_mkZone` (nested zone scan, O(n)) + `f_setupAdvance`-এর POI scan (O(n), ×২ direction)। n ≤ 16। তুচ্ছ।
- **`f_poolPush` ইনলাইনিং:** কিউ প্যাটার্ন (`f_qPush`/`f_qFlush`) দিয়ে ১৬টা ইনলাইন কপি → ১টা। এটা চমৎকার সমাধান, রেখে দিন।
- **ঝুঁকি:** ফাইল টোকেন লিমিটের কাছাকাছি (হেডার বলছে ১০০ ২৫৬-এ CE10117 হিট করেছিল)। নতুন ফিচারের আগে পুরনো রিলিজের ইনলাইন ডুপ্লিকেশন খুঁজুন — এই রিলিজেই R1/R2 সেভাবে বাজেট বের করেছে।

---

## ৭. ফিক্স রোডম্যাপ (অগ্রাধিকার ক্রমে)

| ধাপ | কাজ | ঝুঁকি | প্রভাব |
|---|---|---|---|
| **1** | §3.1 — `reactWin`/`sweepLook` আলাদা ক্লক | কম | 🔴🔴🔴 অনেক বেশি valid সেটআপ বাঁচবে |
| **2** | §3.2 — bound zone prune করবেন না | কম | 🔴🔴🔴 stale-tier এক্সিকিউশন বন্ধ |
| **3** | §3.3 — `f_mkZone` দুই-পাস ডিডুপ | খুব কম | 🔴🔴 POI হারানো বন্ধ |
| **4** | §3.4 — HTF POI-এ sequence id | মাঝারি | 🔴🔴 FEM tier ratchet সত্য হবে |
| **5** | §3.5 — `f_raidAtZone()` | মাঝারি | 🔴🔴 T1 কভারেজ বাড়বে |
| **6** | §3.6 — `congMeasured` / `congested` আলাদা | খুব কম | 🟠 regime সঠিক হবে |
| **7** | §4.2 — `lqTol` ডিডুপে | খুব কম | 🟠 ডাবল এক্সিকিউশন বন্ধ |
| **8** | §4.1 — trendline touch carry | কম | 🟡 PK_TL জীবিত হবে |
| **9** | §4.3, §4.4 — tooltip/নাম সত্য করা | শূন্য | 🟡 অপারেটর বিভ্রান্তি কমবে |
| **10** | §4.6 — target hysteresis | কম | 🟡 jitter starvation কমবে |

---

## ৮. চার্টে কীভাবে যাচাই করবেন (প্রতিটা ফিক্সের জন্য)

1. **§3.1** — Debug panel চালু করুন (`showDebug`, `dbgVerbose`)। একটা raid ধরুন, `row 12 "raid"` দেখুন। যদি ৬-৭ বারের মধ্যে row 3 টিক মুছে গিয়ে `BLOCKED = "target pool broken or expired"` আসে, বাগ কনফার্মড। ফিক্সের পর ১৫ বার পর্যন্ত টিকবে।
2. **§3.2** — `maxZones = 2` করে দিন, `minTier = 3`। Debug row 13 (`POI · array`) একটা zone id দেখাবে যেটা চার্টে আর নেই। ফিক্সের পর হয় বক্স থাকবে, নয় সেটআপ kill হবে।
3. **§3.3** — কম্প্রেসড রেঞ্জে (Asia session) একই সাইডে ৩টা overlapping FVG আছে এমন জায়গা খুঁজুন। bar-by-bar রিপ্লেতে একটা বক্স হঠাৎ উধাও হবে অথচ নতুন কিছু আসবে না।
4. **§3.4** — `useFEM` on, `showPoi` on। একটা FEM সেটআপ stage 4+ থাকা অবস্থায় HTF POI বক্স জায়গা বদলালে debug row 13-এ tier `T2`/`T3` থেকে `T1`-এ ফিরে যাবে — সেটাই বাগ।
5. **§3.5** — একই সাইডে দুটো fresh raid থাকা অবস্থায় নতুন zone-এর tag দেখুন: T3 আসছে অথচ raid wick বক্সের ভেতরেই — বাগ।
6. **§3.6** — `congGate = "Off"` করুন, ড্যাশবোর্ড row 3 দেখুন: `chop 3/4` লেখা থাকবে কিন্তু regime `RANGE` — অসংগতি।

---

## ৯. শেষ কথা

কোডটার **ভিত্তি শক্ত** — v4 থেকে v7.6 পর্যন্ত প্রতিটা অডিটে যা ঠিক হয়েছে তা সত্যিই ঠিক হয়েছে, এবং কমেন্টগুলো আত্মপ্রতারণামূলক নয়, বরং অস্বাভাবিকভাবে সৎ।

এখন যে বাগগুলো বাকি সেগুলো **দ্বিতীয় প্রজন্মের বাগ**। প্রথম প্রজন্মে ছিল "একটা গ্লোবাল ফ্ল্যাগ একটা নির্দিষ্ট সেটআপের হয়ে দাম দিচ্ছে" — সেগুলো মারা হয়েছে। এখনকারগুলো হলো **"দুটো ঠিক জিনিসের মধ্যে ভুল ক্লক / ভুল লাইফসাইকেল"**:

- `reactWin` বনাম `sweepLook` — দুটো সঠিক ধারণা, ভুলভাবে সিরিয়ালে বাঁধা (§3.1)
- `zones` array বনাম `Zone` object — দুটো সঠিক জিনিস, একটা মরে গেলে অন্যটা জানে না (§3.2)
- HTF feed বনাম bound setup — দুটো সঠিক, কিন্তু মাঝে কোনো identity নেই (§3.4)

**তিনটার মূল প্রতিকার একটাই নীতি:**

> যে অবজেক্ট একটা লাইভ সেটআপ ধরে রেখেছে, সেটা সেই সেটআপের অনুমতি ছাড়া মরতে পারবে না — আর মরলে সেটআপকে জানাতেই হবে।

এই নীতিটা কোডে বসালে v7.7-এ এই ক্লাসের বাগ আর ফিরবে না।
