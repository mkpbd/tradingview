//+------------------------------------------------------------------+
//|                                              LQ_v3.8.6_MT5.mq5   |
//|  Liquidity + S/D + Price Action v3.8.6 — MQL5 port of            |
//|  liqudity_trap_trading.v3.8.6.txt (Pine v6, BUILD v3.8.6-b1)     |
//|                                                                  |
//|  Port notes                                                      |
//|  * Every module (3 candle · 4 pivots/EQ · 4B sessions/SB ·       |
//|    5 liquidity · 6 structure · 7 HTF bias · 9 HTF engines ·      |
//|    10 dealing range · 11 regime · 12 FVG · 13 zones · 14 engines |
//|    · 16 score/tier · 16B trap engine · 17 machine · 18 gates ·   |
//|    18B viability · 19 tracker · 20-23 visuals/tables/alerts)     |
//|    runs once per CLOSED bar in the Pine order. Pine gates the    |
//|    engine on barstate.isconfirmed, so nothing repaints.          |
//|  * request.security(..., [1], lookahead_on) = the previous       |
//|    COMPLETED HTF / D1 / W1 candle (CopyRates feeds).             |
//|  * Sessions are New York time: server clock -> UTC ("Server GMT  |
//|    offset", -99 = auto) -> New York with US DST.                 |
//|  * Pine box -> canvas fill (real alpha) + border + text objects. |
//|    Pine label -> filled pill (OBJ_EDIT rows). Pine table ->      |
//|    rectangle labels. plot -> DRAW_LINE buffers. plotchar ->      |
//|    Unicode text marks. bgcolor -> canvas columns.                |
//|  * alertcondition / alert() -> MT5 Alert / push (inputs below).  |
//+------------------------------------------------------------------+
#property copyright   "LQ-SD-PA v3.8.6 — MQL5 port"
#property version     "3.86"
#property description "Liquidity + Supply/Demand + Price Action v3.8.6 (port of the Pine v6 build): sweeps (swing / EQ / PDH-PDL / PWH-PWL / session),"
#property description "structure (BOS / CHoCH / MSS), FVG + IFVG, zones (SD / OB / RB / BRK / MIT / IFVG), HTF bias + HTF POI, Silver Bullet,"
#property description "setup state machine, liquidity trap engine, gates, trade tracker, dashboard, debug, alerts."
#property indicator_chart_window
#property indicator_buffers 8
#property indicator_plots   8
#property indicator_type1   DRAW_LINE
#property indicator_label1  "Resistance (last swing high)"
#property indicator_type2   DRAW_LINE
#property indicator_label2  "Support (last swing low)"
#property indicator_type3   DRAW_LINE
#property indicator_label3  "Protected low (external)"
#property indicator_width3  2
#property indicator_type4   DRAW_LINE
#property indicator_label4  "Protected high (external)"
#property indicator_width4  2
#property indicator_type5   DRAW_LINE
#property indicator_label5  "Prev day high"
#property indicator_type6   DRAW_LINE
#property indicator_label6  "Prev day low"
#property indicator_type7   DRAW_LINE
#property indicator_label7  "Prev week high"
#property indicator_width7  2
#property indicator_type8   DRAW_LINE
#property indicator_label8  "Prev week low"
#property indicator_width8  2

#include <Canvas\Canvas.mqh>

double BRes[], BSup[], BPLo[], BPHi[], BPdh[], BPdl[], BPwh[], BPwl[];

//+------------------------------------------------------------------+
//| option enums (Pine input.string options)                         |
//+------------------------------------------------------------------+
enum ENUM_PROF   { PROF_MAN = 0,   // Manual
                   PROF_FX  = 1,   // FX majors
                   PROF_XAU = 2,   // Metals / XAU
                   PROF_IDX = 3,   // Indices
                   PROF_CRY = 4 }; // Crypto
enum ENUM_BIASF  { BF_OFF = 0,     // Off
                   BF_5   = 1,     // 5
                   BF_15  = 2,     // 15
                   BF_60  = 3,     // 60
                   BF_240 = 4,     // 240
                   BF_D   = 5 };   // D
enum ENUM_BIASM  { BM_EMA = 0,     // EMA only
                   BM_STR = 1,     // Structure only
                   BM_BOTH = 2 };  // Structure + EMA
enum ENUM_NEUT   { NM_BLOCK = 0,   // Block both sides
                   NM_FOLLOW = 1,  // Follow chart structure
                   NM_ALLOW = 2 }; // Allow both (v3.2.2)
enum ENUM_HTFSEL { HS_AUTO = 0,    // Auto
                   HS_15 = 1,      // 15
                   HS_30 = 2,      // 30
                   HS_60 = 3,      // 60
                   HS_240 = 4,     // 240
                   HS_D = 5 };     // D
enum ENUM_NXANCH { NX_PROX = 0,    // Proximal edge
                   NX_CE = 1 };    // Zone 50% (CE)
enum ENUM_RSRC   { RS_EXT = 0,     // External
                   RS_INT = 1 };   // Internal
enum ENUM_SBENT  { SBE_CE = 0,     // CE (50%) only
                   SBE_CEPRX = 1 };// CE preferred + proximal on strong rejection
enum ENUM_SBTIER { SBT_A = 0,      // A and above
                   SBT_AP = 1 };   // A+ only
enum ENUM_SBSUP  { SUP_OFF = 0,    // Off
                   SUP_DOWN = 1,   // Down-weight
                   SUP_SUPP = 2 }; // Suppress
enum ENUM_SBTIME { SBX_FULL = 0,   // Full
                   SBX_PART = 1 }; // Partial (rest to break-even)
enum ENUM_TIERM  { TM_AP = 0,      // A+ only
                   TM_A = 1,       // A and above
                   TM_B = 2,       // B and above
                   TM_ALL = 3 };   // All (incl. C)
enum ENUM_SHIFT  { SH_MSS = 0,     // MSS only
                   SH_EXT = 1,     // MSS / external CHoCH
                   SH_INT = 2,     // + internal CHoCH
                   SH_CISD = 3 };  // + CISD
enum ENUM_POISRC { PS_ZONE = 0,    // Zone / HTF POI only
                   PS_OTE = 1 };   // Zone / HTF POI + OTE
enum ENUM_MCENT  { MC_PRX = 0,     // Proximal edge + confirmation (v3.4)
                   MC_CEPREF = 1,  // CE preferred + confirmation fallback
                   MC_CE = 2 };    // CE (50%) only
enum ENUM_TPMODE { TP_LIQ = 0,     // Liquidity target
                   TP_R = 1 };     // R multiple
enum ENUM_RISKM  { RM_REJ = 0,     // Reject the signal
                   RM_CLAMP = 1 }; // Clamp the stop
enum ENUM_LTMIN  { LTM_MED = 0,    // MEDIUM and above
                   LTM_HIGH = 1,   // HIGH and above
                   LTM_VH = 2 };   // VERY HIGH only
enum ENUM_SZ     { SZ_TINY = 0,    // Tiny
                   SZ_SMALL = 1,   // Small
                   SZ_NORMAL = 2,  // Normal
                   SZ_LARGE = 3 }; // Large

//+------------------------------------------------------------------+
//| INPUTS (MODULE 1) — same names, defaults and groups as Pine      |
//+------------------------------------------------------------------+
input group "MT5 port"
input int         i_calcBars   = 5000;      // Bars to calculate (history depth)
input int         i_srvGmt     = -99;       // Server GMT offset, hours (-99 = auto from terminal)
input string      i_font       = "Arial";   // Font
input string      i_symFont    = "Segoe UI Symbol"; // Font for the ◆ ◈ ◇ ✕ ▵ ▿ ◦ marks
input bool        i_dashShift  = true;      // Shift the chart so the newest bars clear the dashboard
input int         i_maxLabels  = 500;       // Max labels kept (Pine max_labels_count)
input int         i_maxLines   = 500;       // Max lines kept (Pine max_lines_count)
input bool        i_alPopup    = true;      // Alerts: MT5 pop-up
input bool        i_alPush     = false;     // Alerts: push notification
input bool        i_alSignals  = true;      // Alert: A+/A and Any LONG / SHORT signal
input bool        i_alSetup    = false;     // Alert: setup armed / POI / shift / invalidated / continuation
input bool        i_alTrade    = true;      // Alert: TP1 / TP2 / SL
input bool        i_alTrig     = false;     // Alert: MSS / external CHoCH
input bool        i_alLiq      = false;     // Alert: sweeps / pools / session raids / next zone entered
input bool        i_alCtx      = false;     // Alert: volatility window start / end
input bool        i_alLT       = true;      // Alert: trap armed / trap entries
input bool        i_alSB       = true;      // Alert: Silver Bullet entry

input group "General"
input int         pivLen     = 5;           // Internal pivot length
input int         extPivIn   = 12;          // External pivot length (major swings)
input int         atrLen     = 14;          // ATR length
input int         biasLen    = 50;          // Bias EMA length (MTF table)
input bool        showLevels = true;        // Show last swing high/low key levels
input ENUM_PROF   symProfile = PROF_MAN;    // Symbol profile

input group "HTF context"
input ENUM_BIASF  biasFilter   = BF_60;     // HTF bias filter — block counter-trend entries
input ENUM_BIASM  biasMode     = BM_BOTH;   // HTF bias source
input int         htfStructPiv = 5;         // HTF structure pivot length (HTF bars)
input bool        htfProtInval = true;      // HTF protected swing invalidates a setup
input ENUM_NEUT   neutralMode  = NM_FOLLOW; // When the HTF bias is NEUTRAL
input bool        useHtfCrt    = true;      // HTF CRT + Turtle-soup trigger candidates
input ENUM_HTFSEL htfSel       = HS_AUTO;   // HTF for CRT / TBS / POI
input int         hPoiMaxAge   = 40;        // HTF POI max age (HTF candles)
input int         hPoiMaxTouch = 2;         // HTF POI spent after N separate visits

input group "Liquidity"
input bool        showSweeps  = true;       // Mark liquidity sweeps (◆ / ◈)
input int         sweepLook   = 12;         // Sweep stays in play (bars)
input bool        showEq      = true;       // Track equal highs / lows (EQH / EQL)
input double      eqTol       = 0.15;       // Equal level tolerance (ATR ×)
input int         eqMaxAge    = 240;        // EQ pool expires after N bars
input int         minArmQual  = 2;          // Min sweep quality to arm a setup (1–4)
input int         reclaimBars = 4;          // Multi-bar sweep: reclaim within N bars of a break (0 = off)
input bool        showPdwl    = true;       // Previous day / week high–low lines

input group "Structure"
input bool        showStruct = true;        // Label BOS / CHoCH / MSS
input double      structDisp = 0.5;         // Structural break body ≥ ATR × (0 = any close)
input bool        showProt   = true;        // Plot protected swing (external)
input bool        mssNeedExt = true;        // MSS requires an EXTERNAL CHoCH (internal = CISD grade)

input group "FVG"
input bool        showFvg    = true;        // Draw live chart-TF FVGs
input int         fvgMaxKeep = 4;           // Max live FVGs per side
input int         fvgMaxAge  = 120;         // FVG max age (bars)
input bool        useIfvg    = true;        // Flip violated FVGs into IFVG (inverted) POIs

input group "Supply / Demand / Order blocks"
input bool        showZones    = true;      // Show zones
input double      dispFactIn   = 1.2;       // Displacement body ≥ ATR ×
input double      maxZoneAtr   = 2.0;       // Max zone height (ATR ×)
input int         maxZones     = 6;         // Max zones per side
input bool        showOB       = true;      // Also mark the ORDER BLOCK origin candle
input int         confirmWin   = 5;         // Max bars from 50% tap to confirmation
input bool        showFlip     = true;      // Flip violated zones into breaker / mitigation blocks
input bool        showRB       = true;      // Rejection blocks (swept pivot wick + displacement away)
input double      minZoneIn    = 0.15;      // Min zone height (ATR ×)
input int         zoneMaxTests = 2;         // Zone spent after N separate tests

input group "Next buy / sell level"
input bool        showNextLvl    = true;    // Show NEXT BUY / NEXT SELL level
input ENUM_NXANCH nextLvlAnchor  = NX_PROX; // Line sits on
input bool        nextLvlBox     = true;    // Shade the zone band
input bool        nextLvlPct     = true;    // Show distance from price (%)
input int         nextLvlBack    = 60;      // Line extends back N bars
input bool        nextInclHtf    = true;    // Include the HTF FVG POI as a NEXT level candidate
input double      hPoiNextMaxAtr = 4.0;     // HTF POI may be the NEXT level only if height ≤ ATR ×

input group "CRT / Turtle soup / CISD / IFC"
input bool        showCRT     = true;       // CRT 3-candle trigger candidates
input double      crtRangeAtr = 1.2;        // CRT min candle-1 range (ATR ×)
input double      crtDispAtr  = 0.5;        // CRT min candle-3 body (ATR ×)
input bool        showTBS     = true;       // Turtle soup trigger candidates
input int         tbsLen      = 20;         // Turtle soup lookback (bars)
input int         tbsAgeMin   = 4;          // Swept extreme min age (bars)
input int         tbsAgeMax   = 60;         // Swept extreme max age (bars, 0 = off)
input bool        cisdAsConf  = true;       // Accept CISD as execution confirmation
input int         sigCooldown = 10;         // Engine cooldown per direction (bars)

input group "Inside bar / Doji (context-gated)"
input bool        showS3     = true;        // Inside Bar Breakout trigger
input double      ibBodyAtr  = 1.0;         // Min mother-candle body (ATR ×)
input bool        showS4     = true;        // Doji Reversal trigger
input double      dojiPct    = 25;          // Doji body ≤ % of range
input int         dojiMin    = 3;           // Min dojis in window
input double      minWickAtr = 0.3;         // Min significant wick (ATR ×)

input group "Trendlines"
input bool        showTL     = true;        // Draw dynamic trendlines (pivot pairs)
input bool        tlSweepEnt = true;        // Trendline sweep trigger candidates
input bool        tlNeedConf = true;        // Require confirmation candle at the line
input int         tlTouchMin = 0;           // Extra touches before sweep trigger
input int         tlMaxAge   = 150;         // Trendline expires after N bars

input group "◎ HTF POI continuation (HTF POI tap → shift → FVG → CE)"
input bool        contOn  = true;           // ◎ Machine: an HTF POI tap may arm WITHOUT a sweep (continuation)
input bool        showPoi = true;           // Draw live HTF FVG POI boxes

input group "Dealing range / OTE"
input ENUM_RSRC   rangeSrc = RS_EXT;        // Dealing range swings

input group "Sessions (New York time)"
input bool        useKZ     = false;        // Only signal inside killzones (intraday)
input bool        paintKZ   = false;        // Shade killzones
input bool        showSesHL = true;         // Session high / low liquidity lines
input string      asiaSes   = "2000-0000";  // Asia
input string      lonSes    = "0200-0500";  // London
input string      nySes     = "0700-1000";  // New York AM
input string      sbSesLO   = "0300-0400";  // Silver Bullet — London open
input string      sbSesAM   = "1000-1100";  // Silver Bullet — NY AM
input string      sbSesPM   = "1400-1500";  // Silver Bullet — NY PM

input group "◆ ICT Silver Bullet — setup"
input bool        sbEnable     = true;      // Enable the enhanced Silver Bullet module
input bool        sbUseLO      = true;      // London SB — 03:00–04:00 NY
input bool        sbUseAM      = true;      // NY AM SB — 10:00–11:00 NY (priority)
input bool        sbUsePM      = true;      // NY PM SB — 14:00–15:00 NY
input int         sbPreMin     = 15;        // Arm from N minutes BEFORE the window
input int         sbQualLO     = 3;         // London — min sweep quality (1–4)
input int         sbQualAM     = 2;         // NY AM — min sweep quality (1–4)
input int         sbQualPM     = 3;         // NY PM — min sweep quality (1–4)
input bool        sbPoolPref   = true;      // Require a preferred pool (prior session / EQH-EQL / PDH-PDL)
input bool        sbAsiaPool   = true;      // Count Asia session H/L raids as SB pools (inside SB windows only)
input bool        sbChopBypass = true;      // SB may arm in CHOP regime
input bool        sbKillAtEnd  = true;      // Kill an unfilled SB setup at the window close
input int         sbLiqWait    = 12;        // SB clock: bars sweep → POI tap
input int         sbPoiWait    = 8;         // SB clock: bars POI tap → shift
input int         sbRetWait    = 10;        // SB clock: bars shift → entry
input double      sbFvgMinAtr  = 0.10;      // SB FVG min height (ATR ×)
input double      sbDispAtr    = 0.8;       // SB displacement body ≥ ATR × (FVG leg + shift candle)
input bool        sbReqMss     = false;     // Require a true MSS for the SB shift (reject CHoCH / CISD)

input group "◆ Silver Bullet — entry"
input ENUM_SBENT  sbEntryMode = SBE_CEPRX;  // SB entry rule
input bool        sbReqHtf    = true;       // Require HTF bias alignment
input bool        sbReqPD     = true;       // Require the correct premium / discount side
input ENUM_SBTIER sbMinTier   = SBT_A;      // Min tier for an SB entry
input ENUM_SBSUP  sbSuppress  = SUP_DOWN;   // Non-SB signals while an SB setup is live
input bool        sbOnly      = false;      // SB-only mode — no signals outside the SB windows

input group "◆ Silver Bullet — exits"
input bool        sbTimeExit = true;        // Force an exit at the window close when TP1 is unhit
input ENUM_SBTIME sbTimeMode = SBX_FULL;    // Window-close exit
input bool        sbLiqTgt   = true;        // TP3 = nearest opposing session H/L · PDH/PDL · unspent opposite POI
input bool        sbStructEx = true;        // Exit the remainder on an opposing MSS / CISD
input double      sbBeBuf    = 0.15;        // Break-even buffer after TP1 (ATR ×)
input bool        sbTrail    = true;        // Trail behind the protected swing after TP2

input group "◆ Silver Bullet — visuals / alerts"
input bool        sbPaint    = true;        // Highlight the active SB window
input bool        sbShowBox  = true;        // Draw the SB window range box
input int         sbBoxKeep  = 2;           // SB window boxes kept
input bool        sbShowPlan = true;        // Show the locked SB FVG (CE) + the planned exit levels
input bool        sbDynAlert = true;        // Dynamic alert() messages for every SB event

input group "Scheduled volatility windows (NY time) — NOT a live calendar"
input bool        useNews     = true;       // Block entries inside the windows
input bool        paintNews   = true;       // Shade the windows
input bool        newsAllowSb = true;       // Allow the NY AM Silver Bullet window to trade through window #2
input string      news1Ses    = "0825-0845:23456"; // Window #1 — 08:30 US data slot
input string      news2Ses    = "0955-1010:23456"; // Window #2 — 10:00 US data slot
input string      news3Ses    = "1355-1435:4";     // Window #3 — 14:00 FOMC slot (Wed)

input group "Signal quality / state machine"
input ENUM_TIERM  tierMode    = TM_A;       // Show signal tiers
input int         minScore    = 50;         // Min alignment score (0 = off)
input int         masterCd    = 15;         // Global same-direction cooldown (bars, 0 = off)
input bool        useRegime   = true;       // Suppress entries in CHOP regime
input int         liqWait     = 20;         // Machine: bars from sweep to POI tap
input int         poiWait     = 15;         // Machine: bars from POI tap to shift
input int         retWait     = 20;         // Machine: bars from shift to entry
input int         armGrace    = 3;          // Machine: bars after the sweep a setup may still arm
input ENUM_SHIFT  shiftSrc    = SH_EXT;     // Machine: what counts as the SHIFT
input ENUM_POISRC poiSrc      = PS_ZONE;    // Machine: what counts as the POI TAP
input bool        armNeedHtf  = true;       // Machine: do not arm against the HTF bias
input bool        oneDir      = true;       // One direction at a time (machine · engines · traps)
input bool        fastShift   = true;       // Machine: a displaced shift while the sweep is in play skips the POI stage
input ENUM_MCENT  mcEntryMode = MC_CEPREF;  // Machine (non-SB) entry rule
input bool        mcFvgDisp   = true;       // Machine: the retest FVG must be cut by a displacement candle
input bool        mcDispShift = true;       // Machine: a displaced internal CHoCH / CISD that leaves an FVG is a SHIFT
input bool        mcStrictCnf = true;       // Machine: the confirmation candle must close past the anchor CE
input bool        mcReqPD     = true;       // Machine: entries must be on the correct side of the dealing range
input bool        mcPdWaive   = false;      // … waived when HTF bias and external structure both agree

input group "Risk / TP / SL"
input bool        showTrade  = true;        // Show entry / SL / TP of last signal
input ENUM_TPMODE tpMode     = TP_LIQ;      // TP3 mode
input double      rrMult     = 2.0;         // TP2 R multiple
input double      maxRiskAtr = 1.5;         // Max risk (ATR ×, 0 = off)
input ENUM_RISKM  riskMode   = RM_REJ;      // When the structural stop is wider than the cap
input bool        stopTier   = true;        // Stop: fall back to the anchor stop when the sweep-wick stop breaks the risk cap
input double      minRR      = 1.5;         // Min RR to TP2 (0 = off)
input double      costTicks  = 0;           // Round-trip cost (ticks: commission, + spread if Spread = 0)
input double      spreadIn   = 0;           // Spread (ticks, 0 = off) — bid chart, fills/stops tested at ask
input double      riskMoney  = 0;           // Risk per trade (account currency, 0 = off) → ≈ lots on the entry label
input int         tp1Pct     = 50;          // Close % at TP1 (label only)
input double      slipGuard  = 0.5;         // Max distance close → plan entry (ATR ×, 0 = off)
input int         maxTrdBars = 80;          // Tracked trade max life (bars, 0 = off)
input bool        nonSbTp3   = false;       // Non-SB trades: keep a runner to TP3

input group "Volume confirmation (optional)"
input bool        useVol  = false;          // Require relative volume on displacement
input int         volLen  = 20;             // Volume SMA length
input double      volMult = 1.3;            // Displacement volume ≥ SMA ×
input bool        volQual = true;           // Raid candle with volume earns +1 sweep grade

input group "ADR exhaustion (intraday)"
input bool        useAdr = true;            // Penalise chasing an exhausted daily range
input int         adrLen = 10;              // ADR length (days)
input double      adrMax = 1.2;             // Exhausted when day range ≥ ADR ×

input group "Risk governance (per day)"
input bool        useGov     = true;        // Enforce a daily trade / loss limit
input int         maxTrdDay  = 4;           // Max signals per day (0 = off)
input int         maxLossDay = 2;           // Stop after N losing trades (0 = off)
input string      tradeDays  = "23456";     // Trade days (digits, 1=Sun … 7=Sat, NY time; 23456 = Mon–Fri)

input group "Dashboard / Debug"
input bool        showDash   = true;        // Show context dashboard
input bool        showDbg    = false;       // Debug mode (engine state table)
input bool        jrnlEnable = true;        // Journal alert() line on every signal

input group "UI / style"
input ENUM_SZ     uiSizeOpt  = SZ_NORMAL;   // Signal label size
input int         uiTrans    = 25;          // Signal label transparency
input bool        uiMicroBig = true;        // Readable micro-marks
input ENUM_SZ     uiDrawOpt  = SZ_NORMAL;   // Box / level text size
input ENUM_SZ     uiDashOpt  = SZ_NORMAL;   // Dashboard / debug text size
input bool        focusMode  = true;        // Focus mode — draw only what is near price
input double      focusAtr   = 4.0;         // Focus distance (ATR ×)

input group "Advanced tuning (defaults = v3.2 behaviour · ignored unless the profile is Manual)"
input double      nearLvlIn   = 0.25;       // 'At the level' tolerance (ATR ×)
input double      slPadIn     = 0.25;       // Stop padding beyond structure (ATR ×)
input double      sweepCtxIn  = 3.0;        // Sweep stays in play within (ATR ×)
input double      poiNearIn   = 1.5;        // 'Near the POI' distance (ATR ×)
input int         trigLookIn  = 10;         // Shift / CISD stays a live trigger (bars)
input double      atrCapIn    = 1.5;        // ATR shock cap (× 50-bar average ATR, 0 = off)
input int         REGIME_LOOK = 40;         // Regime: external-event memory (bars)
input double      chopRngIn   = 6.0;        // CHOP: external range narrower than (ATR ×)

input group "◬ Liquidity Trap Engine"
input bool        ltEnable  = true;         // Enable Liquidity Trap Engine
input bool        ltCtxGate = true;         // Apply session / volatility / regime / HTF gates to trap signals
input ENUM_LTMIN  ltMinCls  = LTM_HIGH;     // Minimum trap confidence to signal
input bool        ltVeto    = true;         // Trap veto — mute opposing engine signals while a trap waits
input bool        ltP1 = true;              // LT-1 Compression → Expansion breakout (long)
input bool        ltP2 = true;              // LT-2 Expansion + Compression trap (short)
input bool        ltP3 = true;              // LT-3 Lower-wick liquidity trap (short)
input bool        ltP4 = true;              // LT-4 Shadow-high liquidity (long)
input bool        ltP5 = true;              // LT-5 Weak breakout trap (short)
input bool        ltP6 = true;              // LT-6 Structural breakout trap (short)
input bool        ltP7 = true;              // LT-7 Supply rejection breakout (short)

input group "◬ LT — sensitivity"
input double      ltWickAtr    = 0.4;       // Wick sensitivity (ATR ×)
input double      ltWickRatio  = 1.5;       // Significant wick ≥ body ×
input int         ltWickMin    = 3;         // Wick cluster — min candles
input int         ltWickWin    = 8;         // Wick cluster — window (bars)
input double      ltClusterTol = 0.6;       // Wick cluster — level tolerance (ATR ×)
input int         ltCmpLen     = 5;         // Compression window (bars)
input double      ltCmpSens    = 0.5;       // Compression — avg body ≤ ATR ×
input double      ltCmpRngAtr  = 2.5;       // Compression — window range ≤ ATR ×
input double      ltExpSens    = 1.2;       // Expansion body ≥ ATR × (genuine break)
input double      ltBrkStr     = 0.8;       // Weak breakout body < ATR ×
input double      ltNearAtr    = 2.0;       // Compression near level (ATR ×)
input double      ltRetestAtr  = 0.5;       // Retest distance from level (ATR ×)
input int         ltDispLook   = 20;        // Seller-displacement memory (bars)
input int         ltPoolLook   = 25;        // Liquidity pool stays valid (bars)
input int         ltWaitBars   = 25;        // Setup expiry — bars to confirm
input double      ltInvAtr     = 1.0;       // Invalidation beyond level (ATR ×)
input int         ltCd         = 10;        // Cooldown after a trap signal (bars)

input group "◬ LT — confirmation"
input bool        ltReqRetest = true;       // Require retest (long: level retap · short: close back below)
input bool        ltReqSweep  = false;      // Require sweep in play
input bool        ltReqMtf    = false;      // Require HTF bias agreement

input group "◬ LT — score / display"
input int         ltScoreMed   = 50;        // MEDIUM score ≥
input int         ltScoreHigh  = 70;        // HIGH score ≥
input int         ltScoreVHigh = 85;        // VERY HIGH score ≥
input bool        ltShowSig    = true;      // Show trap signal labels
input bool        ltShowMarks  = true;      // Show retest / failed-break marks
input bool        ltDynAlert   = true;      // Dynamic alert() messages (pattern + score + level)

//+------------------------------------------------------------------+
//| na helpers. double na = NaN (compares false like Pine na).       |
//| int na = NAI (INT_MIN) — always guarded before arithmetic.       |
//+------------------------------------------------------------------+
union UDL { double d; long l; };
double NaNv() { UDL u; u.l = 0x7FF8000000000000; return u.d; }
#define NA  NaNv()
#define NAI INT_MIN
bool   isna(const double x)               { return !MathIsValidNumber(x); }
bool   isnai(const int x)                 { return x == NAI; }
double nz(const double x, const double y) { return isna(x) ? y : x; }
int    nzi(const int x, const int y)      { return x == NAI ? y : x; }
// Pine math.min / math.max propagate na
double PMin(const double a, const double b) { return (isna(a) || isna(b)) ? NA : MathMin(a, b); }
double PMax(const double a, const double b) { return (isna(a) || isna(b)) ? NA : MathMax(a, b); }
string fmtPx(const double x)              { return isna(x) ? "NaN" : DoubleToString(x, _Digits); }
string fmtN(const double x, const int d)  { return isna(x) ? "NaN" : DoubleToString(x, d); }
string I2S(const int x)                   { return x == NAI ? "NaN" : IntegerToString(x); }
// Pine str.tostring(x, "#.##") style: up to d decimals, trailing zeros removed
string fmtG(const double x, const int d)
{
   if(isna(x)) return "NaN";
   string s = DoubleToString(x, d);
   if(StringFind(s, ".") >= 0)
   {
      int n = StringLen(s);
      while(n > 0 && StringGetCharacter(s, n - 1) == '0') n--;
      if(n > 0 && StringGetCharacter(s, n - 1) == '.') n--;
      s = StringSubstr(s, 0, n);
   }
   return s;
}
bool Contains(const string s, const string p) { return StringFind(s, p) >= 0; }

//+------------------------------------------------------------------+
//| per-bar series (oldest first). g_bi = Pine bar_index             |
//+------------------------------------------------------------------+
double   gO[], gH[], gL[], gC[], gV[], gATRraw[], gATR[];
datetime gT[];
int      g_bi = 0, g_last = 0, g_lastDone = -1;
bool     g_live = false;
bool     g_intra = true;          // timeframe.isintraday

double O(const int k)  { int j = g_bi - k; if(j < 0) j = 0; return gO[j]; }
double H(const int k)  { int j = g_bi - k; if(j < 0) j = 0; return gH[j]; }
double L(const int k)  { int j = g_bi - k; if(j < 0) j = 0; return gL[j]; }
double C(const int k)  { int j = g_bi - k; if(j < 0) j = 0; return gC[j]; }
double V(const int k)  { int j = g_bi - k; if(j < 0) j = 0; return gV[j]; }
double A(const int k)  { int j = g_bi - k; if(j < 0) j = 0; return gATR[j]; }
double Body(const int k)  { return MathAbs(C(k) - O(k)); }
double Rng(const int k)   { return H(k) - L(k); }
bool   Bull(const int k)  { return C(k) > O(k); }
bool   Bear(const int k)  { return C(k) < O(k); }
double UpW(const int k)   { return H(k) - MathMax(O(k), C(k)); }
double DnW(const int k)   { return MathMin(O(k), C(k)) - L(k); }

// ta.highest(high, len)[off] / ta.lowest(low, len)[off]
double HH(const int len, const int off) { double v = -DBL_MAX; for(int k = off; k < off + len; k++) v = MathMax(v, H(k)); return v; }
double LL(const int len, const int off) { double v = DBL_MAX;  for(int k = off; k < off + len; k++) v = MathMin(v, L(k)); return v; }
// offset (>= 0, bars back from `off`) of the extreme — most recent on ties
int HHoff(const int len, const int off) { double v = -DBL_MAX; int b = off; for(int k = off; k < off + len; k++) if(H(k) > v) { v = H(k); b = k; } return b; }
int LLoff(const int len, const int off) { double v = DBL_MAX;  int b = off; for(int k = off; k < off + len; k++) if(L(k) < v) { v = L(k); b = k; } return b; }

// ta.pivothigh(high, n, n) at the current bar: centre n bars back; left side may tie, right side strict
double PivH(const int n)
{
   int c = g_bi - n;
   if(c - n < 0) return NA;
   double v = gH[c];
   for(int k = 1; k <= n; k++) { if(gH[c - k] > v) return NA; if(gH[c + k] >= v) return NA; }
   return v;
}
double PivL(const int n)
{
   int c = g_bi - n;
   if(c - n < 0) return NA;
   double v = gL[c];
   for(int k = 1; k <= n; k++) { if(gL[c - k] < v) return NA; if(gL[c + k] <= v) return NA; }
   return v;
}

//+------------------------------------------------------------------+
//| array helpers                                                    |
//+------------------------------------------------------------------+
template<typename T>
void APush(T &a[], const T &v) { int n = ArraySize(a); ArrayResize(a, n + 1, 64); a[n] = v; }
template<typename T>
void ARemove(T &a[], const int idx)
{
   int n = ArraySize(a);
   if(idx < 0 || idx >= n) return;
   for(int k = idx; k < n - 1; k++) a[k] = a[k + 1];
   ArrayResize(a, n - 1, 64);
}
void SPush(string &a[], const string v) { int n = ArraySize(a); ArrayResize(a, n + 1, 64); a[n] = v; }
void SRemove(string &a[], const int idx)
{
   int n = ArraySize(a);
   if(idx < 0 || idx >= n) return;
   for(int k = idx; k < n - 1; k++) a[k] = a[k + 1];
   ArrayResize(a, n - 1, 64);
}

//+------------------------------------------------------------------+
//| colours (Pine constants) + transparency blend for objects        |
//+------------------------------------------------------------------+
#define COL_BULL   C'8,153,129'
#define COL_BEAR   C'242,54,69'
#define CL_GRAY    C'120,123,134'
#define CL_SILVER  C'178,181,190'
#define CL_TEAL    C'0,137,123'
#define CL_PURPLE  C'156,39,176'
#define CL_BLUE    C'33,150,243'
#define CL_ORANGE  C'255,152,0'
#define CL_RED     C'255,82,82'
#define CL_NAVY    C'49,27,146'
#define CL_WHITE   C'255,255,255'

color g_bgCol = clrBlack;
color g_fgCol = clrWhite;
color Col(const color c, const int transp)
{
   double t = MathMax(0, MathMin(100, transp)) / 100.0;
   int r1 = (int)(c & 0xFF), g1 = (int)((c >> 8) & 0xFF), b1 = (int)((c >> 16) & 0xFF);
   int r2 = (int)(g_bgCol & 0xFF), g2 = (int)((g_bgCol >> 8) & 0xFF), b2 = (int)((g_bgCol >> 16) & 0xFF);
   int r = (int)MathRound(r1 * (1 - t) + r2 * t);
   int g = (int)MathRound(g1 * (1 - t) + g2 * t);
   int b = (int)MathRound(b1 * (1 - t) + b2 * t);
   return (color)(r | (g << 8) | (b << 16));
}
uchar AlphaOf(const int transp) { return (uchar)MathRound(255.0 * (100 - MathMax(0, MathMin(100, transp))) / 100.0); }

// Pine size.tiny / small / normal / large -> font points
int FsOf(const ENUM_SZ s) { return s == SZ_TINY ? 7 : s == SZ_SMALL ? 8 : s == SZ_LARGE ? 12 : 9; }
int drawSize = 9, sigSize = 9, dashSize = 9, mkSize = 8, tinySize = 7;

//+------------------------------------------------------------------+
//| chart objects                                                    |
//+------------------------------------------------------------------+
#define PFX "LQ386_"
long g_objN = 0;
string NewName() { g_objN++; return PFX + IntegerToString(g_objN); }

datetime X2T(int x)
{
   if(x < 0) x = 0;
   if(x <= g_last) return gT[x];
   return gT[g_last] + (datetime)((long)(x - g_last) * PeriodSeconds());
}

// ---- lines (Pine line.new). Oldest beyond max_lines_count is deleted, like Pine's GC
string g_lineQ[];
void LineGc()
{
   while(ArraySize(g_lineQ) > i_maxLines) { ObjectDelete(0, g_lineQ[0]); SRemove(g_lineQ, 0); }
}
string LineNew(const int x1, const double y1, const int x2, const double y2, const color c, const ENUM_LINE_STYLE sty, const int w, const bool ray)
{
   if(isna(y1) || isna(y2)) return "";
   string n = NewName();
   if(!ObjectCreate(0, n, OBJ_TREND, 0, X2T(x1), y1, X2T(x2), y2)) return "";
   ObjectSetInteger(0, n, OBJPROP_COLOR, c);
   ObjectSetInteger(0, n, OBJPROP_STYLE, sty);
   ObjectSetInteger(0, n, OBJPROP_WIDTH, w);
   ObjectSetInteger(0, n, OBJPROP_RAY_RIGHT, ray);
   ObjectSetInteger(0, n, OBJPROP_RAY_LEFT, false);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, n, OBJPROP_BACK, false);
   SPush(g_lineQ, n);
   LineGc();
   return n;
}
void LineDel(const string n)
{
   if(n == "") return;
   ObjectDelete(0, n);
   for(int k = ArraySize(g_lineQ) - 1; k >= 0; k--) if(g_lineQ[k] == n) { SRemove(g_lineQ, k); break; }
}
void LineSetX2(const string n, const int x)                { if(n != "") ObjectSetInteger(0, n, OBJPROP_TIME, 1, X2T(x)); }
void LineSetStyle(const string n, const ENUM_LINE_STYLE s) { if(n != "") ObjectSetInteger(0, n, OBJPROP_STYLE, s); }
void LineSetRay(const string n, const bool r)              { if(n != "") ObjectSetInteger(0, n, OBJPROP_RAY_RIGHT, r); }
// a line that ends at x2 has to stop at x2: a trend object with a ray to the right is replaced by a segment
void LineEndAt(const string n, const int x)
{
   if(n == "") return;
   double y1 = ObjectGetDouble(0, n, OBJPROP_PRICE, 0), y2 = ObjectGetDouble(0, n, OBJPROP_PRICE, 1);
   datetime t1 = (datetime)ObjectGetInteger(0, n, OBJPROP_TIME, 0), t2 = (datetime)ObjectGetInteger(0, n, OBJPROP_TIME, 1);
   datetime tx = X2T(x);
   if(t2 != t1 && tx != t2) y2 = y1 + (y2 - y1) * (double)(tx - t1) / (double)(t2 - t1);    // keep the slope
   ObjectSetInteger(0, n, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, n, OBJPROP_TIME, 1, tx);
   ObjectSetDouble(0, n, OBJPROP_PRICE, 1, y2);
}

