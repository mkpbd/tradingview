# LQ-SD-PA v3.5 — Professional Operator Review (Bangla)

**ফাইল:** `liqudity_trap_trading.v3.5.txt` (Pine v6, 5,548 lines, 23 modules)
**রিভিউয়ের দৃষ্টিভঙ্গি:** একজন professional FX desk operator-এর চোখে — "এই টুল দিয়ে live execution করলে কোথায় টাকা হারাব, কোথায় edge আছে, কী ঠিক করলে accuracy বাড়বে।"
**তারিখ:** 2026-10-03

---

## ০. এক নজরে verdict

| বিষয় | রায় |
|---|---|
| Architecture | অসাধারণ। Context → Liquidity → POI → Structure → Trigger → Execution — এই chain Pine-এ এত শৃঙ্খলার সাথে খুব কম indicator-এ দেখা যায়। |
| Doctrine fidelity (ICT / SMC) | উচ্চ। Sweep grading, MSS vs CHoCH, dealing range, Silver Bullet windows, CE limit, IFVG, breaker/mitigation — সব আলাদা করে modelled। |
| Execution realism | ভালো, কিন্তু অসম্পূর্ণ। Next-open fill, slippage guard, risk cap, min RR, cost — আছে। **Spread-aware fill/stop নেই**, এটা FX-এ সবচেয়ে বড় ফাঁক। |
| Repaint-safety | একটা সন্দেহজনক জায়গা আছে (HTF `[1] + lookahead_off` idiom) — নিচে P0-1 দেখুন। বাকি সব closed-bar, নিরাপদ। |
| Calibration | **এখনো করা হয়নি।** ফাইল নিজেই বলছে `minScore`, `minRR`, `maxRiskAtr`, governance, symbol profile — সব "reasoned defaults, opinions not measurements"। Live-এ নামার আগে এটা অবশ্যই করতে হবে। |
| Live-ready? | **Demo / forward-test ready, live-ready নয়** — P0 item গুলো ঠিক করে এবং 4–6 সপ্তাহ forward test করে তারপর। |

---

## ১. Indicator-টা আসলে কী করে (feature inventory)

### ১.১ মূল pipeline (MODULE 17 — Master Setup State Machine)

```
IDLE → SWEPT (quality ≥ 2) → AT POI → SHIFTED (MSS/CHoCH) → AWAIT RETEST → ENTRY → ACTIVE → done
```

প্রতিটি stage-এর নিজস্ব clock (`liqWait` 20 / `poiWait` 15 / `retWait` 20 bars), নিজস্ব invalidation reason (sweep undone, reclaim lost, opposing displacement, POI violated, HTF protected swing broken, window closed)। Dashboard-এ কোন gate আটকালো সেটা নামসহ দেখায়।

**Fast path (`fastShift`, 2022 model):** sweep → displaced shift → shift-leg FVG retest। POI tap লাগে না। Raid-ই POI।

### ১.২ Liquidity engine (MODULE 4, 5, 8)

- **Swing sweep:** last pivot high/low wick-through + close back inside, এক level-এ এক event (FIX-W1 latch)।
- **Sweep quality 1–4:** weak / valid / strong / institutional। RAW (candle যা earn করল) আর EFF (MSS upgrade সহ) আলাদা রাখা হয় — A+ tier RAW পড়ে, যাতে MSS নিজেকে নিজে certify করতে না পারে।
- **Engineered pools (kind 2–4):** EQH/EQL (age-out সহ), PDH/PDL (one raid per day latch), Asia/London/NY session H/L (re-raid allowed after 1 ATR walk-off)।
- **Sweep in play:** reclaim ধরে রাখতে হবে (FIX-P0-1) — reclaim হারালে sweep না, breakout।
- PWH/PWL শুধু plot হয়, pool হিসেবে ব্যবহার হয় না।

### ১.৩ Structure (MODULE 6, 7)

- Protected-swing engine internal (`pivLen` 5) + external (`extPiv` 12)।
- BOS / CHoCH / MSS আলাদা; MSS = CHoCH while quality sweep in play, এবং shift raid-এর `TRIG_LOOK` bars-এর ভেতর হতে হবে।
- **HTF bias:** EMA-50 + HTF protected-swing structure, agreement না হলে neutral। Neutral-এ কী করবে তা input (`neutralMode`)।
- HTF protected swing ভাঙলে setup invalid (FIX-T6)।

### ১.৪ POI engines (MODULE 9, 12, 13)

