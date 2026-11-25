# SMC v8.5.2b — Operator review (entry accuracy) · 2026-10-18

ফাইল: `_8/SMC_Pattern/SMC_v8.5.2.txt` (4173 line, BUILD v8.5.2b; `_7` কপির সাথে byte-identical, compiled)।
পদ্ধতি: পুরো code line-by-line পড়া (static review, chart ছাড়া)। প্রতিটি finding-এ line number, operator-দৃষ্টিতে কী ক্ষতি, আর fix প্রস্তাব।
দৃষ্টিকোণ: ৩০ বছরের FX desk / operator — "smart money কোথায় fill নিচ্ছে, indicator সেখানে কী বলছে, আর chart-এ যা দেখাচ্ছে তা সৎ কিনা"।

Severity: **P0** = entry ভুল / লুকানো loss / live-এ trade করা যায় না · **P1** = valid entry হারায় বা খারাপ দামে নেয় · **P2** = ছোট বিকৃতি।

---

## ০. এক নজরে

Structure / liquidity / zone layer মজবুত — v8.4→v8.5.2-এর fix-গুলো (H1, D1, S1, E-2, E-3) সঠিক জায়গায় বসেছে, repaint পাইনি। কিন্তু **entry engine-এ পাঁচটা গর্ত** আছে যেগুলো একসাথে accuracy নষ্ট করছে:

| # | সমস্যা | প্রভাব |
|---|--------|--------|
| R-1 | RETRACE / M74 limit fill হয়ে SL খেলে chart থেকে **মুছে যায়** ("cancel") | chart দেখে win-rate বাড়িয়ে দেখায় — সবচেয়ে বিপজ্জনক |
| R-2 | Limit arm হলে **alert নেই**, alert আসে fill-এর পরে | ⏳ / M74 setup live-এ trade-ই করা যায় না |
| R-3 | CONFIRMED mode-এ tap bar-এ sweep হলেও confirm bar-এ score **−3** | sweep-করা zone-এর সেরা entry গুলো score 8-এর নিচে পড়ে চুপ |
| R-4 | Zone-এ ৪+ bar থাকলে একই visit "2nd touch" → ⚠SWEEP REQ | 5m-এ normal basing-কেই "দ্বিতীয় touch" ধরে, R-3-এর সাথে মিলে zone মেরে দেয় |
| R-5 | Sweep → short-term high break (ICT MSS) = **iBOS**, CHoCH না | ICT-র মূল reversal model-এ M41 / M45 / M74 / M39 arm-ই হয় না |

এগুলো ঠিক না করে threshold / tier টিউন করলে লাভ নেই — ভুল জায়গা মাপা হচ্ছে।

---

## ১. P0 — entry engine

### R-1 · লুকানো loss: fill + stop = "cancel" (L3752-3771)
```
if bar_index - retBarL > window or close < retL.sl   → retL := na        (চুপচাপ মুছে ফেলা)
else if low <= retL.entry and not okL               → fill
```
- **Case A:** একটা bar limit-এর নিচে নেমে SL-এর নিচে close দিল। বাস্তবে: limit fill → SL hit = **−1R loss**। Code: "cancel", কোনো label নেই। ⏳ label থেকে যায়, কিন্তু loss-টা chart-এ কোথাও লেখা নেই।
- **Case B:** একই bar-এ `low ≤ SL` কিন্তু close SL-এর উপরে। Code: **fill signal print করে** (A+ label সহ) — অথচ wick SL ছুঁয়ে গেছে, trade ইতিমধ্যে মৃত।
- Operator ফলাফল: chart scroll করে দেখলে M74 / RETRACE-এর loser-গুলো উধাও, শুধু winner দেখা যায় → system-এর ওপর মিথ্যা আস্থা। আগের screenshot-এ "M74 A+13 6.4R" ধরনের label এই কারণেই বেশি "সুন্দর" দেখাতে পারে।
- **Fix (~60 token):** fill-check আগে, cancel পরে: `low ≤ entry` হলে fill; সেই bar-এই `low ≤ SL` (বা close < SL) হলে label "✖ M74 filled → SL" (grey), alert সহ। শুধু expiry-তে নীরব cancel।

