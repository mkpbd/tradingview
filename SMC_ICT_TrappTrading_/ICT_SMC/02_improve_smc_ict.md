# SMC + ICT TradingView Indicator — Developer Brief

**Version:** 2.0  
**Audience:** Pine Script Developer (non-trader)  
**Primary Objective:** High-quality, logically sequenced, non-repainting SMC + ICT setups — maximum signal quantity নয়, maximum logical correctness.

---

## 0. How To Read This Document

If you are not a trader, don't worry. This document is organized in three layers:

1. **Business Rationale** — কেন এই concept exist করে (কেন code লিখছ)
2. **Precise Definition** — কী condition-এ valid, কী condition-এ invalid (কী লিখবে)
3. **Pseudo-code / Data Model** — কীভাবে implement করবে (কীভাবে লিখবে)

**Golden Rule (memorize this):**

> The indicator must detect a **sequence**, not isolated events.
>
> ❌ `FVG → BUY` — noise  
> ✅ `HTF Bias → Liquidity → Sweep → Displacement → MSS → POI → Retrace → RR Check → ENTRY`

---

## 1. Glossary — Domain Terms

| Term | সহজ ব্যাখ্যা |
|---|---|
| **BSL** | Buy-Side Liquidity — swing high-এর উপরে জমে থাকা retail stop-loss orders |
| **SSL** | Sell-Side Liquidity — swing low-এর নিচে জমে থাকা retail stop-loss orders |
| **BOS** | Break of Structure — trend continue signal |
| **CHoCH** | Change of Character — trend reversal-এর প্রথম warning (entry নয়) |
| **MSS** | Market Structure Shift — sweep + displacement + structure break |
| **FVG** | Fair Value Gap — 3-candle imbalance |
| **IFVG** | Inverted FVG — failed FVG উল্টো role নেয় |
| **OB** | Order Block — institutional entry candle |
| **BB** | Breaker Block — failed OB |
| **POI** | Point of Interest — entry zone (FVG/OB) |
| **OTE** | Optimal Trade Entry — Fibonacci 61.8%–78.6% zone |
| **EQH / EQL** | Equal High / Equal Low |
| **PDH / PDL** | Previous Day High / Low |
| **PWH / PWL** | Previous Week High / Low |
| **AMD** | Accumulation → Manipulation → Distribution |
| **CISD** | Change in State of Delivery |
| **SMT** | Smart Money Technique — correlated divergence |
| **Displacement** | Strong directional candle (body > ATR multiple) |
| **Sweep / Raid** | Liquidity level penetrate করে reversal |
| **Premium / Discount** | Range-এর upper / lower half |
| **Kill Zone** | Session-এর high-probability time window |
| **HTF / LTF** | Higher / Lower Timeframe |

---

## 2. Core Philosophy

### Business Rationale

Large institutional traders cannot buy thousands of lots at once. They need **counterparty** — retail traders on the opposite side.

Smart money play:

1. Push price to where retail stops are clustered (swing high/low)
2. Trigger those stops (sweep)
3. Opposite-side traders exit → liquidity frees up
4. Smart money enters → price moves in real direction

Therefore, the indicator must detect **sequence**:

```
HTF Bias → Liquidity Mapping → POI → Sweep → Displacement
   → MSS/CHoCH/BOS → FVG/OB → Retracement → Entry → SL → TP
```

### Developer Misunderstanding

❌ "Many signals = better indicator"  
✅ "Many signals = garbage indicator"

Target: **0–2 high-probability A+ setups per day**.

---

## 3. Data Model (Pine Script v5/v6)

Declare these **first**. Without these, state machine, zone lifecycle, duplicate prevention will break.

```pinescript
// SWING POINT
type Swing
    int     barIndex
    float   price
    bool    isHigh
    bool    confirmed

// ZONE (FVG / OB / Breaker / IFVG)
type Zone
    string  id              // "FVG_1234"
    string  kind            // "FVG" | "OB" | "BB" | "IFVG"
    string  direction       // "BULL" | "BEAR"
    float   top
    float   bottom
    int     createdBar
    string  state           // NEW | ACTIVE | TOUCHED | MITIGATED | FILLED | INVALID
    bool    consumed
    int     touchCount
    float   mitigationPct

// SETUP (Trade State Machine)
type Setup
    string  id
    string  direction       // "LONG" | "SHORT"
    string  state
    float   sweepLevel
    int     sweepBar
    float   mssLevel
    int     mssBar
    Zone    poi
    float   entryPrice
    float   slPrice
    float   tpPrice
    float   rr
    int     expireBar
    bool    signalEmitted
    int     score
```