- Chart-TF FVG registry (partial fill, inversion → IFVG, age-out)।
- Zone engine: S/D (FVG geometry + displacement), OB companion, Rejection Block, Breaker/Mitigation flip, IFVG — প্রতিটির kind আলাদা, test-counter দিয়ে "spent" হয়, opposing zone band overlap করতে পারে না।
- HTF FVG POI registry: 3 live slot/side, separate-visit freshness, nearest untested wins within distance window।
- NEXT BUY / NEXT SELL location marker (signal নয়)।
- Dealing range = current leg running extremes, premium/discount clamped 0–100%, OTE 62–79%।

### ১.৫ Trigger candidates (MODULE 14, 15, 16B)

CRT (3-candle), Turtle soup (age-gated), trendline sweep (edge-triggered touches), inside-bar breakout, doji reversal, HTF CRT/TBS, Fractal Entry Model (HTF POI → LTF shift → locked LTF FVG), এবং **Liquidity Trap Engine LT-1…LT-7** (compression/expansion, wick clusters, weak breakout, structural trap, supply rejection) নিজস্ব confidence score সহ। সব একই tier/score/cooldown/lock gate দিয়ে যায়।

### ১.৬ Silver Bullet module (SB-1 … SB-14)

- তিন window (NY time): London 03–04, NY AM 10–11 (priority), NY PM 14–15; pre-window arming grace 15 min।
- Window-specific min sweep quality (London 3, AM 2, PM 3), preferred (engineered) pool required, Asia H/L inside window-এ pool।
- LTF shift model (internal CHoCH/CISD + 0.8 ATR displacement), mandatory clean displacement FVG, **CE limit fill on touch**, dealing range frozen at window open, one entry per window per direction, window-close kill।
- Exit: BE+buffer after TP1, protected-swing trail after TP2, TP3 = liquidity target, time exit at window close, structure exit on opposing MSS/CISD।

### ১.৭ Scoring & tiering (MODULE 16, 18)

- Alignment score 0–100: Context 30 / Liquidity 20 / POI 20 / Trigger 20 (recency decay) / Execution 10, + SB context 0–15 (gate-এ বাদ, display-এ আছে)।
- Tier C / B / A / A+; machine entry minimum A, A+ earned from real components (RAW strong sweep + HTF + MSS + P/D + engineered pool + session + no ADR chase)।
- Final gate: bias, direction lock, killzone, volatility window, cooldown, chop (institutional exception), SB-only, daily governance (max 4 signals / 2 losses), P/D side, min score।
- Conflict hierarchy: SB machine > machine > engine।

### ১.৮ Risk / execution / tracking (MODULE 18B, 19)

- Entry = plan price (CE বা anchor edge), engine signal = next bar open, deferred order re-validated at fill (FIX-X2)।
- Two structural stops (sweep-wick → anchor fallback), risk cap 1.5 ATR (reject or clamp), TP2 = 2R clamped to first opposing POI, min net RR 1.5 (spread+commission ticks input), TP1 = 1R, TP3 = max(3, rr+1)R or liquidity target।
- One tracked trade at a time, max life 80 bars, pessimistic same-bar SL>TP booking, counters (A/A+/TP/SL/exp/untracked)।
- Journal alert() line (pipe-separated) — spreadsheet reconciliation-এর জন্য।

### ১.৯ Context & UX

Symbol profile (FX/XAU/Index/Crypto presets), ADR exhaustion, scheduled volatility windows (calendar নয়), killzones, focus mode drawing budget, dashboard verdict, debug table, 37 alertcondition + rich alert() feed, strategy twin generated by script।

---

## ২. কোথায় শক্তি (operator-এর চোখে)

1. **"Why not" সবসময় জানা যায়।** Verdict row + debug reason — live-এ এটা সোনার মতো। অধিকাংশ indicator চুপচাপ signal দেয় না; এটা বলে কোন gate আটকালো।
2. **Entry price সৎ।** CE limit = touch; confirmation entry = next open; slippage guard; cost-net RR। Chart-এ যা RR দেখায় সেটা মোটামুটি bankable।
3. **Self-certifying loop বন্ধ।** RAW vs EFF sweep grade, MSS binding window, `scoreOnBase` — একই event দুইবার point পাচ্ছে না।
4. **One narrative at a time.** Direction lock + conflict hierarchy + governance — overtrading-এর প্রধান উৎসগুলো code-level-এ বন্ধ।
5. **Invalidation explicit.** Sweep undone, reclaim lost, opposing displacement (retest exception সহ), own-anchor violation, HTF protected swing — doctrine অনুযায়ী ঠিক।
6. **Token/output budget সচেতন refactor** — engine অক্ষত রেখে presentation কাটা হয়েছে, এবং সেটা documented।

