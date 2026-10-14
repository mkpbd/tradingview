# SMC / ICT Suite v8.4.0 — Forensic Audit

| | |
|---|---|
| Source | `SMC_v8.4.0.txt` (3,915 lines, Pine Script v6, `indicator()`, overlay) |
| Audit date | 2026-10-14 |
| Method | Full read of the source, static trace of every signal path from market condition → feature flag → candidate → `f_sig` → label/alert. No code was modified. |
| Scope | Phases 1–2 and 7 of the audit brief (inventory, bug audit, severity). Entry footprint, false-signal scenarios, roadmap, test plan and changelog are separate documents in this folder. |
| Limits | No Pine compiler or TradingView session was available during this audit. Compilation, the compiled-token count and any performance statistic are **not** verified here. Nothing in this document is a measured result; every finding is a static-analysis claim with the line evidence beside it. |

Companion documents: `SMC_ENTRY_FOOTPRINT_ANALYSIS.md`, `SMC_FALSE_SIGNAL_ANALYSIS.md`, `SMC_IMPROVEMENT_ROADMAP.md`, `SMC_VALIDATION_TEST_PLAN.md`, `SMC_CHANGELOG.md`.

Line numbers refer to `SMC_v8.4.0.txt` as shipped (header comment included). Findings F1–F16 were first raised in the 2026-10-14 Bangla review (`FORENSIC_AUDIT_v8.4.0_BN.md`, `MostosImportentIndicator_4`); every one of them was re-derived from the source for this document. F17–F26 are new.

---

## 1. Executive summary

The build is architecturally sound: one feature vector per bar, every drawing and alert confirm-gated, three `request.security` calls all using the `[1]` + `lookahead_on` pattern that does not leak future data. **No future-data leakage was found.** The HTF, FVG, zone, label, line and alert layers are stable after bar close.

The defects are logic defects in the **entry layer**, and they cluster around one root cause: v8.4.0 switched the default zone trigger from a one-bar reversal candle (`IMMEDIATE`) to a multi-bar state machine (`CONFIRMED`, lines 2717–2749), but most of the per-bar flags the zone modules consume were written for the one-bar model and are not carried across the arm→confirm gap. The consequences:

| Severity | Count | What is affected |
|---|---|---|
| P0 | 2 (F2, F3) | Stop-loss placed above the reaction / sweep wick; the engine's own invalidation (`sx.poiLowL`) sits below the stop it publishes. |
| P1 | 11 (F1, F4–F7, F9–F11, F17–F19) | Flagship zone setups silently impossible in the default mode (F1, F19); the FVG reaction path is dead under the default FVG mode (F18); structure locks after a weak break (F4, F5, F17); wrong level for the R2 CHoCH rule (F17); limit entry on the wrong side of the close (F7). |
| P2 | 6 (F8, F12–F16) | Pool price averaging, path check ignores FVGs, no OB from a CHoCH leg, MSS window, consolidation double-touch, single-slot identity. |
| P3 | 7 (F20–F26) | Panel shows provisional intrabar signals, alerts ignore the signal toggle, redundant P0-E test, misleading input label, contradictory note, double WARN penalty, CFD auto-killzone. |

Four confirmed defects (F1, F18, F19 and the F2/F3 pair) between them mean that in the shipped default configuration (`CONFIRMED` trigger, `TOUCH` FVG mode) the modules the header calls the highest-quality setups — M36, M37, M41, M42, M45, M46, M54, M68, M73 — either cannot fire in their documented form or fire with a stop inside the wick they are supposed to be protected by.

---

## 2. Phase 1 — Source inventory

### 2.1 Script identity

| Item | Value | Evidence |
|---|---|---|
| Version | `//@version=6` | L1 |
| Type | `indicator("SMC / ICT Suite v8.4.0", "SMC Suite", overlay = true, max_bars_back = 500, max_labels_count = 500, max_lines_count = 500, max_boxes_count = 500)` | L178 |
| Architecture | Layers L0–L7, one pass per bar; all mutable state in `Ctx` (L384) and `Sx` (L517), per-bar feature vector `Feat` (L579) | L109–L112 |
| `request.security` calls | 3: HTF tuple (L2101), daily PDH/PDL (L2206), weekly PWH/PWL (L2207). All read `[1]`-shifted series with `lookahead = barmerge.lookahead_on`. | |
| Alerts | 2 dynamic `alert()` (L3872–3875), 11 `alertcondition()` (L3880–3894) | |
| Drawings | labels FIFO 200 + liquidity labels; lines: struct 100, trade 50, HTF 12, liquidity ≤ 30, major H/L 2, trendlines 2; boxes: FVG 40, zones ≤ 60 | L113–L114, L3592–3601, L3632–3636 |
| Inputs | 10 groups + 5 setup/trade groups; 41 setup toggles (`en_M01`…`en_M73`), 6 filter toggles (`fl_*`), master mode `i_setMode` (L741) resolved by `f_en` (L743) | L728–L931, L2645–L2676, L2909–L2924, L3026–L3040, L3209–L3242 |

### 2.2 Execution order per bar (orchestration L2222–L2304, then features L2317–L2642, setups L2645–L3206, trade engine L3491–L3590, drawing L3603–L3838, alerts L3867–L3894)

