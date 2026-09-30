# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24"]
# ///
"""
edge_finder.py — the honest test for a TIME-OF-DAY (or day-of-week) edge.

The only question that decides whether the 5-min EA can make money:
  Is there a clock bucket the market SYSTEMATICALLY misprices — one that stays
  positive-EV on data it was NOT chosen on, after costs, and survives the fact
  that you tested many buckets?

Most "I found a good hour" claims fail because of three traps. This tool closes
all three:

  1. IN-SAMPLE PEEKING. Pick the hour on the same data you grade it on and you
     will always find one. FIX: candidate hours are chosen on the TRAIN split
     (earlier data) and graded ONLY on the TEST split (later data). True OOS.

  2. MULTIPLE TESTING. Test 24 hours at p<0.05 and ~1 looks "significant" by
     luck. FIX: Benjamini-Hochberg FDR correction across every bucket examined.

  3. NO COSTS. A raw backtest with zero fees/slippage flatters everything.
     FIX: --cost is added to the price you pay on every single trade.

INPUT  (--csv): one row per trade/opportunity, columns (any order, case-insensitive):
    timestamp   UTC time of entry (ISO, or unix seconds/ms)
    price       price you PAY for the favorite, 0..1 (Polymarket ask at entry)
    won         1 if that outcome resolved true, else 0
  Optional:
    stake       $ staked (default 1); PnL scales by it but EV/trade does not.

OUTPUT: OOS EV per trade overall, a per-bucket table, and a one-line VERDICT
that says EDGE / NO EDGE — and only says EDGE if a bucket clears OOS + costs +
FDR. If nothing clears, that is the answer: no tradeable clock pattern here.

SELF-TEST (no data needed) — proves the tool both fires and stays quiet:
    uv run edge_finder.py --self-test
  Builds two synthetic books: a NULL efficient market (must find NOTHING) and
  one with a single hour planted 3c underpriced (must find THAT hour, OOS).

REAL USE:
    uv run edge_finder.py --csv my_trades.csv --cost 0.02
    uv run edge_finder.py --csv my_trades.csv --by dow      # day-of-week instead
"""
import argparse
import csv
import sys
from datetime import datetime, timezone

import numpy as np

RNG = np.random.default_rng(0)
BOOT = 5000            # bootstrap resamples for significance
Q_FDR = 0.05          # false-discovery-rate target


# --------------------------------------------------------------------- returns
def trade_returns(price, won, cost):
    """Return per $1 staked, buying the favorite at `price` + `cost`, settle 1/0.

    win  ->  (1 - p) / p        (buy shares at p, each pays 1)
    lose ->  -1
    Cost is added to the price actually paid (spread + slippage + fee).
    """
    p = np.clip(price + cost, 1e-6, 0.999999)
    r = np.where(won >= 0.5, (1.0 - p) / p, -1.0)
    return r


# ----------------------------------------------------------------- statistics
def boot_p_mean_le_zero(x):
    """One-sided bootstrap p-value that mean(x) <= 0. Small p => real positive EV."""
    if len(x) < 2:
        return 1.0
    idx = RNG.integers(0, len(x), size=(BOOT, len(x)))
    means = x[idx].mean(axis=1)
    return float((means <= 0).mean())


