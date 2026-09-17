# V8 ব্যবহার-গাইড (v8.0.7) — চার্টে বসানো, পড়া, টিউন করা

**একটাই ফাইল: `V8_FULL.pine`** — engine (entry দেয়) + context layer (শুধু annotation/alert) একসাথে।

পুরনো `V8_ENGINE.pine` / `V8_CONTEXT.pine` v8.0.0-তে থেমে আছে — **ব্যবহার করবে না**, ওগুলোতে v8.0.1–v8.0.7-এর কোনো ফিক্স নেই।

---

## ০. ভার্সন ফিরিয়ে আনা (নতুন সমস্যা হলে)

`releases/` ফোল্ডারে প্রতিটা ভার্সনের কপি থাকে:

```
releases/V8_FULL_v8.0.4.pine
releases/V8_FULL_v8.0.5.pine
releases/V8_FULL_v8.0.6.pine
releases/V8_FULL_v8.0.7.pine   ← বর্তমান (= V8_FULL.pine)
```

নতুন ভার্সনে সমস্যা হলে: আগের ফাইল খুলে সব copy → TradingView Pine editor-এ paste → Save। কোনো git লাগবে না।

---

## ১. চার্টে বসানো

1. `V8_FULL.pine` → Pine editor → Add to chart।
2. প্রথম দিন সব default রাখো। নিচের T1–T7 test শেষ না করে কিছু বদলাবে না।
3. `showDebug` চালু করলে Setup ▲/▼ row-এ আটকে থাকার কারণ দেখা যায় — সমস্যা খুঁজতে কাজে লাগে।

### Recommended চার্ট

| Market | TF | কারণ |
|---|---|---|
| BTCUSDT / ETHUSDT | 5m, 15m | volume আছে → `useVolConf` কাজ করে |
| EURUSD / GBPUSD | 5m, 15m | volume না থাকলে vol gate স্বয়ংক্রিয়ভাবে bypass হয় |
| NAS100 / US30 | 1m, 5m | SB window (10:00–11:00 NY) সবচেয়ে সক্রিয় |
| XAUUSD | 5m, 15m | `eqTickMin` 10–20 দাও |

---

## ২. Entry label — কোথা থেকে buy/sell, কোথায় বেরোবে

```
▲ LONG B @ 4312.5          ← এই দামে buy (signal candle-এর close)
Sweep+POI+MSS              ← কোন narrative দিয়ে এসেছে
RR 1.8R · score 62
SL 4308.1 · TP 4316 / 4320 / 4325
```

| অংশ | মানে |
|---|---|
| ▲ LONG / ▼ SHORT | দিক — ▲ = buy, ▼ = sell |
| A+ / A / B | grade। A+ solid রঙ · A হালকা · B কমলা |
| ◆SB | Silver Bullet window-এ arming path দিয়ে এসেছে (সর্বোচ্চ rank) |
| @ 4312.5 | **entry দাম** |
| RR 1.8R | TP2 পর্যন্ত risk-reward |
| SL | stop loss — এর ওপারে গেলে trade শেষ |
| TP a / b / c | TP1 / TP2 / TP3 |

**Producer tag-এর মানে**
- `Sweep+POI+MSS` — পূর্ণ narrative (raid → POI → shift → displacement → FVG → retest)
- `FEM 1H→LTF` — setup-এর POI ছিল HTF FVG
- `·CRT/TBS` — stage-6 displacement একটা CRT / turtle-soup candle দিয়ে পাস করেছে
- `Demand/Supply 50% retest` — S/D producer (`entryMode` = "Narrative + confluence" হলে)

### Trade lines (৫টা)
entry dotted · **SL লাল** (break-even-এর পর dashed) · TP1 dotted · TP2 solid · TP3 dashed

### Position size বের করা
```
risk per unit = |entry − SL|
lot / qty     = (তোমার risk টাকা) ÷ risk per unit
```
উদাহরণ: entry 4312.5, SL 4308.1 → risk 4.4 point। $50 ঝুঁকি নিলে → 50 ÷ 4.4 ≈ 11.3 unit।

