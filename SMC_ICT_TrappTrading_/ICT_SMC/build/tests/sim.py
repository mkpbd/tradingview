"""
Reference simulation of the Tier A core, ported straight from SMC_ICT_Engine.pine.
It exercises the SEQUENCING of the state machine, not the Pine translation.
Order of work per bar mirrors the Pine file: Layer 1 -> Layer 2 -> Layer 3 -> cleanup.
"""

class Zone:
    def __init__(self, zid, kind, direction, top, bottom, created):
        self.id, self.kind, self.direction = zid, kind, direction
        self.top, self.bottom = top, bottom
        self.ce = (top + bottom) / 2
        self.createdBar = created
        self.state = "NEW"
        self.consumed = False
        self.touchCount = 0
        self.lastTouchBar = -10
        self.mitigationPct = 0.0

BUY_SIDE_KINDS   = ("BSL", "EQH", "PDH", "PWH")
NAMED_POOL_KINDS = ("EQH", "EQL", "PDH", "PDL", "PWH", "PWL")

ZONE_PRIORITY = {"UNICORN": 7, "HTF_FVG": 6, "FVG": 6, "OB": 5, "BPR": 5,
                 "BB": 4, "IFVG": 4, "MB": 3, "RB": 2, "SD": 1}

class Liq:
    def __init__(self, kind, price, created, strength=1, isBuySide=None):
        self.kind, self.price, self.createdBar = kind, price, created
        self.swept, self.sweptBar = False, 0
        self.strength = strength
        # Phase 52 - a level knows which side of the book it belongs to
        self.isBuySide = (kind in BUY_SIDE_KINDS) if isBuySide is None else isBuySide

class Setup:
    def __init__(self, direction):
        self.direction = direction
        self.reset()
    def reset(self):
        self.state = "IDLE"
        self.sweepLevel = 0.0; self.sweepBar = 0
        self.mssLevel = 0.0;   self.mssBar = 0
        self.poi = None;       self.poiBar = 0
        self.poiLeft = False
        self.entryPrice = self.slPrice = self.slInit = 0.0
        self.tp1 = self.rr = 0.0
        self.score = 0; self.entryBar = 0
        self.signalEmitted = False
        self.exitReason = ""
        # Phase 50 - evidence captured when it happens, graded later
        self.sweepKind = ""; self.sweepStrength = 1; self.sweepInKz = False
        self.dispMult = 0.0; self.mssConfirmed = False

