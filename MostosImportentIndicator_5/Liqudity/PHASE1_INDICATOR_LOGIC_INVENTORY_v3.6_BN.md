# PHASE 1 — Indicator Discovery & Internal Logic Mapping
## LQ-SD-PA v3.6 (`liqudity_trap_trading.v3.6.txt`, BUILD v3.6-b2 · 2026-10-03)

> **Audit date:** 2026-10-14 · **Scope:** Phase 1 only — কোডে আসলে কী আছে, সেটার inventory।
> এই phase-এ কোনো bug verdict দেওয়া হয়নি। "Potential weakness" column-গুলো Phase 2/3-এর investigation list — confirmed defect নয়।
> প্রতিটি দাবির পাশে source line number আছে। যেটা কোডে নেই, সেটা "নেই" লেখা হয়েছে।

---

## 0. Script facts (verified by grep, comments excluded)

| Fact | Value | Evidence |
|---|---|---|
| Pine version | `//@version=6` | L1 |
| Script type | `indicator(..., overlay = true)` — strategy নয় | L634 |
| Object limits | boxes 500 · lines 500 · labels 500 | L635 |
| Total lines | 5,599 (≈ 640 lines header changelog, L1–633) | — |
| Modules | 1 … 23 (+ 4B, 15A, 16B, 18B) | section headers |
| User inputs | **219** (`input.bool/int/float/string/session`) | grep |
| `request.security()` calls | **7** — সবগুলো `[1]` + `lookahead_on` idiom | L1670, L1671, L2036, L2112, L2188, L2299, L2346 |
| Output budget | plot 8 + plotchar 12 + bgcolor 3 + alertcondition 30 = **53 / 64** | grep; header L83 claim matches |
| `alert()` dynamic calls | 14 (journal line, LT ×2, SB feed ×5, …) | L5548–5599 |
| Drawing objects | label.new 13 sites · box.new 11 · line.new 16 · table.new 2 | grep |
| Bar-close gate | `confirmed = barstate.isconfirmed` (L1206) — প্রায় প্রতিটি state write ও signal এই flag দিয়ে gated | — |
| Last-bar-only redraw | `barstate.islast` ×5 (POI boxes, NEXT level, extend, dashboard, debug) | L5173, L5269, L5315, L5369, L5468 |
| External files referenced in header | `scripts/mktwin.py`, `liqudity_trap_strategy.txt` (L627) — **folder-এ নেই** | `ls` |

---

## 1. Concept checklist — কোন concept কোডে আছে, কোনটা নেই

| Concept | আছে? | Where / how (actual implementation) |
|---|---|---|
| Trend-following logic | আংশিক | কোনো MA-crossover trend engine নেই। "Trend" = external protected-swing structure direction (`extDir`, L1950) + HTF bias (`htfB`, L2118). |
| Support / resistance | আছে | `lastRes` / `lastSup` = শেষ confirmed internal pivot (L1345, L1373). Plot হয় (L5009). |
| Supply & demand zones | আছে | MODULE 13: zone = FVG-imbalance geometry (`low` → `high[2]`) যখন displacement candle থাকে (L2905–2927). |
| Smart Money Concepts | আছে | BOS/CHoCH/MSS, sweeps, OB, FVG, breaker/mitigation, premium/discount। |
| ICT | আছে | Silver Bullet windows (MODULE 4B), CE (consequent encroachment) limit entry, OTE 0.62–0.79, killzones, PDH/PDL/PWH/PWL, CISD, IFC, Turtle soup, CRT। |
| Order Blocks | আছে | "OB companion" = displacement-এর আগের opposing candle `[2]` (L2930–2935, L2955–2960)। শুধু S/D zone তৈরির সময়ই OB তৈরি হয়। |
| FVG | আছে | 3-candle gap: `low > high[2]` / `high < low[2]` (L2550–2551)। Registry (MODULE 12) + latest-FVG tracker (L2660)। IFVG flip (L2602)। |
| BOS | আছে | `f_structure` (L1883): displaced close (`body ≥ structDisp×ATR`) through latest pivot in trend direction। Internal + External দুই instance। |
| CHoCH | আছে | একই function: displaced close through **protected swing** (`protLo/protHi` = leg extreme যেখান থেকে শেষ BOS হয়েছিল)। |
| MSS | আছে | `mssUp = (eChochUp or (not mssNeedExt and chochUp)) and sslInPlay and lastSslQual >= 2` (L1955) — CHoCH + quality sweep in play। |
| Liquidity sweeps / stop runs | আছে | MODULE 5: swing sweep (L1530), EQH/EQL pool (L1625), PDH/PDL/PWH/PWL (L1687), session H/L raid (L1720), multi-bar reclaim (FIX-Y3, L1524)। 4-grade quality (L1533)। |
| Premium / discount | আছে | MODULE 10: dealing range = running high/low since older anchoring swing (L2395–2412)। `pdPos` 0–1 clamped। |
| Fibonacci / OTE | আছে (শুধু OTE) | `OTE_1 = 0.62`, `OTE_2 = 0.79` (L1155); `inOTEbuy/sell` (L2417)। অন্য কোনো Fib level নেই। |
| EMA | আছে | শুধু HTF bias: `close > ta.ema(close, 50)` on bias TF + Daily (L2036)। |
| RSI / ADX | **নেই** | কোনো RSI, ADX, MACD, Stochastic নেই। |
| ATR | আছে (core) | `ta.atr(14)` + 50-bar shock cap (L1192–1194)। ফাইলের সব distance ATR-scaled। |
| Volume | আছে (optional, default OFF) | `relVol` (L1211); displacement gate + sweep grade bonus। |
| HTF confirmation | আছে | 7 security calls: EMA bias, HTF structure (BOS/CHoCH on bias TF), HTF CRT/TBS, HTF FVG POI registry (3 slots/side), PDH/PDL, PWH/PWL, ADR। |
| LTF confirmation | **নেই** | কোনো lower-timeframe `request.security` নেই। "LTF" শব্দ মানে chart TF নিজেই। |
| Sessions / killzones | আছে | Asia 20:00–00:00, London 02:00–05:00, NY 07:00–10:00 NY time (L826–828); SB windows 03–04 / 10–11 / 14–15 (L829–831)। |
| Candle patterns | আছে | Pin bar, engulfing (L1216–1219), doji (L1222), inside bar (L3199), CISD (L1234), IFC (L1268)। |
| Displacement / momentum | আছে | `body ≥ dispFactor×ATR` (1.2 default) — zone creation, LT, opposing-displacement invalidation। |
| Custom scoring | আছে | MODULE 16: 0–100 alignment score (Context 30 / Liquidity 20 / POI 20 / Trigger 20 / Execution 10) + SB bonus ≤15 → clamp 100। Tier C/B/A/A+। LT engine-এর আলাদা 0–100 score। |
| News calendar | **নেই** (fixed clock windows) | L901: "NOT a live calendar" — তিনটি hard-coded session string। |
| SMT divergence, true-day-open, DST handling, weekend gap | **নেই** | header L52–54 "DEFERRED"। |
| Backtest / strategy() | **নেই** | এই ফাইলে নেই। Twin strategy file folder-এ নেই। |

