# SMC v8.4.0 — False-Signal Analysis

Source: `SMC_v8.4.0.txt`. Finding IDs (F#) and hypotheses (H#) are defined in `SMC_v8.4.0_FORENSIC_AUDIT.md`. Each scenario below gives the failing condition, the code evidence, and a **testable** corrective measure. Measures are kept to the minimum that can be evaluated on its own; nothing here proposes stacking every available filter.

A "false signal" in this document means a label that the engine's own model says should not have been produced, or a label whose published numbers (entry, SL, TP) do not describe the trade the model intends. Market outcome is not the criterion — that belongs to the validation plan.

---

## S1 · Entry directly into HTF resistance / support

| | |
|---|---|
| Failing condition | A long fires with an unmitigated opposing HTF level (HTF swing high, HTF bear FVG, PDH/PWH) between the entry and TP1, or just beyond it. |
| Evidence | The HTF layer exposes only `ft.htfBias`, `htfSweepUp/Dn`, `htfManip*`, `htfRej*` and one HTF FVG per side (L2174–L2186). `f_nearestOpp` (L3250) and `f_pathBlock` (L3296) scan **LTF** zones/FVGs/liquidity. PDH/PWH are in the liquidity list and qualify as targets (L3284), so a long whose TP1 is PDH is accepted — but a long whose entry is 0.5 ATR **under** PDH with TP1 beyond it is accepted too, because `f_pathBlock` checks zones only (F12) and liquidity levels never block. |
| Why the model allows it | The path check was written for zones; liquidity levels were treated as targets, not obstacles. |
| Testable correction | Extend `f_pathBlock` to count qualified opposing **liquidity levels** and **FVGs** (F12) strictly between entry and TP1, with the same ±0.10 ATR tolerance. Metric: share of signals rejected with code 4 before/after; replay check that no long has PDH/PWH/SESH or an unmitigated bear FVG inside (entry, TP1). |

## S2 · Entry before displacement confirmation

| | |
|---|---|
| Failing condition | A reversal signal prints off a reaction candle alone, with no displacement away from the POI. |
| Evidence | In `IMMEDIATE` mode `trigBull = revBull` (L2748) — a single pin/engulf/IFC/manip candle. In `CONFIRMED` mode the confirm is `close > poiRefL` **or** `ft.newBullFvg` (L2725). A close one tick above the reaction high satisfies it; no body / range / ATR test is applied to the confirm candle. `MSS` mode raises the bar to the 5-bar high but is not the default. |
| Why the model allows it | S11 defined "confirmation" as a micro-break, not as displacement. |
| Testable correction | Optional displacement test on the confirm candle: `cd.bodyRatio >= i_dispBody and cd.rng >= atrV * i_dispRng` (the same inputs structure already uses, L2235) **or** `ft.newBullFvg`. Expose as a third option of the existing trigger input ("CONFIRMED+DISP") so it can be A/B tested. Metric: signal count, win rate and average MAE of CONFIRMED vs CONFIRMED+DISP on the same replay. |

## S3 · Entry after the move has already travelled too far

| | |
|---|---|
| Failing condition | The confirm candle (or the candle-only modules M05/M15) closes far above the POI, so the published entry is at a premium relative to the zone and the SL (zone edge) is many ATR away. |
| Evidence | `f_stop` sanity caps risk at `2 × maxA` ATR = 4 ATR (L3383, F23); below that any distance is accepted. R:R then needs a target ≥ 2 × that risk, which `f_nearestOpp` may still find at ≤ 6R. The PD array (`f_conf` L3350–L3356) scores but does not gate unless `i_pdGate` is on (default off). OTE earns +1 only. |
| Why the model allows it | Entry extension was handled by R:R, which scales with the stop, not with distance from the POI. |
| Testable correction | Add a max-extension test in the state machine: on the confirm bar reject when `close − zone.top > k × ATR` (k input, suggested 1.0) unless `i_entryPx == "ZONE EDGE"` (a limit back at the POI). Metric: distribution of `(entry − zone.top) / ATR` for shown signals before/after; MAE. |

## S4 · Entry after a liquidity sweep without a valid structure shift

| | |
|---|---|
| Failing condition | M10 fires on the sweep candle itself; M45/M41 arm on BOS, which is a continuation break, not a reversal. |
| Evidence | `s10` L2796 has no structure term. `ft.sweepBosBull` (L2477) arms M45 at tier 3 for a sweep → **BOS** (same-direction break); the reversal form (sweep → CHoCH, tier 4) is the ±2 encoding (L2479–L2491). M41 arms on `st.bullBOS` after a low sweep (L2496). A low sweep followed by a *bull* BOS is only a reversal if the trend was bearish; in a bull trend it is a pullback sweep + continuation, which is legitimate but not the "sweep → shift" model. |
| Why the model allows it | Documented design: M10 is the immediate form; the tiers distinguish BOS from CHoCH. |
| Testable correction | Keep M10 as is (tier already reflects it). Add an optional M10 variant "M10+MSS": after a qualified sweep, require `close > ta.highest(high, 5)[1]` within N bars (the existing `mssHi`, L2687) before bidding, at tier 3. Evaluate independently: signal count, win rate, average R for M10 vs M10+MSS. |

## S5 · Entry into an invalidated or fully mitigated zone

| | |
|---|---|
| Failing condition | The snapshot zone used for SL/score was broken, converted or re-armed between arm and confirm; or a zone tapped long ago still fills the slot. |
| Evidence | Snapshot `sx.poiZb` (L2739) is a reference to the arm bar's `ZS`, not to the live `Zone`. A close through the far edge expires the setup (L2721, since `poiLowL ≤ zone.bottom`), so a *broken* zone cannot confirm — correct. But: (a) `fiftyHit` is latched for the zone's life (L1921, H4), so a zone whose 50 % was hit on visit 1 satisfies the 50 % rule on visit 3 even if visit 3 only touched the top; (b) tapped zones never age out (L2061 applies to untapped only, H3); (c) a zone touched ≥ 2× is "sweep required" but the sweep flag cannot be satisfied on the confirm bar (F1), so these zones are silently excluded rather than traded with the extra evidence. |
| Testable correction | (a) reset `fiftyHit` on re-entry (same hook as F15); (b) expire tapped zones after `zoneMaxAge × 2` bars or after `touches ≥ 3`; (c) F1. Metric: zone age and visit index at signal time, before/after. |

## S6 · Entry during low-volatility consolidation

| | |
|---|---|
| Failing condition | Signals print inside a tight range where the 2R target is reachable only by leaving the range. |
| Evidence | `ft.inRange` (L2433) is computed but consumed only by M50/M53 and the panel. `f_conf` docks −1 for `trendStr == "RANGE"` (L3348). The min-risk floor of 20 ticks (L3411) is a spread floor, not a volatility floor. No ATR-relative test exists. **H2**: `RANGE` also triggers after 20 bars without a BOS/CHoCH (L1178), so an orderly pullback in a trend is scored as a range. |
| Testable correction | Two independent, switchable tests: (1) reject when `ft.inRange and not (name in sweep/range modules)`; (2) reject when `atrV < ta.sma(atrV, 50) × 0.6`. Metric: win rate and R of signals inside vs outside each condition on replay, before deciding which (if either) to keep. |

## S7 · Entry during a high-spread or news period

| | |
|---|---|
| Failing condition | A signal whose stop is a few spreads wide, or that prints in the first minutes of a session open. |
| Evidence | Not implemented. The only cost-aware element is the 20-tick floor (L3411). The killzone filter (L2273–L2274) keeps signals **inside** London/NY, which includes the 08:30 NY data window. |
| Why | The indicator has no spread feed; news calendars are not available in Pine. |
| Testable correction | (1) Make the min-risk floor ATR-relative as well as tick-based (`max(20 ticks, 0.25 ATR)`), exposed as an input. (2) Optional "avoid first N minutes of each session window" input, implemented with the existing `time()` sessions. Both are measurable by replay: compare realised R with a fixed spread assumption. Report the limitation that true spread cannot be modelled on the chart. |

## S8 · Entry against the selected HTF bias

| | |
|---|---|
| Failing condition | A counter-HTF signal shows as ⚠ grey (WARN, default) and is tradable; or an aligned signal shows while the real HTF structure has already flipped. |
| Evidence | WARN keeps reversal modules with −1 (L3511) and an extra −1 INCOMPLETE (L3517, F25); continuation modules are blocked (P1-E, L3504). The bias itself can be stale after a non-displaced HTF break (F5), so "aligned" can be wrong for up to ~72 LTF bars on 5m/1h. |
| Testable correction | F5 first. Then measure WARN-tier signals separately (the panel already names the category, L3831–L3835) and decide STRICT vs WARN from data, not by default. Metric: win rate and R for gate = 2 vs gate = 1 signals. |

## S9 · Insufficient reward relative to risk

| | |
|---|---|
| Failing condition | TP1 at ≥ 2R exists but is unreachable because an obstacle sits between; or the stop is too tight to survive noise so the nominal R:R is fiction. |
| Evidence | Path check ignores FVGs and liquidity (F12, S1). Stop at zone edge instead of reaction wick (F2) makes the risk **smaller** than the real invalidation, which inflates R:R and lowers the target bar: a 1.0 ATR true risk reported as 0.6 ATR turns a 1.2R trade into a "2R" trade. |
| Testable correction | F2/F3 and F12. Metric: before/after distribution of published R:R and of realised R; share of trades stopped by a wick that did not close beyond `poiLowL`. |

## S10 · Repeated signals from the same setup

| | |
|---|---|
| Failing condition | The same POI produces a second label on a later reversal candle. |
| Evidence | Gap 5 bars (L3560) and identity 50 bars (L3571–L3583) cover it, except: (a) identity has one slot for both sides (F16); (b) the identity anchor is the zone midpoint or the swept price (L3486–L3489) — in `IMMEDIATE` mode two different modules on the same zone (M36 then M42) have different identities and both print; (c) a different-but-overlapping zone (SR + OB at the same price) gives a different identity. |
| Testable correction | F16; optionally drop the module name from the identity (keep side + anchor) so one zone visit is one trade regardless of module. Metric: count of signals per (side, anchor) per 50 bars. |

## S11 · Signals that appear historically but were not actionable in real time

| | |
|---|---|
| Failing condition | A label on the historical chart that would not have been emitted, or would have differed, on the live bar. |
| Evidence | No such path was found. All persisted outputs are confirm-gated; HTF data is `[1]` + `lookahead_on`; no `varip`; no negative offsets. The remaining real-time differences are presentational: the panel's provisional signal (F20) and tick-level flicker of event labels that are not persisted. **Not actionable in a different sense:** `RETEST`/`BOTH` M10 entries and `ZONE EDGE`/`CANDLE 50%` limits are counted as signals whether or not price ever returns to the limit (L3400–L3403, L3395–L3399); the label does not say "unfilled". |
| Testable correction | For limit-style entries, add a fill test in the validation harness (price must trade through the limit within N bars) and report the fill rate; on the chart, mark the limit line dotted until a later bar's low ≤ entry (long). The bar-replay test in the validation plan covers the historical/real-time equivalence claim. |

---

## Scenario → finding matrix

| Scenario | Primary findings | Secondary |
|---|---|---|
| S1 HTF obstacle | F12 | F5 |
| S2 no displacement | design (trigger definition) | F14 |
| S3 over-extended | F23 | PD gate off by default |
| S4 sweep without shift | design (M10 tier) | F8, F11 |
| S5 invalid / mitigated zone | F1, F15, H3, H4 | — |
| S6 consolidation | H2 | — |
| S7 spread / news | not implemented | — |
| S8 counter-HTF | F5, F25 | — |
| S9 R:R | F2, F3, F12 | F7 |
| S10 duplicates | F16 | identity anchor design |
| S11 not actionable live | F20 | limit-entry fill reporting |

## Filters deliberately **not** recommended

- A volume filter (tick volume on forex is unreliable; the v8.4.0 cut removed the volume modules for that reason).
- A hard PD gate by default (`i_pdGate`); keep it measurable.
- Blocking all WARN signals (R9 history: STRICT silenced both sides on conflict).
- Any filter that reads the confirm candle's colour alone.