---

## 4. Module Specifications

### 4.1 Market Structure (Swing High / Low)

**Rationale:** Market structure is the map. Without swing points you cannot locate price.

**Definition:**
- Swing High = bar's high > previous N and next N bars' highs (N default = 5)
- Swing Low = inverse
- Only **confirmed bars** — swing forms N bars after the pivot bar

```pinescript
// ❌ WRONG — repaints
if high > high[1] and high > high[2]
    swingHigh := high

// ✅ CORRECT — confirmed after N bars
isConfirmedSwingHigh = high[N] == ta.highest(high, 2*N+1)
```

---

### 4.2 HH / HL / LH / LL

**Rationale:** Trend needs comparison with previous swings.

| Label | Meaning |
|---|---|
| HH | Higher High — bullish |
| HL | Higher Low — bullish |
| LH | Lower High — bearish |
| LL | Lower Low — bearish |

Bullish: `HL → HH → HL → HH`  
Bearish: `LH → LL → LH → LL`

```pinescript
if newSwingHighConfirmed
    if na(lastSwingHigh) or price > lastSwingHigh
        label := "HH"
    else
        label := "LH"
    lastSwingHigh := price
```

---

### 4.3 BOS — Break of Structure

**Rationale:** Trend continuation signal. **Not an entry signal.**

**Definition:**

```
Previous confirmed Swing High
       ↓
Price breaks above (mode-dependent)
       ↓
Bullish BOS confirmed
```

**Wick vs Close Break:**

| Mode | Rule | Trade-off |
|---|---|---|
| Close Break (default) | `close > swingHigh` | High quality |
| Wick Break | `high > swingHigh` | 70%+ false signal |

---

### 4.4 CHoCH — Change of Character

**Rationale:** First hint of reversal. **Warning only — never entry.**

**Definition:** First structural break in the opposite direction of existing structure.

```pinescript
// ❌ WRONG
if chochDetected
    emitBuySignal()

// ✅ CORRECT
if chochDetected
    state := "CHOCH_WARNING"
```

---

### 4.5 MSS — Market Structure Shift

**Rationale:** Full reversal confirmation = sweep + displacement + structure break.

**Bullish MSS:**

```
1. SSL Sweep (low < SSL, close back inside)
       ↓
2. Bullish Displacement (body > ATR mult)
       ↓
3. Break previous internal high (close above)
       ↓
4. Bullish MSS confirmed
```

```pinescript
bullishMSS = sslSwept
    and isBullishDisplacement
    and close > lastInternalHigh

if bullishMSS
    setup.state    := "MSS_CONFIRMED"
    setup.mssLevel := lastInternalHigh
    setup.mssBar   := bar_index
```

---

### 4.6 Liquidity Engine

**Rationale:** Retail stops cluster above swing highs / below swing lows.

Detect:
- BSL (Buy-Side Liquidity)
- SSL (Sell-Side Liquidity)
- EQH / EQL
- PDH / PDL
- PWH / PWL

```pinescript
// EQH/EQL — configurable, ATR-normalized
eqhTolerance = atr * eqhToleranceMult   // default: 0.1
eqh = math.abs(high1 - high2) < eqhTolerance
```

---

### 4.7 Liquidity Sweep / Raid

**Rationale:** Stop hunt before real move.

**Bullish reversal — all 3 must be true:**

1. `low < sslLevel` (penetration)
2. `close > sslLevel` (close back inside)
3. Rejection structure — `(open - close) / (high - low) < 0.5`

```pinescript
// ❌ WRONG — 80% false signals
if low < sslLevel
    emitBullishSignal()

// ✅ CORRECT
if low < sslLevel and close > sslLevel
    setup.state := "LIQUIDITY_SWEPT"
    // Wait for displacement + MSS
```

---

### 4.8 Displacement Engine

**Rationale:** Institutional aggression — one strong candle.

