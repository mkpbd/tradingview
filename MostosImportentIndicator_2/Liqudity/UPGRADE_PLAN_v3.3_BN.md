# UPGRADE PLAN — v3.2.2 → v3.3 "ONE DIRECTION · SB FAST PATH"
### Step-by-step, token-neutral, compile-safe

Reference: `FOURTH_PASS_AUDIT_v3.2.2_BN.md` (F-1 … F-17)
মূল নীতি: **Engine ভাঙব না, gate ঠিক করব।** প্রতিটা phase আলাদা compile + চার্ট test। একটা phase pass না হলে পরেরটায় যাব না।

---

## PHASE 0 — Baseline (কিছু বদলানোর আগে)

**0.1** `liqudity_trap_trading.txt` → git commit "v3.2.2 baseline before v3.3"।
**0.2** Pine Editor-এ paste → compile → কোনো warning থাকলে note করুন।
**0.3** তিনটা চার্ট বুকমার্ক: BTCUSDT.P 5m · XAUUSD 5m · NAS100USD 5m — এই তিনটাই regression test bed।
**0.4** Debug table ON (`showDbg = true`) করে বর্তমান counter লিখে রাখুন: `A / A+ / L / S / TP1 / TP2 / SL / exp / untrk`। v3.3-এর পরে এগুলো compare করব।
**0.5** Token headroom জানা: script-এর শেষে temporary একটা বড় dead-code block (যেমন ৩০ লাইন `string _pad = "…"`) যোগ করে দেখুন কত লাইনে CE10117 আসে → headroom-এর ধারণা। তারপর মুছে ফেলুন।

**Acceptance:** compile clean, তিন চার্টে indicator লোড, counter note করা।

---

## PHASE 1 — Direction conflict বন্ধ (F-1, F-2) · P0

### Step 1.1 — Neutral bias policy (F-1)
নতুন input, group `grpH`:
```pine
neutralMode = input.string("Follow chart structure", "When the HTF bias is NEUTRAL",
     options = ["Block both sides", "Follow chart structure", "Allow both (v3.2.2)"], group = grpH,
     tooltip = "Structure + EMA disagree = neutral. Block = no entry either way. Follow = use the chart's external structure direction. Allow = v3.2.2 behaviour (both sides pass).")
```
`htfB`-এর ঠিক নিচে (line ~1613) **দুটো resolved flag**:
```pine
// FIX-V1 (F-1): a neutral bias is a decision, not a permission slip
biasOkL = biasFilter == "Off" or htfB > 0 or (htfB == 0 and (neutralMode == "Allow both (v3.2.2)" or (neutralMode == "Follow chart structure" and extDir >= 0)))
biasOkS = biasFilter == "Off" or htfB < 0 or (htfB == 0 and (neutralMode == "Allow both (v3.2.2)" or (neutralMode == "Follow chart structure" and extDir <= 0)))
```
> ⚠ `extDir` MODULE 6-এ define হয় (1451) — `htfB` MODULE 7-এ (1613)। MODULE 6 আগে, তাই OK।

**Replace** (৭ জায়গা, প্রতিটায় `htfB >= 0` → `biasOkL`, `htfB <= 0` → `biasOkS`):
| লাইন | পুরনো | নতুন |
|---|---|---|
| 3714 | `(biasFilter == "Off" or htfB >= 0)` | `biasOkL` |
| 3715 | `(biasFilter == "Off" or htfB <= 0)` | `biasOkS` |
| 3511 | `(not armNeedHtf or biasFilter == "Off" or htfB >= 0)` | `(not armNeedHtf or biasOkL)` |
| 3623 | mirror | `(not armNeedHtf or biasOkS)` |
| 3056 | `(not ltCtxGate or biasFilter == "Off" or htfB >= 0)` | `(not ltCtxGate or biasOkL)` |
| 3057 | mirror | `(not ltCtxGate or biasOkS)` |
| 3577 | `(not sbReqHtf or htfB > 0)` | `(not sbReqHtf or (htfB > 0 or (htfB == 0 and biasOkL)))` |
| 3672 | mirror | `(not sbReqHtf or (htfB < 0 or (htfB == 0 and biasOkS)))` |

