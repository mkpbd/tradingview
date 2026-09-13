# AUDIT v5.8 — CRT + TBS + TWS FORENSIC MARKING (V5.8-CTT)

Deliverable: **`11.liquidty+supply-v5.8-ctt.pine`** = `9.liquidty+supply-v5.7-ict.pine` + CRT / TBS / TWS marking only. File 9 is untouched.

Pine version: `//@version=6` (unchanged). Compile: first paste returned **CE10117 (101 135 / 100 256)**; MODULE 16B was then removed per the cut order (§6). Second paste not yet confirmed.

---

## 1. Existing CRT / TBS / TWS in v5.7 — what was already there

All three engines already exist as **state machines** (V5.5-E1/E2/E3), sharing one lifecycle vocabulary `LC_IDLE → LC_ARMED → LC_SWEPT → LC_RECL → LC_CONF | LC_INVAL` (`LC_W1 / LC_W2` for TWS) and one penetration grade `CP_TINY / CP_MEAN / CP_DEEP` off `raidMinAtr / raidDeepAtr`.

| Engine | Where | Reference | Sweep | Reclaim | Confirmation | Invalidation | Marking in v5.7 |
|---|---|---|---|---|---|---|---|
| **CRT** `Crt` / `f_crtAdvance` | after MODULE 11 location filter | previous **CLOSED** candle with range ≥ `crtRangeAtr`·ATR; hi / lo / mid stored at arming | later candle takes the extreme and closes back **inside**; penetration graded | a **later** close through the range **mid** | a **later** displacement candle (body ≥ `crtDispAtr`·ATR, strong close, right side of mid) | close beyond the swept extreme (sweep became a break), or `crtLife` bars | chips `crt sweep <tiny/real/deep>` and `CRT <tiny/real/deep> [·loc✗]` |
| **TBS** (turtle soup) `Tbs` / `f_tbsAdvance` | same section | `tbsLen`-bar extreme, ≥ `tbsAgeMin` bars old; re-anchors while nothing taken, **frozen after the sweep** | trade through, close back on origin side; graded | later close beyond the level by `NEAR_LVL_ATR`·ATR | `tbsConfMode`: reclaim only · reclaim + displacement (default) · reclaim + CISD | close beyond the swept extreme, or `crtLife` bars | chip `tsoup <tiny/real/deep> [·loc✗]` |
| **TWS** `Tws` / `f_twsAdvance` | MODULE 11B | wave 1 = touch of the `twsWaveWin`-bar extreme | wave 2 = **deeper** by ≥ `twsDeepen`·ATR **and** closes back beyond wave 1 (rejected) | — | wave 3 = close beyond wave 1 **plus** displacement or MSS | wave late by `twsWaveWin` bars, or acceptance beyond wave 2 | **none on chart** — only `f_evTag(…, "TWS")` (event list) and an alertcondition |
| HTF CRT / TBS | `f_crtTbsHtf` via `request.security` (`[1]`, one HTF bar delay) | — | — | — | — | — | producers only; untouched |

Also present and reused: `locLong / locShort` location filter (`crtNeedLoc`), `sigCooldown`, `f_chip`, `f_cpTxt`, `f_evTag` descriptors, `COL_BULL / COL_BEAR`.

Duplicate CRT/TBS/TWS logic: none. The HTF producer is a separate, intentionally lighter pattern (one HTF bar) and is not a duplicate of the LTF machines.

## 2. CRT / TBS / TWS-specific problems found

| # | Problem | Severity |
|---|---|---|
| CTT-1 | **TWS confirmed but never drawn.** `twsConfL/S` only fed the event list and an alert. A user with `useTws = ON` saw nothing. | marking gap |
| CTT-2 | **A one-tick poke printed as a pattern.** `CP_TINY` lifecycles reached `LC_CONF` (by design, as descriptors) and the chips printed `CRT tiny` / `tsoup tiny` / `crt sweep tiny` on the chart. Brief §6 / §8: a tiny wick violation must not become CRT / TBS. | false marking |
| CTT-3 | **Vocabulary.** `CRT real`, `tsoup deep` instead of `CRT BULL / CRT BEAR`, `TBS BUY / TBS SELL`. No quality tag. | marking |
| CTT-4 | **No confluence, stacked chips.** CRT and TBS confirm on the same displacement candle often (both need the same displacement); v5.7 stacked two chips on the same bar and never named the confluence. | duplicates / marking |
| CTT-5 | **CRT reference range never drawn.** hi / mid / lo were stored in the UDT but no `CRT HIGH / EQ / LOW` ever reached the chart. | marking gap |

