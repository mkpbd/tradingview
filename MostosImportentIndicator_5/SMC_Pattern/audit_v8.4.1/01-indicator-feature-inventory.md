# 01 — Indicator Feature Inventory · SMC / ICT Suite v8.4.1

তারিখ: 2026-10-10 · ফাইল: `SMC_Pattern/SMC_v8.4.1.txt` (3862 লাইন) · Pine `//@version=6` · `indicator()` (strategy নয়)
পদ্ধতি: পুরো source লাইন-বাই-লাইন পড়া। **কোনো feature "নাম আছে" বলে ধরা হয়নি** — প্রতিটার producer আর consumer দেখানো হয়েছে। Compile/token status: v8.4.1 header নিজেই বলে "compile to confirm" — **TradingView-এ compile হয়েছে কি না এই audit জানে না**; prior review-এর দুটো compile-uncertainty (`ta.lowest(low, series int)`, `math.max` 3-arg) দুটোই v6-এ valid।

## 1. Architecture

| বিষয় | ফল | লাইন |
|---|---|---|
| Script type | `indicator(..., overlay=true, max_bars_back=500, labels/lines/boxes 500)` | 200 |
| Layering | L0 candle → L1 structure → L2 FVG/strength → L3 liquidity → L4 zones → L5 HTF → L6 setups (feature-vector, এক boolean/setup) → L7 trade | 133–134, 2245–2322 |
| State | সব mutable state `var Ctx ctx` + `var Sx sx` (UDT, element cap-এর জন্য দুই ভাগ); per-bar flags `Feat ft` প্রতি bar নতুন | 405–497, 517–593, 596–692, 964–965 |
| Config | এক `Cfg cfg` + এক `Vis vis` (R2) | 204–287, 941–962 |
| Arrays | `ctx.fvgs` (≤40), `ctx.lv` (≤30, priority eviction), `ctx.zones` (≤30 SR + ≤60 total) | 1337, 1575–1587, 2087–2105 |
| Loops | event-driven: `f_legOrigin` ≤490, `f_moveStrength` ≤150, OB walk ≤5, `brkTouch` 30, `brkTimeAt` 10; per-bar: zone/liq/fvg maintenance | 1005, 1355, 1739, 2535, 2607 |
| `request.security` | 3 call: HTF 12-tuple (`[1]`, `lookahead_on`), D `[high[1],low[1]]`, W `[high[1],low[1]]` | 2122–2125, 2225–2226 |
| Drawing budget | labels 200 + liq ≤30 · lines 100 struct + liq + 12 HTF + 50 trade + 2 major · boxes 40 FVG + 60 zone | 135–136 |
| Inputs | 11 group, ~130 input; `i_setMode` master (Custom / Core only / All on / All off) | 726–939, 2614–2644, 2890–2898, 2963–2978, 3146–3181 |
| Alerts | 2 dynamic `alert()` (signal, `freq_once_per_bar_close`) + 11 `alertcondition` (সব `barstate.isconfirmed` gated) | 3814–3841 |
| Data window | 13 plot: score L/S, zones, liq, brkTouches, brkTimeAt, cisdRel, depStrong, pdPct, dispScore, internal/weak break, reject code (L×10+S) | 3844–3862 |
| Panel / legend | 15-row panel (bottom-right), 8-row legend (off default) | 3730–3809 |

## 2. Feature table

