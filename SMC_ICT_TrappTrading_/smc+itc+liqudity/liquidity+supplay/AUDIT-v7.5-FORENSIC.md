# FORENSIC AUDIT — `25.liquidty+supply-v7.5-ict.pine`

**Date:** 2026-09-15 · **Subject:** file 25, 6 340 lines (code from line 1 313), `@version=6`.
**Method:** full static read of every module, producer, gate, `request.security` and state latch.
Cross-checked against `AUDIT-v7.5-CAUSAL.md` so nothing that document already lists as
*known-and-left* is re-reported as new. **Nothing here is compiled or backtested** — Pine cannot be
compiled offline. No code was changed by this audit; it is a findings + plan document.

---

## A · VERDICT

The causal spine is sound and is the best part of the file. `ctxBar < tgtBar < raidBar ≤ poiBar <
mssBar < dispBar ≤ fvgBar < retestBar` is enforced by stamped bars, re-derived independently in
`f_narrOk`, and the machine binds a **pool object**, not a price. Every state latch that matters sits
inside `if confirmed`. The v7.5 work (zone provenance, HTF state, removal of `confGate*`) closed the
three borrowings that used to decide trades, and I could not find a fourth of that class.

What is left splits into two piles:

* **Three defects that change trades today** — F-01, F-02, F-06.
* **A coverage inversion**: the PD arrays the file's own `f_paRank` ranks *highest* — breakers and
  IFVGs — are the only arrays the S/D producer can **never** trade (F-04).

Everything else is quality, honesty-of-comment, or ranking bias.

---

## B · FINDINGS

| # | sev | finding | where |
|---|---|---|---|
| F-01 | **P1** | Counter-HTF reversal context is granted by the mere EXISTENCE of an HTF POI, not by price being at one | L2544-2545 |
| F-02 | **P1** | The CE entry price can be a level the signal bar never traded — RR, risk and every gate are then computed off an unfillable fill | L5651-5652 |
| F-06 | **P1** | A zone's "owned" MSS is still the chart's latest internal CHoCH / CISD; only its TIMING is constrained, never its location | `f_gradeZone` |
| F-03 | P2 | An order block inherits a containment test that was run against the FVG's coordinates, not its own | `f_mkZone` |
| F-04 | P2 | A flipped zone (BREAKER / IFVG / MITIGATION) can never be traded by the S/D producer, ever | `f_zoneFlip` + `f_zoneProv` |
| F-05 | P2 | `f_regrade` is not monotone: the HTF and structure penalties are reversible, which is the transient re-promotion its own comment forbids | `f_regrade` |
| F-08 | P3 | One global trap watch (`wState` is a scalar) — a long-side break blocks every short-side trap until it expires | MODULE 11 |
| F-09 | P3 | The HTF POI counts CANDLES INSIDE, not discrete mitigations — chart zones got edge-triggered `mitN` in v7.5, the HTF array did not | `f_htfPoi` |
| F-10 | P3 | During HTF CONFLICT both direction slots arm, so the least readable HTF state generates the most candidates | L2551-2552 |
| F-12 | P3 | The S/D producer never fills `tc` (pool touches) and forfeits up to 3 LIQUIDITY points it has evidence for | `f_prod` |
| F-16 | P3 | `f_findRaid` does not exclude `bound != 0`, so a raid already claimed by a machine setup can still stamp a new zone | `f_findRaid` |
| F-15 | P3 | The `◆` sweep marks re-print on every bar price sits beyond the last swing, not once per sweep | MODULE 17 |

### F-01 · reversal context is effectively unconditional (P1)

```pine
htfRevLong  = allowRev and htfDir < 0 and ((not na(htfPd) and htfPd <= PD_EXTREME) or not na(hPoiBTop))
htfRevShort = allowRev and htfDir > 0 and ((not na(htfPd) and htfPd >= 1 - PD_EXTREME) or not na(hPoiSTop))
```

`hPoiBTop` is na only when the HTF currently holds **no live bullish FVG at all**. On any liquid
instrument that is rarely true, so the second disjunct is true almost always and `htfRevLong` collapses
to `allowRev and htfDir < 0`. The HTF premium/discount EXTREME that the `allowRev` tooltip advertises is
bypassed, and `htfCtxLong` becomes tautological — which also defeats the purpose of `needHtfAlign`.

The continuation verdict one line above already does this correctly, with the location test:

```pine
htfContLong = htfDir > 0 and (na(htfPd) or htfPd <= 0.5 or atHtfPoiL)
```

**Consequence today:** a long setup arms on every bar of a bearish HTF. It occupies the single long slot
for up to `setupLife` (60) bars. It cannot emit — `revOk` in `f_grade` demands CHoCH + T1 + RQ_A +
`pdExt` and returns `GR_NONE` otherwise — so this is lost opportunity and debug noise rather than a bad
trade. But it is a hard gate the code claims to apply and does not.

**Fix:** `not na(hPoiBTop)` → `atHtfPoiL`, `not na(hPoiSTop)` → `atHtfPoiS`. `f_atHtfPoi()` is already
computed immediately above and is reused by the score and the debug panel — negative token cost.

### F-02 · the CE entry price can be unreachable on the signal bar (P1)

```pine
entryPxL = ceMode and prodL > 0 and prodL <= PR_MACH ? upS.fvgTop - 0.5 * upS.fvgH
         : ceMode and prodL == PR_SD ? (sdTopLong + sdBotLong) / 2 : close
```

For the **machine** this is safe at defaults only: the retest stage requires
`low <= s.fvgTop - retestDepth * h`, so with `retestDepth = 0.5` the gap's 50 % was genuinely traded on
the signal bar. Set `retestDepth` below 0.5 — the input allows 0.0 — and the CE entry becomes a price
the bar never reached.

For the **S/D producer** it is not safe at any setting. The trigger is:

```pine
z.tap50Bar >= 0 and bar_index - z.tap50Bar <= confirmWin and zoneBullConf and low <= top
```

The 50 % tap may be up to `confirmWin` (default 5) bars old. All this bar has to do is touch the zone's
upper edge and print a rejection. The zone midpoint can therefore sit well below the signal bar's low,
and `riskL`, `rrL`, `roomL`, `f_tp`'s clamp and every RR gate are computed from a fill that was not
available. RR is overstated in exactly the direction that passes gates.

**Fix:** gate the CE substitution on the level having been traded on the signal bar —
`ceMode and (isL ? low <= ce : high >= ce)` — and fall back to `close` otherwise. One comparison per
side. This is the same honesty rule `f_tp` already applies to TP2 (V5.1-A1).

### F-06 · the zone's MSS is the chart's MSS with a clock on it (P1)

```pine
int chB  = isSupply ? nz(iChDnBar, -1) : nz(iChUpBar, -1)
int ciB  = isSupply ? nz(cisdDnBar, -1) : nz(cisdUpBar, -1)
int mbar = chB > ciB ? chB : ciB
...
bool mss = liq and mbar > nz(rbar, 99999999) and mbar <= bar_index - 1 and lvlB >= nz(rbar, 0) - mssWin
```

`iChDnBar` / `cisdDnBar` are the chart-wide latest internal shift bars — the same class of global that
v7.5 removed from `confGate*`. What v7.5 added here is **chronology** (after the raid, at or before the
displacement) and a **level-age** test (`lvlB >= rbar - mssWin`). Neither is a statement about
*location*. A shift that happened 30 ATR away, in the window between the raid and the displacement,
promotes the zone to T1 and hands the S/D producer its entire reason for existing.

The machine's own stage 5 is stricter: it additionally requires
`math.abs(lvl - s.liqExt) >= MSS_MIN_SEP_ATR * atr` and reads the level from its own `sInt` event
fields. The zone grader borrows the bar and not the level.

**Fix:** apply the machine's spatial constraint to the zone — the broken level must sit at the zone, and
be separated from the raid extreme:

```pine
float mlvl  = mbar == chB ? (isSupply ? sInt.evLvlDn : sInt.evLvlUp)
                          : (isSupply ? bullRunOpen : bearRunOpen)
bool  msep  = not na(mlvl) and math.abs(mlvl - rpx) >= MSS_MIN_SEP_ATR * atr
bool  mnear = not na(mlvl) and mlvl <= zTop + sdRaidAtr * atr and mlvl >= zBot - sdRaidAtr * atr
bool  mss   = liq and msep and mnear and mbar > nz(rbar, 99999999) and mbar <= bar_index - 1 and lvlB >= nz(rbar, 0) - mssWin
```

This is the single highest-value change in the list: it is the last global input to a T1 tier, and T1 is
what `minTier`, `f_grade`'s A+ rung and the S/D producer are all built on.

