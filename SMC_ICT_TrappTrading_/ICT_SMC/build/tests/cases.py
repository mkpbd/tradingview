"""Phase 16 acceptance cases driven by the reference simulation in sim.py."""
import importlib.util, io, contextlib

import os
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sim", os.path.join(HERE, "sim.py"))
sim = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(sim)

bar = sim.bar
flat = sim.flat


def valid_long(touch_after=0, target=112.0, deep_retrace=False, never_leave=False):
    """SSL sweep -> displacement -> MSS -> FVG -> price leaves -> price returns."""
    seq = []
    seq += flat(6, 100)                        # consolidation
    seq += [bar(100, 100.4, 99.0, 100.0)]      # dip -> swing low at 99.0
    seq += flat(6, 100)                        # pivot confirms
    seq += [bar(100, 100.3, 98.8, 100.0)]      # SWEEP of 99.0, closes back inside
    seq += [bar(100.0, 102.6, 99.9, 102.5)]    # displacement + MSS
    seq += [bar(102.5, 105.2, 102.4, 105.1)]   # second leg -> FVG 100.3 .. 102.4
    if never_leave:
        seq += [bar(105.1, 105.2, 102.2, 102.6)]   # straight back in, never left
        seq += flat(3, 102.6, 0.2)
        return seq
    seq += [bar(105.1, 106.0, 104.5, 105.5)]   # walks away from the gap (POI is picked here)
    # the leg keeps running, so the target pool sits far above the entry
    seq += [bar(105.5, 108.0, 105.3, 107.8)]
    seq += [bar(107.8, 111.0, 107.6, 110.8)]
    seq += [bar(110.8, 115.0, 110.6, 114.8)]   # peak - becomes the BSL target
    seq += [bar(114.8, 114.9, 112.0, 112.4)]
    if deep_retrace:
        seq += [bar(105.5, 105.6, 99.5, 99.8)]
    else:
        seq += [bar(105.5, 105.6, 102.2, 102.6)]   # RETURN into the FVG -> entry
    for _ in range(touch_after):
        seq += [bar(102.6, 103.0, 102.3, 102.7)]
    return seq


def run(seq, seed_target=112.0, **kw):
    e = sim.Engine(**kw)
    if seed_target is not None:
        e.liq.append(sim.Liq("PDH", seed_target, 0))   # a real previous-day high above
    for b in seq:
        e.step(*b)
    return e


def t1():
    # entry is evaluated on the bar AFTER price re-enters the POI, so allow one
    e = run(valid_long(touch_after=1))
    return len(e.signals), e

def t4():
    seq = flat(6, 100) + [bar(100, 100.4, 99.0, 100.0)] + flat(6, 100)
    seq += [bar(100, 100.3, 98.8, 100.0)]      # sweep
    seq += flat(15, 100.0, 0.2)                # never any displacement
    e = run(seq)
    return len(e.signals), e

def t5():
    e = run(valid_long(), seed_target=103.0)   # target so close RR < 1.5
    return len(e.signals), e

def t6():
    e = run(valid_long(touch_after=5))
    return len(e.signals), e

def t_reg_no_departure():
    e = run(valid_long(never_leave=True))
    return len(e.signals), e

def t_reg_touch_count():
    e = run(valid_long(touch_after=5))
    return max((z.touchCount for z in e.zones), default=0), e

def t_timeout():
    """sweep then 12 quiet bars: past mssTimeout the setup must be dead."""
    seq = flat(6, 100) + [bar(100, 100.4, 99.0, 100.0)] + flat(6, 100)
    seq += [bar(100, 100.3, 98.8, 100.0)]
    seq += flat(12, 100.0, 0.2)
    seq += [bar(100.0, 102.6, 99.9, 102.5)]    # displacement arrives TOO LATE
    seq += [bar(102.5, 105.2, 102.4, 105.1)]
    seq += [bar(105.1, 106.0, 104.5, 105.5)]
    seq += flat(2, 105.5, 0.2)
    seq += [bar(105.5, 105.6, 102.2, 102.6)]
    e = run(seq)
    return len(e.signals), e

