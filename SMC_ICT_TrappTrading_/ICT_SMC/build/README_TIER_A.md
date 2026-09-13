# SMC + ICT Engine — Tier A (Phase 1–16)

File: `SMC_ICT_Engine.pine` — Pine Script **v6**, single `indicator()`.

## Phase → code map

| Phase | Section in file | কী আছে |
|---|---|---|
| 1 Swing Structure | `05 LAYER 1` | `ta.pivothigh/low(swingLen)` → HH/HL/LH/LL, cap 100 |
| 2 Liquidity | `05 LAYER 1` | BSL/SSL/EQH/EQL/PDH/PDL/PWH/PWL, ATR-normalized EQ tolerance, cluster strength, cap 50 |
| 3 BOS / CHoCH | `06 LAYER 2` | Close/Wick mode, `trendDir` flip, level consumed flag |
| 4 Displacement | `06 LAYER 2` | ATR size **এবং** body ratio — দুইটাই লাগে |
| 5 Sweep + MSS | `06 LAYER 2` | penetrate + close-back + rejection wick; MSS = displacement + internal break |
| 6 FVG + lifecycle | `06 LAYER 2` | middle candle displacement বাধ্যতামূলক, min gap = ATR×, NEW→ACTIVE→TOUCHED→MITIGATED→FILLED |
| 7 OB / BB / IFVG | `06 LAYER 2` | OB শুধু displacement+MSS validate হলে; FILLED হলে inverse zone (IFVG/BB) |
| 8 Premium/Discount/OTE | `05 LAYER 1` | dealing range = শেষ confirmed swing H/L, EQ, OTE 0.618–0.786 |
| 9 HTF Context | `05 LAYER 1` | `request.security(... [1], lookahead_off)` + auto TF map |
| 10 Session / Kill Zone | `05 LAYER 1` | timezone input, Asia/London/NY |
| 11 Entry State Machine | `07 LAYER 3` | IDLE→CONTEXT→SWEPT→DISP→MSS→POI→RETRACE→ENTRY→TRADE, প্রতি step-এ timeout |
| 12 Score + SL/TP/RR | `07 LAYER 3` | score v1 (max 12, contradiction −3), SL = sweep ± ATR buffer, TP = next liquidity, `rr < minRR` → no trade |
| 13 Visuals + Settings | `09 DRAWING` | ১০টা input group, প্রতি module আলাদা toggle |
| 14 Alerts | `11 ALERTS` | trade / BOS / CHoCH / sweep / zone, `freq_once_per_bar_close` |
| 15 Repaint audit | পুরো ফাইল | নিচে checklist |
| 16 Integration tests | — | নিচে matrix |

## Hard rules যা code-এ enforce করা আছে

- Signal শুধু **একটাই দরজা** — Layer 3 state machine। কোনো module একা signal দেয় না।
- সব state transition `barstate.isconfirmed`-এ।
- এক setup = এক signal (`signalEmitted`), POI `consumed := true`।
- একই bar-এ LONG + SHORT trigger → **দুইটাই reject**।
- Array cap: swings 100 · liquidity 50 · zones 100। মোছার **আগে** `box.delete` / `line.delete`।
- সব array loop backward, এবং size>0 guard (`for i = size-1 to 0` size 0 হলে index −1 → runtime error, তাই guard)।
- সব division `math.max(x, syminfo.mintick)` দিয়ে সুরক্ষিত।
- `request.security` মোট ৪টা (Tier B-র SMT সহ), সবগুলোতে `[1]` + `lookahead_off`।

## Repaint checklist (Phase 15)

- [ ] Chart reload (F5) → history হুবহু এক
- [ ] Realtime signal → bar close → signal টিকল
- [ ] HTF বদলে ফেরত → signal অপরিবর্তিত
- [ ] Bar replay → একই signal একই জায়গায়
- [ ] শেষ `swingLen` bar-এ swing label নেই (এটা সঠিক)

## Integration test matrix (Phase 16)

