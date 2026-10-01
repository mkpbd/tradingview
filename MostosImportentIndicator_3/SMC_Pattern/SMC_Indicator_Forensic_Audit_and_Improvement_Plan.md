# SMC Indicator — Forensic Audit & Accuracy Improvement Plan

**Source reviewed:** `SMC.txt` — SMC / ICT Suite v8.3.0  
**Review type:** Static code/logic review

> **Important limitation:** This report is based on source-code inspection. It does not establish profitability or a verified win rate. Those require reproducible historical tests, realistic trading costs, and out-of-sample validation.

## 1. Executive Summary

The indicator includes useful foundations: confirmed-bar alert gating, confirmed-bar FVG detection, HTF context, structure/liquidity concepts, and separate stop/target calculations.

The main priority is not adding more concepts. It is ensuring candidate selection, final confluence scoring, entry price, stop-loss, target, and displayed signal all describe the same trade setup.

### Main risks to investigate

1. Candidate selection may not choose the candidate that performs best under the final signal rules.
2. The score is a heuristic, not a calibrated probability of winning.
3. Entry-mode changes can make stop-loss geometry inconsistent unless risk is recalculated from the final entry.
4. Fallback targets can pass a numeric R:R threshold without representing a realistic market target.
5. A wick sweep alone does not prove a reversal.
6. Overlapping zones may represent one underlying event and should not automatically count as independent confluence.
7. Cooldown logic may suppress a valid new setup or allow a stale setup to remain relevant, depending on state transitions.
8. As an `indicator()`, chart labels and alerts are not a substitute for a strategy backtest.

## 2. What the Source Appears to Do

The source includes:

- Structure and event concepts such as BOS, CHoCH, CISD, and liquidity sweeps.
- Order-block-related concepts and OB 50% events.
- FVG detection with confirmed-bar gating.
- HTF data/context using prior confirmed HTF bars in the inspected pairing logic.
- Session handling, including configurable timezone behavior.
- Candidate selection and a final signal score.
- Long/short signal generation, score filtering, signal-gap/cooldown handling, and SL/TP calculations.
- Diagnostic plots/data-window values for inspecting internal states.

These are observations about the source, not proof that every module is correct in all market conditions.

## 3. Findings and Risks

### Finding 1 — Candidate selection and final scoring may diverge

**Why it matters:** The candidate chosen during module-level selection may not be the candidate that produces the best final trade after confluence, HTF gates, entry mode, risk checks, and final score are applied.

**What to inspect:**
- How each module creates a candidate.
- How candidate priority is calculated.
- Whether `f_pick` / `f_try` selection order affects ties.
- Whether the selected candidate is re-evaluated using the same criteria as the final signal.
- Whether candidate state is reset consistently on every bar.

**Recommended improvement:**
1. Define one documented candidate-ranking rule.
2. Apply it consistently to all eligible candidates.
3. Make tie-breaking explicit rather than relying on declaration order.
4. Run the complete final validation pipeline after selection.
5. Log why each rejected candidate failed.

**Acceptance test:** When two eligible candidates exist on the same bar, selection should be deterministic and match the documented ranking rule.

### Finding 2 — Score is a heuristic, not a win probability

The inspected source builds the final score from module tier and confidence, with penalties for certain incomplete or weak-gate conditions. A score threshold controls which signals are displayed.

**Risk:** A score of 10 does not automatically mean a higher win probability than a score of 7. That relationship must be measured on historical, unseen data.

**Recommended improvement:**
- Keep the score interpretable: show contributing factors and penalties.
- Avoid counting correlated evidence as independent. Overlapping OB/FVG/structure evidence may describe the same price move.
- Evaluate results by score bucket, setup type, symbol, timeframe, session, and market regime.
- Calibrate score-to-probability only if sufficient representative data exists.

**Acceptance test:** Report sample count, win rate, expectancy in R, and drawdown for each score bucket. Do not label the score as a probability unless calibrated and validated.

### Finding 3 — Recalculate risk from the final entry

The source contains a note that the stop function primarily knows the close, while certain RETEST/BOTH entry modes may move the entry to a swept level. This can create a mismatch between final entry and stop.

