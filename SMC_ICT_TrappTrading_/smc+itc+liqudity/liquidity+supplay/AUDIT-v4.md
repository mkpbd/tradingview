# AUDIT — LQ-SD-PA v2 → v4 "Trade Engine"

**Source audited:** `1.liquidty+supply.txt` (v2, 2 243 lines, 130 848 bytes)
**Output:** `2.liquidty+supply-v4-trade-engine.pine` (3 164 lines, 177 753 bytes)
Date: 2026-09-08 · Pine v6

> **Not compiled.** No Pine compiler exists outside TradingView. This file has
> been statically verified (see §11) but never loaded on a chart. It has not
> been backtested. No accuracy or profitability claim is made anywhere in it.

---

## 1. Major bugs found

Numbered `BUG-nn` in the source header so a TradingView error can be bisected
by tag.

### Structure engine

**BUG-1 — the "protected swing" was not a swing.**
```pine
legLo := na(legLo) ? low : math.min(legLo, low)   // v2
```
`legLo` / `legHi` were a running min/max of *every* low/high since the last
structural event, updated on **every tick**, and reset only inside the
`confirmed and body >= structDisp*atr` branch. Three separate failures:

* immediately after a BOS, `protLo` was the BOS bar's own low, so a one-bar
  pullback printed "CHoCH";
* across any stretch with no qualifying displacement break, `legLo` decayed
  toward the all-time low, so CHoCH became *unreachable*;
* intrabar wicks poisoned it permanently (no `confirmed` guard).

**BUG-2 — the break latch was burned by non-structural closes.**
STEP 3 set `resBroken := true` on *any* confirmed close above `lastRes`, but
`f_structure` only consumed that break when `body >= structDisp*atr`. A weak
close through a swing high therefore consumed the level and the BOS could never
be registered — with the default `structDisp = 0.5` this silently discarded a
large share of real structure events, and the same latch feeds setups ①②③.

**BUG-3 — internal and external structure were merged where it matters most.**
```pine
if chochUp or eChochUp
    lastChUpBar := bar_index
```
One shared trigger memory, so an *internal* (inducement-grade) CHoCH satisfied
both the A+ **Context** term and the A+ **Trigger** term. Exactly the semantic
ambiguity Phase 5 forbids.

### Liquidity

**BUG-7 — EQH/EQL was "two prices are close".**
No time separation, no reaction test, and the pool was registered at
`math.max(ph, prevPH)` — the *higher* of the pair — so the level was pre-swept
by construction and the first wick over it counted as the raid.

**BUG-8 — the EQ scan was destructive and it stole other setups' context.**
The pool was deleted on *any* penetration (a full break with close beyond
included, which is not a sweep), and on a sweep it overwrote the global
`lastBslBar` / `lastBslLvl`. An EQH raid therefore silently replaced the swing
sweep another setup was relying on.

**BUG-9 — "sweep in play" had no lower bound.**
```pine
sslInPlay = recentSsl and close - lastSslLvl <= SWEEP_CTX_ATR * atr
```
Once price closed **below** the swept low — i.e. the sweep failed and became a
breakdown — the expression went negative and still read "in play", paying 10
liquidity points to LONGS.

**BUG-10 — no sweep→setup binding at all.**
`lastSslBar` / `lastSslLvl` were single global slots. Any long producer within
`sweepLook` bars inherited the raid, wherever it was on the chart. "Old
liquidity sweep + new POI → new signal" was reachable by construction.

### POI / zone lifecycle

**BUG-4 — zone state mutated intrabar.** `z.touched`, `z.touchBar`,
`z.tapped50`, `z.tap50Bar` all updated outside `confirmed`, so an intrabar wick
the bar closed away from still opened the `confirmWin` confirmation window.
Textbook realtime-vs-history divergence.

**BUG-5 — zones were consumed by signals that never printed.**
`z.signaled := true` was set inside the zone loop, *before* `longOK` /
`shortOK` (bias, killzone, volatility window, min-score, cooldown) were applied.
Same class: `wState := 0` (setups ①②) and `femL := 0` (FEM) were also reset
before gating. A filtered-out bar destroyed the setup.

