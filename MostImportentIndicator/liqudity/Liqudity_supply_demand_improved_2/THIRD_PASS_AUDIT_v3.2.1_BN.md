# LQ-SD-PA v3.2.1 — তৃতীয় পাস ফরেনসিক অডিট (একদম নতুন করে)

> ফাইল: `Liqudity_supply_demain_improv/version_02_fixed.pine` — 4,807 লাইন, v3.2.1 (ফেজ A–D প্রয়োগের পরের কোড)
> পদ্ধতি: পুরো ফাইল লাইন-বাই-লাইন পাঠ, আগের দুই অডিট (REVIEW_AND_PLAN / DEEP_AUDIT) **না দেখে** — শুধু শেষে ওভারল্যাপ বাদ দেওয়া হয়েছে।
> ফোকাস: **entry accuracy** — কোথায় ভালো সিগন্যাল মরে, কোথায় খারাপ সিগন্যাল বাঁচে, আর চার্টের সংখ্যা কোথায় বাস্তব এক্সিকিউশনের সাথে মেলে না।

⚠️ নোট: `Liqudity_supply_demand_improved_2/version_01_1.txt` = **v3.2.0**, এক ভার্সন পুরোনো (md5 মিলে গেছে `improv/version_01_1.txt`-এর সাথে)। কাজের ফাইল `version_02_fixed.pine`।

---

> ✅ **স্ট্যাটাস (v3.2.2):** নিচের P0 তিনটা, P1 নয়টার মধ্যে সাতটা আর P2-র চারটা প্রয়োগ হয়েছে —
> `version_03_v3.2.2.pine` + `version_03_strategy_v3.2.2.pine`। বিস্তারিত: `CHANGELOG_v3.2.2_BN.md`।
> বাকি: LOG-T8-এর ড্যাশবোর্ড রিপোর্টিং (debug-এ হয়েছে), সিম্বল প্রোফাইল প্রিসেট, আর **ফেজ 4 ক্যালিব্রেশন** (ডেটার কাজ)।

## ০. সারসংক্ষেপ

| শ্রেণি | সংখ্যা | সবচেয়ে গুরুত্বপূর্ণ |
|---|---|---|
| 🔴 P0 — ট্রেড নষ্ট করে | 3 | অসম্পর্কিত zone ভাঙলে setup মরে · একটা আটকে থাকা ট্রেড পরের সব entry গিলে ফেলে · CE fill retroactive (survivorship bias) |
| 🟠 P1 — লজিক/accuracy | 9 | `sbPdPos` unclamped · chop bypass এখনো circular · non-SB arming-এ grace নেই · bare CISD = "shift" |
| 🟡 P2 — polish | 5 | unused HTF protected swing · relVol floor · NEXT level distance |
| 🟢 যাচাই করে ঠিক পেলাম | — | FVG↔IFVG হ্যান্ডঅফ · security `[1]` idiom · sweep quality raw/eff split · output budget 64/64 |

**এক লাইনে:** ইঞ্জিনের *detection* এখন শক্ত। যা বাকি আছে তা মূলত **state-management আর execution-realism** — অর্থাৎ বৈধ setup কীভাবে অন্যায়ভাবে মরে, আর চার্টের RR/counter বাস্তব ফিলের সাথে কতটা মেলে।

---

## ১. 🔴 P0 — আসল বাগ

### BUG-T1 · POI invalidation **গ্লোবাল**, setup-এর নিজের zone নয়
**লাইন 2159, 2210 (`f_zoneUpdate`) vs 3409, 3527 (মেশিন)**

```pine
// f_zoneUpdate — যেকোনো demand zone ভাঙলেই:
if close < bot and confirmed
    zoneInvalidatedUp := true          // ← array-র যেকোনো zone

// MODULE 17:
if suL >= 2 and zoneInvalidatedUp and na(suLFvgBar)
    suL := 0
    suLReason := "POI violated"
```

`zones` array-তে প্রতি সাইডে `maxZones = 6` টা zone থাকে। দামের **অনেক নিচের** একটা পুরোনো demand zone ভেঙে গেলেও `zoneInvalidatedUp` true হয় — আর সেটা আমাদের setup-কে মেরে ফেলে, যার anchor সম্পূর্ণ অন্য zone (বা OTE tap, যেখানে anchor `na`)।

