# Entry Review · `liqudity_trap_trading.v3.8.4.txt` — ৪টা live chart থেকে কী শেখা গেল

তারিখ: 2026-10-16 · Chart: XAUUSD · BTCUSDT · NAS100 · USOIL, সব M5, সময় 16:20 BD = **06:20 NY**
File: `liqudity_trap_trading.v3.8.4.txt` (BUILD v3.8.4-b1)। সব line number এই file-এর।
আগের review: `REVIEW_v3.8.4_BN.md` (bug / token-cut)। এই doc শুধু **entry coverage + smart-money footprint** নিয়ে। পুরনো item আবার লেখা হয়নি।

---

## 0. সংক্ষেপ

- **৪টা chart, ৪টাই Verdict = NO, Setup = idle (XAU-তে একটা SWEPT)।** Code অনুযায়ী প্রতিটা verdict সঠিক। কিন্তু **৩টাতে dashboard ভুল কারণ দেখাচ্ছে** ("score X < 50"), আসল blocker অন্য জায়গায়। Operator ভুল জিনিসের জন্য অপেক্ষা করবে।
- **৪টার মধ্যে ৩টা (BTC, NAS, USOIL) একই ধরনের setup: trend-এর ভেতরে pullback, price HTF POI / next zone-এর ভেতরে, HTF bias align, LTF trigger আছে।** এটা SMC-র সবচেয়ে common continuation entry (HTF POI → LTF CHoCH → FVG → CE)। Indicator-এ এই path **নেই**। পুরনো audit-এর "design gap: reversal-only" এখন live chart-এ দেখা যাচ্ছে।
- **FEM (Fractal Entry Model) default setting-এ কার্যত মৃত।** Sweep ছাড়া `f_tier` কখনো A দেয় না (L3646: `liq >= 10` লাগে), আর `tierMode = "A and above"`। USOIL-এ FEM "FVG locked" পর্যন্ত গেছে, তবু fire করত না।
- **CHOP regime trend-pullback-কে chop পড়ছে** (USOIL)। 9300 → 9730 rally-র পর ৪০ bar consolidation = CHOP → সব long block। Continuation entry ঠিক এখানেই হয়।
- **সব chart 06:20 NY = "off-hours"।** London KZ 02–05, NY AM 07–10। মাঝের ফাঁকে `sesPts = 0` (L3509) → score −5, A+ অসম্ভব (L3512), SB off-window। এটা bug না, কিন্তু আপনার trading hour-এর সাথে config মিলছে না।
- **প্রস্তাব (§3):** একটা continuation arm path machine-এ (FEM-এর বদলে), stage-aware verdict text, displaced internal shift, chop-এ trend-pullback exemption, SMT divergence sweep grade। Net token ≈ 0 (FEM কাটা −250 + E4 −300 দিয়ে পরিশোধ)।

---

## 1. Chart-by-chart পড়া

### 1.1 XAUUSD M5 — "NO · L: score 25 < 50 · SWEPT · ADR 61%"

Dashboard: Bias 60 Bull · D Bear · str Bear → **—** (neutral)। Struct int▼ ext▼ · SSL strong · BSL strong। Disc 49%। Next demand T2 OB **4.5 ATR**। Trigger CHoCH▼। Setup **L SWEPT** / S idle। L 25 (C), S 45 (B)।

Code অনুযায়ী ঠিক আছে? **হ্যাঁ, কিন্তু কারণটা ভুল দেখানো হচ্ছে।**

- Stage 1 (SWEPT)-এ score 50 হওয়া **অসম্ভব**: POI 20 + Trigger 20 + Exec 10 সব শূন্য থাকে stage 2–3-এর আগে। Score gate (`minScore`) শুধু stage 4-এ পড়া হয় (MODULE 18)। তাই L5550-এর "score 25 < 50 · SWEPT" line একটা অর্থহীন সংখ্যা দেখাচ্ছে।
- আসল blocker তিনটা, কোনোটাই dashboard-এ নেই:
  1. **Bias neutral + ext▼ → `biasOkL = false`** (L2209)। `armBiasL` (L2216) দিয়ে arm হয়েছে (FIX-A3), কিন্তু entry gate `biasOkL` পড়ে। ext ▲ না হলে এই long **কখনো** entry পাবে না। Dashboard বলছে না।
  2. **SSL strong আর BSL strong দুটোই in play।** `suL == 1` অবস্থায় যদি BSL sweep (Q ≥ 2) আসে → "range swept both ways" (L4195)। ইতিমধ্যে দুটোই in play থাকলে narrative নেই।
  3. **Next demand 4.5 ATR নিচে।** `liqWait = 20` bar-এ tapZone অসম্ভব। একমাত্র রাস্তা `fastShift` (MSS▲ / ext CHoCH▲)। ext▼ থেকে ext CHoCH▲ হতে `extPivIn = 12` bar confirmation লাগে = ১ ঘণ্টা।