1. `ft = Feat.new(...)` fresh feature vector (L2222); `preHigh/preLow/preTrend` snapshot the structure state as the bar opens (L2225–L2231).
2. `cd = f_candle(...)` L0 candle anatomy (L2232 → L960).
3. `f_fvg(...)` L2 FVG creation (confirm-gated) and mitigation (every tick) (L2233 → L1267).
4. `st = f_structure(...)` L1 pivots, BOS/CHoCH/weak/internal, CISD, pullback, move phase (L2236 → L1029). **Not confirm-gated**; relies on Pine rollback.
5. `mv = f_moveStrength(...)` on confirmed BOS/weak/internal bars; `ctx.chochReal` on CHoCH (L2249–L2257).
6. Session flags, Asia range → SESH/SESL (L2270–L2292).
7. `f_liq(...)` L3 liquidity levels, sweep / run resolution (L2294 → L1417).
8. `f_zones(...)` L4 SR / KL / OB / RCB / QM / RJB creation and per-zone maintenance; writes the per-side slots `ft.zb` / `ft.zs` (L2296 → L1657).
9. `f_htf(...)` L5 HTF bias, HTF sweeps, HTF FVG (L2298 → L2107).
10. Gates (`f_gate`, L2303–L2304), PD array (L2317–L2335), arrival strength (L2338–L2356), leg counters, wick sequences, break state (L2359–L2411), event memory, OB 50% alert flag, range, FVG-at-price, armed state machines M41/M45/M46/M48/M52/M54 (L2427–L2538), internal liquidity, trendlines, M71 (L2543–L2642).
11. Setup groups A–I (L2645–L2902), J–R (L2909–L3019), S–AB (L3026–L3206), each bidding into `bL` / `bS` through `f_bid` (L2851).
12. Rejection codes, `f_sig` per side, score adjustments (L3499–L3541).
13. Both-sides conflict, signal gap, identity suppression, state commit on confirmed bar (L3544–L3590).
14. Trade lines, labels, structure lines, HTF lines, panel, legend, alerts, data-window plots.

### 2.3 Feature inventory

| Feature | Implemented? | Where | Verified weakness (finding) |
|---|---|---|---|
| Swing highs / lows | Yes — `ta.pivothigh/low(i_swingLen)` L2197–2198; stored as `ctx.curHigh/curLow` on confirmation L1182–L1193 | `f_structure` | Legitimate `swingLen`-bar confirmation delay. HH/LH and HL/LL typing at L1034, L1037. |
| BOS | Yes — trend-aligned close through `curHigh/curLow` with displacement L1048–L1049, L1095–L1122 | `f_structure` | F4 (weak-break lock), F17 (R2 rule levels). |
| CHoCH | Yes — close through protected swing against the trend, or R2 rule (LH + close through last pivot low) L1086–L1087 | `f_structure` | F17. |
| MSS | Only as the entry-trigger variant `i_entryConfirm == "MSS"` (L854, L2687, L2736). No separate structural MSS event. | main scope | F14 (window default). |
| Internal / weak break | Yes — `internalBullBOS`, `weakBullBOS`, pending promotion L1063–L1081 | `f_structure` | F4. |
| Displacement | Yes — candle gate `dispOk` L2235 and distance gate `dDist` L1089–L1092; move-level `mv.strong` L1330 | | Displacement by `dDist` uses `curHigh` even when `hiBroken` is already true (minor, inside F17 discussion). |
| Liquidity BSL/SSL, EQH/EQL, PDH/PDL, PWH/PWL, SESH/SESL | Yes — `f_addLevel` L1381, `f_liq` L1417, Asia range L2275–L2292 | | F8 (pool averaging), F11 (two-bar sweep). |
| Sweep / run / failed close | Yes — L1452–L1500 | `f_liq` | F11. |
| Sweep qualification | Yes — `qual` L1510, sets `cx.sweptLowBar` only for qualified L1522 | `f_liq` | Per-bar `fv.sweptLow*` flags vs multi-bar trigger → F1. |
| Inducement (IDM) | Yes — `z.idmLvl` / `z.idmSwept` L1876–L1882, L1947–L1953; consumed by M37 L2835 | `f_zones` | F6. |
| Order Block | Yes — on BOS only, L1668–L1779; OB candle selection L1714–L1746; FVG alignment L1747; self-mitigation L1757; HP via qualified sweep L1766–L1767 | `f_zones` | F13 (no OB from a CHoCH leg). |
| Breaker | Yes — OB broken on close → BRK L1900, L1971 | `f_zones` | — |
| Reclaimed block / QM / Rejection block | Yes — L1782–L1819, L1822–L1841 | `f_zones` | — |
| Key level scoring | Yes — L1668–L1700 | `f_zones` | — |
| Propulsion block | Yes — L1931–L1945, L2000–L2015 | `f_zones` | — |
| FVG / mitigation | Yes — `f_fvg` L1267; `TOUCH` / `50%` / `FULL` L1293 | | **F18**: in `TOUCH` mode `ft.atBullFvg/atBearFvg` can never be true. |
| IFVG | **Not implemented.** No inversion logic exists; a mitigated FVG is faded or deleted (L1300–L1309). | — | — |
| HTF bias | Yes — `f_htf` L2107–L2166, S4 rules on HTF candles | | F5 (lock on non-displaced HTF break). |
| HTF FVG | Yes — P1-B L2110–L2115, mitigation L2168–L2173, flag L2174–L2175 | | Only the latest HTF FVG per side is kept. |
| HTF sweep / manipulation / rejection | Yes — L2117–L2120, L2179–L2186 | | F5 blocks sweep detection on a locked swing. |
| Premium / discount, OTE | Yes — L2317–L2335, scored in `f_conf` L3350–L3356 | | — |
| Session / killzone | Yes — L2214–L2219, L2270–L2274; auto-on for forex/cfd L2273 | | F10 (checked on confirm bar), F26. |
| Trend filter / HTF gate | Yes — `f_gate` L2189, `gateTrend` L2302, P1-E continuation block L3504–L3506 | | — |
| Entry trigger state machine | Yes — S11/P0-A/P1-D L2717–L2749 | main scope | F1, F9, F19 (per-bar flags not carried to the confirm bar). |
| Entry price | Yes — `CLOSE` / `CANDLE 50%` / `ZONE EDGE`, M10 `RETEST` / `BOTH` L3392–L3403 | `f_sig` | F7. |
| Stop-loss | Yes — `f_stop` L3366–L3386 | | **F2, F3.** |
| Take-profit / R:R | Yes — `f_nearestOpp` L3250, `f_nearestLiq` L3313, ladder L3456–L3461, geometry gate L3475 | `f_sig` | F12 (path check ignores FVGs). |
| Confluence score | Yes — `f_conf` L3328–L3363; tier × 2 + conf − penalties L3477 | | F19 (arrival terms per-bar). |
| Duplicate suppression | Yes — signal gap L3560–L3569, identity L3571–L3583 | | F16. |
| Rejection reason | Yes — `rejL/rejS` codes 0–8, data window L3915 | | Codes are not shown on the chart; see Phase 5 proposal. |
| Spread / news / volatility filter | **Not implemented.** Only the min-risk-in-ticks floor L3411. | — | See false-signal analysis. |
| Alerts match labels | Yes — same `sigL/sigS` object, both confirm-gated L3872–L3881 | | F21 (`d_sig` not applied to alerts). |

