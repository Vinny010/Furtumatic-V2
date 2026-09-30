#!/usr/bin/env python3
"""
paper_grid.py — PAPER-TRADE the sat_stacker grid on LIVE Binance prices.

No API keys. No real money. No orders are ever sent. It polls Binance's PUBLIC
price feed, runs the exact grid logic from sat_stacker.py against real live
moves, simulates fills with paper balances, and tracks P&L in BITCOIN.

  * Fills are modeled CONSERVATIVELY (taker): buys at the ask, sells at the bid,
    so the spread is paid, not earned. As a real maker you'd do a bit better —
    this way the paper result never flatters you.
  * The 200-day regime gate is seeded from real historical daily closes at
    startup, then the grid STOPS SELLING in a confirmed bull (same rule as the
    backtester).
  * Every fill is printed and logged to CSV. A summary prints on exit (Ctrl-C)
    or when --hours elapses.

Run it at home (this needs to reach api.binance.com):

    python paper_grid.py --symbol BTCUSDT --step 0.004 --hours 168     # ~1 week
    python paper_grid.py --symbol BTCUSDC --step 0.004 --poll 3 --start-btc 0.5

Only the Python standard library is required.
"""
import argparse
import csv
import json
import signal
import sys
import time
import urllib.request
from datetime import datetime, timezone

BINANCE = "https://api.binance.com"


# ------------------------------------------------------------- live data (public)
def http_json(path):
    req = urllib.request.Request(BINANCE + path, headers={"User-Agent": "paper-grid"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def book_ticker(symbol):
    d = http_json(f"/api/v3/ticker/bookTicker?symbol={symbol}")
    return float(d["bidPrice"]), float(d["askPrice"])


def seed_ma(symbol, window=200):
    """Fetch `window` daily closes to seed the regime moving average."""
    kl = http_json(f"/api/v3/klines?symbol={symbol}&interval=1d&limit={window}")
    closes = [float(k[4]) for k in kl]
    return sum(closes) / len(closes), closes


# ---------------------------------------------------------------------- the grid
class PaperGrid:
    def __init__(self, start_btc, price, ma, step, unit_frac, fee, trend_band):
        self.start_btc = start_btc
        cap = start_btc * price
        self.btc = cap * 0.5 / price      # start 50/50
        self.usd = cap * 0.5
        self.unit = cap * unit_frac
        self.ref = price
        self.ma = ma
        self.step = step
        self.fee = fee
        self.trend_band = trend_band
        self.buys = self.sells = 0
        self.log = []

    def bull(self, price):
        return price > self.ma * (1 + self.trend_band)

    def on_tick(self, bid, ask, ts):
        mid = 0.5 * (bid + ask)
        acted = None
        if mid <= self.ref * (1 - self.step) and self.usd >= self.unit:
            q = self.unit / ask                       # buy at the ask (pay spread)
            self.btc += q * (1 - self.fee); self.usd -= self.unit
            self.ref = mid; self.buys += 1; acted = ("BUY", ask, q)
        elif mid >= self.ref * (1 + self.step) and self.btc * bid > self.unit \
                and not self.bull(mid):
            q = self.unit / bid                       # sell at the bid (pay spread)
            self.btc -= q; self.usd += q * bid * (1 - self.fee)
            self.ref = mid; self.sells += 1; acted = ("SELL", bid, q)
        elif self.bull(mid):
            self.ref = mid                            # bull: let ref ride, don't sell
        if acted:
            side, px, q = acted
            row = dict(time=ts, side=side, price=round(px, 2), qty=round(q, 8),
                       btc=round(self.btc, 8), usd=round(self.usd, 2),
                       value_btc=round(self.value_btc(mid), 6))
            self.log.append(row)
            print(f"  {ts}  {side:4} {q:.6f} BTC @ ${px:,.0f}   "
                  f"stack={row['value_btc']:.5f} BTC  ({self.sells}S/{self.buys}B)"
                  f"{'  [BULL: selling paused]' if self.bull(mid) else ''}")
        return acted

    def value_btc(self, price):
        return self.btc + self.usd / price


# ---------------------------------------------------------------------- runner
def run(args):
    print(f"seeding 200-day regime MA for {args.symbol} ...")
    ma, _ = seed_ma(args.symbol)
    bid, ask = book_ticker(args.symbol)
    p0 = 0.5 * (bid + ask)
    g = PaperGrid(args.start_btc, p0, ma, args.step, args.unit, args.fee, args.trend_band)
    print(f"live paper grid START  {args.symbol}  price ${p0:,.0f}  "
          f"200dMA ${ma:,.0f}  {'(BULL regime: sells gated)' if g.bull(p0) else '(harvest regime)'}")
    print(f"start stack: {g.value_btc(p0):.5f} BTC   step {args.step*100:.2f}%  "
          f"unit ${g.unit:,.0f}  fee {args.fee*100:.3f}%/side\n")

    stop = {"end": time.time() + args.hours * 3600}

    def bye(*_):
        summarize(g, args); sys.exit(0)
    signal.signal(signal.SIGINT, bye)

    last_hodl = args.start_btc
    while time.time() < stop["end"]:
        try:
            bid, ask = book_ticker(args.symbol)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            g.on_tick(bid, ask, ts)
        except Exception as e:                        # network hiccup -> keep going
            print(f"  (feed error: {e}; retrying)")
        time.sleep(args.poll)
    summarize(g, args)


def summarize(g, args):
    try:
        bid, ask = book_ticker(args.symbol)
        price = 0.5 * (bid + ask)
    except Exception:
        price = g.ref
    stack = g.value_btc(price)
    hodl = args.start_btc
    print("\n" + "=" * 60)
    print(f"  PAPER RESULT  {args.symbol}   (price now ${price:,.0f})")
    print(f"  trades: {g.buys+g.sells}  ({g.buys} buys / {g.sells} sells)")
    print(f"  HODL : {hodl:.5f} BTC")
    print(f"  GRID : {stack:.5f} BTC   ({(stack/hodl-1)*100:+.2f}% sats)   "
          f"[USD ${g.btc*price+g.usd:,.0f}]")
    if g.log:
        with open(args.log, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(g.log[0].keys()))
            w.writeheader(); w.writerows(g.log)
        print(f"  {len(g.log)} fills logged -> {args.log}")
    print("  NOTE: one run = one week's regime, not a statistical verdict.")
    print("        Pair with sat_stacker.py --csv over years of history.")
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--step", type=float, default=0.004, help="grid step (0.004 = 0.4%)")
    ap.add_argument("--unit", type=float, default=0.08, help="fraction of capital per fill")
    ap.add_argument("--fee", type=float, default=0.0, help="per-side fee (0 for zero-fee pair)")
    ap.add_argument("--trend-band", type=float, default=0.05)
    ap.add_argument("--start-btc", type=float, default=0.5)
    ap.add_argument("--poll", type=float, default=3.0, help="seconds between price polls")
    ap.add_argument("--hours", type=float, default=168.0, help="run duration (168 = 1 week)")
    ap.add_argument("--log", default="paper_grid_fills.csv")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
