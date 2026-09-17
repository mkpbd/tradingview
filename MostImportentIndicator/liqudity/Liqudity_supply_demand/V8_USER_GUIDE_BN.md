# V8 ব্যবহার-গাইড + Acceptance Test Checklist

দুই ফাইল: **V8_ENGINE.pine** (ফাইল A — entry দেয়) · **V8_CONTEXT.pine** (ফাইল B — শুধু context/alert, কখনো entry দেয় না)।

---

## ১. চার্টে বসানো

1. ফাইল A add → ফাইল B add (একই চার্টে দুটো)।
2. ফাইল B-র **① General** গ্রুপের ৯টা সংখ্যা ফাইল A-র সমান রাখো (pivot 5/12, ATR 14, EMA 50, displacement 1.2, struct 0.5, wick 0.3, sweep 15, raid 0.10)। আলাদা হলে দুই ফাইল আলাদা BOS/CHoCH দেখাবে।
3. প্রথম দিন default রাখো — কিছু tune করার আগে নিচের test শেষ করো।

### Recommended চার্ট
| Market | TF | কারণ |
|---|---|---|
| BTCUSDT / ETHUSDT | 5m, 15m | volume আছে → `useVolConf` কাজ করে |
| EURUSD / GBPUSD | 15m | volume না-থাকলে vol gate স্বয়ং bypass হয় |
| NAS100 / US30 | 1m, 5m | SB window (10:00–11:00 NY) সবচেয়ে সক্রিয় |
| XAUUSD | 5m, 15m | `eqTickMin` 10–20 দাও |

---

## ২. চার্ট পড়া (ফাইল A)

### Entry label
```
▲ LONG A+ ◆SB
◆ SB NY AM · Sweep+POI+MSS        ← producer tag (কোন narrative)
RR 2.3R · score 71
SL 61234.5 · TP 61500 / 61900 / 62400
```
- **A+** solid রঙ · **A** হালকা · **B** কমলা
- **◆SB** = Silver Bullet window-এ SB arming path দিয়ে এসেছে (সবচেয়ে উঁচু rank)
- **FEM 1H→LTF** = HTF FVG POI ছিল setup-এর POI
- **·CRT/TBS** = stage-6 displacement একটা CRT / turtle-soup candle দিয়ে পাস করেছে
- **Demand/Supply 50% retest** = S/D producer (`entryMode` "Narrative + confluence" থাকলে)

### Chart marks
| Mark | মানে |
|---|---|
| ◆ (নিচে/উপরে) | swing / wick / trendline pool raid |
| ◈ | EQH/EQL raid |
| ◇ | external pool raid (PDH/PDL/PWH/PWL/EXT/HTF) |
| ▵ ▿ | session H/L raid |
| CHoCH / BOS chip (উজ্জ্বল) | external structure |
| iCHoCH / ibos (ধূসর) | internal structure — MSS এখান থেকে |
| CISD chip | delivery flip |
| IFC chip | institutional funding candle |
| run chip | weak close-through — level burn হয়নি (`showRuns` on) |
| SL / BE / TP3 / TIME / STRUCT / REPLACED chip | trade কীভাবে শেষ হলো |

### Trade lines (৫টা)
entry dotted · SL লাল (BE-এর পর dashed) · TP1 dotted · TP2 solid · TP3 dashed

### Dashboard (উপর-ডান)
| Row | পড়ার নিয়ম |
|---|---|
| HTF | BULL/BEAR/CONFLICT/NEUTRAL + HTF range-এ premium/discount % |
| Regime | TREND/RANGE/EXPANSION/CHOP · run state · congestion N/4 |
| Range | dealing range-এ কোথায় (discount <50% → long side) |
| Targets | ▲ = উপরের buy-side draw · ▼ = নিচের sell-side draw |
| Setup ▲ N / ▼ N | সবচেয়ে এগোনো setup-এর stage। `showDebug` on → block reason দেখাবে |
| Silver Bullet | ◆ window + বাকি bar, বা "pre" (arming grace) |
| Trade | open trade + TP1✓ TP2✓ BE |
| Count | sig · TP1 · TP2 · SL · BE (mechanical counter, statistics নয়) |

### Setup stage-এর মানে
`idle → CTX → TARGET → RAIDED → POI → MSS → DISP → FVG → ENTRY`
- TARGET-এ আটকে = pool এখনো raid হয়নি (স্বাভাবিক, বেশিরভাগ সময় এখানেই থাকবে)
- RAIDED-এ আটকে + "no valid POI at the raid" = raid wick কোনো zone-এর ভিতরে পড়েনি
- POI-এ "MSS / CHoCH missing" = shift অপেক্ষায়
- FVG-এ "awaiting the FVG retest" = entry-র ঠিক আগে

---

## ৩. চার্ট পড়া (ফাইল B)

| Element | মানে |
|---|---|
| `15m CRT ▲` chip (teal) | ওই HTF-এ closed CRT — chart-এ HTF নতুন candle-এর **প্রথম** bar-এ আসে |
| `1H TWS ▼` (purple) | turtle soup যার reclaim candle displacement-grade |
| `4H TBS ▲` (orange) | plain turtle soup |
| fuchsia box | HTF #1 FVG (mit N = mitigation count) |
| blue box | HTF #2 FVG |
| `◬ LT-3+LT-5 trap?` chip | short trap machine armed, confirmation অপেক্ষায় |
| `◬ TRAP SHORT · HIGH · 75` label | trap confirmed — **শুধু context**, entry নয়। ফাইল A-র signal-এর সাথে মিললে confluence |
| ◦ mark | trap retest / failed-break হলো |
| SSL/BSL pool dashed line | wick-cluster liquidity |

