# SMC v8.4.0 / v8.4.1 — Validation Test Plan

Companion to `SMC_v8.4.0_FORENSIC_AUDIT.md` (F#), `SMC_IMPROVEMENT_ROADMAP.md` (stages, MC#). Test IDs here are referenced from the roadmap's acceptance column.

---

## 0. Limitations stated up front

- **No executable backtest exists in this folder.** The production file is an `indicator()`; it emits no trade list. The header (L85–L87) mentions a companion strategy port (`SMC_Suite_v8.2.1_strategy.pine`) that is **not present** in this folder and is two versions behind. Until a v8.4.x port exists, every statistic below is collected by hand from bar replay or from an exported signal list, and the sample sizes will be small.
- **No performance numbers are claimed in any audit document.** Win rate, expectancy, profit factor and drawdown are *to be measured*; nothing here predicts them.
- TradingView bar replay is the only real-time simulation available. It replays confirmed bars; it does not reproduce intrabar tick order, so intrabar flicker (F20) cannot be measured there, only on a live chart.
- Spread, commission and slippage must be assumed; the chart has no spread feed. Assumptions are fixed in §4 and must be stated with every result.

---

## 1. Reference charts and periods

| Set | Instrument / TF | HTF (Conservative) | Period | Regime it covers |
|---|---|---|---|---|
| A | XAUUSD (OANDA) 5m | 60 | one trending month + one ranging month, chosen **before** looking at signals | trend, range, high-vol |
| B | EURUSD 5m | 60 | same two months | low-vol forex, killzone behaviour |
| C | NAS100 (OANDA) 5m | 60 | one month | index, cash-session gaps |
| D | BTCUSDT.P 15m | 240 | one month | 24h market, no killzone auto-on |
| E | EURUSD 1h | D | six months | HTF behaviour, PDH/PDL weekly rollovers |

In-sample = the first period of each set; out-of-sample = the second period, not opened until the in-sample tests are complete. Walk-forward: when a strategy port exists, roll the two-month window monthly across one year per instrument.

Settings: shipped defaults unless the test says otherwise. Record the full input set with every run.

---

## 2. Repainting and confirmation tests (run on v8.4.0 first, then every stage)

| ID | Test | Procedure | Pass criterion |
|---|---|---|---|
| T-R1 | Historical = replay | Load set A, export the signal list (bar time, side, module, entry, SL, TP1, score) from the data window + labels. Reset bar replay to the start of the same range and step bar by bar; record every signal as it appears. | The two lists are identical: same bars, same values. |
| T-R2 | No earlier-bar signals | For each signal, verify the label bar equals the confirm bar (the bar whose close satisfied `trigBull`/`s##`), never the arm bar. | 0 exceptions. |
| T-R3 | HTF stability | Mark the HTF bias (background tint) at each HTF boundary during replay; compare to the historical tint. | Identical; bias changes only on the first LTF bar after an HTF close. |
| T-R4 | FVG / zone stability | During replay, note any FVG box or zone box that exists on bar N and is gone or resized on bar N+1 **without** being mitigated/broken by price. | 0 exceptions. |
| T-R5 | Alert ↔ label | Create the four signal `alertcondition`s and the dynamic alert on a live chart for one session. | Every alert has a matching label on the same bar with the same entry/SL/TP; no alert without a label (except by `d_sig`, until F21 is fixed). |
| T-R6 | Intrabar panel (live only) | Watch the panel "Signal" row on a live 1m chart for 30 minutes. | Document how often a provisional signal appears and vanishes (F20 evidence). Not a pass/fail until stage 9. |

---

## 3. Regression tests per finding (synthetic or located cases)

Synthetic cases are built with bar replay on a chart where the pattern is known to occur, or by locating a historical instance and recording its bar time. Each test names the observable, not the internal variable, except where a temporary `plot()` is added for the test and removed afterwards.

| ID | Finding | Setup | Observable before fix | Observable after fix |
|---|---|---|---|---|
| T-01 | F2 | CONFIRMED mode; OB tap where the reaction candle's low < zone bottom − 0.15 ATR; confirm next bar | SL line above the reaction low | SL line ≤ reaction low − 0.15 ATR |
| T-02 | F3 | FVG mode `50%`; FVG-only arm (no zone at price); confirm 3 bars later with a higher low | SL = confirm-bar low − buffer | SL ≤ reaction low − buffer |
| T-03 | F11 | Two-bar sweep of a PDL (close below, then close back above), second candle with small lower wick | no M10, or M10 with SL under the second candle | M10 with wick test passed by the first candle; SL under the lower of the two lows |
| T-04 | F1 | Zone with `⚠SWEEP REQ`; sweep candle = reversal candle (arms); confirm next bar | no signal; data window reject code 1x | signal; no −2 in the score tooltip |
| T-05 | F19 | OB tap, pin bar high above zone top, next candle gaps and closes above the pin high with low above zone top; arrival measured WEAK | no M42 / M36 | M42 or M36 label |
| T-06 | F19 inverse | Same shape but arrival STRONG (impulsive leg into the zone) | signal on the confirm bar (M19 bypassed) | no signal; reject code 1 (M19 blocked) |
| T-07 | F18 | TOUCH mode; temporary `plot(ft.atBullFvg ? 1 : 0)`; any bar whose low enters an unmitigated bull FVG | plot 0 on every bar | plot 1 on the entering bar |
| T-08 | F4 | Small-body close 1 tick above `curHigh` (weak), 3 quiet bars, then a displaced close through the same level | no BOS▲, no OB | BOS▲ on the displacement candle; OB at the leg origin |
| T-09 | F6 | One candle whose low takes the inducement pivot low and enters the OB | zone text without `IDM✓` | `IDM✓` |
| T-10 | F7 | `ZONE EDGE` mode; confirm close inside the upper half of the zone | entry line above close (long) | entry line == close |
| T-11 | F17 | Bull trend, LH pivot, displaced close below `curLow` (not below `majorLow`) | CHoCH▼ line at `majorLow`; `stFail` = 1 next bar (temporary plot) | line at `curLow`; `stFail` = 0 |
| T-12 | F5 | 1h candle closes above the last HTF swing high with body < 50 %; next 1h candle closes above it with body ≥ 50 % | tint unchanged after both | tint BULL after the second |
| T-13 | F9 | Deep pin bar closing at 40 % of the zone, CONFIRMED mode; confirm next bar | no signal | signal |
| T-14 | F10 | London window; tap at 04:50 NY, confirm at 05:05 | reject code 3 | signal |
| T-15 | F8 | Two highs 0.05 ATR apart form EQH; a wick exceeds the average but not the higher high | `SWEEP✕ POOL·EQH` label | no sweep until the higher high is exceeded |
| T-16 | F12 | Long with an unmitigated bear FVG between entry and TP1, STRICT path | signal shown | reject code 4 |
| T-17 | F13 | Sweep → displaced CHoCH▲ | only RCB (if fib gate passes) | OB▲ at the leg origin as well |
| T-18 | F14 | MSS mode, default window | confirm window 8 | confirm window 12 |
| T-19 | F15 | Price sits inside a fresh OB for 5 bars without leaving | `⚠SWEEP REQ` appears during the visit | no second touch until re-entry |
| T-20 | F16 | L signal, then S signal, then the same L setup within 50 bars | second L shown | second L suppressed (code 8) |
| T-21 | F20 | Live chart, panel row | provisional signal visible intrabar | row shows last confirmed signal |
| T-22 | F21 | `d_sig` off, alert armed | alert fires | no alert (or documented) |
| T-23 | F24 | ZONE EDGE with no target at the limit price | tooltip "LIMIT @ … R:R fallback → IMMEDIATE" | tooltip "R:R fallback → IMMEDIATE" only; risk ≥ floor |
| T-24 | panel | `d_evidence` on | — | every row populated; "PROVISIONAL" until close |
| T-25 | engine | `i_reqStages` = "Full sequence" | — | signal count ≤ "Module rules only"; every shown signal has all four stage rows non-empty |
| T-26…T-30 | MC-1…MC-6 | per the roadmap §5 | — | A/B metrics per §4 below |

Unaffected-module guard: for every stage, the signal list diff (roadmap §6 step 4) must show changes **only** on bars where the stage's finding applies. Any other change fails the stage.

---

## 4. Quantitative protocol (manual until a strategy port exists)

### 4.1 Execution assumptions (state with every result)

| Item | Assumption |
|---|---|
| Entry | confirm-bar close for `CLOSE`; limit entries count only if a later bar trades through the limit within 10 bars, else "unfilled" (reported separately) |
| Spread | XAUUSD 0.20, EURUSD 0.8 pip, NAS100 1.0, BTCUSDT.P 0.5; applied once per round trip |
| Commission | 0 (spread-only broker assumed) |
| Slippage | 0 on limits, 1 spread on market entries |
| Stop / target | the published SL and TP1; a bar whose low ≤ SL **and** high ≥ TP1 counts as a loss (conservative) |
| Partial | TP1 only (TP2/TP3 are informational) |

### 4.2 Metrics per run (per instrument, per regime, per module tier, per gate category)

| Metric | Definition |
|---|---|
| N signals | labels committed |
| N tradable | signals whose limit filled (= N for CLOSE mode) |
| Win rate | TP1 hits ÷ N tradable |
| Avg win / avg loss | in R (published risk) |
| Expectancy | win rate × avg win − (1 − win rate) × avg loss, in R |
| Profit factor | Σ wins ÷ Σ losses |
| Max drawdown | worst peak-to-trough of the cumulative R curve |
| Duplicates | signals suppressed by code 7/8 **plus** signals on the same (side, zone anchor) within 50 bars that were not suppressed |
| Stability | T-R1 exceptions |
| Missed valid setups | hand-counted from the reference charts: textbook sweep → displacement → POI → reaction sequences that produced no signal, with the reject code |
| By session / regime | the above split by `ft.sessName` and by `st.trend` at signal time |
| Published vs real risk | share of trades where the bar after the signal had a low below the published SL but above `poiLowL` (F2 evidence) |

Sample size: report N everywhere. Below N = 30 per cell, report the cell as "insufficient" and draw no conclusion.

### 4.3 Comparisons that decide the roadmap's open questions

| Question | Compare | Decides |
|---|---|---|
| Did stage 1 change outcomes? | v8.4.0 vs stage 1 on set A+B in-sample | published vs real risk; win rate at equal N |
| CONFIRMED vs IMMEDIATE | same file, trigger input toggled | which default to keep |
| WARN vs STRICT gate | gate category split | S8 |
| MC-1 displacement confirm | trigger option A/B | S2 |
| MC-3 M10+MSS | module split | S4 |
| Killzone filter | `i_ssnFx` on/off on set B | S7 |

### 4.4 Out-of-sample and walk-forward

After every in-sample decision, run the second period of each set once, untouched. If a decision reverses out of sample, revert it and record both results. Walk-forward is deferred until a strategy port exists; the port must replicate the indicator's `f_sig` numbers exactly (T-S1: port entries/SL/TP equal the indicator's on every signal bar) before its statistics are used.

---

## 5. Compile and performance checks (every stage)

| ID | Check | Pass |
|---|---|---|
| T-C1 | Pine compile | no errors; warnings listed in the changelog |
| T-C2 | Compiled-token count | recorded; ≤ 100,256 |
| T-C3 | Drawing counts at `barstate.islast` on set A | labels ≤ 500, lines ≤ 500, boxes ≤ 500 (temporary plots of `array.size`) |
| T-C4 | Historical load time on set E (six months 1h) | not materially slower than v8.4.0 (subjective; note seconds) |
| T-C5 | `request.security` count | 3 |

---

## 6. Reporting template (copy into `SMC_CHANGELOG.md` per stage)

```
Stage N · vX.Y.Z · date
Findings: F#, F#
Compile: OK · tokens NNNNN (was NNNNN)
T-tests: T-xx PASS/FAIL … · T-R1 PASS · unaffected-module guard PASS/FAIL
Signal diff vs previous: +a −b moved c, all on finding bars: yes/no
Open issues:
```