```pinescript
bodySize  = math.abs(close - open)
rangeSize = high - low
bodyRatio = bodySize / rangeSize
atrValue  = ta.atr(14)

isDisplacement = bodyRatio >= bodyRatioMin        // 0.6
    and bodySize >= atrValue * atrMultiplier       // 1.2
    and direction matches intended move
```

**Warning:** Every large candle is not displacement. Large range + small body = indecision.

---

### 4.9 FVG — Fair Value Gap

**Rationale:** 3-candle imbalance, price later fills it.

**Bullish FVG:** `Candle1.High < Candle3.Low` → gap = `[C1.High, C3.Low]`  
**Bearish FVG:** `Candle1.Low > Candle3.High` → gap = `[C3.High, C1.Low]`

```pinescript
bullishFVG = low > high[2] and close[1] > open[1]
if bullishFVG
    array.push(zones, Zone.new(
        id        = "FVG_" + str.tostring(bar_index),
        kind      = "FVG",
        direction = "BULL",
        top       = low,
        bottom    = high[2],
        state     = "NEW"))
```

**Quality filters (optional, default ON):**
- Min gap size
- ATR-normalized gap
- Displacement required
- Structure break required
- Session filter
- HTF alignment

---

### 4.10 FVG Lifecycle

**Rationale:** A consumed FVG loses quality.

```
NEW → ACTIVE → TOUCHED → MITIGATED → FILLED / INVALID
```

```pinescript
// ❌ WRONG — signal every touch
if priceInFVG(fvg)
    emitSignal()

// ✅ CORRECT — one signal per zone
if priceInFVG(fvg) and not fvg.consumed
    emitSignal()
    fvg.consumed := true
```

---

### 4.11 IFVG — Inversion FVG

**Rationale:** Failed FVG becomes opposite role — buy zone turns resistance.

When FVG state → `INVALID`, immediately create new zone with `kind="IFVG"`, opposite direction.

---

### 4.12 Order Block (OB)

**Rationale:** Last opposite candle before institutional displacement.

**Bullish OB:** Last bearish candle before strong bullish displacement  
**Bearish OB:** Last bullish candle before strong bearish displacement

**Validation (all required):**
1. Next candle = displacement
2. Displacement breaks structure
3. (Preferred) Displacement creates FVG

---

### 4.13 Breaker Block

**Rationale:** Failed OB reverses role.

```
Bullish OB created
   ↓
Structure breaks (OB fail)
   ↓
OB state → INVALID
   ↓
Create new Zone: kind="BB", direction="BEAR"
   ↓
Price retests
   ↓
Bearish reaction → Breaker confirmed
```

**Never** label OB and Breaker identically.

---

### 4.14 Premium / Discount

**Rationale:** Institutions sell at premium, buy at discount.

```
Range High ────────
     PREMIUM (sell zone)
50% EQ ────────────
     DISCOUNT (buy zone)
Range Low ─────────
```

**Warning:** Premium/Discount is context, **not a trigger.**

---

### 4.15 OTE — Optimal Trade Entry

**Rationale:** Fib 61.8%–78.6% = institutional sweet spot. Never standalone.

```
Sweep → MSS → Displacement → FVG/OB → OTE retrace → Entry
```

---

### 4.16 Session Engine

**Rationale:**
- Asia = accumulation
- London = manipulation (sweep)
- NY = distribution (real move)

**Rules:**
1. Timezone configurable — never hard-code
2. DST-sensitive — use `America/New_York`, `Europe/London`
3. Kill Zone customizable

```pinescript
nySession = input.session("0930-1600", "NY Session", group="Sessions")
inSession = not na(time(timeframe.period, nySession, "America/New_York"))
```

---

### 4.17 HTF → LTF Framework

```
HTF Bias → HTF Liquidity → HTF POI
   → LTF Sweep → LTF MSS → LTF Entry
```

**NO lookahead:**

```pinescript
// ❌ WRONG
htfHigh = request.security(syminfo.tickerid, htfTF, high)

// ✅ CORRECT
htfHigh = request.security(syminfo.tickerid, htfTF, high[1],
                           lookahead=barmerge.lookahead_off)
```

---

### 4.18 Entry Engine — State Machine

**Rationale:** Every setup has a lifecycle. Without phases, you get duplicates + premature entries.

**Long Setup State Machine:**

