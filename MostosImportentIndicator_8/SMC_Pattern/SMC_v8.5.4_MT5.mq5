//+------------------------------------------------------------------+
//|                                              SMC_v8.5.4_MT5.mq5  |
//|  SMC / ICT Suite v8.5.4 — MQL5 port of SMC_v8.5.4.txt (Pine v6)  |
//|                                                                  |
//|  Port notes                                                      |
//|  * Every engine (L0 candle · L1 structure · L2 FVG/strength ·    |
//|    L3 liquidity · L4 zones · L5 HTF · L6 setups · L7 trade) runs |
//|    once per CLOSED bar, in the same order as the Pine script.    |
//|    Pine gates almost everything on barstate.isconfirmed, so the  |
//|    MT5 port evaluates closed bars only (no repaint, no rollback).|
//|  * request.security(..., lookahead_on) with [1] offsets = the    |
//|    previous COMPLETED HTF / D1 / W1 candle (CopyRates feeds).    |
//|  * Session windows: the server clock is converted to UTC with    |
//|    "Server GMT offset" (-99 = auto from the terminal), then to   |
//|    New York / London (with DST) / Tokyo.                         |
//|  * Pine boxes / lines / labels / table -> chart objects (prefix  |
//|    SMC854_). Zone / FVG fills and the HTF bias tint are painted  |
//|    on one transparent canvas (real alpha, no rectangle XOR).     |
//|    Labels = filled OBJ_EDIT boxes, re-placed on scroll / zoom.   |
//|  * Data-window plots -> 14 DRAW_NONE buffers.                    |
//+------------------------------------------------------------------+
#property copyright   "SMC / ICT Suite v8.5.4 — MQL5 port"
#property version     "8.54"
#property description "SMC / ICT Suite v8.5.4 (port of the Pine v6 build): structure (BOS / CHoCH / CISD), FVG,"
#property description "liquidity (BSL/SSL/EQH/EQL/PDH/PDL/PWH/PWL/SESH/SESL), zones (OB/BRK/RCB/RJB/QM/KL),"
#property description "HTF bias, 30 setup modules, trade engine (entry / SL / TP1-3 / score / grade), panel, alerts."
#property indicator_chart_window
#property indicator_buffers 14
#property indicator_plots   14
#property indicator_type1   DRAW_NONE
#property indicator_label1  "long score"
#property indicator_type2   DRAW_NONE
#property indicator_label2  "short score"
#property indicator_type3   DRAW_NONE
#property indicator_label3  "zones"
#property indicator_type4   DRAW_NONE
#property indicator_label4  "liq levels"
#property indicator_type5   DRAW_NONE
#property indicator_label5  "M01/M02 level rejections (needs >=2)"
#property indicator_type6   DRAW_NONE
#property indicator_label6  "M46 CISD reliability 0-3"
#property indicator_type7   DRAW_NONE
#property indicator_label7  "zone departure STRONG (M33/M42 gate)"
#property indicator_type8   DRAW_NONE
#property indicator_label8  "PD array 0=low of range 1=high"
#property indicator_type9   DRAW_NONE
#property indicator_label9  "displacement quality 0-3"
#property indicator_type10  DRAW_NONE
#property indicator_label10 "S4 internal break"
#property indicator_type11  DRAW_NONE
#property indicator_label11 "S4 weak break"
#property indicator_type12  DRAW_NONE
#property indicator_label12 "reject code (long x10 + short)"
#property indicator_type13  DRAW_NONE
#property indicator_label13 "S1 arrival (bull +-1 / bear +-10)"
#property indicator_type14  DRAW_NONE
#property indicator_label14 "HTF PD array 0=low 1=high"

#include <Canvas\Canvas.mqh>

//+------------------------------------------------------------------+
//| enums (Pine input.string options)                                |
//+------------------------------------------------------------------+
enum ENUM_LBLMODE   { LBL_SIGNALS = 0, // Signals only
                      LBL_KEY     = 1, // Key events
                      LBL_ALL     = 2  // All events
                    };
enum ENUM_SETMODE   { SET_CUSTOM = 0,  // Custom (toggles)
                      SET_CORE   = 1,  // Core only
                      SET_ALLON  = 2,  // All on
                      SET_ALLOFF = 3   // All off
                    };
enum ENUM_DISPGATE  { DG_CANDLE = 0,   // Candle
                      DG_OFF    = 1    // Off
                    };
enum ENUM_FVGMIT    { FM_TOUCH = 0,    // TOUCH
                      FM_50    = 1,    // 50%
                      FM_FULL  = 2     // FULL
                    };
enum ENUM_SWEEPQUAL { SQ_MAJOR = 0,    // Major only
                      SQ_EXT   = 1     // Include external
                    };
enum ENUM_TLANCHOR  { TL_WICK = 0,     // Wick
                      TL_BODY = 1      // Body
                    };
enum ENUM_HTFMODE   { HM_CONS   = 0,   // Conservative (5m->1h, 15m->4h)
                      HM_AGGR   = 1,   // Aggressive (5m->30m, 15m->1h)
                      HM_MANUAL = 2    // Manual
                    };
enum ENUM_GATE3     { G3_OFF    = 0,   // OFF
                      G3_WARN   = 1,   // WARN
                      G3_STRICT = 2    // STRICT
                    };
enum ENUM_GATETREND { GT_ENTER = 0,    // Entering bar
                      GT_THIS  = 1     // This bar
                    };
enum ENUM_ENTRYCONF { EC_IMM  = 0,     // IMMEDIATE
                      EC_CONF = 1,     // CONFIRMED
                      EC_MSS  = 2      // MSS
                    };
enum ENUM_M10CONF   { M10_OFF  = 0,    // Off
                      M10_1BAR = 1,    // 1-bar close above sweep candle
                      M10_CISD = 2     // CISD
                    };
enum ENUM_SSNTZ     { TZ_UTC = 0,      // UTC
                      TZ_LON = 1,      // Europe/London
                      TZ_NY  = 2,      // America/New_York
                      TZ_TKY = 3,      // Asia/Tokyo
                      TZ_EXC = 4       // Exchange (server clock)
                    };
enum ENUM_ZCLOSE    { ZC_OFF = 0,      // Off
                      ZC_50  = 1,      // 50%
                      ZC_TOP = 2       // Top
                    };
enum ENUM_M10ENTRY  { ME_IMM    = 0,   // IMMEDIATE
                      ME_RETEST = 1,   // RETEST
                      ME_BOTH   = 2    // BOTH
                    };
enum ENUM_ENTRYPX   { EP_CLOSE   = 0,  // CLOSE
                      EP_CANDLE  = 1,  // CANDLE 50%
                      EP_ZONE    = 2,  // ZONE EDGE
                      EP_RETRACE = 3   // RETRACE
                    };
enum ENUM_PANELPOS  { PP_BR = 0,       // Bottom right
                      PP_TR = 1,       // Top right
                      PP_BL = 2,       // Bottom left
                      PP_TL = 3        // Top left
                    };

//+------------------------------------------------------------------+
//| INPUTS                                                           |
//+------------------------------------------------------------------+
input group "0 · MT5 port"
input int             i_calcBars   = 5000;      // Bars to calculate (history depth)
input int             i_srvGmt     = -99;       // Server GMT offset, hours (-99 = auto from terminal)
input string          i_font       = "Arial";   // Label font
input bool            i_alertPopup = true;      // Alert: popup
input bool            i_alertPush  = false;     // Alert: push notification
input bool            i_alertEvt   = false;     // Alert: structure / zone events too
input ENUM_PANELPOS   i_panelPos   = PP_BR;     // Panel position
input bool            i_panelShift = true;      // Right panel: shift the chart so the newest bars stay clear of it
input int             i_panelFont  = 8;         // Panel font size

input group "1 · General"
input int             i_atrLen     = 14;        // ATR length
input int             i_swingLen   = 5;         // Swing length (each side)
input int             i_maxLabels  = 200;       // Max labels
input int             i_maxLines   = 100;       // Max lines
input int             i_minGap     = 6;         // Min bars between labels (same side)
input ENUM_LBLMODE    i_lblMode    = LBL_SIGNALS; // Label density
input ENUM_SETMODE    i_setMode    = SET_CUSTOM;  // Setup master mode

input group "2 · Candle (L0)"
input double          i_pinMult    = 2.0;       // Pin bar wick >= N x body
input double          i_pinRatio   = 0.55;      // Pin bar wick/range min
input double          i_dojiMax    = 0.10;      // Doji max body/range
input double          i_largeMult  = 1.5;       // Large range x ATR
input double          i_longWick   = 0.50;      // Long-wick rejection wick/range
input double          i_haramiMax  = 0.60;      // Harami body < N x prev
input double          i_starProx   = 1.0;       // Shooting star proximity x ATR
input double          i_ifcMult    = 2.0;       // IFC wick >= N x body
input bool            i_ifcAnyCol  = false;     // IFC allow any colour
input double          i_manipWick  = 0.30;      // Manipulative min wick/range

input group "3 · Structure (L1)"
input int             i_rangeBars  = 40;        // Bars without BOS/CHoCH -> RANGE
input ENUM_DISPGATE   i_dispGate   = DG_CANDLE; // Structure needs displacement
input double          i_dispBody   = 0.5;       // Displacement body/range >=
input double          i_dispRng    = 0.6;       // Displacement range >= x ATR
input double          i_dispDist   = 0.3;       // ...or close beyond level >= x ATR
input int             i_pendBars   = 3;         // Weak break: follow-through window (bars)
input int             i_failMax    = 2;         // Failed follow-throughs -> RANGE
input bool            i_cisdSweep  = true;      // CISD only after a qualified liquidity sweep

input group "4 · FVG / Strength (L2)"
input double          i_fvgMin     = 0.10;      // Min FVG height x ATR
input ENUM_FVGMIT     i_fvgMode    = FM_TOUCH;  // FVG mitigation mode
input int             i_maxFvg     = 40;        // Max FVGs tracked
input int             i_fvgAge     = 300;       // Drop mitigated FVG after N bars
input int             i_minFvgStr  = 1;         // Min FVG for STRONG (never 0)
input double          i_bodyEff    = 0.55;      // STRONG min body efficiency
input double          i_mixMax     = 0.35;      // STRONG max mixed ratio
input double          i_speedMin   = 0.35;      // STRONG min speed
input int             i_maxMove    = 150;       // Max bars scanned per move

input group "5 · Liquidity (L3)"
input double          i_eqTol      = 0.10;      // Equal H/L tolerance x ATR
input double          i_touchTol   = 0.15;      // Touch tolerance x ATR
input int             i_touchCd    = 3;         // Touch cooldown (bars)
input int             i_extLB      = 50;        // External liquidity lookback
input bool            i_showPD     = true;      // PDH/PDL (intraday)
input bool            i_showPW     = true;      // PWH/PWL (<= daily)
input double          i_runBody    = 0.60;      // RUN min body ratio
input double          i_runClose   = 0.25;      // RUN min close beyond x ATR
input double          i_sweepWick  = 0.50;      // SWEEP min wick ratio
input ENUM_SWEEPQUAL  i_sweepQual  = SQ_MAJOR;  // Sweep arms setups when the level is
input int             i_failBars   = 2;         // Failed-close window (bars)
input bool            i_idmSweep   = true;      // Internal sweep qualifies at a confirmed zone in HTF-aligned discount/premium
input int             i_maxLevels  = 30;        // Max liquidity levels

input group "6 · Zones (L4)"
input int             i_maxZones   = 30;        // Max zones tracked
input int             i_zoneAge    = 500;       // Drop untouched zone after N bars
input double          i_zoneMaxH   = 3.0;       // Zone max height x ATR
input int             i_sweepWin   = 10;        // OB V5: sweep within N bars before OB
input double          i_rjbWick    = 0.50;      // Rejection block min wick ratio
input int             i_rjbBars    = 15;        // Rejection block confirm BOS within N bars
input int             i_qmBars     = 60;        // QM max bars after CHoCH
input int             i_klLeft     = 50;        // Key level hidden-interest lookback
input int             i_klMin      = 3;         // Key level min criteria to show (3-5)
input bool            i_srTrade    = false;     // Count UNSCORED pivot wick zones as tradable zones
input bool            i_obHpOnly   = false;     // OB: high-probability (liquidity hunt) only
input bool            i_rcbFib     = true;      // Reclaimed: enforce 50% fib
input bool            i_rjbPend    = true;      // M10 may trade an unconfirmed RJB ? (HTF-aligned discount sweep only)
input bool            i_klVol      = false;     // Key level volume criterion
input double          i_klVolMult  = 1.5;       // Key level volume x SMA(volume)
input double          i_tlTol      = 0.30;      // Trendline zone +- x ATR
input ENUM_TLANCHOR   i_tlAnchor   = TL_WICK;   // Trendline anchor
input int             i_propWin    = 10;        // Propulsion: re-departure window (bars after tap)
input double          i_propImp    = 0.8;       // Propulsion: re-departure size x ATR
input bool            i_tlConfirm  = false;     // M64: trendline needs a confirming touch

input group "7 · HTF (L5)"
input ENUM_HTFMODE    i_mode       = HM_CONS;   // HTF pairing
input ENUM_TIMEFRAMES i_manual     = PERIOD_H1; // Manual HTF
input ENUM_GATE3      i_gate       = G3_WARN;   // HTF bias gate
input ENUM_GATETREND  i_gateTrend  = GT_ENTER;  // Trend the gate reads
input int             i_htfSwing   = 3;         // HTF pivot length
input bool            i_ltfPb      = true;      // LTF-only trend flip = pullback (continuation not blocked)
input int             i_sweepVal   = 3;         // HTF sweep valid for N HTF bars
input int             i_cLook      = 3;         // HTF candle levels: candles shown
input double          i_rejW       = 0.50;      // HTF rejection min wick ratio

input group "8 · Setup filters (L6)"
input int             i_volLen     = 20;        // Volume SMA length
input double          i_retestBR   = 0.7;       // Retest body ratio (M31)
input double          i_nearZone   = 3.0;       // Liquidity scan distance x ATR (M09)
input int             i_rangeLen   = 20;        // Range detection length (panel regime row)
input double          i_rangeMax   = 3.0;       // Range max width x ATR
input int             i_armBars    = 30;        // Armed setup stays valid N bars
input ENUM_ENTRYCONF  i_entryConfirm = EC_CONF; // Zone entry trigger
input int             i_poiBars    = 8;         // Confirm within (bars)
input double          i_confDist   = 0.10;      // Confirm: close beyond reference >= x ATR
input double          i_confBody   = 0.40;      // Confirm: body/range >=
input ENUM_M10CONF    i_m10Conf    = M10_OFF;   // M10 confirm

input group "9a · Premium / Discount + Sessions"
input bool            i_pdOn       = true;      // Score premium/discount position
input bool            i_pdGate     = false;     // Block longs in premium / shorts in discount
input double          i_pdDeep     = 0.75;      // Deep-premium / deep-discount threshold
input bool            i_pdCont     = true;      // Block CONTINUATION modules in deep premium / discount
input bool            i_hpd        = true;      // HTF dealing range: discount/premium +1, deep = continuation block
input bool            i_ssnOn      = false;     // Only signal inside a killzone
input bool            i_ssnScore   = true;      // Score London / NY sessions
input ENUM_SSNTZ      i_ssnTz      = TZ_NY;     // Session timezone
input string          i_ssnAsia    = "2000-0000"; // Asia session (HHMM-HHMM)
input string          i_ssnLon     = "0200-0500"; // London session
input string          i_ssnNY      = "0700-1000"; // NY session
input bool            i_ssnFx      = true;      // Killzone filter auto-on for forex / CFD symbols
input bool            i_ssnLvl     = true;      // Asia session high / low as liquidity (SESH / SESL)
input bool            i_nyOpen     = true;      // Score NY midnight open (buy below / sell above)

input group "9 · Visual · Colors"
input color           i_cBull      = C'8,153,129';   // Bull
input color           i_cBear      = C'242,54,69';   // Bear
input color           i_cNeut      = C'120,123,134'; // Neutral
input color           i_cPool      = C'255,152,0';   // Pool
input color           i_cSR        = C'120,123,134'; // S/R
input color           i_cBrk       = C'156,39,176';  // Breaker
input color           i_cRcb       = C'0,188,212';   // Reclaimed
input color           i_cRjb       = C'255,152,0';   // Rejection
input color           i_cQm        = C'233,30,99';   // QM
input color           i_cHtf       = C'41,98,255';   // HTF / Entry
input color           i_cInv       = C'120,123,134'; // Invalid / weak
input color           i_cTxt       = clrWhite;       // Text (panel)
input int             i_boxT       = 85;        // Zone/FVG box transparency (0-100, blended)
input int             i_lineT      = 30;        // Line transparency (0-100, blended)
input int             i_sz         = 9;         // Label font size
input int             i_zsz        = 8;         // Zone / level text size
input double          i_off        = 0.30;      // Label offset x ATR
input bool            i_lblFilled  = true;      // Filled label boxes (TradingView style; off = text only)
input int             i_fillT      = 15;        // Label fill transparency (0-100, blended)
input int             i_bgT        = 92;        // HTF bias tint transparency (0-100)

input group "10 · Show"
input bool            d_struct     = true;      // Structure: BOS/CHoCH/CISD labels + major H/L
input bool            d_pb         = false;     // Structure: valid pullback PB
input bool            d_weakBos    = false;     // Label weak BOS (line always drawn)
input bool            d_cisdAll    = false;     // Label every CISD (off = counter-trend only)
input bool            d_fvg        = true;      // FVG boxes
input bool            d_fvgMit     = false;     // Keep mitigated FVG (faded)
input bool            d_liq        = true;      // Liquidity lines
input bool            d_liqEvt     = true;      // Sweep / run events
input bool            d_liqAll     = false;     // Label every BSL/SSL sweep/run
input bool            d_obDiag     = false;     // OB diagnostics labels (T5 / T3)
input bool            d_ob         = true;      // OB / S&D
input bool            d_brk        = true;      // Breaker
input bool            d_kl         = true;      // Key levels
input bool            d_sr         = false;     // S/R wick zones
input bool            d_rcb        = true;      // Reclaimed
input bool            d_rjb        = true;      // Rejection
input bool            d_qm         = true;      // QM
input bool            d_htf        = true;      // HTF candle levels
input bool            d_htfEvt     = true;      // HTF sweep / manip events
input bool            d_bg         = true;      // HTF bias tint
input bool            d_candle     = false;     // Candle pattern tags (L0 debug)
input bool            d_panel      = true;      // Info panel
input bool            d_legend     = false;     // Legend
input bool            d_sig        = true;      // Setup signals (L6)

input group "11 · Setups A–I (toggle)"
input bool            e_M01        = true;      // M01 Breakout rejection trap
input bool            e_M02        = true;      // M02 Pin bar liquidity trap
input bool            e_M05        = true;      // M05 Pin bar after breakout
input bool            e_M08        = true;      // M08 Pin bar on retracement
input bool            e_M09        = true;      // M09 Pin bar + liquidity
input bool            e_M10        = true;      // M10 Sweep reversal
input bool            e_M15        = true;      // M15 Breakout with pin bar
input bool            e_M33        = true;      // M33 Zone flip model
input bool            e_M36        = true;      // M36 Weak retracement on OB
input bool            e_M37        = true;      // M37 Inducement block

input group "12 · Setup filters"
input bool            fl_M19       = true;      // M19 suppress reversal after STRONG arrival
input bool            fl_M26       = true;      // M26 pullback must be corrective (mixed)
input bool            fl_M31       = false;     // M31 retest body-size rule
input bool            fl_SwR       = true;      // §6.2 block reversal at touch>=2 unless swept
input bool            fl_50        = true;      // §6.6 S&D 50% rule
input bool            fl_M01T      = true;      // M01/M02 require the broken level rejected >=2x
input ENUM_ZCLOSE     i_zClose     = ZC_50;     // Zone reversal must close beyond

input group "13 · Setups J–R (toggle)"
input bool            e_M39        = true;      // M39 Reclaimed block retest
input bool            e_M40        = true;      // M40 Rejection block retest
input bool            e_M41        = true;      // M41 Sweep + FVG confluence
input bool            e_M42        = true;      // M42 High-probability S&D
input bool            e_M45        = true;      // M45 Sweep-based CHoCH retest
input bool            e_M46        = true;      // M46 CISD setup
input bool            e_M51        = true;      // M51 Smart BOS model
input bool            e_M54        = true;      // M54 Smart S&D trap

input group "15 · Setups S–AB (toggle)"
input bool            e_M58        = true;      // M58 Double top / bottom
input bool            e_M62        = true;      // M62 Fakeout trap
input bool            e_M64        = true;      // M64 Auto trendline (draw)
input bool            e_M68        = true;      // M68 HTF sweep -> LTF entry
input bool            e_M69        = true;      // M69 IFC candle
input bool            e_M70        = true;      // M70 Quasimodo
input bool            e_M72        = true;      // M72 Operator trap
input bool            e_M73        = true;      // M73 Propulsion Block (ICT)
input bool            e_M74        = true;      // M74 MSS -> FVG retrace limit (ICT)

input group "16 · S–AB parameters"
input double          i_dtTol      = 0.15;      // Double top tolerance x ATR
input int             i_consMin    = 4;         // M72 consolidation min bars
input double          i_consMax    = 1.5;       // M72 consolidation max width x ATR

input group "14 · Trade (L7)"
input double          i_slBuf      = 0.15;      // SL buffer x ATR
input double          i_maxSL      = 2.0;       // Max SL distance x ATR (major HL/LH rule)
input double          i_minRR      = 2.0;       // Min R:R — signals below this are hidden
input double          i_maxRR      = 6.0;       // Max R:R — further target = FAR
input bool            i_fixedR     = false;     // Fixed-R mode
input double          i_fixedRm    = 2.0;       // Fixed R multiple (TP1; TP2 = +1R)
input bool            i_rrReal     = true;      // Require a REAL target at Min R:R
input ENUM_GATE3      i_tpPath     = G3_STRICT; // TP1 path check
input int             i_minScore   = 8;         // Min score to show
input int             i_gradeAp    = 11;        // A+ >=
input int             i_gradeA     = 9;         // A >=
input int             i_sigGap     = 5;         // Min bars between signals (both sides)
input int             i_idBars     = 50;        // Suppress a repeat of the SAME setup for N bars
input ENUM_M10ENTRY   i_entryMode  = ME_IMM;    // M10 entry mode
input ENUM_ENTRYPX    i_entryPx    = EP_CLOSE;  // Entry price
input int             i_retBars    = 12;        // RETRACE: limit valid (bars)
input double          i_autoRet    = 1.5;       // Auto-RETRACE when confirming candle >= x ATR (0 = off)
input int             i_m74Bars    = 20;        // M74: limit valid (bars)
input int             i_minRiskT   = 20;        // Min risk (ticks)
input double          i_minRiskA   = 0.3;       // ... or x ATR
input bool            i_tradeLn    = true;      // Draw entry / SL / TP lines
input int             i_tradeBars  = 20;        // Trade line length (bars)

//+------------------------------------------------------------------+
//| na (NaN) helpers — Pine `na` propagates through arithmetic and   |
//| compares false; IEEE NaN does the same                           |
//+------------------------------------------------------------------+
union UDL { double d; long l; };
double NaNv() { UDL u; u.l = 0x7FF8000000000000; return u.d; }
#define NA NaNv()
bool   isna(const double x)               { return !MathIsValidNumber(x); }
double nz(const double x, const double y) { return isna(x) ? y : x; }
string fmtPx(const double x)              { return isna(x) ? "—" : DoubleToString(x, _Digits); }

//+------------------------------------------------------------------+
//| per-bar series (oldest first). g_bi = Pine bar_index             |
//+------------------------------------------------------------------+
double   gO[], gH[], gL[], gC[], gV[], gATR[];
datetime gT[];
int      g_bi   = 0;
int      g_last = 0;      // index of the newest (forming) bar

double O(const int k) { int j = g_bi - k; if(j < 0) j = 0; return gO[j]; }
double H(const int k) { int j = g_bi - k; if(j < 0) j = 0; return gH[j]; }
double L(const int k) { int j = g_bi - k; if(j < 0) j = 0; return gL[j]; }
double C(const int k) { int j = g_bi - k; if(j < 0) j = 0; return gC[j]; }
double Vo(const int k){ int j = g_bi - k; if(j < 0) j = 0; return gV[j]; }

double HighestH(const int len, const int off)
{
   double v = -DBL_MAX;
   for(int k = off; k < off + len; k++) v = MathMax(v, H(k));
   return v;
}
double LowestL(const int len, const int off)
{
   double v = DBL_MAX;
   for(int k = off; k < off + len; k++) v = MathMin(v, L(k));
   return v;
}
// ta.pivothigh(high, n, n) evaluated at bar j: centre j-n; left side may tie, right side strict
double PivotHighAt(const int j, const int n)
{
   int c = j - n;
   if(c - n < 0 || j > g_last) return NA;
   double v = gH[c];
   for(int k = 1; k <= n; k++)
   {
      if(gH[c - k] > v)  return NA;
      if(gH[c + k] >= v) return NA;
   }
   return v;
}
double PivotLowAt(const int j, const int n)
{
   int c = j - n;
   if(c - n < 0 || j > g_last) return NA;
   double v = gL[c];
   for(int k = 1; k <= n; k++)
   {
      if(gL[c - k] < v)  return NA;
      if(gL[c + k] <= v) return NA;
   }
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
string SShift(string &a[])
{
   int n = ArraySize(a);
   if(n == 0) return "";
   string r = a[0];
   for(int k = 0; k < n - 1; k++) a[k] = a[k + 1];
   ArrayResize(a, n - 1, 64);
   return r;
}
bool StartsWith(const string s, const string p) { return StringLen(p) > 0 && StringFind(s, p) == 0; }
bool Contains(const string s, const string p)   { return StringFind(s, p) >= 0; }

//+------------------------------------------------------------------+
//| colours: Pine transparency -> blend with the chart background    |
//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
//| chart objects (Pine box / line / label)                          |
//+------------------------------------------------------------------+
#define PFX "SMC854_"
long g_objN = 0;
string NewName() { g_objN++; return PFX + IntegerToString(g_objN); }

datetime X2T(int x)
{
   if(x < 0) x = 0;
   if(x <= g_last) return gT[x];
   return gT[g_last] + (datetime)((long)(x - g_last) * PeriodSeconds());
}
// f_xb — Pine pins old anchors to the 500-bar drawing buffer edge; kept for parity (dotted = clamped)
int XB(const int x) { return MathMax(MathMin(x, g_bi), g_bi - 495); }

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
   return n;
}
void LineDel(const string n)                       { if(n != "") ObjectDelete(0, n); }
void LineSetX2(const string n, const int x)        { if(n != "") ObjectSetInteger(0, n, OBJPROP_TIME, 1, X2T(x)); }
void LineSetY(const string n, const double y)      { if(n != "") { ObjectSetDouble(0, n, OBJPROP_PRICE, 0, y); ObjectSetDouble(0, n, OBJPROP_PRICE, 1, y); } }
void LineSetStyle(const string n, const ENUM_LINE_STYLE s) { if(n != "") ObjectSetInteger(0, n, OBJPROP_STYLE, s); }
void LineSetColor(const string n, const color c)   { if(n != "") ObjectSetInteger(0, n, OBJPROP_COLOR, c); }
void LineSetWidth(const string n, const int w)     { if(n != "") ObjectSetInteger(0, n, OBJPROP_WIDTH, w); }
void LineSetRay(const string n, const bool r)      { if(n != "") ObjectSetInteger(0, n, OBJPROP_RAY_RIGHT, r); }

string TextNew(const int x, const double y, const string s, const color tc, const ENUM_ANCHOR_POINT anc, const int fs, const string tip)
{
   if(isna(y)) return "";
   string n = NewName();
   if(!ObjectCreate(0, n, OBJ_TEXT, 0, X2T(x), y)) return "";
   ObjectSetString(0, n, OBJPROP_TEXT, s);
   ObjectSetString(0, n, OBJPROP_FONT, i_font);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, fs);
   ObjectSetInteger(0, n, OBJPROP_COLOR, tc);
   ObjectSetInteger(0, n, OBJPROP_ANCHOR, anc);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   if(tip != "") ObjectSetString(0, n, OBJPROP_TOOLTIP, tip);
   return n;
}
void TextDel(const string n)                       { if(n != "") ObjectDelete(0, n); }
void TextSet(const string n, const string s)       { if(n != "") ObjectSetString(0, n, OBJPROP_TEXT, s); }
void TextSetColor(const string n, const color c)   { if(n != "") ObjectSetInteger(0, n, OBJPROP_COLOR, c); }

// box = record painted on the transparent canvas layer (fill, real alpha) + optional border rectangle "<name>b"
// (unfilled object) + text "<name>t". MT5 XOR-mixes overlapping FILLED rectangles (two light zones -> a black band),
// so no filled rectangle object is used anywhere.
struct BoxRec { string n; datetime t1, t2; double p1, p2; color c; int tr; };
BoxRec g_boxes[];
int BoxFind(const string n)
{
   for(int k = ArraySize(g_boxes) - 1; k >= 0; k--) if(g_boxes[k].n == n) return k;
   return -1;
}
string BoxNew(const int x1, const double top, const int x2, const double bot, const color c, const int tr, const string txt, const bool border)
{
   if(isna(top) || isna(bot)) return "";
   string n = NewName();
   BoxRec r; r.n = n; r.t1 = X2T(x1); r.t2 = X2T(x2); r.p1 = top; r.p2 = bot; r.c = c; r.tr = tr;
   int k = ArraySize(g_boxes);
   ArrayResize(g_boxes, k + 1, 64);
   g_boxes[k] = r;
   if(border)
   {
      string b = n + "b";
      ObjectCreate(0, b, OBJ_RECTANGLE, 0, r.t1, top, r.t2, bot);
      ObjectSetInteger(0, b, OBJPROP_COLOR, Col(c, 40));
      ObjectSetInteger(0, b, OBJPROP_FILL, false);
      ObjectSetInteger(0, b, OBJPROP_BACK, false);
      ObjectSetInteger(0, b, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, b, OBJPROP_HIDDEN, true);
   }
   if(txt != "")
   {
      string t = n + "t";
      ObjectCreate(0, t, OBJ_TEXT, 0, r.t1, top);
      ObjectSetString(0, t, OBJPROP_TEXT, txt);
      ObjectSetString(0, t, OBJPROP_FONT, i_font);
      ObjectSetInteger(0, t, OBJPROP_FONTSIZE, i_zsz);
      ObjectSetInteger(0, t, OBJPROP_COLOR, g_fgCol);
      ObjectSetInteger(0, t, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, t, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, t, OBJPROP_HIDDEN, true);
   }
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
void BoxSetRightT(const string n, const datetime t)
{
   if(n == "") return;
   int k = BoxFind(n);
   if(k >= 0) g_boxes[k].t2 = t;
   ObjectSetInteger(0, n + "b", OBJPROP_TIME, 1, t);
}
void BoxSetRight(const string n, const int x) { BoxSetRightT(n, X2T(x)); }
void BoxSetColor(const string n, const color c, const int tr)
{
   if(n == "") return;
   int k = BoxFind(n);
   if(k >= 0) { g_boxes[k].c = c; g_boxes[k].tr = tr; }
}
void BoxSetBorder(const string n, const color c, const int w, const ENUM_LINE_STYLE sty)
{
   if(n == "" || ObjectFind(0, n + "b") < 0) return;
   ObjectSetInteger(0, n + "b", OBJPROP_COLOR, c);
   ObjectSetInteger(0, n + "b", OBJPROP_WIDTH, w);
   ObjectSetInteger(0, n + "b", OBJPROP_STYLE, sty);
}
void BoxSetText(const string n, const string s)
{
   if(n == "") return;
   string t = n + "t";
   if(ObjectFind(0, t) < 0)
   {
      int k = BoxFind(n);
      if(k < 0) return;
      ObjectCreate(0, t, OBJ_TEXT, 0, g_boxes[k].t1, MathMax(g_boxes[k].p1, g_boxes[k].p2));
      ObjectSetString(0, t, OBJPROP_FONT, i_font);
      ObjectSetInteger(0, t, OBJPROP_FONTSIZE, i_zsz);
      ObjectSetInteger(0, t, OBJPROP_COLOR, g_fgCol);
      ObjectSetInteger(0, t, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, t, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, t, OBJPROP_HIDDEN, true);
   }
   ObjectSetString(0, t, OBJPROP_TEXT, s);
}

//+------------------------------------------------------------------+
//| filled labels (Pine label.style_label_up / down): OBJ_EDIT boxes |
//| anchored to time / price, re-placed on every chart scroll / zoom |
//+------------------------------------------------------------------+
struct LabelRec { string n; datetime t; double y; bool up; int w; int h; };
LabelRec g_lbls[];
int g_panW = 0, g_panH = 0;      // info panel size in pixels (labels under it are hidden)

void LblMeasure(const string s, int &w, int &h)
{
   TextSetFont(i_font, -i_sz * 10);
   uint tw = 0, th = 0;
   TextGetSize(s, tw, th);
   w = (int)tw + 12;
   h = (int)th + 6;
}
void LblPlace(const int k, const int cw, const int ch)
{
   string n = g_lbls[k].n;
   if(!i_lblFilled || n == "") return;
   int x = 0, y = 0;
   bool ok = ChartTimePriceToXY(0, 0, g_lbls[k].t, g_lbls[k].y, x, y);
   int w = g_lbls[k].w, h = g_lbls[k].h;
   int lx = x - w / 2;
   int ly = g_lbls[k].up ? y : y - h;
   bool vis = ok && lx + w > 0 && lx < cw && ly + h > 0 && ly < ch;
   // the info panel sits in the bottom-right corner: a label under it would cover the table
   if(vis && d_panel && g_panW > 0)
   {
      bool pr = i_panelPos == PP_BR || i_panelPos == PP_TR, pl = i_panelPos == PP_BR || i_panelPos == PP_BL;
      int px0 = pr ? cw - g_panW - 18 : 0, px1 = pr ? cw : g_panW + 18;
      int py0 = pl ? ch - g_panH - 18 : 0, py1 = pl ? ch : g_panH + 18;
      if(lx + w > px0 && lx < px1 && ly + h > py0 && ly < py1) vis = false;
   }
   if(vis)
   {
      ObjectSetInteger(0, n, OBJPROP_XDISTANCE, MathMax(lx, 0));
      ObjectSetInteger(0, n, OBJPROP_YDISTANCE, MathMax(ly, 0));
      ObjectSetInteger(0, n, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
   }
   else ObjectSetInteger(0, n, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);
}
void LblPlaceAll()
{
   if(!i_lblFilled) return;
   int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS, 0);
   int ch = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   for(int k = 0; k < ArraySize(g_lbls); k++) LblPlace(k, cw, ch);
}
string LblCreate(const bool up, const double y, const string s, const string tip, const color col)
{
   if(isna(y)) return "";
   if(!i_lblFilled)
      return TextNew(g_bi, y, s, col, up ? ANCHOR_UPPER : ANCHOR_LOWER, i_sz, tip);
   string n = NewName();
   if(!ObjectCreate(0, n, OBJ_EDIT, 0, 0, 0)) return "";
   int w, h;
   LblMeasure(s, w, h);
   color bg = Col(col, i_fillT);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_READONLY, true);
   ObjectSetInteger(0, n, OBJPROP_ALIGN, ALIGN_CENTER);
   ObjectSetString(0, n, OBJPROP_FONT, i_font);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, i_sz);
   ObjectSetInteger(0, n, OBJPROP_COLOR, i_cTxt);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_BORDER_COLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetString(0, n, OBJPROP_TEXT, s);
   if(tip != "") ObjectSetString(0, n, OBJPROP_TOOLTIP, tip);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, n, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);    // placed after the history pass
   return n;
}
void LblPush(const string n, const bool up, const double y)
{
   LabelRec r; r.n = n; r.t = gT[g_bi]; r.y = y; r.up = up; r.w = 0; r.h = 0;
   if(i_lblFilled) LblMeasure(ObjectGetString(0, n, OBJPROP_TEXT), r.w, r.h);
   int k = ArraySize(g_lbls);
   ArrayResize(g_lbls, k + 1, 64);
   g_lbls[k] = r;
   while(ArraySize(g_lbls) > i_maxLabels) { ObjectDelete(0, g_lbls[0].n); ARemove(g_lbls, 0); }
}

