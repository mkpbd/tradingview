# V8 CHANGELOG

## v8.0.0-P0 — skeleton
- M0 indicator, M1 inputs (19 groups), M2 constants + enums + helpers.
- New inputs vs 2..txt: maxSetups, maxPenalty, useVolConf/volMult, spreadGuard, htfOverlapUp,
  allowSynthTp, adaptGrade, trailAfterTp2, previewAlert, SB arming-path group (from 1.txt).
- Removed vs 2..txt: trap engine inputs (→ V8_CONTEXT), MTF ladder (→ V8_CONTEXT), verbose debug (→ V8_CONTEXT).
- No detection yet.

## v8.0.0-P1 — core series + structure
- M3: atrSafe/rngSafe (never divide by raw atr/rng), f_chip lane counter, pins (range-based opposite wick),
  relVol + volPass (auto-bypass when no volume), dispUp/DnBar with volume gate, f_dispQ 7 readings, CISD, IFC.
- M4: Struct UDT, f_structUpdate (real-pivot protected swing, run latch separate from break latch),
  internal + external instances, trigger memories, four vocabularies (BOS/CHoCH/MSS/CISD).
- Temp P1 plots: last swing hi/lo, protected ext hi/lo, display-independence probe (data window).

## v8.0.0-P2 — sessions + SB clock + HTF
- M5: f_inSes, killzone/news gates (newsOK — not volOK, that name is volume), SB minute-math clock
  (sbStart/End, sbPre*, sbWinNow/sbCtxWin, sbActive/sbCtx/sbGate, sbEnd*Evt + f_sbEndEvt, sbWinPts, sbMinRq),
  00:00 / 08:30 lines (draw only), Ses UDT + f_sesTrack (fhi/flo ALWAYS set, lines gated by showSesHL).
- M6: SIX request.security, all expr[1] + lookahead_on + f_tfUp: bias(filter TF), htfCtx, PD, PW, htfStruct, htfPoi.
  htfState (BULL/BEAR/NEUTRAL/CONFLICT), edge-triggered HTF POI mitigation + bSeq/sSeq identity,
  f_atHtfPoi, continuation/reversal verdicts, lqTol/lqReact.
- Temp P2: PDH/PDL plots, SB + news bgcolor, 3 data-window probes (repaint + display-independence).

## v8.0.0-P3 — liquidity registry
- M7: Pool UDT (+kmask/legs), 9 na-safe accessors, f_evTag, f_poolById, draw attrs (PK_WICK lime dashed),
  f_poolPush (single inlined copy, weakest-first prune), registration queue f_qPush/f_qFlush,
  f_poolScan (raid A/B/C grading, TEST vs RAID vs BREAK, two clocks reactWin/sweepLook, consume by distance),
  EQ pivot ring (eqScanN), registrations: swing/EXT/session/PD/PW/HTF,
  V8 wick-cluster pools PK_WICK (LT-3/LT-4 lineage, constants WK_*), trendline sweep → PK_TL,
  target ranking loop (tgtBuy/SellPool objects, inducement, pool breaks), f_findRaid, f_anyRaid, raid marks.
- Temp P3: 8 plotchar raid marks, pool-count + raid probes.

## v8.0.0-P4 — dealing range + zones
- M8: impulse-leg dealing range, OTE bands, PD extremes, SB range LOCK (sbRngHi/Lo frozen at window open; sbSetLive written in M17).
- M9: Zone UDT (+htfOv), accessors, spreadEst/f_zoneThin (V8), f_htfOverlap (V8 nested PD array → tier −1),
  f_raidAtZone, f_gradeZone (causal T1), f_zoneProv, f_regrade (ratchet), f_newZone, f_zoneFlip,
  per-side cap (unbound oldest), lifecycle loop written once via `sup`, 50% CANDIDATE engine,
  f_mkZone (decide-first-delete-second, BPR, OB with own containment), f_mkRb, NEXT POI scan.
- Temp P4: range EQ plot, zone/tier + sdCand/pdPos probes.

## v8.0.0-P5 — triggers + run/congestion/regime + penalty
- M10: CRT (crtTrigB/S) and Turtle soup (tbsTrigB/S) as BOOLEAN stage-6 triggers only → trigDispUp/Dn = disp OR crt OR tbs. Volume-gated like displacement. Never a producer.
- M11: Run UDT + run engine (RN_UNCONF/CONT/EXH/REV), runFadeLong/Short; congestion 4 readings (congMeasured vs congested); regime; AMD/Judas descriptors via f_evTag; f_penalty (V8 counter, capped by maxPenalty).
- Temp P5: regime·run·congN·trig probe.

## v8.0.0-P6 — setup state machine (multi-setup)
- M12: Setup UDT (+sbWin, sbCeFill, dispTrig, blk), upSetups/dnSetups arrays (maxSetups), setupSeq,
  per-POOL blackout (deadPoolId ring) instead of a global resetBar, f_setupRelease (bindings only — no 37-field reset),
  f_narrOk (na-safe), f_inOte, f_htfTier, f_setupAdvance (moved latch, kill flag, SB clocks, SB tag at stage 3,
  trigDispUp/Dn at stage 5/6, SB CE/proximal entry rule + locked-range PD check at stage 8, spread guard on the gap),
  f_runSide (retire → advance → pick winner by tier then raid grade → arm with ctx+tgt SAME bar), f_sideStage.