// ---- boxes: fill on the canvas layer (real alpha, no XOR) + border rectangle "<n>b" + text "<n>t"
#define HA_LEFT   0
#define HA_CENTER 1
#define HA_RIGHT  2
#define VA_TOP    0
#define VA_CENTER 1
#define VA_BOTTOM 2
struct BoxRec { string n; datetime t1, t2; double top, bot; color c; int tr; int ha, va; bool hasTxt; };
BoxRec g_boxes[];
int BoxFind(const string n)
{
   for(int k = ArraySize(g_boxes) - 1; k >= 0; k--) if(g_boxes[k].n == n) return k;
   return -1;
}
void BoxTextPlace(const int k)
{
   if(!g_boxes[k].hasTxt) return;
   string t = g_boxes[k].n + "t";
   datetime tx = g_boxes[k].ha == HA_LEFT ? g_boxes[k].t1 : g_boxes[k].ha == HA_RIGHT ? g_boxes[k].t2 : (datetime)((g_boxes[k].t1 + g_boxes[k].t2) / 2);
   double   py = g_boxes[k].va == VA_TOP ? g_boxes[k].top : g_boxes[k].va == VA_BOTTOM ? g_boxes[k].bot : (g_boxes[k].top + g_boxes[k].bot) / 2;
   ENUM_ANCHOR_POINT a;
   if(g_boxes[k].ha == HA_RIGHT)     a = g_boxes[k].va == VA_TOP ? ANCHOR_RIGHT_UPPER : g_boxes[k].va == VA_BOTTOM ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT;
   else if(g_boxes[k].ha == HA_LEFT) a = g_boxes[k].va == VA_TOP ? ANCHOR_LEFT_UPPER : g_boxes[k].va == VA_BOTTOM ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT;
   else                              a = g_boxes[k].va == VA_TOP ? ANCHOR_UPPER : g_boxes[k].va == VA_BOTTOM ? ANCHOR_LOWER : ANCHOR_CENTER;
   ObjectSetInteger(0, t, OBJPROP_TIME, 0, tx);
   ObjectSetDouble(0, t, OBJPROP_PRICE, 0, py);
   ObjectSetInteger(0, t, OBJPROP_ANCHOR, a);
}
// bdCol = already blended border colour (clrNONE = no border)
string BoxNew(const int x1, const double top, const int x2, const double bot, const color bdCol, const ENUM_LINE_STYLE bdSty,
              const color bg, const int bgTr, const string txt, const color txtCol, const int fs, const int ha, const int va)
{
   if(isna(top) || isna(bot)) return "";
   string n = NewName();
   BoxRec r; r.n = n; r.t1 = X2T(x1); r.t2 = X2T(x2); r.top = MathMax(top, bot); r.bot = MathMin(top, bot); r.c = bg; r.tr = bgTr;
   r.ha = ha; r.va = va; r.hasTxt = true;
   string b = n + "b";
   ObjectCreate(0, b, OBJ_RECTANGLE, 0, r.t1, r.top, r.t2, r.bot);
   ObjectSetInteger(0, b, OBJPROP_COLOR, bdCol);
   ObjectSetInteger(0, b, OBJPROP_STYLE, bdSty);
   ObjectSetInteger(0, b, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, b, OBJPROP_FILL, false);
   ObjectSetInteger(0, b, OBJPROP_BACK, false);
   ObjectSetInteger(0, b, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, b, OBJPROP_HIDDEN, true);
   if(bdCol == clrNONE) ObjectSetInteger(0, b, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);
   string t = n + "t";
   ObjectCreate(0, t, OBJ_TEXT, 0, r.t2, r.top);
   ObjectSetString(0, t, OBJPROP_TEXT, txt == "" ? " " : txt);
   ObjectSetString(0, t, OBJPROP_FONT, i_font);
   ObjectSetInteger(0, t, OBJPROP_FONTSIZE, fs);
   ObjectSetInteger(0, t, OBJPROP_COLOR, txtCol);
   ObjectSetInteger(0, t, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, t, OBJPROP_HIDDEN, true);
   int k = ArraySize(g_boxes);
   ArrayResize(g_boxes, k + 1, 64);
   g_boxes[k] = r;
   BoxTextPlace(k);
   return n;
}
void BoxDel(const string n)
{
   if(n == "") return;
   int k = BoxFind(n);
   if(k >= 0) ARemove(g_boxes, k);
   ObjectDelete(0, n + "t");
   ObjectDelete(0, n + "b");
}
void BoxSetRight(const string n, const int x)
{
   if(n == "") return;
   int k = BoxFind(n);
   if(k < 0) return;
   g_boxes[k].t2 = X2T(x);
   ObjectSetInteger(0, n + "b", OBJPROP_TIME, 1, g_boxes[k].t2);
   BoxTextPlace(k);
}
void BoxSetTopBot(const string n, const double top, const double bot)
{
   if(n == "") return;
   int k = BoxFind(n);
   if(k < 0) return;
   g_boxes[k].top = top; g_boxes[k].bot = bot;
   ObjectSetDouble(0, n + "b", OBJPROP_PRICE, 0, top);
   ObjectSetDouble(0, n + "b", OBJPROP_PRICE, 1, bot);
   BoxTextPlace(k);
}
void BoxSetBg(const string n, const color c, const int tr)
{
   if(n == "") return;
   int k = BoxFind(n);
   if(k >= 0) { g_boxes[k].c = c; g_boxes[k].tr = tr; }
}
void BoxSetBorder(const string n, const color bdCol)
{
   if(n == "") return;
   ObjectSetInteger(0, n + "b", OBJPROP_COLOR, bdCol);
   ObjectSetInteger(0, n + "b", OBJPROP_TIMEFRAMES, bdCol == clrNONE ? OBJ_NO_PERIODS : OBJ_ALL_PERIODS);
}
void BoxSetText(const string n, const string s)     { if(n != "") ObjectSetString(0, n + "t", OBJPROP_TEXT, s == "" ? " " : s); }
void BoxSetTextCol(const string n, const color c)   { if(n != "") ObjectSetInteger(0, n + "t", OBJPROP_COLOR, c); }
void BoxSetTextVa(const string n, const int va)
{
   if(n == "") return;
   int k = BoxFind(n);
   if(k >= 0) { g_boxes[k].va = va; BoxTextPlace(k); }
}
void BoxShowText(const string n, const bool on)
{
   if(n != "") ObjectSetInteger(0, n + "t", OBJPROP_TIMEFRAMES, on ? OBJ_ALL_PERIODS : OBJ_NO_PERIODS);
}

// ---- marks (Pine plotchar): one Unicode text object above / below the bar
void Mark(const bool below, const string ch, const color c, const int fs)
{
   string n = NewName();
   double y = below ? L(0) : H(0);
   if(!ObjectCreate(0, n, OBJ_TEXT, 0, gT[g_bi], y)) return;
   ObjectSetString(0, n, OBJPROP_TEXT, ch);
   ObjectSetString(0, n, OBJPROP_FONT, i_symFont);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, fs);
   ObjectSetInteger(0, n, OBJPROP_COLOR, c);
   ObjectSetInteger(0, n, OBJPROP_ANCHOR, below ? ANCHOR_UPPER : ANCHOR_LOWER);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
}

// ---- labels (Pine label.new): filled pill = one OBJ_EDIT per text row, placed in pixels on every redraw
#define LM_UP    0     // label.style_label_up    : box under the point (yloc.belowbar)
#define LM_DOWN  1     // label.style_label_down  : box over the point  (yloc.abovebar)
#define LM_LEFT  2     // label.style_label_left  : box to the right of the point
#define LM_RIGHT 3     // label.style_label_right : box to the left of the point
struct LabelRec { string n; datetime t; double y; int mode; int rows; int w; int h; };
LabelRec g_lbls[];
int g_dashW = 0, g_dashH = 0, g_dbgW = 0, g_dbgH = 0;

int Split(const string s, string &parts[])
{
   int n = StringSplit(s, '\n', parts);
   if(n <= 0) { ArrayResize(parts, 1); parts[0] = s; n = 1; }
   return n;
}
void LblRowObj(const string n, const string s, const int fs, const color bg, const color tc, const int w, const int h)
{
   ObjectCreate(0, n, OBJ_EDIT, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_READONLY, true);
   ObjectSetInteger(0, n, OBJPROP_ALIGN, ALIGN_CENTER);
   ObjectSetString(0, n, OBJPROP_FONT, i_font);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, fs);
   ObjectSetInteger(0, n, OBJPROP_COLOR, tc);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_BORDER_COLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetString(0, n, OBJPROP_TEXT, s);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, n, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);     // shown by LblPlace
}
void LblDel(const string n)
{
   if(n == "") return;
   for(int k = ArraySize(g_lbls) - 1; k >= 0; k--)
      if(g_lbls[k].n == n)
      {
         for(int r = 0; r < g_lbls[k].rows; r++) ObjectDelete(0, n + "_" + IntegerToString(r));
         ARemove(g_lbls, k);
         return;
      }
}
// x = bar index of the anchor, y = price. bg = already blended fill colour
string LblNew(const int x, const double y, const string s, const int mode, const color bg, const color tc, const int fs)
{
   if(isna(y)) return "";
   string n = NewName();
   string parts[];
   int rows = Split(s, parts);
   TextSetFont(i_font, -fs * 10);
   uint mw = 0, th = 0;
   for(int r = 0; r < rows; r++) { uint tw = 0, h1 = 0; TextGetSize(parts[r] == "" ? " " : parts[r], tw, h1); mw = MathMax(mw, tw); th = MathMax(th, h1); }
   int w = (int)mw + 12, h = (int)th + 4;
   for(int r = 0; r < rows; r++) LblRowObj(n + "_" + IntegerToString(r), parts[r], fs, bg, tc, w, h);
   LabelRec rec; rec.n = n; rec.t = X2T(x); rec.y = y; rec.mode = mode; rec.rows = rows; rec.w = w; rec.h = h;
   APush(g_lbls, rec);
   while(ArraySize(g_lbls) > i_maxLabels)
   {
      for(int r = 0; r < g_lbls[0].rows; r++) ObjectDelete(0, g_lbls[0].n + "_" + IntegerToString(r));
      ARemove(g_lbls, 0);
   }
   return n;
}
void LblSetText(const string n, const string s)
{
   for(int k = ArraySize(g_lbls) - 1; k >= 0; k--)
      if(g_lbls[k].n == n)
      {
         if(g_lbls[k].rows != 1) return;
         int fs = (int)ObjectGetInteger(0, n + "_0", OBJPROP_FONTSIZE);
         TextSetFont(i_font, -fs * 10);
         uint tw = 0, th = 0;
         TextGetSize(s, tw, th);
         g_lbls[k].w = (int)tw + 12;
         ObjectSetString(0, n + "_0", OBJPROP_TEXT, s);
         ObjectSetInteger(0, n + "_0", OBJPROP_XSIZE, g_lbls[k].w);
         return;
      }
}
bool UnderPanel(const int lx, const int ly, const int w, const int h, const int cw, const int ch)
{
   if(showDash && g_dashW > 0 && lx + w > cw - g_dashW - 12 && ly < g_dashH + 12) return true;
   if(showDbg && g_dbgW > 0 && lx + w > cw - g_dbgW - 12 && ly + h > ch - g_dbgH - 12) return true;
   return false;
}
void LblPlace(const int k, const int cw, const int ch)
{
   int x = 0, y = 0;
   bool ok = ChartTimePriceToXY(0, 0, g_lbls[k].t, g_lbls[k].y, x, y);
   int w = g_lbls[k].w, h = g_lbls[k].h, rows = g_lbls[k].rows, gap = 4;
   int lx, ly;
   if(g_lbls[k].mode == LM_UP)        { lx = x - w / 2; ly = y + gap; }
   else if(g_lbls[k].mode == LM_DOWN) { lx = x - w / 2; ly = y - gap - rows * h; }
   else if(g_lbls[k].mode == LM_LEFT) { lx = x + gap;   ly = y - rows * h / 2; }
   else                               { lx = x - gap - w; ly = y - rows * h / 2; }
   bool vis = ok && lx + w > 0 && lx < cw && ly + rows * h > 0 && ly < ch && !UnderPanel(lx, ly, w, rows * h, cw, ch);
   for(int r = 0; r < rows; r++)
   {
      string o = g_lbls[k].n + "_" + IntegerToString(r);
      if(vis)
      {
         ObjectSetInteger(0, o, OBJPROP_XDISTANCE, lx);
         ObjectSetInteger(0, o, OBJPROP_YDISTANCE, ly + r * h);
         ObjectSetInteger(0, o, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
      }
      else ObjectSetInteger(0, o, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);
   }
}
void LblPlaceAll()
{
   int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS, 0);
   int ch = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   for(int k = 0; k < ArraySize(g_lbls); k++) LblPlace(k, cw, ch);
}
// Pine f_chip: text on a solid pill above / below the current bar
void Chip(const bool below, const string txt, const color bg, const color tc, const int fs)
{
   LblNew(g_bi, below ? L(0) : H(0), txt, below ? LM_UP : LM_DOWN, bg, tc, fs);
}

//+------------------------------------------------------------------+
//| New York clock (Pine time(..., "America/New_York"))              |
//+------------------------------------------------------------------+
int g_srvOffSec = 0;
datetime MkTime(const int y, const int mo, const int d, const int h)
{
   MqlDateTime s; s.year = y; s.mon = mo; s.day = d; s.hour = h; s.min = 0; s.sec = 0; s.day_of_week = 0; s.day_of_year = 0;
   return StructToTime(s);
}
int DowOf(const datetime t) { MqlDateTime s; TimeToStruct(t, s); return s.day_of_week; }
int NthSunday(const int y, const int mo, const int n)
{
   int dow = DowOf(MkTime(y, mo, 1, 0));
   return 1 + ((7 - dow) % 7) + 7 * (n - 1);
}
int g_dstYear = -1;
datetime g_usOn, g_usOff;
datetime NyTime(const datetime tSrv)
{
   datetime utc = tSrv - g_srvOffSec;
   MqlDateTime s; TimeToStruct(utc, s);
   if(s.year != g_dstYear)
   {
      g_dstYear = s.year;
      g_usOn  = MkTime(s.year, 3,  NthSunday(s.year, 3, 2), 7);    // 02:00 EST = 07:00 UTC
      g_usOff = MkTime(s.year, 11, NthSunday(s.year, 11, 1), 6);   // 02:00 EDT = 06:00 UTC
   }
   return utc + ((utc >= g_usOn && utc < g_usOff) ? -4 : -5) * 3600;
}
// session "HHMM-HHMM[:days]" (days 1=Sun … 7=Sat)
struct Sess { int a, b; string days; bool ok; };
Sess ParseSess(const string s)
{
   Sess r; r.a = 0; r.b = 0; r.days = ""; r.ok = false;
   if(StringLen(s) < 9) return r;
   r.a = (int)StringToInteger(StringSubstr(s, 0, 2)) * 60 + (int)StringToInteger(StringSubstr(s, 2, 2));
   r.b = (int)StringToInteger(StringSubstr(s, 5, 2)) * 60 + (int)StringToInteger(StringSubstr(s, 7, 2));
   int c = StringFind(s, ":");
   if(c > 0) r.days = StringSubstr(s, c + 1);
   r.ok = true;
   return r;
}
bool InSess(const datetime tSrv, const Sess &s)
{
   if(!s.ok || !g_intra || s.a == s.b) return false;
   datetime ny = NyTime(tSrv);
   MqlDateTime m; TimeToStruct(ny, m);
   int mn = m.hour * 60 + m.min;
   bool in = s.a < s.b ? (mn >= s.a && mn < s.b) : (mn >= s.a || mn < s.b);
   if(in && s.days != "") in = Contains(s.days, IntegerToString(m.day_of_week + 1));
   return in;
}
int NyMinute(const datetime tSrv) { MqlDateTime m; TimeToStruct(NyTime(tSrv), m); return m.hour * 60 + m.min; }
int NyDow(const datetime tSrv)    { MqlDateTime m; TimeToStruct(NyTime(tSrv), m); return m.day_of_week + 1; }

//+------------------------------------------------------------------+
//| HTF / D1 / W1 feeds (request.security [1] + lookahead_on)        |
//+------------------------------------------------------------------+
struct Feed { ENUM_TIMEFRAMES tf; MqlRates r[]; int n; };
Feed fBias, fHtf, fD1, fW1;

bool FeedLoad(Feed &f, const ENUM_TIMEFRAMES tf, const datetime from, const int warm)
{
   f.tf = tf;
   ArraySetAsSeries(f.r, false);
   int ps = PeriodSeconds(tf);
   datetime st0 = from - (datetime)((long)ps * warm);
   int got = CopyRates(_Symbol, tf, st0, TimeCurrent() + ps, f.r);
   if(got <= 0) { f.n = 0; return false; }
   f.n = got;
   return true;
}
int FeedIdx(const Feed &f, const datetime t)
{
   if(f.n <= 0 || f.r[0].time > t) return -1;
   int lo = 0, hi = f.n - 1;
   while(lo < hi)
   {
      int mid = (lo + hi + 1) / 2;
      if(f.r[mid].time <= t) lo = mid; else hi = mid - 1;
   }
   return lo;
}
// index of the last COMPLETED feed bar for a chart bar opening at t (-1 = none)
int FeedPrev(const Feed &f, const datetime t) { int k = FeedIdx(f, t); return k >= 1 ? k - 1 : -1; }
double FeedPivH(const Feed &f, const int j, const int n)
{
   int c = j - n;
   if(c - n < 0 || j >= f.n) return NA;
   double v = f.r[c].high;
   for(int k = 1; k <= n; k++) { if(f.r[c - k].high > v) return NA; if(f.r[c + k].high >= v) return NA; }
   return v;
}
double FeedPivL(const Feed &f, const int j, const int n)
{
   int c = j - n;
   if(c - n < 0 || j >= f.n) return NA;
   double v = f.r[c].low;
   for(int k = 1; k <= n; k++) { if(f.r[c - k].low < v) return NA; if(f.r[c + k].low <= v) return NA; }
   return v;
}
// Pine ta.atr on a feed (RMA seeded with the SMA)
void FeedAtr(const Feed &f, const int len, double &out[])
{
   ArrayResize(out, f.n);
   double s = 0;
   for(int j = 0; j < f.n; j++)
   {
      double tr = j == 0 ? f.r[0].high - f.r[0].low : MathMax(f.r[j].high - f.r[j].low, MathMax(MathAbs(f.r[j].high - f.r[j - 1].close), MathAbs(f.r[j].low - f.r[j - 1].close)));
      if(j < len - 1) { s += tr; out[j] = NA; continue; }
      if(j == len - 1) { s += tr; out[j] = s / len; continue; }
      out[j] = (out[j - 1] * (len - 1) + tr) / len;
   }
}
// Pine ta.ema seeded with the SMA of the first len closes
void FeedEma(const Feed &f, const int len, double &out[])
{
   ArrayResize(out, f.n);
   double a = 2.0 / (len + 1), s = 0;
   for(int j = 0; j < f.n; j++)
   {
      if(j < len - 1) { s += f.r[j].close; out[j] = NA; continue; }
      if(j == len - 1) { s += f.r[j].close; out[j] = s / len; continue; }
      out[j] = a * f.r[j].close + (1 - a) * out[j - 1];
   }
}
string TfName(const ENUM_TIMEFRAMES tf)
{
   int s = PeriodSeconds(tf);
   if(s >= 604800) return "W";
   if(s >= 86400)  return "D";
   return IntegerToString(s / 60);
}

//+------------------------------------------------------------------+
//| MODULE 7 / 9 HTF ENGINES — computed once per feed bar.           |
//| Index m = the feed bar's own state after it CLOSED; a chart bar  |
//| reads m = FeedPrev() (Pine [1] + lookahead_on).                  |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES g_biasTF = PERIOD_H1, g_htfTF = PERIOD_H1;
string g_biasName = "60", g_htfName = "60";
bool   g_htfLive = true;

// bias TF: EMA sign + HTF protected-swing structure
int    hbEma[], hbDir[];
double hbPLo[], hbPHi[];
// D1: EMA sign + ADR
int    hdEma[];
double hdAdr[];
// HTF: CRT / TBS flags + stop anchors
bool   hcCrtB[], hcCrtS[], hcTbsB[], hcTbsS[];
double hcCrtLo[], hcCrtHi[], hcTbsLo[], hcTbsHi[];
// HTF FVG POI registry snapshot (newest first; NA where empty)
struct PoiSnap { double bT[3], bB[3]; int bI[3]; double sT[3], sB[3]; int sI[3]; };
PoiSnap hpSnap[];

void HtfEmaSign(const Feed &f, int &out[])
{
   double ema[];
   FeedEma(f, biasLen, ema);
   ArrayResize(out, f.n);
   for(int j = 0; j < f.n; j++) out[j] = f.r[j].close > ema[j] ? 1 : -1;    // close > na -> false -> -1 (Pine)
}

// f_htfStruct(htfStructPiv, structDisp) on the bias TF
void HtfStructCalc(const Feed &f)
{
   ArrayResize(hbDir, f.n); ArrayResize(hbPLo, f.n); ArrayResize(hbPHi, f.n);
   double fa[];
   FeedAtr(f, atrLen, fa);
   double res = NA, sup = NA, protLo = NA, protHi = NA, legLo = NA, legHi = NA;
   bool resBrk = false, supBrk = false;
   int dir = 0;
   int piv = htfStructPiv;
   for(int j = 0; j < f.n; j++)
   {
      double fph = FeedPivH(f, j, piv), fpl = FeedPivL(f, j, piv);
      if(!isna(fph)) { res = fph; resBrk = false; }
      if(!isna(fpl)) { sup = fpl; supBrk = false; }
      double c = f.r[j].close, o = f.r[j].open, hi = f.r[j].high, lo = f.r[j].low;
      double fb = MathAbs(c - o);
      bool upBrk = !isna(res) && !resBrk && c > res;
      bool dnBrk = !isna(sup) && !supBrk && c < sup;
      if(upBrk) resBrk = true;
      if(dnBrk) supBrk = true;
      legLo = isna(legLo) ? lo : MathMin(legLo, lo);
      legHi = isna(legHi) ? hi : MathMax(legHi, hi);
      bool ev = false;
      if(!isna(fa[j]) && fb >= structDisp * fa[j])
      {
         if(dir == 1)
         {
            if(upBrk) { protLo = legLo; ev = true; }
            else if(!isna(protLo) && c < protLo) { dir = -1; protHi = legHi; protLo = NA; ev = true; }
         }
         else if(dir == -1)
         {
            if(dnBrk) { protHi = legHi; ev = true; }
            else if(!isna(protHi) && c > protHi) { dir = 1; protLo = legLo; protHi = NA; ev = true; }
         }
         else if(upBrk) { dir = 1;  protLo = legLo; ev = true; }
         else if(dnBrk) { dir = -1; protHi = legHi; ev = true; }
         if(ev) { legLo = lo; legHi = hi; }
      }
      hbDir[j] = dir; hbPLo[j] = protLo; hbPHi[j] = protHi;
   }
}

// f_crtTbsHtf() evaluated on each HTF bar m
void HtfCrtTbsCalc(const Feed &f)
{
   int n = f.n;
   ArrayResize(hcCrtB, n); ArrayResize(hcCrtS, n); ArrayResize(hcTbsB, n); ArrayResize(hcTbsS, n);
   ArrayResize(hcCrtLo, n); ArrayResize(hcCrtHi, n); ArrayResize(hcTbsLo, n); ArrayResize(hcTbsHi, n);
   double fa[];
   FeedAtr(f, atrLen, fa);
   for(int m = 0; m < n; m++)
   {
      hcCrtB[m] = false; hcCrtS[m] = false; hcTbsB[m] = false; hcTbsS[m] = false;
      hcCrtLo[m] = m >= 1 ? f.r[m - 1].low  : NA;
      hcCrtHi[m] = m >= 1 ? f.r[m - 1].high : NA;
      hcTbsLo[m] = f.r[m].low;
      hcTbsHi[m] = f.r[m].high;
      if(m < 2 || isna(fa[m])) continue;
      double c = f.r[m].close, o = f.r[m].open, hi = f.r[m].high, lo = f.r[m].low;
      double rg = hi - lo, fb = MathAbs(c - o);
      bool bull = c > o, bear = c < o;
      MqlRates r1 = f.r[m - 1], r2 = f.r[m - 2];
      bool c1big = (r2.high - r2.low) >= crtRangeAtr * fa[m];
      hcCrtB[m] = c1big && r1.low < r2.low && r1.close > r2.low && r1.close < r2.high && r2.low - r1.low >= minWickAtr * fa[m] && bull && c > r1.high && fb >= crtDispAtr * fa[m];
      hcCrtS[m] = c1big && r1.high > r2.high && r1.close < r2.high && r1.close > r2.low && r1.high - r2.high >= minWickAtr * fa[m] && bear && c < r1.low && fb >= crtDispAtr * fa[m];
      if(m - tbsLen < 0) continue;
      double tl = DBL_MAX, th = -DBL_MAX;
      int il = m - 1, ih = m - 1;
      for(int k = m - 1; k >= m - tbsLen; k--)
      {
         if(f.r[k].low < tl)  { tl = f.r[k].low;  il = k; }
         if(f.r[k].high > th) { th = f.r[k].high; ih = k; }
      }
      int loAge = m - il, hiAge = m - ih;
      bool okL = loAge >= tbsAgeMin && (tbsAgeMax == 0 || loAge <= tbsAgeMax);
      bool okH = hiAge >= tbsAgeMin && (tbsAgeMax == 0 || hiAge <= tbsAgeMax);
      hcTbsB[m] = lo < tl && c > tl && bull && okL && c >= lo + 0.5 * rg;
      hcTbsS[m] = hi > th && c < th && bear && okH && c <= hi - 0.5 * rg;
   }
}

// f_htfPoi() — three live HTF FVGs per side, freshness in separate visits
struct PoiSlot { double t, b; int br, in; bool ws; };
void HtfPoiCalc(const Feed &f)
{
   int n = f.n;
   ArrayResize(hpSnap, n);
   PoiSlot bs[], ss[];
   for(int j = 0; j < n; j++)
   {
      double c = f.r[j].close, hi = f.r[j].high, lo = f.r[j].low;
      for(int i = ArraySize(bs) - 1; i >= 0; i--)
      {
         if(j > bs[i].br)
         {
            bool inB = lo <= bs[i].t && hi >= bs[i].b;
            if(inB && !bs[i].ws) bs[i].in++;
            bs[i].ws = inB;
         }
         if(c < bs[i].b || j - bs[i].br > hPoiMaxAge || bs[i].in > hPoiMaxTouch) ARemove(bs, i);
      }
      for(int i = ArraySize(ss) - 1; i >= 0; i--)
      {
         if(j > ss[i].br)
         {
            bool inS = hi >= ss[i].b && lo <= ss[i].t;
            if(inS && !ss[i].ws) ss[i].in++;
            ss[i].ws = inS;
         }
         if(c > ss[i].t || j - ss[i].br > hPoiMaxAge || ss[i].in > hPoiMaxTouch) ARemove(ss, i);
      }
      if(j >= 2 && lo > f.r[j - 2].high)
      {
         PoiSlot p; p.t = lo; p.b = f.r[j - 2].high; p.br = j; p.in = 0; p.ws = false;
         APush(bs, p);
         if(ArraySize(bs) > 3) ARemove(bs, 0);
      }
      if(j >= 2 && hi < f.r[j - 2].low)
      {
         PoiSlot p; p.t = f.r[j - 2].low; p.b = hi; p.br = j; p.in = 0; p.ws = false;
         APush(ss, p);
         if(ArraySize(ss) > 3) ARemove(ss, 0);
      }
      int nb = ArraySize(bs), ns = ArraySize(ss);
      for(int q = 0; q < 3; q++)
      {
         hpSnap[j].bT[q] = nb > q ? bs[nb - 1 - q].t : NA;
         hpSnap[j].bB[q] = nb > q ? bs[nb - 1 - q].b : NA;
         hpSnap[j].bI[q] = nb > q ? bs[nb - 1 - q].in : NAI;
         hpSnap[j].sT[q] = ns > q ? ss[ns - 1 - q].t : NA;
         hpSnap[j].sB[q] = ns > q ? ss[ns - 1 - q].b : NA;
         hpSnap[j].sI[q] = ns > q ? ss[ns - 1 - q].in : NAI;
      }
   }
}

void HtfAdrCalc(const Feed &f)
{
   ArrayResize(hdAdr, f.n);
   for(int j = 0; j < f.n; j++)
   {
      if(j < adrLen - 1) { hdAdr[j] = NA; continue; }
      double s = 0;
      for(int k = j - adrLen + 1; k <= j; k++) s += f.r[k].high - f.r[k].low;
      hdAdr[j] = s / adrLen;
   }
}

ENUM_TIMEFRAMES TfFromSel(const int minutes) { return minutes == 5 ? PERIOD_M5 : minutes == 15 ? PERIOD_M15 : minutes == 30 ? PERIOD_M30 : minutes == 60 ? PERIOD_H1 : minutes == 240 ? PERIOD_H4 : PERIOD_D1; }
ENUM_TIMEFRAMES HtfAuto()
{
   int s = PeriodSeconds(PERIOD_CURRENT);
   if(s <= 60)    return PERIOD_M15;
   if(s <= 180)   return PERIOD_M30;
   if(s <= 300)   return PERIOD_H1;
   if(s <= 600)   return PERIOD_H2;
   if(s <= 1800)  return PERIOD_H4;
   return PERIOD_D1;
}
void ResolveTfs()
{
   // FIX-Z5: the bias TF is never below the chart TF
   int bm = biasFilter == BF_5 ? 5 : biasFilter == BF_15 ? 15 : biasFilter == BF_240 ? 240 : biasFilter == BF_D ? 1440 : 60;
   g_biasTF = TfFromSel(bm);
   if(PeriodSeconds(g_biasTF) < PeriodSeconds(PERIOD_CURRENT)) g_biasTF = (ENUM_TIMEFRAMES)Period();
   g_biasName = TfName(g_biasTF);
   g_htfTF = htfSel == HS_AUTO ? HtfAuto() : TfFromSel(htfSel == HS_15 ? 15 : htfSel == HS_30 ? 30 : htfSel == HS_60 ? 60 : htfSel == HS_240 ? 240 : 1440);
   g_htfLive = PeriodSeconds(g_htfTF) > PeriodSeconds(PERIOD_CURRENT);     // FIX-Z4
   if(!g_htfLive) g_htfTF = (ENUM_TIMEFRAMES)Period();                      // a lower HTF reads the chart's own previous bar
   g_htfName = TfName(g_htfTF);
}

//+------------------------------------------------------------------+
//| MODULE 1/2 resolved constants (symbol profile, FIX-W17)          |
//+------------------------------------------------------------------+
int    profIdx = 0;
bool   profMan = true;
int    extPiv = 12, TRIG_LOOK = 10;
double dispFactor = 1.2, minZoneAtr = 0.15, NEAR_LVL_ATR = 0.25, SL_PAD_ATR = 0.25, SWEEP_CTX_ATR = 3.0, POI_NEAR_ATR = 1.5, CHOP_RANGE_ATR = 6.0;
#define STRONG_CLOSE_PCT 0.30
#define CISD_NEUTRAL_PCT 0.10
#define IFC_LOOK         3
#define BRK_BODY_ATR     0.5
#define IB_WAIT_BARS     4
#define TRADE_BARS       15
#define DOJI_WINDOW      5
#define MAX_EQ_POOLS     8
#define OTE_1            0.62
#define OTE_2            0.79
#define SB_ARM_GRACE     5
#define SB_MEM_EXTRA     5
#define SB_BE_TP1_PCT    0.15
double g_tick = 0;                 // syminfo.mintick

void ResolveProfile()
{
   profIdx = (int)symProfile;
   profMan = profIdx == 0;
   extPiv         = profIdx == 3 ? 10 : profMan ? extPivIn : 12;
   dispFactor     = profIdx == 3 ? 1.1 : profMan ? dispFactIn : 1.2;
   minZoneAtr     = profMan ? minZoneIn : profIdx == 1 ? 0.15 : profIdx == 4 ? 0.25 : 0.20;
   NEAR_LVL_ATR   = profMan ? nearLvlIn  : profIdx == 1 ? 0.25 : profIdx == 4 ? 0.35 : 0.30;
   SL_PAD_ATR     = profMan ? slPadIn    : profIdx == 1 ? 0.25 : profIdx == 2 ? 0.35 : profIdx == 3 ? 0.30 : 0.40;
   SWEEP_CTX_ATR  = profMan ? sweepCtxIn : profIdx == 1 ? 3.0  : profIdx == 4 ? 5.0  : 4.0;
   POI_NEAR_ATR   = profMan ? poiNearIn  : profIdx == 1 ? 1.5  : profIdx == 4 ? 2.0  : 1.75;
   TRIG_LOOK      = profMan ? trigLookIn : profIdx == 3 ? 8    : profIdx == 4 ? 12   : 10;
   CHOP_RANGE_ATR = profMan ? chopRngIn  : profIdx <= 2 ? 6.0 : 7.0;
}

bool f_recent(const int b, const int look) { return b != NAI && g_bi - b <= look; }

//+------------------------------------------------------------------+
//| ENGINE STATE (Pine `var`) + per-bar series                        |
//+------------------------------------------------------------------+
// ---- MODULE 3
double atr, spr, hiA, loA, body, rng, upWick, dnWick;
bool   bullBar, bearBar, volOK, volHot, bullPin, bearPin, bullEngulf, bearEngulf, bullConfirm, bearConfirm, doji;
double relVol;
bool   cisdUp, cisdDn, ifcBull, ifcBear, zoneBullConf, zoneBearConf;
double cdBullRunOpen = NA, cdBearRunOpen = NA;
int    cdBullRunLen = 0, cdBearRunLen = 0;
bool   cdDnDone = false, cdUpDone = false;

// ---- MODULE 4
double ph, pl;
double lastRes = NA, lastSup = NA, prevPH = NA, prevPL = NA;
int    lastResBar = NAI, lastSupBar = NAI, prevPHBar = NAI, prevPLBar = NAI;
bool   resBroken = false, supBroken = false, resBosDone = false, supBosDone = false;
int    resBrkBar = NAI, supBrkBar = NAI;
double tlUpSlope = NA, tlUpPrice = NA, tlDnSlope = NA, tlDnPrice = NA;
int    tlUpBar = NAI, tlDnBar = NAI, tlUpTouch = 0, tlDnTouch = 0;
string tlUpLn = "", tlDnLn = "";
bool   tlUpWasNear = false, tlDnWasNear = false;
double eqhLvls[], eqlLvls[];
string eqhLns[], eqlLns[];
int    eqhBars[], eqlBars[];

// ---- MODULE 4B
Sess   sAsia, sLon, sNY, sSbLO, sSbAM, sSbPM, sN1, sN2, sN3;
bool   inAsia, inLon, inNY, inSbLO, inSbAM, inSbPM, inSB, inKZ, kzOK, inNews, newsOK;
bool   pAsia, pLon, pNY, pSbLO, pSbAM, pSbPM, pNews;           // previous bar
int    sbNowMin, sbWinNow, sbWinPrev, sbCtxWin, sbWinPts, sbMinQual, sbRemMin;
bool   sbOn, sbActive, sbCtx, sbEndLOEvt, sbEndAMEvt, sbEndPMEvt;
string sbWinTxt;
double sbBoxHi = NA, sbBoxLo = NA;
int    sbBoxX1 = NAI, sbBoxWin = 0;
string sbBoxes[];

// ---- MODULE 5
double sslSpentLvl = NA, bslSpentLvl = NA;
bool   sslSweep, bslSweep, eqhSwept, eqlSwept;
double sslExt, bslExt;
int    lastSslBar = NAI, lastBslBar = NAI;
double lastSslLvl = NA, lastBslLvl = NA, lastSslExt = NA, lastBslExt = NA;
int    lastSslQual = 0, lastBslQual = 0, lastSslQualRaw = 0, lastBslQualRaw = 0, lastSslKind = 0, lastBslKind = 0;
double qPoolLo, qPoolHi;
double pdh = NA, pdl = NA, pwh = NA, pwl = NA, pPdh = NA, pPdl = NA, pPwh = NA, pPwl = NA;
bool   pdhDone = false, pdlDone = false, pwhDone = false, pwlDone = false;
bool   pdhSweep, pdlSweep, pwhSweep, pwlSweep;
struct SesTrk { double hi, lo, hiLvl, loLvl; string hiLn, loLn, hiLb, loLb; bool hiSwept, loSwept; bool hiRaid, loRaid; };
SesTrk stAsia, stLon, stNY;
double asiaHiLvl, asiaLoLvl, lonHiLvl, lonLoLvl, nyHiLvl, nyLoLvl;
bool   asiaHiSw, asiaLoSw, lonHiSw, lonLoSw, nyHiSw, nyLoSw, sesHiSwept, sesLoSwept;
bool   recentSsl, recentBsl, sslInPlay, bslInPlay, brokeUp, brokeDn, dispClose, brokeUpS, brokeDnS;

