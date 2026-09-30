#!/usr/bin/env python3
"""
grid_dashboard.py — a live "window" for the sat-stacker paper grid.

Opens a browser dashboard (like a scanner console, but visual) showing:
  * big stat tiles: stack in BTC, sats vs HODL %, USD value, live price, regime
  * a PROFIT curve (your BTC stack over time)
  * a PRICE chart with green ▲ buys and red ▼ sells marked
  * a live trades table (newest first)
It auto-refreshes every 2s while the paper grid runs. No keys, no real money,
no orders sent — it paper-fills the grid against the price feed.

MODES
  --live            pull REAL prices from Binance public API (run this at home)
  --sim             synthetic live feed (test the window anywhere, no network)
  --snapshot FILE   run a quick sim and write a static dashboard HTML you can open

USAGE (at home)
  python grid_dashboard.py --live --symbol BTCUSDT --step 0.004
  # then open  http://localhost:8787  in your browser

Pure Python standard library. Reuses the grid engine from paper_grid.py.
"""
import argparse
import json
import math
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import importlib.util

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("paper_grid", os.path.join(_here, "paper_grid.py"))
paper_grid = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(paper_grid)
PaperGrid = paper_grid.PaperGrid

STATE = {"lock": threading.Lock()}


# ----------------------------------------------------------------- price feeds
def live_feed(symbol):
    while True:
        try:
            bid, ask = paper_grid.book_ticker(symbol)
            yield bid, ask
        except Exception as e:
            print("feed error:", e); time.sleep(2); continue


def sim_feed(mid=60000.0, seed=1, vol=0.0009):
    import random
    rng = random.Random(seed)
    while True:
        mid *= math.exp(rng.gauss(0, vol))
        half = mid * 0.00005
        yield mid - half, mid + half


# --------------------------------------------------------------------- engine
def engine(args):
    if args.live:
        ma, _ = paper_grid.seed_ma(args.symbol)
        feed = live_feed(args.symbol)
        bid, ask = next(feed)
    else:
        feed = sim_feed(vol=0.0011 if args.sim else 0.0009)
        bid, ask = next(feed)
        ma = 0.5 * (bid + ask) * 0.97          # sim: MA just below price (harvest regime)
    p0 = 0.5 * (bid + ask)
    g = PaperGrid(args.start_btc, p0, ma, args.step, args.unit, args.fee, args.trend_band)
    started = time.time()
    hist, trades = [], []

    def push():
        mid = 0.5 * (bid + ask)
        with STATE["lock"]:
            STATE["data"] = {
                "symbol": args.symbol, "mode": "LIVE" if args.live else "SIM",
                "started": started, "now": time.time(), "price": mid, "ma": g.ma,
                "bull": g.bull(mid), "btc": g.btc, "usd": g.usd,
                "start_btc": g.start_btc, "stack_btc": g.value_btc(mid),
                "sats_pct": (g.value_btc(mid) / g.start_btc - 1) * 100,
                "usd_val": g.btc * mid + g.usd, "buys": g.buys, "sells": g.sells,
                "hist": hist[-600:], "trades": trades[-40:],
            }

    push()
    tick = 0
    end = started + args.minutes * 60 if args.minutes else None
    while end is None or time.time() < end:
        bid, ask = next(feed)
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        acted = g.on_tick(bid, ask, ts)
        mid = 0.5 * (bid + ask)
        if acted:
            side, px, q = acted
            trades.append({"time": ts, "side": side, "price": round(px, 2),
                           "qty": round(q, 6), "stack": round(g.value_btc(mid), 6)})
        tick += 1
        if tick % 3 == 0 or acted:
            # x-axis uses tick count so the curve spreads in every mode
            hist.append([tick, round(mid, 2), round(g.value_btc(mid), 6)])
            push()
        time.sleep(0 if args.snapshot else args.poll)
        if args.snapshot and tick >= args.snapshot_ticks:
            break
    push()
    return g


