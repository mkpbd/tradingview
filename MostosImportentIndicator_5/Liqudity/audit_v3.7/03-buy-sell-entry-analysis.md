# 03 — BUY / SELL Entry Analysis · LQ-SD-PA v3.7

তারিখ: 2026-10-10। Long আর short mirror (line-by-line যাচাই); নিচে long লেখা, short উল্টো। Classification analytical — profitability-র দাবি নয়।

## 1. Machine — ordinary path (`sigMCLong`, `sbTagL == 0`) — **High-quality candidate (conditional)**

| প্রশ্ন | উত্তর (code) |
|---|---|
| পূর্বশর্ত | `sslInPlay` (reclaim ধরে রাখা sweep ≤ 12 bar, ≤ 3 ATR) + `lastSslQual >= 2` + `biasOkL` + `lockOkL` + chop নয় (4114–4117) |
| Liquidity | swing low (pivLen 5) / EQL / PDL / PWL / London-NY session low (1597–1830); `lastSslLvl`, wick `lastSslExt` |
| Confirmation | stage 2 POI tap (zone / HTF POI) **অথবা** `fastShift` → stage 3 shift (external CHoCH বা MSS, body ≥ 0.5 ATR) 4132, 4151 |
| Structure shift | `eChochUp` = displaced close > external protected high (1904) — valid, latch-free |
| Displacement | shift body ≥ `structDisp` 0.5 ATR; FVG anchor-এর middle candle displacement নয় (ordinary path-এ `sbFvgOkL` লাগে না, 4162) — **CE anchor incidental FVG হতে পারে** |
| Entry location | CE (50%) of shift-leg FVG, resting limit, `loA <= ceL` 4204; fallback confirmation candle close ≥ CE + outer 30% (4212) |
| Late? | না — retest-ভিত্তিক। `ripeL` = shift bar-এর পরের bar (4178)। `retWait` 20 bar। |
| Room | TP2 clamp শুধু POI zone (D8) |
| Stop | min(low, anchor bottom, sweep wick) − 0.25 ATR; cap ভাঙলে anchor stop (4229–4231) — logical |
| RR | net ≥ 1.5 to TP2 (4607) |
| Invalidation | close < sweep wick · reclaim lost (stage ≤2) · opposing 1.2-ATR candle (stage ≤2, stage 3 শুধু close < anchor) · anchor FVG close-through · HTF protected low · expiry |
| OOS | **মাপা হয়নি** (D3) |

**দুর্বলতা:** (i) grade-2 sweep সস্তা (02 §D.2); (ii) D10 neutral deadlock; (iii) D20 decay clock; (iv) CE anchor incidental FVG হতে পারে — `sbFvgOkL`-এর মতো displacement check ordinary path-এও চাই; (v) reversal-only।

**Typical entry-bar score (NY session, HTF agree, discount, fresh anchor, MSS 3 bar আগে, CE touch, confirmation নেই):** ctx 30 + liq 15–20 + poi 15 + trig 9 + exec 0 ≈ 69–74 → pass। Off-hours + neutral + no P/D: ≈ 49 → **fail at 50**। `minScore` কার্যত "context gate"।

## 2. Machine — SB path (`sbSigLong`) — **High-quality candidate (window-bound)**

- Arm: SB context (window ± 15 min pre), `lastSslQual >= sbMinQual` (London 3, AM **2**, PM 3), preferred pool kind ≥ 2 (EQ/PD/session; Asia inside window) 4000।
- Shift: `sbShiftUp` = MSS / ext CHoCH / (internal CHoCH or CISD) + 0.8 ATR body (4032)। Raid = POI, stage 1→3।
- Anchor: clean displacement FVG only (`sbFvgOkL` 4048), CE limit 4195, proximal edge শুধু rejection candle।
- Gates: HTF bias, P/D off **locked** range (4198), tier ≥ A (sbMinTier), window-close kill, 1 entry/window/direction।
- Exit: BE after TP1 (adaptive), trail after TP2, TP3 liquidity target, time exit, structure exit।

**দুর্বলতা:** NY AM min grade 2 + pool grade floor 2 (D18) → 1-tick PDH poke 10:02-এ "valid preferred pool"। `sbQualAM` 3 করে measure করুন।

## 3. FEM (`sigFEMLong`) — **Conditional candidate**

- HTF FVG tap (fresh লাগে না, 3291) → LTF `cisdUp or chochUp or bosUp or mssUp` (3297, **bosUp-ও shift**) → locked FVG → retest + `zoneBullConf` (3312, CE-past close লাগে না D13)।
- Sweep লাগে না; HTF bias শুধু final gate-এ। Stop: min(low, FVG bottom) − pad — ঠিক।
- Tier A পেতে sweep + trigger লাগে (engine candidate) → বাস্তবে FEM তখনই fire করে যখন machine-এর শর্তও প্রায় পূরণ। Redundant-ish।

## 4. Zone 50% (`sigSDLong`) — **Conditional candidate**

- Zone = displacement FVG (creation 2903), ≤ 2 separate tests, 50% tap edge-triggered, ≤ 5 bar-এ `zoneBullConf` (2858)। Close zone-এর ভিতরে থাকলেও signal।
- Tier A: sweep in play + in-zone + recent CHoCH/CISD + exec। পাস করলে ভালো location। Stop: min(low, zone bottom) − pad — ঠিক।
- দুর্বলতা: confirmation candle anchor-specific নয় (FIX-X9 নেই); D9 internal CHoCH trigger।

