#!/usr/bin/env python3
"""Fetch early Bitcoin block data for Patoshi-pattern analysis.

RUN THIS ON YOUR OWN MACHINE, not inside a restricted agent environment.

Why: Claude Code's hosted environments sit behind an egress proxy that answers 403
to CONNECT for blockchain hosts. GitHub is allowed, so the working pattern is:

    1. run this script locally           -> data/early_blocks.csv
    2. commit and push it to your repo   -> git add data/early_blocks.csv
    3. the agent pulls and analyses it   -> python -m spa.cli patoshi

The output is deliberately small and text-based so it lives comfortably in git:
roughly 60 bytes per block, so 50,000 blocks is about 3 MB.

WHAT IT COLLECTS
----------------
For each block: height, timestamp, the header nonce, the difficulty bits, the
coinbase transaction's scriptSig (which carries the ExtraNonce), and the coinbase
output address if one can be derived.

The Patoshi analysis rests on the ExtraNonce and nonce fields. Sergio Lerner's 2013
work showed early blocks carry a distinctive incrementing structure in these values,
revealing that a single entity using a particular multi-machine setup mined a large
share of the first eighteen months - and that it throttled its own hash rate rather
than taking everything available.

USAGE
-----
    python3 fetch_early_blocks.py --end 50000 --out data/early_blocks.csv

Resumable: re-running appends only blocks missing from the existing file, so an
interrupted fetch costs nothing.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, Iterable, Optional, Set

# Public APIs, in preference order. All are rate-limited; be polite.
BACKENDS = {
    "blockstream": {
        "hash_at_height": "https://blockstream.info/api/block-height/{height}",
        "block": "https://blockstream.info/api/block/{hash}",
        "coinbase": "https://blockstream.info/api/block/{hash}/txids",
        "tx": "https://blockstream.info/api/tx/{txid}",
    },
    "mempool": {
        "hash_at_height": "https://mempool.space/api/block-height/{height}",
        "block": "https://mempool.space/api/block/{hash}",
        "coinbase": "https://mempool.space/api/block/{hash}/txids",
        "tx": "https://mempool.space/api/tx/{txid}",
    },
}

FIELDS = ["height", "timestamp", "nonce", "bits", "version",
          "coinbase_scriptsig", "coinbase_address", "block_hash"]


def _get(url: str, retries: int = 5, pause: float = 1.0) -> Optional[str]:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "satoshi-pgp-audit/1.0"})
            with urllib.request.urlopen(req, timeout=30) as fh:
                return fh.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 502, 503, 504):
                time.sleep(pause * (2 ** attempt))
                continue
            return None
        except Exception:
            time.sleep(pause * (2 ** attempt))
    return None


def existing_heights(path: str) -> Set[int]:
    if not os.path.exists(path):
        return set()
    out: Set[int] = set()
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                out.add(int(row["height"]))
            except (KeyError, ValueError):
                continue
    return out


def fetch_block(api: Dict[str, str], height: int) -> Optional[Dict]:
    bhash = _get(api["hash_at_height"].format(height=height))
    if not bhash:
        return None
    bhash = bhash.strip()
    raw = _get(api["block"].format(hash=bhash))
    if not raw:
        return None
    blk = json.loads(raw)

    scriptsig, address = "", ""
    txids_raw = _get(api["coinbase"].format(hash=bhash))
    if txids_raw:
        try:
            coinbase_txid = json.loads(txids_raw)[0]
            tx_raw = _get(api["tx"].format(txid=coinbase_txid))
            if tx_raw:
                tx = json.loads(tx_raw)
                vin = tx.get("vin", [{}])[0]
                scriptsig = vin.get("scriptsig", "") or ""
                vout = tx.get("vout", [{}])[0]
                address = vout.get("scriptpubkey_address", "") or ""
        except (ValueError, IndexError, KeyError):
            pass

    return {
        "height": height,
        "timestamp": blk.get("timestamp", ""),
        "nonce": blk.get("nonce", ""),
        "bits": blk.get("bits", ""),
        "version": blk.get("version", ""),
        "coinbase_scriptsig": scriptsig,
        "coinbase_address": address,
        "block_hash": bhash,
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=50000,
                    help="last block height (inclusive). Patoshi structure is "
                         "clearest below ~50000.")
    ap.add_argument("--out", default="data/early_blocks.csv")
    ap.add_argument("--backend", choices=sorted(BACKENDS), default="blockstream")
    ap.add_argument("--sleep", type=float, default=0.05,
                    help="delay between blocks; raise if you get rate limited")
    args = ap.parse_args(list(argv) if argv is not None else None)

    api = BACKENDS[args.backend]
    have = existing_heights(args.out)
    todo = [h for h in range(args.start, args.end + 1) if h not in have]
    if not todo:
        print("nothing to do: %d blocks already present in %s" % (len(have), args.out))
        return 0

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    write_header = not os.path.exists(args.out)

    print("fetching %d blocks (%d-%d) from %s"
          % (len(todo), todo[0], todo[-1], args.backend))
    print("already have: %d" % len(have))

    done = failed = 0
    with open(args.out, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        for i, height in enumerate(todo):
            row = fetch_block(api, height)
            if row is None:
                failed += 1
                print("  height %d: FAILED" % height, file=sys.stderr)
            else:
                writer.writerow(row)
                done += 1
            if i % 250 == 0:
                fh.flush()
                pct = 100.0 * (i + 1) / len(todo)
                print("  %6.2f%%  height %-7d ok=%d failed=%d"
                      % (pct, height, done, failed), flush=True)
            time.sleep(args.sleep)

    print("\ndone: %d fetched, %d failed -> %s" % (done, failed, args.out))
    print("\nNext:")
    print("  git add %s && git commit -m 'Add early block data' && git push" % args.out)
    print("  then ask the agent to run: python -m spa.cli patoshi --input %s" % args.out)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
