# LQ-SD-PA v3.1.1 SB — কোড রিভিউ, বাগ রিপোর্ট ও হাই-প্রোবাবিলিটি সিগন্যাল প্ল্যান

> ফাইল: `version_01.txt` (3,664 লাইন, Pine v6)
> রিভিউ দৃষ্টিকোণ: ৩০ বছরের প্রাইস-অ্যাকশন / লিকুইডিটি অপারেটরের চোখে — "কোডটা চলে কি না" নয়, **"কোডটা যা দাবি করছে সেটাই করছে কি না"**।
> স্ট্যাটাস: v3.1.1 আর্কিটেকচার শক্ত। কিন্তু নিচের **৮টা ব্লকার** থাকা অবস্থায় লাইভ ট্রেডে সিগন্যালের প্রোবাবিলিটি ইচ্ছাকৃত ডিজাইনের চেয়ে অনেক কম।

---

## ০. এক নজরে রায়

| দিক | রায় |
|---|---|
| আর্কিটেকচার (state machine, tier, quality grade) | ✅ চমৎকার — ইন্ডাস্ট্রি-গ্রেড |
| Liquidity detection | ⚠️ ৩টা গুরুতর বাগ — false "sweep in play" |
| Structure / MSS | ⚠️ circular logic — A+ tier অতিরিক্ত সহজ হয়ে যাচ্ছে |
| Entry price / Risk model | ❌ সবচেয়ে বড় দুর্বলতা — entry = `close`, RR মিথ্যা |
| Display toggle vs detection | ❌ পুরোনো রোগ আবার ফিরে এসেছে (`showSesHL`, `showEq`) |
| Silver Bullet path | ⚠️ নিজের gate নিজেই মেরে ফেলছে (chop + news window) |
| Liquidity Trap engine | ⚠️ সব কোয়ালিটি ফিল্টার bypass করে |
| Trade tracking / counters | ❌ একসাথে একটাই ট্রেড — কাউন্টার অবিশ্বাস্য |

---

## ১. ব্লকার বাগ (P0) — এগুলো ঠিক না করলে বাকি কিছুর মানে নেই

### 🔴 BUG-1 · "Sweep in play" ভাঙা সুইপেও true থাকে
**লাইন 900–901**
```pine
sslInPlay = recentSsl and not na(lastSslLvl) and close - lastSslLvl <= SWEEP_CTX_ATR * atr
bslInPlay = recentBsl and not na(lastBslLvl) and lastBslLvl - close <= SWEEP_CTX_ATR * atr
```
**সমস্যা:** কোনো নিচের বাউন্ড নেই। sell-side sweep-এর পর দাম যদি লেভেল **ভেঙে অনেক নিচে** চলে যায় (মানে সুইপ ফেল করে আসল breakdown হয়ে গেছে), তখন `close - lastSslLvl` **নেগেটিভ** → শর্তটা এখনও সত্য → ইঞ্জিন মনে করে "bullish liquidity grab live আছে"।

**প্রভাব:** ডাউনট্রেন্ডে ক্রমাগত false LONG arming। `liqLong` স্কোরে ১০ পয়েন্ট, tier B/A পাস, MSS ক্লাসিফিকেশনও ভুল হয়। — এটাই সম্ভবত সবচেয়ে বেশি লস-মেকিং সিগন্যালের উৎস।

**ফিক্স:**
```pine
sslInPlay = recentSsl and not na(lastSslLvl) and close > lastSslLvl
     and close - lastSslLvl <= SWEEP_CTX_ATR * atr
bslInPlay = recentBsl and not na(lastBslLvl) and close < lastBslLvl
     and lastBslLvl - close <= SWEEP_CTX_ATR * atr
```
(reclaim ধরে রাখা = সুইপের সংজ্ঞা; হারালে সেটা আর সুইপ না, সেটা breakout।)

---

### 🔴 BUG-2 · Sweep quality পুরোনো সুইপ থেকে "উত্তরাধিকার" পাচ্ছে
**লাইন 749, 763, 779, 785, 861, 867, 878, 884**
```pine
lastBslQual := math.max(lastBslQual, ... ? 3 : 2)
```
**সমস্যা:** নতুন pool (EQH / PDH / session H) স্ট্যাম্প করার সময় **আগের সুইপের quality-র সাথে `math.max`** নেওয়া হচ্ছে। আগের সুইপ institutional (৪) হলে, আজকের দুর্বল PDH poke-ও ৪ গ্রেড পেয়ে যায়।

**প্রভাব:** `minArmQual`, `sbMinQual` (London=3), chop-bypass (`qual>=4`), A+ tier — সব গেট ফাঁকি দিয়ে যায়। swing sweep-এ (লাইন 728, 734) fresh assign হয়, কিন্তু engineered pool-এ max — অসঙ্গত।

**ফিক্স:** প্রতিটা নতুন সুইপ ইভেন্টে quality **নতুন করে বসাও**। একই বারে একাধিক pool নিলে তখনই কেবল `math.max` — আলাদা বারে না।
```pine
// একই বারে হলে max, নতুন বার হলে reset
qNew = close <= high - (1 - STRONG_CLOSE_PCT) * rng and body >= BRK_BODY_ATR * atr ? 3 : 2
lastBslQual := (lastBslBar == bar_index) ? math.max(lastBslQual, qNew) : qNew
```
⚠️ খেয়াল: `lastBslBar := bar_index` লাইনটা quality assign-এর **পরে** সরাতে হবে, নইলে চেকটা সবসময় true।

---

