# CHANGELOG · `liqudity_trap_trading.v3.8.6.txt` — "Honest tracker"

> তারিখ: 2026-10-18 · ভিত্তি: v3.8.5 (compile OK)।
> Plan: [VERIFY_PATCHPLAN_v3.8.5_BN.md](VERIFY_PATCHPLAN_v3.8.5_BN.md) §4-এর প্রথম সারি। Patch উৎস: [patches_v3.8.6/G1](patches_v3.8.6/G1_tracker_honesty.md), [G4](patches_v3.8.6/G4_htf_continuation.md)।
> **Compile করা হয়নি।** TradingView-এ paste করে compile করুন, তারপর ফল জানান।
> v3.8.5 ফাইল যেমন ছিল তেমনই আছে।

**BUILD stamp (line 2):** `BUILD v3.8.6-b1 · 2026-10-18 · honest tracker …`। Pine editor-এ এই line না দেখলে পুরনো code চলছে।

---

## 1. যা ঢুকেছে

| ID | কী বদলাল | কোথায় (v3.8.6 line, আনুমানিক) | Signal বদলায়? |
|---|---|---|---|
| **E4** | চারটা mirrored exit block → একটা signed core (`d = ±1`) + `f_tight` helper। Order, দাম আর bid/ask আগের মতোই | 4816 helper, 4887-4928 | না |
| **#3** | Stop entry-তে বা তার পার হলে (`trdProt`) সেটা **BE**, SL না: BE, 1R lock, trail, Partial time scratch। `cntBE` counter নতুন। এগুলো আর daily loss হিসেবে গোনা হয় না | 4800, 4884-4885, 4899-4901 | হ্যাঁ: `lossToday` কমবে, governor দেরিতে দিন বন্ধ করবে |
| **F-1** | **`LQEXIT` journal line** প্রতিটা tracked exit-এ: side, SB/NS, tag (SL/BE/TP2/TP3/STR/TIME/EXP), R, bars, MFE, MAE (R-এ), entry, exit, ΣR | 4937-4952, journal `if` ~5609 | না (journal শুধু) |
| **NEW-1** | Gate machine signal মারলে `mcPlanLong/Short := na`। একই bar-এর engine signal এখন নিজের close-এ plan হয় | ~4552, ~4557 | হ্যাঁ: কিছু engine signal-এর accept/reject বদলাবে |
| **D2** | CE limit fill হলো, আর একই bar distal edge পার করে close করল → `cntVoid` + `lossToday` | 4066-4067, long/short violation branch, trackNew-এর আগে | হ্যাঁ: `lossToday` বাড়তে পারে |
| **E3** | Size label: `× syminfo.pointvalue`, cost যোগ, ২ decimal, futures-এ "contracts" | entry label | না (label শুধু) |
| **N-1** | Cont setup কখনো A+ পাবে না (`f_mcTier` `qualOk`) | `f_mcTier` | হ্যাঁ: cont-এ A+ বন্ধ |
| **N-2** | Cont liquidity override (+10) এখন শুধু **gate score**-এ, `f_tier`-এ না | `scoreBaseL/S` | হ্যাঁ: cont চলাকালীন sweep ছাড়া engine tier B |
| **A-4** | Dead external break latch (`extResBrk`…) মুছে দেওয়া | MODULE 6 | না |

**Code-এর হিসাব:**
- Code line: −123 / +73।
- `if`/`else` 423 → **388 (−35 scope)**।
- নতুন plot, alertcondition, input বা `request.security` নেই।
- Line ending সব CRLF।

## 2. যা ইচ্ছে করে বাদ রাখা হয়েছে

| ID | কেন |
|---|---|
| E1/D4, D5, E8 | আপনার default setting (`oneDir` on, `riskMode` Reject)-এ ঘটে না। পরের version-এ |
| SL alertcondition-এর title | **বদলানো হয়নি।** তাই আপনার existing alert ঠিকমতো চলবে। Message-এ শুধু "(loss; BE / trail exits are in the LQEXIT journal line)" যোগ হয়েছে। Alert এখন শুধু **আসল loss**-এ fire করে |
| G2, G3 (raid, stop) | v3.8.7-এ |

