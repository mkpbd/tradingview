# TradingView Indicator Development Specification

## SMC + ICT + CRT + TBS/TWS + Liquidity + Trap Trading Engine

**ডকুমেন্টের উদ্দেশ্য:** এই ডকুমেন্টটি একজন TradingView/Pine Script
developer-এর জন্য implementation specification।\
Developer-এর মূল কাজ হবে existing indicator থাকলে সেটি বুঝে, ভেঙে না ফেলে,
logic-first ভাবে SMC/ICT/CRT/TBS/TWS/liquidity/trap concepts integrate
করা।

> **Important:** এই document-এ trading concepts-গুলো source material
> অনুযায়ী specification হিসেবে দেওয়া হয়েছে। এগুলোকে guaranteed win-rate বা
> financial advice হিসেবে ধরা যাবে না। Indicator-এর প্রতিটি signal
> deterministic, non-repainting এবং historical/live উভয় অবস্থায় একই logic
> follow করবে।

------------------------------------------------------------------------

# 1. Developer Role

Developer-কে একই সাথে নিচের role অনুযায়ী কাজ করতে হবে:

-   Senior Pine Script / TradingView Indicator Developer
-   SMC / ICT logic implementer
-   CRT + TBS/TWS rules implementer
-   Liquidity & Trap detection engineer
-   Market Structure engineer
-   Non-repainting / anti-lookahead specialist
-   Signal-quality and false-signal reduction engineer
-   UI/visualization designer for TradingView

**মূল লক্ষ্য:** শুধু বেশি signal তৈরি করা নয়।\
লক্ষ্য হলো **কম কিন্তু logically filtered, explainable এবং high-quality
setup** তৈরি করা।

------------------------------------------------------------------------

# 2. Core Development Philosophy

Indicator যেন শুধু candle দেখেই Buy/Sell না দেয়।

প্রতিটি setup-এর আগে context বুঝতে হবে:

``` text
Market Context
      ↓
HTF Bias / Structure
      ↓
Liquidity Location
      ↓
POI / Zone
      ↓
Sweep / Breakout / Trap
      ↓
Displacement / Imbalance
      ↓
CRT Validation
      ↓
TBS / TWS Confirmation
      ↓
Entry Model
      ↓
SL / TP / RR Validation
      ↓
Final Signal
```

**Golden Rule:**

> Setup না হলে signal নয়।

একটি candle bullish হলেই Buy signal দেওয়া যাবে না এবং একটি candle
bearish হলেই Sell signal দেওয়া যাবে না।

------------------------------------------------------------------------

# 3. Market Structure Engine

## 3.1 Swing Detection

Indicator-এ robust swing detection থাকতে হবে:

-   Swing High
-   Swing Low
-   Higher High (HH)
-   Higher Low (HL)
-   Lower High (LH)
-   Lower Low (LL)

Swing detection-এর ক্ষেত্রে future candle ব্যবহার করা যাবে না।

### Structure States

``` text
BULLISH:
HH + HL

BEARISH:
LL + LH

RANGE:
No clear directional structure
```

------------------------------------------------------------------------

# 4. BOS / CHOCH / MSS

## 4.1 Valid BOS

Bullish BOS:

``` text
Price > Previous Swing High
AND
Candle CLOSE > Swing High
```

Bearish BOS:

``` text
Price < Previous Swing Low
AND
Candle CLOSE < Swing Low
```

শুধু wick দিয়ে level cross করলে BOS ধরা যাবে না।

### Invalid BOS

যদি:

``` text
High breaks level
BUT
Close returns below level
```

তাহলে এটাকে valid bullish BOS না ধরে liquidity sweep / failed breakout
হিসেবে classify করতে হবে।

একই logic bearish side-এও প্রযোজ্য।

------------------------------------------------------------------------

# 5. CHOCH / Change of Character

Bullish → Bearish:

``` text
Bullish structure
      ↓
Recent HL breaks
      ↓
Close below HL
      ↓
Potential bearish CHOCH
```

Bearish → Bullish:

``` text
Bearish structure
      ↓
Recent LH breaks
      ↓
Close above LH
      ↓
Potential bullish CHOCH
```

