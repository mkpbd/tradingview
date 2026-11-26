# LQ v3.8.6 — Exness Terminal (Indie) port · Phase 1

ফাইল: `LQ_v3.8.6_EXNESS_P1.py` (Indie ভাষা, Python-এর মতো)। Exness Terminal-এর indicator editor ("Powered by Indie") MQL5 বা Pine চালায় না, তাই এই port।

## কিভাবে লাগাবেন
1. Exness Terminal → chart → **Indicators → Create / Code editor (Indie)** খুলুন।
2. নতুন indicator বানান, editor-এর সব লেখা মুছে `LQ_v3.8.6_EXNESS_P1.py`-এর পুরো লেখা paste করুন।
3. **Save / Add to chart** দিন।
4. Compile error এলে **line নম্বর + error-এর পুরো লেখা** আমাকে পাঠান — ঠিক করে দেব। ফাইলটা এখনো compile করে দেখা হয়নি (আমার কাছে Indie compiler নেই)।

## Phase 1-এ যা আছে (Pine-এর logic অনুযায়ী)
- ATR (shock cap), candle anatomy, CISD, IFC, pin/engulf confirmation
- Pivot, last swing high/low, EQH/EQL pool (age-out সহ)
- NY session clock (DST সহ), Asia/London/NY H/L raid, Silver Bullet window, volatility window block
- Sweep engine: এক level-এ এক event, multi-bar reclaim, RAW/EFF quality, pool kind, PDH/PDL/PWH/PWL
- Internal + external structure (BOS / CHoCH / MSS), HTF bias (EMA + HTF structure, শেষ closed HTF bar)
- Dealing range / premium-discount / OTE, SB range lock, regime (TRENDING/TRANSITION/RANGING/CHOP), ADR exhaustion
- FVG registry + IFVG flip, Zone engine (S/D, OB, RB, IFVG, breaker/mitigation, band claim, test count, 50% tap)
- Score + tier, master state machine (SB path সহ), final gate, gate-kill retry, conflict rule, risk/min-RR gate
- Tracker: next-open fill, TP1/TP2/TP3, break-even, SB exit, daily trade/loss limit
- Drawing: zone/FVG box + caption (DEMAND ★HP / OB / RB / MIT / BRK / IFVG ·spent), EQ line, session H/L + tag (Asia H, Lon L broken, NY H raided), PDH/PDL/PWH/PWL, protected swing line, sweep mark (◆ ◈ ◇ ▵), SB/volatility window shading, BOS/CHoCH/MSS chip, BUY/SELL label, E/SL/TP ladder, NEXT BUY/SELL line + label
- HTF FVG POI (chart bar থেকে HTF candle বানিয়ে) + box, machine-এর HTF POI tap, NEXT level-এ HTF POI
- Trendline (pivot pair) + trendline sweep signal
- TradingView-এর মতো dashboard: Bias / Struct·sweep / Range pos / Next demand-supply / Trigger·HTF POI / Setup / Alignment / Session / Trade / Verdict

## এখনো নেই (Phase 2/3)
- HTF CRT / Turtle soup, continuation arm (HTF POI তে sweep ছাড়া arm)
- Chart CRT, TBS, inside-bar, doji engine
- Liquidity Trap engine (LT-1..LT-7), debug table
- Alert — Indie-তে alert() API নেই, তাই port করা যায় না

## পার্থক্য (জেনে রাখুন)
- Day boundary = 00:00 UTC (Exness server day)। TradingView-এর daily candle-এর সাথে PDH/PDL সামান্য আলাদা হতে পারে।
- HTF bias timeframe নিজে বেছে দিন (default 1h); chart TF-এর চেয়ে ছোট দেবেন না।
- Volume confirmation, symbol profile, kill-zone shading, SB window box বাদ (Phase 1)।
- Signal শুধু closed bar-এ — Pine-এর মতোই।