- Chart observation: 4147 → 4183, ৩৬ point rally, ৫–৬টা BOS▲, তবু **ext▼**। M5-এ `extPivIn = 12` মানে প্রতিটা external swing-এ ১ ঘণ্টা lag। Regime পড়ছে TRANSITION। XAU M5-এর জন্য 12 বেশি।

**Operator-এর জন্য সঠিক text হত:** `L: SWEPT · ext▼ blocks entry · POI 4.5 ATR far · need MSS▲`

### 1.2 BTCUSDT M5 — "NO · score 30 < 50 · ADR 38%"

Dashboard: Bias Bear · D Bull · str Bear → **Bear**। int▼ ext▲ · **SSL weak**। Disc 42%। Next supply T2 IFVG 2.1 ATR — chart label বলছে **"SELL T2 IFVG 81895–82108 (INSIDE)"**, অর্থাৎ price এখন supply-র ভেতরে। Trigger BOS▼। Setup idle / idle।

Code অনুযায়ী ঠিক? **হ্যাঁ। কারণ ভুল।**

- আসল কারণ: **SSL weak = Q1 < `minArmQual` 2** (L792) → long arm হয়নি। BSL নেই → short arm হয়নি। Score line (L5561) পড়ার আগে এই কথাটা বলা উচিত ছিল।
- **Short continuation setup হাতছাড়া:** HTF Bear, price next-supply IFVG-র ভেতরে, BOS▼ trigger। এটা "internal range liquidity → supply → continuation" model। Machine arm হয় শুধু `bslInPlay` থাকলে (L4377)। BSL নেই → কিছুই হবে না।
- S/D engine (`sigSDShort`, zone 50% tap) fire করতে পারত। কিন্তু `engOKS` (L4582) `tierShort >= 3` চায়, আর tier 3-এর শর্ত `liq >= 10` (L3646) = `bslInPlay`। **Sweep ছাড়া কোনো engine A হয় না।** Default `tierMode = "A and above"` → সব continuation engine candidate filter হয়ে যায়।

### 1.3 NAS100 M5 — "NO · score 25 < 50 · ADR 56%"

Dashboard: Bias Bear · D Bear · str Bear → **Bear** (সব align)। int▼ ext▼ · **no sweep**। Disc 43%। Next supply T2 MIT 2.5 ATR। Trigger **CHoCH▼ · ◎ POI tap**। Chart: price "HTF 60 supply · fresh"-এর ভেতরে, "Asia H broken", "Lon H"।

Code অনুযায়ী ঠিক? **হ্যাঁ। এটা সবচেয়ে পরিষ্কার missed-setup।**

- FEM stage 1 (POI tap, L5506 text)। সামনে: LTF shift (`cisdDn / chochDn / bosDn / mssDn`) → FVG lock → retest → `sigFEMShort`।
- `sigFEMShort` fire করলেও দুটো gate-এ মরবে:
  1. **Tier:** `liq = 0` (no sweep) → `f_tier` সর্বোচ্চ 2 (B) → `engOKS` false। **Default-এ FEM কখনো signal দিতে পারে না যদি একই সময়ে sweep না থাকে।**
  2. **Score:** ctx 25 (HTF 10 + ext 10 + ses 0 + PD 5) + POI 0 (HTF POI "Next supply" নয়, next = T2 MIT) + trig ≈ 9 + exec 5 ≈ **39 < 50**।
