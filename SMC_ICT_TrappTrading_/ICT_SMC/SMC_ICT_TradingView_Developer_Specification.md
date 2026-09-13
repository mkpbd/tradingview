# TradingView SMC + ICT Indicator — Developer Specification

## 1. উদ্দেশ্য

এই ডকুমেন্টের উদ্দেশ্য হলো একজন TradingView/Pine Script developer-কে পরিষ্কারভাবে বোঝানো:

- কোন SMC/ICT concept implement করতে হবে
- কোন condition-এ concept valid হবে
- কোন condition-এ signal invalid হবে
- কোন event আগে এবং কোন event পরে ঘটতে হবে
- কোথায় entry signal তৈরি হবে
- কোথায় SL/TP নির্ধারণ হবে
- কীভাবে repainting, lookahead এবং duplicate signal বন্ধ করতে হবে

> **Core principle:** Indicator বেশি signal দেবে—এটা লক্ষ্য নয়। লক্ষ্য হলো logically sequenced, non-repainting, high-quality setup detect করা।

---

# 2. Core Trading Philosophy

Indicator-এর মূল workflow:

```text
HTF Bias
   ↓
Liquidity Mapping
   ↓
Price reaches POI
   ↓
Liquidity Sweep / Raid
   ↓
Displacement
   ↓
MSS / CHoCH / BOS
   ↓
FVG / OB confirmation
   ↓
Retracement
   ↓
Entry
   ↓
SL
   ↓
Liquidity Target / TP
```

সব concept একসাথে mandatory করা যাবে না।

**Priority hierarchy:**

1. Market Context
2. Liquidity
3. Structure
4. Displacement
5. POI
6. Entry trigger
7. Risk/Reward
8. Target liquidity

---

# 3. Market Structure Engine

## 3.1 Swing High

একটি confirmed pivot high-কে Swing High হিসেবে mark করতে হবে।

Developer must use confirmed bars/pivots.

### Important

Current candle-এর incomplete information দিয়ে confirmed swing তৈরি করা যাবে না।

---

## 3.2 Swing Low

একইভাবে confirmed pivot low detect করতে হবে।

---

# 4. HH / HL / LH / LL

Confirmed swing sequence থেকে structure classify করতে হবে।

### Bullish

```text
HL → HH → HL → HH
```

### Bearish

```text
LH → LL → LH → LL
```

Labels:

- HH = Higher High
- HL = Higher Low
- LH = Lower High
- LL = Lower Low

---

# 5. BOS — Break of Structure

## Bullish BOS

Price confirmed previous swing high-এর ওপরে break করলে bullish BOS।

### Required

```text
Previous Swing High
       ↓
Price breaks high
       ↓
Bullish BOS
```

## Bearish BOS

Previous swing low break করলে bearish BOS।

### Important validation

শুধু wick cross-কে automatically BOS ধরা যাবে না।

Developer-কে configurable option রাখতে হবে:

- Wick Break
- Close Break

Default preferably **Close Break** for signal quality.

---

# 6. CHoCH

CHoCH হলো existing structure-এর বিপরীত দিকে প্রথম meaningful structural break।

### Example

Bullish structure:

```text
HH
  \
   HL
     \
      HH
       \
        ↓ HL breaks
       CHoCH
```

### Important

CHoCH = warning/transition.

CHoCH-কে standalone entry signal করা যাবে না।

---

# 7. MSS — Market Structure Shift

MSS signal-এর জন্য শুধু swing break যথেষ্ট নয়।

Preferred sequence:

```text
Liquidity Sweep
      ↓
Strong Displacement
      ↓
Structure Break
      ↓
MSS
```

### Bullish MSS

```text
SSL Sweep
   ↓
Bullish displacement
   ↓
Previous internal high breaks
   ↓
Bullish MSS
```

### Bearish MSS

```text
BSL Sweep
   ↓
Bearish displacement
   ↓
Previous internal low breaks
   ↓
Bearish MSS
```

---

# 8. Liquidity Engine

Indicator-এর অন্যতম প্রধান module।

