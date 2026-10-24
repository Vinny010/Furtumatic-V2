#!/usr/bin/env python3
"""Furtumatic arbitrage scanner — proof of concept.

Usage:
    python run_poc.py coffee "olive oil" shampoo
    python run_poc.py --browser coffee        # render with Playwright if blocked
    python run_poc.py --demo                   # no network: show the margin maths

Set credentials in a .env file (see .env.example) or the environment:
    EBAY_CLIENT_ID, EBAY_CLIENT_SECRET
"""
from __future__ import annotations

import argparse
import os
import sys

from furtumatic import ScannerConfig, compute_margin, print_table, write_csv
from furtumatic.ebay_client import EbayBrowseClient
from furtumatic.scanner import ArbitrageScanner

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def run_demo(config: ScannerConfig) -> None:
    """Offline sanity check of the economics — the part that decides if a
    deal is real. No scraping, no API calls."""
    print("DEMO: true net profit after eBay fees + postage\n")
    examples = [
        ("Douwe Egberts Pure Gold 190g", 3.49, 8.99),
        ("Small novelty gift", 1.99, 5.99),
        ("Bulky low-value item", 2.00, 6.00),
    ]
    for name, buy, resale in examples:
        m = compute_margin(buy, resale, config.fees)
        verdict = "WIN " if (m.margin_pct >= config.min_margin_pct and m.net_profit >= config.min_net_profit) else "skip"
        print(
            f"[{verdict}] {name:<32} buy £{buy:<5} resale £{resale:<5} "
            f"-> net £{m.net_profit:<6} (ROI {m.margin_pct:.0f}%, costs £{m.selling_costs})"
        )
    print(f"\nFilters: min ROI {config.min_margin_pct:.0f}%, min net £{config.min_net_profit}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Wholesale -> eBay UK arbitrage scanner (PoC)")
    parser.add_argument("queries", nargs="*", help="search terms to scan at the wholesaler")
    parser.add_argument("--browser", action="store_true", help="render pages with Playwright")
    parser.add_argument("--demo", action="store_true", help="run the offline margin demo and exit")
    parser.add_argument("--out", default="opportunities.csv", help="output CSV path")
    args = parser.parse_args()

    config = ScannerConfig()

    if args.demo:
        run_demo(config)
        return 0

    if not args.queries:
        parser.error("provide at least one search term, or use --demo")

    client_id = os.getenv("EBAY_CLIENT_ID")
    client_secret = os.getenv("EBAY_CLIENT_SECRET")
    if not (client_id and client_secret):
        print("ERROR: set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET (see .env.example).", file=sys.stderr)
        print("Tip: run `python run_poc.py --demo` to see the margin maths with no credentials.", file=sys.stderr)
        return 1

    ebay = EbayBrowseClient(config, client_id, client_secret)
    scanner = ArbitrageScanner(config, ebay, use_browser=args.browser)

    opportunities = scanner.scan(args.queries)
    print_table(opportunities)
    write_csv(opportunities, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
