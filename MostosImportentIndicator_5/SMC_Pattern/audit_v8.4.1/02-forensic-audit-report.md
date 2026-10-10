# 02 — Forensic Audit Report · SMC / ICT Suite v8.4.1

তারিখ: 2026-10-10 · ফাইল: `SMC_Pattern/SMC_v8.4.1.txt`
যাচাই: পুরো source পড়া; প্রতিটা finding-এর লাইন, root cause, reproduce, impact, fix। **Confirmed defect** = code-এ প্রমাণ আছে। **Design weakness** = code যা লেখা তাই করে, কিন্তু trading logic দুর্বল। যেখানে market behaviour objectively বলা যায় না, সেটা আলাদা করে বলা।

## A. Repainting / future data — ফল: কোনো repaint নেই

| পরীক্ষা | ফল | লাইন |
|---|---|---|
| `request.security` ×3 | সব `expr[1]` + `lookahead_on` (HTF 12-tuple, D, W) → history = live | 2122–2125, 2225–2226 |
| HTF pivot | `ta.pivothigh(..,3,3)[1]` security-র ভিতরে → confirmed HTF pivot, 3–4 HTF bar delay (legit) | 2124 |
| HTF timing | `newHtf = timeframe.change(htfTF)`; `[1]` data = just-closed HTF candle → প্রথম LTF bar-এ process, 1 LTF bar delay (legit) | 2126–2129 |
| LTF pivot | `ta.pivothigh/low(5,5)` → 5-bar delay; pivot confirm-এর আগে close ওই high ছাড়াতে পারে না (pivot definition), তাই break detection miss হয় না | 2218–2219, 1056–1057 |
| FVG | `barstate.isconfirmed` gated (C2) | 1299 |
| OB / KL / RCB / QM / RJB | সব `isconfirmed` gated | 1689, 1803, 1816, 1830, 1837, 1843 |
| Move strength / arrival | `isconfirmed` gated, `var Move mv` | 2267, 2273, 2360 |
| Realtime state | `ctx`/`sx` প্রতি tick mutate হয় কিন্তু Pine var-rollback → confirmed bar থেকে re-run; drawing/alert/signal-state (`sigBar`, `lastIdent`) `isconfirmed` | 3529, 3548, 3666, 3686, 3819–3841 |
| Label ↔ alert ↔ state | তিনটাই final `hasL/hasS` (suppression-এর পরে) পড়ে | 3589–3590, 3626, 3640, 3819–3829 |
| Session / time | NY tz explicit; `nyMid` session string | 2232–2243 |
| Drawing offsets | `f_xb` clamp 495; `f_legOrigin` span ≤490; `obOff+1` ≤490; `off < 500` guards | 1289, 1006, 1695, 1366 |

**উপসংহার:** historical আর live signal এক। Confirmation delay (pivot 5 bar, HTF close, CONFIRMED trigger ≤8 bar) আছে — সেটা repaint নয়। Intrabar কিছু fire হয় না।

Runtime-crash path: `ta.lowest(low, poiNL)` poiNL ≥1 (2725); `ta.highest(high, pdSpanB)` ≥1 (2335); array loops সব size-guarded; reverse-iteration-with-remove safe। **পাওয়া যায়নি।** Token: v8.4.1 header "compile to confirm" — user confirm করেনি।

## B. Confirmed defects

### D1 — Default `TOUCH` mitigation-এ `atBullFvg / atBearFvg` কখনো true হয় না · **P1**

