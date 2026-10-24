"""Orchestration: scrape wholesale -> match on eBay -> compute net margin ->
filter to the winners -> rank. This is the PoC's whole job.

It deliberately STOPS at "here are the profitable products". Actually buying
stock and auto-listing on eBay is Stage 3 (needs the eBay Sell/Inventory API,
OAuth, and — per eBay policy — stock you physically hold). See the README."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from typing import Optional

from .config import ScannerConfig
from .ebay_client import EbayBrowseClient, EbayMatch
from .margin import MarginResult, compute_margin
from .wholesale import HomeBargainsScraper, WholesaleProduct


@dataclass
class Opportunity:
    title: str
    source: str
    buy_price: float
    ebay_median: float
    net_profit: float
    margin_pct: float
    matched_by: str
    competition: int        # active eBay listings seen (rough liquidity proxy)
    ean: Optional[str]
    wholesale_url: str
    ebay_url: Optional[str]


class ArbitrageScanner:
    def __init__(self, config: ScannerConfig, ebay: EbayBrowseClient, use_browser: bool = False):
        self.config = config
        self.ebay = ebay
        self.scraper = HomeBargainsScraper(config, use_browser=use_browser)

    def scan(self, queries: list[str]) -> list[Opportunity]:
        products = self.scraper.search_many(queries)
        print(f"[scanner] {len(products)} wholesale products scraped")

        opportunities: list[Opportunity] = []
        for product in products[: self.config.max_ebay_lookups]:
            match = self._safe_lookup(product)
            if not match or not match.median_price:
                continue

            # Use the median asking price as a conservative resale estimate.
            margin = compute_margin(product.price, match.median_price, self.config.fees)

            if self._passes_filters(margin):
                opportunities.append(self._to_opportunity(product, match, margin))

        opportunities.sort(key=lambda o: o.net_profit, reverse=True)
        print(f"[scanner] {len(opportunities)} opportunities above threshold")
        return opportunities

    # --- helpers --------------------------------------------------------
    def _safe_lookup(self, product: WholesaleProduct) -> Optional[EbayMatch]:
        try:
            return self.ebay.find_resale_price(ean=product.ean, title=product.title)
        except Exception as exc:
            print(f"[scanner] eBay lookup failed for '{product.title}': {exc}")
            return None

    def _passes_filters(self, margin: MarginResult) -> bool:
        return (
            margin.net_profit >= self.config.min_net_profit
            and margin.margin_pct >= self.config.min_margin_pct
        )

    @staticmethod
    def _to_opportunity(product: WholesaleProduct, match: EbayMatch, margin: MarginResult) -> Opportunity:
        return Opportunity(
            title=product.title,
            source=product.source,
            buy_price=margin.buy_price,
            ebay_median=margin.resale_price,
            net_profit=margin.net_profit,
            margin_pct=margin.margin_pct,
            matched_by=match.matched_by,
            competition=match.sample_size,
            ean=product.ean,
            wholesale_url=product.url,
            ebay_url=match.example_url,
        )


def write_csv(opportunities: list[Opportunity], path: str) -> None:
    if not opportunities:
        print("[scanner] nothing to write")
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(opportunities[0]).keys()))
        writer.writeheader()
        for opp in opportunities:
            writer.writerow(asdict(opp))
    print(f"[scanner] wrote {len(opportunities)} rows -> {path}")


def print_table(opportunities: list[Opportunity], top: int = 20) -> None:
    if not opportunities:
        print("No profitable products found with current thresholds.")
        return
    print(f"\n{'PRODUCT':<42} {'BUY':>6} {'eBAY':>7} {'PROFIT':>7} {'ROI%':>6} {'MATCH':>6}")
    print("-" * 80)
    for o in opportunities[:top]:
        print(
            f"{o.title[:40]:<42} "
            f"{o.buy_price:>6.2f} {o.ebay_median:>7.2f} "
            f"{o.net_profit:>7.2f} {o.margin_pct:>6.0f} {o.matched_by:>6}"
        )