> 3577/3672-এ neutral-এ SB entry allow হবে শুধু `neutralMode` অনুযায়ী — arm আর entry এখন একই কথা বলে (F-11-ও এতে fix হয়)।

Token: +3 লাইন, −0 → নিট ছোট বৃদ্ধি। Scope: 0 (সব ternary/expression)।

### Step 1.2 — Master direction lock (F-2)
নতুন input, `grpQ`:
```pine
oneDir = input.bool(true, "One direction at a time (machine · engines · traps)", group = grpQ,
     tooltip = "While a trade is open, or a setup is AT POI or beyond, the opposite side may not arm, fire or confirm a trap. Turn OFF for v3.2.2 behaviour.")
```
MODULE 17-এর **আগে** (3462-এর উপরে, `sbFvgOkS`-এর পরে) — কিন্তু `trdDir` MODULE 19-এ declare → আগের বারের মান লাগবে। সমাধান: `trdDir` declaration block (3941–3953) **MODULE 17-এর উপরে** সরান (শুধু `var` লাইনগুলো, logic না)। তারপর:
```pine
// FIX-V2 (F-2): the chart has one narrative at a time
dirLock = not oneDir ? 0 : trdDir != 0 ? trdDir : suL >= 2 ? 1 : suS >= 2 ? -1 : 0
lockOkL = dirLock >= 0
lockOkS = dirLock <= 0
```
**প্রয়োগ:**
- 3510 arm condition-এ `and lockOkL`; 3622-এ `and lockOkS`
- 3714 `longOK ... and lockOkL`; 3715 `shortOK ... and lockOkS`
- LT machine: 3257 (`if _ltLState == 1 and ltBullConfNow ...`) `and lockOkL`; 3297 `and lockOkS`
  > `f_ltMachines` global পড়তে পারে; `dirLock` তার আগে define করতে হবে → `dirLock` block-টা MODULE 16B-এর **উপরে** (2940-এর আগে) রাখুন; `suL/suS` var declaration (3364–3379) সেখানে উঠিয়ে আনুন।

### Step 1.3 — Opposite sweep = stage-1 setup invalid
MODULE 17 long invalidation block (3467–3483)-এ একটা ternary:
```pine
        else if suL == 1 and bslSweep and lastBslQual >= 2
            suL := 0
            suLReason := "range swept both ways"
```
Short mirror (3599–3608): `suS == 1 and sslSweep and lastSslQual >= 2`।
> Scope: +2 `else if` branch। যদি CE10295 আসে → এই দুটো `expL`-এর মতো ternary-তে ভাঁজুন।

**Acceptance (Phase 1):**
- তিন চার্টে dashboard-এ আর "SWEPT / AT POI" দুই দিকে একসাথে দেখা যাবে না।
- Bias `→ —` থাকলে verdict বলবে `NO · neutral bias` (Step 5.3-এ যোগ হবে) অথবা extDir-এর দিকেই শুধু signal।
- Replay করে দেখুন: long trade open থাকতে কোনো short label / trap নেই।

---

## PHASE 2 — POI conflict (F-3, F-4) · P0/P1

