# SMC + ICT Indicator — MASTER Build Plan (একটাই ফাইল, Phase 1–48)

**Version:** 2.0 — `03_BUILD_PLAN.md` (v1.1) + `04_ADVANCED_BUILD_PLAN.md` (v1.0) একসাথে, **এবং যা দুইটাতেই ছিল না সেগুলোও**
**Audience:** Pine Script developer। **Trading জানার দরকার নেই** — প্রতিটা module-এর সাথে এক লাইনের গল্প দেওয়া আছে, ওইটুকুই যথেষ্ট।
**Output:** একটা TradingView `indicator()` — Pine Script v6
**এই ফাইলটাই একমাত্র সত্য।** 03 আর 04 এখন থেকে শুধু ইতিহাস; নতুন কাজ এখান থেকেই হবে।

---

## 0. কীভাবে পড়বে

প্রতিটা Phase-এর ছয়টা অংশ — সবসময় একই ক্রমে:

| অংশ | কী পাবে |
|---|---|
| 📖 **গল্প** | এক-দুই লাইনে বাস্তব জীবনের উপমা। এটুকু বুঝলেই code লেখা যাবে |
| 👁 **চার্টে যা দেখবে** | চোখে কেমন দেখায় |
| ⚙️ **Build** | কী code লিখবে |
| ✅ **Done কখন** | কোন শর্তে phase শেষ |
| 🧪 **Proof** | কী চালিয়ে প্রমাণ করবে |
| 🚫 **একা signal?** | এই module একা trade দেয় কি না (উত্তর প্রায় সবসময় **না**) |

**তিনটা কঠিন নিয়ম:**

1. Phase N-এর Proof pass না করে Phase N+1-এ যাবে না। এক phase = এক commit।
2. Phase 17 থেকে যত module, সবার `input.bool(...)` toggle **default `false`**।
3. কোনো module নিজে signal দেয় না। Signal শুধু **Phase 11-এর state machine** থেকে বের হয় — এক জায়গা, এক দরজা।

---

## 1. পুরো জিনিসটা এক গল্পে

একটা বিশাল পাইকারি ক্রেতা (bank/fund) ১০,০০০ বস্তা চাল কিনবে। বাজারে এক সাথে অত বিক্রেতা নেই। সে যদি হুট করে কিনতে যায়, দাম আকাশে উঠে যাবে — নিজের কেনার খরচ নিজেই বাড়িয়ে ফেলবে।

তাই সে উল্টো কাজ করে: **আগে দাম নামিয়ে আতঙ্ক তৈরি করে।** ছোট ব্যবসায়ীরা ভয় পেয়ে বিক্রি করে দেয় (তাদের stop-loss ঠিক ওইখানেই বসানো ছিল)। ওই বাধ্যতামূলক বিক্রির পুরোটা পাইকার চুপচাপ কিনে নেয়। কেনা শেষ — তারপর দাম হুড়মুড়িয়ে উপরে।

**Indicator-এর একমাত্র কাজ এই নাটকটা ধারাবাহিকভাবে ধরা:**

```text
① বড় ছবি কোনদিকে      (HTF Bias)
② টাকা কোথায় জমা       (Liquidity — stop-এর পুকুর)
③ দাম সেখানে গেল       (Raid)
④ Stop খেয়ে ফিরে এল    (Sweep)  ← সবচেয়ে গুরুত্বপূর্ণ
⑤ জোরে উল্টো ছুটল      (Displacement)
⑥ Structure ভাঙল       (MSS)
⑦ পিছনে ফাঁকা রেখে গেল (FVG / OB = POI)
⑧ দাম ফাঁকা পূরণ করতে ফিরল (Retrace)
⑨ লাভ/ক্ষতির অনুপাত ঠিক (RR)
──────────────────────► ENTRY
```

**❌ ভুল মাথা:** "FVG দেখলাম → BUY"
**✅ ঠিক মাথা:** "উপরের ৯টা ঘটনা **পরপর** ঘটেছে → তবেই BUY"

**লক্ষ্য: দিনে ০–২টা signal।** বেশি signal = logic ঢিলা, ভালো indicator নয়।

---

## 2. শব্দকোষ — এটুকুই জানলে চলবে

| শব্দ | সহজ মানে |
|---|---|
| **Swing High/Low** | চার্টের চূড়া / তলা |
| **Liquidity** | যেখানে হাজার জনের stop জমা — "টাকার পুকুর" |
| **BSL / SSL** | উপরের পুকুর / নিচের পুকুর |
| **EQH / EQL** | দুইটা প্রায় সমান চূড়া / তলা — আরও বড় পুকুর |
| **Sweep** | পুকুরে ঢুকে stop খেয়ে **ফিরে আসা** |
| **Displacement** | বড়, প্রায় পুরো-body candle — আগ্রাসন |
| **BOS** | trend একই দিকে চলছে |
| **CHoCH** | প্রথম সতর্কবার্তা, হয়তো ঘুরছে |
| **MSS** | Sweep + Displacement + break — পূর্ণ ঘোরার প্রমাণ |
| **FVG** | তিন candle-এর মাঝে ফাঁকা দাম — বাজার এড়িয়ে গেছে |
| **OB** | বড় move শুরুর ঠিক আগের উল্টো candle |
| **Breaker** | ভেঙে যাওয়া OB — এখন উল্টো ভূমিকা |
| **POI** | Point of Interest — যেখানে ঢুকব (FVG/OB/BB…) |
| **Premium / Discount** | range-এর উপরের অর্ধেক / নিচের অর্ধেক |
| **OTE** | discount-এর ভেতরের মিষ্টি অংশ (fib 0.618–0.786) |
| **Kill Zone** | দিনের ব্যস্ততম সময়-জানালা |
| **DOL** | Draw on Liquidity — দাম যে চুম্বকের দিকে যাচ্ছে |
| **CE** | Consequent Encroachment — যেকোনো ফাঁকার ঠিক মাঝবিন্দু |
| **RR** | লাভ ÷ ক্ষতি |

---

## 3. Architecture — তিন তলা বাড়ি

```text
┌────────────────────────────────────────────────┐
│ LAYER 3 — সিদ্ধান্ত (একটাই দরজা)               │
│ State Machine → Score → RR → SL/TP → Signal    │
├────────────────────────────────────────────────┤
│ LAYER 2 — ঘটনা                                  │
│ BOS CHoCH MSS Sweep Displacement FVG OB BB      │
│ IFVG Trap CISD BPR VI …                         │
├────────────────────────────────────────────────┤
│ LAYER 1 — কাঁচা তথ্য (কোনো মতামত নেই)           │
│ Swing HH/HL/LH/LL Liquidity ATR Session HTF     │
│ Range Trendline Gap ADR Open-lines Regime       │
└────────────────────────────────────────────────┘
```

- **Layer 1** = শুধু দেখা, কোনো রায় নেই
- **Layer 2** = ঘটনা চিহ্নিত করা, তবুও কোনো buy/sell নেই
- **Layer 3** = একমাত্র জায়গা যেখানে signal জন্মায়

> **৯০% বাজে SMC indicator-এর একটাই রোগ:** Layer 2-এর একটা ঘটনা (FVG/BOS) সরাসরি signal বানিয়ে ফেলা। এটা কোরো না।

---

## 4. Pine Script v6 — যে ফাঁদগুলোতে সবাই পড়ে

এই section টা নতুন (03/04-এ ছিল না)। এক দিন বাঁচাবে।

**4.1 UDT হলো reference — copy নয়**

```pinescript
Zone z = array.get(zones, 0)
z.state := "FILLED"          // ✅ array-র ভেতরের object-ই বদলায়, আলাদা করে set করার দরকার নেই

Zone copy = Zone.new(...)     // নতুন object চাইলে হাতে বানাতে হয়
```

**4.2 `var` object একবারই তৈরি হয়**

```pinescript
var Setup activeLong = Setup.new(state = "IDLE")   // ✅ একবার
Setup bad = Setup.new(...)                          // ❌ প্রতি bar-এ নতুন — state হারায়
```

**4.3 Array থেকে মোছার সময় পেছন থেকে loop**

```pinescript
for i = array.size(zones) - 1 to 0
    if array.get(zones, i).state == "INVALID"
        array.remove(zones, i)      // সামনে থেকে মুছলে index লাফিয়ে যায়
```

**4.4 Drawing object leak** — `array.remove()` করার **আগে** `box.delete()` / `line.delete()` / `label.delete()`। নাহলে object চার্টে থেকে যায়, আর limit ভরে যায়।

**4.5 `na` object-এ field পড়া = runtime error**

```pinescript
if not na(activeLong) and activeLong.state == "IDLE"    // ✅ আগে na check
```

**4.6 শূন্য দিয়ে ভাগ**

```pinescript
rangeSize = math.max(high - low, syminfo.mintick)   // সবসময় এভাবে
```

**4.7 `request.security` তিনটা নিয়ম** — (ক) `[1]` offset, (খ) `lookahead_off`, (গ) সর্বোচ্চ ৮টা কল। এই তিনটার একটাও ভাঙলে repaint।

**4.8 `history_reference_length`** — গভীর reference লাগলে `indicator(..., max_bars_back = 5000)`।

**4.9 `switch` কোনো মান ফেরত না দিলে** compile error — প্রতিটা branch-এ assignment রাখো, নাহলে `=>` এর বদলে `if/else` লেখো।

**4.10 প্রতি bar-এ নতুন drawing বানাবে না** — একবার `box.new()`, তারপর `box.set_right()` দিয়ে টেনে বড় করো।

---

## 5. Code Skeleton — এই কাঠামোতেই লিখবে

```pinescript
//@version=6
indicator("SMC + ICT Engine", overlay = true, max_bars_back = 5000,
          max_boxes_count = 500, max_lines_count = 500, max_labels_count = 500)

// ═══ 01 · INPUTS ══════════════════════════════════
// ═══ 02 · TYPES ═══════════════════════════════════
// ═══ 03 · STATE (var) ═════════════════════════════
// ═══ 04 · HELPERS (pure function) ═════════════════
// ═══ 05 · LAYER 1 — FACTS ═════════════════════════
// ═══ 06 · LAYER 2 — EVENTS ════════════════════════
// ═══ 07 · LAYER 3 — DECISION ══════════════════════
// ═══ 08 · CLEANUP ═════════════════════════════════
// ═══ 09 · DRAWING ═════════════════════════════════
// ═══ 10 · DASHBOARD ═══════════════════════════════
// ═══ 11 · ALERTS ══════════════════════════════════
```

**Naming (একদম মানবে):** input → `xxxOn`, `xxxLen`, `xxxMult` · state → `activeLong` · function → ক্রিয়াপদ `isSweep()`, `nextLiqAbove()` · group string → `grpTL` ধরনের const।

**ক্রম বাধ্যতামূলক:** হিসাব → cleanup → আঁকা। Loop-এর ভেতরে কখনো আঁকবে না।

---

## 6. Data Model — সব type এক জায়গায়

```pinescript
// ── LAYER 1 ──────────────────────────────────────
type Swing
    int    barIndex
    float  price
    bool   isHigh
    string label          // "HH" | "HL" | "LH" | "LL"
    bool   swept

type LiqLevel
    string kind           // BSL SSL EQH EQL PDH PDL PWH PWL TLQ
    float  price
    int    createdBar
    bool   swept
    int    sweptBar
    int    strength       // কয়টা level একসাথে জমে আছে

type Trendline
    string id
    int    x1
    float  y1
    int    x2
    float  y2
    float  slope
    bool   isSupport
    int    touchCount
    int    lastTouchBar
    bool   broken
    int    brokenBar
    bool   retested
    float  strength       // 0–100
    line   drawing

type Gap                  // NWOG NDOG ORG VI — FVG নয়
    string kind
    float  top
    float  bottom
    float  ce
    int    createdBar
    bool   filled
    box    drawing

// ── LAYER 2 ──────────────────────────────────────
type Zone
    string id             // "FVG_1234" — unique, কখনো reuse নয়
    string kind           // FVG OB BB IFVG MB RB SD BPR UNICORN
    string direction      // "BULL" | "BEAR"
    float  top
    float  bottom
    float  ce
    int    createdBar
    string state          // NEW ACTIVE TOUCHED MITIGATED FILLED INVALID
    bool   consumed       // এখান থেকে signal দেওয়া হয়ে গেছে?
    int    touchCount
    float  mitigationPct
    bool   isHTF          // HTF থেকে আনা POI?
    box    drawing

type Divergence
    string kind           // "SMT"
    string direction
    int    barIndex
    string refSymbol
    bool   consumed

// ── LAYER 3 ──────────────────────────────────────
type Setup
    string id
    string direction      // "LONG" | "SHORT"
    string state
    float  sweepLevel
    int    sweepBar
    float  mssLevel
    int    mssBar
    Zone   poi
    float  entryPrice
    float  slPrice
    float  tp1
    float  tp2
    float  tp3
    float  rr
    int    score
    int    expireBar
    bool   signalEmitted
    bool   cisdConfirmed
    bool   smtPresent
    bool   trapConfirmed
    string amdPhase       // ACCUM MANIP DISTRIB NONE
    float  dolTarget
    string modelName      // STANDARD SILVER_BULLET MMBM UNICORN
    float  riskUnits      // position size (Phase 41)
```

```pinescript
var array<Swing>      swings     = array.new<Swing>()
var array<LiqLevel>   liquidity  = array.new<LiqLevel>()
var array<Zone>       zones      = array.new<Zone>()
var array<Trendline>  trendlines = array.new<Trendline>()
var array<Gap>        gaps       = array.new<Gap>()
var array<Divergence> divs       = array.new<Divergence>()
var Setup activeLong  = Setup.new(state = "IDLE", direction = "LONG")
var Setup activeShort = Setup.new(state = "IDLE", direction = "SHORT")
```

