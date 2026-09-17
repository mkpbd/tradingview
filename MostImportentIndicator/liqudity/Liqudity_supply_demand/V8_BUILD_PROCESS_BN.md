# V8 বিল্ড প্রসেস — ধাপে ধাপে, compile/token/runtime error ছাড়া

> **সঙ্গী ডকুমেন্ট:** `V8_MASTER_PLAN_BN.md` (কী বানাবো) · এই ফাইল = **কীভাবে বানাবো**।
> **তিনটা শপথ:** ① প্রতিটা ধাপের শেষে compile সবুজ · ② compiled token headroom ≥ 5,000 · ③ signal কখনো তার চেয়ে দেরিতে আসবে না যতটা ডেটা বাধ্য করে।

---

## ০. শুরুর আগে — Pine v6-এর হার্ড লিমিট (এগুলো ভাঙলে কোড ঠিক হলেও ফেল)

| লিমিট | মান | V8-এ কী মানে |
|---|---|---|
| Compiled tokens | **100,256** (CE10117) | ফাইল A-র বাজেট ৯০k, বাকি ১০k headroom |
| Plot/plotchar/plotshape/bgcolor/hline output | **64** | 1.txt এটা ভরে ফেলেছিল। V8-এ সর্বোচ্চ ৪০, বাকি label/line দিয়ে |
| `request.security` কল | **40** | ফাইল A: সর্বোচ্চ ৬ · ফাইল B: সর্বোচ্চ ১২ |
| box / line / label | **500 প্রতিটা** (`max_*_count`) | registry + zones + trade lines মিলে 500 ছাড়াতে পারে → প্রতিটা array-তে cap |
| Local scopes | **~500** | প্রতিটা `if`/`for`/function body = ১ scope। বড় `if` chain ভেঙে function-এ নেওয়া |
| Loop iterations / bar | **500,000** | pool(28) × zone(16) nested loop = 448/bar, নিরাপদ। কিন্তু setup array × pool × zone = খেয়াল |
| Script execution / bar | **~500ms historical** | string concat প্রতি bar-এ = ধীর → `barstate.islast` গেট |
| Array size | 100,000 | সমস্যা না |
| String length | 4096 | alert payload ছোট রাখা |

---

## ১. ফাইল কাঠামো ও মডিউল ক্রম (dependency order — "undeclared identifier" এড়াতে)

Pine top-down পড়ে। নিচের ক্রম **অপরিবর্তনীয়**:

```
V8_ENGINE.pine
├── H0   header comment (version, changelog ≤ 30 লাইন — 2..txt-এর 1770-লাইন হেডার = source-size waste)
├── M0   indicator() + max_*_count
├── M1   inputs             (সব input এখানে, পরে কোথাও input.* নেই)
├── M2   constants + enum ints + tiny helpers (f_recent, f_geq, f_tfUp)
├── M3   core series        (atr, body, wick, pins, disp, relVol, CISD, IFC)
├── M4   structure          (type Struct, f_structUpdate, 2 instance)
├── M5   sessions + SB clock (type Ses, f_sesTrack, sbWinNow…)
├── M6   HTF context        (সব request.security এখানে — একসাথে, global scope)
├── M7   pool registry      (type Pool, queue, f_poolPush, f_poolScan, target scan)
├── M8   dealing range / OTE / SB range lock
├── M9   zones              (type Zone, create, lifecycle, regrade, tier)
├── M10  trigger candidates (CRT, TBS, inside-bar, doji — শুধু bool + level)
├── M11  run / congestion / regime / penalty
├── M12  setup machine      (type Setup, f_setupAdvance, setup arrays)
├── M13  score
├── M14  gates + dedupe
├── M15  risk primitives    (f_slOk, f_sl, f_tp, f_oppLiq)
├── M16  trade engine       (f_prod, f_grade, hard gates, arbitration, consumption)
├── M17  trade management   (type Trade, BE/trail/time/struct exit)
├── M18  drawing            (labels, lines, boxes — barstate.islast গেট যেখানে সম্ভব)
├── M19  dashboard          (একটা table, islast-এ update)
└── M20  alerts             (alertcondition + alert())
```

**নিয়ম:** কোনো মডিউল তার নিচের মডিউলের variable পড়বে না। যদি লাগে (যেমন M8-এর `sbSetLive` M17-এ লেখা হয়) → `var` declare উপরে, `:=` নিচে, এবং কমেন্টে লেখা "read one bar late by design"।