## 5. Turtle soup (`sigTBSLong`) — **Conditional candidate**

- 20-bar low (age 4–60) wick-through + close > level + bull + close ≥ mid (3122)। Stop low − pad। Fill next open।
- Location ভালো (reversal candle), retest নেই। Tier A লাগে (sweep in play হবে by construction, POI + trigger লাগে)।

## 6. CRT (`sigCRTLong`) — **Low-quality (late)**

- Candle-3 displaced close > candle-2 high → fill next open (3111)। Stop low[1] − pad। Candle-3 ≥ 0.5 ATR body → entry ≥ 0.5–1 ATR above the reclaim → risk প্রায়ই cap/RR-এ reject। Tier A না পেলে বন্ধ। Chasing by design।

## 7. HTF CRT / HTF Turtle soup — **Invalid (D1)**

- নিজস্ব stop নেই → 2-bar low। Fire 1 LTF bar after HTF close। Fix না হওয়া পর্যন্ত **বন্ধ রাখার সুপারিশ** (`useHtfCrt = false`)।

## 8. Trendline sweep (`sigTLLong`) — **Low-quality**

- Internal pivot pair line, 2 approaches, wick below + conf (3157)। Stop low − pad। Trendline liquidity concept ঠিক, কিন্তু 5-bar pivot line noise; `tlNeedConf` on default।

## 9. Inside bar (`sig3Long`) — **Invalid (D1) / Low**

- Mother = `brokeUp` bar ≥ 1 ATR body, inside bar upper half, break close strong (3207–3216)। Stop নেই → 2-bar low। Continuation breakout, fill next open = chase। Tier A প্রায় অসম্ভব (sweep লাগে)।

## 10. Doji reversal (`sig4Long`) — **Invalid (D1) / Low**

- 3+ doji in 5, compressed, level raided, drift down, bull conf + 0.5 ATR body (3265)। Stop নেই → doji-র নিচে না, 2-bar low। Logical stop = `lastSup − pad`।

## 11. Liquidity trap (`sigLTLong/Short`) — **Conditional candidate**

- LT-1 (long): compression ≤ 2 ATR under `lastRes` → 1.2-ATR break → retest ≤ 0.5 ATR → later-bar confirmation (3876)। এটাই একমাত্র BOS+retest model।
- LT-2/5/6 (short): weak-body poke above level → close back below → bear conf। Failed-breakout model, যুক্তিসঙ্গত।
- LT-3/4: wick-cluster pools। LT-7: supply rejection।
- Score 0–100, floor HIGH (70)। Context gate + bias + lock।
- দুর্বলতা: stop D5; veto D6; Tier A-র জন্য sweep লাগে → LT-1 default-এ প্রায় মরা; `f_ltScore` correlated (sweep 20 + MSS 20 + disp 10)।

## 12. Common gates — কোথায় early / late

| Gate | ফল |
|---|---|
| Engine fill next open | সঠিক realism; label bar-এ, fill পরে — "late by one bar" by design |
| CE limit | fill intrabar, label bar close-এ → alert late (D19) |
| `slipGuard` 0.5 ATR | confirmation path-এ runaway bar reject — ঠিক |
| `maxRiskAtr` 1.5 reject | wide sweep-wick stop → anchor stop fallback — ঠিক |
| `minRR` 1.5 net | ঠিক; cost default 0 → gross |
| `masterCd` 15 | একই দিকে 15 bar — SB override |
| `govOK` | 4/day, 2 losses — BE loss নয় (FIX-Z10) |

## 13. Model support matrix (Phase 5)

| Model | Supported? | কোথায় | কী নেই |
|---|---|---|---|
| A — Sweep reversal | ✅ পুরো | Machine ordinary + SB | pool grade floor, D8 target liquidity |
| B — BOS + retest | ⚠️ আংশিক | LT-1 only (internal level) | machine-এ BOS shift নয়; HTF context নেই; tier A বাধা |
| C — FVG/OB retrace | ⚠️ আংশিক | FEM; zone 50%; machine stage-3 CE | OB শুধু bar[2]; FEM lax exec |
| D — Trend continuation | ❌ | — | machine CHoCH-only; IB/CRT trigger-only, stop নেই |

**সৎ কথা:** এই indicator-এর শক্তি Model A। B/C/D দাবি করা যায় না।

## 14. MTF alignment (Phase 6)

- Bias TF: `biasFilter` (60 default) < chart হলে chart (FIX-Z5)। EMA-50 + structure agree, else neutral। Neutral handling: D10।
- HTF engines: auto (M5→60, M15→240, 60→D)। `htfLive` guard।
- HTF POI → LTF: security tuple, 3 slots, visit count — mapping ঠিক।
- HTF protected swing invalidates (FIX-T6) — ঠিক।
- Contradiction: `sbReqHtf` locked range vs live `mcPdOKL` — SB override skips mcPd (intended)।
- সুপারিশ (অনুমান, test লাগবে): M5 entry / 60 bias / 240 POI (FX, XAU); M15 / 240 / D (indices, BTC)। "universal" নয়।
