# SMC v8.4.0 → v8.4.1 — Improvement Roadmap

Source: `SMC_v8.4.0.txt`. Findings F1–F26 / H1–H4: `SMC_v8.4.0_FORENSIC_AUDIT.md`. Acceptance tests: `SMC_VALIDATION_TEST_PLAN.md` (T-numbers).

**Status: proposal only. No production code has been changed.** Implementation starts only after approval, as a new file `SMC_v8.4.1.txt`, one stage per compile.

---

## 1. Constraints that shape every stage

| Constraint | Evidence | Consequence |
|---|---|---|
| Compiled-token ceiling 100,256 | header L35–L38: a previous build landed at 101,975 and modules were cut; current headroom **unknown** | each stage lists its token estimate; the user must report the compile count after stage 1 before stages 6+ |
| `Ctx` at the 254-element UDT cap | L517 comment | new state goes into `Sx` or `Feat`, never `Ctx` |
| `f_bid` inlined ~120× | L2846–L2850 | no logic added inside `f_bid` |
| `f_stop` / `f_sig` have 2 call sites each | L3404, L3437 / L3508, L3527 | their signatures may change cheaply |
| Preserve inputs, defaults, module set, label text | brief §10 | every change is behind existing inputs or is a pure bug fix; one new input (stage 8) is optional |
| Keep `indicator()` | brief §7 | the strategy harness is a separate file, not a conversion |

---

## 2. Stage plan

Order = impact ÷ token cost, with dependencies respected. Each stage is one compile, one commit, one regression run.

| Stage | Findings | Change | Files / functions | Est. tokens | Depends on | Acceptance |
|---|---|---|---|---|---|---|
| 1 | F2, F3, F11 | Stop reference = reaction / sweep extreme | `f_stop` (+2 params), `f_sig` (+2 params), 2 lines in main scope | +60 | — | T-01, T-02, T-03 |
| 2 | F1, F19 | Carry sweep window and arrival verdict across arm→confirm | `Feat` (+2 bool), `ZS` (+2 bool, +1 float), arm block, `zoneOkBull/Bear`, `f_conf` (reads `zz.*`), `arrOkBull`, `pbOk` | +90 | — | T-04, T-05, T-06 |
| 3 | F18 | FVG-at-price evaluated before touch-mitigation | `f_fvg` (set `fv.atBullFvg/atBearFvg` in the `hit` branch), delete the later scan L2455–L2463 | −10 | — | T-07 |
| 4 | F4, F6, F7 | Release swing on expiry/fail; IDM same-candle; clamp limit entry | `f_structure` (4 lines), `f_zones` (−2 tokens), `f_sig` (2 lines) | +30 | — | T-08, T-09, T-10 |
| 5 | F17 | R2 CHoCH level | `f_structure` (`chLvl` once per side), `Sx` (+1 float for the line), drawing L3750–L3753 | +35 | 4 | T-11 |
| 6 | F5 | HTF pending break | `Sx` (+1 int), `f_htf` | +45 | — | T-12 |
| 7 | F9, F10 | Arm without 50 %-close; killzone at arm | `Sx` (+2 bool), arm block, `rejL/rejS` | +50 | 2 | T-13, T-14 |
| 8 | F8, F12, F13, F14 | Pool price = extreme; path check incl. FVG; OB on CHoCH; MSS window | `f_addLevel`, `f_pathBlock`, `f_zones` condition, 2 lines main scope | +45 | 3 | T-15 … T-18 |
| 9 | F15, F16, F20, F21, F24 | Re-entry touch; per-side identity; committed panel signal; alert ↔ `d_sig`; note reset | `f_zones`, main scope, `f_panel` args | +60 | — | T-19 … T-23 |
| 10 | evidence panel (§4) | Optional on-chart setup evidence table | new `f_evidence`, 1 input | +250 | 2, 7 | T-24 |

Cumulative: stages 1–5 ≈ +205 tokens; 1–9 ≈ +405; with stage 10 ≈ +655. If the compile count after stage 1 shows less headroom than that, cut in this order (all default-OFF, per header L39): M44, M47, M48, M49, M50, M52, M53, then M63, M65.

