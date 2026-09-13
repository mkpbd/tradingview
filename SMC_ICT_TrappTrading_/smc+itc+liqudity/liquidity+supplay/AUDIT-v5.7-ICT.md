# AUDIT v5.7 — ICT-ONLY FORENSIC DETECTION & MARKING LAYER

Deliverable: **`10.ict-forensic-layer-v1.pine`** — a standalone ICT detection & marking overlay, run as a second indicator alongside the untouched `8.liquidty+supply-v5.6-liquidity.pine`.

It shipped separately because v5.6 has ~1,750 compiled tokens of headroom and the ICT layer costs ~16,200. See §10 for the measurements. `9.liquidty+supply-v5.7-ict.pine` is the inline attempt and does **not** compile.

---

## 1. Existing ICT implementation (v5.6) — what was already there

| ICT concept | Where | Verdict |
|---|---|---|
| Swing high / low | MODULE 4 `ta.pivothigh/low` (internal `pivLen`, external `extPiv`), confirmed pivots | Correct, non-repainting. Reused. |
| BOS / CHoCH (external + internal) | MODULE 4 `f_structUpdate`, chips `BOS` / `CHoCH` / `ibos` / `iCHoCH` | Correct. Reused as the raw shift feed. |
| MSS | `mssUp = chochUp or cisdUp` — trade machine only | Never printed as "MSS"; not conditioned on a prior raid. |
| CISD, IFC | MODULE 3 | Present, labelled. Untouched. |
| Displacement | `dispUpBar/dispDnBar` (body ≥ `dispFactor`·ATR, outer-third close) | Correct definition, never marked. |
| Liquidity (BSL/SSL, EQH/EQL, EXT, session H/L, PDH/PDL, PWH/PWL) | MODULE 7 registry + MODULE 8B marking | Complete, graded, lifecycle-tracked. Reused. |
| Liquidity raid / sweep / run / break | `f_poolScan` (raid vs break), run engine MODULE 11B | Correct. Only glyphs ◆◈◇▵▿ on chart, no text. |
| FVG | MODULE 9 zones: `bullFVG and body[1] ≥ dispFactor·ATR` | Displacement-filtered, lifecycle fresh/50%/filled, BUT labelled DEMAND/SUPPLY, height clamped to `maxZoneAtr`, no min height, `fvgFillDead` retires it. |
| IFVG | — | Absent as a concept. Flipped zones are named BREAKER/MITIGATION (FVG-based, ICT-imprecise naming). |
| Order block | — | Absent. "Rejection blocks" (swing-wick POIs) are a different thing. |
| Breaker / Mitigation | MODULE 9 zone flip | FVG-zone based, causal chain. Untouched. |
| BPR | — | Absent. |
| Dealing range / Premium / Discount / EQ | MODULE 8 | Correct (external swings). Reused. |
| OTE | MODULE 8 62–79 % of the structural range, drawn on last bar | Present; not tied to a liquidity event. Kept. |
| Sessions / KZ / SB / opens | MODULE 5 | Present. Reused. |
| PDH/PDL/PWH/PWL | MODULE 6 (`[1]` inside `request.security`, lookahead_on) → registry pools | Correct, non-repainting. Reused. |
| HTF FVG POI, HTF bias | MODULE 6 | Present. Read for the PD-array view / context only. |
| Judas swing, AMD / PO3 | — | Absent. |
| Confluence score | `f_score` (trade alignment) | Trade-only. Not an ICT classifier. Untouched. |

## 2. ICT-specific problems discovered

- I1 No "MSS" on chart; every CHoCH/BOS printed identically whether or not liquidity was taken first.
- I2 No named raid label; raid quality (A/B/C) existed in the registry but was invisible.
- I3 FVG boxes said DEMAND/SUPPLY; geometry clamped; no min height; no explicit FRESH/PARTIAL/FILLED/INV text.
- I4 No IFVG. A failed FVG became "BREAKER" (an OB term in ICT) or "MITIGATION".
- I5 No order block detection (institutional origin of displacement).
- I6 No BPR.
- I7 OTE only from the structural range, never from the raid→displacement leg.
- I8 No displacement mark, Judas, AMD, PD-array-at-price view, or ICT confluence class.

## 3. ICT detection architecture (MODULE 16B)

