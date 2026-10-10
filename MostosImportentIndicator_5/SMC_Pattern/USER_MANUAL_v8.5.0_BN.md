# SMC / ICT Suite v8.5.0 — ইউজার ম্যানুয়াল (বাংলা)

ফাইল: `SMC_Pattern/SMC_v8.5.0.txt` · Pine v6 · `indicator()` (strategy নয়, backtest সংখ্যা দেয় না)
এই ম্যানুয়াল = প্রতিটা setting কী করে, default কত, কখন বদলাবেন, chart-এ কী দেখবেন, trade কীভাবে নেবেন, signal না এলে কী দেখবেন।

---

## 0. পাঁচ মিনিটে শুরু

1. TradingView → Pine Editor → পুরো ফাইল paste → **Add to chart**। Compile error / "script too large" এলে message + line নম্বর নোট করুন (§12)।
2. Chart: **EURUSD / GBPUSD / XAUUSD 5m বা 15m** (forex/CFD-তে killzone filter নিজে থেকে চালু হয়)।
3. Settings কিছু না বদলালেও চলে — default = "Core only" সমতুল্য curated set।
4. Chart-এ যা দেখবেন: zone box (OB/BRK/RCB/RJB/QM/KL), FVG box, liquidity dotted line, BOS/CHoCH line, signal label (`▲ M37 A9 · 2.4R`), entry/SL/TP line, নিচে-ডানে info panel।
5. Signal label-এ hover → tooltip-এ entry / SL / TP1-2-3 / score / কারণ।
6. Alert: "Setup: LONG signal" / "SHORT signal" / "Any A+ signal" — alert message-এই entry, SL, TP, R:R থাকে।

**মনে রাখুন:** score / grade = ranking, probability নয়। Win-rate কোথাও দাবি করা হয়নি; §11 অনুযায়ী নিজে মাপুন।

---

## 1. Indicator কীভাবে ভাবে (এক নজরে)

```
Candle (L0) → Structure BOS/CHoCH (L1) → FVG + move strength (L2) → Liquidity levels + sweep (L3)
→ Zones OB/BRK/RCB/RJB/QM/KL (L4) → HTF bias (L5) → 28 setup module (L6) → Trade: entry/SL/TP/score (L7)
```

প্রতি bar-এ সব module একসঙ্গে দেখে, প্রতি side (long/short) **সেরা একটা** বেছে নেয় (rank = tier×10 + priority), তারপর gate → session → R:R/geometry → score ≥ min → gap/duplicate filter → label + alert। **সব কিছু bar close-এ** — live bar-এ কিছু আঁকে না, repaint নেই।

Score = **tier × 2** (module-এর শক্তি, 2–8) **+ confluence** (HTF, trend, zone quality, liquidity, sweep, location, HTF FVG; −/+)। Grade: A+ ≥ 11, A ≥ 8, B < 8 (B default-এ দেখায় না)।

---

## 2. Settings — group ধরে ধরে

### 2.1 · General (group 1)

| Input | Default | কী করে | কখন বদলাবেন |
|---|---|---|---|
| ATR length | 14 | সব "× ATR" মাপের base | বদলাবেন না |
| Swing length (each side) | 5 | pivot high/low = দুপাশে 5 bar। structure, liquidity, zone সব এর উপর | 1m-এ 7–8 (noise কম); 1h+ এ 3–4 |
| Max labels / Max lines | 200 / 100 | drawing budget | পুরোনো label চাইলে বাড়ান |
| Min bars between labels (same side) | 6 | label overlap ঠেকায় (signal label এটা bypass করে) | — |
| Label density | Signals only | Signals only = signal + zone · Key events = + real CHoCH, strong BOS, major sweep, breaker, HTF · All events = সব marker (CISD, FLIP, SWEEP REQ, warning) | শেখার সময় **All events**; trade-এর সময় Signals only |
| Setup master mode | Custom (toggles) | Core only = curated default (toggle ignore) · All on = সব module (ভিড়) · All off = শুধু zone/structure, signal নেই | Core only রাখা নিরাপদ |

### 2.2 · Candle (group 2) — L0 pattern threshold