Panel (নিচ-ডান) 14 row: ladder `5m▲ 15m▼ 1H▲ 4H▲ net +2/4` — net ≥ +2 = ladder bullish।

---

## ৪. Alert সেটআপ

### ফাইল A
- **"Any alert() function call"** → একটা alert, payload:
  `V8 LONG | BTCUSDT 5 | grade=A+ | prod=... | entry= | sl= | tp1= | tp2= | tp3= | rr= | score= | sb=`
  + trade event: `V8 trade TP3 | ...`
- অথবা alertcondition: `V8 LONG entry` · `V8 SHORT entry` · `V8 LONG A+` · `V8 SHORT A+` · `V8 take-profit hit` · `V8 stop hit` — সব **"Once per bar close"**
- `previewAlert` **off রাখো** (repaint করে)

### ফাইল B
- "Any alert() function call" → `V8-CTX HTF ... · confluence +2 · ladder ...` এবং `V8-CTX ◬ TRAP LONG ...`
- alertcondition: HTF CRT/TBS bullish/bearish · trap LONG/SHORT

---

## ৫. Acceptance Test — ৭টা (BUILD_PROCESS §৭)

প্রতিটা test-এর পর নিচের template-এ ফল লেখো। ফল অনুযায়ী আমি tune করবো।

### T1 · Chronology (label ভুল ক্রমে আসে না)
1. যেকোনো entry label-এ যাও। bar replay দিয়ে পিছিয়ে দেখো:
   raid mark (◆/◈/◇) → iCHoCH/CISD chip → বড় displacement candle → FVG → retest candle → label
2. **পাস**: label-এর আগে এই ক্রম আছে। raid label-এর পরে বা MSS raid-এর আগে হলে **ফেল** → bar_index + symbol দাও।

### T2 · Display independence (detection show* পড়ে না)
1. Dashboard **Count** row-এর সংখ্যা লেখো।
2. ⑤ `showZones` off, ④ `showPools` off, ③ `showStruct` off, ② `showSweeps` off, ⑦ `showPoi` off।
3. Count row **একই**? পাস। বদলালে কোন toggle বদলালো তা দাও।

### T3 · Repaint (bar replay)
1. Bar replay → একটা entry label-এর ২০ bar আগে থেকে play।
2. Label যেখানে history-তে আছে ঠিক **সেই bar-এই** আসে, আগে নয়, পরে সরে না?
3. HTF FVG box / ◆ marks replay-এ history-র সাথে মেলে?
4. ফেল হলে: কোন element + কত bar সরল।

### T4 · Ownership (এক pool → এক entry)
1. একই pool (একই দাম) থেকে **দুইটা** label এসেছে কি? `showPools` on করে দেখো।
2. পাস: এক label per pool। ফেল: দুই label-এর দাম + bar দাও।

### T5 · Risk
1. প্রতিটা label-এ `RR ≥ 1.5R`? (B floor)
2. A+ label-এ `RR ≥ 2.0R`?
3. SL সবসময় raid wick-এর **ওপারে** (long: label-এর নিচে, ◆ mark-এর নিচে)?
4. ফেল হলে label text paste করো।

### T6 · Starvation (signal কম না বেশি)
1. 5m চার্টে ৩ মাস স্ক্রোল → Count row-এর `sig` সংখ্যা।
2. প্রত্যাশা: **৩ মাসে 20–60** (BTC 5m, default)। <10 = starve · >120 = loose।
3. সংখ্যা + symbol দাও। সাথে `showDebug` on করে Setup ▲/▼ row-এ সবচেয়ে ঘন block reason ৩টা লেখো।

### T7 · Runtime (৩ symbol × ৩ TF)
BTCUSDT 5m · EURUSD 15m · NAS100 1m — প্রতিটায় চার্টের **শুরু পর্যন্ত** স্ক্রোল। "Error on bar N" থাকলে message + N।

---

## ৬. Report Template (copy-paste)

```
Symbol/TF: 
Token A:            Token B: 
T1 chronology: PASS / FAIL — 
T2 display:    PASS / FAIL — 
T3 repaint:    PASS / FAIL — 
T4 ownership:  PASS / FAIL — 
T5 risk:       PASS / FAIL — 
T6 count (3 mo): ___ sig · ___ A+ · ___ A · ___ B
   top block reasons: 1) 2) 3)
T7 runtime:    PASS / FAIL — 
Trade counters: sig __ TP1 __ TP2 __ SL __ BE __
```

---

## ৭. Tuning cheat-sheet (test-এর পর)

| লক্ষণ | Input |
|---|---|
| signal খুব কম | `minGrade` A→B · `minTier` 2→3 · `tgtMinPri` 3→1 · `needHtfAlign` off · `dispBodyAtr` 1.3→1.0 |
| signal খুব বেশি / দুর্বল | `minGrade` A→A+ · `minScore` 0→55 · `useKZ` on · `sbOnlyIn` on |
| entry দেরি | `mssIsDisp` on (default) · `retestDepth` 0.5→0.3 · `pivLen` 5→4 |
| B grade-এ trade block (target নাই) | `allowSynthTp` on (grade B-তে cap) |
| XAUUSD-এ EQ বেশি | `eqTickMin` 10–20 |
| CHOP-এ বাজে entry | `congGate` "Block" |
| A+ কম | `oteNeedAp` off · `apMaxTouch` 2→3 |