## 3. Dashboard আর alert-এ যা দেখবেন

- **Debug row 3:** `TP a/b/c SL n BE n void n exp n untrk n ΣR x.xx`
  - SL আগের চেয়ে কম দেখাবে, কারণ protected exit এখন BE-তে যায়।
  - ΣR হলো এই chart-এর সব tracked trade-এর মোট R।
- **"Any alert() function call" alert:**
  - এখন trade exit-এ `LQEXIT|…` line আসবে।
  - একই bar-এ exit আর নতুন entry হলে এক alert-এ দুই line আসবে, `\n` দিয়ে আলাদা, LQEXIT আগে।
- **উদাহরণ:**
  ```
  LQEXIT|XAUUSD|5|L|NS|BE|R0.12|b14|mfe1.35|mae0.40|E2645.30|X2645.62|ΣR3.75
  ```
  - `mfe1.35` মানে trade +1.35R পর্যন্ত গিয়েছিল।
  - `mae0.40` মানে −0.40R পর্যন্ত বিপক্ষে গিয়েছিল।

## 4. Compile checklist

1. Pine editor-এ পুরো ফাইল paste করুন, **Save** করুন, তারপর Add to chart।
2. Line 2-তে `v3.8.6-b1` দেখা যাচ্ছে কি না দেখুন।
3. Error এলে line number আর message হুবহু পাঠান।
4. **CE10117 (token limit) এলে কী কাটবেন:**
   1. MFE/MAE অংশ: `trdMfe`/`trdMae`-এর ৬টা লাইন আর message-এর `|mfe…|mae…` (প্রায় −40)।
   2. Debug row-এর `" void "…` আর `" ΣR "…` অংশ (প্রায় −15)।
   3. তারপর REVIEW-এর Doji/IB engine cut (−350)।
   - নোট: কাটার পরেও CE10117-এর count একই থাকলে editor-এ এখনো পুরনো code আছে।

## 5. Test checklist

| # | কী করবেন | কী দেখা উচিত |
|---|---|---|
| 1 | Non-SB trade TP1 ছুঁয়ে BE stop-এ বের হলো | `TP1+1, BE+1, SL+0`, LQEXIT `BE`, R প্রায় +0.1 |
| 2 | SB trade-এ TP2-এর পরে trail exit | `BE`, R > 2 |
| 3 | Gap দিয়ে stop পার হলো | LQEXIT `SL`, R < −1 |
| 4 | SB Partial time exit, পরে entry-তে stop | `BE`, R প্রায় 0, `lossToday` বাড়বে **না** |
| 5 | CE limit touch করে FVG-এর নিচে close করল | `void+1`, journal-এর d field-এ loss +1 |
| 6 | Cont (`MCc`) entry | tier কখনো A+ না |
| 7 | Cont setup চলাকালীন sweep ছাড়া CRT/TL engine signal | tier B (আগে A ছিল) |
| 8 | ES/NQ-এ riskMoney দেওয়া আছে | "≈ x.xx contracts", আগের চেয়ে ৫০/২০ গুণ কম |
| 9 | পুরনো আর নতুন version একই chart আর তারিখে | Entry signal প্রায় একই থাকবে। পার্থক্য শুধু N-1, N-2, NEW-1, D2-এর কারণে |

## 6. USER_MANUAL-এ যা বদলাতে হবে

Manual: `_7/Liqudity/USER_MANUAL_v3.8.5_BN.md`

- Debug row-এ `BE`, `void`, `ΣR`-এর ব্যাখ্যা যোগ করতে হবে।
- `LQEXIT` journal format (§3)।
- "SL hit" alert এখন শুধু loss-এ fire করে।
- Cont setup tier: সর্বোচ্চ A।

**পরের ধাপ:** compile করে ফল জানান। OK হলে v3.8.7 (Stops & raids: G2 + G3) শুরু করবো।