| Input | Default | অর্থ |
|---|---|---|
| Pin bar wick ≥ N × body | 2.0 | wick body-র দ্বিগুণ হলে pin |
| Pin bar wick/range min | 0.55 | wick candle range-এর ≥55% |
| Doji max body/range | 0.10 | (এখন শুধু candle tag-এ) |
| Large range × ATR | 1.5 | long-wick rejection-এর জন্য বড় candle |
| Long-wick rejection wick/range | 0.50 | |
| Harami body < N × prev | 0.60 | M46 IMMEDIATE mode-এ harami trigger |
| Shooting star proximity × ATR | 1.0 | star tag |
| IFC wick ≥ N × body | 2.0 | M69: pivot-এর বাইরে wick + বড় lower/upper wick |
| IFC allow any colour | off | on = IFC candle-এর রঙ ignore |
| Manipulative min wick/range | 0.30 | manip candle (outside bar + wick) — reversal trigger-এর একটা form |

সাধারণত বদলাতে হয় না। Reversal candle (`trigBull/trigBear`-এর ভিত্তি) = pin / engulfing / IFC / manip।

### 2.3 · Structure (group 3) — BOS / CHoCH engine

| Input | Default | কী করে | কখন বদলাবেন |
|---|---|---|---|
| Bars without BOS/CHoCH → RANGE | **40** (v8.5.0, আগে 20) | এত bar কোনো BOS/CHoCH না এলে trend = RANGE | 1m-এ 60–80; 1h-এ 25–30 |
| Structure needs displacement | Candle | Candle = ভাঙা candle-এর body ≥ ratio এবং range ≥ ATR× · Off = যেকোনো close ভাঙলেই structure বদলায় (v8.2) | Off = বেশি BOS, বেশি noise |
| body/range ≥ | 0.5 | displacement candle body | |
| range ≥ × ATR | 0.6 | displacement candle range | |
| …or close beyond level ≥ × ATR | 0.3 | body ছোট হলেও close level-এর 0.3 ATR উপরে গেলে displacement | |
| Weak break: follow-through window | 3 | displacement ছাড়া break "weak" → 3 bar-এ আবার close beyond হলে promote | |
| Failed follow-throughs → RANGE | 2 | পরপর 2 break level-এর ভেতরে ফিরে এলে RANGE (v8.5.0: সফল break counter reset করে) | |
| CISD only after a qualified liquidity sweep | on | CISD (series open-এর নিচে close) শুধু major sweep-এর পরে গোনে | off = সব CISD (বেশি, দুর্বল) |

**পড়ার নিয়ম:** BOS = trend দিকে last pivot ভাঙা + displacement। CHoCH = protected swing ভাঙা **বা** LH-এর পরে last pivot low ভাঙা (R2 form)। Internal (iBOS) = counter-trend pivot ভাঙা, trend বদলায় না। Weak = displacement নেই, pending।

### 2.4 · FVG / Strength (group 4)

| Input | Default | কী করে |
|---|---|---|
| Min FVG height × ATR | 0.10 | ছোট gap বাদ |
| FVG mitigation mode | **TOUCH** | TOUCH = প্রথম ছোঁয়াতেই mitigated · 50% = অর্ধেক · FULL = পুরো ভরলে। v8.5.0-তে TOUCH-এও "at FVG" flag কাজ করে (D1 fix) |
| Max FVGs tracked | 40 | |
| Drop mitigated FVG after N bars | 300 | |
| Min FVG for STRONG | 1 | move "STRONG" হতে leg-এ ≥1 FVG (এখন দিক-অনুযায়ী) |
| STRONG min body efficiency | 0.55 | leg-এর body/range |
| STRONG max mixed ratio | 0.35 | রঙ বদলের অনুপাত |
| STRONG min speed | 0.35 | net move / bars / ATR |
| Max bars scanned per move | 150 | |

"STRONG" departure = OB তৈরির শর্ত, KL★, M42/M33/M51 gate, `dispScore`। Signal কম এলে body efficiency 0.55 → 0.50।

### 2.5 · Liquidity (group 5)