---

## ৩. Accuracy-তে যা ঠিক করা দরকার (prioritized)

### P0 — Live-এ নামার আগে অবশ্যই

#### P0-1 · HTF data idiom: `expr[1]` + `lookahead_off` — history vs realtime mismatch (verify করুন)

**কোথায়:** `f_bias`, `f_htfStruct`, `f_crtTbsHtf`, `f_htfPoi`, `pdh/pdl/pwh/pwl`, `adrVal` — সব `request.security(..., expr[1], lookahead_off)` ব্যবহার করে। ফাইলের নিজের note (RETRACTED BUG-N2) দাবি করে এতে "zero extra delay, no repaint"।

**সমস্যা (সম্ভাব্য):** Pine-এ `lookahead_off` historical bar-এ **শেষ confirmed HTF bar**-এর value দেয়, realtime bar-এ **developing HTF bar**-এর value দেয়। তাই `high[1]`:
- historical bar-এ → দুই দিন আগের high (এক দিন extra lag)
- realtime bar-এ → গতকালের high

অর্থাৎ PDH/PDL, HTF bias, HTF POI, ADR — এগুলো replay/backtest-এ যা দেখায়, live-এ তার চেয়ে এক HTF bar আলাদা। Strategy twin-এর সব সংখ্যা এতে প্রভাবিত।

**যাচাই:** Chart-এ `pdh` plot-এর পাশে `request.security(syminfo.tickerid, "D", high[1], lookahead = barmerge.lookahead_on)` plot করুন। Historical bar-এ দুটো আলাদা হলে bug নিশ্চিত।

**সমাধান:** Pine-এর documented non-repainting idiom হলো `expr[1]` **with `lookahead_on`** — history আর realtime দুটোতেই "previous closed HTF bar"। `[1]` রাখুন, `lookahead_on` করুন। `newHtfBar` edge-detect (`hT != hT[1]`) একইভাবে কাজ করবে।

#### P0-2 · Spread-aware fill এবং stop (FX-এর জন্য critical)

**সমস্যা:** Chart = bid price। 
- Buy limit at CE fill হয় যখন **ask ≤ CE**, অর্থাৎ bid ≤ CE − spread। Code `low <= ceL` ধরে → long CE fill overstated। 
- Short-এর stop trigger হয় ask-এ: `high + spread >= SL`। Code `high >= trdSL` ধরে → short stop-out understated। 
- `costTicks` শুধু RR-এ যায়, fill/stop geometry-তে না।

M5 XAUUSD-এ 20–30 cent spread, FVG CE থেকে 0.1 ATR tolerance — এই spread-এর size-এই পার্থক্য হয়। Live-এ "chart বলল fill, broker-এ fill হয়নি" — এর প্রধান কারণ এটাই হবে।

**সমাধান:** একটা `spreadTicks` input (বা `costTicks` থেকে spread অংশ আলাদা):
- Long CE/limit fill: `low <= ceL - spread`
- Short stop: `high + spread >= trdSL`; short TP: `low + spread <= tp` (conservative)
- Long entry at next open: `open + spread`
- Plan RR-এ এই adjustment reflect করুন।

#### P0-3 · Multi-bar sweep ধরা পড়ে না

**সমস্যা:** `sslSweep = low < lastSup and close > lastSup` — একই candle-এ wick + reclaim লাগে। M5 FX-এ খুব সাধারণ pattern: candle 1 close below level (breakdown), candle 2–3 reclaim। Code এটাকে `brokeDn` (breakout, `supBroken` latch) ধরে এবং পরের reclaim-কে কিছুই ধরে না। ফলে অনেক বৈধ "failed breakdown → reversal" setup কখনো arm হয় না।

**সমাধান:** একটা "reclaim sweep" path: `supBroken` latch হওয়ার পর N bars (3–5) এর মধ্যে close back above `lastSup` হলে sweep event stamp করুন, extreme = সেই N bars-এর lowest low, quality = reclaim candle দিয়ে grade। Turtle soup engine-এও একই logic।

#### P0-4 · Calibration এখনো হয়নি

