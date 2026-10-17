# Patch G1: tracker and alert honesty (v3.8.5 → v3.8.6)

Source: `D:/Learning/tradingview/MostosImportentIndicator_8/Liqudity/liqudity_trap_trading.v3.8.5.txt`. The file was not edited. Line numbers are from v3.8.5.
Token figures are Pine compiled-token estimates, ±30 %.
Rules followed: no new `if` scope (except where E4 *removes* about 35 of them), no new plot, plotchar, bgcolor or alertcondition, and continuation lines indented by 5 or 9 spaces.

---

## Verdict table

| # | Item | Verdict | Reachable with defaults? | Δ tokens |
|---|---|---|---|---|
| 3 | `cntSL` counts BE / lock / trail / scratch exits | **CONFIRMED** (worse than reported: the Partial time-stop scratch also counts as SL **and** as `lossToday`) | yes, very common | +40 (≈+12 inside E4) |
| E1/D4 | tie keeps `sigMC*` true | **CONFIRMED, but only with `oneDir = false`** | no (`oneDir` defaults to true, L1048) | +8 minimal, +40 with rollback |
| E8 | limit-fill bar stop not checked | **PARTIAL**: only reachable with `riskMode = "Clamp the stop"` | no (default "Reject", L1100) | +25 (+20 journal) |
| D2 | CE fill + close through distal edge not counted | **PARTIAL→CONFIRMED** (a real fill, unmeasured; but *not* a stop-out) | yes | +35 |
| D5 | `ceLimitFill` / `mcFillNext` direction-blind | **PARTIAL**: the `mcFillNext` half is moot, the `ceLimitFill` half is real, and both need `oneDir = false` | no | ≈ −2 |
| E3 | size ignores `pointvalue` (and cost) | **CONFIRMED** | yes (futures) | +12 |
| F-1 | no exit journal / R / MAE / MFE | **CONFIRMED** | yes | +130 |
| E4 | exit block ×4 | **CONFIRMED**: about 100 code lines and about 41 local scopes | n/a | **−320** (about 6 scopes left) |
| NEW-1 | `mcPlanLong/Short` not cleared on a gate-kill, so a same-bar engine signal is planned at the dead machine's CE | **NEW, CONFIRMED** | yes | +6 |
| NEW-2 | Partial time-stop scratch (stop = entry, TP1 unhit) is booked as SL + daily loss | **NEW** (fixed by the `trdProt` rule in #3) | yes, with `sbTimeMode = Partial` | 0 (inside #3) |

Net with every patch except E4: about **+256**. **With E4: about −80** (E4 −320, which also absorbs #3's four call sites).

---

## #3 cntSL counts protected exits, plus cntBE: CONFIRMED

Evidence: 4873, 4899, 4922 and 4961 all do `cntSL += 1` unconditionally, and alert 5606 fires on `cntSL > cntSL[1]`. No other path separates the outcomes; `lossToday` alone was fixed by FIX-Z10.

**The finding is worse than reported.** FIX-Z10's `trdTp1Hit` test misses the SB Partial time exit (4958 / 4990), which moves the stop to *entry* while `trdTp1Hit` is false. A later stop at entry is a scratch at 0R, but it counts as cntSL+1 and lossToday+1, so the governor closes the day on scratches.

**Better classifier:** test whether the stop is at or through entry, not whether TP1 was hit. That covers BE, the +1R lock, the trail and the Partial scratch.

### Patch 3a: declare (after L4786)
BEFORE (4786):
```
var int cntSL     = 0
```
AFTER:
```
var int cntSL     = 0
var int cntBE     = 0      // v3.8.6 #3: stop at / through entry (BE · 1R lock · trail · time scratch)
```

### Patch 3b: classifier + entry-direction snapshot (after L4861; F-1 and E4 reuse it)
BEFORE (4860-4861):
```
    cntUntracked := pendFilled ? cntUntracked : cntUntracked + 1      // FIX-W7
    pendDir := 0        // a gap through the stop, or the tracker busy: order cancelled
```
AFTER:
```
    cntUntracked := pendFilled ? cntUntracked : cntUntracked + 1      // FIX-W7
    pendDir := 0        // a gap through the stop, or the tracker busy: order cancelled
// v3.8.6 #3 / F-1: direction live during this bar's exits, and "is the stop protected"
int  trdDirIn = trdDir
bool trdProt  = trdDir == 1 ? trdSL >= trdEntry : trdDir == -1 and trdSL <= trdEntry
```
(Columns 0. `trdProt` is evaluated before the exit block, and that is correct: each path's stop test runs before that bar's BE / trail edits.)

### Patch 3c: the four stop branches (skip this if E4 is applied)
BEFORE (4873-4874, and identically 4899-4900, 4922-4923, 4961-4962, each at 16-space indent):
```
                cntSL += 1
                lossToday += trdTp1Hit ? 0 : 1      // FIX-Z10: a break-even stop is not a loss
```
AFTER (×4):
```
                cntSL += trdProt ? 0 : 1
                cntBE += trdProt ? 1 : 0
                lossToday += trdProt ? 0 : 1      // FIX-Z10 · v3.8.6: a protected stop is not a loss
```

### Patch 3d: alert 5606 (same alertcondition, no new output)
BEFORE:
```
alertcondition(cntSL  > cntSL[1],  "[TRADE] SL hit",  "Stop touched on {{ticker}} {{interval}}")
```
AFTER:
```
alertcondition(cntSL > cntSL[1] or cntBE > cntBE[1], "[TRADE] Stop exit (SL / BE / trail)", "Stop exit on {{ticker}} {{interval}} — R in the LQEXIT journal line")
```
Side effect: the alert's title and text change, so users must re-create this one alert. Alternative: keep `cntSL > cntSL[1]` as a loss-only alert and let LQEXIT report protected exits (−8 tokens).

### Patch 3e: debug row 3 (5576)
BEFORE:
```
             "\nTP " + str.tostring(cntTP1) + "/" + str.tostring(cntTP2) + "/" + str.tostring(cntTP3) + " SL " + str.tostring(cntSL) + " exp " + str.tostring(cntExp) + " untrk " + str.tostring(cntUntracked), rowBg)
```
AFTER (includes D2 `cntVoid` and F-1 `sumR`. Drop those two pieces if the matching patches are not applied):
```
             "\nTP " + str.tostring(cntTP1) + "/" + str.tostring(cntTP2) + "/" + str.tostring(cntTP3) + " SL " + str.tostring(cntSL) + " BE " + str.tostring(cntBE) + " void " + str.tostring(cntVoid) + " exp " + str.tostring(cntExp) + " untrk " + str.tostring(cntUntracked) + " ΣR " + str.tostring(sumR, "#.##"), rowBg)
```
Numbers that change:
- SL drops by every protected exit.
- BE becomes visible.
- `lossToday` drops by the time-stop scratches, so the governor and the `|d` journal field change.
- The "day closed" verdict at 5538 changes with it.
- The SL alert stops reporting profitable trail exits as "Stop touched".

Tokens: about +40 standalone (3a 6, 3b 14, 3c 4×5, 3d ≈0, 3e +10 for BE).

---

## E1/D4: an equal-rank tie keeps `sigMC*` true. CONFIRMED (needs `oneDir = false`)

Evidence: the tie branch 4627-4629 clears `anyLong/anyShort` only. Then:
- the LT veto at 4640 never touches a machine bar;
- `not planOK` (4720) is never reached, because `(anyLong or anyShort)` is false;
- so `sigMCLong` survives.

Symptoms:
- 5594 "[SIGNAL] ◉ Setup machine entry" fires for a muted bar.
- 4821 cancels a pending engine order, then counts it untracked at 4860.
- 5006 holds `suL` at 4. If `trdDir != 0` the stage stays ACTIVE with no trade until the tracker frees, and the stale reason is shown.
- `mcFillNext` / `engFillNext` turn true. This is harmless, because they are only read inside the signal block.

**Partial refutation:** symptoms appear only when *both* sides are machine entries of equal rank. An engine-vs-engine tie has `sigMC*` false already. With `oneDir = true` (default, L1048), `dirLock` (3453) turns `lockOkS` false whenever `suL ≥ 2` (and the reverse), so `shortOK` kills the second machine at 4537-4538, and two machine entries cannot coexist on one bar. So the bug is real but default-unreachable.

BEFORE (4627-4629):
```
    else
        anyLong  := false
        anyShort := false
```
AFTER (full version, +40):
```
    else
        // v3.8.6 E1: an equal-rank tie mutes the machine too and rolls back a same-bar ACTIVE
        suLReason  := suL == 4 and suLBar == bar_index ? "conflict — equal-rank tie, both muted" : suLReason
        suSReason  := suS == 4 and suSBar == bar_index ? "conflict — equal-rank tie, both muted" : suSReason
        suL        := suL == 4 and suLBar == bar_index ? 0 : suL
        suS        := suS == 4 and suSBar == bar_index ? 0 : suS
        anyLong    := false
        anyShort   := false
        sigMCLong  := false
        sigMCShort := false
```
Minimal (+8): only the two `sigMC* := false` lines. 5006 then releases `suL` on the same bar when the tracker is flat. A busy tracker still leaves it at 4, so the full version is recommended.

---

## E8: limit-fill-bar stop is not checked. PARTIAL (only with "Clamp the stop")

Evidence: immediate fills (5089-5101) happen after the exit block (4863), so the fill bar is never tested. **But** every non-deferred fill is a machine or SB entry, and its stop is built below the bar's own extreme:
- `slAnchL = math.min(low, suLAnchorB) - SL_PAD_ATR*atr` and `slRaidL = math.min(math.min(low, …), …) - pad` (4331-4332) are strictly below `low`.
- For the short side, `slMCShort ≥ high + pad`, then `planSL = slS + spr > hiA` (4681).
- The fallback stops (4677-4678) are also beyond the bar.
- Engine signals are always deferred (`engFillNext`), and a deferred fill runs *before* the exit block, so it is covered.

The only way a stop lands inside the fill bar is the risk-cap clamp at 4695 (`riskMode == "Clamp the stop"`), and the default is "Reject the signal" (L1100). So the bug is real only for clamp users. A long CE limit whose bar wicks through the clamped stop and recovers stays open.

BEFORE (5101-5102):
```
        trdShiftG := sbFireL ? sbShiftGL : sbFireS ? sbShiftGS : 0
    cntUntracked := trackNew ? cntUntracked : cntUntracked + 1   // FIX-T2 · SCOPE
```
AFTER:
```
        trdShiftG := sbFireL ? sbShiftGL : sbFireS ? sbShiftGS : 0
    // v3.8.6 E8: a clamped stop can sit inside the fill bar — pessimistic, as at 4868
    bool fillHit = trackNew and not deferFill and (trdDir == 1 ? low <= trdSL : hiA >= trdSL)
    cntSL     += fillHit ? 1 : 0
    lossToday += fillHit ? 1 : 0
    sumR      -= fillHit ? 1.0 : 0.0
    exitMsg   := fillHit ? "LQEXIT|" + syminfo.ticker + "|" + timeframe.period + "|" + (trdDir == 1 ? "L" : "S") + "|FILLSL|R-1|b0" : exitMsg
    trdOutEvt := trdOutEvt or fillHit
    trdDir    := fillHit ? 0 : trdDir
    cntUntracked := trackNew ? cntUntracked : cntUntracked + 1   // FIX-T2 · SCOPE
```
- The `sumR`, `exitMsg` and `trdOutEvt` lines need F-1 (declared at 4999, which is earlier in the source, so this is OK). Without F-1, keep only the cntSL, lossToday and trdDir lines (+25).
- The exit is exactly −1R, because TP1 = E ± |E−SL| on both fill paths (4848, 5034).
- `suL` stays 4 for this bar, and 5006 releases it on the next bar (`sigMCLong` false then).
- Interaction: if an older trade also exited on this bar, its LQEXIT text is overwritten. This needs exit, re-entry and a clamped fill-bar stop on one bar, which is accepted.
- No double count with D2: a D2 bar never sets `sigMC`, so there is no fill.

Optional, same scope: the fill bar's TP touches are not booked either. That is conservative, so leave it.

---

## D2: CE fill + close below distal is not counted. CONFIRMED as an *unmeasured fill*, not as an SL

Evidence: 4317 `if close < suLAnchorB` runs before the entry branch, and 4320 requires `close > suLAnchorB`. A bar whose ask traded `ceL` (`sbCeTapL` 4297 / `mcCeTapL` 4306) and then closed below the distal edge kills the setup. A resting CE limit (the order LQCE pre-fill at 5645 tells the trader to place) **did fill**.

**Refutation of the review's wording:** the trade is not stopped on that bar. The stop would have been `min(low, anchorB) - pad`, which is below `low`. It is an open, underwater position whose thesis has just been invalidated. A disciplined trader exits it at the close for a loss. So the honest booking is "void fill = loss at close", counted separately, not a fake SL.

This is survivorship bias in the CE stats: every CE fill that instantly fails is dropped, and only the survivors are measured.

### Patch D2a: bar flags (after L4063)
BEFORE (4062-4063):
```
bool mcCeFillL  = false
bool mcCeFillS  = false
```
AFTER:
```
bool mcCeFillL  = false
bool mcCeFillS  = false
bool ceVoidL    = false     // v3.8.6 D2: the CE limit traded, then the bar closed through the distal edge
bool ceVoidS    = false
```

### Patch D2b: long violation branch (4317-4319)
BEFORE:
```
            if close < suLAnchorB
                suL := 0
                suLReason := sbTagL != 0 ? "SB FVG violated" : "anchor FVG violated"
```
AFTER:
```
            if close < suLAnchorB
                ceVoidL := (sbEnterL and sbCeTapL) or (stdEnterL and mcCeTapL)
                suL := 0
                suLReason := sbTagL != 0 ? "SB FVG violated" : "anchor FVG violated"
```

### Patch D2c: short (4439-4441)
BEFORE:
```
            if close > suSAnchorT
                suS := 0
                suSReason := sbTagS != 0 ? "SB FVG violated" : "anchor FVG violated"
```
AFTER:
```
            if close > suSAnchorT
                ceVoidS := (sbEnterS and sbCeTapS) or (stdEnterS and mcCeTapS)
                suS := 0
                suSReason := sbTagS != 0 ? "SB FVG violated" : "anchor FVG violated"
```

### Patch D2d: counter (after L4793) and booking (before L5022)
BEFORE (4793):
```
var int cntUntracked = 0
```
AFTER:
```
var int cntUntracked = 0
var int cntVoid      = 0    // v3.8.6 D2: CE fills killed on their own bar (booked as losses)
```
BEFORE (5022):
```
trackNew = (anyLong or anyShort) and confirmed and trdDir == 0
```
AFTER:
```
// v3.8.6 D2: the limit filled and the anchor died on the same bar — a real losing fill
bool ceVoid = confirmed and trdDir == 0 and ((ceVoidL and longOK) or (ceVoidS and shortOK))
cntVoid   := ceVoid ? cntVoid + 1 : cntVoid
lossToday := ceVoid ? lossToday + 1 : lossToday
trackNew = (anyLong or anyShort) and confirmed and trdDir == 0
```
- `longOK` (4503) is the gate the entry would have faced. The tier floor is not re-tested, which is a slight over-count. That is acceptable, because an LQCE auto-trader gets the fill regardless of gates (E13).
- `trdDir == 0` means a busy tracker would not have tracked it either.
- Effect: `lossToday` and the governor include instant CE failures, and debug shows `void n`.
- Interactions: disjoint from E8 and #3. If F-1 should journal it, add `exitMsg := ceVoid ? "LQEXIT|…|VOID|R?" : exitMsg` (+20). The R is not available, because the machine stop is not computed in the violation branch. Not recommended.

---

## D5: CE flags are direction-blind. PARTIAL

The loser's `mcCeFill*` / `sbCeFill*` is never cleared in the rank branches (4613-4626).
- **`mcFillNext` (4747) is moot.** A loser with a CE flag must be a machine of rank 2. The winner then has rank 3 = SB, so `sbSigLong` is true and `mcFillNext` is already false.
- **`ceLimitFill` (4687) is real.** Example: an SB **edge** long (rank 3, `sbCeFillL` false) beats an MC CE short (rank 2, `mcCeFillS` true). The stale `mcCeFillS` skips the slip guard for an edge fill priced off the close.
- Like E1, this needs `oneDir = false`.

BEFORE (4687):
```
    bool ceLimitFill = sbCeFillL or sbCeFillS or mcCeFillL or mcCeFillS
```
AFTER:
```
    bool ceLimitFill = anyLong ? sbCeFillL or mcCeFillL : sbCeFillS or mcCeFillS      // v3.8.6 D5: the winner's own fill
```
BEFORE (4747):
```
mcFillNext  = (sigMCLong or sigMCShort) and not (sbSigLong or sbSigShort) and not (mcCeFillL or mcCeFillS)   // FIX-W6 · FIX-X3
```
AFTER:
```
mcFillNext  = sigMCLong ? not sbSigLong and not mcCeFillL : sigMCShort and not sbSigShort and not mcCeFillS   // FIX-W6 · FIX-X3 · v3.8.6 D5
```
The ternaries are safe because after the conflict block (and with E1) at most one `sigMC*` / `any*` side survives. Δ ≈ −2.

---

## E3: position size. CONFIRMED

5252 gives `riskMoney / |E−SL|`. That is ES ×50 too many, CL ×1000, and `costTicks` is ignored. FX and crypto have `pointvalue` 1, so they are unchanged. `rrCost` is already in scope (5247).

BEFORE (5252):
```
             (riskMoney > 0 ? " · ≈" + str.tostring(math.round(riskMoney / math.max(math.abs(entryP - slP), syminfo.mintick))) + " units" : ""),
```
AFTER:
```
             (riskMoney > 0 ? " · ≈" + str.tostring(math.round(riskMoney / (math.max(math.abs(entryP - slP) + rrCost, syminfo.mintick) * syminfo.pointvalue), 2)) + (syminfo.type == "futures" ? " contracts" : " units") : ""),
```
- Two decimals, so 0.4 contracts no longer prints "≈0".
- An account currency that differs from `syminfo.currency` is still not converted. The input tooltip should say "in the symbol's currency".
- +12 tokens. Label text only.

---

## F-1: exit journal LQEXIT with R / bars / MAE / MFE. CONFIRMED

Evidence: the only `alert()` journal (5649-5663) fires on signal / CE bars, and no outcome line exists.

**Design constraint found while verifying:** a new trade can open on the *same bar* the old one exits (`trackNew` at 5022 tests `trdDir == 0` after the exits). By 5649, `trdEntry`, `trdBar` and `trdIsSb` belong to the new trade, and `trdDir == 0 and trdDir[1] != 0` (the rev_D proposal) is false. So the exit must be detected and **its message built right after 4998**, using `trdDirIn` (Patch 3b).

### F-1a: declare MFE/MAE before the deferred fill (after L4797)
BEFORE (4797):
```
var float pendSL  = na
```
AFTER:
```
var float pendSL  = na
var float trdMfe  = 0.0     // v3.8.6 F-1: max favourable / adverse excursion of the tracked trade (price)
var float trdMae  = 0.0
```

### F-1b: reset on both fill paths
In the deferred fill, BEFORE (4858-4859):
```
            trdLiqTgt := na
            pendFilled := true
```
AFTER:
```
            trdLiqTgt := na
            trdMfe    := 0.0
            trdMae    := 0.0
            pendFilled := true
```
In the immediate fill, BEFORE (5100-5101):
```
        trdSbWin  := sbFireL ? sbTagL : sbFireS ? sbTagS : 0
        trdShiftG := sbFireL ? sbShiftGL : sbFireS ? sbShiftGS : 0
```
AFTER:
```
        trdSbWin  := sbFireL ? sbTagL : sbFireS ? sbTagS : 0
        trdShiftG := sbFireL ? sbShiftGL : sbFireS ? sbShiftGS : 0
        trdMfe    := 0.0
        trdMae    := 0.0
```
(The immediate-fill bar's own excursion is not counted, because the intrabar order is unknown. The deferred-fill bar is counted, because its entry is the open.)

### F-1c: exit event, R and message (after L4998)
BEFORE (4997-4998):
```
cntExp := trdExp ? cntExp + 1 : cntExp
trdDir := trdExp ? 0 : trdDir
```
AFTER:
```
cntExp := trdExp ? cntExp + 1 : cntExp
trdDir := trdExp ? 0 : trdDir
// ◆ v3.8.6 F-1 EXIT JOURNAL — the outcome of every tracked trade, in R.
// Built HERE: a new trade may open later on this same bar and overwrite trd*.
trdMfe := trdDirIn != 0 ? math.max(trdMfe, trdDirIn == 1 ? high - trdEntry : trdEntry - loA) : trdMfe
trdMae := trdDirIn != 0 ? math.max(trdMae, trdDirIn == 1 ? trdEntry - low : hiA - trdEntry) : trdMae
bool   trdOutEvt = confirmed and trdDirIn != 0 and trdDir == 0
float  trdR0     = math.abs(trdTP1 - trdEntry)          // TP1 is exactly 1R on both fill paths
string trdExTag  = cntSL > cntSL[1] ? "SL" : cntBE > cntBE[1] ? "BE" : cntTP3 > cntTP3[1] ? "TP3" : sbStructExitEvt ? "STR" : trdExp ? "EXP" : sbTimeExitEvt ? "TIME" : "TP2"
float  trdExPx   = trdExTag == "SL" or trdExTag == "BE" ? (trdDirIn == 1 ? math.min(trdSL, open) : math.max(trdSL, open + spr)) :
     trdExTag == "TP3" ? trdTP3 : trdExTag == "TP2" ? trdTP2 : close + (trdDirIn == 1 ? 0 : spr)
float  trdROut   = trdOutEvt and trdR0 > 0 ? (trdExPx - trdEntry) * trdDirIn / trdR0 : 0.0
var float sumR   = 0.0
sumR := sumR + trdROut
string exitMsg = trdOutEvt ? "LQEXIT|" + syminfo.ticker + "|" + timeframe.period + "|" + (trdDirIn == 1 ? "L" : "S") + "|" + (trdIsSb ? "SB" : "NS") + "|" + trdExTag +
     "|R" + str.tostring(trdROut, "#.##") + "|b" + str.tostring(bar_index - trdBar) +
     "|mfe" + str.tostring(trdMfe / trdR0, "#.##") + "|mae" + str.tostring(trdMae / trdR0, "#.##") +
     "|E" + str.tostring(trdEntry, format.mintick) + "|X" + str.tostring(trdExPx, format.mintick) + "|ΣR" + str.tostring(sumR, "#.##") : ""
```
Notes and checks:
- Exit price is pessimistic and honest:
  - A gap through the stop fills at the open (`min(trdSL, open)` long, `max(trdSL, open+spr)` short).
  - A short buy-back at the close pays the ask.
  - Targets fill at the level: long at the bid (`high`), short at the ask (`loA`).
  - A deferred fill on this bar implies `open > pendSL`, so the `min()` returns `trdSL`.
- Tag order follows the code's order: stop first, TP2+TP3 on the same bar gives "TP3", and an expiry runs after the exits. A "TP2" tag means a non-SB close at TP2.
- The `cntSL[1]` / `cntBE[1]` / `cntTP3[1]` history on `var int` is safe. E8's later `cntSL` increment cannot leak in, because it comes after this line in the same bar, and `[1]` is the previous bar.
- Without #3, drop the `cntBE` term. "SL" then also covers protected exits, and R still tells the truth.
- MFE/MAE are in R. On the exit bar they include the whole bar (it may exceed the target), which is accepted.
- No `ta.*`, no na concatenation (`trdROut` is never na), and int×float promotes to float.

### F-1d: emit via the existing journal `if` (5649-5650 and 5662)
BEFORE (5649-5650):
```
if jrnlEnable and confirmed and (anyLong or anyShort or ceEvtL or ceEvtS)      // v3.8.3 D19: same scope
    alert(not (anyLong or anyShort) ? ceMsg : "LQJRNL|" + syminfo.ticker + "|" + timeframe.period + "|" + (anyLong ? "L" : "S") +
```
AFTER:
```
if jrnlEnable and confirmed and (anyLong or anyShort or ceEvtL or ceEvtS or trdOutEvt)      // v3.8.3 D19 · v3.8.6 F-1: same scope
    alert((trdOutEvt ? exitMsg + "\n" : "") + (not (anyLong or anyShort) ? (ceEvtL or ceEvtS ? ceMsg : "") : "LQJRNL|" + syminfo.ticker + "|" + timeframe.period + "|" + (anyLong ? "L" : "S") +
```
BEFORE (5662):
```
         "|d" + str.tostring(trdToday) + "/" + str.tostring(lossToday),
```
AFTER (closes the new paren):
```
         "|d" + str.tostring(trdToday) + "/" + str.tostring(lossToday)),
```
- On an exit-plus-entry bar you get one alert with two lines, LQEXIT first. Parsers should split on `\n` and ignore empty lines.
- `ceMsg` is now guarded. Before, it was only reached when `ceEvt*` was true; now `trdOutEvt` alone also enters the scope.
- The deferred-entry LQJRNL `E` field is still the plan price. LQEXIT's `|E` is the real fill, which partly resolves N2.

Tokens: about +90 for the exit line and ΣR, plus about +40 for MFE/MAE. **Cut order if CE10117 hits:** drop the mfe/mae lines (F-1a, F-1b, the two `trdMfe/trdMae :=` lines and the two message fields), saving about −40.

Follow-ups that cost almost nothing once F-1 exists (other groups):
- N3: `lossToday := trdOutEvt and trdROut < 0 and trdExTag != "SL" ? lossToday + 1 : lossToday` (+15). This books losing STR / TIME / EXP exits.
- N17: the partial-profit R model.

---

## E4: exit block ×4, signed-direction core. CONFIRMED (token payment)

Inventory, 4863-4990:
- 128 lines, about 100 of them code.
- **About 41 local scopes** (if/else at every leaf).
- Four near-identical copies: non-SB L/S and SB L/S.
- The only differences are `low` vs `hiA` (adverse side), `high` vs `loA` (favourable side), `max` vs `min` for stop tightening, and the SB-only trail, structure and time exits.

Equivalences verified:
- Stop: long `low <= SL`, short `hiA >= SL`. Both equal `(trdSL - adv) * d >= 0`, with `adv = d == 1 ? low : hiA`.
- Target: long `high >= T`, short `loA <= T`. Both equal `(fav - T) * d >= 0`.
- Tighten: long `math.max(sl, x)`, short `math.min(sl, x)`. This becomes `f_tight(sl, x, d)`.
- BE: 4883 and 4934 are identical (the same `math.max(sbBeBuf*atr, SB_BE_TP1_PCT*|TP1-E|)`). The target is `trdEntry + d*buf`.
- Non-SB TP2: lock `max(SL, E+|TP1-E|)` = `f_tight(SL, trdTP1, d)`, because TP1 = E ± R. Otherwise close.
- SB TP2: no close, then trail.
- TP3: SB is unconditional (4947 has no TP2 requirement). Non-SB needs `nonSbTp3 and trdTp2Hit`, and a non-SB trade still alive with `trdTp2Hit` implies `nonSbTp3`. So the condition is `trdIsSb or trdTp2Hit`.
- Structure and time are SB-only, in the same order (TP3 → STR → TIME). The `trdDir` re-test at each step is kept.

### Replacement (whole of 4863-4990)
Put the helper before the block, for example after 4778:
```
f_tight(float sl, float lvl, int d) => d == 1 ? math.max(sl, lvl) : math.min(sl, lvl)    // v3.8.6 E4: stops only tighten
```
Block:
```
if confirmed and trdDir != 0
    // ◆ v3.8.6 E4 ONE SIGNED EXIT CORE (was four mirrored copies). d = +1 long / −1 short.
    // Long stop / targets on the bid (low / high), short on the ask (hiA / loA) — FIX-Y2.
    // Stop first, pessimistic (FIX-P1-8d); TP1 and TP2 can both book on one bar.
    int   d   = trdDir
    float adv = d == 1 ? low  : hiA
    float fav = d == 1 ? high : loA
    if (trdSL - adv) * d >= 0
        cntSL     += trdProt ? 0 : 1           // v3.8.6 #3: a protected stop is BE / trail, not SL
        cntBE     += trdProt ? 1 : 0
        lossToday += trdProt ? 0 : 1           // FIX-Z10
        trdDir := 0
    else
        if not trdTp1Hit and (fav - trdTP1) * d >= 0
            trdTp1Hit := true
            cntTP1 += 1
            trdSL   := f_tight(trdSL, trdEntry + d * math.max(sbBeBuf * atr, SB_BE_TP1_PCT * math.abs(trdTP1 - trdEntry)), d)   // SB-14
            sbBeEvt := true
        if trdTp1Hit and not trdTp2Hit and (fav - trdTP2) * d >= 0
            trdTp2Hit := true
            cntTP2 += 1
            trdSL  := not trdIsSb and nonSbTp3 ? f_tight(trdSL, trdTP1, d) : trdSL    // FIX-T2: lock 1R
            trdDir := trdIsSb or nonSbTp3 ? d : 0
        // SB-14 trail behind the protected swing, never through the last two bars / price
        float prot = d == 1 ? protLowE : protHighE
        float cap  = d == 1 ? math.min(math.min(low, low[1]), close) - SL_PAD_ATR * atr : math.max(math.max(high, high[1]), close) + SL_PAD_ATR * atr
        trdSL := trdIsSb and trdTp2Hit and sbTrail and not na(prot) ? f_tight(trdSL, d == 1 ? math.min(prot - SL_PAD_ATR * atr, cap) : math.max(prot + SL_PAD_ATR * atr, cap), d) : trdSL
        if trdDir != 0 and (trdIsSb or trdTp2Hit) and (fav - trdTP3) * d >= 0
            cntTP3 += 1
            trdDir := 0
        // SB structure / time exits (SB-6)
        bool sbWEnd = trdSbWin == 1 ? sbEndLOEvt : trdSbWin == 2 ? sbEndAMEvt : trdSbWin == 3 ? sbEndPMEvt : false
        sbStructExitEvt := trdIsSb and trdDir != 0 and sbStructEx and (d == 1 ? mssDn or (trdShiftG <= 1 and (cisdDn or chochDn or eChochDn)) : mssUp or (trdShiftG <= 1 and (cisdUp or chochUp or eChochUp)))
        trdDir := sbStructExitEvt ? 0 : trdDir
        sbTimeExitEvt := trdIsSb and trdDir != 0 and sbTimeExit and sbWEnd and not trdTp1Hit
        trdDir := sbTimeExitEvt and sbTimeMode == "Full" ? 0 : trdDir
        trdSL  := sbTimeExitEvt and sbTimeMode != "Full" ? f_tight(trdSL, trdEntry, d) : trdSL
```
Compile checks:
- `low[1]` / `high[1]` are built-in history refs, legal in any scope.
- No `ta.*`.
- `d` is an int and `(float) * int` gives a float.
- `sbStructExitEvt` / `sbTimeExitEvt` are plain bools declared at 4772-4773, and assigning them in a local scope is fine.
- `f_tight` is declared at the top level, before use.
- The non-SB trail is skipped by `trdIsSb`, and `trdStructEx` / time are SB-only. This is the same as the original.
- The SB trail ran unconditionally after TP2 even if TP3 later closed the trade. Order kept.

Behaviour differences vs v3.8.5:
1. #3: SL / BE split and the Partial-time scratch.
2. None otherwise.

Token count:
- Original ≈ 100 code lines × 9 ≈ 900 tokens, 41 scopes.
- New ≈ 33 lines × 17 ≈ 560 tokens + helper ≈ 20, 6 scopes.
- **Saving ≈ −320 tokens and −35 scopes.** That saving funds every other patch in this group.

---

## NEW-1: stale machine plan price used by an engine signal. CONFIRMED

- 4328 / 4448 write `mcPlanLong/Short` when the machine fires.
- When the final gate kills `sigMCLong` (4537), 4539-4546 clear `sbSigLong`, `sbCeFillL` and `mcCeFillL`, **but not `mcPlanLong`**.
- 4671 `planEntry = anyLong ? nz(mcPlanLong, close)` then prices a same-bar ENGINE long (CRT, TBS, LT…) at the dead machine's CE or edge. The slip guard, risk cap, TP2 clamp and the minRR gate (4688-4716) are all measured from that price, along with the drawn plan lines, RR, size label and the journal `E`.
- The tracked fill is deferred to the next open, so `trdEntry` is right, but the *accept/reject decision* was made on the wrong price.
- Reachable with defaults: for example, the machine tier is below the floor while an engine passes its own tier on the same bar.

BEFORE (4539-4546):
```
if not sigMCLong
    sbSigLong := false
    sbCeFillL := false      // FIX-Z12
    mcCeFillL := false      // FIX-X3: no machine signal, no machine limit fill
if not sigMCShort
    sbSigShort := false
    sbCeFillS := false
    mcCeFillS := false
```
AFTER:
```
if not sigMCLong
    sbSigLong := false
    sbCeFillL := false      // FIX-Z12
    mcCeFillL := false      // FIX-X3: no machine signal, no machine limit fill
    mcPlanLong := na        // v3.8.6 NEW-1: an engine on this bar is planned at its own close
if not sigMCShort
    sbSigShort := false
    sbCeFillS := false
    mcCeFillS := false
    mcPlanShort := na
```
+6 tokens. The rank-conflict and tie paths do not need this, because the losing side's `any*` is false.

## NEW-2: Partial time exit scratch booked as a loss (see #3)
4958 / 4990 set `trdSL := trdEntry` with `trdTp1Hit` false. A later stop at entry counts as `cntSL+1` and `lossToday+1`, so two scratches can close the day under `maxLossDay = 2`. This is fixed by `trdProt` (Patch 3b/3c or E4).

---

## Recommended v3.8.6 application order
1. E4 core (−320), including #3 via `trdProt` (3a, 3b, 3d, 3e).
2. F-1 (a–d).
3. NEW-1.
4. D2.
5. E3.
6. D5.
7. E1 full.
8. E8 (only matters for clamp users, so it can be deferred).

Net ≈ −80 tokens and ≈ −35 scopes.

Test checklist:
- A non-SB trade that goes TP1 → BE stop should show `TP1+1, BE+1, SL+0` and an LQEXIT with R about +0.1 (the BE buffer).
- An SB trail exit should give `BE` with R > 2.
- A gap stop should give an R below −1.
- An exit and a new entry on one bar should produce two lines in one alert.
- ES with riskMoney 500 and an 8-pt stop should print ≈1.25 contracts.
- A CE limit that touched and closed below the FVG should give void+1 and lossToday+1.