---

## ২. Compile error প্রতিরোধ — চেকলিস্ট (প্রতিটা ধাপে)

### ২.১ টাইপ ও স্কোপ
- [ ] প্রতিটা `var` declare-এ explicit type: `var float x = na`, `var int b = na` — `var x = na` ফেল
- [ ] tuple destructure `[a, b] = f()` **শুধু global scope-এ** — `if` ভিতরে দিলে "Cannot use tuple in local scope"
- [ ] `request.security` **কখনো** function ভিতরে যেটা loop/if থেকে call হয়, বা loop ভিতরে নয় → global, unconditional
- [ ] `request.security`-র tf argument `simple string` হতে হবে → input থেকে সরাসরি বা `f_tfUp(simple string)` দিয়ে; series string দিলে compile fail
- [ ] function parameter টাইপ লেখা: `f_x(Pool p, int dir, simple string tf)` — inference ভুল হলে ধরা যাবে
- [ ] function ভিতরে global **scalar** assign নিষেধ (`x := 1` যেখানে x global) → array/UDT field দিয়ে করা (`array.set(seq, 0, ...)`, `p.field := ...`)
- [ ] UDT field default দেওয়া: `type Pool \n float px = na \n int kind = 0` — না দিলে `Pool.new()` খালি call ফেল
- [ ] `switch` সব branch একই type ফেরত দেয়; `=> na` থাকলে অন্য branch float/int mix না করা
- [ ] ternary দুই পাশে একই type: `cond ? 1 : na` ঠিক, `cond ? 1 : "x"` ফেল
- [ ] `plotshape/plotchar/box.new`-এ `size`/`text_size` argument **const** হতে হবে — input থেকে নেওয়া `f_szPick()` series → **ফেল**। সমাধান: label.new-তে series size চলে; box text_size-এ const লিখা। (git log: `48b3c20 fix: plotshape and box.new want a const text size` — এই ভুল আগেও হয়েছে)
- [ ] `alertcondition()` message const string — dynamic লাগলে `alert()`
- [ ] `plot()` global scope-এ, `if` ভিতরে নয়; conditional করতে `plot(cond ? x : na)`

### ২.২ নাম সংঘর্ষ
- [ ] built-in নাম variable হিসেবে না: `time`, `volume`, `high`, `range`, `open`, `close`, `bar_index`, `session`, `label`, `line`, `box`, `table`
- [ ] 1.txt আর 2..txt থেকে copy করলে **একই নামের দুই definition** — `lastRes` 1.txt-এ var, 2..txt-এ alias। Merge-এর আগে grep: `grep -nE "^(var )?lastRes\b" V8_ENGINE.pine`
- [ ] `f_chip` দুই version আছে — 2..txt-এর (lane-spacing) রাখা

### ২.৩ Compile checkpoint প্রতিটা ধাপে
```
Pine Editor → Add to chart → কোনো লাল লাইন নেই
Console → "compiled code contains N tokens" খুঁজে দেখা (error না হলেও console-এ warning দেখায় না;
   token মাপতে: ইচ্ছা করে একটা বড় dummy block যোগ করে CE10117 message-এর সংখ্যা পড়া, তারপর সরানো)
```
সহজ পদ্ধতি: প্রতিটা phase-এর শেষে **নিচের প্রোব** ফাইলের একদম নিচে ১ মিনিটের জন্য paste করা:
```pinescript
// TOKEN PROBE — মাপার পরে মুছে ফেলো
var _probe = array.new<float>()
if barstate.islast
    for _i = 0 to 2000
        array.push(_probe, math.sin(_i) * math.cos(_i) + math.tan(_i) * math.log(_i + 1))
```
CE10117 এলে message-এ "contains X tokens" থাকে → X − (probe cost ≈ 300) = আসল সংখ্যা। না এলে headroom > probe cost — probe-এর loop count বাড়িয়ে খোঁজা।

---

## ৩. Runtime error প্রতিরোধ — চেকলিস্ট

Runtime error compile-এ ধরা পড়ে না, চার্টে **"Error on bar N"** হয়ে ইন্ডিকেটর মরে যায়। সবচেয়ে সাধারণ ৯টা:

| # | Error | কারণ | V8 নিয়ম |
|---|---|---|---|
| R1 | *Cannot access field of an undefined (na) object* | `p.px` যখন `p` = na | **প্রতিটা** UDT read `if not na(p)` গার্ডে, বা 2..txt-এর na-safe accessor (`f_poolPx`, `f_poolState`) দিয়ে। Setup-এর `s.pool.bound` ধরনের chain → দুই স্তরে গার্ড |
| R2 | *Index out of bounds* | `array.get(a, i)` যখন `i ≥ size` বা array খালি | `for i = array.size(a) - 1 to 0` **শুধু** `if array.size(a) > 0` ভিতরে। Reverse loop-এ `array.remove` ঠিক আছে, forward loop-এ remove করলে index shift → **নিষেধ** |
| R3 | *Division by zero* | `x / atr` প্রথম 14 বারে `atr = na`, `rng = 0` doji-তে, `risk = 0` | `math.max(atr, syminfo.mintick)`, `math.max(rng, syminfo.mintick)`, `risk = math.max(abs(e-sl), mintick)` |
| R4 | *Object na passed to line.new / box.new* | coordinate na | `line.new` আগে `not na(px)`; `box.new(x1, top, x2, bot)` — top ≥ bot না হলে error না, কিন্তু উল্টো আঁকে → `math.max/min` |
| R5 | *Too many drawings* (silent — পুরোনো মুছে যায়) | 500 ছাড়ালে TradingView FIFO delete করে → আমাদের array-তে reference থাকে, `line.set_*` তখন **error** | প্রতিটা drawing array-র নিজস্ব cap (`poolMaxN`, `maxZones`, `sbBoxKeep`) এবং সব cap-এর **যোগফল** ≤ 450। V8 budget: pools 28×1 line · zones 16×(1 box+1 line) · trade 5 line · SB 4 box · sessions 6 line+6 label · misc 20 = ~110 |
| R6 | *Loop takes too long* | nested loop বড় | pool × zone nested শুধু stage 3→4-এ, এবং শুধু live setup-এর জন্য (2..txt এটা মানে) |
| R7 | *String too long* | alert payload বা dashboard cell বড় | payload ≤ 400 char; `str.tostring(x, "#.##")` format দিয়ে |
| R8 | `str.tostring(na)` | "NaN" লেখে, error না — কিন্তু alert-এ NaN গেলে bot ভাঙে | `nz()` বা `na(x) ? "—" : str.tostring(x)` |
| R9 | *Memory limit* | `var` array-তে unbounded push | প্রতিটা `array.push` এর পরে size cap (`while array.size(a) > N: array.shift`) |

### R1 বিশদ — na-object প্যাটার্ন (2..txt থেকে, বাধ্যতামূলক)
```pinescript
// ভুল — p na হলে runtime error
float px = p.px

// ঠিক — একটাই accessor, সব জায়গায় এটা
f_poolPx(Pool p) =>
    float px = na
    if not na(p)
        px := p.px
    px
```
Setup-এর ভিতরে nested object (`s.pool`, `s.poiZone`, `s.tgtPool`) → `f_setupReset`-এ প্রথমে `if not na(s.pool)` তারপর `if s.pool.bound == s.id`। **এক লাইনে `and` দিয়ে জোড়া নিষেধ** — Pine short-circuit করে না।

---

## ৪. Token বাজেট — কোডিং নিয়ম (compiled token = source token × ~2.3–2.8)

### ৪.১ যা টোকেন খায় (2..txt-এর মাপা সংখ্যা)
| প্যাটার্ন | খরচ | নিয়ম |
|---|---|---|
| User function call | **পুরো body inline হয় প্রতিটা call site-এ** | ৪০০+ টোকেন body → সর্বোচ্চ ২ call। বেশি লাগলে queue প্যাটার্ন |
| `f_setupReset` ১৯ সাইটে | ~7,000 | `kill` flag, ১ reset site |
| `f_poolPush` ১৬ সাইটে | ~9,700 | `f_qPush` (৭ লাইন) × ১৬ + `f_qFlush` × ১ |
| Per-direction duplicate block | ×2 | `f_x(bool isL, ...)` একবার লেখা, দুইবার call — কিন্তু body ≤ 300 টোকেন হলে; বড় হলে inline ×2 = আবার double। **তাই direction-agnostic লেখা:** `sg = isL ? 1.0 : -1.0`, `pex = isL ? low : high`, তারপর `sg * (pex - px) > 0` (2..txt V5.6-L12) |
| `request.security` | ~250 + expression | ফাইল A-তে ৬ |
| String concat প্রতি bar | compile-এ কম, **runtime-এ বেশি** | `barstate.islast` গেট |
| Input tooltip | source token, compiled-এ কম | তবু ≤ 200 char |
| Dashboard table cells | ~90/cell | ফাইল A: ≤ 24 cell · বাকি ফাইল B |
| Debug panel | ~3,700 | **ফাইল B-তে** |
| Comment | **0** | কিন্তু header 1770 লাইন = editor lag; ≤ 100 লাইন |

