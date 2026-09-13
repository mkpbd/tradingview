# SMC + ICT Indicator — Advanced Build Plan (Phase 17–34)

**Version:** 1.0
**Audience:** Pine Script developer (trading knowledge লাগবে না)
**Prerequisite:** `03_BUILD_PLAN.md` Phase 1–16 সম্পূর্ণ এবং Proof pass
**Source specs:** `SMC_ICT_TradingView_Developer_Specification.md` (§23–§30), `02_improve_smc_ict.md`
**Output:** একই `indicator()` — নতুন file নয়, Phase 1–16-এর code-এর উপরেই layer যোগ হবে

---

## 0. এই ডকুমেন্ট কেন

`03_BUILD_PLAN.md` দিয়ে যা তৈরি হয় সেটা একটা **কাজ করা** SMC engine — sweep → displacement → MSS → POI → entry। কিন্তু spec-এ যা লেখা আছে তার প্রায় ৪০% সেখানে নেই:

| Spec-এ আছে | 03_BUILD_PLAN-এ | এই ডকুমেন্টে |
|---|---|---|
| CISD (§23) | ❌ নেই | Phase 19 |
| SMT Divergence (§24) | Score-এ শুধু `+1` লেখা, logic নেই | Phase 20 |
| AMD / Power of 3 (§25) | ❌ নেই | Phase 21 |
| Trap Trading (§30) | Score-এ শুধু `+1`, logic নেই | Phase 22 |
| Supply & Demand (§29) | ❌ নেই | Phase 23 |
| Mitigation Block (§20) | ❌ নেই | Phase 23 |
| Dynamic Trendline | ❌ কোথাও নেই | **Phase 17–18** |
| Draw on Liquidity / IRL-ERL | ❌ নেই | Phase 26 |
| NWOG / NDOG / ORG | ❌ নেই | Phase 25 |
| Silver Bullet / Macro time | ❌ নেই | Phase 27 |
| MMBM / MMSM / Unicorn | ❌ নেই | Phase 28 |

> **নিয়ম আগের মতোই:** Phase N-এর Proof pass না করে Phase N+1-এ যাবে না। এক phase = এক commit। প্রতিটা নতুন module-এর নিজস্ব `input.bool()` toggle থাকবে, **default `false`** — যাতে নতুন কিছু যোগ করলেও Phase 1–16-এর আচরণ হুবহু অপরিবর্তিত থাকে।

**সোনালী নিয়ম (আবার পড়ো):** এই ডকুমেন্টের একটা module-ও একা signal দেবে না। সব কিছু হয় **Layer 1 context**, নয় **Layer 2 event**, নয় **score-এর উপাদান**। Signal শুধু Phase 11-এর state machine থেকেই আসবে।

---

## 1. নতুন Data Model (Phase 17-এর আগে যোগ করো)

```pinescript
// ── LAYER 1 সম্প্রসারণ ────────────────────────────────
type Trendline
    string id             // "TL_1234"
    int    x1             // প্রথম pivot bar
    float  y1
    int    x2             // দ্বিতীয় pivot bar
    float  y2
    float  slope          // (y2-y1)/(x2-x1) — price per bar
    bool   isSupport      // true = নিচ থেকে ধরে (rising), false = উপর থেকে চাপে
    int    touchCount     // কতবার সঠিকভাবে respect করেছে
    int    lastTouchBar
    bool   broken
    int    brokenBar
    bool   retested
    float  strength       // 0–100 score
    line   drawing

type Gap                  // NWOG / NDOG / ORG — FVG নয়, আলাদা জিনিস
    string kind           // "NWOG" | "NDOG" | "ORG"
    float  top
    float  bottom
    float  ce             // consequent encroachment = (top+bottom)/2
    int    createdBar
    bool   filled

type Divergence
    string kind           // "SMT"
    string direction      // "BULL" | "BEAR"
    int    barIndex
    string refSymbol
    bool   consumed
```

**Setup type-এ নতুন field যোগ করো (Phase 11-এর existing type-এ):**

```pinescript
//     bool   cisdConfirmed
//     bool   smtPresent
//     bool   trapConfirmed
//     string amdPhase        // "ACCUM" | "MANIP" | "DISTRIB" | "NONE"
//     float  dolTarget       // Draw on Liquidity — পরের চুম্বক
//     string modelName       // "SILVER_BULLET" | "MMBM" | "UNICORN" | "STANDARD"
```

**Global state:**

```pinescript
var array<Trendline>  trendlines = array.new<Trendline>()
var array<Gap>        gaps       = array.new<Gap>()
var array<Divergence> divs       = array.new<Divergence>()
```

**Memory cap (বাধ্যতামূলক):** trendlines ≤ 20, gaps ≤ 30, divs ≤ 20। প্রতি bar-এ `broken`/`filled`/`consumed` object cleanup।

---

## 2. Phase Roadmap — এই order বাধ্যতামূলক

| Phase | Module | Layer | নির্ভরশীলতা | আনুমানিক |
|---:|---|---|---|---|
| 17 | **Dynamic Trendline Engine** | 1 | P1 | 2 দিন |
| 18 | Channel + Trendline Liquidity + Break/Retest | 2 | P17 | 1.5 দিন |
| 19 | CISD | 2 | P4, P5 | 1 দিন |
| 20 | SMT Divergence | 1 | P1, P9 | 1 দিন |
| 21 | AMD / Power of 3 + Judas Swing | 1 | P10 | 1.5 দিন |
| 22 | Trap Trading + Turtle Soup | 2 | P3, P5 | 1 দিন |
| 23 | Supply/Demand + Mitigation + Rejection Block | 2 | P7 | 1.5 দিন |
| 24 | BPR + Liquidity Void + CE | 2 | P6 | 1 দিন |
| 25 | NWOG / NDOG / Opening Range Gap | 1 | P2 | 1 দিন |
| 26 | IRL / ERL + Draw on Liquidity | 1 | P2, P8 | 1 দিন |
| 27 | Silver Bullet + Macro Windows | 1 | P10 | 0.5 দিন |
| 28 | MMBM / MMSM + Unicorn Model | 3 | সব | 2 দিন |
| 29 | Daily Bias + Weekly Profile | 1 | P9 | 1 দিন |
| 30 | Standard Deviation Projection | 1 | P5 | 0.5 দিন |
| 31 | **Score v2 + State Machine v2** | 3 | সব | 2 দিন |
| 32 | Dashboard + Visual Density Control | — | সব | 1 দিন |
| 33 | Performance / Object Budget | — | সব | 1 দিন |
| 34 | Extended Integration Tests | — | সব | 1.5 দিন |

**মোট: ~22 কর্মদিবস** (Phase 1–16-এর ১৫ দিনের পরে)।

Phase 17, 28, 31 সবচেয়ে কঠিন — এই তিনটায় তাড়াহুড়ো করবে না।

---

## Phase 17 — Dynamic Trendline Engine ⭐

**Business Logic:**

মানুষ chart-এ হাত দিয়ে যে trendline আঁকে, সেটা আসলে **একই ভুল জায়গায় হাজার জনের একই ধারণা**। সবাই rising trendline-এর নিচে stop বসায়। তাই trendline নিজে support/resistance নয় — trendline হলো **liquidity-র ঠিকানা**, ঠিক swing high/low-এর মতো (Phase 2)।