- **লাইন:** mitigation 1316–1323 (`hit = low <= g.top` TOUCH mode → `g.mitigated := true` একই bar-এ); scan 2453–2461 (`not g.mitigated and ... low <= g.top`)। `f_fvg` (2257) scan-এর **আগে** চলে।
- **Root cause:** price প্রথমবার FVG-র top ছুঁলেই mitigated set হয়; scan তার পরে চলে এবং mitigated বাদ দেয়। ছোঁয়ার আগে price ভিতরে না, ছোঁয়ার bar-এ mitigated — তাই flag কখনো true নয়। `50%`/`FULL` mode-এ কাজ করে (upper half / full gap পর্যন্ত)।
- **Reproduce:** যেকোনো chart, default input। Data window-এ `atBullFvg` নেই, কিন্তু effect: `sx.poiFvgL` (2711) কখনো true নয়; `reactBull` (2902) শুধু `zoneOkBull`; `f_conf` zone-over-FVG term (3280) 0; INCOMPLETE check (3462) FVG half dead; POI arm (2705) FVG-only tap অসম্ভব।
- **Impact:** M41 / M46 / M68-এর "FVG reaction" path বন্ধ — এই তিনটা Model A (sweep → displacement → FVG retrace)-র core module। User-এর কাছে মনে হবে FVG retrace trade আসে না।
- **Fix:** scan-এ `(not g.mitigated or g.mitIdx == bar_index)`। একই condition `f_conf`-এ লাগে না (flag পড়ে)। ~+15 token।
- **Regression:** `50%` mode-এ v8.4.1 আর fix-এর atBullFvg সমান; TOUCH mode-এ M41/M46/M68 signal count বাড়বে — আলাদা count।

### D2 — Delayed-resolve sweep (pend path)-এ SL আসল sweep low-এর **উপরে** বসে · **P1**

- **লাইন:** pend set 1497 / 1515 (`L.pend := failedCloseBars` যখন wick ভেদ + close beyond small body); resolve 1485 / 1503 (পরের bar `close < L.price` → SWEEP); `setLoL = poiConfL ? lowTap : low` 2729 (IMMEDIATE → **এই** bar-এর low); `f_stop` sweep branch 3318–3319 `sl = x − buf`; zone branch 3317 `min(zz.bottom, x)`।
- **Root cause:** SWEEP flag resolve হয় wick bar-এর 1–2 bar পরে; `fv.sweptPriceLo` = level, wick-এর extreme কোথাও রাখা হয় না। `x` = resolve bar-এর low।
- **Reproduce:** EURUSD 5m, PDL 1.0850। Bar A: low 1.0842, close 1.0848 (body ছোট, `runBodyMin` fail) → pend 2। Bar B: pin bar low 1.0846, close 1.0856 → SWEEP resolve, M10 fire (`dnWickRatio ≥ 0.5` bar B-তে)। SL = 1.0846 − 0.15 ATR — bar A-র 1.0842 wick-এর **উপরে**। Risk ছোট দেখায় → R:R বড় দেখায়।
- **Impact:** M10 (IMMEDIATE) আর zone-less sweep branch-এর SL market-এর already-printed low-এর ভিতরে; "stop hunt of the stop hunt"। H3 (v8.4.1) zone branch-এ wick ধরেছে, sweep branch-এ ধরেনি। একই কারণে M10-এর "sweep candle must close in own upper half" (P0-E) test resolve bar-এ হয়, sweep bar-এ নয়।
- **Fix:** `Liq`-এ `float wickX = na` (pend set হওয়ার bar-এ `low`/`high`); resolve-এ `fv.sweptExtLo := math.min(L.wickX, low)` (Feat 2 field); `f_stop`: sweep branch `min(x, fv.sweptExtLo)`, zone branch `min(zz.bottom, x, sweptExtLo)` যখন sweptLow। ~+45 token। (`ta.lowest` loop-এর ভিতরে allowed নয়, তাই field।)
- **Regression:** sweep-based signal-এর risk distribution আগে/পরে; signal count অপরিবর্তিত (শুধু SL সরে, কিছু R:R < 2 হয়ে drop হতে পারে — সেটাই উদ্দেশ্য)।

### D3 — `ft.breakUp / breakDn` CHoCH-কে break ধরে না · **P2**