### ৪.২ Token-সাশ্রয়ী idiom (কোড লেখার সময় সরাসরি)
```pinescript
// ✗ দুইটা function, দুইবার body
f_tapLong()  => low <= nbTop and close > nbBot
f_tapShort() => high >= nsBot and close < nsTop

// ✓ একটা, direction sign দিয়ে
f_tap(bool isL, float edgeNear, float edgeFar) =>
    isL ? (low <= edgeNear and close > edgeFar) : (high >= edgeNear and close < edgeFar)
```
```pinescript
// ✗ প্রতিটা stage-এ আলাদা expiry if
if s.st == 1 and bar_index - s.b1 > w1
    reset
if s.st == 2 and bar_index - s.b2 > w2
    reset

// ✓ একটা table lookup
int  stB = s.st == 1 ? s.b1 : s.st == 2 ? s.b2 : s.b3
int  stW = s.st == 1 ? w1   : s.st == 2 ? w2   : w3
kill := kill or bar_index - stB > stW
```
```pinescript
// ✗ 5টা downgrade if (C2)
// ✓ counter
int pen = (room < oppLiqMult ? 1 : 0) + (congested ? 1 : 0) + (runFade ? 1 : 0) + (hconf ? 1 : 0) + (regDown ? 1 : 0)
g := math.max(g - math.min(pen, maxPenalty), GR_NONE)
```

### ৪.৩ Token গেট প্রতিটা phase-এ
- phase শেষে probe (§২.৩) → সংখ্যা লিখে রাখা `TOKEN_LOG.md`-এ
- **headroom < 5,000 → পরের feature ফাইল B-তে যায়, ফাইল A-তে নয়**
- একবার CE10117 খেলে: প্রথমে dashboard cell কাটা, তারপর tooltip, তারপর trap visual — engine কখনো নয়

---

## ৫. Latency — signal দেরি না হওয়ার নিয়ম

Signal তিন জায়গায় দেরি হয়: **ডেটা** (HTF), **detection** (pivot confirm), **display** (drawing)। প্রতিটার নিয়ম:

### ৫.১ HTF ডেটা — ঠিক ১ HTF বার, তার বেশি নয়
```pinescript
// ✗ 1.txt — ২ HTF বার লেট (lookahead_off নিজেই ১ বার পেছায় + [1])
request.security(sym, tf, x[1], lookahead = barmerge.lookahead_off)

// ✗ repaint — forming HTF bar পড়ে, বার শেষে বদলায়
request.security(sym, tf, x, lookahead = barmerge.lookahead_off)

// ✓ V8 — closed HTF bar, প্রথম LTF bar-এই পাওয়া যায়, non-repainting
f_tfUp(simple string tf) => timeframe.in_seconds(tf) < timeframe.in_seconds() ? timeframe.period : tf
request.security(syminfo.tickerid, f_tfUp(tf), x[1], lookahead = barmerge.lookahead_on)
```
**`f_tfUp` ছাড়া `lookahead_on` = future leak** যদি tf < chart। তাই wrapper বাধ্যতামূলক, সব ৬ কলে।