### 🔴 BUG-3 · Display toggle আবার detection বন্ধ করে দিচ্ছে (পুরোনো রোগের প্রত্যাবর্তন)
কমিট `c19b5ce`-তে ঠিক এই সমস্যাটাই `showOB/showFlip/showBPR/showRB`-এর জন্য ঠিক করা হয়েছিল। কিন্তু দুই জায়গায় রয়ে গেছে:

**(ক) লাইন 806 — `f_sesTrack`**
```pine
if showSesHL and not active and active[1] and confirmed and not na(hi)
    hiLn := line.new(...)   // ← লেভেল কেবল এখানেই তৈরি হয়
```
`hiLvl`/`loLvl` আসে `line.get_y1(hiLn)` থেকে। **`showSesHL = false` হলে লাইনই তৈরি হয় না → session H/L raid কখনো ডিটেক্ট হয় না** → pool kind 4 কখনো আসে না → **Silver Bullet-এর মূল pool (Asia/London H-L) পুরোপুরি মৃত**।

**(খ) লাইন 513, 550 — EQ pool**
```pine
if showEq and not na(prevPH) and math.abs(ph - prevPH) <= eqTol * atr
```
`showEq = false` → EQH/EQL array খালি → `eqhSwept`/`eqlSwept` কখনো true না → pool kind 2 মৃত → `sbPoolPref` (default ON) SB arming ব্লক করে দেয়।

**ফিক্স:** ডিটেকশন আর ড্রয়িং আলাদা করো। লেভেল ট্র্যাকিং সবসময় চলবে; `showSesHL` / `showEq` কেবল `line.new` / `label.new` মোড়ানোর জন্য ব্যবহার করবে। (`f_sesTrack`-এ `hi`/`lo` আলাদা `var float` রাখো, লাইন থেকে পড়ার বদলে।)

---

### 🔴 BUG-4 · Entry price = `close`, অথচ ডকট্রিন বলে CE limit
**লাইন 3018**
```pine
entryP := close
```
**সমস্যা:** SB-5 ডকুমেন্টেশন বলছে "limit at the CE (50%) of the locked FVG"। কিন্তু ট্রেড প্ল্যান বসানো হচ্ছে বারের **close** দিয়ে। CE touch হয় wick-এ, close হয় অনেক দূরে।

**প্রভাব:**
- রিপোর্ট করা RR সম্পূর্ণ মিথ্যা (`f_tradePlan`-এ "RR 2.0 (plan, not promise)" — বাস্তবে হয়তো 1.1)
- TP1 = 1R হিসাব ভুল জায়গা থেকে → BE shift ভুল সময়ে
- SL = `min(low, anchorB, sweepExt) - pad` → entry দূরে বলে R কৃত্রিমভাবে বড়, TP2/TP3 অবাস্তব দূরে
- কাউন্টার (cntTP1/TP2/SL) সব বিকৃত

**ফিক্স:**
```pine
// SB path: CE-তে limit; non-SB: retest anchor edge; fallback: close
entryP := sbFireL ? (sbCeFillL ? ceLockedL : suLAnchorT) :
          sbFireS ? (sbCeFillS ? ceLockedS : suSAnchorB) :
          sigMCLong  ? math.min(close, suLAnchorT) :
          sigMCShort ? math.max(close, suSAnchorB) : close
```
(`ceLockedL/S` = MODULE 17-এ entry বারে `(anchorT+anchorB)/2` গ্লোবালে সেভ করে রাখতে হবে।)
সাথে একটা **slippage guard**: `math.abs(close - entryP) > 0.5 * atr` হলে সিগন্যাল বাতিল — দাম CE ছেড়ে অনেক দূরে চলে গেছে মানে fill বাস্তবসম্মত না।

---

### 🔴 BUG-5 · `sigSLLong` / `sigSLShort` গ্লোবাল শেয়ার্ড — ফিল্টার হওয়া ইঞ্জিনের SL ব্যবহৃত হচ্ছে
**লাইন 1588–1589, 1764, 1777, 1801, 1950, 2648**

সব ইঞ্জিন একই দুই ভেরিয়েবলে SL লেখে, ক্রম: zone → CRT → TBS → TL → FEM → machine। **শেষে যে লিখল সে জেতে।**

কিন্তু MODULE 18-এ tier/cooldown ফিল্টার ইঞ্জিনগুলোকে **মিউট করে** — SL কিন্তু মিউট হয় না। ফলে:
> CRT সিগন্যাল tier-এ বাদ পড়ল, কিন্তু `sigSLLong` এখনও CRT-এর stop ধরে আছে → Demand-zone সিগন্যাল ফায়ার করলে **সে CRT-এর ভুল stop নিয়ে যাবে**।

**ফিক্স:** প্রতিটা ইঞ্জিনের নিজস্ব SL ভেরিয়েবল রাখো (`slCRT_L`, `slTBS_L`, `slSD_L`, `slMC_L` …), আর MODULE 19-এ **যে সিগন্যাল আসলে ফায়ার করেছে** কেবল তার SL বাছাই করো — priority: machine > FEM > SD > CRT > TBS > TL।

---

### 🔴 BUG-6 · চালু ট্রেড নীরবে মুছে যায়
**লাইন 3017**
```pine
if (anyLong or anyShort) and confirmed
    ...
    trdDir := anyLong ? 1 : -1
```
আগের ট্রেড ওপেন (`trdDir != 0`) থাকলেও কোনো চেক নেই — নতুন সিগন্যাল এসে **পুরোনো ট্রেড ওভাররাইট** করে দেয়। ওই ট্রেডের TP/SL কখনো গোনা হয় না।

