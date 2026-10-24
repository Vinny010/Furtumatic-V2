"""eBay side — the RESALE price lookup.

Uses the official eBay **Browse API** (free, ToS-compliant, instant key). For a
given wholesale product we look eBay up, preferring the barcode (gtin) and
falling back to the title, and return a realistic resale price plus a rough
"how much competition" signal.

IMPORTANT distinction:
  * Browse API = LIVE/active listings (asking prices). Good for matching and a
    sanity-check price, but an asking price is not proof anything sells.
  * True "fast moving" (sell-through / sold prices) needs the **Marketplace
    Insights API** (eBay must approve your app — apply on day one) or Terapeak
    in Seller Hub. get_sold_stats() below is the seam where that plugs in.

Get free credentials at developer.ebay.com -> create an app -> use the
PRODUCTION Client ID + Client Secret. Put them in .env.
"""
from __future__ import annotations

import base64
import statistics
import time
from dataclasses import dataclass
from typing import Optional

import requests

from .config import ScannerConfig

_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_BROWSE_SEARCH = "https://api.ebay.com/buy/browse/v1/item_summary/search"
_SCOPE = "https://api.ebay.com/oauth/api_scope"


@dataclass
class EbayMatch:
    query_used: str
    matched_by: str          # "gtin" or "title"
    sample_size: int         # how many active listings we saw
    median_price: Optional[float]
    low_price: Optional[float]
    high_price: Optional[float]
    example_url: Optional[str] = None


class EbayBrowseClient:
    def __init__(self, config: ScannerConfig, client_id: str, client_secret: str):
        self.config = config
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    # --- auth -----------------------------------------------------------
    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        creds = f"{self._client_id}:{self._client_secret}".encode()
        headers = {
            "Authorization": "Basic " + base64.b64encode(creds).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = requests.post(
            _OAUTH_URL,
            headers=headers,
            data={"grant_type": "client_credentials", "scope": _SCOPE},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expiry = time.time() + int(payload.get("expires_in", 7200))
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "X-EBAY-C-MARKETPLACE-ID": self.config.marketplace_id,
            "Content-Type": "application/json",
        }

    # --- lookups --------------------------------------------------------
    def _search(self, params: dict) -> list[dict]:
        resp = requests.get(_BROWSE_SEARCH, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("itemSummaries", []) or []

    def find_resale_price(self, *, ean: Optional[str], title: str, limit: int = 30) -> Optional[EbayMatch]:
        """Look up a product; prefer the barcode, fall back to the title."""
        items, matched_by, query_used = [], "", ""

        if ean:
            items = self._search({"gtin": ean, "limit": limit})
            matched_by, query_used = "gtin", ean

        if not items and title:
            items = self._search({"q": title, "limit": limit})
            matched_by, query_used = "title", title

        if not items:
            return None

        prices = [
            float(i["price"]["value"])
            for i in items
            if i.get("price", {}).get("value")
        ]
        if not prices:
            return None

        return EbayMatch(
            query_used=query_used,
            matched_by=matched_by,
            sample_size=len(prices),
            median_price=round(statistics.median(prices), 2),
            low_price=round(min(prices), 2),
            high_price=round(max(prices), 2),
            example_url=items[0].get("itemWebUrl"),
        )

    # --- sold / sell-through seam --------------------------------------
    def get_sold_stats(self, *, ean: Optional[str], title: str) -> Optional[dict]:
        """Placeholder for REAL demand data (sold count + sell-through rate).

        Wire this to the Marketplace Insights API once eBay approves your app,
        or feed it a Terapeak CSV export. Until then the scanner uses active-
        listing competition as a weak proxy and clearly labels it as such.
        """
        return None