**BUG-21 — spent zones were replaced by fresh overlapping ones.**
The dedupe branch deleted a zone when `z.score < newScore` **or**
`z.signaled`, so a *spent* zone was replaced by a fresh overlapping zone that
immediately re-armed the same price for another entry.

**BUG-22 — the zone cap was wrong twice.** Compared with `>` (so `maxZones + 1`
persisted between creations) and deleted at most **one** zone per bar, in array
order — but rejection blocks are pushed with a historical left edge, so array
order ≠ age order.

**BUG-6 — display toggles gated trade logic.** `showEq` off ⇒ no EQ pools ⇒ the
engineered-liquidity score term is permanently 0. `showSesHL` off ⇒ session
raids invisible to the score. `showZones` off ⇒ no POIs at all. A *visual*
checkbox changed the signal set.

### MTF

**BUG-15 — HTF CRT / turtle soup were two HTF bars late.**
`f_crtTbsHtf()` returned `_crtB[1]` **and** `request.security(...)` used
`lookahead_off`, which already delivers the last *closed* HTF bar. Net: on a
5m chart mapped to 1H the "distribution candle" was an hour old. `f_bias` had
the same `nz((...)[1], 0)` defect, making the whole MTF bias row two HTF bars
stale.

**BUG-16 — the score's HTF context was the bias-filter timeframe.**
`htfB = filtBias != 0 ? filtBias : b60`. With the filter **off** the "HTF
context" silently became 1H — a *lower* timeframe on a 4H chart — and turning
the filter on changed the score.

**BUG-17 — the HTF FVG POI accepted anything.** Any 3-candle HTF gap became a
POI (no displacement requirement, no HTF-direction filter, session-open gaps
included); only one POI per side was kept; and when a POI died `bTop`/`bBot`
were cleared while `bBar`/`bIn` were not, so the touch counter kept comparing
against a stale bar.

### Execution

**BUG-18 — FEM's "delivery shift" accepted a plain internal BOS**
(`if femL == 1 and (cisdUp or chochUp or bosUp)`), had **no displacement
stage**, locked the *latest* post-tap FVG rather than the first (`cFvg*` is
overwritten by every new FVG), and its retest confirmation
(`zoneBullConf ⊇ ifcBull`) is near-tautological on a retest bar.

**BUG-19 — trendlines.** Every bar resting within `NEAR_LVL_ATR` of the line
incremented the touch count, so "validated (≥2 touches)" was reached by two
*adjacent* bars; the sweep branch incremented *before* testing, so the first
pierce of a once-touched line fired; `tlUpTouch` was not reset on break, so a
brand-new line inherited the old count and fired on its first pierce; and the
slope divided by `(bar_index - pivLen - prevPHBar)` with no zero guard.

**BUG-20 — CRT and turtle soup had no location filter.** A mid-range CRT ranked
identically to one at an external pool.

**BUG-23 — `bullPin` required `upWick <= body`.** On the cleanest rejection
candles the body is near zero, so that test is false: perfect hammers were
rejected. The cap has to be a fraction of *range*, not of body.

### Signal architecture (the big one)

**BUG-11 — one stop slot, six writers.** `sigSLLong` / `sigSLShort` were
written by the zone engine, setup ①, the trendline engine, CRT, turtle soup and
FEM — last writer wins. A FEM entry could be drawn with a turtle-soup stop, and
engines that fired then got silenced by the filters still overwrote it.

**BUG-12 — score double counting.** A CISD candle *is* by definition a
displacement close (it requires `body >= BRK_BODY_ATR*atr` and an outer-third
close), so one candle paid 7 (CISD) + 6 (displacement) and, if it also broke a
pivot, +7 (MSS) = **20/20** of the Trigger layer. Liquidity paid 10 (sweep) + 5
(quality of the *same* sweep) + 5 (the EQ pool that *set* that sweep, BUG-8) =
**20/20**. Execution paid 5 for `zoneBullConf`, which for an IFC bar is again
the same candle.

