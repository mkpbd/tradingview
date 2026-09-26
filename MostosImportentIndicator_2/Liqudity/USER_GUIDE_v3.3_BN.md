# LQ-SD-PA v3.3 — ব্যবহারকারীর গাইড (Step by Step)
### Liquidity + Supply/Demand + Price Action · Silver Bullet · Trap engine

এই গাইড **trade নেওয়ার জন্য**, কোড বোঝার জন্য নয়। কোড/audit জানতে: `FOURTH_PASS_AUDIT_v3.2.2_BN.md`, `UPGRADE_PLAN_v3.3_BN.md`।

---

## ০. এক লাইনে indicator-টা কী করে

**Sweep (liquidity নেওয়া) → POI (zone) → Structure shift → Retest → Entry** — এই chain-টা মেশিন নিজে চালায়। Chain শেষ হলে label + Entry/SL/TP লাইন দেয়। Chain-এর মাঝখানে কোথায় আছে সেটা dashboard-এ দেখায়। **Chain শেষ না হলে কোনো signal নেই — সেটাই নিয়ম।**

মনে রাখার ৩টা কথা:
1. Dashboard-এর **Verdict** row-ই আসল উত্তর। বাকি সব context।
2. **NEXT BUY / NEXT SELL** = কোথায় অপেক্ষা করছে, **signal নয়**।
3. Label ছাড়া trade নেই। Label-এর সাথে E / SL / TP1–3 লাইন থাকবেই।

---

## ১. Install (৫ মিনিট)

1. TradingView → Pine Editor → পুরনো script থাকলে মুছে দিন।
2. `liqudity_trap_trading.txt`-এর পুরো content paste করুন।
3. **Save** → নাম দিন `LQ-SD-PA v3.3` → **Add to chart**।
4. Compile error এলে সাথে সাথে screenshot নিন (error text সহ)।
5. Chart-এ dashboard-এর প্রথম cell-এ `LQ-SD-PA v3.3` লেখা আছে কিনা দেখুন — না থাকলে পুরনো version চলছে।

**Chart settings (প্রথমবার):**
- Timeframe: **5m** (primary)। 1m/15m চলে, কিন্তু default গুলো 5m-এর জন্য tune করা।
- Symbol: BTCUSDT.P · XAUUSD · NAS100 (যেগুলোতে test করা হয়েছে)।
- Chart-এর timezone যা-ই হোক, indicator সব session **New York time**-এ ধরে। বদলাতে হবে না।

---

## ২. Dashboard পড়া (উপরে ডানে, ১২ row)

| Row | মানে | কী দেখবেন |
|---|---|---|
| **হেডার** | Regime | `TRENDING` / `TRANSITION` / `RANGING` / `CHOP`। CHOP = সাধারণত entry বন্ধ। |
| **Bias 60** | `EMA · D · str → combined` | শেষের arrow-টাই আসল। `→ —` = neutral → এখন chart-এর external structure follow করে (`ext` দেখুন)। |
| **Struct · sweep** | `int ▲ ext ▼ · SSL valid` | `ext` = বড় structure-এর দিক। `SSL/BSL` = কোন liquidity নেওয়া হয়েছে, grade কত। |
| **Range pos** | `Disc 30% · OTE buy` | Discount-এ buy, Premium-এ sell খোঁজে। `·tight` = range এত ছোট যে premium/discount অর্থহীন। |
| **Next demand** | `T2 83849–83922 ·fresh` | নিচের প্রথম unspent demand। `T3` > `T2`। `·fresh` = কখনো touch হয়নি। |
| **Next supply** | mirror | |
| **Trigger · FEM** | `MSS▲ · ◎ idle` | সাম্প্রতিক structure event। |
| **◉ Setup L / S** | `AT POI / idle` | **মেশিনের stage**: `idle → SWEPT → AT POI → SHIFTED·await retest → ACTIVE`। |
| **Alignment** | `L 34 (B) S 20 (C)` | Score + tier। **Idle bar-এর score signal-এর score নয়** — এটা দেখে trade নেবেন না। |
| **Session** | `NY AM · ◆ SB NY AM 42m left` | কোন killzone, SB window চলছে কিনা, কত মিনিট বাকি। |
| **Trade** | `LONG 84010 SL 83950 ·TP1✓` | Tracker-এ যে trade চলছে (একটাই)। |
| **Verdict** | নিচে দেখুন | **এটাই পড়ুন।** |

