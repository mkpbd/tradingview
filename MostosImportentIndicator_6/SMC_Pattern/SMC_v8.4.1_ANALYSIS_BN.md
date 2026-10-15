# SMC / ICT Suite v8.4.1 — গভীর বিশ্লেষণ (কী কী ব্যবহার করা হয়েছে)

> ফাইল: `SMC_v8.4.1.txt` · 3862 লাইন · Pine Script v6 · `indicator(..., overlay = true)`
> বিশ্লেষণের তারিখ: 2026-10-15 · এই ফাইল `MostosImportentIndicator_5/SMC_Pattern/SMC_v8.4.1.txt`-এর সাথে হুবহু এক (byte-identical)।

---

## সূচিপত্র

1. [এক নজরে](#1-এক-নজরে)
2. [আর্কিটেকচার — লেয়ার (L0–L7)](#2-আর্কিটেকচার--লেয়ার-l0l7)
3. [ব্যবহৃত Pine ফিচার ও রিসোর্স বাজেট](#3-ব্যবহৃত-pine-ফিচার-ও-রিসোর্স-বাজেট)
4. [Data type (UDT) — ১৫টি](#4-data-type-udt--১৫টি)
5. [L0 — Candle pattern](#5-l0--candle-pattern)
6. [L1 — Market structure (BOS / CHoCH / CISD)](#6-l1--market-structure-bos--choch--cisd)
7. [L2 — FVG ও Move strength](#7-l2--fvg-ও-move-strength)
8. [L3 — Liquidity](#8-l3--liquidity)
9. [L4 — Zone (OB / BRK / RCB / RJB / QM / KL)](#9-l4--zone-ob--brk--rcb--rjb--qm--kl)
10. [L5 — HTF (Higher Timeframe)](#10-l5--htf-higher-timeframe)
11. [Premium/Discount, OTE, Session, NY Open](#11-premiumdiscount-ote-session-ny-open)
12. [অন্যান্য feature (trendline, wick sequence, break state)](#12-অন্যান্য-feature)
13. [Entry trigger — POI state machine (IMMEDIATE / CONFIRMED / MSS)](#13-entry-trigger--poi-state-machine)
14. [L6 — Setup module (M01–M73) পূর্ণ তালিকা](#14-l6--setup-module-পূর্ণ-তালিকা)
15. [Setup filter ও gate](#15-setup-filter-ও-gate)
16. [L7 — Trade engine (Entry / SL / TP / R:R)](#16-l7--trade-engine)
17. [Scoring system (tier × 2 + confluence)](#17-scoring-system)
18. [Signal বাছাই ও duplicate দমন](#18-signal-বাছাই-ও-duplicate-দমন)
19. [Drawing — label, line, box, panel, legend](#19-drawing)
20. [Alert ও Data window](#20-alert-ও-data-window)
21. [সব Input — group অনুযায়ী](#21-সব-input)
22. [সরানো (CUT) module ও feature](#22-সরানো-cut-module-ও-feature)
23. [পর্যবেক্ষণ — dead code, অসঙ্গতি, ঝুঁকি](#23-পর্যবেক্ষণ)

---

## 1. এক নজরে

| বিষয় | মান |
|---|---|
| ধরন | Overlay indicator (strategy নয়) |
| মোট setup module (toggle) | **36** (signal দেয় 35টি; M64 শুধু trendline আঁকে) |
| Default ON signal module | **25** |
| `request.security` কল | **3** (HTF tuple · Daily · Weekly) |
| `plot` (data window) | **13** + `bgcolor` 1 |
| `alertcondition` | **11** + dynamic `alert()` 2 |
| Input | ~140টি, 16টি group-এ |
| Table | 2 (Info panel 15 row · Legend 8 row) |
| Drawing cap | labels 500 · lines 500 · boxes 500 (FIFO) |
| Repaint নিয়ন্ত্রণ | FVG, zone, signal, alert — সব `barstate.isconfirmed` gated; HTF `[1]` + `lookahead_on` |

**মূল দর্শন:** "Feature-vector architecture" — প্রতিটা লেয়ার প্রতি bar-এ **একবার** চলে, flag লেখে (`Cndl` / `Struct` / `Feat`); প্রতিটা setup শুধু একটা boolean expression যা ওই flag পড়ে।

---

## 2. আর্কিটেকচার — লেয়ার (L0–L7)

```
L0 candle  ─► L2 FVG ─► L1 structure ─► (move strength)
                                 │
            Asia SESH/SESL ─► L3 liquidity ─► L4 zones ─► L5 HTF ─► gate
                                                                   │
        PD array · arrival · wick seq · break state · trendline · POI machine
                                                                   │
                      L6 setups (M01…M73) → f_bid → best LONG / best SHORT
                                                                   │
                      L7 f_sig (entry/SL/TP/RR/score) → gap/identity filter
                                                                   │
                           label · trade lines · panel · alert · data window
```

Orchestration ক্রম (লাইন ~2246–2316):
`f_candle` → `f_fvg` → `f_structure` → `f_moveStrength` (event-only) → session/Asia level → `f_liq` → `f_zones` → `f_htf` → `f_gate`।

State রাখার জায়গা:
- `Ctx` — মূল mutable state (254-element UDT cap-এ পৌঁছে গেছে)
- `Sx` — S–AB state machine + structure pending + POI + HTF FVG (Ctx overflow)
- `Feat` (`ft`) — প্রতি bar-এ নতুন feature vector

---

## 3. ব্যবহৃত Pine ফিচার ও রিসোর্স বাজেট

| Pine ফিচার | কোথায় ব্যবহার |
|---|---|
| `type` (UDT) | 15টি — config, state, feature, signal |
| `array<UDT>` | `fvgs`, `lv` (liquidity), `zones`, `labs`, `lns`, `hLines`, `tradeLns` |
| `box.*` | FVG box, zone box (text সহ), style আপডেট |
| `line.*` | liquidity, BOS/CHoCH/CISD/sweep, major H/L, HTF OHLC, trendline, trade line |
| `label.*` | signal / event label (tooltip সহ), liquidity text |
| `table.*` | Info panel (bottom-right), Legend (top-right) |
| `request.security` | HTF: `[O,H,L,C][1..2]`, pivot H/L, `high[3]/low[3]` · `"D"` PDH/PDL · `"W"` PWH/PWL |
| `timeframe.change`, `timeframe.in_seconds` | HTF নতুন bar, auto pairing |
| `time(tf, session, tz)` | Asia / London / NY killzone, NY midnight |
| `ta.atr / pivothigh / pivotlow / highest / lowest / sma` | ATR, swing, ext range, PD leg, MSS, vol |
| `syminfo.type / mintick / timezone` | forex/cfd auto-killzone, min risk tick |
| `alert()` + `alertcondition()` | dynamic + static alert |
| `plot(display = display.data_window)` | diagnostic |
| `chart.fg_color` | zone text theme-safe |
| `str.format / str.contains / str.replace` | alert message, M10 tier, label text |

হেডারে দেওয়া object budget: labels 230/500 · lines 196/500 · boxes 100/500 · security 3/40।

---

## 4. Data type (UDT) — ১৫টি

| Type | ভূমিকা | মূল field |
|---|---|---|
| `Cfg` | সব input একটা object-এ (R2 rule) | ~60 parameter |
| `Vis` | রং, transparency, size | bull/bear/pool/brk/rcb/rjb/qm/htf |
| `Cndl` | L0 candle anatomy | body, wick ratio, pin, doji, engulf, inside, harami, star, IFC, manip |
| `Struct` | L1 output | BOS, CHoCH, internal, weak, sweep, PB, CISD, `chLvl/chIdx`, trend, movePhase |
| `Fvg` | একটা FVG | top/bottom/idx/isBull/mitigated/box |
| `Move` | একটা leg-এর শক্তি | strong, fvgCount, bodyEff, mixed, speed, avgBody |
| `Liq` | একটা liquidity level | price, kind (BSL/SSL/EQH/EQL/PDH/PDL/PWH/PWL/SESH/SESL), touches, pooled, result |
| `Zone` | একটা zone | kind (SR/OB/BRK/RCB/RJB/QM), touches, tapped, fiftyHit, flipped, sweepReq, hp, kl, idm, nearSwept, obType, depStrong, prop |
| `Ctx` | সব persistent state | swing, major H/L, trend, CISD, QM, HTF, arrival, M41/M45/M46/M54 arm |
| `ZS` | এক side-এর active zone snapshot | kind, touches, sweepReq, fifty, idm, kl, top/bottom, prop |
| `Sx` | S–AB machine + structure pending + POI + HTF FVG | dt/m62/db/tl/m65/m68/ifc/m72, stPend*, poi*, hFvg* |
| `Feat` | per-bar feature vector | ~90 flag |
| `Best` | এক side-এর সেরা candidate | n (name), s (rank), t (note) |
| `Tag` | label priority pick | text, tip, color, rank |
| `Sig` | একটা signal | entry, sl, tp1-3, rr, score, note, tgt (REAL/SYNTH/FIXED-R) |

---

## 5. L0 — Candle pattern

`f_candle` (লাইন 968) — প্রতি bar একবার:

| Pattern | শর্ত (সংক্ষেপে) | কোথায় লাগে |
|---|---|---|
| Pin bar ▲/▼ | wick ≥ 2×body, wick/range ≥ 0.55, উল্টো wick ≤ body | M02 M05 M06 M07 M09 M14 M15, revBull |
| Doji | body/range ≤ 0.10 | M04, M11 |
| Engulfing | আগের candle-এর body ঢেকে উল্টো রং | revBull/Bear, M07 |
| Inside bar | high ≤ high[1], low ≥ low[1] | M03 |
| Harami | inside + body < 0.6× আগের body | M46 (IMMEDIATE মোডে) |
| Long-wick rejection | wick ≥ 0.5 range + large range | strongRev (M04) |
| Shooting star / hammer | pin + swing extreme-এর 1 ATR-এর মধ্যে | M07 |
| IFC (Institutional Funding Candle) | swing পার করে wick ≥ 2×body | M69, revBull |
| Manipulation candle | আগের low/high নিয়ে উল্টো দিকে close beyond | revBull/Bear |
| Large range | range > 1.5 ATR | M29 |

**Reversal candle সংজ্ঞা:** `revBull = pinBull or engulfBull or ifcBull or manipBull` (mirror bear)।

---

## 6. L1 — Market structure (BOS / CHoCH / CISD)

`f_structure` (লাইন 1037)।

| ঘটনা | সংজ্ঞা |
|---|---|
| **BOS** | trend-এর দিকে (বা RANGE থেকে) শেষ pivot-এর উপর দিয়ে close + **displacement** |
| **CHoCH** | protected swing (`majorHigh/Low`) উল্টো দিকে close + displacement; **অথবা** R2 form: bull trend-এ LH-এর পর শেষ pivot low-এর নিচে close (mirror) |
| **Internal BOS (iBOS)** | trend-এর বিপরীতে সাধারণ pivot break → শুধু label, structure বদলায় না |
| **Weak BOS** | displacement ছাড়া break → pending; `pendBars` (3)-এর মধ্যে follow-through close হলে promote |
| **RANGE** | পরপর 2টা failed follow-through, অথবা 20 bar কোনো BOS/CHoCH নেই |
| **Sweep (structure)** | wick swing পার করে কিন্তু close ফিরে আসে (✖SWEEP label) |
| **Pullback PB✓** | extreme-maker candle-এর low/high ভাঙা (one-shot) |
| **CISD** | leg extreme যে same-colour series দিয়ে তৈরি, তার প্রথম candle-এর **open**-এর মধ্য দিয়ে close — শুধু qualified sweep-এর পর (input) |
| **movePhase** | IMPULSIVE (current swing পার) / RETRACEMENT / RANGE |

**Displacement** = candle body/range ≥ 0.5 **এবং** range ≥ 0.6 ATR, **অথবা** level থেকে ≥ 0.3 ATR দূরে close।

**Protected swing** = `f_legOrigin` — ভাঙা swing-এর পর থেকে break পর্যন্ত সবচেয়ে নিচু low (bull) / উঁচু high (bear)।

**v8.4.1 H1:** CHoCH-এর level এখন `chLvl/chIdx` — যে level-এর মধ্য দিয়ে আসলেই close হয়েছে (R2 form-এ শেষ pivot), protected swing নয়।

---

## 7. L2 — FVG ও Move strength

### FVG (`f_fvg`, লাইন 1292)
- Bull FVG: `low > high[2]`, উচ্চতা ≥ 0.10 ATR · Bear mirror
- **শুধু confirmed bar-এ** তৈরি (repaint বন্ধ)
- Mitigation mode: `TOUCH` (default) / `50%` / `FULL`
- সর্বোচ্চ 40টা; mitigated 300 bar পর মুছে যায়

### Move strength (`f_moveStrength`, লাইন 1355) — event-driven
শুধু BOS / weak / internal break, CHoCH আর zone touch (arrival)-এ চলে।

| মাপ | অর্থ | STRONG শর্ত |
|---|---|---|
| fvgCount | leg-এ unmitigated FVG | ≥ 1 |
| bodyEff | Σbody / Σrange | ≥ 0.55 |
| mixed | রং বদলের অনুপাত | ≤ 0.35 |
| speed | net move / bars / ATR | ≥ 0.35 |

ব্যবহার: `dispBull/Bear`, `chochReal` (CHoCH leg-এ FVG ≥ 1), KL score, OB তৈরি, arrival weak/strong, `dispScore` (0–3)।

---

## 8. L3 — Liquidity

`f_liq` (লাইন 1442) + `f_addLevel`।

| Level | উৎস |
|---|---|
| BSL / SSL | প্রতিটা swing high / low (`ext` = 50-bar extreme হলে) |
| EQH / EQL (POOL) | 0.10 ATR-এর মধ্যে দুটো swing merge, বা touch ≥ 2 |
| PDH / PDL | Daily `request.security` (intraday) |
| PWH / PWL | Weekly (≤ daily TF) |
| SESH / SESL | Asia session (20:00–00:00 NY) high/low, Asia শেষ হলে বসে |

**Level resolve:**
- **SWEEP** — wick পার, close ফিরে আসে (বা `failedCloseBars`-এর মধ্যে ফিরে আসে)
- **RUN** — body ≥ 0.6 এবং ≥ 0.25 ATR দূরে close → "avoid"
- **EXPIRED** — দিন/সপ্তাহ/session পালটালে

**Qualified sweep** (S5) — শুধু POOL / PDH-PDL / PWH-PWL / SESH-SESL (+ চাইলে ext) setup arm করে (HP OB, M41, M45, M54, CISD, f_conf)।

Eviction (M4): resolved → unpooled BSL/SSL আগে বাদ; pooled / PD / PW / session সবশেষে।

`bslAbove` / `sslBelow` = 3 ATR-এর মধ্যে unresolved level সংখ্যা (M09, f_conf)।

---

## 9. L4 — Zone (OB / BRK / RCB / RJB / QM / KL)

`f_zones` (লাইন 1678)।

| Zone | কখন তৈরি | বিশেষত্ব |
|---|---|---|
| **SR** (wick zone) | প্রতিটা pivot | raw material; KL score না পেলে tradable না |
| **KL / KL★** | BOS-এ origin SR zone score | base 1 + FVG + strong + hidden-interest (clean) + (vol) → ≥3 = KL, ≥4 = KL★ |
| **OB** | strong BOS-এ | displacement candle-এর আগের শেষ উল্টো candle; type T1/T1b/T2/G2; aligned FVG না থাকলে T5 (invalid), নিজের FVG খেলে T3 (invalid); sweep-এর 10 bar-এর মধ্যে হলে **HP ★** |
| **BRK** (Breaker) | OB close-এ ভাঙলে | দিক উল্টে যায় |
| **FLIP** | KL/SR close-এ ভাঙলে | S→R / R→S |
| **RCB** (Reclaimed) | CHoCH-এ leg origin candle | 50% fib gate (input) |
| **QM** (Quasimodo) | CHoCH-এর পর নতুন LL/HH | 60 bar window |
| **RJB** (Rejection) | wick ≥ 0.5 এবং পরের candle wick-এর বাইরে | 2 bar-এ FVG না এলে মুছে যায়; 15 bar-এ BOS এলে confirmed |
| **PROP** (Propulsion) | tapped zone (50% ছুঁয়েছে) থেকে নতুন FVG সহ 0.8–2.4 ATR departure | re-arm, priority +3 → M73 |

**Zone state flag:** `tapped` · `fiftyHit` · `touches` (≥2 হলে **⚠SWEEP REQ**) · `idmSwept` (IDM✓ — zone-এর আগের inducement swing sweep) · `nearSwept` (★★ — near-miss তারপর sweep) · `depStrong` · `flipped` · `weak` · `confirmed`।

**Active zone slot (S9):** প্রতি side-এ একটা (`ft.zb` bull, `ft.zs` bear), priority: OB 6 > BRK 5 > RCB/QM 4 > RJB 3 > KL 2 > SR 1, PROP +3।
Weak / unconfirmed / unscored SR কখনো active slot-এ ঢোকে না।

Cap: SR আলাদা budget (30), মোট 60; untouched 500 bar পর মুছে যায়; zone উচ্চতা ≤ 3 ATR (বেশি হলে origin edge রেখে clip)।

---

## 10. L5 — HTF (Higher Timeframe)

**Auto pairing** (`f_htfAuto`):

| Chart TF | Conservative | Aggressive |
|---|---|---|
| ≤1m | 15m | 15m |
| ≤3m | 30m | 30m |
| ≤5m | 1h | 30m |
| ≤15m | 4h | 1h |
| ≤30m | 4h | 4h |
| ≤4h | D | D |
| ≤D | W | W |
| বড় | M | M |

`f_htf` (লাইন 2128) — শুধু নতুন HTF bar-এ:
- **HTF bias** BULL / BEAR / NEUTRAL — LTF-এর মতোই rule (displacement body ≥ 0.5, protected swing, R2 LH/HL form)
- **HTF sweep** ↑/↓ — 3 HTF bar valid
- **HTF manipulation candle**, **HTF rejection** (wick ≥ 0.5)
- **HTF FVG** (P1-B) — শেষ তিনটা completed candle থেকে; price ভিতরে থাকলে f_conf +1
- **HTF OHLC line** — শেষ 3টা candle-এর H/L/O/C
- **Bias tint** — background রং

**Gate** (`f_gate`): HTF bias + LTF trend দুটোই মিললে 2 (pass); না মিললে mode অনুযায়ী WARN = 1 / STRICT = 0 / OFF = 2।
`Trend the gate reads` = **Entering bar** (default) — এই bar-এর নিজের BOS দিয়ে gate trivially pass হয় না।

---

## 11. Premium/Discount, OTE, Session, NY Open

| ফিচার | বিবরণ | প্রভাব |
|---|---|---|
| **PD array** | Dealing range = current leg (bull: majorLow → তার পরের highest high) | discount-এ long / premium-এ short +1; deep (>75%) উল্টো দিকে −1 |
| **Expansion** | close leg-এর বাইরে | neutral (gate ও score কোনোটাই নয়) |
| **OTE** | pdPct 0.21–0.38 (long) / 0.62–0.79 (short) | +1 |
| **PD gate** | input, default OFF | premium-এ long / discount-এ short block |
| **Killzone** | NY timezone: Asia 20–00 · London 02–05 · NY 07–10 | London/NY-তে +1 |
| **Killzone filter** | "Only signal inside a killzone" OFF, কিন্তু **forex/CFD-তে auto-ON** | বাইরে হলে reject code 3 |
| **SESH/SESL** | Asia range = liquidity level | qualified sweep |
| **NY midnight open** (v8.4.1 নতুন) | 00:00 NY bar-এর open | এর নিচে long / উপরে short +1; panel-এ দেখায় |

---

## 12. অন্যান্য feature

| Feature | কাজ | কারা পড়ে |
|---|---|---|
| **Arrival strength** | zone touch-এ, আগের swing থেকে leg মাপা; 10 bar cache | M19 filter, M26, M33, M36, M42, f_conf (−2) |
| **Leg counter** | leg-এ pin / doji সংখ্যা | M04, M06, M07 |
| **Wick sequence** | পরপর 3টা বড় wick বাড়ছে/কমছে | M01, M02 |
| **Break state** | যেকোনো level break (BOS/weak/internal/RUN) — level, bar, hi/lo | M01–M05, M14, M15, M62, M63, M72 |
| **brkTouches** | ভাঙা level আগের 30 bar-এ কতবার reject করেছে | M01/M02 (≥2) |
| **fakeBreak / insideOk** | 1 bar পর ফিরে আসা / inside bar break candle-এর 50%-এর উপরে | M62 / M03 |
| **Auto trendline (M64)** | শেষ দুটো HL (support) / LH (resistance); age ≤ 250, distance ≤ 10 ATR, slope ≤ 0.5 ATR/bar | M12, M65, 4-factor |
| **M41 arm** | qualified sweep → 20 bar-এর মধ্যে BOS (strong = arm, weak = NO TRADE) | M41 |
| **M45 arm** | sweep + BOS (±1) / sweep + CHoCH (±2, tier 4) | M45 |
| **M46 arm** | CISD + reliability ≥1 (HTF rej/sweep · fresh FVG · recent sweep) | M46 |
| **M54 stage** | demand touch → qualified sweep → BOS → retrace | M54 |
| **inRange** | 20 bar BOS নেই + width ≤ 3 ATR | শুধু panel |

---

## 13. Entry trigger — POI state machine

Input **"Zone entry trigger"** (default **CONFIRMED**):

| Mode | কাজ |
|---|---|
| IMMEDIATE | zone/FVG-এ reversal candle-ই trigger |
| **CONFIRMED** | reversal candle (tap) → `i_poiBars` (8)-এর মধ্যে তার high-এর উপরে close **বা** নতুন bull FVG |
| MSS | একই, কিন্তু confirm level = reaction candle-এর আগের 5 bar-এর highest high |

- Tap-এ zone snapshot (`sx.poiZb/Zs`) রাখা হয় — confirm bar-এ price zone ছেড়ে গেলেও SL/score ওই zone ধরে
- Invalidation: tap low − 0.15 ATR-এর নিচে close হলে বাতিল
- **v8.4.1 H2:** armed POI নিজেই §6.2 sweep rule পাস করেছে ধরা হয় (`poiArmL/S`)
- **v8.4.1 H3:** SL-এর জন্য `setLoL/setHiS` = tap থেকে confirm পর্যন্ত lowest low / highest high
- M09 wick test confirm bar-এ reaction candle-এর wick পড়ে (`poiWickL/S`)

**কোন module trigger মানে:** M08 M09 M12 M33 M36 M37 M39 M40 M41 M42 M45 M46 M51 M54 M68 M70 M73।
**মানে না (নিজস্ব trigger):** M01–M07, M10, M11, M14, M15, M29, M58, M62, M63, M65, M69, M72।

---

## 14. L6 — Setup module পূর্ণ তালিকা

Rank = **tier × 10 + priority**; score-এ যায় `tier = rank / 10`।
"Cont." = continuation module (P1-E): HTF WARN-এও **block** হয়।

### Group A–I (11 · Setups A–I)

| ID | নাম | Default | Rank | Cont. | মূল শর্ত |
|---|---|---|---|---|---|
| M01 | Breakout rejection trap | ON | 21 | | break-এর 1–8 bar-এ বাড়তে থাকা wick + strong opposite close level-এর নিচে; level ≥2 বার reject |
| M02 | Pin-bar continuation | ON | 21 | ✔ | structural break-এর পর কমতে থাকা wick + pin/engulf |
| M03 | Inside bar breakout | OFF | 10 | | break → inside bar (50% ধরে) → 5 bar-এর মধ্যে IB পার |
| M04 | Doji move reversal | OFF | 10 | | strong-departure zone + leg-এ ≥2 doji + strong reversal |
| M05 | Pin bar after breakout | ON | 21 | ✔ | break-এর ঠিক পরের bar-এ pin |
| M06 | Multi pin on pullback | OFF | 10 | | trend + retrace + ≥2 pin + zone + pin |
| M07 | Multi pin on impulse (trap) | OFF | 10 | | impulse-এ ≥2 pin → star/engulf উল্টো দিকে |
| M08 | Pin bar on retracement | ON | 21 | ✔ | trend + zone + trigger |
| M09 | Pin bar + liquidity | ON | **32** | | zone + trigger + wick ≥0.65 + ≥2 liquidity target |
| M10 | Sweep reversal | ON | 21 / **31** | | qualified sweep (বা zone-এ sweep) + wick ≥0.5 + নিজের upper half-এ close; PD/PW/SES হলে tier 3; 10 bar-এর fresh strong displacement fade করে না |
| M11 | Doji + breakout | OFF | 10 | | zone-এ doji → পরের bar doji ও zone দুটোই ভাঙে |
| M12 | Confluence zone | OFF | 11 | | flipped zone + (trendline বা KL) + trigger |
| M14 | Pin after breakout (S/R) | OFF | 10 | | level-এর নিচে dip, pin close উপরে |
| M15 | Breakout with pin bar | ON | 21 | ✔ | break candle নিজেই pin (নিচের liquidity নিয়েছে) |
| M29 | Strong move trap (no FVG) | OFF | 10 | | FVG ছাড়া BOS-এর 1–5 bar-এ reversal; warning ⚠M29 |
| M33 | Zone flip model | ON | **32** | ✔ | flipped + strong departure + weak arrival + trend + HTF একই দিকে |
| M36 | Weak retracement on OB | ON | **32** | ✔ | OB/BRK + weak arrival + trigger |
| M37 | Inducement block | ON | **43** | | OB/BRK + IDM swept + trigger |

### Group J–R (13 · Setups J–R)

| ID | নাম | Default | Rank | Cont. | মূল শর্ত |
|---|---|---|---|---|---|
| M39 | Reclaimed block retest | ON | 31 | | RCB + trigger |
| M40 | Rejection block retest | ON | 21 | | RJB (confirmed) + trigger |
| M41 | Sweep + FVG confluence | ON | **43** | | armed (sweep → strong BOS) + zone/FVG reaction + trigger; weak হলে "NO TRADE" |
| M42 | High-probability S&D | ON | **43** | ✔ | OB + strong departure + 50% + weak arrival + trigger (★★ near-swept) |
| M45 | Sweep-based CHoCH retest | ON | 33 / **43** | | armed sweep+BOS (tier 3) বা sweep+CHoCH (tier 4) + OB/BRK + trigger |
| M46 | CISD setup | ON | **32** | | armed CISD + reaction + trigger (IMMEDIATE-এ harami-ও) |
| M51 | Smart BOS model | ON | **32** | ✔ | trend + strong BOS ≤40 bar + zone + trigger; weak BOS → warning |
| M54 | Smart S&D trap | ON | **43** | | 3-stage: demand → stop hunt → BOS → retrace |

### Group S–AB (15 · Setups S–AB)

| ID | নাম | Default | Rank | Cont. | মূল শর্ত |
|---|---|---|---|---|---|
| M58 | Double top / bottom | ON | 21 | | পরপর দুটো pivot ±0.15 ATR; neckline close-এ ভাঙে |
| M62 | Fakeout trap | ON | 21 | | break 1–2 bar-এ ফেরত → level tap + reversal |
| M63 | Direct breakout (no retest) | OFF | 10 | | 8 bar retest নেই → পরে level-এ rejection |
| M64 | Auto trendline | ON | — | | **শুধু আঁকে**, signal নেই |
| M65 | Trendline + flipped level | OFF | 21 | | trendline + flipped/KL + reversal → counter-trendline break |
| M68 | HTF sweep → LTF entry | ON | **43** | | HTF sweep + LTF CHoCH → reaction + trigger |
| M69 | IFC candle | ON | **10** | | zone/sweep-এ IFC → 10 bar-এর মধ্যে IFC high পার |
| M70 | Quasimodo | ON | 22 | | QM zone + trigger |
| M72 | Operator trap | ON | 21 | | break-এর পর level-এর উপরে ≥4 bar consolidation, অর্ধেকে wick → strong close ফেরত |
| M73 | Propulsion Block | ON | **43** | ✔ | PROP zone + 50% + trigger |

### Warning (trade নয়, শুধু label — "All events" মোডে)
`⚠M07 liq below/above` · `⚠M29 weak move` · `RUN — avoid` · `M41 NO TRADE (no FVG)` · `⚠M51 weak BOS — consolidation risk`

---

## 15. Setup filter ও gate

Group "12 · Setup filters":

| Filter | Default | কাজ |
|---|---|---|
| M19 | ON | STRONG arrival-এর পর reversal দমন (`arrOkBull`) |
| M26 | ON | pullback corrective (mixed ≥ 0.35) হতে হবে |
| M31 | OFF | retest-এর body BOS body-এর 0.7×-এর কম |
| §6.2 | ON | touch ≥ 2 zone-এ sweep ছাড়া reversal নিষেধ |
| §6.6 | ON | S&D zone-এর 50% ছুঁতে হবে |
| M01T | ON | M01/M02-এ level ≥2 বার reject |
| Zone close | **50%** | reversal candle zone-এর মাঝের উপরে close (Off / 50% / Top) |

**Shared gate:**
- `zoneOkBull` = active zone + 50% close + (sweepReq না, বা sweep হয়েছে, বা armed POI) + (SR না হলে 50% hit)
- HTF/trend gate: 0 = block, 1 = WARN (score −1, label ধূসর; continuation module block), 2 = pass
- PD gate (optional), Killzone (forex/CFD auto)
- **4-factor** (HTF · trend · dep/arr · liq) — gate ≠ 2 বা zone/FVG/trendline না থাকলে "INCOMPLETE", score −1

---

## 16. L7 — Trade engine

### Entry (`i_entryPx`)
| Mode | Entry |
|---|---|
| **CLOSE** (default) | confirm candle-এর close |
| CANDLE 50% | candle-এর মাঝখানে limit |
| ZONE EDGE | zone top (long) / bottom (short) limit |
| M10 RETEST/BOTH | swept level-এ limit; target না পেলে IMMEDIATE-এ fallback |

### Stop loss (`f_stop`) — অগ্রাধিকার
1. Zone আছে → zone bottom **ও** setup extreme `x`-এর নিচে − 0.15 ATR (v8.4.1 H3)
2. Sweep হয়েছে → `x` − buffer
3. Major HL/LH 2 ATR-এর মধ্যে → তার নিচে
4. Fallback → candle extreme
- Sanity: ভুল দিকে বা 4 ATR-এর বেশি হলে candle extreme-এ fallback
- **Min risk** = max(20 tick, **0.3 ATR**) (v8.4.1 M1)

### Target
- **TP1** = minRR (2R) থেকে maxRR (6R)-এর মধ্যে সবচেয়ে কাছের **qualified** উল্টো zone / unmitigated FVG / qualified liquidity → `REAL`
  - না পেলে: "Require REAL target" ON → signal বাতিল; OFF → synthetic 2R (`SYNTH`)
- **TP2 / TP3** = পরবর্তী liquidity, প্রতিটা আগেরটার চেয়ে ≥1R দূরে (না হলে +1R)
- **Fixed-R mode** → TP1 = N R, TP2/TP3 = +1R করে (`FIXED-R`)

### Path check (`f_pathBlock`) — default **STRICT**
Entry ও TP1-এর মাঝে qualified উল্টো zone থাকলে STRICT = বাতিল, WARN = −1।

### Geometry gate (P0-3)
SL ভুল দিকে, TP1 ভুল দিকে বা R:R < min → বাতিল।

---

## 17. Scoring system

**Final score = tier × 2 + f_conf − (path WARN) − (HTF WARN) − (INCOMPLETE)**

### `f_conf` উপাদান

| উপাদান | পয়েন্ট |
|---|---|
| Base | +1 |
| HTF bias একই দিকে | +1 |
| LTF trend একই দিকে / বিপরীতে | +1 / **−1** |
| POI category (cap **+2**): strong dep + weak arrival · fresh (touch ≤1) · KL★ · zone-over-FVG | 0…+2 |
| Liquidity target সামনে | +1 |
| Qualified sweep বা IDM | +1 |
| STRONG arrival | **−2** |
| sweepReq zone কিন্তু sweep নেই | **−2** |
| RANGE | **−1** |
| HTF FVG-এর ভিতরে | +1 |
| Discount (long) / Premium (short) | +1 |
| Deep উল্টো অবস্থান (>75%) | **−1** |
| OTE | +1 |
| London / NY killzone | +1 |
| NY midnight open-এর সঠিক দিকে | +1 |

সর্বোচ্চ confluence ≈ **+12**, সর্বনিম্ন ≈ **−5**।

### Threshold (input)
| | মান |
|---|---|
| Min score to show | **8** |
| A+ | ≥ 11 |
| A | ≥ 8 |
| B | বাকি (default min 8 হওয়ায় কার্যত দেখা যায় না) |

| Tier | Base (tier×2) | Min 8-এর জন্য লাগবে confluence |
|---|---|---|
| 4 | 8 | 0 |
| 3 | 6 | +2 |
| 2 | 4 | +4 |
| 1 | 2 | **+6** |

---

## 18. Signal বাছাই ও duplicate দমন

1. **f_bid** — প্রতি side-এ সবচেয়ে বেশি rank-এর candidate (strict `>`; সমান হলে আগেরটা)
2. **Gate** → HTF/PD (code 2) → killzone (3) → f_sig R:R/geometry/path (4) → score (5)
3. **Both sides একই bar-এ** → বেশি score রাখে (6)
4. **Signal gap** 5 bar — শুধু উল্টো side-এর ≥ +2 বেশি score ঢুকতে পারে (7)
5. **Setup identity** (module + side + zone kind + POI মধ্যবিন্দু / swept level) — 50 bar-এ একই identity আর না (8)

**Reject code** (data window): `long × 10 + short` — 0 shown · 1 no candidate · 2 gate · 3 session · 4 R:R/geometry/path · 5 score · 6 conflict · 7 gap · 8 duplicate।

---

## 19. Drawing

### Label priority (প্রতি bar, প্রতি side একটা)
নিচে (bull): signal > CHoCH▲ > BOS▲ / iBOS▲ > CISD▲ > SWEEP✕ > zone event (BRK/FLIP/PROP/⚠SWEEP REQ) > HTF SWEEP↓ > HTF MANIP▲ > warning > PB✓ > candle tag
উপরে (bear): mirror + ✖SWEEP (invalid BOS)

**Label density:** `Signals only` (default) / `Key events` / `All events`।
Anti-overlap stack (সর্বোচ্চ 4 ধাপ), label cooldown 6 bar (A+ ও rank 1–5 বাইপাস, 2-bar floor)।

**Signal label text:** `▲▲ M37 A+12 · 3.1R` + tooltip (note, entry, SL, TP1–3 R সহ, score, grade)।

### Line
- BOS solid (strong) / dotted grey (weak, internal) · sweep dashed grey · CHoCH solid (real) / dashed (fake) · CISD dotted
- Live major H/L (dashed) · Liquidity (dotted; POOL thick dashed orange; PD/PW grey) · HTF OHLC (H/L solid, O dotted, C dashed)
- Trendline (M64) · Trade line: entry নীল, SL লাল dashed, TP1/2/3 সবুজ dashed (FIFO 50)

### Box
FVG (border ছাড়া; mitigated optional faded) · Zone box (text ভিতরে, KL★ border 3, weak/BRK/flip dashed)।

### Info panel (bottom-right, 15 row)
Chart/HTF · LTF structure · HTF bias (⚠ mismatch) · Regime · Last event · Move phase · Active zone · Arrival · Nearest BSL · Nearest SSL · 4-factor ✅❌ · Signal · PD array · Session (+ NY open পাশ) · TP1 / gate।

### Legend (top-right, default OFF) — 8 row।

### Background
HTF bias tint (BULL সবুজ / BEAR লাল, 94% transparent)।

---

## 20. Alert ও Data window

### Dynamic `alert()` (bar close-এ একবার)
```
TICKER | M37 LONG | A+12 | Entry … SL … TP1 … TP2 … | risk … · 3.1R | TF 5 | HTF BULL | TP1 REAL
```

### `alertcondition` (11টি, সব `barstate.isconfirmed`)
| নাম | কখন |
|---|---|
| Setup: LONG signal / SHORT signal | signal দেখালে |
| Setup: Any A+ signal | A+ |
| Warning: Counter-HTF signal | gate = 1 |
| Structure: BOS | BOS |
| Structure: CHoCH (Real) | FVG সহ CHoCH |
| Structure: CISD | CISD |
| Liquidity: Sweep detected | যেকোনো sweep |
| Zone: New high-probability OB | HP OB |
| Zone: Propulsion Block formed | PROP |
| Zone: Price entered OB / S&D (50% tapped) | OB 50% |

### Data window plot (13টি)
long score · short score · zones · liq levels · M01/M02 level rejections · M71 bars at level · M46 CISD reliability · zone departure STRONG · PD array · displacement quality · S4 internal break · S4 weak break · reject code।

---

## 21. সব Input

| Group | মূল input (default) |
|---|---|
| **1 · General** | ATR 14 · Swing 5 · Max labels 200 · Max lines 100 · Min gap 6 · Label density "Signals only" · **Setup master mode** (Custom / Core only / All on / All off) |
| **2 · Candle (L0)** | Pin wick 2.0× · Pin ratio 0.55 · Doji 0.10 · Large 1.5 ATR · Long-wick 0.50 · Harami 0.60 · Star prox 1.0 · IFC 2.0 · IFC any colour OFF · Manip wick 0.30 |
| **3 · Structure (L1)** | RANGE after 20 bar · Displacement "Candle" (body 0.5, range 0.6 ATR) · …or close beyond 0.3 ATR · Follow-through 3 · Failed → RANGE 2 · CISD after sweep ON |
| **4 · FVG / Strength (L2)** | Min FVG 0.10 ATR · Mitigation TOUCH · Max 40 · Drop 300 · STRONG: FVG ≥1, bodyEff 0.55, mixed 0.35, speed 0.35 · Max bars 150 |
| **5 · Liquidity (L3)** | Equal tol 0.10 · Touch tol 0.15 · Cooldown 3 · Ext lookback 50 · PDH/PDL ON · PWH/PWL ON · RUN body 0.60, close 0.25 · Sweep wick 0.50 · Sweep qualification "Major only" · Failed-close 2 · Max levels 30 |
| **6 · Zones (L4)** | Max zones 30 · Age 500 · Max height 3 ATR · OB sweep window 10 · RJB wick 0.50, confirm 15 · QM 60 · KL lookback 50, min 3 · SR tradable OFF · OB HP only OFF · RCB fib ON · KL volume OFF (1.5×) · Trendline tol 0.30, anchor Wick · IDM time 5 · Propulsion 10 bar, 0.8 ATR · M64 confirm touch OFF |
| **7 · HTF (L5)** | Pairing Conservative · Manual 60 · **Gate WARN** · Gate trend "Entering bar" · HTF pivot 3 · Sweep valid 3 · Candles shown 3 · Rejection wick 0.50 |
| **8 · Setup filters (L6)** | Vol SMA 20 · Pin count 2 · Doji count 2 · Retest body 0.7 · Liq scan 3 ATR · Range 20 / 3 ATR · Arm 30 bar · **Zone entry trigger CONFIRMED**, window 8 |
| **9a · PD + Sessions** | PD score ON · PD gate OFF · Deep 0.75 · Killzone only OFF · Score sessions ON · Timezone America/New_York · Asia 2000-0000 · London 0200-0500 · NY 0700-1000 · Forex auto-killzone ON · SESH/SESL ON · NY open score ON |
| **9 · Visual · Colors** | 12টা রং · transparency (label 15, box 85, line 30) · Filled ON · Label size normal · Zone text normal · Offset 0.30 ATR |
| **10 · Show** | Structure ON · PB OFF · Weak BOS label OFF · Every CISD OFF · FVG ON · Mitigated FVG OFF · Liquidity ON · Sweep/run ON · Every sweep OFF · OB diag OFF · OB ON · Breaker ON · KL ON · SR OFF · RCB/RJB/QM ON · HTF levels/events/tint ON · Candle tags OFF · Panel ON · Legend OFF · Signals ON |
| **11 / 13 / 15** | Module toggle (§14) |
| **12 · Setup filters** | §15 |
| **14 · Trade (L7)** | SL buffer 0.15 · Max SL 2.0 ATR · Min RR 2.0 · Max RR 6.0 · Fixed-R OFF (2.0) · Require REAL target ON · **TP1 path STRICT** · Min score 8 · A+ 11 · A 8 · Signal gap 5 · Identity 50 · M10 entry IMMEDIATE · Entry price CLOSE · Min risk 20 tick / 0.3 ATR · Trade lines ON, 20 bar |
| **16 · S–AB parameters** | Double top tol 0.15 · M72 cons min 4, max 1.5 ATR · M63 no-retest 8 |

---

## 22. সরানো (CUT) module ও feature

| Version | সরানো | কারণ |
|---|---|---|
| v8.2.0 | M55 M56 M57 M60 M61 M66 M71 + ১৮টা write-only field | token limit, কার্যত কখনো fire করত না |
| v8.3.0 | M43, M38-P4, hidden-liquidity engine, Wyckoff label, "CRT" নাম | token headroom |
| v8.4.0 | M21–M25 (tick volume), M38 P1–P7 | 101,975 token > 100,256 limit |
| **v8.4.1** | **M44 M47 M48 M49 M50 M52 M53** + range-break tracker, 16 Ctx + 3 Feat field | tier-1, min 8 পৌঁছাতে পারত না; আনুমানিক −1,400 token |

পরবর্তী cut তালিকা (কোডের মন্তব্য অনুযায়ী): M63, M65।

---

## 23. পর্যবেক্ষণ

### 23.1 Dead / write-only (লেখা হয় কিন্তু কেউ পড়ে না)

| জিনিস | লাইন | মন্তব্য |
|---|---|---|
| `ft.brkTimeOk` | 2611 | M71 v8.2.0-তে সরানো; flag কেউ পড়ে না। ফলে **input "Bars spent at the level before a break" (`i_idmTime`) এর কোনো প্রভাব নেই** — শুধু data window-এ `sx.brkTimeAt` দেখায় |
| `ft.incomplete` | 3465, 3481 | লেখা হয়, পড়া হয় না (score −1 আলাদাভাবে দেওয়া হয়, তাই ক্ষতি নেই) |
| `ft.sweptPool` | 1554 | write-only |
| `ft.atSupport` / `ft.atResist` | 2072, 2075, 2661, 2665 | write-only (logic `zb.kind` পড়ে) |
| `ZS.hp` | 2063 | snapshot-এ কপি হয়, কেউ পড়ে না |
| `cCol` | 1328 | unused local variable |
| `Cfg.sweepWickMin = 0.40` | 233 | type default 0.40 কিন্তু input 0.50 দিয়ে override — ক্ষতিহীন, শুধু বিভ্রান্তিকর |
| `Cfg.gateMode = "STRICT"` | 248 | একইভাবে input "WARN" দিয়ে override |

> Token বাঁচাতে এগুলো পরের cut-এ সরানো যায় (ছোট লাভ)।

### 23.2 Default ON কিন্তু কার্যত চুপ থাকতে পারে

- **M69 IFC candle** — default ON কিন্তু rank 10 (**tier 1**)। Min score 8 পেতে confluence **+6** লাগে (সর্বোচ্চ ~12)। v8.4.1-এ ঠিক এই যুক্তিতেই M44/M47… কাটা হয়েছে। হয় tier বাড়ানো, নয় default OFF বিবেচনা করা উচিত।
- **Tier-1 module সব** (M03 M04 M06 M07 M11 M12 M14 M29 M63) — একই সমস্যা, তবে এগুলো default OFF।
- **Grade B** — min score 8 = A threshold, তাই B কখনো দেখা যায় না (default-এ)।

### 23.3 পুরোনো audit-এর খোলা issue (এই ফাইলে এখনো আছে)

- **F18 — `ft.atBullFvg/atBearFvg` TOUCH mode-এ কার্যত কখনো true হয় না।** `f_fvg` (লাইন 1318–1322) একই predicate-এ আগেই FVG mitigated করে দেয়, তারপর লাইন 2457 `not g.mitigated` চায়। ফলে M41/M46/M68-এর FVG reaction path, POI-এর FVG tap, f_conf zone-over-FVG — সব FVG-অংশ default-এ মৃত।
- **F19 — arrival (weak/strong) শুধু live zone touch-এ সেট হয়।** `zoneTouch` (লাইন 2356) POI snapshot restore (লাইন 2658)-এর **আগে** হিসাব হয়। CONFIRMED মোডে confirm bar zone ছেড়ে গেলে `arrivalWeak = false` → **M33 / M36 / M42** fire করতে পারে না, আর M19 filter বাইপাস হয়।

### 23.4 Performance ঝুঁকি (runtime timeout)

Series-length `ta.highest/lowest` প্রতি bar চলে:
- লাইন 2337–2338: `pdHiB/pdLoS` — length 490 পর্যন্ত
- লাইন 2727–2728: `lowTap/highTap`

এছাড়া `f_legOrigin` (490 bar loop), `f_moveStrength` (150 bar), brkTouch (30 bar loop), zone/FVG/liquidity array loop। আগের সেশনে v8.4.1 stage-1 build "Calculation timed out" পেয়েছিল; সেখানে PERF-1 (running extreme) প্রয়োগ হয়েছিল — **এই ফাইলে PERF-1 নেই**। TradingView-এ timeout হলে প্রথমে PD array-কে running high/low দিয়ে বদলানো উচিত।

### 23.5 ছোট অসঙ্গতি (comment / docs)

- হেডার (লাইন 136) বলে "plots 18/64" — বাস্তবে 13 `plot` + 1 `bgcolor`।
- Panel comment (লাইন 3729) বলে "12 rows" — বাস্তবে 15 row।
- Legend-এ HTF FVG, OTE, NY open, PROP-এর কোনো উল্লেখ নেই।
- `i_entryMode` label "M10 entry mode" — শুধু M10-এ প্রভাব, কিন্তু Trade group-এ "Entry price"-এর পাশে থাকায় বিভ্রান্তিকর।

---

## সারসংক্ষেপ

এই indicator একটা পূর্ণাঙ্গ ICT/SMC engine: **candle pattern → structure (BOS/CHoCH/CISD, weak/internal break) → FVG ও move strength → liquidity (BSL/SSL/EQH/EQL/PDH/PWH/SESH) → ৮ ধরনের zone (SR/KL/OB/BRK/RCB/RJB/QM/PROP) → HTF bias/sweep/FVG → PD/OTE/killzone/NY open → 35টি setup module → confirmed POI trigger → structural SL/TP → tier×2 + confluence score → gap ও identity ফিল্টার → label/panel/alert**।

যা ভালো: repaint-safe, layered architecture, rejection reason কোড, REAL target বাধ্যতামূলক, STRICT path check।
যা দেখা দরকার: F18 (FVG reaction মৃত), F19 (CONFIRMED মোডে M33/M36/M42 চুপ), M69 tier-1 default ON, `i_idmTime` input-এর প্রভাব নেই, আর PERF-1 না থাকায় timeout ঝুঁকি।
