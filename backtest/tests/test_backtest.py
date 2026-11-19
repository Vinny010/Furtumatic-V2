"""Hand-built bar sequences with known correct outcomes."""
import numpy as np
import pandas as pd

from backtest.engine import Instrument, Signal, simulate
from backtest.report import stats
from backtest.strategies import FboParams, OrbParams, fbo_signals, orb_signals

NY = "America/New_York"
FREE = Instrument(tick=0.25, point_value=2.0, commission_side=0.0, slip_ticks=0.0)


def bars(rows, start="2024-01-03 09:30", freq="1min"):
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz=NY)
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx).assign(volume=1.0)


def one(path, sig, inst=FREE):
    t = simulate(path, [sig], inst)
    assert len(t) == 1
    return t.iloc[0]


def test_market_long_hits_target():
    p = bars([(100, 101, 99.5, 100.5), (100.5, 103, 100, 102.5)])
    t = one(p, Signal(t=p.index[0], side=1, stop=98, target_r=1.0))
    assert (t.entry, t.exit, t.reason) == (100, 102, "target") and t.r == 1.0


def test_bar_touching_stop_and_target_counts_as_stop():
    p = bars([(100, 103, 97, 100)])
    t = one(p, Signal(t=p.index[0], side=1, stop=98, target=102))
    assert t.reason == "stop" and t.exit == 98


def test_short_mirror():
    p = bars([(100, 100.5, 99, 99.5), (99.5, 100, 97, 97.5)])
    t = one(p, Signal(t=p.index[0], side=-1, stop=102, target_r=1.0))
    assert (t.exit, t.reason, t.pnl_pts) == (98, "target", 2)


def test_gap_through_stop_fills_at_gap_price():
    p = bars([(100, 101, 99.5, 100), (95, 96, 94, 95)])
    t = one(p, Signal(t=p.index[0], side=1, stop=98, target=110))
    assert t.exit == 95 and t.reason == "stop"


def test_costs_and_slippage():
    p = bars([(100, 101, 99.5, 100.5), (100.5, 103, 100, 102.5)])
    inst = Instrument(tick=0.25, point_value=2.0, commission_side=0.75, slip_ticks=1)
    t = one(p, Signal(t=p.index[0], side=1, stop=98, target=102), inst)
    assert t.entry == 100.25                      # paid one tick on entry
    assert abs(t.pnl_usd - (1.75 * 2 - 1.5)) < 1e-9  # target is a limit: no slip


def test_limit_needs_trade_through():
    p = bars([(101, 101.5, 100, 101), (101, 101.5, 99.75, 101), (101, 104, 100.5, 103)])
    t = one(p, Signal(t=p.index[0], side=1, kind="limit", price=100, stop=99, target=103))
    assert t.entry_time == p.index[1]             # a mere touch at 100 did not fill
    assert t.exit_time == p.index[2] and t.reason == "target"


def test_limit_fill_bar_cannot_take_target_but_can_stop():
    p = bars([(101, 104, 99.75, 103), (103, 103.5, 102, 103)])
    t = simulate(p, [Signal(t=p.index[0], side=1, kind="limit", price=100, stop=99, target=103)], FREE).iloc[0]
    assert t.exit_time == p.index[1]              # target only credited on a later bar
    p2 = bars([(101, 101, 98.5, 99)])
    t2 = one(p2, Signal(t=p2.index[0], side=1, kind="limit", price=100, stop=99, target=103))
    assert t2.reason == "stop"


def test_limit_expires_unfilled():
    p = bars([(101, 102, 100.5, 101)] * 5)
    sig = Signal(t=p.index[0], side=1, kind="limit", price=100, stop=99, target=103, expire=p.index[3])
    assert simulate(p, [sig], FREE).empty


def test_time_exit_and_no_overlap():
    p = bars([(100, 100.5, 99.5, 100)] * 6)
    a = Signal(t=p.index[0], side=1, stop=90, target=110, time_exit=p.index[3])
    b = Signal(t=p.index[1], side=1, stop=90, target=110)   # arrives while a is open
    t = simulate(p, [a, b], FREE)
    assert len(t) == 1 and t.iloc[0].reason == "time" and t.iloc[0].exit_time == p.index[3]