class Engine:
    # defaults copied from the Pine inputs
    def __init__(self, htfBias="BULL", swingLen=2, intSwingLen=1, atr=1.0, atrMult=1.2,
                 bodyRatioMin=0.6, minGapMult=0.1, mssTimeout=10, mssValidBars=20,
                 poiTimeout=50, minRR=1.5, minScore=6, slBuf=0.2, requirePd=False,
                 requireHtf=True, inKz=True, inDiscount=True, tmOn=False,
                 tpMode="Liquidity", tp1R=1.0):
        self.p = dict(locals()); self.p.pop("self")
        self.bars = []
        self.swings = []; self.liq = []; self.zones = []
        self.lastSH = self.lastSL = None
        self.intHigh = self.intLow = None
        self.L = Setup("LONG"); self.S = Setup("SHORT")
        self.signals = []          # (bar, side, entry, sl, tp, rr, score)
        self.zoneCounter = 0

    # ---------- Layer 1 ----------
    def _pivots(self, i):
        n = self.p["swingLen"]
        if i - n < 0 or i - 2 * n < 0:
            return
        win = self.bars[i - 2 * n: i + 1]
        c = win[n]
        if c["h"] == max(b["h"] for b in win) and all(c["h"] > b["h"] for k, b in enumerate(win) if k != n):
            self.lastSH = c["h"]
            self.swings.append(("H", c["h"]))
            self.liq.append(Liq("BSL", c["h"], i - n))
        if c["l"] == min(b["l"] for b in win) and all(c["l"] < b["l"] for k, b in enumerate(win) if k != n):
            self.lastSL = c["l"]
            self.swings.append(("L", c["l"]))
            self.liq.append(Liq("SSL", c["l"], i - n))
        m = self.p["intSwingLen"]
        if i - 2 * m >= 0:
            w2 = self.bars[i - 2 * m: i + 1]
            c2 = w2[m]
            if all(c2["h"] > b["h"] for k, b in enumerate(w2) if k != m):
                self.intHigh = c2["h"]
            if all(c2["l"] < b["l"] for k, b in enumerate(w2) if k != m):
                self.intLow = c2["l"]

    # ---------- Layer 2 ----------
    def _events(self, i):
        b = self.bars[i]
        rng = max(b["h"] - b["l"], 1e-9)
        body = abs(b["c"] - b["o"])
        disp = body / rng >= self.p["bodyRatioMin"] and body >= self.p["atr"] * self.p["atrMult"]
        bullDisp = disp and b["c"] > b["o"]
        bearDisp = disp and b["c"] < b["o"]

        rejUp = (b["c"] - b["l"]) / rng > 0.5
        rejDn = (b["h"] - b["c"]) / rng > 0.5
        sslSwept = bslSwept = False
        sweptSsl = sweptBsl = None
        sweptSslKind = sweptBslKind = ""
        sweptSslStr = sweptBslStr = 1
        # Phase 52 - only a sell-side level feeds a long, only a buy-side level a short
        for lv in self.liq:
            if lv.swept:
                continue
            if (not lv.isBuySide) and lv.price < b["c"] and b["l"] < lv.price and rejUp:
                lv.swept, lv.sweptBar, sslSwept = True, i, True
                if sweptSsl is None or lv.price > sweptSsl:
                    sweptSsl, sweptSslKind, sweptSslStr = lv.price, lv.kind, lv.strength
            elif lv.isBuySide and lv.price > b["c"] and b["h"] > lv.price and rejDn:
                lv.swept, lv.sweptBar, bslSwept = True, i, True
                if sweptBsl is None or lv.price < sweptBsl:
                    sweptBsl, sweptBslKind, sweptBslStr = lv.price, lv.kind, lv.strength

        mssUp = bullDisp and self.intHigh is not None and b["c"] > self.intHigh
        mssDn = bearDisp and self.intLow is not None and b["c"] < self.intLow
        # Phase 54 - the pivot is retired in Layer 3 at the moment a setup confirms
        # its MSS against it, not here: it has to survive the DISPLACEMENT_CONFIRMED
        # bar that sits between the sweep and the MSS.
        dispMult = body / max(self.p["atr"], 1e-9)

        # FVG (middle candle must be the displacement)
        if i >= 2:
            p2 = self.bars[i - 2]
            prevDispBull = self._isDisp(i - 1) and self.bars[i - 1]["c"] > self.bars[i - 1]["o"]
            if b["l"] > p2["h"] and prevDispBull and (b["l"] - p2["h"]) >= self.p["atr"] * self.p["minGapMult"]:
                self.zoneCounter += 1
                self.zones.append(Zone(f"FVG_{self.zoneCounter}", "FVG", "BULL", b["l"], p2["h"], i))

        # zone lifecycle
        for z in self.zones:
            if z.state == "NEW" and i > z.createdBar:
                z.state = "ACTIVE"
            if z.state in ("ACTIVE", "TOUCHED", "MITIGATED"):
                zh = max(z.top - z.bottom, 1e-9)
                touching = b["l"] <= z.top and b["h"] >= z.bottom
                if touching:
                    if i - z.lastTouchBar > 1:
                        z.touchCount += 1
                    z.lastTouchBar = i
                    pen = (z.top - max(min(b["l"], z.top), z.bottom)) / zh if z.direction == "BULL" \
                        else (min(max(b["h"], z.bottom), z.top) - z.bottom) / zh
                    z.mitigationPct = max(z.mitigationPct, pen)
                    z.state = "MITIGATED" if z.mitigationPct >= 0.5 else "TOUCHED"
                killed = b["c"] < z.bottom if z.direction == "BULL" else b["c"] > z.top
                if killed:
                    z.state = "FILLED"
        return dict(bullDisp=bullDisp, bearDisp=bearDisp, sslSwept=sslSwept, bslSwept=bslSwept,
                    sweptSsl=sweptSsl, sweptBsl=sweptBsl, mssUp=mssUp, mssDn=mssDn,
                    sweptSslKind=sweptSslKind, sweptBslKind=sweptBslKind,
                    sweptSslStr=sweptSslStr, sweptBslStr=sweptBslStr,
                    dispMult=dispMult)

    def _isDisp(self, i):
        b = self.bars[i]
        rng = max(b["h"] - b["l"], 1e-9)
        body = abs(b["c"] - b["o"])
        return body / rng >= self.p["bodyRatioMin"] and body >= self.p["atr"] * self.p["atrMult"]

    def _nextLiqAbove(self, px):
        c = [lv.price for lv in self.liq if not lv.swept and lv.price > px]
        return min(c) if c else None

    def _latestZone(self, direction, px):
        """Phase 54 - a long retraces DOWN into its POI, so the zone must sit at or
        below price. Taking simply the newest zone handed longs zones sitting ABOVE
        price, which price can never retrace into: the setup then sat in POI_CREATED
        until poiTimeout killed it, losing the signal with nothing shown on screen.
        Among the reachable zones, prefer the better kind, then the nearer one."""
        best, bestRank, bestDist = None, -1, None
        for z in reversed(self.zones):
            if z.direction != direction or z.consumed or z.state not in ("NEW", "ACTIVE", "TOUCHED"):
                continue
            reachable = z.top <= px if direction == "BULL" else z.bottom >= px
            if not reachable:
                continue
            rank = ZONE_PRIORITY.get(z.kind, 0)
            dist = (px - z.top) if direction == "BULL" else (z.bottom - px)
            if rank > bestRank or (rank == bestRank and dist < bestDist):
                best, bestRank, bestDist = z, rank, dist
        return best

    def _scoreV1(self, st, direction):
        """Phase 50 - every point is earned. The old model added a flat 6 of 12,
        so the minimum-score input could not separate a good setup from a bad one."""
        isLong = direction == "LONG"
        sc = 0
        sc += 2 if self.p["htfBias"] == ("BULL" if isLong else "BEAR") else 0
        sc += 2 if st.mssConfirmed else 0
        sc += 1 if st.dispMult >= self.p["atrMult"] else 0
        sc += 1 if st.dispMult >= self.p["atrMult"] * 1.8 else 0
        sc += 1 if st.sweepStrength >= 2 else 0
        sc += 1 if st.sweepKind in NAMED_POOL_KINDS else 0
        if st.poi is not None:
            sc += 1
            sc += 1 if st.poi.kind in ("FVG", "IFVG", "OB", "BB", "UNICORN") else 0
        sc += 1 if (self.p["inDiscount"] if isLong else not self.p["inDiscount"]) else 0
        sc += 1 if self.p["inKz"] else 0
        sc -= 3 if self.p["htfBias"] == ("BEAR" if isLong else "BULL") else 0
        return max(sc, 0)

    def _tp1Long(self, entry, risk, tpLiq):
        """mirrors f_tpLadder rung 1: R-based mode ignores the liquidity pool"""
        if not self.p["tmOn"]:
            return tpLiq if tpLiq is not None else entry + risk * 2.0
        if self.p["tpMode"] == "R-based" or tpLiq is None:
            return entry + risk * self.p["tp1R"]
        return tpLiq

    # ---------- Layer 3 ----------
    def _machine(self, i, ev):
        b = self.bars[i]
        L = self.L
        ctxOk = (not self.p["requireHtf"] or self.p["htfBias"] == "BULL")
        trig = False
        if L.state == "IDLE":
            if ctxOk:
                L.state = "CONTEXT_FOUND"
        elif L.state == "CONTEXT_FOUND":
            if not ctxOk:
                L.state = "IDLE"
            elif ev["sslSwept"] and ev["sweptSsl"] is not None:
                L.state = "LIQUIDITY_SWEPT"
                L.sweepLevel = min(ev["sweptSsl"], b["l"]); L.sweepBar = i
                L.sweepKind = ev["sweptSslKind"]; L.sweepStrength = ev["sweptSslStr"]
                L.sweepInKz = self.p["inKz"]
        elif L.state == "LIQUIDITY_SWEPT":
            if i - L.sweepBar > self.p["mssTimeout"]:
                L.state = "INVALIDATED"
            elif ev["bullDisp"] and i > L.sweepBar:
                L.state = "DISPLACEMENT_CONFIRMED"; L.dispMult = ev["dispMult"]
        elif L.state == "DISPLACEMENT_CONFIRMED":
            if i - L.sweepBar > self.p["mssTimeout"]:
                L.state = "INVALIDATED"
            elif ev["mssUp"]:
                L.state = "MSS_CONFIRMED"; L.mssLevel = self.intHigh; L.mssBar = i
                L.mssConfirmed = True
                self.intHigh = None      # spent: the next MSS needs a fresh pivot
        elif L.state == "MSS_CONFIRMED":
            if i - L.mssBar > self.p["mssValidBars"]:
                L.state = "INVALIDATED"
            else:
                cand = self._latestZone("BULL", b["c"])
                if cand is not None and cand.createdBar >= L.sweepBar:
                    L.state = "POI_CREATED"; L.poi = cand; L.poiBar = i
        elif L.state == "POI_CREATED":
            if L.poi is None or i - L.poiBar > self.p["poiTimeout"] or L.poi.state in ("FILLED", "INVALID"):
                L.state = "INVALIDATED"
            else:
                touching = b["l"] <= L.poi.top and b["h"] >= L.poi.bottom
                if not touching:
                    L.poiLeft = True
                elif L.poiLeft:
                    L.state = "RETRACE_WAIT"
        elif L.state == "RETRACE_WAIT":
            if L.poi is None or L.poi.state in ("FILLED", "INVALID") or i - L.poiBar > self.p["poiTimeout"]:
                L.state = "INVALIDATED"
            else:
                entry = b["c"]
                sl = L.sweepLevel - self.p["atr"] * self.p["slBuf"]
                risk = max(entry - sl, 1e-9)
                tpl = self._nextLiqAbove(entry)
                # Phase 51 - RR must grade the target the trade actually takes, not a
                # liquidity pool the R-based ladder is going to ignore
                tp = self._tp1Long(entry, risk, tpl)
                rr = (tp - entry) / risk
                sc = self._scoreV1(L, "LONG")
                if rr >= self.p["minRR"] and sc >= self.p["minScore"] and entry > sl:
                    L.entryPrice, L.slPrice, L.slInit = entry, sl, sl
                    L.tp1, L.rr, L.score = tp, rr, sc
                    L.state = "ENTRY_TRIGGERED"
                    trig = True
        elif L.state == "TRADE_ACTIVE":
            if b["l"] <= L.slPrice or b["h"] >= L.tp1:
                L.exitReason = "SL" if b["l"] <= L.slPrice else "TP1"
                L.state = "INVALIDATED"

        if trig and not L.signalEmitted:
            L.signalEmitted = True; L.entryBar = i; L.state = "TRADE_ACTIVE"
            if L.poi is not None:
                L.poi.consumed = True
            self.signals.append((i, "LONG", L.entryPrice, L.slPrice, L.tp1, round(L.rr, 2), L.score))

        if L.state == "INVALIDATED":
            L.reset()

    def step(self, o, h, l, c):
        i = len(self.bars)
        self.bars.append(dict(o=o, h=h, l=l, c=c))
        self._pivots(i)
        ev = self._events(i)
        self._machine(i, ev)
        return ev


