# 03 — BUY / SELL Entry Analysis · SMC / ICT Suite v8.4.1

তারিখ: 2026-10-10। প্রতিটা pathway-র জন্য Phase 4-এর 12 প্রশ্ন। Classification analytical — profitability-র guarantee নয়। Long/short mirror, তাই long লেখা; short সব উল্টো (line pair দেওয়া)।

## 1. Common pipeline (সব signal এক পথে)

```
L0 cd → L1 st → L2 mv/FVG → L3 liq → L4 zones (ft.zb/zs) → L5 HTF → gates
  → 36 module boolean → f_bid (rank) → best per side
  → HTF gate (2 pass / 1 warn / 0 block; continuation set blocked at warn)   3449–3451
  → killzone (forex auto)                                                    3451
  → f_sig: entry (CLOSE default) → f_stop → risk floor → TP1 real [2R,6R] → path STRICT → geometry   3333–3426
  → score = tier×2 + f_conf − path − warn − INCOMPLETE ≥ 8                  3422, 3456–3466
  → both-sides → gap 5 (override +2) → identity 50 bar                       3495–3528
  → label / lines / alert on bar close                                        3548, 3666, 3819
```

Common weakness (02): D1 (FVG path dead), D5 (counter-context −3), W1 (late entry), W2 (no late-move gate), W4 (maxRR reject), W9 (correlated conf)।

## 2. Pathway-by-pathway (default-ON modules)

Column: Q1 precondition · Q2 liquidity · Q3 PA confirm · Q4 structure · Q5 displacement · Q6 entry vs invalidation · Q7 late-move guard · Q8 room (TP) · Q9 SL · Q10 R:R · Q11 invalidation · Q12 OOS → **class**

### Group 1 — Sweep / reversal (Model A)

**M10 Sweep reversal** (2777, 2855 / 2778, 2875) · tier 2 (POOL) / 3 (PD/PW/SES)
- Q1: qualified level swept (বা pivot sweep inside zone); not fading fresh strong displacement (≤10 bar)। Q2: level নিজেই। Q3: sweep candle close back above + upper-half close + lower wick ≥0.5। Q4: **নেই** (MSS/CISD না)। Q5: না। Q6: entry = close (wick-এর উপরে), SL = low − buf (D2: pend path-এ ভুল low)। Q7: `freshDisp` শুধু। Q8: TP1 real। Q9: sweep low (D2)। Q10: ≥2। Q11: close < sweep low। Q12: untested।
- Gate: counter-trend হলে −3 (D5) → POOL form কার্যত trend-aligned-এ সীমিত।
- **Class: Conditional** — structure confirmation missing (W10), SL D2। Fix-এর পরে HQ candidate at PD/PW/SES level with 1-bar confirm।

**M46 CISD** (2922, 2944 / 2923, 2954) · tier 3
- Q1: CISD (close through series open) after qualified sweep ≤30 bar + ≥1 reliability (HTF rej/sweep · fresh FVG ≤3 bar · sweep ≤5 bar)। Q2: swept level। Q3: zone/FVG reaction + trigger (IMMEDIATE harami-ও)। Q4: CISD = early MSS। Q5: reliability-তে FVG option। Q6: react zone-এ। Q7: না। Q8–10: common। Q11: POI invalidation।
- D1: FVG reaction dead → শুধু zone। reliability term 3 "sweep ≤5 bar" arming শর্তের duplicate (sweep লাগেই) → ≥1 reliability প্রায় free।
- **Class: High-quality candidate** (D1 fix + reliability ≥2 হলে)। এখন Conditional।

**M45 Sweep → BOS/CHoCH → BRK/OB retest** (2918, 2943 / 2919, 2953) · tier 3 (±1 BOS) / 4 (±2 CHoCH)
- Q1: qualified sweep ≤10 bar আগে + displaced BOS/CHoCH (`sweepBosBull/sweepChochBull` 2470–2473), armed ≤30 bar। Q2: swept level। Q3: zone trigger at BRK/OB। Q4: ✔। Q5: BOS/CHoCH displaced (structure gate)। Q6: zone edge-ish (CONFIRMED late, W1)। Q7: armBars 30। Q8–10 common। Q11: zone broken।
- ★ form = ICT "sweep → MSS → breaker" — সবচেয়ে clean model। Retest zone হতে হবে BRK/OB; CHoCH leg-এর origin "RCB" হওয়ায় (1803–1811) origin-OB retest M39 (tier 3)-তে যায়।
- **Class: High-quality candidate (★ form)**; BOS form (continuation after sweep) Conditional।