| Input | Default | কী করে |
|---|---|---|
| Equal H/L tolerance × ATR | 0.10 | দুটো pivot এর মধ্যে হলে merge → EQH/EQL (POOL) |
| Touch tolerance × ATR | 0.15 | level touch গোনার দূরত্ব |
| Touch cooldown (bars) | 3 | |
| External liquidity lookback | 50 | 50-bar extreme = `·ext` |
| PDH/PDL (intraday) · PWH/PWL (≤ daily) | on / on | previous day / week H/L (broker day, 17:00 NY) |
| RUN min body ratio / RUN min close beyond × ATR | 0.60 / 0.25 | level ভেদ করে এত body + দূরত্ব = RUN (continuation, "avoid") |
| SWEEP min wick ratio | 0.50 | M10-র sweep candle-এর wick |
| Sweep arms setups when the level is | Major only | Major only = POOL (EQH/EQL বা ≥3 touch — v8.5.0), PDH/PDL, PWH/PWL, SESH/SESL · Include external = `·ext` ও |
| Failed-close window (bars) | 2 | wick ভেদ + ছোট body → 2 bar wait: close ফিরলে SWEEP, নয়তো RUN |
| Max liquidity levels | 30 | |

**Sweep = trade context, RUN = avoid।** v8.5.0-তে POOL কড়া হয়েছে: এক retest wick আর POOL নয়।

### 2.6 · Zones (group 6)

| Input | Default | কী করে |
|---|---|---|
| Max zones tracked | 30 (SR) / 60 total | |
| Drop untouched zone after N bars | 500 | |
| Zone max height × ATR | 3.0 | বড় wick zone clip |
| OB V5: sweep within N bars before OB | 10 | OB-র আগে major sweep → OB★ (high-probability) |
| Rejection block min wick ratio | 0.50 | RJB |
| Rejection block confirm BOS within N bars | 15 | RJB confirmed হতে BOS লাগে |
| QM max bars after CHoCH | 60 | |
| Key level hidden-interest lookback | 50 | KL scoring criterion |
| Key level min criteria to show | 3 | KL = 3, KL★ = 4+ |
| Count UNSCORED pivot wick zones as tradable | off | on = প্রতিটা pivot wick zone-এ signal (ভিড়) — রাখবেন না |
| OB: high-probability (liquidity hunt) only | off | on = শুধু OB★ তৈরি হয় |
| Reclaimed: enforce 50% fib | on | RCB origin candle leg-এর নিচের অর্ধে |
| Key level volume criterion / × SMA | off / 1.5 | forex tick volume অবিশ্বস্ত — off রাখুন |
| Trendline zone ± × ATR / anchor | 0.30 / Wick | M64 trendline band |
| Propulsion window / size × ATR | 10 / 0.8 | M73: tapped zone থেকে আবার FVG সহ 0.8–2.4 ATR departure → PROP |
| M64: trendline needs a confirming touch | off | on = 3rd touch লাগে |

### 2.7 · HTF (group 7)

| Input | Default | কী করে |
|---|---|---|
| HTF pairing | Conservative | 1m→15m · 3m→30m · 5m→1h · 15m→4h · 30m→4h · 1h-4h→D · D→W। Aggressive: 5m→30m, 15m→1h |
| Manual HTF | 60 | pairing = Manual হলে |
| HTF bias gate | WARN | OFF = ignore · WARN = counter-HTF signal grey + −1 (continuation module block) · STRICT = counter block |
| Trend the gate reads | Entering bar | bar খোলার সময়ের trend (এই bar-এর BOS gate pass করতে পারে না) |
| HTF pivot length | 3 | |
| HTF sweep valid for N HTF bars | 3 | M68 arming window |
| HTF candle levels: candles shown | 3 | নীল O/H/L/C line |
| HTF rejection min wick ratio | 0.50 | M46 reliability |

HTF bias v8.5.0-তে displacement ছাড়া break-এ pivot "consume" করে না (D4) — flip আগের চেয়ে সময়মতো।

### 2.8 · Setup filters (group 8) — **সবচেয়ে গুরুত্বপূর্ণ group**

