# AUDIT — LQ-SD-PA v4 → v5 "Causal Trade Engine"

**Source audited:** `2.liquidty+supply-v4-trade-engine.pine` (3 167 lines, 177 753 bytes)
**Output:** `3.liquidty+supply-v5-trade-engine.pine` (3 876 lines, 217 561 bytes)
Date: 2026-09-08 · Pine v6 · v4 left byte-identical

> **NOT COMPILED.** No Pine compiler exists outside TradingView. This file has
> been statically verified (§9) but has never been loaded on a chart and has
> never been backtested. No accuracy or profitability claim is made anywhere
> in it or in this document. The alignment score is not a win probability.

---

## 0 · What v4 already got right, and was kept

v4's split — VISUAL ENGINE → CONFLUENCE ENGINE → TRADE ENGINE → SIGNAL, with
MODULE 15 as the only thing allowed to emit — is the correct shape and is
untouched. So are: the pool lifecycle (CREATED → VALIDATED → RAIDED → REACTION
→ CONSUMED), the protected-swing rebuild, the internal/external structure
split, the FVG lifecycle, the breaker/mitigation causal chain, the trendline
reaction counting, the location filter on CRT/turtle soup, the producer rank
arbitration, the SL hierarchy, the TP ladder, and all 37 alert names.

**Nothing was removed.** Every v2/v4 feature listed in §8 still exists. Where a
feature conflicted with causal integrity its ROLE changed (it became a
candidate that must clear the same chronology), never its existence.

---

## 1 · Critical bugs found in v4 and fixed

Each is tagged `V4-BUG-nn` in the source header so a TradingView error can be
bisected by tag.

### V4-BUG-1 — the state machine could walk the whole narrative in one candle

v4's `f_setupAdvance` was a straight run of independent tests inside ONE call:

```pine
if s.st == ST_NONE                 // → ST_CTX
if s.st == ST_CTX                  // → ST_TGT
if s.st == ST_TGT                  // → ST_RAID
if s.st == ST_RAID                 // → ST_POI
if s.st == ST_POI                  // → ST_MSS
if s.st == ST_MSS                  // → ST_DISP
if s.st == ST_DISP                 // → ST_FVG
if s.st == ST_FVG                  // → ST_ENTRY   ← only this one compared bars
```

Every trigger can be true on the same candle: HTF context is a standing
condition, "a liquidity target exists" is a standing condition, and a single
sweep candle can be the raid, tap the POI, close as a CISD (MSS), have a
displacement body, and be the third candle of an FVG. Only stage 7 → 8 had a
`bar_index > s.fvgBar` guard, so **0 → 7 in one bar was reachable**, and the
"machine" then rubber-stamped what was really a one-candle pattern.

**Fix.** Every stage stamps its own bar and the next stage compares them:

```
ctxBar < tgtBar < raidBar ≤ poiBar < mssBar < dispBar ≤ fvgBar < retestBar
```

plus a `moved` latch that permits at most one transition per call. The two `≤`
pairs are the only physically simultaneous ones and are named explicitly in the
code: the candle that raids the pool CAN be the candle that taps the POI, and
the displacement candle IS the third candle of the gap it leaves. `strictSeq`
(default on) additionally forces `ctxBar < tgtBar < raidBar`; turning it off
relaxes only those two context stages — raid < MSS < displacement < retest stay
strict in both settings.

### V4-BUG-2 — a new setup could claim an OLD raid

`f_findRaid(dir, freeOnly)` returned the freshest pool raided within
`sweepLook` bars whose `bound == 0`. The setup was armed by HTF context on a
LATER bar. Scenario A of the brief was therefore reachable exactly as written:

```
bar 100  SSL sweep
bar 103  setup created (HTF context turned bullish)
bar 104  setup claims the bar-100 raid
```

**Fix.** The machine no longer calls `f_findRaid` at all. `f_narrOk` re-derives
`raidBar > tgtBar > ctxBar ≥ bornBar` from stored fields at entry time and the
transition itself refuses a raid whose `raidBar` is not strictly after the
target lock ("raid pre-dates the target lock — retroactive claim refused").

### V4-BUG-3 — the target and the raid were unrelated objects

State 1 → 2 stored `tgtPx` from the nearest pool. State 2 → 3 then asked
`f_findRaid` for *any* raid on that side. Scenario B was reachable: target =
EQL at 1.0850, raid = an unrelated swing low at 1.0910, setup satisfied.

**Fix.** Pools carry a stable `id` (assigned from a global sequence held in a
one-element array, because a Pine function may mutate a global array but may
not assign to a global scalar). The setup locks the pool **object** as
`tgtPool` plus its `tgtId`, and state 3 fires only when THAT object reaches
`PS_RAID`/`PS_REACT`. `f_narrOk` re-checks `liqId == tgtId`. Price tolerance is
used only as a secondary POI-binding test (`poiBindAtr`), never as identity.

While still hunting, the target may be RE-SELECTED to the nearest live pool —
that is what price is actually working toward — but `tgtBar` restarts with it,
so re-selection can never be used to back-date a raid.

### V4-BUG-4 — a setup could be reborn on the candle that killed it

Every invalidation branch called `f_setupReset`, and the very next block in the
same call was `if s.st == ST_NONE` → re-arm. The setup died and was reborn on
one candle, which also silently reset its `setupLife` clock forever.

**Fix.** `f_setupReset` stamps `s.resetBar := bar_index`, and the arming stage
refuses to arm while `s.resetBar == bar_index`. The invalidation's own reason
string survives into the debug panel instead of being overwritten.

### V4-BUG-5 — the score was fed by global event contamination

`f_score` read `recentMssUp`, `recentDispUp`, `cisdUpBar`, `dispUpBar2`,
`raidExtLo`, `raidEqLo`, `sslStrong` — global "did this happen in the last N
bars" flags. None of them belonged to the setup being scored, so a dead setup's
CHoCH, a sweep on an unrelated pool and a displacement from an unrelated leg
all paid into one number, and "recent MSS + recent displacement + recent sweep
= strong setup" was literally the implementation.

**Fix.** `f_score` now takes 17 explicit parameters and reads no event memory
at all. For the state machine every one comes from the setup's own fields
(`liqQual`, `liqKind`, `pool.touches`, `poiTier`, `poiFresh`, `mssChoch`,
`dispBody`, `mssBar`, `dispBar`, `retestQ`). For the confluence producers they
come from that producer's own bound raid plus the chronology-checked structure
bars — and those producers must now pass `confGateLong/Short`, which is itself
ordered (below).

### V4-BUG-6 — the MSS could pre-date the raid, or BE the raid

State 4 → 5 accepted `chochUp or cisdUp` with no comparison to `s.liqBar`, and
because the whole chain could run in one call (V4-BUG-1) the "MSS" was very
often the sweep candle itself.

**Fix.** Three requirements:
* `mssBar > raidBar` (hard, both `strictSeq` settings);
* the level the shift broke must be RELEVANT — `sInt.evBarUp/evBarDn` (a new
  field pair on `Struct` recording the bar the broken pivot formed on, and
  `bullRunBar/bearRunBar` for the CISD case) must be no older than `mssWin`
  bars before the raid, so an ancient level cannot be re-broken to manufacture
  a shift;
* the level must be at least `MSS_MIN_SEP_ATR` (0.10·ATR) from the raid
  extreme — otherwise it is the sweep again under another name.

### V4-BUG-7 — displacement was "a big candle"

State 5 → 6 accepted any `dispUpBar` inside `dispWin`, including the MSS candle.

**Fix.** `dispBar > mssBar` strictly, plus the close must clear the level the
MSS broke (`close > s.mssLvl`) AND leave the POI it came from
(`close > s.poiTop`). Together with the existing ATR-normalised body and
strong-close test that is expansion with structural meaning, not size alone.
The body is stored as `dispBody` (in ATR) and scored.

### V4-BUG-8 — the FVG did not belong to the displacement

State 6 → 7 accepted any `bullFVG` within `fvgWin` (default **10**) bars of the
displacement. A gap ten candles later, from a completely different leg, was
locked and labelled "the displacement's FVG".

**Fix.** The displacement candle must be one of the three candles that FORM the
gap: `bar_index - s.dispBar ≤ FVG_OWN_MAX` (2). The gap must also clear
`fvgMinAtr` (0.10·ATR) — a gap thinner than that has a 50 % level inside the
spread on most instruments. If the expansion leaves no gap the setup falls back
to state 5 and waits for the next expansion after the SAME MSS, rather than
being destroyed; a valid narrative is not invalidated by one gapless candle.