| Feature | Implemented? | Logic location | Potential weakness (details: 02) |
|---|---|---|---|
| BUY/SELL signals | ✔ — 36 module → `f_bid` → best-per-side (`bL`/`bS`) → `f_sig` → gate/score/gap/identity → `sigL`/`sigS` | 2832–2883, 2939–2956, 3124–3143, 3333–3534 | Candidate pick direction-only (§C4); CONFIRMED+CLOSE default = late entry (W1) |
| Market structure (LTF) | ✔ — pivot (`ta.pivothigh/low`, len 5) → BOS (trend-aligned + displacement) / CHoCH (protected swing বা R2 LH/HL form) / internal / weak (pending follow-through) / RANGE (2 fail বা 20 bar) | 1037–1283 | 20-bar RANGE decay (W6); stale pending (D8) |
| HH/HL/LH/LL tagging | ✔ `sx.hiType`/`loType` শেষ confirmed pivot-এর | 1040–1045 | — |
| Protected swing | ✔ `majorLow`/`majorHigh` = `f_legOrigin` (break leg-এর price origin) | 1005–1015, 1151–1183 | — |
| Displacement | ✔ candle body ≥0.5 & range ≥0.6 ATR, বা close beyond level ≥0.3 ATR | 2259, 1110–1113 | HTF side displaced-না হলে pivot consume হয় (D4) |
| Move strength (`Move`) | ✔ bodyEff / mixed / speed / fvgCount → `strong`; event-driven (BOS, CHoCH, zone arrival) | 1355–1388, 2267–2283, 2360–2374 | FVG direction-blind (D6) |
| FVG | ✔ 3-candle, min height, `isconfirmed` gated; mitigation TOUCH/50%/FULL; age-drop | 1292–1340 | **TOUCH mode-এ `atBullFvg/atBearFvg` কখনো true হয় না (D1)** |
| HTF FVG | ✔ `high[3]/low[3]` tuple → latest unmitigated bull/bear HTF FVG; `inHtfFvgB/S` +1 conf | 2131–2137, 2188–2196, 3288 | single slot, no age (W16) |
| Liquidity levels | ✔ pivot BSL/SSL (EQH/EQL merge 0.1 ATR), PDH/PDL (D), PWH/PWL (W), SESH/SESL (Asia end); touch count; priority eviction | 1406–1587, 2293–2310 | POOL = 2 touch (1 retest wick-ও) → loose "qualified" (W7); PDH broker-day (W13) |
| Sweep / run | ✔ wick beyond + close back = SWEEP; body close beyond = RUN; else 2-bar pend | 1483–1518 | pend path-এ SL resolve bar-এর low নেয় (D2) |
| Sweep qualification (S5) | ✔ POOL / PD / PW / SES (+ext opt) → `sweptLowQ/HighQ`, `sweptLowBar/HighBar` | 1535–1545 | — |
| Equal H/L | ✔ merge path (`f_addLevel`) + touches≥2 | 1409–1433, 1519 | — |
| S/R wick zones + Key Level score | ✔ SR at every pivot; BOS-এ origin SR scored (base 1 + FVG + strong + hidden-interest + vol) → KL≥3 shown, KL★≥4 | 1681–1719 | — |
| Order Block | ✔ শুধু displaced BOS-এ; OB = last opposite candle before first displacement candle (T1/T1b/T2/G2); FVG-aligned (T5), self-mitigation (T3); HP = qualified sweep within window | 1724–1798 | CHoCH leg-এর OB "RCB" হয়, "OB" নয় (design, 03-এ) |
| Breaker | ✔ OB close-through → BRK (দিক উল্টে) | 1920–1932, 1991–2003 | — |
| Reclaimed block (RCB) | ✔ CHoCH leg origin candle, fib gate (origin high ≤ leg mid) | 1803–1826 | — |
| Rejection block (RJB) | ✔ wick≥50% + next candle held out; FVG within 2 bar; BOS confirm ≤15 bar | 1843–1862, 1880–1895 | — |
| Quasimodo (QM) | ✔ CHoCH → low < last pivot low within 60 bar → QM zone | 1827–1840 | — |
| Propulsion (PROP) | ✔ tapped+50% hit → re-departure with FVG 0.8–2.4 ATR → re-armed | 1959–1968, 2028–2037 | — |
| Inducement (IDM) | ✔ zone-এর উপরের pivot low swept, zone untouched → `idmSwept` | 1899–1903, 1970–1974 | — |
| Zone lifecycle | ✔ tap / 50% / touches / sweepReq (≥2 touch) / broken / flip / age-drop / dedupe-refresh | 1864–2086, 1632–1653 | — |
| Zone slot per side (S9) | ✔ `ft.zb` (bull) / `ft.zs` (bear), priority OB>BRK>RCB=QM>RJB>KL>SR, +3 PROP | 2038–2076 | — |
| Premium / Discount | ✔ dealing range = current leg (protected swing → extreme); pdPct, discount/premium, beyond; OTE band; gate (off default) | 2335–2353, 3290–3295 | discount+OTE+NY-open correlated (W9); gate module-blind (W2) |
| Sessions / killzones | ✔ NY-tz Asia 20–00 / London 02–05 / NY 07–10; filter auto-on forex+cfd; score London/NY; Asia H/L levels | 2231–2243, 2288–2310 | London-close KZ নেই (W13) |
| NY midnight open | ✔ `nyOpen` (00:00–00:05 NY bar open), +1 conf, panel | 2240–2243, 3300–3301 | ≤1h TF-এ কাজ করে |
| HTF bias | ✔ pairing table / manual; HTF pivot (len 3); BOS/CHoCH (R2 incl.) with 50%-body displacement; HTF sweep (3 HTF bar valid); manip / rejection candle | 2108–2207 | D4 |
| HTF/LTF gate | ✔ `f_gate` OFF/WARN/STRICT, reads `preTrend` (entering bar); module-aware (continuation set blocked at WARN) | 2210–2214, 2320–2322, 3449–3451 | counter-trend triple penalty (D5) |
| CISD | ✔ open of the series that made the leg extreme; close through; qualified sweep within armBars; consumed | 1250–1276, 2493–2505 | — |
| Trendline (M64) | ✔ last two HL / LH pivots; age/distance/slope caps; touch count | 2544–2602, 3015–3031 | — |
| Candle anatomy (L0) | ✔ pin, doji, engulf, inside, harami, long-wick, star, IFC, manip | 968–999 | — |
| Entry price | ✔ CLOSE (default) / CANDLE 50% / ZONE EDGE; M10 RETEST/BOTH | 3337–3349 | fallback→IMMEDIATE applies to all limit modes (D10) |
| Stop-loss | ✔ zone (min with setup extreme `x`) → sweep (`x`) → major HL/LH (≤2 ATR) → candle; wrong-side sanity; min risk max(20 tick, 0.3 ATR) | 3311–3330, 3354–3359 | D2 |
| Take-profit | ✔ TP1 = nearest qualified opposing zone / unmitigated FVG / qualified liq in [minRR, maxRR] (REAL) else SYNTH/reject; TP2/TP3 = next liquidity ≥ +1R ladder; Fixed-R mode | 3189–3229, 3360–3406 | maxRR hard reject (W4); path check zone-only (W5) |
| Path check | ✔ qualified opposing **zone** between entry and TP1 → WARN −1 / STRICT reject | 3235–3249, 3409–3416 | FVG/liquidity ignored (W5) |
| Score | ✔ tier×2 (2–8) + `f_conf` (base 1; HTF +1; trend +1/−1; POI cap 2; liq +1; sweep/IDM +1; arrivalStrong −2; sweepReq −2; RANGE −1; HTF FVG +1; PD +1/−1; OTE +1; session +1; NY open +1) − path − gate WARN − INCOMPLETE; min 8, A ≥8, A+ ≥11 | 3267–3302, 3422, 3456–3466 | D5, W9 |
| Signal dedupe | ✔ one-per-side-per-bar; both-sides → higher score; gap 5 bar (override +2 opposite); identity (module+side+POI) 50 bar | 3487–3534 | tie→long (D11) |
| Repaint protection | ✔ security `[1]`+lookahead_on; FVG/OB/RJB/KL/arrival `isconfirmed`; labels/lines/alerts `isconfirmed`; realtime var-rollback | 02 §A | কোনো repaint নেই |
| Trade-state management | ✖ **নেই** — entry/SL/TP লাইন শুধু আঁকা হয় (20 bar); fill/exit/outcome track হয় না; strategy twin repo-তে নেই | 3538–3552 | 05 |

