# SMC v8.4.1 — Forensic Audit & Improvement Plan

**Document type:** Indicator audit plan  
**Subject:** SMC / ICT Suite v8.4.1  
**Basis:** `SMC_v8.4.1_ANALYSIS_BN.md` analysis document  
**Date:** 2026-10-15

> **Important limitation:** This report is based on the supplied analysis/documentation, not a direct inspection of the original 3,862-line Pine Script source. Findings described as bugs are reported by the analysis document and have not been independently verified against source code. Proposed improvements are recommendations, not proof of profitability.

---

## 1. Executive Summary

SMC v8.4.1 is described as a layered Pine Script v6 overlay indicator containing candle patterns, market structure, FVG, liquidity levels, zones, higher-timeframe context, entry triggers, setup modules, scoring, trade levels, alerts, and diagnostics.

The analysis document identifies these priority issues:

1. **F18 — FVG reaction path may be effectively dead in TOUCH mode.**
2. **F19 — Arrival-strength state may be lost in CONFIRMED entry mode.**
3. **Runtime timeout risk** from repeated historical scans and loops.
4. **M69 / tier-1 scoring issue:** a default-enabled module may rarely meet the default score threshold.
5. **`i_idmTime` input appears to have no effective impact.**
6. **Grade B is effectively hidden by the default minimum score threshold.**

These items should be investigated before adding new features. Fixing existing logic and proving that the current features work is more valuable than simply increasing the number of signals.

---

## 2. Scope and Evidence Classification

Use the following labels throughout the implementation:

- **Document-reported issue:** Explicitly listed in the supplied analysis document.
- **Suspected issue / hypothesis:** A plausible risk that requires source-code verification.
- **Recommendation:** A proposed design or testing improvement.
- **Verified fix:** Only use this label after source changes, compilation, and regression tests confirm the result.

The current report is a source-informed audit plan, not a source-code patch. Exact code changes require the original Pine Script file.

---

## 3. Indicator Architecture Described in the Analysis

The documented pipeline is:

1. Candle features
2. FVG detection
3. Market structure
4. Move-strength calculation
5. Session and Asia levels
6. Liquidity detection
7. Zone creation and state
8. Higher-timeframe analysis
9. Shared setup gates
10. Setup modules
11. Candidate selection
12. Entry / SL / TP / RR calculation
13. Duplicate and signal-gap filters
14. Labels, trade lines, panel, alerts, and data-window diagnostics

Documented feature families include:

- Candle patterns: pin bar, doji, engulfing, inside bar, harami, IFC, manipulation candle.
- Structure: BOS, CHoCH, internal BOS, weak BOS, sweep, pullback, CISD, market regime.
- FVG and move strength.
- Liquidity: BSL, SSL, EQH, EQL, PDH/PDL, PWH/PWL, Asia-session high/low.
- Zones: SR, KL, OB, BRK, FLIP, RCB, QM, RJB, PROP.
- HTF bias, sweep, rejection, FVG, and OHLC.
- Premium/discount, OTE, killzones, NY midnight open.
- Setup modules, score/gates, trade geometry, alerts, and diagnostic panel.

The analysis describes 36 setup toggles, approximately 140 inputs, 3 `request.security` calls, 11 `alertcondition` declarations, and two dynamic `alert()` calls. These are documentation-derived counts and should be rechecked against source if the script changes.

---

## 4. Priority Findings

### P0 — F18: FVG Reaction Detection

**Document-reported behavior**

The analysis says that in `TOUCH` mitigation mode, `f_fvg` may mark an FVG as mitigated before later logic checks `not g.mitigated`. This could prevent FVG reaction paths from working, including paths used by M41, M46, M68, POI FVG taps, and zone-over-FVG confluence.

**Why it matters**

If the reaction check and mitigation-state update happen in the wrong order, the indicator may fail to recognize the very touch that should count as a reaction. Signals may be missing or confluence scoring may be incomplete.

**Recommended correction approach**

