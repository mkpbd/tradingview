# FORENSIC AUDIT — `23.liquidty+supply-v7.3-ict.pine` → plan for v7.4

**Date:** 2026-09-11
**Scope:** full read of the 6 153-line file (code from line 1154; lines 1–1150 are the lineage
header). Every module, every producer, every gate, every `request.security`. Cross-checked against
`AUDIT-v7.1-FORENSIC.md`, `AUDIT-v7.2-ICT.md` §E/§F and `AUDIT-v7.3-ICT.md` so that nothing already
documented as *known-and-left* is re-reported as new.
**Method:** static read only. Pine cannot be compiled locally; nothing here has been backtested.
Every finding cites the line, the failure path and a fix sketch with a source-token estimate against
the lineage's validated model (`compiled ≈ 3.418 × tok − 9 475`, v7.3 ≈ 100 099 of 100 256 —
**157 compiled tokens spare**).

---

## 0 · VERDICT IN ONE PARAGRAPH

The architecture is sound and the v7.1→v7.3 ownership work holds: the machine's nine-stage chain is
owned, chronological, confirmed-bar-only and non-repainting; the HTF idiom (`expr[1]` +
`lookahead_on`, clamped ≥ chart) is correct; risk is resolved before emission; the score cannot
create a grade. What remains is (a) **four P1 defects**, three of which are side effects of v7.1–v7.3
fixes that were not followed through — the trap engine still borrows an unrelated raid for its
*admission gate and its consumption*, the FEM path lost A+ to its own tap candle, and the elite trap's
"displacement" is a close-location test — and (b) a set of **entry-frequency limiters** that are
design choices, not bugs, but are the reason the engine prints so rarely: one hunted target per
side, MSS and displacement forced onto different candles, and the 3rd-candle FVG geometry dropped
by P1-3. Section 3 fixes the defects inside the budget; section 4 is the entry-accuracy / signal
plan for v7.4 and what it costs.

---

## 1 · INVENTORY (v7.3 as read)

| | count |
|---|---|
| `alertcondition` | 34 (outputs 4 plot + 14 plotchar + 5 bgcolor + 34 = 57 of 64) |
| `input.*` | 166 |
| UDT | 7 (`Pool` `Struct` `Ses` `Zone` `Tws` `Run` `Setup`) |
| `request.security` sites | 6 (10 instances: 5 × `f_bias`, ctx, PDH/L, PWH/L, HTF struct, HTF POI) |
| producers | FEM 1 · machine 2 · S/D 3 · trap 4 (① graded, ② dead at default) |
| hard gates | `baseOK hNarr slOk hTgt hRr hRoom hDedup hTier hCong hRun hGrade hScore` + arbitration |
| compiled (model) | ≈ 100 099 · **157 spare** · main body 1 725 (cap ≈ 2 030) |

---

## 2 · WHAT IS ALREADY CORRECT — do not "fix"

* **Repainting.** Every state latch is inside `if confirmed`; every chip / mark / entry label fires only
  on confirmed series; the six HTF requests all read `[1]` inside the request with `lookahead_on` and
  are clamped to ≥ chart by `f_tfUp`. The `barstate.islast` redraw blocks (marking layer, dashboard,
  HTF POI boxes, OTE box, next-zone labels) are display only. **No new repaint path found.**
* **Ownership on the machine path.** `tgtId == liqId`, `raidBar > tgtBar`, raid wick contained in the
  POI ± 0.15 ATR, `mssBar > poiBar`, `dispBar > mssBar`, `fvgBar − dispBar ≤ 2`, `f_narrOk` re-derives
  it all at emission. Correct.
* **Risk before emission.** `f_sl` hierarchy + clamp as a hard gate; TP2 measured, never synthetic;
  RR to the clamped TP2; opposing-liquidity room separate from RR. Correct.
* **P1-1 (S/D ownership), P1-4 (trap grade off its own chain), BUG-01…07** are implemented as the
  v7.2/v7.3 notes describe. Verified line by line.