- HTF POI-কে `poiShort`-এ গোনার একমাত্র রাস্তা `nextInclHtf` (L850) দিয়ে Next level হওয়া। এখানে chart-TF MIT আগে আছে, তাই HTF POI score-এ শূন্য। Setup HTF POI-র উপর দাঁড়িয়ে, score সেটা দেখছে না — FIX-W2 (L3520+) যে সমস্যা machine-এ ঠিক করেছিল, FEM-এ সেটা রয়ে গেছে।

### 1.4 USOIL M5 — "NO · chop · ADR 27%"

Dashboard: regime **CHOP**। Bias Bull · D Bull · str Bull → **Bull** (সব align)। int▲ ext▲ · BSL valid। Disc 42%। Next demand **T3 HTF 0.2 ATR** — chart label "BUY T3 HTF 9531–9561.5 (INSIDE)"। Trigger BOS▲ · ◎ **FVG locked**। Setup idle / idle।

Code অনুযায়ী ঠিক? **হ্যাঁ। এটা ৪টার মধ্যে সবচেয়ে ভালো setup, আর দুইবার block।**

- FEM stage 3 (FVG locked) — HTF demand tap হয়েছে, LTF shift হয়েছে, FVG lock হয়েছে। শুধু retest + confirmation বাকি। সব HTF bias align। Discount। এটা textbook continuation long।
- Block 1: **`chopOKL`** (L4478) = `regime != "CHOP" or instSweepL or SB`। `instSweepL` = RAW Q ≥ 3 sweep + MSS। নেই। SB window নয়। → false।
- Block 2: **Tier** — `liq = 0` → B → `engOKL` false (1.3-এর মতো)।
- CHOP read নিজেই প্রশ্নযোগ্য: `regChop` (L2618) = ৪০ bar-এ external event নেই + ext range < 6 ATR + leg narrow + price ext range-এর ভেতরে। 9300 → 9730 thrust-এর পর ৪০ bar সরু consolidation = ঠিক এই শর্ত। কিন্তু **HTF-এ এটা trend-এর ভেতরে pullback / flag, chop না।** `regChop` HTF bias / HTF structure দেখে না। FIX-T12 / T16 নিজের leg দেখে, উপরের timeframe দেখে না।

### 1.5 সব chart-এ common

| বিষয় | প্রভাব | কোথায় |
|---|---|---|
| 06:20 NY = off-hours | `sesPts = 0` → −5 score; `sesTierOK = false` → A+ অসম্ভব; SB off-window | L3509, L3512, L900–901 |
| Verdict "score X < 50" idle / stage 1-3-এ | Operator ভুল জিনিস দেখে | L5550, L5561 |
| Continuation path নেই | ৩/৪ chart-এর setup invisible | MODULE 17 arm L4223 / L4377 |
| Engine tier-এ `liq >= 10` বাধ্যতামূলক | sweep ছাড়া কোনো engine A হয় না → FEM, S/D, IB, CRT সব default-এ sweep-dependent | L3646 |

---

## 2. Smart-money footprint — এখন কী আছে, কী নেই

| Footprint | অবস্থা | মন্তব্য |
|---|---|---|
| Liquidity sweep + grade 1–4 (reclaim, penetration, outer-30% close, displacement, volume) | আছে, ভালো | `f_sweepQual` L1588 |
| Engineered pool kind (EQ / PD / PW / session) | আছে | `lastSslKind` |
| Displacement + FVG left behind | আছে | `cFvgBDisp`, `dispFactIn` 1.2 ATR |
| CISD / IFC (delivery change, funding candle) | আছে | MODULE 3 |
| MSS / BOS / CHoCH, internal + external | আছে | ext lag বেশি M5-এ (§1.1) |
| OB / RB / Breaker / IFVG / HTF FVG POI | আছে | registry ভালো |
| Premium / discount, OTE | আছে | |
| Killzone / SB window | আছে | config আপনার hour-এর সাথে মিলছে না |
| Relative volume | আছে, **OFF** | `useVol = false` L1120। BTC-তে real volume — crypto profile-এ ON দেওয়া উচিত |
| **Continuation (internal liquidity run / Model D)** | **নেই** | §3 S-1 |
| **SMT divergence** (XAU↔XAG/DXY, NAS↔ES, BTC↔ETH) | **নেই** | sweep-এর সবচেয়ে শক্ত footprint। §3 S-5 |
| **Next liquidity pool** (price কোথায় যাবে) | **নেই** dashboard-এ | Next demand / supply আছে, কিন্তু "কোন pool-এ raid হবে" নেই। §3 S-6 |
| PO3 / true-day-open / NWOG-NDOG | নেই | পুরনো deferred list-এ। এখনো P4 |