### ৫.২ Pivot confirm — execution-এ ছোট pivLen
- `ta.pivothigh(len, len)` = **len বার পরে** confirm। `extPiv = 12` context-এর জন্য ঠিক, execution-এ নয়
- MSS/CHoCH (stage 5) **internal** structure-এ (`pivLen = 5`) → ৫ বার latency
- আরও কমাতে: stage-5-এ **CISD** অনুমোদিত রাখা (`mssNeedChoch = false`) — CISD-র কোনো pivot lag নেই, শুধু run-open ভাঙা লাগে। 2..txt এটা default-এ রাখে। V8-ও।
- HTF pivot `ta.pivothigh(2, 2)` (2..txt f_htfStruct) — ২ HTF বার = 15m চার্টে 1H pivot ৮ বার লেট। **গ্রহণযোগ্য**, কারণ HTF শুধু context

### ৫.৩ State transition — `barstate.isconfirmed` কিন্তু smart
- সব state write `confirmed`-এ (repaint শূন্য)। এটা ১ বার latency **বাধ্যতামূলক এবং সঠিক** — বার শেষ না হলে rejection candle-ই নেই
- **কিন্তু entry-র পরের কাজগুলো intrabar চলবে:** trade tracking (`low <= sl`) realtime-এ, label update realtime-এ
- **Preview alert (optional):** stage-7 setup থাকলে realtime bar-এ `alert("PREVIEW: retest forming", alert.freq_once_per_bar)` — 1.txt-এর ltConfMode idea। State বদলায় না, শুধু ট্রেডারকে ১ বার আগে জানায়
- `FVG_OWN_MAX = 2` + P1-3 "awaiting post-displacement confirmation" = displacement-এর পর **১ বার অপেক্ষা**। 2..txt এটা ইচ্ছা করে রেখেছে (expansion given back ধরতে)। V8: রাখা, কিন্তু `mssIsDisp = true` default (MSS candle-ই displacement হলে ১ বার বাঁচে)

### ৫.৪ Entry-র উপর অপ্রয়োজনীয় অপেক্ষা সরানো
| 2..txt-এ | কারণ | V8 |
|---|---|---|
| `strictSeq`: ctx এক বার, tgt পরের বার | চিরকাল ১ বার নষ্ট | ctx + tgt lock **একই বারে** অনুমোদিত (একটা `≤` জোড়া বাড়ানো) — এরা passive stage, কোনো price event নয় |
| entry-র পর `resetBar` blackout | পরের setup ১ বার লেট | blackout শুধু ওই pool id-র জন্য |
| `lateBars = 6` | ৬ বারের পরে retest → LATE kill | রাখা — এটা accuracy, latency নয় |

### ৫.৫ Drawing — চার্ট ধীর হলে signal-ও দেরি দেখায়
- সব "current state" drawing (target line, next zone label, dashboard) **শুধু `barstate.islast`-এ** — আগের বারের drawing মুছে নতুন আঁকা
- Historical bar-এ শুধু **event** drawing (entry label, sweep mark, zone box তৈরি)
- `box.set_right(bx, bar_index + 1)` প্রতি বারে ১৬ zone × ২৮ pool = ৪৪ setter/bar → ঠিক আছে; কিন্তু `extend.right` দিলে setter-ই লাগে না → pool line-এ `extend.right`
- string build (`"Sweep+POI+MSS" + ...`) **শুধু signal bar-এ** বা islast-এ

### ৫.৬ Alert
- `alertcondition()` — `alert.freq_once_per_bar_close` দিয়ে user সেট করবে
- `alert()` dynamic — কোডে `alert.freq_once_per_bar_close`
- Preview alert — `alert.freq_once_per_bar` (repaint স্বীকৃত, message-এ "PREVIEW" লেখা)

---

## ৬. ধাপে ধাপে বিল্ড (প্রতিটা ধাপ = compile + probe + test + commit)

### ধাপ 0 — কঙ্কাল (আধা দিন)
1. নতুন ফাইল `V8_ENGINE.pine`, H0 + M0 + M1 (সব input) + M2 (constants) — **আর কিছু না**
2. `2..txt`-এর input গ্রুপ ①–⑲ copy, tooltip ছোট করা, `showS1…` trap input বাদ (ফাইল B)
3. নতুন input যোগ: `useVolConf, volMult, maxSetups, maxPenalty, allowSynthTp, spreadGuard`
4. compile → সবুজ → probe → লিখো (`~4k` আশা)
5. `git commit -m "v8: skeleton — inputs + constants"`