**প্রভাব:** `cntTP1/TP2/SL/TP3` পরিসংখ্যান অর্থহীন। ড্যাশবোর্ডের "Active trade" ভুল দেখায়। SB exit engine (time exit, struct exit) মাঝপথে হারিয়ে যায়।

**ফিক্স (দুটির যেকোনো একটা):**
- সহজ: `if (anyLong or anyShort) and confirmed and trdDir == 0` — ট্রেড চলাকালীন নতুন এন্ট্রি নেই (ম্যানুয়াল ট্রেডিং-এর বাস্তবতার কাছাকাছি)
- ভালো: ট্রেডগুলোকে `array<Trade>`-এ রাখো, একাধিক একসাথে ট্র্যাক করো। ওভাররাইটের সময় পুরোনোটা "abandoned" হিসেবে কাউন্ট করো।

---

### 🔴 BUG-7 · SB chop-bypass নিজের গেটেই মারা পড়ে
**লাইন 2584 (arming) vs 2750–2755 (final gate)**
```pine
// MODULE 17 — arming: chop bypass কাজ করে
bool chopBlock = useRegime and regime == "CHOP" and lastSslQual < 4
     and not (sbArmOkL and sbChopBypass)
...
// MODULE 18 — final: bypass উধাও
chopOKL = not useRegime or regime != "CHOP" or lastSslQual >= 4
longOK  = ... and chopOKL and ...
```
SB setup chop-এ arm হয়, POI tap হয়, MSS হয়, FVG lock হয়, CE fill হয় — তারপর **MODULE 18-এ নীরবে মারা যায়**। ইউজার শুধু দেখবে "setup ছিল, সিগন্যাল আসেনি", কোনো কারণ কোথাও লেখা নেই।

**ফিক্স:**
```pine
chopOKL = not useRegime or regime != "CHOP" or lastSslQual >= 4
     or (sbFireL and sbChopBypass)
chopOKS = not useRegime or regime != "CHOP" or lastBslQual >= 4
     or (sbFireS and sbChopBypass)
```
সাথে: সিগন্যাল যেখানেই মিউট হচ্ছে, `suLReason`-এ কারণ লেখো — debug টেবিলে "killed at final gate: chop" দেখা যাক।

---

### 🔴 BUG-8 · News window NY AM Silver Bullet-এর মুখে বসে আছে
**লাইন 314 vs 250**
```pine
news2Ses  = input.session("0955-1010:23456", "Window #2 — 10:00 US data slot")
sbSesAM   = input.session("1000-1100", "Silver Bullet — NY AM")
```
`useNews` default `true` → NY AM SB উইন্ডোর **প্রথম ১০ মিনিট** (10:00–10:10) ব্লকড। অথচ SB ডকট্রিনে raid + displacement প্রায়ই ঠিক ওই প্রথম ১০–১৫ মিনিটেই ঘটে। ডকুমেন্টেশন বলছে NY AM "priority window" — বাস্তবে সেটাই সবচেয়ে বেশি সেন্সরড।

**ফিক্স:** নতুন ইনপুট `newsAllowSb` (default ON):
```pine
newsOK = not useNews or not timeframe.isintraday or not inNews
     or (newsAllowSb and sbActive and sbWinNow == 2)
```
অথবা ডিফল্ট window #2 বদলে `0955-1000` করো (ডেটা রিলিজের আগের ৫ মিনিট ব্লক, পরেরটা নয়)।

---

## ২. লজিক্যাল সমস্যা (P1) — বাগ নয়, কিন্তু edge নষ্ট করে

### 🟠 LOGIC-1 · MSS → quality 4 → A+ : circular reasoning
**লাইন 992–997 vs 2043, 2056, 2001**
```pine
mssUp = (chochUp or eChochUp) and sslInPlay and lastSslQual >= 2
if mssUp and confirmed
    lastSslQual := 4          // ← MSS হলেই সুইপ "institutional"
...
if tier == 3 and htfB > 0 and sesPts >= 5 and lastSslQual >= 3 and ...
    tier := 4                 // ← "strong sweep চাই" — কিন্তু MSS-ই সেটা দিয়ে দিয়েছে
```
A+ tier-এর "strong sweep" শর্তটা MSS নিজেই পূরণ করে দিচ্ছে। মানে **A+ = A + HTF + session + P/D** — "strong sweep" শর্তটা কার্যত অস্তিত্বহীন। একই ভাবে `liqLong`-এর `lastSslQual >= 3 ? 5 : 0` বোনাসও automatic।

**ফিক্স:** দুটো আলাদা ফিল্ড রাখো — `lastSslQualRaw` (ক্যান্ডেল থেকে, কখনো ওভাররাইট হয় না) আর `lastSslQualEff` (MSS upgrade সহ)। Tier A+ ও liq বোনাস `Raw >= 3` পড়বে; chop bypass ও arming `Eff` পড়বে।

### 🟠 LOGIC-2 · Machine entry সবসময় tier A — display filter অকার্যকর
**লাইন 2758–2764**
```pine
mcTierL = math.max(tierLong, 3)     // ← জোর করে A
sbTierMin = sbMinTier == "A+ only" ? 4 : 3
sigMCLong := sigMCLong and longOK and mcTierL >= (sbSigLong ? math.max(minRank, sbTierMin) : minRank)
```
`mcTierL` কখনো 3-এর নিচে যায় না, তাই `minRank` = 1/2/3 সব ক্ষেত্রেই পাস। `sbMinTier = "A and above"` **সম্পূর্ণ no-op**। কেবল "A+ only" কিছু করে, আর তখন সেটা `tierLong >= 4` চায় — যেটা `pdPos` (live range) পড়ে, অথচ SB entry `sbPdPos` (locked range) পড়ে → **দুই মাপকাঠি বিরোধ** (লাইন 2043 vs 2638)।