- Temp P6: stage probe, ungated machine LONG/SHORT triangles (NOT signals yet — no risk/grade gates until P7).

## v8.0.0-P7 — score · gates · risk · trade engine (FIRST REAL SIGNALS)
- M13 f_score (+SB context ≤15, PK_WICK class), f_sesStory.
- M14 base gates, f_dedupeOk (id + price/recency + POI + MSS), story keys (ring 64), minGradeEff (adaptGrade), f_machWorking.
- M15 f_slOk/f_sl (sign-based, 5-level hierarchy, fallback clamped), f_nextPool/f_nextZone/f_oppLiq, f_tp ladder + clamp, f_grade with f_penalty and synthetic-TP2 cap at B.
- M16 f_prod (machine/FEM/S&D, SB tag in label), na-safe Setup/Zone accessors, risk-first, CE entry only if traded, f_gates (allowSynthTp softens hTgt), rank arbitration (SB machine = rank 0), consumption.
- Temp P7: LONG/SHORT plotshape, grade/prod/RR/score probes.

## v8.0.0-P8 — trade management
- M17 Trade UDT, one active trade, stop-first (also intrabar), TP1/TP2/TP3 on closed bars, adaptive BE buffer
  (max(beBuf·ATR, 15% of TP1 distance)), protected-swing trail after TP2 capped by last-2-bar extreme,
  SB exits (opposing shift ≥ entry grade, window-close time exit full/partial), new signal → REPLACED (never overwrite),
  consecSL feedback (adaptGrade), mechanical counters, sbSetLive written here, f_exitTxt.
- Temp P8: trade SL/TP2 plots, tradeEvt probe.

## v8.0.0 — file A complete
- M18 drawing: permanent context plots (18/64 outputs), entry label (signal bar only), 5 trade lines updated per bar,
  exit chip, HTF POI boxes / NEXT-zone tags / SB range-lock lines on last bar only. All P1-P8 temp probes removed.
- M19 dashboard: 9 rows x 2 cells, last bar only; showDebug appends block reason.
- M20 alerts: 6 alertcondition + structured alert() payload + trade-event alert() + optional PREVIEW alert.

## v8.0.0-B — file B `V8_CONTEXT.pine` (P10)
- New companion indicator. Annotation + alert() only — never emits an entry.
- C5 MTF bias ladder: 4 configurable rungs, net figure, rung below chart TF shown as `·`.
- C6 HTF CRT / Turtle-soup / TWS layer on 4 TFs (int-coded classifier, one tuple slot), chip per event, per-TF last-event memory, confluence alert().
- C7 HTF FVG POI boxes on HTF #1 and #2 (same detector as file A M6, edge-triggered mitigation count).
- C8 ◬ trap engine LT-1…LT-7 (1.txt M16B lineage): wick pools, LT-4 shadow-high watcher, two machines, score, labels, dynamic alert(), optional PREVIEW. OB term replaced by HTF POI interaction.
- C9 14-row context panel. C10 4 alertcondition + 2 alert() streams.
- request.security = 10 (cap 12). Plot outputs = 2.

## 2026-09-17 — compile verification
- User compiled V8_ENGINE.pine and V8_CONTEXT.pine on TradingView: no compile error, no CE10117, no runtime error on first load. Token probe numbers still to be recorded.
- Added V8_USER_GUIDE_BN.md: setup, reading the chart, alert setup, acceptance-test checklist with report template.

