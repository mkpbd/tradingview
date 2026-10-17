# LQ-SD-PA v3.8.5 — User Manual (বাংলা)

> **Indicator:** Liquidity + S/D + Price Action [MTF] v3.8.5 · short name `LQ-SD-PA v3.8.5` · Pine Script v6
> **File:** `liqudity_trap_trading.v3.8.5.txt` · BUILD line 2: `v3.8.5-b1 · 2026-10-16` · **লেখা:** 2026-10-17
> এটা একটা **rule engine** — chart পড়ে signal দেয়, trade-এর সিদ্ধান্ত আপনার। Educational tool, financial advice নয়। Live money-র আগে demo-তে journal রেখে calibrate করুন।
> v3.6 manual থেকে যা বদলেছে তা **◆ v3.8.5** দিয়ে চিহ্নিত।

---

## সূচি

| § | বিষয় | কার জন্য |
|---|---|---|
| ০ | এক নজরে — engine কী করে | সবাই |
| ১ | Install ও প্রথম চালু | প্রথম দিন |
| ২ | Timeframe, Bias TF, HTF — কোনটা কোথা থেকে আসে ◆ | প্রথম দিন |
| ৩ | Chart-এ কী দেখছেন — mark legend | প্রথম সপ্তাহ |
| ৪ | Dashboard — row by row | প্রতিদিন |
| ৫ | Verdict row — সব message-এর মানে ◆ | প্রতিদিন |
| ৬ | Signal label — tier, score, source | signal এলে |
| ৭ | Signal এলে কী করবেন — operating procedure | signal এলে |
| ৮ | Setup state machine — দুই রকম arm: sweep ও continuation ◆ | বোঝার জন্য |
| ৯ | Silver Bullet module | SB window-এ |
| ১০ | Liquidity Trap engine | ◬ label এলে |
| ১১ | Settings — symbol ও timeframe অনুযায়ী ◆ | setup-এর সময় |
| ১২ | Alerts, journal line, CE pre-fill line ◆ | setup-এর সময় |
| ১৩ | Debug table | সমস্যা হলে |
| ১৪ | FAQ | সমস্যা হলে |
| ১৫ | সীমাবদ্ধতা ও সতর্কতা | অবশ্যই পড়ুন |
| ১৬ | Quick reference card | print করে রাখুন |

---

## ০. এক নজরে

**Core loop (ICT / SMC):**

```
(ক) REVERSAL:      Liquidity sweep → POI tap → Structure shift (MSS / CHoCH) → shift-leg FVG → CE retest → ENTRY
(খ) CONTINUATION:  HTF POI tap (bias + HTF structure align) → Structure shift → shift-leg FVG → CE retest → ENTRY   ◆ v3.8.5
```

দুটো path একই machine চালায়। (খ)-তে sweep লাগে না — HTF POI নিজেই "internal range liquidity"। (খ) সর্বোচ্চ tier **A**; A+ শুধু raid-সহ (ক) path-এ।

প্রতিটা signal **graded**: tier C / B / A / A+, alignment score 0–100। তারপর **gate**: HTF bias, session, volatility window, regime, cooldown, daily governance, day-of-week, dealing-range side, risk cap, min RR। সব পার হলে তবেই label।

**Signal source:**

| Symbol | Source | কী |
|---|---|---|
| ◉ | **Setup machine** | primary path — (ক) বা (খ) |
| ◎ | **Continuation** (machine-এর ভেতরে) ◆ | dashboard / journal-এ আলাদা করে দেখায়; label `◉ SETUP A`-ই |
| ◆ | **Silver Bullet** | machine-এর বিশেষ path, ৩টা SB window-এ |
| (নাম) | **Engine candidates** | Demand/Supply 50% · CRT · TSoup · TL sweep · IB break · Doji rev · HTF CRT/TSoup · ◬ TRAP |

> ◆ v3.8.5: **FEM (Fractal Entry Model) বাদ।** ওর কাজ এখন continuation path করে — একই HTF POI → shift → FVG → retest, কিন্তু machine-এর CE limit, structural stop, gate-retry আর tracker সহ।

**মনে রাখার চারটা নিয়ম:**
1. Signal শুধু **closed bar**-এ। Dashboard live বদলায়, label বদলায় না।
2. Dashboard-এর "Alignment" সংখ্যা **এই bar-এর context**, signal-এর score নয়। Signal-এর score label-এ।
3. Default-এ শুধু **tier A ও A+** দেখায়। B/C study-র জন্য, trade-এর জন্য নয়।
4. ◆ Verdict row এখন **পরের ধাপ** বলে ("wait POI", "wait CE 4163.5"), score নয়। Score শুধু stage 4-এ gate fail হলে দেখাবে।

---

## ১. Install ও প্রথম চালু

### ১.১ Paste

1. VS Code / Notepad-এ `liqudity_trap_trading.v3.8.5.txt` খুলুন → **Ctrl+A → Ctrl+C**।
2. TradingView → নিচে **Pine Editor** → নতুন indicator → editor-এ **Ctrl+A → Delete → Ctrl+V**।
3. Editor-এর **২ নম্বর লাইন**: `// BUILD v3.8.5-b1 · 2026-10-16 · S-1 continuation arm …` — না থাকলে পুরনো code, আবার paste।
4. **Ctrl+S** → "Add to chart"। Dashboard header `LQ-SD-PA v3.8.5` দেখাবে।

> **CE10117 "too many tokens" এলে:** editor-এ পুরনো code থাকতে পারে — Save না চাপলে console আগের compile-এর error দেখায়। Step 2–4 আবার। তবু এলে `REVIEW_v3.8.4_ENTRY_BN.md` §7-এর cut order।

