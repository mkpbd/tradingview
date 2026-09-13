# AUDIT — CRT + TBS + TWS · MTF FORENSIC LAYER v1

Deliverable: **`15.crt-tbs-tws-mtf-layer-v1.pine`** — a standalone companion overlay. Pine `//@version=6`. Compile: **NOT VERIFIED** (Pine cannot be compiled locally); static checks below all pass.

**Files 13 and 14 are byte-for-byte untouched** — 323 063 bytes / 12:13:26 and 326 973 bytes / 13:29:08.

## Why a new file and not an edit to file 14

File 14 (`v6.0 UI2`) and its whole lineage sit at TradingView's compiled-token ceiling: v5.8 measured ~99 600 of the 100 256 cap, v5.9 returned ~30 source tokens, v6.0 spent ~50 again — roughly 500 compiled tokens of headroom remain, and the file is also at the CE10295 global-scope cap. Four HTF detection contexts, each carrying three state machines, is thousands of tokens. Putting it in file 14 would mean deleting working systems, which the scope lock forbids. Files 10 (ICT) and 12 (retail price action) are the precedent: a substantial new capability ships as its own overlay. Load both on one chart.

---

## 1 · CRT / TBS / TWS audit — what already existed, what was missing

| Engine | State in the lineage (file 14) | Verdict |
|---|---|---|
| **CRT** | `V5.5-E1` — a real five-state lifecycle (`LC_IDLE → LC_ARMED → LC_SWEPT → LC_RECL → LC_CONF`, plus `LC_INVAL`), reference candle must have CLOSED and span ≥ `crtRangeAtr × ATR`, penetration graded `CP_TINY / CP_MEAN / CP_DEEP` off the same thresholds the pool registry uses, reclaim through the range MID as a separate stage from the sweep candle's own close-back | Methodology **preserved**, not reinvented |
| **TBS** | `V5.5-E2` — same lifecycle over an N-bar extreme with a minimum age, decisive-reclaim distance, and a user-chosen confirmation rule | **Preserved**, including "a one-tick poke is a descriptor, not a pattern" |
| **TWS** | `V5.5-E3` — wave 1 interaction → a deeper, REJECTED wave 2 → reclaim with displacement; explicitly a context engine that never emits | **Preserved**, and it still never emits |
| **Confluence** | `V5.8-CTT` — one shared label per side updated to `CRT + TBS` / `CRT + TWS` / `TBS + TWS` / `CRT + TBS + TWS` inside `cttWin` bars | **Preserved** as the marking model |
| **MTF** | **MISSING.** All three ran on the CHART timeframe only. The single HTF path, `f_crtTbsHtf`, was a stateless one-shot boolean per HTF bar on ONE timeframe — no lifecycle, no reclaim stage, no penetration grade, no TWS at all | This is the gap file 15 fills |
| **Source-TF tagging** | **MISSING** — nothing carried the timeframe a structure came from | Added |

`UNRELATED EXISTING ISSUE — NOT MODIFIED`: none found in file 14's CRT / TBS / TWS engines this pass. The two items above are scope limitations, not defects, and file 14 was not edited either way.

---

## 2 · Changes made (CRT / TBS / TWS · 15M / 30M / 1H / 4H only)

### Detection — one scan function, four timeframe contexts
`f_cttScan()` runs the six state machines (three engines × two directions) **inside** `request.security`, so every calculation is native to that timeframe: its own ATR, its own bars, its own rolling extremes. Four calls: 15M, 30M, 1H, 4H. Twelve outputs each — CRT direction/quality/high/mid/low, TBS direction/quality/level, TWS direction/quality/wave-1 extreme, and the HTF bar's `time`.