- **লাইন:** 2406–2407 (`st.bullBOS or weak or internal or runUp` — `st.bullCHoCH` নেই); `ctx.breakLvl` 2415–2419 (`preHigh` — CHoCH-এ `st.chLvl` হওয়া উচিত)।
- **Root cause:** S4 comment বলে "trap / continuation modules key off ANY level break" — CHoCH বাদ পড়েছে। R2 form-এ `brkUp` true হলেও `s.bullBOS` set হয় না (CHoCH branch নেয়)।
- **Reproduce:** bear trend, HL তৈরি, close > last LH pivot (displaced) → `bullCHoCH`। পরের bar bullish pin (M05) / 1–2 bar-এ close back below (M62 fakeout) / consolidation (M72) — কিছুই fire করে না কারণ `breakAgo` পুরোনো break-এর।
- **Impact:** ICT-র সবচেয়ে গুরুত্বপূর্ণ break (MSS)-এর retest/trap family (M01 M02 M05 M14 M15 M62 M72) blind। M51/M45 আলাদা path-এ ধরে, তাই পুরো হারায় না।
- **Fix:** `ft.breakUp := ... or st.bullCHoCH`; `stUp`-এ CHoCH যোগ; `breakLvl := st.bullCHoCH ? st.chLvl : preHigh`। `contBrk` অপরিবর্তিত (CHoCH-এর পরে trend flipped, continuation নতুন দিকে — ঠিক)। ~+20 token।
- **Regression:** CHoCH bar-এর পরের 8 bar-এ M05/M15/M62/M72 count; `brkTouches` plot।

### D4 — HTF break displacement ছাড়া হলে pivot consume হয়, pending নেই · **P2**

- **লাইন:** 2146–2151 (`bBrk` → `cx.hHiBroken := true` **dispH নির্বিশেষে**); bias change শুধু `if dispH` 2163–2175; promotion mechanism নেই (LTF-এ `f_pend` আছে 1017–1023)।
- **Root cause:** LTF-র weak-break → follow-through model HTF-এ port হয়নি।
- **Reproduce:** HTF bias BEAR, HL form। HTF candle 1 close > hCurHigh, body 40% → `hHiBroken = true`, bias BEAR থাকে। HTF candle 2 বড় displacement উপরে → `bBrk` false (`not hHiBroken`) → R2 path (`bBrk and hlH`) বন্ধ; শুধু `c1 > protH` (দূরের protected high) path খোলা। পরের HTF pivot high (3+ HTF bar) না আসা পর্যন্ত bias BEAR → 5m-এ সব long WARN −1 বা continuation block।
- **Impact:** HTF CHoCH (R2 form) আর NEUTRAL→first-bias late হয়। 1h HTF-এ 4–6 ঘণ্টা ভুল bias।
- **Fix:** `cx.hHiBroken := true` শুধু যখন bias/level actually consumed (dispH ∧ branch নিল), নয়তো পরের HTF candle-এ আবার test। ~+15 token (দুটো assignment সরানো)। বিকল্প: 1-HTF-bar pending like LTF (~+40)।
- **Regression:** HTF bias flip bar-এর তালিকা v8.4.1 vs fix, EURUSD/XAUUSD 5m→1h।

### D5 — Counter-trend/counter-HTF এক fact-এ −3 (triple count) · **P2**

- **লাইন:** gate WARN −1 3456–3458; INCOMPLETE −1 3462–3465 (`ft.gateUp != 2 or not zone/FVG/TL` — gateUp==1 হলেই fire, zone থাকলেও); `f_conf` LTF trend fade −1 3273। HTF counter হলে: 3270 +1 হারায় + gate −1 + INCOMPLETE −1 = effectively −3।
- **Root cause:** P1-3 (audit F6) POI term cap করেছে, context term-গুলো করেনি। INCOMPLETE "4-factor" check-এর HTF half gate-এর duplicate।
- **Impact:** sweep-reversal module (M10 POOL tier 2 = 4 base) counter-trend-এ: 4 + conf(≤5 realistic) − 3 = ≤6 < 8 → কখনো দেখায় না। M10 কার্যত শুধু trend-aligned pullback sweep-এ fire করে। Reversal module-এর (M45★/M68) retest সাধারণত flip-এর পরে, তাই কম ক্ষতি; কিন্তু early reversal (M46 CISD) ভোগে।
- **Fix:** INCOMPLETE-এর শর্ত শুধু `not (zone or FVG or TL)`; gate half বাদ (gate নিজেই −1 দেয়)। অথবা `f_conf` trend-fade −1 রাখুন, gate WARN −1 রাখুন, INCOMPLETE বাদ — নীতি: context max −2। ~−10 token।
- **Regression:** counter-HTF signal count/score histogram (data window `reject code` 5 → 0 shift)।