**BUG-13 — A+ had no sequence.**
```pine
aPlusLong = htfB > 0 and (extDir > 0 or recentChUp) and liqLong >= 10
     and poiLong >= 5 and (recentChUp or recentCisdUp) and execLong >= 5
```
All six terms are satisfiable with **zero causal order**; `recentChUp`
satisfied both the Context and the Trigger term; there was no displacement
stage, no FVG stage and no retest stage. An old sweep, a zone price merely sits
near, a 10-bar-old internal CHoCH and a pin bar produced "A+".

**BUG-14 — `anyLong` / `anyShort` was a blind OR of 11 producers.** One candle
could print eleven setups in one label, carry the stop of whichever engine
wrote last, and fire every `alertcondition` simultaneously. Long and short
could both fire on the same bar — only the trade *drawing* was suppressed;
labels, alerts and cooldown stamps still went out.

**BUG-24** — the `masterCd` / `minScore` / killzone / volatility gates were
applied to the label flags while the underlying state machines had already
advanced or reset (see BUG-5).

### Not fixed, by design

* `f_htfPoi` still keeps **one** POI per side (a registry would cost more
  compile budget than it is worth here); it is now displacement- and
  direction-filtered, and it expires properly.
* `showRB`, `showCRT`, `showTBS`, `showS1..4`, `showTL`, `useFEM`,
  `useHtfCrt` remain **feature** toggles, not display toggles — turning them
  off is a genuine model choice. `showZones`, `showEq`, `showSesHL`, `showPD`,
  `showPools` are now display-only (BUG-6).

---

## 2. Major changes made

| # | Change | Where |
|---|---|---|
| ARCH-1 | Setup **state machine**, one live setup per direction, states 0→9, every stage with its own expiry | MODULE 12 |
| ARCH-2 | **Liquidity registry**: every level is a `Pool` with CREATED → VALIDATED → RAIDED → REACTION → CONSUMED, plus a liquidity-**intent** read | MODULE 7 |
| ARCH-3 | Structure rebuilt on **real originating pivots**, internal and external kept semantically separate, weak close-throughs classified as liquidity **runs** | MODULE 4 |
| ARCH-4 | POI **quality tiers** T1/T2/T3 + full FVG lifecycle (fresh → 50 % mitigated → filled → invalidated) | MODULE 9 |
| ARCH-5 | Score rebuilt **25/25/20/20/10**, each event paid once | MODULE 13 |
| ARCH-6 | **Trade engine**: rank arbitration, one signal per direction, never both | MODULE 15 |
| ARCH-7 | Structural **SL hierarchy** + liquidity **TP ladder** | MODULE 16 |
| ARCH-8 | **Debug panel** with the state machine and the exact block reason | MODULE 19 |
| ARCH-9 | Confirmed-only by default; developing setups are a dim `⋯` preview that changes no state and raises no alert | throughout |

Module map: 1 inputs · 2 constants/helpers · 3 core series + CISD + IFC ·
4 structure · 5 sessions/killzones/Silver Bullet/opens · 6 HTF context ·
7 liquidity registry · 8 dealing range/PD/OTE · 9 S/D + FVG · 10 trendlines ·
11 pattern producers · 12 state machine · 13 score · 14 base gates ·
15 trade engine · 16 risk · 17 visuals · 18 dashboard · 19 debug · 20 alerts.

**Nothing was removed.** All 13 numbered v2 setups, CISD, IFC, HTF CRT/TBS,
HTF FVG POI, FEM, rejection blocks, breaker/mitigation flips, order-flow
halves, session H/L, opening prices, Silver Bullet, volatility windows,
dashboard, TP ladder and every alert **name** are still present.

### Two defects introduced during the rewrite and fixed before delivery

* `poolRaids = confirmed ? f_poolScan() : 0` — Pine evaluates **both** branches
  of a ternary, so this would have mutated pool state on every intrabar tick.
  The `confirmed` guard now lives *inside* `f_poolScan`, and the call is
  unconditional.
* Array **indices** were originally stored for the bound pool and the candidate
  zone. `f_poolScan` and the zone prune both `array.remove`, which re-points a
  stored index at a *different* object. Both now hold the **object reference**
  (`Pool pool` field on `Setup`, `Zone sdZoneL/sdZoneS`). The zone prune was
  also moved ahead of the update loop so a box handed to the engine as a
  candidate cannot be deleted later in the same bar.

