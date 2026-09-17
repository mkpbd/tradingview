# V8 মাস্টার প্ল্যান — Liquidity + SMC/ICT Entry Engine

> **ভিত্তি:** `1.txt` (LQ-SD-PA v3.1.1 SB · 3664 লাইন) এবং `2..txt` (ICT-TE v7.10 · 7066 লাইন) — দুইটার সম্পূর্ণ কোড অডিট।
> **লক্ষ্য:** একটা নতুন ইন্ডিকেটর, যার entry accuracy দুইটার চেয়ে বেশি — কারণ প্রতিটা entry-র পেছনে একটা **মালিকানাধীন কার্যকারণ শৃঙ্খল (owned causal chain)** থাকবে, এবং কোনো stage অন্য কারো ইভেন্ট ধার করতে পারবে না।

---

## ০. এক নজরে রায়

| | **1.txt (v3.1.1)** | **2..txt (v7.10)** |
|---|---|---|
| শক্তি | ফিচার-সমৃদ্ধ: SB engine, 7 trap pattern, HTF CRT/TBS, FEM, regime | কার্যকারণ-কঠোর: pool registry, chronology enforcement, risk-first, grade ladder |
| দুর্বলতা | **কার্যকারণ প্রায় নেই** — এক ক্যান্ডেলে পুরো setup সম্পন্ন হতে পারে, কোনো RR গেট নেই, display toggle এঞ্জিন মেরে ফেলে | **অতি-ফিল্টার + token ceiling** — এক দিকে একটাই setup slot, চার স্তরের downgrade, CRT/TBS/SB engine মুছে ফেলা |
| কম্পাইল টোকেন | অনেক জায়গা খালি (~3000 কোড লাইন) | সীমার গায়ে (100,256-এর ঠিক নিচে) |

**সিদ্ধান্ত:** V8 = **2..txt-এর কার্যকারণ কাঠামো** + **1.txt-এর ফিচার সেট**, কিন্তু টোকেন সীমা এড়াতে **দুই-ফাইল আর্কিটেকচার** (নিচে §৬)।

---

## ১. `1.txt` — বাগ তালিকা (entry accuracy-র জন্য মারাত্মক)

### 🔴 B1 — এক ক্যান্ডেলে পুরো state machine (সবচেয়ে বড় বাগ)

`MODULE 17`, লাইন 2552–2650। সব stage transition একই `if confirmed` ব্লকে পরপর `if` হিসেবে:

```
2583  if suL == 0 and sslInPlay and sbArmBarL ...   → suL := 1
2597  if suL == 1  → tapZone/tapOte/tapHtf          → suL := 2   (একই বার!)
2610  if suL == 2 and (mssUp or chochUp or ...)     → suL := 3   (একই বার!)
2619  if suL == 3  → ripeL = na(suLFvgBar) or ...   → ENTRY      (একই বার!)
```

zone anchor হলে `suLFvgBar` = `na` → `ripeL` = `true` → **sweep-এর ঠিক সেই ক্যান্ডেলেই entry ফায়ার করতে পারে**। কোনো `moved` latch নেই, কোনো bar-stamp তুলনা নেই।

**পরিণাম:** "sweep → POI → MSS → retest" নামের যে narrative লেবেলে লেখা থাকে, বাস্তবে সেটা এক ক্যান্ডেলের কাকতালীয় মিল। এটাই accuracy-র মূল ফাঁস।

**2..txt এটাকে V4-BUG-1 বলে ধরেছে এবং `moved` latch + `ctxBar < tgtBar < raidBar ≤ poiBar < mssBar < dispBar ≤ fvgBar < retestBar` দিয়ে ঠিক করেছে।**

### 🔴 B2 — display toggle এঞ্জিন মেরে ফেলে

| ইনপুট | কী মরে |
|---|---|
| `showSesHL = false` | `f_sesTrack` লাইন 806: লাইনই তৈরি হয় না → `hiLvl/loLvl = na` (লাইন 823-824, `line.get_y1`) → **session raid কখনো ডিটেক্ট হয় না** → kind-4 pool নাই → SB-এর `sbPoolPref` সবসময় ফেল |
| `showEq = false` | লাইন 513/550: EQH/EQL array-তে কিছু ঢোকে না → EQ sweep নাই → kind-2 pool নাই |
| `showZones = false` | লাইন 1599-1600: `newDemand = showZones and bullFVG and dispUp` → **কোনো zone তৈরি হয় না** → machine-এর stage 1→2 (POI tap) কখনো হয় না |
| `showRB / showOB = false` | RB/OB zone নাই |

**নিয়ম যেটা ভাঙা হয়েছে:** detection ≠ display। 2..txt এটাকে `BUG-6` বলে ধরেছে ("Session state is computed ALWAYS; the display toggles only affect drawing")।

### 🔴 B3 — protected swing ভুল

`f_structure` (লাইন 919-961): `protLo := legLo`, যেখানে `legLo` হচ্ছে running min (`legLo := math.min(legLo, low)`), **আসল originating pivot নয়**।