### ১.২ Chart

- **Bid chart** (OANDA, Binance, OKX — সব সাধারণ feed bid)। Spread indicator নিজে যোগ করে (`spreadIn`)।
- এক chart = এক symbol। Multi-symbol-এর জন্য আলাদা chart / layout।
- Timeframe M5 default। M15 চলে — §২ ও §১১.৪ **অবশ্যই** পড়ুন।

### ১.৩ প্রথম দিনের ৪টা setting

| Input (group) | কী বসাবেন | কেন |
|---|---|---|
| **Symbol profile** (General) | FX majors / Metals / Indices / Crypto | ৯টা ATR-scaled constant preset |
| **HTF bias filter** (HTF context) ◆ | M5 → `60` · **M15 → `240`** · M1 → `15` | §২ — chart TF-এর সাথে নিজে বদলায় না |
| **Spread (ticks)** (Risk / TP / SL) | §১১.১-এর সংখ্যা — session-এ মাপা | long fill ask-এ, short stop ask-এ |
| **Trade days** (Risk governance) | FX / metal / index `23456` · crypto 24/7 চাইলে `1234567` | শনি / রবি block |

তারপর **এক সপ্তাহ শুধু দেখুন**। Trade পরে।

---

## ২. Timeframe, Bias TF, HTF — কোনটা কোথা থেকে আসে ◆

এই indicator-এ **তিনটা আলাদা timeframe** কাজ করে। Chart TF বদলালে দুটো আপনা-আপনি বদলায় না।

| কী | কোথা থেকে | 5m chart | 15m chart | কোথায় ব্যবহার |
|---|---|---|---|---|
| **Chart TF** | আপনি যা select করেন | 5 | 15 | sweep, structure, FVG, zone, entry — সব detection |
| **Bias TF** | input `HTF bias filter` (default **60**)। নিয়ম একটাই: chart TF-এর **নিচে** নামতে পারে না | 60 | **60** (input বদলান → 240) | Dashboard "Bias 60" row · EMA-50 bias · HTF structure (BOS/CHoCH) · `htfB` → সব gate · continuation arm-এর শর্ত |
| **HTF (POI / CRT / TBS)** | input `HTF for CRT / TBS / POI` (default **Auto**) | 60 | **240** | `HTF 240 demand` box · continuation POI · HTF CRT / TSoup · NEXT level-এর `HTF` kind |

**Auto HTF mapping:** 1m→15 · 2m/3m→30 · 5m→60 · 10m→120 · **15m→240** · 30m→240 · 1h+→D।

**Dashboard "Bias 60" row পড়া** (উদাহরণ `▼ Bear · D ▲ Bull · str ▼ Bear → ▼ Bear`):

| অংশ | কী | কোথায় লাগে |
|---|---|---|
| `▼ Bear` | Bias TF-এর EMA-50 bias (last closed candle) | combined-এ |
| `D ▲ Bull` | Daily EMA bias | শুধু context + ◆ continuation chop-bypass (§৮.৩) |
| `str ▼ Bear` | Bias TF-এর **structure** (protected swing BOS / CHoCH) | combined-এ + continuation arm |
| `→ ▼ Bear` | **combined `htfB`** — EMA ও structure একমত হলে সেটা, না হলে `—` neutral | সব entry gate, arm gate, score |

`→ —` (neutral) হলে `neutralMode` ঠিক করে: default "Follow chart structure" = chart-এর external structure যে দিকে, সেই দিক।

**15m-এ কেন `240` দেবেন:** 15m chart-এ POI আসে 4H থেকে, bias আসে 1H থেকে — দুটো HTF আলাদা, confusing। `HTF bias filter = 240` দিলে bias আর POI একই 4H থেকে, আর 15m-এ 1H EMA-র whipsaw কমে। Row label তখন "Bias 240" দেখাবে।

---

## ৩. Chart-এ কী দেখছেন — mark legend

### ৩.১ Line

| দেখতে | কী | মানে |
|---|---|---|
| লাল / সবুজ পাতলা step line | last swing high / low | buy-side / sell-side liquidity |
| লাল / সবুজ **মোটা** step line | protected high / low (external) | ভাঙলে = **CHoCH** |
| silver পাতলা | PDH / PDL | আগের দিনের high / low — pool। **একবার trade হলে spent** (v3.7) |
| silver মোটা | PWH / PWL | আগের সপ্তাহের — pool |
| রঙিন horizontal + `Asia H` / `Lon L` / `NY H` | আগের session-এর high / low | **dashed + "raided"** = sweep · **dotted + "broken"** = accepted break |
| dotted লাল / সবুজ | EQH / EQL pool | equal highs / lows |
| dotted trendline (১ touch-এর পর solid) | dynamic trendline | dashed = ভেঙেছে |

### ৩.২ ছোট mark

| Mark | কোথায় | মানে |
|---|---|---|
| ◆ সবুজ / লাল | নিচে / উপরে | swing sweep (one-bar **বা multi-bar reclaim**, v3.6) |
| ◈ | | EQH / EQL pool swept |
| ◇ | | PDH / PWH বা PDL / PWL swept |
| ▿ / ▵ | | session high / low raided |
| ✕ | | trendline break |
| ◦ | | ◬ trap: retest / failed-break done |

### ৩.৩ Structure chip

