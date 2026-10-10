# 04 — Improvement Roadmap · v8.4.1 → v8.5.0

তারিখ: 2026-10-10। **Production script-এ কোনো change করা হয়নি।** Approve হলে **নতুন ফাইল** `SMC_Pattern/SMC_v8.5.0.txt`-এ incremental patch (a → b → c order), প্রতিটা step-এর পরে TradingView compile + 05-এর regression। Token ceiling 100,256: প্রতিটা item-এর আনুমানিক খরচ + cut source। v8.4.1-এর compile status আগে confirm করুন — header "compile to confirm"।

## P0 — Critical
**কিছু নেই।** Repaint নেই, direction reversal নেই, state corruption নেই, crash path নেই।

## P1 — High

| ID | সমস্যা | Fix | Token | Validation (05) |
|---|---|---|---|---|
| D1 | TOUCH mode-এ `atBullFvg/atBearFvg` dead (1316–1323 vs 2453–2461) | scan: `(not g.mitigated or g.mitIdx == bar_index)` | +15 | M41/M46/M68 count TOUCH vs 50% mode; 50% mode unchanged |
| D2 | Pend-path sweep SL wick-এর উপরে (1497/1515, 2729, 3318) | `Liq.wickX`; `Feat.sweptExtLo/Hi`; `f_stop` min/max | +45 | sweep-signal risk distribution; count same |
| W1 | CONFIRMED+CLOSE late entry | `i_entryPx` option `RETRACE`: armed → limit at displacement-leg 50% / fresh FVG top; expire N bar; signal on touch | +120 | fill %, R distribution vs CLOSE/ZONE EDGE |
| W2 | Continuation modules buy premium | `contL/contS` ∧ `pdPct > i_pdDeep` → reject 2 (score-only for reversal set); `pdBeyond` exempt | +30 | continuation signal pdPct histogram; expectancy by bucket |
| W3 | M54 chain unanchored | `m54Zb` anchor; sweep ≤1.5 ATR under it; BOS leg after sweep; entry zone near anchor / BOS-leg OB | +40 | M54 count ↓, score unchanged; OOS |

## P2 — Medium

| ID | সমস্যা | Fix | Token |
|---|---|---|---|
| D3 | `breakUp/Dn` CHoCH বাদ (2406–2419) | `or st.bullCHoCH`; `breakLvl = st.chLvl` | +20 |
| D4 | HTF non-displaced break consumes pivot (2148–2151) | `hHiBroken/hLoBroken := true` শুধু যে branch bias নিল | +15 |
| D5 | Counter-context −3 (3456–3465, 3273) | INCOMPLETE শর্ত থেকে `gateUp != 2` বাদ | −10 |
| D6 | `f_moveStrength` FVG direction-blind (1377) | `isBull` param + filter | +15 |
| W4 | maxRR hard reject | band-এর বাইরে nearest real → `tgt = "FAR"`, note; reject নয় | +15 |
| W5 | Path check zone-only | FVG (strict) + qualified liq (warn) loop | +45 |
| W6 | 20-bar RANGE decay | default `i_rangeBars` 20 → 40; tooltip | 0 |
| W7 | POOL = 2 touch | `qual`: EQH/EQL kind ∨ touches ≥3 ∨ PD/PW/SES | +10 |
| W8 | 1-tick confirm | `close > ref + 0.1 ATR ∧ body ≥ 0.4` (input) | +12 |
| W9 | Correlated conf | location single term (OTE +2 / discount +1 / deep −1); `bslAbove ≥ 2`; session 0 when filter on | −20 |
| W10 | M10 no shift | input `M10 confirm`: Off / 1-bar close above sweep high / CISD | +35 |
| W11 | M41 react FVG freshness | `atBullFvgFresh` (idx ≥ sweptLowBar) | +20 |
| T1 | M39 tier | real CHoCH ∧ sweep ≤10 bar → rank 43 else 31 | +10 |
| T2 | M73 tier | 43 → 33 (no liquidity event) | 0 |

## P3 — Enhancement / cleanup