ফাইলের OPEN item। `minScore 50`, `minRR 1.5`, `maxRiskAtr 1.5`, governance 4/2, symbol profiles — কোনোটাই measured নয়। Strategy twin (`liqudity_trap_strategy.txt`) run করে EURUSD/GBPUSD/XAUUSD M5 ও M15-এ অন্তত 6 মাস data-তে: score threshold sweep (40/45/50/55/60), RR 1.25/1.5/2.0, tier A vs A+ only — এগুলোর expectancy টেবিল বানান। P0-1 ঠিক না করে twin চালালে সংখ্যা ভুল আসবে — তাই P0-1 আগে।

### P1 — Execution accuracy

#### P1-1 · ATR shock-এ সব threshold একসাথে প্রসারিত হয়
সব distance ATR(14)-এ scaled। News spike-এর পর 14 bars ATR inflated → zone min height, sweep context, slip guard, risk cap সব একসাথে বড়। Sweep ছোট দেখায়, zone বড় দেখায়। **সমাধান:** ATR-এর বদলে `math.min(atr, 1.5 * ta.sma(atr, 50))` বা median ATR ব্যবহার করুন gating-এ (display-এ raw থাকুক)। `ltLowVol` ইতিমধ্যে `ta.sma(atr,50)` ব্যবহার করছে — একই ধারণা।

#### P1-2 · Partial exit sizing indicator-এ নেই
Trade tracker TP1/TP2/TP3 count করে কিন্তু কত % close হচ্ছে বলে না। Strategy twin 50% at TP1 করে। Indicator-এ `tp1Pct`, `tp2Pct` input যোগ করে label ও journal line-এ দেখান — operator broker-এ একই plan বসাতে পারবে।

#### P1-3 · Position size calculator নেই
`accountSize`, `riskPct` input → `units = (account × risk%) / |entry − SL|` label-এ। Lot conversion instrument-specific, কিন্তু units/risk-money দেখালেই operator-এর execution দ্রুত হয়।

#### P1-4 · Weekend / rollover gap
Deferred order gap-through-stop cancel হয় (ভালো), কিন্তু open trade Friday close → Monday gap-এ SL "touch" হিসেবে pessimistic book হয়। Monday-র প্রথম bar-এ `dayofweek` check করে gap size journal-এ লিখুন; ঐচ্ছিক "no new entry last 2 hours Friday" filter।

#### P1-5 · DST mismatch London window
সব session NY time-এ। US আর UK DST তারিখ আলাদা — বছরে ২–৩ সপ্তাহ London killzone 1 ঘণ্টা সরে যায়। `lonSes` এবং `sbSesLO` এর জন্য `"Europe/London"` timezone option দিন।

### P2 — নতুন confluence (edge বাড়াবে)

#### P2-1 · SMT divergence (correlated pair / DXY)
ICT-এর সবচেয়ে শক্তিশালী confirmation-গুলোর একটা, এখানে নেই। `request.security` budget 7/40 — জায়গা আছে। Input: `smtSymbol` (EURUSD-এর জন্য DXY বা GBPUSD)। Logic: chart sweep করল lastSup, correlated symbol একই window-এ তার low sweep করল না (বা inversely correlated ঐ high নিল না) → `smtBull` → liquidity score +5, A+ requirement-এ optional। Token budget tight — কোনো display feature কেটে জায়গা করতে হবে।

#### P2-2 · PWH/PWL ও monthly levels pool হিসেবে
এখন শুধু plot। kind 3-এ PWH/PWL যোগ করুন (PDH/PDL-এর মতো latch)। Weekly level sweep → Monday/Tuesday reversal — FX-এ উচ্চ-quality raid।

#### P2-3 · True day open / midnight open bias
00:00 ও 08:30 opening lines token budget-এ কাটা হয়েছে। Math সস্তা: `request.security("D", open)` বা session-based open। Rule: price above midnight open → long শুধু discount-এ; below → short শুধু premium-এ। Context score-এ +5 এবং SB entry filter হিসেবে।

#### P2-4 · Day-of-week filter
Monday Asia / Friday NY PM statistically দুর্বল। `dayofweek` input mask — সস্তা, কার্যকর।

#### P2-5 · HTF sweep as context
H1/H4 swing sweep (chart-TF-এর বাইরে) context score-এ নেই। `f_htfStruct` ইতিমধ্যে HTF pivots রাখে — সেখান থেকে HTF sweep flag export করে liquidity score-এ +5।

### P3 — UX / consistency

