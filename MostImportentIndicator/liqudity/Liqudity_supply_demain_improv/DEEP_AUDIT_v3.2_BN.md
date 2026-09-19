# LQ-SD-PA v3.2.0 — গভীর অডিট রিপোর্ট (দ্বিতীয় পাস)

> ফাইল: `version_02_fixed.pine` (4,271 লাইন)
> প্রথম অডিটের (REVIEW_AND_PLAN_BN.md) ১৯টা ফিক্স প্রয়োগের **পরে** পূর্ণ পুনঃপাঠ।
> লক্ষ্য: বাকি বাগ · লজিক অসঙ্গতি · missing feature · accuracy বাড়ানোর পথ — **এবং আমার নিজের ফিক্সগুলোর side-effect**।

---

## ০. সারসংক্ষেপ

| শ্রেণি | সংখ্যা | সবচেয়ে গুরুত্বপূর্ণ |
|---|---|---|
| 🔴 আসল বাগ (P0) | 3 | Tier একই বারে তিন জায়গায় তিন রকম · HTF সিগন্যাল এক ক্যান্ডেল দেরিতে · LT veto মেশিন-এর উপরে |
| 🟠 লজিক অসঙ্গতি (P1) | 5 | Regime এখন ভুল range দেখে (আমার P1-12 এর side-effect) · internal CHoCH = MSS · range re-anchor লাফ |
| 🟡 Missing feature (accuracy) | 9 | HTF structure (EMA নয়) · volume confirmation · IFVG · ADR exhaustion · multi-slot HTF POI |
| ⚪ Hardcoded → input | 6 | `SWEEP_CTX_ATR` · `TRIG_LOOK` · `CHOP_RANGE_ATR` · … |

**সৎ কথা:** ৩টা P1 আমার আগের ফিক্সের side-effect। সেগুলো আলাদা করে চিহ্নিত।

---

## ১. 🔴 আসল বাগ (P0)

### BUG-N1 · একই সিগন্যালের tier তিন জায়গায় তিন রকম
**লাইন 3590–3598 (counters) · 3704 & 3708 (label header) · 4162–4163 (alerts) vs 3661 & 3683 (label body)**

FIX-P1-2-এ machine tier-কে `f_mcTier()` দিয়ে সঠিকভাবে গ্রেড করা হয়েছে (`mcTierL`)। কিন্তু **পুরোনো সূত্র `math.max(tierLong, sigMCLong ? 3 : 1)` চার জায়গায় রয়ে গেছে**:

```pine
// লেবেলের প্রথম লাইন (3704)
longTxt := f_tierTxt(math.max(tierLong, sigMCLong ? 3 : 1)) + " · " + ...
// লেবেলের দ্বিতীয় লাইন (3661)
"◉ SETUP " + f_tierTxt(mcTierL)
```

**ফল:** একই লেবেলে উপরে "A · 55", নিচে "◉ SETUP A+" — দুই লাইন দুই কথা। অ্যালার্ট `[SIGNAL] A LONG` ফায়ার করে যখন লেবেল বলছে A+। কাউন্টার `cntA`/`cntAp` ভুল বাকেটে গোনে।

**ফিক্স:** একটা helper:
```pine
f_finalTier(bool isLong) =>
    isLong ? (sigMCLong ? math.max(tierLong, mcTierL) : tierLong)
           : (sigMCShort ? math.max(tierShort, mcTierS) : tierShort)
```
চার জায়গায় এটাই ব্যবহার। **অ্যালার্ট আর লেবেল এক সংখ্যা বলবে।**

---

### ~~BUG-N2~~ · **RETRACTED — ভুল ছিল** (ফেজ B-তে পুনঃযাচাই)

`expr[1]` + `lookahead_off` = HTF বার N-এর ভেতরের প্রতিটা চার্ট-বার **ক্লোজড** N−1 দেখে। N−1 ক্লোজ হওয়ার পরের প্রথম চার্ট-বারেই তথ্য পাওয়া যায় — **অতিরিক্ত দেরি শূন্য, repaint নেই।** `[1]` সরালে historical বার N-এর শেষ মান আগেই দেখত (lookahead bias) আর realtime বার repaint করত। `[1]` সঠিক, **থাকবে**। নিচের বিশ্লেষণ ইতিহাস হিসেবে রাখা:

<details><summary>মূল (ভুল) দাবি</summary>

