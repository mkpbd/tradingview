# LQ-SD-PA v3.6 — User Manual (বাংলা)

> **Indicator:** Liquidity + S/D + Price Action [MTF] v3.6 · short name `LQ-SD-PA v3.6` · Pine Script v6
> **File:** `liqudity_trap_trading.v3.6.txt` · **লেখা:** 2026-10-03
> এটা একটা **rule engine** — chart পড়ে signal দেয়, কিন্তু trade-এর সিদ্ধান্ত আপনার। Educational tool, financial advice নয়। Live money-র আগে demo / Strategy Tester-এ calibrate করুন।

---

## সূচি

| § | বিষয় | কার জন্য |
|---|---|---|
| ০ | এক নজরে — engine কী করে | সবাই |
| ১ | Install ও প্রথম চালু | প্রথম দিন |
| ২ | Chart-এ কী দেখছেন — mark legend | প্রথম সপ্তাহ |
| ৩ | Dashboard — row by row | প্রতিদিন |
| ৪ | Verdict row — সব message-এর মানে | প্রতিদিন |
| ৫ | Signal label — tier, score, source | signal এলে |
| ৬ | Signal এলে কী করবেন — operating procedure | signal এলে |
| ৭ | Setup state machine — IDLE → ACTIVE | বোঝার জন্য |
| ৮ | Silver Bullet module | SB window-এ |
| ৯ | Liquidity Trap engine | ◬ label এলে |
| ১০ | Settings — symbol অনুযায়ী | setup-এর সময় |
| ১১ | Alerts ও journal line | setup-এর সময় |
| ১২ | Debug table | সমস্যা হলে |
| ১৩ | FAQ — সাধারণ বিভ্রান্তি | সমস্যা হলে |
| ১৪ | সীমাবদ্ধতা ও সতর্কতা | অবশ্যই পড়ুন |
| ১৫ | Quick reference card | print করে রাখুন |

---

## ০. এক নজরে

**Core loop (ICT / SMC):**

```
Liquidity sweep  →  POI tap (FVG / zone / HTF FVG)  →  Structure shift (MSS / CHoCH)  →  Retest  →  ENTRY
```

প্রতিটা signal **graded**: tier C / B / A / A+ এবং alignment score 0–100। তারপর **gate**: HTF bias, session, scheduled volatility window, regime (chop), cooldown, daily governance, day-of-week, dealing-range side, risk cap, min RR। সব gate পার হলে তবেই label।

**তিন রকম signal source:**

| Symbol | Source | কী |
|---|---|---|
| ◉ | **Setup machine** | primary path — sweep → POI → shift → retest সম্পূর্ণ chain |
| ◆ | **Silver Bullet** | machine-এর বিশেষ path, শুধু ৩টা SB window-এ (London 03–04, NY AM 10–11, NY PM 14–15 NY time) |
| (নাম) | **Engine candidates** | Demand/Supply 50% · CRT · TSoup · TL sweep · IB break · Doji rev · HTF CRT/TSoup · ◎ FEM · ◬ TRAP — একই tier/score দিয়ে graded |

**মনে রাখার তিনটা নিয়ম:**
1. Signal শুধু **closed bar**-এ। Dashboard live বদলায়, label বদলায় না।
2. Dashboard-এর "Alignment" সংখ্যা **idle bar-এর context**, signal-এর score নয়। Signal-এর score label-এ।
3. Default-এ শুধু **tier A ও A+** দেখায়। B/C দেখতে চাইলে study-র জন্য `tierMode` বদলান, trade-এর জন্য নয়।

---

## ১. Install ও প্রথম চালু

### ১.১ Paste

1. VS Code / Notepad-এ `liqudity_trap_trading.v3.6.txt` খুলুন → **Ctrl+A → Ctrl+C**।
2. TradingView → নিচে **Pine Editor** → নতুন indicator → editor-এ **Ctrl+A → Delete → Ctrl+V**।
3. Editor-এর **২ নম্বর লাইন** দেখুন: `// BUILD v3.6-b2 · 2026-10-03 …` — না থাকলে পুরনো code, আবার paste।
4. **Ctrl+S** (Save) → "Add to chart"। Chart-এর উপরে-ডানে dashboard header `LQ-SD-PA v3.6` দেখাবে।

> **CE10117 "too many tokens" এলে:** editor-এ পুরনো code আছে। Save না চাপলে console-এ আগের compile-এর error-ই থাকে। Step 2–4 আবার।

### ১.২ Chart

- **Timeframe: M5** (সব constant M5-এ tune করা)। M1 / M15 চলে, §১০.৪ দেখুন।
- **Bid chart** (OANDA, OKX, সব সাধারণ broker feed bid)। Spread indicator নিজে যোগ করে (`spreadIn`)।
- এক chart = এক symbol। Multi-symbol-এর জন্য আলাদা chart / layout।
- Indicator-এর **Settings → Inputs** খুলুন। ২০+ group আছে; প্রথম দিন শুধু **৩টা** বসান (নিচে)।

### ১.৩ প্রথম দিনের ৩টা setting

| Input (group) | কী বসাবেন | কেন |
|---|---|---|
| **Symbol profile** (General) | FX majors / Metals / Indices / Crypto | ৯টা ATR-scaled constant symbol অনুযায়ী preset হয় |
| **Spread (ticks)** (Risk / TP / SL) | §১০.১-এর সংখ্যা — session চলাকালে মাপা | long fill ask-এ, short stop ask-এ — বাস্তবের মতো |
| **Trade days** (Risk governance) | FX / metal / index `23456` · crypto 24/7 চাইলে `1234567` | শনি / রবি block (crypto-তে শনিবার `NO · day filter` দেখাবে) |

তারপর **এক সপ্তাহ শুধু দেখুন** — কোন setup আসে, verdict কী বলে, label কোথায় প্রিন্ট হয়। Trade পরে।