| # | Test | প্রত্যাশিত |
|---|---|---|
| 1 | SSL sweep → disp → MSS → FVG → retrace | ঠিক ১টা LONG |
| 2 | BSL sweep → disp → MSS → FVG → retrace | ঠিক ১টা SHORT |
| 3 | Wick ভাঙল, ভেতরে close | Close mode-এ BOS নেই |
| 4 | Sweep আছে, displacement নেই | trade নেই (10 bar পরে INVALIDATED) |
| 5 | RR < 1.5 | trade নেই |
| 6 | একই FVG-তে ৫ touch | ১টা signal |
| 7 | Reload / realtime তুলনা | consistent |
| 8 | Weekend gap | swing ভাঙে না |
| 9 | একই bar-এ LONG + SHORT | দুইটাই reject |
| 10 | 5000 bar history | hang নেই, object error নেই |

**Sanity:** 15M chart, ১ মাস → ১০–৪০টা signal। ২০০+ = logic ঢিলা। ০ = কোনো transition আটকে (Debug table চালু করো: Visuals → Show Debug)।

## Tuning যদি signal ০ হয়

1. `Require HTF Alignment` off করো — HTF bias `NEUTRAL` হলে সব block হয়।
2. `Min Score to Trade` 7 → 5।
3. `Min RR` 1.5 → 1.2।
4. `Sweep -> MSS timeout` 10 → 15।
5. Debug table-এ LONG/SHORT state দেখো — কোন step-এ আটকে আছে।

## পরের ধাপ

Tier B (Phase 17–34) — Trendline engine, CISD, SMT, AMD/PO3, Trap, BPR, Silver Bullet, Score v2।
Tier B-র প্রতিটা module-এর toggle **default `false`** হবে (plan-এর নিয়ম ২)।

---

# TIER B (Phase 17-34) — added

সব Tier B toggle **default `false`**। সব off = Tier A-র আচরণ হুবহু ফিরে আসে (Phase 34 test 11)।

| Phase | Input group | কী করে |
|---|---|---|
| 17 Trendline | `11 - Trendline (B)` | শুধু confirmed swing anchor, validity একবার build-time-এ check, touch cooldown 3 bar, strength 0-100, per-side cap |
| 18 Channel + TLQ | `11 - Trendline (B)` | TL break vs TLQ sweep আলাদা; TLQ `liquidity` array-তে ঢোকে আর **একই** `LIQUIDITY_SWEPT` দরজা ব্যবহার করে |
| 19 CISD | `12 - CISD (B)` | candle run-এর প্রথম open = CISD level; `CISD can replace Displacement` on করলেই কেবল displacement-এর বিকল্প |
| 20 SMT | `13 - SMT (B)` | correlated symbol, inverse toggle, symbol খালি = নিঃশব্দে skip; শুধু score (v2) |
| 21 AMD / PO3 | `14 - AMD / PO3 (B)` | Asia range দিনে একবার lock, Judas swing, phase ACCUM/MANIP/DISTRIB |
| 22 Trap / Turtle Soup | `15 - Trap (B)` | bars-outside গণনা; trap sweep-এর একই দরজায় ঢোকে |
| 23 S/D + MB + RB | `16 - Supply-Demand (B)` | cluster zone, mitigation block, wick-based rejection block |
| 24 BPR / Void / CE | `17 - BPR / Void (B)` | opposite FVG overlap = BPR; void = Gap type; `Entry Reference` = Close / Zone Edge / CE / Zone Full |
| 25 Opening Gaps | `18 - Opening Gaps (B)` | NWOG / NDOG / ORG, per-kind last N, CE line |
| 26 IRL / ERL / DOL | `19 - IRL / ERL / DOL (B)` | bias-এর দিকের সবচেয়ে কাছের unswept level = DOL, dashboard-এ ATR দূরত্ব সহ |
| 27 Silver Bullet | `20 - Silver Bullet (B)` | তিনটা window + macro (:50-:10, <1H only); `sbOnly` শুধু **emit** আটকায়, state চলতে থাকে |
| 28 Unicorn / MMBM | `21 - Market Model (B)` | BB+FVG overlap ≥ ratio = UNICORN zone; MMBM/MMSM model name alert-এ যায় |
| 29 Daily Bias | `22 - Daily Bias (B)` | weekly/daily open `ta.valuewhen` দিয়ে (request.security নয় = repaint নেই) |
| 30 Std Dev | `23 - Std Dev Targets (B)` | sweep→MSS unit-এর multiple; TP priority-তে সবার শেষে, `Use as TP` on করলেই |
| 31 Score v2 | `24 - Score Model (B)` | শ্রেণীভিত্তিক capping (max 14) + penalty; **default `v1`** |
| 32 Dashboard / Density | `10 - Visuals` | 11 row dashboard, `Visual Density` = Minimal / Normal / Full, dashboard position |
| 33 Object budget | — | zones 100 · liquidity 50 · gaps 30 · trendline 2×cap · sdev lines cleared per bar; ভারী loop শুধু `barstate.isconfirmed`-এ; `request.security` মোট **4** |

