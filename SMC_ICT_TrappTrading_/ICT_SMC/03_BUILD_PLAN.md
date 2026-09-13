# SMC + ICT Indicator — Build Plan (Developer Execution Guide)

**Version:** 1.1
**Audience:** Pine Script developer (trading knowledge লাগবে না)
**Source specs:** `SMC_ICT_TradingView_Developer_Specification.md`, `02_improve_smc_ict.md`
**Follow-up:** `04_ADVANCED_BUILD_PLAN.md` (Phase 17–34 — trendline, CISD, SMT, AMD, trap, MMBM …)
**Output:** একটি TradingView `indicator()` — Pine Script v6

---

## 0. এই ডকুমেন্ট কীভাবে ব্যবহার করবে

আগের দুইটা ডকুমেন্ট বলে **কী** বানাতে হবে। এই ডকুমেন্ট বলে **কোন order-এ বানাবে, প্রতিটা step-এ কী deliver করবে, আর কীভাবে প্রমাণ করবে step-টা কাজ করছে।**

প্রতিটা Phase-এর ৪টা অংশ:

| অংশ | মানে |
|---|---|
| **Business Logic** | ব্যবসায়িক কারণ — কেন এই code লিখছ (trader-এর মাথায় কী চলছে) |
| **Build** | কী code লিখবে |
| **Definition of Done** | কোন শর্তে phase শেষ |
| **Proof** | কী test চালিয়ে দেখাবে যে কাজ করেছে |

> **নিয়ম:** Phase N-এর Proof pass না করে Phase N+1-এ যাবে না। এক phase = এক commit।

---

## 1. এক প্যারায় Business Logic (পুরো indicator-এর সারমর্ম)

বড় institution (bank, fund) একসাথে হাজার lot কিনতে পারে না — কেউ বিক্রি না করলে কেনা যায় না। তাই তারা আগে দাম এমন জায়গায় ঠেলে দেয় যেখানে সাধারণ retail trader-দের stop-loss জমা আছে (swing high-এর উপরে / swing low-এর নিচে)। ওই stop-গুলো trigger হলে বাধ্যতামূলক order আসে — সেটাই institution-এর counterparty। Stop খাওয়ার পর দাম উল্টো দিকে জোরে ছোটে।

**Indicator-এর একমাত্র কাজ:** এই পুরো ঘটনাক্রমটা ধারাবাহিকভাবে detect করা —

```text
HTF Bias → Liquidity কোথায় → দাম সেখানে গেল → Sweep (stop খেল)
   → Displacement (জোরে উল্টো move) → MSS (structure ভাঙল)
   → FVG/OB তৈরি হলো → দাম ফিরে এল (retrace) → RR ঠিক আছে → ENTRY
```

**❌ ভুল mental model:** "FVG দেখলাম → BUY"
**✅ ঠিক mental model:** "উপরের ৯টা ঘটনা পরপর ঘটেছে → তবেই BUY"

Target output: **দিনে ০–২টা signal**। বেশি signal মানে logic ভুল, ভালো indicator নয়।

---

## 2. Architecture — একবারে বুঝে নাও

তিনটা স্তর। নিচের স্তর ভাঙা থাকলে উপরের স্তর কখনো ঠিক হবে না।

```text
┌─────────────────────────────────────────────┐
│  LAYER 3 — DECISION                         │
│  Setup State Machine, Score, RR, SL/TP,     │
│  Signal emit, Alerts                        │
├─────────────────────────────────────────────┤
│  LAYER 2 — EVENTS (ঘটনা)                    │
│  BOS, CHoCH, MSS, Sweep, Displacement,      │
│  FVG, OB, Breaker, IFVG                     │
├─────────────────────────────────────────────┤
│  LAYER 1 — FACTS (কাঁচা তথ্য)               │
│  Confirmed Swings, HH/HL/LH/LL, Liquidity   │
│  levels, ATR, Session, HTF bias, Range      │
└─────────────────────────────────────────────┘
```

**Layer 1 = pure observation** — কোনো signal নেই, শুধু বাজারের সত্য তথ্য।
**Layer 2 = ঘটনা detect** — Layer 1-এর তথ্যের উপর ভিত্তি করে ঘটনা চিহ্নিত করা। এখানেও কোনো buy/sell নেই।
**Layer 3 = সিদ্ধান্ত** — শুধু এখানেই signal তৈরি হয়। Layer 2-এর কোনো ঘটনা একা কখনো signal দেবে না।

> **Developer-এর সবচেয়ে common ভুল:** Layer 2-এর কোনো একটা ঘটনা (যেমন FVG বা BOS) সরাসরি signal বানিয়ে ফেলা। এটাই প্রায় সব বাজে SMC indicator-এর মূল সমস্যা।

---

## 3. Data Model — সবার আগে এটা লিখবে

State ছাড়া duplicate signal আর repaint কখনো ঠেকানো যাবে না।