- **Dashboard header "LQ-SD-PA v3.4"** (MODULE 21) — v3.5 হওয়া উচিত। ছোট কিন্তু live-এ বিভ্রান্তিকর।
- Label-এ full score দেখায়, gate base score পড়ে — label-এ `58 (base 45)` ফরম্যাটে দুটোই দেখান, নাহলে operator ভাবে "58 ≥ 50 তবু signal নেই কেন"।
- `costTicks` default 0 — XAU/index-এ এটা না বসালে minRR gate অর্থহীন। Symbol profile-এ default cost বসান (FX 2 ticks, XAU 25, index 2 points)।
- Strategy twin-এর comment বলে "market entry at signal bar close" — indicator এখন next-open/CE fill করে। `mktwin.py` re-run করে twin sync আছে কিনা যাচাই করুন।

---

## ৪. Logic-level observations (bug নয়, কিন্তু জানা দরকার)

| বিষয় | প্রভাব |
|---|---|
| HTF bias EMA `[1]` — 60m bias, 5m chart | bias flip সর্বোচ্চ 60 মিনিট দেরিতে দেখা যায়। Structure mode এটা কিছুটা পূরণ করে। |
| `bullPin` requires `upWick <= body` | কড়া; অনেক বৈধ hammer বাদ পড়ে। `upWick <= 1.5*body` বিবেচনা করুন। |
| OB শুধু FVG-সহ displacement-এ তৈরি হয় | FVG ছাড়া OB (ICT "OB without imbalance") ধরা হয় না। Doctrine-sound, কিন্তু সচেতন থাকুন। |
| `maxTrdBars` 80 non-SB trade | M5-এ 6.7 ঘণ্টা। M15-এ 20 ঘণ্টা — overnight exposure। Timeframe-scaled করুন (minutes input)। |
| Break-even after TP1 সব trade-এ | Doctrine-ঠিক, কিন্তু BE-stop-out rate বাড়ায়। Twin-এ "BE on/off" compare করুন। |
| Trailing শুধু SB trade-এ TP2-এর পর | Non-SB runner (`nonSbTp3`) 1R lock করে কিন্তু trail করে না। |
| Governance "signals" count করে, fills নয় | untracked signal-ও দিনের কোটা খায়। Intentional, কিন্তু conservative। |
| `sesPts` Asia = 2 | Asia-তে A+ অসম্ভব (sesTierOK false)। সঠিক। |

---

## ৫. Operator playbook (এই version দিয়ে কীভাবে trade করব)

### ৫.১ Recommended settings — EURUSD / GBPUSD M5

| Input | Value | কেন |
|---|---|---|
| Symbol profile | FX majors | ATR constants FX-tuned |
| HTF bias | 60, Structure + EMA, neutral → Follow chart structure | default ঠিক আছে |
| Tier filter | A and above | B edge নয় |
| minScore | 50 (calibrate!) | FIX-T18 |
| costTicks | 2–3 (spread+comm) | gate বাস্তব হোক |
| SB enable | ON, London qual 3, AM 2, PM 3 | doctrine |
| useKZ | **ON** | FX-এ off-hours signal noise |
| Governance | 3 signals / 2 losses | FX desk standard |
| maxRiskAtr | 1.25 | FX M5-এ 1.5 ATR stop প্রায়ই অতিরিক্ত |
| Volume confirmation | OFF | tick volume দুর্বল |

### ৫.২ XAUUSD M5

Profile Metals, `costTicks` 25–30, `maxRiskAtr` 1.5, `SL_PAD` 0.35 (profile দেয়), `slipGuard` 0.5। ADR exhaustion ON রাখুন — gold-এ "chasing the 120% day" সবচেয়ে বড় loss source।

### ৫.৩ Daily routine

1. **Pre-session (London 02:00 NY):** Dashboard — regime, bias, next demand/supply distance, ADR %। CHOP হলে শুধু SB window-এ কাজ।
2. **Signal এলে checklist (30 সেকেন্ড):** label tier A/A+? Score base ≥ threshold? Verdict row-এ কোনো suffix (locked / conflict)? Spread এখন normal? News 15 মিনিটের মধ্যে? — একটাও না হলে skip।
3. **Order:** CE fill হলে label-এর E price-এ limit (spread adjust করে), SL ঠিক label-এর SL-এ, TP1 50% close, TP2 বাকি (SB হলে TP3 runner)।
4. **Post-trade:** Journal alert line spreadsheet-এ paste। সপ্তাহ শেষে per-source (SB/MC/LT/ENG) expectancy দেখুন — দুর্বল source off করুন।

### ৫.৪ যেগুলো কখনো trade করবেন না (এই indicator-এ)

- B / C tier (default-এ hidden, রাখুন)।
- "waiting" verdict-এ anticipating entry — NEXT BUY/SELL marker signal নয়।
- Volatility window-এর ভেতর (newsAllowSb শুধু NY AM SB-এর জন্য)।
- Dashboard "CHOP" + non-institutional sweep।