//+------------------------------------------------------------------+
//| TYPES (Pine UDTs). Pine objects are references; here arrays are  |
//| addressed by index so every mutation lands on the stored element |
//+------------------------------------------------------------------+
struct Cndl
{
   double body, rng, upWick, dnWick, bodyRatio, upWickRatio, dnWickRatio;
   bool   isBull, isBear, largeRange, pinBull, pinBear, doji, engulfBull, engulfBear, insideBar, harami,
          longWickRej, starBear, starBull, ifcBull, ifcBear, manipBull, manipBear;
   void Reset()
   {
      body = 0; rng = 0; upWick = 0; dnWick = 0; bodyRatio = 0; upWickRatio = 0; dnWickRatio = 0;
      isBull = false; isBear = false; largeRange = false; pinBull = false; pinBear = false; doji = false;
      engulfBull = false; engulfBear = false; insideBar = false; harami = false; longWickRej = false;
      starBear = false; starBull = false; ifcBull = false; ifcBear = false; manipBull = false; manipBear = false;
   }
   Cndl() { Reset(); }
};

struct St   // Pine `Struct`
{
   bool   swingHigh, swingLow, bullBOS, bearBOS, bullSweep, bearSweep, bullCHoCH, bearCHoCH;
   bool   internalBullBOS, internalBearBOS, weakBullBOS, weakBearBOS, pbValidUp, pbValidDn, cisdBull, cisdBear;
   double chLvl;
   int    chIdx;
   string trend, movePhase;
   void Reset()
   {
      swingHigh = false; swingLow = false; bullBOS = false; bearBOS = false; bullSweep = false; bearSweep = false;
      bullCHoCH = false; bearCHoCH = false; internalBullBOS = false; internalBearBOS = false; weakBullBOS = false;
      weakBearBOS = false; pbValidUp = false; pbValidDn = false; cisdBull = false; cisdBear = false;
      chLvl = NA; chIdx = 0; trend = "RANGE"; movePhase = "IMPULSIVE";
   }
   St() { Reset(); }
};

struct Fvg
{
   double top, bottom;
   int    idx;
   bool   isBull, mitigated;
   int    mitIdx;
   string bx;
   Fvg() { top = NA; bottom = NA; idx = 0; isBull = true; mitigated = false; mitIdx = 0; bx = ""; }
};

struct Move
{
   bool   strong;
   int    fvgCount;
   double bodyEff, mixed, speed, avgBody;
   Move() { strong = false; fvgCount = 0; bodyEff = 0; mixed = 0; speed = 0; avgBody = 0; }
};

struct Liq
{
   double price;
   int    idx;
   bool   isHigh;
   string kind;
   bool   ext;
   int    touches, lastTouch, pend;
   bool   done, pooled;
   string result;
   double wickX;
   string ln, lb;
   Liq() { price = NA; idx = 0; isHigh = true; kind = "BSL"; ext = false; touches = 1; lastTouch = 0; pend = 0;
           done = false; pooled = false; result = ""; wickX = NA; ln = ""; lb = ""; }
};

struct Zone
{
   string kind;
   bool   bull;
   double top, bottom;
   int    idx, touches, lastTouch;
   bool   tapped, fiftyHit, broken;
   int    brokenAt;
   bool   flipped, sweepReq, hp, weak, confirmed;
   int    pendFvg, kl;
   double idmLvl;
   bool   idmSwept;
   double nearMiss;
   bool   nearSwept;
   string obType;
   bool   depStrong, prop;
   string bx;
   Zone() { kind = "SR"; bull = true; top = NA; bottom = NA; idx = 0; touches = 0; lastTouch = 0; tapped = false;
            fiftyHit = false; broken = false; brokenAt = 0; flipped = false; sweepReq = false; hp = false; weak = false;
            confirmed = true; pendFvg = 0; kl = 0; idmLvl = NA; idmSwept = false; nearMiss = NA; nearSwept = false;
            obType = ""; depStrong = false; prop = false; bx = ""; }
};

// S9 — zone snapshot, one per side
struct ZS
{
   string kind;
   int    touches;
   bool   sweepReq, fifty, idm, hp;
   int    kl;
   bool   flipped, nearSwept, depStrong;
   double top, bottom;
   bool   prop;
   int    arr;
   double arrMix;
   bool   pend;
   int    sw;
   void Reset() { kind = ""; touches = 0; sweepReq = false; fifty = false; idm = false; hp = false; kl = 0; flipped = false;
                  nearSwept = false; depStrong = false; top = NA; bottom = NA; prop = false; arr = 0; arrMix = 0; pend = false; sw = 0; }
   ZS() { Reset(); }
};

struct Ctx
{
   double curHigh, prevHigh; int curHighIdx, prevHighIdx; bool hiBroken;
   double curLow, prevLow;   int curLowIdx, prevLowIdx;   bool loBroken;
   double majorHigh; int majorHighIdx; double majorLow; int majorLowIdx;
   string trend; int barsSinceEvt;
   double hiMakerHigh, hiMakerLow; bool pbUpArmed; double loMakerLow, loMakerHigh; bool pbDnArmed;
   double cisdUpOpen; int cisdUpBar; double cisdDnOpen; int cisdDnBar;
   int    sweptHighBar, sweptLowBar;
   bool   qmBullPend; double qmBullLL; int qmBullAt; bool qmBearPend; double qmBearHH; int qmBearAt;
   double hCurHigh, hPrevHigh; bool hHiBroken; double hCurLow, hPrevLow; bool hLoBroken;
   double hMajorHigh, hMajorLow; string hTrend; int hBarCount;
   int    sweepUpAt, sweepDnAt;
   double upW1, upW2, dnW1, dnW2, upR1, upR2, dnR1, dnR2;
   int    breakDir; double breakLvl; int breakBar; double breakLo, breakHi;
   bool   lastDepStrong; int lastBOSBar; double lastBOSAvgBody; bool chochReal;
   bool   arrivalStrong; int arrivalBar, arrivalDir; double arrivalAvgBody, arrivalMixed;
   int    m41Dir, m41Bar, m45Dir, m45Bar, m46Dir, m46Bar, m54Stage, m54Bar, m54StageB, m54BarB;
   int    bullFvgBar, bearFvgBar; string lastEvt; int lastEvtBar; bool fiftyPrev; int brkTouch; int legIdx; double legPx;
   void Reset()
   {
      curHigh = NA; prevHigh = NA; curHighIdx = 0; prevHighIdx = 0; hiBroken = false;
      curLow = NA; prevLow = NA; curLowIdx = 0; prevLowIdx = 0; loBroken = false;
      majorHigh = NA; majorHighIdx = 0; majorLow = NA; majorLowIdx = 0;
      trend = "RANGE"; barsSinceEvt = 0;
      hiMakerHigh = NA; hiMakerLow = NA; pbUpArmed = false; loMakerLow = NA; loMakerHigh = NA; pbDnArmed = false;
      cisdUpOpen = NA; cisdUpBar = 0; cisdDnOpen = NA; cisdDnBar = 0;
      sweptHighBar = -999; sweptLowBar = -999;
      qmBullPend = false; qmBullLL = NA; qmBullAt = 0; qmBearPend = false; qmBearHH = NA; qmBearAt = 0;
      hCurHigh = NA; hPrevHigh = NA; hHiBroken = false; hCurLow = NA; hPrevLow = NA; hLoBroken = false;
      hMajorHigh = NA; hMajorLow = NA; hTrend = "NEUTRAL"; hBarCount = 0;
      sweepUpAt = -999; sweepDnAt = -999;
      upW1 = 0; upW2 = 0; dnW1 = 0; dnW2 = 0; upR1 = 0; upR2 = 0; dnR1 = 0; dnR2 = 0;
      breakDir = 0; breakLvl = NA; breakBar = -999; breakLo = NA; breakHi = NA;
      lastDepStrong = false; lastBOSBar = -999; lastBOSAvgBody = 0; chochReal = false;
      arrivalStrong = false; arrivalBar = -999; arrivalDir = 0; arrivalAvgBody = 0; arrivalMixed = 0;
      m41Dir = 0; m41Bar = -999; m45Dir = 0; m45Bar = -999; m46Dir = 0; m46Bar = -999;
      m54Stage = 0; m54Bar = -999; m54StageB = 0; m54BarB = -999;
      bullFvgBar = -999; bearFvgBar = -999; lastEvt = "—"; lastEvtBar = -999; fiftyPrev = false; brkTouch = 0;
      legIdx = 0; legPx = NA;
   }
   Ctx() { Reset(); }
};

struct Sx
{
   int    dtDir, dtBar; double dtNeck;
   int    m62Dir, m62Bar; double m62Lvl;
   int    tlSx1; double tlSy1; int tlSx2; double tlSy2; int tlSTouch; bool tlSBroken;
   int    tlRx1; double tlRy1; int tlRx2; double tlRy2; int tlRTouch; bool tlRBroken;
   int    m68Dir, m68Bar, ifcDir, ifcBar; double ifcHi, ifcLo;
   int    m72Cnt, m72Wick, m72Dir;
   string hiType, loType;
   int    stPendDir, stPendKind, stPendBar; double stPendLvl; int stPendFrom;
   int    stBrkDir; double stBrkLvl; int stBrkBar; int stFail; bool brkInternal;
   double cisdUpRef; int cisdUpRefBar; bool cisdUpUsed; double cisdDnRef; int cisdDnRefBar; bool cisdDnUsed;
   int    poiDirL, poiBarL; double poiRefL, poiLowL; bool poiFvgL; ZS poiZb; bool hasPoiZb;
   int    poiDirS, poiBarS; double poiRefS, poiHighS; bool poiFvgS; ZS poiZs; bool hasPoiZs;
   double poiWickL, poiWickS; int poiSwL, poiSwS;
   double hFvgBT, hFvgBB, hFvgST, hFvgSB; int hFvgBBar, hFvgSBar;
   double m54Zb, m54Zs;
   int    m10Dir, m10Bar; double m10Ref, m10Ext, m10Lvl; string m10Kind;
   void Reset()
   {
      dtDir = 0; dtBar = -999; dtNeck = NA; m62Dir = 0; m62Bar = -999; m62Lvl = NA;
      tlSx1 = 0; tlSy1 = NA; tlSx2 = 0; tlSy2 = NA; tlSTouch = 0; tlSBroken = false;
      tlRx1 = 0; tlRy1 = NA; tlRx2 = 0; tlRy2 = NA; tlRTouch = 0; tlRBroken = false;
      m68Dir = 0; m68Bar = -999; ifcDir = 0; ifcBar = -999; ifcHi = NA; ifcLo = NA;
      m72Cnt = 0; m72Wick = 0; m72Dir = 0; hiType = ""; loType = "";
      stPendDir = 0; stPendKind = 0; stPendBar = -999; stPendLvl = NA; stPendFrom = 0;
      stBrkDir = 0; stBrkLvl = NA; stBrkBar = -999; stFail = 0; brkInternal = false;
      cisdUpRef = NA; cisdUpRefBar = 0; cisdUpUsed = true; cisdDnRef = NA; cisdDnRefBar = 0; cisdDnUsed = true;
      poiDirL = 0; poiBarL = -999; poiRefL = NA; poiLowL = NA; poiFvgL = false; poiZb.Reset(); hasPoiZb = false;
      poiDirS = 0; poiBarS = -999; poiRefS = NA; poiHighS = NA; poiFvgS = false; poiZs.Reset(); hasPoiZs = false;
      poiWickL = 0; poiWickS = 0; poiSwL = 0; poiSwS = 0;
      hFvgBT = NA; hFvgBB = NA; hFvgST = NA; hFvgSB = NA; hFvgBBar = 0; hFvgSBar = 0;
      m54Zb = NA; m54Zs = NA; m10Dir = 0; m10Bar = -999; m10Ref = NA; m10Ext = NA; m10Lvl = NA; m10Kind = "";
   }
   Sx() { Reset(); }
};

struct Feat
{
   bool   newBullFvg, newBearFvg, dispBull, dispBear, lastDepStrong, sweptHigh, sweptLow, sweptHighQ, sweptLowQ;
   bool   runUp, runDn, sweptMajor, runMajor;
   string sweptKind, sweptKindHi, sweptKindLo;
   double sweptPrice, sweptPriceHi, sweptPriceLo, sweptExtHi, sweptExtLo, runPrice;
   int    bslAbove, sslBelow;
   bool   atDemand, newProp, atSupply, atSupport, atResist;
   ZS     zb, zs;
   string evtUp, tipUp, evtDn, tipDn, htfBias;
   int    gateUp, gateDn;
   bool   htfSweepUp, htfSweepDn, htfManipBull, htfManipBear, htfRejBull, htfRejBear;
   bool   upWickInc, upWickDec, dnWickInc, dnWickDec, breakUp, breakDn;
   int    breakAgo;
   bool   fakeBreak, breakPinBull, breakPinBear, chochReal, retestValid, inRange;
   bool   atBullFvg, atBearFvg, atBullFvgF, atBearFvgF;
   bool   sweepBosBull, sweepBosBear, sweepChochBull, sweepChochBear, newObHp, enteredOb50;
   bool   tlSupValid, tlResValid, atTLsup, atTLres;
   int    brkTouches, cisdRel;
   string sessName;
   bool   sbSessOk;
   double pdPct;
   bool   inDiscount, inPremium, pdBeyond;
   int    dispScore, dispDir;
   bool   inHtfFvgB, inHtfFvgS;
   double htfPdPct;
   void Reset()
   {
      newBullFvg = false; newBearFvg = false; dispBull = false; dispBear = false; lastDepStrong = false;
      sweptHigh = false; sweptLow = false; sweptHighQ = false; sweptLowQ = false; runUp = false; runDn = false;
      sweptMajor = false; runMajor = false; sweptKind = ""; sweptKindHi = ""; sweptKindLo = "";
      sweptPrice = NA; sweptPriceHi = NA; sweptPriceLo = NA; sweptExtHi = NA; sweptExtLo = NA; runPrice = NA;
      bslAbove = 0; sslBelow = 0; atDemand = false; newProp = false; atSupply = false; atSupport = false; atResist = false;
      zb.Reset(); zs.Reset();
      evtUp = ""; tipUp = ""; evtDn = ""; tipDn = ""; htfBias = "NEUTRAL"; gateUp = 2; gateDn = 2;
      htfSweepUp = false; htfSweepDn = false; htfManipBull = false; htfManipBear = false; htfRejBull = false; htfRejBear = false;
      upWickInc = false; upWickDec = false; dnWickInc = false; dnWickDec = false; breakUp = false; breakDn = false;
      breakAgo = 999; fakeBreak = false; breakPinBull = false; breakPinBear = false; chochReal = false;
      retestValid = false; inRange = false; atBullFvg = false; atBearFvg = false; atBullFvgF = false; atBearFvgF = false;
      sweepBosBull = false; sweepBosBear = false; sweepChochBull = false; sweepChochBear = false; newObHp = false;
      enteredOb50 = false; tlSupValid = false; tlResValid = false; atTLsup = false; atTLres = false;
      brkTouches = 0; cisdRel = 0; sessName = ""; sbSessOk = false; pdPct = 0.5; inDiscount = false;
      inPremium = false; pdBeyond = false; dispScore = 0; dispDir = 0; inHtfFvgB = false; inHtfFvgS = false; htfPdPct = NA;
   }
   Feat() { Reset(); }
};

struct Best { string n; int s; string t; Best() { n = ""; s = 0; t = ""; } };
struct Tag  { string t; string p; color c; int r; bool arm; Tag() { t = ""; p = ""; c = clrNONE; r = 0; arm = false; } };

struct Sig
{
   string name;
   int    dir;
   double entry, sl, tp1, tp2, tp3, rr;
   int    score;
   string note, tgt;
   void Reset() { name = ""; dir = 0; entry = NA; sl = NA; tp1 = NA; tp2 = NA; tp3 = NA; rr = 0; score = 0; note = ""; tgt = ""; }
   Sig() { Reset(); }
};

//+------------------------------------------------------------------+
//| global state (Pine `var`)                                        |
//+------------------------------------------------------------------+
Ctx  g_cx;
Sx   g_sx;
Feat ft;
St   st;
Cndl cd;
Move mv;
Fvg  g_fvgs[];
Liq  g_lv[];
Zone g_zones[];

// derived input state
bool   tierAll, tierKey, immMode, mssMode, m10Imm;
bool   en_M01, en_M02, en_M05, en_M08, en_M09, en_M10, en_M15, en_M33, en_M36, en_M37, en_M74;
bool   en_M39, en_M40, en_M41, en_M42, en_M45, en_M46, en_M51, en_M54;
bool   en_M58, en_M62, en_M64, en_M68, en_M69, en_M70, en_M72, en_M73;
bool   ssnIntra, ssnFilt, g_fxCfd;
int    ssA0, ssA1, ssL0, ssL1, ssN0, ssN1;
ENUM_TIMEFRAMES g_htfTF;
string g_htfName;

// orchestration vars
double nyOpen = NA;
double asiaHi = NA, asiaLo = NA;
double pdHiB = NA, pdLoS = NA; int pdHiAt = -1, pdLoAt = -1;
double hRunHi = NA, hRunLo = NA, hAncLo = NA, hAncHi = NA;
bool   g_pdIn = false;
// signal engine
Sig    g_sigL, g_sigS;
bool   g_hasL = false, g_hasS = false;
int    sigBar = -999, sigDir = 0, sigScore = 0;
string lastIdent = ""; int lastIdentBar = -999;
Sig    retL, retS; bool hasRetL = false, hasRetS = false;
int    retBarL = -999, retBarS = -999;
double retPxL = NA, retPxS = NA;
string retNameL = "", retNameS = "";
string retLbL = "", retLbS = "";
// drawings
string tradeLns[], lns[], hLines[];
string hiLine = "", loLine = "", tlSupLn = "", tlResLn = "";
int    lastUp = -1, lastDn = -1, upStack = 0, dnStack = 0;
bool   g_live = false;          // true while processing the newest closed bar in real time (alerts)
int    g_lastDone = -1;         // last processed bar index

//+------------------------------------------------------------------+
//| time zones (sessions). Server clock -> UTC -> target zone         |
//+------------------------------------------------------------------+
int g_srvOffSec = 0;
datetime MkTime(const int y, const int mo, const int d, const int h)
{
   MqlDateTime s; s.year = y; s.mon = mo; s.day = d; s.hour = h; s.min = 0; s.sec = 0; s.day_of_week = 0; s.day_of_year = 0;
   return StructToTime(s);
}
int DowOf(const datetime t) { MqlDateTime s; TimeToStruct(t, s); return s.day_of_week; }
// n-th Sunday of month (n >= 1) / last Sunday, as a day number
int NthSunday(const int y, const int mo, const int n)
{
   datetime first = MkTime(y, mo, 1, 0);
   int dow = DowOf(first);
   int d = 1 + ((7 - dow) % 7);
   return d + 7 * (n - 1);
}
int LastSunday(const int y, const int mo)
{
   int days = (mo == 12) ? 31 : (int)((MkTime(mo == 12 ? y + 1 : y, mo == 12 ? 1 : mo + 1, 1, 0) - MkTime(y, mo, 1, 0)) / 86400);
   datetime last = MkTime(y, mo, days, 0);
   return days - DowOf(last);
}
int g_dstYear = -1;
datetime g_usOn, g_usOff, g_ukOn, g_ukOff;
void DstCache(const int y)
{
   if(y == g_dstYear) return;
   g_dstYear = y;
   g_usOn  = MkTime(y, 3,  NthSunday(y, 3, 2), 7);    // 02:00 EST = 07:00 UTC
   g_usOff = MkTime(y, 11, NthSunday(y, 11, 1), 6);   // 02:00 EDT = 06:00 UTC
   g_ukOn  = MkTime(y, 3,  LastSunday(y, 3), 1);      // 01:00 UTC
   g_ukOff = MkTime(y, 10, LastSunday(y, 10), 1);
}
// minute of day of server time t in the chosen zone
int MinuteOfDay(const datetime tSrv, const ENUM_SSNTZ tz)
{
   datetime utc = tSrv - g_srvOffSec;
   datetime loc = utc;
   if(tz == TZ_EXC) loc = tSrv;
   else if(tz == TZ_TKY) loc = utc + 9 * 3600;
   else if(tz == TZ_NY || tz == TZ_LON)
   {
      MqlDateTime s; TimeToStruct(utc, s);
      DstCache(s.year);
      if(tz == TZ_NY) loc = utc + ((utc >= g_usOn && utc < g_usOff) ? -4 : -5) * 3600;
      else            loc = utc + ((utc >= g_ukOn && utc < g_ukOff) ? 1 : 0) * 3600;
   }
   MqlDateTime m; TimeToStruct(loc, m);
   return m.hour * 60 + m.min;
}
bool ParseSess(const string s, int &a, int &b)
{
   a = 0; b = 0;
   if(StringLen(s) < 9) return false;
   a = (int)StringToInteger(StringSubstr(s, 0, 2)) * 60 + (int)StringToInteger(StringSubstr(s, 2, 2));
   b = (int)StringToInteger(StringSubstr(s, 5, 2)) * 60 + (int)StringToInteger(StringSubstr(s, 7, 2));
   return true;
}
bool InSess(const int m, const int a, const int b)
{
   if(a == b) return false;
   if(a < b) return m >= a && m < b;
   return m >= a || m < b;       // crosses midnight ("2000-0000")
}

//+------------------------------------------------------------------+
//| HTF / D1 / W1 feeds (request.security lookahead_on with [1])     |
//+------------------------------------------------------------------+
struct Feed
{
   ENUM_TIMEFRAMES tf;
   MqlRates r[];
   int n;
};
Feed fHtf, fD1, fW1;

bool FeedLoad(Feed &f, const ENUM_TIMEFRAMES tf, const datetime from)
{
   f.tf = tf;
   ArraySetAsSeries(f.r, false);
   int ps = PeriodSeconds(tf);
   datetime st0 = from - (datetime)((long)ps * 40);
   int got = CopyRates(_Symbol, tf, st0, TimeCurrent() + ps, f.r);
   if(got <= 0) { f.n = 0; return false; }
   f.n = got;
   return true;
}
// index of the feed bar containing time t (largest r[j].time <= t), -1 if none
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
double FeedPivH(const Feed &f, const int j, const int n)   // ta.pivothigh(high,n,n) at feed bar j
{
   int c = j - n;
   if(j < 0 || c - n < 0 || j >= f.n) return NA;
   double v = f.r[c].high;
   for(int k = 1; k <= n; k++) { if(f.r[c - k].high > v) return NA; if(f.r[c + k].high >= v) return NA; }
   return v;
}
double FeedPivL(const Feed &f, const int j, const int n)
{
   int c = j - n;
   if(j < 0 || c - n < 0 || j >= f.n) return NA;
   double v = f.r[c].low;
   for(int k = 1; k <= n; k++) { if(f.r[c - k].low < v) return NA; if(f.r[c + k].low <= v) return NA; }
   return v;
}

ENUM_TIMEFRAMES HtfAuto(const ENUM_HTFMODE mode)
{
   int s = PeriodSeconds(PERIOD_CURRENT);
   bool aggr = mode == HM_AGGR;
   if(s <= 60)    return PERIOD_M15;
   if(s <= 180)   return PERIOD_M30;
   if(s <= 300)   return aggr ? PERIOD_M30 : PERIOD_H1;
   if(s <= 900)   return aggr ? PERIOD_H1 : PERIOD_H4;
   if(s <= 1800)  return PERIOD_H4;
   if(s <= 14400) return PERIOD_D1;
   if(s <= 86400) return PERIOD_W1;
   return PERIOD_MN1;
}
string TfName(const ENUM_TIMEFRAMES tf)
{
   string s = EnumToString(tf);
   StringReplace(s, "PERIOD_", "");
   return s;
}

//+------------------------------------------------------------------+
//| L0 CANDLE ANATOMY                                                |
//+------------------------------------------------------------------+
void CandleCalc(const double aV, const double rLo, const double rHi)
{
   cd.Reset();
   double o = O(0), h = H(0), l = L(0), c = C(0);
   cd.body   = MathAbs(c - o);
   cd.rng    = h - l;
   cd.upWick = h - MathMax(c, o);
   cd.dnWick = MathMin(c, o) - l;
   if(cd.rng > 0)
   {
      cd.bodyRatio   = cd.body   / cd.rng;
      cd.upWickRatio = cd.upWick / cd.rng;
      cd.dnWickRatio = cd.dnWick / cd.rng;
   }
   cd.isBull     = c > o;
   cd.isBear     = c < o;
   cd.largeRange = cd.rng > aV * i_largeMult;
   if(g_bi > 1)
   {
      double pBody = MathAbs(C(1) - O(1));
      cd.pinBull = cd.dnWick >= i_pinMult * cd.body && cd.dnWickRatio >= i_pinRatio && cd.upWick <= cd.body;
      cd.pinBear = cd.upWick >= i_pinMult * cd.body && cd.upWickRatio >= i_pinRatio && cd.dnWick <= cd.body;
      cd.doji    = cd.bodyRatio <= i_dojiMax;
      cd.engulfBull = cd.isBull && c >= O(1) && o <= C(1) && C(1) < O(1);
      cd.engulfBear = cd.isBear && c <= O(1) && o >= C(1) && C(1) > O(1);
      cd.insideBar  = h <= H(1) && l >= L(1);
      cd.harami     = h < H(1) && l > L(1) && cd.body < pBody * i_haramiMax;
      cd.longWickRej = (cd.upWickRatio >= i_longWick || cd.dnWickRatio >= i_longWick) && cd.largeRange;
      cd.starBear = cd.pinBear && MathAbs(h - rHi) <= aV * i_starProx;
      cd.starBull = cd.pinBull && MathAbs(l - rLo) <= aV * i_starProx;
      bool okBull = i_ifcAnyCol || c > o;
      bool okBear = i_ifcAnyCol || c < o;
      cd.ifcBull = l < rLo && okBull && cd.dnWick >= i_ifcMult * cd.body;
      cd.ifcBear = h > rHi && okBear && cd.upWick >= i_ifcMult * cd.body;
      cd.manipBull = l < L(1) && c > H(1) && c > o && cd.dnWickRatio >= i_manipWick;
      cd.manipBear = h > H(1) && c < L(1) && c < o && cd.upWickRatio >= i_manipWick;
   }
}

// S2 — origin of the leg that just broke a swing
void LegOrigin(const bool isBull, const int fromIdx, int &oIdx, double &oPx)
{
   int span = MathMin(MathMax(g_bi - fromIdx, 1), 490);
   int bestOff = 1;
   double bestVal = isBull ? L(1) : H(1);
   if(span >= 2)
      for(int k = 2; k <= span; k++)
      {
         double v = isBull ? L(k) : H(k);
         if((isBull && v < bestVal) || (!isBull && v > bestVal)) { bestVal = v; bestOff = k; }
      }
   oIdx = g_bi - bestOff;
   oPx  = bestVal;
}

// v8.5.1 S2 — highest high / lowest low from fromIdx through this bar
double LegExt(const bool isHi, const int fromIdx)
{
   int span = MathMin(MathMax(g_bi - fromIdx, 0), 490);
   double v = isHi ? H(0) : L(0);
   for(int k = 1; k <= span; k++) v = isHi ? MathMax(v, H(k)) : MathMin(v, L(k));
   return v;
}

// v8.5.2 E-4 — CE of the unmitigated FVG of the current leg nearest to px on the entry side
double LegFvg(const bool isLong, const int fromIdx, const double px)
{
   double best = NA;
   int n = ArraySize(g_fvgs);
   for(int i = 0; i < n; i++)
   {
      if(g_fvgs[i].mitigated || g_fvgs[i].isBull != isLong || g_fvgs[i].idx < fromIdx) continue;
      double ce = (g_fvgs[i].top + g_fvgs[i].bottom) * 0.5;
      if((isLong && ce < px && (isna(best) || ce > best)) || (!isLong && ce > px && (isna(best) || ce < best))) best = ce;
   }
   return best;
}

void Pend(const int dir, const int kind, const double lvl, const int fromIdx)
{
   g_sx.stPendDir = dir; g_sx.stPendKind = kind; g_sx.stPendBar = g_bi; g_sx.stPendLvl = lvl; g_sx.stPendFrom = fromIdx;
}