---

## 3. Entry pipeline

```
STATE 0  NO SETUP
   ↓     HTF context aligned (direction | premium-discount | a live HTF POI)
STATE 1  HTF CONTEXT
   ↓     nearest un-raided opposing pool exists  →  that is the TARGET
STATE 2  LIQUIDITY TARGET IDENTIFIED
   ↓     that pool is RAIDED (wick through, close back inside) and BOUND
STATE 3  LIQUIDITY RAIDED                       [expires: mssWin bars]
   ↓     an eligible POI (tier ≤ minTier) contains the raid wick within
   ↓     poiBindAtr·ATR — HTF FVG POI first (FEM), else a chart-TF zone
STATE 4  VALID POI CONFIRMED                    [expires: mssWin bars]
   ↓     internal CHoCH, or CISD (unless "MSS must be a CHoCH")
STATE 5  LTF MSS / CHoCH / CISD                 [expires: dispWin bars]
   ↓     displacement bar: body ≥ dispFactor·ATR AND close in its outer third
STATE 6  DISPLACEMENT                           [expires: fvgWin bars]
   ↓     the FIRST FVG at/after the displacement bar, LOCKED
STATE 7  FRESH FVG LOCKED                       [expires: retestWin bars]
   ↓     a LATER bar trades to retestDepth into it, closes respecting it,
   ↓     and shows rejection (confirmation candle or a strong close)
STATE 8  ENTRY  ← the only narrative source of a signal
   ↓
STATE 9  CONSUMED (pool → CONSUMED, setup → DEAD)
```

Invalidation at any state ≥ 1: setup older than `setupLife`; opposite
**external** CHoCH; price closed beyond the raid wick (the raid failed);
POI invalidated; FEM window expired; each stage's own window elapsed.

Because state 8 requires `bar_index > fvgBar`, the narrative path can never
complete inside a single bar — the structural minimum is two bars, and in
practice four to eight.

**Non-machine producers** (S/D retest, CRT, turtle soup, trendline, price
action) must additionally pass the confluence gate:
`raid in play AND (MSS or CISD) AND displacement within 3 bars`,
plus their own location/tier requirement.

---

## 4. Signal priority

```
1  FEM                (machine, POI = HTF FVG POI)
2  Sweep + POI + MSS  (machine, POI = chart-TF zone)
3  S/D 50 % retest
4  CRT           (chart TF or HTF)
5  Turtle soup   (chart TF or HTF)
6  Trendline sweep
7  Generic price action  ① ② ③ ④
```

* One `if / else if` chain per direction → **exactly one** producer wins.
* Both directions qualifying: the better rank wins; an **equal-rank tie mutes
  both** sides.
* Consumption happens only when the engine actually emits: the machine's pool
  is set CONSUMED, the setup DEAD; an S/D zone is marked signaled; CRT/TBS
  stamp their cooldown; the ①② wick watch is cleared. A gated-out signal
  consumes nothing (BUG-5).
* Entry mode gates which ranks are eligible:
  * *Narrative only (A+)* — ranks 1–2 only
  * *Narrative + confluence* (**default**) — ranks 1–5
  * *All engines (legacy)* — ranks 1–7
  So by default the trendline sweep and the four price-action patterns are
  **drawn but not tradable**. That is deliberate; raise the mode to enable them.

---

## 5. Repaint audit

* **Every state latch** is gated on `barstate.isconfirmed`. The guard sits
  *inside* `f_structUpdate`, `f_poolScan` and `f_setupAdvance` so it cannot be
  bypassed by a conditional call site, and specifically so a ternary (which
  evaluates both branches) cannot mutate state intrabar.
* **`request.security` — 5 call sites, all `lookahead_off`** except the PDH/PDL
  call, which uses `lookahead_on` **with `[1]` inside the request**: the
  standard idiom that reads only the completed previous day, on historical and
  realtime bars alike.
* The **redundant `[1]`** inside `f_crtTbsHtf`, `f_bias` and `f_htfPoi` is
  gone. `lookahead_off` already returns the last *closed* HTF bar; stacking
  `[1]` on top made the data two HTF bars old (BUG-15).