# =========================== Phase 16 tests ===========================
def bar(o, h, l, c):
    return (o, h, l, c)

def flat(n, px, w=0.3):
    return [bar(px, px + w, px - w, px) for _ in range(n)]

def run(seq, **kw):
    e = Engine(**kw)
    for b in seq:
        e.step(*b)
    return e

def scenario_valid_long(touches_after=0, tp_level=None, rr_ok=True):
    """sweep of an SSL -> displacement -> MSS -> FVG -> leave -> return."""
    seq = []
    seq += flat(6, 100)                       # build structure
    seq += [bar(100, 100.4, 97.0, 100.2)]     # dip makes a swing low at 97
    seq += flat(6, 100)                       # confirm the pivot
    seq += [bar(100, 100.3, 96.5, 100.1)]     # SWEEP: wick under 97, close back above
    seq += [bar(100.1, 103.5, 100.0, 103.4)]  # DISPLACEMENT up (body 3.3 > atr*1.2)
    seq += [bar(103.4, 106.9, 103.3, 106.8)]  # second displacement -> MSS + leaves an FVG
    seq += [bar(106.8, 107.2, 105.5, 106.0)]  # price walks away from the gap (stays above it)
    seq += flat(2, 106.0)                     # still outside
    seq += [bar(106, 106.2, 103.6, 104.2)]    # RETURN into the newest FVG -> entry
    for _ in range(touches_after):
        seq += [bar(104.2, 104.6, 103.7, 104.3)]
    return seq