//+------------------------------------------------------------------+
//| L1 STRUCTURE ENGINE                                              |
//+------------------------------------------------------------------+
void Structure(const double swH, const double swL, const bool dispOk, const double dDist)
{
   st.Reset();
   double close = C(0), open = O(0), high = H(0), low = L(0);
   int pIdx = g_bi - i_swingLen;
   if(!isna(swH)) { st.swingHigh = true; g_sx.hiType = isna(g_cx.curHigh) ? "" : (swH > g_cx.curHigh ? "HH" : "LH"); }
   if(!isna(swL)) { st.swingLow  = true; g_sx.loType = isna(g_cx.curLow)  ? "" : (swL < g_cx.curLow  ? "LL" : "HL"); }
   // failed follow-through
   if(g_sx.stBrkDir != 0 && g_bi - g_sx.stBrkBar >= 1)
   {
      if(g_bi - g_sx.stBrkBar <= i_failBars)
      {
         if((g_sx.stBrkDir == 1 && close < g_sx.stBrkLvl) || (g_sx.stBrkDir == -1 && close > g_sx.stBrkLvl))
         {
            g_sx.stFail++;
            g_sx.stBrkDir = 0;
            if(g_sx.stFail >= i_failMax) g_cx.trend = "RANGE";
         }
      }
      else { g_sx.stBrkDir = 0; g_sx.stFail = 0; }
   }
   bool brkUp = !isna(g_cx.curHigh) && !g_cx.hiBroken && close > g_cx.curHigh;
   bool brkDn = !isna(g_cx.curLow)  && !g_cx.loBroken && close < g_cx.curLow;
   st.bullSweep = !isna(g_cx.curHigh) && !g_cx.hiBroken && high > g_cx.curHigh && close <= g_cx.curHigh;
   st.bearSweep = !isna(g_cx.curLow)  && !g_cx.loBroken && low  < g_cx.curLow  && close >= g_cx.curLow;
   if(brkUp && brkDn)
   {
      if((close - g_cx.curHigh) >= (g_cx.curLow - close)) brkDn = false; else brkUp = false;
   }
   if(brkUp) g_cx.hiBroken = true;
   if(brkDn) g_cx.loBroken = true;
   bool promUp = false, promDn = false;
   if(g_sx.stPendDir != 0)
   {
      if(g_bi - g_sx.stPendBar > i_pendBars) g_sx.stPendDir = 0;
      else if(g_sx.stPendDir == 1 && close > g_sx.stPendLvl)
      {
         promUp = true;
         if(g_sx.stPendKind == 2) { st.bullCHoCH = true; st.chLvl = g_sx.stPendLvl; st.chIdx = g_sx.stPendFrom; }
         else st.bullBOS = true;
         g_sx.stPendDir = 0;
      }
      else if(g_sx.stPendDir == -1 && close < g_sx.stPendLvl)
      {
         promDn = true;
         if(g_sx.stPendKind == 2) { st.bearCHoCH = true; st.chLvl = g_sx.stPendLvl; st.chIdx = g_sx.stPendFrom; }
         else st.bearBOS = true;
         g_sx.stPendDir = 0;
      }
   }
   bool chUpMaj = g_cx.trend == "BEARISH" && !isna(g_cx.majorHigh) && close > g_cx.majorHigh;
   bool chDnMaj = g_cx.trend == "BULLISH" && !isna(g_cx.majorLow)  && close < g_cx.majorLow;
   bool chUp = chUpMaj || (g_cx.trend == "BEARISH" && brkUp && g_sx.loType == "HL");
   bool chDn = chDnMaj || (g_cx.trend == "BULLISH" && brkDn && g_sx.hiType == "LH");
   double chUpLvl = chUpMaj ? g_cx.majorHigh    : g_cx.curHigh;
   int    chUpIdx = chUpMaj ? g_cx.majorHighIdx : g_cx.curHighIdx;
   double chDnLvl = chDnMaj ? g_cx.majorLow     : g_cx.curLow;
   int    chDnIdx = chDnMaj ? g_cx.majorLowIdx  : g_cx.curLowIdx;
   bool dBrkUp = dispOk || (!isna(g_cx.curHigh)   && close - g_cx.curHigh   >= dDist);
   bool dChUp  = dispOk || (!isna(g_cx.majorHigh) && close - g_cx.majorHigh >= dDist) || dBrkUp;
   bool dBrkDn = dispOk || (!isna(g_cx.curLow)    && g_cx.curLow - close    >= dDist);
   bool dChDn  = dispOk || (!isna(g_cx.majorLow)  && g_cx.majorLow - close  >= dDist) || dBrkDn;
   bool evtAny = st.bullBOS || st.bearBOS || st.bullCHoCH || st.bearCHoCH;
   if((brkUp || chUp) && !evtAny)
   {
      if(chUp)
      {
         if(dChUp) { st.bullCHoCH = true; st.chLvl = chUpLvl; st.chIdx = chUpIdx; }
         else { st.weakBullBOS = true; Pend(1, 2, chUpLvl, chUpIdx); }
      }
      else if(g_cx.trend == "BEARISH") st.internalBullBOS = true;
      else if(dBrkUp) st.bullBOS = true;
      else { st.weakBullBOS = true; Pend(1, 1, g_cx.curHigh, g_cx.curHighIdx); }
   }
   evtAny = st.bullBOS || st.bearBOS || st.bullCHoCH || st.bearCHoCH;
   if((brkDn || chDn) && !evtAny && !st.weakBullBOS && !st.internalBullBOS)
   {
      if(chDn)
      {
         if(dChDn) { st.bearCHoCH = true; st.chLvl = chDnLvl; st.chIdx = chDnIdx; }
         else { st.weakBearBOS = true; Pend(-1, 2, chDnLvl, chDnIdx); }
      }
      else if(g_cx.trend == "BULLISH") st.internalBearBOS = true;
      else if(dBrkDn) st.bearBOS = true;
      else { st.weakBearBOS = true; Pend(-1, 1, g_cx.curLow, g_cx.curLowIdx); }
   }
   int oi; double op;
   if(st.bullBOS || st.bullCHoCH)
   {
      int fromI = promUp ? g_sx.stPendFrom : (st.bullCHoCH ? st.chIdx : g_cx.curHighIdx);
      LegOrigin(true, fromI, oi, op);
      g_cx.legIdx = oi; g_cx.legPx = op; g_cx.majorLow = op; g_cx.majorLowIdx = oi;
      g_cx.trend = "BULLISH"; g_cx.barsSinceEvt = 0; g_sx.stFail = 0;
      g_sx.stBrkDir = 1; g_sx.stBrkLvl = st.bullCHoCH ? st.chLvl : g_cx.curHigh; g_sx.stBrkBar = g_bi;
      if(g_sx.stPendDir == -1) g_sx.stPendDir = 0;
      if(st.bullCHoCH) { g_cx.hiBroken = true; g_cx.loBroken = false; }
   }
   if(st.bearBOS || st.bearCHoCH)
   {
      int fromI = promDn ? g_sx.stPendFrom : (st.bearCHoCH ? st.chIdx : g_cx.curLowIdx);
      LegOrigin(false, fromI, oi, op);
      g_cx.legIdx = oi; g_cx.legPx = op; g_cx.majorHigh = op; g_cx.majorHighIdx = oi;
      g_cx.trend = "BEARISH"; g_cx.barsSinceEvt = 0; g_sx.stFail = 0;
      g_sx.stBrkDir = -1; g_sx.stBrkLvl = st.bearCHoCH ? st.chLvl : g_cx.curLow; g_sx.stBrkBar = g_bi;
      if(g_sx.stPendDir == 1) g_sx.stPendDir = 0;
      if(st.bearCHoCH) { g_cx.loBroken = true; g_cx.hiBroken = false; }
   }
   if(st.weakBullBOS || st.internalBullBOS)
   {
      LegOrigin(true, g_cx.curHighIdx, oi, op);
      g_cx.legIdx = oi; g_cx.legPx = op;
      if(st.weakBullBOS)
      {
         g_sx.stBrkDir = 1;
         g_sx.stBrkLvl = g_sx.stPendDir == 1 ? g_sx.stPendLvl : g_cx.curHigh;
         g_sx.stBrkBar = g_bi;
      }
   }
   if(st.weakBearBOS || st.internalBearBOS)
   {
      LegOrigin(false, g_cx.curLowIdx, oi, op);
      g_cx.legIdx = oi; g_cx.legPx = op;
      if(st.weakBearBOS)
      {
         g_sx.stBrkDir = -1;
         g_sx.stBrkLvl = g_sx.stPendDir == -1 ? g_sx.stPendLvl : g_cx.curLow;
         g_sx.stBrkBar = g_bi;
      }
   }
   if(!(st.bullBOS || st.bearBOS || st.bullCHoCH || st.bearCHoCH))
   {
      g_cx.barsSinceEvt++;
      if(g_cx.barsSinceEvt > i_rangeBars) g_cx.trend = "RANGE";
   }
   if(!isna(swH))
   {
      g_cx.prevHigh = g_cx.curHigh; g_cx.prevHighIdx = g_cx.curHighIdx;
      g_cx.curHigh = swH; g_cx.curHighIdx = pIdx; g_cx.hiBroken = false;
   }
   if(!isna(swL))
   {
      g_cx.prevLow = g_cx.curLow; g_cx.prevLowIdx = g_cx.curLowIdx;
      g_cx.curLow = swL; g_cx.curLowIdx = pIdx; g_cx.loBroken = false;
   }
   // §3.5 pullback validity
   if(isna(g_cx.hiMakerHigh) || high >= g_cx.hiMakerHigh) { g_cx.hiMakerHigh = high; g_cx.hiMakerLow = low; g_cx.pbUpArmed = true; }
   else if(g_cx.pbUpArmed && low < g_cx.hiMakerLow) { st.pbValidUp = true; g_cx.pbUpArmed = false; }
   if(isna(g_cx.loMakerLow) || low <= g_cx.loMakerLow) { g_cx.loMakerLow = low; g_cx.loMakerHigh = high; g_cx.pbDnArmed = true; }
   else if(g_cx.pbDnArmed && high > g_cx.loMakerHigh) { st.pbValidDn = true; g_cx.pbDnArmed = false; }
   if(st.bullBOS || st.bearBOS || st.bullCHoCH || st.bearCHoCH)
   {
      g_cx.hiMakerHigh = high; g_cx.hiMakerLow = low; g_cx.pbUpArmed = true;
      g_cx.loMakerLow = low; g_cx.loMakerHigh = high; g_cx.pbDnArmed = true;
   }
   // §3.6 CISD · S10
   if(close > open && !(C(1) > O(1))) { g_cx.cisdUpOpen = open; g_cx.cisdUpBar = g_bi; }
   if(close < open && !(C(1) < O(1))) { g_cx.cisdDnOpen = open; g_cx.cisdDnBar = g_bi; }
   if(high >= g_cx.hiMakerHigh && !isna(g_cx.cisdUpOpen)) { g_sx.cisdUpRef = g_cx.cisdUpOpen; g_sx.cisdUpRefBar = g_cx.cisdUpBar; g_sx.cisdUpUsed = false; }
   if(low <= g_cx.loMakerLow && !isna(g_cx.cisdDnOpen))   { g_sx.cisdDnRef = g_cx.cisdDnOpen; g_sx.cisdDnRefBar = g_cx.cisdDnBar; g_sx.cisdDnUsed = false; }
   bool swOkUp = !i_cisdSweep || (g_cx.sweptHighBar >= 0 && g_bi - g_cx.sweptHighBar <= i_armBars);
   bool swOkDn = !i_cisdSweep || (g_cx.sweptLowBar  >= 0 && g_bi - g_cx.sweptLowBar  <= i_armBars);
   st.cisdBear = !g_sx.cisdUpUsed && !isna(g_sx.cisdUpRef) && close < g_sx.cisdUpRef && swOkUp;
   st.cisdBull = !g_sx.cisdDnUsed && !isna(g_sx.cisdDnRef) && close > g_sx.cisdDnRef && swOkDn;
   if(st.cisdBear) g_sx.cisdUpUsed = true;
   if(st.cisdBull) g_sx.cisdDnUsed = true;
   st.trend = g_cx.trend;
   st.movePhase = g_cx.trend == "RANGE" ? "RANGE" :
                  ((g_cx.trend == "BULLISH" && !isna(g_cx.curHigh) && close >= g_cx.curHigh) ||
                   (g_cx.trend == "BEARISH" && !isna(g_cx.curLow)  && close <= g_cx.curLow)) ? "IMPULSIVE" : "RETRACEMENT";
}

//+------------------------------------------------------------------+
//| L2 FVG ENGINE                                                    |
//+------------------------------------------------------------------+
void FvgEngine(const double aV, const bool drawOn, const bool keepMit)
{
   double minH = aV * i_fvgMin;
   if(g_bi > 2)
   {
      if(L(0) > H(2) && (L(0) - H(2)) >= minH)
      {
         Fvg g; g.top = L(0); g.bottom = H(2); g.idx = g_bi - 1; g.isBull = true;
         if(drawOn) g.bx = BoxNew(g_bi - 1, L(0), g_bi, H(2), i_cBull, i_boxT, "", false);
         APush(g_fvgs, g);
         ft.newBullFvg = true;
      }
      if(H(0) < L(2) && (L(2) - H(0)) >= minH)
      {
         Fvg g; g.top = L(2); g.bottom = H(0); g.idx = g_bi - 1; g.isBull = false;
         if(drawOn) g.bx = BoxNew(g_bi - 1, L(2), g_bi, H(0), i_cBear, i_boxT, "", false);
         APush(g_fvgs, g);
         ft.newBearFvg = true;
      }
   }
   int n = ArraySize(g_fvgs);
   for(int i = n - 1; i >= 0; i--)
   {
      if(!g_fvgs[i].mitigated && g_fvgs[i].idx < g_bi - 1)
      {
         double mid = (g_fvgs[i].top + g_fvgs[i].bottom) * 0.5;
         double lvl = i_fvgMode == FM_TOUCH ? (g_fvgs[i].isBull ? g_fvgs[i].top : g_fvgs[i].bottom) :
                      i_fvgMode == FM_50    ? mid : (g_fvgs[i].isBull ? g_fvgs[i].bottom : g_fvgs[i].top);
         bool hit = g_fvgs[i].isBull ? L(0) <= lvl : H(0) >= lvl;
         if(hit)
         {
            g_fvgs[i].mitigated = true;
            g_fvgs[i].mitIdx    = g_bi;
            if(g_fvgs[i].bx != "")
            {
               BoxSetRight(g_fvgs[i].bx, g_bi);
               if(keepMit) BoxSetColor(g_fvgs[i].bx, i_cInv, 92);
               else { BoxDel(g_fvgs[i].bx); g_fvgs[i].bx = ""; }
            }
         }
      }
      if(g_fvgs[i].mitigated && g_bi - g_fvgs[i].mitIdx > i_fvgAge)
      {
         BoxDel(g_fvgs[i].bx);
         ARemove(g_fvgs, i);
      }
   }
   while(ArraySize(g_fvgs) > i_maxFvg)
   {
      BoxDel(g_fvgs[0].bx);
      ARemove(g_fvgs, 0);
   }
}

// nearest FVG of a direction whose middle candle sits in [fromIdx, toIdx]
double FvgNear(const bool isBull, const int fromIdx, const int toIdx)
{
   int n = ArraySize(g_fvgs);
   for(int i = 0; i < n; i++)
      if(g_fvgs[i].isBull == isBull && g_fvgs[i].idx >= fromIdx && g_fvgs[i].idx <= toIdx)
         return isBull ? g_fvgs[i].bottom : g_fvgs[i].top;
   return NA;
}

//+------------------------------------------------------------------+
//| L2 MOVE STRENGTH                                                 |
//+------------------------------------------------------------------+
Move MoveStrength(const int fromBar, const int toBar, const double aV, const bool isBull)
{
   Move m;
   int fb = MathMax(MathMax(fromBar, toBar - i_maxMove + 1), 0);
   int cnt = toBar - fb + 1;
   if(cnt > 0 && aV > 0)
   {
      double bodySum = 0, rangeSum = 0;
      int flips = 0;
      bool prevBull = false;
      for(int b = fb; b <= toBar; b++)
      {
         int off = g_bi - b;
         if(off >= 0 && off < 500)
         {
            bodySum  += MathAbs(C(off) - O(off));
            rangeSum += H(off) - L(off);
            bool isB = C(off) > O(off);
            if(b > fb && isB != prevBull) flips++;
            prevBull = isB;
         }
      }
      int k = ArraySize(g_fvgs);
      for(int i = 0; i < k; i++)
         if(g_fvgs[i].isBull == isBull && g_fvgs[i].idx >= fb && g_fvgs[i].idx <= toBar && !g_fvgs[i].mitigated)
            m.fvgCount++;
      m.avgBody = bodySum / cnt;
      m.bodyEff = rangeSum > 0 ? bodySum / rangeSum : 0.0;
      m.mixed   = cnt > 1 ? (double)flips / (cnt - 1) : 0.0;
      int offTo   = MathMin(MathMax(g_bi - toBar, 0), 499);
      int offFrom = MathMin(MathMax(g_bi - fb, 0), 499);
      double netMove = MathAbs(C(offTo) - O(offFrom));
      m.speed  = netMove / cnt / aV;
      m.strong = m.fvgCount >= i_minFvgStr && m.bodyEff >= i_bodyEff && m.mixed <= i_mixMax && m.speed >= i_speedMin;
   }
   return m;
}

//+------------------------------------------------------------------+
//| L3 LIQUIDITY                                                     |
//+------------------------------------------------------------------+
bool QualKind(const string k) { return k == "PDH" || k == "PDL" || k == "PWH" || k == "PWL" || k == "SESH" || k == "SESL"; }
color LvlColor(const int i)
{
   if(g_lv[i].pooled) return i_cPool;
   string k = g_lv[i].kind;
   if(k == "PDH" || k == "PDL" || k == "PWH" || k == "PWL") return i_cNeut;
   return g_lv[i].isHigh ? i_cBear : i_cBull;
}
string LvlText(const int i) { return (g_lv[i].pooled ? "POOL·" : "") + g_lv[i].kind + (g_lv[i].ext ? "·ext" : ""); }

void Resolve(const int i, const string res)
{
   g_lv[i].done   = true;
   g_lv[i].result = res;
   if(g_lv[i].ln != "")
   {
      LineSetRay(g_lv[i].ln, false);
      LineSetX2(g_lv[i].ln, g_bi);
      LineSetStyle(g_lv[i].ln, res == "SWEEP" ? STYLE_DOT : STYLE_SOLID);
      LineSetColor(g_lv[i].ln, Col(res == "SWEEP" ? LvlColor(i) : i_cNeut, MathMin(i_lineT + 30, 100)));
   }
}

bool AddLevel(const double aV, const double price, const int idx, const bool isHigh, const string kind, const bool ext, const bool drawOn)
{
   if(isna(price)) return false;
   bool merged = false;
   int n = ArraySize(g_lv);
   if(n > 0 && (kind == "BSL" || kind == "SSL"))
   {
      for(int i = n - 1; i >= 0; i--)
      {
         string k = g_lv[i].kind;
         bool famOk = k == "BSL" || k == "SSL" || k == "EQH" || k == "EQL";
         if(!g_lv[i].done && famOk && g_lv[i].isHigh == isHigh && MathAbs(g_lv[i].price - price) <= aV * i_eqTol)
         {
            g_lv[i].kind      = isHigh ? "EQH" : "EQL";
            g_lv[i].touches  += 1;
            g_lv[i].lastTouch = g_bi;
            g_lv[i].price     = (g_lv[i].price + price) * 0.5;
            g_lv[i].pooled    = true;
            if(g_lv[i].ln != "")
            {
               LineSetY(g_lv[i].ln, g_lv[i].price);
               LineSetWidth(g_lv[i].ln, 2);
               LineSetStyle(g_lv[i].ln, STYLE_DASH);
               LineSetColor(g_lv[i].ln, Col(LvlColor(i), i_lineT));
            }
            if(g_lv[i].lb != "")
            {
               TextSet(g_lv[i].lb, LvlText(i));
               TextSetColor(g_lv[i].lb, LvlColor(i));
               ObjectSetDouble(0, g_lv[i].lb, OBJPROP_PRICE, 0, g_lv[i].price);
            }
            else if(drawOn)
               g_lv[i].lb = TextNew(XB(idx), g_lv[i].price, LvlText(i), LvlColor(i), ANCHOR_LEFT_LOWER, i_zsz, "");
            merged = true;
            break;
         }
      }
   }
   if(!merged)
   {
      Liq Lq; Lq.price = price; Lq.idx = idx; Lq.isHigh = isHigh; Lq.kind = kind; Lq.ext = ext; Lq.lastTouch = g_bi;
      APush(g_lv, Lq);
      int j = ArraySize(g_lv) - 1;
      if(drawOn)
         g_lv[j].ln = LineNew(XB(idx), price, g_bi, price, Col(LvlColor(j), i_lineT), STYLE_DOT, 1, true);
   }
   return merged;
}

void LiqEngine(const double aV, const double swH, const double swL, const double eHi, const double eLo,
               const double pdh, const double pdl, const double pwh, const double pwl, const bool nDay, const bool nWeek, const bool drawOn)
{
   double close = C(0), open = O(0), high = H(0), low = L(0);
   int pIdx = g_bi - i_swingLen;
   double rng = high - low;
   double bodyR = rng > 0 ? MathAbs(close - open) / rng : 0.0;
   if(!isna(swH)) AddLevel(aV, swH, pIdx, true,  "BSL", swH >= eHi, drawOn);
   if(!isna(swL)) AddLevel(aV, swL, pIdx, false, "SSL", swL <= eLo, drawOn);
   if(nDay && !isna(pdh))
   {
      for(int i = ArraySize(g_lv) - 1; i >= 0; i--)
         if(!g_lv[i].done && (g_lv[i].kind == "PDH" || g_lv[i].kind == "PDL")) Resolve(i, "EXPIRED");
      AddLevel(aV, pdh, g_bi, true,  "PDH", false, drawOn);
      AddLevel(aV, pdl, g_bi, false, "PDL", false, drawOn);
   }
   if(nWeek && !isna(pwh))
   {
      for(int i = ArraySize(g_lv) - 1; i >= 0; i--)
         if(!g_lv[i].done && (g_lv[i].kind == "PWH" || g_lv[i].kind == "PWL")) Resolve(i, "EXPIRED");
      AddLevel(aV, pwh, g_bi, true,  "PWH", false, drawOn);
      AddLevel(aV, pwl, g_bi, false, "PWL", false, drawOn);
   }
   int n = ArraySize(g_lv);
   double scanD = aV * i_nearZone;
   for(int i = n - 1; i >= 0; i--)
   {
      if(g_lv[i].done)
      {
         if(g_bi - g_lv[i].lastTouch > i_extLB * 4)
         {
            LineDel(g_lv[i].ln);
            TextDel(g_lv[i].lb);
            ARemove(g_lv, i);
         }
         continue;
      }
      if(g_lv[i].idx >= g_bi) continue;
      double tol   = aV * i_touchTol;
      double minGo = aV * i_runClose;
      double P = g_lv[i].price;
      if(g_lv[i].isHigh)
      {
         if(g_lv[i].pend > 0)
         {
            g_lv[i].wickX = MathMax(nz(g_lv[i].wickX, high), high);
            if(close < P) Resolve(i, "SWEEP");
            else { g_lv[i].pend--; if(g_lv[i].pend == 0) Resolve(i, "RUN"); }
         }
         else if(high > P)
         {
            if(close <= P) Resolve(i, "SWEEP");
            else if(bodyR >= i_runBody && (close - P) >= minGo) Resolve(i, "RUN");
            else { g_lv[i].pend = i_failBars; g_lv[i].wickX = high; }
         }
         else if(high >= P - tol && g_bi - g_lv[i].lastTouch > i_touchCd) { g_lv[i].touches++; g_lv[i].lastTouch = g_bi; }
      }
      else
      {
         if(g_lv[i].pend > 0)
         {
            g_lv[i].wickX = MathMin(nz(g_lv[i].wickX, low), low);
            if(close > P) Resolve(i, "SWEEP");
            else { g_lv[i].pend--; if(g_lv[i].pend == 0) Resolve(i, "RUN"); }
         }
         else if(low < P)
         {
            if(close >= P) Resolve(i, "SWEEP");
            else if(bodyR >= i_runBody && (P - close) >= minGo) Resolve(i, "RUN");
            else { g_lv[i].pend = i_failBars; g_lv[i].wickX = low; }
         }
         else if(low <= P + tol && g_bi - g_lv[i].lastTouch > i_touchCd) { g_lv[i].touches++; g_lv[i].lastTouch = g_bi; }
      }
      if(g_lv[i].touches >= 3 && !g_lv[i].pooled)
      {
         g_lv[i].pooled = true;
         if(g_lv[i].ln != "")
         {
            LineSetWidth(g_lv[i].ln, 2);
            LineSetStyle(g_lv[i].ln, STYLE_DASH);
            LineSetColor(g_lv[i].ln, Col(i_cPool, i_lineT));
         }
         if(g_lv[i].lb != "") { TextSet(g_lv[i].lb, LvlText(i)); TextSetColor(g_lv[i].lb, i_cPool); }
         else if(drawOn) g_lv[i].lb = TextNew(XB(g_lv[i].idx), g_lv[i].price, LvlText(i), i_cPool, ANCHOR_LEFT_LOWER, i_zsz, "");
      }
      if(g_lv[i].done)
      {
         string k = g_lv[i].kind;
         if(g_lv[i].result == "SWEEP")
         {
            bool qual = g_lv[i].pooled || QualKind(k) || (i_sweepQual == SQ_EXT && g_lv[i].ext);
            if(g_lv[i].isHigh)
            {
               ft.sweptHigh  = true;
               ft.sweptExtHi = MathMax(nz(g_lv[i].wickX, high), high);
               if(qual) { ft.sweptHighQ = true; g_cx.sweptHighBar = g_bi; }
            }
            else
            {
               ft.sweptLow   = true;
               ft.sweptExtLo = MathMin(nz(g_lv[i].wickX, low), low);
               if(qual) { ft.sweptLowQ = true; g_cx.sweptLowBar = g_bi; }
            }
            ft.sweptKind = LvlText(i);
            if(g_lv[i].isHigh) { ft.sweptKindHi = LvlText(i); ft.sweptPriceHi = g_lv[i].price; }
            else               { ft.sweptKindLo = LvlText(i); ft.sweptPriceLo = g_lv[i].price; }
            ft.sweptPrice = g_lv[i].price;
            ft.sweptMajor = ft.sweptMajor || g_lv[i].pooled || k == "PDH" || k == "PDL" || k == "PWH" || k == "PWL";
         }
         if(g_lv[i].result == "RUN")
         {
            if(g_lv[i].isHigh) ft.runUp = true; else ft.runDn = true;
            ft.runPrice = g_lv[i].price;
            ft.runMajor = ft.runMajor || g_lv[i].pooled || g_lv[i].ext || k == "PDH" || k == "PDL" || k == "PWH" || k == "PWL";
         }
      }
      else
      {
         if(g_lv[i].isHigh && g_lv[i].price > close && g_lv[i].price - close <= scanD) ft.bslAbove++;
         if(!g_lv[i].isHigh && g_lv[i].price < close && close - g_lv[i].price <= scanD) ft.sslBelow++;
      }
   }
   // §M4 eviction
   while(ArraySize(g_lv) > i_maxLevels)
   {
      int wIdx = 0;
      for(int i = 0; i < ArraySize(g_lv); i++)
         if(g_lv[i].done || (!g_lv[i].pooled && (g_lv[i].kind == "BSL" || g_lv[i].kind == "SSL"))) { wIdx = i; break; }
      LineDel(g_lv[wIdx].ln);
      TextDel(g_lv[wIdx].lb);
      ARemove(g_lv, wIdx);
   }
}

//+------------------------------------------------------------------+
//| L4 ZONES                                                         |
//+------------------------------------------------------------------+
color ZColor(const int i)
{
   string k = g_zones[i].kind; bool b = g_zones[i].bull;
   if(k == "OB")  return b ? i_cBull : i_cBear;
   if(k == "BRK") return i_cBrk;
   if(k == "RCB") return i_cRcb;
   if(k == "RJB") return i_cRjb;
   if(k == "QM")  return i_cQm;
   if(g_zones[i].kl >= 4) return b ? i_cBull : i_cBear;
   return i_cSR;
}
string ZText(const int i)
{
   string k = g_zones[i].kind; bool b = g_zones[i].bull;
   string t;
   if(k == "OB") t = (b ? "OB▲" : "OB▼") + (g_zones[i].hp ? "★" : "") + (g_zones[i].obType != "" ? " " + g_zones[i].obType : "");
   else if(k == "SR") t = g_zones[i].kl >= 4 ? "KL★" : g_zones[i].kl == 3 ? "KL" : (b ? "S" : "R");
   else t = k + (b ? "▲" : "▼");
   if(g_zones[i].flipped)   t += " FLIP";
   if(g_zones[i].sweepReq)  t += " ⚠SWEEP REQ";
   if(g_zones[i].weak)      t += " weak";
   if(!g_zones[i].confirmed) t += " ?";
   if(g_zones[i].idmSwept)  t += " IDM✓";
   if(g_zones[i].prop)      t += " ⇈PROP";
   if(g_zones[i].nearSwept) t += " ★★";
   return t;
}
void ZStyle(const int i)
{
   if(g_zones[i].bx == "") return;
   bool weakZ = g_zones[i].broken || g_zones[i].weak || !g_zones[i].confirmed || (g_zones[i].kind == "OB" && !g_zones[i].hp && g_zones[i].obType != "");
   color c = (weakZ && (g_zones[i].broken || g_zones[i].weak)) ? i_cInv : ZColor(i);
   int tr = (g_zones[i].broken || g_zones[i].weak) ? 90 : g_zones[i].tapped ? MathMin(i_boxT + 6, 100) : i_boxT;
   BoxSetColor(g_zones[i].bx, c, tr);
   int bw = g_zones[i].kl >= 4 ? 3 : g_zones[i].kl == 3 ? 2 : 1;
   bool dsh = weakZ || g_zones[i].kind == "BRK" || g_zones[i].flipped;
   BoxSetBorder(g_zones[i].bx, Col(g_zones[i].sweepReq ? i_cInv : c, g_zones[i].broken ? 80 : 40), bw, dsh ? STYLE_DASH : STYLE_SOLID);
   BoxSetText(g_zones[i].bx, ZText(i));
}
int ZAdd(const double aV, const string kind, const bool bull, const double top, const double bottom, const int idx, const bool drawOn)
{
   double zt = MathMax(top, bottom);
   double zb = MathMin(top, bottom);
   double maxH = aV * i_zoneMaxH;
   if(zt - zb > maxH) { if(bull) zt = zb + maxH; else zb = zt - maxH; }
   int dup = -1;
   int n0 = (kind == "SR" || kind == "RJB") ? 0 : ArraySize(g_zones);
   for(int i = n0 - 1; i >= 0; i--)
      if(!g_zones[i].broken && g_zones[i].kind == kind && g_zones[i].bull == bull && g_zones[i].top >= zb && g_zones[i].bottom <= zt)
      { dup = i; break; }
   if(dup >= 0) return dup;
   Zone z; z.kind = kind; z.bull = bull; z.top = zt; z.bottom = zb; z.idx = idx; z.lastTouch = g_bi;
   APush(g_zones, z);
   int j = ArraySize(g_zones) - 1;
   if(drawOn)
   {
      g_zones[j].bx = BoxNew(XB(idx), zt, g_bi, zb, ZColor(j), i_boxT, ZText(j), true);
      ZStyle(j);
   }
   return j;
}
void ZReset(const int i)
{
   g_zones[i].idmLvl = NA; g_zones[i].idmSwept = false; g_zones[i].nearMiss = NA; g_zones[i].nearSwept = false; g_zones[i].fiftyHit = false;
}
bool HiddenInterest(const double top, const double bottom, const int idx)
{
   int n = ArraySize(g_zones);
   for(int i = 0; i < n; i++)
      if(g_zones[i].idx < idx && g_zones[i].idx >= idx - i_klLeft && g_zones[i].top >= bottom && g_zones[i].bottom <= top) return false;
   return true;
}
void ZSFill(ZS &zz, const int i)
{
   zz.kind = g_zones[i].kind; zz.touches = g_zones[i].touches; zz.sweepReq = g_zones[i].sweepReq; zz.fifty = g_zones[i].fiftyHit;
   zz.idm = g_zones[i].idmSwept; zz.hp = g_zones[i].hp; zz.kl = g_zones[i].kl; zz.flipped = g_zones[i].flipped;
   zz.nearSwept = g_zones[i].nearSwept; zz.depStrong = g_zones[i].depStrong; zz.prop = g_zones[i].prop;
   zz.top = g_zones[i].top; zz.bottom = g_zones[i].bottom; zz.pend = !g_zones[i].confirmed;
}

