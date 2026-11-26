# indie:lang_version = 5
# BUILD SMC-v8.5.4-EXNESS-P1h (default = diag level 0) · 2026-11-08 · source = SMC_Pattern/SMC_v8.5.4.txt (Pine v6, 4250 lines)
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
@indicator('SMC / ICT Suite v8.5.4 EXNESS', overlay_main_pane=True)
# --- 1 · General
@param.str('start_date', default='2026-10-15', title='Calculate from date YYYY-MM-DD (empty = all history; move later if Execution timed out)')
@param.str('dbg_stop', default='0 Nothing (speed test)', options=['All layers', '0 Nothing (speed test)', '1 Structure only', '2 + FVG / liquidity / zones', '3 + HTF / PD', '4 + setups (no trade engine)'], title='DIAGNOSTIC: run engine up to (use if Execution timed out)')
@param.int('atr_len', default=14, min=1, title='ATR length')
@param.int('swing_len', default=5, min=1, title='Swing length (each side)')
@param.int('max_labels', default=200, min=10, max=500, title='Max labels')
@param.int('max_lines', default=100, min=10, max=500, title='Max lines')
@param.int('min_gap', default=6, min=0, max=20, title='Min bars between labels (same side)')
@param.str('lbl_mode', default='Signals only', options=['Signals only', 'Key events', 'All events'], title='Label density')
@param.str('set_mode', default='Custom (toggles)', options=['Custom (toggles)', 'Core only', 'All on', 'All off'], title='Setup master mode')
@param.str('sym_kind', default='Forex / CFD (gold, indices, oil)', options=['Forex / CFD (gold, indices, oil)', 'Crypto / stocks'], title='Symbol type (killzone auto filter + day start)')
# --- 2 · Candle (L0)
@param.float('pin_mult', default=2.0, min=0.5, step=0.1, title='Pin bar wick >= N x body')
@param.float('pin_ratio', default=0.55, min=0.1, max=0.95, step=0.01, title='Pin bar wick/range min')
@param.float('doji_max', default=0.10, min=0.01, max=0.5, step=0.01, title='Doji max body/range')
@param.float('large_mult', default=1.5, min=0.5, step=0.1, title='Large range x ATR')
@param.float('long_wick', default=0.50, min=0.2, max=0.95, step=0.05, title='Long-wick rejection wick/range')
@param.float('harami_max', default=0.60, min=0.1, max=1.0, step=0.05, title='Harami body < N x prev')
@param.float('star_prox', default=1.0, min=0.1, step=0.1, title='Shooting star proximity x ATR')
@param.float('ifc_mult', default=2.0, min=0.5, step=0.1, title='IFC wick >= N x body')
@param.bool('ifc_any', default=False, title='IFC allow any colour')
@param.float('manip_wick', default=0.30, min=0.05, max=0.9, step=0.05, title='Manipulative min wick/range')
# --- 3 · Structure (L1)
@param.int('range_bars', default=40, min=5, title='Bars without BOS/CHoCH -> RANGE')
@param.str('disp_gate', default='Candle', options=['Candle', 'Off'], title='Structure needs displacement')
@param.float('disp_body', default=0.5, min=0.2, max=0.9, step=0.05, title='Displacement body/range >=')
@param.float('disp_rng', default=0.6, min=0.2, step=0.1, title='Displacement range >= x ATR')
@param.float('disp_dist', default=0.3, min=0.0, step=0.05, title='...or close beyond level >= x ATR')
@param.int('pend_bars', default=3, min=1, max=10, title='Weak break: follow-through window (bars)')
@param.int('fail_max', default=2, min=1, max=5, title='Failed follow-throughs -> RANGE')
@param.bool('cisd_sweep', default=True, title='CISD only after a qualified liquidity sweep')
# --- 4 · FVG / Strength (L2)
@param.float('fvg_min', default=0.10, min=0.0, step=0.05, title='Min FVG height x ATR')
@param.str('fvg_mode', default='TOUCH', options=['TOUCH', '50%', 'FULL'], title='FVG mitigation mode')
@param.int('max_fvg', default=40, min=5, max=200, title='Max FVGs tracked')
@param.int('fvg_age', default=300, min=20, title='Drop mitigated FVG after N bars')
@param.int('min_fvg_str', default=1, min=1, title='Min FVG for STRONG')
@param.float('body_eff', default=0.55, min=0.1, max=1.0, step=0.05, title='STRONG min body efficiency')
@param.float('mix_max', default=0.35, min=0.0, max=1.0, step=0.05, title='STRONG max mixed ratio')
@param.float('speed_min', default=0.35, min=0.0, step=0.05, title='STRONG min speed')
@param.int('max_move', default=150, min=10, max=400, title='Max bars scanned per move')
# --- 5 · Liquidity (L3)
@param.float('eq_tol', default=0.10, min=0.01, step=0.01, title='Equal H/L tolerance x ATR')
@param.float('touch_tol', default=0.15, min=0.01, step=0.01, title='Touch tolerance x ATR')
@param.int('touch_cd', default=3, min=1, title='Touch cooldown (bars)')
@param.int('ext_lb', default=50, min=10, title='External liquidity lookback')
@param.bool('show_pd', default=True, title='PDH/PDL (intraday)')
@param.bool('show_pw', default=True, title='PWH/PWL (<= daily)')
@param.float('run_body', default=0.60, min=0.1, max=1.0, step=0.05, title='RUN min body ratio')
@param.float('run_close', default=0.25, min=0.0, step=0.05, title='RUN min close beyond x ATR')
@param.float('sweep_wick', default=0.50, min=0.0, max=1.0, step=0.05, title='SWEEP min wick ratio')
@param.str('sweep_qual', default='Major only', options=['Major only', 'Include external'], title='Sweep arms setups when the level is')
@param.int('fail_bars', default=2, min=1, max=5, title='Failed-close window (bars)')
@param.bool('idm_sweep', default=True, title='Internal sweep qualifies at a confirmed zone in HTF-aligned discount / premium')
@param.int('max_levels', default=30, min=5, max=150, title='Max liquidity levels')
# --- 6 · Zones (L4)
@param.int('max_zones', default=30, min=5, max=120, title='Max zones tracked')
@param.int('zone_age', default=500, min=50, title='Drop untouched zone after N bars')
@param.float('zone_max_h', default=3.0, min=0.5, step=0.5, title='Zone max height x ATR')
@param.int('sweep_win', default=10, min=1, title='OB: sweep within N bars before OB')
@param.float('rjb_wick', default=0.50, min=0.3, max=0.9, step=0.05, title='Rejection block min wick ratio')
@param.int('rjb_bars', default=15, min=3, title='Rejection block confirm BOS within N bars')
@param.int('qm_bars', default=60, min=10, title='QM max bars after CHoCH')
@param.int('kl_left', default=50, min=10, title='Key level hidden-interest lookback')
@param.int('kl_min', default=3, min=3, max=5, title='Key level min criteria to show')
@param.bool('sr_trade', default=False, title='Count UNSCORED pivot wick zones as tradable zones')
@param.bool('ob_hp_only', default=False, title='OB: high-probability (liquidity hunt) only')
@param.bool('rcb_fib', default=True, title='Reclaimed: enforce 50% fib')
@param.bool('rjb_pend', default=True, title='M10 may trade an unconfirmed RJB ? (HTF-aligned discount sweep only)')
@param.float('tl_tol', default=0.30, min=0.1, step=0.05, title='Trendline zone +- x ATR')
@param.str('tl_anchor', default='Wick', options=['Wick', 'Body'], title='Trendline anchor')
@param.int('prop_win', default=10, min=2, title='Propulsion: re-departure window (bars after the tap)')
@param.float('prop_imp', default=0.8, min=0.2, step=0.1, title='Propulsion: re-departure size x ATR')
@param.bool('tl_confirm', default=False, title='M64: trendline needs a confirming touch after the two anchor pivots')
# --- 7 · HTF (L5)
@param.str('htf_mode', default='Conservative', options=['Conservative', 'Aggressive', 'Manual'], title='HTF pairing (5m->1h, 15m->4h / aggressive 5m->30m)')
@param.str('htf_manual', default='60', options=['15', '30', '60', '120', '240', 'D', 'W'], title='Manual HTF')
@param.str('gate', default='WARN', options=['OFF', 'WARN', 'STRICT'], title='HTF bias gate')
@param.str('gate_trend', default='Entering bar', options=['Entering bar', 'This bar'], title='Trend the gate reads')
@param.int('htf_swing', default=3, min=1, max=10, title='HTF pivot length')
@param.bool('ltf_pb', default=True, title='LTF-only trend flip = pullback (continuation modules not blocked)')
@param.int('sweep_val', default=3, min=1, max=20, title='HTF sweep valid for N HTF bars')
@param.int('c_look', default=3, min=1, max=10, title='HTF candle levels: candles shown')
@param.float('rej_w', default=0.50, min=0.3, max=0.9, step=0.05, title='HTF rejection min wick ratio')
# --- 8 · Setup filters (L6)
@param.float('retest_br', default=0.7, min=0.2, max=1.0, step=0.05, title='Retest body ratio (M31)')
@param.float('near_zone', default=3.0, min=0.5, step=0.5, title='Liquidity scan distance x ATR (M09)')
@param.int('range_len', default=20, min=5, title='Range detection length (panel regime row)')
@param.float('range_max', default=3.0, min=0.5, step=0.5, title='Range max width x ATR')
@param.int('arm_bars', default=30, min=5, max=200, title='Armed setup stays valid N bars')
@param.str('entry_confirm', default='CONFIRMED', options=['IMMEDIATE', 'CONFIRMED', 'MSS'], title='Zone entry trigger')
@param.int('poi_bars', default=8, min=2, max=30, title='Zone trigger: confirm within (bars)')
@param.float('conf_dist', default=0.10, min=0.0, step=0.05, title='Confirm: close beyond reference >= x ATR')
@param.float('conf_body', default=0.40, min=0.0, max=0.9, step=0.05, title='Confirm: body/range >=')
@param.str('m10_conf', default='Off', options=['Off', '1-bar close above sweep candle', 'CISD'], title='M10 confirm')
# --- 9a · Premium / Discount + Sessions
@param.bool('pd_on', default=True, title='Score premium/discount position')
@param.bool('pd_gate', default=False, title='Block longs in premium / shorts in discount')
@param.float('pd_deep', default=0.75, min=0.55, max=0.95, step=0.05, title='Deep-premium / deep-discount threshold')
@param.bool('pd_cont', default=True, title='Block CONTINUATION modules in deep premium / discount')
@param.bool('hpd', default=True, title='HTF dealing range: discount / premium +1, deep = continuation block')
@param.bool('ssn_on', default=False, title='Only signal inside a killzone')
@param.bool('ssn_score', default=True, title='Score London / NY sessions')
@param.bool('ssn_fx', default=True, title='Killzone filter auto-on for forex / CFD symbols')
@param.bool('ssn_lvl', default=True, title='Asia session high / low as liquidity levels (SESH / SESL)')
@param.bool('ny_open_on', default=True, title='Score NY midnight open (buy below it / sell above it)')
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
@param.bool('d_sig', default=True, title='Setup signals (L6)')
@param.str('dash_pos', default='Bottom right', options=['Bottom right', 'Top right', 'Bottom left', 'Top left'], title='Panel position')
@param.float('dash_w', default=0.28, min=0.05, max=0.70, step=0.01, title='Panel width estimate (raise if cut off, lower to move right)')
@param.int('dash_font', default=11, min=7, max=18, title='Panel font size')
# --- 11/13/15 · Setups (toggle)
@param.bool('en_m01', default=True, title='M01 Breakout rejection trap')
@param.bool('en_m02', default=True, title='M02 Pin bar liquidity trap')
@param.bool('en_m05', default=True, title='M05 Pin bar after breakout')
@param.bool('en_m08', default=True, title='M08 Pin bar on retracement')
@param.bool('en_m09', default=True, title='M09 Pin bar + liquidity')
@param.bool('en_m10', default=True, title='M10 Sweep reversal')
@param.bool('en_m15', default=True, title='M15 Breakout with pin bar')
@param.bool('en_m33', default=True, title='M33 Zone flip model')
@param.bool('en_m36', default=True, title='M36 Weak retracement on OB')
@param.bool('en_m37', default=True, title='M37 Inducement block')
@param.bool('en_m39', default=True, title='M39 Reclaimed block retest')
@param.bool('en_m40', default=True, title='M40 Rejection block retest')
@param.bool('en_m41', default=True, title='M41 Sweep + FVG confluence')
@param.bool('en_m42', default=True, title='M42 High-probability S&D')
@param.bool('en_m45', default=True, title='M45 Sweep-based CHoCH retest')
@param.bool('en_m46', default=True, title='M46 CISD setup')
@param.bool('en_m51', default=True, title='M51 Smart BOS model')
@param.bool('en_m54', default=True, title='M54 Smart S&D trap')
@param.bool('en_m58', default=True, title='M58 Double top / bottom')
@param.bool('en_m62', default=True, title='M62 Fakeout trap')
@param.bool('en_m64', default=True, title='M64 Auto trendline (draw)')
@param.bool('en_m68', default=True, title='M68 HTF sweep -> LTF entry')
@param.bool('en_m69', default=True, title='M69 IFC candle')
@param.bool('en_m70', default=True, title='M70 Quasimodo')
@param.bool('en_m72', default=True, title='M72 Operator trap')
@param.bool('en_m73', default=True, title='M73 Propulsion Block (ICT)')
@param.bool('en_m74', default=True, title='M74 MSS -> FVG retrace limit (ICT)')
# --- 12 · Setup filters
@param.bool('fl_m19', default=True, title='M19 suppress reversal after STRONG arrival')
@param.bool('fl_m26', default=True, title='M26 pullback must be corrective (mixed)')
@param.bool('fl_m31', default=False, title='M31 retest body-size rule')
@param.bool('fl_swr', default=True, title='6.2 block reversal at touch>=2 unless swept')
@param.bool('fl_50', default=True, title='6.6 S&D 50% rule')
@param.bool('fl_m01t', default=True, title='M01/M02 require the broken level to have been rejected >=2x')
@param.str('z_close', default='50%', options=['Off', '50%', 'Top'], title='Zone reversal must close beyond')
# --- 16 · S-AB parameters
@param.float('dt_tol', default=0.15, min=0.05, step=0.05, title='Double top tolerance x ATR')
@param.int('cons_min', default=4, min=2, title='M72 consolidation min bars')
@param.float('cons_max', default=1.5, min=0.5, step=0.25, title='M72 consolidation max width x ATR')
# --- 14 · Trade (L7)
@param.float('sl_buf', default=0.15, min=0.0, step=0.05, title='SL buffer x ATR')
@param.float('max_sl', default=2.0, min=0.5, step=0.5, title='Max SL distance x ATR (major HL/LH rule)')
@param.float('min_rr', default=2.0, min=1.0, step=0.5, title='Min R:R - signals below this are hidden')
@param.float('max_rr', default=6.0, min=2.0, step=0.5, title='Max R:R - a target further than this does not count')
@param.bool('fixed_r', default=False, title='Fixed-R mode')
@param.float('fixed_rm', default=2.0, min=0.5, step=0.5, title='Fixed R multiple (TP1; TP2 = +1R)')
@param.bool('rr_real', default=True, title='Require a REAL target (zone / FVG / liquidity) at Min R:R')
@param.str('tp_path', default='STRICT', options=['OFF', 'WARN', 'STRICT'], title='TP1 path check')
@param.int('min_score', default=8, min=0, max=20, title='Min score to show')
@param.int('grade_ap', default=11, min=1, max=20, title='A+ >=')
@param.int('grade_a', default=9, min=1, max=20, title='A >=')
@param.int('sig_gap', default=5, min=0, max=100, title='Min bars between signals (both sides)')
@param.int('id_bars', default=50, min=0, max=500, title='Suppress a repeat of the SAME setup for N bars')
@param.str('entry_mode', default='IMMEDIATE', options=['IMMEDIATE', 'RETEST', 'BOTH'], title='M10 entry mode')
@param.str('entry_px', default='CLOSE', options=['CLOSE', 'CANDLE 50%', 'ZONE EDGE', 'RETRACE'], title='Entry price')
@param.int('ret_bars', default=12, min=2, max=100, title='RETRACE: limit valid (bars)')
@param.float('auto_ret', default=1.5, min=0.0, step=0.25, title='Auto-RETRACE when the confirming candle >= x ATR (0 = off)')
@param.int('m74_bars', default=20, min=2, max=100, title='M74: limit valid (bars)')
@param.int('min_risk_t', default=20, min=0, max=1000, title='Min risk (ticks)')
@param.float('min_risk_a', default=0.3, min=0.0, step=0.05, title='... or x ATR')
@param.bool('trade_ln', default=True, title='Draw entry / SL / TP lines')
@param.int('trade_bars', default=20, min=5, max=100, title='Trade line length (bars)')
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
    def calc(self, start_date, dbg_stop, atr_len, swing_len, max_labels, max_lines, min_gap, lbl_mode, set_mode, sym_kind, pin_mult, pin_ratio, doji_max, large_mult, long_wick, harami_max, star_prox, ifc_mult, ifc_any, manip_wick, range_bars, disp_gate, disp_body, disp_rng, disp_dist, pend_bars, fail_max, cisd_sweep, fvg_min, fvg_mode, max_fvg, fvg_age, min_fvg_str, body_eff, mix_max, speed_min, max_move, eq_tol, touch_tol, touch_cd, ext_lb, show_pd, show_pw, run_body, run_close, sweep_wick, sweep_qual, fail_bars, idm_sweep, max_levels, max_zones, zone_age, zone_max_h, sweep_win, rjb_wick, rjb_bars, qm_bars, kl_left, kl_min, sr_trade, ob_hp_only, rcb_fib, rjb_pend, tl_tol, tl_anchor, prop_win, prop_imp, tl_confirm, htf_mode, htf_manual, gate, gate_trend, htf_swing, ltf_pb, sweep_val, c_look, rej_w, retest_br, near_zone, range_len, range_max, arm_bars, entry_confirm, poi_bars, conf_dist, conf_body, m10_conf, pd_on, pd_gate, pd_deep, pd_cont, hpd, ssn_on, ssn_score, ssn_fx, ssn_lvl, ny_open_on, fill_t, box_t, line_t, filled, lbl_font, zone_font, cap_call, lbl_off, ext_bars, d_struct, d_pb, d_weak_bos, d_cisd_all, d_fvg, d_fvg_mit, d_liq, d_liq_evt, d_liq_all, d_ob_diag, d_ob, d_brk, d_kl, d_sr, d_rcb, d_rjb, d_qm, d_htf, d_htf_evt, d_bg, d_candle, d_panel, d_legend, d_sig, dash_pos, dash_w, dash_font, en_m01, en_m02, en_m05, en_m08, en_m09, en_m10, en_m15, en_m33, en_m36, en_m37, en_m39, en_m40, en_m41, en_m42, en_m45, en_m46, en_m51, en_m54, en_m58, en_m62, en_m64, en_m68, en_m69, en_m70, en_m72, en_m73, en_m74, fl_m19, fl_m26, fl_m31, fl_swr, fl_50, fl_m01t, z_close, dt_tol, cons_min, cons_max, sl_buf, max_sl, min_rr, max_rr, fixed_r, fixed_rm, rr_real, tp_path, min_score, grade_ap, grade_a, sig_gap, id_bars, entry_mode, entry_px, ret_bars, auto_ret, m74_bars, min_risk_t, min_risk_a, trade_ln, trade_bars):
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
        tick = self.info.tick_size
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
        en_a = set_mode == 'All on' or set_mode == 'Core only'
        en_x = set_mode == 'All off'
        e01 = ((en_m01 or en_a) and not en_x)
        e02 = ((en_m02 or en_a) and not en_x)
        e05 = ((en_m05 or en_a) and not en_x)
        e08 = ((en_m08 or en_a) and not en_x)
        e09 = ((en_m09 or en_a) and not en_x)
        e10 = ((en_m10 or en_a) and not en_x)
        e15 = ((en_m15 or en_a) and not en_x)
        e33 = ((en_m33 or en_a) and not en_x)
        e36 = ((en_m36 or en_a) and not en_x)
        e37 = ((en_m37 or en_a) and not en_x)
        e39 = ((en_m39 or en_a) and not en_x)
        e40 = ((en_m40 or en_a) and not en_x)
        e41 = ((en_m41 or en_a) and not en_x)
        e42 = ((en_m42 or en_a) and not en_x)
        e45 = ((en_m45 or en_a) and not en_x)
        e46 = ((en_m46 or en_a) and not en_x)
        e51 = ((en_m51 or en_a) and not en_x)
        e54 = ((en_m54 or en_a) and not en_x)
        e58 = ((en_m58 or en_a) and not en_x)
        e62 = ((en_m62 or en_a) and not en_x)
        e64 = ((en_m64 or en_a) and not en_x)
        e68 = ((en_m68 or en_a) and not en_x)
        e69 = ((en_m69 or en_a) and not en_x)
        e70 = ((en_m70 or en_a) and not en_x)
        e72 = ((en_m72 or en_a) and not en_x)
        e73 = ((en_m73 or en_a) and not en_x)
        e74 = ((en_m74 or en_a) and not en_x)
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
        p_body = abs(c1 - o1)
        pin_bull = dn_wick >= pin_mult * body and dn_r >= pin_ratio and up_wick <= body
        pin_bear = up_wick >= pin_mult * body and up_r >= pin_ratio and dn_wick <= body
        engulf_bull = is_bull and c >= o1 and o <= c1 and c1 < o1
        engulf_bear = is_bear and c <= o1 and o >= c1 and c1 > o1
        harami = h < h1 and l > l1 and body < p_body * harami_max
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
        if dbg <= 3:
            self.eng_bi = bi
            self.eng_close = c
            if self.is_last_bar:
                self.live_draw(ext_bars, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min, ret_bars, m74_bars)
            return plot.Background(color.TRANSPARENT)
        # arrival strength (per side, rides the zone snapshot)
        zone_touch = self.ft_zb.kind != '' or self.ft_zs.kind != ''
        arr_dir_now = 1 if self.ft_zb.kind != '' else -1
        if zone_touch and (bi - self.arrival_bar > 5 or self.arrival_dir != arr_dir_now):
            from_idx = self.cur_high_idx if arr_dir_now == 1 else self.cur_low_idx
            self.move_strength(from_idx, bi, atr, arr_dir_now != 1, max_move, min_fvg_str, body_eff, mix_max, speed_min)
            self.arrival_strong = self.ms_strong
            self.arrival_bar = bi
            self.arrival_dir = arr_dir_now
            self.arrival_avg_body = self.ms_avg_body
            self.arrival_mixed = self.ms_mixed
        retest_valid = False
        if zone_touch and bi - self.arrival_bar <= 10:
            z_a = self.ft_zb if self.arrival_dir == 1 else self.ft_zs
            if z_a.kind != '':
                z_a.arr = -1 if self.arrival_strong else 1
                z_a.arr_mix = self.arrival_mixed
            retest_valid = self.last_bos_avg_body > 0 and self.arrival_avg_body < self.last_bos_avg_body * retest_br
        # wick sequences
        wk = 0.4
        up_wick_inc = up_r >= wk and self.up_r1 >= wk and self.up_r2 >= wk and up_wick > self.up_w1 and self.up_w1 > self.up_w2
        up_wick_dec = up_r >= 0.25 and self.up_w1 > up_wick and self.up_w2 > self.up_w1 and self.up_w2 > 0
        dn_wick_inc = dn_r >= wk and self.dn_r1 >= wk and self.dn_r2 >= wk and dn_wick > self.dn_w1 and self.dn_w1 > self.dn_w2
        dn_wick_dec = dn_r >= 0.25 and self.dn_w1 > dn_wick and self.dn_w2 > self.dn_w1 and self.dn_w2 > 0
        self.up_w2 = self.up_w1
        self.up_w1 = up_wick
        self.dn_w2 = self.dn_w1
        self.dn_w1 = dn_wick
        self.up_r2 = self.up_r1
        self.up_r1 = up_r
        self.dn_r2 = self.dn_r1
        self.dn_r1 = dn_r
        # breakout state
        break_up = self.st_bull_bos or self.st_weak_bull or self.st_int_bull or self.st_bull_choch or self.ft_run_up
        break_dn = self.st_bear_bos or self.st_weak_bear or self.st_int_bear or self.st_bear_choch or self.ft_run_dn
        if break_up or break_dn:
            self.break_dir = 1 if break_up else -1
            self.brk_internal = self.st_int_bull or self.st_int_bear
            st_up = self.st_bull_bos or self.st_weak_bull or self.st_int_bull
            st_dn = self.st_bear_bos or self.st_weak_bear or self.st_int_bear
            if break_up:
                self.break_lvl = self.st_ch_lvl if self.st_bull_choch else (pre_high if st_up else nz(self.ft_run_price, self.ft_swept_price))
            else:
                self.break_lvl = self.st_ch_lvl if self.st_bear_choch else (pre_low if st_dn else nz(self.ft_run_price, self.ft_swept_price))
            if isnan(self.break_lvl):
                self.break_lvl = pre_high if break_up else pre_low
            self.break_bar = bi
            self.break_lo = l
            self.break_hi = h
        break_ago = bi - self.break_bar
        fake_break = break_ago == 1 and (not isnan(self.break_lvl)) and ((c < self.break_lvl) if self.break_dir == 1 else (c > self.break_lvl))
        break_pin_bull = break_up and (not self.brk_internal) and pin_bull and (not isnan(self.break_lvl)) and l < self.break_lvl
        break_pin_bear = break_dn and (not self.brk_internal) and pin_bear and (not isnan(self.break_lvl)) and h > self.break_lvl
        cont_brk = not self.brk_internal
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
        fifty_now = (self.ft_zb.kind == 'OB' and self.ft_zb.fifty) or (self.ft_zs.kind == 'OB' and self.ft_zs.fifty)
        self.fifty_prev = fifty_now
        # P7b features
        self.ft_in_range = False
        if self.is_last_bar and self.bars_since_evt >= range_len:
            self.ft_in_range = (self.hh_n(range_len, 0) - self.ll_n(range_len, 0)) <= atr * range_max
        at_bull_fvg_f = False
        at_bear_fvg_f = False
        for g in self.fvgs:
            if ((not g.mitigated) or g.mit_idx == bi) and g.idx < bi - 1:
                if g.is_bull and l <= g.top and h >= g.bottom and c >= g.bottom:
                    self.ft_at_bull_fvg = True
                    if self.swept_low_bar >= 0 and g.idx >= self.swept_low_bar - fail_bars:
                        at_bull_fvg_f = True
                if (not g.is_bull) and h >= g.bottom and l <= g.top and c <= g.top:
                    self.ft_at_bear_fvg = True
                    if self.swept_high_bar >= 0 and g.idx >= self.swept_high_bar - fail_bars:
                        at_bear_fvg_f = True
        if self.ft_new_bull_fvg:
            self.bull_fvg_bar = bi
        if self.ft_new_bear_fvg:
            self.bear_fvg_bar = bi
        sweep_bos_bear = bi - self.swept_high_bar <= 10 and self.swept_high_bar >= 0 and self.st_bear_bos
        sweep_bos_bull = bi - self.swept_low_bar <= 10 and self.swept_low_bar >= 0 and self.st_bull_bos
        sweep_choch_bear = bi - self.swept_high_bar <= 10 and self.swept_high_bar >= 0 and self.st_bear_choch
        sweep_choch_bull = bi - self.swept_low_bar <= 10 and self.swept_low_bar >= 0 and self.st_bull_choch
        if sweep_bos_bear:
            self.m45_dir = -1
            self.m45_bar = bi
        if sweep_bos_bull:
            self.m45_dir = 1
            self.m45_bar = bi
        if sweep_choch_bear:
            self.m45_dir = -2
            self.m45_bar = bi
        if sweep_choch_bull:
            self.m45_dir = 2
            self.m45_bar = bi
        if self.st_bear_bos and bi - self.swept_high_bar <= 20 and self.swept_high_bar >= 0:
            self.m41_dir = -1 if self.mv_strong else -9
            self.m41_bar = bi
        if self.st_bull_bos and bi - self.swept_low_bar <= 20 and self.swept_low_bar >= 0:
            self.m41_dir = 1 if self.mv_strong else 9
            self.m41_bar = bi
        rel_cnt_bear = (1 if (self.ft_htf_rej_bear or self.ft_htf_sweep_up) else 0) + (1 if bi - self.bear_fvg_bar <= 3 else 0) + (1 if bi - self.swept_high_bar <= 5 else 0)
        rel_cnt_bull = (1 if (self.ft_htf_rej_bull or self.ft_htf_sweep_dn) else 0) + (1 if bi - self.bull_fvg_bar <= 3 else 0) + (1 if bi - self.swept_low_bar <= 5 else 0)
        cisd_rel = rel_cnt_bear if self.st_cisd_bear else (rel_cnt_bull if self.st_cisd_bull else 0)
        if self.st_cisd_bear and rel_cnt_bear > 0:
            self.m46_dir = -1
            self.m46_bar = bi
        if self.st_cisd_bull and rel_cnt_bull > 0:
            self.m46_dir = 1
            self.m46_bar = bi
        # M54 stages
        if self.ft_at_demand and self.m54_stage == 0:
            self.m54_stage = 1
            self.m54_bar = bi
            self.m54_zb = self.ft_zb.bottom
        if self.m54_stage == 1 and bi > self.m54_bar and self.ft_swept_low_q and self.ft_swept_price_lo <= self.m54_zb and self.ft_swept_price_lo >= self.m54_zb - atr * 1.5:
            self.m54_stage = 2
            self.m54_bar = bi
        if self.m54_stage == 2 and bi > self.m54_bar and self.st_bull_bos and self.leg_idx >= self.swept_low_bar - fail_bars:
            self.m54_stage = 3
            self.m54_bar = bi
        if self.m54_stage > 0 and bi - self.m54_bar > arm_bars * 2:
            self.m54_stage = 0
        if self.ft_at_supply and self.m54_stage_b == 0:
            self.m54_stage_b = 1
            self.m54_bar_b = bi
            self.m54_zs = self.ft_zs.top
        if self.m54_stage_b == 1 and bi > self.m54_bar_b and self.ft_swept_high_q and self.ft_swept_price_hi >= self.m54_zs and self.ft_swept_price_hi <= self.m54_zs + atr * 1.5:
            self.m54_stage_b = 2
            self.m54_bar_b = bi
        if self.m54_stage_b == 2 and bi > self.m54_bar_b and self.st_bear_bos and self.leg_idx >= self.swept_high_bar - fail_bars:
            self.m54_stage_b = 3
            self.m54_bar_b = bi
        if self.m54_stage_b > 0 and bi - self.m54_bar_b > arm_bars * 2:
            self.m54_stage_b = 0
        # M01/M02 level rejection counter
        if (break_up or break_dn) and not isnan(self.break_lvl):
            t_cnt = 0
            was_at = False
            kmax = min(30, bi)
            for k in range(1, kmax + 1):
                at_lvl = self.high[k] >= self.break_lvl - atr * touch_tol and self.low[k] <= self.break_lvl + atr * touch_tol
                if at_lvl and not was_at:
                    t_cnt += 1
                was_at = at_lvl
            self.brk_touch = t_cnt
        brk_touches = self.brk_touch
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
        at_tl_sup = tl_sup_valid and l <= tl_s + tlz and c >= tl_s - tlz
        at_tl_res = tl_res_valid and h >= tl_r - tlz and c <= tl_r + tlz
        # ---------------------------------------------------- L6 SETUPS A–I
        rev_bull = pin_bull or engulf_bull or ifc_bull or manip_bull
        rev_bear = pin_bear or engulf_bear or ifc_bear or manip_bear
        imm_mode = entry_confirm == 'IMMEDIATE'
        mss_mode = entry_confirm == 'MSS'
        if (not imm_mode) and self.poi_dir_l == 1 and self.ft_zb.kind == '' and self.poi_zb_ok:
            self.zs_copy(self.ft_zb, self.poi_zb)
            self.ft_at_demand = self.ft_zb.kind != 'SR'
            self.ft_at_support = self.ft_zb.kind == 'SR'
        if (not imm_mode) and self.poi_dir_s == 1 and self.ft_zs.kind == '' and self.poi_zs_ok:
            self.zs_copy(self.ft_zs, self.poi_zs)
            self.ft_at_supply = self.ft_zs.kind != 'SR'
            self.ft_at_resist = self.ft_zs.kind == 'SR'
        zb = self.ft_zb
        zs = self.ft_zs
        at_bull_zone = zb.kind != ''
        at_bear_zone = zs.kind != ''
        bull_trend = self.st_trend == 'BULLISH'
        bear_trend = self.st_trend == 'BEARISH'
        z_mid_b = zb.kind == '' or z_close == 'Off' or c >= (zb.top if z_close == 'Top' else (zb.top + zb.bottom) * 0.5)
        z_mid_s = zs.kind == '' or z_close == 'Off' or c <= (zs.bottom if z_close == 'Top' else (zs.top + zs.bottom) * 0.5)
        poi_arm_l = (not imm_mode) and self.poi_dir_l == 1 and self.poi_zb_ok and zb.top == self.poi_zb.top and zb.bottom == self.poi_zb.bottom
        poi_arm_s = (not imm_mode) and self.poi_dir_s == 1 and self.poi_zs_ok and zs.top == self.poi_zs.top and zs.bottom == self.poi_zs.bottom
        if poi_arm_l:
            zb.sw = self.poi_sw_l
        if poi_arm_s:
            zs.sw = self.poi_sw_s
        zone_ok_bull = at_bull_zone and (not zb.pend) and z_mid_b and ((not fl_swr) or (not zb.sweep_req) or self.ft_swept_low or poi_arm_l) and ((not fl_50) or zb.kind == 'SR' or zb.fifty)
        zone_ok_bear = at_bear_zone and (not zs.pend) and z_mid_s and ((not fl_swr) or (not zs.sweep_req) or self.ft_swept_high or poi_arm_s) and ((not fl_50) or zs.kind == 'SR' or zs.fifty)
        arr_ok_bull = (not fl_m19) or zb.arr != -1
        arr_ok_bear = (not fl_m19) or zs.arr != -1
        pb_ok_l = (not fl_m26) or zb.arr != -1 or zb.arr_mix >= 0.35
        pb_ok_s = (not fl_m26) or zs.arr != -1 or zs.arr_mix >= 0.35
        rt_ok = (not fl_m31) or not (zone_touch and retest_valid == False and self.last_bos_avg_body > 0)
        brk_win = break_ago >= 1 and break_ago <= 8
        brk_touch_ok = (not fl_m01t) or brk_touches >= 2
        # S11 POI reaction machine
        poi_conf_l = False
        poi_conf_s = False
        if not imm_mode:
            poi_buf = atr * 0.15
            if self.poi_dir_l == 1 and (bi - self.poi_bar_l > poi_bars or c < self.poi_low_l - poi_buf):
                self.poi_dir_l = 0
            if self.poi_dir_s == 1 and (bi - self.poi_bar_s > poi_bars or c > self.poi_high_s + poi_buf):
                self.poi_dir_s = 0
            cf_up = is_bull and c > self.poi_ref_l + atr * conf_dist and body_r >= conf_body
            cf_dn = is_bear and c < self.poi_ref_s - atr * conf_dist and body_r >= conf_body
            if self.poi_dir_l == 1 and bi - self.poi_bar_l >= 1 and (cf_up or self.ft_new_bull_fvg):
                poi_conf_l = True
                self.poi_dir_l = 0
            if self.poi_dir_s == 1 and bi - self.poi_bar_s >= 1 and (cf_dn or self.ft_new_bear_fvg):
                poi_conf_s = True
                self.poi_dir_s = 0
            if self.poi_dir_l == 0 and (not poi_conf_l) and (zone_ok_bull or self.ft_at_bull_fvg) and rev_bull:
                self.poi_dir_l = 1
                self.poi_bar_l = bi
                self.poi_ref_l = max(h, self.hh_n(5, 1)) if mss_mode else h
                self.poi_wick_l = dn_r
                self.poi_low_l = min(l, nz(zb.bottom, l))
                self.poi_fvg_l = self.ft_at_bull_fvg and zb.kind == ''
                self.zs_copy(self.poi_zb, zb)
                self.poi_zb_ok = True
                self.poi_sw_l = 2 if self.ft_swept_low_q else (1 if self.ft_swept_low else 0)
            if self.poi_dir_s == 0 and (not poi_conf_s) and (zone_ok_bear or self.ft_at_bear_fvg) and rev_bear:
                self.poi_dir_s = 1
                self.poi_bar_s = bi
                self.poi_ref_s = min(l, self.ll_n(5, 1)) if mss_mode else l
                self.poi_wick_s = up_r
                self.poi_high_s = max(h, nz(zs.top, h))
                self.poi_fvg_s = self.ft_at_bear_fvg and zs.kind == ''
                self.zs_copy(self.poi_zs, zs)
                self.poi_zs_ok = True
                self.poi_sw_s = 2 if self.ft_swept_high_q else (1 if self.ft_swept_high else 0)
        trig_bull = rev_bull if imm_mode else poi_conf_l
        trig_bear = rev_bear if imm_mode else poi_conf_s
        # C — M10 sweep reversal (+ W10 confirm)
        fresh_disp_up = self.break_dir == 1 and bi - self.break_bar <= 10 and self.last_dep_strong
        fresh_disp_dn = self.break_dir == -1 and bi - self.break_bar <= 10 and self.last_dep_strong
        s10raw = e10 and (not fresh_disp_dn) and (self.ft_swept_low_q or (self.ft_swept_low and zb.kind != '' and ((not zb.pend) or (self.ft_htf_bias == 'BULL' and self.ft_in_discount)))) and dn_r >= sweep_wick and c > self.ft_swept_price_lo and c >= (h + l) * 0.5
        s10braw = e10 and (not fresh_disp_up) and (self.ft_swept_high_q or (self.ft_swept_high and zs.kind != '' and ((not zs.pend) or (self.ft_htf_bias == 'BEAR' and self.ft_in_premium)))) and up_r >= sweep_wick and c < self.ft_swept_price_hi and c <= (h + l) * 0.5
        m10_imm = m10_conf == 'Off'
        m10_win = arm_bars if m10_conf == 'CISD' else 3
        m10_trg = (not m10_imm) and self.m10_dir == 1 and bi - self.m10_bar >= 1 and bi - self.m10_bar <= m10_win and (self.st_cisd_bull if m10_conf == 'CISD' else c > self.m10_ref)
        m10_trgb = (not m10_imm) and self.m10_dir == -1 and bi - self.m10_bar >= 1 and bi - self.m10_bar <= m10_win and (self.st_cisd_bear if m10_conf == 'CISD' else c < self.m10_ref)
        if self.m10_dir == 1 and (m10_trg or bi - self.m10_bar > m10_win or c < self.m10_ext):
            self.m10_dir = 0
        if self.m10_dir == -1 and (m10_trgb or bi - self.m10_bar > m10_win or c > self.m10_ext):
            self.m10_dir = 0
        if m10_trg:
            self.ft_swept_low = True
            self.ft_swept_price_lo = self.m10_lvl
            self.ft_swept_kind_lo = self.m10_kind
            self.ft_swept_base_lo = self.m10_base
            self.ft_swept_t3_lo = self.m10_t3
            self.ft_swept_ext_lo = self.m10_ext
        if m10_trgb:
            self.ft_swept_high = True
            self.ft_swept_price_hi = self.m10_lvl
            self.ft_swept_kind_hi = self.m10_kind
            self.ft_swept_base_hi = self.m10_base
            self.ft_swept_t3_hi = self.m10_t3
            self.ft_swept_ext_hi = self.m10_ext
        if (not m10_imm) and s10raw:
            self.m10_dir = 1
            self.m10_bar = bi
            self.m10_ref = h
            self.m10_ext = min(l, nz(self.ft_swept_ext_lo, l))
            self.m10_lvl = self.ft_swept_price_lo
            self.m10_kind = self.ft_swept_kind_lo
            self.m10_base = self.ft_swept_base_lo
            self.m10_t3 = self.ft_swept_t3_lo
        if (not m10_imm) and s10braw:
            self.m10_dir = -1
            self.m10_bar = bi
            self.m10_ref = l
            self.m10_ext = max(h, nz(self.ft_swept_ext_hi, h))
            self.m10_lvl = self.ft_swept_price_hi
            self.m10_kind = self.ft_swept_kind_hi
            self.m10_base = self.ft_swept_base_hi
            self.m10_t3 = self.ft_swept_t3_hi
        s10 = s10raw if m10_imm else m10_trg
        s10b = s10braw if m10_imm else m10_trgb
        poi_nl = min(max(bi - self.poi_bar_l, 0), poi_bars) + 1
        poi_ns = min(max(bi - self.poi_bar_s, 0), poi_bars) + 1
        set_lo_l = self.ll_n(poi_nl, 0) if poi_conf_l else l
        set_hi_s = self.hh_n(poi_ns, 0) if poi_conf_s else h
        # E-4 · M74 pre-conditions
        m74_up = e74 and self.ft_htf_bias != 'BEAR' and ((self.st_bull_choch and self.choch_real) or (self.st_bull_bos and self.mv_strong and self.mv_fvg >= 1))
        m74_dn = e74 and self.ft_htf_bias != 'BULL' and ((self.st_bear_choch and self.choch_real) or (self.st_bear_bos and self.mv_strong and self.mv_fvg >= 1))
        m74_x = math.nan
        m74_f = math.nan
        if m74_up or m74_dn:
            m74_x = self.leg_ext(not m74_up, self.leg_idx)
            m74_f = self.leg_fvg(m74_up, self.leg_idx, c)
        m74_px = ((m74_x + h) * 0.5 if m74_up else (m74_x + l) * 0.5) if isnan(m74_f) else m74_f
        m74_sw = self.swept_low_bar if m74_up else self.swept_high_bar
        m74_t = 4 if (m74_sw >= 0 and self.leg_idx - m74_sw <= 10 and self.leg_idx - m74_sw >= -2) else 3
        m74_note = ''
        if m74_up or m74_dn:
            m74_note = 'MSS → FVG retrace: ' + ('real CHoCH' if (self.st_bull_choch or self.st_bear_choch) else 'strong BOS') + (' · limit at leg 50%' if isnan(m74_f) else ' · limit at FVG CE') + (' · after a qualified sweep' if m74_t == 4 else '')
        # A — price action
        s01 = e01 and self.break_dir == 1 and brk_win and brk_touch_ok and up_wick_inc and is_bear and body_r >= 0.5 and c < self.break_lvl
        s02 = e02 and cont_brk and self.break_dir == 1 and brk_win and brk_touch_ok and up_wick_dec and (pin_bull or engulf_bull)
        s01b = e01 and self.break_dir == -1 and brk_win and brk_touch_ok and dn_wick_inc and is_bull and body_r >= 0.5 and c > self.break_lvl
        s02b = e02 and cont_brk and self.break_dir == -1 and brk_win and brk_touch_ok and dn_wick_dec and (pin_bear or engulf_bear)
        s05 = e05 and cont_brk and self.break_dir == 1 and break_ago == 1 and pin_bull
        s05b = e05 and cont_brk and self.break_dir == -1 and break_ago == 1 and pin_bear
        wick_l = dn_r if imm_mode else self.poi_wick_l
        wick_s = up_r if imm_mode else self.poi_wick_s
        s08 = e08 and bull_trend and zone_ok_bull and trig_bull
        s08b = e08 and bear_trend and zone_ok_bear and trig_bear
        s09 = e09 and zone_ok_bull and trig_bull and wick_l >= 0.65 and self.ft_bsl_above >= 2
        s09b = e09 and zone_ok_bear and trig_bear and wick_s >= 0.65 and self.ft_ssl_below >= 2
        s15 = e15 and break_pin_bull
        s15b = e15 and break_pin_bear
        s33 = e33 and zone_ok_bull and zb.flipped and zb.dep_strong and zb.arr == 1 and trig_bull and bull_trend and self.ft_htf_bias == 'BULL'
        s33b = e33 and zone_ok_bear and zs.flipped and zs.dep_strong and zs.arr == 1 and trig_bear and bear_trend and self.ft_htf_bias == 'BEAR'
        ob_bull = zone_ok_bull and (zb.kind == 'OB' or zb.kind == 'BRK')
        ob_bear = zone_ok_bear and (zs.kind == 'OB' or zs.kind == 'BRK')
        s36 = e36 and ob_bull and zb.arr == 1 and trig_bull
        s36b = e36 and ob_bear and zs.arr == 1 and trig_bear
        s37 = e37 and ob_bull and zb.idm and trig_bull
        s37b = e37 and ob_bear and zs.idm and trig_bear
        self.bl_n = ''
        self.bl_s = 0
        self.bl_t = ''
        self.bs_n = ''
        self.bs_s = 0
        self.bs_t = ''
        if s02 and arr_ok_bull:
            self.bid(True, True, 'M02', 21, 'Pin-bar continuation: shrinking upper wicks after breakout + bullish pin → LONG')
        if s01b and arr_ok_bull:
            self.bid(True, True, 'M01', 21, 'Breakout rejection trap (mirror): growing lower wicks then strong close back above')
        if s05:
            self.bid(True, True, 'M05', 21, 'Pin bar right after breakout: flipped support held')
        if s08 and arr_ok_bull and pb_ok_l and rt_ok:
            self.bid(True, True, 'M08', 21, 'Trend + support/demand + bullish pin bar')
        if s09 and arr_ok_bull:
            self.bid(True, True, 'M09', 32, 'HIGH QUALITY: strong pin bar at level with ≥2 liquidity targets above')
        m10_tier_l = 3 if self.ft_swept_t3_lo else 2
        m10_tier_s = 3 if self.ft_swept_t3_hi else 2
        if s10:
            self.bid(True, s10, 'M10', m10_tier_l * 10 + 1, 'Liquidity SWEEP reversal: swept ' + self.ft_swept_kind_lo + ', closed back above' + ('' if m10_imm else ' + confirm (' + m10_conf + ')') + '. SL below sweep low')
        if s15:
            self.bid(True, True, 'M15', 21, 'Breakout candle is itself a bullish pin bar')
        if s33 and rt_ok:
            self.bid(True, True, 'M33', 32, 'Zone flip model: strong breakout → weak retest → refusal, trend + HTF aligned')
        if s36 and pb_ok_l:
            self.bid(True, True, 'M36', 32, 'Weak retracement into valid OB + bullish reversal')
        if s37:
            self.bid(True, True, 'M37', 43, 'Inducement block: EQL swept before the OB tap + reversal')
        if s01 and arr_ok_bear:
            self.bid(False, True, 'M01', 21, 'Breakout rejection trap: growing upper wicks after breakout, strong close back below → SHORT')
        if s02b and arr_ok_bear:
            self.bid(False, True, 'M02', 21, 'Pin-bar continuation (mirror): shrinking lower wicks after breakdown → SHORT')
        if s05b:
            self.bid(False, True, 'M05', 21, 'Pin bar right after breakdown')
        if s08b and arr_ok_bear and pb_ok_s and rt_ok:
            self.bid(False, True, 'M08', 21, 'Trend + resistance/supply + bearish pin bar')
        if s09b and arr_ok_bear:
            self.bid(False, True, 'M09', 32, 'HIGH QUALITY: strong pin bar at level with ≥2 liquidity targets below')
        if s10b:
            self.bid(False, s10b, 'M10', m10_tier_s * 10 + 1, 'Liquidity SWEEP reversal: swept ' + self.ft_swept_kind_hi + ', closed back below' + ('' if m10_imm else ' + confirm (' + m10_conf + ')') + '. SL above sweep high')
        if s15b:
            self.bid(False, True, 'M15', 21, 'Breakdown candle is itself a bearish pin bar')
        if s33b and rt_ok:
            self.bid(False, True, 'M33', 32, 'Zone flip model (bearish)')
        if s36b and pb_ok_s:
            self.bid(False, True, 'M36', 32, 'Weak retracement into valid bearish OB + reversal')
        if s37b:
            self.bid(False, True, 'M37', 43, 'Inducement block (bearish): EQH swept before OB tap')
        warn_up = 'RUN — avoid' if (self.ft_run_up and e10 and (d_liq_all or self.ft_run_major)) else ''
        warn_dn = 'RUN — avoid' if (self.ft_run_dn and e10 and (d_liq_all or self.ft_run_major)) else ''
        # ---------------------------------------------------- L6 SETUPS J–R
        react_bull = zone_ok_bull or self.ft_at_bull_fvg or (poi_conf_l and self.poi_fvg_l)
        react_bear = zone_ok_bear or self.ft_at_bear_fvg or (poi_conf_s and self.poi_fvg_s)
        react_bull_f = zone_ok_bull or at_bull_fvg_f or (poi_conf_l and self.poi_fvg_l)
        react_bear_f = zone_ok_bear or at_bear_fvg_f or (poi_conf_s and self.poi_fvg_s)
        s39 = e39 and zone_ok_bull and zb.kind == 'RCB' and trig_bull
        s39b = e39 and zone_ok_bear and zs.kind == 'RCB' and trig_bear
        s40 = e40 and zone_ok_bull and zb.kind == 'RJB' and trig_bull
        s40b = e40 and zone_ok_bear and zs.kind == 'RJB' and trig_bear
        s41 = e41 and self.armed(1, self.m41_dir, self.m41_bar, arm_bars) and react_bull_f and trig_bull
        s41b = e41 and self.armed(-1, self.m41_dir, self.m41_bar, arm_bars) and react_bear_f and trig_bear
        w41 = e41 and (self.m41_dir == 9 or self.m41_dir == -9) and bi == self.m41_bar
        s42 = e42 and zone_ok_bull and zb.kind == 'OB' and zb.dep_strong and zb.fifty and zb.arr == 1 and trig_bull
        s42b = e42 and zone_ok_bear and zs.kind == 'OB' and zs.dep_strong and zs.fifty and zs.arr == 1 and trig_bear
        s45 = e45 and self.armed_sw(1, self.m45_dir, self.m45_bar, arm_bars) and zone_ok_bull and (zb.kind == 'BRK' or zb.kind == 'OB') and trig_bull
        s45b = e45 and self.armed_sw(-1, self.m45_dir, self.m45_bar, arm_bars) and zone_ok_bear and (zs.kind == 'BRK' or zs.kind == 'OB') and trig_bear
        m45_strong = abs(self.m45_dir) == 2
        s46 = e46 and self.armed(1, self.m46_dir, self.m46_bar, arm_bars) and react_bull and (trig_bull or (imm_mode and harami))
        s46b = e46 and self.armed(-1, self.m46_dir, self.m46_bar, arm_bars) and react_bear and (trig_bear or (imm_mode and harami))
        s51 = e51 and bull_trend and self.last_dep_strong and bi - self.last_bos_bar <= 40 and zone_ok_bull and trig_bull
        s51b = e51 and bear_trend and self.last_dep_strong and bi - self.last_bos_bar <= 40 and zone_ok_bear and trig_bear
        w51 = e51 and (self.st_weak_bull or (self.st_bull_bos and not self.mv_strong))
        w51b = e51 and (self.st_weak_bear or (self.st_bear_bos and not self.mv_strong))
        s54 = e54 and self.m54_stage == 3 and zone_ok_bull and trig_bull and (abs(zb.bottom - self.m54_zb) <= atr or zb.dep_strong)
        s54b = e54 and self.m54_stage_b == 3 and zone_ok_bear and trig_bear and (abs(zs.top - self.m54_zs) <= atr or zs.dep_strong)
        if s54:
            self.m54_stage = 0
        if s54b:
            self.m54_stage_b = 0
        m39_rank_l = 43 if (self.choch_real and self.swept_low_bar >= 0 and self.qm_bull_at >= self.swept_low_bar and self.qm_bull_at - self.swept_low_bar <= 10) else 31
        m39_rank_s = 43 if (self.choch_real and self.swept_high_bar >= 0 and self.qm_bear_at >= self.swept_high_bar and self.qm_bear_at - self.swept_high_bar <= 10) else 31
        if s39:
            self.bid(True, s39 and arr_ok_bull, 'M39', m39_rank_l, 'Reclaimed block retest + bullish reversal' + (' (sweep → real CHoCH origin)' if m39_rank_l == 43 else ''))
        if s40:
            self.bid(True, True, 'M40', 21, 'Rejection block (wick zone) retest + reversal')
        if s41:
            self.bid(True, True, 'M41', 43, 'Sweep + FVG confluence: low swept, STRONG move left FVG, retrace reversal')
        if s42:
            self.bid(True, s42, 'M42', 43, 'High-probability demand: strong departure · 50% tapped · weak arrival' + (' · ★★ near-miss then sweep' if zb.near_swept else ''))
        if s45:
            self.bid(True, s45, 'M45', (4 if m45_strong else 3) * 10 + 3, 'Qualified sweep → ' + ('CHoCH (reversal, tier 4)' if m45_strong else 'BOS (continuation, tier 3)') + ' → breaker/OB retest')
        if s46:
            self.bid(True, True, 'M46', 32, 'CISD (early reversal) with reliability → zone reaction')
        if s51 and pb_ok_l:
            self.bid(True, True, 'M51', 32, 'Smart BOS: aggressive BOS with FVG → OB/support retest')
        if s54:
            self.bid(True, True, 'M54', 43, 'Smart S&D trap: demand reject → stop hunt → BOS up → retrace reversal')
        if s39b:
            self.bid(False, s39b and arr_ok_bear, 'M39', m39_rank_s, 'Reclaimed block retest + bearish reversal' + (' (sweep → real CHoCH origin)' if m39_rank_s == 43 else ''))
        if s40b:
            self.bid(False, True, 'M40', 21, 'Rejection block (wick zone) retest + reversal')
        if s41b:
            self.bid(False, True, 'M41', 43, 'Sweep + FVG confluence: high swept, STRONG move left FVG, retrace reversal')
        if s42b:
            self.bid(False, s42b, 'M42', 43, 'High-probability supply: strong departure · 50% tapped · weak arrival' + (' · ★★ near-miss then sweep' if zs.near_swept else ''))
        if s45b:
            self.bid(False, s45b, 'M45', (4 if m45_strong else 3) * 10 + 3, 'Qualified sweep → ' + ('CHoCH (reversal, tier 4)' if m45_strong else 'BOS (continuation, tier 3)') + ' → breaker/OB retest')
        if s46b:
            self.bid(False, True, 'M46', 32, 'CISD (early reversal) with reliability → zone reaction')
        if s51b and pb_ok_s:
            self.bid(False, True, 'M51', 32, 'Smart BOS (bearish): aggressive BOS with FVG → OB/resistance retest')
        if s54b:
            self.bid(False, True, 'M54', 43, 'Smart S&D trap (mirror): supply reject → stop hunt → BOS down → retrace')
        if warn_up == '':
            warn_up = 'M41 NO TRADE (no FVG)' if (w41 and self.m41_dir == 9) else ('⚠M51 weak BOS — consolidation risk' if w51 else '')
        if warn_dn == '':
            warn_dn = 'M41 NO TRADE (no FVG)' if (w41 and self.m41_dir == -9) else ('⚠M51 weak BOS — consolidation risk' if w51b else '')
        # ---------------------------------------------------- L6 SETUPS S–AB
        if self.st_swing_high and (not isnan(self.prev_high)) and abs(self.cur_high - self.prev_high) <= atr * dt_tol and self.cur_low_idx > self.prev_high_idx:
            self.dt_dir = -1
            self.dt_bar = bi
            self.dt_neck = self.cur_low
        if self.st_swing_low and (not isnan(self.prev_low)) and abs(self.cur_low - self.prev_low) <= atr * dt_tol and self.cur_high_idx > self.prev_low_idx:
            self.dt_dir = 1
            self.dt_bar = bi
            self.dt_neck = self.cur_high
        if self.dt_dir != 0 and bi - self.dt_bar > arm_bars * 2:
            self.dt_dir = 0
        if fake_break or (break_ago == 2 and (not isnan(self.break_lvl)) and ((self.break_dir == 1 and c < self.break_lvl) or (self.break_dir == -1 and c > self.break_lvl))):
            self.m62_dir = -self.break_dir
            self.m62_bar = bi
            self.m62_lvl = self.break_lvl
        tap_m62 = self.m62_dir != 0 and bi - self.m62_bar >= 1 and bi - self.m62_bar <= arm_bars and abs(c - self.m62_lvl) <= tlz
        if e64:
            self.draw_tl(tl_sup_valid, tl_res_valid, slope_s, slope_r, tl_s, tl_r, t)
        if self.ft_htf_sweep_dn and self.st_bull_choch:
            self.m68_dir = 1
            self.m68_bar = bi
        if self.ft_htf_sweep_up and self.st_bear_choch:
            self.m68_dir = -1
            self.m68_bar = bi
        if ifc_bull and (at_bull_zone or self.ft_swept_low):
            self.ifc_dir = 1
            self.ifc_bar = bi
            self.ifc_hi = h
            self.ifc_lo = l
        if ifc_bear and (at_bear_zone or self.ft_swept_high):
            self.ifc_dir = -1
            self.ifc_bar = bi
            self.ifc_hi = h
            self.ifc_lo = l
        if self.ifc_dir != 0 and (bi - self.ifc_bar > 10 or (self.ifc_dir == 1 and c < self.ifc_lo) or (self.ifc_dir == -1 and c > self.ifc_hi)):
            self.ifc_dir = 0
        if break_up or break_dn:
            self.m72_cnt = 0
            self.m72_wick = 0
            self.m72_dir = 1 if break_up else -1
        if self.m72_dir != 0 and break_ago >= 1 and not isnan(self.break_lvl):
            in_band = (c >= self.break_lvl and c <= self.break_lvl + atr * cons_max) if self.m72_dir == 1 else (c <= self.break_lvl and c >= self.break_lvl - atr * cons_max)
            if in_band:
                self.m72_cnt += 1
                self.m72_wick += 1 if ((self.m72_dir == 1 and up_r >= 0.4) or (self.m72_dir == -1 and dn_r >= 0.4)) else 0
            elif (self.m72_dir == 1 and c > self.break_lvl + atr * cons_max) or (self.m72_dir == -1 and c < self.break_lvl - atr * cons_max):
                self.m72_dir = 0
        consol_ok = self.m72_dir != 0 and self.m72_cnt >= cons_min and self.m72_wick * 2 >= self.m72_cnt
        s58b = e58 and self.dt_dir == -1 and (not isnan(self.dt_neck)) and c < self.dt_neck and c1 >= self.dt_neck
        s58 = e58 and self.dt_dir == 1 and (not isnan(self.dt_neck)) and c > self.dt_neck and c1 <= self.dt_neck
        s62 = e62 and tap_m62 and self.m62_dir == 1 and rev_bull
        s62b = e62 and tap_m62 and self.m62_dir == -1 and rev_bear
        s68 = e68 and self.armed(1, self.m68_dir, self.m68_bar, arm_bars) and react_bull and trig_bull
        s68b = e68 and self.armed(-1, self.m68_dir, self.m68_bar, arm_bars) and react_bear and trig_bear
        s69 = e69 and self.ifc_dir == 1 and bi - self.ifc_bar >= 1 and c > self.ifc_hi
        s69b = e69 and self.ifc_dir == -1 and bi - self.ifc_bar >= 1 and c < self.ifc_lo
        s70 = e70 and zone_ok_bull and zb.kind == 'QM' and trig_bull
        s70b = e70 and zone_ok_bear and zs.kind == 'QM' and trig_bear
        s72b = e72 and consol_ok and self.m72_dir == 1 and c < self.break_lvl and is_bear and body_r >= 0.6
        s72 = e72 and consol_ok and self.m72_dir == -1 and c > self.break_lvl and is_bull and body_r >= 0.6
        if s69 or s69b:
            self.ifc_dir = 0
        if s72 or s72b:
            self.m72_dir = 0
        if s58 or s58b:
            self.dt_dir = 0
        if s62 or s62b:
            self.m62_dir = 0
        s73 = e73 and zb.prop and self.ft_at_demand and zb.fifty and trig_bull
        s73b = e73 and zs.prop and self.ft_at_supply and zs.fifty and trig_bear
        if s58:
            self.bid(True, True, 'M58', 21, 'Double bottom: neckline broken on close')
        if s62:
            self.bid(True, True, 'M62', 21, 'Fakeout trap: break failed within 1–2 bars → level tap + reversal against the break')
        if s68:
            self.bid(True, True, 'M68', 43, 'HTF sweep of low + LTF CHoCH up → zone/FVG reaction → LONG')
        if s69:
            self.bid(True, True, 'M69', 21, 'IFC candle at zone: close above IFC high → BUY')
        if s70:
            self.bid(True, True, 'M70', 22, 'Quasimodo left-leg demand + bullish candle')
        if s72:
            self.bid(True, True, 'M72', 21, 'Operator trap (mirror): breakdown → consolidation under level → strong bullish close back above')
        if s73:
            self.bid(True, True, 'M73', 33, 'Propulsion Block: re-departed zone tapped at 50% + bullish reversal')
        if m74_up:
            self.bid(True, True, 'M74', m74_t * 10 + 2, m74_note)
        if s58b:
            self.bid(False, True, 'M58', 21, 'Double top: neckline broken on close')
        if s62b:
            self.bid(False, True, 'M62', 21, 'Fakeout trap: failed breakout → level tap + reversal SHORT')
        if s68b:
            self.bid(False, True, 'M68', 43, 'HTF sweep of high + LTF CHoCH down → zone/FVG reaction → SHORT')
        if s69b:
            self.bid(False, True, 'M69', 21, 'IFC candle at zone: close below IFC low → SELL')
        if s70b:
            self.bid(False, True, 'M70', 22, 'Quasimodo left-leg supply + bearish candle')
        if s72b:
            self.bid(False, True, 'M72', 21, 'Operator trap: breakout → consolidation above level → strong bearish close back below')
        if s73b:
            self.bid(False, True, 'M73', 33, 'Propulsion Block: re-departed zone tapped at 50% + bearish reversal')
        if m74_dn:
            self.bid(False, True, 'M74', m74_t * 10 + 2, m74_note)
        if dbg <= 4:
            self.eng_bi = bi
            self.eng_close = c
            if self.is_last_bar:
                self.live_draw(ext_bars, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min, ret_bars, m74_bars)
            return plot.Background(color.TRANSPARENT)
        # ---------------------------------------------------- L7 TRADE ENGINE
        sig_l = self.no_sig
        sig_s = self.no_sig
        rej_l = 0
        rej_s = 0
        cont_l = self.is_cont(self.bl_n)
        cont_s = self.is_cont(self.bs_n)
        pd_blk_l = pd_cont and ((pd_in and (not self.ft_pd_beyond) and self.ft_pd_pct > pd_deep) or ((not isnan(self.ft_htf_pd_pct)) and self.ft_htf_pd_pct > pd_deep and self.ft_in_premium))
        pd_blk_s = pd_cont and ((pd_in and (not self.ft_pd_beyond) and self.ft_pd_pct < 1.0 - pd_deep) or ((not isnan(self.ft_htf_pd_pct)) and self.ft_htf_pd_pct < 1.0 - pd_deep and self.ft_in_discount))
        htf_ctr_l = self.ft_htf_bias == 'BEAR'
        htf_ctr_s = self.ft_htf_bias == 'BULL'
        g_blk_l = self.ft_gate_up == 1 and cont_l and (htf_ctr_l or not ltf_pb)
        g_blk_s = self.ft_gate_dn == 1 and cont_s and (htf_ctr_s or not ltf_pb)
        if self.bl_n == '':
            rej_l = 1
        elif self.ft_gate_up == 0 or g_blk_l or (pd_blk_l and cont_l):
            rej_l = 2
        elif not self.ft_sb_sess_ok:
            rej_l = 3
        if rej_l == 0:
            is_m74_l = self.bl_n == 'M74'
            sig_l = self.f_sig(self.st_trend if is_m74_l else gate_tr, self.bl_n, int(self.bl_s / 10), self.bl_t, True, atr, entry_mode, sl_buf, max_sl, fixed_r, fixed_rm, min_rr, max_rr, rr_real, tp_path, entry_px, min_risk_t, min_risk_a, m74_x if is_m74_l else set_lo_l, m74_px if is_m74_l else math.nan, kl_min, sweep_ext_ok, ltf_pb, pd_on, pd_deep, ny_open_on, ssn_score, tick)
            if sig_l.name == '':
                rej_l = 4
            if self.ft_gate_up == 1:
                sig_l.score -= 1
                sig_l.note = sig_l.note + (' · ⚠vs HTF' if htf_ctr_l else ' · ⚠ LTF counter (pullback)')
            if is_m74_l:
                sig_l.score += (2 if self.ft_pd_pct > pd_deep else (1 if self.ft_pd_pct >= 0.5 else 0)) + (1 if (self.ft_gate_up == 1 and not htf_ctr_l) else 0) + (0 if isnan(m74_f) else 1)
            if not (zb.kind != '' or self.ft_at_bull_fvg or at_tl_sup):
                sig_l.note = sig_l.note + ' · INCOMPLETE (no POI)'
                sig_l.score -= 1
            if sig_l.score < min_score:
                if rej_l == 0:
                    rej_l = 5
                sig_l = self.no_sig
        if self.bs_n == '':
            rej_s = 1
        elif self.ft_gate_dn == 0 or g_blk_s or (pd_blk_s and cont_s):
            rej_s = 2
        elif not self.ft_sb_sess_ok:
            rej_s = 3
        if rej_s == 0:
            is_m74_s = self.bs_n == 'M74'
            sig_s = self.f_sig(self.st_trend if is_m74_s else gate_tr, self.bs_n, int(self.bs_s / 10), self.bs_t, False, atr, entry_mode, sl_buf, max_sl, fixed_r, fixed_rm, min_rr, max_rr, rr_real, tp_path, entry_px, min_risk_t, min_risk_a, m74_x if is_m74_s else set_hi_s, m74_px if is_m74_s else math.nan, kl_min, sweep_ext_ok, ltf_pb, pd_on, pd_deep, ny_open_on, ssn_score, tick)
            if sig_s.name == '':
                rej_s = 4
            if self.ft_gate_dn == 1:
                sig_s.score -= 1
                sig_s.note = sig_s.note + (' · ⚠vs HTF' if htf_ctr_s else ' · ⚠ LTF counter (pullback)')
            if is_m74_s:
                sig_s.score += (2 if self.ft_pd_pct < 1.0 - pd_deep else (1 if self.ft_pd_pct <= 0.5 else 0)) + (1 if (self.ft_gate_dn == 1 and not htf_ctr_s) else 0) + (0 if isnan(m74_f) else 1)
            if not (zs.kind != '' or self.ft_at_bear_fvg or at_tl_res):
                sig_s.note = sig_s.note + ' · INCOMPLETE (no POI)'
                sig_s.score -= 1
            if sig_s.score < min_score:
                if rej_s == 0:
                    rej_s = 5
                sig_s = self.no_sig
        # one signal at a time
        ok_l = sig_l.name != ''
        ok_s = sig_s.name != ''
        if ok_l and ok_s:
            if sig_l.score >= sig_s.score:
                sig_s = self.no_sig
                ok_s = False
                rej_s = 6
            else:
                sig_l = self.no_sig
                ok_l = False
                rej_l = 6
        gap_ok = bi - self.sig_bar >= sig_gap
        if ok_l and (not gap_ok) and not (self.sig_dir == -1 and sig_l.score >= self.sig_score + 2):
            sig_l = self.no_sig
            ok_l = False
            rej_l = 7
        if ok_s and (not gap_ok) and not (self.sig_dir == 1 and sig_s.score >= self.sig_score + 2):
            sig_s = self.no_sig
            ok_s = False
            rej_s = 7
        ident_l = self.f_ident(sig_l) if ok_l else ''
        ident_s = self.f_ident(sig_s) if ok_s else ''
        ident_expired = bi - self.last_ident_bar >= id_bars
        if ok_l and (not ident_expired) and ident_l == self.last_ident:
            sig_l = self.no_sig
            ok_l = False
            rej_l = 8
        if ok_s and (not ident_expired) and ident_s == self.last_ident:
            sig_s = self.no_sig
            ok_s = False
            rej_s = 8
        # W1 · RETRACE / M74 limits
        ret_mode = entry_px == 'RETRACE'
        ret_now = ret_mode or (auto_ret > 0 and rng >= atr * auto_ret)
        mn_r = max(tick * float(min_risk_t), atr * min_risk_a)
        fill_l = False
        fill_s = False
        stp_l = False
        stp_s = False
        if self.ret_l_on:
            if bi - self.ret_bar_l > (m74_bars if self.ret_name_l == 'M74' else ret_bars):
                self.ret_l_on = False
                self.ret_done(self.ret_lb_l, '⌛ ' + self.ret_name_l + ' LONG expired')
            elif l <= self.ret_l.sl:
                stp_l = True
                self.ret_l_on = False
                self.ret_done(self.ret_lb_l, '⏳ ' + self.ret_name_l + ' LONG → ✖ SL')
            elif l <= self.ret_l.entry and not ok_l:
                self.ret_done(self.ret_lb_l, '⏳ ' + self.ret_name_l + ' LONG → filled')
                sig_l = self.ret_l
                ok_l = True
                fill_l = True
                rej_l = 0
                ident_l = self.f_ident(sig_l)
                self.ret_l_on = False
        if self.ret_s_on:
            if bi - self.ret_bar_s > (m74_bars if self.ret_name_s == 'M74' else ret_bars):
                self.ret_s_on = False
                self.ret_done(self.ret_lb_s, '⌛ ' + self.ret_name_s + ' SHORT expired')
            elif h >= self.ret_s.sl:
                stp_s = True
                self.ret_s_on = False
                self.ret_done(self.ret_lb_s, '⏳ ' + self.ret_name_s + ' SHORT → ✖ SL')
            elif h >= self.ret_s.entry and not ok_s:
                self.ret_done(self.ret_lb_s, '⏳ ' + self.ret_name_s + ' SHORT → filled')
                sig_s = self.ret_s
                ok_s = True
                fill_s = True
                rej_s = 0
                ident_s = self.f_ident(sig_s)
                self.ret_s_on = False
        if (ret_now or sig_l.name == 'M74') and ok_l and not fill_l:
            px_l = sig_l.entry if sig_l.name == 'M74' else (l if self.ft_new_bull_fvg else (set_lo_l + h) * 0.5)
            rk_l = px_l - sig_l.sl
            if (px_l < sig_l.entry or sig_l.name == 'M74') and rk_l > 0:
                rk_l = max(rk_l, mn_r)
                sig_l.sl = px_l - rk_l
                sig_l.entry = px_l
                sig_l.rr = abs(sig_l.tp1 - px_l) / rk_l
                sig_l.note = 'RETRACE limit · ' + sig_l.note
                if self.ret_l_on:
                    self.ret_done(self.ret_lb_l, '⌛ ' + self.ret_name_l + ' LONG replaced')
                self.ret_l = sig_l
                self.ret_l_on = True
                self.ret_bar_l = bi
                self.ret_px_l = px_l
                self.ret_name_l = sig_l.name
                sig_l = self.no_sig
                ok_l = False
                rej_l = 9
        if (ret_now or sig_s.name == 'M74') and ok_s and not fill_s:
            px_s = sig_s.entry if sig_s.name == 'M74' else (h if self.ft_new_bear_fvg else (set_hi_s + l) * 0.5)
            rk_s = sig_s.sl - px_s
            if (px_s > sig_s.entry or sig_s.name == 'M74') and rk_s > 0:
                rk_s = max(rk_s, mn_r)
                sig_s.sl = px_s + rk_s
                sig_s.entry = px_s
                sig_s.rr = abs(sig_s.tp1 - px_s) / rk_s
                sig_s.note = 'RETRACE limit · ' + sig_s.note
                if self.ret_s_on:
                    self.ret_done(self.ret_lb_s, '⌛ ' + self.ret_name_s + ' SHORT replaced')
                self.ret_s = sig_s
                self.ret_s_on = True
                self.ret_bar_s = bi
                self.ret_px_s = px_s
                self.ret_name_s = sig_s.name
                sig_s = self.no_sig
                ok_s = False
                rej_s = 9
        arm_l = rej_l == 9
        arm_s = rej_s == 9
        if ok_l or ok_s:
            self.sig_bar = bi
            self.sig_dir = 1 if ok_l else -1
            self.sig_score = sig_l.score if ok_l else sig_s.score
            self.last_ident = ident_l if ok_l else ident_s
            self.last_ident_bar = bi
        if trade_ln:
            if sig_l.name != '':
                self.trade_lines(sig_l, trade_bars, t)
            if sig_s.name != '':
                self.trade_lines(sig_s, trade_bars, t)
        # ---------------------------------------------------- labels
        has_l = sig_l.name != '' and sig_l.side == 1
        has_s = sig_s.name != '' and sig_s.side == -1
        any_lab = (d_sig and (has_l or has_s or arm_l or arm_s or stp_l or stp_s)) or tier_key or d_pb or d_candle or self.ft_evt_up != '' or self.ft_evt_dn != ''
        if any_lab:
            y_up = l - atr * lbl_off
            y_dn = h + atr * lbl_off
            sig_txt_l = ('▲▲ ' if sig_l.score >= grade_ap else ('▲ ' if sig_l.score >= grade_a else '· ')) + sig_l.name + ' ' + self.grade_txt(sig_l.score, grade_ap, grade_a) + str(sig_l.score) + ' · ' + f1(sig_l.rr) + 'R'
            sig_txt_s = ('▼▼ ' if sig_s.score >= grade_ap else ('▼ ' if sig_s.score >= grade_a else '· ')) + sig_s.name + ' ' + self.grade_txt(sig_s.score, grade_ap, grade_a) + str(sig_s.score) + ' · ' + f1(sig_s.rr) + 'R'
            choch_base = 'CHoCH' if self.choch_real else 'CHoCH?'
            choch_up_x = '✕' if (self.swept_low_bar >= 0 and bi - self.swept_low_bar <= 10) else ''
            choch_dn_x = '✕' if (self.swept_high_bar >= 0 and bi - self.swept_high_bar <= 10) else ''
            cisd_up_ok = self.st_cisd_bull and (d_cisd_all or pre_trend != 'BULLISH')
            cisd_dn_ok = self.st_cisd_bear and (d_cisd_all or pre_trend != 'BEARISH')
            cisd_hp = cisd_rel >= 2
            prec = self.prec
            # below-bar side (bull) — first writer wins, rank recorded
            xu_t = ''
            xu_c = self.c_bull
            xu_r = 0
            cands_up: list[str] = []
            cols_up: list[Color] = []
            rank_up: list[int] = []
            conds_up: list[bool] = []
            conds_up.append(d_sig and has_l)
            cands_up.append(sig_txt_l)
            cols_up.append(self.c_inv if self.ft_gate_up == 1 else self.c_bull)
            rank_up.append(1)
            conds_up.append(d_sig and arm_l)
            cands_up.append('⏳▲ ' + self.ret_name_l + ' LONG @ ' + px(self.ret_px_l, prec))
            cols_up.append(self.c_htf)
            rank_up.append(1)
            conds_up.append(d_sig and stp_l)
            cands_up.append('✖ ' + self.ret_name_l + ' filled → SL')
            cols_up.append(self.c_inv)
            rank_up.append(1)
            conds_up.append(d_struct and tier_key and self.st_bull_choch and (tier_all or self.choch_real))
            cands_up.append(choch_base + choch_up_x + '▲')
            cols_up.append(self.c_bull if self.choch_real else self.c_inv)
            rank_up.append(2)
            conds_up.append(d_struct and tier_key and (self.st_bull_bos or (d_weak_bos and self.st_weak_bull)))
            cands_up.append(('BOS▲ ·' + str(self.mv_fvg) + 'FVG') if self.ft_disp_bull else ('BOS▲ weak' if self.st_weak_bull else 'BOS▲'))
            cols_up.append(self.c_bull if self.ft_disp_bull else self.c_inv)
            rank_up.append(3)
            conds_up.append(d_struct and tier_all and self.st_int_bull)
            cands_up.append('iBOS▲')
            cols_up.append(self.c_inv)
            rank_up.append(3)
            conds_up.append(d_struct and (tier_all or (tier_key and cisd_hp)) and cisd_up_ok)
            cands_up.append('CISD▲' + ('★' if cisd_hp else ''))
            cols_up.append(self.c_bull)
            rank_up.append(4)
            conds_up.append(d_liq_evt and tier_key and self.ft_swept_low and (d_liq_all or self.ft_swept_major))
            cands_up.append('SWEEP✕ ' + self.ft_swept_base_lo)
            cols_up.append(self.c_bull)
            rank_up.append(5)
            ev_up = self.ft_evt_up
            ev_up_t = ev_up[0:1] == 'T'
            ev_up_b = ev_up[0:3] == 'BRK'
            conds_up.append(ev_up != '' and (d_ob_diag or not ev_up_t) and (tier_all or ev_up_b))
            cands_up.append(ev_up)
            cols_up.append(self.c_brk if ev_up_b else (self.c_inv if ev_up_t else self.c_bull))
            rank_up.append(6)
            conds_up.append(d_htf_evt and tier_key and new_htf and self.ft_htf_sweep_dn and self.h_bar_count == self.sweep_dn_at)
            cands_up.append('HTF SWEEP↓')
            cols_up.append(self.c_bull)
            rank_up.append(7)
            conds_up.append(d_htf_evt and tier_key and new_htf and self.ft_htf_manip_bull)
            cands_up.append('HTF MANIP▲')
            cols_up.append(self.c_bull)
            rank_up.append(8)
            conds_up.append(tier_all and warn_up != '')
            cands_up.append(warn_up)
            cols_up.append(self.c_inv)
            rank_up.append(9)
            conds_up.append(d_pb and self.st_pb_up)
            cands_up.append('PB✓')
            cols_up.append(self.c_bull)
            rank_up.append(11)
            conds_up.append(d_candle and (pin_bull or ifc_bull or manip_bull or engulf_bull))
            cands_up.append('IFC▲' if ifc_bull else ('MAN▲' if manip_bull else ('PIN▲' if pin_bull else 'ENG▲')))
            cols_up.append(self.c_bull)
            rank_up.append(12)
            xu_ret = False
            for q in range(len(conds_up)):
                if conds_up[q] and xu_t == '':
                    xu_t = cands_up[q]
                    xu_c = cols_up[q]
                    xu_r = rank_up[q]
                    xu_ret = q == 1
            # above-bar side (bear)
            xd_t = ''
            xd_c = self.c_bear
            xd_r = 0
            cands_dn: list[str] = []
            cols_dn: list[Color] = []
            rank_dn: list[int] = []
            conds_dn: list[bool] = []
            conds_dn.append(d_sig and has_s)
            cands_dn.append(sig_txt_s)
            cols_dn.append(self.c_inv if self.ft_gate_dn == 1 else self.c_bear)
            rank_dn.append(1)
            conds_dn.append(d_sig and arm_s)
            cands_dn.append('⏳▼ ' + self.ret_name_s + ' SHORT @ ' + px(self.ret_px_s, prec))
            cols_dn.append(self.c_htf)
            rank_dn.append(1)
            conds_dn.append(d_sig and stp_s)
            cands_dn.append('✖ ' + self.ret_name_s + ' filled → SL')
            cols_dn.append(self.c_inv)
            rank_dn.append(1)
            conds_dn.append(d_struct and tier_key and self.st_bear_choch and (tier_all or self.choch_real))
            cands_dn.append(choch_base + choch_dn_x + '▼')
            cols_dn.append(self.c_bear if self.choch_real else self.c_inv)
            rank_dn.append(2)
            conds_dn.append(d_struct and tier_key and (self.st_bear_bos or (d_weak_bos and self.st_weak_bear)))
            cands_dn.append(('BOS▼ ·' + str(self.mv_fvg) + 'FVG') if self.ft_disp_bear else ('BOS▼ weak' if self.st_weak_bear else 'BOS▼'))
            cols_dn.append(self.c_bear if self.ft_disp_bear else self.c_inv)
            rank_dn.append(3)
            conds_dn.append(d_struct and tier_all and self.st_int_bear)
            cands_dn.append('iBOS▼')
            cols_dn.append(self.c_inv)
            rank_dn.append(3)
            conds_dn.append(d_struct and (tier_all or (tier_key and cisd_hp)) and cisd_dn_ok)
            cands_dn.append('CISD▼' + ('★' if cisd_hp else ''))
            cols_dn.append(self.c_bear)
            rank_dn.append(4)
            conds_dn.append(d_liq_evt and tier_key and self.ft_swept_high and (d_liq_all or self.ft_swept_major))
            cands_dn.append('SWEEP✕ ' + self.ft_swept_base_hi)
            cols_dn.append(self.c_bear)
            rank_dn.append(5)
            conds_dn.append(d_struct and tier_all and (self.st_bull_sweep or self.st_bear_sweep) and (not self.ft_swept_high) and not self.ft_swept_low)
            cands_dn.append('✖SWEEP')
            cols_dn.append(self.c_inv)
            rank_dn.append(6)
            ev_dn = self.ft_evt_dn
            ev_dn_t = ev_dn[0:1] == 'T'
            ev_dn_b = ev_dn[0:3] == 'BRK'
            conds_dn.append(ev_dn != '' and (d_ob_diag or not ev_dn_t) and (tier_all or ev_dn_b))
            cands_dn.append(ev_dn)
            cols_dn.append(self.c_brk if ev_dn_b else (self.c_inv if ev_dn_t else self.c_bear))
            rank_dn.append(7)
            conds_dn.append(d_htf_evt and tier_key and new_htf and self.ft_htf_sweep_up and self.h_bar_count == self.sweep_up_at)
            cands_dn.append('HTF SWEEP↑')
            cols_dn.append(self.c_bear)
            rank_dn.append(8)
            conds_dn.append(d_htf_evt and tier_key and new_htf and self.ft_htf_manip_bear)
            cands_dn.append('HTF MANIP▼')
            cols_dn.append(self.c_bear)
            rank_dn.append(9)
            conds_dn.append(tier_all and warn_dn != '')
            cands_dn.append(warn_dn)
            cols_dn.append(self.c_inv)
            rank_dn.append(10)
            conds_dn.append(d_pb and self.st_pb_dn)
            cands_dn.append('PB✓')
            cols_dn.append(self.c_bear)
            rank_dn.append(12)
            conds_dn.append(d_candle and (pin_bear or ifc_bear or manip_bear or engulf_bear or star_bear))
            cands_dn.append('IFC▼' if ifc_bear else ('MAN▼' if manip_bear else ('SS' if star_bear else ('PIN▼' if pin_bear else 'ENG▼'))))
            cols_dn.append(self.c_bear)
            rank_dn.append(13)
            xd_ret = False
            for q2 in range(len(conds_dn)):
                if conds_dn[q2] and xd_t == '':
                    xd_t = cands_dn[q2]
                    xd_c = cols_dn[q2]
                    xd_r = rank_dn[q2]
                    xd_ret = q2 == 1
            stack_win = min_gap * 2
            pri_up = xu_r >= 1 and xu_r <= 5
            pri_dn = xd_r >= 1 and xd_r <= 5
            ap_l = has_l and sig_l.score >= grade_ap and (self.last_up < 0 or bi - self.last_up >= 2)
            ap_s = has_s and sig_s.score >= grade_ap and (self.last_dn < 0 or bi - self.last_dn >= 2)
            if xu_t != '' and (self.last_up < 0 or bi - self.last_up >= min_gap or ap_l or pri_up):
                if self.last_up >= 0 and bi - self.last_up <= stack_win:
                    self.up_stack = min(self.up_stack + 1, 4)
                else:
                    self.up_stack = max(self.up_stack - 1, 0)
                lid = self.add_label(True, y_up - atr * lbl_off * 2.0 * float(self.up_stack), xu_t, xu_c, filled, fill_t, max_labels, t)
                self.last_up = bi
                if xu_ret:
                    self.ret_lb_l = lid
            if xd_t != '' and (self.last_dn < 0 or bi - self.last_dn >= min_gap or ap_s or pri_dn):
                if self.last_dn >= 0 and bi - self.last_dn <= stack_win:
                    self.dn_stack = min(self.dn_stack + 1, 4)
                else:
                    self.dn_stack = max(self.dn_stack - 1, 0)
                lid2 = self.add_label(False, y_dn + atr * lbl_off * 2.0 * float(self.dn_stack), xd_t, xd_c, filled, fill_t, max_labels, t)
                self.last_dn = bi
                if xd_ret:
                    self.ret_lb_s = lid2
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
        self.sig_l = sig_l
        self.sig_s = sig_s
        self.has_l = has_l
        self.has_s = has_s
        self.eng_bi = bi
        self.eng_close = c
        if self.is_last_bar:
            self.live_draw(ext_bars, d_panel, d_legend, dash_pos, dash_w, dash_font, grade_ap, grade_a, pd_deep, entry_confirm, kl_min, ret_bars, m74_bars)
        return plot.Background(self.bg_col)

    # =========================================================================
    # small helpers
    # =========================================================================
    def en(self, b: bool, all_on: bool, all_off: bool) -> bool:
        if all_off:
            return False
        if all_on:
            return True
        return b

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

    def zs_copy(self, d: ZS, z: ZS) -> None:
        d.kind = z.kind
        d.touches = z.touches
        d.sweep_req = z.sweep_req
        d.fifty = z.fifty
        d.idm = z.idm
        d.hp = z.hp
        d.kl = z.kl
        d.flipped = z.flipped
        d.near_swept = z.near_swept
        d.dep_strong = z.dep_strong
        d.top = z.top
        d.bottom = z.bottom
        d.prop = z.prop
        d.arr = z.arr
        d.arr_mix = z.arr_mix
        d.pend = z.pend
        d.sw = z.sw

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

    def leg_fvg(self, is_long: bool, from_idx: int, pxv: float) -> float:
        best = math.nan
        for g in self.fvgs:
            if g.mitigated or g.is_bull != is_long or g.idx < from_idx:
                continue
            ce = (g.top + g.bottom) * 0.5
            if (is_long and ce < pxv and (isnan(best) or ce > best)) or ((not is_long) and ce > pxv and (isnan(best) or ce < best)):
                best = ce
        return best

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
    def bid(self, is_long: bool, cond: bool, name: str, sc: int, note: str) -> None:
        if is_long:
            if cond and sc > self.bl_s:
                self.bl_n = name
                self.bl_s = sc
                self.bl_t = note
        else:
            if cond and sc > self.bs_s:
                self.bs_n = name
                self.bs_s = sc
                self.bs_t = note

    def armed(self, dir_want: int, dir_have: int, at_bar: int, arm_bars: int) -> bool:
        return dir_have == dir_want and self.bar_index - at_bar >= 1 and self.bar_index - at_bar <= arm_bars

    def armed_sw(self, dir_want: int, dir_have: int, at_bar: int, arm_bars: int) -> bool:
        return (dir_have == dir_want or dir_have == dir_want * 2) and self.bar_index - at_bar >= 1 and self.bar_index - at_bar <= arm_bars

    def is_cont(self, n: str) -> bool:
        return n == 'M02' or n == 'M05' or n == 'M08' or n == 'M15' or n == 'M33' or n == 'M36' or n == 'M42' or n == 'M51' or n == 'M73'

    def grade_txt(self, sc: int, g_ap: int, g_a: int) -> str:
        if sc >= g_ap:
            return 'A+'
        if sc >= g_a:
            return 'A'
        return 'B'

    # =========================================================================
    # L7 trade engine
    # =========================================================================
    def nearest_opp(self, is_long: bool, pxv: float, min_dist: float, max_dist: float, kl_min: int, sweep_ext_ok: bool) -> float:
        best = math.nan
        for z in self.zones:
            if z.broken or z.bull == is_long:
                continue
            qual_z = (z.kl >= kl_min) if z.kind == 'SR' else (z.confirmed and not z.weak)
            if not qual_z:
                continue
            lvl = z.bottom if is_long else z.top
            dz = (lvl - pxv) if is_long else (pxv - lvl)
            closer = (lvl < best) if is_long else (lvl > best)
            if dz >= min_dist and dz <= max_dist and (isnan(best) or closer):
                best = lvl
        for g in self.fvgs:
            if g.mitigated or g.is_bull == is_long:
                continue
            lvl2 = g.bottom if is_long else g.top
            dg = (lvl2 - pxv) if is_long else (pxv - lvl2)
            closer2 = (lvl2 < best) if is_long else (lvl2 > best)
            if dg >= min_dist and dg <= max_dist and (isnan(best) or closer2):
                best = lvl2
        for L in self.lv:
            if L.done or L.is_high != is_long:
                continue
            qual_l = L.pooled or is_t3_kind(L.kind) or (sweep_ext_ok and L.ext)
            if not qual_l:
                continue
            dl = (L.price - pxv) if is_long else (pxv - L.price)
            closer3 = (L.price < best) if is_long else (L.price > best)
            if dl >= min_dist and dl <= max_dist and (isnan(best) or closer3):
                best = L.price
        return best

    def path_block(self, is_long: bool, pxv: float, tp: float, aV: float, kl_min: int) -> int:
        tol = aV * 0.10
        hit = 0
        for z in self.zones:
            if z.broken or z.bull == is_long:
                continue
            qual_z = (z.kl >= kl_min) if z.kind == 'SR' else (z.confirmed and not z.weak)
            lvl = z.bottom if is_long else z.top
            if qual_z and ((is_long and lvl > pxv + tol and lvl < tp - tol) or ((not is_long) and lvl < pxv - tol and lvl > tp + tol)):
                hit = 2
                break
        if hit == 0:
            for g in self.fvgs:
                if g.mitigated or g.is_bull == is_long:
                    continue
                lvl2 = g.bottom if is_long else g.top
                if (is_long and lvl2 > pxv + tol and lvl2 < tp - tol) or ((not is_long) and lvl2 < pxv - tol and lvl2 > tp + tol):
                    hit = 2
                    break
        if hit == 0:
            for L in self.lv:
                if L.done or L.is_high != is_long:
                    continue
                qual_l = L.pooled or is_t3_kind(L.kind)
                if qual_l and ((is_long and L.price > pxv + tol and L.price < tp - tol) or ((not is_long) and L.price < pxv - tol and L.price > tp + tol)):
                    hit = 1
                    break
        return hit

    def nearest_liq(self, is_long: bool, pxv: float) -> float:
        best = math.nan
        for L in self.lv:
            if L.done or L.is_high != is_long:
                continue
            if (is_long and L.price > pxv and (isnan(best) or L.price < best)) or ((not is_long) and L.price < pxv and (isnan(best) or L.price > best)):
                best = L.price
        return best

    def f_conf(self, trend_str: str, is_long: bool, ltf_pb: bool, pd_on: bool, pd_deep: float, ny_open_on: bool, ssn_score: bool) -> int:
        zz = self.ft_zb if is_long else self.ft_zs
        bias = self.ft_htf_bias
        c = self.close[0]
        sc = 1
        sc += 1 if ((is_long and bias == 'BULL') or ((not is_long) and bias == 'BEAR')) else 0
        sc += 1 if ((is_long and trend_str == 'BULLISH') or ((not is_long) and trend_str == 'BEARISH')) else 0
        pb_wv = ltf_pb and zz.kind != '' and ((is_long and bias == 'BULL' and self.ft_in_discount) or ((not is_long) and bias == 'BEAR' and self.ft_in_premium))
        sc -= 1 if ((not pb_wv) and ((is_long and trend_str == 'BEARISH') or ((not is_long) and trend_str == 'BULLISH'))) else 0
        poi_pts = (1 if (zz.dep_strong and zz.arr == 1) else 0) + (1 if (zz.kind != '' and zz.touches <= 1) else 0) + (1 if zz.kl >= 4 else 0) + (1 if (zz.kind != '' and ((is_long and self.ft_at_bull_fvg) or ((not is_long) and self.ft_at_bear_fvg))) else 0)
        sc += min(poi_pts, 2)
        sc += 1 if ((is_long and self.ft_bsl_above >= 2) or ((not is_long) and self.ft_ssl_below >= 2)) else 0
        sc += 1 if ((is_long and (self.ft_swept_low_q or zz.idm)) or ((not is_long) and (self.ft_swept_high_q or zz.idm)) or zz.sw == 2) else 0
        sc -= 2 if zz.arr == -1 else 0
        sc -= 2 if (zz.sweep_req and zz.sw == 0 and not ((is_long and self.ft_swept_low) or ((not is_long) and self.ft_swept_high))) else 0
        sc -= 1 if trend_str == 'RANGE' else 0
        sc += 1 if ((is_long and self.ft_in_htf_fvg_b) or ((not is_long) and self.ft_in_htf_fvg_s)) else 0
        hp = self.ft_htf_pd_pct
        sc += 1 if ((not isnan(hp)) and ((is_long and hp <= 0.5) or ((not is_long) and hp >= 0.5))) else 0
        loc_pts = 0
        if pd_on:
            pp = self.ft_pd_pct
            ote = (pp >= 0.21 and pp <= 0.38) if is_long else (pp >= 0.62 and pp <= 0.79)
            if ote and not self.ft_pd_beyond:
                loc_pts = 2
            elif (is_long and self.ft_in_discount) or ((not is_long) and self.ft_in_premium):
                loc_pts = 1
            elif (is_long and pp > pd_deep) or ((not is_long) and pp < 1.0 - pd_deep):
                loc_pts = -1
        if ny_open_on and (not isnan(self.ny_open)) and loc_pts == 0:
            loc_pts = 1 if ((is_long and c < self.ny_open) or ((not is_long) and c > self.ny_open)) else 0
        sc += loc_pts
        if ssn_score and not self.ssn_filt:
            sc += 1 if (self.ft_sess_name == 'London' or self.ft_sess_name == 'NY') else 0
        return sc

    def f_stop(self, is_long: bool, aV: float, buf_a: float, max_a: float, ep: float, x: float) -> float:
        buf = aV * buf_a
        xx = min(x, nz(self.ft_swept_ext_lo, x)) if is_long else max(x, nz(self.ft_swept_ext_hi, x))
        sl = math.nan
        zz = self.ft_zb if is_long else self.ft_zs
        if zz.kind != '':
            sl = (min(zz.bottom, xx) - buf) if is_long else (max(zz.top, xx) + buf)
        elif (is_long and self.ft_swept_low) or ((not is_long) and self.ft_swept_high):
            sl = (xx - buf) if is_long else (xx + buf)
        else:
            maj = self.major_low if is_long else self.major_high
            if (not isnan(maj)) and abs(ep - maj) <= aV * max_a:
                sl = (min(maj, xx) - buf) if is_long else (max(maj, xx) + buf)
            else:
                sl = (xx - buf) if is_long else (xx + buf)
        if (is_long and (sl >= ep or ep - sl > aV * max_a * 2)) or ((not is_long) and (sl <= ep or sl - ep > aV * max_a * 2)):
            sl = (min(xx, ep) - buf) if is_long else (max(xx, ep) + buf)
        return sl

    def f_sig(self, trend_str: str, name: str, tier: int, note: str, is_long: bool, aV: float, e_mode: str, sl_buf: float, max_sl: float, fixed_r: bool, fixed_rm: float, min_rr: float, max_rr: float, rr_real: bool, path_mode: str, e_px: str, min_risk_t: int, min_risk_a: float, x: float, lim: float, kl_min: int, sweep_ext_ok: bool, ltf_pb: bool, pd_on: bool, pd_deep: float, ny_open_on: bool, ssn_score: bool, tick: float) -> Sig:
        c = self.close[0]
        h = self.high[0]
        l = self.low[0]
        g = new_sig()
        g.name = name
        g.side = 1 if is_long else -1
        g.entry = c
        zz_e = self.ft_zb if is_long else self.ft_zs
        if e_px == 'ZONE EDGE' and zz_e.kind != '':
            g.entry = zz_e.top if is_long else zz_e.bottom
            g.note = 'LIMIT @ zone edge · '
        elif e_px == 'CANDLE 50%' or e_px == 'ZONE EDGE':
            g.entry = (h + l) * 0.5
            g.note = 'LIMIT @ candle 50% · '
        m10px = self.ft_swept_price_lo if is_long else self.ft_swept_price_hi
        if name == 'M10' and e_mode != 'IMMEDIATE' and not isnan(m10px):
            g.entry = m10px
            g.note = 'RETEST limit @ swept level · ' if e_mode == 'RETEST' else 'BOTH: immediate + retest limit @ level · '
        if not isnan(lim):
            g.entry = lim
            g.note = 'MSS → FVG limit · '
        g.sl = self.f_stop(is_long, aV, sl_buf, max_sl, g.entry, x)
        risk = abs(g.entry - g.sl)
        min_r = max(max(tick * float(min_risk_t), aV * min_risk_a), aV * 0.5 if risk <= 0 else 0.0)
        if risk < min_r:
            risk = min_r
            g.sl = (g.entry - risk) if is_long else (g.entry + risk)
        ok_rr = True
        if fixed_r:
            g.tp1 = (g.entry + fixed_rm * risk) if is_long else (g.entry - fixed_rm * risk)
            g.tp2 = (g.tp1 + risk) if is_long else (g.tp1 - risk)
            g.tp3 = (g.tp2 + risk) if is_long else (g.tp2 - risk)
            g.tgt = 'FIXED-R'
        else:
            need = risk * min_rr
            cap = risk * max_rr
            tp_a = self.nearest_opp(is_long, g.entry, need, 1.0e10, kl_min, sweep_ext_ok)
            if isnan(tp_a) and g.entry != c and name == 'M10':
                g.entry = c
                g.note = g.note + 'R:R fallback → IMMEDIATE entry · '
                g.sl = self.f_stop(is_long, aV, sl_buf, max_sl, g.entry, x)
                risk = abs(g.entry - g.sl)
                if risk <= 0:
                    risk = aV * 0.5
                    g.sl = (g.entry - risk) if is_long else (g.entry + risk)
                need = risk * min_rr
                cap = risk * max_rr
                tp_a = self.nearest_opp(is_long, g.entry, need, 1.0e10, kl_min, sweep_ext_ok)
            if isnan(tp_a):
                if rr_real:
                    ok_rr = False
                else:
                    tp_a = (g.entry + need) if is_long else (g.entry - need)
                    g.tgt = 'SYNTH'
            else:
                g.tgt = 'FAR' if abs(tp_a - g.entry) > cap else 'REAL'
            tp_f = tp_a
            tp_x = math.nan
            if g.tgt == 'FAR':
                tp_x = self.nearest_liq(is_long, (g.entry + need) if is_long else (g.entry - need))
            if (not isnan(tp_x)) and abs(tp_x - g.entry) <= cap:
                tp_a = tp_x
                g.tgt = 'LIQ'
            g.tp1 = tp_a
            tp_b = self.nearest_liq(is_long, g.entry if isnan(g.tp1) else g.tp1)
            if g.tgt == 'LIQ':
                g.tp2 = tp_f
            elif (not isnan(tp_b)) and ((is_long and tp_b >= g.tp1 + risk) or ((not is_long) and tp_b <= g.tp1 - risk)):
                g.tp2 = tp_b
            else:
                g.tp2 = (g.tp1 + risk) if is_long else (g.tp1 - risk)
            tp_c = self.nearest_liq(is_long, g.entry if isnan(g.tp2) else g.tp2)
            if (not isnan(tp_c)) and ((is_long and tp_c >= g.tp2 + risk) or ((not is_long) and tp_c <= g.tp2 - risk)):
                g.tp3 = tp_c
            else:
                g.tp3 = (g.tp2 + risk) if is_long else (g.tp2 - risk)
        g.rr = abs(g.tp1 - g.entry) / risk if (risk > 0 and not isnan(g.tp1)) else 0.0
        blk_raw = self.path_block(is_long, g.entry, g.tp1, aV, kl_min)
        blk = blk_raw if (path_mode != 'OFF' and not isnan(g.tp1)) else 0
        path_pen = 0
        if blk > 0:
            g.note = g.note + ('⚠ opposing zone/FVG between entry and TP1 · ' if blk == 2 else '⚠ liquidity pool between entry and TP1 · ')
            if path_mode == 'STRICT' and blk == 2:
                ok_rr = False
            else:
                path_pen = 1
        if isnan(g.sl) or isnan(g.tp1) or (is_long and (g.sl >= g.entry or g.tp1 <= g.entry)) or ((not is_long) and (g.sl <= g.entry or g.tp1 >= g.entry)) or ((not fixed_r) and g.rr < min_rr - 0.01):
            ok_rr = False
        g.score = tier * 2 + self.f_conf(trend_str, is_long, ltf_pb, pd_on, pd_deep, ny_open_on, ssn_score) - path_pen - (1 if g.tgt == 'FAR' else 0)
        g.note = g.note + note + ('' if g.tgt == 'REAL' else ' · ⚠ TP1 = ' + g.tgt)
        g.name = name if ok_rr else ''
        return g

    def f_ident(self, g: Sig) -> str:
        zz = self.ft_zb if g.side == 1 else self.ft_zs
        anc = (zz.top + zz.bottom) * 0.5 if zz.kind != '' else nz(self.ft_swept_price_lo if g.side == 1 else self.ft_swept_price_hi, 0.0)
        return g.name + ('L' if g.side == 1 else 'S') + zz.kind + px(anc, self.prec)

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

    def ret_done(self, lid: int, txt: str) -> None:
        # Pine f_retDone: grey + rename the ⏳ label (no-op if it was already FIFO-deleted)
        for k in range(len(self.lab_ids)):
            if self.lab_ids[k] == lid:
                lb = self.labs[k]
                lb.text = txt
                lb.bg_color = ca(self.c_inv, 40)
                if self.live:
                    self.chart.draw(lb)
                break

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

    def trade_lines(self, g: Sig, n_bars: int, t: float) -> None:
        t_end = t + float(n_bars) * self.tf_sec
        lns2: list[LineSegment] = []
        lns2.append(LineSegment(AbsolutePosition(t, g.entry), AbsolutePosition(t_end, g.entry), color=ca(self.c_htf, 10), line_style=line_style.SOLID, line_width=2))
        lns2.append(LineSegment(AbsolutePosition(t, g.sl), AbsolutePosition(t_end, g.sl), color=ca(self.c_bear, 20), line_style=line_style.DASHED, line_width=1))
        lns2.append(LineSegment(AbsolutePosition(t, g.tp1), AbsolutePosition(t_end, g.tp1), color=ca(self.c_bull, 30), line_style=line_style.DASHED, line_width=1))
        lns2.append(LineSegment(AbsolutePosition(t, g.tp2), AbsolutePosition(t_end, g.tp2), color=ca(self.c_bull, 55), line_style=line_style.DASHED, line_width=1))
        lns2.append(LineSegment(AbsolutePosition(t, g.tp3), AbsolutePosition(t_end, g.tp3), color=ca(self.c_bull, 75), line_style=line_style.DASHED, line_width=1))
        for ln in lns2:
            if self.live:
                self.chart.draw(ln)
            self.trade_lns.append(ln)
        while len(self.trade_lns) > 50:
            if self.live:
                self.chart.erase(self.trade_lns[0])
            self.trade_lns.pop(0)

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
