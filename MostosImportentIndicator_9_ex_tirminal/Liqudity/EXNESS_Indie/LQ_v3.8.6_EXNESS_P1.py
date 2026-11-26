# indie:lang_version = 5
# =============================================================================
# Liquidity + S/D + Price Action v3.8.6  —  Exness Terminal (Indie) port, PHASE 1
# Source: liqudity_trap_trading.v3.8.6.txt (Pine v5, 5661 lines)
#
# PHASE 1 CONTAINS (logic kept 1:1 with the Pine file where marked):
#   M2  constants · M3 ATR (shock-capped), candle anatomy, CISD, IFC, confirmations
#   M4  pivots, last swing levels, EQH/EQL pools (+age-out)
#   M4B NY session clock, killzones, Silver Bullet windows, volatility windows
#   M5  sweeps (one event per level, multi-bar reclaim, RAW/EFF quality, pool kind),
#       PDH/PDL/PWH/PWL raids, Asia/London/NY session H/L raids, sweep-in-play
#   M6  internal + external protected-swing structure (BOS/CHoCH/MSS), trigger memory
#   M7  HTF bias (EMA + HTF structure on the bias TF, last CLOSED HTF bar) + neutral mode
#   M9  ADR exhaustion (own daily tracking)        M10 dealing range / P-D / OTE / SB lock
#   M11 regime                                      M12 FVG registry + IFVG flip
#   M13 zone engine (S/D, OB, RB, IFVG, breaker/mitigation, band claim, tests, 50% tap)
#   M15A direction lock   M16 score + tiers   M17 master state machine (SB path incl.)
#   M18 final gate, gate-kill retry, conflict rule   M18B plan / risk / min-RR gate
#   M19 next-open fill tracker, TP1/TP2/TP3, BE, SB exits, governance counters
#   M20 drawings (zones, FVG, EQ, session H/L, structure chips, signals, trade ladder)
#   M21 dashboard
# NOT YET (PHASE 2/3): HTF CRT/Turtle-soup/HTF FVG POI (+ continuation arm),
#   chart CRT / TBS / trendline / inside-bar / doji engines, Liquidity Trap engine,
#   debug table. Indie has no alert() API — alerts cannot be ported.
# Day boundary = 00:00 UTC (Exness server day). NY session times are DST-aware.
# =============================================================================
import math
from math import isnan
from datetime import datetime
from dataclasses import dataclass
from indie import indicator, param, param_ref, plot, color, line_style, MainContext, sec_context, MutSeriesF, SeriesF, Var, TimeFrame, Color
from indie.algorithms import Atr, Ema, Sma
from indie.drawings import LabelAbs, LabelRel, AbsolutePosition, RelativePosition, LineSegment, Rectangle, Table, TableRow, TableCell, callout_position
from indie.drawings import vertical_anchor as va, horizontal_anchor as ha

NA = -1000000


def nz_f(x: float, d: float) -> float:
    if isnan(x):
        return d
    return x


def ny_offset_h(ts: float) -> int:
    # US DST: 2nd Sunday of March 07:00 UTC .. 1st Sunday of November 06:00 UTC
    y = datetime.utcfromtimestamp(ts).year
    m1 = datetime(y, 3, 1)
    first_sun_m = 1 + (6 - m1.weekday()) % 7
    dst_start = datetime(y, 3, first_sun_m + 7, 7, 0, 0).timestamp()
    n1 = datetime(y, 11, 1)
    first_sun_n = 1 + (6 - n1.weekday()) % 7
    dst_end = datetime(y, 11, first_sun_n, 6, 0, 0).timestamp()
    if ts >= dst_start and ts < dst_end:
        return -4
    return -5


def in_win(m: int, st: int, en: int) -> bool:
    return m >= st and m < en


def piv_hi(src: SeriesF, p: int, avail: int) -> float:
    if avail < 2 * p + 1:
        return math.nan
    c = src[p]
    for k in range(1, p + 1):
        if src[p + k] > c or src[p - k] >= c:
            return math.nan
    return c


def piv_lo(src: SeriesF, p: int, avail: int) -> float:
    if avail < 2 * p + 1:
        return math.nan
    c = src[p]
    for k in range(1, p + 1):
        if src[p + k] < c or src[p - k] <= c:
            return math.nan
    return c


def tier_txt(t: int) -> str:
    if t == 4:
        return 'A+'
    if t == 3:
        return 'A'
    if t == 2:
        return 'B'
    return 'C'


def sb_win_txt(w: int) -> str:
    if w == 1:
        return 'London'
    if w == 2:
        return 'NY AM'
    if w == 3:
        return 'NY PM'
    return '-'


def stage_txt(s: int) -> str:
    if s == 1:
        return 'SWEPT'
    if s == 2:
        return 'AT POI'
    if s == 3:
        return 'SHIFTED'
    if s == 4:
        return 'ACTIVE'
    return 'IDLE'


def px(x: float, prec: int) -> str:
    if isnan(x):
        return '-'
    if prec <= 0:
        return f'{x:.0f}'
    if prec == 1:
        return f'{x:.1f}'
    if prec == 2:
        return f'{x:.2f}'
    if prec == 3:
        return f'{x:.3f}'
    if prec == 4:
        return f'{x:.4f}'
    return f'{x:.5f}'


@dataclass
class Zone:
    top: float
    bot: float
    is_supply: bool
    touched: bool
    tapped50: bool
    signaled: bool
    score: int
    tap50_bar: int
    flipped: bool
    touch_bar: int
    kind: str
    tests: int
    was_in: bool
    left_t: float


@dataclass
class Fvg:
    top: float
    bot: float
    bar_created: int
    is_bull: bool
    partial: bool
    inverted: bool
    left_t: float


@dataclass
class HPoi:
    top: float
    bot: float
    bar: int
    ins: int
    was_in: bool


def arrow(d: int) -> str:
    if d > 0:
        return '▲ Bull'
    if d < 0:
        return '▼ Bear'
    return '— Neut'


# ---- MODULE 7 · HTF bias TF: EMA bias + protected-swing structure ---------------
# Returns the LAST CLOSED HTF bar's values ([1] + lookahead), as in the Pine file.
@sec_context
@param_ref('bias_len')
@param_ref('htf_piv')
@param_ref('struct_disp')
@param_ref('atr_len')
def HtfSec(self, bias_len, htf_piv, struct_disp, atr_len):
    ema = Ema.new(self.close, bias_len)
    atr_h = Atr.new(atr_len)
    res = Var[float].new(math.nan)
    sup = Var[float].new(math.nan)
    res_brk = Var[bool].new(False)
    sup_brk = Var[bool].new(False)
    sdir = Var[int].new(0)
    plo = Var[float].new(math.nan)
    phi = Var[float].new(math.nan)
    llo = Var[float].new(math.nan)
    lhi = Var[float].new(math.nan)
    nbar = Var[int].new(0)
    nbar.set(nbar.get() + 1)
    h_ph = piv_hi(self.high, htf_piv, nbar.get())
    h_pl = piv_lo(self.low, htf_piv, nbar.get())
    if not isnan(h_ph):
        res.set(h_ph)
        res_brk.set(False)
    if not isnan(h_pl):
        sup.set(h_pl)
        sup_brk.set(False)
    c = self.close[0]
    body = abs(c - self.open[0])
    up_brk = (not isnan(res.get())) and (not res_brk.get()) and c > res.get()
    dn_brk = (not isnan(sup.get())) and (not sup_brk.get()) and c < sup.get()
    if up_brk:
        res_brk.set(True)
    if dn_brk:
        sup_brk.set(True)
    if isnan(llo.get()):
        llo.set(self.low[0])
    else:
        llo.set(min(llo.get(), self.low[0]))
    if isnan(lhi.get()):
        lhi.set(self.high[0])
    else:
        lhi.set(max(lhi.get(), self.high[0]))
    ev = False
    if body >= struct_disp * atr_h[0]:
        d = sdir.get()
        if d == 1:
            if up_brk:
                plo.set(llo.get())
                ev = True
            elif (not isnan(plo.get())) and c < plo.get():
                sdir.set(-1)
                phi.set(lhi.get())
                plo.set(math.nan)
                ev = True
        elif d == -1:
            if dn_brk:
                phi.set(lhi.get())
                ev = True
            elif (not isnan(phi.get())) and c > phi.get():
                sdir.set(1)
                plo.set(llo.get())
                phi.set(math.nan)
                ev = True
        elif up_brk:
            sdir.set(1)
            plo.set(llo.get())
            ev = True
        elif dn_brk:
            sdir.set(-1)
            phi.set(lhi.get())
            ev = True
        if ev:
            llo.set(self.low[0])
            lhi.set(self.high[0])
    eb = 0.0
    if not isnan(ema[0]):
        eb = 1.0 if c > ema[0] else -1.0
    s_eb = MutSeriesF.new(eb)
    s_dir = MutSeriesF.new(float(sdir.get()))
    s_plo = MutSeriesF.new(plo.get())
    s_phi = MutSeriesF.new(phi.get())
    return s_eb[1], s_dir[1], s_plo[1], s_phi[1]


