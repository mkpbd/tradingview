# SMC v8.4.0 — Entry Footprint Analysis

Source: `SMC_v8.4.0.txt`. Companion to `SMC_v8.4.0_FORENSIC_AUDIT.md` (finding IDs F1–F26 are defined there). Line numbers refer to the shipped file.

This document answers one question per pathway: **what exactly has to be true, in what order, for a BUY or SELL label to appear, and what is missing.** The long side is traced; the short side is the mirror unless a difference is noted.

---

## 1. Shared pipeline (every module passes through this)

```
candidate (s##) ──f_bid──► bL.n/bL.s ──rejL gate──► f_sig ──score──► conflict / gap / identity ──► label · lines · alert
```

| Stage | Where | Condition | Reject code (data window) |
|---|---|---|---|
| Candidate | L2861–L2882, L2988–L3002, L3187–L3195 | `s##` true and rank > current best (strict `>`, L2852) | 1 if none |
| HTF / PD gate | L3506 | `ft.gateUp != 0`; WARN (1) also blocks continuation modules M02 M05 M08 M15 M33 M36 M42 M51 M73 (L3504) | 2 |
| Killzone | L3506 | `ft.sbSessOk` (L2274) — forced on for forex/cfd (L2273) | 3 |
| Trade geometry | `f_sig` L3388–L3484 | entry → SL → risk floor → TP1 (REAL within [minRR, maxRR], L3429) → path clear (STRICT, L3464) → SL/TP on the right side and R:R ≥ minRR (L3475) | 4 |
| Score | L3477, L3511–L3523 | `tier × 2 + f_conf − pathPen − (WARN ? 1 : 0) − (INCOMPLETE ? 1 : 0) ≥ i_minScore (8)` | 5 |
| Both sides | L3550–L3558 | higher score wins | 6 |
| Gap | L3560–L3569 | ≥ 5 bars since last signal unless opposite side with +2 | 7 |
| Identity | L3571–L3583 | module + side + POI midpoint (or swept price) not repeated within 50 bars | 8 |
| Commit | L3584–L3590 | `barstate.isconfirmed` | 0 |

**Timing:** every label, line and alert is confirm-gated, so **every signal in this build is a candle-close signal.** There is no intrabar entry. The panel is the only surface that shows provisional state (F20).

**Entry price** (`f_sig` L3392–L3403): `CLOSE` (default) = confirm candle close; `CANDLE 50%`; `ZONE EDGE` (F7); M10 `RETEST`/`BOTH` = swept level.
**Stop** (`f_stop` L3366–L3386): own-side zone edge ± 0.15 ATR → else sweep bar extreme → else `majorLow/High` if within 2 ATR → else confirm candle extreme. Sanity: wrong side or > 4 ATR → confirm candle extreme. Floor: 20 ticks (L3411).
**Targets:** TP1 = nearest qualified opposing zone / unmitigated FVG / qualified liquidity in [2R, 6R] (L3250); TP2/TP3 = next liquidity ≥ 1R further (L3456–L3461).
**Invalidation published to the user:** the SL line. The engine's internal invalidation (`sx.poiLowL`, L2737) is not published and differs from the SL (F2).

---

## 2. Pathway A — Zone reversal family (default `CONFIRMED` trigger)

Modules: M08 M09 M12 M33 M36 M37 M39 M40 M42 M45 M48 M51 M54 M70 M73 and, through `reactBull`, M41 M46 M49 M50 M52 M68.
This is the pathway that carries every tier-4 module except none — all six rank-43 modules (M37 M41 M42 M54 M68 M73) live here.

### 2.1 Required sequence as implemented