| ID | কাজ | Token |
|---|---|---|
| D7 | dead: `brkTimeOk` + plot + `i_idmTime` block (2604–2611, 3850, 822); `sweptPool`; `incomplete` field | −60 |
| D8 | opposite event clears pending | +6 |
| D9 | weak-CHoCH fail level | +8 |
| D10 | fallback→IMMEDIATE only M10 | +4 |
| D11 | cosmetic labels/notes | 0 |
| W12 | `stFail` decay | +8 |
| W13 | London session H/L levels (`asiaHi/Lo` pattern) | +40 |
| W14 | M69 → rank 21 or cut | +0 / −80 |
| W16 | HTF FVG age cap | +10 |

## Token accounting

P1 ≈ +250 · P2 ≈ +170 · P3 ≈ +20 (D7 cut −60 সহ) → **≈ +440**।

Cut sources (সব default-OFF, tier 1–2, 03-এ Low/Conditional-candle-only; delete order):
1. M63 direct breakout (3002–3013, 3094–3095, bids, `i_noRetest`, `dbDir/dbBar/dbLvl/dbNear` Sx) ≈ −160
2. M65 TL+flipped (3034–3051, 3096–3097, bids, `m65*` Sx) ≈ −220
3. M03 inside-bar (2739–2751, `insideOk` 2425, bids) ≈ −120
4. M11 doji+breakout (2780–2793, bids) ≈ −110
5. M29 strong-move trap (2803–2806, w29, bids) ≈ −100
6. M06/M07 multi-pin (2757–2762, bids, `pinCountMin`) ≈ −110
7. M04 doji reversal (2752–2753, `dojiCountMin`) ≈ −60
8. M14 (2797–2798) ≈ −60, M12 (2795–2796) ≈ −60
9. D7 dead features ≈ −60

Cumulative ≈ −1,060 → net ≈ **−600**। Order: cut 1–3 + D7 আগে (−560 cover P1+P2), বাকি cut শুধু compile fail হলে। প্রতিটা cut-এর পরে `f_en` input, `en_M*`, bid line, Sx field একসঙ্গে যায়; data-window plot label update।

## Implementation order

**a. Correctness, behaviour-neutral বা narrow** (একসঙ্গে compile): D1, D2, D6, D3, D4, D8, D9, D10, D11, D7 cut, M63/M65/M03 cut।
Regression: 05 §3 baseline vs a — expected: M41/M46/M68 ↑ (D1), sweep risk ↑ (D2), STRONG BOS count ±(D6), CHoCH+retest family ↑ (D3), HTF flip earlier (D4)।

**b. Scoring / gating** (defaults change): D5, W2, W6, W7, W9, T1, T2, W14।
Regression: score histogram shift, reject-code distribution, signal/day per module। Threshold `i_minScore` re-check (OOS)।

**c. Entry model** (new behaviour, input-gated, default off until validated): W1 RETRACE, W8, W10, W4, W5, W11, W3।
Regression: A/B each input separately (05 §4)।

## Per-change record (template, 05-এ ফলাফল)

| | Problem | Evidence | Root cause | Solution | Benefit | Downside | Validation | Regression |
|---|---|---|---|---|---|---|---|---|
| D1 | FVG flags dead | 1316–1323, 2453 | mitigation precedes scan | mitIdx==bar_index | FVG path alive | more signals (M41/46/68) | count by mode | 50% mode identical |
| D2 | sweep SL inside wick | 1497, 2729, 3318 | extreme not stored | Liq.wickX | honest risk | fewer M10 pass 2R | risk dist | count same |
| W1 | late entry | 2698, 3337 | no retrace step | RETRACE limit | ½ risk, 2× R | unfilled trades | fill %, R | CLOSE mode identical |
| W2 | premium buys | 868, 2349 | gate module-blind | cont set gate | removes late cont. | fewer cont. signals | pdPct hist | reversal set identical |
| W3 | M54 loose | 2507–2528 | no anchor | anchor fields | A-grade honest | M54 rare | count, OOS | — |

## Approval ask

- a → b → c ক্রমে যাব, না কি শুধু a?
- W1 RETRACE: default `CLOSE` রেখে option হিসেবে, না default `RETRACE`?
- Cut list: M63/M65/M03 + D7 approve? (সব default-OFF, কোনো চলমান setup হারায় না।)
- v8.4.1 TradingView-এ compile হয়েছে? (token headroom জানা দরকার।)
