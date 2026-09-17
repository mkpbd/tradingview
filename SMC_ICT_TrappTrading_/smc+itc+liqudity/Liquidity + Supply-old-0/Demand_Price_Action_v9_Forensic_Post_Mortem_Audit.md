# Forensic Post-Mortem Audit — `Demand + Price Action-9.pine`

**Subject:** `Liquidity + S/D + Price Action [MTF] v9` (`LQ-SD-PA v9`)
**File:** `Demand + Price Action-9.pine` — 5,599 lines / 352 KB / Pine v6
**Method:** full static read of every line, module by module, plus cross-module dataflow tracing. No compile, no backtest — this is a source audit.
**Audit date:** 2026-09-15
**Auditor stance:** 30-year desk operator reading someone else's execution logic before putting size behind it.

---

## 0. Executive verdict

v9 is a **genuinely well-engineered script** that has been audited six times and shows it. The changelog discipline is exceptional, the ARCH-1 setup machine is the right primary path, and the v7 arbiter (one decision per bar) is the single most valuable architectural decision in the file.

But six audits of *the same file by the same hand* have produced a characteristic failure signature: **every fault that was found got a named fix and a switch; the faults that were never looked for are still there, and they all live in the same place — the seams where a "quality" number is computed from state that does not belong to the signal.**

The three structural problems below are not bugs in the sense of "wrong operator". They are **category errors that inflate grades**, and a grade-inflating category error in a tier ladder is worse than a crash, because it ships silently as an A+.

| | Finding | Severity |
|---|---|---|
| **S1** | `tierLong` / `tierShort` are **per-BAR, per-SIDE** scores, not per-signal. Every producer firing on that bar inherits the side's best grade. | **P0 — structural** |
| **S2** | The HTF-alignment count awards a free point for an HTF POI that price is nowhere near. A+ threshold is effectively one notch lower than documented. | **P0** |
| **S3** | POI and EXECUTION are double-counted through BPR retest — the exact class of defect V9-07 fixed for the structure leg, left open one layer down. | **P0** |

Below: 6 × P0, 9 × P1, 7 × P2, each with evidence, root cause, blast radius and a concrete fix. Then a phased remediation plan with a token budget.

---

## 1. Architecture as actually wired (not as documented)

Tracing the real dataflow, not the module headers:

```
M3   candle anatomy ─┬─ CISD / IFC ──────────────────────────┐
M4   pivots ─┬─ EQ pools ─┬──────────────────────────────┐   │
             └─ trendlines │                              │   │
M4B  session ladder (sesQ) ─────────────┐                 │   │
M5   LIQUIDITY ENGINE ◄─────────────────┘                 │   │
       sweep writers: swing · EQ · PD/ext/PW · session raid│   │
       ↓ ONE slot per side: lastSslLvl/Ext/Qual/Type/Ses   │   │
       ↓ sslInPlay / bslInPlay  (recency + proximity + HELD)│  │
M6   STRUCTURE ◄──────────────────────────────────────────┘   │
       f_structure ×2 (internal pivLen 5 · external extPiv 12)│
       MSS = eCHoCH + quality sweep in play ──► writes qual:=4│
       f_dispQ 0..3                                           │
M7   HTF bias (3 security datasets) ─┐                        │
M9   HTF CRT/TBS/POI (2 datasets) ───┤                        │
M10  dealing range ◄── rangeSrc ─────┤                        │
M11  REGIME ◄── extDir + extRange ───┤                        │
M12  raw FVG + locked latest gap ────┤                        │
M12B P1 HH/HL/LH/LL + strong/flip ───┤                        │
M12C typed FVG · BPR · hidden CHoCH ─┤                        │
M13  zone engine (SD/OB/RB/BRK/MIT) ─┤                        │
M13B liquidity target map (fresh only)┤                       │
M13C corrected OB · Quasimodo ───────┤                        │
M14  CRT · TBS · TL · IB · Doji ─────┤                        │
M15  FEM ────────────────────────────┤                        │
M16  SCORE + TIER LADDER ◄───────────┘◄───────────────────────┘
M16E exec quality · clean path · decay
M16D P7 models (SB/QM/BRK/FVG4)   } candidates
M16B LT trap engine (7 patterns)  } candidates
M17  SETUP MACHINE (the primary path)
M17B v5 confirmation floor (engine triggers only) + anti-chase + RR
M18  ARBITER — context · tier · cooldown · POI-dedup · clash → ONE direction
M19  TP ladder + trade tracker
M20/21/23  labels · dashboard · alerts
```

**The critical observation:** everything from M16 down consumes **bar-level scalars** (`tierLong`, `execQL`, `pathL`, `htfAlnL`, `poiTL`) that are computed once per bar per side. The arbiter then attaches whichever of those scalars exists to whichever producer survived. That is the root of S1 and of several P1s below.