### ধাপ 1 — Core + Structure (M3, M4)
1. 2..txt লাইন 2282–2664 copy (M3 candle anatomy, CISD, IFC, M4 Struct)
2. `relVol` যোগ M3-এ:
   ```pinescript
   volOk  = not na(volume) and volume > 0
   relVol = volOk ? volume / math.max(ta.sma(volume, 20), 1e-9) : 1.0   // volume না থাকলে bypass
   volPass = not useVolConf or not volOk or relVol >= volMult
   dispUpBar = bullBar and body >= dispFactor * atr and strongUp and volPass
   ```
3. `f_chip` 2..txt version (lane spacing)
4. **Test:** চার্টে BOS/CHoCH chip আসে; `showStruct = false` করলে chip যায় কিন্তু `sInt.dir` dashboard-এ (temp `plot(sInt.dir)`) অপরিবর্তিত
5. compile → probe → commit

### ধাপ 2 — Sessions + SB clock + HTF (M5, M6)
1. 2..txt 2667–2772 (Ses UDT) + 1.txt 612–657 (`f_sesMin`, `sbStart*`, `sbWinNow`, `sbCtxWin`, `sbPre*`, `sbEnd*Evt`)
2. 2..txt 2788–3066 HTF block, **কিন্তু** MTF ladder (2848–2862) **বাদ** → ফাইল B
3. security কল গোনা: bias(1) + htfCtx(1) + PD(1) + PW(1) + htfStruct(1) + htfPoi(1) = **৬**
4. **Test (repaint):** bar replay → `htfDir` চার্টে `plotchar` দিয়ে; replay আর live-এ একই বারে বদলায়
5. compile → probe → commit

### ধাপ 3 — Pool registry (M7) ⭐
1. 2..txt 3076–3813 হুবহু (Pool UDT, accessors, queue, push, scan, EQ ring, TL, target scan, f_findRaid)
2. `PK_WICK = 8, PK_N = 9` যোগ (LT-3/LT-4 cluster পরে এখানে push হবে); `f_kindPri` তে `PK_WICK ? 2`
3. **R2 চেক:** সব `for` reverse যেখানে `array.remove`; সব `if array.size > 0`
4. **R5 চেক:** `poolMaxN` ≤ 28
5. **Test:** pool line আসে; `showPools = false` করলে line transparent হয় **কিন্তু** `sslInPlay` (temp plotchar) অপরিবর্তিত
6. compile → probe (এখানে ~35k আশা) → commit

### ধাপ 4 — Range + Zones (M8, M9)
1. 2..txt M8 (3815–3848) + 1.txt SB-12 range lock (1261–1276) — `sbSetLive` var এখানে declare, M17-এ assign
2. 2..txt M9 zones (3875–4628) হুবহু — Zone UDT, provenance, tier, regrade
3. যোগ `spreadGuard`: zone তৈরির আগে
   ```pinescript
   spreadEst = math.max(syminfo.mintick * 2, ta.sma(rng, 50) * 0.02)   // ২ tick বা 2% of avg range
   zoneOk = not spreadGuard or (zTop - zBot) >= 2 * spreadEst
   ```
4. যোগ `htfOverlap`: `f_zoneTier`-এ `overlap ? tier - 1 : tier`, যেখানে `overlap = not na(hPoiBTop) and zTop >= hPoiBBot and zBot <= hPoiBTop`
5. **R1 চেক:** `f_zoneTier(na)` → 3 ফেরত দেয়
6. **Test:** display-independence — `showZones=false`, zone count (temp plot `array.size(zones)`) সমান
7. compile → probe (~52k) → commit

### ধাপ 5 — Triggers + Regime + Penalty (M10, M11)
1. 1.txt 1757–1779 CRT/TBS **শুধু bool + level**, `sig*` var নয়:
   ```pinescript
   crtB  = crtC1Big and low[1] < low[2] and close[1] > low[2] and close[1] < high[2] and low[2]-low[1] >= minWickAtr*atr and bullBar and close > high[1] and body >= crtDispAtr*atr
   tbsB  = low < tbsLow and close > tbsLow and bullBar and f_tbsAgeOk(tbsLowAge) and close >= low + 0.5*rng
   ```
   এরা M12-এ stage 5→6-এ `dsp or crtB or tbsB` হিসেবে ঢুকবে (তখনও `past and away and hold` লাগবে)
2. 2..txt 4812–4941 run/cong/regime হুবহু
3. penalty counter §৪.২ অনুযায়ী — `f_grade`-এ পাঁচটা `if` বদলে
4. compile → probe → commit