// ---- MODULE 6
struct StructSt { int dir; double protLo, protHi, legLo, legHi; bool bosU, bosD, chU, chD; };
StructSt sInt, sExt;
int    msDir, extDir;
bool   bosUp, bosDn, chochUp, chochDn, eBosUp, eBosDn, eChochUp, eChochDn;
double protLowE, protHighE;
double extRes = NA, extSup = NA;
int    extResBar = NAI, extSupBar = NAI;
bool   extResBosDone = false, extSupBosDone = false, eBrokeUpS, eBrokeDnS;
bool   mssUp, mssDn;
int    lastChUpBar = NAI, lastChDnBar = NAI, lastBosUpBar = NAI, lastBosDnBar = NAI, lastMssUpBar = NAI, lastMssDnBar = NAI;
int    lastCisdUpBar = NAI, lastCisdDnBar = NAI, lastDispUpBar = NAI, lastDispDnBar = NAI;
bool   recentChUp, recentChDn, recentBosUp, recentBosDn, recentMssUp, recentMssDn, recentCisdUp, recentCisdDn;
bool   recentDispUp, recentDispDn, recentStructUp, recentStructDn;

// ---- MODULE 7
int    emaBias, bD, hsDir, htfB;
double hsProtLo, hsProtHi;
bool   biasOkL, biasOkS, armBiasL, armBiasS;

// ---- MODULE 8
int    lastEngLoBar = NAI, lastEngHiBar = NAI;
bool   recentEngLo, recentEngHi;

// ---- MODULE 9
datetime hT = 0, pHT = 0;
bool   newHtfBar, sigHCrtLong, sigHCrtShort, sigHTbsLong, sigHTbsShort;
double slHCrtLong, slHCrtShort, slHTbsLong, slHTbsShort;
double hPoiBTop, hPoiBBot, hPoiSTop, hPoiSBot;
int    hPoiBIn, hPoiSIn;
double adrVal, dayHi = NA, dayLo = NA, dayRng, adrPct, adrPosD;
bool   newDay, adrExh, adrChaseL, adrChaseS;

// ---- MODULE 10
double rngHi, rngLo, rngW, pdPos, oteBuyTop, oteBuyBot, oteSellBot, oteSellTop;
int    rngHiBar, rngLoBar;
bool   rangeOK, rangeHolds, bullRange, bearRange, inOTEbuy, inOTEsell;
double sbRngHi = NA, sbRngLo = NA, sbPdPos;
int    sbRngWin = 0;
bool   sbSetLive = false, sbRngOK, sbPdOK;
int    sbTagL = 0, sbTagS = 0;

// ---- MODULE 11
int    lastEBosUpBar = NAI, lastEBosDnBar = NAI, lastEChUpBar = NAI, lastEChDnBar = NAI;
string regime = "RANGING";
bool   instSweepL, instSweepS;
int    structDir;

// ---- MODULE 12
struct Fvg { string bx; double top, bot; int barCreated; bool isBull, partial, inverted; };
Fvg    bullFvgs[], bearFvgs[];
bool   bullFVG, bearFVG;
double ifvgSupTop, ifvgSupBot, ifvgDemTop, ifvgDemBot;
double cFvgBTop = NA, cFvgBBot = NA, cFvgSTop = NA, cFvgSBot = NA;
int    cFvgBBar = NAI, cFvgSBar = NAI;
bool   cFvgBDisp = false, cFvgSDisp = false;

// ---- MODULE 13
struct Zone { string bx; double top, bot; bool isSupply, touched, tapped50, signaled; int score, tap50Bar; bool flipped; int touchBar; string kind; int tests; bool wasIn; };
Zone   zones[];
bool   sigSDLong, sigSDShort;
double slSDLong, slSDShort;
double nbTop, nbBot, nsTop, nsBot, pNbTop = NA, pNsBot = NA;
bool   nbFresh, nsFresh, touchNextBuy, touchNextSell;
int    nbScore, nsScore;
string nbKind, nsKind;

//+------------------------------------------------------------------+
//| MODULE 3 — core series + candle anatomy + CISD + IFC              |
//+------------------------------------------------------------------+
double RelVolAt(const int k)
{
   double v = V(k);
   if(v <= 0) return NA;
   if(g_bi - k - volLen + 1 < 0) return NA;
   double s = 0;
   for(int q = k; q < k + volLen; q++) s += V(q);
   return v / MathMax(s / volLen, 1);
}
bool VolOkAt(const int k) { double rv = RelVolAt(k); return !useVol || isna(rv) || rv >= volMult; }
bool CisdNeutral(const int k) { return Rng(k) == 0 || Body(k) <= CISD_NEUTRAL_PCT * Rng(k); }
bool CisdBull(const int k)    { return Bull(k) && !CisdNeutral(k); }
bool CisdBear(const int k)    { return Bear(k) && !CisdNeutral(k); }
bool DojiAt(const int k)      { return Rng(k) > 0 && Body(k) <= dojiPct / 100.0 * Rng(k); }

void M3()
{
   atr    = gATR[g_bi];
   spr    = spreadIn * g_tick;
   hiA    = H(0) + spr;
   loA    = L(0) + spr;
   body   = Body(0);
   rng    = Rng(0);
   upWick = UpW(0);
   dnWick = DnW(0);
   bullBar = Bull(0);
   bearBar = Bear(0);
   relVol = RelVolAt(0);
   volOK  = !useVol || isna(relVol) || relVol >= volMult;
   volHot = useVol && volQual && !isna(relVol) && relVol >= volMult;
   bullPin    = rng > 0 && dnWick >= 2 * body && upWick <= body && dnWick >= minWickAtr * atr;
   bearPin    = rng > 0 && upWick >= 2 * body && dnWick <= body && upWick >= minWickAtr * atr;
   bullEngulf = bullBar && Bear(1) && C(0) >= O(1) && O(0) <= C(1) && body > Body(1);
   bearEngulf = bearBar && Bull(1) && C(0) <= O(1) && O(0) >= C(1) && body > Body(1);
   bullConfirm = bullPin || bullEngulf;
   bearConfirm = bearPin || bearEngulf;
   doji = DojiAt(0);
   // f_cisd
   bool neut = CisdNeutral(0), cB = CisdBull(0), cS = CisdBear(0);
   bool newBull = cB && !CisdBull(1), newBear = cS && !CisdBear(1);
   cdBullRunOpen = neut ? NA : newBull ? O(0) : cdBullRunOpen;
   cdBearRunOpen = neut ? NA : newBear ? O(0) : cdBearRunOpen;
   cdBullRunLen  = neut ? 0 : newBull ? 1 : cB ? cdBullRunLen + 1 : cdBullRunLen;
   cdBearRunLen  = neut ? 0 : newBear ? 1 : cS ? cdBearRunLen + 1 : cdBearRunLen;
   cdDnDone = newBull ? false : cdDnDone;
   cdUpDone = newBear ? false : cdUpDone;
   cisdDn = !isna(cdBullRunOpen) && !cdDnDone && cS && C(0) < cdBullRunOpen && cdBullRunLen >= 2 && body >= BRK_BODY_ATR * atr && C(0) <= L(0) + STRONG_CLOSE_PCT * rng;
   cisdUp = !isna(cdBearRunOpen) && !cdUpDone && cB && C(0) > cdBearRunOpen && cdBearRunLen >= 2 && body >= BRK_BODY_ATR * atr && C(0) >= H(0) - STRONG_CLOSE_PCT * rng;
   if(cisdDn) cdDnDone = true;
   if(cisdUp) cdUpDone = true;
   // IFC
   double prevMid = (H(1) + L(1)) / 2;
   double ifcPoolL = LL(IFC_LOOK, 1), ifcPoolH = HH(IFC_LOOK, 1);
   ifcBull = L(0) < ifcPoolL && ifcPoolL - L(0) >= NEAR_LVL_ATR * atr && bullBar && C(0) > prevMid && C(0) >= H(0) - STRONG_CLOSE_PCT * rng && body >= BRK_BODY_ATR * atr;
   ifcBear = H(0) > ifcPoolH && H(0) - ifcPoolH >= NEAR_LVL_ATR * atr && bearBar && C(0) < prevMid && C(0) <= L(0) + STRONG_CLOSE_PCT * rng && body >= BRK_BODY_ATR * atr;
   zoneBullConf = bullConfirm || ifcBull || (cisdAsConf && cisdUp);
   zoneBearConf = bearConfirm || ifcBear || (cisdAsConf && cisdDn);
}

//+------------------------------------------------------------------+
//| MODULE 4 — pivots + EQ pools + trendline anchors                 |
//+------------------------------------------------------------------+
void M4()
{
   ph = PivH(pivLen);
   pl = PivL(pivLen);
   if(!isna(ph))
   {
      if(!isna(prevPH) && MathAbs(ph - prevPH) <= eqTol * atr)
      {
         double lvl = MathMax(ph, prevPH);
         APush(eqhLvls, lvl);
         APush(eqhBars, g_bi);
         SPush(eqhLns, showEq ? LineNew(g_bi - pivLen, lvl, g_bi + 1, lvl, Col(COL_BEAR, 25), STYLE_DOT, 1, false) : "");
         if(ArraySize(eqhLvls) > MAX_EQ_POOLS)
         {
            LineDel(eqhLns[0]);
            SRemove(eqhLns, 0); ARemove(eqhLvls, 0); ARemove(eqhBars, 0);
         }
      }
      if(!isna(prevPH) && !isnai(prevPHBar) && ph < prevPH && (isna(tlDnSlope) || tlDnTouch == 0))
      {
         LineDel(tlDnLn);
         tlDnLn    = "";
         tlDnSlope = (ph - prevPH) / (double)(g_bi - pivLen - prevPHBar);
         tlDnPrice = ph;
         tlDnBar   = g_bi - pivLen;
         tlDnTouch = 0;
         if(showTL) tlDnLn = LineNew(prevPHBar, prevPH, g_bi - pivLen, ph, Col(COL_BEAR, 30), STYLE_DOT, 1, true);
      }
      prevPH = ph; prevPHBar = g_bi - pivLen;
      lastRes = ph; lastResBar = g_bi - pivLen;
      resBroken = false; resBosDone = false;
   }
   if(!isna(pl))
   {
      if(!isna(prevPL) && MathAbs(pl - prevPL) <= eqTol * atr)
      {
         double lvl = MathMin(pl, prevPL);
         APush(eqlLvls, lvl);
         APush(eqlBars, g_bi);
         SPush(eqlLns, showEq ? LineNew(g_bi - pivLen, lvl, g_bi + 1, lvl, Col(COL_BULL, 25), STYLE_DOT, 1, false) : "");
         if(ArraySize(eqlLvls) > MAX_EQ_POOLS)
         {
            LineDel(eqlLns[0]);
            SRemove(eqlLns, 0); ARemove(eqlLvls, 0); ARemove(eqlBars, 0);
         }
      }
      if(!isna(prevPL) && !isnai(prevPLBar) && pl > prevPL && (isna(tlUpSlope) || tlUpTouch == 0))
      {
         LineDel(tlUpLn);
         tlUpLn    = "";
         tlUpSlope = (pl - prevPL) / (double)(g_bi - pivLen - prevPLBar);
         tlUpPrice = pl;
         tlUpBar   = g_bi - pivLen;
         tlUpTouch = 0;
         if(showTL) tlUpLn = LineNew(prevPLBar, prevPL, g_bi - pivLen, pl, Col(COL_BULL, 30), STYLE_DOT, 1, true);
      }
      prevPL = pl; prevPLBar = g_bi - pivLen;
      lastSup = pl; lastSupBar = g_bi - pivLen;
      supBroken = false; supBosDone = false;
   }
}

//+------------------------------------------------------------------+
//| MODULE 4B — session clock + Silver Bullet windows                |
//+------------------------------------------------------------------+
string f_sbWinTxt(const int w) { return w == 1 ? "London" : w == 2 ? "NY AM" : w == 3 ? "NY PM" : "—"; }
void M4B()
{
   datetime t0 = gT[g_bi], t1 = gT[MathMax(g_bi - 1, 0)];
   inAsia = InSess(t0, sAsia); inLon = InSess(t0, sLon); inNY = InSess(t0, sNY);
   inSbLO = InSess(t0, sSbLO); inSbAM = InSess(t0, sSbAM); inSbPM = InSess(t0, sSbPM);
   pAsia = InSess(t1, sAsia); pLon = InSess(t1, sLon); pNY = InSess(t1, sNY);
   pSbLO = InSess(t1, sSbLO); pSbAM = InSess(t1, sSbAM); pSbPM = InSess(t1, sSbPM);
   inSB = inSbLO || inSbAM || inSbPM;
   inKZ = inAsia || inLon || inNY || inSB;
   kzOK = !useKZ || !g_intra || inKZ;
   inNews = InSess(t0, sN1) || InSess(t0, sN2) || InSess(t0, sN3);
   pNews  = InSess(t1, sN1) || InSess(t1, sN2) || InSess(t1, sN3);
   sbNowMin = g_intra ? NyMinute(t0) : NAI;
   bool hasNow = sbNowMin != NAI;
   bool sbPreLO = sbUseLO && !inSbLO && sSbLO.ok && hasNow && sbNowMin < sSbLO.a && sSbLO.a - sbNowMin <= sbPreMin;
   bool sbPreAM = sbUseAM && !inSbAM && sSbAM.ok && hasNow && sbNowMin < sSbAM.a && sSbAM.a - sbNowMin <= sbPreMin;
   bool sbPrePM = sbUsePM && !inSbPM && sSbPM.ok && hasNow && sbNowMin < sSbPM.a && sSbPM.a - sbNowMin <= sbPreMin;
   sbWinNow  = (sbUseAM && inSbAM) ? 2 : (sbUseLO && inSbLO) ? 1 : (sbUsePM && inSbPM) ? 3 : 0;
   sbWinPrev = g_bi == 0 ? 0 : (sbUseAM && pSbAM) ? 2 : (sbUseLO && pSbLO) ? 1 : (sbUsePM && pSbPM) ? 3 : 0;
   sbCtxWin  = sbWinNow != 0 ? sbWinNow : sbPreAM ? 2 : sbPreLO ? 1 : sbPrePM ? 3 : 0;
   sbOn      = sbEnable && g_intra;
   sbActive  = sbOn && sbWinNow != 0;
   sbCtx     = sbOn && sbCtxWin != 0;
   newsOK = !useNews || !g_intra || !inNews || (newsAllowSb && sbActive && sbWinNow == 2);
   int endNow = sbWinNow == 1 ? sSbLO.b : sbWinNow == 2 ? sSbAM.b : sbWinNow == 3 ? sSbPM.b : NAI;
   sbRemMin = sbActive && endNow != NAI && hasNow ? MathMax(0, endNow - sbNowMin) : NAI;
   sbEndLOEvt = sbOn && !inSbLO && pSbLO;
   sbEndAMEvt = sbOn && !inSbAM && pSbAM;
   sbEndPMEvt = sbOn && !inSbPM && pSbPM;
   sbWinTxt  = f_sbWinTxt(sbCtxWin);
   sbWinPts  = sbCtxWin == 2 ? 6 : sbCtxWin == 3 ? 5 : sbCtxWin == 1 ? 4 : 0;
   sbMinQual = sbCtxWin == 1 ? sbQualLO : sbCtxWin == 2 ? sbQualAM : sbCtxWin == 3 ? sbQualPM : 4;
   // SB window range boxes
   if(sbOn && sbShowBox)
   {
      if(sbWinNow != 0)
      {
         if(sbWinPrev != sbWinNow) { sbBoxHi = H(0); sbBoxLo = L(0); sbBoxX1 = g_bi; sbBoxWin = sbWinNow; }
         else { sbBoxHi = MathMax(nz(sbBoxHi, H(0)), H(0)); sbBoxLo = MathMin(nz(sbBoxLo, L(0)), L(0)); }
      }
      else if(sbWinPrev != 0 && !isna(sbBoxHi))
      {
         SPush(sbBoxes, BoxNew(sbBoxX1, sbBoxHi, g_bi, sbBoxLo, Col(CL_TEAL, 55), STYLE_DOT, CL_TEAL, 97,
                               "SB " + f_sbWinTxt(sbBoxWin), Col(CL_TEAL, 30), tinySize, HA_CENTER, VA_TOP));
         sbBoxHi = NA; sbBoxLo = NA;
         if(ArraySize(sbBoxes) > sbBoxKeep) { BoxDel(sbBoxes[0]); SRemove(sbBoxes, 0); }
      }
   }
}

//+------------------------------------------------------------------+
//| MODULE 5 — liquidity engine                                      |
//+------------------------------------------------------------------+
int f_sweepQual(const bool isLow)
{
   double pen  = isLow ? lastSup - L(0) : H(0) - lastRes;
   bool   firm = isLow ? C(0) >= lastSup + NEAR_LVL_ATR * atr * 0.5 : C(0) <= lastRes - NEAR_LVL_ATR * atr * 0.5;
   bool   outr = isLow ? C(0) >= L(0) + (1 - STRONG_CLOSE_PCT) * rng : C(0) <= H(0) - (1 - STRONG_CLOSE_PCT) * rng;
   bool   disp = body >= BRK_BODY_ATR * atr;
   int q = 1;
   if(firm || pen >= NEAR_LVL_ATR * atr) q = 2;
   if(q == 2 && outr && disp) q = 3;
   if(volHot && q >= 2 && (outr || disp)) q = 3;
   return q;
}
int f_poolQ(const bool isLow, const double lvl)
{
   bool ok = isLow ? (C(0) >= lvl + NEAR_LVL_ATR * atr * 0.5 || lvl - L(0) >= NEAR_LVL_ATR * atr)
                   : (C(0) <= lvl - NEAR_LVL_ATR * atr * 0.5 || H(0) - lvl >= NEAR_LVL_ATR * atr);
   return ok ? (int)(isLow ? qPoolLo : qPoolHi) : 1;
}
// FIX-P0-2 stamp rule: grades merge only on the same bar
void StampSsl(const int q, const double lvl, const double ext, const int kind)
{
   lastSslQualRaw = lastSslBar == g_bi ? MathMax(lastSslQualRaw, q) : q;
   lastSslQual    = lastSslBar == g_bi ? MathMax(lastSslQual, q)    : q;
   lastSslBar = g_bi; lastSslLvl = lvl; lastSslExt = ext; lastSslKind = kind;
}
void StampBsl(const int q, const double lvl, const double ext, const int kind)
{
   lastBslQualRaw = lastBslBar == g_bi ? MathMax(lastBslQualRaw, q) : q;
   lastBslQual    = lastBslBar == g_bi ? MathMax(lastBslQual, q)    : q;
   lastBslBar = g_bi; lastBslLvl = lvl; lastBslExt = ext; lastBslKind = kind;
}

void SesTrkReset(SesTrk &s)
{
   s.hi = NA; s.lo = NA; s.hiLvl = NA; s.loLvl = NA; s.hiLn = ""; s.loLn = ""; s.hiLb = ""; s.loLb = "";
   s.hiSwept = false; s.loSwept = false; s.hiRaid = false; s.loRaid = false;
}
void SesTrack(SesTrk &s, const bool active, const bool activePrev, const string tag, const color col)
{
   if(active)
   {
      s.hi = !activePrev ? H(0) : MathMax(nz(s.hi, H(0)), H(0));
      s.lo = !activePrev ? L(0) : MathMin(nz(s.lo, L(0)), L(0));
   }
   if(!active && activePrev && !isna(s.hi))
   {
      s.hiLvl = s.hi; s.loLvl = s.lo;
      s.hiSwept = false; s.loSwept = false;
      LineDel(s.hiLn); LineDel(s.loLn); LblDel(s.hiLb); LblDel(s.loLb);
      s.hiLn = ""; s.loLn = ""; s.hiLb = ""; s.loLb = "";
      if(showSesHL)
      {
         s.hiLn = LineNew(g_bi, s.hi, g_bi + 1, s.hi, Col(col, 35), STYLE_SOLID, 1, true);
         s.loLn = LineNew(g_bi, s.lo, g_bi + 1, s.lo, Col(col, 35), STYLE_SOLID, 1, true);
         s.hiLb = LblNew(g_bi, s.hi, tag + " H", LM_LEFT, Col(col, 20), CL_WHITE, drawSize);
         s.loLb = LblNew(g_bi, s.lo, tag + " L", LM_LEFT, Col(col, 20), CL_WHITE, drawSize);
      }
   }
   if(s.hiSwept && !isna(s.hiLvl) && C(0) < s.hiLvl - atr) s.hiSwept = false;
   if(s.loSwept && !isna(s.loLvl) && C(0) > s.loLvl + atr) s.loSwept = false;
   s.hiRaid = false; s.loRaid = false;
   bool hiHit = !active && !isna(s.hiLvl) && !s.hiSwept && H(0) > s.hiLvl;
   bool loHit = !active && !isna(s.loLvl) && !s.loSwept && L(0) < s.loLvl;
   if(hiHit)
   {
      s.hiSwept = true;
      bool brk = C(0) > s.hiLvl;
      s.hiRaid = !brk;
      if(s.hiLn != "")
      {
         LineEndAt(s.hiLn, g_bi);
         LineSetStyle(s.hiLn, s.hiRaid ? STYLE_DASH : STYLE_DOT);
         LblSetText(s.hiLb, tag + (s.hiRaid ? " H raided" : " H broken"));
      }
   }
   if(loHit)
   {
      s.loSwept = true;
      bool brk = C(0) < s.loLvl;
      s.loRaid = !brk;
      if(s.loLn != "")
      {
         LineEndAt(s.loLn, g_bi);
         LineSetStyle(s.loLn, s.loRaid ? STYLE_DASH : STYLE_DOT);
         LblSetText(s.loLb, tag + (s.loRaid ? " L raided" : " L broken"));
      }
   }
}

void M5()
{
   double c = C(0), h = H(0), l = L(0);
   if(!isna(sslSpentLvl) && MathAbs(c - sslSpentLvl) > SWEEP_CTX_ATR * atr) sslSpentLvl = NA;
   if(!isna(bslSpentLvl) && MathAbs(c - bslSpentLvl) > SWEEP_CTX_ATR * atr) bslSpentLvl = NA;
   bool sslLvlFresh = isna(sslSpentLvl) || (!isna(lastSup) && MathAbs(lastSup - sslSpentLvl) > NEAR_LVL_ATR * atr);
   bool bslLvlFresh = isna(bslSpentLvl) || (!isna(lastRes) && MathAbs(lastRes - bslSpentLvl) > NEAR_LVL_ATR * atr);
   bool sslRecl = reclaimBars > 0 && supBroken && !isnai(supBrkBar) && g_bi - supBrkBar <= reclaimBars && !isna(lastSup) && c > lastSup;
   bool bslRecl = reclaimBars > 0 && resBroken && !isnai(resBrkBar) && g_bi - resBrkBar <= reclaimBars && !isna(lastRes) && c < lastRes;
   int lenL = MathMax(1, MathMin(500, g_bi - nzi(supBrkBar, g_bi) + 1));
   int lenH = MathMax(1, MathMin(500, g_bi - nzi(resBrkBar, g_bi) + 1));
   double lowSinceBrk = LL(lenL, 0), hiSinceBrk = HH(lenH, 0);
   sslExt = sslRecl ? MathMin(l, lowSinceBrk) : l;
   bslExt = bslRecl ? MathMax(h, hiSinceBrk) : h;
   sslSweep = !isna(lastSup) && ((l < lastSup && c > lastSup && !supBroken) || sslRecl) && sslLvlFresh;
   bslSweep = !isna(lastRes) && ((h > lastRes && c < lastRes && !resBroken) || bslRecl) && bslLvlFresh;

   qPoolLo = (c >= l + (1 - STRONG_CLOSE_PCT) * rng || (volHot && body >= BRK_BODY_ATR * atr)) && body >= BRK_BODY_ATR * atr ? 3 : 2;
   qPoolHi = (c <= h - (1 - STRONG_CLOSE_PCT) * rng || (volHot && body >= BRK_BODY_ATR * atr)) && body >= BRK_BODY_ATR * atr ? 3 : 2;

   if(sslSweep)
   {
      int qS = f_sweepQual(true);
      int kind = f_recent(lastSslBar, sweepLook) && lastSslKind >= 2 && MathAbs(lastSup - lastSslLvl) <= NEAR_LVL_ATR * atr ? lastSslKind : 1;
      StampSsl(qS, lastSup, sslExt, kind);
      sslSpentLvl = lastSup;
   }
   if(bslSweep)
   {
      int qB = f_sweepQual(false);
      int kind = f_recent(lastBslBar, sweepLook) && lastBslKind >= 2 && MathAbs(lastRes - lastBslLvl) <= NEAR_LVL_ATR * atr ? lastBslKind : 1;
      StampBsl(qB, lastRes, bslExt, kind);
      bslSpentLvl = lastRes;
   }
   // EQ pools
   eqhSwept = false; eqlSwept = false;
   for(int i = ArraySize(eqhLvls) - 1; i >= 0; i--)
   {
      double lvl = eqhLvls[i];
      if(h > lvl)
      {
         if(c < lvl) { eqhSwept = true; StampBsl(f_poolQ(false, lvl), lvl, h, 2); }
         LineDel(eqhLns[i]); SRemove(eqhLns, i); ARemove(eqhLvls, i); ARemove(eqhBars, i);
      }
      else if(g_bi - eqhBars[i] > eqMaxAge)
      {
         LineDel(eqhLns[i]); SRemove(eqhLns, i); ARemove(eqhLvls, i); ARemove(eqhBars, i);
      }
   }
   for(int i = ArraySize(eqlLvls) - 1; i >= 0; i--)
   {
      double lvl = eqlLvls[i];
      if(l < lvl)
      {
         if(c > lvl) { eqlSwept = true; StampSsl(f_poolQ(true, lvl), lvl, l, 2); }
         LineDel(eqlLns[i]); SRemove(eqlLns, i); ARemove(eqlLvls, i); ARemove(eqlBars, i);
      }
      else if(g_bi - eqlBars[i] > eqMaxAge)
      {
         LineDel(eqlLns[i]); SRemove(eqlLns, i); ARemove(eqlLvls, i); ARemove(eqlBars, i);
      }
   }
   // previous day / week high-low (closed D1 / W1 candle)
   int kD = FeedPrev(fD1, gT[g_bi]), kW = FeedPrev(fW1, gT[g_bi]);
   pdh = kD >= 0 ? fD1.r[kD].high : NA; pdl = kD >= 0 ? fD1.r[kD].low : NA;
   pwh = kW >= 0 ? fW1.r[kW].high : NA; pwl = kW >= 0 ? fW1.r[kW].low : NA;
   pdhDone = !isna(pdh) && pdh != nz(pPdh, pdh) ? false : pdhDone;
   pdlDone = !isna(pdl) && pdl != nz(pPdl, pdl) ? false : pdlDone;
   pwhDone = !isna(pwh) && pwh != nz(pPwh, pwh) ? false : pwhDone;
   pwlDone = !isna(pwl) && pwl != nz(pPwl, pwl) ? false : pwlDone;
   pdhSweep = !isna(pdh) && h > pdh && c < pdh && !pdhDone;
   pdlSweep = !isna(pdl) && l < pdl && c > pdl && !pdlDone;
   pwhSweep = !isna(pwh) && h > pwh && c < pwh && !pwhDone;
   pwlSweep = !isna(pwl) && l < pwl && c > pwl && !pwlDone;
   pdhDone = pdhDone || h > pdh;
   pdlDone = pdlDone || l < pdl;
   pwhDone = pwhDone || h > pwh;
   pwlDone = pwlDone || l < pwl;
   if(pdhSweep || pwhSweep) StampBsl(f_poolQ(false, pdhSweep ? pdh : pwh), pdhSweep ? pdh : pwh, h, 3);
   if(pdlSweep || pwlSweep) StampSsl(f_poolQ(true, pdlSweep ? pdl : pwl), pdlSweep ? pdl : pwl, l, 3);
   // per-session liquidity
   SesTrack(stAsia, inAsia && g_intra, pAsia && g_intra && g_bi > 0, "Asia", CL_PURPLE);
   SesTrack(stLon,  inLon && g_intra,  pLon && g_intra && g_bi > 0,  "Lon",  CL_BLUE);
   SesTrack(stNY,   inNY && g_intra,   pNY && g_intra && g_bi > 0,   "NY",   CL_ORANGE);
   asiaHiSw = stAsia.hiRaid; asiaLoSw = stAsia.loRaid; asiaHiLvl = stAsia.hiLvl; asiaLoLvl = stAsia.loLvl;
   lonHiSw  = stLon.hiRaid;  lonLoSw  = stLon.loRaid;  lonHiLvl  = stLon.hiLvl;  lonLoLvl  = stLon.loLvl;
   nyHiSw   = stNY.hiRaid;   nyLoSw   = stNY.loRaid;   nyHiLvl   = stNY.hiLvl;   nyLoLvl   = stNY.loLvl;
   sesHiSwept = asiaHiSw || lonHiSw || nyHiSw;
   sesLoSwept = asiaLoSw || lonLoSw || nyLoSw;
   if(lonLoSw || nyLoSw) StampSsl(f_poolQ(true, lonLoSw ? lonLoLvl : nyLoLvl), lonLoSw ? lonLoLvl : nyLoLvl, l, 4);
   if(lonHiSw || nyHiSw) StampBsl(f_poolQ(false, lonHiSw ? lonHiLvl : nyHiLvl), lonHiSw ? lonHiLvl : nyHiLvl, h, 4);
   if(sbCtx && sbAsiaPool)
   {
      if(asiaLoSw && !(lonLoSw || nyLoSw)) StampSsl(f_poolQ(true, asiaLoLvl), asiaLoLvl, l, 4);
      if(asiaHiSw && !(lonHiSw || nyHiSw)) StampBsl(f_poolQ(false, asiaHiLvl), asiaHiLvl, h, 4);
   }
   // V31-FIX-1 sweep in play (after every stamp)
   int sbMemLook = sbCtx ? sweepLook + SB_MEM_EXTRA : sweepLook;
   recentSsl = f_recent(lastSslBar, sbMemLook);
   recentBsl = f_recent(lastBslBar, sbMemLook);
   sslInPlay = recentSsl && !isna(lastSslLvl) && c > lastSslLvl && c - lastSslLvl <= SWEEP_CTX_ATR * atr;
   bslInPlay = recentBsl && !isna(lastBslLvl) && c < lastBslLvl && lastBslLvl - c <= SWEEP_CTX_ATR * atr;
   // once-per-level breakout latch
   brokeUp = !isna(lastRes) && !resBroken && c > lastRes;
   brokeDn = !isna(lastSup) && !supBroken && c < lastSup;
   if(brokeUp) { resBroken = true; resBrkBar = g_bi; }
   if(brokeDn) { supBroken = true; supBrkBar = g_bi; }
   dispClose = body >= structDisp * atr;
   brokeUpS = !isna(lastRes) && !resBosDone && c > lastRes;
   brokeDnS = !isna(lastSup) && !supBosDone && c < lastSup;
   if(brokeUpS && dispClose) resBosDone = true;
   if(brokeDnS && dispClose) supBosDone = true;
}

//+------------------------------------------------------------------+
//| MODULE 6 — structure (protected swing) + MSS                      |
//+------------------------------------------------------------------+
void StructReset(StructSt &s) { s.dir = 0; s.protLo = NA; s.protHi = NA; s.legLo = NA; s.legHi = NA; s.bosU = false; s.bosD = false; s.chU = false; s.chD = false; }
void StructStep(StructSt &s, const bool upBrk, const bool dnBrk)
{
   s.bosU = false; s.bosD = false; s.chU = false; s.chD = false;
   s.legLo = isna(s.legLo) ? L(0) : MathMin(s.legLo, L(0));
   s.legHi = isna(s.legHi) ? H(0) : MathMax(s.legHi, H(0));
   if(!isna(atr) && body >= structDisp * atr)
   {
      if(s.dir == 1)
      {
         if(upBrk) { s.bosU = true; s.protLo = s.legLo; }
         else if(!isna(s.protLo) && C(0) < s.protLo) { s.chD = true; s.dir = -1; s.protHi = s.legHi; s.protLo = NA; }
      }
      else if(s.dir == -1)
      {
         if(dnBrk) { s.bosD = true; s.protHi = s.legHi; }
         else if(!isna(s.protHi) && C(0) > s.protHi) { s.chU = true; s.dir = 1; s.protLo = s.legLo; s.protHi = NA; }
      }
      else if(upBrk) { s.bosU = true; s.dir = 1;  s.protLo = s.legLo; }
      else if(dnBrk) { s.bosD = true; s.dir = -1; s.protHi = s.legHi; }
      if(s.bosU || s.bosD || s.chU || s.chD) { s.legLo = L(0); s.legHi = H(0); }
   }
}
void M6()
{
   StructStep(sInt, brokeUpS, brokeDnS);
   msDir = sInt.dir; bosUp = sInt.bosU; bosDn = sInt.bosD; chochUp = sInt.chU; chochDn = sInt.chD;
   double eph = PivH(extPiv), epl = PivL(extPiv);
   if(!isna(eph)) { extRes = eph; extResBar = g_bi - extPiv; extResBosDone = false; }
   if(!isna(epl)) { extSup = epl; extSupBar = g_bi - extPiv; extSupBosDone = false; }
   eBrokeUpS = !isna(extRes) && !extResBosDone && C(0) > extRes;
   eBrokeDnS = !isna(extSup) && !extSupBosDone && C(0) < extSup;
   if(eBrokeUpS && dispClose) extResBosDone = true;
   if(eBrokeDnS && dispClose) extSupBosDone = true;
   StructStep(sExt, eBrokeUpS, eBrokeDnS);
   extDir = sExt.dir; eBosUp = sExt.bosU; eBosDn = sExt.bosD; eChochUp = sExt.chU; eChochDn = sExt.chD;
   protLowE = sExt.protLo; protHighE = sExt.protHi;
   mssUp = (eChochUp || (!mssNeedExt && chochUp)) && sslInPlay && lastSslQual >= 2;
   mssDn = (eChochDn || (!mssNeedExt && chochDn)) && bslInPlay && lastBslQual >= 2;
   if(mssUp && f_recent(lastSslBar, TRIG_LOOK)) lastSslQual = 4;
   if(mssDn && f_recent(lastBslBar, TRIG_LOOK)) lastBslQual = 4;
   // trigger memory
   if(chochUp || eChochUp) lastChUpBar = g_bi;
   if(chochDn || eChochDn) lastChDnBar = g_bi;
   if(bosUp || eBosUp) lastBosUpBar = g_bi;
   if(bosDn || eBosDn) lastBosDnBar = g_bi;
   if(mssUp) lastMssUpBar = g_bi;
   if(mssDn) lastMssDnBar = g_bi;
   if(cisdUp) lastCisdUpBar = g_bi;
   if(cisdDn) lastCisdDnBar = g_bi;
   if(bullBar && body >= dispFactor * atr) lastDispUpBar = g_bi;
   if(bearBar && body >= dispFactor * atr) lastDispDnBar = g_bi;
   recentChUp   = f_recent(lastChUpBar, TRIG_LOOK);
   recentChDn   = f_recent(lastChDnBar, TRIG_LOOK);
   recentBosUp  = f_recent(lastBosUpBar, TRIG_LOOK);
   recentBosDn  = f_recent(lastBosDnBar, TRIG_LOOK);
   recentMssUp  = f_recent(lastMssUpBar, TRIG_LOOK);
   recentMssDn  = f_recent(lastMssDnBar, TRIG_LOOK);
   recentCisdUp = f_recent(lastCisdUpBar, TRIG_LOOK);
   recentCisdDn = f_recent(lastCisdDnBar, TRIG_LOOK);
   recentDispUp = f_recent(lastDispUpBar, 3);
   recentDispDn = f_recent(lastDispDnBar, 3);
   recentStructUp = recentChUp || recentBosUp;
   recentStructDn = recentChDn || recentBosDn;
   // structure marks: MSS > CHoCH > BOS; internal marks muted
   if(showStruct)
   {
      bool up = mssUp || eChochUp || eBosUp || chochUp || bosUp;
      bool dn = mssDn || eChochDn || eBosDn || chochDn || bosDn;
      bool iUp = !(mssUp || eChochUp || eBosUp), iDn = !(mssDn || eChochDn || eBosDn);
      if(up) Chip(true, mssUp ? "MSS" : eChochUp ? "CHoCH" : eBosUp ? "BOS" : chochUp ? "iCHoCH" : "ibos",
                  iUp ? Col(CL_GRAY, 60) : Col(COL_BULL, mssUp ? 0 : 15), iUp ? COL_BULL : CL_WHITE, iUp ? tinySize : sigSize);
      if(dn) Chip(false, mssDn ? "MSS" : eChochDn ? "CHoCH" : eBosDn ? "BOS" : chochDn ? "iCHoCH" : "ibos",
                  iDn ? Col(CL_GRAY, 60) : Col(COL_BEAR, mssDn ? 0 : 15), iDn ? COL_BEAR : CL_WHITE, iDn ? tinySize : sigSize);
   }
}

