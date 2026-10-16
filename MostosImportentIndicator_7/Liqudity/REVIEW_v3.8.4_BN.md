# Deep Review · `liqudity_trap_trading.v3.8.4.txt` — কী কী improve করা যায়

> তারিখ: 2026-10-15 · সব line number **v3.8.4** ফাইলের।
> পদ্ধতি: ৫টা module-range আলাদা করে line-by-line পড়া হয়েছে। Top finding-গুলো (C1, C2, E1/D4, E2, E3, A-1, B1) আবার নিজে code খুলে মিলিয়ে দেখা হয়েছে।
> পুরনো audit (`_6/Liqudity/FORENSIC_AUDIT_v3.8.1.md`)-এর open item-গুলোর বর্তমান অবস্থাও যাচাই করা হয়েছে।
> **কোনো code বদলানো হয়নি।** এটা শুধু review।

---

## 0. সংক্ষেপ

- **Repaint নেই।** সব `request.security` `[1]` + `lookahead_on` দিয়ে করা (2121, 2198, 2284, 2399, 2446, PD/PW 1732)। Future leak নেই।
- **সবচেয়ে বড় সমস্যা: stop placement।** তিনটা engine-এর stop আসল raid wick-এর **ভেতরে** বসে:
  - LT trap: C2 / পুরনো D5
  - Zone 50% tap: B1
  - FEM: C8
  - এছাড়া একই bar-এ pool stamp হলে multi-bar sweep extreme overwrite হয়ে যায় (A-1)। ফলে stop-out বেশি হয় আর R ভুলভাবে বড় দেখায়।
- **FEM-এর HTF POI kill (FIX-Z8) কখনো fire করে না (C1)।** `f_pickPoi` সবসময় এমন POI বাছে যার `bot <= close`, তাই `close < hPoiBBot` কখনো সত্য হয় না।
- **Conflict tie-তে ভুল alert যায় (E1/D4)।** `anyLong`/`anyShort` false হয়, কিন্তু `sigMCLong`/`sigMCShort` true থেকে যায়। ফলে "◉ Setup machine entry" alert fire করে, অথচ কোনো trade নেই।
- **Tracker win-rate বাড়িয়ে দেখায়, দুই জায়গায়:**
  - D2: CE limit fill হলো, আর একই bar distal edge-এর নিচে close করল। এই loss tracker-এ কখনো ঢোকে না।
  - E8: limit fill-এর bar-এই stop wick ছুঁলে তা check হয় না।
- **Token budget-এ অনেক জায়গা আছে।** নিরাপদ token-cut প্রায় **−550 থেকে −900**:
  - E4: exit block দুবার লেখা, −300
  - Doji/IB engine বাদ দিলে আরও −350 থেকে −400
  - এই জায়গা দিয়ে সব P1/P2 fix (প্রায় +150) সহজে বসানো যায়, CE10117-এর ভয় ছাড়াই।
- **Output budget-এর comment ভুল।** Comment বলছে "64 FULL", আসলে **53/64**। ১১টা slot খালি (E11)।

---

## 1. পুরনো audit item — এখনকার অবস্থা