**Cap (হার্ড লিমিট):** swings 100 · liquidity 50 · zones 100 · trendlines 20 · gaps 30 · divs 20।
**Unique id:** `kind + "_" + str.tostring(bar_index)` — কখনো পুনর্ব্যবহার নয়।
**State change শুধু `barstate.isconfirmed`-এ** (Phase 46-এর intrabar mode ছাড়া)।

---

## 7. Roadmap — তিনটা Tier

Tier A শেষ হলেই indicator **বিক্রয়যোগ্য**। B আর C মান বাড়ায়।

### Tier A — Core (এটা ছাড়া কিছু নেই) · ~15 দিন

| # | Module | Layer | নির্ভর | দিন |
|---:|---|---|---|---|
| 1 | Swing + HH/HL/LH/LL | 1 | — | 1 |
| 2 | Liquidity mapping | 1 | 1 | 1 |
| 3 | BOS / CHoCH | 2 | 1 | 1 |
| 4 | Displacement | 2 | — | 0.5 |
| 5 | Sweep + MSS | 2 | 2,4 | 1 |
| 6 | FVG + lifecycle | 2 | 4 | 1 |
| 7 | OB / Breaker / IFVG | 2 | 6 | 1.5 |
| 8 | Premium/Discount + OTE | 1 | 1 | 0.5 |
| 9 | HTF context | 1 | 1,3 | 1 |
| 10 | Session / Kill Zone | 1 | — | 0.5 |
| 11 | **Entry State Machine** ⭐ | 3 | সব | 2 |
| 12 | Score + SL/TP + RR | 3 | 11 | 1 |
| 13 | Visuals + Settings | — | সব | 1 |
| 14 | Alerts | 3 | 11 | 0.5 |
| 15 | Repaint audit | — | সব | 1 |
| 16 | Integration tests | — | সব | 1 |

### Tier B — Advanced (ICT depth) · ~22 দিন

| # | Module | দিন |
|---:|---|---|
| 17 | **Dynamic Trendline Engine** ⭐ | 2 |
| 18 | Channel + Trendline Liquidity | 1.5 |
| 19 | CISD | 1 |
| 20 | SMT Divergence | 1 |
| 21 | AMD / PO3 + Judas Swing | 1.5 |
| 22 | Trap Trading + Turtle Soup | 1 |
| 23 | Supply/Demand + Mitigation + Rejection Block | 1.5 |
| 24 | BPR + Liquidity Void + CE | 1 |
| 25 | NWOG / NDOG / ORG | 1 |
| 26 | IRL / ERL + Draw on Liquidity | 1 |
| 27 | Silver Bullet + Macro Windows | 0.5 |
| 28 | MMBM / MMSM + Unicorn | 2 |
| 29 | Daily Bias + Weekly Profile | 1 |
| 30 | Standard Deviation Projection | 0.5 |
| 31 | **Score v2 + State Machine v2** ⭐ | 2 |
| 32 | Dashboard + Density Control | 1 |
| 33 | Performance / Object Budget | 1 |
| 34 | Extended Integration Tests | 1.5 |

### Tier C — Production (03/04 দুইটাতেই ছিল না) · ~13 দিন

| # | Module | কেন লাগবে | দিন |
|---:|---|---|---|
| 35 | **Range / Chop Regime Filter** | পাশাপাশি বাজারে সব SMC logic মিথ্যা বলে | 1 |
| 36 | ADR + Daily Range Exhaustion | দিন ইতিমধ্যে ১২০% হেঁটে ফেললে আর continuation নেই | 0.5 |
| 37 | True Day Open / Midnight / Weekly Open | ICT-র সবচেয়ে বেশি ব্যবহৃত reference line | 0.5 |
| 38 | Volume Imbalance + Gap taxonomy | VI ≠ FVG ≠ Void — আলাদা জিনিস, গুলিয়ে ফেলা হয় | 1 |
| 39 | HTF POI → LTF projection | HTF-এর FVG/OB ছোট chart-এ দেখাতে হয় | 1 |
| 40 | **Trade Management: TP1/2/3, BE, Trail** | একটামাত্র TP বাস্তবে কেউ ব্যবহার করে না | 1.5 |
| 41 | Risk % + Position Size | "কত lot?" — trader-এর ১ নম্বর প্রশ্ন | 1 |
| 42 | Time exit / EOD flat / News blackout | রাতভর ঝুলে থাকা trade আর news spike | 1 |
| 43 | Instrument Presets (FX/Gold/Index/Crypto) | এক default সব instrument-এ চলে না | 0.5 |
| 44 | **Backtest Stats Table** | কোনো প্রমাণ ছাড়া কেউ indicator বিশ্বাস করে না | 1.5 |
| 45 | Webhook JSON Alerts | bot/automation-এ লাগে | 0.5 |
| 46 | Intrabar Mode + Realtime handling | live trader আগে জানতে চায় | 1 |
| 47 | Defensive coding + input validation | runtime error = ১-star review | 1 |
| 48 | Delivery / Publish Checklist | — | 0.5 |

**মোট ~50 কর্মদিবস।** Tier A একা delivery করা যায়।

**⭐ চিহ্নিত ৩টা phase-এ (11, 17, 31) তাড়াহুড়ো করলে পুরো project নষ্ট।**

---
# TIER A — CORE ENGINE

## Phase 1 — Swing Structure

📖 **গল্প:** পাহাড়ের চূড়া আর উপত্যকার তলা চিহ্নিত করা। মানচিত্র ছাড়া পথ চেনা যায় না। আর সবচেয়ে জরুরি — মানুষ ঠিক ওই চূড়া/তলার বাইরেই stop-loss রাখে, তাই চূড়া = পরের phase-এ "টাকার পুকুরের ঠিকানা"।

👁 **চার্টে:** উঁচু বিন্দুতে ছোট লেখা `HH`/`LH`, নিচু বিন্দুতে `HL`/`LL`।

⚙️ **Build:**

```pinescript
swingLen = input.int(5, "Swing Length", minval = 3, maxval = 20, group = "Structure")

var float lastSwingHigh = na
var float lastSwingLow  = na

// pivot len bar পরে confirm হয় — এটাই non-repaint-এর চাবি
ph = ta.pivothigh(high, swingLen, swingLen)
pl = ta.pivotlow(low,  swingLen, swingLen)

if not na(ph)
    p   = high[swingLen]
    lbl = na(lastSwingHigh) ? "HH" : (p > lastSwingHigh ? "HH" : "LH")
    array.push(swings, Swing.new(bar_index - swingLen, p, true, lbl, false))
    lastSwingHigh := p

if not na(pl)
    p   = low[swingLen]
    lbl = na(lastSwingLow) ? "LL" : (p < lastSwingLow ? "LL" : "HL")
    array.push(swings, Swing.new(bar_index - swingLen, p, false, lbl, false))
    lastSwingLow := p

if array.size(swings) > 100
    array.shift(swings)
```

✅ **Done কখন:** swing শুধু `swingLen` bar পরে আসে · HH/HL/LH/LL আগেরটার সাথে তুলনা করে বসে · চলমান candle কখনো swing নয় · array cap আছে।

🧪 **Proof:** (১) F5 reload → পুরনো swing হুবহু একই জায়গায় (২) শেষ `swingLen` bar-এ কোনো label নেই — এটা **সঠিক**, bug নয় (৩) weekend gap-ওয়ালা chart-এ ভাঙে না।

🚫 **একা signal?** না।

> ⚠️ এখানে repaint থাকলে পুরো indicator মিথ্যা। এই test pass না করে এক ইঞ্চি এগোবে না।

---

## Phase 2 — Liquidity Mapping

📖 **গল্প:** দশ হাজার মানুষ একই জায়গায় টাকা ফেলে রেখেছে (stop-loss)। বড় ক্রেতার ওটাই দরকার। দুইটা চূড়া প্রায় সমান হলে (EQH) পুকুর আরও বড়, কারণ সবাই ভাবে "double top, নিরাপদ"।

👁 **চার্টে:** চূড়া/তলা বরাবর অনুভূমিক dotted line, ডানে লেখা `BSL`/`SSL`/`EQH`/`PDH`…

⚙️ **Build:**

- প্রতিটা confirmed swing high → `BSL`, swing low → `SSL`
- EQH/EQL: `math.abs(h1 - h2) < atrVal * eqTol` (default 0.1) — **চলমান bar বাদ**
- PDH/PDL/PWH/PWL:

```pinescript
pdh = request.security(syminfo.tickerid, "D", high[1], lookahead = barmerge.lookahead_off)
```

- `strength` = কতগুলো level একে অপরের `atrVal * 0.3`-এর ভেতরে জমে আছে (পুকুর যত ঘন, তত বড় target)

✅ **Done কখন:** সব type আঁকা হয় · EQ tolerance ATR-normalized (hard-coded pip নয় — নাহলে XAUUSD আর EURUSD এক code-এ চলবে না) · sweep হলে `swept = true`, level ধূসর · প্রতিটা type আলাদা toggle।

🧪 **Proof:** daily high line আজকের দিনের সাথে নড়ে না · EQH শুধু চোখেও সমান দেখালে আঁকে · sweep-এর পর auto-invalidate।

🚫 **একা signal?** না।

---

## Phase 3 — BOS / CHoCH

📖 **গল্প:** **BOS** = "গাড়ি একই দিকে চলছে"। **CHoCH** = "প্রথমবার brake লাইট জ্বলল" — হয়তো ঘুরবে, হয়তো না। "হয়তো" দিয়ে টাকা লাগানো যায় না।

👁 **চার্টে:** ভাঙা level বরাবর ছোট রেখা + `BOS` বা `CHoCH` লেখা, দুইটার রঙ আলাদা।

⚙️ **Build:**

```pinescript
bosMode = input.string("Close", "Break Mode", options = ["Close", "Wick"], group = "Structure")
brokeUp = bosMode == "Close" ? close > lastSwingHigh : high > lastSwingHigh
```

- Trend `var string trendDir = "NEUTRAL"` — `"BULL" | "BEAR" | "NEUTRAL"`
- Break trend-এর দিকে → **BOS** · উল্টো দিকে → **CHoCH** + trend flip

✅ **Done কখন:** Close mode default · আলাদা label ও রঙ · CHoCH কোথাও signal দেয় না, শুধু `"CHOCH_WARNING"` · একই level থেকে বারবার BOS আঁকে না (level consumed)।

🧪 **Proof:** wick level ছুঁয়ে ভেতরে close → Close mode-এ **কোনো BOS নেই** · Wick mode-এ toggle করলে ওখানেই BOS আসে।

🚫 **একা signal?** না।

---

## Phase 4 — Displacement

📖 **গল্প:** কেউ দরজা আস্তে খোলে, কেউ লাথি মেরে। লাথিটাই displacement — বড় candle, প্রায় পুরোটা body। বড় candle কিন্তু দুই দিকে লম্বা wick মানে ধাক্কাধাক্কি, কেউ জেতেনি — ওটা displacement নয়।

👁 **চার্টে:** লম্বা মোটা candle, ছোট wick। ইচ্ছা করলে উপরে ছোট ত্রিভুজ।

⚙️ **Build:**

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

✅ **Done কখন:** **দুইটা** শর্তই লাগে (ATR size **এবং** body ratio) · direction আলাদা · দুইটাই input।

🧪 **Proof:** বড় doji → displacement **নয়** · ১০০ bar-এ ~২–৫টা স্বাভাবিক; ২০+ হলে threshold ঢিলা।

🚫 **একা signal?** না।

---

## Phase 5 — Sweep + MSS ⭐ (Layer 2-এর হৃদয়)

📖 **গল্প:** চোর জানালা দিয়ে হাত ঢুকিয়ে টাকা নিয়ে **হাত বের করে আনল** — জানালা ভেঙে ভেতরে ঢুকে যায়নি। হাত ফিরিয়ে আনাটাই প্রমাণ যে উদ্দেশ্য ছিল শুধু টাকা, ঘর দখল নয়। বাইরেই থেকে গেলে সেটা sweep নয় — সেটা সত্যিকারের breakout, **উল্টো ঘটনা**।

**MSS** = তিনটা ঘটনা **এই ক্রমে**: ① stop খাওয়া হলো (জ্বালানি ভরা) → ② জোরে উল্টো move (ইঞ্জিন চালু) → ③ structure ভাঙল (দিক নিশ্চিত)। একটা missing = setup নেই।

👁 **চার্টে:** level-এর বাইরে লম্বা wick, body ভেতরে। তার পরে বড় উল্টো candle, তারপর ছোট চূড়া ভাঙা।

⚙️ **Build:**

```pinescript
// Bullish sweep — তিনটাই লাগবে
penetrated = low   < sslLevel
closedBack = close > sslLevel
rejection  = (close - low) / rangeSize > 0.5

sslSwept = penetrated and closedBack and rejection
```

- Sweep → `LiqLevel.swept := true`, `Setup.sweepLevel/sweepBar` রেকর্ড
- MSS check শুধু sweep-এর **পরের** bar থেকে (একই bar-এ sweep+MSS → reject)
- MSS = displacement + `close > lastInternalHigh`

✅ **Done কখন:** শুধু wick-এ sweep হয় না, close-back বাধ্যতামূলক · একই level দ্বিতীয়বার sweep হলে ignore · `mssTimeout` (10 bar) এর মধ্যে MSS না এলে setup মৃত · তিনটা উপাদান আলাদা debug করা যায়।

🧪 **Proof:** sweep আছে displacement নেই → **MSS নেই** · level-এর বাইরে close → sweep নয়, breakout · একই bar-এ sweep+break → reject।

🚫 **একা signal?** না — কিন্তু এটাই signal-এর মেরুদণ্ড।

---

## Phase 6 — FVG + Lifecycle

