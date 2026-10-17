# patch_G3: Engine stops and the trap engine (v3.8.5 → v3.8.6 candidate)

Source: `D:/Learning/tradingview/MostosImportentIndicator_8/Liqudity/liqudity_trap_trading.v3.8.5.txt` (CRLF). The source was not edited.

## Facts verified first

- `f_ltMachines()` is called once (4018) and `f_zoneUpdate()` is called once (3000). Each `var` therefore has a single call site, so adding new `var`s is safe.
- LT stops are used only when the LT engine is the surviving engine. Its rank is last in `selSLLong/Short` (4669-4674). `planEntry = close` for non-MC engines.
- Risk cap (4693): `maxRiskAtr` defaults to 1.5 and `riskMode` defaults to "Reject the signal". A wider, honest stop therefore REJECTS the signal rather than clamping it.
- Arm, retest and confirm order inside the machine, per bar:
  1. expiry / invalidation
  2. cooldown release
  3. arm
  4. retest
  5. confirm

  The long machine runs fully before the short machine.
- Short arm bar = the poke bar for LT-2/LT-5/LT-6 (weak poke / wick on `brokeUp`) and for LT-3 (`brokeUp`).
- With `ltReqRetest` (default true), confirmation needs `bar_index > _ltSRetBar > _ltSBar`. So confirmation is on arm+2 or later, and the arm bar's high is never the confirmation bar's high.
- `dirLock` (3453) = open trade direction, else `suL>=2 ? 1 : suS>=2 ? -1`. `longOK` / `engOKL` carry the lock, so lock-owner engines are live, and only the veto (4640) then mutes them.
- `SL_PAD_ATR` is 0.25 to 0.40 depending on profile. `dispFactor` is 1.1 to 1.2. `ltExpSens` is 1.2, `ltInvAtr` is 1.0, `ltWaitBars` is 25 and `ltCd` is 10.

---

## Verdict table

| ID | Verdict | Severity |
|---|---|---|
| C2 long stop (3962) | CONFIRMED | P1 |
| C2 short stop (4005) | CONFIRMED, worse than reported: the arm-bar poke high is excluded | P0/P1 |
| LT-7 stop ignores supply top | CONFIRMED | P1 |
| B1 zone 50% stop ignores tap wick (2964/2994) | CONFIRMED (conditional) | P2 |
| C3 short confirm lacks acceptance (4000) | CONFIRMED | P2 |
| C4 invalidation needs displacement (3928/3971) | CONFIRMED | P2 |
| C5 arm ignores lock; veto mutes lock owner (3936/3976, 4640) | CONFIRMED. The veto gate is the real fix; the arm gate is secondary | P2 |
| LT-3 / LT-7 arm on displaced breaks (3841/3844) | CONFIRMED for LT-3; PARTIAL for LT-7 | P2 |
| LT long confirm 1 ATR below level (3957) | CONFIRMED (design looseness) | P3 |
| C13 ambiguity penalty (3882) | CONFIRMED (counts state 2 and is order-dependent) | P3 |
| NEW-1 LT-7 invalidation anchored at the break level, not the supply top | NEW, CONFIRMED | P2. Becomes P1 if C4 is applied alone |
| NEW-2 `ltReqRetest=false` lets LT-1 confirm on its own expansion bar | NEW, LOW | P3. No patch |
| NEW-3 Risk cap "Clamp" mode re-inserts the stop inside the trap wick | NEW, note only | — |

---

## C2: LT stop inside the raid wick (CONFIRMED)

### Evidence

**Long.** `_ltSlL := math.min(low, _ltLLevel) - SL_PAD_ATR*atr` reads only the confirmation bar.
- FIX-V6a requires the confirmation bar to come after the retest bar.
- The retest condition is `low <= level + 0.5 ATR`, and the wick can go far below the level, up to "anything without a 1.2-ATR bear body closing 1 ATR below".
- So the retest raid wick is structurally never inside the stop. The stop sits at level − pad, and the raid low is often 0.3 to 0.9 ATR below that.