### Verdict-এর ভাষা
| লেখা | মানে | আপনি কী করবেন |
|---|---|---|
| `LONG signal` / `SHORT signal` | এই bar-এ entry | Label + লাইন দেখুন, checklist মিলিয়ে নিন |
| `LONG narrative live · shorts locked · AT POI` | Long setup চলছে, short বন্ধ | অপেক্ষা; short-এর কথা ভাববেন না |
| `NO · score 42 < 50` | alignment কম | কিছু না |
| `NO · POI conflict (…)` | demand আর supply গায়ে গায়ে | zone-টা বিশ্বাস করবেন না |
| `NO · neutral bias` | (শুধু "Block both" mode-এ) | কিছু না |
| `NO · chop` | regime CHOP | কিছু না |
| `NO · gate: score 48 < 50` | setup entry পর্যন্ত এসে final gate-এ আটকেছে; **retest window-এ আবার চেষ্টা করবে** | দেখতে থাকুন |
| `NO · reward blocked — only 1.1R…` | TP2-র আগে opposite POI | কিছু না — এটা আপনাকে বাঁচাল |
| `NO · risk 2.1 ATR exceeds the cap` | SL অনেক দূরে | কিছু না — late |
| `NO · no liquidity event` | sweep-ই হয়নি | কিছু না |
| `waiting` | sweep আছে, chain চলছে | Setup row দেখুন |

---

## ৩. Chart-এর জিনিসগুলো

| দেখবেন | মানে |
|---|---|
| **Label নিচে (সবুজ)** `A · 62` + `◉ SETUP A` | **LONG entry**। উপরের লাইন = tier · score; নিচে কোন engine দিল |
| **Label উপরে (লাল)** | SHORT entry |
| **Teal label** `◆ SB NY AM · CE A+` | Silver Bullet entry — সবচেয়ে উঁচু grade |
| `◬ TRAP LT-5 · HIGH · failed-break✓` | Trap engine-এর entry (label-এর ভেতরে, আলাদা না) |
| **E / SL / TP1 / TP2 / TP3 লাইন** | Signal bar থেকে ১৫ bar ডানে। `E … RR 2.1 (plan, not promise)` |
| `NEXT BUY T3 HTF • 4254–4258 (0.67% below) ·fresh` | অপেক্ষার জায়গা। **Signal না।** |
| `◆ SB … FVG locked · CE 84012 · await retest` (teal box) | SB setup stage 3 — CE-তে limit order-এর জায়গা |
| `◉ SETUP anchor · await retest` | সাধারণ machine setup stage 3 |
| Box: `DEMAND ★HP` / `OB` / `RB` / `MIT` / `BRK` / `IFVG` | Zone-এর ধরন। ★HP = high probability। text ছাড়া box = সাধারণ S/D |
| `BOS` / `CHoCH` / `MSS` chip | Structure event। MSS সবচেয়ে শক্ত |
| `◆ ◈ ◇` ছোট চিহ্ন | sweep: swing / EQ pool / PDH-PDL |
| `Asia H raided`, `Lon L broken` | session level নেওয়া (raided = wick, broken = close) |
| Teal background band | SB window চলছে |
| লাল background | volatility window (08:30 / 10:00 / FOMC) — entry বন্ধ |

---

## ৪. একটা signal এলে কী করবেন (checklist)

Label দেখলেই button চাপবেন না। ৬০ সেকেন্ডের checklist:

1. **Verdict** row `LONG signal` / `SHORT signal` বলছে? (label পুরনো হতে পারে)
2. **Tier** `A` বা `A+`? (`B` default-এ আসে না; এলে setting বদলেছে)
3. **Bias row**-এর শেষ arrow signal-এর দিকে বা `—`? উল্টো হলে কিছু ভুল — নেবেন না
4. **E লাইন** থেকে দাম কত দূরে? `engine fill = next open` লেখা থাকলে পরের candle-এর open-এ ঢুকুন, দৌড়ে নয়
5. **SL লাইন** যেখানে, সেখানেই SL — এক tick ভেতরে না
6. **RR** label-এ ≥ 1.5? (কম হলে indicator নিজেই reject করত; দেখা যাচ্ছে মানে ঠিক আছে)
7. **Trade row** `flat` ছিল? Open trade থাকলে নতুন signal আসেই না (one direction rule)
8. Session: `off-hours` হলে signal দুর্বল; killzone (London/NY AM/SB) হলে ভালো

**Exit:**
- TP1 (1R) hit → SL breakeven-এ যায় (Trade row-এ `·TP1✓`)। আপনিও আনুন।
- TP2 → non-SB trade শেষ (default)। SB trade → protected swing-এর পেছনে trail।
- SB trade: window শেষে TP1 না এলে → **full exit** (`◆ SB time exit` chip)।
- Opposite MSS/CHoCH chip এলে SB trade বন্ধ (`◆ SB structure exit`)।

