# patch_G4 — HTF structure / HTF POI / S-1 continuation (v3.8.5, 5701 lines)

Source: D:/Learning/tradingview/MostosImportentIndicator_8/Liqudity/liqudity_trap_trading.v3.8.5.txt (not edited).
All line numbers verified against the file. Indent = spaces; continuation lines use 5 spaces (file style, not a multiple of 4).

## Verdict table

| ID | Verdict | Lines | Tokens |
|---|---|---|---|
| #8 f_htfStruct break latch body-blind | CONFIRMED | 2190-2200 | +6 |
| B5 HTF FVG no min height | CONFIRMED | 2352, 2384, 2396 | +16 |
| N-6 picker freshness jumps off the POI price is in | CONFIRMED | 2455, 2464 | +16 |
| N-1 cont setup reaches A+ from stale raw grade | CONFIRMED (header line 19 claims "never A+") | 4520 (+3627 only if N-2 not taken) | +8 |
| N-2 liq override feeds f_tier (engine piggy-back) / double count | CONFIRMED (tier part); score part = design | 3546-3547, 3577-3578 | -2 |
| N-4 cont arms on 2nd visit / latch remembers only last POI | CONFIRMED | 4125-4126 | +10 |
| N-5 no HTF premium/discount for cont (+ NEW-2 arm below hsProtLo) | CONFIRMED | 2230, 2232, 4125-4126 | +30 |
| N-7 opposing displacement kills cont at stage 2 | CONFIRMED | 4177, 4350 | +10 |
| A-4 dead external break latch | CONFIRMED dead | 2047-2048, 2054, 2059, 2061-2064 | -45 |
| F-2 day boundary time("D") | REFUTED as bug (consistent with ADR "D" bars); NY midnight open = feature, defer | 2481, 5509 | 0 (opt. +30) |
| NEW-1 fastShift path uses stale sslInPlay on a cont setup | PARTIAL (low impact) | 4234, 4390 | +4 (optional) |
| NEW-2 cont arms on a POI below/at a broken HTF protected low → killed next bar, latch wasted | CONFIRMED | 4125/4199 | folded into N-5 |
| NEW-3 header says 7 request.security, real count 8 | CONFIRMED (doc only) | 526 | 0 |
| NEW-4 governor resets on session day, dowOK on NY calendar day | PARTIAL (minor mismatch) | 4486, 4493 | 0 (note) |

Recommended package: #8, B5, N-6, N-1(mcTier), N-2(B), N-4, N-5, N-7, A-4 → **≈ +49 tokens** (+53 with NEW-1).
request.security count unchanged (8 real). One tuple grows 3→5 (single destructuring site 2232). No new `if`, plot, alertcondition, input.

---

## #8 — f_htfStruct break latch is body-blind — CONFIRMED

Evidence: 2191-2196 latch `_resBrk/_supBrk` on ANY HTF close beyond the pivot; the BOS/CHoCH branch (2200) needs
`_body >= dispMult*_atr`. A weak close above `_res` eats the latch → the following displaced close is not a BOS →
`_protLo` not raised, `_legLo` not reset. Chart-TF twin was fixed by FIX-A2 (2065-2068: `extResBosDone` latches only with
`dispClose`); the HTF engine never got it. Refutation attempts: (a) `structDisp` = 0 makes it moot — default is 0.5 so no;
(b) a later pivot resets the latch — yes, but piv=5 HTF bars → hours of wrong `hsDir/hsProtLo` on H1. Consumers:
`htfB` (2238-2240), `contArmL/S` (4125), `htfProtInval` (4199/4361).