### F-03 · the order block borrows the gap's spatial test (P2)

```pine
[tZ, liqZ, smZ, mchZ] = f_gradeZone(isSupply, zTop, zBot)   // the GAP's coordinates
...
Zone ob = f_newZone(isSupply, obT, obB, tZ, ...)
f_zoneProv(ob, isSupply, liqZ, smZ, mchZ, dq)               // liqZ was proved against the GAP
```

`liqZ` means "the raid wick sits at **this array's** origin", and it was evaluated against `zTop/zBot`.
The OB is a different box, one to three candles earlier, at a different price band. It then inherits T1
and a full provenance stamp on evidence never tested against it. Because a demand OB usually sits
*below* the gap and closer to the sweep low, this mostly under-rewards rather than over-rewards — but it
is provenance by assertion, the exact failure the module header names.

**Fix:** `[tO, liqO, smO, mchO] = f_gradeZone(isSupply, obT, obB)` and stamp the OB from its own tuple.

### F-04 · the highest-ranked PD arrays are the least tradable (P2)

`f_zoneFlip` zeroes `srcPoolId`, and `f_zoneProv` is only ever called from `f_mkZone` at creation. A zone
that flips to BREAKER, MITIGATION or (later) IFVG therefore has `srcPoolId == 0` **permanently**, and
both S/D gates read:

```pine
if eligD and z.srcPoolId != 0 and not na(z.srcMssBar) and ...
```

So `PA_BRK` and `PA_IFVG` — which `f_paRank` ranks **above** a raw FVG, and which ICT treats as primary
entry arrays — are structurally excluded from the only producer that trades arrays. They survive only as
machine-bindable POIs, where the machine re-proves everything itself and never reads the stamp.

Secondary: the flip clears `srcPoolId` and `srcRaidBar` but leaves `srcRaidExt`, `srcRaidPx`,
`srcRaidRq`, `srcRaidKind`, `srcRaidTag`, `srcMssBar`, `srcDispBar`, `srcDispQ` and `srcIdm` stale.
Unreachable behind the `srcPoolId != 0` gate today; a loaded gun for any future edit.

**Fix, in two parts.**

1. Clear the whole chain in `f_zoneFlip`, not two fields of it.
2. Re-stamp at the flip. The zone already records `liqBeforeFail` — the evidence that a liquidity event
   happened AT it. Store the pool id alongside that flag (`z.failPoolId`), and on a flip whose `isBrk`
   chain holds (liquidity at the zone + displacement + structure shift), write a fresh provenance chain
   from that pool. A breaker with a proven raid, displacement and shift is a *better*-evidenced array
   than the raw FVG the producer trades today. Same for the IFVG promotion, which already demands a
   return, a hold and a rejection.

This is the one change that adds signals, and it adds them by promoting arrays the file already grades
as superior — not by loosening a threshold.

### F-05 · `f_regrade` is not the ratchet its comment claims (P2)

```pine
// The tier can only ever get WORSE than the one the zone was born with, which is
// what stops a stale POI from being re-promoted by a transient alignment.
f_regrade(Zone z) =>
    int t = z.tier0
    ...
    if not (z.isSupply ? htfDir <= 0 : htfDir >= 0)
        t := t >= 3 ? 3 : t + 1
```

`t` is rebuilt from `tier0` on every confirmed bar. The `state` and `mitN` penalties are monotone
because those fields are monotone. The **HTF and structure penalties are not**: a T1 demand zone
downgraded to T2 when the HTF flipped bearish is restored to T1 the instant the HTF flips back — exactly
the transient re-promotion the comment says it prevents. The machine reads `f_zoneTier` live every bar,
so this feeds `hTierL`, `f_grade`'s A+ rung and the score.

**Fix (pick one, and make the comment match):** add `int tierWorst = 3` to `Zone`, keep
`z.tierWorst := math.max(z.tierWorst, t)` and publish that. One int field, two statements. If
reversibility is *wanted* — a zone that survived an HTF wobble is arguably still good — then delete the
sentence from the comment. What is not acceptable is code and comment disagreeing about a T1 tier.

### F-08 / F-09 / F-10 / F-12 / F-16 / F-15 (P3)

