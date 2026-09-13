# AUDIT v6.1 — CRT / TBS / TWS ON 15M / 30M / 1H / 4H (V6.1-CTT-MTF)

Deliverable: **`16.liquidty+supply-v6.1-ctt-mtf.pine`** = `14.liquidty+supply-v6.0-ui2.pine` + **MODULE 11C**, the MTF CRT / TBS / TWS detection and marking layer. File 14 is byte-for-byte untouched (326 973 bytes / 13:29:08). Pine `//@version=6`.

**Compile: expected to FAIL with CE10117 as shipped — see §5. Read that section before pasting.**

---

## 1 · CRT / TBS / TWS audit

| Engine | What file 14 already had | Kept? |
|---|---|---|
| **CRT** | `V5.5-E1` `f_crtAdvance` — a real lifecycle `LC_IDLE → LC_ARMED → LC_SWEPT → LC_RECL → LC_CONF / LC_INVAL`, reference candle must have CLOSED and span ≥ `crtRangeAtr × ATR`, penetration graded `CP_TINY / CP_MEAN / CP_DEEP` off `raidMinAtr` / `raidDeepAtr`, reclaim through the range MID as its own stage | untouched, and its methodology is what MODULE 11C reuses |
| **TBS** | `V5.5-E2` `f_tbsAdvance` — same lifecycle over an aged N-bar extreme, decisive reclaim, three user confirmation rules | untouched |
| **TWS** | `V5.5-E3` `f_twsAdvance` — wave 1 → deeper REJECTED wave 2 → reclaim + displacement, context only, never emits | untouched |
| **Marking / confluence** | `V5.8-CTT` — one shared chip per side inside `cttWin`, updated to CRT + TBS / CRT + TWS / TBS + TWS / CRT + TBS + TWS; CRT HIGH / EQ / LOW via `f_cttLvl` | untouched, still owns the CHART timeframe |
| **MTF** | **missing.** All three engines were CHART-TIMEFRAME only. The single HTF path, `f_crtTbsHtf`, is a stateless one-shot boolean per HTF bar on ONE timeframe (`htfTf`), with no lifecycle, no reclaim stage, no penetration grade and no TWS — and it feeds the trade engine, so it was left exactly as it is | this is the gap MODULE 11C fills |
| **Source-TF tag** | missing | added |

`UNRELATED EXISTING ISSUE — NOT MODIFIED`: none found in the CRT / TBS / TWS engines this pass.

---

## 2 · Changes made (CRT / TBS / TWS + 15M / 30M / 1H / 4H only)

**Three edits to existing text, all of them CRT/TBS/TWS or cosmetic:** the `indicator()` title, six new inputs appended inside the existing group ⑩ (`ctt_m15`, `ctt_m30`, `ctt_m60`, `ctt_m24`, `ctt_mQ`, `ctt_mMax`), and the v6.1 header comment. Everything else is the new block inserted after `// CTT-CUT-2 ends`.

**MODULE 11C — MTF-1 one machine, four contexts.** `f_ctt_htf()` is requested on 15 / 30 / 60 / 240 and returns fourteen values: the CLOSED HTF candle (`high[1]`, `low[1]`, `close[1]`), the candle before it (`high[2]`, `low[2]`), that timeframe's ATR, its displacement verdict as ±1/0, its aged TBS extremes and their ages (`[2]`, so the level pre-dates the sweep), its TWS window extremes, and the HTF bar's `time`. The state machines then run **chart-side inside one `for` loop** over 4 timeframes × 2 directions, so machine code is compiled ONCE instead of 24 times. 24 UDT instances (`4 × 3 engines × 2 sides`) are allocated once, indexed `tf*6 + engine*2 + dir`.

**MTF-2 CRT and TBS share one machine** (`f_ctt_mach`, `kind` 0/1) because after arming they share every stage. CRT: reference = previous CLOSED candle, must span `crtRangeAtr × ATR`, sweep must close back INSIDE the range, reclaim = the range MID. TBS: reference = an AGED rolling extreme (`tbsAgeMin`), sweep must close back on the origin side, reclaim must clear the level by `NEAR_LVL_ATR × ATR`. Both then need displacement on a LATER bar — except the existing `"Close back inside"` mode, which confirms at the reclaim, exactly as `f_tbsAdvance` does.

**MTF-3 TWS keeps its own shape** (`f_ctt_tws2`): wave 1 interaction → wave 2 exceeds wave 1 by ≥ `twsDeepen × ATR` **and closes back beyond it** → wave 3 reclaims wave 1 WITH displacement. Acceptance beyond wave 2 invalidates.

**MTF-4 grading + invalidation** are the file's own: `CP_TINY / CP_MEAN / CP_DEEP` printed ★ / ★★ / ★★★; `ctt_mQ` defaults to **Valid**, so a one-tick poke is tracked and never drawn. A close beyond the swept extreme, or `crtLife` / `twsWaveWin` bars **of that timeframe**, sets `LC_INVAL` and the structure can never confirm afterwards.

**MTF-5 confluence.** Each engine passes or fails on its own; inside `cttWin` chart bars, on ONE timeframe and ONE side, the label is UPDATED to `CRT+TBS` / `CRT+TWS` / `TBS+TWS` / `CRT+TBS+TWS`. Marks read `CRT+TBS 1H ★★ ▲`.

**MTF-6 duplicate + repaint control.** A timeframe is processed only when its published `time` changes, and only on a CONFIRMED chart bar. Every read is `[1]` / `[2]` inside the request; calls use `barmerge.lookahead_off`. A timeframe at or below the chart is never requested (falls back to `timeframe.period`) and never drawn, so the v5.8-CTT layer keeps sole ownership of the chart timeframe and nothing prints twice.

