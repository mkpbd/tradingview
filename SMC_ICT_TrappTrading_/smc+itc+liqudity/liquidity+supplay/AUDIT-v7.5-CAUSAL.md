# FORENSIC AUDIT + CAUSAL UPGRADE — `24.liquidty+supply-v7.4-ict.pine` → `25.liquidty+supply-v7.5-ict.pine`

**Date:** 2026-09-11 · **Method:** full static read of the 6 228-line v7.4 file (code from line 1 222), every
module, producer, gate and `request.security`; cross-checked against `AUDIT-v7.3-FORENSIC.md` so nothing already
listed as *known-and-left* is re-reported. Pine cannot be compiled locally; **nothing here is compiled or backtested.**
v7.5 is a NEW file (lineage rule); file 24 is untouched. Build = `build_v75.py` (84 exact-match patches, each
asserting its occurrence count), verified by `check.py` (brackets, indent, defined-before-called, call / tuple arity,
duplicate declarations, UDT field access, forbidden identifiers) and `pinetok.py` (budget).

---

## A · EXECUTIVE SUMMARY

The v7.4 machine path (context → target → raid → POI → MSS → displacement → FVG → retest) was already owned,
chronological and confirmed-bar-only. The *rest* of the engine still borrowed. Three borrowings decided trades:

1. **S/D provenance was fake.** `f_gradeZone` returned the id of the freshest live raid on the side *whether or not
   that raid was at the zone*, and MODULE 9 stamped it as `srcPoolId` on every FVG and OB. The S/D producer then
   "owned" a raid it never traded, and the zone's provenance test (P1-1) compared that borrowed id back against
   the same live raid — a tautology. Fixed: provenance stamped only when the raid wick is at the zone's origin,
   chronology enforced, the whole chain copied onto the zone, the producer reads nothing else.
2. **HTF context was one EMA.** `htfDir` drove the context verdict, the zone tiers, the HTF-POI tier and the score.
   HTF external structure (`hStrDir`) existed and was displayed but decided nothing. Fixed: HTF STATE
   (BULL / BEAR / NEUTRAL / CONFLICT) with structure first; conflict handled explicitly (default: A+ only).
3. **Global trigger flags still gated two producers.** `confGateLong/Short` = the chart's latest internal CHoCH /
   CISD + "a displacement in the last 3 bars", none owned by the array traded. Removed; the S/D producer reads its
   zone's own stamped MSS / displacement, the trap carries its own chronology.

Plus: TWS removed in full; IFVG separated from FAILED FVG; zone mitigation lifecycle; displacement quality;
impulse-leg dealing range; regime → execution policy; story-level dedupe; Judas needs a confirmed reaction; two
compile/runtime-class defects (na-object deref in a ternary, unclamped daily/weekly requests). Net effect is
**fewer, better-owned setups**, and the file is ≈ 650 compiled tokens LIGHTER than v7.4.

---

## B · REMOVED FEATURES — TWS, IN FULL

| removed | where it was |
|---|---|
| inputs `useTws`, `twsWaveWin`, `twsDeepen`; group renamed "⑫ Liquidity run · congestion · regime" | MODULE 1 |
| `LC_IDLE…LC_W2` lifecycle constants and `f_lcTxt` (TWS was their last consumer) | MODULE 2 |
| `type Tws`, `f_twsAdvance`, `twsUp` / `twsDn`, `f_twsRun`, `twsConfL` / `twsConfS`, both "TWS ↑/↓" chips | MODULE 11B |
| `f_evTag(anyLoPool/anyHiPool, "TWS")` — the descriptor written onto the freshest raid on the side | MODULE 11B |
| dashboard row "TWS · AMD · regime" (AMD / regime moved to the new row 3) | MODULE 18 |
| alert `[TRIG] TWS three-wave confirmed` | MODULE 20 |