### Step 2.1 — FIX-T20-কে একটা function-এ তুলে সব creation-এ ব্যবহার (F-3)
`f_newZone`-এর **উপরে** একটা helper (token-এ **সাশ্রয়**, কারণ দুটো inline block উঠে যাবে):
```pine
// FIX-V3 (F-3): one band, one side. The newcomer takes the band; the opposite
// side keeps what is left or is dropped (FIX-T19 height). Was inline for SD only.
f_claimBand(bool isSupply, float top, float bot) =>
    if array.size(zones) > 0
        for k = array.size(zones) - 1 to 0
            zo = array.get(zones, k)
            if zo.isSupply != isSupply
                float ot = box.get_top(zo.bx)
                float ob = box.get_bottom(zo.bx)
                if not (ob > top or ot < bot)
                    ot := isSupply ? math.min(ot, bot) : ot
                    ob := isSupply ? ob : math.max(ob, top)
                    if ot - ob < minZoneAtr * atr
                        box.delete(zo.bx)
                        array.remove(zones, k)
                    else if isSupply
                        box.set_top(zo.bx, ot)
                    else
                        box.set_bottom(zo.bx, ob)
```
**Replace:**
- 2392–2404 inline block → `f_claimBand(false, zTop, zBot)`
- 2431–2443 inline block → `f_claimBand(true, zTop, zBot)`
- OB push-এর আগে (2412, 2449) → `f_claimBand(false/true, obTop, obBot)`
- RB push-এর আগে (2468, 2480) → `f_claimBand(true, rbTop, rbBot)` / `f_claimBand(false, rbTop2, rbBot2)`
- IFVG push-এর আগে (2501, 2510) → same
- Flip (2249, 2295): flip-এর **পরে** `f_claimBand(z.isSupply, top, bot)` — ⚠ loop-এর ভেতরে `zones` mutate হবে; descending index loop + `continue` আছে, নিরাপদ, কিন্তু flipped zone নিজেই remove হতে পারে না (isSupply মিলে যায়) — ঠিক আছে।

Token: −২টা inline block (~26 লাইন) + ১ function (~16) + ৬ call → **নিট সাশ্রয়**। Scope: function ভেতরে 4, inline-এ ছিল 2×4 → সাশ্রয়।

### Step 2.2 — `poiConflict` flag (F-4)
`inDemand … nearSupply` (2846–2849)-এর নিচে:
```pine
// FIX-V4 (F-4): demand and supply within one ATR of each other is indecision, not a POI
poiConflict = not na(nbTop) and not na(nsBot) and nsBot - nbTop <= atr
```
**প্রয়োগ:**
- `poiLong`/`poiShort` (2860–2861): সামনে `poiConflict ? 0 :` 
- MODULE 17 `tapZone` (3527, 3639): `and not poiConflict`
- Dashboard verdict (Step 5.3): `poiConflict ? "NO · POI conflict (demand/supply " + str.tostring(nsBot - nbTop, format.mintick) + " apart)"`

### Step 2.3 — Flipped block-এর quarantine (optional, P2)
`Zone` type-এ field যোগ করার বদলে (token) `touchBar` reuse: flip-এ `z.touchBar := bar_index` set করুন (এখন −1)। `f_nextZones`-এ: `not (z.flipped and bar_index - z.touchBar < 10)`। Flip-এর ১০ বার পরে সেটা NEXT হতে পারবে।

**Acceptance (Phase 2):**
- BTC-র মতো `demand top == supply bottom` কেস আর দেখা যাবে না (Next demand / Next supply row মিলিয়ে দেখুন)।
- NAS-এর মতো ০.০৫% দূরত্বে দুই NEXT থাকলে verdict "NO · POI conflict"।

---

## PHASE 3 — Trap engine main pipeline-এ (F-5 … F-8) · P0/P1

### Step 3.1 — Confirmation থেকে raw sweep বাদ, confirmation bar ≠ retest bar (F-6)
- 3255: `ltBullConfNow = zoneBullConf or mssUp or chochUp or eChochUp` (**`or sslSweep` মুছুন**)
- 3294: mirror, **`or bslSweep` মুছুন**
- retest bar record: `_ltLRetOk := true` (3253)-এর সাথে `_ltLRetBar := bar_index` (নতুন `var int`); short 3292-এ `_ltSRetBar`।
- Signal condition (3257 / 3297)-এ যোগ: `and (not ltReqRetest or bar_index > _ltLRetBar)` / `_ltSRetBar`।
  > Retest বারে confirmation নয় — পরের বারে চাই। এটাই "failed break → confirmation" doctrine।