### ধাপ 6 — Setup machine, multi-setup (M12) ⭐⭐ সবচেয়ে ঝুঁকিপূর্ণ
1. 2..txt 4996–5666 copy। **প্রথমে single-setup রেখে compile করা** — কাজ করছে নিশ্চিত হওয়া
2. তারপর array-তে রূপান্তর:
   ```pinescript
   var upSetups = array.new<Setup>()
   var dnSetups = array.new<Setup>()

   // advance সব live setup, dead সরাও (reverse loop)
   f_runSide(array<Setup> arr, int dir) =>
       bool  anyEntry = false
       Setup winner   = na
       string blk     = ""
       if array.size(arr) > 0
           for i = array.size(arr) - 1 to 0
               Setup s = array.get(arr, i)
               [e, b] = f_setupAdvance(s, dir)        // ✗ tuple in local scope — নিচে দেখো
               ...
   ```
   **সমস্যা:** tuple destructure local scope-এ চলে না। **সমাধান:** `f_setupAdvance` `entry` bool ফেরত না দিয়ে `s.st == ST_ENTRY` দিয়ে পড়া, `blk` string `s.blk` field-এ লেখা। তখন:
   ```pinescript
   f_runSide(array<Setup> arr, int dir) =>
       Setup winner = na
       if array.size(arr) > 0
           for i = array.size(arr) - 1 to 0
               Setup s = array.get(arr, i)
               f_setupAdvance(s, dir)
               if s.st == ST_DEAD
                   array.remove(arr, i)
               else if s.st == ST_ENTRY
                   if na(winner) or s.poiTier < winner.poiTier
                       winner := s
       // নতুন arm: slot খালি এবং target pool কারো দখলে নয়
       Pool tp = dir == 1 ? tgtSellPool : tgtBuyPool
       bool  free = not na(tp)
       if free and array.size(arr) > 0
           for i = 0 to array.size(arr) - 1
               if array.get(arr, i).tgtId == tp.id
                   free := false
       if free and array.size(arr) < maxSetups and (dir == 1 ? htfCtxLong : htfCtxShort)
           Setup n = Setup.new()
           n.st := ST_CTX
           ... (ctx + tgt একই বারে — §৫.৪)
           array.push(arr, n)
       winner
   ```
   `f_setupAdvance` **inline ×1** (শুধু `f_runSide` ভিতরে), `f_runSide` inline ×2 → `f_setupAdvance` body মোট ×2 — 2..txt-এর সমান। **ভালো।**
3. **R1:** `winner` na হতে পারে → M16-এ `f_prod(..., winner, ...)` আগে `not na(winner)` → `mach = not na(winner)`
4. **R6:** setup(2) × zone(16) stage-3→4 loop = 32/bar। ঠিক
5. **Test (chronology):** temp label প্রতিটা entry-তে `raidBar/poiBar/mssBar/dispBar/fvgBar/retestBar` — strictly বাড়ছে
6. **Test (multi):** dashboard-এ দুই setup-এর stage আলাদা দেখা যায়
7. compile → probe (~72k আশা — এখানে **সবচেয়ে বড় লাফ**) → commit

### ধাপ 7 — Score + Gates + Risk + Trade engine (M13–M16)
1. 2..txt 5688–6430 copy; `f_prod`-এ `Setup s` = `winner`; trap producer ফাইল B-তে → `pa1/paSl/tw/tq/tel` parameter বাদ (টোকেন বাঁচে)
2. `allowSynthTp`: `hTgt = tgtSrc != 0 or allowSynthTp`; `f_grade`-এ `if tgtSrc == 0: g := math.min(g, GR_B)`
3. SB score component (1.txt 2023–2028) `f_score`-এ `+ sbCtx` clamp 100
4. **Test (risk):** প্রতিটা entry label-এ RR প্রিন্ট; কোনোটা < 1.5 নেই; SL/ATR 0.25–3.0
5. compile → probe (~84k — **সীমার কাছে**) → commit
6. **headroom < 8k হলে:** dashboard cell ২৪ → ১২, tooltip সব ≤ 100 char

