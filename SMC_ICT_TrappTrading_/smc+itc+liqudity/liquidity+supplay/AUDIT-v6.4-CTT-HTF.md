# AUDIT v6.4 — CRT / TBS / TWS marking moves to the auto HTF

File: `19.liquidty+supply-v6.4-ctt-htf.pine` (from `18.liquidty+supply-v6.3-fit.pine`)
Scope: **display only.** No entry, exit, TP/SL, gate, grade, score, dedupe, state
machine, producer, request.security or alert was edited.

---

## 1 · The reported defect

Screenshot: XAUUSD 5m, roughly twenty CRT / TBS / TWS marks in one session —
`CRT SWP deep` ×3, `CRT SWP real` ×3, `TWS SELL ★ ✗` ×2, `CRT + TWS ★★ ✗`,
`TBS SELL ★★`, `CRT HIGH / CRT EQ / CRT LOW` ×2 sets, plus confirmation chips.

Requested behaviour: CRT / TBS / TWS should come from the **higher timeframe**,
per the map the user stated — 1m → 15m, 5m → 1H, 15m → 4H. That map is already
`f_autoHtf()` in this file; the marking layer simply never used it.

## 2 · Root causes (four, all in the marking layer)

| # | Where | What it did |
|---|-------|-------------|
| 1 | `f_ctt_chart()` | Ran CRT / TBS / TWS off the **chart** timeframe. `f_crtAdvance` re-arms on any closed candle spanning ≥ `crtRangeAtr`(1.2) × ATR — on 5m that is every few bars, so it swept and confirmed constantly. |
| 2 | `f_ctt_swp()` | Drew a separate `CRT SWP <class>` chip on **every** graded sweep, on top of the confirmation mark that followed it off the same range. |
| 3 | `f_cttMark` | Drew the mark even when the ⑫⑬ **location filter failed**, appending `✗`. Those patterns can never trade (`crtNeedLoc`) — pure noise. |
| 4 | `cttShowRng` | Every confirmation drew CRT HIGH / EQ / LOW: 3 lines + 3 labels, 3 sets kept. |

## 3 · The fix

**H1 — new input** `⑫⑬ CRT / TBS / TWS marking timeframe`
`HTF (auto)` *(default)* · `Chart` (v6.3 behaviour) · `Both`.
`HTF (auto)` uses `htfTf`, i.e. `f_autoHtf()` unless `⑦ HTF for CRT / TBS / POI`
overrides it: 1m→15m · 2m/3m→30m · 5m→1H · 10m→2H · 15m/30m→4H · 1H/2H/4H→D.

**H2 — new input** `⑫⑬ Only mark patterns at a valid LOCATION` (default ON).
Hides every `✗` mark. Same test `crtNeedLoc` uses: HTF FVG POI, a raided
engineered / external pool, OTE, or a premium / discount extreme.

**H3 — removed, with the reason (§40):** the per-sweep `CRT SWP` chip
(`f_ctt_swp`). It announced a sweep that the confirmation mark then announced
again two to five bars later off the same range. Nothing is lost: the sweep
still advances the CRT lifecycle (`LC_SWEPT`), still appears in the dashboard's
`CRT·TS·TWS` row, still attaches its event descriptor via `f_evTag`, and still
produces the confirmation mark when the reclaim and displacement arrive. Its
~60 raw tokens paid for H4/H5.

**H4 — the HTF marks reuse `f_cttMark`.** A CRT and a turtle soup confirming on
the same HTF candle therefore share ONE label — `CRT + TBS ★★ 60` — instead of
stacking two chips, exactly as the chart-TF marker already did (V5.8-CTT-4).
`f_cttMark` gained one `string sfx` parameter carrying the source timeframe;
chart-TF calls pass `""`.

**H5 — zero new `request.security` calls and zero new HTF series.** The HTF
marks are drawn from `hCrtB / hCrtS / hTbsB / hTbsS`, published by
`f_crtTbsHtf` on `htfTf` since v2 and until now read only by the trade engine.

## 4 · Non-repainting