def t_sl_below_sweep():
    e = run(valid_long(touch_after=1))
    if not e.signals:
        return None, e
    _, _, entry, sl, tp, rr, sc = e.signals[0]
    return (sl < 98.8 and entry > sl and tp > entry and rr >= 1.5), e


# ===================== Phase 50..56 regression cases =====================

def t_score_discriminates():
    """Phase 50: the score must separate a good setup from a poor one.

    Before the rebuild, score v1 added a flat 6 of 12 and score v2 handed out
    liq=2, mom=2 and stc=2 as constants, so these two runs scored the same and the
    minimum-score input decided nothing."""
    strong = run(valid_long(touch_after=1), minScore=0, inKz=True,  htfBias="BULL")
    weak   = run(valid_long(touch_after=1), minScore=0, inKz=False, htfBias="NEUTRAL",
                 requireHtf=False, inDiscount=False)
    if not strong.signals or not weak.signals:
        return None, strong
    return (strong.signals[0][6], weak.signals[0][6]), strong


def t_buyside_level_cannot_arm_a_long():
    """Phase 52: a buy-side pool sitting below price is not sell-side liquidity.

    The sweep test used to look only at position relative to close, so a PDH price
    had already traded through was consumed as an SSL sweep and armed a long."""
    e = sim.Engine()
    e.liq.append(sim.Liq("PDH", 99.0, 0))          # buy-side pool, now below price
    e.step(100.0, 100.3, 99.7, 100.0)
    ev = e.step(100.0, 100.2, 98.0, 100.0)         # wick under it, close back above
    return ev["sslSwept"], e


def t_sellside_level_still_arms_a_long():
    """control for the case above: a genuine SSL must still pass through the door."""
    e = sim.Engine()
    e.liq.append(sim.Liq("SSL", 99.0, 0))
    e.step(100.0, 100.3, 99.7, 100.0)
    ev = e.step(100.0, 100.2, 98.0, 100.0)
    return ev["sslSwept"], e


def t_poi_must_be_reachable():
    """Phase 54: a long retraces DOWN into its POI, so a bull zone above price is
    unreachable and must never be selected - it used to be, whenever it was newest,
    and the setup then died silently on poiTimeout."""
    e = sim.Engine()
    e.zones.append(sim.Zone("Z_LOW",   "FVG", "BULL",  99.0,  98.0, 0))
    e.zones.append(sim.Zone("Z_ABOVE", "FVG", "BULL", 120.0, 118.0, 0))   # newest
    pick = e._latestZone("BULL", 100.0)
    return (pick.id if pick else None), e


def t_poi_prefers_better_kind():
    """among reachable zones, priority beats recency."""
    e = sim.Engine()
    e.zones.append(sim.Zone("Z_FVG", "FVG", "BULL", 99.0, 98.0, 0))
    e.zones.append(sim.Zone("Z_SD",  "SD",  "BULL", 99.5, 99.2, 1))       # newer, weaker
    pick = e._latestZone("BULL", 100.0)
    return (pick.id if pick else None), e


def t_mss_pivot_is_spent():
    """Phase 54: the internal pivot is retired once a setup confirms its MSS against
    it, so the next MSS needs fresh structure instead of re-breaking a dead level."""
    e = sim.Engine()
    e.bars.append(dict(o=100.0, h=102.0, l=99.5, c=101.5))
    e.intHigh = 100.0
    e.L.state = "DISPLACEMENT_CONFIRMED"
    e.L.sweepBar = 0
    e.L.sweepLevel = 99.0
    ev = dict(bullDisp=True, bearDisp=False, sslSwept=False, bslSwept=False,
              sweptSsl=None, sweptBsl=None, mssUp=True, mssDn=False,
              sweptSslKind="", sweptBslKind="", sweptSslStr=1, sweptBslStr=1,
              dispMult=2.0)
    e._machine(0, ev)
    return (e.L.state == "MSS_CONFIRMED" and e.intHigh is None), e