**Short.** `_ltSlS := math.max(high, _ltSLevel) + pad`. `_ltSLevel` is the BREAK level (`ltBrkUpLvl` / `lastRes`), not the poke high.
- LT-2/5/6 are defined by a poke or wick ABOVE the level on the arm bar, and the confirmation bar is at arm+2 or later.
- The trap high, the one level a trap short must be protected by, is therefore excluded on every default-settings short. The stop sits at level + 0.3 ATR, inside the very wick the pattern is named after.

**Refutation attempts.**
- Is the extreme tracked elsewhere? No. `f_ltPools` keeps only `_ltBrkUpLvl` (= `lastRes`), and `_p4HiMax` is LT-4-internal and not returned.
- Is the poke bar the confirmation bar? Only when `ltReqRetest=false`.

Both attempts failed.

### Patch C2 (+ LT-7 supply top, + NEW-1, + C3). Apply as one unit

**A. Var declarations.** BEFORE (3906-3907):
```
    var float  _ltLDoneLvl = na
    var float  _ltSDoneLvl = na
```
AFTER:
```
    var float  _ltLDoneLvl = na
    var float  _ltSDoneLvl = na
    // v3.8.6 C2: trap extremes since arm (long: after the arm bar · short: incl. the poke bar) + LT-7 supply top
    var float  _ltLExt  = na
    var float  _ltSExt  = na
    var float  _ltSZTop = na
```

**B. Long invalidation (C4).** BEFORE (3928-3930):
```
            else if close < _ltLLevel - ltInvAtr * atr and bearBar and body >= dispFactor * atr
                _ltLState  := 0
                _ltLReason := "breakout failed (bear displacement below level)"
```
AFTER:
```
            else if close < _ltLLevel - ltInvAtr * atr
                _ltLState  := 0
                _ltLReason := "breakout failed (close below level)"
```

**C. Long arm (C5 + reset).** BEFORE (3936-3944):
```
        if _ltLArmTxt != "" and not na(_ltLLvlNow) and (na(_ltLDoneLvl) or math.abs(_ltLLvlNow - _ltLDoneLvl) > ltClusterTol * atr)   // FIX-V6b / FIX-W8
            if _ltLState == 0
                _ltLState  := 1
                _ltLBar    := bar_index
                _ltLLevel  := _ltLLvlNow
                _ltLPats   := _ltLArmTxt
                _ltLRetOk  := false
                _ltLRetBar := na
                _ltArmLEvt := true
```
AFTER:
```
        if _ltLArmTxt != "" and lockOkL and not na(_ltLLvlNow) and (na(_ltLDoneLvl) or math.abs(_ltLLvlNow - _ltLDoneLvl) > ltClusterTol * atr)   // FIX-V6b / FIX-W8 / v3.8.6 C5
            if _ltLState == 0
                _ltLState  := 1
                _ltLBar    := bar_index
                _ltLLevel  := _ltLLvlNow
                _ltLPats   := _ltLArmTxt
                _ltLRetOk  := false
                _ltLRetBar := na
                _ltLExt    := na
                _ltArmLEvt := true
```

**D. Long extreme tracking.** Insert between 3951 (`_ltRetLEvt := true`) and 3952 (the `// FIX-V6a:` comment). The new line has 8-space indent, at the level of the `if ltEnable and confirmed` body:
```
        _ltLExt := _ltLState == 1 and bar_index > _ltLBar ? math.min(nz(_ltLExt, low), low) : _ltLExt    // v3.8.6 C2
```

**E. Long confirm (3957: acceptance) and stop (3962).** BEFORE (3957):
```
        if _ltLState == 1 and ltBullConfNow and ltGatesL and ltCtxOKLong and lockOkL and (not ltReqRetest or (_ltLRetOk and bar_index > _ltLRetBar)) and close > _ltLLevel - ltInvAtr * atr
```
AFTER:
```
        if _ltLState == 1 and ltBullConfNow and ltGatesL and ltCtxOKLong and lockOkL and (not ltReqRetest or (_ltLRetOk and bar_index > _ltLRetBar)) and close > _ltLLevel
```
BEFORE (3962):
```
                _ltSlL       := math.min(low, _ltLLevel) - SL_PAD_ATR * atr
```
AFTER:
```
                _ltSlL       := math.min(low, _ltLLevel, nz(_ltLExt, low)) - SL_PAD_ATR * atr      // v3.8.6 C2: below the retest raid
```