| Item | অবস্থা | v3.8.4 line | মন্তব্য |
|---|---|---|---|
| D4 display toggle detection-কে gate করে | **OPEN** | 3001-3002, 3024, 3049, 3062 | `showZones` off করলে zone, NEXT, TP2 clamp, SD signal, LT-7 সব বন্ধ হয়ে যায় (B2) |
| D5 LT stop raid wick ধরে না | **OPEN** | 3990, 4033 | C2 দেখুন |
| D6 LT invalidation-এ body লাগে, veto 25 bar পর্যন্ত | **OPEN** | 3956, 3999, 4645 | C4 দেখুন |
| D7 HTF FVG-এর min height নেই | **OPEN** | 2350, 2362 | B5 দেখুন |
| Z6 chart FVG min height | FIXED | 2650 | — |
| D8 TP2 clamp শুধু POI zone দেখে | **OPEN** | 4711-4714, 4842 | D12 দেখুন |
| D21 TP2 clamp grade দেখে না | **OPEN** | 4711, 4713 | D12 দেখুন |
| N-C 18B kill করলে stage 0-তে যায় | **OPEN** | 4727-4732 | D11 দেখুন |
| N-D `trdToday` untracked signal-ও গোনে | **OPEN** | 5112 | E14 দেখুন |
| D15 cancel হওয়া pending order ফেরত গোনা হয় না | **OPEN** | 4865 | E14 দেখুন |
| D11 Asia `inKZ`-এর ভেতরে | **OPEN** | 1453 | A-15 দেখুন |
| D12 SB-11 comment ≠ code | **OPEN** (শুধু comment) | 4290-4293 | code ঠিক আছে, comment ঠিক করতে হবে |
| D13 FEM entry-তে CE/outer-30% নিয়ম নেই | **OPEN** | 3418, 3445 | C8 দেখুন |
| D16 day boundary (`time("D")` বনাম NY) | **OPEN** | 2447, 4496, 5530 | E6 দেখুন |
| D17 EQH শুধু পরপর pivot দেখে | **OPEN** | 1372, 1403 | A-11 দেখুন |
| Z3, Z4, Z5, Z10, Z11 (stage 1-2), F-ALERT, D19 | FIXED | — | Z5-এর side effect B10-এ, Z11 stage 3-এ বাকি (D10) |

---

## 2. P1 / P2 — আগে এগুলো ঠিক করুন

### C2 · P1 · LT trap-এর stop trap wick-এর ভেতরে বসে
- **Line:** 3990 `_ltSlL := math.min(low, _ltLLevel) - pad`, 4033 `_ltSlS := math.max(high, _ltSLevel) + pad`
- **সমস্যা:**
  - Arm bar-এর poke high-টাই আসল raid extreme। Confirmation আসে ২ বা তার বেশি bar পরে, আর stop দেখে শুধু confirmation bar-এর high।
  - ফলে stop বসে poke high-এর **নিচে**, ঠিক যেখানে stop run শেষ হয়।
  - LT-7 সবচেয়ে খারাপ: level হলো breakout level, supply zone-টা stop-এ ধরা হয় না।
- **Fix** (`f_ltMachines`-এর ভেতরে):
  ```
  var float _ltLExt = na
  var float _ltSExt = na
  _ltLExt := _ltLState == 1 ? math.min(nz(_ltLExt, low), low) : na
  _ltSExt := _ltSState == 1 ? math.max(nz(_ltSExt, high), high) : na
  _ltSlL := math.min(low, _ltLLevel, nz(_ltLExt, low)) - SL_PAD_ATR * atr
  _ltSlS := math.max(high, _ltSLevel, nz(_ltSExt, high)) + SL_PAD_ATR * atr
  ```
- **Cost:** প্রায় +40 token। নতুন scope বা output নেই।
- **Effect:** stop চওড়া হবে, stop-out কমবে, R একটু কমবে।

### C1 · P2 · FEM-এর HTF POI kill কখনো fire করে না
- **Line:** 3395, 3422। কারণ `f_pickPoi` (2415-2428), যেখানে শর্ত `b1 <= close`।
- **সমস্যা:**
  - Price POI-এর নিচে close করলে picker পরের দূরের POI বেছে নেয়। তাই `close < hPoiBBot` কখনো সত্য হয় না।
  - FEM chain একটা ভাঙা POI-এর ওপর বেঁচে থাকে, যতক্ষণ না `femWait` (40 bar) শেষ হয়।
- **Fix:**
  - Arm-এর সময় tapped POI-এর edge store করুন: `femLBot := hPoiBBot`, `femSTop := hPoiSTop`।
  - Kill লিখুন `close < femLBot` / `close > femSTop`।
  - Stage-3-এর আলাদা kill (3416, 3443) তখন অপ্রয়োজনীয় হয়ে যায়।