---

## 2. P0 findings

### P0-1 — The tier is a property of the BAR, not of the SIGNAL

**Evidence:** `f_tier(bool isL)` — [line 4080-4097]. Called exactly twice: `tierLong = f_tier(true)` / `tierShort = f_tier(false)` [4098-4099]. Consumed at [5031-5032]:

```pine
engTierOKL = tierLong  >= v5RankL and v5OkL
engTierOKS = tierShort >= v5RankS and v5OkS
```

and then applied identically to **all eleven long producers** [5033-5046], and reported as the final grade at [5070]:

```pine
finTierL = sigMCLong  ? mcTierL : tierLong
```

**Root cause:** `f_tier` reads only side-wide context — `liqLong`, `poiLong`, `recentMssUp`, `dispUpLive`, `sesQ`, `execQL`, `htfAlnL`, `pdPos`, `pathL`, `poiTL`. Not one term asks *which producer fired*. So when an inside-bar breakout (`sig3Long`, a continuation trigger with no liquidity requirement of its own) fires on a bar where a sweep is in play, price is in demand, an external CHoCH printed 6 bars ago and the close is a strong engulfing candle — that IB break is graded **A**, and if HTF/session/type/path also line up, **A+**.

The machine is exempt (it builds `mcTierL` from its own memory — that fix was V7-A6 and it is correct). **The nine engines, four P7 models and seven trap patterns are not.**

**Impact:** the entire tier ladder — the thing the whole file is organised around, the thing `tierMode` filters on, the thing the A+ alertcondition fires on — is **not a measure of the signal**. It is a measure of the bar's context, attached to whatever happened to trigger. This is the same class of defect as V7-A6 (*"the machine's A+ was decided by unrelated state"*), never applied to the other 20 producers.

**Why it survived six audits:** because each audit fixed the *terms* inside `f_tier` (V8-04 tightened the POI leg, V8-08 added exec quality, V9-07 added the shift-before-entry rule) and never questioned that one function serves 20 callers.

**Fix (the real one, ~180 raw tokens):** make `f_tier` take a producer profile.

```pine
// producer class: 0 narrative (machine/SB/FVG4) · 1 reversal-at-liquidity
// (CRT/TBS/HTF/doji/TL/trap) · 2 POI retest (zone50/FEM/QM/BRK) · 3 continuation (IB)
f_tier(bool isL, int pcls) =>
    ...
    // A requires the producer's OWN core layer, not the bar's:
    bool ownCore = pcls == 0 ? true :
                   pcls == 1 ? (isL ? sslInPlay : bslInPlay) :
                   pcls == 2 ? atPoi :
                               (isL ? extDir == 1 and htfB > 0 : extDir == -1 and htfB < 0)
    if hasLiq and atPoi and aTrig and hasExec and ownCore
        tier := 3
    // A+ additionally refuses pcls == 3 outright (a continuation break is never A+)
    if tier == 3 and pcls <= 2 and <existing A+ chain>
        tier := 4
```

Then call it per accepted producer inside the arbiter rather than once per side. **Cheap interim mitigation (~25 tokens):** cap tier at B for `sig3Long/Short` and for any candidate where `nEvL == 1 and clsL == 2` — a lone technical trigger is never an A.

---

### P0-2 — HTF alignment awards a free point

**Evidence:** [4323-4324]

```pine
htfAlnL = (htfB > 0 ? 1 : 0) + (nz(hStruct) > 0 ? 1 : 0)
        + (htfLive and not na(hPoiBTop) and close >= hPoiBBot ? 1 : 0) + (bD > 0 ? 1 : 0)
htfAlnS = (htfB < 0 ? 1 : 0) + (nz(hStruct) < 0 ? 1 : 0)
        + (htfLive and not na(hPoiSTop) and close <= hPoiSTop ? 1 : 0) + (bD < 0 ? 1 : 0)
```

**Root cause:** the HTF POI's own lifecycle in `f_htfPoi()` [2306-2311] deletes a bullish POI precisely when `close < bBot`:

```pine
if not na(bBot) and (close < bBot or bar_index - bBar > hPoiMaxAge or bIn > hPoiMaxTouch)
    bTop := na
    bBot := na
```

So **`not na(hPoiBTop)` already implies `close >= hPoiBBot`** for the entire life of the POI (modulo the one-HTF-bar `[1]` lag). The third term is a tautology: it is not "HTF POI on the trade's side", it is "an HTF bull FVG exists somewhere below".

Mirror-identical for shorts: a bear POI is alive while `close <= sTop`.

