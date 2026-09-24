"""
export_xauusd_mt5.py — run on the Windows PC that has MT5 installed + logged in.
    pip install MetaTrader5 pandas
    python export_xauusd_mt5.py --symbol XAUUSD --start 2024-10-01
Writes data/xauusd_m5.csv and data/xauusd_m15.csv (server time, naive) and
data/server_offset.txt (broker server offset vs UTC in hours, measured live).
In MT5: Tools > Options > Charts > "Max bars in chart" = Unlimited first.
"""
import argparse, time, sys
from datetime import datetime, timedelta, timezone
import pandas as pd
import MetaTrader5 as mt5

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="XAUUSD")
ap.add_argument("--start", default="2024-10-01")
ap.add_argument("--out", default="data")
a = ap.parse_args()

if not mt5.initialize():
    sys.exit(f"MT5 init failed: {mt5.last_error()}")
if not mt5.symbol_select(a.symbol, True):
    cands = [s.name for s in mt5.symbols_get("*XAU*")] + [s.name for s in mt5.symbols_get("*GOLD*")]
    sys.exit(f"symbol {a.symbol} not found; candidates: {cands}")

# server offset vs UTC: tick time is server-clock epoch, compare with real UTC
tick = mt5.symbol_info_tick(a.symbol)
offset_h = round((tick.time - time.time()) / 3600.0)
open(f"{a.out}/server_offset.txt", "w").write(
    f"server_utc_offset_hours={offset_h}\nbroker={mt5.account_info().server}\nmeasured={datetime.now(timezone.utc).isoformat()}\n")
print(f"broker server {mt5.account_info().server}  offset vs UTC = {offset_h:+d} h")

start = datetime.strptime(a.start, "%Y-%m-%d")
end   = datetime.now() + timedelta(days=1)
for tf_name, tf in (("m5", mt5.TIMEFRAME_M5), ("m15", mt5.TIMEFRAME_M15)):
    frames, t0 = [], start
    while t0 < end:                                   # monthly chunks avoid bar caps
        t1 = min(t0 + timedelta(days=31), end)
        r = mt5.copy_rates_range(a.symbol, tf, t0, t1)
        if r is not None and len(r):
            frames.append(pd.DataFrame(r))
        t0 = t1
    df = pd.concat(frames).drop_duplicates("time").sort_values("time")
    df["time"] = pd.to_datetime(df["time"], unit="s")     # server time, naive
    df = df[["time","open","high","low","close","tick_volume","spread"]]
    df.to_csv(f"{a.out}/xauusd_{tf_name}.csv", index=False)
    print(f"{tf_name}: {len(df):,} bars  {df.time.min()} -> {df.time.max()}")
mt5.shutdown()