| Chip | মানে |
|---|---|
| **MSS** (গাঢ়) | sweep চলাকালে displaced external CHoCH — সবচেয়ে শক্তিশালী |
| **CHoCH** | external protected swing displaced close দিয়ে ভাঙল |
| **BOS** | external continuation break |
| iCHoCH / ibos (ধূসর) | internal (5-bar pivot)। ◆ v3.8.5: displaced (body ≥ 1.2 ATR) + FVG রেখে গেলে machine-এর **shift** হিসেবে গোনে (`mcDispShift`) |

### ৩.৪ Box

| Text | কী | POI? |
|---|---|---|
| `FVG` / `FVG ·tested` | chart-TF FVG (≥ 0.15 ATR) | retest anchor হতে পারে |
| `IFVG ▲` / `IFVG ▼` | inverted FVG | হ্যাঁ |
| `DEMAND ★HP` / `SUPPLY ★HP` | high-probability S/D (displacement leg structure ভেঙেছে) | হ্যাঁ, T3 |
| (text নেই) | সাধারণ S/D | T2 |
| `OB` / `RB` / `BRK` / `MIT` | order block / rejection block / breaker / mitigation | হ্যাঁ |
| `… ·spent` | ২ বার tested | **না** |
| `HTF 240 demand · fresh` / `·×1` (dashed) | HTF FVG POI (§২) | হ্যাঁ, T3। ◆ **continuation path-এর arm point** |
| `◉ CE 4131.8 · await retest` / `◉ anchor · await retest` | **machine stage 3** — limit এখানে | **সবচেয়ে গুরুত্বপূর্ণ** |
| `◆ SB CE … · await retest` (teal) | SB anchor + CE line | SB limit |
| `SB NY AM` (teal dotted) | SB window range | context |

> ◆ v3.8.5: `◎ FEM FVG · await retest` box আর নেই।
> **Focus mode (ON):** 4 ATR-এর বেশি দূরের box স্বচ্ছ। Detection বদলায় না।

### ৩.৫ NEXT BUY / NEXT SELL label

`SELL T2 IFVG 81895.68-82108.00 (INSIDE) ·fresh` — নিকটতম unspent supply, grade T2, kind IFVG, band, price ভেতরে, test হয়নি। **Signal নয়**, location।

### ৩.৬ Trade plan (signal bar-এ)

| Line | Label |
|---|---|
| ধূসর dashed | `E 4131.800 · RR 1.8 (plan, not promise) · engine fill = next open · ≈120 units` |
| লাল dashed | `SL 4128.000` |
| সবুজ ×3 | `TP1 … · 50%` / `TP2 …` / `TP3 …` |

RR cost-সহ net। `engine fill = next open` = market পরের bar open-এ; না থাকলে CE limit ওই bar-এ fill। Trade শেষে ladder মুছে যায়।

### ৩.৭ Background

teal = SB window · লাল = scheduled volatility window · বেগুনি / নীল / কমলা = killzone (default OFF)।

---

## ৪. Dashboard (উপরে-ডানে) — row by row

| Row | উদাহরণ | কীভাবে পড়বেন |
|---|---|---|
| **Header** | `LQ-SD-PA v3.8.5` · `RANGING` | Regime: TRENDING · TRANSITION · RANGING · **CHOP (লাল, block)** — ◆ continuation setup তিন HTF align হলে পার হয় |
| **Bias 60** | `▼ Bear · D ▲ Bull · str ▼ Bear → ▼ Bear` | §২ |
| **Struct · sweep** | `int ▼ ext ▼ · SSL strong` | internal / external direction · sweep in play + grade, বা `no sweep` |
| **Range pos** | `Prem 77%` | Disc < 50% long allowed · Prem ≥ 50% short allowed · `·tight` · `·OTE` |
| **Next demand / supply** | `T2 MIT · 0.5 ATR ·fresh` | নিকটতম POI, দূরত্ব ATR-এ |
| **Trigger · ◎ HTF POI** ◆ | `BOS▼ · ◎ —` | গত 10 bar-এর trigger · ◎ slot: `—` কিছু নেই · `HTF dmd tap` / `HTF sup tap` price এখন HTF POI-র ভেতরে (arm হয়নি) · `cont L` / `cont S` continuation setup live · `off` = `contOn` বন্ধ |
| **◉ Setup L / S** | `idle / AT POI` | stage — §৮ |
| **Alignment** | `L 17 (C)  S 49 (C)` | এই bar-এর score + tier (signal-এর নয়) |
| **Session** | `Asia · SB off-window` | killzone · `⚠ vol window` · SB state |
| **Trade** | `flat` / `order pending — fills next open` / `LONG 4131.8 SL 4128.0 ·TP1✓` | tracked trade |
| **Verdict** | `S: AT POI ◎ · wait shift ▼ · ADR 11% (early)` | §৫ |

---

## ৫. Verdict row — সব message-এর মানে ◆

Verdict **সবসময় একটা কারণ বা পরের ধাপ** বলে। ক্রম: signal → plan kill → gate kill → active setup-এর পরের ধাপ → context block → idle কারণ।

### ৫.১ Signal ও plan

| Verdict | মানে | করবেন |
|---|---|---|
| `LONG signal` / `SHORT signal` | এই bar-এ signal | §৭ |
| `NO · entry slipped (close 0.8 ATR from the plan price)` | fill fiction | skip |
| `NO · risk 2.1 ATR exceeds the cap` | stop চওড়া | late — skip |
| `NO · reward blocked — only 1.2R net to the first opposing POI` | RR নেই | skip |

### ৫.২ Stage 4-এ gate fail (setup SHIFTED-এ ফিরে retry করে)