**Impact:** `v8ApHtf` defaults to **3 of 4**. With the POI term free whenever any HTF gap survives, A+ really needs **2 of the 3 real terms** (filter EMA · HTF rolling structure · daily EMA). The documented bar — *"A bullish EMA alone no longer makes an A+"* (V8-09) — is weaker than stated: a bullish EMA **plus a daily EMA in the same direction** (highly correlated by construction) makes A+ on the HTF leg. Feeds `f_tier` A+ [4095] and `mcApL/mcApS` [5001-5002], i.e. **both** A+ paths.

**Fix (~10 tokens, behaviour-tightening):** the script already computes the correct predicate one line above:

```pine
htfLocL = htfLive and not na(hPoiBTop) and low <= hPoiBTop and close > hPoiBBot   // [4321]
```

Swap the third term for `htfLocL` / `htfLocS`. Then the point means *"the entry candle is at the HTF POI"* — which is what the V8-09 tooltip claims and what `poiTL == 1` already uses [4047].

---

### P0-3 — POI and EXECUTION double-counted via the BPR retest

**Evidence:** `f_p3ZoneLife()` [2978-2988] — the BPR tap event requires a confirmation candle to be raised at all:

```pine
if z.isBull and low <= zt and close >= zb and zoneBullConf     // ← zoneBullConf
    z.tapped := true
    tapUp    := true
```

`tapUp` becomes `p3BprTapUp` [2993], which is then consumed as a **POI** in two places:

- `poiTL = htfLocL ? 1 : ... : p6InQmL or inOTEbuy or p3BprTapUp ? 3 : ...` [4047]
- `poiL = inDemand or inOTEbuy or p6InObL or p6InQmL or p6InFvgL or p3BprTapUp` [4900] — the POI layer of the v5 confirmation floor.

**Root cause:** the same candle is the evidence for two supposedly independent layers. `zoneBullConf` [1460] is *also* the `hasExec` term in `f_tier` [4089] and the `execQ` subject in M16E. So on a BPR-retest bar, one engulfing candle satisfies POI **and** EXEC, and lifts `poiTL` to 3.

This is structurally identical to **V9-07** (*"one candle could be the shift AND its own retest"*) and **V9-06** (*"the candle that CREATES a typed FVG counted as price at the FVG"*). The same audit pass fixed the shift/retest and creation/retest overlaps but not the POI/exec overlap one module over.

**Impact:** inflates `poiLong`/`poiShort` scoring and, via `poiTL <= 2` not being reachable here, mostly inflates the *floor* rather than A+. Lower blast radius than P0-1/P0-2, but it is a live double count in a file whose stated design rule is *"no double counting"*.

**Fix (~15 tokens):** split detection from confirmation.

```pine
// tap = price entered and held the zone; confirmation stays a separate layer
if z.isBull and low <= zt and close >= zb
    z.tapped := true
    tapUp    := true                       // POI layer
    tapUpConf := zoneBullConf              // EXEC layer, returned separately
```

Return both, feed `tapUp` to the POI layer and `tapUpConf` nowhere but the chip. The BPR box caption is unchanged.

---

### P0-4 — `usedPoiL` / `usedPoiS` erase themselves, defeating V9-10

**Evidence:** [4972-4973] and [5139-5146]

```pine
poiTopL = sigMCLong ? suLAnchorT : p6InFvgL ? p3BullTop : p6InObL ? p4ObBullTop
        : inDemand ? nbTop : p6InQmL ? p4QmBullTop : na
...
if anyLong
    lastLongSigBar := bar_index
    usedPoiL    := poiTopL          // ← unconditional, including na
    usedPoiBarL := bar_index
```

**Root cause:** `poiTopL` is `na` for any accepted long whose POI is an **OTE leg**, a **BPR retest**, an **HTF FVG POI**, or **no POI at all** (an IB break, a trendline sweep, a trap). Those are not rare — `poiTL == 1` (HTF POI) and `poiTL == 3` (OTE/QM/BPR) are two of the five POI tiers, and `f_v5Gate`'s `poiL` explicitly admits `inOTEbuy` and `p3BprTapUp`.

When such a signal is accepted, `usedPoiL := na` **wipes the remembered POI**, and `poiFreeL` [4978] then returns true for everything:

```pine
poiFreeL = na(poiTopL) or na(usedPoiL) or math.abs(...) > NEAR_LVL_ATR * atr or (aged out)
```

**Impact:** V9-10 (*"ONE POI, ONE PRIMARY ENTRY … stops the third entry from one FVG"*) is defeated by any intervening non-zone signal. The exact spam pattern the feature exists to kill — repeated entries off one FVG — reopens after a single OTE or trap entry on the other leg of the move.

**Fix (~12 tokens):** only overwrite on a real level, and give the "no POI" case its own answer.

```pine
if anyLong
    lastLongSigBar := bar_index
    if not na(poiTopL)
        usedPoiL    := poiTopL
        usedPoiBarL := bar_index
```