---

## ২. Chart-এ কী দেখছেন — mark legend

### ২.১ Line

| দেখতে | কী | মানে |
|---|---|---|
| লাল পাতলা step line | last swing **high** | buy-side liquidity (stop-এর পুল উপরে) |
| সবুজ পাতলা step line | last swing **low** | sell-side liquidity |
| লাল / সবুজ **মোটা** step line | protected high / low (external) | এটা ভাঙলে = **CHoCH**। Trend-এর "অবশ্যই ধরে রাখতে হবে" level |
| silver পাতলা | PDH / PDL | আগের দিনের high / low — pool |
| silver মোটা | PWH / PWL | আগের সপ্তাহের high / low — pool |
| রঙিন horizontal + label `Asia H` / `Lon L` / `NY H` | আগের session-এর high / low | **dashed + "raided"** = wick গেছে, close ফিরেছে → sweep · **dotted + "broken"** = close দিয়ে ভেঙেছে → accepted break |
| dotted লাল / সবুজ | EQH / EQL pool | equal highs / lows — engineered liquidity |
| dotted trendline (১ touch-এর পর solid) | dynamic trendline | dashed = ভেঙেছে |

### ২.২ ছোট mark (candle-এর উপরে / নিচে)

| Mark | কোথায় | মানে |
|---|---|---|
| ◆ সবুজ | নিচে | sell-side **swing sweep** (low wick গেছে, close উপরে) |
| ◆ লাল | উপরে | buy-side swing sweep |
| ◈ | উপরে / নিচে | EQH / EQL **pool** swept |
| ◇ | উপরে / নিচে | PDH / PWH বা PDL / PWL swept |
| ▿ / ▵ | উপরে / নিচে | session high / low **raided** |
| ✕ | | trendline break |
| ◦ সবুজ (নিচে) / লাল (উপরে) | | ◬ trap engine: retest done (long) / failed-break done (short) |

### ২.৩ Structure chip

| Chip | মানে | গুরুত্ব |
|---|---|---|
| **MSS** (গাঢ়) | sweep চলাকালে displaced external CHoCH | সবচেয়ে শক্তিশালী shift |
| **CHoCH** | external protected swing displaced close দিয়ে ভাঙল | trend বদলের প্রথম প্রমাণ |
| **BOS** | external continuation break | trend চলছে |
| iCHoCH / ibos (ধূসর, ছোট) | internal (5-bar pivot) | noise-ঘেঁষা; machine এগুলো দিয়ে shift করে না (default) |

### ২.৪ Box

| Text | কী | POI? |
|---|---|---|
| `FVG` / `FVG ·tested` (dotted, পাতলা) | chart-TF fair value gap | machine-এর retest anchor হতে পারে |
| `IFVG ▲` / `IFVG ▼` | inverted FVG — close দিয়ে ভাঙার পর উল্টো দিকে কাজ করে | হ্যাঁ |
| `DEMAND ★HP` / `SUPPLY ★HP` | high-probability S/D zone (break-এর সাথে তৈরি) | হ্যাঁ, grade T3 |
| (text নেই, সবুজ / লাল) | সাধারণ S/D zone | হ্যাঁ, T2 |
| `OB` | order block (displacement-এর আগের বিপরীত candle) | হ্যাঁ |
| `RB` | rejection block (swept pivot-এর wick) | হ্যাঁ |
| `BRK` / `MIT` | breaker / mitigation (ভাঙা zone উল্টে গেছে) | হ্যাঁ, BRK শক্তিশালী |
| `… ·spent` | ২ বার tested — আর POI নয় | **না** |
| `HTF 60 demand · fresh` / `·×1` (dashed) | HTF (auto: M5 → 60m) FVG POI | হ্যাঁ, T3 |
| `◎ FEM FVG · await retest` | fractal entry model-এর locked FVG | FEM-এর নিজের |
| `◉ CE 4131.8 · await retest` / `◉ anchor · await retest` | **machine stage 3** — এখানে limit বসবে | **সবচেয়ে গুরুত্বপূর্ণ box** |
| `◆ SB CE 4131.8 · await retest` (teal) | SB setup-এর anchor + teal CE line | SB limit price |
| `SB NY AM` (teal dotted) | ওই SB window-এর range | context |

> **Focus mode (default ON):** price থেকে 4 ATR-এর বেশি দূরের box স্বচ্ছ হয়ে যায়। Zone মুছে যায় না — শুধু আঁকা হয় না। `focusAtr` দিয়ে দূরত্ব বদলান।

### ২.৫ NEXT BUY / NEXT SELL label

উদাহরণ: `SELL T2 MIT 4143.295-4144.230 (0.08% above) ·fresh`

| অংশ | মানে |
|---|---|
| `BUY` / `SELL` | নিচের নিকটতম unspent demand / উপরের নিকটতম unspent supply |
| `T1` / `T2` / `T3` | grade — T3 = ★HP zone, BRK, বা HTF POI |
| `MIT` / `OB` / `RB` / `HTF` / `IFVG` | zone kind (S/D হলে কিছু লেখা থাকে না) |
| `4143.295-4144.230` | zone-এর band |
| `(0.08% above)` / `(INSIDE)` | close থেকে দূরত্ব, বা price band-এর ভেতরে |
| `·fresh` | এখনো test হয়নি |

**এটা signal নয়** — engine **কোথায় অপেক্ষা করছে** তার marker। Chain (sweep → POI → shift → retest) তবু চালাতে হবে।

### ২.৬ Trade plan (signal bar-এ)

| Line | Label |
|---|---|
| ধূসর dashed | `E 4131.800 · RR 1.8 (plan, not promise) · engine fill = next open · ≈120 units` |
| লাল dashed | `SL 4128.000` |
| সবুজ হালকা | `TP1 4135.600 · 50%` |
| সবুজ | `TP2 4139.400` |
| সবুজ গাঢ় | `TP3 4146.000` (liquidity target বা ≥ 3R) |