### D6 — `f_moveStrength` FVG direction দেখে না · **P2**

- **লাইন:** 1373–1378 (`g.idx` window-এ, `not g.mitigated` — `g.isBull` test নেই)।
- **Impact:** `mv.strong` (BOS displacement, KL score 1710, OB creation 1724, `dispScore`), `ctx.chochReal` (2275 "imbalance inside the move"), `arrivalStrong` (2363) — সবাই বিপরীত দিকের gap-ও গোনে। Choppy leg-এ bear FVG থাকলে bull BOS "strong"। `chochReal` fake/real ভুল হতে পারে।
- **Fix:** signature-এ `isBull` যোগ (caller জানে), `g.isBull == isBull` filter। arrival-এ direction = `arrDirNow == 1 ? false : true` (bull zone-এ arrival = down-leg → bear FVG)। ~+15 token।
- **Regression:** STRONG BOS count, chochReal ratio, KL★ count আগে/পরে।

### D7 — Dead features (write-only) · **P3**

- `ft.brkTimeOk` (2611) consumer 0 — M71 cut হয়েছে, feature + plot (3850) + input `i_idmTime` (822) থেকে গেছে। ~−45 token cut।
- `ft.sweptPool` (1554) consumer 0। ~−8।
- `ft.incomplete` শুধু set (3465/3481), কোথাও পড়া হয় না (note+score আলাদা করে করা হয়)। ~−6।
- `ft.insideOk` (2425) শুধু M03 (default off) — M03 cut হলে সঙ্গে যায়।

### D8 — Opposite displaced event-এ stale pending weak break clear হয় না · **P3**

- **লাইন:** promotion 1073–1093 state-change block-এর আগে চলে; 1151–1183-এ `sx.stPendDir := 0` নেই।
- **Reproduce:** bar 100 weak bull break (pend 3 bar); bar 101 displaced bear CHoCH (news spike); bar 102 close > পুরোনো curHigh → promUp → bull BOS → 2 bar-এ দুইবার flip, majorLow re-anchor। বিরল কিন্তু সম্ভব।
- **Fix:** state-change block-এ opposite dir-এর pending clear। ~+6।

### D9 — Weak CHoCH (protected-swing form) fail-counter level ভুল · **P3**

- **লাইন:** 1123 `f_pend(sx,1,2,chUpLvl,...)` ঠিক (H1), কিন্তু 1191–1194 `sx.stBrkLvl := cx.curHigh` — Maj form-এ level ছিল `majorHigh`। `curHigh` price-এর নিচে বসে থাকায় fail-test lenient (ভুয়া fail নয়, miss)। Fix: `s.bullCHoCH-weak` হলে `chUpLvl`। ~+8।

### D10 — "R:R fallback → IMMEDIATE" limit-entry mode-গুলোতেও চলে · **P3**

- **লাইন:** 3379 `if na(tpA) and g.entry != close` — `ZONE EDGE` / `CANDLE 50%`-এও true। Comment (3374–3378) বলে exception শুধু M10 RETEST — P1-A-র পরে ভুল। Impact: limit mode-এ target band-এ কিছু না থাকলে signal নীরবে market entry হয়ে যায় (note-এ লেখা থাকে)। Fix: শর্তে `name == "M10"` যোগ, বা document করে রাখা। 0 token।

### D11 — Cosmetic