কিন্তু হাতে আঁকা line-এর সমস্যা: প্রত্যেকে একটু আলাদা আঁকে। তাই code-এ line টানতে হবে **নিয়ম মেনে, যান্ত্রিকভাবে** — যাতে একই chart-এ একই line প্রতিবার আসে।

**দুইটা কাজ trendline করে:**

1. **Dynamic S/R** — দাম line ছুঁলে reaction হয় (কারণ সবাই ওখানে order দিয়েছে)
2. **Trendline liquidity (TLQ)** — line ভাঙলে ওই জমা stop গুলো খায় → প্রায়ই সেটাই sweep, reversal নয়

**❌ ভুল:** "Trendline ভাঙল → SELL"
**✅ ঠিক:** "Trendline ভাঙল → ওখানে stop খাওয়া হলো → এখন দেখো displacement + MSS এল কি না"

---

### 17.1 Anchor নির্বাচন — কোন দুই point দিয়ে line

**Build:**

শুধু **confirmed swing** (Phase 1-এর `swings` array) ব্যবহার করবে। চলমান bar-এর high/low কখনো anchor নয় — নাহলে line প্রতি tick-এ নড়বে (repaint)।

```pinescript
grpTL      = "Trendline"
tlEnable   = input.bool(false, "Enable Dynamic Trendline", group = grpTL)
tlMaxAge   = input.int(200,  "Max Anchor Age (bars)",    minval = 30, maxval = 1000, group = grpTL)
tlMinBars  = input.int(10,   "Min Bars Between Anchors", minval = 5,  maxval = 100,  group = grpTL)
tlMaxLines = input.int(4,    "Max Lines Per Side",       minval = 1,  maxval = 10,   group = grpTL)

// Rising support line: শেষ দুইটা swing LOW, দ্বিতীয়টা প্রথমটার চেয়ে উঁচু
// Falling resist  line: শেষ দুইটা swing HIGH, দ্বিতীয়টা প্রথমটার চেয়ে নিচু
buildSupport(Swing a, Swing b) =>
    valid = b.barIndex - a.barIndex >= tlMinBars and b.price > a.price
    valid ? Trendline.new(
        id = "TL_" + str.tostring(bar_index), x1 = a.barIndex, y1 = a.price,
        x2 = b.barIndex, y2 = b.price,
        slope = (b.price - a.price) / (b.barIndex - a.barIndex),
        isSupport = true, touchCount = 2, lastTouchBar = b.barIndex,
        broken = false, retested = false, strength = 0.0) : na
```

**Anchor নিয়ম (সব পূরণ হতে হবে):**

| নিয়ম | কারণ |
|---|---|
| দুইটাই confirmed pivot | repaint ঠেকানো |
| দূরত্ব ≥ `tlMinBars` | খাড়া অর্থহীন line বাদ |
| বয়স ≤ `tlMaxAge` | পুরনো line কেউ দেখে না |
| Support line-এ `y2 > y1` | rising channel-ই support |
| Resistance line-এ `y2 < y1` | falling channel-ই resistance |

---

### 17.2 Validity Test — line টা আসলেই বৈধ?

**Business Logic:** দুইটা point দিয়ে যেকোনো line টানা যায় — কিন্তু যদি মাঝখানে দাম line-এর ভুল পাশে চলে গিয়ে থাকে, তাহলে ওই line-এর কোনো মূল্য নেই। কেউ সেটা আঁকবে না, কেউ ওখানে stop রাখবে না।

**Build — "কোনো violation নেই" check:**

```pinescript
// x1 থেকে x2 পর্যন্ত প্রতিটা bar: support line-এর নিচে কোনো CLOSE থাকতে পারবে না
// (wick ছাড় দেওয়া হয় — ওটাই stop hunt)
tlIsClean(Trendline t) =>
    ok  = true
    len = t.x2 - t.x1
    for i = 0 to len
        off = bar_index - (t.x1 + i)
        if off >= 0 and off < 4000
            lineY = t.y1 + t.slope * i
            if t.isSupport and close[off] < lineY - syminfo.mintick
                ok := false
            if not t.isSupport and close[off] > lineY + syminfo.mintick
                ok := false
    ok
```

> **Performance সতর্কতা:** এই loop প্রতি bar-এ প্রতিটা candidate line-এ চালালে chart জমে যাবে। **শুধু line তৈরির মুহূর্তে একবার** চালাও, তারপর result cache করো। পরে প্রতি bar-এ শুধু নতুন bar-টা check করো (incremental)।

---

### 17.3 Strength Score — কোন line গুরুত্বপূর্ণ

**Business Logic:** যে line ৫ বার respect হয়েছে সেটা ২ বারের line-এর চেয়ে অনেক বেশি মানুষ দেখছে — মানে ওখানে stop-এর পরিমাণ অনেক বেশি।

```pinescript
// 0–100
tlStrength(Trendline t) =>
    touchScore = math.min(t.touchCount, 6) * 12                 // সর্বোচ্চ 72
    ageBars    = bar_index - t.x1
    ageScore   = math.min(ageBars / 10, 15)                     // সর্বোচ্চ 15
    slopeNorm  = math.abs(t.slope) / (atrVal / 10)
    angleScore = slopeNorm > 0.2 and slopeNorm < 3.0 ? 13 : 0   // খুব খাড়া/সমতল = খারাপ
    math.min(touchScore + ageScore + angleScore, 100)
```

**Touch গণনার নিয়ম:** দাম line-এর `atrVal * 0.25` ভেতরে এল **এবং** সঠিক দিকে close করল → `touchCount += 1`। একই touch পরপর ৩ bar গোনা যাবে না — `lastTouchBar` দিয়ে cooldown।

---

### 17.4 অগ্রাধিকার ও পরিচ্ছন্নতা

- প্রতি দিকে সর্বোচ্চ `tlMaxLines` টা line — `strength` অনুযায়ী sort, দুর্বলগুলো ফেলে দাও
- দুইটা line প্রায় সমান্তরাল ও কাছাকাছি (`|slope1-slope2| < atr*0.02` এবং বর্তমান bar-এ দূরত্ব `< atr*0.5`) → শুধু বেশি strength-এরটা রাখো
- `broken = true` হওয়ার ২০ bar পর line মুছে ফেলো

**Definition of Done:**

- [ ] Line শুধু confirmed swing থেকে তৈরি — চলমান bar কখনো anchor নয়
- [ ] Validity test (17.2) pass না করলে line তৈরিই হয় না
- [ ] `touchCount` সঠিক গোনা হয়, একই touch দুইবার গোনা হয় না
- [ ] প্রতি দিকে line সংখ্যা cap মানা হয়
- [ ] Strength অনুযায়ী line-এর opacity/thickness আলাদা দেখায়
- [ ] `line.set_xy2()` দিয়ে extend হয় — প্রতি bar-এ নতুন line object তৈরি হয় না
- [ ] সম্পূর্ণ module একটা toggle দিয়ে বন্ধ করা যায় (default off)

**Proof:**

1. Chart reload (F5) → প্রতিটা line হুবহু আগের জায়গায়, একই anchor
2. Realtime-এ ১০ মিনিট দেখো → line-এর anchor নড়ে না (শুধু ডান দিক extend হয়)
3. ৫০০০ bar history → `line` object সংখ্যা কখনো 50 ছাড়ায় না
4. চোখে দেখো: যেসব line code এঁকেছে, একজন মানুষ হাতে মোটামুটি ওখানেই আঁকত
5. স্পষ্ট violation-ওয়ালা জায়গায় কোনো line নেই

