"""Summary statistics for a table of trades."""
from __future__ import annotations

import numpy as np
import pandas as pd


def stats(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"trades": 0}
    usd, r = trades["pnl_usd"], trades["r"]
    wins, losses = usd[usd > 0], usd[usd <= 0]
    equity = usd.cumsum()
    drawdown = (equity.cummax().clip(lower=0) - equity).max()
    # longest run of consecutive losing trades
    streak = longest = 0
    for x in usd:
        streak = streak + 1 if x <= 0 else 0
        longest = max(longest, streak)
    return {
        "trades": len(trades),
        "win_rate_%": round(100 * len(wins) / len(trades), 1),
        "avg_win_$": round(wins.mean(), 2) if len(wins) else 0.0,
        "avg_loss_$": round(losses.mean(), 2) if len(losses) else 0.0,
        "profit_factor": round(wins.sum() / -losses.sum(), 2) if losses.sum() < 0 else np.inf,
        "avg_R": round(r.mean(), 3),
        "net_$": round(usd.sum(), 2),
        "max_drawdown_$": round(drawdown, 2),
        "max_losing_streak": longest,
    }


def summarize(trades: pd.DataFrame, split: pd.Timestamp | None = None) -> pd.DataFrame:
    """Rows: all / in-sample / out-of-sample / long / short / each year."""
    if trades.empty:
        return pd.DataFrame([stats(trades)], index=["all"])
    rows = {"all": trades}
    if split is not None:
        rows["in-sample (before split)"] = trades[trades["entry_time"] < split]
        rows["OUT-OF-SAMPLE (after split)"] = trades[trades["entry_time"] >= split]
    rows["long only"] = trades[trades["side"] > 0]
    rows["short only"] = trades[trades["side"] < 0]
    for year, g in trades.groupby(trades["entry_time"].dt.year):
        rows[str(year)] = g
    return pd.DataFrame({k: stats(v) for k, v in rows.items()}).T