- M10 note সবসময় "(IMMEDIATE)" (2855/2875) — RETEST mode-এও।
- plot label "M04/M21/M33/M42 gate" (3852) — M21 নেই; `i_tlTol` label "M12/M64/M65/M66" (819) — M66 নেই; 3850 "M71"।
- `f_pathBlock` comment "zone or FVG" (3231) — code শুধু zone।
- Both-sides tie (`>=` 3496) → long জেতে।

## C. Design weaknesses (code ঠিক, logic দুর্বল)

### W1 — CONFIRMED + CLOSE default: entry late, risk inflated · **P1**

- **লাইন:** trigger 2698 (`close > sx.poiRefL`), entry 3337 (`close`), SL 3317 (`min(zone.bottom, lowTap) − buf`)।
- **ব্যাখ্যা:** tap bar T-তে reaction candle (pin, ~1 ATR); confirm = close > high[T]। Entry = confirm close (reaction high-এর উপরে)। Risk = confirm close − zone bottom − buf ≈ zone height + reaction candle + confirm progress ≈ 1.5–2.5 ATR 5m-এ। `minRR 2` → TP1 ≥ 3–5 ATR দূরে এবং `maxRR 6` cap-এর ভিতরে real level লাগে → reject code 4 বেশি। `ZONE EDGE` option (P1-A) আছে, default নয়; সেটাও "fill নাও হতে পারে"।
- **ICT model:** sweep → MSS/displacement → **retrace into the displacement leg's FVG / OB (OTE)** → limit। এখানে retrace step নেই: confirm-এর পর chase।
- **প্রস্তাব:** নতুন entry option `RETRACE`: confirm হলে signal "armed" (label ⏳), displacement leg-এর (tap → confirm) 50% বা leg-এর fresh bull FVG-র top-এ limit; SL অপরিবর্তিত (zone/wick); N bar-এ touch না হলে expire; touch হলে **তখন** signal + alert। Risk অর্ধেক, R:R দ্বিগুণ, "late chase" বন্ধ। ~+120 token (state: armed price / expiry / dir, 2 side)। Validation: fill rate vs CLOSE (কত % armed → fill) আর R-multiple distribution।

### W2 — PD gate module-blind, off by default; continuation module deep premium-এ কেনে · **P1**

- **লাইন:** `i_pdGate` false 868; gate 2349–2353 (সব module); score −1 শুধু 3292।
- **ব্যাখ্যা:** M08/M36/M42/M51/M73 (continuation) tier 3–4 = base 6–8; deep premium −1 → তবু ≥8। "Entering too late after an extended move" (Phase 4 Q7) কোনো hard check নেই। `freshDisp` guard শুধু M10 fade-এ।
- **প্রস্তাব:** P1-E-র `contL/contS` set reuse: continuation module-এ `pdPct > i_pdDeep` (long) → block (reject 2), reversal module score-only। `pdBeyond` (expansion) হলে block নয়। ~+30। Validation: continuation signal-এর pdPct histogram আগে/পরে; expectancy by pdPct bucket।

### W3 — M54 (tier 4) chain এক zone/level-এ anchored নয় · **P1**

- **লাইন:** 2507–2528। stage 1 = যেকোনো demand touch; stage 2 = যেকোনো `sweptLowQ` (দূরের PDL-ও); stage 3 = যেকোনো bull BOS; entry = যেকোনো bull zone + trigger; প্রতি stage 60 bar renew।
- **ব্যাখ্যা:** "demand reject → stop hunt **under it** → BOS → retrace into **that** block" — code-এ "under it" আর "that" নেই। Tier 4 = 8 base → A grade conf ছাড়াই। False confluence।
- **প্রস্তাব:** stage 1-এ `m54Zb := ft.zb.bottom`; stage 2 শর্ত `fv.sweptPriceLo <= m54Zb and >= m54Zb − 1.5 ATR`; stage 3 BOS `ctx.legIdx >= sweptLowBar`; entry zone `ft.zb.idx`/bottom within 1 ATR of m54Zb বা BOS leg-এর নতুন OB (`depStrong`)। ~+40। নয়তো M54 → tier 3।