- `RR` = TP2 পর্যন্ত, **cost বাদ দিয়ে** (`costTicks` + spread)।
- `engine fill = next open` থাকলে entry পরের bar-এর open-এ (market)। না থাকলে CE limit — ওই bar-এই fill হয়েছে।
- `≈ units` তখনই, যখন `riskMoney` > 0।
- Trade শেষ হলে (TP2 / SL / expiry) ladder মুছে যায়।

### ২.৭ Background

| রং | কী |
|---|---|
| teal band | SB window চলছে (NY AM সবচেয়ে উজ্জ্বল) |
| লাল | scheduled volatility window (08:30 / 10:00 US data · Wed 14:00 FOMC) — entry block |
| বেগুনি / নীল / কমলা | Asia / London / NY killzone — default **OFF** (`paintKZ`) |

---

## ৩. Dashboard (উপরে-ডানে) — row by row

| Row | উদাহরণ | কীভাবে পড়বেন |
|---|---|---|
| **Header** | `LQ-SD-PA v3.6` · `RANGING` | **Regime:** TRENDING (দিকের রঙে) · TRANSITION · RANGING · **CHOP (লাল — entry block**, শুধু institutional sweep বা SB পার হয়) |
| **Bias 60** | `▼ Bear · D ▲ Bull · str ▲ Bull → —` | filter TF-এর EMA bias · daily EMA · HTF structure · **→ combined bias** (সব gate এটা পড়ে)। `—` = neutral → `neutralMode` ঠিক করে (default: chart-এর external structure follow) |
| **Struct · sweep** | `int ▲ ext ▼ · BSL valid` | internal / external structure direction · sweep in play + grade (weak / valid / strong / institutional) বা `no sweep` |
| **Range pos** | `Disc 33% · OTE buy` | dealing range-এ position: **Disc** < 50% (long allowed), **Prem** ≥ 50% (short allowed) · `·tight` = range < 2 ATR (P/D gate waived) · `·OTE buy / sell` |
| **Next demand / supply** | `T3 HTF · 0.5 ATR · fresh` | §২.৫-এর zone, দূরত্ব ATR-এ |
| **Trigger · FEM** | `CISD▼ · ◎ POI tap` | গত 10 bar-এর live trigger (MSS / CHoCH / BOS / CISD, দিকসহ) · FEM stage (idle → POI tap → shift✓ → FVG locked) |
| **◉ Setup L / S** | `idle / idle` | machine stage: `idle` · `SWEPT` · `AT POI` · `SHIFTED·await retest` · `ACTIVE` — §৭ |
| **Alignment** | `L 30 (C)  S 33 (B)` | **এই bar-এর** score + tier। Signal-এর score নয় (§০ নিয়ম ২) |
| **Session** | `off-hours · SB off-window` | killzone নাম · `⚠ vol window` · SB state (`◆ SB NY AM 23m left` / `◆ pre NY AM`) |
| **Trade** | `flat` / `order pending — fills next open` / `LONG 4131.8 SL 4128.0 ·TP1✓ ·SB` | tracked trade (indicator-এর নিজের book, আপনার account নয়) |
| **Verdict** | `NO · day filter · ADR 13% (early)` | §৪ |

---

## ৪. Verdict row — সব message-এর মানে

Verdict **সবসময় একটা কারণ** বলে। প্রথম যে কারণ block করছে, সেটাই দেখায়।

| Verdict | মানে | কী করবেন |
|---|---|---|
| `LONG signal` / `SHORT signal` | এই bar-এ signal | §৬ |
| `NO · entry slipped (close 0.8 ATR from the plan price)` | plan price থেকে close অনেক দূরে — fill fiction | skip |
| `NO · risk 2.1 ATR exceeds the cap` | structural stop খুব চওড়া (cap 1.5 ATR) | late — skip |
| `NO · reward blocked — only 1.2R net to the first opposing POI` | TP2-র আগেই বিপরীত POI, net RR < 1.5 | skip |
| `NO · L: gate: score 42 < 50` | setup stage 4 পৌঁছেছিল, final gate-এ score কম → SHIFTED-এ ফিরে retry | অপেক্ষা |
| `NO · L: gate: tier A below floor` | SB entry-র tier floor পার হয়নি | অপেক্ষা |
| `NO · L: gate: cooldown` / `volatility window` / `day filter` / `chop` / `daily signal limit` / `daily loss limit` | নামের gate | অপেক্ষা / দিন শেষ |
| `NO · L: gate: short narrative live` | বিপরীত দিকে setup / trade চলছে (`oneDir`) | অপেক্ষা |
| `NO · L: gate: premium — wrong side of the dealing range` | long কিন্তু price premium-এ | অপেক্ষা |
| `NO · L: gate: bias / session` | HTF bias বা killzone | অপেক্ষা |
| `NO · L: score 35 < 50 · AT POI` | active side-এর setup আছে, score কম | দেখুন — shift এলে score বাড়বে |
| `L: SHIFTED·await retest · shorts locked` | **setup live**, entry-র অপেক্ষা | CE limit বসানোর সময় (§৬.২) |
| `NO · day closed — 4 signals, 2 losses` | governance | আজ আর নয় |
| `LONG trade live · shorts locked` | tracked trade চলছে | manage |
| `NO · POI conflict — no tie-break` | demand ও supply 1 ATR-এর মধ্যে, bias নেই | অপেক্ষা |
| `NO · POI conflict resolved to longs` | conflict, long side জিতেছে | শুধু long |
| `NO · neutral bias` | `neutralMode = Block both sides` | অপেক্ষা |
| `NO · outside SB windows` | `sbOnly` ON | window-এর অপেক্ষা |
| `NO · day filter` | `tradeDays`-এ আজ নেই (NY calendar day) | crypto হলে `1234567` |
| `NO · chop` | regime CHOP | অপেক্ষা |
| `NO · volatility window` | news window | 15–20 মিনিট |
| `NO · score 40 < 50` | idle bar — কোনো setup নেই, context কম | স্বাভাবিক অবস্থা |
| `NO · no liquidity event` | কোনো sweep in play নেই | স্বাভাবিক — chain শুরুই হয়নি |
| `waiting` | sweep আছে, setup নেই, কিছু block করছে না | দেখুন |
| **suffix** `· ADR 130% (early) no-chase▼` | দিন ADR-এর 130% চলেছে · `(early)` = দিনের প্রথম ¼ · `no-chase▲/▼` = ওই দিকে chase করলে −10 ও A+ নেই | reversal setup ঠিক আছে, continuation নয় |

