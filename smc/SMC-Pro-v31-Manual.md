# SMC Master Pro v31 — User Manual

Smart Money Concepts / ICT indicator for TradingView (Pine v5). Detects market structure, order blocks, FVGs, liquidity sweeps, premium/discount zones, and fires **pullback** LONG/SHORT setups with a validated risk/reward engine, position tracking, and risk guards.

> **Important:** this is an `indicator()`, not a `strategy()`. It does **not** place broker orders and does **not** produce TradingView Strategy-Tester metrics (PF / Sharpe / max DD). All P&L/equity numbers it shows are an in-script simulation for reference only. For real backtest stats run the companion `smc_strategy.pine`.

---

## 1. Install

1. Open TradingView → **Pine Editor** (bottom panel).
2. Open `smc-32.pine`, select all, paste into the editor.
3. Click **Add to chart**.
4. If you see `too many tokens` — you edited and re-added code; remove a cosmetic block (see §12).
5. Save. Open the gear ⚙️ icon on the indicator to reach all settings.

**Requirements:** the chart needs ≥200 HTF bars of history for the EMA200 trend filter, and a few weeks of data for sessions/PDH-PDL. Works on any symbol; tuned for FX, Gold/Silver, indices, crypto.

---

## 2. The 10-second mental model

```
1. HTF trend (EMA200 ×3 timeframes)  ─┐
2. Market structure shift (MSS): BOS / CHoCH / sweep   →  ARMS a bias
3. Price RETRACES into a discount OB / FVG / OTE zone   →  TRIGGERS the entry
4. RR engine checks: SL beyond the sweep, target = real liquidity, RR ≥ Min
5. Confluence score ≥ threshold + hard gate pass        →  LONG / SHORT prints
6. Position tracked: SL / TP1 / TP2 / TP3, BE, trail, risk guards
```

The arrow does **not** print on the breakout candle. It waits for the pullback. See §6 — that is the single most common point of confusion.

---

## 3. First-run setup (do this once)

| Step | Setting (group) | Set to |
|------|------------------|--------|
| 1 | 🎯 Display Preset → **Display Mode** | `Trading (Balanced)` |
| 2 | 💼 Position Sizing → **Account equity ($)** | your real balance |
| 3 | 💼 Position Sizing → **Risk per trade (%)** | `0.5`–`1.0` |
| 4 | 💼 Position Sizing → **Account currency** | your account base (USD/EUR/…) |
| 5 | 💸 Trading Costs → **Spread (round-trip)** | your broker's typical spread |
| 6 | 🌍 Sessions → **Timezone** | `America/New_York` (ICT standard) |
| 7 | ⚖️ Margin Guard → **Account leverage** | your broker leverage (e.g. 100) |

If the chart shows `⚠ FX conv unresolved` → the symbol's quote currency can't convert to your account currency; sizing assumes 1.0. Switch **Account currency** to the symbol's quote currency or ignore if you trade R-multiples only.

---

## 4. Settings reference (by group)

### 🎯 Display Preset
- **Display Mode** — `Minimal` (clean, signals only) / `Trading` (balanced) / `Full` (everything). Minimal hides OB/FVG/liquidity/patterns.
- **Dark Theme**, **Text Size** — cosmetic.

### 🕐 Multi-Timeframe
- **HTF #1/#2/#3** — the three higher timeframes scored for trend (default 60 / 240 / D). All three bullish = STRONG BULL bias.
- **Dashboard / Position** — on-chart status table + corner.

### 📊 Market Structure
- **Primary Pivot Length** (default 3) — drives the displayed BOS/CHoCH and `internalTrend`. Lower = more reactive/noisier.
- **HTF Context Pivot Length** (default 8) — slower swings for PD/Fib anchor.
- **Entry Structure Pivot (MSS)** (default 5) — the **entry** track. Raise to 8/12 for fewer, cleaner setups; lower to 3 only on clean instruments.
- **First shift = CHoCH** — first break from a flat trend is labeled CHoCH (on) or INIT (off).
- **Wick for BOS (vs close)** — break confirmed by wick (aggressive) or close (default, stricter).