---

## 2. Indicator Logic Inventory (module by module)

Column meanings: **Actual implementation** = কোডে যা আছে · **Signal purpose** = pipeline-এ এর কাজ · **Potential weakness** = Phase 2/3-তে investigate করার point (এখনো confirmed নয়)।

### MODULE 1–3 · Inputs, constants, candle anatomy

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Symbol profile (L653–661, L742, L756, L1142–1146, L1164) | `profIdx` 0–4; Manual হলে user input, নইলে FX/XAU/Index/Crypto preset for `extPiv`, `dispFactor`, `minZoneAtr`, 6 Advanced constants, `CHOP_RANGE_ATR` | সব ATR-scaled threshold-এর একটা preset | Header-ই বলছে "opinions, not measurements" (L630–633)। কোনো calibration evidence নেই। |
| Gating ATR (L1192–1194) | `atr = min(atrRaw, 1.5 × SMA(atr,50))` | প্রতিটি distance/threshold এটা পড়ে | Cap-এর পরে এক news candle-এর ATR নিচে থাকে, কিন্তু প্রকৃত volatility বেশি — stop padding ছোট হতে পারে। |
| Spread model (L1197–1199) | `spr = spreadIn × mintick`; `hiA = high + spr`, `loA = low + spr` | Long fill at ask, short SL/TP at ask | Default 0 = off। Chart = bid assumption শুধু OANDA-type FX feeds-এ সত্য। |
| Pin / engulf / doji (L1216–1222) | wick ≥ 2×body, opposite wick ≤ body, wick ≥ 0.3 ATR; engulf body > prior body | `zoneBullConf/BearConf` execution confirmation | Pin-এর কোনো location requirement নেই (FIX-X9 শুধু machine path-এ anchor-tie করে)। |
| CISD (L1234–1259) | ≥2-candle opposite run-এর origin open-এর মধ্য দিয়ে displacement close (body ≥ 0.5 ATR, outer-30% close); neutral candle (body ≤ 10%) run void | Execution confirmation; optional shift (`shiftSrc`); SB shift; exit trigger | `_cisdDnDone` latch একবার per run — run restart হলে reset; neutral candle definition কড়া (10%)। |
| IFC (L1265–1269) | Prior 3-bar extreme-এর ≥0.25 ATR বাইরে wick, close past prior mid, body ≥ 0.5 ATR, outer-30% close | Confirmation + SB rejection | 3-bar pool খুব ছোট — এটা "institutional" নয়, intrabar reversal candle। |

### MODULE 4 · Pivots, EQ pools, trendline anchors

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Internal pivots (L1278–1279) | `ta.pivothigh/low(5,5)` | `lastRes/lastSup`, sweep levels, RB, doji-at-level | Confirmation delay = 5 bars; level update হওয়ার আগে ওই level-এ sweep হলে ধরা পড়বে না (Phase 2: timing)। |
| EQH/EQL pools (L1318–1329, L1348–1359) | **শুধু consecutive দুই pivot** `|ph − prevPH| ≤ 0.15 ATR` হলে pool; max 8/side; age-out 240 bars | Pool kind 2 (engineered liquidity); SB preferred pool | মাঝে একটা pivot থাকলে equal highs miss হয়। Pool consumed হলে array থেকে remove — "swept" ও "broken" দুটোই delete। |
| Trendlines (L1332–1342, L1360–1370) | শেষ দুই pivot high (lower) / low (higher) → candidate line; ≥1 touch হলে re-anchor বন্ধ | TL sweep trigger (MODULE 14) | একদিকে একটাই line; validated line পুরনো হয়ে গেলেও `tlMaxAge` পর্যন্ত থাকে। |

### MODULE 4B · Session clock + SB windows

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Session flags (L1388–1398) | `time(tf, ses, "America/New_York")` | killzone gate, session H/L tracker, sesPts | DST handled by tz string — ঠিক আছে; কিন্তু `f_sesMin` (L1409) midnight-crossing window support করে না (header বলছে SB windows কেউ cross করে না — সত্য)। |
| SB window id (L1433–1437) | 2 = NY AM (priority), 1 = London, 3 = NY PM; `sbCtx` = window or pre-window grace (15 min) | SB arming path, score bonus, clocks | `sbNowMin` bar OPEN time থেকে — M15-এ 09:45 bar pre-window, ঠিক। |
| News windows (L910–912, L1442) | 3 fixed sessions; `newsAllowSb` NY-AM SB-কে window #2 থেকে exempt | `newsOK` final gate | Calendar নয় — user-কে প্রতি সপ্তাহে edit করতে হবে। |
| SB range boxes (L1460–1485) | window open→close high/low box, keep 2 | display only | — |