---

## ৫. Signal label — tier, score, source

```
A+ · 72 (base 60)        ← header: tier · score (SB bonus থাকলে base score)
◆ SB NY AM · CE A+       ← source line(s)
```

- **সবুজ, candle-এর নিচে** = LONG · **লাল, উপরে** = SHORT · **teal** = Silver Bullet entry।
- Header-এর tier = `finalTier` — label, counter, alert সব একই সংখ্যা পড়ে।
- `(base 60)` তখনই যখন SB context bonus (০–১৫) যোগ হয়েছে। **Gate base পড়ে**, তাই base ≥ `minScore` কিনা দেখুন।

### ৫.১ Tier

| Tier | শর্ত | trade? |
|---|---|---|
| **C** | শুধু trigger | না |
| **B** | trigger + (liquidity বা POI) | না — study |
| **A** | liquidity ≥ 10 + POI ≥ 10 + trigger + execution | হ্যাঁ |
| **A+** | A + HTF bias agree + killzone + RAW strong sweep (≥ 3) + সঠিক premium / discount | হ্যাঁ, priority |

Machine entry (◉) floor **A**; A+ পেতে লাগে: raw sweep ≥ 3, HTF agree, true MSS, সঠিক P/D side, engineered pool (session / EQ / PD), killzone, ADR chase নয়।

### ৫.২ Score (alignment, 0–100 — win probability নয়)

| Component | Max | কী কী |
|---|---|---|
| Context | 30 | HTF bias 10 (neutral 5) · external structure 10 · session 5 (Asia 2) · P/D 5 · ADR chase −10 |
| Liquidity | 20 | sweep in play 10 · engineered pool / session / PD 5 · raw grade ≥ 3 → 5 |
| POI | 20 | in zone 10 (near 5) · fresh 5 · OTE 5 |
| Trigger | 20 | MSS 12 / CHoCH 9 / BOS 5 (10 bar-এ linearly fade) · আলাদা CISD +8 · cap 20 |
| Execution | 10 | retest 5 · confirmation candle 5 |
| SB context | +15 | শুধু SB window-এ; gate-এ ধরা হয় না |

### ৫.৩ Source line

| Line | Source | Entry |
|---|---|---|
| `◉ SETUP A` | setup machine, confirmation candle | next open |
| `◉ SETUP A` + box-এ `◉ CE` | machine, CE limit | signal bar-এই fill (limit) |
| `◆ SB NY AM · CE A+` / `· edge A` | Silver Bullet, CE limit / proximal edge | signal bar |
| `Demand 50% +OTE` / `Supply 50%` | zone 50% tap + confirmation | next open |
| `IB break` | inside-bar breakout | next open |
| `Doji rev` | doji cluster reversal | next open |
| `TL sweep` | trendline sweep + confirmation | next open |
| `CRT` / `TSoup` | chart-TF CRT / turtle soup | next open |
| `HTF 60 CRT` / `HTF 60 TSoup` | HTF candle pattern (closed HTF bar) | next open |
| `◎ FEM 60→LTF` | fractal entry model | next open |
| `◬ TRAP LT-2+LT-5 · HIGH · failed-break✓` | liquidity trap (§৯) | next open |

এক bar-এ একাধিক source → এক label-এ একাধিক line। Long ও short একসাথে → rank (SB > machine > engine) যে জেতে সে থাকে, সমান rank হলে দুটোই বাদ।

---

## ৬. Signal এলে কী করবেন — operating procedure

### ৬.১ Session শুরুর আগে (৫ মিনিট)

1. **Bias row** — কোন দিক allowed? `→ —` হলে ext structure দেখুন।
2. **Regime** — CHOP হলে আজ machine প্রায় চুপ থাকবে (SB ছাড়া)।
3. **Next demand / supply** — কোথায় অপেক্ষা, কত ATR দূরে।
4. **নিজের economic calendar** — indicator-এর news window **fixed clock** (08:30 / 10:00 / Wed 14:00 NY)। সপ্তাহের বড় event অন্য সময়ে হলে `news1Ses`–`news3Ses` বদলান বা ওই সময় হাতে skip।
5. **Spread** — broker-এ এখনকার spread `spreadIn`-এর কাছাকাছি? না হলে বসান।

### ৬.২ `◉ CE … await retest` box এলে (stage 3)

Chain-এর sweep + shift হয়ে গেছে; engine CE-তে limit-এর অপেক্ষায়। দুটো উপায়:

- **(ক) আগে থেকে limit:** Buy limit = box-এর CE price (short: sell limit = CE)। SL = anchor box-এর নিচের edge − 0.25 ATR (short: উপরের edge + 0.25 ATR); sweep wick আরও দূরে হলে ওটা, কিন্তু 1.5 ATR-এর বেশি নয়। Label এলে SL / TP মিলিয়ে ঠিক করুন।
- **(খ) label-এর অপেক্ষা:** bar close-এ label → তখন E / SL / TP সব পাবেন। CE fill হলে price ততক্ষণে CE থেকে সরে গেছে — তখন market-এ ঢুকলে RR খারাপ হয়।

