# SMC Suite — Better Solution Plan (v8.5.1)

> ভিত্তি: `SMC_v8.4.1_ANALYSIS_BN.md` + `SMC_v8.4.1_Forensic_Audit_Improvement_Plan.md`, দুটোই **আসল source-এর সাথে মিলিয়ে যাচাই করা**।
> তারিখ: 2026-10-15
> Source যা দেখা হয়েছে: `_6/SMC_Pattern/SMC_v8.4.1.txt` (3862 লাইন) এবং `_5/SMC_Pattern/SMC_v8.5.0.txt` (3984 লাইন)।

---

## 0. সবচেয়ে গুরুত্বপূর্ণ আবিষ্কার

দুটো document-ই **v8.4.1**-এর উপর লেখা। কিন্তু `_5/SMC_Pattern/`-এ আগেই একটা **v8.5.0** আছে, যেটা অনেক issue ঠিক করে ফেলেছে।
তাই v8.4.1-এ নতুন করে fix করলে কাজ দুবার হবে, আর দুটো version-এর মধ্যে conflict হবে।

**সিদ্ধান্ত:** নতুন build হবে **v8.5.0-এর উপর → v8.5.1**। v8.4.1 আর ছোঁয়া হবে না।

| Issue | v8.4.1 | v8.5.0 | v8.5.1 (এই plan) |
|---|---|---|---|
| F18 — TOUCH mode-এ FVG reaction মৃত | ❌ আছে | ✅ ঠিক (D1) | ছোট guard যোগ (S3) |
| F19 — CONFIRMED মোডে arrival হারায় | ❌ আছে | ❌ **এখনো আছে** (লাইন 2428 বনাম 2717) | ✅ **S1** |
| W15 — arrival দুই side-এ shared | ❌ | ❌ defer করা হয়েছিল | ✅ **S1**-এর সাথেই ঠিক হয় |
| PERF — PD array-তে 490-bar scan প্রতি bar-এ | ❌ | ❌ **এখনো আছে** (লাইন 2409–2410) | ✅ **S2** |
| `i_idmTime` input-এর প্রভাব নেই | ❌ | ✅ সরানো | — |
| Write-only field (`sweptPool`, `incomplete`, `brkTimeOk`) | ❌ | ✅ সরানো | — |
| M69 tier 1 অথচ default ON | ❌ | ✅ tier 2 | — |
| একই counter-context-এর জন্য তিনবার জরিমানা | ❌ | ✅ ঠিক (D5) | — |
| শুধু sweep দেখেই reversal ধরা (doc-2 §5.1) | আংশিক | ✅ M10 confirm option (W10) | — |
| Grade B কখনো দেখা যায় না | ❌ | ❌ আছে | ✅ **S4** |
| Signal-এর ফলাফল মাপার উপায় নেই (expectancy) | ❌ | ❌ (strategy port v8.2.1-এর, পুরোনো) | ✅ **S6** |

---

## 1. দুটো document-এর মূল্যায়ন

### Doc-1 `SMC_v8.4.1_ANALYSIS_BN.md`
- **শক্তি:** source থেকে লাইন নম্বরসহ লেখা, তাই F18/F19/dead input/PERF সব সঠিক।
- **দুর্বলতা:** v8.5.0-এর অস্তিত্ব হিসাবে ধরেনি, তাই "fix করা দরকার" তালিকার অর্ধেক আগেই করা হয়ে গেছে।

### Doc-2 `SMC_v8.4.1_Forensic_Audit_Improvement_Plan.md`
- **শক্তি:** নীতিগুলো ঠিক: আগে correctness, তারপর logic, তারপর মাপা। এর Definition of Done আর test matrix কাজের।
- **দুর্বলতা:**
  1. নিজেই স্বীকার করেছে source দেখেনি ("not a direct inspection"), তাই কোনো exact patch নেই, শুধু "verify করুন"।
  2. কিছু সুপারিশ Pine-এ বাস্তবে করা যায় না বা খুব খরুচে:

| Doc-2-এর সুপারিশ | সমস্যা | এই plan-এ বিকল্প |
|---|---|---|
| প্রতিটা candidate-এর timestamp, score ভাগ, rejection log রাখা (§6) | Pine-এ কোনো log/file নেই; label দিয়ে করলে 500-এর cap ভেঙে যায় | Data window-এর reject code আগে থেকেই আছে + S5-এ দুটো diagnostic plot + S6 strategy twin |
| Zone multi-factor rank করে বাদ পড়া zone-গুলোও রাখা (§5.2) | প্রতি bar-এ 60 zone × কয়েকটা factor = আরও CPU; `Ctx` 254-element cap-এ | এখন করা হচ্ছে না। S6-এর ফলাফলে zone selection-এর দোষ প্রমাণ হলে তখন |
| HTF context / setup / entry timeframe আলাদা করা (§5.3) | আগে থেকেই আলাদা: HTF শুধু gate ও score, trigger LTF-এর POI machine | কিছু করতে হবে না |
| Spread, slippage, একই candle-এ SL ও TP দুটোই ছোঁয়া (§5.4) | Indicator-এ মাপা যায় না | **S6** strategy twin-এ conservative fill |

---

## 2. সমাধান — exact patch (v8.5.0-এর লাইন নম্বর)

### S1 — F19 + W15: arrival-কে zone snapshot-এর ভিতরে, প্রতি side আলাদা করে রাখা ⭐ সবচেয়ে গুরুত্বপূর্ণ

**মূল কারণ (source থেকে যাচাই করা):**
- লাইন 2428: `zoneTouch = ft.zb.kind != "" or ft.zs.kind != ""` হিসাব হয় **live touch** থেকে।
- লাইন 2717: POI snapshot restore হয় (`ft.zb := sx.poiZb`) **তার পরে**।
- ফলে CONFIRMED মোডে confirm bar zone-এর বাইরে থাকলে `ft.arrivalWeak = false`। তখন:
  - **M33, M36, M42** fire করতে পারে না।
  - M19 filter বাইপাস হয়, অর্থাৎ STRONG arrival-এর পরেও reversal চলে যায়।
- আরেকটা সমস্যা: `ft.arrivalWeak` একটাই flag, দুই side-এর জন্য shared (লাইন 2431 `arrDirNow`)। Supply-তে touch-এর verdict দিয়ে long-ও বিচার হয় (W15)।

**সমাধানের ধারণা:** Arrival-কে `ZS`-এর field বানানো। Tap-এর সময় `sx.poiZb := ft.zb` পুরো ZS object-টা রাখে, তাই arrival **নিজে থেকেই** snapshot-এর সাথে চলে যায়। কোনো নতুন state machine লাগে না। আর `Ctx`-এ কিছু যোগ হয় না (cap রক্ষা)।

**ধাপ ১ — `type ZS`-এ দুটো field (লাইন 538–551):**
```pine
    bool   prop      = false
    int    arr       = 0       // v8.5.1 S1 — arrival into THIS zone: 1 weak · -1 strong · 0 not measured
    float  arrMix    = 0.0     //            mixed ratio of that arrival leg
```

**ধাপ ২ — arrival block-এর শেষ অংশ বদল (লাইন 2441–2447):**
```pine
if zoneTouch and bar_index - ctx.arrivalBar <= 10
    // v8.5.1 S1 — the verdict belongs to the side it was measured on, and rides in the zone snapshot,
    // so a CONFIRMED trigger that fires after price left the zone still sees the arrival of its tap
    zA = ctx.arrivalDir == 1 ? ft.zb : ft.zs
    if zA.kind != ""
        zA.arr    := ctx.arrivalStrong ? -1 : 1
        zA.arrMix := ctx.arrivalMixed
    ft.retestValid := ctx.lastBOSAvgBody > 0 and ctx.arrivalAvgBody < ctx.lastBOSAvgBody * cfg.retestBodyRatio
```
এরপর `Feat`-এর `arrivalWeak`, `arrivalStrong`, `arrivalMixed`-এর আর কোনো reader থাকবে না। এই তিনটা field মুছে দিন, token ফেরত আসবে।

