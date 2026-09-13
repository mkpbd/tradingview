# AUDIT v5.9 — UI READABILITY (V5.9-UI)

Deliverable: **`13.liquidty+supply-v5.9-ui.pine`** = `11.liquidty+supply-v5.8-ctt.pine` with the on-chart text made legible. **File 11 is byte-for-byte untouched** (318 654 bytes, timestamp unchanged).

Pine version: `//@version=6` (unchanged). Compile: **NOT VERIFIED** — Pine cannot be compiled locally.

Verification of scope, run mechanically:

| Check | Result |
|---|---|
| Non-comment line count, 11 vs 13 | **3799 = 3799** — no code line added or removed, every edit in place |
| Lines added | +61, **all of them comments** (the v5.9 header block) |
| Code diff surface | every changed line is inside a `label.new` / `box.new` / `f_chip` argument list, one of two text-building expressions, or one input default |
| Source tokens (comments stripped) | 22 689 → **22 663 (−26)** — token-negative, so the v5.8 headroom is preserved |
| Declaration order | `mkSize` declared L1027, first use L1435 · `infoSize` declared L1035, first use L1511 — all uses follow their declaration |
| Dead variables | `mkTrans` lost 4 of 5 uses but is still live at L2573 |

---

## 1. The defect

The chart annotations were unreadable. Three independent causes, all in the drawing layer.

**UI-1 · text hard-coded to `size.tiny` in 20 places.** `uiInfoSize` and `uiMicroBig` already existed and controlled almost nothing: every box caption (S/D zones, breaker / mitigation, rejection blocks, HTF POI, the locked FVG, the premium / discount halves) and every level label (00:00 and 08:30 opens, session H/L, CRT HIGH / EQ / LOW) ignored both inputs and printed at `size.tiny`.

**UI-2 · low-contrast text.** The worst case was `CRT HIGH / CRT EQ / CRT LOW`: the label was created with `color.new(col, 100)` — a fully **transparent** pill — plus coloured text, i.e. red or green letters sitting directly on the candles. Nine further sites were merely dim.

**UI-3 · three label columns stacked at one x.** The liquidity-marking labels, the target BSL/SSL labels, the NEXT BUY/SELL labels and the OTE label all anchored at `bar_index + TRADE_BARS`, so wherever two of them shared a price the text overlapped and neither was readable. This is the collision visible in the report screenshot at 4403.725 (`target BSL EXT-H RESTING` over `NEXT SELL T2 4401.520-4403.725`).

**UI-4 · text longer than it needed to be**, which is the other half of an overlap problem.

---

## 2. What changed

### 2.1 Sizes
| Site | Before | After |
|---|---|---|
| iCHoCH / ibos chips, run chip, `CRT SWP` chip | `size.tiny` | `mkSize` (follows **uiMicroBig**) |
| 00:00 / 08:30 open labels, session H/L labels, CRT HIGH/EQ/LOW labels | `size.tiny` | `infoSize` (follows **uiInfoSize**) |
| zone / breaker / mitigation / rejection captions, HTF POI caption, locked-FVG caption, premium & discount captions | `size.tiny` | `size.small` (const) |
| `plotchar` glyphs ◆ ◈ ▵ ▿ ⇡ ⇣ ◇ | `size.tiny` | **unchanged** |
| developing-setup `⋯` preview | `size.tiny` | **unchanged** (deliberately dim) |

Box captions get a **const** `size.small` rather than a variable on purpose: `box.new`'s `text_size` qualifier is not documented as `series`, and a variable there is a compile risk not worth taking for one step of size. `plotchar`'s `size` argument is const-only, so it could not take a variable at all. Labels are safe — file 11 already passes `infoSize` to `label.new`.

**Practical consequence:** the two existing display inputs now actually reach the chart. Raise **⑱ Dashboard / UI → "Info label size"** from Small to Normal or Large for bigger level labels; **"Readable micro-marks"** governs the chips.

