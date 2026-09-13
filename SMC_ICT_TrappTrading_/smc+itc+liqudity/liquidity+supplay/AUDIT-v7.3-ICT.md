# AUDIT-v7.3-ICT — the P1 residual ownership pass

**File:** `23.liquidty+supply-v7.3-ict.pine` (from `22.liquidty+supply-v7.2-ict.pine`)
**Date:** 2026-09-10
**Scope:** the four P1 residuals left by `AUDIT-v7.2-ICT.md`. No module added or
removed, no input added or removed, no producer rank, grade rung, score block or
alert name changed.

| Inventory | v7.2 | v7.3 |
|---|---|---|
| `alertcondition` | 34 | 34 |
| `input.*` | 166 | 166 |
| `type` | 7 | 7 |
| top-level `f_*` | 98 | 99 (`f_htfTier`) |
| `request.security` | 6 | 6 |
| tok (fit-B) | 32 052 | 32 073 |
| compiled (predicted) | 100 079 | 100 151 |
| compiled (true ≈ pred − 52) | ≈ 100 027 | ≈ **100 099** (cap 100 256, **157 spare**) |
| main body | 1 741 | **1 725** (cap ≈ 2 030) |

Net cost of the four fixes: **+21 tok**, after paying for them with the reclaim
classes v7.2 proved (pure-alias elimination, dead-guard deletion).

---

## P1-1 · S/D producer ownership gap

**Defect.** v7.2's BUG-02 fix required the live raid on that side to be spatially
CONTAINED in the zone the confluence producer was trading. Containment is not
identity: two raids of the same pool (`Pool.raidBar` is overwritten in place), or
two different pools inside one array, both pass it. The producer could therefore
still take its stop (`psl := anyExt`), its reason and — through the shared
`pr > PR_MACH` block — its raid grade from an event the zone was not built from.

**Fix.** MODULE 9 already stamps `srcPoolId` / `srcRaidBar` on every zone it
creates. `f_prod` now resolves one owned predicate, `sdOwn`, and demands the
stamped event *and* containment:

```pine
bool sdOwn = not na(sdZ) and sdZ.srcPoolId != 0 and sdZ.srcPoolId == anyId and
     sdZ.srcRaidBar == anyRb and anyExt <= sdZ.top + poiBindAtr * atr and
     anyExt >= sdZ.bot - poiBindAtr * atr
```

`anyRb` is a new parameter (`anyLoBar` / `anyHiBar` at the two call sites). The
branch gate became `(not needSweep or sdOwn)`, and the stop is now
`psl := sdOwn ? anyExt : na` — with the sweep requirement OFF the producer still
trades the 50 % retest, but an unowned wick can never be its stop; `f_sl` falls
back to the protected swing and the POI edge, both of which belong to the array.

`f_zoneFlip` additionally clears `srcPoolId` / `srcRaidBar`: a zone that changes
side was built from a raid on the *other* side, so its provenance is void.

## P1-2 · HTF FVG POI tier was frozen

**Defect.** Stage 3→4 stamped `s.poiTier := 1` for every HTF POI tap, and the
live re-grade in the invalidation block explicitly skipped `poiIsHtf`. So the FEM
producer held tier-1 (A+-eligible) status after the HTF array had been mitigated
and after the HTF itself had flipped against the setup.

**Fix.** One function, two call sites (the stamp and the per-bar refresh):

```pine
f_htfTier(bool isL) =>
    int(math.min(1 + nz(isL ? hPoiBIn : hPoiSIn, 0) + ((isL ? htfDir >= 0 : htfDir <= 0) ? 0 : 1), 3))
```

`hPoiBIn` / `hPoiSIn` are the HTF candle-inside counters the HTF feed already
returns (no new `request.security`). Fresh and aligned = 1, one candle inside =
2, more = 3, an opposed HTF costs one further tier, clamped at 3 — the same
monotone-worse ladder `f_regrade` applies to chart zones. The refresh line is now

```pine
if s.st >= ST_POI
    s.poiTier := s.poiIsHtf ? f_htfTier(isL) : f_zoneTier(s.poiZone)
```

(`f_zoneTier` is already na-safe, so the old `not na(s.poiZone)` guard went away.)

## P1-3 · Post-displacement integrity

**Defect.** Stage 6→7 ran with `(not moved or s.dispBar == bar_index)`, so the
execution FVG could be locked on the displacement bar itself. A candle that
expanded and was handed straight back still advanced the setup to ST_FVG.

**Fix.** Two branches in front of the FVG detection:

```pine
else if bar_index == s.dispBar
    blk := "awaiting post-displacement confirmation"
else if not (isL ? close > s.poiTop : close < s.poiBot)
    blk := "expansion given back into the POI"
```

