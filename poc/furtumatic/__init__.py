"""Furtumatic PoC — retail-arbitrage scanner (wholesale -> eBay UK)."""

from .config import FeeModel, ScannerConfig
from .margin import MarginResult, compute_margin
from .scanner import ArbitrageScanner, Opportunity, print_table, write_csv

__all__ = [
    "FeeModel",
    "ScannerConfig",
    "MarginResult",
    "compute_margin",
    "ArbitrageScanner",
    "Opportunity",
    "print_table",
    "write_csv",
]