### Important Filter

CHOCH পেলেই entry নয়।

CHOCH-এর displacement quality পরীক্ষা করতে হবে।

যদি CHOCH move-এর ভিতরে meaningful imbalance/FVG না থাকে, signal-এর
confidence কমাতে হবে।

------------------------------------------------------------------------

# 6. Imbalance / FVG Engine

FVG-এর জন্য 3-candle structure ব্যবহার করতে হবে।

### Bullish FVG

``` text
Candle 1 High < Candle 3 Low
```

তাহলে মাঝের area:

``` text
C1 High → C3 Low
```

Bullish FVG।

### Bearish FVG

``` text
Candle 1 Low > Candle 3 High
```

তাহলে:

``` text
C3 High → C1 Low
```

Bearish FVG।

### FVG Quality

FVG শুধু detect করলেই হবে না।

প্রয়োজনে score করতে হবে:

-   Displacement strength
-   Candle body size
-   FVG size
-   HTF alignment
-   Liquidity sweep before FVG
-   Structure break
-   Zone location
-   Mitigation status

------------------------------------------------------------------------

# 7. Supply / Demand এবং Reaction Zone

Supply/Demand line হিসেবে নয়, **zone** হিসেবে তৈরি করতে হবে।

## Supply

Strong bearish reaction-এর origin area।

## Demand

Strong bullish reaction-এর origin area।

Zone-এর জন্য:

-   High
-   Low
-   Creation time
-   Direction
-   Strength
-   Touch count
-   Mitigation state
-   Broken/invalid state

store করতে হবে।

### Zone Rules

Zone:

``` text
Fresh
→ Tested
→ Mitigated
→ Broken
→ Invalid
```

একবার invalid হলে পুরনো zone বারবার signal generate করবে না।

------------------------------------------------------------------------

# 8. Liquidity Engine

Indicator-এর অন্যতম প্রধান module।

## 8.1 Buy-Side Liquidity

Liquidity সাধারণত:

-   Swing High-এর উপরে
-   Equal High-এর উপরে
-   Previous Day High
-   Previous Week High
-   Clear Resistance-এর উপরে

## 8.2 Sell-Side Liquidity

Liquidity সাধারণত:

-   Swing Low-এর নিচে
-   Equal Low-এর নিচে
-   Previous Day Low
-   Previous Week Low
-   Clear Support-এর নিচে

Source material-এ liquidity-কে traders-এর stop-order concentration
হিসেবে ব্যাখ্যা করা হয়েছে। তাই obvious levels-কে বেশি গুরুত্ব দিতে হবে।

------------------------------------------------------------------------

# 9. Liquidity Sweep বনাম Liquidity Run

এটি আলাদা module হিসেবে implement করতে হবে।

## Liquidity Run

Example bullish:

``` text
Resistance broken
+
Strong bullish candle
+
Close clearly above resistance
+
Acceptance above level
```

Classification:

``` text
REAL BREAKOUT / LIQUIDITY RUN
```

এখানে immediate short signal দেওয়া যাবে না।

## Liquidity Sweep

Example bullish-side sweep:

``` text
Price breaks above resistance
+
Long upper wick
+
Small/normal body
+
Close back below level
```

অথবা:

``` text
Break above
→
Next candle quickly returns below
```

Classification:

``` text
BUY-SIDE LIQUIDITY SWEEP
```

এখান থেকে bearish setup খোঁজা যাবে।

Bearish-side sweep-এর জন্য একই logic inverse হবে।

------------------------------------------------------------------------

# 10. Trap Trading Engine

Trap detect করার সময় নিচের components combine করতে হবে:

``` text
Liquidity
+
Key Level
+
Breakout
+
Retail FOMO
+
Rejection
+
Displacement
+
Structure
```

## Bull Trap

Potential condition:

``` text
Resistance
→
Liquidity above
→
Strong breakout
→
Retail FOMO
→
Failure / rejection
→
Close back below
→
Bearish confirmation
```

## Bear Trap

Potential condition:

``` text
Support
→
Liquidity below
→
Strong breakdown
→
Retail FOMO
→
Failure / rejection
→
Close back above
→
Bullish confirmation
```

------------------------------------------------------------------------

# 11. Pin Bar Trap Logic

Pin bar একা signal নয়।

### Bullish Pin Bar

প্রাধান্য পাবে যখন:

``` text
Downside liquidity swept
+
Important support/POI
+
Long lower wick
+
Close back upward
+
Bullish confirmation
```

### Bearish Pin Bar

``` text
Upside liquidity swept
+
Resistance/POI
+
Long upper wick
+
Close back downward
+
Bearish confirmation
```

------------------------------------------------------------------------

# 12. CRT Engine

CRT = Candle Range Theory model।

## 12.1 CRT Ranging Candle

প্রথমে একটি potential ranging candle identify করতে হবে।

Store:

``` text
CRT High (CRH)
CRT Low  (CRL)
CRT 50%
Direction
Timeframe
Creation time
Validity
```

### 50% Level

``` text
CRT_50 = (CRH + CRL) / 2
```

এটি TP1 / midpoint reference হিসেবে ব্যবহার করা যাবে।

------------------------------------------------------------------------

# 13. CRT Validity

Source অনুযায়ী CRT ranging candle valid হওয়ার জন্য previous liquidity /
OLP বা relevant POI interaction গুরুত্বপূর্ণ।

Potential validation:

``` text
Previous liquidity / OLP
OR
FVG
OR
IFVG
OR
Order Block
```

এগুলোর relevant tap/interaction থাকলে CRT validity বাড়বে।

### Candle Structure Filter

যদি ranging candle-এর body অতিরিক্ত বড় হয় এবং source rule অনুযায়ী
wick/body relationship invalid হয়, তাহলে CRT reject করতে হবে।

Developer implementation-এ এই threshold configurable রাখতে হবে।

------------------------------------------------------------------------

# 14. CRT Timeframe Mapping

CRT timeframe থেকে lower execution timeframe automatically map করতে হবে।

Source material-এ উল্লেখিত mapping:

  CRT Timeframe   Entry / Confirmation TF
  --------------- -------------------------
  15m             1m
  1H              5m
  4H              5m
  1D              15m

Developer-এর implementation configurable হওয়া উচিত যাতে future-এ mapping
পরিবর্তন করা যায়।

------------------------------------------------------------------------

# 15. TBS / TWS Engine

TS = Turtle Soup।

দুটি classification:

``` text
TBS = Turtle Body Soup
TWS = Turtle Wick Soup
```

## TWS

Level শুধু wick দিয়ে interact/sweep করলে:

``` text
TWS
```

## TBS

Level-এর বাইরে body/close acceptance হলে:

``` text
TBS
```

Source strategy অনুযায়ী preferred confirmation হলো **TBS** এবং TWS-কে
lower-quality / avoid condition হিসেবে treat করা হবে।

------------------------------------------------------------------------

# 16. TBS Detection

উদাহরণ bullish-side setup:

``` text
CRT High
      ↓
Lower TF
      ↓
Price attacks CRT High
      ↓
Body closes beyond/through relevant level
      ↓
TBS classification
      ↓
Model-1 confirmation
      ↓
Long setup
```

Bearish side-এ inverse।

### Important

শুধু wick touch = TWS।

Body close/acceptance = TBS।

First interaction যদি wick-based হয় এবং পরে body close হয়, developer-কে
event history preserve করতে হবে যাতে প্রথম interaction ভুলভাবে TBS হিসেবে
classify না হয়।

------------------------------------------------------------------------

# 17. Model-1 Entry Confirmation

CRT + TBS পেলেই সরাসরি trade signal নয়।

এর পরে **Model-1 candle** confirmation দরকার।

Model-1:

``` text
TBS confirmed
      ↓
Entry confirmation candle
      ↓
Candle CLOSE
      ↓
Entry
```

Entry ideally confirmed candle close-এর কাছাকাছি।

Configurable option:

``` text
Entry Mode:
1. Close
2. Small limit offset
```

------------------------------------------------------------------------

# 18. CRT Target Logic