Detect করতে হবে:

- Buy-Side Liquidity (BSL)
- Sell-Side Liquidity (SSL)
- Equal High (EQH)
- Equal Low (EQL)
- Previous Day High (PDH)
- Previous Day Low (PDL)
- Previous Week High (PWH)
- Previous Week Low (PWL)
- Major swing liquidity
- Internal liquidity
- External liquidity

---

# 9. BSL — Buy-Side Liquidity

সাধারণত:

- Previous swing highs-এর ওপরে
- Equal highs-এর ওপরে
- PDH/PWH-এর ওপরে

Potential stop/liquidity area হিসেবে mark করতে হবে।

---

# 10. SSL — Sell-Side Liquidity

সাধারণত:

- Previous swing lows-এর নিচে
- Equal lows-এর নিচে
- PDL/PWL-এর নিচে

Potential liquidity area হিসেবে mark করতে হবে।

---

# 11. EQH / EQL

Equal High এবং Equal Low-এর জন্য configurable tolerance রাখতে হবে।

Example:

```text
High A ≈ High B
      ↓
     EQH
      ↓
Potential BSL
```

Tolerance fixed hard-coded না করে input হিসেবে রাখা ভালো।

---

# 12. Liquidity Sweep / Raid

## Bullish Reversal Candidate

```text
SSL
────────────
     ↓
Price sweeps SSL
     ↓
Strong bullish rejection/displacement
     ↓
MSS
```

## Bearish Reversal Candidate

```text
BSL
────────────
     ↑
Price sweeps BSL
     ↓
Strong bearish displacement
     ↓
MSS
```

### Sweep validation

Sweep detect করার পর শুধু immediate wick reversal হলেই signal দেওয়া যাবে না।

Preferred confirmation:

1. Liquidity taken
2. Rejection/displacement
3. Structure shift
4. Entry zone তৈরি

---

# 13. Displacement Engine

Displacement = strong directional price delivery।

Possible validation:

- Candle body > configurable ATR multiple
- Body/range ratio threshold
- Consecutive directional candles
- Structure break
- FVG creation

Developer must avoid defining every large candle as displacement.

---

# 14. FVG — Fair Value Gap

3-candle model ব্যবহার করতে হবে।

## Bullish FVG

```text
Candle 1 High < Candle 3 Low
```

Gap:

```text
Candle 1 High
─────────────
     FVG
─────────────
Candle 3 Low
```

## Bearish FVG

```text
Candle 1 Low > Candle 3 High
```

---

# 15. FVG Quality Filter

সব FVG mark করা যাবে না।

Optional quality filters:

- Minimum gap size
- ATR normalized gap
- Displacement candle required
- Structure break required
- Session filter
- HTF alignment

### Preferred

```text
Displacement
    ↓
FVG created
    ↓
FVG becomes valid POI
```

---

# 16. FVG Mitigation

Price FVG-তে ফিরে এলে:

- First touch
- Partial mitigation
- 50% mitigation
- Full fill

track করা যেতে পারে।

Developer-কে state maintain করতে হবে:

```text
NEW
 ↓
ACTIVE
 ↓
MITIGATED
 ↓
FILLED / INVALID
```

একই FVG থেকে বারবার signal generate করা যাবে না unless explicitly configured.

---

# 17. IFVG — Inversion FVG

যখন FVG invalidates করে এবং opposite side-এ reaction zone হিসেবে কাজ করে।

Example:

```text
Bullish FVG
────────────
     ↓
Price breaks through
     ↓
FVG becomes resistance
     ↓
IFVG
```

IFVG-কে original FVG থেকে আলাদা state হিসেবে track করতে হবে।

---

# 18. Order Block

## Bullish OB

Strong bullish displacement-এর আগে শেষ meaningful bearish candle/zone।

## Bearish OB

Strong bearish displacement-এর আগে শেষ meaningful bullish candle/zone।

### OB validation

Preferred:

```text
OB
 ↓
Displacement
 ↓
Structure break
```

শুধু last opposite candle = automatically high-quality OB নয়।