Verified: `grep -i tws` on non-comment code returns nothing. No score term, tier, grade, gate, dashboard state,
setup stage or entry condition reads anything TWS-derived. Historical changelog prose in the lineage header
(v5.5 … v6.4 notes) still *mentions* TWS as history and was left as history. No feature replaced it.

---

## C · CRITICAL BUGS FOUND (P0 / P1) AND FIXED

| # | sev | bug | location (v7.4) | cause | impact | fix (v7.5) |
|---|---|---|---|---|---|---|
| C-1 | **P0** | Zone provenance stamped from an unrelated raid | `f_gradeZone` L3496 `[t, liq, na(rp) ? 0 : rp.id, …]`; MODULE 9 L3761/3777/3807/3819 | return value ignored `liq`; the id of the freshest live raid on the side was written to every FVG and OB | S/D producer "owned" raids nowhere near its zone; its stop (`anyExt`), grade (`anyRq`), class, dedupe id all belonged to another event; P1-1's identity test was tautological | `f_zoneProv` stamps the chain **only when `liq`** (raid wick at the zone origin) |
| C-2 | **P0** | HTF context = EMA only; structure ignored | `htfDir = nz(htfDirRaw,0)` L2316 → 8 consumers | `hStrDir` (HTF external structure) fed the dashboard only | EMA-bull + structure-bear read as bullish context; zone tiers, HTF-POI tier and score agreed with the EMA | HTF STATE block: `htfConf`, `htfDir` (resolved), `htfState`; `htfConfMode` Off / Downgrade / **A+ only** / Block |
| C-3 | **P0** | Global trigger gate on S/D and trap producers | `confGateLong/Short`, `cMssBarL/S`, `cDispBdL/S` L5067-5072; `f_prod` params `cg`, `iChBar`, `cDispBd`, `cMssBar`, `dispBar2` | latest chart CHoCH / CISD + `recentDispUp` (≤ 3 bars), unrelated to the zone | an S/D retest passed on somebody else's shift and displacement; the trap's "MSS" was the chart's latest CHoCH | removed; S/D reads `srcMssBar / srcMssCh / srcDispBar / srcDispQ`; trap has no MSS (honest 0 trigger points) |
| C-4 | P1 | na-object field access inside a ternary | `f_gradeZone` `na(rp) ? 0 : rp.id` | Pine evaluates both branches; `rp` is na on every bar without a live raid | runtime error class the lineage forbids (never surfaced because never compiled) | uses the `anyLoId / anyHiId` series |
| C-5 | P1 | `mssNeedDisp` inert | `cisdMssUp = cisdUp and (not mssNeedDisp or dispUpBar or strongUp)` L2099 | `cisdUp` already requires `strongUp` | a 0.5-ATR CISD candle was a stage-5 MSS "with displacement" | `or strongUp/Dn` removed |
| C-6 | P1 | Daily / weekly requests not clamped | `request.security(…, "D", [high[1], low[1]], lookahead_on)` L2321, `"W"` L2330 | `f_tfUp` (BUG-01) was applied to every TF except these two | future-data leak on a weekly / monthly chart (registry unaffected — PD/PW registration is gated intraday/daily — but the series existed) | `f_tfUp("D")`, `f_tfUp("W")` |
| C-7 | P1 | Session story read from the wrong event | `sesStoryL` L4998 read `anyLoTag / anyLoKind` for every producer | the freshest raid on the side, not the traded event | machine and trap entries scored / labelled "session story" off another pool | `f_sesStory(evTag, kind)` on the producer's own event |
| C-8 | P1 | Non-machine producers read chart-wide OTE and inducement | `oteQL = … : inOTEbuy ? 2 : 0`, `indHitL = … : indLoBar …` L5564-5570 | global fallbacks | S/D and trap got POI / liquidity points from the chart range and from an inducement they never owned | S/D: OTE on its zone's leg (`srcRaidExt → legExt`, `deepest`), `srcIdm`; trap: 0 / false |
| C-9 | P1 | Score paid a GLOBAL CISD (F-10 known, now fixed) | `f_score` `f_recent(cisdB, TRIG_LOOK)` L5034 | contrary to V4-BUG-5 | +3 on any recent CISD anywhere | term replaced by "owned gap ≥ FVG_GOOD_ATR" (+3) |

