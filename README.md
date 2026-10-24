# Furtumatic-V2

Retail-arbitrage tooling: find products sold cheaply at UK wholesalers/discount
retailers (e.g. Home Bargains) that resell for more on **eBay UK** after real
costs, and rank the winners.

👉 **The working tool lives in [`poc/`](poc/). Full docs: [`poc/README.md`](poc/README.md).**

---

## Run it locally (copy-paste)

```bash
# 1. Clone
git clone -b ccr-eb5c9319-f7d8ck https://github.com/Vinny010/Furtumatic-V2.git
cd Furtumatic-V2/poc

# 2. Install
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. See the profit maths immediately (no keys, no network needed)
python run_poc.py --demo

# 4. Real scan — needs free eBay dev keys (see below)
cp .env.example .env                 # then paste your eBay keys into .env
python run_poc.py coffee "olive oil" shampoo

# 5. If the wholesaler blocks plain requests, drive a real Chrome/Chromium:
pip install playwright && playwright install chromium
python run_poc.py --browser coffee
```

Output: a ranked table in the terminal **and** `opportunities.csv`.

## Get your free eBay API keys (5 min)

1. Go to <https://developer.ebay.com> → sign in → **create an app**.
2. Copy the **Production** `Client ID` (App ID) and `Client Secret` (Cert ID).
3. Paste them into `poc/.env`:
   ```
   EBAY_CLIENT_ID=your-id-here
   EBAY_CLIENT_SECRET=your-secret-here
   ```
That's all the Browse API needs. (For true *sold* / sell-through data later,
apply for the **Marketplace Insights API** in the same dashboard — approval
takes a few days.)

## Tune your numbers

Everything that decides profit is in `poc/.env` (or `poc/furtumatic/config.py`):

| Setting | Meaning | Default |
|---|---|---|
| `MIN_MARGIN_PCT` | only show ≥ this % ROI on buy price | `100` |
| `MIN_NET_PROFIT` | minimum £ profit per unit | `2.0` |
| `EBAY_FV_FEE_PCT` | eBay final value fee % | `0.128` |
| `EBAY_FV_FEE_FIXED` | eBay fixed fee per order (£) | `0.30` |
| `POSTAGE_COST` | what postage costs you (£) | `3.30` |
| `PACKAGING_COST` | packaging per order (£) | `0.30` |

**Set these to your real numbers** — the headline price gap is not profit, and
the defaults are generic.

## What it does / doesn't do

- ✅ Scrapes the wholesaler, matches to eBay UK (barcode-first), computes true
  net margin, filters + ranks winners → CSV.
- ❌ Does not buy stock or list on eBay yet — that's Stage 3 (eBay Sell API).

See [`poc/README.md`](poc/README.md) for the full breakdown, roadmap, and notes.