# =============================================================================
# MAIN
# =============================================================================
@indicator('LQ-SD-PA v3.8.6 EXNESS P1', overlay_main_pane=True)
# --- General
@param.int('piv_len', default=5, min=2, title='Internal pivot length')
@param.int('ext_piv', default=12, min=5, title='External pivot length (major swings)')
@param.int('atr_len', default=14, min=1, title='ATR length')
@param.float('atr_cap', default=1.5, min=0.0, step=0.25, title='ATR shock cap (x 50-bar avg ATR, 0 = off)')
@param.bool('show_levels', default=True, title='Plot last swing high / low')
# --- HTF context
@param.bool('bias_on', default=True, title='HTF bias filter ON (off = scored, never blocking)')
@param.time_frame('bias_tf', default='1h', title='HTF bias timeframe')
@param.int('bias_len', default=50, min=5, title='Bias EMA length')
@param.str('bias_mode', default='Structure + EMA', options=['EMA only', 'Structure only', 'Structure + EMA'], title='HTF bias source')
@param.int('htf_piv', default=5, min=2, max=20, title='HTF structure pivot length')
@param.bool('htf_prot_inval', default=True, title='HTF protected swing invalidates a setup')
@param.str('neutral_mode', default='Follow chart structure', options=['Block both sides', 'Follow chart structure', 'Allow both'], title='When the HTF bias is NEUTRAL')
# --- Liquidity
@param.int('sweep_look', default=12, min=1, title='Sweep stays in play (bars)')
@param.float('eq_tol', default=0.15, min=0.05, step=0.05, title='Equal level tolerance (ATR x)')
@param.int('eq_max_age', default=240, min=20, title='EQ pool expires after N bars')
@param.int('min_arm_qual', default=2, min=1, max=4, title='Min sweep quality to arm (1-4)')
@param.int('reclaim_bars', default=4, min=0, max=10, title='Multi-bar sweep reclaim window (0 = off)')
@param.bool('show_eq', default=True, title='Draw EQH / EQL pools')
@param.bool('show_pdwl', default=True, title='Draw PDH/PDL/PWH/PWL')
# --- Structure
@param.float('struct_disp', default=0.5, min=0.0, step=0.1, title='Structural break body >= ATR x')
@param.bool('show_struct', default=True, title='Label BOS / CHoCH / MSS')
@param.bool('mss_need_ext', default=True, title='MSS requires an EXTERNAL CHoCH')
@param.bool('show_int_struct', default=True, title='Also label internal iBOS / iCHoCH')
# --- FVG / zones
@param.bool('show_fvg', default=True, title='Draw chart-TF FVGs')
@param.int('fvg_keep', default=4, min=1, max=10, title='Max live FVGs per side')
@param.int('fvg_age', default=120, min=10, title='FVG max age (bars)')
@param.bool('use_ifvg', default=True, title='Flip violated FVGs into IFVG POIs')
@param.bool('show_zones', default=True, title='Supply / demand zones')
@param.float('disp_fact', default=1.2, min=0.5, step=0.1, title='Displacement body >= ATR x')
@param.float('max_zone_atr', default=2.0, min=0.5, step=0.5, title='Max zone height (ATR x)')
@param.int('max_zones', default=6, min=1, max=20, title='Max zones per side')
@param.bool('show_ob', default=True, title='Order block companions')
@param.int('confirm_win', default=5, min=1, max=20, title='Max bars 50% tap -> confirmation')
@param.bool('show_flip', default=True, title='Breaker / mitigation flips')
@param.bool('show_rb', default=True, title='Rejection blocks')
@param.float('min_zone', default=0.15, min=0.0, step=0.05, title='Min zone height (ATR x)')
@param.int('zone_tests', default=2, min=1, max=6, title='Zone spent after N separate tests')
# --- Sessions / Silver Bullet
@param.bool('use_kz', default=False, title='Only signal inside killzones')
@param.bool('show_ses', default=True, title='Session high / low lines')
@param.bool('sb_enable', default=True, title='Silver Bullet module')
@param.int('sb_pre_min', default=15, min=0, max=60, title='SB: arm N minutes before the window')
@param.int('sb_qual_lo', default=3, min=1, max=4, title='SB London min sweep quality')
@param.int('sb_qual_am', default=2, min=1, max=4, title='SB NY AM min sweep quality')
@param.int('sb_qual_pm', default=3, min=1, max=4, title='SB NY PM min sweep quality')
@param.bool('sb_pool_pref', default=True, title='SB requires a preferred pool')
@param.float('sb_disp', default=0.8, min=0.3, step=0.1, title='SB displacement body >= ATR x')
@param.bool('use_news', default=True, title='Block scheduled volatility windows (NY 08:25-08:45, 09:55-10:10, Wed 13:55-14:35)')
# --- Quality / machine
@param.str('tier_mode', default='A and above', options=['A+ only', 'A and above', 'B and above', 'All (incl. C)'], title='Show signal tiers')
@param.int('min_score', default=50, min=0, max=100, title='Min alignment score (0 = off)')
@param.int('master_cd', default=15, min=0, title='Same-direction cooldown (bars)')
@param.bool('use_regime', default=True, title='Suppress entries in CHOP')
@param.int('liq_wait', default=20, min=3, title='Machine: bars sweep -> POI tap')
@param.int('poi_wait', default=15, min=3, title='Machine: bars POI tap -> shift')
@param.int('ret_wait', default=20, min=3, title='Machine: bars shift -> entry')
@param.int('arm_grace', default=3, min=0, max=10, title='Machine: arm grace bars after the sweep')
@param.str('shift_src', default='MSS / external CHoCH', options=['MSS only', 'MSS / external CHoCH', '+ internal CHoCH', '+ CISD'], title='Machine: what counts as the SHIFT')
@param.bool('one_dir', default=True, title='One direction at a time')
@param.bool('fast_shift', default=True, title='Displaced shift while sweep in play skips POI stage')
@param.str('mc_entry', default='CE preferred + confirmation fallback', options=['Proximal edge + confirmation', 'CE preferred + confirmation fallback', 'CE (50%) only'], title='Machine entry rule')
@param.bool('mc_req_pd', default=True, title='Machine: correct side of the dealing range')
# --- Risk
@param.float('rr_mult', default=2.0, min=0.5, step=0.5, title='TP2 R multiple')
@param.float('max_risk', default=1.5, min=0.0, step=0.25, title='Max risk (ATR x, 0 = off)')
@param.str('risk_mode', default='Reject the signal', options=['Reject the signal', 'Clamp the stop'], title='Stop wider than the cap')
@param.float('min_rr', default=1.5, min=0.0, step=0.25, title='Min RR to TP2 (0 = off)')
@param.float('spread_ticks', default=0.0, min=0.0, step=0.5, title='Spread (ticks) - bid chart, ask-side tests')
@param.float('slip_guard', default=0.5, min=0.0, step=0.1, title='Max close -> plan entry (ATR x)')
@param.int('max_trd_bars', default=80, min=0, title='Tracked trade max life (bars)')
@param.bool('use_gov', default=True, title='Daily trade / loss limit')
@param.int('max_trd_day', default=4, min=0, title='Max signals per day')
@param.int('max_loss_day', default=2, min=0, title='Stop after N losing trades')
# --- Advanced
@param.float('near_lvl', default=0.25, min=0.05, step=0.05, title='At-the-level tolerance (ATR x)')
@param.float('sl_pad', default=0.25, min=0.0, step=0.05, title='Stop padding (ATR x)')
@param.float('sweep_ctx', default=3.0, min=1.0, step=0.5, title='Sweep in play within (ATR x)')
@param.float('poi_near', default=1.5, min=0.5, step=0.25, title='Near the POI (ATR x)')
@param.int('trig_look', default=10, min=3, max=30, title='Shift stays a live trigger (bars)')
@param.int('regime_look', default=40, min=10, max=200, title='Regime: external-event memory (bars)')
@param.float('chop_rng', default=6.0, min=2.0, step=0.5, title='CHOP: external range < ATR x')
# --- UI
@param.bool('show_dash', default=True, title='Dashboard')
@param.bool('show_trade', default=True, title='Entry / SL / TP of last signal')
@param.int('font', default=11, min=8, max=18, title='Dashboard font size')
@param.str('dash_pos', default='Top right', options=['Top right', 'Top left', 'Bottom right', 'Bottom left'], title='Dashboard position')
@param.float('dash_w', default=0.15, min=0.05, max=0.60, step=0.01, title='Dashboard width estimate (raise if cut off, lower to move right)')
@param.bool('dash_compact', default=False, title='Compact dashboard (fewer rows)')
@param.int('lbl_font', default=12, min=8, max=20, title='Chart label text size')
@param.bool('show_sweeps', default=True, title='Mark liquidity sweeps (swing / EQ / PD-PW / session)')
@param.bool('show_prot', default=True, title='Plot protected swing (external)')
@param.bool('sb_paint', default=True, title='Shade Silver Bullet windows')
@param.bool('paint_news', default=True, title='Shade scheduled volatility windows')
@param.bool('show_tl', default=True, title='Dynamic trendlines (pivot pairs)')
@param.bool('tl_sweep', default=True, title='Trendline sweep trigger candidates')
@param.int('tl_max_age', default=150, min=20, title='Trendline expires after N bars')
@param.bool('show_poi', default=True, title='HTF FVG POI boxes')
@param.str('poi_tf', default='Auto', options=['Auto', '15', '30', '60', '240', 'D'], title='HTF for the FVG POI')
@param.int('hpoi_age', default=40, min=5, title='HTF POI max age (HTF candles)')
@param.int('hpoi_touch', default=2, min=1, title='HTF POI spent after N separate visits')
@param.bool('show_next', default=True, title='NEXT BUY / NEXT SELL level')
@param.int('next_back', default=60, min=10, max=300, title='NEXT line extends back N bars')
@param.float('hpoi_next_max', default=4.0, min=1.0, step=0.5, title='HTF POI may be NEXT only if height <= ATR x')
@plot.line('res', title='Last swing high', color=color.rgba(242, 54, 69, 0.5))
@plot.line('sup', title='Last swing low', color=color.rgba(8, 153, 129, 0.5))
@plot.line('plo', title='Protected low (external)', color=color.rgba(8, 153, 129, 0.85), line_width=2)
@plot.line('phi', title='Protected high (external)', color=color.rgba(242, 54, 69, 0.85), line_width=2)
@plot.line('pdh', title='Prev day high', color=color.SILVER(0.45))
@plot.line('pdl', title='Prev day low', color=color.SILVER(0.45))
@plot.line('pwh', title='Prev week high', color=color.SILVER(0.3), line_width=2)
@plot.line('pwl', title='Prev week low', color=color.SILVER(0.3), line_width=2)
@plot.marker(title='Sell-side sweep', color=color.rgba(8, 153, 129, 1.0), style=plot.marker_style.CIRCLE, position=plot.marker_position.BELOW, size=2)
@plot.marker(title='Buy-side sweep', color=color.rgba(242, 54, 69, 1.0), style=plot.marker_style.CIRCLE, position=plot.marker_position.ABOVE, size=2)
@plot.background(title='Silver Bullet window', color=color.TRANSPARENT)
@plot.background(title='Volatility window', color=color.TRANSPARENT)
class Main(MainContext):
    def __init__(self, bias_tf):
        self.high.request_size(520)
        self.low.request_size(520)
        self.close.request_size(520)
        self.open.request_size(520)
        self.time.request_size(520)
        self._hb, self._hd, self._hplo, self._hphi = self.calc_on(HtfSec, time_frame=bias_tf, lookahead=True)
        self.c_bull = color.rgba(8, 153, 129, 1.0)
        self.c_bear = color.rgba(242, 54, 69, 1.0)
        self.nbar = 0
        self.lf = 12
        self.cap_bg = color.rgba(19, 23, 34, 0.75)
        # M3 CISD / atr history
        self.atr_hist: list[float] = []
        self.atr_raw_hist: list[float] = []
        self.bull_run_open = math.nan
        self.bear_run_open = math.nan
        self.bull_run_len = 0
        self.bear_run_len = 0
        self.cisd_dn_done = False
        self.cisd_up_done = False
        self.prev_cisd_bull = False
        self.prev_cisd_bear = False
        # M4
        self.last_res = math.nan
        self.last_sup = math.nan
        self.last_res_bar = NA
        self.last_sup_bar = NA
        self.prev_ph = math.nan
        self.prev_pl = math.nan
        self.res_broken = False
        self.sup_broken = False
        self.res_bos_done = False
        self.sup_bos_done = False
        self.res_brk_bar = NA
        self.sup_brk_bar = NA
        self.eqh_lvls: list[float] = []
        self.eqh_bars: list[int] = []
        self.eqh_lns: list[LineSegment] = []
        self.eql_lvls: list[float] = []
        self.eql_bars: list[int] = []
        self.eql_lns: list[LineSegment] = []
        # M4B
        self.sb_win_prev = 0
        self.in_sblo_prev = False
        self.in_sbam_prev = False
        self.in_sbpm_prev = False
        # M5
        self.ssl_spent = math.nan
        self.bsl_spent = math.nan
        self.last_ssl_bar = NA
        self.last_bsl_bar = NA
        self.last_ssl_lvl = math.nan
        self.last_bsl_lvl = math.nan
        self.last_ssl_ext = math.nan
        self.last_bsl_ext = math.nan
        self.ssl_q = 0
        self.bsl_q = 0
        self.ssl_q_raw = 0
        self.bsl_q_raw = 0
        self.ssl_kind = 0
        self.bsl_kind = 0
        # daily / weekly
        self.day_id = -1
        self.week_id = -1
        self.day_hi = math.nan
        self.day_lo = math.nan
        self.week_hi = math.nan
        self.week_lo = math.nan
        self.pdh = math.nan
        self.pdl = math.nan
        self.pwh = math.nan
        self.pwl = math.nan
        self.pdh_done = False
        self.pdl_done = False
        self.pwh_done = False
        self.pwl_done = False
        self.day_ranges: list[float] = []
        self.new_day = False
        # sessions: index 0 Asia · 1 London · 2 NY
        self.s_act_prev: list[bool] = [False, False, False]
        self.s_hi: list[float] = [math.nan, math.nan, math.nan]
        self.s_lo: list[float] = [math.nan, math.nan, math.nan]
        self.s_hi_lvl: list[float] = [math.nan, math.nan, math.nan]
        self.s_lo_lvl: list[float] = [math.nan, math.nan, math.nan]
        self.s_hi_sw: list[bool] = [False, False, False]
        self.s_lo_sw: list[bool] = [False, False, False]
        self.s_hi_t: list[float] = [0.0, 0.0, 0.0]
        self.s_hi_end_t: list[float] = [0.0, 0.0, 0.0]
        self.s_lo_end_t: list[float] = [0.0, 0.0, 0.0]
        self.s_hi_ln: list[LineSegment] = []
        self.s_lo_ln: list[LineSegment] = []
        for _k in range(3):
            self.s_hi_ln.append(LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0)))
            self.s_lo_ln.append(LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0)))
        self.s_drawn: list[bool] = [False, False, False]
        self.last_eng_lo_bar = NA
        self.last_eng_hi_bar = NA
        # M6 structure (index 0 internal · 1 external)
        self.st_dir: list[int] = [0, 0]
        self.st_plo: list[float] = [math.nan, math.nan]
        self.st_phi: list[float] = [math.nan, math.nan]
        self.st_llo: list[float] = [math.nan, math.nan]
        self.st_lhi: list[float] = [math.nan, math.nan]
        self.ext_res = math.nan
        self.ext_sup = math.nan
        self.ext_res_bar = NA
        self.ext_sup_bar = NA
        self.ext_res_bos_done = False
        self.ext_sup_bos_done = False
        self.l_ch_up = NA
        self.l_ch_dn = NA
        self.l_bos_up = NA
        self.l_bos_dn = NA
        self.l_mss_up = NA
        self.l_mss_dn = NA
        self.l_cisd_up = NA
        self.l_cisd_dn = NA
        self.l_ech_up = NA
        self.l_ech_dn = NA
        self.l_ebos_up = NA
        self.l_ebos_dn = NA
        # M10
        self.sb_rng_hi = math.nan
        self.sb_rng_lo = math.nan
        self.sb_rng_win = 0
        self.sb_set_live = False
        self.sb_tag_l = 0
        self.sb_tag_s = 0
        self.close_hist: list[float] = []
        # M12 FVG
        self.bfv: list[Fvg] = []
        self.sfv: list[Fvg] = []
        self.bfx: list[Rectangle] = []
        self.sfx: list[Rectangle] = []
        self.cfb_top = math.nan
        self.cfb_bot = math.nan
        self.cfb_bar = NA
        self.cfb_disp = False
        self.cfs_top = math.nan
        self.cfs_bot = math.nan
        self.cfs_bar = NA
        self.cfs_disp = False
        # M13 zones
        self.zones: list[Zone] = []
        self.zbx: list[Rectangle] = []
        self.nb_top_prev = math.nan
        self.ns_bot_prev = math.nan
        # M15A machine + tracker
        self.su_l = 0
        self.su_l_bar = NA
        self.su_l_at = math.nan
        self.su_l_ab = math.nan
        self.su_l_fvg_bar = NA
        self.su_l_sw_lvl = math.nan
        self.su_l_sw_ext = math.nan
        self.su_l_reason = ''
        self.su_s = 0
        self.su_s_bar = NA
        self.su_s_at = math.nan
        self.su_s_ab = math.nan
        self.su_s_fvg_bar = NA
        self.su_s_sw_lvl = math.nan
        self.su_s_sw_ext = math.nan
        self.su_s_reason = ''
        self.sb_shift_gl = 0
        self.sb_shift_gs = 0
        self.sb_armed_ssl = NA
        self.sb_armed_bsl = NA
        self.armed_ssl = NA
        self.armed_bsl = NA
        self.sb_done_win_l = 0
        self.sb_done_win_s = 0
        self.trd_entry = math.nan
        self.trd_sl = math.nan
        self.trd_tp1 = math.nan
        self.trd_tp2 = math.nan
        self.trd_tp3 = math.nan
        self.trd_dir = 0
        self.trd_bar = NA
        self.trd_tp1_hit = False
        self.trd_tp2_hit = False
        self.trd_is_sb = False
        self.trd_sb_win = 0
        self.trd_shift_g = 0
        self.pend_dir = 0
        self.pend_sl = math.nan
        self.last_long_sig = NA
        self.last_short_sig = NA
        self.trd_today = 0
        self.loss_today = 0
        self.cnt_long = 0
        self.cnt_short = 0
        self.cnt_tp1 = 0
        self.cnt_tp2 = 0
        self.cnt_tp3 = 0
        self.cnt_sl = 0
        self.cnt_be = 0
        self.cnt_exp = 0
        self.cnt_untracked = 0
        self.sum_r = 0.0
        # display state
        self.marks: list[LabelAbs] = []
        self.ladder: list[LineSegment] = []
        self.pd_lns: list[LineSegment] = []
        pd_cols: list[Color] = [color.RED(0.6), color.GREEN(0.6), color.MAROON(0.6), color.TEAL(0.6)]
        for _j in range(4):
            self.pd_lns.append(LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0), color=pd_cols[_j], line_style=line_style.DASHED, line_width=1))
        self.pd_drawn = False
        self.last_sig_txt = ''
        self.dash = Table(position=RelativePosition(va.TOP, ha.LEFT, 0.03, 0.80), bg_color=color.rgba(19, 23, 34, 0.95), text_color=color.rgba(220, 224, 232, 1.0), frame_color=color.rgba(90, 96, 110, 1.0), grid_color=color.rgba(50, 55, 68, 1.0))
        # dealing-range running extremes + DST cache
        self.dr_start = NA
        self.dr_hi = math.nan
        self.dr_lo = math.nan
        self.dr_hi_bar = NA
        self.dr_lo_bar = NA
        self.dst_y0 = 0.0
        self.dst_y1 = -1.0
        self.dst_s = 0.0
        self.dst_e = 0.0
        # plot outputs
        self.o_plo = math.nan
        self.o_phi = math.nan
        self.o_pdh = math.nan
        self.o_pdl = math.nan
        self.o_pwh = math.nan
        self.o_pwl = math.nan
        # session tags
        self.s_hi_lb: list[LabelAbs] = []
        self.s_lo_lb: list[LabelAbs] = []
        for _q in range(3):
            self.s_hi_lb.append(LabelAbs('', AbsolutePosition(0.0, 0.0)))
            self.s_lo_lb.append(LabelAbs('', AbsolutePosition(0.0, 0.0)))
        # daily EMA bias
        self.d_ema = math.nan
        self.d_bias = 0
        # trendlines
        self.prev_ph_bar = NA
        self.prev_pl_bar = NA
        self.prev_ph_t = 0.0
        self.prev_pl_t = 0.0
        self.tl_up_slope = math.nan
        self.tl_up_price = math.nan
        self.tl_up_bar = NA
        self.tl_up_touch = 0
        self.tl_up_near = False
        self.tl_up_t0 = 0.0
        self.tl_up_p0 = 0.0
        self.tl_up_live = False
        self.tl_dn_slope = math.nan
        self.tl_dn_price = math.nan
        self.tl_dn_bar = NA
        self.tl_dn_touch = 0
        self.tl_dn_near = False
        self.tl_dn_t0 = 0.0
        self.tl_dn_p0 = 0.0
        self.tl_dn_live = False
        self.tl_up_ln = LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0), color=self.c_bull(0.7), line_style=line_style.DOTTED, line_width=2)
        self.tl_dn_ln = LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0), color=self.c_bear(0.7), line_style=line_style.DOTTED, line_width=2)
        self.tl_up_drawn = False
        self.tl_dn_drawn = False
        self.tl_old: list[LineSegment] = []
        # HTF POI (own HTF aggregation of chart bars)
        self.h_bucket = -1
        self.h_n = 0
        self.h_cur_h = math.nan
        self.h_cur_l = math.nan
        self.h_cur_c = math.nan
        self.h_hist_h: list[float] = []
        self.h_hist_l: list[float] = []
        self.hpd: list[HPoi] = []
        self.hps: list[HPoi] = []
        self.hp_bx: list[Rectangle] = []
        self.hp_lb: list[LabelAbs] = []
        self.hp_drawn: list[bool] = [False, False]
        for _r in range(2):
            self.hp_bx.append(Rectangle(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0), line_style=line_style.DASHED))
            self.hp_lb.append(LabelAbs('', AbsolutePosition(0.0, 0.0)))
        self.d_hpb_top = math.nan
        self.d_hpb_bot = math.nan
        self.d_hpb_in = 0
        self.d_hps_top = math.nan
        self.d_hps_bot = math.nan
        self.d_hps_in = 0
        self.d_htf_lbl = ''
        # NEXT labels + zone captions
        self.nx_ln: list[LineSegment] = []
        self.nx_lb: list[LabelAbs] = []
        self.nx_drawn: list[bool] = [False, False]
        for _u in range(2):
            self.nx_ln.append(LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0)))
            self.nx_lb.append(LabelAbs('', AbsolutePosition(0.0, 0.0)))
        self.zlb: list[LabelAbs] = []
        self.d_nb_score = 0
        self.d_ns_score = 0
        self.d_nb_fresh = False
        self.d_ns_fresh = False
        self.d_nb_kind = ''
        self.d_ns_kind = ''
        self.d_trig = ''
        self.d_sweep = ''
        self.d_tight = False
        self.d_sbtxt = ''
        self.d_verdict = ''
        self.d_in_poi = ''
        self.d_ema_b = 0
        self.d_hs_dir = 0
        self.d_bias_tf = ''
        # dashboard snapshot
        self.d_regime = ''
        self.d_htfb = 0
        self.d_ext = 0
        self.d_int = 0
        self.d_score_l = 0
        self.d_score_s = 0
        self.d_tier_l = 1
        self.d_tier_s = 1
        self.d_pd = math.nan
        self.d_nb_top = math.nan
        self.d_nb_bot = math.nan
        self.d_ns_top = math.nan
        self.d_ns_bot = math.nan
        self.d_ses = ''
        self.d_adr = math.nan

    # =========================================================================
    def calc(self, piv_len, ext_piv, atr_len, atr_cap, show_levels, bias_on, bias_tf, bias_len, bias_mode, htf_piv, htf_prot_inval, neutral_mode, sweep_look, eq_tol, eq_max_age, min_arm_qual, reclaim_bars, show_eq, show_pdwl, struct_disp, show_struct, mss_need_ext, show_int_struct, show_fvg, fvg_keep, fvg_age, use_ifvg, show_zones, disp_fact, max_zone_atr, max_zones, show_ob, confirm_win, show_flip, show_rb, min_zone, zone_tests, use_kz, show_ses, sb_enable, sb_pre_min, sb_qual_lo, sb_qual_am, sb_qual_pm, sb_pool_pref, sb_disp, use_news, tier_mode, min_score, master_cd, use_regime, liq_wait, poi_wait, ret_wait, arm_grace, shift_src, one_dir, fast_shift, mc_entry, mc_req_pd, rr_mult, max_risk, risk_mode, min_rr, spread_ticks, slip_guard, max_trd_bars, use_gov, max_trd_day, max_loss_day, near_lvl, sl_pad, sweep_ctx, poi_near, trig_look, regime_look, chop_rng, show_dash, show_trade, font, dash_pos, dash_w, dash_compact, lbl_font, show_sweeps, show_prot, sb_paint, paint_news, show_tl, tl_sweep, tl_max_age, show_poi, poi_tf, hpoi_age, hpoi_touch, show_next, next_back, hpoi_next_max):
        atr_raw_s = Atr.new(atr_len)
        self.lf = lbl_font
        atr_avg_s = Sma.new(atr_raw_s, 50)
        res_out = self.last_res if show_levels else math.nan
        sup_out = self.last_sup if show_levels else math.nan
        # every engine below runs on CLOSED bars only (Pine `barstate.isconfirmed`)
        if not self.is_closed_bar:
            return res_out, sup_out, self.o_plo, self.o_phi, self.o_pdh, self.o_pdl, self.o_pwh, self.o_pwl, plot.Marker(math.nan), plot.Marker(math.nan), plot.Background(color.TRANSPARENT), plot.Background(color.TRANSPARENT)
        bi = self.bar_index
        avail = bi + 1
        if bi < 25:
            return res_out, sup_out, self.o_plo, self.o_phi, self.o_pdh, self.o_pdl, self.o_pwh, self.o_pwl, plot.Marker(math.nan), plot.Marker(math.nan), plot.Background(color.TRANSPARENT), plot.Background(color.TRANSPARENT)
        # ------------------------------------------------------------ MODULE 2/3
        STRONG = 0.30
        BRK_BODY = 0.5
        MINWICK = 0.3
        OTE_1 = 0.62
        OTE_2 = 0.79
        SB_ARM_GRACE = 5
        SB_MEM_EXTRA = 5
        SB_BE_TP1 = 0.15
        SB_LIQ_WAIT = 12
        SB_POI_WAIT = 8
        SB_RET_WAIT = 10
        SB_FVG_MIN = 0.10
        SB_BE_BUF = 0.15
        TRADE_BARS = 15
        o = self.open[0]
        h = self.high[0]
        l = self.low[0]
        c = self.close[0]
        t = self.time[0]
        o1 = self.open[1]
        h1 = self.high[1]
        l1 = self.low[1]
        c1 = self.close[1]
        tick = self.info.tick_size
        prec = self.info.price_precision
        tf_sec = float(self.time_frame.to_seconds())
        intraday = self.time_frame.to_seconds() < 86400
        atr = atr_raw_s[0]
        if atr_cap > 0 and (not isnan(atr_avg_s[0])) and atr_avg_s[0] > 0:
            atr = min(atr, atr_cap * atr_avg_s[0])
        if isnan(atr) or atr <= 0:
            atr = max(h - l, tick)
        spr = spread_ticks * tick
        hi_a = h + spr
        lo_a = l + spr
        body = abs(c - o)
        rng = h - l
        up_wick = h - max(o, c)
        dn_wick = min(o, c) - l
        bull = c > o
        bear = c < o
        body1 = abs(c1 - o1)
        bull1 = c1 > o1
        bear1 = c1 < o1
        bull_pin = rng > 0 and dn_wick >= 2 * body and up_wick <= body and dn_wick >= MINWICK * atr
        bear_pin = rng > 0 and up_wick >= 2 * body and dn_wick <= body and up_wick >= MINWICK * atr
        bull_eng = bull and bear1 and c >= o1 and o <= c1 and body > body1
        bear_eng = bear and bull1 and c <= o1 and o >= c1 and body > body1
        # CISD (strict consecutive delivery, latched once per run)
        cneut = rng == 0 or body <= 0.10 * rng
        cbull = bull and not cneut
        cbear = bear and not cneut
        new_bull = cbull and not self.prev_cisd_bull
        new_bear = cbear and not self.prev_cisd_bear
        if cneut:
            self.bull_run_open = math.nan
            self.bear_run_open = math.nan
            self.bull_run_len = 0
            self.bear_run_len = 0
        else:
            if new_bull:
                self.bull_run_open = o
                self.bull_run_len = 1
            elif cbull:
                self.bull_run_len += 1
            if new_bear:
                self.bear_run_open = o
                self.bear_run_len = 1
            elif cbear:
                self.bear_run_len += 1
        if new_bull:
            self.cisd_dn_done = False
        if new_bear:
            self.cisd_up_done = False
        cisd_dn = (not isnan(self.bull_run_open)) and (not self.cisd_dn_done) and cbear and c < self.bull_run_open and self.bull_run_len >= 2 and body >= BRK_BODY * atr and c <= l + STRONG * rng
        cisd_up = (not isnan(self.bear_run_open)) and (not self.cisd_up_done) and cbull and c > self.bear_run_open and self.bear_run_len >= 2 and body >= BRK_BODY * atr and c >= h - STRONG * rng
        if cisd_dn:
            self.cisd_dn_done = True
        if cisd_up:
            self.cisd_up_done = True
        self.prev_cisd_bull = cbull
        self.prev_cisd_bear = cbear
        # IFC
        prev_mid = (h1 + l1) / 2
        pool_l = min(self.low[1], self.low[2], self.low[3])
        pool_h = max(self.high[1], self.high[2], self.high[3])
        ifc_bull = l < pool_l and pool_l - l >= near_lvl * atr and bull and c > prev_mid and c >= h - STRONG * rng and body >= BRK_BODY * atr
        ifc_bear = h > pool_h and h - pool_h >= near_lvl * atr and bear and c < prev_mid and c <= l + STRONG * rng and body >= BRK_BODY * atr
        z_bull_conf = bull_pin or bull_eng or ifc_bull or cisd_up
        z_bear_conf = bear_pin or bear_eng or ifc_bear or cisd_dn
        # ------------------------------------------------------------ MODULE 4
        ph = piv_hi(self.high, piv_len, avail)
        pl = piv_lo(self.low, piv_len, avail)
        if not isnan(ph):
            if (not isnan(self.prev_ph)) and abs(ph - self.prev_ph) <= eq_tol * atr:
                lvl = max(ph, self.prev_ph)
                self.eqh_lvls.append(lvl)
                self.eqh_bars.append(bi)
                ln = LineSegment(AbsolutePosition(self.time[piv_len], lvl), AbsolutePosition(t, lvl), color=self.c_bear(0.75), line_style=line_style.DOTTED, line_width=2)
                self.eqh_lns.append(ln)
                if show_eq:
                    self.chart.draw(ln)
                if len(self.eqh_lvls) > 8:
                    if show_eq:
                        self.chart.erase(self.eqh_lns[0])
                    self.eqh_lns.pop(0)
                    self.eqh_lvls.pop(0)
                    self.eqh_bars.pop(0)
            if (not isnan(self.prev_ph)) and self.prev_ph_bar != NA and ph < self.prev_ph and (isnan(self.tl_dn_slope) or self.tl_dn_touch == 0):
                self.tl_dn_slope = (ph - self.prev_ph) / float(bi - piv_len - self.prev_ph_bar)
                self.tl_dn_price = ph
                self.tl_dn_bar = bi - piv_len
                self.tl_dn_touch = 0
                self.tl_dn_t0 = self.prev_ph_t
                self.tl_dn_p0 = self.prev_ph
                self.tl_dn_live = True
            self.prev_ph_bar = bi - piv_len
            self.prev_ph_t = self.time[piv_len]
            self.prev_ph = ph
            self.last_res = ph
            self.last_res_bar = bi - piv_len
            self.res_broken = False
            self.res_bos_done = False
        if not isnan(pl):
            if (not isnan(self.prev_pl)) and abs(pl - self.prev_pl) <= eq_tol * atr:
                lvl2 = min(pl, self.prev_pl)
                self.eql_lvls.append(lvl2)
                self.eql_bars.append(bi)
                ln2 = LineSegment(AbsolutePosition(self.time[piv_len], lvl2), AbsolutePosition(t, lvl2), color=self.c_bull(0.75), line_style=line_style.DOTTED, line_width=2)
                self.eql_lns.append(ln2)
                if show_eq:
                    self.chart.draw(ln2)
                if len(self.eql_lvls) > 8:
                    if show_eq:
                        self.chart.erase(self.eql_lns[0])
                    self.eql_lns.pop(0)
                    self.eql_lvls.pop(0)
                    self.eql_bars.pop(0)
            if (not isnan(self.prev_pl)) and self.prev_pl_bar != NA and pl > self.prev_pl and (isnan(self.tl_up_slope) or self.tl_up_touch == 0):
                self.tl_up_slope = (pl - self.prev_pl) / float(bi - piv_len - self.prev_pl_bar)
                self.tl_up_price = pl
                self.tl_up_bar = bi - piv_len
                self.tl_up_touch = 0
                self.tl_up_t0 = self.prev_pl_t
                self.tl_up_p0 = self.prev_pl
                self.tl_up_live = True
            self.prev_pl_bar = bi - piv_len
            self.prev_pl_t = self.time[piv_len]
            self.prev_pl = pl
            self.last_sup = pl
            self.last_sup_bar = bi - piv_len
            self.sup_broken = False
            self.sup_bos_done = False
        # ------------------------------------------------------------ MODULE 4B
        off = self.ny_off(t)
        lt = t + off * 3600.0
        ld = int(lt / 86400.0)
        ny_min = int((lt - ld * 86400.0) / 60.0)
        ny_wd = (ld + 3) % 7
        in_asia = intraday and in_win(ny_min, 1200, 1440)
        in_lon = intraday and in_win(ny_min, 120, 300)
        in_ny = intraday and in_win(ny_min, 420, 600)
        in_sblo = intraday and in_win(ny_min, 180, 240)
        in_sbam = intraday and in_win(ny_min, 600, 660)
        in_sbpm = intraday and in_win(ny_min, 840, 900)
        in_sb = in_sblo or in_sbam or in_sbpm
        in_kz = in_asia or in_lon or in_ny or in_sb
        kz_ok = (not use_kz) or (not intraday) or in_kz
        in_news = intraday and ((ny_wd <= 4 and (in_win(ny_min, 505, 525) or in_win(ny_min, 595, 610))) or (ny_wd == 2 and in_win(ny_min, 835, 875)))
        sb_pre_lo = intraday and (not in_sblo) and ny_min < 180 and 180 - ny_min <= sb_pre_min
        sb_pre_am = intraday and (not in_sbam) and ny_min < 600 and 600 - ny_min <= sb_pre_min
        sb_pre_pm = intraday and (not in_sbpm) and ny_min < 840 and 840 - ny_min <= sb_pre_min
        sb_win_now = 0
        if in_sbam:
            sb_win_now = 2
        elif in_sblo:
            sb_win_now = 1
        elif in_sbpm:
            sb_win_now = 3
        sb_ctx_win = sb_win_now
        if sb_ctx_win == 0:
            if sb_pre_am:
                sb_ctx_win = 2
            elif sb_pre_lo:
                sb_ctx_win = 1
            elif sb_pre_pm:
                sb_ctx_win = 3
        sb_on = sb_enable and intraday
        sb_active = sb_on and sb_win_now != 0
        sb_ctx = sb_on and sb_ctx_win != 0
        news_ok = (not use_news) or (not intraday) or (not in_news) or (sb_active and sb_win_now == 2)
        sb_end_lo = sb_on and (not in_sblo) and self.in_sblo_prev
        sb_end_am = sb_on and (not in_sbam) and self.in_sbam_prev
        sb_end_pm = sb_on and (not in_sbpm) and self.in_sbpm_prev
        self.in_sblo_prev = in_sblo
        self.in_sbam_prev = in_sbam
        self.in_sbpm_prev = in_sbpm
        sb_win_pts = 0
        sb_min_qual = 4
        if sb_ctx_win == 2:
            sb_win_pts = 6
            sb_min_qual = sb_qual_am
        elif sb_ctx_win == 3:
            sb_win_pts = 5
            sb_min_qual = sb_qual_pm
        elif sb_ctx_win == 1:
            sb_win_pts = 4
            sb_min_qual = sb_qual_lo
        dow_ok = (not intraday) or ny_wd <= 4
        # ------------------------------------------------------------ MODULE 5
        if (not isnan(self.ssl_spent)) and abs(c - self.ssl_spent) > sweep_ctx * atr:
            self.ssl_spent = math.nan
        if (not isnan(self.bsl_spent)) and abs(c - self.bsl_spent) > sweep_ctx * atr:
            self.bsl_spent = math.nan
        ssl_fresh = isnan(self.ssl_spent) or ((not isnan(self.last_sup)) and abs(self.last_sup - self.ssl_spent) > near_lvl * atr)
        bsl_fresh = isnan(self.bsl_spent) or ((not isnan(self.last_res)) and abs(self.last_res - self.bsl_spent) > near_lvl * atr)
        ssl_recl = reclaim_bars > 0 and self.sup_broken and self.sup_brk_bar != NA and bi - self.sup_brk_bar <= reclaim_bars and (not isnan(self.last_sup)) and c > self.last_sup
        bsl_recl = reclaim_bars > 0 and self.res_broken and self.res_brk_bar != NA and bi - self.res_brk_bar <= reclaim_bars and (not isnan(self.last_res)) and c < self.last_res
        ssl_ext = l
        if ssl_recl:
            ssl_ext = min(l, self.ll(min(avail, max(1, bi - self.sup_brk_bar + 1))))
        bsl_ext = h
        if bsl_recl:
            bsl_ext = max(h, self.hh(min(avail, max(1, bi - self.res_brk_bar + 1))))
        ssl_sweep = (not isnan(self.last_sup)) and ((l < self.last_sup and c > self.last_sup and not self.sup_broken) or ssl_recl) and ssl_fresh
        bsl_sweep = (not isnan(self.last_res)) and ((h > self.last_res and c < self.last_res and not self.res_broken) or bsl_recl) and bsl_fresh
        if ssl_sweep:
            q_s = self.sweep_q(True, self.last_sup, h, l, c, rng, body, atr, near_lvl)
            k_s = 1
            if self.recent(self.last_ssl_bar, sweep_look) and self.ssl_kind >= 2 and abs(self.last_sup - self.last_ssl_lvl) <= near_lvl * atr:
                k_s = self.ssl_kind
            self.stamp_ssl(q_s, self.last_sup, ssl_ext, k_s, bi)
            self.ssl_spent = self.last_sup
        if bsl_sweep:
            q_b = self.sweep_q(False, self.last_res, h, l, c, rng, body, atr, near_lvl)
            k_b = 1
            if self.recent(self.last_bsl_bar, sweep_look) and self.bsl_kind >= 2 and abs(self.last_res - self.last_bsl_lvl) <= near_lvl * atr:
                k_b = self.bsl_kind
            self.stamp_bsl(q_b, self.last_res, bsl_ext, k_b, bi)
            self.bsl_spent = self.last_res
        # EQ pools: Judas sweep vs real break; age-out
        eqh_swept = False
        eql_swept = False
        for i in range(len(self.eqh_lvls) - 1, -1, -1):
            lv = self.eqh_lvls[i]
            if h > lv or bi - self.eqh_bars[i] > eq_max_age:
                if h > lv and c < lv:
                    eqh_swept = True
                    self.stamp_bsl(self.pool_q(False, lv, h, l, c, rng, body, atr, near_lvl), lv, h, 2, bi)
                if show_eq:
                    self.chart.erase(self.eqh_lns[i])
                self.eqh_lns.pop(i)
                self.eqh_lvls.pop(i)
                self.eqh_bars.pop(i)
        for i in range(len(self.eql_lvls) - 1, -1, -1):
            lv = self.eql_lvls[i]
            if l < lv or bi - self.eql_bars[i] > eq_max_age:
                if l < lv and c > lv:
                    eql_swept = True
                    self.stamp_ssl(self.pool_q(True, lv, h, l, c, rng, body, atr, near_lvl), lv, l, 2, bi)
                if show_eq:
                    self.chart.erase(self.eql_lns[i])
                self.eql_lns.pop(i)
                self.eql_lvls.pop(i)
                self.eql_bars.pop(i)
        # previous day / week (00:00 UTC day, Monday week)
        day_id = int(t / 86400.0)
        week_id = (day_id + 3) // 7
        self.new_day = False
        if day_id != self.day_id:
            if self.day_id >= 0 and not isnan(self.day_hi):
                self.pdh = self.day_hi
                self.pdl = self.day_lo
                self.day_ranges.append(self.day_hi - self.day_lo)
                d_alpha = 2.0 / (bias_len + 1.0)
                if isnan(self.d_ema):
                    self.d_ema = c1
                else:
                    self.d_ema = self.d_ema + d_alpha * (c1 - self.d_ema)
                self.d_bias = 1 if c1 > self.d_ema else -1
                if len(self.day_ranges) > 10:
                    self.day_ranges.pop(0)
                self.pdh_done = False
                self.pdl_done = False
            self.day_id = day_id
            self.day_hi = h
            self.day_lo = l
            self.new_day = True
        else:
            self.day_hi = max(self.day_hi, h)
            self.day_lo = min(self.day_lo, l)
        if week_id != self.week_id:
            if self.week_id >= 0 and not isnan(self.week_hi):
                self.pwh = self.week_hi
                self.pwl = self.week_lo
                self.pwh_done = False
                self.pwl_done = False
            self.week_id = week_id
            self.week_hi = h
            self.week_lo = l
        else:
            self.week_hi = max(self.week_hi, h)
            self.week_lo = min(self.week_lo, l)
        pdh = self.pdh
        pdl = self.pdl
        pwh = self.pwh
        pwl = self.pwl
        pdh_sw = (not isnan(pdh)) and h > pdh and c < pdh and not self.pdh_done
        pdl_sw = (not isnan(pdl)) and l < pdl and c > pdl and not self.pdl_done
        pwh_sw = (not isnan(pwh)) and h > pwh and c < pwh and not self.pwh_done
        pwl_sw = (not isnan(pwl)) and l < pwl and c > pwl and not self.pwl_done
        if (not isnan(pdh)) and h > pdh:
            self.pdh_done = True
        if (not isnan(pdl)) and l < pdl:
            self.pdl_done = True
        if (not isnan(pwh)) and h > pwh:
            self.pwh_done = True
        if (not isnan(pwl)) and l < pwl:
            self.pwl_done = True
        if pdh_sw or pwh_sw:
            lv_h = pdh if pdh_sw else pwh
            self.stamp_bsl(self.pool_q(False, lv_h, h, l, c, rng, body, atr, near_lvl), lv_h, h, 3, bi)
        if pdl_sw or pwl_sw:
            lv_l = pdl if pdl_sw else pwl
            self.stamp_ssl(self.pool_q(True, lv_l, h, l, c, rng, body, atr, near_lvl), lv_l, l, 3, bi)
        # per-session liquidity (0 Asia · 1 London · 2 NY)
        act: list[bool] = [in_asia, in_lon, in_ny]
        hi_raid: list[bool] = [False, False, False]
        lo_raid: list[bool] = [False, False, False]
        for s in range(3):
            a = act[s]
            if a:
                if not self.s_act_prev[s]:
                    self.s_hi[s] = h
                    self.s_lo[s] = l
                else:
                    self.s_hi[s] = max(self.s_hi[s], h)
                    self.s_lo[s] = min(self.s_lo[s], l)
            if (not a) and self.s_act_prev[s] and not isnan(self.s_hi[s]):
                self.s_hi_lvl[s] = self.s_hi[s]
                self.s_lo_lvl[s] = self.s_lo[s]
                self.s_hi_sw[s] = False
                self.s_lo_sw[s] = False
                self.ses_lines_new(s, t, show_ses)
            if self.s_hi_sw[s] and (not isnan(self.s_hi_lvl[s])) and c < self.s_hi_lvl[s] - atr:
                self.s_hi_sw[s] = False
            if self.s_lo_sw[s] and (not isnan(self.s_lo_lvl[s])) and c > self.s_lo_lvl[s] + atr:
                self.s_lo_sw[s] = False
            if (not a) and (not isnan(self.s_hi_lvl[s])) and (not self.s_hi_sw[s]) and h > self.s_hi_lvl[s]:
                self.s_hi_sw[s] = True
                hi_raid[s] = c <= self.s_hi_lvl[s]
                self.s_hi_end_t[s] = t
                self.ses_tag(s, True, ' H raided' if hi_raid[s] else ' H broken', show_ses)
            if (not a) and (not isnan(self.s_lo_lvl[s])) and (not self.s_lo_sw[s]) and l < self.s_lo_lvl[s]:
                self.s_lo_sw[s] = True
                lo_raid[s] = c >= self.s_lo_lvl[s]
                self.s_lo_end_t[s] = t
                self.ses_tag(s, False, ' L raided' if lo_raid[s] else ' L broken', show_ses)
            self.s_act_prev[s] = a
        ses_hi_swept = hi_raid[0] or hi_raid[1] or hi_raid[2]
        ses_lo_swept = lo_raid[0] or lo_raid[1] or lo_raid[2]
        if lo_raid[1] or lo_raid[2]:
            lv_sl = self.s_lo_lvl[1] if lo_raid[1] else self.s_lo_lvl[2]
            self.stamp_ssl(self.pool_q(True, lv_sl, h, l, c, rng, body, atr, near_lvl), lv_sl, l, 4, bi)
        if hi_raid[1] or hi_raid[2]:
            lv_sh = self.s_hi_lvl[1] if hi_raid[1] else self.s_hi_lvl[2]
            self.stamp_bsl(self.pool_q(False, lv_sh, h, l, c, rng, body, atr, near_lvl), lv_sh, h, 4, bi)
        if sb_ctx:
            if lo_raid[0] and not (lo_raid[1] or lo_raid[2]):
                self.stamp_ssl(self.pool_q(True, self.s_lo_lvl[0], h, l, c, rng, body, atr, near_lvl), self.s_lo_lvl[0], l, 4, bi)
            if hi_raid[0] and not (hi_raid[1] or hi_raid[2]):
                self.stamp_bsl(self.pool_q(False, self.s_hi_lvl[0], h, l, c, rng, body, atr, near_lvl), self.s_hi_lvl[0], h, 4, bi)
        if eql_swept or ses_lo_swept or pdl_sw or pwl_sw:
            self.last_eng_lo_bar = bi
        if eqh_swept or ses_hi_swept or pdh_sw or pwh_sw:
            self.last_eng_hi_bar = bi
        recent_eng_lo = self.recent(self.last_eng_lo_bar, sweep_look)
        recent_eng_hi = self.recent(self.last_eng_hi_bar, sweep_look)
        sb_mem = sweep_look + SB_MEM_EXTRA if sb_ctx else sweep_look
        recent_ssl = self.recent(self.last_ssl_bar, sb_mem)
        recent_bsl = self.recent(self.last_bsl_bar, sb_mem)
        ssl_in_play = recent_ssl and (not isnan(self.last_ssl_lvl)) and c > self.last_ssl_lvl and c - self.last_ssl_lvl <= sweep_ctx * atr
        bsl_in_play = recent_bsl and (not isnan(self.last_bsl_lvl)) and c < self.last_bsl_lvl and self.last_bsl_lvl - c <= sweep_ctx * atr
        broke_up = (not isnan(self.last_res)) and (not self.res_broken) and c > self.last_res
        broke_dn = (not isnan(self.last_sup)) and (not self.sup_broken) and c < self.last_sup
        if broke_up:
            self.res_broken = True
            self.res_brk_bar = bi
        if broke_dn:
            self.sup_broken = True
            self.sup_brk_bar = bi
        disp_close = body >= struct_disp * atr
        broke_up_s = (not isnan(self.last_res)) and (not self.res_bos_done) and c > self.last_res
        broke_dn_s = (not isnan(self.last_sup)) and (not self.sup_bos_done) and c < self.last_sup
        if broke_up_s and disp_close:
            self.res_bos_done = True
        if broke_dn_s and disp_close:
            self.sup_bos_done = True
        # ------------------------------------------------------------ MODULE 6
        bos_up, bos_dn, ch_up, ch_dn = self.struct_step(0, broke_up_s, broke_dn_s, disp_close, h, l, c)
        eph = piv_hi(self.high, ext_piv, avail)
        epl = piv_lo(self.low, ext_piv, avail)
        if not isnan(eph):
            self.ext_res = eph
            self.ext_res_bar = bi - ext_piv
            self.ext_res_bos_done = False
        if not isnan(epl):
            self.ext_sup = epl
            self.ext_sup_bar = bi - ext_piv
            self.ext_sup_bos_done = False
        e_up_s = (not isnan(self.ext_res)) and (not self.ext_res_bos_done) and c > self.ext_res
        e_dn_s = (not isnan(self.ext_sup)) and (not self.ext_sup_bos_done) and c < self.ext_sup
        if e_up_s and disp_close:
            self.ext_res_bos_done = True
        if e_dn_s and disp_close:
            self.ext_sup_bos_done = True
        ebos_up, ebos_dn, ech_up, ech_dn = self.struct_step(1, e_up_s, e_dn_s, disp_close, h, l, c)
        ms_dir = self.st_dir[0]
        ext_dir = self.st_dir[1]
        prot_low_e = self.st_plo[1]
        prot_high_e = self.st_phi[1]
        mss_up = (ech_up or ((not mss_need_ext) and ch_up)) and ssl_in_play and self.ssl_q >= 2
        mss_dn = (ech_dn or ((not mss_need_ext) and ch_dn)) and bsl_in_play and self.bsl_q >= 2
        if mss_up and self.recent(self.last_ssl_bar, trig_look):
            self.ssl_q = 4
        if mss_dn and self.recent(self.last_bsl_bar, trig_look):
            self.bsl_q = 4
        if ch_up or ech_up:
            self.l_ch_up = bi
        if ch_dn or ech_dn:
            self.l_ch_dn = bi
        if bos_up or ebos_up:
            self.l_bos_up = bi
        if bos_dn or ebos_dn:
            self.l_bos_dn = bi
        if mss_up:
            self.l_mss_up = bi
        if mss_dn:
            self.l_mss_dn = bi
        if cisd_up:
            self.l_cisd_up = bi
        if cisd_dn:
            self.l_cisd_dn = bi
        if ebos_up:
            self.l_ebos_up = bi
        if ebos_dn:
            self.l_ebos_dn = bi
        if ech_up:
            self.l_ech_up = bi
        if ech_dn:
            self.l_ech_dn = bi
        recent_ch_up = self.recent(self.l_ch_up, trig_look)
        recent_ch_dn = self.recent(self.l_ch_dn, trig_look)
        recent_mss_up = self.recent(self.l_mss_up, trig_look)
        recent_mss_dn = self.recent(self.l_mss_dn, trig_look)
        recent_cisd_up = self.recent(self.l_cisd_up, trig_look)
        recent_cisd_dn = self.recent(self.l_cisd_dn, trig_look)
        recent_struct_up = recent_ch_up or self.recent(self.l_bos_up, trig_look)
        recent_struct_dn = recent_ch_dn or self.recent(self.l_bos_dn, trig_look)
        if show_struct:
            major_u = mss_up or ech_up or ebos_up
            if major_u or (show_int_struct and (ch_up or bos_up)):
                txt_u = 'MSS' if mss_up else ('CHoCH' if ech_up else ('BOS' if ebos_up else ('iCHoCH' if ch_up else 'iBOS')))
                self.mark(txt_u, t, l - 0.4 * atr, self.c_bull(0.9) if major_u else color.rgba(70, 76, 90, 0.9), color.WHITE, self.lf if major_u else self.lf - 1)
            major_d = mss_dn or ech_dn or ebos_dn
            if major_d or (show_int_struct and (ch_dn or bos_dn)):
                txt_d = 'MSS' if mss_dn else ('CHoCH' if ech_dn else ('BOS' if ebos_dn else ('iCHoCH' if ch_dn else 'iBOS')))
                self.mark(txt_d, t, h + 0.4 * atr, self.c_bear(0.9) if major_d else color.rgba(70, 76, 90, 0.9), color.WHITE, self.lf if major_d else self.lf - 1)
        # ------------------------------------------------------------ MODULE 7
        ema_bias = 0
        if not isnan(self._hb[0]):
            ema_bias = int(self._hb[0])
        hs_dir = 0
        if not isnan(self._hd[0]):
            hs_dir = int(self._hd[0])
        hs_prot_lo = self._hplo[0]
        hs_prot_hi = self._hphi[0]
        htf_b = ema_bias
        if bias_mode == 'Structure only':
            htf_b = hs_dir if hs_dir != 0 else ema_bias
        elif bias_mode == 'Structure + EMA':
            if hs_dir == 0:
                htf_b = ema_bias
            elif hs_dir == ema_bias:
                htf_b = hs_dir
            else:
                htf_b = 0
        follow = neutral_mode == 'Follow chart structure'
        allow_both = neutral_mode == 'Allow both'
        bias_ok_l = (not bias_on) or htf_b > 0 or (htf_b == 0 and (allow_both or (follow and ext_dir >= 0)))
        bias_ok_s = (not bias_on) or htf_b < 0 or (htf_b == 0 and (allow_both or (follow and ext_dir <= 0)))
        arm_bias_l = bias_ok_l or (htf_b == 0 and follow)
        arm_bias_s = bias_ok_s or (htf_b == 0 and follow)
        # ------------------------------------------------------------ MODULE 9 (ADR)
        adr = math.nan
        if len(self.day_ranges) >= 10:
            adr = sum(self.day_ranges) / float(len(self.day_ranges))
        day_rng = self.day_hi - self.day_lo
        adr_exh = intraday and (not isnan(adr)) and adr > 0 and day_rng / adr >= 1.2
        adr_pos = (c - self.day_lo) / day_rng if day_rng > 0 else 0.5
        adr_chase_l = adr_exh and adr_pos >= 0.7
        adr_chase_s = adr_exh and adr_pos <= 0.3
        # ------------------------------------------------------------ MODULE 10
        a1 = bi if self.ext_res_bar == NA else self.ext_res_bar
        a2 = bi if self.ext_sup_bar == NA else self.ext_sup_bar
        dr_len = max(5, min(500, bi - min(a1, a2) + 1))
        dr_len = min(dr_len, avail)
        dr_start = bi - dr_len + 1
        rescan = self.dr_start == NA or dr_start < self.dr_start or dr_start > self.dr_start + 1 or self.dr_hi_bar < dr_start or self.dr_lo_bar < dr_start
        if rescan:
            self.dr_hi = h
            self.dr_lo = l
            self.dr_hi_bar = bi
            self.dr_lo_bar = bi
            for k in range(1, dr_len):
                if self.high[k] > self.dr_hi:
                    self.dr_hi = self.high[k]
                    self.dr_hi_bar = bi - k
                if self.low[k] < self.dr_lo:
                    self.dr_lo = self.low[k]
                    self.dr_lo_bar = bi - k
        else:
            if h >= self.dr_hi:
                self.dr_hi = h
                self.dr_hi_bar = bi
            if l <= self.dr_lo:
                self.dr_lo = l
                self.dr_lo_bar = bi
        self.dr_start = dr_start
        rng_hi = self.dr_hi
        rng_lo = self.dr_lo
        hi_k = bi - self.dr_hi_bar
        lo_k = bi - self.dr_lo_bar
        range_ok = rng_hi > rng_lo
        range_holds = range_ok and (rng_hi - rng_lo) >= 2 * atr
        bull_range = range_ok and hi_k < lo_k
        bear_range = range_ok and lo_k < hi_k
        rng_w = rng_hi - rng_lo
        pd_pos = 0.5
        if range_ok:
            pd_pos = min(1.0, max(0.0, (c - rng_lo) / rng_w))
        in_ote_buy = bull_range and c <= rng_hi - OTE_1 * rng_w and c >= rng_hi - OTE_2 * rng_w
        in_ote_sell = bear_range and c >= rng_lo + OTE_1 * rng_w and c <= rng_lo + OTE_2 * rng_w
        if sb_on:
            if sb_win_now != 0 and self.sb_win_prev != sb_win_now:
                self.sb_rng_hi = rng_hi
                self.sb_rng_lo = rng_lo
                self.sb_rng_win = sb_win_now
            elif sb_win_now == 0 and self.sb_rng_win != 0 and not self.sb_set_live:
                self.sb_rng_hi = math.nan
                self.sb_rng_lo = math.nan
                self.sb_rng_win = 0
        self.sb_win_prev = sb_win_now
        sb_rng_ok = (not isnan(self.sb_rng_hi)) and (not isnan(self.sb_rng_lo)) and self.sb_rng_hi > self.sb_rng_lo
        sb_pd_ok = sb_rng_ok or range_ok
        sb_pd_pos = pd_pos
        if sb_rng_ok:
            raw = (c - self.sb_rng_lo) / (self.sb_rng_hi - self.sb_rng_lo)
            if raw >= -0.15 and raw <= 1.15:
                sb_pd_pos = min(1.0, max(0.0, raw))
        # ------------------------------------------------------------ MODULE 11
        reg_ebos_up = self.recent(self.l_ebos_up, regime_look)
        reg_ebos_dn = self.recent(self.l_ebos_dn, regime_look)
        reg_ech_up = self.recent(self.l_ech_up, regime_look)
        reg_ech_dn = self.recent(self.l_ech_dn, regime_look)
        reg_trending = (ext_dir == 1 and reg_ebos_up and not reg_ech_dn) or (ext_dir == -1 and reg_ebos_dn and not reg_ech_up)
        reg_transition = (not reg_trending) and (reg_ech_up or reg_ech_dn)
        ext_ok = (not isnan(self.ext_res)) and (not isnan(self.ext_sup))
        ext_rng_atr = abs(self.ext_res - self.ext_sup) / atr if ext_ok else math.nan
        leg_rng_atr = rng_w / atr
        in_ext_rng = ext_ok and c <= max(self.ext_res, self.ext_sup) and c >= min(self.ext_res, self.ext_sup)
        reg_thrust = avail > regime_look and abs(c - self.close[regime_look]) >= chop_rng * atr
        reg_chop = (not reg_trending) and (not reg_transition) and (not reg_thrust) and (not isnan(ext_rng_atr)) and ext_rng_atr < chop_rng and leg_rng_atr < chop_rng and in_ext_rng
        regime = 'TRENDING' if reg_trending else ('TRANSITION' if reg_transition else ('CHOP' if reg_chop else 'RANGING'))
        inst_sweep_l = self.ssl_q_raw >= 3 and recent_mss_up
        inst_sweep_s = self.bsl_q_raw >= 3 and recent_mss_dn
        # ------------------------------------------------------------ MODULE 12
        bull_fvg = l - self.high[2] >= min_zone * atr
        bear_fvg = self.low[2] - h >= min_zone * atr
        inv_sup_top = math.nan
        inv_sup_bot = math.nan
        inv_dem_top = math.nan
        inv_dem_bot = math.nan
        if bull_fvg:
            self.fvg_add(True, Fvg(l, self.high[2], bi, True, False, False, self.time[2]), fvg_keep, show_fvg, t)
        if bear_fvg:
            self.fvg_add(False, Fvg(self.low[2], h, bi, False, False, False, self.time[2]), fvg_keep, show_fvg, t)
        for i in range(len(self.bfv) - 1, -1, -1):
            f = self.bfv[i]
            if bi > f.bar_created:
                if l <= f.top and not f.partial:
                    f.partial = True
                if use_ifvg and c < f.bot and not f.inverted:
                    f.inverted = True
                    f.is_bull = False
                    f.partial = False
                    f.bar_created = bi
                    inv_sup_top = f.top
                    inv_sup_bot = f.bot
                    rx = self.bfx[i]
                    rx.line_color = self.c_bear(0.55)
                    rx.bg_color = self.c_bear(0.08)
                    self.bfv.pop(i)
                    self.bfx.pop(i)
                    self.sfv.append(f)
                    self.sfx.append(rx)
                    if len(self.sfv) > fvg_keep:
                        if show_fvg:
                            self.chart.erase(self.sfx[0])
                        self.sfv.pop(0)
                        self.sfx.pop(0)
                elif c < f.bot or l <= f.bot or bi - f.bar_created > fvg_age:
                    if show_fvg:
                        self.chart.erase(self.bfx[i])
                    self.bfv.pop(i)
                    self.bfx.pop(i)
        for i in range(len(self.sfv) - 1, -1, -1):
            f2 = self.sfv[i]
            if bi > f2.bar_created:
                if h >= f2.bot and not f2.partial:
                    f2.partial = True
                if use_ifvg and c > f2.top and not f2.inverted:
                    f2.inverted = True
                    f2.is_bull = True
                    f2.partial = False
                    f2.bar_created = bi
                    inv_dem_top = f2.top
                    inv_dem_bot = f2.bot
                    rx2 = self.sfx[i]
                    rx2.line_color = self.c_bull(0.55)
                    rx2.bg_color = self.c_bull(0.08)
                    self.sfv.pop(i)
                    self.sfx.pop(i)
                    self.bfv.append(f2)
                    self.bfx.append(rx2)
                    if len(self.bfv) > fvg_keep:
                        if show_fvg:
                            self.chart.erase(self.bfx[0])
                        self.bfv.pop(0)
                        self.bfx.pop(0)
                elif c > f2.top or h >= f2.top or bi - f2.bar_created > fvg_age:
                    if show_fvg:
                        self.chart.erase(self.sfx[i])
                    self.sfv.pop(i)
                    self.sfx.pop(i)
        if bull_fvg:
            self.cfb_top = l
            self.cfb_bot = self.high[2]
            self.cfb_bar = bi
            self.cfb_disp = bull1 and body1 >= min(disp_fact, sb_disp) * atr
        if (not isnan(self.cfb_bot)) and c < self.cfb_bot:
            self.cfb_top = math.nan
            self.cfb_bot = math.nan
            self.cfb_bar = NA
        if bear_fvg:
            self.cfs_bot = h
            self.cfs_top = self.low[2]
            self.cfs_bar = bi
            self.cfs_disp = bear1 and body1 >= min(disp_fact, sb_disp) * atr
        if (not isnan(self.cfs_top)) and c > self.cfs_top:
            self.cfs_top = math.nan
            self.cfs_bot = math.nan
            self.cfs_bar = NA
        # ------------------------------------------------------------ MODULE 13
        sig_sd_long = False
        sig_sd_short = False
        sl_sd_long = math.nan
        sl_sd_short = math.nan
        flip_top = math.nan
        flip_bot = math.nan
        flip_sup = False
        for i in range(len(self.zones) - 1, -1, -1):
            z = self.zones[i]
            mid = (z.top + z.bot) / 2
            if z.is_supply:
                if c > z.top:
                    if show_flip and not z.flipped:
                        self.zone_flip(i, False, recent_ssl and recent_struct_up)
                        flip_top = z.top
                        flip_bot = z.bot
                        flip_sup = False
                    else:
                        self.zone_del(i)
                    continue
                in_z = h >= z.bot
                if in_z and not z.touched:
                    z.touch_bar = bi
                z.touched = in_z or z.touched
                if in_z and not z.was_in:
                    z.tests += 1
                    if z.tests > zone_tests and not z.signaled:
                        z.signaled = True
                        self.zbx[i].bg_color = self.c_bear(0.03)
                z.was_in = in_z
                if h < z.bot:
                    z.tapped50 = False
                if h >= mid and not z.tapped50:
                    z.tapped50 = True
                    z.tap50_bar = bi
                if (not z.signaled) and z.tapped50 and bi - z.tap50_bar <= confirm_win and z_bear_conf and h >= z.bot:
                    sig_sd_short = True
                    sl_sd_short = max(h, z.top) + sl_pad * atr
                    z.signaled = True
                    self.zbx[i].bg_color = self.c_bear(0.05)
            else:
                if c < z.bot:
                    if show_flip and not z.flipped:
                        self.zone_flip(i, True, recent_bsl and recent_struct_dn)
                        flip_top = z.top
                        flip_bot = z.bot
                        flip_sup = True
                    else:
                        self.zone_del(i)
                    continue
                in_zd = l <= z.top
                if in_zd and not z.touched:
                    z.touch_bar = bi
                z.touched = in_zd or z.touched
                if in_zd and not z.was_in:
                    z.tests += 1
                    if z.tests > zone_tests and not z.signaled:
                        z.signaled = True
                        self.zbx[i].bg_color = self.c_bull(0.03)
                z.was_in = in_zd
                if l > z.top:
                    z.tapped50 = False
                if l <= mid and not z.tapped50:
                    z.tapped50 = True
                    z.tap50_bar = bi
                if (not z.signaled) and z.tapped50 and bi - z.tap50_bar <= confirm_win and z_bull_conf and l <= z.top:
                    sig_sd_long = True
                    sl_sd_long = min(l, z.bot) - sl_pad * atr
                    z.signaled = True
                    self.zbx[i].bg_color = self.c_bull(0.05)
        if not isnan(flip_top):
            self.claim_band(flip_sup, flip_top, flip_bot, min_zone * atr)
        # creation: S/D (imbalance geometry) + OB companion
        disp_up = bull1 and body1 >= disp_fact * atr
        disp_dn = bear1 and body1 >= disp_fact * atr
        new_dem = show_zones and bull_fvg and disp_up
        new_sup = show_zones and bear_fvg and disp_dn
        created = False
        if new_dem:
            z_top = l
            z_bot = max(self.high[2], l - max_zone_atr * atr)
            bs = self.res_brk_bar != NA and self.res_brk_bar >= bi - 1
            new_score = 3 if bs else 2
            dup = False
            for i in range(len(self.zones) - 1, -1, -1):
                zz = self.zones[i]
                if (not zz.is_supply) and not (z_bot > zz.top or z_top < zz.bot):
                    if zz.score >= new_score and not zz.signaled:
                        dup = True
                    else:
                        self.zone_del(i)
            if (not dup) and z_top - z_bot >= min_zone * atr:
                self.claim_band(False, z_top, z_bot, min_zone * atr)
                self.zone_add(False, z_top, z_bot, bs, 'SD', 'DEMAND HP' if bs else 'DEMAND', self.time[2], t)
                created = True
                if show_ob and self.close[2] < self.open[2]:
                    ob_top = self.high[2]
                    ob_bot = max(self.low[2], self.high[2] - max_zone_atr * atr)
                    if ob_top - ob_bot >= min_zone * atr:
                        self.claim_band(False, ob_top, ob_bot, min_zone * atr)
                        self.zone_add(False, ob_top, ob_bot, False, 'OB', 'OB', self.time[2], t)
        if new_sup:
            s_bot = h
            s_top = min(self.low[2], h + max_zone_atr * atr)
            bs2 = self.sup_brk_bar != NA and self.sup_brk_bar >= bi - 1
            new_score2 = 3 if bs2 else 2
            dup2 = False
            for i in range(len(self.zones) - 1, -1, -1):
                zs = self.zones[i]
                if zs.is_supply and not (s_bot > zs.top or s_top < zs.bot):
                    if zs.score >= new_score2 and not zs.signaled:
                        dup2 = True
                    else:
                        self.zone_del(i)
            if (not dup2) and s_top - s_bot >= min_zone * atr:
                self.claim_band(True, s_top, s_bot, min_zone * atr)
                self.zone_add(True, s_top, s_bot, bs2, 'SD', 'SUPPLY HP' if bs2 else 'SUPPLY', self.time[2], t)
                created = True
                if show_ob and self.close[2] > self.open[2]:
                    ob_bot2 = self.low[2]
                    ob_top2 = min(self.high[2], self.low[2] + max_zone_atr * atr)
                    if ob_top2 - ob_bot2 >= min_zone * atr:
                        self.claim_band(True, ob_top2, ob_bot2, min_zone * atr)
                        self.zone_add(True, ob_top2, ob_bot2, False, 'OB', 'OB', self.time[2], t)
        # rejection blocks
        if show_rb and avail > 3 * piv_len + 2:
            if not isnan(ph):
                hp = self.high[piv_len]
                prior_hi = self.high[piv_len + 1]
                for k in range(piv_len + 1, 3 * piv_len + 1):
                    prior_hi = max(prior_hi, self.high[k])
                swp_h = hp > prior_hi
                dsp_h = self.ll(piv_len) <= hp - disp_fact * atr
                rb_top = hp
                rb_bot = max(self.open[piv_len], self.close[piv_len])
                if rb_top - rb_bot >= MINWICK * atr and swp_h and dsp_h and not self.zone_overlap(True, rb_top, rb_bot):
                    self.claim_band(True, rb_top, rb_bot, min_zone * atr)
                    self.zone_add(True, rb_top, rb_bot, False, 'RB', 'RB', self.time[piv_len], t)
                    created = True
            if not isnan(pl):
                lp = self.low[piv_len]
                prior_lo = self.low[piv_len + 1]
                for k in range(piv_len + 1, 3 * piv_len + 1):
                    prior_lo = min(prior_lo, self.low[k])
                swp_l = lp < prior_lo
                dsp_l = self.hh(piv_len) >= lp + disp_fact * atr
                rb_bot2 = lp
                rb_top2 = min(self.open[piv_len], self.close[piv_len])
                if rb_top2 - rb_bot2 >= MINWICK * atr and swp_l and dsp_l and not self.zone_overlap(False, rb_top2, rb_bot2):
                    self.claim_band(False, rb_top2, rb_bot2, min_zone * atr)
                    self.zone_add(False, rb_top2, rb_bot2, False, 'RB', 'RB', self.time[piv_len], t)
                    created = True
        # IFVG -> POI zone
        if use_ifvg:
            if (not isnan(inv_sup_top)) and (not self.zone_overlap(True, inv_sup_top, inv_sup_bot)) and inv_sup_top - inv_sup_bot >= min_zone * atr:
                self.claim_band(True, inv_sup_top, inv_sup_bot, min_zone * atr)
                self.zone_add(True, inv_sup_top, inv_sup_bot, False, 'IFVG', 'IFVG', self.time[2], t)
                created = True
            if (not isnan(inv_dem_top)) and (not self.zone_overlap(False, inv_dem_top, inv_dem_bot)) and inv_dem_top - inv_dem_bot >= min_zone * atr:
                self.claim_band(False, inv_dem_top, inv_dem_bot, min_zone * atr)
                self.zone_add(False, inv_dem_top, inv_dem_bot, False, 'IFVG', 'IFVG', self.time[2], t)
                created = True
        if created:
            d_keep = 0
            s_keep = 0
            d_rb = 0
            s_rb = 0
            for i in range(len(self.zones) - 1, -1, -1):
                zc = self.zones[i]
                drop = False
                if zc.is_supply:
                    s_keep += 1
                    if zc.kind == 'RB':
                        s_rb += 1
                    drop = s_keep > max_zones or (zc.kind == 'RB' and s_rb > 2)
                else:
                    d_keep += 1
                    if zc.kind == 'RB':
                        d_rb += 1
                    drop = d_keep > max_zones or (zc.kind == 'RB' and d_rb > 2)
                if drop:
                    self.zone_del(i)
        # ---- MODULE 9 · HTF FVG POI (closed HTF candles aggregated from chart bars)
        ch_min = self.time_frame.to_minutes()
        p_min = 1440
        if poi_tf == 'Auto':
            if ch_min <= 1:
                p_min = 15
            elif ch_min <= 3:
                p_min = 30
            elif ch_min <= 5:
                p_min = 60
            elif ch_min <= 10:
                p_min = 120
            elif ch_min <= 30:
                p_min = 240
        elif poi_tf != 'D':
            p_min = int(poi_tf)
        htf_live = p_min > ch_min
        self.d_htf_lbl = 'D' if p_min >= 1440 else str(p_min)
        bucket = int(t / (p_min * 60.0))
        if htf_live:
            if bucket != self.h_bucket:
                if self.h_bucket >= 0 and not isnan(self.h_cur_h):
                    self.htf_close(self.h_cur_h, self.h_cur_l, self.h_cur_c, hpoi_age, hpoi_touch)
                self.h_bucket = bucket
                self.h_cur_h = h
                self.h_cur_l = l
            else:
                self.h_cur_h = max(self.h_cur_h, h)
                self.h_cur_l = min(self.h_cur_l, l)
            self.h_cur_c = c
        hpb_top = math.nan
        hpb_bot = math.nan
        hpb_in = 0
        win = poi_near * 2 * atr
        for hp in self.hpd:
            if hp.bot <= c:
                near2 = abs(c - hp.top) <= win
                fresher = hp.ins == 0 and hpb_in != 0 and near2
                same = (hp.ins == 0) == (hpb_in == 0)
                if isnan(hpb_top) or fresher or (same and hp.top > hpb_top):
                    hpb_top = hp.top
                    hpb_bot = hp.bot
                    hpb_in = hp.ins
        hps_top = math.nan
        hps_bot = math.nan
        hps_in = 0
        for hq in self.hps:
            if hq.top >= c:
                near3 = abs(c - hq.bot) <= win
                fresher3 = hq.ins == 0 and hps_in != 0 and near3
                same3 = (hq.ins == 0) == (hps_in == 0)
                if isnan(hps_top) or fresher3 or (same3 and hq.bot < hps_bot):
                    hps_top = hq.top
                    hps_bot = hq.bot
                    hps_in = hq.ins
        self.d_hpb_top = hpb_top
        self.d_hpb_bot = hpb_bot
        self.d_hpb_in = hpb_in
        self.d_hps_top = hps_top
        self.d_hps_bot = hps_bot
        self.d_hps_in = hps_in
        cont_tap_l = htf_live and (not isnan(hpb_top)) and l <= hpb_top and c > hpb_bot
        cont_tap_s = htf_live and (not isnan(hps_top)) and h >= hps_bot and c < hps_top
        # NEXT buy / sell (nearest un-spent POI per side)
        nb_score = 0
        ns_score = 0
        nb_top = math.nan
        nb_bot = math.nan
        ns_top = math.nan
        ns_bot = math.nan
        nb_fresh = False
        ns_fresh = False
        nb_kind = ''
        ns_kind = ''
        for zn in self.zones:
            if (not zn.is_supply) and (not zn.signaled) and zn.bot <= c and (isnan(nb_top) or zn.top > nb_top):
                nb_top = zn.top
                nb_bot = zn.bot
                nb_fresh = (not zn.touched) or zn.touch_bar == bi
                nb_kind = zn.kind
                nb_score = zn.score
            if zn.is_supply and (not zn.signaled) and zn.top >= c and (isnan(ns_bot) or zn.bot < ns_bot):
                ns_top = zn.top
                ns_bot = zn.bot
                ns_fresh = (not zn.touched) or zn.touch_bar == bi
                ns_kind = zn.kind
                ns_score = zn.score
        if (not isnan(hpb_top)) and hpb_top - hpb_bot <= hpoi_next_max * atr and (isnan(nb_top) or hpb_top > nb_top):
            nb_top = hpb_top
            nb_bot = hpb_bot
            nb_fresh = hpb_in == 0
            nb_score = 3
            nb_kind = 'HTF'
        if (not isnan(hps_top)) and hps_top - hps_bot <= hpoi_next_max * atr and (isnan(ns_bot) or hps_bot < ns_bot):
            ns_top = hps_top
            ns_bot = hps_bot
            ns_fresh = hps_in == 0
            ns_score = 3
            ns_kind = 'HTF'
        # ---- MODULE 14 · trendline liquidity (candidate -> validated -> sweep / break)
        sig_tl_long = False
        sig_tl_short = False
        sl_tl_long = math.nan
        sl_tl_short = math.nan
        tl_up_val = self.tl_up_price + self.tl_up_slope * float(bi - self.tl_up_bar) if not isnan(self.tl_up_slope) else math.nan
        tl_dn_val = self.tl_dn_price + self.tl_dn_slope * float(bi - self.tl_dn_bar) if not isnan(self.tl_dn_slope) else math.nan
        if not isnan(tl_up_val):
            near_up = l <= tl_up_val + near_lvl * atr
            if c < tl_up_val:
                self.tl_retire(True, t, tl_up_val, show_tl)
            else:
                if near_up and not self.tl_up_near:
                    self.tl_up_touch += 1
                if l < tl_up_val and tl_sweep and self.tl_up_touch >= 2 and z_bull_conf:
                    sig_tl_long = True
                    sl_tl_long = l - sl_pad * atr
                self.tl_up_near = near_up
                if self.tl_up_bar != NA and bi - self.tl_up_bar > tl_max_age:
                    self.tl_drop(True, show_tl)
        if not isnan(tl_dn_val):
            near_dn = h >= tl_dn_val - near_lvl * atr
            if c > tl_dn_val:
                self.tl_retire(False, t, tl_dn_val, show_tl)
            else:
                if near_dn and not self.tl_dn_near:
                    self.tl_dn_touch += 1
                if h > tl_dn_val and tl_sweep and self.tl_dn_touch >= 2 and z_bear_conf:
                    sig_tl_short = True
                    sl_tl_short = h + sl_pad * atr
                self.tl_dn_near = near_dn
                if self.tl_dn_bar != NA and bi - self.tl_dn_bar > tl_max_age:
                    self.tl_drop(False, show_tl)
        # ------------------------------------------------------------ MODULE 15A
        dir_lock = 0
        if one_dir:
            if self.trd_dir != 0:
                dir_lock = self.trd_dir
            elif self.su_l >= 2:
                dir_lock = 1
            elif self.su_s >= 2:
                dir_lock = -1
        lock_ok_l = dir_lock >= 0
        lock_ok_s = dir_lock <= 0
        # ------------------------------------------------------------ MODULE 16
        ses_pts = 3
        if intraday:
            ses_pts = 5 if (in_sb or in_ny or in_lon) else (2 if in_asia else 0)
        ses_tier_ok = (not intraday) or ses_pts >= 5
        use_anch_l = self.su_l >= 2 and (not isnan(self.su_l_at)) and (not isnan(self.su_l_ab))
        use_anch_s = self.su_s >= 2 and (not isnan(self.su_s_at)) and (not isnan(self.su_s_ab))
        dmd_top = self.su_l_at if use_anch_l else nb_top
        dmd_bot = self.su_l_ab if use_anch_l else nb_bot
        sup_top = self.su_s_at if use_anch_s else ns_top
        sup_bot = self.su_s_ab if use_anch_s else ns_bot
        dmd_fresh = self.su_l <= 3 if use_anch_l else nb_fresh
        sup_fresh = self.su_s <= 3 if use_anch_s else ns_fresh
        in_demand = (l <= dmd_top and c >= dmd_bot) if use_anch_l else ((not isnan(nb_top)) and c <= nb_top)
        near_demand = (not isnan(dmd_top)) and (not in_demand) and abs(c - dmd_top) <= poi_near * atr
        in_supply = (h >= sup_bot and c <= sup_top) if use_anch_s else ((not isnan(ns_bot)) and c >= ns_bot)
        near_supply = (not isnan(sup_bot)) and (not in_supply) and abs(sup_bot - c) <= poi_near * atr
        poi_conf_raw = (not isnan(nb_top)) and (not isnan(ns_bot)) and nb_kind != 'HTF' and ns_kind != 'HTF' and ns_bot - nb_top <= atr
        side_bias = htf_b if htf_b != 0 else (dir_lock if dir_lock != 0 else ext_dir)
        poi_block_l = poi_conf_raw and (not use_anch_l) and side_bias <= 0
        poi_block_s = poi_conf_raw and (not use_anch_s) and side_bias >= 0
        ctx_long = max(0, (10 if htf_b > 0 else (5 if htf_b == 0 else 0)) + (10 if ext_dir > 0 else 0) + ses_pts + (5 if (range_ok and pd_pos < 0.5) else 0) - (10 if adr_chase_l else 0))
        ctx_short = max(0, (10 if htf_b < 0 else (5 if htf_b == 0 else 0)) + (10 if ext_dir < 0 else 0) + ses_pts + (5 if (range_ok and pd_pos >= 0.5) else 0) - (10 if adr_chase_s else 0))
        liq_long = (10 if ssl_in_play else 0) + (5 if recent_eng_lo else 0) + (5 if (ssl_in_play and self.ssl_q_raw >= 3) else 0)
        liq_short = (10 if bsl_in_play else 0) + (5 if recent_eng_hi else 0) + (5 if (bsl_in_play and self.bsl_q_raw >= 3) else 0)
        poi_long = 0
        if not poi_block_l:
            poi_long = (10 if in_demand else (5 if near_demand else 0)) + (5 if ((in_demand or near_demand) and dmd_fresh) else 0) + (5 if in_ote_buy else 0)
        poi_short = 0
        if not poi_block_s:
            poi_short = (10 if in_supply else (5 if near_supply else 0)) + (5 if ((in_supply or near_supply) and sup_fresh) else 0) + (5 if in_ote_sell else 0)
        cisd_sep_up = recent_cisd_up and (self.l_ch_up == NA or self.l_cisd_up != self.l_ch_up)
        cisd_sep_dn = recent_cisd_dn and (self.l_ch_dn == NA or self.l_cisd_dn != self.l_ch_dn)
        tl_f = max(self.decay(self.l_mss_up, 12.0, trig_look), self.decay(self.l_ch_up, 9.0, trig_look), self.decay(self.l_bos_up, 5.0, trig_look)) + (self.decay(self.l_cisd_up, 8.0, trig_look) if cisd_sep_up else 0.0)
        ts_f = max(self.decay(self.l_mss_dn, 12.0, trig_look), self.decay(self.l_ch_dn, 9.0, trig_look), self.decay(self.l_bos_dn, 5.0, trig_look)) + (self.decay(self.l_cisd_dn, 8.0, trig_look) if cisd_sep_dn else 0.0)
        trig_long = min(20, round(tl_f))
        trig_short = min(20, round(ts_f))
        if self.su_l == 3 and self.su_l_bar != NA:
            rw = SB_RET_WAIT if self.sb_tag_l != 0 else ret_wait
            base_l = 12.0 if (self.l_mss_up != NA and self.l_mss_up >= self.su_l_bar) else 9.0
            trig_long = max(trig_long, round(base_l * max(0.5, 1.0 - float(bi - self.su_l_bar) / (rw + 1.0))))
        if self.su_s == 3 and self.su_s_bar != NA:
            rws = SB_RET_WAIT if self.sb_tag_s != 0 else ret_wait
            base_s = 12.0 if (self.l_mss_dn != NA and self.l_mss_dn >= self.su_s_bar) else 9.0
            trig_short = max(trig_short, round(base_s * max(0.5, 1.0 - float(bi - self.su_s_bar) / (rws + 1.0))))
        retest_long = (not use_anch_l) and (not isnan(dmd_top)) and l <= dmd_top and c >= dmd_bot
        retest_short = (not use_anch_s) and (not isnan(sup_bot)) and h >= sup_bot and c <= sup_top
        exec_long = (5 if retest_long else 0) + (5 if z_bull_conf else 0)
        exec_short = (5 if retest_short else 0) + (5 if z_bear_conf else 0)
        score_base_l = ctx_long + liq_long + poi_long + trig_long + exec_long
        score_base_s = ctx_short + liq_short + poi_short + trig_short + exec_short
        sb_pool_ok_l = (not sb_pool_pref) or self.ssl_kind >= 2
        sb_pool_ok_s = (not sb_pool_pref) or self.bsl_kind >= 2
        sb_ctx_long = 0
        sb_ctx_short = 0
        if sb_ctx:
            sb_ctx_long = sb_win_pts + (3 if (ssl_in_play and self.ssl_kind >= 2) else 0) + (3 if self.ssl_q_raw >= 4 else (2 if self.ssl_q_raw >= 3 else 0)) + (2 if recent_mss_up else (1 if recent_ch_up else 0)) + (1 if (ssl_in_play and self.ssl_q >= sb_min_qual and sb_pool_ok_l) else 0)
            sb_ctx_short = sb_win_pts + (3 if (bsl_in_play and self.bsl_kind >= 2) else 0) + (3 if self.bsl_q_raw >= 4 else (2 if self.bsl_q_raw >= 3 else 0)) + (2 if recent_mss_dn else (1 if recent_ch_dn else 0)) + (1 if (bsl_in_play and self.bsl_q >= sb_min_qual and sb_pool_ok_s) else 0)
        score_long = min(100, score_base_l + sb_ctx_long)
        score_short = min(100, score_base_s + sb_ctx_short)
        trig_cisd = shift_src == '+ CISD'
        trig_int = shift_src == '+ internal CHoCH' or trig_cisd
        has_trig_l = recent_mss_up or self.recent(self.l_ech_up, trig_look) or (trig_int and recent_ch_up) or (trig_cisd and recent_cisd_up)
        has_trig_s = recent_mss_dn or self.recent(self.l_ech_dn, trig_look) or (trig_cisd and recent_cisd_dn) or (trig_int and recent_ch_dn)
        pd_ok_tl = (sb_pd_ok and sb_pd_pos < 0.5) if self.sb_tag_l != 0 else (range_ok and ((not range_holds) or pd_pos < 0.5))
        pd_ok_ts = (sb_pd_ok and sb_pd_pos >= 0.5) if self.sb_tag_s != 0 else (range_ok and ((not range_holds) or pd_pos >= 0.5))
        tier_long = self.tier(liq_long, poi_long, has_trig_l, exec_long >= 5, htf_b > 0, ses_tier_ok, self.ssl_q_raw, pd_ok_tl)
        tier_short = self.tier(liq_short, poi_short, has_trig_s, exec_short >= 5, htf_b < 0, ses_tier_ok, self.bsl_q_raw, pd_ok_ts)
        min_rank = 4 if tier_mode == 'A+ only' else (3 if tier_mode == 'A and above' else (2 if tier_mode == 'B and above' else 1))
        # ------------------------------------------------------------ MODULE 17
        sig_mc_long = False
        sig_mc_short = False
        mc_plan_long = math.nan
        mc_plan_short = math.nan
        sl_mc_long = math.nan
        sl_mc_short = math.nan
        sb_sig_long = False
        sb_sig_short = False
        sb_ce_l = False
        sb_ce_s = False
        mc_ce_l = False
        mc_ce_s = False
        mc_ce_on = mc_entry != 'Proximal edge + confirmation'
        if sb_ctx_win == 0:
            self.sb_done_win_l = 0
            self.sb_done_win_s = 0
        sb_arm_ok_l = sb_ctx and self.ssl_q >= sb_min_qual and sb_pool_ok_l and sb_ctx_win != self.sb_done_win_l
        sb_arm_ok_s = sb_ctx and self.bsl_q >= sb_min_qual and sb_pool_ok_s and sb_ctx_win != self.sb_done_win_s
        sb_grace_l = sb_arm_ok_l and ssl_in_play and self.recent(self.last_ssl_bar, SB_ARM_GRACE) and self.sb_armed_ssl != self.last_ssl_bar
        sb_grace_s = sb_arm_ok_s and bsl_in_play and self.recent(self.last_bsl_bar, SB_ARM_GRACE) and self.sb_armed_bsl != self.last_bsl_bar
        std_grace_l = arm_grace > 0 and ssl_in_play and self.recent(self.last_ssl_bar, arm_grace) and self.armed_ssl != self.last_ssl_bar
        std_grace_s = arm_grace > 0 and bsl_in_play and self.recent(self.last_bsl_bar, arm_grace) and self.armed_bsl != self.last_bsl_bar
        arm_bar_l = self.last_ssl_bar == bi or sb_grace_l or std_grace_l
        arm_bar_s = self.last_bsl_bar == bi or sb_grace_s or std_grace_s
        shift_up_ok = mss_up
        shift_dn_ok = mss_dn
        if shift_src == 'MSS / external CHoCH':
            shift_up_ok = mss_up or ech_up
            shift_dn_ok = mss_dn or ech_dn
        elif shift_src == '+ internal CHoCH':
            shift_up_ok = mss_up or ech_up or ch_up
            shift_dn_ok = mss_dn or ech_dn or ch_dn
        elif shift_src == '+ CISD':
            shift_up_ok = mss_up or ech_up or ch_up or cisd_up
            shift_dn_ok = mss_dn or ech_dn or ch_dn or cisd_dn
        shift_up_ok = shift_up_ok or ((ch_up or cisd_up) and bull and body >= disp_fact * atr and bull_fvg)
        shift_dn_ok = shift_dn_ok or ((ch_dn or cisd_dn) and bear and body >= disp_fact * atr and bear_fvg)
        sb_disp_now = body >= sb_disp * atr
        sb_shift_up = mss_up or ech_up or ((ch_up or cisd_up) and bull and sb_disp_now)
        sb_shift_dn = mss_dn or ech_dn or ((ch_dn or cisd_dn) and bear and sb_disp_now)
        sb_fvg_ok_l = (not isnan(self.cfb_top)) and self.cfb_disp and self.cfb_top - self.cfb_bot >= SB_FVG_MIN * atr
        sb_fvg_ok_s = (not isnan(self.cfs_top)) and self.cfs_disp and self.cfs_top - self.cfs_bot >= SB_FVG_MIN * atr
        # ---- LONG machine
        if self.su_l == 0:
            self.sb_tag_l = 0
            self.sb_shift_gl = 0
        liq_wl = SB_LIQ_WAIT if self.sb_tag_l != 0 else liq_wait
        poi_wl = SB_POI_WAIT if self.sb_tag_l != 0 else poi_wait
        ret_wl = SB_RET_WAIT if self.sb_tag_l != 0 else ret_wait
        sb_kill_l = self.sb_tag_l != 0 and ((self.sb_tag_l == 1 and sb_end_lo) or (self.sb_tag_l == 2 and sb_end_am) or (self.sb_tag_l == 3 and sb_end_pm))
        if self.su_l >= 1:
            if (not isnan(self.su_l_sw_ext)) and c < self.su_l_sw_ext:
                self.su_l = 0
                self.su_l_reason = 'sweep undone'
            elif self.su_l <= 2 and (not isnan(self.su_l_sw_lvl)) and c < self.su_l_sw_lvl - near_lvl * atr:
                self.su_l = 0
                self.su_l_reason = 'sweep reclaim lost'
            elif bear and body >= disp_fact * atr and self.su_l <= 3 and not (self.su_l == 3 and (not isnan(self.su_l_ab)) and c > self.su_l_ab):
                self.su_l = 0
                self.su_l_reason = 'opposing displacement'
            elif self.su_l == 1 and bsl_sweep and self.bsl_q >= 2:
                self.su_l = 0
                self.su_l_reason = 'range swept both ways'
        if self.su_l >= 1 and self.su_l <= 2:
            self.su_l_sw_ext = min(self.su_l_sw_ext, l)
        if self.su_l >= 2 and self.su_l_fvg_bar == NA and (not isnan(self.su_l_ab)) and c < self.su_l_ab:
            self.su_l = 0
            self.su_l_reason = 'POI violated (own anchor)'
        if htf_prot_inval and self.su_l >= 1 and self.su_l <= 3 and (not isnan(hs_prot_lo)) and c < hs_prot_lo:
            self.su_l = 0
            self.su_l_reason = 'HTF protected low broken'
        if sb_kill_l and self.su_l >= 1 and self.su_l <= 3:
            self.su_l = 0
            self.su_l_reason = 'SB window closed'
        if (self.su_l == 1 and bi - self.su_l_bar > liq_wl) or (self.su_l == 2 and bi - self.su_l_bar > poi_wl) or (self.su_l == 3 and bi - self.su_l_bar > ret_wl):
            self.su_l_reason = 'sweep expired (no POI tap)' if self.su_l == 1 else ('POI tap expired (no shift)' if self.su_l == 2 else 'retest window expired')
            self.su_l = 0
        std_arm_l = ssl_in_play and arm_bar_l and (self.ssl_q >= min_arm_qual or sb_arm_ok_l) and arm_bias_l
        if self.su_l == 0 and std_arm_l and lock_ok_l:
            chop_block_l = use_regime and regime == 'CHOP' and (not inst_sweep_l) and not sb_arm_ok_l
            if not chop_block_l:
                self.su_l = 1
                self.su_l_bar = bi
                self.su_l_sw_lvl = self.last_ssl_lvl
                self.su_l_sw_ext = self.last_ssl_ext
                self.su_l_at = math.nan
                self.su_l_ab = math.nan
                self.su_l_fvg_bar = NA
                self.sb_tag_l = sb_ctx_win if sb_arm_ok_l else 0
                self.sb_shift_gl = 0
                self.armed_ssl = self.last_ssl_bar
                if sb_arm_ok_l:
                    self.sb_armed_ssl = self.last_ssl_bar
        if self.su_l == 1 and ssl_in_play and (sb_shift_up if self.sb_tag_l != 0 else (fast_shift and shift_up_ok)):
            self.su_l = 3
            self.su_l_bar = bi
            self.sb_shift_gl = 2 if mss_up else 1
            self.su_l_at = math.nan
            self.su_l_ab = math.nan
            self.su_l_fvg_bar = NA
        if self.su_l == 1:
            tap_zone_l = in_demand and retest_long and not poi_block_l
            if tap_zone_l or cont_tap_l:
                self.su_l = 2
                self.su_l_bar = bi
                if tap_zone_l:
                    self.su_l_at = nb_top
                    self.su_l_ab = nb_bot
        if self.su_l == 2 and (sb_shift_up if self.sb_tag_l != 0 else shift_up_ok):
            self.su_l = 3
            self.su_l_bar = bi
            self.sb_shift_gl = 2 if mss_up else 1
            if (not isnan(self.cfb_top)) and self.cfb_bar >= self.su_l_bar and (self.cfb_disp if self.sb_tag_l == 0 else sb_fvg_ok_l):
                self.su_l_at = self.cfb_top
                self.su_l_ab = self.cfb_bot
                self.su_l_fvg_bar = self.cfb_bar
        if self.su_l == 3:
            if self.su_l_fvg_bar == NA and (not isnan(self.cfb_top)) and self.cfb_bar >= self.su_l_bar and (self.cfb_disp if self.sb_tag_l == 0 else sb_fvg_ok_l):
                self.su_l_at = self.cfb_top
                self.su_l_ab = self.cfb_bot
                self.su_l_fvg_bar = self.cfb_bar
            if not isnan(self.su_l_at):
                ce_l = (self.su_l_at + self.su_l_ab) / 2
                ripe_l = bi > self.su_l_bar and (self.su_l_fvg_bar == NA or bi > self.su_l_fvg_bar)
                sb_set_l = self.sb_tag_l != 0 and self.su_l_fvg_bar != NA and sb_win_now == self.sb_tag_l
                sb_rej_l = bull_pin or bull_eng or ifc_bull or cisd_up
                sb_ce_tap_l = lo_a <= ce_l
                sb_prx_tap_l = l <= self.su_l_at and sb_rej_l
                sb_loc_ok_l = (htf_b > 0 or (htf_b == 0 and bias_ok_l)) and (sb_pd_ok and sb_pd_pos < 0.5)
                sb_enter_l = sb_set_l and ripe_l and sb_loc_ok_l and (sb_ce_tap_l or sb_prx_tap_l)
                mc_ce_tap_l = mc_ce_on and self.sb_tag_l == 0 and self.su_l_fvg_bar != NA and lo_a <= ce_l
                mc_cnf_ok_l = c >= ce_l and c >= l + (1 - STRONG) * rng
                mc_cnf_tap_l = mc_entry != 'CE (50%) only' and l <= self.su_l_at and z_bull_conf and mc_cnf_ok_l
                std_enter_l = self.sb_tag_l == 0 and ripe_l and (mc_ce_tap_l or mc_cnf_tap_l)
                if c < self.su_l_ab:
                    self.su_l = 0
                    self.su_l_reason = 'SB FVG violated' if self.sb_tag_l != 0 else 'anchor FVG violated'
                elif (sb_enter_l or std_enter_l) and c > self.su_l_ab:
                    sig_mc_long = True
                    sb_sig_long = sb_enter_l
                    sb_ce_l = sb_enter_l and sb_ce_tap_l
                    mc_ce_l = std_enter_l and mc_ce_tap_l
                    mc_plan_long = ce_l if (sb_ce_l or mc_ce_l) else min(c, self.su_l_at) + spr
                    sl_anch_l = min(l, self.su_l_ab) - sl_pad * atr
                    sl_raid_l = min(min(l, self.su_l_ab), nz_f(self.su_l_sw_ext, l)) - sl_pad * atr
                    sl_mc_long = sl_raid_l if (max_risk == 0 or mc_plan_long - sl_raid_l <= max_risk * atr) else sl_anch_l
                    self.su_l = 4
                    self.su_l_bar = bi
        # ---- SHORT machine
        if self.su_s == 0:
            self.sb_tag_s = 0
            self.sb_shift_gs = 0
        liq_ws = SB_LIQ_WAIT if self.sb_tag_s != 0 else liq_wait
        poi_ws = SB_POI_WAIT if self.sb_tag_s != 0 else poi_wait
        ret_ws = SB_RET_WAIT if self.sb_tag_s != 0 else ret_wait
        sb_kill_s = self.sb_tag_s != 0 and ((self.sb_tag_s == 1 and sb_end_lo) or (self.sb_tag_s == 2 and sb_end_am) or (self.sb_tag_s == 3 and sb_end_pm))
        if self.su_s >= 1:
            if (not isnan(self.su_s_sw_ext)) and c > self.su_s_sw_ext:
                self.su_s = 0
                self.su_s_reason = 'sweep undone'
            elif self.su_s <= 2 and (not isnan(self.su_s_sw_lvl)) and c > self.su_s_sw_lvl + near_lvl * atr:
                self.su_s = 0
                self.su_s_reason = 'sweep reclaim lost'
            elif bull and body >= disp_fact * atr and self.su_s <= 3 and not (self.su_s == 3 and (not isnan(self.su_s_at)) and c < self.su_s_at):
                self.su_s = 0
                self.su_s_reason = 'opposing displacement'
            elif self.su_s == 1 and ssl_sweep and self.ssl_q >= 2:
                self.su_s = 0
                self.su_s_reason = 'range swept both ways'
        if self.su_s >= 1 and self.su_s <= 2:
            self.su_s_sw_ext = max(self.su_s_sw_ext, h)
        if self.su_s >= 2 and self.su_s_fvg_bar == NA and (not isnan(self.su_s_at)) and c > self.su_s_at:
            self.su_s = 0
            self.su_s_reason = 'POI violated (own anchor)'
        if htf_prot_inval and self.su_s >= 1 and self.su_s <= 3 and (not isnan(hs_prot_hi)) and c > hs_prot_hi:
            self.su_s = 0
            self.su_s_reason = 'HTF protected high broken'
        if sb_kill_s and self.su_s >= 1 and self.su_s <= 3:
            self.su_s = 0
            self.su_s_reason = 'SB window closed'
        if (self.su_s == 1 and bi - self.su_s_bar > liq_ws) or (self.su_s == 2 and bi - self.su_s_bar > poi_ws) or (self.su_s == 3 and bi - self.su_s_bar > ret_ws):
            self.su_s_reason = 'sweep expired (no POI tap)' if self.su_s == 1 else ('POI tap expired (no shift)' if self.su_s == 2 else 'retest window expired')
            self.su_s = 0
        std_arm_s = bsl_in_play and arm_bar_s and (self.bsl_q >= min_arm_qual or sb_arm_ok_s) and arm_bias_s
        if self.su_s == 0 and std_arm_s and lock_ok_s:
            chop_block_s = use_regime and regime == 'CHOP' and (not inst_sweep_s) and not sb_arm_ok_s
            if not chop_block_s:
                self.su_s = 1
                self.su_s_bar = bi
                self.su_s_sw_lvl = self.last_bsl_lvl
                self.su_s_sw_ext = self.last_bsl_ext
                self.su_s_at = math.nan
                self.su_s_ab = math.nan
                self.su_s_fvg_bar = NA
                self.sb_tag_s = sb_ctx_win if sb_arm_ok_s else 0
                self.sb_shift_gs = 0
                self.armed_bsl = self.last_bsl_bar
                if sb_arm_ok_s:
                    self.sb_armed_bsl = self.last_bsl_bar
        if self.su_s == 1 and bsl_in_play and (sb_shift_dn if self.sb_tag_s != 0 else (fast_shift and shift_dn_ok)):
            self.su_s = 3
            self.su_s_bar = bi
            self.sb_shift_gs = 2 if mss_dn else 1
            self.su_s_at = math.nan
            self.su_s_ab = math.nan
            self.su_s_fvg_bar = NA
        if self.su_s == 1:
            tap_zone_s = in_supply and retest_short and not poi_block_s
            if tap_zone_s or cont_tap_s:
                self.su_s = 2
                self.su_s_bar = bi
                if tap_zone_s:
                    self.su_s_at = ns_top
                    self.su_s_ab = ns_bot
        if self.su_s == 2 and (sb_shift_dn if self.sb_tag_s != 0 else shift_dn_ok):
            self.su_s = 3
            self.su_s_bar = bi
            self.sb_shift_gs = 2 if mss_dn else 1
            if (not isnan(self.cfs_top)) and self.cfs_bar >= self.su_s_bar and (self.cfs_disp if self.sb_tag_s == 0 else sb_fvg_ok_s):
                self.su_s_at = self.cfs_top
                self.su_s_ab = self.cfs_bot
                self.su_s_fvg_bar = self.cfs_bar
        if self.su_s == 3:
            if self.su_s_fvg_bar == NA and (not isnan(self.cfs_top)) and self.cfs_bar >= self.su_s_bar and (self.cfs_disp if self.sb_tag_s == 0 else sb_fvg_ok_s):
                self.su_s_at = self.cfs_top
                self.su_s_ab = self.cfs_bot
                self.su_s_fvg_bar = self.cfs_bar
            if not isnan(self.su_s_ab):
                ce_s = (self.su_s_at + self.su_s_ab) / 2
                ripe_s = bi > self.su_s_bar and (self.su_s_fvg_bar == NA or bi > self.su_s_fvg_bar)
                sb_set_s = self.sb_tag_s != 0 and self.su_s_fvg_bar != NA and sb_win_now == self.sb_tag_s
                sb_rej_s = bear_pin or bear_eng or ifc_bear or cisd_dn
                sb_ce_tap_s = h >= ce_s
                sb_prx_tap_s = h >= self.su_s_ab and sb_rej_s
                sb_loc_ok_s = (htf_b < 0 or (htf_b == 0 and bias_ok_s)) and (sb_pd_ok and sb_pd_pos >= 0.5)
                sb_enter_s = sb_set_s and ripe_s and sb_loc_ok_s and (sb_ce_tap_s or sb_prx_tap_s)
                mc_ce_tap_s = mc_ce_on and self.sb_tag_s == 0 and self.su_s_fvg_bar != NA and h >= ce_s
                mc_cnf_ok_s = c <= ce_s and c <= h - (1 - STRONG) * rng
                mc_cnf_tap_s = mc_entry != 'CE (50%) only' and h >= self.su_s_ab and z_bear_conf and mc_cnf_ok_s
                std_enter_s = self.sb_tag_s == 0 and ripe_s and (mc_ce_tap_s or mc_cnf_tap_s)
                if c > self.su_s_at:
                    self.su_s = 0
                    self.su_s_reason = 'SB FVG violated' if self.sb_tag_s != 0 else 'anchor FVG violated'
                elif (sb_enter_s or std_enter_s) and c < self.su_s_at:
                    sig_mc_short = True
                    sb_sig_short = sb_enter_s
                    sb_ce_s = sb_enter_s and sb_ce_tap_s
                    mc_ce_s = std_enter_s and mc_ce_tap_s
                    mc_plan_short = ce_s if (sb_ce_s or mc_ce_s) else max(c, self.su_s_ab)
                    sl_anch_s = max(h, self.su_s_at) + sl_pad * atr
                    sl_raid_s = max(max(h, self.su_s_at), nz_f(self.su_s_sw_ext, h)) + sl_pad * atr
                    sl_mc_short = sl_raid_s if (max_risk == 0 or sl_raid_s - mc_plan_short <= max_risk * atr) else sl_anch_s
                    self.su_s = 4
                    self.su_s_bar = bi
        # ------------------------------------------------------------ MODULE 18
        long_cd_ok = master_cd == 0 or self.last_long_sig == NA or bi - self.last_long_sig > master_cd
        short_cd_ok = master_cd == 0 or self.last_short_sig == NA or bi - self.last_short_sig > master_cd
        chop_ok_l = (not use_regime) or regime != 'CHOP' or inst_sweep_l or (sb_enable and sb_sig_long)
        chop_ok_s = (not use_regime) or regime != 'CHOP' or inst_sweep_s or (sb_enable and sb_sig_short)
        if self.new_day:
            self.trd_today = 0
            self.loss_today = 0
        gov_trd_ok = (not use_gov) or (not intraday) or max_trd_day == 0 or self.trd_today < max_trd_day
        gov_loss_ok = (not use_gov) or (not intraday) or max_loss_day == 0 or self.loss_today < max_loss_day
        gov_ok = gov_trd_ok and gov_loss_ok
        mc_pd_ok_l = (not mc_req_pd) or (not range_ok) or (not range_holds) or pd_pos < 0.5
        mc_pd_ok_s = (not mc_req_pd) or (not range_ok) or (not range_holds) or pd_pos >= 0.5
        score_ok_l = min_score == 0 or score_base_l >= min_score
        score_ok_s = min_score == 0 or score_base_s >= min_score
        common_l = bias_ok_l and lock_ok_l and kz_ok and news_ok and dow_ok and chop_ok_l and gov_ok and score_ok_l
        common_s = bias_ok_s and lock_ok_s and kz_ok and news_ok and dow_ok and chop_ok_s and gov_ok and score_ok_s
        long_ok = common_l and long_cd_ok and mc_pd_ok_l
        short_ok = common_s and short_cd_ok and mc_pd_ok_s
        long_ok = long_ok or (sb_sig_long and common_l)
        short_ok = short_ok or (sb_sig_short and common_s)
        mc_tier_l = self.mc_tier(self.ssl_q_raw >= 3, htf_b > 0, self.sb_shift_gl >= 2, (sb_pd_ok and sb_pd_pos < 0.5) if self.sb_tag_l != 0 else (range_ok and pd_pos < 0.5), self.ssl_kind >= 2, ses_tier_ok, not adr_chase_l)
        mc_tier_s = self.mc_tier(self.bsl_q_raw >= 3, htf_b < 0, self.sb_shift_gs >= 2, (sb_pd_ok and sb_pd_pos >= 0.5) if self.sb_tag_s != 0 else (range_ok and pd_pos >= 0.5), self.bsl_kind >= 2, ses_tier_ok, not adr_chase_s)
        sig_mc_long = sig_mc_long and long_ok and mc_tier_l >= (max(min_rank, 3) if sb_sig_long else min_rank)
        sig_mc_short = sig_mc_short and short_ok and mc_tier_s >= (max(min_rank, 3) if sb_sig_short else min_rank)
        if not sig_mc_long:
            sb_sig_long = False
            sb_ce_l = False
            mc_ce_l = False
            mc_plan_long = math.nan
        if not sig_mc_short:
            sb_sig_short = False
            sb_ce_s = False
            mc_ce_s = False
            mc_plan_short = math.nan
        if self.su_l == 4 and self.su_l_bar == bi and not sig_mc_long:
            self.su_l = 3
            self.su_l_reason = self.gate_txt(long_ok, tier_txt(mc_tier_l), score_ok_l, score_base_l, min_score, gov_trd_ok, gov_loss_ok, long_cd_ok, news_ok, dow_ok, chop_ok_l, lock_ok_l, mc_pd_ok_l, True)
        if self.su_s == 4 and self.su_s_bar == bi and not sig_mc_short:
            self.su_s = 3
            self.su_s_reason = self.gate_txt(short_ok, tier_txt(mc_tier_s), score_ok_s, score_base_s, min_score, gov_trd_ok, gov_loss_ok, short_cd_ok, news_ok, dow_ok, chop_ok_s, lock_ok_s, mc_pd_ok_s, False)
        sb_live = sb_enable and ((self.sb_tag_l != 0 and self.su_l >= 2) or (self.sb_tag_s != 0 and self.su_s >= 2))
        eng_rank = min(4, min_rank + 1) if sb_live else min_rank
        sig_sd_long = sig_sd_long and long_ok and tier_long >= eng_rank
        sig_sd_short = sig_sd_short and short_ok and tier_short >= eng_rank
        sig_tl_long = sig_tl_long and long_ok and tier_long >= eng_rank
        sig_tl_short = sig_tl_short and short_ok and tier_short >= eng_rank
        any_long = sig_mc_long or sig_sd_long or sig_tl_long
        any_short = sig_mc_short or sig_sd_short or sig_tl_short
        if any_long and any_short:
            rk_l = (3 if sb_sig_long else 2) if sig_mc_long else 1
            rk_s = (3 if sb_sig_short else 2) if sig_mc_short else 1
            if rk_l > rk_s:
                any_short = False
                sig_mc_short = False
                sb_sig_short = False
                if self.su_s == 4 and self.su_s_bar == bi:
                    self.su_s = 0
                    self.su_s_reason = 'conflict - higher-rank long won the bar'
            elif rk_s > rk_l:
                any_long = False
                sig_mc_long = False
                sb_sig_long = False
                if self.su_l == 4 and self.su_l_bar == bi:
                    self.su_l = 0
                    self.su_l_reason = 'conflict - higher-rank short won the bar'
            else:
                any_long = False
                any_short = False
        # ------------------------------------------------------------ MODULE 18B
        sel_sl_l = sl_mc_long if sig_mc_long else (sl_sd_long if sig_sd_long else sl_tl_long)
        sel_sl_s = sl_mc_short if sig_mc_short else (sl_sd_short if sig_sd_short else sl_tl_short)
        plan_entry = math.nan
        if any_long:
            plan_entry = nz_f(mc_plan_long, c)
        elif any_short:
            plan_entry = nz_f(mc_plan_short, c)
        plan_sl = math.nan
        plan_tp2 = math.nan
        plan_ok = True
        plan_kill = ''
        if any_long or any_short:
            fb_l = min(l, l1) - sl_pad * atr
            fb_s = max(h, h1) + sl_pad * atr
            sl_l = sel_sl_l if ((not isnan(sel_sl_l)) and sel_sl_l < plan_entry) else fb_l
            sl_s = sel_sl_s if ((not isnan(sel_sl_s)) and sel_sl_s > plan_entry) else fb_s
            plan_sl = sl_l if any_long else sl_s + spr
            ce_fill = sb_ce_l or sb_ce_s or mc_ce_l or mc_ce_s
            if slip_guard > 0 and (not ce_fill) and abs(c - plan_entry) > slip_guard * atr:
                plan_ok = False
                plan_kill = 'entry slipped from the plan price'
            plan_risk = abs(plan_entry - plan_sl)
            if plan_ok and max_risk > 0 and plan_risk > max_risk * atr:
                if risk_mode == 'Clamp the stop':
                    plan_sl = plan_entry - max_risk * atr if any_long else plan_entry + max_risk * atr
                    plan_risk = max_risk * atr
                else:
                    plan_ok = False
                    plan_kill = f'risk {plan_risk / atr:.2f} ATR exceeds the cap'
            if plan_ok:
                want_tp2 = plan_entry + rr_mult * plan_risk if any_long else plan_entry - rr_mult * plan_risk
                if any_long and (not isnan(ns_bot)) and ns_bot > plan_entry:
                    want_tp2 = min(want_tp2, ns_bot)
                if any_short and (not isnan(nb_top)) and nb_top < plan_entry:
                    want_tp2 = max(want_tp2, nb_top)
                plan_tp2 = want_tp2
                rr = abs(want_tp2 - plan_entry) / plan_risk if plan_risk > 0 else 0.0
                if min_rr > 0 and rr < min_rr:
                    plan_ok = False
                    plan_kill = f'reward blocked - only {rr:.2f}R to the first opposing POI'
            if plan_ok and plan_risk <= 0:
                plan_ok = False
                plan_kill = 'degenerate risk'
        if not plan_ok:
            if any_long and self.su_l == 4 and self.su_l_bar == bi:
                self.su_l = 0
                self.su_l_reason = plan_kill
            if any_short and self.su_s == 4 and self.su_s_bar == bi:
                self.su_s = 0
                self.su_s_reason = plan_kill
            any_long = False
            any_short = False
            sig_mc_long = False
            sig_mc_short = False
            sb_sig_long = False
            sb_sig_short = False
        sb_fire_l = any_long and sig_mc_long and sb_sig_long
        sb_fire_s = any_short and sig_mc_short and sb_sig_short
        if sb_fire_l:
            self.sb_done_win_l = self.sb_tag_l
        if sb_fire_s:
            self.sb_done_win_s = self.sb_tag_s
        mc_fill_next = (sig_mc_long or sig_mc_short) and not (sb_sig_long or sb_sig_short) and not (mc_ce_l or mc_ce_s)
        eng_fill_next = ((any_long or any_short) and not (sig_mc_long or sig_mc_short)) or mc_fill_next
        final_tier_l = max(tier_long, mc_tier_l) if sig_mc_long else tier_long
        final_tier_s = max(tier_short, mc_tier_s) if sig_mc_short else tier_short
        if any_long:
            self.last_long_sig = bi
        if any_short:
            self.last_short_sig = bi
        # ------------------------------------------------------------ MODULE 19
        if self.pend_dir != 0:
            filled = False
            if self.trd_dir == 0 and not (sig_mc_long or sig_mc_short):
                p_ent = o + spr if self.pend_dir == 1 else o
                p_risk = abs(p_ent - self.pend_sl)
                p_tp2 = p_ent + rr_mult * p_risk if self.pend_dir == 1 else p_ent - rr_mult * p_risk
                if self.pend_dir == 1 and (not isnan(ns_bot)) and ns_bot > p_ent:
                    p_tp2 = min(p_tp2, ns_bot)
                if self.pend_dir == -1 and (not isnan(nb_top)) and nb_top < p_ent:
                    p_tp2 = max(p_tp2, nb_top)
                p_rr = abs(p_tp2 - p_ent) / p_risk if p_risk > 0 else 0.0
                p_slip = slip_guard == 0 or abs(o - c1) <= slip_guard * atr
                p_risk_ok = max_risk == 0 or p_risk <= max_risk * atr
                p_rr_ok = min_rr == 0 or p_rr >= min_rr
                side_ok = (o > self.pend_sl) if self.pend_dir == 1 else (o + spr < self.pend_sl)
                if p_risk > 0 and side_ok and p_slip and p_risk_ok and p_rr_ok:
                    pm = max(3.0, rr_mult + 1)
                    tp1 = p_ent + p_risk if self.pend_dir == 1 else p_ent - p_risk
                    tp3 = p_ent + pm * p_risk if self.pend_dir == 1 else p_ent - pm * p_risk
                    self.trade_open(self.pend_dir, p_ent, self.pend_sl, tp1, p_tp2, tp3, False, 0, 0, bi)
                    filled = True
            if not filled:
                self.cnt_untracked += 1
            self.pend_dir = 0
        trd_dir_in = self.trd_dir
        trd_prot = (self.trd_sl >= self.trd_entry) if self.trd_dir == 1 else (self.trd_dir == -1 and self.trd_sl <= self.trd_entry)
        if self.trd_dir != 0:
            d = self.trd_dir
            adv = l if d == 1 else hi_a
            fav = h if d == 1 else lo_a
            if (self.trd_sl - adv) * d >= 0:
                if trd_prot:
                    self.cnt_be += 1
                else:
                    self.cnt_sl += 1
                    self.loss_today += 1
                    self.sum_r -= 1.0
                self.trd_dir = 0
            else:
                if (not self.trd_tp1_hit) and (fav - self.trd_tp1) * d >= 0:
                    self.trd_tp1_hit = True
                    self.cnt_tp1 += 1
                    be = self.trd_entry + d * max(SB_BE_BUF * atr, SB_BE_TP1 * abs(self.trd_tp1 - self.trd_entry))
                    self.trd_sl = max(self.trd_sl, be) if d == 1 else min(self.trd_sl, be)
                if self.trd_tp1_hit and (not self.trd_tp2_hit) and (fav - self.trd_tp2) * d >= 0:
                    self.trd_tp2_hit = True
                    self.cnt_tp2 += 1
                    if not self.trd_is_sb:
                        self.trd_dir = 0
                        self.sum_r += abs(self.trd_tp2 - self.trd_entry) / max(abs(self.trd_tp1 - self.trd_entry), tick)
                prot = prot_low_e if d == 1 else prot_high_e
                if self.trd_is_sb and self.trd_tp2_hit and not isnan(prot):
                    cap = min(min(l, l1), c) - sl_pad * atr if d == 1 else max(max(h, h1), c) + sl_pad * atr
                    trail = min(prot - sl_pad * atr, cap) if d == 1 else max(prot + sl_pad * atr, cap)
                    self.trd_sl = max(self.trd_sl, trail) if d == 1 else min(self.trd_sl, trail)
                if self.trd_dir != 0 and (self.trd_is_sb or self.trd_tp2_hit) and (fav - self.trd_tp3) * d >= 0:
                    self.cnt_tp3 += 1
                    self.trd_dir = 0
                    self.sum_r += abs(self.trd_tp3 - self.trd_entry) / max(abs(self.trd_tp1 - self.trd_entry), tick)
                if self.trd_is_sb and self.trd_dir != 0:
                    str_ex = (mss_dn or (self.trd_shift_g <= 1 and (cisd_dn or ch_dn or ech_dn))) if d == 1 else (mss_up or (self.trd_shift_g <= 1 and (cisd_up or ch_up or ech_up)))
                    w_end = (self.trd_sb_win == 1 and sb_end_lo) or (self.trd_sb_win == 2 and sb_end_am) or (self.trd_sb_win == 3 and sb_end_pm)
                    if str_ex or (w_end and not self.trd_tp1_hit):
                        self.trd_dir = 0
        if self.trd_dir != 0 and max_trd_bars > 0 and self.trd_bar != NA and bi - self.trd_bar > max_trd_bars:
            self.cnt_exp += 1
            self.trd_dir = 0
        if trd_dir_in != 0 and self.trd_dir == 0:
            self.ladder_clear()
        self.sb_set_live = (self.sb_tag_l != 0 and self.su_l >= 1) or (self.sb_tag_s != 0 and self.su_s >= 1) or (self.trd_dir != 0 and self.trd_is_sb)
        if self.su_l == 4 and self.trd_dir == 0 and self.pend_dir == 0 and not sig_mc_long:
            self.su_l = 0
        if self.su_s == 4 and self.trd_dir == 0 and self.pend_dir == 0 and not sig_mc_short:
            self.su_s = 0
        if any_long or any_short:
            d_new = 1 if any_long else -1
            entry_p = plan_entry
            sl_p = plan_sl
            risk = abs(entry_p - sl_p)
            tp1_p = entry_p + d_new * risk
            tp2_p = nz_f(plan_tp2, entry_p + d_new * rr_mult * risk)
            tp3_p = entry_p + d_new * max(3.0, rr_mult + 1) * risk
            tgt = math.nan
            if d_new == 1:
                if (not isnan(ns_bot)) and ns_bot > entry_p:
                    tgt = ns_bot
                elif (not isnan(self.last_res)) and self.last_res > entry_p:
                    tgt = self.last_res
            else:
                if (not isnan(nb_top)) and nb_top < entry_p:
                    tgt = nb_top
                elif (not isnan(self.last_sup)) and self.last_sup < entry_p:
                    tgt = self.last_sup
            if (not isnan(tgt)) and abs(tgt - entry_p) >= rr_mult * risk:
                tp3_p = tgt
            if d_new == 1:
                self.cnt_long += 1
            else:
                self.cnt_short += 1
            if self.trd_dir == 0 and self.pend_dir == 0:
                self.trd_today += 1
                if eng_fill_next:
                    self.pend_dir = d_new
                    self.pend_sl = sl_p
                else:
                    is_sb = sb_fire_l or sb_fire_s
                    self.trade_open(d_new, entry_p, sl_p, tp1_p, tp2_p, tp3_p, is_sb, self.sb_tag_l if d_new == 1 else self.sb_tag_s, self.sb_shift_gl if d_new == 1 else self.sb_shift_gs, bi)
            else:
                self.cnt_untracked += 1
            # ---- MODULE 20 signal label + ladder
            ftier = final_tier_l if d_new == 1 else final_tier_s
            sc = score_long if d_new == 1 else score_short
            src = ('SB' if (sb_sig_long or sb_sig_short) else 'SETUP') if (sig_mc_long or sig_mc_short) else ('Zone 50%' if (sig_sd_long or sig_sd_short) else 'TL sweep')
            rr2 = abs(tp2_p - entry_p) / risk if risk > 0 else 0.0
            txt = ('BUY ' if d_new == 1 else 'SELL ') + tier_txt(ftier) + ' ' + src + f' {sc}' + '\nE ' + px(entry_p, prec) + '  SL ' + px(sl_p, prec) + f'\nTP2 {rr2:.1f}R'
            self.last_sig_txt = ('BUY ' if d_new == 1 else 'SELL ') + tier_txt(ftier) + ' ' + src + ' @' + px(entry_p, prec)
            lb = LabelAbs(txt, AbsolutePosition(t, l - 0.6 * atr if d_new == 1 else h + 0.6 * atr), font_size=self.lf + 1, text_color=color.WHITE, bg_color=self.c_bull(0.9) if d_new == 1 else self.c_bear(0.85), callout_position=callout_position.TOP_RIGHT if d_new == 1 else callout_position.BOTTOM_RIGHT)
            self.chart.draw(lb)
            self.marks.append(lb)
            self.trim_marks()
            if show_trade:
                self.ladder_clear()
                t2 = t + TRADE_BARS * tf_sec
                self.ladder_add(t, t2, entry_p, color.BLUE, line_style.SOLID)
                self.ladder_add(t, t2, sl_p, color.RED, line_style.SOLID)
                self.ladder_add(t, t2, tp1_p, color.GREEN(0.6), line_style.DASHED)
                self.ladder_add(t, t2, tp2_p, color.GREEN(0.8), line_style.DASHED)
                self.ladder_add(t, t2, tp3_p, color.GREEN, line_style.DOTTED)
        # ------------------------------------------------------------ MODULE 20/21 display
        self.d_regime = regime
        self.d_htfb = htf_b
        self.d_ext = ext_dir
        self.d_int = ms_dir
        self.d_score_l = score_long
        self.d_score_s = score_short
        self.d_tier_l = tier_long
        self.d_tier_s = tier_short
        self.d_pd = pd_pos if range_ok else math.nan
        self.d_nb_top = nb_top
        self.d_nb_bot = nb_bot
        self.d_ns_top = ns_top
        self.d_ns_bot = ns_bot
        self.d_ses = ('SB ' + sb_win_txt(sb_ctx_win)) if sb_ctx else ('London' if in_lon else ('NY' if in_ny else ('Asia' if in_asia else 'off-session')))
        self.d_adr = day_rng / adr if ((not isnan(adr)) and adr > 0) else math.nan
        self.d_nb_score = nb_score
        self.d_ns_score = ns_score
        self.d_nb_fresh = nb_fresh
        self.d_ns_fresh = ns_fresh
        self.d_nb_kind = nb_kind
        self.d_ns_kind = ns_kind
        self.d_ema_b = ema_bias
        self.d_hs_dir = hs_dir
        self.d_bias_tf = str(bias_tf.to_minutes()) if bias_tf.to_minutes() < 1440 else 'D'
        trg = '—'
        if recent_mss_up or recent_mss_dn:
            trg = 'MSS ▲' if self.l_mss_up >= self.l_mss_dn else 'MSS ▼'
        elif recent_ch_up or recent_ch_dn:
            trg = 'CHoCH ▲' if self.l_ch_up >= self.l_ch_dn else 'CHoCH ▼'
        elif self.recent(self.l_bos_up, trig_look) or self.recent(self.l_bos_dn, trig_look):
            trg = 'BOS ▲' if self.l_bos_up >= self.l_bos_dn else 'BOS ▼'
        self.d_trig = trg
        self.d_in_poi = 'in HTF demand' if cont_tap_l else ('in HTF supply' if cont_tap_s else '—')
        sw_txt = 'no sweep'
        if ssl_in_play:
            sw_txt = f'SSL Q{self.ssl_q}'
        if bsl_in_play:
            sw_txt = f'BSL Q{self.bsl_q}' if sw_txt == 'no sweep' else sw_txt + f' · BSL Q{self.bsl_q}'
        self.d_sweep = sw_txt
        self.d_tight = not range_holds
        sb_rem = ''
        if sb_win_now == 1:
            sb_rem = f' {240 - ny_min}m'
        elif sb_win_now == 2:
            sb_rem = f' {660 - ny_min}m'
        elif sb_win_now == 3:
            sb_rem = f' {900 - ny_min}m'
        ses_name = 'London' if in_lon else ('NY' if in_ny else ('Asia' if in_asia else 'off-hours'))
        self.d_sbtxt = ses_name + ' · ' + (('SB ' + sb_win_txt(sb_ctx_win) + (sb_rem if sb_win_now != 0 else ' (pre)')) if sb_ctx else 'SB off-window')
        vd = ''
        if self.trd_dir != 0:
            vd = 'IN TRADE · ' + ('LONG' if self.trd_dir == 1 else 'SHORT')
        elif self.su_l == 3 or self.su_s == 3:
            vd = 'WAIT · retest of the anchor (' + ('long' if self.su_l == 3 else 'short') + ')'
        elif self.su_l >= 1:
            vd = 'SETUP · ' + stage_txt(self.su_l) + ' long'
        elif self.su_s >= 1:
            vd = 'SETUP · ' + stage_txt(self.su_s) + ' short'
        elif regime == 'CHOP' and use_regime:
            vd = 'NO · chop regime'
        elif not (ssl_in_play or bsl_in_play):
            vd = 'NO · no sweep in play'
        elif poi_conf_raw:
            vd = 'NO · POI conflict resolved to ' + ('longs' if side_bias > 0 else ('shorts' if side_bias < 0 else 'nobody'))
        else:
            vd = 'NO · waiting for POI / shift'
        if (not isnan(adr)) and adr > 0:
            vd = vd + f' · ADR {day_rng / adr * 100:.0f}%'
        self.d_verdict = vd
        self.o_plo = prot_low_e if show_prot else math.nan
        self.o_phi = prot_high_e if show_prot else math.nan
        self.o_pdh = pdh if show_pdwl else math.nan
        self.o_pdl = pdl if show_pdwl else math.nan
        self.o_pwh = pwh if show_pdwl else math.nan
        self.o_pwl = pwl if show_pdwl else math.nan
        mk_lo_v = math.nan
        mk_lo_t = ''
        mk_hi_v = math.nan
        mk_hi_t = ''
        if show_sweeps:
            if ssl_sweep:
                mk_lo_t = '◆'
            elif eql_swept:
                mk_lo_t = '◈'
            elif pdl_sw or pwl_sw:
                mk_lo_t = '◇'
            elif ses_lo_swept:
                mk_lo_t = '▵'
            if bsl_sweep:
                mk_hi_t = '◆'
            elif eqh_swept:
                mk_hi_t = '◈'
            elif pdh_sw or pwh_sw:
                mk_hi_t = '◇'
            elif ses_hi_swept:
                mk_hi_t = '▿'
            if mk_lo_t != '':
                mk_lo_v = l
            if mk_hi_t != '':
                mk_hi_v = h
        bg_sb = plot.Background(color.TRANSPARENT)
        if sb_paint and sb_on and in_sb:
            bg_sb = plot.Background(color.TEAL(0.14 if sb_win_now == 2 else (0.10 if sb_win_now == 3 else 0.08)))
        bg_nw = plot.Background(color.TRANSPARENT)
        if paint_news and in_news:
            bg_nw = plot.Background(color.RED(0.10))
        if self.is_last_history_bar or self.is_realtime:
            self.refresh_drawings(t, show_zones, show_fvg, show_ses, False)
            self.draw_extras(t, c, atr, prec, tf_sec, zone_tests, show_poi and htf_live, show_next, next_back, show_tl)
            if show_dash:
                self.draw_dash(c, atr, prec, font, sb_ctx, self.ssl_q, self.bsl_q, ssl_in_play, bsl_in_play, dash_pos, dash_w, dash_compact)
        res_out = self.last_res if show_levels else math.nan
        sup_out = self.last_sup if show_levels else math.nan
        return res_out, sup_out, self.o_plo, self.o_phi, self.o_pdh, self.o_pdl, self.o_pwh, self.o_pwl, plot.Marker(mk_lo_v, text=mk_lo_t), plot.Marker(mk_hi_v, text=mk_hi_t), bg_sb, bg_nw

    # =========================================================================
    # helpers
    # =========================================================================
    def ny_off(self, ts: float) -> int:
        if ts < self.dst_y0 or ts >= self.dst_y1:
            y = datetime.utcfromtimestamp(ts).year
            self.dst_y0 = datetime(y, 1, 1).timestamp()
            self.dst_y1 = datetime(y + 1, 1, 1).timestamp()
            m1 = datetime(y, 3, 1)
            fs_m = 1 + (6 - m1.weekday()) % 7
            self.dst_s = datetime(y, 3, fs_m + 7, 7, 0, 0).timestamp()
            n1 = datetime(y, 11, 1)
            fs_n = 1 + (6 - n1.weekday()) % 7
            self.dst_e = datetime(y, 11, fs_n, 6, 0, 0).timestamp()
        if ts >= self.dst_s and ts < self.dst_e:
            return -4
        return -5

    def recent(self, b: int, look: int) -> bool:
        return b != NA and self.bar_index - b <= look

    def hh(self, n: int) -> float:
        r = self.high[0]
        for k in range(1, n):
            r = max(r, self.high[k])
        return r

    def ll(self, n: int) -> float:
        r = self.low[0]
        for k in range(1, n):
            r = min(r, self.low[k])
        return r

    def decay(self, ev: int, pts: float, look: int) -> float:
        if ev == NA or self.bar_index - ev > look:
            return 0.0
        return pts * (1.0 - float(self.bar_index - ev) / (look + 1.0))

    def sweep_q(self, is_low: bool, lvl: float, h: float, l: float, c: float, rng: float, body: float, atr: float, near: float) -> int:
        pen = lvl - l if is_low else h - lvl
        firm = (c >= lvl + near * atr * 0.5) if is_low else (c <= lvl - near * atr * 0.5)
        outr = (c >= l + 0.7 * rng) if is_low else (c <= h - 0.7 * rng)
        disp = body >= 0.5 * atr
        q = 1
        if firm or pen >= near * atr:
            q = 2
        if q == 2 and outr and disp:
            q = 3
        return q

    def pool_q(self, is_low: bool, lvl: float, h: float, l: float, c: float, rng: float, body: float, atr: float, near: float) -> int:
        ok = (c >= lvl + near * atr * 0.5 or lvl - l >= near * atr) if is_low else (c <= lvl - near * atr * 0.5 or h - lvl >= near * atr)
        if not ok:
            return 1
        strong = (c >= l + 0.7 * rng) if is_low else (c <= h - 0.7 * rng)
        if strong and body >= 0.5 * atr:
            return 3
        return 2

    def stamp_ssl(self, q: int, lvl: float, ext: float, kind: int, bi: int) -> None:
        if self.last_ssl_bar == bi:
            self.ssl_q_raw = max(self.ssl_q_raw, q)
            self.ssl_q = max(self.ssl_q, q)
        else:
            self.ssl_q_raw = q
            self.ssl_q = q
        self.last_ssl_bar = bi
        self.last_ssl_lvl = lvl
        self.last_ssl_ext = ext
        self.ssl_kind = kind

    def stamp_bsl(self, q: int, lvl: float, ext: float, kind: int, bi: int) -> None:
        if self.last_bsl_bar == bi:
            self.bsl_q_raw = max(self.bsl_q_raw, q)
            self.bsl_q = max(self.bsl_q, q)
        else:
            self.bsl_q_raw = q
            self.bsl_q = q
        self.last_bsl_bar = bi
        self.last_bsl_lvl = lvl
        self.last_bsl_ext = ext
        self.bsl_kind = kind

    def struct_step(self, i: int, up_brk: bool, dn_brk: bool, disp_ok: bool, h: float, l: float, c: float) -> tuple[bool, bool, bool, bool]:
        bos_u = False
        bos_d = False
        ch_u = False
        ch_d = False
        if isnan(self.st_llo[i]):
            self.st_llo[i] = l
        else:
            self.st_llo[i] = min(self.st_llo[i], l)
        if isnan(self.st_lhi[i]):
            self.st_lhi[i] = h
        else:
            self.st_lhi[i] = max(self.st_lhi[i], h)
        if disp_ok:
            d = self.st_dir[i]
            if d == 1:
                if up_brk:
                    bos_u = True
                    self.st_plo[i] = self.st_llo[i]
                elif (not isnan(self.st_plo[i])) and c < self.st_plo[i]:
                    ch_d = True
                    self.st_dir[i] = -1
                    self.st_phi[i] = self.st_lhi[i]
                    self.st_plo[i] = math.nan
            elif d == -1:
                if dn_brk:
                    bos_d = True
                    self.st_phi[i] = self.st_lhi[i]
                elif (not isnan(self.st_phi[i])) and c > self.st_phi[i]:
                    ch_u = True
                    self.st_dir[i] = 1
                    self.st_plo[i] = self.st_llo[i]
                    self.st_phi[i] = math.nan
            elif up_brk:
                bos_u = True
                self.st_dir[i] = 1
                self.st_plo[i] = self.st_llo[i]
            elif dn_brk:
                bos_d = True
                self.st_dir[i] = -1
                self.st_phi[i] = self.st_lhi[i]
            if bos_u or bos_d or ch_u or ch_d:
                self.st_llo[i] = l
                self.st_lhi[i] = h
        return bos_u, bos_d, ch_u, ch_d

    def tier(self, liq: int, poi: int, has_trig: bool, has_exec: bool, htf_ok: bool, ses_ok: bool, q_raw: int, pd_ok: bool) -> int:
        t = 1
        if has_trig and (liq >= 10 or poi >= 5):
            t = 2
        if liq >= 10 and poi >= 10 and has_trig and has_exec:
            t = 3
        if t == 3 and htf_ok and ses_ok and q_raw >= 3 and pd_ok:
            t = 4
        return t

    def mc_tier(self, qual_ok: bool, htf_ok: bool, shift_ok: bool, pd_ok: bool, pool_ok: bool, ses_ok: bool, adr_ok: bool) -> int:
        if qual_ok and htf_ok and shift_ok and pd_ok and pool_ok and ses_ok and adr_ok:
            return 4
        return 3

    def gate_txt(self, ok: bool, tier_s: str, score_ok: bool, sc: int, min_sc: int, gov_trd: bool, gov_loss: bool, cd: bool, news: bool, dow: bool, chop: bool, lock: bool, pd: bool, is_long: bool) -> str:
        if ok:
            return 'gate: tier ' + tier_s + ' below floor'
        if not score_ok:
            return f'gate: score {sc} < {min_sc}'
        if not gov_trd:
            return 'gate: daily signal limit'
        if not gov_loss:
            return 'gate: daily loss limit'
        if not cd:
            return 'gate: cooldown'
        if not news:
            return 'gate: volatility window'
        if not dow:
            return 'gate: day filter'
        if not chop:
            return 'gate: chop'
        if not lock:
            return 'gate: short narrative live' if is_long else 'gate: long narrative live'
        if not pd:
            return 'gate: premium - wrong side of range' if is_long else 'gate: discount - wrong side of range'
        return 'gate: bias / session'

    # ---- FVG registry
    def fvg_add(self, is_bull: bool, f: Fvg, keep: int, show: bool, t: float) -> None:
        col = self.c_bull if is_bull else self.c_bear
        rx = Rectangle(AbsolutePosition(f.left_t, f.top), AbsolutePosition(t, f.bot), line_style=line_style.DOTTED, line_color=col(0.3), bg_color=col(0.04))
        if show:
            self.chart.draw(rx)
        if is_bull:
            self.bfv.append(f)
            self.bfx.append(rx)
            if len(self.bfv) > keep:
                if show:
                    self.chart.erase(self.bfx[0])
                self.bfv.pop(0)
                self.bfx.pop(0)
        else:
            self.sfv.append(f)
            self.sfx.append(rx)
            if len(self.sfv) > keep:
                if show:
                    self.chart.erase(self.sfx[0])
                self.sfv.pop(0)
                self.sfx.pop(0)

    # ---- zone registry
    def zone_add(self, is_supply: bool, top: float, bot: float, star: bool, kind: str, txt: str, left_t: float, t: float) -> None:
        col = self.c_bear if is_supply else self.c_bull
        thin = kind == 'OB'
        rx = Rectangle(AbsolutePosition(left_t, top), AbsolutePosition(t, bot), line_color=col(0.25 if thin else 0.45), bg_color=col(0.04 if thin else 0.07))
        self.chart.draw(rx)
        self.zones.append(Zone(top, bot, is_supply, False, False, False, 3 if star else 2, -1, False, -1, kind, 0, False, left_t))
        self.zbx.append(rx)

    def zone_del(self, i: int) -> None:
        self.chart.erase(self.zbx[i])
        self.zones.pop(i)
        self.zbx.pop(i)

    def zone_flip(self, i: int, to_supply: bool, is_brk: bool) -> None:
        z = self.zones[i]
        z.is_supply = to_supply
        z.flipped = True
        z.touched = False
        z.touch_bar = -1
        z.tapped50 = False
        z.signaled = False
        z.tap50_bar = -1
        z.tests = 0
        z.was_in = False
        z.kind = 'BRK' if is_brk else 'MIT'
        z.score = 3 if is_brk else 2
        col = self.c_bear if to_supply else self.c_bull
        rx = self.zbx[i]
        rx.line_color = col(0.45)
        rx.bg_color = col(0.07)
        rx.line_style = line_style.DASHED
        self.chart.draw(rx)

    def zone_overlap(self, is_supply: bool, top: float, bot: float) -> bool:
        for z in self.zones:
            if z.is_supply == is_supply and not (bot > z.top or top < z.bot):
                return True
        return False

    def claim_band(self, is_supply: bool, top: float, bot: float, min_h: float) -> None:
        for k in range(len(self.zones) - 1, -1, -1):
            zo = self.zones[k]
            if zo.is_supply != is_supply and not (zo.bot > top or zo.top < bot):
                ot = zo.top
                ob = zo.bot
                if is_supply:
                    ot = min(ot, bot)
                else:
                    ob = max(ob, top)
                if ot - ob < min_h:
                    self.zone_del(k)
                elif is_supply:
                    zo.top = ot
                    self.zbx[k].point_a = AbsolutePosition(zo.left_t, ot)
                    self.chart.draw(self.zbx[k])
                else:
                    zo.bot = ob
                    self.zbx[k].point_b = AbsolutePosition(self.zbx[k].point_b.time, ob)
                    self.chart.draw(self.zbx[k])

    # ---- tracker
    def trade_open(self, d: int, ent: float, sl: float, tp1: float, tp2: float, tp3: float, is_sb: bool, win: int, shift_g: int, bi: int) -> None:
        self.trd_dir = d
        self.trd_entry = ent
        self.trd_sl = sl
        self.trd_tp1 = tp1
        self.trd_tp2 = tp2
        self.trd_tp3 = tp3
        self.trd_bar = bi
        self.trd_tp1_hit = False
        self.trd_tp2_hit = False
        self.trd_is_sb = is_sb
        self.trd_sb_win = win
        self.trd_shift_g = shift_g

    # ---- drawings
    def mark(self, txt: str, t: float, price: float, bg: Color, tc: Color, fs: int) -> None:
        lb = LabelAbs(txt, AbsolutePosition(t, price), font_size=fs, text_color=tc, bg_color=bg)
        self.chart.draw(lb)
        self.marks.append(lb)
        self.trim_marks()

    def trim_marks(self) -> None:
        while len(self.marks) > 120:
            self.chart.erase(self.marks[0])
            self.marks.pop(0)

    def ladder_add(self, t1: float, t2: float, p: float, col: Color, st: line_style) -> None:
        ln = LineSegment(AbsolutePosition(t1, p), AbsolutePosition(t2, p), color=col, line_style=st, line_width=2)
        self.chart.draw(ln)
        self.ladder.append(ln)

    def ladder_clear(self) -> None:
        for ln in self.ladder:
            self.chart.erase(ln)
        self.ladder.clear()

    def ses_lines_new(self, s: int, t: float, show: bool) -> None:
        if not show:
            return
        col = color.PURPLE if s == 0 else (color.BLUE if s == 1 else color.ORANGE)
        if self.s_drawn[s]:
            self.chart.erase(self.s_hi_ln[s])
            self.chart.erase(self.s_lo_ln[s])
            self.chart.erase(self.s_hi_lb[s])
            self.chart.erase(self.s_lo_lb[s])
        self.s_hi_ln[s] = LineSegment(AbsolutePosition(t, self.s_hi_lvl[s]), AbsolutePosition(t, self.s_hi_lvl[s]), color=col(0.65), line_width=1)
        self.s_lo_ln[s] = LineSegment(AbsolutePosition(t, self.s_lo_lvl[s]), AbsolutePosition(t, self.s_lo_lvl[s]), color=col(0.65), line_width=1)
        self.s_hi_end_t[s] = 0.0
        self.s_lo_end_t[s] = 0.0
        self.s_drawn[s] = True
        self.chart.draw(self.s_hi_ln[s])
        self.chart.draw(self.s_lo_ln[s])
        tag = 'Asia' if s == 0 else ('Lon' if s == 1 else 'NY')
        self.s_hi_lb[s] = LabelAbs(tag + ' H', AbsolutePosition(t, self.s_hi_lvl[s]), font_size=self.lf, text_color=color.WHITE, bg_color=col(0.9))
        self.s_lo_lb[s] = LabelAbs(tag + ' L', AbsolutePosition(t, self.s_lo_lvl[s]), font_size=self.lf, text_color=color.WHITE, bg_color=col(0.9))
        self.chart.draw(self.s_hi_lb[s])
        self.chart.draw(self.s_lo_lb[s])

    def refresh_drawings(self, t: float, show_zones: bool, show_fvg: bool, show_ses: bool, show_pdwl: bool) -> None:
        for i in range(len(self.zones)):
            z = self.zones[i]
            self.zbx[i].point_a = AbsolutePosition(z.left_t, z.top)
            self.zbx[i].point_b = AbsolutePosition(t, z.bot)
            self.chart.draw(self.zbx[i])
        if show_fvg:
            for i in range(len(self.bfv)):
                self.bfx[i].point_b = AbsolutePosition(t, self.bfv[i].bot)
                self.chart.draw(self.bfx[i])
            for i in range(len(self.sfv)):
                self.sfx[i].point_b = AbsolutePosition(t, self.sfv[i].bot)
                self.chart.draw(self.sfx[i])
        if show_ses:
            for s in range(3):
                if self.s_drawn[s]:
                    te = self.s_hi_end_t[s] if self.s_hi_end_t[s] > 0 else t
                    self.s_hi_ln[s].point_b = AbsolutePosition(te, self.s_hi_lvl[s])
                    self.s_hi_ln[s].line_style = line_style.DASHED if self.s_hi_end_t[s] > 0 else line_style.SOLID
                    self.chart.draw(self.s_hi_ln[s])
                    tl = self.s_lo_end_t[s] if self.s_lo_end_t[s] > 0 else t
                    self.s_lo_ln[s].point_b = AbsolutePosition(tl, self.s_lo_lvl[s])
                    self.s_lo_ln[s].line_style = line_style.DASHED if self.s_lo_end_t[s] > 0 else line_style.SOLID
                    self.chart.draw(self.s_lo_ln[s])
        if show_pdwl:
            t0 = t - 86400.0
            lv: list[float] = [self.pdh, self.pdl, self.pwh, self.pwl]
            for k in range(4):
                if not isnan(lv[k]):
                    self.pd_lns[k].point_a = AbsolutePosition(t0, lv[k])
                    self.pd_lns[k].point_b = AbsolutePosition(t, lv[k])
                    self.chart.draw(self.pd_lns[k])

    def ses_tag(self, s: int, is_hi: bool, suffix: str, show: bool) -> None:
        if (not show) or (not self.s_drawn[s]):
            return
        tag = 'Asia' if s == 0 else ('Lon' if s == 1 else 'NY')
        if is_hi:
            self.s_hi_lb[s].text = tag + suffix
            self.chart.draw(self.s_hi_lb[s])
        else:
            self.s_lo_lb[s].text = tag + suffix
            self.chart.draw(self.s_lo_lb[s])

    def htf_close(self, hh: float, ll: float, cc: float, age: int, touch: int) -> None:
        self.h_n += 1
        n = self.h_n
        for i in range(len(self.hpd) - 1, -1, -1):
            pz = self.hpd[i]
            if n > pz.bar:
                inb = ll <= pz.top and hh >= pz.bot
                if inb and not pz.was_in:
                    pz.ins += 1
                pz.was_in = inb
            if cc < pz.bot or n - pz.bar > age or pz.ins > touch:
                self.hpd.pop(i)
        for i in range(len(self.hps) - 1, -1, -1):
            qz = self.hps[i]
            if n > qz.bar:
                ins = hh >= qz.bot and ll <= qz.top
                if ins and not qz.was_in:
                    qz.ins += 1
                qz.was_in = ins
            if cc > qz.top or n - qz.bar > age or qz.ins > touch:
                self.hps.pop(i)
        self.h_hist_h.append(hh)
        self.h_hist_l.append(ll)
        if len(self.h_hist_h) > 3:
            self.h_hist_h.pop(0)
            self.h_hist_l.pop(0)
        if len(self.h_hist_h) == 3:
            if ll > self.h_hist_h[0]:
                self.hpd.append(HPoi(ll, self.h_hist_h[0], n, 0, False))
                if len(self.hpd) > 3:
                    self.hpd.pop(0)
            if hh < self.h_hist_l[0]:
                self.hps.append(HPoi(self.h_hist_l[0], hh, n, 0, False))
                if len(self.hps) > 3:
                    self.hps.pop(0)

    def tl_retire(self, is_up: bool, t: float, val: float, show: bool) -> None:
        if is_up:
            if show and self.tl_up_drawn:
                self.tl_up_ln.point_b = AbsolutePosition(t, val)
                self.tl_up_ln.line_style = line_style.DASHED
                self.chart.draw(self.tl_up_ln)
                self.tl_old.append(self.tl_up_ln)
            self.tl_up_ln = LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0), color=self.c_bull(0.7), line_style=line_style.DOTTED, line_width=2)
            self.tl_up_drawn = False
            self.tl_up_slope = math.nan
            self.tl_up_near = False
        else:
            if show and self.tl_dn_drawn:
                self.tl_dn_ln.point_b = AbsolutePosition(t, val)
                self.tl_dn_ln.line_style = line_style.DASHED
                self.chart.draw(self.tl_dn_ln)
                self.tl_old.append(self.tl_dn_ln)
            self.tl_dn_ln = LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0), color=self.c_bear(0.7), line_style=line_style.DOTTED, line_width=2)
            self.tl_dn_drawn = False
            self.tl_dn_slope = math.nan
            self.tl_dn_near = False
        while len(self.tl_old) > 6:
            self.chart.erase(self.tl_old[0])
            self.tl_old.pop(0)

    def tl_drop(self, is_up: bool, show: bool) -> None:
        if is_up:
            if self.tl_up_drawn:
                self.chart.erase(self.tl_up_ln)
            self.tl_up_drawn = False
            self.tl_up_slope = math.nan
        else:
            if self.tl_dn_drawn:
                self.chart.erase(self.tl_dn_ln)
            self.tl_dn_drawn = False
            self.tl_dn_slope = math.nan

    def zone_caption(self, z: Zone, zone_tests: int) -> str:
        base = ''
        if z.kind == 'SD':
            if z.score >= 3:
                base = ('SUPPLY' if z.is_supply else 'DEMAND') + ' ★HP'
        else:
            base = z.kind
        if z.signaled:
            return (base if base != '' else z.kind) + ' ·spent'
        if z.tests > 0 and base != '':
            return base + ' ·tested'
        return base

    def draw_extras(self, t: float, c: float, atr: float, prec: int, tf_sec: float, zone_tests: int, show_poi: bool, show_next: bool, next_back: int, show_tl: bool) -> None:
        # zone captions (Indie rectangles carry no text)
        for zl in self.zlb:
            self.chart.erase(zl)
        self.zlb.clear()
        for z in self.zones:
            cap = self.zone_caption(z, zone_tests)
            if cap != '':
                col = self.c_bear if z.is_supply else self.c_bull
                zlab = LabelAbs(cap, AbsolutePosition(t, z.top if z.is_supply else z.bot), font_size=self.lf - 1, text_color=col, bg_color=self.cap_bg)
                self.chart.draw(zlab)
                self.zlb.append(zlab)
        # HTF FVG POI boxes
        for side in range(2):
            ptop = self.d_hpb_top if side == 0 else self.d_hps_top
            pbot = self.d_hpb_bot if side == 0 else self.d_hps_bot
            pin = self.d_hpb_in if side == 0 else self.d_hps_in
            if show_poi and not isnan(ptop):
                pcol = self.c_bull if side == 0 else self.c_bear
                bx = self.hp_bx[side]
                bx.point_a = AbsolutePosition(t - 10.0 * tf_sec, ptop)
                bx.point_b = AbsolutePosition(t + 15.0 * tf_sec, pbot)
                bx.line_color = pcol(0.5)
                bx.bg_color = pcol(0.05)
                self.chart.draw(bx)
                lb = self.hp_lb[side]
                lb.text = 'HTF ' + self.d_htf_lbl + (' demand' if side == 0 else ' supply') + (' · fresh' if pin == 0 else f' · x{pin}')
                lb.position = AbsolutePosition(t + 15.0 * tf_sec, ptop if side == 1 else pbot)
                lb.text_color = pcol
                lb.bg_color = self.cap_bg
                lb.font_size = self.lf - 1
                self.chart.draw(lb)
                self.hp_drawn[side] = True
            elif self.hp_drawn[side]:
                self.chart.erase(self.hp_bx[side])
                self.chart.erase(self.hp_lb[side])
                self.hp_drawn[side] = False
        # NEXT BUY / NEXT SELL
        for side in range(2):
            ntop = self.d_nb_top if side == 0 else self.d_ns_top
            nbot = self.d_nb_bot if side == 0 else self.d_ns_bot
            if show_next and not isnan(ntop):
                ncol = self.c_bull if side == 0 else self.c_bear
                lvl = ntop if side == 0 else nbot
                back = float(next_back) if side == 0 else float(next_back) * 0.7
                ln = self.nx_ln[side]
                ln.point_a = AbsolutePosition(t - back * tf_sec, lvl)
                ln.point_b = AbsolutePosition(t, lvl)
                ln.color = ncol(0.9)
                ln.line_style = line_style.DASHED
                ln.line_width = 1
                self.chart.draw(ln)
                inside = c <= ntop and c >= nbot
                dist = abs(c - lvl) / atr
                sc = self.d_nb_score if side == 0 else self.d_ns_score
                fr = self.d_nb_fresh if side == 0 else self.d_ns_fresh
                kd = self.d_nb_kind if side == 0 else self.d_ns_kind
                txt = ('BUY' if side == 0 else 'SELL') + f' T{sc} ' + px(nbot, prec) + '-' + px(ntop, prec)
                txt = txt + (' (INSIDE)' if inside else f' ({dist:.1f}A)') + (' fresh' if fr else '') + (' HTF' if kd == 'HTF' else '')
                nl = self.nx_lb[side]
                nl.text = txt
                nl.position = AbsolutePosition(t - back * tf_sec, lvl)
                nl.bg_color = ncol(0.92)
                nl.text_color = color.WHITE
                nl.font_size = self.lf
                self.chart.draw(nl)
                self.nx_drawn[side] = True
            elif self.nx_drawn[side]:
                self.chart.erase(self.nx_ln[side])
                self.chart.erase(self.nx_lb[side])
                self.nx_drawn[side] = False
        # live trendlines
        bi = self.bar_index
        if show_tl and not isnan(self.tl_up_slope):
            self.tl_up_ln.point_a = AbsolutePosition(self.tl_up_t0, self.tl_up_p0)
            self.tl_up_ln.point_b = AbsolutePosition(t, self.tl_up_price + self.tl_up_slope * float(bi - self.tl_up_bar))
            self.tl_up_ln.line_style = line_style.SOLID if self.tl_up_touch >= 1 else line_style.DOTTED
            self.chart.draw(self.tl_up_ln)
            self.tl_up_drawn = True
        if show_tl and not isnan(self.tl_dn_slope):
            self.tl_dn_ln.point_a = AbsolutePosition(self.tl_dn_t0, self.tl_dn_p0)
            self.tl_dn_ln.point_b = AbsolutePosition(t, self.tl_dn_price + self.tl_dn_slope * float(bi - self.tl_dn_bar))
            self.tl_dn_ln.line_style = line_style.SOLID if self.tl_dn_touch >= 1 else line_style.DOTTED
            self.chart.draw(self.tl_dn_ln)
            self.tl_dn_drawn = True

    def drow(self, k: str, v: str, bg: Color) -> None:
        self.dash.append(TableRow([TableCell(k), TableCell(v, bg_color=bg)]))

    def draw_dash(self, c: float, atr: float, prec: int, font: int, sb_ctx: bool, ssl_q: int, bsl_q: int, ssl_ip: bool, bsl_ip: bool, dash_pos: str, dash_w: float, compact: bool) -> None:
        tb = self.dash
        tb.clear()
        tb.font_size = font
        is_right = dash_pos == 'Top right' or dash_pos == 'Bottom right'
        is_bottom = dash_pos == 'Bottom right' or dash_pos == 'Bottom left'
        x = max(0.0, 0.995 - dash_w) if is_right else 0.06
        tb.position = RelativePosition(va.BOTTOM if is_bottom else va.TOP, ha.LEFT, 0.97 if is_bottom else 0.03, x)
        g = color.rgba(8, 153, 129, 0.40)
        r = color.rgba(242, 54, 69, 0.40)
        n = color.rgba(60, 66, 80, 0.55)
        reg_bg = g if self.d_regime == 'TRENDING' else (r if self.d_regime == 'CHOP' else n)
        tb.append(TableRow([TableCell('LQ-SD-PA v3.8.6', text_color=color.WHITE, bg_color=color.NAVY(0.85)), TableCell(self.d_regime, text_color=color.WHITE, bg_color=reg_bg)]))
        bias_txt = arrow(self.d_ema_b) + ' · D ' + arrow(self.d_bias) + ' · str ' + arrow(self.d_hs_dir) + ' → ' + arrow(self.d_htfb)
        self.drow('Bias ' + self.d_bias_tf, bias_txt, g if self.d_htfb > 0 else (r if self.d_htfb < 0 else n))
        ia = '▲' if self.d_int > 0 else ('▼' if self.d_int < 0 else '—')
        ea = '▲' if self.d_ext > 0 else ('▼' if self.d_ext < 0 else '—')
        self.drow('Struct · sweep', 'int ' + ia + ' ext ' + ea + ' · ' + self.d_sweep, g if self.d_ext > 0 else (r if self.d_ext < 0 else n))
        pdt = '-'
        pd_bg = n
        if not isnan(self.d_pd):
            pdt = ('Prem ' if self.d_pd >= 0.5 else 'Disc ') + f'{self.d_pd * 100:.0f}%' + (' ·tight' if self.d_tight else '')
            pd_bg = r if self.d_pd >= 0.5 else g
        self.drow('Range pos', pdt, pd_bg)
        nb = '—'
        if not isnan(self.d_nb_top):
            ins_b = c <= self.d_nb_top and c >= self.d_nb_bot
            nb = f'T{self.d_nb_score} · ' + ('INSIDE' if ins_b else f'{(c - self.d_nb_top) / atr:.1f} ATR') + (' · fresh' if self.d_nb_fresh else '') + (' · HTF' if self.d_nb_kind == 'HTF' else '')
        ns = '—'
        if not isnan(self.d_ns_bot):
            ins_s = c <= self.d_ns_top and c >= self.d_ns_bot
            ns = f'T{self.d_ns_score} · ' + ('INSIDE' if ins_s else f'{(self.d_ns_bot - c) / atr:.1f} ATR') + (' · fresh' if self.d_ns_fresh else '') + (' · HTF' if self.d_ns_kind == 'HTF' else '')
        self.drow('Next demand', nb, color.rgba(8, 153, 129, 0.22))
        self.drow('Next supply', ns, color.rgba(242, 54, 69, 0.22))
        self.drow('Trigger · HTF POI', self.d_trig + ' · ' + self.d_in_poi, n)
        sl_t = stage_txt(self.su_l).lower() + ('' if self.sb_tag_l == 0 else ' SB')
        ss_t = stage_txt(self.su_s).lower() + ('' if self.sb_tag_s == 0 else ' SB')
        self.drow('Setup L / S', sl_t + '  /  ' + ss_t, g if self.su_l >= 2 else (r if self.su_s >= 2 else n))
        self.drow('Alignment', f'L {self.d_score_l} (' + tier_txt(self.d_tier_l) + f')  S {self.d_score_s} (' + tier_txt(self.d_tier_s) + ')', n)
        self.drow('Session', self.d_sbtxt, color.rgba(0, 128, 128, 0.35) if sb_ctx else n)
        trd = 'flat'
        if self.trd_dir != 0:
            trd = ('LONG ' if self.trd_dir == 1 else 'SHORT ') + px(self.trd_entry, prec) + ' · SL ' + px(self.trd_sl, prec) + (' · TP1 hit' if self.trd_tp1_hit else '')
        elif self.pend_dir != 0:
            trd = 'pending (next open)'
        self.drow('Trade', trd, g if self.trd_dir == 1 else (r if self.trd_dir == -1 else n))
        vd_bg = r if self.d_verdict[0:2] == 'NO' else g
        self.drow('Verdict', self.d_verdict, vd_bg)
        if not compact:
            self.drow('Why L', self.su_l_reason[0:40] if self.su_l_reason != '' else '—', n)
            self.drow('Why S', self.su_s_reason[0:40] if self.su_s_reason != '' else '—', n)
            self.drow('Last signal', self.last_sig_txt if self.last_sig_txt != '' else '—', n)
            self.drow('Stats', f'L/S {self.cnt_long}/{self.cnt_short} · TP {self.cnt_tp1}/{self.cnt_tp2}/{self.cnt_tp3} · SL {self.cnt_sl} · BE {self.cnt_be}', n)
        self.chart.draw(tb)