**কেন গুরুতর:** এটা **নীরব signal loss**। ড্যাশবোর্ড শুধু বলে "POI violated" — কোন POI, বলে না। ট্রেন্ডিং মার্কেটে যেখানে পুরোনো zone ঝরে পড়ছে, সেখানে এটা সবচেয়ে বেশি ঘটে — অর্থাৎ ঠিক যেখানে setup-টা সবচেয়ে ভালো।

**ফিক্স:** setup যে zone-এ tap করেছে তার সীমা মনে রাখো, শুধু সেটাই চেক করো:
```pine
// stage 1→2, tapZone হলে ইতিমধ্যে সেভ হচ্ছে:
suLAnchorT := nbTop
suLAnchorB := nbBot
// invalidation:
if suL >= 2 and na(suLFvgBar) and not na(suLAnchorB) and close < suLAnchorB
    suL := 0
    suLReason := "POI violated (own zone)"
```
`zoneInvalidatedUp/Dn` তখন শুধু ডিসপ্লে/স্কোরের জন্য থাকুক। OTE-tap (anchor `na`) কেসে কোনো zone-kill লাগে না — `sweep reclaim lost` + `opposing displacement` যথেষ্ট।

---

### BUG-T2 · একটা আটকে থাকা ট্র্যাকড ট্রেড পরের **সব** মেশিন-entry বাতিল করে
**লাইন 3897–3933 (non-SB exit), 4014–4028, 4036**

```pine
trackNew = (anyLong or anyShort) and confirmed and trdDir == 0
...
if confirmed and sigMCLong and suL == 4 and suLBar == bar_index and trdDir != 0
    suL := 0
    suLReason := "entry not tracked — a trade was already open"
```

Non-SB ট্রেডের **কোনো টাইম-স্টপ নেই, TP3 নেই, structure exit নেই** — শুধু SL বা TP2। রেঞ্জিং মার্কেটে একটা ট্রেড ২০০+ বার খোলা থাকতে পারে। ওই পুরো সময়:

1. প্রতিটা নতুন মেশিন entry `suL := 0` করে মুছে দেওয়া হয় — শুধু tracking নয়, **state machine-ই রিসেট**;
2. `cntLong/cntA/cntAp` তবু বাড়ে, কিন্তু `cntTP1/TP2/SL` বাড়ে না → ড্যাশবোর্ডের দুই সংখ্যা তুলনাযোগ্য থাকে না;
3. SB ট্রেডের `trdSbWin` time-stop আছে, non-SB-র নেই — তাই **non-SB ট্রেডই বেশি আটকে থাকে**।

**ফিক্স (তিনটা একসাথে):**
```pine
// (a) non-SB ট্রেডে সর্বোচ্চ আয়ু
maxTrdBars = input.int(60, "Tracked trade max life (bars, 0 = off)", minval = 0, group = grpR)
var int trdBar = na
// entry-তে: trdBar := bar_index
if confirmed and trdDir != 0 and maxTrdBars > 0 and bar_index - trdBar > maxTrdBars
    cntExp += 1
    trdDir := 0                       // সময়ে শেষ — outcome "expired"

// (b) non-SB ট্রেডেও TP3 ল্যাডার (TP2-এ পুরো বন্ধ না করে runner রাখো)
// (c) untracked signal আলাদা গোনা:
if (anyLong or anyShort) and not trackNew
    cntUntracked += 1                 // suL রিসেট কোরো না — ACTIVE থাকুক
```
`suL := 0` করার বদলে stage 4-এ থাকতে দাও: entry বৈধ ছিল, শুধু tracker ব্যস্ত ছিল।

---

### BUG-T3 · CE fill **retroactive** — লাইভ লিমিট অর্ডারের সাথে মেলে না
**লাইন 3490–3495 (long), 3587–3592 (short)**

```pine
bool sbCeTchL = low <= suLAnchorT and low <= ceL + sbCeTol * atr
bool sbCeTapL = sbCeTchL and (close >= ceL or sbRejL)     // SB-11
```

