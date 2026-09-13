# LQ-SD-PA v3.1 — ICT Silver Bullet upgrade

`2.version-3.1-silverbullet.pine` — built from `1.version-3.txt` (untouched).

**Not compiled or backtested.** No Pine compiler exists outside TradingView, so
nothing here has been verified to compile and no accuracy figure is claimed.
Static checks that DID run: bracket balance, indentation (4k / 4k+1, and no
wrapped line on a 4-multiple indent), function defined-before-called, every new
identifier declared-before-used, tuple-destructure arity, UDT field count vs
`.new()` args, table cells inside their declared size, the output budget, and —
for the CE10295 refactor — no function assigning to a global, no forbidden
output call or `input.*` inside a function, no destructured variable later
reassigned with `:=`, and no orphaned reference to state that moved inside a
function.

---

## 1. Changelog

### V31-FIX-1 — a defect repair, not a feature (active even with SB disabled)

In v3, `recentSsl / recentBsl / sslInPlay / bslInPlay` were evaluated in
MODULE 5 **above** the PDH/PDL stamps and **above** MODULE 8's session-raid
stamps. The state machine arms on `sslInPlay and lastSslBar == bar_index`, so a
PD-level or session-level raid could never satisfy that test — **only swing and
EQH/EQL sweeps ever armed a setup.** Silver Bullet depends on exactly those
pools, so this had to be repaired first.

- The killzone / volatility-window flags moved out of MODULE 8 into the new
  **MODULE 4B**, so they exist before the liquidity engine.
- The per-session H/L tracker (`f_sesTrack` + the three calls + the ARCH-8
  stamping) moved out of MODULE 8 into **MODULE 5**.
- The four sweep-in-play lines now sit **after every stamp**. The expressions
  are byte-identical; only the evaluation point moved.
- MODULE 8 keeps the engineered-liquidity score memory and the 00:00 / 08:30
  opening lines, and is renamed accordingly.

Side effect worth knowing: MSS grading (MODULE 6) now also sees session and
PD-level raids, so `MSS` will label more often than it did in v3. That is the
intended behaviour — a PDL raid plus a displaced CHoCH *is* an MSS.

### SB-1 · MODULE 4B — session clock + Silver Bullet window engine

- Three doctrine windows, New York time, taken from the existing `sbSes*`
  session inputs so they stay tunable: **London 03:00–04:00 · NY AM 10:00–11:00
  (priority) · NY PM 14:00–15:00**, each with its own enable toggle.
- `f_sesMin()` parses `"HHMM-HHMM[:days]"` into a NY minute-of-day, giving
  minute-accurate **window remaining** (`sbRemMin`, `sbRemBar`).
- **Pre-window arming grace** (`sbPreMin`, default 15 min) — the doctrine
  sequence often *starts* on the approach. Entry is still gated to the window.
- Per-window **close edges** (`sbEndLOEvt / sbEndAMEvt / sbEndPMEvt`) — this is
  the exit clock MODULE 19 uses.
- Window id `sbWinNow` / `sbCtxWin`, `sbActive`, `sbCtx`, plus the per-window
  score weight and minimum sweep quality.
- SB window **range boxes**, capped at `sbBoxKeep`.

### SB-3 · sweep pool KIND memory

`lastSslKind` / `lastBslKind`: **1** swing pivot · **2** EQH/EQL pool ·
**3** PDH/PDL · **4** prior-session H/L. Kind ≥ 2 is *engineered* liquidity —
the pool an SB raid is supposed to be taking, and what `sbPoolPref` requires.
Inside an SB window an **Asia** session raid also counts as a pool (its classic
NY-AM role); outside the windows Asia keeps its v3 score-only role, so non-SB
behaviour is unchanged.

### SB-4 · a dedicated SB arming path on the MODULE 17 machine

Arming inside an SB context window, with **that window's own** minimum sweep
quality and a preferred pool, stamps a **window tag** (`sbTagL` / `sbTagS`) onto
the setup. The tag then drives everything else:

| | tagged SB setup | tag 0 (v3 path) |
|---|---|---|
| sweep → POI tap | `sbLiqWait` **12** | `liqWait` 20 |
| POI tap → shift | `sbPoiWait` **8** | `poiWait` 15 |
| shift → entry | `sbRetWait` **10** | `retWait` 20 |
| anchor | **must** be a locked, clean displacement FVG | FVG or POI zone |
| CHOP regime | may be waived (`sbChopBypass`) | suppressed unless quality 4 |
| window close | setup killed (`sbKillAtEnd`) | n/a |

- The arming test became `lastSslQual >= minArmQual **or** sbArmOkL`, so the SB
  gate can arm a setup the generic `minArmQual` would reject.