**(ক) doctrine, (খ) নিরাপদ।** Setup মরলে (`anchor FVG violated`, `retest window expired`) limit cancel করুন — dashboard Setup row `idle` হয়ে যাবে।

### ৬.৩ Label print হলে — ৩০ সেকেন্ডের checklist

| ✓ | প্রশ্ন | না হলে |
|---|---|---|
| ☐ | Tier **A বা A+**? | skip |
| ☐ | Header score (SB হলে **base**) ≥ `minScore`? | skip |
| ☐ | Verdict `LONG signal` / `SHORT signal` (suffix-এ `no-chase` আপনার দিকে নয়)? | skip |
| ☐ | Broker spread স্বাভাবিক? | skip |
| ☐ | পরের 15 মিনিটে high-impact news নেই? | skip |
| ☐ | আজ governance-এর ভেতরে (≤ 4 signal, < 2 loss)? | দিন শেষ |

**একটাও না → skip।** পরের setup আসবে।

### ৬.৪ Order

| Label-এ | Entry | SL | TP |
|---|---|---|---|
| `engine fill = next open` | পরের bar open-এ **market** (indicator-ও তাই ধরে) | label-এর SL | label-এর TP1 / TP2 / TP3 |
| CE (`◉ CE` box / `◆ SB … CE`) | limit **ইতিমধ্যে fill** (ক) — বা (খ) হলে price CE-র কাছে থাকলে limit, নাহলে skip | label-এর SL | label-এর TP |

Position size = `riskMoney ÷ (E − SL)` — label-এ `≈ units` (USD-quoted symbol-এ exact; অন্যগুলোতে আনুমানিক)।

### ৬.৫ Management (indicator-এর tracker যা করে, আপনিও তাই করুন)

| Event | Action |
|---|---|
| **TP1** (1R) | `tp1Pct`% (default 50%) close · SL → break-even + buffer (max(0.15 ATR, TP1-দূরত্বের 15%)) |
| **TP2** (2R বা প্রথম বিপরীত POI) | non-SB: বাকিটা close · SB বা `nonSbTp3` ON: SL 1R-এ lock, runner TP3-এ |
| **TP3** | runner close। SB-তে TP3 = নিকটতম বিপরীত session H/L / PDH-PDL / PWH-PWL / unspent POI যা ≥ TP2 দেয় |
| **SB window close**, TP1 unhit | পুরো exit (`sbTimeMode = Full`) বা partial + BE |
| **বিপরীত MSS / CISD** (SB) | runner exit |
| **80 bar** পার (`maxTrdBars`) | indicator trade "expired" ধরে — আপনার account-এ কিছু করে না; নিজে সিদ্ধান্ত নিন |

### ৬.৬ Post-trade

- "Any alert() function call" alert থাকলে `LQJRNL|…` line আসে → spreadsheet-এ paste (§১১.৩)।
- সপ্তাহ শেষে source (SB / MC / LT / ENG) অনুযায়ী expectancy দেখুন → দুর্বল source-এর engine OFF করুন।

---

## ৭. Setup state machine — IDLE → ACTIVE

প্রতি দিকের জন্য একটা machine (L ও S)। Dashboard `◉ Setup L / S` row।

| Stage | নাম | কী হয়েছে | পরের ধাপের clock |
|---|---|---|---|
| 0 | `idle` | কিছু নেই | — |
| 1 | `SWEPT` | quality ≥ 2 sweep in play, bias agree, lock free, chop নয় | POI tap: 20 bar (SB 12) |
| 2 | `AT POI` | zone / HTF POI tap (OTE না, default) | shift: 15 bar (SB 8) |
| 3 | `SHIFTED·await retest` | MSS / external CHoCH, shift-leg FVG anchor locked (`◉ CE` box) | entry: 20 bar (SB 10) |
| 4 | `ACTIVE` | entry fired, trade tracked | trade শেষ হলে idle |

**Fast path (`fastShift`, default ON):** stage 1 → 3 সরাসরি, যদি sweep চলাকালে displaced shift আসে (2022 model — raid-ই POI)। SB path সবসময় এভাবে।

**Invalidation reason** (debug table Machine row-এ দেখা যায়):

| Reason | মানে |
|---|---|
| `sweep undone` | close sweep wick-এর ওপারে — sweep ব্যর্থ, breakout |
| `sweep reclaim lost` | stage 1–2-এ close swept level-এর ভুল দিকে |
| `opposing displacement` | বিপরীত 1.2 ATR body (stage 3-এ anchor ধরে রাখলে মাফ) |
| `range swept both ways` | stage 1-এ বিপরীত দিকেও quality sweep |
| `POI violated (own anchor)` | zone anchor close দিয়ে ভাঙল |
| `HTF protected low / high broken` | HTF narrative শেষ |
| `SB window closed` | SB setup window-এর বাইরে |
| `sweep expired (no POI tap)` / `POI tap expired (no shift)` / `retest window expired` | clock শেষ |
| `anchor FVG violated` / `SB FVG violated` | retest-এ FVG close দিয়ে ভাঙল |
| `gate: …` | stage 4-এ final gate fail → stage 3-এ ফিরে retry |
| `conflict — higher-rank … won the bar` | একই bar-এ বিপরীত উঁচু rank |
| `entry slipped …` / `risk … exceeds the cap` / `reward blocked …` | viability gate fail → idle |
| `entry not tracked — tracker busy` | signal হয়েছে, কিন্তু আগের trade খোলা → counter-এ `untrk` |

---

## ৮. Silver Bullet module

### ৮.১ Window (NY time → Bangladesh UTC+6)

