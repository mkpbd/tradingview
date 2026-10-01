# Generates the strategy twin from the indicator, so the DETECTION code is
# identical by construction. Re-run after every change to the indicator.
import os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, 'liqudity_trap_trading.txt')
DST = os.path.join(HERE, 'liqudity_trap_strategy.txt')

s = open(SRC, encoding='utf-8').read()

old_decl = ('indicator("Liquidity + S/D + Price Action [MTF] v3.4", "LQ-SD-PA v3.4", overlay = true,\n'
            '     max_boxes_count = 500, max_lines_count = 500, max_labels_count = 500)')
new_decl = (
    '// \u2550\u2550\u2550\u2550\u2550 STRATEGY TWIN \u2014 GENERATED FILE, DO NOT EDIT BY HAND \u2550\u2550\u2550\u2550\u2550\n'
    '// Produced from `liqudity_trap_trading.txt` by scripts/mktwin.py. The only\n'
    '// differences are this declaration and MODULE 19S at the end of the file, so\n'
    '// the Strategy Tester measures the SAME signals the chart tool prints.\n'
    '// Re-generate after every change to the indicator \u2014 never patch this file.\n'
    '//\n'
    '// Purpose (FIX-F9 / OP-21): `minScore`, `minRR`, `maxRiskAtr`, `rrMult`, the\n'
    '// symbol profiles and `fastShift` are currently OPINIONS. This twin is how\n'
    '// they become measurements. Calibration protocol: REVIEW_AND_PLAN_v3.3.1.md.\n'
    '// The tester is not the truth either \u2014 one tracked trade at a time, no\n'
    '// intrabar order, and a pessimistic same-bar stop rule mean the numbers are\n'
    '// a RANKING of settings, not an expectancy you can bank.\n'
    'strategy("LQ-SD-PA v3.4 STRATEGY TWIN", "LQ-SD-PA v3.4 TWIN", overlay = true,\n'
    '     max_boxes_count = 500, max_lines_count = 500, max_labels_count = 500,\n'
    '     process_orders_on_close = true, calc_on_every_tick = false,\n'
    '     default_qty_type = strategy.fixed, default_qty_value = 1,\n'
    '     initial_capital = 10000, currency = currency.NONE,\n'
    '     commission_type = strategy.commission.percent, commission_value = 0.0)')

assert s.count(old_decl) == 1, 'indicator() declaration not found \u2014 was the version bumped?'
s = s.replace(old_decl, new_decl, 1)

tail = '''

// \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550 MODULE 19S
// BROKER HAND-OFF \u2014 the ONLY code in this file that the indicator does not have.
// It places no orders of its own: it mirrors MODULE 19's tracked trade, which is
// the same population the dashboard counters describe. What that means:
//   \u00b7 one position at a time, like the tracker;
//   \u00b7 entry at the signal bar's CLOSE (`process_orders_on_close`), because the
//     indicator commits on the closed bar \u2014 an engine / non-SB machine signal
//     already deferred itself to the next open inside MODULE 19, so its
//     `trdEntry` IS that open;
//   \u00b7 fixed-fractional size from the distance to the structural stop;
//   \u00b7 50% at TP1, the rest at TP2 (TP3 when the trade carries a runner);
//   \u00b7 `trdSL` is re-issued every bar, so break-even and the trail are honoured;
//   \u00b7 a flat tracker with a position still open = the indicator closed it for a
//     non-price reason (time stop, window close, opposing structure) \u2014 flatten.
// \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
grpST = "Strategy twin"
stRiskPct = input.float(1.0, "Risk per trade (% of equity)", step = 0.25, minval = 0.05, group = grpST,
     tooltip = "Position size = (equity \u00d7 this) / distance to the structural stop. Sizing does not change WHICH trades fire.")
stRunner  = input.bool(true, "Let the runner aim at TP3 when the trade has one", group = grpST,
     tooltip = "SB trades and, with `nonSbTp3` on, ordinary ones. OFF books everything at TP2.")

stNewTrade = confirmed and trdDir != 0 and nz(trdDir[1], 0) == 0
stRunTP3   = stRunner and (trdIsSb or nonSbTp3)

if stNewTrade and not na(trdEntry) and not na(trdSL)
    float stRisk = math.abs(trdEntry - trdSL)
    float stQty  = stRisk > 0 ? (strategy.equity * stRiskPct / 100) / stRisk : na
    if not na(stQty) and stQty > 0
        strategy.entry(trdDir == 1 ? "L" : "S", trdDir == 1 ? strategy.long : strategy.short, qty = stQty)

// exits re-issued every bar so the moved stop is always the live one
if strategy.position_size > 0
    strategy.exit("L tp1", "L", qty_percent = 50, limit = trdTP1, stop = trdSL)
    strategy.exit("L tp2", "L", limit = stRunTP3 ? trdTP3 : trdTP2, stop = trdSL)
if strategy.position_size < 0
    strategy.exit("S tp1", "S", qty_percent = 50, limit = trdTP1, stop = trdSL)
    strategy.exit("S tp2", "S", limit = stRunTP3 ? trdTP3 : trdTP2, stop = trdSL)

// the indicator flattened for a reason the broker emulator cannot see
if confirmed and strategy.position_size != 0 and trdDir == 0 and nz(trdDir[1], 0) != 0
    strategy.close_all("tracker flat")
'''
s = s.rstrip('\n') + '\n' + tail
open(DST, 'w', encoding='utf-8').write(s)
print('wrote', DST, len(s.split(chr(10))), 'lines')