| Verdict | মানে |
|---|---|
| `NO · L: gate: score 42 < 50` | **এখানেই শুধু** score দেখায় — entry bar-এর আসল score |
| `NO · L: gate: tier A below floor` | SB tier floor |
| `NO · L: gate: cooldown` / `volatility window` / `day filter` / `chop` / `daily signal limit` / `daily loss limit` | নামের gate |
| `NO · L: gate: short narrative live` | বিপরীত setup / trade (`oneDir`) |
| `NO · L: gate: premium — wrong side of the dealing range` | long কিন্তু premium |
| `NO · L: gate: bias / session` | HTF bias বা killzone |

### ৫.৩ Setup live — পরের ধাপ ◆ v3.8.5

| Verdict | মানে | করবেন |
|---|---|---|
| `L: SWEPT · wait POI · T2 OB · 4.5 ATR ·fresh` | sweep হয়েছে; next demand 4.5 ATR দূরে — 20 bar-এ tap না হলে expire | দূরত্ব দেখুন; fastShift (MSS▲) এলে stage 3 |
| `S: AT POI ◎ · wait shift ▼` | POI-তে (◎ = continuation path); MSS▼ / CHoCH▼ / displaced iCHoCH▼ দরকার | দেখুন |
| `L: SHIFTED·await retest · wait shift-leg FVG` | shift হয়েছে, FVG এখনো হয়নি | অপেক্ষা |
| `L: SHIFTED·await retest · wait CE 4163.500` | **limit বসানোর সময়** (§৭.২) — box-এ একই CE | limit |
| suffix `· ⚠ bias blocks entry` | setup আছে, কিন্তু entry gate `biasOk` fail করবে (neutral bias + ext উল্টো, বা HTF উল্টো) | **ext / bias না বদলালে এই setup entry পাবে না** — অপেক্ষা করবেন না |
| suffix `· shorts locked` / `· longs locked` | `oneDir` lock | context |

### ৫.৪ Idle কারণ

| Verdict | মানে |
|---|---|
| `NO · day closed — 4 signals, 2 losses` | governance |
| `LONG trade live · shorts locked` | tracked trade চলছে |
| `NO · POI conflict — no tie-break` / `… resolved to shorts` | demand ও supply 1 ATR-এর মধ্যে; bias যে দিকে সেই দিক POI point রাখে |
| `NO · neutral bias` | `neutralMode = Block both sides` |
| `NO · outside SB windows` | `sbOnly` ON |
| `NO · day filter` | `tradeDays` |
| `NO · chop` | regime CHOP, কোনো exemption নেই |
| `NO · volatility window` | news window |
| `NO · SSL weak < arm Q2` ◆ | sweep হয়েছে কিন্তু grade 1 (reclaim দুর্বল) — arm হবে না। `BSL weak` short-এ |
| `NO · no liquidity event · wait sweep or HTF POI tap` ◆ | chain শুরু হয়নি। দুটো রাস্তা: sweep (reversal) বা HTF POI tap (continuation) |
| `waiting` | sweep আছে, setup নেই, কিছু block করছে না |
| suffix `· ADR 61% · (early) · no-chase▲` | দিন ADR-এর কত % চলেছে · দিনের প্রথম ¼ · ওই দিকে chase −10, A+ নেই |

> পুরনো `NO · score 25 < 50 · SWEPT` আর নেই — stage 1–3-এ score 50 হওয়া অসম্ভব ছিল, তাই সংখ্যাটা কিছু বলত না।

---

## ৬. Signal label — tier, score, source

```
A · 64                   ← tier · score (SB হলে "(base 52)")
◉ SETUP A                ← source
```

সবুজ নিচে LONG · লাল উপরে SHORT · teal = SB।

### ৬.১ Tier

| Tier | শর্ত | trade? |
|---|---|---|
| C | শুধু trigger | না |
| B | trigger + (liquidity বা POI) | না |
| **A** | liquidity ≥ 10 + POI ≥ 10 + trigger + execution | হ্যাঁ |
| **A+** | A + HTF agree + killzone + RAW strong sweep ≥ 3 + সঠিক P/D + engineered pool + true MSS + ADR chase নয় | হ্যাঁ, priority |

◆ Continuation entry **সবসময় A** (raid নেই → A+ হয় না)। Reversal entry-তে A+ সম্ভব।

### ৬.২ Score (0–100, alignment)

| Component | Max | কী |
|---|---|---|
| Context | 30 | HTF 10 (neutral 5) · ext structure 10 · session 5 (Asia 2, off-hours 0) · P/D 5 · ADR chase −10 |
| Liquidity | 20 | sweep in play 10 **বা ◆ continuation POI 10** · engineered pool 5 · raw ≥ 3 → 5 |
| POI | 20 | in anchor 10 (near 5) · fresh 5 · OTE 5 |
| Trigger | 20 | MSS 12 / CHoCH 9 / BOS 5, fade; stage 3-এ অন্তত অর্ধেক থাকে (v3.8.3) |
| Execution | 10 | retest 5 · confirmation 5 |
| SB context | +15 | শুধু SB window; gate base পড়ে |

### ৬.৩ Source line

| Line | Source | Entry |
|---|---|---|
| `◉ SETUP A` + `◉ CE` box | machine, CE limit | signal bar-এ fill |
| `◉ SETUP A` (box `◉ anchor`) | machine, confirmation candle | next open |
| `◆ SB NY AM · CE A+` | Silver Bullet | signal bar |
| `Demand 50%` / `Supply 50%` | zone tap + confirmation | next open |
| `IB break` / `Doji rev` / `TL sweep` / `CRT` / `TSoup` / `HTF 240 CRT` | engine | next open |
| `◬ TRAP LT-2+LT-5 · HIGH · failed-break✓` | trap | next open |