### 2.4 Signal modules (41 toggles, 29 enabled in `Core only` / default)

Default-ON: M01 M02 M05 M08 M09 M10 M15 M33 M36 M37 M39 M40 M41 M42 M45 M46 M51 M54 M58 M62 M64(draw) M68 M69 M70 M72 M73.
Default-OFF: M03 M04 M06 M07 M11 M12 M14 M29 M44 M47 M48 M49 M50 M52 M53 M63 M65.

Pick rank (`f_bid` second argument, tier = rank ÷ 10): tier 4 (rank 43): M37 M41 M42 M45★ M54 M68 M73 · tier 3: M09 M33 M36 M39 M45 M46 M51 M10(PD/PW/SES) · tier 2: M01 M02 M05 M08 M10(pool) M12 M15 M40 M58 M62 M65 M70 M72 · tier 1: the rest. Ties are broken by declaration order (strict `>` at L2852), which the header lists as "STILL OPEN".

---

## 3. Phase 2 — Forensic bug audit

### 3.1 Repainting and future-data leakage

| Check | Result | Evidence |
|---|---|---|
| `request.security` lookahead | **Safe.** All three calls read `[1]`-offset series (`open[1]`, `high[1]`, `ta.pivothigh(...)[1]`, `high[3]`) with `lookahead_on`. This is the documented non-repainting HTF pattern: the value is the last *completed* HTF candle for every LTF bar inside the current HTF candle, identical on historical and realtime bars. | L2101–L2104, L2206–L2207 |
| HTF processing timing | `f_htf` mutates HTF state only when `timeframe.change(htfTF)` is true (L2105, L2108), i.e. on the first LTF bar after the HTF close. No partial-candle reads. | |
| Pivots | `ta.pivothigh/low` confirm `swingLen` bars late; structure consumes the confirmed value. Structure lines are back-anchored to the pivot index (L3741–L3755) — visual back-plotting, not leakage. | L2197, L1182–L1193 |
| FVG | Creation gated on `barstate.isconfirmed` (L1276). Mitigation runs every tick but rollback restores it; final state is the close state. | L1267–L1315 |
| Signals, labels, trade lines, alerts | `sigL/sigS` are rebuilt every tick but every consumer that persists is confirm-gated: state commit L3584, trade lines L3603, labels L3721, structure lines L3741, `alert()` L3872–L3875, `alertcondition` L3880–L3894. | |
| Negative indexing | None found. Largest historical offsets are bounded: `f_legOrigin` ≤ 490 (L998), `f_moveStrength` < 500 (L1341), OB walk `obOff + 1` ≤ 490 (L1733), `pdSpanB` ≤ 491 (L2317). `max_bars_back = 500`. | |
| `var` / `varip` | No `varip`. All persistent objects are `var`; Pine rolls them back per realtime tick, so intrabar flicker does not persist. | |
| Intrabar instability (not leakage) | `f_structure`, `f_liq`, `f_zones` maintenance and the whole candidate chain run on every tick. The **panel** (L3838, `barstate.islast`) and the data-window plots (L3897–L3915) therefore display provisional values that can vanish at the close. This is F20 (P3), not repainting of any persisted object. | |

**Conclusion:** no P0 repainting defect. Historical and realtime signals are produced by the same confirm-gated path.

### 3.2 Market-structure errors

Covered by F4, F5, F17 below. Additional observations that are **not** classified as defects:

- A BOS consumes the swing (`hiBroken := true`, L1059) until the next pivot high confirms. This is correct for a genuine break; the defect is only that *failed* or *expired* weak breaks also consume it (F4).
- The §M1 tie-break (L1053–L1057) prevents a gap bar from registering both a bull and a bear break. Correct.
- The bear-side guard `not s.weakBullBOS and not s.internalBullBOS` (L1111) prevents two events on one bar. Correct.
- `RANGE` after `rangeBarsThresh` (20) bars without a BOS/CHoCH (L1178–L1181) is a design choice, not a bug, but it degrades the trend term of `f_conf` during long pullbacks (see false-signal scenario S6).

### 3.3 Liquidity and institutional-style concepts

Covered by F1, F6, F8, F11, F13, F18. The code never asserts "institutional order flow"; labels say OB, BRK, KL, SWEEP. The HP flag (`z.hp`, L1775) is a sweep-proximity heuristic (L1766–L1767), correctly named "high-probability", not "institutional".

### 3.4 Signal engine and state management

Covered by F1, F7, F9, F10, F15, F16, F19, F20, F21, F24, F25. Verified correct:

- Arm-after-confirm ordering (L2719–L2749): the confirming candle cannot re-arm the same bar.
- One-shot triggers: `poiDirL := 0` on confirm (L2727), M54 latch consumed (L2982–L2985), M58/M62/M69/M72 latches consumed (L3169–L3178), M65 reset (L3113–L3114).
- Both-sides conflict resolved by score (L3550–L3558); gap override needs +2 (L3562–L3569).
- Geometry gate on final numbers (L3475–L3476) prevents wrong-side SL/TP from being shown.
- Array loops that remove elements iterate downward (`for i = n - 1 to 0`) — safe.

### 3.5 Performance and compatibility

- Compilation not verified here. The header records a previous compile at 101,975 tokens over the 100,256 limit, resolved by cutting modules; headroom after the cut is **unknown**. Every proposed fix in the roadmap is sized against that constraint.
- `f_bid` is inlined ~120 times (L2846–L2850); any logic added inside it is paid 120×. All proposed fixes keep `f_bid` untouched.
- Per-bar cost is dominated by the zone maintenance loop (≤ 60 zones, L1849–L2066) and the liquidity loop (≤ 30 levels). Event-only scans (`f_moveStrength`, `f_nearestOpp`, `f_pathBlock`, `f_hiddenInterest`) are bounded. No concern.
- Drawing budgets (L113–L114) are below the 500 caps.

---

## 4. Phase 7 — Findings

Each finding: severity · location · evidence · expected · actual · root cause · reproduction · correction · regression test. Severity scale per the audit brief (P0 leakage / fundamentally invalid signal / severe execution defect; P1 structure, major repaint, broken entry or invalidation; P2 duplicates, stale zones, risk calculation, performance; P3 visual / minor).

### F2 · P0 · Stop-loss ignores the reaction wick (zone slot path)

- **Location:** `f_stop` L3366–L3386, specifically L3371–L3372.
- **Evidence:**
  ```pine
  if zz.kind != ""
      sl := isLong ? zz.bottom - buf : zz.top + buf
  ```
  The state machine's own invalidation is `sx.poiLowL := math.min(low, nz(ft.zb.bottom, low))` (L2737) and the setup is expired when `close < sx.poiLowL - poiBuf` (L2721). `sx.poiLowL` is never read by `f_stop`.
- **Expected:** the stop sits beyond the lowest point price printed while reacting at the POI (reaction candle wick, or the sweep wick for sweep-based modules), plus the buffer.
- **Actual:** the stop sits at the zone bottom minus `0.15 ATR`. When the reaction wick pierced below the zone bottom by more than the buffer, the published SL is **inside** the wick. The engine simultaneously says "setup still valid" (`poiLowL` below SL) and "trade stopped out".
- **Root cause:** `f_stop` predates the S11/P0-A state machine; it reads only the zone geometry and the current bar.
- **Reproduction:** CONFIRMED mode, 5m, any OB tap where the reaction candle's low < `zone.bottom - 0.15·ATR` (common on forex at London open). Confirm bar fires; red dashed SL line is above the reaction candle's low.
- **Correction:** pass a reference low/high into `f_stop` (two call sites, L3404 and L3437) and take `math.min(zz.bottom, refLo) - buf`; see roadmap step 1.
- **Regression test:** synthetic sequence [tap candle with low = zone.bottom − 0.5·ATR, confirm candle close > tap high] → SL must be ≤ tap low − buf. Assert `sl < low[k]` for the tap bar.

### F3 · P0 · Stop-loss on an FVG-only tap uses the confirm candle's low

- **Location:** `f_stop` L3373–L3382; `reactBull` L2928; `sx.poiFvgL` L2739.
- **Evidence:** for an FVG-only arm (`ft.zb.kind == ""`) the zone branch is skipped; without a same-bar sweep the stop falls to `majorLow` (if within `maxA` ATR) or `low - buf` where `low` is the **confirm** bar's low (L3381), which is above the reaction low by construction (price already moved up).
- **Expected:** stop beyond the reaction low (`sx.poiLowL`).
- **Actual:** stop a few ticks under the confirm candle; routinely hit by the first pullback.
- **Root cause:** same as F2.
- **Note:** under the default `TOUCH` FVG mode this path is unreachable because of F18. It becomes live as soon as the FVG mode is `50%` or `FULL`, or after F18 is fixed. Fixing F2 fixes F3 (same reference value).
- **Regression test:** FVG mode `50%`, FVG-only arm, confirm 3 bars later with a higher low → SL must be ≤ reaction low − buf.