void ZonesEngine(const double aV, const double swH, const double swL, const bool bullBOS, const bool bearBOS,
                 const bool bullCHoCH, const bool bearCHoCH, const bool mvStrong, const int mvFvg, const bool vOk, const int oIdxIn,
                 const bool onSR, const bool onKL, const bool onOB, const bool onBrk, const bool onRcb, const bool onRjb, const bool onQm)
{
   double close = C(0), high = H(0), low = L(0);
   int pIdx = g_bi - i_swingLen;
   int o = i_swingLen;
   if(!isna(swH)) ZAdd(aV, "SR", false, H(o), MathMax(O(o), C(o)), pIdx, onSR);
   if(!isna(swL)) ZAdd(aV, "SR", true, MathMin(O(o), C(o)), L(o), pIdx, onSR);

   // BOS -> Key Level score on origin SR + Order Block
   if(bullBOS || bearBOS)
   {
      bool isBull = bullBOS;
      int oIdx = oIdxIn;
      int off = g_bi - oIdx;
      if(off >= 1 && off < 490)
      {
         int n0 = ArraySize(g_zones);
         for(int i = 0; i < n0; i++)
         {
            if(g_zones[i].kind == "SR" && g_zones[i].bull == isBull && g_zones[i].kl == 0 && g_zones[i].idx >= oIdx - i_swingLen && g_zones[i].idx <= oIdx + i_swingLen)
            {
               int sc = 1;
               sc += mvFvg >= 1 ? 1 : 0;
               sc += mvStrong ? 1 : 0;
               sc += HiddenInterest(g_zones[i].top, g_zones[i].bottom, oIdx) ? 1 : 0;
               sc += (i_klVol && vOk) ? 1 : 0;
               g_zones[i].kl = sc;
               g_zones[i].depStrong = mvStrong;
               if(sc >= i_klMin && g_zones[i].bx == "" && onKL)
                  g_zones[i].bx = BoxNew(XB(g_zones[i].idx), g_zones[i].top, g_bi, g_zones[i].bottom, ZColor(i), i_boxT, ZText(i), true);
               ZStyle(i);
               break;
            }
         }
         if(!mvStrong)
         {
            if(isBull) { ft.evtUp = "T5 no-FVG"; ft.tipUp = "Big move but NO imbalance — no OB here (Type 5). Look for reversal the other way."; }
            else       { ft.evtDn = "T5 no-FVG"; ft.tipDn = "Big move but NO imbalance — no OB here (Type 5). Look for reversal the other way."; }
         }
         else
         {
            int obOff = off;
            string obT = "T1";
            int dispOff = -1;
            if(obOff >= 2)
               for(int k = obOff - 1; k >= MathMax(obOff - i_swingLen, 1); k--)
               {
                  double rk = H(k) - L(k);
                  double bodyK = rk > 0 ? MathAbs(C(k) - O(k)) / rk : 0.0;
                  bool colOk = isBull ? C(k) > O(k) : C(k) < O(k);
                  if(colOk && bodyK >= 0.5 && rk >= aV * 0.5) { dispOff = k; break; }
               }
            if(dispOff > 0)
               for(int k = dispOff + 1; k <= obOff; k++)
               {
                  bool opp = isBull ? C(k) < O(k) : C(k) > O(k);
                  if(opp) { obOff = k; obT = k == off ? "T1" : "T1b"; break; }
               }
            if(H(obOff) <= H(obOff + 1) && L(obOff) >= L(obOff + 1)) { obOff = obOff + 1; obT = "T2"; }
            double zTop = H(obOff), zBot = L(obOff);
            if(obOff >= 1)
            {
               int nb = obOff - 1;
               bool smallBody = MathAbs(C(obOff) - O(obOff)) < 0.3 * (H(obOff) - L(obOff));
               bool engulfs   = L(nb) <= L(obOff) && H(nb) >= H(obOff);
               if(smallBody && engulfs)
               {
                  zTop = isBull ? H(obOff) : H(nb);
                  zBot = isBull ? L(nb) : L(obOff);
                  obT = "G2";
               }
            }
            int obIdx = g_bi - obOff;
            double fvgLvl = FvgNear(isBull, obIdx, obIdx + 3);
            if(isna(fvgLvl))
            {
               if(isBull) { ft.evtUp = "T5 no-FVG"; ft.tipUp = "STRONG move but no FVG aligned with the OB candle — OB invalid (Type 5)."; }
               else       { ft.evtDn = "T5 no-FVG"; ft.tipDn = "STRONG move but no FVG aligned with the OB candle — OB invalid (Type 5)."; }
            }
            else
            {
               bool selfMit = isBull ? H(obOff) > fvgLvl : L(obOff) < fvgLvl;
               if(selfMit)
               {
                  if(isBull) { ft.evtUp = "T3 invalid"; ft.tipUp = "OB wick mitigated its own FVG (Type 3) — not plotted."; }
                  else       { ft.evtDn = "T3 invalid"; ft.tipDn = "OB wick mitigated its own FVG (Type 3) — not plotted."; }
               }
               else
               {
                  int sw = isBull ? g_cx.sweptLowBar : g_cx.sweptHighBar;
                  bool hpNow = sw >= obIdx - i_sweepWin && sw <= obIdx + 2;
                  if(hpNow || !i_obHpOnly)
                  {
                     int zi = ZAdd(aV, "OB", isBull, zTop, zBot, obIdx, onOB);
                     g_zones[zi].obType = obT;
                     g_zones[zi].depStrong = mvStrong;
                     g_zones[zi].hp = hpNow;
                     ft.newObHp = hpNow;
                     ZStyle(zi);
                  }
               }
            }
         }
      }
   }

   // CHoCH -> Reclaimed Block + QM pending
   if(bullCHoCH)
   {
      int llIdx = oIdxIn;
      int off = g_bi - llIdx;
      if(off >= 1 && off < 490 && llIdx > 0)
      {
         double legMid = (L(off) + high) * 0.5;
         if(H(off) <= legMid || !i_rcbFib)
         {
            int zr = ZAdd(aV, "RCB", true, H(off), L(off), llIdx, onRcb);
            g_zones[zr].depStrong = g_cx.chochReal;
         }
      }
      g_cx.qmBullPend = true; g_cx.qmBullLL = g_cx.curLow; g_cx.qmBullAt = g_bi;
   }
   if(bearCHoCH)
   {
      int hhIdx = oIdxIn;
      int off = g_bi - hhIdx;
      if(off >= 1 && off < 490 && hhIdx > 0)
      {
         double legMid = (H(off) + low) * 0.5;
         if(L(off) >= legMid || !i_rcbFib)
         {
            int zr = ZAdd(aV, "RCB", false, H(off), L(off), hhIdx, onRcb);
            g_zones[zr].depStrong = g_cx.chochReal;
         }
      }
      g_cx.qmBearPend = true; g_cx.qmBearHH = g_cx.curHigh; g_cx.qmBearAt = g_bi;
   }
   if(g_cx.qmBullPend)
   {
      if(g_bi - g_cx.qmBullAt > i_qmBars || bearCHoCH) g_cx.qmBullPend = false;
      else if(!isna(g_cx.qmBullLL) && low < g_cx.qmBullLL)
      {
         int zq = ZAdd(aV, "QM", true, g_cx.qmBullLL, low, g_bi, onQm);
         g_zones[zq].depStrong = g_cx.chochReal;
         g_cx.qmBullPend = false;
      }
   }
   if(g_cx.qmBearPend)
   {
      if(g_bi - g_cx.qmBearAt > i_qmBars || bullCHoCH) g_cx.qmBearPend = false;
      else if(!isna(g_cx.qmBearHH) && high > g_cx.qmBearHH)
      {
         int zq = ZAdd(aV, "QM", false, high, g_cx.qmBearHH, g_bi, onQm);
         g_zones[zq].depStrong = g_cx.chochReal;
         g_cx.qmBearPend = false;
      }
   }

   // §6.9 Rejection Block
   if(g_bi > 2)
   {
      double rr1 = H(1) - L(1);
      double uw1 = rr1 > 0 ? (H(1) - MathMax(O(1), C(1))) / rr1 : 0.0;
      double dw1 = rr1 > 0 ? (MathMin(O(1), C(1)) - L(1)) / rr1 : 0.0;
      if(uw1 >= i_rjbWick)
      {
         double zbx = MathMax(O(1), C(1));
         if(high < zbx)
         {
            int zi = ZAdd(aV, "RJB", false, H(1), zbx, g_bi - 1, onRjb);
            g_zones[zi].confirmed = false; g_zones[zi].pendFvg = 2;
            ZStyle(zi);
         }
      }
      if(dw1 >= i_rjbWick)
      {
         double ztx = MathMin(O(1), C(1));
         if(low > ztx)
         {
            int zi = ZAdd(aV, "RJB", true, ztx, L(1), g_bi - 1, onRjb);
            g_zones[zi].confirmed = false; g_zones[zi].pendFvg = 2;
            ZStyle(zi);
         }
      }
   }

   // per-bar maintenance + "zone at price" extraction
   int n = ArraySize(g_zones);
   int bestPri = -1, bestPriS = -1;
   for(int i = n - 1; i >= 0; i--)
   {
      bool changed = false;
      if(g_zones[i].broken)
      {
         if(g_bi - g_zones[i].brokenAt > 20) { BoxDel(g_zones[i].bx); ARemove(g_zones, i); }
         continue;
      }
      if(g_zones[i].idx >= g_bi) continue;
      if(g_zones[i].kind == "RJB" && !g_zones[i].confirmed)
      {
         if(g_zones[i].pendFvg > 0)
         {
            g_zones[i].pendFvg--;
            if(g_zones[i].pendFvg == 0 && isna(FvgNear(g_zones[i].bull, g_zones[i].idx - 1, g_zones[i].idx + 1)))
            {
               BoxDel(g_zones[i].bx);
               ARemove(g_zones, i);
               continue;
            }
         }
         if((g_zones[i].bull && bullBOS) || (!g_zones[i].bull && bearBOS))
         { g_zones[i].confirmed = true; g_zones[i].depStrong = mvStrong; changed = true; }
         else if(g_bi - g_zones[i].idx > i_rjbBars)
         { g_zones[i].broken = true; g_zones[i].brokenAt = g_bi; changed = true; }
      }
      double mid = (g_zones[i].top + g_zones[i].bottom) * 0.5;
      bool touchedNow = false;
      if(g_zones[i].bull)
      {
         if(!isna(swL) && swL > g_zones[i].top && (isna(g_zones[i].idmLvl) || swL < g_zones[i].idmLvl)) g_zones[i].idmLvl = swL;
         if(!isna(g_zones[i].idmLvl) && !g_zones[i].idmSwept && low < g_zones[i].idmLvl && low > g_zones[i].top) { g_zones[i].idmSwept = true; changed = true; }
         if(low > g_zones[i].top && low <= g_zones[i].top + 0.5 * aV && isna(g_zones[i].nearMiss)) g_zones[i].nearMiss = low;
         if(!isna(g_zones[i].nearMiss) && !g_zones[i].nearSwept && low < g_zones[i].nearMiss && close > g_zones[i].nearMiss) { g_zones[i].nearSwept = true; changed = true; }
         if(close < g_zones[i].bottom)
         {
            if(g_zones[i].kind == "SR" && !g_zones[i].flipped)
            {
               g_zones[i].bull = false; g_zones[i].flipped = true; g_zones[i].touches = 0; g_zones[i].sweepReq = false;
               ZReset(i); changed = true;
               if(g_zones[i].kl >= 4) { ft.evtDn = "FLIP S→R"; ft.tipDn = "Support broken on close — same wick zone now acts as resistance (§6.3)."; }
            }
            else if(g_zones[i].kind == "OB")
            {
               g_zones[i].kind = "BRK"; g_zones[i].bull = false; g_zones[i].touches = 0; g_zones[i].tapped = false; g_zones[i].sweepReq = false;
               ZReset(i); changed = true;
               ft.evtDn = "BRK▼"; ft.tipDn = "Bullish OB broken on close → bearish Breaker Block (§6.7).";
               if(!onBrk && g_zones[i].bx != "") { BoxDel(g_zones[i].bx); g_zones[i].bx = ""; }
            }
            else { g_zones[i].broken = true; g_zones[i].brokenAt = g_bi; changed = true; }
         }
         else if(low <= g_zones[i].top)
         {
            touchedNow = true;
            if(!g_zones[i].tapped) { g_zones[i].tapped = true; changed = true; }
            if(low <= mid && !g_zones[i].fiftyHit) g_zones[i].fiftyHit = true;
            if(g_bi - g_zones[i].lastTouch > i_touchCd && L(1) > g_zones[i].top)
            {
               g_zones[i].touches++;
               g_zones[i].lastTouch = g_bi;
               if(g_zones[i].touches >= 2 && !g_zones[i].sweepReq)
               {
                  g_zones[i].sweepReq = true; changed = true;
                  if(g_zones[i].kind == "OB" || g_zones[i].kind == "BRK")
                  { ft.evtUp = "⚠SWEEP REQ"; ft.tipUp = "Zone touched >= 2x — direct reversal forbidden, wait for a sweep + pin bar (§6.2)."; }
               }
            }
         }
         else if(g_zones[i].fiftyHit && g_zones[i].touches >= 1 && !g_zones[i].prop && ft.newBullFvg && g_bi - g_zones[i].lastTouch <= i_propWin &&
                 low - g_zones[i].top >= i_propImp * aV && low - g_zones[i].top <= i_propImp * aV * 3)
         {
            g_zones[i].prop = true; g_zones[i].touches = 0; g_zones[i].tapped = false; g_zones[i].sweepReq = false;
            ZReset(i); changed = true;
            ft.newProp = true; ft.evtUp = "PROP▲";
            ft.tipUp = "Propulsion Block: price used this zone for a strong move, returned, and departed again with an imbalance. Trade the NEXT tap of its 50% (§6.9).";
         }
      }
      else
      {
         if(!isna(swH) && swH < g_zones[i].bottom && (isna(g_zones[i].idmLvl) || swH > g_zones[i].idmLvl)) g_zones[i].idmLvl = swH;
         if(!isna(g_zones[i].idmLvl) && !g_zones[i].idmSwept && high > g_zones[i].idmLvl && high < g_zones[i].bottom) { g_zones[i].idmSwept = true; changed = true; }
         if(high < g_zones[i].bottom && high >= g_zones[i].bottom - 0.5 * aV && isna(g_zones[i].nearMiss)) g_zones[i].nearMiss = high;
         if(!isna(g_zones[i].nearMiss) && !g_zones[i].nearSwept && high > g_zones[i].nearMiss && close < g_zones[i].nearMiss) { g_zones[i].nearSwept = true; changed = true; }
         if(close > g_zones[i].top)
         {
            if(g_zones[i].kind == "SR" && !g_zones[i].flipped)
            {
               g_zones[i].bull = true; g_zones[i].flipped = true; g_zones[i].touches = 0; g_zones[i].sweepReq = false;
               ZReset(i); changed = true;
               if(g_zones[i].kl >= 4) { ft.evtUp = "FLIP R→S"; ft.tipUp = "Resistance broken on close — same wick zone now acts as support (§6.3)."; }
            }
            else if(g_zones[i].kind == "OB")
            {
               g_zones[i].kind = "BRK"; g_zones[i].bull = true; g_zones[i].touches = 0; g_zones[i].tapped = false; g_zones[i].sweepReq = false;
               ZReset(i); changed = true;
               ft.evtUp = "BRK▲"; ft.tipUp = "Bearish OB broken on close → bullish Breaker Block (§6.7).";
               if(!onBrk && g_zones[i].bx != "") { BoxDel(g_zones[i].bx); g_zones[i].bx = ""; }
            }
            else { g_zones[i].broken = true; g_zones[i].brokenAt = g_bi; changed = true; }
         }
         else if(high >= g_zones[i].bottom)
         {
            touchedNow = true;
            if(!g_zones[i].tapped) { g_zones[i].tapped = true; changed = true; }
            if(high >= mid && !g_zones[i].fiftyHit) g_zones[i].fiftyHit = true;
            if(g_bi - g_zones[i].lastTouch > i_touchCd && H(1) < g_zones[i].bottom)
            {
               g_zones[i].touches++;
               g_zones[i].lastTouch = g_bi;
               if(g_zones[i].touches >= 2 && !g_zones[i].sweepReq)
               {
                  g_zones[i].sweepReq = true; changed = true;
                  if(g_zones[i].kind == "OB" || g_zones[i].kind == "BRK")
                  { ft.evtDn = "⚠SWEEP REQ"; ft.tipDn = "Zone touched >= 2x — direct reversal forbidden, wait for a sweep + pin bar (§6.2)."; }
               }
            }
         }
         else if(g_zones[i].fiftyHit && g_zones[i].touches >= 1 && !g_zones[i].prop && ft.newBearFvg && g_bi - g_zones[i].lastTouch <= i_propWin &&
                 g_zones[i].bottom - high >= i_propImp * aV && g_zones[i].bottom - high <= i_propImp * aV * 3)
         {
            g_zones[i].prop = true; g_zones[i].touches = 0; g_zones[i].tapped = false; g_zones[i].sweepReq = false;
            ZReset(i); changed = true;
            ft.newProp = true; ft.evtDn = "PROP▼";
            ft.tipDn = "Propulsion Block: price used this zone for a strong move, returned, and departed again with an imbalance. Trade the NEXT tap of its 50% (§6.9).";
         }
      }
      bool srOk = g_zones[i].kind != "SR" || g_zones[i].kl >= i_klMin || i_srTrade;
      if(touchedNow && !g_zones[i].broken && srOk && !g_zones[i].weak && (g_zones[i].confirmed || (i_rjbPend && g_zones[i].kind == "RJB")))
      {
         string k = g_zones[i].kind;
         int priK = k == "OB" ? 6 : k == "BRK" ? 5 : k == "RCB" ? 4 : k == "QM" ? 4 : k == "RJB" ? 3 : g_zones[i].kl >= 3 ? 2 : 1;
         int pri = (g_zones[i].confirmed ? priK : 0) + (g_zones[i].prop ? 3 : 0);
         if(g_zones[i].bull && pri > bestPri)
         {
            bestPri = pri;
            ZSFill(ft.zb, i);
            ft.atSupport = k == "SR";
            ft.atDemand  = k != "SR";
         }
         else if(!g_zones[i].bull && pri > bestPriS)
         {
            bestPriS = pri;
            ZSFill(ft.zs, i);
            ft.atResist = k == "SR";
            ft.atSupply = k != "SR";
         }
      }
      if(g_zones[i].broken && g_zones[i].bx != "") BoxSetRight(g_zones[i].bx, g_bi);
      if(changed) ZStyle(i);
      if(!g_zones[i].tapped && g_bi - g_zones[i].idx > i_zoneAge)
      {
         BoxDel(g_zones[i].bx);
         ARemove(g_zones, i);
         continue;
      }
   }
   // caps — SR has its own budget
   int srCnt = 0;
   int nzc = ArraySize(g_zones);
   for(int i = 0; i < nzc; i++) if(g_zones[i].kind == "SR") srCnt++;
   if(srCnt > i_maxZones)
      for(int i = 0; i < nzc; i++)
         if(g_zones[i].kind == "SR") { BoxDel(g_zones[i].bx); ARemove(g_zones, i); break; }
   while(ArraySize(g_zones) > i_maxZones * 2) { BoxDel(g_zones[0].bx); ARemove(g_zones, 0); }
}

//+------------------------------------------------------------------+
//| L5 HTF                                                           |
//+------------------------------------------------------------------+
void HtfEngine(const bool isNew, const double o1, const double h1, const double l1, const double c1,
               const double o2, const double h2, const double l2, const double c2,
               const double ph, const double pl, const double h3, const double l3)
{
   double close = C(0), high = H(0), low = L(0);
   if(isNew && !isna(c1))
   {
      g_cx.hBarCount++;
      if(!isna(h3) && l1 > h3) { g_sx.hFvgBT = l1; g_sx.hFvgBB = h3; g_sx.hFvgBBar = g_cx.hBarCount; }
      if(!isna(l3) && h1 < l3) { g_sx.hFvgST = l3; g_sx.hFvgSB = h1; g_sx.hFvgSBar = g_cx.hBarCount; }
      if(!isna(g_sx.hFvgBB) && g_cx.hBarCount - g_sx.hFvgBBar > 50) { g_sx.hFvgBT = NA; g_sx.hFvgBB = NA; }
      if(!isna(g_sx.hFvgST) && g_cx.hBarCount - g_sx.hFvgSBar > 50) { g_sx.hFvgST = NA; g_sx.hFvgSB = NA; }
      if(!isna(g_cx.hCurHigh) && !g_cx.hHiBroken && h1 > g_cx.hCurHigh && c1 <= g_cx.hCurHigh) g_cx.sweepUpAt = g_cx.hBarCount;
      if(!isna(g_cx.hCurLow)  && !g_cx.hLoBroken && l1 < g_cx.hCurLow  && c1 >= g_cx.hCurLow)  g_cx.sweepDnAt = g_cx.hBarCount;
      bool dispH = (h1 - l1) > 0 && MathAbs(c1 - o1) / (h1 - l1) >= 0.5;
      bool bBrk = !isna(g_cx.hCurHigh) && !g_cx.hHiBroken && c1 > g_cx.hCurHigh;
      bool sBrk = !isna(g_cx.hCurLow)  && !g_cx.hLoBroken && c1 < g_cx.hCurLow;
      if(bBrk && dispH) g_cx.hHiBroken = true;
      if(sBrk && dispH) g_cx.hLoBroken = true;
      double protH = nz(g_cx.hMajorHigh, g_cx.hCurHigh);
      double protL = nz(g_cx.hMajorLow,  g_cx.hCurLow);
      bool lhH = !isna(g_cx.hPrevHigh) && !isna(g_cx.hCurHigh) && g_cx.hCurHigh < g_cx.hPrevHigh;
      bool hlH = !isna(g_cx.hPrevLow)  && !isna(g_cx.hCurLow)  && g_cx.hCurLow  > g_cx.hPrevLow;
      bool chUpH = g_cx.hTrend == "BEAR" && ((!isna(protH) && c1 > protH) || (bBrk && hlH));
      bool chDnH = g_cx.hTrend == "BULL" && ((!isna(protL) && c1 < protL) || (sBrk && lhH));
      if(dispH)
      {
         if(chUpH)                              { g_cx.hTrend = "BULL"; g_cx.hMajorLow = g_cx.hCurLow; }
         else if(chDnH)                         { g_cx.hTrend = "BEAR"; g_cx.hMajorHigh = g_cx.hCurHigh; }
         else if(bBrk && g_cx.hTrend != "BEAR")   { g_cx.hTrend = "BULL"; g_cx.hMajorLow = g_cx.hCurLow; }
         else if(sBrk && g_cx.hTrend != "BULL")   { g_cx.hTrend = "BEAR"; g_cx.hMajorHigh = g_cx.hCurHigh; }
      }
      if(!isna(ph))
      {
         g_cx.hPrevHigh = g_cx.hCurHigh; g_cx.hCurHigh = ph; g_cx.hHiBroken = false;
         if(g_cx.hTrend == "BEAR" && isna(g_cx.hMajorHigh)) g_cx.hMajorHigh = ph;
      }
      if(!isna(pl))
      {
         g_cx.hPrevLow = g_cx.hCurLow; g_cx.hCurLow = pl; g_cx.hLoBroken = false;
         if(g_cx.hTrend == "BULL" && isna(g_cx.hMajorLow)) g_cx.hMajorLow = pl;
      }
   }
   if(!isna(g_sx.hFvgBB) && close < g_sx.hFvgBB) { g_sx.hFvgBT = NA; g_sx.hFvgBB = NA; }
   if(!isna(g_sx.hFvgST) && close > g_sx.hFvgST) { g_sx.hFvgST = NA; g_sx.hFvgSB = NA; }
   ft.inHtfFvgB = !isna(g_sx.hFvgBB) && low <= g_sx.hFvgBT && high >= g_sx.hFvgBB;
   ft.inHtfFvgS = !isna(g_sx.hFvgST) && high >= g_sx.hFvgSB && low <= g_sx.hFvgST;
   ft.htfBias    = g_cx.hTrend;
   ft.htfSweepUp = g_cx.hBarCount - g_cx.sweepUpAt < i_sweepVal;
   ft.htfSweepDn = g_cx.hBarCount - g_cx.sweepDnAt < i_sweepVal;
   if(!isna(c1) && !isna(c2))
   {
      double rr1 = h1 - l1;
      double upW = rr1 > 0 ? (h1 - MathMax(o1, c1)) / rr1 : 0.0;
      double dnW = rr1 > 0 ? (MathMin(o1, c1) - l1) / rr1 : 0.0;
      ft.htfManipBull = l1 < l2 && c1 > h2 && c1 > o1 && dnW >= i_manipWick;
      ft.htfManipBear = h1 > h2 && c1 < l2 && c1 < o1 && upW >= i_manipWick;
      ft.htfRejBear   = upW >= i_rejW && c1 < o1;
      ft.htfRejBull   = dnW >= i_rejW && c1 > o1;
   }
}

// §7.3 gate: 2 pass · 1 warn · 0 block
int Gate(const string bias, const string trend, const bool sigBull)
{
   bool htfOk = bias == "NEUTRAL" || (sigBull && bias == "BULL") || (!sigBull && bias == "BEAR");
   bool trOk  = trend == "RANGE" || (sigBull && trend == "BULLISH") || (!sigBull && trend == "BEARISH");
   bool ok = htfOk && trOk;
   return (i_gate == G3_OFF || ok) ? 2 : (i_gate == G3_WARN ? 1 : 0);
}

//+------------------------------------------------------------------+
//| L7 TRADE ENGINE                                                  |
//+------------------------------------------------------------------+
// nearest qualified opposite level at least minDist beyond px (TP1)
double NearestOpp(const bool isLong, const double px, const double minDist, const double maxDist)
{
   double best = NA;
   int nzc = ArraySize(g_zones);
   for(int i = 0; i < nzc; i++)
   {
      if(g_zones[i].broken || g_zones[i].bull == isLong) continue;
      bool qualZ = g_zones[i].kind == "SR" ? g_zones[i].kl >= i_klMin : (g_zones[i].confirmed && !g_zones[i].weak);
      if(!qualZ) continue;
      double lvl = isLong ? g_zones[i].bottom : g_zones[i].top;
      double dz = isLong ? lvl - px : px - lvl;
      bool closer = isLong ? lvl < best : lvl > best;
      if(dz >= minDist && dz <= maxDist && (isna(best) || closer)) best = lvl;
   }
   int nf = ArraySize(g_fvgs);
   for(int i = 0; i < nf; i++)
   {
      if(g_fvgs[i].mitigated || g_fvgs[i].isBull == isLong) continue;
      double lvl = isLong ? g_fvgs[i].bottom : g_fvgs[i].top;
      double dg = isLong ? lvl - px : px - lvl;
      bool closer = isLong ? lvl < best : lvl > best;
      if(dg >= minDist && dg <= maxDist && (isna(best) || closer)) best = lvl;
   }
   int nl = ArraySize(g_lv);
   for(int i = 0; i < nl; i++)
   {
      if(g_lv[i].done || g_lv[i].isHigh != isLong) continue;
      bool qualL = g_lv[i].pooled || QualKind(g_lv[i].kind) || (i_sweepQual == SQ_EXT && g_lv[i].ext);
      if(!qualL) continue;
      double dl = isLong ? g_lv[i].price - px : px - g_lv[i].price;
      bool closer = isLong ? g_lv[i].price < best : g_lv[i].price > best;
      if(dl >= minDist && dl <= maxDist && (isna(best) || closer)) best = g_lv[i].price;
   }
   return best;
}

// 0 clear · 2 qualified opposing zone / FVG in the path · 1 qualified liquidity in the path
int PathBlock(const bool isLong, const double px, const double tp, const double aV)
{
   double tol = aV * 0.10;
   int hit = 0;
   int nzc = ArraySize(g_zones);
   for(int i = 0; i < nzc; i++)
   {
      if(g_zones[i].broken || g_zones[i].bull == isLong) continue;
      bool qualZ = g_zones[i].kind == "SR" ? g_zones[i].kl >= i_klMin : (g_zones[i].confirmed && !g_zones[i].weak);
      double lvl = isLong ? g_zones[i].bottom : g_zones[i].top;
      if(qualZ && ((isLong && lvl > px + tol && lvl < tp - tol) || (!isLong && lvl < px - tol && lvl > tp + tol))) { hit = 2; break; }
   }
   int nf = ArraySize(g_fvgs);
   if(hit == 0)
      for(int i = 0; i < nf; i++)
      {
         if(g_fvgs[i].mitigated || g_fvgs[i].isBull == isLong) continue;
         double lvl = isLong ? g_fvgs[i].bottom : g_fvgs[i].top;
         if((isLong && lvl > px + tol && lvl < tp - tol) || (!isLong && lvl < px - tol && lvl > tp + tol)) { hit = 2; break; }
      }
   int nl = ArraySize(g_lv);
   if(hit == 0)
      for(int i = 0; i < nl; i++)
      {
         if(g_lv[i].done || g_lv[i].isHigh != isLong) continue;
         bool qualL = g_lv[i].pooled || QualKind(g_lv[i].kind);
         double P = g_lv[i].price;
         if(qualL && ((isLong && P > px + tol && P < tp - tol) || (!isLong && P < px - tol && P > tp + tol))) { hit = 1; break; }
      }
   return hit;
}

// nearest unresolved liquidity beyond a price
double NearestLiq(const bool isLong, const double px)
{
   double best = NA;
   if(isna(px)) return best;
   int n = ArraySize(g_lv);
   for(int i = 0; i < n; i++)
   {
      if(g_lv[i].done || g_lv[i].isHigh != isLong) continue;
      double P = g_lv[i].price;
      if((isLong && P > px && (isna(best) || P < best)) || (!isLong && P < px && (isna(best) || P > best))) best = P;
   }
   return best;
}

// §9.4 confluence score
int Conf(const string trendStr, const bool isLong)
{
   double close = C(0);
   ZS zz; if(isLong) zz = ft.zb; else zz = ft.zs;
   int sc = 1;
   sc += ((isLong && ft.htfBias == "BULL") || (!isLong && ft.htfBias == "BEAR")) ? 1 : 0;
   sc += ((isLong && trendStr == "BULLISH") || (!isLong && trendStr == "BEARISH")) ? 1 : 0;
   bool pbWv = i_ltfPb && zz.kind != "" && ((isLong && ft.htfBias == "BULL" && ft.inDiscount) || (!isLong && ft.htfBias == "BEAR" && ft.inPremium));
   sc -= (!pbWv && ((isLong && trendStr == "BEARISH") || (!isLong && trendStr == "BULLISH"))) ? 1 : 0;
   int poiPts = ((zz.depStrong && zz.arr == 1) ? 1 : 0) + ((zz.kind != "" && zz.touches <= 1) ? 1 : 0) + (zz.kl >= 4 ? 1 : 0) +
                ((zz.kind != "" && ((isLong && ft.atBullFvg) || (!isLong && ft.atBearFvg))) ? 1 : 0);
   sc += MathMin(poiPts, 2);
   sc += ((isLong && ft.bslAbove >= 2) || (!isLong && ft.sslBelow >= 2)) ? 1 : 0;
   sc += ((isLong && (ft.sweptLowQ || zz.idm)) || (!isLong && (ft.sweptHighQ || zz.idm)) || zz.sw == 2) ? 1 : 0;
   sc -= zz.arr == -1 ? 2 : 0;
   sc -= (zz.sweepReq && zz.sw == 0 && !((isLong && ft.sweptLow) || (!isLong && ft.sweptHigh))) ? 2 : 0;
   sc -= trendStr == "RANGE" ? 1 : 0;
   sc += ((isLong && ft.inHtfFvgB) || (!isLong && ft.inHtfFvgS)) ? 1 : 0;
   sc += (!isna(ft.htfPdPct) && ((isLong && ft.htfPdPct <= 0.5) || (!isLong && ft.htfPdPct >= 0.5))) ? 1 : 0;
   int locPts = 0;
   if(i_pdOn)
   {
      bool ote = isLong ? (ft.pdPct >= 0.21 && ft.pdPct <= 0.38) : (ft.pdPct >= 0.62 && ft.pdPct <= 0.79);
      locPts = (ote && !ft.pdBeyond) ? 2 :
               ((isLong && ft.inDiscount) || (!isLong && ft.inPremium)) ? 1 :
               ((isLong && ft.pdPct > i_pdDeep) || (!isLong && ft.pdPct < 1.0 - i_pdDeep)) ? -1 : 0;
   }
   if(i_nyOpen && !isna(nyOpen) && locPts == 0)
      locPts = ((isLong && close < nyOpen) || (!isLong && close > nyOpen)) ? 1 : 0;
   sc += locPts;
   if(i_ssnScore && !ssnFilt)
      sc += (ft.sessName == "London" || ft.sessName == "NY") ? 1 : 0;
   return sc;
}

// §9.2 SL
double Stop(const bool isLong, const double aV, const double ep, const double x)
{
   double buf = aV * i_slBuf;
   double xx = isLong ? MathMin(x, nz(ft.sweptExtLo, x)) : MathMax(x, nz(ft.sweptExtHi, x));
   double sl = NA;
   ZS zz; if(isLong) zz = ft.zb; else zz = ft.zs;
   if(zz.kind != "")
      sl = isLong ? MathMin(zz.bottom, xx) - buf : MathMax(zz.top, xx) + buf;
   else if((isLong && ft.sweptLow) || (!isLong && ft.sweptHigh))
      sl = isLong ? xx - buf : xx + buf;
   else
   {
      double maj = isLong ? g_cx.majorLow : g_cx.majorHigh;
      if(!isna(maj) && MathAbs(ep - maj) <= aV * i_maxSL)
         sl = isLong ? MathMin(maj, xx) - buf : MathMax(maj, xx) + buf;
      else
         sl = isLong ? xx - buf : xx + buf;
   }
   if((isLong && (sl >= ep || ep - sl > aV * i_maxSL * 2)) || (!isLong && (sl <= ep || sl - ep > aV * i_maxSL * 2)))
      sl = isLong ? MathMin(xx, ep) - buf : MathMax(xx, ep) + buf;
   return sl;
}