### 🟦 Order Block / 🟥 Breakers / 📐 FVG
- **Max Active OBs / FVGs** — how many live boxes kept.
- **OB Min Impulse (×ATR)**, **Min displacement (×ATR)** — strength filters; raise to keep only strong OB/FVG.
- **Strict: require BOS/CHoCH** — OB only valid if tied to a structure event.
- **Max active breakers / iFVGs (per side)** — v31 hard count cap (prevents object-ceiling crash). Leave at 6.
- **Track mitigation / Mit threshold** — Touch / 50% fill / Full fill = when a zone counts as used.

### 💎 Premium/Discount
- **Dealing-range source** — `CHoCH leg (reactive)` = OTE sits local near price (default). `HTF swings (smoother)` = wider, stable range but OTE floats further.

### 💧 Liquidity / 🔷 Patterns / 🌀 AMD / 🐢 Turtle / ⚔ Judas
- **Detect sweeps / grabs** — equal-highs/lows + stop-runs.
- **Pin Bar / Double T-B / Turtle Soup** — candlestick + liquidity patterns feeding confluence.
- **Detect AMD** — Asia range → London sweep (Power of 3).

### 🔭 HTF POI
- **Detect HTF POI** — higher-timeframe FVG/OB tap adds confluence and a "HTF POI Tap" alert.

### 🕯️ Signals  ← entry frequency lives here
- **Require Confluence / Min Confluence** (default 5) — minimum score to print a signal. **Raise = fewer/stricter, lower = more signals.**
- **Institutional Mode** (default ON) — forces confirmed-bar entries (non-repaint). Keep ON for live/prop. OFF = experimental intrabar, repaints.
- **Cooldown bars** — minimum bars between signals.
- **+1 in KZ** — confluence boost inside kill zones.

### 📈 Position
- **Track Positions / Trade Lines / Live P&L** — the on-chart trade visuals.
- **Allow Flip / Min flip advantage** — reverse an open trade if the opposite score beats it by N.
- **Backtest fill mode** — `Next bar open` (realistic, default) vs `Signal close` (optimistic).

### 💰 Risk
- **SL Method** — `Swing-based` / `Previous candle` / `ATR-based` (only used when RR engine is OFF).
- **Target R:R (TP3)**, **TP1/TP2 R-ratio**, **TP1/TP2 close %** — the take-profit ladder.
- **BE after TP1** (default ON) — move stop to breakeven after TP1.
- **Struct trail after TP2** — trail the runner on the entry-track swing.

### 🎯 RR Engine ← trade quality lives here
- **Enable RR validation engine** (ON) — measures RR from a logical SL (beyond the swept wick) to the nearest real liquidity target; rejects weak setups.
- **Min RR** (default 1.5) — setups below this are **rejected, not shown**. Raise for quality, lower for frequency.
- **Max SL distance (×ATR)** — reject if the stop would be too wide.
- **Final TP = measured liquidity target** (ON) — TP3 anchors to the real draw-on-liquidity (PDH/PDL/session H-L/HTF swing).
- **Measure RR net of spread/commission** (ON) — honest RR after costs.

### 🎚️ Dynamic Risk / 🛡️ Risk Guards / 🚨 Drawdown / ⚖️ Margin
- **Scale risk by ATR / after losses / outside KZ** — auto-trims position size in bad conditions.
- **Daily loss cap (R)** — once the day's R hits this, **new** entries blocked (open trade still runs to its SL/TP).
- **Max consecutive losses**, **Max trades per KZ / per day** — over-trading guards.
- **Max drawdown circuit breaker** — halts new entries (and flattens the open trade) past the DD threshold.
- **Block entry if margin > cap** — rejects over-leveraged entries.

### 🚦 Hard Gate (all must pass for an entry)
- **HTF align ≥2/3** — at least 2 of 3 HTFs agree.
- **PD zone match** — buy in discount / sell in premium only.
- **Recent liq event** — a sweep/grab within the lookback.
- **Healthy vol** — not in dead chop (ADX + ATR percentile filter, 🌊 Range Filter group).

