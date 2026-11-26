# indie:lang_version = 5
# BUILD SMC-v8.5.4-EXNESS-CORE-2 (structure / FVG / liquidity / zones / HTF / panel; setups = SIGNALS file) · 2026-11-08 · source = SMC_Pattern/SMC_v8.5.4.txt (Pine v6, 4250 lines)
# =============================================================================
#  SMC / ICT SUITE v8.5.4  —  Exness Terminal (Indie) port
#
#  Logic is ported 1:1 from the Pine file (same layer order, same defaults):
#   L0 candle anatomy · L1 structure (BOS / CHoCH / weak / internal / CISD / pullback)
#   L2 FVG engine + move strength · L3 liquidity (BSL/SSL/EQH/EQL/PDH/PDL/PWH/PWL/SESH/SESL,
#   sweep / run / pend, POOL) · L4 zones (SR/KL, OB T1/T1b/T2/G2, BRK, RCB, QM, RJB, PROP,
#   IDM✓, ★★, ⚠SWEEP REQ) · L5 HTF (own HTF candles from chart bars, bias, HTF FVG, HTF PD)
#   L6 setups M01 M02 M05 M08 M09 M10 M15 M33 M36 M37 M39 M40 M41 M42 M45 M46 M51 M54
#      M58 M62 M64 M68 M69 M70 M72 M73 M74 · POI tap → confirm machine · rank pick
#   L7 trade engine (f_stop / f_sig / f_conf / path check / R-14 LIQ TP / identity /
#      gap / RETRACE + M74 limits ⏳ / ✖ filled → SL) · labels · lines · panel · legend
#  Not portable (Indie has no API for them): alerts / alertcondition, label tooltips,
#  data-window plots, volume key-level criterion (default OFF in Pine anyway).
#  Engine runs on CLOSED bars only (Pine barstate.isconfirmed).
# =============================================================================
import math
from math import isnan
from datetime import datetime
from dataclasses import dataclass
from indie import indicator, param, plot, color, line_style, MainContext, SeriesF, Color
from indie.algorithms import Atr
from indie.drawings import LabelAbs, AbsolutePosition, RelativePosition, LineSegment, Rectangle, Table, TableRow, TableCell, callout_position
from indie.drawings import vertical_anchor as va, horizontal_anchor as ha

NA_I = -999


def nz(x: float, d: float) -> float:
    if isnan(x):
        return d
    return x


def ca(c: Color, t: int) -> Color:
    # Pine color.new(c, transparency 0..100) -> Indie alpha 0..1
    a = float(100 - t) / 100.0
    if a < 0.0:
        a = 0.0
    return c(a)


def f1(x: float) -> str:
    # Pine str.tostring(x, "#.#")
    r = math.floor(x * 10.0 + 0.5) / 10.0
    if abs(r - math.floor(r)) < 0.000001:
        return f'{r:.0f}'
    return f'{r:.1f}'


def f0(x: float) -> str:
    # Pine str.tostring(x, "#")
    r = math.floor(x + 0.5)
    return f'{r:.0f}'


def px(x: float, prec: int) -> str:
    if isnan(x):
        return '—'
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


def piv_hi(src: SeriesF, p: int, avail: int) -> float:
    # Pine ta.pivothigh(src, p, p): value of the bar p back when no left bar is higher and every right bar is lower
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


def lst_piv_hi(a: list[float], p: int) -> float:
    # pivot high on a list of COMPLETED HTF candles, centre = the candle p before the last one
    n = len(a)
    if n < 2 * p + 1:
        return math.nan
    ci = n - 1 - p
    c = a[ci]
    for k in range(1, p + 1):
        if a[ci - k] > c or a[ci + k] >= c:
            return math.nan
    return c


def lst_piv_lo(a: list[float], p: int) -> float:
    n = len(a)
    if n < 2 * p + 1:
        return math.nan
    ci = n - 1 - p
    c = a[ci]
    for k in range(1, p + 1):
        if a[ci - k] < c or a[ci + k] <= c:
            return math.nan
    return c


def parse_ymd(s: str) -> float:
    # 'YYYY-MM-DD' -> unix seconds (Indie forbids datetime.strptime); -1.0 if not a valid date
    if len(s) < 10:
        return -1.0
    for k in [0, 1, 2, 3, 5, 6, 8, 9]:
        ch = s[k:k + 1]
        if ch < '0' or ch > '9':
            return -1.0
    y = int(s[0:4])
    m = int(s[5:7])
    d = int(s[8:10])
    if m < 1 or m > 12 or d < 1 or d > 31:
        return -1.0
    return datetime(y, m, d).timestamp()


def call_pos(s: str) -> callout_position:
    if s == 'TOP_LEFT':
        return callout_position.TOP_LEFT
    if s == 'BOTTOM_RIGHT':
        return callout_position.BOTTOM_RIGHT
    if s == 'BOTTOM_LEFT':
        return callout_position.BOTTOM_LEFT
    return callout_position.TOP_RIGHT


def is_t3_kind(k: str) -> bool:
    # Pine: str.contains(kind, "PD") or "PW" or "SES"
    return k == 'PDH' or k == 'PDL' or k == 'PWH' or k == 'PWL' or k == 'SESH' or k == 'SESL'


def is_pdpw(k: str) -> bool:
    return k == 'PDH' or k == 'PDL' or k == 'PWH' or k == 'PWL'


@dataclass
class Fvg:
    top: float
    bottom: float
    idx: int
    is_bull: bool
    mitigated: bool
    mit_idx: int
    has_bx: bool


@dataclass
class Liq:
    price: float
    idx: int
    is_high: bool
    kind: str
    ext: bool
    touches: int
    last_touch: int
    pend: int
    done: bool
    pooled: bool
    result: str
    wick_x: float
    has_ln: bool
    has_lb: bool


@dataclass
class Zone:
    kind: str
    bull: bool
    top: float
    bottom: float
    idx: int
    touches: int
    last_touch: int
    tapped: bool
    fifty_hit: bool
    broken: bool
    broken_at: int
    flipped: bool
    sweep_req: bool
    hp: bool
    weak: bool
    confirmed: bool
    pend_fvg: int
    kl: int
    idm_lvl: float
    idm_swept: bool
    near_miss: float
    near_swept: bool
    ob_type: str
    dep_strong: bool
    prop: bool
    has_bx: bool


@dataclass
class ZS:
    kind: str
    touches: int
    sweep_req: bool
    fifty: bool
    idm: bool
    hp: bool
    kl: int
    flipped: bool
    near_swept: bool
    dep_strong: bool
    top: float
    bottom: float
    prop: bool
    arr: int
    arr_mix: float
    pend: bool
    sw: int


@dataclass
class Sig:
    name: str
    side: int
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    rr: float
    score: int
    note: str
    tgt: str


def new_zs() -> ZS:
    return ZS('', 0, False, False, False, False, 0, False, False, False, math.nan, math.nan, False, 0, 0.0, False, 0)


def new_sig() -> Sig:
    return Sig('', 0, math.nan, math.nan, math.nan, math.nan, math.nan, 0.0, 0, '', '')


def new_zone(kind: str, bull: bool, top: float, bottom: float, idx: int, bi: int) -> Zone:
    return Zone(kind, bull, top, bottom, idx, 0, bi, False, False, False, 0, False, False, False, False, True, 0, 0, math.nan, False, math.nan, False, '', False, False, False)


def lvl_text(L: Liq) -> str:
    return ('POOL·' if L.pooled else '') + L.kind + ('·ext' if L.ext else '')


def z_text(z: Zone) -> str:
    t = ''
    if z.kind == 'OB':
        t = ('OB▲' if z.bull else 'OB▼') + ('★' if z.hp else '') + ((' ' + z.ob_type) if z.ob_type != '' else '')
    elif z.kind == 'SR':
        t = 'KL★' if z.kl >= 4 else ('KL' if z.kl == 3 else ('S' if z.bull else 'R'))
    else:
        t = z.kind + ('▲' if z.bull else '▼')
    t += ' FLIP' if z.flipped else ''
    t += ' ⚠SWEEP REQ' if z.sweep_req else ''
    t += ' weak' if z.weak else ''
    t += ' ?' if not z.confirmed else ''
    t += ' IDM✓' if z.idm_swept else ''
    t += ' ⇈PROP' if z.prop else ''
    t += ' ★★' if z.near_swept else ''
    return t


