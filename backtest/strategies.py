"""The two strategies under test. Parameters are fixed here BEFORE looking at
any results; do not tune them against the full history.

Both take completed decision bars (15-minute, indexed by open time in New
York time) and return a list of `Signal`s. A signal only ever uses bars that
have already closed.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .engine import Signal


# --------------------------------------------------------------------------
# 1. Opening-range breakout (the "ORB scalper" video)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class OrbParams:
    range_start: str = "09:30"   # the 9:30-9:45 ET bar defines the range
    last_entry: str = "11:30"    # no new breakout entries after this bar
    flat_at: str = "15:55"       # close any open trade before the cash close
    target_r: float = 1.0        # target = this multiple of the risk


def orb_signals(bars: pd.DataFrame, p: OrbParams = OrbParams()) -> list[Signal]:
    """First 15m close outside the opening range -> enter at the next open,
    stop at the opposite side of the range. One trade per day."""
    out = []
    step = bars.index[1] - bars.index[0]
    for day, g in bars.groupby(bars.index.date):
        g = g.between_time(p.range_start, p.last_entry)
        if len(g) < 2 or g.index[0].strftime("%H:%M") != p.range_start:
            continue
        hi, lo = g["high"].iloc[0], g["low"].iloc[0]
        for t, close in g["close"].iloc[1:].items():
            side = 1 if close > hi else -1 if close < lo else 0
            if side:
                flat = pd.Timestamp(f"{day} {p.flat_at}", tz=bars.index.tz)
                out.append(Signal(t=t + step, side=side, stop=lo if side > 0 else hi,
                                  target_r=p.target_r, time_exit=flat, tag="orb"))
                break
    return out


# --------------------------------------------------------------------------
# 2. Failed breakout of a post-impulse range (the "Patrick Nill" video)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class FboParams:
    """The video does not disclose how the range is drawn, so this is our own
    explicit definition of "strong push, then a range with three touches"."""
    atr_len: int = 50            # bars used for average true range
    impulse_bars: int = 8        # the push must happen within this many bars
    impulse_atr: float = 4.0     # ... and cover at least this many ATRs
    pause_bars: int = 3          # push is over after this many bars without a new extreme
    max_height: float = 0.75     # range height may not exceed this share of the push
    min_bars: int = 20           # range must last at least this long (5 hours of 15m bars)
    max_bars: int = 150          # give up if no valid range by then
    touch_tol: float = 0.15      # a "touch" is within this share of the height from an edge
    touches: int = 3             # touches of one edge needed for a valid range
    armed_bars: int = 100        # how long a valid range stays tradable
    reclaim_bars: int = 3        # a break must close back inside within this many bars
    min_risk_atr: float = 0.10   # skip trades whose stop is closer than this many ATRs
    limit_bars: int = 4          # entry limit order lives this many bars
    target_r: float = 3.0        # target as a multiple of risk (video: at least 3)
    max_hold_hours: int = 48     # time stop


def _touch_count(extreme: np.ndarray, edge: float, tol: float, upper: bool) -> int:
    """Number of separate visits of `extreme` to within `tol` of `edge`."""
    near = (extreme >= edge - tol) if upper else (extreme <= edge + tol)
    return int(near[0]) + int(np.sum(near[1:] & ~near[:-1]))


def fbo_signals(bars: pd.DataFrame, p: FboParams = FboParams(), tick: float = 0.25) -> list[Signal]:
    h, l, c = (bars[k].to_numpy() for k in ("high", "low", "close"))
    prev_c = np.roll(c, 1)
    prev_c[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    atr = pd.Series(tr).rolling(p.atr_len).mean().to_numpy()
    idx = bars.index
    step = idx[1] - idx[0]

    out: list[Signal] = []
    state, i, n = "seek", p.atr_len + p.impulse_bars, len(bars)
    hi = lo = extreme = 0.0
    start = 0
    impulse = origin = peak = 0.0
    count = peak_i = direction = 0
    while i < n:
        if state == "seek":
            move = c[i] - c[i - p.impulse_bars]
            if abs(move) >= p.impulse_atr * atr[i]:
                direction = 1 if move > 0 else -1
                origin = c[i - p.impulse_bars]
                peak, peak_i, state = (h[i] if direction > 0 else l[i]), i, "push"
        elif state == "push":
            # the push is over once `pause_bars` bars pass without a new extreme
            new_peak = h[i] if direction > 0 else l[i]
            if (new_peak - peak) * direction > 0:
                peak, peak_i = new_peak, i
            elif i - peak_i >= p.pause_bars:
                impulse, start, state = abs(peak - origin), peak_i + 1, "build"
                continue  # evaluate this bar as part of the range
        elif state == "build":
            hi, lo = h[start:i + 1].max(), l[start:i + 1].min()
            length = i - start + 1
            if hi - lo > p.max_height * impulse or length > p.max_bars:
                state = "seek"
                continue  # re-examine this bar as a possible new impulse
            if length >= p.min_bars:
                tol = p.touch_tol * (hi - lo)
                top = _touch_count(h[start:i + 1], hi, tol, True)
                bot = _touch_count(l[start:i + 1], lo, tol, False)
                if max(top, bot) >= p.touches:
                    state, count = "armed", 0
        elif state == "armed":
            count += 1
            if c[i] < lo:
                state, extreme, count = "down", l[i], 0
            elif c[i] > hi:
                state, extreme, count = "up", h[i], 0
            elif count > p.armed_bars:
                state = "seek"
        else:  # "down" or "up": price closed outside; does it come back?
            side = 1 if state == "down" else -1
            edge = lo if side > 0 else hi
            count += 1
            extreme = min(extreme, l[i]) if side > 0 else max(extreme, h[i])
            if (c[i] - edge) * side >= 0:  # closed back inside: the breakout failed
                stop = extreme - side * tick
                if (edge - stop) * side >= p.min_risk_atr * atr[i]:
                    t = idx[i] + step
                    out.append(Signal(
                        t=t, side=side, kind="limit", price=edge, stop=stop,
                        target_r=p.target_r, expire=t + p.limit_bars * step,
                        time_exit=t + pd.Timedelta(hours=p.max_hold_hours),
                        tag="fbo_long" if side > 0 else "fbo_short"))
                state = "seek"
            elif count >= p.reclaim_bars:  # a real breakout; stand aside
                state = "seek"
        i += 1
    return out