পরিণাম: CHoCH ভুল দামে ফায়ার করে, এবং `protLowE` যেটা SL trail-এ ব্যবহার হয় (লাইন 2954) সেটাও ভুল লেভেল।

2..txt এটা `BUG-1` — সেখানে `s.protLo := s.swLo` (আসল pivot) + `s.protLoBar` (bar stamp)।

### 🔴 B4 — দুর্বল ক্লোজ লেভেল পুড়িয়ে ফেলে, কিন্তু কোনো ইভেন্ট দেয় না

লাইন 904-909:
```
brokeUp = not na(lastRes) and not resBroken and close > lastRes
if brokeUp and confirmed
    resBroken := true          ← displacement যাচাই ছাড়াই latch সেট
```
কিন্তু `f_structure` ভেতরে `if confirmed and body >= structDisp * atr` — অর্থাৎ **weak close latch পুড়িয়ে দেয় কিন্তু BOS রেজিস্টার হয় না**। লেভেলটা চিরতরে হারিয়ে যায়; পরে আসল structural break হলেও আর ইভেন্ট হয় না।

2..txt এটা `BUG-2` — weak close = "liquidity RUN", latch সেট হয় না।

### 🟠 B5 — sweep quality দূষণ

লাইন 723-734 vs 745-749/775-785/856-867:
```
sslSweep  → lastSslQual := f_sweepQual(true)          ← ওভাররাইট
EQ/PD/ses → lastSslQual := math.max(lastSslQual, ...) ← পুরোনো, ভিন্ন sweep-এর quality ধার!
```
`math.max` পুরোনো কোনো সম্পর্কহীন sweep-এর grade বহন করে → নতুন দুর্বল sweep A-grade হয়ে যায় → `minArmQual` গেট অকেজো।

### 🟠 B6 — sweep-এর কোনো ন্যূনতম penetration নেই

লাইন 695-696: `sslSweep = low < lastSup and close > lastSup`। **১ টিক wick = sweep।** `f_sweepQual`-এ `pen >= NEAR_LVL_ATR * atr` কেবল quality 2-এ তোলে, কিন্তু quality 1 দিয়েও `minArmQual = 1` সেট করলে arm হয়।

2..txt-এ `raidMinAtr` (0.10 ATR) হার্ড রিকোয়ারমেন্ট — তার নিচে হলে "TEST", raid নয়।

### 🟠 B7 — liquidity-র কোনো identity নেই

`lastSup` / `lastRes` মানে **শুধু শেষ pivot**। নতুন pivot প্রিন্ট হলে আগেরটা চিরতরে হারায়। কোনো pool registry নেই, কোনো id নেই, কোনো lifecycle নেই।

পরিণাম: state machine "এই বারে একটা sweep হয়েছে" দেখে arm করে — কিন্তু **কোন pool শিকার করছিল সেটা কখনো জানে না**। ফলে stage 1→2-এর POI হচ্ছে "দামের সবচেয়ে কাছের unspent zone" (`f_nextZones`), যার sweep wick-এর সাথে কোনো সম্পর্ক নেই।

### 🟠 B8 — HTF POI দুর্বল

`f_htfPoi` (লাইন 1197-1226):
- কোনো displacement রিকোয়ারমেন্ট নেই → session-open gap-ও POI হয়ে যায় (2..txt-এর `BUG-17`, সেখানে `hPoiDisp = 0.8 ATR`)
- কোনো HTF direction ফিল্টার নেই (`hPoiNeedDir` অনুপস্থিত)
- `bIn += 1` প্রতি ক্যান্ডেলে বাড়ে যদি দাম ভিতরে থাকে → **dwell time, mitigation নয়**। দাম ঠিক ভিতরে পার্ক করলে ৩ ক্যান্ডেলে POI মরে যায় (2..txt V7.6 F-09: edge-triggered করা হয়েছে)

### 🟠 B9 — HTF ডেটা ২ ক্যান্ডেল পুরোনো

```
f_bias: request.security(..., nz((...)[1], 0), lookahead = barmerge.lookahead_off)
```
`lookahead_off` মানে "শেষ **সম্পূর্ণ** HTF বার", আর ভিতরে `[1]` মানে আরও এক বার পিছনে → **মোট ২ HTF বার লেট**। 1H bias 15m চার্টে ৮টা ক্যান্ডেল পুরোনো।

সঠিক গঠন (2..txt): `expr[1]` + `lookahead_on` → ঠিক ১ বার, non-repainting।
একই সমস্যা `f_htfPoi`, `f_crtTbsHtf`-এও।

### 🟡 B10 — কোনো RR / risk গেট নেই

`MODULE 19` TP/SL হিসাব করে **সিগন্যাল ফায়ার হওয়ার পরে** (লাইন 3017)। ফলে:
- SL দূরত্বের কোনো min/max clamp নেই → ৫ ATR stop আর ০.৩ ATR stop একই দেখায়
- RR কোনো গেট নয় — খারাপ RR trade ব্লক হয় না
- opposing liquidity চেক নেই → entry থেকে ০.৪ ATR দূরে un-raided PDH থাকলেও 3R target আঁকা হয়

### 🟡 B11 — dedupe নেই