**Recommended improvement:**
1. Determine final entry price first.
2. Determine the setup's invalidation level.
3. Calculate SL from that invalidation level and final entry.
4. Validate stop direction: long SL below entry; short SL above entry.
5. Calculate risk using final entry and SL.
6. Calculate targets and R:R from that same risk.
7. Reject the signal if any value is invalid or the stop is on the wrong side.

**Acceptance test:** For every emitted signal, verify entry, SL, TP1, direction, and R:R on the exact signal bar. Include RETEST/BOTH modes.

### Finding 4 — Numeric R:R may not mean a realistic target

The source has a configurable minimum R:R and fallback target logic when a real target is unavailable under some settings.

**Risk:** A risk-multiple target can pass the R:R filter while sitting beyond a nearby opposing zone or before an obstacle.

**Recommended improvement:**
- Distinguish structural targets from synthetic risk-multiple targets in diagnostics.
- Prefer a valid external liquidity pool or another explicitly defined target.
- Check intervening opposing zones/obstacles.
- Calculate R:R only after final entry, SL, and TP1 are fixed.
- If no valid target exists, reject the signal or clearly label it as a fallback-target setup.

**Acceptance test:** Show target type in the signal panel/data window and apply a documented target-validity rule.

### Finding 5 — A liquidity sweep alone is insufficient

A wick through a prior high/low can be a sweep, but it does not by itself prove a reversal.

For a reversal-style setup, test a sequence such as:

1. Identify a meaningful, pre-existing liquidity level.
2. Price sweeps that level.
3. Price reclaims or closes back across the level according to a defined rule.
4. Displacement confirms rejection.
5. A relevant structure shift (such as CHoCH/MSS) confirms the directional change.
6. Price returns to a valid POI, if required by the setup.
7. Entry, invalidation, target, and R:R pass validation.

Do not require every step for every setup without testing. Continuation and reversal setups may need different rules.

**Acceptance test:** Classify sweep-only signals separately from sweep-plus-confirmation signals and compare results.

### Finding 6 — Correlated confluence may be double-counted

OB, FVG, displacement, and structure events can arise from the same underlying price movement. Counting all as independent confirmations can inflate the score.

**Recommended improvement:**
- Group evidence into context, liquidity, structure, POI, execution, and risk.
- Set a cap per category or define dependency rules.
- Deduplicate overlapping zones from the same origin event.
- Record which evidence contributed to the score.

**Acceptance test:** Compare score distributions and historical results before and after correlation controls.

### Finding 7 — HTF gate modes need separate evaluation

The inspected source supports different gate behavior, including a mode that can warn rather than strictly block counter-HTF setups.

**Recommended improvement:**
- Report aligned, warning-mode, and counter-HTF signals separately.
- Define any reversal exception explicitly.
- Do not interpret a warning-only state as fully aligned.

**Acceptance test:** Produce separate metrics for each HTF-gate category.

### Finding 8 — Premium/Discount and dealing-range anchors require validation

Premium/Discount logic depends on the selected dealing range and its high/low anchors.

**Recommended improvement:**
- Document how the dealing range is formed and when it resets.
- Confirm anchors are available at signal time.
- Test range transitions, missing swings, and unusually wide/narrow ranges.
- Do not use Premium/Discount as a standalone entry trigger.

**Acceptance test:** Visually audit a fixed set of examples and verify the range and 50% equilibrium on each signal bar.

### Finding 9 — Session and timezone handling can change results

Session windows depend on configured timezone behavior, and session boundaries can affect signal eligibility.

**Recommended improvement:**
- Document the intended timezone for each session.
- Test exchange-timezone and configured-timezone options separately.
- Verify session boundaries and daylight-saving transitions where relevant.
- Test instruments whose exchange timezone differs from the intended session timezone.

**Acceptance test:** Confirm timestamps are classified consistently under the documented configuration.

### Finding 10 — Cooldown and signal replacement need state-transition tests

Cooldown can prevent duplicate signals, but may suppress a genuinely new setup. An old setup may also remain eligible if invalidation/reset conditions are incomplete.

**Recommended improvement:**
- Define setup identity using the relevant event, POI, direction, and creation bar/time.
- Suppress repeat alerts for the same setup identity.
- Permit a new signal when a genuinely new setup is created and validated.
- Invalidate a setup when its premise/POI is broken or its target is reached, as appropriate.