### Step 3.2 — Once-per-level latch (F-7)
`f_ltMachines`-এ `var float _ltLDoneLvl = na`, `_ltSDoneLvl = na`। Signal fire করার সময় `_ltSDoneLvl := _ltSLevel`। Arm condition (3274 `if _ltSArmTxt != ""`)-এ যোগ: `and (na(_ltSDoneLvl) or math.abs(_ltBrkLvlNow - _ltSDoneLvl) > ltClusterTol * atr)`। Long mirror।

### Step 3.3 — Narrative gate (F-8)
`ltCtxOKShort` (3057)-এ যোগ:
```pine
and not (regime == "TRENDING" and extDir == 1 and lastBslQualRaw < 3)
```
`ltCtxOKLong` mirror: `and not (regime == "TRENDING" and extDir == -1 and lastSslQualRaw < 3)`।
Score (3194) −10 → −20 counter-trend; নতুন লাইন: `s -= (isLong ? inOTEsell : inOTEbuy) ? 15 : 0  // fighting the OTE`।

### Step 3.4 — LT-কে engine candidate বানানো (F-5) — **সবচেয়ে বড় কাজ**
1. `f_ltMachines`-এ SL হিসাব করে return-এ যোগ: long → `math.min(low, _ltLLevel) - SL_PAD_ATR * atr`; short → `math.max(high, _ltSLevel) + SL_PAD_ATR * atr`। Return tuple-এ `_ltSlL, _ltSlS` (২টা বাড়ল)।
2. MODULE 13-র per-engine stop list (2351–2362)-এ `float slLTLong = na`, `float slLTShort = na` যোগ; `f_ltMachines`-এর পরে assign।
3. MODULE 18 (3762–3779): `sigLTLong := ltLongSig and longOK and engTierOKL`; `sigLTShort` mirror। (`ltLongSig` global bool → `sigLTLong = ltLongSig` দিয়ে শুরু করুন 3329-এর নিচে।)
4. `anyLong` (3781)-এ `or sigLTLong`; `anyShort`-এ `or sigLTShort`।
5. `selSLLong` (3844): `... sigTLLong ? slTLLong : sigLTLong ? slLTLong : na`; short mirror।
6. `f_sigLabels`: `longTxt := sigLTLong ? f_join(longTxt, "◬ TRAP " + ltPatsL + " · " + str.tostring(ltLongScore)) : longTxt` — এজন্য `_ltLPats` return করতে হবে (`ltDbgMach` string ইতিমধ্যে আছে; সেটা থেকে না নিয়ে সরাসরি `_ltLPats` return যোগ করুন)।
7. **মুছুন** 3305–3314 (আলাদা TRAP label block) — token সাশ্রয়। LT alert() feed (3316–3321) রাখুন।
8. **মুছুন** 4800–4801 দুটো `[LT] HIGH+` alertcondition (এখন "Any LONG/SHORT" দিয়েই আসে) → **২টা output slot free** (Phase 4-এ লাগবে)।
9. Veto (3822–3823) রাখুন — এখন `sigLTLong` নিজেই `anyLong`-এর অংশ, তাই veto শুধু opposite engine মুছবে।

**ফল:** Trap signal এখন SL/TP line, RR, risk cap, min RR, cooldown, tracking, SB-13 hierarchy — সব পায়। "VERY HIGH 85" আর "score 42" একই বারে আর হবে না, কারণ `longOK` (minScore) trap-কেও gate করবে।

> Trap score-কে tier-এ map করার দরকার নেই — `engTierOKL` (`tierLong >= minRank`) দিয়েই grade হবে; trap-এর নিজের class শুধু label text।

**Acceptance (Phase 3):**
- XAU replay: uptrend/discount-এ TRAP SHORT নেই।
- প্রতিটা TRAP label-এর সাথে E/SL/TP1/TP2/TP3 line।
- একই level-এ ১০ বারের মধ্যে দ্বিতীয় TRAP নেই।
- Debug counter-এ trap trade-গুলো TP/SL-এ গণনা হচ্ছে।

---