### 2.2 Contrast
CRT HIGH/EQ/LOW pill `100 → 20` transparency with white text (was coloured text on a transparent pill) · `crt sweep` chip `72 → 40` · iCHoCH / ibos `60 → 35` · run chip `70 → 45` and its text `white@20 → white` · session and opening-price labels `80 / 85 → 45` with solid white text · zone caption text `35 → 0` · breaker and mitigation captions `35 → 0` · HTF POI caption `30 → 0` · locked-FVG caption `20 → 0` · order-flow captions `35 / 65 → 10 / 45`.

### 2.3 Four label columns
| Column | x | Contents |
|---|---|---|
| 1 | `+TRADE_BARS` | entry / SL / TP ladder, NEXT BUY / SELL |
| 2 | `+2 × TRADE_BARS` | liquidity marking layer (BSL / SSL rows) |
| 3 | `+3 × TRADE_BARS` | target BSL / SSL, OTE label |

Only the OTE **label** moved; its box still ends at `rx2`.

### 2.4 Shorter text (no information lost — the tooltips are unchanged)
`MEDIUM / HIGH / VERY HIGH` → `★ / ★★ / ★★★` · `·loc✗` → `✗` · pool lifecycle `DETECTED / RESTING / APPROACHED / SWEPT ✓ REVERSED / ARCHIVED` → `NEW / REST / NEAR / SWEPT✓REV / OLD` (`SWEPT`, `BROKEN` unchanged) · `◎ locked FVG · await retest` → `◎ FVG · retest` · `HTF 60 FVG · demand POI` → `HTF 60 demand POI` · `DISCOUNT · buy flow` → `DISCOUNT` · `OTE 62–79% (buy)` → `OTE buy` · `crt sweep` → `CRT SWP`.

### 2.5 One default
`cttMaxRng` **6 → 3**. Six frozen CRT ranges is eighteen lines plus eighteen labels on one chart. Range is still 1-20; nothing else changed its default and **no input was added or removed**.

---

## 3. What was deliberately NOT changed

Detection and decision-making are untouched: the liquidity registry and its lifecycle, SMC / ICT, the CRT / TBS / TWS state machines and the CTT confluence mask, FVG / IFVG, order block / breaker / mitigation, CISD, MSS / BOS / CHoCH, the setup state machine, the trade engine, TP / SL, risk, dedupe, the score, the grades, every hard gate, the MTF `request.security` calls, sessions, the dashboard, the debug panel, every alert, and every input **semantic**. The five-system layer of files 10 and 12 was also not touched.

`UNRELATED EXISTING ISSUE — NOT MODIFIED`: none newly found this pass.

---

## 4. Safety audit

| Check | Result |
|---|---|
| Syntax / parser | 28 replacements, each matched a verbatim expected string an expected number of times; a mismatch would have aborted the write. Indentation and continuation lines preserved verbatim. |
| Type qualifiers | `label.new(size=)` takes `infoSize` — precedent already in file 11 (L2573, L5018). `f_chip`'s `sz` takes `mkSize` — precedent at L1196. `box.new(text_size=)` kept const. `plotchar(size=)` untouched (const-only). |
| Scope / declaration order | verified mechanically, see the table at the top. |
| Runtime | no loop, array, index or `na` path touched. |
| Repainting / lookahead | no state, no `confirmed` guard, no `request.security` touched. Drawing-only edits cannot repaint what they draw. |
| Object limits | **unchanged for every object type except CRT ranges, which fall from 18 lines + 18 labels to 9 + 9** — a net saving against the 500-object caps. |
| Token budget | −26 source tokens, so compiled tokens fall by roughly 70-100 from v5.8's ≈ 99 600. The `CTT-CUT-1` / `CTT-CUT-2` levers documented in v5.8 remain available and unmoved. |
| Performance | identical work per bar; two fewer string concatenations in `f_cttMark`. |

**Compile verification remains outstanding** — first paste into the Pine Editor will confirm.
