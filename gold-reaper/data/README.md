# Expected inputs (drop here, commit, push)

- `gold_reaper_history.csv` — raw table from the MQL5 signal History tab
  (tools/scrape_mql5_history.js). Any column order is fine; keep the header row.
- `xauusd_m5.csv`, `xauusd_m15.csv` — from tools/export_xauusd_mt5.py
  (columns: time,open,high,low,close,tick_volume,spread; time = broker server time).
- `server_offset.txt` — written by the exporter (your broker's UTC offset).
- Add one line here with the SIGNAL's broker/server name from the signal page
  (needed to align the signal's timestamps to your bar data):
  signal_broker=