| Input | Default | কী করে | কখন বদলাবেন |
|---|---|---|---|
| Volume SMA length | 20 | KL volume criterion | — |
| Retest body ratio (M31) | 0.7 | M31 filter on থাকলে | — |
| Liquidity scan distance × ATR (M09) | 3.0 | কত দূরের BSL/SSL "target" গোনা | |
| Range detection length / max width | 20 / 3.0 | panel "range" row | |
| Armed setup stays valid N bars | 30 | M41/45/46/54/58/62/68 arming window | |
| **Zone entry trigger** | **CONFIRMED** | IMMEDIATE = zone-এ reversal candle-ই entry · CONFIRMED = reversal candle, তারপর তার high-এর উপরে displaced close (বা fresh FVG) · MSS = আগের 5 bar-এর high-এর উপরে close | Scalp/aggressive: IMMEDIATE · Conservative: MSS + window 12 |
| confirm within (bars) | 8 | reaction candle-এর পরে confirm-এর সময়সীমা | MSS হলে 12 |
| **Confirm: close beyond reference ≥ × ATR** | **0.10** (v8.5.0) | confirm candle reference-এর কত উপরে close | 0 = v8.4 আচরণ |
| **body/range ≥** | **0.40** (v8.5.0) | confirm candle-এর body | 0 = যেকোনো candle |
| **M10 confirm** | **Off** (v8.5.0) | Off = sweep candle-ই entry · 1-bar = sweep candle-এর high-এর উপরে পরের close (3 bar) · CISD = CISD এলে | A/B করে দেখুন (§11) |

### 2.9 · Premium / Discount + Sessions (group 9a)

| Input | Default | কী করে |
|---|---|---|
| Score premium/discount position | on | leg-এর নিচের অর্ধে long +1, OTE (62–79%) +2, deep premium (>75%) −1 (v8.5.0: এক location term) |
| Block longs in premium / shorts in discount | off | hard gate সব module-এ — দরকার নেই, নিচেরটা ব্যবহার করুন |
| Deep-premium / deep-discount threshold | 0.75 | |
| **Block CONTINUATION modules in deep premium / discount** | **on** (v8.5.0) | M02 M05 M08 M15 M33 M36 M42 M51 M73 deep premium-এ long নেয় না (late entry)। Reversal module প্রভাবিত নয় |
| Only signal inside a killzone | off | manual filter |
| Score London / NY sessions | on | +1 (killzone filter on থাকলে v8.5.0-তে 0 — সব signal-ই session-এ) |
| Session timezone | America/New_York | |
| Asia / London / NY | 2000-0000 / 0200-0500 / 0700-1000 | ICT killzone, NY time |
| Killzone filter auto-on for forex / CFD | on | forex + OANDA gold/indices-এ শুধু killzone-এ signal। Crypto/stock-এ নয় |
| Asia session high / low as liquidity (SESH/SESL) | on | Asia range sweep → London reversal |
| Score NY midnight open | on | 00:00 NY open-এর নিচে long +1 — শুধু location term 0 হলে (tie-break) |

**Forex-এ কোনো signal না এলে প্রথমে দেখুন:** আপনি killzone-এর বাইরে (panel Session row "outside killzones")।

### 2.10 · Visual · Colors (group 9) / Show (group 10)

রং, transparency, label size। `Filled label` off = text-only (theme-safe)। Show group: কোন drawing দেখাবেন — **detection বন্ধ হয় না**, শুধু আঁকা বন্ধ হয়। `Legend` on করলে top-right-এ key।

### 2.11 · Setups (group 11 / 13 / 15) — module toggles

Default ON (curated):