---

## 3. প্রস্তাব (priority অনুযায়ী)

নিয়ম (memory): নতুন `if` scope না, নতুন plot / alertcondition না, প্রতিটা addition presentation-only cut দিয়ে পরিশোধ।

### S-1 · P1 · Continuation arm path — FEM-এর বদলে machine-এ

**কী:** HTF POI tap + HTF bias/structure align = machine-এর stage 1 হিসেবে গোনা, sweep ছাড়া। তারপর বাকি সব এক: POI tap (stage 2) → shift (stage 3) → shift-leg FVG anchor → CE limit entry → FIX-X4 stop → tracker।

**কেন machine-এ, FEM-এ না:** Machine-এ gate-kill retry (FIX-V8), CE limit (FIX-X3), raid/anchor stop (FIX-X4), slippage guard, min RR, journal, dashboard stage — সব আছে। FEM-এ এর কিছুই নেই, আর FEM-এর stop wick-এর ভেতরে (পুরনো C8)। FEM কেটে দিলে ≈ −250 token, একটা `var` block কমে।

**Design (long side; short mirror):**

```
// MODULE 17, arm condition L4223 — একটা `or` যোগ
contArmL = contOn and htfB > 0 and hsDir > 0 and tapHtf_pre and lockOkL and not bslInPlay
//   tapHtf_pre = htfLive and not na(hPoiBTop) and low <= hPoiBTop and close > hPoiBBot   (L4251-এর copy, arm-এর আগে দরকার)
if suL == 0 and ((sslInPlay and sbArmBarL and (...)) or contArmL) and ...
    suL := 1
    suLSweepLvl := contArmL ? hPoiBBot : lastSslLvl        // POI-র distal edge = premise
    suLSweepExt := contArmL ? hPoiBBot - NEAR_LVL_ATR * atr : lastSslExt
    suLCont     := contArmL                                 // নতুন var bool
```

- একই bar-এ `if suL == 1` block (L4251) `tapHtf` দেখে → stage 2। Anchor = HTF POI। কোনো নতুন branch লাগে না।
- Invalidation নিজে থেকে ঠিক কাজ করে: "sweep undone" = close < POI distal − tol = **POI violated**। "sweep reclaim lost" একই অর্থ। "range swept both ways" = POI-তে বসে থাকা অবস্থায় opposite raid → ঠিকই kill।
- `fastShift` path (L4223-এর পরের block) `sslInPlay` চায় → cont-এ কাজ করবে না। ঠিক আছে: continuation-এ POI stage জরুরি।

**Score / tier fairness:**

```
liqLong  := suLCont and suL >= 1 ? math.max(liqLong, 10) : liqLong     // POI-র internal liquidity = sweep-এর সমান weight
```

- `f_tier` (L3646) এখন A দিতে পারবে। `f_mcTier` (L4521): `qualOk` / `poolOk` cont-এ false → **A+ হবে না**। ঠিক: continuation A, reversal-with-raid A+।
- Strictness রাখুন: `mcReqPD` (discount লাগবে), `mcFvgDisp` (shift-leg FVG displacement-এ কাটা), `mcStrictCnf` — সব existing gate প্রযোজ্য।

**Input:** `contOn = input.bool(true, "Machine: HTF POI tap may arm without a sweep (continuation)")` — ১টা।
**Token:** ≈ +180 (arm ternary ×2 side, var ×2, liq override ×2, input, verdict text)। FEM কাটলে −250। **Net ≈ −70।**
**Test:** USOIL chart (1.4) — FEM FVG locked অবস্থা → machine-এ stage 3 হত। NAS (1.3) — stage 2 হত। BTC (1.2) — hPoi না থাকলে না; chart-TF next-zone-কে cont POI ধরা **দ্বিতীয় ধাপ**, আগে HTF POI দিয়ে মাপুন।

### S-2 · P1 · Verdict row: stage-aware "next step" text

**কী:** L5550 আর L5561-এর "score X < 50" বদলে যা আসলে আটকাচ্ছে তা, আর পরের ধাপ।