**MTF-7 no signal.** Labels and the existing `f_cttLvl` lines only. It never feeds `cand*`, `f_sl`, `f_tp`, `f_score`, `f_grade`, a gate, the dedupe, a machine or an alert. No LONG / SHORT / entry / exit / TP / SL / RR.

**Reused, not duplicated:** `atrLen`, `crtRangeAtr`, `crtDispAtr`, `crtLife`, `tbsLen`, `tbsAgeMin`, `tbsConfMode`, `twsWaveWin`, `twsDeepen`, `raidMinAtr`, `raidDeepAtr`, `cttWin`, `cttShowRng`, `cttMaxRng`, `infoSize`, `LC_*`, `CP_*`, `NEAR_LVL_ATR`, `STRONG_CLOSE_PCT`, `COL_BULL/BEAR`, and `f_cttLvl` with its existing `3 × cttMaxRng` object budget.

---

## 3 · Untouched systems

Liquidity registry / pools, MODULE 8B marking, support/resistance, supply/demand, SMC, ICT, FVG, IFVG, order blocks, breaker/mitigation blocks, rejection blocks, CISD, MSS, BOS, CHoCH, OTE, dealing range, premium/discount, entry logic, the setup state machine, FEM, TP, SL, RR, risk, dedupe, score, grades, every hard gate, `request.security` calls that existed, sessions, killzones, Silver Bullet, volatility windows, the dashboard, the debug panel, all existing alerts, all existing plots, all existing inputs, and the entire v5.8-CTT chart-timeframe marker. Verified mechanically: `f_crtAdvance` / `f_tbsAdvance` / `f_twsAdvance` / `f_cttMark` / `f_cttTxt` / `f_cttLvl` / `type Ctt` / `cttCrtL…` all still present and unmodified.

---

## 4 · TradingView safety audit

| Check | Result |
|---|---|
| Non-repainting | every HTF read is `[1]`/`[2]` inside the request; no unfinished HTF candle is ever published |
| Lookahead | `barmerge.lookahead_off` on all four new calls |
| MTF purity | per-timeframe request string, per-timeframe bar counter, per-timeframe label tag; a TF at or below the chart is never requested and never drawn |
| Duplicates | per-TF `time` guard + `confirmed` gate → one structure, one mark, no tick redraw |
| Lifecycle / invalidation | `LC_IDLE → ARMED → SWEPT → RECL → CONF`, `LC_W1/W2` for TWS, `LC_INVAL` on a close beyond the swept extreme, on acceptance beyond wave 2, or on the per-TF clock |
| Objects | MTF labels FIFO-capped by `ctt_mMax` (default 30, min 6); CRT levels reuse the existing capped arrays; no new object class, no boxes |
| Arrays | fixed-size 4-slot arrays and one 24-slot UDT array built once; every index is `i`, `i*6+d`, `i*6+2+d`, `i*6+4+d` with `i ≤ 3`, `d ≤ 1` — in range by construction |
| Names | verified mechanically: no duplicate function, type or global; every new `ctt_*` / `f_ctt_*` / `CttM` / `m1…m4` use follows its declaration |
| Types | every int crossing the security boundary via `int(nz(…, 0))`; the `math.max` chain wrapped in `int()` |
| Global scope | 4 requests + 4 destructures + 16 `array.from` + one `if confirmed` loop; all machine logic inside functions; no function assigns a global scalar |
| Performance | 4 new `request.security` (13 → 17 total), 8 rolling built-ins per HTF context, and one 4×2 loop that only does work on a bar where an HTF candle has just closed |

---

## 5 · TOKEN BUDGET — the honest number

Measured with the same tokenizer used for v5.9/v6.0, comments excluded:

| | raw tokens | ≈ compiled |
|---|---|---|
| file 14 | 43 855 | ~99 600 of the 100 256 cap (~650 headroom) |
| file 16 | 46 967 | **+7 060** |
| MODULE 11C alone | 2 824 | ~6 400 |

So file 16 is expected to exceed the cap by roughly **5 700 – 6 400 compiled tokens** and return **CE10117**. The loop architecture is already the cheapest correct shape (machines compiled once; nineteen existing inputs, constants and one existing draw function reused rather than re-declared) — there is no further ~6 000-token saving available inside CRT / TBS / TWS scope. Measured in-scope and out-of-scope levers, so the trade is yours to pick:

| Lever | raw | ≈ compiled | In CRT/TBS/TWS scope? |
|---|---|---|---|
| MTF-CUT-1 · MTF CRT HIGH/EQ/LOW levels | ~90 | ~200 | yes |
| MTF-CUT-2 · MTF TWS mark (`f_ctt_tws2`) | ~230 | ~520 | yes |
| MTF-CUT-3 · drop the 4H context | ~120 | ~270 | yes |
| MTF-CUT-4 · delete the v5.8-CTT chart-TF marker | 704 | ~1 600 | yes |
| delete MODULE 19 debug panel (default OFF) | 1 618 | ~3 675 | **no — needs your OK** |
| delete MODULE 18 dashboard | 2 679 | ~6 080 | **no — needs your OK** |
| delete MODULE 8B liquidity marking | 1 740 | ~3 950 | **no — needs your OK** |

All four in-scope cuts together free ~2 600 compiled — not enough. The smallest combination that actually fits is **MTF-CUT-4 + the debug panel** (~5 275) or **MTF-CUT-4 + MODULE 8B** (~5 550), plus MTF-CUT-1/2/3 for margin.

Zero-loss alternative, already built and requiring no deletion at all: **`15.crt-tbs-tws-mtf-layer-v1.pine`** — the same layer as a standalone overlay on the same chart, with file 14 kept whole.