শুধু `masterCd` bar cooldown। একই pool, একই zone, একই MSS থেকে বারবার entry। 2..txt-এ `dedupePool` + `dedupePoi` + `dedupeMss` + `storyKey`।

### 🟡 B12 — active trade ওভাররাইট

লাইন 3017: `if (anyLong or anyShort) and confirmed` — চলমান trade থাকলেও `trdEntry/trdSL/trdDir` নির্বিচারে overwrite। counter হিসাব নষ্ট।

---

## ২. `2..txt` — বাগ ও সীমাবদ্ধতা

### 🔴 C1 — এক দিকে একটাই setup slot

```
var Setup upS = Setup.new()
var Setup dnS = Setup.new()
```
একটা setup `ST_CTX`-এ arm হলে সেটা **`setupLife` = 60 বার পর্যন্ত slot দখল করে রাখে**। ওই সময়ে ওই দিকে আর কোনো narrative arm হতে পারে না — এমনকি অনেক ভালো একটা এলেও।

ফাইলের নিজের হেডার এটা স্বীকার করে (V7.6 F-10: *"held both setup slots hostage for setupLife bars"*) কিন্তু সমাধান করেনি, শুধু arm কম করেছে।

**এটাই 2..txt কম সিগন্যাল দেওয়ার প্রধান কারণ।**

### 🔴 C2 — downgrade স্ট্যাকিং → নীরব মৃত্যু

`f_grade`-এ পাঁচটা স্বাধীন one-step downgrade:
```
room < oppLiqMult        → −1
congested                → −1
runFade                  → −1
htfConf (Downgrade মোডে) → −1
regDown                  → −1
```
A+ থেকে শুরু করেও **দুইটা লাগলেই B, তিনটায় GR_NONE = no trade**। ডিফল্টে `runGate = "Downgrade"`, `congGate = "Downgrade"`, `regPolicy = true` — অর্থাৎ তিনটাই সক্রিয়।

ট্রেন্ডিং মার্কেটে RANGE ভুল-শ্রেণীবদ্ধ হলে (`regime` এর সংজ্ঞা দুর্বল) প্রতিটা candidate নীরবে এক ধাপ নামে।

### 🟠 C3 — `hTgt` হার্ড ব্লক অতি-কঠোর

```
hTgtL = tgtSrcL != 0
```
"Liquidity ladder" মোডে যদি entry থেকে `rrB × risk` (= 1.5R) দূরত্বে কোনো structural target না থাকে → **trade সম্পূর্ণ ব্লক**। আবার `tpClamp = true` TP2-কে নিকটতম opposing wall-এ কেটে দেয় → সেই wall 1.5R-এর কাছে থাকলেই ব্লক।

Range-bound সেশনে এটা প্রায় সব entry মেরে ফেলে।

### 🟠 C4 — বাদ পড়া ইঞ্জিন (token ceiling-এর কারণে)

| মুছে ফেলা | কোথায় | আনুমানিক টোকেন |
|---|---|---|
| MODULE 11C — MTF CRT / TBS / TWS (15M/30M/1H/4H) | v6.3-এ | ~8,890 |
| MODULE 8B — liquidity marking layer | v7.10-এ | ~3,960 |
| MODULE 16B — ICT detection + marking | v5.8-এ | — |
| CRT + Turtle Soup producer (১৫টা ইনপুট) | v7.0-এ | — |
| Silver Bullet arming path | কখনো ছিল না (শুধু filter/score) | — |

অর্থাৎ **ICT-র দুইটা primary entry model (CRT, Turtle Soup) সম্পূর্ণ অনুপস্থিত**, এবং Silver Bullet কেবল একটা সেশন ফিল্টার।

### 🟠 C5 — MTF ladder = ৪টা নষ্ট `request.security`

```
mtfB5 / mtfB15 / mtfB60 / mtfB240   ← "DISPLAY ONLY"
```
ফাইলটা CE10117-এর সাথে যুদ্ধ করছিল, অথচ ৪টা security call শুধু dashboard row-এর জন্য। কোনো গেট, grade, score এদের পড়ে না।

### 🟡 C6 — trade management শুধু bookkeeping

MODULE 16C: একটা trade একসাথে, কোনো partial/scale-out নেই, `beAfter` ছাড়া trail নেই, window-close time exit নেই (1.txt-এর SB-6 এঞ্জিন এখানে নেই)।

### 🟡 C7 — trap engine মাত্র একটা প্যাটার্ন

`①  Breakout Rejection Trap` — 1.txt-এ ৭টা (LT-1…LT-7)।

### 🟡 C8 — entry-র পরে ১ বার dead time

`f_setupAdvance` এর টপে reset হয় পরের বারে, তারপর `s.resetBar == bar_index` চেক arm ব্লক করে → entry-র পর কমপক্ষে ২ বার কিছুই arm হতে পারে না। C1-এর সাথে যোগ হয়ে frequency আরও কমে।

---

## ৩. দুইটাতেই যা নেই (accuracy-র জন্য যা দরকার)