## Plan থেকে ইচ্ছাকৃত দুইটা বিচ্যুতি (কারণসহ)

1. **`Entry Reference` default = `Close`** (plan বলেছিল `CE`)। কারণ: Tier B-র এক নম্বর শর্ত — সব নতুন toggle off রাখলে Tier A-র ফল অপরিবর্তিত থাকতে হবে। CE default দিলে entry price বদলে যেত, তাই Tier A-র আচরণই default; CE হাতে বেছে নেওয়া যায়।
2. **Score v2 default off** (plan বলেছিল v2 + threshold 8 দিয়ে v1 replace)। একই কারণ। `Score Model = v2` করলেই 14-point শ্রেণীভিত্তিক score + threshold 8 চালু।

## Tier B test matrix (Phase 34)

| # | Test | প্রত্যাশিত |
|---|---|---|
| 11 | সব Tier B toggle off | Phase 16-এর ফল অক্ষরে অক্ষরে এক |
| 12 | Trendline on, reload ×3 | প্রতিটা line একই anchor |
| 13 | TL break, displacement নেই | trade নেই |
| 14 | TLQ sweep + disp + MSS + POI | ঠিক ১টা signal |
| 15 | SMT symbol খালি | error নেই, skip |
| 16 | SMT ভুল symbol | signal সংখ্যা অপরিবর্তিত (v1-এ score-ও অপরিবর্তিত) |
| 17 | Asia range + Judas | range lock, Judas চিহ্নিত, amdBias set |
| 18 | Trap: ১০ bar বাইরে থেকে ফেরত | trap **নয়** (limit 5) |
| 19 | Unicorn (BB+FVG overlap) | ১টাই UNICORN zone, confluence +2 (v2) |
| 20 | `sbOnly` on | বাইরের emit বন্ধ, state আটকায় না |
| 21 | সব module on, 5000 bar | load < 5s, object error নেই |
| 22 | Weekend gap + NWOG | gap আঁকে, swing ভাঙে না |

**Golden check:** সব on করলে signal সংখ্যা **কমবে**, বাড়বে না। বাড়লে কোনো module signal emit করছে — বাগ।

---

# TIER C (Phase 35-48) — added