| Module | কী | Tier | কবে ভরসা করবেন |
|---|---|---|---|
| M01 Breakout rejection trap | break-এর পরে growing wick + strong close ফেরত | 2 | trap |
| M02 Pin-bar continuation | break-এর পরে shrinking wick + pin | 2 | continuation |
| M05 Pin bar after breakout | break +1 bar-এ pin | 2 | continuation |
| M08 Pin bar on retracement | trend + zone + trigger | 2 | সবচেয়ে generic; PD gate জরুরি |
| M09 Pin bar + liquidity | zone + wick ≥65% + ≥2 target উপরে | 3 | |
| M10 Sweep reversal | major level sweep + close back | 2 (POOL) / 3 (PD/PW/SES) | M10 confirm দিয়ে শক্ত করুন |
| M15 Breakout with pin | break candle নিজেই pin | 2 | |
| M33 Zone flip model | flipped KL + strong departure + weak arrival + trend + HTF | 3 | |
| M36 Weak retrace on OB | OB + weak arrival | 3 | |
| **M37 Inducement block** | OB-র উপরের inducement swept → OB tap | **4** | সবচেয়ে ভালো POI module |
| **M39 RCB retest** | CHoCH leg-এর origin candle retest | 3 / **4** (sweep → real CHoCH হলে, v8.5.0) | ICT reversal OB |
| M40 RJB retest | wick zone, BOS confirmed | 2 | |
| **M41 Sweep + FVG** | sweep → strong BOS with FVG → fresh FVG/zone react | **4** | v8.5.0-তে FVG path জীবিত |
| M42 HP S&D | strong-departure OB, 50%, weak arrival | 4 | sweep লাগে না → PD gate দরকার |
| **M45 Sweep CHoCH retest** | sweep → CHoCH (★) / BOS → breaker/OB retest | 3 / **4** | সবচেয়ে clean ICT model |
| M46 CISD | sweep → CISD + reliability → zone/FVG react | 3 | early reversal |
| M51 Smart BOS | strong BOS ≤40 bar → zone retest | 3 | Model B |
| M54 Smart S&D trap | demand reject → sweep নিচে → BOS → same demand retest (v8.5.0 anchored) | 4 | |
| M58 Double top/bottom | neckline close | 2 | SMC-র বাইরে; off করা যায় |
| M62 Fakeout trap | break fail 1–2 bar → level tap + reversal | 2 | |
| M64 Auto trendline | শুধু আঁকে | — | |
| **M68 HTF sweep → LTF** | HTF sweep + LTF CHoCH → react | **4** | Model A |
| M69 IFC candle | IFC at zone/sweep → close beyond | 2 (v8.5.0) | |
| M70 Quasimodo | QM zone | 2 | |
| M72 Operator trap | break → consolidation with wicks → strong close back | 2 | |
| M73 Propulsion | PROP zone 50% tap | 3 (v8.5.0) | |

Default OFF: M12 (TL + flipped), M14 (pin after break S/R)।

Group 12 filters: M19 (strong arrival-এ reversal block, on) · M26 (pullback corrective, on) · M31 (retest body, off) · §6.2 (zone 2× touched হলে sweep ছাড়া reversal না, on) · §6.6 (S&D 50% tap লাগে, on) · M01/M02 level ≥2× rejected (on) · Zone reversal must close beyond 50% (on)।

### 2.12 · Trade (group 14) — entry / SL / TP / score

| Input | Default | কী করে | কখন বদলাবেন |
|---|---|---|---|
| SL buffer × ATR | 0.15 | zone/wick-এর বাইরে buffer | spread বড় হলে 0.2 |
| Max SL distance × ATR | 2.0 | major HL/LH stop-এর cap | |
| Min R:R | 2.0 | এর নিচে signal hidden | 1.5 = বেশি signal |
| Max R:R | 6.0 | এর বাইরের real target "FAR" মার্ক (v8.5.0: reject নয়) | |
| Fixed-R mode / multiple | off / 2.0 | TP = R multiple, level নয় | |
| Require a REAL target | on | TP1 অবশ্যই zone/FVG/liquidity level | off = synthetic TP (empty space) |
| TP1 path check | STRICT | entry–TP1 মাঝে opposing zone/FVG → reject (STRICT) / −1 (WARN); liquidity pool → সবসময় −1 | signal কম হলে WARN |
| **Min score to show** | **8** | | v8.5.0-তে score গড়ে 1–2 কম → signal কম লাগলে 7, OOS-এ যাচাই |
| A+ ≥ / A ≥ | 11 / 8 | grade | |
| Min bars between signals | 5 | opposite side +2 score হলে override | |
| Suppress a repeat of the SAME setup for N bars | 50 | এক zone = এক trade | |
| M10 entry mode | IMMEDIATE | RETEST = swept level-এ limit · BOTH | |
| **Entry price** | **CLOSE** | CLOSE = confirm candle-এর close · CANDLE 50% = সেই candle-এর মাঝে limit · ZONE EDGE = zone-এর কিনারায় limit · **RETRACE** (v8.5.0) = ⏳ armed, displacement leg-এর 50% / fresh FVG-তে limit; fill হলে তবেই signal | RETRACE = risk অর্ধেক, কিছু trade miss |
| RETRACE: limit valid (bars) | 12 | | |
| Min risk (ticks) / … or × ATR | 20 / 0.3 | spread-size stop আটকায় | |
| Draw entry / SL / TP lines · length | on / 20 | | |

---

## 3. Chart-এ যা দেখবেন