Detection logic itself (the three `f_*Advance` machines) audited and found sound: closed-bar arming, strict chronology (`bar_index > sweepBar / reclBar / w1Bar / w2Bar`), break-invalidation, lifecycle timeout, frozen reference after the sweep, `confirmed`-only evaluation. **No detection line was changed.**

## 3. Detection methodology (as it now stands — unchanged engines, new marking gate)

**CRT BULL** — reference candle closed with range ≥ 1.2·ATR → a later candle wicks below the range low and closes back inside (penetration ≥ `raidMinAtr`·ATR = **CP_MEAN or deeper**) → a later close back above the range **EQ** → a later bullish displacement candle closing above EQ. Marked on that displacement candle. **CRT BEAR** mirrors it on the high side.

**TBS BUY** — a ≥ `tbsAgeMin`-bar-old `tbsLen`-bar low is traded through and the candle closes back above it (penetration CP_MEAN+) → a later decisive close above the level (+`NEAR_LVL_ATR`·ATR) → confirmation per `tbsConfMode` (default: displacement). **TBS SELL** mirrors it. Invalidated by a close beyond the swept extreme (= genuine breakout) or by the `crtLife` clock.

**TWS BUY** — wave 1 touches the rolling low; wave 2 goes ≥ `twsDeepen`·ATR deeper **and is rejected** (closes back above wave 1); wave 3 closes above wave 1 **with** displacement or MSS. Acceptance below wave 2 = trend, sequence invalidated. **TWS SELL** mirrors it. TWS has no penetration class; its depth gate is `twsDeepen`.

**Marking gate (new):** a lifecycle is drawn only when it reached `LC_CONF` **and** (for CRT / TBS) its penetration class is `CP_MEAN` or `CP_DEEP`. `CP_TINY` confirmations remain event descriptors (`f_evTag`) and remain visible in the event list / dashboard, but never on the chart.

**Confluence (new):** per side, mask `1 = CRT · 2 = TBS · 4 = TWS`. Engines confirming within `cttWin` bars (default 4) of the side's last mark **update that label** to `CRT + TBS` / `CRT + TWS` / `TBS + TWS` / `CRT + TBS + TWS`. Each component must have independently reached `LC_CONF`; nothing is inferred from proximity alone.

**Quality (new, label suffix):** `VERY HIGH` = all three · `HIGH` = two engines, or a `CP_DEEP` raid · `MEDIUM` = one engine on a real raid · LOW (tiny) is not drawn. `·loc✗` is appended when the location filter would block the trade (kept from v5.7 — the mark is information, the trade gate is separate).

**CRT range (new):** on a CRT confirmation, three lines from the stored `armBar` to the confirmation bar at `hi / mid / lo`, tagged `CRT HIGH / CRT EQ / CRT LOW`. Values are the ones frozen at arming, so the lines never move.

## 4. Changes made (file 11 vs file 9) — CRT / TBS / TWS only

| Where | Change |
|---|---|
| `indicator()` title strings | `v5.7 CTE` → `v5.8 CTT` (lineage convention) |
| header comment block | v5.8 note (comments only, zero tokens) |
| MODULE 16B (v5.7 inline ICT) | **REMOVED** after CE10117 — inputs `ictOn` / `ictJWin`, `type IctM`, `f_ict`, `ictDone`. Not CRT/TBS/TWS code, but it was the header-documented budget lever; ICT marking continues in file 10. |
| inputs, group ⑩ | + `cttWin` (int 4), `cttShowRng` (bool), `cttMaxRng` (int 6) |
| lifecycle chip block (was file 9 l.3283-3294) | `crt sweep` chip now requires `CP_MEAN+`; the `CRT …` and `tsoup …` confirmation chips **removed** (replaced by the marker below) |
| after `twsConfL/S` (MODULE 11B) | + `type Ctt`, `f_cttTxt`, `f_cttMark`, `f_cttLvl`, two `Ctt` instances, two arrays, one `if confirmed` driver — the whole marker, fenced `CTT-CUT-2 begins … ends`; range drawing fenced `CTT-CUT-1` |

Diff: 12 lines removed (title + the 3 chip blocks), ~130 lines added (≈ 70 code, rest comments). Removed lines verified with `diff` — nothing else was deleted.

## 5. Complete updated Pine script

`11.liquidty+supply-v5.8-ctt.pine` (5 436 lines). Paste the whole file into the Pine Editor.