---

# 19. Breaker Block

Failed OB-এর role reversal detect করতে হবে।

Example:

```text
Bullish OB
────────────
     ↓
Structure breaks
     ↓
OB invalidated
     ↓
Price retests
     ↓
Bearish reaction
     ↓
Breaker
```

---

# 20. Mitigation Block

Old institutional reaction/order area revisit এবং mitigation-এর concept আলাদা module হিসেবে রাখা হবে।

OB, Breaker এবং Mitigation-কে একই label দেওয়া যাবে না।

---

# 21. Premium / Discount

একটি valid dealing range নির্ধারণ করতে হবে:

```text
High
────────────
 PREMIUM
────────────
50% EQ
────────────
 DISCOUNT
────────────
Low
```

### Long preference

Discount area.

### Short preference

Premium area.

### Important

Premium/Discount একা entry trigger নয়।

---

# 22. OTE

Default Fibonacci OTE zone:

```text
61.8% → 78.6%
```

OTE শুধু entry context হিসেবে ব্যবহার হবে।

Preferred sequence:

```text
Liquidity Sweep
 ↓
MSS
 ↓
Displacement
 ↓
FVG/OB
 ↓
OTE retracement
 ↓
Entry
```

---

# 23. CISD

Change in State of Delivery detect করার জন্য price delivery-এর directional shift এবং relevant candle structure analyze করতে হবে।

CISD-কে standalone buy/sell signal না করে structure/price-delivery confirmation হিসেবে ব্যবহার করা উচিত।

---

# 24. SMT Divergence

Correlated instruments-এর মধ্যে divergence detect করার optional module।

Examples:

- Gold ↔ Silver
- EURUSD ↔ GBPUSD
- Related indices

Example:

```text
Asset A → New High
Asset B → Fails to make New High
        ↓
Potential bearish SMT
```

SMT standalone entry নয়।

---

# 25. AMD / Power of 3

Optional session model:

```text
Accumulation
     ↓
Manipulation
     ↓
Distribution
```

Indicator-এর session module-এর সঙ্গে integrate করতে হবে।

---

# 26. Session Engine

Support:

- Asia
- London
- New York
- London/NY overlap
- Custom Kill Zone

### Important

Timezone অবশ্যই configurable হতে হবে।

DST-sensitive timezone ব্যবহার করতে হবে।

Hard-coded Bangladesh/local time দিয়ে ICT session permanently define করা যাবে না।

---

# 27. HTF → LTF Framework

Top-down logic:

```text
HTF
 ↓
Bias
 ↓
HTF Liquidity
 ↓
HTF POI
 ↓
LTF Liquidity Sweep
 ↓
LTF MSS
 ↓
LTF FVG/OB
 ↓
Entry
```

### Example

15M entry chart:

```text
HTF = 1H / 4H
LTF = 15M / 5M
```

Indicator-এ user configurable HTF রাখতে হবে।

---

# 28. Recommended HTF Overlay

Optional presets:

```text
1M  → 15M
5M  → 1H
15M → 4H / 5H
30M → 4H
1H  → 4H / Daily
```

Developer should NOT hard-code only one mapping.

---

# 29. Supply & Demand

Supply/Demand module SMC/ICT-এর সঙ্গে integrate করা যাবে।

### Demand

Strong bullish displacement-এর origin area।

### Supply

Strong bearish displacement-এর origin area।

Quality factors:

- Freshness
- Displacement
- Structure break
- Liquidity interaction
- Number of touches
- HTF alignment

---

# 30. Trap Trading

Detect:

### Bull Trap

```text
Resistance
────────────
      ↑ breakout
      ↑
      ↓ reversal
      ↓
```

Potential sequence:

```text
BSL Sweep
 ↓
Failed breakout
 ↓
Bearish displacement
 ↓
MSS
 ↓
SHORT
```

### Bear Trap

```text
SSL Sweep
 ↓
Failed breakdown
 ↓
Bullish displacement
 ↓
MSS
 ↓
LONG
```

---

# 31. Entry Engine

## A+ Long Model