| Phase | Input group | কী করে |
|---|---|---|
| 35 Regime filter | `25 - Regime (C)` | তিনটা স্বাধীন মাপকাঠি (efficiency, range squeeze, structure consistency) — অন্তত **দুইটা** একমত হলে regime। CHOP = score −3 + `chopBlock` on থাকলে emit বন্ধ। RANGE = শুধু range-এর প্রান্তের setup |
| 36 ADR | `26 - ADR (C)` | ADR = previous-day range-এর SMA (`[1]`+`lookahead_off`)। আজকের ব্যবহৃত % dashboard-এ; exhausted হলে **continuation**-এ −2, reversal-এ কিছু নয় |
| 37 Open lines | `27 - Open Lines (C)` | Midnight Open / True Day Open (08:30) / Weekly Open — সব `open` capture, `request.security` নয় |
| 38 Volume Imbalance | `28 - VI (C)` | body gap + wick overlap, `< ATR × 0.05` বাদ। শুধু density `Full`-এ আঁকে (নাহলে চার্ট ভরে যায়) |
| 39 HTF POI | `29 - HTF POI (C)` | HTF FVG শুধু **বন্ধ** HTF candle থেকে (`[1]`/`[2]`/`[3]`), একই `zones` array-তে `isHTF = true`, আলাদা cap 20 |
| 40 Trade management | `30 - Trade Mgmt (C)` | TP1/TP2/TP3 (Liquidity বা R-based), TP1-এ BE, structure trail (কখনো পেছনে যায় না), EOD flat |
| 41 Position size | `31 - Position Size (C)` | account × risk% ÷ (SL দূরত্ব × pointvalue); unit `syminfo.type` অনুযায়ী (lot / contracts / coin) |
| 42 Time exit / News | `32 - Exits & News (C)` | max hold, EOD flat, news blackout (হাতে লেখা সময় — Pine-এ news feed নেই)। Blackout শুধু **নতুন entry** আটকায়, চলমান trade-এর BE/trail চলে |
| 43 Instrument preset | `33 - Preset (C)` | Auto (`syminfo.type` + XAU detect) / Forex / Gold / Index / Crypto / **Manual (default)** — preset শুধু effective মান বদলায় |
| 44 Backtest stats | `34 - Stats (C)` | trades / win% / total R / expectancy / avg RR / best-worst / max consecutive loss। একই bar-এ TP+SL = **SL** ধরা হয় |
| 45 Webhook JSON | `35 - Alert Format (C)` | `Text` বা `JSON` — JSON সরাসরি string দিয়ে বানানো, `{{...}}` placeholder-এর উপর নির্ভর করে না |
| 46 Intrabar mode | `8 - Entry Engine` | `intrabar` default off। On করলে label-এ `LIVE` লেখা + dashboard হলুদ; **alert সবসময় bar close-এ** |
| 47 Defensive coding | `01C` section | `runtime.error` চারটা পরস্পরবিরোধী setting-এ; HTF < chart TF হলে module নিঃশব্দে skip (`HTF<TF!` dashboard-এ); সব division ও array access guarded |
| 48 Publish checklist | নিচে | — |

## Tier C-তে ইচ্ছাকৃত বিচ্যুতি

- **Preset default = `Manual`** (plan-এ `Auto`)। Auto গোল্ড/ক্রিপ্টোতে swingLen ও ATR mult বদলে দিত, তাতে "সব off = Tier A হুবহু" শর্ত ভাঙত। `Auto` হাতে বেছে নেওয়া যায়।
- সব Tier C toggle default **off** (stats table, VI, regime, ADR, trade management, size, news — সব)। Default setting = Tier A behavior.

## Phase 48 — Publish checklist

**Code**
- [x] প্রতিটা section `// === NN - NAME ===` header
- [x] Section ক্রম: inputs → preset → validation → types → state → helpers → L1 → L2 → L3 → cleanup → drawing → dashboard → alerts
- [ ] প্রতিটা input-এ `tooltip` — **এখনো বাকি** (publish-এর আগে যোগ করতে হবে)
- [x] Default setting-এ চার্ট পরিষ্কার (Tier B/C সব off)

**Correctness**
- [ ] Phase 15 repaint audit ৪টা (TradingView-তে চালাতে হবে)
- [ ] Test 1–22
- [ ] ৩ instrument × ৩ timeframe = ৯ combination
- [ ] সব module on → load < ৫ সেকেন্ড

**Publish**
- [ ] Description: এটা **indicator, strategy নয়**
- [ ] সীমাবদ্ধতা: stats approximation (spread/slippage/commission নেই), position size আনুমানিক, intrabar mode repaint করতে পারে, news time হাতে দিতে হয়
- [ ] কোনো লাভের প্রতিশ্রুতি নেই
- [ ] পরিষ্কার চার্টের screenshot
- [ ] ৩ লাইনের quick-start

## Quick start (৩ লাইন)

1. Default-এই চালাও — Tier A engine, ১৫M chart, দিনে ০–২টা signal।
2. Signal ০ হলে: `Require HTF Alignment` off → `Min Score` 5 → Debug table on।
3. মান বাড়াতে: `Regime Filter` on + `chopBlock` on, তারপর `Score Model = v2`।