📖 **গল্প:** দৌড়ে যাওয়া লোক মাঝের একটা সিঁড়ি লাফিয়ে টপকে গেল। ওই না-মাড়ানো সিঁড়িটাই FVG। বাজার সাধারণত ফিরে এসে সিঁড়িটা মাড়িয়ে যায়।

**Lifecycle কেন:** কুয়ায় প্রথমবার বালতি ফেললে পানি আসে, পঞ্চমবার কাদা। তাই "কতবার ছোঁয়া হয়েছে" গুনতে হবে, আর **এক zone থেকে একটাই signal**।

👁 **চার্টে:** আয়তাকার ছায়া box, ভেতরে মাঝ বরাবর dashed line (CE)।

⚙️ **Build:**

```pinescript
bullFVG = low > high[2] and isBullDisp[1]          // মাঝের candle displacement হতে হবে
if bullFVG and (low - high[2]) >= atrVal * minGapMult
    array.push(zones, Zone.new(
        id = "FVG_" + str.tostring(bar_index), kind = "FVG", direction = "BULL",
        top = low, bottom = high[2], ce = (low + high[2]) / 2,
        createdBar = bar_index, state = "NEW", consumed = false))
```

**Lifecycle (প্রতি bar-এ প্রতিটা zone-এ চালাও):**

```text
NEW ─(পরের bar)─> ACTIVE ─(দাম ঢুকল)─> TOUCHED
 └─> MITIGATED (50%) ──> FILLED (100%) ──> INVALID
```

✅ **Done কখন:** দুই দিকেই formula সঠিক · min gap ATR-normalized · মাঝের candle displacement বাধ্যতামূলক · 50% mitigation track হয় · box `box.set_right()` দিয়ে extend, প্রতি bar-এ নতুন নয় · nested FVG-তে শুধু বাইরেরটা।

🧪 **Proof:** একই FVG-তে ৫ বার touch → `touchCount = 5`, signal **১টাই** · পূরণ হলে box ধূসর/মুছে যায় · 500 box limit-এ hang নেই।

🚫 **একা signal?** না। **এটাই সবচেয়ে বড় ফাঁদ** — FVG দেখে buy করা।

---

## Phase 7 — OB / Breaker / IFVG

📖 **গল্প:** **OB** = বড় লাফের ঠিক আগে যেখানে লোকটা পা রেখেছিল। ওখানে তার বাকি order পড়ে আছে, ফিরে এলে আবার কাজ করে। কিন্তু **প্রতিটা উল্টো candle OB নয়** — শুধু সেটাই, যার পরে সত্যিকারের লাফ এসেছে।

**Breaker** = OB ব্যর্থ। যারা ওখানে কিনেছিল তারা এখন আটকা; দাম ফিরলে তারা break-even-এ পালাবে → জায়গাটা এখন উল্টো ভূমিকায়।

**IFVG** = একই ব্যাপার FVG-র জন্য। Support ছিল, ভাঙল, এখন resistance।

👁 **চার্টে:** OB = ভরাট box · BB = ডোরাকাটা box, উল্টো রঙ · IFVG = ফিকে box।

⚙️ **Build:**

- Bullish OB = displacement candle-এর আগের **শেষ** bearish candle
- Validation (তিনটাই): পরের candle displacement + structure break + (preferred) FVG তৈরি
- OB `INVALID` → সাথে সাথে নতুন Zone `kind = "BB"`, direction উল্টো
- FVG `INVALID` → নতুন Zone `kind = "IFVG"`, direction উল্টো

✅ **Done কখন:** তিনটার আলাদা label ও রঙ · validation ছাড়া OB নেই · "Fresh OB only" toggle · FVG+OB overlap-এ FVG priority।

🧪 **Proof:** প্রতিটা bearish candle OB হিসেবে আঁকা হচ্ছে না · OB ভাঙার পর BB হয়ে যায়, পুরনো box পড়ে থাকে না।

🚫 **একা signal?** না।

---

## Phase 8 — Premium / Discount / OTE

📖 **গল্প:** দোকানদারের নীতি — সস্তায় কেনো, দামে বেচো। Range-এর নিচের অর্ধেক = discount (কেনার জায়গা), উপরের অর্ধেক = premium (বেচার জায়গা)। Premium-এ long নেওয়া মানে ইতিমধ্যেই দামে কেনা — RR খারাপ।

👁 **চার্টে:** range-এর মাঝ বরাবর `EQ` line, উপরে-নিচে হালকা ছায়া, OTE zone আলাদা রঙ।

⚙️ **Build:**

- Dealing range = সাম্প্রতিক confirmed swing high ও low
- `eq = (rangeHigh + rangeLow) / 2` · `inDiscount = close < eq`
- OTE: sweep low → MSS high পর্যন্ত fib, `0.618–0.786` zone আঁকো

✅ **Done কখন:** range নির্বাচনের নিয়ম documented · P/D শুধু score দেয়, signal নয় · structure বদলালে range নতুন করে হিসাব।

🚫 **একা signal?** না — **"discount-এ আছে" দেখে কখনো buy নয়।**

---

## Phase 9 — HTF Context

📖 **গল্প:** নদীতে সাঁতার। ১৫ মিনিটের ঢেউ যেদিকেই যাক, স্রোত (৪ ঘণ্টা) উল্টো হলে তুমি পিছিয়ে যাবে। আগে স্রোত দেখো, তারপর ঢেউয়ে ঝাঁপাও।

👁 **চার্টে:** উপরের কোণে `HTF: BULL` লেখা ছোট table।

⚙️ **Build — repaint-এর সবচেয়ে বিপজ্জনক জায়গা:**

```pinescript
// ❌ ভুল — চলমান HTF candle, ভবিষ্যৎ ফাঁস
htfHigh = request.security(syminfo.tickerid, htfTF, high)

// ✅ ঠিক — শুধু বন্ধ হওয়া HTF candle
htfHigh = request.security(syminfo.tickerid, htfTF, high[1], lookahead = barmerge.lookahead_off)
```

- HTF bias আসে HTF-এর BOS/CHoCH বা structure থেকে
- Auto-map: 1M→15M · 5M→1H · 15M→4H · 30M→4H · 1H→D (user override পারবে)

✅ **Done কখন:** প্রতিটা `request.security`-এ `[1]` + `lookahead_off` · auto-map আছে কিন্তু hard-coded নয় · bias চার্টে দেখা যায়।

🧪 **Proof:** realtime-এ signal → reload → signal ঠিক একই জায়গায় · HTF বদলে ফিরে এলে history অপরিবর্তিত।

🚫 **একা signal?** না।

---

## Phase 10 — Session / Kill Zone

📖 **গল্প:** বাজার সারাদিন এক নয়। এশিয়া = দোকান গোছানো (শান্ত)। London খোলা = প্রথম ধাক্কা, প্রায়ই এশিয়ার চূড়া/তলা sweep। New York = আসল কেনাবেচা। তাই sweep+MSS যদি London/NY-তে হয়, বেশি নির্ভরযোগ্য।

👁 **চার্টে:** session জুড়ে হালকা রঙিন background।

⚙️ **Build:**

```pinescript
tz   = input.string("America/New_York", "Session Timezone", group = "Sessions")
nyS  = input.session("0930-1600", "New York", group = "Sessions")
inNY = not na(time(timeframe.period, nyS, tz))
```

✅ **Done কখন:** timezone input (hard-coded নয়, DST নিজে হয়) · Asia/London/NY/Overlap/Custom সব আছে · shading toggle।

> ⚠️ Bangladesh local time দিয়ে কখনো session লিখবে না — DST-এর কারণে বছরে দুইবার ভুল হবে।

🚫 **একা signal?** না।

---

## Phase 11 — Entry State Machine ⭐⭐ সবচেয়ে গুরুত্বপূর্ণ

📖 **গল্প:** Visa আবেদন। ফর্ম → কাগজ জমা → interview → approval — প্রতিটা ধাপ আগেরটার পরে, আর প্রতিটার মেয়াদ আছে। মেয়াদ পেরোলে আবার প্রথম থেকে। State machine ছাড়া যা হয়: পুরনো setup নতুন trade খুলে দেয়, এক setup থেকে ৫টা signal আসে, MSS-এর আগেই entry হয়ে যায়।

```text
IDLE
 │  HTF bullish + দাম discount-এ
 ▼
CONTEXT_FOUND
 │  SSL sweep (close back inside)
 ▼
LIQUIDITY_SWEPT ────⏱ 10 bar────> INVALIDATED
 │  bullish displacement
 ▼
DISPLACEMENT_CONFIRMED
 │  close > internal high
 ▼
MSS_CONFIRMED ──────⏱ 20 bar────> INVALIDATED
 │  FVG বা OB তৈরি হলো
 ▼
POI_CREATED ────────⏱ 50 bar────> INVALIDATED
 │  দাম POI-তে ফিরল
 ▼
RETRACE_WAIT
 │  RR ≥ 1.5  এবং  score ≥ threshold
 ▼
ENTRY_TRIGGERED ──> signal একবার emit ──> TRADE_ACTIVE
 ▼
TP / SL / INVALIDATED ──> RESET (IDLE)
```

SHORT হুবহু আয়না-উল্টো।

⚙️ **Build:**

```pinescript
if barstate.isconfirmed
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

**কঠিন নিয়ম:** ① একসাথে একটাই LONG + একটাই SHORT ② একই bar-এ দুইটা trigger হলে **দুইটাই reject** ③ `ENTRY_TRIGGERED`-এ signal ঠিক একবার, তারপর `signalEmitted := true` ④ প্রতিটা transition শুধু `barstate.isconfirmed`-এ ⑤ প্রতিটা timeout input।

✅ **Done কখন:** সব state ও timeout কাজ করে · state কখনো পেছনে যায় না · debug table-এ চলমান state দেখা যায় · reset-এ **সব** field পরিষ্কার।

🧪 **Proof:** পুরো bullish ক্রম → ঠিক **১টা** LONG · FVG-তে ৫ touch → এখনো **১টা** · sweep-এর পর ১৫ bar চুপ → setup মৃত, পরে আর trigger করে না।

---

## Phase 12 — Score + SL / TP / RR

📖 **গল্প:** চাকরির interview — যত বেশি স্বাধীন যোগ্যতা, তত ভালো প্রার্থী। কিন্তু score দিয়ে **দ্বন্দ্ব ঢাকা যায় না**: HTF পরিষ্কার bearish হলে পাঁচটা bullish কারণ যোগ করেও সেটা long হয় না।

**SL** বসে সেখানে, যেখানে দাম গেলে পুরো ধারণাটাই মিথ্যা — sweep low-এর নিচে।
**TP** বসে পরের টাকার পুকুরে — দাম টাকার দিকেই ছোটে।
**RR কেন:** ২৫% জিতলেও 1:3-এ লাভ; 1:0.5-এ ৭০% জিতেও লোকসান। RR না মিললে **trade নেই**।

⚙️ **Build:**

```pinescript
buffer = atrVal * 0.2
longSL = activeLong.sweepLevel - buffer
longTP = nextLiquidityAbove(close)
rr     = (longTP - entry) / math.max(entry - longSL, syminfo.mintick)

if rr < minRR
    activeLong.state := "INVALIDATED"     // signal নেই — জোর করে বানাবে না
```

**TP priority:** Internal liquidity → previous swing → EQH/EQL → PDH/PDL → PWH/PWL → external → HTF liquidity → (সবার শেষে) Std-Dev projection

**Score v1** (Tier A): HTF+2 · Sweep+2 · MSS+2 · Displacement+2 · FVG+1 · OB+1 · P/D+1 · KillZone+1 → সর্বোচ্চ **12**
**Contradiction −3** (HTF উল্টো)

| Score | Grade | কর্ম |
|---:|---|---|
| 0–3 | Weak | NO TRADE |
| 4–6 | Moderate | optional |
| 7–9 | Strong | trade |
| 10+ | A+ | trade |

> Tier B শেষে এই score **Phase 31-এর v2**-তে বদলে যাবে (শ্রেণীভিত্তিক capping)। Tier A-তে SMT/Trap **সবসময় 0** — fake implementation বসাবে না।

✅ **Done কখন:** SL/TP/RR হিসাব হয় ও label-এ দেখায় · `rr < minRR` → signal নেই · score চার্টে দেখা যায়, threshold input · contradiction penalty কাজ করে।

---

## Phase 13 — Visuals + Settings

📖 **গল্প:** Trader-কে ২ সেকেন্ডে সিদ্ধান্ত নিতে হয়। ৫০টা box থাকলে সে কিছুই দেখে না — indicator তখন সাহায্য নয়, বাধা।

⚙️ **Build:** প্রতিটা module-এর নিজস্ব toggle · group: Structure / Liquidity / FVG / OB / HTF / Sessions / Entry / Risk / Visuals · `INVALID`/`FILLED` zone auto-hide · optional debug table।

✅ **Done কখন:** সব module আলাদা বন্ধ করা যায় · সব off = chart সম্পূর্ণ পরিষ্কার · object limit-এ error নেই · dark ও light দুই theme-এ পড়া যায়।

---

## Phase 14 — Alerts

```pinescript
if longSignal and not activeLong.signalEmitted and barstate.isconfirmed
    alert("LONG " + syminfo.ticker + " | E:" + str.tostring(entry) +
          " SL:" + str.tostring(sl) + " TP:" + str.tostring(tp) +
          " RR:" + str.tostring(rr, "#.##") + " Score:" + str.tostring(score),
          alert.freq_once_per_bar_close)
    activeLong.signalEmitted := true
