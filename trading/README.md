# Trading bots and research tools built in this session

None of these place real orders. All are paper/backtest tools unless stated.

| file | what it is | how to run |
|---|---|---|
| `sat_dashboard.py` | **Latest.** Single-file live paper bot: BTC-accumulating volatility-harvesting grid on live Binance prices, 200-period MA regime gate, BTC-denominated scoring, browser dashboard at http://localhost:8787 (`/api/status` JSON). | `python sat_dashboard.py --live --symbol BTCUSDT` |
| `grid_dashboard.py` | Earlier dashboard version (used by START_DASHBOARD.bat). | `python grid_dashboard.py --live --symbol BTCUSDT --step 0.004` |
| `START_DASHBOARD.bat` | Windows one-click launcher for the paper dashboard. | double-click |
| `paper_grid.py` | Headless paper-trading grid on live Binance prices, logs trades to disk. | `python paper_grid.py --symbol BTCUSDT` |
| `sat_stacker.py` | Backtester for the BTC-accumulating grid: scores in BTC, tests step sizes and the regime gate on historical klines. | `uv run sat_stacker.py` |
| `edge_finder.py` | Backtest harness used to evaluate the Polymarket 5-min EA idea and other simple rules with costs; reports when strategies lose. | `uv run edge_finder.py` |
| `sat_stacker_window.html` | Static dashboard mock-up (design reference only). | open in browser |

Live-desktop result so far (user's PC, 2026-09): 7 trades, 3 buys / 4 sells, -0.03% after fees. Not an edge yet.

## Not in this folder
- **Gold Reaper New V2 2** reverse-engineering: only the data tools exist (`../gold-reaper/tools/`); the signal's trade history could not be pulled from this sandbox. No EA was built.
- **garchmethod** (Miles Deutscher): evaluated, not built here; it is a position-sizing tool, not a signal.
- **Prop-firm alpha engine**: specified as a prompt for your desktop Claude session (C:\AlphaLab). Not built here.