### 3.1 Signal label
`▲▲ M37 A+12 · 2.4R` = long, module M37, grade A+, score 12, TP1 2.4R। `▲` = A, `·` = B (default-এ দেখায় না)। **Grey label** = counter-HTF (WARN)। `▼` short।
`⏳ M37 limit @ 1.0845` (নীল) = RETRACE armed; fill হলে সাধারণ label আসবে।
Hover → tooltip: কারণ, entry, SL, TP1 [structural / ⚠ SYNTH / ⚠ FAR], TP2, TP3, score, "LIMIT @", "⚠ opposing zone/FVG", "⚠ liquidity pool", "⚠vs HTF/trend", "INCOMPLETE (no POI)"।

### 3.2 Lines
- নীল solid = entry · লাল dashed = SL · সবুজ dashed ×3 = TP1/TP2/TP3 (20 bar)।
- BOS: solid (displaced) / dotted grey (weak, internal) · CHoCH: solid (real) / dashed grey (fake) · CISD: dotted · sweep of pivot: dashed grey।
- Major H/L (CHoCH trigger): dashed red/green।
- Liquidity: dotted = BSL/SSL · thick dashed orange = POOL/EQH/EQL · grey = PDH/PDL/PWH/PWL · SESH/SESL · `·ext` = 50-bar extreme। Resolved হলে line থেমে যায় (dotted = swept, solid grey = run)।
- HTF candle: নীল H/L solid, O dotted, C dashed।
- Trendline: সবুজ/লাল solid (M64)।

### 3.3 Zones (box text)
`OB▲★ T1` = bullish order block, ★ = liquidity-hunt (sweep আগে), T1/T1b/T2/G2 = candle type · `BRK▼` = breaker · `RCB▲` = reclaimed (CHoCH origin) · `RJB▼` = rejection (wick) · `QM▲` · `KL★ / KL` = key level 4+/3 · `S/R` (off default)।
Suffix: `FLIP` · `⚠SWEEP REQ` (2× touched, sweep ছাড়া reversal নেই) · `weak` · `?` (unconfirmed) · `IDM✓` (inducement swept → M37 ready) · `⇈PROP` · `★★` (near-miss then sweep)। Dashed border = weak/breaker/flipped।

### 3.4 Event labels (Key / All events)
`CHoCH✕▲` (✕ = sweep-এর পরে) · `BOS▲ ·2FVG` · `iBOS` · `CISD▲★` · `SWEEP✕ PDL` · `BRK▲` · `HTF SWEEP↓` · `HTF MANIP▲` · `✖SWEEP` (wick beyond swing, invalid BOS) · `RUN — avoid` · `⚠M51 weak BOS` · `M41 NO TRADE (no FVG)` · `PB✓` · `T5 no-FVG / T3 invalid` (OB diag)।

### 3.5 Info panel (নিচে ডানে)
Chart/HTF · LTF structure (BULLISH/BEARISH/RANGE) · HTF bias (⚠ = mismatch) · Regime · Last event (b ago) · Move phase · Active zone (fresh / ×n / SWEEP REQ) · Arrival (WEAK ✅ = ভালো, STRONG ❌ = reversal নয়) · Nearest BSL / SSL · 4-factor ✅❌ (HTF · trend · departure/arrival · liquidity) · Signal · PD array (% of leg, premium/discount/expansion) · Session (⛔ = filter block) + NY open side · TP1 type / HTF gate।

### 3.6 Data window (right-click → Data Window)
`long score`, `short score`, `zones`, `liq levels`, `M01/M02 level rejections`, `M46 CISD reliability`, `zone departure STRONG`, `PD array`, `displacement quality`, `internal break`, `weak break`, **`reject code (long×10 + short)`**।

Reject code (কেন এই bar-এ signal নেই):

| Code | অর্থ | কী করবেন |
|---|---|---|
| 0 | signal দেখানো হয়েছে | — |
| 1 | কোনো module fire করেনি | স্বাভাবিক |
| 2 | HTF gate (STRICT, বা WARN + continuation module) / PD continuation block | HTF bias দেখুন; reversal module-ই যাবে |
| 3 | killzone-এর বাইরে | session দেখুন |
| 4 | R:R / geometry / path (STRICT) | tooltip নেই; Min R:R 1.5, path WARN দিয়ে test |
| 5 | score < min | Min score 7 দিয়ে দেখুন |
| 6 | একই bar-এ উল্টো side জিতেছে | — |
| 7 | signal gap | — |
| 8 | একই setup/zone দ্বিতীয়বার | — |
| 9 | RETRACE armed (⏳) | fill-এর অপেক্ষা |