### V4-BUG-9 — every HTF read was the bar that was still being built

v4 removed v2's `[1]` from all four `lookahead_off` security calls (that was
v4's own "BUG-15"). **`lookahead_off` does not mean "the last closed HTF bar"**
— it means "no future data", and the forming HTF candle is not future data. So
`f_htfCtx`, `f_htfPoi`, `f_crtTbsHtf` and `f_bias` all read a bar that changed
under the script as it built: a repainting HTF bias. It was worse for the HTF
CRT: `newHtfBar` fires on the FIRST chart bar of a new HTF candle, so the
"confirmation candle" of the pattern was an HTF candle roughly one chart bar
old.

**Fix.** Every HTF read is now `expr[1]` inside the request with
`lookahead = barmerge.lookahead_on` — the only combination that is both
leak-free and stable. The `[1]` steps back to the bar that has closed;
`lookahead_on` then serves that closed bar from the first chart bar of the new
HTF candle instead of an entire HTF candle later. See §3.

### V4-BUG-10 — a one-tick poke graded as a liquidity raid

`f_poolScan` needed only `high > p.px and close < p.px`. Depth was never
measured and every raid was equal.

**Fix.** A raid needs `raidMinAtr` (0.10·ATR default) of real penetration.
Below that the bar is recorded as a **test**: it raises the pool's `touches`
(price respected the level) and the pool stays hunting. Above it, the raid is
graded (§2.2). Grade is a hard requirement for A+ and a soft term elsewhere.

### V4-BUG-11 — POI tier was frozen at creation

`f_gradeZone` ran once inside `f_newZone`. A T1 demand zone stayed T1 after the
HTF flipped bearish, after external structure broke down, and after 90 % of it
had been eaten.

**Fix.** `f_regrade(z)` runs on every zone on every confirmed bar. It starts
from `tier0` (the creation grade, stored separately) and can only make it
worse: ≥50 % mitigated → never better than T2 · fully filled → T3 (visual
only) · HTF now opposes → one tier worse · structure now opposes → one tier
worse. The box text follows. The machine additionally kills a setup whose POI
has been re-graded below `minTier` ("POI spent or re-graded below the minimum
tier").

### V4-BUG-12 — RR and opposing liquidity were computed AFTER the signal

v4's MODULE 16 resolved SL/TP *after* MODULE 15 had already emitted, so a
signal whose structural stop was 3·ATR wide with un-raided liquidity 0.4·ATR
overhead still printed, drew a full TP ladder and fired its alert.

**Fix.** The risk primitives moved to a new MODULE 14B (they are function
definitions, so this changes nothing except that the engine can ASK before it
decides). MODULE 15 now computes SL → risk → TP ladder → RR → opposing
liquidity BEFORE the gates, and MODULE 16 only selects the winning side's
numbers for drawing.

### V4-BUG-13 — A+ was two conditions

```pine
aPlusLong = prodL > 0 and prodL <= PR_MACH and tierL == 1
```

No RR, no raid quality, no chronology check, and `tierL` was the frozen
creation tier of V4-BUG-11. See §6 for the v5 definition.

### V4-BUG-14 — dedupe was a bar cooldown only

`masterCd` bars after an entry, the same pool, the same POI and the same
structure shift could each produce another entry. `pool.bound` was set but
never consulted on re-entry, and the zone was marked spent only for the S/D
producer.

**Fix.** Three independent memories per direction — `lastPoolId`, `lastPoiId`,
`lastMssBar` — plus a permanent `pool.spent` flag and `zone.signaled`. One
liquidity event → one POI → one execution. The machine will not even select a
POI that matches `lastPoiId`, and a spent pool can never become a target again.

### V4-BUG-15 — the confluence producers had no chronology at all

```pine
confGateLong = sslInPlay and (recentMssUp or mssUp) and recentDispUp
```

Three independent global flags in ANY order, so "displacement, then a shift,
then an old sweep that is still in play" passed as a liquidity reversal.

**Fix.** `confGateLong/Short` now requires the same ORDER the machine does:
`raidBar < mssBar ≤ dispBar`, all still live. S/D retest, CRT, turtle soup,
trendline sweep and the four price-action patterns are all gated on it.

### V4-BUG-16 — counter-trend trades were indistinguishable from continuations

```pine
htfCtxLong = not needHtfAlign or htfDir > 0 or (not na(htfPd) and htfPd <= 0.5) or not na(hPoiBTop)
```

An OR chain: a long taken while the HTF was bearish, merely because price was
in the lower half of the HTF range, was classified exactly like a long taken
with the HTF.

**Fix.** Two separate verdicts. **CONTINUATION**: the closed HTF agrees and
price is on the correct side of the HTF range (or in an HTF POI).
**REVERSAL**: the closed HTF disagrees — allowed only from an HTF premium /
discount EXTREME (`PD_EXTREME`, 25 %) or an opposing HTF FVG POI, only when
`allowRev` is on, tagged `REVERSAL` on the label and in the reason code, and
capped at grade B unless it shows a CHoCH-grade shift.

---

## 2 · Logic improvements

### 2.1 Event ownership

Every setup now carries the identity and the bar of everything it claims:

```
id · bornBar · ctxBar · reversal
tgtId  tgtPx  tgtTag  tgtKind  tgtBar  tgtPool
liqId  liqPx  liqBar  liqExt  liqStrong  liqKind  liqTag  liqQual  liqDepth  pool
poiId  poiTop poiBot  poiTier  poiFresh  poiIsHtf  poiBar  poiZone
mssBar mssChoch mssLvl
dispBar dispBody dispExt
fvgBar fvgTop fvgBot fvgH
retestBar retestPen retestQ  sbWindow  resetBar
```

`f_narrOk(s)` re-derives the entire causal chain from those fields at emission
time, **independently of the transitions that produced it**, and is a hard gate.

### 2.2 Raid quality grading (§11)

Measured on the raid candle, in ATR:

| Grade | Condition |
|---|---|
| **A** | penetration ≥ `raidDeepAtr` (0.35·ATR) **and** close back inside past the candle midpoint |
| **B** | one of the two, not both |
| **C** | shallow and weak |
| — | penetration < `raidMinAtr` → not a raid at all; counted as a test |

A raid that later produces a displacement or MSS away from the level is
promoted C → B once. Grade A is mandatory for A+.

### 2.3 Pool quality (§12)

`Pool.touches` counts reactions and tests with `eqMinSep` bars of separation, so
adjacent bars resting near a level cannot inflate it. `poolMinTouch` (default 0)
can require prior respect before a pool may be hunted at all. EQH/EQL keep v4's
ATR tolerance + time separation + reaction-at-both-legs construction and are
registered at the MEAN of the pair. Pool class (external/PD/session · EQ ·
minor swing) and touch count are separate score terms.

### 2.4 FVG retest quality (§10)

A touch is not an entry. Entry requires **penetration ≥ `retestDepth`** AND a
**close back through the gap's 50 %** AND a rejection (confirmation candle,
IFC, or a strong close). The penetration is stored and graded:
touch (1) / 50 % (2) / deep ≥80 % (3), and feeds the EXECUTION score layer. A
full trade-through invalidates the setup outright.

### 2.5 Opposing liquidity and realistic RR (§17, §18)

`f_oppLiq` returns the nearest **meaningful** obstacle: a live opposing pool
that is external / PD / session / EQ liquidity or a minor swing price has
already respected, or an opposing POI that is still fresh (<50 % mitigated) and
graded T1/T2. Un-validated minor pivots are excluded — they sit everywhere and
would cap every trade at nothing.

RR is then **realistic**, not theoretical:

```
rr = min( (TP2_ladder − entry) / risk , distance_to_opposing_liquidity / risk )
```

This matters: in ladder mode `TP2` can never be below `rrMult × risk`, so an
unclamped RR floor would pass by construction. With the clamp, a 3R target
sitting behind an un-raided pool 0.8R away scores 0.8R and is refused. Floors
are configurable per grade (A+ 2.0 · A 1.5 · B 1.2). Insufficient room
downgrades one step by default, or blocks outright with `oppLiqHard`.

### 2.6 Session narrative (§20)

`sesStoryL/S` recognises London taking Asia's extreme, New York (or a Silver
Bullet window) taking London's, a session-pool raid inside a Silver Bullet
window, and a PDH/PDL raid inside London or New York. It is a CONTEXT score
term, not a permission gate — the killzone/Silver Bullet filters are unchanged
and still optional.

### 2.7 Volatility normalisation (§21)