The gap may only be locked on a later bar, and that bar must still be outside the
POI the expansion left. The MSS level is already covered by v7.1's ST_DISP
reversal kill, which runs at the top of every confirmed bar. `FVG_OWN_MAX = 2`
still allows two bars, and an expansion that leaves no gap still falls back to
ST_MSS.

## P1-4 · Elite trap residual contamination

**Defect.** The trap producer reached tier 1 / A+ in v7.2 but still read its raid
GRADE, pool CLASS, touch count and dedupe identity from `anyLoRq / anyLoKind /
anyLoPool / anyLoId`. That is the freshest raid anywhere on the side — and by
construction it can never be the pool the trap broke, because a broken pool is
`PS_DONE` and `f_findRaid` only returns `PS_RAID` / `PS_REACT`. The trap's grade
was therefore always somebody else's event.

**Fix.** The watch stamps the class of the pool it actually broke
(`var int wKnd = -1`, written at both arm sites as `tPoolU ? brkUpKind : -1`),
and `f_prod` overrides the four contaminated fields for a ① trap:

```pine
if pr == PR_TRAP and pa1
    rqv := trapQ
    rk  := wKnd
    tc  := 0
    pid := 0
```

`trapQ` is `f_trapQual` of the trap's own five ingredients, and it is `RQ_A`
exactly when `f_trapElite` is true, so the A+ rung's `rq == RQ_A` requirement is
unchanged and elite traps remain A+-eligible. What the trap does not own now
reads as unknown (`-1` is not a `PK_*` value → 0 pool-class points; no touch
credit; no borrowed pool identity in `f_dedupeOk`) instead of as an unrelated
event's quality. ② PinTrap (absorption, tier 3, display-only at the default
`minTier`) is untouched.

---

## Reclaim that paid for the pass (zero behaviour change)

| Item | tok |
|---|---|
| 5 `emit*` + `trapConf` + 3 `mach*New` aliases inlined into their one `alertcondition` each | −27 |
| `not na(anyLoBar/anyHiBar)` deleted from `confGateLong/Short` (`sslInPlay`/`bslInPlay` already prove the raid bar) | −12 |
| `not na(bBar)` / `not na(sBar)` deleted from `f_htfPoi`'s touch counters (written and cleared with `bTop`/`sTop`) | −12 |
| 4 na-guards deleted from `bullRange` / `bearRange` (a `Struct` writes `swHi` and `swHiBar` in one block, so `rangeOK` proves both stamps) | −24 |
| `not na(rbar)` deleted from `f_gradeZone` (`f_recent` is na-safe by definition) | −6 |
| `extResBar` / `extSupBar` / `htfPd` / `descNL` / `descNS` / `sslSweep` / `bslSweep` / `extHiRaidNow` / `extLoRaidNow` folded into their single use | −30 |

## Verification on a chart

1. **P1-1** — Debug panel, S/D line: with `needSweep` ON, a `Demand/Supply 50%
   retest` entry must now only appear where the zone's own stamped raid is the
   live raid. Expect materially fewer PR_SD signals on charts where the side is
   being raided repeatedly.
2. **P1-2** — Park on a FEM setup at an HTF POI and watch `POI · array` in the
   debug panel: `HTF T1` must degrade to `T2` / `T3` as HTF candles trade into
   the array or the HTF bias flips, and A+ FEM must stop appearing once it does.
3. **P1-3** — Any setup that reaches state 6 now shows `awaiting
   post-displacement confirmation` for exactly one bar before state 7. A
   displacement bar whose next bar closes back inside the POI must print
   `expansion given back into the POI` and never reach ST_FVG.
4. **P1-4** — On a ① trap entry, the dashboard raid grade must equal the trap's
   own `f_rqTxt(trapQ)` shown in the chip, and the pool-class score contribution
   must be 0 whenever `trapNeedPool` is OFF and no tracked pool broke.

## Known, unmodified

* `f_evTag(anyLoPool, "BEAR TRAP")` still writes the trap descriptor onto the
  live raid pool rather than the broken one. Making it owned would delete the
  descriptor entirely (the broken pool has left the registry), so this is left as
  the file's documented "one event, many descriptors" design. The descriptor
  allowance is capped at 6 and debited by congestion, and P1-4 removed its route
  into the LIQUIDITY block.
* `evPxL` / `evPxS` (the price half of the dedupe) still read `anyLoPx` /
  `anyHiPx` for non-machine producers.
* MODULE 9 stamps `srcPoolId` / `srcRaidBar` on a zone even when `liq` is false;
  P1-1 enforces containment at consumption time instead.
* Pine cannot be compiled locally. Token/main-body figures above are the
  validated fits from the lineage note, not TradingView output.