**ধাপ ৩ — reader বদল:**

| লাইন | আগে | পরে |
|---|---|---|
| 2739 | `arrOkBull = not fl_M19 or not ft.arrivalStrong` | `arrOkBull = not fl_M19 or ft.zb.arr != -1` |
| 2740 | `arrOkBear = arrOkBull` | `arrOkBear = not fl_M19 or ft.zs.arr != -1` |
| 2741 | `pbOk = not fl_M26 or not ft.arrivalStrong or ft.arrivalMixed >= 0.35` | `pbOkL = not fl_M26 or ft.zb.arr != -1 or ft.zb.arrMix >= 0.35`<br>`pbOkS = not fl_M26 or ft.zs.arr != -1 or ft.zs.arrMix >= 0.35` |
| 2902, 2913, 2998 (LONG bid) | `pbOk` | `pbOkL` |
| 2920, 2927, 3008 (SHORT bid) | `pbOk` | `pbOkS` |
| 2865 / 2866 (M33) | `ft.arrivalWeak` | `ft.zb.arr == 1` / `ft.zs.arr == 1` |
| 2871 / 2872 (M36) | `ft.arrivalWeak` | `ft.zb.arr == 1` / `ft.zs.arr == 1` |
| 2963 / 2964 (M42) | `ft.arrivalWeak` | `ft.zb.arr == 1` / `ft.zs.arr == 1` |
| 3314 (f_conf POI) | `zz.depStrong and fv.arrivalWeak` | `zz.depStrong and zz.arr == 1` |
| 3321 (f_conf) | `sc -= fv.arrivalStrong ? 2 : 0` | `sc -= zz.arr == -1 ? 2 : 0` |
| 3864 (panel 4-factor) | `zz.depStrong and fv.arrivalWeak` | `zz.depStrong and zz.arr == 1` |
| 3885 (panel Arrival row) | `fv.arrivalWeak ? … : fv.arrivalStrong ? …` | `zArr = fv.zb.kind != "" ? fv.zb.arr : fv.zs.arr` → `zArr == 1 ? "WEAK ✅" : zArr == -1 ? "STRONG ❌" : "—"` |

**আচরণে কী বদলাবে:**
- CONFIRMED / MSS মোডে M33, M36, M42 আবার fire করতে পারবে। **Signal বাড়বে**, তাই regression দরকার (§4)।
- M19 filter CONFIRMED মোডেও কাজ করবে। ফলে **কিছু M08/M09/M01/M02/M39 signal কমবে**। এটা ইচ্ছাকৃত, আগে ভুল করে পাস হচ্ছিল।
- একই bar-এ দুই side-এর zone ছুঁলে শুধু bull side মাপা হয়। Bear side-এর `arr = 0` (unknown) থাকে, তাই M33/M36/M42 short ওই bar-এ fire করে না, আর M19 short block করে না। আগে ভুল side-এর verdict দেওয়া হতো, এখন "জানি না"। এটা নিরাপদ।

---

### S2 — PERF-1: PD array-এর 490-bar scan প্রতি bar-এ বন্ধ

**মূল কারণ:** লাইন 2409–2410:
```pine
pdHiB   = ta.highest(high, pdSpanB)   // pdSpanB 491 পর্যন্ত, প্রতি bar
pdLoS   = ta.lowest(low, pdSpanS)
```
পরিবর্তনশীল length-এর `ta.highest` প্রতি bar-এ পুরো window ঘুরে দেখে। ফলে প্রতি bar-এ প্রায় 1000 বার পড়া হয়। Script-এ এটাই সবচেয়ে বড় **সবসময়-চলা** loop। (বাকি বড় loop, যেমন `f_legOrigin` বা `f_moveStrength`, শুধু event-এ চলে।) আগের build-এ "Calculation timed out" এসেছিল, আর v8.5.0-এ RETRACE engine যোগ হওয়ায় চাপ আরও বেড়েছে।

