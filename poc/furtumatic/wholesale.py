"""Wholesale-side scraper.

Target in the PoC: Home Bargains (home.bargains). The goal is to pull, for
each product on a search/category page: title, price, product URL, image, and
— most importantly — the EAN/barcode (GTIN), because the barcode is the only
reliable key for matching the SAME product on eBay. Fuzzy title matching alone
produces garbage.

Parsing strategy (most robust first), because retail sites change their HTML
often and render a lot client-side:
  1. JSON-LD  (<script type="application/ld+json">)  -> Product/Offer objects
  2. __NEXT_DATA__ / embedded JSON blobs              -> structured catalogue data
  3. CSS selectors on the rendered grid               -> last-resort fallback

NOTE: Home Bargains blocks plain datacentre requests fairly aggressively and
renders a lot with JavaScript. If requests+BeautifulSoup returns little, switch
HomeBargainsScraper(use_browser=True) to render with Playwright, or route via a
scraping provider (see README). Run this locally where the site is reachable —
cloud sandboxes often have the domain blocked.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

import requests
from bs4 import BeautifulSoup

from .config import ScannerConfig


@dataclass
class WholesaleProduct:
    title: str
    price: float
    url: str
    source: str = "home_bargains"
    ean: Optional[str] = None       # barcode / GTIN — the match key
    brand: Optional[str] = None
    image: Optional[str] = None
    raw: dict = field(default_factory=dict)


_PRICE_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)")


def _parse_price(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = _PRICE_RE.search(str(value).replace(",", ""))
    return float(m.group(1)) if m else None


def _first_gtin(obj: dict) -> Optional[str]:
    for key in ("gtin13", "gtin", "gtin12", "gtin14", "gtin8", "mpn", "sku"):
        val = obj.get(key)
        if val:
            return str(val).strip()
    return None


class HomeBargainsScraper:
    SEARCH_URL = "https://www.home.bargains/search?q={query}"

    def __init__(self, config: ScannerConfig, use_browser: bool = False):
        self.config = config
        self.use_browser = use_browser
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept-Language": "en-GB,en;q=0.9",
            }
        )

    # --- fetching -------------------------------------------------------
    def _fetch(self, url: str) -> str:
        if self.use_browser:
            return self._fetch_with_browser(url)
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _fetch_with_browser(self, url: str) -> str:
        # Lazy import so Playwright is only needed if you actually use it.
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=self.config.user_agent)
            page.goto(url, wait_until="networkidle", timeout=45000)
            html = page.content()
            browser.close()
            return html

    # --- parsing --------------------------------------------------------
    def _parse_jsonld(self, soup: BeautifulSoup) -> list[WholesaleProduct]:
        products: list[WholesaleProduct] = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            for node in _iter_product_nodes(data):
                offer = node.get("offers") or {}
                if isinstance(offer, list):
                    offer = offer[0] if offer else {}
                price = _parse_price(offer.get("price") or node.get("price"))
                if not price:
                    continue
                products.append(
                    WholesaleProduct(
                        title=(node.get("name") or "").strip(),
                        price=price,
                        url=node.get("url") or offer.get("url") or "",
                        ean=_first_gtin(node),
                        brand=_brand_name(node.get("brand")),
                        image=_first_image(node.get("image")),
                        raw=node,
                    )
                )
        return products

    def _parse_css(self, soup: BeautifulSoup) -> list[WholesaleProduct]:
        """Fallback. Selectors WILL need confirming against the live DOM —
        inspect a real page and adjust. Kept generic on purpose."""
        products: list[WholesaleProduct] = []
        cards = soup.select("[data-productid], .product, li.product-item, article")
        for card in cards:
            name_el = card.select_one(".productTitle, .product-name, h2, h3, [itemprop=name]")
            price_el = card.select_one(".price, .productPrice, [itemprop=price]")
            link_el = card.select_one("a[href]")
            price = _parse_price(price_el.get_text() if price_el else None)
            if not (name_el and price):
                continue
            products.append(
                WholesaleProduct(
                    title=name_el.get_text(strip=True),
                    price=price,
                    url=link_el["href"] if link_el else "",
                    raw={"html_fallback": True},
                )
            )
        return products

    def search(self, query: str) -> list[WholesaleProduct]:
        url = self.SEARCH_URL.format(query=requests.utils.quote(query))
        html = self._fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        products = self._parse_jsonld(soup)
        if not products:
            products = self._parse_css(soup)

        # De-dup by (title, price); keep first (usually best).
        seen, unique = set(), []
        for p in products:
            key = (p.title.lower(), round(p.price, 2))
            if key not in seen and p.title:
                seen.add(key)
                unique.append(p)
        time.sleep(self.config.request_delay_s)
        return unique

    def search_many(self, queries: Iterable[str]) -> list[WholesaleProduct]:
        out: list[WholesaleProduct] = []
        for q in queries:
            try:
                out.extend(self.search(q))
            except Exception as exc:  # keep going if one query fails
                print(f"[wholesale] '{q}' failed: {exc}")
        return out


def _iter_product_nodes(data) -> Iterable[dict]:
    """Walk arbitrary JSON-LD (graphs, lists, ItemList) yielding Product dicts."""
    if isinstance(data, list):
        for item in data:
            yield from _iter_product_nodes(item)
    elif isinstance(data, dict):
        if "@graph" in data:
            yield from _iter_product_nodes(data["@graph"])
        types = data.get("@type")
        types = types if isinstance(types, list) else [types]
        if "Product" in types:
            yield data
        if "itemListElement" in data:
            for el in data["itemListElement"]:
                item = el.get("item", el) if isinstance(el, dict) else el
                yield from _iter_product_nodes(item)


def _brand_name(brand) -> Optional[str]:
    if isinstance(brand, dict):
        return brand.get("name")
    return brand if isinstance(brand, str) else None


def _first_image(image) -> Optional[str]:
    if isinstance(image, list):
        return image[0] if image else None
    return image if isinstance(image, str) else None