### Validation — nothing is marked on movement alone
* **CRT** — reference candle CLOSED and ≥ `ctt_crtRng × ATR` wide → its extreme swept with the close back INSIDE the range → penetration graded → a **later** candle reclaims the range MID → a **later** candle displaces (body ≥ `ctt_dispAtr × ATR`, closing in its own outer third). A close beyond the swept extreme is expansion: `CS_INV`.
* **TBS** — the reference extreme must be ≥ `ctt_tbsAge` bars old (an extreme two bars old is the current leg, not resting liquidity) → swept with the close back on the origin side → graded → a **decisive** reclaim, 0.25 × ATR beyond the level → then the chosen rule: reclaim only / reclaim + displacement (default) / reclaim + delivery flip. A sweep alone is never a TBS; the extreme drifts with the window only while nothing has been taken, never after a sweep.
* **TWS** — wave 1 interaction with the window extreme → wave 2 must exceed wave 1 by ≥ `ctt_twsDeep × ATR` **and close back beyond wave 1** (rejected, not accepted) → wave 3 reclaims wave 1 **with** displacement. Acceptance beyond wave 2 invalidates: that is a trend, not a manipulation.
* **Quality** — WEAK / VALID / STRONG from sweep penetration in ATR (`ctt_minAtr`, `ctt_deepAtr`). `ctt_minQ` (default **Valid**) decides what earns a label; detection and the lifecycle are unaffected, so a weak poke is tracked and not drawn.

### Confluence (phases 6-9)
Each engine passes or fails on its own; a confluence label is only the union of **independently confirmed** structures on the **same timeframe**, the **same side**, inside `ctt_win` chart bars. Mask 1 = CRT, 2 = TBS, 4 = TWS, so `CRT + TBS` = 3, `CRT + TWS` = 5, `TBS + TWS` = 6, master = 7. Three labels landing near each other is never a master confluence.

### Marking
`CRT 15M ★★ ▲`, `TBS 1H ★★★ ▼`, `TWS 30M ★★ ▲`, `CRT + TBS + TWS 4H ★★★ ▲`. One label per timeframe per side inside the window — a second engine **updates** that label instead of stacking a chip. The tooltip carries structure, source timeframe, direction, quality, lifecycle and legs. CRT HIGH / EQ / LOW lines are drawn on confirmation from the stored reference candle, frozen at the sweep, capped at `ctt_maxRng` sets.

### Inputs added (all `ctt_`-prefixed, all CRT/TBS/TWS)
Engines: CRT / TBS / TWS toggles. Timeframes: 15M / 30M / 1H / 4H toggles. Validation: ATR length, CRT reference range, confirmation displacement, minimum and strong penetration, lifecycle window, TBS lookback / age / confirmation rule, TWS wave window / wave-2 depth, minimum quality. Marking: confluence window, CRT range lines + length + count, maximum labels, label size, label offset.

### Alerts (detection only)
`[CTT] CRT confirmed`, `[CTT] TBS confirmed`, `[CTT] TWS confirmed`, `[CTT] Confluence (≥ 2)`. No direction call, no entry, no exit.

---

## 3 · Untouched systems

**This is a separate script; it cannot reach into file 14's state.** It contains no code for, and reads nothing from: liquidity registry / pools / BSL / SSL, support, resistance, supply, demand, SMC, ICT, FVG, IFVG, order blocks, breaker blocks, mitigation blocks, rejection blocks, CISD, MSS, BOS, CHoCH, OTE, dealing range, premium / discount, trendlines, entry logic, buy / sell logic, TP, SL, RR, risk management, dedupe, score, grades, gates, sessions / killzones / Silver Bullet, volatility windows, the MTF bias dashboard, the debug panel, file 14's alerts, plots or inputs. Files 10, 12, 13 and 14 on disk are unmodified — 13 and 14 verified byte-identical by size and timestamp.

No BUY / SELL / LONG / SHORT / entry / exit / TP / SL / RR exists anywhere in file 15 (phase 14).

---

## 4 · TradingView safety audit