**Known-and-left, verified still present, NOT re-reported below:** congestion double count +
`RG_CHOP` coupled to the gate switch · EQ/swing pools registered `pivLen` late, no backfill ·
`evPxL/S` and `f_evTag(...,"BEAR TRAP")` read the unrelated live raid · producer ② dead at default ·
double-counted structural break in `f_structUpdate` · `liqBeforeFail` not side-aware ·
`raidNearPx` uses pool price not wick · zone overlap loses a zone instead of replacing · `legHi/legLo`
extend through ST_DISP · `poiFresh` frozen at tap · `strongUp` pays the CISD→MSS promotion ·
dashboard bias row label for a clamped TF · `f_tfUp` qualifier unverifiable offline.

---

## 3 · NEW FINDINGS

Severity: **P1** = wrong signal / wrong consumption / advertised capability unreachable ·
**P2** = lost valid signals or mis-graded entries · **P3** = dead code, inflation, inconsistency.

### F-01 · A trap (or unowned S/D) entry SPENDS AN UNRELATED POOL — **P1**

**Where.** MODULE 15 consumption, lines 5589 / 5610:

```pine
if not na(anyLoPool) and prodL > PR_MACH and dedupePool
    anyLoPool.spent := true
```

**Why it is wrong.** For `PR_TRAP` the live raid on the side (`anyLoPool`) is *by construction* not the
trap's pool — the pool the trap broke is `PS_DONE` and `f_findRaid` never returns it (this is exactly
P1-4's premise). So a trap entry marks the freshest *unrelated* raid as spent. `f_setupAdvance` then
kills any machine setup bound to that pool: `s.st >= ST_RAID and f_poolSpent(s.pool)` →
`"target pool already produced an entry"` (line ≈ 4522). A rank-4 producer silently destroys a
rank-1/2 narrative in progress, and the dedupe (`lastPoolIdL := poolIdL`, which P1-4 set to 0 for the
trap) no longer even protects the trap's own level. With `needSweep` OFF the S/D producer does the
same to a pool its zone does not own.

**Fix (≈ +8 tok).** Spend only what the producer owns:
`if prodL == PR_SD and needSweep and dedupePool and not na(anyLoPool)` (with `needSweep` ON, `sdOwn`
proved `anyLoPool` is the zone's own pool). The trap spends nothing here — it already consumes its
watch (`wState := 0`) and F-04 gives it its own dedupe identity.

### F-02 · FEM A+ IS UNREACHABLE IN PRACTICE AFTER P1-2 — **P1 (regression)**

**Where.** `f_htfTier`, line 4470; stamped at the tap (4654) and refreshed every bar (≈ 4505):

```pine
f_htfTier(bool isL) =>
    int(math.min(1 + nz(isL ? hPoiBIn : hPoiSIn, 0) + (aligned ? 0 : 1), 3))
```

**Why it is wrong.** `hPoiBIn` counts every *closed* HTF candle whose low traded into the array. The
HTF candle **containing the setup's own tap** counts once it closes. On 15m/4H (16 LTF bars per HTF
candle) the LTF sequence tap → MSS → displacement → FVG → retest almost never completes inside the
tap candle, so the FEM POI reads tier 2 at entry and the A+ rung (`tier == 1`) is closed. P1-2 meant
to catch *later* mitigation and an HTF flip; it also penalised the setup for the mitigation it *is*.

**Fix (≈ +30 tok).** Stamp the count at the tap and forgive exactly one candle:
`Setup.poiIn0` (+ reset), `s.poiIn0 := nz(isL ? hPoiBIn : hPoiSIn, 0)` at 3→4, and
`f_htfTier(isL, in0)` = `1 + max(nz(hPoiBIn) − in0 − 1, 0) + opposed`, clamped 3. Fresh at the tap
and still aligned = tier 1 until a *second* HTF candle trades into the array.

### F-03 · THE ELITE TRAP'S "DISPLACEMENT" IS A CLOSE-LOCATION TEST — **P1**

**Where.** Lines 3951–3964: `f_trapQual(…, dispDnBar or strongDn)` / `f_trapElite(…, dispUpBar or
strongUp)`.

**Why it is wrong.** `strongDn` is "closed in the lower 30 % of its own range". The reclaim candle
already needs `body >= BRK_BODY_ATR (0.5) × atr`, so a 0.5-ATR candle closing near its low is a
complete fifth ingredient. Elite ⇒ tier 1 + `rqv = trapQ = RQ_A` ⇒ A+ eligible with a stop at the
overshoot. Meanwhile the machine's stage 6 demands a 1.3-ATR body, a close past the MSS level, out of
the POI, and a hold. The one producer allowed to substitute for the machine narrative (`elite` in
`f_grade`) has the weakest displacement definition in the file — the same family as the known
`strongUp`-pays-CISD item, but this one reaches A+.