* **F-08** `var int wState` is a single scalar. A structural break up arms the watch; until
  `maxAfterBrk` (8) bars pass, a runaway, or a fired signal, **no short-side trap can arm**. For a
  pattern v7.1 promoted to A+-eligible, a shared slot is an odd constraint. Mirror the seven `w*`
  variables per side if the trap is to stay a primary model.
* **F-09** `f_htfPoi` does `bIn += 1` for every HTF candle with `low <= bTop`. That is dwell time, not
  mitigation. Price parked just inside the array retires it in `hPoiMaxTouch` candles without ever
  leaving. The chart-zone side got edge-triggered `mitN` in v7.5 (`if inD and not z.inZ`); the HTF side
  should get the same two lines inside the request.
* **F-10** `htfCtxLong` and `htfCtxShort` both carry `(htfConf and htfConfMode != "Block")`, so both
  slots arm during CONFLICT. Emission is controlled ("A+ only" by default); arming is not. With F-01
  this is where most of the wasted setup lifetime goes.
* **F-12** the `f_prod` S/D branch leaves `tc = 0`. The pool is looked up by identity at consumption
  (`f_poolById`), so the data is reachable — the producer simply is not asking. It costs the S/D
  producer up to 3 of 25 LIQUIDITY points: a systematic ranking bias against it.
* **F-16** `f_findRaid` filters on `state`, `spent` and `f_recent`, but not on `bound`. So a raid a
  machine setup has already claimed can still be stamped onto a new zone by `f_zoneProv`, giving two
  producers one event. `machFirst` and the pool dedupe bound the damage; `f_anyRaid` directly below it
  *does* check `p.bound == 0`, so the asymmetry looks unintentional.
* **F-15** `plotchar(showSweeps and confirmed and low < lastSup and close > lastSup, ...)` is a level
  test, not an event test, so it re-prints on every bar that wicks under the same swing. Display only.

---

## C · REPAINT / LOOKAHEAD — RE-VERIFIED

| area | verdict |
|---|---|
| `request.security` × 6 (`f_bias`, `f_htfCtx`, PDH/PDL, PWH/PWL, `f_htfStruct`, `f_htfPoi`) | **clean.** Every one indexes `[1]` INSIDE the requested expression and uses `lookahead_on`; every TF goes through `f_tfUp`, including the `"D"` and `"W"` calls v7.5 fixed. Checked call by call. |
| pivots | **clean.** `ta.pivothigh/low(n, n)` throughout; a pool is back-dated to the pivot bar but registered on the confirming bar. I specifically tested whether the `pvLen`-late `s.swHi := pvH; s.hiBroken := false` in `f_structUpdate` can declare a BOS on an already-broken level: it cannot. `ta.pivothigh` requires strictly higher on both sides, so no bar in the confirmation window has a high above the pivot, and `close ≤ high`. **Not a bug.** |
| `[1]` / `[2]` / `[3]` reads | **clean.** `zDispUp = bullBar[1] …`, `dqUp[1]`, `bullFVG[1]`, `nbTop[1]`, `dispUpBar[1]`, the OB's `bullBar[2..4]` — all history of series already final on those bars. |
| state mutation | **clean.** Structure, CISD runs, registry scan, zone loop, trap watch, run engine, machine and consumption are all inside `if confirmed`. The two exceptions are `f_sesTrack`'s live hi/lo and `f_chip`'s lane counter, both `var` state that TradingView rolls back per tick. |
| v7.5 state | `Zone.mitN/inZ/legExt/ifvgPend` mutate inside the confirmed zone loop; `storyKeys` is pushed inside `if finalLong/Short`; the HTF state is a pure function of closed-HTF series. **Clean.** |
| alerts / plots | every `[SIGNAL]` reads `finalLong/finalShort`; `[TRIG] IFC` carries its own `and confirmed`; the structure and CISD conditions are confirmed-gated at source. **Clean.** |
| deliberate intrabar | `showDev` only. Dim, no state, no alert — correctly scoped. |
| unverifiable offline | `f_tfUp`'s `simple string` qualifier chain, and the lineage assumption that Pine evaluates both ternary branches (treated as true; every object deref sits inside an `if` body or an na-safe helper). |

**No repaint or lookahead defect found in v7.5.**

---

## D · IMPROVEMENT PLAN

Ordered by signal quality per compiled token. Nothing below adds an indicator; every item tightens or
correctly re-uses evidence the file already computes.

**Tier 1 — do these. They change trades, and all four are small.**