Consider also extending `poiTopL` to cover the OTE / HTF-POI cases (`htfLocL ? hPoiBTop : inOTEbuy ? oteBuyTop : na`) so those entries are deduped too.

---

### P0-5 — `f_zoneFree` destroys live zones for a candidate it then rejects

**Evidence:** [3283-3295]

```pine
f_zoneFree(bool isSup, float zTop, float zBot, int newScore) =>
    bool dup = false
    if array.size(zones) > 0
        for i = array.size(zones) - 1 to 0
            z = array.get(zones, i)
            if z.isSupply == isSup and not (zBot > z.zTop or zTop < z.zBot)
                if z.score >= newScore and not z.signaled
                    dup := true                  // ← reject the new zone…
                else
                    box.delete(z.bx)             // …but keep deleting others
                    line.delete(z.mid)
                    array.remove(zones, i)
    not dup
```

**Root cause:** there is no `break` after `dup := true`, and the delete branch is not guarded by `not dup`. The loop is a **single pass that both decides and mutates**. A new demand zone overlapping three existing ones — one strong (score 3, blocks) and two weaker (score 2) — is rejected **and** takes the two weaker zones with it.

**Impact:** silent POI loss. `nbTop`/`nbBot` [3389-3401], `inDemand`, `poiLong`, the machine's `tapZone` [4654] and the P7 BRK scan all read a registry that has been thinned by zones that were never replaced. Data-dependent and invisible — the chart just has fewer demand boxes than it should, and the dashboard "Next demand" row points further away.

**Fix (~35 tokens):** two passes — decide, then mutate.

```pine
f_zoneFree(bool isSup, float zTop, float zBot, int newScore) =>
    bool dup = false
    if array.size(zones) > 0
        for i = array.size(zones) - 1 to 0          // pass 1: decide only
            z = array.get(zones, i)
            if z.isSupply == isSup and not (zBot > z.zTop or zTop < z.zBot) and z.score >= newScore and not z.signaled
                dup := true
                break
        if not dup                                   // pass 2: evict the weaker
            for i = array.size(zones) - 1 to 0
                z = array.get(zones, i)
                if z.isSupply == isSup and not (zBot > z.zTop or zTop < z.zBot)
                    box.delete(z.bx)
                    line.delete(z.mid)
                    array.remove(zones, i)
    not dup
```

---

### P0-6 — The machine is invalidated by a zone it never tapped

**Evidence:** `f_zoneLoop()` [3170-3174] sets one global flag for the **whole registry**:

```pine
if (sup ? close > top : close < bot) and confirmed
    if sup
        invD := true
    else
        invU := true
```

consumed at [4624] / [4733]:

```pine
if suL >= 2 and zoneInvalidatedUp and na(suLFvgBar)
    suL := 0
    suLReason := "POI violated"
```

**Root cause:** `maxZones` defaults to **6 per side**. `invU` is true if *any* of up to six demand zones — plus OB companions, rejection blocks, breakers and mitigation blocks, all of which live in the same array — is violated on this bar. The machine's own POI is `suLAnchorT/suLAnchorB`, and it is never compared.

**Impact:** a valid long setup at stage 2/3 with a healthy anchor is killed because an unrelated stale demand zone 3 ATR lower finally broke. The dashboard prints `↳ POI violated` — the operator reads it as *"my POI broke"*, which is false. This is a **false-negative generator** on the primary signal path, and it is exactly the class of fault V5.3-F4 fixed for `trdDir` (*"the setup machine was locked out by an unrelated trade"*).

**Fix (~20 tokens):** test the machine's own anchor.

```pine
// v9 has the anchor for both the FVG and the zone case — use it
if suL >= 2 and not na(suLAnchorB) and close < suLAnchorB
    suL := 0
    suLReason := "POI violated"
```

and drop the `zoneInvalidatedUp` / `zoneInvalidatedDn` plumbing entirely (it is read nowhere else — ~30 tokens reclaimed, more than paying for the fix).

---

## 3. P1 findings

### P1-1 — The POI-location family never registers a close INSIDE the POI

**Evidence:** `f_p3Nearest` [3053] and `f_p4Nearest` [3706, 3709, 3713, 3716] both require the zone to be strictly on the far side of the close:

```pine
bool ok = ... and (isBull ? f.top <= close : f.bot >= close)      // f_p3Nearest
if okOb and z.isBull and zt <= close and ...                      // f_p4Nearest
```

**Consequence:** `p3BullTop` is always a gap whose **top is at or below the close**. Therefore `p6InFvgL = not na(p3BullTop) and low <= p3BullTop and close >= p3BullBot` [3999] can only ever mean *"this bar wicked into the next untouched gap below and closed back above its top"*.

The classic FVG entry — **close inside the gap** — is structurally unreachable. Same for corrected OBs and Quasimodo.