- **Cost:** প্রায় −15 token, ২টা `if` কম।

### E1 + D4 · P2 · Equal-rank conflict tie-তে ভুল alert, আর stage 4 আটকে থাকে
- **Line:** 4632-4634 (tie branch), 5608 (alert)
- **সমস্যা:**
  - Tie branch শুধু `anyLong`/`anyShort` false করে।
  - `sigMCLong`/`sigMCShort` true থেকে যায়। ফলে:
    - "◉ Setup machine entry" alert fire করে।
    - `suL`/`suS` 4-এ থেকে যায়, কোনো reason ছাড়া।
    - Pending engine order cancel হয়ে যায় (4826)।
  - `oneDir` off থাকলে এটা ঘটতে পারে।
- **Fix:** 4646-এর পরে এই দুই লাইন:
  ```
  sigMCLong  := sigMCLong and anyLong
  sigMCShort := sigMCShort and anyShort
  ```
- **Cost:** প্রায় +8 token।

### D5 · P2 · Conflict-এ হেরে যাওয়া side-এর CE flag winner-এর কাছে চলে যায়
- **Line:** 4619-4631; flag পড়া হয় 4692 ও 4752-এ।
- **সমস্যা:**
  - `ceLimitFill = sbCeFillL or sbCeFillS or mcCeFillL or mcCeFillS` direction দেখে না।
  - ফলে winner-এর slippage guard skip হয়।
  - আর `mcFillNext` ভুল হয়, confirmation entry next open-এর বদলে plan price-এ fill হয়।
- **Fix:**
  ```
  ceLimitFill = anyLong ? sbCeFillL or mcCeFillL : sbCeFillS or mcCeFillS
  ```
  `mcFillNext`-ও একইভাবে direction-aware করুন।
- **Cost:** প্রায় +6 token।

### D2 · P2 · আসল CE fill-এর loss tracker-এ ঢোকে না
- **Line:** 4324-4327 (মিরর 4442-4445), stage 3-এর জন্য 4187-4189
- **সমস্যা:**
  - একই bar-এ `loA <= ceL` (limit fill হয়েছে) আর `close < suLAnchorB`।
  - তখন `if close < suLAnchorB` আগে চলে, তাই "anchor FVG violated" দিয়ে setup kill হয়।
  - বাস্তবে এটা একটা loss trade, কিন্তু কখনো গোনা হয় না। Win-rate বাড়িয়ে দেখায় (survivorship)।
- **Fix:**
  ```
  bool ceHitL = (sbEnterL and sbCeTapL) or (stdEnterL and mcCeTapL)
  if close < suLAnchorB and not ceHitL
  ```
  4188-এ stage 3-কে opposing-displacement kill থেকে বাদ দিন। তারপর E8 দিয়ে fill bar-এর stop check করুন।
- **Cost:** প্রায় +12 token।

### E8 / D6 · P2 · Limit fill-এর নিজের bar-এ stop check হয় না
- **Line:** 5094-5106। Exit block 4868-এ, যা এর **আগে** চলে।
- **সমস্যা:**
  - Non-deferred limit fill-এর bar-এর wick যদি SL-ও ছোঁয়, trade তবু open হিসেবে record হয়।
  - এটা "pessimistic" নিয়মের (4873-4875) উল্টো।
  - Risk-cap clamp করা stop (4699-4701) entry bar-এর range-এর ভেতরে পড়লেও একই সমস্যা।
- **Fix** (শুধু assignment, 5114-এর পরে):
  ```
  bool fillStop = trackNew and not deferFill and (anyLong ? low <= slP : hiA >= slP)
  cntSL     := fillStop ? cntSL + 1 : cntSL
  lossToday := fillStop ? lossToday + 1 : lossToday
  trdDir    := fillStop ? 0 : trdDir
  ```
