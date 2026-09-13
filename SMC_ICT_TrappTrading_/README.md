# ICT + SMC Institutional Toolkit — v1.2.0

Single Pine Script **v6** indicator: market structure, liquidity, order blocks, imbalances,
premium/discount, PD-array levels, sessions & kill zones, ICT time model, HTF bias, a gated +
scored entry model, dashboard, 26 alert conditions.

**File:** `ICT_SMC_Institutional_Toolkit.pine` · **Status:** compiles clean on TradingView, tested live on XAUUSD 3m/15m.

---

## 1. Quick start

1. TradingView → **Pine Editor** → paste the file → **Save** → **Add to chart**.
2. After any script update: **remove the indicator and re-add it** (or *Settings → Defaults → Reset*) — TradingView pins old input values otherwise.
3. Alerts — two ways:
   * **Granular:** *Create Alert → Condition → ICT│SMC →* pick one of 26 named conditions (e.g. `Entry BUY`), trigger **Once per bar close**.
   * **Firehose:** one alert on **Any alert() function call** — receives every category enabled in *Settings → ⑬ Alerts*, all messages pre-formatted with ticker/timeframe/score.
4. First look: dashboard top-right shows Trend / HTF bias / Structure / Prem-Disc / Session / Liquidity / Signal at a glance. BUY/SELL labels print with score + grade; `✕` marks the structure-based exit.

## 2. Reading the chart

Visual hierarchy is deliberate — **the louder it renders, the more actionable it is**:

| Layer | Look |
|---|---|
| BUY/SELL/✕ signals, BOS/CHoCH/MSS labels | solid, primary text size |
| Fresh OB / FVG / IFVG / BPR | colored boxes riding the right edge |
| Touched / frozen zones | frozen at mitigation point, one notch fainter, dimmed tag |
| Breaker (gold `BRK`) / Reclaimed (`RCL`) | recolored, live again |
| Liquidity levels (BSL/SSL/EQH/EQL) | dotted lines, `×` when swept, `RAID` on displacement |
| HTF zones (`HTF-OB`, `HTF-FVG`) | fainter than chart-TF zones — context, not entries |
| PDH/PDL/PWH/PWL… | dashed lines, fade once broken |
| Fib 62/70.5/79 + OTE band | max 150 bars wide, amber |
| Sessions / kill zones / silver bullet / macros | one whisper-level background shade per bar, KZ wins |

## 3. Architecture

19 numbered sections, top-down. Mutable state lives in UDTs (`MS`, `Zone`, `Liq`, `Lvl`, `Sess`,
`Cand`) because Pine forbids assigning to global scalars inside functions — object fields keep the
engines modular. Every drawing is owned by a UDT in a registry array, trimmed to its cap, deleted
on eviction.

| § | Block | § | Block |
|---|---|---|---|
| 1–2 | Palette, 17 settings groups | 11 | FVG · IFVG · BPR · VI · OG |
| 3–4 | UDTs, registries, confluence memory | 12 | Prem/Disc, fib, OTE |
| 5 | Helpers (recycling, rendering, noise filter) | 13 | 12 PD-array levels |
| 6 | HTF data layer (batched security) | 14 | Sessions & kill zones |
| 7 | Pivots & displacement | 15 | Time model |
| 8 | BOS / CHoCH / MSS / CISD | 16 | HTF machine + trend vote |
| 9 | Liquidity engine | 17 | Entry model & score |
| 10 | Order block engine | 18–19 | Dashboard, alerts |

## 4. Detection rules (exact)