Everything that can be scaled is scaled by ATR: raid depth (`raidMinAtr`,
`raidDeepAtr`), displacement (`dispFactor`, `structDisp`, `crtDispAtr`), FVG
height (`fvgMinAtr`), zone height (`maxZoneAtr`), MSS separation
(`MSS_MIN_SEP_ATR`), POI binding (`poiBindAtr`), stop distance (`minRiskAtr`,
`maxRiskAtr`, `atrStopMult`, `SL_PAD_ATR`), level proximity (`NEAR_LVL_ATR`).
No absolute price, pip or point constant exists anywhere in the file, so XAGUSD,
XAUUSD, FX and crypto behave the same way in units of their own volatility.

---

## 3 · Repainting audit (§14, §30)

**Confirmed / non-repainting**

| Calculation | Why |
|---|---|
| Every state transition, pool lifecycle, zone lifecycle, structure event | `f_setupAdvance`, `f_poolScan`, `f_structUpdate` each carry `if confirmed` INSIDE the body and are called unconditionally (Pine evaluates both branches of a ternary, so gating the CALL would still mutate on every tick) |
| `f_bias` (all 5 timeframes), `f_htfCtx`, `f_crtTbsHtf`, `f_htfPoi` | `expr[1]` + `lookahead_on` = the last CLOSED HTF bar. Cost: an HTF event surfaces on the first chart bar after the HTF candle closes. That delay is real and is the honest price of not repainting |
| PDH / PDL | `[high[1], low[1]]` + `lookahead_on` — only the completed previous day is ever read (unchanged from v4) |
| Pivots (`ta.pivothigh/low`) | Confirmed `pivLen` / `extPiv` bars late by construction; the delay is accepted, never worked around |
| Signals, labels, alerts, SL/TP drawings | All downstream of `confirmed` state |

**Deliberately realtime / developing**

| Calculation | Effect |
|---|---|
| The `⋯` developing preview (`showDev`, off by default) | Drawn on the unclosed bar, dim, changes no state, raises no alert, and can disappear before the close — which is the point of drawing it dim |
| Session high/low tracking while a session is open | The frozen level handed to the pool registry is stamped only on the session close under `confirmed` |
| Dashboard / debug tables | Redrawn on `barstate.islast` for readability; they display state, they do not create it |

No future-bar references, no `lookahead_on` without a compensating `[1]`, no
retroactive signal generation, no historical signal that can change because
later information arrived.

---

## 4 · State-machine audit (§35 D)

```
        ST_NONE  0
           │  htfCtx (CONTINUATION or REVERSAL)   ·  refused if resetBar == this bar
           ▼
        ST_CTX   1        stamps ctxBar
           │  a live pool exists on the correct side, touches ≥ poolMinTouch
           │  requires bar_index > ctxBar        (strictSeq)
           ▼
        ST_TGT   2        stamps tgtBar, tgtId, tgtPool   (re-selectable, clock restarts)
           │  THAT pool reaches PS_RAID / PS_REACT
           │  requires raidBar > tgtBar, pool unbound, not spent, raid not stale
           ▼
        ST_RAID  3        stamps liqBar, liqId, liqQual, liqExt
           │  HTF FVG POI tap, or the best eligible zone CONTAINING liqExt
           │  requires poiBar ≥ liqBar          ← the only same-bar pair here
           ▼
        ST_POI   4        stamps poiBar, poiId, poiTier, poiZone
           │  CHoCH (or CISD unless mssNeedChoch), level formed near the raid,
           │  ≥ MSS_MIN_SEP_ATR from the raid extreme
           │  requires mssBar > liqBar  AND  mssBar ≥ poiBar
           ▼
        ST_MSS   5        stamps mssBar, mssLvl, mssChoch
           │  displacement body + strong close + close beyond mssLvl + close out of POI
           │  requires dispBar > mssBar
           ▼
        ST_DISP  6        stamps dispBar, dispBody, dispExt
           │  an FVG whose three candles include the displacement candle
           │  requires fvgBar − dispBar ≤ 2, height ≥ fvgMinAtr
           │  (no gap in 2 bars → fall back to ST_MSS, do not destroy the setup)
           ▼
        ST_FVG   7        stamps fvgBar, fvgTop, fvgBot, fvgH
           │  penetration ≥ retestDepth + close back through 50 % + rejection
           │  requires retestBar > fvgBar
           ▼
        ST_ENTRY 8   →  f_narrOk re-derives the whole chain  →  MODULE 15 hard gates
           ▼
        ST_DEAD  9        cleared on a LATER bar, which stamps resetBar
```

**How same-bar skipping is prevented — three independent mechanisms:**

1. **Bar comparisons.** Each stage compares `bar_index` (or the event's own
   bar) with the previous stage's stamp. Six of the seven transitions demand a
   strictly later bar.
2. **The `moved` latch.** At most one transition per call. The only two blocks
   that may run after `moved` is set are guarded by the *specific* condition
   that makes them physically simultaneous — `s.liqBar == bar_index` for
   raid→POI and `s.dispBar == bar_index` for displacement→FVG — so the chain
   can extend by exactly one extra stage and only in those two places.
3. **`f_narrOk` at the end.** An independent re-derivation of the entire order
   from the stored fields, run as a hard gate before emission, so even a future
   edit that broke a transition guard could not produce an out-of-order entry.

Longest legal single-bar advance: 2 stages (raid+POI, or displacement+FVG).
Minimum bars from arming to entry: **5**.

---

## 5 · Hard gates vs soft score (§16)

**HARD — any one blocks the trade**

| Gate | Variable |
|---|---|
| Narrative integrity (ownership + chronology), machine producers | `hNarr` / `f_narrOk` |
| Producer exists | `prod > 0` |
| Per-direction cooldown | `longCdOK` / `shortCdOK` |
| Duplicate pool / POI / MSS | `hDedup` / `f_dedupeOk` |
| Bias filter · killzone · scheduled volatility window · Silver-Bullet restriction · structure filter | `baseLongOK` / `baseShortOK` |
| Live POI tier ≤ `minTier` | `hTier` |
| Realistic RR ≥ the floor for the grade | `hRr` |
| Opposing-liquidity room (only when `oppLiqHard`) | `hRoom` |
| Grade ≥ `minGrade` | `hGrade` |
| Score ≥ `minScore` (0 = off) | `hScore` |
| Equal-rank cross-direction conflict | `bothTie` mutes BOTH |

**SOFT — ranks what already passed, never creates a grade**

CONTEXT 25 (HTF agreement 10 · external structure 6 · premium/discount 5 ·
session narrative 4) · LIQUIDITY 25 (raid grade 12 · pool class 8 · pool
quality 5) · POI 20 (HTF POI 6 · freshness 5 · live tier 5 · OTE 4) ·
TRIGGER 20 (MSS grade 8 · displacement strength 6 · MSS ≠ displacement bar 3 ·
CISD independent of the MSS 3) · EXECUTION 10 (retest quality 6 · rejection 4).

---

## 6 · The v5 A+ definition (§35 F)

`gradeL/S == GR_AP` requires **all** of:

1. the producer is the state machine (rank FEM or MACH) — no confluence
   producer can ever be A+;
2. `f_narrOk` true: raid hit the LOCKED target pool by id, and
   `ctxBar < tgtBar < raidBar ≤ poiBar < mssBar < dispBar ≤ fvgBar < retestBar`
   with `raidBar > bornBar` and `fvgBar − dispBar ≤ 2`;
3. the POI's **live** tier (after re-grading) is T1;
4. the raid graded **A** — deep penetration with a real close-back rejection;
5. if the setup fights the closed HTF (REVERSAL), the shift must be a CHoCH,
   not a CISD;
6. realistic RR ≥ `rrAplus` (2.0 default), where realistic means clamped by the
   distance to the nearest meaningful opposing liquidity;
7. and then every hard gate in §5 as well.

A+ is downgraded to A if the opposing-liquidity room is under `oppLiqMult × risk`
(unless the hard-block option is on, in which case it is refused).

**Grade A**: narrative intact (or a confluence producer with full chronology),
live tier ≤ T2, raid grade ≥ B, CHoCH if reversal, RR ≥ `rrA`.
**Grade B**: everything else that still clears every hard gate, RR ≥ `rrB`.

---

## 7 · Scenario validation (§34)

Traced against the implementation, not against a chart.

