# দ্বিতীয় পাস · Adversarial Verify + Exact Patch Plan — `liqudity_trap_trading.v3.8.5.txt`

> তারিখ: 2026-10-18 · সব line number **v3.8.5** ফাইলের। আগের doc: [REVIEW_v3.8.5_OPERATOR_BN.md](REVIEW_v3.8.5_OPERATOR_BN.md)।
> **লক্ষ্য:** আগের review-এর প্রতিটা finding-কে **ভুল প্রমাণ করার চেষ্টা** করা হয়েছে, অর্থাৎ অন্য কোনো code path আগে থেকেই কি এটা ঠিক করে? যেগুলো টিকেছে, সেগুলোর জন্য **হুবহু BEFORE/AFTER Pine patch** লেখা হয়েছে।
> **Calibration:** XAUUSD M1/M5, NAS100/US30 M5, BTC। Spread input broker অনুযায়ী set আছে ধরে নেওয়া হয়েছে।
> **কোনো code বদলানো হয়নি, কিছু compile করা হয়নি।** Patch-এর token সংখ্যা আনুমানিক (±30%)।

**পূর্ণ patch code** (English, verbatim BEFORE/AFTER, line number সহ), `patches_v3.8.6/` folder-এ:

| File | Group | Item |
|---|---|---|
| [G1_tracker_honesty.md](patches_v3.8.6/G1_tracker_honesty.md) | Tracker / alert / journal | #3, E1, E8, D2, D5, E3, F-1, E4, NEW-1 |
| [G2_raid_detection.md](patches_v3.8.6/G2_raid_detection.md) | Liquidity raid (MODULE 1-5) | #1, A-1, #6, #7, F-5, F-6, A-10 |
| [G3_engine_stops.md](patches_v3.8.6/G3_engine_stops.md) | LT trap, zone stop | C2, LT-7, B1, C3, C4, C5, LT-3, C13 |
| [G4_htf_continuation.md](patches_v3.8.6/G4_htf_continuation.md) | HTF structure / POI / S-1 | #8, B5, N-1…N-7, A-4, F-2 |

---

## 0. সংক্ষেপ — কী টিকল, কী ভাঙল

- **৩৫টা item যাচাই করা হয়েছে:**
  - **২৭টা CONFIRMED।**
  - **৬টা PARTIAL।** Bug সত্যি, কিন্তু default setting-এ ঘটে না, অথবা আংশিক।
  - **১টা REFUTED** (F-2 day boundary)।
  - **১টা ভুল দিক:** E8 যতটা বলা হয়েছিল, ততটা না।
- **নতুন bug ৯টা।** সবচেয়ে গুরুত্বপূর্ণ ৩টা:
  1. **G1 NEW-1 ★ (P1):** final gate machine signal মারে, কিন্তু `mcPlanLong/Short` clear করে না (4539-4546)।
     - ফলে একই bar-এ কোনো engine signal থাকলে তার entry দাম ধরা হয় মরা machine-এর CE-তে (4671 `nz(mcPlanLong, close)`)।
     - Slip guard, risk cap, TP2, minRR, plan line, journal-এর `E` — সব ভুল দামে হিসাব হয়।
     - **Fix:** ২টা `:= na` লাইন, +6 token। নিজে code খুলে মিলিয়ে দেখা হয়েছে।
  2. **G1 #3-এর বিস্তার:** SB "Partial" time exit TP1 ছোঁয়ার আগেই stop entry-তে নিয়ে আসে।
     - পরে 0R-এ scratch হলে সেটা SL **এবং** `lossToday`, দুই জায়গাতেই গোনা হয়।
     - দুটো scratch হলেই `maxLossDay = 2`-এ দিন বন্ধ হয়ে যায় (G1 NEW-2)।
  3. **G3 NEW-1:** LT-7-এর invalidation break level-এ বাঁধা, যা supply zone-এর **নিচে**।
     - তাই C4 fix একা দিলে LT-7 arm-এর পরের bar-েই প্রায় সবসময় মরবে।
     - **C4 আর LT-7 fix একসাথে ship করতে হবে।**