| Step | Model step (brief §4) | Code | Status in v8.4.0 |
|---|---|---|---|
| 1 | HTF context | `ft.htfBias` from `f_htf` (L2107); gate L3506; `f_conf` +1/−0 (L3332) | Implemented. **F5**: bias can be stale after a non-displaced HTF break. HTF **POI** (HTF OB) is not modelled; only the latest HTF FVG (P1-B). |
| 2 | Liquidity event | `fv.sweptLowQ` (qualified: pool / PD / PW / SES, L1510) or internal sweep; `z.idmSwept` for M37 | Implemented per bar only. **F1**: the flag is false on the confirm bar; **F6**: same-candle IDM sweep + tap not credited; **F8**: pool price averaged; **F11**: two-bar sweep read on the wrong candle. |
| 3 | Displacement | `mv.strong` at the BOS that created the OB (`z.depStrong`, L1774); `ft.dispBull`; M41 requires `mv.strong` after the sweep (L2496–L2498) | Implemented at zone-creation time. **F4**: a weak break can suppress the BOS that would have created the OB. |
| 4 | Structure confirmation | BOS/CHoCH at L1095–L1160; modules M45 (sweep → BOS/CHoCH, L2476–L2491), M54 (demand → sweep → BOS, L2527–L2538), M68 (HTF sweep + LTF CHoCH, L3117–L3122) | Implemented. **F17** for R2-rule CHoCHs. |
| 5 | Entry zone | Per-side slot `ft.zb` written by `f_zones` (L2027–L2050): OB 6 > BRK 5 > RCB/QM 4 > RJB 3 > KL 2 > SR 1, +3 PROP; FVG via `ft.atBullFvg` | Implemented. **F18**: the FVG slot is dead in TOUCH mode. **F13**: no OB from a CHoCH leg. |
| 6 | Mitigation | `touchedNow` (L1916), `fiftyHit` (L1921), `sweepReq` after 2 touches (L1926), broken on close through the far edge (L1888) | Implemented. **F15**: consolidation inside counts a second touch; **H3**: tapped zones never expire; **H4**: `fifty` latched. |
| 7a | Reaction (arm) | `revBull` (pin / engulf / IFC / manip, L2678) **and** `zoneOkBull` (L2706: at zone, close ≥ zone 50 %, sweep rule, 50 % rule) → `sx.poiDirL := 1`, snapshot `sx.poiZb`, `poiRefL = high` (MSS: max of last 5 highs), `poiLowL = min(low, zone.bottom)` (L2732–L2739) | Implemented. **F9**: 50 %-close rule applied to the reaction candle. |
| 7b | Trigger (confirm) | within `i_poiBars` (8): `close > poiRefL` **or** a new bull FVG (L2725); expired by window or `close < poiLowL − 0.15 ATR` (L2721) | Implemented, one-shot (L2727). **F14**: MSS window default. |
| 7c | Module predicate on the confirm bar | e.g. `s42 = zoneOkBull and kind == OB and depStrong and fifty and arrivalWeak and trigBull` (L2942) | **F1** (`zoneOkBull` false for sweepReq zones), **F19** (`arrivalWeak` false once price left the zone), **F10** (killzone tested here). |
| 8 | Invalidation | SL line from `f_stop` | **F2 / F3**: SL at zone edge / confirm-bar low, not at the reaction extreme. |
| 9 | R:R | `f_sig` L3404–L3476 | Implemented. **F12** path check ignores FVGs; **F7** entry side. |
| 10 | Timing | confirm-bar close | Correct. |

### 2.2 Footprint report — M42 "High-probability S&D" (representative tier-4 zone module)

| Item | Value |
|---|---|
| Source | `s42` L2942; bid L2991 (rank 43); continuation list L3504 |
| Original condition | `en_M42 and zoneOkBull and ft.zb.kind == "OB" and ft.zb.depStrong and ft.zb.fifty and ft.arrivalWeak and trigBull` |
| Preceding events | displaced BOS → OB created with `depStrong` (L1774); price returns, taps the 50 % (L1921); arrival leg measured weak (L2342–L2348); reversal candle at the OB arms the state machine; confirm close through the reaction high |
| Confirmation | `trigBull = poiConfL` (L2748) |
| Entry | confirm close (default) |
| SL | OB bottom − 0.15 ATR (F2) |
| TP | nearest qualified opposing level in [2R, 6R], path clear |
| State | confirmed at close; provisional only in the panel |
| Why a false signal can occur | (a) arrival flag absent, so a strong-arrival tap is not blocked (F19 inverse); (b) SL inside the reaction wick (F2); (c) OB never created after a weak-break lock, so the signal fires off an older, lower-quality zone (F4); (d) `fifty` latched from a previous visit (H4) |
| Missing conditions | arrival verdict in the snapshot; sweep-window flag; reaction low in the stop |
| Contradictory filters | P1-E blocks M42 on WARN although M42 is a reversal-at-POI module that the gate's WARN tier was designed to keep (design question, not a defect) |
| Proposed correction | Roadmap steps 1–2; expected effect: M42 fires on confirm bars whose candle has left the zone, with the stop under the reaction low; strong-arrival taps are blocked again |

### 2.3 Footprint report — M37 "Inducement block"

