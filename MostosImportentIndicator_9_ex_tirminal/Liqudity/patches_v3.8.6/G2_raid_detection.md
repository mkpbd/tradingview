# G2 — Liquidity raid detection (MODULE 1-5): adversarial verification and exact patches

**Target file:** `D:/Learning/tradingview/MostosImportentIndicator_8/Liqudity/liqudity_trap_trading.v3.8.5.txt` (5701 lines, CRLF)

- Source was NOT edited. Line numbers below are v3.8.5.
- Token figures are Pine compiler-token estimates (identifier, operator and literal ≈ 1 each).
- The user HAS set `spreadIn`, so `spr = spreadIn * syminfo.mintick > 0`.

## Verdict table

| ID | Verdict | Patch | Tokens |
|---|---|---|---|
| #1 multi-bar raid: PD/PW | **CONFIRMED** | G2-1a/1c | +8 |
| #1 multi-bar raid: EQ pool | **CONFIRMED** | G2-1b | +16 |
| #1 multi-bar raid: session H/L | **CONFIRMED** | G2-1d | ~+62 |
| shared windows (rcN/hiN/loN/cAbv/cBlw) | — | G2-1 core | ~+32 |
| A-1 same-bar stamp `low`/`high` | **PARTIAL (latent today, real after #1)** | folded into G2-1 (`hiN`/`loN` at 8 sites) | 0 |
| #6 ATR cap shrinks SL pad | **CONFIRMED** | G2-6 (`slPad`, 32 sites) | **−59** |
| #7 rollover spread-spike sweeps | **CONFIRMED** (mechanism; frequency is broker-dependent) | G2-4 | ~+60 |
| F-5 Asia raid in London/NY KZ cannot arm | **CONFIRMED** | G2-3 | +4 |
| F-6 spread-blind grade thresholds | **CONFIRMED** | G2-5 (`nearSp`) | −6 |
| A-10 ATR floor | **PARTIAL** (no floor exists, but a history floor rarely binds; the real low-vol failure is relative to spread → G2-5) | G2-7 optional | +8 |
| NEW-1 session re-raid latch = 1 ATR | NEW, P3 | G2-8 | +4 |
| NEW-2 session multi-bar label says "broken" | NEW, P4 cosmetic | none (would need a new `if`) | — |
| NEW-3 alerts/plotchar move to the reclaim bar | NEW, side-effect note | — | — |

**Net:** about **+120 tokens** for everything, or about **+130** with G2-7. #6 alone is −59.

---

## #1 Multi-bar raid: PDH/PDL/PWH/PWL, EQ pools, session H/L — CONFIRMED

### Evidence (attempting to refute)

**Swing path.** The swing path HAS a multi-bar reclaim (FIX-Y3, 1613-1618, `reclaimBars` default 4, max 10). That logic only reads `lastSup`/`lastRes` (internal pivots). No other site covers the pools:
- `grep sslRecl|bslRecl` returns only lines 1613-1619.

**PD (1783-1791).** Trace of a two-bar raid:
- Bar 1: `high > pdh`, `close > pdh`. There is no sweep, because `close < pdh` is false. Then 1788 `pdhDone := pdhDone or high > pdh` sets it to **true**.
- Bar 2 closes back below: `pdhSweep` needs `not pdhDone`, so it is **false forever today** (the reset at 1779 only fires when `pdh` changes).
- The FIX-Z2 comment says "spent once traded through (sweep or acceptance)". It treats ONE close beyond as acceptance. That contradicts the file's own FIX-Y3 definition of acceptance (more than `reclaimBars` closes beyond).
- So the intent is internally inconsistent. This is not a deliberate design that should stand.

**EQ (1722-1735).**
- `if high > lvl and confirmed` → stamp only if `close < lvl`.
- `line.delete` / `array.remove` sit OUTSIDE the inner `if`, so the pool is deleted on bar 1 of a close-through.

**Session (1868-1873).**
- On the first touch, `hiSwept := true` and `hiBrk := close > hiLvl` → `hiRaid := false`.
- `hiSwept` only clears at the next session close or at `close < hiLvl - atr`. A reclaim one bar later is invisible.

**Partial coverage elsewhere:**
- When a pool happens to coincide with the current internal pivot, the swing path stamps it, but as kind 1.
- FIX-V11 (1701) keeps kind ≥ 2 only if a pool stamp already landed within `sweepLook`. Here none did, so the SB `sbPoolPref` (3590), A+ `poolOk` (4526) and `sbCtxLong` +3 all fail.

### Design (once-per-level guaranteed, `reclaimBars = 0` ⇒ identical to today)

**Raid window.** `rcN = reclaimBars + 1` bars. This matches FIX-Y3: `bar_index - brkBar <= reclaimBars` ⇒ at most R+1 bars from the break to the reclaim.

**Why `hiN = ta.highest(high, rcN)` cannot leak an older high above the level:**
- **PD/PW:** every bar of the prior period is ≤ the level by definition. Every bar of today with `high > pdh` either swept the level (latch set) or belongs to the pending raid.
- **EQ:** bars around the pivot are below the pool level by the pivot definition.
- **Session:** detection is state-based (below), not window-based, so the window cannot leak.

**Acceptance:**
- `cAbv = ta.lowest(close, rcN)`: if `cAbv > lvl`, every close in the window was beyond the level, so it is accepted (spent or deleted).
- `cBlw` is the mirror.

**Once-per-level:**
- PD: the latch is set by the sweep itself.
- EQ: the pool is deleted on the stamp.
- Session: `hiBrkB := na` when the reclaim fires.

**Calls at global scope.** All `ta.*` calls are made at global scope on every bar.

**A-1 resolution.** On a swing-reclaim bar, `lowSinceBrk` spans ≤ R+1 bars, so `loN ≤ sslExt`. Writing `loN`/`hiN` at the pool sites can never record a shallower extreme than the swing stamp it overwrites. On a single-bar pool raid, `loN == low`, because earlier window bars sit above the pool. So **A-1 is fixed at 0 tokens** by the same edit.

**Why A-1 is only PARTIAL today:**
- Pools cannot stamp a multi-bar raid today.
- So a pool stamp on the same bar as a swing reclaim implies the pool was first touched on THIS bar.
- That means this bar's `low` < pool level ≤ every low since the swing break, so `low == lowSinceBrk`.
- The overwrite only becomes harmful once #1 lands, which is why it must ship together with #1.

**Penetration and grade.**
- `f_poolQ(isLow, lvl)` stays unchanged. Penetration is the reclaim candle's own (`lvl - low`), which is consistent with FIX-Z3 / A-12 on the swing path.
- On a multi-bar raid the grade usually rests on `firm` (close ≥ lvl + ½·nearSp).
- Option, not recommended (it breaks symmetry with the swing path): use `loN`/`hiN` inside `f_poolQ`, at 0 tokens.

### G2-1 core: new globals (insert after line 1490 `inNews = ...`, together with G2-4)

```
rcN    = reclaimBars + 1                 // ◆ G2-1: raid window = break bar … reclaim bar (FIX-Y3 span)
```
Insert after line 1618 (`bslExt = ...`):
```
// ◆ G2-1 (v3.8.6): engineered pools (EQ · PD/PW · session) get the FIX-Y3 multi-bar
// raid. hi/loN = the raid extreme; cAbv/cBlw = every close of the window beyond = accepted.
hiN  = ta.highest(high, rcN)
loN  = ta.lowest(low, rcN)
cAbv = ta.lowest(close, rcN)
cBlw = ta.highest(close, rcN)
```
About +32 tokens.

### G2-1b: EQ pools

BEFORE
```
1722:         if high > lvl and confirmed
1723:             if close < lvl
...
1730:                 lastBslExt  := high
...
1744:         if low < lvl and confirmed
1745:             if close > lvl
...
1752:                 lastSslExt  := low
```
AFTER
```
        if hiN > lvl and confirmed and rollOK and (close < lvl or cAbv >= lvl)   // G2-1: an open multi-bar raid keeps the pool
            if close < lvl
...
                lastBslExt  := hiN
...
        if loN < lvl and confirmed and rollOK and (close > lvl or cBlw <= lvl)
            if close > lvl
...
                lastSslExt  := loN
```
Notes:
- With R = 0: `hiN = high`, `cAbv = close` → `(close < lvl or close >= lvl)` is always true, so the behaviour is byte-identical except for `rollOK`.
- While a raid is open (neither a sweep nor accepted), control falls to the `else if` age expiry. That is fine.
- +16 tokens.

### G2-1a / G2-1c: PD/PW (lines 1783-1791, 1798, 1806)

BEFORE
```
1783: pdhSweep = confirmed and not na(pdh) and high > pdh and close < pdh and not pdhDone
1784: pdlSweep = confirmed and not na(pdl) and low  < pdl and close > pdl and not pdlDone
1785: pwhSweep = confirmed and not na(pwh) and high > pwh and close < pwh and not pwhDone
1786: pwlSweep = confirmed and not na(pwl) and low  < pwl and close > pwl and not pwlDone
1787: // FIX-Z2: the level is SPENT once traded through (sweep or acceptance)
1788: pdhDone := pdhDone or high > pdh
1789: pdlDone := pdlDone or low < pdl
1790: pwhDone := pwhDone or high > pwh
1791: pwlDone := pwlDone or low < pwl
```
AFTER
```
pdhSweep = confirmed and rollOK and not na(pdh) and hiN > pdh and close < pdh and not pdhDone   // G2-1
pdlSweep = confirmed and rollOK and not na(pdl) and loN < pdl and close > pdl and not pdlDone
pwhSweep = confirmed and rollOK and not na(pwh) and hiN > pwh and close < pwh and not pwhDone
pwlSweep = confirmed and rollOK and not na(pwl) and loN < pwl and close > pwl and not pwlDone
// FIX-Z2 → G2-1: SPENT by its sweep, or by acceptance (every close of the window beyond)
pdhDone := pdhDone or pdhSweep or cAbv > pdh
pdlDone := pdlDone or pdlSweep or cBlw < pdl
pwhDone := pwhDone or pwhSweep or cAbv > pwh
pwlDone := pwlDone or pwlSweep or cBlw < pwl
```
1798 `    lastBslExt  := high` → `    lastBslExt  := hiN`
1806 `    lastSslExt  := low` → `    lastSslExt  := loN`

Notes:
- With R = 0 and rollover off, the only difference from today is a bar with `high > pdh` and `close == pdh` exactly, which is no longer "spent". Negligible.
- A rollover spike with a close back above does not spend the level (`cBlw` stays above it). That is intended.
- `pdhDone` is read nowhere else (grep).
- +8 tokens.

### G2-1d: session H/L (inside `f_sesTrack`, 4-space body indent)

**1.** After 1829 `    var bool  loSwept = false` add:
```
    var int   hiBrkB  = na      // G2-1: bar the level was CLOSED through (raid may still reclaim)
    var int   loBrkB  = na
```
**2.** Before 1859 (`    if hiSwept and not na(hiLvl) and close < hiLvl - atr`) add:
```
    // G2-1: a close back inside within reclaimBars of that break is the raid (once: B cleared)
    bool hiRecl = not active and rollOK and bar_index - hiBrkB <= reclaimBars and close < hiLvl
    bool loRecl = not active and rollOK and bar_index - loBrkB <= reclaimBars and close > loLvl
    hiBrkB := hiRecl ? na : hiBrkB
    loBrkB := loRecl ? na : loBrkB
```
- If `hiBrkB` is na, `bar_index - na` is na, so the test is false. That makes it na-safe without `not na()`.
- `confirmed` is not needed: the stamp sites (1899 and 1920) are inside `if confirmed`, and `var` writes made on an intrabar tick are rolled back.
- It is placed BEFORE the 1-ATR latch reset, so a violent reclaim bar is not lost.

**3.** 1863-1864 BEFORE
```
    bool hiRaid = false
    bool loRaid = false
```
AFTER
```
    bool hiRaid = hiRecl
    bool loRaid = loRecl
```
**4.** 1868-1869: append `and rollOK` to both `_hiHit` and `_loHit`:
```
    bool _hiHit = not active and confirmed and not na(hiLvl) and not hiSwept and high > hiLvl and rollOK
    bool _loHit = not active and confirmed and not na(loLvl) and not loSwept and low < loLvl and rollOK
```
**5.** Inside the existing `if _hiHit` block, after `        hiRaid  := not hiBrk` add `        hiBrkB  := hiBrk ? bar_index : na`. Inside `if _loHit`, after `        loRaid  := not loBrk` add `        loBrkB  := loBrk ? bar_index : na`. These are statements in existing scopes; no new `if`.

**6.** Stamp extremes:
- 1906 `        lastSslExt  := low` → `loN`
- 1914 `        lastBslExt  := high` → `hiN`
- 1927 `        lastSslExt  := low` → `loN`
- 1935 `        lastBslExt  := high` → `hiN`

**No double stamp:**
- `hiRecl` clears `hiBrkB` on the bar it fires.
- `hiRecl` and the `_hiHit` sweep can coincide only after a same-bar 1-ATR reset. Both then set `hiRaid = true` (one tuple flag → one stamp), and `_hiHit` sets `hiBrkB := na`.
- `hiRecl` (`close < hiLvl`) and `hiBrk` (`close > hiLvl`) are mutually exclusive.

**Globals read inside the function:** `rollOK` and `reclaimBars` are declared before line 1819, which is legal.

About +62 tokens.

### Side effects (#1)

- **More kind 2/3/4 stamps on M1/M5.**
  - Each stamp moves `lastSslBar`, so `armedSslBar != lastSslBar` re-opens the standard and SB arm guards (4090-4096).
  - `sbPoolOkL`, A+ `poolOk`, and `sbCtxLong` +3 now pass on Judas-shaped raids. That is the intended effect.
  - Expect more SB arms. Measure with LQJRNL before and after.
- **Visual and alert timing.** `plotchar` (5132-5146), the alerts (5615-5617) and `lastEngLoBar` (2264) fire on the RECLAIM bar of a multi-bar raid. No plot or alert count changes.
- **Session label.** A reclaimed session level still reads "H broken" / dotted (NEW-2, cosmetic).

### Calibration

- **XAU M1 / NAS M5:** `reclaimBars` 4 (default) = 4 minutes on M1, which is right for a gold stop-run (1-3 bars beyond, then reclaim), and 20 minutes on NAS M5. Use 2-3 on M5 indices if the journal shows late "reclaims" that are really retests.
- **BTC:** works unchanged.
  - The PD boundary is the UTC day (N-13).
  - Weekly PWH/PWL on Binance flips Monday 00:00 UTC.

---

## A-1: same-bar stamp overwrite — PARTIAL (latent), fixed by G2-1 (0 tokens)

Sites: 1730, 1752, 1798, 1806, 1906, 1914, 1927, 1935 → `hiN` / `loN` (listed above).

- **Proof it is harmless today:** a pool stamped on the same bar as a swing reclaim must have been first touched on this bar. Otherwise EQ is deleted, PD is spent and session is latched earlier. So `low` ≤ every low since the swing break, i.e. `low == sslExt`.
- **Proof it is fixed after #1:** on a reclaim bar, `lowSinceBrk` spans ≤ R+1 bars, so `loN ≤ sslExt`.
- **Downstream reader:** only `suLSweepExt := ... : lastSslExt` (4221/4379) reads this, which feeds the `slRaidL` stop (4332) and the invalidation at 4156.

---

## #6: ATR cap shrinks the SL pad — CONFIRMED

Line 1279: `atr = atrCapIn > 0 and atrAvg50 > 0 ? math.min(atrRaw, atrCapIn * atrAvg50) : atrRaw`.

**Mechanism.** `atrAvg50` is an SMA-50 of an RMA-14, which is 50 minutes on M1. At NY 09:30 (NAS) or 08:30 data (XAU), the RMA climbs to 2-2.5× the pre-market mean while the SMA-50 lags. The 1.5× cap binds for 20-60 bars.

**Intent check.** FIX-Y4 meant to stop one news candle from re-scaling the GATES. A stop pad is not a gate: a larger pad is the safe side.

**Example, XAU M1:**
- avg $0.8, raw $2.0, cap $1.2.
- Pad 0.35 × $1.2 = $0.42, against 0.35 × $2.0 = $0.70.
- The difference is about one spread, at the moment wicks re-run the most.

**All sites.** `grep -o "SL_PAD_ATR \* atr"` returns 32 occurrences on 30 lines, and there is no other spelling:
- 2326, 2327, 2328, 2329, 2964, 2994, 3243, 3244, 3254, 3255, 3289, 3312, 3348, 3362, 3406, 3407, 3962, 4005, 4331, 4332, 4450, 4451, 4677, 4678, 4945, 4946, 4977, 4978
- 5646 (×2) and 5647 (×2), the journal SLa/SLr. These keep the journal consistent with the live stop.

### G2-6 patch

After 1279 add:
```
slPad    = SL_PAD_ATR * atrRaw     // ◆ G2-6: stop pad uses the UNCAPPED ATR (cap is for gates; wider pad = safe side)
```
(`math.max(atr, atrRaw)` is identical to `atrRaw`, because `atr ≤ atrRaw` always.)

Then replace all 32 occurrences, byte-safe on CRLF:
```
sed -i 's/SL_PAD_ATR \* atr\b/slPad/g' liqudity_trap_trading.v3.8.6.txt
```
Afterwards check `grep -c "slPad"` = 33.

- **Tokens:** each `SL_PAD_ATR * atr` is 3 tokens and becomes 1, so −64; the new line costs +5. **Net −59.**
- **Side effects:**
  - Wider SL at the opens → lower R:R. A few more setups may fail a min-RR or TP1 gate in the first 30-60 minutes, and position size (risk-based) gets smaller.
  - TP distances that are multiples of risk get longer.
  - This is the correct trade-off for M1/M5.

---

## #7: rollover spread-spike sweeps — CONFIRMED

- **No existing filter:** a grep for rollover, 1655, 1700 or 17:00 finds none.
- **Mechanism.** At the 17:00 NY rollover and the 18:00 reopen (XAU and NAS CFDs halt 17:00-18:00), the spread widens 5-20×. On a BID chart the low spikes and the close comes back.
- **Sites affected:**
  - The swing test at 1619 satisfies `low < lastSup and close > lastSup`.
  - The EQL pool (1744) is deleted by a price nobody traded.
  - PDL/PWL (1784/1786) and session `_loHit` (1869) are hit the same way.
- **BSL on the bid** is rarely spiked, because the spread widens around mid and the bid moves down. It is gated as well, since 17:00-18:15 is untradeable anyway.

**Window subtlety.** With the G2-1 windows, a spike bar at 16:59 can still sit inside `loN` at 18:01 (the halt removes the bars in between). So `rollOK` must be false while ANY bar of the window is in the rollover.

### G2-4 patch

After 828 (`reclaimBars = ...`) add:
```
rollOn  = input.bool(true, "Ignore raids printed in the daily rollover / reopen", group = grpL,
     tooltip = "Bid-chart spread spikes at 17:00 NY rollover and the 18:00 reopen fake SSL sweeps. Auto-off on the Crypto profile; on an exchange BTC feed keep it off, on a BTC CFD set the profile to Manual and keep it on.")
rollSes = input.session("1655-1810", "Rollover window (NY time)", group = grpL)
```
(The continuation line is indented 5 spaces, which is not a multiple of 4.)

After line 1490 (`inNews = ...`) add:
```
rcN    = reclaimBars + 1                 // ◆ G2-1: raid window = break bar … reclaim bar (FIX-Y3 span)
rollOK = not rollOn or profIdx == 4 or ta.highest(f_inSes(rollSes) ? 1 : 0, rcN) == 0   // ◆ G2-4
```

1619-1620: append `and rollOK` (place it before the trailing comment):
```
sslSweep = not na(lastSup) and ((low < lastSup and close > lastSup and not supBroken) or sslRecl) and sslLvlFresh and rollOK   // FIX-Z1 · G2-4
bslSweep = not na(lastRes) and ((high > lastRes and close < lastRes and not resBroken) or bslRecl) and bslLvlFresh and rollOK   // FIX-Z1 · G2-4
```
EQ, PD and session: `rollOK` is already included in the G2-1 text above.

- **Pool behaviour during the window.** In the EQ pool test, `rollOK` sits in the OUTER condition, so a pool survives the spike (nothing is touched). A real break during rollover is consumed after the window.
- **Swing state.** `supBroken` is untouched, because a spike that closes back does not satisfy `brokeDn`.
- **Tokens:** inputs about 22, `rollOK` about 16, uses about 22 → about **+60**.
- **Calibration:**
  - FX: rollover 16:58-17:10.
  - XAU/NAS: halt 17:00-18:00; the reopen spread normalises by about 18:05-18:10.
  - On M5 with R = 4, the block ends at about 18:35 (dead time anyway).
  - Sunday 18:00 open: covered, because the session string has no day filter, i.e. all days.
- **BTC and crypto:**
  - Auto-off through `profIdx == 4`. It must be off on 24/7 exchange feeds, where there is no rollover and 17:00 NY is a normal hour.
  - Caveat: BTC **CFDs** do spike at 17:00. The tooltip tells those users to use Manual.

---

## F-5: Asia H/L raid during London/NY KZ cannot arm — CONFIRMED

- **The gate.** Line 1920 is `if sbCtx and sbAsiaPool and confirmed`. `sbCtx` covers only `sbSesLO` 03:00-04:00 plus `sbPreMin` 15, i.e. from 02:45, and the AM/PM windows.
- **What happens to a London Judas.** A London Judas through Asia H/L at 02:00-02:45 sets `asiaHiSw` (the `f_sesTrack` latch is consumed, `hiSwept := true`) but never stamps.
- **The same in NY.** An Asia-level raid at 07:00-09:45 NY is likewise score-only (`sesHiSwept`, `lastEngHiBar`).
- **No other pool covers London.** During London (02:00-05:00) the London session is ACTIVE, so its own levels cannot be raided. The only engineered pools are Asia, PD and EQ, so London setups are starved of kind ≥ 2.

### G2-3 patch

BEFORE `1920: if sbCtx and sbAsiaPool and confirmed`

AFTER
```
if (sbCtx or inKZ) and sbAsiaPool and confirmed      // ◆ G2-3: Asia H/L is THE London/NY-KZ Judas pool
```
- `inKZ` is defined at 1487 and includes Asia, but Asia hits are impossible while Asia is active (`not active`), so the effect is London + NY + SB.
- Raids in the 00:00-02:00 dead zone stay score-only.
- +4 tokens.
- The input label at 949 says "(inside SB windows only)". Update the tooltip text, not the title, to be safe with saved settings.
- **Side effect:** more kind-4 arms in London 02:00-02:45 and NY 07:00-09:45 (non-SB machine plus A+ `poolOk`). This is the operator's doctrinal choice, and ICT doctrine supports it.

---

## F-6: spread-aware sweep thresholds — CONFIRMED

- **No spread in the grading code.** Lines 1590-1990 never read `spr`/`hiA`/`loA` (grep).
- **Thresholds today:**
  - `firm` = 0.5·N·ATR (1626, 1689)
  - `pen` = N·ATR (1630, 1689)
  - N = 0.25 (FX profile), 0.30 (XAU/Index), 0.35 (Crypto)
- **XAU M1, ATR $0.6:** firm = $0.09 and pen = $0.18, against a $0.25-0.35 spread. VALID can be less than one spread.

### G2-5 patch

After 1282 (`spr = ...`) add:
```
nearSp  = math.max(NEAR_LVL_ATR * atr, spr)      // ◆ G2-5: sweep-grade tolerance never below one spread
```
Replace `NEAR_LVL_ATR * atr` with `nearSp` ONLY on these lines:
```
1626:    bool  firm = isLow ? close >= lastSup + nearSp * 0.5 : close <= lastRes - nearSp * 0.5
1630:    if firm or pen >= nearSp
1689:    bool _ok = isLow ? (close >= lvl + nearSp * 0.5 or lvl - low >= nearSp) : (close <= lvl - nearSp * 0.5 or high - lvl >= nearSp)
```
- Leave 1605/1606/1701/1710 (freshness and kind proximity) on ATR.
- **Tokens:** 7 × (−2) + 8 = **−6**.
- **Calibration:**
  - **XAU M1** (spread $0.30): pen floor $0.30, firm $0.15. It binds while ATR < $1.0, i.e. most of Asia and London on M1.
  - **XAU M5** (ATR $2+): inert.
  - **NAS M5** (ATR 15-25, spread 1-2): inert.
  - **BTC exchange** (spread about $1): inert.
  - **BTC CFD** on a weekend M1 (ATR $15, spread $30): binds, which is correct.
- **Side effect:** fewer grade-2 raids on XAU M1 → fewer arms at `minArmQual` 2. This removes exactly the sub-spread pokes.

---

## A-10: ATR floor — PARTIAL (optional G2-7)

- **Confirmed:** there is no floor at 1279.
- **Refuted in part:** a floor of `0.5 × atrAvg50` almost never binds. RMA-14 rarely falls below half of its own SMA-50, except about 30-50 bars after a news spike, when avg50 is inflated.
- **The real low-vol hazard is spread-relative** (Asia XAU M1, ATR ≈ spread), and that is handled where it matters by G2-5.

Optional, about +8 tokens:
```
atr      = math.max(atrCapIn > 0 and atrAvg50 > 0 ? math.min(atrRaw, atrCapIn * atrAvg50) : atrRaw, 0.5 * nz(atrAvg50))
```
(`math.max(na, x)` returns na, so the first bars stay na, as today.)

A stronger variant, `..., 0.5 * nz(atrAvg50), 2 * spr)`, floors EVERY gate at 2 spreads (displacement body ≥ 1 spread). That is good for XAU M1 Asia, but it changes all modules, so only adopt it after a journal comparison.

---

## NEW findings

**NEW-1 (P3): the session raid latch re-arms after only 1 ATR (1859-1862).**
- PD is once per day, EQ is once per pool, and swing re-arms at `SWEEP_CTX_ATR` (3-5 ATR, 1601-1604).
- Session levels re-arm after `close` travels 1 ATR, which is about $0.6 on XAU M1.
- So price chopping ±1 ATR around Asia H produces several kind-4 stamps of the same level. Each one moves `lastSslBar`, which re-opens the once-per-sweep arm guards.
- Fix (G2-8, +4 tokens): `close < hiLvl - SWEEP_CTX_ATR * atr` and `close > loLvl + SWEEP_CTX_ATR * atr`.
- This also partially covers A-5 (re-raid of a broken level).

**NEW-2 (P4, cosmetic):** with G2-1d, a reclaimed session level keeps the "H broken" text and dotted style, because it was set on the break bar. A fix needs a new `if hiRecl and not na(hiLn)` block, so it is skipped.

**NEW-3 (side-effect note):**
- The EQ/PD/session `plotchar` (5132-5146), the alerts (5615-5617) and `lastEngLo/HiBar` (2264-2265) now also fire on multi-bar raids, on the reclaim bar.
- No plot or alert was added.
- Users with "[LIQ] Prev-day / week level swept" alerts will see more of them on M1.

**Checked, OK:**
- PD `[1]` + `lookahead_on` does not repaint.
- `pdhDone` is not read outside 1775-1791.
- The new names (`hiN loN cAbv cBlw rcN rollOK rollOn rollSes nearSp slPad hiBrkB loBrkB hiRecl loRecl`) have 0 collisions (grep -cw).
- `reclaimBars` is in 0..10, so `rcN` is in 1..11, a valid `ta.highest` length.
- `f_inSes` takes a simple string, and `input.session` returns one.

## Apply order (for v3.8.6)

1. G2-4 inputs at 829.
2. `rcN` + `rollOK` after 1490.
3. `nearSp` after 1282 and `slPad` after 1279 (do the 1279 line before 1282).
4. G2-1 windows after 1618 and the `rollOK` additions at 1619/1620.
5. EQ.
6. PD.
7. Session.
8. Stamp extremes.
9. F-5.
10. The `slPad` sed.
11. Optional: G2-7 and G2-8.

**Compile check:** no new `if`, no plot or alertcondition. Every `ta.*` call is at global scope. Continuation indent is 5.