- **Narrative tracker** per side (`Narr`): `RAID → MSS → DISPLACEMENT → FVG → retrace into PD array/OTE`. Independent of the trade machine (which carries HTF/target/POI trade gates that must not filter chart marks). Display-only.
- **One object type** (`Ict`) for FVG · IFVG · OB · BREAKER · BPR · OTE, one array, one lifecycle loop: `CONF → PART → FULL → INV → ARCH`; FVG/OB may leave INV by **inversion** (→ IFVG / BREAKER) after a meaningful failure and a confirming retest.
- **Raid qualification**: registry raid this bar, grade ≥ B (Strict/Normal) on a non-minor pool (EQ/EXT/session/PD/PW; Normal also allows swing pools price has already respected).
- **Confluence** (`f_ictConf`): LOW / MEDIUM / HIGH / VERY HIGH from the narrative's own stages only.
- **Rendering**: event chips at the event bar (raid, displacement, PD-array retrace, Judas, AMD), MSS as level line + label, PD arrays as box + label updated in place, last-bar-only: PDH/PDL/PWH/PWL state tags, PD-array-at-price label, box extension.

## 4. Exact changes

No line of `8.liquidty+supply-v5.6-liquidity.pine` was touched. The ICT layer is a new file of ~1,480 lines:

| module | contents |
|---|---|
| 1-2 | ICT-only inputs (6 groups), constants, helpers |
| 3-4 | candle anatomy + displacement; the two-scale structure engine (BOS / CHoCH, protected swings, liquidity runs) |
| 5-6 | sessions; HTF bias + HTF FVG POI + PDH/PDL + PWH/PWL (3 `request.security` calls, all `[1]` + `lookahead_on`) |
| 7 | the liquidity pool registry with raid/break separation, A/B/C grading and a full lifecycle |
| 8 | dealing range, premium / discount / equilibrium, structural OTE |
| 9 | ICT object + narrative types and their vocabulary |
| 10 | the per-bar ICT pass: raids, MSS, displacement, OTE, FVG, BPR, order block, PD-array retrace, Judas, AMD |
| 11 | last-bar render: BSL/SSL level tags, PD arrays at price, both stories, range boxes |
| 12 | 12 observation alerts — no entry alerts, because there are no entries |

## 5. Confirmation: ICT only

`8.liquidty+supply-v5.6-liquidity.pine` is byte-identical to how it started — it was never opened for writing. The two scripts share no state: TradingView runs them as separate indicators. The ICT layer emits no LONG, no SHORT, no entry, no stop and no target, and none of its alerts is a trade instruction.

## 6. UNRELATED EXISTING ISSUES — NOT MODIFIED

- `fvgMinAtr` is applied only to the machine's execution FVG, not to MODULE 9 zone creation (tooltip says so; still, tiny zones can be drawn).
- MODULE 9 zone geometry clamps the FVG to `maxZoneAtr`; the drawn "FVG" zone is not the true gap for large displacements.
- Flipped FVG zones are labelled "BREAKER" — in ICT vocabulary a breaker is order-block based; this is closer to an IFVG.
- `newDay = ta.change(time("D"))` follows the exchange session boundary (17:00 NY on many FX feeds), so PDH/PDL register at the exchange day roll, not at 00:00 NY.
- `sesStoryL/S` and the AMD Asia test rely on pool `tag` strings; `f_poolPush` can re-tag an upgraded pool (e.g. "Asia H" → "EQH"), which silently drops the session story for that pool.
- `f_lqCluster` / MODULE 8B render on every tick of the last bar (documented as intended, but heavy with many pools).
- Pine auto-deletes the oldest drawings beyond `max_*_count = 500`; the registry keeps `line` handles and calls `line.set_*` on them without checking deletion (pre-existing exposure, now marginally more likely with more labels).

## 7. Concepts detected (rules)