### W4 — `maxRR` hard reject tight-stop setup ফেলে দেয় · **P2**

- **লাইন:** 3371–3372, 3390–3392। risk 0.3 ATR (floor) → cap 1.8 ATR; nearest real level 2.5 ATR → `tpA` na → reject। সবচেয়ে ভালো entry (POI edge, ছোট stop) hidden।
- **প্রস্তাব:** band-এ কিছু না পেলে cap-এর বাইরের nearest real level নিন, TP1 = সেটা কিন্তু `g.tgt := "FAR"` + note; বা TP1 = `entry + maxRR×risk` SYNTH-marked, TP2 = real level। Reject নয়। ~+15।

### W5 — Path check শুধু zone; opposing FVG / liquidity pool ignore · **P2**

- **লাইন:** 3235–3249। Long entry-র 1R উপরে EQH pool বা unmitigated bear FVG → path "clear"।
- **প্রস্তাব:** `f_pathBlock`-এ FVG (unmitigated, opposite) আর qualified liq (POOL/PD/PW/SES) loop; liq হলে WARN level (sweep হয়ে যেতে পারে), zone/FVG STRICT। ~+45।

### W6 — Trend 20 bar-এ RANGE-এ decay · **P2**

- **লাইন:** 1203–1206 (`rangeBarsThresh` 20, input 763)। 5m-এ swingLen 5 → pivot ≥11 bar; এক pullback + এক leg সহজে >20 bar। RANGE-এ CHoCH অসম্ভব (1098–1101 trend check), continuation module silent, `f_conf` −1, পরের displaced break যেদিকেই হোক "BOS" (reversal-কে BOS বলে)।
- **প্রস্তাব:** default 20 → 40 (5m) বা `swingLen × 8`; অথবা RANGE শুধু fail-counter থেকে, time-decay শুধু `inRange` panel-এ। Validation: trend-state distribution + CHoCH count আগে/পরে।

### W7 — POOL = 2 touch (1 pivot + 1 retest wick) · **P2**

- **লাইন:** 1498–1500 / 1516–1518 touch++ (tol 0.15 ATR, cooldown 3) → 1519 pooled; 1535 `qual = touches >= 2`। 5m-এ pivot-এর এক retest = "EQH" = qualified sweep → M10 tier 2, M41/M45/M54/CISD arm।
- **প্রস্তাব:** `qual` = EQH/EQL kind (merge path, দুটো pivot) ∨ touches ≥3 ∨ PD/PW/SES; label POOL শুধু তখন। ~+10। Validation: qualified sweep count/day।

### W8 — CONFIRMED trigger 1-tick close যথেষ্ট · **P2**

- **লাইন:** 2698 `close > sx.poiRefL`। Confirm candle displacement লাগে না। MSS mode (5-bar high) ভালো কিন্তু default নয়।
- **প্রস্তাব:** confirm = `close > ref + 0.1 ATR` ∧ `cd.bodyRatio ≥ 0.4`, বা FVG (আছে)। ~+12। বিকল্প: default MSS + window 12।

### W9 — Correlated confluence terms · **P2**

- discount (+1) ⊃ OTE (+1) — OTE band 0.21–0.38 discount-এর ভিতরে → এক location fact = +2 (3291, 3295)। NY-open side (+1, 3301) bull day-এ discount-এর সঙ্গে highly correlated → +3।
- `bslAbove ≥ 1` (3282) 30 level + 3 ATR scan → প্রায় সবসময় +1।
- session +1 (3298) killzone filter on থাকলে Asia ছাড়া সবসময়।
- HTF +1 (3270) আর gate −1 → এক fact-এ 2-point swing (D5 সহ 3)।
- **প্রস্তাব (Phase 8 model):** location term এক: OTE +2 / discount +1 / deep −1 (NY-open আলাদা নয়, বা শুধু tie-break); liq term: `bslAbove ≥ 2` বা TP1 REAL-এর duplicate বলে বাদ; session: killzone filter on হলে 0। Threshold input থাকবে, OOS-এ validate। ~−20।