Primary levels:

``` text
TP1 = CRT 50%
TP2 = CRT opposite boundary / relevant target
```

উদাহরণ:

Bullish CRT:

``` text
CRL ---------------- CRH
       ↑
      50%
```

TP1:

``` text
50% of CRT range
```

TP2:

``` text
CRT High / next liquidity / next structural target
```

Bearish setup-এ inverse।

------------------------------------------------------------------------

# 19. Stop Loss Logic

SL setup-এর invalidation point-এর বাইরে থাকবে।

### Liquidity Sweep Setup

Bearish:

``` text
SL = Sweep High + buffer
```

Bullish:

``` text
SL = Sweep Low - buffer
```

### CRT/TBS Setup

SL:

``` text
Beyond invalidation level
```

অর্থাৎ signal-এর logical invalidation point-এর বাইরে।

------------------------------------------------------------------------

# 20. Risk/Reward Filter

Final signal দেওয়ার আগে projected RR calculate করতে হবে।

Example:

``` text
Risk = abs(Entry - SL)
Reward = abs(TP - Entry)

RR = Reward / Risk
```

Default minimum:

``` text
RR >= 1.5
```

Configurable input:

``` text
Minimum RR = 1.5
```

RR requirement না পূরণ করলে:

``` text
NO TRADE
```

------------------------------------------------------------------------

# 21. HTF Bias Engine

Lower timeframe signal-এর আগে HTF context দেখতে হবে।

Example:

``` text
HTF Bullish
+
LTF Bullish liquidity sweep
+
Bullish CRT/TBS
=
High-quality Long candidate
```

যদি:

``` text
HTF Bearish
+
LTF Long
```

তাহলে signal score কমাতে হবে অথবা strict mode-এ reject করতে হবে।

------------------------------------------------------------------------

# 22. Multi-Timeframe Architecture

Indicator-এ আলাদা module:

``` text
HTF Analysis
LTF Analysis
Entry TF
```

যদি chart timeframe খুব ছোট হয়, relevant higher timeframe data overlay
করতে হবে।

Developer implementation-এ `request.security()` ব্যবহার করলে:

-   lookahead_off
-   confirmed HTF values
-   no future leak
-   realtime/historical consistency

অবশ্যই নিশ্চিত করতে হবে।

------------------------------------------------------------------------

# 23. Suggested HTF Overlay Framework

Default mapping configurable রাখতে হবে:

  Active Chart   HTF Context
  -------------- --------------
  1m             15m
  5m             1H
  15m            5H
  30m            configurable
  1H             configurable

HTF overlay components:

-   FVG
-   IFVG
-   Order Block
-   Breaker Block
-   Mitigation Block
-   CISD
-   Liquidity
-   Structure

------------------------------------------------------------------------

# 24. Breaker Block

Order Block invalidation-এর পরে role reversal detect করতে হবে।

Example:

``` text
Bullish OB
→
Bearish break
→
Zone flips
→
Potential Bearish Breaker
```

Opposite direction-এও একই logic।

Breaker zone-এর lifecycle maintain করতে হবে।

------------------------------------------------------------------------

# 25. Mitigation Block

Price যখন পূর্বের institutional zone-এ ফিরে আসে এবং imbalance/order flow
mitigate করে, সেটিকে mitigation context হিসেবে classify করা যেতে পারে।

Developer-কে zone state track করতে হবে:

``` text
Fresh
Partial Mitigation
Full Mitigation
Invalid
```

------------------------------------------------------------------------

# 26. IFVG

FVG যখন invalidated/broken হয়ে opposite role নেয়, তখন IFVG হিসেবে
classify করতে হবে।

Example:

``` text
Bullish FVG
→
Strong bearish break through FVG
→
Role reversal
→
Bearish IFVG
```

Retest + rejection হলে setup quality বাড়বে।

------------------------------------------------------------------------

# 27. CISD

CISD module-এর জন্য:

-   Relevant candle sequence
-   Directional shift
-   Close confirmation
-   Structure context
-   Liquidity context

track করতে হবে।

CISD standalone signal না হয়ে confirmation layer হিসেবে কাজ করবে।