**লাইন 1387, 1428**

```pine
[_crtB[1], _crtS[1], _tbsB[1], _tbsS[1], time[1]]     // ← [1]
...
[bTop[1], bBot[1], sTop[1], sBot[1], bIn[1], sIn[1]]   // ← [1]
```
`request.security(..., lookahead = barmerge.lookahead_off)` **ইতিমধ্যে** শুধু ক্লোজড HTF বারের ডেটা দেয়। তার উপর `[1]` = আরও এক HTF বার পেছনে। **দ্বিগুণ সুরক্ষা = দ্বিগুণ দেরি।**

**প্রভাব:** 5m → 60m চার্টে HTF CRT সিগন্যাল **৬০ মিনিট** দেরিতে, HTF FVG POI বক্স **১ ঘণ্টা** পরে দেখা যায়। FEM-এর `femL == 0 → 1` ট্রানজিশন (HTF POI tap) এক ঘণ্টা মিস করে।

**যাচাই:** `newHtfBar` গেট (লাইন 1392) নিশ্চিত করে চার্ট-বার HTF বারের প্রথম বার — তখন security ঠিক-ক্লোজ-হওয়া HTF বার দেয়। `[1]` তার আগেরটা। হ্যাঁ, দেরি নিশ্চিত।

**ফিক্স:** `[1]` সরাও। `lookahead_off` + `newHtfBar` গেট যথেষ্ট, repaint হবে না।
```pine
[_crtB, _crtS, _tbsB, _tbsS, time]
[bTop, bBot, sTop, sBot, bIn, sIn]
```
⚠️ পরিবর্তনের পর ২ দিন replay-এ যাচাই করো যে HTF POI বক্স লাইভ বারে লাফাচ্ছে না।

</details>

---

### BUG-N3 · LT veto মেশিন-পথের উপরে বসে আছে — SB-13 hierarchy ভাঙে
**লাইন 3225–3229** (এখন `ltVeto` default **ON**)

```pine
if ltEnable and ltVeto
    if ltSState == 1
        anyLong := false      // ← machine A+ entry-ও মিউট
```
SB-13 বলে: **SB machine > ordinary machine > pure engine**। কিন্তু LT veto — যা কেবল একটা "WAITING" ট্র্যাপ (এখনো confirm হয়নি) — একটা পূর্ণ A+ machine entry মেরে ফেলে। LT ট্র্যাপ দুর্বল/wick-heavy breakout-এ ঘনঘন arm হয়; default ON করার পর এটা অনেক বৈধ machine entry গিলে ফেলবে।

**উপরন্তু** tooltip এখনও বলছে "OFF by default (backward compatible)" — default এখন true। মিথ্যা tooltip।

**ফিক্স:**
```pine
if ltEnable and ltVeto
    if ltSState == 1 and not sigMCLong      // engine candidates only
        anyLong := false
    if ltLState == 1 and not sigMCShort
        anyShort := false
```
+ tooltip ঠিক করো। মেশিন-পথ কখনো veto-র শিকার হবে না — SB-13-এর সাথে সঙ্গতিপূর্ণ।

---

## ২. 🟠 লজিক অসঙ্গতি (P1)

### LOGIC-N1 · Regime এখন dealing range দেখে, নিজের range নয় ⚠️ আমার side-effect
**লাইন 1545, 1552**
```pine
extRngAtr = rangeOK and atr > 0 ? rngW / atr : na
regChop   = ... and extRngAtr < CHOP_RANGE_ATR
```
FIX-P1-12-এ `rngW` = running-extreme range (pivot-to-pivot-এর চেয়ে **বড়**)। Regime classifier সেই `rngW`-ই পড়ে। ফল: `extRngAtr` ফুলে গেছে → **CHOP কম ধরা পড়ে** → chop-এ বেশি সিগন্যাল। ডকট্রিন বলে external swing range (pivot থেকে pivot), সেটাই হারিয়ে গেছে।

**ফিক্স:** regime-এর নিজস্ব range:
```pine
regRngW   = not na(extRes) and not na(extSup) ? math.abs(extRes - extSup) : na
extRngAtr = not na(regRngW) and atr > 0 ? regRngW / atr : na
```
Dealing range আর regime range আলাদা — যেমন ছিল v3.1.1-এ।

---