### W10 — M10 sweep candle-এই entry, MSS/CISD ছাড়া · **P2**

- **লাইন:** 2777–2778। P0-E (upper-half close) আছে, structure shift নেই। M46 (CISD) confirmed form, কিন্তু `cisdNeedSweep` + reliability লাগে।
- **প্রস্তাব:** input `M10 confirm`: Off (এখন) / "close above sweep candle high" (1-bar) / "CISD". Validation: M10 win-rate by variant (05)।

### W11 — M41 react FVG sweep-এর আগেরও হতে পারে · **P2**

- 2902 `reactBull` যেকোনো unmitigated bull FVG; M41-র দাবি "STRONG move left FVG" → FVG `g.idx ≥ ctx.sweptLowBar` হওয়া উচিত। D1 fix-এর পরে relevant। ~+20 (flag `atBullFvgFresh`)।

### W12 — `stFail` decay নেই · **P3**

- 1050 ++, reset শুধু displaced event 1160/1177। 300 bar আগের এক fail + আজকের এক fail → RANGE। Fix: `stBrkDir := 0` branch (1055)-এ `stFail := 0` যদি `bar_index − stBrkBar > failedCloseBars × 5`। ~+8।

### W13 — PDH/PDL broker day; London session H/L নেই · **P3**

- 2225 `"D"` = TradingView daily (forex 17:00 NY)। ICT true day 00:00 NY। London H/L (02–05) NY-তে sweep হয় — `asiaHi/Lo` pattern copy ~+40।

### W14 — Tier-1 module min-score 8-এ dead · **P3**

- Tier 1 = 2 + conf; conf ≥6 বাস্তবে বিরল। Default-ON M69 (IFC) tier 1 → কার্যত কখনো দেখায় না। হয় M69 → 21 (zone-এ IFC + sweep যৌক্তিক), নয় cut। বাকি tier-1 (M03 M04 M06 M07 M11 M14 M29 M63) default off → token cut source (04)।

### W15 — Arrival verdict দুই side share করে · **P3**

- 2359 `arrDirNow` bull-preferred; 2682 `arrOkBear = arrOkBull`। Overlapping bull/bear zone touch একই bar-এ bear side bull-এর verdict পড়ে। Edge case।

### W16 — HTF FVG single slot, age নেই · **P3**

- 2131–2137 latest overwrite; mitigation শুধু far-edge close। পুরোনো HTF FVG মাসের পর মাস +1 দিতে পারে। Fix: HTF bar count age cap (e.g., 50 HTF bar)। ~+10।

## D. যা ঠিক আছে (verified, বদলানো নয়)

- Long/short mirror: setup lines, f_bid rank, f_stop, f_sig, f_conf, gate — line-by-line symmetric।
- H1/H2/H3 (v8.4.1) code-এ ঠিকভাবে landed: `chLvl/chIdx` 1080–1081, 1105–1108, 1120–1124, 1162, 3696–3699; `poiArmL/S` 2677–2680; `setLoL/setHiS` 2725–2730 → `f_stop(x)` 3311–3329।
- Candidate pick deterministic (rank), identity dedupe, both-sides conflict, gap override — spec-মতো।
- OB definition (last opposite candle before displacement, FVG-aligned, self-mitigation) ICT-consistent।
- CISD definition (series open that made the extreme, after qualified sweep) ICT-consistent।
- IDM logic (inducement above OB swept, OB untouched → later tap) — ভালো।
- Zone dedupe/refresh, priority slot per side, sweepReq ≥2 touch — spec-মতো।

## E. Uncertainty

- Token count: v8.4.1 compile হয়েছে কি না অজানা। 04-এর প্রতিটা fix cut-covered।
- "Institutional" দাবি কোথাও করা হয়নি — সব module observable price action; win-rate অজানা (strategy twin নেই, 05)।
- D4-এর impact HTF pairing-এর উপর নির্ভর; 1h-এ 4–6 ঘণ্টা, 4h-এ দিন।
