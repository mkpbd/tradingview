# AUDIT-v10 — Forensic audit of `Demand + Price Action-9.pine` and the V10 build

Date 2026-09-05 · Source audited: `Demand + Price Action-9.pine` (5,599 lines, 3,298 code lines) · Output: `Demand + Price Action-10.pine` (5,171 lines, 3,495 code lines). V9 is untouched.

**Compile status: NOT compiled locally.** There is no Pine compiler outside TradingView. Every V9 header before this one carried the same caveat, and V9 declared itself at ~99.5 % of the CE10117 compiled-token cap by an uncalibrated local count — it too was never compiled. Load V10 in the Pine editor and report the exact error text if any. Section 9 lists the ranked removal levers if CE10117 (token cap) or CE10295 (global-scope size) appears.

---

## 1. Executive summary

**Biggest bugs**

1. **P2 OFF killed every signal (P0).** `f_p2Dist` returned `na` for all four targets when the liquidity map switch was off; `rrOkL/S = not na(rr) and …` was therefore false on every bar; machine, engines and models were all refused with "no target". The tooltip promised a fallback to the last swing that did not exist.
2. **MSS → displacement had no causal link (P1).** Tier A's structure leg was `recentMss (10 bars) AND dispUpLive (any body ≥ dispFactor in 10 bars)`. An MSS nine bars ago plus an unrelated impulse now produced A. The machine's own anchor rule ("first FVG after the shift") accepted a gap up to 20 bars later.
3. **RR was measured to the nearest opposing level, not to a target (P1).** A swing 1.2 R away refused a setup whose external target paid 3 R; conversely nothing ever said "opposing liquidity inside 1 R = path blocked".
4. **Retest had no dwell or depth (P1).** A visit that sat inside the anchor for six bars was still "the first retest".
5. **POI freshness was binary (P1).** Zones had a visit count but no mitigation %; typed FVGs had a fill state but no visit count; the third test of a zone was still tier A.
6. **Weak engines proposed no stop (P2).** IB break, doji, HTF CRT/TBS fell back to a 2-bar low, so their RR to the gate looked excellent.

**Biggest accuracy weaknesses**: TRIG_LOOK = 10 as the only structure-age test; `f_sweepQual` grade 2 on penetration OR firm close (a wick was a sweep); HTF POI location alone lifting the bias filter; CISD and internal noise reaching B and then being displayed at the default "B and above".

**Biggest architectural weaknesses**: two ~110-line mirror-copy machines at global scope with outside writes into their state (M18 `mcLSl := na`, M19 `suL := 0`); no setup identity, so the journal could not say which liquidity event, shift, displacement and FVG belonged together; P3Zone / P4Zone geometry still read back from drawings (the v5.3 F2 latent fault); target selection, RR gate and TP ladder each computed their own view of "the target".

---

## 2. Issue register

Severity: **P0** critical bug · **P1** high-impact accuracy · **P2** medium · **P3** enhancement. Every item names the V9 location, the defect, why it is wrong, the trading impact and the fix as implemented in V10.