### 🕒 Time Blackout
- Static NY clock windows (e.g. `0830,1000,1400`) to avoid around news. **Not** a live calendar feed.

---

## 5. The on-chart objects

| Object | Meaning |
|--------|---------|
| `BOS ▲/▼` (dashed) | Break of structure — trend continuation |
| `⚡ CHoCH ▲/▼` (thick) | Change of character — possible reversal |
| `🟢 BULL OB` / `🔴 BEAR OB` / `💎 MB` | Order block / mitigation block |
| `🔵/🟠 FVG`, `↯ iFVG` | Fair value gap / inverted FVG |
| `💧 BSL / SSL` | Buy-side / sell-side liquidity (equal highs/lows) |
| `💎 SWEEP`, `⬆/⬇ grab`, `🌀 AMD`, `🐢 TS`, `⚔ JUDAS`, `CISD` | Liquidity events / ICT patterns |
| Red/green PD boxes + EQ line | Premium (sell) / Discount (buy) / equilibrium |
| Gold `⭐ OTE` + 50/61.8/78.6% lines | Optimal Trade Entry retrace zone |
| `▲ / ▼` arrow + `score / RR / ★` | A confirmed LONG / SHORT entry |
| Gold `⏳ PENDING ▲ ENTRY …` box | The **next** armed entry plan (see §7) |
| `● ENTRY / 🛑 SL / 🎯 TP / 🛡️ BE` lines | The live tracked position |

---

## 6. How a trade actually fires (pullback mode — default)

1. **Arm:** an entry-track MSS (BOS/CHoCH) or a liquidity sweep arms a bull or bear bias for `pbArmBars` (default 20) bars.
2. **Wait:** the bias is armed but no arrow yet — price must come back.
3. **Trigger:** price **retraces** into a fresh OB / FVG / OTE zone, on the correct side of the PD mid (buy in discount), and a confirmation candle closes.
4. **Validate:** RR engine + confluence + hard gate must all pass.
5. **Print:** the `▲/▼` arrow + grade label appears; the position lines draw.

➡️ **This is why the arrow looks "late" or "missing": it is a pullback entry, not a breakout entry.** If price shifts structure and runs without retracing, no trade fires — that runner is intentionally skipped.

---

## 7. The "Next-entry zone" box (pending projection)

While a bias is **armed** and you are **flat**, a gold box draws on the last bar with a label:

```
⏳ PENDING ▲ ENTRY 1.09421  RR 2.4
 SL 1.09180  TP 1.10050  Δ-5.2
```

- **ENTRY** = the exact price the pullback will fill at (the OTE edge). Place a limit order here.
- **SL / TP** = projected stop and target. **RR** = measured risk/reward (v31 fixed: SL is now always the correct side of entry).
- **Δ** = how far price must still travel to reach the entry. Negative on a long = price is **above**, must retrace down. A large Δ means the entry is far and may not fill.

Toggle: 🎯 Pullback → **Show next-entry zone + price**.

---

## 8. "I can't get entries" — fixes

The pullback model only buys the **discount** after a bullish shift. If price shifts then runs into premium without retracing, no fill. Choose your trade-off:

| You want | Change |
|----------|--------|
| Catch the move **without waiting** for a retrace (momentum) | 🕯️ Signals path: 🎯 Pullback → **Pullback entry mode = OFF** (enters on the break) |
| Fill pullbacks **sooner / shallower** (first OB/FVG tap, higher than deep OTE) | 🎯 Pullback → **Require confirmation candle = OFF** |
| **More signals overall** | 🕯️ Signals → lower **Min Confluence** (e.g. 5 → 4) and/or 🎯 RR Engine → lower **Min RR** |
| Keep armed setups alive longer | 🎯 Pullback → raise **Setup stays armed N bars** |

Trade-off: pullback ON = better entry price, misses runners. Pullback OFF = catches runners, worse fill / later entry.

If you get **zero** trades, check (in order): Hard Gate too strict (HTF align, zone, liq, vol) → Min Confluence too high → Min RR too high → Time Blackout / KZ-only filters active → wrong session timezone.

---

## 9. Alerts