BEFORE
```
2190:     float _body = math.abs(close - open)
2191:     bool  _upBrk = not na(_res) and not _resBrk and close > _res
2192:     bool  _dnBrk = not na(_sup) and not _supBrk and close < _sup
...
2200:     if _body >= dispMult * _atr
```
AFTER
```
    float _body = math.abs(close - open)
    bool  _dispH = _body >= dispMult * _atr
    bool  _upBrk = not na(_res) and not _resBrk and close > _res and _dispH
    bool  _dnBrk = not na(_sup) and not _supBrk and close < _sup and _dispH
...
    if _dispH
```
(lines 2193-2196 unchanged.) Inside the `if _dispH` branch `_upBrk/_dnBrk` were already implicitly displaced, so BOS
semantics are identical except the latch now survives a weak break. +6 tok. Side effect: HTF BOS fires on the first
DISPLACED close beyond the pivot (later, higher protLo) → hsDir flips sooner on reversals; htfProtInval kills sooner.

## B5 — HTF FVG has no minimum height — CONFIRMED

2384 `if low > high[2]`, 2396 `if high < low[2]`: a 1-tick H1 gap is a POI; since S-1 it ARMS the machine. Chart-TF
has FIX-Z6 (2684-2685 `>= minZoneAtr * atr`). `minZoneAtr` (869) is input-derived (const/input form) → legal inside
the security expression; `atrLen` (763) input.

BEFORE
```
2352:     // 1 · lifecycle of the live slots: visit counting, then invalidation / age / spent
...
2384:     if low > high[2]
...
2396:     if high < low[2]
```
AFTER
```
    float _hAtr = ta.atr(atrLen)      // B5: HTF ATR, unconditional (top level of the function)
    // 1 · lifecycle of the live slots: visit counting, then invalidation / age / spent
...
    if low - high[2] >= minZoneAtr * _hAtr      // B5 = FIX-Z6 on the HTF
...
    if low[2] - high >= minZoneAtr * _hAtr
```
+16 tok. Optional displacement of the middle candle (`and math.abs(close[1] - open[1]) >= structDisp * _hAtr`, +10 each)
— not recommended without journal data. Side effect: fewer HTF POIs → fewer cont arms, NEXT/POI score less often HTF.

## N-6 — f_pickPoi freshness override leaves the POI price is inside — CONFIRMED

Visits are counted on CLOSED HTF candles and exported `[1]`. H1 candle k dips into slot 1 → from candle k+1 `i1 = 1`
while M5 price is still inside slot 1. Slot 2 (older, untested, `b2 <= close`, within `POI_NEAR_ATR*2*atr` ≈ 3.5 ATR)
wins `fresher2` → `hPoiBTop/Bot` jump below price → `contTapL` (4119) and `tapHtf` (4244) false mid-tap, NEXT BUY moves,
POI score lost, and `contArmLvlL` latch can later re-arm on the old POI (see N-4). Refutation: "fresher is better" only
holds before price reaches the current pick.

BEFORE
```
2455:         bool fresher2 = nz(i2) == 0 and pI != 0 and near2
...
2464:         bool fresher3 = nz(i3) == 0 and pI != 0 and near3
```
AFTER
```
        bool fresher2 = nz(i2) == 0 and pI != 0 and near2 and (demand ? close > pT : close < pB)
...
        bool fresher3 = nz(i3) == 0 and pI != 0 and near3 and (demand ? close > pT : close < pB)
```
`pI != 0` implies `pT/pB` set (non-na). +16 tok. Side effect: none when price is outside the current pick.

## N-1 — continuation can be A+ — CONFIRMED

`lastSslQualRaw/lastSslKind` (1663/1667) are latches, only rewritten on a new sweep (1699…1928), never decayed.
`f_mcTier` (4518-4531): `qualOk` and `poolOk` read them with no link to THIS setup; `htfOk` always true for a cont arm
(contArmL requires `htfB > 0`); `shiftOk` from `sbShiftGL` which the cont path also sets (4237/4256). → t = 4.
Header line 19 promises "continuation is never A+". At the fire bar `suLCont` is still true (reset only at 4152 on
the next bar with suL == 0), and `f_mcTier` is evaluated after the machine (4532), so the gate below works.