//+------------------------------------------------------------------+
//| MODULE 7 — HTF bias · MODULE 8 — engineered-liquidity memory      |
//+------------------------------------------------------------------+
void M7()
{
   int kb = FeedPrev(fBias, gT[g_bi]);
   int kd = FeedPrev(fD1, gT[g_bi]);
   emaBias  = kb >= 0 ? hbEma[kb] : 0;
   bD       = kd >= 0 ? hdEma[kd] : 0;
   hsDir    = kb >= 0 ? hbDir[kb] : 0;
   hsProtLo = kb >= 0 ? hbPLo[kb] : NA;
   hsProtHi = kb >= 0 ? hbPHi[kb] : NA;
   htfB = biasMode == BM_EMA ? emaBias : biasMode == BM_STR ? (hsDir != 0 ? hsDir : emaBias) : (hsDir == 0 ? emaBias : hsDir == emaBias ? hsDir : 0);
   biasOkL = biasFilter == BF_OFF || htfB > 0 || (htfB == 0 && (neutralMode == NM_ALLOW || (neutralMode == NM_FOLLOW && extDir >= 0)));
   biasOkS = biasFilter == BF_OFF || htfB < 0 || (htfB == 0 && (neutralMode == NM_ALLOW || (neutralMode == NM_FOLLOW && extDir <= 0)));
   armBiasL = biasOkL || (htfB == 0 && neutralMode == NM_FOLLOW);
   armBiasS = biasOkS || (htfB == 0 && neutralMode == NM_FOLLOW);
   // MODULE 8
   if(eqlSwept || sesLoSwept || pdlSweep || pwlSweep) lastEngLoBar = g_bi;
   if(eqhSwept || sesHiSwept || pdhSweep || pwhSweep) lastEngHiBar = g_bi;
   recentEngLo = f_recent(lastEngLoBar, sweepLook);
   recentEngHi = f_recent(lastEngHiBar, sweepLook);
}

//+------------------------------------------------------------------+
//| MODULE 9 — HTF CRT / TBS / FVG POI + ADR                          |
//+------------------------------------------------------------------+
void PickPoi(const bool demand, const PoiSnap &s, double &pT, double &pB, int &pI)
{
   pT = NA; pB = NA; pI = NAI;
   double win = POI_NEAR_ATR * 2 * atr, c = C(0);
   for(int q = 0; q < 3; q++)
   {
      double t = demand ? s.bT[q] : s.sT[q], b = demand ? s.bB[q] : s.sB[q];
      int in = demand ? s.bI[q] : s.sI[q];
      if(isna(t) || !(demand ? b <= c : t >= c)) continue;
      if(q == 0) { pT = t; pB = b; pI = nzi(in, 0); continue; }
      bool nearQ    = MathAbs(c - (demand ? t : b)) <= win;
      bool fresherQ = nzi(in, 0) == 0 && pI != 0 && nearQ;          // pI na != 0 is false in Pine
      if(pI == NAI) fresherQ = false;
      bool sameQ    = pI != NAI && ((nzi(in, 0) == 0) == (pI == 0));
      bool nearerQ  = demand ? t > pT : b < pB;
      if(isna(pT) || fresherQ || (sameQ && nearerQ)) { pT = t; pB = b; pI = nzi(in, 0); }
   }
}
bool f_tbsAgeOk(const int age) { return age >= tbsAgeMin && (tbsAgeMax == 0 || age <= tbsAgeMax); }
void M9()
{
   int k = FeedPrev(fHtf, gT[g_bi]);
   hT = k >= 0 ? fHtf.r[k].time : 0;
   newHtfBar = g_htfLive && k >= 0 && hT != pHT;
   sigHCrtLong  = useHtfCrt && newHtfBar && hcCrtB[k];
   sigHCrtShort = useHtfCrt && newHtfBar && hcCrtS[k];
   sigHTbsLong  = useHtfCrt && newHtfBar && hcTbsB[k];
   sigHTbsShort = useHtfCrt && newHtfBar && hcTbsS[k];
   slHCrtLong  = k >= 0 ? hcCrtLo[k] - SL_PAD_ATR * atr : NA;
   slHCrtShort = k >= 0 ? hcCrtHi[k] + SL_PAD_ATR * atr : NA;
   slHTbsLong  = k >= 0 ? hcTbsLo[k] - SL_PAD_ATR * atr : NA;
   slHTbsShort = k >= 0 ? hcTbsHi[k] + SL_PAD_ATR * atr : NA;
   if(k >= 0)
   {
      PickPoi(true,  hpSnap[k], hPoiBTop, hPoiBBot, hPoiBIn);
      PickPoi(false, hpSnap[k], hPoiSTop, hPoiSBot, hPoiSIn);
   }
   else { hPoiBTop = NA; hPoiBBot = NA; hPoiBIn = NAI; hPoiSTop = NA; hPoiSBot = NA; hPoiSIn = NAI; }
   // ADR exhaustion
   int kd = FeedPrev(fD1, gT[g_bi]);
   adrVal = kd >= 0 ? hdAdr[kd] : NA;
   newDay = g_intra && g_bi > 0 && (long)gT[g_bi] / 86400 != (long)gT[g_bi - 1] / 86400;
   if(newDay || isna(dayHi)) { dayHi = H(0); dayLo = L(0); }
   else { dayHi = MathMax(dayHi, H(0)); dayLo = MathMin(dayLo, L(0)); }
   dayRng = dayHi - dayLo;
   adrPct = g_intra && !isna(adrVal) && adrVal > 0 ? dayRng / adrVal : NA;
   adrExh = useAdr && !isna(adrPct) && adrPct >= adrMax;
   adrPosD = dayRng > 0 ? (C(0) - dayLo) / dayRng : NA;
   adrChaseL = adrExh && !isna(adrPosD) && adrPosD >= 0.7;
   adrChaseS = adrExh && !isna(adrPosD) && adrPosD <= 0.3;
}

//+------------------------------------------------------------------+
//| MODULE 10 — dealing range + SB range lock · MODULE 11 — regime    |
//+------------------------------------------------------------------+
void M10()
{
   int anchBarExt = MathMin(nzi(extResBar, g_bi), nzi(extSupBar, g_bi));
   int anchBarInt = MathMin(nzi(lastResBar, g_bi), nzi(lastSupBar, g_bi));
   int anchBar = rangeSrc == RS_EXT ? anchBarExt : anchBarInt;
   int drLen = MathMax(5, MathMin(500, g_bi - anchBar + 1));
   rngHi = HH(drLen, 0);
   rngLo = LL(drLen, 0);
   rngHiBar = g_bi - HHoff(drLen, 0);
   rngLoBar = g_bi - LLoff(drLen, 0);
   rangeOK = rngHi > rngLo;
   rangeHolds = rangeOK && atr > 0 && (rngHi - rngLo) >= 2 * atr;
   bullRange = rangeOK && rngHiBar > rngLoBar;
   bearRange = rangeOK && rngLoBar > rngHiBar;
   rngW = rangeOK ? rngHi - rngLo : NA;
   pdPos = rangeOK ? MathMin(1, MathMax(0, (C(0) - rngLo) / rngW)) : NA;
   oteBuyTop  = rangeOK ? rngHi - OTE_1 * rngW : NA;
   oteBuyBot  = rangeOK ? rngHi - OTE_2 * rngW : NA;
   oteSellBot = rangeOK ? rngLo + OTE_1 * rngW : NA;
   oteSellTop = rangeOK ? rngLo + OTE_2 * rngW : NA;
   inOTEbuy  = bullRange && C(0) <= oteBuyTop  && C(0) >= oteBuyBot;
   inOTEsell = bearRange && C(0) >= oteSellBot && C(0) <= oteSellTop;
   if(sbOn)
   {
      if(sbWinNow != 0 && sbWinPrev != sbWinNow) { sbRngHi = rngHi; sbRngLo = rngLo; sbRngWin = sbWinNow; }
      else if(sbWinNow == 0 && sbRngWin != 0 && !sbSetLive) { sbRngHi = NA; sbRngLo = NA; sbRngWin = 0; }
   }
   sbRngOK = !isna(sbRngHi) && !isna(sbRngLo) && sbRngHi > sbRngLo;
   sbPdOK  = sbRngOK || rangeOK;
   double sbPdRaw = sbRngOK ? (C(0) - sbRngLo) / (sbRngHi - sbRngLo) : pdPos;
   bool sbPdOut = sbRngOK && (sbPdRaw < -0.15 || sbPdRaw > 1.15);
   sbPdPos = sbPdOut ? pdPos : sbRngOK ? MathMin(1, MathMax(0, sbPdRaw)) : pdPos;
}
void M11()
{
   if(eBosUp) lastEBosUpBar = g_bi;
   if(eBosDn) lastEBosDnBar = g_bi;
   if(eChochUp) lastEChUpBar = g_bi;
   if(eChochDn) lastEChDnBar = g_bi;
   bool regEBosUp = f_recent(lastEBosUpBar, REGIME_LOOK), regEBosDn = f_recent(lastEBosDnBar, REGIME_LOOK);
   bool regEChUp  = f_recent(lastEChUpBar, REGIME_LOOK),  regEChDn  = f_recent(lastEChDnBar, REGIME_LOOK);
   double regRngW = !isna(extRes) && !isna(extSup) ? MathAbs(extRes - extSup) : NA;
   double extRngAtr = !isna(regRngW) && atr > 0 ? regRngW / atr : NA;
   bool regTrending = (extDir == 1 && regEBosUp && !regEChDn) || (extDir == -1 && regEBosDn && !regEChUp);
   bool regTransition = !regTrending && (regEChUp || regEChDn);
   double legRngAtr = !isna(rngW) && atr > 0 ? rngW / atr : NA;
   bool inExtRng = !isna(extRes) && !isna(extSup) && C(0) <= MathMax(extRes, extSup) && C(0) >= MathMin(extRes, extSup);
   bool regThrust = atr > 0 && MathAbs(C(0) - C(REGIME_LOOK)) >= CHOP_RANGE_ATR * atr;
   bool regChop = !regTrending && !regTransition && !regThrust && !isna(extRngAtr) && extRngAtr < CHOP_RANGE_ATR
                  && (isna(legRngAtr) || legRngAtr < CHOP_RANGE_ATR) && inExtRng;
   regime = regTrending ? "TRENDING" : regTransition ? "TRANSITION" : regChop ? "CHOP" : "RANGING";
   instSweepL = lastSslQualRaw >= 3 && recentMssUp;
   instSweepS = lastBslQualRaw >= 3 && recentMssDn;
   structDir = extDir != 0 ? extDir : msDir;
}

//+------------------------------------------------------------------+
//| MODULE 12 — FVG registry + IFVG + latest FVG                      |
//+------------------------------------------------------------------+
Fvg NewFvg(const bool isBull, const double top, const double bot)
{
   Fvg f;
   color c = isBull ? COL_BULL : COL_BEAR;
   f.bx = showFvg ? BoxNew(g_bi - 2, top, g_bi + 1, bot, Col(c, 70), STYLE_DOT, c, 96, "FVG", Col(c, 30), tinySize, HA_RIGHT, VA_CENTER) : "";
   f.top = top; f.bot = bot; f.barCreated = g_bi; f.isBull = isBull; f.partial = false; f.inverted = false;
   return f;
}
void M12()
{
   bullFVG = L(0) - H(2) >= minZoneAtr * atr;
   bearFVG = L(2) - H(0) >= minZoneAtr * atr;
   ifvgSupTop = NA; ifvgSupBot = NA; ifvgDemTop = NA; ifvgDemBot = NA;
   if(bullFVG)
   {
      APush(bullFvgs, NewFvg(true, L(0), H(2)));
      if(ArraySize(bullFvgs) > fvgMaxKeep) { BoxDel(bullFvgs[0].bx); ARemove(bullFvgs, 0); }
   }
   if(bearFVG)
   {
      APush(bearFvgs, NewFvg(false, L(2), H(0)));
      if(ArraySize(bearFvgs) > fvgMaxKeep) { BoxDel(bearFvgs[0].bx); ARemove(bearFvgs, 0); }
   }
   for(int i = ArraySize(bullFvgs) - 1; i >= 0; i--)
   {
      if(i >= ArraySize(bullFvgs)) continue;
      if(g_bi <= bullFvgs[i].barCreated) continue;
      if(L(0) <= bullFvgs[i].top && !bullFvgs[i].partial)
      {
         bullFvgs[i].partial = true;
         BoxSetText(bullFvgs[i].bx, "FVG ·tested");
      }
      if(useIfvg && C(0) < bullFvgs[i].bot && !bullFvgs[i].inverted)
      {
         Fvg f = bullFvgs[i];
         f.inverted = true; f.isBull = false; f.partial = false; f.barCreated = g_bi;
         if(f.bx != "")
         {
            BoxSetBorder(f.bx, Col(COL_BEAR, 45));
            BoxSetBg(f.bx, COL_BEAR, 92);
            BoxSetText(f.bx, "IFVG ▼");
            BoxSetTextCol(f.bx, COL_BEAR);
         }
         ifvgSupTop = f.top; ifvgSupBot = f.bot;
         ARemove(bullFvgs, i);
         APush(bearFvgs, f);
         if(ArraySize(bearFvgs) > fvgMaxKeep) { BoxDel(bearFvgs[0].bx); ARemove(bearFvgs, 0); }
      }
      else if(C(0) < bullFvgs[i].bot || L(0) <= bullFvgs[i].bot || g_bi - bullFvgs[i].barCreated > fvgMaxAge)
      {
         BoxDel(bullFvgs[i].bx);
         ARemove(bullFvgs, i);
      }
   }
   for(int i = ArraySize(bearFvgs) - 1; i >= 0; i--)
   {
      if(i >= ArraySize(bearFvgs)) continue;
      if(g_bi <= bearFvgs[i].barCreated) continue;
      if(H(0) >= bearFvgs[i].bot && !bearFvgs[i].partial)
      {
         bearFvgs[i].partial = true;
         BoxSetText(bearFvgs[i].bx, bearFvgs[i].inverted ? "IFVG ▼ ·tested" : "FVG ·tested");
      }
      if(useIfvg && C(0) > bearFvgs[i].top && !bearFvgs[i].inverted)
      {
         Fvg f = bearFvgs[i];
         f.inverted = true; f.isBull = true; f.partial = false; f.barCreated = g_bi;
         if(f.bx != "")
         {
            BoxSetBorder(f.bx, Col(COL_BULL, 45));
            BoxSetBg(f.bx, COL_BULL, 92);
            BoxSetText(f.bx, "IFVG ▲");
            BoxSetTextCol(f.bx, COL_BULL);
         }
         ifvgDemTop = f.top; ifvgDemBot = f.bot;
         ARemove(bearFvgs, i);
         APush(bullFvgs, f);
         if(ArraySize(bullFvgs) > fvgMaxKeep) { BoxDel(bullFvgs[0].bx); ARemove(bullFvgs, 0); }
      }
      else if(C(0) > bearFvgs[i].top || H(0) >= bearFvgs[i].top || g_bi - bearFvgs[i].barCreated > fvgMaxAge)
      {
         BoxDel(bearFvgs[i].bx);
         ARemove(bearFvgs, i);
      }
   }
   // latest respected FVG per side
   if(bullFVG)
   {
      cFvgBTop = L(0); cFvgBBot = H(2); cFvgBBar = g_bi;
      cFvgBDisp = Bull(1) && Body(1) >= MathMin(dispFactor, sbDispAtr) * atr;
   }
   if(!isna(cFvgBBot) && C(0) < cFvgBBot) { cFvgBTop = NA; cFvgBBot = NA; cFvgBBar = NAI; }
   if(bearFVG)
   {
      cFvgSBot = H(0); cFvgSTop = L(2); cFvgSBar = g_bi;
      cFvgSDisp = Bear(1) && Body(1) >= MathMin(dispFactor, sbDispAtr) * atr;
   }
   if(!isna(cFvgSTop) && C(0) > cFvgSTop) { cFvgSTop = NA; cFvgSBot = NA; cFvgSBar = NAI; }
}

//+------------------------------------------------------------------+
//| MODULE 13 — zone engine                                          |
//+------------------------------------------------------------------+
void ZoneSetCoords(const int k)
{
   BoxSetTopBot(zones[k].bx, zones[k].top, zones[k].bot);
}
// FIX-T20 / FIX-V3: opposing zones may not overlap — the newer zone wins the band
void f_claimBand(const bool isSupply, const double top, const double bot)
{
   for(int k = ArraySize(zones) - 1; k >= 0; k--)
   {
      if(k >= ArraySize(zones)) continue;
      if(zones[k].isSupply == isSupply) continue;
      double ot = zones[k].top, ob = zones[k].bot;
      if(!(ob > top || ot < bot))
      {
         ot = isSupply ? MathMin(ot, bot) : ot;
         ob = isSupply ? ob : MathMax(ob, top);
         if(ot - ob < minZoneAtr * atr) { BoxDel(zones[k].bx); ARemove(zones, k); }
         else if(isSupply) { zones[k].top = ot; ZoneSetCoords(k); }
         else { zones[k].bot = ob; ZoneSetCoords(k); }
      }
   }
}
Zone NewZone(const bool isSupply, const double top, const double bot, const bool star, const string kind, const string txt, const int lft)
{
   color c = isSupply ? COL_BEAR : COL_BULL;
   int x1 = lft != 0 ? lft : g_bi - 2;
   bool thin = kind == "OB";
   Zone z;
   z.bx = BoxNew(x1, top, g_bi + 1, bot, Col(c, thin ? 75 : 55), STYLE_SOLID, c, thin ? 96 : 93, txt, Col(c, thin ? 35 : 0), drawSize,
                 HA_RIGHT, isSupply ? VA_TOP : VA_BOTTOM);
   z.top = top; z.bot = bot; z.isSupply = isSupply; z.touched = false; z.tapped50 = false; z.signaled = false;
   z.score = star ? 3 : 2; z.tap50Bar = -1; z.flipped = false; z.touchBar = -1; z.kind = kind; z.tests = 0; z.wasIn = false;
   return z;
}
void FlipZone(const int k, const bool toSupply, const bool isBrk)
{
   zones[k].isSupply = toSupply; zones[k].flipped = true; zones[k].touched = false; zones[k].touchBar = -1;
   zones[k].tapped50 = false; zones[k].signaled = false; zones[k].tap50Bar = -1; zones[k].tests = 0; zones[k].wasIn = false;
   zones[k].kind = isBrk ? "BRK" : "MIT";
   zones[k].score = isBrk ? 3 : 2;
   color c = toSupply ? COL_BEAR : COL_BULL;
   BoxSetBorder(zones[k].bx, Col(c, 55));
   BoxSetBg(zones[k].bx, c, 93);
   BoxSetText(zones[k].bx, zones[k].kind);
   BoxSetTextCol(zones[k].bx, c);
   BoxSetTextVa(zones[k].bx, toSupply ? VA_TOP : VA_BOTTOM);
}
void ZoneUpdate()
{
   sigSDLong = false; sigSDShort = false;
   slSDLong = NA; slSDShort = NA;
   double flipTop = NA, flipBot = NA;
   bool flipSup = false;
   for(int i = ArraySize(zones) - 1; i >= 0; i--)
   {
      if(i >= ArraySize(zones)) continue;
      double top = zones[i].top, bot = zones[i].bot, midP = (top + bot) / 2;
      if(zones[i].isSupply)
      {
         if(C(0) > top)
         {
            if(showFlip && !zones[i].flipped) { FlipZone(i, false, recentSsl && recentStructUp); flipTop = top; flipBot = bot; flipSup = false; }
            else { BoxDel(zones[i].bx); ARemove(zones, i); }
            continue;
         }
         bool inZ = H(0) >= bot;
         zones[i].touchBar = inZ && !zones[i].touched ? g_bi : zones[i].touchBar;
         zones[i].touched  = inZ || zones[i].touched;
         bool newTest = inZ && !zones[i].wasIn;
         zones[i].tests = newTest ? zones[i].tests + 1 : zones[i].tests;
         if(newTest && zones[i].tests > zoneMaxTests && !zones[i].signaled)
         {
            zones[i].signaled = true;
            BoxSetBg(zones[i].bx, COL_BEAR, 96);
            BoxSetText(zones[i].bx, zones[i].kind + " ·spent");
         }
         zones[i].wasIn = inZ;
         zones[i].tapped50 = H(0) < bot ? false : zones[i].tapped50;
         bool tap = H(0) >= midP && !zones[i].tapped50;
         if(tap) { zones[i].tapped50 = true; zones[i].tap50Bar = g_bi; }
         if(!zones[i].signaled && zones[i].tapped50 && g_bi - zones[i].tap50Bar <= confirmWin && zoneBearConf && H(0) >= bot)
         {
            sigSDShort = true;
            slSDShort = MathMax(H(0), top) + SL_PAD_ATR * atr;
            zones[i].signaled = true;
            BoxSetBg(zones[i].bx, COL_BEAR, 94);
         }
      }
      else
      {
         if(C(0) < bot)
         {
            if(showFlip && !zones[i].flipped) { FlipZone(i, true, recentBsl && recentStructDn); flipTop = top; flipBot = bot; flipSup = true; }
            else { BoxDel(zones[i].bx); ARemove(zones, i); }
            continue;
         }
         bool inZ = L(0) <= top;
         zones[i].touchBar = inZ && !zones[i].touched ? g_bi : zones[i].touchBar;
         zones[i].touched  = inZ || zones[i].touched;
         bool newTest = inZ && !zones[i].wasIn;
         zones[i].tests = newTest ? zones[i].tests + 1 : zones[i].tests;
         if(newTest && zones[i].tests > zoneMaxTests && !zones[i].signaled)
         {
            zones[i].signaled = true;
            BoxSetBg(zones[i].bx, COL_BULL, 96);
            BoxSetText(zones[i].bx, zones[i].kind + " ·spent");
         }
         zones[i].wasIn = inZ;
         zones[i].tapped50 = L(0) > top ? false : zones[i].tapped50;
         bool tap = L(0) <= midP && !zones[i].tapped50;
         if(tap) { zones[i].tapped50 = true; zones[i].tap50Bar = g_bi; }
         if(!zones[i].signaled && zones[i].tapped50 && g_bi - zones[i].tap50Bar <= confirmWin && zoneBullConf && L(0) <= top)
         {
            sigSDLong = true;
            slSDLong = MathMin(L(0), bot) - SL_PAD_ATR * atr;
            zones[i].signaled = true;
            BoxSetBg(zones[i].bx, COL_BULL, 94);
         }
      }
   }
   if(!isna(flipTop)) f_claimBand(flipSup, flipTop, flipBot);
}
bool ZoneOverlapSide(const bool isSupply, const double top, const double bot)
{
   for(int k = 0; k < ArraySize(zones); k++)
      if(zones[k].isSupply == isSupply && !(bot > zones[k].top || top < zones[k].bot)) return true;
   return false;
}
void ZoneCreate()
{
   bool dispUp = Bull(1) && Body(1) >= dispFactor * atr && VolOkAt(1);
   bool dispDn = Bear(1) && Body(1) >= dispFactor * atr && VolOkAt(1);
   bool newDemand = showZones && bullFVG && dispUp;
   bool newSupply = showZones && bearFVG && dispDn;
   if(newDemand)
   {
      double zTop = L(0), zBot = MathMax(H(2), L(0) - maxZoneAtr * atr);
      bool bs = !isnai(resBrkBar) && resBrkBar >= g_bi - 1;
      int newScore = bs ? 3 : 2;
      bool dup = false;
      for(int i = ArraySize(zones) - 1; i >= 0; i--)
      {
         if(i >= ArraySize(zones)) continue;
         if(!zones[i].isSupply && !(zBot > zones[i].top || zTop < zones[i].bot))
         {
            bool keep = zones[i].score >= newScore && !zones[i].signaled;
            dup = keep || dup;
            if(!keep) { BoxDel(zones[i].bx); ARemove(zones, i); }
         }
      }
      if(!dup && zTop - zBot >= minZoneAtr * atr)
      {
         f_claimBand(false, zTop, zBot);
         APush(zones, NewZone(false, zTop, zBot, bs, "SD", bs ? "DEMAND ★HP" : "", 0));
         if(showOB && Bear(2))
         {
            double obTop = H(2), obBot = MathMax(L(2), H(2) - maxZoneAtr * atr);
            if(obTop - obBot >= minZoneAtr * atr)
            {
               f_claimBand(false, obTop, obBot);
               APush(zones, NewZone(false, obTop, obBot, false, "OB", "OB", g_bi - 2));
            }
         }
      }
   }
   if(newSupply)
   {
      double zBot = H(0), zTop = MathMin(L(2), H(0) + maxZoneAtr * atr);
      bool bs = !isnai(supBrkBar) && supBrkBar >= g_bi - 1;
      int newScore = bs ? 3 : 2;
      bool dup = false;
      for(int i = ArraySize(zones) - 1; i >= 0; i--)
      {
         if(i >= ArraySize(zones)) continue;
         if(zones[i].isSupply && !(zBot > zones[i].top || zTop < zones[i].bot))
         {
            bool keep = zones[i].score >= newScore && !zones[i].signaled;
            dup = keep || dup;
            if(!keep) { BoxDel(zones[i].bx); ARemove(zones, i); }
         }
      }
      if(!dup && zTop - zBot >= minZoneAtr * atr)
      {
         f_claimBand(true, zTop, zBot);
         APush(zones, NewZone(true, zTop, zBot, bs, "SD", bs ? "SUPPLY ★HP" : "", 0));
         if(showOB && Bull(2))
         {
            double obBot = L(2), obTop = MathMin(H(2), L(2) + maxZoneAtr * atr);
            if(obTop - obBot >= minZoneAtr * atr)
            {
               f_claimBand(true, obTop, obBot);
               APush(zones, NewZone(true, obTop, obBot, false, "OB", "OB", g_bi - 2));
            }
         }
      }
   }
   // rejection blocks
   bool rbSwpH = H(pivLen) > HH(pivLen * 2, pivLen + 1);
   bool rbDspH = LL(pivLen, 0) <= H(pivLen) - dispFactor * atr;
   bool rbSwpL = L(pivLen) < LL(pivLen * 2, pivLen + 1);
   bool rbDspL = HH(pivLen, 0) >= L(pivLen) + dispFactor * atr;
   bool rbNew = false;
   if(showRB)
   {
      if(!isna(ph))
      {
         double rbTop = H(pivLen), rbBot = MathMax(O(pivLen), C(pivLen));
         if(rbTop - rbBot >= minWickAtr * atr && rbSwpH && rbDspH && !ZoneOverlapSide(true, rbTop, rbBot))
         {
            f_claimBand(true, rbTop, rbBot);
            APush(zones, NewZone(true, rbTop, rbBot, false, "RB", "RB", g_bi - pivLen));
            rbNew = true;
         }
      }
      if(!isna(pl))
      {
         double rbBot2 = L(pivLen), rbTop2 = MathMin(O(pivLen), C(pivLen));
         if(rbTop2 - rbBot2 >= minWickAtr * atr && rbSwpL && rbDspL && !ZoneOverlapSide(false, rbTop2, rbBot2))
         {
            f_claimBand(false, rbTop2, rbBot2);
            APush(zones, NewZone(false, rbTop2, rbBot2, false, "RB", "RB", g_bi - pivLen));
            rbNew = true;
         }
      }
   }
   // IFVG -> POI zone
   bool ifvgNew = false;
   if(useIfvg)
   {
      if(!isna(ifvgSupTop) && !ZoneOverlapSide(true, ifvgSupTop, ifvgSupBot) && ifvgSupTop - ifvgSupBot >= minZoneAtr * atr)
      {
         f_claimBand(true, ifvgSupTop, ifvgSupBot);
         APush(zones, NewZone(true, ifvgSupTop, ifvgSupBot, false, "IFVG", "IFVG", g_bi - 2));
         ifvgNew = true;
      }
      if(!isna(ifvgDemTop) && !ZoneOverlapSide(false, ifvgDemTop, ifvgDemBot) && ifvgDemTop - ifvgDemBot >= minZoneAtr * atr)
      {
         f_claimBand(false, ifvgDemTop, ifvgDemBot);
         APush(zones, NewZone(false, ifvgDemTop, ifvgDemBot, false, "IFVG", "IFVG", g_bi - 2));
         ifvgNew = true;
      }
   }
   // keep the newest maxZones per side (rejection blocks max 2 per side)
   if(newDemand || newSupply || rbNew || ifvgNew)
   {
      int dKeep = 0, sKeep = 0, dRb = 0, sRb = 0;
      for(int i = ArraySize(zones) - 1; i >= 0; i--)
      {
         bool sup = zones[i].isSupply;
         sKeep = sup ? sKeep + 1 : sKeep;
         dKeep = sup ? dKeep : dKeep + 1;
         sRb   = sup && zones[i].kind == "RB" ? sRb + 1 : sRb;
         dRb   = !sup && zones[i].kind == "RB" ? dRb + 1 : dRb;
         if((sup ? sKeep : dKeep) > maxZones || (sup ? sRb : dRb) > 2) { BoxDel(zones[i].bx); ARemove(zones, i); }
      }
   }
}
void NextZones()
{
   nbTop = NA; nbBot = NA; nsTop = NA; nsBot = NA; nbFresh = false; nsFresh = false;
   nbScore = 0; nsScore = 0; nbKind = ""; nsKind = "";
   double c = C(0);
   for(int k = 0; k < ArraySize(zones); k++)
   {
      double t = zones[k].top, b = zones[k].bot;
      if(!zones[k].isSupply && !zones[k].signaled && b <= c && (isna(nbTop) || t > nbTop))
      { nbTop = t; nbBot = b; nbFresh = !zones[k].touched || zones[k].touchBar == g_bi; nbScore = zones[k].score; nbKind = zones[k].kind; }
      if(zones[k].isSupply && !zones[k].signaled && t >= c && (isna(nsBot) || b < nsBot))
      { nsTop = t; nsBot = b; nsFresh = !zones[k].touched || zones[k].touchBar == g_bi; nsScore = zones[k].score; nsKind = zones[k].kind; }
   }
   if(nextInclHtf && !isna(hPoiBTop) && hPoiBBot <= c && hPoiBTop - hPoiBBot <= hPoiNextMaxAtr * atr && (isna(nbTop) || hPoiBTop > nbTop))
   { nbTop = hPoiBTop; nbBot = hPoiBBot; nbFresh = nzi(hPoiBIn, 0) == 0; nbScore = 3; nbKind = "HTF"; }
   if(nextInclHtf && !isna(hPoiSTop) && hPoiSTop >= c && hPoiSTop - hPoiSBot <= hPoiNextMaxAtr * atr && (isna(nsBot) || hPoiSBot < nsBot))
   { nsTop = hPoiSTop; nsBot = hPoiSBot; nsFresh = nzi(hPoiSIn, 0) == 0; nsScore = 3; nsKind = "HTF"; }
   touchNextBuy  = !isna(nbTop) && !isna(pNbTop) && L(0) <= nbTop && L(1) > pNbTop;
   touchNextSell = !isna(nsBot) && !isna(pNsBot) && H(0) >= nsBot && H(1) < pNsBot;
}
void M13()
{
   ZoneUpdate();
   ZoneCreate();
   NextZones();
}

//+------------------------------------------------------------------+
//| MODULE 14 — trigger-candidate engines                             |
//+------------------------------------------------------------------+
int    lastCrtLongBar = NAI, lastCrtShortBar = NAI, lastTbsLongBar = NAI, lastTbsShortBar = NAI;
bool   sigCRTLong, sigCRTShort, sigTBSLong, sigTBSShort, sigTLLong, sigTLShort, tlUpBreak, tlDnBreak;
bool   sig3Long, sig3Short, sig4Long, sig4Short;
double slCRTLong, slCRTShort, slTBSLong, slTBSShort, slTLLong, slTLShort, sl3Long, sl3Short, sl4Long, sl4Short;
double slMCLong, slMCShort, slLTLong, slLTShort;
int    ibStage = 0, ibStart = NAI;
double ibMHigh = NA, ibMLow = NA, ibHigh = NA, ibLow = NA;

