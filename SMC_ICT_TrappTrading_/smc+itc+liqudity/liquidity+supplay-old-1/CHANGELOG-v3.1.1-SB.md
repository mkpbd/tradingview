# LQ-SD-PA v3.1.1 — SB-only refinements

`3.version-3.1.1-silverbullet.pine` — built from `2.version-3.1-silverbullet.pine`,
which is left untouched. See `CHANGELOG-v3.1-SB.md` for everything v3.1 itself changed.

## v3.1.1 — six SB-only refinements

Same file, `2.version-3.1-silverbullet.pine`. Every non-SB path is unchanged;
each item is gated on `sbCtx` / `sbTag*` / `trdIsSb`. Outputs still exactly
64/64 (8 plot + 14 plotchar + 5 bgcolor + 37 alertcondition) — nothing added.
**Still not compiled.** The same static checks were re-run and pass.

| Tag | Module | Change |
| --- | --- | --- |
| SB-9 | 17 | Relaxed same-bar arming, SB path only. Non-SB still needs `lastSslBar == bar_index`; an SB-gated setup may also arm while the sweep is still `inPlay`, within `SB_ARM_GRACE` = 5 bars of it. `sbArmedSslBar` / `sbArmedBslBar` allow one SB arm per sweep so a grace re-arm cannot churn after an invalidation. Quality, preferred-pool and chop-bypass gates untouched. |
| SB-10 | 5 | `sbMemLook = sbCtx ? sweepLook + SB_MEM_EXTRA : sweepLook` feeds `recentSsl` / `recentBsl`. Outside an SB context the value is byte-identical to v3.1. |
| SB-11 | 17 | CE fill = touch **plus** confirmation: `sbCeTapL = sbCeTchL and (close >= ceL or sbRejL)` (short: `close <= ceS`). A wick through the CE that closes back out no longer fills. Proximal-edge fills still need `sbRejL/S` and an entry mode that permits them. |
| SB-12 | 10 / 17 / 19 | Dealing-range **lock**: `sbRngHi` / `sbRngLo` freeze at the open of a new SB window; `sbPdPos` / `sbPdOK` replace `pdPos` / `rangeOK` inside `sbLocOkL/S` only. Cleared when the window has ended and `sbSetLive` (written at the end of MODULE 19, read one bar later) is false. |
| SB-13 | 18 | Conflict hierarchy replaces the mutual kill. Rank 3 SB machine, 2 ordinary machine, 1 pure engine; the higher rank takes the bar, the loser's flags are muted and a same-bar stage-4 entry is rolled back with a reason string. Equal rank still mutes both. |
| SB-14 | 19 | SB exits: break-even after TP1 uses `max(sbBeBuf * atr, SB_BE_TP1_PCT * TP1 distance)`; the post-TP2 trail is capped by `min(low, low[1])` (short: `max(high, high[1])`) as well as by `close`, so it never trails through the last two bars. |

### Known effects to watch

- SB-9 lets the SB clock start on the arming bar, not the sweep bar, so a
  grace-armed setup gets up to 5 extra bars of total life.
- SB-10 also widens `sslInPlay` / `bslInPlay` for the MSS grader on SB bars —
  MSS grades slightly more often inside a window, as V31-FIX-1 already did.
- SB-13 means the losing side's `suL/suS == 4` is rolled back only when the
  entry happened on that bar; an older stage-4 still waits for `trdDir == 0`.
- The lock survives the window close while an SB trade runs, by design.