**সমাধান — running extreme।** Loop শুধু তখন চলে যখন anchor বদলায় (BOS বা CHoCH, খুব কম হয়):
```pine
// v8.5.1 S2 (PERF-1) — the leg extreme since the protected swing, kept as a running max / min. The loop
// runs only when the anchor moves (a BOS / CHoCH), not on every bar like a series-length ta.highest.
f_legExt(isHi, fromIdx) =>
    span = math.min(math.max(bar_index - fromIdx, 0), 490)
    v = isHi ? high : low
    if span > 0
        for k = 1 to span
            v := isHi ? math.max(v, high[k]) : math.min(v, low[k])
    v

var float pdHiB = na
var int   pdHiAt = -1
var float pdLoS = na
var int   pdLoAt = -1
pdHiB  := ctx.majorLowIdx  != pdHiAt ? f_legExt(true,  ctx.majorLowIdx)  : math.max(pdHiB, high)
pdHiAt := ctx.majorLowIdx
pdLoS  := ctx.majorHighIdx != pdLoAt ? f_legExt(false, ctx.majorHighIdx) : math.min(pdLoS, low)
pdLoAt := ctx.majorHighIdx
```
- `pdSpanB` / `pdSpanS` লাইন মুছে দিন।
- `if span > 0` guard জরুরি: Pine-এ `for k = 1 to 0` উল্টো দিকে চলে (k = 1, 0), তাই guard ছাড়া ভুল bar পড়বে।
- নতুন main-scope `if` নেই। Ternary + function ব্যবহার করা হয়েছে, কারণ main scope local-scope সীমার কাছে।
- **Semantic পার্থক্য:** leg 490 bar-এর বেশি লম্বা হলে পুরোনো code সবচেয়ে পুরোনো bar ফেলে দিত, নতুন code পুরো leg-এর extreme রাখে। এটাই বেশি সঠিক (dealing range = পুরো leg)। এর বাইরে ফলাফল হুবহু এক।

`lowTap` / `highTap` (লাইন 2833) বদলানো হচ্ছে না। এদের length ≤ `i_poiBars + 1` (default 9), তাই খরচ নগণ্য।

---

### S3 — F18 fix-এ ছোট guard

v8.5.0 D1 (লাইন 2522) এই bar-এ mitigated FVG-কেও "at price" ধরে। এটা ঠিক। কিন্তু **FULL** মোডে candle পুরো gap ভেদ করে নিচে close করলেও এটা reaction ধরে নেয়।
```pine
            if g.isBull and low <= g.top and high >= g.bottom and close >= g.bottom
            ...
            if not g.isBull and high >= g.bottom and low <= g.top and close <= g.top
```
Gap-এর ভিতর দিয়ে close হয়ে বেরিয়ে গেলে সেটা reaction নয়, break। খরচ: 8 token।

---

### S4 — Grade B দৃশ্যমান করা

`i_gradeA` default **8 → 9** (লাইন 3176)। কোনো logic বদলায় না।
- 8 = **B** (minimum পাস করেছে) · 9–10 = **A** · ≥11 = **A+**
- এখন min score 8 = A threshold, তাই B label কখনো দেখা যায় না, আর সব signal "A" দেখায়। Grade তখন কোনো তথ্য দেয় না।

---

### S5 — যাচাইয়ের জন্য দুটো diagnostic plot

v8.5.0-এ 12টা plot (সীমা 64)। দুটো যোগ:
```pine
plot(ft.zb.arr * 1 + ft.zs.arr * 10, "S1 · arrival (bull ±1 · bear ±10)", display = display.data_window)
plot(ft.atBullFvg ? 1 : ft.atBearFvg ? -1 : 0, "D1/S3 · FVG reaction at price", display = display.data_window)
```
এগুলো দিয়ে chart-এ সরাসরি দেখা যাবে S1 আর F18 কাজ করছে কিনা। চাইলে পরের version-এ সরিয়ে ফেলা যায়।

