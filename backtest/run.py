"""Run the backtests.

    python -m backtest.run --data path/to/bars.csv [--strategy both] [--split 0.7]

`--data` should be 1-minute bars if possible (coarser bars work but make
intrabar stop/target ordering less accurate). Decisions are always taken on
15-minute bars.
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

from .data import bar_minutes, load_bars, resample
from .engine import Instrument, simulate
from .report import summarize
from .strategies import fbo_signals, orb_signals


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--src-tz", default="UTC", help="timezone of naive timestamps in the file")
    ap.add_argument("--strategy", choices=["orb", "fbo", "both"], default="both")
    ap.add_argument("--split", type=float, default=0.7,
                    help="share of the history treated as in-sample; the rest is held out")
    ap.add_argument("--point-value", type=float, default=2.0)
    ap.add_argument("--tick", type=float, default=0.25)
    ap.add_argument("--commission", type=float, default=0.75, help="dollars per side")
    ap.add_argument("--slip-ticks", type=float, default=1.0)
    ap.add_argument("--out", default="backtest_out")
    a = ap.parse_args()

    path = load_bars(a.data, a.src_tz)
    step = bar_minutes(path)
    if step > 15:
        raise SystemExit(f"Bars are {step:.0f} minutes; need 15-minute or finer.")
    bars = path if step == 15 else resample(path, "15min")
    inst = Instrument(a.tick, a.point_value, a.commission, a.slip_ticks)
    split = path.index[0] + (path.index[-1] - path.index[0]) * a.split

    print(f"Data: {path.index[0]} -> {path.index[-1]}, {len(path):,} bars of {step:.0f} min")
    if step > 1:
        print("WARNING: not 1-minute data; intrabar fills are approximate.")
    print(f"Hold-out starts {split.date()}. Costs: ${a.commission}/side, {a.slip_ticks} tick slippage.\n")

    os.makedirs(a.out, exist_ok=True)
    pd.set_option("display.width", 200)
    runs = {"orb": ("Opening-range breakout", orb_signals),
            "fbo": ("Failed breakout of range", lambda b: fbo_signals(b, tick=a.tick))}
    for key, (name, make) in runs.items():
        if a.strategy not in (key, "both"):
            continue
        signals = make(bars)
        trades = simulate(path, signals, inst)
        trades.to_csv(os.path.join(a.out, f"{key}_trades.csv"), index=False)
        print(f"=== {name}: {len(signals)} signals, {len(trades)} trades ===")
        print(summarize(trades, split).to_string(), "\n")


if __name__ == "__main__":
    main()