## PHASE 4 — Silver Bullet FAST PATH (F-9 … F-13) · P0

### Step 4.1 — SB-র নিজস্ব shift definition (F-9)
নতুন input, `grpSB`:
```pine
sbShiftSrc = input.string("Internal CHoCH / CISD + displacement", "SB shift (LTF model)",
     options = ["Same as machine (v3.2.2)", "Internal CHoCH / CISD + displacement"], group = grpSB,
     tooltip = "Silver Bullet is a lower-timeframe model: its shift is a displaced break of the SHORT-TERM swing (internal CHoCH) or a CISD, cut by a displacement candle. External CHoCH inside an 8-bar clock is not realistic on M5.")
```
`shiftUpOk`-এর নিচে:
```pine
sbDispNow  = body >= dispFactor * atr
sbShiftUp  = sbShiftSrc == "Same as machine (v3.2.2)" ? shiftUpOk : (mssUp or eChochUp or ((chochUp or cisdUp) and bullBar and sbDispNow))
sbShiftDn  = sbShiftSrc == "Same as machine (v3.2.2)" ? shiftDnOk : (mssDn or eChochDn or ((chochDn or cisdDn) and bearBar and sbDispNow))
```
3538: `if suL == 2 and (sbTagL != 0 ? (sbReqMss ? mssUp : sbShiftUp) : shiftUpOk)`; 3647 mirror।
`sbShiftGL := mssUp ? 2 : 1` অপরিবর্তিত (CHoCH/CISD grade 1 — score-এ ১ point কম, exit rule-এ কড়া — ঠিকই আছে)।

### Step 4.2 — SB stage 1 → 3 সরাসরি (F-10)
Long machine-এ stage-1 block (3526)-এর **আগে**:
```pine
    // FIX-V6 (F-10): in the SB model the raid IS the POI — a displaced shift while
    // the sweep is in play goes straight to stage 3
    if suL == 1 and sbTagL != 0 and sslInPlay and sbShiftUp
        suL := 3
        suLBar := bar_index
        sbShiftGL := mssUp ? 2 : 1
        suLAnchorT := na
        suLAnchorB := na
        suLFvgBar  := na
```
তারপর existing stage-3 block (3553) "first FVG after shift" ধরে নেবে (`cFvgBBar > suLBar`) — ⚠ shift bar-এই FVG cut হলে `cFvgBBar == suLBar` → `>` fail। তাই 3554-র `cFvgBBar > suLBar` → `cFvgBBar >= suLBar` (FIX-P1-3-এর intent অক্ষুণ্ণ: shift bar বা পরে)। Short mirror।

### Step 4.3 — Final gate: reason লিখুন, stage 3-এ ফেরত, SB cooldown-মুক্ত (F-12)
MODULE 18-এ 3744-এর **আগে**:
```pine
// FIX-V7 (F-12): the SB path outranks the same-direction cooldown (SB-13 rank 3)
longOK  := longOK  or (sbSigLong  and (biasOkL) and kzOK and newsOK and chopOKL and sbOnlyOK and (minScore == 0 or scoreLong  + sbCtxLong >= minScore))
shortOK := shortOK or (sbSigShort and (biasOkS) and kzOK and newsOK and chopOKS and sbOnlyOK and (minScore == 0 or scoreShort + sbCtxShort >= minScore))
```
> `masterCd` বাদ গেল SB-র জন্য; বাকি gate একই। (`scoreLong` ইতিমধ্যে sbCtx সহ clamp করা — `+ sbCtxLong` বাদ দিন, শুধু `scoreLong >= minScore`।)