1. Separate “price touched the FVG” detection from “mark FVG mitigated” state mutation.
2. Capture a per-bar FVG-touch event before changing mitigation state.
3. Define whether the event is valid on the first touch only or can repeat.
4. Ensure that one FVG cannot generate duplicate reaction events on subsequent bars.
5. Confirm behavior for TOUCH, 50%, and FULL mitigation modes.

**Regression tests**

- Fresh bullish FVG touched for the first time.
- Fresh bearish FVG touched for the first time.
- FVG touched but not mitigated under 50% mode.
- FVG fully traversed under FULL mode.
- Multiple FVGs overlapping one candle.
- Reload chart and compare historical signals.

**Acceptance criteria**

- A valid first-touch event is recognized according to the selected mitigation mode.
- Mitigation state is updated consistently.
- Related modules receive the intended event.
- No duplicate event is emitted unless explicitly designed.

### P0 — F19: Arrival State in CONFIRMED Entry Mode

**Document-reported behavior**

The analysis says `zoneTouch` is evaluated before the POI snapshot is restored. When the confirmation candle is already outside the zone, `arrivalWeak` may be false. This could affect M33, M36, M42, and the M19 filter.

**Why it matters**

A setup can begin with a valid zone reaction but lose its original context while waiting for confirmation. That can cause valid setups to be missed or filters to behave inconsistently.

**Recommended correction approach**

1. At the initial POI tap, snapshot zone identity, zone type, arrival strength, freshness, sweep requirement, and relevant reaction values.
2. Preserve the snapshot for the full confirmation window.
3. On confirmation, evaluate the stored setup context rather than relying only on current-bar zone contact.
4. Reset the snapshot on invalidation, timeout, or completed signal.
5. Add state-transition diagnostics.

**Regression tests**

- Tap and confirmation occur within the zone.
- Tap occurs in the zone; confirmation occurs outside it.
- Confirmation window expires.
- Price invalidates the POI before confirmation.
- A second POI tap occurs while another POI is armed.
- Long and short cases behave symmetrically.

**Acceptance criteria**

- Arrival state remains tied to the original POI throughout the confirmation window.
- Invalidated or expired setups cannot generate a signal.
- The M19 filter receives the intended arrival state.

### P1 — Runtime and Calculation Timeout

**Document-reported risk**

The analysis highlights scans up to roughly 490 bars, loops such as `f_legOrigin`, move-strength scans, and repeated array processing. It also says a previous build experienced a calculation timeout and that the documented file does not contain the described PERF-1 optimization.

**Recommended correction approach**

- Profile the expensive calculations first.
- Replace repeated historical extrema scans with cached or running extrema where semantics remain equivalent.
- Run expensive work only when the relevant event occurs.
- Bound array scans and remove stale objects safely.
- Avoid optimization that changes historical signal semantics without regression tests.

**Tests**

- Compile on representative chart timeframes.
- Load symbols with long histories.
- Test high-volatility and dense-signal periods.
- Test with maximum allowed zone/FVG/liquidity objects.
- Compare signals before and after optimization.

**Acceptance criteria**

- No runtime timeout on the agreed test matrix.
- Signal timestamps and levels remain unchanged except for explicitly approved bug fixes.

### P1 — Scoring, Module Rank, and Grade Thresholds

**Document-reported behavior**

- M69 is default ON but has rank 10, described as tier 1.
- With minimum score 8, tier-1 setups require substantial confluence.
- The default minimum score is 8 and grade A begins at 8, so grade B is effectively not shown.
- The analysis says the `i_idmTime` input has no effective influence because its associated flag is no longer read by an active module.

**Recommended correction approach**

1. Do not increase module rank simply to force more signals.
2. Measure per-module candidate counts, rejection reasons, final signal counts, and outcomes.
3. Decide whether M69 should remain enabled by default, have its rank adjusted, or be disabled by default.
4. Align minimum score and grade thresholds with the intended display behavior.
5. Either reconnect `i_idmTime` to an active rule or remove/rename the input so users are not misled.
6. Check whether correlated evidence is counted multiple times.

**Acceptance criteria**

- Every visible input has a documented, testable effect.
- Grade thresholds behave as described in the UI.
- Module-level behavior is measurable.
- Rank changes are supported by out-of-sample evidence, not intuition alone.

