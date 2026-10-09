# LQ-SD-PA v3.6 — Review রিপোর্ট ও v3.7 পরিবর্তন

তারিখ: 2026-10-09 · ফাইল: `liqudity_trap_trading.v3.6.txt` → `liqudity_trap_trading.v3.7.txt`

## সংক্ষেপে

- **কোনো CRITICAL সমস্যা নেই।** TradingView-এ runtime crash হতে পারে এমন কোনো পথ পাওয়া যায়নি।
- **Repaint হয় না।** সাতটা `request.security`-ই `[1]` + `lookahead_on` মানে, আর সব signal ও alert bar close-এ fire করে।
- **মূল সমস্যা trading logic-এ।** দুটো HIGH আর প্রায় দশটা MEDIUM ভুল পাওয়া গেছে। এগুলোর কারণে কিছু ভুয়া sweep হয়, score ফুলে যায়, আর break-even trade-কে loss গোনা হয়।
- **v3.7-এ ১৩টা fix-group বসানো হয়েছে।** নতুন input বা output slot যোগ হয়নি। Token খরচ পূরণ করতে ৪২টা কম-দরকারি tooltip সরানো হয়েছে। স্বাধীন review-এর হিসাবে fix গুলো প্রায় ২৫ token বেশি নেয়। পরে সরানো ২২টা tooltip সেই খরচ ঢেকে আরও margin দেয়।
- **Compile এখনো যাচাই হয়নি।** Local-এ Pine compiler নেই, তাই TradingView-এ paste করে দেখতে হবে।

## যা ঠিক আছে (যাচাই করা)

| বিষয় | ফল |
|---|---|
| Array loop (১১টা) | সব উল্টো দিকে চলে, খালি-array guard আছে |
| HTF data | `[1]` + lookahead_on, history আর live একই |
| Session / killzone | America/New_York time-এ, DST TradingView নিজে সামলায় |
| ICT window | London KZ 02-05, SB 03-04 / 10-11 / 14-15 NY, ঠিক আছে |
| Spread geometry | Long ask-এ fill, bid-এ SL/TP; short উল্টো, ঠিক আছে |
| একই bar-এ SL ও TP | SL আগে ধরা হয় (রক্ষণশীল), ঠিক আছে |
| OTE / Premium-Discount | দুই দিকেই 0.62-0.79 ঠিক |
| Long/Short mirror | প্রায় সব branch line-by-line মেলে |

## পাওয়া সমস্যা ও v3.7 সমাধান

### HIGH

1. **Break-even stop-কে loss গোনা হতো (FIX-Z10)।** TP1-এর পর stop entry-তে সরে যায়। সেখানে stop হলে `lossToday` বাড়ত। দুটো BE trade-এর পরই daily loss limit পুরো দিনের জন্য indicator বন্ধ করে দিত। এখন TP1-এর আগে stop হলেই কেবল loss গোনা হয়।
2. **আগেই ভাঙা swing আবার "sweep" হতো (FIX-Z1)।** দাম swing low-এর নিচে close করে সেখানে থেকে যাওয়ার পর নিচ থেকে retest করলে সেটাকে sweep ধরা হতো। Institutional দৃষ্টিতে এটা raid না, ভাঙা level-এর retest। এখন ভাঙা level-এ এক-bar sweep হয় না। FIX-Y3-এর ৪-bar reclaim path আগের মতোই আছে।

### MEDIUM