---

## ৬. Implementation roadmap (সুপারিশ)

| Phase | Items | কাজ |
|---|---|---|
| **A (1–2 দিন)** | P0-1 verify+fix, P3 header, P3 cost defaults | ছোট edit, কিন্তু সব সংখ্যা ঠিক করে |
| **B (2–3 দিন)** | P0-2 spread-aware fills/stops, P1-1 ATR cap | execution accuracy |
| **C (2–3 দিন)** | P0-3 multi-bar sweep | signal coverage |
| **D (1 সপ্তাহ)** | P0-4 calibration via twin: 3 symbols × 2 TF × 6 months | থ্রেশহোল্ড measured হবে |
| **E (optional)** | P2-1 SMT, P2-2 PWH/PWL, P2-3 midnight open, P2-4 DOW | token budget থেকে display feature কাটতে হবে |
| **F (4–6 সপ্তাহ)** | Demo forward test, journal reconcile vs broker | live-এর আগে শেষ gate |

**Token budget সতর্কতা:** v3.2.2 এবং v3.4 দুবারই compiled-token ceiling (100,256) ছুঁয়েছে। P2-এর কোনো feature যোগ করতে হলে আগে ঠিক করুন কী কাটবেন (candidates: trendline engine, inside-bar/doji triggers — এগুলো lowest-tier source, twin-এ expectancy দেখে সিদ্ধান্ত)।

---

## ৭. শেষ কথা

এটা indicator নয়, একটা trading system-এর rule engine। Doctrine layer প্রায় সম্পূর্ণ; যা বাকি তা **measurement** (calibration) আর **broker-reality** (spread, HTF idiom)। P0 চারটা ঠিক করে twin চালালে এটা একটা দায়িত্বশীল operator-এর primary decision-support tool হতে পারে। তার আগে live money নয়।

---

## ৮. v3.6 — কী apply হয়েছে (`liqudity_trap_trading.v3.6.txt`)

v3.5 ফাইল অক্ষত। নতুন ফাইলে নিচের item গুলো গেছে। **Design rule:** কোনো নতুন `if` scope নয় (সব ternary/assignment), কোনো নতুন plot/plotchar/bgcolor/alertcondition slot নয় (62/64 অপরিবর্তিত), `request.security` 7/40 অপরিবর্তিত। Token offset: dashboard + debug table-এর ~40টা চার-argument `table.cell` call একটা `f_cell` helper-এ — presentation only।

| Review item | v3.6 tag | কী হয়েছে | Behaviour change |
|---|---|---|---|
| P0-1 HTF idiom | FIX-Y1 | 7টা `request.security` → `lookahead_on` (সব expression আগেই `[1]`-shifted ছিল) | History-তে PDH/PDL, HTF bias, HTF POI, CRT/TBS, ADR এক HTF bar আগে আসবে; live অপরিবর্তিত। Backtest সংখ্যা বদলাবে — এটাই উদ্দেশ্য। |
| P0-2 Spread | FIX-Y2 | `spreadIn` (ticks, default 0 = off); `hiA/loA = high/low + spread`; long CE fill `loA <= CE`, long next-open fill `open + spr`, long non-limit plan `+ spr`, short stop `hiA >= SL`, short TP `loA <= TP` | Default 0 → v3.5 identical। Set করলে long fill কম, short stop-out বেশি — বাস্তবের মতো। |
| P0-3 Multi-bar sweep | FIX-Y3 | `reclaimBars` (default 4); break-এর পর N bar-এর মধ্যে close back = sweep; extreme = break-পরবর্তী lowest/highest; `f_sweepQual(isLow, ext)` | নতুন sweep event বাড়বে (failed breakdown/breakout)। Break latch অপরিবর্তিত → structure engine একই। |
| P1-1 ATR cap | FIX-Y4 | `atrCapIn` 1.5 × SMA(ATR,50); gating `atr` capped | Vol shock-এর 14 bar-এ threshold গুলো আর inflate হবে না। 0 = off। |
| P2-4 DOW filter | FIX-Y5 | `tradeDays` "23456" → `dowOK` final gate-এ + verdict "day filter" | Default Mon–Fri; Sun/Sat intraday বন্ধ। |
| P2-2 PWH/PWL pools | FIX-Y6 | kind 3 stamp + daily-style latch; engineered memory; SB TP3 target scan; plotchar/alert merged with PDH/PDL | Weekly level raid এখন arm করতে পারে। |
| P3 surface | FIX-Y7 | Label: `58 (base 45)` যখন SB bonus আছে; entry label `≈ units` (`riskMoney`); TP1 label `· 50%` (`tp1Pct`); dashboard header v3.6; debug row-এ spread | Display only। |

