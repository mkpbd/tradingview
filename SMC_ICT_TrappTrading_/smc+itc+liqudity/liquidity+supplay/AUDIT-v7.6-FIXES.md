# v7.6 — WHAT SHIPPED · `26.liquidty+supply-v7.6-ict.pine`

**Date:** 2026-09-15 · **From:** `25.liquidty+supply-v7.5-ict.pine` (file 25 untouched, lineage rule).
**Findings source:** `AUDIT-v7.5-FORENSIC.md` — all twelve findings fixed.
**Not compiled, not backtested.** Pine cannot be compiled offline; the standing lineage caveat applies.

---

## A · WHAT CHANGED, BY FINDING

| # | sev | fix | where |
|---|---|---|---|
| F-01 | P1 | reversal context uses the LOCATION test `atHtfPoiL/S`, not `not na(hPoi*Top)` | `htfRevLong` / `htfRevShort` |
| F-02 | P1 | a CE entry price is used only when the signal bar's range contains it | `ceRawL/S` → `entryPxL/S` |
| F-06 | P1 | the zone's MSS must break a level AT the zone, separated from the raid wick | `f_gradeZone` |
| F-04 | P2 | a proven BREAKER / IFVG inherits the failure's liquidity event as its chain | `f_zoneFlip` + zone loop capture |
| F-03 | P2 | the order block re-runs the containment test on its own edges | `f_mkZone` |
| F-05 | P2 | `Zone.tierW` makes the tier ratchet structural | `f_regrade` |
| F-08 | P3 | one trap watch per side (`Trap` UDT ×2) | MODULE 11 |
| F-09 | P3 | the HTF POI mitigation count is edge-triggered | `f_htfPoi` |
| F-10 | P3 | an HTF CONFLICT arms only the side structure favours | `htfCtxLong` / `htfCtxShort` |
| F-12 | P3 | the S/D producer reads its pool's touch history | `f_score` call |
| F-16 | P3 | `f_findRaid` reports `bound`; a claimed raid cannot stamp a new zone | `f_findRaid` / `f_gradeZone` |
| F-15 | P3 | the `◆` sweep marks are edge-triggered per level | MODULE 17 |

### Detail on the three that change trades

**F-01.** `htfRevLong = allowRev and htfDir < 0 and ((htfPd <= PD_EXTREME) or not na(hPoiBTop))`. The second
disjunct means "the HTF holds a live bullish FVG *somewhere*", which on a liquid instrument is nearly always
true — so the premium/discount EXTREME the `allowRev` tooltip advertises was bypassed and `htfCtxLong` became
tautological. A long setup armed on every bar of a bearish HTF, occupied the single long slot for `setupLife`
bars and could never grade (`revOk` demands CHoCH + T1 + RQ_A + `pdExt`). Now both the continuation and the
reversal verdict use `atHtfPoiL/S`, which was already computed one line above.

**F-02.** The S/D producer's trigger accepts a 50 % tap up to `confirmWin` (5) bars old, so the signal bar only
has to touch the zone's near edge and print a rejection — the zone midpoint can sit far below its low. The
machine has the same hole whenever `retestDepth < 0.5` (the input allows 0.0). v7.5 measured `riskL`, `rrL`,
`roomL` and the whole TP ladder from that midpoint. The CE level is now used only when `ceRaw >= low and
ceRaw <= high`; otherwise the entry is the rejection close, as in the v7.3 model.

**F-06.** `f_gradeZone` read `iChDnBar` / `cisdDnBar` — the chart-wide latest internal shift — and constrained
only its timing. A shift thirty ATR away promoted an array to T1. The added `mAt` test requires the broken
level (`sInt.evLvlDn/Up`, or the CISD run open) to sit within `sdRaidAtr` of the zone AND to be at least
`MSS_MIN_SEP_ATR` from the raid wick — the machine's own stage-5 rule, applied to the zone's chain.

### Detail on the one that adds setups

**F-04.** `f_zoneFlip` zeroed `srcPoolId`, and `f_zoneProv` only ever ran at creation, so `PA_BRK` and
`PA_IFVG` — the two arrays `f_paRank` ranks **above** a raw FVG — were permanently untradeable by the S/D
producer. That is backwards: a flip whose `isBrk` chain holds (a liquidity event AT the zone, then
displacement, then a structure shift) has *stronger* evidence than the gap it replaces.

The zone now records the raid at it in full — `failBuy`, `failId`, `failBar`, `failExt`, `failPx`, `failRq`,
`failKind`, `failTag` — instead of the bare `liqBeforeFail` boolean, because the re-stamp has to know whether
the liquidity that paid for the failure was BSL or SSL. At the flip:

```
rest = isBrk and liqBeforeFail and failId != 0 and failBuy == toSup
```

A DEMAND breaker (`toSup == false`) is paid for by a SELL-side raid; a SUPPLY breaker by a buy-side one.
Anything short of that clears to nothing, exactly as v7.5 did. All twelve `src*` fields are written
unconditionally — v7.5 left nine of them behind as stale values, unreachable only because of the `srcPoolId`
gate, which was a loaded gun for any future edit.

Tier is unchanged: a flipped OB / rejection zone reaches T2 and is tradable at the default `minTier`; a flipped
FVG is a FAILED FVG at T3 and only reaches T2 through the IFVG promotion, which already demands a return, a
hold and a rejection.

---

## B · HOW IT IS PAID FOR

No feature is cut. Two structural reclaims, both behaviour-identical, both the pattern v7.5 itself used (R1
`f_mkZone`, R3 `f_ctxBox`, R4 `f_entryLbl`):