## 6. TradingView error-safety report

| Check | Result |
|---|---|
| Token / CE10117 | **Measured on TradingView: 101 135 / 100 256 (879 over) with MODULE 16B present.** Cut step 1 applied: MODULE 16B (inline ICT, ICT-CUT-1/2/3, 586 source ≈ 1 594 compiled tokens) removed from file 11 — the full ICT layer runs standalone as file 10. Expected now ≈ 99 550, ~700 under the cap. **Recompile required.** If it still fails: CTT-CUT-1 (range lines, ~550) → CTT-CUT-2 (whole marker). |
| CE10295 main body | + 8 global statements (2 `var`, 4 bools, 2 arrays, 1 `if`). v5.6 was already at this cap's edge; same cut order applies. |
| Syntax | Multiline ternary continuation uses the same 9-space indent as `f_kindPri`. No tabs (checked). No tuple destructuring in `if`/`for`. Functions end with an expression (`s.m`, `array.size(cttLns)`). |
| Name collisions | `ctt*`, `Ctt`, `f_ctt*` unused anywhere in v5.7 (grepped). New block-locals `rx rh rm rl rc two q tx tr bg join deep loc` have no global declaration (grepped). |
| Types | `Ctt` fields `int / int / label`; `f_cttMark` returns `int`; `f_cttLvl` returns `int`; `f_cttTxt` returns `string`; all ternary branches same type. |
| Arrays | Own arrays, pushed 3 per CRT, trimmed 3 per overflow (`for 0 to 2` after a `size > 3·cttMaxRng` check) — never shifts an empty array. Mutating a global array inside a function follows the existing `f_poolPush` / `f_qPush` precedent. |
| Objects | Labels: ≤ 1 new chip per side per confirmation (updated in place inside the window) + 3 tiny range tags per CRT, capped `3 × cttMaxRng` (18 by default). Lines: capped `3 × cttMaxRng`. Chips use the same 500-label GC every existing chip uses. |
| `na` | `armBar / hi / mid / lo` are always set before `LC_CONF` (the lifecycle cannot reach CONF without arming). `s.bar / s.lb` na-guarded before use. |
| MTF | No new `request.security`. |
| Runtime | No division, no indexing, no `[n]` offsets in new code. |

## 7. Non-repainting report

- Every read is confirmed-bar state: `crtConfL/S`, `tbsConfL/S`, `twsConfL/S` are set only inside `if confirmed` by machines that advance one stage per closed bar with `bar_index >` chronology guards.
- Every write (`f_cttMark`, `f_cttLvl`) is inside `if confirmed` — nothing is drawn on a forming bar, nothing changes when the realtime bar closes.
- Range lines use `armBar / hi / mid / lo` that were stored when the reference candle closed — knowable at the time, frozen since.
- Label **updates** (confluence) only ever change the text / colour of a label created on an earlier confirmed bar; the bar it sits on never moves.
- No lookahead, no future bar, no `request.security`. Bar Replay reproduces the same marks because every input is closed-bar state.

## 8. Non-CRT/TBS/TWS protection report

> **NO NON-CRT/TBS/TWS LOGIC WAS MODIFIED.**

`diff` between file 9 and file 11 removes exactly 12 lines: the `indicator()` title line and the three lifecycle-chip blocks (file 9 l.3283-3294). `f_crtAdvance`, `f_tbsAdvance`, `f_twsAdvance`, `crtCand*`, `tbsCand*`, `crtSl*`, `tbsSl*`, `hCand*`, `f_evTag`, `f_score`, `f_sl`, every alertcondition, the dashboard, MODULE 16B and everything else are byte-identical.

## 9. Unrelated issues (observed, not modified)

- `UNRELATED EXISTING ISSUE — NOT MODIFIED`: the `crt sweep` chip and the HTF `f_crtTbsHtf` producer both choose the label side from the **long** flag (`crtSwpL`), so on an outside bar that sweeps both sides of the same reference candle the bearish chip would print below the bar. Pre-existing v5.5 behaviour; cosmetic; left as is.
- `UNRELATED EXISTING ISSUE — NOT MODIFIED`: `tbsConfMode = "Close back inside"` confirms on `close > close[1]` (any up-close), which is weaker than the tooltip's "reclaim only" wording suggests. User-selected, non-default mode; left as is.
- File 9's own compile status is still unverified (see memory / AUDIT-v5.7-ICT.md §10). If file 9 already fails CE10117, file 11 will too until MODULE 16B is cut.