### LOGIC-N2 · Dealing range নতুন pivot কনফার্ম হলে **লাফ** দেয় — ✅ **ACCEPTED LIMITATION** (ফেজ B সিদ্ধান্ত)

> লাফটা আসল structural change (নতুন swing pair) — শুধু ১২ বার দেরিতে রিপোর্ট হয় কারণ pivot-এর right-side confirmation লাগে। smoothing করলে বদলটা **লুকাবে**, দেরি কমবে না। কোডে কমেন্ট দিয়ে ডকুমেন্টেড, `·tight` ফ্ল্যাগ degenerate case ধরে। কোড বদল নেই।
**লাইন 1457–1460**
```pine
anchBar = math.min(extResBar, extSupBar)
drLen   = bar_index - anchBar + 1
```
একটা external pivot কনফার্ম হওয়ার মুহূর্তে (১২ বার দেরিতে) `anchBar` সামনে লাফায় → `drLen` ধ্বসে পড়ে → `rngHi/rngLo` হঠাৎ বদলায় → **Range pos এক বারে 85% থেকে 25%-এ যেতে পারে, দাম না নড়লেও।** A+ tier আর SB entry rule এই সংখ্যা পড়ে।

**ফিক্স (দুটির একটা):**
- সহজ: `drLen` কখনো এক বারে ৫০%-এর বেশি ছোট হতে দেবে না (`drLen := math.max(drLen, nz(drLen[1]) * 0.5)`)
- ভালো: range **শুধু structure event-এ** re-anchor হবে (eBosUp/eBosDn/eChochUp/eChochDn), pivot কনফার্মেশনে নয়। `var` range রাখো, event-এ reset, বাকি সময় running extreme দিয়ে expand।

---

### LOGIC-N3 · Internal CHoCH = MSS — কিন্তু চার্ট বলে internal "minor"
**লাইন 1190–1191**
```pine
mssUp = (chochUp or eChochUp) and sslInPlay and lastSslQual >= 2
```
`chochUp` = **internal** (pivLen=5) CHoCH। `f_structMarks` internal-কে ধূসর "iCHoCH" দেখায় — minor। কিন্তু `mssUp` internal আর external সমান ধরে। ফল: ৫-pivot-এর ছোট্ট CHoCH + sweep = **MSS গ্রেড**, trigger স্কোর 12, quality upgrade 4, SB shift grade 2। **ডিসপ্লে আর লজিক একমত নয়।**

**ফিক্স:** ইনপুট `mssNeedExt` (default ON):
```pine
mssUp = (eChochUp or (not mssNeedExt and chochUp)) and sslInPlay and lastSslQual >= 2
```
MSS = external structure shift। Internal CHoCH থাকুক CISD-grade (1)।

---

### LOGIC-N4 · `TP3 = 3R` hardcoded — `rrMult > 3` হলে TP2 > TP3
**লাইন 3532**
```pine
tp3P := anyLong ? entryP + 3 * risk : entryP - 3 * risk
```
`rrMult` ইনপুট 4.0 করলে TP2 = 4R, TP3 = 3R → ladder উল্টো। Liquidity target-ও `need = rrMult × risk` চায়, তাই tgt ≥ 4R হলে ঠিক, না হলে 3R fallback আবার উল্টো।

**ফিক্স:** `tp3P := entryP ± math.max(3, rrMult + 1) * risk`

---

### LOGIC-N5 · HTF POI freshness "candles inside" গোনে, chart-TF zone "separate visits" গোনে
**লাইন 1418–1419 vs MODULE 13 `z.tests`**
```pine
if not na(bTop) and bar_index > bBar and low <= bTop
    bIn += 1                          // ← প্রতি HTF বারে +1
```
`hPoiMaxTouch = 3`: দাম HTF POI-র ভেতরে ৩টা HTF ক্যান্ডেল consolidate করলেই POI "spent" — একবারও ছেড়ে না গিয়েও। Chart-TF zone engine ঠিকভাবে **leave + return** গোনে (`z.wasIn`)। দুই engine দুই সংজ্ঞা। HTF POI-ই আবার FEM-এর ভিত্তি।

**ফিক্স:** `f_htfPoi`-তে `var bool bWasIn` যোগ, `bIn` শুধু `not bWasIn and inside` হলে বাড়ুক।

---

### LOGIC-N6 · `f_htfPoi` একটাই slot — নতুন FVG পুরোনো fresh POI মুছে দেয়
**লাইন 1399–1428**