**R1 · the zone violation and re-grade, written once.** The two side branches of the zone update loop spelled
an identical violation block and an identical eligibility test, so `f_zoneFlip` (517 src) and `f_regrade` were
each inlined **twice**. This is the duplication v7.5's own R1 removed from the zone CREATION path and left
behind on the UPDATE path. The side-specific work (leg extreme, `inS`/`inD`, mitigation count, fill depth,
50 % tap, IFVG promotion) stays in its branch; the violation, the re-grade, the eligibility test and the
candidate write are now written once against a `sup` flag.

**R2 · the nine debug state rows, written once.** Nine inlined copies of `f_dbgRow` (150 src each) spelling one
pattern — the state constants `ST_CTX … ST_ENTRY` **are** 1 … 8, so row *r* is ticked when `st >= r`. Row 9 is
the emission, which is not a state. Same nine rows, same labels, same colours. The lineage's rule is never to
*cut* the debug panel; nothing here is cut.

---

## C · BUDGET

The lineage's published fit (`3.422 · src_tokens − 9 411`) cannot see inlining: removing a *call site* deletes a
whole function body from the compiled output but changes the source count by one line. Re-fitted here on the
only two **measured** CE10117 figures in the lineage — file 14 = 99 740 and file 17 = 108 630 — against an
inline-**expanded** metric (`source tokens + Σ body × (call sites − 1)`), which is what the cap actually counts:

```
compiled ≈ 1.8102 · M − 4 684        M = src + inline expansion
```

Both measured points are reproduced exactly by construction; the fit then puts v7.4 at ≈ 100 243 and v7.5 at
≈ 99 613, i.e. ~650 above the lineage's own source-token estimates for the same files — consistently
conservative, which is the right direction for a cap.

| file | src | inline expansion | M | predicted compiled | vs cap 100 256 |
|---|---|---|---|---|---|
| 14 (v6.0) | 36 959 | 20 727 | 57 686 | **99 740** (measured) | — |
| 17 (v6.2) | 39 970 | 22 627 | 62 597 | **108 630** (measured) | — |
| 25 (v7.5) | 36 475 | 21 141 | 57 616 | ≈ 99 613 | 643 spare |
| **26 (v7.6)** | **37 006** | **20 065** | **57 071** | **≈ 98 627** | **≈ 1 630 spare** |

v7.6 is ≈ 990 compiled tokens **lighter** than v7.5 with all twelve fixes in. Top-level statements 964 → 951,
so CE10295 is not in play. Before R1 and R2 the same fit put v7.6 at ≈ 100 953, i.e. ~700 **over** — the
reclaims are not cosmetic, they are what makes the release fit.

---

## D · VERIFICATION ON A CHART

| # | check | expect |
|---|---|---|
| 1 | it compiles | note the real CE10117 figure back into the lineage header; this fit predicts ≈ 98 627 |
| 2 | bearish HTF, price at equilibrium, `allowRev` ON, no HTF demand array at price | debug row 1 LONG `✗`, BLOCKED reads "HTF context not aligned". v7.5 showed `✓` and then stalled for 60 bars |
| 3 | S/D entry whose 50 % tap was 4 bars ago, `entryModel = FVG 50% (CE)` | entry = the rejection close, not the zone midpoint. RR drops and may now fail `hRr` — that is the correct answer |
| 4 | demand FVG whose only internal CHoCH in the window broke a level far from the zone | grades T2, S/D does not fire, debug says "no producer" |
| 5 | supply zone swept on the sell side, then closed through upward with displacement + CHoCH | box reads `BREAKER ▲ T2`, and an S/D entry on it shows the SSL pool id in `story` — new in v7.6 |
| 6 | FVG closed through with displacement, later returned to and held | `IFVG ▲ T2`, tradable by the S/D producer if the flip re-stamped |
| 7 | demand OB under a T1 gap whose sweep low is 2 ATR below the OB | OB prints T2, not T1 |
| 8 | zone T1 → HTF flips → T2 → HTF flips back | stays T2 |
| 9 | long-side structural break, then a short-side failed breakout within 8 bars | both traps available; in v7.5 the short trap never armed |
| 10 | HTF CONFLICT with structure bearish | only the SHORT slot arms; LONG shows "HTF context not aligned" |
| 11 | price wicking under the same swing low for five bars | one `◆`, not five |
| 12 | debug panel rows 1-9 | unchanged text, unchanged ticks |
| 13 | alert list | all 33 names unchanged |

---

## E · WHAT WAS NOT DONE, AND WHY

* **No new confluence** — no volume, no oscillator, no extra pattern, no second displacement definition. This
  file's failure mode has never been too few conditions; it has been conditions belonging to a different event.
* **No threshold was loosened** to offset F-06 tightening the S/D producer. If frequency is wanted, F-04 is the
  honest source of it.
* **`f_mkZone`'s two call sites were NOT merged** (a further ~527 M of reclaim). It would pass `isSupply` as a
  *series* into `f_newZone`, and `box.new`'s `text_valign` may require a const — this lineage has already hit
  that exact class of error once (`plotshape` / `box.new` wanting a const text size). Not worth a compile
  failure for headroom that is no longer needed.
* **Still open from the v7.5 audit's own "known and left" list:** congestion double count · `legHi/legLo`
  extending through `ST_DISP` · `poiFresh` frozen at tap · the double-counted structural break in
  `f_structUpdate` · `f_tfUp`'s qualifier chain being unverifiable offline. None of these was a v7.5 finding.