| Window | NY | BD গ্রীষ্ম (EDT, Mar–Nov) | BD শীত (EST, Nov–Mar) | min sweep quality |
|---|---|---|---|---|
| **London SB** | 03:00–04:00 | 13:00–14:00 | 14:00–15:00 | 3 (strong) |
| **NY AM SB** (priority) | 10:00–11:00 | 20:00–21:00 | 21:00–22:00 | 2 (valid) |
| **NY PM SB** | 14:00–15:00 | 00:00–01:00 (+1) | 01:00–02:00 (+1) | 3 |
| Arming grace | window-এর 15 মিনিট আগে থেকে | | | |

Killzone: Asia 20:00–00:00 NY (BD 06:00–10:00 গ্রীষ্ম) · London 02:00–05:00 (BD 12:00–15:00) · NY AM 07:00–10:00 (BD 17:00–20:00)। News window: 08:25–08:45 (BD 18:25–18:45) · 09:55–10:10 (BD 19:55–20:10) · Wed 13:55–14:35 (BD 23:55–00:35)।

Indicator-এর সব session input NY time-এ — TradingView নিজে NY DST সামলায়। শুধু আপনার ঘড়ির column বদলায়।

### ৮.২ SB path কীভাবে আলাদা

| বিষয় | সাধারণ machine | SB |
|---|---|---|
| Pool | যেকোনো swing | **engineered** — session H/L, EQH/EQL, PDH/PDL/PWH/PWL (Asia H/L window-এর ভেতরে গুনে) |
| Shift | MSS / external CHoCH | internal CHoCH বা CISD-ও চলে, যদি candle body ≥ 0.8 ATR |
| Anchor | shift-leg FVG বা zone | **শুধু clean displacement FVG** (≥ 0.10 ATR) |
| Entry | CE limit বা confirmation | **CE limit** (ask touch) · proximal edge শুধু pin / engulf / IFC / CISD-এ |
| P/D | live range | window open-এ **frozen** range |
| Clock | 20 / 15 / 20 | **12 / 8 / 10** |
| Tier floor | A | A (`sbMinTier` → A+) |
| Chop | block | **bypass** |
| প্রতি window | — | **১টা entry প্রতি দিক** |
| Window শেষ | — | unfilled setup মরে; TP1-unhit trade exit |

Chart-এ: teal band, `SB NY AM` box, teal `◆ SB CE` box + CE line, teal label `◆ SB NY AM · CE A+`, trade চলাকালে `◆ SB target 4146.0` line।

### ৮.৩ SB চলাকালে অন্য signal

`sbSuppress = Down-weight` (default): SB setup live থাকলে engine candidate-দের এক tier বেশি লাগে। `Suppress` = engine mute। Machine কখনো mute হয় না।

---

## ৯. Liquidity Trap engine (◬)

Breakout **trap** ধরে — ভাঙার পর ফাঁদে পড়া crowd-এর বিপরীতে। Default ON, class floor **HIGH** (score ≥ 70)।

| Pattern | দিক | গল্প |
|---|---|---|
| LT-1 | LONG | compression → displacement break → **retest + bullish confirmation** (genuine breakout) |
| LT-2 | SHORT | strong sellers displaced দূরে, weak buyers crawl back, level-এর উপরে দুর্বল poke |
| LT-3 | SHORT | নিচে lower-wick cluster pool বেঁচে আছে, উপরে breakout সন্দেহজনক |
| LT-4 | LONG | strong breakout-এর পর উপরে upper-wick cluster (buy-side pool) — support retest + confirmation |
| LT-5 | SHORT | breakout candle-এ লম্বা upper wick, দুর্বল body |
| LT-6 | SHORT | prior bear leg + compressed crawl + weak poke; **level-এর নিচে close বাধ্যতামূলক** |
| LT-7 | SHORT | breakout সরাসরি supply zone-এ ধাক্কা খেয়ে reject |

- Label: `◬ TRAP LT-2+LT-5 · HIGH · failed-break✓` — pattern, class, retest হয়েছে কিনা।
- ◦ mark: retest (সবুজ নিচে) / failed break (লাল উপরে)।
- **Veto (`ltVeto`):** trap WAITING থাকলে বিপরীত engine candidate mute; machine / SB নয়।
- Trap signal এখন সাধারণ engine candidate — একই tier / score / gate / risk cap পার হতে হয়।

---

## ১০. Settings — symbol অনুযায়ী

### ১০.১ প্রথম যা বসাবেন

| Input | EURUSD (5-digit) | XAUUSD (OANDA, tick 0.001) | NAS100 (OANDA, tick 0.1) | BTCUSDT.P (OKX, tick 0.1) |
|---|---|---|---|---|
| Symbol profile | FX majors | Metals / XAU | Indices | Crypto |
| Spread (ticks) — **session-এ মাপা** | ≈ 10 | ≈ 250–350 | ≈ 10–15 | ≈ 1 |
| Round-trip cost (ticks) | commission only (ECN 2–3 · spread-only broker 0) | commission only | 0 (spread-only) | 0–2 (taker fee ছোট) |
| Trade days | `23456` | `23456` | `23456` | `1234567` (weekend trade চাইলে) |
| Volume confirmation | OFF | OFF | OFF | **ON** (real volume) |
| HTF bias filter | 60 | 60 | 60 | 60 (240 শান্ত) |

**Spread মাপা:** London / NY session-এ TradingView-এর Buy / Sell button-এর পার্থক্য ÷ `syminfo.mintick`। Weekend quote 3–5× চওড়া — ওটা নয়।

### ১০.২ যা default-এ রাখুন (calibration ছাড়া বদলাবেন না)

| Input | Default | কেন |
|---|---|---|
| Show signal tiers | A and above | B / C edge নয় |
| Min alignment score | 50 | Strategy Tester-এ measure না করে বদলাবেন না |
| Max risk (ATR ×) / Min RR | 1.5 / 1.5 | |
| TP2 R multiple | 2.0 | |
| Max signals / losses per day | 4 / 2 | |
| Advanced tuning group | — | profile Manual না হলে ignore হয় |
| SB clocks, SB displacement | 12 / 8 / 10, 0.8 | |
| Structural break body | 0.5 | |