| # | ফিচার | কেন entry accuracy বাড়ে |
|---|---|---|
| **M1** | **Volume / delivery confirmation** | দুইটাতেই displacement শুধু body×ATR। Volume spike ছাড়া displacement আর retail breakout আলাদা করা যায় না। TradingView-তে `volume` পাওয়া যায় — relative volume (`volume / sma(volume,20)`) displacement quality-তে যোগ করা যায় |
| **M2** | **Multi-timeframe FVG alignment** | LTF FVG যদি HTF FVG-র ভিতরে বসে → nested PD array। দুইটাতেই HTF POI আর LTF FVG আলাদা stage, কিন্তু **overlap মাপা হয় না** |
| **M3** | **Entry-র আগে spread / instrument sanity** | 2..txt-এ `eqTickMin` আছে, কিন্তু কোনোটাতেই "FVG height < spread" চেক নেই। Crypto perp / index-এ CE entry অসম্ভব হয়ে যায় |
| **M4** | **একের বেশি concurrent setup (ranked)** | দুইটাতেই এক দিকে এক setup (1.txt-এ `suL`/`suS`, 2..txt-এ `upS`/`dnS`)। বাস্তবে একই সময়ে ২-৩টা pool শিকার হতে পারে |
| **M5** | **Partial fill / laddered entry** | দুইটাই একটাই entry price দেয়। CE + proximal দুই স্তরে ঢোকার প্ল্যান নেই (1.txt-এ SB-তে আংশিক আছে, generic নয়) |
| **M6** | **Post-entry invalidation ট্র্যাকিং যা state-এ ফেরত যায়** | 2..txt স্পষ্ট বলে trade tracking *"cannot feed back into any gate"*। ফলে পরপর ৩টা SL হলেও এঞ্জিন একইভাবে চালিয়ে যায় |
| **M7** | **সেশন-ভিত্তিক প্যারামিটার** | Asia-র ATR আর NY-র ATR ভিন্ন, কিন্তু `dispFactor`, `raidMinAtr` একই থাকে সারা দিন |
| **M8** | **Backtest-যোগ্য পরিসংখ্যান প্যানেল** | 1.txt-এ raw counter আছে (cntTP1/cntSL), 2..txt-এ কিছুই নেই। win-rate by grade / by session / by producer ছাড়া tuning অন্ধ |
| **M9** | **Alert payload-এ পূর্ণ narrative** | দুইটাতেই আছে আংশিক; কিন্তু structured (JSON-ish) payload নেই যা bot-এ পাঠানো যায় |

---

## ৪. V8 — ডিজাইন নীতি

1. **কার্যকারণ প্রথম, confluence পরে।** প্রতিটা stage একটা **object** (Pool / Zone / Setup) বাঁধবে — global flag নয়। 2..txt-এর `V4-BUG-3/5` নীতি।
2. **এক bar = এক transition।** `moved` latch বাধ্যতামূলক। শুধু দুইটা জোড়া একই বারে অনুমোদিত: `raid ≤ poiTap` এবং `disp ≤ fvg`।
3. **Detection কখনো display toggle-এর উপর নির্ভর করবে না।** সব `show*` ইনপুট কেবল drawing গেট করবে। (1.txt-এর B2 ঠিক করা)
4. **Risk আগে, signal পরে।** SL/TP/RR/room হিসাব হবে emit-এর **আগে**, এবং `slOk` হার্ড গেট।
5. **Downgrade সর্বোচ্চ ২ ধাপ।** পাঁচটা স্বাধীন downgrade স্ট্যাক করা বন্ধ — একটা `penalty` কাউন্টার, `math.min(penalty, 2)`।
6. **প্রতিটা `show*`-এর একটা `use*` যমজ থাকবে না** — বরং detection সবসময় চলবে, শুধু draw গেট হবে। ইনপুট সংখ্যা বাড়বে না।
7. **Non-repainting শপথ:** প্রতিটা `request.security` = expression ভিতরে `[1]` + `lookahead_on` + `f_tfUp()` clamp।

---

## ৫. V8 — Entry narrative (হার্ড শৃঙ্খল)

```
0  IDLE
1  HTF CONTEXT      · htfState ∈ {BULL,BEAR} বা qualified REVERSAL (PD extreme)
2  TARGET LOCKED    · registry থেকে সর্বোচ্চ-ranked live pool (identity সহ)
3  TARGET RAIDED    · সেই pool-ই, lock-এর পরে, pen ≥ raidMinAtr, close ফিরে ভিতরে
4  POI BOUND        · এমন array যা raid wick ধারণ করে (containment, proximity নয়)
5  MSS              · CHoCH (displacement বাধ্যতামূলক) বা CISD+displacement
6  DISPLACEMENT     · body ≥ dispBodyAtr · MSS level পার · POI ছেড়ে · hold ≥ 55%
                     · ★ নতুন: relVolume ≥ 1.2 (M1)
7  FVG              · displacement-এর নিজের gap · height ≥ max(fvgMinAtr·ATR, 2·spread)
                     · ★ নতুন: HTF FVG-র সাথে overlap → tier bonus (M2)
8  RETEST = ENTRY   · depth ≥ retestDepth · 50% ফেরত ক্লোজ · rejection candle
                     · OTE band class · touch count ≤ apMaxTouch
```

