# TOKEN LOG — V8_ENGINE.pine (probe method: V8_BUILD_PROCESS_BN.md §2.3)

| Phase | Date | Compiled tokens | Headroom (100,256 −) | Note |
|---|---|---|---|---|
| P0 | 2026-09-17 | ? | ? | run probe after first compile |
| v8.0.0 (file A complete) | 2026-09-17 | compiles, number pending | ? | user: compile OK, no CE10117 · probe number still to fill |
| v8.0.0-B `V8_CONTEXT.pine` | 2026-09-17 | compiles, number pending | ? | user: compile OK · 10 request.security |
| v8.0.0-full `V8_FULL.pine` | 2026-09-17 | compiles (< 100,256) | unknown, > 0 | user: "ok" — engine + context fit in ONE script. V8_FULL is now the main file |
| v8.0.1 funnel (before cut) | 2026-09-17 | **100,511** | −255 (CE10117) | first real measurement · V8_FULL + funnel rows |
| v8.0.1 funnel (after cut) | 2026-09-17 | compiles, est. ~98k | est. ~2k | cut 3 panel rows + 23 tooltips + dead vars · headroom thin — any new feature must cut first |
| v8.0.3 funnel+MSS (before cut) | 2026-09-17 | **100,602** | −346 | cut opening lines, run chips, AMD/Judas, sesStory, Targets row → compiles |
| v8.0.5 | 2026-09-17 | compile pending | est. ~0–500 | +MSS fallback loop, +array.sum, −7 helpers · net chars +28 |
| v8.0.5 | 2026-09-17 | compiles | unknown, > 0 | user: XAU 5m OK |
| v8.0.6 | 2026-09-17 | compile pending | est. thin | +fb loop always, +2nd kill reason · net chars +~400 |
| v8.0.6 | 2026-09-17 | compiles | unknown, > 0 | user: 4 symbols OK |
| v8.0.7 | 2026-09-17 | compile pending | est. thin | −reclaim kill, −f_poolBrkBar, +entry on label · net chars ≈ 0 |