**ফিক্স:** machine tier জোর করে 3 না বানিয়ে **আসল কম্পোনেন্ট থেকে** হিসাব করো (sweep quality + POI + shift grade + execution + HTF + session + P/D)। আর tier-এর P/D চেকটাও SB-tagged হলে `sbPdPos` পড়ুক।

### 🟠 LOGIC-3 · Anchor FVG বাসি হতে পারে
**লাইন 2615**
```pine
if not na(cFvgBTop) and cFvgBBar >= suLBar - TRIG_LOOK and (sbTagL == 0 or sbFvgOkL)
```
`suLBar` ঠিক আগের লাইনেই `bar_index` হয়েছে। মানে শর্ত = "গত ১০ বারে তৈরি যেকোনো FVG"। সেই FVG **সুইপের আগের** হতে পারে, **displacement leg-এর সাথে সম্পর্কহীন** হতে পারে। SB ডকট্রিনে anchor অবশ্যই shift leg-এর FVG।

**ফিক্স:** `cFvgBBar >= suLBar` (shift বার বা তার পরে) দাবি করো, আর যদি না থাকে তাহলে stage 3-এ গিয়ে পরবর্তী FVG-র জন্য অপেক্ষা করো (লাইন 2620 ইতিমধ্যে সেটা করে)।

### 🟠 LOGIC-4 · Trendline touch কাউন্ট ফুলে যায়
**লাইন 1798, 1803, 1814, 1819**
```pine
else if low <= tlUpVal + NEAR_LVL_ATR * atr
    tlUpTouch += 1          // ← প্রতি বারে +1
```
দাম লাইনের কাছে ৮ বার ঘোরাফেরা করলে touch = 8। ফলে `tlUpTouch >= 2` তুচ্ছভাবে পাস, `tlTouchMin` অর্থহীন, TL sweep সিগন্যাল স্প্যাম করে।

**ফিক্স:** edge-trigger করো — `wasNear` ফ্ল্যাগ রাখো, দাম দূরে গিয়ে ফিরে এলে তবেই +1। আর line-টা N বার পর expire করো (এখন ভাঙা না পর্যন্ত চিরকাল বাঁচে)।

### 🟠 LOGIC-5 · Liquidity Trap সিগন্যাল সব গেট বাইপাস করে
**লাইন 2445, 2800–2801**
`ltLongSig` / `ltShortSig` কখনো `anyLong` / `anyShort`-এ ঢোকে না। ফলে LT সিগন্যাল পায় **না**: tier ফিল্টার, `minScore`, `masterCd` cooldown, killzone, news window, HTF bias filter, chop suppression, SB conflict hierarchy — কিচ্ছু না। শুধু লেবেল + alert।

**প্রভাব:** চার্টে দুই রকমের সিগন্যাল — একটা কঠোরভাবে ফিল্টার্ড, আরেকটা প্রায় কাঁচা। ট্রেডার বিভ্রান্ত হয়, আর LOW/MEDIUM স্কোরের trap সিগন্যাল noise বাড়ায়।

**ফিক্স:** LT-কে **সিগন্যাল জেনারেটর নয়, একটা স্কোর/কনফ্লুয়েন্স লেয়ার** বানাও (নিচের প্ল্যান দেখো) — অথবা অন্তত `longOK`/`shortOK` ও `ltScoreHigh` থ্রেশহোল্ড দিয়ে গেট করো।

### 🟠 LOGIC-6 · `ripeL` "retest" নিশ্চিত করে না
**লাইন 2626, 2640**
```pine
bool ripeL = na(suLFvgBar) or bar_index > suLFvgBar
bool stdEnterL = sbTagL == 0 and ripeL and low <= suLAnchorT and zoneBullConf
```
Zone anchor (FVG নেই, `suLFvgBar` = na) হলে `ripeL` সাথে সাথেই true → POI tap-এর **একই বারে** entry হতে পারে। সেটা retest না, সেটা reaction। ARCH-1-এর "AWAIT RETEST" স্টেজ কার্যত এড়িয়ে যাচ্ছে।

**ফিক্স:** `ripeL = bar_index > suLBar` (shift বারের পরে) — anchor type নির্বিশেষে।

### 🟠 LOGIC-7 · SL = sweep wick → R অস্বাভাবিক বড়
**লাইন 2648**
```pine
sigSLLong := math.min(math.min(low, suLAnchorB), nz(suLSweepExt, low)) - SL_PAD_ATR * atr
```
`suLSweepExt` হলো সুইপের wick extreme, যা entry থেকে ২০ বার দূরেও হতে পারে। ফলে risk বিশাল, TP2 (2R) / TP3 (3R) অবাস্তব দূরে, TP1 কখনো হিট হয় না, BE shift কখনো ট্রিগার হয় না।

**ফিক্স:**
```pine
float rawSL = math.min(math.min(low, suLAnchorB), nz(suLSweepExt, low)) - SL_PAD_ATR * atr
float capSL = close - maxRiskAtr * atr        // নতুন ইনপুট, default 1.5
sigSLLong  := math.max(rawSL, capSL)
// এবং: risk > maxRiskAtr * atr হলে সিগন্যাল সম্পূর্ণ বাতিল (বেশি ভালো)
```