// build one Sig
Sig MakeSig(const string trendStr, const string name, const int tier, const string note, const bool isLong, const double aV, const double x, const double lim)
{
   double close = C(0), high = H(0), low = L(0);
   Sig g;
   g.name  = name;
   g.dir   = isLong ? 1 : -1;
   g.entry = close;
   ZS zzE; if(isLong) zzE = ft.zb; else zzE = ft.zs;
   if(i_entryPx == EP_ZONE && zzE.kind != "")
   {
      g.entry = isLong ? zzE.top : zzE.bottom;
      g.note  = "LIMIT @ zone edge · ";
   }
   else if(i_entryPx == EP_CANDLE || i_entryPx == EP_ZONE)
   {
      g.entry = (high + low) * 0.5;
      g.note  = "LIMIT @ candle 50% · ";
   }
   double m10px = isLong ? ft.sweptPriceLo : ft.sweptPriceHi;
   if(name == "M10" && i_entryMode != ME_IMM && !isna(m10px))
   {
      g.entry = m10px;
      g.note  = i_entryMode == ME_RETEST ? "RETEST limit @ swept level · " : "BOTH: immediate + retest limit @ level · ";
   }
   if(!isna(lim))
   {
      g.entry = lim;
      g.note  = "MSS → FVG limit · ";
   }
   g.sl = Stop(isLong, aV, g.entry, x);
   double risk = MathAbs(g.entry - g.sl);
   double minR = MathMax(MathMax(_Point * i_minRiskT, aV * i_minRiskA), risk <= 0 ? aV * 0.5 : 0.0);
   if(risk < minR)
   {
      risk = minR;
      g.sl = isLong ? g.entry - risk : g.entry + risk;
   }
   bool okRR = true;
   if(i_fixedR)
   {
      g.tp1 = isLong ? g.entry + i_fixedRm * risk : g.entry - i_fixedRm * risk;
      g.tp2 = isLong ? g.tp1 + risk : g.tp1 - risk;
      g.tp3 = isLong ? g.tp2 + risk : g.tp2 - risk;
      g.tgt = "FIXED-R";
   }
   else
   {
      double need = risk * i_minRR;
      double cap  = risk * i_maxRR;
      double tpA  = NearestOpp(isLong, g.entry, need, 1.0e10);
      if(isna(tpA) && g.entry != close && name == "M10")
      {
         g.entry = close;
         g.note  = g.note + "R:R fallback → IMMEDIATE entry · ";
         g.sl    = Stop(isLong, aV, g.entry, x);
         risk    = MathAbs(g.entry - g.sl);
         if(risk <= 0)
         {
            risk = aV * 0.5;
            g.sl = isLong ? g.entry - risk : g.entry + risk;
         }
         need = risk * i_minRR;
         cap  = risk * i_maxRR;
         tpA  = NearestOpp(isLong, g.entry, need, 1.0e10);
      }
      if(isna(tpA))
      {
         if(i_rrReal) okRR = false;
         else
         {
            tpA   = isLong ? g.entry + need : g.entry - need;
            g.tgt = "SYNTH";
         }
      }
      else g.tgt = MathAbs(tpA - g.entry) > cap ? "FAR" : "REAL";
      // v8.5.4 R-14
      double tpF = tpA;
      double tpX = g.tgt == "FAR" ? NearestLiq(isLong, isLong ? g.entry + need : g.entry - need) : NA;
      if(!isna(tpX) && MathAbs(tpX - g.entry) <= cap)
      {
         tpA   = tpX;
         g.tgt = "LIQ";
      }
      g.tp1 = tpA;
      double tpB = NearestLiq(isLong, isna(g.tp1) ? g.entry : g.tp1);
      if(g.tgt == "LIQ") g.tp2 = tpF;
      else g.tp2 = (!isna(tpB) && ((isLong && tpB >= g.tp1 + risk) || (!isLong && tpB <= g.tp1 - risk))) ? tpB : (isLong ? g.tp1 + risk : g.tp1 - risk);
      double tpC = NearestLiq(isLong, isna(g.tp2) ? g.entry : g.tp2);
      g.tp3 = (!isna(tpC) && ((isLong && tpC >= g.tp2 + risk) || (!isLong && tpC <= g.tp2 - risk))) ? tpC : (isLong ? g.tp2 + risk : g.tp2 - risk);
   }
   g.rr = (risk > 0 && !isna(g.tp1)) ? MathAbs(g.tp1 - g.entry) / risk : 0.0;
   int blkRaw = PathBlock(isLong, g.entry, g.tp1, aV);
   int blk = (i_tpPath != G3_OFF && !isna(g.tp1)) ? blkRaw : 0;
   int pathPen = 0;
   if(blk > 0)
   {
      g.note = g.note + (blk == 2 ? "⚠ opposing zone/FVG between entry and TP1 · " : "⚠ liquidity pool between entry and TP1 · ");
      if(i_tpPath == G3_STRICT && blk == 2) okRR = false;
      else pathPen = 1;
   }
   if(isna(g.sl) || isna(g.tp1) || (isLong && (g.sl >= g.entry || g.tp1 <= g.entry)) || (!isLong && (g.sl <= g.entry || g.tp1 >= g.entry)) || (!i_fixedR && g.rr < i_minRR - 0.01))
      okRR = false;
   g.score = tier * 2 + Conf(trendStr, isLong) - pathPen - (g.tgt == "FAR" ? 1 : 0);
   g.note  = g.note + note + (g.tgt == "REAL" ? "" : " · ⚠ TP1 = " + g.tgt);
   g.name  = okRR ? name : "";
   return g;
}

// P0-5 — setup identity
string Ident(const Sig &g)
{
   ZS zz; if(g.dir == 1) zz = ft.zb; else zz = ft.zs;
   double anc = zz.kind != "" ? (zz.top + zz.bottom) * 0.5 : nz(g.dir == 1 ? ft.sweptPriceLo : ft.sweptPriceHi, 0.0);
   return g.name + (g.dir == 1 ? "L" : "S") + zz.kind + DoubleToString(anc, _Digits);
}

string GradeTxt(const int sc) { return sc >= i_gradeAp ? "A+" : sc >= i_gradeA ? "A" : "B"; }

void Bid(Best &b, const bool cond, const string name, const int sc, const string note)
{
   if(cond && sc > b.s) { b.n = name; b.s = sc; b.t = note; }
}
void AddTag(Tag &x, const int rank, const bool cond, const string tag, const string tip, const color col)
{
   if(cond && x.t == "") { x.t = tag; x.p = tip; x.c = col; x.r = rank; }
}

string RTxt(const double px, const double ep, const double rk)
{
   return (rk > 0 && !isna(px)) ? fmtPx(px) + "  (" + DoubleToString(MathAbs(px - ep) / rk, 1) + "R)" : "—";
}
string TpTip(const Sig &sg)
{
   double rk = MathAbs(sg.entry - sg.sl);
   return sg.note + "\nentry " + fmtPx(sg.entry) + " · SL " + fmtPx(sg.sl) +
          "\nTP1 " + RTxt(sg.tp1, sg.entry, rk) + (sg.tgt == "REAL" ? "  [structural]" : sg.tgt == "" ? "" : "  [⚠ " + sg.tgt + "]") +
          "\nTP2 " + RTxt(sg.tp2, sg.entry, rk) + "\nTP3 " + RTxt(sg.tp3, sg.entry, rk) +
          "\nscore " + IntegerToString(sg.score) + " (" + GradeTxt(sg.score) + ")";
}

// drawing helpers with FIFO caps
string Lbl(const bool isUp, const double y, const string s, const string tip, const color col)
{
   string n = LblCreate(isUp, y, s, tip, col);
   if(n == "") return "";
   LblPush(n, isUp, y);
   return n;
}
void EvLine(const int xa, const double y, const color col, const ENUM_LINE_STYLE sty)
{
   bool clamped = xa < g_bi - 495;
   string n = LineNew(XB(xa), y, g_bi, y, col, clamped ? STYLE_DOT : sty, 1, false);
   if(n == "") return;
   SPush(lns, n);
   while(ArraySize(lns) > i_maxLines) LineDel(SShift(lns));
}
void TradeLines(const Sig &g, const int nBars)
{
   int xEnd = g_bi + nBars;
   SPush(tradeLns, LineNew(g_bi, g.entry, xEnd, g.entry, Col(i_cHtf, 10), STYLE_SOLID, 2, false));
   SPush(tradeLns, LineNew(g_bi, g.sl,    xEnd, g.sl,    Col(i_cBear, 20), STYLE_DASH, 1, false));
   SPush(tradeLns, LineNew(g_bi, g.tp1,   xEnd, g.tp1,   Col(i_cBull, 30), STYLE_DASH, 1, false));
   SPush(tradeLns, LineNew(g_bi, g.tp2,   xEnd, g.tp2,   Col(i_cBull, 55), STYLE_DASH, 1, false));
   SPush(tradeLns, LineNew(g_bi, g.tp3,   xEnd, g.tp3,   Col(i_cBull, 75), STYLE_DASH, 1, false));
   while(ArraySize(tradeLns) > 50) LineDel(SShift(tradeLns));
}
void RetDone(const string lb, const string txt)
{
   if(lb == "" || ObjectFind(0, lb) < 0) return;
   ObjectSetString(0, lb, OBJPROP_TEXT, txt);
   if(!i_lblFilled) { TextSetColor(lb, Col(i_cInv, 40)); return; }
   color bg = Col(i_cInv, 40);
   ObjectSetInteger(0, lb, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, lb, OBJPROP_BORDER_COLOR, bg);
   for(int k = ArraySize(g_lbls) - 1; k >= 0; k--)
      if(g_lbls[k].n == lb) { LblMeasure(txt, g_lbls[k].w, g_lbls[k].h); ObjectSetInteger(0, lb, OBJPROP_XSIZE, g_lbls[k].w); break; }
}
void Notify(const string msg)
{
   if(!g_live) return;
   if(i_alertPopup) Alert(msg);
   if(i_alertPush)  SendNotification(msg);
}
string AlertMsg(const Sig &g, const string bias)
{
   return _Symbol + " | " + g.name + " " + (g.dir == 1 ? "LONG" : "SHORT") + " | " + GradeTxt(g.score) + IntegerToString(g.score) +
          " | Entry " + fmtPx(g.entry) + " SL " + fmtPx(g.sl) + " TP1 " + fmtPx(g.tp1) + " TP2 " + fmtPx(g.tp2) +
          " | risk " + fmtPx(MathAbs(g.entry - g.sl)) + " · " + DoubleToString(g.rr, 1) + "R | TF " + TfName((ENUM_TIMEFRAMES)Period()) +
          " | HTF " + bias + " | TP1 " + g.tgt;
}

//+------------------------------------------------------------------+
//| data-window buffers                                              |
//+------------------------------------------------------------------+
double B0[], B1[], B2[], B3[], B4[], B5[], B6[], B7[], B8[], B9[], B10[], B11[], B12[], B13[];

bool IsCont(const string n)
{
   return n == "M02" || n == "M05" || n == "M08" || n == "M15" || n == "M33" || n == "M36" || n == "M42" || n == "M51" || n == "M73";
}
bool Armed(const int dirWant, const int dirHave, const int atBar)
{
   return dirHave == dirWant && g_bi - atBar >= 1 && g_bi - atBar <= i_armBars;
}
bool ArmedSw(const int dirWant, const int dirHave, const int atBar)
{
   return (dirHave == dirWant || dirHave == dirWant * 2) && g_bi - atBar >= 1 && g_bi - atBar <= i_armBars;
}
// horizontal line kept as one object, moved instead of deleted / recreated every bar
void MoveLine(string &n, const int x1, const double y1, const int x2, const double y2, const color c, const ENUM_LINE_STYLE sty, const int w, const bool ray)
{
   if(isna(y1) || isna(y2)) return;
   if(n == "" || ObjectFind(0, n) < 0) { n = LineNew(x1, y1, x2, y2, c, sty, w, ray); return; }
   ObjectMove(0, n, 0, X2T(x1), y1);
   ObjectMove(0, n, 1, X2T(x2), y2);
   ObjectSetInteger(0, n, OBJPROP_COLOR, c);
   ObjectSetInteger(0, n, OBJPROP_RAY_RIGHT, ray);
}