```pinescript
//@version=6
indicator("SMC + ICT Engine", overlay = true, max_boxes_count = 500,
          max_lines_count = 500, max_labels_count = 500)

// ── LAYER 1 ─────────────────────────────────────────
type Swing
    int    barIndex
    float  price
    bool   isHigh
    string label          // "HH" | "HL" | "LH" | "LL"
    bool   swept          // liquidity হিসেবে খাওয়া হয়ে গেছে?

type LiqLevel
    string kind           // "BSL" | "SSL" | "EQH" | "EQL" | "PDH" | "PDL" | "PWH" | "PWL"
    float  price
    int    createdBar
    bool   swept
    int    sweptBar

// ── LAYER 2 ─────────────────────────────────────────
type Zone
    string id             // "FVG_1234" — unique, কখনো reuse নয়
    string kind           // "FVG" | "OB" | "BB" | "IFVG"
    string direction      // "BULL" | "BEAR"
    float  top
    float  bottom
    int    createdBar
    string state          // NEW | ACTIVE | TOUCHED | MITIGATED | FILLED | INVALID
    bool   consumed       // এই zone থেকে signal দেওয়া হয়ে গেছে?
    int    touchCount
    float  mitigationPct
    box    drawing        // chart object handle

// ── LAYER 3 ─────────────────────────────────────────
type Setup
    string id
    string direction      // "LONG" | "SHORT"
    string state          // দেখো Phase 11-এর state machine
    float  sweepLevel
    int    sweepBar
    float  mssLevel
    int    mssBar
    Zone   poi
    float  entryPrice
    float  slPrice
    float  tpPrice
    float  rr
    int    score
    int    expireBar
    bool   signalEmitted
```

**Global state:**

```pinescript
var array<Swing>    swings      = array.new<Swing>()
var array<LiqLevel> liquidity   = array.new<LiqLevel>()
var array<Zone>     zones       = array.new<Zone>()
var Setup           activeLong  = na
var Setup           activeShort = na
```

**নিয়ম:**

1. প্রতিটা object-এর unique `id` থাকবে — `kind + "_" + str.tostring(bar_index)`
2. Array কখনো unbounded বাড়তে দেবে না — প্রতি bar-এ `INVALID`/`FILLED` object cleanup করবে (cap: 100 zones, 50 liq levels)
3. প্রতিটা state change **শুধু** `barstate.isconfirmed`-এ ঘটবে (intrabar mode আলাদা input দিয়ে explicitly enable করা ছাড়া)

---

## 4. Phase Roadmap — এই order বাধ্যতামূলক

| Phase | Module | Layer | নির্ভরশীলতা | আনুমানিক |
|---:|---|---|---|---|
| 1 | Swing + HH/HL/LH/LL | 1 | — | 1 দিন |
| 2 | Liquidity mapping | 1 | P1 | 1 দিন |
| 3 | BOS / CHoCH | 2 | P1 | 1 দিন |
| 4 | Displacement | 2 | — | 0.5 দিন |
| 5 | Sweep + MSS | 2 | P2, P4 | 1 দিন |
| 6 | FVG + lifecycle | 2 | P4 | 1 দিন |
| 7 | OB / Breaker / IFVG | 2 | P6 | 1.5 দিন |
| 8 | Premium/Discount + OTE | 1 | P1 | 0.5 দিন |
| 9 | HTF context | 1 | P1, P3 | 1 দিন |
| 10 | Session / Kill Zone | 1 | — | 0.5 দিন |
| 11 | **Entry State Machine** | 3 | সব | 2 দিন |
| 12 | Score + SL/TP + RR | 3 | P11 | 1 দিন |
| 13 | Visuals + Settings panel | — | সব | 1 দিন |
| 14 | Alerts | 3 | P11 | 0.5 দিন |
| 15 | Repaint / Lookahead audit | — | সব | 1 দিন |
| 16 | Integration testing | — | সব | 1 দিন |

**মোট: ~15 কর্মদিবস।** Phase 11 সবচেয়ে গুরুত্বপূর্ণ — সেখানে তাড়াহুড়ো করবে না।

### 4.1 এই ডকুমেন্টের সীমা (Scope Boundary)

Spec-এ আছে কিন্তু **এই ১৬টা phase-এ ইচ্ছাকৃতভাবে নেই** — কারণ এগুলো ছাড়াও indicator সম্পূর্ণ কাজ করে, আর আগে core-টা দাঁড় না করালে এগুলো শুধু জটিলতা বাড়াবে:

| বিষয় | কোথায় আছে |
|---|---|
| Dynamic Trendline + Trendline Liquidity | `04_ADVANCED_BUILD_PLAN.md` Phase 17–18 |
| CISD (§23) | 04 — Phase 19 |
| SMT Divergence (§24) | 04 — Phase 20 |
| AMD / Power of 3 / Judas Swing (§25) | 04 — Phase 21 |
| Trap Trading / Turtle Soup (§30) | 04 — Phase 22 |
| Supply & Demand, Mitigation Block, Rejection Block (§20, §29) | 04 — Phase 23 |
| BPR, Liquidity Void, Consequent Encroachment | 04 — Phase 24 |
| NWOG / NDOG / Opening Range Gap | 04 — Phase 25 |
| IRL / ERL, Draw on Liquidity | 04 — Phase 26 |
| Silver Bullet / Macro window | 04 — Phase 27 |
| MMBM / MMSM / Unicorn | 04 — Phase 28 |

> Phase 12-এর score table-এ `SMT +1` আর `Trap +1` লেখা আছে কিন্তু এই ডকুমেন্টে তাদের logic নেই। **v1-এ এই দুইটা সবসময় 0 ধরো** — কোনো fake implementation বসাবে না। Phase 20 ও 22 শেষ হলে তারা নিজেরাই যুক্ত হবে।

---

## Phase 1 — Swing Structure

**Business Logic:**
Swing high/low হলো বাজারের মানচিত্র। Trader প্রথমে তাকায় — দাম আগের চূড়া ভেঙেছে নাকি আগের তলা ভেঙেছে? এটা ছাড়া "trend কী" প্রশ্নের উত্তর নেই। আরও গুরুত্বপূর্ণ — retail trader-রা ঠিক এই swing point-গুলোর বাইরে stop-loss বসায়, তাই swing = পরের phase-এ liquidity-র ঠিকানা।