```
// idle, sweep আছে কিন্তু arm হয়নি
sslInPlay and suL == 0 and lastSslQual < minArmQual ? "NO · SSL " + f_qualTxt(lastSslQual) + " < arm Q" + str.tostring(minArmQual)
// stage 1-3: পরের ধাপ + entry gate-এর pre-check
suL == 1 ? "L: SWEPT · wait POI " + nbTxt + (not biasOkL ? " · ext▼ blocks entry" : "")
suL == 2 ? "L: AT POI · wait MSS▲ / CHoCH▲" + ...
suL == 3 ? "L: SHIFTED · wait CE " + str.tostring((suLAnchorT + suLAnchorB) / 2, format.mintick)
```

- Score শুধু stage 4 gate-kill-এ দেখান (সেখানে `f_gateKill` ইতিমধ্যে দেখায়)।
- `biasOkL` pre-check (1.1-এর blocker #1) stage 1 থেকেই বলা যায়।
- **Token:** ≈ +80 (সব ternary / string, নতুন `if` নেই)। পরিশোধ: L5550–5562 chain-এর কিছু branch merge।

### S-3 · P2 · Ordinary machine-এ displaced internal shift

**কী:** SB path-এ ইতিমধ্যে আছে (`sbShiftUp` L4141: internal CHoCH / CISD + bull bar + body ≥ 0.8 ATR)। Ordinary path শুধু MSS / external CHoCH (L4130)। M5-এ external CHoCH ১ ঘণ্টা lag (§1.1)।

```
mcDispShift = input.bool(true, "Machine: displaced internal CHoCH / CISD counts as the SHIFT")
shiftUpOk := shiftUpOk or (mcDispShift and (chochUp or cisdUp) and bullBar and body >= dispFactor * atr and bullFVG)
```

- `bullFVG` শর্ত = shift candle নিজে FVG রেখে গেছে → footprint। `shiftSrc = "+ internal CHoCH"` এখনই set করা যায় কিন্তু displacement filter ছাড়া noisy।
- **Token:** ≈ +40।
- **এখনই config দিয়ে test:** `shiftSrc = "+ internal CHoCH"`, `structDisp = 0.8`। Journal-এ entry count আর stop-out দেখুন।

### S-4 · P2 · CHOP-এ trend-pullback exemption

**কী:** `chopOKL` (L4478)-এ একটা `or`:

```
chopOKL = ... or instSweepL or (sbEnable and sbChopBypass and sbSigLong)
     or (htfB > 0 and hsDir > 0 and bD > 0 and suLCont)          // HTF trend-এর ভেতরে pullback chop না
```

- শুধু cont path-এ (S-1), তিন HTF read align হলে। Reversal / sweep path-এ chop rule আগের মতোই।
- Machine arm-এর `chopBlock` (L4225)-এও একই exemption লাগবে, না হলে arm-ই হবে না।
- **Token:** ≈ +30।
- বিকল্প (বড় পরিবর্তন): `regChop`-এ `and not (htfB != 0 and hsDir == htfB)` — regime নিজেই HTF trend দেখুক। Dashboard regime cell বদলাবে। আপনার সিদ্ধান্ত।

### S-5 · P3 · SMT divergence → sweep grade +1

**কী:** correlated symbol input (`smtSym`, "" = off)। `request.security(smtSym, timeframe.period, [high[1], low[1]], lookahead = barmerge.lookahead_on)`। Chart-এ swing low sweep হলো, correlated symbol তার নিজের last pivot low ভাঙেনি → SMT বুল। `f_sweepQual`-এর পরে: `q := smtBull and q >= 2 ? math.min(3, q + 1) : q`। Dashboard sweep text-এ " ·SMT"।

- Pair: XAUUSD↔XAGUSD (বা DXY উল্টো), NAS100↔US500, BTC↔ETH, USOIL↔UKOIL।
- Correlated symbol-এর pivot: `ta.pivotlow(smtLo, pivLen, pivLen)` — একটা `var float` latch।
- **Token:** ≈ +120। `request.security` 7 → 8। Output slot বদলায় না।
- পুরনো deferred list-এ ছিল। এখন E4 (−300) দিয়ে জায়গা হয়।

### S-6 · P3 · Dashboard "Next pool" row

**কী:** price-এর উপরে nearest unswept BSL (session H, PDH, EQH, ext swing high) আর নিচে nearest SSL, ATR distance সহ। "Smart money কোথায় যাবে" — এটাই footprint-এর অর্ধেক।

```
nearBsl = math.min(pdh > close ? pdh : na, sesHiLive > close ? sesHiLive : na, eqhNear > close ? eqhNear : na, extRes > close ? extRes : na)   // na-safe min লাগবে
```

- Table 2×12 → 2×13 (table output budget-এ পড়ে না)।
- **Token:** ≈ +120 (na-safe min ৪ term × ২ side)।

### S-7 · P3 · Config (code নেই)

| Setting | এখন | প্রস্তাব | কেন |
|---|---|---|---|
| `lonSes` (L900) | 0200-0500 | **0200-0700** বা trading hour 07:00–11:00 NY (17:00–21:00 BD) | আপনার screenshot সময় off-hours; sesPts 0, A+ বন্ধ |
| `extPivIn` (L730) | 12 | **8** M5-এ (XAU / NAS) | ext structure ১ ঘণ্টা lag (§1.1) |
| `useVol` (L1120) | false | **true** BTC profile-এ | real volume আছে |
| `shiftSrc` (L1002) | MSS / external CHoCH | "+ internal CHoCH" (S-3 আসা পর্যন্ত) | M5-এ shift দ্রুত |
| `tierMode` (L979) | A and above | রাখুন। S-1 ছাড়া "B and above" করলে noise বাড়বে | |
| `minScore` (L987) | 50 | রাখুন। S-1-এর liq override-এ cont setup 50 পাবে | |

---

## 4. Token হিসাব

| Item | Token | Signal বদলায়? |
|---|---|---|
| FEM module কাটা (MODULE 15, L3377–3449 + `sigFEM*` gate / label / alert refs) | **−250** | হ্যাঁ: FEM signal বন্ধ (default-এ এমনিতেই fire করে না, §1.3) |
| E4 exit block dedupe (পুরনো review) | **−300** | না |
| S-1 cont path | +180 | হ্যাঁ |
| S-2 verdict text | +80 | না (display) |
| S-3 displaced shift | +40 | হ্যাঁ |
| S-4 chop exemption | +30 | হ্যাঁ |
| S-5 SMT | +120 | হ্যাঁ (grade) |
| S-6 next pool row | +120 | না (display) |
| **Net** | **≈ +20** | |

Output slot: 53/64, অপরিবর্তিত। `request.security`: 7 → 8। নতুন input: 3 (`contOn`, `mcDispShift`, `smtSym`)।

---

## 5. Version plan-এ কোথায় বসবে

আগের plan (REVIEW_v3.8.4_BN.md §7): v3.8.5 token-cut → v3.8.6 stop/tracker → v3.8.7 filters → v3.8.8 measure-first।

| Version | যোগ |
|---|---|
| v3.8.5 (token-cut) | FEM কাটা এখানেই (−250)। S-2 verdict text (display only) |
| v3.8.7 (filters) | **S-1 cont path + S-4 chop exemption + S-3 displaced shift** — একসাথে, কারণ তিনটা একই setup-এ কাজ করে |
| v3.8.8 (measure) | S-5 SMT, S-6 next pool। Journal দিয়ে cont entry-র win-rate আলাদা মাপুন (`LQJRNL` line-এ cont flag যোগ করুন) |

**S-1 আগে কেন:** ৪টা chart-এর ৩টা এই path-এ পড়ে। বাকি সব improvement এর তুলনায় ছোট।

---

## 6. Test checklist (S-1 compile হলে)

1. USOIL M5 (1.4 chart) replay: HTF demand tap → `Setup L` "AT POI" দেখাবে, chop থাকলেও। shift → "SHIFTED·await retest" → CE touch → LONG signal, tier A (A+ না)।
2. NAS100 M5 (1.3): HTF supply tap → `Setup S` "AT POI"। CHoCH▼ → stage 3। Dashboard-এ "score" আর দেখাবে না stage 1–3-এ।
3. XAU (1.1): SWEPT অবস্থায় verdict "ext▼ blocks entry" দেখাবে।
4. BTC (1.2): "SSL weak < arm Q2" দেখাবে।
5. Cont setup-এ `f_mcTier` A+ **না** দেয় — journal-এ tier column দেখুন।
6. Cont arm হওয়ার পর opposite sweep Q ≥ 2 → "range swept both ways" reason।
7. HTF POI-র distal edge-এর নিচে close → "sweep undone" reason (text বদলে "POI violated" করা যায়, +10 token)।
8. CE10117 হলে cut order: S-6 → S-5 → S-3 → S-2 → তারপর S-1 ছোট করুন।

---

## 7. BUILD — `liqudity_trap_trading.v3.8.5.txt` (2026-10-16, uncompiled)

BUILD stamp line 2: `v3.8.5-b1`। Pine editor-এ এই line না দেখলে পুরনো code আছে।

**যা ঢুকেছে:** S-1 (cont arm, FEM removed), S-2 (verdict next-step), S-3 (`mcDispShift`), S-4 (chop pullback exemption)। **বাদ:** S-5 SMT, S-6 next-pool row (v3.8.8-এ), E4 dedupe (v3.8.5 token-cut আলাদা করে করা হয়নি — FEM cut দিয়েই পরিশোধ)।

| বদল | কোথায় (v3.8.5 line) |
|---|---|
| `contOn` input (grpFE), `mcDispShift` input (grpQ) | 888, 1051 |
| `suLCont / suSCont` state | 3438–3439 |
| Score: cont setup-এ `liqLong/Short` ≥ 10 | 3546–3547 |
| `shiftUpOk/DnOk` += displaced internal CHoCH/CISD + FVG | 4110–4111 |
| `contTapL/S`, `contTrendL/S`, `contArmLvlL/S`, `contArmL/S` | 4117–4126 |
| Long arm: `stdArmL or contArmL`, premise = POI distal, once per POI | 4213–4231 |
| Short arm mirror | 4371–4389 |
| `chopOKL/S` += `suXCont and contTrendX` | 4476, 4478 |
| FEM: MODULE 15 body, `sigFEM*`, `slFEM*`, label, boxes, 2 alertcondition — removed | — |
| Dashboard row 6 "Trigger · ◎ HTF POI" (cont L / cont S / HTF dmd tap / HTF sup tap) | 5486–5488 |
| Verdict: stage + next step + "⚠ bias blocks entry"; idle "SSL weak < arm Q2"; score line বাদ | 5520–5545 |
| Alert "[SETUP] ◎ Continuation armed (HTF POI)" (FEM FVG locked-এর জায়গায়) | 5621 |
| Journal engine tag `MCc` (continuation machine entry) | 5651 |

Output: 53 → **52/64**। `request.security`: 7 (অপরিবর্তিত)। নতুন `if` scope: 0 (FEM-এর ~20টা গেছে)।

**Reason string (debug table):** cont setup-এ "sweep undone" → **"HTF POI violated"**। "sweep reclaim lost" / "range swept both ways" / "opposing displacement" আগের text-এই, অর্থ একই।

**জানা সীমাবদ্ধতা (test-এ দেখুন):**
1. "opposing displacement" (FIX-X6) cont setup-এও চলে। Demand-এ নামার সময় 1.2 ATR bear body stage 2-এ setup মারবে। Continuation-এ এটা বেশি হবে। যদি journal-এ "opposing displacement" কারণে cont setup বেশি মরে, stage 2 cont-এ এই check waive করা পরের ধাপ (+15 token)।
2. Cont arm `bD` (daily bias) দেখে না; শুধু chop bypass দেখে। BTC-র মতো D উল্টো থাকলে arm হবে, chop-এ block হবে।
3. `hPoiMaxTouch = 2` → একই POI দুই visit-এর পর spent। `contArmLvlL` তার উপরে once-per-POI।
4. USER_MANUAL (v3.6, `_4/Liqudity/`) update হয়নি: FEM row, "Trigger · FEM" label, verdict text বদলেছে।

**CE10117 হলে cut order:**
1. `contOn` tooltip + `mcDispShift` tooltip (−60)
2. Verdict `nextL / nextS`-এর CE price text → শুধু "wait CE" (−40)
3. `armTxt` branch (−40)
4. `biasPre` (−20)
5. S-3 `shiftUpOk/DnOk` override (−40)
6. তারপর REVIEW_v3.8.4_BN.md §4 E4 exit dedupe (−300)