//+------------------------------------------------------------------+
//| ORCHESTRATION — every engine once per closed bar, layer order    |
//+------------------------------------------------------------------+
void ProcessBar(const int i)
{
   g_bi = i;
   double open = O(0), high = H(0), low = L(0), close = C(0), volume = Vo(0);
   double atrV = gATR[i];

   // ── global-scope series ──
   double swingHi = PivotHighAt(i, i_swingLen);
   double swingLo = PivotLowAt(i, i_swingLen);
   double extHi   = HighestH(i_extLB, 0);
   double extLo   = LowestL(i_extLB, 0);
   double volSma  = 0;
   for(int k = 0; k < i_volLen; k++) volSma += Vo(k);
   volSma /= MathMax(i_volLen, 1);
   double rngHiN  = HighestH(i_rangeLen, 0);
   double rngLoN  = LowestL(i_rangeLen, 0);

   datetime t0 = gT[i], tp = gT[MathMax(i - 1, 0)];
   // HTF tuple — previous completed HTF candles
   int hk = FeedIdx(fHtf, t0), hkp = FeedIdx(fHtf, tp);
   bool newHtf = i > 0 && hk >= 0 && hk != hkp;
   double hO1 = NA, hH1 = NA, hL1 = NA, hC1 = NA, hO2 = NA, hH2 = NA, hL2 = NA, hC2 = NA, hH3 = NA, hL3 = NA;
   if(hk >= 1) { hO1 = fHtf.r[hk - 1].open; hH1 = fHtf.r[hk - 1].high; hL1 = fHtf.r[hk - 1].low; hC1 = fHtf.r[hk - 1].close; }
   if(hk >= 2) { hO2 = fHtf.r[hk - 2].open; hH2 = fHtf.r[hk - 2].high; hL2 = fHtf.r[hk - 2].low; hC2 = fHtf.r[hk - 2].close; }
   if(hk >= 3) { hH3 = fHtf.r[hk - 3].high; hL3 = fHtf.r[hk - 3].low; }
   double hPH = FeedPivH(fHtf, hk - 1, i_htfSwing);
   double hPL = FeedPivL(fHtf, hk - 1, i_htfSwing);
   // PDH/PDL · PWH/PWL
   bool intra = PeriodSeconds() < 86400;
   bool daily = PeriodSeconds() == 86400;
   int dk = FeedIdx(fD1, t0), dkp = FeedIdx(fD1, tp);
   int wk = FeedIdx(fW1, t0), wkp = FeedIdx(fW1, tp);
   double pdhRaw = dk >= 1 ? fD1.r[dk - 1].high : NA;
   double pdlRaw = dk >= 1 ? fD1.r[dk - 1].low  : NA;
   double pwhRaw = wk >= 1 ? fW1.r[wk - 1].high : NA;
   double pwlRaw = wk >= 1 ? fW1.r[wk - 1].low  : NA;
   bool newDay  = i_showPD && intra && i > 0 && dk >= 0 && dk != dkp;
   bool newWeek = i_showPW && (intra || daily) && i > 0 && wk >= 0 && wk != wkp;
   // sessions (killzones)
   int mT = MinuteOfDay(t0, i_ssnTz), mP = MinuteOfDay(tp, i_ssnTz);
   bool inAsia  = ssnIntra && InSess(mT, ssA0, ssA1);
   bool inAsiaP = ssnIntra && i > 0 && InSess(mP, ssA0, ssA1);
   bool inLon   = ssnIntra && InSess(mT, ssL0, ssL1);
   bool inNY    = ssnIntra && InSess(mT, ssN0, ssN1);
   bool asiaEnd = ssnIntra && !inAsia && inAsiaP;
   bool nyMid   = ssnIntra && InSess(MinuteOfDay(t0, TZ_NY), 0, 5);
   bool nyMidP  = ssnIntra && i > 0 && InSess(MinuteOfDay(tp, TZ_NY), 0, 5);
   if(nyMid && !nyMidP) nyOpen = open;

   // ── engines ──
   ft.Reset();
   double refLo = nz(g_cx.curLow, L(1));
   double refHi = nz(g_cx.curHigh, H(1));
   double preHigh = g_cx.curHigh, preLow = g_cx.curLow;
   int    preHighIdx = g_cx.curHighIdx, preLowIdx = g_cx.curLowIdx;
   string preTrend = g_cx.trend;
   CandleCalc(atrV, refLo, refHi);
   FvgEngine(atrV, d_fvg, d_fvgMit);
   bool dispOk = i_dispGate == DG_OFF || (cd.bodyRatio >= i_dispBody && cd.rng >= atrV * i_dispRng);
   Structure(swingHi, swingLo, dispOk, atrV * i_dispDist);

   bool bosEvt = st.bullBOS || st.bearBOS;
   bool wkEvt  = st.weakBullBOS || st.weakBearBOS || st.internalBullBOS || st.internalBearBOS;
   if(bosEvt || wkEvt)
   {
      mv = MoveStrength(g_cx.legIdx, g_bi, atrV, st.bullBOS || st.weakBullBOS || st.internalBullBOS);
      g_cx.lastDepStrong  = mv.strong;
      g_cx.lastBOSBar     = g_bi;
      g_cx.lastBOSAvgBody = mv.avgBody;
   }
   if(st.bullCHoCH || st.bearCHoCH)
   {
      Move mc = MoveStrength(g_cx.legIdx, g_bi, atrV, st.bullCHoCH);
      g_cx.chochReal = mc.fvgCount >= 1;
   }
   ft.dispBull      = st.bullBOS && mv.strong;
   ft.dispBear      = st.bearBOS && mv.strong;
   ft.lastDepStrong = g_cx.lastDepStrong;
   ft.chochReal     = g_cx.chochReal;
   ft.dispDir   = st.bullBOS ? 1 : st.bearBOS ? -1 : 0;
   ft.dispScore = ft.dispDir == 0 ? 0 : (mv.strong ? 1 : 0) + (mv.fvgCount >= 2 ? 1 : 0) + (mv.bodyEff >= 0.7 ? 1 : 0);

   // session feature + Asia-range liquidity
   ft.sessName = inLon ? "London" : inNY ? "NY" : inAsia ? "Asia" : "";
   ft.sbSessOk = !ssnFilt || !ssnIntra || ft.sessName != "";
   if(inAsia)
   {
      if(!inAsiaP) { asiaHi = high; asiaLo = low; }
      else { asiaHi = MathMax(nz(asiaHi, high), high); asiaLo = MathMin(nz(asiaLo, low), low); }
   }
   if(i_ssnLvl && asiaEnd && !isna(asiaHi) && !isna(asiaLo))
   {
      for(int j = ArraySize(g_lv) - 1; j >= 0; j--)
         if(!g_lv[j].done && (g_lv[j].kind == "SESH" || g_lv[j].kind == "SESL")) Resolve(j, "EXPIRED");
      AddLevel(atrV, asiaHi, g_bi, true,  "SESH", true, d_liq);
      AddLevel(atrV, asiaLo, g_bi, false, "SESL", true, d_liq);
   }

   LiqEngine(atrV, swingHi, swingLo, extHi, extLo, pdhRaw, pdlRaw, pwhRaw, pwlRaw, newDay, newWeek, d_liq);
   bool volOk = volume > volSma * i_klVolMult;
   ZonesEngine(atrV, swingHi, swingLo, st.bullBOS, st.bearBOS, st.bullCHoCH, st.bearCHoCH,
               mv.strong, mv.fvgCount, volOk, g_cx.legIdx, d_sr, d_kl, d_ob, d_brk, d_rcb, d_rjb, d_qm);
   HtfEngine(newHtf, hO1, hH1, hL1, hC1, hO2, hH2, hL2, hC2, hPH, hPL, hH3, hL3);
   string gateTrend = i_gateTrend == GT_ENTER ? preTrend : st.trend;
   ft.gateUp = Gate(ft.htfBias, gateTrend, true);
   ft.gateDn = Gate(ft.htfBias, gateTrend, false);

   // ── Premium / Discount array (current leg) ──
   pdHiB  = g_cx.majorLowIdx  != pdHiAt ? LegExt(true,  g_cx.majorLowIdx)  : MathMax(nz(pdHiB, high), high);
   pdHiAt = g_cx.majorLowIdx;
   pdLoS  = g_cx.majorHighIdx != pdLoAt ? LegExt(false, g_cx.majorHighIdx) : MathMin(nz(pdLoS, low), low);
   pdLoAt = g_cx.majorHighIdx;
   bool bullPD = st.trend == "BULLISH" && !isna(g_cx.majorLow);
   bool bearPD = st.trend == "BEARISH" && !isna(g_cx.majorHigh);
   double pdHi = bullPD ? pdHiB : bearPD ? g_cx.majorHigh : g_cx.curHigh;
   double pdLo = bullPD ? g_cx.majorLow : bearPD ? pdLoS : g_cx.curLow;
   bool pdIn = !isna(pdHi) && !isna(pdLo) && pdHi > pdLo;
   g_pdIn = pdIn;
   ft.pdBeyond   = pdIn && (close > pdHi || close < pdLo);
   ft.pdPct      = pdIn ? MathMax(0.0, MathMin(1.0, (close - pdLo) / (pdHi - pdLo))) : 0.5;
   ft.inDiscount = pdIn && !ft.pdBeyond && ft.pdPct <= 0.5;
   ft.inPremium  = pdIn && !ft.pdBeyond && ft.pdPct >= 0.5;
   if(i_pdGate && pdIn && !ft.pdBeyond)
   {
      if(!ft.inDiscount) ft.gateUp = 0;
      if(!ft.inPremium)  ft.gateDn = 0;
   }

   // v8.5.2 E-3 — context-qualified internal sweep
   if(i_idmSweep && ft.sweptLow && !ft.sweptLowQ && ft.zb.kind != "" && !ft.zb.pend && ft.htfBias == "BULL" && ft.inDiscount)
   { ft.sweptLowQ = true; ft.sweptKindLo = "IDM·" + ft.sweptKindLo; g_cx.sweptLowBar = g_bi; }
   if(i_idmSweep && ft.sweptHigh && !ft.sweptHighQ && ft.zs.kind != "" && !ft.zs.pend && ft.htfBias == "BEAR" && ft.inPremium)
   { ft.sweptHighQ = true; ft.sweptKindHi = "IDM·" + ft.sweptKindHi; g_cx.sweptHighBar = g_bi; }

   // v8.5.2 E-7 — HTF dealing range
   hRunHi = (nz(g_cx.hMajorLow, -1.0)  != nz(hAncLo, -1.0) || isna(hRunHi)) ? high : MathMax(hRunHi, high);
   hRunLo = (nz(g_cx.hMajorHigh, -1.0) != nz(hAncHi, -1.0) || isna(hRunLo)) ? low  : MathMin(hRunLo, low);
   hAncLo = g_cx.hMajorLow;
   hAncHi = g_cx.hMajorHigh;
   double hPdLo = ft.htfBias == "BULL" ? g_cx.hMajorLow : ft.htfBias == "BEAR" ? MathMin(nz(g_cx.hCurLow, hRunLo), hRunLo) : g_cx.hCurLow;
   double hPdHi = ft.htfBias == "BULL" ? MathMax(nz(g_cx.hCurHigh, hRunHi), hRunHi) : ft.htfBias == "BEAR" ? g_cx.hMajorHigh : g_cx.hCurHigh;
   ft.htfPdPct = (i_hpd && ft.htfBias != "NEUTRAL" && !isna(hPdHi) && !isna(hPdLo) && hPdHi > hPdLo) ?
                 MathMax(0.0, MathMin(1.0, (close - hPdLo) / (hPdHi - hPdLo))) : NA;

   // §4.5 arrival strength
   bool zoneTouch = ft.zb.kind != "" || ft.zs.kind != "";
   int arrDirNow = ft.zb.kind != "" ? 1 : -1;
   if(zoneTouch && (g_bi - g_cx.arrivalBar > 5 || g_cx.arrivalDir != arrDirNow))
   {
      int fromIdx = arrDirNow == 1 ? g_cx.curHighIdx : g_cx.curLowIdx;
      Move ma = MoveStrength(fromIdx, g_bi, atrV, arrDirNow != 1);
      g_cx.arrivalStrong  = ma.strong;
      g_cx.arrivalBar     = g_bi;
      g_cx.arrivalDir     = arrDirNow;
      g_cx.arrivalAvgBody = ma.avgBody;
      g_cx.arrivalMixed   = ma.mixed;
   }
   if(zoneTouch && g_bi - g_cx.arrivalBar <= 10)
   {
      if(g_cx.arrivalDir == 1) { if(ft.zb.kind != "") { ft.zb.arr = g_cx.arrivalStrong ? -1 : 1; ft.zb.arrMix = g_cx.arrivalMixed; } }
      else                   { if(ft.zs.kind != "") { ft.zs.arr = g_cx.arrivalStrong ? -1 : 1; ft.zs.arrMix = g_cx.arrivalMixed; } }
      ft.retestValid = g_cx.lastBOSAvgBody > 0 && g_cx.arrivalAvgBody < g_cx.lastBOSAvgBody * i_retestBR;
   }

   // wick sequences
   double wkr = 0.4;
   ft.upWickInc = cd.upWickRatio >= wkr && g_cx.upR1 >= wkr && g_cx.upR2 >= wkr && cd.upWick > g_cx.upW1 && g_cx.upW1 > g_cx.upW2;
   ft.upWickDec = cd.upWickRatio >= 0.25 && g_cx.upW1 > cd.upWick && g_cx.upW2 > g_cx.upW1 && g_cx.upW2 > 0;
   ft.dnWickInc = cd.dnWickRatio >= wkr && g_cx.dnR1 >= wkr && g_cx.dnR2 >= wkr && cd.dnWick > g_cx.dnW1 && g_cx.dnW1 > g_cx.dnW2;
   ft.dnWickDec = cd.dnWickRatio >= 0.25 && g_cx.dnW1 > cd.dnWick && g_cx.dnW2 > g_cx.dnW1 && g_cx.dnW2 > 0;
   g_cx.upW2 = g_cx.upW1; g_cx.upW1 = cd.upWick; g_cx.dnW2 = g_cx.dnW1; g_cx.dnW1 = cd.dnWick;
   g_cx.upR2 = g_cx.upR1; g_cx.upR1 = cd.upWickRatio; g_cx.dnR2 = g_cx.dnR1; g_cx.dnR1 = cd.dnWickRatio;

   // breakout state
   ft.breakUp = st.bullBOS || st.weakBullBOS || st.internalBullBOS || st.bullCHoCH || ft.runUp;
   ft.breakDn = st.bearBOS || st.weakBearBOS || st.internalBearBOS || st.bearCHoCH || ft.runDn;
   if(ft.breakUp || ft.breakDn)
   {
      g_cx.breakDir = ft.breakUp ? 1 : -1;
      g_sx.brkInternal = st.internalBullBOS || st.internalBearBOS;
      bool stUp = st.bullBOS || st.weakBullBOS || st.internalBullBOS;
      bool stDn = st.bearBOS || st.weakBearBOS || st.internalBearBOS;
      g_cx.breakLvl = ft.breakUp ? (st.bullCHoCH ? st.chLvl : stUp ? preHigh : nz(ft.runPrice, ft.sweptPrice))
                               : (st.bearCHoCH ? st.chLvl : stDn ? preLow  : nz(ft.runPrice, ft.sweptPrice));
      if(isna(g_cx.breakLvl)) g_cx.breakLvl = ft.breakUp ? preHigh : preLow;
      g_cx.breakBar = g_bi; g_cx.breakLo = low; g_cx.breakHi = high;
   }
   ft.breakAgo     = g_bi - g_cx.breakBar;
   ft.fakeBreak    = ft.breakAgo == 1 && !isna(g_cx.breakLvl) && (g_cx.breakDir == 1 ? close < g_cx.breakLvl : close > g_cx.breakLvl);
   ft.breakPinBull = ft.breakUp && !g_sx.brkInternal && cd.pinBull && !isna(g_cx.breakLvl) && low < g_cx.breakLvl;
   ft.breakPinBear = ft.breakDn && !g_sx.brkInternal && cd.pinBear && !isna(g_cx.breakLvl) && high > g_cx.breakLvl;
   bool contBrk = !g_sx.brkInternal;

   // panel: last structural event
   if(st.bullCHoCH || st.bearCHoCH) { g_cx.lastEvt = (st.bullCHoCH ? "CHoCH▲" : "CHoCH▼") + (g_cx.chochReal ? " (real)" : " (fake)"); g_cx.lastEvtBar = g_bi; }
   else if(bosEvt)                  { g_cx.lastEvt = (st.bullBOS ? "BOS▲" : "BOS▼") + (mv.strong ? " strong" : " weak"); g_cx.lastEvtBar = g_bi; }
   else if(st.cisdBull || st.cisdBear) { g_cx.lastEvt = st.cisdBull ? "CISD▲" : "CISD▼"; g_cx.lastEvtBar = g_bi; }
   else if(ft.sweptHigh || ft.sweptLow) { g_cx.lastEvt = "SWEEP " + ft.sweptKind; g_cx.lastEvtBar = g_bi; }
   bool fiftyNow = (ft.zb.kind == "OB" && ft.zb.fifty) || (ft.zs.kind == "OB" && ft.zs.fifty);
   ft.enteredOb50 = fiftyNow && !g_cx.fiftyPrev;
   g_cx.fiftyPrev = fiftyNow;

   // range + price inside an unmitigated FVG
   ft.inRange = g_cx.barsSinceEvt >= i_rangeLen && (rngHiN - rngLoN) <= atrV * i_rangeMax;
   int nF = ArraySize(g_fvgs);
   for(int j = 0; j < nF; j++)
   {
      if((!g_fvgs[j].mitigated || g_fvgs[j].mitIdx == g_bi) && g_fvgs[j].idx < g_bi - 1)
      {
         if(g_fvgs[j].isBull && low <= g_fvgs[j].top && high >= g_fvgs[j].bottom && close >= g_fvgs[j].bottom)
         {
            ft.atBullFvg = true;
            if(g_cx.sweptLowBar >= 0 && g_fvgs[j].idx >= g_cx.sweptLowBar - i_failBars) ft.atBullFvgF = true;
         }
         if(!g_fvgs[j].isBull && high >= g_fvgs[j].bottom && low <= g_fvgs[j].top && close <= g_fvgs[j].top)
         {
            ft.atBearFvg = true;
            if(g_cx.sweptHighBar >= 0 && g_fvgs[j].idx >= g_cx.sweptHighBar - i_failBars) ft.atBearFvgF = true;
         }
      }
   }
   if(ft.newBullFvg) g_cx.bullFvgBar = g_bi;
   if(ft.newBearFvg) g_cx.bearFvgBar = g_bi;
   ft.sweepBosBear   = g_bi - g_cx.sweptHighBar <= 10 && g_cx.sweptHighBar >= 0 && st.bearBOS;
   ft.sweepBosBull   = g_bi - g_cx.sweptLowBar  <= 10 && g_cx.sweptLowBar  >= 0 && st.bullBOS;
   ft.sweepChochBear = g_bi - g_cx.sweptHighBar <= 10 && g_cx.sweptHighBar >= 0 && st.bearCHoCH;
   ft.sweepChochBull = g_bi - g_cx.sweptLowBar  <= 10 && g_cx.sweptLowBar  >= 0 && st.bullCHoCH;
   if(ft.sweepBosBear)   { g_cx.m45Dir = -1; g_cx.m45Bar = g_bi; }
   if(ft.sweepBosBull)   { g_cx.m45Dir = 1;  g_cx.m45Bar = g_bi; }
   if(ft.sweepChochBear) { g_cx.m45Dir = -2; g_cx.m45Bar = g_bi; }
   if(ft.sweepChochBull) { g_cx.m45Dir = 2;  g_cx.m45Bar = g_bi; }
   if(st.bearBOS && g_bi - g_cx.sweptHighBar <= 20 && g_cx.sweptHighBar >= 0) { g_cx.m41Dir = mv.strong ? -1 : -9; g_cx.m41Bar = g_bi; }
   if(st.bullBOS && g_bi - g_cx.sweptLowBar  <= 20 && g_cx.sweptLowBar  >= 0) { g_cx.m41Dir = mv.strong ? 1 : 9;   g_cx.m41Bar = g_bi; }
   int relCntBear = ((ft.htfRejBear || ft.htfSweepUp) ? 1 : 0) + (g_bi - g_cx.bearFvgBar <= 3 ? 1 : 0) + (g_bi - g_cx.sweptHighBar <= 5 ? 1 : 0);
   int relCntBull = ((ft.htfRejBull || ft.htfSweepDn) ? 1 : 0) + (g_bi - g_cx.bullFvgBar <= 3 ? 1 : 0) + (g_bi - g_cx.sweptLowBar  <= 5 ? 1 : 0);
   ft.cisdRel = st.cisdBear ? relCntBear : st.cisdBull ? relCntBull : 0;
   if(st.cisdBear && relCntBear > 0) { g_cx.m46Dir = -1; g_cx.m46Bar = g_bi; }
   if(st.cisdBull && relCntBull > 0) { g_cx.m46Dir = 1;  g_cx.m46Bar = g_bi; }
   // M54
   if(ft.atDemand && g_cx.m54Stage == 0) { g_cx.m54Stage = 1; g_cx.m54Bar = g_bi; g_sx.m54Zb = ft.zb.bottom; }
   if(g_cx.m54Stage == 1 && g_bi > g_cx.m54Bar && ft.sweptLowQ && ft.sweptPriceLo <= g_sx.m54Zb && ft.sweptPriceLo >= g_sx.m54Zb - atrV * 1.5) { g_cx.m54Stage = 2; g_cx.m54Bar = g_bi; }
   if(g_cx.m54Stage == 2 && g_bi > g_cx.m54Bar && st.bullBOS && g_cx.legIdx >= g_cx.sweptLowBar - i_failBars) { g_cx.m54Stage = 3; g_cx.m54Bar = g_bi; }
   if(g_cx.m54Stage > 0 && g_bi - g_cx.m54Bar > i_armBars * 2) g_cx.m54Stage = 0;
   if(ft.atSupply && g_cx.m54StageB == 0) { g_cx.m54StageB = 1; g_cx.m54BarB = g_bi; g_sx.m54Zs = ft.zs.top; }
   if(g_cx.m54StageB == 1 && g_bi > g_cx.m54BarB && ft.sweptHighQ && ft.sweptPriceHi >= g_sx.m54Zs && ft.sweptPriceHi <= g_sx.m54Zs + atrV * 1.5) { g_cx.m54StageB = 2; g_cx.m54BarB = g_bi; }
   if(g_cx.m54StageB == 2 && g_bi > g_cx.m54BarB && st.bearBOS && g_cx.legIdx >= g_cx.sweptHighBar - i_failBars) { g_cx.m54StageB = 3; g_cx.m54BarB = g_bi; }
   if(g_cx.m54StageB > 0 && g_bi - g_cx.m54BarB > i_armBars * 2) g_cx.m54StageB = 0;

   // M01/M02 pre-condition: separate rejections of the broken level
   if((ft.breakUp || ft.breakDn) && !isna(g_cx.breakLvl))
   {
      int tCnt = 0; bool wasAt = false;
      for(int k = 1; k <= 30; k++)
      {
         bool atLvl = H(k) >= g_cx.breakLvl - atrV * i_touchTol && L(k) <= g_cx.breakLvl + atrV * i_touchTol;
         if(atLvl && !wasAt) tCnt++;
         wasAt = atLvl;
      }
      g_cx.brkTouch = tCnt;
   }
   ft.brkTouches = g_cx.brkTouch;

   // ── M64 trendline engine ──
   double tlz = atrV * i_tlTol;
   if(st.swingLow && !isna(g_cx.prevLow) && g_cx.curLow > g_cx.prevLow)
   {
      int o1r = g_bi - g_cx.prevLowIdx, o2r = g_bi - g_cx.curLowIdx;
      bool bodyOk = i_tlAnchor == TL_BODY && o1r >= 0 && o1r < 500 && o2r >= 0 && o2r < 500;
      int o1 = MathMin(MathMax(o1r, 0), 499), o2 = MathMin(MathMax(o2r, 0), 499);
      g_sx.tlSx1 = g_cx.prevLowIdx; g_sx.tlSy1 = bodyOk ? MathMin(O(o1), C(o1)) : g_cx.prevLow;
      g_sx.tlSx2 = g_cx.curLowIdx;  g_sx.tlSy2 = bodyOk ? MathMin(O(o2), C(o2)) : g_cx.curLow;
      g_sx.tlSTouch = 2; g_sx.tlSBroken = false;
   }
   if(st.swingHigh && !isna(g_cx.prevHigh) && g_cx.curHigh < g_cx.prevHigh)
   {
      int p1r = g_bi - g_cx.prevHighIdx, p2r = g_bi - g_cx.curHighIdx;
      bool bodyOkR = i_tlAnchor == TL_BODY && p1r >= 0 && p1r < 500 && p2r >= 0 && p2r < 500;
      int p1 = MathMin(MathMax(p1r, 0), 499), p2 = MathMin(MathMax(p2r, 0), 499);
      g_sx.tlRx1 = g_cx.prevHighIdx; g_sx.tlRy1 = bodyOkR ? MathMax(O(p1), C(p1)) : g_cx.prevHigh;
      g_sx.tlRx2 = g_cx.curHighIdx;  g_sx.tlRy2 = bodyOkR ? MathMax(O(p2), C(p2)) : g_cx.curHigh;
      g_sx.tlRTouch = 2; g_sx.tlRBroken = false;
   }
   double slopeS = g_sx.tlSx2 > g_sx.tlSx1 ? (g_sx.tlSy2 - g_sx.tlSy1) / (g_sx.tlSx2 - g_sx.tlSx1) : 0.0;
   double slopeR = g_sx.tlRx2 > g_sx.tlRx1 ? (g_sx.tlRy2 - g_sx.tlRy1) / (g_sx.tlRx2 - g_sx.tlRx1) : 0.0;
   double tlSraw = (!isna(g_sx.tlSy2) && g_sx.tlSx2 > g_sx.tlSx1) ? g_sx.tlSy2 + slopeS * (g_bi - g_sx.tlSx2) : NA;
   double tlRraw = (!isna(g_sx.tlRy2) && g_sx.tlRx2 > g_sx.tlRx1) ? g_sx.tlRy2 + slopeR * (g_bi - g_sx.tlRx2) : NA;
   bool tlSFresh = !isna(tlSraw) && g_bi - g_sx.tlSx1 <= 250 && MathAbs(close - tlSraw) <= atrV * 10 && MathAbs(slopeS) <= atrV * 0.5;
   bool tlRFresh = !isna(tlRraw) && g_bi - g_sx.tlRx1 <= 250 && MathAbs(close - tlRraw) <= atrV * 10 && MathAbs(slopeR) <= atrV * 0.5;
   double tlS = (g_sx.tlSBroken || !tlSFresh) ? NA : tlSraw;
   double tlR = (g_sx.tlRBroken || !tlRFresh) ? NA : tlRraw;
   if(!isna(tlS) && g_bi > g_sx.tlSx2 + 1)
   {
      if(low <= tlS + tlz && low >= tlS - tlz && close > tlS) g_sx.tlSTouch++;
      if(close < tlS - tlz) g_sx.tlSBroken = true;
   }
   if(!isna(tlR) && g_bi > g_sx.tlRx2 + 1)
   {
      if(high >= tlR - tlz && high <= tlR + tlz && close < tlR) g_sx.tlRTouch++;
      if(close > tlR + tlz) g_sx.tlRBroken = true;
   }
   int tlNeed = i_tlConfirm ? 3 : 2;
   ft.tlSupValid = !isna(tlS) && g_sx.tlSTouch >= tlNeed;
   ft.tlResValid = !isna(tlR) && g_sx.tlRTouch >= tlNeed;
   ft.atTLsup = ft.tlSupValid && low <= tlS + tlz && close >= tlS - tlz;
   ft.atTLres = ft.tlResValid && high >= tlR - tlz && close <= tlR + tlz;

   // ── L6 SETUPS ──
   bool revBull = cd.pinBull || cd.engulfBull || cd.ifcBull || cd.manipBull;
   bool revBear = cd.pinBear || cd.engulfBear || cd.ifcBear || cd.manipBear;
   double mssHi = HighestH(5, 1);
   double mssLo = LowestL(5, 1);
   if(!immMode && g_sx.poiDirL == 1 && ft.zb.kind == "" && g_sx.hasPoiZb)
   { ft.zb = g_sx.poiZb; ft.atDemand = ft.zb.kind != "SR"; ft.atSupport = ft.zb.kind == "SR"; }
   if(!immMode && g_sx.poiDirS == 1 && ft.zs.kind == "" && g_sx.hasPoiZs)
   { ft.zs = g_sx.poiZs; ft.atSupply = ft.zs.kind != "SR"; ft.atResist = ft.zs.kind == "SR"; }
   bool atBullZone = ft.zb.kind != "";
   bool atBearZone = ft.zs.kind != "";
   bool bullTrend  = st.trend == "BULLISH";
   bool bearTrend  = st.trend == "BEARISH";
   bool zMidB = ft.zb.kind == "" || i_zClose == ZC_OFF || close >= (i_zClose == ZC_TOP ? ft.zb.top : (ft.zb.top + ft.zb.bottom) * 0.5);
   bool zMidS = ft.zs.kind == "" || i_zClose == ZC_OFF || close <= (i_zClose == ZC_TOP ? ft.zs.bottom : (ft.zs.top + ft.zs.bottom) * 0.5);
   bool poiArmL = !immMode && g_sx.poiDirL == 1 && g_sx.hasPoiZb && ft.zb.top == g_sx.poiZb.top && ft.zb.bottom == g_sx.poiZb.bottom;
   bool poiArmS = !immMode && g_sx.poiDirS == 1 && g_sx.hasPoiZs && ft.zs.top == g_sx.poiZs.top && ft.zs.bottom == g_sx.poiZs.bottom;
   if(poiArmL) ft.zb.sw = g_sx.poiSwL;
   if(poiArmS) ft.zs.sw = g_sx.poiSwS;
   bool zoneOkBull = atBullZone && !ft.zb.pend && zMidB && (!fl_SwR || !ft.zb.sweepReq || ft.sweptLow || poiArmL) && (!fl_50 || ft.zb.kind == "SR" || ft.zb.fifty);
   bool zoneOkBear = atBearZone && !ft.zs.pend && zMidS && (!fl_SwR || !ft.zs.sweepReq || ft.sweptHigh || poiArmS) && (!fl_50 || ft.zs.kind == "SR" || ft.zs.fifty);
   bool arrOkBull  = !fl_M19 || ft.zb.arr != -1;
   bool arrOkBear  = !fl_M19 || ft.zs.arr != -1;
   bool pbOkL      = !fl_M26 || ft.zb.arr != -1 || ft.zb.arrMix >= 0.35;
   bool pbOkS      = !fl_M26 || ft.zs.arr != -1 || ft.zs.arrMix >= 0.35;
   bool rtOk       = !fl_M31 || !(zoneTouch && ft.retestValid == false && g_cx.lastBOSAvgBody > 0);
   bool brkWin     = ft.breakAgo >= 1 && ft.breakAgo <= 8;
   bool brkTouchOk = !fl_M01T || ft.brkTouches >= 2;

   // S11 POI reaction state machine
   bool poiConfL = false, poiConfS = false;
   if(!immMode)
   {
      double poiBuf = atrV * 0.15;
      if(g_sx.poiDirL == 1 && (g_bi - g_sx.poiBarL > i_poiBars || close < g_sx.poiLowL - poiBuf)) g_sx.poiDirL = 0;
      if(g_sx.poiDirS == 1 && (g_bi - g_sx.poiBarS > i_poiBars || close > g_sx.poiHighS + poiBuf)) g_sx.poiDirS = 0;
      bool cfUp = cd.isBull && close > g_sx.poiRefL + atrV * i_confDist && cd.bodyRatio >= i_confBody;
      bool cfDn = cd.isBear && close < g_sx.poiRefS - atrV * i_confDist && cd.bodyRatio >= i_confBody;
      if(g_sx.poiDirL == 1 && g_bi - g_sx.poiBarL >= 1 && (cfUp || ft.newBullFvg)) { poiConfL = true; g_sx.poiDirL = 0; }
      if(g_sx.poiDirS == 1 && g_bi - g_sx.poiBarS >= 1 && (cfDn || ft.newBearFvg)) { poiConfS = true; g_sx.poiDirS = 0; }
      if(g_sx.poiDirL == 0 && !poiConfL && (zoneOkBull || ft.atBullFvg) && revBull)
      {
         g_sx.poiDirL = 1; g_sx.poiBarL = g_bi;
         g_sx.poiRefL = mssMode ? MathMax(high, mssHi) : high;
         g_sx.poiWickL = cd.dnWickRatio;
         g_sx.poiLowL = MathMin(low, nz(ft.zb.bottom, low));
         g_sx.poiFvgL = ft.atBullFvg && ft.zb.kind == "";
         g_sx.poiZb = ft.zb; g_sx.hasPoiZb = true;
         g_sx.poiSwL = ft.sweptLowQ ? 2 : ft.sweptLow ? 1 : 0;
      }
      if(g_sx.poiDirS == 0 && !poiConfS && (zoneOkBear || ft.atBearFvg) && revBear)
      {
         g_sx.poiDirS = 1; g_sx.poiBarS = g_bi;
         g_sx.poiRefS = mssMode ? MathMin(low, mssLo) : low;
         g_sx.poiWickS = cd.upWickRatio;
         g_sx.poiHighS = MathMax(high, nz(ft.zs.top, high));
         g_sx.poiFvgS = ft.atBearFvg && ft.zs.kind == "";
         g_sx.poiZs = ft.zs; g_sx.hasPoiZs = true;
         g_sx.poiSwS = ft.sweptHighQ ? 2 : ft.sweptHigh ? 1 : 0;
      }
   }
   bool trigBull = immMode ? revBull : poiConfL;
   bool trigBear = immMode ? revBear : poiConfS;

   // C — M10 sweep reversal
   bool freshDispUp = g_cx.breakDir == 1  && g_bi - g_cx.breakBar <= 10 && g_cx.lastDepStrong;
   bool freshDispDn = g_cx.breakDir == -1 && g_bi - g_cx.breakBar <= 10 && g_cx.lastDepStrong;
   bool s10raw  = en_M10 && !freshDispDn && (ft.sweptLowQ  || (ft.sweptLow  && ft.zb.kind != "" && (!ft.zb.pend || (ft.htfBias == "BULL" && ft.inDiscount)))) &&
                  cd.dnWickRatio >= i_sweepWick && close > ft.sweptPriceLo && close >= (high + low) * 0.5;
   bool s10braw = en_M10 && !freshDispUp && (ft.sweptHighQ || (ft.sweptHigh && ft.zs.kind != "" && (!ft.zs.pend || (ft.htfBias == "BEAR" && ft.inPremium)))) &&
                  cd.upWickRatio >= i_sweepWick && close < ft.sweptPriceHi && close <= (high + low) * 0.5;
   int m10Win = i_m10Conf == M10_CISD ? i_armBars : 3;
   bool m10Trg  = !m10Imm && g_sx.m10Dir == 1  && g_bi - g_sx.m10Bar >= 1 && g_bi - g_sx.m10Bar <= m10Win && (i_m10Conf == M10_CISD ? st.cisdBull : close > g_sx.m10Ref);
   bool m10Trgb = !m10Imm && g_sx.m10Dir == -1 && g_bi - g_sx.m10Bar >= 1 && g_bi - g_sx.m10Bar <= m10Win && (i_m10Conf == M10_CISD ? st.cisdBear : close < g_sx.m10Ref);
   if(g_sx.m10Dir == 1  && (m10Trg  || g_bi - g_sx.m10Bar > m10Win || close < g_sx.m10Ext)) g_sx.m10Dir = 0;
   if(g_sx.m10Dir == -1 && (m10Trgb || g_bi - g_sx.m10Bar > m10Win || close > g_sx.m10Ext)) g_sx.m10Dir = 0;
   if(!m10Imm && s10raw)
   { g_sx.m10Dir = 1; g_sx.m10Bar = g_bi; g_sx.m10Ref = high; g_sx.m10Ext = MathMin(low, nz(ft.sweptExtLo, low)); g_sx.m10Lvl = ft.sweptPriceLo; g_sx.m10Kind = ft.sweptKindLo; }
   if(!m10Imm && s10braw)
   { g_sx.m10Dir = -1; g_sx.m10Bar = g_bi; g_sx.m10Ref = low; g_sx.m10Ext = MathMax(high, nz(ft.sweptExtHi, high)); g_sx.m10Lvl = ft.sweptPriceHi; g_sx.m10Kind = ft.sweptKindHi; }
   if(m10Trg)  { ft.sweptLow  = true; ft.sweptPriceLo = g_sx.m10Lvl; ft.sweptKindLo = g_sx.m10Kind; ft.sweptExtLo = g_sx.m10Ext; }
   if(m10Trgb) { ft.sweptHigh = true; ft.sweptPriceHi = g_sx.m10Lvl; ft.sweptKindHi = g_sx.m10Kind; ft.sweptExtHi = g_sx.m10Ext; }
   bool s10  = m10Imm ? s10raw  : m10Trg;
   bool s10b = m10Imm ? s10braw : m10Trgb;
   // H3 — setup extreme for the stop
   int poiNL = MathMin(MathMax(g_bi - g_sx.poiBarL, 0), i_poiBars) + 1;
   int poiNS = MathMin(MathMax(g_bi - g_sx.poiBarS, 0), i_poiBars) + 1;
   double lowTap  = LowestL(poiNL, 0);
   double highTap = HighestH(poiNS, 0);
   double setLoL  = poiConfL ? lowTap  : low;
   double setHiS  = poiConfS ? highTap : high;
   // M74 pre-conditions
   bool m74Up = en_M74 && ft.htfBias != "BEAR" && ((st.bullCHoCH && ft.chochReal) || (st.bullBOS && mv.strong && mv.fvgCount >= 1));
   bool m74Dn = en_M74 && ft.htfBias != "BULL" && ((st.bearCHoCH && ft.chochReal) || (st.bearBOS && mv.strong && mv.fvgCount >= 1));
   double m74X = NA, m74F = NA;
   if(m74Up || m74Dn)
   {
      m74X = LegExt(!m74Up, g_cx.legIdx);
      m74F = LegFvg(m74Up, g_cx.legIdx, close);
   }
   double m74Px = isna(m74F) ? (m74Up ? (m74X + high) * 0.5 : (m74X + low) * 0.5) : m74F;
   int m74Sw = m74Up ? g_cx.sweptLowBar : g_cx.sweptHighBar;
   int m74T  = (m74Sw >= 0 && g_cx.legIdx - m74Sw <= 10 && g_cx.legIdx - m74Sw >= -2) ? 4 : 3;
   string m74Note = "MSS → FVG retrace: " + ((st.bullCHoCH || st.bearCHoCH) ? "real CHoCH" : "strong BOS") + (isna(m74F) ? " · limit at leg 50%" : " · limit at FVG CE") + (m74T == 4 ? " · after a qualified sweep" : "");

   // A — price action
   bool s01  = en_M01 && g_cx.breakDir == 1  && brkWin && brkTouchOk && ft.upWickInc && cd.isBear && cd.bodyRatio >= 0.5 && close < g_cx.breakLvl;
   bool s02  = en_M02 && contBrk && g_cx.breakDir == 1  && brkWin && brkTouchOk && ft.upWickDec && (cd.pinBull || cd.engulfBull);
   bool s01b = en_M01 && g_cx.breakDir == -1 && brkWin && brkTouchOk && ft.dnWickInc && cd.isBull && cd.bodyRatio >= 0.5 && close > g_cx.breakLvl;
   bool s02b = en_M02 && contBrk && g_cx.breakDir == -1 && brkWin && brkTouchOk && ft.dnWickDec && (cd.pinBear || cd.engulfBear);
   // B — pin bars
   bool s05  = en_M05 && contBrk && g_cx.breakDir == 1  && ft.breakAgo == 1 && cd.pinBull;
   bool s05b = en_M05 && contBrk && g_cx.breakDir == -1 && ft.breakAgo == 1 && cd.pinBear;
   double wickL = immMode ? cd.dnWickRatio : g_sx.poiWickL;
   double wickS = immMode ? cd.upWickRatio : g_sx.poiWickS;
   bool s08  = en_M08 && bullTrend && zoneOkBull && trigBull;
   bool s08b = en_M08 && bearTrend && zoneOkBear && trigBear;
   bool s09  = en_M09 && zoneOkBull && trigBull && wickL >= 0.65 && ft.bslAbove >= 2;
   bool s09b = en_M09 && zoneOkBear && trigBear && wickS >= 0.65 && ft.sslBelow >= 2;
   bool s15  = en_M15 && ft.breakPinBull;
   bool s15b = en_M15 && ft.breakPinBear;
   bool s33  = en_M33 && zoneOkBull && ft.zb.flipped && ft.zb.depStrong && ft.zb.arr == 1 && trigBull && bullTrend && ft.htfBias == "BULL";
   bool s33b = en_M33 && zoneOkBear && ft.zs.flipped && ft.zs.depStrong && ft.zs.arr == 1 && trigBear && bearTrend && ft.htfBias == "BEAR";
   bool obBull = zoneOkBull && (ft.zb.kind == "OB" || ft.zb.kind == "BRK");
   bool obBear = zoneOkBear && (ft.zs.kind == "OB" || ft.zs.kind == "BRK");
   bool s36  = en_M36 && obBull && ft.zb.arr == 1 && trigBull;
   bool s36b = en_M36 && obBear && ft.zs.arr == 1 && trigBear;
   bool s37  = en_M37 && obBull && ft.zb.idm && trigBull;
   bool s37b = en_M37 && obBear && ft.zs.idm && trigBear;

   Best bL, bS;
   Bid(bL, s02 && arrOkBull, "M02", 21, "Pin-bar continuation: shrinking upper wicks after breakout + bullish pin → LONG, TP = liquidity above");
   Bid(bL, s01b && arrOkBull, "M01", 21, "Breakout rejection trap (mirror): growing lower wicks then strong close back above");
   Bid(bL, s05, "M05", 21, "Pin bar right after breakout: flipped support held");
   Bid(bL, s08 && arrOkBull && pbOkL && rtOk, "M08", 21, "Trend + support/demand + bullish pin bar");
   Bid(bL, s09 && arrOkBull, "M09", 32, "HIGH QUALITY: strong pin bar at level with >=2 liquidity targets above");
   int m10TierL = (Contains(ft.sweptKindLo, "PD") || Contains(ft.sweptKindLo, "PW") || Contains(ft.sweptKindLo, "SES")) ? 3 : 2;
   int m10TierS = (Contains(ft.sweptKindHi, "PD") || Contains(ft.sweptKindHi, "PW") || Contains(ft.sweptKindHi, "SES")) ? 3 : 2;
   string m10ConfTxt = i_m10Conf == M10_CISD ? "CISD" : "1-bar close above sweep candle";
   Bid(bL, s10, "M10", m10TierL * 10 + 1, "Liquidity SWEEP reversal: swept " + ft.sweptKindLo + ", closed back above" + (m10Imm ? "" : " + confirm (" + m10ConfTxt + ")") + ". SL below sweep low");
   Bid(bL, s15, "M15", 21, "Breakout candle is itself a bullish pin bar (took liquidity below first)");
   Bid(bL, s33 && rtOk, "M33", 32, "Zone flip model: strong breakout → weak retest → refusal, trend + HTF aligned");
   Bid(bL, s36 && pbOkL, "M36", 32, "Weak retracement into valid OB + bullish reversal");
   Bid(bL, s37, "M37", 43, "Inducement block: EQL swept before the OB tap + reversal (highest quality)");

   Bid(bS, s01 && arrOkBear, "M01", 21, "Breakout rejection trap: growing upper wicks after breakout, strong close back below → SHORT");
   Bid(bS, s02b && arrOkBear, "M02", 21, "Pin-bar continuation (mirror): shrinking lower wicks after breakdown → SHORT");
   Bid(bS, s05b, "M05", 21, "Pin bar right after breakdown");
   Bid(bS, s08b && arrOkBear && pbOkS && rtOk, "M08", 21, "Trend + resistance/supply + bearish pin bar");
   Bid(bS, s09b && arrOkBear, "M09", 32, "HIGH QUALITY: strong pin bar at level with >=2 liquidity targets below");
   Bid(bS, s10b, "M10", m10TierS * 10 + 1, "Liquidity SWEEP reversal: swept " + ft.sweptKindHi + ", closed back below" + (m10Imm ? "" : " + confirm (" + m10ConfTxt + ")") + ". SL above sweep high");
   Bid(bS, s15b, "M15", 21, "Breakdown candle is itself a bearish pin bar");
   Bid(bS, s33b && rtOk, "M33", 32, "Zone flip model (bearish)");
   Bid(bS, s36b && pbOkS, "M36", 32, "Weak retracement into valid bearish OB + reversal");
   Bid(bS, s37b, "M37", 43, "Inducement block (bearish): EQH swept before OB tap");

   string warnUp = (ft.runUp && en_M10 && (d_liqAll || ft.runMajor)) ? "RUN — avoid" : "";
   string warnDn = (ft.runDn && en_M10 && (d_liqAll || ft.runMajor)) ? "RUN — avoid" : "";

   // J–R
   bool reactBull  = zoneOkBull || ft.atBullFvg  || (poiConfL && g_sx.poiFvgL);
   bool reactBear  = zoneOkBear || ft.atBearFvg  || (poiConfS && g_sx.poiFvgS);
   bool reactBullF = zoneOkBull || ft.atBullFvgF || (poiConfL && g_sx.poiFvgL);
   bool reactBearF = zoneOkBear || ft.atBearFvgF || (poiConfS && g_sx.poiFvgS);
   bool s39  = en_M39 && zoneOkBull && ft.zb.kind == "RCB" && trigBull;
   bool s39b = en_M39 && zoneOkBear && ft.zs.kind == "RCB" && trigBear;
   bool s40  = en_M40 && zoneOkBull && ft.zb.kind == "RJB" && trigBull;
   bool s40b = en_M40 && zoneOkBear && ft.zs.kind == "RJB" && trigBear;
   bool s41  = en_M41 && Armed(1, g_cx.m41Dir, g_cx.m41Bar)  && reactBullF && trigBull;
   bool s41b = en_M41 && Armed(-1, g_cx.m41Dir, g_cx.m41Bar) && reactBearF && trigBear;
   bool w41  = en_M41 && (g_cx.m41Dir == 9 || g_cx.m41Dir == -9) && g_bi == g_cx.m41Bar;
   bool s42  = en_M42 && zoneOkBull && ft.zb.kind == "OB" && ft.zb.depStrong && ft.zb.fifty && ft.zb.arr == 1 && trigBull;
   bool s42b = en_M42 && zoneOkBear && ft.zs.kind == "OB" && ft.zs.depStrong && ft.zs.fifty && ft.zs.arr == 1 && trigBear;
   bool s45  = en_M45 && ArmedSw(1, g_cx.m45Dir, g_cx.m45Bar)  && zoneOkBull && (ft.zb.kind == "BRK" || ft.zb.kind == "OB") && trigBull;
   bool s45b = en_M45 && ArmedSw(-1, g_cx.m45Dir, g_cx.m45Bar) && zoneOkBear && (ft.zs.kind == "BRK" || ft.zs.kind == "OB") && trigBear;
   bool m45Strong = MathAbs(g_cx.m45Dir) == 2;
   bool s46  = en_M46 && Armed(1, g_cx.m46Dir, g_cx.m46Bar)  && reactBull && (trigBull || (immMode && cd.harami));
   bool s46b = en_M46 && Armed(-1, g_cx.m46Dir, g_cx.m46Bar) && reactBear && (trigBear || (immMode && cd.harami));
   bool s51  = en_M51 && bullTrend && g_cx.lastDepStrong && g_bi - g_cx.lastBOSBar <= 40 && zoneOkBull && trigBull;
   bool s51b = en_M51 && bearTrend && g_cx.lastDepStrong && g_bi - g_cx.lastBOSBar <= 40 && zoneOkBear && trigBear;
   bool w51  = en_M51 && (st.weakBullBOS || (st.bullBOS && !mv.strong));
   bool w51b = en_M51 && (st.weakBearBOS || (st.bearBOS && !mv.strong));
   bool s54  = en_M54 && g_cx.m54Stage == 3  && zoneOkBull && trigBull && (MathAbs(ft.zb.bottom - g_sx.m54Zb) <= atrV || ft.zb.depStrong);
   bool s54b = en_M54 && g_cx.m54StageB == 3 && zoneOkBear && trigBear && (MathAbs(ft.zs.top - g_sx.m54Zs) <= atrV || ft.zs.depStrong);
   if(s54)  g_cx.m54Stage = 0;
   if(s54b) g_cx.m54StageB = 0;
   int m39RankL = (g_cx.chochReal && g_cx.sweptLowBar  >= 0 && g_cx.qmBullAt >= g_cx.sweptLowBar  && g_cx.qmBullAt - g_cx.sweptLowBar  <= 10) ? 43 : 31;
   int m39RankS = (g_cx.chochReal && g_cx.sweptHighBar >= 0 && g_cx.qmBearAt >= g_cx.sweptHighBar && g_cx.qmBearAt - g_cx.sweptHighBar <= 10) ? 43 : 31;
   Bid(bL, s39 && arrOkBull, "M39", m39RankL, "Reclaimed block retest + bullish reversal" + (m39RankL == 43 ? " (sweep → real CHoCH origin)" : ""));
   Bid(bL, s40, "M40", 21, "Rejection block (wick zone) retest + reversal");
   Bid(bL, s41, "M41", 43, "Sweep + FVG confluence: low swept, STRONG move left FVG, retrace reversal");
   Bid(bL, s42, "M42", 43, "High-probability demand: strong departure · 50% tapped · weak arrival" + (ft.zb.nearSwept ? " · ★★ near-miss then sweep (strongest)" : ""));
   Bid(bL, s45, "M45", (m45Strong ? 4 : 3) * 10 + 3, "Qualified sweep → " + (m45Strong ? "CHoCH (reversal, tier 4)" : "BOS (continuation, tier 3)") + " → breaker/OB retest");
   Bid(bL, s46, "M46", 32, "CISD (early reversal) with reliability → zone reaction. SL beyond zone");
   Bid(bL, s51 && pbOkL, "M51", 32, "Smart BOS: aggressive BOS with FVG → OB/support retest");
   Bid(bL, s54, "M54", 43, "Smart S&D trap: demand reject → stop hunt → BOS up → retrace reversal");
   Bid(bS, s39b && arrOkBear, "M39", m39RankS, "Reclaimed block retest + bearish reversal" + (m39RankS == 43 ? " (sweep → real CHoCH origin)" : ""));
   Bid(bS, s40b, "M40", 21, "Rejection block (wick zone) retest + reversal");
   Bid(bS, s41b, "M41", 43, "Sweep + FVG confluence: high swept, STRONG move left FVG, retrace reversal");
   Bid(bS, s42b, "M42", 43, "High-probability supply: strong departure · 50% tapped · weak arrival" + (ft.zs.nearSwept ? " · ★★ near-miss then sweep (strongest)" : ""));
   Bid(bS, s45b, "M45", (m45Strong ? 4 : 3) * 10 + 3, "Qualified sweep → " + (m45Strong ? "CHoCH (reversal, tier 4)" : "BOS (continuation, tier 3)") + " → breaker/OB retest");
   Bid(bS, s46b, "M46", 32, "CISD (early reversal) with reliability → zone reaction. SL beyond zone");
   Bid(bS, s51b && pbOkS, "M51", 32, "Smart BOS (bearish): aggressive BOS with FVG → OB/resistance retest");
   Bid(bS, s54b, "M54", 43, "Smart S&D trap (mirror): supply reject → stop hunt → BOS down → retrace");
   if(warnUp == "") warnUp = (w41 && g_cx.m41Dir == 9)  ? "M41 NO TRADE (no FVG)" : w51  ? "⚠M51 weak BOS — consolidation risk" : "";
   if(warnDn == "") warnDn = (w41 && g_cx.m41Dir == -9) ? "M41 NO TRADE (no FVG)" : w51b ? "⚠M51 weak BOS — consolidation risk" : "";

   // S–AB state machines
   if(st.swingHigh && !isna(g_cx.prevHigh) && MathAbs(g_cx.curHigh - g_cx.prevHigh) <= atrV * i_dtTol && g_cx.curLowIdx > g_cx.prevHighIdx)
   { g_sx.dtDir = -1; g_sx.dtBar = g_bi; g_sx.dtNeck = g_cx.curLow; }
   if(st.swingLow && !isna(g_cx.prevLow) && MathAbs(g_cx.curLow - g_cx.prevLow) <= atrV * i_dtTol && g_cx.curHighIdx > g_cx.prevLowIdx)
   { g_sx.dtDir = 1; g_sx.dtBar = g_bi; g_sx.dtNeck = g_cx.curHigh; }
   if(g_sx.dtDir != 0 && g_bi - g_sx.dtBar > i_armBars * 2) g_sx.dtDir = 0;
   if(ft.fakeBreak || (ft.breakAgo == 2 && !isna(g_cx.breakLvl) && ((g_cx.breakDir == 1 && close < g_cx.breakLvl) || (g_cx.breakDir == -1 && close > g_cx.breakLvl))))
   { g_sx.m62Dir = -g_cx.breakDir; g_sx.m62Bar = g_bi; g_sx.m62Lvl = g_cx.breakLvl; }
   bool tapM62 = g_sx.m62Dir != 0 && g_bi - g_sx.m62Bar >= 1 && g_bi - g_sx.m62Bar <= i_armBars && MathAbs(close - g_sx.m62Lvl) <= tlz;
   // M64 trendline drawing
   if(en_M64)
   {
      if(ft.tlSupValid)
      {
         int x1c = XB(g_sx.tlSx1);
         MoveLine(tlSupLn, x1c, g_sx.tlSy1 + slopeS * (x1c - g_sx.tlSx1), g_bi, tlS, Col(i_cBull, 30), STYLE_SOLID, 2, true);
      }
      else if(tlSupLn != "" && g_sx.tlSBroken) { LineSetRay(tlSupLn, false); LineSetColor(tlSupLn, Col(i_cInv, 60)); }
      if(ft.tlResValid)
      {
         int x1c = XB(g_sx.tlRx1);
         MoveLine(tlResLn, x1c, g_sx.tlRy1 + slopeR * (x1c - g_sx.tlRx1), g_bi, tlR, Col(i_cBear, 30), STYLE_SOLID, 2, true);
      }
      else if(tlResLn != "" && g_sx.tlRBroken) { LineSetRay(tlResLn, false); LineSetColor(tlResLn, Col(i_cInv, 60)); }
   }
   if(ft.htfSweepDn && st.bullCHoCH) { g_sx.m68Dir = 1;  g_sx.m68Bar = g_bi; }
   if(ft.htfSweepUp && st.bearCHoCH) { g_sx.m68Dir = -1; g_sx.m68Bar = g_bi; }
   if(cd.ifcBull && (atBullZone || ft.sweptLow))  { g_sx.ifcDir = 1;  g_sx.ifcBar = g_bi; g_sx.ifcHi = high; g_sx.ifcLo = low; }
   if(cd.ifcBear && (atBearZone || ft.sweptHigh)) { g_sx.ifcDir = -1; g_sx.ifcBar = g_bi; g_sx.ifcHi = high; g_sx.ifcLo = low; }
   if(g_sx.ifcDir != 0 && (g_bi - g_sx.ifcBar > 10 || (g_sx.ifcDir == 1 && close < g_sx.ifcLo) || (g_sx.ifcDir == -1 && close > g_sx.ifcHi))) g_sx.ifcDir = 0;
   if(ft.breakUp || ft.breakDn) { g_sx.m72Cnt = 0; g_sx.m72Wick = 0; g_sx.m72Dir = ft.breakUp ? 1 : -1; }
   if(g_sx.m72Dir != 0 && ft.breakAgo >= 1 && !isna(g_cx.breakLvl))
   {
      bool inBand = g_sx.m72Dir == 1 ? (close >= g_cx.breakLvl && close <= g_cx.breakLvl + atrV * i_consMax) : (close <= g_cx.breakLvl && close >= g_cx.breakLvl - atrV * i_consMax);
      if(inBand)
      {
         g_sx.m72Cnt++;
         g_sx.m72Wick += ((g_sx.m72Dir == 1 && cd.upWickRatio >= 0.4) || (g_sx.m72Dir == -1 && cd.dnWickRatio >= 0.4)) ? 1 : 0;
      }
      else if((g_sx.m72Dir == 1 && close > g_cx.breakLvl + atrV * i_consMax) || (g_sx.m72Dir == -1 && close < g_cx.breakLvl - atrV * i_consMax))
         g_sx.m72Dir = 0;
   }
   bool consolOk = g_sx.m72Dir != 0 && g_sx.m72Cnt >= i_consMin && g_sx.m72Wick * 2 >= g_sx.m72Cnt;
   bool s58b = en_M58 && g_sx.dtDir == -1 && !isna(g_sx.dtNeck) && close < g_sx.dtNeck && C(1) >= g_sx.dtNeck;
   bool s58  = en_M58 && g_sx.dtDir == 1  && !isna(g_sx.dtNeck) && close > g_sx.dtNeck && C(1) <= g_sx.dtNeck;
   bool s62  = en_M62 && tapM62 && g_sx.m62Dir == 1  && revBull;
   bool s62b = en_M62 && tapM62 && g_sx.m62Dir == -1 && revBear;
   bool s68  = en_M68 && Armed(1, g_sx.m68Dir, g_sx.m68Bar)  && reactBull && trigBull;
   bool s68b = en_M68 && Armed(-1, g_sx.m68Dir, g_sx.m68Bar) && reactBear && trigBear;
   bool s69  = en_M69 && g_sx.ifcDir == 1  && g_bi - g_sx.ifcBar >= 1 && close > g_sx.ifcHi;
   bool s69b = en_M69 && g_sx.ifcDir == -1 && g_bi - g_sx.ifcBar >= 1 && close < g_sx.ifcLo;
   bool s70  = en_M70 && zoneOkBull && ft.zb.kind == "QM" && trigBull;
   bool s70b = en_M70 && zoneOkBear && ft.zs.kind == "QM" && trigBear;
   bool s72b = en_M72 && consolOk && g_sx.m72Dir == 1  && close < g_cx.breakLvl && cd.isBear && cd.bodyRatio >= 0.6;
   bool s72  = en_M72 && consolOk && g_sx.m72Dir == -1 && close > g_cx.breakLvl && cd.isBull && cd.bodyRatio >= 0.6;
   if(s69 || s69b) g_sx.ifcDir = 0;
   if(s72 || s72b) g_sx.m72Dir = 0;
   if(s58 || s58b) g_sx.dtDir = 0;
   if(s62 || s62b) g_sx.m62Dir = 0;
   bool s73  = en_M73 && ft.zb.prop && ft.atDemand && ft.zb.fifty && trigBull;
   bool s73b = en_M73 && ft.zs.prop && ft.atSupply && ft.zs.fifty && trigBear;
   Bid(bL, s58, "M58", 21, "Double bottom: neckline broken on close");
   Bid(bL, s62, "M62", 21, "Fakeout trap: break failed within 1–2 bars → level tap + reversal against the break");
   Bid(bL, s68, "M68", 43, "HTF sweep of low + LTF CHoCH up → zone/FVG reaction → LONG (SL beyond FVG, TP nearest swing)");
   Bid(bL, s69, "M69", 21, "IFC candle at zone: close above IFC high → BUY (TP just below nearest swing high)");
   Bid(bL, s70, "M70", 22, "Quasimodo left-leg demand + bullish candle (TP1 = CHoCH high)");
   Bid(bL, s72, "M72", 21, "Operator trap (mirror): breakdown → consolidation under level with lower wicks → strong bullish close back above");
   Bid(bL, s73, "M73", 33, "Propulsion Block: zone made a strong move, was retraced into, departed again with an imbalance — now tapped at 50% + bullish reversal");
   Bid(bL, m74Up, "M74", m74T * 10 + 2, m74Note);
   Bid(bS, s58b, "M58", 21, "Double top: neckline broken on close");
   Bid(bS, s62b, "M62", 21, "Fakeout trap: failed breakout → level tap + reversal SHORT");
   Bid(bS, s68b, "M68", 43, "HTF sweep of high + LTF CHoCH down → zone/FVG reaction → SHORT");
   Bid(bS, s69b, "M69", 21, "IFC candle at zone: close below IFC low → SELL");
   Bid(bS, s70b, "M70", 22, "Quasimodo left-leg supply + bearish candle");
   Bid(bS, s72b, "M72", 21, "Operator trap: breakout → consolidation above level with upper wicks → strong bearish close back below");
   Bid(bS, s73b, "M73", 33, "Propulsion Block: zone made a strong move, was retraced into, departed again with an imbalance — now tapped at 50% + bearish reversal");
   Bid(bS, m74Dn, "M74", m74T * 10 + 2, m74Note);

   // ── L7 signal build ──
   Sig sigL, sigS;
   int rejL = 0, rejS = 0;
   bool contL = IsCont(bL.n), contS = IsCont(bS.n);
   bool pdBlkL = i_pdCont && ((pdIn && !ft.pdBeyond && ft.pdPct > i_pdDeep) || (!isna(ft.htfPdPct) && ft.htfPdPct > i_pdDeep && ft.inPremium));
   bool pdBlkS = i_pdCont && ((pdIn && !ft.pdBeyond && ft.pdPct < 1.0 - i_pdDeep) || (!isna(ft.htfPdPct) && ft.htfPdPct < 1.0 - i_pdDeep && ft.inDiscount));
   bool htfCtrL = ft.htfBias == "BEAR";
   bool htfCtrS = ft.htfBias == "BULL";
   bool gBlkL = ft.gateUp == 1 && contL && (htfCtrL || !i_ltfPb);
   bool gBlkS = ft.gateDn == 1 && contS && (htfCtrS || !i_ltfPb);
   rejL = bL.n == "" ? 1 : (ft.gateUp == 0 || gBlkL || (pdBlkL && contL)) ? 2 : !ft.sbSessOk ? 3 : 0;
   if(rejL == 0)
   {
      bool isM74L = bL.n == "M74";
      sigL = MakeSig(isM74L ? st.trend : gateTrend, bL.n, bL.s / 10, bL.t, true, atrV, isM74L ? m74X : setLoL, isM74L ? m74Px : NA);
      if(sigL.name == "") rejL = 4;
      if(ft.gateUp == 1) { sigL.score--; sigL.note += htfCtrL ? " · ⚠vs HTF" : " · ⚠ LTF counter (pullback)"; }
      if(isM74L) sigL.score += (ft.pdPct > i_pdDeep ? 2 : ft.pdPct >= 0.5 ? 1 : 0) + ((ft.gateUp == 1 && !htfCtrL) ? 1 : 0) + (isna(m74F) ? 0 : 1);
      if(!(ft.zb.kind != "" || ft.atBullFvg || ft.atTLsup)) { sigL.note += " · INCOMPLETE (no POI)"; sigL.score--; }
      if(sigL.score < i_minScore) { if(rejL == 0) rejL = 5; sigL.Reset(); }
   }
   rejS = bS.n == "" ? 1 : (ft.gateDn == 0 || gBlkS || (pdBlkS && contS)) ? 2 : !ft.sbSessOk ? 3 : 0;
   if(rejS == 0)
   {
      bool isM74S = bS.n == "M74";
      sigS = MakeSig(isM74S ? st.trend : gateTrend, bS.n, bS.s / 10, bS.t, false, atrV, isM74S ? m74X : setHiS, isM74S ? m74Px : NA);
      if(sigS.name == "") rejS = 4;
      if(ft.gateDn == 1) { sigS.score--; sigS.note += htfCtrS ? " · ⚠vs HTF" : " · ⚠ LTF counter (pullback)"; }
      if(isM74S) sigS.score += (ft.pdPct < 1.0 - i_pdDeep ? 2 : ft.pdPct <= 0.5 ? 1 : 0) + ((ft.gateDn == 1 && !htfCtrS) ? 1 : 0) + (isna(m74F) ? 0 : 1);
      if(!(ft.zs.kind != "" || ft.atBearFvg || ft.atTLres)) { sigS.note += " · INCOMPLETE (no POI)"; sigS.score--; }
      if(sigS.score < i_minScore) { if(rejS == 0) rejS = 5; sigS.Reset(); }
   }

   // one signal at a time
   bool okL = sigL.name != "";
   bool okS = sigS.name != "";
   if(okL && okS)
   {
      if(sigL.score >= sigS.score) { sigS.Reset(); okS = false; rejS = 6; }
      else                         { sigL.Reset(); okL = false; rejL = 6; }
   }
   bool gapOk = g_bi - sigBar >= i_sigGap;
   if(okL && !gapOk && !(sigDir == -1 && sigL.score >= sigScore + 2)) { sigL.Reset(); okL = false; rejL = 7; }
   if(okS && !gapOk && !(sigDir == 1  && sigS.score >= sigScore + 2)) { sigS.Reset(); okS = false; rejS = 7; }
   string identL = okL ? Ident(sigL) : "";
   string identS = okS ? Ident(sigS) : "";
   bool identExpired = g_bi - lastIdentBar >= i_idBars;
   if(okL && !identExpired && identL == lastIdent) { sigL.Reset(); okL = false; rejL = 8; }
   if(okS && !identExpired && identS == lastIdent) { sigS.Reset(); okS = false; rejS = 8; }

   // v8.5.0 W1 · RETRACE entry
   bool retMode = i_entryPx == EP_RETRACE;
   bool retNow  = retMode || (i_autoRet > 0 && cd.rng >= atrV * i_autoRet);
   double mnR   = MathMax(_Point * i_minRiskT, atrV * i_minRiskA);
   bool fillL = false, fillS = false, stpL = false, stpS = false;
   if(hasRetL)
   {
      if(g_bi - retBarL > (retNameL == "M74" ? i_m74Bars : i_retBars)) { hasRetL = false; RetDone(retLbL, "⏳ " + retNameL + " LONG expired"); }
      else if(low <= retL.sl) { stpL = true; hasRetL = false; RetDone(retLbL, "⏳ " + retNameL + " LONG → ✖ SL"); }
      else if(low <= retL.entry && !okL)
      {
         RetDone(retLbL, "⏳ " + retNameL + " LONG → filled");
         sigL = retL; okL = true; fillL = true; rejL = 0; identL = Ident(sigL); hasRetL = false;
      }
   }
   if(hasRetS)
   {
      if(g_bi - retBarS > (retNameS == "M74" ? i_m74Bars : i_retBars)) { hasRetS = false; RetDone(retLbS, "⏳ " + retNameS + " SHORT expired"); }
      else if(high >= retS.sl) { stpS = true; hasRetS = false; RetDone(retLbS, "⏳ " + retNameS + " SHORT → ✖ SL"); }
      else if(high >= retS.entry && !okS)
      {
         RetDone(retLbS, "⏳ " + retNameS + " SHORT → filled");
         sigS = retS; okS = true; fillS = true; rejS = 0; identS = Ident(sigS); hasRetS = false;
      }
   }
   string stpNameL = retNameL, stpNameS = retNameS;
   if((retNow || sigL.name == "M74") && okL && !fillL)
   {
      double pxL = sigL.name == "M74" ? sigL.entry : ft.newBullFvg ? low : (setLoL + high) * 0.5;
      double rkL = pxL - sigL.sl;
      if((pxL < sigL.entry || sigL.name == "M74") && rkL > 0)
      {
         rkL = MathMax(rkL, mnR);
         sigL.sl = pxL - rkL; sigL.entry = pxL; sigL.rr = MathAbs(sigL.tp1 - pxL) / rkL;
         sigL.note = "RETRACE limit · " + sigL.note;
         if(hasRetL) RetDone(retLbL, "⏳ " + retNameL + " LONG replaced");
         retL = sigL; hasRetL = true; retBarL = g_bi; retPxL = pxL; retNameL = sigL.name;
         sigL.Reset(); okL = false; rejL = 9;
      }
   }
   if((retNow || sigS.name == "M74") && okS && !fillS)
   {
      double pxS = sigS.name == "M74" ? sigS.entry : ft.newBearFvg ? high : (setHiS + low) * 0.5;
      double rkS = sigS.sl - pxS;
      if((pxS > sigS.entry || sigS.name == "M74") && rkS > 0)
      {
         rkS = MathMax(rkS, mnR);
         sigS.sl = pxS + rkS; sigS.entry = pxS; sigS.rr = MathAbs(sigS.tp1 - pxS) / rkS;
         sigS.note = "RETRACE limit · " + sigS.note;
         if(hasRetS) RetDone(retLbS, "⏳ " + retNameS + " SHORT replaced");
         retS = sigS; hasRetS = true; retBarS = g_bi; retPxS = pxS; retNameS = sigS.name;
         sigS.Reset(); okS = false; rejS = 9;
      }
   }
   bool armL = rejL == 9;
   bool armS = rejS == 9;
   if(okL || okS)
   {
      sigBar = g_bi; sigDir = okL ? 1 : -1; sigScore = okL ? sigL.score : sigS.score;
      lastIdent = okL ? identL : identS; lastIdentBar = g_bi;
   }
   if(i_tradeLn)
   {
      if(sigL.name != "") TradeLines(sigL, i_tradeBars);
      if(sigS.name != "") TradeLines(sigS, i_tradeBars);
   }

   // ── labels: priority pick per side ──
   double yUp = low  - atrV * i_off;
   double yDn = high + atrV * i_off;
   bool hasL = sigL.name != "" && sigL.dir == 1;
   bool hasS = sigS.name != "" && sigS.dir == -1;
   string sigTipL = TpTip(sigL), sigTipS = TpTip(sigS);
   string sigTxtL = (sigL.score >= i_gradeAp ? "▲▲ " : sigL.score >= i_gradeA ? "▲ " : "· ") + sigL.name + " " + GradeTxt(sigL.score) + IntegerToString(sigL.score) + " · " + DoubleToString(sigL.rr, 1) + "R";
   string sigTxtS = (sigS.score >= i_gradeAp ? "▼▼ " : sigS.score >= i_gradeA ? "▼ " : "· ") + sigS.name + " " + GradeTxt(sigS.score) + IntegerToString(sigS.score) + " · " + DoubleToString(sigS.rr, 1) + "R";
   string chochBase = ft.chochReal ? "CHoCH" : "CHoCH?";
   string chochUpX  = (g_cx.sweptLowBar  >= 0 && g_bi - g_cx.sweptLowBar  <= 10) ? "✕" : "";
   string chochDnX  = (g_cx.sweptHighBar >= 0 && g_bi - g_cx.sweptHighBar <= 10) ? "✕" : "";
   string swKUp = ft.sweptKindLo; StringReplace(swKUp, "POOL·", ""); StringReplace(swKUp, "·ext", "");
   string swKDn = ft.sweptKindHi; StringReplace(swKDn, "POOL·", ""); StringReplace(swKDn, "·ext", "");
   bool cisdUpOk = st.cisdBull && (d_cisdAll || preTrend != "BULLISH");
   bool cisdDnOk = st.cisdBear && (d_cisdAll || preTrend != "BEARISH");
   bool cisdHP   = ft.cisdRel >= 2;
   string chochTip = ft.chochReal ? "REAL CHoCH — imbalance inside the move (M30). Retracement tradable." : "FAKE CHoCH — no FVG in the move (M30). Do not trade.";
   string armTip = " bars — the signal prints when it fills (W1 / E-4 / E-5)";

   Tag xU, xD;
   AddTag(xU, 1, d_sig && hasL, sigTxtL, sigTipL, ft.gateUp == 1 ? i_cInv : i_cBull);
   AddTag(xU, 1, d_sig && armL, "⏳▲ " + retNameL + " LONG @ " + fmtPx(retPxL), "RETRACE: limit armed for " + IntegerToString(retNameL == "M74" ? i_m74Bars : i_retBars) + armTip, i_cHtf);
   AddTag(xU, 1, d_sig && stpL, "✖ " + stpNameL + " filled → SL", "R-1: the limit filled and the stop was hit on this bar — a LOSS, shown so the chart does not hide it", i_cInv);
   AddTag(xU, 2, d_struct && tierKey && st.bullCHoCH && (tierAll || ft.chochReal), chochBase + chochUpX + "▲", chochTip, ft.chochReal ? i_cBull : i_cInv);
   AddTag(xU, 3, d_struct && tierKey && (st.bullBOS || (d_weakBos && st.weakBullBOS)),
          ft.dispBull ? "BOS▲ ·" + IntegerToString(mv.fvgCount) + "FVG" : st.weakBullBOS ? "BOS▲ weak" : "BOS▲",
          ft.dispBull ? "Bullish BOS with displacement (STRONG)" : st.weakBullBOS ? "Bullish break without displacement — pending follow-through, no structure change" : "Bullish BOS (displaced candle, no FVG in the leg)",
          ft.dispBull ? i_cBull : i_cInv);
   AddTag(xU, 3, d_struct && tierAll && st.internalBullBOS, "iBOS▲", "Internal break: a lower high closed through inside a bearish trend — no structure change (S4)", i_cInv);
   AddTag(xU, 4, d_struct && (tierAll || (tierKey && cisdHP)) && cisdUpOk, "CISD▲" + (cisdHP ? "★" : ""), "Bullish CISD: close above the open of the down-series that made the low, after a sweep — early reversal", i_cBull);
   AddTag(xU, 5, d_liqEvt && tierKey && ft.sweptLow && (d_liqAll || ft.sweptMajor), "SWEEP✕ " + swKUp, "Liquidity sweep of " + ft.sweptKindLo + " — reversal context", i_cBull);
   AddTag(xU, 6, ft.evtUp != "" && (d_obDiag || !StartsWith(ft.evtUp, "T")) && (tierAll || StartsWith(ft.evtUp, "BRK")), ft.evtUp, ft.tipUp,
          StartsWith(ft.evtUp, "BRK") ? i_cBrk : StartsWith(ft.evtUp, "T") ? i_cInv : i_cBull);
   AddTag(xU, 7, d_htfEvt && tierKey && newHtf && ft.htfSweepDn && g_cx.hBarCount == g_cx.sweepDnAt, "HTF SWEEP↓", "HTF candle swept below the last HTF swing low and closed back", i_cBull);
   AddTag(xU, 8, d_htfEvt && tierKey && newHtf && ft.htfManipBull, "HTF MANIP▲", "HTF manipulative candle — trade its O/H/L/C levels", i_cBull);
   AddTag(xU, 9, tierAll && warnUp != "", warnUp, "Warning marker — not a trade", i_cInv);
   AddTag(xU, 11, d_pb && st.pbValidUp, "PB✓", "Valid bullish pullback confirmed (§3.5)", i_cBull);
   AddTag(xU, 12, d_candle && (cd.pinBull || cd.ifcBull || cd.manipBull || cd.engulfBull), cd.ifcBull ? "IFC▲" : cd.manipBull ? "MAN▲" : cd.pinBull ? "PIN▲" : "ENG▲", "Candle pattern (L0)", i_cBull);
   if(d_sig && armL && xU.t != "" && StartsWith(xU.t, "⏳")) xU.arm = true;

   AddTag(xD, 1, d_sig && hasS, sigTxtS, sigTipS, ft.gateDn == 1 ? i_cInv : i_cBear);
   AddTag(xD, 1, d_sig && armS, "⏳▼ " + retNameS + " SHORT @ " + fmtPx(retPxS), "RETRACE: limit armed for " + IntegerToString(retNameS == "M74" ? i_m74Bars : i_retBars) + armTip, i_cHtf);
   AddTag(xD, 1, d_sig && stpS, "✖ " + stpNameS + " filled → SL", "R-1: the limit filled and the stop was hit on this bar — a LOSS, shown so the chart does not hide it", i_cInv);
   AddTag(xD, 2, d_struct && tierKey && st.bearCHoCH && (tierAll || ft.chochReal), chochBase + chochDnX + "▼", chochTip, ft.chochReal ? i_cBear : i_cInv);
   AddTag(xD, 3, d_struct && tierKey && (st.bearBOS || (d_weakBos && st.weakBearBOS)),
          ft.dispBear ? "BOS▼ ·" + IntegerToString(mv.fvgCount) + "FVG" : st.weakBearBOS ? "BOS▼ weak" : "BOS▼",
          ft.dispBear ? "Bearish BOS with displacement (STRONG)" : st.weakBearBOS ? "Bearish break without displacement — pending follow-through, no structure change" : "Bearish BOS (displaced candle, no FVG in the leg)",
          ft.dispBear ? i_cBear : i_cInv);
   AddTag(xD, 3, d_struct && tierAll && st.internalBearBOS, "iBOS▼", "Internal break: a higher low closed through inside a bullish trend — no structure change (S4)", i_cInv);
   AddTag(xD, 4, d_struct && (tierAll || (tierKey && cisdHP)) && cisdDnOk, "CISD▼" + (cisdHP ? "★" : ""), "Bearish CISD: close below the open of the up-series that made the high, after a sweep — early reversal", i_cBear);
   AddTag(xD, 5, d_liqEvt && tierKey && ft.sweptHigh && (d_liqAll || ft.sweptMajor), "SWEEP✕ " + swKDn, "Liquidity sweep of " + ft.sweptKindHi + " — reversal context", i_cBear);
   AddTag(xD, 6, d_struct && tierAll && (st.bullSweep || st.bearSweep) && !ft.sweptHigh && !ft.sweptLow, "✖SWEEP", "Invalid BOS — wick beyond swing, close back (buyers/sellers weakening)", i_cInv);
   AddTag(xD, 7, ft.evtDn != "" && (d_obDiag || !StartsWith(ft.evtDn, "T")) && (tierAll || StartsWith(ft.evtDn, "BRK")), ft.evtDn, ft.tipDn,
          StartsWith(ft.evtDn, "BRK") ? i_cBrk : StartsWith(ft.evtDn, "T") ? i_cInv : i_cBear);
   AddTag(xD, 8, d_htfEvt && tierKey && newHtf && ft.htfSweepUp && g_cx.hBarCount == g_cx.sweepUpAt, "HTF SWEEP↑", "HTF candle swept above the last HTF swing high and closed back", i_cBear);
   AddTag(xD, 9, d_htfEvt && tierKey && newHtf && ft.htfManipBear, "HTF MANIP▼", "HTF manipulative candle — trade its O/H/L/C levels", i_cBear);
   AddTag(xD, 10, tierAll && warnDn != "", warnDn, "Warning marker — not a trade", i_cInv);
   AddTag(xD, 12, d_pb && st.pbValidDn, "PB✓", "Valid bearish pullback confirmed (§3.5)", i_cBear);
   AddTag(xD, 13, d_candle && (cd.pinBear || cd.ifcBear || cd.manipBear || cd.engulfBear || cd.starBear), cd.ifcBear ? "IFC▼" : cd.manipBear ? "MAN▼" : cd.starBear ? "SS" : cd.pinBear ? "PIN▼" : "ENG▼", "Candle pattern (L0)", i_cBear);
   if(d_sig && armS && xD.t != "" && StartsWith(xD.t, "⏳")) xD.arm = true;

   int stackWin = i_minGap * 2;
   bool priUp = xU.r >= 1 && xU.r <= 5;
   bool priDn = xD.r >= 1 && xD.r <= 5;
   bool apL = hasL && sigL.score >= i_gradeAp && (lastUp < 0 || g_bi - lastUp >= 2);
   bool apS = hasS && sigS.score >= i_gradeAp && (lastDn < 0 || g_bi - lastDn >= 2);
   if(xU.t != "" && (lastUp < 0 || g_bi - lastUp >= i_minGap || apL || priUp))
   {
      upStack = (lastUp >= 0 && g_bi - lastUp <= stackWin) ? MathMin(upStack + 1, 4) : MathMax(upStack - 1, 0);
      string nm = Lbl(true, yUp - atrV * i_off * 2.0 * upStack, xU.t, xU.p, xU.c);
      lastUp = g_bi;
      if(xU.arm) retLbL = nm;
   }
   if(xD.t != "" && (lastDn < 0 || g_bi - lastDn >= i_minGap || apS || priDn))
   {
      dnStack = (lastDn >= 0 && g_bi - lastDn <= stackWin) ? MathMin(dnStack + 1, 4) : MathMax(dnStack - 1, 0);
      string nm = Lbl(false, yDn + atrV * i_off * 2.0 * dnStack, xD.t, xD.p, xD.c);
      lastDn = g_bi;
      if(xD.arm) retLbS = nm;
   }

   // §11.1 structure lines
   if(d_struct)
   {
      if((st.bullBOS || st.weakBullBOS || st.internalBullBOS) && !isna(preHigh))
         EvLine(preHighIdx, preHigh, Col(st.bullBOS ? i_cBull : i_cInv, 20), st.bullBOS ? STYLE_SOLID : STYLE_DOT);
      if((st.bearBOS || st.weakBearBOS || st.internalBearBOS) && !isna(preLow))
         EvLine(preLowIdx, preLow, Col(st.bearBOS ? i_cBear : i_cInv, 20), st.bearBOS ? STYLE_SOLID : STYLE_DOT);
      if(st.bullSweep && !isna(preHigh)) EvLine(preHighIdx, preHigh, Col(i_cInv, 30), STYLE_DASH);
      if(st.bearSweep && !isna(preLow))  EvLine(preLowIdx, preLow, Col(i_cInv, 30), STYLE_DASH);
      if(st.bullCHoCH && !isna(st.chLvl)) EvLine(st.chIdx, st.chLvl, Col(ft.chochReal ? i_cBull : i_cInv, 10), ft.chochReal ? STYLE_SOLID : STYLE_DASH);
      if(st.bearCHoCH && !isna(st.chLvl)) EvLine(st.chIdx, st.chLvl, Col(ft.chochReal ? i_cBear : i_cInv, 10), ft.chochReal ? STYLE_SOLID : STYLE_DASH);
      if(st.cisdBear && !isna(g_sx.cisdUpRef)) EvLine(MathMax(g_sx.cisdUpRefBar, g_bi - 30), g_sx.cisdUpRef, Col(i_cBear, 40), STYLE_DOT);
      if(st.cisdBull && !isna(g_sx.cisdDnRef)) EvLine(MathMax(g_sx.cisdDnRefBar, g_bi - 30), g_sx.cisdDnRef, Col(i_cBull, 40), STYLE_DOT);
      if(!isna(g_cx.majorHigh)) MoveLine(hiLine, XB(g_cx.majorHighIdx), g_cx.majorHigh, g_bi, g_cx.majorHigh, Col(i_cBear, 50), STYLE_DASH, 1, false);
      if(!isna(g_cx.majorLow))  MoveLine(loLine, XB(g_cx.majorLowIdx),  g_cx.majorLow,  g_bi, g_cx.majorLow,  Col(i_cBull, 50), STYLE_DASH, 1, false);
   }
   // HTF candle O/H/L/C levels
   if(d_htf && newHtf && !isna(hC1))
   {
      color cc = Col(i_cHtf, i_lineT);
      SPush(hLines, LineNew(g_bi, hH1, g_bi + 1, hH1, cc, STYLE_SOLID, 1, true));
      SPush(hLines, LineNew(g_bi, hL1, g_bi + 1, hL1, cc, STYLE_SOLID, 1, true));
      SPush(hLines, LineNew(g_bi, hO1, g_bi + 1, hO1, cc, STYLE_DOT,   1, true));
      SPush(hLines, LineNew(g_bi, hC1, g_bi + 1, hC1, cc, STYLE_DASH,  1, true));
      int nh = ArraySize(hLines);
      if(nh > 4)
         for(int j = 0; j <= nh - 5; j++) { LineSetRay(hLines[j], false); LineSetX2(hLines[j], g_bi); }
      while(ArraySize(hLines) > i_cLook * 4) LineDel(SShift(hLines));
   }
   // ── alerts (newest closed bar, real time only) ──
   if(hasL) Notify(AlertMsg(sigL, ft.htfBias));
   if(hasS) Notify(AlertMsg(sigS, ft.htfBias));
   if(armL && hasRetL) Notify(_Symbol + " LIMIT " + retNameL + " LONG @ " + fmtPx(retPxL) + " | SL " + fmtPx(retL.sl) + " | TP1 " + fmtPx(retL.tp1));
   if(armS && hasRetS) Notify(_Symbol + " LIMIT " + retNameS + " SHORT @ " + fmtPx(retPxS) + " | SL " + fmtPx(retS.sl) + " | TP1 " + fmtPx(retS.tp1));
   if(stpL || stpS) Notify(_Symbol + " x " + (stpL ? stpNameL + " LONG" : stpNameS + " SHORT") + " limit filled → SL (loss)");
   if(i_alertEvt)
   {
      if(st.bullBOS || st.bearBOS) Notify(_Symbol + " SMC Suite: Break of Structure " + (st.bullBOS ? "UP" : "DOWN"));
      if((st.bullCHoCH || st.bearCHoCH) && ft.chochReal) Notify(_Symbol + " SMC Suite: real CHoCH " + (st.bullCHoCH ? "UP" : "DOWN"));
      if(st.cisdBull || st.cisdBear) Notify(_Symbol + " SMC Suite: CISD " + (st.cisdBull ? "UP" : "DOWN"));
      if(ft.sweptHigh || ft.sweptLow) Notify(_Symbol + " SMC Suite: liquidity sweep " + ft.sweptKind);
      if(ft.newObHp) Notify(_Symbol + " SMC Suite: new HP order block");
      if(ft.newProp) Notify(_Symbol + " SMC Suite: propulsion block");
      if(ft.enteredOb50) Notify(_Symbol + " SMC Suite: OB 50% tapped");
   }

   // ── data window ──
   B0[i]  = sigL.score;
   B1[i]  = sigS.score;
   B2[i]  = ArraySize(g_zones);
   B3[i]  = ArraySize(g_lv);
   B4[i]  = ft.brkTouches;
   B5[i]  = ft.cisdRel;
   B6[i]  = ft.zb.depStrong ? 1 : ft.zs.depStrong ? -1 : 0;
   B7[i]  = ft.pdPct;
   B8[i]  = ft.dispScore;
   B9[i]  = st.internalBullBOS ? 1 : st.internalBearBOS ? -1 : 0;
   B10[i] = st.weakBullBOS ? 1 : st.weakBearBOS ? -1 : 0;
   B11[i] = rejL * 10 + rejS;
   B12[i] = ft.zb.arr + ft.zs.arr * 10;
   B13[i] = isna(ft.htfPdPct) ? EMPTY_VALUE : ft.htfPdPct;

   if(i < ArraySize(g_bias)) g_bias[i] = ft.htfBias == "BULL" ? 1 : ft.htfBias == "BEAR" ? -1 : 0;
   g_sigL = sigL; g_sigS = sigS; g_hasL = hasL; g_hasS = hasS;
}