**Impact:** `poiTL == 2` (the tier that A+ requires via `poiTL <= 2`) is only reachable by wick-rejection, never by acceptance into the gap. `f_v5Gate`'s `poiL` and the P7 SB/QM entry conditions inherit the same narrowing. This is defensible as a *style* (wick-and-reject only) but it is **not what the code comments or tooltips describe**, and it silently removes a large share of legitimate POI entries.

**Fix:** decide deliberately. If wick-and-reject is intended, say so in the tooltips. If not, widen the scan to `isBull ? f.bot <= close : f.top >= close` (gap bottom at/below close = price is in or above it) and let `p6InFvgL` do the containment test it was written for.

### P1-2 — The trap engine's level is not the level the pattern is about

**Evidence:** [4451] and [4503]

```pine
float ltBrkLvlNow = not na(ltBrkUpLvl) and f_recent(ltBrkUpBar, 5) ? ltBrkUpLvl : lastRes
...
ltSLevel := ltBrkLvlNow        // for LT-2, LT-3, LT-5, LT-6 AND LT-7
```

LT-3 is about a **lower-wick pool** (`lt3PoolLow`). LT-7 is about a **supply zone** (`nsBot` / `nsTop`, [4426]). Both are armed with `ltBrkLvlNow` — a broken resistance — as their reference level. Worse, after 5 bars `ltBrkLvlNow` **falls back to `lastRes`**, which by then is typically a *different, newer* swing high.

**Impact:** `qS`'s "close back below the level" term, the `ltSNeedBelow` hard rule for LT-6, and the invalidation `close > ltSLevel + ltInvAtr * atr` [4493] all measure against a level unrelated to the arming pattern. The v9 §14 trap-quality count — presented as the fix for *"a wick + one red candle is not a trap"* — is partly measuring noise.

**Fix:** store the level with the arm, per pattern: `ltSLevel := lt7Arm ? nsBot : lt3Arm ? lt3PoolLow : ltBrkLvlNow`, and never fall back to a live `lastRes`.

### P1-3 — TP1 is placed beyond liquidity it ignores

**Evidence:** [5241-5242]

```pine
tp1Real := not na(t1) and d1 >= risk and d1 < rrMult * risk
tp1P    := tp1Real ? t1 : anyLong ? entryP + risk : entryP - risk
```

If the nearest fresh resting liquidity `t1` is **closer than 1R**, `tp1Real` is false and TP1 becomes a synthetic 1R — which sits **beyond** that level. The plan therefore asks price to trade through known resting liquidity to reach a target the script invented.

**Impact:** systematically optimistic TP1 in exactly the situation where it matters (tight structure, near-by opposing pool). `p2MinAtr` (0.5 ATR) filters *very* close levels out of the map entirely, but leaves the 0.5-ATR-to-1R band exposed.

**Fix:** three-way. `d1 < risk` → TP1 = `t1` and mark it `·liq <1R`; the operator sees the real geometry and can size or skip. Do not silently step over it.

### P1-4 — Same-session raids are still invisible

**Evidence:** `f_sesTrack` reports a raid only outside its own session [1820]:

```pine
if not active and confirmed
    if not na(hiLvl) and not hiSwept and high > hiLvl
```

and the arming test [1857-1858]:

```pine
sesArmLo = (asiaLoSw or lonLoSw or nyLoSw) and sesQ >= 3
```

**Root cause:** V7-A2 correctly diagnosed that *"f_sesTrack reports a raid only once its session is OVER"*, and fixed the **arming** side (any tracked level taken inside a trade window now arms). It did not fix the **detection** side: a level is frozen at session close, so a raid *of the current session's own high/low, during that session* is never an event at all.

**Impact:** the New York AM session raiding its own opening range low at 09:15 — an extremely common institutional pattern — produces no session-type sweep. It may still register as a swing or PD sweep, but `lastSslType` will be 1 or 4 rather than 3, which matters for `v8ApLiq`.

**Fix:** track a *running* session high/low alongside the frozen one and emit a raid event when the running extreme from earlier in the session is taken and reclaimed. Budget ~60 raw tokens; defer if tight.

### P1-5 — `f_taken` misses the equal-level replacement

**Evidence:** [1734-1740]

```pine
f_taken(float lvl, bool isHi) =>
    var bool t = false
    if lvl != lvl[1]
        t := false
```

**Root cause:** two things. (a) A new pivot at the **same price** as the previous one (equal highs — the pattern the EQ-pool engine exists for) leaves `t` latched `true`, so a genuinely fresh level is permanently marked CONSUMED. (b) `na != na` evaluates to `na`, which is falsy, so the `na → value` transition also does not reset.

