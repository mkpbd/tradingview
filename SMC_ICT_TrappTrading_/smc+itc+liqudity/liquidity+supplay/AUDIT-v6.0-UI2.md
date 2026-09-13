# AUDIT v6.0 — CHIP COLLISION (V6.0-UI2)

Deliverable: **`14.liquidty+supply-v6.0-ui2.pine`** = `13.liquidty+supply-v5.9-ui.pine` with on-chart marks that can no longer land on top of each other. **File 13 is byte-for-byte untouched** (323 063 bytes, timestamp 2026-09-09 12:13:26).

Pine version: `//@version=6` (unchanged). Compile: **NOT VERIFIED** — Pine cannot be compiled locally.

---

## 1. The defect

v5.9 fixed size and contrast, so the text became big enough to read — and that made the real remaining problem obvious in the report screenshot: **two marks on the same candle print at the same point**.

Cause, one line: `f_chip` created every chip with

```pine
label.new(bar_index, na, txt, yloc = below ? yloc.belowbar : yloc.abovebar, …)
```

`yloc.abovebar` / `yloc.belowbar` is **one fixed y per bar per side**. Everything that marks a candle went through that anchor:

CISD · IFC · BOS / CHoCH · iCHoCH / ibos · run · BULL/BEAR TRAP · CRT SWP · the CTT confluence marker (`CRT + TWS ★★ ✗` etc.) — plus, through their own identical `label.new`, the **LONG / SHORT entry label** and the developing-setup `⋯` preview.

So any two of them firing on one bar, on one side, drew as a single unreadable smear. That is every red box in the screenshot except two: `PREMIUM` (its own cause, §2.3) and the pair of `DEMAND T3` box captions (§3).

---

## 2. What changed — 9 edits, nothing else

Each replacement matched a verbatim expected string an expected number of times; a single mismatch would have aborted the write without producing file 14.

### 2.1 Chip lanes (`f_chip`)

`f_chip` now positions on **price**, not on the bar anchor, and keeps a per-bar counter per side:

```pine
var int[] chipLn = array.new_int(3, -1)   // 0 = above count, 1 = below count, 2 = whose bar
f_chip(bool below, string txt, color bg, color tc, string sz) =>
    if array.get(chipLn, 2) != bar_index
        array.set(chipLn, 2, bar_index)
        array.set(chipLn, 0, 0)
        array.set(chipLn, 1, 0)
    int   k  = below ? 1 : 0
    int   n  = array.get(chipLn, k)
    array.set(chipLn, k, n + 1)
    float st = nz(atr, high - low) * (0.45 + n * uiChipGap)
    label.new(bar_index, below ? low - st : high + st, txt,
         style = below ? label.style_label_up : label.style_label_down,
         color = bg, textcolor = tc, size = sz)
```

The nth chip of a bar sits `ATR × (0.45 + n × uiChipGap)` away from the candle, so marks stack **outward in call order** instead of overlapping. Styles are unchanged, so a below chip still hangs below its anchor and an above chip still sits above it.

Two Pine constraints shaped this:

* A function may **mutate a global array** but may never assign a global scalar — hence `chipLn` is an `int[]`, not three `var int`s.
* `f_chip` now needs `atr`, which is declared in MODULE 3 at what is now L1167. So the definition **moved** from the rendering preamble (old L1041) to L1176, immediately after `atr`. Its first call site is L1257, well below. A comment marks the old location.

### 2.2 The entry label and the preview join the lanes

The `LONG` / `SHORT` label and the `⋯` preview had their own `label.new` with the same `yloc` anchor — the same collision, on the two marks that matter most. Both now call `f_chip` with identical colour, transparency and size. Because they are drawn last, they take the outermost lane. **This edit is token-negative.**

### 2.3 PREMIUM / DISCOUNT captions

Both were `text.align_left`, i.e. pinned at `fx1` = the left edge of the dealing range — the middle of the candles, exactly where the chips live. Both become `text.align_right`, which puts them at `fx2 = bar_index + TRADE_BARS`, in the projection space. Box geometry, colours and `valign` unchanged.