সব condition mandatory নয়, কিন্তু preferred sequence:

```text
1. HTF bullish / neutral-to-bullish context
        ↓
2. Price reaches valid Discount / Demand / Bullish POI
        ↓
3. SSL taken
        ↓
4. Bullish displacement
        ↓
5. Bullish MSS / CHoCH
        ↓
6. Valid FVG / OB
        ↓
7. Retracement
        ↓
8. LONG
```

## A+ Short Model

```text
1. HTF bearish / neutral-to-bearish context
        ↓
2. Price reaches Premium / Supply / Bearish POI
        ↓
3. BSL taken
        ↓
4. Bearish displacement
        ↓
5. Bearish MSS / CHoCH
        ↓
6. Valid FVG / OB
        ↓
7. Retracement
        ↓
8. SHORT
```

---

# 32. Signal Quality Score

Developer should implement a configurable scoring system rather than binary random confluence.

Example:

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

Example:

```text
0–3  = Weak
4–6  = Moderate
7–9  = Strong
10+  = A+
```

Score thresholds should be configurable.

> Score must not hide contradictory logic. A setup with strong bearish HTF bias should not become a long merely because many unrelated indicators add points.

---

# 33. Entry Confirmation Rules

### LONG

Minimum preferred:

```text
SSL Sweep
+
Bullish Displacement
+
Bullish MSS
```

Then:

```text
FVG / OB retracement
```

### SHORT

Minimum preferred:

```text
BSL Sweep
+
Bearish Displacement
+
Bearish MSS
```

Then:

```text
FVG / OB retracement
```

---

# 34. Stop Loss Logic

## Long

SL preferably:

```text
Below liquidity sweep low
```

or

```text
Below valid OB / structural invalidation
```

## Short

SL preferably:

```text
Above liquidity sweep high
```

or

```text
Above valid OB / structural invalidation
```

No arbitrary fixed SL unless user enables fixed-risk mode.

---

# 35. Take Profit Logic

Priority target:

1. Internal liquidity
2. Previous swing
3. EQH/EQL
4. PDH/PDL
5. PWH/PWL
6. External liquidity
7. HTF liquidity

---

# 36. Minimum Risk/Reward

Default minimum:

```text
RR >= 1:1.5
```

If projected TP cannot provide minimum RR:

```text
NO TRADE
```

Do not force a signal.

---

# 37. Trade State Machine

Developer MUST use state management.

Example LONG:

```text
IDLE
 ↓
CONTEXT_FOUND
 ↓
LIQUIDITY_SWEPT
 ↓
DISPLACEMENT_CONFIRMED
 ↓
MSS_CONFIRMED
 ↓
POI_CREATED
 ↓
RETRACE_WAIT
 ↓
ENTRY_TRIGGERED
 ↓
TRADE_ACTIVE
 ↓
TP / SL / INVALIDATED
 ↓
RESET
```

Same architecture for SHORT.

This is important to prevent:

- Duplicate signals
- Repeated entries
- State corruption
- Old setup triggering new trades

---

# 38. Signal Expiration

Every setup should have expiration.

Example:

```text
Sweep detected
 ↓
Wait N bars for MSS
 ↓
If no MSS
 ↓
Setup invalid
```

Likewise:

```text
MSS
 ↓
Wait N bars for retracement
 ↓
No retracement
 ↓
Setup expires
```

N must be configurable.

---

# 39. Repainting Prevention

This is mandatory.

Developer MUST audit:

- `request.security()`
- HTF data
- Lookahead
- Pivot confirmation
- Current candle state
- Historical vs realtime behavior
- Object deletion/recreation
- `var` state
- Signal reset logic

### Rules

Never use future data.

Never use confirmed future pivot information on historical bars as if it were known in realtime.

Use confirmed HTF values when required.

---

# 40. No Lookahead

HTF request must not leak future values.

Avoid:

```text
Future HTF candle
       ↓
Current LTF signal
```

Correct model:

```text
Confirmed HTF candle
       ↓
Current LTF decision
```

---

# 41. Real-Time Bar Handling