---

## 5. Additional Design Risks to Verify in Source

These are review hypotheses and recommendations, not confirmed defects.

### 5.1 Liquidity sweep is not sufficient proof of reversal

A sweep may be followed by continuation rather than reversal.

**Recommendation:** For reversal-style setups, evaluate a sequence such as:

`Liquidity pool → sweep → reclaim → displacement → MSS/CHoCH → POI retest`

Make each stage explicit and configurable. Do not treat every sweep as a reversal signal.

### 5.2 Active-zone selection may discard a better candidate

The documented system maintains one active zone per side using priority ordering. Verify whether a high-priority zone can displace a nearer, fresher, or more structurally relevant zone.

**Recommendation:** Rank eligible zones using a transparent set of factors:
- Freshness and mitigation state
- Departure/displacement quality
- Sweep or inducement evidence
- HTF alignment
- Entry-to-target path
- Invalidation distance and zone expiry

Keep the selected zone and rejected alternatives available for diagnostics.

### 5.3 HTF bias should not be treated as entry timing

Higher-timeframe direction is context, not a complete entry trigger.

**Recommendation:** Separate:
- HTF directional context
- Setup-timeframe liquidity and structure
- Entry-timeframe confirmation and invalidation

Test each timeframe pairing independently.

### 5.4 Chart entry price is not guaranteed execution

A plotted entry at candle close, candle midpoint, or zone edge is not proof that an order would fill at that price.

**Recommendation:** In external backtesting, account for spread, slippage, commissions, order-fill assumptions, and cases where SL and TP are both touched within one candle. Use conservative assumptions where intrabar sequence is unknown.

### 5.5 Repainting and historical stability

The analysis reports confirmed-bar gates and HTF use of `[1]` with `lookahead_on`. These are useful patterns, but do not by themselves prove that the entire indicator is repaint-free.

**Required checks**
- Compare signal state before and after bar close.
- Reload the chart and compare historical labels.
- Audit all `request.security` expressions.
- Check pivot confirmation delays and future-data dependencies.
- Confirm that signal entry, SL, TP, and identity do not silently change later.
- Ensure alerts correspond to the same confirmed event as chart labels.

---

## 6. Institutional-Style Price-Action Evidence

The indicator can detect patterns consistent with liquidity-taking and institutional-style price action. OHLC candles alone cannot prove that a specific institution or operator placed orders at a given level.

Use a descriptive name such as **Institutional-Style Price Action Evidence**, not a claim of confirmed operator identification.

Suggested evidence sequence:

1. Identify a relevant liquidity pool.
2. Detect a sweep and reclaim.
3. Require confirmed displacement.
4. Confirm a meaningful structure shift.
5. Identify an eligible POI.
6. Wait for a valid retest/entry trigger.
7. Define invalidation and a qualified target.
8. Record the evidence and rejection reason.

For every candidate, log timestamp, side, source level, sweep status, structure event, zone identity, confirmation state, entry, SL, TP, score contributions, and rejection code.

---

## 7. Scoring-System Improvements

The documented formula is:

`Final score = tier × 2 + confluence − path WARN − HTF WARN − INCOMPLETE`

A potential risk is double-counting correlated evidence. For example, displacement, strong departure, FVG presence, BOS, and move-strength features may partly describe the same underlying event.

**Recommendations**

- Group factors into structure, liquidity, POI quality, HTF context, execution quality, and risk penalties.
- Prevent the same event from generating several independent bonuses without justification.
- Show each factor's contribution in diagnostics.
- Keep raw confluence, penalties, and final score separate.
- Validate score thresholds against outcome data.
- Do not assume that a higher score necessarily means a higher win probability until calibrated against sufficient historical samples.

---

## 8. Risk and Target Validation

The analysis describes structural stop placement, a minimum risk threshold, qualified targets, optional synthetic 2R targets, fixed-R mode, a strict target-path check, and RR geometry validation.

Audit the following:

- SL must be on the correct side of entry.
- TP must be on the correct side of entry.
- The selected target must satisfy the configured RR bounds.
- Opposing zones between entry and TP must be handled consistently.
- Synthetic targets must be clearly identified as synthetic.
- The recorded entry must match the chosen entry mode.
- Minimum risk rules must not silently distort structural stops.
- Long and short behavior must be symmetric.
- Historical outcome calculations must include realistic costs.

Do not interpret a displayed R multiple as realized performance.

---

## 9. Performance and Regression Test Matrix

Run the same test matrix before and after changes.

| Test category | Required scenarios |
|---|---|
| FVG | First touch, partial mitigation, full mitigation, overlapping FVGs |
| POI state | Confirmation inside/outside zone, expiry, invalidation, repeated tap |
| Structure | Strong BOS, weak break, failed follow-through, CHoCH, range |
| Liquidity | Sweep/reclaim, failed reclaim, continuation/run, session rollover |
| HTF | Confirmed HTF candle, bias change, neutral bias, mismatch |
| Zone selection | Multiple overlapping zones, stale zone, invalidated zone |
| Risk geometry | Valid/invalid SL, target path blocked, RR below threshold |
| Duplicates | Same module/side/zone, opposite-side conflict, signal-gap rules |
| Alerts | Alert and label match, one confirmed event, reload stability |
| Runtime | Long history, dense objects, high volatility, multiple timeframes |

---

## 10. Validation Metrics

Compare the existing indicator with the corrected version using the same data and assumptions. Then test on a separate out-of-sample period.

Track:

- Net expectancy in R per trade
- Profit factor
- Maximum drawdown
- Win rate
- Average win and average loss
- Signal count by module
- Candidate-to-signal conversion rate
- Rejection reason counts
- Duplicate signal rate
- Performance by symbol, timeframe, session, and market regime
- Sensitivity to spread and slippage

A minimum sample size should be chosen before evaluating results. Avoid selecting parameters solely because they perform best on the same historical period used to tune them.

---

## 11. Implementation Roadmap

### Phase 1 — Correctness first
- Verify F18 and F19 against the original source.
- Repair event/state ordering if confirmed.
- Audit `i_idmTime` and other dead or misleading inputs.
- Confirm score/grade display behavior.
- Compile and run focused regression tests.

### Phase 2 — Signal logic
- Verify sweep → reclaim → displacement → structure shift sequences.
- Audit active-zone selection and state preservation.
- Check correlated scoring factors.
- Add explicit candidate and rejection diagnostics.

### Phase 3 — Execution realism
- Validate entry, SL, TP, RR, and path logic.
- Test spread, slippage, and ambiguous intrabar fills externally.
- Clearly distinguish structural, synthetic, and fixed-R targets.

### Phase 4 — Runtime stability
- Profile expensive scans and loops.
- Apply semantics-preserving caching and event-driven calculations.
- Test long histories and object limits.

### Phase 5 — Evidence-based validation
- Run a symbol/timeframe test matrix.
- Compare before/after behavior.
- Use out-of-sample and walk-forward tests.
- Keep a changelog of every behavior-changing fix.

---

## 12. Definition of Done

A change is complete only when:

- [ ] The original issue is reproducible or clearly classified as a hypothesis.
- [ ] Root cause is identified in the source.
- [ ] The smallest appropriate fix is implemented.
- [ ] The script compiles in Pine Script v6.
- [ ] Relevant regression tests pass.
- [ ] Historical signals remain stable except for intended corrections.
- [ ] Alerts and chart labels agree.
- [ ] Performance is checked on representative symbols and timeframes.
- [ ] The change is documented with before/after evidence.
- [ ] No claim of profitability is made without suitable testing.

---

## 13. Required Source File for Code-Level Work

The supplied Markdown analysis is useful for prioritization, but it is not a substitute for the original Pine Script.

To proceed with code-level forensic auditing, provide the actual `SMC_v8.4.1.txt` or `.pine` source. Then inspect each reported issue at its exact code location, verify the root cause, propose a minimal patch, and define regression tests before changing unrelated features.

**Final principle:** Fix correctness first, then improve signal logic, then measure execution realism and out-of-sample performance. More features or more signals do not automatically produce better trading decisions.