------------------------------------------------------------------------

# 28. Trend Filter

Trendline / trend direction indicator-এর সাথে ব্যবহার করা যেতে পারে।

### Bullish

``` text
HH + HL
+
Bullish trendline
```

### Bearish

``` text
LL + LH
+
Bearish trendline
```

Trendline break নিজে final entry signal নয়।

Trendline break-এর পরে:

``` text
Liquidity
+
Structure
+
FVG/Displacement
+
Confirmation
```

দেখতে হবে।

------------------------------------------------------------------------

# 29. Support / Resistance

Support/Resistance:

**Line নয় → Zone**

Important rules:

-   Multiple touches
-   Equal High/Low
-   Previous rejection
-   Strong departure
-   Liquidity accumulation
-   Breakout
-   Retest
-   Role reversal

একই zone বারবার নতুন object তৈরি করবে না।

------------------------------------------------------------------------

# 30. Zone Flip Model

Three-step model:

``` text
1. Breakout
2. Retest
3. Refusal
```

Example:

``` text
Resistance
→
Strong bullish breakout
→
Resistance becomes Support
→
Weak pullback
→
Bullish refusal
→
Long
```

Opposite direction-এ:

``` text
Support
→
Bearish breakout
→
Support becomes Resistance
→
Retest
→
Bearish refusal
→
Short
```

Breakout-এর সময় displacement/imbalance থাকলে quality score বাড়বে।

------------------------------------------------------------------------

# 31. Corrective Pullback Filter

সব pullback tradable নয়।

## Avoid Pullback

যদি:

``` text
Strong bearish candles
+
Fresh imbalance
+
Strong displacement
```

তাহলে bullish trend-এর মধ্যে এমন pullback-এ blind long নেওয়া যাবে না।

## Better Corrective Pullback

যদি:

``` text
Mixed candles
+
Small internal pullbacks
+
No fresh strong imbalance
+
Existing imbalance mitigated
+
Liquidity available
```

তাহলে corrective pullback হিসেবে score বাড়বে।

------------------------------------------------------------------------

# 32. Strong Move Trap

Strong-looking move সবসময় strong institutional move নয়।

যদি বড় candle হয় কিন্তু:

``` text
No meaningful imbalance
```

তাহলে move-এর quality কম।

এমন অবস্থায়:

``` text
Do not chase
Wait for reversal / liquidity confirmation
```

------------------------------------------------------------------------

# 33. Signal Scoring System

Binary signal-এর বদলে score-based engine ব্যবহার করা ভালো।

Example:

  Condition                     Score
  -------------------------- --------
  HTF aligned                      +2
  Liquidity sweep                  +2
  TBS                              +2
  CRT valid                        +2
  FVG / displacement               +1
  BOS / CHOCH confirmation         +1
  Strong POI                       +1
  Trend alignment                  +1
  TWS only                         -2
  Against HTF                      -2
  Weak breakout                    -2
  RR \< minimum                Reject

Suggested threshold:

``` text
Score >= 7 → High Quality
Score 5-6 → Medium
Score < 5 → No Trade
```

Score system input হিসেবে configurable রাখতে হবে।

------------------------------------------------------------------------

# 34. Signal Types

Indicator-এর signal types আলাদা করতে হবে:

``` text
LONG
SHORT

LONG WATCH
SHORT WATCH

HIGH QUALITY LONG
HIGH QUALITY SHORT

TRAP
LIQUIDITY SWEEP
LIQUIDITY RUN
TBS
TWS
CRT
BOS
CHOCH
MSS
FVG
IFVG
```

সব event-এর জন্য একই BUY/SELL label ব্যবহার করা যাবে না।

------------------------------------------------------------------------

# 35. Signal Lifecycle

Signal state machine তৈরি করতে হবে:

``` text
DETECTED
   ↓
VALIDATING
   ↓
CONFIRMED
   ↓
ENTRY
   ↓
TP1 / TP2 / SL
   ↓
CLOSED
```

একই setup বারবার signal generate করা যাবে না।

------------------------------------------------------------------------

# 36. Duplicate Signal Prevention