def t1_single_long():
    e = run(scenario_valid_long())
    return len([s for s in e.signals if s[1] == "LONG"]), e

def t4_sweep_without_displacement():
    seq = flat(6, 100) + [bar(100, 100.4, 97.0, 100.2)] + flat(6, 100)
    seq += [bar(100, 100.3, 96.5, 100.1)]     # sweep
    seq += flat(15, 100.1)                    # no displacement, ever
    e = run(seq)
    return len(e.signals), e

def t5_rr_too_small():
    # a liquidity level just above the entry caps RR below 1.5
    e = Engine()
    seq = scenario_valid_long()
    for b in seq[:-1]:
        e.step(*b)
    e.liq.append(Liq("BSL", 101.5, len(e.bars)))   # target only ~0.6 away
    e.step(*seq[-1])
    return len(e.signals), e

def t6_five_touches_one_signal():
    e = run(scenario_valid_long(touches_after=5))
    return len(e.signals), e

def t_no_instant_entry():
    """regression: without leaving the POI there must be no signal."""
    seq = flat(6, 100) + [bar(100, 100.4, 97.0, 100.2)] + flat(6, 100)
    seq += [bar(100, 100.3, 96.5, 100.1)]
    seq += [bar(100.1, 103.5, 100.0, 103.4)]
    seq += [bar(103.4, 106.9, 103.3, 106.8)]   # FVG created here
    seq += [bar(106.8, 107.0, 103.6, 104.0)]   # price never leaves - sits straight back in the gap
    seq += flat(3, 104.0, 0.2)
    e = run(seq)
    return len(e.signals), e