### MODULE 5 · Liquidity engine

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Swing sweep (L1510–1531) | `low < lastSup and close > lastSup` **or** multi-bar reclaim (`supBroken` latch + close back within 4 bars); once-per-level via `sslSpentLvl`, re-arm after 3 ATR travel or new pivot | Primary arming event | Reclaim test `close > lastSup` — spread/noise tolerance নেই; multi-bar path-এ latch clear হয় না (structure engine already booked break) — Phase 2: structure vs sweep conflict। |
| Sweep quality (L1533–1556) | 1 weak → 2 valid (`firm` close ≥ level + 0.125 ATR **or** penetration ≥ 0.25 ATR) → 3 strong (+outer-30% close + body ≥ 0.5 ATR); volume bump capped 3 | `minArmQual` (2), A+ needs RAW ≥ 3, score bonus | Grade 2 খুব সহজ (penetration OR firm)। Header নিজেই বলছে "trivially earned" (L1548)। |
| RAW vs EFF (L1572–1575, L1969) | RAW = candle-earned, never rewritten; EFF = RAW + MSS upgrade → 4 (within TRIG_LOOK of raid) | A+/score read RAW; arming/chop bypass/SB read EFF | — |
| Pool kind (L1578–1579) | 1 swing · 2 EQ · 3 PD/PW · 4 session | SB `sbPoolPref`, mcTier A+ needs ≥2 | Same-bar multi-pool: পরের stamp wins kind (session > PD > EQ > swing in source order)। |
| PDH/PDL/PWH/PWL (L1670–1708) | `high[1]/low[1]` on D and W, lookahead_on; one raid per level until level changes | Kind 3 pool, SB target scan, plot | Daily bar boundary = exchange day (not NY midnight for all symbols)। |
| Session H/L tracker (L1720–1797) | Per session: closed session H/L stored; raid = wick through + close back; break = close through; latch clears after 1 ATR walk-off | Kind 4 pool (London/NY arm, Asia score-only unless SB ctx) | `sesHiBroke/sesLoBroke` (L1796–1797) **কোথাও পড়া হয় না** → dead। |
| Sweep in play (L1848–1865) | within `sweepLook` (12; +5 in SB ctx) bars **and** reclaim still holds **and** within 3 ATR | `sslInPlay` → MSS, machine arm, score, LT | — |
| Break latch (L1868–1873) | once-per-level `close > lastRes` | feeds structure, IB, LT | — |

### MODULE 6 · Structure

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| `f_structure` (L1883–1925) | dir ∈ {0,1,−1}; BOS = displaced close through latest pivot in trend dir; CHoCH = displaced close through protected swing (leg extreme at last BOS); `legLo/legHi` reset on event | `msDir` (internal, pivLen 5), `extDir` (external, extPiv 12) | Displacement filter `body ≥ 0.5 ATR` applies to **break candle only**; a 3-bar grind through the level with small bodies কখনো BOS হবে না (latch set হয়ে যায় line 1870 regardless) — Phase 2: silent break। |
| MSS (L1955–1970) | external CHoCH (default) + `sslInPlay` + EFF quality ≥2; upgrades EFF to 4 if within TRIG_LOOK | Highest trigger (12 pts), SB shift grade 2, chop exemption | Internal CHoCH as MSS only if `mssNeedExt = false`. |
| Trigger memory (L1975–2010) | last-bar stamps for CH/BOS/MSS/CISD/Disp; `recentX = within TRIG_LOOK (10)` | tier `hasTrig`, score decay, dashboard | — |
| Structure chips (L2017–2030) | display only, priority MSS > CHoCH > BOS > internal | — | — |

### MODULE 7 · HTF data

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| EMA bias (L2035–2044) | `(close > EMA50 ? 1 : −1)[1]` on `biasTf` (default 60) and "D" | `htfB`, dashboard | Daily bias `bD` **শুধু dashboard-এ** দেখানো হয়; কোনো gate পড়ে না। |
| HTF structure (L2051–2114) | `f_htfStruct` = same protected-swing engine on bias TF (pivot 5, disp 0.5 ATR), returns `[dir, protLo, protHi][1]` | `hsDir` → `htfB`; `hsProtLo/Hi` → setup invalidation (FIX-T6) | Comments L2033/L2050 বলছে "lookahead off", code `lookahead_on` — **doc drift** (FIX-Y1-এর পর comment update হয়নি)। |
| Combined bias (L2118–2124) | EMA only / Structure only / Both (disagree → 0); `biasOkL/S` with `neutralMode` | arm gate, final gate, LT, SB entry, tier A+ (needs `htfB > 0`) | Neutral + "Follow chart structure" → `extDir` decides। |

### MODULE 8–9 · Engineered-liquidity memory, HTF engines

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Eng-liq memory (L2134–2140) | last bar of any EQ/session/PD/PW raid; recent within `sweepLook` | +5 liquidity score; LT score | — |
| HTF auto map (L2148–2162) | 1→15, 5→60, 15/30→240, 60+→D; `htfLive = htfTf != chart TF` | CRT/TBS/POI/FEM source | On D chart `htfLive = false` → HTF engines silently off. |
| HTF CRT / Turtle soup (L2171–2195) | 3-candle CRT and 20-bar TBS evaluated on HTF closed bars, `[1]`-shifted; fires on first chart bar of new HTF bar | `sigHCrtLong/Short`, `sigHTbsLong/Short` | **No own stop** → fallback `min(low, low[1]) − pad` (L4572)। |
| HTF FVG POI registry (L2207–2300) | up to 3 live FVGs/side on HTF; visit-count freshness; invalidate on HTF close through far edge, age 40, visits > 2 | `hPoiB/S` → FEM, machine `tapHtf`, NEXT level, SB target | Only the **most recent 3** kept (oldest dropped even if untested, L2256). |
| POI picker (L2310–2340) | nearest untested within 2×POI_NEAR window else nearest | — | — |
| ADR (L2346–2362) | `SMA(D range,10)[1]`; today's range tracked on chart; exhausted ≥1.2×; chase = pos ≥0.7 / ≤0.3 | −10 ctx, no A+ | `newDay = ta.change(time("D"))` = exchange day. |

### MODULE 10–11 · Dealing range, regime

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Dealing range (L2395–2418) | anchor = older of last two external (or internal) pivots; range = `highest/lowest` since anchor (5–500 bars); `pdPos` clamped; OTE 62–79% retrace **only when range direction matches** (`bullRange` = high after low) | ctx +5, A+ test, `mcPdOK`, SB `sbReqPD`, OTE score | Header-acknowledged step when a new pivot confirms (L2388–2394). `rangeHolds` needs ≥2 ATR. |
| SB range lock (L2429–2457) | range frozen at SB window open while SB setup/trade live; fallback to live if price >15% outside | SB P/D tests | — |
| Regime (L2469–2520) | TRENDING = ext dir + ext BOS within 40 bars, no opposing CHoCH; TRANSITION = ext CHoCH within 40; CHOP = none of those + ext range <6 ATR + leg <6 ATR + price inside + no 6-ATR thrust; else RANGING | chop gate (`useRegime`), LT −10, dashboard | Four fixes stacked (T12/T16/N1b/P1-8); no empirical validation that "CHOP" bars underperform. |
| `instSweepL/S` (L2527–2528) | RAW ≥3 **and** recent MSS | chop exemption at arm and final gate | — |