Reversal না continuation — label-এ লেখা নেই; **dashboard ◎ slot (`cont L`) আর journal tag `MCc`** বলে।

---

## ৭. Signal এলে কী করবেন — operating procedure

### ৭.১ Session শুরুর আগে (৫ মিনিট)

1. **Bias row** → combined কোন দিক? `—` হলে ext structure।
2. **Regime** — CHOP হলে reversal path চুপ; continuation তিন HTF align হলে চলে।
3. **Next demand / supply + HTF POI box** — কোথায় অপেক্ষা। ◆ HTF POI-র কাছে এলে ◎ slot `HTF dmd tap` দেখাবে — continuation arm হতে পারে।
4. **নিজের calendar** — news window fixed clock।
5. **Spread** চেক।

### ৭.২ `◉ CE … await retest` box / verdict `wait CE` এলে (stage 3)

- **(ক) আগে থেকে limit:** buy limit = CE। SL = anchor-এর নিচের edge − 0.25 ATR; sweep wick (reversal) বা HTF POI distal edge (continuation) আরও দূরে হলে ওটা, কিন্তু 1.5 ATR-এর বেশি নয়। ◆ "Any alert()" feed-এ **`LQCE|…|CE…|SLa…|SLr…`** line একই bar-এ আসে (§১২.৩) — ওখান থেকে সরাসরি।
- **(খ) label-এর অপেক্ষা:** bar close-এ label → E / SL / TP।

Setup মরলে (`anchor FVG violated`, `retest window expired`, `HTF POI violated`) limit cancel — Setup row `idle` হবে।

### ৭.৩ Label print হলে — checklist

| ✓ | প্রশ্ন | না হলে |
|---|---|---|
| ☐ | Tier A / A+? | skip |
| ☐ | Header score (SB হলে base) ≥ 50? | skip |
| ☐ | Verdict `LONG signal` / `SHORT signal`, suffix-এ `no-chase` আপনার দিকে নয়? | skip |
| ☐ | Spread স্বাভাবিক? পরের 15 মিনিটে news নেই? | skip |
| ☐ | আজ ≤ 4 signal, < 2 loss? | দিন শেষ |

### ৭.৪ Order

| Label-এ | Entry | SL / TP |
|---|---|---|
| `engine fill = next open` | পরের bar open-এ market | label-এর |
| CE | limit ইতিমধ্যে fill (ক), বা price CE-র কাছে থাকলে limit, নাহলে skip | label-এর |

Size = `riskMoney ÷ (E − SL)` → label-এ `≈ units`।

### ৭.৫ Management

| Event | Action |
|---|---|
| **TP1** (1R) | 50% close · SL → BE + buffer |
| **TP2** | non-SB: close · SB / `nonSbTp3`: SL 1R lock, runner TP3 |
| **TP3** | runner close (SB: liquidity target) |
| **SB window close**, TP1 unhit | exit (Full) বা stop → entry (Partial, size নিজে কমান) |
| **বিপরীত MSS / CISD** (SB) | runner exit |
| **80 bar** | indicator "expired" ধরে; নিজে সিদ্ধান্ত |

### ৭.৬ Post-trade

`LQJRNL|…` line spreadsheet-এ। সপ্তাহ শেষে source (SB / MC / **MCc** / LT / ENG) × tier অনুযায়ী expectancy। ◆ **MCc (continuation) আলাদা করে মাপুন** — নতুন path, এখনো measured নয়।

---

## ৮. Setup state machine — দুই রকম arm ◆

### ৮.১ Stage

| Stage | নাম | কী হয়েছে | clock |
|---|---|---|---|
| 0 | `idle` | — | — |
| 1 | `SWEPT` | (ক) quality ≥ 2 sweep in play, bias agree, lock free · (খ) continuation arm একই bar-এ stage 2-তে চলে যায় | 20 bar (SB 12) |
| 2 | `AT POI` | zone / HTF POI tap | 15 bar (SB 8) |
| 3 | `SHIFTED·await retest` | MSS / external CHoCH / ◆ displaced iCHoCH+FVG; shift-leg FVG anchor (`◉ CE` box) | 20 bar (SB 10) |
| 4 | `ACTIVE` | entry, trade tracked | trade শেষ হলে idle |

**Fast path (`fastShift`):** stage 1 → 3 সরাসরি, sweep চলাকালে displaced shift এলে।

### ৮.২ Continuation arm — কখন হয় ◆

সব শর্ত একসাথে:

1. `contOn` ON (default)।
2. Price **HTF POI**-র ভেতরে (low ≤ POI top, close > POI bottom) — ◎ slot `HTF dmd tap`।
3. **Combined bias** ওই দিকে (`→ ▲ Bull`) **এবং** HTF structure (`str ▲ Bull`) ওই দিকে।
4. বিপরীত দিকে sweep in play নেই।
5. এই POI-তে আগে arm হয়নি (একবার প্রতি POI)।
6. `oneDir` lock free।

হলে: Setup row `AT POI`, verdict `L: AT POI ◎ · wait shift ▲`, alert `[SETUP] ◎ Continuation armed (HTF POI)`।

**Sweep arm আর continuation arm দুটোই যোগ্য হলে sweep জেতে** (তখন ◎ দেখাবে না)।

### ৮.৩ Continuation-এ CHOP