def t_touch_count():
    e = run(scenario_valid_long(touches_after=5))
    z = [z for z in e.zones if z.kind == "FVG"]
    return (max((x.touchCount for x in z), default=0)), e

tests = [
    ("T1  valid long sequence -> exactly 1 LONG", t1_single_long, lambda v: v == 1),
    ("T4  sweep, no displacement -> 0 signals",   t4_sweep_without_displacement, lambda v: v == 0),
    ("T5  RR below minRR -> 0 signals",           t5_rr_too_small, lambda v: v == 0),
    ("T6  5 touches after entry -> still 1",      t6_five_touches_one_signal, lambda v: v == 1),
    ("REG no departure from POI -> 0 signals",    t_no_instant_entry, lambda v: v == 0),
    ("REG touchCount counts touches not bars",    t_touch_count, lambda v: v <= 3),
]

fails = 0
for name, fn, ok in tests:
    val, eng = fn()
    good = ok(val)
    fails += 0 if good else 1
    print(("PASS " if good else "FAIL ") + name + f"   -> {val}")
    if not good:
        print("      signals:", eng.signals)
        print("      L state:", eng.L.state, "zones:", [(z.kind, z.state, z.touchCount) for z in eng.zones])
print("\n", "all passed" if fails == 0 else f"{fails} FAILED")