### 2.4 One new input

`⑱ Dashboard / UI → "Mark spacing (× ATR)"` — `uiChipGap`, default **0.9**, range 0.2–3.0, step 0.1. Raise it when the chart is zoomed out and stacked chips still touch; lower it on a tall chart. **No input was removed and no existing default changed.**

---

## 3. What was deliberately NOT changed

Detection and decision-making are untouched: the liquidity registry and its lifecycle, SMC / ICT, the CRT / TBS / TWS state machines and the CTT confluence mask, FVG / IFVG, order block / breaker / mitigation, CISD, MSS / BOS / CHoCH, the setup state machine, the trade engine, TP / SL, risk, dedupe, the score, the grades, every hard gate, the MTF `request.security` calls, sessions, the dashboard, the debug panel, every alert, and every other input semantic or default. Files 10 and 12 (the companion forensic layers) were not touched.

`plotchar` glyphs (◆ ◈ ▵ ▿ ⇡ ⇣ ◇ ▲ ▼) are **not** movable — `plotchar` has no y argument at all. Lane 0's `0.45 × ATR` base offset is what keeps a chip clear of them; it is not a guarantee at extreme zoom.

`UNRELATED EXISTING ISSUE — NOT MODIFIED`: **two box captions can still collide.** Zone captions are drawn by `box.new(text_halign = right, text_valign = top/bottom)` at the box's right edge. Where two zones of the same direction overlap in price, their captions can still touch — this is the second `DEMAND T3` in the screenshot. Fixing it needs per-caption y nudging, which `box` cannot express (a box caption is anchored to the box, not to a price), so it would mean replacing zone captions with labels — a real change to the drawing model and a token cost, not a display tweak. Not done in this pass.

---

## 4. Safety audit

| Check | Result |
|---|---|
| Code diff surface | 9 edits, all in `f_chip`, two entry `label.new`s, one preview `label.new`, two `box.new` `text_halign`s, the `indicator()` title, and one added input. Diff printed and reviewed line by line. |
| Non-comment line count | 3 538 → 3 543 (+5): the lane array and its bookkeeping, minus the lines refunded by routing three call sites through `f_chip` |
| Declaration order | `uiChipGap` L958 · `atr` L1167 · `chipLn` L1175 · `f_chip` L1176 · first `f_chip` call L1257 — every use follows its declaration |
| Global-scalar assignment inside a function | none — state is an array (`array.set`), which Pine permits |
| Continuation lines | indented 9 spaces (non-multiple of 4), as the rest of the file requires |
| `na` handling | `nz(atr, high - low)` covers the first `atrLen` bars, where `ta.atr` is `na`; without it the chip y would be `na` and the label invisible |
| Realtime creep | the counter is `var` state, which Pine rolls back before each intrabar recalculation, so repeated ticks on the live bar cannot push chips progressively further out |
| Repainting / lookahead | no state, no `confirmed` guard, no `request.security` touched. Positioning-only edits cannot repaint what they draw. |
| Object limits | unchanged — same number of labels and boxes, at different y |
| `label.set_*` compatibility | the CTT marker reuses its label via `label.set_text` / `label.set_color`, and the CRT range labels via the same; **no `label.set_y` / `set_yloc` / `get_y` exists anywhere in the file**, so moving from `yloc.abovebar` to `yloc.price` breaks no later mutation |
| Token budget | +101 raw source tokens by the local tokenizer, of which the 26-word tooltip string counts as one token to TradingView — real cost ≈ +50 source ≈ **+140 compiled** against v5.9's ~700 of headroom. The `CTT-CUT-1` / `CTT-CUT-2` levers remain available and unmoved. |
| Performance | identical work per bar plus three `array` accesses per chip drawn |

**Compile verification remains outstanding** — first paste into the Pine Editor will confirm.
