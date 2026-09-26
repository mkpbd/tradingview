# IMPROVEMENT PLAN — SMC Suite v8.2.1 → v8.3.0

Source of findings: `FORENSIC_AUDIT_SMC_v8.2.1.md` (B1-B15, T1-T14, RC1-RC7).
Rule: one step = one commit = one compile = one replay check. Never two steps in one commit.
Baseline first: copy `SMC.txt` → `SMC_v8.2.1.backup.txt` before step 1.

Legend: **Touch** = lines to edit · **New** = new code · **Tokens** = rough compile-token delta (limit 100 256, build sits at the edge) · **Verify** = pass condition.

---

## STEP 0 — Token headroom (prerequisite)

Build is at the compiler limit; steps 4, 6, 9, 11 add code. Free ~4-5k tokens first.

Remove (all default-OFF or cosmetic, audit §15 REMOVE):
- M43 hidden-liquidity setups: `en_M43`, `s43`, `s43b`, two `f_bid` (2570, 2602-2603, 2652, 2670), `ctx.hidSSLBar/hidBSLBar` writes (2117-2120).
- M38-P4: `p4`, `p4b`, two `f_bid` (2470, 2476, 2525, 2555).
- Hidden-liquidity engine itself only if nothing else reads `ft.hiddenSSL/BSL`: readers left = label rank 10/11 and one alertcondition → remove all three, then remove 1258-1275 and `Ctx.hidSSLprev/hidBSLprev`.
- Wyckoff: `Struct.wyckoff`, 956-960, panel row 3 (3317-3318) → replace row with "Regime" = `st.trend` + (`ft.inRange ? " · range" : "")`.
- Stale tooltip 696 text → "Dealing range = current leg (see PD array)".
- Title: "SMC / ICT Suite v8.3.0" (drop CRT).

Tokens: ≈ −3 500. Verify: compiles; data-window plots unchanged except removed ones.

---

## STEP 1 — Confirm event alerts (B4, RC5)

Touch 3390-3397. Wrap every event condition:

```pine
alertcondition(barstate.isconfirmed and (st.bullBOS or st.bearBOS), "Structure: BOS", ...)
```
Same for CHoCH-real, CISD, Sweep, HP OB, PROP, OB 50% (hidden-liquidity alert removed in step 0).

Tokens: +40. Verify: create all alerts on 1m BTC, run one hour; every alert has a matching label/line at bar close; none without.

---

## STEP 2 — Leg-origin helper (B1, RC3)

**New** (after `f_xb`, ~line 968):

```pine
// origin of the leg that just broke a swing: lowest low (bull) / highest high (bear)
// between the broken swing's bar and the bar before this one. Returns [idx, price].
f_legOrigin(isBull, fromIdx) =>
    span = math.min(math.max(bar_index - fromIdx, 1), 490)
    bestOff = 1
    bestVal = isBull ? low[1] : high[1]
    for k = 2 to span
        v = isBull ? low[k] : high[k]
        if (isBull and v < bestVal) or (not isBull and v > bestVal)
            bestVal := v
            bestOff := k
    [bar_index - bestOff, bestVal]
```

Wire-up:
- Orchestration (1896-1905): on BOS bar compute `[legIdx, legPx] = f_legOrigin(st.bullBOS, st.bullBOS ? preHighIdx : preLowIdx)`; pass `legIdx` to `f_moveStrength` instead of `preLowIdx/preHighIdx`. Same for CHoCH with `st.bullCHoCH ? ctx.majorHighIdx : ctx.majorLowIdx` as `fromIdx` (protected swing after step 4).
- `f_zones` signature: add `oIdxIn` parameter; line 1379 `oIdx = oIdxIn`.
- KL lookup 1386 `z.idx == oIdx` → overlap match: `z.kind == "SR" and z.bull == isBull and z.kl == 0 and z.idx >= oIdx - cf.swingLen and z.idx <= oIdx + cf.swingLen` (origin low is not always a pivot bar).
- OB candle selection (1416-1439): `obOff = bar_index - oIdx`; then search backwards from `obOff` (up to `cf.swingLen` bars, not beyond the swing) for the **last opposite-colour candle before the first displacement candle**: walk `k = obOff-1 … 1`; first `k` where body ratio ≥ 0.5 and colour = trade direction is the displacement candle; OB = nearest opposite-colour candle at index > k (or the origin candle if none). Keep T2/G2 labels, drop G1 (always-true artefact).
- Arrival strength (1977): unchanged (recent leg, fine).
- Store `ctx.legIdx/legPx` for step 7 (PD) and step 4 (protected swing).

Ctx fields: +2 (`legIdx`, `legPx`) — Ctx is at 254 cap → remove `hidSSLprev/hidBSLprev/hidSSLBar/hidBSLBar` (step 0) to make room.

Tokens: +350. Verify: on 30 BOS bars in replay, OB box sits on the last opposite candle before the displacement; `plot(ctx.legIdx)` in data window equals visual leg low.

---

## STEP 3 — Sessions with timezone (B5, RC6)

Inputs (group gPD):
```pine
i_ssnTz   = input.string("UTC", "Session timezone", options = ["UTC","Europe/London","America/New_York","Asia/Tokyo","Exchange"])
```
Defaults changed: Asia `0000-0700`, London `0700-1000`, NY `1200-1500` (UTC; non-overlapping).
1869-1871: `time(timeframe.period, i_ssnAsia, i_ssnTz == "Exchange" ? syminfo.timezone : i_ssnTz)`.
SESH/SESL placement: replace `lonOpen` (1930) with `asiaEnd = ssnIntra and not inAsia and inAsia[1]`. Keep expiry on next `asiaEnd`.

Tokens: +60. Verify: EURUSD on two brokers; London window starts 07:00 London local across a DST boundary (replay March/October).

---

## STEP 4 — Structure rebuild (B2, B3, RC1) — the core change

### 4.1 State
New UDT (keeps Ctx under cap; move structure state out of Ctx):
```pine
type Str
    float curHigh = na,  int curHighIdx = 0,  float prevHigh = na, int prevHighIdx = 0, bool hiBroken = false
    float curLow  = na,  int curLowIdx  = 0,  float prevLow  = na, int prevLowIdx  = 0, bool loBroken = false
    string hiType = ""      // "HH" | "LH" of the last confirmed pivot high
    string loType = ""      // "HL" | "LL"
    float protHigh = na, int protHighIdx = 0   // protected swing (bear trend) = leg origin of last bear BOS/CHoCH
    float protLow  = na, int protLowIdx  = 0   // protected swing (bull trend)
    string trend = "RANGE"
    int   barsSinceEvt = 0
    int   failCnt = 0        // consecutive failed follow-throughs
    int   pendDir = 0        // CHoCH without displacement waiting for follow-through
    int   pendBar = -999
```
`ctx.majorHigh/Low(+Idx)` remain as **aliases** written from `protHigh/protLow` so L4/L7/labels stay untouched.

### 4.2 Struct output (add, keep existing names)
```pine
bool internalBullBOS, internalBearBOS   // counter-trend pivot break, no state change
bool weakBullBOS,  weakBearBOS          // trend-aligned break without displacement, no state change
bool bullCHoCH, bearCHoCH               // now: close through protected swing against trend (+disp or follow-through)
```

### 4.3 Displacement proxy available inside f_structure
`f_moveStrength` runs after `f_structure` today. Cheap in-line proxy for the gate (full `mv` still computed afterwards for labels/OB):
```pine
dispOk = cd.bodyRatio >= 0.5 and (high - low) >= aV * 0.8   // or dispScore>=1 next bar
```
Input `i_dispGate = "Candle" | "Move (mv.strong)" | "Off"`. "Move" mode: state change deferred to the same bar's `mv` (computed right after; move the trend-flip block to orchestration after `mv` — do this only if "Candle" proves too loose in validation).

### 4.4 Rules (per bar, before pivot shift)
```
pivot classification (on confirmation):
  hiType = swH > prevHigh ? "HH" : "LH";  loType = swL < prevLow ? "LL" : "HL"

bull side, close > curHigh and not hiBroken:
  hiBroken := true
  if trend == BULLISH or trend == RANGE:
      if dispOk:  bullBOS; trend := BULLISH; protLow := legOrigin(low since curHighIdx); failCnt := 0
      else:       weakBullBOS (no state); pend follow-through: if close > curHigh again within 3 bars → promote to bullBOS
  else (trend == BEARISH):
      if close > protHigh:
          if dispOk: bullCHoCH; trend := BULLISH; protLow := legOrigin; hiBroken := true; loBroken := false
          else:      pendDir := 1, pendBar := bar_index   (promote to bullCHoCH if close > protHigh on a bar ≤ pendBar+3)
      else: internalBullBOS (label only, feeds breakUp for trap modules)

bear side: mirror.

failed follow-through:
  a bar within cf.failedCloseBars after any BOS/internalBOS that closes back through the broken level → failCnt += 1
  failCnt >= 2 → trend := RANGE (protected swings kept)
  barsSinceEvt > rangeBarsThresh → RANGE (fallback, unchanged)

protected swing maintenance:
  in BULLISH trend, each confirmed HL raises protLow only if a bullBOS occurred after that HL (i.e. it is the HL that produced the last BOS) — implemented as: on bullBOS, protLow := legOrigin (step 2). Nothing else moves it.
```

### 4.5 Readers to re-point
- `ft.breakUp := st.bullBOS or st.internalBullBOS or st.weakBullBOS or ft.runUp` (2029) so M01/M02/M05/M14/M15/M22/M24/M62/M63/M72/M38 keep their break events.
- Zone engine OB creation stays on `bullBOS` only (displaced by construction now) → remove `if not mvStrong` T5 branch? Keep (mv can still be weak in "Candle" gate mode).
- `w29/w51` ("weak BOS") → read `st.weakBullBOS`.
- Labels: rank 3 "BOS▲ weak" → weak flag; add "iBOS▲" for internal at tier All.
- `preTrend` gate unchanged.
- `movePhase` (955): IMPULSIVE if close beyond the leg extreme in trend direction (`close >= highest since protLowIdx` for bull), else RETRACEMENT; RANGE trend → "RANGE".
- HTF (`f_htf` 1798-1828): same rule set with `dispOk = |c1-o1| / (h1-l1) >= 0.5`; `hMajor*` become `hProt*`; `hTrend` NEUTRAL until first HTF BOS **or** first HTF CHoCH.

Tokens: +900 (−400 from Ctx field removal). Verify (replay, per 100 bars, before/after): BOS count in chop ↓ ≥ 50%; ≥ 1 CHoCH per visible reversal; trend flips ≤ 1 per reversal; `plot(str.failCnt)`; RCB/QM now appear at real CHoCH.

---

## STEP 5 — Sweep qualification (T3, §9)

- `Liq.qual` computed at creation/merge: `pooled or kind in {PDH,PDL,PWH,PWL,SESH,SESL}`; `ext` counts only if input `i_sweepQual == "Include external"`.
- In `f_liq` SWEEP branch (1209-1227): write `cx.sweptHighBar` only when `L.qual`; else `cx.intSweptHighBar` (new, replaces `intSwpBear` from 2219-2222 which becomes redundant).
- Orchestration 1888-1891 (`st.bullSweep` pivot wick): write `intSwept*Bar` only.
- Readers: HP OB (1461), M41 (2146), M45 (2129-2132), M54 (2183), `relCnt` (2154), `chochUpX` (3180), `f_conf` sweep credit (2942 via `fv.sweptLow`) → qualified. M47, M53, M49 → internal.
- `ft.sweptLow` stays "any sweep this bar"; add `ft.sweptLowQ` for M10: `s10 = … and (ft.sweptLowQ or (ft.sweptLow and ft.zb.kind != ""))` — pivot sweep only counts inside a zone.

Tokens: +200. Verify: count of HP★ OB on 1m BTC per 1000 bars drops; M10 signals only at POOL/PD/PW/SES or in-zone.

---

## STEP 6 — Unified scoring (B7, RC2)

Replace base-score bidding with tiers. `f_bid(b, cond, name, tier, note)`; pick = highest tier, tie → higher `seq`, tie → earlier declaration.

Tier table (edit each `f_bid` call's number):
| Tier | Modules |
|---|---|
| 4 | M41, M45 (★ form), M54, M68, M37, M42, M73 |
| 3 | M10, M36, M39, M46, M33, M51, M09, M45 (BOS form) |
| 2 | M08, M40, M58, M62, M72, M70, M01, M02, M05, M15, M65 |
| 1 | everything else |

`seq` (direction-aware, computed once per bar):
```pine
seqL = (ft.sweptLowQ or bar_index - ctx.sweptLowBar <= cfg.armBars ? 1 : 0)
     + (ft.dispBull or ctx.lastDepStrong ? 1 : 0)
     + (bar_index - ctx.lastChochBar <= cfg.armBars and ctx.lastChochDir == 1 ? 1 : 0)
     + (ft.zb.kind != "" ? 1 : 0)
```
Final: `g.score := tier * 2 + f_conf(...)` ; grade thresholds become inputs (`i_gradeAplus = 11`, `i_gradeA = 8`), `i_minScore` default 6. `Best` gets `int q` (seq) field.

Tokens: +150. Verify: same chart, label text shows tier-consistent grades; M37/M42/M73 outrank candle-only modules on the same bar.

---

## STEP 7 — PD array = leg range (B6)

```pine
legHi = st.trend == "BULLISH" ? highest high since protLowIdx (ta.highest over span) : ctx.majorHigh
legLo = st.trend == "BEARISH" ? lowest low since protHighIdx : ctx.majorLow
pdIn  = not na(legHi) and not na(legLo) and legHi > legLo
pdPct = pdIn ? clamp((close - legLo) / (legHi - legLo), 0, 1) : 0.5
pdBeyond = pdIn and (close > legHi or close < legLo)
```
Span computed with `math.min(bar_index - idx, 490)` and a loop (or `ta.highest(high, n)` is not allowed with series length ≥ 0? it is allowed in v6 with series int → use `ta.highest(high, span)`).
Score unchanged; gate unchanged (default off). Panel row text: "beyond leg (expansion)" when `pdBeyond`.

Tokens: +120. Verify: in an up-leg the panel reads premium near the leg high, discount near protLow; never "outside" during the leg.

---

## STEP 8 — TP target quality (B8, RC7)

`f_nearestOpp` (2893): skip zone unless `(z.kind == "SR" ? z.kl >= cf.klMinCrit : (z.confirmed and not z.weak))`. Add third pass over `cx.lv` for qualified liquidity (`L.qual`, not done) so TP1 can be a POOL/PD/PW/SES level when no zone/FVG exists (fewer signals dropped by `rrReal` for the wrong reason).

Tokens: +90. Verify: TP1 lines land only on scored KL, live OB/BRK/RCB/QM/RJB(confirmed), FVG, or major liquidity.

---

## STEP 9 — Per-side zone slot (B10)

New UDT `ZS` (kind, touches, sweepReq, fifty, idm, hp, kl, flipped, nearSwept, depStrong, top, bottom, prop). `Feat` gets `ZS zb` and `ZS zs`; delete the flat `ft.z*`, `ft.atDemand/atSupply/atSupport/atResist/atProp` fields → derive:
```pine
atBullZone = ft.zb.kind != ""      // replaces atDemand or atSupport
atBearZone = ft.zs.kind != ""
ft.atDemand := ft.zb.kind != "" and ft.zb.kind != "SR"  (keep as computed bools for panel/f_stop)
```
`f_zones` maintenance (1720-1747): two `bestPri` accumulators, write into `zb` or `zs` by `z.bull`.
Readers: `zoneOkBull` → `ft.zb.*`; `zoneOkBear` → `ft.zs.*`; every long module `ft.zKind` → `ft.zb.kind`; short → `ft.zs.kind`; `f_conf(fv, trend, isLong)` → `z = isLong ? fv.zb : fv.zs`; `f_stop` same; panel shows both; `zoneTouch/arrDirNow` (1972-1975) → arrival computed per touched side.

Tokens: +500 (field moves are near-neutral; reader edits are renames). Verify: overlapping supply+demand bar → both slots populated; long modules no longer silent inside overlaps.

---

## STEP 10 — CISD rebuild (T11)

Ctx/Str fields: `upSerOpen, upSerBar` (open of the first candle of the running up-close series), `cisdUpRef` (open of the series that delivered the last leg high), mirror for down.
```
each bar:
  if close > open and not (close[1] > open[1]): upSerOpen := open; upSerBar := bar_index
  if high >= hiMakerHigh (new leg high this bar, from §3.5 tracker): cisdUpRef := upSerOpen
  cisdBear := not na(cisdUpRef) and close < cisdUpRef and (not i_cisdNeedSweep or bar_index - ctx.sweptHighBar <= cf.armBars)
  on cisdBear: cisdUpRef := na   (consumed)
```
Input `i_cisdNeedSweep` default true. Mother-candle rule dropped (series start replaces it). M46 reliability count unchanged.

Tokens: +100 (replaces 932-951). Verify: CISD▼ prints on the first close below the opening of the last up-series after a qualified sweep; no CISD deep inside a trend without a sweep.

---

## STEP 11 — POI reaction state / confirmed entry mode (RC4)

Input `i_entryConfirm = "IMMEDIATE" | "CONFIRMED"` (default IMMEDIATE = current behaviour, so validation can A/B).
Sx fields: `poiDirL, poiBarL, poiRefL` (long side), mirror short.
```
stage 1 (tap): zoneOkBull and revBull  → poiBarL := bar_index; poiRefL := high (reaction candle high); poiDirL := 1
stage 2 (confirm), within 8 bars, edge-triggered:
    poiConfL = poiDirL == 1 and bar_index - poiBarL >= 1 and (close > poiRefL or ft.newBullFvg) and close > ft.zb.bottom
    on poiConfL: poiDirL := 0
invalidate: close < ft.zb.bottom - buf → poiDirL := 0
trigBull = i_entryConfirm == "IMMEDIATE" ? revBull : poiConfL
```
Replace `revBull`/`revBear` with `trigBull`/`trigBear` in the zone modules only (M04 M06 M08 M09 M12 M21 M23 M33 M36 M37 M39 M40 M42 M44 M51 M70 M73 and armed M41 M45 M46 M48 M49 M50 M52 M54 M68). Trap/break modules keep `revBull`.
In CONFIRMED mode `f_stop` uses `math.min(low of tap candle, zone bottom)`: store `poiLowL` at stage 1.

Tokens: +300. Verify: A/B per module expectancy in the strategy port (audit §17-6); CONFIRMED mode signals/100 bars lower, avg R higher.

---

## STEP 12 — Cosmetics & naming (P3)

- M02 label "Pin-bar continuation", M45 note "sweep → BOS/CHoCH", "CHoCH✕" derived from qualified sweeps (step 5 already).
- Remove `G1` OB type text; keep T1/T2/G2.
- Legend row 3 update; panel "Regime" (step 0).
- `f_xb` anchor: when clamped, set box/line style dotted to signal "anchor truncated".
- Version bump in header + changelog block listing B-numbers fixed.

Tokens: ±0.

---

## TOKEN LEDGER

| Step | Δ tokens | Running (from ~100 000) |
|---|---|---|
| 0 | −3 500 | 96 500 |
| 1 | +40 | 96 540 |
| 2 | +350 | 96 890 |
| 3 | +60 | 96 950 |
| 4 | +500 net | 97 450 |
| 5 | +200 | 97 650 |
| 6 | +150 | 97 800 |
| 7 | +120 | 97 920 |
| 8 | +90 | 98 010 |
| 9 | +500 | 98 510 |
| 10 | +100 | 98 610 |
| 11 | +300 | 98 910 |

Margin ≈ 1 300. If step 4 overruns: also remove M11, M14, M23 (default-OFF, tier 1) ≈ −600.

---

## VALIDATION GATE PER STEP (from audit §17)

| Step | Gate |
|---|---|
| 0 | compiles; label/line/box counts identical on 1m BTC 20k bars |
| 1 | alert log == label set over one live hour |
| 2 | 30 sampled BOS: OB on last opposite candle before displacement |
| 3 | London window correct across DST on 2 brokers |
| 4 | chop BOS ↓50%; CHoCH ≥1 per reversal; RANGE inside chop; historical == replay |
| 5 | HP★ count ↓; M10 only at qualified levels / in zone |
| 6 | grade order follows tier on same-bar candidates |
| 7 | PD reads premium/discount inside a leg, never "outside" |
| 8 | TP1 never on unscored SR / weak RJB |
| 9 | overlap bar populates both slots |
| 10 | CISD only after qualified sweep (default) |
| 11 | A/B expectancy per module (strategy port), CONFIRMED ≥ IMMEDIATE on avg R |

Final acceptance: every default-ON module expectancy ≥ 0 over ≥ 50 trades on ≥ 3 symbols; no historical/realtime divergence; object counts < 500.

---

## ORDER RATIONALE

0-3 are independent, low-risk, unblock the rest. 4 is the pivot: 5-7 and 10 depend on protected swings / leg origin. 6 depends on 5 (seq uses qualified sweep). 9 before 11 (11 reads per-side slots). 8 any time after 4. 12 last.