```

✅ **Done কখন:** Structure / Liquidity / Zone / Trade — চার category-র alert আছে · প্রতি setup-এ একবার · `alert.freq_once_per_bar_close` · message-এ entry/SL/TP/RR/score সব আছে।

---

## Phase 15 — Repaint & Lookahead Audit (delivery-র আগে বাধ্যতামূলক)

- [ ] সব `request.security()`-এ `lookahead_off` **এবং** `[1]`
- [ ] কোনো unconfirmed HTF candle ব্যবহৃত হয়নি
- [ ] Pivot N bar পরে confirm
- [ ] চলমান bar-এর high/low swing হিসেবে ব্যবহৃত হয়নি
- [ ] `var` state realtime-এ reset হয় না
- [ ] Alert-এ `barstate.isconfirmed` আছে
- [ ] Zone delete/recreate সঠিক

```text
1. Chart reload (F5)            → history হুবহু এক?
2. Realtime signal → bar close  → signal টিকল?
3. HTF বদলে ফেরত                → signal অপরিবর্তিত?
4. Bar replay                   → একই signal একই জায়গায়?
```

---

## Phase 16 — Integration Tests (Tier A acceptance)

| # | Test | প্রত্যাশিত |
|---|---|---|
| 1 | SSL sweep → disp → MSS → FVG → retrace | ঠিক ১টা LONG |
| 2 | BSL sweep → disp → MSS → FVG → retrace | ঠিক ১টা SHORT |
| 3 | Wick ভাঙল, ভেতরে close | Close mode-এ BOS নেই |
| 4 | Sweep আছে, displacement নেই | trade নেই |
| 5 | Valid setup কিন্তু RR < 1.5 | trade নেই |
| 6 | একই FVG-তে ৫ touch | ১টা signal |
| 7 | Reload / realtime তুলনা | সম্পূর্ণ consistent |
| 8 | Weekend gap | swing ভাঙে না |
| 9 | একই bar-এ LONG + SHORT | দুইটাই reject |
| 10 | ৫০০০ bar history | hang নেই, object error নেই |

**Sanity:** ১৫M chart, এক মাস → **১০–৪০টা signal**। ২০০+ হলে logic ঢিলা; ০ হলে কোনো transition আটকে আছে (debug table দেখো)।

---
# TIER B — ADVANCED (ICT depth)

> এখান থেকে প্রতিটা module-এর toggle **default off**। যেকোনো সময় সব off করলে Tier A-এর আচরণ হুবহু ফিরে আসতে হবে — এটাই Tier B-র একমাত্র সবচেয়ে গুরুত্বপূর্ণ শর্ত।

## Phase 17 — Dynamic Trendline Engine ⭐

📖 **গল্প:** মাঠের উপর দিয়ে হাজার মানুষ হেঁটে হেঁটে একটা পায়ে-চলা পথ বানিয়ে ফেলেছে। সবাই একই পথ দেখে, সবাই পথের ধারে জিনিস রাখে। Trendline নিজে support নয় — trendline হলো **stop-এর ঠিকানা**, ঠিক swing high/low-এর মতো।

**❌** "Trendline ভাঙল → SELL"
**✅** "Trendline ভাঙল → ওখানকার stop খাওয়া হলো → এখন দেখো displacement + MSS আসে কি না"

### 17.1 Anchor — কোন দুই বিন্দু

শুধু **confirmed swing** (Phase 1-এর array)। চলমান bar কখনো anchor নয়।

```pinescript
grpTL      = "Trendline"
tlOn       = input.bool(false, "Enable Dynamic Trendline", group = grpTL)
tlMaxAge   = input.int(200, "Max Anchor Age (bars)",    minval = 30, maxval = 1000, group = grpTL)
tlMinBars  = input.int(10,  "Min Bars Between Anchors", minval = 5,  maxval = 100,  group = grpTL)
tlMaxLines = input.int(4,   "Max Lines Per Side",       minval = 1,  maxval = 10,   group = grpTL)

buildSupport(Swing a, Swing b) =>
    valid = b.barIndex - a.barIndex >= tlMinBars and b.price > a.price
    valid ? Trendline.new(
        id = "TL_" + str.tostring(bar_index), x1 = a.barIndex, y1 = a.price,
        x2 = b.barIndex, y2 = b.price,
        slope = (b.price - a.price) / (b.barIndex - a.barIndex),
        isSupport = true, touchCount = 2, lastTouchBar = b.barIndex,
        broken = false, retested = false, strength = 0.0) : na
```

| Anchor নিয়ম | কারণ |
|---|---|
| দুইটাই confirmed pivot | repaint ঠেকানো |
| দূরত্ব ≥ `tlMinBars` | খাড়া অর্থহীন line বাদ |
| বয়স ≤ `tlMaxAge` | পুরনো line কেউ দেখে না |
| Support-এ `y2 > y1` | rising-ই support |
| Resistance-এ `y2 < y1` | falling-ই resistance |

### 17.2 Validity — line টা আসলেই বৈধ?

দুই বিন্দু দিয়ে যেকোনো line টানা যায়। কিন্তু মাঝখানে দাম line-এর ভুল পাশে চলে গিয়ে থাকলে ওই line কেউ আঁকবে না, কেউ ওখানে stop রাখবে না।

```pinescript
// x1→x2 এর মধ্যে support line-এর নিচে কোনো CLOSE থাকতে পারবে না
// (wick ছাড় — ওটাই stop hunt)
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

> **Performance:** এই loop প্রতি bar-এ প্রতিটা line-এ চালালে chart জমে যাবে। **শুধু তৈরির মুহূর্তে একবার**, তারপর cache। পরে প্রতি bar-এ শুধু নতুন bar-টা check (incremental)।

### 17.3 Strength (0–100)

```pinescript
tlStrength(Trendline t) =>
    touchScore = math.min(t.touchCount, 6) * 12                 // ≤72
    ageScore   = math.min((bar_index - t.x1) / 10, 15)          // ≤15
    slopeNorm  = math.abs(t.slope) / (atrVal / 10)
    angleScore = slopeNorm > 0.2 and slopeNorm < 3.0 ? 13 : 0   // খুব খাড়া/সমতল = খারাপ
    math.min(touchScore + ageScore + angleScore, 100)
```

**Touch গণনা:** দাম line-এর `atrVal * 0.25` ভেতরে + সঠিক দিকে close → `touchCount += 1`। পরপর ৩ bar একই touch গোনা যাবে না (`lastTouchBar` cooldown)।

### 17.4 পরিচ্ছন্নতা

প্রতি দিকে `tlMaxLines` টা, strength অনুযায়ী sort · প্রায় সমান্তরাল ও কাছাকাছি দুইটা line-এর মধ্যে শুধু শক্তিশালীটা · `broken` হওয়ার ২০ bar পর মুছে ফেলো।

✅ **Done কখন:** শুধু confirmed swing থেকে line · validity fail = line-ই তৈরি হয় না · touch দুইবার গোনা হয় না · cap মানা হয় · strength অনুযায়ী opacity/thickness · `line.set_xy2()` দিয়ে extend · toggle default off।

🧪 **Proof:** (১) reload → প্রতিটা line একই anchor (২) realtime-এ anchor নড়ে না, শুধু ডান দিক বাড়ে (৩) ৫০০০ bar-এ line object ≤ 50 (৪) চোখে দেখো — মানুষ হাতেও মোটামুটি ওখানেই আঁকত (৫) স্পষ্ট violation-এর জায়গায় কোনো line নেই।

🚫 **একা signal?** না, কখনোই না।

---

## Phase 18 — Channel + Trendline Liquidity (TLQ)

📖 **গল্প:** পায়ে-চলা পথের দুই ধারে দুইটা সমান্তরাল দাগ = channel। দাগের বাইরে সবার জিনিস (stop) রাখা। দাগ ভাঙলে দুইটার একটা ঘটে —

| যা ঘটল | মানে | করণীয় |
|---|---|---|
| ভাঙল + displacement + retest + structure break | আসল break | নতুন দিক ধরো |
| ভাঙল কিন্তু সাথে সাথে ভেতরে ফিরে close | **TLQ sweep** — শুধু stop খেল | **উল্টো দিকে** setup খোঁজো |

দ্বিতীয়টাই বেশি ঘটে। তাই default — break কে **sweep candidate** ধরা।

⚙️ **Build:**

```pinescript
tlBreakMode = input.string("Close", "TL Break Mode", options = ["Close", "Wick"], group = grpTL)
tlqOn       = input.bool(true, "Treat TL Break as Liquidity", group = grpTL)

tlPriceNow(Trendline t) => t.y2 + t.slope * (bar_index - t.x2)

lineY = tlPriceNow(t)
broke = tlBreakMode == "Close" ? close < lineY : low < lineY

// TLQ sweep = wick বাইরে, close ভেতরে
tlqSweep = low < lineY and close > lineY and (close - low) / rangeSize > 0.5
```

- `broke` → `t.broken := true`, `t.brokenBar := bar_index`
- Break-এর ২০ bar-এর মধ্যে ফিরে এসে reject → `t.retested := true` (ভালো entry context)
- `tlqSweep` → `liquidity` array-তে `LiqLevel.new(kind = "TLQ", price = lineY, swept = true)`

> **এখানেই trendline state machine-এ ঢোকে।** TLQ ঠিক SSL/BSL sweep-এর মতো আচরণ করে — `CONTEXT_FOUND → LIQUIDITY_SWEPT`। **আলাদা signal path কখনো নয়।**

**Channel:** support line-এর সমান্তরাল (একই slope) line উপরের সবচেয়ে দূরের swing high ছুঁয়ে। প্রস্থ `< atrVal * 1.5` হলে বাদ।

✅ **Done কখন:** TLQ sweep আর genuine break আলাদা label+রঙ · TLQ `liquidity` array-তে ঢোকে · retest flag কাজ করে · channel toggle default off · trendline নিজে কখনো signal দেয় না।

🧪 **Proof:** break আছে displacement নেই → trade নেই · trendline module off করলে Tier A-র signal সংখ্যা **হুবহু আগের মতো**।

---

## Phase 19 — CISD (Change in State of Delivery)

📖 **গল্প:** পাঁচজন মিলে দরজা ঠেলে বন্ধ রাখছিল। একজন এসে দরজাটা তাদের **শুরুর জায়গার চেয়েও বেশি খুলে ফেলল** — মানে ওদের পুরো চেষ্টাটা বাতিল। MSS-এর আগের সবচেয়ে ছোট প্রমাণ।

CISD = **আগাম** ইঙ্গিত · MSS = **পূর্ণ** নিশ্চয়তা। CISD-র level চমৎকার SL reference।

⚙️ **Build:**

```pinescript
grpC       = "CISD"
cisdOn     = input.bool(false, "Enable CISD", group = grpC)
cisdMaxRun = input.int(6, "Max Candle Run", minval = 2, maxval = 12, group = grpC)

var float cisdBullLevel = na
var int   runLen        = 0

if close < open
    runLen += 1
else
    runLen := 0

if runLen >= 2 and runLen <= cisdMaxRun
    cisdBullLevel := open[runLen - 1]      // দলের প্রথম candle-এর open

bullCISD = not na(cisdBullLevel) and close > cisdBullLevel and close > open
```

Bearish হুবহু উল্টো।

✅ **Done কখন:** run length সঠিক · CISD level dashed line-এ দেখা যায় · ব্যবহার শুধু (ক) score, (খ) `cisdAsDisplacement` on থাকলে displacement-এর বিকল্প প্রমাণ · কখনো একা signal নয়।

🧪 **Proof:** sideways-এ CISD প্রচুর আসে — স্বাভাবিক, তাই একা কিছু নয় · প্রতিটা MSS-এর আগে সাধারণত একটা CISD থাকে (ক্রম যাচাই করো)।

---

## Phase 20 — SMT Divergence

📖 **গল্প:** যমজ দুই ভাই সবসময় একসাথে হাঁটে। একদিন একজন পড়ে গেল, অন্যজন দাঁড়িয়ে রইল — কিছু একটা গণ্ডগোল। একটায় stop খাওয়ানো হচ্ছে, অন্যটা তাল মেলাচ্ছে না।

⚙️ **Build:**

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

bullSMT = low <= myLow and cLow > coLow
bullSMT := smtInv ? (low <= myLow and cHigh < ta.highest(cHigh, smtLook)) : bullSMT
```

**জোড়া:** EURUSD↔GBPUSD · ES↔NQ · EURUSD↔DXY (inverse) · BTC↔ETH

✅ **Done কখন:** `[1]` + `lookahead_off` · symbol খালি থাকলে নিঃশব্দে skip (error নয়) · inverse toggle কাজ করে · শুধু score `+1` · দুই swing জুড়ে dotted line।

🧪 **Proof:** অসম্পর্কিত symbol দিলে অর্থহীন SMT-র বন্যা — এটা documentation-এ লিখে দাও · SMT থাকা-না-থাকায় signal সংখ্যা বদলায় না, শুধু score।

---

## Phase 21 — AMD / Power of 3 + Judas Swing

📖 **গল্প:** তিন অঙ্কের নাটক, প্রতিদিন একই — ① **জমানো** (এশিয়া, শান্ত) ② **ধোঁকা** (London open-এ উল্টো দিকে ঝটকা = Judas Swing, retail কে ভুল দিকে ঢোকানো) ③ **আসল move** (NY)।

**কাজের কথা:** সকালের প্রথম বড় move প্রায়ই মিথ্যা। মিথ্যাটার দিক জানলে আসল দিক আগেই জানা।

⚙️ **Build:**

```pinescript
grpA   = "AMD / PO3"
amdOn  = input.bool(false, "Enable AMD", group = grpA)
asiaS  = input.session("2000-0000", "Accumulation (Asia)",   group = grpA)
judasS = input.session("0200-0500", "Manipulation (London)", group = grpA)
distS  = input.session("0700-1100", "Distribution (NY)",     group = grpA)

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
    asiaRangeSet := true          // lock — আর বদলাবে না