* **The remaining delay is stated, not hidden:** an HTF bar is only usable once
  it has closed, so an HTF event surfaces on the first chart bar after that
  close. HTF CRT / turtle soup are therefore one HTF bar late by construction.
  This is a confirmation delay, not a repaint.
* **No future data anywhere.** Every `[n]` is a backward reference; there is no
  `lookahead_on` without `[1]`, no `security` of a *lower* timeframe, and no
  `barstate.islast`-only computation feeding a signal (the `islast` blocks only
  draw).
* **Developing vs confirmed** is explicit: `Confirmed signals only` is ON by
  default, and `Preview developing setups` draws a dim `⋯` on the live bar that
  changes no state and raises no alert. Turning the preview on does **not**
  make signals earlier.
* Session extremes deliberately track intrabar highs/lows (that is real price)
  but are **frozen** only on a confirmed session close.
* Objects are never styled after deletion: pool lines are always created (fully
  transparent when their display group is off, so no `na`-id setters exist), and
  the zone prune runs before the update loop.

---

## 6. Scoring changes

| Layer | 25/25/20/20/10 | Components |
|---|---|---|
| CONTEXT | 25 | HTF direction 8 · external structure 8 · premium/discount 5 · session 4 |
| LIQUIDITY | 25 | external liquidity 10 · engineered liquidity 7 · raid quality 8 |
| POI | 20 | HTF POI 8 · freshness 4 · FVG/OB quality (tier) 4 · OTE 4 |
| TRIGGER | 20 | MSS/CHoCH 8 (BOS 4) · displacement 6 · CISD 6 |
| EXECUTION | 10 | FVG retest 6 · rejection quality 4 |

Anti-double-count rules, which is the whole point of the rebuild:

* **Displacement pays only if it happened on a different bar from the MSS**,
  and **CISD only if on a different bar from the CHoCH**. In v2 a single candle
  could collect all three.
* **External and engineered liquidity are different pools.** The layer scans
  the registry for a live external-class raid and a live EQ raid separately, so
  paying both is independent evidence — but one pool can never pay twice.
* Only the **winning producer's** tier / freshness / HTF-POI flag feed the POI
  layer, so a zone unrelated to the signal cannot contribute (v2's `retestLong`
  read the *next un-signaled* zone, whatever that was).

**A+ is not a score threshold.** `aPlus = producer ≤ rank 2 AND POI tier == 1`,
i.e. the machine completed the whole sequence *and* the POI was A-grade. A score
of 95 with an incomplete sequence produces no A+ and, on its own, no signal at
all. The dashboard labels the number "narrative alignment 0–100 — NOT a win
probability", and no alert message calls it a probability.

---

## 7. SL / TP changes

**SL hierarchy** — first candidate that is on the correct side **and** inside
`[minRiskAtr, maxRiskAtr]·ATR` wins; each is padded by `SL_PAD_ATR`:

1. the **liquidity-raid wick** (`Setup.liqExt`; for CRT/TBS/①/TL, that
   producer's own invalidation wick)
2. the **protected structural swing** (internal, falling back to external)
3. the **FVG invalidation** level (`Setup.fvgBot` / `fvgTop`)
4. the **POI edge**
5. ATR fallback (`atrStopMult`)

The `maxRiskAtr` ceiling is what stops an HTF-sized structural level from being
pinned onto a 5m entry — the hierarchy falls through to the next candidate
instead. The stop's **source is printed on the SL label** ("raid wick",
"protected swing", "FVG invalidation", "POI edge", "ATR fallback"), so a wrong
stop is diagnosable at a glance. Only the **winning** producer's levels are
used, which retires BUG-11.

**TP ladder** (`Liquidity ladder`, the new default):

* **TP1 = internal liquidity** — nearest live minor-swing pool beyond entry,
  floored at 1 R
* **TP2 = opposing FVG / OB** — nearest live opposing zone edge, floored at
  `rrMult` R
* **TP3 = external liquidity** — nearest live external / PD / session / EQ
  pool, floored at 2 R