def bh_reject(pvals, q=Q_FDR):
    """Benjamini-Hochberg: return boolean mask of hypotheses that clear FDR=q."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    if m == 0:
        return np.zeros(0, dtype=bool)
    order = np.argsort(p)
    thresh = q * (np.arange(1, m + 1) / m)
    passed = p[order] <= thresh
    reject = np.zeros(m, dtype=bool)
    if passed.any():
        kmax = np.max(np.where(passed))          # largest rank that passes
        reject[order[: kmax + 1]] = True
    return reject


# --------------------------------------------------------------------- buckets
def bucket_of(ts, by):
    dt = ts.astimezone(timezone.utc)
    return dt.hour if by == "hour" else dt.weekday()   # 0=Mon


BUCKET_NAMES = {
    "hour": [f"{h:02d}:00 UTC" for h in range(24)],
    "dow": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}


def analyse(ts, price, won, by="hour", cost=0.0, train_frac=0.6):
    """Chronological train/test split; pick +EV buckets on train, grade on test."""
    order = np.argsort([t.timestamp() for t in ts])
    ts = [ts[i] for i in order]
    price, won = price[order], won[order]
    ret = trade_returns(price, won, cost)
    b = np.array([bucket_of(t, by) for t in ts])

    n = len(ret)
    cut = int(n * train_frac)
    tr = slice(0, cut)
    te = slice(cut, n)

    n_buckets = 24 if by == "hour" else 7
    rows, cand_idx = [], []
    for k in range(n_buckets):
        tr_mask = (b[tr] == k)
        te_mask = (b[te] == k)
        tr_ev = ret[tr][tr_mask].mean() if tr_mask.sum() else np.nan
        te_r = ret[te][te_mask]
        te_ev = te_r.mean() if len(te_r) else np.nan
        rows.append({
            "k": k, "name": BUCKET_NAMES[by][k],
            "n_tr": int(tr_mask.sum()), "n_te": int(len(te_r)),
            "tr_ev": tr_ev, "te_ev": te_ev, "te_r": te_r,
        })
        # candidate = looked good on TRAIN (chosen without seeing test)
        if np.isfinite(tr_ev) and tr_ev > 0 and len(te_r) >= 30:
            cand_idx.append(k)

    # significance on TEST only, for the candidates, with FDR across candidates
    pvals = [boot_p_mean_le_zero(rows[k]["te_r"]) for k in cand_idx]
    rej = bh_reject(pvals, Q_FDR)
    winners = []
    for j, k in enumerate(cand_idx):
        rows[k]["p_oos"] = pvals[j]
        rows[k]["fdr_pass"] = bool(rej[j])
        if rows[k]["te_ev"] > 0 and rej[j]:
            winners.append(k)

    overall_te_ev = ret[te].mean()
    return rows, winners, overall_te_ev, cut, n


def report(rows, winners, overall, cut, n, by, cost):
    unit = "hour-of-day" if by == "hour" else "day-of-week"
    print(f"\n  EDGE FINDER — {unit} test   (cost {cost*100:.1f}c/trade, "
          f"train {cut:,} / test {n-cut:,} trades, OOS)")
    print(f"  overall OOS EV: {overall*100:+.2f}% per $1 staked "
          f"(all buckets, held-out data)\n")
    hdr = f"  {'bucket':>11}{'trainEV%':>10}{'testEV%':>9}{'n_test':>8}{'OOS p':>8}  verdict"
    print(hdr)
    for r in rows:
        te = f"{r['te_ev']*100:+.2f}" if np.isfinite(r["te_ev"]) else "  --"
        tr = f"{r['tr_ev']*100:+.2f}" if np.isfinite(r["tr_ev"]) else "  --"
        p = f"{r.get('p_oos'):.3f}" if "p_oos" in r else "   -"
        if r["k"] in winners:
            v = "*** EDGE (holds OOS + FDR) ***"
        elif "p_oos" in r:
            v = "candidate, failed OOS/FDR"
        else:
            v = ""
        print(f"  {r['name']:>11}{tr:>10}{te:>9}{r['n_te']:>8}{p:>8}  {v}")

    print()
    if winners:
        names = ", ".join(rows[k]["name"] for k in winners)
        print(f"  VERDICT: EDGE FOUND -> {names}")
        print("  A bucket stayed positive on data it was NOT chosen on, after")
        print("  costs, and survived multiple-testing correction. Worth sizing")
        print("  (this is exactly what the GARCH layer would then wrap).")
    else:
        print("  VERDICT: NO EDGE. No clock bucket held up out-of-sample after")
        print("  costs and multiple-testing correction. Any 'good hour' you see")
        print("  in trainEV% is noise that did not repeat on held-out data.")
    print()


# --------------------------------------------------------------------- I/O
def load_csv(path):
    ts, price, won = [], [], []
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh)
        cols = {c.lower().strip(): c for c in rd.fieldnames}
        def col(*names):
            for nm in names:
                if nm in cols:
                    return cols[nm]
            sys.exit(f"CSV needs a column among {names}; found {list(cols)}")
        tc, pc, wc = col("timestamp", "time", "date"), col("price", "ask", "entry"), col("won", "win", "outcome")
        for row in rd:
            raw = row[tc].strip()
            try:
                f = float(raw)
                t = datetime.fromtimestamp(f / (1000 if f > 1e11 else 1), timezone.utc)
            except ValueError:
                t = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
            ts.append(t)
            price.append(float(row[pc]))
            won.append(1.0 if str(row[wc]).strip() in ("1", "1.0", "true", "True", "win", "won", "yes") else 0.0)
    return ts, np.array(price), np.array(won)


# --------------------------------------------------------------- self-test data
def make_synth(planted_hour=None, n=24000, edge=0.03, seed=1):
    """Build a synthetic favorite book. If planted_hour is set, that hour is
    underpriced by `edge` (a real +EV mispricing); every other hour is fair."""
    rng = np.random.default_rng(seed)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    ts, price, won = [], [], []
    for i in range(n):
        t = base.replace()  # copy
        # spread trades across ~500 days and all 24 hours
        from datetime import timedelta
        t = base + timedelta(minutes=5 * i)
        p_true = rng.uniform(0.70, 0.97)             # favorite's true win prob
        q = p_true                                    # efficient: price == truth
        if planted_hour is not None and t.hour == planted_hour:
            q = p_true - edge                         # underpriced -> real edge
        w = 1.0 if rng.random() < p_true else 0.0
        ts.append(t); price.append(q); won.append(w)
    return ts, np.array(price), np.array(won)


def self_test():
    print("=" * 68)
    print("SELF-TEST 1/2 — NULL efficient market (tool MUST find no edge)")
    print("=" * 68)
    ts, pr, wn = make_synth(planted_hour=None)
    rows, win, ov, cut, n = analyse(ts, pr, wn, by="hour", cost=0.0)
    report(rows, win, ov, cut, n, "hour", 0.0)

    print("=" * 68)
    print("SELF-TEST 2/2 — one hour (14:00 UTC) planted 3c underpriced")
    print("                (tool MUST detect 14:00, OOS, after correction)")
    print("=" * 68)
    ts, pr, wn = make_synth(planted_hour=14, edge=0.03)
    rows, win, ov, cut, n = analyse(ts, pr, wn, by="hour", cost=0.0)
    report(rows, win, ov, cut, n, "hour", 0.0)

    got = {rows[k]["name"] for k in win}
    ok = (got == {"14:00 UTC"})
    print("SELF-TEST RESULT:", "PASS ✅ (found only the planted hour)" if ok
          else f"CHECK ⚠  (found {got or 'nothing'})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--by", choices=["hour", "dow"], default="hour")
    ap.add_argument("--cost", type=float, default=0.0,
                    help="price add-on per trade (spread+slippage+fee), e.g. 0.02")
    ap.add_argument("--train-frac", type=float, default=0.6)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test(); return
    if not args.csv:
        sys.exit("give --csv trades.csv  (or --self-test). See header for format.")
    ts, price, won = load_csv(args.csv)
    if len(ts) < 200:
        sys.exit(f"only {len(ts)} trades; need a few hundred+ for a real test.")
    rows, winners, overall, cut, n = analyse(
        ts, price, won, by=args.by, cost=args.cost, train_frac=args.train_frac)
    report(rows, winners, overall, cut, n, args.by, args.cost)


if __name__ == "__main__":
    main()