**Fix (−8 tok).** Drop `or strongDn` / `or strongUp` at the four sites. Optionally require the
reclaim body ≥ `dispBodyAtr × atr` for *elite* only (+6 tok), leaving ordinary ① graded as before.

### F-04 · TRAP ADMISSION IS GATED ON AN UNRELATED RAID — **P1**

**Where.** `f_prod`, line 5378: `else if (allowAll or (trapEl and pa1)) and (pa1 or pa2) and cg`,
where `cg = confGateLong = sslInPlay and cMssBarL > anyLoBar and …` (4994).

**Why it is wrong.** A bear trap is: buy-side… no — a *sell-side* pool BROKE (close below), late
sellers entered, the level was RECLAIMED. Its own chain is `wStart` (break bar) → reclaim bar, with
`tPoolD` proving tracked liquidity. `cg` instead demands that **some other sell-side pool is in
`PS_RAID/PS_REACT` right now** and that an internal CHoCH/CISD post-dates *that* pool's raid. So an
elite trap only exists when a coincidental second raid happens to be live — and every downstream
label reads the coincidence: `evIdL`, `evTagL`, `descTL`, `evPxL` (dedupe price) and the
`"BEAR TRAP"` descriptor all name the unrelated pool. P1-4 fixed the *grade*; the *gate* and the
*identity* still belong to somebody else. Effect: elite traps are much rarer than designed and the
reason line lies about which event was traded.

**Fix (≈ +45 tok).** Stamp identity at arming (`var int wId`, `var float wPx`, written with `wKnd`
from the breaking pool — `brkUpId/brkDnId` harvested in the same registry loop as `brkUpPx`). In
`f_prod`: trap branch gate becomes `(allowAll or (trapEl and pa1)) and (pa1 or pa2)` with its own
chronology already inside the watch (break < reclaim ≤ `maxAfterBrk`); set `pid := wId` (so
`dedupePool` binds the *broken* level). Outside: `evIdL = prodL == PR_TRAP ? wId : …`,
`evPxL = prodL == PR_TRAP ? wPx : …`, and `f_evTag` the trap descriptor onto nothing (the broken pool
has left the registry) rather than onto `anyLoPool`.

### F-05 · THE MACHINE MAY BIND A POI BORN AFTER ITS RAID — **P2**

**Where.** Stage 3→4 chart-zone scan, line 4679: `live = … and bar_index - z.bornBar <= poiMaxAge`.
There is no `z.bornBar <= s.liqBar`.