### R-2 · Limit-এর alert নেই (L3774-3801, L4127-4130)
- Arm হলে `sigL := Sig.new()` → `hasL` false → alert() চলে না। alertcondition-ও নেই।
- Fill হলে alert আসে **fill bar-এর close-এ** — তখন দাম limit পেরিয়ে চলে গেছে। Webhook / mobile দিয়ে কেউ এই setup নিতে পারবে না; শুধু chart-এর সামনে বসে থাকলে পারবে।
- M74 সবসময় limit (L3774), E-5 auto-RETRACE বড় confirm candle-এ সবসময় limit — মানে v8.5.2-এর নতুন entry-গুলো **সবই** alert-হীন।
- **Fix (~50 token):** arm-এ `alert("⏳ M74 LONG LIMIT @ x · SL y · TP1 z · valid N bars")` + একটা alertcondition "Setup: limit armed"। Fill / stop alert আলাদা।

### R-3 · CONFIRMED mode-এ sweep-এর credit হারায় (f_conf L3449, L3451)
- v8.4.1 H2 শুধু `zoneOkBull`-এ (L2851 `poiArmL`) ঠিক করেছিল যে sweep tap bar-এ হয়েছে। কিন্তু **score** confirm bar-এর `ft.sweptLow` পড়ে, যেটা তখন false:
  - L3451: `zz.sweepReq and not sweptLow → −2`
  - L3449: `sweptLowQ or zz.idm → +1` পায় না
- ফল: ICT-র textbook entry — "2nd touch zone, SSL sweep করে wick, তারপর displacement confirm" — IMMEDIATE mode-এর চেয়ে **৩ point কম**। Tier 3 module (6) + বাকি confluence প্রায়ই 8 ছোঁয় না → rej 5।
- **Fix (~35 token):** `ZS`-এ `swept` / `sweptQ` field; arm-এর সময় (L2881-এর block) `sx.poiZb.swept := ft.sweptLow`, `sweptQ := ft.sweptLowQ`। f_conf L3449/L3451 `fv.sweptLow or zz.swept` পড়ুক। (Ctx-এ না, ZS-এ — ZS-এ জায়গা আছে।)

### R-4 · একই visit-কে একাধিক touch গোনা (L2081-2089, mirror L2152-2160)
```
if bar_index - z.lastTouch > cf.touchCooldown      // 3
    z.touches += 1   → touches ≥ 2 → sweepReq
```
- Zone-এর ভেতরে price টানা থাকলে bar t-তে touch 1, t+4-এ touch 2 → **⚠SWEEP REQ**, অথচ price কখনো zone ছেড়ে যায়নি। 5m-এ OB-তে 4–8 bar basing খুব সাধারণ — ঠিক যেখানে accumulation হয়।
- এরপর: `zoneOkBull` তখনই পাস করে যখন **সেই bar-এই** sweep, f_conf −2 (R-3), "fresh" +1 হারায় (L3443 `touches <= 1`)। Reversal candle আসে basing-এর শেষে → ততক্ষণে zone "নষ্ট"।
- **Fix (~20 token):** touch গোনো শুধু নতুন visit-এ: bull zone-এ `low[1] > z.top` (আগের bar zone-এর বাইরে ছিল), bear-এ `high[1] < z.bottom`। Cooldown রেখে দাও।

### R-5 · Sweep → MSS কে CHoCH ধরে না (f_structure L1251-1252)
- Bear trend-এ SSL sweep (নতুন LL wick) → তারপর শেষ LH pivot-এর ওপরে displaced close = ICT MSS। Engine-এ:
  - `chUpMaj` চায় close > `majorHigh` (পুরো bear leg-এর origin — সাধারণত অনেক উপরে),
  - R2 form চায় `loType == "HL"` — কিন্তু sweep low নিজেই **LL**,
  - তাই → `internalBullBOS` (শুধু "iBOS▲" label, trend BEARISH থাকে)।