Developer must clearly separate:

- Historical confirmed bars
- Realtime open bar

If signal is allowed intrabar, it must be explicitly labeled/configured.

Default should prioritize confirmed-bar signals.

---

# 42. Duplicate Signal Prevention

Example problem:

```text
Same FVG
 ↓
Price touches 5 times
 ↓
5 BUY signals
```

This is NOT desired by default.

Each setup should have unique ID/state.

Preferred:

```text
Setup ID
 ↓
One entry
 ↓
Consumed
```

---

# 43. Zone Lifecycle

Every zone should have state:

```text
CREATED
 ↓
ACTIVE
 ↓
TOUCHED
 ↓
MITIGATED
 ↓
INVALIDATED
```

Optional:

```text
FILLED
```

Developer should not continuously recreate the same zone on every bar.

---

# 44. Visual Design

Chart should remain clean.

### Suggested labels

- HH
- HL
- LH
- LL
- BOS
- CHoCH
- MSS
- BSL
- SSL
- EQH
- EQL
- FVG
- IFVG
- OB
- BB
- POI
- LONG
- SHORT
- TP
- SL

Avoid excessive labels.

User should be able to toggle each module independently.

---

# 45. Settings Panel

Inputs should include:

## Structure

- Swing length
- BOS mode
- CHoCH enable
- MSS enable

## Liquidity

- BSL
- SSL
- EQH
- EQL
- Sweep sensitivity

## FVG

- Minimum size
- ATR filter
- 50% mitigation
- FVG expiration

## OB

- OB detection mode
- Fresh OB only
- OB expiration

## HTF

- HTF timeframe
- HTF FVG
- HTF OB
- HTF liquidity

## Sessions

- Session timezone
- Asia
- London
- New York
- Kill Zone

## Entry

- Minimum score
- MSS required
- Liquidity sweep required
- Displacement required
- RR minimum

## Risk

- SL mode
- TP mode
- Minimum RR

---

# 46. Alert Conditions

Alerts should exist for:

### Structure

- Bullish BOS
- Bearish BOS
- Bullish MSS
- Bearish MSS
- CHoCH

### Liquidity

- BSL sweep
- SSL sweep
- EQH sweep
- EQL sweep

### Zones

- FVG created
- FVG mitigated
- OB created
- OB retest
- Breaker created

### Trade

- LONG setup
- SHORT setup
- Entry
- TP
- SL
- Setup invalidated

Alerts should trigger only once per event unless repeat mode is explicitly enabled.

---

# 47. Important "Do NOT" Rules

Developer MUST NOT:

- Blindly combine every indicator/concept.
- Generate signal simply because BOS exists.
- Generate signal simply because FVG exists.
- Treat every opposite candle as OB.
- Treat every wick beyond a level as valid liquidity sweep.
- Use future data.
- Use unconfirmed pivots as confirmed structure.
- Generate duplicate signals from the same setup.
- Keep invalid zones active.
- Force trades when RR < minimum.
- Use repainting HTF logic.
- Add random EMA/RSI/MACD confluence unless explicitly requested.
- Optimize only for historical appearance.

---

# 48. Backtest/Validation Mindset

Although this is an `indicator()`, the developer should create simulated trade tracking internally if needed.

Track:

```text
Signal
Entry
SL
TP
RR
Result
Bars to result
Maximum favorable excursion
Maximum adverse excursion
```

This is for evaluation only.

Do NOT convert the indicator into `strategy()` unless explicitly requested.

---

# 49. Quality Control Test Cases

Developer must test at least:

### Test 1 — Bullish reversal

```text
SSL sweep
→ bullish displacement
→ MSS
→ FVG
→ retracement
→ LONG
```

Expected: One valid long signal.

### Test 2 — Bearish reversal

```text
BSL sweep
→ bearish displacement
→ MSS
→ FVG
→ retracement
→ SHORT
```

Expected: One valid short signal.

### Test 3 — Fake BOS

```text
Wick breaks structure
→ candle closes back
```

Expected: No BOS if Close Break mode is enabled.