//+------------------------------------------------------------------+
//| §11.2 INFO PANEL / LEGEND (screen objects)                       |
//+------------------------------------------------------------------+
void ScrLabel(const string n, const ENUM_BASE_CORNER corner, const int x, const int y, const string txt, const color c, const int fs)
{
   if(ObjectFind(0, n) < 0)
   {
      ObjectCreate(0, n, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, n, OBJPROP_CORNER, corner);
      ObjectSetInteger(0, n, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
      ObjectSetString(0, n, OBJPROP_FONT, i_font);
   }
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, fs);
   ObjectSetInteger(0, n, OBJPROP_COLOR, c);
   ObjectSetString(0, n, OBJPROP_TEXT, txt == "" ? " " : txt);
}
void ScrRect(const string n, const ENUM_BASE_CORNER corner, const int x, const int y, const int w, const int h, const color bg, const color bd)
{
   if(ObjectFind(0, n) < 0)
   {
      ObjectCreate(0, n, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, n, OBJPROP_CORNER, corner);
      ObjectSetInteger(0, n, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, n, OBJPROP_BACK, false);
   }
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_COLOR, bd);
}
int TxtW(const string s, const int fs)
{
   TextSetFont(i_font, -fs * 10);
   uint w = 0, h = 0;
   TextGetSize(s, w, h);
   return (int)w;
}
int TxtH(const int fs)
{
   TextSetFont(i_font, -fs * 10);
   uint w = 0, h = 0;
   TextGetSize("Ag", w, h);
   return (int)h;
}
color CardCol()   // table background: the chart background lifted (dark theme) or darkened (light theme) a little
{
   int r = (int)(g_bgCol & 0xFF), g = (int)((g_bgCol >> 8) & 0xFF), b = (int)((g_bgCol >> 16) & 0xFF);
   bool dark = (r * 299 + g * 587 + b * 114) / 1000 < 128;
   return dark ? Col(clrWhite, 90) : Col(clrBlack, 94);
}
// two-column table (Pine table.new + table.cell) in any chart corner.
// nb / vb = clrNONE -> card colour. tw / th = table size in pixels.
void Table(const string id, const ENUM_BASE_CORNER cn, const int rows, string &nm[], string &vl[], color &nc[], color &vc[],
           color &nb[], color &vb[], const int fs, int &tw, int &th)
{
   bool right = cn == CORNER_RIGHT_LOWER || cn == CORNER_RIGHT_UPPER;
   bool lower = cn == CORNER_RIGHT_LOWER || cn == CORNER_LEFT_LOWER;
   int pad = 6, gap = 1, mg = 8;
   int wN = 0, wV = 0;
   for(int r = 0; r < rows; r++) { wN = MathMax(wN, TxtW(nm[r], fs)); wV = MathMax(wV, TxtW(vl[r], fs)); }
   wN += 2 * pad;
   wV += 2 * pad;
   int lh = TxtH(fs) + 6;
   tw = wN + wV + 3 * gap;
   th = rows * (lh + gap) + gap;
   color card = CardCol(), grid = Col(i_cNeut, 60);
   // table-space (left, top) -> corner distances of an object's upper-left point
   #define TX(lx) (right ? mg + tw - (lx) : mg + (lx))
   #define TY(ty) (lower ? mg + th - (ty) : mg + (ty))
   ScrRect(PFX + id + "_bg", cn, TX(0), TY(0), tw, th, grid, grid);
   int lN = gap, lV = gap + wN + gap;
   for(int r = 0; r < rows; r++)
   {
      int top = gap + r * (lh + gap);
      color bN = nb[r] == clrNONE ? card : nb[r];
      color bV = vb[r] == clrNONE ? card : vb[r];
      ScrRect(PFX + id + "_nb" + IntegerToString(r), cn, TX(lN), TY(top), wN, lh, bN, bN);
      ScrRect(PFX + id + "_vb" + IntegerToString(r), cn, TX(lV), TY(top), wV, lh, bV, bV);
      ScrLabel(PFX + id + "_n" + IntegerToString(r), cn, TX(lN + pad), TY(top + 3), nm[r], nc[r], fs);
      ScrLabel(PFX + id + "_v" + IntegerToString(r), cn, TX(lV + pad), TY(top + 3), vl[r], vc[r], fs);
   }
   #undef TX
   #undef TY
}
ENUM_BASE_CORNER PanelCorner()
{
   return i_panelPos == PP_TR ? CORNER_RIGHT_UPPER : i_panelPos == PP_BL ? CORNER_LEFT_LOWER : i_panelPos == PP_TL ? CORNER_LEFT_UPPER : CORNER_RIGHT_LOWER;
}