একটা bull, একটা bear POI। নতুন HTF FVG তৈরি হলে আগেরটা **সম্পূর্ণ হারিয়ে যায়** — সেটা untested, বেশি গুরুত্বপূর্ণ হলেও। ৬০m-এ দিনে ৩–৪টা FVG হয়; সকালের fresh POI দুপুরে মুছে যায়।

**ফিক্স:** chart-TF FVG registry-র মতো `array<Fvg>` (max 3 per side) HTF-এ। `hPoiBTop` = নিকটতম untested। বড় কাজ, কিন্তু FEM-এর accuracy-তে সরাসরি প্রভাব।

---

### LOGIC-N7 · Machine arm-এ reclaim চায়, continuation-এ চায় না
**লাইন 2903–2905**
```pine
if not na(suLSweepExt) and close < suLSweepExt   // sweep undone
```
Arm করতে `sslInPlay` লাগে (= close > sweep **level**)। কিন্তু stage 2/3-এ শুধু `close < sweep **extreme**` (wick) চেক। Level আর extreme-এর মাঝখানে দাম বন্ধ হলে — reclaim হারিয়েছে, `sslInPlay` false — কিন্তু setup বাঁচে। প্রথম অডিটের BUG-1-এর ছোট ভাই।

**ফিক্স:** stage 1–2-এ (POI tap-এর আগে) `not sslInPlay` হলে kill; stage 3-এ (shift হয়ে গেছে) wick-check-ই থাকুক — তখন structure বদলেছে, সুইপের কাজ শেষ।

---

## ৩. 🟡 Missing feature — accuracy বাড়াতে

অগ্রাধিকার = প্রভাব ÷ কাজ।

### 🥇 F1 · HTF **structure** bias — EMA-50 নয়
এখন `htfB` = 60m ক্লোজ vs EMA-50। এটা lagging, MA-based, ICT নয়। ইঞ্জিনের নিজের protected-swing structure আছে — HTF-এ সেটাই চালাও:
```pine
[htfDir] = request.security(syminfo.tickerid, "60", f_structure(...))   // ধারণা
```
বাস্তবে: HTF-এ `ta.pivothigh/low` + BOS/CHoCH state → `htfStructDir`। EMA bias থাকুক দ্বিতীয় মত হিসেবে।
**প্রভাব:** counter-trend ফিল্টার ৩০–৫০% ভালো হবে (EMA whipsaw নেই)।
**কাজ:** মাঝারি (নতুন security call, budget নয়)।

### 🥇 F2 · Volume / relative volume confirmation
Displacement = শুধু body ≥ 1.2 ATR। Volume নেই। Crypto/indices-এ volume আসল; FX-এ tick volume দুর্বল কিন্তু তবু কাজে লাগে।
```pine
relVol = volume / ta.sma(volume, 20)
dispUp = bullBar[1] and body[1] >= dispFactor * atr and (not useVol or relVol[1] >= volMult)
```
+ sweep quality: raid candle-এ `relVol ≥ 1.5` → +1 grade।
**প্রভাব:** false displacement (thin-volume spike) কমে। **ইনপুট optional রাখো** (FX-এ OFF)।

### 🥇 F3 · Inverted FVG (IFVG) — মুছে না ফেলে ফ্লিপ করো
**লাইন MODULE 12:** bull FVG `low <= f.bot` হলেই **delete**। ICT-তে ভায়োলেটেড FVG = **IFVG** — এখন resistance। Zone engine breaker/mitigation ফ্লিপ করে, FVG registry করে না। অসঙ্গতি + হারানো POI।
**ফিক্স:** `close < f.bot` হলে `f.isBull := false`, box রঙ বদলাও, `kind = "IFVG"`, `f_nextZones`-এ অন্তর্ভুক্ত।

### 🥈 F4 · ADR / daily range exhaustion
দাম যদি আজ ইতিমধ্যে ADR-এর ১২০% চলেছে, continuation entry দুর্বল। এক লাইন:
```pine
adr = request.security(syminfo.tickerid, "D", ta.sma(high - low, 10)[1])
dayRng = ta.highest(high, barsSinceMidnight) - ta.lowest(low, ...)
exhausted = dayRng / adr > adrMax        // default 1.2
```
Context স্কোরে −10, বা A+ থেকে বাদ।

