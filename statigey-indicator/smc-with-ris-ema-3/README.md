# Sniper Scalp — SMC / ICT [Strategy] V3 (V11 build)

A TradingView **Pine v6 `strategy()`** that trades Smart Money Concepts / ICT setups:
structure break (BOS / CHoCH / MSS) → retrace into a PD-array zone (FVG / OB / breaker /
IFVG / rejection block) inside the golden / OTE fib band → confirmed trigger candle, all
filtered by a 0–100 confluence score. It drives the **native order engine**, so the
Strategy Tester produces a real equity curve, profit factor, drawdown and walk-forward stats.

File: `indecatior-v-fixed.pine`

> ⚠️ **This is a research / evaluation tool, not a verified money-maker.** The author's own
> changelog states the statistical edge is **unproven**. Treat every backtest as optimistic
> until you set real costs and pass an out-of-sample test. See [Before You Trust Anything](#before-you-trust-anything).

---

## Table of Contents
1. [What it does](#what-it-does)
2. [Install](#install)
3. [Core trade logic](#core-trade-logic)
4. [Execution model (no repaint)](#execution-model-no-repaint)
5. [Quick-start presets](#quick-start-presets)
6. [Settings reference](#settings-reference)
7. [The dashboard](#the-dashboard)
8. [The stats panel](#the-stats-panel)
9. [Alerts / webhook automation](#alerts--webhook-automation)
10. [Before you trust anything](#before-you-trust-anything)
11. [Risk management](#risk-management)
12. [Troubleshooting](#troubleshooting)
13. [V11 audit fixes](#v11-audit-fixes)
14. [Limitations](#limitations)

---

## What it does

| | |
|---|---|
| **Methodology** | Hybrid SMC / ICT — mean-reversion into the higher-timeframe trend |
| **Direction** | Long and short |
| **Entry** | Market-on-close, on the confirmed signal bar |
| **Exit** | 3-stage ladder: TP1 partial → TP2 partial → trailed runner |
| **Sizing** | Risk-% of live equity, auto-computed per trade |
| **Best markets** | XAU/USD, NAS100 / ES, BTC, FX majors |
| **Best sessions** | London + New York AM killzones |
| **Best regime** | Trending, mid-volatility |
| **Timeframes** | 1M–15M entry, with 60m / 240m / D HTF bias |

---

## Install

1. Open **TradingView → Pine Editor**.
2. Paste the full contents of `indecatior-v-fixed.pine`.
3. **Add to chart.** It loads as a *Strategy* (equity/PF/DD in the Strategy Tester tab).
4. Open **Settings (⚙)** to configure. Defaults are a sane "sniper" starting point.
5. **Set costs** (mandatory before trusting any result) — see [Before You Trust Anything](#before-you-trust-anything).

Requirements: a Pine v6-capable plan. Drawing-object heavy (boxes/lines/labels capped at 200 each).

---

## Core trade logic

A long fires only when **every** hard gate passes **and** the quality score clears `qMin`:

```
1. ARM      structure break (BOS / CHoCH / MSS) in the trade direction
2. RETRACE  price pulls back into the dealing range (no entry on the break bar)
3. ZONE     price taps a PD array: FVG / OB / breaker / IFVG / rejection block
4. FIB      tap lands in the Golden (50–78.6%) OR OTE (62–79%) band
5. SEQUENCE an ENGINEERED liquidity sweep printed, THEN an MSS after it (hard gate)
6. TRIGGER  engulfing candle OR sweep-fakeout, with displacement
7. SCORE    0–100 confluence >= qMin (default 74)
8. CONTEXT  HTF agreement, ADX, ATR regime, narrative (premium/discount), session, news
```

**Score weights (sum 100):** HTF 20 · order-flow 15 · MSS 15 · FVG 10 · OB 10 ·
displacement 10 · PD-location 10 · ADX-strength 10. Score **decays** `qDecay` pts/bar after
the arm, so a fresh retrace beats a late one.

**Soft vs hard gates:** with `useSoftGates` ON (default) the *context* filters
(ext-structure / ADX / regime / narrative) become **score penalties** instead of hard blocks
— this lifts trade frequency so the sample is statistically evaluable. The **sequence gate
stays hard** (it is the core thesis: "manipulation precedes entry").

---

## Execution model (no repaint)

- Entries gate `barstate.isconfirmed` + `process_orders_on_close=true` → fill on the
  **confirmed bar's close**. No repaint.
- Every `request.security` uses `[1]` history + `lookahead_off` → no future leak.
- Pivots confirm `swingLen` bars late and are stamped at their true bar — no pivot repaint.
- Live dashboard score may flicker intrabar (cosmetic); the **signal** is fixed at bar close.

---

## Quick-start presets

### By instrument

| Instrument | Key settings |
|---|---|
| **XAU/USD (Gold)** | `useOFdelta` ON (real volume helps less on metals — keep score-only). Spread 2–4 pip. Quote=USD → rate auto-1.0. |
| **NAS100 / ES** | `useVWAPscore` ON, `useOFdelta` ON (real volume). Quote=USD. |
| **BTC / crypto** | `useOFdelta` ON (true volume), `useVWAPscore` ON. 24/7 — relax killzones. |
| **EUR/USD, GBP/USD** | Quote=USD → rate auto-1.0. Tick-volume OF is a proxy (down-weighted). |
| **USD/JPY, crosses** | **MUST set `Quote→Account rate`** (e.g. JPY≈0.0067) or entries are hard-blocked. |

### By timeframe (Scalp Preset input)

| Preset | Swing | EMAs | RSI | Notes |
|---|---|---|---|---|
| **1M** | 3 | 9/21/50 | 7 | Auto-enables low-lag fast-break |
| **3M** | 4 | 13/34/89 | 9 | Auto-enables low-lag fast-break |
| **5M** | 5 | 20/50/200 | 14 | Standard |
| Off (manual) | uses your input values | | | |

Set the **Structure timeframe** (MTF group) to your *analysis* TF (e.g. 15M) while charting
your *entry* TF (e.g. 3M).

---

## Settings reference

Grouped as they appear in the Settings panel. Only the high-impact inputs are listed —
hover any input in TradingView for its full tooltip.

### Market Structure
| Input | Default | Effect |
|---|---|---|
| Swing pivot lookback | 5 | Bars L/R for swing detection. Lower = faster but noisier. |
| Trade BOS / CHoCH | on / on | Which break types arm a direction. |
| Arm window after break | 15 | Bars the arm stays live for the retrace. |
| Require retrace | on | Blocks entry on the break bar itself. |
| Structure break needs displacement | on | Real break = impulsive candle ≥ mult × ATR. |
| MSS needs displacement body | on | Filters thin chop CHoCHs from counting as MSS. |
| Require agree with external structure | on | Major-structure bias must agree (soft under soft-gates). |
| Low-lag break | off | Early arm without pivot-confirm wait (auto-on under 1M/3M). |

### Higher-Timeframe Bias
- **HTF gate mode**: `All agree` (strict, default) / `Majority` / `HTF #2 only`.
- HTF #1/#2/#3 = 60 / 240 / D. Bias from market structure (not EMA) by default.

### Entry Zones (PD Arrays)
Require FVG, show OBs, displacement requirement, OB-must-originate-the-leg, max zone age/count.

### Fibonacci / OTE / Premium-Discount
Golden 50–78.6%, OTE 62–79%. With both ON the band is the **union** (Golden OR OTE) to
catch sharp stop-hunt retraces. Optional fib-extension TP.

### Liquidity Mapping
PDH/PDL, equal H/L pools, Asia range, prior-week draw. Relative (ATR-fraction) equal-H/L
tolerance adapts across pairs.

### Advanced ICT
Breaker / IFVG / inducement / rejection blocks / SMT divergence / news blackout windows.
Inducement can require **engineered** (pooled) liquidity.

### Trigger
- **Require engulfing trigger** (default) — closed displacement candle (sniper mode).
- **Zone-tap entry** (off) — fire on the bare tap; earlier but lower precision.

### Risk Management
| Input | Default | Effect |
|---|---|---|
| Take Profit R:R | 3.0 | Runner target. |
| Risk per trade (%) | 0.5 | Of **live** equity (compounds). |
| Quote→Account rate | 1.0 | **Set for non-USD-quote symbols** or sizing is wrong/blocked. |
| qMin (min score) | 74 | Signal floor. Raise to 80–85 for ultra-selective after an OOS edge is proven. |
| qDecay | 1.5 | Quality lost per bar after arm. |

### Trade Tracker (exits)
Break-even after partial, ATR + structure trail, TP1 at 1.5R, time-stop, max-hold bars.

### V3 · Real Partial TP
TP1 fraction, **TP2 second scale-out** at 2.5R, TP2 fraction.

### V3 · ATR Regime / News / Narrative / Sequencing / Dynamic Risk
ATR-percentile gate, manual news timestamps + auto-NFP blackout, dealing-range
premium/discount location, hard sweep→MSS→zone sequence, **daily-loss stop**,
**consecutive-loss halt**, **overall max-DD prop guard**.

### V6.2 · Audit Remediation
- `useSoftGates` (on) — context gates grade the score instead of hard-blocking.
- `useNarrContinuation` (off) — allow trend-continuation entries in the "wrong" PD half.
- `useConsvFill` (on) — stop wins an ambiguous straddle bar (honest fills).
- **`useSoftSLcap` (off, V11)** — lift the hard max-SL block; risk-% sizing keeps $ risk fixed.

### V4 · Order-Flow / Walk-Forward / Cost Honesty
LTF volume-delta confirmation (proxy on FX), IS/OOS split, and the **cost interlock**
(`ackCosts` + `costBlock`) that refuses to fire until you confirm realistic costs.

### Validation Mode
Diagnostic — floors quality to 50 and bypasses context gates to **count raw setups**.
Use it to confirm setups exist before tightening filters.

---

## The dashboard

Top-right table. Reads, top to bottom:
- **TREND** (chart) and **HTF #1/#2/#3** bias (BULL/BEAR/FLAT).
- **MTF BIAS**, **SESSION**, **KILL ZONE** status.
- **PD Zone** — Premium / Discount / Equilibrium.
- **CONFLUENCE** — live `L<score>  S<score>` out of 100.
- **POSITION** — flat / long / short.
- **Signal** — Awaiting / armed / READY.
- **READY?** — the gate that's blocking you: `SET COSTS`, `SET QT RATE`, `MIS-SIZE`, or `ARMED`.

If **READY? ≠ ARMED**, no orders can fire. Fix the named gate first.

---

## The stats panel

Bottom-left. **Per-entry** accounting (one full position = one win/loss, partials folded in):

| Row | Meaning |
|---|---|
| Win rate (per entry) | Honest — not inflated by counting each partial. |
| Profit factor | Gross profit / gross loss. ≥1.5 green. |
| Net profit (R / $) | |
| Expectancy/trade | Avg R per entry. |
| Payoff | avgWin / avgLoss. |
| Max drawdown | R and % of initial capital. |
| Max consec loss | |
| Risk of ruin (proxy) | **Analytic, not Monte Carlo** — directional only. |
| **IS / OOS win + exp** | In-sample vs out-of-sample (overfit check). |
| **WF verdict** | ROBUST / DEGRADED / OVERFIT / IS-NEG. |
| London / NY / Asia | Per-killzone expectancy — which session actually pays. |
| **Sharpe (per-trade)** | V11. Per-trade, not annualized. ≥1.0 green. |
| **Sortino (per-trade)** | V11. Downside-deviation version. |
| **Recovery factor** | V11. Net profit / max drawdown. ≥2.0 green. |

> The Sharpe/Sortino here are **per-trade**. For annualized Sharpe/Sortino use TradingView's
> native Strategy Tester "Performance Summary".

---

## Alerts / webhook automation

Two layers:
- **`alertcondition`** — static: "Sniper LONG", "Sniper SHORT", "Sniper EXIT".
- **`alert()`** — dynamic webhook text fired on entry/exit, e.g.:
  ```
  SNIPER BUY EURUSD @ 1.08542  SL 1.08401  TP 1.08965  Q 81/100  units 1.42
  ```
  Includes symbol, price, SL, TP, quality score, and risk-sized units.

To use: create an alert on the strategy, set condition to "Any alert() function call",
paste your webhook URL.

---

## Before you trust anything

A zero-cost backtest is **fiction**. Do this in order:

1. **Strategy Tester → Properties** → set realistic **Commission** + **Slippage** for your broker.
   - FX majors ≈ 0.7–1.0 pip round-turn + commission · Indices ≈ 0.5–1.0 pt · Metals ≈ 2–4 pip.
2. Tick **"I have set realistic Commission + Slippage"** (`ackCosts`). Until then, entries are
   blocked and a chart warning is drawn.
3. Set **Quote→Account rate** for any non-USD-quote symbol.
4. Run **Validation Mode** once to confirm setups exist (raw count).
5. Turn Validation Mode off. Set **OOS start** (WF group) to where your tuning window ends.
6. Run the backtest. **Read the WF verdict:**
   - `ROBUST` — OOS expectancy ≥ 60% of IS. Worth demo-forward.
   - `DEGRADED` / `OVERFIT` / `IS NEG` — do **not** trade. The edge was curve-fit.
7. Want true robustness? Export the trade list → run a **Python Monte Carlo**.

**Minimum bar for going live:** OOS expectancy holds, across ≥3 instruments, with ≥100 OOS
trades. Anything less is a guess.

---

## Risk management

Built-in, layered:
- **Per-trade**: risk-% of live equity, ATR min/max stop bounds, spread cap.
- **Daily**: loss limit in R off frozen day-start equity, with a persistent halt latch.
- **Streak**: halt after N consecutive losing entries, with cooldown hours.
- **Account**: trailing peak-equity max-DD guard (prop rule) — flattens and permanently halts.
- **Cooldown** after a tracked loss.

Defaults: 0.5% risk, 2R daily stop, 3-loss halt, 10% max-DD. Tune to your prop firm's rules.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| No trades at all | Costs unacknowledged | Tick `ackCosts` after setting costs. |
| READY? = SET QT RATE | Non-USD quote, rate still 1.0 | Set Quote→Account rate. |
| READY? = MIS-SIZE | `pointvalue`/rate unresolved | Check symbol; set rate. |
| Very few trades / empty WF | Over-filtering | Keep `useSoftGates` ON; consider `useSoftSLcap` ON; lower `qMin`; run Validation Mode. |
| Order-flow does nothing on 1M | `ofLTF` not below chart TF | V11 auto-guards it; OF score just zeroes — expected. |
| "Discount Buy Zone" during HTF sell-off | — | `useHTFimpulse` ON makes the range obey the bigger HTFs. |
| Wrong-side entry zone drawn | — | Directional fib bands already separate long/short; check armed side on dashboard. |

---

## V11 audit fixes

Latest build (`indecatior-v-fixed.pine`). **C-1/C-4/C-5 are behavior-neutral at defaults;
C-2/C-3 are opt-in/additive.**

| ID | Severity | Fix |
|---|---|---|
| **C-1** | High | `request.security_lower_tf` now uses an effective LTF that can't exceed the chart TF — no more silent error / dead order-flow feed on a 1M chart. |
| **C-2** | Medium | New `useSoftSLcap` (default OFF) — lifts the hard max-SL block. Risk-% sizing keeps $ risk fixed, so the block was lost frequency, not safety. |
| **C-3** | Medium | Stats panel adds **Sharpe / Sortino** (per-trade, honest entry-R) + **Recovery factor**. |
| **C-4** | Low | De-duplicated `riskMoney` compute. |
| **C-5** | Low | `longScore` / `shortScore` clamped ≤100 so raised weights can't break the 0–100 contract. |

> After enabling `useSoftSLcap`, **re-run the IS/OOS walk-forward** — it changes frequency.

---

## Limitations

- **Edge unproven.** Heavy parameterization (100+ inputs) → overfitting risk. The soft-gate /
  `qMin` tuning shapes frequency; that is curve-fit-prone. Prove it OOS.
- **FX order-flow is tick-volume** = a proxy, not true bid/ask delta. Real only on
  futures / indices / crypto. Down-weighted accordingly.
- **No live news calendar** in Pine. Only NFP (first Friday) is auto-scheduled; CPI/FOMC need
  manual timestamps.
- **Manual operator inputs** (quote rate, news times, OOS date) — fragile if mis-set; the
  dashboard READY? row surfaces the silent ones.
- **Sharpe/Sortino in-panel are per-trade**, not annualized.

---

### Deployment verdict

**Demo / evaluation only** until you: set real costs, fix the quote rate, and pass an
out-of-sample test (`WF verdict = ROBUST`, ≥100 OOS trades, ≥3 instruments). The engineering
is sound and honest; the *edge* is your job to prove. **Do not fund on a backtest alone.**