**Impact:** `resTaken` / `supTaken` / `extResTaken` / `extSupTaken` feed the target map [3436-3437]. A latched-taken level is removed from the TP ladder and from the RR gate — so `v5RrOkL` can fail and **refuse an otherwise valid signal**, with the dashboard reporting `no target`. False negative, invisible.

**Fix (~8 tokens):** reset on the bar the level is *written*, not on value change:

```pine
resTaken = f_taken(lastRes, true, not na(lastResBar) and lastResBar == bar_index - pivLen)
// f_taken(lvl, isHi, isNew) => ... if isNew ... t := false
```

### P1-6 — `rangeSrc` silently re-wires the regime classifier

**Evidence:** `rangeSrc` [1098] chooses `rngHi/rngLo` [2330-2331], which produce `rngW` → `extRngAtr` [2378] → `regChop` [2382] → `regime`.

**Impact:** a switch presented under *"4 · POI — Dealing range / OTE"* changes **the regime engine, the chop suppression, the `v5RegUp` tier floor and the premium/discount rule for every reversal candidate**. Setting it to `Internal` narrows the measured range (internal pivots are closer together), which makes `extRngAtr < CHOP_RANGE_ATR` far more often, which turns CHOP on across the chart and suppresses the machine.

This is the same category as **V5.3-F1** (*"display toggles were gating detection engines"*) — a switch whose stated scope is much smaller than its real one.

**Fix:** either pin the regime to the external range unconditionally (`extRes - extSup`, ~6 tokens) or state the coupling in the `rangeSrc` tooltip. The first is correct — "regime" is an external-structure concept by the script's own ARCH-5 definition.

### P1-7 — Silver Bullet arms only on a PD sweep

**Evidence:** [4181, 4184]

```pine
[sbStL, sbL] = f_p7Sb(p7Enable and p7mSb and confirmed and pdlSweep, ...)
```

**Impact:** the entire V8-10 liquidity hierarchy (swing · EQ · session · PD · ext swing · PW) exists, is graded, is remembered per sweep — and the SB model ignores all of it except PDH/PDL. A London-session Asia-low raid followed by MSS and an FVG retrace inside the 10:00–11:00 window is **not** an SB fire.

**Fix (~6 tokens):** arm on the graded sweep instead: `sslInPlay and lastSslBar == bar_index and lastSslQual >= minArmQual` — identical to the machine's arm test, which is the correct ancestor.

### P1-8 — `dispUp`/`dispDn` mix a prior body with the current ATR

**Evidence:** [3266-3267]

```pine
dispUp = bullBar[1] and body[1] >= dispFactor * atr
```

**Impact:** on a volatility expansion, the current `atr` is larger than the ATR that was live when `body[1]` printed, so the previous candle is judged against a standard it never faced — zones stop being created exactly during the expansions that create the best zones. Small, systematic, direction-neutral.

**Fix (~4 tokens):** `body[1] >= dispFactor * atr[1]`. Apply the same reading to `f_dispQ`'s `body[1] >= BRK_BODY_ATR * atr` [2035].

### P1-9 — "At a POI" has two different definitions

**Evidence:** the tier ladder [4087] and the confirmation floor [4900] disagree:

```pine
bool atPoi = isL ? inDemand or p6InObL or p6InFvgL : ...             // f_tier — no QM, no OTE, no BPR
bool poiL  = inDemand or inOTEbuy or p6InObL or p6InQmL or p6InFvgL or p3BprTapUp   // f_v5Gate
```

**Impact:** a QM or OTE entry passes the Balanced floor but can never reach tier A, so it is admitted and then graded B — which then fails `v5RankL` in RANGING (where `v5RegUp` lifts the floor to A). The two gates fight each other, and the dashboard Verdict row says `clear` while the arbiter refuses with `tier<floor`. Operator-confusing.

**Fix:** one named helper, both callers. If QM/OTE genuinely should not reach A, say so in the floor's `whyL` string rather than admitting and then silently demoting.

---

## 4. P2 findings