- **Cost:** প্রায় +35 token।

### B1 · P2 · Zone 50% tap-এর stop tap wick ধরে না
- **Line:** 2930 `math.max(high, top)`, 2960 `math.min(low, bot)`
- **সমস্যা:**
  - Tap হতে পারে `confirmWin` (5) bar আগে।
  - Zone-এর বাইরে wick যদি close ছাড়া হয়, zone flip হয় না।
  - তাই stop শুধু confirmation bar দেখে।
- **Fix:** 2884-এর আগে
  ```
  zHiCW = ta.highest(high, confirmWin + 1)
  zLoCW = ta.lowest(low, confirmWin + 1)
  ```
  তারপর 2930-এ `math.max(zHiCW, top)`, 2960-এ `math.min(zLoCW, bot)`।
- **Cost:** প্রায় +14 token।

### A-1 · P2 · একই bar-এ pool stamp হলে multi-bar sweep extreme হারিয়ে যায়
- **Line:** 1718, 1772, 1872, 1893 (মিরর 1696, 1764, 1880, 1901)
- **সমস্যা:**
  - Swing stamp লেখে `lastSslExt := sslExt` (1670)।
  - একই bar-এ পরে আসা EQ/PD/session stamp লেখে `lastSslExt := low`।
  - 3-bar stop run-এর raid wick হারিয়ে যায়। Machine-এর raid stop ভুল জায়গায় বসে।
- **Fix:** ৮টা জায়গায় `low` → `sslExt`, `high` → `bslExt`।
- **Cost:** 0 token।

### B2 · P2 · D4: display toggle off করলে engine মরে যায়
- **Fix:**
  - 3001-3002 থেকে `showZones and` সরান।
  - Color-এ `showZones ? COL_BULL : na` ব্যবহার করুন। Box invisible থাকবে, logic চলবে।
  - `showOB` / `showRB` input-এর label বদলে লিখুন "(logic)"।
- **Cost:** প্রায় +12 token।
- **Effect:** display setting যাই হোক, signal একই থাকবে।

### C3 · P2 · Short trap breakout accept হওয়ার পরও confirm হয় (long/short asymmetry)
- **Line:** 4028
- **সমস্যা:** long side-এ `close > _ltLLevel - ltInvAtr * atr` guard আছে, short side-এ নেই।
- **Fix:** 4028-এ যোগ করুন `and close < _ltSLevel + ltInvAtr * atr`।
- **Cost:** প্রায় +8 token।

### C4 · P2 · LT invalidation close-based করা (D6)
- **Line:** 3956, 3999
- **Fix:** `and bearBar and body >= dispFactor * atr` বাদ দিন (মিরর-সহ)। ধীরে ধীরে level পার হলে trap মরবে, আর veto 25 bar ধরে opposite engine আটকাবে না।
- **Cost:** প্রায় −14 token।

### C5 · P2 · Trap arm direction lock মানে না
- **Line:** 3964, 4004
- **সমস্যা:** opposite side arm হয়, কখনো confirm হয় না, কিন্তু 25 bar ধরে veto চালায়।
- **Fix:** `and lockOkL` / `and lockOkS` যোগ করুন।
- **Cost:** +4 token।

### D1 · P2 · SB edge / confirmation entry-এর plan price বাস্তবে trade হয়নি
- **Line:** 4335 `math.min(close, suLAnchorT) + spr` (মিরর 4451)
- **সমস্যা:**
  - Confirmation পাওয়া যায় শুধু bar close-এ, অথচ price ধরা হয় anchor-এ, যা close-এর চেয়ে ভালো।
  - শক্তিশালী confirmation candle হলে 18B "entry slipped" দিয়ে মিথ্যা kill করে, যদিও deferred fill open-এ আবার validate হয়।
- **Fix:**
  ```
  mcPlanLong := sbCeFillL or mcCeFillL ? ceL : close + spr
  ```
  Short-এর জন্য `close`।