* **Clamp:** with `tpClamp` on, TP3 is pulled back to just short of the nearest
  un-raided opposing POI rather than parked behind it
* The ladder is forced monotone, and `Next level` / `R multiple` preserve the
  v2 behaviour exactly

---

## 8. Performance

* **`request.security` count unchanged at 5** call sites despite the added HTF
  context engine — the context bundle (direction, external swings,
  premium/discount) is **one** call returning a tuple, not four.
* **One displacement definition** (`dispUpBar` / `dispDnBar`) replaces three
  near-duplicates; one `atr` series; one `f_recent`.
* **Pool lines are created once and mutated** (style/extend/x2), never
  recreated; capped at `poolMaxN` (28).
* **Zones**: the O(n) dedupe and prune run only on a creation bar; the prune is
  now a single pass per side instead of one deletion per bar.
* **`barstate.islast` only** for zone extension, HTF POI boxes, locked-FVG
  boxes, order-flow halves, the OTE box, next-POI labels, liquidity-target
  labels, the dashboard and the debug panel — no historical redraw.
* **Object budget:** ≤ 28 pool lines + ≤ 40 zigzag lines + ≤ 12 zone boxes and
  midlines + a bounded set of session / opening / trade drawings, against
  `max_boxes_count = max_lines_count = max_labels_count = 500`.
* **Output slots: 58 / 64** — 4 `plot` + 12 `plotchar` + 5 `bgcolor` +
  37 `alertcondition`. Six free. Adding any output beyond six will fail
  to compile.

---

## 9. Remaining limitations — honest list

1. **Nothing here is compiled or backtested.** Treat the first TradingView load
   as part of the work.
2. **Compile budget is the standing risk.** A like-for-like token proxy puts v4
   at ~1.41× v2. v2's real compiled-token count was never measured, so v4's
   headroom under the 100 256 cap (CE10117) is an estimate. Main-body statement
   count is 1 606, which is comfortably under the CE10295 ceiling this lineage
   has hit before (a sibling build failed at 2 515 and passed at 2 107).
3. **"Scheduled volatility windows" are fixed clock slots, not a live economic
   calendar.** Not every 08:30 is CPI/NFP and not every Wednesday is FOMC. The
   input group, tooltips and dashboard row all say so.
4. **Pine cannot see order flow.** "Displacement", "liquidity raid" and "POI"
   are candle-geometry proxies for intent. There is no volume delta, no book,
   no auction data.
5. **The HTF confirmation delay is real.** An HTF CRT is reported one HTF bar
   after it completes. That is the price of not cheating with lookahead.
6. **`request.security` on the chart's own timeframe is meaningless**, so the
   HTF engines self-disable when `htfTf == timeframe.period` (`htfLive`).
7. **One HTF FVG POI per side.** A second, deeper HTF POI is not tracked.
8. **The narrative path is deliberately rare.** On a 5m chart expect a handful
   of state-8 entries per week per side. If nothing prints, read the debug
   panel before loosening anything — and loosen `minTier` / `needHtfAlign` /
   the stage windows, in that order, rather than switching to legacy mode.
9. **Tier grading uses the state at zone creation.** A zone created in poor
   context stays T3 even if context later improves. Breaker/mitigation flips
   re-grade, ordinary zones do not.
10. **`bothTie` mutes both directions** on an equal-rank conflict. That is a
    deliberate choice to avoid coin-flip entries, and it does discard some
    genuine setups.
11. **No position management.** No break-even, no trailing, no partials — the
    file draws one entry/SL/TP set and stops. (The sibling v3.1.1 lineage has
    adaptive BE + trail; it was not ported.)
12. **`f_setupAdvance` runs a single top-down pass**, so a bar that satisfies
    several stages advances several states at once. That is intended (a strong
    reversal bar can be the raid *and* the MSS *and* the displacement) but it
    does compress the narrative on very volatile bars — XAGUSD/XAUUSD news
    spikes in particular.

---

## 10. Validation checklist