void M14()
{
   bool crtLongCd  = isnai(lastCrtLongBar)  || g_bi - lastCrtLongBar  > sigCooldown;
   bool crtShortCd = isnai(lastCrtShortBar) || g_bi - lastCrtShortBar > sigCooldown;
   bool tbsLongCd  = isnai(lastTbsLongBar)  || g_bi - lastTbsLongBar  > sigCooldown;
   bool tbsShortCd = isnai(lastTbsShortBar) || g_bi - lastTbsShortBar > sigCooldown;
   slCRTLong = NA; slCRTShort = NA; slTBSLong = NA; slTBSShort = NA; slTLLong = NA; slTLShort = NA;
   slMCLong = NA; slMCShort = NA; slLTLong = NA; slLTShort = NA;
   // CRT
   bool crtC1Big = Rng(2) >= crtRangeAtr * atr;
   bool crtBullSetup = crtC1Big && L(1) < L(2) && C(1) > L(2) && C(1) < H(2) && L(2) - L(1) >= minWickAtr * atr;
   bool crtBearSetup = crtC1Big && H(1) > H(2) && C(1) < H(2) && C(1) > L(2) && H(1) - H(2) >= minWickAtr * atr;
   sigCRTLong  = showCRT && crtBullSetup && bullBar && C(0) > H(1) && body >= crtDispAtr * atr && crtLongCd;
   sigCRTShort = showCRT && crtBearSetup && bearBar && C(0) < L(1) && body >= crtDispAtr * atr && crtShortCd;
   if(sigCRTLong)  slCRTLong  = L(1) - SL_PAD_ATR * atr;
   if(sigCRTShort) slCRTShort = H(1) + SL_PAD_ATR * atr;
   // Turtle soup
   double tbsLow = LL(tbsLen, 1), tbsHigh = HH(tbsLen, 1);
   int tbsLowAge = LLoff(tbsLen, 1), tbsHighAge = HHoff(tbsLen, 1);
   sigTBSLong  = showTBS && L(0) < tbsLow && C(0) > tbsLow && bullBar && f_tbsAgeOk(tbsLowAge) && C(0) >= L(0) + 0.5 * rng && tbsLongCd;
   sigTBSShort = showTBS && H(0) > tbsHigh && C(0) < tbsHigh && bearBar && f_tbsAgeOk(tbsHighAge) && C(0) <= H(0) - 0.5 * rng && tbsShortCd;
   if(sigTBSLong)  slTBSLong  = L(0) - SL_PAD_ATR * atr;
   if(sigTBSShort) slTBSShort = H(0) + SL_PAD_ATR * atr;
   // Trendlines
   double tlUpVal = !isna(tlUpSlope) ? tlUpPrice + tlUpSlope * (g_bi - tlUpBar) : NA;
   double tlDnVal = !isna(tlDnSlope) ? tlDnPrice + tlDnSlope * (g_bi - tlDnBar) : NA;
   sigTLLong = false; sigTLShort = false; tlUpBreak = false; tlDnBreak = false;
   if(!isna(tlUpVal))
   {
      bool nearUp = L(0) <= tlUpVal + NEAR_LVL_ATR * atr;
      if(C(0) < tlUpVal)
      {
         tlUpBreak = true;
         if(tlUpLn != "") { LineEndAt(tlUpLn, g_bi); LineSetStyle(tlUpLn, STYLE_DASH); ObjectSetInteger(0, tlUpLn, OBJPROP_WIDTH, 1); }
         tlUpLn = ""; tlUpSlope = NA; tlUpWasNear = false;
      }
      else
      {
         if(nearUp && !tlUpWasNear) tlUpTouch++;
         if(L(0) < tlUpVal && tlSweepEnt && tlUpTouch > tlTouchMin && tlUpTouch >= 2 && (!tlNeedConf || zoneBullConf))
         { sigTLLong = true; slTLLong = L(0) - SL_PAD_ATR * atr; }
         tlUpWasNear = nearUp;
      }
      if(!isnai(tlUpBar) && g_bi - tlUpBar > tlMaxAge) { LineDel(tlUpLn); tlUpLn = ""; tlUpSlope = NA; }
   }
   if(!isna(tlDnVal))
   {
      bool nearDn = H(0) >= tlDnVal - NEAR_LVL_ATR * atr;
      if(C(0) > tlDnVal)
      {
         tlDnBreak = true;
         if(tlDnLn != "") { LineEndAt(tlDnLn, g_bi); LineSetStyle(tlDnLn, STYLE_DASH); ObjectSetInteger(0, tlDnLn, OBJPROP_WIDTH, 1); }
         tlDnLn = ""; tlDnSlope = NA; tlDnWasNear = false;
      }
      else
      {
         if(nearDn && !tlDnWasNear) tlDnTouch++;
         if(H(0) > tlDnVal && tlSweepEnt && tlDnTouch > tlTouchMin && tlDnTouch >= 2 && (!tlNeedConf || zoneBearConf))
         { sigTLShort = true; slTLShort = H(0) + SL_PAD_ATR * atr; }
         tlDnWasNear = nearDn;
      }
      if(!isnai(tlDnBar) && g_bi - tlDnBar > tlMaxAge) { LineDel(tlDnLn); tlDnLn = ""; tlDnSlope = NA; }
   }
   if(tlUpLn != "" && tlUpTouch >= 1) { LineSetStyle(tlUpLn, STYLE_SOLID); ObjectSetInteger(0, tlUpLn, OBJPROP_WIDTH, 2); }
   if(tlDnLn != "" && tlDnTouch >= 1) { LineSetStyle(tlDnLn, STYLE_SOLID); ObjectSetInteger(0, tlDnLn, OBJPROP_WIDTH, 2); }
   // Inside bar breakout
   sig3Long = false; sig3Short = false; sl3Long = NA; sl3Short = NA;
   double mMid = (ibMHigh + ibMLow) / 2;
   if(ibStage == 1)
   {
      if(H(0) < ibMHigh && L(0) > ibMLow && L(0) >= mMid) { ibHigh = H(0); ibLow = L(0); ibStage = 2; }
      else ibStage = 0;
   }
   else if(ibStage == 2)
   {
      if(C(0) > ibHigh)
      {
         sig3Long = showS3 && bullBar && body >= BRK_BODY_ATR * atr && C(0) >= H(0) - STRONG_CLOSE_PCT * rng && structDir >= 0 && biasOkL;
         sl3Long = (ibLow + ibMLow) / 2 - SL_PAD_ATR * atr;
         ibStage = 0;
      }
      else if(C(0) < ibLow || g_bi - ibStart > IB_WAIT_BARS) ibStage = 0;
   }
   else if(ibStage == -1)
   {
      if(H(0) < ibMHigh && L(0) > ibMLow && H(0) <= mMid) { ibHigh = H(0); ibLow = L(0); ibStage = -2; }
      else ibStage = 0;
   }
   else if(ibStage == -2)
   {
      if(C(0) < ibLow)
      {
         sig3Short = showS3 && bearBar && body >= BRK_BODY_ATR * atr && C(0) <= L(0) + STRONG_CLOSE_PCT * rng && structDir <= 0 && biasOkS;
         sl3Short = (ibHigh + ibMHigh) / 2 + SL_PAD_ATR * atr;
         ibStage = 0;
      }
      else if(C(0) > ibHigh || g_bi - ibStart > IB_WAIT_BARS) ibStage = 0;
   }
   if(showS3 && ibStage == 0 && brokeUp && body >= ibBodyAtr * atr)      { ibStage = 1;  ibMHigh = H(0); ibMLow = L(0); ibStart = g_bi; }
   else if(showS3 && ibStage == 0 && brokeDn && body >= ibBodyAtr * atr) { ibStage = -1; ibMHigh = H(0); ibMLow = L(0); ibStart = g_bi; }
   // Doji reversal
   int dojiRecent1 = 0;
   for(int k = 1; k <= DOJI_WINDOW; k++) if(DojiAt(k)) dojiRecent1++;
   int ctxBias = structDir != 0 ? structDir : htfB;
   double sRng = 0;
   for(int k = 1; k <= DOJI_WINDOW; k++) sRng += Rng(k);
   bool dojiCompressed = sRng / DOJI_WINDOW <= atr;
   bool dojiRaidRes = !isna(lastRes) && HH(DOJI_WINDOW, 0) > lastRes;
   bool dojiRaidSup = !isna(lastSup) && LL(DOJI_WINDOW, 0) < lastSup;
   sig4Long = false; sig4Short = false;
   if(showS4)
   {
      bool atRes = !isna(lastRes) && H(0) >= lastRes - NEAR_LVL_ATR * atr && C(0) <= lastRes + NEAR_LVL_ATR * atr;
      bool atSup = !isna(lastSup) && L(0) <= lastSup + NEAR_LVL_ATR * atr && C(0) >= lastSup - NEAR_LVL_ATR * atr;
      bool driftUp = C(1) > C(DOJI_WINDOW + 1), driftDn = C(1) < C(DOJI_WINDOW + 1);
      bool dispConf = body >= BRK_BODY_ATR * atr;
      sig4Short = ctxBias == -1 && dojiRecent1 >= dojiMin && atRes && driftUp && dojiCompressed && dojiRaidRes && bearConfirm && dispConf;
      sig4Long  = ctxBias == 1  && dojiRecent1 >= dojiMin && atSup && driftDn && dojiCompressed && dojiRaidSup && bullConfirm && dispConf;
   }
   sl4Long  = PMin(lastSup, LL(DOJI_WINDOW, 0)) - SL_PAD_ATR * atr;
   sl4Short = PMax(lastRes, HH(DOJI_WINDOW, 0)) + SL_PAD_ATR * atr;
}

//+------------------------------------------------------------------+
//| MODULE 15A — machine + tracker state, direction lock             |
//+------------------------------------------------------------------+
int    suL = 0, suLBar = NAI, suLFvgBar = NAI, suS = 0, suSBar = NAI, suSFvgBar = NAI;
double suLAnchorT = NA, suLAnchorB = NA, suLSweepLvl = NA, suLSweepExt = NA;
double suSAnchorT = NA, suSAnchorB = NA, suSSweepLvl = NA, suSSweepExt = NA;
string suLReason = "", suSReason = "";
bool   suLCont = false, suSCont = false;
double trdEntry = NA, trdSL = NA, trdTP1 = NA, trdTP2 = NA, trdTP3 = NA, trdLiqTgt = NA;
int    trdDir = 0, trdSbWin = 0, trdShiftG = 0;
bool   trdTp1Hit = false, trdTp2Hit = false, trdIsSb = false;
int    dirLock;
bool   lockOkL, lockOkS;

//+------------------------------------------------------------------+
//| MODULE 16 — confluence score + tiers                              |
//+------------------------------------------------------------------+
int    sesPts, ctxLong, ctxShort, liqLong, liqShort, poiLong, poiShort, trigLong, trigShort, execLong, execShort;
int    scoreBaseL, scoreBaseS, scoreLong, scoreShort, sbCtxLong, sbCtxShort, tierLong, tierShort, minRank, poiSideBias;
bool   sesTierOK, useAnchL, useAnchS, dmdFresh, supFresh, inDemand, nearDemand, inSupply, nearSupply;
bool   poiConflictRaw, poiBlockL, poiBlockS, poiConflict, retestLong, retestShort, sbPoolOkL, sbPoolOkS;
double dmdTop, dmdBot, supTop, supBot;

double f_decay(const int evBar, const double pts)
{
   return evBar != NAI && g_bi - evBar <= TRIG_LOOK ? pts * (1.0 - (g_bi - evBar) / (TRIG_LOOK + 1.0)) : 0.0;
}
string f_tierTxt(const int t) { return t == 4 ? "A+" : t == 3 ? "A" : t == 2 ? "B" : "C"; }
int f_tier(const bool isLong)
{
   bool trigCisd = shiftSrc == SH_CISD, trigInt = shiftSrc == SH_INT || trigCisd;
   int liq = isLong ? liqLong : liqShort;
   int poi = isLong ? poiLong : poiShort;
   bool hasTrig = isLong ? (recentMssUp || f_recent(lastEChUpBar, TRIG_LOOK) || (trigInt && recentChUp) || (trigCisd && recentCisdUp))
                         : (recentMssDn || f_recent(lastEChDnBar, TRIG_LOOK) || (trigInt && recentChDn) || (trigCisd && recentCisdDn));
   bool hasExec = (isLong ? execLong : execShort) >= 5;
   int tier = 1;
   if(hasTrig && (liq >= 10 || poi >= 5)) tier = 2;
   if(liq >= 10 && poi >= 10 && hasTrig && hasExec) tier = 3;
   bool pdLock = isLong ? sbPdPos < 0.5 : sbPdPos >= 0.5;
   bool pdLive = isLong ? pdPos < 0.5 : pdPos >= 0.5;
   bool pdOk   = (isLong ? sbTagL : sbTagS) != 0 ? (sbPdOK && pdLock) : (rangeOK && (!rangeHolds || pdLive));
   if(tier == 3 && (isLong ? htfB > 0 : htfB < 0) && sesTierOK && (isLong ? lastSslQualRaw : lastBslQualRaw) >= 3 && pdOk) tier = 4;
   return tier;
}
void M16()
{
   dirLock = !oneDir ? 0 : trdDir != 0 ? trdDir : suL >= 2 ? 1 : suS >= 2 ? -1 : 0;
   lockOkL = dirLock >= 0;
   lockOkS = dirLock <= 0;
   sesPts = !g_intra ? 3 : inSB || inNY || inLon ? 5 : inAsia ? 2 : 0;
   sesTierOK = !g_intra || sesPts >= 5;
   useAnchL = suL >= 2 && !isna(suLAnchorT) && !isna(suLAnchorB);
   useAnchS = suS >= 2 && !isna(suSAnchorT) && !isna(suSAnchorB);
   dmdTop = useAnchL ? suLAnchorT : nbTop;
   dmdBot = useAnchL ? suLAnchorB : nbBot;
   supTop = useAnchS ? suSAnchorT : nsTop;
   supBot = useAnchS ? suSAnchorB : nsBot;
   dmdFresh = useAnchL ? suL <= 3 : nbFresh;
   supFresh = useAnchS ? suS <= 3 : nsFresh;
   double c = C(0);
   inDemand   = useAnchL ? (L(0) <= dmdTop && c >= dmdBot) : (!isna(nbTop) && c <= nbTop);
   nearDemand = !isna(dmdTop) && !inDemand && MathAbs(c - dmdTop) <= POI_NEAR_ATR * atr;
   inSupply   = useAnchS ? (H(0) >= supBot && c <= supTop) : (!isna(nsBot) && c >= nsBot);
   nearSupply = !isna(supBot) && !inSupply && MathAbs(supBot - c) <= POI_NEAR_ATR * atr;
   poiConflictRaw = !isna(nbTop) && !isna(nsBot) && nbKind != "HTF" && nsKind != "HTF" && nsBot - nbTop <= atr;
   poiSideBias = htfB != 0 ? htfB : dirLock != 0 ? dirLock : extDir;
   poiBlockL = poiConflictRaw && !useAnchL && poiSideBias <= 0;
   poiBlockS = poiConflictRaw && !useAnchS && poiSideBias >= 0;
   poiConflict = poiConflictRaw && poiSideBias == 0;
   ctxLong  = MathMax(0, (htfB > 0 ? 10 : htfB == 0 ? 5 : 0) + (extDir > 0 ? 10 : 0) + sesPts + (rangeOK && pdPos < 0.5 ? 5 : 0) - (adrChaseL ? 10 : 0));
   ctxShort = MathMax(0, (htfB < 0 ? 10 : htfB == 0 ? 5 : 0) + (extDir < 0 ? 10 : 0) + sesPts + (rangeOK && pdPos >= 0.5 ? 5 : 0) - (adrChaseS ? 10 : 0));
   liqLong  = (sslInPlay ? 10 : 0) + (recentEngLo ? 5 : 0) + (sslInPlay && lastSslQualRaw >= 3 ? 5 : 0);
   liqShort = (bslInPlay ? 10 : 0) + (recentEngHi ? 5 : 0) + (bslInPlay && lastBslQualRaw >= 3 ? 5 : 0);
   poiLong  = poiBlockL ? 0 : (inDemand ? 10 : nearDemand ? 5 : 0) + ((inDemand || nearDemand) && dmdFresh ? 5 : 0) + (inOTEbuy ? 5 : 0);
   poiShort = poiBlockS ? 0 : (inSupply ? 10 : nearSupply ? 5 : 0) + ((inSupply || nearSupply) && supFresh ? 5 : 0) + (inOTEsell ? 5 : 0);
   bool cisdSepUp = recentCisdUp && (isnai(lastChUpBar) || lastCisdUpBar != lastChUpBar);
   bool cisdSepDn = recentCisdDn && (isnai(lastChDnBar) || lastCisdDnBar != lastChDnBar);
   trigLong  = (int)MathMin(20, MathRound(MathMax(MathMax(f_decay(lastMssUpBar, 12), f_decay(lastChUpBar, 9)), f_decay(lastBosUpBar, 5)) + (cisdSepUp ? f_decay(lastCisdUpBar, 8) : 0)));
   trigShort = (int)MathMin(20, MathRound(MathMax(MathMax(f_decay(lastMssDnBar, 12), f_decay(lastChDnBar, 9)), f_decay(lastBosDnBar, 5)) + (cisdSepDn ? f_decay(lastCisdDnBar, 8) : 0)));
   if(suL == 3 && !isnai(suLBar))
      trigLong = (int)MathMax(trigLong, MathRound((nzi(lastMssUpBar, -1) >= suLBar ? 12 : 9) * MathMax(0.5, 1.0 - (g_bi - suLBar) / ((sbTagL != 0 ? sbRetWait : retWait) + 1.0))));
   if(suS == 3 && !isnai(suSBar))
      trigShort = (int)MathMax(trigShort, MathRound((nzi(lastMssDnBar, -1) >= suSBar ? 12 : 9) * MathMax(0.5, 1.0 - (g_bi - suSBar) / ((sbTagS != 0 ? sbRetWait : retWait) + 1.0))));
   retestLong  = !useAnchL && !isna(dmdTop) && L(0) <= dmdTop && c >= dmdBot;
   retestShort = !useAnchS && !isna(supBot) && H(0) >= supBot && c <= supTop;
   execLong  = (retestLong ? 5 : 0) + (zoneBullConf ? 5 : 0);
   execShort = (retestShort ? 5 : 0) + (zoneBearConf ? 5 : 0);
   scoreBaseL = ctxLong  + (suLCont && suL >= 1 ? MathMax(liqLong, 10) : liqLong) + poiLong + trigLong + execLong;
   scoreBaseS = ctxShort + (suSCont && suS >= 1 ? MathMax(liqShort, 10) : liqShort) + poiShort + trigShort + execShort;
   sbPoolOkL = !sbPoolPref || lastSslKind >= 2;
   sbPoolOkS = !sbPoolPref || lastBslKind >= 2;
   sbCtxLong  = sbCtx ? sbWinPts + (sslInPlay && lastSslKind >= 2 ? 3 : 0) + (lastSslQualRaw >= 4 ? 3 : lastSslQualRaw >= 3 ? 2 : 0) + (recentMssUp ? 2 : recentChUp ? 1 : 0) + (sslInPlay && lastSslQual >= sbMinQual && sbPoolOkL ? 1 : 0) : 0;
   sbCtxShort = sbCtx ? sbWinPts + (bslInPlay && lastBslKind >= 2 ? 3 : 0) + (lastBslQualRaw >= 4 ? 3 : lastBslQualRaw >= 3 ? 2 : 0) + (recentMssDn ? 2 : recentChDn ? 1 : 0) + (bslInPlay && lastBslQual >= sbMinQual && sbPoolOkS ? 1 : 0) : 0;
   scoreLong  = MathMin(100, scoreBaseL + sbCtxLong);
   scoreShort = MathMin(100, scoreBaseS + sbCtxShort);
   tierLong  = f_tier(true);
   tierShort = f_tier(false);
   minRank = tierMode == TM_AP ? 4 : tierMode == TM_A ? 3 : tierMode == TM_B ? 2 : 1;
}

//+------------------------------------------------------------------+
//| MODULE 16B — liquidity trap engine                                |
//+------------------------------------------------------------------+
double p3PoolLow = NA, p3Swept = NA, ltBrkUpLvl = NA, p4Lvl = NA, p4HiMax = NA, p4HiMin = NA;
int    p3PoolBar = NAI, ltBrkUpBar = NAI, p4Stage = 0, p4Bar = NAI, p4WickCnt = 0, p1PrimeBar = NAI;
bool   p4Arm, ltCmpNow = false, ltCmpPrev = false, ltLowVol, ltCtxOKLong, ltCtxOKShort, obNearL, obNearS;
int    ltLState = 0, ltLBar = NAI, ltSState = 0, ltSBar = NAI, ltLRetBar = NAI, ltSRetBar = NAI;
double ltLLevel = NA, ltSLevel = NA, ltLDoneLvl = NA, ltSDoneLvl = NA;
string ltLPats = "", ltSPats = "", ltLReason = "", ltSReason = "", ltDbgMach = "", ltDbgLast = "";
bool   ltLRetOk = false, ltSRetOk = false;
bool   sigLTLong, sigLTShort, ltArmEvt, ltRetLEvt, ltRetSEvt;
int    ltLongScore, ltShortScore, ltClsFloor;

bool LoWickAt(const int k) { return Rng(k) > 0 && DnW(k) >= ltWickAtr * A(k) && DnW(k) >= ltWickRatio * Body(k) && DnW(k) > UpW(k); }
bool HiWickAt(const int k) { return Rng(k) > 0 && UpW(k) >= ltWickAtr * A(k) && UpW(k) >= ltWickRatio * Body(k) && UpW(k) > DnW(k); }
bool LtCmpAt(const int k)
{
   double sb = 0, mb = 0;
   int bc = 0;
   for(int q = k; q < k + ltCmpLen; q++) { sb += Body(q); mb = MathMax(mb, Body(q)); if(Bull(q)) bc++; }
   double a = A(k);
   return sb / ltCmpLen <= ltCmpSens * a && HH(ltCmpLen, k) - LL(ltCmpLen, k) <= ltCmpRngAtr * a && bc >= 1 && bc <= ltCmpLen - 1 && mb < dispFactor * a;
}
string f_addPat(const string acc, const bool c, const string nm) { return c ? (acc == "" ? nm : acc + "+" + nm) : acc; }
string f_ltCls(const int s) { return s >= ltScoreVHigh ? "VERY HIGH" : s >= ltScoreHigh ? "HIGH" : s >= ltScoreMed ? "MEDIUM" : "LOW"; }
string f_ltStTxt(const int s) { return s == 0 ? "idle" : s == 1 ? "WAITING" : "ACTIVE"; }
int f_ltScore(const bool isLong, const bool retOk, const int lState, const int sState)
{
   int s = 10;
   s += (isLong ? sslInPlay : bslInPlay) ? 20 : 0;
   bool strongRej = isLong ? (bullPin || (rng > 0 && dnWick >= 2 * body && dnWick >= minWickAtr * atr)) : (bearPin || (rng > 0 && upWick >= 2 * body && upWick >= minWickAtr * atr));
   s += strongRej ? 15 : 0;
   s += (isLong ? (recentMssUp || recentChUp) : (recentMssDn || recentChDn)) ? 20 : 0;
   s += (isLong ? (inDemand || nearDemand) : (inSupply || nearSupply)) ? 10 : 0;
   s += (isLong ? !isna(cFvgBTop) : !isna(cFvgSTop)) ? 10 : 0;
   s += (isLong ? obNearL : obNearS) ? 10 : 0;
   s += (isLong ? recentDispUp : recentDispDn) ? 10 : 0;
   s += retOk ? 10 : 0;
   s += (isLong ? htfB > 0 : htfB < 0) ? 15 : 0;
   s -= regime == "CHOP" ? 10 : 0;
   s -= (isLong ? extDir == -1 : extDir == 1) ? 20 : 0;
   s -= (isLong ? inOTEsell : inOTEbuy) ? 15 : 0;
   s -= ltLowVol ? 5 : 0;
   s -= !(isLong ? (sslInPlay || recentEngLo) : (bslInPlay || recentEngHi)) ? 10 : 0;
   s -= lState >= 1 && sState >= 1 ? 15 : 0;
   return MathMax(0, MathMin(100, s));
}
void M16B()
{
   double avg = 0; bool ok = g_bi >= 49;
   for(int k = 0; k < 50 && ok; k++) { double a = A(k); if(isna(a)) ok = false; else avg += a; }
   double ltAtrAvg = ok ? avg / 50 : NA;
   ltLowVol = ltAtrAvg > 0 && atr < 0.7 * ltAtrAvg;
   ltClsFloor = ltMinCls == LTM_VH ? ltScoreVHigh : ltMinCls == LTM_MED ? ltScoreMed : ltScoreHigh;
   bool ltCtxBase = !ltCtxGate || (kzOK && newsOK && (!useRegime || regime != "CHOP"));
   ltCtxOKLong  = ltCtxBase && (!ltCtxGate || biasOkL) && !(regime == "TRENDING" && extDir == -1 && lastSslQualRaw < 3);
   ltCtxOKShort = ltCtxBase && (!ltCtxGate || biasOkS) && !(regime == "TRENDING" && extDir == 1 && lastBslQualRaw < 3);
   bool ltHiWickBar = HiWickAt(0);
   ltCmpPrev = LtCmpAt(1);
   ltCmpNow  = LtCmpAt(0);
   // wick cluster (LT-3)
   int cnt = 0; double mn = NA, mx = NA;
   if(ltEnable && ltP3)
      for(int q = 1; q <= ltWickWin; q++)
         if(LoWickAt(q)) { cnt++; mn = isna(mn) ? L(q) : MathMin(mn, L(q)); mx = isna(mx) ? L(q) : MathMax(mx, L(q)); }
   bool p3ClusterOk = cnt >= ltWickMin && !isna(mn) && mx - mn <= ltClusterTol * atr;
   double p3ClusterLow = mn;
   if(ltEnable && ltP3)
   {
      if(!isna(p3PoolLow) && L(0) < p3PoolLow) { p3Swept = p3PoolLow; p3PoolLow = NA; }
      if(!isna(p3PoolLow) && g_bi - p3PoolBar > ltPoolLook) p3PoolLow = NA;
      bool freshOk = isna(p3Swept) || (!isna(p3ClusterLow) && MathAbs(p3ClusterLow - p3Swept) > ltClusterTol * atr);
      if(p3ClusterOk && L(0) > p3ClusterLow && freshOk) { p3PoolLow = p3ClusterLow; p3PoolBar = g_bi; }
   }
   if(ltEnable && brokeUp) { ltBrkUpBar = g_bi; ltBrkUpLvl = lastRes; }
   p4Arm = false;
   if(ltEnable && ltP4)
   {
      if(p4Stage == 1)
      {
         if(C(0) < p4Lvl || g_bi - p4Bar > ltPoolLook) p4Stage = 0;
         else
         {
            if(ltHiWickBar && H(0) <= H(1))
            {
               p4WickCnt++;
               p4HiMax = isna(p4HiMax) ? H(0) : MathMax(p4HiMax, H(0));
               p4HiMin = isna(p4HiMin) ? H(0) : MathMin(p4HiMin, H(0));
            }
            if(p4WickCnt >= ltWickMin && !isna(p4HiMax) && p4HiMax - p4HiMin <= ltClusterTol * atr) { p4Stage = 0; p4Arm = true; }
         }
      }
      if(p4Stage == 0 && !p4Arm && brokeUp && bullBar && body >= dispFactor * atr)
      { p4Stage = 1; p4Lvl = lastRes; p4Bar = g_bi; p4WickCnt = 0; p4HiMax = NA; p4HiMin = NA; }
   }
   // pattern arms
   if(ltEnable && ltP1 && ltCmpNow && !isna(lastRes) && C(0) < lastRes && lastRes - C(0) <= ltNearAtr * atr) p1PrimeBar = g_bi;
   bool ltWeakPoke = brokeUp && body <= ltBrkStr * atr;
   bool ltWeakWickUp = ltHiWickBar && body <= ltBrkStr * atr;
   bool ltWeakWickUp1 = HiWickAt(1) && Body(1) <= ltBrkStr * A(1);
   bool p1Arm = ltEnable && ltP1 && brokeUp && bullBar && body >= ltExpSens * atr && f_recent(p1PrimeBar, ltCmpLen * 2);
   bool p2Arm = ltEnable && ltP2 && ltWeakPoke && f_recent(lastDispDnBar, ltDispLook) && (ltCmpNow || ltCmpPrev) && C(0) > C(ltCmpLen);
   bool p3Arm = ltEnable && ltP3 && brokeUp && !isna(p3PoolLow) && C(0) - p3PoolLow <= SWEEP_CTX_ATR * atr;
   bool p5Arm = ltEnable && ltP5 && ((brokeUp && ltHiWickBar) || (f_recent(ltBrkUpBar, 3) && !isna(ltBrkUpLvl) && C(0) > ltBrkUpLvl && ltWeakWickUp && ltWeakWickUp1));
   bool p6Arm = ltEnable && ltP6 && ltWeakPoke && !isna(extSup) && (extDir == -1 || f_recent(lastDispDnBar, ltDispLook * 2)) && (isnai(lastDispUpBar) || g_bi - lastDispUpBar > ltCmpLen) && (ltCmpNow || ltCmpPrev);
   bool p7Arm = ltEnable && ltP7 && !isna(nsBot) && nsKind != "HTF" && H(0) >= nsBot && C(0) <= nsTop && (brokeUp || f_recent(ltBrkUpBar, 3)) && !isna(ltBrkUpLvl) && nsBot >= ltBrkUpLvl;
   // OB interaction
   obNearL = false; obNearS = false;
   if(ltEnable)
      for(int k = 0; k < ArraySize(zones); k++)
         if(zones[k].kind == "OB" && !zones[k].signaled)
         {
            if(!zones[k].isSupply && L(0) <= zones[k].top && C(0) >= zones[k].bot) obNearL = true;
            if(zones[k].isSupply && H(0) >= zones[k].bot && C(0) <= zones[k].top) obNearS = true;
         }
   // trap machines
   sigLTLong = false; sigLTShort = false; ltLongScore = 0; ltShortScore = 0;
   bool armL = false, armS = false; ltRetLEvt = false; ltRetSEvt = false;
   string lArm = f_addPat(f_addPat("", p1Arm, "LT-1"), p4Arm, "LT-4");
   string sArm = f_addPat(f_addPat(f_addPat(f_addPat(f_addPat("", p2Arm, "LT-2"), p3Arm, "LT-3"), p5Arm, "LT-5"), p6Arm, "LT-6"), p7Arm, "LT-7");
   double brkLvlNow = !isna(ltBrkUpLvl) && f_recent(ltBrkUpBar, 5) ? ltBrkUpLvl : lastRes;
   if(ltEnable)
   {
      // LONG
      if(ltLState == 1)
      {
         if(g_bi - ltLBar > ltWaitBars) { ltLState = 0; ltLReason = "expired (no confirmation)"; }
         else if(C(0) < ltLLevel - ltInvAtr * atr && bearBar && body >= dispFactor * atr) { ltLState = 0; ltLReason = "breakout failed (bear displacement below level)"; }
      }
      if(ltLState == 2 && g_bi - ltLBar > ltCd) ltLState = 0;
      double lLvlNow = p1Arm ? brkLvlNow : p4Lvl;
      if(lArm != "" && !isna(lLvlNow) && (isna(ltLDoneLvl) || MathAbs(lLvlNow - ltLDoneLvl) > ltClusterTol * atr))
      {
         if(ltLState == 0)
         { ltLState = 1; ltLBar = g_bi; ltLLevel = lLvlNow; ltLPats = lArm; ltLRetOk = false; ltLRetBar = NAI; armL = true; }
         else if(ltLState == 1)
         {
            if(p1Arm && !Contains(ltLPats, "LT-1")) ltLPats += "+LT-1";
            if(p4Arm && !Contains(ltLPats, "LT-4")) ltLPats += "+LT-4";
         }
      }
      if(ltLState == 1 && g_bi > ltLBar && !isna(ltLLevel) && L(0) <= ltLLevel + ltRetestAtr * atr && !ltLRetOk)
      { ltLRetOk = true; ltLRetBar = g_bi; ltRetLEvt = true; }
      bool confL = zoneBullConf || mssUp || chochUp || eChochUp;
      bool gatesL = (!ltReqSweep || sslInPlay) && (!ltReqMtf || biasOkL);
      if(ltLState == 1 && confL && gatesL && ltCtxOKLong && lockOkL && (!ltReqRetest || (ltLRetOk && g_bi > ltLRetBar)) && C(0) > ltLLevel - ltInvAtr * atr)
      {
         int scL = f_ltScore(true, ltLRetOk, ltLState, ltSState);
         if(scL >= ltClsFloor)
         {
            sigLTLong = true; ltLongScore = scL;
            slLTLong = MathMin(L(0), ltLLevel) - SL_PAD_ATR * atr;
            ltLDoneLvl = ltLLevel; ltLState = 2; ltLBar = g_bi;
         }
      }
      // SHORT
      if(ltSState == 1)
      {
         if(g_bi - ltSBar > ltWaitBars) { ltSState = 0; ltSReason = "expired (no confirmation)"; }
         else if(C(0) > ltSLevel + ltInvAtr * atr && bullBar && body >= dispFactor * atr) { ltSState = 0; ltSReason = "breakout accepted (bull displacement above level)"; }
      }
      if(ltSState == 2 && g_bi - ltSBar > ltCd) ltSState = 0;
      if(sArm != "" && !isna(brkLvlNow) && (isna(ltSDoneLvl) || MathAbs(brkLvlNow - ltSDoneLvl) > ltClusterTol * atr))
      {
         if(ltSState == 0)
         {
            ltSState = 1; ltSBar = g_bi; ltSLevel = brkLvlNow; ltSPats = sArm;
            ltSRetOk = p7Arm; ltSRetBar = p7Arm ? g_bi : NAI; armS = true;
         }
         else if(ltSState == 1)
         {
            if(p2Arm && !Contains(ltSPats, "LT-2")) ltSPats += "+LT-2";
            if(p3Arm && !Contains(ltSPats, "LT-3")) ltSPats += "+LT-3";
            if(p5Arm && !Contains(ltSPats, "LT-5")) ltSPats += "+LT-5";
            if(p6Arm && !Contains(ltSPats, "LT-6")) ltSPats += "+LT-6";
            if(p7Arm && !Contains(ltSPats, "LT-7")) ltSPats += "+LT-7";
            if(p7Arm) ltSRetOk = true;
            if(p7Arm && isnai(ltSRetBar)) ltSRetBar = g_bi;
         }
      }
      if(ltSState == 1 && g_bi > ltSBar && !isna(ltSLevel) && C(0) < ltSLevel && !ltSRetOk)
      { ltSRetOk = true; ltSRetBar = g_bi; ltRetSEvt = true; }
      bool confS = zoneBearConf || mssDn || chochDn || eChochDn;
      bool gatesS = (!ltReqSweep || bslInPlay) && (!ltReqMtf || biasOkS);
      bool needBelow = Contains(ltSPats, "LT-6");
      if(ltSState == 1 && confS && gatesS && ltCtxOKShort && lockOkS && (!ltReqRetest || (ltSRetOk && !isnai(ltSRetBar) && g_bi > ltSRetBar)) && (!needBelow || C(0) < ltSLevel))
      {
         int scS = f_ltScore(false, ltSRetOk, ltLState, ltSState);
         if(scS >= ltClsFloor)
         {
            sigLTShort = true; ltShortScore = scS;
            slLTShort = MathMax(H(0), ltSLevel) + SL_PAD_ATR * atr;
            ltSDoneLvl = ltSLevel; ltSState = 2; ltSBar = g_bi;
         }
      }
   }
   ltArmEvt = armL || armS;
   ltDbgMach = "L " + f_ltStTxt(ltLState) + (ltLState >= 1 && ltLPats != "" ? " [" + ltLPats + "]" : "") + " · S " + f_ltStTxt(ltSState) + (ltSState >= 1 && ltSPats != "" ? " [" + ltSPats + "]" : "");
   ltDbgLast = "L: " + (ltLReason != "" ? ltLReason : "—") + " · S: " + (ltSReason != "" ? ltSReason : "—");
   if(ltEnable && ltShowMarks && ltRetLEvt) Mark(true,  "◦", Col(COL_BULL, 20), tinySize + 2);
   if(ltEnable && ltShowMarks && ltRetSEvt) Mark(false, "◦", Col(COL_BEAR, 20), tinySize + 2);
}

//+------------------------------------------------------------------+
//| MODULE 17 — master setup state machine                            |
//+------------------------------------------------------------------+
bool   sigMCLong, sigMCShort, sbSigLong, sbSigShort, sbCeFillL, sbCeFillS, mcCeFillL, mcCeFillS, ceVoidL, ceVoidS;
double mcPlanLong, mcPlanShort;
int    sbShiftGL = 0, sbShiftGS = 0;
int    sbArmedSslBar = NAI, sbArmedBslBar = NAI, armedSslBar = NAI, armedBslBar = NAI, sbDoneWinL = 0, sbDoneWinS = 0;
double contArmLvlL = NA, contArmLvlS = NA;
bool   contTapL, contTapS, contTrendL, contTrendS, sbArmOkL, sbArmOkS;