### P2 (logic quality) fixed

| # | issue | fix |
|---|---|---|
| C-10 | Every closed-through FVG became an "IFVG" (tier 2 if `isBrk`) on the violation bar | FAILED FVG (tier 3, `PA_MIT`, `ifvgPend`) → TRUE IFVG (tier 2, `PA_IFVG`) only after price returns from the other side and holds with a rejection; violation must be meaningful (displacement or ≥ 0.5-ATR body) |
| C-11 | BPR overlap PROMOTED a zone's tier from an unrelated later gap | re-tag only (`pa`, `kindTxt`); `f_paRank` already prefers BPR over a raw FVG at POI selection |
| C-12 | No discrete mitigation count; lifecycle was fill-depth only | `Zone.mitN` / `inZ` (edge-triggered); `f_regrade`: 2nd mitigation ≤ T2, 3rd = T3 |
| C-13 | Displacement quality = body size | `f_dispQ` (6 readings) → `Setup.dispQ`, `Zone.srcDispQ`; score reads quality |
| C-14 | Dealing range = latest external high + low, regardless of leg | protected low → swing high after it (bull) / protected high → swing low after it (bear); pivot pair only as fallback |
| C-15 | Regime reported only | `regPolicy`: TREND penalises a reversal, RANGE penalises the wrong half, EXPANSION refuses the trap's reclaim-close entry, CHOP = congestion gate (+ "A+ only" mode) |
| C-16 | No story-level dedupe across producers | `f_storyKey` = dir\|pool\|raid bar\|POI\|MSS bar\|FVG bar, 60-slot ring, hard gate `hStory` |
| C-17 | Judas = a session/PD raid inside a killzone | + raid grade ≥ B + pool at `PS_REACT` (confirmed reaction) |
| C-18 | FVG zones had no minimum height (machine gap did) | `newDemand/newSupply` require `fvgMinAtr` |
| C-19 | S/D retest quality constant 2 (F-10) | measured from fill depth (`sdRetQL/S`) |
| C-20 | `raidNearPx` compared pool PRICE not wick (known) | `anyLoExt / anyHiExt` |
| C-21 | S/D `spent` flag on the LIVE raid pool (F-01 residual: with `needSweep` the live pool was the owned pool only by the tautology in C-1) | `f_poolById(dedupePool, poolIdL)` spends the pool the zone owns, by identity |

Known-and-left items from `AUDIT-v7.3-FORENSIC.md` §2 / §7 verified still present and **not** re-reported: congestion
double count · EQ/swing pools registered `pivLen` late · `legHi/legLo` extend through ST_DISP · `poiFresh` frozen at
tap · double-counted structural break in `f_structUpdate` · dashboard label for a clamped bias TF · `f_tfUp`
qualifier unverifiable offline · E2-E IFVG continuation (now partly covered: an IFVG is a machine-bindable POI but
still not a raid-equivalent for the opposite machine).

---

## D · LOGIC IMPROVEMENTS — THE CAUSAL FLOW

### D.1 Setup identity (§4) — what each producer OWNS