### MODULE 12 · FVG registry

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Creation (L2550–2562, L2580–2591) | 3-candle gap, no min size, no displacement requirement for registry; box drawn; keep 4/side | visuals, IFVG source | Any 1-tick gap enters registry (size filter only at zone/SB level). |
| Lifecycle (L2594–2653) | partial = any wick inside; **full fill = wick to far edge (`low <= f.bot`) or close through** → delete; inversion (IFVG) on close through if `useIfvg`; age 120 | — | Registry does **not** track 50% CE state; "full fill" = wick touch, not close — Phase 3: FVG definition check. Inverted gap removed from one array and pushed to other **while iterating the first** (L2615–2616) — Phase 2: index safety. |
| Latest-FVG tracker (L2660–2691) | last bull/bear FVG + whether leg candle `[1]` was displacement (`min(dispFactor, sbDispAtr)` = 0.8 ATR) | machine anchor (`cFvgB*`), FEM, SB `sbFvgOk` | Cleared only on close through bottom; a new FVG overwrites regardless of age. |

### MODULE 13 · Zone engine

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Zone type (L2700–2712) | box + flags: touched, tapped50, signaled, score 2/3, kind SD/OB/RB/BRK/MIT/IFVG, tests, wasIn | — | — |
| S/D creation (L2905–2960) | FVG + displacement candle `[1]` (body ≥1.2 ATR, `volOK[1]`); zone = `low` → `max(high[2], low − 2 ATR)`; ★HP (score 3) if `close[1]` broke `lastRes`; dup check same side; min height 0.15 ATR; band claim vs opposite side | POI for machine tap, NEXT level, zone-50% signal | "Break of originating structure" = internal pivot break, not external. Zone top = `low` of **current** bar (the FVG bottom edge of gap), i.e. zone sits **below** the gap — Phase 3: verify geometry matches S/D doctrine. |
| OB companion (L2930–2935) | candle `[2]` (opposing colour) range, capped 2 ATR, only when `obTop <= zBot` | kind "OB", LT `obNear` | OB only created together with S/D; no standalone OB detection. |
| Rejection block (L2963–2994) | pivot wick that swept prior 10-bar extreme + displacement away ≥1.2 ATR; max 2/side | kind "RB" | — |
| IFVG → zone (L3005–3026) | inverted FVG becomes zone kind "IFVG", score 2 | POI | — |
| Lifecycle / 50% tap (L2784–2869) | violate (close through far edge) → flip to BRK (if recent sweep + structure) else MIT, second violation delete; tests counted on leave+return; spent after 2 tests; **50% tap edge-triggered** → if confirmation candle within 5 bars and wick still in zone → `sigSDLong/Short`, SL beyond zone + 0.25 ATR | `sigSD*` engine signal; `zoneInvalidatedUp/Dn` | `zoneInvalidatedUp/Dn` returned & assigned (L2873–2874) but **never read** → dead (FIX-T1 replaced it). Flip check `recentSsl and recentStructUp` (L2808) uses sweep of the **same** side as the new demand — Phase 3: breaker definition. |
| Cap (L3032–3045) | newest 6/side, RB ≤2/side | — | — |
| NEXT zones (L3050–3096) | nearest unsignaled demand with bottom ≤ close / supply with top ≥ close; HTF POI competes if height ≤4 ATR | `nbTop/nsBot` → score POI, TP2 clamp, p7Arm, POI conflict | `touchNextBuy/Sell` alert = first wick into band. |

### MODULE 14 · Trigger-candidate engines

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| CRT (L3112–3118) | c1 range ≥1.2 ATR; c2 wicks beyond c1 low/high ≥0.3 ATR and closes inside; c3 displacement close beyond c2 extreme (body ≥0.5 ATR); cooldown 10 | `sigCRT*`, SL = c2 extreme ± pad | Entry at c3 **close** (after the move) — Phase 4: late-entry check. |
| Turtle soup (L3122–3129) | wick below 20-bar low (age 4–60), close back above, bull bar, close ≥ mid-range; SL = low ± pad | `sigTBS*` | Overlaps with swing sweep (same event, different level source) — duplicate-signal candidate. |
| Trendline sweep (L3132–3195) | touches edge-triggered; sweep = wick through validated line (≥2 touches) + optional confirmation | `sigTL*`, SL = bar extreme ± pad | — |
| Inside bar (L3199–3249) | mother = break candle (body ≥1.0 ATR); inside bar on correct half; break within 4 bars with strong close, `structDir`, `biasOk` | `sig3*` | **No own stop** → fallback. |
| Doji reversal (L3252–3273) | ≥3 dojis in 5 bars, compressed, at level, drift, level raided, confirmation + displacement, `ctxBias` | `sig4*` | **No own stop** → fallback. |