### F1 · P1 · "Sweep-required" zones are untradable in CONFIRMED / MSS mode

- **Location:** `zoneOkBull/zoneOkBear` L2706–L2707; `f_conf` L3346; sweep flags written per bar at L1519–L1524.
- **Evidence:**
  ```pine
  zoneOkBull = atBullZone and zMidB and (not fl_SwR or not ft.zb.sweepReq or ft.sweptLow) and ...
  ```
  `ft.sweptLow` is true only on the bar where `f_liq` resolves a level. On the confirm bar (1–8 bars later) it is false; the snapshot `sx.poiZb.sweepReq` is still true (zone touched ≥ 2×, L1926). `zoneOkBull` → false → every `zoneOkBull and trigBull` module (M08 M09 M12 M33 M36 M37 M39 M40 M42 M45 M48 M51 M54 M70) is false on the only bar `trigBull` can be true. Reject code reads 1 (no candidate). `f_conf` additionally docks −2 (L3346) because the same per-bar flag is false.
- **Expected:** a sweep within the arm window satisfies the §6.2 rule on the confirm bar.
- **Actual:** the §6.2 "sweep then reversal at a revisited zone" setup is impossible in the default mode; it worked in IMMEDIATE mode (v8.3).
- **Root cause:** per-bar flag consumed by a multi-bar trigger.
- **Reproduction:** zone with `touches ≥ 2`; sweep candle = reversal candle (arms); next bar closes above the reaction high → no signal; data window reject code 1x.
- **Correction:** windowed sweep flag (`bar_index - ctx.sweptLowBar <= N or bar_index - ctx.intSwpBull <= N`), stored in `Feat`, used by `zoneOkBull` and `f_conf`. Roadmap step 2.
- **Regression test:** the reproduction above must emit the signal with no −2 penalty; IMMEDIATE mode behaviour unchanged.

### F19 · P1 · Arrival-strength flags are per-bar; M33 / M36 / M42 cannot fire once price has left the zone

- **Location:** `zoneTouch` L2338; `ft.arrivalWeak/arrivalStrong` L2350–L2353; consumers `s33` L2827, `s36` L2833, `s42` L2942, `arrOkBull` L2708, `pbOk` L2710, `f_conf` L3341, L3345; slot restore L2689–L2696.
- **Evidence:** `zoneTouch` is computed from the **live** slot before the snapshot restore. `ft.arrivalWeak` is assigned only inside `if zoneTouch and ...` (L2350). On the confirm bar, if the confirm candle's low is above the zone top, `zoneTouch` is false and both arrival flags stay false.
- **Expected:** the arrival verdict measured when price *arrived* at the POI is what qualifies the trade; it should be part of the snapshot.
- **Actual:** M42 (rank 43, "weak arrival" is one of its five criteria), M36 and M33 fire only when the confirm candle still overlaps the zone — a selection bias toward shallow, overlapping confirmations. At the same time, the M19 strong-arrival suppression (`arrOkBull`) and the −2 `arrivalStrong` penalty are silently disabled on every confirm bar, for every module.
- **Root cause:** same class as F1.
- **Reproduction:** OB tap, pin bar whose high is above the zone top, next candle gaps up and closes above the pin high with its low above the zone top → `s42` false although depStrong, fifty and the confirm are all satisfied.
- **Correction:** add `arrivalWeak/arrivalStrong/arrivalMixed` to the `ZS` snapshot (or to `Sx` at arm time) and read the snapshot on the confirm bar. Roadmap step 2.
- **Regression test:** the reproduction above must emit M42; a strong-arrival tap must still be blocked by M19 on the confirm bar.

### F18 · P1 · `ft.atBullFvg` / `ft.atBearFvg` can never be true in the default `TOUCH` FVG mode

- **Location:** `f_fvg` mitigation L1291–L1296 (runs first, L2233); FVG-at-price scan L2455–L2463.
- **Evidence:**
  ```pine
  // f_fvg, every tick
  lvl = cf.fvgMitMode == "TOUCH" ? (g.isBull ? g.top : g.bottom) : ...
  hit = g.isBull ? low <= lvl : high >= lvl
  if hit: g.mitigated := true
  // later, same bar
  if not g.mitigated and g.idx < bar_index - 1
      if g.isBull and low <= g.top and high >= g.bottom: ft.atBullFvg := true
  ```
  Any bar with `low <= g.top` has already set `g.mitigated` before the scan; the scan's `not g.mitigated and low <= g.top` is therefore unsatisfiable. In `50%` mode the flag is true only for `low ∈ (mid, top]`; in `FULL` mode for `low ∈ (bottom, top]`.