| # | Scenario | v4 | v5 | Mechanism |
|---|---|---|---|---|
| A | Old raid → new setup | claimed | **refused** | `raidBar > tgtBar > ctxBar ≥ bornBar`, re-checked by `f_narrOk` |
| B | Target A, raid B | accepted | **refused** | machine binds `tgtPool` object; `liqId == tgtId` |
| C | MSS before the raid | accepted | **refused** | `mssBar > liqBar` hard, both `strictSeq` settings |
| D | Displacement before the MSS | accepted | **refused** | `dispBar > mssBar` hard |
| E | FVG unrelated to the displacement | accepted (up to `fvgWin` = 10 bars) | **refused** | `fvgBar − dispBar ≤ 2` |
| F | POI invalidated | reset **and re-armed same bar** | **reset, no same-bar re-arm** | `resetBar` stamp |
| G | HTF candle still developing | used as confirmed bias | **not used** | `expr[1]` + `lookahead_on` everywhere |
| H | Opposing liquidity too close | ignored (SL/TP came after the signal) | **downgraded, or blocked** | `f_oppLiq`, RR clamp, `oppLiqHard` |
| I | Same POI touched repeatedly | re-signalled after `masterCd` | **one execution** | `zone.signaled`, `lastPoiId`, `pool.spent`, `lastMssBar` |
| J | Everything aligned in order | printed, often A+ on thin evidence | **A+ only with §6 satisfied** | grade + hard gates |

---

## 8 · Features preserved (§25)

Supply/Demand zones · FVG (+ lifecycle: fresh / touched / 50 % / filled) ·
rejection blocks · breaker blocks · mitigation blocks · order blocks (via the
displacement-origin zones) · liquidity pools · EQH/EQL · swing liquidity ·
session H/L liquidity · PDH/PDL · internal and external structure · BOS ·
CHoCH · MSS · CISD · IFC · liquidity runs · protected swings · order-flow
zigzag · dealing range · premium/discount halves · OTE 62–79 % · CRT ·
turtle soup · HTF CRT/TBS · HTF FVG POI · FEM · dynamic trendlines · the four
price-action setups (breakout rejection trap, pin-bar trap, inside-bar
breakout, doji reversal) · killzones · Silver Bullet · scheduled volatility
windows · 00:00 and 08:30 opening prices · MTF dashboard · SL hierarchy ·
TP ladder · debug panel · all 37 alerts with their v2/v4 names.

**Input compatibility (§31).** No input was renamed, removed or had its default
changed. Twelve inputs were ADDED: `minGrade`, `strictSeq`, `allowRev`,
`raidMinAtr`, `raidDeepAtr`, `poolMinTouch`, `fvgMinAtr`, `dedupePool`,
`dedupePoi`, `dedupeMss`, `rrAplus`/`rrA`/`rrB`, `useOppLiq`, `oppLiqMult`,
`oppLiqHard`, `dbgVerbose`. Two tooltips were rewritten where they described
behaviour that changed. Colours, label styles and drawing styles are unchanged
except that the entry label now carries the grade, the raid quality and the RR
instead of a bare "A+" prefix.

---

## 9 · Static verification and budgets

Checked mechanically (`check.py`, `fields.py` in the session scratchpad):

* bracket balance — clean
* indentation 4k / 4k+1, continuation lines follow an open operator — clean
  (the 12 reported "violations" are string-stripping artefacts and are present
  identically in v4)
* function defined-before-called — clean
* call arity vs definition, tuple destructure arity vs return arity — clean
* UDT field access vs declared fields, scope-aware — **0 bad accesses**
* no `plot` / `input` / `alertcondition` inside a function body — clean
* no function assigning to a global scalar — clean
* no duplicate top-level declarations — clean
* na-object dereference: every `obj.field` is either on a `var` object that is
  never na, or inside an `if` that proved it exists, or behind one of the four
  guard helpers (`f_poolSpent`, `f_poolTouch`, `f_zoneId`, `f_zoneDead`).
  Pine evaluates both ternary branches and does not reliably short-circuit
  `and`, so this class was swept deliberately.

| Budget | v4 | v5 | Limit |
|---|---|---|---|
| Output slots (4 plot + 12 plotchar + 5 bgcolor + 37 alertcondition) | 58 | **58** | 64 |
| Main-body statements (CE10295) | 780 | **879** | a sibling failed at 2 515, passed at 2 107 |
| `request.security` sites | 5 | **5** | 40 |
| Compiled-token proxy (comments stripped, string = 1 token) | 22 024 | **27 023** (+22.7 %) | CE10117 cap 100 256 real tokens |

**The token proxy is the one real risk.** The proxy → real-token mapping has
never been measured for this lineage, so the CE10117 margin is unknown. If
TradingView rejects the file with CE10117, remove in this order — each is
self-contained and none breaks the causal engine:

1. the four price-action producers (`showS1`–`showS4`, MODULE 11's ①②③④ blocks
   and their two `alertcondition`s) — they are only reachable in
   "All engines (legacy)" mode anyway;