### ধাপ 8 — Trade management (M17)
1. 2..txt 16C (`Trade` UDT, stop-first) + 1.txt SB-6 (2905–3001: adaptive BE, protected trail with 2-bar cap, TP3 liq target, time exit, struct exit)
2. `sbSetLive :=` এখানে (M8-এ declare করা var)
3. একটা trade; নতুন signal এলে চলমান trade **বন্ধ** করে counter-এ "replaced" — overwrite নয় (B12)
4. compile → probe → commit — **এখানে যদি CE10117 → §৪.৩ কাটার ক্রম**

### ধাপ 9 — Drawing + Dashboard + Alerts (M18–M20)
1. Entry label: একটা `label.new` per signal, text signal bar-এ build
2. Trade lines: ৫টা `var line`, islast-এ `set_xy`
3. Dashboard: ১টা `table.new`, ≤ 12 cell, `if barstate.islast` ভিতরে সব `table.cell`
4. Alerts: ৪ `alertcondition` (long/short A+, long/short A) + ১ `alert()` structured payload
5. **Output count** গোনা: plot ≤ 12, plotchar ≤ 10, bgcolor ≤ 4 = 26 < 64
6. compile → probe → **final headroom ≥ 5k নিশ্চিত** → commit `v8.0.0`

### ধাপ 10 — ফাইল B (`V8_CONTEXT.pine`)
1. 2..txt MTF ladder (4 security) + 1.txt M13 `f_crtTbsHtf` চার TF-এ (4 security) + `f_htfPoi` HTF FVG box drawing
2. 1.txt M16B trap engine LT-1…7 **visual + alert() only** — কোনো entry label নয়
3. 2..txt debug panel (dbgVerbose) — কিন্তু এটা ফাইল A-র internal state পড়তে পারে না → ফাইল B **নিজের** copy of structure/pool light version চালায় শুধু display-এর জন্য, বা debug panel ফাইল A-তেই ছোট রাখা (৬ cell)
4. আলাদা compile, আলাদা probe (~45k)

---

## ৭. পরীক্ষা প্রোটোকল (প্রতিটা ধাপে ৫ মিনিট)

| টেস্ট | কীভাবে | পাস মানে |
|---|---|---|
| Compile | Add to chart | কোনো লাল লাইন |
| Token | probe §২.৩ | headroom ≥ 5k লিখে রাখা |
| Runtime | ৩টা symbol × ৩ TF (BTCUSDT 5m, EURUSD 15m, NAS100 1m) স্ক্রোল করে শুরু থেকে শেষ | কোনো "Error on bar" |
| Display-independence | সব `show*` off → temp `plot(signalCount)` | সংখ্যা সমান |
| Repaint | Bar replay ২০০ বার, একটা entry-র bar_index নোট → live-এ একই | সমান |
| Latency | entry label-এর bar vs rejection candle-এর bar | পার্থক্য = 0 (confirmed-এ label) |
| Chronology | temp label stage bars | strictly ordered |

Temp `plot`/`label` প্রতিটা টেস্টের পরে **মুছে** commit।

---

## ৮. Git কনভেনশন
```
v8: P<n> <module> — <what>

<why, ১-২ লাইন>
tokens: <probe number> / 100256
```
প্রতিটা ধাপ একটা commit। CE10117 fix আলাদা commit যাতে কী কাটা হলো ট্র্যাক থাকে।

---

## ৯. যা **করবো না** (দুই ফাইলের ভুল থেকে)
- ❌ Header-এ changelog 1770 লাইন (2..txt) — `CHANGELOG.md` আলাদা
- ❌ `showX and detection` (1.txt B2)
- ❌ `lookahead_off` + `[1]` (1.txt B9)
- ❌ per-direction দুইবার লেখা block (1.txt M17 LONG/SHORT 90 লাইন × 2)
- ❌ function যেটা 400+ টোকেন এবং ৩+ বার call (2..txt f_poolPush v5.5)
- ❌ `p.field` na গার্ড ছাড়া
- ❌ forward loop-এ `array.remove`
- ❌ dashboard/debug string প্রতি historical bar-এ build
- ❌ `plotshape(size = seriesVar)` — const লাগে
- ❌ ৪টা display-only `request.security` ফাইল A-তে (2..txt C5)
- ❌ input বাড়িয়ে ফিচার "configurable" করা যেখানে একটা sensible const চলে — প্রতিটা input ≈ 40 compiled টোকেন