P3 items not scheduled (document only): F22 (redundant test — leave, costs nothing), F23 (rename input label; zero tokens, can ride any stage), F25 (design decision), F26 (hypothesis; toggle exists).

---

## 3. Stage detail — smallest safe change per defect

### Stage 1 — F2 / F3 / F11

Main scope, after the POI state machine (after L2749):
```pine
slRefLo = not immMode and poiConfL ? math.min(low, sx.poiLowL)  : math.min(low, nz(low[1], low), nz(low[2], low))
slRefHi = not immMode and poiConfS ? math.max(high, sx.poiHighS) : math.max(high, nz(high[1], high), nz(high[2], high))
// (keyed on poiConfL, not na(sx.poiLowL): poiLowL is never reset, so an older arm would otherwise leak into non-POI modules)
```
`f_stop(cf, cx, fv, isLong, aV, bufA, maxA, ep, refLo, refHi)`:
```pine
if zz.kind != ""
    sl := isLong ? math.min(zz.bottom, refLo) - buf : math.max(zz.top, refHi) + buf
else if (isLong and fv.sweptLow) or (not isLong and fv.sweptHigh)
    sl := isLong ? refLo - buf : refHi + buf
else
    ... (majorLow branch unchanged)
    else
        sl := isLong ? refLo - buf : refHi + buf
```
`f_sig` gains `refLo, refHi` and passes them to both `f_stop` calls. M10's wick test (L2796/L2797): `math.max(cd.dnWickRatio, ctx.dnR2) >= cfg.sweepWickMin` (`ctx.dnR1` is already this bar at that point, L2385).
Why `low[1], low[2]` in IMMEDIATE mode: covers the two-bar sweep (F11) and a reaction candle one bar before an engulfing confirm.
Behaviour preserved: when the reaction low is inside the zone, `math.min` returns the zone bottom — identical to v8.4.0.

### Stage 2 — F1 / F19

`Feat` +`swRecentL`, `swRecentS` (bool). `ZS` +`arrWeak`, `arrStrong` (bool), `arrMixed` (float).
Main scope before `zoneOkBull`:
```pine
ft.swRecentL := ft.sweptLow  or (ctx.sweptLowBar  >= 0 and bar_index - ctx.sweptLowBar  <= 10) or (ctx.intSwpBull > 0 and bar_index - ctx.intSwpBull <= 10)
ft.swRecentS := ft.sweptHigh or (ctx.sweptHighBar >= 0 and bar_index - ctx.sweptHighBar <= 10) or (ctx.intSwpBear > 0 and bar_index - ctx.intSwpBear <= 10)
zoneOkBull = atBullZone and zMidB and (not fl_SwR or not ft.zb.sweepReq or ft.swRecentL) and ...
```
In the slot-write block of `f_zones` (L2037–L2049) copy nothing new; instead at the arm (L2732–L2739) write `sx.poiZb.arrWeak := ft.arrivalWeak`, `arrStrong`, `arrMixed`. After the restore (L2689–L2696) add:
```pine
if not immMode and sx.poiDirL == 1 and not zoneTouch
    ft.arrivalWeak := ft.zb.arrWeak
    ft.arrivalStrong := ft.zb.arrStrong
    ft.arrivalMixed := ft.zb.arrMixed
```
(mirror for the short side; when both sides are armed and neither is live-touched, the long restore runs first — acceptable, both snapshots were measured on their own arm bars). `f_conf` L3346: `fv.sweptLow` → `fv.swRecentL`; L3340: `fv.sweptLowQ` → `(fv.sweptLowQ or (ctx window))` — simplest is a second `Feat` bool `swRecentQL/S` using only `cx.sweptLowBar`.
The 10-bar window matches the existing `sweepBosBull` window (L2477) and the ✕ marker (L3665).

### Stage 3 — F18

In `f_fvg`, inside `if hit:` (L1296) before `g.mitigated := true`:
```pine
if g.isBull
    fv.atBullFvg := true
else
    fv.atBearFvg := true
```
This marks the bar that **enters** the FVG (TOUCH mode) — the reaction bar — which is what the modules need. For `50%` / `FULL` modes keep the existing scan (L2455–L2463) so that bars inside the gap but not yet at the mitigation level still count; the scan can stay as is because it is already correct for those modes. Net: +12 tokens, or −10 if the scan is removed and only TOUCH semantics are kept (decide at compile time).