- **BSL/SSL RAID / SWEEP** — registry pool moves to `PS_RAID` this bar; `RQ_A` → "RAID", `RQ_B` → "SWEEP"; `RQ_C` prints nothing (Loose sensitivity allows it). Breaks (close beyond) never print as sweeps.
- **MSS ↑/↓** — a BOS/CHoCH (internal or external, displacement already required by MODULE 4) strictly after the raid, within `ictSeqWin`, breaking a level formed inside the window and ≥ `MSS_MIN_SEP_ATR` from the raid extreme. One per raid.
- **DISPLACEMENT** — `dispUpBar` with body ≥ `ictDispAtr`·ATR and (structure break this bar, or raid in window, or previous bar also displacement). One per 3 bars per side.
- **ICT FVG** — `low > high[2]` with `dispUpBar[1]`, height ≥ `ictFvgMin`·ATR, and (default) context: raid in 2×window, recent MSS, or structure break on one of the three candles. True gap geometry.
- **FVG lifecycle** — FRESH → PARTIAL (wick inside) → FILLED (wick reaches far edge) → INV (close beyond far edge) → ARCH.
- **IFVG** — INV FVG whose failure was meaningful (displacement candle, or a second close beyond), then a retest from the other side that touches the gap and closes on its far half. Confirmed → `IFVG` with opposite direction; then normal lifecycle; a second failure archives it.
- **OB** — last opposing candle within 5 bars before a displacement candle that (broke structure, or came within `ictSeqWin` of a raid, or created an ICT FVG); block ≤ 2 ATR tall, price has left it, impulse ≥ 1 ATR. ★ when born from a raid.
- **BREAKER** — OB failed meaningfully, then retested from the other side and held.
- **BPR** — new ICT FVG overlapping an opposing ICT FVG (≤ 2×window old) that it traded through; overlap ≥ `ictFvgMin`·ATR; the consumed FVG is archived.
- **ICT OTE** — after displacement: 62–79 % of raid-extreme → leg-extreme; expands with new leg extremes until first tap; TAPPED; DONE when the leg extreme is retaken; INV when the raid extreme is closed through. One per story.
- **PD ARRAY retrace** — after displacement, price trades into a same-side ICT array or the range OTE → last narrative stage.
- **Judas** — session open (London / NY): qualified raid on one side within `ictJudasWin` bars above/below the open, then displacement + MSS closing back through the open within 3× the window. Acceptance beyond the raid extreme = failed (expansion).
- **AMD / PO3** — Asia frozen range; qualified raid of "Asia H"/"Asia L"; then displacement + MSS closing through the opposite Asia extreme. Acceptance beyond the manipulation extreme = failed. Resets at each Asia close.
- **PDH/PDL/PWH/PWL tags** — UNTOUCHED · SWEPT (grade B/C) · RAIDED (A) · RAIDED ✓ REVERSED · BROKEN · EXPIRED, from the pool's own state. Skipped when the ④b layer already labelled that level.
- **Confluence** — LOW: one item · MEDIUM: two · HIGH: raid+MSS+disp+(FVG or PDA) · VERY HIGH: all five.

## 8. Repaint behaviour

- Every mutation is inside `confirmed`. Pivots are the existing confirmed pivots. HTF data is the existing closed-bar feed; **no new `request.security`**.
- OB box is drawn back to its origin candle but created on the displacement close; FVG on candle 3's close; MSS on the break candle. Nothing is back-dated after creation; state changes update text/colour in place.
- Realtime: objects are created once; last-bar renders (level tags, PD-array label, box extension) are rebuilt per tick inside bounded arrays.

## 9. Object lifecycle & limits

- `ictObjs` capped at `ictMaxObj` (oldest evicted, drawings deleted); age cap `ictLife`; INV non-flippable objects archived after 3 bars; inversion candidates after 2×window without retest; OTE DONE after 20 bars.
- MSS lines capped at 30. Event chips rely on Pine's 500-label GC (same as every existing chip).

## 10. THE COMPILE FINDING — why this shipped as a companion script

Two TradingView limits were hit, in order.

**CE10295 "main body of the script is too long"** — the GLOBAL-SCOPE size cap. Fixed structurally: the ICT per-bar pass became `f_ictBar()`, the last-bar pass `f_ictLast()`, and every mutable ICT scalar moved into an `IctMem` object because a Pine function may mutate a UDT field but never assign a global.

**CE10117 "compiled code contains too many tokens: 114709, the limit is 100256"** — this one is not fixable by restructuring. Measured:

| | compiled tokens |
|---|---|
| v5.6 alone | ~98,500 |
| TradingView limit | 100,256 |
| **headroom in v5.6** | **~1,750** |
| ICT layer as built | ~16,200 |

The ICT layer is **nine times** the available headroom. Its type, constant and helper declarations alone cost ~4,500 — 2.5× the headroom before a single detection rule runs. The cheapest useful sub-block (liquidity raid labelling) is ~470, and it needs those declarations to exist. Per-block costs measured: PD-array lifecycle 1,935 · FVG+BPR 1,522 · MSS 1,462 · last-bar render 1,329 · displacement+OTE 1,047 · PD-array retrace 726 · Judas 726 · order block 622 · AMD 576 · raid labels 468 · narrative expiry 239.

