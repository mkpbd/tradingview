# SMC / ICT Suite v8.4.0 — ফরেনসিক অডিট (Operator entry footprint)

তারিখ: 2026-10-14 · ফাইল: `SMC_Pattern/SMC_v8.4.0.txt` (Pine v6, 3,915 লাইন) · দৃষ্টিকোণ: professional forex operator — "entry কোথায় valid, কোড কোথায় ভুল"

---

## ১. এক নজরে রায়

v8.4.0-এর architecture ঠিক আছে। কিন্তু **entry footprint-এর ৩টি জায়গায় কোড নিজের নিয়মের সাথে নিজেই বিরোধ করে**, আর সেগুলো ঠিক সেই জায়গা যেখানে একজন operator ঢোকে:

| # | সমস্যা | কোথায় | প্রভাব |
| --- | --- | --- | --- |
| F1 | CONFIRMED / MSS mode-এ "sweep-required" zone কখনো trade হয় না — sweep flag শুধু sweep bar-এ true, confirm bar-এ false | L2706-2707, L3346 | §6.2 "sweep + pin bar" entry — সবচেয়ে ভালো setup — নীরবে বাদ, উল্টো f_conf −2 |
| F2 | SL zone bottom-এ বসে, reaction/sweep wick-এর নিচে নয় | L3366-3385 | stop wick-এর ভেতরে → re-test-এ stop hunt |
| F3 | FVG-only tap-এ SL = confirm candle-এর low (reaction low নয়) | L3366-3385, L2928 | M41 / M46 / M49 / M52 / M68 সবার SL ভুল |
| F4 | weak break expire হলে `hiBroken` reset হয় না → পরের displaced close-এ BOS হয় না | L1059, L1067 | BOS নেই → OB তৈরি হয় না → M36/M37/M42/M51 মরে যায় |
| F5 | HTF: non-displaced break-এ `hHiBroken` lock → bias stale | L2128, L2142 | gate, f_conf, P1-E সব ভুল bias পড়ে |
| F6 | M37-এর IDM sweep: যে candle inducement নেয় আর OB tap করে একই সাথে, সে IDM✓ পায় না | L1180-1181 | সবচেয়ে উঁচু rank-এর module (43) সবচেয়ে common form-এ চুপ |
| F7 | ZONE EDGE "limit" entry long-এ close-এর উপরে বসতে পারে | L3395-3397 | label বলে LIMIT, আসলে market-এর চেয়ে খারাপ দাম |

এর বাইরে P1/P2 পর্যায়ের ৯টি বিষয় §৩-এ। কোনোটিই compile-ভাঙা bug নয়; সবগুলোই **logic bug — signal দেয় ভুল দামে, বা সঠিক setup-এ signal দেয় না**।

---

## ২. Operator entry footprint — আদর্শ ক্রম বনাম কোড

একজন forex operator (5m/15m, HTF 1h/4h) যে ক্রমে ঢোকে, আর v8.4.0 সেটার কতটুকু করে:

| ধাপ | Operator যা দেখে | কোড যা করে | অবস্থা |
| --- | --- | --- | --- |
| 1 | HTF bias + HTF POI (1h OB / FVG) | `hTrend` + HTF FVG flag (P1-B) | ✅ bias · ⚠ HTF OB নেই · ❌ F5 bias lock |
| 2 | Liquidity নেওয়া (Asia low / PDL / EQL / SSL sweep) | `sweptLowQ`, `sweptLow`, SESH/SESL | ✅ · ⚠ F11 (2-bar sweep ভুল candle), F8 (EQL দাম গড়) |
| 3 | Displacement + MSS/CHoCH, লেগে FVG | `bullCHoCH` + `chochReal`, `dispBull` | ✅ · ❌ F4 (weak-break lock BOS আটকায়) |
| 4 | Retrace → POI (OB / FVG / BRK), discount, OTE | zone slot, `inDiscount`, OTE +1 | ✅ · ⚠ F13 (CHoCH লেগের OB তৈরি হয় না, শুধু RCB) |
| 5 | Reaction candle, তারপর short-term high close (MSS) | `poiDirL` state machine, MSS mode | ✅ · ❌ F1 (sweepReq zone বাদ) · ⚠ F9 (arm-bar-এ 50% rule) · ⚠ F14 (window 8) |
| 6 | Entry: POI / candle 50% · SL sweep wick-এর নিচে · TP opposing liquidity ≥ 2R, পথ পরিষ্কার | P1-A entry · f_stop · f_nearestOpp · f_pathBlock | ❌ F2, F3 (SL) · ❌ F7 (entry) · ⚠ F12 (path শুধু zone দেখে) |
| 7 | Killzone (London 02-05 / NY 07-10 NY time) | `ssnFilt` auto-on forex/cfd | ✅ · ⚠ F10 (tap ভেতরে, confirm বাইরে → reject) |