- **Budget:**
  - সব patch মিলিয়ে net প্রায় **+196 token**।
  - এর মধ্যে E4-এর −320 আর #6-এর −59 আছে।
  - নতুন `if` scope প্রায় **−35** (E4 থেকে)।
  - নতুন plot, alertcondition বা `request.security` নেই।
  - একটা HTF tuple 3 থেকে 5 element হচ্ছে। এর destructuring site মাত্র একটা (2232)।

---

## 1. আগের review-এর সংশোধন (সৎভাবে)

| আগের দাবি | এখন | কারণ |
|---|---|---|
| E8 fill-bar stop check হয় না (P2) | **PARTIAL, default-এ ঘটে না** | Immediate fill-এর stop সবসময় bar-এর নিজের low-এর নিচে / high-এর উপরে বানানো হয় (4331, 4450, 4677)। শুধু `riskMode = "Clamp the stop"` হলে stop bar-এর ভেতরে পড়ে, আর default হলো Reject |
| E1/D4 tie-তে ভুয়া alert (#10) | **CONFIRMED, কিন্তু default-এ ঘটে না** | `oneDir = true` (default) হলে lock দ্বিতীয় machine-কে আগেই মারে (4537)। শুধু `oneDir` off থাকলে ঘটে |
| D2 CE loss গোনা হয় না = "stop-out" | **CONFIRMED, তবে অন্য রূপে** | Stop bar-এর low-এর নিচে, তাই এটা stop-out না। এটা **অমাপা fill** (survivorship)। আলাদা `cntVoid` + `lossToday` দিয়ে book করতে হবে |
| D5 CE flag direction-blind | **PARTIAL** | `mcFillNext` অংশ আসলে কোনো প্রভাব ফেলে না। `ceLimitFill` অংশ সত্যি, কিন্তু সেটাও `oneDir = false` লাগে |
| A-1 same-bar ext overwrite (P2) | **আজ latent** | আজ pool multi-bar raid stamp করতেই পারে না, তাই ক্ষতি হয় না। #1 fix এলে এটা ক্ষতিকর হবে, তাই #1-এর সাথে 0 token-এ ঠিক হয় |
| F-2 day boundary (D16/E6) bug | **REFUTED** | `time("D")` আর `adrVal` একই symbol session day ব্যবহার করে, তাই ADR% নিজের মধ্যে সামঞ্জস্যপূর্ণ। NY midnight-এ সরালে উল্টো ভাঙবে। Midnight open আলাদা **feature** হিসেবে রাখা হলো (প্রায় +30) |
| A-10 ATR floor | **PARTIAL** | 50-bar average-এর floor প্রায় কখনো কাজে লাগে না। আসল low-vol সমস্যা হলো ATR প্রায় spread-এর সমান হয়ে যাওয়া, সেটা F-6 সমাধান করে |
| B1 zone stop | **CONFIRMED, শর্তসাপেক্ষ** | Tap আর confirm-এর মাঝে (৫ bar পর্যন্ত) wick zone edge পার হলে তবেই ক্ষতি হয় |
| "request.security 7টা" (header 526) | **ভুল, আসলে 8** | `f_bias` দুবার call হয়। শুধু comment fix |

> **Live trading-এর জন্য অর্থ:** E1, E8, D5 আপনার default setting-এ (`oneDir` on, risk Reject) আপনাকে এখন আঘাত করছে না। Priority নিচে নামানো হলো।

---

## 2. Group-ভিত্তিক verdict

### G1 · Tracker / journal সততা

| # | Verdict | Default-এ ঘটে? | Δ token | এক লাইনে fix |
|---|---|---|---|---|
| #3 cntSL = BE/trail | **CONFIRMED+** | হ্যাঁ | +40 (E4-এর ভেতরে +12) | "Stop entry-তে বা তার পার" = `trdProt`; `cntBE` নতুন; SL alert text "SL / BE / trail" |
| NEW-1 মরা machine-এর plan price ★ | **CONFIRMED** | হ্যাঁ | +6 | 4539-4546-এ `mcPlanLong := na` |
| F-1 exit journal | **CONFIRMED** | হ্যাঁ | +130 (MFE/MAE বাদ দিলে −40) | `LQEXIT\|side\|SB/NS\|tag\|R\|bars\|MFE\|MAE\|fill\|exit\|ΣR` |
| D2 CE void fill | **CONFIRMED** | হ্যাঁ | +35 | `ceVoidL/S` + `cntVoid` + `lossToday` |
| E3 position size | **CONFIRMED** | futures-এ | +12 | `* syminfo.pointvalue`, cost যোগ, "contracts" |
| E4 exit ×4 dedupe | **CONFIRMED** | — | **−320, −35 scope** | একটা signed core (`d = ±1`) + `f_tight` helper |
| D5 | PARTIAL | না | −2 | direction-aware ternary |
| E1/D4 | CONFIRMED | না | +8 / +40 | tie `else`-এ clear + rollback |
| E8 | PARTIAL | না (শুধু Clamp mode) | +25 | fill-এর পরে −1R book |

> **F-1-এর একটা সূক্ষ্ম বিষয়:**
> - একই bar-এ পুরনো trade বের হয়ে নতুন trade ঢুকতে পারে।
> - তাই `trdDir == 0 and trdDir[1] != 0` দিয়ে exit ধরলে সেই bar-গুলোতে exit মিস হয়।
> - Patch exit ধরে L4998-এর ঠিক পরে, pending fill-এর পরের snapshot `trdDirIn` দিয়ে।

### G2 · Raid detection

| # | Verdict | Δ token | মূল কথা |
|---|---|---|---|
| #1 PD/PW multi-bar | **CONFIRMED** | +8 | FIX-Z2 এক close-কেই "acceptance" ধরে, অথচ file-এর নিজের FIX-Y3 নিয়মে acceptance মানে `reclaimBars`-এর বেশি close। নিজের নিয়মের সাথেই সাংঘর্ষিক |
| #1 EQ pool | **CONFIRMED** | +16 | `line.delete` ভেতরের `if`-এর **বাইরে**, তাই break bar-েই pool মুছে যায় |
| #1 session H/L | **CONFIRMED** | +62 | `f_sesTrack`-এ `var int hiBrkB` |
| shared window | — | +32 | `hiN`, `loN`, `cAbv`, `cBlw`, সব global scope-এ |
| #6 SL pad | **CONFIRMED** | **−59** | `slPad = SL_PAD_ATR * atrRaw`, **৩২টা জায়গায়** replace |
| #7 rollover | **CONFIRMED** | +60 | `rollOn` / `rollSes` = 1655-1810 NY। Window-এর **যেকোনো** bar rollover-এ থাকলে false (17:00-18:00 halt-এর পরেও 16:59-এর spike window-এ থেকে যায়) |
| F-5 Asia raid in KZ | **CONFIRMED** | +4 | 1920: `(sbCtx or inKZ) and sbAsiaPool` |
| F-6 spread-aware | **CONFIRMED** | −6 | `nearSp = math.max(NEAR_LVL_ATR * atr, spr)`, শুধু 1626, 1630, 1689-এ |
| NEW session re-raid | NEW, P3 | +4 | 1 ATR (XAU M1-এ প্রায় $0.6) → `SWEEP_CTX_ATR * atr` |

### G3 · Engine stop / trap

| # | Verdict | মূল প্রমাণ |
|---|---|---|
| C2 long | **CONFIRMED** | Confirm bar retest bar-এর পরে আসতেই হবে, তাই retest wick কখনো stop-এ ঢোকে না |
| C2 short | **CONFIRMED, আরও খারাপ** | Arm bar-এর poke high-ই trap wick। Default setting-এ প্রতিটা LT short-এ এটা stop-এর **বাইরে** থাকে |
| LT-7 supply top | **CONFIRMED** | Stop supply zone-এর ভেতরে বসে |
| C3, C4, C5, LT-3, 3957, C13 | **CONFIRMED** | C5: আসল fix হলো veto-তে lock দেওয়া, arm-এ দেওয়া পরের কাজ |
| LT-7 arm | PARTIAL | শুধু একই bar-এ LT-1 long-এর সাথে সংঘর্ষ ভুল |
| B1 | CONFIRMED (শর্তসাপেক্ষ) | `Zone` type-এ শেষ field হিসেবে `float tapExt` যোগ করুন, তাতে `Zone.new` call-গুলো ভাঙবে না |

**Token:** প্রায় +107।
**Side effect:**
- XAU-তে LT short stop প্রায় 0.3-1.0 ATR চওড়া হবে। এর **২০-৪০%** 1.5 ATR cap-এ reject হতে পারে।
- Signal কমবে, কিন্তু প্রতি signal-এর win-rate বাড়ার কথা।

### G4 · HTF / continuation

| # | Verdict | Δ token | Fix |
|---|---|---|---|
| #8 HTF latch | **CONFIRMED** | +6 | `_dispH` দিয়ে `_upBrk`/`_dnBrk` gate করুন, 2200-এ reuse করুন |
| B5 HTF FVG height | **CONFIRMED** | +16 | `f_htfPoi`-এর মাথায় `_hAtr` |
| N-6 picker jump | **CONFIRMED** | +16 | `fresher2/3`-এ `and (demand ? close > pT : close < pB)` |
| N-1 cont A+ | **CONFIRMED** | +8 | `qualOk = not suLCont and …`। `suLCont` fire bar-এ এখনো true থাকে, কারণ reset হয় পরের bar-এ (4152) |
| N-2 liq override | **CONFIRMED (tier leak)** | −2 | **Score-এ রাখুন, tier থেকে সরান:** 3546-3547 মুছে override `scoreBaseL/S`-এর ভেতরে দিন। পুরো সরালে cont entry 41-58 score পাবে, আর minScore 50-এ অনেকগুলো আটকে যাবে |
| N-4 + N-5 + NEW-2 | **CONFIRMED** | +40 | `f_htfStruct` থেকে `_legLo[1]`, `_legHi[1]` export করুন। `contArmL`-এ যোগ করুন: `nz(hPoiBIn) == 0 and not (close < hsProtLo or hPoiBTop > (hsProtLo + hsLegHi) / 2)` |
| N-7 | **CONFIRMED** | +10 | Cont-কে শুধু stage 2-এ opposing displacement থেকে ছাড় দিন |
| A-4 dead latch | **CONFIRMED dead** | **−45** | মুছে দিন |
| NEW-1 fastShift stale `sslInPlay` | PARTIAL | +4 | `and not suLCont` (optional) |

> **N-2 বদলালে N-1-এর `f_tier` অংশ আর লাগে না।** কারণ raw liq ≥ 10 মানেই `sslInPlay`।

---

## 3. Calibration — আপনার তিন market

| Setting / effect | XAUUSD M1 | XAUUSD M5 | NAS100 / US30 M5 | BTC |
|---|---|---|---|---|
| `reclaimBars` (#1) | 4 (default) = ৪ মিনিট, ঠিক আছে | 3-4 | **2-3**। ৪ মানে ২০ মিনিট, যেটা retest-কে reclaim বানিয়ে ফেলে | 4 |
| `slPad` (#6), NY open | $0.42 থেকে প্রায় $0.70, মোটামুটি এক spread | চওড়া হবে | 09:30-এ সবচেয়ে বড় পরিবর্তন | কম প্রভাব |
| Rollover filter (#7) | **ON** | **ON** | **ON** (17:00-18:00 halt) | Exchange BTC হলে **OFF**। CFD BTC হলে Manual profile + ON |
| `nearSp` (F-6) | penetration floor $0.30, firm $0.15 | প্রভাব নেই | প্রভাব নেই | প্রভাব নেই |
| `maxRiskAtr` | 1.5 → C2-এর পরে **journal দেখে 2.0** | 1.5-2.0 | 1.5-2.0 | 2.0 |
| `riskMode` | **Reject** রাখুন। Clamp করলে stop আবার trap wick-এর ভেতরে চলে যায় (G3 NEW-3) | Reject | Reject | Reject |
| PD day | broker session (17:00 NY) | একই | একই | **UTC day**, PWH/PWL সোমবার 00:00 UTC |

---

## 4. Build plan (আপডেট করা)

নিয়ম: নতুন versioned file, line 2-তে BUILD stamp, নতুন `if` scope / output নয়।

| Version | কী থাকবে | Net token | কেন |
|---|---|---|---|
| **v3.8.6 · Honest tracker** | **G1:** E4 (+#3) → F-1 → NEW-1 → D2 → E3। সাথে **G4:** A-4 (−45), N-1 (+8), N-2 (−2) | প্রায় **−100** | মাপার যন্ত্র আগে। NEW-1 আর N-1 ভুল দাম ও ভুল tier দেখায়, তাই এখানেই |
| **v3.8.7 · Stops & raids** | **G2:** সব (#6 আগে, কারণ −59) + **G3:** C2+LT-7+C3+C4 একসাথে, B1, C5 veto, LT-3 | প্রায় **+230** | সবচেয়ে বেশি টাকা এখানে। C4 আর LT-7 আলাদা করা যাবে না |
| **v3.8.8 · HTF / cont** | **G4:** #8, B5, N-6, N-4/N-5, N-7, NEW-1 | প্রায় **+90** | S-1-কে শক্ত ভিত দেওয়া |
| পরে | E1, D5, E8 (default-এ ঘটে না), C13, midnight open, SMT | — | চাহিদা অনুযায়ী |

**CE10117 এলে কী কাটবেন (ক্রমানুসারে):**
1. F-1-এর MFE/MAE অংশ (−40)
2. Doji/IB engine (−350)
3. LT-2 (−45)
4. Tooltip

---

## 5. Test checklist

**v3.8.6**
1. Line 2-তে `BUILD v3.8.6-b1` দেখা যাচ্ছে কি না দেখুন।
2. Non-SB trade TP1 ছুঁয়ে BE stop-এ বের হলো। Debug-এ দেখাবে `TP1+1, BE+1, SL+0`, আর LQEXIT-এ R প্রায় +0.1।
3. SB trail exit → `BE`, R > 2।
4. Gap stop → R < −1।
5. একই bar-এ exit আর নতুন entry → এক alert-এ দুটো line।
6. CE limit touch করে FVG-এর নিচে close করল → `void+1`, `lossToday+1`।
7. Cont (`MCc`) trade কখনো A+ পাবে না।
8. Cont চলাকালীন sweep ছাড়া engine signal → tier B।
9. **SB Partial time-exit scratch আর loss হিসেবে গোনা হবে না।**
10. **Alert re-create করুন।** SL alert-এর text বদলেছে।

**v3.8.7**
1. XAU M5 London-এ ২ bar PDH-এর উপরে close, তারপর নিচে → kind 3 stamp হবে, SB arm হবে।
2. 17:00 / 18:00 NY bar-এ sweep stamp হবে না।
3. LT short-এর SL trap high-এর উপরে বসবে।
4. Journal-এ reject % আর stop-out % আগে আর পরে তুলনা করুন।

**v3.8.8**
1. H1-এ দুর্বল close protected high ছুঁয়ে গেল, তারপর displaced close এলো → `hsDir` flip করবে।
2. H1 premium-এ থাকা demand-এ cont arm হবে না।

---

## 6. আপনার কাছ থেকে যা জানা দরকার

1. **`sbTimeMode`:** আপনি "Partial" ব্যবহার করেন? করলে G1 NEW-2 (scratch = loss, দিন বন্ধ) আপনাকে **এখনই** আঘাত করছে, আর v3.8.6 জরুরি।
2. **`oneDir` আর `riskMode`:** default (on / Reject) রেখেছেন? রাখলে E1, D5, E8 পিছিয়ে দেওয়া হবে।
3. **BTC:** exchange feed (Binance/Bybit), না broker CFD? এর ওপর নির্ভর করে rollover filter কোন profile-এ default ON থাকবে।
4. **NAS/US30 M5-এ `reclaimBars`:** 2-3 করবেন, না journal দেখে ঠিক করবেন?
5. **v3.8.6 build শুরু করবো?** §4-এর প্রথম সারি অনুযায়ী।