---

## Phase 18 — Channel + Trendline Liquidity + Break/Retest

**Business Logic:**

দুইটা সমান্তরাল line = channel। Channel-এর মূল্য হলো — উপরের line-এর উপরে আর নিচের line-এর নিচে **stop জমে**। Channel যত দীর্ঘ, তত বেশি মানুষ সেটা দেখছে, তত বড় liquidity pool।

**Trendline break-এর পর আসল প্রশ্ন দুইটা:**

| যা ঘটল | মানে | করণীয় |
|---|---|---|
| ভাঙল, displacement সহ, ফিরে এসে retest হলো, structure ভাঙল | আসল break | trend-এর নতুন দিক ধরো |
| ভাঙল, কিন্তু সাথে সাথে ভেতরে ফিরে close করল | **TLQ sweep** — শুধু stop খেল | উল্টো দিকে setup খোঁজো |

দ্বিতীয়টাই বেশি ঘটে। তাই default আচরণ — trendline break কে **sweep candidate** ধরা, breakout নয়।

**Build:**

```pinescript
tlBreakMode = input.string("Close", "TL Break Mode", options = ["Close", "Wick"], group = grpTL)
tlqEnable   = input.bool(true, "Treat TL Break as Liquidity", group = grpTL)

tlPriceNow(Trendline t) => t.y2 + t.slope * (bar_index - t.x2)

// Support line ভাঙা
lineY = tlPriceNow(t)
broke = tlBreakMode == "Close" ? close < lineY : low < lineY

// TLQ sweep = wick নিচে গেল কিন্তু close ভেতরেই
tlqSweep = low < lineY and close > lineY and (close - low) / rangeSize > 0.5
```

- `broke` হলে → `t.broken := true`, `t.brokenBar := bar_index`
- Break-এর পর ২০ bar-এর মধ্যে দাম line-এ ফিরে এসে reject করলে → `t.retested := true` (এটাই ভালো entry context)
- `tlqSweep` হলে → Phase 2-এর `liquidity` array-তে `LiqLevel.new(kind = "TLQ", price = lineY, swept = true)` push করো

> **সংযোগ (গুরুত্বপূর্ণ):** এখানেই trendline Phase 11-এর state machine-এ ঢোকে। TLQ sweep ঠিক SSL/BSL sweep-এর মতোই আচরণ করবে — `CONTEXT_FOUND → LIQUIDITY_SWEPT` transition trigger করতে পারবে। আলাদা কোনো signal path তৈরি করবে না।

**Channel Build:**

- Support line আছে, তার সমান্তরাল (একই slope) line উপরের swing high-গুলোর মধ্যে সবচেয়ে দূরেরটা ছুঁয়ে → upper channel
- Channel width `< atrVal * 1.5` হলে বাদ দাও (খুব সরু, অর্থহীন)

**Definition of Done:**

- [ ] TLQ sweep আর genuine break আলাদা করে চিহ্নিত (দুইটা আলাদা label + রঙ)
- [ ] TLQ `liquidity` array-তে ঢোকে, state machine-এ আলাদা path নেই
- [ ] Retest detect হয় এবং `retested` flag set হয়
- [ ] Channel toggle করা যায়, default off
- [ ] Trendline নিজে কখনো signal emit করে না

**Proof:**

- Trendline break হয়েছে কিন্তু displacement নেই → **কোনো trade নেই**
- TLQ sweep + displacement + MSS → LONG/SHORT আসে, কিন্তু Phase 11-এর পথ ধরেই
- Trendline module বন্ধ করলে Phase 1–16-এর signal সংখ্যা **হুবহু আগের মতো**

---

## Phase 19 — CISD (Change in State of Delivery)

**Business Logic:**

MSS বলে "structure ভাঙল" — কিন্তু structure ভাঙতে অনেক bar লাগে। CISD হলো **তার আগের সবচেয়ে ছোট প্রমাণ**: একটা candle এমন জায়গায় close করল যেখানে আগের ধারাবাহিক বিপরীত candle-গুলোর delivery বাতিল হয়ে গেল।

সহজভাবে — নিচে নামার সময় পরপর কয়েকটা লাল candle ছিল। এখন একটা সবুজ candle এসে ওই পুরো লাল দলের **প্রথম candle-এর open**-এর উপরে close করল। মানে বিক্রেতাদের ওই পুরো চেষ্টাটা বাতিল।

CISD MSS-এর **আগে** আসে। তাই CISD = early confirmation, MSS = full confirmation। CISD একা entry নয় — কিন্তু CISD থাকলে setup-এর মান বাড়ে, আর CISD-র level টা চমৎকার SL reference।

**Build:**

```pinescript
grpC       = "CISD"
cisdOn     = input.bool(false, "Enable CISD", group = grpC)
cisdMaxRun = input.int(6, "Max Candle Run", minval = 2, maxval = 12, group = grpC)

// Bullish CISD: পরপর N টা bearish candle-এর দল, তারপর bullish close
// ওই দলের প্রথম candle-এর OPEN-এর উপরে
var float cisdBullLevel = na
var int   runLen        = 0

if close < open
    runLen += 1
else
    runLen := 0

// দল শেষ হওয়ার মুহূর্তে reference ধরে রাখো
if runLen >= 2 and runLen <= cisdMaxRun
    cisdBullLevel := open[runLen - 1]

bullCISD = not na(cisdBullLevel) and close > cisdBullLevel and close > open
```

Bearish হুবহু উল্টো — পরপর bullish candle-এর দল, তারপর নিচে close।

**Definition of Done:**

- [ ] Run length গণনা সঠিক, `cisdMaxRun` এর বেশি দলে CISD হয় না
- [ ] CISD level chart-এ ছোট dashed line হিসেবে দেখা যায়
- [ ] CISD ব্যবহৃত হয় শুধু (ক) score `+1`, (খ) `LIQUIDITY_SWEPT → DISPLACEMENT_CONFIRMED` transition-এর বিকল্প প্রমাণ হিসেবে, যদি `cisdAsDisplacement` input on থাকে
- [ ] CISD কখনো একা signal দেয় না

**Proof:**

- Sideways chop-এ CISD প্রচুর আসে — সেটাই স্বাভাবিক, তাই এটা একা কিছু নয়
- প্রতিটা MSS-এর আগে সাধারণত একটা CISD পাওয়া যায় (সময়ের ক্রম ঠিক আছে কি না যাচাই করো)

---

## Phase 20 — SMT Divergence

**Business Logic:**

দুইটা সম্পর্কিত জিনিস (EURUSD ও GBPUSD; ES ও NQ; DXY ও EURUSD) সাধারণত একসাথে নড়ে। যখন একটা নতুন low বানায় কিন্তু অন্যটা বানায় না — সেটা বলে দেয় যে বিক্রির চাপ আসল নয়। একটা বাজারে stop খাওয়ানো হচ্ছে, অন্যটা তাল মেলাচ্ছে না।

এটা **অত্যন্ত শক্তিশালী confirmation**, কিন্তু আবারও — একা কিছু নয়। SMT + sweep + MSS = খুব ভালো। শুধু SMT = কিছু না।

**Build:**

