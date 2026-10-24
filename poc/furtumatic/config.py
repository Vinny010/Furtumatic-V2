"""Central configuration for the arbitrage scanner.

Everything that affects the economics lives here so you can tune the model
without touching the scraping / matching code. Values can be overridden with
environment variables (see .env.example) so nothing sensitive is committed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


@dataclass
class FeeModel:
    """eBay UK selling costs. Defaults are typical private/standard-shop
    numbers for late 2025 — CHECK them against your own category & shop tier,
    because the fee is what separates a real winner from a loss."""

    # Final value fee: eBay takes a % of the total sale (item + postage) + fixed.
    fv_fee_pct: float = field(default_factory=lambda: _env_float("EBAY_FV_FEE_PCT", 0.128))
    fv_fee_fixed: float = field(default_factory=lambda: _env_float("EBAY_FV_FEE_FIXED", 0.30))

    # What it costs YOU to fulfil one order.
    postage: float = field(default_factory=lambda: _env_float("POSTAGE_COST", 3.30))
    packaging: float = field(default_factory=lambda: _env_float("PACKAGING_COST", 0.30))

    # Optional per-unit handling (petrol to the shop, your time, etc.).
    handling: float = field(default_factory=lambda: _env_float("HANDLING_COST", 0.0))


@dataclass
class ScannerConfig:
    # Only surface products whose net profit is at least this % of the buy cost.
    # 100 means "we at least double our money after all fees" (the user's target).
    min_margin_pct: float = field(default_factory=lambda: _env_float("MIN_MARGIN_PCT", 100.0))

    # Absolute floor so tiny-but-high-% items don't clutter results (£).
    min_net_profit: float = field(default_factory=lambda: _env_float("MIN_NET_PROFIT", 2.0))

    # Be a polite scraper: seconds to wait between wholesale page requests.
    request_delay_s: float = field(default_factory=lambda: _env_float("REQUEST_DELAY_S", 1.5))

    # Cap eBay API calls during a PoC run so you don't burn your daily quota.
    max_ebay_lookups: int = field(default_factory=lambda: _env_int("MAX_EBAY_LOOKUPS", 50))

    marketplace_id: str = field(default_factory=lambda: os.getenv("EBAY_MARKETPLACE_ID", "EBAY_GB"))
    fees: FeeModel = field(default_factory=FeeModel)

    user_agent: str = field(
        default_factory=lambda: os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        )
    )