**M68 HTF sweep → LTF CHoCH → react** (3054–3059, 3098, 3128) · tier 4
- Q1: HTF sweep ≤3 HTF bar + LTF CHoCH same bar → armed 30 bar। Q2: HTF swing। Q3: zone/FVG trigger। Q4: ✔ CHoCH। Q5: CHoCH displaced। Q6: react POI। Q7: no。 Q8–10 common。
- D1: FVG react dead; D4: HTF sweep detection fine (sweep path hHiBroken independent) ✔。 Arming requires CHoCH **same bar** as `htfSweepDn` window (3 HTF bar = 36 LTF bar on 5m→1h) — ok।
- **Class: High-quality candidate**।

**M41 Sweep + strong BOS (FVG) → react** (2487–2492, 2911, 2941) · tier 4
- Q1: qualified low sweep ≤20 bar then displaced bull BOS with `mv.strong` (FVG ≥1)। Q3: zone/FVG trigger ≤30 bar। Q4: BOS ✔ (CHoCH নয় — sweep-এর পরে BOS = continuation-after-sweep; reversal হলে CHoCH হতো → M45★)। Q5: ✔。 
- D1: FVG react dead → "sweep + FVG" module FVG ছাড়া চলে (zone-এ)। W11: FVG freshness। D6: fvgCount direction-blind।
- **Class: Conditional** (D1/W11 fix → HQ)।

**M62 Fakeout trap** (2995–2999, 3092, 3125) · tier 2
- Q1: break then close back within 1–2 bar → armed; tap of level ±0.3 ATR + reversal candle ≤30 bar。 Q2: break level (trapped breakout traders)。 Q3: reversal candle (IMMEDIATE always — trap module)。 Q4: না। Q5: না。 Q9: candle/major。 
- D3: CHoCH fakeout miss。 Level includes RUN (liquidity) break ✔。
- **Class: Conditional** (candle-only confirm; counter-trend −3 হলে ≤8 rarely)。

**M58 Double top/bottom** (2983–2992, 3090, 3124) · tier 2
- Neckline close-through = breakout entry; no POI, no sweep。 SL = major/candle。 Entry after a full leg (late)。
- **Class: Low-quality** (SMC context-এ pattern breakout; keep as optional, consider default off)。

**M72 Operator trap** (3076–3087, 3104, 3131) · tier 2 — consolidation at broken level with wicks → strong close back。 Trap logic reasonable; D3 CHoCH miss。 **Conditional**。

### Group 2 — POI retracement (Model C)

**M37 Inducement block** (2816, 2863 / 2817, 2883) · tier 4
- Q1: OB/BRK tapped, `idmSwept` (pivot low above the OB swept earlier, OB untouched then)。 Q2: inducement pool ✔ (ICT IDM)。 Q3: zoneOk (50%, close ≥ mid, sweepReq) + trigger。 Q4: OB from displaced BOS ✔。 Q5: OB leg displaced ✔。 Q6: zone (W1 late)。 Q7: PD score only (W2)。 Q9: zone bottom ∧ wick ✔ (H3)。
- **Class: High-quality candidate** — strongest POI module. W2 (premium OB tap in extended trend) is the main leak。

**M42 HP S&D** (2915, 2942) · tier 4
- OB depStrong + 50% + arrivalWeak + trigger。 No liquidity event required。 Continuation set (HTF gate blocks counter)。 Fires on FIRST tap of a strong OB — ICT "fresh OB" play。 W2 relevant。
- **Class: Conditional → HQ with PD gate** (without liquidity sweep it is a plain OB retest)。

**M36 Weak retrace on OB** (2814, 2862) · tier 3 — same as M42 minus depStrong/50%。 **Conditional**。

**M73 Propulsion** (3120, 3132) · tier 4 — zone proved twice; 50% tap + trigger; `sweepReq` intentionally bypassed。 Reasonable ICT concept; no sweep requirement → **Conditional** (tier 4 without liquidity event is generous; suggest tier 3)。

**M39 RCB retest** (2906, 2939) · tier 3 — CHoCH leg origin candle (fib gate) retest。 This IS the ICT reversal OB。 `chochReal` as depStrong。 **High-quality candidate** when `chochReal` ∧ sweep before CHoCH (`chochUpX`) — suggest tier 4 if `ctx.sweptLowBar` within 10 bars of the CHoCH, else 3。