# =============================================================================
# MAIN
# =============================================================================
@indicator('SMC v8.5.4 CORE EXNESS', overlay_main_pane=True)
# --- 1 · General
@param.str('start_date', default='2026-10-15', title='Calculate from date YYYY-MM-DD (empty = all history; move later if Execution timed out)')
@param.str('dbg_stop', default='All layers', options=['All layers', '0 Nothing (speed test)', '1 Structure only', '2 + FVG / liquidity / zones', '3 + HTF / PD', '4 + setups (no trade engine)'], title='DIAGNOSTIC: run engine up to (use if Execution timed out)')
@param.int('atr_len', default=14, min=1, title='ATR length')
@param.int('swing_len', default=5, min=1, title='Swing length (each side)')
@param.int('max_labels', default=200, min=10, max=500, title='Max labels')
@param.int('max_lines', default=100, min=10, max=500, title='Max lines')
@param.int('min_gap', default=6, min=0, max=20, title='Min bars between labels (same side)')
@param.str('lbl_mode', default='Signals only', options=['Signals only', 'Key events', 'All events'], title='Label density')
@param.str('sym_kind', default='Forex / CFD (gold, indices, oil)', options=['Forex / CFD (gold, indices, oil)', 'Crypto / stocks'], title='Symbol type (killzone auto filter + day start)')
# --- 2 · Candle (L0)
# --- 3 · Structure (L1)
@param.str('disp_gate', default='Candle', options=['Candle', 'Off'], title='Structure needs displacement')
@param.bool('cisd_sweep', default=True, title='CISD only after a qualified liquidity sweep')
# --- 4 · FVG / Strength (L2)
@param.str('fvg_mode', default='TOUCH', options=['TOUCH', '50%', 'FULL'], title='FVG mitigation mode')
@param.int('max_fvg', default=40, min=5, max=200, title='Max FVGs tracked')
# --- 5 · Liquidity (L3)
@param.bool('show_pd', default=True, title='PDH/PDL (intraday)')
@param.bool('show_pw', default=True, title='PWH/PWL (<= daily)')
@param.str('sweep_qual', default='Major only', options=['Major only', 'Include external'], title='Sweep arms setups when the level is')
@param.bool('idm_sweep', default=True, title='Internal sweep qualifies at a confirmed zone in HTF-aligned discount / premium')
@param.int('max_levels', default=30, min=5, max=150, title='Max liquidity levels')
# --- 6 · Zones (L4)
@param.int('max_zones', default=30, min=5, max=120, title='Max zones tracked')
@param.bool('sr_trade', default=False, title='Count UNSCORED pivot wick zones as tradable zones')
@param.bool('ob_hp_only', default=False, title='OB: high-probability (liquidity hunt) only')
@param.str('tl_anchor', default='Wick', options=['Wick', 'Body'], title='Trendline anchor')
# --- 7 · HTF (L5)
@param.str('htf_mode', default='Conservative', options=['Conservative', 'Aggressive', 'Manual'], title='HTF pairing (5m->1h, 15m->4h / aggressive 5m->30m)')
@param.str('htf_manual', default='60', options=['15', '30', '60', '120', '240', 'D', 'W'], title='Manual HTF')
@param.str('gate', default='WARN', options=['OFF', 'WARN', 'STRICT'], title='HTF bias gate')
@param.str('gate_trend', default='Entering bar', options=['Entering bar', 'This bar'], title='Trend the gate reads')
@param.bool('ltf_pb', default=True, title='LTF-only trend flip = pullback (continuation modules not blocked)')
@param.int('c_look', default=3, min=1, max=10, title='HTF candle levels: candles shown')
# --- 8 · Setup filters (L6)
@param.int('arm_bars', default=30, min=5, max=200, title='Armed setup stays valid N bars')
@param.str('entry_confirm', default='CONFIRMED', options=['IMMEDIATE', 'CONFIRMED', 'MSS'], title='Zone entry trigger')
# --- 9a · Premium / Discount + Sessions
@param.bool('pd_gate', default=False, title='Block longs in premium / shorts in discount')
@param.bool('hpd', default=True, title='HTF dealing range: discount / premium +1, deep = continuation block')
@param.bool('ssn_on', default=False, title='Only signal inside a killzone')
@param.bool('ssn_fx', default=True, title='Killzone filter auto-on for forex / CFD symbols')
@param.bool('ssn_lvl', default=True, title='Asia session high / low as liquidity levels (SESH / SESL)')
# --- 9 · Visual
@param.int('fill_t', default=15, min=0, max=100, title='Label fill transparency')
@param.int('box_t', default=85, min=0, max=100, title='Zone/FVG box transparency')
@param.int('line_t', default=30, min=0, max=100, title='Line transparency')
@param.bool('filled', default=True, title='Filled label (off = text-only)')
@param.int('lbl_font', default=11, min=7, max=20, title='Label text size')
@param.int('zone_font', default=10, min=7, max=20, title='Zone / level text size')
@param.str('cap_call', default='BOTTOM_RIGHT', options=['BOTTOM_RIGHT', 'TOP_RIGHT', 'BOTTOM_LEFT', 'TOP_LEFT'], title='Zone / level caption anchor (flip if text sits outside the box)')
@param.float('lbl_off', default=0.30, min=0.0, step=0.05, title='Label offset x ATR')
@param.int('ext_bars', default=12, min=0, max=200, title='Live zones / levels extend N bars right of the last bar')
# --- 10 · Show
@param.bool('d_struct', default=True, title='Structure: BOS/CHoCH/CISD labels + major H/L')
@param.bool('d_pb', default=False, title='Structure: valid pullback PB✓')
@param.bool('d_weak_bos', default=False, title='Label weak BOS (line always drawn)')
@param.bool('d_cisd_all', default=False, title='Label every CISD (off = counter-trend only)')
@param.bool('d_fvg', default=True, title='FVG boxes')
@param.bool('d_fvg_mit', default=False, title='Keep mitigated FVG (faded)')
@param.bool('d_liq', default=True, title='Liquidity lines')
@param.bool('d_liq_evt', default=True, title='Sweep / run events')
@param.bool('d_liq_all', default=False, title='Label every BSL/SSL sweep/run (off = POOL / ext / PD / PW only)')
@param.bool('d_ob_diag', default=False, title='OB diagnostics labels (T5 no-FVG / T3 invalid)')
@param.bool('d_ob', default=True, title='OB / S&D')
@param.bool('d_brk', default=True, title='Breaker')
@param.bool('d_kl', default=True, title='Key levels')
@param.bool('d_sr', default=False, title='S/R wick zones')
@param.bool('d_rcb', default=True, title='Reclaimed')
@param.bool('d_rjb', default=True, title='Rejection')
@param.bool('d_qm', default=True, title='QM')
@param.bool('d_htf', default=True, title='HTF candle levels')
@param.bool('d_htf_evt', default=True, title='HTF sweep / manip events')
@param.bool('d_bg', default=True, title='HTF bias tint')
@param.bool('d_candle', default=False, title='Candle pattern tags (L0 debug)')
@param.bool('d_panel', default=True, title='Info panel')
@param.bool('d_legend', default=False, title='Legend')
@param.str('dash_pos', default='Bottom right', options=['Bottom right', 'Top right', 'Bottom left', 'Top left'], title='Panel position')
@param.float('dash_w', default=0.28, min=0.05, max=0.70, step=0.01, title='Panel width estimate (raise if cut off, lower to move right)')
@param.int('dash_font', default=11, min=7, max=18, title='Panel font size')
# --- 11/13/15 · Setups (toggle)
# --- 12 · Setup filters
# --- 16 · S-AB parameters
# --- 14 · Trade (L7)
@param.int('grade_ap', default=11, min=1, max=20, title='A+ >=')
@param.int('grade_a', default=9, min=1, max=20, title='A >=')
@plot.background(title='HTF bias tint', color=color.TRANSPARENT)
class Main(MainContext):
    def __init__(self):
        self.open.request_size(520)
        self.high.request_size(520)
        self.low.request_size(520)
        self.close.request_size(520)
        self.time.request_size(520)
        # Vis
        self.c_bull = color.rgba(8, 153, 129, 1.0)
        self.c_bear = color.rgba(242, 54, 69, 1.0)
        self.c_neut = color.rgba(120, 123, 134, 1.0)
        self.c_pool = color.rgba(255, 152, 0, 1.0)
        self.c_brk = color.rgba(156, 39, 176, 1.0)
        self.c_rcb = color.rgba(0, 188, 212, 1.0)
        self.c_rjb = color.rgba(255, 152, 0, 1.0)
        self.c_qm = color.rgba(233, 30, 99, 1.0)
        self.c_htf = color.rgba(41, 98, 255, 1.0)
        self.c_inv = color.rgba(120, 123, 134, 1.0)
        self.c_txt = color.WHITE
        self.box_t = 85
        self.line_t = 30
        self.lf = 11
        self.zf = 10
        self.cap_cp = callout_position.BOTTOM_RIGHT
        self.tf_sec = 300.0
        self.prec = 2
        self.t_now = 0.0
        # ---- Ctx
        self.fvgs: list[Fvg] = []
        self.fvg_bx: list[Rectangle] = []
        self.lv: list[Liq] = []
        self.lv_ln: list[LineSegment] = []
        self.lv_lb: list[LabelAbs] = []
        self.zones: list[Zone] = []
        self.z_bx: list[Rectangle] = []
        self.z_cap: list[LabelAbs] = []
        self.cur_high = math.nan
        self.prev_high = math.nan
        self.cur_high_idx = 0
        self.prev_high_idx = 0
        self.hi_broken = False
        self.cur_low = math.nan
        self.prev_low = math.nan
        self.cur_low_idx = 0
        self.prev_low_idx = 0
        self.lo_broken = False
        self.major_high = math.nan
        self.major_high_idx = 0
        self.major_low = math.nan
        self.major_low_idx = 0
        self.trend = 'RANGE'
        self.bars_since_evt = 0
        self.hi_maker_high = math.nan
        self.hi_maker_low = math.nan
        self.pb_up_armed = False
        self.lo_maker_low = math.nan
        self.lo_maker_high = math.nan
        self.pb_dn_armed = False
        self.cisd_up_open = math.nan
        self.cisd_up_bar = 0
        self.cisd_dn_open = math.nan
        self.cisd_dn_bar = 0
        self.swept_high_bar = NA_I
        self.swept_low_bar = NA_I
        self.qm_bull_pend = False
        self.qm_bull_ll = math.nan
        self.qm_bull_at = 0
        self.qm_bear_pend = False
        self.qm_bear_hh = math.nan
        self.qm_bear_at = 0
        self.h_cur_high = math.nan
        self.h_prev_high = math.nan
        self.h_hi_broken = False
        self.h_cur_low = math.nan
        self.h_prev_low = math.nan
        self.h_lo_broken = False
        self.h_major_high = math.nan
        self.h_major_low = math.nan
        self.h_trend = 'NEUTRAL'
        self.h_bar_count = 0
        self.sweep_up_at = NA_I
        self.sweep_dn_at = NA_I
        self.up_w1 = 0.0
        self.up_w2 = 0.0
        self.dn_w1 = 0.0
        self.dn_w2 = 0.0
        self.up_r1 = 0.0
        self.up_r2 = 0.0
        self.dn_r1 = 0.0
        self.dn_r2 = 0.0
        self.break_dir = 0
        self.break_lvl = math.nan
        self.break_bar = NA_I
        self.break_lo = math.nan
        self.break_hi = math.nan
        self.last_dep_strong = False
        self.last_bos_bar = NA_I
        self.last_bos_avg_body = 0.0
        self.choch_real = False
        self.arrival_strong = False
        self.arrival_bar = NA_I
        self.arrival_dir = 0
        self.arrival_avg_body = 0.0
        self.arrival_mixed = 0.0
        self.m41_dir = 0
        self.m41_bar = NA_I
        self.m45_dir = 0
        self.m45_bar = NA_I
        self.m46_dir = 0
        self.m46_bar = NA_I
        self.m54_stage = 0
        self.m54_bar = NA_I
        self.m54_stage_b = 0
        self.m54_bar_b = NA_I
        self.bull_fvg_bar = NA_I
        self.bear_fvg_bar = NA_I
        self.last_evt = '—'
        self.last_evt_bar = NA_I
        self.fifty_prev = False
        self.brk_touch = 0
        self.leg_idx = 0
        self.leg_px = math.nan
        # ---- Sx
        self.dt_dir = 0
        self.dt_bar = NA_I
        self.dt_neck = math.nan
        self.m62_dir = 0
        self.m62_bar = NA_I
        self.m62_lvl = math.nan
        self.tl_sx1 = 0
        self.tl_sy1 = math.nan
        self.tl_sx2 = 0
        self.tl_sy2 = math.nan
        self.tl_s_touch = 0
        self.tl_s_broken = False
        self.tl_rx1 = 0
        self.tl_ry1 = math.nan
        self.tl_rx2 = 0
        self.tl_ry2 = math.nan
        self.tl_r_touch = 0
        self.tl_r_broken = False
        self.m68_dir = 0
        self.m68_bar = NA_I
        self.ifc_dir = 0
        self.ifc_bar = NA_I
        self.ifc_hi = math.nan
        self.ifc_lo = math.nan
        self.m72_cnt = 0
        self.m72_wick = 0
        self.m72_dir = 0
        self.hi_type = ''
        self.lo_type = ''
        self.st_pend_dir = 0
        self.st_pend_kind = 0
        self.st_pend_bar = NA_I
        self.st_pend_lvl = math.nan
        self.st_pend_from = 0
        self.st_brk_dir = 0
        self.st_brk_lvl = math.nan
        self.st_brk_bar = NA_I
        self.st_fail = 0
        self.brk_internal = False
        self.cisd_up_ref = math.nan
        self.cisd_up_ref_bar = 0
        self.cisd_up_used = True
        self.cisd_dn_ref = math.nan
        self.cisd_dn_ref_bar = 0
        self.cisd_dn_used = True
        self.poi_dir_l = 0
        self.poi_bar_l = NA_I
        self.poi_ref_l = math.nan
        self.poi_low_l = math.nan
        self.poi_fvg_l = False
        self.poi_zb = new_zs()
        self.poi_zb_ok = False
        self.poi_dir_s = 0
        self.poi_bar_s = NA_I
        self.poi_ref_s = math.nan
        self.poi_high_s = math.nan
        self.poi_fvg_s = False
        self.poi_zs = new_zs()
        self.poi_zs_ok = False
        self.poi_wick_l = 0.0
        self.poi_wick_s = 0.0
        self.poi_sw_l = 0
        self.poi_sw_s = 0
        self.h_fvg_bt = math.nan
        self.h_fvg_bb = math.nan
        self.h_fvg_st = math.nan
        self.h_fvg_sb = math.nan
        self.h_fvg_b_bar = 0
        self.h_fvg_s_bar = 0
        self.m54_zb = math.nan
        self.m54_zs = math.nan
        self.m10_dir = 0
        self.m10_bar = NA_I
        self.m10_ref = math.nan
        self.m10_ext = math.nan
        self.m10_lvl = math.nan
        self.m10_kind = ''
        self.m10_base = ''
        self.m10_t3 = False
        # ---- Move (var mv) + scratch outputs
        self.mv_strong = False
        self.mv_fvg = 0
        self.mv_body_eff = 0.0
        self.mv_avg_body = 0.0
        self.ms_strong = False
        self.ms_fvg = 0
        self.ms_body_eff = 0.0
        self.ms_mixed = 0.0
        self.ms_avg_body = 0.0
        self.lo_idx = 0
        self.lo_px = math.nan
        # ---- per-bar Struct (st_*)
        self.st_swing_high = False
        self.st_swing_low = False
        self.st_bull_bos = False
        self.st_bear_bos = False
        self.st_bull_sweep = False
        self.st_bear_sweep = False
        self.st_bull_choch = False
        self.st_bear_choch = False
        self.st_int_bull = False
        self.st_int_bear = False
        self.st_weak_bull = False
        self.st_weak_bear = False
        self.st_pb_up = False
        self.st_pb_dn = False
        self.st_cisd_bull = False
        self.st_cisd_bear = False
        self.st_ch_lvl = math.nan
        self.st_ch_idx = 0
        self.st_trend = 'RANGE'
        self.st_move_phase = 'IMPULSIVE'
        # ---- per-bar Feat (ft_*)
        self.ft_new_bull_fvg = False
        self.ft_new_bear_fvg = False
        self.ft_disp_bull = False
        self.ft_disp_bear = False
        self.ft_swept_high = False
        self.ft_swept_low = False
        self.ft_swept_high_q = False
        self.ft_swept_low_q = False
        self.ft_run_up = False
        self.ft_run_dn = False
        self.ft_swept_major = False
        self.ft_run_major = False
        self.ft_swept_kind = ''
        self.ft_swept_kind_hi = ''
        self.ft_swept_kind_lo = ''
        self.ft_swept_base_hi = ''
        self.ft_swept_base_lo = ''
        self.ft_swept_t3_hi = False
        self.ft_swept_t3_lo = False
        self.ft_swept_price = math.nan
        self.ft_swept_price_hi = math.nan
        self.ft_swept_price_lo = math.nan
        self.ft_swept_ext_hi = math.nan
        self.ft_swept_ext_lo = math.nan
        self.ft_run_price = math.nan
        self.ft_bsl_above = 0
        self.ft_ssl_below = 0
        self.ft_at_demand = False
        self.ft_new_prop = False
        self.ft_at_supply = False
        self.ft_at_support = False
        self.ft_at_resist = False
        self.ft_zb = new_zs()
        self.ft_zs = new_zs()
        self.ft_evt_up = ''
        self.ft_evt_dn = ''
        self.ft_htf_bias = 'NEUTRAL'
        self.ft_gate_up = 2
        self.ft_gate_dn = 2
        self.ft_htf_sweep_up = False
        self.ft_htf_sweep_dn = False
        self.ft_htf_manip_bull = False
        self.ft_htf_manip_bear = False
        self.ft_htf_rej_bull = False
        self.ft_htf_rej_bear = False
        self.ft_in_range = False
        self.ft_at_bull_fvg = False
        self.ft_at_bear_fvg = False
        self.ft_new_ob_hp = False
        self.ft_in_htf_fvg_b = False
        self.ft_in_htf_fvg_s = False
        self.ft_htf_pd_pct = math.nan
        self.ft_pd_pct = 0.5
        self.ft_in_discount = False
        self.ft_in_premium = False
        self.ft_pd_beyond = False
        self.ft_sess_name = ''
        self.ft_sb_sess_ok = True
        self.ft_choch_real = False
        # ---- globals (Pine var)
        self.ny_open = math.nan
        self.ny_mid_prev = False
        self.in_asia_prev = False
        self.asia_hi = math.nan
        self.asia_lo = math.nan
        self.pd_hi_b = math.nan
        self.pd_hi_at = -1
        self.pd_lo_s = math.nan
        self.pd_lo_at = -1
        self.h_run_hi = math.nan
        self.h_run_lo = math.nan
        self.h_anc_lo = math.nan
        self.h_anc_hi = math.nan
        self.sig_bar = NA_I
        self.sig_dir = 0
        self.sig_score = 0
        self.last_ident = ''
        self.last_ident_bar = NA_I
        self.no_sig = new_sig()
        self.sig_l = new_sig()
        self.sig_s = new_sig()
        self.ret_l = new_sig()
        self.ret_s = new_sig()
        self.ret_l_on = False
        self.ret_s_on = False
        self.ret_bar_l = NA_I
        self.ret_bar_s = NA_I
        self.ret_px_l = math.nan
        self.ret_px_s = math.nan
        self.ret_name_l = ''
        self.ret_name_s = ''
        self.ret_lb_l = -1
        self.ret_lb_s = -1
        self.ssn_filt = False
        # ---- drawings
        self.labs: list[LabelAbs] = []
        self.lab_ids: list[int] = []
        self.lab_seq = 0
        self.lns: list[LineSegment] = []
        self.h_lns: list[LineSegment] = []
        self.h_ext: list[bool] = []
        self.hi_line = LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0))
        self.lo_line = LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0))
        self.hi_on = False
        self.lo_on = False
        self.last_up = -1
        self.last_dn = -1
        self.up_stack = 0
        self.dn_stack = 0
        self.trade_lns: list[LineSegment] = []
        self.tl_sup_ln = LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0))
        self.tl_res_ln = LineSegment(AbsolutePosition(0.0, 0.0), AbsolutePosition(0.0, 0.0))
        self.tl_sup_on = False
        self.tl_res_on = False
        self.tl_sup_ext = False
        self.tl_res_ext = False
        self.tl_sup_t = 0.0
        self.tl_sup_p = 0.0
        self.tl_sup_k = 0.0
        self.tl_res_t = 0.0
        self.tl_res_p = 0.0
        self.tl_res_k = 0.0
        # ---- own HTF / D / W candles (Pine request.security [1] + lookahead_on)
        self.hb_cur = -1
        self.hc_o = math.nan
        self.hc_h = math.nan
        self.hc_l = math.nan
        self.hc_c = math.nan
        self.hh_o: list[float] = []
        self.hh_h: list[float] = []
        self.hh_l: list[float] = []
        self.hh_c: list[float] = []
        self.htf_lbl = '60'
        self.d_cur = -1
        self.d_h = math.nan
        self.d_l = math.nan
        self.pdh = math.nan
        self.pdl = math.nan
        self.w_cur = -1
        self.w_h = math.nan
        self.w_l = math.nan
        self.pwh = math.nan
        self.pwl = math.nan
        self.dst_y0 = 0.0
        self.dst_y1 = -1.0
        self.dst_s = 0.0
        self.dst_e = 0.0
        # ---- panel
        self.dash = Table(position=RelativePosition(va.BOTTOM, ha.LEFT, 0.97, 0.70), bg_color=color.rgba(19, 23, 34, 0.92), text_color=color.rgba(220, 224, 232, 1.0), frame_color=color.rgba(90, 96, 110, 1.0), grid_color=color.rgba(50, 55, 68, 1.0))
        self.lgd = Table(position=RelativePosition(va.TOP, ha.LEFT, 0.03, 0.55), bg_color=color.rgba(19, 23, 34, 0.92), text_color=color.rgba(220, 224, 232, 1.0), frame_color=color.rgba(90, 96, 110, 1.0), grid_color=color.rgba(50, 55, 68, 1.0))
        self.last_refresh = -1
        self.eng_bi = 0
        self.eng_close = math.nan
        self.has_l = False
        self.has_s = False
        self.bg_col = color.TRANSPARENT
        self.live = False
        self.start_ts = -1.0
        self.start_str = '#'
        self.n_done = 0
        self.bl_n = ''
        self.bl_s = 0
        self.bl_t = ''
        self.bs_n = ''
        self.bs_s = 0
        self.bs_t = ''

    # =========================================================================
    def calc(self, start_date, dbg_stop, atr_len, swing_len, max_labels, max_lines, min_gap, lbl_mode, sym_kind, disp_gate, cisd_sweep, fvg_mode, max_fvg, show_pd, show_pw, sweep_qual, idm_sweep, max_levels, max_zones, sr_trade, ob_hp_only, tl_anchor, htf_mode, htf_manual, gate, gate_trend, ltf_pb, c_look, arm_bars, entry_confirm, pd_gate, hpd, ssn_on, ssn_fx, ssn_lvl, fill_t, box_t, line_t, filled, lbl_font, zone_font, cap_call, lbl_off, ext_bars, d_struct, d_pb, d_weak_bos, d_cisd_all, d_fvg, d_fvg_mit, d_liq, d_liq_evt, d_liq_all, d_ob_diag, d_ob, d_brk, d_kl, d_sr, d_rcb, d_rjb, d_qm, d_htf, d_htf_evt, d_bg, d_candle, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a):
        # fixed (former inputs, Pine defaults) — kept off the input list: Indie timed out with 192 inputs
        pin_mult = 2.0
        pin_ratio = 0.55
        star_prox = 1.0
        ifc_mult = 2.0
        ifc_any = False
        manip_wick = 0.30
        range_bars = 40
        disp_body = 0.5
        disp_rng = 0.6
        disp_dist = 0.3
        pend_bars = 3
        fail_max = 2
        fvg_min = 0.10
        fvg_age = 300
        min_fvg_str = 1
        body_eff = 0.55
        mix_max = 0.35
        speed_min = 0.35
        max_move = 150
        eq_tol = 0.10
        touch_tol = 0.15
        touch_cd = 3
        ext_lb = 50
        run_body = 0.60
        run_close = 0.25
        fail_bars = 2
        zone_age = 500
        zone_max_h = 3.0
        sweep_win = 10
        rjb_wick = 0.50
        rjb_bars = 15
        qm_bars = 60
        kl_left = 50
        kl_min = 3
        rcb_fib = True
        rjb_pend = True
        tl_tol = 0.30
        prop_win = 10
        prop_imp = 0.8
        tl_confirm = False
        htf_swing = 3
        sweep_val = 3
        rej_w = 0.50
        near_zone = 3.0
        range_len = 20
        range_max = 3.0
        pd_deep = 0.75
        ret_bars = 12
        m74_bars = 20
        atr_s = Atr.new(atr_len)
        self.box_t = box_t
        self.line_t = line_t
        self.lf = lbl_font
        self.zf = zone_font
        self.cap_cp = call_pos(cap_call)
        self.prec = self.info.price_precision
        self.tf_sec = float(self.time_frame.to_seconds())
        if not self.is_closed_bar:
            if self.is_last_bar:
                self.live_draw(ext_bars, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min, ret_bars, m74_bars)
            return plot.Background(self.bg_col)
        bi = self.bar_index
        if start_date != self.start_str:
            self.start_str = start_date
            self.start_ts = parse_ymd(start_date)
        if self.time[0] < self.start_ts:
            return plot.Background(color.TRANSPARENT)
        self.n_done += 1
        if dbg_stop[0:1] == '0':
            self.eng_bi = bi
            self.eng_close = self.close[0]
            if self.is_last_bar:
                self.live_draw(ext_bars, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min, ret_bars, m74_bars)
            return plot.Background(color.TRANSPARENT)
        if bi < 2 * swing_len + 4 or isnan(atr_s[0]) or atr_s[0] <= 0:
            return plot.Background(color.TRANSPARENT)
        atr = atr_s[0]
        tf_sec = self.tf_sec
        intra = tf_sec < 86400.0
        o = self.open[0]
        h = self.high[0]
        l = self.low[0]
        c = self.close[0]
        t = self.time[0]
        o1 = self.open[1]
        h1 = self.high[1]
        l1 = self.low[1]
        c1 = self.close[1]
        self.t_now = t
        tier_all = lbl_mode == 'All events'
        tier_key = lbl_mode != 'Signals only'
        crypto = sym_kind == 'Crypto / stocks'
        sweep_ext_ok = sweep_qual == 'Include external'
        dbg = 9 if dbg_stop == 'All layers' else (1 if dbg_stop[0:1] == '1' else (2 if dbg_stop[0:1] == '2' else (3 if dbg_stop[0:1] == '3' else 4)))
        self.reset_bar()
        # ---------------------------------------------------------------- clocks
        off = self.ny_off(t)
        ny_loc = t + float(off) * 3600.0
        ny_min = int((ny_loc - math.floor(ny_loc / 86400.0) * 86400.0) / 60.0)
        s_t = t if crypto else t + float(off + 7) * 3600.0     # forex day = 17:00 New York
        day_id = int(math.floor(s_t / 86400.0))
        week_id = int(math.floor((s_t / 86400.0 + 3.0) / 7.0))
        # HTF pairing (f_htfAuto)
        hm = 60
        if htf_mode == 'Manual':
            if htf_manual == 'D':
                hm = 1440
            elif htf_manual == 'W':
                hm = 10080
            else:
                hm = int(htf_manual)
        else:
            aggr = htf_mode == 'Aggressive'
            if tf_sec <= 60.0:
                hm = 15
            elif tf_sec <= 180.0:
                hm = 30
            elif tf_sec <= 300.0:
                hm = 30 if aggr else 60
            elif tf_sec <= 900.0:
                hm = 60 if aggr else 240
            elif tf_sec <= 1800.0:
                hm = 240
            elif tf_sec <= 14400.0:
                hm = 1440
            elif tf_sec <= 86400.0:
                hm = 10080
            else:
                hm = 43200
        self.htf_lbl = 'D' if hm == 1440 else ('W' if hm == 10080 else ('M' if hm == 43200 else str(hm)))
        hb = 0
        if hm < 1440:
            hb = int(math.floor(s_t / (float(hm) * 60.0)))
        elif hm == 1440:
            hb = day_id
        elif hm == 10080:
            hb = week_id
        else:
            dtm = datetime.utcfromtimestamp(s_t)
            hb = dtm.year * 12 + dtm.month
        new_htf = False
        if hb != self.hb_cur:
            if self.hb_cur >= 0:
                self.hh_o.append(self.hc_o)
                self.hh_h.append(self.hc_h)
                self.hh_l.append(self.hc_l)
                self.hh_c.append(self.hc_c)
                if len(self.hh_c) > 40:
                    self.hh_o.pop(0)
                    self.hh_h.pop(0)
                    self.hh_l.pop(0)
                    self.hh_c.pop(0)
                new_htf = True
            self.hb_cur = hb
            self.hc_o = o
            self.hc_h = h
            self.hc_l = l
            self.hc_c = c
        else:
            self.hc_h = max(self.hc_h, h)
            self.hc_l = min(self.hc_l, l)
            self.hc_c = c
        nh = len(self.hh_c)
        h_o1 = self.hh_o[nh - 1] if nh >= 1 else math.nan
        h_h1 = self.hh_h[nh - 1] if nh >= 1 else math.nan
        h_l1 = self.hh_l[nh - 1] if nh >= 1 else math.nan
        h_c1 = self.hh_c[nh - 1] if nh >= 1 else math.nan
        h_o2 = self.hh_o[nh - 2] if nh >= 2 else math.nan
        h_h2 = self.hh_h[nh - 2] if nh >= 2 else math.nan
        h_l2 = self.hh_l[nh - 2] if nh >= 2 else math.nan
        h_c2 = self.hh_c[nh - 2] if nh >= 2 else math.nan
        h_h3 = self.hh_h[nh - 3] if nh >= 3 else math.nan
        h_l3 = self.hh_l[nh - 3] if nh >= 3 else math.nan
        h_ph = lst_piv_hi(self.hh_h, htf_swing)
        h_pl = lst_piv_lo(self.hh_l, htf_swing)
        # D / W (PDH/PDL · PWH/PWL)
        new_day = False
        if day_id != self.d_cur:
            if self.d_cur >= 0:
                self.pdh = self.d_h
                self.pdl = self.d_l
                new_day = True
            self.d_cur = day_id
            self.d_h = h
            self.d_l = l
        else:
            self.d_h = max(self.d_h, h)
            self.d_l = min(self.d_l, l)
        new_week = False
        if week_id != self.w_cur:
            if self.w_cur >= 0:
                self.pwh = self.w_h
                self.pwl = self.w_l
                new_week = True
            self.w_cur = week_id
            self.w_h = h
            self.w_l = l
        else:
            self.w_h = max(self.w_h, h)
            self.w_l = min(self.w_l, l)
        n_day = show_pd and intra and new_day
        n_week = show_pw and tf_sec <= 86400.0 and new_week
        # sessions (New York killzones, DST-aware)
        in_asia = intra and ny_min >= 1200
        in_lon = intra and ny_min >= 120 and ny_min < 300
        in_ny = intra and ny_min >= 420 and ny_min < 600
        asia_end = intra and (not in_asia) and self.in_asia_prev
        ny_mid = intra and ny_min < 5
        if ny_mid and not self.ny_mid_prev:
            self.ny_open = o
        self.ny_mid_prev = ny_mid
        # ------------------------------------------------------- ORCHESTRATION
        ref_lo = nz(self.cur_low, l1)
        ref_hi = nz(self.cur_high, h1)
        pre_high = self.cur_high
        pre_low = self.cur_low
        pre_high_idx = self.cur_high_idx
        pre_low_idx = self.cur_low_idx
        pre_trend = self.trend
        # L0 candle
        body = abs(c - o)
        rng = h - l
        up_wick = h - max(c, o)
        dn_wick = min(c, o) - l
        body_r = 0.0
        up_r = 0.0
        dn_r = 0.0
        if rng > 0:
            body_r = body / rng
            up_r = up_wick / rng
            dn_r = dn_wick / rng
        is_bull = c > o
        is_bear = c < o
        pin_bull = dn_wick >= pin_mult * body and dn_r >= pin_ratio and up_wick <= body
        pin_bear = up_wick >= pin_mult * body and up_r >= pin_ratio and dn_wick <= body
        engulf_bull = is_bull and c >= o1 and o <= c1 and c1 < o1
        engulf_bear = is_bear and c <= o1 and o >= c1 and c1 > o1
        star_bear = pin_bear and abs(h - ref_hi) <= atr * star_prox
        ok_bull = ifc_any or c > o
        ok_bear = ifc_any or c < o
        ifc_bull = l < ref_lo and ok_bull and dn_wick >= ifc_mult * body
        ifc_bear = h > ref_hi and ok_bear and up_wick >= ifc_mult * body
        manip_bull = l < l1 and c > h1 and c > o and dn_r >= manip_wick
        manip_bear = h > h1 and c < l1 and c < o and up_r >= manip_wick
        # L2 FVG
        self.f_fvg(atr, fvg_min, fvg_mode, max_fvg, fvg_age, d_fvg, d_fvg_mit)
        # L1 structure
        disp_ok = disp_gate == 'Off' or (body_r >= disp_body and rng >= atr * disp_rng)
        sw_h = piv_hi(self.high, swing_len, bi + 1)
        sw_l = piv_lo(self.low, swing_len, bi + 1)
        self.f_structure(sw_h, sw_l, disp_ok, atr * disp_dist, pend_bars, fail_max, swing_len, range_bars, fail_bars, cisd_sweep, arm_bars)
        if dbg <= 1:
            self.eng_bi = bi
            self.eng_close = c
            if self.is_last_bar:
                self.live_draw(ext_bars, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min, ret_bars, m74_bars)
            return plot.Background(color.TRANSPARENT)
        # L2 strength (event-driven)
        bos_evt = self.st_bull_bos or self.st_bear_bos
        wk_evt = self.st_weak_bull or self.st_weak_bear or self.st_int_bull or self.st_int_bear
        if bos_evt or wk_evt:
            self.move_strength(self.leg_idx, bi, atr, self.st_bull_bos or self.st_weak_bull or self.st_int_bull, max_move, min_fvg_str, body_eff, mix_max, speed_min)
            self.mv_strong = self.ms_strong
            self.mv_fvg = self.ms_fvg
            self.mv_body_eff = self.ms_body_eff
            self.mv_avg_body = self.ms_avg_body
            self.last_dep_strong = self.mv_strong
            self.last_bos_bar = bi
            self.last_bos_avg_body = self.mv_avg_body
        if self.st_bull_choch or self.st_bear_choch:
            self.move_strength(self.leg_idx, bi, atr, self.st_bull_choch, max_move, min_fvg_str, body_eff, mix_max, speed_min)
            self.choch_real = self.ms_fvg >= 1
        self.ft_disp_bull = self.st_bull_bos and self.mv_strong
        self.ft_disp_bear = self.st_bear_bos and self.mv_strong
        self.ft_choch_real = self.choch_real
        # sessions feature + Asia range liquidity
        self.ft_sess_name = 'London' if in_lon else ('NY' if in_ny else ('Asia' if in_asia else ''))
        ssn_filt = ssn_on or (ssn_fx and not crypto)
        self.ssn_filt = ssn_filt
        self.ft_sb_sess_ok = (not ssn_filt) or (not intra) or self.ft_sess_name != ''
        if in_asia:
            if not self.in_asia_prev:
                self.asia_hi = h
                self.asia_lo = l
            else:
                self.asia_hi = max(nz(self.asia_hi, h), h)
                self.asia_lo = min(nz(self.asia_lo, l), l)
        if ssn_lvl and asia_end and not isnan(self.asia_hi) and not isnan(self.asia_lo):
            for i in range(len(self.lv) - 1, -1, -1):
                lx = self.lv[i]
                if not lx.done and (lx.kind == 'SESH' or lx.kind == 'SESL'):
                    self.lv_resolve(i, 'EXPIRED')
            self.add_level(atr, self.asia_hi, bi, True, 'SESH', True, d_liq, eq_tol)
            self.add_level(atr, self.asia_lo, bi, False, 'SESL', True, d_liq, eq_tol)
        self.in_asia_prev = in_asia
        # L3 liquidity
        ext_hi = self.hh_n(ext_lb, 0) if not isnan(sw_h) else math.nan
        ext_lo = self.ll_n(ext_lb, 0) if not isnan(sw_l) else math.nan
        self.f_liq(atr, sw_h, sw_l, ext_hi, ext_lo, n_day, n_week, d_liq, swing_len, eq_tol, near_zone, touch_tol, run_close, run_body, fail_bars, touch_cd, ext_lb, sweep_ext_ok, max_levels)
        # L4 zones
        self.f_zones(atr, sw_h, sw_l, swing_len, zone_max_h, sweep_win, rjb_wick, rjb_bars, qm_bars, kl_left, kl_min, sr_trade, ob_hp_only, rcb_fib, rjb_pend, prop_win, prop_imp, touch_cd, max_zones, zone_age, d_sr, d_kl, d_ob, d_brk, d_rcb, d_rjb, d_qm)
        if dbg <= 2:
            self.eng_bi = bi
            self.eng_close = c
            if self.is_last_bar:
                self.live_draw(ext_bars, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min, ret_bars, m74_bars)
            return plot.Background(color.TRANSPARENT)
        # L5 HTF
        self.f_htf(new_htf, h_o1, h_h1, h_l1, h_c1, h_o2, h_h2, h_l2, h_c2, h_ph, h_pl, h_h3, h_l3, sweep_val, manip_wick, rej_w)
        gate_tr = pre_trend if gate_trend == 'Entering bar' else self.st_trend
        self.ft_gate_up = self.f_gate(gate, self.ft_htf_bias, gate_tr, True)
        self.ft_gate_dn = self.f_gate(gate, self.ft_htf_bias, gate_tr, False)
        # Premium / Discount (current leg)
        if self.major_low_idx != self.pd_hi_at:
            self.pd_hi_b = self.leg_ext(True, self.major_low_idx)
        else:
            self.pd_hi_b = max(nz(self.pd_hi_b, h), h)
        self.pd_hi_at = self.major_low_idx
        if self.major_high_idx != self.pd_lo_at:
            self.pd_lo_s = self.leg_ext(False, self.major_high_idx)
        else:
            self.pd_lo_s = min(nz(self.pd_lo_s, l), l)
        self.pd_lo_at = self.major_high_idx
        bull_pd = self.st_trend == 'BULLISH' and not isnan(self.major_low)
        bear_pd = self.st_trend == 'BEARISH' and not isnan(self.major_high)
        pd_hi = self.pd_hi_b if bull_pd else (self.major_high if bear_pd else self.cur_high)
        pd_lo = self.major_low if bull_pd else (self.pd_lo_s if bear_pd else self.cur_low)
        pd_in = (not isnan(pd_hi)) and (not isnan(pd_lo)) and pd_hi > pd_lo
        self.ft_pd_beyond = pd_in and (c > pd_hi or c < pd_lo)
        self.ft_pd_pct = max(0.0, min(1.0, (c - pd_lo) / (pd_hi - pd_lo))) if pd_in else 0.5
        self.ft_in_discount = pd_in and (not self.ft_pd_beyond) and self.ft_pd_pct <= 0.5
        self.ft_in_premium = pd_in and (not self.ft_pd_beyond) and self.ft_pd_pct >= 0.5
        if pd_gate and pd_in and not self.ft_pd_beyond:
            if not self.ft_in_discount:
                self.ft_gate_up = 0
            if not self.ft_in_premium:
                self.ft_gate_dn = 0
        # E-3 context-qualified internal sweep
        if idm_sweep and self.ft_swept_low and (not self.ft_swept_low_q) and self.ft_zb.kind != '' and (not self.ft_zb.pend) and self.ft_htf_bias == 'BULL' and self.ft_in_discount:
            self.ft_swept_low_q = True
            self.ft_swept_kind_lo = 'IDM·' + self.ft_swept_kind_lo
            self.ft_swept_base_lo = 'IDM·' + self.ft_swept_base_lo
            self.swept_low_bar = bi
        if idm_sweep and self.ft_swept_high and (not self.ft_swept_high_q) and self.ft_zs.kind != '' and (not self.ft_zs.pend) and self.ft_htf_bias == 'BEAR' and self.ft_in_premium:
            self.ft_swept_high_q = True
            self.ft_swept_kind_hi = 'IDM·' + self.ft_swept_kind_hi
            self.ft_swept_base_hi = 'IDM·' + self.ft_swept_base_hi
            self.swept_high_bar = bi
        # E-7 HTF dealing range
        if nz(self.h_major_low, -1.0) != nz(self.h_anc_lo, -1.0) or isnan(self.h_run_hi):
            self.h_run_hi = h
        else:
            self.h_run_hi = max(self.h_run_hi, h)
        if nz(self.h_major_high, -1.0) != nz(self.h_anc_hi, -1.0) or isnan(self.h_run_lo):
            self.h_run_lo = l
        else:
            self.h_run_lo = min(self.h_run_lo, l)
        self.h_anc_lo = self.h_major_low
        self.h_anc_hi = self.h_major_high
        hb_bias = self.ft_htf_bias
        hpd_lo = self.h_major_low if hb_bias == 'BULL' else (min(nz(self.h_cur_low, self.h_run_lo), self.h_run_lo) if hb_bias == 'BEAR' else self.h_cur_low)
        hpd_hi = max(nz(self.h_cur_high, self.h_run_hi), self.h_run_hi) if hb_bias == 'BULL' else (self.h_major_high if hb_bias == 'BEAR' else self.h_cur_high)
        self.ft_htf_pd_pct = math.nan
        if hpd and hb_bias != 'NEUTRAL' and (not isnan(hpd_hi)) and (not isnan(hpd_lo)) and hpd_hi > hpd_lo:
            self.ft_htf_pd_pct = max(0.0, min(1.0, (c - hpd_lo) / (hpd_hi - hpd_lo)))
        # panel: last structural event
        if self.st_bull_choch or self.st_bear_choch:
            self.last_evt = ('CHoCH▲' if self.st_bull_choch else 'CHoCH▼') + (' (real)' if self.choch_real else ' (fake)')
            self.last_evt_bar = bi
        elif bos_evt:
            self.last_evt = ('BOS▲' if self.st_bull_bos else 'BOS▼') + (' strong' if self.mv_strong else ' weak')
            self.last_evt_bar = bi
        elif self.st_cisd_bull or self.st_cisd_bear:
            self.last_evt = 'CISD▲' if self.st_cisd_bull else 'CISD▼'
            self.last_evt_bar = bi
        elif self.ft_swept_high or self.ft_swept_low:
            self.last_evt = 'SWEEP ' + self.ft_swept_kind
            self.last_evt_bar = bi
        # P7b features
        self.ft_in_range = False
        if self.is_last_bar and self.bars_since_evt >= range_len:
            self.ft_in_range = (self.hh_n(range_len, 0) - self.ll_n(range_len, 0)) <= atr * range_max
        for g in self.fvgs:
            if ((not g.mitigated) or g.mit_idx == bi) and g.idx < bi - 1:
                if g.is_bull and l <= g.top and h >= g.bottom and c >= g.bottom:
                    self.ft_at_bull_fvg = True
                if (not g.is_bull) and h >= g.bottom and l <= g.top and c <= g.top:
                    self.ft_at_bear_fvg = True
        if self.ft_new_bull_fvg:
            self.bull_fvg_bar = bi
        if self.ft_new_bear_fvg:
            self.bear_fvg_bar = bi
        rel_cnt_bear = (1 if (self.ft_htf_rej_bear or self.ft_htf_sweep_up) else 0) + (1 if bi - self.bear_fvg_bar <= 3 else 0) + (1 if bi - self.swept_high_bar <= 5 else 0)
        rel_cnt_bull = (1 if (self.ft_htf_rej_bull or self.ft_htf_sweep_dn) else 0) + (1 if bi - self.bull_fvg_bar <= 3 else 0) + (1 if bi - self.swept_low_bar <= 5 else 0)
        cisd_rel = rel_cnt_bear if self.st_cisd_bear else (rel_cnt_bull if self.st_cisd_bull else 0)
        # M64 trendline engine
        tlz = atr * tl_tol
        if self.st_swing_low and (not isnan(self.prev_low)) and self.cur_low > self.prev_low:
            o1r = bi - self.prev_low_idx
            o2r = bi - self.cur_low_idx
            body_ok = tl_anchor == 'Body' and o1r >= 0 and o1r < 500 and o2r >= 0 and o2r < 500
            oo1 = min(max(o1r, 0), 499)
            oo2 = min(max(o2r, 0), 499)
            self.tl_sx1 = self.prev_low_idx
            self.tl_sy1 = min(self.open[oo1], self.close[oo1]) if body_ok else self.prev_low
            self.tl_sx2 = self.cur_low_idx
            self.tl_sy2 = min(self.open[oo2], self.close[oo2]) if body_ok else self.cur_low
            self.tl_s_touch = 2
            self.tl_s_broken = False
        if self.st_swing_high and (not isnan(self.prev_high)) and self.cur_high < self.prev_high:
            p1r = bi - self.prev_high_idx
            p2r = bi - self.cur_high_idx
            body_ok_r = tl_anchor == 'Body' and p1r >= 0 and p1r < 500 and p2r >= 0 and p2r < 500
            pp1 = min(max(p1r, 0), 499)
            pp2 = min(max(p2r, 0), 499)
            self.tl_rx1 = self.prev_high_idx
            self.tl_ry1 = max(self.open[pp1], self.close[pp1]) if body_ok_r else self.prev_high
            self.tl_rx2 = self.cur_high_idx
            self.tl_ry2 = max(self.open[pp2], self.close[pp2]) if body_ok_r else self.cur_high
            self.tl_r_touch = 2
            self.tl_r_broken = False
        slope_s = (self.tl_sy2 - self.tl_sy1) / float(self.tl_sx2 - self.tl_sx1) if self.tl_sx2 > self.tl_sx1 else 0.0
        slope_r = (self.tl_ry2 - self.tl_ry1) / float(self.tl_rx2 - self.tl_rx1) if self.tl_rx2 > self.tl_rx1 else 0.0
        tl_s_raw = self.tl_sy2 + slope_s * float(bi - self.tl_sx2) if ((not isnan(self.tl_sy2)) and self.tl_sx2 > self.tl_sx1) else math.nan
        tl_r_raw = self.tl_ry2 + slope_r * float(bi - self.tl_rx2) if ((not isnan(self.tl_ry2)) and self.tl_rx2 > self.tl_rx1) else math.nan
        tl_s_fresh = (not isnan(tl_s_raw)) and bi - self.tl_sx1 <= 250 and abs(c - tl_s_raw) <= atr * 10 and abs(slope_s) <= atr * 0.5
        tl_r_fresh = (not isnan(tl_r_raw)) and bi - self.tl_rx1 <= 250 and abs(c - tl_r_raw) <= atr * 10 and abs(slope_r) <= atr * 0.5
        tl_s = math.nan if (self.tl_s_broken or not tl_s_fresh) else tl_s_raw
        tl_r = math.nan if (self.tl_r_broken or not tl_r_fresh) else tl_r_raw
        if (not isnan(tl_s)) and bi > self.tl_sx2 + 1:
            if l <= tl_s + tlz and l >= tl_s - tlz and c > tl_s:
                self.tl_s_touch += 1
            if c < tl_s - tlz:
                self.tl_s_broken = True
        if (not isnan(tl_r)) and bi > self.tl_rx2 + 1:
            if h >= tl_r - tlz and h <= tl_r + tlz and c < tl_r:
                self.tl_r_touch += 1
            if c > tl_r + tlz:
                self.tl_r_broken = True
        tl_need = 3 if tl_confirm else 2
        tl_sup_valid = (not isnan(tl_s)) and self.tl_s_touch >= tl_need
        tl_res_valid = (not isnan(tl_r)) and self.tl_r_touch >= tl_need
        draw_tl_on = True
        if draw_tl_on:
            self.draw_tl(tl_sup_valid, tl_res_valid, slope_s, slope_r, tl_s, tl_r, t)
        # ---------------------------------------------------- labels (structure / events; setup signals = SIGNALS indicator)
        if tier_key or d_pb or d_candle or self.ft_evt_up != '' or self.ft_evt_dn != '':
            choch_base = 'CHoCH' if self.choch_real else 'CHoCH?'
            cisd_hp = cisd_rel >= 2
            xu_t = ''
            xu_c = self.c_bull
            xu_r = 0
            ev_up = self.ft_evt_up
            ev_up_t = ev_up[0:1] == 'T'
            ev_up_b = ev_up[0:3] == 'BRK'
            if d_struct and tier_key and self.st_bull_choch and (tier_all or self.choch_real):
                xu_t = choch_base + ('✕' if (self.swept_low_bar >= 0 and bi - self.swept_low_bar <= 10) else '') + '▲'
                xu_c = self.c_bull if self.choch_real else self.c_inv
                xu_r = 2
            elif d_struct and tier_key and (self.st_bull_bos or (d_weak_bos and self.st_weak_bull)):
                xu_t = ('BOS▲ ·' + str(self.mv_fvg) + 'FVG') if self.ft_disp_bull else ('BOS▲ weak' if self.st_weak_bull else 'BOS▲')
                xu_c = self.c_bull if self.ft_disp_bull else self.c_inv
                xu_r = 3
            elif d_struct and tier_all and self.st_int_bull:
                xu_t = 'iBOS▲'
                xu_c = self.c_inv
                xu_r = 3
            elif d_struct and (tier_all or (tier_key and cisd_hp)) and self.st_cisd_bull and (d_cisd_all or pre_trend != 'BULLISH'):
                xu_t = 'CISD▲' + ('★' if cisd_hp else '')
                xu_r = 4
            elif d_liq_evt and tier_key and self.ft_swept_low and (d_liq_all or self.ft_swept_major):
                xu_t = 'SWEEP✕ ' + self.ft_swept_base_lo
                xu_r = 5
            elif ev_up != '' and (d_ob_diag or not ev_up_t) and (tier_all or ev_up_b):
                xu_t = ev_up
                xu_c = self.c_brk if ev_up_b else (self.c_inv if ev_up_t else self.c_bull)
                xu_r = 6
            elif d_htf_evt and tier_key and new_htf and self.ft_htf_sweep_dn and self.h_bar_count == self.sweep_dn_at:
                xu_t = 'HTF SWEEP↓'
                xu_r = 7
            elif d_htf_evt and tier_key and new_htf and self.ft_htf_manip_bull:
                xu_t = 'HTF MANIP▲'
                xu_r = 8
            elif d_pb and self.st_pb_up:
                xu_t = 'PB✓'
                xu_r = 11
            elif d_candle and (pin_bull or ifc_bull or manip_bull or engulf_bull):
                xu_t = 'IFC▲' if ifc_bull else ('MAN▲' if manip_bull else ('PIN▲' if pin_bull else 'ENG▲'))
                xu_r = 12
            xd_t = ''
            xd_c = self.c_bear
            xd_r = 0
            ev_dn = self.ft_evt_dn
            ev_dn_t = ev_dn[0:1] == 'T'
            ev_dn_b = ev_dn[0:3] == 'BRK'
            if d_struct and tier_key and self.st_bear_choch and (tier_all or self.choch_real):
                xd_t = choch_base + ('✕' if (self.swept_high_bar >= 0 and bi - self.swept_high_bar <= 10) else '') + '▼'
                xd_c = self.c_bear if self.choch_real else self.c_inv
                xd_r = 2
            elif d_struct and tier_key and (self.st_bear_bos or (d_weak_bos and self.st_weak_bear)):
                xd_t = ('BOS▼ ·' + str(self.mv_fvg) + 'FVG') if self.ft_disp_bear else ('BOS▼ weak' if self.st_weak_bear else 'BOS▼')
                xd_c = self.c_bear if self.ft_disp_bear else self.c_inv
                xd_r = 3
            elif d_struct and tier_all and self.st_int_bear:
                xd_t = 'iBOS▼'
                xd_c = self.c_inv
                xd_r = 3
            elif d_struct and (tier_all or (tier_key and cisd_hp)) and self.st_cisd_bear and (d_cisd_all or pre_trend != 'BEARISH'):
                xd_t = 'CISD▼' + ('★' if cisd_hp else '')
                xd_r = 4
            elif d_liq_evt and tier_key and self.ft_swept_high and (d_liq_all or self.ft_swept_major):
                xd_t = 'SWEEP✕ ' + self.ft_swept_base_hi
                xd_r = 5
            elif d_struct and tier_all and (self.st_bull_sweep or self.st_bear_sweep) and (not self.ft_swept_high) and not self.ft_swept_low:
                xd_t = '✖SWEEP'
                xd_c = self.c_inv
                xd_r = 6
            elif ev_dn != '' and (d_ob_diag or not ev_dn_t) and (tier_all or ev_dn_b):
                xd_t = ev_dn
                xd_c = self.c_brk if ev_dn_b else (self.c_inv if ev_dn_t else self.c_bear)
                xd_r = 7
            elif d_htf_evt and tier_key and new_htf and self.ft_htf_sweep_up and self.h_bar_count == self.sweep_up_at:
                xd_t = 'HTF SWEEP↑'
                xd_r = 8
            elif d_htf_evt and tier_key and new_htf and self.ft_htf_manip_bear:
                xd_t = 'HTF MANIP▼'
                xd_r = 9
            elif d_pb and self.st_pb_dn:
                xd_t = 'PB✓'
                xd_r = 12
            elif d_candle and (pin_bear or ifc_bear or manip_bear or engulf_bear or star_bear):
                xd_t = 'IFC▼' if ifc_bear else ('MAN▼' if manip_bear else ('SS' if star_bear else ('PIN▼' if pin_bear else 'ENG▼')))
                xd_r = 13
            stack_win = min_gap * 2
            if xu_t != '' and (self.last_up < 0 or bi - self.last_up >= min_gap or (xu_r >= 1 and xu_r <= 5)):
                if self.last_up >= 0 and bi - self.last_up <= stack_win:
                    self.up_stack = min(self.up_stack + 1, 4)
                else:
                    self.up_stack = max(self.up_stack - 1, 0)
                self.add_label(True, l - atr * lbl_off - atr * lbl_off * 2.0 * float(self.up_stack), xu_t, xu_c, filled, fill_t, max_labels, t)
                self.last_up = bi
            if xd_t != '' and (self.last_dn < 0 or bi - self.last_dn >= min_gap or (xd_r >= 1 and xd_r <= 5)):
                if self.last_dn >= 0 and bi - self.last_dn <= stack_win:
                    self.dn_stack = min(self.dn_stack + 1, 4)
                else:
                    self.dn_stack = max(self.dn_stack - 1, 0)
                self.add_label(False, h + atr * lbl_off + atr * lbl_off * 2.0 * float(self.dn_stack), xd_t, xd_c, filled, fill_t, max_labels, t)
                self.last_dn = bi
        # ---------------------------------------------------- structure lines
        if d_struct:
            if (self.st_bull_bos or self.st_weak_bull or self.st_int_bull) and not isnan(pre_high):
                self.ev_line(pre_high_idx, pre_high, ca(self.c_bull if self.st_bull_bos else self.c_inv, 20), line_style.SOLID if self.st_bull_bos else line_style.DOTTED, max_lines, t)
            if (self.st_bear_bos or self.st_weak_bear or self.st_int_bear) and not isnan(pre_low):
                self.ev_line(pre_low_idx, pre_low, ca(self.c_bear if self.st_bear_bos else self.c_inv, 20), line_style.SOLID if self.st_bear_bos else line_style.DOTTED, max_lines, t)
            if self.st_bull_sweep and not isnan(pre_high):
                self.ev_line(pre_high_idx, pre_high, ca(self.c_inv, 30), line_style.DASHED, max_lines, t)
            if self.st_bear_sweep and not isnan(pre_low):
                self.ev_line(pre_low_idx, pre_low, ca(self.c_inv, 30), line_style.DASHED, max_lines, t)
            if self.st_bull_choch and not isnan(self.st_ch_lvl):
                self.ev_line(self.st_ch_idx, self.st_ch_lvl, ca(self.c_bull if self.choch_real else self.c_inv, 10), line_style.SOLID if self.choch_real else line_style.DASHED, max_lines, t)
            if self.st_bear_choch and not isnan(self.st_ch_lvl):
                self.ev_line(self.st_ch_idx, self.st_ch_lvl, ca(self.c_bear if self.choch_real else self.c_inv, 10), line_style.SOLID if self.choch_real else line_style.DASHED, max_lines, t)
            if self.st_cisd_bear and not isnan(self.cisd_up_ref):
                self.ev_line(max(self.cisd_up_ref_bar, bi - 30), self.cisd_up_ref, ca(self.c_bear, 40), line_style.DOTTED, max_lines, t)
            if self.st_cisd_bull and not isnan(self.cisd_dn_ref):
                self.ev_line(max(self.cisd_dn_ref_bar, bi - 30), self.cisd_dn_ref, ca(self.c_bull, 40), line_style.DOTTED, max_lines, t)
            if not isnan(self.major_high):
                self.hi_line.point_a = AbsolutePosition(self.bt(self.major_high_idx), self.major_high)
                self.hi_line.point_b = AbsolutePosition(t, self.major_high)
                self.hi_line.color = ca(self.c_bear, 50)
                self.hi_line.line_style = line_style.DASHED
                self.hi_on = True
            if not isnan(self.major_low):
                self.lo_line.point_a = AbsolutePosition(self.bt(self.major_low_idx), self.major_low)
                self.lo_line.point_b = AbsolutePosition(t, self.major_low)
                self.lo_line.color = ca(self.c_bull, 50)
                self.lo_line.line_style = line_style.DASHED
                self.lo_on = True
        # HTF candle O/H/L/C levels
        if d_htf and new_htf and not isnan(h_c1):
            self.htf_lines(h_o1, h_h1, h_l1, h_c1, c_look, t)
        # bias tint + panel snapshot
        self.bg_col = color.TRANSPARENT
        if d_bg:
            if self.ft_htf_bias == 'BULL':
                self.bg_col = ca(self.c_bull, 94)
            elif self.ft_htf_bias == 'BEAR':
                self.bg_col = ca(self.c_bear, 94)
        self.eng_bi = bi
        self.eng_close = c
        if self.is_last_bar:
            self.live_draw(ext_bars, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min, ret_bars, m74_bars)
        return plot.Background(self.bg_col)

    # =========================================================================
    # small helpers
    # =========================================================================
    def ny_off(self, ts: float) -> int:
        # US DST: 2nd Sunday of March 07:00 UTC .. 1st Sunday of November 06:00 UTC (cached per year)
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

    def bt(self, idx: int) -> float:
        # time of bar `idx` (Pine bar_index x-coordinate)
        off = self.bar_index - idx
        if off < 0:
            off = 0
        if off <= 515:
            return self.time[off]
        return self.time[0] - float(off) * self.tf_sec

    def hh_n(self, n: int, start: int) -> float:
        # highest high of n bars starting `start` bars back (Pine ta.highest(high, n)[start])
        v = self.high[start]
        nn = min(n, self.bar_index + 1 - start)
        for k in range(start + 1, start + nn):
            v = max(v, self.high[k])
        return v

    def ll_n(self, n: int, start: int) -> float:
        v = self.low[start]
        nn = min(n, self.bar_index + 1 - start)
        for k in range(start + 1, start + nn):
            v = min(v, self.low[k])
        return v

    def zs_clear(self, z: ZS) -> None:
        z.kind = ''
        z.touches = 0
        z.sweep_req = False
        z.fifty = False
        z.idm = False
        z.hp = False
        z.kl = 0
        z.flipped = False
        z.near_swept = False
        z.dep_strong = False
        z.top = math.nan
        z.bottom = math.nan
        z.prop = False
        z.arr = 0
        z.arr_mix = 0.0
        z.pend = False
        z.sw = 0

    def reset_bar(self) -> None:
        self.st_swing_high = False
        self.st_swing_low = False
        self.st_bull_bos = False
        self.st_bear_bos = False
        self.st_bull_sweep = False
        self.st_bear_sweep = False
        self.st_bull_choch = False
        self.st_bear_choch = False
        self.st_int_bull = False
        self.st_int_bear = False
        self.st_weak_bull = False
        self.st_weak_bear = False
        self.st_pb_up = False
        self.st_pb_dn = False
        self.st_cisd_bull = False
        self.st_cisd_bear = False
        self.st_ch_lvl = math.nan
        self.st_ch_idx = 0
        self.ft_new_bull_fvg = False
        self.ft_new_bear_fvg = False
        self.ft_disp_bull = False
        self.ft_disp_bear = False
        self.ft_swept_high = False
        self.ft_swept_low = False
        self.ft_swept_high_q = False
        self.ft_swept_low_q = False
        self.ft_run_up = False
        self.ft_run_dn = False
        self.ft_swept_major = False
        self.ft_run_major = False
        self.ft_swept_kind = ''
        self.ft_swept_kind_hi = ''
        self.ft_swept_kind_lo = ''
        self.ft_swept_base_hi = ''
        self.ft_swept_base_lo = ''
        self.ft_swept_t3_hi = False
        self.ft_swept_t3_lo = False
        self.ft_swept_price = math.nan
        self.ft_swept_price_hi = math.nan
        self.ft_swept_price_lo = math.nan
        self.ft_swept_ext_hi = math.nan
        self.ft_swept_ext_lo = math.nan
        self.ft_run_price = math.nan
        self.ft_bsl_above = 0
        self.ft_ssl_below = 0
        self.ft_at_demand = False
        self.ft_new_prop = False
        self.ft_at_supply = False
        self.ft_at_support = False
        self.ft_at_resist = False
        self.zs_clear(self.ft_zb)
        self.zs_clear(self.ft_zs)
        self.ft_evt_up = ''
        self.ft_evt_dn = ''
        self.ft_gate_up = 2
        self.ft_gate_dn = 2
        self.ft_htf_manip_bull = False
        self.ft_htf_manip_bear = False
        self.ft_htf_rej_bull = False
        self.ft_htf_rej_bear = False
        self.ft_in_range = False
        self.ft_at_bull_fvg = False
        self.ft_at_bear_fvg = False
        self.ft_new_ob_hp = False
        self.ft_pd_pct = 0.5
        self.ft_in_discount = False
        self.ft_in_premium = False
        self.ft_pd_beyond = False

    # =========================================================================
    # L2 FVG engine
    # =========================================================================
    def f_fvg(self, aV: float, fvg_min: float, fvg_mode: str, max_fvg: int, fvg_age: int, draw_on: bool, keep_mit: bool) -> None:
        bi = self.bar_index
        l = self.low[0]
        h = self.high[0]
        min_h = aV * fvg_min
        if bi > 2:
            if l > self.high[2] and (l - self.high[2]) >= min_h:
                self.fvg_push(Fvg(l, self.high[2], bi - 1, True, False, 0, draw_on))
                self.ft_new_bull_fvg = True
            if h < self.low[2] and (self.low[2] - h) >= min_h:
                self.fvg_push(Fvg(self.low[2], h, bi - 1, False, False, 0, draw_on))
                self.ft_new_bear_fvg = True
        for i in range(len(self.fvgs) - 1, -1, -1):
            g = self.fvgs[i]
            if (not g.mitigated) and g.idx < bi - 1:
                mid = (g.top + g.bottom) * 0.5
                lvl = mid
                if fvg_mode == 'TOUCH':
                    lvl = g.top if g.is_bull else g.bottom
                elif fvg_mode == 'FULL':
                    lvl = g.bottom if g.is_bull else g.top
                hit = (l <= lvl) if g.is_bull else (h >= lvl)
                if hit:
                    g.mitigated = True
                    g.mit_idx = bi
                    if g.has_bx:
                        rx = self.fvg_bx[i]
                        if keep_mit:
                            rx.point_b = AbsolutePosition(self.t_now, g.bottom)
                            rx.bg_color = ca(self.c_inv, 92)
                            rx.line_color = color.TRANSPARENT
                            if self.live:
                                self.chart.draw(rx)
                        else:
                            if self.live:
                                self.chart.erase(rx)
                            g.has_bx = False
            if g.mitigated and bi - g.mit_idx > fvg_age:
                if g.has_bx:
                    if self.live:
                        self.chart.erase(self.fvg_bx[i])
                self.fvgs.pop(i)
                self.fvg_bx.pop(i)
        while len(self.fvgs) > max_fvg:
            if self.fvgs[0].has_bx:
                if self.live:
                    self.chart.erase(self.fvg_bx[0])
            self.fvgs.pop(0)
            self.fvg_bx.pop(0)

    def fvg_push(self, g: Fvg) -> None:
        col = self.c_bull if g.is_bull else self.c_bear
        rx = Rectangle(AbsolutePosition(self.bt(g.idx), g.top), AbsolutePosition(self.t_now, g.bottom), line_color=color.TRANSPARENT, bg_color=ca(col, self.box_t))
        if g.has_bx:
            if self.live:
                self.chart.draw(rx)
        self.fvgs.append(g)
        self.fvg_bx.append(rx)

    def fvg_near(self, is_bull: bool, from_idx: int, to_idx: int) -> float:
        for g in self.fvgs:
            if g.is_bull == is_bull and g.idx >= from_idx and g.idx <= to_idx:
                return g.bottom if is_bull else g.top
        return math.nan

    # =========================================================================
    # legs / move strength
    # =========================================================================
    def leg_origin(self, is_bull: bool, from_idx: int) -> None:
        bi = self.bar_index
        span = min(max(bi - from_idx, 1), 490)
        span = min(span, bi)
        best_off = 1
        best_val = self.low[1] if is_bull else self.high[1]
        if span >= 2:
            for k in range(2, span + 1):
                v = self.low[k] if is_bull else self.high[k]
                if (is_bull and v < best_val) or ((not is_bull) and v > best_val):
                    best_val = v
                    best_off = k
        self.lo_idx = bi - best_off
        self.lo_px = best_val

    def leg_ext(self, is_hi: bool, from_idx: int) -> float:
        bi = self.bar_index
        span = min(max(bi - from_idx, 0), 490)
        span = min(span, bi)
        v = self.high[0] if is_hi else self.low[0]
        if span > 0:
            for k in range(1, span + 1):
                v = max(v, self.high[k]) if is_hi else min(v, self.low[k])
        return v

    def move_strength(self, from_bar: int, to_bar: int, aV: float, is_bull: bool, max_move: int, min_fvg_str: int, body_eff: float, mix_max: float, speed_min: float) -> None:
        bi = self.bar_index
        self.ms_strong = False
        self.ms_fvg = 0
        self.ms_body_eff = 0.0
        self.ms_mixed = 0.0
        self.ms_avg_body = 0.0
        fb = max(max(from_bar, to_bar - max_move + 1), 0)
        fb = max(fb, bi - 499)
        cnt = to_bar - fb + 1
        if cnt > 0 and aV > 0:
            body_sum = 0.0
            range_sum = 0.0
            flips = 0
            prev_bull = False
            for b in range(fb, to_bar + 1):
                off = bi - b
                if off >= 0 and off < 500:
                    body_sum += abs(self.close[off] - self.open[off])
                    range_sum += self.high[off] - self.low[off]
                    is_b = self.close[off] > self.open[off]
                    if b > fb and is_b != prev_bull:
                        flips += 1
                    prev_bull = is_b
            fc = 0
            for g in self.fvgs:
                if g.is_bull == is_bull and g.idx >= fb and g.idx <= to_bar and not g.mitigated:
                    fc += 1
            self.ms_fvg = fc
            self.ms_avg_body = body_sum / float(cnt)
            self.ms_body_eff = body_sum / range_sum if range_sum > 0 else 0.0
            self.ms_mixed = float(flips) / float(cnt - 1) if cnt > 1 else 0.0
            off_to = min(max(bi - to_bar, 0), 499)
            off_from = min(max(bi - fb, 0), 499)
            net_move = abs(self.close[off_to] - self.open[off_from])
            speed = net_move / float(cnt) / aV
            self.ms_strong = fc >= min_fvg_str and self.ms_body_eff >= body_eff and self.ms_mixed <= mix_max and speed >= speed_min

    # =========================================================================
    # L1 structure engine
    # =========================================================================
    def f_pend(self, d: int, kind: int, lvl: float, from_idx: int) -> None:
        self.st_pend_dir = d
        self.st_pend_kind = kind
        self.st_pend_bar = self.bar_index
        self.st_pend_lvl = lvl
        self.st_pend_from = from_idx

    def f_structure(self, sw_h: float, sw_l: float, disp_ok: bool, d_dist: float, pend_bars: int, fail_max: int, swing_len: int, range_bars: int, fail_bars: int, cisd_sweep: bool, arm_bars: int) -> None:
        bi = self.bar_index
        o = self.open[0]
        h = self.high[0]
        l = self.low[0]
        c = self.close[0]
        p_idx = bi - swing_len
        if not isnan(sw_h):
            self.st_swing_high = True
            self.hi_type = '' if isnan(self.cur_high) else ('HH' if sw_h > self.cur_high else 'LH')
        if not isnan(sw_l):
            self.st_swing_low = True
            self.lo_type = '' if isnan(self.cur_low) else ('LL' if sw_l < self.cur_low else 'HL')
        if self.st_brk_dir != 0 and bi - self.st_brk_bar >= 1:
            if bi - self.st_brk_bar <= fail_bars:
                if (self.st_brk_dir == 1 and c < self.st_brk_lvl) or (self.st_brk_dir == -1 and c > self.st_brk_lvl):
                    self.st_fail += 1
                    self.st_brk_dir = 0
                    if self.st_fail >= fail_max:
                        self.trend = 'RANGE'
            else:
                self.st_brk_dir = 0
                self.st_fail = 0
        brk_up = (not isnan(self.cur_high)) and (not self.hi_broken) and c > self.cur_high
        brk_dn = (not isnan(self.cur_low)) and (not self.lo_broken) and c < self.cur_low
        self.st_bull_sweep = (not isnan(self.cur_high)) and (not self.hi_broken) and h > self.cur_high and c <= self.cur_high
        self.st_bear_sweep = (not isnan(self.cur_low)) and (not self.lo_broken) and l < self.cur_low and c >= self.cur_low
        if brk_up and brk_dn:
            if (c - self.cur_high) >= (self.cur_low - c):
                brk_dn = False
            else:
                brk_up = False
        if brk_up:
            self.hi_broken = True
        if brk_dn:
            self.lo_broken = True
        prom_up = False
        prom_dn = False
        if self.st_pend_dir != 0:
            if bi - self.st_pend_bar > pend_bars:
                self.st_pend_dir = 0
            elif self.st_pend_dir == 1 and c > self.st_pend_lvl:
                prom_up = True
                if self.st_pend_kind == 2:
                    self.st_bull_choch = True
                    self.st_ch_lvl = self.st_pend_lvl
                    self.st_ch_idx = self.st_pend_from
                else:
                    self.st_bull_bos = True
                self.st_pend_dir = 0
            elif self.st_pend_dir == -1 and c < self.st_pend_lvl:
                prom_dn = True
                if self.st_pend_kind == 2:
                    self.st_bear_choch = True
                    self.st_ch_lvl = self.st_pend_lvl
                    self.st_ch_idx = self.st_pend_from
                else:
                    self.st_bear_bos = True
                self.st_pend_dir = 0
        ch_up_maj = self.trend == 'BEARISH' and (not isnan(self.major_high)) and c > self.major_high
        ch_dn_maj = self.trend == 'BULLISH' and (not isnan(self.major_low)) and c < self.major_low
        ch_up = ch_up_maj or (self.trend == 'BEARISH' and brk_up and self.lo_type == 'HL')
        ch_dn = ch_dn_maj or (self.trend == 'BULLISH' and brk_dn and self.hi_type == 'LH')
        ch_up_lvl = self.major_high if ch_up_maj else self.cur_high
        ch_up_idx = self.major_high_idx if ch_up_maj else self.cur_high_idx
        ch_dn_lvl = self.major_low if ch_dn_maj else self.cur_low
        ch_dn_idx = self.major_low_idx if ch_dn_maj else self.cur_low_idx
        d_brk_up = disp_ok or ((not isnan(self.cur_high)) and c - self.cur_high >= d_dist)
        d_ch_up = disp_ok or ((not isnan(self.major_high)) and c - self.major_high >= d_dist) or d_brk_up
        d_brk_dn = disp_ok or ((not isnan(self.cur_low)) and self.cur_low - c >= d_dist)
        d_ch_dn = disp_ok or ((not isnan(self.major_low)) and self.major_low - c >= d_dist) or d_brk_dn
        evt_any = self.st_bull_bos or self.st_bear_bos or self.st_bull_choch or self.st_bear_choch
        if (brk_up or ch_up) and not evt_any:
            if ch_up:
                if d_ch_up:
                    self.st_bull_choch = True
                    self.st_ch_lvl = ch_up_lvl
                    self.st_ch_idx = ch_up_idx
                else:
                    self.st_weak_bull = True
                    self.f_pend(1, 2, ch_up_lvl, ch_up_idx)
            elif self.trend == 'BEARISH':
                self.st_int_bull = True
            elif d_brk_up:
                self.st_bull_bos = True
            else:
                self.st_weak_bull = True
                self.f_pend(1, 1, self.cur_high, self.cur_high_idx)
        evt_any = self.st_bull_bos or self.st_bear_bos or self.st_bull_choch or self.st_bear_choch
        if (brk_dn or ch_dn) and (not evt_any) and (not self.st_weak_bull) and not self.st_int_bull:
            if ch_dn:
                if d_ch_dn:
                    self.st_bear_choch = True
                    self.st_ch_lvl = ch_dn_lvl
                    self.st_ch_idx = ch_dn_idx
                else:
                    self.st_weak_bear = True
                    self.f_pend(-1, 2, ch_dn_lvl, ch_dn_idx)
            elif self.trend == 'BULLISH':
                self.st_int_bear = True
            elif d_brk_dn:
                self.st_bear_bos = True
            else:
                self.st_weak_bear = True
                self.f_pend(-1, 1, self.cur_low, self.cur_low_idx)
        if self.st_bull_bos or self.st_bull_choch:
            from_i = self.st_pend_from if prom_up else (self.st_ch_idx if self.st_bull_choch else self.cur_high_idx)
            self.leg_origin(True, from_i)
            self.leg_idx = self.lo_idx
            self.leg_px = self.lo_px
            self.major_low = self.lo_px
            self.major_low_idx = self.lo_idx
            self.trend = 'BULLISH'
            self.bars_since_evt = 0
            self.st_fail = 0
            self.st_brk_dir = 1
            self.st_brk_lvl = self.st_ch_lvl if self.st_bull_choch else self.cur_high
            self.st_brk_bar = bi
            if self.st_pend_dir == -1:
                self.st_pend_dir = 0
            if self.st_bull_choch:
                self.hi_broken = True
                self.lo_broken = False
        if self.st_bear_bos or self.st_bear_choch:
            from_j = self.st_pend_from if prom_dn else (self.st_ch_idx if self.st_bear_choch else self.cur_low_idx)
            self.leg_origin(False, from_j)
            self.leg_idx = self.lo_idx
            self.leg_px = self.lo_px
            self.major_high = self.lo_px
            self.major_high_idx = self.lo_idx
            self.trend = 'BEARISH'
            self.bars_since_evt = 0
            self.st_fail = 0
            self.st_brk_dir = -1
            self.st_brk_lvl = self.st_ch_lvl if self.st_bear_choch else self.cur_low
            self.st_brk_bar = bi
            if self.st_pend_dir == 1:
                self.st_pend_dir = 0
            if self.st_bear_choch:
                self.lo_broken = True
                self.hi_broken = False
        if self.st_weak_bull or self.st_int_bull:
            self.leg_origin(True, self.cur_high_idx)
            self.leg_idx = self.lo_idx
            self.leg_px = self.lo_px
            if self.st_weak_bull:
                self.st_brk_dir = 1
                self.st_brk_lvl = self.st_pend_lvl if self.st_pend_dir == 1 else self.cur_high
                self.st_brk_bar = bi
        if self.st_weak_bear or self.st_int_bear:
            self.leg_origin(False, self.cur_low_idx)
            self.leg_idx = self.lo_idx
            self.leg_px = self.lo_px
            if self.st_weak_bear:
                self.st_brk_dir = -1
                self.st_brk_lvl = self.st_pend_lvl if self.st_pend_dir == -1 else self.cur_low
                self.st_brk_bar = bi
        if not (self.st_bull_bos or self.st_bear_bos or self.st_bull_choch or self.st_bear_choch):
            self.bars_since_evt += 1
            if self.bars_since_evt > range_bars:
                self.trend = 'RANGE'
        if not isnan(sw_h):
            self.prev_high = self.cur_high
            self.prev_high_idx = self.cur_high_idx
            self.cur_high = sw_h
            self.cur_high_idx = p_idx
            self.hi_broken = False
        if not isnan(sw_l):
            self.prev_low = self.cur_low
            self.prev_low_idx = self.cur_low_idx
            self.cur_low = sw_l
            self.cur_low_idx = p_idx
            self.lo_broken = False
        if isnan(self.hi_maker_high) or h >= self.hi_maker_high:
            self.hi_maker_high = h
            self.hi_maker_low = l
            self.pb_up_armed = True
        elif self.pb_up_armed and l < self.hi_maker_low:
            self.st_pb_up = True
            self.pb_up_armed = False
        if isnan(self.lo_maker_low) or l <= self.lo_maker_low:
            self.lo_maker_low = l
            self.lo_maker_high = h
            self.pb_dn_armed = True
        elif self.pb_dn_armed and h > self.lo_maker_high:
            self.st_pb_dn = True
            self.pb_dn_armed = False
        if self.st_bull_bos or self.st_bear_bos or self.st_bull_choch or self.st_bear_choch:
            self.hi_maker_high = h
            self.hi_maker_low = l
            self.pb_up_armed = True
            self.lo_maker_low = l
            self.lo_maker_high = h
            self.pb_dn_armed = True
        if c > o and not (self.close[1] > self.open[1]):
            self.cisd_up_open = o
            self.cisd_up_bar = bi
        if c < o and not (self.close[1] < self.open[1]):
            self.cisd_dn_open = o
            self.cisd_dn_bar = bi
        if h >= self.hi_maker_high and not isnan(self.cisd_up_open):
            self.cisd_up_ref = self.cisd_up_open
            self.cisd_up_ref_bar = self.cisd_up_bar
            self.cisd_up_used = False
        if l <= self.lo_maker_low and not isnan(self.cisd_dn_open):
            self.cisd_dn_ref = self.cisd_dn_open
            self.cisd_dn_ref_bar = self.cisd_dn_bar
            self.cisd_dn_used = False
        sw_ok_up = (not cisd_sweep) or (self.swept_high_bar >= 0 and bi - self.swept_high_bar <= arm_bars)
        sw_ok_dn = (not cisd_sweep) or (self.swept_low_bar >= 0 and bi - self.swept_low_bar <= arm_bars)
        self.st_cisd_bear = (not self.cisd_up_used) and (not isnan(self.cisd_up_ref)) and c < self.cisd_up_ref and sw_ok_up
        self.st_cisd_bull = (not self.cisd_dn_used) and (not isnan(self.cisd_dn_ref)) and c > self.cisd_dn_ref and sw_ok_dn
        if self.st_cisd_bear:
            self.cisd_up_used = True
        if self.st_cisd_bull:
            self.cisd_dn_used = True
        self.st_trend = self.trend
        if self.trend == 'RANGE':
            self.st_move_phase = 'RANGE'
        elif (self.trend == 'BULLISH' and (not isnan(self.cur_high)) and c >= self.cur_high) or (self.trend == 'BEARISH' and (not isnan(self.cur_low)) and c <= self.cur_low):
            self.st_move_phase = 'IMPULSIVE'
        else:
            self.st_move_phase = 'RETRACEMENT'

    # =========================================================================
    # L3 liquidity
    # =========================================================================
    def lvl_color(self, L: Liq) -> Color:
        if L.pooled:
            return self.c_pool
        if is_pdpw(L.kind):
            return self.c_neut
        return self.c_bear if L.is_high else self.c_bull

    def lv_resolve(self, i: int, res: str) -> None:
        L = self.lv[i]
        L.done = True
        L.result = res
        if L.has_ln:
            ln = self.lv_ln[i]
            ln.point_b = AbsolutePosition(self.t_now, L.price)
            ln.line_style = line_style.DOTTED if res == 'SWEEP' else line_style.SOLID
            ln.color = ca(self.lvl_color(L) if res == 'SWEEP' else self.c_neut, min(self.line_t + 30, 100))
            if self.live:
                self.chart.draw(ln)

    def lv_del(self, i: int) -> None:
        if self.lv[i].has_ln:
            if self.live:
                self.chart.erase(self.lv_ln[i])
        if self.lv[i].has_lb:
            if self.live:
                self.chart.erase(self.lv_lb[i])
        self.lv.pop(i)
        self.lv_ln.pop(i)
        self.lv_lb.pop(i)

    def lv_pool_style(self, i: int, lbl_idx: int, draw_on: bool) -> None:
        L = self.lv[i]
        col = self.lvl_color(L)
        if L.has_ln:
            ln = self.lv_ln[i]
            ln.point_a = AbsolutePosition(ln.point_a.time, L.price)
            ln.point_b = AbsolutePosition(ln.point_b.time, L.price)
            ln.line_width = 2
            ln.line_style = line_style.DASHED
            ln.color = ca(col, self.line_t)
            if self.live:
                self.chart.draw(ln)
        if L.has_lb:
            lb = self.lv_lb[i]
            lb.text = lvl_text(L)
            lb.text_color = col
            if self.live:
                self.chart.draw(lb)
        elif draw_on:
            lb2 = LabelAbs(lvl_text(L), AbsolutePosition(self.bt(lbl_idx), L.price), font_size=self.zf, text_color=col, bg_color=color.TRANSPARENT, callout_position=self.cap_cp)
            self.lv_lb[i] = lb2
            L.has_lb = True
            if self.live:
                self.chart.draw(lb2)

    def add_level(self, aV: float, price: float, idx: int, is_high: bool, kind: str, ext: bool, draw_on: bool, eq_tol: float) -> bool:
        bi = self.bar_index
        merged = False
        n = len(self.lv)
        if n > 0 and (kind == 'BSL' or kind == 'SSL'):
            for i in range(n - 1, -1, -1):
                L = self.lv[i]
                fam_ok = L.kind == 'BSL' or L.kind == 'SSL' or L.kind == 'EQH' or L.kind == 'EQL'
                if (not L.done) and fam_ok and L.is_high == is_high and abs(L.price - price) <= aV * eq_tol:
                    L.kind = 'EQH' if is_high else 'EQL'
                    L.touches += 1
                    L.last_touch = bi
                    L.price = (L.price + price) * 0.5
                    L.pooled = True
                    self.lv_pool_style(i, idx, draw_on)
                    merged = True
                    break
        if not merged:
            L2 = Liq(price, idx, is_high, kind, ext, 1, bi, 0, False, False, '', math.nan, draw_on, False)
            ln = LineSegment(AbsolutePosition(self.bt(idx), price), AbsolutePosition(self.t_now, price), color=ca(self.lvl_color(L2), self.line_t), line_style=line_style.DOTTED, line_width=1)
            if draw_on:
                if self.live:
                    self.chart.draw(ln)
            self.lv.append(L2)
            self.lv_ln.append(ln)
            self.lv_lb.append(LabelAbs('', AbsolutePosition(0.0, 0.0)))
        return merged

    def f_liq(self, aV: float, sw_h: float, sw_l: float, e_hi: float, e_lo: float, n_day: bool, n_week: bool, draw_on: bool, swing_len: int, eq_tol: float, near_zone: float, touch_tol: float, run_close: float, run_body: float, fail_bars: int, touch_cd: int, ext_lb: int, sweep_ext_ok: bool, max_levels: int) -> None:
        bi = self.bar_index
        h = self.high[0]
        l = self.low[0]
        c = self.close[0]
        o = self.open[0]
        p_idx = bi - swing_len
        rng = h - l
        body_rr = abs(c - o) / rng if rng > 0 else 0.0
        if not isnan(sw_h):
            self.add_level(aV, sw_h, p_idx, True, 'BSL', sw_h >= e_hi, draw_on, eq_tol)
        if not isnan(sw_l):
            self.add_level(aV, sw_l, p_idx, False, 'SSL', sw_l <= e_lo, draw_on, eq_tol)
        if n_day and not isnan(self.pdh):
            for i in range(len(self.lv) - 1, -1, -1):
                if (not self.lv[i].done) and (self.lv[i].kind == 'PDH' or self.lv[i].kind == 'PDL'):
                    self.lv_resolve(i, 'EXPIRED')
            self.add_level(aV, self.pdh, bi, True, 'PDH', False, draw_on, eq_tol)
            self.add_level(aV, self.pdl, bi, False, 'PDL', False, draw_on, eq_tol)
        if n_week and not isnan(self.pwh):
            for i in range(len(self.lv) - 1, -1, -1):
                if (not self.lv[i].done) and (self.lv[i].kind == 'PWH' or self.lv[i].kind == 'PWL'):
                    self.lv_resolve(i, 'EXPIRED')
            self.add_level(aV, self.pwh, bi, True, 'PWH', False, draw_on, eq_tol)
            self.add_level(aV, self.pwl, bi, False, 'PWL', False, draw_on, eq_tol)
        scan_d = aV * near_zone
        for i in range(len(self.lv) - 1, -1, -1):
            L = self.lv[i]
            if L.done:
                if bi - L.last_touch > ext_lb * 4:
                    self.lv_del(i)
                continue
            if L.idx >= bi:
                continue
            tol = aV * touch_tol
            min_go = aV * run_close
            if L.is_high:
                if L.pend > 0:
                    L.wick_x = max(L.wick_x, h)
                    if c < L.price:
                        self.lv_resolve(i, 'SWEEP')
                    else:
                        L.pend -= 1
                        if L.pend == 0:
                            self.lv_resolve(i, 'RUN')
                elif h > L.price:
                    if c <= L.price:
                        self.lv_resolve(i, 'SWEEP')
                    elif body_rr >= run_body and (c - L.price) >= min_go:
                        self.lv_resolve(i, 'RUN')
                    else:
                        L.pend = fail_bars
                        L.wick_x = h
                elif h >= L.price - tol and bi - L.last_touch > touch_cd:
                    L.touches += 1
                    L.last_touch = bi
            else:
                if L.pend > 0:
                    L.wick_x = min(L.wick_x, l)
                    if c > L.price:
                        self.lv_resolve(i, 'SWEEP')
                    else:
                        L.pend -= 1
                        if L.pend == 0:
                            self.lv_resolve(i, 'RUN')
                elif l < L.price:
                    if c >= L.price:
                        self.lv_resolve(i, 'SWEEP')
                    elif body_rr >= run_body and (L.price - c) >= min_go:
                        self.lv_resolve(i, 'RUN')
                    else:
                        L.pend = fail_bars
                        L.wick_x = l
                elif l <= L.price + tol and bi - L.last_touch > touch_cd:
                    L.touches += 1
                    L.last_touch = bi
            if L.touches >= 3 and not L.pooled:
                L.pooled = True
                self.lv_pool_style(i, L.idx, draw_on)
            if L.done:
                if L.result == 'SWEEP':
                    qual = L.pooled or is_t3_kind(L.kind) or (sweep_ext_ok and L.ext)
                    if L.is_high:
                        self.ft_swept_high = True
                        self.ft_swept_ext_hi = max(nz(L.wick_x, h), h)
                        if qual:
                            self.ft_swept_high_q = True
                            self.swept_high_bar = bi
                        self.ft_swept_kind_hi = lvl_text(L)
                        self.ft_swept_base_hi = L.kind
                        self.ft_swept_t3_hi = is_t3_kind(L.kind)
                        self.ft_swept_price_hi = L.price
                    else:
                        self.ft_swept_low = True
                        self.ft_swept_ext_lo = min(nz(L.wick_x, l), l)
                        if qual:
                            self.ft_swept_low_q = True
                            self.swept_low_bar = bi
                        self.ft_swept_kind_lo = lvl_text(L)
                        self.ft_swept_base_lo = L.kind
                        self.ft_swept_t3_lo = is_t3_kind(L.kind)
                        self.ft_swept_price_lo = L.price
                    self.ft_swept_kind = lvl_text(L)
                    self.ft_swept_price = L.price
                    self.ft_swept_major = self.ft_swept_major or L.pooled or is_pdpw(L.kind)
                if L.result == 'RUN':
                    if L.is_high:
                        self.ft_run_up = True
                    else:
                        self.ft_run_dn = True
                    self.ft_run_price = L.price
                    self.ft_run_major = self.ft_run_major or L.pooled or L.ext or is_pdpw(L.kind)
            else:
                if L.is_high and L.price > c and L.price - c <= scan_d:
                    self.ft_bsl_above += 1
                if (not L.is_high) and L.price < c and c - L.price <= scan_d:
                    self.ft_ssl_below += 1
        while len(self.lv) > max_levels:
            w_idx = 0
            for j in range(len(self.lv)):
                le = self.lv[j]
                if le.done or ((not le.pooled) and (le.kind == 'BSL' or le.kind == 'SSL')):
                    w_idx = j
                    break
            self.lv_del(w_idx)

    # =========================================================================
    # L4 zones
    # =========================================================================
    def z_color(self, z: Zone) -> Color:
        if z.kind == 'OB':
            return self.c_bull if z.bull else self.c_bear
        if z.kind == 'BRK':
            return self.c_brk
        if z.kind == 'RCB':
            return self.c_rcb
        if z.kind == 'RJB':
            return self.c_rjb
        if z.kind == 'QM':
            return self.c_qm
        if z.kl >= 4:
            return self.c_bull if z.bull else self.c_bear
        return self.c_neut

    def z_style(self, i: int) -> None:
        z = self.zones[i]
        if not z.has_bx:
            return
        weak_z = z.broken or z.weak or (not z.confirmed) or (z.kind == 'OB' and (not z.hp) and z.ob_type != '')
        c = self.c_inv if (weak_z and (z.broken or z.weak)) else self.z_color(z)
        rx = self.z_bx[i]
        rx.point_a = AbsolutePosition(self.bt(z.idx), z.top)
        rx.point_b = AbsolutePosition(rx.point_b.time, z.bottom)
        bt_ = 90 if (z.broken or z.weak) else (min(self.box_t + 6, 100) if z.tapped else self.box_t)
        rx.bg_color = ca(c, bt_)
        rx.line_color = ca(self.c_inv if z.sweep_req else c, 80 if z.broken else 40)
        rx.line_width = 3 if z.kl >= 4 else (2 if z.kl == 3 else 1)
        rx.line_style = line_style.DASHED if (weak_z or z.kind == 'BRK' or z.flipped) else line_style.SOLID
        if self.live:
            self.chart.draw(rx)
        cp = self.z_cap[i]
        cp.text = z_text(z)
        cp.position = AbsolutePosition(self.bt(z.idx), z.top)
        cp.text_color = color.WHITE
        cp.font_size = self.zf
        cp.callout_position = self.cap_cp
        if self.live:
            self.chart.draw(cp)

    def z_show(self, i: int) -> None:
        # create the box of an existing zone (Pine box.new on a zone that had none)
        z = self.zones[i]
        z.has_bx = True
        self.z_bx[i].point_a = AbsolutePosition(self.bt(z.idx), z.top)
        self.z_bx[i].point_b = AbsolutePosition(self.t_now, z.bottom)
        self.z_style(i)

    def z_hide(self, i: int) -> None:
        z = self.zones[i]
        if z.has_bx:
            if self.live:
                self.chart.erase(self.z_bx[i])
            if self.live:
                self.chart.erase(self.z_cap[i])
        z.has_bx = False

    def z_del(self, i: int) -> None:
        self.z_hide(i)
        self.zones.pop(i)
        self.z_bx.pop(i)
        self.z_cap.pop(i)

    def z_add(self, aV: float, kind: str, bull: bool, top: float, bottom: float, idx: int, draw_on: bool, zone_max_h: float) -> int:
        zt = max(top, bottom)
        zbm = min(top, bottom)
        max_h = aV * zone_max_h
        if zt - zbm > max_h:
            if bull:
                zt = zbm + max_h
            else:
                zbm = zt - max_h
        if not (kind == 'SR' or kind == 'RJB'):
            for i in range(len(self.zones) - 1, -1, -1):
                zx = self.zones[i]
                if (not zx.broken) and zx.kind == kind and zx.bull == bull and zx.top >= zbm and zx.bottom <= zt:
                    return i
        self.zones.append(new_zone(kind, bull, zt, zbm, idx, self.bar_index))
        self.z_bx.append(Rectangle(AbsolutePosition(self.bt(idx), zt), AbsolutePosition(self.t_now, zbm)))
        self.z_cap.append(LabelAbs('', AbsolutePosition(self.bt(idx), zt), font_size=self.zf, text_color=color.WHITE, bg_color=color.TRANSPARENT, callout_position=self.cap_cp))
        k = len(self.zones) - 1
        if draw_on:
            self.z_show(k)
        return k

    def z_reset(self, z: Zone) -> None:
        z.idm_lvl = math.nan
        z.idm_swept = False
        z.near_miss = math.nan
        z.near_swept = False
        z.fifty_hit = False

    def hidden_interest(self, top: float, bottom: float, idx: int, kl_left: int) -> bool:
        for z in self.zones:
            if z.idx < idx and z.idx >= idx - kl_left and z.top >= bottom and z.bottom <= top:
                return False
        return True

    def f_zones(self, aV: float, sw_h: float, sw_l: float, swing_len: int, zone_max_h: float, sweep_win: int, rjb_wick: float, rjb_bars: int, qm_bars: int, kl_left: int, kl_min: int, sr_trade: bool, ob_hp_only: bool, rcb_fib: bool, rjb_pend: bool, prop_win: int, prop_imp: float, touch_cd: int, max_zones: int, zone_age: int, on_sr: bool, on_kl: bool, on_ob: bool, on_brk: bool, on_rcb: bool, on_rjb: bool, on_qm: bool) -> None:
        bi = self.bar_index
        h = self.high[0]
        l = self.low[0]
        c = self.close[0]
        p_idx = bi - swing_len
        bull_bos = self.st_bull_bos
        bear_bos = self.st_bear_bos
        bull_choch = self.st_bull_choch
        bear_choch = self.st_bear_choch
        mv_strong = self.mv_strong
        mv_fvg = self.mv_fvg
        o_idx_in = self.leg_idx
        sl_ = swing_len
        if not isnan(sw_h):
            self.z_add(aV, 'SR', False, self.high[sl_], max(self.open[sl_], self.close[sl_]), p_idx, on_sr, zone_max_h)
        if not isnan(sw_l):
            self.z_add(aV, 'SR', True, min(self.open[sl_], self.close[sl_]), self.low[sl_], p_idx, on_sr, zone_max_h)
        # BOS -> key level score on the origin SR + order block
        if bull_bos or bear_bos:
            is_bull = bull_bos
            o_idx = o_idx_in
            off = bi - o_idx
            if off >= 1 and off < 490:
                for i in range(len(self.zones)):
                    z = self.zones[i]
                    if z.kind == 'SR' and z.bull == is_bull and z.kl == 0 and z.idx >= o_idx - swing_len and z.idx <= o_idx + swing_len:
                        sc = 1
                        sc += 1 if mv_fvg >= 1 else 0
                        sc += 1 if mv_strong else 0
                        sc += 1 if self.hidden_interest(z.top, z.bottom, o_idx, kl_left) else 0
                        z.kl = sc
                        z.dep_strong = mv_strong
                        if sc >= kl_min and (not z.has_bx) and on_kl:
                            self.z_show(i)
                        self.z_style(i)
                        break
                if not mv_strong:
                    if is_bull:
                        self.ft_evt_up = 'T5 no-FVG'
                    else:
                        self.ft_evt_dn = 'T5 no-FVG'
                else:
                    ob_off = off
                    ob_t = 'T1'
                    disp_off = -1
                    if ob_off >= 2:
                        k_lo = max(ob_off - swing_len, 1)
                        for k in range(ob_off - 1, k_lo - 1, -1):
                            rk = self.high[k] - self.low[k]
                            body_k = abs(self.close[k] - self.open[k]) / rk if rk > 0 else 0.0
                            col_ok = (self.close[k] > self.open[k]) if is_bull else (self.close[k] < self.open[k])
                            if col_ok and body_k >= 0.5 and rk >= aV * 0.5:
                                disp_off = k
                                break
                    if disp_off > 0:
                        for k2 in range(disp_off + 1, ob_off + 1):
                            opp = (self.close[k2] < self.open[k2]) if is_bull else (self.close[k2] > self.open[k2])
                            if opp:
                                ob_off = k2
                                ob_t = 'T1' if k2 == off else 'T1b'
                                break
                    if self.high[ob_off] <= self.high[ob_off + 1] and self.low[ob_off] >= self.low[ob_off + 1]:
                        ob_off = ob_off + 1
                        ob_t = 'T2'
                    z_top = self.high[ob_off]
                    z_bot = self.low[ob_off]
                    if ob_off >= 1:
                        nb = ob_off - 1
                        small_body = abs(self.close[ob_off] - self.open[ob_off]) < 0.3 * (self.high[ob_off] - self.low[ob_off])
                        engulfs = self.low[nb] <= self.low[ob_off] and self.high[nb] >= self.high[ob_off]
                        if small_body and engulfs:
                            z_top = self.high[ob_off] if is_bull else self.high[nb]
                            z_bot = self.low[nb] if is_bull else self.low[ob_off]
                            ob_t = 'G2'
                    ob_idx = bi - ob_off
                    fvg_lvl = self.fvg_near(is_bull, ob_idx, ob_idx + 3)
                    if isnan(fvg_lvl):
                        if is_bull:
                            self.ft_evt_up = 'T5 no-FVG'
                        else:
                            self.ft_evt_dn = 'T5 no-FVG'
                    else:
                        self_mit = (self.high[ob_off] > fvg_lvl) if is_bull else (self.low[ob_off] < fvg_lvl)
                        if self_mit:
                            if is_bull:
                                self.ft_evt_up = 'T3 invalid'
                            else:
                                self.ft_evt_dn = 'T3 invalid'
                        else:
                            sw = self.swept_low_bar if is_bull else self.swept_high_bar
                            hp_now = sw >= ob_idx - sweep_win and sw <= ob_idx + 2
                            if hp_now or not ob_hp_only:
                                kz = self.z_add(aV, 'OB', is_bull, z_top, z_bot, ob_idx, on_ob, zone_max_h)
                                zo = self.zones[kz]
                                zo.ob_type = ob_t
                                zo.dep_strong = mv_strong
                                zo.hp = hp_now
                                self.ft_new_ob_hp = hp_now
                                self.z_style(kz)
        # CHoCH -> reclaimed block + QM pending
        if bull_choch:
            ll_idx = o_idx_in
            off2 = bi - ll_idx
            if off2 >= 1 and off2 < 490 and ll_idx > 0:
                leg_mid = (self.low[off2] + h) * 0.5
                if self.high[off2] <= leg_mid or not rcb_fib:
                    kr = self.z_add(aV, 'RCB', True, self.high[off2], self.low[off2], ll_idx, on_rcb, zone_max_h)
                    self.zones[kr].dep_strong = self.choch_real
            self.qm_bull_pend = True
            self.qm_bull_ll = self.cur_low
            self.qm_bull_at = bi
        if bear_choch:
            hh_idx = o_idx_in
            off3 = bi - hh_idx
            if off3 >= 1 and off3 < 490 and hh_idx > 0:
                leg_mid2 = (self.high[off3] + l) * 0.5
                if self.low[off3] >= leg_mid2 or not rcb_fib:
                    kr2 = self.z_add(aV, 'RCB', False, self.high[off3], self.low[off3], hh_idx, on_rcb, zone_max_h)
                    self.zones[kr2].dep_strong = self.choch_real
            self.qm_bear_pend = True
            self.qm_bear_hh = self.cur_high
            self.qm_bear_at = bi
        if self.qm_bull_pend:
            if bi - self.qm_bull_at > qm_bars or bear_choch:
                self.qm_bull_pend = False
            elif (not isnan(self.qm_bull_ll)) and l < self.qm_bull_ll:
                kq = self.z_add(aV, 'QM', True, self.qm_bull_ll, l, bi, on_qm, zone_max_h)
                self.zones[kq].dep_strong = self.choch_real
                self.qm_bull_pend = False
        if self.qm_bear_pend:
            if bi - self.qm_bear_at > qm_bars or bull_choch:
                self.qm_bear_pend = False
            elif (not isnan(self.qm_bear_hh)) and h > self.qm_bear_hh:
                kq2 = self.z_add(aV, 'QM', False, h, self.qm_bear_hh, bi, on_qm, zone_max_h)
                self.zones[kq2].dep_strong = self.choch_real
                self.qm_bear_pend = False
        # rejection block
        if bi > 2:
            rr1 = self.high[1] - self.low[1]
            uw1 = (self.high[1] - max(self.open[1], self.close[1])) / rr1 if rr1 > 0 else 0.0
            dw1 = (min(self.open[1], self.close[1]) - self.low[1]) / rr1 if rr1 > 0 else 0.0
            if uw1 >= rjb_wick:
                zbx = max(self.open[1], self.close[1])
                if h < zbx:
                    kj = self.z_add(aV, 'RJB', False, self.high[1], zbx, bi - 1, on_rjb, zone_max_h)
                    self.zones[kj].confirmed = False
                    self.zones[kj].pend_fvg = 2
                    self.z_style(kj)
            if dw1 >= rjb_wick:
                ztx = min(self.open[1], self.close[1])
                if l > ztx:
                    kj2 = self.z_add(aV, 'RJB', True, ztx, self.low[1], bi - 1, on_rjb, zone_max_h)
                    self.zones[kj2].confirmed = False
                    self.zones[kj2].pend_fvg = 2
                    self.z_style(kj2)
        # per-bar maintenance + zone-at-price feature (one slot per side)
        best_pri = -1
        best_pri_s = -1
        sw_l_na = isnan(sw_l)
        sw_h_na = isnan(sw_h)
        half_a = 0.5 * aV
        for i in range(len(self.zones) - 1, -1, -1):
            z = self.zones[i]
            changed = False
            if z.broken:
                if bi - z.broken_at > 20:
                    self.z_del(i)
                continue
            if z.idx >= bi:
                continue
            if z.kind == 'RJB' and not z.confirmed:
                if z.pend_fvg > 0:
                    z.pend_fvg -= 1
                    if z.pend_fvg == 0 and isnan(self.fvg_near(z.bull, z.idx - 1, z.idx + 1)):
                        self.z_del(i)
                        continue
                if (z.bull and bull_bos) or ((not z.bull) and bear_bos):
                    z.confirmed = True
                    z.dep_strong = mv_strong
                    changed = True
                elif bi - z.idx > rjb_bars:
                    z.broken = True
                    z.broken_at = bi
                    changed = True
            if not changed:
                busy = True
                if z.bull:
                    busy =(not sw_l_na) or l <= z.top + half_a or ((not z.idm_swept) and l < z.idm_lvl) or ((not z.near_swept) and l < z.near_miss) or (self.ft_new_bull_fvg and z.fifty_hit)
                else:
                    busy = (not sw_h_na) or h >= z.bottom - half_a or ((not z.idm_swept) and h > z.idm_lvl) or ((not z.near_swept) and h > z.near_miss) or (self.ft_new_bear_fvg and z.fifty_hit)
                if not busy:
                    if (not z.tapped) and bi - z.idx > zone_age:
                        self.z_del(i)
                    continue
            mid = (z.top + z.bottom) * 0.5
            touched_now = False
            if z.bull:
                if (not isnan(sw_l)) and sw_l > z.top and (isnan(z.idm_lvl) or sw_l < z.idm_lvl):
                    z.idm_lvl = sw_l
                if (not isnan(z.idm_lvl)) and (not z.idm_swept) and l < z.idm_lvl and l > z.top:
                    z.idm_swept = True
                    changed = True
                if l > z.top and l <= z.top + 0.5 * aV and isnan(z.near_miss):
                    z.near_miss = l
                if (not isnan(z.near_miss)) and (not z.near_swept) and l < z.near_miss and c > z.near_miss:
                    z.near_swept = True
                    changed = True
                if c < z.bottom:
                    if z.kind == 'SR' and not z.flipped:
                        z.bull = False
                        z.flipped = True
                        z.touches = 0
                        z.sweep_req = False
                        self.z_reset(z)
                        changed = True
                        if z.kl >= 4:
                            self.ft_evt_dn = 'FLIP S→R'
                    elif z.kind == 'OB':
                        z.kind = 'BRK'
                        z.bull = False
                        z.touches = 0
                        z.tapped = False
                        z.sweep_req = False
                        self.z_reset(z)
                        changed = True
                        self.ft_evt_dn = 'BRK▼'
                        if (not on_brk) and z.has_bx:
                            self.z_hide(i)
                    else:
                        z.broken = True
                        z.broken_at = bi
                        changed = True
                elif l <= z.top:
                    touched_now = True
                    if not z.tapped:
                        z.tapped = True
                        changed = True
                    if l <= mid and not z.fifty_hit:
                        z.fifty_hit = True
                    if bi - z.last_touch > touch_cd and self.low[1] > z.top:
                        z.touches += 1
                        z.last_touch = bi
                        if z.touches >= 2 and not z.sweep_req:
                            z.sweep_req = True
                            changed = True
                            if z.kind == 'OB' or z.kind == 'BRK':
                                self.ft_evt_up = '⚠SWEEP REQ'
                elif z.fifty_hit and z.touches >= 1 and (not z.prop) and self.ft_new_bull_fvg and bi - z.last_touch <= prop_win and l - z.top >= prop_imp * aV and l - z.top <= prop_imp * aV * 3:
                    z.prop = True
                    z.touches = 0
                    z.tapped = False
                    z.sweep_req = False
                    self.z_reset(z)
                    changed = True
                    self.ft_new_prop = True
                    self.ft_evt_up = 'PROP▲'
            else:
                if (not isnan(sw_h)) and sw_h < z.bottom and (isnan(z.idm_lvl) or sw_h > z.idm_lvl):
                    z.idm_lvl = sw_h
                if (not isnan(z.idm_lvl)) and (not z.idm_swept) and h > z.idm_lvl and h < z.bottom:
                    z.idm_swept = True
                    changed = True
                if h < z.bottom and h >= z.bottom - 0.5 * aV and isnan(z.near_miss):
                    z.near_miss = h
                if (not isnan(z.near_miss)) and (not z.near_swept) and h > z.near_miss and c < z.near_miss:
                    z.near_swept = True
                    changed = True
                if c > z.top:
                    if z.kind == 'SR' and not z.flipped:
                        z.bull = True
                        z.flipped = True
                        z.touches = 0
                        z.sweep_req = False
                        self.z_reset(z)
                        changed = True
                        if z.kl >= 4:
                            self.ft_evt_up = 'FLIP R→S'
                    elif z.kind == 'OB':
                        z.kind = 'BRK'
                        z.bull = True
                        z.touches = 0
                        z.tapped = False
                        z.sweep_req = False
                        self.z_reset(z)
                        changed = True
                        self.ft_evt_up = 'BRK▲'
                        if (not on_brk) and z.has_bx:
                            self.z_hide(i)
                    else:
                        z.broken = True
                        z.broken_at = bi
                        changed = True
                elif h >= z.bottom:
                    touched_now = True
                    if not z.tapped:
                        z.tapped = True
                        changed = True
                    if h >= mid and not z.fifty_hit:
                        z.fifty_hit = True
                    if bi - z.last_touch > touch_cd and self.high[1] < z.bottom:
                        z.touches += 1
                        z.last_touch = bi
                        if z.touches >= 2 and not z.sweep_req:
                            z.sweep_req = True
                            changed = True
                            if z.kind == 'OB' or z.kind == 'BRK':
                                self.ft_evt_dn = '⚠SWEEP REQ'
                elif z.fifty_hit and z.touches >= 1 and (not z.prop) and self.ft_new_bear_fvg and bi - z.last_touch <= prop_win and z.bottom - h >= prop_imp * aV and z.bottom - h <= prop_imp * aV * 3:
                    z.prop = True
                    z.touches = 0
                    z.tapped = False
                    z.sweep_req = False
                    self.z_reset(z)
                    changed = True
                    self.ft_new_prop = True
                    self.ft_evt_dn = 'PROP▼'
            sr_ok = z.kind != 'SR' or z.kl >= kl_min or sr_trade
            if touched_now and (not z.broken) and sr_ok and (not z.weak) and (z.confirmed or (rjb_pend and z.kind == 'RJB')):
                pri_k = 6 if z.kind == 'OB' else (5 if z.kind == 'BRK' else (4 if (z.kind == 'RCB' or z.kind == 'QM') else (3 if z.kind == 'RJB' else (2 if z.kl >= 3 else 1))))
                pri = (pri_k if z.confirmed else 0) + (3 if z.prop else 0)
                if (z.bull and pri > best_pri) or ((not z.bull) and pri > best_pri_s):
                    zz = self.ft_zb if z.bull else self.ft_zs
                    if z.bull:
                        best_pri = pri
                    else:
                        best_pri_s = pri
                    zz.kind = z.kind
                    zz.touches = z.touches
                    zz.sweep_req = z.sweep_req
                    zz.fifty = z.fifty_hit
                    zz.idm = z.idm_swept
                    zz.hp = z.hp
                    zz.kl = z.kl
                    zz.flipped = z.flipped
                    zz.near_swept = z.near_swept
                    zz.dep_strong = z.dep_strong
                    zz.prop = z.prop
                    zz.top = z.top
                    zz.bottom = z.bottom
                    zz.pend = not z.confirmed
                    if z.bull:
                        self.ft_at_support = z.kind == 'SR'
                        self.ft_at_demand = z.kind != 'SR'
                    else:
                        self.ft_at_resist = z.kind == 'SR'
                        self.ft_at_supply = z.kind != 'SR'
            if z.broken and z.has_bx:
                self.z_bx[i].point_b = AbsolutePosition(self.t_now, z.bottom)
            if changed:
                self.z_style(i)
            if (not z.tapped) and bi - z.idx > zone_age:
                self.z_del(i)
                continue
        sr_cnt = 0
        for zc in self.zones:
            if zc.kind == 'SR':
                sr_cnt += 1
        if sr_cnt > max_zones:
            for i in range(len(self.zones)):
                if self.zones[i].kind == 'SR':
                    self.z_del(i)
                    break
        while len(self.zones) > max_zones * 2:
            self.z_del(0)

    # =========================================================================
    # L5 HTF
    # =========================================================================
    def f_htf(self, is_new: bool, o1: float, h1: float, l1: float, c1: float, o2: float, h2: float, l2: float, c2: float, ph: float, pl: float, h3: float, l3: float, sweep_val: int, manip_wick: float, rej_w: float) -> None:
        h = self.high[0]
        l = self.low[0]
        c = self.close[0]
        if is_new and not isnan(c1):
            self.h_bar_count += 1
            if (not isnan(h3)) and l1 > h3:
                self.h_fvg_bt = l1
                self.h_fvg_bb = h3
                self.h_fvg_b_bar = self.h_bar_count
            if (not isnan(l3)) and h1 < l3:
                self.h_fvg_st = l3
                self.h_fvg_sb = h1
                self.h_fvg_s_bar = self.h_bar_count
            if (not isnan(self.h_fvg_bb)) and self.h_bar_count - self.h_fvg_b_bar > 50:
                self.h_fvg_bt = math.nan
                self.h_fvg_bb = math.nan
            if (not isnan(self.h_fvg_st)) and self.h_bar_count - self.h_fvg_s_bar > 50:
                self.h_fvg_st = math.nan
                self.h_fvg_sb = math.nan
            if (not isnan(self.h_cur_high)) and (not self.h_hi_broken) and h1 > self.h_cur_high and c1 <= self.h_cur_high:
                self.sweep_up_at = self.h_bar_count
            if (not isnan(self.h_cur_low)) and (not self.h_lo_broken) and l1 < self.h_cur_low and c1 >= self.h_cur_low:
                self.sweep_dn_at = self.h_bar_count
            disp_h = (h1 - l1) > 0 and abs(c1 - o1) / (h1 - l1) >= 0.5
            b_brk = (not isnan(self.h_cur_high)) and (not self.h_hi_broken) and c1 > self.h_cur_high
            s_brk = (not isnan(self.h_cur_low)) and (not self.h_lo_broken) and c1 < self.h_cur_low
            if b_brk and disp_h:
                self.h_hi_broken = True
            if s_brk and disp_h:
                self.h_lo_broken = True
            prot_h = nz(self.h_major_high, self.h_cur_high)
            prot_l = nz(self.h_major_low, self.h_cur_low)
            lh_h = (not isnan(self.h_prev_high)) and (not isnan(self.h_cur_high)) and self.h_cur_high < self.h_prev_high
            hl_h = (not isnan(self.h_prev_low)) and (not isnan(self.h_cur_low)) and self.h_cur_low > self.h_prev_low
            ch_up_h = self.h_trend == 'BEAR' and (((not isnan(prot_h)) and c1 > prot_h) or (b_brk and hl_h))
            ch_dn_h = self.h_trend == 'BULL' and (((not isnan(prot_l)) and c1 < prot_l) or (s_brk and lh_h))
            if disp_h:
                if ch_up_h:
                    self.h_trend = 'BULL'
                    self.h_major_low = self.h_cur_low
                elif ch_dn_h:
                    self.h_trend = 'BEAR'
                    self.h_major_high = self.h_cur_high
                elif b_brk and self.h_trend != 'BEAR':
                    self.h_trend = 'BULL'
                    self.h_major_low = self.h_cur_low
                elif s_brk and self.h_trend != 'BULL':
                    self.h_trend = 'BEAR'
                    self.h_major_high = self.h_cur_high
            if not isnan(ph):
                self.h_prev_high = self.h_cur_high
                self.h_cur_high = ph
                self.h_hi_broken = False
                if self.h_trend == 'BEAR' and isnan(self.h_major_high):
                    self.h_major_high = ph
            if not isnan(pl):
                self.h_prev_low = self.h_cur_low
                self.h_cur_low = pl
                self.h_lo_broken = False
                if self.h_trend == 'BULL' and isnan(self.h_major_low):
                    self.h_major_low = pl
        if (not isnan(self.h_fvg_bb)) and c < self.h_fvg_bb:
            self.h_fvg_bt = math.nan
            self.h_fvg_bb = math.nan
        if (not isnan(self.h_fvg_st)) and c > self.h_fvg_st:
            self.h_fvg_st = math.nan
            self.h_fvg_sb = math.nan
        self.ft_in_htf_fvg_b = (not isnan(self.h_fvg_bb)) and l <= self.h_fvg_bt and h >= self.h_fvg_bb
        self.ft_in_htf_fvg_s = (not isnan(self.h_fvg_st)) and h >= self.h_fvg_sb and l <= self.h_fvg_st
        self.ft_htf_bias = self.h_trend
        self.ft_htf_sweep_up = self.h_bar_count - self.sweep_up_at < sweep_val
        self.ft_htf_sweep_dn = self.h_bar_count - self.sweep_dn_at < sweep_val
        if (not isnan(c1)) and not isnan(c2):
            rr1 = h1 - l1
            up_w = (h1 - max(o1, c1)) / rr1 if rr1 > 0 else 0.0
            dn_w = (min(o1, c1) - l1) / rr1 if rr1 > 0 else 0.0
            self.ft_htf_manip_bull = l1 < l2 and c1 > h2 and c1 > o1 and dn_w >= manip_wick
            self.ft_htf_manip_bear = h1 > h2 and c1 < l2 and c1 < o1 and up_w >= manip_wick
            self.ft_htf_rej_bear = up_w >= rej_w and c1 < o1
            self.ft_htf_rej_bull = dn_w >= rej_w and c1 > o1

    def f_gate(self, gate_mode: str, bias: str, trend: str, sig_bull: bool) -> int:
        htf_ok = bias == 'NEUTRAL' or (sig_bull and bias == 'BULL') or ((not sig_bull) and bias == 'BEAR')
        tr_ok = trend == 'RANGE' or (sig_bull and trend == 'BULLISH') or ((not sig_bull) and trend == 'BEARISH')
        if gate_mode == 'OFF' or (htf_ok and tr_ok):
            return 2
        if gate_mode == 'WARN':
            return 1
        return 0

    # =========================================================================
    # L6 pick helpers
    # =========================================================================
    def grade_txt(self, sc: int, g_ap: int, g_a: int) -> str:
        if sc >= g_ap:
            return 'A+'
        if sc >= g_a:
            return 'A'
        return 'B'

    # =========================================================================
    # L7 trade engine
    # =========================================================================
    def nearest_liq(self, is_long: bool, pxv: float) -> float:
        best = math.nan
        for L in self.lv:
            if L.done or L.is_high != is_long:
                continue
            if (is_long and L.price > pxv and (isnan(best) or L.price < best)) or ((not is_long) and L.price < pxv and (isnan(best) or L.price > best)):
                best = L.price
        return best

    # =========================================================================
    # drawing helpers
    # =========================================================================
    def add_label(self, is_up: bool, y: float, txt: str, col: Color, filled: bool, fill_t: int, mx: int, t: float) -> int:
        bgc = ca(col, fill_t) if filled else color.TRANSPARENT
        tc = self.c_txt if filled else col
        lb = LabelAbs(txt, AbsolutePosition(t, y), font_size=self.lf, text_color=tc, bg_color=bgc, callout_position=callout_position.TOP_RIGHT if is_up else callout_position.BOTTOM_RIGHT)
        if self.live:
            self.chart.draw(lb)
        self.lab_seq += 1
        self.labs.append(lb)
        self.lab_ids.append(self.lab_seq)
        while len(self.labs) > mx:
            if self.live:
                self.chart.erase(self.labs[0])
            self.labs.pop(0)
            self.lab_ids.pop(0)
        return self.lab_seq

    def ev_line(self, xa: int, y: float, col: Color, sty: line_style, mx: int, t: float) -> None:
        st2 = line_style.DOTTED if xa < self.bar_index - 495 else sty
        ln = LineSegment(AbsolutePosition(self.bt(xa), y), AbsolutePosition(t, y), color=col, line_style=st2, line_width=1)
        if self.live:
            self.chart.draw(ln)
        self.lns.append(ln)
        while len(self.lns) > mx:
            if self.live:
                self.chart.erase(self.lns[0])
            self.lns.pop(0)

    def htf_lines(self, o1: float, h1: float, l1: float, c1: float, c_look: int, t: float) -> None:
        cc = ca(self.c_htf, self.line_t)
        t2 = t + self.tf_sec
        lvls: list[float] = [h1, l1, o1, c1]
        for q in range(4):
            sty = line_style.SOLID if q < 2 else (line_style.DOTTED if q == 2 else line_style.DASHED)
            ln = LineSegment(AbsolutePosition(t, lvls[q]), AbsolutePosition(t2, lvls[q]), color=cc, line_style=sty, line_width=1)
            if self.live:
                self.chart.draw(ln)
            self.h_lns.append(ln)
            self.h_ext.append(True)
        nl = len(self.h_lns)
        if nl > 4:
            for i in range(nl - 4):
                if self.h_ext[i]:
                    self.h_ext[i] = False
                    old = self.h_lns[i]
                    old.point_b = AbsolutePosition(t, old.point_a.price)
                    if self.live:
                        self.chart.draw(old)
        while len(self.h_lns) > c_look * 4:
            if self.live:
                self.chart.erase(self.h_lns[0])
            self.h_lns.pop(0)
            self.h_ext.pop(0)

    def draw_tl(self, sup_valid: bool, res_valid: bool, slope_s: float, slope_r: float, tl_s: float, tl_r: float, t: float) -> None:
        if sup_valid:
            x1 = self.tl_sx1
            self.tl_sup_ln.point_a = AbsolutePosition(self.bt(x1), self.tl_sy1)
            self.tl_sup_ln.point_b = AbsolutePosition(t, tl_s)
            self.tl_sup_ln.color = ca(self.c_bull, 30)
            self.tl_sup_ln.line_style = line_style.SOLID
            self.tl_sup_ln.line_width = 2
            if self.live:
                self.chart.draw(self.tl_sup_ln)
            self.tl_sup_on = True
            self.tl_sup_ext = True
            self.tl_sup_t = t
            self.tl_sup_p = tl_s
            self.tl_sup_k = slope_s
        elif self.tl_sup_on and self.tl_s_broken and self.tl_sup_ext:
            self.tl_sup_ext = False
            self.tl_sup_ln.color = ca(self.c_inv, 60)
            if self.live:
                self.chart.draw(self.tl_sup_ln)
        if res_valid:
            x2 = self.tl_rx1
            self.tl_res_ln.point_a = AbsolutePosition(self.bt(x2), self.tl_ry1)
            self.tl_res_ln.point_b = AbsolutePosition(t, tl_r)
            self.tl_res_ln.color = ca(self.c_bear, 30)
            self.tl_res_ln.line_style = line_style.SOLID
            self.tl_res_ln.line_width = 2
            if self.live:
                self.chart.draw(self.tl_res_ln)
            self.tl_res_on = True
            self.tl_res_ext = True
            self.tl_res_t = t
            self.tl_res_p = tl_r
            self.tl_res_k = slope_r
        elif self.tl_res_on and self.tl_r_broken and self.tl_res_ext:
            self.tl_res_ext = False
            self.tl_res_ln.color = ca(self.c_inv, 60)
            if self.live:
                self.chart.draw(self.tl_res_ln)

    # =========================================================================
    # last bar: extend live objects to the right (Pine extend.right) + panel
    # =========================================================================
    def render_all(self) -> None:
        # history was computed without drawing (Indie execution-time budget); draw the surviving objects once
        for i in range(len(self.zones)):
            if self.zones[i].has_bx:
                self.chart.draw(self.z_bx[i])
                self.chart.draw(self.z_cap[i])
        for j in range(len(self.lv)):
            if self.lv[j].has_ln:
                self.chart.draw(self.lv_ln[j])
            if self.lv[j].has_lb:
                self.chart.draw(self.lv_lb[j])
        for k in range(len(self.fvgs)):
            if self.fvgs[k].has_bx:
                self.chart.draw(self.fvg_bx[k])
        for lb in self.labs:
            self.chart.draw(lb)
        for ln in self.lns:
            self.chart.draw(ln)
        for tl in self.trade_lns:
            self.chart.draw(tl)
        for hl in self.h_lns:
            self.chart.draw(hl)
        if self.tl_sup_on:
            self.chart.draw(self.tl_sup_ln)
        if self.tl_res_on:
            self.chart.draw(self.tl_res_ln)

    def live_draw(self, ext_bars: int, d_panel: bool, d_legend: bool, dash_pos: str, dash_w: float, dash_font: int, grade_ap: int, grade_a: int, pd_deep: float, entry_confirm: str, kl_min: int, ret_bars: int, m74_bars: int) -> None:
        if not self.live:
            self.live = True
            self.render_all()
        if self.bar_index != self.last_refresh:
            self.last_refresh = self.bar_index
            te = self.time[0] + float(ext_bars) * self.tf_sec
            if self.hi_on:
                if self.live:
                    self.chart.draw(self.hi_line)
            if self.lo_on:
                if self.live:
                    self.chart.draw(self.lo_line)
            for i in range(len(self.zones)):
                z = self.zones[i]
                if z.has_bx and not z.broken:
                    self.z_bx[i].point_b = AbsolutePosition(te, z.bottom)
                    if self.live:
                        self.chart.draw(self.z_bx[i])
            for j in range(len(self.lv)):
                L = self.lv[j]
                if L.has_ln and not L.done:
                    self.lv_ln[j].point_b = AbsolutePosition(te, L.price)
                    if self.live:
                        self.chart.draw(self.lv_ln[j])
            for k in range(len(self.fvgs)):
                g = self.fvgs[k]
                if g.has_bx and not g.mitigated:
                    self.fvg_bx[k].point_b = AbsolutePosition(te, g.bottom)
                    if self.live:
                        self.chart.draw(self.fvg_bx[k])
            for q in range(len(self.h_lns)):
                if self.h_ext[q]:
                    hl = self.h_lns[q]
                    hl.point_b = AbsolutePosition(te, hl.point_a.price)
                    if self.live:
                        self.chart.draw(hl)
            if self.tl_sup_on and self.tl_sup_ext and self.tf_sec > 0:
                nb = (te - self.tl_sup_t) / self.tf_sec
                self.tl_sup_ln.point_b = AbsolutePosition(te, self.tl_sup_p + self.tl_sup_k * nb)
                if self.live:
                    self.chart.draw(self.tl_sup_ln)
            if self.tl_res_on and self.tl_res_ext and self.tf_sec > 0:
                nb2 = (te - self.tl_res_t) / self.tf_sec
                self.tl_res_ln.point_b = AbsolutePosition(te, self.tl_res_p + self.tl_res_k * nb2)
                if self.live:
                    self.chart.draw(self.tl_res_ln)
        if d_panel:
            self.draw_panel(dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min)
        if d_legend:
            self.draw_legend(dash_font)

    def prow(self, k: str, v: str, tc: Color) -> None:
        self.dash.append(TableRow([TableCell(k, text_color=self.c_txt, bg_color=ca(self.c_neut, 60)), TableCell(v, text_color=tc)]))

    def prow_bg(self, k: str, v: str, tc: Color, bg: Color) -> None:
        self.dash.append(TableRow([TableCell(k, text_color=self.c_txt, bg_color=ca(self.c_neut, 60)), TableCell(v, text_color=tc, bg_color=bg)]))

    def draw_panel(self, dash_pos: str, dash_w: float, dash_font: int, grade_ap: int, grade_a: int, pd_deep: float, entry_confirm: str, kl_min: int) -> None:
        tb = self.dash
        tb.clear()
        tb.font_size = dash_font
        is_right = dash_pos == 'Bottom right' or dash_pos == 'Top right'
        is_bottom = dash_pos == 'Bottom right' or dash_pos == 'Bottom left'
        xr = max(0.0, 0.995 - dash_w) if is_right else 0.06
        tb.position = RelativePosition(va.BOTTOM if is_bottom else va.TOP, ha.LEFT, 0.97 if is_bottom else 0.03, xr)
        fg = color.WHITE
        c = self.eng_close
        prec = self.prec
        trend = self.st_trend
        bias = self.ft_htf_bias
        tcol = self.c_bull if trend == 'BULLISH' else (self.c_bear if trend == 'BEARISH' else self.c_neut)
        hcol = self.c_bull if bias == 'BULL' else (self.c_bear if bias == 'BEAR' else self.c_neut)
        mism = (trend == 'BULLISH' and bias == 'BEAR') or (trend == 'BEARISH' and bias == 'BULL')
        n_bsl = self.nearest_liq(True, c)
        n_ssl = self.nearest_liq(False, c)
        sgl = self.sig_l
        sgs = self.sig_s
        best = sgl if (self.has_l and ((not self.has_s) or sgl.score >= sgs.score)) else sgs
        is_l = (best.side == 1) if best.name != '' else (bias != 'BEAR')
        f_a = (is_l and bias == 'BULL') or ((not is_l) and bias == 'BEAR')
        f_b = (is_l and trend == 'BULLISH') or ((not is_l) and trend == 'BEARISH')
        zz = self.ft_zb if is_l else self.ft_zs
        f_c = zz.dep_strong and zz.arr == 1
        f_d = (is_l and self.ft_bsl_above >= 1) or ((not is_l) and self.ft_ssl_below >= 1)
        chk = ('✅' if f_a else '❌') + ('✅' if f_b else '❌') + ('✅' if f_c else '❌') + ('✅' if f_d else '❌')
        tfm = int(self.tf_sec / 60.0)
        tf_txt = str(tfm) if tfm < 1440 else ('D' if tfm < 10080 else 'W')
        self.prow('Chart / HTF', tf_txt + ' → ' + self.htf_lbl + '  · ' + str(self.n_done) + ' bars', fg)
        self.prow_bg('LTF structure', trend, self.c_txt, ca(tcol, 40))
        self.prow_bg('HTF bias', bias + (' ⚠' if mism else ''), self.c_txt, ca(hcol, 40))
        self.prow('Regime', trend + (' · range' if self.ft_in_range else ''), fg)
        self.prow('Last event', self.last_evt + ((' · ' + str(self.eng_bi - self.last_evt_bar) + 'b ago') if self.last_evt_bar >= 0 else ''), fg)
        self.prow('Move phase', self.st_move_phase, fg)
        zb = self.ft_zb
        zs = self.ft_zs
        zb_t = ''
        if zb.kind != '':
            zb_t = 'Bull ' + (('KL★' if zb.kl >= 4 else 'KL') if zb.kind == 'SR' else zb.kind) + (' ?' if zb.pend else '') + (' (fresh)' if zb.touches <= 1 else ' (×' + str(zb.touches) + ')') + (' ⚠SWEEP REQ' if zb.sweep_req else '')
        zs_t = ''
        if zs.kind != '':
            zs_t = 'Bear ' + (('KL★' if zs.kl >= 4 else 'KL') if zs.kind == 'SR' else zs.kind) + (' ?' if zs.pend else '') + (' (fresh)' if zs.touches <= 1 else ' (×' + str(zs.touches) + ')') + (' ⚠SWEEP REQ' if zs.sweep_req else '')
        self.prow('Active zone', '—' if (zb_t == '' and zs_t == '') else zb_t + (' · ' if (zb_t != '' and zs_t != '') else '') + zs_t, fg)
        arr_v = zb.arr if zb.kind != '' else zs.arr
        arr_t = '—'
        if zb.kind != '' or zs.kind != '':
            arr_t = 'WEAK ✅' if arr_v == 1 else ('STRONG ❌' if arr_v == -1 else '—')
        self.prow('Arrival', arr_t, fg)
        self.prow('Nearest BSL', px(n_bsl, prec), self.c_bear)
        self.prow('Nearest SSL', px(n_ssl, prec), self.c_bull)
        self.prow('4-factor', ('watch ' if best.name == '' else '') + chk + '  (HTF·trend·dep/arr·liq)', fg)
        sig_t = '—' if best.name == '' else best.name + ' ' + str(best.score) + ' (' + self.grade_txt(best.score, grade_ap, grade_a) + ')'
        sig_bg = self.c_neut if best.name == '' else (self.c_bull if best.side == 1 else self.c_bear)
        self.prow_bg('Signal', sig_t, self.c_txt, ca(sig_bg, 40))
        pp = self.ft_pd_pct
        pd_t = '—'
        if self.ft_pd_beyond:
            pd_t = 'beyond leg (expansion)'
        elif self.ft_in_premium or self.ft_in_discount:
            pd_t = f0(pp * 100.0) + '% of leg · ' + ('premium (sell side)' if pp > 0.5 else ('discount (buy side)' if pp < 0.5 else 'equilibrium'))
        hpp = self.ft_htf_pd_pct
        if not isnan(hpp):
            pd_t += ' · ' + self.htf_lbl + ' ' + f0(hpp * 100.0) + '%' + (' deep' if (hpp > pd_deep or hpp < 1.0 - pd_deep) else '')
        self.prow('PD array', pd_t, self.c_bear if pp > 0.5 else (self.c_bull if pp < 0.5 else fg))
        ses_t = ('— (outside killzones)' if self.ft_sess_name == '' else self.ft_sess_name + ('' if self.ft_sb_sess_ok else ' ⛔'))
        if not isnan(self.ny_open):
            ses_t += ' · >00:00 open' if c > self.ny_open else ' · <00:00 open'
        self.prow('Session', ses_t, fg)
        gate_n = self.ft_gate_up if is_l else self.ft_gate_dn
        g_txt = 'aligned' if gate_n == 2 else ('⚠ LTF counter (pullback)' if ((is_l and bias != 'BEAR') or ((not is_l) and bias != 'BULL')) else '⚠ counter')
        self.prow('TP1 / gate', '—' if best.name == '' else best.tgt + ' · HTF ' + g_txt, fg if (best.tgt == 'REAL' and gate_n == 2) else self.c_rjb)
        w_txt = '—'
        if self.ret_l_on:
            w_txt = '⏳ ' + self.ret_name_l + ' LONG limit @ ' + px(self.ret_px_l, prec)
        elif self.ret_s_on:
            w_txt = '⏳ ' + self.ret_name_s + ' SHORT limit @ ' + px(self.ret_px_s, prec)
        elif bias != 'NEUTRAL':
            w_l = bias == 'BULL'
            wk = -1
            for i in range(len(self.zones)):
                z = self.zones[i]
                if z.broken or z.weak or (not z.confirmed) or z.bull != w_l or (z.kind == 'SR' and z.kl < kl_min):
                    continue
                if wk < 0:
                    if (w_l and z.top <= c) or ((not w_l) and z.bottom >= c):
                        wk = i
                else:
                    wz0 = self.zones[wk]
                    if (w_l and z.top <= c and z.top > wz0.top) or ((not w_l) and z.bottom >= c and z.bottom < wz0.bottom):
                        wk = i
            if wk >= 0:
                wz = self.zones[wk]
                lq = self.nearest_liq(not w_l, c)
                lq_in = (not isnan(lq)) and ((lq > wz.top) if w_l else (lq < wz.bottom))
                w_txt = ('LONG · ' if w_l else 'SHORT · ') + wz.kind + ('▲ ' if w_l else '▼ ') + px(wz.bottom, prec) + '–' + px(wz.top, prec) + (((' · sweep SSL ' if w_l else ' · sweep BSL ') + px(lq, prec) + ' first') if lq_in else '') + ' · ' + entry_confirm
        self.prow('Watch', w_txt, fg)
        self.chart.draw(tb)

    def draw_legend(self, dash_font: int) -> None:
        tb = self.lgd
        tb.clear()
        tb.font_size = dash_font
        fg = color.WHITE
        tb.append(TableRow([TableCell('▲▲ A+ · ▲ A · · B', text_color=self.c_txt, bg_color=ca(self.c_bull, 40)), TableCell('setup signal · grey = ⚠vs HTF/trend', text_color=fg)]))
        tb.append(TableRow([TableCell('BOS / CHoCH / CISD', text_color=self.c_txt, bg_color=ca(self.c_bull, 40)), TableCell('solid = displaced · dotted grey = weak / internal · dashed grey = sweep · dotted = CISD', text_color=fg)]))
        tb.append(TableRow([TableCell('SWEEP✕ · RUN', text_color=self.c_txt, bg_color=ca(self.c_bear, 40)), TableCell('liquidity sweep (trade) · run (avoid)', text_color=fg)]))
        tb.append(TableRow([TableCell('OB★ BRK RCB RJB QM', text_color=self.c_txt, bg_color=ca(self.c_brk, 40)), TableCell('zones (T1/T1b/T2/G2 = OB candle) · dashed grey = weak · ⚠SWEEP REQ · IDM✓ · ★★', text_color=fg)]))
        tb.append(TableRow([TableCell('KL / KL★', text_color=self.c_txt, bg_color=ca(self.c_neut, 40)), TableCell('key level (criteria ≥ min) / 4+', text_color=fg)]))
        tb.append(TableRow([TableCell('▮ FVG', text_color=self.c_bull, bg_color=ca(self.c_bull, 85)), TableCell('fair value gap · deleted when mitigated', text_color=fg)]))
        tb.append(TableRow([TableCell('┈┈ ╌╌', text_color=self.c_pool, bg_color=ca(self.c_pool, 85)), TableCell('dotted = BSL/SSL · thick dashed orange = POOL/EQH/EQL · grey = PDH/PDL', text_color=fg)]))
        tb.append(TableRow([TableCell('━ entry ╌ SL ╌ TP', text_color=self.c_htf, bg_color=ca(self.c_htf, 85)), TableCell('blue entry · red SL · green TP1/TP2/TP3 · HTF candle H/L/O/C blue', text_color=fg)]))
        self.chart.draw(tb)