**Chronology:** `ctxBar < tgtBar < raidBar ≤ poiBar < mssBar < dispBar ≤ fvgBar < retestBar`
**Integrity re-check:** emit-এর ঠিক আগে `f_narrOk()` পুরো শৃঙ্খল আবার bar-stamp থেকে যাচাই করবে।

### সমান্তরাল producer (একই গেট, কম rank)

| Rank | Producer | উৎস |
|---|---|---|
| 1 | **FEM** (HTF POI = setup-এর POI) | 2..txt |
| 2 | **Machine** (chart-TF POI) | 2..txt |
| 3 | **CRT** (Range→Raid→Reclaim→Delivery) — ★ ফেরত আনা | 1.txt M14 |
| 4 | **Turtle Soup** (min+max age সহ) — ★ ফেরত আনা | 1.txt M14 |
| 5 | **S/D 50% retest** (zone-এর নিজের chain) | 2..txt |
| 6 | **Elite Trap** | 2..txt + 1.txt LT-1…7 |

**নিয়ম:** CRT/TBS আর নিজে নিজে signal দেবে না — এরা **stage-5/6 trigger candidate** হিসেবে মেশিনে ঢুকবে। অর্থাৎ CRT ফায়ার করতে হলেও আগে pool lock + raid + POI লাগবে। এটাই 1.txt-এর "independent signal generator" সমস্যার সমাধান।

---

## ৬. টোকেন বাজেট — দুই-ফাইল আর্কিটেকচার

2..txt প্রমাণ করেছে সব এক ফাইলে ধরে না (103,567 / 100,256)। V8 ইচ্ছাকৃতভাবে ভাগ:

### ফাইল A — `V8_ENGINE.pine` (প্রধান, overlay)
মডিউল: constants · core series · structure (int+ext) · sessions · HTF context · **pool registry** · dealing range · zones/PD arrays · producers · **state machine** · score · gates · risk · trade engine · entry label · alerts · compact dashboard

আনুমানিক: ~85,000 compiled টোকেন (2..txt-এর engine অংশ + CRT/TBS + SB arming, কিন্তু heavy marking layer ছাড়া)

### ফাইল B — `V8_CONTEXT.pine` (সহযোগী, overlay)
মডিউল: MTF bias ladder · MTF CRT/TBS/TWS layer (1.txt-এর M13 + 2..txt-এর মুছে ফেলা 11C) · liquidity marking layer (8B) · trap pattern LT-1…LT-7 visual · debug panel

আনুমানিক: ~45,000 টোকেন। **কোনো entry দেয় না** — শুধু context আঁকে এবং `alert()`-এ পাঠায়।

### টোকেন-সাশ্রয়ের নির্দিষ্ট কৌশল (শেখা 2..txt থেকে)
- **Registration queue প্যাটার্ন:** `f_poolPush` ১৬ বার inline হলে ~9,700 টোকেন। `f_qPush` + একটা `f_qFlush` → ১টা copy (2..txt V5.6-BUDGET)
- **এক reset site:** `f_setupReset` ১৯ জায়গায় call = ~7,000 টোকেন। `kill` flag + বারের শেষে একবার reset (V5.6-L12)
- **একটাই producer chain function**, দুইবার call (`f_prod`) — দুইবার লেখা নয় (V6.5-O4)
- **MTF ladder ফাইল B-তে** — ফাইল A-তে শুধু ১টা bias security call
- এই তিনটা মিলে ~20,000 টোকেন বাঁচে, যা CRT + TBS + SB arming path-এর জন্য যথেষ্ট

---

## ৭. মডিউল স্পেসিফিকেশন (ফাইল A)

### M1 · INPUTS
গ্রুপিং 2..txt-এর ক্রমে (① Master … ⑲ Debug)। **নতুন ইনপুট:**
```
useVolConf   bool   true    "Displacement needs relative volume"
volMult      float  1.2     "Relative volume ≥ (× 20-bar mean)"
maxSetups    int    2       "Concurrent setups per side (1–3)"      ← C1 সমাধান
maxPenalty   int    2       "Max grade downgrade steps"             ← C2 সমাধান
allowSynthTp bool   false   "Allow synthetic TP2 when no structural target" ← C3 সমাধান
spreadGuard  bool   true    "Refuse an FVG thinner than 2× spread"  ← M3
```

### M2 · CONSTANTS + HELPERS
2..txt-এর সব constant (`RUNAWAY_ATR`, `POI_LEAVE_ATR`, `DISP_HOLD_FRAC`, `TGT_HYST`, …) + pool kind/state/grade enum। `f_maskAdd`/`f_maskN` confluence mask রাখা।

### M3 · CORE SERIES + CANDLE ANATOMY
2..txt সংস্করণ (bullPin-এর `PIN_OPP_PCT` range-ভিত্তিক সংশোধন সহ — 1.txt-এর `upWick <= body` হ্যামারে ফেল করে)।
**যোগ:** `relVol = volume / math.max(ta.sma(volume, 20), 1)`, `dispUpBar := ... and (not useVolConf or relVol >= volMult)`।