void M17()
{
   sigMCLong = false; sigMCShort = false; mcPlanLong = NA; mcPlanShort = NA;
   sbSigLong = false; sbSigShort = false; sbCeFillL = false; sbCeFillS = false;
   mcCeFillL = false; mcCeFillS = false; ceVoidL = false; ceVoidS = false;
   bool mcCeOn = mcEntryMode != MC_PRX;
   double c = C(0);
   sbDoneWinL = sbCtxWin == 0 ? 0 : sbDoneWinL;
   sbDoneWinS = sbCtxWin == 0 ? 0 : sbDoneWinS;
   sbArmOkL = sbCtx && lastSslQual >= sbMinQual && sbPoolOkL && sbCtxWin != sbDoneWinL;
   sbArmOkS = sbCtx && lastBslQual >= sbMinQual && sbPoolOkS && sbCtxWin != sbDoneWinS;
   bool sbGraceL  = sbArmOkL && sslInPlay && f_recent(lastSslBar, SB_ARM_GRACE) && nzi(sbArmedSslBar, -1) != lastSslBar;
   bool sbGraceS  = sbArmOkS && bslInPlay && f_recent(lastBslBar, SB_ARM_GRACE) && nzi(sbArmedBslBar, -1) != lastBslBar;
   bool stdGraceL = armGrace > 0 && sslInPlay && f_recent(lastSslBar, armGrace) && nzi(armedSslBar, -1) != lastSslBar;
   bool stdGraceS = armGrace > 0 && bslInPlay && f_recent(lastBslBar, armGrace) && nzi(armedBslBar, -1) != lastBslBar;
   bool sbArmBarL = lastSslBar == g_bi || sbGraceL || stdGraceL;
   bool sbArmBarS = lastBslBar == g_bi || sbGraceS || stdGraceS;
   bool shiftUpOk = shiftSrc == SH_MSS ? mssUp : shiftSrc == SH_EXT ? (mssUp || eChochUp) : shiftSrc == SH_INT ? (mssUp || eChochUp || chochUp) : (mssUp || eChochUp || chochUp || cisdUp);
   bool shiftDnOk = shiftSrc == SH_MSS ? mssDn : shiftSrc == SH_EXT ? (mssDn || eChochDn) : shiftSrc == SH_INT ? (mssDn || eChochDn || chochDn) : (mssDn || eChochDn || chochDn || cisdDn);
   shiftUpOk = shiftUpOk || (mcDispShift && (chochUp || cisdUp) && bullBar && body >= dispFactor * atr && bullFVG);
   shiftDnOk = shiftDnOk || (mcDispShift && (chochDn || cisdDn) && bearBar && body >= dispFactor * atr && bearFVG);
   contTapL = g_htfLive && !isna(hPoiBTop) && L(0) <= hPoiBTop && c > hPoiBBot;
   contTapS = g_htfLive && !isna(hPoiSTop) && H(0) >= hPoiSBot && c < hPoiSTop;
   contTrendL = htfB > 0 && hsDir > 0 && bD > 0;
   contTrendS = htfB < 0 && hsDir < 0 && bD < 0;
   bool contArmL = contOn && htfB > 0 && hsDir > 0 && contTapL && !bslInPlay && nz(contArmLvlL, 0) != hPoiBBot;
   bool contArmS = contOn && htfB < 0 && hsDir < 0 && contTapS && !sslInPlay && nz(contArmLvlS, 0) != hPoiSTop;
   bool sbDispNow = body >= sbDispAtr * atr;
   bool sbShiftUp = mssUp || eChochUp || ((chochUp || cisdUp) && bullBar && sbDispNow);
   bool sbShiftDn = mssDn || eChochDn || ((chochDn || cisdDn) && bearBar && sbDispNow);
   int sbLiqWL = sbTagL != 0 ? sbLiqWait : liqWait, sbPoiWL = sbTagL != 0 ? sbPoiWait : poiWait, sbRetWL = sbTagL != 0 ? sbRetWait : retWait;
   int sbLiqWS = sbTagS != 0 ? sbLiqWait : liqWait, sbPoiWS = sbTagS != 0 ? sbPoiWait : poiWait, sbRetWS = sbTagS != 0 ? sbRetWait : retWait;
   bool sbKillL = sbTagL != 0 && ((sbTagL == 1 && sbEndLOEvt) || (sbTagL == 2 && sbEndAMEvt) || (sbTagL == 3 && sbEndPMEvt));
   bool sbKillS = sbTagS != 0 && ((sbTagS == 1 && sbEndLOEvt) || (sbTagS == 2 && sbEndAMEvt) || (sbTagS == 3 && sbEndPMEvt));
   bool sbFvgOkL = !isna(cFvgBTop) && cFvgBDisp && cFvgBTop - cFvgBBot >= sbFvgMinAtr * atr;
   bool sbFvgOkS = !isna(cFvgSTop) && cFvgSDisp && cFvgSTop - cFvgSBot >= sbFvgMinAtr * atr;

   // ---------------- LONG machine ----------------
   sbTagL    = suL == 0 ? 0 : sbTagL;
   suLCont   = suL == 0 ? false : suLCont;
   sbShiftGL = suL == 0 ? 0 : sbShiftGL;
   if(suL >= 1)
   {
      if(!isna(suLSweepExt) && c < suLSweepExt) { suL = 0; suLReason = suLCont ? "HTF POI violated" : "sweep undone"; }
      else if(suL <= 2 && !isna(suLSweepLvl) && c < suLSweepLvl - NEAR_LVL_ATR * atr) { suL = 0; suLReason = "sweep reclaim lost"; }
      else if(bearBar && body >= dispFactor * atr && suL <= 3 && !(suL == 3 && !isna(suLAnchorB) && c > suLAnchorB)) { suL = 0; suLReason = "opposing displacement"; }
      else if(suL == 1 && bslSweep && lastBslQual >= 2) { suL = 0; suLReason = "range swept both ways"; }
   }
   suLSweepExt = suL >= 1 && suL <= 2 ? PMin(suLSweepExt, L(0)) : suLSweepExt;
   if(suL >= 2 && isnai(suLFvgBar) && !isna(suLAnchorB) && c < suLAnchorB) { suL = 0; suLReason = "POI violated (own anchor)"; }
   if(htfProtInval && suL >= 1 && suL <= 3 && !isna(hsProtLo) && c < hsProtLo) { suL = 0; suLReason = "HTF protected low broken"; }
   if(sbKillAtEnd && sbKillL && suL >= 1 && suL <= 3) { suL = 0; suLReason = "SB window closed"; }
   bool expL = (suL == 1 && g_bi - suLBar > sbLiqWL) || (suL == 2 && g_bi - suLBar > sbPoiWL) || (suL == 3 && g_bi - suLBar > sbRetWL);
   if(expL) { suLReason = suL == 1 ? "sweep expired (no POI tap)" : suL == 2 ? "POI tap expired (no shift)" : "retest window expired"; suL = 0; }
   bool stdArmL = sslInPlay && sbArmBarL && (lastSslQual >= minArmQual || sbArmOkL) && (!armNeedHtf || armBiasL);
   if(suL == 0 && (stdArmL || contArmL) && lockOkL)
   {
      bool cL = contArmL && !stdArmL;
      bool chopBlock = useRegime && regime == "CHOP" && !instSweepL && !(sbArmOkL && sbChopBypass) && !(cL && contTrendL);
      if(!chopBlock)
      {
         suL = 1; suLBar = g_bi;
         suLSweepLvl = cL ? hPoiBBot : lastSslLvl;
         suLSweepExt = cL ? hPoiBBot - NEAR_LVL_ATR * atr : lastSslExt;
         suLAnchorT = NA; suLAnchorB = NA; suLFvgBar = NAI;
         suLCont = cL;
         contArmLvlL = cL ? hPoiBBot : contArmLvlL;
         sbTagL = sbArmOkL && !cL ? sbCtxWin : 0;
         sbShiftGL = 0;
         armedSslBar = cL ? armedSslBar : lastSslBar;
         if(sbArmOkL && !cL) sbArmedSslBar = lastSslBar;
      }
   }
   if(suL == 1 && sslInPlay && (sbTagL != 0 ? (sbReqMss ? mssUp : sbShiftUp) : (fastShift && shiftUpOk)))
   {
      suL = 3; suLBar = g_bi; sbShiftGL = mssUp ? 2 : 1;
      suLAnchorT = NA; suLAnchorB = NA; suLFvgBar = NAI;
   }
   if(suL == 1)
   {
      bool tapZone = inDemand && retestLong && !poiBlockL;
      bool tapOte  = poiSrc != PS_ZONE && inOTEbuy;
      bool tapHtf  = contTapL;
      if(tapZone || tapOte || tapHtf)
      {
         suL = 2; suLBar = g_bi;
         suLAnchorT = tapZone ? nbTop : suLAnchorT;
         suLAnchorB = tapZone ? nbBot : suLAnchorB;
      }
   }
   if(suL == 2 && (sbTagL != 0 ? (sbReqMss ? mssUp : sbShiftUp) : shiftUpOk))
   {
      suL = 3; suLBar = g_bi; sbShiftGL = mssUp ? 2 : 1;
      if(!isna(cFvgBTop) && !isnai(cFvgBBar) && cFvgBBar >= suLBar && (sbTagL == 0 ? (!mcFvgDisp || cFvgBDisp) : sbFvgOkL))
      { suLAnchorT = cFvgBTop; suLAnchorB = cFvgBBot; suLFvgBar = cFvgBBar; }
   }
   if(suL == 3)
   {
      if(isnai(suLFvgBar) && !isna(cFvgBTop) && !isnai(cFvgBBar) && cFvgBBar >= suLBar && (sbTagL == 0 ? (!mcFvgDisp || cFvgBDisp) : sbFvgOkL))
      { suLAnchorT = cFvgBTop; suLAnchorB = cFvgBBot; suLFvgBar = cFvgBBar; }
      if(!isna(suLAnchorT))
      {
         double ceL = (suLAnchorT + suLAnchorB) / 2;
         bool ripeL = g_bi > suLBar && (isnai(suLFvgBar) || g_bi > suLFvgBar);
         bool sbSetL = sbTagL != 0 && !isnai(suLFvgBar) && (sbWinNow == sbTagL || !sbKillAtEnd);
         bool sbRejL = bullPin || bullEngulf || ifcBull || cisdUp;
         bool sbCeTapL = loA <= ceL;
         bool sbPrxTapL = L(0) <= suLAnchorT && sbRejL;
         bool sbLocOkL = (!sbReqHtf || htfB > 0 || (htfB == 0 && biasOkL)) && (!sbReqPD || (sbPdOK && sbPdPos < 0.5));
         bool sbEnterL = sbSetL && ripeL && sbLocOkL && (sbCeTapL || (sbEntryMode != SBE_CE && sbPrxTapL));
         bool mcCeTapL = mcCeOn && sbTagL == 0 && !isnai(suLFvgBar) && loA <= ceL;
         bool mcCnfOkL = !mcStrictCnf || (c >= ceL && c >= L(0) + (1 - STRONG_CLOSE_PCT) * rng);
         bool mcCnfTapL = mcEntryMode != MC_CE && L(0) <= suLAnchorT && zoneBullConf && mcCnfOkL;
         bool stdEnterL = sbTagL == 0 && ripeL && (mcCeTapL || mcCnfTapL);
         if(c < suLAnchorB)
         {
            ceVoidL = (sbEnterL && sbCeTapL) || (stdEnterL && mcCeTapL);
            suL = 0;
            suLReason = sbTagL != 0 ? "SB FVG violated" : "anchor FVG violated";
         }
         else if((sbEnterL || stdEnterL) && c > suLAnchorB)
         {
            sigMCLong = true;
            sbSigLong = sbEnterL;
            sbCeFillL = sbEnterL && sbCeTapL;
            mcCeFillL = stdEnterL && mcCeTapL;
            mcPlanLong = sbCeFillL || mcCeFillL ? ceL : MathMin(c, suLAnchorT) + spr;
            double slAnchL = MathMin(L(0), suLAnchorB) - SL_PAD_ATR * atr;
            double slRaidL = MathMin(MathMin(L(0), suLAnchorB), nz(suLSweepExt, L(0))) - SL_PAD_ATR * atr;
            slMCLong = !stopTier || maxRiskAtr == 0 || mcPlanLong - slRaidL <= maxRiskAtr * atr ? slRaidL : slAnchL;
            suL = 4; suLBar = g_bi;
         }
      }
   }

   // ---------------- SHORT machine ----------------
   sbTagS    = suS == 0 ? 0 : sbTagS;
   suSCont   = suS == 0 ? false : suSCont;
   sbShiftGS = suS == 0 ? 0 : sbShiftGS;
   if(suS >= 1)
   {
      if(!isna(suSSweepExt) && c > suSSweepExt) { suS = 0; suSReason = suSCont ? "HTF POI violated" : "sweep undone"; }
      else if(suS <= 2 && !isna(suSSweepLvl) && c > suSSweepLvl + NEAR_LVL_ATR * atr) { suS = 0; suSReason = "sweep reclaim lost"; }
      else if(bullBar && body >= dispFactor * atr && suS <= 3 && !(suS == 3 && !isna(suSAnchorT) && c < suSAnchorT)) { suS = 0; suSReason = "opposing displacement"; }
      else if(suS == 1 && sslSweep && lastSslQual >= 2) { suS = 0; suSReason = "range swept both ways"; }
   }
   suSSweepExt = suS >= 1 && suS <= 2 ? PMax(suSSweepExt, H(0)) : suSSweepExt;
   if(suS >= 2 && isnai(suSFvgBar) && !isna(suSAnchorT) && c > suSAnchorT) { suS = 0; suSReason = "POI violated (own anchor)"; }
   if(htfProtInval && suS >= 1 && suS <= 3 && !isna(hsProtHi) && c > hsProtHi) { suS = 0; suSReason = "HTF protected high broken"; }
   if(sbKillAtEnd && sbKillS && suS >= 1 && suS <= 3) { suS = 0; suSReason = "SB window closed"; }
   bool expS = (suS == 1 && g_bi - suSBar > sbLiqWS) || (suS == 2 && g_bi - suSBar > sbPoiWS) || (suS == 3 && g_bi - suSBar > sbRetWS);
   if(expS) { suSReason = suS == 1 ? "sweep expired (no POI tap)" : suS == 2 ? "POI tap expired (no shift)" : "retest window expired"; suS = 0; }
   bool stdArmS = bslInPlay && sbArmBarS && (lastBslQual >= minArmQual || sbArmOkS) && (!armNeedHtf || armBiasS);
   if(suS == 0 && (stdArmS || contArmS) && lockOkS)
   {
      bool cS = contArmS && !stdArmS;
      bool chopBlock = useRegime && regime == "CHOP" && !instSweepS && !(sbArmOkS && sbChopBypass) && !(cS && contTrendS);
      if(!chopBlock)
      {
         suS = 1; suSBar = g_bi;
         suSSweepLvl = cS ? hPoiSTop : lastBslLvl;
         suSSweepExt = cS ? hPoiSTop + NEAR_LVL_ATR * atr : lastBslExt;
         suSAnchorT = NA; suSAnchorB = NA; suSFvgBar = NAI;
         suSCont = cS;
         contArmLvlS = cS ? hPoiSTop : contArmLvlS;
         sbTagS = sbArmOkS && !cS ? sbCtxWin : 0;
         sbShiftGS = 0;
         armedBslBar = cS ? armedBslBar : lastBslBar;
         if(sbArmOkS && !cS) sbArmedBslBar = lastBslBar;
      }
   }
   if(suS == 1 && bslInPlay && (sbTagS != 0 ? (sbReqMss ? mssDn : sbShiftDn) : (fastShift && shiftDnOk)))
   {
      suS = 3; suSBar = g_bi; sbShiftGS = mssDn ? 2 : 1;
      suSAnchorT = NA; suSAnchorB = NA; suSFvgBar = NAI;
   }
   if(suS == 1)
   {
      bool tapZone = inSupply && retestShort && !poiBlockS;
      bool tapOte  = poiSrc != PS_ZONE && inOTEsell;
      bool tapHtf  = contTapS;
      if(tapZone || tapOte || tapHtf)
      {
         suS = 2; suSBar = g_bi;
         suSAnchorT = tapZone ? nsTop : suSAnchorT;
         suSAnchorB = tapZone ? nsBot : suSAnchorB;
      }
   }
   if(suS == 2 && (sbTagS != 0 ? (sbReqMss ? mssDn : sbShiftDn) : shiftDnOk))
   {
      suS = 3; suSBar = g_bi; sbShiftGS = mssDn ? 2 : 1;
      if(!isna(cFvgSTop) && !isnai(cFvgSBar) && cFvgSBar >= suSBar && (sbTagS == 0 ? (!mcFvgDisp || cFvgSDisp) : sbFvgOkS))
      { suSAnchorT = cFvgSTop; suSAnchorB = cFvgSBot; suSFvgBar = cFvgSBar; }
   }
   if(suS == 3)
   {
      if(isnai(suSFvgBar) && !isna(cFvgSTop) && !isnai(cFvgSBar) && cFvgSBar >= suSBar && (sbTagS == 0 ? (!mcFvgDisp || cFvgSDisp) : sbFvgOkS))
      { suSAnchorT = cFvgSTop; suSAnchorB = cFvgSBot; suSFvgBar = cFvgSBar; }
      if(!isna(suSAnchorB))
      {
         double ceS = (suSAnchorT + suSAnchorB) / 2;
         bool ripeS = g_bi > suSBar && (isnai(suSFvgBar) || g_bi > suSFvgBar);
         bool sbSetS = sbTagS != 0 && !isnai(suSFvgBar) && (sbWinNow == sbTagS || !sbKillAtEnd);
         bool sbRejS = bearPin || bearEngulf || ifcBear || cisdDn;
         bool sbCeTapS = H(0) >= ceS;
         bool sbPrxTapS = H(0) >= suSAnchorB && sbRejS;
         bool sbLocOkS = (!sbReqHtf || htfB < 0 || (htfB == 0 && biasOkS)) && (!sbReqPD || (sbPdOK && sbPdPos >= 0.5));
         bool sbEnterS = sbSetS && ripeS && sbLocOkS && (sbCeTapS || (sbEntryMode != SBE_CE && sbPrxTapS));
         bool mcCeTapS = mcCeOn && sbTagS == 0 && !isnai(suSFvgBar) && H(0) >= ceS;
         bool mcCnfOkS = !mcStrictCnf || (c <= ceS && c <= H(0) - (1 - STRONG_CLOSE_PCT) * rng);
         bool mcCnfTapS = mcEntryMode != MC_CE && H(0) >= suSAnchorB && zoneBearConf && mcCnfOkS;
         bool stdEnterS = sbTagS == 0 && ripeS && (mcCeTapS || mcCnfTapS);
         if(c > suSAnchorT)
         {
            ceVoidS = (sbEnterS && sbCeTapS) || (stdEnterS && mcCeTapS);
            suS = 0;
            suSReason = sbTagS != 0 ? "SB FVG violated" : "anchor FVG violated";
         }
         else if((sbEnterS || stdEnterS) && c < suSAnchorT)
         {
            sigMCShort = true;
            sbSigShort = sbEnterS;
            sbCeFillS = sbEnterS && sbCeTapS;
            mcCeFillS = stdEnterS && mcCeTapS;
            mcPlanShort = sbCeFillS || mcCeFillS ? ceS : MathMax(c, suSAnchorB);
            double slAnchS = MathMax(H(0), suSAnchorT) + SL_PAD_ATR * atr;
            double slRaidS = MathMax(MathMax(H(0), suSAnchorT), nz(suSSweepExt, H(0))) + SL_PAD_ATR * atr;
            slMCShort = !stopTier || maxRiskAtr == 0 || slRaidS - mcPlanShort <= maxRiskAtr * atr ? slRaidS : slAnchS;
            suS = 4; suSBar = g_bi;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| MODULE 18 — final gates · 18B — trade viability                   |
//+------------------------------------------------------------------+
int    lastLongSigBar = NAI, lastShortSigBar = NAI, trdToday = 0, lossToday = 0, mcTierL, mcTierS, finalTierL, finalTierS;
bool   longCdOK, shortCdOK, chopOKL, chopOKS, sbOnlyOK, govTrdOK, govLossOK, govOK, dowOK, mcPdOKL, mcPdOKS, longOK, shortOK;
bool   anyLong, anyShort, sbFireL, sbFireS, mcFillNext, engFillNext, planOK;
int    gateScoreL, gateScoreS;
string gateKillL, gateKillS, planKill;
double planEntry, planSL, planTP2;

int f_mcTier(const bool isLong)
{
   int t = 3;
   bool qualOk  = !(isLong ? suLCont : suSCont) && (isLong ? lastSslQualRaw : lastBslQualRaw) >= 3;
   bool htfOk   = isLong ? htfB > 0 : htfB < 0;
   bool shiftOk = (isLong ? sbShiftGL : sbShiftGS) >= 2;
   bool pdOkL   = sbTagL != 0 ? (sbPdOK && sbPdPos < 0.5)  : (rangeOK && pdPos < 0.5);
   bool pdOkS   = sbTagS != 0 ? (sbPdOK && sbPdPos >= 0.5) : (rangeOK && pdPos >= 0.5);
   bool pdOk    = isLong ? pdOkL : pdOkS;
   bool poolOk  = (isLong ? lastSslKind : lastBslKind) >= 2;
   bool adrOk   = !(isLong ? adrChaseL : adrChaseS);
   if(qualOk && htfOk && shiftOk && pdOk && poolOk && sesTierOK && adrOk) t = 4;
   return t;
}
string f_gateKill(const bool isLong)
{
   int  sc = isLong ? gateScoreL : gateScoreS;
   bool cd = isLong ? longCdOK : shortCdOK;
   bool ch = isLong ? chopOKL : chopOKS;
   bool lk = isLong ? lockOkL : lockOkS;
   bool pd = isLong ? mcPdOKL : mcPdOKS;
   if(isLong ? longOK : shortOK) return "gate: tier " + f_tierTxt(isLong ? mcTierL : mcTierS) + " below floor";
   if(minScore > 0 && sc < minScore) return "gate: score " + IntegerToString(sc) + " < " + IntegerToString(minScore);
   if(!govOK) return !govTrdOK ? "gate: daily signal limit" : "gate: daily loss limit";
   if(!cd) return "gate: cooldown";
   if(!newsOK) return "gate: volatility window";
   if(!dowOK) return "gate: day filter";
   if(!ch) return "gate: chop";
   if(!lk) return isLong ? "gate: short narrative live" : "gate: long narrative live";
   if(!pd) return isLong ? "gate: premium — wrong side of the dealing range" : "gate: discount — wrong side of the dealing range";
   return "gate: bias / session";
}
void M18()
{
   longCdOK  = masterCd == 0 || isnai(lastLongSigBar)  || g_bi - lastLongSigBar  > masterCd;
   shortCdOK = masterCd == 0 || isnai(lastShortSigBar) || g_bi - lastShortSigBar > masterCd;
   chopOKL = !useRegime || regime != "CHOP" || instSweepL || (sbEnable && sbChopBypass && sbSigLong) || (suLCont && contTrendL);
   chopOKS = !useRegime || regime != "CHOP" || instSweepS || (sbEnable && sbChopBypass && sbSigShort) || (suSCont && contTrendS);
   sbOnlyOK = !(sbEnable && sbOnly && g_intra) || sbCtx;
   if(newDay) { trdToday = 0; lossToday = 0; }
   govTrdOK  = !useGov || !g_intra || maxTrdDay == 0 || trdToday < maxTrdDay;
   govLossOK = !useGov || !g_intra || maxLossDay == 0 || lossToday < maxLossDay;
   govOK = govTrdOK && govLossOK;
   dowOK = !g_intra || Contains(tradeDays, IntegerToString(NyDow(gT[g_bi])));
   gateScoreL = scoreBaseL;
   gateScoreS = scoreBaseS;
   mcPdOKL = !mcReqPD || !rangeOK || !rangeHolds || pdPos < 0.5 || (mcPdWaive && htfB > 0 && extDir > 0);
   mcPdOKS = !mcReqPD || !rangeOK || !rangeHolds || pdPos >= 0.5 || (mcPdWaive && htfB < 0 && extDir < 0);
   longOK  = biasOkL && lockOkL && kzOK && newsOK && dowOK && longCdOK && chopOKL && sbOnlyOK && govOK && mcPdOKL && (minScore == 0 || gateScoreL >= minScore);
   shortOK = biasOkS && lockOkS && kzOK && newsOK && dowOK && shortCdOK && chopOKS && sbOnlyOK && govOK && mcPdOKS && (minScore == 0 || gateScoreS >= minScore);
   longOK  = longOK  || (sbSigLong  && biasOkL && lockOkL && kzOK && newsOK && dowOK && chopOKL && sbOnlyOK && govOK && (minScore == 0 || gateScoreL >= minScore));
   shortOK = shortOK || (sbSigShort && biasOkS && lockOkS && kzOK && newsOK && dowOK && chopOKS && sbOnlyOK && govOK && (minScore == 0 || gateScoreS >= minScore));
   mcTierL = f_mcTier(true);
   mcTierS = f_mcTier(false);
   int sbTierMin = sbMinTier == SBT_AP ? 4 : 3;
   sigMCLong  = sigMCLong  && longOK  && mcTierL >= (sbSigLong  ? MathMax(minRank, sbTierMin) : minRank);
   sigMCShort = sigMCShort && shortOK && mcTierS >= (sbSigShort ? MathMax(minRank, sbTierMin) : minRank);
   if(!sigMCLong)  { sbSigLong = false;  sbCeFillL = false; mcCeFillL = false; mcPlanLong = NA; }
   if(!sigMCShort) { sbSigShort = false; sbCeFillS = false; mcCeFillS = false; mcPlanShort = NA; }
   gateKillL = suL == 4 && suLBar == g_bi && !sigMCLong  ? f_gateKill(true)  : "";
   gateKillS = suS == 4 && suSBar == g_bi && !sigMCShort ? f_gateKill(false) : "";
   if(gateKillL != "") { suL = 3; suLReason = gateKillL; }
   if(gateKillS != "") { suS = 3; suSReason = gateKillS; }
   bool sbLive = (sbEnable && sbTagL != 0 && suL >= 2) || (sbEnable && sbTagS != 0 && suS >= 2);
   int  engRank = sbLive && sbSuppress == SUP_DOWN ? MathMin(4, minRank + 1) : minRank;
   bool engMute = sbLive && sbSuppress == SUP_SUPP;
   bool engOKL = longOK  && tierLong  >= engRank && !engMute;
   bool engOKS = shortOK && tierShort >= engRank && !engMute;
   sigSDLong = sigSDLong && engOKL; sig3Long = sig3Long && engOKL; sig4Long = sig4Long && engOKL; sigTLLong = sigTLLong && engOKL;
   sigCRTLong = sigCRTLong && engOKL; sigTBSLong = sigTBSLong && engOKL; sigHCrtLong = sigHCrtLong && engOKL; sigHTbsLong = sigHTbsLong && engOKL;
   sigLTLong = sigLTLong && engOKL;
   sigSDShort = sigSDShort && engOKS; sig3Short = sig3Short && engOKS; sig4Short = sig4Short && engOKS; sigTLShort = sigTLShort && engOKS;
   sigCRTShort = sigCRTShort && engOKS; sigTBSShort = sigTBSShort && engOKS; sigHCrtShort = sigHCrtShort && engOKS; sigHTbsShort = sigHTbsShort && engOKS;
   sigLTShort = sigLTShort && engOKS;
   anyLong  = sigMCLong  || sigSDLong  || sig3Long  || sig4Long  || sigTLLong  || sigCRTLong  || sigTBSLong  || sigHCrtLong  || sigHTbsLong  || sigLTLong;
   anyShort = sigMCShort || sigSDShort || sig3Short || sig4Short || sigTLShort || sigCRTShort || sigTBSShort || sigHCrtShort || sigHTbsShort || sigLTShort;
   if(anyLong && anyShort)
   {
      int rkL = sigMCLong  ? (sbSigLong  ? 3 : 2) : 1;
      int rkS = sigMCShort ? (sbSigShort ? 3 : 2) : 1;
      if(rkL > rkS)
      {
         anyShort = false; sigMCShort = false; sbSigShort = false;
         if(suS == 4 && suSBar == g_bi) { suS = 0; suSReason = "conflict — higher-rank long won the bar"; }
      }
      else if(rkS > rkL)
      {
         anyLong = false; sigMCLong = false; sbSigLong = false;
         if(suL == 4 && suLBar == g_bi) { suL = 0; suLReason = "conflict — higher-rank short won the bar"; }
      }
      else { anyLong = false; anyShort = false; }
   }
   if(ltEnable && ltVeto && ltSState == 1 && !sigMCLong)  anyLong  = false;
   if(ltEnable && ltVeto && ltLState == 1 && !sigMCShort) anyShort = false;

   // ---- MODULE 18B viability
   double selSLLong  = sigMCLong ? slMCLong : sigSDLong ? slSDLong : sigCRTLong ? slCRTLong : sigTBSLong ? slTBSLong : sigHCrtLong ? slHCrtLong : sigHTbsLong ? slHTbsLong :
                       sig3Long ? sl3Long : sig4Long ? sl4Long : sigTLLong ? slTLLong : sigLTLong ? slLTLong : NA;
   double selSLShort = sigMCShort ? slMCShort : sigSDShort ? slSDShort : sigCRTShort ? slCRTShort : sigTBSShort ? slTBSShort : sigHCrtShort ? slHCrtShort : sigHTbsShort ? slHTbsShort :
                       sig3Short ? sl3Short : sig4Short ? sl4Short : sigTLShort ? slTLShort : sigLTShort ? slLTShort : NA;
   planEntry = anyLong ? nz(mcPlanLong, C(0)) : anyShort ? nz(mcPlanShort, C(0)) : NA;
   planSL = NA; planTP2 = NA; planOK = true; planKill = "";
   if(anyLong || anyShort)
   {
      double fallbackL = MathMin(L(0), L(1)) - SL_PAD_ATR * atr;
      double fallbackS = MathMax(H(0), H(1)) + SL_PAD_ATR * atr;
      double slL = !isna(selSLLong)  && selSLLong  < planEntry ? selSLLong  : fallbackL;
      double slS = !isna(selSLShort) && selSLShort > planEntry ? selSLShort : fallbackS;
      planSL = anyLong ? slL : slS + spr;
      bool ceLimitFill = sbCeFillL || sbCeFillS || mcCeFillL || mcCeFillS;
      if(slipGuard > 0 && !ceLimitFill && MathAbs(C(0) - planEntry) > slipGuard * atr)
      {
         planOK = false;
         planKill = "entry slipped (close " + fmtG(MathRound(MathAbs(C(0) - planEntry) / atr * 100) / 100, 2) + " ATR from the plan price)";
      }
      double planRisk = MathAbs(planEntry - planSL);
      if(planOK && maxRiskAtr > 0 && planRisk > maxRiskAtr * atr)
      {
         if(riskMode == RM_CLAMP) { planSL = anyLong ? planEntry - maxRiskAtr * atr : planEntry + maxRiskAtr * atr; planRisk = maxRiskAtr * atr; }
         else { planOK = false; planKill = "risk " + fmtG(MathRound(planRisk / atr * 100) / 100, 2) + " ATR exceeds the cap"; }
      }
      if(planOK)
      {
         double wantTP2 = anyLong ? planEntry + rrMult * planRisk : planEntry - rrMult * planRisk;
         if(anyLong && !isna(nsBot) && nsBot > planEntry) wantTP2 = MathMin(wantTP2, nsBot);
         if(anyShort && !isna(nbTop) && nbTop < planEntry) wantTP2 = MathMax(wantTP2, nbTop);
         planTP2 = wantTP2;
         double cost = costTicks * g_tick;
         double rr = planRisk + cost > 0 ? MathMax(0, MathAbs(wantTP2 - planEntry) - cost) / (planRisk + cost) : 0;
         if(minRR > 0 && rr < minRR)
         {
            planOK = false;
            planKill = "reward blocked — only " + fmtG(MathRound(rr * 100) / 100, 2) + "R net to the first opposing POI";
         }
      }
      if(planOK && planRisk <= 0) { planOK = false; planKill = "degenerate risk"; }
   }
   if(!planOK)
   {
      if(anyLong && suL == 4 && suLBar == g_bi)  { suL = 0; suLReason = planKill; }
      if(anyShort && suS == 4 && suSBar == g_bi) { suS = 0; suSReason = planKill; }
      anyLong = false; anyShort = false; sigMCLong = false; sigMCShort = false; sbSigLong = false; sbSigShort = false;
   }
   sbFireL = anyLong  && sigMCLong  && sbSigLong;
   sbFireS = anyShort && sigMCShort && sbSigShort;
   sbDoneWinL = sbFireL ? sbTagL : sbDoneWinL;
   sbDoneWinS = sbFireS ? sbTagS : sbDoneWinS;
   mcFillNext  = (sigMCLong || sigMCShort) && !(sbSigLong || sbSigShort) && !(mcCeFillL || mcCeFillS);
   engFillNext = ((anyLong || anyShort) && !(sigMCLong || sigMCShort)) || mcFillNext;
   finalTierL = sigMCLong  ? MathMax(tierLong,  mcTierL) : tierLong;
   finalTierS = sigMCShort ? MathMax(tierShort, mcTierS) : tierShort;
   if(sigCRTLong && anyLong)   lastCrtLongBar  = g_bi;
   if(sigCRTShort && anyShort) lastCrtShortBar = g_bi;
   if(sigTBSLong && anyLong)   lastTbsLongBar  = g_bi;
   if(sigTBSShort && anyShort) lastTbsShortBar = g_bi;
   if(anyLong)  lastLongSigBar  = g_bi;
   if(anyShort) lastShortSigBar = g_bi;
}

//+------------------------------------------------------------------+
//| MODULE 19 — TP / SL + ACTIVE trade tracking + exit journal        |
//+------------------------------------------------------------------+
int    cntA = 0, cntAp = 0, cntLong = 0, cntShort = 0, cntTP1 = 0, cntTP2 = 0, cntSL = 0, cntBE = 0, cntTP3 = 0, cntSbEnt = 0;
int    cntExp = 0, cntUntracked = 0, cntVoid = 0, trdBar = NAI, pendDir = 0;
double pendSL = NA, trdMfe = 0, trdMae = 0, sumR = 0;
bool   sbTimeExitEvt, sbStructExitEvt, sbBeEvt, trdOutEvt, trackNew;
string exitMsg = "";
double entryP, slP, tp1P, tp2P, tp3P;
int    pCntTP1 = 0, pCntTP2 = 0, pCntSL = 0;

double f_tight(const double sl, const double lvl, const int d) { return d == 1 ? MathMax(sl, lvl) : MathMin(sl, lvl); }
double f_nearAbove(const double best, const double cand, const double ref) { return !isna(cand) && cand >= ref && (isna(best) || cand < best) ? cand : best; }
double f_nearBelow(const double best, const double cand, const double ref) { return !isna(cand) && cand <= ref && (isna(best) || cand > best) ? cand : best; }

void M19()
{
   sbTimeExitEvt = false; sbStructExitEvt = false; sbBeEvt = false;
   int cSL0 = cntSL, cBE0 = cntBE, cTP30 = cntTP3;
   // FIX-T7 deferred engine fill at this bar's open
   if(pendDir != 0)
   {
      bool pendFilled = false;
      if(trdDir == 0 && !(sigMCLong || sigMCShort))
      {
         double pEnt = pendDir == 1 ? O(0) + spr : O(0);
         double pRisk = MathAbs(pEnt - pendSL);
         double pTp2raw = pendDir == 1 ? pEnt + rrMult * pRisk : pEnt - rrMult * pRisk;
         double pTp2 = pendDir == 1 && !isna(nsBot) && nsBot > pEnt ? MathMin(pTp2raw, nsBot) :
                       pendDir == -1 && !isna(nbTop) && nbTop < pEnt ? MathMax(pTp2raw, nbTop) : pTp2raw;
         double pCost = costTicks * g_tick;
         double pRR = pRisk + pCost > 0 ? MathMax(0, MathAbs(pTp2 - pEnt) - pCost) / (pRisk + pCost) : 0;
         bool pSlipOK = slipGuard == 0 || MathAbs(O(0) - C(1)) <= slipGuard * atr;
         bool pRiskOK = maxRiskAtr == 0 || pRisk <= maxRiskAtr * atr;
         bool pRrOK   = minRR == 0 || pRR >= minRR;
         if(pRisk > 0 && (pendDir == 1 ? O(0) > pendSL : O(0) + spr < pendSL) && pSlipOK && pRiskOK && pRrOK)
         {
            double pM = MathMax(3.0, rrMult + 1);
            trdEntry = pEnt; trdSL = pendSL;
            trdTP1 = pendDir == 1 ? pEnt + pRisk : pEnt - pRisk;
            trdTP2 = pTp2;
            trdTP3 = pendDir == 1 ? pEnt + pM * pRisk : pEnt - pM * pRisk;
            trdDir = pendDir; trdBar = g_bi; trdTp1Hit = false; trdTp2Hit = false; trdIsSb = false;
            trdSbWin = 0; trdShiftG = 0; trdLiqTgt = NA; trdMfe = 0; trdMae = 0;
            pendFilled = true;
         }
      }
      cntUntracked = pendFilled ? cntUntracked : cntUntracked + 1;
      pendDir = 0;
   }
   int  trdDirIn = trdDir;
   bool trdProt  = trdDir == 1 ? trdSL >= trdEntry : trdDir == -1 && trdSL <= trdEntry;
   if(trdDir != 0)
   {
      int d = trdDir;
      double adv = d == 1 ? L(0) : hiA;
      double fav = d == 1 ? H(0) : loA;
      if((trdSL - adv) * d >= 0)
      {
         cntSL += trdProt ? 0 : 1;
         cntBE += trdProt ? 1 : 0;
         lossToday += trdProt ? 0 : 1;
         trdDir = 0;
      }
      else
      {
         if(!trdTp1Hit && (fav - trdTP1) * d >= 0)
         {
            trdTp1Hit = true; cntTP1++;
            trdSL = f_tight(trdSL, trdEntry + d * MathMax(sbBeBuf * atr, SB_BE_TP1_PCT * MathAbs(trdTP1 - trdEntry)), d);
            sbBeEvt = true;
         }
         if(trdTp1Hit && !trdTp2Hit && (fav - trdTP2) * d >= 0)
         {
            trdTp2Hit = true; cntTP2++;
            trdSL  = !trdIsSb && nonSbTp3 ? f_tight(trdSL, trdTP1, d) : trdSL;
            trdDir = trdIsSb || nonSbTp3 ? d : 0;
         }
         double prot = d == 1 ? protLowE : protHighE;
         double cap  = d == 1 ? MathMin(MathMin(L(0), L(1)), C(0)) - SL_PAD_ATR * atr : MathMax(MathMax(H(0), H(1)), C(0)) + SL_PAD_ATR * atr;
         if(trdIsSb && trdTp2Hit && sbTrail && !isna(prot))
            trdSL = f_tight(trdSL, d == 1 ? MathMin(prot - SL_PAD_ATR * atr, cap) : MathMax(prot + SL_PAD_ATR * atr, cap), d);
         if(trdDir != 0 && (trdIsSb || trdTp2Hit) && (fav - trdTP3) * d >= 0) { cntTP3++; trdDir = 0; }
         bool sbWEnd = trdSbWin == 1 ? sbEndLOEvt : trdSbWin == 2 ? sbEndAMEvt : trdSbWin == 3 ? sbEndPMEvt : false;
         sbStructExitEvt = trdIsSb && trdDir != 0 && sbStructEx && (d == 1 ? mssDn || (trdShiftG <= 1 && (cisdDn || chochDn || eChochDn)) : mssUp || (trdShiftG <= 1 && (cisdUp || chochUp || eChochUp)));
         trdDir = sbStructExitEvt ? 0 : trdDir;
         sbTimeExitEvt = trdIsSb && trdDir != 0 && sbTimeExit && sbWEnd && !trdTp1Hit;
         trdDir = sbTimeExitEvt && sbTimeMode == SBX_FULL ? 0 : trdDir;
         trdSL  = sbTimeExitEvt && sbTimeMode != SBX_FULL ? f_tight(trdSL, trdEntry, d) : trdSL;
      }
   }
   bool trdExp = trdDir != 0 && maxTrdBars > 0 && !isnai(trdBar) && g_bi - trdBar > maxTrdBars;
   if(trdExp) { cntExp++; trdDir = 0; }
   if(trdDirIn != 0)
   {
      trdMfe = MathMax(trdMfe, trdDirIn == 1 ? H(0) - trdEntry : trdEntry - loA);
      trdMae = MathMax(trdMae, trdDirIn == 1 ? trdEntry - L(0) : hiA - trdEntry);
   }
   trdOutEvt = trdDirIn != 0 && trdDir == 0;
   double trdR0 = MathAbs(trdTP1 - trdEntry);
   string exTag = cntSL > cSL0 ? "SL" : cntBE > cBE0 ? "BE" : cntTP3 > cTP30 ? "TP3" : sbStructExitEvt ? "STR" : trdExp ? "EXP" : sbTimeExitEvt ? "TIME" : "TP2";
   double exPx = exTag == "SL" || exTag == "BE" ? (trdDirIn == 1 ? MathMin(trdSL, O(0)) : MathMax(trdSL, O(0) + spr)) :
                 exTag == "TP3" ? trdTP3 : exTag == "TP2" ? trdTP2 : C(0) + (trdDirIn == 1 ? 0 : spr);
   double rOut = trdOutEvt && trdR0 > 0 ? (exPx - trdEntry) * trdDirIn / trdR0 : 0.0;
   sumR += rOut;
   exitMsg = trdOutEvt ? "LQEXIT|" + _Symbol + "|" + TfName((ENUM_TIMEFRAMES)Period()) + "|" + (trdDirIn == 1 ? "L" : "S") + "|" + (trdIsSb ? "SB" : "NS") + "|" + exTag +
             "|R" + fmtG(rOut, 2) + "|b" + IntegerToString(g_bi - trdBar) +
             "|mfe" + fmtG(trdR0 > 0 ? trdMfe / trdR0 : 0.0, 2) + "|mae" + fmtG(trdR0 > 0 ? trdMae / trdR0 : 0.0, 2) +
             "|E" + fmtPx(trdEntry) + "|X" + fmtPx(exPx) + "|ΣR" + fmtG(sumR, 2) : "";
   sbSetLive = (sbTagL != 0 && suL >= 1) || (sbTagS != 0 && suS >= 1) || (trdDir != 0 && trdIsSb);
   suL = suL == 4 && trdDir == 0 && !sigMCLong  ? 0 : suL;
   suS = suS == 4 && trdDir == 0 && !sigMCShort ? 0 : suS;
   if(sigMCLong && suL == 4 && suLBar == g_bi && trdDir != 0)  suLReason = "entry not tracked — tracker busy (stage stays ACTIVE)";
   if(sigMCShort && suS == 4 && suSBar == g_bi && trdDir != 0) suSReason = "entry not tracked — tracker busy (stage stays ACTIVE)";
   bool ceVoid = trdDir == 0 && ((ceVoidL && longOK) || (ceVoidS && shortOK));
   if(ceVoid) { cntVoid++; lossToday++; }
   trackNew = (anyLong || anyShort) && trdDir == 0;
   entryP = NA; slP = NA; tp1P = NA; tp2P = NA; tp3P = NA;
   if(anyLong || anyShort)
   {
      entryP = planEntry;
      slP = planSL;
      double risk = MathAbs(entryP - slP);
      tp1P = anyLong ? entryP + risk : entryP - risk;
      tp2P = nz(planTP2, anyLong ? entryP + rrMult * risk : entryP - rrMult * risk);
      double tp3Mult = MathMax(3.0, rrMult + 1);
      tp3P = anyLong ? entryP + tp3Mult * risk : entryP - tp3Mult * risk;
      if(tpMode == TP_LIQ)
      {
         double tgt = NA;
         if(anyLong)
         {
            if(!isna(nsBot) && nsBot > entryP) tgt = nsBot;
            else if(!isna(lastRes) && lastRes > entryP) tgt = lastRes;
            if(!isna(tgt) && tgt - entryP >= rrMult * risk) tp3P = tgt;
         }
         else
         {
            if(!isna(nbTop) && nbTop < entryP) tgt = nbTop;
            else if(!isna(lastSup) && lastSup < entryP) tgt = lastSup;
            if(!isna(tgt) && entryP - tgt >= rrMult * risk) tp3P = tgt;
         }
      }
      trdLiqTgt = trackNew ? NA : trdLiqTgt;
      if(sbLiqTgt && (sbFireL || sbFireS))
      {
         double need = anyLong ? entryP + rrMult * risk : entryP - rrMult * risk;
         double lt = NA;
         if(anyLong)
         {
            lt = f_nearAbove(lt, nsBot, need); lt = f_nearAbove(lt, asiaHiLvl, need); lt = f_nearAbove(lt, lonHiLvl, need);
            lt = f_nearAbove(lt, nyHiLvl, need); lt = f_nearAbove(lt, pdh, need); lt = f_nearAbove(lt, pwh, need);
         }
         else
         {
            lt = f_nearBelow(lt, nbTop, need); lt = f_nearBelow(lt, asiaLoLvl, need); lt = f_nearBelow(lt, lonLoLvl, need);
            lt = f_nearBelow(lt, nyLoLvl, need); lt = f_nearBelow(lt, pdl, need); lt = f_nearBelow(lt, pwl, need);
         }
         tp3P = isna(lt) ? tp3P : lt;
         trdLiqTgt = trackNew ? lt : trdLiqTgt;
      }
      bool deferFill = engFillNext;
      if(trackNew && deferFill) { pendDir = anyLong ? 1 : -1; pendSL = slP; }
      if(trackNew && !deferFill)
      {
         trdEntry = entryP; trdSL = slP; trdTP1 = tp1P; trdTP2 = tp2P; trdTP3 = tp3P;
         trdDir = anyLong ? 1 : -1; trdBar = g_bi; trdTp1Hit = false; trdTp2Hit = false;
         trdIsSb = sbFireL || sbFireS;
         trdSbWin = sbFireL ? sbTagL : sbFireS ? sbTagS : 0;
         trdShiftG = sbFireL ? sbShiftGL : sbFireS ? sbShiftGS : 0;
         trdMfe = 0; trdMae = 0;
      }
      cntUntracked = trackNew ? cntUntracked : cntUntracked + 1;
      cntSbEnt = (sbFireL || sbFireS) && trackNew ? cntSbEnt + 1 : cntSbEnt;
      cntLong  = anyLong ? cntLong + 1 : cntLong;
      cntShort = anyShort ? cntShort + 1 : cntShort;
      trdToday++;
      cntAp += (anyLong && finalTierL >= 4 ? 1 : 0) + (anyShort && finalTierS >= 4 ? 1 : 0);
      cntA  += (anyLong && finalTierL == 3 ? 1 : 0) + (anyShort && finalTierS == 3 ? 1 : 0);
   }
}

//+------------------------------------------------------------------+
//| MODULE 20 — visualization                                         |
//+------------------------------------------------------------------+
// bgcolor layers per bar (colour + transparency, 100 = none): killzones · SB band · volatility window
color  g_bgC1[], g_bgC2[], g_bgC3[];
int    g_bgT1[], g_bgT2[], g_bgT3[];
// persistent drawings
string tpEntryLn = "", tpSlLn = "", tpTp1Ln = "", tpTp2Ln = "", tpTp3Ln = "";
string tpEntryLb = "", tpSlLb = "", tpTp1Lb = "", tpTp2Lb = "", tpTp3Lb = "";
string poiBuyBx = "", poiSellBx = "", mcAnchBxL = "", mcAnchBxS = "", sbCeLnL = "", sbCeLnS = "", sbTgtLn = "", sbTgtLb = "";
string nbLn = "", nsLn = "", nbBx = "", nsBx = "", nbLb = "", nsLb = "";

string f_join(const string acc, const string part) { return acc == "" ? part : acc + "\n" + part; }
double LotsFor(const double dist)
{
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0 || dist <= 0) return 0;
   return riskMoney / (dist / ts * tv);
}

void Visual()
{
   int i = g_bi;
   BRes[i] = showLevels && !isna(lastRes) ? lastRes : EMPTY_VALUE;
   BSup[i] = showLevels && !isna(lastSup) ? lastSup : EMPTY_VALUE;
   BPLo[i] = showStruct && showProt && !isna(protLowE) ? protLowE : EMPTY_VALUE;
   BPHi[i] = showStruct && showProt && !isna(protHighE) ? protHighE : EMPTY_VALUE;
   BPdh[i] = showPdwl && !isna(pdh) ? pdh : EMPTY_VALUE;
   BPdl[i] = showPdwl && !isna(pdl) ? pdl : EMPTY_VALUE;
   BPwh[i] = showPdwl && !isna(pwh) ? pwh : EMPTY_VALUE;
   BPwl[i] = showPdwl && !isna(pwl) ? pwl : EMPTY_VALUE;
   // sweep marks (◆ swing · ◈ engineered pool · ◇ PD/PW) + trendline / session marks
   if(showSweeps && sslSweep) Mark(true,  "◆", COL_BULL, mkSize);
   if(showSweeps && bslSweep) Mark(false, "◆", COL_BEAR, mkSize);
   if(showSweeps && eqlSwept) Mark(true,  "◈", COL_BULL, mkSize);
   if(showSweeps && eqhSwept) Mark(false, "◈", COL_BEAR, mkSize);
   if(showSweeps && (pdlSweep || pwlSweep)) Mark(true,  "◇", Col(COL_BULL, 20), mkSize);
   if(showSweeps && (pdhSweep || pwhSweep)) Mark(false, "◇", Col(COL_BEAR, 20), mkSize);
   if(showTL && tlUpBreak) Mark(true,  "✕", Col(COL_BEAR, 20), mkSize);
   if(showTL && tlDnBreak) Mark(false, "✕", Col(COL_BULL, 20), mkSize);
   if(showSesHL && sesHiSwept) Mark(false, "▿", Col(COL_BEAR, 15), mkSize);
   if(showSesHL && sesLoSwept) Mark(true,  "▵", Col(COL_BULL, 15), mkSize);
   // bgcolor: killzones · Silver Bullet band · volatility window
   g_bgT1[i] = 100; g_bgT2[i] = 100; g_bgT3[i] = 100;
   if(paintKZ && g_intra)
   {
      if(inAsia)     { g_bgC1[i] = CL_PURPLE; g_bgT1[i] = 95; }
      else if(inLon) { g_bgC1[i] = CL_BLUE;   g_bgT1[i] = 94; }
      else if(inNY)  { g_bgC1[i] = CL_ORANGE; g_bgT1[i] = 94; }
   }
   if((paintKZ || (sbOn && sbPaint)) && g_intra && inSB)
   { g_bgC2[i] = CL_TEAL; g_bgT2[i] = sbWinNow == 2 ? 86 : sbWinNow == 3 ? 90 : sbWinNow == 1 ? 92 : 94; }
   if(paintNews && g_intra && inNews) { g_bgC3[i] = CL_RED; g_bgT3[i] = 90; }
   // merged signal labels (one per direction per bar, tier-tagged)
   string lt = "", st = "";
   if(sigMCLong)   lt = f_join(lt, sbFireL ? "◆ SB " + f_sbWinTxt(sbTagL) + " · " + (sbCeFillL ? "CE" : "edge") + " " + f_tierTxt(mcTierL) : "◉ SETUP " + f_tierTxt(mcTierL));
   if(sigSDLong)   lt = f_join(lt, "Demand 50%" + (inOTEbuy ? " +OTE" : ""));
   if(sig3Long)    lt = f_join(lt, "IB break");
   if(sig4Long)    lt = f_join(lt, "Doji rev");
   if(sigTLLong)   lt = f_join(lt, "TL sweep");
   if(sigCRTLong)  lt = f_join(lt, "CRT");
   if(sigTBSLong)  lt = f_join(lt, "TSoup");
   if(sigHCrtLong) lt = f_join(lt, "HTF " + g_htfName + " CRT");
   if(sigHTbsLong) lt = f_join(lt, "HTF " + g_htfName + " TSoup");
   if(sigLTLong && ltShowSig) lt = f_join(lt, "◬ TRAP " + ltLPats + " · " + f_ltCls(ltLongScore) + (ltLRetOk ? " · retest✓" : ""));
   if(sigMCShort)   st = f_join(st, sbFireS ? "◆ SB " + f_sbWinTxt(sbTagS) + " · " + (sbCeFillS ? "CE" : "edge") + " " + f_tierTxt(mcTierS) : "◉ SETUP " + f_tierTxt(mcTierS));
   if(sigSDShort)   st = f_join(st, "Supply 50%" + (inOTEsell ? " +OTE" : ""));
   if(sig3Short)    st = f_join(st, "IB break");
   if(sig4Short)    st = f_join(st, "Doji rev");
   if(sigTLShort)   st = f_join(st, "TL sweep");
   if(sigCRTShort)  st = f_join(st, "CRT");
   if(sigTBSShort)  st = f_join(st, "TSoup");
   if(sigHCrtShort) st = f_join(st, "HTF " + g_htfName + " CRT");
   if(sigHTbsShort) st = f_join(st, "HTF " + g_htfName + " TSoup");
   if(sigLTShort && ltShowSig) st = f_join(st, "◬ TRAP " + ltSPats + " · " + f_ltCls(ltShortScore) + (ltSRetOk ? " · failed-break✓" : ""));
   if(anyLong && lt != "")
      LblNew(i, L(0), f_tierTxt(finalTierL) + " · " + IntegerToString(scoreLong) + (sbCtxLong > 0 ? " (base " + IntegerToString(scoreBaseL) + ")" : "") + "\n" + lt,
             LM_UP, Col(sbFireL ? CL_TEAL : COL_BULL, uiTrans), CL_WHITE, sigSize);
   if(anyShort && st != "")
      LblNew(i, H(0), f_tierTxt(finalTierS) + " · " + IntegerToString(scoreShort) + (sbCtxShort > 0 ? " (base " + IntegerToString(scoreBaseS) + ")" : "") + "\n" + st,
             LM_DOWN, Col(sbFireS ? CL_TEAL : COL_BEAR, uiTrans), CL_WHITE, sigSize);
   if(sbOn && sbTimeExitEvt)   Chip(false, "◆ SB time exit" + (sbTimeMode == SBX_FULL ? "" : " · stop → BE"), Col(CL_TEAL, 25), CL_WHITE, mkSize);
   if(sbOn && sbStructExitEvt) Chip(false, "◆ SB structure exit", Col(CL_TEAL, 25), CL_WHITE, mkSize);
   // entry / SL / TP ladder of the most recent signal
   bool planDraw  = showTrade && (anyLong || anyShort) && !isna(entryP);
   bool planClear = trdDir == 0 && pendDir == 0 && !(anyLong || anyShort) && tpEntryLn != "";
   if(planDraw || planClear)
   {
      LineDel(tpEntryLn); LineDel(tpSlLn); LineDel(tpTp1Ln); LineDel(tpTp2Ln); LineDel(tpTp3Ln);
      LblDel(tpEntryLb); LblDel(tpSlLb); LblDel(tpTp1Lb); LblDel(tpTp2Lb); LblDel(tpTp3Lb);
      tpEntryLn = ""; tpSlLn = ""; tpTp1Ln = ""; tpTp2Ln = ""; tpTp3Ln = "";
      tpEntryLb = ""; tpSlLb = ""; tpTp1Lb = ""; tpTp2Lb = ""; tpTp3Lb = "";
   }
   if(planDraw)
   {
      int x2 = i + TRADE_BARS;
      tpEntryLn = LineNew(i, entryP, x2, entryP, CL_GRAY, STYLE_DASH, 1, false);
      tpSlLn    = LineNew(i, slP,    x2, slP,    COL_BEAR, STYLE_DASH, 1, false);
      tpTp1Ln   = LineNew(i, tp1P,   x2, tp1P,   Col(COL_BULL, 45), STYLE_DASH, 1, false);
      tpTp2Ln   = LineNew(i, tp2P,   x2, tp2P,   Col(COL_BULL, 20), STYLE_DASH, 1, false);
      tpTp3Ln   = LineNew(i, tp3P,   x2, tp3P,   COL_BULL, STYLE_DASH, 1, false);
      double rrCost = costTicks * g_tick;
      string rrTxt = fmtG(MathRound(MathMax(0, MathAbs(tp2P - entryP) - rrCost) / MathMax(MathAbs(entryP - slP) + rrCost, g_tick) * 10) / 10, 1);
      double lots = riskMoney > 0 ? LotsFor(MathMax(MathAbs(entryP - slP) + rrCost, g_tick)) : 0;
      tpEntryLb = LblNew(x2, entryP, "E " + fmtPx(entryP) + " · RR " + rrTxt + " (plan, not promise)" + (engFillNext ? " · engine fill = next open" : "") +
                         (riskMoney > 0 ? " · ≈" + fmtG(MathRound(lots * 100) / 100, 2) + " lots" : ""), LM_LEFT, Col(CL_GRAY, 20), CL_WHITE, drawSize);
      tpSlLb  = LblNew(x2, slP,  "SL " + fmtPx(slP), LM_LEFT, Col(COL_BEAR, 20), CL_WHITE, drawSize);
      tpTp1Lb = LblNew(x2, tp1P, "TP1 " + fmtPx(tp1P) + (tp1Pct > 0 ? " · " + IntegerToString(tp1Pct) + "%" : ""), LM_LEFT, Col(COL_BULL, 45), CL_WHITE, drawSize);
      tpTp2Lb = LblNew(x2, tp2P, "TP2 " + fmtPx(tp2P), LM_LEFT, Col(COL_BULL, 30), CL_WHITE, drawSize);
      tpTp3Lb = LblNew(x2, tp3P, "TP3 " + fmtPx(tp3P), LM_LEFT, Col(COL_BULL, 15), CL_WHITE, drawSize);
   }
}

// last-bar drawings: HTF POI boxes, machine anchors, SB CE / target, NEXT levels, extend + focus
string f_nextLvlTxt(const string side, const int score, const string kind, const double lo, const double hi)
{
   double c = C(0);
   string pct = !nextLvlPct || c <= 0 ? "" : c >= lo && c <= hi ? " (INSIDE)" :
                " (" + fmtG(MathAbs((lo + hi) / 2 - c) / c * 100, 2) + "% " + ((lo + hi) / 2 > c ? "above" : "below") + ")";
   return side + " T" + IntegerToString(score) + (kind != "SD" && kind != "" ? " " + kind : "") + " " + fmtPx(lo) + "-" + fmtPx(hi) + pct;
}
void LastBarDraw()
{
   int i = g_bi;
   BoxDel(poiBuyBx); BoxDel(poiSellBx); BoxDel(mcAnchBxL); BoxDel(mcAnchBxS);
   poiBuyBx = ""; poiSellBx = ""; mcAnchBxL = ""; mcAnchBxS = "";
   bool mcCeOn = mcEntryMode != MC_PRX;
   if(showPoi && !isna(hPoiBTop))
      poiBuyBx = BoxNew(i - 10, hPoiBTop, i + TRADE_BARS, hPoiBBot, Col(COL_BULL, 50), STYLE_DASH, COL_BULL, 95,
                        "HTF " + g_htfName + " demand" + (nzi(hPoiBIn, 0) == 0 ? " · fresh" : " · ×" + IntegerToString(nzi(hPoiBIn, 0))), COL_BULL, drawSize, HA_RIGHT, VA_CENTER);
   if(showPoi && !isna(hPoiSTop))
      poiSellBx = BoxNew(i - 10, hPoiSTop, i + TRADE_BARS, hPoiSBot, Col(COL_BEAR, 50), STYLE_DASH, COL_BEAR, 95,
                         "HTF " + g_htfName + " supply" + (nzi(hPoiSIn, 0) == 0 ? " · fresh" : " · ×" + IntegerToString(nzi(hPoiSIn, 0))), COL_BEAR, drawSize, HA_RIGHT, VA_CENTER);
   if(suL == 3 && !isna(suLAnchorT))
   {
      color ac = sbTagL != 0 ? CL_TEAL : COL_BULL;
      bool showCe = sbTagL != 0 || (mcCeOn && !isnai(suLFvgBar));
      mcAnchBxL = BoxNew(nzi(suLFvgBar, i - 5), suLAnchorT, i + TRADE_BARS, suLAnchorB, Col(ac, 20), STYLE_SOLID, ac, 90,
                         (sbTagL != 0 ? "◆ SB CE " : mcCeOn && !isnai(suLFvgBar) ? "◉ CE " : "◉ anchor") + (showCe ? fmtPx((suLAnchorT + suLAnchorB) / 2) : "") + " · await retest",
                         ac, drawSize, HA_RIGHT, VA_CENTER);
   }
   if(suS == 3 && !isna(suSAnchorT))
   {
      color ac = sbTagS != 0 ? CL_TEAL : COL_BEAR;
      bool showCe = sbTagS != 0 || (mcCeOn && !isnai(suSFvgBar));
      mcAnchBxS = BoxNew(nzi(suSFvgBar, i - 5), suSAnchorT, i + TRADE_BARS, suSAnchorB, Col(ac, 20), STYLE_SOLID, ac, 90,
                         (sbTagS != 0 ? "◆ SB CE " : mcCeOn && !isnai(suSFvgBar) ? "◉ CE " : "◉ anchor") + (showCe ? fmtPx((suSAnchorT + suSAnchorB) / 2) : "") + " · await retest",
                         ac, drawSize, HA_RIGHT, VA_CENTER);
   }
   LineDel(sbCeLnL); LineDel(sbCeLnS); LineDel(sbTgtLn); LblDel(sbTgtLb);
   sbCeLnL = ""; sbCeLnS = ""; sbTgtLn = ""; sbTgtLb = "";
   if(sbOn && sbShowPlan && suL == 3 && sbTagL != 0 && !isna(suLAnchorT))
      sbCeLnL = LineNew(nzi(suLFvgBar, i - 5), (suLAnchorT + suLAnchorB) / 2, i + TRADE_BARS, (suLAnchorT + suLAnchorB) / 2, Col(CL_TEAL, 10), STYLE_SOLID, 2, false);
   if(sbOn && sbShowPlan && suS == 3 && sbTagS != 0 && !isna(suSAnchorT))
      sbCeLnS = LineNew(nzi(suSFvgBar, i - 5), (suSAnchorT + suSAnchorB) / 2, i + TRADE_BARS, (suSAnchorT + suSAnchorB) / 2, Col(CL_TEAL, 10), STYLE_SOLID, 2, false);
   if(sbOn && sbShowPlan && trdIsSb && trdDir != 0 && !isna(trdLiqTgt))
   {
      sbTgtLn = LineNew(i - 5, trdLiqTgt, i + TRADE_BARS, trdLiqTgt, Col(CL_TEAL, 25), STYLE_DOT, 1, false);
      sbTgtLb = LblNew(i + TRADE_BARS, trdLiqTgt, "◆ SB target " + fmtPx(trdLiqTgt), LM_LEFT, Col(CL_TEAL, 30), CL_WHITE, drawSize);
   }
   // NEXT BUY / NEXT SELL
   LineDel(nbLn); LineDel(nsLn); BoxDel(nbBx); BoxDel(nsBx); LblDel(nbLb); LblDel(nsLb);
   nbLn = ""; nsLn = ""; nbBx = ""; nsBx = ""; nbLb = ""; nsLb = "";
   int x1 = i - nextLvlBack, x2 = i + TRADE_BARS, xLn = i - MathMin(nextLvlBack, 18);
   if(showNextLvl && !isna(nbTop) && !isna(nbBot))
   {
      double lvl = nextLvlAnchor == NX_CE ? (nbTop + nbBot) / 2 : nbTop;
      if(nextLvlBox) nbBx = BoxNew(x1, nbTop, x2, nbBot, Col(COL_BULL, 70), STYLE_DOT, COL_BULL, 92, "", COL_BULL, drawSize, HA_RIGHT, VA_CENTER);
      nbLn = LineNew(xLn, lvl, x2, lvl, Col(COL_BULL, 10), STYLE_DASH, 1, false);
      nbLb = LblNew(xLn + 1, lvl, f_nextLvlTxt("BUY", nbScore, nbKind, nbBot, nbTop) + (nbFresh ? " ·fresh" : ""), LM_RIGHT, Col(COL_BULL, 10), CL_WHITE, drawSize);
   }
   if(showNextLvl && !isna(nsTop) && !isna(nsBot))
   {
      double lvl = nextLvlAnchor == NX_CE ? (nsTop + nsBot) / 2 : nsBot;
      if(nextLvlBox) nsBx = BoxNew(x1, nsTop, x2, nsBot, Col(COL_BEAR, 70), STYLE_DOT, COL_BEAR, 92, "", COL_BEAR, drawSize, HA_RIGHT, VA_CENTER);
      nsLn = LineNew(xLn, lvl, x2, lvl, Col(COL_BEAR, 10), STYLE_DASH, 1, false);
      nsLb = LblNew(xLn + 13, lvl, f_nextLvlTxt("SELL", nsScore, nsKind, nsBot, nsTop) + (nsFresh ? " ·fresh" : ""), LM_RIGHT, Col(COL_BEAR, 10), CL_WHITE, drawSize);
   }
   // extend live drawings + focus mode
   double focusHi = C(0) + focusAtr * atr, focusLo = C(0) - focusAtr * atr;
   for(int k = 0; k < ArraySize(zones); k++)
   {
      BoxSetRight(zones[k].bx, i + 1);
      if(focusMode)
      {
         bool far = zones[k].bot > focusHi || zones[k].top < focusLo;
         color zc = zones[k].isSupply ? COL_BEAR : COL_BULL;
         BoxSetBg(zones[k].bx, zc, far ? 100 : 93);
         BoxSetBorder(zones[k].bx, far ? clrNONE : Col(zc, 55));
         BoxShowText(zones[k].bx, !far);
      }
   }
   for(int k = 0; k < ArraySize(eqhLns); k++) LineSetX2(eqhLns[k], i + 1);
   for(int k = 0; k < ArraySize(eqlLns); k++) LineSetX2(eqlLns[k], i + 1);
   for(int k = 0; k < ArraySize(bullFvgs); k++)
   {
      if(bullFvgs[k].bx == "") continue;
      BoxSetRight(bullFvgs[k].bx, i + 1);
      if(focusMode && (bullFvgs[k].bot > focusHi || bullFvgs[k].top < focusLo)) { BoxSetBg(bullFvgs[k].bx, COL_BULL, 100); BoxSetBorder(bullFvgs[k].bx, clrNONE); BoxShowText(bullFvgs[k].bx, false); }
   }
   for(int k = 0; k < ArraySize(bearFvgs); k++)
   {
      if(bearFvgs[k].bx == "") continue;
      BoxSetRight(bearFvgs[k].bx, i + 1);
      if(focusMode && (bearFvgs[k].bot > focusHi || bearFvgs[k].top < focusLo)) { BoxSetBg(bearFvgs[k].bx, COL_BEAR, 100); BoxSetBorder(bearFvgs[k].bx, clrNONE); BoxShowText(bearFvgs[k].bx, false); }
   }
}

//+------------------------------------------------------------------+
//| MODULE 21 / 22 — dashboard + debug tables                         |
//+------------------------------------------------------------------+
void ScrRect(const string n, const ENUM_BASE_CORNER corner, const int x, const int y, const int w, const int h, const color bg, const color bd)
{
   if(ObjectFind(0, n) < 0)
   {
      ObjectCreate(0, n, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, n, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, n, OBJPROP_BACK, false);
   }
   ObjectSetInteger(0, n, OBJPROP_CORNER, corner);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_COLOR, bd);
   ObjectSetInteger(0, n, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
}
void ScrLabel(const string n, const ENUM_BASE_CORNER corner, const int x, const int y, const string txt, const color c, const int fs)
{
   if(ObjectFind(0, n) < 0)
   {
      ObjectCreate(0, n, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, n, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   }
   ObjectSetString(0, n, OBJPROP_FONT, i_font);
   ObjectSetInteger(0, n, OBJPROP_CORNER, corner);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, fs);
   ObjectSetInteger(0, n, OBJPROP_COLOR, c);
   ObjectSetString(0, n, OBJPROP_TEXT, txt == "" ? " " : txt);
   ObjectSetInteger(0, n, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
}
int TxtW(const string s, const int fs) { TextSetFont(i_font, -fs * 10); uint w = 0, h = 0; TextGetSize(s == "" ? " " : s, w, h); return (int)w; }
int TxtH(const int fs)                 { TextSetFont(i_font, -fs * 10); uint w = 0, h = 0; TextGetSize("Ag", w, h); return (int)h; }
#define MAXCL 4
// two-column table (Pine table.new + table.cell, multi-line cells). bg already blended. Returns its size.
void Table(const string id, const ENUM_BASE_CORNER cn, const int rows, string &c0[], string &c1[], color &b0[], color &b1[], const int fs, int &tw, int &th)
{
   bool right = cn == CORNER_RIGHT_LOWER || cn == CORNER_RIGHT_UPPER;
   bool lower = cn == CORNER_RIGHT_LOWER || cn == CORNER_LEFT_LOWER;
   int pad = 6, gap = 1, mg = 8, lh = TxtH(fs) + 3;
   int w0 = 0, w1 = 0;
   int nl[];
   ArrayResize(nl, rows);
   for(int r = 0; r < rows; r++)
   {
      string p0[], p1[];
      int n0 = Split(c0[r], p0), n1 = Split(c1[r], p1);
      nl[r] = MathMin(MAXCL, MathMax(n0, n1));
      for(int q = 0; q < n0; q++) w0 = MathMax(w0, TxtW(p0[q], fs));
      for(int q = 0; q < n1; q++) w1 = MathMax(w1, TxtW(p1[q], fs));
   }
   w0 += 2 * pad; w1 += 2 * pad;
   tw = w0 + w1 + 3 * gap;
   th = gap;
   for(int r = 0; r < rows; r++) th += nl[r] * lh + 4 + gap;
   color grid = Col(CL_GRAY, 70);
   #define TX(lx) (right ? mg + tw - (lx) : mg + (lx))
   #define TY(ty) (lower ? mg + th - (ty) : mg + (ty))
   ScrRect(PFX + id + "_bg", cn, TX(0), TY(0), tw, th, grid, grid);
   int top = gap, l0 = gap, l1 = gap + w0 + gap;
   for(int r = 0; r < rows; r++)
   {
      int hh = nl[r] * lh + 4;
      ScrRect(PFX + id + "_b0_" + IntegerToString(r), cn, TX(l0), TY(top), w0, hh, b0[r], b0[r]);
      ScrRect(PFX + id + "_b1_" + IntegerToString(r), cn, TX(l1), TY(top), w1, hh, b1[r], b1[r]);
      string p0[], p1[];
      int n0 = Split(c0[r], p0), n1 = Split(c1[r], p1);
      for(int q = 0; q < MAXCL; q++)
      {
         string a = PFX + id + "_t0_" + IntegerToString(r) + "_" + IntegerToString(q);
         string b = PFX + id + "_t1_" + IntegerToString(r) + "_" + IntegerToString(q);
         if(q < n0 && q < nl[r]) ScrLabel(a, cn, TX(l0 + pad), TY(top + 2 + q * lh), p0[q], CL_WHITE, fs);
         else if(ObjectFind(0, a) >= 0) ObjectSetInteger(0, a, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);
         if(q < n1 && q < nl[r]) ScrLabel(b, cn, TX(l1 + pad), TY(top + 2 + q * lh), p1[q], CL_WHITE, fs);
         else if(ObjectFind(0, b) >= 0) ObjectSetInteger(0, b, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);
      }
      top += hh + gap;
   }
   #undef TX
   #undef TY
}

string f_biasTxt(const int b) { return b > 0 ? "▲ Bull" : b < 0 ? "▼ Bear" : "—"; }
color  f_biasCol(const int b) { return b > 0 ? Col(COL_BULL, 75) : b < 0 ? Col(COL_BEAR, 75) : Col(CL_GRAY, 75); }
string f_qualTxt(const int q) { return q >= 4 ? "institutional" : q == 3 ? "strong" : q == 2 ? "valid" : q == 1 ? "weak" : "—"; }
string f_suTxt(const int s)   { return s == 0 ? "idle" : s == 1 ? "SWEPT" : s == 2 ? "AT POI" : s == 3 ? "SHIFTED·await retest" : "ACTIVE"; }

void Dashboard()
{
   string c0[12], c1[12];
   color b0[12], b1[12];
   color rowBg = Col(CL_GRAY, 85);
   for(int r = 0; r < 12; r++) { b0[r] = rowBg; b1[r] = rowBg; }
   double c = C(0);
   c0[0] = "LQ-SD-PA v3.8.6"; b0[0] = Col(CL_GRAY, 60);
   c1[0] = regime; b1[0] = regime == "TRENDING" ? f_biasCol(extDir) : regime == "CHOP" ? Col(CL_RED, 70) : rowBg;
   c0[1] = "Bias " + g_biasName;
   c1[1] = f_biasTxt(emaBias) + " · D " + f_biasTxt(bD) + " · str " + f_biasTxt(hsDir) + " → " + f_biasTxt(htfB); b1[1] = f_biasCol(htfB);
   string sweepTxt = (sslInPlay ? "SSL " + f_qualTxt(lastSslQual) : "") + (sslInPlay && bslInPlay ? " · " : "") + (bslInPlay ? "BSL " + f_qualTxt(lastBslQual) : "");
   c0[2] = "Struct · sweep";
   c1[2] = "int " + (msDir > 0 ? "▲" : msDir < 0 ? "▼" : "—") + " ext " + (extDir > 0 ? "▲" : extDir < 0 ? "▼" : "—") + " · " + (sweepTxt == "" ? "no sweep" : sweepTxt); b1[2] = f_biasCol(extDir);
   string pdTxt = isna(pdPos) ? "—" : (pdPos >= 0.5 ? "Prem " : "Disc ") + DoubleToString(pdPos * 100, 0) + "%" + (rangeHolds ? "" : " ·tight") + (inOTEbuy ? " ·OTE buy" : inOTEsell ? " ·OTE sell" : "");
   c0[3] = "Range pos"; c1[3] = pdTxt;
   string nbTxt = isna(nbTop) ? "none" : "T" + IntegerToString(nbScore) + (nbKind != "SD" && nbKind != "" ? " " + nbKind : "") + " · " + DoubleToString(MathAbs(c - nbTop) / atr, 1) + " ATR" + (nbFresh ? " ·fresh" : "");
   string nsTxt = isna(nsBot) ? "none" : "T" + IntegerToString(nsScore) + (nsKind != "SD" && nsKind != "" ? " " + nsKind : "") + " · " + DoubleToString(MathAbs(nsBot - c) / atr, 1) + " ATR" + (nsFresh ? " ·fresh" : "");
   c0[4] = "Next demand"; c1[4] = nbTxt; b1[4] = isna(nbTop) ? rowBg : Col(COL_BULL, 80);
   c0[5] = "Next supply"; c1[5] = nsTxt; b1[5] = isna(nsBot) ? rowBg : Col(COL_BEAR, 80);
   string trigTxt = (recentMssUp ? "MSS▲ " : recentChUp ? "CHoCH▲ " : recentBosUp ? "BOS▲ " : "") + (recentCisdUp ? "CISD▲ " : "") +
                    (recentMssDn ? "MSS▼ " : recentChDn ? "CHoCH▼ " : recentBosDn ? "BOS▼ " : "") + (recentCisdDn ? "CISD▼" : "");
   string contTxt = suL >= 1 && suLCont ? "cont L" : suS >= 1 && suSCont ? "cont S" : contTapL ? "HTF dmd tap" : contTapS ? "HTF sup tap" : !contOn ? "off" : "—";
   c0[6] = "Trigger · ◎ HTF POI"; c1[6] = (trigTxt == "" ? "none" : trigTxt) + " · ◎ " + contTxt;
   c0[7] = "◉ Setup L / S"; c1[7] = f_suTxt(suL) + "  /  " + f_suTxt(suS); b1[7] = suL >= 1 ? Col(COL_BULL, 60) : suS >= 1 ? Col(COL_BEAR, 60) : rowBg;
   c0[8] = "Alignment";
   c1[8] = "L " + IntegerToString(scoreLong) + " (" + f_tierTxt(tierLong) + ")  S " + IntegerToString(scoreShort) + " (" + f_tierTxt(tierShort) + ")";
   b1[8] = scoreLong >= 80 ? Col(COL_BULL, 55) : scoreShort >= 80 ? Col(COL_BEAR, 55) : rowBg;
   string sbRemTxt = sbRemMin == NAI ? "" : " " + IntegerToString(sbRemMin) + "m left";
   string sbTxt = !sbEnable ? "SB off" : sbActive ? "◆ SB " + f_sbWinTxt(sbWinNow) + sbRemTxt : sbCtx ? "◆ pre " + sbWinTxt : "SB off-window";
   string kzTxt = !g_intra ? "—" : (inSB ? "SB KZ" : inNY ? "NY AM" : inLon ? "London" : inAsia ? "Asia" : "off-hours") + (inNews ? " · ⚠ vol window" : "") + " · " + sbTxt;
   c0[9] = "Session"; c1[9] = kzTxt; b1[9] = inNews && g_intra ? Col(CL_RED, 60) : sbActive ? Col(CL_TEAL, 45) : rowBg;
   string riskTxt = trdDir == 0 ? (pendDir != 0 ? "order pending — fills next open" : "flat") :
                    (trdDir == 1 ? "LONG " : "SHORT ") + fmtPx(trdEntry) + " SL " + fmtPx(trdSL) + (trdTp1Hit ? " ·TP1✓" : "") + (trdTp2Hit ? " ·TP2✓" : "") + (trdIsSb ? " ·SB" : "");
   c0[10] = "Trade"; c1[10] = riskTxt; b1[10] = trdDir == 1 ? Col(COL_BULL, 70) : trdDir == -1 ? Col(COL_BEAR, 70) : rowBg;
   double dayFrac = g_intra ? MathMin(1.0, (double)((long)gT[g_bi] % 86400) / 86400.0) : NA;
   string adrTxt = isna(adrPct) ? "" : " · ADR " + DoubleToString(adrPct * 100, 0) + "%" + (!isna(dayFrac) && dayFrac < 0.25 ? " (early)" : "") + (adrChaseL ? " no-chase▲" : adrChaseS ? " no-chase▼" : "");
   int actSide = suL >= 2 ? 1 : suS >= 2 ? -1 : suL == 1 ? 1 : suS == 1 ? -1 : 0;
   string actTag = actSide == 1 ? "L: " : "S: ";
   string actKill = actSide == 1 ? gateKillL : actSide == -1 ? gateKillS : "";
   int actStage = actSide == 1 ? suL : suS;
   string lockTxt = dirLock == 0 ? "" : dirLock == 1 ? " · shorts locked" : " · longs locked";
   string nextL = suL == 1 ? "wait POI · " + nbTxt : suL == 2 ? "wait shift ▲" : suL == 3 ? (isna(suLAnchorT) ? "wait shift-leg FVG" : "wait CE " + fmtPx((suLAnchorT + suLAnchorB) / 2)) : "";
   string nextS = suS == 1 ? "wait POI · " + nsTxt : suS == 2 ? "wait shift ▼" : suS == 3 ? (isna(suSAnchorT) ? "wait shift-leg FVG" : "wait CE " + fmtPx((suSAnchorT + suSAnchorB) / 2)) : "";
   string biasPre = actSide == 1 && !biasOkL ? " · ⚠ bias blocks entry" : actSide == -1 && !biasOkS ? " · ⚠ bias blocks entry" : "";
   string armTxt = sslInPlay && lastSslQual < minArmQual ? "SSL " + f_qualTxt(lastSslQual) + " < arm Q" + IntegerToString(minArmQual) :
                   bslInPlay && lastBslQual < minArmQual ? "BSL " + f_qualTxt(lastBslQual) + " < arm Q" + IntegerToString(minArmQual) : "";
   string noTrade;
   if(anyLong || anyShort) noTrade = "";
   else if(planKill != "") noTrade = "NO · " + planKill;
   else if(actKill != "") noTrade = "NO · " + actTag + actKill + lockTxt;
   else if(actSide != 0) noTrade = actTag + f_suTxt(actStage) + ((suLCont && actSide == 1) || (suSCont && actSide == -1) ? " ◎" : "") + " · " + (actSide == 1 ? nextL : nextS) + biasPre + lockTxt;
   else if(!govOK) noTrade = "NO · day closed — " + IntegerToString(trdToday) + " signals, " + IntegerToString(lossToday) + " losses";
   else if(trdDir != 0) noTrade = trdDir == 1 ? "LONG trade live · shorts locked" : "SHORT trade live · longs locked";
   else if(poiConflict) noTrade = "NO · POI conflict — no tie-break";
   else if(poiConflictRaw) noTrade = "NO · POI conflict resolved to " + (poiSideBias > 0 ? "longs" : "shorts");
   else if(htfB == 0 && neutralMode == NM_BLOCK) noTrade = "NO · neutral bias";
   else if(!sbOnlyOK) noTrade = "NO · outside SB windows";
   else if(!dowOK) noTrade = "NO · day filter";
   else if(regime == "CHOP" && !chopOKL && !chopOKS) noTrade = "NO · chop";
   else if(inNews && g_intra && useNews && !newsOK) noTrade = "NO · volatility window";
   else if(armTxt != "") noTrade = "NO · " + armTxt;
   else if(suL == 0 && suS == 0 && !sslInPlay && !bslInPlay) noTrade = "NO · no liquidity event · wait sweep" + (contOn ? " or HTF POI tap" : "");
   else noTrade = "waiting";
   c0[11] = "Verdict";
   c1[11] = (anyLong ? "LONG signal" : anyShort ? "SHORT signal" : noTrade) + adrTxt;
   b1[11] = anyLong ? Col(COL_BULL, 40) : anyShort ? Col(COL_BEAR, 40) : adrExh ? Col(CL_ORANGE, 65) : rowBg;
   Table("D", CORNER_RIGHT_UPPER, 12, c0, c1, b0, b1, dashSize, g_dashW, g_dashH);
}
void DebugTable()
{
   string c0[5], c1[5];
   color b0[5], b1[5];
   color rowBg = Col(CL_NAVY, 80);
   for(int r = 0; r < 5; r++) { b0[r] = rowBg; b1[r] = rowBg; }
   c0[0] = "Sweeps raw/eff k";
   c1[0] = "SSL raw" + IntegerToString(lastSslQualRaw) + "/eff" + IntegerToString(lastSslQual) + " k" + IntegerToString(lastSslKind) + (sslInPlay ? " live" : " stale") +
           "\nBSL raw" + IntegerToString(lastBslQualRaw) + "/eff" + IntegerToString(lastBslQual) + " k" + IntegerToString(lastBslKind) + (bslInPlay ? " live" : " stale");
   c0[1] = "Machine L / S";
   c1[1] = "L " + f_suTxt(suL) + " · " + suLReason + "\nS " + f_suTxt(suS) + " · " + suSReason;
   c0[2] = "Score C/L/P/T/E";
   c1[2] = "L " + IntegerToString(ctxLong) + "/" + IntegerToString(liqLong) + "/" + IntegerToString(poiLong) + "/" + IntegerToString(trigLong) + "/" + IntegerToString(execLong) +
           "\nS " + IntegerToString(ctxShort) + "/" + IntegerToString(liqShort) + "/" + IntegerToString(poiShort) + "/" + IntegerToString(trigShort) + "/" + IntegerToString(execShort);
   c0[3] = "Counts · untrk";
   c1[3] = "A " + IntegerToString(cntA) + " A+ " + IntegerToString(cntAp) + " L" + IntegerToString(cntLong) + " S" + IntegerToString(cntShort) +
           "\nTP " + IntegerToString(cntTP1) + "/" + IntegerToString(cntTP2) + "/" + IntegerToString(cntTP3) + " SL " + IntegerToString(cntSL) + " BE " + IntegerToString(cntBE) +
           " void " + IntegerToString(cntVoid) + " exp " + IntegerToString(cntExp) + " untrk " + IntegerToString(cntUntracked) + " ΣR " + fmtG(sumR, 2);
   c0[4] = "◬ LT · ◆ SB · day";
   c1[4] = ltDbgMach + "\n" + ltDbgLast + "\nSB win " + IntegerToString(sbWinNow) + " tag " + IntegerToString(sbTagL) + "/" + IntegerToString(sbTagS) + " ent " + IntegerToString(cntSbEnt) +
           " · day " + IntegerToString(trdToday) + " sig " + IntegerToString(lossToday) + " loss" + (spr > 0 ? " · spr " + fmtG(spreadIn, 1) + "t" : "");
   b1[4] = ltLState == 1 ? Col(COL_BULL, 70) : ltSState == 1 ? Col(COL_BEAR, 70) : sbActive ? Col(CL_TEAL, 60) : rowBg;
   Table("G", CORNER_RIGHT_LOWER, 5, c0, c1, b0, b1, dashSize, g_dbgW, g_dbgH);
}

//+------------------------------------------------------------------+
//| MODULE 23 — alerts (live closed bar only) + journal lines         |
//+------------------------------------------------------------------+
int  pSuL = 0, pSuS = 0, pSbTagL = 0, pSbTagS = 0, pSuLFvgBar = NAI, pSuSFvgBar = NAI;
void Notify(const bool on, const string msg)
{
   if(!on || !g_live) return;
   string m = "LQ " + _Symbol + " " + TfName((ENUM_TIMEFRAMES)Period()) + ": " + msg;
   if(i_alPopup) Alert(m);
   if(i_alPush) SendNotification(m);
}
void Journal(const string msg)
{
   if(!g_live || msg == "") return;
   Print(msg);
   if(i_alPush) SendNotification(msg);
}
void Alerts()
{
   if(!g_live) return;
   int tL = finalTierL, tS = finalTierS;
   string ep = " · E " + fmtPx(entryP) + " SL " + fmtPx(slP) + " TP2 " + fmtPx(tp2P);
   if(anyLong)  Notify(i_alSignals, (tL >= 4 ? "[SIGNAL] A+ LONG" : tL == 3 ? "[SIGNAL] A LONG" : "[SIGNAL] LONG") + (sigMCLong ? " · ◉ machine" : "") + ep);
   if(anyShort) Notify(i_alSignals, (tS >= 4 ? "[SIGNAL] A+ SHORT" : tS == 3 ? "[SIGNAL] A SHORT" : "[SIGNAL] SHORT") + (sigMCShort ? " · ◉ machine" : "") + ep);
   if((suL == 1 && pSuL != 1) || (suS == 1 && pSuS != 1)) Notify(i_alSetup, "[SETUP] Armed (quality sweep)");
   if((suL == 2 && pSuL != 2) || (suS == 2 && pSuS != 2)) Notify(i_alSetup, "[SETUP] POI tapped");
   if((suL == 3 && pSuL != 3) || (suS == 3 && pSuS != 3)) Notify(i_alSetup, "[SETUP] Structure shifted — awaiting retest");
   if((suL == 0 && pSuL >= 1 && pSuL <= 3) || (suS == 0 && pSuS >= 1 && pSuS <= 3)) Notify(i_alSetup, "[SETUP] Invalidated / expired — " + (suL == 0 && pSuL >= 1 && pSuL <= 3 ? suLReason : suSReason));
   if((suL >= 1 && pSuL == 0 && suLCont) || (suS >= 1 && pSuS == 0 && suSCont)) Notify(i_alSetup, "[SETUP] ◎ Continuation armed (HTF POI)");
   if(cntTP1 > pCntTP1) Notify(i_alTrade, "[TRADE] TP1 hit");
   if(cntTP2 > pCntTP2) Notify(i_alTrade, "[TRADE] TP2 hit");
   if(cntSL > pCntSL)   Notify(i_alTrade, "[TRADE] SL hit");
   if(mssUp || mssDn)       Notify(i_alTrig, "[TRIG] MSS " + (mssUp ? "▲" : "▼"));
   if(eChochUp || eChochDn) Notify(i_alTrig, "[TRIG] External CHoCH " + (eChochUp ? "▲" : "▼"));
   if(sslSweep || bslSweep) Notify(i_alLiq, "[LIQ] Swing sweep");
   if(eqhSwept || eqlSwept) Notify(i_alLiq, "[LIQ] EQH/EQL pool swept");
   if(pdhSweep || pdlSweep || pwhSweep || pwlSweep) Notify(i_alLiq, "[LIQ] Prev-day / week level swept");
   if(sesHiSwept || sesLoSwept) Notify(i_alLiq, "[LIQ] Session level raided");
   if(touchNextBuy)  Notify(i_alLiq, "[POI] Price entered next demand");
   if(touchNextSell) Notify(i_alLiq, "[POI] Price entered next supply");
   if(inNews && !pNews) Notify(i_alCtx, "[CTX] Volatility window started — entries suppressed");
   if(!inNews && pNews) Notify(i_alCtx, "[CTX] Volatility window ended — entries re-enabled");
   if(ltArmEvt) Notify(i_alLT, "[LT] Trap setup detected — " + (ltLState == 1 ? ltLPats : ltSPats));
   if(sigLTLong && anyLong)   Notify(i_alLT && ltDynAlert, "◬ LT BUY · " + ltLPats + " · " + IntegerToString(ltLongScore) + " · E " + fmtPx(entryP) + " SL " + fmtPx(slP));
   if(sigLTShort && anyShort) Notify(i_alLT && ltDynAlert, "◬ LT SELL · " + ltSPats + " · " + IntegerToString(ltShortScore) + " · E " + fmtPx(entryP) + " SL " + fmtPx(slP));
   // Silver Bullet feed
   if(sbDynAlert && sbOn && i_alSB)
   {
      if(sbFireL || sbFireS)
         Notify(true, "◆ SB " + (sbFireL ? "BUY" : "SELL") + " · " + f_sbWinTxt(sbFireL ? sbTagL : sbTagS) + " · " + ((sbFireL ? sbCeFillL : sbCeFillS) ? "CE" : "edge") +
                " · " + f_tierTxt(sbFireL ? mcTierL : mcTierS) + " · SL " + fmtPx(slP) + " TP1 " + fmtPx(tp1P) + " TP2 " + fmtPx(tp2P));
      if(sbBeEvt && trdIsSb) Notify(true, "◆ SB TP1 · stop to BE · SL " + fmtPx(trdSL));
      if(sbTimeExitEvt)      Notify(true, "◆ SB TIME EXIT · " + (sbTimeMode == SBX_FULL ? "close" : "reduce manually, stop → BE"));
      if(sbStructExitEvt)    Notify(true, "◆ SB STRUCTURE EXIT · close the remainder");
      if((suL == 0 && pSuL >= 1 && pSuL <= 3 && pSbTagL != 0) || (suS == 0 && pSuS >= 1 && pSuS <= 3 && pSbTagS != 0))
         Notify(true, "◆ SB setup gone · " + (suL == 0 && pSbTagL != 0 ? suLReason : suSReason));
   }
   // journal lines (LQEXIT / LQCE / LQJRNL) -> Experts log (+ push)
   if(jrnlEnable)
   {
      bool ceEvtL = suL == 3 && !isnai(suLFvgBar) && (pSuL != 3 || isnai(pSuLFvgBar));
      bool ceEvtS = suS == 3 && !isnai(suSFvgBar) && (pSuS != 3 || isnai(pSuSFvgBar));
      string tf = TfName((ENUM_TIMEFRAMES)Period());
      if(trdOutEvt) Journal(exitMsg);
      if(!(anyLong || anyShort) && (ceEvtL || ceEvtS))
      {
         string ce = "LQCE|" + _Symbol + "|" + tf + (ceEvtL ?
            "|L|CE" + fmtPx((suLAnchorT + suLAnchorB) / 2) + "|SLa" + fmtPx(suLAnchorB - SL_PAD_ATR * atr) + "|SLr" + fmtPx(MathMin(suLAnchorB, nz(suLSweepExt, suLAnchorB)) - SL_PAD_ATR * atr) :
            "|S|CE" + fmtPx((suSAnchorT + suSAnchorB) / 2) + "|SLa" + fmtPx(suSAnchorT + SL_PAD_ATR * atr + spr) + "|SLr" + fmtPx(MathMax(suSAnchorT, nz(suSSweepExt, suSAnchorT)) + SL_PAD_ATR * atr + spr));
         Journal(ce);
      }
      if(anyLong || anyShort)
         Journal("LQJRNL|" + _Symbol + "|" + tf + "|" + (anyLong ? "L" : "S") +
                 "|" + (sbFireL || sbFireS ? "SB" : sigMCLong || sigMCShort ? ((anyLong ? suLCont : suSCont) ? "MCc" : "MC") : sigLTLong || sigLTShort ? "LT" : "ENG") +
                 "|" + f_tierTxt(anyLong ? finalTierL : finalTierS) + "|sc" + IntegerToString(anyLong ? scoreLong : scoreShort) +
                 "|k" + IntegerToString(anyLong ? lastSslKind : lastBslKind) + "q" + IntegerToString(anyLong ? lastSslQualRaw : lastBslQualRaw) +
                 "sh" + IntegerToString(anyLong ? sbShiftGL : sbShiftGS) + "w" + IntegerToString(anyLong ? sbTagL : sbTagS) + "|" + regime +
                 "|E" + fmtPx(entryP) + "|SL" + fmtPx(slP) + "|T2" + fmtPx(tp2P) + "|d" + IntegerToString(trdToday) + "/" + IntegerToString(lossToday));
   }
}

//+------------------------------------------------------------------+
//| one closed bar, every module in Pine order                        |
//+------------------------------------------------------------------+
void ProcessBar(const int i)
{
   g_bi = i;
   M3(); M4(); M4B(); M5(); M6(); M7(); M9(); M10(); M11(); M12(); M13();
   M14(); M16(); M16B(); M17(); M18(); M19();
   Visual();
   Alerts();
   // previous-bar values for the next bar ([1] references)
   pPdh = pdh; pPdl = pdl; pPwh = pwh; pPwl = pwl; pHT = hT;
   pNbTop = nbTop; pNsBot = nsBot;
   pSuL = suL; pSuS = suS; pSbTagL = sbTagL; pSbTagS = sbTagS; pSuLFvgBar = suLFvgBar; pSuSFvgBar = suSFvgBar;
   pCntTP1 = cntTP1; pCntTP2 = cntTP2; pCntSL = cntSL;
}

//+------------------------------------------------------------------+
//| canvas: box fills + bgcolor bands (real alpha, behind the bars)   |
//+------------------------------------------------------------------+
#define CVNAME "LQ386cv"
CCanvas g_cv;
bool    g_cvOk = false;
double  g_pmax = 0, g_pmin = 0;
bool    g_shiftSet = false;
long    g_shiftOrig = 0;
double  g_shiftSizeOrig = 0;

void BandLayer(color &cc[], int &tt[], const int iFrom, const int iTo, const int sp, const int cw, const int ch)
{
   int x, y, x2, y2;
   int a = iFrom;
   while(a <= iTo)
   {
      int b = a;
      while(b + 1 <= iTo && tt[b + 1] == tt[a] && cc[b + 1] == cc[a]) b++;
      if(tt[a] < 100 && ChartTimePriceToXY(0, 0, gT[a], gC[a], x, y) && ChartTimePriceToXY(0, 0, gT[b], gC[b], x2, y2))
         g_cv.FillRectangle(MathMax(x - sp / 2, 0), 0, MathMin(x2 + (sp + 1) / 2, cw - 1), ch - 1, ColorToARGB(cc[a], AlphaOf(tt[a])));
      a = b + 1;
   }
}
void Render()
{
   int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS, 0);
   int ch = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   if(cw <= 0 || ch <= 0 || g_last <= 0) return;
   if(!g_cvOk)
   {
      if(!g_cv.CreateBitmapLabel(0, 0, CVNAME, 0, 0, cw, ch, COLOR_FORMAT_ARGB_NORMALIZE)) return;
      ObjectSetInteger(0, CVNAME, OBJPROP_BACK, true);
      ObjectSetInteger(0, CVNAME, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, CVNAME, OBJPROP_HIDDEN, true);
      g_cvOk = true;
   }
   else if(g_cv.Width() != cw || g_cv.Height() != ch) g_cv.Resize(cw, ch);
   g_cv.Erase(0);
   g_pmax = ChartGetDouble(0, CHART_PRICE_MAX, 0);
   g_pmin = ChartGetDouble(0, CHART_PRICE_MIN, 0);
   if(ArraySize(g_bgT1) > g_last)
   {
      int first = (int)ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR, 0);
      int vis   = (int)ChartGetInteger(0, CHART_VISIBLE_BARS, 0);
      int sp    = 1 << (int)ChartGetInteger(0, CHART_SCALE, 0);
      int iFrom = MathMax(g_last - first - 1, 0);
      int iTo   = MathMin(g_last - first + vis + 1, g_last);
      BandLayer(g_bgC1, g_bgT1, iFrom, iTo, sp, cw, ch);
      BandLayer(g_bgC2, g_bgT2, iFrom, iTo, sp, cw, ch);
      BandLayer(g_bgC3, g_bgT3, iFrom, iTo, sp, cw, ch);
   }
   int x, y, x2, y2;
   for(int k = 0; k < ArraySize(g_boxes); k++)
   {
      if(g_boxes[k].tr >= 100) continue;
      if(!ChartTimePriceToXY(0, 0, g_boxes[k].t1, g_boxes[k].top, x, y)) continue;
      if(!ChartTimePriceToXY(0, 0, g_boxes[k].t2, g_boxes[k].bot, x2, y2)) continue;
      int l = MathMin(x, x2), r = MathMax(x, x2), t = MathMin(y, y2), b = MathMax(y, y2);
      if(r < 0 || l >= cw || b < 0 || t >= ch) continue;
      g_cv.FillRectangle(MathMax(l, 0), MathMax(t, 0), MathMin(r, cw - 1), MathMin(b, ch - 1), ColorToARGB(g_boxes[k].c, AlphaOf(g_boxes[k].tr)));
   }
   g_cv.Update(false);
}
// keep the newest bars out from under the dashboard
void ApplyShift()
{
   if(!showDash || !i_dashShift || g_dashW <= 0) return;
   int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS, 0);
   if(cw <= 0) return;
   double pct = MathMax(10.0, MathMin(50.0, MathCeil((g_dashW + 30) * 100.0 / cw)));
   if(!g_shiftSet) { g_shiftOrig = ChartGetInteger(0, CHART_SHIFT); g_shiftSizeOrig = ChartGetDouble(0, CHART_SHIFT_SIZE); g_shiftSet = true; }
   if(!ChartGetInteger(0, CHART_SHIFT)) ChartSetInteger(0, CHART_SHIFT, true);
   double cur = ChartGetDouble(0, CHART_SHIFT_SIZE);
   if(cur < pct || cur > pct + 6) ChartSetDouble(0, CHART_SHIFT_SIZE, pct);
}

//+------------------------------------------------------------------+
//| full reset (history reload)                                       |
//+------------------------------------------------------------------+
void ResetState()
{
   ObjectsDeleteAll(0, PFX);
   g_objN = 0;
   ArrayFree(g_boxes); ArrayFree(g_lbls); ArrayFree(g_lineQ);
   cdBullRunOpen = NA; cdBearRunOpen = NA; cdBullRunLen = 0; cdBearRunLen = 0; cdDnDone = false; cdUpDone = false;
   lastRes = NA; lastSup = NA; prevPH = NA; prevPL = NA; lastResBar = NAI; lastSupBar = NAI; prevPHBar = NAI; prevPLBar = NAI;
   resBroken = false; supBroken = false; resBosDone = false; supBosDone = false; resBrkBar = NAI; supBrkBar = NAI;
   tlUpSlope = NA; tlUpPrice = NA; tlDnSlope = NA; tlDnPrice = NA; tlUpBar = NAI; tlDnBar = NAI; tlUpTouch = 0; tlDnTouch = 0;
   tlUpLn = ""; tlDnLn = ""; tlUpWasNear = false; tlDnWasNear = false;
   ArrayFree(eqhLvls); ArrayFree(eqlLvls); ArrayFree(eqhLns); ArrayFree(eqlLns); ArrayFree(eqhBars); ArrayFree(eqlBars);
   sbBoxHi = NA; sbBoxLo = NA; sbBoxX1 = NAI; sbBoxWin = 0; ArrayFree(sbBoxes);
   sslSpentLvl = NA; bslSpentLvl = NA; lastSslBar = NAI; lastBslBar = NAI; lastSslLvl = NA; lastBslLvl = NA; lastSslExt = NA; lastBslExt = NA;
   lastSslQual = 0; lastBslQual = 0; lastSslQualRaw = 0; lastBslQualRaw = 0; lastSslKind = 0; lastBslKind = 0;
   pPdh = NA; pPdl = NA; pPwh = NA; pPwl = NA; pdhDone = false; pdlDone = false; pwhDone = false; pwlDone = false;
   SesTrkReset(stAsia); SesTrkReset(stLon); SesTrkReset(stNY);
   StructReset(sInt); StructReset(sExt);
   extRes = NA; extSup = NA; extResBar = NAI; extSupBar = NAI; extResBosDone = false; extSupBosDone = false;
   lastChUpBar = NAI; lastChDnBar = NAI; lastBosUpBar = NAI; lastBosDnBar = NAI; lastMssUpBar = NAI; lastMssDnBar = NAI;
   lastCisdUpBar = NAI; lastCisdDnBar = NAI; lastDispUpBar = NAI; lastDispDnBar = NAI;
   lastEngLoBar = NAI; lastEngHiBar = NAI;
   pHT = 0; dayHi = NA; dayLo = NA;
   sbRngHi = NA; sbRngLo = NA; sbRngWin = 0; sbSetLive = false; sbTagL = 0; sbTagS = 0;
   lastEBosUpBar = NAI; lastEBosDnBar = NAI; lastEChUpBar = NAI; lastEChDnBar = NAI;
   ArrayFree(bullFvgs); ArrayFree(bearFvgs);
   cFvgBTop = NA; cFvgBBot = NA; cFvgSTop = NA; cFvgSBot = NA; cFvgBBar = NAI; cFvgSBar = NAI; cFvgBDisp = false; cFvgSDisp = false;
   ArrayFree(zones); pNbTop = NA; pNsBot = NA;
   lastCrtLongBar = NAI; lastCrtShortBar = NAI; lastTbsLongBar = NAI; lastTbsShortBar = NAI;
   ibStage = 0; ibStart = NAI; ibMHigh = NA; ibMLow = NA; ibHigh = NA; ibLow = NA;
   suL = 0; suLBar = NAI; suLFvgBar = NAI; suS = 0; suSBar = NAI; suSFvgBar = NAI;
   suLAnchorT = NA; suLAnchorB = NA; suLSweepLvl = NA; suLSweepExt = NA; suSAnchorT = NA; suSAnchorB = NA; suSSweepLvl = NA; suSSweepExt = NA;
   suLReason = ""; suSReason = ""; suLCont = false; suSCont = false;
   trdEntry = NA; trdSL = NA; trdTP1 = NA; trdTP2 = NA; trdTP3 = NA; trdLiqTgt = NA; trdDir = 0; trdSbWin = 0; trdShiftG = 0;
   trdTp1Hit = false; trdTp2Hit = false; trdIsSb = false;
   p3PoolLow = NA; p3Swept = NA; ltBrkUpLvl = NA; p4Lvl = NA; p4HiMax = NA; p4HiMin = NA;
   p3PoolBar = NAI; ltBrkUpBar = NAI; p4Stage = 0; p4Bar = NAI; p4WickCnt = 0; p1PrimeBar = NAI;
   ltLState = 0; ltLBar = NAI; ltSState = 0; ltSBar = NAI; ltLRetBar = NAI; ltSRetBar = NAI;
   ltLLevel = NA; ltSLevel = NA; ltLDoneLvl = NA; ltSDoneLvl = NA; ltLPats = ""; ltSPats = ""; ltLReason = ""; ltSReason = "";
   ltLRetOk = false; ltSRetOk = false;
   sbShiftGL = 0; sbShiftGS = 0; sbArmedSslBar = NAI; sbArmedBslBar = NAI; armedSslBar = NAI; armedBslBar = NAI;
   sbDoneWinL = 0; sbDoneWinS = 0; contArmLvlL = NA; contArmLvlS = NA;
   lastLongSigBar = NAI; lastShortSigBar = NAI; trdToday = 0; lossToday = 0;
   cntA = 0; cntAp = 0; cntLong = 0; cntShort = 0; cntTP1 = 0; cntTP2 = 0; cntSL = 0; cntBE = 0; cntTP3 = 0; cntSbEnt = 0;
   cntExp = 0; cntUntracked = 0; cntVoid = 0; trdBar = NAI; pendDir = 0; pendSL = NA; trdMfe = 0; trdMae = 0; sumR = 0;
   pCntTP1 = 0; pCntTP2 = 0; pCntSL = 0;
   tpEntryLn = ""; tpSlLn = ""; tpTp1Ln = ""; tpTp2Ln = ""; tpTp3Ln = ""; tpEntryLb = ""; tpSlLb = ""; tpTp1Lb = ""; tpTp2Lb = ""; tpTp3Lb = "";
   poiBuyBx = ""; poiSellBx = ""; mcAnchBxL = ""; mcAnchBxS = ""; sbCeLnL = ""; sbCeLnS = ""; sbTgtLn = ""; sbTgtLb = "";
   nbLn = ""; nsLn = ""; nbBx = ""; nsBx = ""; nbLb = ""; nsLb = "";
   pSuL = 0; pSuS = 0; pSbTagL = 0; pSbTagS = 0; pSuLFvgBar = NAI; pSuSFvgBar = NAI;
   g_dashW = 0; g_dashH = 0; g_dbgW = 0; g_dbgH = 0;
   g_lastDone = -1;
}

//+------------------------------------------------------------------+
int OnInit()
{
   SetIndexBuffer(0, BRes, INDICATOR_DATA); SetIndexBuffer(1, BSup, INDICATOR_DATA);
   SetIndexBuffer(2, BPLo, INDICATOR_DATA); SetIndexBuffer(3, BPHi, INDICATOR_DATA);
   SetIndexBuffer(4, BPdh, INDICATOR_DATA); SetIndexBuffer(5, BPdl, INDICATOR_DATA);
   SetIndexBuffer(6, BPwh, INDICATOR_DATA); SetIndexBuffer(7, BPwl, INDICATOR_DATA);
   for(int k = 0; k < 8; k++) PlotIndexSetDouble(k, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   g_bgCol = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   g_fgCol = (color)ChartGetInteger(0, CHART_COLOR_FOREGROUND);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, Col(COL_BEAR, 50));
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, Col(COL_BULL, 50));
   PlotIndexSetInteger(2, PLOT_LINE_COLOR, Col(COL_BULL, 15));
   PlotIndexSetInteger(3, PLOT_LINE_COLOR, Col(COL_BEAR, 15));
   PlotIndexSetInteger(4, PLOT_LINE_COLOR, Col(CL_SILVER, 55));
   PlotIndexSetInteger(5, PLOT_LINE_COLOR, Col(CL_SILVER, 55));
   PlotIndexSetInteger(6, PLOT_LINE_COLOR, Col(CL_SILVER, 70));
   PlotIndexSetInteger(7, PLOT_LINE_COLOR, Col(CL_SILVER, 70));
   IndicatorSetString(INDICATOR_SHORTNAME, "LQ-SD-PA v3.8.6");
   ResolveProfile();
   ResolveTfs();
   g_intra = PeriodSeconds(PERIOD_CURRENT) < 86400;
   g_tick  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(g_tick <= 0) g_tick = _Point;
   drawSize = FsOf(uiDrawOpt); sigSize = FsOf(uiSizeOpt); dashSize = FsOf(uiDashOpt);
   mkSize = uiMicroBig ? 8 : 7; tinySize = 7;
   sAsia = ParseSess(asiaSes); sLon = ParseSess(lonSes); sNY = ParseSess(nySes);
   sSbLO = ParseSess(sbSesLO); sSbAM = ParseSess(sbSesAM); sSbPM = ParseSess(sbSesPM);
   sN1 = ParseSess(news1Ses); sN2 = ParseSess(news2Ses); sN3 = ParseSess(news3Ses);
   if(i_srvGmt == -99)
   {
      long d = (long)(TimeTradeServer() - TimeGMT());
      g_srvOffSec = (int)(MathRound(d / 1800.0) * 1800);
   }
   else g_srvOffSec = i_srvGmt * 3600;
   g_lastDone = -1;
   return INIT_SUCCEEDED;
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_CHART_CHANGE) { ApplyShift(); LblPlaceAll(); Render(); ChartRedraw(); }
}