একটি setup-এর unique ID থাকতে হবে।

Example:

``` text
setupId =
symbol
+
timeframe
+
setupDirection
+
zoneTime
+
CRTTime
```

একবার confirmed হলে একই setup-এর duplicate label/alert তৈরি করা যাবে না।

------------------------------------------------------------------------

# 37. Repainting নিষিদ্ধ

Developer অবশ্যই নিশ্চিত করবে:

-   Future candle ব্যবহার নয়
-   Lookahead নয়
-   Historical signal পরে disappear করবে না
-   Confirmed candle ছাড়া final signal নয়
-   HTF data properly confirmed
-   Swing detection-এর confirmation delay clearly handled
-   Real-time bar-এর intrabar fluctuation final historical signal-এর
    সাথে mismatch করবে না

যদি কোনো component inherently delayed হয়, UI-তে সেটা clear করতে হবে।

------------------------------------------------------------------------

# 38. Alert System

Alerts আলাদা category-তে দিতে হবে:

``` text
CRT Detected
CRT Validated
Liquidity Sweep
TBS Confirmed
TWS Detected
BOS
CHOCH
FVG Created
Zone Retest
Long Confirmed
Short Confirmed
TP1
TP2
SL
```

Final trade alert শুধু final confirmation-এ trigger হবে।

------------------------------------------------------------------------

# 39. Visual Design

Chart clutter কমাতে হবে।

### Recommended Colors

Developer user-configurable colors রাখবে।

Example categories:

``` text
Liquidity = one style
FVG = one style
IFVG = another style
OB = one style
Breaker = one style
CRT = highlighted range
TBS = strong marker
TWS = warning marker
LONG = bullish marker
SHORT = bearish marker
```

প্রতিটি object-এর label ছোট এবং meaningful হবে।

------------------------------------------------------------------------

# 40. Information Panel

Top-right বা configurable panel:

``` text
MARKET BIAS
HTF STRUCTURE
LTF STRUCTURE
LIQUIDITY
CRT STATUS
TBS/TWS STATUS
FVG STATUS
POI STATUS
SIGNAL SCORE
RR
TRADE STATUS
```

Example:

``` text
HTF Bias      : BULLISH
Structure     : HH/HL
Liquidity     : SSL Swept
CRT           : VALID
TBS           : CONFIRMED
FVG           : PRESENT
POI           : DEMAND
Score         : 8/10
RR            : 2.4
Signal        : HIGH QUALITY LONG
```

------------------------------------------------------------------------

# 41. Debug Mode

Developer অবশ্যই Debug Mode রাখবে।

Debug Mode ON করলে chart-এ দেখা যাবে:

``` text
Why CRT valid?
Why CRT invalid?
Which liquidity was swept?
Why TBS?
Why TWS?
Why BOS valid?
Why CHOCH invalid?
Which FVG?
Which POI?
Score breakdown
RR calculation
Signal rejection reason
```

এটি developer-এর testing এবং future bug fixing-এর জন্য অত্যন্ত গুরুত্বপূর্ণ।

------------------------------------------------------------------------

# 42. No-Trade Reason Engine

Signal না দিলেও indicator explain করবে।

Examples:

``` text
NO TRADE
Reason:
- TWS only
- HTF bearish
- No liquidity sweep
- CRT invalid
- No displacement
- RR below 1.5
- Weak breakout
- POI already mitigated
- Duplicate setup
```

এটি false-signal debugging-এ খুব useful হবে।

------------------------------------------------------------------------

# 43. Performance Requirements

Pine Script object limit মাথায় রাখতে হবে।

Developer:

-   unnecessary boxes delete/reuse করবে
-   old zones lifecycle manage করবে
-   arrays bounded রাখবে
-   duplicate objects avoid করবে
-   excessive `request.security()` calls avoid করবে
-   loops optimize করবে

------------------------------------------------------------------------

# 44. Input Settings

Inputs logical group-এ ভাগ করতে হবে:

``` text
01. Market Structure
02. BOS / CHOCH
03. Liquidity
04. SMC / ICT
05. FVG / IFVG
06. Order Block
07. Breaker
08. Mitigation
09. CRT
10. TBS / TWS
11. Trap Trading
12. Supply / Demand
13. Trendline
14. HTF Mapping
15. Entry Model
16. Risk / RR
17. Alerts
18. Visuals
19. Debug
```

প্রতিটি module ON/OFF করা যাবে।

------------------------------------------------------------------------

# 45. Developer Implementation Order

সবকিছু একসাথে code করা যাবে না।

## Phase 1 --- Foundation

Implement:

1.  Swing engine
2.  Market structure
3.  BOS
4.  CHOCH
5.  Liquidity

## Phase 2 --- SMC/ICT

6.  FVG
7.  IFVG
8.  Order Block
9.  Breaker
10. Mitigation
11. CISD

## Phase 3 --- CRT

12. CRT ranging candle
13. CRT validity
14. CRH
15. CRL
16. 50% level
17. CRT timeframe mapping

## Phase 4 --- TBS/TWS

18. Turtle Soup detection
19. TBS
20. TWS
21. Model-1 confirmation
22. CRT + TBS engine

## Phase 5 --- Trap

23. Liquidity sweep
24. Liquidity run
25. Bull trap
26. Bear trap
27. FOMO trap
28. Breakout rejection

## Phase 6 --- Trade Engine

29. Entry
30. SL
31. TP1
32. TP2
33. RR
34. Score
35. No-trade filter

## Phase 7 --- UI

36. Labels
37. Zones
38. Dashboard
39. Alerts
40. Debug mode

------------------------------------------------------------------------

# 46. Final Entry Logic

## Long

Minimum logical structure:

``` text
HTF bullish / acceptable context
        ↓
Sell-side liquidity identified
        ↓
Liquidity sweep / valid CRT event
        ↓
Bullish displacement / confirmation
        ↓
CRT valid
        ↓
TBS preferred
        ↓
Model-1 confirmation
        ↓
POI / FVG / Demand alignment
        ↓
RR >= Minimum RR
        ↓
LONG
```

## Short

``` text
HTF bearish / acceptable context
        ↓
Buy-side liquidity identified
        ↓
Liquidity sweep / valid CRT event
        ↓
Bearish displacement / confirmation
        ↓
CRT valid
        ↓
TBS preferred
        ↓
Model-1 confirmation
        ↓
POI / FVG / Supply alignment
        ↓
RR >= Minimum RR
        ↓
SHORT
```

------------------------------------------------------------------------

# 47. Strict Rejection Rules

Indicator-এর quality বাড়ানোর জন্য নিচের setup reject করতে হবে:

``` text
❌ Wick-only BOS
❌ TWS-only setup (Strict mode)
❌ No liquidity context
❌ Invalid CRT
❌ No confirmation
❌ Against strong HTF bias
❌ Weak displacement
❌ Fresh opposing FVG
❌ Strong opposing POI
❌ RR below minimum
❌ Duplicate signal
❌ Already mitigated/invalid zone
❌ Unconfirmed realtime signal
```

------------------------------------------------------------------------

# 48. Testing Requirements

Developer code শেষ করার পরে শুধু chart-এ কয়েকটি signal দেখে "working" বলা
যাবে না।

Testing করতে হবে:

### Historical

-   Trending market
-   Ranging market
-   High volatility
-   Low volatility
-   News spike
-   Gold
-   Silver
-   Forex
-   Crypto

### Timeframes

-   1m
-   5m
-   15m
-   30m
-   1H
-   4H

### Test Cases

1.  Valid CRT
2.  Invalid CRT
3.  TBS
4.  TWS
5.  Sweep
6.  Run
7.  BOS
8.  Fake BOS
9.  CHOCH
10. Fake CHOCH
11. FVG
12. FVG mitigation
13. IFVG
14. OB
15. Breaker
16. Zone flip
17. Trap
18. Duplicate signal
19. HTF/LTF mismatch
20. RR rejection

------------------------------------------------------------------------

# 49. Acceptance Criteria

Indicator তখনই complete ধরা হবে যখন:

-   [ ] No repaint
-   [ ] No lookahead
-   [ ] No future-data leakage
-   [ ] Valid/invalid BOS আলাদা
-   [ ] Valid/invalid CHOCH আলাদা
-   [ ] Liquidity Run vs Sweep আলাদা
-   [ ] CRT validity deterministic
-   [ ] CRT 50% calculated correctly
-   [ ] TBS vs TWS correctly classified
-   [ ] TWS-only setup strict mode-এ rejected
-   [ ] Model-1 confirmation কাজ করছে
-   [ ] HTF mapping কাজ করছে
-   [ ] FVG/IFVG lifecycle কাজ করছে
-   [ ] OB/Breaker/Mitigation lifecycle কাজ করছে
-   [ ] Duplicate signals blocked
-   [ ] RR filter কাজ করছে
-   [ ] No-trade reason visible
-   [ ] Debug mode available
-   [ ] Alerts correctly synchronized
-   [ ] Historical এবং realtime behavior consistent
-   [ ] Performance acceptable

------------------------------------------------------------------------

# 50. সবচেয়ে গুরুত্বপূর্ণ Developer Rule

**এই indicator-কে "Buy/Sell signal generator" হিসেবে develop করা যাবে
না।**

এটাকে develop করতে হবে একটি:

> **Context → Liquidity → Structure → POI → Confirmation → Risk → Signal
> Engine**

হিসেবে।

একটি signal-এর সাথে indicator-কে explain করতে হবে:

``` text
আমি কেন এই signal দিলাম?
```

এবং signal না দিলে:

``` text
আমি কেন signal দিলাম না?
```

দুটোরই উত্তর Debug Mode এবং No-Trade Reason Engine-এর মাধ্যমে দেখা যাবে।

------------------------------------------------------------------------

# 51. Source-Based Concept Notes

এই specification-এর CRT অংশে source material অনুযায়ী:

-   CRT ranging candle-এর validity-তে previous liquidity/OLP এবং
    FVG/IFVG/Order Block interaction গুরুত্বপূর্ণ।
-   CRT range-এর CRH/CRL এবং 50% midpoint track করা হয়।
-   15m CRT-এর জন্য 1m confirmation, 1H/4H-এর জন্য 5m এবং 1D-এর জন্য 15m
    confirmation mapping উল্লেখ করা হয়েছে।
-   Turtle Soup-এর দুই ধরন TBS (body) এবং TWS (wick); source strategy
    TBS-কে preferred confirmation হিসেবে উল্লেখ করে।
-   Model-1 confirmation-এর পরে entry, এবং CRT 50% ও opposite
    boundary/target ব্যবহার করার উদাহরণ দেওয়া হয়েছে।

Liquidity অংশে source material অনুযায়ী:

-   Swing High/Equal High/Resistance-এর উপরে buy-side liquidity এবং
    Swing Low/Equal Low/Support-এর নিচে sell-side liquidity হিসেবে
    context করা হয়েছে।
-   Strong close এবং acceptance-কে liquidity run/real breakout-এর দিকে
    এবং wick/rejection + return-কে liquidity sweep-এর দিকে classify করা
    হয়েছে।
-   Sweep-এর পরে immediate বা retest entry model এবং sweep extreme-এর
    বাইরে SL-এর ধারণা দেওয়া হয়েছে।

Market-structure অংশে source অনুযায়ী:

-   Close-confirmed BOS-কে valid এবং wick-only break-কে invalid/sweep
    হিসেবে আলাদা করা হয়েছে।
-   Corrective pullback এবং strong imbalance থাকা pullback-এর মধ্যে
    পার্থক্য করা হয়েছে।
-   CHOCH-এর quality বিচার করতে displacement/imbalance context গুরুত্বপূর্ণ
    হিসেবে বর্ণনা করা হয়েছে।

Support/Resistance অংশে:

-   Level-কে line নয়, zone হিসেবে ব্যবহার করা।
-   Multiple touch liquidity বাড়াতে পারে---তাই repeated touch-কে blindly
    "stronger" ধরে নেওয়া যাবে না।
-   Breakout → Retest → Refusal হলো zone-flip model-এর মূল sequence।