## v8.0.0-full — V8_FULL.pine (merged single-script build)
- V8_ENGINE.pine + the unique parts of V8_CONTEXT.pine in one script (user request). Context block reuses engine globals; B's duplicate inputs/core/structure/sweep/FVG-slot removed, B's HTF POI #1 dropped (engine M6 already has it).
- Adds 9 request.security (4 ladder · 4 HTF layer · 1 POI #2) → 15 total. Plot outputs 20/64.
- Purpose doubles as the token probe: a CE10117 on this file gives the exact compiled-token count.
- 2026-09-17: user compiled V8_FULL.pine → green, no CE10117. V8_FULL.pine is the MAIN file from here; V8_ENGINE / V8_CONTEXT kept as split fallback.

## v8.0.1 — funnel diagnostics (V8_FULL.pine)
- XAUUSD 5m, 8–17 Sep: 0 signals in ~10 days (T6 starvation FAIL). Long side never armed (HTF 60 BEAR, PD 46% → no reversal); short side stuck at TARGET with no history of why.
- Added dashboard rows "Funnel" (setups that reached T/R/P/M/D/F/E + top kill reason) and "Gates" (candidates that reached M16 + first failing gate). `f_gates` now returns the first failing gate code (0 = pass). Diagnostics only — no gate/grade/score change.

## v8.0.2 — funnel-driven fix (V8_FULL.pine)
- Funnel on 4 symbols (XAU/BTC/EUR/ETH 5m): RAID→POI ~88% dead, POI→MSS ~90% dead, 0 candidates reached M16.
- POI fallback `poiWickFb` (default on): when no zone / HTF FVG contains the raid wick, the raid candle's own rejection wick [extreme → body edge] becomes the POI (tier 2, PA_REJ). New Setup field `poiWick`.
- Defaults: poiBindAtr 0.15→0.35 · mssNeedDisp true→false (CISD alone = MSS; stage 6 still demands the displacement) · mssWin 12→16.

## v8.0.3 — funnel round 2 (V8_FULL.pine)
- Funnel after v8.0.2 (5 symbols): RAID→POI now ~80%; POI→MSS still 6–17%; 4 candidates reached the gates, all failed (3× no TP target, 1× grade).
- MSS stage gains two sources: (a) short-term shift — the latest INTERNAL swing high/low crossed this bar with body ≥ structDisp·ATR; (b) a CISD that fired on the raid candle itself counts one bar later if the close still holds its run-open (new globals cisdUpLvl/cisdDnLvl). Chronology unchanged (mssBar > liqBar).
- Defaults for the test phase: allowSynthTp true (synthetic TP2 graded ≤ B), minGrade "B".

## v8.0.4 — wall definition + retest (V8_FULL.pine)
- US30 5m after v8.0.3: P→M 37% (fixed), D/M 41%, F→E 14%, 1 candidate blocked by "RR floor" — synthetic TP2 clamped by the nearest wall, and every validated minor swing / T3 zone counted as a wall.
- Walls are now engineered pools only (not PK_SWING / PK_WICK) and fresh T1/T2 zones only (f_oppLiq, f_nextZone). Minor swings stay TP1 targets.
- retestDepth 0.5→0.35, lateBars 6→8.
- Token: v8.0.3 measured 100,602 before the display cut; compiles after.

## v8.0.5 — soft penalty floor, MSS short-term fallback, disp body (V8_FULL.pine)
- 4-symbol funnel after v8.0.4 (XAU/EUR/BTC/ETH 5m): P→M 18–29%, M→D 6–42% (ETH 16→1), F→E ~25%; gate fails "grade" (BTC) and "RR floor" (EUR, tie hidden).
- f_grade: a soft penalty (room / congestion / run-fade / HTF conflict / regime) can no longer push B → NONE. Floor is GR_B once the hard grade exists. Soft = re-label, never block (hard blocks stay in f_gates).
- MSS stage: when the confirmed internal pivot is missing or pre-dates the raid by > mssWin, the short-term level is the extreme of the MSS_STH_LOOK (8) bars INTO the raid candle — ICT short-term high/low break.
- dispBodyAtr 1.3 → 1.0.
- Gates row now shows total fails (`fail N: top ×n`) — ties between gates were invisible.
- Cut 7 unused helpers (f_kindTxt, f_tick, f_tmTxt, f_rqTxt, f_biasTxt, f_paTxt, f_roomTxt) to pay for the MSS loop.

## v8.0.6 — MSS nearest level + break definition, 2nd kill reason (V8_FULL.pine)
- XAU 5m after v8.0.5: P→M unchanged at 21% (65→14). Two causes in the stage-4→5 code: (a) `st` fired only on the exact cross bar — a weak cross bar lost the MSS for good; (b) a confirmed pivot inside the window always won over the 8-bar-into-raid extreme, so the level to break was the far pivot, not the nearest lower-high/higher-low.
- Level = NEAREST of the confirmed internal pivot and the MSS_STH_LOOK extreme (long: lower, short: higher). Break = close through it with `min(close[1], open)` on the wrong side (cross, or open-below/close-above) and a displaced body.
- Funnel row shows the top TWO kill reasons (f_topIx takes a skip index) — the P→M kill was hidden behind "setup expired".

## v8.0.7 — raid invalidation = wick only, reversal grading, defaults, entry price on label (V8_FULL.pine)
- 4-symbol funnel after v8.0.6 (second kill reason now visible): "raid failed/stale" ×55–66 = ~70% of raided setups. Cause: "raid level reclaimed" — any close back through the swept LEVEL (pool px) set brkBar and killed the setup. ICT invalidation is the raid WICK, not the level. Rule removed; the wick rule stays. `f_poolBrkBar` accessor cut (unused).
- Gates: BTC "grade ×2" = reversal setups — `revOk` demanded CHoCH + T1 + A-raid + PD-extreme together. Now a reversal exists with a ≥ B raid and grades above B only with the full chain (`revAp`).
- Defaults: htfConfMode "A+ only" → "Downgrade" (ETH: HTF conflict gate blocked the only candidate); tpClamp true → false (EUR: RR floor ×2 from the wall clamp; room check still downgrades).
- Entry label head now carries the entry price: `▲ LONG B @ 4312.5`.
- Releases: every version is now also saved as `releases/V8_FULL_vX.Y.Z.pine` (v8.0.4–v8.0.7 exported from git) so an older build can be restored without git.