- **Expected:** price trading inside an unmitigated FVG is a reaction zone (comment at L2454: "reaction zone for M46/M50/M52").
- **Actual (default config):** `reactBull` reduces to `zoneOkBull`; `sx.poiFvgL` is never true; the FVG-only entry path of M41, M46, M49, M50, M52, M68 is dead; the `f_conf` zone-over-FVG point (L3339) is never earned; the 4-factor INCOMPLETE test (L3517) never passes via FVG. M41's label "Sweep + FVG confluence … retrace reversal" describes a path that does not exist; the M41 signals that do appear are zone-only.
- **Root cause:** mitigation-on-touch and at-price are the same predicate.
- **Reproduction:** default settings, any unmitigated bull FVG, any bar whose low enters it → data window / debug plot of `ft.atBullFvg` is 0. (The variable is not plotted today; add a temporary plot to verify.)
- **Correction:** evaluate "at FVG" against the pre-mitigation state: either run the at-price scan before `f_fvg`, or in `f_fvg` set a `fv.atBullFvg := true` on the bar that mitigates (`hit` branch) when `g.idx < bar_index - 1`. Roadmap step 3. (Operator workaround: set FVG mitigation to `50%`.)
- **Regression test:** with TOUCH mode, bar entering an FVG → `ft.atBullFvg` true on that bar; a later bar fully through the FVG → false.

### F4 · P1 · Expired or failed weak break leaves `hiBroken` / `loBroken` latched

- **Location:** L1059, L1061 (set), L1066–L1067 (expiry clears only `stPendDir`), L1039–L1047 (failed follow-through clears only `stBrkDir`).
- **Expected:** a break that was never promoted (or that failed) should release the swing so the next displaced close through it registers as a BOS.
- **Actual:** `hiBroken` stays true until the next pivot high confirms (≥ `swingLen × 2` bars). A displaced close through the same swing in that window produces no BOS (`brkUp` false at L1048), no `dispBull`, no `mv` update, and **no OB** (OB creation is BOS-only, L1668). Modules M36 M37 M42 M51 have nothing to trade on that leg.
- **Reproduction:** small-body close 1 tick above `curHigh` (weak), 3 quiet bars (expire), then a large displacement candle through the same level → no BOS label, no OB box.
- **Correction:** clear the matching `hiBroken/loBroken` in the expiry branch and in the failed-follow-through branch. Roadmap step 4.
- **Regression test:** the reproduction must produce BOS▲ on the displacement candle and an OB at the leg origin.

### F5 · P1 · HTF bias locks on a non-displaced HTF break

- **Location:** `f_htf` L2125–L2130 (break consumes the swing), L2142 (bias changes only `if dispH`).
- **Expected:** a non-displaced HTF close through a swing is pending, as on the LTF (S4), and is promoted or released.
- **Actual:** the swing is consumed (`hHiBroken := true`) but the bias does not change; the next HTF close through the same swing cannot register (`bBrk` false) until a new HTF pivot forms — on a 5m/1h pairing, `i_htfSwing × 2 = 6` HTF candles ≈ 72 LTF bars. `f_gate`, the `f_conf` HTF point, P1-E, M48, M68 (`htfSweepUp/Dn` also blocked by the same flag at L2117–L2120) all read a stale bias.
- **Reproduction:** 1h candle closes above the last HTF swing high with body < 50 % of range → background tint and panel bias unchanged; subsequent 1h displaced close above the same high changes nothing.
- **Correction:** add `Sx.hPend` (±1) and promote on the next HTF close in the same direction; only a displaced or promoted break consumes the swing. Roadmap step 6.
- **Regression test:** HTF sequence [weak break up, displaced close up] → bias BULL after the second candle.

### F17 · P1 · R2 CHoCH rule (LH + close through last pivot low) uses the protected swing as its level

- **Location:** `chDn` L1087 (trigger uses `curLow`), weak path `f_pend(sx, -1, 2, cx.majorLow, cx.majorLowIdx)` L1117, failure-counter level `sx.stBrkLvl := s.bearCHoCH ? cx.majorLow : cx.curLow` L1154, event line `f_evLine(lns, ctx.majorLowIdx, ctx.majorLow, ...)` L3752–L3753. Mirror: L1086, L1101, L1137, L3750–L3751.
- **Evidence:** the R2 rule fires on `brkDn and sx.hiType == "LH"` — the broken level is `curLow`, which in a bull trend sits **above** `majorLow`. Three consumers then read `majorLow`:
  1. Non-displaced case → pending at `majorLow`; promotion requires `close < majorLow` within 3 bars → effectively never; the pending expires and `loBroken` stays latched (F4). A legitimate non-displaced R2 CHoCH that gets a follow-through close below `curLow` is lost.
  2. Displaced case → `stBrkLvl = majorLow`; on the next bar `close > majorLow` is true (price only broke `curLow`) → the failed-follow-through counter increments immediately (L1041–L1043) and `stBrkDir` is cleared. Every R2-rule CHoCH therefore starts the next leg with `stFail = 1`, so a single later weak-break failure sends the trend to `RANGE` (`failMax = 2`).
  3. Event line drawn at `majorLow`, not at the level that was actually broken.
- **Expected:** level = `curLow` (`curHigh` for the mirror) for all three consumers when the CHoCH came from the R2 rule.
- **Correction:** compute `chLvlDn = close < majorLow ? majorLow : curLow` once in `f_structure` and use it at L1117, L1154 and (via a new `Sx` float) at L3752. Roadmap step 5.
- **Regression test:** bull trend, LH pivot, non-displaced close below `curLow`, displaced close below `curLow` two bars later → CHoCH▼ on the second close; `stFail` must be 0 on the bar after a displaced R2 CHoCH.

### F6 · P1 · M37 inducement sweep not credited when the sweep candle also taps the OB