* **Structure break** = candle **close** beyond a *confirmed* pivot (`ta.pivothigh/low`, lag = length, never revises). Wick-only penetration is routed to the liquidity engine as a sweep, never a break. First break in history initialises direction silently (no fake CHoCH).
* **BOS** continues direction; **CHoCH** is the first close against it; **MSS** = CHoCH whose breaking candle range ≥ `1.5 × ATR`; **CISD** = close back through the open of the opposing same-colour candle run.
* **Order block** = origin candle of the breaking impulse (deepest opposing candle in lookback, or last-opposite). Lifecycle `FRESH → MITIGATED → INVALID → BREAKER / RECLAIMED`; breaker requires the retest on a **later** bar than the invalidation. ≥60%-overlap duplicates are skipped.
* **FVG** = 3-candle gap ≥ `0.15 × ATR` with same-direction middle candle. Fully traded through → flips in place to **IFVG** (fill tracking + right edge reset). Overlapping same-direction gaps auto-merge (`×N` stack tag at 3).
* **Zone touch** counts only on bars **after** creation — the displacement candle that creates a zone always overlaps it geometrically and must not count as confluence.
* **Sweep** (strict, default) = wick through a stored level + close back inside; **raid** = sweep + opposite displacement within 3 bars.
* **Zones freeze**: fresh zones ride the right edge; a touched/invalidated zone freezes where the event happened. Breaker and IFVG un-freeze. Anything older than `Zone Max Age` (500 bars) is deleted.

## 5. Entry model

Signal = **all enabled gates pass** AND **score ≥ threshold** AND **locks clear**, committed on bar close.

**Gates** (each toggleable; a gate whose source module is disabled auto-passes):

| Gate | Requirement within the 12-bar confluence window |
|---|---|
| Sweep | liquidity sweep in trade direction |
| Shift | MSS **or** CISD in trade direction |
| Zone | OB **or** FVG touched in trade direction |
| Prem/Disc | discount for buys, premium for sells |
| HTF | HTF structure bias aligned |
| Kill zone (off by default) | inside KZ or Silver Bullet window |

**Score** (editable weights, default sums to 100):
`Sweep 20 · OB 20 · FVG 15 · HTF 15 · OTE 10 · Session 10 · CISD 10 · Volume 0`
Grades: **HIGH ≥ 80 · MEDIUM ≥ 60 · LOW** below. Print threshold `emMinScore` = 65.

**Locks:** one signal per external structural leg + `emCooldown` (10 bars) hard minimum distance + `barstate.isconfirmed` (no intrabar flicker). **Exit** (`✕`) on opposing external structure break. Stop/target guides: 1R = signal-bar swing floored at ¼ ATR, target = `emRR` (2.0) multiple.

## 6. Non-repainting contract

1. Structure: close beyond confirmed pivot only.
2. HTF: every read is `expr[1]` + `lookahead_on` — last **closed** HTF value, correct alignment, zero future leak. (The `[1]` shift is what makes `lookahead_on` safe.)
3. PD-array levels read the *previous* period — immutable once closed. Only CDH/CDL (off by default) are live.
4. Signals commit on `barstate.isconfirmed`; dynamic alerts fire `once_per_bar_close`.
5. Pine rolls back `var` mutations on intrabar recalculation, so state machines cannot corrupt history.

Net: **nothing on a historical bar was computed with information that bar could not have had.**

## 7. Performance

* 7 `request.security` calls total: 1 batched 13-expression HTF call + 3 period calls carrying extremes **and** opens + quarterly/yearly/current-day.
* `pfMaxBars` (2000) skips detection on older history — the main 1-minute-chart knob.
* `pfHeavy` restricts cosmetic refresh (box stretching, label moves) to the last bar; detection unaffected.
* `pfZoneAge` (500) hard-deletes stale zones.
* Registry caps: OB 3/side · FVG 4/side · HTF 2/side · liquidity 8 · structure 8 · sessions 3 · time 6/day · signals 20.
* Session/KZ shading via `bgcolor` — zero drawing objects, and only **one** shade per bar.

## 8. Tuning