`f_ctt_htfMark()` writes only inside `confirmed and newHtfBar`. `newHtfBar`
fires on the first chart bar after the HTF candle has **closed** — the `[1]` is
inside `f_crtTbsHtf`'s return, so only a completed HTF candle is ever visible.
No new lookahead, no back-dating, one mark per HTF event.

## 5 · Known limits, stated

- **No HTF TWS.** MODULE 11C, the layer that had TWS on 15/30/60/240, is 8 890
  compiled tokens and was removed in v6.3. In `HTF (auto)` mode TWS is not
  marked. Use `Both`, or run `15.crt-tbs-tws-mtf-layer-v1.pine` on the same
  chart.
- **HTF CRT / TBS is the stateless `f_crtTbsHtf` test**, not the v5.5-E
  lifecycle: no penetration grade, no separate reclaim stage. HTF marks
  therefore print `★★` flat rather than `★ / ★★ / ★★★`.
- **CRT HIGH / EQ / LOW are chart-timeframe drawings** and follow the chart-TF
  marker — they appear in `Chart` and `Both`, not in `HTF (auto)`.
- If `htfTf` equals the chart timeframe (`htfLive` false), `newHtfBar` never
  fires and `HTF (auto)` draws nothing. Set `⑦ HTF` explicitly or use `Chart`.

## 6 · Token budget — MEASURED, then fixed

**First build returned CE10117: 100 451 / 100 256 — over by 195.**
The prediction (≈100 056) was wrong because the v6.3 baseline was ≈100 135, not
the ≈99 740 the v6.3 header assumed.

### The model, now calibrated on three real TradingView results

| build | compiled (measured) | raw source tokens |
|---|---|---|
| v6.0 (file 14) | 99 740 | 34 901 |
| v6.2 (file 17) | 108 630 | 37 636 |
| v6.4 first build (file 19) | 100 451 | 35 141 |

Linear fit through the first two: **compiled ≈ 3.250 × raw − 13 704**
(comments excluded, dotted names counted as one token). It predicts the third
at 100 504 against the measured 100 451 — error 53 in 100 000.
**One raw source token ≈ 3.25 compiled tokens.**

### The optimisation pass (V6.5-O) — no feature removed

| # | change | raw saved |
|---|---|---|
| O1 | `f_cpTxt` — zero call sites after H3 retired the sweep chip | ~22 |
| O2 | `f_crtAdvance` returned `[conf, swept]`; `swept` fed only that chip | ~16 |
| O3 | `f_htfCtx` published `htfSwHi` / `htfSwLo` — read by nothing. **Two HTF series dropped** | ~10 + 2 series |
| O4 | MODULE 15's five-producer ladder was written twice, mirrored, behind forty default declarations → one `f_prod`, two calls | ~153 |
| O5 | 73 named constants `var <type> NAME = lit` → `NAME = lit`. Makes them **const**-qualified instead of a persistent variable holding a literal; none is ever reassigned, and const is accepted anywhere simple/series is | ~156 |
| O6 | the breaker / mitigation flip was mirrored supply↔demand → one `f_zoneFlip(z, toSup, isBrk)` | ~37 |

**35 141 → 34 747 raw (−394) ≈ −1 280 compiled.**
Predicted **99 224 of 100 256 — about 1 030 spare.**
Main body 1 809 statements vs the 2 034 that last compiled, so CE10295 is not
in play; O4 and O6 both hand statements back to the main body.

### If TradingView STILL returns CE10117

The prediction has ~1 030 of margin and the model's error on the last three
builds was 53, so this should not happen. If it does, in order — each is
self-contained and inside CRT / TBS / TWS scope:

1. delete `CTT-CUT-1` (the CRT HIGH / EQ / LOW lines and `f_cttLvl`, ~550);
2. delete `CTT-CUT-2` (the whole chart-TF marker) and leave `cttSrc` on
   `HTF (auto)`, which is already the default;
3. the remaining large non-CTT systems, measured: MODULE 18 dashboard
   ≈ 6 090 compiled · MODULE 8B liquidity marking ≈ 3 960 · MODULE 19 debug
   panel ≈ 3 680. Those are feature removals, so they are a last resort.