- **Location:** L1880 `low < z.idmLvl and low > z.top` (mirror L1951).
- **Actual:** a candle that takes the inducement low **and** enters the OB in one move (textbook ICT form; on 5m the IDM low and OB top are often a few pips apart) does not set `idmSwept`; M37 (rank 43) stays silent in its most common form.
- **Correction:** drop `and low > z.top` / `and high < z.bottom` (`idmLvl` is above the zone by construction, L1878). Roadmap step 4.
- **Regression test:** one candle with low below IDM and inside OB → zone text shows `IDM✓`.

### F7 · P1 · `ZONE EDGE` / `CANDLE 50%` limit entry can sit on the wrong side of the close

- **Location:** `f_sig` L3395–L3399.
- **Evidence:** with `i_zClose = "50%"` the confirm close may be between the zone midpoint and the zone top (L2704); `g.entry := zzE.top` is then **above** the close for a long. The label says `LIMIT @ zone edge`, the alert carries that price, and `f_stop` / R:R are computed from it.
- **Actual:** a "limit" that is really a stop-entry at a worse price than market; an operator placing the limit as instructed is not filled, or is filled worse than the close.
- **Correction:** `g.entry := isLong ? math.min(close, zzE.top) : math.max(close, zzE.bottom)`; same clamp for the candle-50 % path. Roadmap step 4.
- **Regression test:** confirm close inside the upper half of the zone, ZONE EDGE mode → entry == close.

### F9 · P1 · P0-B "close beyond 50 %" rule applied on the arm bar

- **Location:** `zMidB` L2704 inside `zoneOkBull` L2706, used by the arm condition L2732.
- **Actual:** a deep pin bar that closes inside the zone cannot arm in CONFIRMED/MSS mode, although the whole point of CONFIRMED is that the *confirm* close provides the proof. P0-B was written for IMMEDIATE.
- **Correction:** separate `zoneArmB` (no `zMidB`) for arming from `zoneOkBull` (with `zMidB`) for the confirm bar. Roadmap step 7.

### F10 · P1 · Killzone checked on the confirm bar, not the arm bar

- **Location:** `rejL` L3506 `not ft.sbSessOk ? 3`.
- **Actual:** tap at 04:50 NY inside London, confirm at 05:05 → reject 3. The MSS window makes it worse.
- **Correction:** store `sx.poiSessL := ft.sbSessOk` at arm; accept `ft.sbSessOk or (poiConfL and sx.poiSessL)`. Roadmap step 7.

### F11 · P1 · Two-bar sweep classifies on the wrong candle

- **Location:** `f_liq` L1472, L1490 (`L.pend := failedCloseBars`), resolution on the later bar L1455–L1460; consumer `s10` L2796 (`cd.dnWickRatio`), `f_stop` L3374 (`low - buf`).
- **Actual:** close beyond the level without a RUN → pending; a close back within 2 bars → `SWEEP` flagged on **that** bar. M10's wick test and SL read the second bar, not the candle that actually swept.
- **Correction:** wick test `math.max(cd.dnWickRatio, ctx.dnR2)` — at the point `s10` is evaluated `ctx.dnR1` already holds this bar's ratio (updated at L2385), so the previous bar is `ctx.dnR2`; SL reference `math.min(low, low[1], low[2])` (shared with F2). Roadmap step 1.

### F8 · P2 · EQH / EQL pool price is averaged

- **Location:** `f_addLevel` L1394.
- **Actual:** stops rest above the *higher* of the two highs; a wick through the average but not the higher high is classified as a qualified sweep (`sweptHighQ`) and arms M10 / M41 / M45 / CISD on an incomplete sweep.
- **Correction:** `L.price := isHigh ? math.max(L.price, price) : math.min(L.price, price)`.

### F12 · P2 · `f_pathBlock` scans zones only

- **Location:** L3296–L3310; comment at L3291 says "zone or FVG".
- **Actual:** an unmitigated opposing FVG between entry and TP1 does not block. With `i_tpPath = STRICT` default, this is a gap in the gate.
- **Correction:** add the FVG loop (mirror of L3266–L3275) with `hit := true`.

### F13 · P2 · No order block from a CHoCH leg

- **Location:** L1668 `if (bullBOS or bearBOS)`.
- **Actual:** the sweep → CHoCH leg (the ICT reversal entry) produces only an RCB (L1782–L1803), and only if `rcbFibGate` passes. M45 wants BRK/OB; M68 wants zone/FVG.
- **Correction:** `(bullBOS or bearBOS or bullCHoCH or bearCHoCH)` with `isBull = bullBOS or bullCHoCH`; `oIdxIn = ctx.legIdx` is already correct on CHoCH bars (L1128–L1130).

### F14 · P2 · MSS window default contradicts its tooltip

- **Location:** L854–L856. Tooltip: "For MSS set the window to ~12"; default 8 for all modes.
- **Correction:** `poiWin = mssMode ? math.max(i_poiBars, 12) : i_poiBars` at L2721 / L2723.

### F15 · P2 · Consolidation inside a zone counts a second touch

- **Location:** L1923–L1926, L1994–L1997.
- **Actual:** price sitting inside the zone for `touchCooldown + 1` bars increments `touches` → `sweepReq` on the same visit. In CONFIRMED mode the live slot (not the snapshot) is used while price is still inside, so `zoneOkBull` turns false mid-visit.
- **Correction:** count a touch only on re-entry (`low[1] > z.top` for bull, `high[1] < z.bottom` for bear).

### F16 · P2 · Identity suppression has one slot for both sides

