"""Load intraday price bars and resample them.

All bars are indexed by their OPEN time, timezone-aware in America/New_York.
"""
from __future__ import annotations

import pandas as pd

NY = "America/New_York"
COLS = ["open", "high", "low", "close", "volume"]
TIME_NAMES = ("time", "timestamp", "datetime", "date", "gmt time", "local time")


def load_bars(path: str, src_tz: str = "UTC") -> pd.DataFrame:
    """Read a CSV of OHLC(V) bars.

    Understands:
      * generic CSVs with a header (time/open/high/low/close[/volume]), where
        time is ISO text or unix seconds (TradingView exports look like this);
      * histdata.com "generic ASCII" files (no header, ';' separated,
        `YYYYMMDD HHMMSS` in fixed EST with no daylight saving);
      * MetaTrader 5 bar exports (`<DATE> <TIME> <OPEN> ...`), whose times are
        in the broker's server timezone: pass it as `src_tz`.

    `src_tz` is the timezone of naive timestamps in a generic CSV.
    """
    with open(path) as f:
        first = f.readline()

    if ";" in first and first[:8].isdigit():
        df = pd.read_csv(path, sep=";", header=None, names=["time"] + COLS)
        t = pd.to_datetime(df["time"], format="%Y%m%d %H%M%S")
        # histdata uses EST without DST, i.e. a fixed UTC-5 offset
        idx = pd.DatetimeIndex(t).tz_localize("Etc/GMT+5").tz_convert(NY)
    elif first.startswith("<DATE>"):
        # MetaTrader 5 export: tab separated, times in the broker's server time
        df = pd.read_csv(path, sep="\t")
        df.columns = [c.strip("<>").lower() for c in df.columns]
        t = pd.to_datetime(df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M:%S")
        idx = pd.DatetimeIndex(t).tz_localize(src_tz, ambiguous="NaT", nonexistent="NaT").tz_convert(NY)
        df["volume"] = df["tickvol"]
        df = df[idx.notna()]
        idx = idx[idx.notna()]
    else:
        df = pd.read_csv(path)
        df.columns = [c.strip().lower() for c in df.columns]
        tcol = next((c for c in df.columns if c in TIME_NAMES), df.columns[0])
        raw = df[tcol]
        if pd.api.types.is_numeric_dtype(raw):
            unit = "ms" if raw.iloc[0] > 1e11 else "s"
            idx = pd.DatetimeIndex(pd.to_datetime(raw, unit=unit, utc=True))
        else:
            idx = pd.DatetimeIndex(pd.to_datetime(raw))
            if idx.tz is None:
                idx = idx.tz_localize(src_tz)
        idx = idx.tz_convert(NY)

    if "volume" not in df.columns:
        df["volume"] = 0.0
    out = df[COLS].astype(float).set_axis(idx)
    out.index.name = "time"
    out = out[~out.index.duplicated()].sort_index()
    return out.dropna(subset=["open", "high", "low", "close"])


def resample(bars: pd.DataFrame, rule: str = "15min") -> pd.DataFrame:
    """Aggregate finer bars into `rule` bars (labelled by open time)."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = bars.resample(rule, label="left", closed="left").agg(agg)
    return out.dropna(subset=["open"])


def bar_minutes(bars: pd.DataFrame) -> float:
    """Typical bar length in minutes."""
    return float(bars.index.to_series().diff().dt.total_seconds().median() / 60)