void Panel()
{
   const int rows = 16;
   string name[16], val[16];
   color  nc[16], vc[16], nb[16], vb[16];
   color  lab = Col(i_cNeut, 60);
   for(int r = 0; r < rows; r++) { nc[r] = i_cTxt; nb[r] = lab; vc[r] = g_fgCol; vb[r] = clrNONE; }

   double close = gC[g_lastDone >= 0 ? g_lastDone : 0];
   color tcol = st.trend == "BULLISH" ? i_cBull : st.trend == "BEARISH" ? i_cBear : i_cNeut;
   color hcol = ft.htfBias == "BULL" ? i_cBull : ft.htfBias == "BEAR" ? i_cBear : i_cNeut;
   bool mism = (st.trend == "BULLISH" && ft.htfBias == "BEAR") || (st.trend == "BEARISH" && ft.htfBias == "BULL");
   double nBSL = NearestLiq(true, close), nSSL = NearestLiq(false, close);
   Sig bestSig;
   if(g_hasL && (!g_hasS || g_sigL.score >= g_sigS.score)) bestSig = g_sigL; else bestSig = g_sigS;
   bool isL = bestSig.name != "" ? bestSig.dir == 1 : ft.htfBias != "BEAR";
   bool fA = (isL && ft.htfBias == "BULL") || (!isL && ft.htfBias == "BEAR");
   bool fB = (isL && st.trend == "BULLISH") || (!isL && st.trend == "BEARISH");
   ZS zz; if(isL) zz = ft.zb; else zz = ft.zs;
   bool fC = zz.depStrong && zz.arr == 1;
   bool fD = (isL && ft.bslAbove >= 1) || (!isL && ft.sslBelow >= 1);
   string chk = (fA ? "✔" : "✘") + (fB ? "✔" : "✘") + (fC ? "✔" : "✘") + (fD ? "✔" : "✘");

   name[0] = "Chart / HTF";   val[0] = TfName((ENUM_TIMEFRAMES)Period()) + " → " + g_htfName;
   name[1] = "LTF structure"; val[1] = st.trend; vb[1] = Col(tcol, 40); vc[1] = i_cTxt;
   name[2] = "HTF bias";      val[2] = ft.htfBias + (mism ? " ⚠" : ""); vb[2] = Col(hcol, 40); vc[2] = i_cTxt;
   name[3] = "Regime";        val[3] = st.trend + (ft.inRange ? " · range" : "");
   name[4] = "Last event";    val[4] = g_cx.lastEvt + (g_cx.lastEvtBar >= 0 ? " · " + IntegerToString(g_lastDone - g_cx.lastEvtBar) + "b ago" : "");
   name[5] = "Move phase";    val[5] = st.movePhase;
   string zbT = ft.zb.kind == "" ? "" : "Bull " + (ft.zb.kind == "SR" ? (ft.zb.kl >= 4 ? "KL★" : "KL") : ft.zb.kind) + (ft.zb.pend ? " ?" : "") +
                (ft.zb.touches <= 1 ? " (fresh)" : " (×" + IntegerToString(ft.zb.touches) + ")") + (ft.zb.sweepReq ? " ⚠SWEEP REQ" : "");
   string zsT = ft.zs.kind == "" ? "" : "Bear " + (ft.zs.kind == "SR" ? (ft.zs.kl >= 4 ? "KL★" : "KL") : ft.zs.kind) + (ft.zs.pend ? " ?" : "") +
                (ft.zs.touches <= 1 ? " (fresh)" : " (×" + IntegerToString(ft.zs.touches) + ")") + (ft.zs.sweepReq ? " ⚠SWEEP REQ" : "");
   name[6] = "Active zone";   val[6] = (zbT == "" && zsT == "") ? "—" : zbT + ((zbT != "" && zsT != "") ? " · " : "") + zsT;
   int arrV = ft.zb.kind != "" ? ft.zb.arr : ft.zs.arr;
   name[7] = "Arrival";       val[7] = (ft.zb.kind == "" && ft.zs.kind == "") ? "—" : arrV == 1 ? "WEAK ✔" : arrV == -1 ? "STRONG ✘" : "—";
   name[8] = "Nearest BSL";   val[8] = fmtPx(nBSL); vc[8] = i_cBear;
   name[9] = "Nearest SSL";   val[9] = fmtPx(nSSL); vc[9] = i_cBull;
   name[10] = "4-factor";     val[10] = (bestSig.name == "" ? "watch " : "") + chk + "  (HTF·trend·dep/arr·liq)";
   name[11] = "Signal";       val[11] = bestSig.name == "" ? "—" : bestSig.name + " " + IntegerToString(bestSig.score) + " (" + GradeTxt(bestSig.score) + ")";
   vb[11] = Col(bestSig.name == "" ? i_cNeut : bestSig.dir == 1 ? i_cBull : i_cBear, 40); vc[11] = i_cTxt;
   string pdTxt = ft.pdBeyond ? "beyond leg (expansion)" : !(ft.inPremium || ft.inDiscount) ? "—" :
                  DoubleToString(ft.pdPct * 100, 0) + "% of leg · " + (ft.pdPct > 0.5 ? "premium (sell side)" : ft.pdPct < 0.5 ? "discount (buy side)" : "equilibrium");
   if(!isna(ft.htfPdPct))
      pdTxt += " · " + g_htfName + " " + DoubleToString(ft.htfPdPct * 100, 0) + "%" + ((ft.htfPdPct > i_pdDeep || ft.htfPdPct < 1.0 - i_pdDeep) ? " deep" : "");
   name[12] = "PD array";     val[12] = pdTxt; vc[12] = ft.pdPct > 0.5 ? i_cBear : ft.pdPct < 0.5 ? i_cBull : g_fgCol;
   name[13] = "Session";      val[13] = (ft.sessName == "" ? "— (outside killzones)" : ft.sessName + (ft.sbSessOk ? "" : " ⛔")) +
                                        (isna(nyOpen) ? "" : close > nyOpen ? " · >00:00 open" : " · <00:00 open");
   int gateN = isL ? ft.gateUp : ft.gateDn;
   string gTxt = gateN == 2 ? "aligned" : ((isL && ft.htfBias != "BEAR") || (!isL && ft.htfBias != "BULL")) ? "⚠ LTF counter (pullback)" : "⚠ counter";
   name[14] = "TP1 / gate";   val[14] = bestSig.name == "" ? "—" : bestSig.tgt + " · HTF " + gTxt;
   vc[14] = (bestSig.tgt == "REAL" && gateN == 2) ? g_fgCol : i_cRjb;
   string wTxt = "—";
   if(hasRetL) wTxt = "⏳ " + retNameL + " LONG limit @ " + fmtPx(retPxL);
   else if(hasRetS) wTxt = "⏳ " + retNameS + " SHORT limit @ " + fmtPx(retPxS);
   else if(ft.htfBias != "NEUTRAL")
   {
      bool wL = ft.htfBias == "BULL";
      int wz = -1;
      int nw = ArraySize(g_zones);
      for(int i = 0; i < nw; i++)
      {
         if(g_zones[i].broken || g_zones[i].weak || !g_zones[i].confirmed || g_zones[i].bull != wL || (g_zones[i].kind == "SR" && g_zones[i].kl < i_klMin)) continue;
         if((wL && g_zones[i].top <= close && (wz < 0 || g_zones[i].top > g_zones[wz].top)) || (!wL && g_zones[i].bottom >= close && (wz < 0 || g_zones[i].bottom < g_zones[wz].bottom)))
            wz = i;
      }
      if(wz >= 0)
      {
         double lq = NearestLiq(!wL, close);
         bool lqIn = !isna(lq) && (wL ? lq > g_zones[wz].top : lq < g_zones[wz].bottom);
         string trg = i_entryConfirm == EC_IMM ? "IMMEDIATE" : i_entryConfirm == EC_MSS ? "MSS" : "CONFIRMED";
         wTxt = (wL ? "LONG · " : "SHORT · ") + g_zones[wz].kind + (wL ? "▲ " : "▼ ") + fmtPx(g_zones[wz].bottom) + "–" + fmtPx(g_zones[wz].top) +
                (lqIn ? (wL ? " · sweep SSL " : " · sweep BSL ") + fmtPx(lq) + " first" : "") + " · " + trg;
      }
   }
   name[15] = "Watch";        val[15] = wTxt;
   Table("P", PanelCorner(), rows, name, val, nc, vc, nb, vb, i_panelFont, g_panW, g_panH);
}

void Legend()
{
   string k[8], d[8];
   color kc[8], dc[8], kb[8], db[8];
   k[0] = "▲▲ A+ · ▲ A · · B";   d[0] = "setup signal · ▲▲ = A+ · ▲ = A · · = B · grey = ⚠vs HTF/trend";                     kb[0] = Col(i_cBull, 40);
   k[1] = "BOS / CHoCH / CISD";   d[1] = "solid = displaced · dotted grey = weak / internal · dashed grey = sweep · iBOS = internal"; kb[1] = Col(i_cBull, 40);
   k[2] = "SWEEP✕ · RUN";         d[2] = "liquidity sweep (trade) · run (avoid)";                                               kb[2] = Col(i_cBear, 40);
   k[3] = "OB★ BRK RCB RJB QM";   d[3] = "zones (T1/T1b/T2/G2 = OB candle) · dashed = weak/invalid · ⚠SWEEP REQ · IDM✓ · ★★";   kb[3] = Col(i_cBrk, 40);
   k[4] = "KL / KL★";             d[4] = "key level (criteria >= min) / 4+";                                                    kb[4] = Col(i_cSR, 40);
   k[5] = "▮ FVG";                d[5] = "fair value gap (no border) · grey = mitigated";                                      kb[5] = Col(i_cBull, 85);
   k[6] = "┈┈ ╌╌";                d[6] = "dotted = BSL/SSL · thick dashed orange = POOL/EQH/EQL · grey = PDH/PDL";             kb[6] = Col(i_cPool, 85);
   k[7] = "━ entry ╌ SL ╌ TP";    d[7] = "blue entry · red dashed SL · green dashed TP1/2/3 · HTF candle O/H/L/C blue";        kb[7] = Col(i_cHtf, 85);
   for(int r = 0; r < 8; r++) { kc[r] = i_cTxt; dc[r] = g_fgCol; db[r] = clrNONE; }
   kc[5] = i_cBull; kc[6] = i_cPool; kc[7] = i_cHtf;
   int tw, th;
   Table("L", i_panelPos == PP_TR ? CORNER_LEFT_UPPER : CORNER_RIGHT_UPPER, 8, k, d, kc, dc, kb, db, i_panelFont, tw, th);
}

//+------------------------------------------------------------------+
//| extend-right boxes / background segment to the right edge        |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| transparent canvas layer: zone / FVG fills + HTF bias tint       |
//| (Pine box bgcolor + bgcolor(), real alpha, behind the bars)      |
//+------------------------------------------------------------------+
#define CVNAME "SMC854cv"
CCanvas g_cv;
bool    g_cvOk = false;
double  g_pmax = 0, g_pmin = 0;
int     g_bias[];                 // HTF bias per bar: 1 bull · -1 bear · 0 neutral / not computed
bool    g_shiftSet = false;
long    g_shiftOrig = 0;
double  g_shiftSizeOrig = 0;

uchar AlphaOf(const int transp) { return (uchar)MathRound(255.0 * (100 - MathMax(0, MathMin(100, transp))) / 100.0); }

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
   int x, y, x2, y2;
   // HTF bias tint, one column per bar (runs of equal bias merged)
   if(d_bg && ArraySize(g_bias) > g_last)
   {
      int first = (int)ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR, 0);
      int vis   = (int)ChartGetInteger(0, CHART_VISIBLE_BARS, 0);
      int sp    = 1 << (int)ChartGetInteger(0, CHART_SCALE, 0);
      int iFrom = MathMax(g_last - first - 1, 0);
      int iTo   = MathMin(g_last - first + vis + 1, g_last);
      int a = iFrom;
      while(a <= iTo)
      {
         int b = a;
         while(b + 1 <= iTo && g_bias[b + 1] == g_bias[a]) b++;
         if(g_bias[a] != 0 &&
            ChartTimePriceToXY(0, 0, gT[a], gC[a], x, y) && ChartTimePriceToXY(0, 0, gT[b], gC[b], x2, y2))
         {
            uint argb = ColorToARGB(g_bias[a] > 0 ? i_cBull : i_cBear, AlphaOf(i_bgT));
            g_cv.FillRectangle(MathMax(x - sp / 2, 0), 0, MathMin(x2 + (sp + 1) / 2, cw - 1), ch - 1, argb);
         }
         a = b + 1;
      }
   }
   // zone / FVG fills (later boxes painted over earlier ones; no XOR)
   for(int k = 0; k < ArraySize(g_boxes); k++)
   {
      if(!ChartTimePriceToXY(0, 0, g_boxes[k].t1, g_boxes[k].p1, x, y)) continue;
      if(!ChartTimePriceToXY(0, 0, g_boxes[k].t2, g_boxes[k].p2, x2, y2)) continue;
      int l = MathMin(x, x2), r = MathMax(x, x2), t = MathMin(y, y2), b = MathMax(y, y2);
      if(r < 0 || l >= cw || b < 0 || t >= ch) continue;
      g_cv.FillRectangle(MathMax(l, 0), MathMax(t, 0), MathMin(r, cw - 1), MathMin(b, ch - 1), ColorToARGB(g_boxes[k].c, AlphaOf(g_boxes[k].tr)));
   }
   g_cv.Update(false);
}

// keep the newest bars out from under a right-hand panel: chart shift sized to the panel width
void ApplyShift()
{
   if(!d_panel || !i_panelShift || g_panW <= 0) return;
   if(!(i_panelPos == PP_BR || i_panelPos == PP_TR)) return;
   int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS, 0);
   if(cw <= 0) return;
   double pct = MathMax(10.0, MathMin(50.0, MathCeil((g_panW + 30) * 100.0 / cw)));
   if(!g_shiftSet)
   {
      g_shiftOrig     = ChartGetInteger(0, CHART_SHIFT);
      g_shiftSizeOrig = ChartGetDouble(0, CHART_SHIFT_SIZE);
      g_shiftSet      = true;
   }
   if(!ChartGetInteger(0, CHART_SHIFT)) ChartSetInteger(0, CHART_SHIFT, true);
   double cur = ChartGetDouble(0, CHART_SHIFT_SIZE);
   if(cur < pct || cur > pct + 6) ChartSetDouble(0, CHART_SHIFT_SIZE, pct);   // hysteresis: the panel width moves a little each bar
}

void EndPass()
{
   datetime fut = X2T(g_last + 30);
   for(int i = 0; i < ArraySize(g_fvgs); i++)
      if(!g_fvgs[i].mitigated && g_fvgs[i].bx != "") BoxSetRightT(g_fvgs[i].bx, fut);
   for(int i = 0; i < ArraySize(g_zones); i++)
      if(!g_zones[i].broken && g_zones[i].bx != "") BoxSetRightT(g_zones[i].bx, fut);
}

void ResetAll()
{
   ObjectsDeleteAll(0, PFX);
   g_objN = 0;
   g_cx.Reset(); g_sx.Reset(); ft.Reset(); st.Reset(); cd.Reset();
   Move m0; mv = m0;
   ArrayFree(g_fvgs); ArrayFree(g_lv); ArrayFree(g_zones);
   nyOpen = NA; asiaHi = NA; asiaLo = NA;
   pdHiB = NA; pdLoS = NA; pdHiAt = -1; pdLoAt = -1;
   hRunHi = NA; hRunLo = NA; hAncLo = NA; hAncHi = NA;
   g_sigL.Reset(); g_sigS.Reset(); g_hasL = false; g_hasS = false;
   sigBar = -999; sigDir = 0; sigScore = 0; lastIdent = ""; lastIdentBar = -999;
   retL.Reset(); retS.Reset(); hasRetL = false; hasRetS = false;
   retBarL = -999; retBarS = -999; retPxL = NA; retPxS = NA; retNameL = ""; retNameS = ""; retLbL = ""; retLbS = "";
   ArrayFree(tradeLns); ArrayFree(g_lbls); ArrayFree(lns); ArrayFree(hLines);
   hiLine = ""; loLine = ""; tlSupLn = ""; tlResLn = "";
   lastUp = -1; lastDn = -1; upStack = 0; dnStack = 0;
   ArrayFree(g_boxes);
   g_lastDone = -1;
}

bool DetectFxCfd()
{
   long mode = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_CALC_MODE);
   bool fxcfd = mode == SYMBOL_CALC_MODE_FOREX || mode == SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE || mode == SYMBOL_CALC_MODE_CFD ||
                mode == SYMBOL_CALC_MODE_CFDINDEX || mode == SYMBOL_CALC_MODE_CFDLEVERAGE;
   string path = SymbolInfoString(_Symbol, SYMBOL_PATH);
   string sym = _Symbol;
   StringToUpper(path); StringToUpper(sym);
   if(Contains(path, "CRYPTO")) return false;
   string cr[] = {"BTC", "ETH", "LTC", "XRP", "BCH", "SOL", "ADA", "DOGE", "DOT", "BNB", "XLM", "LINK", "TRX", "AVAX", "MATIC", "UNI", "XTZ", "EOS", "SHIB", "TON"};
   for(int i = 0; i < ArraySize(cr); i++) if(Contains(sym, cr[i])) return false;
   return fxcfd;
}
bool En(const bool b, const bool core)
{
   if(i_setMode == SET_ALLON)  return true;
   if(i_setMode == SET_ALLOFF) return false;
   if(i_setMode == SET_CORE)   return core;
   return b;
}

//+------------------------------------------------------------------+
int OnInit()
{
   SetIndexBuffer(0, B0, INDICATOR_DATA);   SetIndexBuffer(1, B1, INDICATOR_DATA);
   SetIndexBuffer(2, B2, INDICATOR_DATA);   SetIndexBuffer(3, B3, INDICATOR_DATA);
   SetIndexBuffer(4, B4, INDICATOR_DATA);   SetIndexBuffer(5, B5, INDICATOR_DATA);
   SetIndexBuffer(6, B6, INDICATOR_DATA);   SetIndexBuffer(7, B7, INDICATOR_DATA);
   SetIndexBuffer(8, B8, INDICATOR_DATA);   SetIndexBuffer(9, B9, INDICATOR_DATA);
   SetIndexBuffer(10, B10, INDICATOR_DATA); SetIndexBuffer(11, B11, INDICATOR_DATA);
   SetIndexBuffer(12, B12, INDICATOR_DATA); SetIndexBuffer(13, B13, INDICATOR_DATA);
   for(int k = 0; k < 14; k++) PlotIndexSetDouble(k, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME, "SMC Suite v8.5.4");
   IndicatorSetInteger(INDICATOR_DIGITS, 2);

   tierAll = i_lblMode == LBL_ALL;
   tierKey = i_lblMode != LBL_SIGNALS;
   en_M01 = En(e_M01, true); en_M02 = En(e_M02, true); en_M05 = En(e_M05, true); en_M08 = En(e_M08, true);
   en_M09 = En(e_M09, true); en_M10 = En(e_M10, true); en_M15 = En(e_M15, true); en_M33 = En(e_M33, true);
   en_M36 = En(e_M36, true); en_M37 = En(e_M37, true); en_M74 = En(e_M74, true);
   en_M39 = En(e_M39, true); en_M40 = En(e_M40, true); en_M41 = En(e_M41, true); en_M42 = En(e_M42, true);
   en_M45 = En(e_M45, true); en_M46 = En(e_M46, true); en_M51 = En(e_M51, true); en_M54 = En(e_M54, true);
   en_M58 = En(e_M58, true); en_M62 = En(e_M62, true); en_M64 = En(e_M64, true); en_M68 = En(e_M68, true);
   en_M69 = En(e_M69, true); en_M70 = En(e_M70, true); en_M72 = En(e_M72, true); en_M73 = En(e_M73, true);
   immMode = i_entryConfirm == EC_IMM;
   mssMode = i_entryConfirm == EC_MSS;
   m10Imm  = i_m10Conf == M10_OFF;
   ParseSess(i_ssnAsia, ssA0, ssA1);
   ParseSess(i_ssnLon,  ssL0, ssL1);
   ParseSess(i_ssnNY,   ssN0, ssN1);
   g_htfTF   = i_mode == HM_MANUAL ? i_manual : HtfAuto(i_mode);
   g_htfName = TfName(g_htfTF);
   ssnIntra  = PeriodSeconds() < 86400;
   g_fxCfd   = DetectFxCfd();
   ssnFilt   = i_ssnOn || (i_ssnFx && g_fxCfd);
   if(i_srvGmt == -99)
   {
      long d = (long)(TimeTradeServer() - TimeGMT());
      g_srvOffSec = (int)(MathRound(d / 1800.0) * 1800);
   }
   else g_srvOffSec = i_srvGmt * 3600;
   g_bgCol = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   g_fgCol = (color)ChartGetInteger(0, CHART_COLOR_FOREGROUND);
   g_lastDone = -1;
   return INIT_SUCCEEDED;
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_CHART_CHANGE) { ApplyShift(); LblPlaceAll(); Render(); ChartRedraw(); }
}

void OnDeinit(const int reason)
{
   if(g_shiftSet)
   {
      ChartSetInteger(0, CHART_SHIFT, g_shiftOrig);
      ChartSetDouble(0, CHART_SHIFT_SIZE, g_shiftSizeOrig);
   }
   if(g_cvOk) { g_cv.Destroy(); g_cvOk = false; }
   ObjectsDeleteAll(0, PFX);
   ChartRedraw();
}

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[], const double &open[],
                const double &high[], const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   if(rates_total < 4 * i_swingLen + 20) return 0;
   ArraySetAsSeries(time, false); ArraySetAsSeries(open, false); ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);  ArraySetAsSeries(close, false); ArraySetAsSeries(tick_volume, false);

   bool full = prev_calculated == 0 || g_lastDone < 0 || g_lastDone > rates_total - 2;
   int lastClosed = rates_total - 2;
   if(!full && lastClosed <= g_lastDone)                          // tick on the forming bar: nothing new to close
   {
      // autoscale can move the price axis on a tick: re-place the labels and repaint the fills
      if(ChartGetDouble(0, CHART_PRICE_MAX, 0) != g_pmax || ChartGetDouble(0, CHART_PRICE_MIN, 0) != g_pmin)
      { LblPlaceAll(); Render(); ChartRedraw(); }
      return rates_total;
   }

   // copy series
   ArrayResize(gO, rates_total); ArrayResize(gH, rates_total); ArrayResize(gL, rates_total);
   ArrayResize(gC, rates_total); ArrayResize(gV, rates_total); ArrayResize(gT, rates_total);
   ArrayResize(gATR, rates_total);
   int oldB = ArraySize(g_bias);
   ArrayResize(g_bias, rates_total);
   for(int j = (full ? 0 : oldB); j < rates_total; j++) g_bias[j] = 0;
   int cpFrom = full ? 0 : MathMax(g_lastDone - 2, 0);
   for(int j = cpFrom; j < rates_total; j++)
   {
      gO[j] = open[j]; gH[j] = high[j]; gL[j] = low[j]; gC[j] = close[j]; gV[j] = (double)tick_volume[j]; gT[j] = time[j];
   }
   g_last = rates_total - 1;
   // ATR = RMA(TR, len), seeded with the SMA of the first len values (Pine ta.atr)
   int aFrom = full ? 0 : MathMax(g_lastDone, 1);
   for(int j = aFrom; j <= lastClosed; j++)
   {
      double tr = j == 0 ? gH[0] - gL[0] : MathMax(gH[j] - gL[j], MathMax(MathAbs(gH[j] - gC[j - 1]), MathAbs(gL[j] - gC[j - 1])));
      if(j < i_atrLen - 1) { gATR[j] = NA; continue; }
      if(j == i_atrLen - 1)
      {
         double s = 0;
         for(int k = 0; k < i_atrLen; k++)
            s += k == 0 ? gH[0] - gL[0] : MathMax(gH[k] - gL[k], MathMax(MathAbs(gH[k] - gC[k - 1]), MathAbs(gL[k] - gC[k - 1])));
         gATR[j] = s / i_atrLen;
         continue;
      }
      gATR[j] = (gATR[j - 1] * (i_atrLen - 1) + tr) / i_atrLen;
   }

   int startIdx;
   if(full)
   {
      ResetAll();
      startIdx = MathMax(rates_total - 1 - i_calcBars, 2 * i_swingLen + 2);
      startIdx = MathMax(startIdx, i_atrLen + 1);
      ArrayInitialize(B0, EMPTY_VALUE); ArrayInitialize(B1, EMPTY_VALUE); ArrayInitialize(B2, EMPTY_VALUE);
      ArrayInitialize(B3, EMPTY_VALUE); ArrayInitialize(B4, EMPTY_VALUE); ArrayInitialize(B5, EMPTY_VALUE);
      ArrayInitialize(B6, EMPTY_VALUE); ArrayInitialize(B7, EMPTY_VALUE); ArrayInitialize(B8, EMPTY_VALUE);
      ArrayInitialize(B9, EMPTY_VALUE); ArrayInitialize(B10, EMPTY_VALUE); ArrayInitialize(B11, EMPTY_VALUE);
      ArrayInitialize(B12, EMPTY_VALUE); ArrayInitialize(B13, EMPTY_VALUE);
   }
   else startIdx = g_lastDone + 1;

   // HTF / D1 / W1 feeds (reloaded on every new bar; a not-yet-synchronised feed retries on the next tick)
   datetime from = gT[MathMax(full ? startIdx : MathMax(rates_total - 1 - i_calcBars, 0), 0)];
   if(!FeedLoad(fHtf, g_htfTF, from) || FeedIdx(fHtf, gT[lastClosed]) < 0)
   {
      if(full) { g_lastDone = -1; return 0; }
      return prev_calculated;
   }
   FeedLoad(fD1, PERIOD_D1, from);
   FeedLoad(fW1, PERIOD_W1, from);

   for(int i = startIdx; i <= lastClosed; i++)
   {
      g_live = !full && i == lastClosed;
      ProcessBar(i);
      g_lastDone = i;
   }
   B0[rates_total - 1] = EMPTY_VALUE; B1[rates_total - 1] = EMPTY_VALUE; B2[rates_total - 1] = EMPTY_VALUE;
   B3[rates_total - 1] = EMPTY_VALUE; B4[rates_total - 1] = EMPTY_VALUE; B5[rates_total - 1] = EMPTY_VALUE;
   B6[rates_total - 1] = EMPTY_VALUE; B7[rates_total - 1] = EMPTY_VALUE; B8[rates_total - 1] = EMPTY_VALUE;
   B9[rates_total - 1] = EMPTY_VALUE; B10[rates_total - 1] = EMPTY_VALUE; B11[rates_total - 1] = EMPTY_VALUE;
   B12[rates_total - 1] = EMPTY_VALUE; B13[rates_total - 1] = EMPTY_VALUE;

   EndPass();
   if(d_panel)  Panel();
   if(d_legend) Legend();
   ApplyShift();
   LblPlaceAll();
   Render();
   ChartRedraw();
   return rates_total;
}
//+------------------------------------------------------------------+