| Item | Value |
|---|---|
| Source | `s37` L2835; bid L2882 (rank 43, first declared → wins every tier-4 tie) |
| Condition | `obBull (zoneOkBull and OB/BRK) and ft.zb.idm and trigBull` |
| Preceding events | OB; a pivot low above the OB registered as `idmLvl` (L1878); a candle takes that low **without** entering the zone (L1880, F6); then a tap + reversal + confirm |
| Entry / SL / TP | as pathway A |
| False-signal risk | the IDM level is the lowest pivot above the zone, which may be hundreds of bars old; no recency test on `idmLvl` |
| Missing | same-candle sweep+tap (F6); recency of the inducement |
| Correction | drop `low > z.top` (F6); consider `bar_index - idmBar <= N` (new field, optional) |

### 2.4 Footprint report — M41 "Sweep + FVG confluence"

| Item | Value |
|---|---|
| Source | arm L2496–L2498 (`st.bullBOS` within 20 bars of a qualified low sweep, `mv.strong` → dir 1 else 9 = no-trade); `s41` L2938 `armed(1,…) and reactBull and trigBull` |
| Documented model | sweep → displacement leaving an FVG → retrace **into the FVG** → reversal |
| Actual model | `reactBull = zoneOkBull or ft.atBullFvg or (poiConfL and sx.poiFvgL)` (L2928). Under default TOUCH mode `ft.atBullFvg` is never true (F18), so M41 fires only when the retrace lands on a **zone**. The FVG retrace path does not exist in the shipped defaults. |
| SL on the FVG path (once live) | confirm-bar low (F3) |
| Correction | F18 then F2/F3; label text should say which POI was used |

### 2.5 Footprint report — M68 "HTF sweep → LTF entry"

| Item | Value |
|---|---|
| Source | arm L3117–L3122 (`ft.htfSweepDn and st.bullCHoCH`); `s68` L3161 |
| HTF sweep flag | `cx.hBarCount - cx.sweepDnAt < 3` (L2178); the sweep itself requires `not cx.hLoBroken` (L2119) — **F5** can hide it |
| LTF CHoCH | `st.bullCHoCH` — **F17** if it came from the R2 rule and was non-displaced |
| Reaction | `reactBull` — FVG path dead (F18) |
| SL | zone edge or confirm-bar low (F2/F3) — the bid text promises "SL beyond FVG" (L3191), which the code does not do |

### 2.6 Footprint report — M73 "Propulsion block"

| Item | Value |
|---|---|
| Source | zone re-arm L1931–L1945; `s73` L3183 `ft.zb.prop and ft.atDemand and ft.zb.fifty and trigBull` |
| Note | deliberately bypasses `zoneOkBull` (comment L3180–L3182), so **F1 does not apply**; but it also bypasses `zMidB` and `fl_SwR` entirely. `trigBull` still requires the arm, and the arm requires `zoneOkBull or ft.atBullFvg` (L2732) — so a PROP zone with `sweepReq` **cannot arm** in CONFIRMED mode. The bypass at L3183 is therefore ineffective in the default mode. This is a sub-case of F1. |

---

## 3. Pathway B — M10 liquidity sweep reversal (IMMEDIATE, independent of the trigger input)

| Item | Value |
|---|---|
| Source | `s10` L2796; bid L2874 (rank 31 for PD/PW/SES, 21 for pool) |
| Condition | `not freshDispDn and (sweptLowQ or (sweptLow and zone slot filled)) and dnWickRatio ≥ 0.5 and close > sweptPriceLo and close ≥ candle midpoint` |
| Preceding events | a qualified (or in-zone) low swept and resolved on this bar (L1455–L1460, L1510–L1524) |
| Confirmation | none beyond the sweep candle's own close (one-bar) |
| Entry | close; `RETEST` / `BOTH` → limit at the swept level (L3400–L3403), falling back to close when no target exists (L3434) |
| SL | zone bottom if a zone is touched, else sweep-bar low − 0.15 ATR (L3371–L3374) |
| False-signal risk | (a) two-bar sweep reads the wrong candle (F11); (b) pool price averaged → incomplete sweep counts (F8); (c) no structure shift required — the "sweep without MSS" scenario is allowed by design and is mitigated only by score (tier 2 for a pool needs 4 confluence points) and `freshDisp` no-fade; (d) the `close ≥ midpoint` test is redundant (F22) |
| Missing | optional structure confirmation (an MSS within N bars after the sweep) as a **separate, configurable** step — see Phase 5 engine |

---

## 4. Pathway C — Break / trap family (one-bar, no POI state machine)

