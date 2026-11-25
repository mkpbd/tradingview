# LQ-SD-PA v3.8.6 — MT5 (MQL5) পোর্ট

উৎস: `liqudity_trap_trading.v3.8.6.txt` (Pine v6, BUILD v3.8.6-b1)
ফাইল: `LQ_v3.8.6_MT5.mq5` (৪১৭৫ লাইন) · MetaEditor compile: **0 error, 0 warning** (2026-11-26)
টার্মিনালে কপি: `MQL5/Indicators/LQ/LQ_v3.8.6_MT5.mq5` + `.ex5`

## ইনস্টল
1. MT5 → Navigator → Indicators → **LQ → LQ_v3.8.6_MT5** চার্টে টেনে আনুন (না দেখালে Navigator-এ right-click → Refresh)।
2. প্রথম লোডে HTF / D1 / W1 ডেটা sync হতে কয়েক সেকেন্ড লাগতে পারে — চার্ট ফাঁকা থাকলে একটা নতুন tick-এর জন্য অপেক্ষা করুন।
3. "Server GMT offset" = -99 (auto)। Exness সার্ভার GMT+0; auto ঠিক কাজ না করলে 0 দিন।

## TradingView-এর সাথে যা একই
- সব ২৩টা module একই ক্রমে, প্রতিটা **closed bar**-এ একবার চলে (Pine-ও `barstate.isconfirmed` দিয়ে gate করে — repaint নেই)।
- সব input একই নাম, একই default, একই group (Settings → Inputs)।
- HTF ডেটা = আগের **বন্ধ** HTF candle (Pine `[1]` + `lookahead_on`) — bias TF, HTF CRT/TBS/POI, PDH/PDL, PWH/PWL, ADR।
- Session (Asia / London / NY / Silver Bullet / volatility window) = **New York সময়**, US DST সহ।
- ডিজাইন: zone / FVG / IFVG / HTF POI / NEXT box (একই রং ও transparency), BOS/CHoCH/MSS chip, signal label (tier · score + engine list), E/SL/TP1-3 ladder, session H/L line + label, EQH/EQL dotted line, trendline, ◆ ◈ ◇ ✕ ▵ ▿ ◦ mark, killzone / SB / news band, উপরে-ডানে Dashboard (১২ row), নিচে-ডানে Debug table।

## পার্থক্য (MT5 সীমাবদ্ধতা)
| বিষয় | TV | MT5 |
|---|---|---|
| শেষ bar | developing bar-ও দেখায় | dashboard / label শেষ **বন্ধ** bar থেকে |
| Daily boundary (newDay, PDH/PDL) | TV exchange session | MT5 সার্ভার দিন (Exness = 00:00 UTC) |
| alertcondition / alert() | TV alert dialog | MT5 pop-up / push (input "MT5 port" group-এ চালু/বন্ধ) |
| LQJRNL / LQCE / LQEXIT journal | alert() feed | **Experts log** (Toolbox → Experts) + push চালু থাকলে push |
| ঘন dotted line (width 2) | TV | MT5-এ dotted শুধু width 1 |
| Size label "≈ units" | pointvalue | **≈ lots** (tick value / tick size থেকে) |
| HTF EMA warm-up | TV-র পুরো history | ~300 HTF bar — শুরুর দিকে bias সামান্য আলাদা হতে পারে |

## নতুন input (শুধু MT5, group "MT5 port")
- `Bars to calculate` 5000 — বেশি দিলে প্রথম লোড ধীর।
- `Shift the chart…` — dashboard-এর নিচে শেষ candle যেন না ঢাকে।
- Alert toggle: Signals ✔ · Setup ✘ · Trade ✔ · Trig ✘ · Liq ✘ · Ctx ✘ · LT ✔ · SB ✔।
- `Font for marks` = Segoe UI Symbol (◆ ◈ ◇ ✕ চিহ্নের জন্য)।

## যাচাই করুন (live chart)
1. XAUUSDm / USTECm / BTCUSDm / USOILm M5-এ লাগান; TV-র একই সময়ের সাথে dashboard-এর Regime, Bias, Setup L/S, Verdict মিলিয়ে দেখুন।
2. Signal label-এর tier · score, E/SL/TP মিলছে কিনা।
3. কোনো "array out of range" বা ধীরগতি হলে Experts tab-এর লাইনসহ জানান।