- **Clean FVG rule:** MODULE 12 now records whether the latest FVG was cut by a
  displacement leg (`cFvgBDisp` / `cFvgSDisp`). A tagged SB setup may only lock
  an FVG that is both displacement-cut and at least `sbFvgMinAtr` ATR tall. If
  the first gap fails, the SB setup waits for a better one instead of locking a
  bad anchor.
- **MSS preferred:** the shift grade is recorded (`sbShiftGL/S` — 2 MSS, 1
  CHoCH/CISD). `sbReqMss` (default off) restricts a tagged SB setup to a true
  MSS; off, an external CHoCH or CISD still qualifies but scores one point less
  and lowers the bar for the structure-based exit.
- Setups deliberately kept per-direction and edge-triggered, exactly as v3.

**Design note:** this is an overlay on the existing machine rather than a
second parallel state machine. Two machines arming on the same bar in the same
direction would need a conflict rule of their own and would duplicate ~200
lines of stage logic; the tag gives every behaviour the spec asked for while
leaving the v3 path bit-for-bit intact when the tag is 0.

### SB-5 · SB entry

- **Limit at the CE** — the 50% of the locked FVG (`sbCeTol` tolerance). The CE
  test also requires the proximal edge, so "CE reached" always means price
  actually traded into the gap.
- **Proximal edge** accepted only with a strong rejection: pin, engulf, IFC or
  CISD (`sbEntryMode`; set to "CE (50%) only" to forbid it).
- **HTF bias alignment** (`sbReqHtf`) and the **correct premium/discount side**
  (`sbReqPD`) are required.
- Entry must land **inside the setup's own window** (relaxed only if
  `sbKillAtEnd` is off).
- No confirmation candle is required for a CE fill — that is the point of a
  limit order at the CE. The proximal path is the one that needs confirmation.

### SB-6 · SB exit engine (MODULE 19)

Only an **SB-tagged** trade uses it. A non-SB trade keeps the v3 path and the
v3 counter semantics exactly (closed at TP2), so nothing about existing
statistics changes.

- **TP1** → stop to **break-even + `sbBeBuf` ATR**.
- **TP2** → stay in; **trail behind the external protected swing**, capped so
  the stop is never trailed through current price.
- **TP3** → the **liquidity target**: the *nearest* opposing pool that still
  pays ≥ TP2, chosen from the nearest unspent opposite POI, the prior Asia /
  London / NY session high or low, and PDH/PDL. Nothing qualifying leaves TP3
  on its 3R / `tpMode` value.
- **Time** → at the close of the originating window with **TP1 unhit**: full
  exit, or (`sbTimeMode` = Partial) mark the reduction and put the remainder at
  break-even.
- **Structure** → opposing **MSS**, or an opposing CHoCH/CISD when the entry
  shift was only CHoCH/CISD grade — equal or higher quality, never lower.
- New counters: `cntSbEnt`, `cntTP3`, `cntSbTime`, `cntSbStruct`. Mechanical
  touch counts, not a backtest.

### SB-7 · scoring, tiers and precedence

- New **SB Context component, 0–15**: window weight (NY AM 6 · NY PM 5 · London
  4) + preferred pool 3 + sweep quality 3/2 + shift grade 2/1 + window gate 1.
  Zero outside an SB context window, and the total is **clamped at 100**, so a
  non-SB bar scores exactly what it scored in v3.
- SB entries must clear a **higher tier floor** than the generic machine entry:
  `sbMinTier` = A (default) or A+, on top of the display filter.
- While a clean SB setup is live (tagged and past its POI), non-SB **engine
  candidates** are **down-weighted one tier** (default) or **muted**
  (`sbSuppress`). The machine path is never muted — it is what carries the SB
  narrative. The existing tier system and confluence scoring are otherwise
  untouched.
- `sbOnly` — hard SB-only mode; nothing fires outside the windows, and the
  dashboard verdict says so.

### SB-8 · visuals and alerts

- **Per-window background band**, brightest for NY AM. This **reuses v3's
  single Silver Bullet `bgcolor` slot** — see the budget note below.
- SB **window range boxes**; the **locked SB FVG** box now names its window and
  prints its CE; a solid **CE line**; a dotted **liquidity-target line** with a
  label while an SB trade runs.
- Distinct **`◆ SB <window> · CE|edge <tier>`** labels in teal, versus the
  ordinary `◉ SETUP`. Forced exits print `◆ SB time exit` / `◆ SB structure
  exit` chips.
- Dashboard: **`◆ Silver Bullet`** row showing `ACTIVE <window> · Nm left (N
  bars)`, and a **`◆ SB setup`** row with the tagged side, stage and live trade
  plan. Debug table: SB state (window, tag, pool kind, FVG cleanliness) and the
  SB exit counters.
