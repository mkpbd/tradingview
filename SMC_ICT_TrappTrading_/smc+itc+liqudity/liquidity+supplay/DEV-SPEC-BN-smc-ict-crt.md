# SMC + ICT + Liquidity + Supply-Demand Indicator — ডেভেলপার বিল্ড স্পেসিফিকেশন

> উৎস: `smc_ict_crt.txt` (PKR Trading চ্যানেলের ভিডিও ট্রান্সক্রিপ্ট, ১৬৪৬ লাইন)। এই ডকুমেন্টে সেই ট্রান্সক্রিপ্ট থেকে সব প্রমোশনাল/ভূমিকা/লাইক-সাবস্ক্রাইব অংশ বাদ দিয়ে শুধু **কোড করা যায় এমন ট্রেডিং লজিক** বের করে, ডেভেলপারের জন্য গুছিয়ে সাজানো হয়েছে।
>
> **লক্ষ্য:** TradingView Pine Script ইনডিকেটর ডেভেলপ করা — যেটা এই ডকুমেন্টে বর্ণিত SMC/ICT/Liquidity/Price-Action প্যাটার্নগুলো অটো-ডিটেক্ট করে চার্টে দেখাবে এবং অ্যালার্ট দেবে।

---

## ০. এই প্রজেক্টের বর্তমান অবস্থা (Context)

এই ফোল্ডারে (`liquidty+supplay`) আগে থেকেই একটা বড় Pine Script ইনডিকেটর লিনিয়েজ চলছে (v4 থেকে v7.5 পর্যন্ত, ২৫টা numbered ফাইল)। প্রতিটা নতুন ভার্সনের জন্য **নতুন numbered ফাইল** বানাতে হয় (পুরনো ফাইল ওভাররাইট না করে) — কারণ Pine Script-এর compile সাইজ লিমিট আছে এবং একটা নির্দিষ্ট সাইজের পরে script compile ফেল করে।

**ডেভেলপারের জন্য জরুরি নোট:**
- Pine Script-এ **compile token/লাইন লিমিট** আছে। এই লিনিয়েজে আগে মাপা caps: ~CE10117 tokens এবং ~CE10295 main-body লাইনে গিয়ে compile ফেইল করেছে।
- তাই **৯৬টা প্যাটার্ন একসাথে এক স্ক্রিপ্টে ঢোকানোর চেষ্টা করবেন না।** এর আগেও এই সমস্যা হয়েছে বলেই আলাদা "companion overlay" script বানানো হয়েছে (ফাইল 10, 12, 15 — যেমন `ict-forensic-layer`, `retail-pa-forensic-layer`, `crt-tbs-tws-mtf-layer`)। নতুন ক্যাপাবিলিটি যোগ করার সময় একই প্যাটার্ন follow করুন: হয় existing main engine-এ যোগ করুন যতক্ষণ compile পাশ করে, নাহলে আলাদা companion overlay বানান।
- প্রতিটা নতুন ভার্সনের সাথে একটা `AUDIT-vX.md` ফাইলও বানানো হয়েছে — সেই কনভেনশন বজায় রাখুন (কী যোগ হলো, কী বাগ ফিক্স হলো, তার লগ)।

**তাই এই স্পেকের ব্যবহারবিধি:** পুরো ডকুমেন্ট একবারে implement করার প্ল্যান না করে, নিচের **সেকশন ৩ (ইমপ্লিমেন্টেশন প্রায়োরিটি)** অনুযায়ী ধাপে ধাপে (ফেজ ধরে) করুন।

---

## ১. দরকারি "বিল্ডিং ব্লক" (Core Reusable Logic)

নিচের প্যাটার্ন ক্যাটালগে থাকা ৯৬টা সেটআপের বেশিরভাগই আসলে এই কয়েকটা মৌলিক জিনিসের বিভিন্ন কম্বিনেশন মাত্র। তাই প্রথমে এই ফাংশনগুলো আলাদাভাবে বানিয়ে নিলে বাকি সব প্যাটার্ন লেখা সহজ হবে।