```pinescript
grpS    = "SMT"
smtOn   = input.bool(false, "Enable SMT Divergence", group = grpS)
smtSym  = input.symbol("", "Correlated Symbol", group = grpS)
smtInv  = input.bool(false, "Inverse Correlation (e.g. DXY)", group = grpS)
smtLook = input.int(20, "Lookback", minval = 5, maxval = 60, group = grpS)

[cHigh, cLow] = request.security(smtSym, timeframe.period, [high[1], low[1]],
                                 lookahead = barmerge.lookahead_off)

myLow = ta.lowest(low,  smtLook)
coLow = ta.lowest(cLow, smtLook)

// Bullish SMT: আমি নতুন low বানালাম, correlated বানায়নি
bullSMT = low <= myLow and cLow > coLow
bullSMT := smtInv ? (low <= myLow and cHigh < ta.highest(cHigh, smtLook)) : bullSMT
```

**Definition of Done:**

- [ ] `request.security`-তে `[1]` offset + `lookahead_off` (নাহলে repaint audit-এ ধরা পড়বে)
- [ ] Correlated symbol খালি থাকলে module নিঃশব্দে skip — error নয়
- [ ] Inverse correlation toggle কাজ করে (DXY-র জন্য)
- [ ] SMT শুধু score `+1` দেয় (spec §32 অনুযায়ী)
- [ ] Divergence chart-এ দেখা যায় (দুই swing জুড়ে dotted line)

**Proof:**

- ভুল/অসম্পর্কিত symbol দিলে (যেমন BTCUSD vs EURUSD) প্রচুর অর্থহীন SMT আসবে — documentation-এ এটা লিখে দাও
- SMT থাকা-না-থাকায় signal সংখ্যা বদলায় না, শুধু score বদলায়

---

## Phase 21 — AMD / Power of 3 + Judas Swing

**Business Logic:**

প্রতিটা trading দিন প্রায় একই নাটক তিন অঙ্কে:

1. **Accumulation** — এশিয়া session, সরু range, institution চুপচাপ position নিচ্ছে
2. **Manipulation** — London open, range-এর উল্টো দিকে একটা ঝটকা (**Judas Swing**) — retail কে ভুল দিকে ঢোকানো + stop খাওয়া
3. **Distribution** — আসল move, সাধারণত NY session

কেন কাজে লাগে: সকালের প্রথম বড় move প্রায়ই **মিথ্যা**। ওই মিথ্যা move-এর দিক জানলে আসল দিন কোনদিকে যাবে সেটা আগেই বোঝা যায়।

**Build:**

```pinescript
grpA   = "AMD / PO3"
amdOn  = input.bool(false, "Enable AMD", group = grpA)
asiaS  = input.session("2000-0000", "Accumulation (Asia)",    group = grpA)
judasS = input.session("0200-0500", "Manipulation (London)",  group = grpA)
distS  = input.session("0700-1100", "Distribution (NY)",      group = grpA)

var float asiaHigh     = na
var float asiaLow      = na
var bool  asiaRangeSet = false

newDay = ta.change(time("D")) != 0
if newDay
    asiaHigh     := na
    asiaLow      := na
    asiaRangeSet := false

inAsia = not na(time(timeframe.period, asiaS, tz))
if inAsia
    asiaHigh := na(asiaHigh) ? high : math.max(asiaHigh, high)
    asiaLow  := na(asiaLow)  ? low  : math.min(asiaLow,  low)
if not inAsia and inAsia[1]
    asiaRangeSet := true          // range lock — এখন আর বদলাবে না

inJudas   = not na(time(timeframe.period, judasS, tz))
judasBull = inJudas and asiaRangeSet and low  < asiaLow  and close > asiaLow
judasBear = inJudas and asiaRangeSet and high > asiaHigh and close < asiaHigh
```

- `judasBull` → `amdPhase := "MANIP"`, দিনের প্রত্যাশিত bias = **BULL**
- Distribution window-এ ওই bias-এর দিকের setup `+1` score পায়, বিপরীতমুখী setup `−1`

**Definition of Done:**

- [ ] Asia range দিনে একবার lock হয়, পরে আর বদলায় না
- [ ] Judas swing detect হয় এবং chart-এ চিহ্নিত হয়
- [ ] দিনের AMD phase dashboard-এ দেখা যায়
- [ ] Session window সব input, hard-coded নয়, timezone input থেকে আসে
- [ ] AMD শুধু bias ও score দেয় — signal নয়

**Proof:**

- Asia range box আজকের চলমান দিনে সঠিক সময়ে বন্ধ হয়
- Weekend/ছুটির দিনে module crash করে না (range খালি থাকলে skip)

---

## Phase 22 — Trap Trading + Turtle Soup

**Business Logic:**

**Bull Trap** — দাম resistance ভেঙে উপরে গেল, সবাই ভাবল breakout, কিনল। তারপর সাথে সাথে ফিরে ভেতরে ঢুকে গেল। যারা কিনেছিল তারা এখন আটকা — তাদের বেরোতেই হবে, সেই বাধ্যতামূলক বিক্রিই দামকে আরও নিচে ঠেলে।

**Turtle Soup** হলো একই জিনিসের ICT নাম: ২০-bar high/low ভাঙার পর ফিরে আসা।

Trap আর sweep প্রায় একই ঘটনা — পার্থক্য শুধু সময়ের দৈর্ঘ্যে। Sweep এক candle-এ ঘটে; trap-এ দাম কয়েক bar বাইরে থাকতে পারে, তারপর ফেরে। তাই **আলাদা module দরকার** — sweep logic trap ধরতে পারবে না।

**Build:**

```pinescript
grpT     = "Trap"
trapOn   = input.bool(false, "Enable Trap Detection", group = grpT)
trapBars = input.int(5,  "Max Bars Outside",       minval = 1,  maxval = 15, group = grpT)
tsLook   = input.int(20, "Turtle Soup Lookback",   minval = 10, maxval = 60, group = grpT)

var int barsAboveLevel = 0
if close > lastSwingHigh
    barsAboveLevel += 1
else
    barsAboveLevel := 0

// Bull trap: ভেঙেছিল, ≤ trapBars bar বাইরে ছিল, এখন ভেতরে close
bullTrap = barsAboveLevel[1] >= 1 and barsAboveLevel[1] <= trapBars
           and close < lastSwingHigh

// Turtle soup: ২০ bar high ভেঙে ফিরে আসা
tsLevel = ta.highest(high[1], tsLook)
tsShort = high > tsLevel and close < tsLevel
```

**Definition of Done:**

- [ ] Trap আর genuine breakout আলাদা (bars-outside গণনা দিয়ে)
- [ ] `trapBars` ছাড়িয়ে গেলে সেটা trap নয় — genuine breakout, trend flip
- [ ] Trap হলে `liquidity` array-তে swept level push হয় (sweep-এর মতোই পথ)
- [ ] Trap score `+1` (spec §32)
- [ ] Turtle Soup আলাদা toggle

**Proof:**

- ভাঙার পর ১০ bar উপরে থেকে তারপর নামল → trap **নয়** (`trapBars = 5` হলে)
- Trap detect হলে state machine-এ ঠিক sweep-এর মতোই প্রবেশ করে, আলাদা signal path নেই

---

## Phase 23 — Supply / Demand + Mitigation Block + Rejection Block

**Business Logic:**