CHOP regime-এ continuation arm / entry **তখনই** যদি তিনটা HTF read align: combined bias + HTF structure + **Daily EMA** (`D ▲ Bull`)। Daily উল্টো হলে CHOP block করে — BTC-র `D ▲ Bull` অথচ bias Bear-এর মতো অবস্থায় short continuation CHOP-এ হবে না।

### ৮.৪ Invalidation reason (debug Machine row)

| Reason | মানে |
|---|---|
| `sweep undone` | close sweep wick-এর ওপারে |
| `HTF POI violated` ◆ | continuation: close HTF POI-র distal edge-এর ওপারে |
| `sweep reclaim lost` | stage 1–2-এ close swept level (বা POI distal) ভুল দিকে |
| `opposing displacement` | বিপরীত 1.2 ATR body (stage 3-এ anchor ধরলে মাফ)। ◆ continuation-এও চলে — demand-এ নামার বড় bear candle setup মারতে পারে |
| `range swept both ways` | stage 1-এ বিপরীত quality sweep |
| `POI violated (own anchor)` | zone anchor ভাঙল |
| `HTF protected low / high broken` | HTF narrative শেষ |
| `SB window closed` | |
| `… expired` | clock শেষ |
| `anchor FVG violated` / `SB FVG violated` | retest FVG ভাঙল |
| `gate: …` | stage 4 gate fail → stage 3 retry |
| `conflict — …` | একই bar-এ উঁচু rank বিপরীত |
| `entry slipped` / `risk … cap` / `reward blocked` | viability fail |
| `entry not tracked — tracker busy` | signal হয়েছে, আগের trade খোলা |

---

## ৯. Silver Bullet module

### ৯.১ Window (NY → Bangladesh UTC+6)

| Window | NY | BD গ্রীষ্ম (EDT, Mar–Nov) | BD শীত (EST, Nov–Mar) | min quality |
|---|---|---|---|---|
| London SB | 03:00–04:00 | 13:00–14:00 | 14:00–15:00 | 3 |
| **NY AM SB** | 10:00–11:00 | 20:00–21:00 | 21:00–22:00 | 2 |
| NY PM SB | 14:00–15:00 | 00:00–01:00 (+1) | 01:00–02:00 (+1) | 3 |

Killzone: Asia 20:00–00:00 NY (BD 06:00–10:00) · London 02:00–05:00 (BD 12:00–15:00) · NY AM 07:00–10:00 (BD 17:00–20:00)। **05:00–07:00 NY (BD 15:00–17:00) = off-hours**: session point 0, A+ অসম্ভব। News window: 08:25–08:45 · 09:55–10:10 · Wed 13:55–14:35 NY।

### ৯.২ SB path

| বিষয় | সাধারণ machine | SB |
|---|---|---|
| Pool | যেকোনো swing / HTF POI | **engineered** — session H/L, EQ, PD/PW |
| Shift | MSS / ext CHoCH / displaced iCHoCH+FVG | internal CHoCH / CISD, body ≥ 0.8 ATR |
| Anchor | shift-leg FVG / zone | clean displacement FVG |
| Entry | CE limit বা confirmation | CE limit · edge শুধু rejection-এ |
| P/D | live range | window open-এ frozen |
| Clock | 20 / 15 / 20 | 12 / 8 / 10 |
| Chop | block (continuation exemption ছাড়া) | bypass |
| প্রতি window | — | ১ entry প্রতি দিক |

### ৯.৩ SB চলাকালে অন্য signal

`sbSuppress = Down-weight`: engine candidate এক tier বেশি লাগে। Machine mute হয় না।

---

## ১০. Liquidity Trap engine (◬)

Default ON, floor HIGH (≥ 70)। LT-1 (long, genuine break retest) · LT-2 / 3 / 5 / 6 / 7 (short traps) · LT-4 (long, shadow-high)। Label `◬ TRAP LT-2+LT-5 · HIGH · failed-break✓`। Veto: trap WAITING থাকলে বিপরীত engine mute, machine নয়। Trap signal সাধারণ engine candidate — একই gate।

---

## ১১. Settings — symbol ও timeframe অনুযায়ী ◆

### ১১.১ প্রথম যা বসাবেন

| Input | EURUSD | XAUUSD (OANDA) | NAS100 (OANDA) | BTCUSDT (Binance) |
|---|---|---|---|---|
| Symbol profile | FX majors | Metals / XAU | Indices | Crypto |
| Spread (ticks, session-এ মাপা) | ≈ 10 | ≈ 250–350 | ≈ 10–15 | ≈ 1 |
| Round-trip cost | commission only | commission only | 0 | 0–2 |
| Trade days | `23456` | `23456` | `23456` | `1234567` |
| Volume confirmation | OFF | OFF | OFF | **ON** |
| HTF bias filter | TF অনুযায়ী (§১১.৪) | | | |

### ১১.২ Default-এ রাখুন

`tierMode` A and above · `minScore` 50 · `maxRiskAtr` / `minRR` 1.5 · `rrMult` 2 · governance 4 / 2 · SB clocks · `contOn` ON · `mcDispShift` ON · `mcFvgDisp` ON।

### ১১.৩ Chart পরিষ্কার (display only)

Trendline · RB · EQ line · session line · structure chip · FVG box OFF করা যায়; detection চলে। `focusAtr` 4 → 3।

### ১১.৪ Timeframe ◆