| field (brief) | machine (`Setup`) | S/D producer (`Zone`) | trap (watch) |
|---|---|---|---|
| setupId | `s.id` | `z.id` | `wStart` |
| targetPoolId / raidPoolId | `tgtId` == `liqId` (f_narrOk) | `srcPoolId` | `wId` (the pool BROKEN) |
| raidBar / raidPrice / raidExtreme / raidGrade | `liqBar` / pool px / `liqExt` / `liqQual` | `srcRaidBar` / `srcRaidPx` / `srcRaidExt` / `srcRaidRq` | `wStart` / `wPx` / `wExtreme` / `trapQ` |
| poiId / poiType | `poiId` / `poiPa` | `z.id` / `z.pa` | — (the reclaimed level) |
| mssBar / mssLevel / mssDirection | `mssBar` / `mssLvl` / `mssChoch` | `srcMssBar` / `srcMssCh` | none (honest) |
| displacementBar / displacementScore | `dispBar` / `dispQ` | `srcDispBar` / `srcDispQ` | reclaim bar / `dqUp` if it displaced |
| fvgId / fvgBar | `fvgBar` (+ top/bot/H) | `bornBar` (the zone IS the gap) | — |
| session / regime | `sbWindow`; live session + `regime` at grade | same | same |
| entryBar / entryPrice | `retestBar` / `entryPxL` | signal bar / zone 50 % or close | signal bar / close |
| story | `f_storyKey(dir, liqId, liqBar, poiId, mssBar, fvgBar)` | `(dir, srcPoolId, srcRaidBar, id, srcMssBar, bornBar)` | `(dir, wId, wStart, 0, na, na)` |

### D.2 Supply / Demand provenance (§6 / §7)

```
zone created on the FVG-confirming bar (displacement = bar-1, gap = high[2]..low)
  liq  : live raid on the side, wick inside [zBot − sdRaidAtr·ATR, zTop + poiBindAtr·ATR] (demand; inverse supply)
  mss  : latest internal CHoCH / CISD with  raidBar < mssBar ≤ dispBar  AND the broken level formed ≥ raidBar − mssWin
  disp : dispUpBar[1] (the leg that left the gap; adjacency is by construction)
  T1   = liq ∧ disp ∧ mss ∧ HTF agrees ∧ discount half        → f_zoneProv stamps the chain
  T2   = disp ∧ chart structure agrees                        → no provenance; machine-bindable POI only
  OB   = last opposing candle of the SAME leg, same tier, same provenance stamp
```
The S/D producer requires `srcPoolId != 0 ∧ srcMssBar known`; stop = `srcRaidExt`, grade = `srcRaidRq`, MSS /
displacement / inducement / OTE = the zone's own. `machFirst` still yields to a same-side machine on the same pool.

### D.3 The machine path — unchanged in kind, tightened in three places
`cisdMssUp` needs a real displacement candle; stage 6 / E2-B stamp `dispQ`; the story key is checked before emission.
Chronology `ctxBar < tgtBar < raidBar ≤ poiBar < mssBar < dispBar ≤ fvgBar < retestBar` and `f_narrOk` unchanged.

### D.4 Trap (§17)
Liquidity BREAK (registry pool, `wId`) → failed acceptance (growing wicks) → RECLAIM (close back through, body ≥ 0.5
ATR) → displacement (graded; required for elite) → entry. Owned identity since v7.4; v7.5 stops it borrowing the
chart's MSS / OTE / inducement, refuses it in EXPANSION, and (consequence, deliberate) a **counter-HTF trap can no
longer pass `revOk`** because it owns no CHoCH-grade MSS.

---

## E · REPAINT / LOOKAHEAD AUDIT — what was checked

| area | finding |
|---|---|
| `request.security` (6 sites, 6 instances) | all read `expr[1]` INSIDE the request with `lookahead_on` = last CLOSED HTF bar; all TFs clamped ≥ chart by `f_tfUp` — **v7.5 closes the two unclamped ones ("D", "W")** |
| pivots | `ta.pivothigh/low(n, n)` everywhere; a level is usable `n` bars after it printed; pools are back-dated to the pivot bar but REGISTERED on the confirming bar. Documented delay, no leak |
| `[1]` / `[2]` reads | `zDispUp = body[1]…`, `dqUp[1]`, `bullFVG[1]` (F-06), `nbTop[1]`: history of series already final on those bars |
| state mutation | every latch is inside `if confirmed` (structure, CISD runs, registry scan, zone loop, trap watch, run engine, machine, consumption). Unconfirmed-bar mutation exists only in `f_sesTrack` hi/lo and `f_chip`'s lane counter, both on `var` state that TradingView rolls back per tick |
| new v7.5 state | `Zone.mitN/inZ/legExt/ifvgPend` mutate inside the confirmed zone loop; `storyKeys` pushed inside `if finalLong/Short` (confirmed series); HTF state is a pure function of closed-HTF series |
| labels / alerts / plots | entry marks = `finalLong/Short` (confirmed producers only); chips gated on confirmed events; `alertcondition`s read confirmed series (`(ifcBull or ifcBear) and confirmed`, etc.) |
| realtime = historical | the decision bar uses `close/high/low` of the closed bar and HTF values from closed HTF bars; the `showDev` preview is the one deliberately intrabar element (dim, no state, no alert) |
| unverifiable offline | `f_tfUp`'s `simple string` qualifier chain (unchanged from v7.2); Pine's ternary both-branch evaluation was treated as true (lineage rule) — every object deref in v7.5 sits inside `if` bodies or na-safe helpers |

