# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24"]
# ///
"""
sat_stacker.py — the converged design, scored in BITCOIN.

A volatility-harvesting GRID on a BTC/stable pair that:
  * buys a fixed slice of BTC each time price falls one grid step,
  * sells a slice each time it rises one step,
  * so it accumulates sats from oscillation (no direction call needed),
  * and is GATED by regime: in a confirmed strong bull it STOPS SELLING
    (never sell coins into a rip — that's the one place holding beats the grid).

Fees and the maker/taker choice are explicit knobs, because at high frequency
they decide whether the edge survives (see hft_truth.py). Everything is scored
in BTC: start 0.5 BTC of capital, how many sats do you end with vs just holding?

INPUT
  --csv FILE      columns: date, close  (optionally high, low for realistic fills)
  --self-test     run on synthetic bull / chop / bear years (no data needed)

KNOBS
  --step 0.03     grid step (3% moves). Smaller step -> more trades (finer HF grid).
  --fee 0.0       per-side fee fraction. 0.0 = zero-fee pair, 0.00075 = BNB spot.
  --unit 0.08     fraction of starting capital traded per grid fill.
  --ma 200        regime filter window. --trend-band 0.05 = "bull" if >5% over rising MA.
  --half-spread 0 taker spread cost per fill (0 if you're the maker earning it).

HONESTY: this stacks sats in chop and bear and UNDERPERFORMS holding in a strong
bull. It reports both BTC and USD so you see the trade-off, never just the flattering
number.
"""
import argparse
import csv
import sys

import numpy as np

START_BTC = 0.5


# --------------------------------------------------------------- the strategy
def run_grid(px, ma_win=200, trend_band=0.05, step=0.03, unit_frac=0.08,
             fee=0.0, half_spread=0.0, gate=True):
    """Grid on a close series with a bull-regime sell-gate. Scores in BTC."""
    n = len(px)
    cap = START_BTC * px[0]
    btc = cap * 0.5 / px[0]          # start 50% BTC / 50% stable
    usd = cap * 0.5
    unit = cap * unit_frac
    ref = px[0]
    ma = np.full(n, np.nan)
    if n >= ma_win:
        c = np.cumsum(np.insert(px, 0, 0))
        ma[ma_win - 1:] = (c[ma_win:] - c[:-ma_win]) / ma_win
    buys = sells = 0
    for t in range(1, n):
        p = px[t]
        # regime: strong bull if price well above a rising MA
        bull = False
        if gate and not np.isnan(ma[t]) and t > ma_win:
            bull = (p > ma[t] * (1 + trend_band)) and (ma[t] > ma[t - 5])
        eff_buy = p * (1 + half_spread)      # you pay a touch more as taker
        eff_sell = p * (1 - half_spread)
        if p <= ref * (1 - step) and usd >= unit:                 # dip -> buy BTC
            q = unit / eff_buy
            btc += q * (1 - fee); usd -= unit; ref = p; buys += 1
        elif p >= ref * (1 + step) and btc * p > unit and not bull:  # rip -> sell (gated)
            q = unit / eff_sell
            btc -= q; usd += unit * (1 - fee); ref = p; sells += 1
        elif bull:
            ref = p                          # in a bull, let ref ride up (don't sell)
    end_btc_value = btc + usd / px[-1]        # total value expressed in BTC
    end_usd_value = btc * px[-1] + usd
    return {
        "end_btc": end_btc_value, "sats_vs_hodl_pct": (end_btc_value / START_BTC - 1) * 100,
        "end_usd": end_usd_value, "hodl_usd": START_BTC * px[-1],
        "buys": buys, "sells": sells, "trades": buys + sells,
    }


# ------------------------------------------------------------------- reporting
def show(tag, px, r):
    move = px[-1] / px[0]
    hodl_btc = START_BTC
    print(f"\n  {tag}   (price {move:.2f}x over the sample)")
    print(f"    trades: {r['trades']:>4}  ({r['buys']} buys / {r['sells']} sells)")
    print(f"    HODL   : {hodl_btc:.3f} BTC   (${r['hodl_usd']:,.0f})")
    print(f"    GRID   : {r['end_btc']:.3f} BTC  ({r['sats_vs_hodl_pct']:+.1f}% sats)   "
          f"(${r['end_usd']:,.0f})")
    verdict = ("STACKED sats" if r["end_btc"] > START_BTC + 1e-6
               else "lost sats vs holding")
    print(f"    -> {verdict}")


# ------------------------------------------------------------- synthetic data
def synth(mu, vol, days=365, p0=60000, seed=0):
    rng = np.random.default_rng(seed)
    r = mu / 365 + (vol / np.sqrt(365)) * rng.standard_normal(days)
    return p0 * np.exp(np.cumsum(np.insert(r, 0, 0)))


def self_test(step, fee, unit, half_spread):
    print("=" * 66)
    print("SELF-TEST — grid + bull-gate across three regimes, scored in BTC")
    print(f"  step {step*100:.1f}%  fee/side {fee*100:.3f}%  "
          f"unit {unit*100:.0f}%  half-spread {half_spread*100:.3f}%")
    print("=" * 66)
    cases = [
        ("STRONG BULL", synth(1.00, 0.60, seed=1)),
        ("CHOP       ", synth(0.00, 0.70, seed=2)),
        ("BEAR       ", synth(-0.80, 0.75, seed=3)),
    ]
    for tag, px in cases:
        r = run_grid(px, step=step, fee=fee, unit_frac=unit, half_spread=half_spread)
        show(tag, px, r)
    print("\n  Read it honestly: sats stacked in CHOP/BEAR; in a STRONG BULL the")
    print("  gate limits the damage but holding still wins in BTC terms. Expected.")


def load_csv(path):
    px = []
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh)
        cols = {c.lower().strip(): c for c in rd.fieldnames}
        pc = next((cols[k] for k in ("close", "price", "adj close") if k in cols), None)
        if not pc:
            sys.exit(f"CSV needs a close/price column; found {list(cols)}")
        for row in rd:
            try:
                px.append(float(row[pc]))
            except (ValueError, TypeError):
                pass
    return np.array(px)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--step", type=float, default=0.03)
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--unit", type=float, default=0.08)
    ap.add_argument("--ma", type=int, default=200)
    ap.add_argument("--trend-band", type=float, default=0.05)
    ap.add_argument("--half-spread", type=float, default=0.0)
    ap.add_argument("--no-gate", action="store_true", help="disable the bull regime gate")
    args = ap.parse_args()

    if args.self_test or not args.csv:
        if not args.csv:
            self_test(args.step, args.fee, args.unit, args.half_spread)
        if not args.csv:
            return
    px = load_csv(args.csv)
    if len(px) < args.ma + 10:
        sys.exit(f"need > {args.ma+10} rows; got {len(px)}")
    r = run_grid(px, ma_win=args.ma, trend_band=args.trend_band, step=args.step,
                 unit_frac=args.unit, fee=args.fee, half_spread=args.half_spread,
                 gate=not args.no_gate)
    show(f"REAL DATA ({args.csv})", px, r)


if __name__ == "__main__":
    main()