| TF | HTF bias filter | HTF (Auto) | অন্য |
|---|---|---|---|
| **M5** | **60** | 60 | default |
| **M15** | **240** | 240 | profile Manual হলে `Shift / CISD stays a live trigger` 6–8, `Regime memory` 30 |
| M1 | 15 | 15 | trigger look 12–15; `spreadIn` অবশ্যই |
| M30 | 240 | 240 | |
| H1+ | D | D | killzone / SB অর্থহীন — `useKZ` off, SB off |

**নিয়ম:** bias TF আর HTF একই রাখলে dashboard আর chart একই গল্প বলে।

### ১১.৫ আপনার trading hour

Screenshot-এর সময় (BD 16:00–18:00 = NY 06:00–08:00) London KZ (02–05) আর NY AM (07–10)-এর মাঝে পড়ে। 06:00–07:00 NY-তে session point 0, A+ হবে না। বিকল্প: `London` session `0200-0700` করুন (তখন 06:00–07:00 "London" গোনে), অথবা NY AM 07:00–11:00 NY = BD 17:00–21:00-তে trade করুন।

---

## ১২. Alerts, journal line, CE pre-fill line ◆

### ১২.১ কীভাবে

Chart → Alert → Condition: **LQ-SD-PA v3.8.5** → condition → **"Once per bar close"** → open-ended।

### ১২.২ কোন alert

| Set | Condition |
|---|---|
| **Minimum** | `[SIGNAL] A+ LONG / SHORT`, `[SIGNAL] A LONG / SHORT` |
| Heads-up | `[SETUP] Structure shifted` (stage 3 — limit) · ◆ `[SETUP] ◎ Continuation armed (HTF POI)` |
| Trade | `[TRADE] TP1 / TP2 / SL hit` |
| SB | `[SB] ◆ Silver Bullet entry` |
| **Detail feed** | **"Any alert() function call"** — SB feed, LT feed, journal line, ◆ CE pre-fill line |
| Context | `[LIQ] …`, `[POI] …`, `[CTX] …`, `[LT] Trap setup detected` |

মোট 29 alertcondition + alert() feed (output 52/64)। ◆ `[SIGNAL] ◎ Fractal entry model` আর `[POI] FEM FVG locked` নেই।

### ১২.৩ CE pre-fill line (v3.8.3) ◆

Stage 3-এ FVG anchor lock হওয়ার bar-এ:

```
LQCE|XAUUSD|5|L|CE4163.500|SLa4160.250|SLr4158.900
```

`CE` = limit price · `SLa` = anchor stop (FVG distal − pad) · `SLr` = raid stop (sweep wick / HTF POI distal − pad)। Machine fill-এর সময় `SLr` যদি 1.5 ATR-এর মধ্যে থাকে সেটা, নাহলে `SLa`। **Label আসার আগেই order বসানোর data।**

### ১২.৪ Journal line

```
LQJRNL|BTCUSDT|15|S|MCc|A|sc64|k1q0sh1w0|RANGING|E81900.0|SL82150.0|T281400.0|d1/0
```

| Field | মানে |
|---|---|
| source | `SB` · `MC` (reversal machine) · ◆ **`MCc`** (continuation machine) · `LT` · `ENG` |
| `sc64` | score |
| `k1 q0` | pool kind / RAW sweep grade (continuation-এ sweep নাও থাকতে পারে → q0) |
| `sh1` | shift grade: 2 MSS · 1 CHoCH / CISD |
| `w0` | SB window |
| `E` `SL` `T2` `dN/M` | plan price · আজ N-তম signal, M loss |

---

## ১৩. Debug table (`showDbg` ON)

| Row | পড়বেন |
|---|---|
| `Sweeps raw/eff k` | raw grade / MSS upgrade সহ / pool kind / live-stale |
| `Machine L / S` | stage + **শেষ invalidation reason** (§৮.৪) |
| `Score C/L/P/T/E` | কোন component কম। ◆ continuation setup-এ L ≥ 10 দেখাবে sweep ছাড়াই |
| `Counts · untrk` | mechanical count, backtest নয় |
| `◬ LT · ◆ SB · day` | trap state · SB window / tag · আজকের signal / loss |

---

## ১৪. FAQ

**Q. 15m chart-এ "Bias 60" কেন?**
Bias TF input থেকে আসে (default 60), chart TF থেকে নয়। শুধু chart TF-এর নিচে নামে না। 15m-এ `HTF bias filter = 240` দিন — §২।

**Q. "HTF 240 supply" box, কিন্তু bias 60 — কোনটা মানব?**
দুটো আলাদা input (§২)। POI 4H, bias 1H। একই রাখতে bias 240 করুন।

**Q. Trend-এ pullback, price HTF POI-তে, bias ঠিক — তবু idle?** ◆
◎ slot দেখুন। `HTF dmd tap` আছে কিন্তু arm হয়নি → `str` (HTF structure) bias-এর সাথে একমত নয়, বা বিপরীত sweep in play, বা এই POI-তে আগে arm হয়েছে, বা `oneDir` lock। `—` → price POI-র ভেতরে নেই (box দেখুন: wick ঢুকতে হবে, close bottom-এর উপরে)।

**Q. Continuation setup AT POI-তে বারবার "opposing displacement"-এ মরে।** ◆
Demand-এ নামার বড় bear candle। এটা জানা সীমাবদ্ধতা; journal-এ বেশি হলে পরের version-এ stage 2 cont-এ waive হবে। আপাতত POI-র ভেতরে displacement থামার পর নতুন visit-এ আবার arm হতে পারে না (একবার প্রতি POI) — পরের HTF POI-র অপেক্ষা।

