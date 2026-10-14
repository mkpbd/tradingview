# SMC Suite — Changelog (audit cycle 2026-10-14)

## v8.4.1 — IN PROGRESS (`SMC_v8.4.1.txt`, built from an unmodified `SMC_v8.4.0.txt`)

### Stage 1 · v8.4.1-s1 · 2026-10-14
Findings addressed: F2, F3, F11
Changed functions / lines (v8.4.1 numbering): header L3–L15 and title L190; main scope L2762–L2767 (`slRefLo` / `slRefHi`); `s10` / `s10b` L2814–L2815 (wick test reads `math.max(this bar, ctx.dnR2 / upR2)`); `f_stop` L3384–L3400 (+`refLo`, `refHi`; zone branch `math.min(zz.bottom, refLo)`, sweep and fallback branches use the reference); `f_sig` L3408 (+2 params), its two `f_stop` calls L3428, L3457; call sites L3528, L3547.
Reason: F2 — the published SL ignored the reaction wick while the state machine's invalidation (`sx.poiLowL`) sat below it; F3 — FVG-only taps used the confirm bar's low; F11 — a two-bar sweep was wick-tested and stopped on the wrong candle.
Implementation note: the roadmap sketch named `ctx.dnR1` as the previous bar's wick ratio; at the point `s10` is evaluated `ctx.dnR1` already holds **this** bar (updated at L2393–L2396), so the previous bar is `ctx.dnR2`. The reference uses `sx.poiLowL` only on the bar the POI confirms (`poiConfL`), never the stale value from an older arm.
Behaviour preserved: when the reaction low is inside the zone, `math.min(zz.bottom, refLo)` returns the zone bottom — identical to v8.4.0. IMMEDIATE-mode single-bar setups whose previous two lows are higher are unchanged. The `f_stop` sanity fallback (risk > 4 ATR) still uses the current bar's extreme.
Compile: **NOT RUN** — no Pine compiler available in this environment. User to compile and report the token count (previous build: unknown after the v8.4.0 cut).
Tests: T-01, T-02, T-03, T-R1, unaffected-module guard — **pending** (require TradingView replay).
Signal diff vs v8.4.0: expected changes only on bars where (a) a POI confirm's reaction low is below the zone bottom − 0.15 ATR, (b) an FVG-only confirm (50 %/FULL FVG mode), (c) a two-bar sweep. Any other change fails the stage.
Unresolved: F1, F4–F10, F12–F26 (stages 2–9).

### Stage 1b · v8.4.1-s1b · 2026-10-14 · PERF-1
Trigger: stage 1 compiled on TradingView, then raised the runtime error "Calculation timed out. Remove the indicator and reapply it to the chart". Stage 1 itself adds two `math.min/max` lines, so the timeout is a per-bar cost that was already near the limit on that chart.
Change: `pdHiB` / `pdLoS` were `ta.highest(high, pdSpanB)` / `ta.lowest(low, pdSpanS)` with a series length up to 491, evaluated on every bar (the only unconditional O(500) scan in the script). Replaced with running extremes in `Sx` (`pdHiRun/pdHiFrom`, `pdLoRun/pdLoFrom`, L601–L604): full rescan only when the anchor (`ctx.majorLowIdx` / `majorHighIdx`) changes, otherwise one `math.max` / `math.min` per bar (L2339–L2363).
Behaviour: identical while a leg is shorter than 490 bars. Beyond that the old call dropped the oldest bars from its window; the running value keeps the true leg extreme (arguably more correct for the PD array). Intrabar rollback of `var` state keeps it consistent.
Compile / timeout: **to be re-tested by the user** on the same chart. Also to test: whether `SMC_v8.4.0.txt` times out on the same chart (isolates chart depth from the stage-1 change).
If still timing out, next candidates (in order): `f_zones` per-zone `f_fvgNear` for unconfirmed RJBs (L1862), the arrival `f_moveStrength` cadence (every 6 bars per side, L2342), and the two `f_nearestOpp` + `f_pathBlock` scans per candidate bar.

Each further stage is appended in this form:

```
### Stage N · v8.4.1-sN · <date>
Findings addressed: F#, F#
Changed functions / lines: ...
Reason: <one line per finding, referencing the audit>
Compile: OK/FAIL · compiled tokens NNNNN (previous NNNNN) · warnings: ...
Tests: T-xx PASS/FAIL ... · T-R1 PASS/FAIL · unaffected-module guard PASS/FAIL
Signal diff vs previous stage: +a −b moved c · all on finding bars: yes/no
Unresolved / deferred: ...
```

## Audit deliverables produced 2026-10-14 (documentation only)

| File | Content |
|---|---|
| `SMC_v8.4.0_FORENSIC_AUDIT.md` | Source inventory, repaint audit, findings F1–F26 with severity, hypotheses H1–H4 |
| `SMC_ENTRY_FOOTPRINT_ANALYSIS.md` | BUY/SELL pathways A–D, per-module footprint reports, state mapping |
| `SMC_FALSE_SIGNAL_ANALYSIS.md` | Scenarios S1–S11 with code evidence and testable corrections |
| `SMC_IMPROVEMENT_ROADMAP.md` | Stages 1–10, token estimates, dependencies, Phase 5 engine + evidence panel proposal, model-change proposals MC-1…MC-8 |
| `SMC_VALIDATION_TEST_PLAN.md` | Repaint tests T-R1…R6, regression tests T-01…T-30, quantitative protocol, compile checks |
| `SMC_CHANGELOG.md` | this file |

## Known limitations carried into v8.4.1

- Compiled-token headroom after the v8.4.0 cut is unknown; the roadmap orders stages so the user can report the count after stage 1.
- No strategy harness for v8.4.x exists; quantitative validation is manual until one is written (test plan §0).
- IFVG, spread/news filtering and a structural MSS event are not implemented in v8.4.0 and are not part of v8.4.1 (model changes, separate proposals).