```
IDLE
 ↓
CONTEXT_FOUND              (HTF bullish + POI identified)
 ↓
LIQUIDITY_SWEPT            (SSL taken)
 ↓
DISPLACEMENT_CONFIRMED     (bullish displacement)
 ↓
MSS_CONFIRMED              (internal high broken)
 ↓
POI_CREATED                (FVG/OB formed)
 ↓
RETRACE_WAIT               (price returning to POI)
 ↓
ENTRY_TRIGGERED            (price touched POI, RR ok)
 ↓
TRADE_ACTIVE
 ↓
TP / SL / INVALIDATED
 ↓
RESET
```

```pinescript
switch setup.state
    "IDLE":
        if htfBias == "BULL" and inDiscount
            setup.state := "CONTEXT_FOUND"

    "CONTEXT_FOUND":
        if sslSwept
            setup.state      := "LIQUIDITY_SWEPT"
            setup.sweepLevel := sslLevel

    "LIQUIDITY_SWEPT":
        if isBullishDisplacement
            setup.state := "DISPLACEMENT_CONFIRMED"

    "DISPLACEMENT_CONFIRMED":
        if close > internalHigh
            setup.state := "MSS_CONFIRMED"

    "MSS_CONFIRMED":
        if newFVG or newOB
            setup.poi   := newZone
            setup.state := "POI_CREATED"

    "POI_CREATED":
        if priceTouches(setup.poi)
            setup.state := "RETRACE_WAIT"

    "RETRACE_WAIT":
        entry = setup.poi.top
        sl    = setup.sweepLevel - buffer
        tp    = nextLiquidityTarget
        rr    = (tp - entry) / (entry - sl)
        if rr >= minRR
            setup.entryPrice := entry
            setup.slPrice    := sl
            setup.tpPrice    := tp
            setup.rr         := rr
            setup.state      := "ENTRY_TRIGGERED"
            emitLongSignal(setup)
```

---

### 4.19 Signal Quality Score

**Rationale:** Not all setups are equal.

| Condition | Score |
|---|---:|
| HTF alignment | +2 |
| Liquidity sweep | +2 |
| MSS | +2 |
| Strong displacement | +2 |
| FVG | +1 |
| Valid OB | +1 |
| Premium/Discount alignment | +1 |
| Kill Zone | +1 |
| SMT | +1 |
| Trap confirmation | +1 |

**Grades:**

| Score | Grade |
|---:|---|
| 0–3 | Weak — NO TRADE |
| 4–6 | Moderate — optional |
| 7–9 | Strong |
| 10+ | A+ |

**Rule:** Score cannot hide contradictions. HTF bearish + LTF bullish = −3 penalty. Below threshold = NO TRADE.

---

### 4.20 Stop Loss Logic

**Long:**
- Primary: `sweepLow - (atr * 0.2)`
- Fallback: OB bottom / structural invalidation

**Short:**
- Primary: `sweepHigh + (atr * 0.2)`
- Fallback: OB top / structural invalidation

```pinescript
buffer  = atr * 0.2
longSL  = sweepLow - buffer
shortSL = sweepHigh + buffer
```

---

### 4.21 Take Profit Logic

Priority:
1. Internal liquidity
2. Previous swing high/low
3. EQH / EQL
4. PDH / PDL
5. PWH / PWL
6. External liquidity
7. HTF liquidity

---

### 4.22 Minimum RR Filter

```pinescript
if rr < minRR    // default 1.5
    setup.state := "INVALIDATED"
    // Do not emit signal
```

---

### 4.23 Signal Expiration

```pinescript
if setup.state == "LIQUIDITY_SWEPT"
   and (bar_index - setup.sweepBar) > mssTimeout    // default 10
    setup.state := "INVALIDATED"

if setup.state == "MSS_CONFIRMED"
   and (bar_index - setup.mssBar) > retraceTimeout  // default 20
    setup.state := "INVALIDATED"
```

---

## 5. Worked Example — Bullish Setup (EURUSD 15M)

**HTF (4H):** Bullish bias, 4H range = 1.0800–1.1000 → Discount ✓  
**LTF (15M):** Entry chart