**Footprint module-গুলো**: M41 (sweep → displacement FVG → retrace), M45 (sweep → CHoCH → BRK/OB), M68 (HTF sweep → LTF CHoCH → zone), M37 (IDM → OB), M54 (demand → stop hunt → BOS → retrace), M42 (HP S&D)। এই ৬টির প্রতিটি F1/F2/F3 দ্বারা আক্রান্ত; M37 অতিরিক্ত F6।

---

## ৩. Finding-গুলো বিস্তারিত

প্রতিটিতে: কোড, কেন ভুল, operator-এর ক্ষতি, token-safe fix।

### F1 · P0 · sweep flag per-bar, কিন্তু trigger multi-bar

```pine
// L2706
zoneOkBull = atBullZone and zMidB and (not fl_SwR or not ft.zb.sweepReq or ft.sweptLow) and (...)
// L3346
sc -= zz.sweepReq and not ((isLong and fv.sweptLow) or (not isLong and fv.sweptHigh)) ? 2 : 0
```

`ft.sweptLow` শুধু সেই bar-এ true যেখানে f_liq level resolve করে। CONFIRMED / MSS mode-এ arm bar-এ sweep হলে `zoneOkBull` true → `poiDirL = 1`। ১-৮ bar পরে confirm bar-এ `ft.sweptLow = false`, zone-এর `sweepReq = true` (snapshot `sx.poiZb`-এ) → `zoneOkBull = false` → s08 / s36 / s37 / s39 / s40 / s42 / s45 / s51 / s54 / s70 / s73 সবই `zoneOkBull and trigBull` → false। `trigBull` true হলেও signal নেই, reject code 1 (no candidate)। তার উপর f_conf −2।

**Operator-এর ক্ষতি**: দ্বিতীয়বার যাওয়া zone-এ sweep + reversal — ICT-র "sweep the inducement, then tap" — ঠিক যেটা §6.2 চায়, সেটাই v8.4.0 default mode-এ অসম্ভব। IMMEDIATE mode-এ (v8.3) কাজ করত; P0-A default বদলানোর পর নীরবে ভেঙেছে।

**Fix** (main scope, নতুন `if` নেই, ~40 token):
```pine
// zoneOkBull-এর আগে
swL10 = ft.sweptLow or bar_index - ctx.sweptLowBar <= 10 or bar_index - ctx.intSwpBull <= 10
swH10 = ft.sweptHigh or bar_index - ctx.sweptHighBar <= 10 or bar_index - ctx.intSwpBear <= 10
zoneOkBull = atBullZone and zMidB and (not fl_SwR or not ft.zb.sweepReq or swL10) and ...
zoneOkBear = atBearZone and zMidS and (not fl_SwR or not ft.zs.sweepReq or swH10) and ...
```
f_conf-এ `fv.sweptLow` → একই window দরকার; f_conf-এর signature না বদলে `Feat`-এ দুটি bool যোগ করা যায় (`swRecentL/S`) অথবা `fv.sweptLow` লেখার পর main scope-এ `ft.sweptLow := swL10` করলে label "SWEEP✕" প্রতি bar আসবে — তাই Feat field-ই নিরাপদ। `ctx.intSwpBull` pivot-wick sweep ও internal-liquidity sweep দুটোই ধরে (L2240-2259)।

### F2 · P0 · SL zone bottom-এ, wick-এর নিচে নয়

```pine
// L3371-3372
if zz.kind != ""
    sl := isLong ? zz.bottom - buf : zz.top + buf
```

State machine invalidation = `sx.poiLowL = min(low, zone bottom)` (L2737), কিন্তু f_stop সেটা পড়ে না। Reaction candle-এর wick zone bottom ভেদ করলে SL wick-এর **উপরে** বসে। M10-র note বলে "SL below sweep low" (L2874) কিন্তু zone slot ভরা থাকলে zone bottom নেয় — sweep wick-এর ভেতরে।