# ------------------------------------------------------------------- web layer
PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sat Stacker — Grid Monitor</title>
<style>
:root{--bg:#0b0e13;--panel:#141a22;--line:#232c38;--txt:#e6edf3;--dim:#8a97a6;
--up:#26d07c;--down:#ff5c5c;--accent:#3aa0ff;--gold:#f2a900}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font:14px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
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
svg{width:100%;height:180px;display:block}
.pos{color:var(--up)}.neg{color:var(--down)}.gold{color:var(--gold)}
</style></head><body><div class="wrap">
<h1>◆ SAT STACKER — GRID MONITOR</h1>
<div class="sub" id="sub">connecting…</div>
<div class="tiles" id="tiles"></div>
<div class="charts">
 <div class="card"><h2>Profit — stack in BTC</h2><svg id="eq" viewBox="0 0 500 180" preserveAspectRatio="none"></svg></div>
 <div class="card"><h2>Price + trades</h2><svg id="px" viewBox="0 0 500 180" preserveAspectRatio="none"></svg></div>
</div>
<div class="card"><h2>Trades (newest first)</h2>
 <table><thead><tr><th>Time</th><th>Side</th><th>Price</th><th>Qty BTC</th><th>Stack BTC</th></tr></thead>
 <tbody id="tb"><tr><td colspan="5" style="color:var(--dim)">no fills yet…</td></tr></tbody></table></div>
</div>
<script>
const SNAPSHOT = __SNAPSHOT__;
function fmt(n,d){return Number(n).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d})}
function hms(s){s=Math.floor(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;
 return (h?h+'h ':'')+(m<10?'0':'')+m+'m '+(x<10?'0':'')+x+'s'}
function path(pts,vb){if(!pts.length)return'';const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
 const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
 const W=500,H=180,pad=6;const sx=v=>x1==x0?W/2:pad+(v-x0)/(x1-x0)*(W-2*pad);
 const sy=v=>y1==y0?H/2:H-pad-(v-y0)/(y1-y0)*(H-2*pad);
 return {d:pts.map((p,i)=>(i?'L':'M')+sx(p[0]).toFixed(1)+' '+sy(p[1]).toFixed(1)).join(' '),sx,sy}}
function draw(d){
 document.getElementById('sub').innerHTML=
   `${d.symbol} · <span class="badge" style="background:${d.mode=='LIVE'?'#123':'#332'};color:${d.mode=='LIVE'?'#3aa0ff':'#f2a900'}">${d.mode}</span>`
   +` · running ${hms(d.now-d.started)} · regime: `
   +`<b class="${d.bull?'gold':'pos'}">${d.bull?'BULL (selling paused)':'HARVEST'}</b>`;
 const sp=d.sats_pct, cls=sp>=0?'pos':'neg';
 const tiles=[
  ['Stack (BTC)',fmt(d.stack_btc,5),'gold'],
  ['Sats vs HODL',(sp>=0?'+':'')+fmt(sp,2)+'%',cls],
  ['Value (USD)','$'+fmt(d.usd_val,0),''],
  ['Price','$'+fmt(d.price,0),''],
  ['Trades',d.buys+d.sells+' ('+d.buys+'B/'+d.sells+'S)',''],
  ['BTC / USDC',fmt(d.btc,4)+' / $'+fmt(d.usd,0),''],
 ];
 document.getElementById('tiles').innerHTML=tiles.map(t=>
  `<div class="tile"><div class="k">${t[0]}</div><div class="v ${t[2]}">${t[1]}</div></div>`).join('');
 // equity curve
 const eq=path(d.hist.map(h=>[h[0],h[2]]));
 document.getElementById('eq').innerHTML= eq.d?
  `<path d="${eq.d}" fill="none" stroke="#f2a900" stroke-width="1.6"/>`+
  `<line x1="0" y1="${eq.sy(d.start_btc).toFixed(1)}" x2="500" y2="${eq.sy(d.start_btc).toFixed(1)}" stroke="#8a97a6" stroke-dasharray="3 3" stroke-width="1"/>`:'';
 // price + trade markers
 const pp=path(d.hist.map(h=>[h[0],h[1]]));
 let marks='';
 if(pp.d){d.trades.forEach(t=>{const h=d.hist.reduce((a,b)=>Math.abs(b[1]-t.price)<Math.abs(a[1]-t.price)?b:a,d.hist[0]);
   const x=pp.sx(h[0]),y=pp.sy(t.price);marks+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.6" fill="${t.side=='BUY'?'#26d07c':'#ff5c5c'}"/>`});}
 document.getElementById('px').innerHTML= pp.d?
  `<path d="${pp.d}" fill="none" stroke="#3aa0ff" stroke-width="1.4"/>`+marks:'';
 // trades table
 const tb=d.trades.slice().reverse().map(t=>
  `<tr><td>${t.time}</td><td class="${t.side=='BUY'?'pos':'neg'}">${t.side}</td>`+
  `<td>$${fmt(t.price,0)}</td><td>${fmt(t.qty,6)}</td><td>${fmt(t.stack,5)}</td></tr>`).join('');
 document.getElementById('tb').innerHTML=tb||'<tr><td colspan="5" style="color:var(--dim)">no fills yet…</td></tr>';
}
if(SNAPSHOT){draw(SNAPSHOT);}
else{async function tick(){try{const r=await fetch('/api/status');draw(await r.json())}catch(e){}}
 tick();setInterval(tick,2000);}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/api/status"):
            with STATE["lock"]:
                body = json.dumps(STATE.get("data", {})).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body)
        else:
            html = PAGE.replace("__SNAPSHOT__", "null").encode()
            self.send_response(200); self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(html))); self.end_headers()
            self.wfile.write(html)


def serve(port):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://localhost:{port}"
    print(f"  dashboard: {url}   (Ctrl-C to stop)")
    # auto-open the browser window so there's nothing to click
    try:
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--snapshot")
    ap.add_argument("--snapshot-ticks", type=int, default=2500)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--step", type=float, default=0.004)
    ap.add_argument("--unit", type=float, default=0.08)
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--trend-band", type=float, default=0.05)
    ap.add_argument("--start-btc", type=float, default=0.5)
    ap.add_argument("--poll", type=float, default=3.0)
    ap.add_argument("--minutes", type=float, default=0.0)
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    if not (args.live or args.sim or args.snapshot):
        args.sim = True

    if args.snapshot:
        engine(args)
        with STATE["lock"]:
            data = STATE["data"]
        html = PAGE.replace("__SNAPSHOT__", json.dumps(data))
        with open(args.snapshot, "w") as fh:
            fh.write(html)
        print(f"snapshot written -> {args.snapshot}  "
              f"({data['buys']+data['sells']} trades, stack {data['stack_btc']:.5f} BTC, "
              f"{data['sats_pct']:+.2f}% sats)")
        return
    serve(args.port)
    try:
        engine(args)
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