---

## F · HTF FRAMEWORK (final)

```
layer 1  HTF external structure   hStrDir   (htfTf pivots 2,2 · closed HTF bar)        ← authority
layer 2  HTF momentum             htfMom    (EMA(biasLen) on htfCtxTf · closed HTF bar)
layer 3  HTF dealing range        htfPd     (htfCtxTf pivots 3,3)  → premium / discount precondition
layer 4  HTF liquidity position   hPoiB/S   (HTF FVG POI, mitigation count)  → FEM POI, "at a location"
state    htfConf = struct ≠ 0 ∧ mom ≠ 0 ∧ struct ≠ mom
         htfDir  = conf ? 0 : struct ≠ 0 ? struct : mom       (resolved direction, read by every consumer)
         HS_BULL / HS_BEAR / HS_CONF / HS_NEUT
context  continuation = htfDir agrees ∧ (discount half ∨ at HTF POI)
         reversal     = allowRev ∧ htfDir opposes ∧ (HTF PD extreme ∨ opposing HTF POI)  → hard grade-A/T1/CHoCH/PD rule
         conflict     = arms (unless Block) → Downgrade | A+ only (default) | Block
LTF      internal CHoCH / CISD = execution timing only; it never touches the HTF state (§10)
```

---

## G · ENTRY MODEL — why an A+ qualifies

An **A+** (machine or FEM) requires, all at once: HTF state not opposed (or reversal rule met; conflict → A+ only
passes); a target pool LOCKED before its raid, raided after the lock, grade-A raid (depth ≥ raidDeepAtr + rejection);
a POI that existed before the raid and CONTAINS the wick; an MSS after the POI tap breaking a level that formed around
the raid; a displacement candle with body ≥ dispBodyAtr, closing past the MSS level, out of the POI, holding ≥ 55 %;
an FVG of which the displacement is one of the three candles, ≥ fvgMinAtr; a retest to depth with a close back
through the gap's 50 % and a rejection, within `lateBars` of the first touch and ≤ `apMaxTouch` touches; OTE class 1
(62-70 % of its own raid→displacement leg) when `oteNeedAp`; live POI tier 1; `f_narrOk` re-derived chain; a stop
inside the risk clamp; a REAL TP2 (opposing wall / external / internal pool ≥ rrB away) with RR ≥ rrAplus; room to the
nearest opposing liquidity; not congested, not fading a live run, not a duplicated pool / price / POI / MSS / STORY;
regime policy not objecting. **A** = one soft ingredient short (grade-B raid, tier 2, OTE deep, third touch…).
**B** = graded raid + B floor + real target. Anything else is NO TRADE with the exact gate named in the debug panel.
Session, Silver Bullet, OTE, regime, descriptors and score can only FILTER or RANK — none can create a trade.

---

## H · PERFORMANCE / BUDGET

| | src tok | compiled (fit: 3.422·tok − 9 411, from files 14 = 99 740 and 17 = 108 630 real) | spare |
|---|---|---|---|
| v7.4 (file 24) | 31 850 | ≈ 99 580 | ≈ 676 |
| v7.5 before reclaim | 32 290 | ≈ 101 085 | −829 |
| **v7.5 shipped** | **31 659** | **≈ 98 930** | **≈ 1 330** |