BEFORE
```
4520:     bool qualOk  = (isLong ? lastSslQualRaw : lastBslQualRaw) >= 3
```
AFTER
```
    bool qualOk  = not (isLong ? suLCont : suSCont) and (isLong ? lastSslQualRaw : lastBslQualRaw) >= 3      // N-1: cont is never A+
```
+8 tok. `f_tier` (3627): ONLY if N-2(B) is NOT applied, add `and (isLong ? sslInPlay : bslInPlay)` to the A+ test
(+6). With N-2(B) the raw `liq >= 10` already implies `sslInPlay` (3541: without a live sweep liq ≤ 5), so not needed.

## N-2 — S-1 liquidity override — CONFIRMED (tier leak); chosen fix = move it to the score only

Facts: machine tier = `max(tierLong, mcTierL)` (4756), `mcTierL` floors at 3 → the machine never needed `liq` for A.
The override (3546) leaks into `f_tier` (3610) → every non-machine long engine firing while a cont setup lives
(suL ≥ 1, previous-bar state) gets tier A/A+ with no raid. The score part is the real reason S-1 added it: a cont
entry without it scores ≈ 41-58 vs `minScore` 50 (ctx 20-30, liq 0-5, poi 15-20, trig 6-12, exec 0-10) — removing it
would silently gate cont entries. Double count POI-as-liq + POI-in-zone is real only at stage 2 (NEXT = HTF POI, nbKind
"HTF"); at the entry bar the anchor is normally the shift-leg FVG, so the score double count is minor.
Decision: keep +10 in the GATE score, take it out of the tier grader.

BEFORE
```
3543: // ◆ v3.8.5 S-1: a continuation setup stands on the HTF POI — internal-range
3544: // liquidity — which carries the same weight as a sweep in play. Without this
3545: // no engine / machine entry could reach tier A without a raid (`f_tier`).
3546: liqLong  := suLCont and suL >= 1 ? math.max(liqLong, 10) : liqLong
3547: liqShort := suSCont and suS >= 1 ? math.max(liqShort, 10) : liqShort
...
3577: scoreBaseL = ctxLong  + liqLong  + poiLong  + trigLong  + execLong
3578: scoreBaseS = ctxShort + liqShort + poiShort + trigShort + execShort
```
AFTER (delete 3543-3547; replace 3577-3578)
```
scoreBaseL = ctxLong  + (suLCont and suL >= 1 ? math.max(liqLong, 10) : liqLong) + poiLong  + trigLong  + execLong      // S-1 / N-2: score only, never the tier
scoreBaseS = ctxShort + (suSCont and suS >= 1 ? math.max(liqShort, 10) : liqShort) + poiShort + trigShort + execShort
```
≈ -2 tok. Side effects: engines inside a cont narrative without a raid drop to tier B (correct); dbg row 5572 shows raw
liq (component sum ≠ score for a cont setup — cosmetic). Stricter optional variant: `math.max(liqLong, recentEngLo ? 10 : 5)`
(+4/side) — pays 10 only when inducement was taken; risks pushing plain cont entries under minScore 50.

## N-4 — cont arm on a 2nd POI visit — CONFIRMED

`contArmL` (4125) never reads `hPoiBIn`. The latch `contArmLvlL` remembers only the LAST POI armed: POI A arms → POI B
arms → price returns to A (visit 2, still alive because `hPoiMaxTouch` = 2) → `contArmLvlL != A.bot` → re-arms on a
spent POI. Also arms on visit 2 whenever visit 1 was blocked (bias, chop, suL busy). Gate on first visit: `hPoiBIn`
is `[1]`-shifted, so it reads 0 for the whole HTF candle in which the first touch happens (arm window = rest of that
HTF candle; M5/H1 ≤ 12 bars, M1/M15 ≤ 15 bars). Patch combined with N-5 below.

## N-5 (+ NEW-2) — HTF premium/discount for the continuation arm — CONFIRMED

