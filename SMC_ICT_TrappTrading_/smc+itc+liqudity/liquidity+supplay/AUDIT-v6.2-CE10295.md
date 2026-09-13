# AUDIT v6.2 — CE10295 FIX (MAIN-BODY LENGTH). NOTHING REMOVED.

Deliverable: **`17.liquidty+supply-v6.2-ctt-mtf.pine`** = file 16 (v6.1) with the same code moved out of the script's main body and into functions. Files 13, 14, 15, 16 untouched on disk.

## 1 · What the error actually was

TradingView returned:

```
CE10295 — The main body of the script is too long. Try wrapping code in functions.
```

**This is not the token cap.** The CE10117 that v6.1's own header predicted never appeared, so the compiled-token count was fine all along and that warning was wrong — corrected in the v6.2 header. The real limit is how many statements may sit in the script's **main body** (global scope, including every line nested under a top-level `if` / `for`).

Measured with one counter (a non-comment line at indent 0 that is not a `type` / function declaration, plus every line nested under a top-level block):

| File | main-body statements | raw tokens |
|---|---|---|
| 13 · v5.9 | 2 036 | 43 754 |
| 14 · v6.0 | **2 034** | 43 855 |
| 16 · v6.1 (CE10295) | **2 141** | 46 967 |
| **17 · v6.2** | **2 018** | 46 856 |

v6.1 added ~107 main-body statements to a file already at the cap: four tuple destructures, sixteen `array.from` statements, six `var` arrays, the timeframe gates, and a two-level `for` loop whose ~70 nested lines all count. v6.2 is **16 statements shorter than v6.0**, which is the last main-body size the lineage is known to have accepted.

## 2 · What changed (all of it CRT / TBS / TWS scope, all of it code MOVEMENT)

| Tag | Change | Main body |
|---|---|---|
| **SC-1** | `f_ctt_feed(tf, sec, en, i)` now owns one timeframe's `request.security` **and** its destructure and writes the fourteen values into packed arrays. `f_ctt_proc()` owns the entire `if confirmed` loop — both machines, the marking, the confluence label and the CRT range levels. Main body keeps one seconds line, one init call, four feed calls, one proc call. | ~90 → 7 |
| **SC-2** | State packed: nine arrays → three. `ctt_f` 10 floats/TF, `ctt_i` 5 ints/TF, `ctt_s` 6 marking slots/TF, plus the 24 machine instances and two label arrays. Indices are `i*10+k`, `i*5+k`, `i*6+k` with `i ≤ 3`. | −6 |
| **SC-3** | The v5.8-CTT chart-timeframe marker moved into `f_ctt_chart()`. `cttCrtL / cttCrtS / cttTbsL / cttTbsS` were read nowhere else in the file, so they are locals of that function now. | 19 → 4 |
| **SC-4** | Six-statement blocks folded into one tuple each: `f_ctt_crtCand` (CRT candidate + raw SL), `f_ctt_tbsCand`, `f_ctt_htfCand` (HTF CRT / turtle soup + its invalidation level), `f_ctt_loc` (location filter), `f_ctt_twsRun` (both TWS lifecycles), `f_ctt_swp` (the CRT SWP chip). Every global name a consumer reads — `crtCandLong`, `crtSlLong`, `tbsCandShort`, `hCandCrtLong`, `hSlLong`, `locLong`, `atHtfPoiL`, `twsConfL`, … — still exists, with the same value. | −22 |

`request.security` inside a user function is this file's own existing pattern (`f_bias` does exactly that) and the timeframe argument stays `simple`, so the requests themselves are unchanged: 14 security instances total, under the 40 limit.

## 3 · Nothing was removed

Every engine, state machine, gate, grade, score, alert, plot, input, default and drawing of v6.1 is present. MODULE 11C is intact in full — all four timeframes (15M / 30M / 1H / 4H), all three engines, both directions, the confluence label, the CRT HIGH / EQ / LOW levels, the six new inputs. The v5.8-CTT chart marker is intact. The v6.1 audit's ranked cut levers (MTF-CUT-1 … 4) remain **unused**. No system outside CRT / TBS / TWS was edited: liquidity, S/R, supply/demand, SMC/ICT, FVG/IFVG, OB/breaker/mitigation, CISD, MSS, BOS, CHoCH, OTE, entry, TP/SL/RR, risk, dedupe, sessions, dashboard, debug panel and existing alerts are byte-identical to v6.1.

## 4 · Behaviour and safety

Bit-identical to v6.1: same machines, same thresholds (`crtRangeAtr`, `crtDispAtr`, `crtLife`, `tbsLen`, `tbsAgeMin`, `tbsConfMode`, `twsWaveWin`, `twsDeepen`, `raidMinAtr`, `raidDeepAtr`, `NEAR_LVL_ATR`), same duplicate guard (per-timeframe HTF `time` change + `confirmed` chart bar), same `lookahead_off`, same `[1]` / `[2]` reads inside the request, same FIFO object caps, same `f_cttLvl` budget.

`ta.*` safety: `f_ctt_twsRun` computes the two wave-1 references inside a function that is called **unconditionally** at global scope, so the built-ins advance every bar exactly as the top-level version did — the hazard the file warns about is a `ta.*` call inside a *conditional branch*, which this is not.

Verified mechanically on file 17: no duplicate function / type / global name; every `f_ctt*` / `ctt_*` / `CttM` and every folded global used only after its declaration; all 22 consumer-facing globals still declared; 7 `request.security` source lines / 14 instances.

**Compile: paste it.** If a different CE appears, the header's cut levers and this audit's numbers are the map.
