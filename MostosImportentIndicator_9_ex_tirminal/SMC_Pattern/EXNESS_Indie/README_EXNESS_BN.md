# SMC / ICT Suite v8.5.4 — Exness Terminal (Indie) port · P1

ফাইল: `SMC_v8.5.4_EXNESS_P1.py` (Indie, ~3.9k লাইন)। Source: `../SMC_v8.5.4.txt` (Pine v6, 4250 লাইন)।

## কিভাবে লাগাবেন
1. Exness Terminal → chart → **Indicators → Code editor (Indie)** → নতুন indicator।
2. Editor-এর সব লেখা মুছে পুরো `.py` ফাইলটা paste → **Save / Add to chart**।
3. Compile error এলে **line নম্বর + পুরো error text** পাঠান। এখনো Exness-এ compile করে দেখা হয়নি; Python syntax + pyflakes clean, আর mock-runtime-এ 4000 bar × 4 setting combo চালিয়ে কোনো crash নেই।
4. Line 2-এর `BUILD` stamp দেখে বুঝবেন editor-এ কোন version আছে।

## "Execution timed out" হলে (P1e)
- Indie-তে মোট bar সংখ্যা বা "এখনকার সময়" জানার উপায় নেই (`bar_count` = এ পর্যন্ত গোনা bar)। তাই নতুন setting **"Calculate from date"** (default `2026-10-15`) — এর আগের bar-এ হিসাব হয় না।
- Timeout হলে তারিখটা আরও কাছে আনুন (যেমন `2026-11-01`)। চললে পিছিয়ে দিন। ফাঁকা রাখলে পুরো history।
- Panel-এর প্রথম row-এ কত bar হিসাব হলো দেখায় (`5 → 60 · 4800 bars`)।
- **DIAGNOSTIC** setting: "1 Structure only" … "4 + setups" — কোন অংশ ভারী তা খুঁজতে। স্বাভাবিক ব্যবহারে "All layers"।
- আঁকা হয় শুধু শেষ bar-এ (history-তে draw নেই); per-bar object তৈরি বন্ধ; দূরের zone skip — ফলাফল আগের মতোই।

## TradingView-এর সাথে যা হুবহু (logic 1:1, default একই)
- Structure: BOS / CHoCH (real/fake) / weak / internal / CISD / pullback, protected swing (major H/L dashed line)
- FVG (TOUCH mitigation-এ মুছে যায়), liquidity line: BSL/SSL dotted, **POOL·EQH/EQL** dashed কমলা, PDH/PDL/PWH/PWL, Asia SESH/SESL
- Zone: OB (T1/T1b/T2/G2, ★), BRK, **RCB▲/▼**, **QM**, RJB, KL/KL★, ⇈PROP, **IDM✓**, **★★**, ⚠SWEEP REQ — screenshot-এর box গুলো
- HTF bias tint (BEAR লাল / BULL সবুজ), HTF candle O/H/L/C নীল line, M64 trendline
- সব setup M01…M74, POI tap→confirm machine, score/grade, gate, PD block, identity/gap, RETRACE / M74 ⏳ limit (filled / ✖ SL / expired / replaced)
- Signal label: `▲ M08 A9 · 2.4R`, entry/SL/TP1-3 line
- Panel 16 row (Chart/HTF … Watch) — ডান-নিচে

## পার্থক্য (Indie-র সীমাবদ্ধতা)
- **Alert নেই** (Indie-তে alert API নেই), label tooltip নেই, data-window plot নেই।
- Indie rectangle-এ text বসে না → zone-এর লেখা আলাদা label। লেখা box-এর বাইরে বসলে setting **"Zone / level caption anchor"** বদলান।
- Extend-right নেই → জীবিত zone/level/FVG শেষ bar থেকে `ext_bars` (12) bar ডানে টানা হয়।
- HTF / Daily / Weekly candle chart bar থেকে বানানো। Forex/CFD-তে দিন শুরু 17:00 New York (TV-র মতো); crypto হলে setting **Symbol type = Crypto / stocks** দিন (দিন = 00:00 UTC, killzone auto-filter বন্ধ)।
- Killzone auto-filter: Pine `syminfo.type` দেখে; এখানে ওই **Symbol type** setting।
- Volume key-level criterion বাদ (Pine-এ default OFF)। Color input নেই (TV-র default রং fixed)।
- Signal শুধু closed bar-এ (Pine-এর মতোই)। History depth আলাদা হলে প্রথম দিকের zone/level TV থেকে সামান্য আলাদা হতে পারে।