### 🥈 F5 · Multi-slot HTF POI (LOGIC-N6-এর সমাধান)
উপরে বলা। FEM এর উপর দাঁড়িয়ে।

### 🥈 F6 · NEXT BUY/SELL-এ HTF POI অন্তর্ভুক্ত
এখন `f_nextZones` শুধু chart-TF zone দেখে। HTF FVG POI (`hPoiBTop/Bot`) প্রায়ই **বেশি গুরুত্বপূর্ণ** target। নিকটতম বাছাইয়ে ওটাও candidate হোক, লেবেলে "HTF" ট্যাগ।

### 🥉 F7 · NWOG / NDOG (New Week / Day Opening Gap)
00:00 open line আছে; weekly open নেই। Sunday open → Friday close gap একটা classic ICT magnet।

### 🥉 F8 · Score-এ recency decay
`recentMssUp` 10 বার পর্যন্ত পূর্ণ 12 পয়েন্ট, ১১তম বারে 0। Cliff। `12 × (1 − age/TRIG_LOOK)` — মসৃণ, সত্যের কাছাকাছি।

### 🥉 F9 · `strategy()` port — আসল backtest
Debug counters "mechanical, not statistics"। একটা `strategy()` twin (একই লজিক, `strategy.entry` দিয়ে) TradingView Strategy Tester চালাতে দেবে — win rate, PF, drawdown। **এটা ছাড়া accuracy দাবি সব অনুমান।**

---

## ৪. ⚪ Hardcoded constant → input হওয়া উচিত

| Constant | মান | কোথায় লাগে | কেন input |
|---|---|---|---|
| `SWEEP_CTX_ATR` (470) | 3.0 | sweep in play দূরত্ব | ভোলাটাইল সিম্বলে 3 ATR কম, শান্ত সিম্বলে বেশি |
| `TRIG_LOOK` (474) | 10 | shift/CISD live | M5-এ 10, M15-এ 6 ভালো |
| `CHOP_RANGE_ATR` (484) | 6.0 | chop threshold | সিম্বল-নির্ভর |
| `NEAR_LVL_ATR` (468) | 0.25 | "at level" | |
| `SL_PAD_ATR` (469) | 0.25 | stop padding | spread-নির্ভর |
| `POI_NEAR_ATR` | 1.5 | near POI স্কোর | |

সব একটা "Advanced tuning" গ্রুপে। ডিফল্ট অপরিবর্তিত।

---

## ৫. আমার আগের ফিক্সগুলোর যাচাই (regression check)

| ফিক্স | অবস্থা | মন্তব্য |
|---|---|---|
| P0-1 reclaim | ✅ ঠিক | চার্টে "Sweep in play: none" যখন সত্যিই নেই |
| P0-2 quality reset | ✅ ঠিক | debug টেবিল `raw3/eff4` দেখাচ্ছে |
| P0-3 detection ≠ drawing | ✅ ঠিক | |
| P0-4 plan entry | ✅ ঠিক | লাইভে যাচাই বাকি (সিগন্যাল আসেনি এখনো) |
| P0-5 per-engine SL | ✅ ঠিক | |
| P0-6 no overwrite | ✅ ঠিক | কিন্তু `cntLong` এখনও untracked সিগন্যাল গোনে → counters vs outcomes mismatch (ডকুমেন্টেড) |
| P0-7 chop bypass | ✅ ঠিক | |
| P0-8 news vs SB | ✅ ঠিক | |
| P1-2 mcTier | ⚠️ **অসম্পূর্ণ** | → BUG-N1: ৪ জায়গায় পুরোনো সূত্র রয়ে গেছে |
| P1-5 LT gate | ⚠️ **side-effect** | → BUG-N3: veto default ON মেশিন মারে |
| P1-9/12 range | ⚠️ **side-effect** | → LOGIC-N1 (regime ভুল range) · LOGIC-N2 (re-anchor লাফ) |
| বাকি সব | ✅ | |

---

## ৬. ডকুমেন্টেশন ত্রুটি (আমার)

`USER_MANUAL_BN.md` সেকশন ২ বলে `★HP = সুইপ-ভিত্তিক`। **ভুল।** কোড (লাইন 1864):
```pine
bs = not na(lastRes) and close[1] > lastRes    // displacement candle broke the last swing HIGH
```
★HP = displacement leg **structure ভেঙেছে** (BOS-grade origin), সুইপ নয়। ম্যানুয়াল ঠিক করতে হবে।

