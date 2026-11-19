# Strategy backtests

An honest test of two intraday strategies taken from trading videos, on Nasdaq-100
futures, one micro contract (MNQ) at a time. This folder is independent of the
FUR token files in the rest of the repository.

## The strategies

| Key | Idea | Rules (fixed in `strategies.py` before any results were seen) |
|---|---|---|
| `orb` | Opening-range breakout | The 9:30-9:45 ET bar sets the range. The first 15-minute close outside it (up to 11:30) is entered at the next open. Stop at the opposite side of the range, target 1x the risk, flat by 15:55. One trade a day. |
| `fbo` | Failed breakout of a range | A strong push (at least 4 ATR within 8 bars), then a range no taller than 75% of the push, lasting 20+ bars with three touches of one edge. If price closes outside the range and closes back inside within 3 bars, place a limit order at the range edge. Stop one tick beyond the fake-out extreme, target 3x the risk, 48-hour time stop. |

The source video for `fbo` says its range-drawing rules are not disclosed, so the
range definition here is our own.

## Fill assumptions

All chosen to hurt results, not help them (details in `engine.py`):

- a bar that touches both stop and target counts as a loss;
- limit orders fill only when price trades through them by a tick;
- market and stop fills lose one tick; gaps through a stop fill at the gap price;
- $0.75 commission per side;
- one position at a time.

## Running it

```
pip install pandas numpy pytest
python -m pytest backtest            # hand-built cases with known outcomes
python -m backtest.run --data bars.csv
```

`bars.csv` should be 1-minute bars with `time,open,high,low,close[,volume]`
columns (TradingView, histdata.com and MetaTrader 5 exports are also read; for MT5 pass the broker server timezone with `--src-tz`). The last 30%
of the history is held out and reported separately; judge the strategy on that row.

## Rules for using the results

1. Do not change a parameter after looking at the hold-out row.
2. A few dozen trades prove nothing; look for hundreds.
3. Results here are simulations, not a forecast of live trading.