| Check | Status | How |
|---|---|---|
| No lookahead | ✔ | 5 `request.security` sites; all `lookahead_off` except PDH/PDL which is `lookahead_on` **with `[1]`** (completed-day idiom) |
| No future-data leakage | ✔ | every history reference is backward; no lower-TF security; `islast` blocks only draw |
| No uncontrolled signal spam | ✔ | rank arbitration + per-direction `masterCd` (default 6) + per-producer cooldowns + per-stage expiries |
| No duplicate final signals | ✔ | one `if/else if` chain per direction; equal-rank cross-direction tie mutes both |
| HTF context works | ✔ | one consolidated bundle; context TF independent of the filter TF (BUG-16); context enables, never triggers |
| Liquidity lifecycle works | ✔ | `PS_NEW → PS_VAL → PS_RAID → PS_REACT → PS_DONE`, raid bound to one setup, dies on failure / staleness / travel |
| POI lifecycle works | ✔ | fresh → touched → 50 % → filled → dead, `deepest` fill tracking, edge-triggered 50 % tap, causal breaker chain |
| MSS/CHoCH works | ✔ | real originating pivots; internal = MSS only, external = context only; weak close-through = "run" |
| FVG lifecycle works | ✔ | tiered at creation, 50 % is preparation not entry, full fill retires the POI (`fvgFillDead`) |
| FEM works | ✔ | now the machine with the HTF POI as its POI stage → outranks everything, cannot fire on its own |
| CRT/TBS location filter works | ✔ | `crtNeedLoc`: HTF POI / engineered or external raid / OTE / PD extreme; raw pattern still drawn with a `·loc✗` tag |
| Silver Bullet properly filtered | ✔ | window is a filter or a score boost, never a signal; `sbOnlyIn` optional; entries tagged `· SB` |
| SL is structural | ✔ | 5-level hierarchy, ATR is last; source printed on the label |
| TP uses liquidity | ✔ | internal → opposing FVG/OB → external, with R floors and an opposing-POI clamp |
| Alerts work | ✔ | all 34 v2 names preserved + 3 new = 37; `[SIGNAL]` conditions now come from the trade engine |
| Dashboard works | ✔ | 21 rows; adds HTF context, raid-in-play, liquidity targets, machine state, tier tags |
| Debug mode works | ✔ | 3×11 panel: the 9 stages per direction + the exact block reason |
| **Compiles** | ✖ | **not verified — no Pine compiler outside TradingView** |
| **Backtested** | ✖ | **not done** |

---

## 11. Static verification performed

Run against the assembled file:

* indentation is 4k or 4k+1 throughout, and **every** 4k+1 line follows a line
  ending in an open operator (a wrapped line on a 4-multiple indent is read by
  Pine as a new statement)
* brackets balanced; no tab indentation
* output slots counted: **58 / 64**
* no `plot` / `plotchar` / `bgcolor` / `alertcondition` / `input` / `alert`
  inside any function body
* no function assigns to a global (UDT-field and array mutation only)
* every function is defined before its first call site
* tuple arity matches at every destructure
* every identifier is declared before use; **no duplicate top-level
  declarations**
* no user function with side effects appears inside a ternary
* no `array.remove` inside an ascending `for`
* no drawing setter on an id that can be `na`
* no function parameter reassigned with `:=`
* main-body statement count: **1 606**

## 12. Test plan not yet executed

Phase 34 asks for a forensic test; it needs a chart, so it is a hand-off, not a
result. Priority order:

1. **5m XAUUSD** and **5m XAGUSD** — the intended instruments; confirm the
   machine reaches state 8 at all, and check the debug panel's block reason on
   bars where it stalls.
2. Turn on `Show state-machine debug panel` first, before changing any input.
3. Then 1m / 15m / 1H / 4H, watching for: state 8 never reached (windows too
   tight), `POI tier T3 below the minimum` dominating (tier grading too
   strict on that symbol), or `cooldown` dominating (`masterCd` too high).
4. Conditions to hunt specifically: liquidity grab, fake breakout,
   breakout + retest, deep FVG fill, multiple simultaneous pools, session
   transition, Silver Bullet window, HTF/LTF conflict, and a news-like spike
   (which is where the single-pass state compression in §9.12 shows up).
5. Realtime vs history: leave it on a live 1m chart for a session and confirm
   no mark that printed on close later disappears.