**M40 RJB retest** (2908, 2940) · tier 2 — wick zone confirmed by BOS。 **Conditional**。

**M70 Quasimodo** (3102, 3130) · tier 2 — QM zone tap。 **Conditional**。

**M08 Pin bar on retracement** (2766, 2849) · tier 2 — trend + any bull zone + trigger。 No sweep, no depStrong。 Most generic; W2 critical (buys premium pullbacks)。 **Low-quality** unless PD gate + depStrong。

**M09 Pin + liquidity** (2768, 2850) · tier 3 — zone + wick ≥0.65 + ≥2 BSL above (room ✔ Q8)。 **Conditional**。

**M33 Zone flip** (2808, 2861) · tier 3 — flipped KL + depStrong + weak arrival + trend + HTF。 Classic flip retest。 **Conditional/HQ**。

**M51 Smart BOS** (2925, 2945) · tier 3 — strong BOS ≤40 bar + zone + trigger。 Model B retest。 **Conditional** (zone not required to be the BOS leg's OB — any bull zone)。

**M54 Smart S&D trap** (2929, 2946) · tier 4 — W3: chain unanchored。 **Low-quality as coded** (A grade with no confluence); HQ after W3 fix。

### Group 3 — Break continuation (Model B/D)

**M05 / M15 / M02** (2755, 2799, 2735) · tier 2 — pin within 1 bar of break / break candle is pin / shrinking wicks。 contBrk (structural only)。 D3 (CHoCH excluded)。 No retest wait; entry at break +1。 Q7: no。 **Conditional** (M15 best: break candle took liquidity first)。

**M01** trap (2734) · tier 2 — growing wicks after break + strong close back。 **Conditional**。

**M69 IFC** (3062, 3129) · tier 1 — effectively dead at min 8 (W14)。 **Invalid (as configured)** — either re-tier or cut。

## 3. Classification summary

| Class | Modules |
|---|---|
| High-quality candidate | M45★, M68, M37, M39 (real CHoCH + sweep), M46 (after D1 + reliability ≥2) |
| Conditional | M10, M41, M42, M36, M73, M33, M51, M09, M40, M70, M62, M72, M05, M15, M02, M01, M45 (BOS form) |
| Low-quality | M08 (no PD gate), M58, M54 (as coded) |
| Invalid as configured | M69 (tier 1, min 8) |

## 4. Model support (Phase 5) — code-এ যা আছে

| Model | Steps supported | Missing | Modules |
|---|---|---|---|
| A Sweep reversal | sweep (qualified) ✔ · reclaim ✔ · MSS/CISD ✔ (M45/M46/M68) · retrace zone ✔ (zone; FVG dead D1) · invalidation ✔ · target/room ✔ | retrace **limit** entry (W1); M10 lacks MSS | M10 M46 M45★ M68 M41 |
| B BOS + retest | bias ✔ · displaced BOS ✔ · retest zone ✔ (M51) · acceptance = trigger ✔ · chase guard ✖ (W2; M51 ≤40 bar only) | retest must be BOS leg's own OB/FVG | M51 M33 M05/M15 (no retest) |
| C FVG/OB retrace | bias ✔ · displacement leg ✔ · OB ✔ / FVG ✖ (D1) · fresh/mitigated ✔ · depth: 50% ✔ · confirm ✔ · room ✔ | FVG tap; OTE limit | M37 M42 M36 M39 M73 |
| D Trend continuation | structure ✔ · pullback zone ✔ · opposing liquidity check ✖ (W5) · trigger ✔ · extended-move guard ✖ (W2) | W2, W5 | M08 M51 M02 |

## 5. Too early / too late

- **Early:** M10 (sweep candle, no shift); M05/M15 (break +1, no retest); M46 in IMMEDIATE with harami。
- **Late:** every CONFIRMED-mode zone module (entry above reaction high, W1); M58 (neckline); continuation modules in premium (W2)。
- **Right timing but blocked:** FVG retrace (D1); CHoCH retest family (D3); counter-trend sweeps (D5)。

## 6. Conflicts / redundancy found

- `arrivalStrong` used as hard gate (arrOk), as f_conf −2, and inside M36/M42 (`arrivalWeak`) — consistent but heavy。
- `zoneOkBull` 50% rule + M42's `ft.zb.fifty` duplicate (harmless)。
- M46 reliability term 3 duplicates arming (sweep)。
- D5 triple context penalty。
- W9 location triple credit。