Reclaim: TWS (−≈330) · `confGate*` block (−≈70) · `needSweep`/`sdOwn` (−≈55) · `f_findRaid` dead params ·
R1 mirrored demand / supply creation → `f_mkZone` (−≈130) · R2 `f_atHtfPoi` reused by the context verdict (−≈40) ·
R3 `f_ctxBox` (−≈70) · R4 `f_entryLbl` (−≈30) · R5 display cut: session-line "✓ SWEPT" annotation + `lqSesState`
(−≈165; the pool line at the same price already restyles). Runtime: `f_poolById` scans are gated (`go`) and run only on
an S/D emission or descriptor lookup; no new `request.security`, no new per-bar loop; six instances unchanged.
Top-level statements 962 → 964 (CE10295 cap ≈ 2 030 by the lineage's metric — not in play). Outputs 54 → 53.

---

## I · REMAINING LIMITATIONS (honest)

* Not compiled, not backtested. If CE10117 appears, the first behaviour-free cut is MODULE 8B's cluster pass
  (`f_lqCluster`, ≈ 280 src); never the debug panel.
* A zone's pool usually leaves the registry (reactWin / sweepLook / distance) before the 50 % retest → the S/D entry
  then carries no descriptors and the `spent` flag cannot be set; the PRICE dedupe (E7) still holds the level.
* HTF "structure" is `hStrDir` = close beyond the last HTF pivot(2,2) — a BOS/CHoCH-lite without HTF protected swings.
* `f_dispQ`'s thresholds (0.75 hold, 0.2 wick, 1.5× mean body) are operator defaults, not fitted.
* Regime policy penalties are one-grade steps; RANGE uses the chart leg's equilibrium, not an HTF one.
* TP1 / TP3 remain synthetic (entry ± R) when no pool qualifies — RR never reads them (TP2 only), so no gate is affected.
* Counter-HTF traps are now effectively blocked (no owned CHoCH); intended, but it lowers trap frequency further.
* The story key uses `str.tostring` concatenation on emission bars only; a 60-entry ring is cheap but finite.
* Descriptor bonus (JUDAS / RUN EXH) is still attached to the live raid pool by the engines that recognise it — that
  pool is by construction the event they describe, so it is owned, but it is the one remaining `anyLo*` consumer that
  feeds a score term.

---

## J · VERIFICATION ON A CHART (after loading v7.5)

| # | check | expect |
|---|---|---|
| 1 | compiles | note the real CE10117 figure back into the lineage note; fit predicts ≈ 98 930 |
| 2 | dashboard row 1 during an HTF pullback (EMA against structure) | `CONFLICT`, orange; debug BLOCKED reads "HTF CONFLICT …" for a non-A+ candidate |
| 3 | new demand FVG with a sweep low ≤ 1 ATR below it | box `DEMAND T1`; debug `story` on its S/D entry shows the SAME pool id as the raid chip |
| 4 | new demand FVG with the latest raid far away | `T2` at most; S/D producer never fires on it ("no producer") |
| 5 | FVG closed through with a displacement candle | box `FAILED FVG ▼ T3`; after a return + hold + rejection: `IFVG ▼ T2` |
| 6 | zone touched, left, touched, left, touched | tier ≤ T2 after the 2nd entry, T3 after the 3rd |
| 7 | debug `disp · quality` | `q0…q6`; score TRIGGER 6 only at q ≥ 5 or (q ≥ 3 and left the range) |
| 8 | same narrative re-discovered after cooldown | BLOCKED "duplicate STORY …" |
| 9 | regime EXPANSION with a trap candidate | BLOCKED "regime policy — EXPANSION …" |
| 10 | alert list | `[TRIG] TWS three-wave confirmed` gone; the other 32 names unchanged |