1. **Swing High / Swing Low ডিটেকশন** — pivot-based (`ta.pivothigh` / `ta.pivotlow`), lookback configurable।
2. **ক্যান্ডেল বডি/উইক মাপার ইউটিলিটি** — body size, upper wick, lower wick, এবং এদের অনুপাত। বেশিরভাগ সেটআপে দরকার হয় "আগের ক্যান্ডেলের উইক থেকে বড়/ছোট" — তাই ফাংশন এমনভাবে বানান যাতে আগের N ক্যান্ডেলের সাথে তুলনা করা যায়।
3. **Doji ডিটেকশন** — body size threshold (range-এর তুলনায় খুব ছোট body)।
4. **Pin Bar ডিটেকশন** (bullish/bearish) — এক দিকের wick অন্য দিকের তুলনায় ও body-এর তুলনায় বড় (সাধারণত 2x-3x)।
5. **Engulfing ডিটেকশন** (bullish/bearish) — বর্তমান ক্যান্ডেলের body আগের ক্যান্ডেলের পুরো body/range ঢেকে দেয়।
6. **Inside Bar ডিটেকশন** — বর্তমান ক্যান্ডেলের high/low আগের ক্যান্ডেলের high/low-এর ভেতরে।
7. **Imbalance / Fair Value Gap (FVG) ডিটেকশন** — ৩-ক্যান্ডেল গ্যাপ লজিক (candle[1] এর high/low, candle[3] এর low/high-এর মধ্যে gap)।
8. **Order Block (OB) ডিটেকশন + validity ফিল্টার** — যে ক্যান্ডেল swing high/low বানিয়েছে তার color না দেখে, শুধু structural role দেখে মার্ক করা। Valid হওয়ার শর্ত: FVG সাথে align করে + এখনো mitigate হয়নি (unmitigated) + এর পরে BOS/CHoCH হয়েছে।
9. **BOS / CHoCH ডিটেকশন — valid vs fake** — শুধু wick দিয়ে লেভেল টাচ করলে হবে না, **candle close** দিয়ে লেভেল ক্রস করতে হবে ভ্যালিড ধরার জন্য। Sweep-qualified CHoCH-ও আলাদা করে হ্যান্ডল করতে হবে (নিচে #59 দেখুন)।
10. **Liquidity Zone / Equal Highs-Lows ডিটেকশন** — কাছাকাছি প্রাইসে ≥২ বার টাচ হওয়া high/low গুলো গ্রুপ করে liquidity pool হিসেবে মার্ক করা (tolerance % বা ATR-based)।
11. **Liquidity Sweep vs Liquidity Run ক্লাসিফায়ার** — এটা পুরো স্ট্র্যাটেজির সবচেয়ে গুরুত্বপূর্ণ বিল্ডিং ব্লক (নিচের অনেক সেটআপে বারবার লাগবে): লেভেল ব্রেক করার ক্যান্ডেলের close যদি লেভেলের ওপারে stay করে (strong body) → **Run** (আসল breakout, fade করবেন না)। যদি শুধু wick দিয়ে ভেঙে close ফিরে আসে (long wick, ছোট body) → **Sweep** (fade করার সুযোগ)।
12. **ভলিউম কম্প্যারিজন** — বর্তমান ক্যান্ডেলের ভলিউম বনাম গড় ভলিউম (SMA of volume, ২০-৫০ পিরিয়ড), "high volume" থ্রেশহোল্ড ইনপুট করা যায় এমন।
13. **Multi-Timeframe (HTF) ডেটা রিকোয়েস্ট + টাইমফ্রেম পেয়ারিং টেবিল** — `request.security()` দিয়ে HTF ক্যান্ডেল আনা। ট্রান্সক্রিপ্টে বারবার এই পেয়ারিং টেবিল এসেছে (ইনপুট হিসেবে configurable রাখুন):

   | Entry TF | Confirm করার HTF |
   |---|---|
   | 1m | 15m |
   | 3m | 30m |
   | 5m | 1H |
   | 15m | 4H |
   | 30m | 4H |
   | 1H | Daily |

14. **Fibonacci 50% জোন ক্যালকুলেশন** — একটা range (high–low)-এর মাঝের 50% লেভেল বের করা (discount/premium জোন এবং OB/zone validity ফিল্টারে বহুবার লাগবে)।
15. **CRT Ranging Candle + TBS/TWS ক্লাসিফায়ার** — Candle Range Theory-র জন্য আলাদা মডিউল (দেখুন ক্যাটাগরি ৪০, খুবই precise rule, নিচে বিস্তারিত)।

---

## ২. প্যাটার্ন ক্যাটালগ (৪০ ক্যাটাগরি, ৯৬টা সেটআপ)

> প্রতিটা সেটআপে ৫টা জিনিস দেওয়া আছে: **চার্ট কন্ডিশন** (এই সেটআপ কখন apply হয়), **ট্রিগার** (ঠিক কোন ক্যান্ডেল প্যাটার্ন/শর্ত কোড করতে হবে), **এন্ট্রি**, **স্টপ লস**, **টার্গেট**, **বায়াস** (বুলিশ/বেয়ারিশ/উভয়)।
>
> যেখানে ট্রান্সক্রিপ্টে শুধু এক দিকের (bullish বা bearish) উদাহরণ দেওয়া হয়েছে কিন্তু mirror version স্পষ্টভাবেই প্রযোজ্য, সেখানে "(mirror প্রযোজ্য)" লেখা আছে — ডেভেলপার উভয় দিকের কোড লিখবে।

### ক্যাটাগরি ১ — Price Action Setups (৪টা বেসিক প্রাইস অ্যাকশন সেটআপ)

**১. Breakout Rejection Trap Model (বেয়ারিশ)**
- চার্ট কন্ডিশন: একটা resistance level বহুবার টেস্ট/রিজেক্ট হয়েছে (উপরে stop-loss liquidity জমা)।
- ট্রিগার: প্রাইস লেভেল ব্রেক করে ব্রেকআউটের পর ≥২টা ক্যান্ডেল লম্বা upper wick নিয়ে ফর্ম করে — শর্ত: প্রতিটা rejection ক্যান্ডেলের upper wick আগেরটার চেয়ে **বড়** হতে হবে (ক্রমশ বাড়তে থাকা wick = বিক্রেতারা আরও শক্তিশালী হচ্ছে)।
- এন্ট্রি: লেভেলের নিচে close হওয়া strong bearish ক্যান্ডেলের close-এ।
- স্টপ লস: সেই confirming bearish ক্যান্ডেলের high-এর ওপরে।
- টার্গেট: পরের key level।
- বায়াস: বেয়ারিশ (mirror প্রযোজ্য)।

**২. Pin Bar Liquidity Trap Model**
- চার্ট কন্ডিশন: key level ব্রেক আউট হয়েছে।
- ট্রিগার: ব্রেকআউটের পর একাধিক long-upper-wick bearish pin bar ফর্ম হয়, যেখানে **প্রতিটার wick আগেরটার চেয়ে ছোট** হতে থাকে (কমতে থাকা wick = বিক্রেতা দুর্বল হচ্ছে, রিটেইল ফাঁদে পড়ছে)।
- এন্ট্রি: এই সিকোয়েন্সের পর bullish reversal সিগন্যাল (bullish pin bar / bullish engulfing) এর close-এ।
- স্টপ লস: reversal ক্যান্ডেলের নিচে।
- টার্গেট: pin bar high-গুলোর ওপরের liquidity / পরের key level।
- বায়াস: বুলিশ (mirror প্রযোজ্য)।

**৩. Inside Bar Breakout**
- চার্ট কন্ডিশন: key level-এ প্রাইস পৌঁছে ব্রেক করে।
- ট্রিগার: ব্রেকআউট ক্যান্ডেলের পরের ক্যান্ডেল একটা **inside bar** হতে হবে (ব্রেকআউট ক্যান্ডেলের high/low-এর ভেতরে সম্পূর্ণ থাকবে), এবং inside bar-এর পুরো body+wick range ব্রেকআউট ক্যান্ডেলের **50%-এর ওপরে** থাকতে হবে (validity শর্ত)।
- এন্ট্রি: যে ক্যান্ডেল inside bar-এর high ব্রেক করে close করে।
- স্টপ লস: inside bar-এর নিচে।
- টার্গেট: পরের resistance/key level।
- বায়াস: বুলিশ (mirror প্রযোজ্য)। নোট: breakout-এর ঠিক পরের ক্যান্ডেল যদি লেভেলের নিচে close করে (inside bar না হয়ে), সেটা fake breakout।

**৪. Doji Move Reversal Setup**
- চার্ট কন্ডিশন: একটা strong move দিয়ে তৈরি key level।
- ট্রিগার: প্রাইস সেই লেভেলে ফিরে এসে **একাধিক Doji ক্যান্ডেল** ফর্ম করে (indecision)।
- এন্ট্রি: Doji ক্লাস্টারের পর strong reversal ক্যান্ডেল (bearish pin bar / bearish engulfing / strong bearish rejection) এর close-এ।
- স্টপ লস: reversal ক্যান্ডেলের ওপরে।
- টার্গেট: পরের support/key level।
- বায়াস: বেয়ারিশ শোন করা হয়েছে (mirror প্রযোজ্য)। ওভারল ট্রেন্ডের সাথে align থাকলে win-rate বাড়ে।

---

### ক্যাটাগরি ২ — Pin Bar Strategies (৫টা পিন বার স্ট্র্যাটেজি)

**৫. Pin Bar After Breakout** *(S&R ক্যাটাগরিতে টেকনিক #৪ ও #৫ হিসেবে একই লজিক আবার আসে)*
- চার্ট কন্ডিশন: key level ব্রেক আউট হয়।
- ট্রিগার: ব্রেকআউট ক্যান্ডেলের **ঠিক পরের** ক্যান্ডেল breakout দিকেই strong pin bar ফর্ম করে (যেমন upside breakout-এর পর প্রাইস ব্রেকেন লেভেলের দিকে ডিপ করে আবার buyer পুশ করে long lower wick তৈরি করে বুলিশ pin bar বানায়)।
- এন্ট্রি: এই pin bar-এর close-এ।
- স্টপ লস: pin bar-এর নিচে (বুলিশ কেস) / ওপরে (বেয়ারিশ কেস)।
- টার্গেট: নির্দিষ্ট বলা নেই (পরের resistance ধরে নেওয়া যায়)।
- বায়াস: উভয়। **রিপিট নোট:** S&R Secrets Part 2-এ "pin bar after breakout" (breakout ক্যান্ডেল, তারপর পরের ক্যান্ডেল ডিপ করে flipped level থেকে রিজেক্ট হয়ে বুলিশ pin bar বানায়) এবং "breakout with a pin bar candle" (breakout ক্যান্ডেল **নিজেই** pin bar — আগে ডিপ করে, তারপর রিজেক্ট হয়ে breakout করে pin bar হিসেবে close করে) — দুটোই একই লজিক, শুধু টাইমিং (কোন ক্যান্ডেলে pin bar হচ্ছে) আলাদা।

**৬. Multiple Pin Bar Candles on Pullback**
- চার্ট কন্ডিশন: বুলিশ আপট্রেন্ড স্ট্রাকচার, প্রাইস pullback দিচ্ছে।
- ট্রিগার: pullback-এর মধ্যে একাধিক pin bar ফর্ম হয় (bear বারবার চেষ্টা করছে, buyer বারবার পুশ ব্যাক করছে)।
- এন্ট্রি: pullback একটা গুরুত্বপূর্ণ support level-এ পৌঁছে সেখানে strong bullish pin bar ফর্ম করলে — সেই pin bar-এর close-এ।
- স্টপ লস: সেই pin bar-এর নিচে।
- টার্গেট: নির্দিষ্ট বলা নেই।
- বায়াস: বুলিশ (mirror প্রযোজ্য — ডাউনট্রেন্ড pullback-এ)।

**৭. Multiple Pin Bar Candles on an Impulsive Move (ফাঁদ)**
- চার্ট কন্ডিশন: আপট্রেন্ড, প্রাইস একটা strong **impulsive** মুভ দিচ্ছে (pullback না)।
- ট্রিগার: impulsive লেগের **ভেতরেই** একাধিক bullish pin bar ফর্ম হয় (রিটেইল প্রতিটা pin bar-এর নিচে stop loss রেখে বাই করছে → নিচে liquidity জমা হচ্ছে)।
- এন্ট্রি: এখানে বাই করা যাবে না। মুভের টপে reversal সিগন্যাল (shooting star / bearish engulfing) এর জন্য অপেক্ষা করে **শর্ট** এন্ট্রি।
- স্টপ লস: reversal ক্যান্ডেলের ওপরে।
- টার্গেট: pin bar low-গুলোর নিচের liquidity, তারপর আরও নিচে।
- বায়াস: বেয়ারিশ রিভার্সাল ট্রেড (সেটআপ নিজেই একটা বুলিশ-মুভ ফাঁদ)।

**৮. Pin Bar on Retracement**
- চার্ট কন্ডিশন: ওভারল বুলিশ ট্রেন্ড (HH/HL), প্রাইস একটা key support-এ pull back করছে।
- ট্রিগার: সেই support লেভেলেই একটা strong bullish pin bar ফর্ম হয় (বড় lower wick — buyer ডিফেন্ড করেছে)।
- এন্ট্রি: pin bar-এর close-এ।
- স্টপ লস: pin bar-এর নিচে।
- টার্গেট: নির্দিষ্ট বলা নেই।
- বায়াস: বুলিশ (mirror প্রযোজ্য)।

**৯. Pin Bar + Liquidity কনফ্লুয়েন্স সেটআপ** (বক্তার "ফেভারিট" সেটআপ)
- চার্ট কন্ডিশন: একটা গুরুত্বপূর্ণ লেভেলের কাছে যেকোনো দিকের মুভ।
- ট্রিগার: লেভেলে strong pin bar ফর্ম হয় **এবং** একই দিকে একাধিক liquidity level (equal highs/lows, swing points) থাকে।
- এন্ট্রি: liquidity confluence থাকলে pin bar-এর close-এ।
- স্টপ লস: pin bar-এর extreme-এর বাইরে।
- টার্গেট: চিহ্নিত liquidity pool(গুলো)।
- বায়াস: উভয়। **সাধারণ নিয়ম:** যেকোনো সেটআপে liquidity confluence যোগ হলে সেটার কোয়ালিটি/probability বাড়ে — এটা একটা universal filter হিসেবে কোড করা উচিত।

---

### ক্যাটাগরি ৩ — Stoploss / Liquidity Hunting Strategy

**১০. Liquidity Run vs. Liquidity Sweep** (মূল ডিস্টিংশন + ট্রেড — এটা #১১ বিল্ডিং ব্লক)
- চার্ট কন্ডিশন: স্পষ্ট, বহুবার টেস্ট হওয়া resistance/support (যত বেশি টেস্ট, তত বেশি জমে থাকা liquidity)।
- ট্রিগার (Run বনাম Sweep আলাদা করা):
  - **Liquidity Run (fade করবেন না):** প্রাইস লেভেল ব্রেক করে এবং একটা বড় body-র ক্যান্ডেল লেভেলের অনেক ওপরে close করে (আসল breakout)।
  - **Liquidity Sweep (ট্রেড করার সুযোগ):** প্রাইস লেভেলের ওপরে যায় কিন্তু ক্যান্ডেল ওপরে close করে না (বা সামান্য ওপরে করে), wick body-র তুলনায় লম্বা; পরের ক্যান্ডেলই লেভেলের নিচে ফিরে আসে।
- এন্ট্রি (দুই পদ্ধতি):
  1. **Immediate entry:** sweep/rejection (pin bar) ক্যান্ডেলের close-এ। বড় target, বেশি risk।
  2. **Retest entry:** প্রাইস নিচে নেমে ব্রেকেন লেভেলে retest করে আবার রিজেক্ট হলে — নিরাপদ, কম risk।
- স্টপ লস: sweep-এর high-এর ঠিক ওপরে।
- টার্গেট: পরের major support/previous low, অথবা ন্যূনতম 1:3 R:R — যেটা আগে আসে।
- বায়াস: বেয়ারিশ শোন (mirror প্রযোজ্য)।

---

### ক্যাটাগরি ৪ — Support & Resistance Strategy Part 2

**১১. Doji Plus Breakout**
- চার্ট কন্ডিশন: resistance/support level-এ প্রাইস পৌঁছায়।
- ট্রিগার: লেভেলে একটা Doji ফর্ম হয়, তারপর **পরের ক্যান্ডেল Doji-র high এবং resistance level দুটোই ব্রেক করে** (buyer strength কনফার্ম)। Mirror: support-এ Doji-র low + support level break।
- এন্ট্রি: এই break ক্যান্ডেলের close-এ।
- স্টপ লস: নির্দিষ্ট বলা নেই (Doji-র high/low-এর বিপরীতে ধরা যায়)।
- টার্গেট: নির্দিষ্ট বলা নেই।
- বায়াস: উভয়।

**১২. Confluence Zone**
- চার্ট কন্ডিশন: trend line অনুসরণ করে বুলিশ ট্রেন্ড; একটা pullback থেকে resistance তৈরি হয়; সেই resistance ব্রেক হয়ে support-এ ফ্লিপ হয়; প্রাইস আবার pull back করে যেখানে flipped support ও trend line **ওভারল্যাপ** করে।
- ট্রিগার: এই কনফ্লুয়েন্স জোনে bullish reversal সিগন্যাল।
- এন্ট্রি: রিভার্সাল সিগন্যালে।
- স্টপ লস/টার্গেট: নির্দিষ্ট বলা নেই।
- বায়াস: বুলিশ শোন (mirror প্রযোজ্য)।

**১৩. Trend-Based Support/Resistance (শুধু ট্রেন্ডের দিকে ট্রেড করা)**
- নিয়ম (filter, standalone সেটআপ না): বুলিশ ট্রেন্ডে শুধু support-এ **buy-side** reversal সিগন্যাল নেওয়া, resistance-এ sell সিগন্যাল উপেক্ষা করা (এগুলো বেশি fail করে)। বেয়ারিশ ট্রেন্ডে উল্টো — শুধু resistance-এ sell সিগন্যাল।
- বায়াস: directional filter, উভয় দিকে প্রযোজ্য।

**১৪/১৫.** Pin Bar After Breakout / Breakout With Pin Bar Candle — *সেটআপ #৫-এর ডুপ্লিকেট, ক্যাটাগরি ২ দেখুন।*

---

### ক্যাটাগরি ৫ — Volume Strategies

**১৬. Resistance Volume Reversal Strategy**
- চার্ট কন্ডিশন: strong resistance (আগের strong down-move থেকে তৈরি)।
- ট্রিগার: প্রাইস **দুর্বল মুভ** দিয়ে (কোনো imbalance ছাড়া) resistance-এ পৌঁছায়; লেভেলে reversal ক্যান্ডেল (pin bar/engulfing) ফর্ম হয় **গড় ভলিউমের চেয়ে অনেক বেশি ভলিউমে**।
- এন্ট্রি: হাই-ভলিউম reversal ক্যান্ডেলের close-এ।
- স্টপ লস: reversal ক্যান্ডেলের ওপরে।
- টার্গেট: নির্দিষ্ট বলা নেই।
- বায়াস: বেয়ারিশ (mirror প্রযোজ্য)।

**১৭. Bullish Trap / Real-Breakout-by-Volume Strategy**
- চার্ট কন্ডিশন: resistance-এর দিকে ছোট body-র ক্যান্ডেল দিয়ে প্রাইস এগোচ্ছে।
- ট্রিগার: resistance-এ **হাই ভলিউমে** strong bullish ক্যান্ডেল ব্রেকআউট করে (হাই ভলিউম + strong candle = institutional buying, আসল breakout)।
- এন্ট্রি: breakout ক্যান্ডেলের close অথবা retest-এ।
- স্টপ লস/টার্গেট: নির্দিষ্ট বলা নেই।
- বায়াস: বুলিশ (mirror প্রযোজ্য)।

**১৮. Volume Price Divergence Strategy**
- চার্ট কন্ডিশন: বুলিশ স্ট্রাকচার, প্রাইস pullback শুরু করছে।
- ট্রিগার: pullback-এর সময় **ভলিউম কমছে** (seller দুর্বল, তাই এটা আসল/ট্রেডযোগ্য pullback, রিভার্সাল না)।
- এন্ট্রি: এই কম-ভলিউম pullback-এর মধ্যে প্রাইস কোনো লেভেল টাচ করে reversal ক্যান্ডেল বানালে।
- বায়াস: বুলিশ কন্টিনিউয়েশন (mirror প্রযোজ্য)।

**১৯. Displacement Trap Volume Strategy**
- চার্ট কন্ডিশন: key level; প্রাইস displacement/imbalance তৈরি করে strong মুভে এগোচ্ছে।
- ট্রিগার: key level-এ **অনেক আগের ক্যান্ডেলের তুলনায় খুব হাই ভলিউমে** strong bullish ক্যান্ডেল ব্রেকআউট করে — কিন্তু এটা smart money-র ফাঁদ (FOMO buyer টেনে এনে profit বুক করার জন্য), আসল breakout না।
- এন্ট্রি: এই breakout কিনবেন না। breakout ক্যান্ডেলের পরে reversal ক্যান্ডেলের (bearish pin bar/engulfing/লেভেলের নিচে close) জন্য অপেক্ষা করে **শর্ট**।
- বায়াস: বেয়ারিশ (mirror প্রযোজ্য)।

**২০. Bullish FOMO Trap Strategy** (মিড-ট্রেন্ড ভলিউম ফাঁদ)
- চার্ট কন্ডিশন: ধারাবাহিক green ক্যান্ডেল দিয়ে বুলিশ মুভমেন্ট (fresh key level-এ না, মাঝ ট্রেন্ডে)।
- ট্রিগার: মাঝপথে **গড়ের চেয়ে অনেক বেশি ভলিউমে** একটা strong bullish ক্যান্ডেল ফর্ম হয় — smart money-র profit-booking ফাঁদ।
- এন্ট্রি: এই ক্যান্ডেল কিনবেন না; ঠিক পরে reversal ক্যান্ডেল (bearish pin bar/engulfing) এলে শর্ট।
- বায়াস: বেয়ারিশ। (#১৯ থেকে পার্থক্য: এটা key level/breakout-এ না, মাঝ ট্রেন্ডে হয়।)

---

### ক্যাটাগরি ৬ — Market Structure Hacks

**২১. Corrective Pullback vs. Simple Pullback (ট্রেডযোগ্যতা ফিল্টার)**
- **Simple pullback (ট্রেড করবেন না):** ট্রেন্ডের বিপরীতে একই দিকের পরপর ক্যান্ডেল, pullback-এর ভেতরে **fresh imbalance/FVG দেখা যায়** → বিপরীত পক্ষ এখনো আক্রমণাত্মক, liquidity কম, প্রাইস আগে liquidity sweep করবে তারপর রিভার্স করবে।
- **Corrective pullback (ট্রেডযোগ্য):** মিশ্র red/green ক্যান্ডেল বা ছোট ছোট ইন্টারনাল pullback, **নতুন imbalance তৈরি হয়নি (বা আগেরটা mitigate হয়ে গেছে)** → স্বাস্থ্যকর pullback।
- এন্ট্রি: শুধু "corrective" টাইপ pullback হলেই reaction zone-এ reversal সিগন্যাল ট্রেড করুন।
- বায়াস: উভয়।

**২২. Valid vs. Invalid Break of Structure (BOS)**
- নিয়ম: BOS ভ্যালিড হবে শুধু তখনই যখন ক্যান্ডেল আগের higher high-এর **ওপরে close করে** (body sustain করে)। যদি শুধু **wick** দিয়ে আগের high-এর ওপরে যায় কিন্তু **close নিচে** হয় — এটা valid BOS না, বরং liquidity sweep / invalid BOS (ট্রেন্ড দুর্বল হওয়ার সতর্কসংকেত)।
- অ্যাকশন: যদি আগে থেকেই "BOS" ধরে ট্রেডে থাকেন আর পরে দেখা যায় এটা শুধু wick ছিল — stop trail করুন বা exit বিবেচনা করুন।
- বায়াস: উভয়।

**২৩. Reaction Zone Trap**
- নিয়ম: ট্রেন্ডের সময় তৈরি হওয়া order block/reaction zone শুধু তখনই ট্রেড করুন যখন প্রাইস সেখানে **দুর্বল মুভে** (কোনো imbalance ছাড়া, বা আগেরটা mitigate হয়ে গেছে) পৌঁছায়। যদি **strong মুভে (imbalance সহ)** পৌঁছায় — মানে বিপরীত পক্ষ এখন শক্তিশালী, reversal ট্রেড করবেন না (fail-rate বেশি)।
- বায়াস: উভয়।

**২৪. Strong Move Trap (দুর্বল-মুভ-যেন-শক্তিশালী = Fade সেটআপ)**
- চার্ট কন্ডিশন: আপট্রেন্ডে pullback-এর পর প্রাইস বড় বড় ক্যান্ডেল দিয়ে ওপরে যাচ্ছে কিন্তু **কোনো imbalance নেই** — এটা আসলে দুর্বল মুভ (FOMO টোপ), যদিও ক্যান্ডেল বড় দেখাচ্ছে।
- এন্ট্রি: টপে reversal সিগন্যালের জন্য অপেক্ষা করে শর্ট, target = এই মুভের swing low-গুলোর নিচের liquidity।
- বায়াস: বেয়ারিশ (mirror প্রযোজ্য)।

---

### ক্যাটাগরি ৭ — Fake vs. Real CHoCH (Power of Imbalance)

**২৫. Real vs. Fake Change of Character (imbalance দিয়ে validate)**
- নিয়ম: CHoCH তখনই **আসল/ট্রেডযোগ্য** যখন structure-ব্রেক করা মুভে **একাধিক imbalance/FVG** থাকে। কোনো imbalance না থাকলে এটা সাময়িক/fake CHoCH, fail করার সম্ভাবনা বেশি।
- এন্ট্রি: validated CHoCH-এর পর প্রাইস retrace করে reaction zone-এ (FVG/OB) reversal সিগন্যাল দিলে নতুন ট্রেন্ড দিকে এন্ট্রি।
- **breakout-এও প্রযোজ্য:** resistance/support-এর breakout শুধু তখনই ট্রেডযোগ্য (breakout দিকে) যখন breakout মুভে imbalance থাকে; imbalance ছাড়া breakout fade করা উচিত।
- বায়াস: উভয়।

---

### ক্যাটাগরি ৮ — Support & Resistance Secrets Part 1

**২৬. Zones Not Lines (মার্কিং নিয়ম)**
- নিয়ম: S/R একটা **zone** হিসেবে মার্ক করুন (reversal পয়েন্টের ওপরে/নিচে পুরো wick range), একটামাত্র লাইন না — যাতে প্রাইস ঠিক লাইনে না এসে আগেই রিভার্স করলে entry miss না হয়। (কোনো standalone ট্রেড না, marking rule।)

**২৭. Multiple-Touch Weakness + Third-Touch Sweep Reversal**
- চার্ট কন্ডিশন: একটা লেভেল **অন্তত দুবার** টেস্ট/রিজেক্ট হয়েছে (বেশি টাচ = বেশি জমে থাকা liquidity = লেভেল দুর্বল, শক্তিশালী না)।
- ট্রিগার: **তৃতীয়বার** প্রাইস আসার সময় লেভেল **sweep** হতে হবে (ব্রেক করে আবার ফিরে আসা) এবং bearish pin bar (resistance-এ) / bullish pin bar (support-এ) ফর্ম করতে হবে।
- এন্ট্রি: sweep + pin bar close-এ।
- নিয়ম: ১ম বা ২য় টাচে ট্রেড করবেন না — শুধু ৩য় (বা পরে) টাচে sweep হওয়ার পরে।
- বায়াস: উভয়।

**২৮. Support/Resistance Interchange (Role-Flip Retest)**
- চার্ট কন্ডিশন: resistance-এ প্রাইস পৌঁছে রিভার্স না করে **ব্রেকআউট করে**, support-এ ফ্লিপ হয়।
- এন্ট্রি: নতুন support-এ retracement করে reversal সিগন্যাল দিলে।
- বায়াস: বুলিশ শোন (mirror প্রযোজ্য)।

**২৯. Strong-Move / Weak-Reversal Trap (এড়িয়ে যান)**
- চার্ট কন্ডিশন: resistance-এ **imbalance সহ strong মুভে** পৌঁছেছে।
- নিয়ম: এমনকি সেখানে bearish pin bar/reversal ফর্ম করলেও sell করবেন না — strong-move approach মানে buyer আসলে ডমিনেন্ট, এই reversal সিগন্যাল প্রায়ই fail করে।
- বায়াস: filter rule (sell এড়িয়ে চলুন)।

**৩০. Weak-Move / Strong-Reversal Setup (ট্রেড করুন)**
- চার্ট কন্ডিশন: resistance আগে strong down-move দিয়ে তৈরি (ঐতিহাসিকভাবে strong seller)।
- ট্রিগার: প্রাইস এখন **দুর্বল মুভে, imbalance ছাড়া** resistance-এ পৌঁছায় (buyer এখন দুর্বল) এবং লেভেলে reversal সিগন্যাল দেয়।
- এন্ট্রি: reversal সিগন্যালে।
- বায়াস: বেয়ারিশ শোন (mirror প্রযোজ্য)।

---

### ক্যাটাগরি ৯ — Zone Flip Model

**৩১. Zone Flip Model (Breakout → Retest → Refusal)**
- চার্ট কন্ডিশন: একটা supply/resistance (বা demand/support) জোন আছে।
- ট্রিগার (৩ ধাপ):
  1. **Breakout:** imbalance সহ strong ক্যান্ডেল জোন ব্রেক করে (institutional signature দরকার)।
  2. **Retest:** প্রাইস flipped জোন **দুর্বল মুভে** retest করে — মিশ্র red/green, ছোট body, বা একাধিক pin bar।
  3. **Refusal:** retest-এ একটা reversal ক্যান্ডেল (pin bar/engulfing) ফর্ম হয়।
- এন্ট্রি: refusal ক্যান্ডেলের close-এ।
- **HTF/LTF পেয়ারিং টেবিল:** 1m entry → 15m HTF কনফার্ম; 3m → 30m; 5m → 1H; 15m → 4H।
- নিয়ম: শুধু **higher-timeframe ট্রেন্ডের** দিকে ট্রেড করুন; LTF শুধু precise entry-র জন্য।
- বায়াস: উভয়।

---

### ক্যাটাগরি ১০ — Real vs. Fake Order Block (৬টা সিক্রেট)

**৩২. Valid Order Block — মূল শর্ত**
- নিয়ম: OB ক্যান্ডেল হলো যেটা strong মুভের ঠিক আগে swing low (bullish OB) / swing high (bearish OB) **বানিয়েছে** — "শেষ বিপরীত-রঙের ক্যান্ডেল" এই সংজ্ঞা ভুল (color গুরুত্বপূর্ণ না)। ভ্যালিড শুধু তখনই যখন সেই ক্যান্ডেলের সাথে একটা **FVG** ফর্ম হয়।
- এন্ট্রি: প্রাইস OB-তে **দুর্বল মুভে (imbalance ছাড়া)** ফিরে এসে reversal/CHoCH সিগন্যাল দিলে — impulsive-move দিকেই এন্ট্রি।
- বায়াস: উভয়।

**৩৩. Inside-Bar Order Block Correction**
- চার্ট কন্ডিশন: impulsive মুভের আগে "শেষ বিপরীত ক্যান্ডেল" আসলে একটা **inside bar** (আগের ক্যান্ডেলের ভেতরে সম্পূর্ণ)।
- নিয়ম: inside bar-কে OB হিসেবে মার্ক করবেন না — আসল swing low/high বানানো **mother candle**-কে মার্ক করুন।

**৩৪. Mitigated-FVG Invalidates Order Block**
- নিয়ম: যদি OB ক্যান্ডেলের নিজের wick তার নিজের aligned FVG-কে **tap করে mitigate** করে ফেলে, OB invalid/দুর্বল হয়ে যায় — সেখানে reversal সিগন্যাল এলেও ট্রেড করবেন না।

**৩৫. Engulfed-Candle Order Block Correction**
- চার্ট কন্ডিশন: naive "শেষ red candle" আসলে পরের bullish (বা bearish) engulfing ক্যান্ডেল দিয়ে **সম্পূর্ণ engulfed**, এবং engulfing ক্যান্ডেলটাই আসল swing low/high বানিয়েছে।
- নিয়ম: engulfed ক্যান্ডেল না, **engulfing ক্যান্ডেলকে** OB হিসেবে মার্ক করুন।

**৩৬. No-Imbalance Move = No Order Block (Fade করুন)**
- চার্ট কন্ডিশন: বড় ক্যান্ডেলের মুভ কিন্তু **কোনো imbalance নেই** — এটা weak/FOMO মুভ, আসল smart-money মুভ না।
- নিয়ম: এখানে কোনো order block মার্ক করবেন না। বরং এই fake মুভের টপ/বটমে reversal সিগন্যালের জন্য অপেক্ষা করে fade ট্রেড করুন।

---

### ক্যাটাগরি ১১ — ৭টা Liquidity Trading Patterns

**৩৭. Compression-to-Expansion Breakout (আসল)**
- ট্রিগার: প্রাইস **দুর্বল মুভে (compression: মিশ্র red/green)** লেভেলে পৌঁছে, তারপর রিভার্স করে **strong মুভ + imbalance দিয়ে expand** করে লেভেল ব্রেক করে।
- এন্ট্রি: ব্রেকেন লেভেলের retest-এ reversal সিগন্যাল।
- বায়াস: breakout দিকে ট্রেডযোগ্য।

**৩৮. Expansion-and-Compression Trap (Fade)**
- ট্রিগার: প্রাইস লেভেলের দিকে **imbalance সহ strong expansion মুভ** করে (বর্তমান পক্ষের strength দেখায়), তারপর ব্রেক করার আগে **compress** করে (দুর্বল মুভ, মিশ্র ক্যান্ডেল)।
- নিয়ম: এই breakout ট্রেড করবেন না — fail করার সম্ভাবনা বেশি।
- এন্ট্রি: breakout-এর পর bearish reversal ক্যান্ডেল (pin bar/engulfing) এলে শর্ট।
- বায়াস: breakout fade করুন।

**৩৯. Lower-Wick Liquidity Trap Pattern**
- ট্রিগার: লেভেলের কাছে/ব্রেক করার সময় বেশিরভাগ ক্যান্ডেলের **lower wick upper wick-এর তুলনায় লম্বা হতে থাকে** → নিচে অনেক liquidity জমে আছে, এখনো hunt হয়নি।
- নিয়ম: breakout ট্রেড করবেন না; breakout-এর পর reversal ক্যান্ডেল এলে শর্ট (প্রাইস আগে নিচে গিয়ে liquidity hunt করবে)।
- বায়াস: Fade।

**৪০. Shadow High Liquidity Pattern**
- ট্রিগার: imbalance সহ strong breakout, তারপর **retest-এ** একাধিক লম্বা **upper wick** ফর্ম হয় কিন্তু **কোনো ক্যান্ডেল আগেরটার high ব্রেক করে না** — মানে এই wick-গুলোর ওপরে unhunted liquidity আছে (রিটেইল ভুলভাবে pin bar-এ শর্ট করছে, breakout fail ভেবে)।
- এন্ট্রি: প্রাইস support/retest জোনে পৌঁছে reversal সিগন্যাল দিলে → বাই।
- বায়াস: বুলিশ কন্টিনিউয়েশন।

**৪১. Weak Breakout Liquidity Trap Pattern**
- ট্রিগার: লেভেল ব্রেক আউট হয়, কিন্তু breakout-এর সময় **বেশিরভাগ ক্যান্ডেলে লম্বা upper wick** থাকে → seller পুরোপুরি হারেনি, breakout fail করার সম্ভাবনা; ক্যান্ডেল low-গুলোর নিচে liquidity জমছে।
- এন্ট্রি: breakout-এর পর reversal ক্যান্ডেল (bearish pin bar/engulfing) এলে শর্ট।
- বায়াস: Fade।

**৪২. Structural Breakout Liquidity Trap Pattern**
- ট্রিগার: strong key level strong মুভে approach করে, breakout হয় কিন্তু পথে **একাধিক retracement** সহ — মানে buyer দুর্বল, retracement-এ তৈরি swing low-গুলোর নিচে অনেক liquidity।
- এন্ট্রি: লেভেলের নিচে reversal সিগন্যালে শর্ট।
- বায়াস: Fade।

**৪৩. Supply Rejection Breakout**
- চার্ট কন্ডিশন: strong key level (strong bearish মুভ দিয়ে তৈরি), ঠিক ওপরে একটা **supply zone**।
- ট্রিগার: প্রাইস **দুর্বল মুভে** key level ব্রেক করে supply zone-এ ঢোকে।
- নিয়ম: এই breakout বিশ্বাস করবেন না — supply zone-এ active seller এটাকে রিজেক্ট করবে।
- এন্ট্রি: supply zone টাচ করার পর reversal সিগন্যালে শর্ট।
- বায়াস: Fade।

---

### ক্যাটাগরি ১২ — Liquidity Sweep + Fair Value Gap Strategy

**৪৪. Liquidity Sweep + FVG Confirmation Entry**
- চার্ট কন্ডিশন: একটা swing high (বা low) মার্ক করা আছে।
- ট্রিগার: প্রাইস swing high-এর ওপরে sweep করে (liquidity hunt), তারপর **strong মুভে বড় বড় FVG তৈরি করে** রিভার্স করে → smart money sell-side এ active (mirror: swing low-এর নিচে sweep + strong মুভে বড় FVG উপরে = buy-side active)।
- এন্ট্রি: retracement + reversal সিগন্যালে, smart-money দিকে।
- **Invalidation:** sweep-এর পরের রিভার্সাল মুভে যদি **কোনো FVG/imbalance না থাকে**, এটা দুর্বল মুভ — ট্রেড করবেন না।
- বায়াস: উভয়।

---

### ক্যাটাগরি ১৩ — ICT Reclaimed Block Strategy

**৪৫. Reclaimed Block (বুলিশ ও বেয়ারিশ)**
- **বুলিশ কন্ডিশন:** বেয়ারিশ ট্রেন্ড (LH/LL); প্রাইস strong ভাবে শেষ lower high ব্রেক করে ওপরে close করে = CHoCH/MSH।
- মার্কিং নিয়ম: সেই ব্রেক-হওয়া lower high-র **ঠিক আগের lower low বানানো ক্যান্ডেলকে** Reclaimed Block জোন হিসেবে মার্ক করুন (color গুরুত্বপূর্ণ না)।
- Validity ফিল্টার: সেই low থেকে high পর্যন্ত Fibonacci আঁকুন; reclaimed block অবশ্যই **50%-এর নিচে (discount)** থাকতে হবে ভ্যালিড হওয়ার জন্য।
- এন্ট্রি: জোনে retracement + reversal সিগন্যালে → বাই।
- **Mirror (বেয়ারিশ):** বুলিশ ট্রেন্ডে শেষ higher low ব্রেক = CHoCH; সেই higher low-র আগের higher high ক্যান্ডেল মার্ক; 50%-এর ওপরে (premium) থাকলে ভ্যালিড; retracement + bearish সিগন্যালে → সেল।
- বায়াস: উভয়।

---

### ক্যাটাগরি ১৪ — "3 Powerful Strategies" *(ফাইলে দুবার এসেছে, একই — merge করা)*

**৪৬. Break and Retest Strategy (ক্যান্ডেল-বডি তুলনা ফিল্টার)**
- চার্ট কন্ডিশন: resistance ব্রেক আউট হয়ে (support-এ ফ্লিপ), প্রাইস retest করে pin bar বানায়।
- নিয়ম (গুরুত্বপূর্ণ ফিল্টার): retest-এর ক্যান্ডেল body-গুলোকে original breakout মুভের ক্যান্ডেল body-গুলোর সাথে তুলনা করুন —
  - retest body **বড়** হলে → seller buyer-এর চেয়ে শক্তিশালী → বাই করবেন না (~৯০% fail)।
  - retest body **ছোট** হলে → buyer শক্তিশালী → valid বাই সেটআপ।
- এন্ট্রি: শুধু body-সাইজ নিয়ম অনুকূলে থাকলে retest-এর pin bar close-এ।
- বায়াস: উভয় (breakdown-এও mirror প্রযোজ্য)।

**৪৭. Change of Character Failure vs. Valid CHoCH (Order Block শক্তি নিয়ম)**
- CHoCH validity: higher low **দুর্বল মুভে (imbalance ছাড়া)** ভাঙলে সম্ভবত fake CHoCH — ট্রেড করবেন না। **strong মুভ + imbalance** দিয়ে ভাঙলে আসল CHoCH — FVG/OB-এর retest ট্রেড করুন।
- Order Block আপেক্ষিক-শক্তি নিয়ম: OB ভ্যালিড হয় শুধু (a) aligned imbalance থাকলে, ও (b) একটা লেভেল ব্রেক করার পর ফর্ম হলে। তবুও, প্রাইস যদি OB-তে **strong মুভ + imbalance দিয়ে** ফিরে আসে, বাই করবেন না (smart money অন্য কোথাও profit বুক করেছে, seller এখন কন্ট্রোলে) — শুধু তখনই ট্রেড করুন যখন প্রাইস original impulsive মুভের চেয়ে **দুর্বল মুভে** ফিরে আসে।
- বায়াস: উভয়।

---

### ক্যাটাগরি ১৫ — Liquidity Concept ("Liquidity Is Everything")

**৪৮. Liquidity Zone vs. Pool vs. Swing Points vs. Equal Highs/Lows (সংজ্ঞা + এড়ানোর নিয়ম)**
- সংজ্ঞা (liquidity-marking লজিক কোড করার জন্য):
  - **Liquidity zone:** যেকোনো জায়গা যেখানে stop loss জমা থাকে (যেমন bullish reaction ক্যান্ডেলের পর support-এর ঠিক নিচে)।
  - **Liquidity pool:** একটা **range** তৈরি হলে (অনেক অংশগ্রহণকারী) — range-এর ওপরে/নিচে জোন।
  - **Swing highs/lows:** প্রতিটা swing high-এর ওপরে, প্রতিটা swing low-এর নিচে liquidity।
  - **Equal highs/lows:** ≥২ বার একই (কাছাকাছি) প্রাইসে টাচ = strong liquidity pool।
- এড়ানোর নিয়ম (actionable filter):
  1. এন্ট্রি নেওয়ার আগে সবসময় **ক্যান্ডেল ক্লোজের** জন্য অপেক্ষা করুন (breakout-এ মাঝ-ক্যান্ডেলে এন্ট্রি না)।
  2. LTF সিগন্যাল বিশ্বাস করার আগে **higher timeframe**-এ sentiment কনফার্ম করুন।
  3. penny/কম-liquidity স্টক পুরোপুরি এড়িয়ে চলুন।
- (এটা কনসেপ্ট এপিসোড, উপরের ফিল্টার ছাড়া আলাদা entry/SL/TP নেই।)

---

### ক্যাটাগরি ১৬ — ICT Rejection Block Strategy

**৪৯. Rejection Block (বুলিশ ও বেয়ারিশ)**
- **বেয়ারিশ কন্ডিশন:** প্রাইস আগের high-এর liquidity sweep করে **লম্বা upper-wick rejection ক্যান্ডেল** বানায়।
- Validity শর্ত (সবগুলো লাগবে):
  1. **পরের ক্যান্ডেলের পুরো OHLC** rejection block-এর (wick zone-এর) **সম্পূর্ণ নিচে** থাকতে হবে।
  2. rejection ক্যান্ডেলের সাথে একটা **FVG** ফর্ম হতে হবে।
  3. এর পরের strong bearish মুভে একটা structural লেভেল ব্রেক হতে হবে।
- দুর্বল ভ্যারিয়েন্ট: যদি rejection block-এর wick পরের ক্যান্ডেলের wick দিয়ে **tap** হয়ে যায় — এটা "weak rejection block" (কম win-rate, তবু ব্যবহারযোগ্য)।
- মার্কিং: জোন হলো rejection ক্যান্ডেলের **শুধু upper wick** (পুরো ক্যান্ডেল না)।
- এন্ট্রি: rejection block-এ retracement + reversal সিগন্যালে → শর্ট।
- **Mirror (বুলিশ):** আগের low-এর নিচে sweep → লম্বা lower-wick rejection ক্যান্ডেল → পরের ক্যান্ডেলের OHTC সম্পূর্ণ ওপরে + FVG + structural break → lower wick-কে জোন মার্ক → retracement + bullish সিগন্যাল → বাই।
- নোট: liquidity sweep ছাড়াও rejection block ফর্ম হতে পারে, কিন্তু বাকি ৩টা শর্ত লাগবেই।
- বায়াস: উভয়।

---

### ক্যাটাগরি ১৭ — High-Probability Supply & Demand Strategy

**৫০. High-Probability Supply/Demand জোন শর্ত + 50%-Tap নিয়ম + Sweep-Then-Tap ভ্যারিয়েন্ট**
- বেসিক মার্কিং: Demand zone = strong bullish মুভের আগে swing low বানানো ক্যান্ডেল; Supply zone = strong bearish মুভের আগে swing high বানানো ক্যান্ডেল।
- High-probability ফিল্টার (সবগুলো লাগবে): (a) জোন থেকে **strong displacement** মুভ, (b) সেই displacement-এ জোন-ক্যান্ডেলের সাথে align করা **imbalance/FVG** দৃশ্যমান, (c) মুভ একটা আগের swing high/low বা key level **ব্রেক** করে।
- 50%-tap নিয়ম (এন্ট্রি টাইমিং): প্রাইস জোনের **কমপক্ষে 50% রেঞ্জ tap করার আগে** কোনো reversal সিগন্যাল ট্রেড করবেন না। শুধু ≥50% tap হওয়ার পর reversal সিগন্যাল ভ্যালিড।
- সবচেয়ে শক্তিশালী ভ্যারিয়েন্ট (sweep-then-tap): supply zone আরও শক্তিশালী হয় যদি প্রাইস **আগে জোনের কাছে এসে tap না করে ফিরে যায়, আবার এসে জোনের ঠিক নিচে/ওপরের liquidity sweep করে**, তারপর জোন tap করে রিভার্স করে।
- এন্ট্রি: 50%-tap শর্ত (বা sweep-then-tap সিকোয়েন্স) পূরণ হওয়ার পর reversal সিগন্যালে।
- বায়াস: উভয়।

---

### ক্যাটাগরি ১৮ — Power of Higher Timeframe

**৫১. HTF Trend/Liquidity ফিল্টার LTF এন্ট্রির আগে** (নিয়ম, standalone সেটআপ না)
- নিয়ম: যেকোনো LTF সেটআপ (OB, FVG ইত্যাদি) ট্রেড করার আগে HTF চার্টের ট্রেন্ড ও সাম্প্রতিক liquidity বিহেভিয়ার চেক করুন (যেমন — supply zone/swing low-এর HTF liquidity sweep রিভার্সাল সিগন্যাল দিচ্ছে কিনা)। HTF কনটেক্সট LTF সিগন্যালের বিপরীত হলে LTF ট্রেড নেবেন না — বরং LTF সেটআপ **fail** হওয়ার জন্য অপেক্ষা করে HTF দিকে reversal/pullback ট্রেড করুন।
- এটা একটা filter layer, নিজস্ব SL/TP নেই।

---

### ক্যাটাগরি ১৯ — Hidden Liquidity Trading

**৫২. Candle-Structure Hidden Liquidity (মাল্টি-ক্যান্ডেল লম্বা-উইক ফেড)**
- কনসেপ্ট: প্রতিটা ক্যান্ডেলের নিজস্ব হিডেন liquidity থাকে — low-এর নিচে buyer stop-loss liquidity, high-এর ওপরে seller stop-loss liquidity (ক্যান্ডেলের ইন্টারনাল লোয়ার-টাইমফ্রেম স্ট্রাকচার থেকে derive করা)।
- ট্রিগার: একটা মুভের মধ্যে **একই দিকে একাধিক ক্যান্ডেলে লম্বা lower (বা upper) wick**, এবং **কোনো ক্যান্ডেল আগেরটার low (বা high) ব্রেক করে না** → সেই দিকে hidden, unhunted liquidity জমছে।
- Breakout-এ প্রয়োগ: resistance breakout-এর আগে যদি long lower-wick বুলিশ ক্যান্ডেল থাকে, breakout-এর ঠিক পরে **bearish engulfing** আশা করুন (breakout fail করবে) কারণ মার্কেট সেই hidden lower-wick liquidity hunt করতে নিচে নামবে।
- এন্ট্রি: breakout-এর পর reversal engulfing ক্যান্ডেল এলে শর্ট (বা mirror-এ লং)।
- বায়াস: উভয়। (ক্যাটাগরি ১১-এর প্যাটার্ন #৩৯-৪২-এর সাথে খুব সম্পর্কিত।)

---

### ক্যাটাগরি ২০ — Break & Retest Setup Secret (Time-Frame Integration)

**৫৩. HTF-Validated Break & Retest** *(সেটআপ #৪৬-এর সম্প্রসারণ)*
- নিয়ম: শুধু LTF-এ break-and-retest ট্রেড করবেন না। HTF ক্যান্ডেল ভেঙে দেখুন: যদি HTF ক্যান্ডেল লেভেলের ওপরে/নিচে wick দেয় কিন্তু **ভেতরে ফিরে close করে** (মানে HTF ক্যান্ডেল আসলে rejection/indecision ক্যান্ডেল), তাহলে LTF-এর "breakout" আসলে সেই HTF ক্যান্ডেলের ইন্টারনাল retracement মাত্র — একটা **fakeout**। শুধু তখনই LTF break & retest বিশ্বাস করুন যখন HTF নিজেও তার মেজর স্ট্রাকচার (BOS/CHoCH) ব্রেক করেছে।
- **টাইমফ্রেম পেয়ারিং:** 1m→15m, 3m→30m, 5m→1H, 15m→4H।
- বায়াস: উভয়।

---

### ক্যাটাগরি ২১ — Smart Money Order Block Secret

**৫৪. Liquidity-Hunted Order Block (High- বনাম Low-Probability OB)**
- নিয়ম: OB শুধু তখনই **high-probability** যখন এটা প্রাইস একটা liquidity level sweep/hunt করার (যেমন আগের low ভেঙে বা আগের high ভেঙে) **ঠিক পরে**, impulsive মুভ শুরু হওয়ার আগে তৈরি হয়েছে। আগে liquidity hunt ছাড়া তৈরি OB **low-probability**, দেখতে টেক্সটবুক OB মনে হলেও fail করার সম্ভাবনা বেশি।
- এন্ট্রি: liquidity-hunted OB-তে reversal/rejection ক্যান্ডেলে impulsive-move দিকে ট্রেড।
- বায়াস: উভয়।

---

### ক্যাটাগরি ২২ — Key Level চেনার উপায়

**৫৫. Key Level Validity শর্ত + ৩টা ট্রেডযোগ্য কন্ডিশন**
- ভ্যালিড key level-এর ৪টা আবশ্যক শর্ত (+১টা ঐচ্ছিক):
  1. **Hidden interest:** লেভেলের বাঁ পাশে আগে কোনো স্পষ্ট reaction ছাড়াই প্রাইস রিভার্স করেছে।
  2. **Imbalance confirmation:** লেভেল থেকে দূরে সরে যাওয়া মুভে FVG আছে।
  3. **Structural break:** এই মুভ একটা আগের support/resistance ব্রেক করে।
  4. **Unmitigated:** প্রাইস আর কখনো লেভেলে ফিরে টাচ করেনি।
  5. *(ঐচ্ছিক)* Volume: রিভার্সাল পয়েন্টে বাড়তি ভলিউম থাকলে আরও কনফিডেন্স।
- প্রাইস ভ্যালিড key level-এ ফিরে এলে ৩টা ট্রেডযোগ্য কন্ডিশন:
  - **৫৫ক. Choppy Momentum:** প্রাইস **দুর্বল/এলোমেলো মিশ্র red-green ক্যান্ডেলে** লেভেলে আসে → smart money সেখানে বিপরীত ভারী অর্ডার বসানোর জন্য প্রাইস টেনে আনছে → লেভেলে reversal সিগন্যাল → approach-এর বিপরীত দিকে ট্রেড।
  - **৫৫খ. Liquidity Build-Up Momentum:** প্রাইস একটা পরিষ্কার **স্ট্রাকচার (HH/HL বা মিরর)** বানিয়ে আসে → প্রতিটা higher low-এর নিচে liquidity জমে (রিটেইল "ট্রেন্ড" ভেবে কিনছে) → লেভেলে reversal → জমে থাকা liquidity-র বিপরীত দিকে ট্রেড।
  - **৫৫গ. Depletion of Momentum:** লেভেলের কাছে **ক্যান্ডেল ছোট হতে থাকে** (momentum কমছে) → লেভেলে বিপরীত পক্ষ শক্তিশালী → reversal সিগন্যাল → depleting momentum-এর বিপরীত দিকে ট্রেড।
- এন্ট্রি: এই ৩টার যেকোনো একটা কন্ডিশনে key level-এ reversal সিগন্যাল।
- বায়াস: উভয়।

---

### ক্যাটাগরি ২৩ — Order Block + Liquidity Trading Strategy

**৫৬. High-Probability Order Block শর্ত (পুনরাবৃত্তি)**
- ৩টা আবশ্যক শর্ত: (১) OB ক্যান্ডেলের সাথে align করা FVG/imbalance, (২) OB ফর্ম হওয়ার পর structure/CHoCH ব্রেক, (৩) OB এখনো **unmitigated** (আবার টাচ হয়নি)।

**৫৭. Weak Retracement on Order Block**
- ট্রিগার: প্রাইস valid (৩-শর্ত) OB-তে **দুর্বল-momentum মুভে** retrace করে — পর্যায়ক্রমে red-green-red-green ক্যান্ডেল ("লড়াই", পথে liquidity জমছে) — তারপর OB-তে bullish reversal সিগন্যাল (sweeping ক্যান্ডেল, engulfing ইত্যাদি) দেখায়।
- এন্ট্রি: reversal সিগন্যালে।
- বায়াস: উভয়।

**৫৮. Inducement Block Strategy**
- চার্ট কন্ডিশন: বুলিশ মার্কেট, valid OB চিহ্নিত।
- ট্রিগার: OB-তে পৌঁছানোর আগে প্রাইস প্রথমে OB-র ঠিক ওপরে একটা **equal low (inducement)** বানায় — একটা ছোট liquidity pool। প্রাইস এই equal low-এর নিচে sweep করে (liquidity hunt), তারপর OB-তে পৌঁছে bullish reversal (sweeping candle) দেখায়।
- এন্ট্রি: equal-low sweep-এর পর OB-তে reversal সিগন্যালে।
- বায়াস: বুলিশ শোন (mirror প্রযোজ্য)।

---

### ক্যাটাগরি ২৪ — Market Structure + Sweep Technique

**৫৯. Sweep-Qualified BOS/CHoCH** (সেটআপ #২২/#২৫-এর পরিমার্জন)
- নিয়ম ১: প্রাইস যদি আগের low-এর **নিচে wick দেয় কিন্তু close না করে** (শুধু sweep), এটা break of structure না — কিন্তু এটা একটা early warning যে ট্রেন্ড দিক দুর্বল হচ্ছে।
- নিয়ম ২: এই non-closing sweep-এর পর যদি প্রাইস বিপরীত সাম্প্রতিক high/low-এর **ওপারে close করে ব্রেক** করে, এই কম্বিনেশন (sweep + বিপরীত-দিকে close) **একটা ভ্যালিড Change of Character হিসেবে গণ্য হয়**, যদিও আসল low নিজে কখনো close দিয়ে ভাঙেনি।
- এন্ট্রি: এই sweep-qualified CHoCH-এর পর একটা high-probability FVG/OB/breaker block মার্ক করে retracement + reversal সিগন্যালে নতুন-ট্রেন্ড দিকে এন্ট্রি।
- বায়াস: উভয়।

---

### ক্যাটাগরি ২৫ — Valid & Invalid Pullbacks ("৮ প্রকার")

**৬০. Pullback Validity মূল নিয়ম + ৮টা কোডযোগ্য প্যাটার্ন**
- মূল নিয়ম (বুলিশ মার্কেট): একটা pullback **valid** হয় শুধু তখনই যখন pullback-এর সর্বোচ্চ high বানানো ক্যান্ডেলের **low** পরবর্তী কোনো ক্যান্ডেল দিয়ে ভাঙা হয় (wick বা close দিয়ে)। (বেয়ারিশ mirror: pullback-এর সর্বনিম্ন low বানানো ক্যান্ডেলের **high** ভাঙতে হবে।)
- ৮টা প্যাটার্ন ভ্যারিয়েন্ট (সবগুলো মূল নিয়ম দিয়ে যাচাই করা):
  1. সাধারণ: শেষ impulsive ক্যান্ডেলের high-ই pullback high → পরের ক্যান্ডেল তার low ভাঙলে = **valid**।
  2. Equal highs: ≥২টা ক্যান্ডেলের একই high → এদের মধ্যে **শেষটার low** ভাঙতে হবে = **valid**।
  3. পরে ফর্ম হওয়া বিপরীত-রঙের ক্যান্ডেলের high শেষ impulsive ক্যান্ডেলের চেয়েও বেশি → সেই নতুন ক্যান্ডেলের low-ই ভাঙতে হবে = **valid**।
  4. High-বানানো ক্যান্ডেলের low শুধু **wick দিয়ে** ভাঙলে (close না হলেও) = তবুও **valid**।
  5. Impulsive ক্যান্ডেলের পর inside bar ফর্ম হয়, তৃতীয় ক্যান্ডেল **inside bar-এর** low ভাঙে কিন্তু আসল high-বানানো ক্যান্ডেলের low ভাঙে না = **invalid** (পুরো মুভ একটাই impulsive লেগ)।
  6. High-বানানো ক্যান্ডেলের পর "দ্বিতীয় ক্যান্ডেল" হিসেবে একটা pin bar ফর্ম হয়, তারপর প্রাইস high-বানানো ক্যান্ডেলের low না ভেঙেই আবার ওপরে যায় = **invalid**।
  7. একাধিক ক্যান্ডেল pull back করে কিন্তু শুধু **শেষ** pullback ক্যান্ডেলের low ভাঙে (আসল high-বানানো ক্যান্ডেলের না) = **invalid**।
  8. (#৭-এর বেয়ারিশ mirror) একাধিক green pullback ক্যান্ডেল, শুধু শেষ green ক্যান্ডেলের high ভাঙে, আসল low-বানানো ক্যান্ডেলের না = **invalid**।
- প্রয়োগ: একটা "invalid pullback" ভেঙে গেলেও সেটাকে valid CHoCH হিসেবে ধরা উচিত না — ভিডিওতে একটা নির্দিষ্ট stop-out উদাহরণের মূল কারণ হিসেবে এটা দেখানো হয়েছে।
- বায়াস: উভয় (এটা structure-mapping নিয়ম, একা কোনো P&L সেটআপ না)।

---

### ক্যাটাগরি ২৬ — Change in State of Delivery (CISD) মডেল

**৬১. CISD প্যাটার্ন + ৩টা রিলায়েবিলিটি ফিল্টার**
- বেসিক CISD মার্কিং (আপট্রেন্ডে বুলিশ-থেকে-বেয়ারিশ রিভার্সাল কনটেক্সট): সাম্প্রতিক BOS বানানো impulsive বুলিশ লেগ চিহ্নিত করুন; সেই লেগের **প্রথম bullish ক্যান্ডেলের open price**-কে CISD লেভেল হিসেবে মার্ক করুন।
- ট্রিগার: প্রাইস পরে একটা ছোট retracement দিয়ে সেই open-price CISD লেভেলের **নিচে close করে** → মোমেন্টাম buy-side থেকে sell-side-এ শিফট হয়েছে কনফার্ম হয় (প্রায়ই পূর্ণ CHoCH-এর চেয়ে আগে সিগন্যাল দেয়)।
- **Mirror (বেয়ারিশ-থেকে-বুলিশ):** down-লেগের প্রথম bearish ক্যান্ডেলের open মার্ক করুন; তার **ওপরে close** = bullish CISD।
- CISD-পরবর্তী এন্ট্রি: আগের support (বুল কেসে) এখন resistance হিসেবে কাজ করবে; resistance/FVG/OB-তে retracement + bearish reversal সিগন্যালে শর্ট। (বুলিশ CISD-এ mirror।)
- ৩টা রিলায়েবিলিটি ফিল্টার (যেকোনো একটা কনফিডেন্স বাড়ায়):
  - **৬১ক. CISD + HTF Rejection:** LTF-এ CISD ফর্ম হওয়ার একই সময়ে প্রাইস একটা HTF reaction zone (FVG/OB/supply-demand/S-R) থেকে রিজেক্ট হচ্ছে।
  - **৬১খ. CISD + Power Reversal:** CISD-তে যাওয়া রিভার্সাল মুভে নিজেই imbalance আছে (choppy না, strong momentum reversal)।
  - **৬১গ. CISD + Liquidity Sweep:** কাছাকাছি equal-highs/equal-lows liquidity pool sweep করার ঠিক পরে CISD ফর্ম হয়।
- স্টপ লস/টার্গেট (বেয়ারিশ উদাহরণ থেকে): SL breaker block-এর ওপরে; TP নিকটতম swing low।
- বায়াস: উভয়।

---

### ক্যাটাগরি ২৭ — Smart Money Manipulation Techniques ("৪টা জায়গা")

**৬২. Manipulated Breakout Entry (sweep fade করা)**
- ট্রিগার: আপট্রেন্ডে প্রাইস সাম্প্রতিক higher high-এর ওপরে sweep করে (ম্যানিপুলেটেড breakout) — একটা sweeping ক্যান্ডেল ফর্ম হয়।
- এন্ট্রি: breakout-এ sweeping ক্যান্ডেলে শর্ট।
- টার্গেট: নিকটতম reaction zone; ১ম টার্গেটের পর হোল্ড/ট্রেইল করা যায়।
- বায়াস: বেয়ারিশ (আপট্রেন্ড কনটেক্সটে counter-trend স্ক্যাল্প)।

**৬৩. Fake Change of Character**
- নিয়ম: আপট্রেন্ডে মেজর low ব্রেক হলেই সাথে সাথে CHoCH ট্রেড করবেন না — একটা order block-এ retracement + rejection ক্যান্ডেলের জন্য অপেক্ষা করুন; নাহলে এটা শুধু একটা HTF-লেভেল inducement হতে পারে।
- এন্ট্রি: "fake CHoCH"-এর পর OB rejection-এ buy-side (original ট্রেন্ড কন্টিনিউয়েশন)।
- বায়াস: continuation ট্রেড।

**৬৪. Internal Liquidity Gap Entry**
- ট্রিগার: impulsive আপট্রেন্ডের মধ্যে একটা internal retracement low ফর্ম হয় (buyer-এর stop loss নিচে); প্রাইস এই internal low-এর নিচে ডিপ করে (ফাঁদ), তারপর একটা reaction zone-এ (OB/support/FVG) পৌঁছায়।
- এন্ট্রি: সেই reaction zone-এ reversal ক্যান্ডেল সিগন্যালে → বাই।
- বায়াস: বুলিশ (mirror প্রযোজ্য)।

**৬৫. Range Manipulation**
- ট্রিগার: আপট্রেন্ড একটা range-এ consolidate করে; প্রাইস (higher ট্রেন্ডের বিপরীতে) range-এর **breakdown** ম্যানিপুলেট করে range-buyer-দের ফাঁদে ফেলে নতুন seller টেনে আনে; তারপর নিচের একটা order block-এ পৌঁছে রিভার্স করে।
- এন্ট্রি: ভাঙা range-এর নিচে OB-তে reversal সিগন্যালে → বাই। (বিকল্প: miss হলে range-এর ওপরে liquidity sweep-এর পর একটা strong reaction zone-এ retrace করে bullish সিগন্যালেও বাই।)
- লাইভ উদাহরণ: SL OB-এর নিচে, target range high-এর সামান্য ওপরে (external liquidity target)।
- বায়াস: বুলিশ (ট্রেন্ড কন্টিনিউয়েশন; mirror প্রযোজ্য)।

---

### ক্যাটাগরি ২৮ — ৪টা Golden Strategies

**৬৬. Smart BOS Model**
- ট্রিগার: আপট্রেন্ড; retracement-এর পর প্রাইস আক্রমণাত্মকভাবে FVG তৈরি করে structure ব্রেক করে (imbalance সহ BOS = smart money active)।
- এন্ট্রি: BOS-এর পর একটা strong zone-এ (OB/support/demand) reversal সিগন্যালে।
- Invalidation: BOS **দুর্বল momentum-এ** (imbalance ছাড়া) হলে বাই করবেন না — বরং consolidation আশা করুন।
- বায়াস: বুলিশ শোন (mirror প্রযোজ্য)।

**৬৭. Smart Reversal Model**
- ট্রিগার: বুলিশ স্ট্রাকচারের মধ্যে প্রাইস একটা supply zone-এ পৌঁছে রিজেক্ট হয়, এবং সেই rejection **market structure ব্রেক করে**।
- এন্ট্রি: reaction zone-এ (FVG/supply/resistance/OB) retracement + reversal সিগন্যালে → সেল।
- স্টপ লস: entry zone-এর ওপরে। টার্গেট: extreme/নিকটতম demand zone।
- বায়াস: বেয়ারিশ শোন (mirror প্রযোজ্য)।

**৬৮. Smart Pullback Trap Model**
- ট্রিগার: ডাউনট্রেন্ড একটা consolidation range-এ pull back করে; seller range-এর নিচে ব্রেক করে, কিন্তু প্রাইস **recent low**-তে পৌঁছানোমাত্র buyer আক্রমণাত্মক হয়।
- এন্ট্রি: recent low-তে reversal সিগন্যালে (range breakout-এর জন্য অপেক্ষা করার চেয়ে এটা বেশি win-rate দেয়, বক্তার মতে)।
- বায়াস: বুলিশ রিভার্সাল (mirror প্রযোজ্য — আপট্রেন্ড pullback range-এ)।

**৬৯. Smart Supply-Demand Trap Model**
- ট্রিগার: প্রাইস একটা demand zone টাচ করে একবার রিজেক্ট হয়, কিন্তু seller আবার নিচে পুশ করে তার **recent low ব্রেক করে** (নিচের stop hunt করে); তারপর buyer আবার পুশ ব্যাক করে **market structure ব্রেক করে**।
- এন্ট্রি: demand zone/OB/support-এ retracement + reversal সিগন্যালে → বাই।
- স্টপ লস: জোনের নিচে। টার্গেট: নিকটতম swing high।
- বায়াস: বুলিশ শোন (mirror প্রযোজ্য)।

---

### ক্যাটাগরি ২৯ — Manipulative Candlestick Strategy

**৭০. Manipulative Candle (২-ক্যান্ডেল Liquidity Sweep Reversal)**
- প্যাটার্ন (বুলিশ): ক্যান্ডেল ১ = যেকোনো ক্যান্ডেল। ক্যান্ডেল ২ ওপেন হয়ে প্রথমে ক্যান্ডেল ১-এর **LOW ভাঙে** (নিচের liquidity sweep), তারপর রিভার্স করে ক্যান্ডেল ১-এর **HIGH-এর ওপরে close করে**, লম্বা lower wick সহ একটা strong bullish ক্যান্ডেল বানায় — এটাই "ম্যানিপুলেশন" (নিচের buyer আর ওপরের seller দুজনেই ফাঁদে পড়ে)।
- **Mirror (বেয়ারিশ):** ক্যান্ডেল ২ প্রথমে ক্যান্ডেল ১-এর HIGH ভাঙে, তারপর রিভার্স করে ক্যান্ডেল ১-এর LOW-এর নিচে close করে, লম্বা upper-wick বেয়ারিশ ক্যান্ডেল বানায়।
- এন্ট্রি পদ্ধতি (HTF→LTF ম্যাপিং): এই ২-ক্যান্ডেল প্যাটার্ন HTF-এ চিহ্নিত করুন; পেয়ারিং টেবিল অনুযায়ী LTF-এ নামুন (Day→1H, 4H→30m, 1H→15m, 30m→5m, 15m→1m)। LTF-এ এই জোনগুলোর কাছে reaction zone মার্ক করুন: candle-1 low, candle-1 close, candle-2 low, candle-2 close (বুলিশ কেস — বেয়ারিশে high/close mirror)। এই জোনগুলোর যেকোনো একটায় reversal ক্যান্ডেলের জন্য অপেক্ষা করুন।
- স্টপ লস: reaction zone-এর সামান্য বাইরে।
- টার্গেট: নিকটতম swing low/high, অথবা স্টপ-লসের ২ গুণ দূরত্ব।
- বায়াস: উভয়।

---

### ক্যাটাগরি ৩০ — Dual Trap Trading Setup *(ফাইলে দুবার এসেছে, একই — merge করা)*

**৭১. Market Structure Dual Trap**
- ট্রিগার: আপট্রেন্ড একটা swing high ব্রেক করে (breakout buyer-দের ফাঁদে ফেলে, নিচে রিভার্স করে), **তারপর** আগের swing low-ও ভাঙে (নতুন CHoCH seller-দেরও ফাঁদে ফেলে), **তারপর** আবার রিভার্স করে **আসল আপট্রেন্ডে** ফিরে যায় (তাদেরও ফাঁদে ফেলে) — আসল মুভের আগে "দুই-দিকের" ফাঁদ।
- এন্ট্রি নিয়ম: LTF-এ CHoCH-এর পরে সাথে সাথে reversal ট্রেড নেবেন না। কয়েক ক্যান্ডেলের মধ্যে প্রাইস আবার breakout/CHoCH লেভেলের ওপরে ফিরে আসে কিনা চেক করুন — যদি আসে, HTF চেক করুন (LTF/HTF পেয়ারিং: 5m→30m)। যদি HTF-এ একটা red ক্যান্ডেলের low sweep করার পরে লম্বা lower-wick rejection ক্যান্ডেল দেখা যায়, LTF-এ ফিরে এসে CHoCH লেভেলের ওপরে ক্রস করার পর লং এন্ট্রি নিন।
- স্টপ লস: swing low-এর নিচে। টার্গেট: নিকটতম swing high বা SL-এর ২ গুণ।
- **Mirror:** symmetric বেয়ারিশ ভার্সন (green ক্যান্ডেলের high sweep করার পর লম্বা upper-wick HTF rejection ক্যান্ডেল → LTF-এ CHoCH লেভেলের নিচে শর্ট এন্ট্রি)।
- বায়াস: উভয়।

**৭২. Dual Trap Candlestick — Bullish/Bearish Engulfing (২-দিকের liquidity grab)**
- প্যাটার্ন: একটা ছোট bearish ক্যান্ডেল, তারপর একটা strong bullish ক্যান্ডেল যেটা **প্রথম ক্যান্ডেলের low sweep করে** (seller ফাঁদে) **এবং** প্রথম ক্যান্ডেলের high **ভেঙে/engulf করে** (দেরিতে শর্ট করা ট্রেডাররাও ফাঁদে) — সম্পূর্ণ engulfing।
- এন্ট্রি পদ্ধতি: HTF-এ (যেমন 30m) engulfing প্যাটার্ন চিহ্নিত করুন; LTF-এ নামুন; engulfing ক্যান্ডেলের ঠিক পরেই এন্ট্রি না নিয়ে LTF-এ একটা FVG/OB/support (বুলিশ) বা FVG/OB/resistance (বেয়ারিশ)-এ পৌঁছে reversal ক্যান্ডেলের জন্য অপেক্ষা করুন।
- বায়াস: উভয় (mirror bearish engulfing ভার্সনও স্পষ্টভাবে দেওয়া আছে)।

**৭৩. Dual Trap Candlestick — Long Wick Rejection Candle**
- প্যাটার্ন: একটা ক্যান্ডেল (যেমন red) ফর্ম হয়; পরের ক্যান্ডেল ওপেন হয়ে red ক্যান্ডেলের low ভাঙে (liquidity sweep), তারপর ভারী বাইং ফিরে এসে সেটাকে আগের ক্যান্ডেলের range-এর ভেতরে একটা **লম্বা lower-wick rejection ক্যান্ডেল** হিসেবে close করায়।
- ইঙ্গিত: নিচের liquidity এখন sweep হয়ে গেছে বলে প্রাইস সম্ভবত পরের বার সেই একই red ক্যান্ডেলের **high** sweep করতে যাবে।
- এন্ট্রি: LTF-এ সেই বিপরীত-দিকের liquidity টার্গেট করে buy-side ট্রেড প্ল্যান করুন (বিস্তারিত পদ্ধতি একটা আলাদা "Power of Candle Closer" এপিসোডে বলা, এই ট্রান্সক্রিপ্টে নেই)।
- বায়াস: উভয়।

---

### ক্যাটাগরি ৩১ — The Ultimate Market Structure Trading Strategy

**৭৪. Dow Theory ট্রেন্ড/Impulse/Retracement ট্রেডিং নিয়ম**
- নিয়ম: Dow Theory দিয়ে ট্রেন্ড (up/down/sideways) চিহ্নিত করুন (পরপর HH/HL = up; পরপর LH/LL = down; ফ্ল্যাট = sideways — স্পষ্ট ট্রেন্ড না আসা পর্যন্ত sideways ট্রেড এড়িয়ে চলুন)। শুধু **retracement ফেজে** এন্ট্রি নিন, impulse-এর মাঝে না (impulsive মুভ চেজ করা রিস্কি)। আপট্রেন্ডে former-resistance-থেকে-support retracement-এ বাই; ডাউনট্রেন্ডে former-support-থেকে-resistance retracement-এ সেল।
- বায়াস: উভয় (ট্রেন্ড ফিল্টার/নিয়ম)।

**৭৫. Double Top Pattern**
- ট্রিগার: আপট্রেন্ডে প্রাইস resistance-এ পৌঁছায়, seller নিচে পুশ করে, প্রাইস আবার ওপরে যায় কিন্তু **আগের high ব্রেক করতে ব্যর্থ হয়** (২য় top) — buyer দুর্বল হচ্ছে এই ইঙ্গিত।
- এন্ট্রি: দুই top-এর মাঝের **low ব্রেক** হওয়ার ওপরে (রিভার্সাল কনফার্ম)।
- নোট: আগে থেকে গুরুত্বপূর্ণ resistance লেভেলে double top হলে win-rate আরও বেশি।
- বায়াস: বেয়ারিশ।

**৭৬. Double Bottom Pattern**
- ট্রিগার: ডাউনট্রেন্ডে প্রাইস support-এ পৌঁছায়, buyer ওপরে পুশ করে, প্রাইস আবার নিচে যায় কিন্তু **আগের low ব্রেক করতে ব্যর্থ হয়** (২য় bottom) — seller দুর্বল হচ্ছে এই ইঙ্গিত।
- এন্ট্রি: দুই bottom-এর মাঝের **high ব্রেক** হওয়ার ওপরে।
- বায়াস: বুলিশ।

**৭৭. Wyckoff-স্টাইল ৪-ফেজ সাইকেল ট্রেড** (ট্রান্সক্রিপ্টে ভুল করে "Whack-Off/Wedge Method" বলা হয়েছে — এটা স্পষ্টতই "Wyckoff Method"-এর ভুল ট্রান্সক্রিপশন)
- ফেজসমূহ: (১) **Accumulation** — ডাউনট্রেন্ডের পর range-bound, range support-এর নিচে false breakdown seller/panic-seller-দের সস্তায় ফাঁদে ফেলে smart money-র বাই করার জন্য। (২) **Markup** — HH/HL কনফার্ম করে breakout, buyer কন্ট্রোলে। (৩) **Distribution** — আপট্রেন্ডের পর range-bound, range resistance-এর ওপরে false breakout নতুন buyer-দের ফাঁদে ফেলে smart money-কে তাদের কাছে সেল করার সুযোগ দেয়। (৪) **Markdown** — LH/LL কনফার্ম করে breakdown, seller কন্ট্রোলে।
- এন্ট্রি (Accumulation→Markup): range-breakdown ম্যানিপুলেশনের পর range-এর ভেতরে ফিরে ওপরে বিস্ফোরিত হলে buy-side এন্ট্রি, markup ফেজ শুরুর কনফার্মেশনে।
- এন্ট্রি (Distribution→Markdown): range-breakout ম্যানিপুলেশনের পর range-এর ভেতরে ফিরে range support ব্রেক করলে sell-side এন্ট্রি।
- বায়াস: উভয়।

---

### ক্যাটাগরি ৩২ — ৪টা Market Manipulation Decoded (ফাঁদে-পড়া-ট্রেডার সাইকোলজি)

**৭৮. Long-Range Candle Break-Even-Exit Reversal**
- ট্রিগার: একটা long-range ক্যান্ডেল (যেমন বড় red ক্যান্ডেল) সেই দিকে ব্যাপক রিটেইল এন্ট্রি (sell) ট্রিগার করে। প্রাইস তারপর রিভার্স করে; যখন সেই long-range ক্যান্ডেলের **original entry level**-এর কাছে ফিরে আসে, ফাঁদে-পড়া ট্রেডাররা breakeven-এ exit করার জন্য ছুটে আসে, একটা তীব্র প্রতিক্রিয়া তৈরি হয়।
- এন্ট্রি: এই breakeven-exit জোনের কাছে প্রাইস আসার সময় original long-range ক্যান্ডেলের **বিপরীত দিকে** ট্রেড করুন।
- বায়াস: উভয় (ফাঁদে-পড়া পক্ষের বিপরীতে)।

**৭৯. Large Wick / Pin Bar Trapped-Breakout Reversal**
- ট্রিগার: একটা ক্যান্ডেল প্রথমে মনে হয় strong trend-continuation ক্যান্ডেল হিসেবে close করবে (যেমন বড় green breakout ক্যান্ডেল) কিন্তু close-এ এসে একটা **বড় বিপরীত-দিকের wick সহ pin bar** হয়ে যায় — breakout ট্রেডারদের ফাঁদে ফেলে।
- এন্ট্রি: wick যেদিকে ইঙ্গিত দেয় সেদিকে fade করুন (যেমন ব্যর্থ বুলিশ breakout-এর পর বড় upper wick-এর কাছে শর্ট)।
- বায়াস: উভয়।

**৮০. Fakeout Reversal**
- ট্রিগার: প্রাইস একটা support/resistance লেভেল ব্রেক করে (fakeout), তারপর **পরের ১-২ ক্যান্ডেলের মধ্যে সেই লেভেলে ফিরে আসে**। ফাঁদে-পড়া breakout ট্রেডাররা তাদের entry level-এর কাছে exit শুরু করে, রিভার্সাল আরও জোরালো হয়।
- এন্ট্রি: breakeven-exit জোনের কাছে ফাঁদে-পড়া পক্ষের বিপরীতে ট্রেড করুন।
- বায়াস: উভয়।

**৮১. Direct Breakout (কোনো Retest ছাড়া) → Retest Entry**
- ট্রিগার: প্রাইস একটা লেভেল **সরাসরি একটা strong ক্যান্ডেল দিয়ে, কোনো retest ছাড়াই** ব্রেক করে — দুই পক্ষকেই ফাঁদে ফেলে (আগেভাগে fade করা seller, এবং FOMO-miss করে retrace-এর অপেক্ষায় থাকা buyer)।
- এন্ট্রি: প্রাইস শেষমেশ **ব্রেকেন লেভেলে ফিরে আসার** জন্য অপেক্ষা করুন; সেখানে rejection সিগন্যালে এন্ট্রি (original breakout-এর দিকেই)।
- স্টপ লস: লেভেলের ওপরে/নিচে। টার্গেট: নিকটতম swing high/low।
- বায়াস: breakout-দিকে কন্টিনিউয়েশন।

---

### ক্যাটাগরি ৩৩ — Trend Line Trading Masterclass

**৮২. Trend Line + Key-Level Confluence Continuation** (শর্ট-টার্ম-ট্রেন্ডলাইন কনফার্মেশন সহ)
- চার্ট কন্ডিশন: আপট্রেন্ড; ≥২টা swing low জুড়ে trend line আঁকা; একটা flipped key level (আগের resistance এখন support) যেটা trend line-এর সাথে **ক্রস/align** করে = high-confluence জোন।
- ট্রিগার: প্রাইস কনফ্লুয়েন্স জোনে পৌঁছে trend line-এ একটা bullish ক্যান্ডেল বানায় — **এটাই যথেষ্ট না**। retracement-এর ওপর একটা **শর্ট-টার্ম (খাড়া) trend line** আঁকুন; এই শর্ট-টার্ম trend line ব্রেক হওয়ার জন্য অপেক্ষা করুন — এটাই ফাইনাল কনফার্মেশন।
- এন্ট্রি: কনফ্লুয়েন্স-জোন rejection-এর পর শর্ট-টার্ম trend-line break-এ।
- **Mirror:** ডাউনট্রেন্ড trend-line + flipped-resistance কনফ্লুয়েন্সে symmetric বেয়ারিশ ভার্সন।
- বায়াস: ট্রেন্ড-অনুযায়ী কন্টিনিউয়েশন, উভয় দিকে।

**৮৩. Trend Line Fakeout Strategy** (HTF-validated)
- নিয়ম: শুধু trend-line break/breakdown একা ট্রেড করবেন না। এন্ট্রি TF-এ trend line ব্রেক হলে HTF-এ যান (স্ট্যান্ডার্ড পেয়ারিং: 1m→15m, 3m→30m, 5m→1H, 15m→4H) এবং চেক করুন HTF-এ আসল structural CHoCH দেখাচ্ছে নাকি শুধু কনফ্লুয়েন্স জোনে **liquidity-sweep rejection candle**।
  - HTF-এ শুধু sweep/rejection দেখালে (trend line + key level কনফ্লুয়েন্স ডিফেন্ড হয়েছে) → LTF trend-line break একটা **fakeout** → প্রাইস LTF trend line-এর ওপরে original দিকে ফিরে ক্রস করলে HTF-ট্রেন্ড দিকে ট্রেড করুন।
  - HTF-এ আসল CHoCH দেখালে (মেজর swing ব্রেক + close) → LTF trend-line break আসল → নতুন দিকে ট্রেড করুন।
- অতিরিক্ত কনফ্লুয়েন্স (বেয়ারিশ উদাহরণে): LTF-এ Head & Shoulders নেকলাইন ব্রেক + HTF liquidity sweep একসাথে।
- বায়াস: উভয়।

---

### ক্যাটাগরি ৩৪ — Perfect Entry-র ৪টা শক্তিশালী ফ্যাক্টর

**৮৪. Four-Factor Entry চেকলিস্ট** (ফ্রেমওয়ার্ক + SL/TP বসানোর নিয়ম)
- **ফ্যাক্টর ১ — Market Structure:** এন্ট্রি TF এবং পরের-উঁচু TF দুটোতেই আপট্রেন্ড/ডাউনট্রেন্ড/সাইডওয়েজ কনফার্ম করুন (পেয়ারিং: 1m→15m, 5m→30m, 15m→1H, 30m→4H, 1H→Daily)। শুধু দুটো align করলেই ট্রেড করুন।
- **ফ্যাক্টর ২ — Reaction Zones:** Support/resistance, supply/demand (order block), FVG, trend line — কোথায় প্রাইস react করতে পারে চিহ্নিত করুন।
- **ফ্যাক্টর ৩ — Entry Signal:** reaction zone-এ এন্ট্রি নেওয়ার আগে একটা আসল reversal/rejection ক্যান্ডেল **অবশ্যই** লাগবে — শুধু structure + zone যথেষ্ট না (ব্যর্থ ট্রেডের কারণ হিসেবে স্পষ্টভাবে বলা হয়েছে)।
- **ফ্যাক্টর ৪ — Smart SL/TP Placement:**
  - **স্টপ লস নিয়ম:** reaction zone-এর পেছনে বসান (যেমন demand zone/support-এর নিচে, বা ট্রেন্ডিং স্ট্রাকচারে সংশ্লিষ্ট higher-low/lower-high-এর নিচে/ওপরে), কখনো এলোমেলো/র‍্যান্ডম প্রাইসে না।
  - **টার্গেট নিয়ম:** প্রথম টার্গেট = ট্রেড-দিকের নিকটতম reaction zone (লং-এর জন্য নিকটতম resistance/supply, শর্টের জন্য নিকটতম support/demand)। প্রথম টার্গেট হিট হলে এবং momentum থাকলে অর্ধেক এক্সিট করে বাকিটা ট্রেইল করুন।
- (এটা মেটা-ফ্রেমওয়ার্ক; আন্ডারলাইং ক্যান্ডেল লজিক আগের সেটআপগুলোই reuse করে।)

---

### ক্যাটাগরি ৩৫ — HTF Liquidity Sweep ইন্টিগ্রেশন

**৮৫. HTF Liquidity Sweep → LTF CHoCH/Pullback Reversal Entry**
- ট্রিগার: HTF-এ একটা liquidity sweep চিহ্নিত করুন — প্রাইস একটা swing high/equal-highs/support ভাঙে এবং **ক্যান্ডেল লেভেলের বিপরীত পাশে ফিরে close করে** (rejection close = sweep কনফার্ম, pending order অ্যাক্টিভেট)।
- এন্ট্রি পদ্ধতি: LTF-এ যান (পেয়ারিং: 1m→15m, 5m→30m, 15m→1H)। LTF-এ পরের CHoCH/BOS বা pullback খুঁজুন, এবং একটা reversal ক্যান্ডেলের (যেমন FVG-তে bearish engulfing, বা FVG-তে inside bar) জন্য অপেক্ষা করে HTF-sweep দিকে এন্ট্রি কনফার্ম করুন।
- স্টপ লস: সংশ্লিষ্ট FVG/zone-এর ওপরে/নিচে। টার্গেট: নিকটতম swing low/high।
- বায়াস: উভয়।

---

### ক্যাটাগরি ৩৬ — IFC Candle (Institutional Funding Candle) সরলীকৃত

**৮৬. Bullish IFC Candle সেটআপ**
- প্যাটার্ন: support লেভেলে একটা ক্যান্ডেল **support-এর নিচে ব্রেক করে** (buyer stop loss sweep করে নতুন seller টেনে আনে), তারপর strong বাইং দিয়ে রিভার্স করে, **নিজের open-এর ওপরে close করে**, একটা **লম্বা lower wick** সহ ক্যান্ডেল বানায় — এটাই Bullish IFC ক্যান্ডেল (ক্যান্ডেলের নিজের রঙ গুরুত্বপূর্ণ না, শুধু লম্বা lower wick + support ব্রেক/reclaim ম্যাটার করে)।
- এন্ট্রি: **পরের ক্যান্ডেল IFC ক্যান্ডেলের high-এর ওপরে close করার** জন্য অপেক্ষা করে লং।
- টার্গেট: পরের swing high-এর সামান্য নিচে।
- লাইভ-ট্রেড উদাহরণ: কাছাকাছি দুটো bullish IFC ক্যান্ডেল ফর্ম হয়েছিল; মাঝের/পরের ক্যান্ডেল higher sustain করায় এন্ট্রি নেওয়া হয়; SL ২৫ পয়েন্ট, টার্গেট ৫০ পয়েন্ট (ব্যাংক নিফটি উদাহরণ)।
- বায়াস: বুলিশ।

**৮৭. Bearish IFC Candle সেটআপ**
- প্যাটার্ন: resistance লেভেলে একটা ক্যান্ডেল **resistance-এর ওপরে ব্রেক করে** (seller stop loss sweep করে নতুন buyer টেনে আনে), তারপর strong সেলিং দিয়ে রিভার্স করে, নিজের open-এর নিচে close করে, **body-র অন্তত দ্বিগুণ লম্বা upper wick** সহ ক্যান্ডেল বানায়।
- এন্ট্রি: পরের ক্যান্ডেল IFC ক্যান্ডেলের low-এর নিচে close করার জন্য অপেক্ষা করে শর্ট।
- টার্গেট: নিকটতম swing low-এর কাছে/সামান্য ওপরে।
- বায়াস: বেয়ারিশ।

---

### ক্যাটাগরি ৩৭ — Quasimodo Pattern (QM)

**৮৮. Bullish Quasimodo Pattern**
- স্ট্রাকচার: ডাউনট্রেন্ডে (LH/LL) প্রাইস একটা আগের lower high ব্রেক করে (CHoCH পয়েন্ট) — সেই lower-high পয়েন্ট থেকে নতুন higher high পর্যন্ত একটা trend line আঁকুন, এবং আগের lower-low থেকে নতুন (উঁচু) low পর্যন্ত আরেকটা; পুরনো lower-low ও নতুন higher-low-এর **মাঝের গ্যাপ**টাকে **Quasimodo Zone** হিসেবে বক্স করুন (demand হিসেবে কাজ করে)।
- এন্ট্রি: প্রাইস QM জোনে retrace করে সেখানে bullish ক্যান্ডেল বানালে → বাই।
- টার্গেট: TP1 = CHoCH breakout লেভেলে, TP2 = আরও দূরে আগের swing high-এ।
- বায়াস: বুলিশ (ডাউনট্রেন্ড রিভার্সাল)।

**৮৯. Bearish Quasimodo Pattern**
- স্ট্রাকচার (mirror): আপট্রেন্ডে প্রাইস একটা আগের higher low ব্রেক করে — পুরনো higher-high ও নতুন (নিচু) high-এর মাঝের গ্যাপকে QM Zone হিসেবে বক্স করুন (supply হিসেবে কাজ করে)।
- এন্ট্রি: জোনে retrace করে bearish ক্যান্ডেল বানালে → সেল।
- টার্গেট: TP1/TP2 আগের swing low-গুলোতে।
- বায়াস: বেয়ারিশ (আপট্রেন্ড রিভার্সাল)।

---

### ক্যাটাগরি ৩৮ — Inducement টেকনিক

**৯০. Inducement via Breakout (Fade)**
- ট্রিগার: smart money একটা লেভেলের breakout ইঞ্জিনিয়ার করে; রিটেইল breakout কিনে লেভেলের ঠিক নিচে stop রাখে; smart money তারপর প্রাইসকে সেই লেভেলের নিচে রিভার্স করে সেই stop-গুলো হিট করে।
- এন্ট্রি: রিভার্সাল শুরু হলে breakout fade করুন (মূলত ক্যাটাগরি ৩/১১/১৯-এর fade লজিক-ই)।
- বায়াস: breakout-এর বিপরীত।

**৯১. Inducement via Trend Line Break** (কনফার্মেশন ফিল্টার)
- নিয়ম: শুধু একটা সাধারণ trend-line break-কে reversal হিসেবে ট্রেড করবেন না। শুধু তখনই ট্রেড করুন যখন trend-line break **মেজর swing low/high (structural break)** ব্রেকের সাথে মিলে যায়। একা trend-line break প্রায়ই শুধু inducement।
- বায়াস: filter rule।

**৯২. Inducement via Support/Resistance Breakout** ("সময় কাটানো" ফিল্টার)
- নিয়ম: লেভেলে পৌঁছানোর **সাথে সাথে** breakout হলে সেটা inducement/fail হওয়ার সম্ভাবনা বেশি। breakout তখন বেশি নির্ভরযোগ্য যখন প্রাইস আগে লেভেলে **কিছু সময় কাটায়** (consolidate করে) — এতে ব্রেক করার আগে বিপরীত-পক্ষের stop loss জমে ওঠে।
- বায়াস: filter rule।

**৯৩. Inducement via Range Break** (শুধু higher-ট্রেন্ডের দিকে ট্রেড করুন)
- নিয়ম: আপট্রেন্ডে প্রাইস একটা range-এ consolidate করে তারপর **range-এর নিচে ব্রেক** করলে (higher ট্রেন্ডের বিপরীতে) — এটা খুব সম্ভবত inducement — sell করবেন না; higher ট্রেন্ড সাধারণত আবার ওপরে যাবে। শুধু higher-timeframe ট্রেন্ডের সাথে align করা range-break ট্রেড করুন।
- বায়াস: filter rule (ট্রেন্ড-align শর্ত)।

---

### ক্যাটাগরি ৩৯ — অপারেটররা কীভাবে রিটেইলকে ফাঁদে ফেলে (Breakout-এর পর Consolidation)

**৯৪. Consolidation-After-Breakout Operator Trap**
- চার্ট কন্ডিশন: একটা range/level স্ট্রাকচার যেখানে operator বড় অর্ডার fill করতে চায় — শুরু হয় একটা resistance level তৈরি হয়ে ভারী operator-buying দিয়ে ব্রেক হওয়ার মাধ্যমে।
- ট্রিগার সিকোয়েন্স:
  1. Resistance একটা strong ক্যান্ডেল দিয়ে ব্রেকআউট হয় (operator-চালিত ভারী buy অর্ডার) → রিটেইল breakout কিনে (আগের resistance, এখন support)-এর নিচে stop রাখে।
  2. রিটেইল বাইং প্রাইস ওপরে ঠেলার সাথে সাথে operator বিপরীত ভারী sell অর্ডার বসিয়ে advance cap করে — এটা কয়েক ক্যান্ডেল ধরে চলে, প্রতিটায় **লম্বা upper wick** তৈরি হয় প্রাইস ওপরে যাওয়ার চেষ্টায় রিজেক্ট হয়ে, **range top-এর ওপরে কোনো ক্যান্ডেল close করে না** (ট্রেন্ড না করে consolidate করে)।
  3. দীর্ঘ consolidation থেকে যথেষ্ট buy-side liquidity (support-এর নিচে stop loss) জমা হলে, operator ভারী sell অর্ডার বসিয়ে **support/range floor ব্রেক করে**, রিটেইল stop loss + নতুন রিটেইল শর্ট ট্রিগার করে — একটা strong ডাউনসাইড momentum মুভ তৈরি হয়।
- এন্ট্রি: প্রাথমিক breakout-এ বা breakdown হওয়ার সাথে সাথে এন্ট্রি নেবেন না। breakdown-এর পর মার্কেট **আবার consolidate** করার জন্য অপেক্ষা করুন, তারপর বিপরীত (নিচের) দিকে একটা strong ক্যান্ডেলের close-এ এন্ট্রি (আসল মুভ কনফার্ম)।
- টার্গেট: নিকটতম support level।
- লাইভ উদাহরণ (Bank Nifty, Feb 13): এই সিকোয়েন্সের পর put option-এ এন্ট্রি; SL resistance-এর ~৭০ পয়েন্ট ওপরে; টার্গেট ১৭০ পয়েন্ট (প্রথম টার্গেট হিট হওয়ার পর ২৫০ পয়েন্টে ট্রেইল করা হয়)।
- বায়াস: এই উদাহরণে বেয়ারিশ (support-consolidation-breakdown-then-reversal-এর mirror বুলিশ ভার্সনও একই লজিকে প্রযোজ্য)।

---

### ক্যাটাগরি ৪০ — CRT + TBS স্ট্র্যাটেজি (Candle Range Theory + Turtle Soup)

**৯৫. CRT Ranging Candle — Validity নিয়ম**
- সংজ্ঞা: CRT "ranging candle" হলো এমন একটা ক্যান্ডেল যার **body তার wick-গুলোর চেয়ে বড়**, এবং যেটা আগের liquidity-তে **tap করে** — নির্দিষ্টভাবে এদের একটায়: OLP (Old Liquidity Pool — আগের অপরীক্ষিত high/low), একটা (I)FVG, অথবা একটা order block।
- Validity নিয়ম: ranging candle-কে (বা এর ঠিক পরের ক্যান্ডেলকে) OLP/FVG/OB **টাচ/tap** করতে হবে ভ্যালিড গণ্য হওয়ার জন্য (wick বা body contact — দুটোই গ্রহণযোগ্য)।
- Invalidity নিয়ম: ranging-candle ফর্মেশনের মধ্যে যদি পরের কোনো ক্যান্ডেলের **body** এমনভাবে wick-এর চেয়ে বড় হয়ে যায় যে আর OLP/FVG/OB **tap করে না** (স্ট্রাকচার সেই tap-কে disqualify করে দেয়) — তাহলে CRT invalid (weekly high/low-ভিত্তিক body-size তুলনা নিয়ম দিয়ে বর্ণিত)।
- **CRT High/Low + 50% Fib মার্কিং:** ranging candle-এর high (CRH) ও low (CRL) মার্ক করুন; CRH থেকে CRL পর্যন্ত Fibonacci আঁকুন — 50% লেভেল হয়ে যায় **TP1**; দূরের প্রান্ত (বুলিশে CRL, বেয়ারিশে CRH) হয় **TP2**।

**৯৬. CRT + TBS (Turtle Body Soup) "Model One" এন্ট্রি**
- **কনফার্মেশনের জন্য টাইমফ্রেম পেয়ারিং:** 15m CRT → 1m-এ কনফার্ম/এন্ট্রি; 4H/1H CRT → 5m-এ; Daily CRT (5m-এ কনফার্ম) → 15m-এ এন্ট্রি।
- নিচের টাইমফ্রেমে, CRT ranging candle-এর আগের high/low-এর সাপেক্ষে **TS (Turtle Soup) সাব-টাইপ**:
  - **TWS (Turtle Wick Soup) — ট্রেড করবেন না:** লেভেল শুধু **wick দিয়ে** ব্রেক/টাচ হয়, ক্যান্ডেল আবার original পাশে close করে।
  - **TBS (Turtle Body Soup) — ট্রেডযোগ্য:** লেভেল ব্রেক হয় এবং ক্যান্ডেল তার **body দিয়ে লেভেলের ওপারে close করে** (শুধু wick poke না, আসল body-close-through)। যদি একটা ক্যান্ডেল আগে wick দিয়ে ভেঙে তারপর body দিয়ে close করে, এটাও **TWS** হিসেবে গণ্য হবে (সিকোয়েন্সে যেকোনো জায়গায় wick contact থাকলেই downgrade) — শুধু আগে কোনো wick violation ছাড়া একদম "ক্লিন" body-close-through-ই ভ্যালিড TBS।
- **Model One ক্যান্ডেল:** valid TBS ফর্ম হওয়ার পর, **"Model One" ক্যান্ডেল** = সেই নির্দিষ্ট ক্যান্ডেল (CRT-র আগের high/low-এর সাপেক্ষে চিহ্নিত) যার **body সেই TBS লেভেলের ওপারে/মধ্যে ফিরে close করে** — এই closing ক্যান্ডেলই এন্ট্রি ট্রিগার।
- এন্ট্রি: Model One ক্যান্ডেলের close-এ (বা এর সামান্য বাইরে একটা limit-এ)।
- স্টপ লস: Model One ক্যান্ডেল/TBS লেভেলের ঠিক ওপরে/নিচে (বিপরীত পাশে)।
- টার্গেট: TP1 = original CRT ranging candle-এর 50% Fibonacci লেভেল (CRH–CRL); TP2 = CRT ranging candle-এর দূরের প্রান্ত (বুলিশ সেটআপে CRL, বেয়ারিশে CRH)।
- বায়াস: উভয় — বুলিশ রিভার্সাল (low-এর নিচে TBS, Model One ক্যান্ডেল আবার ওপরে close করে) অথবা বেয়ারিশ রিভার্সাল (high-এর ওপরে TBS, Model One ক্যান্ডেল আবার নিচে close করে) হিসেবে কাজ করে; higher-timeframe ট্রেন্ডের সাথে align থাকলে সবচেয়ে ভালো পারফর্ম করে বলা হয়েছে।

---

## ৩. ইমপ্লিমেন্টেশন প্রায়োরিটি (ফেজ ধরে করার পরামর্শ)

৯৬টা সেটআপ একসাথে এক ফাইলে কোড করলে Pine compile limit-এ আটকে যাবে (এই প্রজেক্টের আগের ইতিহাস অনুযায়ী)। তাই এভাবে ভাগ করে করুন:

**ফেজ ১ — কোর ইঞ্জিন (বিল্ডিং ব্লক, সেকশন ১-এ যা আছে)**
Swing detection, wick/body utility, pin bar/engulfing/doji/inside-bar ডিটেক্টর, FVG ডিটেক্টর, basic OB মার্কিং, BOS/CHoCH (valid vs wick-only), liquidity sweep-vs-run ক্লাসিফায়ার, equal-highs/lows গ্রুপিং। — এটাই বাকি সবকিছুর ভিত্তি, সবার আগে এটা রক-সলিড করতে হবে।

**ফেজ ২ — হাই-ভ্যালু, বহু-জায়গায়-রিপিট হওয়া সেটআপ (সেটআপ #১০, #২২, #২৫, #৩২, #৪৪, #৫০, #৫৫, #৫৯, #৬০, #৯৫-৯৬)**
এগুলো ট্রান্সক্রিপ্টে বারবার (ভিন্ন নামে) ফিরে এসেছে — মানে এগুলোই আসল "কোর কনসেপ্ট" (liquidity sweep, valid BOS/CHoCH, valid OB, valid FVG-sweep entry, supply/demand 50%-tap, key-level validity, pullback validity, CRT+TBS)। এগুলো একবার ঠিকমতো কোড হলে ক্যাটাগরি ২,৩,৪,৫,১১,১৯,২০,২৭,৩৮,৩৯-এর বেশিরভাগ "fade the breakout" / "sweep vs run" ভ্যারিয়েন্ট প্রায় ফ্রি-তে চলে আসবে (একই আন্ডারলাইং ফাংশনের প্যারামিটার বদলে)।

**ফেজ ৩ — HTF-নির্ভর সেটআপ (সেটআপ #৩১, #৫৩, #৬২-৬৫, #৭০-৭৩, #৮৩, #৮৪, #৮৫)**
`request.security()` লাগবে, তাই আলাদা ফেজে রাখা ভালো (রিপেইন্টিং ইস্যু সাবধানে হ্যান্ডেল করতে হবে — `barmerge.lookahead_off` ব্যবহার করুন)।

**ফেজ ৪ — বাকি নিশ (niche) প্যাটার্ন**
Quasimodo (#৮৮-৮৯), IFC candle (#৮৬-৮৭), CISD (#৬১), Reclaimed/Rejection block (#৪৫, #৪৯), Wyckoff (#৭৭), Double top/bottom (#৭৫-৭৬) — এগুলো compile-space বাঁচলে main engine-এ, নাহলে existing লিনিয়েজের মতো একটা companion overlay script-এ।

**সবগুলো ফেজেই দরকার:**
- প্রতিটা সেটআপ toggle করার input (`input.bool`) — ডেভেলপার/ইউজার নিজের দরকার মতো on/off করতে পারবে।
- প্রতিটা মেজর সেটআপের জন্য `alertcondition()`।
- প্রতিটা নতুন ভার্সনের সাথে একটা `AUDIT-vX.md` (এই প্রজেক্টের existing কনভেনশন)।

---

## ৪. উৎস ফাইল সংক্রান্ত নোট

- `smc_ict_crt.txt`-এ দুটো ভিডিও সেকশন **হুবহু দুইবার** এসেছে ("3 Powerful Strategies" এবং "Dual Trap Trading Setup") — এই ডকুমেন্টে merge করে একবারই রাখা হয়েছে (সেটআপ #৪৬-৪৭ ও #৭১-৭৩)।
- ক্যাটাগরি ৩১-এ "Wyckoff Method"-কে ট্রান্সক্রিপশন ভুলে "Whack-Off/Wedge Method" লেখা হয়েছিল — ডেভেলপমেন্টের সময় এটা আসলে **Wyckoff Method** ধরে নিতে হবে।
- অনেক সেটআপে "Stop Loss" বা "Target" এর নির্দিষ্ট নিয়ম বলা হয়নি (ভিডিওতে conceptually এড়িয়ে গেছে) — এসব ক্ষেত্রে ফেজ ৪-এ ডেভেলপ করার সময় ফ্রেমওয়ার্ক সেটআপ #৮৪ (Four-Factor Entry — reaction zone-এর পেছনে SL, নিকটতম reaction zone-এ TP) অনুসরণ করে ডিফল্ট বসিয়ে দিন।