### M4 · STRUCTURE
2..txt-এর `Struct` UDT হুবহু — দুই instance (internal `pivLen`, external `extPiv`)।
আসল pivot = protected swing (B3 ঠিক), weak close = `run` latch আলাদা (B4 ঠিক)।

### M5 · SESSIONS · KILLZONES · SILVER BULLET
2..txt-এর `Ses` UDT (detection সবসময় চলে — B2 ঠিক)
**যোগ (1.txt থেকে):** `f_sesMin()` minute-math, `sbPreMin` pre-window grace, `sbWinNow`/`sbCtxWin`, per-window `sbQualLO/AM/PM`, `sbEndLOEvt/AMEvt/PMEvt` exit clock।

### M6 · HTF CONTEXT
2..txt হুবহু: `f_tfUp` clamp, `expr[1]` + `lookahead_on`, `htfState` (BULL/BEAR/NEUTRAL/**CONFLICT**), `f_htfPoi` edge-triggered mitigation + `bSeq/sSeq` identity।
**যোগ:** HTF FVG-র coordinate global রাখা যাতে M9 overlap মাপতে পারে (M2 ফিচার)।

### M7 · LIQUIDITY REGISTRY
2..txt হুবহু — `Pool` UDT, ৮ kind (SWING/EXT/EQ/SES/PD/PW/TL/HTF), ৫ state, `f_qPush`/`f_qFlush` queue, `f_poolScan` lifecycle, raid grading A/B/C, `TGT_HYST` hysteresis, weakest-first prune।
**যোগ:** 1.txt-এর wick-cluster pool (LT-3/LT-4) নতুন kind `PK_WICK` হিসেবে — registry-তে ঢুকলে free-তে সব lifecycle পায়।

### M8 · DEALING RANGE · PD · OTE
2..txt-এর impulse-leg range (`legBull`/`legBear`) + `f_inOte` band class (1/2/3)।
**যোগ (1.txt SB-12):** SB window খোলার মুহূর্তে range freeze করে `sbRngHi/sbRngLo` — raid নিজে range বাড়িয়ে premium/discount উল্টে দিতে পারবে না।

### M9 · ZONES / PD ARRAYS
2..txt-এর `Zone` UDT + provenance (`srcPoolId`, `srcRaidBar`, `srcRaidExt`, `srcMssBar`, `srcDispBar`, `srcDispQ`) + tier T1/T2/T3 + `f_regrade` (monotone-worse) + PD-array class (FVG/OB/BRK/MIT/IFVG/BPR/REJ)।
**যোগ:** `htfOverlap` bool — zone যদি live HTF FVG-র সাথে ওভারল্যাপ করে → tier এক ধাপ উন্নত (M2)।
**যোগ:** `spreadGuard` — `top - bot < 2 * syminfo.mintick * spreadEst` হলে zone তৈরিই হবে না (M3)।

### M10 · PRODUCERS
2..txt-এর S/D + Trap
**ফেরত আনা (1.txt থেকে, কিন্তু candidate হিসেবে):**
- `crtBullSetup/crtBearSetup` → stage-5/6 trigger, নিজে signal নয়
- `tbsLong/tbsShort` (min+max age সহ) → একই
- `f_insideBar`, `f_dojiRev` → শুধু score বোনাস, producer নয়

### M11 · RUN · CONGESTION · REGIME
2..txt হুবহু (`congMeasured` vs `congested` আলাদা রাখা — V7.7 F-06)।
**পরিবর্তন:** সব downgrade একটা কাউন্টারে যাবে, `math.min(penalty, maxPenalty)` (C2 সমাধান)।

### M12 · SETUP STATE MACHINE ⭐
2..txt-এর `Setup` UDT + `f_setupAdvance` + `moved` latch + `kill` single-reset।
**পরিবর্তন (C1 সমাধান):**
```
var upSetups = array.new<Setup>()   // সর্বোচ্চ maxSetups
var dnSetups = array.new<Setup>()
```
প্রতি বারে সব setup advance হবে; নতুন arm হবে যদি `array.size < maxSetups` এবং কোনো live setup একই `tgtId` ধরে না থাকে। Emit-এ সর্বোচ্চ rank/grade-এর একটা জেতে, বাকিরা বেঁচে থাকে।

**পরিবর্তন (C8 সমাধান):** entry-র পর setup সাথে সাথে remove, `resetBar` blackout শুধু **ওই pool-এর জন্য** (global নয়)।

### M13 · SCORE
2..txt-এর `f_score` (Context 25 / Liquidity 25 / POI 20 / Trigger 20 / Execution 10 + descriptor ≤6)।
**যোগ:** SB context component (1.txt M16-এর sbCtxLong/Short, 0–15) — কিন্তু মোট 100-এ clamp।
**যোগ:** `relVol` displacement quality-তে ৭ম reading হিসেবে।

### M14 · GATES + DEDUPE
2..txt হুবহু: `dedupePool` (id + price + recency), `dedupePoi`, `dedupeMss`, `storyKey`।
**পরিবর্তন (C3):** `hTgt` আর হার্ড ব্লক নয় যদি `allowSynthTp = true` — তখন synthetic TP2 অনুমোদিত কিন্তু grade সর্বোচ্চ B।

### M15 · RISK PRIMITIVES
2..txt হুবহু: `f_slOk` (min/max clamp), `f_sl` ৫-স্তর hierarchy, `f_tp` ladder, `f_oppLiq`, `f_geq` float hygiene, `rrAn`/`rrAPn` normalisation।

### M16 · TRADE ENGINE
2..txt-এর `f_prod` + hard gates + `f_grade` + arbitration।
**পরিবর্তন:** producer rank-এ CRT/TBS নেই (এরা এখন trigger), বদলে SB-tagged machine entry সর্বোচ্চ rank পায়।

### M17 · TRADE MANAGEMENT ⭐ (নতুন, দুইটার সেরা মিলিয়ে)
- 2..txt-এর `trackTrade` + `beAfter` + `beOffset` (stop-first conservative reading)
- **1.txt-এর SB-6 exit engine যোগ:** TP1 → adaptive BE (`max(sbBeBuf·ATR, 15% of TP1 distance)`) · TP2 → protected-swing trail (শেষ ২ বারের low/high দিয়ে capped) · TP3 → liquidity target · window-close time exit · opposing MSS/CISD structural exit
- **M6 যোগ:** rolling result memory (শেষ ১০ trade) — পরপর ৩ SL হলে `minGrade` স্বয়ংক্রিয়ভাবে এক ধাপ কড়া (optional input, ডিফল্ট OFF)

### M18 · VISUAL + DASHBOARD + ALERTS
- Entry label: grade · producer · narrative reason · RR · SL/TP
- Dashboard: HTF state · regime · run · target pool · setup stage (প্রতি দিক, সব live setup) · score · grade
- Alert: structured payload —
  `{dir, grade, producer, entry, sl, tp1, tp2, tp3, rr, pool, poolKind, raidGrade, poiTier, oteBand, score}`

---

## ৮. বাস্তবায়নের পর্যায়

| Phase | কাজ | যাচাই |
|---|---|---|
| **P0** | `2..txt` কপি করে `V8_ENGINE.pine` বানানো, MTF ladder (C5) সরানো, compile করা | CE10117 নেই, টোকেন হেডরুম মাপা |
| **P1** | M12 multi-setup array (C1) | এক দিকে ২টা setup একসাথে stage দেখানো — debug panel-এ |
| **P2** | penalty counter (C2) + `allowSynthTp` (C3) | একই চার্টে signal সংখ্যা তুলনা, before/after |
| **P3** | `relVol` displacement gate (M1) + spread guard (M3) + HTF FVG overlap (M2) | crypto + forex + index তিনটায় zone সংখ্যা যাচাই |
| **P4** | SB arming path port (1.txt M4B + M17 SB overlay) | SB window-এ tagged entry, window-close kill কাজ করে |
| **P5** | CRT + Turtle Soup trigger হিসেবে port | CRT ফায়ার হয় শুধু pool+raid+POI থাকলে |
| **P6** | M17 exit engine (SB-6 + trade memory) | TP1 BE, TP2 trail, time exit — লেবেলে দেখা যায় |
| **P7** | `V8_CONTEXT.pine` — MTF CRT/TBS layer + marking + LT-1…7 visual | আলাদা compile, alert() ফিড |
| **P8** | Stats panel (M8) — grade/session/producer অনুযায়ী hit count | ৬ মাস history-তে সংখ্যা যুক্তিসঙ্গত |

---

## ৯. গ্রহণযোগ্যতা পরীক্ষা (প্রতিটা phase-এ চালাতে হবে)

1. **Chronology test:** কোনো entry-তে `retestBar == raidBar` হতে পারবে না। Debug panel-এ প্রতিটা stage bar প্রিন্ট করে চোখে যাচাই।
2. **Display-independence test:** সব `show*` = false করে দেখা — signal সংখ্যা **অপরিবর্তিত** থাকতে হবে। (1.txt এখানে ফেল করে)
3. **Repaint test:** bar replay-তে historical আর realtime signal একই bar-এ আসতে হবে। সব `request.security` = `expr[1]` + `lookahead_on` + `f_tfUp`।
4. **Ownership test:** প্রতিটা entry-র `poolId` যে pool `tgtId`-তে lock ছিল, সেটাই হতে হবে। `f_narrOk` এটা যাচাই করে।
5. **Risk test:** প্রতিটা emit-এ `minRiskAtr ≤ |entry−sl|/ATR ≤ maxRiskAtr` এবং `rr ≥ rrB`।
6. **Starvation test:** ৩ মাস 5m history-তে entry সংখ্যা — 2..txt-এর চেয়ে **বেশি** এবং 1.txt-এর চেয়ে **কম** হওয়া উচিত। (1.txt অতি-বেশি সিগন্যাল দেয় কারণ B1; 2..txt অতি-কম দেয় কারণ C1+C2+C3)
7. **Token test:** প্রতিটা phase-এর পরে compile — হেডরুম ৫,০০০-এর নিচে নামলে থামা।

---

## ১০. প্রস্তাবিত ডিফল্ট (5m–15m intraday)

```
Entry mode          Narrative + confluence
minTier             2
minGrade            A            ← 2..txt-এর B ছিল, খুব ঢিলা
needHtfAlign        true
strictSeq           true
maxSetups           2            ← নতুন
maxPenalty          2            ← নতুন

raidMinAtr          0.10
raidDeepAtr         0.35
sweepLook           15
reactWin            6

poiBindAtr          0.15         ← containment, proximity নয়
dispBodyAtr         1.3
useVolConf          true
volMult             1.2          ← নতুন
fvgMinAtr           0.10
retestDepth         0.5
lateBars            6
apMaxTouch          2

rrB / rrA / rrA+    1.5 / 1.5 / 2.0
minRiskAtr          0.25
maxRiskAtr          3.0
tpMode              Liquidity ladder
allowSynthTp        false        ← range দিনে true করা যায়

runGate             Downgrade
congGate            Downgrade
regPolicy           true
htfConfMode         A+ only

Silver Bullet role  Filter + arming path   ← নতুন (1.txt থেকে)
```

---

## ১১. ঝুঁকি ও সীমা (সৎভাবে)

- **টোকেন সীমা আসল।** 2..txt তিনবার CE10117 খেয়েছে। V8-এ CRT+TBS+SB+multi-setup যোগ করলে ফাইল A-ও সীমায় পৌঁছাবে। তাই §৬-এর তিনটা সাশ্রয় কৌশল **আগে** প্রয়োগ করতে হবে, ফিচার যোগের পরে নয়।
- **multi-setup (C1) সবচেয়ে ঝুঁকিপূর্ণ পরিবর্তন।** `Setup` UDT array-তে রাখলে প্রতিটা field access array lookup হয়ে যায় — টোকেন খরচ বাড়ে। `maxSetups = 2` দিয়ে শুরু, ৩-এ যাওয়ার আগে টোকেন মাপা।
- **`relVol` সব instrument-এ কাজ করে না।** Forex spot-এ volume = tick count, index CFD-তে প্রায়ই অর্থহীন। তাই `useVolConf` ইনপুট রাখা, এবং volume না থাকলে স্বয়ংক্রিয়ভাবে বাইপাস।
- **Accuracy-র কোনো গ্যারান্টি নেই।** এই প্ল্যান যা করে তা হলো: ভুল কার্যকারণে তৈরি সিগন্যাল কমায় (1.txt-এর B1/B7/B10) এবং সঠিক কার্যকারণে তৈরি সিগন্যাল যেগুলো অকারণে ব্লক হচ্ছিল সেগুলো ফেরত আনে (2..txt-এর C1/C2/C3)। Win-rate শুধু forward test-ই বলতে পারে।

---

## পরিশিষ্ট — বাগ-থেকে-সমাধান ম্যাপ

| বাগ | ফাইল | V8-এ সমাধান |
|---|---|---|
| B1 এক-বার machine | 1 | M12 `moved` latch + bar-stamp chronology |
| B2 display gates detection | 1 | M5/M7/M9 — detection সবসময়, draw গেট |
| B3 protected swing ভুল | 1 | M4 `Struct.protLo := swLo` + bar |
| B4 weak close latch পোড়ায় | 1 | M4 আলাদা `run` latch |
| B5 sweep quality দূষণ | 1 | M7 প্রতি pool-এর নিজের `rq` |
| B6 penetration নেই | 1 | M7 `raidMinAtr` হার্ড |
| B7 liquidity identity নেই | 1 | M7 Pool registry + id binding |
| B8 HTF POI দুর্বল | 1 | M6 `hPoiDisp` + `hPoiNeedDir` + edge-triggered `bIn` + `bSeq` |
| B9 HTF ২ বার লেট | 1 | M6 `expr[1]` + `lookahead_on` |
| B10 RR গেট নেই | 1 | M15 risk-first + `slOk`/`hRr`/`hRoom` |
| B11 dedupe নেই | 1 | M14 pool/POI/MSS/story dedupe |
| B12 trade overwrite | 1 | M17 একটা active trade, নতুনটা queue |
| C1 এক setup slot | 2 | M12 setup array (`maxSetups`) |
| C2 downgrade স্ট্যাক | 2 | M11 penalty counter, `maxPenalty` |
| C3 `hTgt` হার্ড ব্লক | 2 | M14 `allowSynthTp` (grade cap B) |
| C4 CRT/TBS/SB নেই | 2 | M10 trigger হিসেবে ফেরত + M5 SB arming |
| C5 নষ্ট MTF security | 2 | ফাইল B-তে সরানো |
| C6 exit শুধু bookkeeping | 2 | M17 SB-6 exit engine |
| C7 এক trap প্যাটার্ন | 2 | ফাইল B-তে LT-1…7 visual + score feed |
| C8 entry-র পর dead time | 2 | M12 per-pool blackout, global নয় |
| M1–M9 অনুপস্থিত ফিচার | দুইটাই | §৭-এ মডিউল-ভিত্তিক |