Modules: M01 M02 M05 M14 M15 (break continuation / rejection), M03 M11 (own two-bar confirm), M29, M47, M53, M62 M63 M65 M69 M72 (own latch + confirm).

| Item | Value |
|---|---|
| Source | break state L2388–L2411 (`ft.breakUp`, `ctx.breakLvl`, `breakAgo`, `brkInternal`); M01/M02 L2753–L2756; M05 L2774; M15 L2818; M62 L3058–L3062, L3155; M69 L3125–L3135, L3163; M72 L3139–L3150, L3168 |
| Common precondition | a level break: structural BOS / weak / internal (`st.*`) **or** a liquidity RUN (`ft.runUp`); `contBrk` excludes internal breaks for continuation modules (R2) |
| Confirmation | the candle itself (M05 M15), a wick sequence + candle (M01 M02, with `brkTouches ≥ 2`), or a latch consumed by a close through a reference (M62 M69 M72) |
| Entry zone | none (M01 M02 M05 M15 M62 M72) → `INCOMPLETE −1` unless a trendline or zone happens to be at price (L3517) |
| SL | sweep low if a sweep coincided, else `majorLow` if within 2 ATR, else candle low − buffer |
| False-signal risk | candle-only modules at tier 2 reach the minimum score with 4 confluence points (HTF + trend + session + liquidity target is enough); no displacement requirement on the break for M05 / M15 when the break was a RUN |
| Status | behaves as documented; quality concerns only (false-signal doc S2, S3) |

---

## 5. Pathway D — Armed multi-step machines (M41 M45 M46 M48 M52 M54 M58 M68)

All arm on a structural event, stay armed `cfg.armBars` (30) bars (L2925–L2927), and need `reactBull and trigBull` (or `zoneOkBull and trigBull`) to fire; M58 fires on its own neckline close (L3154). Each inherits pathway A's confirm-bar defects (F1, F2, F19, F18). M54's stage 1 is entered on **any** demand touch and persists 60 bars (L2527–L2538); the only selective steps are the qualified sweep and the BOS.

---

## 6. State mapping to the Phase 5 engine

| Engine state | v8.4.0 equivalent | Gap |
|---|---|---|
| `NO_SETUP` | `sx.poiDirL == 0`, no armed machine | — |
| `CONTEXT_VALID` | `ft.gateUp != 0`, killzone, PD gate | checked **after** the trigger, on the confirm bar (F10); no state recorded |
| `LIQUIDITY_CONFIRMED` | `fv.sweptLowQ` / `cx.sweptLowBar` / `z.idmSwept` | per-bar flag (F1, F6, F8, F11) |
| `DISPLACEMENT_CONFIRMED` | `mv.strong` at BOS; `ctx.lastDepStrong` | zone-creation time only; not re-checked for the reaction leg (M41 checks it at arm) |
| `STRUCTURE_CONFIRMED` | BOS/CHoCH flags; M45/M54/M68 arms | F4, F5, F17 |
| `ZONE_VALID` | `zoneOkBull` on the arm bar | F9, F15, H3, H4 |
| `ENTRY_TRIGGERED` | `poiConfL` | F2/F3 stop, F7 entry, F19 arrival |
| `INVALIDATED` | `close < poiLowL − buf` or window expiry | not surfaced to the user; SL ≠ `poiLowL` (F2) |
| `EXPIRED` | `bar_index − poiBarL > i_poiBars` | reject code is 1 (no candidate), indistinguishable from "never armed" |

**Missing evidence surfaced to the operator:** which stage a setup is in, why it was rejected (codes exist only in the data window), the entry/SL/TP of a setup that is armed but not yet confirmed, and the arrival verdict that qualified it.

---

## 7. Bearish side — differences from the mirror

- `s07`/`s07b` are cross-wired by design (M07 is a counter-trend fade: bull-trend pins bid the **short** side, L2780–L2782, L2867, L2891). Correct.
- `s47`/`s47b` likewise (manipulated breakout fades the sweep, L2958–L2959). Correct.
- `s50`/`s53` polarity notes at L2964–L2966 and L2975–L2978 are consistent with the code.
- `relCntBear` (L2501) reads `ft.htfSweepUp` for a bear CISD — correct (a sweep of highs precedes a bearish reversal).
- No asymmetry found in `f_stop`, `f_sig`, `f_conf`, `f_ident`, the gates or the suppression logic. Every F-finding applies to both sides with the mirrored line numbers given in the audit.