### Stage 4 — F4 / F6 / F7

`f_structure` expiry (L1066–L1067):
```pine
if bar_index - sx.stPendBar > pendBars
    if sx.stPendDir == 1
        cx.hiBroken := false
    else
        cx.loBroken := false
    sx.stPendDir := 0
```
Failed follow-through (L1041–L1043): add the same two-way reset keyed on `sx.stBrkDir` before clearing it.
F6: delete `and low > z.top` (L1880) and `and high < z.bottom` (L1951).
F7 (`f_sig` L3395–L3399):
```pine
g.entry := isLong ? math.min(close, zzE.top) : math.max(close, zzE.bottom)
...
g.entry := isLong ? math.min(close, (high + low) * 0.5) : math.max(close, (high + low) * 0.5)
```

### Stage 5 — F17

In `f_structure` after `chUp/chDn` (L1086–L1087):
```pine
chLvlUp = not na(cx.majorHigh) and close > cx.majorHigh ? cx.majorHigh : cx.curHigh
chLvlDn = not na(cx.majorLow)  and close < cx.majorLow  ? cx.majorLow  : cx.curLow
```
Use `chLvlUp` at L1101 (`f_pend(sx, 1, 2, chLvlUp, ...)`) and L1137; `chLvlDn` at L1117 and L1154. Store `sx.chLineLvl := chLvlUp/Dn` and `sx.chLineIdx` for the event line at L3750–L3753 (`fromIdx` for `f_pend`/`f_legOrigin` stays `majorHighIdx`, which is the correct protected swing for the new leg).

### Stage 6 — F5

`Sx` +`hPend` (int). In `f_htf`:
```pine
if bBrk
    cx.hHiBroken := dispH
if sBrk
    cx.hLoBroken := dispH
promH = (sx.hPend == 1 and bBrk) or (sx.hPend == -1 and sBrk)
sx.hPend := bBrk and not dispH ? 1 : sBrk and not dispH ? -1 : 0
if dispH or promH
    ... existing block
```
A promoted break consumes the swing: add `cx.hHiBroken := true` / `cx.hLoBroken := true` inside the `promH` case.

### Stage 7 — F9 / F10

`Sx` +`poiSessL`, `poiSessS` (bool).
```pine
zoneArmB = atBullZone and (not fl_SwR or not ft.zb.sweepReq or ft.swRecentL) and (not fl_50 or ft.zb.kind == "SR" or ft.zb.fifty)
// arm:  ... and (zoneArmB or ft.atBullFvg) and revBull   ; sx.poiSessL := ft.sbSessOk
sessOkL = ft.sbSessOk or (poiConfL and sx.poiSessL)
rejL := bL.n == "" ? 1 : ... : not sessOkL ? 3 : 0
```
`zoneOkBull` (with `zMidB`) stays for the confirm bar and for IMMEDIATE mode.

### Stage 8 — F8 / F12 / F13 / F14

- F8 `f_addLevel` L1394: `L.price := isHigh ? math.max(L.price, price) : math.min(L.price, price)`.
- F12 `f_pathBlock`: add the FVG loop from `f_nearestOpp` (L3266–L3275) with `hit := true; break`.
- F13 `f_zones` L1668: `if (bullBOS or bearBOS or bullCHoCH or bearCHoCH) and barstate.isconfirmed`, `isBull = bullBOS or bullCHoCH`. KL scoring then also runs on CHoCH legs — acceptable and consistent with S2's "origin of the breaking leg".
- F14: `poiWin = mssMode ? math.max(i_poiBars, 12) : i_poiBars` used at L2721/L2723.

### Stage 9 — F15 / F16 / F20 / F21 / F24

- F15: replace the cooldown test at L1923/L1994 with a re-entry test: `if low[1] > z.top` (bull) / `if high[1] < z.bottom` (bear), keep `lastTouch` update.
- F16: `lastIdentL/lastIdentS`, `lastIdentBarL/S`.
- F20: `var Sig lastL = Sig.new()`, `var Sig lastS` written at L3584; pass `lastL/lastS` to `f_panel`; row label "Signal (last confirmed)".
- F21: `hasL and d_sig` in L3872–L3883 (or document).
- F24: `g.note := ""` before the fallback append; re-apply the min-risk floor in the fallback branch.