inJudas   = not na(time(timeframe.period, judasS, tz))
judasBull = inJudas and asiaRangeSet and low  < asiaLow  and close > asiaLow
judasBear = inJudas and asiaRangeSet and high > asiaHigh and close < asiaHigh
```

- `judasBull` → `amdPhase := "MANIP"`, দিনের bias = **BULL**
- Distribution window-এ ওই bias-এর দিকের setup `+1`, উল্টোটা `−1`

✅ **Done কখন:** Asia range দিনে একবার lock · Judas চিহ্নিত · phase dashboard-এ · session সব input · শুধু bias ও score।

🧪 **Proof:** Asia box সঠিক সময়ে বন্ধ হয় · ছুটির দিনে crash নেই (range খালি → skip)।

---

## Phase 22 — Trap Trading + Turtle Soup

📖 **গল্প:** "বিরাট ছাড়!" লেখা দেখে দোকানে ঢুকলে, ভেতরে ঢোকার পরই দরজা বন্ধ। যারা breakout দেখে কিনেছিল তারা আটকা — বের হতে তাদের বিক্রি করতেই হবে, সেই বাধ্যতামূলক বিক্রি দামকে আরও নামায়।

**Sweep vs Trap:** sweep এক candle-এ ঘটে; trap-এ দাম কয়েক bar বাইরে থাকতে পারে। তাই sweep logic দিয়ে trap ধরা যায় না — আলাদা module লাগে।

⚙️ **Build:**

```pinescript
grpT     = "Trap"
trapOn   = input.bool(false, "Enable Trap Detection", group = grpT)
trapBars = input.int(5,  "Max Bars Outside",     minval = 1,  maxval = 15, group = grpT)
tsLook   = input.int(20, "Turtle Soup Lookback", minval = 10, maxval = 60, group = grpT)

var int barsAbove = 0
if close > lastSwingHigh
    barsAbove += 1
else
    barsAbove := 0

bullTrap = barsAbove[1] >= 1 and barsAbove[1] <= trapBars and close < lastSwingHigh

tsLevel = ta.highest(high[1], tsLook)
tsShort = high > tsLevel and close < tsLevel      // Turtle Soup
```

✅ **Done কখন:** trap আর genuine breakout আলাদা (bars-outside গণনা) · `trapBars` ছাড়ালে সেটা breakout, trend flip · trap হলে `liquidity`-তে swept level push · score `+1` · Turtle Soup আলাদা toggle।

🧪 **Proof:** ১০ bar বাইরে থেকে নামল → trap **নয়** (limit 5) · trap ঠিক sweep-এর পথেই state machine-এ ঢোকে।

---

## Phase 23 — Supply/Demand + Mitigation + Rejection Block

📖 **গল্প:** OB হলো **একটা** পায়ের ছাপ। S/D zone হলো **পুরো দাঁড়ানোর জায়গা** — কয়েকটা candle-এর ছোট জটলা, যেখান থেকে বড় দৌড় শুরু। OB নিখুঁত, S/D প্রশস্ত — দুইটাই দরকার।

**Mitigation Block:** OB ভাঙেনি, কিন্তু দাম ফিরে এসে আটকা লোকদের break-even-এ ছেড়ে দিল, তারপর আবার মূল দিকে। Breaker-এর চেয়ে দুর্বল, trend continuation-এ কাজের।
**Rejection Block:** body নয়, **wick** দিয়ে মাপা zone — যেখানে বারবার লম্বা wick প্রত্যাখ্যান করেছে।

⚙️ **Build:**

- **Demand zone:** ≥3 candle-এর সরু জটলা (`range < atrVal * 0.8`), তার পরেই bullish displacement → zone = জটলার high/low
- **MB:** `kind = "MB"` — OB যেটা `TOUCHED` কিন্তু `mitigationPct < 100`, তারপর মূল দিকে displacement
- **RB:** যে candle-এর wick `> range * 0.6`, সেই wick-টাই zone

**Zone priority (overlap-এ কে জেতে):**

```text
UNICORN > FVG > OB > Breaker > MB > Rejection Block > S/D zone
```

✅ **Done কখন:** প্রতিটার আলাদা `kind`, রঙ, toggle · priority প্রয়োগ হয়, overlap-এ একটাই আঁকা হয় · চলমান জটলা থেকে S/D তৈরি হয় না · সব zone একই lifecycle মানে · মোট zone ≤ 100।

---

## Phase 24 — BPR + Liquidity Void + CE

📖 **গল্প:** **BPR** — একই জায়গায় উপরের দিকের ফাঁকা আর নিচের দিকের ফাঁকা একে অপরের উপর বসেছে। দুই দিকের অসামঞ্জস্য এক বিন্দুতে = শক্ত ভারসাম্য, সাধারণ FVG-র চেয়ে নির্ভরযোগ্য।
**Liquidity Void** — পরপর কয়েকটা candle প্রায় বিনা overlap-এ ছুটেছে, একটা লম্বা ফাঁকা করিডোর। দাম প্রায়ই পুরোটা ফেরত পূরণ করে।
**CE** — যেকোনো ফাঁকার ঠিক **মাঝবিন্দু**। বাস্তবে দাম পুরো ফাঁকা পূরণ না করে প্রায়ই মাঝখান থেকেই ঘুরে যায় — তাই entry-র জন্য সবচেয়ে কার্যকর একক দাম।

⚙️ **Build:**

```pinescript
ce(float top, float bottom) => (top + bottom) / 2

bprTop    = math.min(bullFVGTop, bearFVGTop)
bprBottom = math.max(bullFVGBottom, bearFVGBottom)
isBPR     = bprTop > bprBottom
```

- Liquidity Void: পরপর ≥3 candle, প্রতিটার সাথে আগেরটার overlap `< range * 0.2`
- প্রতিটা zone-এর ভেতরে CE dashed line
- **Entry reference input:** `"Zone Edge" | "CE" | "Zone Full"` — default **CE**

✅ **Done কখন:** সব zone/gap-এ CE হিসাব · entry reference input কাজ করে · BPR আলাদা `kind` ও রঙ · Liquidity Void আলাদা toggle, default off।

🧪 **Proof:** "CE" mode-এ entry zone-এর মাঝখানে বসে, RR সেই অনুযায়ী বদলায় · BPR শুধু সত্যিকারের overlap-এ আঁকা হয়।

---

## Phase 25 — NWOG / NDOG / Opening Range Gap

📖 **গল্প:** শুক্রবার বাজার বন্ধ হলো ১০০-তে, রবিবার খুলল ১০৩-এ। মাঝের ৩ টাকায় **কোনো লেনদেনই হয়নি** — বাজার সারা সপ্তাহ ওই ফাঁকটার দিকে টানে।

এগুলো FVG **নয়** — FVG তিন candle-এর গঠন, এগুলো **সময়ের** ফাঁক। আলাদা type, আলাদা রঙ, আলাদা toggle।

⚙️ **Build:**

```pinescript
grpG   = "Opening Gaps"
nwogOn = input.bool(false, "New Week Opening Gap", group = grpG)
nwogN  = input.int(3, "Keep Last N Gaps", minval = 1, maxval = 10, group = grpG)

newWeek = ta.change(time("W")) != 0
if newWeek and nwogOn
    prevClose = request.security(syminfo.tickerid, "W", close[1], lookahead = barmerge.lookahead_off)
    array.push(gaps, Gap.new(kind = "NWOG",
        top = math.max(open, prevClose), bottom = math.min(open, prevClose),
        ce = (open + prevClose) / 2, createdBar = bar_index, filled = false))
```

✅ **Done কখন:** শেষ N টা রাখা হয় · CE line আঁকা · পূরণ হলে `filled := true` · `[1]` + `lookahead_off` · শুধু context ও TP target, signal নয়।

🧪 **Proof:** Forex-এ রবিবার gap আসে, crypto-তে প্রায় শূন্য — দুইটাই সঠিক · reload-এ জায়গা অপরিবর্তিত।

---

## Phase 26 — IRL / ERL + Draw on Liquidity

📖 **গল্প:** দাম সবসময় একটা চুম্বকের দিকে যাচ্ছে। দুই রকম চুম্বক — **ভেতরের** (range-এর ভেতরের FVG/OB) আর **বাইরের** (range-এর বাইরের চূড়া/তলা, EQH/EQL)।

**নিয়ম:** বাইরে → ভেতরে → বাইরে। মানে: **ভেতরেরটা entry-র জায়গা, বাইরেরটা target।** এটাই Phase 12-এর TP priority-র পেছনের আসল কারণ।

⚙️ **Build:** dealing range-এর ভেতরের zone = IRL · বাইরের `LiqLevel` = ERL · `dolTarget` = bias-এর দিকে সবচেয়ে কাছের **unswept** ERL · চার্টে DOL একটা তীর।

✅ **Done কখন:** সব zone ও level শ্রেণীবদ্ধ · `dolTarget` Phase 12-এর TP-র সাথে সঙ্গতিপূর্ণ · structure বদলালে নতুন করে হিসাব · dashboard-এ দেখা যায়।

🧪 **Proof:** TP সবসময় একটা ERL-এ বসে (মাঝখানে শূন্যে নয়) · entry সবসময় একটা IRL-এ।

---

## Phase 27 — Silver Bullet + Macro Windows

📖 **গল্প:** ট্রেন প্ল্যাটফর্মে সারাদিন ভিড় থাকে না — নির্দিষ্ট কয়েকটা সময়ে থাকে। NY 10:00–11:00, NY 14:00–15:00, London 03:00–04:00। Macro = প্রতি ঘণ্টার `:50` থেকে পরের `:10`।

এগুলো signal নয় — **সময়ের ছাঁকনি**।

⚙️ **Build:**

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

✅ **Done কখন:** তিনটা window input, timezone থেকে · `sbOnly` on = window-এর বাইরে **emit** বন্ধ (state machine চলতে থাকে) · shading toggle · score `+1`।

🧪 **Proof:** `sbOnly` on করলে signal কমে কিন্তু কোনো state আটকে যায় না · macro window ≥1H timeframe-এ auto-disable (অর্থহীন)।

---

## Phase 28 — MMBM / MMSM + Unicorn

📖 **গল্প (MMBM):** দোকানদার দাম নামিয়ে সব মাল কিনে নিল, তারপর দাম আবার আগের জায়গায় তুলে বিক্রি করল। দাম যেখান থেকে শুরু, শেষে সেখানেই ফেরে — মাঝের পুরোটাই সংগ্রহ।

```text
Original Consolidation → Sell-side curve (নামা)
  → Smart Money Reversal (SSL sweep + MSS)
  → Buy-side curve (ওঠা) → Original Consolidation-এ ফেরা
```

📖 **গল্প (Unicorn):** দুইটা স্বাধীন কারণ ঠিক **একই দামে** — একটা Breaker Block আর একটা FVG overlap করছে। সবচেয়ে উচ্চমানের setup, আর সেই কারণেই বিরল।

⚙️ **Build:** MMBM = dealing range + state ট্র্যাক করে একটা `marketModel` var · Unicorn = `kind="BB"` আর `kind="FVG"` এর overlap `> 50%` → নতুন `kind="UNICORN"`, confluence score `+2` · `modelName` Setup-এ set, label ও alert-এ দেখাও।

✅ **Done কখন:** overlap শতাংশভিত্তিক (শুধু ছোঁয়া নয়) · Unicorn আলাদা রঙ ও label · MMBM phase dashboard-এ · `modelName` alert-এ যায় · কোনো model একা signal দেয় না।

🧪 **Proof:** Unicorn বিরল — ১০০০ bar-এ ০–৩টা। বেশি এলে threshold ঢিলা।

---

## Phase 29 — Daily Bias + Weekly Profile

📖 **গল্প:** সপ্তাহের দিনগুলোর চরিত্র আছে — সপ্তাহের চূড়া/তলা প্রায়ই মঙ্গল/বুধবার তৈরি হয়, সোমবার সরু, শুক্রবার প্রায়ই ফেরত হাঁটা।

⚙️ **Build:**

- `weeklyOpen = ta.valuewhen(newWeek, open, 0)` — **`request.security("W", open)` নয়**, ওটা repaint করবে
- Daily bias = (HTF bias ×2) + (PDH না PDL swept) + (weekly open-এর উপরে/নিচে)
- Dashboard: `BULL / BEAR / NEUTRAL` + কারণ

✅ **Done কখন:** weekly open repaint করে না · প্রতিটা উপাদান আলাদা করে dashboard-এ · শুধু score ও filter · day-of-week label optional।

---

## Phase 30 — Standard Deviation Projection

📖 **গল্প:** Sweep থেকে MSS পর্যন্ত দূরত্বটাকে একটা "ফিতা" ধরো। ওই ফিতার ২, ২.৫, ৪ গুণ দূরে দাম প্রায়ই থেমে যায়। কাছাকাছি কোনো liquidity target না থাকলে TP-র জন্য কাজে লাগে।

```pinescript
sdOn   = input.bool(false, "Std Dev Projections", group = "Targets")
sdMult = input.string("-2,-2.5,-4", "Multipliers", group = "Targets")