**F. Short invalidation (C4 + NEW-1).** BEFORE (3971-3973):
```
            else if close > _ltSLevel + ltInvAtr * atr and bullBar and body >= dispFactor * atr
                _ltSState  := 0
                _ltSReason := "breakout accepted (bull displacement above level)"
```
AFTER:
```
            else if close > (na(_ltSZTop) ? _ltSLevel + ltInvAtr * atr : _ltSZTop)
                _ltSState  := 0
                _ltSReason := "breakout accepted (close above level / supply)"
```

**G. Short arm (C5 + reset + LT-7 top).** BEFORE (3976-3984):
```
        if _ltSArmTxt != "" and not na(_ltBrkLvlNow) and (na(_ltSDoneLvl) or math.abs(_ltBrkLvlNow - _ltSDoneLvl) > ltClusterTol * atr)   // FIX-V6b / FIX-W8
            if _ltSState == 0
                _ltSState  := 1
                _ltSBar    := bar_index
                _ltSLevel  := _ltBrkLvlNow
                _ltSPats   := _ltSArmTxt
                _ltSRetOk  := p7Arm      // LT-7's supply tap IS its retest
                _ltSRetBar := p7Arm ? bar_index : na
                _ltArmSEvt := true
```
AFTER:
```
        if _ltSArmTxt != "" and lockOkS and not na(_ltBrkLvlNow) and (na(_ltSDoneLvl) or math.abs(_ltBrkLvlNow - _ltSDoneLvl) > ltClusterTol * atr)   // FIX-V6b / FIX-W8 / v3.8.6 C5
            if _ltSState == 0
                _ltSState  := 1
                _ltSBar    := bar_index
                _ltSLevel  := _ltBrkLvlNow
                _ltSPats   := _ltSArmTxt
                _ltSRetOk  := p7Arm      // LT-7's supply tap IS its retest
                _ltSRetBar := p7Arm ? bar_index : na
                _ltSExt    := high
                _ltSZTop   := p7Arm ? nsTop : na
                _ltArmSEvt := true
```
Append branch. BEFORE (3992):
```
                _ltSRetBar := p7Arm and na(_ltSRetBar) ? bar_index : _ltSRetBar
```
AFTER:
```
                _ltSRetBar := p7Arm and na(_ltSRetBar) ? bar_index : _ltSRetBar
                _ltSZTop   := p7Arm and na(_ltSZTop) ? nsTop : _ltSZTop
```

**H. Short extreme tracking.** Insert between 3996 (`_ltRetSEvt := true`) and 3997 (`bool ltBearConfNow`), with 8-space indent:
```
        _ltSExt := _ltSState == 1 ? math.max(nz(_ltSExt, high), high) : _ltSExt    // v3.8.6 C2: incl. the poke bar
```

**I. Short confirm (C3) and stop.** BEFORE (4000):
```
        if _ltSState == 1 and ltBearConfNow and ltGatesS and ltCtxOKShort and lockOkS and (not ltReqRetest or (_ltSRetOk and bar_index > _ltSRetBar)) and (not ltSNeedBelow or close < _ltSLevel)
```
AFTER:
```
        if _ltSState == 1 and ltBearConfNow and ltGatesS and ltCtxOKShort and lockOkS and (not ltReqRetest or (_ltSRetOk and bar_index > _ltSRetBar)) and (not na(_ltSZTop) and not ltSNeedBelow or close < _ltSLevel)
```
Precedence: `(A and B) or C`, because unary `not` binds tightest. BEFORE (4005):
```
                _ltSlS        := math.max(high, _ltSLevel) + SL_PAD_ATR * atr
```
AFTER:
```
                _ltSlS        := math.max(high, _ltSLevel, nz(_ltSExt, high), nz(_ltSZTop, high)) + SL_PAD_ATR * atr      // v3.8.6 C2 / LT-7
```