`_legHi/_legLo` already exist in f_htfStruct (2179-2180, reset to the event bar at 2228-2229), so in dir 1 the HTF
dealing range is `[hsProtLo, _legHi]`; in dir -1 `[_legLo, hsProtHi]`. Exporting them costs two tuple slots, no new
security call (only destructuring site: 2232). NEW-2: nothing stops an arm on a tap that already closes below
`hsProtLo` — the next bar kills it "HTF protected low broken" (4199) and the once-per-POI latch is burned; folded in.
v6 comparisons with na return false, so `not (a > na)` passes when the range is unknown (no new blocking on warm-up).
Note: structure is on `biasTf` (60 default), POI on `htfTf` (M1→15, M5→60) — prices only, mixing TFs is fine.

BEFORE
```
2230:     [_dir[1], _protLo[1], _protHi[1]]
2232: [hsDirRaw, hsProtLo, hsProtHi] = request.security(syminfo.tickerid, biasTf, f_htfStruct(htfStructPiv, structDisp),
...
4125: contArmL = contOn and htfB > 0 and hsDir > 0 and contTapL and not bslInPlay and nz(contArmLvlL) != hPoiBBot
4126: contArmS = contOn and htfB < 0 and hsDir < 0 and contTapS and not sslInPlay and nz(contArmLvlS) != hPoiSTop
```
AFTER
```
    [_dir[1], _protLo[1], _protHi[1], _legLo[1], _legHi[1]]
...
[hsDirRaw, hsProtLo, hsProtHi, hsLegLo, hsLegHi] = request.security(syminfo.tickerid, biasTf, f_htfStruct(htfStructPiv, structDisp),
...
// N-4 first visit only · N-5 POI in HTF discount / premium · NEW-2 not through the HTF protected swing
contArmL = contOn and htfB > 0 and hsDir > 0 and contTapL and not bslInPlay and nz(contArmLvlL) != hPoiBBot
     and nz(hPoiBIn) == 0 and not (close < hsProtLo or hPoiBTop > (hsProtLo + hsLegHi) / 2)
contArmS = contOn and htfB < 0 and hsDir < 0 and contTapS and not sslInPlay and nz(contArmLvlS) != hPoiSTop
     and nz(hPoiSIn) == 0 and not (close > hsProtHi or hPoiSBot < (hsProtHi + hsLegLo) / 2)
```
`[1]` + lookahead_on preserved. N-4 ≈ +10, N-5/NEW-2 ≈ +30. Side effects: fewer cont arms (premium POIs in strong
shallow trends skipped — classic late-entry loss avoided; journal NAS which often continues from premium FVGs);
dashboard "HTF dmd tap" (5486) still shows the tap even when not armed — consider later. `hsLegLo/hsLegHi` can also feed
a dashboard "HTF EQ" read (not included).

## N-7 — opposing displacement kills a continuation at stage 2 — CONFIRMED

4177: any bearish body ≥ `dispFactor*atr` at `suL <= 3` kills, except stage 3 with an anchor. A cont setup goes 0→2 on
the tap bar (4241-4249), and the delivery INTO an H1 FVG (several M5 ATR tall) is routinely a 1.2-ATR bearish M5 body
that still closes inside the POI — the exact bar before an MSS-up. Premise protection remains: close below
`hPoiBBot - NEAR_LVL_ATR*atr` kills via 4156/4166, plus poiWait expiry. Sweep setups unchanged.

BEFORE
```
4177:         else if bearBar and body >= dispFactor * atr and suL <= 3
...
4350:         else if bullBar and body >= dispFactor * atr and suS <= 3
```
AFTER
```
        else if bearBar and body >= dispFactor * atr and suL <= 3 and not (suLCont and suL == 2)      // N-7
...
        else if bullBar and body >= dispFactor * atr and suS <= 3 and not (suSCont and suS == 2)
```
(4178/4351 continuation lines unchanged.) +10 tok.

## A-4 — dead external break latch — CONFIRMED dead