---

## ৩. Chart marks

| Mark | মানে |
|---|---|
| ◆ (নিচে / উপরে) | swing / wick-cluster / trendline pool raid |
| ◈ | EQH / EQL raid |
| ◇ | external pool raid (PDH/PDL/PWH/PWL/EXT/HTF) |
| ▵ ▿ | session high / low raid |
| CHoCH / BOS chip (উজ্জ্বল) | external structure |
| iCHoCH / ibos (ধূসর) | internal structure — MSS এখান থেকে আসে |
| CISD chip | delivery flip |
| IFC chip | institutional funding candle |
| SL / BE / TP3 / TIME / STRUCT / REPLACED chip | trade কীভাবে শেষ হলো |
| `15m CRT ▲` (teal) | ওই HTF-এ closed CRT — HTF নতুন candle-এর **প্রথম** chart bar-এ আসে |
| `1H TWS ▼` (purple) | turtle soup যার reclaim candle displacement-grade |
| `4H TBS ▲` (orange) | সাধারণ turtle soup |
| fuchsia box | HTF #1 FVG POI |
| blue box | HTF #2 FVG POI (mit N = mitigation সংখ্যা) |
| `◬ LT-3+LT-5 trap?` chip | trap machine armed, confirmation অপেক্ষায় |
| `◬ TRAP SHORT · HIGH · 75` | trap confirmed — **শুধু context, entry নয়**। engine signal-এর সাথে মিললে confluence |
| ◦ mark | trap retest / failed-break হলো |

---

## ৪. Dashboard (উপর-ডান, ১০ row)

| Row | পড়ার নিয়ম |
|---|---|
| HTF | BULL / BEAR / CONFLICT / NEUTRAL + HTF range-এ premium/discount % |
| Regime | TREND / RANGE / EXPANSION / CHOP · run state · congestion N/4 |
| Range | dealing range-এ কোথায় (discount < 50% → long-এর দিক) |
| Setup ▲ N / ▼ N | সবচেয়ে এগোনো setup-এর stage। `showDebug` on → আটকে থাকার কারণ |
| Silver Bullet | ◆ active window, বা "pre" (arming grace) |
| Trade | চলমান trade + TP1✓ TP2✓ BE |
| Count | sig · TP1 · TP2 · SL · BE — যান্ত্রিক গণনা, statistics নয় |
| **Funnel** | নিচে দেখো |
| **Gates** | নিচে দেখো |

### Setup stage-এর ক্রম
`idle → TARGET → RAIDED → POI → MSS → DISP → FVG → ENTRY`

- **TARGET**-এ আটকে = pool এখনো raid হয়নি (স্বাভাবিক, বেশিরভাগ সময় এখানেই থাকে)
- **RAIDED** + "no valid POI at the raid" = raid wick কোনো zone-এর ভিতরে পড়েনি
- **POI** + "MSS / CHoCH missing" = shift-এর অপেক্ষা
- **FVG** + "awaiting the FVG retest" = entry-র ঠিক আগে

---

## ৫. Funnel + Gates পড়া (এটাই diagnosis tool)

```
Funnel   T210 R81 P65 M14 D6 F3 E1 · kill: setup expired ×57 · raid failed/stale ×55
Gates    cand 3 · fail 3: grade ×2
```

**Funnel** = chart load হওয়ার পর থেকে কতগুলো setup প্রতিটা stage-এ **পৌঁছেছে**:

| অক্ষর | Stage |
|---|---|
| T | TARGET lock (pool ঠিক করা হলো) |
| R | RAIDED (ওই pool raid হলো) |
| P | POI পাওয়া গেল |
| M | MSS হলো |
| D | Displacement হলো |
| F | FVG তৈরি হলো |
| E | ENTRY (retest সম্পূর্ণ) |

**kill:** = সবচেয়ে বেশি যে দুই কারণে setup মরেছে।

**Gates** = যত candidate entry পর্যন্ত এসেছে (`cand`), তার মধ্যে কতগুলো hard gate-এ আটকেছে (`fail`), আর শীর্ষ কারণ।