### MODULE 15 · Fractal Entry Model (FEM)

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| FEM chain (L3280–3346) | 0 → 1 tap HTF POI (`htfLive`) → 2 any shift (cisd/choch/bos/mss, **internal included**) → 3 lock first chart FVG after tap → retest wick + close inside + confirmation → `sigFEM*`; expire 40 bars; die on close through FVG | engine signal; stop = min(low, FVG bottom) − pad | Stage 2 accepts bare `bosUp`/`cisdUp` (weaker than machine's `shiftSrc`). FEM and machine can fire on the same structure → duplicate-signal candidate (both go through `anyLong`, same bar → merged label, one tracker). |

### MODULE 15A / 16 · Direction lock, score, tier

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Direction lock (L3384–3386) | `dirLock` = open trade dir, else setup ≥ stage 2 side | arm, final gate, LT | — |
| POI source for score (L3423–3440) | stage ≥2 → own anchor; else NEXT zone | — | — |
| POI conflict (L3457–3463) | next demand & supply within 1 ATR (chart-TF only) → side with bias keeps points; tie → both 0 | — | — |
| Score (L3468–3520) | Ctx: HTF 10/5/0 + ext 10 + ses 5/3/2/0 + P/D 5 − ADR 10 · Liq: inPlay 10 + eng 5 + RAW≥3 5 · POI: in 10/near 5 + fresh 5 + OTE 5 · Trig: max(MSS 12, CH 9, BOS 5) decayed + CISD 8 if separate, cap 20 · Exec: retest 5 + conf 5 · SB ≤15, clamp 100 | `minScore` gate reads **base** (no SB); label prints full | Header: "ALIGNMENT, NOT WIN PROBABILITY" (L3394). Correlated factors (sweep in play ↔ MSS ↔ SB window gate ↔ liquidity bonus) — Phase 6 dedup. |
| Tier (L3527–3550) | C=1; B = trig + (liq≥10 or poi≥5); A = liq≥10 + poi≥10 + trig + exec≥5; A+ = A + htfB dir + session + RAW≥3 + P/D (SB-locked if tagged, waived if `not rangeHolds`) | `tierMode` display filter, counters, alerts | Three different P/D tests exist: `f_tier` (waives on tight range), `f_mcTier` (no waiver, L4421), `mcPdOKL` (waives on bias+structure, L4399) — **conflicting-rule candidate**. |

### MODULE 16B · Liquidity Trap engine

| Component | Actual implementation | Signal purpose | Potential weakness |
|---|---|---|---|
| Patterns (L3764–3769) | Long: LT-1 compression→expansion break, LT-4 shadow-high. Short: LT-2, LT-3 lower-wick pool, LT-5 weak break, LT-6 structural trap, LT-7 supply rejection | arm per-direction trap machine | **2 long vs 5 short patterns** — asymmetric; all built on `brokeUp` (upside break). No mirrored downside-break trap set. |
| Trap machine (L3813–3943) | IDLE → WAITING (level, patterns merged) → retest (long: wick to level +0.5 ATR; short: close back below) → confirmation on a **later** bar (rejection/IFC/CISD/shift) + ctx gates + lock + class floor → CONFIRMED (cooldown 10); expire 25; invalidate on displacement beyond 1 ATR | `sigLT*`, SL = min(low, level) ∓ pad | — |
| LT score (L3790–3808) | +10 base, +20 sweep, +15 rej, +20 shift, +10 S/D, +10 FVG, +10 OB, +10 disp, +10 retest, +15 HTF; −10 chop, −20 counter-trend, −15 wrong OTE, −5 low vol, −10 no liq, −15 both armed | class MEDIUM 50 / HIGH 70 / VERY HIGH 85; floor HIGH default | Second, independent 0–100 scale alongside MODULE 16 — same inputs counted twice (sweep, shift, FVG, OB). |
| LT veto (L4538–4539) | waiting trap mutes opposing **engine-only** bars | — | — |
| Dead exports | `ltLLevel`, `ltSLevel`, `p3PoolBar`, `p4PoolBar` returned (L3754, L3943) never read | — | dead |

### MODULE 17 · Master setup state machine (primary signal path)

| Stage | Transition (long side, L4058–4238; short mirrored L4241–4352) | Evidence |
|---|---|---|
| 0 → 1 SWEPT | `sslInPlay` + arm bar (sweep bar, or grace ≤3 bars non-SB / ≤5 SB, once per sweep) + (EFF qual ≥2 or SB gate) + `biasOkL` (if `armNeedHtf`) + `lockOkL` + not chop (unless inst sweep / SB bypass). Stamps `suLSweepLvl/Ext`, SB tag | L4119–4134 |
| 1 → 3 (fastShift) | `sslInPlay` + displaced shift (`shiftUpOk` = MSS/ext CHoCH default; SB: `sbShiftUp` = MSS/eCHoCH/(iCHoCH or CISD + 0.8 ATR body)) → anchor cleared, waits for shift-leg FVG | L4137–4143 |
| 1 → 2 AT POI | `tapZone` (wick into NEXT demand + close ≥ bottom, no POI conflict) or `tapOte` (if input) or `tapHtf` (HTF POI) | L4144–4152 |
| 2 → 3 SHIFTED | `shiftUpOk` (SB: `sbShiftUp`); lock FVG if `cFvgBBar >= suLBar` (SB: must be displacement FVG ≥0.10 ATR) | L4156–4170 |
| 3 → 4 ENTRY | anchor set; `ripeL` (bar after shift and after FVG bar); SB: window + CE touch by ask (`loA <= ceL`) or proximal + rejection, HTF + P/D (locked range). Non-SB: CE touch (if `mcCeOn`) or proximal wick + confirmation closing above CE in outer 30%. Close must hold above anchor bottom. Plan price = CE or `min(close, anchorTop) + spr`. Stop = raid wick (sweep extreme) if fits cap else anchor stop | L4171–4238 |
| Invalidation (any stage) | close < sweep extreme; stages 1–2 close < sweep level − 0.25 ATR; opposing displacement (stage 3 exempt if close holds above anchor); stage 1 opposite quality sweep; own-anchor violated (zone anchor); HTF protected low; SB window close; stage clocks 20/15/20 (SB 12/8/10) | L4062–4115 |
| 4 → 0 | when tracker flat (`trdDir == 0`) and no new signal (L4901); final-gate mute returns to 3 with reason (L4460) | — |

**Potential weakness (Phase 2/4):** Stage-2 zone anchor = `nbTop/nbBot` at tap time; if a HTF tap (`tapHtf`) happened, anchor stays `na` → stage 3 waits for an FVG; a zone-anchor setup with no FVG uses proximal edge + confirmation only (no CE). Entry at stage 4 requires `close > suLAnchorB` **this bar** — a CE touch that closes below the anchor bottom dies as "anchor FVG violated" on the same bar (L4220), which is correct for a violated gap but means a deep wick fill is never counted.

### MODULE 18 / 18B · Final gate, conflict, viability

| Gate | Rule | Evidence |
|---|---|---|
| `longOK` | `biasOkL · lockOkL · kzOK · newsOK · dowOK · cooldown(15) · chopOKL · sbOnlyOK · govOK(4/day, 2 losses) · mcPdOKL · base score ≥ 50` | L4401 |
| SB override | SB entry ignores cooldown and `mcPdOK` only | L4405 |
| Machine tier | floor A; A+ if RAW≥3 + htfB + MSS + P/D + pool≥2 + session + ADR | L4416–4431 |
| Engine tier | `tierLong ≥ minRank` (A default), +1 if SB live & Down-weight, muted if Suppress | L4472–4475 |
| Conflict | SB(3) > machine(2) > engine(1); equal rank → both muted | L4508–4527 |
| LT veto | engine-only bars muted while opposite trap waits | L4538 |
| Viability | stop of surviving engine (priority MC > FEM > SD > CRT > TBS > TL > LT; **IB/Doji/HTF-CRT/HTF-TBS → 2-bar fallback**); slip guard 0.5 ATR (waived for CE); risk cap 1.5 ATR (reject/clamp); TP2 = 2R clamped to first opposing POI; net RR ≥1.5 incl. `costTicks`; roll back machine stage on fail | L4560–4628 |

### MODULE 19 · TP/SL + trade tracker

| Component | Actual implementation | Evidence |
|---|---|---|
| Entry price | Machine/SB: plan price (CE or anchor edge + spread). Engine & confirmation-candle machine: **label prints `close`**, tracker fills at **next bar open** (+spread for long) after re-validating slip/risk/RR | L4566, L4642, L4709–4756 |
| Ladder | TP1 = 1R; TP2 = 2R clamped; TP3 = max(3, rr+1)R, or liquidity target (next supply/`lastRes` if ≥2R), SB: nearest pool ≥ TP2 (session H/L, PDH/PWH, next POI) | L4929–4975 |
| Exits (non-SB) | SL first (pessimistic), TP1 → SL to BE + max(0.15 ATR, 15% of TP1 dist), TP2 closes (or runner to TP3 if `nonSbTp3`) | L4758–4812 |
| Exits (SB) | + trail behind external protected swing after TP2 (never through last 2 bars), TP3, structure exit (opposing MSS, or CHoCH/CISD if entry shift was ≤ grade 1), time exit at window close if TP1 unhit (full / partial-BE) | L4813–4885 |
| Time stop | 80 bars → EXPIRED | L4891 |
| One trade at a time | new signal while trade open → `cntUntracked`, stage stays ACTIVE | L4917, L4997 |
| Counters | A, A+, L, S, TP1/2/3, SL, exp, untracked, SB entries, day book | L4675–4688, L5000–5004 |

### MODULE 20–23 · Visuals, dashboard, debug, alerts

| Component | Actual implementation | Evidence |
|---|---|---|
| Plots (8) | lastRes, lastSup, protLowE, protHighE, pdh, pdl, pwh, pwl | L5009–5020 |
| plotchar (12) | SSL/BSL ◆, EQ ◈, PD/PW ◇, TL ✕ ×2, session raid ▿▵, LT retest ◦ ×2 | L5023–5042, L3949–3950 |
| bgcolor (3) | killzones (merged), SB band, news | L5046–5052 |
| Merged signal label | one label/direction/bar: tier · score (base) + engine list | L5059–5097 |
| Trade plan | E/SL/TP1/TP2/TP3 lines + labels, RR net, ≈units | L5106–5159 |
| Last-bar drawings | HTF POI boxes, FEM FVG, machine anchor (CE), SB CE line, SB target, NEXT buy/sell | L5162–5311 |
| Dashboard (12 rows) | regime, bias (EMA·D·struct→combined), struct/sweep, range pos, next demand/supply, trigger/FEM, setup L/S, alignment, session/SB, trade, verdict (names blocking gate) + ADR | L5366–5456 |
| Debug table (5 rows) | sweeps raw/eff/kind, machine reasons, score components, counters, LT/SB/day | L5462–5486 |
| alertcondition (30) | 8 signal, 4 setup lifecycle, 3 trade, 2 trigger, 4 liquidity, 3 POI, 2 context, 3 LT, 1 SB | L5494–5574 |
| alert() feed | journal line `LQJRNL|…` per signal (L5548), LT BUY/SELL (L5565, 5567), SB entry/BE/time/struct/gone (L5580–5598) | — |

---

## 3. Every BUY / SELL source (11 per side) → one `anyLong` / `anyShort`

```
anyLong  = sigMCLong (machine; sub-flag sbFireL = SB path)
         | sigSDLong   (demand zone 50% tap + confirmation ≤5 bars)
         | sig3Long    (inside-bar breakout)
         | sig4Long    (doji reversal)
         | sigTLLong   (trendline sweep)
         | sigCRTLong  (chart-TF CRT)
         | sigTBSLong  (chart-TF turtle soup)
         | sigHCrtLong (HTF CRT, first chart bar of new HTF bar)
         | sigHTbsLong (HTF turtle soup)
         | sigFEMLong  (fractal entry model)
         | sigLTLong   (liquidity-trap LT-1 / LT-4)
```
(L4497–4498; short side mirrored.) সবগুলোই `confirmed` (bar close) gated — কোনো signal intrabar commit হয় না। Label ও alert signal bar-এই; tracked fill engine-এর জন্য **পরের bar open**।

**Stop ownership:** MC, FEM, SD, CRT, TBS, TL, LT — নিজের stop। **IB, Doji, HTF-CRT, HTF-TBS — কোনো stop নেই**, 18B-তে `min(low, low[1]) − 0.25 ATR` fallback (L4572–4575)।

---

## 4. Signal pipeline — raw OHLC → final signal (trace)

```
OHLC ──► M3 candle anatomy (ATR cap, pin/engulf/doji, CISD, IFC)
      ├─► M4 pivots(5) ──► lastRes/lastSup ─┬─► M5 sweep (+EQ, PD/PW, session) ──► quality 1–4, kind 1–4
      │                                    │        └─► sslInPlay / bslInPlay (reclaim holds, ≤12 bars, ≤3 ATR)
      │                                    └─► M5 break latch ──► M6 internal structure (BOS/CHoCH)
      ├─► ext pivots(12) ──► M6 external structure (eBOS/eCHoCH, protected swing, extDir)
      │                         └─► MSS = eCHoCH + sweep in play  ──► EFF quality → 4
      ├─► M7 HTF: EMA bias + HTF structure ──► htfB ──► biasOkL/S (neutralMode)
      ├─► M9 HTF FVG POI (3 slots) ──► hPoiB/S ──► FEM tap · machine tapHtf · NEXT level
      ├─► M10 dealing range ──► pdPos, OTE  ──► ctx +5, A+, mcPdOK, SB lock
      ├─► M11 regime ──► chop gate
      ├─► M12 FVG registry + latest FVG ──► machine anchor (CE)
      └─► M13 zones (S/D, OB, RB, IFVG, BRK/MIT) ──► NEXT buy/sell, 50% tap signal, POI tap
                                   │
   M17 MACHINE:  0 ─sweep in play + arm gates─► 1 ─POI tap─► 2 ─shift─► 3 ─retest/CE touch─► 4 (sigMC)
                     └──────── fastShift: displaced shift while sweep in play ─────────┘
   M14/15/16B ENGINES: CRT · TBS · TL · IB · Doji · HTF CRT/TBS · FEM · LT-traps  (candidates)
                                   │
   M16 score (0–100 base + SB≤15) · tier C/B/A/A+ · mcTier A/A+
                                   │
   M18 gate: bias · lock · killzone · news · day · cooldown · chop · SB-only · governance · P/D · minScore(base)
             machine tier ≥ A (SB ≥ sbMinTier) · engine tier ≥ A (+1 if SB live) · conflict rank · LT veto
                                   │
   M18B viability: stop pick · slip guard · risk cap · TP2 clamp to POI · net RR ≥ 1.5 · rollback on fail
                                   │
   anyLong / anyShort ──► M19 tracker (next-open fill for engines) ──► M20 label/plan ──► M23 alerts + journal
```

---

## 5. All 219 inputs — group, name, purpose

| Group | Inputs (name = default) | Purpose |
|---|---|---|
| General (6) | `pivLen`=5, `extPivIn`=12, `atrLen`=14, `biasLen`=50, `showLevels`, `symProfile`=Manual | pivot sizes, ATR, EMA bias length, key-level plot, preset |
| HTF context (9) | `biasFilter`=60, `biasMode`=Structure+EMA, `htfStructPiv`=5, `htfProtInval`=on, `neutralMode`=Follow chart structure, `useHtfCrt`=on, `htfSel`=Auto, `hPoiMaxAge`=40, `hPoiMaxTouch`=2 | bias TF/source, neutral handling, HTF engines TF, HTF POI life |
| Liquidity (8) | `showSweeps`, `sweepLook`=12, `showEq`, `eqTol`=0.15, `eqMaxAge`=240, `minArmQual`=2, `reclaimBars`=4, `showPdwl` | sweep memory, EQ tolerance/age, arm quality, multi-bar sweep |
| Structure (4) | `showStruct`, `structDisp`=0.5, `showProt`, `mssNeedExt`=on | break body, protected swing plot, MSS definition |
| FVG (4) | `showFvg`, `fvgMaxKeep`=4, `fvgMaxAge`=120, `useIfvg`=on | registry size/age, inversion |
| S/D/OB (10) | `showZones`, `dispFactIn`=1.2, `maxZoneAtr`=2.0, `maxZones`=6, `showOB`, `confirmWin`=5, `showFlip`, `showRB`, `minZoneIn`=0.15, `zoneMaxTests`=2 | zone creation/size/caps, 50% confirmation window, flips, freshness |
| Next level (7) | `showNextLvl`, `nextLvlAnchor`=Proximal, `nextLvlBox`, `nextLvlPct`, `nextLvlBack`=60, `nextInclHtf`=on, `hPoiNextMaxAtr`=4.0 | NEXT buy/sell marker display + HTF candidacy |
| CRT/TBS/CISD (9) | `showCRT`, `crtRangeAtr`=1.2, `crtDispAtr`=0.5, `showTBS`, `tbsLen`=20, `tbsAgeMin`=4, `tbsAgeMax`=60, `cisdAsConf`=on, `sigCooldown`=10 | trigger engine thresholds, CISD as confirmation, engine cooldown |
| IB/Doji (6) | `showS3`, `ibBodyAtr`=1.0, `showS4`, `dojiPct`=25, `dojiMin`=3, `minWickAtr`=0.3 | inside bar / doji engine, wick size (also used by pin, CRT, RB) |
| Trendlines (5) | `showTL`, `tlSweepEnt`, `tlNeedConf`, `tlTouchMin`=0, `tlMaxAge`=150 | TL engine |
| FEM (3) | `useFEM`, `femWait`=40, `showPoi` | fractal model on/off, expiry, HTF POI boxes |
| Dealing range (1) | `rangeSrc`=External | anchor swings |
| Sessions (9) | `useKZ`=off, `paintKZ`=off, `showSesHL`, `asiaSes`, `lonSes`, `nySes`, `sbSesLO`, `sbSesAM`, `sbSesPM` | killzone gate/paint, session strings |
| SB setup (18) | `sbEnable`=on, `sbUseLO/AM/PM`, `sbPreMin`=15, `sbQualLO`=3, `sbQualAM`=2, `sbQualPM`=3, `sbPoolPref`=on, `sbAsiaPool`=on, `sbChopBypass`=on, `sbKillAtEnd`=on, `sbLiqWait`=12, `sbPoiWait`=8, `sbRetWait`=10, `sbFvgMinAtr`=0.10, `sbDispAtr`=0.8, `sbReqMss`=off | SB arming path |
| SB entry (6) | `sbEntryMode`=CE preferred+proximal, `sbReqHtf`=on, `sbReqPD`=on, `sbMinTier`=A, `sbSuppress`=Down-weight, `sbOnly`=off | SB entry rule, hierarchy |
| SB exits (6) | `sbTimeExit`=on, `sbTimeMode`=Full, `sbLiqTgt`=on, `sbStructEx`=on, `sbBeBuf`=0.15, `sbTrail`=on | SB exit engine |
| SB visuals (5) | `sbPaint`, `sbShowBox`, `sbBoxKeep`=2, `sbShowPlan`, `sbDynAlert` | display/alerts |
| News windows (6) | `useNews`=on, `paintNews`, `newsAllowSb`=on, `news1Ses`, `news2Ses`, `news3Ses` | fixed volatility windows |
| Quality / machine (17) | `tierMode`=A and above, `minScore`=50, `masterCd`=15, `useRegime`=on, `liqWait`=20, `poiWait`=15, `retWait`=20, `armGrace`=3, `shiftSrc`=MSS/ext CHoCH, `poiSrc`=Zone/HTF only, `armNeedHtf`=on, `oneDir`=on, `fastShift`=on, `mcEntryMode`=CE preferred, `mcStrictCnf`=on, `mcReqPD`=on, `mcPdWaive`=on | state-machine rules and final gate |
| Risk (14) | `showTrade`, `tpMode`=Liquidity target, `rrMult`=2.0, `maxRiskAtr`=1.5, `riskMode`=Reject, `stopTier`=on, `minRR`=1.5, `costTicks`=0, `spreadIn`=0, `riskMoney`=0, `tp1Pct`=50, `slipGuard`=0.5, `maxTrdBars`=80, `nonSbTp3`=off | plan geometry, costs, tracker |
| Volume (4) | `useVol`=off, `volLen`=20, `volMult`=1.3, `volQual`=on | optional relative volume |
| ADR (3) | `useAdr`=on, `adrLen`=10, `adrMax`=1.2 | exhaustion penalty |
| Governance (4) | `useGov`=on, `maxTrdDay`=4, `maxLossDay`=2, `tradeDays`=23456 | daily limits, day mask |
| Dashboard (3) | `showDash`, `showDbg`=off, `jrnlEnable`=on | tables, journal alert |
| UI (7) | `uiSizeOpt`, `uiTrans`=25, `uiMicroBig`, `uiDrawOpt`, `uiDashOpt`, `focusMode`=on, `focusAtr`=4.0 | display |
| Advanced (8) | `nearLvlIn`=0.25, `slPadIn`=0.25, `sweepCtxIn`=3.0, `poiNearIn`=1.5, `trigLookIn`=10, `atrCapIn`=1.5, `REGIME_LOOK`=40, `chopRngIn`=6.0 | ATR-scaled constants (ignored unless profile Manual, except `atrCapIn`, `REGIME_LOOK`) |
| LT engine (11) | `ltEnable`=on, `ltCtxGate`=on, `ltMinCls`=HIGH, `ltVeto`=on, `ltP1`…`ltP7`=on | trap engine master + patterns |
| LT sensitivity (17) | `ltWickAtr`=0.4, `ltWickRatio`=1.5, `ltWickMin`=3, `ltWickWin`=8, `ltClusterTol`=0.6, `ltCmpLen`=5, `ltCmpSens`=0.5, `ltCmpRngAtr`=2.5, `ltExpSens`=1.2, `ltBrkStr`=0.8, `ltNearAtr`=2.0, `ltRetestAtr`=0.5, `ltDispLook`=20, `ltPoolLook`=25, `ltWaitBars`=25, `ltInvAtr`=1.0, `ltCd`=10 | pattern thresholds |
| LT confirmation (3) | `ltReqRetest`=on, `ltReqSweep`=off, `ltReqMtf`=off | hard gates |
| LT score/display (6) | `ltScoreMed`=50, `ltScoreHigh`=70, `ltScoreVHigh`=85, `ltShowSig`, `ltShowMarks`, `ltDynAlert` | class thresholds, display |

**Hidden constants (not inputs, L1147–1170):** `STRONG_CLOSE_PCT` 0.30, `CISD_NEUTRAL_PCT` 0.10, `IFC_LOOK` 3, `BRK_BODY_ATR` 0.5, `IB_WAIT_BARS` 4, `TRADE_BARS` 15, `DOJI_WINDOW` 5, `MAX_EQ_POOLS` 8, `OTE_1/2` 0.62/0.79, `SB_ARM_GRACE` 5, `SB_MEM_EXTRA` 5, `SB_BE_TP1_PCT` 0.15.

---

## 6. Dead code, unused variables, duplicated / conflicting rules (Phase 1 item 6)

| # | Type | Location | Finding |
|---|---|---|---|
| D1 | Dead variable | L1796–1797 `sesHiBroke`, `sesLoBroke` | Computed, never read (v3.6 token pass removed the "session broken" plotchars; the expressions and the `hiBrk/loBrk` tuple fields stayed). |
| D2 | Dead variable | L2873–2874 `zoneInvalidatedUp/Dn` | Returned by `f_zoneUpdate`, assigned to globals, never read. FIX-T1 (own-anchor test) replaced its only consumer. |
| D3 | Dead tuple exports | L3754 `p3PoolBar`, `p4PoolBar`; L3943 `ltLLevel`, `ltSLevel` | Returned, never consumed. Cost = compiled tokens only. |
| D4 | Doc drift | L2033, L2050, L2206, L2343 (+2) comments say `lookahead_off` | Code uses `lookahead_on` everywhere (FIX-Y1). Comments not updated. Risk: a future edit "fixes" the code to match the comment. |
| D5 | Display-only dead input | `bD` (daily EMA bias, L2044) | Only the dashboard prints it; no gate reads it. Not dead code, but a security call that gates nothing. |
| C1 | Conflicting-rule candidate | Three premium/discount tests: `f_tier` pdOk (L3541–3543, waived when `not rangeHolds`), `f_mcTier` pdOk (L4421–4423, **no** tight-range waiver), `mcPdOKL/S` (L4399–4400, waived on bias+structure agreement) | A machine entry can pass the final gate (waived) and still be denied A+ (no waiver) — by design? Phase 2 to decide. |
| C2 | Duplicate-signal candidate | Swing sweep (M5) vs Turtle soup (M14) vs HTF TBS vs LT trap vs machine arm — same wick-through-and-reclaim event feeds up to four signal families | Merged into one label and one tracker per bar, so not duplicate *trades*, but duplicate *evidence* in score/tier (Phase 6). |
| C3 | Duplicate-signal candidate | FEM (M15) stage 2 accepts bare `bosUp`/`cisdUp`; machine requires MSS/ext CHoCH | Same HTF POI tap can produce an FEM entry the machine's own rules would not allow. |
| C4 | Asymmetry | LT engine: 2 long patterns / 5 short patterns, all anchored on **upside** breaks | Short-biased trap set; no downside-break mirror. |
| C5 | Missing own stop | IB, Doji, HTF CRT, HTF TBS | Use the generic 2-bar fallback stop (L4572), not a structural level. |
| N1 | Not a defect, note | `confirmed` gate | `sslSpentLvl` reset (L1512–1515) and `dayHi/dayLo` (L2350) run every tick, but Pine rolls back `var` state per realtime tick, so only the bar-close value persists. Phase 2 will re-check each un-gated `var` write. |

---

**Applied 2026-10-14 → `liqudity_trap_trading.v3.6.1.txt` (BUILD v3.6.1-b1):** D1, D2, D3, D4 cut/corrected; title + dashboard header bumped to v3.6.1; changelog block added under the BUILD stamp. 62 changed lines, zero logic change (C1–C5 untouched — those need Phase 2 verdicts first). Original v3.6 file untouched (md5 `ccb6cf07…`). Not compiled locally — paste into the Pine editor and check the BUILD line shows `v3.6.1-b1`.

## 7. What Phase 1 did **not** judge (reserved)

- Repainting / lookahead per `request.security` call → Phase 2B.
- Whether each "weakness" above is a confirmed defect → Phase 2A.
- Whether S/D, OB, FVG, breaker definitions match doctrine → Phase 3.
- Signal timing (late / premature), stop logic, RR → Phase 4.
- Score factor correlation / validity → Phase 6.
- Any performance number — **none exists**; the strategy twin referenced in the header is not in this folder, so nothing can be measured yet → Phase 7.

**Phase 1 verdict:** ফাইলটা একটা **closed-bar, multi-engine, state-machine-driven SMC/ICT indicator**, যার primary path হলো sweep → POI → shift → retest machine, আর 10টা secondary engine একই gate/score/tier pipeline-এর ভেতর দিয়ে যায়। কোনো RSI/ADX/MACD নেই, কোনো LTF data নেই, কোনো live news feed নেই, কোনো backtest নেই। 4টা dead export + 1 comment drift পাওয়া গেছে; 5টা rule-conflict / duplicate-evidence candidate Phase 2-এ যাচাই হবে।