---

### S6 — Strategy twin v8.5.1 (সবচেয়ে বড় বাস্তব gap)

দুটো document-ই বলে "expectancy, PF, drawdown মাপুন"। কিন্তু indicator এগুলো মাপতে পারে না, আর `SMC_Suite_v8.2.1_strategy.pine` চারটা version পুরোনো। Indicator যত ভালোই হোক, **প্রমাণ ছাড়া কোন module রাখবেন বা কাটবেন, সেটা অনুমান**।

Strategy twin-এর জন্য প্রস্তাব (indicator compile হওয়ার পরে আলাদা ফাইলে):
- Indicator-এর signal engine হুবহু copy। শুধু drawing, panel, alert বাদ, যাতে token খালি হয়।
- `strategy.entry` + `strategy.exit(stop = sl, limit = tp1)`। TP1-এ partial, বাকিটা TP2-এ।
- `commission_value`, `slippage` input। `process_orders_on_close = false`।
- **একই candle-এ SL ও TP দুটোই ছুঁলে → SL ধরা হবে** (conservative)। Pine-এ intrabar order জানা যায় না।
- Limit entry (CANDLE 50% / ZONE EDGE / RETRACE): fill না হলে trade নেই।
- **Per-module ফলাফল:** module নাম `strategy.entry`-এর `comment`-এ দিন। TradingView-এর List of Trades export করে module অনুযায়ী R গুণে নিন। Strategy-তে array দিয়ে module-ভিত্তিক count রাখলে token খরচ বাড়ে।

এটাই doc-2-এর §10 "Validation Metrics" বাস্তবে করার একমাত্র পথ।

---

## 3. কী করা হচ্ছে না, আর কেন

| প্রস্তাব | সিদ্ধান্ত | কারণ |
|---|---|---|
| v8.4.1-এ সরাসরি fix | ❌ | v8.5.0 আগেই অনেক fix করেছে; দুটো branch হয়ে যাবে |
| Signal বাড়াতে module rank বাড়ানো | ❌ | Doc-2-এর সাথে একমত। S6-এর প্রমাণ ছাড়া rank বদল নয় |
| Zone multi-factor ranking | ⏸ defer | CPU + `Ctx` cap। S6 দেখালে তখন |
| W13 London session H/L | ⏸ defer | v8.5.0-এই defer করা (+40 token) |
| Repaint audit | ✅ শুধু test হিসেবে (§4 T6) | Source-এ সব signal / line / alert `barstate.isconfirmed` gated, HTF `[1]` + `lookahead_on`। Code বদলের দরকার পাওয়া যায়নি |

---

## 4. Test plan (প্রতিটা fix-এর জন্য chart-এ কী দেখবেন)

একই symbol/TF-এ **v8.5.0 আর v8.5.1 পাশাপাশি** দুটো আলাদা indicator হিসেবে চালান। প্রস্তাবিত: XAUUSD 5m, EURUSD 5m, BTCUSDT.P 5m, NAS100 15m।

| # | যা যাচাই করবেন | কীভাবে | পাস হবে যদি |
|---|---|---|---|
| T0 | Compile | Pine editor → Save → token count নোট করুন | Error নেই, token ≤ 100,256 |
| T1 | Runtime | 5m chart, সর্বোচ্চ history | "Calculation timed out" আসে না |
| T2 | S2 PD array | Data window "PD array" দুটো version-এ একই bar-এ মিলিয়ে দেখুন | 490 bar-এর কম leg-এ হুবহু এক |
| T3 | S1 confirm বাইরে | CONFIRMED মোড, POI tap → zone-এর বাইরে confirm bar খুঁজুন | "S1 · arrival" plot ≠ 0, আর M36/M42 এখন fire করতে পারে |
| T4 | S1 M19 | STRONG arrival (`-1`) zone-এ confirm | ওই side-এর M08/M09 signal নেই |
| T5 | S3 FVG | FULL mode, gap ভেদ করে close-এর bar | "FVG reaction" plot = 0 |
| T6 | Repaint | Live bar-এ signal দেখুন → chart reload | Label, entry, SL, TP আর alert সব এক |
| T7 | Signal count | Data window reject code ধরে 500 bar-এ গুনুন | পার্থক্য S1-এর ব্যাখ্যার সাথে মেলে (M33/M36/M42 ↑, M19-blocked ↓) |
| T8 | Grade | কোনো 8-score signal | Label-এ "B" দেখায় |