- **Cost:** −6 token।
- **Effect:** SB edge-এর stats সৎ হবে। ভুয়া slip kill বন্ধ হবে।

### E2 · P2 · Untracked signal live trade-এর plan drawing মুছে দেয়
- **Line:** 5233
- **Fix:** `planDraw = showTrade and trackNew and not na(entryP)`।
- **Optional:** SL line-কে `trdSL`-এর সাথে sync করুন (BE বা trail হলে), প্রায় +25 token।

### E3 · P2 · Position size `syminfo.pointvalue` ধরে না
- **Line:** 5259
- **সমস্যা:** ES-এ ৫০ গুণ, NQ-তে ২০ গুণ, CL-এ ১০০০ গুণ বেশি unit দেখায়।
- **Fix:** ভাগফলে `* syminfo.pointvalue` যোগ করুন। +4 token।

### D12 · P2 · TP2 clamp liquidity আর grade দেখুক (D8 + D21)
- **Line:** 4711-4714, deferred copy 4842-4843
- **Fix:**
  - আগে থেকে থাকা `f_nearAbove` / `f_nearBelow` দিয়ে PDH/PDL, session H/L আর PWH/PWL-এও clamp করুন।
  - Zone clamp শুধু score ≥ 3 বা HTF হলে।
- **Cost:** প্রায় +30 token প্রতি side।
- **Effect:** "reward blocked" kill বাড়বে, TP2 বাস্তবসম্মত হবে। **Journal দিয়ে মেপে তারপর apply করুন।**

---

## 3. P3 — পরের ব্যাচ