**Operator-এর ক্ষতি**: forex-এ POI-র wick re-test স্বাভাবিক (London-এর প্রথম ঘণ্টায় প্রায় নিয়ম)। stop wick-এর ভেতরে = stop hunted, তারপর trade আসল দিকে যায়। এটা "stop ঠিক ছিল, তবু loss" নয় — stop ভুল ছিল।

**Fix**: f_stop-এ দুটি param যোগ (call site মাত্র ২, L3408 ও L3437; f_bid নয়, তাই inline cost নেই):
```pine
f_stop(cf, cx, fv, isLong, aV, bufA, maxA, ep, refLo, refHi) =>
    ...
    if zz.kind != ""
        sl := isLong ? math.min(zz.bottom, refLo) - buf : math.max(zz.top, refHi) + buf
    else if (isLong and fv.sweptLow) or (not isLong and fv.sweptHigh)
        sl := isLong ? refLo - buf : refHi + buf
    ...
        else
            sl := isLong ? refLo - buf : refHi + buf
```
main scope-এ:
```pine
slRefLo = immMode or na(sx.poiLowL)  ? math.min(low, low[1], low[2])  : math.min(low, sx.poiLowL)
slRefHi = immMode or na(sx.poiHighS) ? math.max(high, high[1], high[2]) : math.max(high, sx.poiHighS)
```
`low[1], low[2]` IMMEDIATE / M10-র জন্য: F11-এর 2-bar sweep-ও ঢাকে। f_sig-এর signature-এ ২টি param যোগ (call ২টি)। `sx.poiLowL` reset হয় না confirm-এর পর, কিন্তু `poiConfL` শুধু সেই bar-এ true যে bar-এ arm জীবিত ছিল, তাই মান তাজা।

### F3 · P0 · FVG-only tap: SL confirm candle-এর low

`reactBull = zoneOkBull or ft.atBullFvg or (poiConfL and sx.poiFvgL)` (L2928)। FVG tap-এ `ft.zb.kind == ""` → f_stop: sweep নেই → majorLow 2 ATR-এর ভেতরে না হলে `low - buf` — **confirm bar-এর** low, যা reaction low-র উপরে (দাম ইতিমধ্যে উঠে গেছে)। M41 / M46 / M49 / M52 / M68 — footprint-এর তিনটি (M41, M68, M46) এখানে।

**Fix**: F2-র `slRefLo` একই সাথে এটা ঠিক করে (`sx.poiLowL` FVG tap-এ reaction low)।

### F4 · P0 · weak break lock

```pine
// L1058-1061
if brkUp
    cx.hiBroken := true
// L1066-1067
if bar_index - sx.stPendBar > pendBars
    sx.stPendDir := 0            // hiBroken থেকে গেল true
```

Close 1 tick উপরে ছোট candle → weak → 3 bar-এ follow-through নেই → বাতিল। কিন্তু `hiBroken = true` পরের pivot high পর্যন্ত (কমপক্ষে swingLen×2 = 10 bar)। এর মধ্যে বড় displacement candle একই swing ভেদ করলে `brkUp = false` → BOS নেই, `dispBull` নেই, `lastDepStrong` পুরোনো, **OB তৈরি হয় না** (OB শুধু BOS bar-এ, L1967)। একই জিনিস failed follow-through-তে (L1039-1047: `stBrkDir := 0` কিন্তু hiBroken থাকে)।

**Operator-এর ক্ষতি**: forex-এ ঠিক এই ক্রমই চলে — ছোট poke, pullback, তারপর আসল displacement। Indicator আসলটাকে চিনতে পারে না; pullback-এ তৈরি OB নেই, তাই M36 / M37 / M42 / M51-এর কিছু নেই trade করার।

**Fix** (f_structure, বিদ্যমান branch-এ ২ লাইন):
```pine
if bar_index - sx.stPendBar > pendBars
    if sx.stPendDir == 1
        cx.hiBroken := false
    else
        cx.loBroken := false
    sx.stPendDir := 0
```
আর failed follow-through block-এ (L1041-1043) `cx.hiBroken := false` / `cx.loBroken := false` dir অনুযায়ী। `if` scope যোগ হচ্ছে function-এর ভেতরে, main scope-এ নয়।

### F5 · P0 · HTF bias lock