unit = mssLevel - sweepLevel          // bullish
// প্রতিটা multiplier m → level = sweepLevel + unit * math.abs(m)
```

✅ **Done কখন:** comma-separated parse · dotted line + label · TP priority-তে **সবার শেষে** · default off।

---

## Phase 31 — Score v2 + State Machine v2 ⭐

📖 **গল্প:** ১৮টা নতুন কারণ যোগ হওয়ার পর সবকিছু `+1` করলে প্রতিটা setup "A+" দেখাবে — score অর্থহীন হয়ে যাবে। তাই কারণগুলোকে **শ্রেণীতে ভাগ করো, আর এক শ্রেণী থেকে একবারই পয়েন্ট**।

| শ্রেণী | সদস্য | সর্বোচ্চ |
|---|---|---:|
| Context | HTF bias, Daily bias, Weekly profile | +2 |
| Liquidity | SSL/BSL sweep, TLQ, Trap, Turtle Soup | +2 |
| Structure | MSS, CISD, BOS | +2 |
| Momentum | Displacement | +2 |
| POI | FVG, OB, BB, MB, S/D, BPR | +1 |
| POI Confluence | Unicorn, FVG+OB overlap | +2 |
| Location | Premium/Discount, OTE, CE | +1 |
| Time | Kill Zone, Silver Bullet, Macro, AMD distribution | +1 |
| Correlation | SMT | +1 |
| **সর্বোচ্চ** | | **14** |

| দ্বন্দ্ব | শাস্তি |
|---|---:|
| HTF bias উল্টো | −3 |
| Daily bias উল্টো | −2 |
| AMD manipulation-এর দিকেই trade | −2 |
| POI ইতিমধ্যে ২+ বার touched | −1 |
| Premium-এ LONG (বা discount-এ SHORT) | −2 |
| **Range/Chop regime** (Phase 35) | −3 |
| **ADR ১২০% শেষ** (Phase 36) | −2 |

| Score | Grade | কর্ম |
|---:|---|---|
| ≤ 4 | Weak | NO TRADE |
| 5–7 | Moderate | optional (input) |
| 8–10 | Strong | trade |
| 11+ | A+ | trade, size বড় করার যোগ্য |

**State Machine v2 — নতুন প্রবেশপথ (নতুন দরজা নয়, একই দরজার নতুন চাবি):**

```text
CONTEXT_FOUND ─> LIQUIDITY_SWEPT
   • SSL/BSL sweep (P5) · TLQ sweep (P18) · Trap/Turtle Soup (P22)

LIQUIDITY_SWEPT ─> DISPLACEMENT_CONFIRMED
   • displacement (P4) · অথবা CISD যদি cisdAsDisplacement = true (P19)

MSS_CONFIRMED ─> POI_CREATED
   • FVG | OB | BB | MB | S/D | BPR | UNICORN | HTF-POI (P6,7,23,24,28,39)

RETRACE_WAIT ─> ENTRY_TRIGGERED
   • RR ≥ minRR  এবং  score ≥ threshold
   • এবং sbOnly হলে inSB · এবং regime ≠ CHOP (P35) · এবং news blackout নয় (P42)
```

**নতুন কঠিন নিয়ম (Phase 11-এর ৫টার সাথে):**

6. একই bar-এ একাধিক liquidity trigger → **একবারই** transition, Liquidity শ্রেণী থেকে **একটাই** পয়েন্ট
7. নতুন কোনো module signal emit করতে পারবে না — শুধু state trigger বা score
8. কোনো module-এর toggle off = state machine-এ তার path সম্পূর্ণ নিষ্ক্রিয়
9. Score threshold input, default **8** (Tier A-তে ছিল 7)

✅ **Done কখন:** শ্রেণীভিত্তিক capping কাজ করে, double counting নেই · সব penalty কাজ করে · debug table-এ শ্রেণী অনুযায়ী ভাঙা score · সব নতুন module off = v1-এর সমান ফল · state কখনো পেছনে যায় না।

🧪 **Proof (সবচেয়ে গুরুত্বপূর্ণ):** সব নতুন toggle off → Phase 16-এর ১০টা test **হুবহু** আগের ফল · সব on → signal সংখ্যা **কমে**, বাড়ে না। বাড়লে কোনো module signal emit করছে — খুঁজে বের করো।

---

## Phase 32 — Dashboard + Visual Density

```pinescript
densityMode = input.string("Normal", "Visual Density",
                           options = ["Minimal", "Normal", "Full"], group = "Visuals")
// Minimal : শুধু active setup-এর POI + signal label
// Normal  : + structure label, liquidity level, active zone
// Full    : সব
```

| সারি | Dashboard-এ যা থাকবে |
|---:|---|
| 1 | HTF Bias / Daily Bias |
| 2 | AMD Phase + Session + Regime (P35) |
| 3 | Active LONG state + bars in state |
| 4 | Active SHORT state + bars in state |
| 5 | Score (শ্রেণী অনুযায়ী ভাঙা) |
| 6 | DOL target + দূরত্ব (ATR-এ) |
| 7 | ADR ব্যবহৃত % (P36) |
| 8 | Object count: zones / lines / boxes / labels |
| 9 | Session stats: আজকের signal সংখ্যা |

✅ **Done কখন:** toggle + তিনটা position · density তিনটাই কাজ করে · dark ও light-এ পড়া যায় · row 8 দেখে limit-এর দূরত্ব বোঝা যায়।

---

## Phase 33 — Performance / Object Budget

📖 **গল্প:** TradingView-তে আঁকার জিনিসের কঠিন সীমা। সীমায় পৌঁছালে পুরনো object **নিঃশব্দে** মুছে যায় — indicator ভুল দেখায়, কোনো error ছাড়াই। এটাই সবচেয়ে বিভ্রান্তিকর bug।

| Module | Box | Line | Label |
|---|---:|---:|---:|
| Zones (সব ধরন) | 100 | 0 | 100 |
| Trendlines + channel | 0 | 40 | 20 |
| Liquidity levels | 0 | 60 | 60 |
| Gaps (NWOG/NDOG/VI) | 30 | 30 | 30 |
| Sessions / AMD / SB | 60 | 0 | 20 |
| Open lines (P37) | 0 | 20 | 20 |
| Signals + SL/TP/TP2/TP3 | 0 | 80 | 80 |
| Structure (BOS/CHoCH/MSS) | 0 | 80 | 80 |
| **মোট** | **190** | **310** | **410** |

**নিয়ম:** ① কোনো module budget ছাড়াবে না — array cap দিয়ে জোর করো ② ভারী হিসাব (trendline validity, SMT) শুধু `barstate.isconfirmed`-এ ③ `request.security` সর্বোচ্চ ৮টা ④ `max_bars_back` স্পষ্ট ⑤ loop-এর ভেতরে আঁকবে না — আগে হিসাব, পরে আঁকা ⑥ delete করার আগে drawing delete (Pine ফাঁদ 4.4)।

✅ **Done কখন:** ৫০০০ bar + সব module on → load < ৫ সেকেন্ড · "object limit" আচরণ নেই · dashboard বাস্তব সংখ্যা দেখায় · ১০ বার timeframe বদলেও freeze নেই।

---

## Phase 34 — Extended Integration Tests (Tier B acceptance)

Phase 16-এর ১০টা **আগে** pass করতে হবে (সব নতুন toggle off অবস্থায়)।

| # | Test | প্রত্যাশিত |
|---|---|---|
| 11 | সব নতুন module off | Phase 16-এর ফল **অক্ষরে অক্ষরে** এক |
| 12 | Trendline on, reload ×3 | প্রতিটা line একই anchor |
| 13 | Trendline break, displacement নেই | trade নেই |
| 14 | TLQ sweep + disp + MSS + POI | ঠিক ১টা signal |
| 15 | SMT symbol খালি | error নেই, skip |
| 16 | SMT ভুল symbol | signal সংখ্যা অপরিবর্তিত, শুধু score |
| 17 | Asia range + Judas | range lock, Judas চিহ্নিত, bias set |
| 18 | Trap: ১০ bar বাইরে থেকে ফেরত | trap **নয়** |
| 19 | Unicorn (BB+FVG overlap) | confluence +2, ১টাই zone |
| 20 | `sbOnly` on | বাইরের signal বন্ধ, state আটকায় না |
| 21 | সব module on, 5000 bar | load < 5s, object error নেই |
| 22 | Weekend gap + NWOG | gap আঁকে, swing ভাঙে না |

---
# TIER C — PRODUCTION (03 আর 04, দুইটাতেই এগুলো ছিল না)

## Phase 35 — Range / Chop Regime Filter ⭐ (সবচেয়ে বড় missing জিনিস)

📖 **গল্প:** পুরো SMC দর্শনটা দাঁড়িয়ে আছে "বড় ক্রেতা একদিকে ঠেলছে" ধারণার উপর। কিন্তু বাজার সময়ের ৬০–৭০% **কেউ ঠেলছে না** — এলোমেলো পাশাপাশি চলছে। ওই সময় প্রতিটা sweep মিথ্যা, প্রতিটা MSS দুই bar পরে উল্টে যায়। **Indicator-এর জানতে হবে কখন চুপ থাকতে হয়।**

👁 **চার্টে:** dashboard-এ `REGIME: TREND` / `RANGE` / `CHOP`, আর chop হলে background হালকা ধূসর।

⚙️ **Build (তিনটা স্বাধীন মাপকাঠি — অন্তত দুইটা একমত হতে হবে):**

```pinescript
grpR      = "Regime"
regimeOn  = input.bool(false, "Enable Regime Filter", group = grpR)
regimeLen = input.int(20, "Regime Lookback", minval = 10, maxval = 100, group = grpR)
chopBlock = input.bool(true, "Block signals in CHOP", group = grpR)

// ① দিকনির্দেশনার দক্ষতা: সরলরেখায় কতটা গেল বনাম মোট কত হাঁটল
netMove  = math.abs(close - close[regimeLen])
pathSum  = math.sum(math.abs(close - close[1]), regimeLen)
efficiency = netMove / math.max(pathSum, syminfo.mintick)      // 0–1

// ② Range সংকোচন: এখনকার range গড়ের তুলনায়
rngNow   = ta.highest(high, regimeLen) - ta.lowest(low, regimeLen)
rngAvg   = ta.sma(rngNow, regimeLen)
squeeze  = rngNow < rngAvg * 0.7

// ③ Structure ধারাবাহিকতা: শেষ 4 swing HH/HL (বা LH/LL) নাকি এলোমেলো
// (swings array থেকে গুনে নাও — consistent হলে trend)

regime = efficiency > 0.35 and not squeeze ? "TREND" :
         efficiency < 0.15 or squeeze      ? "CHOP"  : "RANGE"
```

**যা করবে:**

| Regime | আচরণ |
|---|---|
| `TREND` | স্বাভাবিক, score-এ কিছু বদল নেই |
| `RANGE` | শুধু range-এর প্রান্ত থেকে setup নাও, মাঝখান থেকে নয় |
| `CHOP` | score **−3**, আর `chopBlock` on থাকলে entry emit সম্পূর্ণ বন্ধ |

✅ **Done কখন:** তিনটা মাপকাঠি আলাদাভাবে দেখা যায় · regime dashboard-এ · `chopBlock` on/off কাজ করে · regime নিজে কখনো signal দেয় না, শুধু আটকায়।

🧪 **Proof:** স্পষ্ট sideways এলাকায় (চোখে দেখা) regime `CHOP` দেখায় · `chopBlock` on করলে ওই এলাকায় signal সংখ্যা শূন্যের কাছাকাছি নামে · স্পষ্ট trend-এ `TREND` দেখায়।

> এই একটা phase সাধারণত signal সংখ্যা ৩০–৫০% কমায় আর মান অনেক বাড়ায়।

---

## Phase 36 — ADR + Daily Range Exhaustion

📖 **গল্প:** একজন মানুষ দিনে গড়ে ১০ কিলোমিটার হাঁটে। আজ সে ইতিমধ্যে ১২ কিমি হেঁটে ফেলেছে — এখন "সে আরও হাঁটবে" ধরে বাজি ধরা বোকামি। দাম নিয়েও একই কথা।

👁 **চার্টে:** dashboard-এ `ADR: 82%`, আর ১০০% ছাড়ালে লাল।

⚙️ **Build:**

```pinescript
grpADR  = "ADR"
adrOn   = input.bool(false, "Enable ADR Filter", group = grpADR)
adrLen  = input.int(14, "ADR Days", minval = 5, maxval = 30, group = grpADR)
adrCap  = input.float(1.2, "Block above % of ADR", minval = 0.5, maxval = 2.0, group = grpADR)

dHigh = request.security(syminfo.tickerid, "D", high[1], lookahead = barmerge.lookahead_off)
dLow  = request.security(syminfo.tickerid, "D", low[1],  lookahead = barmerge.lookahead_off)
adr   = ta.sma(dHigh - dLow, adrLen)

todayHigh = ta.valuewhen(newDay, high, 0)   // চলমান দিনের running high/low রাখো
adrUsed   = (todayHigh - todayLow) / math.max(adr, syminfo.mintick)
adrBlock  = adrOn and adrUsed > adrCap
```

- `adrUsed > 1.2` → continuation setup-এ score **−2**
- কিন্তু **reversal setup-এ কিছু বিয়োগ নয়** — দিন শেষের দিকে reversal-ই বেশি ঘটে

✅ **Done কখন:** ADR repaint করে না (`[1]` + `lookahead_off`) · dashboard-এ % দেখায় · continuation আর reversal আলাদা আচরণ করে · toggle default off।

---

## Phase 37 — True Day Open / Midnight Open / Weekly Open

📖 **গল্প:** ICT-র সবচেয়ে বেশি ব্যবহৃত তিনটা রেখা — **মধ্যরাত NY (00:00)**, **08:30 NY**, আর **সপ্তাহের open**। কারণ সহজ: algorithm দিনের হিসাব ওখান থেকে শুরু করে। দাম ওই রেখার উপরে = দিনের bias bullish, নিচে = bearish।

👁 **চার্টে:** তিনটা অনুভূমিক রেখা, ডানে ছোট লেখা `MO` / `TDO` / `WO`।

⚙️ **Build:**

```pinescript
grpO    = "Open Lines"
moOn    = input.bool(false, "Midnight Open (00:00 NY)", group = grpO)
tdoOn   = input.bool(false, "True Day Open (08:30 NY)", group = grpO)
woOn    = input.bool(false, "Weekly Open",              group = grpO)

isMidnight = hour(time, tz) == 0 and minute(time, tz) == 0
var float midnightOpen = na
if isMidnight
    midnightOpen := open

var float weeklyOpen = na
if ta.change(time("W")) != 0
    weeklyOpen := open        // ✅ request.security নয় — repaint-free