উদাহরণ: 25 = long 2 (gate), short 5 (score)।

---

## 4. Trade নেওয়ার ধাপ (checklist)

1. **HTF bias** panel-এ দেখুন; signal grey হলে (counter-HTF) size অর্ধেক বা skip।
2. **Signal label** → module নাম। Tier-4 module (M37 M41 M45★ M54 M68, M39-sweep) সবচেয়ে ভরসার; tier-2 (M01 M02 M05 M15 M58 M62 M72) শুধু A+ হলে।
3. **Tooltip**: TP1 `[structural]` হোক; `⚠ FAR` = দূরে, partial নিন; `⚠ SYNTH` = empty space (Require REAL off থাকলে)। `⚠ liquidity pool between` = TP1-এর আগে pool, partial সেখানে।
4. **PD array** row: continuation module premium-এ হলে এমনিই block; reversal module premium-এ short ঠিক আছে।
5. **Arrival WEAK ✅** হোক (STRONG ❌ = impulsive arrival, reversal দুর্বল)।
6. **Active zone**: `⚠SWEEP REQ` থাকলে signal এসেছে মানে sweep হয়েছে — ঠিক আছে; `fresh` ভালো।
7. Entry: CLOSE = market; `LIMIT @` / `RETRACE` = limit বসান, fill না হলে trade নেই।
8. SL = লাল line (zone/wick-এর বাইরে, min 0.3 ATR)। **SL কখনো tight করবেন না** — indicator wick পর্যন্ত গোনে।
9. TP1 = partial, SL → BE; TP2/TP3 = liquidity ladder।
10. Alert: "Setup: LONG/SHORT signal" (সব) বা "Any A+ signal" (শুধু A+)। Webhook message: `EURUSD | M37 LONG | A+12 | Entry … SL … TP1 … TP2 … | risk … · 2.4R | TF 5 | HTF BULL | TP1 REAL`।

---

## 5. Preset (সুপারিশ)

| কাজ | বদল |
|---|---|
| **Forex 5m (default)** | কিছু না |
| XAUUSD 5m | SL buffer 0.2; Min risk ticks 30 |
| 15m / 1h swing | Swing length 4; RANGE bars 30; HTF pairing Conservative; killzone filter off বিবেচনা (`Only signal inside a killzone` off + auto-on off) |
| 1m scalp | Swing length 7; RANGE bars 70; Zone trigger IMMEDIATE; Min R:R 1.5; label density Signals only |
| Crypto/BTC | killzone auto-on প্রযোজ্য নয়; `Score London/NY` off; PDH/PDL on |
| Conservative | Zone trigger MSS + window 12; M10 confirm = CISD; Entry RETRACE; Min score 9; HTF gate STRICT |
| Aggressive (বেশি signal) | Zone trigger IMMEDIATE; Confirm dist/body 0/0; Min score 7; TP1 path WARN; Max R:R 8; Block CONTINUATION off |
| শেখা / review | Label density All events; Show: PB✓, weak BOS, every CISD, OB diagnostics, Legend on |

**Setup master mode = Core only** রাখলে module toggle ভুল করে বদলালেও default থাকে।

---

## 6. "Signal আসছে না" — কারণ ক্রমে

1. Data window `reject code` দেখুন (§3.6)।
2. Forex: killzone (Asia 20–00, London 02–05, NY 07–10 NY time) — বাইরে code 3।
3. HTF gate WARN + continuation module → code 2; reversal module কম বলে সব চুপ।
4. Min score 8: tier-2 module-এর +4 confluence লাগে; v8.5.0-তে score কম → 7 test।
5. TP1 path STRICT + Require REAL on: ছোট TF-এ zone/FVG ভিড়ে code 4 বেশি → WARN।
6. Zone trigger CONFIRMED: reaction candle-এর পরে 8 bar-এ displaced close না এলে কিছু নেই — chart-এ zone tap দেখলেও signal না আসা স্বাভাবিক।
7. `Setup master mode = All off` হয়ে আছে কি না।