| # | Finding | Evidence | Note |
|---|---|---|---|
| **P2-1** | `P3Zone` / `P4Zone` still read geometry back out of the drawing (`box.get_top`/`get_bottom`). V5.3-F2 fixed this for `Zone` and explicitly listed these two as **NOT FIXED**; v9 still has not fixed them. | [2972-2973], [3575], [3667-3668], [3703-3704] | **Latent, not live** — total box count is currently bounded (~60) by the family FIFOs, so the 500-cap deletion that makes `get_*` return `na` is not reachable today. It becomes live the moment any family cap is raised. Note also that `f_p4Life`'s deletion test `close < zb` with `zb = na` is falsy, so the zone would leak rather than fail loudly. Fix: add `zTop`/`zBot` fields, ~40 tokens. |
| **P2-2** | `corrRaw` issues a `request.security` call even when `v8CorrSym == ""`. | [2158-2159] | Burns one of the 64 output slots unconditionally. Pine has no conditional dependency, so the only real fix is to accept the cost or remove the feature. Document it. |
| **P2-3** | Label budget. Every chip, glyph and signal label is `label.new` with no delete; `max_labels_count = 500`. | [1007], `f_chipP`/`f_mark`/`f_bare` | TradingView silently drops the oldest. On a dense intraday chart the **v9 forensic journal tooltips on historical signals disappear** — the feature that exists for post-mortem review is the first casualty of the ink it competes with. Mitigation: ship `dcMode = "Clean"` (hides priority-2 glyphs) as the default, or delete glyph labels older than ~300 bars. |
| **P2-4** | Doji reversal requires trend *agreement*, not reversal context. | [3880-3883] — `ctxBias == -1` for a short | A "doji reversal" that needs `structDir` already down is a continuation pattern wearing a reversal name. Either rename it or invert the context test. Design decision, not a bug. |
| **P2-5** | Tooltip drift: `v5MinRr`'s tooltip references *"Require a KNOWN liquidity target"* — an input (`v8ReqTgt`) removed in the v9 size pass. | [4867] | Several v9-frozen constants still have stale prose. Sweep the tooltips against the v9 REMOVED list. |
| **P2-6** | `suLIn := inA` executes after the entry branch has already set `suL := 4`. | [4719], [4817] | Harmless today (stage 4 does not read `suLIn`), but it leaves the dashboard's `f_suTxt` reading a stale flag if stage 3 is re-entered. Move inside the `else` chain. |
| **P2-7** | `f_p7Sb`'s shift stage is not gated on `p7mSb`. | [4182] — the middle argument omits `p7mSb` | With the SB model switched off, the state machine still advances 1→2 (arm is gated, so it can never reach 1 — dead code today, live the moment arm gating changes). Tidy for symmetry. |

---

## 5. What is genuinely right (do not "fix" these)

Recording these so the next pass does not re-open them:

1. **Non-repainting discipline is correct.** `lookahead_on` + internal `[1]` is the documented idiom and V8-03 applied it consistently. All 7 security sites [1727, 1728, 2144, 2158, 2273, 2314] follow it. Every cross-bar mutation traces to `confirmed`.
2. **The arbiter is the right shape.** One decision per bar, rank = `tier × 10 + (2 − class)`, equal rank = no trade [5080-5090]. Keep it.
3. **Turtle-soup age math is correct.** `-ta.lowestbars(...)[1] + 1`. It has been "fixed" wrongly before — the note at [2243-2247] is right, leave it.
4. **The machine grading itself from its own memory** (`suLQual`/`suLType`/`suLSes`/`suLMssQ`/`suLPoiT`/`suLVisit`) is the correct answer to V7-A6 and is exactly what P0-1 asks you to do for the other 20 producers.
5. **`sslHeld`/`bslHeld`** in the in-play definition [1897-1900] is the right place for that test — V5-I1 got it right.
6. **The visit-based retest model** (V9-01) is a real improvement over the per-bar flag and is implemented correctly [4703-4719].
7. **`f_structure`'s protected-swing selection** [1969-1970] — `legPlB > legLoB ? legPl : legLo` — is correct and matches its comment. Do not invert it.
8. **The v5.3-F2 `zTop`/`zBot` fix on `Zone`** is correct and is the template for P2-1.

---

## 6. Remediation plan

Ordered by **(impact on signal quality) ÷ (token cost)**. Each phase is independently shippable and independently verifiable.

### Phase 1 — Stop the grade inflation (~60 raw tokens net, 3 changes)

| Change | Tokens | Effect |
|---|---|---|
| P0-2: `htfAlnL/S` third term → `htfLocL` / `htfLocS` | +2 | A+ HTF leg becomes real. **Expect A+ count to drop sharply — that is the point.** |
| P0-4: guard `usedPoiL/S` writes with `not na(poiTopL/S)` | +12 | V9-10 starts working. |
| P0-1 interim: cap tier at B for `sig3Long/Short`, and for `nEvL == 1 and clsL == 2` | +25 | Kills the worst of the inherited-tier problem without restructuring. |

**Verify:** load on 5m XAUUSD with `tierMode = "A+ only"`. A+ count before/after must fall materially. If it does not, P0-2 was not the binding constraint and you have learned something.

### Phase 2 — Stop the false negatives (~15 tokens net, frees ~30)

| Change | Tokens | Effect |
|---|---|---|
| P0-6: machine POI invalidation reads `suLAnchorB` / `suSAnchorT`; delete `zoneInvalidatedUp/Dn` | −30 +20 | Machine stops dying on unrelated zones. **Net token gain.** |
| P0-5: `f_zoneFree` two-pass | +35 | Zone registry stops losing POIs. |
| P1-5: `f_taken` reset on write, not on value change | +8 | Equal-high levels stop being permanently consumed. |