| # | Sev | Location (V9) | Problem | Why wrong | Trading impact | Fix (V10) |
|---|-----|---------------|---------|-----------|----------------|-----------|
| 1 | P0 | M13B `f_p2Dist`, M17B `rrOkL/S` | `p2Enable` OFF → all targets `na` → RR gate fails | `na` treated as "no target = refuse" is right, but a display-scope switch must not produce it | Zero signals with the switch off; user thinks the market is quiet | External map + last fresh swing always built; `p2Enable` only adds zone edges and EQ pools (V10-01) |
| 2 | P1 | M16 `f_tier` `aTrig` | MSS and displacement tested in two independent 10-bar windows | No causality between shift and impulse | Random impulses graded A after a stale shift | `f_shift` lineage: displacement on the shift candle or ≤ `maxDispDelay` after; `chainL/S` (V10-02) |
| 3 | P1 | M17 stage 3 anchor | "First FVG after the shift" within `retWait` (20) | A gap 15 bars later is not the shift leg's gap | Late, unrelated anchors → late entries | FVG must be created ≤ `maxFvgDelay` after the shift; none + no zone = invalidated "no shift-leg FVG" (V10-08) |
| 4 | P1 | M6 `TRIG_LOOK`, `recentMssUp` | 10-bar memory, no age grade for A/A+ | 1-bar and 9-bar shifts are different evidence | Stale shifts made A/A+ on 1M–5M | `f_ageQ`: ≤1 strongest · ≤`mssAgeAp` A+ · ≤`mssAgeA` A · else B; score × age factor (V10-03) |
| 5 | P1 | M17B `rrL`, M19 ladder | RR to the nearest level; ladder computed separately | Nearest level is a waypoint or an obstacle, not the target | Refused 3 R setups; never flagged blocked paths | `f_tgt`: path check (`minPathR`), TP2 = best fresh level ≥ rrMult (else ≥ v5MinRr, flagged), RR to TP2, one engine for gate and ladder (V10-04) |
| 6 | P1 | M17 `suLVisit/suLIn` | Visit had no start bar, dwell or depth | Sitting inside a level is acceptance, not rejection | Multi-bar "retests" entered late | `retStart`, dwell (1–2 A+ · 3 A · 4–5 B · > `maxRetDwell` failed), depth 0..1+ scored (V10-05) |
| 7 | P1 | M13 `Zone.tests`, `nbFresh`; M12C `P3Fvg.mit` | Binary freshness; FVGs never counted visits; `zoneMaxTests` 3 | Third touch is a dead level | Recycled POIs graded A | `Zone.mit` + `f_life` (FRESH→1ST TOUCH→MITIGATED→WEAK→DEAD); `P3Fvg.vis`, entry-grade needs ≤1; `zoneMaxTests` 2 (V10-06) |
| 8 | P1 | M17 (both machines), M18, M19 | Two mirror machines at global scope; M18/M19 wrote `suL`, `mcLSl` from outside | Fragile, unauditable, CE10295 risk | State desync when the arbiter voided a machine entry (stage 4 lived on) | One `f_machine`; verdict (`mcAccL`) and real TP2 (`mcTgtL`) passed in; SETUP-n id; lineage fields (V10-07) |
| 9 | P1 | M5 `f_sweepQual` | Grade 2 on `firm OR pen ≥ 0.25 ATR` | A 0.3-ATR wick closing one tick inside has no rejection evidence | Weak pokes armed the machine | Grade 2 needs `firm AND pen ≥ 0.125 ATR` (V10-09) |
| 10 | P1 | M5 (missing) | No RAID→BREAKOUT→TRAP classification; only one-candle sweeps | An accepted break that fails in ≤6 bars is the strongest liquidity event | Breakout traps never armed the primary path | `f_brkTrap`: type 7 grade 3 into the sweep memory; `[LIQ] Breakout trap` alert (V10-09) |
| 11 | P1 | M16 score, `minScore` | Alignment score 0–100 with no causal buckets; default 0 (off) | Points for context, not for the chain | Score never said no | Entry Quality Score (9 buckets); < `minScore` (60) = NO TRADE; A ≥ `scoreA`, A+ ≥ `scoreAp`; can only remove a tier (V10-10) |
| 12 | P1 | M18 `f_rej` (debug only) | Refusal reasons only in a debug row; generic labels | Operator could not see why | Blind waiting | Expanded reason set incl. `f_cause`; `⚙ No-trade` row always visible; machine writes "entry refused · reason" to its Setup row (V10-11) |
| 13 | P2 | M1 `tierMode` default "B and above" | B = trigger + (liquidity OR POI) shown by default | L1 aggressive noise on the chart | Signal spam | Levels L1/L2/L3 = B/A/A+; default "A and above" (V10-12) |
| 14 | P2 | M11 `CHOP_RANGE_ATR` 6, M16B `ltLowVol` (dead) | Hard-coded ATR numbers; low-vol flag never read | Not normalised across instruments | Chop filter mis-tuned; nothing for extreme vol | `volReg` from ATR percentile: LOW (exec +10) · NORMAL · EXPANSION · EXTREME (machine only, anti-chase halved) (V10-13) |
| 15 | P2 | M8 `newsState` 0/1/2 | No pre-news; post-news let the machine enter the first impulse | First post-news candle is repricing | Entries into the print | 5 states: PRE-NEWS (`newsPreMin`) · RISK · REPRICE (`newsRepMin`, nothing enters) · CONFIRMATION · NORMAL (V10-14) |
| 16 | P2 | M16 `longCtx` `v9HtfLoc` | HTF POI alone passed the bias filter | Location ≠ reversal model | Counter-trend entries on an HTF box tap | Needs sweep in play AND external shift (`htfRevL/S`); HTF conflict −5 in the score (V10-15) |
| 17 | P2 | M16E `f_execQ` | No wick-rejection component; max 110 capped | Pin bars under-scored vs engulfing | Confirmation types treated alike | Rebalanced to 100 with wick rejection 10 (V10-16) |
| 18 | P2 | M14 IB / doji, M9 HTF CRT/TBS | No proposed stop → 2-bar fallback | Tiny risk → inflated RR | Passed the RR gate too easily | IB low / doji window extreme / HTF raid-candle extreme (V10-16) |
| 19 | P2 | M12C `P3Zone`, M13C `P4Zone` | `box.get_top/bottom` read back from drawings | Returns `na` once the 500-box cap evicts the drawing (v5.3 F2 class) | Silent geometry loss | `top/bot` fields (V10-17) |
| 20 | P2 | M16D BRK scan | Third per-bar walk of `zones` | Nothing mutates `zones` between M13 and M16D | Runtime | Folded into the nearest-POI walk (V10-17) |
| 21 | P3 | M16B `ltLowVol/ltAtrAvg`, M4 `tlTouchMin`, `ltP1…7`, `p3T67Trig*` | Dead code | — | — | Removed |
| 22 | P3 | M20 journal | No lineage | — | — | Journal prints SETUP-n · chain (liq → shift q → disp q → FVG → retest # · dwell · depth) · POI life · exec · path · score · L · RR |

**Verified correct, deliberately unchanged**: all `request.security` sites (lookahead_on + `[1]`); turtle-soup age sign; confirmed-pivot levels; `f_taken` liquidity lifecycle; arbiter ranking; per-class stop slots; cooldown / POI-used dedup; session ladder; `f_structure` protected-swing rule.

---

## 3. KEEP / IMPROVE / REPLACE / REMOVE

| Module | Verdict | Reason |
|--------|---------|--------|
| M3 candle anatomy, CISD, IFC | KEEP | Correct, confirmed-only |
| M4 pivots, EQ pools, trendlines | KEEP (dead const removed) | Correct; `tlTouchMin` was always 0 |
| M5 liquidity engine | IMPROVE | Grade-2 rejection evidence; breakout-trap classifier as writer |
| M6 structure | KEEP + ADD | `f_shift` lineage sits beside it (placed after M12 for the FVG anchors) |
| M7 HTF bias, correlation | KEEP | Correlation now also a score modifier |
| M8 sessions / news | IMPROVE | Five news states |
| M9 HTF CRT/TBS/POI | IMPROVE | Real HTF stops returned |
| M10 dealing range | KEEP | — |
| M11 regime | KEEP + ADD | Volatility regime |
| M12 FVG anchors | KEEP + ADD | Lineage |
| M12B P1 structure | REMOVE (V10-18, compile cap) | Fed only the Strict floor, a rare machine flip and QM at default; M6 is the structure engine |
| M12C typed FVGs, BPR, hCHoCH | IMPROVE | Visit count; P3Zone geometry as data |
| M13 zones | IMPROVE | Mitigation %, life state, BRK fold |
| M13B liquidity map | IMPROVE | Fallback; consumed by the new target engine |
| M13C corrected OB | IMPROVE | P4Zone geometry as data; QM zones removed with P1 (V10-18) |
| M14 CRT/TBS/TL/IB/doji | IMPROVE | Stops for IB / doji |
| M15 FEM | KEEP | — |
| M16 score | REPLACE | v3 alignment score → entry quality score (M18A) |
| M16 tier ladder | IMPROVE | Causal chain, age, POI life, vol-adjusted exec |
| M16D P7 models | KEEP | BRK reads the folded scan |
| M16B trap engine | REMOVE (V10-18, compile cap) | Lever (1) applied on first load; the M5 breakout-trap classifier carries the concept into the machine |
| M17 machine | REPLACE (behaviour-preserving) | One `f_machine`, self-resolving, lineage, dwell, depth |
| M17B gate | IMPROVE | Target engine, path, vol rule |
| M18 finalize | IMPROVE | Score, level, no-trade engine |
| M19 tracker / ladder | IMPROVE | Ladder from the target engine; machine TP2 real |
| M20 visuals | IMPROVE | Level + score on the label; lineage journal |
| M21 dashboard | IMPROVE | Score/chain row, No-trade row, news states, vol |
| M23 alerts | KEEP + ADD | Same alertconditions; dynamic alert carries level/score; one alert() line for traps |
| Header history v4–v8 | REMOVE (comments) | Zero compile cost; 900 lines shorter; full text stays in V9 |

---

## 4. Signal flow (V10)

```
Liquidity event      sweep (f_sweepQual ≥ 2: firm close-back AND penetration)
                     or BREAKOUT TRAP (accepted break fails inside TRAP_WIN)   → SETUP-n armed
       ↓
MSS / external CHoCH (f_structure, protected swing) — grade 1/2/3 — age graded (f_ageQ)
       ↓
Displacement         ON the shift candle or ≤ maxDispDelay after (f_shift.dBar) — grade ≥ minDispQ
       ↓
Shift-leg FVG        created between the liquidity event and ≤ maxFvgDelay after the shift (f_shift.gBar / machine anchor)
       ↓
First retest         visit #1 · dwell ≤ maxRetDwell · depth scored · entry close ≤ chasePoiAtr from the edge
       ↓
Confirmation         pin / engulfing / IFC / CISD, f_execQ ≥ v8ExecA (+10 in LOW volatility)
       ↓
Target               f_tgt: fresh map → path not blocked (minPathR) → TP2 = best fresh level ≥ rrMult → TP1 · TP3
       ↓
RR                   effective RR to TP2 ≥ v5MinRr; no target = refused
       ↓
Score                0–100 (liq 15 · HTF 15 · POI 15 · shift 15 · disp 10 · FVG 10 · retest 10 · target 5 · session 5)
                     < minScore = NO TRADE · caps the tier (A ≥ scoreA · A+ ≥ scoreAp)
       ↓
Signal               arbiter: one direction per bar; tier × level; label · journal · alert
       ↓
Consumed             POI used (0.25 ATR, zoneMaxAge) · machine ACTIVE resolves on its own SL / real TP2
```

Entry levels: **L1 AGGRESSIVE** = tier B (POI touch + rejection, or trigger + liquidity) · **L2 CONFIRMED** = tier A (liquidity in play + at POI with life ≤ 2 + causal chain + age ≤ mssAgeA + exec) · **L3 INSTITUTIONAL** = A+ (L2 + age ≤ mssAgeAp + shift-leg FVG + HTF bias & alignment + core session + strong sweep type ≥ 2 + range side + exec ≥ v8ExecAp + clean path + no correlation conflict + POI tier ≤ 2 + first touch; machine adds dwell ≤ 2 and the FVG anchor).

---

## 5. Hard no-trade reasons

Config: `config: HTF ≤ chart` · Context: `HTF conflict` (bias filter without an LTF reversal model) · `killzone` · `pre-news` · `news window` · `post-news reprice` · `chop` (unless institutional sweep) · `cooldown` · Ladder: `tier<floor (no ext shift | no causal displacement | stale shift | POI weak/dead | FVG 2nd visit | no liquidity event)` · Floor layers: `liq` · `poi` · `struct` · `disp` · `v4struct` · `chase` · `path blocked` · `no target` · `RR` · `extreme vol · machine only` · `post-news` (engines need the whole narrative) · Machine: `no shift-leg FVG within N bars` · `FIRST RETEST FAILED (dwell N > max)` · `FIRST RETEST FAILED (left the POI unconfirmed)` · `anchor POI violated` · `sweep undone` · `opposing displacement` · `POI violated` · stage expiries · `entry refused · <reason>` · Finalize: `range side` · `clash` · `POI used` · `score N < minScore` · `score-graded below the tier filter`.

---

## 6. Repaint / future-data audit

```
Repainting risk found:      NO
Future-data leakage found:  NO
Lookahead risk found:       NO
```

- All 6 `request.security` sites use `lookahead_on` **with** an internal `[1]` offset (the documented non-repainting idiom). The two series added in V10 (`hSlL`, `hSlS`) are offset `[1]` like the rest. The HTF CRT/TBS fire on the first chart bar of the next HTF bar (`newHtfBar`) — one HTF bar of lag, not a repaint.
- Pivots: `ta.pivothigh/low` levels are written only on the confirmation bar (`pivLen` bars after the pivot) and every consumer reads the stored level. Confirmed vs developing pivots are never mixed.
- Every cross-bar state change (arrays, UDT fields, `var` state in `f_machine`, `f_shift`, `f_brkTrap`, `f_taken`) is gated by `barstate.isconfirmed`. Scores and gates are evaluated per bar but only latch through confirmed-only producers.
- `f_preNews` uses the bar's own `time` (stable intrabar); `ta.percentrank(atr)` mutates intrabar but is consumed only on the confirmed tick.
- Historical vs realtime: `barstate.isconfirmed` is true on every historical bar, so evaluation is identical; `mcAccL/mcTgtL` are read the bar after they are written on both.
- Labels / boxes are created on confirmed bars only; last-bar drawings (`barstate.islast`) are display-only extensions.

---

## 7. Validation

| Check | Status |
|-------|--------|
| Pine compilation | **Not run — no local compiler.** Static checks passed: declaration order of all new symbols, tuple arity (f_machine 22/22, f_v5Gate 20/20, f_shift 7/7, f_tgt 7, f_brkTrap 3/3, f_p3Nearest 4/4, HTF tuple 8/8), parameter counts (f_machine 25/25, f_rej 17/17, f_v5Why 9/9), no undefined identifiers, indentation multiples of 4 (continuation lines keep the V9 5-space convention), no tabs. |
| Runtime safety | Division guards: `h > 0`, `risk > 0`, `hz > 0`; `str.substring` guarded by `str.length ≥ 9`; `ta.percentrank` na-guarded; array counter for setup ids. |
| `na` handling | Targets: `na` = refused, never a pass; P2 OFF no longer produces `na`; all `math.abs(na)` comparisons evaluate false by Pine semantics. |
| Object lifecycle | No new drawings; zones/FVGs/EQ/P3/P4 caps unchanged; P3Zone/P4Zone geometry no longer depends on the box surviving the 500 cap. |
| Alerts | 16 alertconditions unchanged; dynamic alert adds level, score, TP1; one new alert() line ([LIQ] Breakout trap). Output slots ≈ 46/64 incl. security series. |
| State transitions | f_machine: IDLE→SWEPT→AT POI→SHIFTED→(anchor)→RETEST→TRIGGERED→ACTIVE→IDLE with a named reason on every exit; refused entry releases the bar after via `mcAccL` (V9 released the same bar — one-bar difference, re-arm on that bar preserved). |
| Duplicate prevention | Unchanged cooldowns, POI-used memory, first-visit-only; plus FVG `vis ≤ 1`, zone life, one setup id per arm. |
| Realtime / historical | Identical by construction (confirmed-only state). |
| Performance | One fewer `zones` walk per bar; new per-bar work: f_shift ×2, f_brkTrap ×2, f_tgt ×2, f_score ×2, f_preNews ×3 (string ops on inputs — cheap), percentrank. |

**Not done / not claimable**: no backtest, no accuracy figure. The tracked TP2/SL/ambiguous counters remain mechanical counts, not statistics.

---

## 8. Configuration (new group "1 · Core engine — causality · retest · score (v10)")

| Input | Default | Meaning |
|-------|---------|---------|
| mssAgeA | 5 | max shift age (bars) for tier A |
| mssAgeAp | 3 | max shift age for A+ |
| maxDispDelay | 2 | displacement on the shift candle or ≤ N bars after |
| maxFvgDelay | 3 | shift-leg FVG within N bars of the shift |
| minDispQ | 2 | min displacement grade in the shift leg (A / A+) |
| maxRetDwell | 5 | bars price may sit inside the anchor |
| retDepthLo / retDepthHi | 33 / 66 | optimal mitigation band (%) |
| chasePoiAtr | 1.5 | entry close within N ATR of the anchor edge (halved in EXTREME) |
| minPathR | 1.0 | nearest opposing fresh liquidity must be ≥ N R (path) |
| scoreA / scoreAp | 80 / 90 | entry score for A / A+ |
| volLook / volExtPct | 200 / 95 | ATR percentile lookback / EXTREME threshold |
| newsPreMin / newsRepMin | 10 / 5 | pre-news block / post-news reprice block (minutes) |

Changed defaults: `tierMode` "A and above" (Level 2+; with `v5RegUp` ON, engine triggers outside TRENDING need A+ — the machine keeps A) · `minScore` 60 (now the entry score) · `zoneMaxTests` 2. Set `tierMode` "B and above" and `minScore` 0 to approximate V9 output volume.

---

## 9. Compile budget — what happened on first load (V10-18)

TradingView returned **CE10117: compiled 106,706 tokens, limit 100,256** (6.4 % over). Two removals, both named in advance as levers:

| Removed | ~compiled tokens | What it did at default settings | What replaces it |
|---|---|---|---|
| MODULE 16B liquidity-trap engine (LT-1…7) | ~5,400 | Candidate producer since v7; short-biased 5:2 | M5 breakout-trap classifier (`f_brkTrap`) writes an accepted-then-failed break into the sweep memory as a type-7 grade-3 liquidity event → the primary machine trades trap → MSS → displacement → shift-leg FVG → first retest |
| MODULE 12B P1 HH/HL engine + 13C Quasimodo zones + ·ev count | ~6,900 | HH/HL labels (display); Strict-mode "V4STR" layer; a rare strong-level flip invalidation; QM zones (POI tier 3, P7 QM model); evidence-class metadata | Primary structure engine M6 (protected swings · BOS · CHoCH · MSS) is untouched; Strict = LIQ + POI + STRUCT + DISP; POI tier 3 = OTE / BPR |

Estimated compiled size after both: ~94,000 (≈ 6 % margin) by a tokenizer calibrated on the 106,706 reading. Every trigger engine, BPR, hidden CHoCH, trendlines, FEM, SB/BRK/FVG4 models, the dashboard (all rows) and the alerts are intact. The removed modules' full text is in `Demand + Price Action-9.pine` for a companion indicator.

If the cap is hit again, remaining levers in order: IB / doji triggers (~1,650) · dashboard debug rows 18–19 (~600) · MFE/MAE tracker (~480) · library split of the pure helpers.

- **CE10295 (global-scope size)** — wrap the M18 finalize block (from `mcApL` to `mcAccS :=`) into `f_finalize()` returning a tuple; the machine and the score are already functions.
- **Any other error** — report the exact text and line; every V10 change is tagged `v10` / `V10-nn` in the source for bisecting.