ডকট্রিন বলে: CE-তে **লিমিট অর্ডার বসানো আছে**। দাম CE ছুঁলেই ফিল হয় — bar কীভাবে ক্লোজ করল তাতে কিছু যায় আসে না। কিন্তু কোড ফিল স্বীকার করে **কেবল তখনই**, যখন বার CE-এর ভেতরে/ওপারে ক্লোজ করেছে বা rejection candle হয়েছে।

**ফল দুই দিকেই খারাপ:**
- যে ট্রেডগুলো ফিল হয়ে সাথে সাথে ফেল করেছে, চার্ট সেগুলো **কখনো দেখায় না** → `cntTP1/cntSL` অনুকূলভাবে পক্ষপাতদুষ্ট (survivorship bias)। "accuracy" মাপার সব চেষ্টা এখানে মিথ্যা বলে।
- লাইভে তুমি এমন ট্রেডে ঢুকে যাবে যেটা ইন্ডিকেটর মার্ক করেনি — signal আর position একমত না।

**ফিক্স:** দুইটা আলাদা ইভেন্ট রাখো, একটাকে অন্যটার ভান করতে দিও না:
```pine
sbCeTouch = sbCeTchL                              // লিমিট ফিল (বাস্তব)
sbCeHold  = sbCeTchL and (close >= ceL or sbRejL) // ফিল + প্রথম বার ধরে রেখেছে
fillMode  = input.string("Limit touch (realistic)", "CE fill model",
     options = ["Limit touch (realistic)", "Touch + hold (v3.2.1)"])
```
ডিফল্ট "Limit touch" রাখো — তাহলে counter আর strategy twin দুটোই সত্য বলবে। "Touch + hold" থাকুক discretionary ফিল্টার হিসেবে, আলাদা ট্যাগে।

---

## ২. 🟠 P1 — লজিক / accuracy

### LOG-T1 · `sbPdPos` clamp করা হয়নি
**লাইন 1848 vs 1886**
```pine
pdPos   = rangeOK ? math.min(1, math.max(0, (close - rngLo) / rngW)) : na   // ✅ clamped
sbPdPos = sbRngOK ? (close - sbRngLo) / (sbRngHi - sbRngLo) : pdPos        // ❌ unbounded
```
SB উইন্ডো খোলার মুহূর্তে রেঞ্জ ফ্রিজ হয়; raid সেই রেঞ্জ ছাড়িয়ে গেলে `sbPdPos` হয় −0.4 বা 1.6। এটা পড়ে `sbReqPD` (entry rule) আর `f_mcTier` (A+ গেট)। FIX-P1-9 ঠিক এই রোগই সারিয়েছিল live range-এ — locked range-এ ফেরত এসেছে।

**ফিক্স:** clamp + escape hatch —
```pine
sbPdRaw = sbRngOK ? (close - sbRngLo) / (sbRngHi - sbRngLo) : pdPos
sbOut   = sbRngOK and (sbPdRaw < -0.15 or sbPdRaw > 1.15)   // রেঞ্জ অপ্রাসঙ্গিক
sbPdPos = sbOut ? pdPos : math.min(1, math.max(0, sbPdRaw))
```

### LOG-T2 · CHOP bypass এখনো circular (FIX-P1-1 অর্ধেক শেষ)
**লাইন 3622–3625**
```pine
chopOKL = not useRegime or regime != "CHOP" or lastSslQual >= 4      // ← EFF grade
```
`lastSslQual` EFF, আর MSS নিজেই সেটাকে 4 বানায় (লাইন 1357)। মানে: chop-এ MSS হলেই chop-ফিল্টার নিজে থেকে খুলে যায়। FIX-P1-1 tier আর score-এ RAW ব্যবহার করে circularity ভেঙেছে, কিন্তু **chop exemption ভাঙেনি** — অথচ ARCH-5-এর "institutional exception" মানে ছিল *সুইপটাই* institutional, MSS-এর কারণে নয়।

**ফিক্স:** দুই শর্তকে আলাদা রাখো, দুটোই চাও —
```pine
instSweepL = lastSslQualRaw >= 3 and recentMssUp     // শক্ত raid + সত্যিকারের shift
chopOKL = not useRegime or regime != "CHOP" or instSweepL or (sbEnable and sbChopBypass and sbSigLong)
```