**Acceptance test:** Test duplicate same-direction signals, opposite-direction replacements, invalidated setups, and new structure events during cooldown.

## 4. HTF Pairing and Confirmed Data

The inspected pairing logic maps chart timeframes to higher timeframes, with some mappings depending on the aggressive setting. The inspected HTF requests use prior-bar values with `lookahead_on`, a commonly used pattern for accessing confirmed higher-timeframe data without leaking the still-forming HTF candle into historical bars.

This does not prove the entire script is non-repainting. Audit every `request.security()` call and all other stateful logic.

**Test checklist:**
- Compare historical signals with signals observed live and after reload.
- Check all HTF requests, not just the inspected pairing function.
- Verify pivot/swing confirmation delays.
- Check for future bars or unconfirmed HTF values affecting past signals.
- Document drawings that may update or disappear as new bars arrive.

## 5. Recommended Operator Workflow

Use this as a proposed validation sequence, not a guarantee of profitable trading:

1. **Context:** Determine HTF direction/state and whether the setup is continuation or reversal.
2. **Liquidity:** Identify the relevant pre-existing liquidity pool or level.
3. **Event:** Confirm a qualified sweep, breakout, or setup-specific event.
4. **Confirmation:** Require relevant displacement and structure confirmation for that setup type.
5. **POI:** Identify a valid, not-yet-invalidated point of interest.
6. **Execution:** Choose the final entry method and calculate entry price.
7. **Invalidation:** Set SL from the setup's invalidation point and verify its side.
8. **Target:** Select a defensible structural target and check intervening obstacles.
9. **Risk:** Calculate R:R from final entry, SL, and TP1. Reject invalid geometry.
10. **Signal control:** Apply score, HTF policy, session policy, and setup-identity duplicate suppression.
11. **Confirmation:** Emit the alert under the intended bar-confirmation rules.
12. **Logging:** Record factors, target type, rejection reasons, and eventual outcome.

Continuation and reversal setups should have clearly defined, separately testable rules. Avoid forcing every SMC/ICT concept into one universal signal recipe.

## 6. Practical Hard-Gate Checklist

Before displaying a trade signal, validate:

- [ ] Setup type is identified: continuation, reversal, breakout/retest, or another defined type.
- [ ] Required context is available and confirmed.
- [ ] The liquidity/structure event existed before the signal decision.
- [ ] Required confirmation conditions for that setup type are met.
- [ ] The POI is valid and has not been invalidated.
- [ ] Final entry price is known.
- [ ] SL is on the correct side of entry and represents meaningful invalidation.
- [ ] TP1 is valid under the documented target policy.
- [ ] R:R is recalculated from final entry, SL, and TP1.
- [ ] Minimum R:R and score rules pass.
- [ ] Duplicate/setup-identity rules pass.
- [ ] Alert timing follows the confirmed/unconfirmed-bar policy.
- [ ] Signal reason codes are available for debugging.

A checklist improves consistency but cannot establish an edge without testing.

## 7. Validation Plan

### Phase A — Forensic code audit

Inspect and document:
- Candidate creation, selection, tie-breaking, and reset behavior.
- Final scoring and all penalties/bonuses.
- Entry-mode behavior and final entry price.
- Stop-loss direction, invalidation logic, and buffer calculations.
- TP1/TP2/TP3 source and fallback behavior.
- HTF requests, lookahead settings, and confirmed-bar handling.
- Session/timezone calculations.
- Cooldown, duplicate suppression, and signal replacement.
- Arrays/objects, `var` variables, and reset conditions.
- All alert conditions and the exact bar on which they can fire.

### Phase B — Instrumented diagnostics

For every candidate and emitted signal, record:
- Symbol, timeframe, timestamp, direction, and setup type.
- Candidate/module name and rank.
- HTF state and gate mode.
- Liquidity event and structure confirmation.
- POI type, bounds, age, and invalidation status.
- Entry, SL, TP1, TP2, TP3, target type, and R:R.
- Score components and penalties.
- Session classification.
- Rejection reason, if rejected.
- Outcome measured using a fixed, documented rule.

### Phase C — Historical testing

Because the source is an `indicator()`, create a separate test harness or controlled strategy version for measurement. Preserve the original indicator while testing.

