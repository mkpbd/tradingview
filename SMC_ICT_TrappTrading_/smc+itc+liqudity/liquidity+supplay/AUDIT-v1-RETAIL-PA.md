# AUDIT — RETAIL PRICE-ACTION FORENSIC LAYER v1 (SUPPORT · DEMAND · RESISTANCE · SUPPLY · PATTERNS)

Deliverable: **`12.retail-pa-forensic-layer-v1.pine`** — a standalone companion overlay. **`11.liquidty+supply-v5.8-ctt.pine` is byte-for-byte untouched.**

Pine version: `//@version=6`. Compile: **NOT VERIFIED** (Pine cannot be compiled locally). Paste into the Pine Editor; the script has its own full token budget (estimated ≈ 25–30 k compiled of 100 256), so CE10117 is not expected.

---

## 0. Why a new companion file and not an inline edit

| Fact | Source |
|---|---|
| File 11 compiles at ≈ 99 550 / 100 256 tokens (101 135 measured with MODULE 16B, ≈ 1 500 removed) | file 11 header, v5.8 note |
| File 11 sits at the CE10295 global-scope cap | file 11 header, v5.7 note |
| Five new detection systems ≈ 20 k+ compiled tokens | estimate from file 10 (16 k for ICT) |
| Brief forbids removing / trimming any other subsystem to make room | brief, ABSOLUTE SCOPE LOCK |

Inline = guaranteed CE10117. The only scope-safe path is the one file 10 (ICT layer) already took: a second indicator on the same chart. Result: **zero** edits to liquidity, SMC, ICT, CRT, TBS, TWS, FVG, OB, breaker, mitigation, CISD, MSS/BOS/CHoCH, entry logic, TP/SL, alerts, MTF, sessions, inputs, plots or UI of file 11.

---

## 1. What was found in file 11 (read in full, 5 368 lines)

| System | What file 11 has | Verdict |
|---|---|---|
| **Support** | `lastSup = sInt.swLo` — the LAST internal pivot low, plotted as "Support (last swing low)" (MODULE 17). One level, no touches, no strength, no lifecycle, replaced on every new pivot. | Not retail support. Left untouched. |
| **Resistance** | `lastRes = sInt.swHi`, same construction. | Same. Left untouched. |
| **Demand** | MODULE 9 `Zone`: created from **displacement + bullish FVG** (`newDemand = bullFVG and zDispUp`), plus `REJECTION ▲` wick blocks. T1/T2/T3 tier, 50 % tap engine, breaker / mitigation flip. **Feeds the TRADE ENGINE** (`sdCandLong`). | ICT imbalance POI, not a rally-base-rally zone. Left untouched (it is trade-engine input). |
| **Supply** | Mirror of the above (`newSupply = bearFVG and zDispDn`, `REJECTION ▼`). | Same. Left untouched. |
| **Patterns** | MODULE 11 = trap engine (① breakout-rejection, ② pin-bar trap), CRT, TBS, TWS state machines; `bullPin / bearPin / bullEngulf / bearEngulf` used as **confirmation candles** for retests. No classical chart patterns (no double top/bottom, H&S, triangle, flag). | Producers for the trade engine. Left untouched. |