## 3. Module inventory (L6)

Rank = tier×10 + priority; score = tier×2 + conf। Default = `Core only`-র curated set।

| Module | Default | Rank/Tier | Setup line | Family |
|---|---|---|---|---|
| M01 Breakout rejection trap | ON | 21 / 2 | 2734, 2736 | break-trap |
| M02 Pin-bar continuation | ON | 21 / 2 | 2735, 2737 | break-cont (contBrk) |
| M03 Inside-bar breakout | off | 10 / 1 | 2748–2751 | break |
| M04 Doji move reversal | off | 10 / 1 | 2752–2753 | zone |
| M05 Pin bar after breakout | ON | 21 / 2 | 2755–2756 | break-cont |
| M06 Multi pin pullback | off | 10 / 1 | 2757–2758 | zone+trend |
| M07 Multi pin impulse (trap) | off | 10 / 1 | 2759–2762 | counter |
| M08 Pin bar on retracement | ON | 21 / 2 | 2766–2767 | zone+trend (cont) |
| M09 Pin bar + liquidity | ON | 32 / 3 | 2768–2769 | zone + ≥2 BSL/SSL |
| M10 Sweep reversal | ON | 21 / 31 | 2777–2778 | sweep (immediate) |
| M11 Doji + breakout | off | 10 / 1 | 2785–2793 | zone |
| M12 Confluence zone | off | 11 / 1 | 2795–2796 | flipped+TL/KL |
| M14 Pin after breakout (S/R) | off | 10 / 1 | 2797–2798 | break-cont |
| M15 Breakout with pin | ON | 21 / 2 | 2799–2800 | break-cont |
| M29 Strong move trap | off | 10 / 1 | 2803–2806 | counter |
| M33 Zone flip model | ON | 32 / 3 | 2808–2809 | flip, trend+HTF (cont) |
| M36 Weak retrace on OB | ON | 32 / 3 | 2814–2815 | OB (cont) |
| M37 Inducement block | ON | 43 / 4 | 2816–2817 | OB + IDM |
| M39 RCB retest | ON | 31 / 3 | 2906–2907 | RCB |
| M40 RJB retest | ON | 21 / 2 | 2908–2909 | RJB |
| M41 Sweep + FVG | ON | 43 / 4 | 2911–2913 | sweep→BOS strong→react |
| M42 HP S&D | ON | 43 / 4 | 2915–2916 | OB depStrong+50%+weak arr (cont) |
| M45 Sweep CHoCH retest | ON | 33 / 43 | 2918–2920 | sweep→BOS/CHoCH→BRK/OB |
| M46 CISD | ON | 32 / 3 | 2922–2923 | CISD + reliability → react |
| M51 Smart BOS | ON | 32 / 3 | 2925–2928 | strong BOS ≤40 bar → zone (cont) |
| M54 Smart S&D trap | ON | 43 / 4 | 2929–2936 | demand→sweepQ→BOS→zone |
| M58 Double top/bottom | ON | 21 / 2 | 2983–2992, 3090–3091 | pattern |
| M62 Fakeout trap | ON | 21 / 2 | 2995–2999, 3092–3093 | failed break |
| M63 Direct breakout | off | 10 / 1 | 3002–3013, 3094–3095 | break |
| M64 Auto trendline | ON | draw only | 3017–3031 | — |
| M65 TL + flipped level | off | 21 / 2 | 3034–3051, 3096–3097 | TL |
| M68 HTF sweep → LTF | ON | 43 / 4 | 3054–3059, 3098–3099 | HTF sweep + CHoCH → react |
| M69 IFC candle | ON | 10 / 1 | 3062–3073, 3100–3101 | candle (score 2+conf → কার্যত dead at min 8, W14) |
| M70 Quasimodo | ON | 22 / 2 | 3102–3103 | QM |
| M72 Operator trap | ON | 21 / 2 | 3076–3087, 3104–3105 | consolidation after break |
| M73 Propulsion | ON | 43 / 4 | 3120–3121 | PROP 50% (cont) |