### 🟠 LOGIC-8 · অন্যান্য ছোট কিন্তু বাস্তব
| # | লাইন | সমস্যা |
|---|---|---|
| a | 1991 | `sesPts` non-intraday-তে সবসময় 5 → daily চার্টে context স্কোর কৃত্রিমভাবে বেশি |
| b | 1312 | `regChop` — `na(extRngAtr)` হলেই CHOP; চার্টের শুরুতে সব ব্লকড |
| c | 1699–1714 | zone cap প্রতি বারে মাত্র **একটা** zone মোছে — RB burst-এ cap ছাড়িয়ে যায় |
| d | 2911–2916 | একই বারে TP1+TP2 হলে কেবল TP1 গোনা হয় (`else if` চেইন) |
| e | 1185, 1190 | HTF CRT/TBS `[1]` + `newHtfBar` → সিগন্যাল প্রায় ২ HTF বার পুরোনো |
| f | 3007–3010 | `suL == 4` reset `trdDir == 0`-এর উপর নির্ভর; BUG-6-এর কারণে আটকে থাকতে পারে |
| g | 1373 | bull FVG `low <= f.bot` হলেই মুছে যায় — inversion (IFVG) হিসেবে রাখার সুযোগ হারানো |
| h | 3606 | ৬৪ output বাজেট **পূর্ণ** — নতুন কোনো `plot`/`plotchar`/`bgcolor`/`alertcondition` যোগ করা যাবে না |

---

## ৩. ✅ হাই-প্রোবাবিলিটি BUY / SELL — স্টেপ-বাই-স্টেপ প্ল্যান

> নীতি: **প্রতিটা স্টেপ একটা "না" বলার সুযোগ।** সিগন্যাল তখনই, যখন কোনো স্টেপ "না" বলেনি।
> নিচের চেইনটাই v3.2-এ ইমপ্লিমেন্ট করার টার্গেট। বর্তমান কোড এই চেইনের ৭০% ধরে, বাকি ৩০% উপরের বাগে নষ্ট হচ্ছে।

### STEP 0 — অনুমতি (Permission gate)
নিচের যেকোনো একটা "না" হলে ওই বারে কোনো সিগন্যাল নেই:
- [ ] বার **ক্লোজড** (`barstate.isconfirmed`)
- [ ] Regime ≠ CHOP — ব্যতিক্রম: raw sweep quality 4, **অথবা** সক্রিয় SB উইন্ডো (`sbChopBypass`)
- [ ] News window-এর বাইরে — ব্যতিক্রম: NY AM SB উইন্ডো (BUG-8 ফিক্সের পর)
- [ ] Same-direction cooldown শেষ (`masterCd`)
- [ ] `atr > 0` এবং `ltLowVol == false` (ATR < 0.7 × SMA50 হলে মুভ নেই — বসে থাকো)

### STEP 1 — বায়াস (Context, HTF থেকে LTF)
- [ ] HTF bias EMA (default 60m, **closed candle**) দিক দেয় → BUY হলে `htfB > 0`
- [ ] External structure `extDir` একই দিক, অথবা অন্তত বিপরীত নয়
- [ ] Dealing range-এ অবস্থান সঠিক দিকে — **BUY = discount (`pdPos < 0.5`), SELL = premium (`pdPos >= 0.5`)**
  → SB-tagged হলে `sbPdPos` (window-open-এ frozen range) পড়বে, `pdPos` নয়

**কেন:** ৩০ বছরের নিয়ম — premium-এ কিনো না, discount-এ বেচো না। এই একটা শর্তই সবচেয়ে বেশি খারাপ ট্রেড কাটে।

### STEP 2 — লিকুইডিটি ইভেন্ট (Raid, সুইপের শুরু)
- [ ] Sell-side pool নেওয়া হয়েছে (BUY-এর জন্য) — wick লেভেলের নিচে, **close লেভেলের উপরে**
- [ ] Pool-এর **kind** যাচাই: 4 = prior session H/L · 3 = PDH/PDL · 2 = EQH/EQL · 1 = bare pivot
  → হাই-প্রোবাবিলিটির জন্য **kind ≥ 2 বাধ্যতামূলক** (engineered liquidity)। Bare pivot = retail stop, অতটা নির্ভরযোগ্য নয়।
- [ ] **Raw quality ≥ 2** (firm reclaim), A+ চাইলে **raw quality ≥ 3** (outer-half close + displacement body)
- [ ] সুইপ এখনো "in play": `close > level` **এবং** `close - level <= 3 × ATR` (BUG-1 ফিক্স)
- [ ] সুইপের বয়স ≤ `sweepLook` (SB context-এ +5 বার)

**কেন:** লিকুইডিটি ছাড়া reversal নেই। কে stopped out হলো সেটাই মুভের জ্বালানি।

### STEP 3 — POI (কোথায় দাম ফিরবে)
নিচের যেকোনো **একটা** — কিন্তু অগ্রাধিকার ক্রমে:
1. **HTF FVG POI** (fresh, `hPoiBIn == 0`) — সর্বোচ্চ মান
2. **Order Block** (displacement leg-এর আগের বিপরীত ক্যান্ডেল)
3. **Demand/Supply zone** (FVG-imbalance geometry), `tests <= zoneMaxTests`
4. **Breaker** (সুইপ + structure break-এর পর ফ্লিপ হওয়া zone)
5. **OTE 62–79%** — একা নয়, উপরের কোনোটার সাথে মিললে বোনাস

- [ ] Zone **fresh** (`nbFresh` / `z.tests == 0`) — বারবার টেস্ট হওয়া zone মৃত
- [ ] Zone height ≤ `maxZoneAtr × ATR` (২ ATR-এর বেশি লম্বা zone মানে কোনো precision নেই)