- **Location:** L3571–L3583, L3589.
- **Actual:** L signal → S signal → same L setup inside 50 bars is not suppressed.
- **Correction:** `lastIdentL/lastIdentS` with their own bar stamps.

### F20 · P3 · Panel and data window display provisional intrabar signals

- **Location:** `f_panel` called on `barstate.islast` (L3838) with the tick-level `sigL/sigS`; plots L3897–L3898, L3915.
- **Actual:** the "Signal" row and the score plots can show a candidate that disappears at the close. Labels/alerts are unaffected.
- **Correction:** feed the panel the last *committed* signal (store it at L3584), or annotate the row "provisional" while `not barstate.isconfirmed`.

### F21 · P3 · `d_sig` hides labels but not alerts

- **Location:** L3681/L3695 use `d_sig and hasL`; L3872–L3881 use `hasL` only.
- **Correction:** gate the four signal alerts on `d_sig` as well, or document the behaviour.

### F22 · P3 · P0-E close-position test is redundant

- **Location:** `s10` L2796 `close >= (high + low) * 0.5`.
- **Evidence:** `cd.dnWickRatio >= 0.5` ⇒ `min(open, close) − low ≥ 0.5·range` ⇒ `close ≥ low + 0.5·range`. The added test is implied. If a stricter rejection is wanted, use `close >= low + 0.6 * cd.rng` or `cd.isBull`.

### F23 · P3 · "Max SL distance" input is applied at 2×

- **Location:** L3211 label "Max SL distance × ATR"; `f_stop` L3383 tests `ep - sl > aV * maxA * 2`.
- **Correction:** rename the input or drop the `* 2`.

### F24 · P3 · R:R fallback leaves a contradictory note

- **Location:** L3434–L3437: `g.note` already contains "LIMIT @ … · " and then receives "R:R fallback → IMMEDIATE entry · ". The min-risk floor (L3411–L3414) is also not re-applied on this path.
- **Correction:** reset `g.note := ""` before appending; re-apply the floor.

### F25 · P3 (design) · WARN gate costs two points

- **Location:** L3511–L3512 (−1 for `gateUp == 1`) and L3517–L3519 (INCOMPLETE −1 when `gateUp != 2`).
- **Observation:** a WARN signal is penalised twice. Not a defect if intended; the header describes only the −1. Document or merge.

### F26 · P3 · Killzone auto-on keys on `syminfo.type == "cfd"`

- **Location:** L2273.
- **Observation:** crypto or index CFDs on some brokers report `cfd`, so the filter engages on instruments that trade through the Asia window. Hypothesis until checked on the user's broker; mitigation is the existing `i_ssnFx` toggle.

---

## 5. Hypotheses (not confirmed defects)

| ID | Statement | Evidence needed |
|---|---|---|
| H1 | Tier-4 ties (rank 43: M37 M41 M42 M54 M68 M73) are settled by declaration order, so M37 always wins a same-bar tie. | Count of same-bar tier-4 collisions in replay; the header already lists this as open. |
| H2 | `RANGE` after 20 bars without BOS/CHoCH (L1178–L1181) flips the `f_conf` trend term to −1 during ordinary trend pullbacks on 5m, lowering scores exactly where continuation entries are sought. | Distribution of `st.trend` inside HTF-aligned legs on replay. |
| H3 | Tapped zones never age out (L2061 applies only to untapped zones); after ~500 bars a chart carries stale OBs that still fill the slot. | Zone age histogram at `barstate.islast`. |
| H4 | `ft.zb.fifty` is latched for the zone's life (L1921), so the 50 % rule can be satisfied by a previous visit. | Trace of `fiftyHit` vs visit index. |

---

## 6. Verified-correct items (do not change)

- All three `request.security` calls: `[1]` + `lookahead_on` (L2101–L2104, L2206–L2207).
- Confirm gating of FVG creation, OB/RCB/QM/RJB creation, labels, trade lines, structure lines, `alert()` and every `alertcondition`.
- Arm-after-confirm order in the POI state machine (L2731 comment and L2732/L2740 placement).
- Geometry gate (L3475–L3476), TP ladder (L3456–L3461), REAL/SYNTH/FIXED-R provenance (L3449–L3455).
- P1-E continuation block (L3504–L3506), R2 counter-trend −1 (L3334), M10 fresh-displacement no-fade (L2793–L2797).
- Min-risk floor in ticks (L3411–L3414).
- Downward iteration with `array.remove` in every maintenance loop.

---

## 7. Answers to the five questions in the brief

1. **What is implemented?** §2.3. Not implemented: IFVG, spread/news/volatility filter, a structural MSS event (MSS exists only as a trigger variant), an on-chart rejection reason.
2. **Where are the bugs?** §4: 2 × P0, 11 × P1, 6 × P2, 7 × P3, all with line evidence.
3. **How does an entry become valid?** `SMC_ENTRY_FOOTPRINT_ANALYSIS.md`.
4. **What stops a weak setup?** Tier + `f_conf` ≥ 8, HTF/trend gate, killzone, R:R ≥ 2 to a REAL target with a clear path, geometry gate, gap and identity suppression. What does **not** stop it: arrival strength on a confirm bar (F19), a sweep rule that cannot be satisfied (F1), a stop that is inside the wick (F2).
5. **Minimal testable changes?** `SMC_IMPROVEMENT_ROADMAP.md` — nine stages, each one compile, each with an acceptance test in `SMC_VALIDATION_TEST_PLAN.md`.