```pine
// L2125-2130
if bBrk
    cx.hHiBroken := true
...
if dispH            // L2142 — body ≥ 50% range না হলে কিছুই বদলায় না
```

HTF (1h/4h) breakout candle-এর body প্রায়ই 50%-এর নিচে (long wick breakout)। তখন `hHiBroken = true`, bias বদলায় না, এবং এই swing আর কখনো "break" হয় না — পরের HTF pivot (3 bar × 2 = 6 HTF candle = 5m-এ 72 bar) পর্যন্ত। LTF-এর pending mechanism HTF-এ নেই। `f_gate`, f_conf-এর HTF +1, P1-E continuation block — সব stale bias-এ।

**Fix** (f_htf, Sx-এ ১টি int):
```pine
// Sx
int hPend = 0        // ±1 — non-displaced HTF break, next HTF close confirms
// f_htf
if bBrk
    cx.hHiBroken := dispH
if sBrk
    cx.hLoBroken := dispH
promH = (sx.hPend == 1 and bBrk) or (sx.hPend == -1 and sBrk)
sx.hPend := bBrk and not dispH ? 1 : sBrk and not dispH ? -1 : 0
if dispH or promH
    ... (বিদ্যমান block, dispH-এর জায়গায়)
```
দ্বিতীয় পরপর HTF close একই দিকে = promoted। `bBrk and not dispH` হলে hHiBroken false থাকে তাই পরের candle আবার bBrk হতে পারে।

### F6 · P1 · M37 IDM: একই candle sweep + tap

```pine
// L1180-1181
if not na(z.idmLvl) and not z.idmSwept and low < z.idmLvl and low > z.top
    z.idmSwept := true
```

`low > z.top` শর্ত: inducement নেওয়া candle zone-এ ঢুকলে IDM✓ হয় না। বাস্তবে inducement low আর OB top-এর দূরত্ব 5m-এ কয়েক pip; একটি candle-ই দুটো করে — ICT-র textbook form। M37 (rank 43, সবচেয়ে উঁচু) সেই form-এ চুপ। আগের bar-এ sweep, পরের bar-এ tap হলে কাজ করে।

**Fix**: `and low > z.top` বাদ (bear side L1251-এ `high < z.bottom` বাদ)। idmLvl zone-এর উপরে বলে `low < idmLvl` যথেষ্ট। Token কমে।

### F7 · P1 · ZONE EDGE entry close-এর ভুল দিকে

```pine
// L3395-3397
if ePx == "ZONE EDGE" and zzE.kind != ""
    g.entry := isLong ? zzE.top : zzE.bottom
```

P0-B 50% rule confirm close zone-এর ভেতরে (mid–top) থাকতে দেয়। তখন long-এর entry = zone top > close: "limit" আসলে buy-stop, label বলে LIMIT @ zone edge, alert-এ সেই দাম। Operator limit বসালে fill হবে না বা তৎক্ষণাৎ market-এর চেয়ে খারাপ দামে।

**Fix**: `g.entry := isLong ? math.min(close, zzE.top) : math.max(close, zzE.bottom)`। CANDLE 50% একই: `isLong ? math.min(close, mid) : math.max(close, mid)` (strong bull candle-এ mid < close সবসময়, তাই এটা শুধু safety)।

### F8 · P1 · EQH/EQL pool দাম = গড়

L1394: `L.price := (L.price + price) * 0.5`। Stops থাকে **উঁচু** high-এর উপরে। tolerance 0.10 ATR, তাই পার্থক্য ছোট, কিন্তু sweep classification 1 tick-এও বদলায়: গড় ছাড়াল, উঁচুটা ছাড়াল না → `sweptHighQ` true → M10 / M45 / M41 arm হয় incomplete sweep-এ।
**Fix**: `L.price := isHigh ? math.max(L.price, price) : math.min(L.price, price)`।

### F9 · P1 · P0-B 50% rule arm bar-এ

`zMidB` (L2704) arm bar-এও লাগে। Deep pin bar — wick OB bottom ছুঁয়ে close 40%-এ — CONFIRMED mode-এ arm হয় না। কিন্তু CONFIRMED-এর পুরো ধারণা: reaction candle দুর্বল হোক, **confirm close** প্রমাণ। P0-B IMMEDIATE-এর জন্য লেখা হয়েছিল; CONFIRMED/MSS-এ confirm bar-এ (snapshot-এর বিরুদ্ধে) পরীক্ষা হলেই যথেষ্ট।
**Fix**: arm condition (L2732, L2740) থেকে `zMidB` সরানো: `zoneArmB = atBullZone and (sweep rule) and (fifty rule)` আলাদা বুল (২টি), `zoneOkBull` অপরিবর্তিত confirm bar-এর জন্য।