| ID | কী | Line | Fix (সংক্ষেপে) | Token |
|---|---|---|---|---|
| D3 | Gate-kill retry প্রতিবার retest clock আবার শুরু করে, setup দিন পার হয়ে বাঁচে | 4342, 4567 | Stage 4-এ `suLBar` লিখবেন না; `mcRawL` flag দিয়ে test করুন | +10 |
| D7 | Machine tier সর্বশেষ sweep দেখে, setup-এর নিজের sweep না | 4523, 4529 | `armedSslBar == lastSslBar` শর্ত যোগ করুন | +10 |
| D10 | Stage 3-এ গভীর wick raid stop সরায় না (Z11-এর বাকি অংশ) | 4196, 4363 | `suL <= 2` → `suL <= 3` | 0 |
| D11 | N-C: 18B-এর সব kill terminal | 4727-4732 | Risk kill হলে 0, slip বা reward kill হলে 3 | +10 |
| D14 | Short stop-tier test-এ `spr` নেই | 4455 | `slRaidS + spr - mcPlanShort` | +2 |
| C6 | Trendline sweep bar নিজেকেই touch হিসেবে গোনে (2-touch নিয়ম আসলে 1) | 3253-3257, 3276-3280 | Sweep `if` touch-increment-এর আগে নিন | 0 |
| C7 | TL expiry-তে `WasNear` reset হয় না | 3260, 3282 | `:= false` | +6 |
| C8 | FEM entry 1-tick wick-এ fill হয়; stop FVG-এর নিচে, tap low-এর নিচে না | 3418, 3445 | CE entry `low <= (femLTop+femLBot)/2`; tap-low track করুন | +8 / +40 |
| C12 | D20 floor CISD-only shift-কে 9 দেয় | 3592 | `: nz(lastChUpBar,-1) >= suLBar ? 9 : 8` | +12 |
| C13 | Trap ambiguity penalty order-এর ওপর নির্ভর করে | 3910 | `lState == 1 and sState == 1` | 0 |
| A-3 | উল্টো রঙের candle BOS/CHoCH book করতে পারে (gap open) | 1944-1988, 2033 | `bullBar` / `bearBar` শর্ত যোগ করুন | +16 |
| A-5 | ভাঙা session level পরে আবার "raid" হিসেবে ফেরে | 1825-1848 | `hiLvl := hiBrk ? na : hiLvl` | +12 |
| A-9 | Volume floor 1, crypto-তে volume test অচল | 1262 | `volSma > 0 ? volume/volSma : na` | 0 |
| A-11 | D17: EQ pool শুধু পরপর pivot ধরে | 1372, 1403 | `prevPH2` দিয়ে দ্বিতীয় তুলনা | +40 |
| A-15 | D11: Asia `inKZ`-এ | 1453 | `inKZ = inLon or inNY or inSB` | −2 |
| B3 | HTF structure-এর প্রথম leg-এ protected swing = সব history-এর extreme | 2187, 2191 | `nz(_sup, _legLo)` / `nz(_res, _legHi)` | +6 |
| B4 | `htfLive` false হলেও HTF POI NEXT level ও TP2 clamp-এ ঢোকে | 3175, 3181, 5290, 5296 | `htfLive and` যোগ করুন | +8 |
| B5 | D7: HTF FVG-এর min height নেই | 2350, 2362 | `>= minZoneAtr * ta.atr(atrLen)` (HTF context-এ) | +16 |
| B6 | এক bar-এ একাধিক FVG invert হলে শুধু সবচেয়ে পুরনোটা IFVG zone হয় | 2713, 2743 | Price-এর সবচেয়ে কাছেরটা রাখুন | +18 |
| B7 | এক bar-এ শুধু শেষ flip band claim করে | 2906, 2937 | Band union: `math.max` / `math.min` | +10 |
| B8 | EMA bias na বা tie হলে −1 (bearish) | 2121 | `math.sign(close - ema)` | −2 |
| B10 | Z5 fix-এ HTF bias chart-TF EMA হয়ে যায় | 2128 | Floor-এ `f_autoHtf()` ব্যবহার করুন | +2 |
| B11 | RB-তে body swept high-এর নিচে close করতে হয় না | 3057, 3059 | Body-close শর্ত | +18 |
| E5 | Deferred fill TP3 "Liquidity target" mode উপেক্ষা করে | 4855 | `pendTP3` store করুন | +25 |
| E6 | ADR "(early)" flag 24h ধরে নেয় | 5530 | `time_close("D") - time("D")` দিয়ে ভাগ | +8 |
| E7 | SB structure exit বা Full time exit কোনো counter-এ পড়ে না | 4955-5003 | `cntSbX` | +30 |
| E9 | TP3 liquidity খোঁজা কাছের zone-এ আটকে যায় | 5049-5062 | SB chain (`f_nearAbove`) সবার জন্য ব্যবহার করুন | **−40** |
| E10 | Focus mode zone-এর state color মুছে দেয়, FVG স্থায়ীভাবে লুকিয়ে ফেলে | 5437, 5450 | Unconditional color set | +5 |
| E12 | Non-SB BE বা max-life exit-এ কোনো alert নেই | 5001, 5706 | `LQTRK|` alert() লাইন | +35 |
| E13 | Gate block থাকলেও LQCE pre-fill alert যায় | 5658 | `govOK and dowOK and sbOnlyOK and trdDir == 0` | +14 |
| E14 | N-D + D15: `trdToday` | 5112, 4865 | `trackNew ?` দিয়ে increment, cancel হলে refund | +15 |
| E15 | SB label-এ `mcTierL`, header-এ `finalTierL`: দুটো আলাদা tier | 5173, 5186, 5700 | সব জায়গায় `finalTierL/S` | 0 |
| B15 | নতুন SB window খুললে live setup-এর range lock বদলে যায় | 2540 | `and not sbSetLive` | +4 |
| B14 | Flip করা zone same-side dedupe আর cap এড়িয়ে যায় | 2861, 3126 | Cap trigger-এ `or not na(flipTop)` | +6 |

---

## 4. Token-cut তালিকা (signal বদলায় না)