**Build:**

```pinescript
swingLen = input.int(5, "Swing Length", minval = 3, maxval = 20, group = "Structure")

var float lastSwingHigh = na
var float lastSwingLow  = na

// pivot len bar পরে confirm হয় — এটাই non-repaint-এর চাবি
ph = ta.pivothigh(high, swingLen, swingLen)
pl = ta.pivotlow(low,  swingLen, swingLen)

if not na(ph)
    price = high[swingLen]
    bar   = bar_index - swingLen
    lbl   = na(lastSwingHigh) ? "HH" : (price > lastSwingHigh ? "HH" : "LH")
    array.push(swings, Swing.new(bar, price, true, lbl, false))
    lastSwingHigh := price

if not na(pl)
    price = low[swingLen]
    bar   = bar_index - swingLen
    lbl   = na(lastSwingLow) ? "LL" : (price < lastSwingLow ? "LL" : "HL")
    array.push(swings, Swing.new(bar, price, false, lbl, false))
    lastSwingLow := price

// array cap — memory leak ঠেকাও
if array.size(swings) > 100
    array.shift(swings)
```

**Definition of Done:**

- [ ] Swing শুধু `swingLen` bar পরে appear করে, pivot bar-এ নয়
- [ ] HH/HL/LH/LL label আগের swing-এর সাথে তুলনা করে দেওয়া হয়
- [ ] চলমান (unclosed) candle কখনো swing হয় না
- [ ] Array cap আছে, memory leak নেই

**Proof:**

1. Chart reload (F5) → পুরনো সব swing হুবহু একই জায়গায় আছে
2. শেষ `swingLen` bar-এ কোনো swing label নেই — এটা সঠিক আচরণ, bug নয়
3. Weekend gap-ওয়ালা chart (Forex রবিবার open) → swing detection ভাঙেনি

> ⚠️ এখানে repaint থাকলে পুরো indicator মিথ্যা। Phase 2-এ যাওয়ার আগে reload test অবশ্যই pass করাতে হবে।

---

## Phase 2 — Liquidity Mapping

**Business Logic:**
Retail trader swing low-এর ঠিক নিচে stop বসায় (long trade-এ) আর swing high-এর ঠিক উপরে (short trade-এ)। একই জায়গায় হাজার জনের stop জমে — ওটাই institution-এর জন্য "টাকার পুকুর"। দুটো high প্রায় সমান হলে (EQH) সেটা আরও বড় পুকুর, কারণ trader-রা ভাবে "double top, এখানে resistance" — সবাই একই জায়গায় stop দেয়। PDH/PDL/PWH/PWL একই কারণে গুরুত্বপূর্ণ — সবাই ওই level দেখে।

**Build:**

- প্রতিটা confirmed swing high → `BSL` level, swing low → `SSL` level
- EQH/EQL: `math.abs(h1 - h2) < atr * eqTolerance` (default 0.1) — **চলমান bar-এর high বাদ দেবে**
- PDH/PDL/PWH/PWL: `request.security` দিয়ে, নিচের non-repaint নিয়ম মেনে

```pinescript
pdh = request.security(syminfo.tickerid, "D", high[1],
                       lookahead = barmerge.lookahead_off)
```

**Definition of Done:**

- [ ] সব liquidity type detect হচ্ছে এবং chart-এ আঁকা হচ্ছে
- [ ] EQ tolerance ATR-normalized, hard-coded pip নয় (নাহলে XAUUSD আর EURUSD-এ একই code কাজ করবে না)
- [ ] Level sweep হলে `swept = true` set হয়, level ধূসর/মুছে যায়
- [ ] প্রতিটা type আলাদাভাবে toggle করা যায়

**Proof:**

1. Daily high line আজকের চলমান দিনের সাথে সাথে নড়ছে না
2. EQH শুধু তখনই আঁকা হয় যখন দুই high চোখেও প্রায় সমান দেখায়
3. Sweep-এর পর level auto-invalidate হয়

---

## Phase 3 — BOS / CHoCH

**Business Logic:**
**BOS (Break of Structure)** = trend একই দিকে চলছে। দাম আগের চূড়া ভেঙে উপরে গেল মানে ক্রেতারাই নিয়ন্ত্রণে — trend continuation। এটা entry নয়, শুধু "trend কোনদিকে" তার নিশ্চয়তা।

**CHoCH (Change of Character)** = প্রথম সতর্কবার্তা। উপরে উঠতে থাকা বাজার প্রথমবার আগের তলা ভাঙল — মানে হয়তো নিয়ন্ত্রণ হাতবদল হচ্ছে। কিন্তু "হয়তো" মানে trade নয়। CHoCH এককভাবে trade করলে প্রচুর লোকসান — কারণ trend-এর মাঝে ছোট pullback-ও CHoCH দেখায়।

**Build:**

```pinescript
bosMode = input.string("Close", "Break Mode", options = ["Close", "Wick"],
                       group = "Structure")
brokeUp = bosMode == "Close" ? close > lastSwingHigh : high > lastSwingHigh
```

- Trend direction `var` তে রাখো: `"BULL" | "BEAR" | "NEUTRAL"`
- Break trend-এর দিকে হলে → **BOS**; বিপরীত দিকে হলে → **CHoCH** + trend flip

**Definition of Done:**