```

- `close > midnightOpen` → দিনের bias bullish (Phase 29-এর সাথে যোগ হয়)
- প্রতিটা line নিজের দিন/সপ্তাহ শেষে থেমে যায়, অনন্তকাল extend হয় না

✅ **Done কখন:** তিনটা আলাদা toggle ও রঙ · timezone input থেকে · line দিন/সপ্তাহ শেষে থামে · repaint নেই · শুধু bias ও score, signal নয়।

---

## Phase 38 — Volume Imbalance + Gap Taxonomy

📖 **গল্প:** তিন রকম "ফাঁকা" আছে, বেশিরভাগ developer গুলিয়ে ফেলে —

| নাম | সংজ্ঞা | আকার |
|---|---|---|
| **FVG** | candle 1-এর high আর candle 3-এর low মেলে না | বড় |
| **VI (Volume Imbalance)** | আগের candle-এর **close** আর এই candle-এর **open** মেলে না, কিন্তু wick মিলে যায় | ছোট |
| **Liquidity Void** | পরপর কয়েকটা candle প্রায় বিনা overlap-এ ছুটেছে | খুব বড় |

VI ছোট কিন্তু নির্ভুল — দাম প্রায়ই ঠিক ওইটুকু পূরণ করে ঘুরে যায়। ভালো entry refinement, খারাপ প্রধান POI।

⚙️ **Build:**

```pinescript
viOn = input.bool(false, "Volume Imbalance", group = "Gaps")

// Bullish VI: গত candle-এর close থেকে আজকের open উপরে, কিন্তু wick overlap আছে
bullVI = open > close[1] and low <= high[1]
if bullVI and (open - close[1]) >= atrVal * 0.05
    array.push(gaps, Gap.new(kind = "VI", top = open, bottom = close[1],
        ce = (open + close[1]) / 2, createdBar = bar_index, filled = false))
```

✅ **Done কখন:** তিনটা ধরন আলাদা `kind`, রঙ, toggle · VI কখনো প্রধান POI হয় না (শুধু entry refinement বা confluence) · খুব ছোট VI (`< atr * 0.05`) বাদ · zone cap-এর ভেতরে থাকে।

🧪 **Proof:** VI on করলে চার্টে প্রচুর ছোট box আসে — তাই default off আর density mode "Full"-এ ছাড়া দেখাবে না।

---

## Phase 39 — HTF POI → LTF Projection

📖 **গল্প:** ৪ ঘণ্টার চার্টের FVG-টা ১৫ মিনিটের চার্টেও একই দামে আছে — শুধু তুমি সেটা দেখছ না। HTF-এর POI অনেক বেশি শক্তিশালী, কারণ অনেক বেশি মানুষ ওটা দেখছে।

👁 **চার্টে:** মোটা সীমানার box, লেখা `4H FVG` — সাধারণ box-এর চেয়ে গাঢ়।

⚙️ **Build:**

```pinescript
htfPoiOn = input.bool(false, "Show HTF POI on LTF", group = "HTF")

[hH2, hL0, hDisp] = request.security(syminfo.tickerid, htfTF,
                        [high[2], low[0], isBullDisp[1]], lookahead = barmerge.lookahead_off)
// HTF FVG detect হলে Zone.new(..., isHTF = true) — একই zones array-তে
```

**নিয়ম:**

- HTF zone একই `zones` array-তে থাকবে, `isHTF = true` flag দিয়ে
- HTF POI-তে entry হলে score `+1` (POI Confluence শ্রেণীতে, আলাদা নতুন শ্রেণী নয়)
- HTF zone-এর lifecycle LTF zone-এর মতোই, কিন্তু cap আলাদা (সর্বোচ্চ 20টা)
- Zone priority-তে HTF একই kind-এর LTF zone-কে হারায়

✅ **Done কখন:** `[1]`/`[2]` offset + `lookahead_off` · HTF zone দৃশ্যত আলাদা · lifecycle কাজ করে · cap আলাদা · repaint audit pass।

🧪 **Proof:** HTF chart খুলে চোখে মিলিয়ে দেখো — box ঠিক একই দামে আছে · HTF বদলে ফেরত এলে history অপরিবর্তিত।

---

## Phase 40 — Trade Management: TP1/TP2/TP3 + BE + Trail ⭐

📖 **গল্প:** বাস্তবে কেউ একটা TP নিয়ে বসে থাকে না। সে অর্ধেক তাড়াতাড়ি নেয় (মানসিক শান্তি), stop-কে খরচহীন জায়গায় সরায় (আর হারানোর ভয় নেই), বাকিটা দৌড়াতে দেয়। **এটা না থাকলে indicator অসম্পূর্ণ** — trader জিজ্ঞেস করবেই "এখন কী করব?"

👁 **চার্টে:** entry থেকে তিনটা লক্ষ্যরেখা `TP1 / TP2 / TP3`, একটা লাল `SL`, আর BE-তে সরলে line সবুজ হয়ে যায়।

⚙️ **Build:**

```pinescript
grpM    = "Trade Management"
tp1R    = input.float(1.0, "TP1 at R", minval = 0.5, maxval = 3.0, group = grpM)
tp1Pct  = input.int(50, "Close % at TP1", minval = 0, maxval = 100, group = grpM)
beOnTP1 = input.bool(true, "Move SL to BE at TP1", group = grpM)
trailOn = input.bool(false, "Trail by structure (last swing)", group = grpM)

risk = entry - sl                       // long
tp1  = entry + risk * tp1R              // R-ভিত্তিক
tp2  = nextLiquidityAbove(tp1)          // liquidity-ভিত্তিক
tp3  = activeLong.dolTarget             // চূড়ান্ত চুম্বক (P26)
```

**TP-র দুই দর্শন — দুইটাই দাও, input দিয়ে বেছে নেবে:**

| Mode | TP কোথায় |
|---|---|
| `R-based` | 1R, 2R, 3R — সহজ, যান্ত্রিক |
| `Liquidity-based` | পরের পুকুরগুলোতে — বাস্তবসম্মত (default) |

**Trail নিয়ম:** নতুন confirmed HL তৈরি হলে SL সেটার `atrVal * 0.2` নিচে সরাও। কখনো পেছনে সরবে না।

**State machine যোগ:** `TRADE_ACTIVE` → `TP1_HIT` → `BE_ACTIVE` → `TP2_HIT` → … → `CLOSED`

✅ **Done কখন:** তিনটা TP হিসাব ও আঁকা হয় · TP1-এ BE কাজ করে (input দিয়ে বন্ধ করা যায়) · trail কখনো পেছনে যায় না · প্রতিটা ধাপে আলাদা alert · label-এ `TP1 hit +1R` ধরনের লেখা।

🧪 **Proof:** history-তে একটা trade ধরে চোখে অনুসরণ করো — SL সঠিক সময়ে BE-তে সরেছে · TP2 কখনো TP1-এর নিচে বসে না।

---

## Phase 41 — Risk % + Position Size

📖 **গল্প:** Trader-এর ১ নম্বর প্রশ্ন: "কত lot?" উত্তর সবসময় একই অঙ্ক — **account × ঝুঁকি% ÷ (SL দূরত্ব × প্রতি পয়েন্টের মূল্য)**। Indicator এটা না দিলে trader হাতে ক্যালকুলেটর খোলে, আর ভুল করে।

👁 **চার্টে:** signal label-এ `Size: 0.42 lot | Risk: $100`।

⚙️ **Build:**

```pinescript
grpRisk  = "Risk"
acctSize = input.float(10000, "Account Size", minval = 100, group = grpRisk)
riskPct  = input.float(1.0, "Risk % per trade", minval = 0.1, maxval = 5.0, group = grpRisk)

riskCash  = acctSize * riskPct / 100
slDist    = math.abs(entry - sl)
tickValue = syminfo.pointvalue                       // instrument-ভেদে আলাদা
posSize   = riskCash / math.max(slDist * tickValue, 0.000001)
```

⚠️ **Instrument-ভেদে সতর্কতা:** Forex lot, index point, crypto coin — তিনটার হিসাব আলাদা। `syminfo.type` দেখে branch করো, আর label-এ **সবসময় একক লিখে দাও** (`0.42 lot` / `2 contracts` / `0.015 BTC`)।

✅ **Done কখন:** account ও risk% input · `syminfo.pointvalue`/`mintick` থেকে হিসাব · তিন ধরনের instrument-এ সঠিক একক · label ও alert-এ size যায় · **disclaimer**: "আনুমানিক, broker-এর হিসাব ভিন্ন হতে পারে"।

🧪 **Proof:** ঝুঁকি ১% → হাতে গুনে মিলিয়ে দেখো, SL hit হলে ক্ষতি ≈ account-এর ১% · SL দূরত্ব দ্বিগুণ করলে size ঠিক অর্ধেক হয়।

---

## Phase 42 — Time Exit / EOD Flat / News Blackout

📖 **গল্প:** তিনটা আলাদা ঝামেলা —
① Setup ঘণ্টার পর ঘণ্টা ঝুলে থাকে, বাজার ততক্ষণে সম্পূর্ণ বদলে গেছে
② NY বন্ধ হওয়ার পর পাতলা বাজারে trade ধরে রাখা অর্থহীন
③ বড় খবরের সময়কার লাফ SMC logic নয় — ওটা আতঙ্ক

⚙️ **Build:**

```pinescript
grpX      = "Exits & Filters"
maxHold   = input.int(50, "Max bars in trade", minval = 10, maxval = 300, group = grpX)
eodFlat   = input.bool(false, "Close at session end", group = grpX)
newsOn    = input.bool(false, "News Blackout", group = grpX)
newsTimes = input.string("0830,1000,1400", "Blackout times (NY, comma)", group = grpX)
newsPad   = input.int(15, "Blackout ± minutes", minval = 5, maxval = 60, group = grpX)
```

- `bar_index - entryBar > maxHold` → `TIME_EXIT`, আলাদা alert
- `eodFlat` on + session শেষ → `TIME_EXIT`
- News blackout window-এ **entry emit বন্ধ**, কিন্তু চলমান trade-এর management (BE/trail) চলতে থাকে

⚠️ Pine নিজে news feed পায় না — তাই সময় **হাতে লিখে** দিতে হয়। Documentation-এ পরিষ্কার লিখে দাও, নাহলে user ভাববে bug।

✅ **Done কখন:** তিনটা আলাদা toggle · time exit-এর আলাদা alert ও label · blackout শুধু নতুন entry আটকায়, management নয় · blackout window চার্টে ছায়া দিয়ে দেখা যায়।

---

## Phase 43 — Instrument Presets

📖 **গল্প:** EURUSD-এর জন্য ঠিক করা setting XAUUSD-এ পাগলামি করে (Gold-এর range ৫ গুণ বড়), আর BTC-তে তো ২৪/৭ session-এর অর্থই আলাদা। এক default সব instrument-এ চলে না।

⚙️ **Build:**

```pinescript
preset = input.string("Auto", "Instrument Preset",
                      options = ["Auto", "Forex", "Gold", "Index", "Crypto", "Manual"],
                      group = "Presets")

// Auto: syminfo.type + syminfo.ticker দেখে বেছে নাও
```

| Preset | Swing len | ATR mult | EQ tol | Min RR | Session |
|---|---:|---:|---:|---:|---|
| Forex | 5 | 1.2 | 0.10 | 1.5 | London+NY |
| Gold | 7 | 1.5 | 0.15 | 2.0 | London+NY |
| Index | 5 | 1.3 | 0.10 | 1.5 | NY only |
| Crypto | 8 | 1.4 | 0.12 | 2.0 | 24/7 |

✅ **Done কখন:** Auto-detect কাজ করে (`syminfo.type`) · `Manual` বাছলে preset সব input উপেক্ষা করে · dashboard-এ কোন preset চলছে দেখা যায় · preset শুধু **default** বদলায়, user override সবসময় জেতে।

---

## Phase 44 — Backtest Stats Table ⭐

📖 **গল্প:** "এটা ভালো indicator" — প্রমাণ কী? চার্টেই গুনে দেখাও: কয়টা signal, কয়টা TP-তে গেছে, কয়টা SL-এ, মোট কত R। প্রমাণ ছাড়া কেউ বিশ্বাস করে না, আর তুমি নিজেও জানবে না threshold ঠিক আছে কি না।

👁 **চার্টে:** নিচের কোণে ছোট table।

⚙️ **Build:**

```pinescript
var int   nTrades = 0
var int   nWins   = 0
var float sumR    = 0.0

// SL/TP hit detect করে (indicator-এর ভেতরেই, strategy() নয়)
if tradeClosed
    nTrades += 1
    rResult = (exitPrice - entry) / math.max(entry - sl, syminfo.mintick)   // long
    sumR   += rResult
    if rResult > 0
        nWins += 1

winRate    = nTrades > 0 ? nWins / nTrades * 100 : 0.0
expectancy = nTrades > 0 ? sumR / nTrades : 0.0
```

| Table সারি | মান |
|---|---|
| Total signals | 47 |
| Win rate | 41% |
| Total R | +18.4R |
| Expectancy | +0.39R / trade |
| Avg RR | 2.6 |
| Best / Worst | +4.2R / −1.0R |
| Max consecutive loss | 6 |

⚠️ **সৎ থাকার নিয়ম:** এটা **approximation**, backtester নয় — spread, slippage, commission ধরা নেই। একই bar-এ TP আর SL দুইটাই ছুঁলে **SL ধরো** (রক্ষণশীল)। এটা table-এর নিচে ছোট করে লিখে দাও।

✅ **Done কখন:** SL/TP hit সঠিকভাবে ধরা হয় · একই bar-এ দুইটা hit হলে SL ধরা হয় · table toggle · reset শুধু chart reload-এ · সীমাবদ্ধতার disclaimer লেখা আছে।

🧪 **Proof:** হাতে ১০টা signal গুনে table-এর সাথে মেলাও · expectancy ঋণাত্মক হলে threshold কড়া করো — table-টা এই কাজেই।

---

## Phase 45 — Webhook JSON Alerts

📖 **গল্প:** মানুষ পড়বে টেক্সট, bot পড়বে JSON। দুইটাই দাও।

```pinescript
alertFmt = input.string("Text", "Alert Format", options = ["Text", "JSON"], group = "Alerts")