| Bar | Event | Detail |
|---:|---|---|
| 10 | SSL identified | Swing low @ 1.0820 |
| 25 | Sweep | Low = 1.0812, Close = 1.0835 (back inside) ✓ |
| 25 | State | `LIQUIDITY_SWEPT` |
| 26 | Displacement | Body = 22 pips, ATR = 15, ratio = 1.47 ✓ |
| 26 | State | `DISPLACEMENT_CONFIRMED` |
| 27 | MSS | Close 1.0848 > internal high 1.0842 ✓ |
| 27 | State | `MSS_CONFIRMED` |
| 28 | FVG | C1.High=1.0840, C3.Low=1.0845 → [1.0840, 1.0845] |
| 28 | State | `POI_CREATED` |
| 35 | Retrace | Price back to 1.0843 (50% FVG) |
| 35 | Entry/SL/TP | entry=1.0843, SL=1.0808, TP=1.0900 |
| 35 | RR | (1.0900−1.0843)/(1.0843−1.0808) = **1.63** ✓ |
| 35 | Score | HTF+2, Sweep+2, MSS+2, Disp+2, FVG+1, Discount+1, KZ+1 = **11 (A+)** |
| 35 | Signal | **LONG** |

---

## 6. Edge Cases — MUST Handle

| # | Edge Case | Action |
|---|---|---|
| 1 | Gap bars (weekend/open) | Do not ignore gaps in swing detection |
| 2 | Same bar sweep + MSS | Reject — wait next confirmed bar |
| 3 | Nested FVG | Track outer only |
| 4 | FVG + OB overlap | FVG priority |
| 5 | HTF mid-formation | Use last confirmed HTF candle |
| 6 | Setup mid-session | Skip Kill Zone filter |
| 7 | Data gap (missing bars) | Expire setup |
| 8 | EQH same bar | Exclude current bar's high |
| 9 | CHoCH then immediate BOS | Reset, new context |
| 10 | Multiple sweeps same level | First valid, ignore rest |
| 11 | Conflicting LONG + SHORT | Reject both |
| 12 | Signal emitted, no fill | Mark consumed, expire in 3 bars |

---

## 7. Parameter Tuning Guide

| Parameter | Default | Range | Impact |
|---|---|---|---|
| Swing length | 5 | 3–20 | Higher = fewer swings, less noise |
| BOS mode | Close | Close / Wick | Wick = 2–3× false signal |
| ATR mult (displacement) | 1.2 | 0.8–2.0 | Lower = more setup, less quality |
| Body ratio (displacement) | 0.6 | 0.5–0.8 | Higher = stricter |
| EQH/EQL tolerance | 0.1 × ATR | 0.05–0.3 × ATR | — |
| Min RR | 1.5 | 1.0–3.0 | Higher = fewer trades |
| MSS wait timeout | 10 bars | 5–30 | — |
| Retrace timeout | 20 bars | 10–50 | — |
| POI expire | 50 bars | 20–200 | — |
| Score threshold | 7 | 5–12 | — |
| FVG min size | 0.3 × ATR | 0.1–1.0 × ATR | — |

---

## 8. Repainting & Lookahead Audit

**Mandatory before delivery.**

- [ ] `request.security()` — `lookahead=barmerge.lookahead_off` + `[1]` offset
- [ ] No unconfirmed HTF candle
- [ ] Pivot confirmed N bars later, not same bar
- [ ] `var` state does not reset in realtime
- [ ] Historical signals = realtime signals
- [ ] Zone deletion/recreation logic correct
- [ ] Alert has `barstate.isconfirmed` check
- [ ] Current bar's high/low NOT used as swing

**Test procedure:**

```
1. Reload chart (F5) → history same? → repaint test
2. Trigger realtime signal → close bar → signal same? → realtime test
3. Switch HTF and back → signals same?
```

---

## 9. Testing Checklist

### Module-Level

**Swing:** last bar no confirm; EQH tolerance; gap bars  
**BOS:** close mode rejects wick; consecutive BOS handled  
**Sweep:** wick-only rejected; 10-bar MSS timeout; second sweep ignored  
**FVG:** formula correct; min size filter; 50% mitigation state; full fill INVALID  
**State Machine:** no second signal; expiry resets; LONG+SHORT rejected

### Integration

- [ ] **Test 1 (Bullish):** SSL sweep → disp → MSS → FVG → retrace → 1 LONG
- [ ] **Test 2 (Bearish):** BSL sweep → disp → MSS → FVG → retrace → 1 SHORT
- [ ] **Test 3 (Fake BOS):** Wick break → close back → NO signal
- [ ] **Test 4 (No MSS):** Sweep, no displacement → NO trade
- [ ] **Test 5 (Poor RR):** RR < 1.5 → NO trade
- [ ] **Test 6 (Repeated FVG):** 5 touches → 1 signal
- [ ] **Test 7 (Repaint):** Reload → history consistent