### Compile notes
- No new `if`. Every new line is a plain assignment or ternary inside an existing block.
- `math.max` / `math.min` are variadic in v6.
- `nsTop` is a global series. It is read only, and inside the function that is allowed.
- No `ta.*` calls are added.
- Continuation lines are unchanged.

### Tokens (rough compiled)

| Part | Tokens |
|---|---|
| Vars | +9 |
| Resets (3) | +10 |
| Two tracking lines | +28 |
| Stop edits | +10 |
| `_ltSZTop` append line | +8 |
| C3 acceptance | +5 |
| C4 deletions (2 × `and bearBar and body >= dispFactor * atr`) | −14 |
| NEW-1 ternary | +6 |
| C5 arm gates | +2 |
| 3957 (`- ltInvAtr * atr` removed) | −4 |
| **Net for C2 / LT-7 / C3 / C4 / NEW-1 / C5-arm / 3957** | **≈ +60** |

### Side effects

- **Short stop distance.** It grows by the poke above level: typically 0.3 to 1.0 ATR on XAU M1/M5, and 0.3 to 0.8 ATR on NAS M5.
  - Short entries now close below the level (C3), so risk = (pokeHigh − close) + pad. That often lands at 1.0 to 1.8 ATR.
  - Expect roughly 20 to 40 % of LT shorts to hit the 1.5-ATR cap and be REJECTED under the default "Reject". Before, those trades were stopped by the wick-retest noise anyway.
- **Long stop.** It grows by the retest raid, typically 0.2 to 0.6 ATR. A few more rejects.
- **LT-7 stop.** It now sits above the supply top. A zone taller than about 1.2 ATR → reject. That is correct: the zone is too fat for a scalp stop.
- **Signal count.** It goes down: rejects from the cap, the C3 acceptance filter and earlier invalidation.
- **Win-rate per signal.** It should go up, because stops are no longer inside the trap wick.

### Operator view
- A trap short is protected by the trap high, full stop.
- On XAU M1, London and NY spikes re-tag the poke high about 60 % of the time before the fade. A stop at level + 0.3 ATR is a donation.
- For a breakout-retest long, the stop goes under the retest raid low, not the breakout level.
- LT-7 is a supply fade, so its invalidation is the zone's distal edge.

All four changes match how the trade is actually managed.

---

## B1: Zone 50% tap stop ignores tap wick (CONFIRMED, conditional)

### Evidence
- The signal can fire up to `confirmWin` (5) bars after the 50% tap (2962).
- The stop is `math.max(high, top)` of the confirmation bar only (2964), and the mirror `math.min(low, bot)` (2994).
- The zone is deleted or flipped only on a CLOSE beyond the distal edge (2936/2968). So the tap bar, or any bar between tap and confirmation, can wick above `top` (or below `bot`) and the zone survives. The stop is then at top + 0.3 ATR, inside that wick.
- Refutation: when the confirmation bar IS the tap bar, `high` already covers it, so there is no bug in that case. The issue exists only when tap < confirmation bar. That is the common case: the zone confirmation (`zoneBearConf`) is usually 1 to 3 bars after the first tap.

### Patch B1
Add a UDT field at the end of the type, so the positional `Zone.new` (2891) stays valid and unspecified fields default to `na`.

BEFORE (2846):
```
    bool   wasIn     // price overlapped the zone on the previous bar
```
AFTER:
```
    bool   wasIn     // price overlapped the zone on the previous bar
    float  tapExt    // v3.8.6 B1: extreme since the 50% tap
```

Supply side. Insert after 2961 (`z.tap50Bar := _tap ? bar_index : z.tap50Bar`), with 16-space indent:
```
                z.tapExt   := _tap ? high : math.max(nz(z.tapExt, high), high)
```
BEFORE (2964):
```
                    sigSLShort := math.max(high, top) + SL_PAD_ATR * atr
```
AFTER:
```
                    sigSLShort := math.max(high, top, nz(z.tapExt, high)) + SL_PAD_ATR * atr
```