def t_mss_survives_the_displacement_bar():
    """guard against over-correcting the case above: retiring the pivot as soon as
    mssUp is true (rather than when a setup uses it) starves the state machine,
    because DISPLACEMENT_CONFIRMED sits between the sweep and the MSS."""
    e = run(valid_long(touch_after=1))
    return len(e.signals), e


def t_rr_grades_the_real_tp1():
    """Phase 51: with R-based trade management, TP1 is 1.0R. Measuring RR against a
    far liquidity pool let that setup clear a 1.5R filter and then take a 1.0R exit."""
    e = run(valid_long(touch_after=1), tmOn=True, tpMode="R-based", tp1R=1.0)
    return len(e.signals), e


def t_rr_passes_when_tp1_really_is_big_enough():
    """control: the same setup with TP1 at 2R must still trade."""
    e = run(valid_long(touch_after=1), tmOn=True, tpMode="R-based", tp1R=2.0)
    return len(e.signals), e


EXTRA_CASES = [
    ("P50  score separates strong from weak setup", t_score_discriminates,
     lambda v: v is not None and v[0] > v[1]),
    ("P52  buy-side pool below price -> no SSL sweep", t_buyside_level_cannot_arm_a_long,
     lambda v: v is False),
    ("P52  genuine SSL still sweeps", t_sellside_level_still_arms_a_long,
     lambda v: v is True),
    ("P54  unreachable POI above price is skipped", t_poi_must_be_reachable,
     lambda v: v == "Z_LOW"),
    ("P54  reachable POI picked by priority", t_poi_prefers_better_kind,
     lambda v: v == "Z_FVG"),
    ("P54  MSS retires the internal pivot", t_mss_pivot_is_spent,
     lambda v: v is True),
    ("P54  MSS still fires after the disp bar", t_mss_survives_the_displacement_bar,
     lambda v: v == 1),
    ("P51  R-based TP1 below minRR -> 0", t_rr_grades_the_real_tp1,
     lambda v: v == 0),
    ("P51  R-based TP1 above minRR -> 1", t_rr_passes_when_tp1_really_is_big_enough,
     lambda v: v == 1),
]

CASES = [
    ("T1   valid sequence -> exactly 1 LONG",        t1,                 lambda v: v == 1),
    ("T4   sweep without displacement -> 0",         t4,                 lambda v: v == 0),
    ("T5   RR below minRR -> 0",                     t5,                 lambda v: v == 0),
    ("T6   5 touches after entry -> still 1",        t6,                 lambda v: v == 1),
    ("REG  no departure from POI -> 0",              t_reg_no_departure, lambda v: v == 0),
    ("REG  touchCount counts touches, not bars",     t_reg_touch_count,  lambda v: v <= 3),
    ("T_TO displacement after mssTimeout -> 0",      t_timeout,          lambda v: v == 0),
    ("T12  SL sits below the sweep, RR >= 1.5",      t_sl_below_sweep,   lambda v: v is True),
]

CASES += EXTRA_CASES

fails = 0
for name, fn, ok in CASES:
    val, eng = fn()
    good = ok(val)
    fails += 0 if good else 1
    print(("PASS  " if good else "FAIL  ") + name + f"   -> {val}")
    if not good:
        print("       signals:", eng.signals)
        print("       state:", eng.L.state,
              "zones:", [(z.kind, round(z.top, 2), round(z.bottom, 2), z.state, z.touchCount) for z in eng.zones])
print()
print("all passed" if fails == 0 else f"{fails} FAILED")
if fails == 0:
    e = run(valid_long(touch_after=1))
    print("sample signal (bar, side, entry, sl, tp, rr, score):", e.signals[0])