### LOG-T3 · non-SB arming-এ grace নেই → বৈধ সুইপ চিরতরে হারায়
**লাইন 3367–3368, 3428**
```pine
sbArmBarL = lastSslBar == bar_index or sbGraceL      // non-SB: শুধু সুইপের ঠিক ওই বারে
```
সুইপ বারে যদি chop ব্লক থাকে, বা opposing displacement, বা তখনও POI-এর ভেতরে — setup আর কখনো arm হবে না, যদিও `sslInPlay` পরের ১২ বার সত্য থাকে। SB পথে ৫ বার grace আছে; সাধারণ পথে শূন্য। এটাই "চার্ট চুপচাপ" অনুভূতির বড় কারণ।

**ফিক্স:** ইনপুট `armGrace` (default 2–3, 0 = পুরোনো আচরণ), SB-9-এর মতো per-sweep একবারই:
```pine
armGrace = input.int(3, "Non-SB: bars after the sweep a setup may still arm", minval = 0, group = grpQ)
stdGraceL = sslInPlay and f_recent(lastSslBar, armGrace) and nz(armedSslBar, -1) != lastSslBar
```

### LOG-T4 · খালি `cisdUp` = "structure shift"
**লাইন 3455, 3566**
```pine
if suL == 2 and (sbTagL != 0 and sbReqMss ? mssUp : (mssUp or chochUp or eChochUp or cisdUp))
```
CISD কোনো structure ভাঙে না — এটা delivery-এর বদল, একটা লেগের ভেতরেই ঘটতে পারে। POI tap-এর পরে একটা CISD-কে shift ধরে নিলে setup stage 3-এ চলে যায়, FVG lock করে, entry দেয় — অথচ কোনো swing ভাঙেনি। `mssNeedExt` দিয়ে MSS কঠিন করা হয়েছে, কিন্তু এই দরজা খোলা রয়ে গেছে।

**ফিক্স:** shift-source ইনপুট (SB-র `sbReqMss`-এর সাধারণ সংস্করণ):
```pine
shiftSrc = input.string("MSS / external CHoCH", "Machine: what counts as the shift",
     options = ["MSS only", "MSS / external CHoCH", "+ internal CHoCH", "+ CISD"], group = grpQ)
```
ডিফল্ট "MSS / external CHoCH"। CISD থাকুক execution confirmation হিসেবে (`zoneBullConf`-এ ইতিমধ্যে আছে) — trigger হিসেবে নয়।

### LOG-T5 · `tapOte` — POI ছাড়াই "AT POI"
**লাইন 3444, 3558**
```pine
bool tapOte = inOTEbuy      // শুধু OTE ব্যান্ডে থাকা = stage 2
```
OTE একটা *দামের এলাকা*, POI নয়। এটা দিয়ে stage 2 পেরোলে setup-এর কোনো anchor থাকে না (`suLAnchorT = na`), tier-এর POI স্তর 0–5 থাকতে পারে, আর invalidation-এ শুধু sweep চেক বাকি থাকে। চেইনের সবচেয়ে দুর্বল entry-গুলো এখান থেকেই আসে।

**ফিক্স:** `poiSrc` ইনপুট — `Zone / HTF POI only` (default) · `+ OTE`. অথবা OTE tap মানলে সেই বারে অন্তত `nearDemand` চাও।

### LOG-T6 · HTF protected swing আনা হয়, ব্যবহার হয় না
**লাইন 1523**
```pine
[hsDirRaw, hsProtLo, hsProtHi] = request.security(...)   // hsProtLo/hsProtHi কোথাও পড়া হয় না
```
পুরো ফাইলে দুইটা নামের একটাই করে occurrence। হয় বাদ দাও, নয়তো কাজে লাগাও — **এটা প্রায়-বিনামূল্যে accuracy**: HTF protected swing হলো একটা structural stop/target যা LTF wick-এ মরে না।
```pine
// SL কে HTF কাঠামোর বাইরে ঠেলো না, কিন্তু HTF swing ভাঙলে runner ছাড়ো:
htfInvalL = not na(hsProtLo) and close < hsProtLo     // HTF কাঠামো ভেঙেছে → long narrative শেষ
```