"Signal বেশি / ভুল": Min score 9, HTF gate STRICT, Block CONTINUATION on, M10 confirm 1-bar/CISD, M58/M62/M72 off।

---

## 7. v8.5.0-তে যা বদলেছে (user-visible)

- RANGE 20 → 40 bar; CHoCH বেশি, "BOS" কম।
- POOL কড়া (দুটো pivot বা ≥3 touch) → sweep-based signal কম কিন্তু শক্ত।
- FVG-reaction path (M41/M46/M68) এখন কাজ করে (আগে dead)।
- CHoCH-এর পরে break-retest/trap module (M05 M15 M62 M72) কাজ করে।
- Confirm candle displacement লাগে (0.10 ATR, body 0.40, trade-direction)।
- Continuation module deep premium/discount-এ block।
- TP1 "FAR" নতুন; path check FVG + liquidity দেখে।
- Score গড়ে 1–2 কম (correlated term কমানো) — Min score 8 একই; signal কমলে 7।
- Sweep SL আসল wick-এর নিচে (কিছু M10 R:R-এ fail করে hidden)।
- নতুন option: Entry RETRACE, M10 confirm, Block CONTINUATION, confirm displacement।
- Cut: M03 M04 M06 M07 M11 M29 M63 M65 (default-OFF ছিল)।

---

## 8. সীমাবদ্ধতা (সত্যি কথা)

- Win-rate / expectancy অজানা — strategy twin নেই। Grade = ordering।
- Limit entry (CANDLE 50% / ZONE EDGE / RETRACE) fill নাও হতে পারে; alert fill-এর আগে/পরে আলাদা নয় (RETRACE-এ fill-এ alert)।
- PDH/PDL broker day (17:00 NY), ICT true day নয়। London session H/L নেই।
- HTF pivot 3-bar lag → HTF bias flip দেরি।
- Pivot 5-bar lag: সব structure 5 bar পরে confirm — repaint নয়, delay।
- News/spread model নেই।

---

## 9. Alerts তালিকা

Signal: `Setup: LONG signal` · `Setup: SHORT signal` · `Setup: Any A+ signal` · `Warning: Counter-HTF signal`
Event: `Structure: BOS` · `Structure: CHoCH (Real)` · `Structure: CISD` · `Liquidity: Sweep detected` · `Zone: New high-probability OB` · `Zone: Propulsion Block formed` · `Zone: Price entered OB / S&D (50% tapped)`
Dynamic `alert()` (webhook): signal-এ full message, "Any alert() function call" দিয়ে।
সব alert bar close-এ।

---

## 10. Troubleshooting (compile / runtime)

| সমস্যা | কারণ / সমাধান |
|---|---|
| `script is too large` | token limit — M12, M14 off করে cut করতে বলুন (প্রতিটা ≈ −60), তারপর M58 |
| `Cannot access field of na object` | report করুন (RETRACE block সম্ভাব্য) — line নম্বর দিন |
| "The requested historical offset is beyond the historical buffer" | drawing clamp আছে; এলে Max lines কমান |
| Label/box দেখা যাচ্ছে না | Show group; Label density; `Filled label` off/on; transparency |
| Panel ঢেকে যাচ্ছে | `Info panel` off, বা chart-এর right margin বাড়ান |
| সব signal grey | HTF bias mismatch (panel ⚠) — stand aside বা reversal module |

---

## 11. নিজে মাপবেন কীভাবে (সংক্ষেপে)

`SMC_Pattern/audit_v8.4.1/05-testing-and-validation-plan.md` দেখুন। সারাংশ: default-এ 2 chart × 4 সপ্তাহ signal log (module, grade, entry, SL, TP1, outcome) → win%, avg R, expectancy per module/grade → একবারে একটা input বদলে A/B → OOS period-এ confirm। Score ↑ = win% ↑ কি না — এটা মাপার আগে grade-কে probability ভাববেন না।

---

## 12. Compile status

এই ম্যানুয়াল লেখার সময় v8.5.0 **TradingView-এ compile করা হয়নি** (local compiler নেই)। প্রথম paste-এ error/token message এলে line + message পাঠান; fix একই ফাইলে হবে। Behaviour বদল হলে v8.5.1।