Order Block (Phase 7) হলো **একটা candle**। Supply/Demand **zone** হলো একটা ছোট consolidation এলাকা যেখান থেকে বড় move শুরু হয়েছিল — কয়েকটা candle মিলে। OB precise, S/D zone প্রশস্ত। দুটোই দরকার — S/D দেয় প্রেক্ষাপট, OB দেয় নির্ভুল entry।

**Mitigation Block** — OB ভাঙল না, কিন্তু দাম ফিরে এসে ওখানকার আটকা position গুলো break-even-এ ছেড়ে দিল। তারপর আবার মূল দিকে গেল। Breaker-এর চেয়ে দুর্বল, কিন্তু trend continuation-এ কাজ করে।

**Rejection Block** — OB-র মতো, তবে body নয়, **wick** দিয়ে মাপা। যেখানে লম্বা wick বারবার প্রত্যাখ্যান করেছে।

**Build:**

- **Demand zone:** ≥3 candle-এর সরু range (`range < atr * 0.8`), তার পরেই bullish displacement → zone = ওই consolidation-এর high/low
- **Mitigation Block:** `Zone.kind = "MB"` — OB যেটা touch হয়েছে কিন্তু ভাঙেনি (`state = TOUCHED` অথচ `mitigationPct < 100`), এবং তারপর মূল দিকে displacement এসেছে
- **Rejection Block:** যে candle-এর wick `> range * 0.6`, সেই wick-এর অংশটাই zone

**Zone priority (overlap হলে কে জেতে):**

```text
FVG > OB > Breaker > MB > Rejection Block > S/D zone
```

**Definition of Done:**

- [ ] পাঁচ ধরনের zone আলাদা `kind`, আলাদা রঙ, আলাদা toggle
- [ ] Priority নিয়ম প্রয়োগ হয় — overlap-এ একটাই zone আঁকা হয়
- [ ] S/D zone চলমান consolidation থেকে তৈরি হয় না (শুধু শেষ হওয়া consolidation)
- [ ] সব zone একই lifecycle state machine (Phase 6) মানে
- [ ] Zone মোট সংখ্যা cap 100-এর মধ্যে

**Proof:**

- সব zone toggle off → chart পরিষ্কার, Phase 1–16 signal অপরিবর্তিত
- Zone গুলো একটা আরেকটার উপর স্তূপ হয়ে যায় না

---

## Phase 24 — BPR + Liquidity Void + Consequent Encroachment

**Business Logic:**

**BPR (Balanced Price Range)** — একই জায়গায় একটা bullish FVG আর একটা bearish FVG উপরে-নিচে বসে গেছে। দুই দিকের অসামঞ্জস্য একই জায়গায় মানে ওটা খুব শক্ত ভারসাম্য বিন্দু — সাধারণ FVG-র চেয়ে বেশি নির্ভরযোগ্য।

**Liquidity Void** — শুধু ৩-candle gap নয়, বরং পরপর কয়েকটা candle প্রায় বিনা overlap-এ চলে গেছে — একটা বড় ফাঁকা করিডোর। দাম প্রায়ই পুরোটা ফেরত পূরণ করে।

**CE (Consequent Encroachment)** — যেকোনো gap-এর ঠিক মাঝবিন্দু (৫০%)। বাস্তবে দাম প্রায়ই gap পুরো পূরণ না করে ঠিক মাঝখান থেকে ঘুরে যায়। তাই entry-র জন্য CE = সবচেয়ে কার্যকর একক দাম।

**Build:**

```pinescript
// CE — প্রতিটা Zone আর Gap-এর জন্য
ce(float top, float bottom) => (top + bottom) / 2

// BPR — bullish FVG আর bearish FVG overlap
bprTop    = math.min(bullFVGTop, bearFVGTop)
bprBottom = math.max(bullFVGBottom, bearFVGBottom)
isBPR     = bprTop > bprBottom
```

- Liquidity Void: পরপর ≥3 candle যেখানে প্রতিটার সাথে আগেরটার overlap `< range * 0.2`
- CE line প্রতিটা zone-এর ভেতরে dashed line হিসেবে আঁকো
- Entry mode input: `"Zone Edge" | "CE" | "Zone Full"` — default **CE**

**Definition of Done:**

- [ ] CE সব zone আর gap-এ হিসাব হয় এবং আঁকা যায়
- [ ] Entry reference input দিয়ে বেছে নেওয়া যায়
- [ ] BPR আলাদা রঙে, আলাদা `kind = "BPR"`
- [ ] Liquidity Void আলাদা toggle, default off (chart ভরে যায়)

**Proof:**

- Entry mode "CE" করলে entry price zone-এর ঠিক মাঝখানে বসে, RR সেই অনুযায়ী বদলায়
- BPR শুধু তখনই আঁকা হয় যখন দুই দিকের FVG সত্যিই overlap করে

---

## Phase 25 — NWOG / NDOG / Opening Range Gap

**Business Logic:**

শুক্রবার close আর রবিবার open-এর মধ্যে যে ফাঁক (**NWOG** — New Week Opening Gap), সেখানে কোনো লেনদেন হয়নি। পুরো সপ্তাহ ওই এলাকা চুম্বকের মতো কাজ করে। **NDOG** একই জিনিস দৈনিক। **ORG** = index-এর regular session open আর আগের close-এর ফাঁক।

এগুলো FVG নয় — FVG তিন candle-এর গঠন, এগুলো **সময়ভিত্তিক** ফাঁক। তাই আলাদা type (`Gap`), আলাদা রঙ, আলাদা toggle।

**Build:**

```pinescript
grpG   = "Opening Gaps"
nwogOn = input.bool(false, "New Week Opening Gap", group = grpG)
nwogN  = input.int(3, "Keep Last N Gaps", minval = 1, maxval = 10, group = grpG)

newWeek = ta.change(time("W")) != 0
if newWeek and nwogOn
    prevClose = request.security(syminfo.tickerid, "W", close[1],
                                 lookahead = barmerge.lookahead_off)
    array.push(gaps, Gap.new(kind = "NWOG",
        top = math.max(open, prevClose), bottom = math.min(open, prevClose),
        ce = (open + prevClose) / 2, createdBar = bar_index, filled = false))
```

**Definition of Done:**

- [ ] শেষ N টা gap রাখা হয়, বাকি মুছে যায়
- [ ] CE line প্রতিটা gap-এ আঁকা
- [ ] Gap সম্পূর্ণ পূরণ হলে `filled := true`, box ধূসর
- [ ] `request.security`-তে `[1]` + `lookahead_off`
- [ ] Gap শুধু Layer 1 context — TP target ও score-এ ব্যবহৃত, signal নয়

**Proof:**

- Forex-এ রবিবার open-এ NWOG আসে; crypto-তে (24/7) gap প্রায় শূন্য — দুটোই সঠিক আচরণ
- Reload-এ gap-এর জায়গা অপরিবর্তিত

---

## Phase 26 — IRL / ERL + Draw on Liquidity

**Business Logic:**

দাম সবসময় একটা লক্ষ্যের দিকে যাচ্ছে — সেই লক্ষ্যটাই **Draw on Liquidity (DOL)**। বাজার দুইটা জিনিসের মধ্যে দোল খায়:

- **IRL (Internal Range Liquidity)** — range-এর ভেতরের FVG, OB — এগুলো **entry**-র জায়গা
- **ERL (External Range Liquidity)** — range-এর বাইরের swing high/low, EQH/EQL — এগুলো **target**-এর জায়গা