3749-এর পরে rollback with reason:
```pine
// FIX-V8 (F-12): a final-gate mute is a reason and a retry, not a silent death
gateKillL = suL == 4 and suLBar == bar_index and not sigMCLong ? (not longOK ? (minScore > 0 and scoreLong < minScore ? "gate: score " + str.tostring(scoreLong) + " < " + str.tostring(minScore) : not longCdOK ? "gate: cooldown" : not newsOK ? "gate: volatility window" : not chopOKL ? "gate: chop" : "gate: bias / session") : "gate: tier " + f_tierTxt(mcTierL) + " < min") : ""
suL       := gateKillL != "" ? 3 : suL          // back to SHIFTED — the anchor is still valid
suLReason := gateKillL != "" ? gateKillL : suLReason
```
Short mirror। এখন retest window (`retWait` / `sbRetWait`)-এর ভেতরে পরের বারে আবার entry চেষ্টা হবে। `mcPlanLong`/`slMCLong` non-var, প্রতি বারে নতুন — ঠিক আছে।
> ⚠ 4167 `suL == 4 and trdDir == 0 and not sigMCLong → 0` এখন আর এই কেসে লাগে না (stage 3-এ)। Conflict rollback (3799–3808) আর planOK rollback (3897–3902) আগের মতোই 0-তে — ওগুলো ঠিক আছে।

### Step 4.4 — Pool kind memory রক্ষা (F-13)
1158 / 1166-এ:
```pine
    lastSslKind := (sslInPlay[1] and lastSslKind >= 2 and math.abs(lastSup - lastSslLvl) <= NEAR_LVL_ATR * atr) ? lastSslKind : 1
```
> Engineered pool in play থাকতে তার গায়ের (0.25 ATR) swing sweep kind downgrade করবে না। `lastSslLvl` assignment-এর **আগে** এই লাইন (1156-এর উপরে) রাখুন, নইলে `lastSslLvl` ইতিমধ্যে overwritten। Short mirror।

### Step 4.5 — SB per-window once + SB dashboard reason
- `var int sbDoneWinL = 0` — SB entry fire করলে `sbDoneWinL := sbTagL`; arm gate `sbArmOkL`-এ `and sbCtxWin != sbDoneWinL`; window বদলালে reset (`sbWinNow != sbWinNow[1] → 0`)। Short mirror।
- Debug table "◆ SB" row-এ `suLReason` যখন `sbTagL != 0` — reason ইতিমধ্যে Machine L row-এ আছে; extra কিছু লাগবে না।

### Step 4.6 — SB displacement threshold আলাদা (tuning)
`sbFvgOkL` (3459)-এ `cFvgBDisp` 1.2 ATR body চায়। SB-র জন্য input `sbDispAtr = 0.8` যোগ করে `f_latestFvg`-এ `_cFvgBDisp := bullBar[1] and body[1] >= math.min(dispFactor, sbDispAtr) * atr`। (একটা মাত্র লাইন; non-SB path `sbFvgOkL` পড়ে না, তাই প্রভাব নেই।)

**Acceptance (Phase 4):**
- Replay NY AM window (10:00–11:00 NY) ৫টা দিন: প্রতিটায় debug "◆ SB" row-এ `tag L/S ≠ 0` দেখা যাবে; setup stage 3 পর্যন্ত যাবে; কমপক্ষে ২–৩টা `◆ SB … CE` entry।
- কোনো SB setup আর "POI tap expired (no shift)" বলে মরবে না; মরলে reason `gate: …` বা `SB window closed`।
- `cntSbEnt > 0`।

---

## PHASE 5 — Display / clutter (F-15, F-16) · P2

**5.1** `f_newZone`: text শুধু `star` (★HP) zone-এ; বাকি `text = ""`। NEXT zone-এর text `f_drawNextLvl` দেয়। Flip text (`"MITIGATION ▲"`) → `"MIT"`; RB → `"RB"`; IFVG → `"IFVG"`। Token সাশ্রয় (string literal ছোট)।
**5.2** RB zone cap: `f_zoneCreate`-এর শেষে `maxZones` census-এ RB আলাদা করে সর্বোচ্চ 2/side (kind == "RB" count)।
**5.3** Dashboard verdict-এ নতুন reason (Step 1.1, 2.2): `dirLock != 0 ? "NO · " + (dirLock == 1 ? "long" : "short") + " narrative live"`, `poiConflict ? "NO · POI conflict"`, `htfB == 0 and neutralMode == "Block both sides" ? "NO · neutral bias"`।
**5.4** Trap label-এ score-এর জায়গায় class শুধু (`HIGH`), Alignment score label header-এ থাকে — দুই সংখ্যা এক label-এ নয় (F-16)।

