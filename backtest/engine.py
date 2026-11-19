"""Trade simulator with deliberately pessimistic fill rules.

Strategies emit `Signal`s from completed decision bars (e.g. 15-minute). The
simulator then walks the finest bars available (ideally 1-minute) to decide
what would have happened.

Pessimistic assumptions, all of which hurt results rather than help them:
  * if a bar touches both the stop and the target, the stop is taken;
  * a limit order only fills when price trades THROUGH it by one tick;
  * on the bar where a limit order fills, the stop can be hit but the target
    cannot;
  * market and stop fills pay slippage; a gap through the stop fills at the
    worse (gap) price;
  * commission is charged on both sides;
  * one position at a time: signals arriving while in a trade are skipped.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Instrument:
    """Defaults are Micro E-mini Nasdaq-100 (MNQ), one contract."""
    tick: float = 0.25
    point_value: float = 2.0       # dollars per index point
    commission_side: float = 0.75  # dollars per contract per side, incl. fees
    slip_ticks: float = 1.0        # ticks lost on each market/stop fill


@dataclass
class Signal:
    t: pd.Timestamp                 # when the order becomes active
    side: int                       # +1 long, -1 short
    stop: float
    kind: str = "market"            # "market" or "limit"
    price: float | None = None      # limit price
    target: float | None = None     # absolute target price, or ...
    target_r: float | None = None   # ... target as a multiple of actual risk
    expire: pd.Timestamp | None = None     # unfilled limit cancelled at this time
    time_exit: pd.Timestamp | None = None  # open trade closed at this time
    tag: str = ""


def simulate(path: pd.DataFrame, signals: list[Signal], inst: Instrument = Instrument()) -> pd.DataFrame:
    """Run `signals` against `path` bars. Returns one row per completed trade."""
    ts = path.index.as_unit("ns").asi8
    o, h, l, c = (path[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(ts)
    slip = inst.slip_ticks * inst.tick
    ns = lambda t: None if t is None else pd.Timestamp(t).value  # nanoseconds

    trades = []
    busy_until = -1  # index of the bar on which the last trade exited
    for s in sorted(signals, key=lambda x: x.t):
        i = int(np.searchsorted(ts, ns(s.t), "left"))
        if i >= n or i <= busy_until:
            continue
        d = s.side
        exp, tex = ns(s.expire), ns(s.time_exit)

        # ---- entry -------------------------------------------------------
        if s.kind == "market":
            entry, j, limit_bar = o[i] + d * slip, i, False
        else:
            entry = None
            j = i
            while j < n and (exp is None or ts[j] < exp):
                # cancel if the stop level trades before the limit can fill
                gapped_better = (o[j] - s.price) * d <= 0
                through = (l[j] <= s.price - inst.tick) if d > 0 else (h[j] >= s.price + inst.tick)
                if gapped_better:
                    entry = o[j]
                elif through:
                    entry = s.price
                if entry is not None:
                    break
                j += 1
            if entry is None:
                continue
            limit_bar = True
        risk = (entry - s.stop) * d
        if risk <= 0:
            continue
        target = s.target if s.target is not None else (
            entry + d * s.target_r * risk if s.target_r is not None else None)

        # ---- exit --------------------------------------------------------
        exit_px, reason, k = None, "", j
        while k < n:
            first = k == j
            if not first and tex is not None and ts[k] >= tex:
                exit_px, reason = o[k] - d * slip, "time"
                break
            if not first and (o[k] - s.stop) * d <= 0:           # gap through stop
                exit_px, reason = o[k] - d * slip, "stop"
                break
            adverse = l[k] if d > 0 else h[k]
            if (adverse - s.stop) * d <= 0:
                exit_px, reason = s.stop - d * slip, "stop"
                break
            if target is not None and not (first and limit_bar):
                if not first and (o[k] - target) * d >= 0:        # gap through target
                    exit_px, reason = o[k], "target"
                    break
                favourable = h[k] if d > 0 else l[k]
                if (favourable - target) * d >= 0:
                    exit_px, reason = target, "target"
                    break
            k += 1
        if exit_px is None:                                       # data ended
            k = n - 1
            exit_px, reason = c[k] - d * slip, "end"
        busy_until = k

        pts = (exit_px - entry) * d
        usd = pts * inst.point_value - 2 * inst.commission_side
        trades.append(dict(
            signal_time=s.t, entry_time=path.index[j], exit_time=path.index[k],
            side=d, entry=entry, stop=s.stop, target=target, exit=exit_px,
            reason=reason, risk_pts=risk, pnl_pts=pts, pnl_usd=usd,
            r=usd / (risk * inst.point_value), tag=s.tag))
    return pd.DataFrame(trades)