নিয়ম: দাম ERL থেকে IRL-এ যায়, তারপর IRL থেকে ERL-এ। মানে — FVG থেকে entry নিয়ে swing high-এ TP। এটাই Phase 12-এর TP priority-র পেছনের কারণ; এখানে সেটা স্পষ্ট model হিসেবে লেখা হচ্ছে।

**Build:**

- Dealing range (Phase 8) এর ভেতরের সব zone = IRL
- Range-এর বাইরের সব `LiqLevel` = ERL
- `dolTarget` = বর্তমান bias-এর দিকে সবচেয়ে কাছের **unswept** ERL
- Chart-এ DOL একটা তীর/line দিয়ে দেখাও

**Definition of Done:**

- [ ] প্রতিটা zone ও level IRL/ERL হিসেবে শ্রেণীবদ্ধ
- [ ] `dolTarget` হিসাব হয় এবং Phase 12-এর TP এর সাথে সঙ্গতিপূর্ণ
- [ ] Structure বদলালে শ্রেণীবিভাগ নতুন করে হয়
- [ ] DOL dashboard-এ দেখা যায়

**Proof:**

- TP সবসময় একটা ERL-এ বসে, কখনো range-এর মাঝখানে শূন্যস্থানে নয়
- Entry সবসময় একটা IRL-এ বসে

---

## Phase 27 — Silver Bullet + Macro Windows

**Business Logic:**

দিনের কিছু নির্দিষ্ট ১ ঘণ্টা বা ২০ মিনিটের জানালায় algorithmic কার্যকলাপ সবচেয়ে ঘন। ICT-র Silver Bullet — NY সময় **10:00–11:00**, **14:00–15:00**, আর London **03:00–04:00**। Macro window — প্রতি ঘণ্টার **:50 থেকে পরের ঘণ্টার :10**।

এগুলো signal নয় — **সময়ের filter**। একই setup ওই জানালায় হলে বেশি নির্ভরযোগ্য।

**Build:**

```pinescript
grpSB  = "Silver Bullet"
sbOn   = input.bool(false, "Enable Silver Bullet Window", group = grpSB)
sb1    = input.session("1000-1100", "NY AM",  group = grpSB)
sb2    = input.session("1400-1500", "NY PM",  group = grpSB)
sb3    = input.session("0300-0400", "London", group = grpSB)
sbOnly = input.bool(false, "Signals ONLY in SB window", group = grpSB)

inSB = not na(time(timeframe.period, sb1, tz))
    or not na(time(timeframe.period, sb2, tz))
    or not na(time(timeframe.period, sb3, tz))

macroOn = input.bool(false, "Macro Windows (:50-:10)", group = grpSB)
minNow  = minute(time, 1)
inMacro = minNow >= 50 or minNow <= 10
```

**Definition of Done:**

- [ ] তিনটা window আলাদা input, timezone input থেকে
- [ ] `sbOnly` on থাকলে window-এর বাইরে signal emit বন্ধ (state machine চলতে থাকে, শুধু emit আটকায়)
- [ ] Window background shading toggle
- [ ] Score `+1` যদি entry SB window-এ হয়

**Proof:**

- `sbOnly` on করলে signal সংখ্যা স্পষ্টভাবে কমে, কিন্তু কোনো state আটকে যায় না
- Macro window intraday timeframe (≤15M) ছাড়া অর্থহীন — ≥1H timeframe-এ auto-disable

---

## Phase 28 — MMBM / MMSM + Unicorn Model

**Business Logic:**

**MMBM (Market Maker Buy Model)** হলো পুরো দিন/সপ্তাহের ছক, একক ঘটনা নয়:

```text
Original Consolidation → Sell-side curve (নিচে নামা)
  → Smart Money Reversal (SSL sweep + MSS)
  → Buy-side curve (উপরে ওঠা) → Original Consolidation-এ ফেরা
```

মানে দাম যেখান থেকে শুরু করেছিল, শেষ পর্যন্ত সেখানেই ফেরে — মাঝের পুরোটা stop সংগ্রহ। এটা ধরতে পারলে TP কোথায় হবে সেটা আগেই জানা যায়।

**Unicorn Model** — সবচেয়ে উচ্চমানের setup: একটা **Breaker Block** আর একটা **FVG** ঠিক একই দামে overlap করছে। দুইটা স্বাধীন কারণ একই বিন্দুতে।

**Build:**

- MMBM: Phase 8-এর dealing range + Phase 11-এর state ট্র্যাক করে একটা উচ্চস্তরের `marketModel` var রাখো
- Unicorn: `zones` array-তে একটা `kind = "BB"` আর একটা `kind = "FVG"` যাদের top/bottom overlap `> 50%` → নতুন `kind = "UNICORN"`, score `+2` (confluence শ্রেণী)
- `modelName` field Setup-এ set করো, signal label-এ দেখাও

**Definition of Done:**

- [ ] Unicorn overlap হিসাব সঠিক (শতাংশ ভিত্তিক, শুধু ছোঁয়া নয়)
- [ ] Unicorn zone আলাদা রঙে, স্পষ্ট label
- [ ] MMBM/MMSM dashboard-এ phase দেখায়
- [ ] `modelName` alert message-এ যায়
- [ ] কোনো model একা signal দেয় না — শুধু score আর label

**Proof:**

- Unicorn বিরল — ১০০০ bar-এ ০–৩টা। বেশি এলে overlap threshold ঢিলা।
- MMBM phase বদলালে আগের signal পুনর্লিখিত হয় না

---

## Phase 29 — Daily Bias + Weekly Profile

**Business Logic:**

সপ্তাহের দিনের নিজস্ব চরিত্র আছে: সপ্তাহের high/low প্রায়ই মঙ্গল বা বুধবার তৈরি হয়; সোমবার সাধারণত সরু; শুক্রবার প্রায়ই আগের move-এর retrace। Daily bias আসে — আগের দিনের high/low-এর কোনটা নেওয়া হয়েছে, HTF FVG কোথায়, আর সপ্তাহের খোলা দাম থেকে এখন উপরে না নিচে।

**Build:**

- `weeklyOpen` = চলমান সপ্তাহের প্রথম bar-এর open — `ta.valuewhen(newWeek, open, 0)` (`request.security("W", open)` নয়, ওটা repaint করবে)
- Daily bias = (HTF bias `×2`) + (PDH/PDL কোনটা swept) + (weekly open-এর উপরে/নিচে)
- Dashboard-এ দেখাও: `BULL / BEAR / NEUTRAL` + কারণ

**Definition of Done:**

- [ ] Weekly open repaint করে না
- [ ] Bias হিসাবের প্রতিটা উপাদান dashboard-এ আলাদা করে দেখা যায়
- [ ] Bias শুধু score ও filter — signal নয়
- [ ] Day-of-week label optional toggle

---

## Phase 30 — Standard Deviation Projection

**Business Logic:**

Sweep low থেকে MSS high পর্যন্ত দূরত্বটাকে একক ধরে, সেটার গুণিতক (−1, −2, −2.5, −4) ভবিষ্যতের দিকে প্রক্ষেপণ করলে দাম প্রায়ই ঠিক ওই level-গুলোতে থামে। যখন কাছাকাছি কোনো liquidity target নেই, তখন TP-র জন্য এটা কাজে লাগে।

**Build:**

