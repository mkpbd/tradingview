# AUDIT-v11 — bug pass, Quasimodo restoration, Silver Bullet fidelity, token pass

Date 2026-09-07 · Source audited: `Demand + Price Action-10.pine` (4,517 lines / 2,979 code lines) · Output: `Demand + Price Action-11.pine` (4,703 lines / 2,997 code lines). **v10 and v9 are untouched.**

**Compile status: NOT compiled.** There is no Pine compiler outside TradingView, and v10 itself was never re-loaded after its own V10-18 removals — so the "~94,000 compiled" figure under v10 is an estimate, not a measurement. Load v11 in the Pine editor and report the exact error text if any. §5 has the budget arithmetic and the ranked levers.

---

## 1. What was asked and what was done

| Brief | Delivered |
|---|---|
| Remaining logical / causal bugs | 6 fixes, V11-01 … V11-06. One is P0 (the drawn/tracked RR was the RR of a trade nobody took), one is a re-opened P1 (the same double-count V9-07 closed in the ladder was still open in the SB model), one is a P1 back door around v10's own V10-09 sweep tightening. |
| Quasimodo quality + entry model | V11-07. Restored on the CORRECT definition, without resurrecting the 5,200-token engine V10-18 deleted, and wired into the existing zone lifecycle it never had. |
| Silver Bullet fidelity to ICT rules | V11-08. The macro window now gates the whole sequence, not just the entry; the entry is the shift leg's own FVG, not any FVG. |
| Token efficiency | V11-09. Six dead structures removed. Net still **+0.83 %** vs v10 — see §5. This is the one brief only partly met, and deliberately so: I did not pay for it by cutting diagnostics from a build that has never run. |

---

## 2. Issue register

Severity: **P0** critical · **P1** high-impact accuracy · **P2** medium.

### V11-01 · P0 · The TP ladder was measured against a different stop than the RR gate

**Where** M17B `f_v5Gate` → `f_tgt(true, close, slL)`; M19 `slP`; M20 E-line, journal, dynamic alert.

**Defect.** `f_slPick` ranks stops **machine > model > engine** and runs *before* the gates, so `sigSLLong` at gate time is the highest-ranked **raw** candidate's stop. `f_v5Gate` fed that stop to the target engine, which selected `TP2 = the best fresh level paying ≥ rrMult × risk`. MODULE 19 then drew, tracked and alerted using `slP` — the **accepted** producer's stop, re-picked at line 4030 after the arbiter.