**Deferred (token/evidence-এর অপেক্ষায়):** P1-2 twin re-sync (`mktwin.py` re-run করুন), P1-4 weekend gap, P1-5 London DST tz, P2-1 SMT, P2-3 true-day-open, P2-5 HTF sweep।

### ৮.১ Token pass (CE10117 — first build 100,751 / 100,256)

প্রথম build 495 token over ছিল। নিচের cut গুলো করা হয়েছে — সব presentation / mirror-fold / dead code / default-OFF option; **default setting-এ কোনো gate, score, tier, zone, sweep বা exit rule বদলায়নি**:

| Cut | ধরন | আনুমানিক সাশ্রয় |
|---|---|---|
| `f_tier(isLong)` — long/short tier grader এক function | mirror fold | ~50 |
| `f_gateKill(isLong)` — final-gate reason এক function (+ "day filter" reason) | mirror fold | ~60 |
| `f_flipZone(z, toSupply, isBrk)` — breaker/mitigation flip এক function | mirror fold | ~95 |
| `engOKL/S` — 20টা engine gate line-এ এক bool | fold | ~20 |
| Trade-plan drawing: এক delete pass | fold | ~60 |
| Dead: `sbRemBar`, `sbTfMin`, `ltShowScore`, `cntSbTime/Struct`, CISD run-length tuple | dead code | ~55 |
| Legacy "Touch + hold (v3.2.1)" CE fill mode + `sbCeTol` সরানো | legacy option | ~80 |
| LT hard gates MSS/CHoCH/FVG/S-D/OB সরানো (সব default OFF, `f_ltScore`-এ আগেই weighted) | default-OFF option | ~120 |
| LT "armed" chips সরানো (default OFF) | default-OFF display | ~45 |
| 3 killzone bgcolor → 1 slot | output | ~30 |
| "Session level broken" 2 plotchar + 5 context alertcondition (Ext BOS, CISD, IFC, session broken, TL break) | output | ~100 |
| SB alert() feed: "armed" / "FVG locked" message | alert text | ~80 |
| Dashboard/debug tooltips, debug header row, Machine L/S merge | display | ~120 |
| নতুন 5 input-এর tooltip | display | ~15 |

| **Second pass (margin):** CISD/IFC study chips (default OFF), legacy `engFillMode`/`mcFillMode`/`sbShiftSrc` option, `scoreOnBase` toggle (gate সবসময় base), NEXT-label "Right edge" option, `f_size` mapper | legacy / default-OFF / fold | ~210 |

মোট আনুমানিক ~1,140 token (দরকার ছিল 495)। Output budget এখন 8 plot + 12 plotchar + 3 bgcolor + 30 alertcondition = **53/64**।

> **Paste সতর্কতা:** দ্বিতীয়বার যে error screenshot এসেছে তাতে সংখ্যা **100,751 — প্রথম build-এর হুবহু একই**। প্রথম cut pass-এর পর এটা অসম্ভব; অর্থাৎ TradingView editor-এ পুরনো code ছিল। Editor-এর সব text মুছে `liqudity_trap_trading.v3.6.txt`-এর **সম্পূর্ণ** content paste করুন (file ~5,560 line; header-এ "second pass (margin)" লাইন থাকলে সঠিক file)।

**যা হারালেন:** LT engine-এর 5টা optional hard gate (score দিয়ে একই কাজ হয়), SB legacy fill model, 5টা context alert, session-broken marks, tooltip hover text। **যা পেলেন:** 11টা output slot খালি — ভবিষ্যতে SMT/TDO যোগ করার জায়গা।

**আবার CE10117 এলে পরের cut (ক্রমে):** (a) `f_dbg` debug table পুরো body, (b) `showCisd/showIFC` chips (default OFF), (c) inside-bar + doji trigger engines (lowest-tier source — twin-এ expectancy দেখে)।

### ৮.২ Compile checklist