### কোথায় সমস্যা — pass rate দেখে
প্রতিটা ধাপের ভাগফল বের করো। স্বাভাবিক লক্ষ্য:

| ধাপ | সুস্থ | কম হলে যা দেখতে হবে |
|---|---|---|
| R ÷ T | 30–50% | pool ঠিক জায়গায় বসছে কিনা (`showPools` on) |
| P ÷ R | 60–85% | POI fallback (`poiWickFb`) · `poiBindAtr` |
| M ÷ P | 30%+ | MSS নিয়ম — `mssWin`, `structDisp` |
| D ÷ M | 40%+ | `dispBodyAtr`, `dispWin` |
| F ÷ D | 60%+ | `fvgMinAtr` |
| E ÷ F | 25%+ | `retestDepth`, `lateBars`, `retestWin` |

সবচেয়ে ছোট অনুপাতটাই আসল bottleneck — সেটা ঠিক করো, বাকিগুলো নয়।

### Gate কারণের মানে

| Gate | মানে | সম্ভাব্য ব্যবস্থা |
|---|---|---|
| base (bias/kz/news/cd) | bias filter / killzone / news window / cooldown আটকেছে | `useNews` off, `masterCd` কমাও |
| narrative | চেইনের ক্রম ভেঙেছে (internal bug হলে জানাও) | — |
| SL range | stop `minRiskAtr`–`maxRiskAtr`-এর বাইরে | `maxRiskAtr` বাড়াও |
| no TP target | কাঠামোগত target নেই | `allowSynthTp` on (default on) |
| RR floor | RR < 1.5R | `tpClamp` off (default off), `rrB` দেখো |
| room | opposing liquidity খুব কাছে | `oppLiqHard` off (default off) |
| dedupe | একই pool/POI/MSS আগেই trade হয়েছে | স্বাভাবিক |
| tier | POI tier > `minTier` | `minTier` 2→3 |
| grade | grade < `minGrade` | `minGrade` B রাখো |
| score | `minScore`-এর নিচে | `minScore` 0 রাখো |
| congestion / run / HTF conflict | ওই gate "Block" বা "A+ only"-তে আছে | "Downgrade"-এ নামাও |
| story | হুবহু একই story আগে trade হয়েছে | স্বাভাবিক |

---

## ৬. Alert সেটআপ

- **"Any alert() function call"** → একটাই alert, payload:
  `V8 LONG | BTCUSDT 5 | grade=A+ | prod=... | entry= | sl= | tp1= | tp2= | tp3= | rr= | score= | sb=`
  সাথে trade event: `V8 trade TP3 | ...`
- অথবা alertcondition আলাদা করে: `V8 LONG entry` · `V8 SHORT entry` · `V8 LONG A+` · `V8 SHORT A+` · `V8 take-profit hit` · `V8 stop hit` · `V8 HTF CRT/TBS bullish/bearish` · `V8 trap LONG/SHORT` — সব **"Once per bar close"**
- `previewAlert` **off রাখো** (repaint করে)

---

## ৭. Acceptance Test — ৭টা

### T1 · Chronology (label ভুল ক্রমে আসে না)
1. যেকোনো entry label-এ যাও। পিছিয়ে দেখো: raid mark (◆/◈/◇) → iCHoCH বা CISD chip → বড় displacement candle → FVG → retest candle → label।
2. **পাস**: label-এর আগে এই ক্রম আছে। raid যদি label-এর পরে বা MSS raid-এর আগে হয় → **ফেল**, bar time + symbol দাও।

### T2 · Display independence (detection show* পড়ে না)
1. Count row-এর সংখ্যা লিখে রাখো।
2. `showZones` off, `showPools` off, `showStruct` off, `showSweeps` off, `showPoi` off করো।
3. Count row **একই** থাকলে পাস। বদলালে কোন toggle বদলালো তা দাও।

### T3 · Repaint (bar replay)
1. Bar replay → একটা entry label-এর ২০ bar আগে থেকে play।
2. Label ঠিক **সেই bar-এই** আসে তো? আগে আসে না, পরে সরে না?
3. HTF FVG box / ◆ mark replay-এ history-র সাথে মেলে?
4. ফেল হলে: কোন element, কত bar সরল।