Demand side. Insert after 2991, with 16-space indent:
```
                z.tapExt   := _tap ? low : math.min(nz(z.tapExt, low), low)
```
BEFORE (2994):
```
                    sigSLLong := math.min(low, bot) - SL_PAD_ATR * atr
```
AFTER:
```
                    sigSLLong := math.min(low, bot, nz(z.tapExt, low)) - SL_PAD_ATR * atr
```

### Notes
- **No reset needed.** The signal requires `tapped50`, which requires a `_tap` bar, and the tap bar re-seeds `tapExt`.
- **Accumulation is bounded.** The confirmation must come within `confirmWin` bars of `tap50Bar`, so stale accumulation is never read.
- **Realtime ticks.** Intrabar highs are ≤ the final high, so `max` never over-states. The behaviour matches the existing `tapped50` writes.
- **`f_flipZone`.** It needs no change: it clears `tapped50`.
- **Tokens:** about +34.
- **Side effect:** wider SD stops only when a wick pierced the distal edge, typically +0.2 to 0.5 ATR. There are some extra cap rejects on tall zones.
- **Operator view.** The swept-edge zone tap is the best SD entry on XAU, and its stop must sit above the sweep. Correct.

---

## C3: Short confirm lacks acceptance (CONFIRMED)

- 4000 requires `close < _ltSLevel` only for LT-6. The long side has an acceptance guard (3957); the short side has none.
- `ltReqRetest` only proves that ONE earlier close was below the level. Price can reclaim and sit 0.9 ATR above the level when an internal CHoCH-down prints, and the trap would short a breakout that is holding.
- **Patch:** folded into C2-I.
  - Every short except LT-7 (with no LT-6) must close below the level.
  - LT-7 is bounded by its supply-top invalidation instead (NEW-1).
- **Tokens:** +5.
- **Operator view:** a failed breakout is only failed while price is back below the level. Correct.

## C4: Invalidation requires a displacement body (CONFIRMED)

- 3928/3971 invalidate only on a 1.1 to 1.2-ATR body bar.
- A grind of small closes 1 to 2 ATR beyond the level never invalidates. The machine waits 25 bars, and the veto keeps muting the opposite engines for those 25 bars. Typical case: a NAS M5 trend day after a "weak poke" short arm.
- **Patch:** C2-B and C2-F, deleting the displacement terms. **Tokens:** −14 (+6 for the NEW-1 ternary).

> **WARNING: apply C4 together with NEW-1.**
> LT-7's level is the break level BELOW the supply (`nsBot >= ltBrkUpLvl`). A tap into a supply that starts more than 1 ATR above the break would be invalidated on the very next close if C4 were applied alone.

## NEW-1: LT-7 invalidation anchored at the break level (NEW, CONFIRMED)

- Even today, a 1.2-ATR bull bar that closes inside the supply (above level + 1 ATR, below `nsTop`) kills LT-7 while the supply is intact.
- **Patch:** C2-F. When `_ltSZTop` exists, the invalidation is `close > _ltSZTop`, which means the zone failed.

## C5: Arm ignores the direction lock, and the veto mutes the lock owner (CONFIRMED)

- Arm (3936/3976) has no lock test. Confirm (3957/4000) does.
- With `dirLock = 1` (`suL >= 2`, a long setup at the POI or later), a short pattern arms to state 1 even though it can never confirm.
- The veto at 4640 then sets `anyLong := false` for every non-MC long engine (SD 50 %, CRT, TL, LT-1 and so on). Those engines are the lock OWNER's own confirmations, muted for up to 25 bars.
- The arm gate alone is not enough: a trap armed before the lock was set still vetoes after it.

**Patch, veto (primary).** BEFORE (4640-4641):
```
anyLong  := ltEnable and ltVeto and ltSState == 1 and not sigMCLong  ? false : anyLong
anyShort := ltEnable and ltVeto and ltLState == 1 and not sigMCShort ? false : anyShort
```
AFTER:
```
anyLong  := ltEnable and ltVeto and ltSState == 1 and lockOkS and not sigMCLong  ? false : anyLong
anyShort := ltEnable and ltVeto and ltLState == 1 and lockOkL and not sigMCShort ? false : anyShort
```

**Patch, arm (secondary).** In C2-C and C2-G, `and lockOkL` / `and lockOkS` stop a stale arm (made while the lock was held) from confirming later at an old level.