| ID | কী | Token |
|---|---|---|
| **E4** | Long/short + SB/non-SB exit block চারবার লেখা। একটা direction-signed core বানান | **−250 থেকে −350**, প্রায় ৮টা scope কম |
| D8 | `longOK`/`shortOK`-এ ৯টা gate দুবার: `B and (sbSig or cd and pd)` | −35 |
| A-4 | Dead external break latch (`extResBrk`, `eBrokeUp`…) | −45 |
| E9 | Non-SB TP3 block মুছে SB chain ব্যবহার করুন | −40 |
| A-6 | `dispB = body >= BRK_BODY_ATR * atr` একবার হিসাব করুন (১০ জায়গায় লাগে) | −30 |
| A-8 | ১৫টা `var` constant থেকে `var` বাদ | −30 |
| B12 | Redundant guard ও clamp (2507, 2512, 2721, 2751, 2557) | −35 |
| A-7 | Pool grade expression সরল করুন | −14 |
| C4 | LT invalidation body test বাদ | −14 |
| C1 | FEM kill restructure | −15 |
| D9, B13 | `if` flag clear → assignment | 0 token, প্রায় ১০টা scope কম |
| D13 | Else-if-এর redundant `close > suLAnchorB` | −8 |
| **মোট (signal বদলায় না)** | | **প্রায় −560 থেকে −660** |

**Optional, signal বদলায়:**

| ID | কী | Token |
|---|---|---|
| C10 | LT-2 বাদ দিন। LT-6 প্রায় একই জিনিস; score কোন pattern তা পড়ে না, শুধু label বদলায় | −45 |
| C11 | Doji reversal engine বাদ দিন। এটা TBS/LT reclaim-এর strict subset | −150 থেকে −200 |
| C11 | Inside-bar engine বাদ দিন। Liquidity/POI context নেই, machine-এর BOS→retest-এর দুর্বল কপি | প্রায় −200, প্রায় ৮টা scope কম |

> Doji / IB বাদ দেওয়ার আগে journal (`LQJRNL`)-এ দেখে নিন A-tier fire প্রায় শূন্য কি না। পুরনো audit-এর cut order-এর সাথে এটা মেলে।

---

## 5. Strategy-level improvement (P4, আলাদা test লাগবে)

1. **Multi-bar PDH/PDL raid (A-2).**
   - সমস্যা: এখন PD sweep মানে এক candle-এ wick through আর close back।
   - M1/M5-এ Judas run সাধারণত bar 1-এ উপরে close করে, bar 2-এ ফিরে আসে। এটা kind 3 হিসেবে stamp হয় না।
   - ফলে `sbPoolPref` সেরা SB raid-গুলো হারায়।
   - Fix: PDH/PDL-এ `reclaimBars` window দিন। প্রায় +70 token প্রতি side।
2. **ATR floor (A-10).**
   - সমস্যা: মরা Asia সময়ে ATR ছোট হয়, তখন 0.125 ATR "firm" মাত্র কয়েক tick।
   - Fix: `math.max(0.5 * atrAvg50, …)`। প্রায় +10 token।
3. **HTF CHoCH body-blind neutral (B9).**
   - সমস্যা: ছোট body-তে protected level ভাঙলে `hsDir` আগের দিকেই থাকে।
   - Fix: breach হলে bias 0 (neutral) করুন। প্রায় +20 token।
4. **Multi-bar reclaim-এর গভীরতা (A-12).**
   - Fix: `pen` মাপুন `sslExt` থেকে।
   - এটা Z3-এর সিদ্ধান্ত আংশিক উল্টায়, তাই আপনার সিদ্ধান্ত।
5. **Continuation model (Model D).**
   - পুরনো audit-এর design gap: ordinary machine শুধু reversal ধরে।
   - Trend-এ BOS → FVG retest-এর জন্য আলাদা path নেই।
   - এখন IB engine এই কাজের দুর্বল সংস্করণ। IB বাদ দিলে সেই token দিয়ে machine-এ "BOS-shift" mode বানানো যায়।