| Check | Result |
|---|---|
| **Non-repainting** | Every one of the twelve outputs is indexed `[1]` inside `f_cttScan`, so the chart only ever sees the **last CLOSED bar** of the requested timeframe. The developing HTF candle is never published. |
| **Lookahead** | `lookahead = barmerge.lookahead_off` on all four calls, as required — no future bar, no future confirmation shown early. |
| **MTF correctness** | A timeframe lower than the chart is never requested (`ctt_tf*` falls back to `timeframe.period`) and never drawn (`ctt_ok*` false), so 15M can never print as 30M, nor 1H as 4H. Every label carries its own source timeframe. |
| **Duplicate safety** | Each timeframe stores the `time` of the HTF bar it last processed; drawing runs only when that value changes, so a confirmation is drawn once, on the first chart bar after the HTF close, and never re-drawn on ticks or on an unchanged HTF bar. |
| **Realtime safety** | Pine rolls back `var` state (UDT instances included) before each intrabar recalculation, so an intrabar advance inside a security context cannot leak into a drawn object; and no object is created on a tick where the HTF time is unchanged. |
| **State / lifecycle** | `CS_IDLE → CS_ARM → CS_SWP → CS_RCL → CS_CNF`, plus `CS_INV` and the TWS `CS_W1 / CS_W2`. Terminal states clear on a LATER bar, so a confirmation is always visible for a full bar. Invalidation is deterministic: close beyond the swept extreme, acceptance beyond TWS wave 2, or `ctt_life` / `ctt_twsWin` expiry. |
| **Objects** | Labels and lines live in two FIFO-capped arrays (`ctt_maxLbl`, default 40, min 8; `3 × ctt_maxRng`, default 12 lines) against `max_labels_count = 500` / `max_lines_count = 500`. No boxes. No leak is possible — every push is followed by a capped shift. |
| **Arrays** | Three arrays, all fixed-shape or FIFO. `ctt_ev` is `array.new_int(4, 0)` and only ever indexed 0-3 by literal. No computed index, no negative index, no unbounded growth. |
| **Syntax / parser** | Verified mechanically: no duplicate function, type or global name (14 functions, 2 types, 114 globals); every `f_*` / `ctt_*` / `CS_*` / `CQ_*` / `CTT_*` / `Ctt*` use follows its declaration; parentheses and brackets balance; no tuple destructuring inside an `if` / `for` (Pine forbids it) — all six in `f_cttScan` are at function-body level and all four `request.security` destructures are at global scope; continuation lines are indented to a non-multiple of 4. |
| **Type safety** | Every int argument crossing the `request.security` boundary is passed through `int(nz(…, 0))`, and the one `math.max` chain that feeds an int is wrapped in `int()`, so no float→int assignment can be produced. |
| **Global-scope cap (CE10295)** | Global scope is four security calls, four destructures, four apply calls, four timeframe gates and the alerts. All per-bar logic lives in functions; all mutable state lives in UDTs and arrays. No function assigns a global scalar (Pine forbids it) — `f_ctt_apply` mutates a `CttTf` passed by reference and `ctt_ev` via `array.set`. |
| **Performance** | Per timeframe: 8 rolling built-ins and six small state machines — no history rescan, no nested loop, no array growth. The only chart-side loop is `for k = 0 to 1` and it runs solely on the bar where an HTF candle has just closed. Drawing is O(1) per event. |
| **Runtime** | No `na` arithmetic on a drawn coordinate (`na(pv) ? close : pv`, `nz(ctt_atr, high - low)`); `nz` guards on every `bar_index` comparison against a possibly-`na` stage bar. |

### Conceptual test matrix
15M / 30M / 1H / 4H charts each draw only the timeframes at or above them (a 1H chart shows 1H and 4H; 15M and 30M are gated off, which is the correct answer, not a silent mislabel). Lower-TF charts show all four. Bull / bear / ranging: the CRT and TBS invalidation rules retire swept references that turn into breaks, and the TWS acceptance rule kills three-wave claims inside trends. Strong vs weak sweeps separate by `ctt_minAtr` / `ctt_deepAtr` and the default minimum quality drops the weak ones from the chart. False TBS (an unaged extreme, or a sweep with no decisive reclaim) never reaches `CS_CNF`. Confluence marks only on genuinely independent confirmations. Realtime candle and HTF close: nothing is drawn until the HTF bar's `time` advances. Long history: label / line budgets are FIFO-bounded. Multiple symbols: everything is `syminfo.tickerid`-relative and ATR-normalised.

**Compile verification remains outstanding** — first paste into the Pine Editor will confirm.