| Want | Change |
|---|---|
| Fewer / higher-quality signals | all gates on, `emMinScore` 80, `emKzOnly` on, `emCooldown` 20 |
| More signals | drop Sweep or Shift gate, `emMinScore` 50, `emWindow` 20 |
| Cleaner chart | `fvMax` 2, disable OG, `noiseFactor` 0.25 |
| Busier chart | raise per-side caps, enable swing labels + PD zones + VI |
| Bigger text | General → Label Size → `large` (two-tier: secondary labels render one step below primary) |
| Faster on 1m | `pfMaxBars` 800, disable HTF FVG |
| Different HTF | untick Auto HTF, pick manually |
| Non-NY hours | edit session strings; all times evaluate in Reference Timezone |

## 9. Pine v6 compile traps (learned the hard way — keep for future edits)

1. **CE10235:** every branch of an `if`/`else if` chain must end in the *same type*, even when the value is discarded. `break` (void) beside an assignment (float) fails. Fix: split into independent single-branch `if`s guarded by a bool.
2. **CE10088:** functions cannot assign to global scalars. Return values in tuples and write globals at call site, or hold state in UDT fields (field mutation is allowed).
3. **CE10095:** one namespace for everything — an `input.color` named `cKz` collides with a bool `cKz`.
4. **Ternary object creation leaks:** Pine evaluates both `?:` branches → `x := na(x) ? box.new() : x` creates a box every bar. Always `if na(x)`.
5. `plotshape` size must be a **const** — no input-derived sizes there.

## 10. Changelog

### v1.2.0 — signal-quality audit
* Zones can no longer self-touch on their creation bar (confluence inflated at the break → premature signals).
* Gates auto-pass when their source module is disabled (Prem/Disc off used to block every signal).
* `emCooldown` + close-confirmation kill back-to-back and intrabar-flicker signals.
* First break in history initialises silently (no fake CHoCH).
* Two-tier label sizing, default `normal`; dashboard one step bigger.
* `request.security` 10 → 7 calls.

### v1.1.0 — lifecycle correctness + chart hygiene
* Breaker requires retest on a later bar than invalidation (was same-bar).
* Zone right-edge freezing (fresh rides edge, touched freezes; breaker/IFVG un-freeze) — killed the ghost-rectangle wallpaper.
* ≥60%-overlap duplicate suppression for OB/HTF; EQH/EQL no longer double-print BSL/SSL.
* Volume-na hardening; ¼-ATR risk floor; `✕` exit marker.
* One background shade per bar; HTF fainter than LTF; PD full-range shading off by default; fib clamped to 150 bars; `pfZoneAge`; trimmed defaults.

### v1.0.0
* Initial release: all 19 sections, full OB lifecycle, IFVG inversion, HTF structure machine, gated scoring, 26 alert conditions, object-recycling registries.

## 11. Extension points

* **SMT divergence** — largest missing ICT concept: needs a correlated-symbol input (`request.security` on ES/NQ or EURUSD/GBPUSD) + swing comparison at pivots. Registry + label plumbing already fits.
* **New zone kind** — add a `kind` string, a color case in `f_zoneBase`, a detector calling `f_drawZone`. Lifecycle/trim/render free.
* **New level** — push an `Lvl` + cases in `f_lvlPrice` / `f_lvlShow`.
* **New confluence factor** — weight input + direction-aware flag + one `f_score` argument.
* **Strategy port** — swap to `strategy()`, drive entries from `buySig`/`sellSig`/`exitSig`; `stopPx`/`tgtPx` already computed.
* **Webhooks** — replace `alert()` message strings with JSON payloads.

## 12. Known limitations

* Intraday-only features (verticals, macros, silver bullet, KZ shading) silent on daily+ charts.
* True bid/ask spread unavailable in Pine — dashboard shows tick size.
* Volume features inert on feeds without volume (auto-degrade, never block).
* MSS displacement measures the breaking candle, not the full leg.
* "Mitigation block" = retained mitigated OB (simplified vs strict ICT definition).
* Quarters are calendar `3M`, not fiscal.