| # | change | effect | ≈ tokens |
|---|---|---|---|
| 1 | **F-06** · the zone's MSS must break a level at the zone, separated from the raid extreme | removes the last global input to a T1 tier; fewer, better-owned S/D entries | +80 |
| 2 | **F-02** · CE entry only when the signal bar traded the CE level | kills phantom RR; affects every gate downstream | +30 |
| 3 | **F-01** · reversal context uses `atHtfPoiL/S`, not `not na(hPoi*Top)` | the advertised premium/discount-extreme rule starts working; frees the setup slots | −5 |
| 4 | **F-03** · the OB gets its own `f_gradeZone` call | provenance stops being asserted | +70 |

**Tier 2 — the one change that adds setups, and it adds good ones.**

| # | change | effect | ≈ tokens |
|---|---|---|---|
| 5 | **F-04** · clear the full provenance chain on a flip, record `failPoolId` with `liqBeforeFail`, re-stamp a proven BREAKER / IFVG | makes the two arrays `f_paRank` ranks highest tradable by the S/D producer, on evidence stronger than the raw FVG it trades today | +180 |

**Tier 3 — correctness of claim, and ranking fairness.**

| # | change | effect | ≈ tokens |
|---|---|---|---|
| 6 | **F-05** · `Zone.tierWorst` ratchet (or fix the comment) | a T1 stops coming back from the dead | +25 |
| 7 | **F-12** · S/D fills `tc` from `f_poolById(true, sdPid)` | removes a systematic score bias against the S/D producer | +15 |
| 8 | **F-09** · edge-trigger the HTF POI mitigation count inside the request | an HTF array stops dying of dwell time | +40 |
| 9 | **F-16** · `f_findRaid` also requires `p.bound == 0` | one event, one producer | +8 |

**Tier 4 — only if budget allows** (v7.5 ships with ≈ 1 330 spare by the lineage's own fit).

| # | change | ≈ tokens |
|---|---|---|
| 10 | **F-08** · per-side trap watch | +120 |
| 11 | **F-10** · during CONFLICT, arm only the side the HTF *structure* favours | +10 |
| 12 | **F-15** · make the `◆` marks edge-triggered | +10 |

Tier 1 + 2 + 3 is ≈ 440 compiled tokens against ≈ 1 330 spare — no cut order needs to be invoked.

### What I deliberately do NOT recommend

* **No new confluence.** No volume, no oscillator, no extra pattern, no second displacement definition.
  This file's failure mode has never been too few conditions; it has been conditions that belong to a
  different event.
* **No relaxing** of `poiBindAtr`, `dispBodyAtr`, `DISP_HOLD_FRAC` or `lateBars` to raise frequency. If
  frequency is the goal, item 5 is the honest way to get it.
* **Do not remove the MSS requirement from the S/D producer** to compensate for item 1 tightening it. A
  producer that trades an array with no shift behind it is the v6.4 behaviour this lineage spent three
  versions removing.

---

## E · CHART VERIFICATION AFTER ANY OF THE ABOVE

| # | check | expect |
|---|---|---|
| 1 | compiles; note the real CE10117 figure | the lineage's fit predicts ≈ 98 930 before these changes |
| 2 | bearish HTF, price at equilibrium, `allowRev` ON | after item 3: debug row 1 LONG shows `✗`, BLOCKED reads "HTF context not aligned". Before: `✓`, then a stall |
| 3 | an S/D entry whose 50 % tap was 4 bars ago, `entryModel = FVG 50% (CE)` | after item 2: entry price is the rejection close, not the zone midpoint; RR drops and may fail `hRr` — that is the correct answer |
| 4 | a demand FVG graded T1 while the only internal CHoCH in the window broke a level far from the zone | after item 1: the zone grades T2, the S/D producer does not fire, debug says "no producer" |
| 5 | an FVG closed through with displacement, then returned to and held | after item 5: `IFVG ▲ T2`, and its `story` on an S/D entry shows the pool id of the raid that broke it |
| 6 | a demand OB under a T1 gap whose sweep low is inside the OB but 2 ATR under the gap | after item 4: the OB keeps T1 on its own test; before, it inherited it |
| 7 | zone T1 → HTF flips → T2 → HTF flips back | after item 6: stays T2 |
| 8 | a long-side structural break, then a short-side failed breakout inside 8 bars | after item 10: both traps available; before, the short trap never arms |