---

## ৭. রোডম্যাপ v3.3

### ফেজ A — বাগ (১–২ ঘণ্টা)
1. BUG-N1 · `f_finalTier()` — ৪ জায়গা এক সূত্রে
2. BUG-N3 · LT veto মেশিন বাদ + tooltip
3. LOGIC-N1 · regime নিজের range
4. LOGIC-N4 · TP3 = max(3, rrMult+1) R
5. ম্যানুয়াল ★HP সংশোধন

### ফেজ B — accuracy (৩–৪ ঘণ্টা)
6. BUG-N2 · HTF `[1]` সরানো (replay যাচাই সহ)
7. LOGIC-N3 · `mssNeedExt` ইনপুট
8. LOGIC-N2 · range re-anchor শুধু structure event-এ
9. LOGIC-N7 · stage 1–2 reclaim check
10. F2 · relative volume (optional input)
11. F8 · score recency decay
12. Constants → "Advanced" input গ্রুপ

### ফেজ C — feature (৫–৮ ঘণ্টা)
13. F1 · HTF structure bias
14. F3 · IFVG
15. F5 · multi-slot HTF POI + LOGIC-N5
16. F6 · HTF POI in NEXT level
17. F4 · ADR exhaustion

### ফেজ D — যাচাই
18. F9 · `strategy()` port → Strategy Tester → **আসল সংখ্যা**

> ✅ **সম্পন্ন (v3.2.1 ফেজ D):** `version_02_strategy.pine` তৈরি। ইন্ডিকেটরের সাথে diff = `strategy()` হেডার + ড্যাশবোর্ড শিরোনাম + MODULE 19S। Entry = সিগন্যাল বারের close-এ market (CE limit নয় — কারণ ম্যানুয়াল §৮ক), fixed-fractional risk, 50% TP1 + বাকি TP2/TP3, `trdSL` প্রতি বারে re-issue (BE/trail), non-price flat হলে `close_all`। Output budget অপরিবর্তিত 64/64। ফেজ A–D roadmap শেষ; এখন কাজ ব্যবহারকারীর — compile → Strategy Tester → score threshold calibrate।

---

## ৮. যা যাচাই করে **ঠিক** পেলাম (দ্বিতীয় পাসেও)

- `f_structure()` — দুইবার কল, আলাদা `var` state: Pine-এ সঠিক। `legLo/legHi` `confirmed`-এর বাইরে আপডেট হয় কিন্তু Pine realtime rollback-এ সমস্যা নেই
- Zone `inZ` সংজ্ঞা — invalidation আগে চেক হয় বলে upper bound লাগে না
- `f_nextZones` straddling zone — `(price INSIDE)` লেবেল এখন সেটা বলে
- 9টা `request.security` কল — সীমা 40-এর বহু নিচে
- Output budget — 8+14+5+37 = **64/64**, একটাও যোগ করা যাবে না (F-গুলো alert()/label দিয়ে করতে হবে)
- CISD / IFC / turtle-soup age / SB-11…14 — আগের মতোই নির্ভুল

---

## ৯. চূড়ান্ত কথা

ইঞ্জিন এখন **কাজ করছে** — চার্টে setup arm হচ্ছে, tier উঠছে, verdict সত্য বলছে। দ্বিতীয় পাসে যা পেলাম তা প্রথম পাসের মতো মারাত্মক নয়:

- **BUG-N1** বিরক্তিকর (লেবেল আর অ্যালার্ট একমত না) কিন্তু ট্রেড নষ্ট করে না
- **BUG-N2** সবচেয়ে বড় accuracy leak — HTF তথ্য এক ক্যান্ডেল বাসি
- **BUG-N3 + LOGIC-N1** আমার নিজের side-effect, এখনই ঠিক করা উচিত

তারপর **F1 (HTF structure) + F2 (volume) + F9 (strategy port)** — এই তিনটা ইন্ডিকেটরকে "ভালো" থেকে "প্রমাণযোগ্য"-তে নিয়ে যাবে। F9 ছাড়া বাকি সব accuracy দাবি অনুমান।

> কম সিগন্যাল = ভালো ইন্ডিকেটর। এখন লক্ষ্য: সিগন্যাল **আরও কম**, কিন্তু প্রতিটার পেছনে **HTF structure + volume + প্রমাণিত সংখ্যা**।