2. the dynamic trendline engine (MODULE 10 + `PR_TL`);
3. the verbose debug rows (`dbgVerbose` and `f_dbgTxt`'s ten calls);
4. the order-flow zigzag (`showOF` and its line array);
5. the HTF CRT / turtle-soup producers (`useHtfCrt`, `f_crtTbsHtf`, one
   `request.security`).

---

## 10 · Known limits, stated rather than hidden

* **Not compiled, not backtested.** Both facts are absolute.
* **The `[POI]`, `[TRIG]` and `[LIQ]` alerts still fire on non-entry events.**
  §29 asks for entry-only alerts; §31 asks that existing alert names keep
  working. The `[SIGNAL]` family is now strictly post-hard-gate, and the other
  three families are kept, and kept clearly prefixed, so alerts users already
  created do not silently die. Anyone wanting entry-only alerts should
  subscribe to `[SIGNAL]` conditions only.
* **The displacement must close outside the POI.** On a very wide HTF FVG POI
  that is a demanding test and will cost some legitimate setups. It is the
  literal reading of "movement away from POI" and was chosen deliberately over
  a softer midpoint test.
* **`FVG_OWN_MAX` is a constant, not an input.** Loosening it past 2 would
  re-open V4-BUG-8, so it is intentionally not user-tunable.
* **REVERSAL setups are permitted.** They are tagged, capped at grade B without
  a CHoCH, and require an HTF extreme — but they are not forbidden. Turn
  `allowRev` off for continuation-only behaviour.
* **`f_gradeZone`'s creation tier still reads global recency flags.** That is a
  snapshot at creation, and `f_regrade` can only make it worse afterwards, so
  contamination there cannot promote a zone — but the creation tier is not
  setup-owned and is not claimed to be.
* Signals evaluate on CLOSED bars. Use "Once per bar close" alerts.
---

## 11 · v5.2 Phase B (2026-09-08) — registry identity + risk/lifecycle consistency

A forensic re-audit of the v5.1 file found five defects that survived Phase A.
All five are fixed in a NEW generation file,
`4.liquidty+supply-v5.2-trade-engine.pine` (title bumped to "LQ-SD-PA v5.2
CTE" so both versions can sit on one chart), tagged `V5.2-B1` … `V5.2-B5` in
the source. File 3 is the unmodified v5.1 and stays frozen, per the lineage
rule that every generation is a new file. Outputs unchanged at 58/64; no new
inputs, no new alerts; all 18 patches applied by exact-match script.

* **B1 — engineered/external pools could not register (HIGH).** `f_poolPush`
  refused any pool within `eqTol·ATR` of a live same-side pool. Every EQH/EQL
  (the mean of two pivots whose first pivot already registered as a SWING pool
  ≤ 0.075·ATR away at the default 0.15 tolerance) and nearly every EXT pivot
  (the same price as its earlier internal pivot) is exactly that, so the
  registry almost never held `PK_EQ` or `PK_EXT` pools. Downstream: the
  `raidEq*`/`raidExt*` classes rarely fired, the CRT/TBS location filter lost
  two legs, the liquidity score paid 3 instead of 6–8, and the TP ladder's
  external scope was empty (so `hTgt` blocked trades with real targets). Fix:
  a duplicate that outranks a live **un-raided** SWING pool now upgrades that
  pool in place — kind, tag, px, +touch — preserving id, binding, bornBar and
  touch history. A raided pool is never re-classified.
* **B2 — double stop padding (MED).** The CRT/TBS/TL/PA/HTF producers handed
  `f_sl` levels already padded by `SL_PAD_ATR`, and `f_sl` pads every
  candidate again: every confluence stop was double-padded, understating RR.
  Producers hand raw levels now; `f_sl` owns the pad (the machine's raw
  `liqExt` was already correct).
* **B3 — a transiently-blocked machine entry destroyed its own narrative
  (MED).** State 8 refused by cooldown / session / RR-this-bar / room /
  target / grade / arbitration was never consumed and the state-9 cleanup
  reset it. Fix: MODULE 15 reverts such a setup to state 7 (retest fields
  cleared) so it may retest again inside `retestWin`. Permanent verdicts —
  failed narrative integrity, dedupe — remain terminal.
* **B4 — post-raid reclaim was not a break (MED).** `f_poolScan` marked a
  post-raid close back through the level `PS_DONE` without stamping `brkBar`,
  so pool-break flags missed it and the machine kept hunting an MSS off a
  failed sweep until the deeper close-beyond-the-wick test. Every
  close-beyond path stamps `brkBar` now (new na-safe `f_poolBrkBar` helper),
  and the machine invalidates: "raid level reclaimed".
* **B5 — hardening.** `f_narrOk` now demands `mssBar > poiBar` (the machine
  can never produce the equality). Dashboard locals `int freshD/freshS`
  renamed `freshDZ/freshSZ` — the latter shadowed the global `bool freshS`.

### Known-and-left after Phase B (do not re-report)

* `f_score`'s independent-CISD term (3 soft points) still reads the global
  `cisdUpBar`/`cisdDnBar` — a purity violation of V4-BUG-5's claim, but it can
  gate nothing (soft score, `minScore` default 0) and fixing it costs a
  signature change across both callers.
* `f_oppLiq` counts opposing zones at `state < 2` while the TP clamp uses
  `f_nextZone`'s `state < 3` — a half-mitigated wall caps targets but does not
  count as a room obstacle. Defensible: a 50 %-eaten zone is a weaker
  obstacle than an untouched one.
* With `tpClamp` ON (default) the soft room-downgrade in `f_grade` is largely
  redundant — a wall closer than 1R clamps TP2 below `rrB` and the RR gate
  blocks first. The downgrade only matters with `tpClamp` OFF.
* "R multiple" TP mode still makes the RR gate inert, by request (v5.1-A1).

---

## 12 · v5.3 Phase C (2026-09-08) — live tier at the grade + honest docs

A Phase-C forensic re-audit of the v5.2 file (excluding everything §11 lists
as known-and-left) found one behavioural defect, one silently dead code path
and three documentation lies. All are addressed in a NEW generation file,
`5.liquidty+supply-v5.3-trade-engine.pine` (title bumped to "LQ-SD-PA v5.3
CTE"), tagged `V5.3-C1` … `V5.3-C5`. File 4 is the unmodified v5.2 and stays
frozen. Outputs unchanged at 58/64; no new inputs, no new alerts; statically
verified (brackets balanced, helper defined before called, 37/12/4/5 output
counts intact).

* **C1 — the grade read a FROZEN POI tier (MED).** `s.poiTier` was stamped
  once at the stage-4 POI tap and never refreshed, while `f_regrade` decays
  every zone every confirmed bar (V5-6). Up to `retestWin` (25) bars later the
  entry was graded — and `hTier` gated — on the tier the zone HAD: a T1 that
  fell to T2 (HTF flipped / structure flipped / half eaten) still bought an
  A+, which §6.3 of this audit explicitly promised it could not. Fix: a
  na-safe `f_zoneTier` accessor plus a per-confirmed-bar refresh of
  `s.poiTier` from the live zone inside `f_setupAdvance`'s invalidation
  block, so the grade, the `hTier` gate and the debug panel all read the
  re-graded tier. `f_zoneDead` still kills the setup outright when the live
  tier falls below `minTier`. HTF FVG POIs have no re-grade engine and keep
  their fixed tier 1 (known limit, below).
* **C2 — legacy producers silently dead at defaults (MED, behaviour kept).**
  The trendline and price-action producers never assign a tier, so they carry
  tier 3 — and the default `minTier` = 2 hard-blocks tier 3, so "All engines
  (legacy)" added producers that could never emit and nothing said so.
  Behaviour KEPT deliberately (quality over frequency); the `entryMode` and
  `minTier` tooltips now state the interaction: legacy producers trade only
  with `minTier` = 3.
* **C3 — MODULE 11 header claimed no self-consumption (LOW).** The trap
  watch latches `wFired` on its own candidate — one candidate per armed
  watch, even if the trade engine blocks it. That IS the anti-duplicate
  choice; the comment now says so instead of denying it.
* **C4 — tpClamp tooltip over-claimed (LOW).** It said all three rungs are
  capped in every mode; the clamp exists in Liquidity-ladder mode only. The
  tooltip now carries the scope ("Next level": TP2 is itself the structural
  target, TP3 aspirational and unclamped; "R multiple": synthetic by request).
* **C5 — pool-scan ordering comment inverted (LOW).** It claimed
  scan-after-registration prevents same-bar raids of a new level; the
  ordering does the opposite (it EXPOSES new pools to this bar's scan) —
  pivot construction is what prevents the SWING/EQ case, and a same-bar raid
  of a freshly frozen session/PDH-PDL level is a real event. Rewritten.

### Known-and-left after Phase C (do not re-report)

* `poiFresh` stays frozen at the tap — 5 soft score points only, and "was the
  POI fresh when tapped" is arguably the right semantic.
* A second, deeper wick into an already-raided pool does not upgrade the
  pool's raid grade or reset staleness — raid identity is the FIRST raid, by
  design (only `raidExt` extends).
* An HTF FVG POI has no dedupe id (`poiId` = 0) and no live re-grade — FEM
  re-entries off the same HTF POI are still bound by the pool and MSS
  dedupes, which require a genuinely new raid and a new shift.
* Everything in §11's list still stands.

---

## 13 · v5.4 Phase D (2026-09-08) — runtime ("heavy script" warning)

v5.3 COMPILED and loaded on TradingView — the first on-chart confirmation in
this lineage — but drew the "Heavy script … close to your plan's runtime
limit (20s)" warning. Phase D is a pure performance pass in a NEW generation
file, `6.liquidty+supply-v5.4-trade-engine.pine` (title "LQ-SD-PA v5.4 CTE"),
tagged `V5.4-D1`/`V5.4-D2`. **No signal, gate, grade, input, alert or drawing
change** — every value the engine trades on is bit-identical to v5.3. File 5
frozen. Statically verified: brackets balanced, all 4 re-signatured functions
arity-checked at every call site, outputs unchanged at 58/64.

* **D1 — zone geometry cached.** `box.get_top`/`box.get_bottom` are
  drawing-API reads and sat inside every per-bar loop: the zone update loop,
  the next-POI scan, the machine's POI selection, `f_nextZone`, `f_oppLiq`
  and four overlap scans — dozens of API reads per bar. A zone's box
  coordinates never change after creation (verified: no `box.set_top`/
  `box.set_bottom` exists; flips restyle, they do not move), so `Zone` gained
  `top`/`bot` fields stamped once in `f_newZone`, and all fourteen hot-path
  reads use them. The two getters left are in the `barstate.islast` dashboard
  highlight loop (zero historical cost).
* **D2 — the risk stack no longer scans every bar.** `f_tp` (→ `f_nextPool`
  ×2 + `f_nextZone` + `f_oppLiq`) plus the standalone `f_oppLiq` room check
  ran unconditionally for BOTH directions on EVERY bar — ~12 full pool+zone
  scans per bar pricing signals that exist on almost none of them. A `go`
  flag (`prodX > 0 or barstate.islast`) is now passed INTO the scanners (the
  lineage pattern — never a ternary around the call, Pine evaluates both
  branches) and gates the loops. Correctness: `okLong`/`okShort` already
  require `prodX > 0`, and the only other consumers of RR / room / TP —
  dashboard and debug panel — draw on the last bar, where the gate is true.

**What Phase D cannot fix:** the 9 `request.security` instances (5 bias TFs,
context, PDH/PDL, HTF CRT/TBS, HTF POI) are a fixed cost — Pine forbids
conditional `security` calls. If the warning persists on a slow symbol/TF,
apply §9's ranked removal levers (price-action producers → trendlines →
verbose debug rows → order-flow zigzag → HTF CRT/TBS, which also removes one
security call). Chart-side mitigations that change nothing structural:
`showOF` off, structure chips off, `showDev` off, lower `poolMaxN`/`maxZones`.
Measure with TradingView's Pine Profiler before removing anything.

---

## 14 · v5.4 → PHASE E — FORENSIC RE-AUDIT (2026-09-08) · **FINDINGS ONLY, NOT YET IMPLEMENTED**

Target: `6.liquidty+supply-v5.4-trade-engine.pine` (4 226 lines, 242 794 bytes).
Scope: complete file. Everything §11 / §12 lists as *known-and-left* was excluded
from re-reporting. No code has been changed by this pass — file 6 is byte-identical
to the version audited here.

### 14.0 · What re-verified CLEAN

* **Bracket balance** — `()` / `[]` / `{}` all zero, no negative excursion.
* **Array-loop safety** — all 15 `for i = 0 to array.size(x) - 1` sites sit behind a
  `size > 0` guard (including the one inside `while cnt > maxZones`, where `cnt >= 2`
  is itself the proof). No reachable descending-underflow `for i = 0 to -1`.
* **Output budget** — 4 plot + 12 plotchar + 5 bgcolor + 37 alertcondition
  = **58 / 64**, unchanged.
* **request.security** — 5 call sites, 9 instances (5 bias TFs + context + PDH/PDL
  + HTF CRT/TBS + HTF POI). Every one is `expr[1]` + `lookahead_on`.
* **No intrabar state mutation.** Every producer that can reach `finalLong` /
  `finalShort` is itself `confirmed`-gated (machine, S/D, CRT, TBS, HTF CRT/TBS,
  trendline, patterns 1-4), so MODULE 15's consumption block — which is NOT wrapped
  in `if confirmed` — can only ever run on a closed bar. Verified producer by
  producer. The only intrabar writes in the file are `f_sesTrack`'s running session
  extremes (frozen on a confirmed bar) and the 00:00 / 08:30 opens (a bar's open is
  fixed on its first tick). Repaint-safe.
* **No stuck state.** Every stage has a bounded exit: ST_CTX / ST_TGT by `setupLife`,
  ST_RAID by `mssWin` from `liqBar`, ST_POI by `mssWin` from `poiBar`, ST_MSS by
  `dispWin`, ST_DISP by `FVG_OWN_MAX` (revert to ST_MSS or reset), ST_FVG by
  `retestWin`, ST_ENTRY / ST_DEAD on the next bar. No setup can be permanently locked.
* **Setup id collision impossible** — `bar_index*2 + 1` (long) and `+ 2` (short) are
  opposite parity, and only one setup per direction is ever live, so `pool.bound`
  cannot be claimed by the wrong owner. Pools are side-partitioned, so the two
  directions can never contend for one pool.
* **All pool BREAK paths stamp `brkBar`** with `bar_index > liqBar`, so the V5.2-B4
  reclaim invalidation cannot be silently bypassed.
* **Objects survive `array.remove`.** `s.pool` / `s.poiZone` are references; pruning
  the registry does not create an na-dereference.

### 14.1 · Defect table

| ID | Location | Bug | Market consequence | Severity |
|---|---|---|---|---|
| E1 | `f_poolScan`, reaction block (~1493) | The RAID to REACT transition is not compared to `raidBar`, so **the raid candle can be its own reaction**, and that path upgrades the raid grade `RQ_C` to `RQ_B`. Reachable when the raid bar is also a global `mssDn` / `mssUp` (a `dispXBar` implies `rej`, so displacement cannot upgrade a C). | A shallow, weakly rejected poke is re-graded B off an *unrelated* internal CHoCH / CISD on the same candle, and grade **A** then becomes reachable (`f_grade` needs `rq >= RQ_B`). This is the V4-BUG-6/7 family — an event confirming itself — and the V4-BUG-5 family — a global flag paying a specific setup. | **MED** |
| E2 | MODULE 15, lines 3343 / 3445 | `freshL := nbFresh`, `freshS := nsFresh`. `nbFresh` / `nsFresh` describe the **NEXT** buy / sell POI from MODULE 9's scan, which is not necessarily `sdZoneL` / `sdZoneS`. | The S/D producer's 5 POI-freshness score points are attributed from a zone the trade is not taking. Surviving V4-BUG-5 leak. Soft only (`minScore` = 0 by default) so it can gate nothing, but it corrupts the ranking the score exists to provide. | **MED** |
| E3 | MODULE 15, lines 3528 / 3544 | `lvlPoiL = not na(poiBotL) ? poiBotL : sdBotLong`. `PR_SD` already writes `poiBotL := sdBotLong`, so **the fallback can only ever fire for a producer that has no POI at all** (CRT / TBS / TL / PA) — and it then hands `f_sl` an unrelated demand-zone edge as stop candidate 4. | A CRT / TBS / TL / PA stop can be placed at a zone edge belonging to a different setup, i.e. inside the level that invalidates the actual thesis. Reachable only when candidates 1-3 are all rejected, which is uncommon (`c1` is usually valid) — but it is a wrong *risk* number, not a cosmetic one. | **MED** |
| E4 | MODULE 15, lines 3696-3697 and 3765 / 3772 | `reasonLong` / `reasonShort` and both entry labels read `upS.liqTag` / `upS.sbWindow` (and the `dnS` equivalents) **regardless of which producer won**. For `prodL >= PR_SD` those are another object's fields — usually empty or stale. | The operator-facing "why this trade exists" line names the wrong raid, or no raid, on every non-machine entry, and the SB badge reports the machine setup's Silver-Bullet state rather than the emitting bar's. The brief's "explainable signals" requirement is not met for 5 of the 7 producers. | **MED** |
| E5 | `f_setupAdvance` invalidation block (2648-2680) vs `f_poolScan` retirement | A setup **outlives the registry retirement of its own bound pool**. Only `spent`, `brkBar` and the state-2 `PS_DONE` test invalidate; the *time* and *distance* retirements (`poolLife` expiry, `reactWin` staleness at PS_RAID, `sweepLook` / `POOL_CONSUME_ATR` at PS_REACT) are silent. With `reactWin` = 6 against the machine's own `mssWin` 12 + `dispWin` 10 + `FVG_OWN_MAX` 2 + `retestWin` 25, the pool is routinely dead long before the entry. | Two consequences. (a) The stage-2 invalidation "target pool broken or expired" has **no analogue after stage 3** — the two lifecycles have unreconciled clocks and nothing says so. (b) Once retired, `f_poolPush` may re-register the same price as a **new pool with a new id**, so `dedupePool` — which compares ids — cannot recognise a second entry off the same physical liquidity. The one-pool-one-execution rule is therefore only partly enforced. | **MED** |
| E6 | `type Setup` / `type Pool` / `type Zone` | **Eight write-only (dead) fields:** `Setup.tgtPx`, `Setup.tgtKind`, `Setup.liqPx`, `Setup.liqDepth`, `Setup.dispExt`, `Setup.retestPen`, `Pool.reactBar`, `Zone.mitig`. `Zone.mitig` is also *computed* (two math ops per zone per side) on every confirmed bar and never read — `f_regrade`'s "50 % mitigated, never better than T2" is implemented through `z.state >= 2`, not through `mitig`. | No behavioural effect. Dead weight against the CE10117 token ceiling and the 20 s runtime Phase D was spent on, plus a maintenance trap: `mitig` reads as the mitigation driver and is not. | **LOW** |
| E7 | MODULE 15, lines 3613-3614 and 3696-3697 | `blockLong` / `blockShort` are rebuilt on **every historical bar** but are read only inside `if showDebug and barstate.islast`. `reasonLong` / `reasonShort` sit behind a ternary — and Pine evaluates **both** branches, which is the premise Phase D's D2 was built on — so `f_reason` also executes on every bar. Roughly 20 `str.tostring` calls plus concatenations per bar, both sides, always. | Pure runtime waste on the exact axis Phase D was addressing, and the largest remaining per-bar cost that is not a `request.security`. Zero behaviour change to remove: a `go` flag passed into both functions, the established lineage pattern. | **LOW / PERF** |
| E8 | `f_tp`, ladder branch (~3178) | The comment promises "nearest candidate that is at least the loosest RR floor away, **by preference**: opposing wall, external liquidity, internal liquidity". The code seeds `c2` from the wall and then replaces it with the external pool whenever the external pool is **nearer** — i.e. nearest-of-{wall, external}, with internal only as a fallback. | No wrong number is produced; the selected TP2 is defensible either way. But the comment states a rule the code does not implement, which is exactly the C3 / C5 class of defect Phase C was created to stop. | **LOW** |
| E9 | `f_poolPush` upgrade path (line 1363) | The V5.2-B1 in-place upgrade writes `q.px := px`, moving a live pool's price. A setup that locked that pool at stage 2 keeps a stale `s.tgtPx`. | Harmless **today, and only** because `s.tgtPx` is never read (E6). The moment anything reads it, it is wrong. Guard the invariant or delete the field. | **LOW** |

### 14.2 · One finding deliberately NOT raised as a bug

`Setup.liqQual` is snapshotted from `pool.rq` at stage 3 and never refreshed, while
`f_poolScan` can still improve `pool.rq` afterwards (`RQ_C` to `RQ_B` on the
reaction). That asymmetry looks like V5.3-C1 (the frozen POI tier) and invites the
same fix — **it must not get one.** The `rq` improvement is driven by the *global*
`dispDnBar` / `mssDn` flags, so refreshing `liqQual` from the live pool would pipe
exactly the global event contamination V4-BUG-5 outlawed straight into the grade.
Freezing the raid grade at the moment of binding is the correct behaviour. E1
attacks the same problem from the honest end: stop the raid candle from being its
own reaction.

### 14.3 · Gaps against the operator brief (missing features, not defects)

Stated plainly because five phases have not addressed them and nothing in the file
or in this document has said so.

* **TWS — absent entirely.** Zero occurrences of the term in 4 226 lines. No wave
  state machine, no `TWS_IDLE` ... `TWS_CONFIRMED`, no descriptor.
* **CRT is stateless.** `crtBullSetup` / `crtBearSetup` are a 3-candle pattern test
  plus a location filter and a cooldown. There is no `CRT_IDLE` to
  `CRT_RANGE_CREATED` to SWEEP to RECLAIM to CONFIRMATION lifecycle, no stored
  CRT high / low / mid / size, and no tiny-penetration versus deep-manipulation
  distinction inside CRT itself (MODULE 7's raid grading is a different object).
* **TBS is a single hard-wired rule**, not the configurable rule-composer the brief
  specifies, and carries no `TBS_IDLE` ... `TBS_CONFIRMED` states.
* **No liquidity-RUN engine.** `runUp` / `runDn` mark a weak (non-displacement)
  close-through of one level. There is no pool-A to pool-B run detection, no
  internal-to-external progression, and no RUN_CONTINUATION / EXHAUSTION /
  REVERSAL / UNCONFIRMED classification. The brief's "never fade a run merely
  because liquidity was taken" is satisfied *implicitly* — the machine demands
  reclaim, MSS and displacement — but is nowhere stated or measured.
* **No congestion / compression filter.** `dojiCompressed` exists for pattern 4
  only. Nothing downgrades a setup for overlapping candles, alternating structure
  breaks or an absent liquidity narrative.
* **No shared `eventId` object.** Event identity is carried by `Pool.id` +
  `Zone.id` + `mssBar`. That is enough to satisfy the anti-inflation rule — the
  liquidity score is paid once, from one bound pool, and CRT / TBS / trap
  contribute no independent liquidity points — but it is not the descriptor-bearing
  event record the brief asks for, and there is nowhere to hang TWS / CRT / run
  descriptors if they are added.

**Engineering tension that must be decided, not assumed away:** v5.3 compiled and
loaded but drew TradingView's "Heavy script, close to your plan's runtime limit
(20 s)" warning, and Phase D was spent entirely on that. Four new state machines
plus a run classifier and a congestion filter push in the opposite direction,
against both the 20 s runtime and the unmeasured CE10117 token margin (section 9).
Adding them is a real option; adding them *silently* is not.

---

## 15 · v5.5 PHASE E (2026-09-08) — implementation of §14, plus the six missing engines

New generation file: `7.liquidty+supply-v5.5-trade-engine.pine`
(title "LQ-SD-PA v5.5 CTE"). File 6 is the unmodified v5.4 and stays frozen.
Tagged `V5.5-E1` … `V5.5-E9` in the source. Scope was chosen by the operator:
all nine §14 defects **plus** the six subsystems §14.3 listed as absent, with
the two legacy producers removed to pay the budget.

> **NOT COMPILED.** v5.3 is the only file in this lineage that has ever been
> loaded on TradingView. v5.5 has been statically verified (§15.4) and has never
> been on a chart or backtested. No accuracy or profitability claim is made.

### 15.1 · The nine defects, as fixed

| ID | Fix |
|---|---|
| E1 | `f_poolScan`'s PS_RAID → PS_REACT transition now requires `bar_index > p.raidBar`. The raid candle can no longer be its own reaction, which is what let a shallow poke carrying an unrelated internal CHoCH/CISD have its raid grade lifted `RQ_C → RQ_B` on the spot — and RQ_B is exactly what `f_grade` needs for grade A. |
| E2 | New na-safe `f_zoneFresh(Zone)`. The S/D producer scores freshness from `sdZoneL`/`sdZoneS` — the zone it is actually trading. `nbFresh`/`nsFresh` became write-only and were deleted. |
| E3 | `lvlPoiL = poiBotL` / `lvlPoiS = poiTopS`. The `: sdBotLong` fallback is gone: PR_SD already writes `poiBotL` from it, so the fallback could only ever fire for a producer with no POI, handing `f_sl` a foreign zone edge as stop candidate 4. |
| E4 | One event-ownership block resolves `descNL/descTL/evTagL/evIdL/evPxL/sbWinL` (and the short equivalents) from the object that actually produced the candidate — the pool the machine BOUND, or the live raid on that side. The reason line, both entry labels, the dashboard and the dedupe all read those instead of `upS.*`. |
| E5 | **Documented, deliberately not "fixed".** A setup outliving its pool's time/distance retirement is not a contradiction of the narrative, and with `reactWin` = 6 against the machine's own 12 + 10 + 2 + 25 a hard PS_DONE invalidation would kill nearly every setup. The two clocks are intentionally different. The *damage* is fixed in E7 instead. |
| E6 | Eight write-only fields deleted: `Setup.tgtPx / tgtKind / liqPx / liqDepth / dispExt / retestPen`, `Pool.reactBar`, `Zone.mitig` — plus `mitig`'s two per-bar `math.max`/`math.min` computations, which nothing read (`f_regrade`'s 50 %-mitigation rule runs off `z.state`). |
| E7 | `f_dedupeOk` gained a `poolPx` argument and a price+recency test: same side, within `eqTol·ATR` of the last executed level, inside `setupLife` bars. This closes E5's real hole — a retired pool's level re-registering under a new id, which made id-equality dedupe blind to the same physical liquidity. `lastPoolPxL/S` and `lastPoolBarL/S` are written at consumption. |
| E8 | `f_blockReason` and `f_reason` take a leading `go` flag that short-circuits the whole body. Pine evaluates both ternary branches, so gating the call would not have skipped the work — the same reason Phase D pushed its gate inside the risk scanners. `go` is `showDebug and barstate.islast` for the block reason and `finalX and showReason` for the entry reason. |
| E9 | Neutralised by E6: the B1 upgrade's `q.px := px` had stranded `Setup.tgtPx`, and that field no longer exists. `evPx` reads a pool already past `PS_VAL`, which the upgrade can never re-price. |

### 15.2 · The six subsystems

* **EVENT IDENTITY + DESCRIPTORS (§7 / §8).** `Pool` carries `desc` / `descN`,
  seeded at the raid with the raid's own grade (WICK / SWEEP / DEEP RAID).
  `f_evTag` appends a descriptor, idempotently, for every engine that recognises
  the same raid. In `f_score` all descriptors together are worth ONE capped
  allowance of at most 6 points, in a block that cannot reach LIQUIDITY —
  which is still paid exactly once from the event's own raid grade, pool class
  and touch history. Congestion is a debit against the same allowance, so a
  descriptor pile-up inside chop nets to nothing, and the total is clamped to
  100 so the score stays a normalised 0–100 reading.
  **Known limit, stated:** a descriptor is written onto the freshest live raid on
  its side (`anyLoPool` / `anyHiPool`). When the machine's bound pool is not that
  pool, the machine's setup does not receive the bonus. That is deliberately
  conservative — the alternative is tagging two different events with one
  physical descriptor, which is the inflation this whole mechanism exists to
  prevent.
* **CRT AS A STATE MACHINE (§12).** `type Crt`, two instances, `f_crtAdvance`.
  `LC_IDLE → LC_ARMED` (reference candle has CLOSED; hi/lo/mid/size stored) →
  `LC_SWEPT` (penetration graded CP_TINY / CP_MEAN / CP_DEEP off the *same*
  `raidMinAtr` / `raidDeepAtr` the registry uses) → `LC_RECL` (a later close back
  through the MID) → `LC_CONF` (a later displacement) · `LC_INVAL` when the sweep
  becomes a break. The arming bar IS the model's candle 2, so arm+sweep may share
  a call (`armBar = bar_index - 1` keeps reference < sweep strict); reclaim and
  confirmation always need later bars. CP_TINY reaches LC_CONF but is never
  tradable — §12's one-tick-wick rule, enforced.
* **TURTLE SOUP AS A COMPOSER (§13).** `type Tbs`, same lifecycle, with the
  reference window, the extreme's minimum age, penetration grading, a decisive
  reclaim distance (`NEAR_LVL_ATR`) and a **user-chosen** confirmation rule as
  separate stages. The anchor follows the rolling window while nothing has been
  taken and freezes the moment a sweep registers.
* **TWS (§14).** `type Tws`: interaction → a deeper, *rejected* manipulation →
  reclaim with displacement, each wave bounded by `twsWaveWin`, and acceptance
  beyond wave 2 invalidating outright (that is a trend, not a three-wave
  manipulation). §14 calls TWS a context engine, so it cannot emit, writes no
  stop and holds no rank — it attaches a descriptor and nothing else.
* **LIQUIDITY RUN ENGINE (§11).** `type Run`, driven off the break data the
  MODULE 7 intent loop already had (`brkUpKind` / `brkUpPx` / …, no second scan).
  `RN_UNCONF` → `RN_CONT` (pool A broken, then pool B, same direction, with an
  internal→external flag) → `RN_EXH` (the run RAIDED the next pool instead of
  breaking it) → `RN_REV` (exhaustion AND a later opposing shift WITH
  displacement). `runGate` carries §11's hard rule: fading a run still classified
  RN_CONT costs one grade, or is blocked. Both sides breaking on one candle is
  treated as churn, not a run.
* **CONGESTION FILTER (§29).** Price action only (§39 rules out the oscillator):
  compressed range · most bars overlapping the previous bar · almost no net
  travel for the distance covered · structure broken in BOTH directions. Two of
  four = congested → one grade down, or blocked. na-hardened for the first
  `congLen` bars.
* **TRAP ENGINE (§15 / §16).** v5.4's ① watch, promoted. The broken level must be
  TRACKED liquidity (`trapNeedPool`: a registry pool actually broke — §16's
  "crowded, obvious liquidity" is what separates a trap from a plain failed
  breakout), and `f_trapQual` grades it A/B/C from obvious liquidity, breakout
  depth, reclaim speed, reclaim decisiveness and displacement. A graded trap sets
  the producer's POI tier (2 at grade ≥ B, else 3) and pays no liquidity points.
  `PR_PA` is renamed `PR_TRAP` (rank 6).

### 15.3 · Removed, with reasons (§40 requires the reasons, not the silence)

* **R1 — the dynamic trendline engine** (v5.4 MODULE 10, `PR_TL`, its two
  plotchars, its `[LIQ]` and `[SIGNAL]` alerts, its input group, its dashboard
  row). It is not liquidity or PD-array logic; V5.3-C2 already established that
  it carries no POI, therefore tier 3, therefore it **cannot emit at the default
  `minTier` = 2** — display-only in every shipped configuration; and it is §9's
  own second removal lever.
* **R2 — price-action patterns ③ Inside Bar and ④ Doji Reversal** (their state
  machines, five inputs, two constants, the `doji` series, two `[SIGNAL]`
  alerts). Neither contains liquidity content — shape matching, which §39 rules
  out; both were tier 3 and equally unable to emit at defaults; and ④ carried
  four rolling built-ins for a producer that could never fire. **① and ② are
  kept** — ① became the trap engine, and ② (shrinking wicks = absorption, a
  continuation) is retained for backward compatibility as the weakest producer
  in the file. Both alert NAMES survive.

`entryMode`'s three option strings are unchanged on purpose: changing an
`input.string` option resets that user's saved selection to the default.

### 15.4 · Static verification of v5.5

Mechanically checked (`check.py`, `verify.py` in the session scratchpad),
with v5.4 run as a baseline for every check:

* bracket balance — `()`/`[]`/`{}` all zero, no negative excursion
* **71 functions**, no duplicate definitions
* **call arity vs definition at every site** — clean (this is what caught the
  `f_score` 6→7 tuple, `f_grade` +2, `f_dedupeOk` +1, `f_layers` +1,
  `f_blockReason` +3 and `f_reason` +5 signature changes)
* tuple destructure arity vs return arity — clean
* function defined-before-called — clean
* UDT field access vs declared fields, 9 types — 2 findings, both **present
  identically in v4/v5.4** (a `Zone o` local the checker resolves to `Pool o`)
* no `plot` / `plotchar` / `input` / `alertcondition` / `bgcolor` inside a
  function body — clean
* no function assigning to a global scalar — clean (`poolSeq` / `zoneSeq`
  one-element-array pattern preserved; every new engine mutates UDT fields only)
* no duplicate top-level declarations — clean
* indentation: 2 anomalies, **the same two lines as v5.4** (nested-ternary
  continuations inside `f_blockReason`, which Pine permits)
* dangling references to every removed identifier — none
* every new engine opens with `if confirmed`; every producer that can reach
  `finalLong` / `finalShort` was re-traced and is confirmed-gated, so MODULE 15's
  un-wrapped consumption block still cannot run intrabar

| Budget | v4 | v5.4 | **v5.5** | Limit |
|---|---|---|---|---|
| Output slots (plot + plotchar + bgcolor + alertcondition) | 58 | 58 | **57** (4+10+5+38) | 64 |
| `request.security` instances | 5 | 9 | **9** | 40 |
| Top-level statements | 819 | 956 | **984** | a sibling failed at 2 515 |
| Compiled-token proxy | 23 143 | 29 447 | **31 518** (+7.0 %) | CE10117 |
| Inputs | — | 142 | **141** | — |

Runtime, honestly: **no new loop and no new `request.security`.** Removed —
MODULE 10's line work and pivot handling, ④'s four rolling built-ins, `mitig`'s
per-bar arithmetic, and ~20 `str.tostring` calls plus their concatenations per
bar per side (E8). Added — three O(1) state machines, one O(1) run engine, the
congestion block's five built-ins, one `ta.lowest`/`ta.highest` pair for the TWS
reference, and four na-safe accessor calls per bar. Built-ins net roughly even;
string work is strongly down. Expect neutral-to-better than v5.4, but this is an
argument, not a measurement — use TradingView's Pine Profiler.

### 15.5 · Post-implementation re-audit (§44), answered

* *Does every state transition work?* Each of the four new machines was traced
  branch by branch. Every one uses an `if / else if` chain over its own state, so
  at most one progression per call; the only same-call pairs are the two named
  ones (CRT arm+sweep, TBS arm+sweep), both of which compare bars.
* *Can a setup get stuck?* No. CRT: `crtLife` from arming and from the sweep.
  TBS: `crtLife` from the sweep (`LC_ARMED` deliberately never expires — resting
  liquidity does not). TWS: `twsWaveWin` per wave. Run: `runLife`. Every terminal
  state stamps `endBar` and clears on the following bar.
* *Can one event create multiple entries?* Harder than in v5.4: pool `spent` +
  zone `signaled` + id dedupe + **price/recency dedupe** (E7) + cooldown.
* *Can a developing candle create confirmation?* No — every new engine and the
  descriptor attachment open with `if confirmed`.
* *Can the score double count?* Structurally no. The descriptor allowance is
  capped at 6, paid once from `descN` regardless of how many engines fired,
  cannot reach the LIQUIDITY block, and the total is clamped to 100.
* *Can alerts duplicate?* The five new ones fire on single-bar transitions
  (`LC_CONF` is entered once and `endBar` blocks re-entry on the same bar; the
  run alert fires on `runFresh`; the trap alert is bounded by `wFired`).
* *Can HTF data repaint?* Unchanged — all 9 instances remain `expr[1]` +
  `lookahead_on`.

### 15.6 · Known-and-left after Phase E (do not re-report)

* Everything §11's and §12's known-and-left lists still stand.
* **E5 is a documented design position, not an oversight** (see 15.1).
* **Descriptors attach to the freshest live raid on their side**, so the machine
  does not always receive the bonus (see 15.2).
* `Setup.liqQual` stays frozen at the stage-3 bind, and must — refreshing it
  would pipe V4-BUG-5's global contamination into the grade (see 15.1, E1).
* The CRT sweep requires the sweeping candle to close INSIDE the range, so a
  single candle that sweeps the low and closes above the range high — a strong
  reversal — is not registered as a CRT. Deliberately conservative.
* `f_gradeZone`'s creation tier still reads global recency flags (v5 known limit).
* HTF POIs still have no live re-grade and no dedupe id.
* Group labels inside `grpC` still carry the old producer glyphs (⑫/⑬) while
  those numbers are now group indices. Cosmetic, and pre-existing.
* **Not compiled, not backtested.** The alignment score is not a win probability.