void OnDeinit(const int reason)
{
   if(g_shiftSet) { ChartSetInteger(0, CHART_SHIFT, g_shiftOrig); ChartSetDouble(0, CHART_SHIFT_SIZE, g_shiftSizeOrig); }
   if(g_cvOk) { g_cv.Destroy(); g_cvOk = false; }
   ObjectsDeleteAll(0, PFX);
   ChartRedraw();
}

bool LoadFeeds(const datetime from)
{
   if(!FeedLoad(fBias, g_biasTF, from, 300) || FeedIdx(fBias, gT[g_last - 1]) < 0) return false;
   if(!FeedLoad(fHtf, g_htfTF, from, MathMax(tbsLen, hPoiMaxAge) + 60) || FeedIdx(fHtf, gT[g_last - 1]) < 0) return false;
   if(!FeedLoad(fD1, PERIOD_D1, from, 300) || FeedIdx(fD1, gT[g_last - 1]) < 0) return false;
   if(!FeedLoad(fW1, PERIOD_W1, from, 10)) return false;
   HtfEmaSign(fBias, hbEma);
   HtfStructCalc(fBias);
   HtfEmaSign(fD1, hdEma);
   HtfAdrCalc(fD1);
   HtfCrtTbsCalc(fHtf);
   HtfPoiCalc(fHtf);
   return true;
}

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[], const double &open[],
                const double &high[], const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   int need = MathMax(2 * extPiv + 20, atrLen + 60);
   if(rates_total < need) return 0;
   ArraySetAsSeries(time, false); ArraySetAsSeries(open, false); ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);  ArraySetAsSeries(close, false); ArraySetAsSeries(tick_volume, false);

   bool full = prev_calculated == 0 || g_lastDone < 0 || g_lastDone > rates_total - 2;
   int lastClosed = rates_total - 2;
   if(!full && lastClosed <= g_lastDone)
   {
      if(ChartGetDouble(0, CHART_PRICE_MAX, 0) != g_pmax || ChartGetDouble(0, CHART_PRICE_MIN, 0) != g_pmin)
      { LblPlaceAll(); Render(); ChartRedraw(); }
      return rates_total;
   }
   int oldN = ArraySize(gO);
   ArrayResize(gO, rates_total); ArrayResize(gH, rates_total); ArrayResize(gL, rates_total);
   ArrayResize(gC, rates_total); ArrayResize(gV, rates_total); ArrayResize(gT, rates_total);
   ArrayResize(gATRraw, rates_total); ArrayResize(gATR, rates_total);
   ArrayResize(g_bgC1, rates_total); ArrayResize(g_bgC2, rates_total); ArrayResize(g_bgC3, rates_total);
   ArrayResize(g_bgT1, rates_total); ArrayResize(g_bgT2, rates_total); ArrayResize(g_bgT3, rates_total);
   int from0 = full ? 0 : MathMin(MathMax(g_lastDone - 2, 0), oldN);
   for(int j = from0; j < rates_total; j++)
   {
      gO[j] = open[j]; gH[j] = high[j]; gL[j] = low[j]; gC[j] = close[j]; gV[j] = (double)tick_volume[j]; gT[j] = time[j];
      g_bgT1[j] = 100; g_bgT2[j] = 100; g_bgT3[j] = 100; g_bgC1[j] = clrNONE; g_bgC2[j] = clrNONE; g_bgC3[j] = clrNONE;
   }
   g_last = rates_total - 1;
   // ATR = RMA(TR) seeded with the SMA (Pine ta.atr); gating ATR capped at atrCapIn × its 50-bar mean (FIX-Y4)
   int aFrom = full ? 0 : MathMax(g_lastDone, 1);
   for(int j = aFrom; j <= lastClosed; j++)
   {
      double tr = j == 0 ? gH[0] - gL[0] : MathMax(gH[j] - gL[j], MathMax(MathAbs(gH[j] - gC[j - 1]), MathAbs(gL[j] - gC[j - 1])));
      if(j < atrLen - 1) gATRraw[j] = NA;
      else if(j == atrLen - 1)
      {
         double s = 0;
         for(int k = 0; k < atrLen; k++) s += k == 0 ? gH[0] - gL[0] : MathMax(gH[k] - gL[k], MathMax(MathAbs(gH[k] - gC[k - 1]), MathAbs(gL[k] - gC[k - 1])));
         gATRraw[j] = s / atrLen;
      }
      else gATRraw[j] = (gATRraw[j - 1] * (atrLen - 1) + tr) / atrLen;
      double avg = NA;
      if(j >= atrLen - 1 + 49)
      {
         double s = 0;
         for(int k = j - 49; k <= j; k++) s += gATRraw[k];
         avg = s / 50;
      }
      gATR[j] = atrCapIn > 0 && !isna(avg) && avg > 0 ? MathMin(gATRraw[j], atrCapIn * avg) : gATRraw[j];
   }
   int startIdx;
   if(full)
   {
      ResetState();
      startIdx = MathMax(rates_total - 1 - i_calcBars, need);
      ArrayInitialize(BRes, EMPTY_VALUE); ArrayInitialize(BSup, EMPTY_VALUE); ArrayInitialize(BPLo, EMPTY_VALUE); ArrayInitialize(BPHi, EMPTY_VALUE);
      ArrayInitialize(BPdh, EMPTY_VALUE); ArrayInitialize(BPdl, EMPTY_VALUE); ArrayInitialize(BPwh, EMPTY_VALUE); ArrayInitialize(BPwl, EMPTY_VALUE);
   }
   else startIdx = g_lastDone + 1;
   datetime from = gT[MathMax(rates_total - 1 - i_calcBars, need)];
   if(!LoadFeeds(from))
   {
      if(full) { g_lastDone = -1; return 0; }
      return prev_calculated;
   }
   for(int i = startIdx; i <= lastClosed; i++)
   {
      g_live = !full && i == lastClosed;
      ProcessBar(i);
      g_lastDone = i;
   }
   BRes[rates_total - 1] = EMPTY_VALUE; BSup[rates_total - 1] = EMPTY_VALUE; BPLo[rates_total - 1] = EMPTY_VALUE; BPHi[rates_total - 1] = EMPTY_VALUE;
   BPdh[rates_total - 1] = EMPTY_VALUE; BPdl[rates_total - 1] = EMPTY_VALUE; BPwh[rates_total - 1] = EMPTY_VALUE; BPwl[rates_total - 1] = EMPTY_VALUE;
   // last-bar drawings + tables (Pine barstate.islast) on the newest closed bar
   g_bi = lastClosed;
   LastBarDraw();
   if(showDash) Dashboard();
   if(showDbg) DebugTable();
   ApplyShift();
   LblPlaceAll();
   Render();
   ChartRedraw();
   return rates_total;
}
//+------------------------------------------------------------------+
