#!/usr/bin/env python3
"""
sat_dashboard.py — ONE-FILE live paper-trading grid dashboard.

Everything is baked into this single file — nothing else to download.
No API keys. No real money. No orders are ever sent. It reads Binance's
PUBLIC price feed, paper-trades the sat-stacker grid against real live
moves, and opens a browser window showing your stack, trades and profit.

RUN (Windows):
    python sat_dashboard.py --live --symbol BTCUSDT --step 0.004
  then a browser window opens by itself at http://localhost:8787

  --sim   run with a fake feed (no network) just to see the window
"""
import argparse
import json
import math
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BINANCE = "https://api.binance.com"
STATE = {"lock": threading.Lock()}


# ------------------------------------------------------- live public data
def http_json(path):
    req = urllib.request.Request(BINANCE + path, headers={"User-Agent": "sat-dash"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def book_ticker(symbol):
    d = http_json(f"/api/v3/ticker/bookTicker?symbol={symbol}")
    return float(d["bidPrice"]), float(d["askPrice"])


def seed_ma(symbol, window=200):
    kl = http_json(f"/api/v3/klines?symbol={symbol}&interval=1d&limit={window}")
    closes = [float(k[4]) for k in kl]
    return sum(closes) / len(closes)


# ------------------------------------------------------------- grid engine
class PaperGrid:
    def __init__(self, start_btc, price, ma, step, unit_frac, fee, trend_band):
        self.start_btc = start_btc
        cap = start_btc * price
        self.btc = cap * 0.5 / price
        self.usd = cap * 0.5
        self.unit = cap * unit_frac
        self.ref = price
        self.ma = ma
        self.step = step
        self.fee = fee
        self.trend_band = trend_band
        self.buys = self.sells = 0

    def bull(self, price):
        return price > self.ma * (1 + self.trend_band)

    def value_btc(self, price):
        return self.btc + self.usd / price

    def on_tick(self, bid, ask):
        mid = 0.5 * (bid + ask)
        acted = None
        if mid <= self.ref * (1 - self.step) and self.usd >= self.unit:
            q = self.unit / ask
            self.btc += q * (1 - self.fee); self.usd -= self.unit
            self.ref = mid; self.buys += 1; acted = ("BUY", ask, q)
        elif mid >= self.ref * (1 + self.step) and self.btc * bid > self.unit \
                and not self.bull(mid):
            q = self.unit / bid
            self.btc -= q; self.usd += q * bid * (1 - self.fee)
            self.ref = mid; self.sells += 1; acted = ("SELL", bid, q)
        elif self.bull(mid):
            self.ref = mid
        return acted


# ----------------------------------------------------------------- feeds
def live_feed(symbol):
    while True:
        try:
            yield book_ticker(symbol)
        except Exception as e:
            print("  feed hiccup:", e); time.sleep(2)


def sim_feed(mid=60000.0, seed=1):
    import random
    rng = random.Random(seed)
    while True:
        mid *= math.exp(rng.gauss(0, 0.0011))
        half = mid * 0.00005
        yield mid - half, mid + half


# ----------------------------------------------------------------- engine
def engine(args):
    if args.live:
        print(f"  seeding 200-day regime average for {args.symbol} (live) ...")
        ma = seed_ma(args.symbol)
        feed = live_feed(args.symbol)
        bid, ask = next(feed)
    else:
        feed = sim_feed()
        bid, ask = next(feed)
        ma = 0.5 * (bid + ask) * 0.97
    p0 = 0.5 * (bid + ask)
    g = PaperGrid(args.start_btc, p0, ma, args.step, args.unit, args.fee, args.trend_band)
    started = time.time()
    hist, trades, tick = [], [], 0
    print(f"  START {args.symbol}  price ${p0:,.0f}  200dMA ${ma:,.0f}  "
          f"{'BULL (sells paused)' if g.bull(p0) else 'HARVEST'}")

    def push(mid):
        with STATE["lock"]:
            STATE["data"] = {
                "symbol": args.symbol, "mode": "LIVE" if args.live else "SIM",
                "started": started, "now": time.time(), "price": mid, "ma": g.ma,
                "bull": g.bull(mid), "btc": g.btc, "usd": g.usd,
                "start_btc": g.start_btc, "stack_btc": g.value_btc(mid),
                "sats_pct": (g.value_btc(mid) / g.start_btc - 1) * 100,
                "usd_val": g.btc * mid + g.usd, "buys": g.buys, "sells": g.sells,
                "hist": hist[-400:], "trades": trades[-40:],
            }
    push(p0)
    while True:
        bid, ask = next(feed)
        mid = 0.5 * (bid + ask)
        acted = g.on_tick(bid, ask)
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        if acted:
            side, px, q = acted
            trades.append({"time": ts, "side": side, "price": round(px, 2),
                           "qty": round(q, 6), "stack": round(g.value_btc(mid), 6)})
            print(f"  {ts} {side:4} {q:.6f} BTC @ ${px:,.0f}  "
                  f"stack={g.value_btc(mid):.5f} BTC ({g.sells}S/{g.buys}B)")
        tick += 1
        if tick % 3 == 0 or acted:
            hist.append([tick, round(mid, 2), round(g.value_btc(mid), 6)])
            push(mid)
        time.sleep(args.poll)


# ------------------------------------------------------------- web layer
PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sat Stacker — Live</title><style>
:root{--bg:#0b0e13;--panel:#141a22;--line:#232c38;--txt:#e6edf3;--dim:#8a97a6;
--up:#26d07c;--down:#ff5c5c;--price:#3aa0ff;--gold:#f2a900;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.4 var(--mono)}
.wrap{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:16px;margin:0 0 2px;letter-spacing:.5px}
.sub{color:var(--dim);font-size:12px;margin-bottom:14px}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px}
.tile .k{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.tile .v{font-size:22px;font-weight:700;margin-top:4px}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
@media(max-width:760px){.charts{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px}
.card h2{font-size:12px;color:var(--dim);margin:0 0 8px;text-transform:uppercase;letter-spacing:.5px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{color:var(--dim);text-align:right;font-weight:600;padding:6px 8px;border-bottom:1px solid var(--line)}
td{text-align:right;padding:5px 8px;border-bottom:1px solid #1b2330}
th:first-child,td:first-child{text-align:left}
svg{width:100%;height:180px;display:block}.pos{color:var(--up)}.neg{color:var(--down)}.gold{color:var(--gold)}
</style></head><body><div class="wrap">
<h1>◆ SAT STACKER — LIVE GRID MONITOR</h1><div class="sub" id="sub">connecting…</div>
<div class="tiles" id="tiles"></div>
<div class="charts">
 <div class="card"><h2>Profit — stack in BTC</h2><svg id="eq" viewBox="0 0 500 180" preserveAspectRatio="none"></svg></div>
 <div class="card"><h2>Price + trades</h2><svg id="px" viewBox="0 0 500 180" preserveAspectRatio="none"></svg></div></div>
<div class="card"><h2>Trades (newest first)</h2>
 <table><thead><tr><th>Time</th><th>Side</th><th>Price</th><th>Qty BTC</th><th>Stack BTC</th></tr></thead>
 <tbody id="tb"><tr><td colspan="5" style="color:var(--dim)">waiting for first fill…</td></tr></tbody></table></div>
</div><script>
function fmt(n,d){return Number(n).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d})}
function hms(s){s=Math.floor(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;
 return (h?h+'h ':'')+(m<10?'0':'')+m+'m '+(x<10?'0':'')+x+'s'}
function sc(pts){if(!pts.length)return null;const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
 const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);const W=500,H=180,p=6;
 const sx=v=>x1==x0?W/2:p+(v-x0)/(x1-x0)*(W-2*p),sy=v=>y1==y0?H/2:H-p-(v-y0)/(y1-y0)*(H-2*p);
 return {sx,sy,d:pts.map((q,i)=>(i?'L':'M')+sx(q[0]).toFixed(1)+' '+sy(q[1]).toFixed(1)).join(' ')}}
function draw(d){if(!d||!d.symbol)return;
 document.getElementById('sub').innerHTML=`${d.symbol} · <span class="badge" style="background:${d.mode=='LIVE'?'#123':'#332'};color:${d.mode=='LIVE'?'#3aa0ff':'#f2a900'}">${d.mode}</span> · running ${hms(d.now-d.started)} · regime: <b class="${d.bull?'gold':'pos'}">${d.bull?'BULL (selling paused)':'HARVEST'}</b>`;
 const sp=d.sats_pct,cls=sp>=0?'pos':'neg';
 const t=[['Stack (BTC)',fmt(d.stack_btc,5),'gold'],['Sats vs HODL',(sp>=0?'+':'')+fmt(sp,2)+'%',cls],
  ['Value (USD)','$'+fmt(d.usd_val,0),''],['Price','$'+fmt(d.price,0),''],
  ['Trades',d.buys+d.sells+' ('+d.buys+'B/'+d.sells+'S)',''],['BTC / USDC',fmt(d.btc,4)+' / $'+fmt(d.usd,0),'']];
 document.getElementById('tiles').innerHTML=t.map(x=>`<div class="tile"><div class="k">${x[0]}</div><div class="v ${x[2]}">${x[1]}</div></div>`).join('');
 const eq=sc(d.hist.map(h=>[h[0],h[2]]));
 document.getElementById('eq').innerHTML=eq?`<line x1="0" y1="${eq.sy(d.start_btc).toFixed(1)}" x2="500" y2="${eq.sy(d.start_btc).toFixed(1)}" stroke="#8a97a6" stroke-dasharray="3 3"/><path d="${eq.d}" fill="none" stroke="#f2a900" stroke-width="1.6"/>`:'';
 const pp=sc(d.hist.map(h=>[h[0],h[1]]));let m='';
 if(pp)d.trades.forEach(tr=>{const h=d.hist.reduce((a,b)=>Math.abs(b[1]-tr.price)<Math.abs(a[1]-tr.price)?b:a,d.hist[0]);m+=`<circle cx="${pp.sx(h[0]).toFixed(1)}" cy="${pp.sy(tr.price).toFixed(1)}" r="2.6" fill="${tr.side=='BUY'?'#26d07c':'#ff5c5c'}"/>`});
 document.getElementById('px').innerHTML=pp?`<path d="${pp.d}" fill="none" stroke="#3aa0ff" stroke-width="1.4"/>`+m:'';
 document.getElementById('tb').innerHTML=d.trades.slice().reverse().map(tr=>`<tr><td>${tr.time}</td><td class="${tr.side=='BUY'?'pos':'neg'}">${tr.side}</td><td>$${fmt(tr.price,0)}</td><td>${fmt(tr.qty,6)}</td><td>${fmt(tr.stack,5)}</td></tr>`).join('')||'<tr><td colspan="5" style="color:var(--dim)">waiting for first fill…</td></tr>';}
async function tick(){try{const r=await fetch('/api/status');draw(await r.json())}catch(e){}}
tick();setInterval(tick,2000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/api/status"):
            with STATE["lock"]:
                body = json.dumps(STATE.get("data", {})).encode()
            ct = "application/json"
        else:
            body = PAGE.encode(); ct = "text/html"
        self.send_response(200); self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--step", type=float, default=0.004)
    ap.add_argument("--unit", type=float, default=0.08)
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--trend-band", type=float, default=0.05)
    ap.add_argument("--start-btc", type=float, default=0.5)
    ap.add_argument("--poll", type=float, default=3.0)
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    if not (args.live or args.sim):
        args.live = True

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://localhost:{args.port}"
    print(f"\n  dashboard window: {url}   (leave this window open; Ctrl-C to stop)\n")
    try:
        import webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    except Exception:
        pass
    try:
        engine(args)
    except KeyboardInterrupt:
        print("\n  stopped.")


if __name__ == "__main__":
    main()