**Why it is wrong.** Those are different numbers whenever the machine raised a candidate and an engine won the bar (the machine's stop reaches back to the sweep wick; a CRT stop is one candle). TP2 was then "the level that pays 2R on the *machine's* risk" printed against the *engine's* risk. Every RR the operator could see — the E-line, `f_meta`'s `RR 1:x`, the journal, the dynamic alert — described a trade nobody took, and `trdTP2` tracked it, so the TP2/SL outcome counters were counting the wrong target.

**Trading impact.** Systematically misreported reward. With a machine stop ~3× an engine stop, an engine trade shown as "RR 1:2.1 →liq" is really ~1:0.7 to that level.

**Fix.** `f_tgt` is a pure function of (side, entry, stop) with no state, so MODULE 19 re-runs it once against `slP`. The **gate is deliberately unchanged** — it must judge the candidate it ranked, not the one that won; changing it would let a wide-stop machine candidate be admitted on an engine's tight-stop arithmetic. `na` entry/stop on non-signal bars propagate to `na` targets, which the fallback rows already handle. The journal now prints both: `RR 2.1 (gate 1.4)`.

### V11-02 · P1 · The Silver Bullet could arm, shift and enter on ONE candle

**Where** M16D `f_p7Sb`.

**Defect.** The three stage tests ran as sequential `if`s in a single bar pass: `st == 0 and arm → st := 1`, then `st == 1 and shift → st := 2`, then `st == 2 and entry → fired`. Nothing required a later bar.

**Why it is wrong.** This is exactly V9-07 — "one candle cannot be the shift AND its own retest" — closed in the tier ladder (`shift bar < entry bar`) and in the machine (`bar_index > stBar`), and left open in the model. A single candle that sweeps PDL, breaks structure and taps an FVG was scored as a complete three-stage institutional narrative and reached the arbiter at model class 1 (above every technical trigger).

**Trading impact.** The SB fired on wide single-bar reversal candles — the worst possible entry, at the extreme of the range it just travelled.

**Fix.** `shift` and `entry` each require `bar_index > bar_`.

### V11-03 · P1 · The breakout-trap classifier was a back door around V10-09

**Where** M5 `f_brkTrap`.

**Defect.** V10-09 tightened `f_sweepQual` so grade 2 needs **both** a firm close-back **and** real penetration ("a wick is not a sweep"). The breakout-trap classifier added in the same change then armed on **any** close beyond a level with **any** body, and fired on **any** close back inside within `TRAP_WIN`, writing **grade 3 / type 7** — the highest liquidity class the script has — straight into the sweep memory.

**Why it is wrong.** A one-tick close through a swing low followed by a one-tick close back is not a trapped crowd; there is no acceptance to trap and no rejection to measure. Type 7 grade 3 clears `minArmQual` (2), clears the A+ sweep-type floor (`v8ApLiq` 2), satisfies `sslInPlay and lastSslQual >= 4` after any MSS (the CHOP exception) and scores 15/15 in the liquidity bucket. v10 closed the front door and opened a wider back one.

**Trading impact.** The primary machine armed on noise, in chop, at the highest liquidity grade.

**Fix.** The break must be displacement-grade (`body ≥ BRK_BODY_ATR × atr`) **or** penetrate ≥ `NEAR_LVL_ATR × atr`; the reclaim must clear the level by ≥ `0.5 × NEAR_LVL_ATR × atr` — the same close-back evidence `f_sweepQual` demands of a swing sweep.

### V11-04 · P2 · Machine POI tier preferred a generic zone over an OTE tap

**Where** M17 `f_machine`, the SWEPT → AT POI transition.

**Defect.** `poiT := tapHtf ? 1 : tapZone ? 4 : 3` tested the zone first, so a tap that was **both** a generic S/D zone **and** an OTE leg graded 4 (generic) instead of 3 (OTE). POI tier ≤ 2 is an A+ requirement and the tier drives 15 points of the entry score, so the worse of two true locations decided the grade.

**Fix.** `poiT := tapHtf ? 1 : tapOte or (isL ? nbQm : nsQm) ? 3 : 4`. The zone still supplies the anchor. A Quasimodo QML (V11-07) is tier 3, not 4.

### V11-05 · P2 · Tier A unreachable in a quiet tape at high exec settings

**Where** M16 `execAEff`.

**Defect.** `execAEff = v8ExecA + (volReg == 0 ? 10 : 0)`, while `f_execQ` is `math.min(100, …)`. At `v8ExecA ≥ 91` in the LOW volatility regime the floor exceeded the maximum achievable score.

**Fix.** `math.min(100, …)`.

### V11-06 · P2 · "entry refused · —"

**Where** M17 `f_machine` stage-4 release.

**Defect.** `rejL` / `rejS` are cleared to `"—"` on any bar the arbiter **accepted** another producer. A machine entry voided by the clash rule therefore released the next bar with `reason := "entry refused · —"` on the dashboard Setup row.

**Fix.** `"entry refused (arbiter)"` when the reason slot is empty.

---

## 3. V11-07 — QUASIMODO restored, on the right definition

### What v9 had, and why v10 deleted it

v9's QM was *"a close through the last LH → a demand zone between the two lows flanking that LH"*. It required the whole MODULE 12B HH/HL swing registry (`p1Swings`, the 40 % pullback rule, the validity state machine) and V10-18 deleted **both** for CE10117: the P1 engine ~5,200 compiled tokens, QM ~1,300.

### What a Quasimodo actually is

Bullish: **L1 → H1 → L2 < L1** (the *head* takes L1's sell-side liquidity) **→ a displaced close back above H1** (the right-shoulder break). The level a trader waits for — the **QML** — is the **left shoulder L1**, the level that was raided. The invalidation is the head L2.

### The reconstruction

Both prices are already in the sweep memory the instant an MSS lands:

| QM component | Already in v10 |
|---|---|
| left shoulder / QML | `lastSslLvl` — the level the sweep took |
| head / invalidation | `lastSslExt` — the sweep wick |
| right-shoulder break | `mssUp` — *external CHoCH while that raid is in play* |

So the whole pattern needs **no swing registry at all**. On `mssUp` / `mssDn`, MODULE 13 pushes a zone spanning `[head … QML]` into the **existing** `zones` array with `kind = "QM"`.

**What this buys over v9's version.** The v9 QM was a bare `P4Zone` with a three-state counter. This one inherits the full v10 lifecycle it never had: separate-visit counting, mitigation depth, the `f_life` state (FRESH → 1ST TOUCH → MITIGATED → WEAK → DEAD), `zoneMaxAge`, the spent flag, the violation/breaker flip, the nearest-POI walk, the `f_p2Dist` target map, `f_path`, the anti-chase and the POI-used dedup. A third tap of a QML is now DEAD, not tier A.

**Wiring.** `nbQm` / `nsQm` in the nearest-POI walk → POI tier 3 in `poiTL` / `poiTS`, in `f_machine`'s POI tap, and in the score's 15-point POI bucket. The P7 **QM model** returns (`p7mQm`, default ON): a confirmed rejection inside the QML with the stop under the zone.

**Two deliberate choices, stated so the next audit does not re-open them.**

1. **Dedup is non-destructive.** `f_zoneFree(…, 1)` is a pure "does a live same-side zone already cover this?" test — it deletes nothing except an already-spent overlap. The QM never evicts a legitimate FVG or order block; if one is already there, that zone is the POI. `star = true` scores the QM 3, so a later plain zone cannot evict *it*.
2. **The zone is clamped to `maxZoneAtr` from the QML edge, not from the head.** An unclamped sweep-wick band is the v5.2 W1 defect (price lives inside it, `inDemand` reads true permanently, the POI layer is satisfied for free). Clamping keeps the edge nearest price — the QML, the level you actually enter at — exactly as every other zone family in this script is clamped. **Consequence:** on a sweep wick taller than 2 ATR the P7 QM model's stop sits at the clamped edge, not at the true head. The *machine*, when it uses a QM zone as its anchor, still folds in its own held `swExt`, so its stop is at the head. If you want the model's stop at the head too, widen `maxZoneAtr`.

---

## 4. V11-08 — Silver Bullet, macro-window fidelity

ICT's Silver Bullet is a **macro-window** model: inside the killzone hour (03:00–04:00 / 10:00–11:00 / 14:00–15:00 NY), liquidity is taken, price displaces and shifts, and the entry is the FVG **that displacement leg itself created**.

| Stage | v10 | v11 |
|---|---|---|
| window | gated the **entry** only — a 20:00 raid could arm a 10:15 entry through the 15-bar stage budget | gates the **arm, the shift and the entry** (`sbWin`) |
| arm | `pdlSweep` / `pdhSweep` alone — the two levels ICT is least specific about, and often not even inside the window | any quality sweep of the **unified** liquidity memory printed **this bar** (swing · EQ · session · PD · ext swing · PW · breakout trap), graded ≥ `minArmQual` |
| shift | `mssUp or eChochUp`, any bar | same, inside the window, on a **later** bar (V11-02) |
| entry | `p6InFvgL or p6InObL` — the nearest entry-grade FVG, which can be hours old | `inShFvgL` / `inShFvgS` — the **shift leg's own FVG** from the `f_shift` lineage (created between the raid and `maxFvgDelay` bars after the shift, creation bar excluded) |
| stop | the entry candle's low vs the sweep wick | under the **FVG** and the raid wick (`shUpFvgB` / `shDnFvgT`) |

`p7SbSes` OFF now means "ignore the window entirely" — the model degrades to sweep → shift → shift-leg FVG, which is still a coherent model. Expect **strictly fewer** SB signals, better located.

---

## 5. Compile budget — read this before loading

Measured with one tokenizer across all three files (comments stripped, string literals counted as one token, as Pine does):

| File | proxy tokens | code lines |
|---|---|---|
| v9 | 32,586 | 3,298 |
| v10 | 31,497 | 2,979 |
| **v11** | **31,759** | **2,997** |

**v11 − v10 = +262 proxy tokens (+0.83 %).**

The only hard datum that exists is v10's first load: **CE10117 at 106,706** *before* V10-18. Post-removal, v10 was estimated at ~94,000 by that same removal arithmetic and never re-measured. Scaling by the proxy ratio:

- if v10 really shipped at ~94,000 → **v11 ≈ 94,800** (5.4 % margin)
- if v10 shipped nearer ~100,000 → **v11 ≈ 100,800** (**over the cap**)

I cannot distinguish those two cases without a load. If **CE10117** appears, the ranked levers are unchanged and all still available:

1. IB / doji triggers (~1,650) — the weakest producers; v10 had to invent stops for them
2. dashboard debug rows 18–19 (~600) — behind `showDbg`, which ships OFF, but compiles anyway
3. MFE / MAE tracker (~480)
4. HTF CRT / TBS candidates (~150 for the pattern half of `f_crtTbsHtf`; keep the call, `hStruct` and `hT` are load-bearing)
5. library split of the pure helpers

Every v11 change is tagged `v11` / `V11-nn` in the source for bisecting. **CE10295** (global-scope size): wrap the M18 finalize block (`mcApL` → `mcAccS :=`) into `f_finalize()` returning a tuple.

### Why the token brief was only partly met

The clean removals available after V10-18 are small (six dead structures, ~90 proxy tokens) because v10 already swept twice. The large levers left are all **feature or diagnostic removals**, and I did not take them: cutting the forensic rows out of a build that has never executed is the wrong trade when the next step is precisely to execute it and read those rows. The one diagnostic I did drop (`rrN`, the RR to the nearest opposing level) was redundant with the `blocked` flag the same engine already returns.

---

## 6. Repaint / future-data audit

```
Repainting risk found:      NO
Future-data leakage found:  NO
Lookahead risk found:       NO
```

- No `request.security` site was touched. All 6 remain `lookahead_on` **with** an internal `[1]` offset.
- Every new cross-bar state change is inside a `confirmed` guard: the QM zone push (`mssUp and confirmed`), the `f_brkTrap` arm/reclaim tests (already inside `if confirmed`), the `f_p7Sb` transitions (all three arguments carry `confirmed`).
- `f_p7Sb`'s expiry (`bar_index - bar_ > p7Win`) runs on unconfirmed ticks as it did in v10; Pine rolls script state back before each realtime recalculation, so the committed value equals the closed-bar value.
- `nbQm` / `nsQm` are non-`var` per-bar booleans recomputed in the same walk that sets `nbTop` / `nsBot`, so they can never describe a different zone than the one reported.
- V11-01's extra `f_tgt` call is pure — no state, no series offsets, no drawings.

## 7. Validation

| Check | Status |
|---|---|
| Pine compilation | **Not run — no local compiler.** |
| Function resolution | 91 functions defined, 91 called, every call site after its definition |
| Tuple arity | `f_machine` 22/22 (×2 destructures) · `f_v5Gate` 18/18 · `f_tgt` 6/6 (×3 call sites) · `f_p3Nearest` 3/3 · `f_p3Hidden` 2/2 · `f_p7Models` 6/6 · `f_p7Sb` 2/2 · `f_brkTrap` 3/3 |
| UDT integrity | `P4Zone` 8 fields / `P4Zone.new` 8 args after dropping `kind`, `flipped`, `volTag` |
| Declaration order | all new symbols (`nbQm`, `nsQm`, `qmNew`, `p7mQm`, `sbWin`, `ldT1…ldSh`) declared before first use |
| Dead identifiers | `f_p4Col`, `f_p4Vis`, `p3BullUlt`, `p3BearUlt`, `v5RrNL/S`, `rrN` — zero remaining references |
| Brackets / tabs / indent | balanced, no tabs, indentation 4k or the file's 4k+1 continuation convention |
| Output slots | 16 alertcondition + 8 plot + 2 bgcolor + 6 security ≈ 46 / 64 |

**Not done and not claimable: no backtest, no accuracy figure, no compile.** The TP2 / SL / ambiguous counters are mechanical counts, not statistics.

## 8. Known, accepted, not fixed

Recorded so the next pass does not re-open them.

- **`slEngL` / `slEngS` are last-writer-wins *within* the engine class.** V8-07 gave each *class* its own stop slot, but a chart-TF turtle soup and an HTF CRT firing on the same bar still share one engine slot, and the HTF stop (an HTF candle's extreme) overwrites the tight one. Fixing it means per-producer stop slots, which the RR gate cannot consume without another restructure.
- **HTF CRT / TBS now rarely pass the RR gate.** V10-16 correctly gave them a real HTF-sized stop; on a 5m chart with a Daily HTF that risk is large enough that `rrOk` almost never holds. That is arguably correct (an HTF signal carries HTF risk) but it silently retires two producers. Watch the `⚙ No-trade` row for `RR` on `sigHCrt*` bars before deciding.
- **`f_shift` lineage never expires.** `sBar` persists until the opposite external CHoCH, so `chainL` / `chainFvgL` and the dashboard `✓disp ✓FVG` stay true on a 500-bar-old shift. Every *consumer* grades it by age (`f_ageQ` → tier A needs ≤ `mssAgeA`, the score multiplies by 0.3 when stale), so no signal is produced by it — the display is what misleads.
- **`f_preNews` near midnight.** A window starting at e.g. 00:05 with `newsPreMin` 10 flags only 00:00–00:04, not 23:55–23:59, because the comparison is in same-day minutes.
- **`f_score`'s machine branch never penalises POI life** (`lf := 0` when `mc`). The machine's own `tapZone` requires `nbFresh`, so the case is largely covered.