### LOG-T7 · engine সিগন্যালের entry এখনো bar close
**লাইন 3767**
```pine
float planEntry = anyLong ? nz(mcPlanLong, close) : anyShort ? nz(mcPlanShort, close) : na
```
FIX-P0-4 মেশিনের entry ঠিক করেছে; CRT / turtle soup / zone-50% / FEM / trendline এখনো **close**-এ ঢোকে। বাস্তবে তুমি ঢুকবে পরের বারের open-এ। M5-এ এক displacement candle = 0.3–0.8 ATR পার্থক্য — সরাসরি RR-এ লাগে।

**ফিক্স:** `engFillMode` ইনপুট: `Bar close (v3.2.1)` | `Next bar open (realistic)`। পরেরটায় entry/SL/TP এক বার পিছিয়ে হিসাব করো (strategy twin-এ এটাই ডিফল্ট হওয়া উচিত)।

### LOG-T8 · কাউন্টারের হিসাব মেলে না (BUG-T2-এর যমজ)
`cntLong/cntShort/cntA/cntAp` বাড়ে প্রতিটা সিগন্যালে; `cntTP1/TP2/SL` কেবল tracked ট্রেডে। ড্যাশবোর্ডে "A+ 14 · TP1 4 · SL 3" দেখে মনে হয় ৭টা ট্রেড অমীমাংসিত — আসলে ৭টা কখনো ট্র্যাকই হয়নি। **`cntTracked` আর `cntUntracked` আলাদা দেখাও**, নইলে সংখ্যা পড়া অসম্ভব।

### LOG-T9 · `f_pickPoi` দূরত্ব দেখে না
**লাইন 1746–1773**
fresher (visits == 0) সবসময় nearer-কে হারায়। ফল: ৪০ HTF-বার পুরোনো, ৮ ATR দূরের একটা untested FVG জিতে যায় — আর সেটাই `hPoiBTop`, সেটাই NEXT BUY লেবেল, সেটাই মেশিনের `tapHtf`। **ফিক্স:** freshness bonus কেবল একটা দূরত্ব-জানালার ভেতরে (যেমন ≤ 3 ATR), বাইরে হলে nearest জেতে।

---

## ৩. 🟡 P2 — polish

| # | জায়গা | কথা |
|---|---|---|
| T-a | 669 | `relVol` floor `syminfo.mintick` — ভলিউমের একক নয়; `math.max(ta.sma(volume, volLen), 1)` |
| T-b | 3091 | LT-7 `nsBot/nsTop` ধরে নেয় chart supply zone, কিন্তু FIX-F6-এর পরে সেটা HTF POI-ও হতে পারে |
| T-c | 1841, 4543 | `rangeHolds` শুধু "·tight" লেখা দেখায়; leg < 2 ATR হলে A+-এর P/D শর্তটাই **মওকুফ** করা উচিত, নইলে সেটা এলোমেলো কয়েন-টস |
| T-d | 2788–2789 | ctx স্কোর live `pdPos` পড়ে, অথচ tier/entry SB-locked রেঞ্জ পড়ে — একই বারে দুই সংজ্ঞা |
| T-e | 4700–4753 | output 64/64 (8 plot + 14 plotchar + 5 bgcolor + 37 alertcondition) — নিশ্চিত করা হলো। নতুন কিছু `label`/`alert()`-এ করতে হবে |

---

## ৪. ✅ যা যাচাই করে **ঠিক** পেলাম (তৃতীয় পাসে)

- **FVG → IFVG হ্যান্ডঅফ** (2008–2059): invert করে উল্টো array-তে push, `bar_index > f.barCreated` গার্ডের কারণে একই বারে দ্বিতীয় লুপ সেটা ধরে না। iteration-এর সময় remove downward-loop — নিরাপদ।
- **`request.security(..., f(...)[1], lookahead_off)`** — সব HTF কলে (CRT/TBS, POI registry, structure, ADR) একই non-repainting idiom। DEEP_AUDIT-এর retraction সঠিক; `[1]` থাকবে।
- **sweep quality raw/eff split** — প্রতিটা stamp সাইটে একইভাবে লেখা, same-bar merge ছাড়া কোনো উত্তরাধিকার নেই।
- **`f_structure()` দুইবার কল, আলাদা `var` state** — Pine-এ বৈধ।
- **zone cap drain loop** (2427–2450) — `removed` ফ্ল্যাগে infinite loop বন্ধ।
- **SB-14 trail** — `capL` current low/close-এর নিচে রাখে, তাই ভুয়া ফিল হয় না।
- **conflict hierarchy + rollback** (3707–3726) — হারা দিকের stage 4 একই বারে রোলব্যাক হয়, কুলডাউন stamp পরে চলে, তাই বাতিল সিগন্যাল কুলডাউন পোড়ায় না।