---

## 4. Phase 5 — Transparent entry decision engine (proposal, separate from the bug fixes)

This is a **model change**, not a bug fix, and is documented as a separate proposal per brief §10. It can be implemented after stages 1–7 without changing any module's trading rule: it only records *which stage* each side is in and *why* it stopped, and shows it.

### 4.1 States and transitions (per side; long shown)

```
NO_SETUP
  └─(gate ≠ 0 ∧ session ok ∧ not PD-blocked)────────────► CONTEXT_VALID
CONTEXT_VALID
  └─(swRecentQL ∨ zb.idm ∨ htfSweepDn)───────────────────► LIQUIDITY_CONFIRMED   [optional stage, see 4.3]
LIQUIDITY_CONFIRMED
  └─(lastDepStrong within N ∨ dispBull ∨ newBullFvg)──────► DISPLACEMENT_CONFIRMED
DISPLACEMENT_CONFIRMED
  └─(bullBOS ∨ bullCHoCH ∨ armed M45/M54/M68)─────────────► STRUCTURE_CONFIRMED
STRUCTURE_CONFIRMED
  └─(zoneArmB ∨ atBullFvg) ∧ revBull──────────────────────► ZONE_VALID            (= sx.poiDirL := 1)
ZONE_VALID
  ├─(close > poiRefL ∨ newBullFvg) ∧ module predicate─────► ENTRY_TRIGGERED       (= poiConfL ∧ bL.n ≠ "")
  ├─(close < poiLowL − buf)───────────────────────────────► INVALIDATED
  └─(bar_index − poiBarL > poiWin)────────────────────────► EXPIRED
ENTRY_TRIGGERED
  └─(f_sig ok ∧ score ≥ min ∧ no conflict/gap/identity)───► SIGNAL (commit)        else REJECTED(code)
INVALIDATED / EXPIRED / REJECTED / SIGNAL ──(next bar)────► NO_SETUP
```

Reset rules: any transition to INVALIDATED / EXPIRED / SIGNAL clears the side; an opposite-side SIGNAL does **not** clear this side (the gap/conflict logic already handles it); a new structural event against the side (bearCHoCH while long is ZONE_VALID) → INVALIDATED.

### 4.2 Mapping to existing state (no new trading logic)

| State | Existing variables | New |
|---|---|---|
| CONTEXT_VALID | `ft.gateUp`, `ft.sbSessOk`, PD gate | `sx.stageL` (int 0–7) |
| LIQUIDITY_CONFIRMED | `ft.swRecentQL` (stage 2), `ft.zb.idm`, `ft.htfSweepDn` | — |
| DISPLACEMENT_CONFIRMED | `ctx.lastDepStrong`, `ft.dispBull`, `ft.newBullFvg` | — |
| STRUCTURE_CONFIRMED | `st.bullBOS/bullCHoCH`, `ctx.m45Dir/m54Stage/sx.m68Dir` | — |
| ZONE_VALID | `sx.poiDirL == 1` | — |
| ENTRY_TRIGGERED | `poiConfL and bL.n != ""` | — |
| INVALIDATED / EXPIRED | the two branches at L2721 | `sx.whyL` (int: 0 none · 1 window · 2 close below invalidation · 3 opposite structure) |
| REJECTED | `rejL` 2–8 | reuse |

The stage is **descriptive**: modules keep their own predicates. The engine does not force every module through LIQUIDITY → DISPLACEMENT → STRUCTURE; a module that does not require a step records that step as "n/a". This satisfies the brief's "do not force every trade to satisfy every concept".

### 4.3 Configurability

One input `i_reqStages` (string, options "Module rules only" · "Require liquidity" · "Require liquidity + displacement" · "Full sequence"). Default "Module rules only" = v8.4.1 behaviour. Higher settings add a hard gate at the named stages for **all** modules, which makes the strict ICT sequence testable against the module rules in the validation plan (T-25).

### 4.4 Properties required by the brief