**Tokens:** +4 for the veto, +2 for the arm.

**Operator view:** a trap that is not allowed to trade must not get a vote. Correct.

## LT-3 / LT-7 arm on displaced breakouts (CONFIRMED for LT-3 / PARTIAL for LT-7)

- **LT-3 (3841):** `brokeUp` plus an SSL pool within `SWEEP_CTX_ATR` (3 to 5 ATR!). There is no weakness test.
  - A 1.5-ATR marubozu arms LT-1 long and LT-3 short on the same bar.
  - Result: the C13 −15 penalty hits both machines, and the veto mutes all long engines.
  - The script's own input defines a genuine break as `ltExpSens` ("Expansion body ≥ ATR × (genuine break)").
- **LT-7 (3844):** this is a supply fade, so a displaced bar INTO an intact supply is still a valid premise. The confirmation needs CHoCH-down. Only the same-bar LT-1 conflict is wrong.

**Patch.** BEFORE (3841):
```
p3Arm = ltEnable and ltP3 and confirmed and brokeUp and not na(p3PoolLow) and close - p3PoolLow <= SWEEP_CTX_ATR * atr
```
AFTER:
```
p3Arm = ltEnable and ltP3 and confirmed and brokeUp and body < ltExpSens * atr and not na(p3PoolLow) and close - p3PoolLow <= SWEEP_CTX_ATR * atr
```
BEFORE (3844), append at the end of the line:
```
... and not na(ltBrkUpLvl) and nsBot >= ltBrkUpLvl
```
AFTER:
```
... and not na(ltBrkUpLvl) and nsBot >= ltBrkUpLvl and not p1Arm
```
`p1Arm` is defined on 3839, before 3844, so the reference is valid.

**Tokens:** about +9. **Side effect:** fewer LT-3 arms and fewer false vetoes on trend days.

## 3957: LT long confirm allows a close 1 ATR below the level (CONFIRMED)

- LT-1 and LT-4 are breakout-hold longs. A confirmation close below the breakout level is the geometry of the opposite LT-2/5/6 trap.
- **Patch:** C2-E (`close > _ltLLevel`). **Tokens:** −4.
- **Operator view:** a reclaim-and-hold is required. On XAU M1 a 1 ATR tolerance is about $1 to $2 of "failed breakout" being bought.

## C13: Ambiguity penalty (CONFIRMED, minor)

- 3882 `lState >= 1 and sState >= 1` also counts state 2 (the opposite trap already FIRED and is cooling down).
- It is also order-dependent. The short machine is scored after the long machine updated this bar: a long that fires on this bar sets state 2, and that penalises a short confirming on the same bar.

**Patch.** BEFORE (3882):
```
    s -= lState >= 1 and sState >= 1 ? 15 : 0                                           // ambiguous — both directions armed
```
AFTER:
```
    s -= lState == 1 and sState == 1 ? 15 : 0                                           // ambiguous — both directions armed (v3.8.6 C13: WAITING only)
```

**Tokens:** 0. **Side effect:** scores rise by 15 only in the cooldown overlap. Small change in the signal count.

## NEW-2 (LOW, no patch)
With `ltReqRetest=false`, LT-1 can confirm on its own expansion arm bar when `mssUp` prints on the breakout, so the "trap" long is just the breakout bar. Defaults are unaffected. Optionally add `bar_index > _ltLBar` (+4 tokens).

## NEW-3 (note)
`riskMode = "Clamp the stop"` (4694) pulls `planSL` back to 1.5 ATR, which can put it back inside the trap wick that C2 / B1 just protected. Document in the manual: for trap and SD engines, use "Reject".

---

## Token total

| Group | Tokens |
|---|---|
| C2 / LT-7 / NEW-1 / C3 / C4 / C5-arm / 3957 bundle | ≈ +60 |
| B1 | ≈ +34 |
| C5 veto | +4 |
| LT-3 / LT-7 arm | +9 |
| C13 | 0 |
| **Total** | **≈ +107** |

No new `if`, plot, alertcondition or `ta.*` is added.