**কেন:** raid + POI = "কোথায়" আর "কেন" একসাথে। শুধু raid = গ্যাম্বলিং।

### STEP 4 — স্ট্রাকচার শিফট (নিশ্চিতকরণ)
- [ ] **MSS** (সর্বোত্তম): protected swing-এর displaced break, **যখন quality sweep এখনো in play**
- [ ] বিকল্প: External CHoCH (displaced close through protected swing)
- [ ] দুর্বলতম গ্রহণযোগ্য: CISD (≥2-ক্যান্ডেল বিপরীত run-এর origin open ভেদ করে displacement close)
- [ ] Break candle body ≥ `structDisp × ATR` (default 0.5)
- [ ] Shift **POI tap-এর পরে** ঘটেছে, আগে নয় — এবং `poiWait` বারের মধ্যে

**গ্রেডিং:** MSS = 2 · CHoCH/CISD = 1। এই গ্রেড পরে exit rule ঠিক করবে (সমান বা উঁচু গ্রেডের বিপরীত shift-এ বেরোও)।

### STEP 5 — এন্ট্রি অ্যাংকর (FVG lock)
- [ ] Shift leg **একটা FVG রেখে গেছে** — এবং সেটাই anchor (`cFvgBBar >= shift bar`, LOGIC-3)
- [ ] FVG উচ্চতা ≥ `sbFvgMinAtr × ATR` — এক-টিকের গ্যাপ নয়
- [ ] FVG-র জন্মদাতা ক্যান্ডেল একটা **displacement** ক্যান্ডেল (`body >= dispFactor × ATR`)
- [ ] **CE (50%) নির্ণয় করো** — এটাই তোমার limit price

### STEP 6 — এন্ট্রি ট্রিগার (দুইটার যেকোনো একটা)
**(A) CE fill — পছন্দনীয়**
- [ ] দাম CE স্পর্শ করেছে (`sbCeTol × ATR` সহনশীলতা)
- [ ] **এবং** confirmation: CE-তে বা তার ভেতরে close, **অথবা** genuine rejection bar (pin / engulf / IFC / CISD)
- [ ] খালি wick দিয়ে CE ছুঁয়ে বাইরে close = **fill প্রত্যাখ্যান** (SB-11 নিয়ম — এটা ঠিক আছে, রাখো)

**(B) Proximal edge — কেবল শক্তিশালী rejection-এ**
- [ ] FVG-র প্রথম প্রান্ত স্পর্শ + pin/engulf/IFC/CISD

- [ ] এন্ট্রি বার shift বারের **পরে** (`bar_index > suLBar`, LOGIC-6)
- [ ] দাম FVG-র বিপরীত প্রান্ত ভাঙেনি (ভাঙলে setup মৃত)

### STEP 7 — রিস্ক (ট্রেড নেওয়ার আগে শেষ "না")
- [ ] **Entry = CE (বা edge)** — বারের close নয় (BUG-4)
- [ ] SL = `min(entry candle low, FVG bottom, sweep extreme) - 0.25 ATR`, কিন্তু **cap: `maxRiskAtr = 1.5 × ATR`**
- [ ] Risk > cap → **ট্রেড বাদ** (দেরিতে ঢুকছো, edge নেই)
- [ ] TP1 = 1R · TP2 = `rrMult` R (default 2R) · TP3 = নিকটতম বিপরীত pool যা ≥ TP2 pay করে
- [ ] **TP2 পর্যন্ত পৌঁছানোর পথে কোনো বিপরীত POI নেই** — থাকলে সেটাই TP2 (নতুন চেক, এখন নেই)
- [ ] সর্বনিম্ন RR ≥ 1.5 — নইলে বাদ

### STEP 8 — ম্যানেজমেন্ট
- [ ] TP1 → SL = entry + max(0.15 ATR, 15% × TP1 দূরত্ব) [SB-14, ভালো লজিক — সব ট্রেডে প্রয়োগ করো, শুধু SB-তে নয়]
- [ ] TP2 → protected swing-এর পেছনে trail, কিন্তু শেষ ২ বারের low/high ভেদ করে নয়
- [ ] বিপরীত MSS (বা entry shift grade ≤1 হলে বিপরীত CHoCH/CISD) → বাকিটা বন্ধ
- [ ] SB ট্রেড + উইন্ডো শেষ + TP1 unhit → সম্পূর্ণ/আংশিক exit

### ⭐ A+ সেটআপ (সর্বোচ্চ প্রোবাবিলিটি) — নিচের সব একসাথে
```
Raw sweep quality ≥ 3   (MSS-উপহার নয়, ক্যান্ডেল থেকে অর্জিত)
Pool kind ≥ 3           (PDH/PDL অথবা prior session H/L)
HTF bias একমত          (60m ও 240m — দুটোই)
Regime = TRENDING বা TRANSITION (CHOP নয়)
P/D সঠিক দিকে          (BUY = discount)
POI = fresh HTF FVG অথবা untested OB
Shift = MSS (CHoCH নয়)
Anchor = shift leg-এর clean displacement FVG
Entry = CE fill, wick-only নয়
Risk ≤ 1.5 ATR, RR ≥ 2
Session = London / NY AM (Asia-only নয়)
```
**বাস্তবতা:** এই সেট দিনে ০–২ বার আসবে। সেটাই ঠিক। বর্তমান ডিফল্ট (`tierMode = "B and above"`) দিনে ১৫–৩০টা সিগন্যাল দেয় — তার বেশিরভাগই noise। **ডিফল্ট `"A and above"` করার সুপারিশ করছি।**

---