### F10 · P1 · Killzone: tap ভেতরে, confirm বাইরে

L3506: `not ft.sbSessOk ? 3`। London 02:00-05:00 NY। 5m-এ 04:50 tap, 05:05 confirm → reject 3। MSS mode-এ (window 12) আরও বেশি। Session-এর মধ্যে setup তৈরি হওয়াটাই গুরুত্বপূর্ণ, confirm candle-এর minute নয়।
**Fix**: Sx-এ `bool poiSessL/S`, arm-এ `sx.poiSessL := ft.sbSessOk`; `sessOkL = ft.sbSessOk or (poiConfL and sx.poiSessL)`; rejL-এ `not sessOkL ? 3`।

### F11 · P1 · 2-bar sweep ভুল candle পড়ে

L1466-1472: level-এর উপরে close, RUN নয় → `pend = 2`; পরের bar close নিচে → SWEEP flag **সেই bar-এ**। s10 (L2796)-র `cd.dnWickRatio ≥ 0.5` ও P0-E সেই দ্বিতীয় bar-এ; আসল sweep candle-এর wick দেখা হয় না। SL `low - buf` দ্বিতীয় bar-এর।
**Fix**: F2-র `math.min(low, low[1], low[2])` SL ঠিক করে। s10-র wick test-এ `math.max(cd.dnWickRatio, ctx.dnR1)` (ctx.dnR1 = আগের bar-এর ratio, L2382-এ ইতিমধ্যে আছে)।

### F12 · P2 · f_pathBlock শুধু zone

L3296-3310: comment বলে "zone or FVG", loop শুধু zones। Unmitigated opposing FVG entry আর TP1-এর মাঝে → blocker নয়। STRICT default-এ এটা ফাঁক।
**Fix**: f_nearestOpp-এর FVG loop কপি করে `hit := true` (~10 লাইন, function-এর ভেতরে)।

### F13 · P2 · CHoCH লেগের OB তৈরি হয় না

L1967: `if (bullBOS or bearBOS)` — OB শুধু BOS-এ। Sweep → CHoCH লেগের origin-এ যে OB (ICT reversal entry) থাকে, সেটা শুধু RCB হয়, তাও `rcbFibGate` পাশ করলে। M45 চায় BRK/OB, M68 zone/FVG। FVG থাকলে কাজ চলে; OB না থাকলে M45-এর আসল form হারায়।
**Fix**: condition `(bullBOS or bearBOS or bullCHoCH or bearCHoCH)`, `isBull = bullBOS or bullCHoCH`। Block অপরিবর্তিত; `oIdxIn = ctx.legIdx` CHoCH-এও সঠিক (L1128-1130)। KL scoring block-ও CHoCH-এ চলবে — গ্রহণযোগ্য। Token: condition-এ ~6।

### F14 · P2 · MSS window

Tooltip বলে MSS-এ window ~12, default 8। `poiWin = mssMode ? math.max(i_poiBars, 12) : i_poiBars` — L2721/2723-এ `i_poiBars` → `poiWin`।

### F15 · P2 · Consolidation-এ zone দ্বিতীয় touch

L1921-1927: cooldown 3 bar পর zone-এর ভেতরে থাকলেই `touches++` → 4-5 bar-এর grind-এ একই visit-এ `sweepReq`। CONFIRMED mode-এ দাম zone-এ থাকলে live slot (snapshot নয়) → zoneOkBull false। Fix: touch শুধু re-entry-তে — `low[1] > z.top` (bull) / `high[1] < z.bottom` (bear) শর্ত cooldown-এর জায়গায়।

### F16 · P2 · Identity suppression single-slot

L3571-3589: `lastIdent` একটাই। L → S → একই L 50 bar-এর মধ্যে → suppress হয় না। `lastIdentL/S` আলাদা করলে ঠিক।

### P0-E note (bug নয়)