---

## ৫. Silver Bullet — দিনের ৩টা সময়

| Window | NY time | **বাংলাদেশ (UTC+6)** | কড়াকড়ি |
|---|---|---|---|
| London | 03:00–04:00 | **13:00–14:00** | সবচেয়ে কড়া (sweep grade ≥ 3) |
| **NY AM** | 10:00–11:00 | **20:00–21:00** | সবচেয়ে গুরুত্বপূর্ণ (grade ≥ 2) |
| NY PM | 14:00–15:00 | **00:00–01:00** | grade ≥ 3 |

> US daylight saving বদলালে BD time ১ ঘণ্টা সরে। Dashboard-এর Session row-ই সত্য।

**SB-র নিজস্ব chain (v3.3):**
1. Window-এর ১৫ মিনিট আগে থেকে দেখতে শুরু করুন (Session row `◆ pre NY AM`)।
2. **Raid**: Asia/London/NY H-L, PDH/PDL বা EQH/EQL নেওয়া হবে (`Lon L raided` label, `◈`/`◇` চিহ্ন)। Setup row → `SWEPT`।
3. **Shift**: displacement candle + internal CHoCH/CISD → Setup row সরাসরি `SHIFTED·await retest`, teal box `◆ SB … FVG locked · CE …`।
4. **Entry**: দাম CE (box-এর ৫০%) touch করলে → teal label `◆ SB NY AM · CE`। **Limit order CE-তে আগেই বসিয়ে রাখুন** — এটাই doctrine।
5. TP3 = নিকটতম opposite session H/L / PDH-PDL (`◆ SB liquidity target` লাইন)।

Window-প্রতি একটা SB entry per direction। Window বন্ধ = unfilled setup মরে (`SB window closed`)।

**SB fire না করলে debug করুন:** Settings → Dashboard/Debug → `Debug mode` ON → নিচে ডানে table:
- `◆ SB` row: `tag L2` = long setup NY AM window-এ armed। `L0S0` = arm-ই হয়নি → raid হয়নি বা pool kind < 2 (`Sweeps` row-এ `k1` = swing, `k4` = session)।
- `Machine L` row: `gate: score 46 < 50` → score কম; `SB FVG violated` → FVG ভেঙেছে; `retest window expired` → CE touch হয়নি।

---

## ৬. Trap engine (◬)

Breakout ফাঁদ ধরে: দাম level ভাঙে, ফিরে আসে, confirmation → বিপরীত দিকে entry।
- v3.3-এ trap signal **সাধারণ engine candidate** — একই tier/score/cooldown/direction lock। আলাদা "TRAP SHORT" label আর নেই; merged label-এর ভেতরে `◬ TRAP LT-5 · HIGH` লাইন।
- Uptrend-এ short trap আসবে না (strong raid ছাড়া)। OTE-র বিরুদ্ধেও না।
- একই level-এ একবারই।
- বেশি trap চাইলে: Settings → `Show signal tiers` = `B and above` (noise বাড়বে, সাবধান)।

---

## ৭. Alerts (একবার set করে রাখুন)

Alert তৈরি: chart → Alert → Condition = `LQ-SD-PA v3.3` → নিচের list। **সবসময় "Once per bar close"।**

**ন্যূনতম set (৪টা):**
| Alert | কেন |
|---|---|
| `[SIGNAL] Any LONG` | সব long entry |
| `[SIGNAL] Any SHORT` | সব short entry |
| `[SB] ◆ Silver Bullet entry` | SB আলাদা করে জানতে |
| `Any alert() function call` | SB + Trap-এর detail feed (window, CE, SL/TP, reason) — **এটা না দিলে SB-র detail পাবেন না** |

**অতিরিক্ত (চাইলে):**
- `[SETUP] Armed` / `POI tapped` / `Structure shifted` — chain-এর প্রতিটা ধাপে
- `[SETUP] Invalidated / expired` — setup মরলে
- `[TRADE] TP1 / TP2 / SL hit`
- `[LT] Trap setup detected` — trap arm হলে (signal না)

Telegram/phone-এ পাঠাতে alert message-এ `{{ticker}} {{interval}}` আগে থেকেই আছে।

---

## ৮. Settings — কী বদলাবেন, কী না

**প্রথম ২ সপ্তাহ কিছু বদলাবেন না।** Default = audit-এর পরে ঠিক করা।

তারপর, প্রয়োজন অনুযায়ী:

| চাহিদা | Setting | Default → বদল |
|---|---|---|
| Signal খুব কম | Signal quality → `Min alignment score` | 50 → 40 (Strategy Tester-এ মেপে) |
| আরও signal | `Show signal tiers` | `A and above` → `B and above` (noise বাড়ে) |
| শুধু SB নিতে চাই | Silver Bullet entry → `SB-only mode` | OFF → ON |
| Neutral bias-এ কিছুই নিতে চাই না | HTF context → `When the HTF bias is NEUTRAL` | `Follow chart structure` → `Block both sides` |
| দুই দিকে setup দেখতে চাই (আগের মতো) | Signal quality → `One direction at a time` | ON → OFF (**সুপারিশ করি না**) |
| Crypto/index-এ volume চাই | Volume confirmation → `Require relative volume` | OFF → ON |
| 15m-এ চালাব | Advanced → `Shift / CISD stays a live trigger` | 10 → 6–8 |
| 1m-এ চালাব | ওই একই | 10 → 12–15 |
| Chart clutter | FVG → `Draw live chart-TF FVGs` OFF; Zones → `Rejection blocks` OFF | |
| SB shift কড়া চাই | Silver Bullet setup → `Require a true MSS` | OFF → ON (SB entry কমবে) |
| Volatility window বদল (data দিনে) | Scheduled volatility windows → session string | নিজের calendar দেখে |

**কখনো বদলাবেন না** (audit-এ ভুল ঠিক করা): `Max risk`, `Min RR`, `Max distance close → plan entry`, `Engine signal fill price`, `Machine: what counts as the SHIFT`, `Machine: what counts as the POI TAP`।

---

## ৯. দিনের routine (উদাহরণ, BD time)

| সময় | কাজ |
|---|---|
| 12:45 | Chart খুলুন, dashboard: regime, bias, Next demand/supply নোট করুন |
| 13:00–14:00 | London SB — কড়া window; শুধু `A+` নিন |
| 14:00–19:30 | Chain দেখুন; `SWEPT` / `AT POI` এলে alert-এর অপেক্ষা |
| 19:45 | NY AM pre-window। Asia/London H-L লাইনগুলো দেখুন — এগুলোই raid-এর target |
| 20:00–21:00 | **NY AM SB** — প্রধান window। CE-তে limit, SL sweep wick-এর নিচে |
| 21:00 | Window বন্ধ। TP1 না এলে বেরিয়ে যান (indicator নিজেও `time exit` বলবে) |
| 00:00–01:00 | NY PM SB (ঐচ্ছিক) |
| দিন শেষে | Debug table → Counts row লিখে রাখুন: `A / A+ / TP1 / TP2 / SL / exp` |

---

## ১০. যা করবেন না

- NEXT BUY/SELL label দেখে trade নেওয়া — এটা location, signal না।
- Dashboard-এর `Alignment L 34` দেখে "score কম, তাই skip" ভাবা — idle bar-এর score signal-এর score নয়।
- Label-এর SL সরিয়ে "একটু জায়গা দেওয়া" — SL sweep wick-এর পেছনে; সরালে model নষ্ট।
- Open trade থাকতে অন্য symbol-এ একই direction-এর ২টা — indicator per-chart; risk আপনার।
- `One direction at a time` OFF করা — buy+sell একসাথে আবার ফিরে আসবে।
- Volatility window (লাল band)-এ manual entry।
- Historical chart-এ label গুনে "win rate" বের করা — Debug counter mechanical, statistics না। Strategy twin (`version_02_strategy.pine`) ব্যবহার করুন।

---

## ১১. সমস্যা হলে

| সমস্যা | কী করবেন |
|---|---|
| Compile error | Error text + line screenshot |
| Dashboard `v3.2.2` দেখাচ্ছে | পুরনো script chart-এ; remove করে v3.3 add করুন |
| কোনো signal-ই আসে না ৫ দিন | Debug ON → `Machine L/S` reason + `Counts` screenshot |
| SB window-এ কিছু হয় না | Debug `◆ SB` row + `Sweeps` row screenshot (window চলাকালীন) |
| Buy আর sell একসাথে | `One direction at a time` ON আছে কিনা; `When the HTF bias is NEUTRAL` = `Allow both` না তো? |
| Chart খুব ভরা | §৮-এর clutter row |
| `Study error` / runtime | Symbol + timeframe + screenshot; পুরনো bar-এ হলে "Deep backtesting" off করুন |

Screenshot দেওয়ার সময়: **dashboard + debug table + label** একসাথে দেখা যায় এমন frame।

---

*v3.3 · 2026-09-26 · Educational tool, not financial advice. Backtest before live use.*