| Requirement | How it is met |
|---|---|
| No duplicate signals | existing gap + identity, F16 fixed |
| Reject invalidated zones | ZONE_VALID → INVALIDATED on close below `poiLowL`; stage 1 makes the SL equal to that level |
| Setup vs entry distinction | ZONE_VALID (setup) vs ENTRY_TRIGGERED (entry) are separate stages and separate panel rows |
| Confirmed-bar mode | all commits remain `barstate.isconfirmed`; stage values shown as "provisional" until confirmed |
| Long / short independent | `stageL/stageS`, `whyL/whyS` |
| No lookahead | no new `request.security`; no new offsets |
| Rejection reason | `rejL` + `whyL` rendered as text |
| Consistent entry/SL/TP | single `f_sig` call; panel reads the same `Sig` |
| Alerts match | alerts read the committed `Sig` (stage 9) |

### 4.5 Setup evidence panel (on-chart, optional, `d_evidence` input)

A second table (`position.bottom_left`, 2 × 14), filled on `barstate.islast` from the **committed** signal if one exists on this bar, else from the current stage:

| Row | Source |
|---|---|
| Direction | `lastL/lastS` or stage side |
| HTF bias · gate | `ft.htfBias`, `gateUp/Dn` (aligned / ⚠ counter / blocked) |
| Liquidity | `swRecentQL` kind + bars ago, or IDM✓, or HTF sweep, or "—" |
| Displacement | `lastDepStrong` + `dispScore`, bars since |
| Structure | last BOS/CHoCH + real/fake, bars since |
| Entry zone | `zb.kind`, touches, fifty, sweepReq, arrival verdict (from snapshot) |
| Trigger | stage text: armed (n/8) · confirmed · invalidated (why) · expired |
| Invalidation | `sx.poiLowL` (long) — the number the engine actually uses |
| Entry / SL / TP1 / R:R | from `Sig` |
| Confirmation state | CONFIRMED (bar closed) / PROVISIONAL |
| Rejection reason | `rejL` code → text table (1 no candidate … 8 duplicate) |

Wording on the panel: "Setup evidence" and "entry evidence footprint". No row claims to show institutional orders; the "Liquidity" row names the level kind (POOL / PDL / SESL) that was swept, which is an observable price event.

Token note: a 14-row table body in a function is ~250 tokens. If headroom is insufficient, ship the stage + reason as two data-window plots first (≈ 20 tokens) and the table later.

---

## 5. Model-change proposals (not bug fixes, each needs separate approval and its own A/B test)

| ID | Proposal | Rationale | Test |
|---|---|---|---|
| MC-1 | `CONFIRMED+DISP` trigger option: confirm candle must satisfy the structure displacement inputs or print an FVG | false-signal S2 | T-26 |
| MC-2 | Max entry extension from the POI (k × ATR) on the confirm bar | S3 | T-27 |
| MC-3 | `M10+MSS` variant at tier 3 | S4 | T-28 |
| MC-4 | Liquidity levels as path obstacles | S1 | T-16 (extension) |
| MC-5 | Re-entry resets `fiftyHit`; tapped-zone expiry | S5 | T-29 |
| MC-6 | ATR-relative min risk; session-open exclusion | S7 | T-30 |
| MC-7 | Identity without module name (one visit = one trade) | S10 | T-22 (extension) |
| MC-8 | Merge the WARN −1 and INCOMPLETE −1 into one penalty | F25 | score distribution before/after |

---

## 6. Implementation protocol (per stage)

1. Copy the previous stage's file to the new version name; edit only the lines listed for the stage.
2. Compile in TradingView; record the compiled-token count in `SMC_CHANGELOG.md`.
3. Run the stage's T-tests from the validation plan on the reference charts (bar replay, confirmed-bar mode).
4. Export the signal list (bar time, side, module, entry, SL, TP1, score) before and after; diff. Only the signals the stage's finding predicts may change.
5. Confirm that no historical signal appears or moves earlier than its confirm bar (repaint test T-R1).
6. Commit with the finding IDs in the message.

Stop conditions: compile over the limit (cut per §2 order, re-run), any T-test regression on an unrelated module, any signal that moves to an earlier bar.