Trimming cannot close a 9× gap, and cutting non-ICT features to make room is forbidden by the brief. So the ICT layer ships as **`10.ict-forensic-layer-v1.pine`**, a second indicator on the same chart. It carries its own copies of the primitives it needs (structure engine, pool registry, sessions, dealing range, HTF context) and measures **~34,100 of the 100,256 token budget** — roughly two-thirds spare for future ICT work.

This is also the strictest possible reading of the brief's absolute rule: v5.6 is not edited at all, so no existing signal, gate, grade, input, alert or drawing can have moved.

### File status

| file | state |
|---|---|
| `8.liquidty+supply-v5.6-liquidity.pine` | **unchanged**, still the trading system |
| `9.liquidty+supply-v5.7-ict.pine` | **DOES NOT COMPILE** (CE10117). Kept only as the reference for the inline attempt and the evidence behind the table above. Do not load it. |
| `10.ict-forensic-layer-v1.pine` | **the deliverable** — add as a second indicator on the same chart |

### Verification status

Static checks pass on file 10: no tuple destructuring inside a conditional block (Pine forbids it — this was a latent error in file 9 too, at the order-block scan); no `var` inside the wrapped functions; every `:=` target inside a function is a local or a UDT field; no write-only globals; continuation indentation consistent; 268 global-scope statements. **Not compiled by me** — Pine has no local compiler. Report any editor error with its exact text and line.

## Forensic test matrix (walk-through, not executed)

| Scenario | Expected marks |
|---|---|
| SSL raid → bull MSS → displacement → bull FVG → retrace into FVG/OTE | `SSL RAID · <tag>` chip → `MSS ↑ · MEDIUM/HIGH` at level → `DISPLACEMENT ↑` → `FVG ↑ · FRESH` → `OTE ↑ · PROJECTED` → `PD ARRAY ↑ · VERY HIGH`; FVG → PARTIAL; OTE → TAPPED |
| Bearish mirror | same with ↓ / BSL |
| Trending market (no raids) | FVGs with structure-break context only, OBs with `brokeUp/Dn`; no MSS/raid chips |
| Ranging market | EQ raids print; MSS only if a level breaks after the raid; congestion produces few FVGs (no displacement) |
| Wick-only poke (grade C) | nothing (Normal/Strict) |
| Fake breakout → reclaim | pool break → no sweep label; if later reclaim happens the existing trap engine marks it, ICT layer silent |
| Multiple overlapping FVGs | `f_ictDup` refuses same-side overlaps; opposing overlap → BPR |
| Session transitions | Judas watches London/NY open only; AMD resets at Asia close |
| MTF chart (H1+) | Judas/AMD off (intraday only), PW tags off on W+ |

## 11. 2026-09-09 (later session) — brief re-issued; static hardening pass on file 10

The same ICT-only brief was re-run against file 8. Nothing changed on the token side: v5.6 is still ~98,500 / 100,256 and at the CE10295 global-scope cap, so an inline `9.*-v5.7-ict.pine` still cannot compile and was **not** produced. File 10 remains the deliverable. Two ICT-only edits were made to it after a line-by-line static audit:

| # | where | change | why |
|---|---|---|---|
| H1 | `f_ictBar` · OTE leg-expansion block | inner `float w` → `float wOte` | `f_ictBar` later declares `float w` / `float w2` at function scope for the OTE projection; Pine can reject the inner block's `w` as a redeclaration once the outer one exists in the same function. Behaviour identical. |
| H2 | `f_ictBar` · `mssU` / `mssD` | `nz(mssBarU, -1) >= …` → `not na(mssBarU) and mssBarU >= …` (both sides) | the MSS line is drawn with `line.new(mssBarU, …)`; on early bars `mssBarU` can be `na`, and `nz(...)=-1` still passed the window test when `raidBar ≤ ictSeqWin`, letting an `na` x-coordinate reach `line.new` (runtime error). Now the shift is simply not an MSS until its level has a known bar. |

Mechanical scan (no findings): every reverse `for … to 0` is size-guarded; no tuple destructuring inside a local block; no continuation line indented to a multiple of 4 after an open operator. Still **not compiled** — Pine has no local compiler.