Naming check: every new identifier in file 12 carries `ret_` / `RET_` / `RCOL_` / `RC_` / `PT_` / `Ret*` prefixes; no name collides with file 11 (irrelevant across scripts, but kept for the brief's PHASE 22).

---

## 2. What the new layer does (file 12 only)

### 2.1 Support / Resistance (MODULE 5)
- **Source**: confirmed `ta.pivotlow / ta.pivothigh(pivLen, pivLen)`.
- **Merge**: a same-side swing inside `ret_srTol` ATR of an existing level = a TOUCH; the level re-centres on the mean of its legs. No duplicate levels at one price.
- **Tests**: edge-triggered wick into the zone with the close held (`inside` latch) = a TEST.
- **Role flip**: a swing of the opposite kind at a PENDING/BROKEN qualified level = R>S / S>R, same object, `flips` counted. A swing of the opposite kind at an ACTIVE level creates nothing (noise inside the zone).
- **Eligibility to draw**: `touches + tests ≥ ret_srMinT` (default 2) **or** a flip, **and** class ≥ minimum. A single low is never marked.
- **Strength** (`f_ret_lvlCls`): touches, tests, post-swing reaction (ATR), rejection wick, flips, failed breaks; minus weakening / age → WEAK · NORMAL · STRONG · MAJOR.
- **Lifecycle**: candidate → fresh → tested → WEAKENING (tests ≥ `ret_srWeak`) → BREAK? (close beyond zone by `ret_srBrk` ATR) → FAILED BREAK (close back inside within `ret_srRecl` bars, level strengthens) **or** BROKEN → flip (default) or dimmed for `ret_srKeep` bars → removed. Expiry after `ret_srLife` bars without a touch. Unqualified candidates that break are simply dropped.
- **Cap**: `ret_srMax` per side, weakest-then-oldest evicted.
- **Separation from S/D**: with `ret_sdHideSR` a level covered by a live same-side zone is hidden (box deleted, registry kept) and re-appears when the zone dies. No "Support + Demand" double label.

### 2.2 Demand / Supply (MODULE 6)
- **Trigger**: a confirmed DEPARTURE candle — body ≥ `ret_sdDep` ATR (× sensitivity), close in its outer 30 %, close beyond the base by `ret_sdLeave` ATR.
- **Base**: the consecutive candles immediately before it with range ≤ `ret_sdBaseRng` ATR, up to `ret_sdBaseMax`. No base → no zone (a lone big candle is not demand).
- **Geometry**: proximal edge = base bodies, distal edge = base wicks; clamped to `[RET_MIN_H_ATR, ret_sdMaxH]` ATR.
- **Kind**: leg-in candle (with a real body) names it: **DBR / RBR** (demand), **RBD / DBD** (supply). DBR / RBD are flagged as reversal zones (stronger).
- **Follow-through**: checked ONCE, `ret_sdFt` bars later (`ret_sdFtAtr` ATR away) — forward-only upgrade.
- **Strength** (`f_ret_zCls`): departure body, base length, reversal kind, follow-through, freshness, width.
- **Lifecycle**: fresh → tested (edge-triggered) → WEAKENING (`ret_sdWeak`) → BROKEN (close beyond distal edge by `ret_sdBrk` ATR, box frozen, dimmed `ret_sdKeep` bars) → removed. Expiry `ret_sdLife`.
- **Dedupe**: overlapping live same-side zone → skip. Cap `ret_sdMax` per side, weakest-then-oldest.

### 2.3 Retail patterns (MODULE 7) — marked only on the CONFIRMED completing close
| Pattern | Geometry (confirmed swings) | Confirmation |
|---|---|---|
| Double bottom / top | last two same-side swings within `ret_ptTol` ATR, ≥ `ret_ptSep` bars apart, neckline = extreme swing between them, depth ≥ `ret_ptDepth` ATR | close through the neckline with body ≥ 0.5 ATR |
| Triple bottom / top | last three within tolerance, spread ≥ 2 × sep | same; suppresses the double for the same swing |
| Head & shoulders / inverse | three swings, head beyond both shoulders by ≥ `ret_ptHead` ATR, shoulders within 2 × tol, neckline through the two intervening swings (tilt ≤ 1.5 ATR) | close through the projected neckline at the current bar |
| Bull / bear flag | pole ≥ `ret_ptPole` ATR into the first swing (`ret_ptPoleB` bars), then falling highs + falling lows (bull) retracing ≤ 62 % of the pole | close beyond the last channel swing |
| Bull / bear pennant | pole, then converging (falling highs + rising lows) | close beyond the last swing in the pole direction |
| Ascending / descending triangle | flat highs + rising lows / flat lows + falling highs | close beyond the flat side |
| Symmetrical triangle | falling highs + rising lows, height ≥ 1 ATR, no pole | close beyond the last swing (up or down) |
| Rectangle | flat highs + flat lows, height ≥ 1 ATR | close beyond the range (up or down) |

One mark per swing set per type (`ret_ptKey`); all swings must sit inside `ret_ptWin` bars. **Rounding top / bottom are NOT implemented** — a pivot-based reading produces mostly noise, and the brief lists them as "potential", not required.

### 2.4 Candle patterns (MODULE 8)
ENGULF ▲/▼ · HAMMER · SHOOTING STAR · OUTSIDE ▲/▼ · INSIDE · BREAKOUT ▲/▼ (a level / zone closed through with a real body and strong close) · FAILED BREAK ▲/▼ (a pending S/R break reclaimed). Default: **only at a live drawn level / zone**; one chip per side per `ret_cdlCd` bars; ring of 80.

### 2.5 Visual / summary (MODULE 10) · Alerts (MODULE 11)
Boxes only for zones, small chips for patterns, one rebuilt summary label. Eight `alertcondition`s, all observational (`[S/R]`, `[S/D]`, `[PATTERN]`). **No BUY / SELL, no entry, SL, TP, RR anywhere.**

---

## 3. Deliberately NOT changed
Everything in file 11: liquidity registry + marking, SMC/ICT, CRT/TBS/TWS engines and CTT marking, FVG/IFVG, OB/breaker/mitigation, CISD, MSS/BOS/CHoCH, setup machine, trade engine, TP/SL, risk, alerts, MTF (`request.security`), sessions, dashboard, debug panel, every input, every plot. File 11 was **read** in full and **not written**.

`UNRELATED EXISTING ISSUE — NOT MODIFIED`: none newly found in the parts read this pass beyond those already logged in AUDIT-v5.8-CTT.md.

---

## 4. Error / safety audit (file 12)

| Check | Result |
|---|---|
| Syntax / parser | 4-space blocks; every continuation line indented to a non-multiple of 4 (scripted check: 0 violations); no tabs; no tuple destructuring anywhere; no nested-ternary deeper than a flat chain; readable intermediate booleans. |
| Scope rules | Functions mutate only UDT fields, arrays and drawings (never a global scalar); all `ta.*` calls at global scope; history offsets use loop / input ints only; `max_bars_back = 200` covers `[ret_pivLen + 1]` and base scans. |
| Types | No `na` int/float mixing without `nz`/`na()`; all functions end with a single-type expression; `array.new<int>(7, -1)` keys. |
| Runtime | Every `for i = size-1 to 0` guarded by `size > 0`; reverse iteration when removing; `break` on failed cap search; divide-by-zero guarded (`ret_atr > 0`, `x2 > x1`). |
| Repainting / lookahead | All state inside `barstate.isconfirmed`; pivots `(pivLen, pivLen)`; post-swing reaction read from the confirming window; patterns marked on the completing close; follow-through is a forward-only upgrade; no `request.security`; no future bars. |
| Object limits | S/R ≤ 24 boxes, S/D ≤ 24 boxes, pattern sets ≤ `ret_ptMax` (≤ 3 lines + 1 label each), chips ≤ 80, summary 1. Broken objects frozen, then deleted. |
| Array safety | Rings trimmed to `RET_RING`; pattern set counts tracked so deletions stay aligned; keys sized 7 for 7 slots. |
| MTF safety | No MTF in this layer. File 11's MTF untouched. |
| Realtime safety | Nothing draws intrabar except the last-bar `set_right` / summary rebuild; a realtime bar changes no state until it closes. |
| Performance | Per-bar loops over ≤ 24 levels × ≤ 24 zones (shadow check) + 8-slot rings; base scan ≤ 10 bars; one function call per bar. |

## 5. Structural test matrix (mental, as the brief asks)
1–3 trends: levels merge along the trend and flip on breaks (R>S in an uptrend); flags / pennants need the pole. 4 sideways: rectangle / triangles, many tests → WEAKENING, cap keeps the strongest. 5–6 volatility: every threshold is ATR-scaled; `Strict / Loose` sensitivity. 7–8 stacked levels: merge distance fuses them; cap evicts weakest. 9–10 fresh zones: `fresh · FT` upgrade after `ret_sdFt` bars. 11 retests: edge-triggered counting, never one per bar. 12–13 break vs false break: PENDING → FAILED BREAK / BROKEN with `ret_srRecl` bars of honest delay. 14–16 patterns: geometry from confirmed swings, mark only on the completing close. 17 realtime: no state change intrabar. 18 long history: bounded objects everywhere. 19–20 symbols / timeframes: ATR-relative, bar-relative windows.

**Compile verification remains outstanding** — first paste into TradingView will tell.
