# SMC / ICT / CRT Suite — ফরেনসিক পোস্টমর্টেম ও ইম্প্রুভমেন্ট প্ল্যান

**ফাইল:** `vesiont_01.txt` (Pine v6, 3254 লাইন, single-file build)
**অডিট তারিখ:** 2026-09-18
**দৃষ্টিভঙ্গি:** ৩০ বছরের অপারেটর/ফরেক্স ট্রেডার + কোড ফরেনসিক
**পড়ার ধরন:** পুরো ফাইল লাইন-বাই-লাইন পড়া হয়েছে, কোনো স্যাম্পলিং নয়

---

## ০. এক নজরে রায় (Executive verdict)

আর্কিটেকচার ভালো — layer L0→L7, feature-vector, এক বারে এক ইঞ্জিন, state একটা `Ctx`-এ, FIFO drawing cap। এটা আমি যত Pine SMC ইন্ডিকেটর দেখেছি তার শীর্ষ ৫%-এ পড়ে। কোডে পুরনো বাগ ফিক্সের কমেন্ট আছে, মানে আগে ডিবাগ হয়েছে।

কিন্তু **৫টা গুরুতর সমস্যা** আছে যেগুলো সিগন্যাল কোয়ালিটি সরাসরি নষ্ট করছে:

| # | সমস্যা | প্রভাব |
|---|--------|--------|
| **C1** | `movePhase` কার্যত সব সময় `RETRACEMENT` — extreme-maker কখনো reset হয় না | M06 এর ফিল্টার অকেজো, M07 ওয়ার্নিং মৃত, M23 বিকৃত |
| **C2** | FVG ডিটেকশন live (unconfirmed) bar-এ হয় → **repaint** | OB, zone, TP, score — সব নিচে repaint হয় |
| **C3** | Display toggle (`d_ob`, `d_rcb`, `d_rjb`, `d_qm`) zone **তৈরি**-ই বন্ধ করে দেয় | OB box অফ করলে M36/M37/M42/M45/M48 মরে যায় |
| **C4** | সর্বোচ্চ-স্কোর ক্যান্ডিডেট বাদ পড়লে (RR/score/gate fail) সেই বারে **২য় সেরা ক্যান্ডিডেট আর চান্স পায় না** | অনেক ভালো সেটআপ নীরবে হারায় |
| **C5** | `majorHigh`/`majorLow` স্টেল বা `na` থেকে যেতে পারে অনির্দিষ্টকাল | CHoCH কখনো ফায়ার না করা, বা প্রাচীন লেভেলে ফায়ার করা |

এর সাথে **১৪টা মিডিয়াম বাগ**, **একগুচ্ছ ডেড কোড** (৯টা অব্যবহৃত `Feat` ফিল্ড, `Sig.sb`/`Sig.grade`, `SESH`/`SESL` শাখা যার কোনো producer নেই), আর **২টা স্পেক-গ্যাপ** (Premium/Discount আর Session/Killzone ফিল্টার ডিক্লেয়ার করা আছে কিন্তু ইমপ্লিমেন্ট নেই)।

---

## ১. আর্কিটেকচার ফরেনসিক (যা ঠিক আছে)

এগুলো নষ্ট করবেন না:

1. **R1 — এক bar-এ প্রতিটা ইঞ্জিন একবার।** [vesiont_01.txt:1734-1770](vesiont_01.txt#L1734-L1770) orchestration ব্লক পরিষ্কার, লেয়ার অর্ডার ঠিক।
2. **R3 — সব mutable state `Ctx`/`Sx`-এ।** UDT-র 254-element লিমিট হিট করার পর `Sx` আলাদা করা — সঠিক সিদ্ধান্ত।
3. **Drawing budget হিসাব করা** এবং FIFO cap: labels 230/500, lines ~196/500, boxes 100/500, security 3/40। সব লিমিটের ভেতরে।
4. **`f_xb()` clamp** [vesiont_01.txt:873](vesiont_01.txt#L873) — `max_bars_back` overflow থেকে বাঁচায়। এটা বেশিরভাগ পাবলিক ইন্ডিকেটরে থাকে না।
5. **`f_moveStrength` offset guard** (`off >= 0 and off < 500`) — historical buffer error আটকায়।
6. **Real vs fake CHoCH** (`chochReal` = move-এ FVG আছে কিনা) — ICT-সঠিক।
7. **TP1 = অন্তত `minRR` দূরে সত্যিকারের opposite level** [vesiont_01.txt:2885-2895](vesiont_01.txt#L2885-L2895) — আগের "নিকটতম যেকোনো level" বাগের ফিক্স। এটাই expectancy বাঁচানো সিদ্ধান্ত।
8. **`f_stop` side sanity check** [vesiont_01.txt:2853-2856](vesiont_01.txt#L2853-L2856) — SL ভুল পাশে গেলে fallback।
9. **`i_sigGap` (signal spacing)** — এক swing-এ ১০টা সিগন্যাল আসা বন্ধ করে।
10. **Data-window diagnostics** [vesiont_01.txt:3249-3254](vesiont_01.txt#L3249-L3254) — invisible gate দেখার জন্য। খুব ভালো প্র্যাকটিস।

---

## ২. ক্রিটিক্যাল বাগ (C — এগুলো আগে ঠিক করুন)

### C1 · `movePhase` ভেঙে গেছে → `retrace` কার্যত সর্বদা true

**কোথায়:** [vesiont_01.txt:821-834](vesiont_01.txt#L821-L834) এবং [vesiont_01.txt:861](vesiont_01.txt#L861)

```pine
if na(cx.hiMakerHigh) or high >= cx.hiMakerHigh
    cx.hiMakerHigh := high          // শুধু বাড়ে, কখনো কমে না, কখনো reset হয় না
...
s.movePhase := (not na(prevHiMk) and close >= prevHiMk) or (not na(prevLoMk) and close <= prevLoMk) ? "IMPULSIVE" : "RETRACEMENT"
```

**ফরেনসিক:** `hiMakerHigh` monotonic increasing — এটা চার্টের **সর্বকালীন সর্বোচ্চ** হয়ে যায়। `loMakerLow` সর্বকালীন সর্বনিম্ন। তাই `close >= prevHiMk` মানে "close ≥ all-time high", যা প্রায় কখনো সত্য না। ফল: **`movePhase` স্থায়ীভাবে `RETRACEMENT`**।

**ডাউনস্ট্রিম ক্ষতি:**
- `retrace = st.movePhase == "RETRACEMENT"` [vesiont_01.txt:2126](vesiont_01.txt#L2126)
- **M06** (`s06 = ... and retrace and ...`) — ফিল্টারটা আর কিছুই ফিল্টার করে না, impulse-এর মধ্যেও ফায়ার করে
- **M07 warning** (`w07 = ... and not retrace`) — **সম্পূর্ণ মৃত**, কখনো ফায়ার করবে না
- **M23** (`s23 = ... and retrace`) — একই সমস্যা
- Info panel-এর "Move phase" row সবসময় RETRACEMENT দেখায় → ট্রেডার ভুল তথ্য পায়
- `pbValidUp`/`pbValidDn` (§3.5 pullback) একই maker-এর উপর দাঁড়ানো → downtrend-এ `hiMakerLow` প্রাচীন হয়ে যায়, PB detection দুর্বল
- Leg counters (`pinBullInLeg`, `dojiInLeg`) pbValid-এ reset হয় [vesiont_01.txt:1796](vesiont_01.txt#L1796) → reset কম হয় → counter ফুলে যায় → M04/M06 ভুল ট্রিগার

**ফিক্স:** maker কে **BOS/CHoCH-এ reset** করুন, অথবা lookback-bound করুন:

```pine
// f_structure এর ভেতরে, BOS/CHoCH handling এর পরে:
if s.bullBOS or s.bearBOS or s.bullCHoCH or s.bearCHoCH
    cx.hiMakerHigh := high
    cx.hiMakerLow  := low
    cx.hiMakerIdx  := bar_index
    cx.loMakerLow  := low
    cx.loMakerHigh := high
    cx.loMakerIdx  := bar_index
    cx.pbUpArmed   := true
    cx.pbDnArmed   := true
```

অথবা আরো সহজ ও সঠিক — movePhase-কে current leg-এর সাপেক্ষে মাপুন:

```pine
s.movePhase := cx.trend == "BULLISH" ? (close >= nz(cx.curHigh, close) ? "IMPULSIVE" : "RETRACEMENT") :
               cx.trend == "BEARISH" ? (close <= nz(cx.curLow, close) ? "IMPULSIVE" : "RETRACEMENT") : "RETRACEMENT"
```

---

### C2 · FVG live bar-এ ডিটেক্ট হয় → পুরো chain repaint করে

**কোথায়:** [vesiont_01.txt:876-890](vesiont_01.txt#L876-L890)

```pine
if bar_index > 2
    if low > high[2] and (low - high[2]) >= minH      // `low` = চলমান bar-এর live low
        g = Fvg.new(top = low, bottom = high[2], ...)
        box.new(...)                                   // box এখনই আঁকা হয়
```

**ফরেনসিক:** তৃতীয় candle এখনো বন্ধ হয়নি। তার `low` প্রতি tick-এ নামতে পারে → FVG-র `top` নড়ে, অথবা `low > high[2]` মিথ্যা হয়ে যায় → box অদৃশ্য। এটা classic repaint।

Pine রিয়েলটাইমে `var` state rollback করে, তাই array corrupt হবে না — কিন্তু **ট্রেডার যা দেখে তা bar close-এ বদলে যায়**। আর যেহেতু FVG থেকে আসে:
- `mv.fvgCount` → `mv.strong` → OB তৈরি/না-তৈরি
- `chochReal` (real vs fake CHoCH)
- `ft.atBullFvg`/`atBearFvg` → `reactBull`/`reactBear` → M41/M46/M49/M52/M55/M56/M68
- `f_nearestOpp` → **TP1 ও R:R**
- `f_conf` score

...তাই **একটা FVG repaint মানে সিগন্যাল, SL, TP, score — সব repaint**।

**ফিক্স:** detection-কে confirmed করুন, অথবা closed candle ব্যবহার করুন:

```pine
// অপশন A (recommended): এক bar দেরিতে, কিন্তু সৎ
if barstate.isconfirmed and bar_index > 2
    if low > high[2] and (low - high[2]) >= minH
        ...
```

অথবা offset shift করে `low[1] > high[3]` ব্যবহার করুন (তখন `g.idx = bar_index - 2`)। **অপশন A সহজ ও নিরাপদ** — বাকি সব ইঞ্জিন (`f_zones`-এর OB/RCB/RJB/QM) ইতিমধ্যেই `barstate.isconfirmed` gate করা, তাই FVG-ও করা উচিত ছিল। এটা একটা inconsistency।

একইভাবে চেক করুন: `f_liq`-এর `f_addLevel` unconfirmed bar-এ level বানায় (pivot-derived হওয়ায় কম ঝুঁকি, কিন্তু PDH/PDL rollover unconfirmed bar-এ হয়)।

---

### C3 · Display toggle detection বন্ধ করে দেয়

**কোথায়:** [vesiont_01.txt:1280](vesiont_01.txt#L1280), [vesiont_01.txt:1347](vesiont_01.txt#L1347), [vesiont_01.txt:1352](vesiont_01.txt#L1352), [vesiont_01.txt:1385](vesiont_01.txt#L1385)

```pine
if onOB            // = d_ob input
    ... OB zone তৈরির পুরো ব্লক ...
if onRcb and off >= 1 ...
    zr = f_zAdd(... "RCB" ...)
if onQm
    cx.qmBullPend := true
if onRjb and barstate.isconfirmed ...
    ... RJB তৈরি ...
```

**ফরেনসিক:** `d_ob` হলো একটা **"Show"** গ্রুপের toggle ("OB / S&D" দেখাবে কিনা)। কিন্তু এটা zone **তৈরি**-ই আটকায়। ফল:

| Toggle অফ করলে | যে সেটআপ মরে |
|---|---|
| `d_ob` | M36, M37, M42, M45, M48 (সব `zKind == "OB"` নির্ভর) + BRK চেইন (M33-এর একাংশ) |
| `d_rcb` | M39 |
| `d_rjb` | M40 |
| `d_qm` | M70 |

ট্রেডার চার্ট পরিষ্কার করতে box অফ করে, আর বুঝতেই পারে না যে সে ইঞ্জিনের অর্ধেক অফ করে দিল। একই রিপোতে অন্য ব্রাঞ্চে (`Indicator` branch, commit c19b5ce) ঠিক এই বাগটাই ফিক্স হয়েছে — "detection no longer gated by show* toggles"। এখানে regress করেছে বা port হয়নি।

**ফিক্স:** detection সবসময় চালান, শুধু `drawOn` প্যারামিটারে toggle পাঠান (যেটা SR zone-এ ইতিমধ্যেই সঠিকভাবে করা আছে — [vesiont_01.txt:1253](vesiont_01.txt#L1253)):

```pine
// আগে:  if onOB
// পরে:   (কোনো gate নেই — সবসময় detect)
...
z = f_zAdd(cf, cx, v, aV, "OB", isBull, zTop, zBot, obIdx, onOB and (hpNow or not cf.obHpOnly))
```

RCB/RJB/QM-এও একই প্যাটার্ন: `f_zAdd(..., drawOn = onRcb)` ইত্যাদি।

---

### C4 · সেরা ক্যান্ডিডেট বাদ পড়লে ২য় সেরা চান্স পায় না

**কোথায়:** [vesiont_01.txt:2266-2268](vesiont_01.txt#L2266-L2268) (`f_pick`), [vesiont_01.txt:2905](vesiont_01.txt#L2905), [vesiont_01.txt:2912-2931](vesiont_01.txt#L2912-L2931)

**ফরেনসিক:** `f_pick` চেইন প্রতি সাইডে **একটাই** বিজয়ী রাখে (`nL`, `scL`)। তারপর সেই একজনের উপর তিনটা ফিল্টার চলে:

1. `ft.gateUp > 0` — HTF/trend gate
2. `okRR` — `f_nearestOpp` এ `minRR` দূরে সত্যিকারের target আছে কিনা
3. `sigL.score < i_minScore` — confluence score

যেকোনোটা fail করলে `sigL = Sig.new()` — **পুরো সাইড খালি**। অথচ হয়তো একই bar-এ score 5-এর M39 ছিল যার target ঠিকই আছে, কিন্তু score 7-এর M37 (যার কোনো real TP নেই) তাকে চেইনেই হারিয়ে দিয়েছে।

একই সমস্যা both-side conflict-এ [vesiont_01.txt:2941-2947](vesiont_01.txt#L2941-L2947) — হারা সাইড সম্পূর্ণ মুছে যায়।

**প্রভাবের মাপ:** `i_rrReal = true` (default) এবং `i_minRR = 2.0` — মানে TP1-কে ২R দূরে একটা opposite zone/FVG/liquidity লাগবে। রেঞ্জিং মার্কেটে এটা প্রায়ই পাওয়া যায় না → শীর্ষ ক্যান্ডিডেট বাদ → সেই বারে কিছুই আসে না, যদিও অন্য সেটআপ valid ছিল।

**ফিক্স (দুটো অপশন):**

**A — Top-3 ক্যান্ডিডেট রাখুন** (পরিষ্কার, কিন্তু চেইন রিফ্যাক্টর লাগে): `f_pick`-কে ৩-slot ranking-এ বদলান, তারপর প্রথম যেটা তিনটা ফিল্টার পাস করে সেটা নিন।

**B — Fallback re-scan** (কম ইনভেসিভ): ফিল্টার fail করলে দ্বিতীয় চেইন চালান যেখানে বিজয়ীটাকে বাদ দেওয়া হয়। `f_pick`-এ একটা `exclude` প্যারাম যোগ করুন:

```pine
f_pick2(cond, name, sc, note, curN, curS, curNote, excl) =>
    take = cond and sc > curS and name != excl
    [take ? name : curN, take ? sc : curS, take ? note : curNote]
```

Pine-এ ৬০+ লাইনের চেইন দুবার লেখা ব্যয়বহুল (`CE10295` main-scope লিমিট ইতিমধ্যেই hit হয়েছে, কমেন্টে লেখা আছে)। তাই **অপশন A-ই সঠিক পথ**: candidate list-কে array-তে নিন।

**সরল মধ্যপথ (এখনই করার মতো):** `i_rrReal` fail হলে synthetic target দিন কিন্তু signal-কে `· ⚠no real TP` note + score −1 দিয়ে দেখান, পুরো লুকিয়ে ফেলার বদলে। ট্রেডার নিজেই সিদ্ধান্ত নেবে।

> **সংশোধনী (v8.2.0 ইমপ্লিমেন্টের সময় পাওয়া):** উপরের C4 আমি বড় করে দেখিয়েছি। তিনটা ফিল্টারের কোনোটাই setup-নির্দিষ্ট নয় —
> `f_conf()` শুধু `Feat` + direction পড়ে, `f_gate()` শুধু bias + trend পড়ে, আর `f_stop()`/`f_nearestOpp()` শুধু `close` + direction + feature পড়ে।
> মানে শীর্ষ ক্যান্ডিডেট যদি fail করে, **ওই সাইডের বাকি সব ক্যান্ডিডেটও একই কারণে fail করত** — ২য়-সেরা slot রাখলেও লাভ হতো না।
> একমাত্র আসল ব্যতিক্রম: **M10 `RETEST`/`BOTH` মোডে entry কে swept level-এ সরায়**, তাই তার risk আলাদা হয়।
> v8.2.0-এ সেটাই ফিক্স করা হয়েছে — RR fail করলে entry `close`-এ ফিরে গিয়ে আবার মাপে, signal ফেলে দেয় না।
> ৯০টা `f_pick` call refactor করার দরকার নেই। যা এখনো খোলা আছে তা হলো **M13** (tie-তে declaration order জেতে) — সেটা priority-tier refactor।

---

### C5 · `majorHigh` / `majorLow` স্টেল বা কখনো সেট না হওয়া

**কোথায়:** [vesiont_01.txt:775-788](vesiont_01.txt#L775-L788)

```pine
if s.bearBOS
    if not na(cx.prevHigh) and cx.curHigh < cx.prevHigh    // ← শুধু LH হলে
        cx.majorHigh := cx.curHigh
    cx.trend := "BEARISH"
...
s.bullCHoCH := cx.trend == "BEARISH" and not na(cx.majorHigh) and close > cx.majorHigh
```

**ফরেনসিক:** `majorHigh` শুধু তখনই আপডেট হয় যখন bearBOS-এর সময় `curHigh < prevHigh` (lower high)। কিন্তু:

- **প্রথম bearBOS যদি HH থেকে হয়** (curHigh ≥ prevHigh — যেমন uptrend-এর টপ থেকে প্রথম ভাঙা), `majorHigh` `na` থেকে যায় → **`bullCHoCH` কখনো ফায়ার করতে পারবে না** যতক্ষণ না একটা LH-সহ bearBOS আসে।
- একটা দীর্ঘ downtrend-এ যদি ধারাবাহিক LH না হয় (consolidation), `majorHigh` **অনেক পুরনো লেভেলে আটকে থাকে** → CHoCH দেরিতে/ভুল লেভেলে ফায়ার করে।
- CHoCH লাইন আঁকা হয় `ctx.majorHighIdx` দিয়ে [vesiont_01.txt:3110-3113](vesiont_01.txt#L3110-L3113) — সেই stale index।

আর **`majorHigh`/`majorLow` কখনো CHoCH-এর সময় আপডেট হয় না**। `bullCHoCH` হলে trend BULLISH হয়, কিন্তু `majorLow` পুরনো থেকে যায় → পরের `bearCHoCH` ভুল (অনেক নিচের) লেভেল দেখে।

**ফিক্স:**

```pine
if s.bearBOS
    // LH না হলেও major কে অন্তত curHigh এ সেট করুন — CHoCH কে reference লাগে
    cx.majorHigh    := na(cx.prevHigh) or cx.curHigh < cx.prevHigh ? cx.curHigh : math.max(cx.curHigh, nz(cx.majorHigh, cx.curHigh))
    cx.majorHighIdx := cx.curHighIdx
    cx.trend := "BEARISH"

// CHoCH এর পরেও major re-anchor করুন:
if s.bullCHoCH
    cx.trend     := "BULLISH"
    cx.majorLow  := cx.curLow          // নতুন trend এর invalidation level
    cx.majorLowIdx := cx.curLowIdx
if s.bearCHoCH
    cx.trend      := "BEARISH"
    cx.majorHigh  := cx.curHigh
    cx.majorHighIdx := cx.curHighIdx
```

আর `ctx.majorLow` SL-এও ব্যবহৃত হয় [vesiont_01.txt:2848](vesiont_01.txt#L2848) — stale major মানে **ভুল stop distance**, শুধু `maxSLATR` clamp তাকে আটকায়।

---

## ৩. মিডিয়াম বাগ (M — দ্বিতীয় রাউন্ড)

### M1 · `bullBOS` ও `bearBOS` একই bar-এ দুটোই true হতে পারে
[vesiont_01.txt:767-768](vesiont_01.txt#L767-L768) — একটা বড় outside candle `close > curHigh` **এবং** `close < curLow` করতে পারে না (mutually exclusive by price), কিন্তু `curHigh` ও `curLow` দুটোই যদি close-এর একই পাশে থাকে (gap-এর পরে), সম্ভব। তখন [vesiont_01.txt:781-786](vesiont_01.txt#L781-L786)-এ bull block পরে চলায় trend BULLISH হয়ে যায়, আর `f_zones`-এ [vesiont_01.txt:1260](vesiont_01.txt#L1260) `isBull = bullBOS` → bull ধরে নেয়। M41-ও দুই দিকে arm করে।
**ফিক্স:** একটা tie-breaker যোগ করুন — কোন level বেশি দূরে ভাঙল (displacement) সেটা নিন, বা `bodyRatio`-র দিক ধরুন।

### M2 · `hiBroken` / `loBroken` CHoCH-এ reset হয় না
[vesiont_01.txt:771-774](vesiont_01.txt#L771-L774) — CHoCH trend flip করে কিন্তু break flag ছাড়ায় না। একটা bullCHoCH-এর পরে `hiBroken` এখনো `true` থাকতে পারে → পরের bullBOS মিস হবে যতক্ষণ না নতুন pivot high confirm হয় (swingLen=5 → ৫+ bar দেরি)।

### M3 · `i_obHpOnly` শুধু আঁকা আটকায়, zone আটকায় না
[vesiont_01.txt:1336](vesiont_01.txt#L1336) — `f_zAdd(..., hpNow or not cf.obHpOnly)` → `drawOn` প্যারামে যায়। zone তৈরি হয়ই, তাই setup gate-ও চলে। ইনপুট label বলছে "high-probability only" — ট্রেডার ভাববে non-HP OB উপেক্ষা হচ্ছে, কিন্তু M36/M42 ঠিকই সেগুলোতে ট্রিগার করবে। **আচরণ আর label-এর mismatch।**
**ফিক্স:** hpNow false হলে zone-ই তৈরি করবেন না (যখন obHpOnly on), অথবা label বদলে "OB: শুধু HP গুলো দেখাও" করুন।

### M4 · `f_liq`: unresolved level-এর age-based cleanup নেই
[vesiont_01.txt:1058-1064](vesiont_01.txt#L1058-L1064) — শুধু `L.done` হলে বয়স দেখে মোছা হয়। Unresolved level শুধু `while size > maxLevels` → `array.shift` দিয়ে যায় [vesiont_01.txt:1164](vesiont_01.txt#L1164)। `shift` **সবচেয়ে পুরনো insert** মোছে — যা হতে পারে আজকের PDH (কারণ PDH দিনের শুরুতে ঢোকে)। গুরুত্বপূর্ণ level হারানোর ঝুঁকি।
**ফিক্স:** eviction-এ priority দিন — `touches`, `kind` (PDH/PWH আগে বাঁচাও), close থেকে দূরত্ব।

### M5 · `hiddenSSL` / `hiddenBSL` প্রথম bar-গুলোয় ফলস
[vesiont_01.txt:1171-1182](vesiont_01.txt#L1171-L1182) — `hidS = true` দিয়ে শুরু; `low[k] < low[k+1]` যখন `low[k+1]` = `na`, তুলনা false → flag টেকে। প্রথম `hiddenN` bar-এ ভুল signal।
**ফিক্স:** `if bar_index < cf.hiddenN + 1` হলে দুটোই false করুন।

### M6 · একই সমস্যা wick-dominance লুপে
[vesiont_01.txt:1850-1856](vesiont_01.txt#L1850-L1856) — `for k = 0 to 7` `high[k]` na হলে subtraction na, `dw > uw` false → count কম → `wickLowerDom` false। এখানে ফলস-negative, কম ক্ষতিকর, তবু bar_index guard দিন।

### M7 · `ft.sweepCHoCHBull/Bear` নামে CHoCH, কাজে BOS
[vesiont_01.txt:1918-1919](vesiont_01.txt#L1918-L1919) — `st.bullBOS` ব্যবহার করে, CHoCH না। কোডেই কমেন্টে স্বীকার করা আছে [vesiont_01.txt:3028](vesiont_01.txt#L3028)। M45-এর ডকুমেন্টেড আচরণ ("Sweep-based CHoCH retest") আর আসল আচরণ ("sweep + BOS retest") আলাদা। ট্রেডার ভুল জিনিস আশা করবে।
**ফিক্স:** হয় নাম বদলান (`sweepBOSBull`), নয়তো আসল CHoCH দিয়ে করুন (`st.bullCHoCH`) — যেটা ট্রেডিং-লজিকে বেশি ঠিক, কারণ sweep + CHoCH = reversal, sweep + BOS = continuation।

### M8 · `ft.incomplete` লেখা হয়, কখনো পড়া হয় না
[vesiont_01.txt:2921](vesiont_01.txt#L2921), [vesiont_01.txt:2931](vesiont_01.txt#L2931) — "4-factor" fail হলে শুধু note-এ text যোগ হয়, signal দেখানো বন্ধ হয় না, score কমেও না। Flag টা কেউ পড়ে না।
**ফিক্স:** হয় score −1 করুন, নয়তো panel/label-এ visible marker দিন, নয়তো flag টা মুছে ফেলুন।

### M9 · `gateUp`/`gateDn` BOS bar-এ trivially পাস করে
[vesiont_01.txt:1769-1770](vesiont_01.txt#L1769-L1770) — `st.trend` ইতিমধ্যেই এই বারের নিজের BOS/CHoCH দিয়ে flip হয়ে গেছে ([vesiont_01.txt:785](vesiont_01.txt#L785))। তাই breakout-এর দিকে trend filter সবসময় align দেখাবে। `preTrend` ভেরিয়েবল [vesiont_01.txt:1733](vesiont_01.txt#L1733) ইতিমধ্যে ধরে রাখা আছে (CISD label-এর জন্য ব্যবহৃত) — gate-এও সেটাই লাগবে, অন্তত breakout-continuation সেটআপের জন্য।

### M10 · `ctx.arrivalMixed` স্টেল থেকে যায়
[vesiont_01.txt:2132](vesiont_01.txt#L2132) — `pbOk` `ctx.arrivalMixed >= 0.35` দেখে, কিন্তু `arrivalMixed` শুধু arrival event-এ আপডেট হয় ([vesiont_01.txt:1784](vesiont_01.txt#L1784))। ১০ bar-পর zoneTouch false হয়ে গেলেও পুরনো মান রয়ে যায়। `ft.arrivalStrong` ঠিকভাবে ১০-bar window দিয়ে gate করা, কিন্তু `ctx.arrivalMixed` সরাসরি পড়া হয় — inconsistent।
**ফিক্স:** `arrivalMixed`-কেও `Feat`-এ তুলুন এবং একই window gate দিন।

### M11 · Zone `broken` cleanup ও zone flip-এ `nearMiss`/`idmLvl` reset হয় না
[vesiont_01.txt:1451-1456](vesiont_01.txt#L1451-L1456) — SR zone flip হলে `touches`/`sweepReq` reset হয় কিন্তু `idmLvl`, `idmSwept`, `nearMiss`, `nearSwept`, `fiftyHit` আগের দিকের মান নিয়ে থাকে। Flipped support-এ পুরনো bearish IDM level দিয়ে `zIdm` true হবে → **M37 ভুয়া ট্রিগার** (M37-এর score 7+, সবচেয়ে উঁচু!)।
**ফিক্স:** flip ও PROP re-arm ব্লকে সব directional state clear করুন:
```pine
z.idmLvl := na, z.idmSwept := false, z.nearMiss := na, z.nearSwept := false, z.fiftyHit := false
```
(PROP ব্লক [vesiont_01.txt:1494-1504](vesiont_01.txt#L1494-L1504) `fiftyHit` reset করে কিন্তু `idm`/`nearMiss` করে না — একই ফাঁক।)

### M12 · `ctx.rangeBrkDir` কখনো clear হয় না
[vesiont_01.txt:1887-1892](vesiont_01.txt#L1887-L1892) — একবার সেট হলে চিরকাল। `recentHi` (armBars window) রক্ষা করে, কিন্তু `s50`/`s53` `ctx.rangeBrkDir == -1`-ও পড়ে আর `recentHi` আলাদা শর্ত — দুটো একসাথে মিললেই চলবে, তাই ঠিক আছে। তবু নতুন range শুরু হলে dir clear করা উচিত (`if ft.inRange and not ctx.inRangePrev → rangeBrkDir := 0`)।

### M13 · `f_pick` strict `>` — tie-তে চেইনের আগের জন জেতে
[vesiont_01.txt:2267](vesiont_01.txt#L2267) — সমান score হলে **চেইনে আগে থাকা** সেটআপ জেতে। চেইন অর্ডার M01→M02→...→M73, মানে **গুণগত ranking নয়, declaration order**। M39 (score 5) আর M63 (score 5) সমান হলে M39 জেতে শুধু কারণ সে আগে declare করা।
**ফিক্স:** base score-এ tier যোগ করুন (যেমন liquidity-confirmed সেটআপ +0.5 সমতুল্য), বা ইচ্ছাকৃত priority order ডকুমেন্ট করুন।

### M14 · Trendline: pivot-anchor পুরনো হলে slope বিকৃত
[vesiont_01.txt:2046-2049](vesiont_01.txt#L2046-L2049) — `tlSx1` চিরকাল থাকে যতক্ষণ নতুন HL না আসে। ৩০০ bar আগের দুই pivot থেকে extrapolate করলে বর্তমান দাম থেকে বহু দূরে চলে যায়, কিন্তু `tlSupValid` তবু true (touch ≥ 2) → `ft.atTLsup` কখনো true হবে না (ভালো), কিন্তু M64 line আঁকা চলতেই থাকে → চার্টে বিভ্রান্তিকর লাইন।
**ফিক্স:** anchor-এর বয়স cap দিন (`bar_index - sx.tlSx1 <= 200`) এবং দাম থেকে দূরত্ব cap (`math.abs(close - tlS) <= atrV * 10`)।

---

## ৪. ডেড কোড ও অসম্পূর্ণ ফিচার

গ্রেপ করে নিশ্চিত: নিচের প্রতিটা identifier ফাইলে **ঠিক একবার** আছে (শুধু declaration), অর্থাৎ কখনো লেখা বা পড়া হয় না:

| Identifier | অবস্থান | কী বলে দেয় |
|---|---|---|
| `Feat.sessName`, `Feat.sbSessOk` | [vesiont_01.txt:504-505](vesiont_01.txt#L504-L505) | **Session / Killzone ফিল্টার পরিকল্পিত ছিল, কখনো লেখা হয়নি** |
| `Feat.pdPct`, `inDiscount`, `inPremium` | [vesiont_01.txt:506-508](vesiont_01.txt#L506-L508) | **Premium/Discount (Fib 50% array) ইমপ্লিমেন্ট নেই** |
| `Feat.dispScore`, `Feat.dispDir` | [vesiont_01.txt:511-512](vesiont_01.txt#L511-L512) | Displacement scoring পরিকল্পিত, হয়নি |
| `Sig.sb`, `Sig.grade` | [vesiont_01.txt:527-528](vesiont_01.txt#L527-L528) | "SB engine" (কমেন্টে উল্লেখ, [vesiont_01.txt:1140](vesiont_01.txt#L1140)) কখনো বানানো হয়নি |
| `"SESH"` / `"SESL"` kind | [vesiont_01.txt:1142](vesiont_01.txt#L1142) | এই kind-এর level কেউ তৈরি করে না → শাখা মৃত |
| `Cndl.dualTrap` | [vesiont_01.txt:128](vesiont_01.txt#L128), সেট [vesiont_01.txt:756](vesiont_01.txt#L756) | সেট হয়, কখনো পড়া হয় না |
| `Zone.propBar` | সেট [vesiont_01.txt:1496](vesiont_01.txt#L1496) | কখনো পড়া হয় না |
| `Sx.dtTop` | সেট [vesiont_01.txt:2541](vesiont_01.txt#L2541), [vesiont_01.txt:2546](vesiont_01.txt#L2546) | M58-এ TP হিসেবে লাগত, ব্যবহার হয়নি |
| `Feat.lastMoveFvg` | সেট [vesiont_01.txt:1761](vesiont_01.txt#L1761) | কখনো পড়া হয় না |
| `f_gradeSz()` | [vesiont_01.txt:2997](vesiont_01.txt#L2997) | কখনো কল হয় না (কমেন্টে ব্যাখ্যা আছে কেন) |

**কেন এটা গুরুত্বপূর্ণ:** Premium/Discount আর Session filter — এই দুটোই ICT-র সবচেয়ে বড় win-rate ফিল্টার। দুটোই টাইপে declare করা আছে মানে ডিজাইনার জানত এগুলো দরকার। এগুলো যোগ করলে সবচেয়ে বেশি লাভ হবে (§৬ দেখুন)।

---

## ৫. পরিমাণগত ঝুঁকি বিশ্লেষণ (অপারেটর দৃষ্টিতে)

### ৫.১ সেটআপ সংখ্যা vs সিগন্যাল কোয়ালিটি

৭৩টা মডিউল, default-এ ~৩০টা চালু। এক bar-এ ৬০+ boolean evaluate হয়ে একটা বিজয়ী বের হয়। সমস্যা:

- **Score inflation:** base score + `liqBonus` + `m20` + `hpB` + `zNearSwept` — M42 সর্বোচ্চ `6+2+1 = 9` পেতে পারে, M37 `7+1+1 = 9`। কিন্তু চূড়ান্ত display score আসে `f_conf()` থেকে ([vesiont_01.txt:2902](vesiont_01.txt#L2902)) — **base score শুধু ক্যান্ডিডেট বাছে, দেখানো score সম্পূর্ণ আলাদা হিসাব**। এটা বিভ্রান্তিকর: M37 (base 7) জিতে আসে কিন্তু `f_conf` তাকে 3 দিলে "B" grade দেখাবে। দুটো scoring system একসাথে থাকা মানে কোনোটাই calibrated না।
- **`f_conf` range:** সর্বোচ্চ `1+1+1+1+1+1+1+1+1 = 9`, সর্বনিম্ন `1-2-2-1 = -4`। `i_minScore = 3` default → অনেকটাই permissive।

**সুপারিশ:** একটা scoring system রাখুন। `f_conf`-কেই authority করুন (কমেন্টে তাই লেখা), আর base score-কে শুধু tie-break priority হিসেবে ব্যবহার করুন (পূর্ণসংখ্যা priority tier, score নয়)।

### ৫.২ Repaint ও intrabar ফায়ারিং

- `sigL`/`sigS` প্রতি tick-এ রিবিল্ড হয় ([vesiont_01.txt:2910-2911](vesiont_01.txt#L2910-L2911))
- label, trade line, `alert()` — সব `barstate.isconfirmed` gate করা ✓ (ভালো)
- কিন্তু **info panel** `barstate.islast`-এ চলে → intrabar মান দেখায়
- `plot(sigL.score, ...)` data window-এ → intrabar

মোটামুটি ঠিক আছে, তবে C2 (FVG repaint) ঠিক না করলে confirmed মানগুলোও historical vs realtime-এ ভিন্ন হবে।

### ৫.৩ Computational budget

প্রতি bar-এ লুপ: zones ≤60 + fvgs ≤40 + levels ≤30 + hidden 3 + wickDom 8 + brkTouch 30 (event) + brkTime 10 (event) + moveStrength ≤150 (event) + f_nearestOpp (zones+fvgs = 100, ২বার) + f_nearestLiq (30, ৩বার)।

Signal bar-এ worst case ~600 iteration। Non-signal bar ~150। TradingView-র লিমিটে ঠিক আছে, কিন্তু **`f_nearestOpp`/`f_nearestLiq` signal প্রতি ৫ বার কল হয়** — cache করা যায়।

---

## ৬. ইম্প্রুভমেন্ট প্ল্যান — অগ্রাধিকার ক্রমে

### ধাপ ১ · Correctness (আগে এগুলো, নতুন কিছু না)

| ক্রম | কাজ | আনুমানিক প্রভাব |
|---|---|---|
| 1 | **C2** FVG detection-এ `barstate.isconfirmed` | repaint শেষ — সবচেয়ে বড় একক ফিক্স |
| 2 | **C1** extreme-maker reset / movePhase পুনর্লিখন | M06/M07/M23 কাজ করা শুরু করবে, panel সত্য বলবে |
| 3 | **C3** detection-কে display toggle থেকে আলাদা করা | user-এর চার্ট পরিষ্কার করা আর ইঞ্জিন ভাঙা এক জিনিস না |
| 4 | **C5** major H/L re-anchor | CHoCH নির্ভরযোগ্য হবে, SL ঠিক হবে |
| 5 | **M11** flip/PROP-এ directional state clear | M37 (সর্বোচ্চ score সেটআপ) এর ভুয়া ট্রিগার বন্ধ |
| 6 | **C4** candidate fallback | হারানো ভালো সেটআপ ফিরে আসবে |
| 7 | M1, M2, M5, M6, M8, M10, M12 | ছোট ছোট, একসাথে ১ কমিটে |

### ধাপ ২ · অসম্পূর্ণ ফিচার শেষ করা (সবচেয়ে বেশি edge এখানে)

**২.১ Premium / Discount array (ICT-র সবচেয়ে বড় ফিল্টার)**

টাইপে জায়গা আছে (`pdPct`, `inPremium`, `inDiscount`)। বর্তমান dealing range = `majorLow..majorHigh`:

```pine
// orchestration এ, f_structure এর পরে:
if not na(ctx.majorHigh) and not na(ctx.majorLow) and ctx.majorHigh > ctx.majorLow
    ft.pdPct := math.max(0.0, math.min(1.0, (close - ctx.majorLow) / (ctx.majorHigh - ctx.majorLow)))
    ft.inDiscount := ft.pdPct <= 0.5
    ft.inPremium  := ft.pdPct >= 0.5
else
    ft.pdPct := 0.5
    ft.inDiscount := true
    ft.inPremium  := true        // gate না থাকলে block করবেন না
```

তারপর `f_conf`-এ:
```pine
sc += (isLong and fv.inDiscount) or (not isLong and fv.inPremium) ? 1 : 0
sc -= (isLong and fv.pdPct > 0.75) or (not isLong and fv.pdPct < 0.25) ? 1 : 0
```
আর একটা ইনপুট: `"PD array: শুধু discount এ long / premium এ short"` (default off → তারপর backtest করে on)।

**২.২ Session / Killzone ফিল্টার**

```pine
i_ssn = input.bool(false, "শুধু killzone এ সিগন্যাল", group = gX)
i_ssnAsia   = input.session("0000-0800", "Asia",   group = gX)
i_ssnLondon = input.session("0700-1000", "London", group = gX)
i_ssnNY     = input.session("1200-1500", "NY",     group = gX)
inAsia = not na(time(timeframe.period, i_ssnAsia))
inLon  = not na(time(timeframe.period, i_ssnLondon))
inNY   = not na(time(timeframe.period, i_ssnNY))
ft.sessName  := inLon ? "London" : inNY ? "NY" : inAsia ? "Asia" : ""
ft.sbSessOk  := not i_ssn or ft.sessName != ""
```
`f_conf`-এ `sc += fv.sessName == "London" or fv.sessName == "NY" ? 1 : 0`, আর signal gate-এ `and ft.sbSessOk`।

**২.৩ Session high/low level (SESH/SESL)** — শাখা ইতিমধ্যেই [vesiont_01.txt:1142](vesiont_01.txt#L1142)-এ আছে, শুধু producer নেই:
```pine
// Asia session এর high/low, London open এ level হিসেবে যোগ করুন
var float asiaHi = na
var float asiaLo = na
if inAsia
    asiaHi := na(asiaHi) ? high : math.max(asiaHi, high)
    asiaLo := na(asiaLo) ? low  : math.min(asiaLo, low)
if inLon and not inLon[1] and not na(asiaHi)
    f_addLevel(cfg, ctx, vis, atrV, asiaHi, bar_index, true,  "SESH", false, d_liq)
    f_addLevel(cfg, ctx, vis, atrV, asiaLo, bar_index, false, "SESL", false, d_liq)
    asiaHi := na
    asiaLo := na
```
Asia range sweep → London reversal — সবচেয়ে বেশি repeatable ICT প্যাটার্ন। ইঞ্জিনে ৯০% অবকাঠামো আগেই আছে।

### ধাপ ৩ · ভ্যালিডেশন (এটা ছাড়া ধাপ ১/২ অন্ধ কাজ)

**৩.১ Strategy port (আলাদা ফাইল, ইন্ডিকেটর নষ্ট করবেন না)**

`indicator()` → `strategy()` সহ একটা প্যারালাল বিল্ড বানান, শেষ ~৩০ লাইন বদলে:
```pine
if hasL and barstate.isconfirmed
    strategy.entry("L", strategy.long)
    strategy.exit("Lx", "L", stop = sigL.sl, limit = sigL.tp1)
```
এতে TradingView Strategy Tester-এ **প্রতি সেটআপের আসল win rate ও expectancy** পাবেন। এখন পর্যন্ত ৭৩টা মডিউলের কোনোটার পরিসংখ্যান নেই — মানে score 7 বনাম score 3 কোনো প্রমাণের উপর দাঁড়ানো নয়, শুধু মতামত।

**৩.২ Per-module counter (ইন্ডিকেটরেই, সস্তা)**

```pine
var array<int> modHit = array.new<int>(80, 0)
// f_pick এর বিজয়ী নাম থেকে index বের করে count করুন, অথবা প্রতিটা sXX এর জন্য:
var int cM37 = 0
if s37 or s37b
    cM37 += 1
plot(cM37, "M37 hits", display = display.data_window)
```
কোন মডিউল আসলে ফায়ার করে আর কোনটা মৃত কোড — এক সপ্তাহ চার্টে রাখলেই বেরিয়ে যাবে। আমার সন্দেহ: **M55, M56, M57, M60, M61, M66, M71 প্রায় কখনো ফায়ার করে না** (খুব সংকীর্ণ multi-stage শর্ত, latch timeout ছোট)। ওগুলো হয় ঠিক করুন, নয় বাদ দিন।

**৩.৩ Forward-test প্রোটোকল**

১. C-বাগ ফিক্স করে একটা symbol/TF-এ (যেমন XAUUSD 15m) `i_setMode = "Core only"` দিয়ে চালান
২. ৫০টা সিগন্যাল screenshot + outcome নোট করুন (spreadsheet: module, score, grade, RR, result)
৩. যেসব মডিউল ১০+ sample-এ <৪০% win → ডিফল্ট off
৪. `f_conf`-এর weight গুলো ওই ডেটা দিয়ে re-fit করুন

### ধাপ ৪ · আর্কিটেকচার পরিষ্কার

1. **ডেড কোড মুছুন** (§৪-এর তালিকা) — অথবা `TODO` কমেন্ট দিয়ে স্পষ্ট করুন কী বাকি। অব্যবহৃত টাইপ-ফিল্ড UDT-র 254-element budget খায়, যা ইতিমধ্যেই hit হয়েছে।
2. **Scoring একীভূত করুন** (§৫.১) — base score → priority tier, `f_conf` → একমাত্র score।
3. **`f_nearestOpp`/`f_nearestLiq` cache করুন** — signal-প্রতি ৫ কল → ২ কল।
4. **Candidate chain-কে array করুন** — C4-এর সঠিক ফিক্স, আর `CE10295` main-scope pressure-ও কমবে।
5. **Version স্ট্যাম্প ও changelog** — ফাইলের নাম `vesiont_01.txt` (টাইপো সহ)। `SMC_Suite_v8.x.pine` করুন, হেডারে version + spec hash রাখুন। রিপোর অন্য ব্রাঞ্চে ইতিমধ্যে `releases/` ফোল্ডার আছে — একই ডিসিপ্লিন এখানেও আনুন (C3 বাগটা সম্ভবত port মিস হওয়ার ফল)।

---

## ৭. যা করবেন না

- **নতুন মডিউল যোগ করবেন না** যতক্ষণ C1–C5 ফিক্স আর ধাপ ৩-এর ভ্যালিডেশন না হয়। ৭৩টা সেটআপের মধ্যে কতগুলো আসলে লাভজনক তা কেউ জানে না — ৭৪তম যোগ করলে জানার সম্ভাবনা আরো কমবে।
- **`lookahead_on` সরাবেন না।** [vesiont_01.txt:1650](vesiont_01.txt#L1650), [vesiont_01.txt:1718-1719](vesiont_01.txt#L1718-L1719)-এ `[1]`/`[2]` offset-এর সাথে এটা **সঠিক** non-repainting ইডিয়ম। এটা বদলালে HTF ডেটা ১ HTF-bar দেরি করবে।
- **`max_bars_back = 500` বাড়াবেন না** বিনা কারণে — `f_xb` clamp আর `off < 500` guard ওই সংখ্যার উপর hard-coded। বাড়ালে দুটোই একসাথে বদলাতে হবে।
- **`i_minRR` কমিয়ে সিগন্যাল বাড়াবেন না।** কোডের কমেন্ট ([vesiont_01.txt:2885-2887](vesiont_01.txt#L2885-L2887)) ঠিক বলেছে: নিকটতম target নিলে average winner ~1R হয় আর প্রতিটা loser 1R — ৫০%-এর নিচে win rate-এ গাণিতিকভাবে negative expectancy। C4-এর ফিক্সই সঠিক উত্তর, `minRR` কমানো নয়।

---

## ৮. চেকলিস্ট (কমিট-ধারা)

```
[ ] commit 1  fix: FVG detection gated on barstate.isconfirmed (C2)
[ ] commit 2  fix: reset extreme-makers on BOS/CHoCH; movePhase vs current leg (C1)
[ ] commit 3  fix: zone detection decoupled from show* toggles (C3)
[ ] commit 4  fix: re-anchor majorHigh/majorLow on BOS-without-LH and on CHoCH (C5)
[ ] commit 5  fix: clear directional zone state on flip and on PROP re-arm (M11)
[ ] commit 6  fix: candidate fallback when top pick fails RR/score/gate (C4)
[ ] commit 7  fix: batch — BOS tie-break, break-flag reset, early-bar guards,
              stale arrivalMixed, incomplete flag, rangeBrkDir clear (M1,M2,M5,M6,M8,M10,M12)
[ ] commit 8  feat: premium/discount array + f_conf weight
[ ] commit 9  feat: session/killzone filter + SESH/SESL levels
[ ] commit 10 chore: remove dead type fields, unify scoring, cache TP scans
[ ] commit 11 test: strategy.pine port + per-module hit counters
```

প্রতিটা কমিটের পর: একই symbol/TF-এ চালিয়ে data-window diagnostics ([vesiont_01.txt:3249-3254](vesiont_01.txt#L3249-L3254)) দেখুন — signal সংখ্যা হঠাৎ ১০× বাড়া বা শূন্য হওয়া মানে regression।

---

## ৯. সারসংক্ষেপ

কোডটা দক্ষ হাতে লেখা — layering, state discipline, drawing budget, আর কমেন্টে পুরনো বাগের ব্যাখ্যা সব পেশাদার মানের। কিন্তু পাঁচটা বাগ সিগন্যাল chain-এর গোড়ায় বসে আছে, আর দুটো সবচেয়ে শক্তিশালী ICT ফিল্টার (PD array, killzone) টাইপে জায়গা পেয়েও কখনো লেখা হয়নি।

**একটা বাক্যে:** ৭৩টা সেটআপ নিয়ে একটা ইঞ্জিন, যার মধ্যে ৫টা মৌলিক বাগ আছে আর যার কোনো সেটআপের পরিসংখ্যান জানা নেই। **নতুন সেটআপ নয় — বাগ ফিক্স, তারপর দুটো ফিল্টার, তারপর পরিমাপ।** সেটাই এই বিল্ডের edge বের করার একমাত্র পথ।