Use:
- A fixed, documented entry/exit model.
- Realistic spread, commission, slippage, and execution assumptions.
- A representative sample across symbols, timeframes, sessions, and regimes.
- A rule for ambiguous bars where SL and TP are both touched.
- Report sample size rather than relying on a single headline win rate.

### Phase D — Out-of-sample and robustness checks

- Separate development data from validation data chronologically.
- Do not tune parameters on the final validation period.
- Test nearby parameter values to identify brittle settings.
- Compare trend, range, high-volatility, and low-volatility periods.
- Check whether results survive realistic trading costs.
- Recheck signal behavior after chart reload and on live bars.

## 8. Metrics to Report

Report at least:
- Number of trades/signals.
- Win rate, with outcome definition stated.
- Average win and average loss in R.
- Expectancy in R per trade.
- Profit factor.
- Maximum drawdown.
- Long and short results separately.
- Results by setup type, score bucket, timeframe, session, and HTF gate mode.
- Costs/slippage assumptions.
- In-sample versus out-of-sample results.

Hypothetical example: if 45% of trades win an average of +2R and 55% lose 1R, expectancy is:

`(0.45 × 2R) − (0.55 × 1R) = +0.35R per trade before costs.`

This is only an arithmetic example, not a result from this indicator.

## 9. Implementation Priorities

### Priority 0 — Correctness before tuning

1. Ensure candidate selection is deterministic and aligned with final scoring.
2. Recalculate SL/TP/R:R from final entry price.
3. Reject invalid stop direction and target geometry.
4. Make fallback targets explicit.
5. Audit state resets, setup invalidation, and duplicate suppression.
6. Verify all MTF data paths for repainting/lookahead issues.

### Priority 1 — Signal quality

1. Separate continuation and reversal rules.
2. Add setup-specific confirmation where evidence supports it.
3. Prevent correlated evidence from inflating confluence.
4. Report HTF-aligned and counter-HTF setups separately.
5. Make score contributions and rejection reasons visible.

### Priority 2 — Evidence-driven tuning

1. Compare entry modes independently.
2. Compare strict HTF gating with warning-mode behavior.
3. Compare target policies.
4. Measure results by score bucket and setup type.
5. Keep changes only when they improve out-of-sample results after costs without unacceptable drawdown or fragility.

Do not optimize only for win rate. A higher win rate can still have negative expectancy if losses are much larger than wins.

## 10. Suggested Test Matrix

| Dimension | Variants to compare |
|---|---|
| Entry mode | Immediate / Confirmed / Retest / Both, where supported |
| HTF policy | Strict alignment / Warning mode / Explicit reversal exception |
| Setup type | Continuation / Reversal / Breakout-retest |
| Target policy | Structural liquidity / Explicit fallback / Reject if no structural target |
| Signal threshold | Several pre-defined score thresholds |
| Session | Each configured session and outside-session behavior |
| Direction | Long / Short |
| Market regime | Trend / Range / High volatility / Low volatility |
| Validation | Development / Out-of-sample |

Change one major dimension at a time where possible. Record source version and settings for every test.

## 11. Final Conclusion

The most defensible path to better accuracy is to improve **trade-definition consistency and measurement**, not simply add more indicators or raise the score threshold.

Start with candidate selection, final entry-to-stop geometry, target validity, and setup lifecycle. Then instrument the indicator and test each setup category separately with realistic costs and out-of-sample data.

This audit does **not** claim a verified win rate, profitability, or guaranteed improvement. Any claimed improvement should be supported by repeatable results from a documented test process.

---

## 12. Verification Against the Source (v8.3.0 → v8.3.1)

Each finding was checked against `SMC.txt` line by line. Verdicts below are from code inspection only; they say whether the mechanism exists, not whether it is profitable.