## ৪. ইমপ্লিমেন্টেশন রোডম্যাপ (ফেজ অনুযায়ী)

### ফেজ ১ — ব্লকার ফিক্স (v3.2.0) · আনুমানিক ৩–৪ ঘণ্টা
আচরণ বদলাবে, কিন্তু এগুলো **defect repair**, feature নয়।
1. BUG-1 · `sslInPlay`/`bslInPlay` reclaim-side চেক — **সবচেয়ে বড় ROI**
2. BUG-3 · `showSesHL` / `showEq` detection থেকে আলাদা করা
3. BUG-2 · sweep quality per-event reset
4. BUG-7 · `chopOKL/S`-এ SB bypass
5. BUG-8 · news window vs NY AM SB

✅ **যাচাই:** ফিক্সের আগে-পরে ৩ মাসের চার্টে সিগন্যাল সংখ্যা তুলনা করো। BUG-1 ফিক্সে LONG সিগন্যাল ডাউনট্রেন্ডে **উল্লেখযোগ্য কমবে** — সেটাই সফলতার চিহ্ন, ব্যর্থতার নয়।

### ফেজ ২ — রিস্ক মডেল (v3.2.1) · আনুমানিক ৪–৫ ঘণ্টা
6. BUG-4 · `entryP` = CE / anchor edge + slippage guard
7. BUG-5 · per-engine SL ভেরিয়েবল + priority সিলেকশন
8. LOGIC-7 · `maxRiskAtr` ইনপুট (default 1.5) + risk-cap reject
9. নতুন: `minRR` ইনপুট (default 1.5) — MODULE 19-এ শেষ gate
10. BUG-6 · চালু ট্রেড ওভাররাইট বন্ধ

✅ **যাচাই:** debug টেবিলে `cntTP1 / cntTP2 / cntSL` — TP1 hit রেট নাটকীয়ভাবে বাড়বে (আগে R বড় ছিল বলে TP1 অধরা ছিল)।

### ফেজ ৩ — কোয়ালিটি রিফাইনমেন্ট (v3.3.0) · আনুমানিক ৫–৬ ঘণ্টা
11. LOGIC-1 · `QualRaw` vs `QualEff` বিভাজন
12. LOGIC-2 · machine tier আসল কম্পোনেন্ট থেকে হিসাব; tier-এ `sbPdPos` ব্যবহার
13. LOGIC-3 · anchor FVG অবশ্যই shift-এর পরে
14. LOGIC-6 · `ripeL/ripeS` = shift বারের পরে
15. LOGIC-4 · trendline touch edge-trigger + line expiry
16. LOGIC-8(c) · zone cap লুপে `while`

### ফেজ ৪ — LT ইঞ্জিন একীভূতকরণ (v3.4.0) · আনুমানিক ৩ ঘণ্টা
17. LT সিগন্যালকে `anyLong/anyShort`-এ আনো, `longOK/shortOK` গেট প্রয়োগ করো
18. **অথবা (সুপারিশ)** LT-কে স্কোর কম্পোনেন্টে রূপান্তর করো:
   - `ltShortSig` + score ≥ HIGH → `scoreLong` থেকে −15 (breakout সন্দেহজনক)
   - `ltLongSig` + score ≥ HIGH → `scoreLong`-এ +10
   এতে ৭টা প্যাটার্নের কাজ থাকে, কিন্তু চার্টে দ্বিতীয় সমান্তরাল সিগন্যাল সিস্টেম থাকে না
19. `ltVeto` default ON করো (একদিকে trap অপেক্ষারত থাকলে বিপরীত দিক সন্দেহজনক)

### ফেজ ৫ — ভ্যালিডেশন (v3.4.1)
20. কাউন্টার ঠিক করো: abandoned ট্রেড, একই বারে TP1+TP2, tier-ভিত্তিক আলাদা কাউন্টার
21. Debug টেবিলে **"শেষ ১০টা kill reason"** যোগ করো — কোন গেট সবচেয়ে বেশি মারছে সেটা দেখা যাক (commit `05396ec`-এর Funnel ধারণা এখানেও লাগাও)
22. ⚠️ output বাজেট পূর্ণ — নতুন কিছু দরকার হলে পুরোনো `alertcondition` মার্জ করতে হবে

---

## ৫. প্যারামিটার সুপারিশ (ফেজ ১–২ ফিক্সের পর)

| ইনপুট | এখন | সুপারিশ | কারণ |
|---|---|---|---|
| `tierMode` | B and above | **A and above** | B-tier = trigger + একটা লেয়ার; সেটা edge নয়, সেটা noise |
| `minScore` | 0 (off) | **60** | tier আর score দুটোই লাগুক — একে অপরের ব্যাকআপ |
| `minArmQual` | 2 | **2** (ঠিক আছে) | quality reset ফিক্সের পর ২-ই যথেষ্ট কঠোর হবে |
| `sweepLook` | 15 | **12** | ১৫ বার পুরোনো সুইপ আর "in play" নয় (M5/M15-এ) |
| `sbPoolPref` | ON | **ON** (রাখো) | engineered liquidity = SB-র মূল কথা |
| `sbReqMss` | OFF | **ON** (M15+ এ) | CHoCH/CISD দিয়ে SB = doctrine লঙ্ঘন |
| `zoneMaxTests` | 3 | **2** | তৃতীয় টেস্টে zone কার্যত শেষ |
| `useRegime` | ON | **ON** | রাখো |
| `masterCd` | 10 | **15** | একই narrative থেকে দুটো এন্ট্রি = double risk |
| নতুন `maxRiskAtr` | — | **1.5** | ফেজ ২ |
| নতুন `minRR` | — | **1.5** | ফেজ ২ |