---

## 10. Alert Conditions

| Category | Alerts |
|---|---|
| Structure | Bullish BOS, Bearish BOS, Bullish MSS, Bearish MSS, CHoCH |
| Liquidity | BSL sweep, SSL sweep, EQH sweep, EQL sweep |
| Zones | FVG created, FVG mitigated, OB created, OB retest, Breaker created |
| Trade | LONG setup, SHORT setup, Entry, TP, SL, Setup invalidated |

**Rule:** Each alert fires **once**, unless repeat mode explicitly enabled.

```pinescript
if signalEmitted and not setup.signalEmitted
    alert("LONG: " + syminfo.ticker, alert.freq_once_per_bar_close)
    setup.signalEmitted := true
```

---

## 11. Development Priority

```
Phase 1  → Market Structure
Phase 2  → Liquidity
Phase 3  → BOS / CHoCH / MSS
Phase 4  → Displacement
Phase 5  → FVG / IFVG + Lifecycle
Phase 6  → OB / Breaker / Mitigation
Phase 7  → Premium / Discount / OTE
Phase 8  → HTF Context
Phase 9  → Session / Kill Zone
Phase 10 → Entry Engine (State Machine)
Phase 11 → SL / TP / RR
Phase 12 → Alerts
Phase 13 → Repaint / Lookahead Audit
Phase 14 → Historical + Realtime Testing
```

Each phase ends with unit test pass → next phase.

---

## 12. Do NOT Rules

1. ❌ Blindly combine every indicator/concept
2. ❌ Signal just because BOS exists
3. ❌ Signal just because FVG exists
4. ❌ Treat every opposite candle as OB
5. ❌ Treat every wick beyond level as sweep
6. ❌ Use future data
7. ❌ Use unconfirmed pivots as structure
8. ❌ Duplicate signals from same setup
9. ❌ Keep invalid zones active
10. ❌ Force trade when RR < minimum
11. ❌ Repainting HTF logic
12. ❌ Random EMA/RSI/MACD confluence
13. ❌ Over-optimize for historical appearance

---

## 13. Final A+ Setup — Long

```
HTF Bullish Context
   ↓
Price reaches Discount / Demand / Bullish POI
   ↓
Sell-Side Liquidity exists below
   ↓
SSL Sweep (close back inside)
   ↓
Bullish Displacement
   ↓
Bullish MSS
   ↓
FVG / OB created
   ↓
Retracement into valid POI
   ↓
RR >= 1:1.5
   ↓
Score >= threshold
   ↓
LONG
   ↓
SL below invalidation
   ↓
TP at next liquidity
```

Short = inverse.

---

## 14. Developer Handoff Checklist

### Before Coding
- [ ] Glossary read
- [ ] Business rationale read for each module
- [ ] Data Model understood, Pine types declared
- [ ] Worked example followed
- [ ] Edge cases read

### During Coding
- [ ] Module dependency order followed
- [ ] Each module unit-tested
- [ ] `var` state reset logic written
- [ ] Setup ID system implemented
- [ ] Zone lifecycle state machine written

### Before Delivery
- [ ] Repaint audit (realtime vs reload)
- [ ] Lookahead audit
- [ ] Duplicate signal test pass
- [ ] Expiry test pass
- [ ] RR filter test pass
- [ ] Integration Tests 1–7 pass
- [ ] Alerts fire once per setup
- [ ] Chart readability OK
- [ ] Input panel toggles for each module

---

## 15. Golden Rule

> **The indicator must detect a sequence, not isolated events.**

**❌ Wrong:**
```
FVG → BUY
BOS → BUY
RSI oversold → BUY
```

**✅ Correct:**
```
HTF Context → Liquidity → Sweep → Displacement → MSS
   → POI → Retracement → RR Validation → ENTRY
```

**Primary Objective:**  
High-quality, logically sequenced, non-repainting SMC + ICT setups — maximum signal quantity নয়, maximum logical correctness.

---

**Document Version:** 2.0  
**Contact:** Spec maintainer — ask questions when ambiguous, never guess.