- **One** new `alertcondition` — `[SB] ◆ Silver Bullet entry`. Everything else
  (armed · FVG locked · TP1 break-even · time exit · structure exit · setup
  gone, each with window, grade, CE, score and the full plan) goes through
  `alert()`.

---

## 2. Two hard constraints you should know about

### CE10295 — "the main body of the script is too long" (fixed)

TradingView rejected the first build with **CE10295**. That is a *different*
limit from the compiled-token cap: it bounds how much code may sit in the
script's **main body**, and the remedy is the one the error names — move code
into functions, because a function body is its own scope.

Main-body statement counts (non-comment, outside any function):

| build | main-body stmts |
|---|---|
| v3 | 2107 |
| v3.1, first build | 2515 — **CE10295** |
| v3.1, after this refactor | **1457** (31 % below v3, 42 % below the build that failed) |

**42 functions now, up from 18.** What moved, and why each move is safe:

- *Display / table / alert leaves* — `f_sigLabels` `f_tradePlan` `f_drawPoi`
  `f_drawFlow` `f_extendDraw` `f_dash` `f_dbg` `f_sbAlertFeed` `f_structMarks`
  `f_openLines` `f_ltSigLabels` `f_ltPoolLines`. These only READ state and emit
  labels, boxes, table cells or `alert()` messages — all legal inside a Pine
  function — so they moved verbatim.
- *Self-contained state* — `f_cisd` `f_trigMem` `f_regimeMem` `f_fvgRegistry`
  `f_latestFvg` `f_insideBar` `f_dojiRev` `f_zoneUpdate` `f_zoneCreate`
  `f_nextZones` `f_ltPools` `f_ltObNear` `f_ltMachines`. Their `var` state now
  lives inside the function and the values the rest of the script reads come
  back as a tuple.

Four rules governed the whole refactor, and a static checker enforces each:

1. **A Pine function cannot assign to a global.** So state either moved inside
   and returned, or stayed put. Mutating a global *array* or a UDT field from
   inside a function IS allowed (it is a reference, not an assignment) — that
   is what lets `f_zoneCreate` and `f_fvgRegistry` return nothing at all.
2. **No nested function definitions.** `f_ltScore` and `f_pushZone` had to be
   lifted out of the ranges that were wrapped around them. `f_ltScore` could no
   longer read the two trap-machine states as globals, so it now takes them as
   parameters — the only signature change in the refactor.
3. **State names inside the new functions are `_`-prefixed** (`_ltLState`,
   `_cisdDn`, …) so a function-local can never shadow the same-named global the
   destructure re-creates.
4. **Every guard stayed inside its function** and every call site is
   unconditional, so `var` state advances on exactly the bars it did before.
   A conditionally-called function would silently stop advancing its history.

Two consequences worth knowing:

- The debug table's two ◬ LT rows are now built inside `f_ltMachines` and
  handed out as `ltDbgMach` / `ltDbgLast`. Same text, different assembly point.
- `sig3Long` / `sig4Long` / `sigSDLong` and friends are deliberately
  **re-declared as plain globals** from temporaries (`sig3Long = t3L`) rather
  than destructured directly, so MODULE 18 can still gate them with `:=`.

**No behaviour changed.** Nothing was added, removed or re-tuned — this is a
pure scope move.

### The two limits now pull in opposite directions

Wrapping code into functions costs a little in compiled tokens (signatures,
tuple destructures) while buying a lot of main-body room. The estimate went
from ~95,000 to **~96,800** against the 100,256 CE10117 cap — roughly 3.5 %
headroom, on the same scaled estimate as before, still **not a measurement**.

So: **CE10295 → move more code into functions. CE10117 → the opposite, remove
features.** If CE10117 fires now, the cheapest cuts are the SB window range
boxes (SB-1), the SB debug rows, the `alert()` message bodies, and then LT-5 /
LT-6 / LT-7. Do not try to fix a token error by un-wrapping functions.

Still in reserve for CE10295 if it somehow returns: MODULE 17's state machine
(~200 statements) and MODULE 19's trade-resolve tree (~90). Both were left
alone deliberately — they are the heart of the system and they need in/out
parameters rather than a clean move.

### The output budget is FULL: 64 / 64

8 `plot` + 14 `plotchar` + 5 `bgcolor` + 37 `alertcondition` = **64**, which is
the Pine ceiling. That is why the SB window band reuses v3's existing Silver
Bullet `bgcolor` instead of adding one, why SB marks are drawn as labels rather
than `plotchar`, and why there is exactly one new `alertcondition`.