Filters (group 12): M19 arrivalStrong block (on), M26 corrective pullback (on), M31 retest body (off), §6.2 sweep-required (on), §6.6 50% (on), M01/M02 ≥2 rejection (on), zone close beyond 50% (on). Continuation set for HTF gate (P1-E): M02 M05 M08 M15 M33 M36 M42 M51 M73।

## 4. Shared gates (সব zone module-এর উপর)

- `zoneOkBull` = at bull zone ∧ close ≥ zone mid ∧ (no sweepReq ∨ sweptLow ∨ armed POI) ∧ (SR ∨ 50% hit) — 2679
- `trigBull` = IMMEDIATE: reversal candle (pin/engulf/IFC/manip); CONFIRMED/MSS: POI state machine (tap → close > reaction high [বা 5-bar high] বা fresh FVG, ≤8 bar, invalidation = below zone/low −0.15 ATR) — 2690–2722
- `arrOkBull`/`pbOk`/`rtOk` — arrival strength filters — 2681–2684
- HTF gate → session → `f_sig` (geometry, R:R, path) → score ≥ 8 → both-sides → gap → identity — 3449–3534

## 5. যা নেই (নামে আছে / spec-এ আছে কিন্তু code-এ নেই)

- Strategy twin / win-rate stats (header 198 `SMC_Suite_v8.2.1_strategy.pine`) — repo-তে নেই (`find` → 0)।
- London-close killzone, London session H/L, ICT true-day PDH/PDL (broker day ব্যবহার হয়)।
- POI-তে limit re-entry after MSS (OTE/FVG limit) — শুধু "ZONE EDGE" limit option, default CLOSE।
- Trade outcome tracking (hit SL/TP) — নেই।
- M22/M71 data-window label (3850 "M71 · bars at level") — M71 module v8.2.0-এ cut, feature `brkTimeOk` শুধু plot হয়, কোনো setup পড়ে না (`ft.brkTimeOk` consumer: 0) — dead feature, cut candidate (~40 token)।