- এর ফলে arm হয় না: M41 (L2673 শুধু `st.bullBOS`), M45 (L2654/2656 BOS/CHoCH), M74 (L2956 CHoCH/BOS), M39 tier 4, RCB zone, M68। বাকি থাকে শুধু M10 (sweep candle) আর M46 (CISD)।
- এটাই সম্ভবত "reversal-এ indicator চুপ, তারপর late BOS-এ ঢোকে" — এর প্রধান কারণ।
- **Fix (~90 token, trend engine না ছুঁয়ে):** নতুন feature `ft.mssUp`: `internalBullBOS` + displaced (dBrkUp) + `bar_index - ctx.sweptLowBar <= 10` (qualified বা E-3 IDM)। এটা M41 / M45 (±2 form) / M74 arm করবে, `chochReal`-এর মতো leg FVG count নেবে। Trend flip হবে না (structure-এর সততা থাকে), শুধু sweep-chain জাগবে।

---

## ২. P1 — valid entry হারায় / খারাপ দামে নেয়

### R-6 · M74 limit সবচেয়ে **অগভীর** FVG-তে (f_legFvg L1137)
- `ce < px and ce > best` → close-এর সবচেয়ে কাছের FVG = leg-এর 80–90% (premium)। SL leg origin-এ → risk বিশাল → হয় R:R reject (rej 4), নয়তো premium-এ কেনা।
- L3655 comment বলে "limit lower half of the leg by construction" — **সত্য না**। L3658-এ location score breakout bar-এর pdPct থেকে, limit-এর দাম থেকে না।
- **Fix (~40 token):** leg 50%-এর নিচের (discount) **সবচেয়ে গভীর** unmitigated FVG-এর CE; না থাকলে OTE 62% / 50%। Location বোনাস limit price-এর pd থেকে।

### R-7 · এক bar-এ একাধিক level sweep → এলোমেলো level (f_liq L1684-1691)
- Loop `n-1 → 0`; শেষ write = array-এর পুরনোতম level। একটা wick PDL আর একটা internal SSL দুটোই নিলে `sweptKindLo` "SSL" হতে পারে → M10 tier 3 → 2 (L3031), M10-এর `close > sweptPriceLo` ভুল level-এ, M54 anchor (L2700-এর block) ভুল, f_ident ভুল।
- **Fix (~25 token):** qualified level-কে অগ্রাধিকার, তারপর সবচেয়ে গভীর price।

### R-8 · 2-candle sweep (turtle soup) M10 পায় না (L2908)
- Pend path: bar t নিচে close, bar t+1 ফিরে উপরে close → SWEEP resolve t+1-এ। M10 চায় **t+1-এর** `dnWickRatio ≥ 0.5` — কিন্তু t+1 সাধারণত bullish body candle, wick ছোট → fail।
- **Fix (~20 token):** `ft.sweptExtLo < low` (pend path) হলে wick-ratio-র বদলে `cd.isBull and close > sweptPriceLo`।

### R-9 · HTF deep-PD continuation block খুব চওড়া (L3636-3637, L2535-2537)
- HTF BULL trend-এ `hPdHi` = running max → price সাধারণত HTF leg-এর উপরের 25%-এ → **প্রায় সব continuation long (M08 M36 M42 M51 M73 M33 …) block**। 5m pullback কদাচিৎ 1h leg-এর 25% retrace করে।
- HTF NEUTRAL-এ `hCurLow..hCurHigh`-এর বাইরে price → clamp 0/1 → "deep" → দুই দিকেই block। LTF-এর মতো `pdBeyond` ছাড় HTF-এ নেই।
- **Fix (~25 token):** NEUTRAL বা range-এর বাইরে → `na` (block না); HTF block শুধু যখন LTF-ও premium-এ। অথবা HTF শুধু score (block না)। আগে data দেখা দরকার (প্রশ্ন ৪)।