grep: `extResBrk/extSupBrk/eBrokeUp/eBrokeDn` appear only at 2047-2048, 2054, 2059, 2061-2064. `f_structure` is fed
`eBrokeUpS/eBrokeDnS` (2069, FIX-A2 twins). Delete:
```
2047: var bool  extResBrk = false
2048: var bool  extSupBrk = false
2054:     extResBrk := false
2059:     extSupBrk := false
2061: eBrokeUp = not na(extRes) and not extResBrk and close > extRes
2062: eBrokeDn = not na(extSup) and not extSupBrk and close < extSup
2063: extResBrk := eBrokeUp and confirmed ? true : extResBrk     // SCOPE
2064: extSupBrk := eBrokeDn and confirmed ? true : extSupBrk
```
-45 tok, 2 fewer `var`. No behaviour change.

## F-2 — day boundary / NY midnight open — REFUTED as a bug; feature deferred

`newDay` (2481) = `ta.change(time("D"))` = the symbol's daily-session start (XAU/FX 17:00 NY, CME 18:00 NY, crypto
00:00 UTC). `adrVal` (2480) comes from the SAME "D" bars, so `dayRng / adrVal` is apples-to-apples; switching `newDay`
to NY midnight would make ADR% inconsistent. 5509 `dayFrac` "(early)" = first 6 h of the session day — consistent too.
NEW-4 (minor): `dowOK` (4493) uses the NY calendar day while the governor (4486) resets at the session day → trades
17:00-24:00 NY count toward the next session's limit while being day-filtered as the previous NY date. Note only.
NY midnight open as a level: feasible without a security call, ≈ +30 tok:
```
nyDom = dayofmonth(time, "America/New_York")
var float nyMidOpen = na
nyMidOpen := timeframe.isintraday and nyDom != nyDom[1] ? open : nyMidOpen
```
plus a use (e.g. cont long only `not (close > nyMidOpen)`). Recommend defer — overlaps N-5's HTF P/D gate.

## NEW-1 — fastShift path with stale sslInPlay on a cont setup — PARTIAL (low)

4234 `if suL == 1 and sslInPlay and (... fastShift and shiftUpOk)`: on the cont arm bar an unrelated live SSL sweep
sends the setup 1→3 directly. The normal path reaches 3 on the same bar anyway (4241 tap → 2, 4253 shift → 3), so the
only loss is the stage-2 zone anchor (`tapZone ? nbTop`), i.e. stage 3 then waits for a shift-leg FVG instead of using the
zone. Optional:
```
4234:     if suL == 1 and sslInPlay and not suLCont and (sbTagL != 0 ? (sbReqMss ? mssUp : sbShiftUp) : (fastShift and shiftUpOk))   // FIX-V14 · NEW-1
4390:     if suS == 1 and bslInPlay and not suSCont and (sbTagS != 0 ? (sbReqMss ? mssDn : sbShiftDn) : (fastShift and shiftDnOk))   // FIX-V9b · FIX-V14 · NEW-1
```
+4 tok.

## S-1 machine — other checks (no defect)

- `suLSweepExt` deepening (4186) for cont: a wick below the POI bottom lowers the stop; close-kill still at
  `hPoiBBot - NEAR_LVL_ATR*atr` via 4166 → correct (wick raid of the POI).
- "range swept both ways" (4183) never applies to cont (stage 1 lasts 0 bars) — harmless.
- `contArmLvlL` set only when actually armed (after lockOk + chop) — correct; its single-slot weakness is N-4.
- Stop (4332) for cont uses `suLSweepExt` = POI bottom − tol → wide; FIX-X4 falls back to the anchor stop under
  `maxRiskAtr` — as designed.
- Short machine mirrors the long one line-for-line (4338-4400) — no asymmetry found.
- NEW-3: header 526 says 7 security calls; real = 8 (1766, 1767, f_bias ×2 [2163-2164], 2232, 2318, 2433, 2480). Doc fix.

## Token total
#8 +6 · B5 +16 · N-6 +16 · N-1 +8 · N-2 −2 · N-4 +10 · N-5 +30 · N-7 +10 · A-4 −45 = **+49** (NEW-1 → +53).