```pinescript
sdOn   = input.bool(false, "Std Dev Projections", group = "Targets")
sdMult = input.string("-2,-2.5,-4", "Multipliers", group = "Targets")

unit = mssLevel - sweepLevel               // bullish
// প্রতিটা multiplier m: level = sweepLevel + unit * math.abs(m)
```

**Definition of Done:**

- [ ] Multiplier input, comma-separated parse
- [ ] Level গুলো dotted line, label সহ
- [ ] TP priority-তে সবার **শেষে** — liquidity target থাকলে সেটাই জেতে
- [ ] Default off

---

## Phase 31 — Score v2 + State Machine v2 ⭐

**Business Logic:**

এতগুলো নতুন উপাদান যোগ হওয়ার পর score সহজেই ফুলে যাবে — সব কিছু `+1` করলে প্রায় প্রতিটা setup "A+" দেখাবে। তাই score-কে **শ্রেণীবদ্ধ** করতে হবে, আর একই জিনিস দুইবার গোনা যাবে না।

**মূল নীতি — এক শ্রেণী থেকে সর্বোচ্চ একবারই পয়েন্ট:**

| শ্রেণী | সদস্য | সর্বোচ্চ |
|---|---|---:|
| Context (HTF) | HTF bias, Daily bias, Weekly profile | +2 |
| Liquidity | SSL/BSL sweep, TLQ, Trap, Turtle Soup | +2 |
| Structure | MSS, CISD, BOS | +2 |
| Momentum | Displacement | +2 |
| POI | FVG, OB, BB, MB, S/D, BPR | +1 |
| POI Confluence | Unicorn (BB+FVG), FVG+OB overlap | +2 |
| Location | Premium/Discount, OTE, CE | +1 |
| Time | Kill Zone, Silver Bullet, Macro, AMD distribution | +1 |
| Correlation | SMT | +1 |
| **সর্বোচ্চ সম্ভব** | | **14** |

**Contradiction penalty (যোগ নয়, বিয়োগ):**

| দ্বন্দ্ব | শাস্তি |
|---|---:|
| HTF bias উল্টো | −3 |
| Daily bias উল্টো | −2 |
| AMD manipulation-এর দিকেই trade (Judas-এর ফাঁদে পা) | −2 |
| POI ইতিমধ্যে ২+ বার touched | −1 |
| Entry premium-এ কিন্তু LONG (বা discount-এ কিন্তু SHORT) | −2 |

| Score | Grade | কর্ম |
|---:|---|---|
| ≤ 4 | Weak | NO TRADE |
| 5–7 | Moderate | optional (input দিয়ে on/off) |
| 8–10 | Strong | trade |
| 11+ | A+ | trade, size বড় করার যোগ্য |

**State Machine v2 — নতুন transition:**

```text
CONTEXT_FOUND ──> LIQUIDITY_SWEPT
   ট্রিগার করতে পারে যেকোনো একটা:
     • SSL/BSL sweep      (Phase 5)
     • TLQ sweep          (Phase 18)  ← নতুন
     • Trap / Turtle Soup (Phase 22)  ← নতুন

LIQUIDITY_SWEPT ──> DISPLACEMENT_CONFIRMED
     • displacement candle (Phase 4)
     • অথবা CISD, যদি cisdAsDisplacement = true (Phase 19)  ← নতুন

MSS_CONFIRMED ──> POI_CREATED
     • FVG | OB | BB | MB | S/D | BPR | UNICORN
       (Phase 6, 7, 23, 24, 28)  ← সম্প্রসারিত

RETRACE_WAIT ──> ENTRY_TRIGGERED
     • RR ≥ minRR  এবং  score ≥ threshold
     • এবং (sbOnly হলে) inSB = true  ← নতুন
```

**বাধ্যতামূলক নিয়ম (Phase 11-এর ৫টার সাথে নতুন ৪টা):**

6. একই bar-এ একাধিক liquidity trigger (যেমন SSL sweep + TLQ) → **একবারই** transition, আর Liquidity শ্রেণী থেকে **একটাই** পয়েন্ট
7. নতুন কোনো module signal emit করতে পারবে না — শুধু state trigger বা score
8. প্রতিটা নতুন module-এর toggle off করলে state machine-এ তার path সম্পূর্ণ নিষ্ক্রিয়
9. Score threshold input, default 8 (v1-এ ছিল 7 — উপাদান বেড়েছে তাই বেড়েছে)

**Definition of Done:**

- [ ] শ্রেণীভিত্তিক capping প্রয়োগ হয় — double counting নেই
- [ ] সব contradiction penalty কাজ করে
- [ ] Debug table-এ শ্রেণী অনুযায়ী score ভাঙা দেখা যায়
- [ ] সব নতুন module off করলে score হিসাব v1-এর সমান ফল দেয়
- [ ] State machine কখনো পেছনে যায় না

**Proof:**

- সব নতুন toggle off → Phase 16-এর ১০টা test হুবহু আগের ফল দেয় (**সবচেয়ে গুরুত্বপূর্ণ proof**)
- সব toggle on → signal সংখ্যা **কমে** (filter বেড়েছে), বাড়ে না। বাড়লে কোথাও একটা module signal emit করছে — খুঁজে বের করো।

---

## Phase 32 — Dashboard + Visual Density Control

**Business Logic:**

এতগুলো module on থাকলে chart অপাঠ্য হয়ে যাবে। তাই দুইটা জিনিস দরকার — সংখ্যায় প্রকাশ করা dashboard, আর একটা master "কতটা দেখাবে" knob।

**Build:**

```pinescript
densityMode = input.string("Normal", "Visual Density",
                           options = ["Minimal", "Normal", "Full"], group = "Visuals")
// Minimal : শুধু active setup-এর POI + signal label
// Normal  : + structure label, liquidity level, active zone
// Full    : সব কিছু
```

**Dashboard table (উপর-ডান কোণে):**

| সারি | বিষয়বস্তু |
|---:|---|
| 1 | HTF Bias / Daily Bias |
| 2 | AMD Phase + Session |
| 3 | Active LONG state + bars in state |
| 4 | Active SHORT state + bars in state |
| 5 | Score (শ্রেণী অনুযায়ী ভাঙা) |
| 6 | DOL target + দূরত্ব (ATR-এ) |
| 7 | Object count: zones / lines / boxes / labels |

**Definition of Done:**

- [ ] Dashboard toggle করা যায়, তিনটা position-এ বসানো যায়
- [ ] Density mode তিনটাই কাজ করে
- [ ] Dark ও light theme দুটোতেই পড়া যায়
- [ ] Row 7 (object count) দেখে বোঝা যায় limit-এর কতটা কাছে

---

## Phase 33 — Performance / Object Budget

**Business Logic:** TradingView-তে box/line/label-এর কঠিন সীমা আছে। সীমায় পৌঁছালে পুরনো object নিঃশব্দে মুছে যায় — indicator ভুল দেখাতে শুরু করে, কোনো error ছাড়াই।

**Object budget (মোট 500 box, 500 line, 500 label):**

| Module | Box | Line | Label |
|---|---:|---:|---:|
| Zones (সব ধরন) | 100 | 0 | 100 |
| Trendlines + channel | 0 | 40 | 20 |
| Liquidity levels | 0 | 60 | 60 |
| Gaps (NWOG/NDOG) | 30 | 30 | 30 |
| Sessions / AMD / SB | 60 | 0 | 20 |
| Signals + SL/TP | 0 | 60 | 60 |
| Structure (BOS/CHoCH/MSS) | 0 | 80 | 80 |
| **মোট** | **190** | **270** | **370** |