**টাইমফ্রেম:** এই ইঞ্জিন **M5 / M15**-এর জন্য ডিজাইন করা (SB উইন্ডো ৬০ মিনিট, stage clock ৮–১২ বার)। M1-এ noise, H1+ এ SB উইন্ডোতে ১টাই বার — অর্থহীন। **M15 = sweet spot।**

---

## ৬. টেস্টিং প্রোটোকল (প্রতিটা ফেজের পরে বাধ্যতামূলক)

1. **Compile check** — Pine Editor, কোনো warning নেই
2. **Output budget** — ৬৪ সীমা অতিক্রম হয়নি (8 plot + 14 plotchar + 5 bgcolor + 37 alertcondition)
3. **Replay test** — কমপক্ষে ২টা ইনস্ট্রুমেন্ট (একটা indices, একটা FX) × ৩ মাস M15
4. **Repaint test** — লাইভ বারে সিগন্যাল দেখা গেলে, বার ক্লোজের পর সেটা টিকে আছে কি? (LT "Intrabar" mode বাদে সব non-repainting হওয়া উচিত)
5. **Toggle test** — প্রতিটা `show*` ইনপুট একবার OFF করে দেখো **সিগন্যাল সংখ্যা বদলায় কি না**। বদলালে সেটা BUG-3-এর মতো আরেকটা কেস
6. **Counter sanity** — `cntLong + cntShort == cntTP1 + cntSL + cntTP2 + cntTP3 + open` (±1)
7. **Kill-reason funnel** — ১০০ বারে কোন গেট কতবার মেরেছে? একটা গেট ৮০%+ মারলে সেটা হয় ভুল, নয় অতিরিক্ত কঠোর

---

## ৭. যা **ঠিক আছে** — ভুলেও বদলিও না

এই অংশগুলো অডিট করে দেখেছি, লজিক নির্ভুল:

- ✅ **CISD strict run tracker** (লাইন 419–455) — neutral candle দুই run-ই ভাঙে, origin open ভেদ, run ≥ 2, latch একবার। পাঠ্যপুস্তকসম্মত।
- ✅ **IFC** (লাইন 461–465) — আসল pool নেওয়া + meaningful penetration + midpoint ভেদ + outer-30% close। দুর্দান্ত।
- ✅ **Turtle soup age math** (`-ta.lowestbars()[1] + 1`) — কমেন্টে যা লেখা আছে ঠিক তাই। **সাইন "ঠিক" করতে যেও না**, এটা ইতিমধ্যে ঠিক আছে।
- ✅ **SB-11 CE fill = touch + confirmation** — wick-only fill প্রত্যাখ্যান। এটাই সঠিক ডকট্রিন।
- ✅ **SB-12 dealing-range lock** — raid নিজেই range বাড়িয়ে setup-কে ভুল দিকে ফেলে দিত। চমৎকার ধরা।
- ✅ **SB-13 conflict hierarchy** — mutual kill-এর বদলে rank। v3-এর "silent day" সমস্যার সঠিক সমাধান।
- ✅ **SB-14 adaptive BE + two-bar trail cap** — ভালো ট্রেড ম্যানেজমেন্ট। **এটা সব ট্রেডে ছড়িয়ে দাও, শুধু SB-তে নয়।**
- ✅ **Breaker vs Mitigation split** (লাইন 1487, 1538) — breaker-এর জন্য sweep + structure break চাওয়া সঠিক।
- ✅ **Protected-swing structure engine** — CHoCH-এর সংজ্ঞা হিসেবে leg extreme ব্যবহার, inducement এড়ানো। সঠিক।
- ✅ **HTF `lookahead_off` + `[1]`** — repaint-মুক্ত। রাখো।

---

## ৮. চূড়ান্ত কথা

এই ইন্ডিকেটরের **ধারণাগত ভিত্তি অসাধারণ** — layered narrative (Context → Liquidity → POI → Structure → Trigger → Execution), state machine, quality grading, tier system। এগুলো বেশিরভাগ কমার্শিয়াল ইন্ডিকেটরের চেয়ে এগিয়ে।

সমস্যা ধারণায় নয়, **execution detail-এ**। বিশেষ করে দুটো জিনিস edge-এর বেশিরভাগ খেয়ে ফেলছে:

1. **BUG-1** — ভাঙা সুইপকে "in play" ধরা। এটা ডাউনট্রেন্ডে LONG এবং আপট্রেন্ডে SHORT জেনারেট করছে। এক লাইনের ফিক্স, সবচেয়ে বড় প্রভাব।
2. **BUG-4** — entry price = close। এর ফলে প্রতিটা RR সংখ্যা, প্রতিটা TP লেভেল, প্রতিটা কাউন্টার মিথ্যা। ইঞ্জিন যা দেখাচ্ছে আর ট্রেডার যা পাচ্ছে — দুটো আলাদা।

শুধু **ফেজ ১ + ফেজ ২** করলেই সিগন্যাল সংখ্যা ~৪০% কমবে আর কোয়ালিটি নাটকীয়ভাবে বাড়বে। বাকি ফেজগুলো পরিমার্জন।

> **মনে রাখো:** কম সিগন্যাল = ভালো ইন্ডিকেটর। লিকুইডিটি-ভিত্তিক ট্রেডিং-এ দিনে ২টা A+ সেটআপই যথেষ্ট। ইঞ্জিন যদি দিনে ২০টা দেয়, ইঞ্জিন তোমাকে সাহায্য করছে না — ব্যস্ত রাখছে।