### R-10 · TOUCH mode-এ FVG প্রথম ছোঁয়াতেই মরে (L1448-1452, L2636)
- FVG top ছুঁলেই mitigated; D1 fix শুধু **সেই bar**-কে "at FVG" রাখে। CE / 50%-এ reaction যদি ১–৩ bar পরে আসে (সাধারণ ঘটনা) → FVG POI নেই → arm হয় না।
- **Test আজই (code ছাড়া):** FVG mitigation mode → `50%`। Code fix: at-price scan-এ gap বেঁচে থাকবে যতক্ষণ না close দিয়ে far edge ভাঙে।

### R-11 · Session filter arm-এ, fill-এ না; Asia-ও "killzone" (L3645, L2442)
- M74 / RETRACE: BOS killzone-এর বাইরে হলে arm-ই হয় না, অথচ fill হতো NY open-এ। উল্টোটা — killzone-এ arm, lunch-এ fill — অনুমোদিত।
- `sbSessOk` Asia-কেও পাস করে; forex-এ Asia = range / liquidity তৈরির সময়, entry না (score-এ ঠিকই বাদ, L3471)।
- **Fix (~20 token):** session check fill-এর সময়; input "Asia = entry নয়"।

### R-12 · TP1 আগে ছুঁয়ে পরে fill (L3752-3771)
- Arm → price সোজা TP1 পর্যন্ত → ফিরে এসে limit fill → signal print, অথচ target-এর liquidity আগেই নেওয়া। ICT-তে setup বাতিল।
- **Fix (~25 token):** arm থেকে running high/low; TP1 ছুঁলে cancel "TP before fill"।

### R-13 · RETRACE re-price min-risk floor মানে না (L3776-3779)
- `pxL - sl` 0.3 ATR-এর কম হতে পারে → R ফুলে 8R–10R। f_sig-এর P2-B floor (L3532) এখানে প্রয়োগ হয় না।
- **Fix (~15 token):** `rkL := math.max(rkL, minR)`, তারপর SL পুনর্গণনা।

### R-14 · TP1 "FAR" এর কোনো সীমা নেই (L3550, L3580)
- Nearest real level 12R দূরে হলে সেটাই TP1 → label "12R"। বাস্তবে hit-rate খুব কম; label-এর R দেখে system মূল্যায়ন ভুল হয়।
- **প্রস্তাব:** FAR হলে TP1 = maxRR-এর ভেতরের নিকটতম qualified liquidity (partial), FAR level TP2-তে; অথবা FAR-এ grade এক ধাপ নামানো।

---

## ৩. P2

| # | কোথায় | সমস্যা | Fix |
|---|--------|--------|-----|
| R-15 | L1551 | EQH/EQL price = গড় → উঁচু high-টা না নিয়েই "sweep" | EQH = max, EQL = min |
| R-16 | L3615 | zone / sweep ছাড়া setup (M58 M62 M69 M72 M74)-এর identity anchor = 0 → ৫০ bar একে অপরকে suppress | anchor = breakLvl / entry |
| R-17 | L3752-3771 | Fill gap / both-sides / identity check এড়ায় → একই bar-এ উল্টো দুই label সম্ভব | fill-কেও conflict check-এ ঢোকানো |
| R-18 | L3482-3501 | SL buffer 0.15 ATR, spread নেই; short-এর SL ask-এ hit হয় | input "spread (points)" SL / entry-তে যোগ |
| R-19 | — | News filter নেই — NFP / CPI / FOMC spike-এ M10 flood | time-block input (manual) |
| R-20 | L984 | Index (NAS / US30)-এ NY killzone 07:00–10:00; cash open 09:30 | index-এর জন্য 09:30–11:30 (setting) |

---

## ৪. আজই করা যায় (code ছাড়া)