**Q. `NO · SSL weak < arm Q2` — মানে কী?**
Sweep হয়েছে কিন্তু reclaim candle দুর্বল (close level-এর 0.125 ATR উপরে নয়, penetration 0.25 ATR নয়)। arm-এর জন্য grade 2 লাগে। `minArmQual` 1 করলে arm হবে কিন্তু quality কমবে।

**Q. Verdict "wait POI · T2 OB · 4.5 ATR"** — 4.5 ATR মানে?
Next demand 4.5 ATR নিচে। 20 bar-এ tap অসম্ভব প্রায়। `fastShift` দিয়ে MSS▲ এলে POI ছাড়াই stage 3। নাহলে expire।

**Q. "⚠ bias blocks entry" অথচ setup চলছে।**
Arm হয়েছে neutral bias-এ (FIX-A3), কিন্তু entry gate ext structure বা HTF bias দেখবে। ext না flip করলে entry হবে না। অপেক্ষা না করে পরের setup দেখুন।

**Q. দিনের পর দিন signal নেই।**
Verdict পড়ুন। `tierMode = B and above` করে দেখুন কী বাদ যাচ্ছে (trade নয়)। Off-hours-এ (NY 05–07) A+ হবে না — §১১.৫।

**Q. Label হঠাৎ এল, পরে গেল?**
Label closed bar-এ, মুছে না। Last-bar drawing (NEXT, anchor box, HTF POI box, dashboard) live update।

**Q. CE fill label, broker-এ হয়নি।**
`spreadIn` বসান।

**Q. `NO · chop` অথচ trend।**
Regime external pivot-এ (12 bar) মাপে। `Regime memory` 40 → 60। Continuation তিন HTF align হলে chop পার হয়।

**Q. SB window-এ কিছু হয় না।**
Engineered pool লাগে (debug `k` ≥ 2)।

**Q. Repaint?**
না। Detection `barstate.isconfirmed`, HTF `[1] + lookahead_on`।

**Q. Strategy Tester?**
Indicator। Twin strategy / `mktwin.py` এই folder-এ নেই।

---

## ১৫. সীমাবদ্ধতা ও সতর্কতা

1. **Counter backtest নয়।** Intrabar order অজানা; slippage, swap নেই।
2. **Threshold measured নয়।** `minScore 50`, `minRR 1.5`, cap 1.5, governance 4/2 — reasoned default।
3. ◆ **Continuation path নতুন, uncalibrated।** Journal-এ `MCc` আলাদা করে ২–৩ সপ্তাহ মাপুন। খারাপ হলে `contOn` OFF — বাকি সব v3.8.4-এর মতো।
4. **News window fixed clock।**
5. **London DST** সপ্তাহে London window এক ঘণ্টা সরে।
6. **Weekend gap** misread হতে পারে।
7. **Spread static।**
8. **One tracked trade.**
9. **Drawing limit** 500।
10. **`≈ units`** USD-quoted-এ exact।

**Live-এর আগে:** এক সপ্তাহ observe → দুই সপ্তাহ demo + journal → source × tier × window expectancy → দুর্বল source OFF → ছোট size।

---

## ১৬. Quick reference card

```
┌─ SIGNAL এলে ──────────────────────────────────────────────────────────┐
│ tier A/A+?  base score ≥ 50?  verdict "LONG/SHORT signal"?             │
│ spread normal?  news 15 min-এ নেই?  আজ ≤ 4 signal, < 2 loss?           │
│ → "next open" = market · CE = limit (LQCE line-এ CE/SLa/SLr আগেই)      │
│ → TP1 50% + SL→BE · TP2 close (SB: runner TP3) · SB window শেষ = exit   │
└────────────────────────────────────────────────────────────────────────┘

TF     Chart TF (detection) · Bias TF = input "HTF bias filter" (M5 60 · M15 240) · HTF = Auto (M5→60 · M15→240)
PATH   (ক) sweep → POI → shift → FVG → CE     (খ) ◎ HTF POI tap + bias + str align → shift → FVG → CE  (A max)
DASH   Bias → combined · Regime · Trigger · ◎ (— / HTF dmd tap / cont L) · Setup L/S · Verdict = পরের ধাপ
VERD   "wait POI · T2 OB · 4.5 ATR" · "AT POI ◎ · wait shift" · "wait CE 4163.5" · "⚠ bias blocks entry"
       "SSL weak < arm Q2" · "no liquidity event · wait sweep or HTF POI tap" · score শুধু "gate: score"
STAGE  idle → SWEPT → AT POI → SHIFTED·await retest → ACTIVE   (20/15/20 · SB 12/8/10)
MARK   ◆ sweep  ◈ EQ  ◇ PD/PW  ▵▿ session  ✕ TL  ◦ trap · CHIP MSS > CHoCH > BOS · iCHoCH displaced+FVG = shift
BOX    ★HP · OB · RB · BRK · MIT · IFVG · HTF POI (◎ arm point) · ◉ CE await retest (limit) · ·spent
SB     London 03–04 · NY AM 10–11 · NY PM 14–15 NY  (BD +10h গ্রীষ্ম / +11h শীত) · off-hours NY 05–07 = BD 15–17
SET    profile · bias TF · spreadIn · tradeDays · crypto volume ON · contOn ON · mcDispShift ON
ALERT  Once per bar close · A+/A · [SETUP] Structure shifted · [SETUP] ◎ Continuation armed · "Any alert()" feed
FEED   LQCE|sym|tf|L|CE|SLa|SLr   ·   LQJRNL|sym|tf|L/S|SB·MC·MCc·LT·ENG|tier|sc|k q sh w|regime|E|SL|T2|dN/M
```