Create alert → **Condition = "SMC Master Pro v31"** → pick a signal:

- **LONG Signal / SHORT Signal** — confirmed entry (matches the chart arrow). v31: confirm-gated so the alert = what the engine trades.
- **Pre-entry ARMED alert** — fires the moment a bias arms (before the confirm candle) with projected entry/SL/RR. To use it, create an alert with **Condition = "Any alert() function call"** (toggle 🔔 Alerts → *Pre-entry ARMED alert*).
- Structure/liquidity events: BOS, CHoCH, Bull/Bear Sweep, Liq Grab, AMD, Turtle Soup, SMT, CISD, Judas, HTF POI Tap, MTF Aligned, Max Drawdown Hit, Silver Bullet.

Set **Alerts → Confluence only = ON** so the LONG/SHORT alert only fires on a full validated setup.

---

## 10. Dashboard (top-right table)

| Row | Shows |
|-----|-------|
| Current / HTF #1-3 trend | per-timeframe bull/bear/neutral |
| MTF BIAS | STRONG BULL / BEAR / MIXED |
| SESSION / KILL ZONE | active session + KZ |
| PD Zone | price in Premium / Discount (what the gate uses) |
| CONFLUENCE | `▲bull ▼bear / max` score |
| POSITION / P&L | open trade + simulated R / $ |
| GUARDS | day R, consec losses, equity, drawdown % (red = a guard is blocking) |

---

## 11. Recommended starting presets

**Forex / Gold (5m–15m, intraday):**
- Display `Trading`, Entry Pivot `5`, Min Confluence `5`, Min RR `1.5`
- Hard Gate: HTF align ON, PD zone ON, Recent liq ON, Healthy vol ON
- Sessions timezone `America/New_York`, trade London + NY KZ

**Indices / Crypto (15m–1H, swing):**
- Entry Pivot `8`, HTF `240/D/W`, Daily reset `Chart exchange midnight`
- Dealing-range source `HTF swings (smoother)`

**More aggressive (more trades):**
- Pullback `Require confirmation = OFF`, Min Confluence `4`, Min RR `1.3`

**Stricter (fewer, A+ only):**
- Entry Pivot `8/12`, Min Confluence `6`, Min RR `2.0`, `Require ≥1 liquidity point = ON`

> Re-optimize Min Confluence and Min RR per instrument — the score scale differs by symbol.

---

## 12. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `too many tokens (>80000)` | You added code. Remove a cosmetic block (next-entry projection or a dashboard row) or trim long input tooltips. |
| `Undeclared identifier X` | A variable used before it's defined (Pine has no hoisting). Move the definition above first use. |
| No arrows ever | See §8 — gates/thresholds too strict, or pullback never retraces. |
| Pending entry far below price | Normal — it's a limit plan; Δ shows the distance. Price must retrace to fill. |
| Equity/P&L looks wrong | Set Account currency + equity correctly; check `⚠ FX conv unresolved` warning. |
| Numbers change on the live bar | Turn **Institutional Mode ON** (forces confirmed bars, non-repaint). |
| SL looks above a long entry | Fixed in v31. Re-paste the latest `smc-32.pine`. |

---

## 13. What v31 changed (forensic-audit fixes)

16 fixes incl.: confirmed-gated exit accounting (no intrabar equity repaint), OB/FVG mitigation no longer repaints, breaker/iFVG count caps (crash fix), Judas confluence un-inverted, RR fresh-sweep floor, alert = execution, deferred-fill re-validation, retro-broken swings no longer poison PD/liquidity, entry-track CHoCH honors the setting, plus the next-entry projection SL/RR geometry fix. Full list in the file header comment.

---

## 14. Honesty notes (read before going live)

- **Not a strategy.** No broker fills, no Strategy-Tester stats. Run `smc_strategy.pine` for real PF/Sharpe/DD/WFO.
- **Time Blackout** is a static clock, not a live news feed.
- **Setup-score (0–100)** is a heuristic confluence index, **not** a calibrated win rate.
- **Pullback mode misses runners** by design. That is a feature, not a bug.
- Always forward-test on demo before risking capital.