`cd.dnWickRatio ≥ 0.5` হলে `min(open, close) ≥ low + 0.5·range` → close স্বতঃই upper half-এ। তাই `close >= (high+low)*0.5` (L2796) কিছুই যোগ করে না। P0-E আসলে শুধু 0.40 → 0.50 ছিল। কঠোর করতে চাইলে `close >= low + 0.6 * cd.rng` বা `cd.isBull`।

---

## ৪. "Entry valid" — operator checklist (বর্তমান build-এ)

Fix-গুলো আসার আগে chart-এ signal দেখে ঢোকার আগে এই ৭টি হাতে যাচাই:

1. **Label**: ▲▲/▲ (score ≥ 8), module M37 / M41 / M42 / M45 / M54 / M68 / M73 (tier 3-4)। `· M10` tier 2 হলে pool sweep — PD/PW/SES না হলে skip।
2. **Tooltip**: `TP1 … [structural]` — `[⚠ SYNTH]` হলে না। `⚠ opposing zone` থাকলে না (STRICT-এ আসার কথা নয়)। `⚠vs HTF/trend` থাকলে না।
3. **SWEEP✕ label** বা HTF SWEEP শেষ 10 bar-এ থাকতে হবে (F1-এর কারণে sweepReq zone-এ signal আসবেই না; আসলে তা sweep-ছাড়া fresh zone)।
4. **SL হাতে নামান**: লাল dashed SL line reaction/sweep candle-এর wick-এর উপরে হলে wick-এর নিচে + 0.15 ATR (F2/F3)। R:R আবার হিসাব; < 2R হলে skip।
5. **Entry দাম**: ZONE EDGE-এ নীল entry line close-এর উপরে (long) হলে limit বসাবেন না — candle 50% বা zone top-এর যেটা close-এর নিচে (F7)।
6. **HTF bias panel**: "HTF bias BULL" কিন্তু 1h chart-এ শেষ swing low close-এ ভেঙেছে (wicky candle) → bias stale (F5), panel বিশ্বাস না করে 1h-এ নিজে দেখুন।
7. **Panel "Last event"**: BOS-এর আগে যদি "BOS weak" এসে থাকে আর পরে বড় candle একই level ভেঙেছে কিন্তু BOS label আসেনি → F4; সেই leg-এর OB নেই, তাই OB-module signal আসবে না — FVG module (M41/M68) দেখুন।

---

## ৫. প্রয়োগের ক্রম (প্রতি compile একটি)

Build 100,256-token সীমায়; প্রতিটি fix function-এর ভেতরে বা ternary। ক্রম — প্রভাব / token:

| ধাপ | Fix | আনুমানিক token | কাটার দরকার হলে |
| --- | --- | --- | --- |
| 1 | F2 + F3 + F11 (f_stop refLo/refHi, slRefLo/Hi) | +60 | — |
| 2 | F1 (swL10/swH10 + Feat.swRecentL/S) | +50 | — |
| 3 | F4 (hiBroken reset ×2) | +20 | — |
| 4 | F6 (`low > z.top` বাদ) | −6 | — |
| 5 | F7 (math.min/max entry) | +12 | — |
| 6 | F5 (Sx.hPend) | +45 | — |
| 7 | F9, F10 (Sx.poiSessL/S, zoneArmB/S) | +60 | M44 / M47 / M48 |
| 8 | F8, F13, F14, F12 | +40 | M49 / M50 / M52 |
| 9 | F15, F16 | +30 | M53, M63 |

ধাপ 1-5 একসাথে ~+140 token; v8.4.0 cut-এর পর headroom অজানা (compile count user দেবে)। Version: v8.4.1, header-এ F-ID changelog।

---

## ৬. যা ঠিক আছে (পরিবর্তন নয়)

- FVG, zone, drawing, alert সব `barstate.isconfirmed`-গেটেড; HTF `[1]` + `lookahead_on` — repaint নেই।
- P0-A/P1-D state machine-এর arm-after-confirm ক্রম (L2731) সঠিক — একই bar-এ re-arm হয় না।
- f_sig-এর geometry gate (L3475), TP ladder, REAL/SYNTH provenance — operator-গ্রেড।
- P1-E continuation block, R2 counter-trend −1, M10 fresh-displacement no-fade — সঠিক নীতি।
- Min risk 20 tick: EURUSD 2 pip, XAUUSD $0.20, JPY 2 pip — spread-floor হিসেবে যথাযথ।