1. **FVG mitigation mode → 50%** (R-10 test)।
2. **Sweep arms setups → Include external** (R-5-এর আংশিক উপশম, আগের E-1-এর মতো)।
3. Index-এ NY session `0930-1130`।
4. ⏳ label দেখলে **নিজে** limit বসাও — alert আসবে না (R-2)। Fill-এর পর ✖-বিহীন অদৃশ্য ⏳ মানে: হয় expire, নয়তো **SL খেয়েছে** (R-1) — chart থেকে win-rate গুনবে না।
5. Data window-এ `reject code` দেখো: long-এর ঘরে 5 (score) বেশি হলে R-3/R-4, 2 (gate) বেশি হলে R-9।

---

## ৫. Build plan প্রস্তাব (v8.5.3)

| Stage | Items | আনুমানিক token | কেন এই ক্রম |
|-------|-------|---------------|-------------|
| 1 | R-1, R-2, R-13 | ~125 | সততা + live tradability; logic বদলায় না |
| 2 | R-3, R-4 | ~55 | CONFIRMED mode-এর সবচেয়ে বড় leak |
| 3 | R-5 (`mssUp`) | ~90 | নতুন signal আসবে — আলাদা compile + chart test |
| 4 | R-6, R-7, R-8, R-12 | ~110 | M74 / M10 মান |
| 5 | R-9, R-11, R-15, R-16 | ~90 | data দেখে |

Token estimate অনুমান — compile ছাড়া নিশ্চিত না। Budget জানা নেই (v8.5.2b-র compile count report হয়নি)। Over হলে cut order: Watch row (E-6) → S5 diag plots → legend।
নিয়ম মেনে: নতুন `f_sig` / `f_conf` call site নয়; নতুন state `Sx` / `ZS`-এ, `Ctx`-এ না।

---

## ৫ক. User-এর উত্তর (2026-10-18) → priority বদল

- **Trade = chart দেখে** (alert / webhook না)। তাই R-2 (arm alert) P0 → **P1** (⏳ label chart-এ দেখা যায়)। R-1 আরও জরুরি — chart-ই একমাত্র record, আর সেটাই loss লুকাচ্ছে।
- **Symbol: XAU, NAS, BTC, USOIL** (5m)।
  - XAU / NAS / USOIL = `cfd` → killzone filter auto-on। BTC = crypto → filter off, 24/7 signal।
  - **NAS:** NY window 07:00–10:00 cash open 09:30 এর মাত্র 30 মিনিট ধরে → NAS chart-এ `0930-1130` (R-20)।
  - **USOIL:** NYMEX 09:00 open + EIA বুধবার 10:30 ET → `0800-1130` ভালো।
  - **XAU:** default London 02–05 / NY 07–10 ঠিক আছে (08:30 data)।
  - **BTC:** weekend / Asia-র পাতলা liquidity-তে sweep signal সন্দেহজনক → weekend skip input বিবেচ্য।
  - তিনটা cfd-ই news-sensitive (CPI / NFP / FOMC, oil-এ EIA) → **R-19 news time-block P2 → P1**।
- নতুন build order: Stage 1 = R-1, R-13 (+ R-2 সস্তা হলে) · Stage 2 = R-3, R-4 · Stage 3 = R-5 · Stage 4 = R-6 R-7 R-8 R-12 · Stage 5 = R-9 R-11 R-19 R-15 R-16।

---

## ৫খ. প্রয়োগ (2026-10-18) → `SMC_v8.5.3.txt` (uncompiled)

Stage 1+2: R-1 · R-2 · R-3 · R-4 · R-13 (patch script `patch_853.py`, 20 exact replace, base = v8.5.2b)। R-5 design ঠিক হয়েছে = আলাদা `mssUp` flag (পরের build)।
- নতুন field: `ZS.sw` (int), `Sx.poiSwL / poiSwS` (int — `sx.poiZb` প্রথম arm-এর আগে `na`, তাই snapshot object-এ না)।
- নতুন label: `✖ <module> filled → SL` (grey)। নতুন alert: limit arm (entry / SL / TP1), fill→SL; alertcondition "Setup: limit armed (⏳)"।
- নতুন input নেই। আনুমানিক +200 token।
- CE10117 হলে cut order: R-2-এর তিনটা alert() block → E-6 Watch row → S5 diag plots → legend।

---