### ১০.৩ Chart পরিষ্কার করতে (display only — detection চলতে থাকে)

| Input | OFF করলে |
|---|---|
| Draw dynamic trendlines | trendline আর TL break mark যায় |
| Rejection blocks | RB box যায় |
| Track equal highs / lows | EQ dotted line যায় (pool তবু track হয়) |
| Session high / low lines | session line + label যায় (raid তবু detect হয়) |
| Label BOS / CHoCH / MSS | chip যায় |
| Draw live chart-TF FVGs | FVG box যায় |
| Focus distance | 4 → 3 করলে আরও কম box |

### ১০.৪ Timeframe

| TF | পরামর্শ |
|---|---|
| **M5** | default; সব constant এখানে tune |
| M15 | profile Manual → `Shift / CISD stays a live trigger` 6–8; `Regime: external-event memory` 30 |
| M1 | trigger look 12–15; spread-এর প্রভাব অনেক বেশি — `spreadIn` অবশ্যই |
| H1+ | killzone / SB অর্থহীন হয়ে যায়; `useKZ` off, SB off |

---

## ১১. Alerts ও journal line

### ১১.১ কীভাবে বানাবেন

Chart → Alert (ঘড়ি icon) → Condition: **LQ-SD-PA v3.6** → condition বাছুন → **Trigger: "Once per bar close"** (বাধ্যতামূলক — signal closed bar-এ) → Expiration open-ended।

### ১১.২ কোন alert

| Set | Condition | কখন |
|---|---|---|
| **Minimum** | `[SIGNAL] A+ LONG`, `[SIGNAL] A+ SHORT`, `[SIGNAL] A LONG`, `[SIGNAL] A SHORT` | trade-যোগ্য signal |
| Heads-up | `[SETUP] Structure shifted` | stage 3 — limit বসানোর সময় (§৬.২) |
| Trade | `[TRADE] TP1 hit`, `TP2 hit`, `SL hit` | management |
| SB | `[SB] ◆ Silver Bullet entry` | |
| **Detail feed** | **"Any alert() function call"** (condition list-এর একদম উপরে) | SB window / CE / tier / exit plan, LT pattern / score, SB BE / time exit / structure exit / setup gone, **journal line** |
| Context (ঐচ্ছিক) | `[LIQ] …`, `[POI] Price entered next demand / supply`, `[CTX] Volatility window started / ended`, `[LT] Trap setup detected` | শেখার জন্য |

মোট 30 alertcondition + alert() feed। Free plan-এ alert সংখ্যা সীমিত — Minimum set + Any alert() দিয়ে শুরু।

### ১১.৩ Journal line (spreadsheet-এর জন্য)

```
LQJRNL|XAUUSD|5|S|SB|A+|sc72|k4q3sh2w2|RANGING|E4131.800|SL4134.900|T24125.600|d2/0
```

| Field | মানে |
|---|---|
| `XAUUSD` · `5` | symbol · timeframe |
| `S` / `L` | দিক |
| `SB` / `MC` / `LT` / `ENG` | source: Silver Bullet / machine / trap / engine |
| `A+` | tier |
| `sc72` | score (header) |
| `k4` | pool kind: 1 swing · 2 EQ · 3 PD/PW · 4 session |
| `q3` | RAW sweep grade 1–4 |
| `sh2` | shift grade: 2 MSS · 1 CHoCH/CISD · 0 engine |
| `w2` | SB window: 1 London · 2 NY AM · 3 NY PM · 0 none |
| `RANGING` | regime |
| `E` `SL` `T2` | plan price |
| `d2/0` | আজ 2nd signal, 0 loss |

Alert → webhook / email → `|` দিয়ে split → column। সপ্তাহ শেষে source × tier × window অনুযায়ী outcome মেলান।

---

## ১২. Debug table (নিচে-ডানে, `showDbg` ON)

| Row | পড়বেন |
|---|---|
| `Sweeps raw/eff k` | `SSL raw2/eff4 k3 live` — raw = candle-এর নিজের grade, eff = MSS upgrade সহ, k = pool kind, live / stale |
| `Machine L / S` | stage + **শেষ invalidation reason** (§৭) — "কেন setup মরল" এখানে |
| `Score C/L/P/T/E` | Context / Liquidity / POI / Trigger / Execution — কোন component কম |
| `Counts · untrk` | A, A+, L, S সংখ্যা · TP1/TP2/TP3 · SL · exp (time-expired) · untrk (tracker busy) — **mechanical count, backtest নয়** |
| `◬ LT · ◆ SB · day` | trap machine state + pattern · শেষ trap reason · SB window / tag / entries · আজকের signal / loss · spread setting |

---

## ১৩. FAQ — সাধারণ বিভ্রান্তি

**Q. দিনের পর দিন signal নেই।**
Default filter কড়া: tier A/A+, score ≥ 50, bias agree, chop নয়, news নয়, governance। Verdict row পড়ুন — কোন gate। Study-র জন্য `tierMode = B and above` করে দেখতে পারেন কী বাদ যাচ্ছে; trade করবেন না।

**Q. Dashboard-এ score সবসময় 30–40, কখনো 50 হয় না।**
ওটা idle bar-এর context। Setup chain চললে (sweep + POI + shift + retest) এক bar-এ 60–80 হয়। Label-এর score-ই signal-এর score।

**Q. শনিবার BTC-তে `NO · day filter`।**
`tradeDays = 23456`। Crypto 24/7 চাইলে `1234567`।

**Q. Label হঠাৎ এল, পরে চলে গেল?**
Signal শুধু closed bar-এ — label মুছে যায় না। যা বদলায় তা dashboard আর last-bar drawing (NEXT level, anchor box, HTF POI box) — ওগুলো bar চলাকালে update হয়।

