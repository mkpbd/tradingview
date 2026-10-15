# Changelog · v3.8.2 + v3.8.3 (Step 1 + Step 2)

তারিখ: 2026-10-15 · ভিত্তি: `FORENSIC_AUDIT_v3.8.1.md` roadmap · ফোল্ডার: `MostosImportentIndicator_6/Liqudity/`
পুরনো ফাইল (`v3.8.1.txt`) অপরিবর্তিত। Local Pine compiler নেই, তাই দুটো build-ই **TradingView-এ compile করে দেখতে হবে**।

## Step 1 — `liqudity_trap_trading.v3.8.2.txt` (BUILD v3.8.2-b1)

**কেন:** `v3.8.1.txt` আসলে v3.6.1 code ছিল। v3.7-এর Z1–Z13 আর v3.8-এর A1–A3 তাতে ছিল না।

**কী:** `_5/Liqudity/liqudity_trap_trading.v3.8.txt` হুবহু নেওয়া হয়েছে। তার উপর শুধু v3.6.1-এর dead-code pass বসানো হয়েছে।

| ID | পরিবর্তন |
|---|---|
| D1 | `sesHiBroke/LoBroke` আর `f_sesTrack`-এর break flag export সরানো |
| D2 | `zoneInvalidatedUp/Dn` সরানো (FIX-T1 আগেই এর জায়গা নিয়েছে) |
| D3 | `p3PoolBar/p4PoolBar`, `ltLLevel/ltSLevel` tuple export সরানো |
| D4 | দুটো comment-এ `lookahead_off` → `lookahead_on` |

- কোনো gate, score, tier, zone, sweep, entry বা exit বদলায়নি। Signal v3.8-এর সাথে হুবহু এক হওয়া উচিত।
- যাচাই হয়েছে: `slHCrt`, `resBosDone`, `armBiasL`, FIX-Z10 আর FEM alert gate সব আছে। Outputs 8 + 12 + 3 + 30 = 53/64।
- Audit-এর P1 list-এর Z10 আর FEM-alert fix v3.8-এ আগেই ছিল। তাই Step 1-এ নতুন logic লাগেনি।

## Step 2 — `liqudity_trap_trading.v3.8.3.txt` (BUILD v3.8.3-b1)

**ইচ্ছাকৃত behaviour change।** নতুন `if` scope বা output slot নেই। একটা নতুন input যোগ হয়েছে।

| ID | সমস্যা | Fix | কী বদলাবে |
|---|---|---|---|
| D18 | EQ/PD/PW/session raid সবসময় কমপক্ষে VALID (2) পেত, 1-tick poke-ও | নতুন `f_poolQ(isLow, lvl)`। নিজের level-এর firm reclaim (0.125 ATR) বা penetration (0.25 ATR) না হলে WEAK (1)। আটটা stamp site এটা পড়ে | দুর্বল pool poke থেকে কম arm হবে |
| D20 | Shift-এর score `TRIG_LOOK` (10 bar)-এ শূন্য হতো, অথচ retest window 20 bar। ফলে বার 11–20-এ retest হলে `minScore` fail | Stage 3-এ shift points নিজের retest clock ধরে কমে, সর্বনিম্ন 50%। MSS 12, CHoCH 9 | দেরিতে আসা বৈধ retest এখন pass করতে পারে |
| D9 | Engine tier internal CHoCH বা খালি CISD-কেও trigger ধরত, machine ধরত না | Engine trigger = MSS বা external CHoCH। `shiftSrc` যোগ করলে তবেই internal CHoCH / CISD | Engine A-tier কম হবে |
| N1 | Ordinary machine-এর retest anchor যেকোনো ছোট FVG হতে পারত | নতুন input `mcFvgDisp` (ডিফল্ট ON)। Anchor FVG একটা displacement candle (≥ 0.8 ATR body) দিয়ে তৈরি হতে হবে | Anchor কম কিন্তু পরিষ্কার হবে। OFF করলে v3.8.2-এর মতো |
| D19 | CE limit দাম আগে জানানো হতো না, entry alert আসত fill-এর পরে | Anchor lock হওয়ার bar-এ alert() feed-এ `LQCE\|ticker\|tf\|L/S\|CE…\|SLa…\|SLr…` | Limit order আগে বসানো যাবে |

**D19 alert:** "Any alert() function call" alert-এ আসে। এটা journal-এর একই `if` ব্যবহার করে, তাই `jrnlEnable` OFF করলে এটাও বন্ধ। SLa হলো anchor stop, SLr হলো raid stop। Fill-এর সময় machine এই দুটোর একটা বেছে নেয়।

## Compile checklist (TradingView)

1. প্রথমে v3.8.2 paste করে Save করুন। Line 2-এ `BUILD v3.8.2-b1` দেখা যাচ্ছে কিনা মিলিয়ে নিন।
2. v3.8.2 compile হলে v3.8.3 একইভাবে করুন।
3. Compile-sensitive জায়গা:
   - `f_poolQ` একটা `for` loop-এর ভিতর থেকে call হয়। এতে কোনো `ta.*` নেই, তাই সমস্যা হওয়ার কথা না।
   - `hasTrig`-এর দ্বিতীয় লাইন continuation, indent 29 space।
   - `ceMsg` তিন লাইনের ternary, indent 5 space।
   - `trigLong :=` reassignment-এর type int, `math.round` int ফেরত দেয়।

## CE10117 ("too many tokens") এলে যা কাটবেন, এই ক্রমে

1. v3.8.3 header changelog comment (comment token গোনা হয় না, তবে নিশ্চিত হতে চাইলে)।
2. বাকি ২৫টা tooltip থেকে যেগুলো শুধু label আবার বলে (প্রায় −100)।
3. `riskMoney` / `tp1Pct` label text (প্রায় −40)।
4. `nonSbTp3` runner branch (প্রায় −80)।
5. D19 (`ceMsg` + `ceEvt*`, প্রায় −60)। Feature হারাবে, signal বদলাবে না।

Error এলে exact message আর token count পাঠান। একই count আবার এলে editor-এ পুরনো code রয়ে গেছে।

## Regression (chart-এ দেখার জিনিস)

| Build | প্রত্যাশা |
|---|---|
| v3.8.2 vs v3.8 | Signal, label, journal line হুবহু এক |
| v3.8.3 vs v3.8.2 | ◈/◇/▵ pool sweep-এর পরে কম `[SETUP] Armed`; বেশি দেরির (shift + 11–20 bar) machine entry; কম engine A-tier; শুধু displacement-FVG anchor; `LQCE` line প্রতিটা anchor lock-এ একবার |
| দুটোতেই | একই bar-এ long + short নেই; CE fill-এর entry bar-এ stop hit নেই; `[SIGNAL]` alert ↔ label 1:1 |

## পরের ধাপ (Step 3, compile ফলাফলের পর)

D8 + D21 (reward clamp), D4 (display ≠ detection), D5 (LT stop raid wick), D6 (LT invalidation / veto), D7 (HTF FVG min height), N-C (18B kill → stage 3)। আনুমানিক +190 token। v3.8.3 CE10117 দিলে Step 3-এর সাথে cut-ও লাগবে।