## ৬. যাচাই checklist (build-এর পরে)

1. R-1: একটা M74 limit যেটা fill হয়ে SL খেয়েছে → "✖ filled → SL" label আসে কিনা।
2. R-2: ⏳ arm-এর bar-এ alert log-এ message।
3. R-3/R-4: 2nd-touch OB, tap bar-এ SSL sweep, CONFIRMED → score আগের চেয়ে +3; ৫-bar basing-এর পর zone-এ ⚠SWEEP REQ আর বসে না।
4. R-5: bear trend-এ SSL sweep → iBOS▲ → M45 / M74 arm (label "MSS")।
5. Regression: NAS-type HTF BEAR-এ continuation long এখনও block।
6. Reject code distribution আগে / পরে (2, 4, 5)।

---

## ৭. v8.5.3 live check (2026-10-18 · BTCUSDT / NAS100 / XAUUSD 5m screenshot)

Compile OK (chart-এ `✖ M74 filled → SL` দেখা যাচ্ছে → R-1 কাজ করছে)।

| # | দেখা গেছে | মানে | প্রস্তাব |
|---|-----------|------|----------|
| L-1 | তিন chart-এ প্রায় সব label = `⏳ M74 limit @ …`; বেশিরভাগ fill হয় না | M74 প্রতিটা strong BOS-এ arm হয় (R-6) — chart noise | M74 শুধু HTF BULL/BEAR (NEUTRAL না) + limit leg-এর 50%-এর নিচে (R-6) |
| L-2 | ⏳ label-এ LONG / SHORT লেখা নেই; মেয়াদ শেষ হলে label যেমন ছিল তেমনই থাকে | chart trader বুঝতে পারে না কোনটা জীবিত | label `⏳▲ M74 LONG …`; expire / fill / stop হলে label grey + text বদল |
| L-3 | XAU `M74 A10 15.9R`, `16.?R`; BTC `M10 A10 9.9R` | TP1 = FAR (R-14) — অবাস্তব R | TP1 ≤ maxRR-এর liquidity / FAR হলে grade এক ধাপ নিচে |
| L-4 | NAS: HTF BEAR, LTF BEARISH, PD `1h 12% deep`; ১৫ ও ১৭ তারিখের বড় drop-এ কোনো short নেই | R-9 (HTF deep-discount continuation block) + killzone (NAS 07–10) | HTF block শুধু যখন LTF-ও deep; NAS session 0930-1130 — reject code দিয়ে নিশ্চিত করতে হবে |
| L-5 | BTC: HTF `90% deep` → continuation long block, অথচ trend BULL | একই R-9 | একই |
| L-6 | XAU `CHoCH▼ (fake)`; sweep-এর পর MSS-এ reversal setup নেই | R-5 | stage 3 `mssUp` |
| L-7 | Watch row লম্বা, panel-এর বাইরে কাটে; NAS ৯ তারিখে label একটার উপর আরেকটা | cosmetic | Watch text ছোট; stack offset বাড়ানো |

### ৭ক. প্রয়োগ (2026-10-18) → `SMC_v8.5.4.txt` (uncompiled; base v8.5.3, `patch_854.py`, 17 replace)
- **L-2:** ⏳ label = `⏳▲ M74 LONG @ x` / `⏳▼ … SHORT @ x`। Resolve হলে grey + text: `→ filled` · `→ ✖ SL` · `expired` · `replaced`। **নীল ⏳ = এখনও জীবিত limit।**
- **R-14:** TP1 FAR হলে TP1 = Max R:R-এর ভেতরের নিকটতম liquidity (`tgt = LIQ`, tooltip-এ `⚠ TP1 = LIQ`), FAR level = TP2। Liquidity না থাকলে FAR থাকে, score −1।
- **R-9:** HTF deep block তখনই, যখন 5m leg-ও একই দিকে (long: premium, short: discount, leg-এর ভেতরে)। HTF NEUTRAL → HTF PD নেই।
- CE10117 হলে cut order: R-2 alert blocks → Watch row → S5 plots → legend।