---

## PHASE 6 — Budget, twin, verification

### 6.1 Token / scope ledger (প্রতিটা phase-এর পরে compile)
| Phase | যোগ | কাটা | নিট |
|---|---|---|---|
| 1 | ~12 লাইন | 0 | + |
| 2 | ~20 (function) | ~26 (২ inline block) | **−** |
| 3 | ~25 | ~12 (label block) + 2 alertcondition | + ছোট |
| 4 | ~40 | 0 | + |
| 5 | 0 | ~15 (text literal) | **−** |

CE10117 এলে কাটার ক্রম (least value first):
1. Doji engine (`f_dojiRev` + inputs + label text) — C-tier, কখনো A হয় না
2. Inside-bar engine (`f_insideBar`)
3. LT-4 shadow-high watcher (`_p4*`) + pool line
4. `f_dbg` debug table (release build-এ)
5. HTF CRT/TBS security call (`f_crtTbsHtf`)

CE10295 (scope) এলে: নতুন `if` block → ternary assignment (script-এর "SCOPE:" pattern)।

### 6.2 Output budget
Phase 3.4-এ ২টা alertcondition free → একটায় `[SIGNAL] ◬ Trap entry` (anyLong/anyShort-এর subset হিসেবে `sigLTLong or sigLTShort`), একটা reserve।

### 6.3 Strategy twin
`version_02_strategy.pine` ব্যবহার করলে: v3.3 file → `indicator()` লাইন swap → MODULE 19S paste → Strategy Tester-এ তিন symbol × ৩ মাস। তুলনা: v3.2.2 vs v3.3 — trade count, win %, avg R, max DD। **কমপক্ষে ৩০ trade না হলে কোনো সিদ্ধান্ত নয়।**

### 6.4 Forward test checklist (২ সপ্তাহ, alert "Once per bar close")
- [ ] কোনো বারে long আর short label একসাথে নেই
- [ ] Trade open থাকতে opposite trap/signal নেই
- [ ] Next demand/supply কখনো edge share করে না
- [ ] প্রতিটা signal label-এর E/SL/TP line আছে
- [ ] SB window-এ setup arm → stage 3 → entry বা reason সহ death
- [ ] Debug counters: `untrk` ছোট, `exp` যুক্তিসঙ্গত

### 6.5 Commit / version
- Header-এ `v3.3` block: FIX-V1 … FIX-V8 তালিকা (এই ফাইলের step number-এর সাথে মিলিয়ে)।
- `indicator("… v3.3", "LQ-SD-PA v3.3", …)`।
- Commit: `feat(indicator): v3.3 one-direction lock + SB fast path (FIX-V1..V8)`।

---

## দ্রুত সারসংক্ষেপ — কোন step কোন finding

| Step | Fix করে | Severity |
|---|---|---|
| 1.1 | F-1, F-11 | P0 |
| 1.2, 1.3 | F-2 | P0 |
| 2.1 | F-3 | P0 |
| 2.2, 2.3 | F-4 | P1 |
| 3.1 | F-6 | P1 |
| 3.2 | F-7 | P1 |
| 3.3 | F-8 | P1 |
| 3.4 | F-5, F-16 | P0 |
| 4.1 | F-9 | P0 (SB) |
| 4.2 | F-10 | P0 (SB) |
| 4.3 | F-12 | P0 (SB) |
| 4.4 | F-13 | P1 (SB) |
| 5.x | F-15, F-16 | P2 |
| 6.x | F-17 | — |

**ক্রম বদলাবেন না।** Phase 1 ছাড়া Phase 4-এর SB এখনো দুই দিকে arm করবে; Phase 3 ছাড়া trap label SB entry-র পাশে গোলমাল করবে।
