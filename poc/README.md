# Furtumatic PoC — Wholesale → eBay UK Arbitrage Scanner

A proof-of-concept that finds products sold cheaply at a UK wholesaler/discount
retailer (Home Bargains in this PoC) that resell for materially more on eBay UK,
**after real costs** — and ranks the winners.

> This is **Stage 1 of 3**: the discovery engine. It proves where the money is.
> It does **not** buy stock or list on eBay (see [Roadmap](#roadmap)).

## How it works

```
Scrape wholesaler  ──►  extract title + price + EAN(barcode)
       │
       ▼
Match on eBay (Browse API)  ──►  prefer barcode, fall back to title
       │                         ► median resale price + competition
       ▼
Margin engine  ──►  net profit = resale − (eBay fee + postage + packaging) − buy
       │
       ▼
Filter (ROI ≥ 100% & net ≥ £2)  ──►  rank by profit  ──►  CSV + table
```

The barcode (EAN/GTIN) is the match key — fuzzy title matching alone is
unreliable, so the scanner prefers the barcode wherever the wholesaler exposes it.

## Quick start

```bash
cd poc
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# See the economics with zero setup (no network, no keys):
python run_poc.py --demo

# Real run (needs free eBay dev keys in .env):
cp .env.example .env         # then fill in EBAY_CLIENT_ID / EBAY_CLIENT_SECRET
python run_poc.py coffee "olive oil" shampoo
python run_poc.py --browser coffee     # if the site blocks plain requests
```

Run it on **your own machine/server** — cloud sandboxes (and this repo's CI
environment) often have `home.bargains` and eBay blocked at the network level.

## The two things that decide if this makes money

1. **Fees, not the headline gap.** A £2 → £6 item is *not* £4 profit. eBay takes
   ~12.8% + £0.30, postage is ~£3.30, packaging ~£0.30 — that £6 sale nets ≈
   **£1.63**, so at a £2 buy you'd *lose* money. Winners are usually higher-value
   or small/light items. All of this is tunable in `.env` / `config.py` — set
   them to YOUR real numbers.
2. **Sold price, not asking price.** The Browse API returns *active* listings
   (what people are *asking*). That an item is listed at £6 doesn't prove it
   sells. For true "fast moving" data (sell-through rate + sold prices) wire up
   the **Marketplace Insights API** (eBay must approve your app — apply on day
   one) or export **Terapeak** from Seller Hub. The hook is
   `EbayBrowseClient.get_sold_stats()`.

## Legal / policy notes (read these)

- **Retail arbitrage is legal.** Buying stock and reselling it is fine.
- eBay **bans retail dropshipping** — listing an item you don't own and ordering
  it from Home Bargains/Amazon to ship straight to the buyer when it sells.
  Accounts get suspended for this. The intended model here is: *scanner finds
  winners → you buy & hold the stock → then list what you physically have.*
- Use the **official eBay API** (this PoC does) to stay within eBay's terms.
- Home Bargains has no public API, so that side is scraping: respect
  `robots.txt`, rate-limit (`REQUEST_DELAY_S`), and don't hammer the site. If you
  get blocked, use `--browser` or route through a scraping provider.

## Project layout

```
poc/
├── run_poc.py            # CLI entry point
├── furtumatic/
│   ├── config.py         # thresholds + fee model (all the economics)
│   ├── wholesale.py      # Home Bargains scraper (JSON-LD → __NEXT_DATA__ → CSS)
│   ├── ebay_client.py    # eBay Browse API client (+ sold-data seam)
│   ├── margin.py         # net-profit maths
│   └── scanner.py        # orchestration + CSV/table output
├── requirements.txt
└── .env.example
```

## Roadmap

| Stage | What | Status |
|-------|------|--------|
| 1 | Discovery: scrape → match → margin → rank | ✅ this PoC |
| 2 | Real demand data (Marketplace Insights / Terapeak), price-history DB, more wholesalers (B&M, Aldi, ASDA), scheduling | next |
| 3 | Assisted listing via eBay Sell/Inventory API — on stock you actually hold | later |

## Tuning the scraper

`wholesale.py` parses structured data first (JSON-LD, then embedded JSON), with
CSS selectors as a fallback. The CSS selectors are generic placeholders — after
your first local run, inspect a real Home Bargains page and confirm/adjust them.