**Q. Label বলল CE fill, broker-এ fill হয়নি।**
Spread। `spreadIn` 0 হলে indicator bid দিয়ে fill ধরে। §১০.১-এর মান বসান — তখন long fill-এ ask লাগে।

**Q. PDH line broker-এর daily high-এর সাথে মেলে না।**
Daily bar-এর boundary data feed অনুযায়ী (OANDA 17:00 NY, OKX 00:00 UTC)। Indicator chart symbol-এর daily bar পড়ে, `[1] + lookahead_on` — history ও live একই।

**Q. Chart ভর্তি box / label।**
Focus mode ON আছে? §১০.৩-এর display toggle OFF করুন। Detection বদলায় না।

**Q. `NO · chop` অথচ trend দেখছি।**
Regime external pivot (12 bar) দিয়ে মাপে — M5-এ confirm হতে এক ঘণ্টা লাগে। `Regime: external-event memory` 40 → 60 করলে TRENDING বেশিক্ষণ থাকে। 6 ATR net move সবসময় chop-মুক্ত।

**Q. SB window-এ কিছুই হয় না।**
SB-র জন্য engineered pool লাগে (session H/L, EQ, PD) + window quality। Debug `Sweeps` row-এ `k` দেখুন — k1 (swing) হলে SB arm হবে না। `sbPoolPref` OFF করলে swing-ও চলে (doctrine নয়)।

**Q. Strategy Tester-এ চালাব?**
এটা indicator। Twin strategy file (`liqudity_trap_strategy.txt`) আর generator script (`scripts/mktwin.py`) এই folder-এ নেই — পেলে re-generate করতে হবে, v3.6-এর detection বদলেছে।

**Q. Repaint করে?**
না। সব detection `barstate.isconfirmed`-এ, HTF data `[1] + lookahead_on` (closed HTF bar)। Last bar-এর dashboard / drawing live — ওটা repaint নয়, preview।

---

## ১৪. সীমাবদ্ধতা ও সতর্কতা

1. **Counter backtest নয়।** Debug table-এর TP / SL count mechanical — intrabar order জানা নেই (stop ও target এক bar-এ লাগলে loss ধরা হয়), slippage নেই, swap নেই।
2. **Threshold measured নয়।** `minScore 50`, `minRR 1.5`, `maxRiskAtr 1.5`, governance 4/2, symbol profile — reasoned default। Strategy Tester calibration ছাড়া এগুলো মতামত।
3. **News window fixed clock।** Economic calendar নয়। NFP, CPI, central bank — নিজে দেখুন।
4. **London DST।** Session input NY time-এ; London-এর নিজের DST shift-এর সপ্তাহে (মার্চ / অক্টোবরের শেষ) London window এক ঘণ্টা সরে।
5. **Weekend gap।** Sunday open gap-এ sweep / structure misread হতে পারে; Monday Asia default-এ `tradeDays` block করে না (দিন 2), শুধু রবিবার NY time block।
6. **Spread input static।** News-এ spread 5× হলে indicator জানে না। §৬.৩ checklist-এর "spread স্বাভাবিক?" এজন্যই।
7. **One tracked trade.** Tracker busy থাকলে পরের signal `untrk` — label তবু আসে, outcome count হয় না।
8. **Drawing limit** 500 box / line / label — পুরনো zone মুছে নতুন আসে।
9. **Position size `≈ units`** USD-quoted symbol-এ exact; JPY pair / cross-এ conversion নিজে।

**Live-এর আগে:** এক সপ্তাহ observe → দুই সপ্তাহ demo + journal → source / tier / window অনুযায়ী expectancy → যা কাজ করে না OFF → তারপর ছোট size।

---

## ১৫. Quick reference card

```
┌─ SIGNAL এলে ──────────────────────────────────────────────────────────┐
│ label tier A/A+?  base score ≥ 50?  verdict "LONG/SHORT signal"?      │
│ spread normal?  news 15 min-এ নেই?  আজ ≤ 4 signal, < 2 loss?           │
│ → সব ✓: E/SL/TP label থেকে · "next open" = market · CE = limit         │
│ → TP1 50% + SL→BE · TP2 close (SB: runner TP3) · SB window শেষ = exit   │
└────────────────────────────────────────────────────────────────────────┘

MARK   ◆ swing sweep  ◈ EQ pool  ◇ PDH/PDL/PWH/PWL  ▵▿ session raid  ✕ TL break  ◦ trap retest
CHIP   MSS > CHoCH > BOS (external) · iCHoCH/ibos ধূসর = internal
BOX    ★HP S/D · OB · RB · BRK · MIT · IFVG · HTF POI · ◉ CE await retest (limit এখানে) · ·spent = বাদ
NEXT   BUY/SELL T1–3 kind band (দূরত্ব | INSIDE) ·fresh  — location, signal নয়
LABEL  সবুজ নিচে LONG · লাল উপরে SHORT · teal = SB · header "A+ · 72 (base 60)"

DASH   Bias → combined (— neutral) · Regime (CHOP লাল = block) · Setup L/S stage · Verdict = কারণ
STAGE  idle → SWEPT → AT POI → SHIFTED·await retest → ACTIVE   (clock 20/15/20 · SB 12/8/10)

SB     London 03–04 · NY AM 10–11 · NY PM 14–15 NY  (BD +10h গ্রীষ্ম / +11h শীত)
       engineered pool + displaced shift + clean FVG → CE limit · 1 entry/window/দিক

SET    profile · spreadIn (session-এ মাপা: EURUSD 10 · XAU 250–350 · NAS 10–15 · BTC 1) · tradeDays
ALERT  "Once per bar close" · A+/A LONG/SHORT · [SETUP] Structure shifted · [TRADE] · "Any alert()" feed
JRNL   LQJRNL|sym|tf|L/S|SB·MC·LT·ENG|tier|scNN|kK qQ shS wW|regime|E|SL|T2|dN/M
```