- [ ] Close mode default
- [ ] BOS আর CHoCH আলাদা label, আলাদা রঙ
- [ ] CHoCH কোথাও signal emit করে না — শুধু `state := "CHOCH_WARNING"`
- [ ] একই swing level থেকে বারবার BOS আঁকে না (level consumed হয়ে যায়)

**Proof:**

- Wick level ছুঁয়ে candle ভেতরে close করল → Close mode-এ **কোনো BOS নেই** (Test 3)
- Wick mode-এ toggle করলে ওই একই জায়গায় BOS আসে

---

## Phase 4 — Displacement

**Business Logic:**
Institution যখন সত্যিই ঢোকে, দাম আস্তে আস্তে নড়ে না — একটা বড় জোরালো candle আসে, প্রায় পুরোটাই body। এটাই "আগ্রাসন"-এর স্বাক্ষর। বড় range কিন্তু ছোট body (লম্বা দুই দিকের wick) মানে উল্টোটা — দ্বিধা, লড়াই, কেউ জেতেনি। তাই শুধু "বড় candle" দেখে displacement বলা যাবে না; body-র অনুপাত দেখতে হবে।

**Build:**

```pinescript
atrLen       = input.int(14,    "ATR Length",     group = "Displacement")
atrMult      = input.float(1.2, "ATR Multiplier", minval = 0.8, maxval = 3.0)
bodyRatioMin = input.float(0.6, "Min Body Ratio", minval = 0.4, maxval = 0.9)

atrVal    = ta.atr(atrLen)
bodySize  = math.abs(close - open)
rangeSize = math.max(high - low, syminfo.mintick)
bodyRatio = bodySize / rangeSize

isDisp     = bodyRatio >= bodyRatioMin and bodySize >= atrVal * atrMult
isBullDisp = isDisp and close > open
isBearDisp = isDisp and close < open
```

**Definition of Done:**

- [ ] দুটো শর্তই লাগে — ATR size **এবং** body ratio
- [ ] Direction আলাদা করা আছে
- [ ] দুটো threshold-ই input

**Proof:**

- বড় doji / লম্বা wick candle → displacement **নয়**
- সাধারণ chart-এ ১০০ bar-এ ~২–৫টা displacement। ২০+ হলে threshold অনেক ঢিলা।

---

## Phase 5 — Sweep + MSS (সবচেয়ে গুরুত্বপূর্ণ Layer 2 module)

**Business Logic:**
**Sweep** = দাম liquidity level ভেদ করে ঢুকল, stop গুলো খেল, তারপর **আবার level-এর ভেতরে ফিরে close করল**। ফিরে আসাটাই মূল কথা — এটা প্রমাণ করে ভাঙাটা আসল ছিল না, উদ্দেশ্য ছিল শুধু stop সংগ্রহ। যদি level-এর বাইরেই close করে, সেটা sweep নয়, সেটা genuine breakout — সম্পূর্ণ আলাদা ঘটনা, উল্টো trade হবে।

**MSS (Market Structure Shift)** = পূর্ণাঙ্গ reversal-এর প্রমাণ। তিনটা ঘটনা **এই ক্রমে**:

1. Stop সংগ্রহ হলো (sweep) — institution-এর জ্বালানি ভরা শেষ
2. জোরে উল্টো move (displacement) — institution এখন ঠেলছে
3. Structure ভাঙল — নতুন দিক নিশ্চিত

তিনটার যেকোনো একটা missing মানে setup নেই। এই তিনটার ক্রম-ই SMC আর সাধারণ "support/resistance bounce" indicator-এর মধ্যে পার্থক্য।

**Build:**

```pinescript
// Bullish sweep — তিনটাই লাগবে
penetrated = low   < sslLevel
closedBack = close > sslLevel
rejection  = (close - low) / rangeSize > 0.5   // নিচে লম্বা wick

sslSwept = penetrated and closedBack and rejection
```