1. **Local scope** error এলে: v3.6 নতুন `if` যোগ করেনি; pdh/pdl latch reset ternary (−2), LT chips (−2), zone flip body function-এ (−0), trade-plan delete merge (−1)।
2. **FIX-Y1 verify:** `pdh` plot-এর পাশে পুরনো v3.5 চালিয়ে historical bar-এ তুলনা করুন — v3.6-এ PDH সঠিক দিনে দেখা উচিত।
3. **Spread default 0** — `spreadIn` tick-এ (= `syminfo.mintick`)। Chart-এর trading panel-এ BUY − SELL পড়ুন **London/NY session চলাকালে**, tick দিয়ে ভাগ করুন। EURUSD 5-digit ≈ 10 · OANDA XAUUSD (tick 0.001) ≈ 250–350 · OANDA NAS100 (tick 0.1) ≈ 10–15 · OKX BTC perp (tick 0.1) ≈ 1। `costTicks` তখন commission-only।
4. Strategy twin: header `scripts/mktwin.py` আর `liqudity_trap_strategy.txt`-এর কথা বলে, কিন্তু এই folder-এ কোনোটাই নেই। Script আগে খুঁজে বের করুন (অন্য folder/branch); না পেলে twin = v3.6 file-এ `indicator()` → `strategy()` + MODULE 19S হাতে বসাতে হবে। Detection code বদলেছে — পুরনো twin-এর সংখ্যা আর এই chart-এর সংখ্যা এক নয়।

### ৮.৩ Compile ফলাফল + প্রথম live read (2026-10-03)

**Compile OK।** BTCUSDT.P (OKX), XAUUSD (OANDA), NAS100USD (OANDA) — তিনটা M5 chart-এই dashboard header `LQ-SD-PA v3.6`। আগের তিনবারের 100,751 ছিল editor-এ পুরনো code (§8.1 Paste সতর্কতা) — নতুন code প্রথমবারেই ceiling-এর নিচে।

Screenshot-এর সময় শনিবার 00:54 NY (10:54 UTC+6)। তিন chart-এর dashboard যা বলছে, আর তা ঠিক কিনা:

| Chart | Dashboard | পড়া |
|---|---|---|
| BTC | `Verdict: NO · day filter · ADR 13% (early)` · bias `▼ Bear · D ▲ · str ▲ → —` · `L 30 (C) S 33 (B)` | **ঠিক।** শনিবার → `tradeDays "23456"` block করেছে (FIX-Y5)। Crypto 24/7 trade করলে `tradeDays = "1234567"`; FX/metal/index-এ default-ই থাকুক। Bias neutral (EMA bear, structure bull) → `neutralMode` "Follow chart structure" → ext ▼ → short side only। |
| XAU | `Verdict: NO · score 29 < 50 · ADR 130% no-chase▼` · bias সব `▼ Bear` · `L 0 (C) S 29 (B)` · FEM `FVG locked` | **ঠিক।** Friday close। L 0 = context 0 (bias bear, ext bear, off-hours, Prem 52%) + demand 2.3 ATR দূরে (> `POI_NEAR_ATR` 1.5)। `no-chase▼` = দিন 130% ADR চলেছে, price নিচের 30%-এ → short-এ −10 ও A+ নেই। |
| NAS | `Struct · sweep: int ▲ ext ▲ · BSL valid` · bias সব `▲ Bull` · `Verdict: NO · score 40 < 50 · ADR 106%` | **ঠিক।** BSL sweep in play কিন্তু bias bull → `biasOkS` false, short arm হয়নি (FIX-T14)। Verdict long side-এর 40 দেখাচ্ছে (bestScore)। |

Verdict row প্রতিবার সঠিক gate-এর নাম বলছে (FIX-P1-10 / FIX-W4 / FIX-Y5 কাজ করছে)। Range pos তিনটাতেই 0–100%-এর ভেতরে (FIX-P1-9)। কোনো anomaly চোখে পড়েনি।

**Spread — screenshot থেকে মাপা (weekend quote, চওড়া):** XAU BUY−SELL 4141.250 − 4139.790 = 1.46 → tick 0.001 → **1460 ticks** (session-এ ~300); NAS 30829.6 − 30825.8 = 3.8 → tick 0.1 → **38 ticks** (session-এ ~10–15); BTC 0.1 → **1 tick**। `spreadIn` session-এর মান দিয়ে বসান, weekend-এর নয়।

**এখনো বাকি:**
1. FIX-Y1 যাচাই (§8.2 item 2) — PDH line সারাদিন flat, শুধু 00:00 NY-তে step; v3.5 পাশে চালিয়ে historical bar-এ তুলনা।
2. `spreadIn` / `costTicks` per symbol (উপরের সংখ্যা)।
3. Strategy twin (§8.2 item 4) — script এই folder-এ নেই।
4. P0-4 calibration — twin ছাড়া হবে না।