**Verify:** dashboard `◉ Setup long/short` rows should show materially fewer `↳ POI violated` invalidations. `⚙ Target` (showDbg) should stop reporting `none → TP synthetic` on bars where a visible swing high is clearly overhead.

### Phase 3 — Fix the double counts and the wiring (~50 tokens)

| Change | Tokens | Effect |
|---|---|---|
| P0-3: split BPR tap from BPR confirmation | +15 | Last documented double count closed. |
| P1-2: per-pattern trap levels | +25 | Trap quality count measures the right thing. |
| P1-6: pin regime to the external range | +6 | `rangeSrc` stops re-wiring the regime engine. |
| P1-8: `atr[1]` for `body[1]` tests | +4 | Zones survive volatility expansions. |

### Phase 4 — The structural fix (~180 tokens, needs budget)

P0-1 proper: `f_tier(isL, pcls)` with a producer class, called per accepted producer inside the arbiter. This is the change that makes the tier ladder mean what the README says it means.

**Where the budget comes from** — v9 sits at ~31,041 raw against a last-known-good compile of 31,112. Candidate removals, all display-only, in order of least loss:

- `dcPillC` / `p8Gap` / `dcChW` collapsed to constants (~40) — they are tuning knobs for a packer that already has sane defaults.
- The `⚙ Target` and `⚙ Reject` debug rows (~120) — they are developer rows, default OFF, and everything in them is derivable from the Verdict row.
- The `f_jour` journal string (~90) — valuable, but it is the newest feature and the label-budget problem (P2-3) already degrades it.

Phase 2 also returns ~10 net. **Recommendation: take Phases 1–3 first (~125 tokens, comfortably affordable), measure, then decide whether Phase 4 justifies cutting the debug rows.**

### Phase 5 — Deferred, listed so it is not forgotten

- P1-1: decide the wick-vs-close POI question deliberately.
- P1-4: same-session raid detection (~60).
- P1-7: SB arms on any graded sweep (~6 — cheap, do it with Phase 3 if convenient).
- P1-9: unify `atPoi` and `poiL`.
- P2-1: `zTop`/`zBot` on `P3Zone`/`P4Zone` — do this *before* raising any family cap, not after.
- P2-3: label-budget policy for the journal.

---

## 7. Regression checklist

Run after every phase. These are the properties that six audits' worth of fixes are protecting, and each has been broken at least once historically:

1. **No repaint.** Every `request.security` still `lookahead_on` + internal `[1]`. Every array/UDT mutation still behind `confirmed`.
2. **Display ≠ detection.** Toggle `showZones`, `showOB`, `showRB`, `showFlip`, `p4ShowOb`, `p4ShowQm`, `p3ShowBpr`, `p3ShowHch`, `showEq`, `showSesHL` **off** one at a time. Signal count must be **identical**. (This is V5.3-F1 / V5.2-V4 / V8-06 / V9-17 — the single most-repeated fault class in the file's history.)
3. **One decision per bar.** No bar ever carries both a LONG and a SHORT label.
4. **Machine liveness.** `◉ Setup long/short` never sits at stage 4 for more than the life of its own trade.
5. **Config guard.** Chart 1H + HTF 15m ⇒ dashboard title reads `⚠ CONFIG: HTF ≤ chart` and zero signals fire.
6. **Output budget.** Source `plot` + `plotchar` + `bgcolor` + `alertcondition` ≈ 25; security series ≈ 18; total ≈ 43 of 64. Any new visual uses labels/lines/boxes; any new alert uses `alert()`.
7. **Compile.** Raw token count stays under 31,112.

---

## 8. Closing note

The recurring pattern across v5 → v9 is worth naming, because it predicts where v10's faults will be:

> **Every fault this file has ever had lives in the seam between two subsystems, and every fix has been applied inside one of them.**

V5.3 called this out explicitly (*"six WIRING faults, all in the seams BETWEEN subsystems"*) and then the next four versions kept auditing subsystems. P0-1 (one tier function, 20 callers), P0-4 (one POI slot, many POI kinds), P0-6 (one invalidation flag, one registry, one machine), P1-2 (one level slot, seven patterns) and P1-9 (two definitions of "at a POI") are all the same shape: **a single-slot scalar serving multiple consumers that need different answers.**

The highest-value process change for v10 is not another feature. It is a rule: **when a scalar is read by more than one producer, either it is genuinely producer-independent, or it must become a function of the producer.** Applying that rule mechanically to this file would have caught five of the six P0s above.

---

*Source audit only — no compile, no backtest. Every line reference is to `Demand + Price Action-9.pine` as of 2026-09-15. Educational tooling; the tier ladder is narrative alignment, not win probability.*