### T4 · Ownership (এক pool → এক entry)
1. একই দামের pool থেকে **দুইটা** label এসেছে কি? `showPools` on করে দেখো।
2. পাস: এক label per pool। ফেল: দুই label-এর দাম + সময় দাও।

### T5 · Risk
1. প্রতিটা label-এ `RR ≥ 1.5R`?
2. A+ label-এ `RR ≥ 2.0R`?
3. SL সবসময় raid wick-এর **ওপারে**? (long হলে ◆ mark-এর নিচে)
4. ফেল হলে label-এর text হুবহু দাও।

### T6 · Starvation (signal কম না বেশি)
1. 5m চার্টে ৩ মাস স্ক্রোল → Count row-এর `sig` সংখ্যা।
2. প্রত্যাশা: **৩ মাসে 20–60** (BTC 5m, default)। <10 = starve · >120 = loose।
3. সংখ্যা + symbol + Funnel row দাও।

### T7 · Runtime (৩ symbol × ৩ TF)
BTCUSDT 5m · EURUSD 15m · NAS100 1m — প্রতিটায় চার্টের **শুরু পর্যন্ত** স্ক্রোল। "Error on bar N" এলে message + N দাও।

---

## ৮. Report Template (copy-paste)

```
Version:        v8.0.__
Symbol/TF:
Compile:        OK / CE10117 ______
Funnel:         T__ R__ P__ M__ D__ F__ E__ · kill: ______ · ______
Gates:          cand __ · fail __: ______
Count:          __ sig · __ TP1 · __ TP2 · __ SL · __ BE
T1 chronology:  PASS / FAIL —
T2 display:     PASS / FAIL —
T3 repaint:     PASS / FAIL —
T4 ownership:   PASS / FAIL —
T5 risk:        PASS / FAIL —
T6 count (3 mo): ___ sig
T7 runtime:     PASS / FAIL —
প্রথম ২ label-এর text:
```

---

## ৯. Tuning cheat-sheet

| লক্ষণ | কী বদলাবে |
|---|---|
| signal খুব কম | `minTier` 2→3 · `tgtMinPri` 3→1 · `needHtfAlign` off · `dispBodyAtr` 1.0→0.8 · `mssWin` 16→20 |
| signal খুব বেশি / দুর্বল | `minGrade` B→A · `minScore` 0→55 · `useKZ` on · `sbOnlyIn` on |
| entry দেরিতে আসে | `retestDepth` 0.35→0.2 · `pivLen` 5→4 · `lateBars` বাড়াও |
| "RR floor"-এ আটকায় | `tpClamp` off (default) · `rrMult` কমাও |
| "grade"-এ আটকায় | `minGrade` B · congestion/run/HTF gate "Downgrade"-এ রাখো |
| "no TP target" | `allowSynthTp` on (default) |
| XAUUSD-এ EQ বেশি | `eqTickMin` 10–20 |
| CHOP-এ বাজে entry | `congGate` "Block" |
| A+ কম | `oteNeedAp` off · `apMaxTouch` 2→3 |

---

## ১০. v8.0.7-এ যা বদলেছে (আগের গাইড থেকে)

- **এক ফাইল** `V8_FULL.pine` — আর দুই ফাইল add করতে হয় না।
- Entry label-এ **entry দাম** (`@ 4312.5`) যোগ হয়েছে।
- Raid invalidation এখন **শুধু wick** — swept level-এ close ফিরলে setup মরে না (আগে ৭০% setup এখানে মরত)।
- Reversal setup-এ B-grade raid থাকলেই trade হয় (grade B-তে cap)।
- Default বদল: `htfConfMode` → Downgrade · `tpClamp` → off · `dispBodyAtr` → 1.0 · `minGrade` → B · `allowSynthTp` → on।
- Dashboard-এ **Funnel** ও **Gates** row — কেন signal আসছে না, এক নজরে।