3. **PDH/PDL/PWH/PWL শুধু sweep হলে "খরচ" হতো (FIX-Z2)।** সকালে PDH-এর উপরে close হয়ে accept হলেও পরে wick দিয়ে আবার sweep ধরা হতো। এখন level একবার trade হলেই খরচ।
4. **Multi-bar sweep-এ break-এর গভীরতা grade বাড়াত (FIX-Z3)।** গভীর breakdown-এর পর দুর্বল reclaim candle-ও "valid" grade পেত। এখন grade reclaim candle-এর নিজের penetration দিয়ে হয়।
5. **HTF timeframe chart-এর চেয়ে ছোট হলেও "live" ধরা হতো (FIX-Z4, Z5)।** যেমন 4H chart-এ HTF "60" দিলে প্রতি bar-এ HTF signal আসত। এখন seconds তুলনা হয়, আর bias TF কখনো chart TF-এর নিচে যায় না।
6. **১-tick FVG-ও FVG ধরা হতো (FIX-Z6)।** Gold আর BTC-তে noise gap SB/FEM-এর anchor হয়ে যেত। এখন FVG-র উচ্চতা অন্তত `minZoneAtr` × ATR হতে হবে। ফলে SB-র FVG সীমা কার্যত `sbFvgMinAtr` আর `minZoneAtr`-এর মধ্যে যেটা বড় সেটা। Manual profile-এ `minZoneIn` = 0 দিলে শূন্য-উচ্চতার gap-ও ঢুকবে, তাই 0 দেবেন না।
7. **"DEMAND ★HP" star ভুল জায়গায় বসত (FIX-Z7)।** পুরোনো pivot-এর উপরে যেকোনো close-কে structure break ধরা হতো। এখন এই displacement leg-কেই structure ভাঙতে হবে।
8. **FEM HTF POI ভাঙার পরও চলত (FIX-Z8)।** দাম demand POI-এর নিচে close করলে এখন setup reset হয়।
9. **Score-এ একই touch দুবার গোনা হতো (FIX-Z9)।** Anchor touch POI-তে ১০ আর execution-এ ৫ পেত। এখন একবারই গোনা হয়। **ফলে stage-3 score প্রায় ৫ কমবে।** Signal কমে গেলে `minScore` ৫০ থেকে ৪৫ করে দেখুন।
10. **Premium-এ buy অনুমোদিত ছিল (FIX-Z13)।** `mcPdWaive` default চালু থাকায় trend-এ premium-এ long নেওয়া যেত। এখন default বন্ধ। Trend continuation চাইলে input থেকে চালু করুন।
11. **Arming-এর পর আরও গভীর sweep হলে stop সরত না (FIX-Z11)।** Shift-এর আগে নতুন গভীর wick হলে এখন stop সেই wick-এর বাইরে যায়।
12. **FEM alert gate-এ বাদ পড়া signal-এও fire করত (FIX-Z13)।** এখন শুধু চূড়ান্ত signal-এ fire করে।

### LOW (v3.7-এ ঠিক করা)

- Short stop-এ spread যোগ হয়, কারণ ask দিয়ে hit হয় (FIX-Z13)।
- Deferred long-এর gap পরীক্ষা এখন bid open দিয়ে হয়।
- বাদ পড়া machine signal-এর পুরোনো CE fill flag মুছে ফেলা হয় (FIX-Z12)।
- পুরোনো "lookahead_off" comment ঠিক করা হয়েছে।

## Token-এর অভাবে বাকি রাখা (v3.8 প্রার্থী)

অগ্রাধিকার অনুযায়ী:

1. **CE limit alert আগেভাগে।** Anchor lock হলে CE দাম সহ একটা alert দরকার, যাতে limit order আগে বসানো যায়। এখন alert আসে fill-এর পরে। এটাই বাস্তব trading-এর সবচেয়ে বড় ফাঁক। খরচ প্রায় ৬০ token।
2. **Trap level mute হলে retry হয় না।** LT signal cooldown বা gate-এ বাদ পড়লে level চিরতরে খরচ হয়ে যায়।
3. **Pool sweep-এর grade কমপক্ষে ২।** EQH/PDH-এ ১-tick poke-ও "valid" হয়। Swing sweep-এর মতো "weak" ধাপ দরকার।
4. **Weak-body break latch খেয়ে ফেলে।** ছোট body-র প্রথম close latch ধরে ফেলে, তাই পরের displaced candle BOS পায় না।
5. **OB শুধু bar[2]।** "Displacement-এর আগের শেষ বিপরীত candle" পুরো নিয়মে খোঁজা হয় না, আর OB structure break-এর সাথে যুক্ত না।
6. **Direction lock-এ টাই হলে সবসময় long জেতে।**
7. **Crypto-তে দিনের সীমা UTC।** PDH/PDL আর daily limit UTC দিনে চলে, অথচ `tradeDays` NY দিনে চলে। Default `23456` BTC-র weekend বন্ধ রাখে।
8. **আগের deferred তালিকা।** SMT, true day open, HTF sweep, weekend gap।

## Symbol অনুযায়ী পরামর্শ

| Symbol | Profile | Spread (`spreadIn`, tick-এ) |
|---|---|---|
| EURUSD / GBPUSD | FX majors | ১ pip = ১০ tick → ১০-১৫ |
| XAUUSD | Metals / XAU | broker spread ÷ mintick (সাধারণত ২০-৩৫) |
| NAS100 / US30 | Indices | broker অনুযায়ী |
| BTCUSDT | Crypto | `tradeDays` = `1234567` দিলে weekend-ও চলবে |

## যাচাই করার ধাপ

1. Pine Editor-এ v3.7 paste করুন। প্রথম লাইনে `BUILD v3.7-b1` দেখা যাচ্ছে কি না দেখুন।
2. "Add to chart" করুন। CE10117 এলে error-এ token সংখ্যা জানাবেন, আরও presentation কাটা হবে।
3. EURUSD M5, XAUUSD M5, NAS100 M15, BTCUSDT M15-এ খুলে দেখুন dashboard, signal label আর runtime error।
4. v3.6 আর v3.7 পাশাপাশি রাখুন। একই bar-এ কোন signal বাদ গেছে, আর বাদ যাওয়াটা যুক্তিসঙ্গত কি না দেখুন।