| # | Finding | Verdict in v8.3.0 | Action in v8.3.1 |
|---|---|---|---|
| 1 | Candidate selection vs final scoring | **Partly real.** `f_bid` compared `sc > b.s` on the module TIER only, so equal tiers were settled by the order of the `f_bid` lines in the file (already listed as open item "M13"). The rest of the divergence claim does not hold: `f_conf`, the HTF gate and the R:R test are direction-only, so they cannot prefer one candidate over another on the same side — the one exception, M10 in RETEST/BOTH, moves the entry. | `f_pri()` + rank `tier × 10 + priority`; ties now resolve by a documented module-quality tier, independent of declaration order. |
| 2 | Score is a heuristic, not a probability | **Real, by construction.** Score = `tier × 2 + f_conf`, thresholds are inputs. Nothing in the script claims or measures probability. | No code change (correct as designed). Contributions are now more visible via the panel/data window; calibration still needs the strategy port. |
| 3 | Risk must be recalculated from the final entry | **Real.** `f_stop` only knew `close`; the RETEST entry was patched up afterwards by a wrong-side re-check, and the max-SL-distance cap was still measured from `close`. | `f_stop(..., ep)` takes the final entry. Order is now entry → invalidation → risk → targets → R:R, with the fallback path recomputing all four. |
| 4 | Numeric R:R may not mean a real target | **Real.** With "Require a REAL target" off, a synthetic `risk × minRR` target was displayed identically to a structural one. `f_nearestOpp` does enforce target quality (scored KL, confirmed non-weak zones, unmitigated FVGs, qualified liquidity) and a max-R:R ceiling. | New `Sig.tgt` = `REAL` / `SYNTH` / `FIXED-R`, shown in the label tooltip, the panel and the data window; note carries a ⚠ when not structural. Intervening-obstacle checking is **not** implemented (see Open below). |
| 5 | A sweep alone is insufficient | **Mostly addressed already.** M10 needs a qualified sweep (S5), a wick ratio, and a close back across the level, and R2 blocks fading a fresh strong displacement. Structure confirmation is not required, but M10 bids tier 2–3, so it cannot reach the score threshold without confluence. | No change. |
| 6 | Correlated confluence double-counted | **Real.** Four `f_conf` terms (strong departure + weak arrival, fresh zone, KL ≥ 4, zone over FVG) all describe the same zone and could add +4. | POI category capped at +2. Liquidity-target and sweep/IDM terms stay independent. Expect slightly lower scores at the same threshold. |
| 7 | HTF gate modes need separate evaluation | **Partly real.** WARN mode already docks a point, marks the signal ⚠ and has its own `alertcondition`, but the gate category was not machine-readable. | `gateUp` / `gateDn` plotted to the data window; panel row shows aligned vs counter (WARN). |
| 8 | Premium/Discount anchors | **Already fixed** in v8.2.1 R1 and v8.3 S7: the dealing range is the current leg, and price beyond it is flagged as expansion instead of saturated premium. | No change. |
| 9 | Session / timezone handling | **Already fixed** in v8.3 S3: sessions take an explicit timezone input, defaults are UTC and no longer overlap; SESH/SESL are placed when the Asia window ends. | No change. |
| 10 | Cooldown and setup identity | **Real.** Suppression was purely a bar gap plus a +2-score opposite-side override. Nothing identified a *setup*, so the same zone could re-fire as soon as the gap expired. | Setup identity = module + side + POI (or swept level). A repeat of the same identity is suppressed for N bars (new input, default 50); a different setup is unaffected. |

### Added in v8.3.2

- **TP1 path check** (Finding 4, now closed in code). `f_pathBlock` counts qualified opposing zones and unmitigated opposing FVGs strictly between the final entry and TP1 — the band scan in `f_nearestOpp` could not see them because they sit closer than `minRR`. New input `TP1 path check`: `OFF` / `WARN` (default: note the blockers, −1 score) / `STRICT` (reject).
- **Rejection reasons** (Priority 1 §5). Per-side code in the data window: 0 shown · 1 no candidate · 2 HTF/PD gate · 3 outside killzone · 4 R:R / geometry / path gate · 5 score below minimum · 6 lost the both-sides conflict · 7 inside the signal gap · 8 duplicate setup identity.

### Still open after v8.3.2

- **Score calibration** (Finding 2) and every metric in §8 — these require the strategy port, not the indicator.
- **Per-category historical reporting** (Findings 2, 5, 7). The indicator now labels the categories; measuring them is a harness job.
- **Separate continuation and reversal rule sets** (Priority 1 §1). The modules are tagged by tier and by module id, not by setup class; splitting them is a design change, not a fix.
- The build was previously close to the Pine token limit. v8.3.1/8.3.2 add `f_pri`, `f_ident`, `f_pathBlock`, the geometry guard and five diagnostic plots, so verify it still compiles before trading it.