**নিয়ম:**

1. কোনো module নিজের budget ছাড়াতে পারবে না — array cap দিয়ে জোর করো
2. ভারী হিসাব (trendline validity, SMT) শুধু `barstate.isconfirmed`-এ
3. `request.security` কল সর্বোচ্চ ৮টা — বেশি হলে compile সময় ও load বাড়ে
4. `max_bars_back` স্পষ্টভাবে set করো যেখানে historical reference গভীরে যায়
5. Loop-এর ভেতরে drawing object তৈরি করবে না — আগে হিসাব, পরে আঁকা

**Definition of Done:**

- [ ] ৫০০০ bar history + সব module on → chart ৫ সেকেন্ডের মধ্যে load হয়
- [ ] কোনো "object limit reached" আচরণ নেই
- [ ] Dashboard row 7 বাস্তব সংখ্যা দেখায়
- [ ] Timeframe দ্রুত বদলালে (১০ বার) crash/freeze নেই

---

## Phase 34 — Extended Integration Tests

Phase 16-এর ১০টা test **অবশ্যই আগে pass করতে হবে** (সব নতুন toggle off অবস্থায়)। তারপর এই ১২টা:

| # | Test | প্রত্যাশিত ফল |
|---|---|---|
| 11 | সব নতুন module off | Phase 16-এর ফলাফল **অক্ষরে অক্ষরে** এক |
| 12 | Trendline on, reload ×3 | প্রতিটা line একই anchor, একই জায়গা |
| 13 | Trendline break, displacement নেই | কোনো trade নেই |
| 14 | TLQ sweep + disp + MSS + POI | ঠিক ১টা signal |
| 15 | SMT symbol খালি | Error নেই, module skip |
| 16 | SMT ভুল symbol | Signal সংখ্যা বদলায় না, শুধু score |
| 17 | Asia range + Judas swing | Range lock, Judas চিহ্নিত, bias set |
| 18 | Trap: ১০ bar বাইরে থেকে ফেরত | Trap **নয়** (limit 5) |
| 19 | Unicorn (BB+FVG overlap) | Confluence score +2, ১টাই zone আঁকা হয় |
| 20 | `sbOnly` on | Window-বাইরের signal বন্ধ, state আটকায় না |
| 21 | সব module on, 5000 bar | Load < 5s, object limit error নেই |
| 22 | Weekend gap + NWOG | Gap আঁকা হয়, swing detection ভাঙে না |

**Sanity check (১৫M chart, এক মাস):**

| অবস্থা | প্রত্যাশিত signal |
|---|---|
| Phase 1–16 only | ১০–৪০ |
| + সব নতুন module (filter হিসেবে) | **৫–২৫** |
| `sbOnly` + score ≥ 11 | ২–৮ |

> সব module on করার পর signal সংখ্যা যদি **বাড়ে**, তাহলে নিশ্চিতভাবে কোনো একটা নতুন module signal emit করছে। সেটা bug — খুঁজে বের করে সরাও।

---

## 3. নতুন Parameter Defaults

| Parameter | Default | Range | প্রভাব |
|---|---|---|---|
| সব নতুন module enable | off | — | v1 আচরণ রক্ষা করতে |
| TL max anchor age | 200 bar | 30–1000 | বেশি = পুরনো line টিকে থাকে |
| TL min bars between anchors | 10 | 5–100 | কম = খাড়া অর্থহীন line |
| TL max lines per side | 4 | 1–10 | বেশি = chart জট |
| TL touch tolerance | 0.25 × ATR | 0.1–0.6 | বেশি = ঢিলা touch গণনা |
| TL break mode | Close | Close / Wick | Wick = ২–৩× বেশি false break |
| CISD max run | 6 | 2–12 | বেশি = বিরল CISD |
| SMT lookback | 20 | 5–60 | — |
| Trap max bars outside | 5 | 1–15 | বেশি = breakout-কেও trap বলবে |
| Turtle Soup lookback | 20 | 10–60 | — |
| Entry reference | CE | Edge / CE / Full | CE = ভালো RR, কম fill |
| NWOG keep last | 3 | 1–10 | — |
| Score threshold v2 | 8 | 5–14 | v1-এ ছিল 7 |
| Std dev multipliers | −2, −2.5, −4 | — | — |

---

## 4. Do NOT List — সম্প্রসারিত

Phase 1–16-এর ১৪টা নিয়ম **সব এখনো প্রযোজ্য**। নতুন ৮টা:

15. ❌ Trendline break দেখে সরাসরি signal — TLQ sweep ধরে state machine-এ পাঠাও
16. ❌ চলমান bar-এর high/low দিয়ে trendline anchor
17. ❌ প্রতি bar-এ প্রতিটা trendline-এ full validity loop চালানো (chart জমে যাবে)
18. ❌ CISD-কে MSS-এর বিকল্প ধরা — CISD আগাম ইঙ্গিত, নিশ্চয়তা নয়
19. ❌ SMT-র জন্য অসম্পর্কিত symbol ব্যবহার
20. ❌ একই জিনিস দুই শ্রেণীতে score গোনা (sweep + trap = ২ পয়েন্ট নয়, ১ পয়েন্ট)
21. ❌ নতুন module default `true` রেখে দেওয়া
22. ❌ Phase 16-এর regression test না চালিয়ে নতুন module merge করা

---

## 5. Final Acceptance Criteria (Phase 17–34)

- [ ] Phase 17–34 সব Definition of Done পূর্ণ
- [ ] Integration Test 11–22 pass
- [ ] Test 11 (সব off → v1-এর সাথে হুবহু মিল) — **এটা pass না হলে বাকি কিছুর মানে নেই**
- [ ] Repaint audit আবার চালানো হয়েছে, নতুন প্রতিটা `request.security` সহ
- [ ] প্রতিটা নতুন module স্বাধীনভাবে toggle, default off
- [ ] Object budget মানা হয়েছে, dashboard-এ যাচাইযোগ্য
- [ ] ৩টা instrument × ৩টা timeframe = ৯টা combination-এ test
- [ ] সব module on করে ৫০০০ bar-এ load < ৫ সেকেন্ড
- [ ] Code-এ প্রতিটা নতুন module `// ═══ PHASE NN — NAME ═══` header দিয়ে চিহ্নিত

---

## 6. Golden Rule (অপরিবর্তিত)

> **Indicator একটা ধারাবাহিকতা detect করবে, বিচ্ছিন্ন ঘটনা নয়।**

নতুন ১৮টা module যোগ হলো — কিন্তু signal-এর পথ এখনো **একটাই**:

```text
Context → Liquidity → Sweep → Displacement → MSS
    → POI → Retracement → RR → Score → ENTRY
```

নতুন সব কিছু এই পথের **কোনো একটা ধাপকে শক্তিশালী করে** — নতুন কোনো পথ তৈরি করে না।

**অস্পষ্ট কিছু পেলে অনুমান করবে না — spec maintainer-কে জিজ্ঞেস করবে।**

---

**Document Version:** 1.0
**Build target:** Pine Script v6, TradingView `indicator()`
**Prerequisite:** `03_BUILD_PLAN.md` Phase 1–16 complete