**Why it matters.** A PD array price "raided into" must pre-exist the raid. Without the test, the
first zone that *contains the wick* wins — which, after a reaction leg, is often the leg's own OB
(the raid candle itself when it was opposite-coloured: `obB = low[obI]` = the raid low) or its FVG,
created at `disp + 1`. The setup then sits at ST_POI needing a *second* MSS within `mssWin`, while the
real trade (the first leg's FVG retest) has no owner. Either the setup expires (wasted) or it chains a
second shift/expansion onto a raid up to 60 bars old.

**Fix (+6 tok).** Add `and z.bornBar <= s.liqBar` to `live`. (The HTF path already implies it: the HTF
POI is `[1]`-shifted, so it existed before the chart bar.)

### F-06 · P1-3 DROPPED THE "DISPLACEMENT = 3rd CANDLE" FVG — **P2 (regression)**

**Where.** Lines 4806–4809: `else if bar_index == s.dispBar → "awaiting post-displacement
confirmation"`, then at `disp + 1` `else if isL ? bullFVG : bearFVG` tests the **current** triplet
(disp−1, disp, disp+1).

**Why it matters.** The gap formed by (disp−2, disp−1, disp), where the displacement is the *third*
candle, was lockable in v7.2 on the displacement bar. v7.3 forbids locking on that bar and never looks
at `bullFVG[1]` on the next bar, so that geometry is now unreachable. `FVG_OWN_MAX = 2` is honoured in
the header but not in the code path. Lost valid entries, no false ones.

**Fix (≈ +40 tok).** At `bar_index == s.dispBar + 1`, accept `bullFVG[1]` (with `ft = low[1]`,
`fb = high[3]`, still ≥ `fvgMinAtr`) when the current-bar gap is absent, stamping `fvgBar :=
bar_index`. `f_narrOk` (`fvgBar − dispBar ≤ 2`) and the post-displacement hold test are unchanged.

### F-07 · OTE IS READ FROM THE REJECTION CANDLE, NOT FROM THE PULLBACK — **P2**

**Where.** Line 4864: `f_inOte(isL, s.legLo, s.legHi, isL ? low : high, close)`.

**Why it matters.** `deep` is *this bar's* extreme. A retracement that bottomed at 66 % two bars ago
and now rejects from 58 % reads `oteQ = 0` → A+ refused (`oteNeedAp`) and 0 POI points; the reverse
mis-grade (rejection candle spiking past 79 % on a pullback that lived at 65 %) reads class 3. The
OTE is a property of the pullback, not of the confirming candle.

**Fix (≈ +25 tok).** `Setup.pbExt` (+ reset), updated every ST_FVG bar
(`s.pbExt := isL ? math.min(nz(s.pbExt, low), low) : …`) and passed as `deep`.

### F-08 · `congTight` FIRES ON ALMOST EVERY NON-TRENDING WINDOW — **P2 (calibration)**

**Where.** Line 4199: `congTight = highest(high,10) − lowest(low,10) <= 0.45 × 10 × atr` = **4.5 ATR**.

**Why it matters.** A 10-bar window's high–low range on a random walk is ≈ 3–3.5 ATR(14); only a
trending window exceeds 4.5. So `congTight` is true whenever the market is not trending, and
"2 of 4" degenerates to "any one of churn / no-net / flip". Combined with the known double count,
this is the main reason A+ candidates print as A. Not a false-signal source — an over-downgrade one.

**Verify first, then fix (0 tok).** Watch the dashboard `chop N/4` row across a trending session: if
`congTight` reads 1 through the trend, lower the constant to `0.25 × congLen × atr` (2.5 ATR for
10 bars) and re-check.

### F-09 · ONE HUNTED TARGET PER SIDE — **P2 (entry frequency)**

**Where.** Target weight loop ≈ 2986–2998 (`f_kindPri × 10 + maskN × 5 + touches × 4 + legs × 2 −
dAtr × 1.5`), stage 2→3 re-selection at 4627 (only to the single best-weighted pool).

**Why it matters.** Kind dominates: an HTF swing (70) or PWH (60) 15 ATR away outranks a session low
(30) two ATR away. The machine locks the far pool, and every raid of a *nearer* pool on that side is
invisible to it (`anyLo*` shows it, the machine cannot bind it). Setups routinely expire at
`setupLife` "target not yet raided" while the tradeable sweep happened under their nose. This is the
single largest reason the narrative producer prints rarely on intraday charts.

**Plan item (§4-A).** Not a two-line fix; costed there.

### F-10 · DEAD / GLOBAL SCORE TERMS — **P3**

* 4956: `+3` "MSS ≠ displacement bar" — for the machine `dispBar > mssBar` is *enforced*, so the
  term is unconditionally paid (+3 inflation on every machine entry; only S/D can miss it).
* 4957: `+3` "CISD independent of the MSS" reads the **global** `cisdUpBar`, contrary to the
  module's own V4-BUG-5 rule.
* 5371: S/D `rtq := 2` constant → EXECUTION 4 points always.
  Keep for now (published score semantics); repurpose the first term in §4-B.

### F-11 · CONFLUENCE CHRONOLOGY ACCEPTS A BARE CISD AS MSS — **P3**

4990: `cMssBarL = max(iChUpBar, cisdUpBar)` — the *undisplaced* CISD bar, ignoring `mssNeedDisp`.
The machine uses `cisdMssUp`. `recentDispUp` (≤ 3 bars) partly covers it. Fix: keep a
`cisdMssUpBar` memory instead (+10 tok), or accept as documented.

### F-12 · S/D CANDIDATE PICKS BEST TIER, NOT THE OWNED ZONE — **P3**

3660: `if not sdCandLong or z.tier < sdTierL`. With `needSweep` ON the producer then fails `sdOwn`
when a higher-tier zone without provenance shadows an owned lower-tier one. Fix: prefer
`z.srcPoolId == anyLoId` first, tier second (+12 tok).

### F-13 · HTF CONTINUATION ADMITS A PREMIUM LONG ON ANY HTF POI — **P3**

2372: `htfContLong = htfDir > 0 and (na(htfPd) or htfPd <= 0.5 or not na(hPoiBTop))` — the HTF POI
may be anywhere. Tighten to "price within the POI ± slack" (`atHtfPoiL`, already computed) (+4 tok).

### F-14 · A LOWER-RANKED S/D ENTRY KILLS A MACHINE SETUP ON THE SAME POOL — design tension

S/D consumption sets `anyLoPool.spent`, which is the machine's `s.pool` when both trade the same raid;
the machine dies at "target pool already produced an entry". Arbitration only compares producers on
the *same bar*; the S/D 50 % retest typically fires earlier. Option (§4-D): suppress `PR_SD` while a
machine setup on the same side is ≥ `ST_POI` **and** `upS.liqId == anyLoId` (+10 tok). Quality over
frequency, consistent with the file's own rule.

---

## 4 · v7.4 PLAN — ENTRY ACCURACY + SIGNAL GENERATION

Ordered by value per compiled token. Everything in **E1** is a defect repair and is budget-neutral
after the reclaim in §5. **E2** adds signals and needs a bigger reclaim (also in §5). Each item names
the exact input it adds (if any), the default, and what the operator will see change.

### E1 · REPAIRS (F-01 … F-08, F-12, F-13) — ≈ +150 source tokens before reclaim

| # | Change | Trading effect |
|---|---|---|
| E1-1 | F-01 owned consumption | Machine setups stop dying to trap / unowned S/D entries |
| E1-2 | F-02 `poiIn0` tap forgiveness | FEM A+ becomes reachable again; still decays on a 2nd HTF mitigation or HTF flip |
| E1-3 | F-03 drop `strongX` from trap disp; elite reclaim body ≥ `dispBodyAtr` | Elite ① traps rarer, genuinely displaced; A+ trap = real |
| E1-4 | F-04 trap-owned gate + identity (`wId`/`wPx`) | Elite traps fire in *Narrative only* as advertised; reason / event / dedupe name the broken level |
| E1-5 | F-05 `bornBar <= liqBar` | No POI hijack by the reaction leg's own array |
| E1-6 | F-06 restore 3rd-candle FVG at `disp+1` | Recovers the gaps P1-3 lost, with the hold test intact |
| E1-7 | F-07 `pbExt` for OTE | OTE class reflects the pullback → correct A+ / POI points |
| E1-8 | F-08 verify → `0.25` | Fewer spurious A+→A downgrades |
| E1-9 | F-12, F-13 | Owned S/D zone wins; premium longs need the POI under price |

### E2 · SIGNAL GENERATION (design changes, each behind an input, default = current behaviour)

**E2-A · Multi-candidate liquidity target (F-09).** New input `tgtMode`: `"Best pool (v7.3)"` /
`"Any qualifying pool"` (default: v7.3). In "Any" mode stage 2 stores the *side* and a minimum kind
priority (`tgtMinPri`, default `PK_SES`-level = 3) instead of one id; stage 3 binds the **first pool on
that side raided after `tgtBar`** whose `f_kindPri ≥ tgtMinPri`, is unbound, unspent, within
`sweepLook`. Identity is still locked *at the raid* (`liqId`, `bound`), chronology is unchanged
(`raidBar > tgtBar`), `f_narrOk` still requires `liqId == tgtId` (set `tgtId := liqId` at bind). This
is the biggest single lever on signal count for the narrative producer. Cost ≈ +90 tok.

**E2-B · MSS candle may be the displacement candle.** New input `mssIsDisp` (default OFF = v7.3).
ON: at stage 4→5, if the MSS bar itself passes all four stage-6 tests (body ≥ `dispBodyAtr`, past
the MSS level — trivially, out of the POI, hold), stamp `mssBar = dispBar = bar_index` and go straight
to ST_DISP. `f_narrOk` relaxes `dispBar > mssBar` to `>=` only when `mssIsDisp`. The score's dead
`+3` (F-10) becomes meaningful again (`dispB != mssB` now *can* be false). Canonical ICT MSS-with-
displacement stops needing a second 1.3-ATR candle. Cost ≈ +60 tok.

**E2-C · CE (consequent encroachment) entry model.** New input `entryModel`: `"Close of rejection
candle (v7.3)"` / `"FVG 50 %"`. In CE mode `sigEntry`, `f_sl`'s `entry`, `riskL`, `f_tp`, `rrL` all
use `mid` (the gap's 50 %) instead of `close` when the retest penetrated to it. Same signal bar, same
gates, better RR arithmetic and a stop measured from the level actually traded. Cost ≈ +40 tok
(one `entryPxL/S` series replacing `close` at ~8 sites).

**E2-D · Machine-first arbitration (F-14).** `PR_SD` suppressed while the same-side machine is ≥
ST_POI on the same pool. Cost ≈ +10 tok.

**E2-E · IFVG continuation (later).** When the machine's locked FVG is traded through (`close <
fvgBot`), v7.3 kills the setup. ICT treats the inverted gap as an execution array for the opposite
side. Feeding that into the *opposite* direction's state machine as a POI candidate (with the break as
its raid-equivalent) is a real signal source but a new ownership chain; not for v7.4.

### E3 · WHAT NOT TO ADD

No oscillator, no candlestick library, no second gate on evidence already gated (congestion /
regime). No re-introduction of CRT / turtle soup. No loosening of `hTgt`, `slOk`, `f_narrOk`.

---

## 5 · BUDGET — HOW v7.4 PAYS FOR ITSELF

v7.3 has **157 compiled ≈ 46 source tokens** spare. E1 needs ≈ +150 source ≈ +510 compiled. E2 needs
≈ +200 source ≈ +680 compiled more.

**Reclaim R1 (pays for E1): retire producer ②.** `AUDIT-v7.2` §F already listed "give ② a grade and
a stop, or retire it explicitly". It is dead at the default `minTier = 2`, carries no stop, no grade,
and is absorption rather than a trap. Remove: `showS2`, `pa2Long/Short`, `shrinking/shrankPrev`
(the 4-wick block), the two `else if showS2` branches, the `"② PinTrap"` tag branch, its
alertcondition and dashboard/prodTxt mentions. Estimate **−130 … −160 source ≈ −450 … −550
compiled**, and one output slot freed. Together with the F-03 deletion (−8) this covers E1 at or just
inside the cap; if the model says otherwise, E1-6 (+40) is the first to defer.

**Reclaim R2 (pays for E2): move MODULE 8B (liquidity marking layer, ≈ 3 960 compiled) to a
companion file** — the lineage already does this for the ICT layer (file 10), retail PA (12) and the
MTF CTT layer (15). It writes nothing any other module reads (its own header says so), so the split is
behaviour-free. Alternative: the debug panel (≈ 3 680), but that panel is how F-08 and every
verification step below is observed — keep it.

Every patch: Python exact-match (one occurrence asserted), CRLF preserved, then the scratchpad
checkers (brackets, continuation lines, defined-before-called, arity, output slots, no global assign
in functions). Per the lineage rule, **v7.4 is a new file (`24.liquidty+supply-v7.4-ict.pine`)**;
file 23 stays untouched.

---

## 6 · VERIFICATION ON A CHART (after v7.4)

| # | Check | Expect |
|---|---|---|
| 1 | Compiles | CE10117 headroom per the model; note the real number back into the lineage note |
| 2 | ① trap entry, debug `event · desc` | Names the **broken** pool id / price, not the live raid; machine rows on that side unchanged next bar |
| 3 | Machine setup at ST_POI/MSS on pool #N, then a trap fires on the same side | Setup survives (F-01) |
| 4 | FEM setup, debug `POI · array` | `HTF T1` through the tap candle's HTF close; `T2` only after a *second* HTF candle trades in or HTF flips |
| 5 | Elite trap chip `+` | Only with a real displacement reclaim body; count drops vs v7.3 |
| 6 | Stage 6→7 on a displacement that was the 3rd FVG candle | Locks at `disp+1` (F-06) instead of falling back to ST_MSS |
| 7 | Debug `FVG · OTE · IDM` | OTE class equals the pullback's deepest retracement band, not the rejection bar's |
| 8 | Dashboard `chop N/4` through a trending session | `congTight` no longer contributes 1 by default |
| 9 | `tgtMode = Any` on a 5m/15m chart | Materially more state-3 binds; every bind still shows `raid > target` bars in the debug panel |
| 10 | `mssIsDisp` ON | Setups reach ST_DISP on the MSS bar when it displaces; `narrative ✓` still required |
| 11 | `entryModel = FVG 50 %` | Entry line at the gap midpoint; RR ≥ v7.3's on the same signals |
| 12 | Alert list | ② alert gone; all other 33 names unchanged |

---

## 8 · v7.4 AS BUILT — `24.liquidty+supply-v7.4-ict.pine` (2026-09-11)

Built from file 23 by an exact-match patch script (66 patches, each asserting its occurrence
count; LF preserved; file 23 untouched). Everything in §4 E1 and E2-A/B/C/D landed; E2-E deferred.

**Tokenizer re-calibration.** The lineage tokenizer reads 200 compiled tokens LOW against the two
real CE10117 results (file 14: 99 740 real vs 99 549 model · file 17: 108 630 vs 108 429), so
**true ≈ 3.418 × srcTok − 9 275**. File 23 = 31 991 src → ≈ 100 070 (audit said ≈ 100 099).

| | src tok | compiled (true model) | spare |
|---|---|---|---|
| v7.3 (file 23) | 31 991 | ≈ 100 070 | ≈ 186 |
| v7.4 before reclaim | 32 629 | ≈ 102 250 | **−1 995** |
| **v7.4 shipped** | **31 849** | **≈ 99 585** | **≈ 670** |

**Reclaim actually used** (§5 proposed retiring ② + moving MODULE 8B to a companion; the companion
is not possible — 8B reads this script's registry — so display-only cuts were taken instead, every
one a lever an earlier header had already ranked):

| | src tok |
|---|---|
| R1 producer ② retired (input, 2 branches, shrinking-wick series, alert) | −≈150 |
| R2 five bias `request.security` → one at the filter TF; 5 dashboard rows → 1 | −≈160 |
| R3 order-flow zigzag (`showOF`) | −≈136 |
| R4 MODULE 8B per-label tooltip + cluster boxes + dead `f_lsTxt` | −≈230 |
| R5 dashboard rows Layers (+`f_layers`), Day open (+`midOpen`), Descriptors | −≈210 |

Nothing that decides, gates, grades, scores, stops or targets a trade was removed. `request.security`
instances 10 → 6 (runtime win too). Inputs 166 → 169. Alerts 34 → 33. Outputs 55 → 54.

**Checkers (scratchpad `check.py`):** brackets net 0, never negative · no duplicate top-level
declaration · every `f_*` defined before first call · call arity matches for `f_prod` `f_htfTier`
`f_anyRaid` `f_score` `f_grade` `f_sl` `f_tp` `f_findRaid` · two odd-indent lines, both pre-existing
in v7.3 · dead identifiers: `tlN`/`poolFlush` (deliberate sinks, as before) and the five per-side
score-block outputs `ctxL…exeL` / `ctxS…exeS` (only the removed Layers row read them; unused tuple
elements are legal Pine).

**Defaults that CHANGED (repairs):** F-01 owned consumption · F-02 tap forgiveness · F-03 trap
displacement = `dispUpBar/dispDnBar` · F-04 trap without `cg`, own identity · F-05 `bornBar <=
liqBar` · F-06 3rd-candle FVG at `disp+1` · F-07 pullback OTE · F-08 `congTight` 0.25 · F-12 owned
S/D zone first · F-13 HTF POI must be at price · F-14 `machFirst` ON.
**Defaults that did NOT change (E2 switches, all = v7.3):** `tgtMode` Best pool · `mssIsDisp` OFF ·
`entryModel` Rejection close. To get the signal-generation effect, turn on `tgtMode = Any qualifying
pool` first, then `mssIsDisp`, then try `entryModel = FVG 50% (CE)`.

**Not compiled, not backtested.** One construct unverifiable offline besides `f_tfUp`: none new —
every new statement uses shapes already present in the file (object-returning function, `var`
scalars, ternaries over series). If CE10117 appears the header names the cut order (E2-C first).

## 7 · KNOWN, DELIBERATELY LEFT (add to the lineage list)

* F-10's global CISD `+3` and the S/D constant `rtq = 2` — score semantics, separate pass.
* F-11 bare-CISD chronology on the confluence path — mitigated by `recentDispUp`.
* E2-E IFVG continuation — new ownership chain, not v7.4.
* The dashboard label for a clamped bias row, and `f_tfUp` qualifier inference — unchanged from v7.2.