**Adding any `plot` / `plotchar` / `bgcolor` / `alertcondition` anywhere in this
file will now fail to compile.** To add one, either consolidate two existing
`alertcondition`s (which breaks any alert a user already created on them) or
raise nothing — there is no slack.

Create **one** alert on **"Any alert() function call"** to get the detailed SB
feed. Use **"Once per bar close"** for the `alertcondition` alerts.

### Compile-token budget — estimated, not measured

The binding limit is 100,256 compiled tokens (CE10117). Scaling from the one
real measurement on record (the v10 file's first load = 106,706 compiled tokens
at a 31,497-token like-for-like proxy) gives v3.1 ≈ **95,000**, i.e. under the
cap with roughly 5% headroom. **This is an estimate from a different file's
measurement, not a reading.** If TradingView rejects the script with CE10117,
bisect with the `SB-n` / `V31-FIX-1` tags in the source; the cheapest removals
are the SB window range boxes (SB-1), then the SB debug rows, then the `alert()`
message bodies.

---

## 3. Usage notes — settings for a Silver Bullet focus

**Timeframe.** 1m–5m chart. The SB windows are 60 minutes, so a 5m chart gives
12 bars per window and the default SB clocks (12 / 8 / 10) span roughly the
whole window; on 1m they are deliberately tight. Above 15m the module is
pointless — the window is 4 bars.

**Recommended SB-focused configuration**

| Input | Value | Why |
|---|---|---|
| `HTF bias filter` | 60 (or 15 on a 1m chart) | SB entries require alignment |
| `HTF for CRT / TBS / POI` | Auto | leaves the FEM/CRT pairing sane |
| `Show signal tiers` | A and above | SB is an A/A+ model |
| `Min tier for an SB entry` | A and above → A+ only once you trust it | |
| `Non-SB signals while an SB setup is live` | Down-weight, or Suppress for a pure SB session | |
| `SB-only mode` | **off** while you learn the module, **on** for a dedicated SB session | |
| `Require a preferred pool` | on | the doctrine raid takes engineered liquidity |
| `London / NY AM / NY PM min sweep quality` | 3 / 2 / 3 | London is the most selective window, as asked |
| `Require a true MSS` | off at first; on if you get too many CHoCH-grade entries | |
| `SB entry rule` | CE preferred + proximal on strong rejection | |
| `Block entries inside the windows` (news) | on — note **Window #2 is 09:55–10:10**, which overlaps the start of the NY AM SB | see caveat below |
| `Global same-direction cooldown` | 10 | |
| `Suppress entries in CHOP regime` | on, with `SB may arm in CHOP` also on | the window is a scheduled delivery slot |

**The news-window overlap is deliberate but check it.** The stock volatility
Window #2 (`0955-1010`) blocks entries through the first ten minutes of the NY
AM Silver Bullet. On a day with no 10:00 release that costs you the window's
opening entries. Either narrow it to `0958-1004`, or turn `Block entries inside
the windows` off and watch the calendar yourself. These are fixed clock windows,
**not** a live economic calendar.

**How to read a live SB setup**

1. Dashboard `◆ Silver Bullet` turns teal: `ACTIVE NY AM · 43m left (8 bars)`.
2. `◆ SB setup` shows `LONG NY AM · SWEPT` — the raid took an engineered pool.
3. It moves to `AT POI`, then `SHIFTED·await retest`, and a teal box appears
   with `◆ SB NY AM FVG locked · CE <price>` plus a solid CE line. **That CE
   line is your limit price.**
4. Entry prints a teal `◆ SB NY AM · CE A+` label with the score. The dotted
   teal line is the planned liquidity target (TP3).
5. `◆ SB setup` then tracks `trade TP1✓ TP2· SL <price>`.
6. If the window closes with TP1 unhit you get a `◆ SB time exit` chip and an
   alert. That is the model telling you the trade failed to deliver in its own
   window — the most useful exit rule in the whole set.

**Known limitations, stated rather than hidden**

- `sbRemMin` is measured from the **current bar's open**, so on the last bar of
  a window it reads one bar high.
- The window minute math does not support a window that crosses midnight. None
  of the three does, but a user retuning `sbSes*` across midnight would get
  `na` remaining time (the window flags themselves still work).
- The pre-window grace compares the minute-of-day only, so it ignores any
  `:days` filter you add to an `sbSes*` string.
- `sbTimeMode` = Partial cannot model position size; it marks the reduction and
  moves the remainder to break-even.
- Every open item in `AUDIT-v11.md` §8 that also exists in this lineage is
  untouched — in particular `slEngL / slEngS` remain last-writer-wins within an
  engine class.