---

## 6. ঠিক আছে — হাত দেবেন না

- CISD run tracker (1285-1310), PD/PW `[1]` + `lookahead_on` latch order (1732-1757), sweep quality stamp merge rule, RAW/EFF split.
- সব `request.security` call: repaint নেই। HTF CRT/TBS stop anchor-এর shift ঠিক।
- `f_htfStruct` protected swing definition (শুধু প্রথম leg-এর seed, B3, ঠিক করতে হবে)।
- Zone lifecycle loop index-safe। Box সংখ্যা প্রায় 60, 500-এর অনেক নিচে।
- CRT, Turtle Soup-এর logic। FEM FVG coordinate।
- Anchor lock-এর ripeness (`bar_index > suLFvgBar`)। CE limit-এর bid/ask mirror। Gate-kill mechanism। FIX-N3 veto exemption।
- Deferred fill re-validation (4841-4849)। Exit ordering (SL আগে)। Z10 BE ≠ loss।
- Drawing object budget: trade plan delete-before-redraw, POI/NEXT শুধু `barstate.islast`-এ।

---

## 7. প্রস্তাবিত version plan

| Version | কী থাকবে | আনুমানিক net token | Signal বদলায়? |
|---|---|---|---|
| **v3.8.5** (token-cut) | E4, D8, A-4, A-6, A-7, A-8, B12, D9, B13, D13 + comment fix (E11, D12, A-14) | **প্রায় −500** | না। একই chart-এ journal line মিলিয়ে দেখুন |
| **v3.8.6** (bug batch 1, stop / tracker) | C2, B1, A-1, D10, C1, E1/D4, D5, D2, E8, D14, E2, E3, E15 | প্রায় +130 | হ্যাঁ: stop চওড়া হবে, ভুয়া alert বন্ধ হবে, win-rate সৎ হবে |
| **v3.8.7** (bug batch 2, filters) | C3, C4, C5, C6, C7, B2, B4, B5, B8, D1, D3, D7, D11, E5, E9, E13, E14 | প্রায় +80 | হ্যাঁ: LT/TL/FEM signal কমবে, quality বাড়বে |
| **v3.8.8** (measure-first) | D12 TP2 clamp, A-2, A-10, B9, C8, C10/C11 engine cut | হিসাব অনুযায়ী | হ্যাঁ। Journal দিয়ে আগে আর পরে মাপুন |

**কেন এই ক্রমে:** token-cut আগে করলে বাকি সব fix বসানোর জায়গা তৈরি হয়। তাছাড়া cut-এ signal বদলায় না, তাই compile আর journal diff দিয়ে সহজে প্রমাণ করা যায় যে কিছু ভাঙেনি।

---

## 8. Test checklist (প্রতি version-এ)

1. Pine editor-এর line 2-তে নতুন BUILD stamp দেখা যাচ্ছে কি না দেখুন।
2. CE10117 এলে: v3.8.5-এর cut কাজ করেনি, অথবা editor-এ এখনো পুরনো code আছে।
3. v3.8.5: একই symbol, TF আর তারিখে `LQJRNL` line-গুলো আগের version-এর সাথে **হুবহু মিলতে হবে**।
4. v3.8.6:
   - LT, zone আর FEM signal-এ SL-এর দূরত্ব বাড়বে।
   - Debug row-এ SL count বাড়তে পারে (D2/E8 আসল loss যোগ করছে)। এটা প্রত্যাশিত।
5. Tie test: `oneDir` off রাখুন, দুই দিকের machine একই bar-এ আছে এমন জায়গা খুঁজুন। "◉ Setup machine entry" alert আর আসা উচিত না।
6. Futures (ES/NQ)-এ trade-plan label-এর "≈ units" ঠিক দেখাচ্ছে কি না দেখুন।