---

## ৫. Accuracy বাড়ানোর প্ল্যান (অগ্রাধিকার অনুসারে)

### ফেজ 1 — "বৈধ setup আর অন্যায়ভাবে মরবে না" (২–৩ ঘণ্টা)
1. **BUG-T1** anchor-নির্দিষ্ট POI invalidation
2. **BUG-T2** trade max-life + untracked সিগন্যালে `suL` রিসেট বন্ধ + আলাদা কাউন্টার
3. **LOG-T3** non-SB arm grace (default 3)
4. **LOG-T1** `sbPdPos` clamp
5. **LOG-T2** chop bypass = RAW≥3 **এবং** MSS

> প্রত্যাশা: A/A+ সিগন্যালের সংখ্যা বাড়বে (হারানো setup ফিরবে), মান কমবে না — কারণ প্রতিটা এখনো পুরো চেইন পার হচ্ছে।

### ফেজ 2 — "চার্টের সংখ্যা = বাস্তব সংখ্যা" (৩–৪ ঘণ্টা)
6. **BUG-T3** CE fill model ইনপুট, default = limit touch
7. **LOG-T7** engine entry = next bar open (option)
8. **LOG-T8** tracked vs untracked কাউন্টার
9. `version_02_strategy.pine` দুই fill মডেলেই চালাও → **প্রথম আসল সংখ্যা**

> এই ফেজের আগে "accuracy কত?" প্রশ্নের কোনো সৎ উত্তর নেই। এটাই সবচেয়ে বেশি রিটার্ন দেয়।

### ফেজ 3 — "signal কম, কিন্তু ভারী" (৪–৬ ঘণ্টা)
10. **LOG-T4** `shiftSrc` — CISD আর shift নয়
11. **LOG-T5** `poiSrc` — OTE একা POI নয়
12. **LOG-T6** HTF protected swing কাজে লাগাও (HTF invalidation + HTF-aware TP)
13. **LOG-T9** POI বাছাইয়ে দূরত্ব-জানালা
14. সিম্বল প্রোফাইল প্রিসেট: FX (volume off, SWEEP_CTX 3) · Index/Crypto (volume on 1.3, SWEEP_CTX 4–5)

### ফেজ 4 — ক্যালিব্রেশন (ডেটা, কোড নয়)
15. Strategy Tester: প্রতি সিম্বল × TF-এ tier (A/A+), window (LO/AM/PM), regime আলাদা করে expectancy বের করো
16. `minScore` আর `tierMode` **মাপা** expectancy থেকে সেট করো, অনুমান থেকে নয়
17. যে engine গুলো নেগেটিভ expectancy দেখায় (সম্ভবত inside-bar, doji, trendline) — ডিফল্ট OFF করে দাও

---

## ৬. চূড়ান্ত মত

v3.2.1-এর **detection layer পরিণত** — sweep grading, structure, POI registry, IFVG, HTF multi-slot, ADR — এগুলো ডকট্রিন-সঙ্গত এবং non-repainting।

দুর্বলতা এখন তিনটা জায়গায়, তিনটাই "কোড ঠিক, কিন্তু ভুল প্রশ্নের উত্তর দিচ্ছে":
1. **state management** — বৈধ setup গ্লোবাল invalidation আর tracker-ব্যস্ততায় মরে (BUG-T1, T2);
2. **execution realism** — ফিল আর দাম বাস্তব অর্ডারের মতো নয় (BUG-T3, LOG-T7);
3. **প্রমাণ** — সব "accuracy" এখনো অনুমান, কারণ কাউন্টার পক্ষপাতদুষ্ট (LOG-T8 + ফেজ 2)।

> ফেজ 1 + 2 শেষ না করে নতুন কোনো ফিচার যোগ কোরো না। ফিচার যোগ করলে শুধু অনুমানের সংখ্যা বাড়ে; ফেজ 2 শেষ হলে প্রথমবার জানা যাবে ইন্ডিকেটরটা আসলে কী করে।