def test_stats():
    t = pd.DataFrame({"pnl_usd": [10.0, -5.0, -5.0, 20.0], "r": [1, -0.5, -0.5, 2]})
    s = stats(t)
    assert s["win_rate_%"] == 50.0 and s["profit_factor"] == 3.0
    assert s["max_drawdown_$"] == 10.0 and s["max_losing_streak"] == 2


def test_orb_long_signal():
    rows = [(100, 101, 99, 100.5),     # 09:30 range 99-101
            (100.5, 100.9, 100, 100.4),  # inside
            (100.4, 102, 100.3, 101.5),  # closes above -> long
            (101.5, 103, 101, 102.5)]
    b = bars(rows, freq="15min")
    s = orb_signals(b, OrbParams())
    assert len(s) == 1 and s[0].side == 1 and s[0].stop == 99
    assert s[0].t == b.index[3]        # acts on the bar AFTER the signal bar


def test_orb_no_signal_without_opening_bar():
    b = bars([(100, 101, 99, 100.5)] * 4, start="2024-01-03 10:00", freq="15min")
    assert orb_signals(b) == []


def _fbo_bars(fail=True):
    """Quiet market, sharp push up, a range 109-111 with repeated touches of
    both edges, a close below the range, then (optionally) a close back in."""
    rows = [(100, 100.3, 99.7, 100)] * 30
    rows += [(100 + i * 1.25, 101.5 + i * 1.25, 100 + i * 1.25, 101.25 + i * 1.25) for i in range(8)]  # push to 110
    cycle = [(110, 111, 110, 110.8), (110.8, 110.9, 110, 110.1),
             (110.1, 110.2, 109, 109.2), (109.2, 110, 109.1, 110)]
    rows += cycle * 6                                 # 24 range bars
    rows += [(110, 110.1, 108.2, 108.5)]              # closes below 109
    rows += [(108.5, 109.6, 108.4, 109.5)] if fail else [(108.5, 108.6, 107, 107.2)] * 4
    rows += [(109.5, 109.8, 108.7, 109.6), (109.6, 113, 109.5, 112.8)]
    return bars(rows, start="2024-01-03 00:00", freq="15min")


SMALL = FboParams(atr_len=10, impulse_bars=8, impulse_atr=4.0, min_bars=20)


def test_fbo_long_after_failed_breakdown():
    b = _fbo_bars(fail=True)
    s = fbo_signals(b, SMALL)
    assert len(s) == 1
    sig = s[0]
    assert sig.side == 1 and sig.kind == "limit" and sig.price == 109
    assert sig.stop == 108.2 - 0.25                   # one tick under the fake-out low
    t = simulate(b, s, FREE)
    assert len(t) == 1 and t.iloc[0].entry == 109 and t.iloc[0].reason == "target"
    assert abs(t.iloc[0].r - 3.0) < 1e-9


def test_fbo_ignores_genuine_breakdown():
    assert fbo_signals(_fbo_bars(fail=False), SMALL) == []


def test_fbo_uses_no_future_bars():
    """Signals found on a truncated history must not change when more data arrives."""
    b = _fbo_bars(fail=True)
    full = fbo_signals(b, SMALL)
    cut = fbo_signals(b.iloc[:-1], SMALL)
    assert [(s.t, s.price, s.stop) for s in cut] == [(s.t, s.price, s.stop) for s in full]


def test_mt5_export_is_read_in_new_york_time(tmp_path):
    from backtest.data import load_bars
    f = tmp_path / "US100_M1.csv"
    f.write_text("<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
                 "2024.01.03\t16:30:00\t100.0\t101.0\t99.0\t100.5\t50\t0\t12\n"
                 "2024.01.03\t16:31:00\t100.5\t101.5\t100.0\t101.0\t40\t0\t12\n")
    b = load_bars(str(f), src_tz="Europe/Athens")   # typical GMT+2/+3 broker server time
    assert b.index[0].strftime("%Y-%m-%d %H:%M") == "2024-01-03 09:30"
    assert b["close"].tolist() == [100.5, 101.0] and b["volume"].tolist() == [50.0, 40.0]