---

## 5. বাস্তবায়নের ক্রম

**ধাপ 0 — আগে v8.5.0 compile করুন।** v8.5.0 compile হয়েছে কিনা, token কত, timeout আসে কিনা, এর কোনো রেকর্ড নেই। এটা না জেনে নতুন কিছু যোগ করা ঝুঁকিপূর্ণ।
- Timeout এলে → আগে শুধু **S2** দিয়ে v8.5.1 বানাতে হবে।
- Token সীমার কাছে থাকলে → নিচের cut list।

**ধাপ 1 — `SMC_v8.5.1.txt`** (নতুন ফাইল, v8.5.0 অক্ষত থাকবে):
S2 → S1 → S3 → S4 → S5, header-এ changelog, line 2-এ BUILD stamp।

**ধাপ 2 — Compile + T0–T8।**

**ধাপ 3 — S6 strategy twin** (আলাদা ফাইল), তারপর 3–6 মাসের data-য় per-module R।

**ধাপ 4 — S6-এর প্রমাণ দেখে** কোন module কাটবেন, rank বদলাবেন বা default OFF করবেন।

### আনুমানিক token হিসাব
| বদল | Token |
|---|---|
| S1: ZS +2 field, block, reader | +60 |
| S1: Feat থেকে 3 field মুছে ফেলা | −25 |
| S2: function + 4 var, 2 লাইন মুছে ফেলা | +45 |
| S3 | +8 |
| S5: 2 plot | +25 |
| **মোট** | **≈ +115** |

### Token সীমা পার হলে cut list (presentation-only আগে)
1. S5-এর plot দুটো (যাচাই শেষে)
2. `f_legend` + `d_legend` input (default OFF, ≈150 token)
3. HTF OHLC line drawing (`d_htf`)
4. M58 (double top/bottom, tier 2)

---

## 6. Definition of Done (doc-2 থেকে, এই project-এর সাথে মিলিয়ে)

- [ ] Source-এর লাইন নম্বরসহ root cause লেখা আছে (উপরে আছে)
- [ ] নতুন versioned ফাইল; পুরোনো ফাইল অক্ষত
- [ ] TradingView-এ compile হয়; token count নোট করা
- [ ] Timeout নেই
- [ ] T0–T8 পাস
- [ ] Alert আর chart label একই confirmed event-এ
- [ ] Changelog-এ before/after
- [ ] Strategy twin-এর প্রমাণ ছাড়া "বেশি profitable" দাবি নয়

---

## সারসংক্ষেপ

দুটো document-এর তালিকার বেশিরভাগ **v8.5.0-এ আগেই ঠিক হয়ে গেছে**। আসলে বাকি আছে দুটো বাস্তব সমস্যা:
1. **F19 (+W15):** CONFIRMED মোডে arrival হারিয়ে যায় আর দুই side-এ shared থাকে। সমাধান: arrival-কে `ZS` snapshot-এর ভিতরে প্রতি side আলাদা করে রাখা। কোনো নতুন state machine লাগে না।
2. **PERF:** PD array-এ প্রতি bar-এ 490-bar scan। সমাধান: running extreme, loop শুধু anchor বদলালে চলে।

তার সাথে ছোট তিনটা জিনিস: S3 guard, S4 grade, S5 diagnostic plot। আর সবচেয়ে বড় অনুপস্থিত জিনিস হলো **S6 strategy twin**। এটা ছাড়া কোন setup আসলে কাজ করে, সেটা শুধু অনুমান।