### Test 4 — No MSS

```text
Liquidity sweep
→ no displacement
→ no MSS
```

Expected: No trade.

### Test 5 — Poor RR

```text
Valid setup
→ target too close
→ RR < 1:1.5
```

Expected: No trade.

### Test 6 — Repeated FVG touch

```text
Same FVG
→ multiple touches
```

Expected: No repeated signals from the same consumed setup.

### Test 7 — HTF repaint

Check realtime chart vs reload.

Expected:

```text
Signal history remains logically consistent.
```

---

# 50. Developer Implementation Priority

Development order MUST be:

```text
Phase 1
Market Structure
        ↓
Phase 2
Liquidity
        ↓
Phase 3
BOS / CHoCH / MSS
        ↓
Phase 4
Displacement
        ↓
Phase 5
FVG / IFVG
        ↓
Phase 6
Order Block / Breaker / Mitigation
        ↓
Phase 7
Premium / Discount / OTE
        ↓
Phase 8
HTF Context
        ↓
Phase 9
Session / Kill Zone
        ↓
Phase 10
Entry Engine
        ↓
Phase 11
SL / TP / RR
        ↓
Phase 12
Alerts
        ↓
Phase 13
Repaint / Lookahead Audit
        ↓
Phase 14
Historical + Realtime Testing
```

---

# 51. Final A+ Setup Logic

## LONG

```text
HTF Bullish Context
       ↓
Price reaches Discount / Demand / Bullish POI
       ↓
Sell-Side Liquidity exists
       ↓
SSL Sweep
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
LONG
       ↓
SL below invalidation
       ↓
TP at liquidity
```

## SHORT

```text
HTF Bearish Context
       ↓
Price reaches Premium / Supply / Bearish POI
       ↓
Buy-Side Liquidity exists
       ↓
BSL Sweep
       ↓
Bearish Displacement
       ↓
Bearish MSS
       ↓
FVG / OB created
       ↓
Retracement into valid POI
       ↓
RR >= 1:1.5
       ↓
SHORT
       ↓
SL above invalidation
       ↓
TP at liquidity
```

---

# 52. Golden Rule

Developer-এর জন্য সবচেয়ে গুরুত্বপূর্ণ rule:

> **Indicator should detect a sequence, not isolated events.**

Wrong:

```text
FVG → BUY
```

Wrong:

```text
BOS → BUY
```

Wrong:

```text
RSI oversold → BUY
```

Better:

```text
HTF Context
    ↓
Liquidity
    ↓
Sweep
    ↓
Displacement
    ↓
MSS
    ↓
POI
    ↓
Retracement
    ↓
RR Validation
    ↓
ENTRY
```

---

# 53. Final Acceptance Criteria

Indicator complete বলা যাবে শুধুমাত্র যখন:

- [ ] SMC structure works
- [ ] ICT liquidity works
- [ ] BOS/CHoCH/MSS logically sequenced
- [ ] Sweep detection works
- [ ] Displacement filter works
- [ ] FVG/IFVG lifecycle works
- [ ] OB/Breaker lifecycle works
- [ ] Premium/Discount works
- [ ] HTF context works
- [ ] Session logic works
- [ ] Entry state machine works
- [ ] SL/TP works
- [ ] RR filter works
- [ ] Duplicate signals prevented
- [ ] Expired setups reset
- [ ] Repainting audited
- [ ] Lookahead audited
- [ ] Historical/realtime consistency tested
- [ ] Alerts tested
- [ ] Chart remains readable
- [ ] No unnecessary indicators/confluence added

---

## Developer Instruction

**Do not rewrite everything blindly.**

First:

1. Design the architecture.
2. Define every state.
3. Define event order.
4. Define invalidation rules.
5. Implement module by module.
6. Test each module independently.
7. Test module interaction.
8. Perform repaint/lookahead audit.
9. Perform historical vs realtime comparison.
10. Only then finalize the indicator.

**Primary objective:**

> High-quality, logically sequenced, non-repainting SMC + ICT trade setups — not maximum signal quantity.
