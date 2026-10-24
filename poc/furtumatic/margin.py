"""The money maths. This is the heart of the whole idea: a headline price
gap is NOT profit. Here we turn (buy price, resale price) into true net
profit after everything eBay and the Post Office take."""
from __future__ import annotations

from dataclasses import dataclass

from .config import FeeModel


@dataclass
class MarginResult:
    buy_price: float          # what you pay at the wholesaler
    resale_price: float       # what it realistically sells for on eBay
    selling_costs: float      # eBay fees + postage + packaging + handling
    net_profit: float         # profit in your pocket per unit
    margin_pct: float         # net_profit as a % of buy_price (ROI)
    net_margin_on_sale: float # net_profit as a % of resale_price

    @property
    def is_profitable(self) -> bool:
        return self.net_profit > 0


def compute_margin(buy_price: float, resale_price: float, fees: FeeModel) -> MarginResult:
    """Return the full profit breakdown for one unit.

    eBay's final value fee is charged on the TOTAL the buyer pays, which on a
    postage-included listing is the full resale price — so we apply it to
    resale_price, not just the item portion.
    """
    fv_fee = resale_price * fees.fv_fee_pct + fees.fv_fee_fixed
    selling_costs = fv_fee + fees.postage + fees.packaging + fees.handling

    net_profit = resale_price - selling_costs - buy_price
    margin_pct = (net_profit / buy_price * 100.0) if buy_price > 0 else 0.0
    net_margin_on_sale = (net_profit / resale_price * 100.0) if resale_price > 0 else 0.0

    return MarginResult(
        buy_price=round(buy_price, 2),
        resale_price=round(resale_price, 2),
        selling_costs=round(selling_costs, 2),
        net_profit=round(net_profit, 2),
        margin_pct=round(margin_pct, 1),
        net_margin_on_sale=round(net_margin_on_sale, 1),
    )