jsonMsg = '{"sym":"' + syminfo.ticker + '","tf":"' + timeframe.period +
          '","side":"LONG","entry":' + str.tostring(entry) +
          ',"sl":' + str.tostring(sl) +
          ',"tp1":' + str.tostring(tp1) + ',"tp2":' + str.tostring(tp2) +
          ',"rr":' + str.tostring(rr, "#.##") +
          ',"score":' + str.tostring(score) +
          ',"model":"' + modelName + '","size":' + str.tostring(posSize, "#.##") +
          ',"time":' + str.tostring(time) + '}'
```

✅ **Done কখন:** দুইটা format-ই কাজ করে · JSON বৈধ (কোনো trailing comma নেই, string quoted) · প্রতিটা সংখ্যায় নির্দিষ্ট দশমিক · `{{...}}` placeholder-এর উপর নির্ভর করে না (সরাসরি string বানানো) · একই alert দুইবার যায় না।

🧪 **Proof:** alert message copy করে JSON validator-এ paste করো — পাস করতেই হবে।

---

## Phase 46 — Intrabar Mode + Realtime Handling

📖 **গল্প:** Live trader candle বন্ধ হওয়ার আগেই জানতে চায়। কিন্তু candle বন্ধ হওয়ার আগের সব কিছু **বদলাতে পারে** — এটাই repaint-এর উৎস। সমাধান: দুইটা mode দাও, আর **যা ঘটছে সেটা পরিষ্কার করে চার্টে লিখে দাও**।

⚙️ **Build:**

```pinescript
intrabar = input.bool(false, "Intrabar (early) signals — CAN REPAINT", group = "Entry")

confirmOK = intrabar ? true : barstate.isconfirmed
```

**নিয়ম:**

1. `intrabar = false` (default) → সব transition শুধু `barstate.isconfirmed`-এ, কোনো repaint নেই
2. `intrabar = true` → early signal আসে, কিন্তু label-এ `⚠ LIVE` লেখা থাকবে, আর bar বন্ধ হলে যদি শর্ত ভেঙে যায় → label মুছে যাবে
3. Alert **সবসময়** `alert.freq_once_per_bar_close` — early হলেও alert bar close-এই যাবে (নাহলে ভুয়া alert-এর বন্যা)
4. Intrabar on থাকলে dashboard-এ লাল সতর্কতা

✅ **Done কখন:** default off · on করলে চার্টে দৃশ্যমান সতর্কতা · alert কখনো intrabar-এ যায় না · off করলে Phase 15-এর repaint audit ১০০% pass।

---

## Phase 47 — Defensive Coding + Input Validation

📖 **গল্প:** একটা runtime error = TradingView-তে "Script error" লাল লেখা = ১-star review। প্রায় সব error-এর উৎস মাত্র পাঁচটা জায়গা।

**পাঁচটা প্রহরী:**

```pinescript
// ① শূন্য দিয়ে ভাগ — সবসময়
den = math.max(entry - sl, syminfo.mintick)

// ② na object
if not na(activeLong) and activeLong.state == "IDLE"

// ③ খালি array
lastSwing = array.size(swings) > 0 ? array.get(swings, array.size(swings) - 1) : na

// ④ ইতিহাসের বাইরে index
safeIdx = math.min(lookback, bar_index)

// ⑤ পরস্পরবিরোধী input
if tp1R >= 3.0 and minRR < 1.0
    runtime.error("TP1 R এবং Min RR পরস্পরবিরোধী — setting ঠিক করো")
```

**Input validation table (compile-time নয়, চালানোর সময়):**

| যাচাই | ব্যবস্থা |
|---|---|
| `swingLen >= 3` | `minval` দিয়ে আটকানো |
| HTF < current TF | সতর্কতা label, module নিঃশব্দে skip |
| SMT symbol invalid | skip, error নয় |
| Session string ভুল | default-এ ফিরে যাও + সতর্কতা |
| `mssTimeout > poiExpire` | `runtime.error` স্পষ্ট বার্তা সহ |

✅ **Done কখন:** পাঁচটা প্রহরীই আছে · ভুল input-এ পরিষ্কার বাংলা/ইংরেজি বার্তা, রহস্যময় crash নয় · HTF < LTF দিলে crash করে না · ১০টা অদ্ভুত setting চেষ্টা করে দেখো — একটাও crash করবে না।

---

## Phase 48 — Delivery / Publish Checklist

**Code:**

- [ ] প্রতিটা section `// ═══ NN · NAME ═══` header দিয়ে চিহ্নিত
- [ ] কোনো unused variable / dead code নেই
- [ ] প্রতিটা input-এ `tooltip` আছে
- [ ] Input group-এর ক্রম যুক্তিসঙ্গত (উপরে যেটা আগে দরকার)
- [ ] Default setting-এ চার্ট পরিষ্কার দেখায়

**Correctness:**

- [ ] Phase 15-এর repaint audit চারটাই pass
- [ ] Test 1–22 pass
- [ ] ৩ instrument × ৩ timeframe = ৯ combination
- [ ] সব module off → চার্ট সম্পূর্ণ খালি, error নেই
- [ ] সব module on → load < ৫ সেকেন্ড

**Publish:**

- [ ] Description-এ লেখা: এটা indicator, **strategy নয়**
- [ ] সীমাবদ্ধতা স্পষ্ট: stats approximation, position size আনুমানিক, intrabar mode repaint করতে পারে
- [ ] কোনো লাভের প্রতিশ্রুতি নেই
- [ ] পরিষ্কার চার্টের screenshot (৫টা box-এর জঙ্গল নয়)
- [ ] Setting দিয়ে কীভাবে শুরু করবে — ৩ লাইনের quick-start

---

# চূড়ান্ত তথ্যছক

## A. Parameter Defaults (সব একসাথে)

| Parameter | Default | Range | প্রভাব |
|---|---|---|---|
| Swing length | 5 | 3–20 | বেশি = কম swing, কম noise |
| BOS mode | Close | Close/Wick | Wick = ২–৩× বেশি false |
| ATR mult (displacement) | 1.2 | 0.8–2.0 | কম = বেশি setup, কম মান |
| Body ratio | 0.6 | 0.5–0.8 | বেশি = কড়া |
| EQH/EQL tolerance | 0.1 × ATR | 0.05–0.3 | — |
| FVG min size | 0.3 × ATR | 0.1–1.0 | — |
| Min RR | 1.5 | 1.0–3.0 | বেশি = কম trade |
| MSS timeout | 10 bar | 5–30 | — |
| Retrace timeout | 20 bar | 10–50 | — |
| POI expire | 50 bar | 20–200 | — |
| Score threshold (Tier A) | 7 | 5–12 | — |
| Score threshold (v2) | 8 | 5–14 | উপাদান বেড়েছে |
| **সব Tier B/C module** | **off** | — | v1 আচরণ রক্ষা |
| TL max anchor age | 200 bar | 30–1000 | — |
| TL min bars between anchors | 10 | 5–100 | কম = খাড়া line |
| TL max lines per side | 4 | 1–10 | বেশি = জট |
| TL touch tolerance | 0.25 × ATR | 0.1–0.6 | — |
| CISD max run | 6 | 2–12 | — |
| SMT lookback | 20 | 5–60 | — |
| Trap max bars outside | 5 | 1–15 | বেশি = breakout-ও trap |
| Entry reference | CE | Edge/CE/Full | CE = ভালো RR, কম fill |
| Regime lookback | 20 | 10–100 | — |
| ADR days | 14 | 5–30 | — |
| ADR block above | 1.2 | 0.5–2.0 | — |
| TP1 at R | 1.0 | 0.5–3.0 | — |
| Close % at TP1 | 50 | 0–100 | — |
| Risk % per trade | 1.0 | 0.1–5.0 | — |
| Max bars in trade | 50 | 10–300 | — |

## B. সম্পূর্ণ Test Matrix

**Tier A:** Test 1–10 (Phase 16) · **Tier B:** Test 11–22 (Phase 34) · **Tier C:** নিচের 23–32

| # | Test | প্রত্যাশিত |
|---|---|---|
| 23 | স্পষ্ট sideways এলাকা | Regime `CHOP`, signal প্রায় শূন্য |
| 24 | ADR ১৫০% শেষ, continuation setup | Score −2, বেশিরভাগ ক্ষেত্রে NO TRADE |
| 25 | Midnight open line | দিন বদলালে নতুন line, পুরনোটা থামে |
| 26 | HTF POI on LTF | HTF chart-এর সাথে দাম হুবহু মেলে |
| 27 | TP1 hit → BE | SL entry-তে সরে, label সবুজ |
| 28 | SL দূরত্ব দ্বিগুণ | Position size ঠিক অর্ধেক |
| 29 | Max hold পেরোলো | TIME_EXIT, আলাদা alert |
| 30 | JSON alert | Validator-এ pass করে |
| 31 | Intrabar on → bar close-এ শর্ত ভাঙল | Label মুছে যায়, alert যায়নি |
| 32 | ১০টা অদ্ভুত input combination | একটাও runtime error নেই |

**Sanity (১৫M, এক মাস):**

| অবস্থা | প্রত্যাশিত signal |
|---|---|
| Tier A only | ১০–৪০ |
| + Tier B (filter) | ৫–২৫ |
| + Tier C (regime + ADR + news) | **৩–১৫** |
| `sbOnly` + score ≥ 11 | ১–৬ |

> **সোনালী যাচাই:** module যোগ করলে signal সংখ্যা **কমতে হবে**। বাড়লে নিশ্চিতভাবে কোথাও একটা module নিজে signal emit করছে — সেটা bug, খুঁজে বের করো।

## C. Do NOT List — ২৬টা

**Layer ভাঙা (১–৮):**

1. ❌ FVG দেখে BUY
2. ❌ BOS দেখে BUY
3. ❌ CHoCH দেখে trade
4. ❌ Trendline break দেখে SELL — TLQ sweep ধরে state machine-এ পাঠাও
5. ❌ প্রতিটা উল্টো candle-কে OB বলা
6. ❌ Level-এর বাইরে প্রতিটা wick-কে sweep বলা
7. ❌ "Discount-এ আছে" দেখে buy
8. ❌ কোনো নতুন module থেকে সরাসরি signal emit

**Repaint (৯–১৪):**

9. ❌ ভবিষ্যতের data
10. ❌ Unconfirmed pivot-কে structure ধরা
11. ❌ চলমান bar-এর high/low দিয়ে swing বা trendline anchor
12. ❌ `request.security`-তে `[1]` বা `lookahead_off` বাদ দেওয়া
13. ❌ `request.security("W", open)` দিয়ে চলমান সপ্তাহের open
14. ❌ Alert-এ `barstate.isconfirmed` check বাদ

**State ও memory (১৫–২০):**

15. ❌ একই setup থেকে duplicate signal
16. ❌ Invalid zone চার্টে রেখে দেওয়া
17. ❌ `array.remove()` করার আগে drawing delete না করা
18. ❌ Array unbounded বাড়তে দেওয়া
19. ❌ প্রতি bar-এ নতুন drawing object তৈরি
20. ❌ প্রতি bar-এ প্রতিটা trendline-এ full validity loop

**Logic (২১–২৬):**

21. ❌ RR কম হলেও trade জোর করে বানানো
22. ❌ একই জিনিস দুই শ্রেণীতে score গোনা (sweep + trap = ১ পয়েন্ট, ২ নয়)
23. ❌ CISD-কে MSS-এর বিকল্প ধরা
24. ❌ SMT-র জন্য অসম্পর্কিত symbol
25. ❌ চাওয়া ছাড়া EMA/RSI/MACD যোগ করা
26. ❌ বলা ছাড়া `strategy()` বানিয়ে ফেলা

## D. Golden Rule

> **Indicator একটা ধারাবাহিকতা detect করবে, বিচ্ছিন্ন ঘটনা নয়।**

৪৮টা phase, ৩০+ module — কিন্তু signal-এর দরজা এখনো **একটাই**:

```text
Regime OK → Context → Liquidity → Sweep → Displacement → MSS
   → POI → Retrace → RR → Score → Time OK → ENTRY
```

নতুন প্রতিটা module এই পথের **একটা ধাপকে শক্ত করে** — নতুন কোনো পথ বানায় না।

**অস্পষ্ট কিছু পেলে অনুমান করবে না — spec maintainer-কে জিজ্ঞেস করবে।**

---

## E. পুরনো ডকুমেন্টের সাথে মিল

| এই ফাইল | আগে কোথায় ছিল |
|---|---|
| Phase 1–16 | `03_BUILD_PLAN.md` (v1.1) — হুবহু, শুধু গল্প সহজ করা |
| Phase 17–34 | `04_ADVANCED_BUILD_PLAN.md` (v1.0) — হুবহু |
| **Phase 35–48** | **নতুন — কোথাও ছিল না** |
| Pine v6 ফাঁদ (§4) | **নতুন** |
| Code skeleton (§5) | **নতুন** |
| শব্দকোষ (§2) | `02_improve_smc_ict.md` থেকে সহজ করে আনা |

03 আর 04 আর হালনাগাদ হবে না। নতুন কাজ শুধু এই ফাইলে।

---

**Document Version:** 2.0 (MASTER — একটাই ফাইল)
**Build target:** Pine Script v6, TradingView `indicator()`
**Phase গণনা:** 48 · **আনুমানিক সময়:** ~50 কর্মদিবস (Tier A একা ~15)