- Sweep হলে → `LiqLevel.swept := true`, `Setup.sweepLevel/sweepBar` রেকর্ড
- MSS check শুধুমাত্র sweep-এর **পরের** bar থেকে শুরু (একই bar-এ sweep+MSS reject — Edge Case #2)
- MSS = displacement + `close > lastInternalHigh` (bullish)

**Definition of Done:**

- [ ] শুধু wick দিয়ে sweep হয় না, close-back বাধ্যতামূলক
- [ ] একই level দ্বিতীয়বার sweep করলে ignore (Edge Case #10)
- [ ] Sweep-এর পর `mssTimeout` (default 10 bar) এর মধ্যে MSS না এলে setup invalid
- [ ] MSS-এর তিনটা উপাদান আলাদাভাবে log/debug করা যায়

**Proof:**

- Sweep হয়েছে কিন্তু displacement আসেনি → **কোনো MSS নেই** (Test 4)
- Level-এর বাইরে close হয়েছে → sweep নয়, breakout
- একই bar-এ sweep+break → reject

---

## Phase 6 — FVG + Lifecycle

**Business Logic:**
দাম এত দ্রুত নড়লে মাঝখানে এমন একটা দামের জায়গা তৈরি হয় যেখানে কেনাবেচা ঠিকমতো হয়নি — বাজার ওই জায়গাটা "এড়িয়ে" গেছে। ৩টা candle-এর মধ্যে ১ম আর ৩য় candle overlap না করলে সেই ফাঁকাই FVG। বাজার সাধারণত পরে ফিরে এসে ওই ফাঁকা পূরণ করে — তাই ওটা entry-র জন্য ভালো জায়গা।

**Lifecycle কেন দরকার:** একটা FVG-তে দাম প্রথমবার এলে reaction ভালো হয়। পঞ্চমবার এলে ওখানকার order অনেক আগেই শেষ — আর কাজ করে না। তাই প্রতিটা zone-এর "কতবার ছোঁয়া হয়েছে" track রাখতে হবে, আর **এক zone থেকে একটাই signal**।

**Build:**

```pinescript
bullFVG = low > high[2] and isBullDisp[1]   // মাঝের candle displacement হতে হবে
if bullFVG and (low - high[2]) >= atrVal * minGapMult
    array.push(zones, Zone.new(
        id = "FVG_" + str.tostring(bar_index), kind = "FVG",
        direction = "BULL", top = low, bottom = high[2],
        createdBar = bar_index, state = "NEW", consumed = false))
```

**Lifecycle state machine (প্রতি bar-এ প্রতিটা zone-এর উপর চালাও):**

```text
NEW ──(পরের bar)──> ACTIVE ──(দাম ঢুকল)──> TOUCHED
 └─> MITIGATED (50% পূর্ণ) ──> FILLED (100%) ──> INVALID
```

**Definition of Done:**

- [ ] FVG formula সঠিক, উভয় দিকে
- [ ] Min gap size ATR-normalized
- [ ] Quality filter: মাঝের candle displacement হতে হবে
- [ ] 50% mitigation track হয়
- [ ] Box প্রতি bar-এ নতুন করে আঁকা হয় না — `box.set_right()` দিয়ে extend হয়
- [ ] Nested FVG-তে শুধু বাইরেরটা রাখা হয় (Edge Case #3)

**Proof:**

- একই FVG-তে দাম ৫ বার এল → `touchCount = 5`, কিন্তু signal ১টাই (Test 6)
- FVG সম্পূর্ণ পূরণ হলে box মুছে যায়/ধূসর হয়
- 500 box limit-এ chart hang করে না

---

## Phase 7 — OB / Breaker / IFVG

**Business Logic:**
**Order Block** = জোরালো move শুরু হওয়ার ঠিক আগের বিপরীত candle। Institution ওখানেই তাদের বড় order রেখেছিল — তাই দাম ফিরে এলে বাকি order-গুলো আবার activate হয়। কিন্তু **প্রতিটা বিপরীত candle OB নয়** — শুধু সেটাই যেটার পরে সত্যিকারের displacement এসেছে এবং structure ভেঙেছে।

**Breaker** = OB ব্যর্থ হলো। দাম OB ভেদ করে উল্টো দিকে চলে গেল — মানে ওখানে যারা কিনেছিল তারা এখন আটকা। দাম ফিরে এলে তারা break-even-এ বেরিয়ে যেতে চাইবে → ওই জায়গা এখন উল্টো ভূমিকা পালন করে।

**IFVG** = একই ধারণা, FVG-র জন্য। Support হিসেবে কাজ করার কথা ছিল, ভেঙে গেল, এখন resistance।

**Build:**

- Bullish OB: displacement candle-এর আগের শেষ bearish candle
- Validation (তিনটাই): পরের candle displacement + structure break + (preferred) FVG তৈরি
- OB `INVALID` হলে → সাথে সাথে নতুন Zone তৈরি `kind = "BB"`, direction উল্টো
- FVG `INVALID` হলে → নতুন Zone `kind = "IFVG"`, direction উল্টো

**Definition of Done:**

- [ ] OB, BB, IFVG — তিনটার আলাদা label ও রঙ (কখনো একই নামে নয়)
- [ ] Validation ছাড়া OB তৈরি হয় না
- [ ] "Fresh OB only" toggle আছে
- [ ] FVG + OB overlap হলে FVG-কে priority (Edge Case #4)

**Proof:**

- প্রতিটা bearish candle OB হিসেবে আঁকা হচ্ছে না
- OB ভাঙার পর সেটা BB হয়ে যায়, আগের OB box রয়ে যায় না

---

## Phase 8 — Premium / Discount / OTE

**Business Logic:**
দোকানদারের নীতি — সস্তায় কেনো, দামে বেচো। Institution range-এর নিচের অর্ধেকে (discount) কেনে, উপরের অর্ধেকে (premium) বেচে। তাই range-এর উপরের অর্ধেকে long নেওয়া মানে ইতিমধ্যেই দামি জায়গায় কেনা — খারাপ RR। OTE (Fib 61.8%–78.6%) হলো discount-এর মধ্যেও সবচেয়ে মিষ্টি অংশ।

**এটা context, trigger নয়** — "discount-এ আছে" দেখে কখনো buy নয়।

**Build:**

- Dealing range = সাম্প্রতিক confirmed swing high ও low
- EQ = 50%; `inDiscount = close < eq`, `inPremium = close > eq`
- OTE: sweep low থেকে MSS high পর্যন্ত fib, 0.618–0.786 zone আঁকো

**Definition of Done:**

- [ ] Range নির্বাচনের নিয়ম স্পষ্ট ও documented
- [ ] Premium/Discount শুধু score-এ +1 দেয়, signal দেয় না
- [ ] Structure পাল্টালে range নতুন করে হিসাব হয়

---

## Phase 9 — HTF Context

**Business Logic:**
১৫ মিনিটের chart-এ যা reversal মনে হয়, ৪ ঘণ্টার chart-এ সেটা হয়তো downtrend-এর ছোট্ট bounce মাত্র। বড় timeframe-এর স্রোতের বিরুদ্ধে trade করলে জেতার হার নাটকীয়ভাবে কমে। তাই আগে বড় ছবি দেখো, তারপর ছোট timeframe-এ ঢোকার জায়গা খোঁজো।

**Build — Repaint-এর একমাত্র সবচেয়ে বিপজ্জনক জায়গা:**

```pinescript
// ❌ ভুল — চলমান HTF candle, ভবিষ্যৎ ফাঁস করে
htfHigh = request.security(syminfo.tickerid, htfTF, high)

// ✅ ঠিক — শুধু বন্ধ হয়ে যাওয়া HTF candle
htfHigh = request.security(syminfo.tickerid, htfTF, high[1],
                           lookahead = barmerge.lookahead_off)
```

- HTF bias = HTF-এর BOS/CHoCH থেকে, বা HTF structure থেকে
- HTF auto-map preset: 1M→15M, 5M→1H, 15M→4H, 30M→4H, 1H→D (user override করতে পারবে)

**Definition of Done:**

- [ ] প্রতিটা `request.security` কল-এ `[1]` offset + `lookahead_off`
- [ ] HTF auto-map আছে কিন্তু hard-coded নয়
- [ ] HTF bias chart-এ দেখা যায় (label/table)

**Proof:**

1. Realtime-এ signal এল → chart reload → signal ঠিক একই জায়গায় (Test 7)
2. HTF timeframe বদলে আবার আগেরটায় ফিরে এলে history অপরিবর্তিত

---

## Phase 10 — Session / Kill Zone

**Business Logic:**
বাজার সারাদিন একরকম নয়। এশিয়া session শান্ত — দাম জমা হয় (accumulation)। London খোলার সময় প্রথম বড় ধাক্কা — প্রায়ই এশিয়ার high/low sweep করে (manipulation)। New York-এ আসল দিক প্রকাশ পায় (distribution)। তাই sweep + MSS যদি London/NY kill zone-এ ঘটে, সেটা বেশি নির্ভরযোগ্য।

**Build:**

```pinescript
tz   = input.string("America/New_York", "Session Timezone", group = "Sessions")
nyS  = input.session("0930-1600", "New York", group = "Sessions")
inNY = not na(time(timeframe.period, nyS, tz))
```

**Definition of Done:**

- [ ] Timezone input, hard-coded নয় — DST নিজে handle হয়
- [ ] Asia / London / NY / Overlap / Custom KZ — সব আছে
- [ ] Session background shading toggle করা যায়

> ⚠️ Bangladesh local time দিয়ে কখনো session define করবে না। DST-এর কারণে বছরে দুইবার ভুল হবে।

---

## Phase 11 — Entry State Machine ⭐ সবচেয়ে গুরুত্বপূর্ণ Phase

**Business Logic:**
এখানেই "ধারাবাহিকতা" প্রয়োগ হয়। একটা setup একটা যাত্রা — প্রতিটা ধাপ আগের ধাপের উপর নির্ভরশীল, আর প্রতিটা ধাপের একটা মেয়াদ আছে। State machine ছাড়া যা হয়: পুরনো setup নতুন trade trigger করে, একই setup থেকে ৫টা signal আসে, MSS-এর আগেই entry হয়ে যায়।

**Long State Machine:**

```text
IDLE
 │  HTF bullish + দাম discount/POI-তে
 ▼
CONTEXT_FOUND
 │  SSL sweep (close back inside)
 ▼
LIQUIDITY_SWEPT ────⏱ 10 bar timeout────> INVALIDATED
 │  bullish displacement
 ▼
DISPLACEMENT_CONFIRMED
 │  close > internal high
 ▼
MSS_CONFIRMED ──────⏱ 20 bar timeout────> INVALIDATED
 │  FVG বা OB তৈরি হলো
 ▼
POI_CREATED ────────⏱ 50 bar timeout────> INVALIDATED
 │  দাম POI-তে ফিরল
 ▼
RETRACE_WAIT
 │  RR >= 1.5 এবং score >= threshold
 ▼
ENTRY_TRIGGERED ──> signal একবার emit ──> TRADE_ACTIVE
 │
 ▼
TP / SL / INVALIDATED ──> RESET (IDLE)
```

SHORT হুবহু উল্টো।

**Build:**

```pinescript
if not na(activeLong)
    switch activeLong.state
        "IDLE" =>
            if htfBias == "BULL" and inDiscount
                activeLong.state := "CONTEXT_FOUND"
        "CONTEXT_FOUND" =>
            if sslSwept
                activeLong.state      := "LIQUIDITY_SWEPT"
                activeLong.sweepLevel := sweptLevel
                activeLong.sweepBar   := bar_index
        "LIQUIDITY_SWEPT" =>
            if bar_index - activeLong.sweepBar > mssTimeout
                activeLong.state := "INVALIDATED"
            else if isBullDisp
                activeLong.state := "DISPLACEMENT_CONFIRMED"
        // ... বাকি state একইভাবে
```

**বাধ্যতামূলক নিয়ম:**

1. একসাথে **একটাই** active LONG setup আর **একটাই** active SHORT setup
2. একই bar-এ LONG আর SHORT দুটোই trigger হলে → দুটোই reject (Edge Case #11)
3. `ENTRY_TRIGGERED`-এ signal ঠিক একবার emit, তারপর `signalEmitted := true`
4. প্রতিটা transition শুধু `barstate.isconfirmed`-এ
5. প্রতিটা timeout input

**Definition of Done:**

- [ ] সব state implement, সব timeout কাজ করে
- [ ] State machine পেছনে যায় না (POI_CREATED থেকে LIQUIDITY_SWEPT-এ ফেরত নয়)
- [ ] Debug table-এ চলমান state দেখা যায়
- [ ] Reset logic-এ সব field পরিষ্কার হয়

**Proof:**

- Test 1: পুরো bullish ক্রম → ঠিক **১টা** LONG
- Test 6: FVG-তে ৫ বার touch → এখনো **১টা** signal
- Sweep-এর পর ১৫ bar কিছু ঘটল না → setup মুছে গেছে, পরে আর trigger করে না

---

## Phase 12 — Score + SL / TP / RR

**Business Logic:**
সব setup সমান নয়। যত বেশি স্বাধীন কারণ একই দিকে ইঙ্গিত করে, সম্ভাবনা তত ভালো। কিন্তু score দিয়ে দ্বন্দ্ব ঢাকা যাবে না — HTF পরিষ্কার bearish হলে পাঁচটা bullish কারণ যোগ করেও সেটা long হয় না।

**SL** যাবে সেই জায়গার বাইরে যেখানে গেলে পুরো ধারণাটাই মিথ্যা প্রমাণিত হয় — sweep low-এর নিচে। ওখানে দাম গেলে মানে institution ঢোকেনি, আমরা ভুল পড়েছি।

**TP** যাবে পরের liquidity pool-এ — কারণ দাম টাকার দিকেই ছোটে।

**RR filter কেন:** ২৫% trade জিতলেও 1:3 RR-এ লাভ থাকে, কিন্তু 1:0.5 RR-এ ৭০% জিতেও লোকসান। তাই RR না মিললে **trade নেই** — signal জোর করে বানানো নিষেধ।

**Build:**

```pinescript
buffer = atrVal * 0.2
longSL = activeLong.sweepLevel - buffer
longTP = nextLiquidityAbove(close)        // priority অনুযায়ী
rr     = (longTP - entry) / (entry - longSL)

if rr < minRR
    activeLong.state := "INVALIDATED"     // signal নেই
```

TP priority: Internal liquidity → previous swing → EQH/EQL → PDH/PDL → PWH/PWL → external → HTF liquidity

Score: HTF+2, Sweep+2, MSS+2, Displacement+2, FVG+1, OB+1, P/D+1, KillZone+1, SMT+1, Trap+1
**Contradiction penalty −3** (HTF bearish কিন্তু LONG setup)

> **v1 note:** SMT ও Trap-এর logic এই ডকুমেন্টে নেই (দেখো §4.1) — তাই v1-এ দুটোই **সবসময় 0**, সর্বোচ্চ সম্ভব score 12। `04_ADVANCED_BUILD_PLAN.md` Phase 31-এ পুরো score system শ্রেণীভিত্তিক v2-তে যাবে; সেখানে double counting আটকাতে capping যোগ হবে।

| Score | Grade | কর্ম |
|---:|---|---|
| 0–3 | Weak | NO TRADE |
| 4–6 | Moderate | optional |
| 7–9 | Strong | trade |
| 10+ | A+ | trade |

**Definition of Done:**

- [ ] SL/TP/RR সব হিসাব হয় এবং signal label-এ দেখা যায়
- [ ] `rr < minRR` → signal নেই (Test 5)
- [ ] Score chart-এ দেখা যায়, threshold input
- [ ] Contradiction penalty প্রয়োগ হয়

---

## Phase 13 — Visuals + Settings

**Business Logic:**
Trader-কে ২ সেকেন্ডে সিদ্ধান্ত নিতে হয়। Chart-এ ৫০টা box থাকলে সে কিছুই দেখে না — indicator তখন সাহায্যের বদলে বাধা।

**Build:**

- প্রতিটা module-এর নিজস্ব on/off toggle
- Settings group: Structure / Liquidity / FVG / OB / HTF / Sessions / Entry / Risk / Visuals
- Zone auto-hide: `INVALID`/`FILLED` হলে মুছে যাবে
- Optional debug table: HTF bias, current state, score, active zone count

**Definition of Done:**

- [ ] সব module আলাদাভাবে বন্ধ করা যায়
- [ ] সব toggle off করলে chart সম্পূর্ণ পরিষ্কার
- [ ] Object limit-এ পৌঁছালেও error নেই
- [ ] Dark ও light theme দুটোতেই পড়া যায়

---

## Phase 14 — Alerts

```pinescript
if longSignal and not activeLong.signalEmitted
    alert("LONG " + syminfo.ticker + " | E:" + str.tostring(entry) +
          " SL:" + str.tostring(sl) + " TP:" + str.tostring(tp) +
          " RR:" + str.tostring(rr, "#.##") + " Score:" + str.tostring(score),
          alert.freq_once_per_bar_close)
    activeLong.signalEmitted := true
```

**Definition of Done:**

- [ ] Structure / Liquidity / Zone / Trade — চার category-র সব alert আছে
- [ ] প্রতিটা alert setup প্রতি একবার
- [ ] `alert.freq_once_per_bar_close` ব্যবহৃত
- [ ] Alert message-এ entry/SL/TP/RR/score সব আছে

---

## Phase 15 — Repaint & Lookahead Audit (Delivery-র আগে বাধ্যতামূলক)

- [ ] সব `request.security()`-এ `lookahead = barmerge.lookahead_off` **এবং** `[1]` offset
- [ ] কোনো unconfirmed HTF candle ব্যবহৃত হয়নি
- [ ] Pivot N bar পরে confirm, একই bar-এ নয়
- [ ] চলমান bar-এর high/low swing হিসেবে ব্যবহৃত হয়নি
- [ ] `var` state realtime-এ reset হয় না
- [ ] Alert-এ `barstate.isconfirmed` check আছে
- [ ] Zone delete/recreate logic সঠিক

**Test procedure:**

```text
1. Chart reload (F5)           → history হুবহু এক?
2. Realtime signal → bar close → signal টিকে থাকল?
3. HTF বদলে ফেরত আসো           → signal অপরিবর্তিত?
4. Replay mode                 → একই signal একই জায়গায়?
```

---

## Phase 16 — Integration Tests (Acceptance)

| # | Test | প্রত্যাশিত ফল |
|---|---|---|
| 1 | SSL sweep → disp → MSS → FVG → retrace | ঠিক ১টা LONG |
| 2 | BSL sweep → disp → MSS → FVG → retrace | ঠিক ১টা SHORT |
| 3 | Wick structure ভাঙল, ভেতরে close | Close mode-এ কোনো BOS নেই |
| 4 | Sweep হলো, displacement নেই | কোনো trade নেই |
| 5 | Valid setup কিন্তু RR < 1.5 | কোনো trade নেই |
| 6 | একই FVG-তে ৫ বার touch | ১টা signal |
| 7 | Reload / realtime তুলনা | সম্পূর্ণ consistent |
| 8 | Weekend gap | Swing detection ভাঙে না |
| 9 | একই bar-এ LONG + SHORT | দুটোই reject |
| 10 | ৫০০০ bar history | Chart hang করে না, object limit error নেই |

**Sanity check:** ১৫M chart-এ এক মাসের data → **১০–৪০টা signal** হওয়ার কথা।

- ২০০+ signal → logic অনেক ঢিলা, threshold কড়া করো
- ০ signal → কোনো state transition আটকে আছে, debug table দিয়ে খোঁজো

---

## 5. Parameter Defaults

| Parameter | Default | Range | প্রভাব |
|---|---|---|---|
| Swing length | 5 | 3–20 | বেশি = কম swing, কম noise |
| BOS mode | Close | Close / Wick | Wick = ২–৩× বেশি false signal |
| ATR mult (displacement) | 1.2 | 0.8–2.0 | কম = বেশি setup, কম মান |
| Body ratio | 0.6 | 0.5–0.8 | বেশি = কড়া |
| EQH/EQL tolerance | 0.1 × ATR | 0.05–0.3 × ATR | — |
| Min RR | 1.5 | 1.0–3.0 | বেশি = কম trade |
| MSS timeout | 10 bar | 5–30 | — |
| Retrace timeout | 20 bar | 10–50 | — |
| POI expire | 50 bar | 20–200 | — |
| Score threshold | 7 | 5–12 | — |
| FVG min size | 0.3 × ATR | 0.1–1.0 × ATR | — |

---

## 6. Do NOT List (প্রতিদিন পড়বে)

1. ❌ সব concept অন্ধভাবে একসাথে মেশানো
2. ❌ BOS আছে বলেই signal
3. ❌ FVG আছে বলেই signal
4. ❌ প্রতিটা বিপরীত candle-কে OB বলা
5. ❌ Level-এর বাইরে প্রতিটা wick-কে sweep বলা
6. ❌ ভবিষ্যতের data ব্যবহার
7. ❌ Unconfirmed pivot-কে structure ধরা
8. ❌ একই setup থেকে duplicate signal
9. ❌ Invalid zone chart-এ রেখে দেওয়া
10. ❌ RR কম হলেও trade জোর করে বানানো
11. ❌ Repainting HTF logic
12. ❌ চাওয়া ছাড়া EMA/RSI/MACD confluence যোগ করা
13. ❌ History সুন্দর দেখানোর জন্য over-optimize
14. ❌ বলা ছাড়া `strategy()` বানিয়ে ফেলা

---

## 7. Final Acceptance Criteria

- [ ] Phase 1–16 সব Definition of Done পূর্ণ
- [ ] Integration Test 1–10 pass
- [ ] Repaint audit pass (চারটা procedure-ই)
- [ ] প্রতিটা module স্বাধীনভাবে toggle করা যায়
- [ ] Alert setup প্রতি একবার fire করে
- [ ] Chart পরিষ্কার ও পড়ার যোগ্য
- [ ] ৩টা ভিন্ন instrument-এ test (Forex major, Gold, Index)
- [ ] ৩টা ভিন্ন timeframe-এ test (5M, 15M, 1H)
- [ ] কোনো অপ্রয়োজনীয় indicator যোগ করা হয়নি
- [ ] Code-এ প্রতিটা module comment-এ চিহ্নিত

---

## 8. Golden Rule

> **Indicator একটা ধারাবাহিকতা detect করবে, বিচ্ছিন্ন ঘটনা নয়।**

```text
❌  FVG → BUY
❌  BOS → BUY
❌  RSI oversold → BUY

✅  HTF Context → Liquidity → Sweep → Displacement → MSS
       → POI → Retracement → RR Validation → ENTRY
```

**অস্পষ্ট কিছু পেলে অনুমান করবে না — spec maintainer-কে জিজ্ঞেস করবে।**

---

**Document Version:** 1.1
**Build target:** Pine Script v6, TradingView `indicator()`
**পরের ধাপ:** Phase 1–16 pass হলে → `04_ADVANCED_BUILD_PLAN.md` (Phase 17–34)
