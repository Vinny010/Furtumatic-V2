# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "pandas>=2.0", "pyarrow>=14", "scipy>=1.10", "lightgbm>=4.0", "scikit-learn>=1.3"]
# ///
"""AlphaLab-lite: machine alpha discovery on GitHub-hosted market data, validated the way a fund would.
Stages: load -> features -> genetic-programming alpha search (SEARCH period only) -> holdout evaluation
(never touched during search) -> Deflated Sharpe + PBO (CSCV) -> LightGBM walk-forward -> prop-firm 30-day sim.
Usage: uv run alphalab.py [--pop 300] [--gens 25] [--symbols XAUUSD,BTCUSD,EURUSD,GBPUSD,USDJPY] [--quick]"""
import argparse, os, sys, time, json, math, random, itertools, glob, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr, norm, skew, kurtosis
from multiprocessing import Pool
warnings.filterwarnings("ignore")
ROOT=os.path.dirname(os.path.abspath(__file__))
MKT=os.environ.get("ALPHALAB_DATA","/tmp/claude-0/-home-user-Furtumatic-V2/b2f13734-927b-54b6-8ba1-3eddf46c40dc/scratchpad/mkt")
CACHE=os.path.join(ROOT,"cache"); os.makedirs(CACHE,exist_ok=True)
OUT=os.path.join(ROOT,"results"); os.makedirs(OUT,exist_ok=True)
H=8                       # primary horizon in M15 bars (2 hours)
BARS_PER_YEAR=252*24*4    # M15 bars in a trading year (approx, 24h markets)
def log(*a):
    print(time.strftime("%H:%M:%S"),*a,flush=True)
# ------------------------------------------------------------------ data
def load_xau():
    fs=sorted(glob.glob(os.path.join(MKT,"XAUUSD_Dataset","XAUUSD_M1_*.csv")))
    parts=[]
    for f in fs:
        d=pd.read_csv(f,usecols=["timestamp","open_bid","high_bid","low_bid","close_bid","open_ask","high_ask","low_ask","close_ask","volume_bid","volume_ask"])
        parts.append(d)
    d=pd.concat(parts,ignore_index=True); d["timestamp"]=pd.to_datetime(d["timestamp"]); d=d.set_index("timestamp").sort_index()
    d=d[~d.index.duplicated()]
    mid=pd.DataFrame({"open":(d.open_bid+d.open_ask)/2,"high":(d.high_bid+d.high_ask)/2,"low":(d.low_bid+d.low_ask)/2,"close":(d.close_bid+d.close_ask)/2,
                      "spread":d.close_ask-d.close_bid,"vb":d.volume_bid,"va":d.volume_ask})
    b=mid.resample("15min").agg({"open":"first","high":"max","low":"min","close":"last","spread":"mean","vb":"sum","va":"sum"}).dropna(subset=["close"])
    b["vol"]=b.vb+b.va; b["imb"]=(b.vb-b.va)/(b.vb+b.va+1e-12); b=b.drop(columns=["vb","va"])
    b=b[b.vol>0]; return b
def load_btc():
    f=os.path.join(MKT,"bitstamp-btcusd-minute-data","data","historical","btcusd_bitstamp_1min_2012-2025.csv.gz")
    d=pd.read_csv(f); u=os.path.join(MKT,"bitstamp-btcusd-minute-data","data","updates","btcusd_bitstamp_1min_latest.csv")
    if os.path.exists(u): d=pd.concat([d,pd.read_csv(u)],ignore_index=True)
    d["timestamp"]=pd.to_datetime(d["timestamp"],unit="s"); d=d.set_index("timestamp").sort_index(); d=d[~d.index.duplicated()]
    d=d[d.index>="2017-01-01"]
    b=d.resample("15min").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna(subset=["close"]).rename(columns={"volume":"vol"})
    b["spread"]=np.nan; b["imb"]=np.nan; b=b[b.vol>0]; return b
def load_fx(sym):
    f=os.path.join(MKT,"historical-data",sym,f"{sym}m15.csv"); d=pd.read_csv(f)
    d["Date"]=pd.to_datetime(d["Date"]); d=d.set_index("Date").sort_index(); d=d[~d.index.duplicated()]
    scale={"XAUUSD":100.0,"USDJPY":1000.0}.get(sym,100000.0)
    b=pd.DataFrame({"open":d.open/scale,"high":d.high/scale,"low":d.low/scale,"close":d.close/scale,"vol":d.tick_volume.astype(float)})
    b["spread"]=np.nan; b["imb"]=np.nan; return b
# round-trip cost as a fraction of price when the data has no spread column
FIXED_RT_COST={"BTCUSD":0.0006,"EURUSD":0.00011,"GBPUSD":0.00013,"USDJPY":0.00011,"XAUUSD":0.00025}
def load_symbol(sym):
    p=os.path.join(CACHE,f"{sym}_m15.parquet")
    if os.path.exists(p): return pd.read_parquet(p)
    b={"XAUUSD":load_xau,"BTCUSD":load_btc}.get(sym,lambda: load_fx(sym))()
    b.to_parquet(p); return b
# ------------------------------------------------------------------ features
def rsi(c,n):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean(); return 100-100/(1+up/(dn+1e-12))
def features(b):
    c,h,l,o,v=b.close,b.high,b.low,b.open,b.vol; F=pd.DataFrame(index=b.index); r1=np.log(c).diff()
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); atr=tr.ewm(alpha=1/14,adjust=False).mean(); F["atr_pct"]=atr/c
    for k in (1,2,4,8,16,32,96,480): F[f"ret_{k}"]=np.log(c/c.shift(k))/(F.atr_pct*math.sqrt(k)+1e-12)
    for k in (20,50,100,200): F[f"z_{k}"]=(c-c.rolling(k).mean())/(c.rolling(k).std()+1e-12)
    F["rsi2"]=rsi(c,2)/100-0.5; F["rsi14"]=rsi(c,14)/100-0.5
    F["atr_rank"]=F.atr_pct.rolling(500).rank(pct=True)-0.5
    F["volratio"]=r1.rolling(12).std()/(r1.rolling(96).std()+1e-12)
    for k in (20,50,100): F[f"don_{k}"]=(c-l.rolling(k).min())/(h.rolling(k).max()-l.rolling(k).min()+1e-12)-0.5
    F["barpos"]=(c-l)/(h-l+1e-12)-0.5; F["body"]=(c-o)/(atr+1e-12)
    hr=b.index.hour; F["hour_sin"]=np.sin(2*np.pi*hr/24); F["hour_cos"]=np.cos(2*np.pi*hr/24); F["dow"]=(b.index.dayofweek-2)/2.0
    F["asia"]=((hr>=0)&(hr<7)).astype(float); F["london"]=((hr>=7)&(hr<16)).astype(float); F["ny"]=((hr>=13)&(hr<21)).astype(float)
    F["vol_z"]=(v-v.rolling(96).mean())/(v.rolling(96).std()+1e-12)
    F["amihud"]=(r1.abs()/(v+1e-9)).rolling(16).mean(); F["amihud"]=F.amihud/(F.amihud.rolling(500).median()+1e-12)-1
    cov=r1.rolling(32).cov(r1.shift()); F["roll"]=2*np.sqrt((-cov).clip(lower=0))/(F.atr_pct+1e-12)
    sgn=np.sign(r1); runs=sgn.groupby((sgn!=sgn.shift()).cumsum()).cumcount()+1; F["runlen"]=(runs*sgn).clip(-8,8)/8
    F["vr16"]=np.log(c/c.shift(16)).rolling(200).var()/(16*r1.rolling(200).var()+1e-12)-1
    up=h.diff(); dn=-l.diff(); pdm=((up>dn)&(up>0))*up; ndm=((dn>up)&(dn>0))*dn
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/(atr+1e-12); ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/(atr+1e-12)
    F["adx"]=((pdi-ndi).abs()/(pdi+ndi+1e-12)).ewm(alpha=1/14,adjust=False).mean()-0.25; F["dmi"]=(pdi-ndi)/100
    ema=c.ewm(span=200,adjust=False).mean(); F["ema_slope"]=(ema-ema.shift(8))/(atr+1e-12)
    day=b.index.normalize(); dclose=c.groupby(day).transform("last").shift(96); F["gap_prevday"]=np.log(c/dclose.reindex(b.index).ffill())/(F.atr_pct*10+1e-12)
    F["dom"]=(b.index.day-15)/15.0
    if b.spread.notna().any(): F["spread_z"]=(b.spread-b.spread.rolling(96).mean())/(b.spread.rolling(96).std()+1e-12)
    if b.imb.notna().any():
        F["imb4"]=b.imb.rolling(4).mean(); F["imb16"]=b.imb.rolling(16).mean(); F["imb_ret_corr"]=r1.rolling(32).corr(b.imb)
    F=F.replace([np.inf,-np.inf],np.nan)
    return F
def targets(b,F):
    c=b.close; T={}
    for h in (4,8,16): T[f"y{h}"]=np.log(c.shift(-h)/c)/(F.atr_pct*math.sqrt(h)+1e-12)   # forward return in ATR units
    return pd.DataFrame(T)
def cost_rt(b,sym):
    if b.spread.notna().any(): return ((b.spread*1.5)/b.close).fillna(FIXED_RT_COST[sym])   # spread + 50% slippage
    return pd.Series(FIXED_RT_COST[sym],index=b.index)
# ------------------------------------------------------------------ genetic programming
UN=["neg","abs","sign","tanh","rank200","lag1","lag4","lag16","rmean4","rmean16","rmean64","rstd16","delta4","delta16"]
BI=["add","sub","mul","div","max","min","gt"]
class GP:
    def __init__(self,cols,rng): self.cols=cols; self.rng=rng
    def rand(self,d=0):
        r=self.rng.random()
        if d>=4 or r<0.25: return self.rng.choice(self.cols) if self.rng.random()<0.9 else ("c",round(self.rng.uniform(-2,2),2))
        if r<0.6: return (self.rng.choice(UN),self.rand(d+1))
        return (self.rng.choice(BI),self.rand(d+1),self.rand(d+1))
    def size(self,f): return 1 if isinstance(f,str) else (1 if f[0]=="c" else 1+sum(self.size(x) for x in f[1:]))
    def s(self,f):
        if isinstance(f,str): return f
        if f[0]=="c": return str(f[1])
        return f"{f[0]}({','.join(self.s(x) for x in f[1:])})"
    def mutate(self,f,d=0):
        if self.rng.random()<0.15 or isinstance(f,str) or f[0]=="c": return self.rand(d)
        i=self.rng.randrange(1,len(f)); g=list(f); g[i]=self.mutate(f[i],d+1); return tuple(g)
    def sub(self,f):
        nodes=[]; 
        def walk(x,path):
            nodes.append(path)
            if not isinstance(x,str) and x[0]!="c":
                for i in range(1,len(x)): walk(x[i],path+(i,))
        walk(f,()); return self.rng.choice(nodes)
    def get(self,f,p):
        for i in p: f=f[i]
        return f
    def put(self,f,p,g):
        if not p: return g
        l=list(f); l[p[0]]=self.put(f[p[0]],p[1:],g); return tuple(l)
    def cross(self,a,b): return self.put(a,self.sub(a),self.get(b,self.sub(b)))
def ev(f,F):
    if isinstance(f,str): return F[f].values
    if f[0]=="c": return np.full(len(F),f[1])
    op=f[0]; a=ev(f[1],F)
    if op in BI:
        b=ev(f[2],F)
        if op=="add": return a+b
        if op=="sub": return a-b
        if op=="mul": return a*b
        if op=="div": return a/np.where(np.abs(b)<1e-6,np.nan,b)
        if op=="max": return np.maximum(a,b)
        if op=="min": return np.minimum(a,b)
        if op=="gt": return (a>b).astype(float)
    s=pd.Series(a)
    if op=="neg": return -a
    if op=="abs": return np.abs(a)
    if op=="sign": return np.sign(a)
    if op=="tanh": return np.tanh(a)
    if op=="rank200": return (s.rolling(200).rank(pct=True)-0.5).values
    if op.startswith("lag"): return s.shift(int(op[3:])).values
    if op.startswith("rmean"): return s.rolling(int(op[5:])).mean().values
    if op.startswith("rstd"): return s.rolling(int(op[4:])).std().values
    if op.startswith("delta"): k=int(op[5:]); return (s-s.shift(k)).values
    raise ValueError(op)
def ic_by_year(a,y,years):
    out=[]
    for yr in np.unique(years):
        m=(years==yr)&np.isfinite(a)&np.isfinite(y)
        if m.sum()<1500: continue
        r=spearmanr(a[m],y[m]).correlation; out.append(0.0 if not np.isfinite(r) else r)
    return np.array(out)
def fitness(f,gp,F,y,years):
    try: a=ev(f,F)
    except Exception: return -9,None
    if not np.isfinite(a).any() or np.nanstd(a)<1e-9: return -9,None
    ics=ic_by_year(a,y,years)
    if len(ics)<3: return -9,None
    s=np.sign(ics.mean()); fit=s*ics.mean()-0.5*ics.std()-0.0015*gp.size(f)
    return fit,ics*s
def gp_search(args):
    sym,pop,gens,seed=args
    F=pd.read_parquet(os.path.join(CACHE,f"{sym}_F.parquet")); T=pd.read_parquet(os.path.join(CACHE,f"{sym}_T.parquet")); meta=json.load(open(os.path.join(CACHE,f"{sym}_meta.json")))
    search=F.index<pd.Timestamp(meta["holdout_start"]); Fs=F[search].reset_index(drop=True); ys=T[search][f"y{H}"].values; years=(F.index[search].year*2+(F.index[search].month>6)).values   # half-year blocks
    rng=random.Random(seed); gp=GP(list(F.columns),rng); seen={}; hall=[]
    def score(f):
        k=gp.s(f)
        if k in seen: return seen[k]
        fit,ics=fitness(f,gp,Fs,ys,years); seen[k]=(fit,ics); return seen[k]
    P=[gp.rand() for _ in range(pop)]; t0=time.time()
    for g in range(gens):
        scored=[(score(f)[0],f) for f in P]; scored.sort(key=lambda x:-x[0])
        hall=sorted(hall+scored[:20],key=lambda x:-x[0]); hall=list({gp.s(f):(s,f) for s,f in hall}.values()); hall.sort(key=lambda x:-x[0]); hall=hall[:60]
        if g%5==0 or g==gens-1: log(f"  [{sym}] gen {g} best {scored[0][0]:.4f} ({gp.s(scored[0][1])[:70]}) trials={len(seen)} {time.time()-t0:.0f}s")
        elite=[f for _,f in scored[:max(2,pop//10)]]; newP=elite[:]
        while len(newP)<pop:
            def tour(): return max(rng.sample(scored,5),key=lambda x:x[0])[1]
            r=rng.random()
            child=gp.cross(tour(),tour()) if r<0.6 else (gp.mutate(tour()) if r<0.9 else gp.rand())
            if gp.size(child)<=25: newP.append(child)
        P=newP
    res=[]
    for s,f in hall: fit,ics=seen[gp.s(f)]; res.append({"formula":gp.s(f),"tree":f,"fit":float(fit),"ic_years":[float(x) for x in ics] if ics is not None else []})
    return sym,res,len(seen)
# ------------------------------------------------------------------ evaluation
def backtest(alpha,y,cost,zwin=500,thr=1.0,h=H):
    """position = sign of rolling z-score of alpha when |z|>thr, held h bars, non-overlapping. returns per-trade net return in ATR units and bar indexes."""
    s=pd.Series(alpha); z=((s-s.rolling(zwin).mean())/(s.rolling(zwin).std()+1e-12)).values
    n=len(z); i=zwin; pnl=[]; idx=[]
    while i<n-h:
        if np.isfinite(z[i]) and abs(z[i])>thr and np.isfinite(y[i]):
            pos=np.sign(z[i]); pnl.append(pos*y[i]-cost[i]); idx.append(i); i+=h
        else: i+=1
    return np.array(pnl),np.array(idx)
def sharpe(pnl,trades_per_year):
    if len(pnl)<10 or pnl.std()==0: return 0.0
    return float(pnl.mean()/pnl.std()*math.sqrt(trades_per_year))
def deflated_sharpe(sr,n_trials,T,sk,ku,sr_var):
    # Bailey & Lopez de Prado (2014). sr and sr0 in per-trade units (not annualised)
    e=math.e; z1=norm.ppf(1-1/n_trials); z2=norm.ppf(1-1/(n_trials*e)); gamma=0.5772
    sr0=math.sqrt(sr_var)*((1-gamma)*z1+gamma*z2)
    denom=math.sqrt(max(1e-12,1-sk*sr+(ku-1)/4*sr*sr))
    return float(norm.cdf((sr-sr0)*math.sqrt(max(T-1,1))/denom)),float(sr0)
def pbo_cscv(M,S=8):
    """M: (T x N) matrix of per-period returns for N trials. Probability of backtest overfitting via CSCV."""
    T,N=M.shape; blocks=np.array_split(np.arange(T),S); logits=[]
    for comb in itertools.combinations(range(S),S//2):
        tr=np.concatenate([blocks[i] for i in comb]); te=np.concatenate([blocks[i] for i in range(S) if i not in comb])
        def sr(X): m=X.mean(0); s=X.std(0)+1e-12; return m/s
        best=np.argmax(sr(M[tr])); r=sr(M[te]); rank=(r<r[best]).mean()   # relative rank of IS-best in OOS
        rank=min(max(rank,1e-6),1-1e-6); logits.append(math.log(rank/(1-rank)))
    logits=np.array(logits); return float((logits<=0).mean())
def prop_sim(daily_pnl_frac,target=0.10,daily_cap=0.05,dd_cap=0.10,window=30):
    """daily_pnl_frac: Series of daily P/L as fraction of equity. Simulate every rolling 30-calendar-day evaluation."""
    days=daily_pnl_frac.index; results=[]
    for start in range(0,len(days)-window):
        eq=1.0; peak=1.0; passed=False; failed=False
        for d in daily_pnl_frac.values[start:start+window]:
            if d<=-daily_cap: failed=True; break
            eq*=(1+d); peak=max(peak,eq)
            if eq<=1-dd_cap: failed=True; break
            if eq>=1+target: passed=True; break
        results.append(1 if passed else (0 if failed else 0))
    return float(np.mean(results)) if results else 0.0, len(results)
def evaluate(symbols,gp_results,n_trials_total):
    lines=["# AlphaLab-lite results","",f"Generated {time.strftime('%Y-%m-%d %H:%M')} UTC. Horizon {H} bars (M15). Total formulas tried across all symbols: {n_trials_total:,}.",""]
    alphas_md=["# Surviving alphas",""]; survivors={}; all_trade_series={}
    for sym in symbols:
        F=pd.read_parquet(os.path.join(CACHE,f"{sym}_F.parquet")); T=pd.read_parquet(os.path.join(CACHE,f"{sym}_T.parquet")); meta=json.load(open(os.path.join(CACHE,f"{sym}_meta.json")))
        cost=pd.read_parquet(os.path.join(CACHE,f"{sym}_cost.parquet"))["cost"]; y=T[f"y{H}"].values; atr=F["atr_pct"].values
        cost_atr=(cost.values/(atr*math.sqrt(H)+1e-12))   # round-trip cost in the same ATR units as y
        hold=F.index>=pd.Timestamp(meta["holdout_start"]); search=~hold
        lines.append(f"## {sym}"); lines.append(f"bars {len(F):,} | search {F.index[search][0].date()}..{F.index[search][-1].date()} | holdout {F.index[hold][0].date()}..{F.index[hold][-1].date()} | median round-trip cost {np.nanmedian(cost.values)*1e4:.1f} bp = {np.nanmedian(cost_atr):.2f} ATR-units of the {H}-bar move")
        res=[r for r in gp_results[sym] if r["ic_years"]]; Fr=F.reset_index(drop=True); years=(F.index.year*2+(F.index.month>6)).values
        # trial matrix for PBO on the SEARCH period: top 40 hall-of-fame formulas
        rows=[]
        for r in res[:40]:
            try: a=ev(r["tree"],Fr)
            except Exception: continue
            pnl,idx=backtest(a,y,cost_atr); 
            if len(idx)<50: continue
            ser=pd.Series(pnl,index=F.index[idx]); rows.append(ser)
        if rows:
            M=pd.concat(rows,axis=1).fillna(0.0); Ms=M[M.index<pd.Timestamp(meta["holdout_start"])].resample("W").sum()
            pbo=pbo_cscv(Ms.values) if Ms.shape[0]>16 and Ms.shape[1]>=5 else float("nan")
        else: pbo=float("nan")
        rb=[]
        for sd in range(5):
            rp,ri=backtest(np.random.default_rng(sd).standard_normal(len(y)),y,cost_atr); hm=ri>=np.argmax(hold); rp=rp[hm]
            tpy=len(rp)/max(1e-9,(F.index[hold][-1]-F.index[hold][0]).days/365.25); rb.append(sharpe(rp,1)*math.sqrt(max(tpy,1)))
        lines.append(f"Random-entry baseline on holdout (same costs, 5 seeds): annualised Sharpe {np.mean(rb):.2f} +- {np.std(rb):.2f}. Anything near this number is cost drag, not signal.")
        lines.append(f"PBO (probability of backtest overfitting, CSCV over top {len(rows)} trials, weekly): **{pbo:.2f}**  (0.5 = pure luck, <0.2 is what you want)")
        lines.append(""); lines.append("| rank | formula | search IC/half-yr | holdout IC/half-yr | holdout trades | holdout Sharpe (ann.) | deflated SR p | verdict |"); lines.append("|---|---|---|---|---|---|---|---|")
        sr_list=[]
        for r in res[:40]:
            try: a=ev(r["tree"],Fr)
            except Exception: continue
            pnl,idx=backtest(a,y,cost_atr); hmask=idx>=np.argmax(hold) if hold.any() else np.zeros(len(idx),bool)
            ph=pnl[hmask]; sr_list.append(sharpe(ph,1) if len(ph)>10 else 0.0)
        sr_var=float(np.var(sr_list)) if len(sr_list)>1 else 1e-4
        for k,r in enumerate(res[:15]):
            try: a=ev(r["tree"],Fr)
            except Exception: continue
            ics_h=ic_by_year(a[hold],y[hold],years[hold]); ics_s=np.array(r["ic_years"])
            sgn=1.0 if ics_s.mean()>=0 else -1.0
            pnl,idx=backtest(sgn*a,y,cost_atr); hmask=idx>=np.argmax(hold); ph=pnl[hmask]
            tpy=len(ph)/max(1e-9,(F.index[hold][-1]-F.index[hold][0]).days/365.25)
            sr_t=sharpe(ph,1) if len(ph)>10 else 0.0; sr_ann=sr_t*math.sqrt(max(tpy,1))
            dsr,sr0=deflated_sharpe(sr_t,max(n_trials_total,2),len(ph),float(skew(ph)) if len(ph)>10 else 0,float(kurtosis(ph,fisher=False)) if len(ph)>10 else 3,max(sr_var,1e-6))
            ok=(len(ics_h)>0 and (sgn*ics_h).mean()>0.005 and (sgn*ics_h).min()>-0.005 and sr_ann>0.5 and dsr>0.95)
            verdict="**SURVIVES**" if ok else ("holdout positive but not significant" if sr_ann>0 else "fails holdout")
            hm=(sgn*ics_h).mean() if len(ics_h) else float("nan"); hmin=(sgn*ics_h).min() if len(ics_h) else float("nan")
            lines.append(f"| {k+1} | `{r['formula'][:60]}` | {ics_s.mean():+.3f} (min {ics_s.min():+.3f}) | {hm:+.3f} (min {hmin:+.3f}) | {len(ph)} | {sr_ann:.2f} | {dsr:.3f} | {verdict} |")
            if ok:
                survivors.setdefault(sym,[]).append(r["formula"]); all_trade_series[(sym,r["formula"])]=pd.Series(ph,index=F.index[idx[hmask]])
                alphas_md+= [f"## {sym}: `{r['formula']}`",f"- search IC by half-year: {', '.join(f'{x:+.3f}' for x in ics_s)}",f"- holdout IC by half-year: {', '.join(f'{x:+.3f}' for x in sgn*ics_h)}",f"- holdout trades {len(ph)}, annualised Sharpe {sr_ann:.2f}, deflated-Sharpe probability {dsr:.3f}, PBO (symbol-level) {pbo:.2f}",""]
        lines.append("")
    return lines,alphas_md,survivors,all_trade_series
def lgbm_walkforward(sym):
    import lightgbm as lgb
    F=pd.read_parquet(os.path.join(CACHE,f"{sym}_F.parquet")); T=pd.read_parquet(os.path.join(CACHE,f"{sym}_T.parquet")); cost=pd.read_parquet(os.path.join(CACHE,f"{sym}_cost.parquet"))["cost"]
    y=T[f"y{H}"]; atr=F["atr_pct"]; cost_atr=cost/(atr*math.sqrt(H)+1e-12); X=F.fillna(0.0)
    months=pd.period_range(F.index[0],F.index[-1],freq="M"); preds=pd.Series(np.nan,index=F.index); imp=None
    for i in range(12,len(months)):
        tr=(F.index>=months[i-12].start_time)&(F.index<(months[i].start_time-pd.Timedelta(hours=2*H*0.25)))   # embargo 2 horizons
        te=(F.index>=months[i].start_time)&(F.index<months[i].end_time)
        if tr.sum()<5000 or te.sum()<100: continue
        m=lgb.LGBMRegressor(n_estimators=200,learning_rate=0.03,num_leaves=15,min_child_samples=200,subsample=0.7,subsample_freq=1,colsample_bytree=0.7,reg_lambda=5.0,verbose=-1,n_jobs=1)
        ok=np.isfinite(y.values)&tr; m.fit(X[ok],y[ok]); preds[te]=m.predict(X[te])
        imp=m.feature_importances_ if imp is None else imp+m.feature_importances_
    m=preds.notna()&y.notna(); ic=spearmanr(preds[m],y[m]).correlation
    icy=[(yr,spearmanr(preds[m&(F.index.year==yr)],y[m&(F.index.year==yr)]).correlation) for yr in sorted(set(F.index[m].year))]
    sw={}
    for thr in (1.0,1.5,2.0,2.5):
        pnl,idx=backtest(preds.fillna(0).values,y.values,cost_atr.values,zwin=500,thr=thr)
        tpy=len(pnl)/max(1e-9,(F.index[-1]-F.index[0]).days/365.25); sw[thr]=(int(len(pnl)),float(sharpe(pnl,1)*math.sqrt(max(tpy,1))) if len(pnl)>10 else 0.0,float(pnl.mean()) if len(pnl) else 0.0)
    pnl,idx=backtest(preds.fillna(0).values,y.values,cost_atr.values,zwin=500,thr=1.0); sr=sw[1.0][1]
    top=sorted(zip(X.columns,imp if imp is not None else np.zeros(len(X.columns))),key=lambda x:-x[1])[:8]
    return {"sym":sym,"ic":float(ic),"ic_years":[(int(a),float(b)) for a,b in icy],"trades":int(len(pnl)),"sharpe":float(sr),"acc":float((np.sign(preds[m])==np.sign(y[m])).mean()),"sweep":sw,"top":[(a,int(b)) for a,b in top]}
# ------------------------------------------------------------------ main
def prep(sym,quick):
    t0=time.time(); b=load_symbol(sym)
    if quick: b=b.iloc[-60000:]
    F=features(b); T=targets(b,F); c=cost_rt(b,sym)
    keep=F.notna().mean(axis=1)>0.9; F=F[keep]; T=T[keep]; c=c[keep]
    n=len(F); holdout_start=str(F.index[int(n*0.7)])   # last 30% of the data is never seen by the search
    F.to_parquet(os.path.join(CACHE,f"{sym}_F.parquet")); T.to_parquet(os.path.join(CACHE,f"{sym}_T.parquet")); pd.DataFrame({"cost":c}).to_parquet(os.path.join(CACHE,f"{sym}_cost.parquet"))
    json.dump({"holdout_start":holdout_start,"rows":n,"start":str(F.index[0]),"end":str(F.index[-1]),"features":list(F.columns)},open(os.path.join(CACHE,f"{sym}_meta.json"),"w"))
    log(f"prepared {sym}: {n:,} M15 bars {F.index[0].date()}..{F.index[-1].date()}, {F.shape[1]} features, holdout from {holdout_start[:10]} ({time.time()-t0:.0f}s)")
    return sym
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--pop",type=int,default=300); ap.add_argument("--gens",type=int,default=25)
    ap.add_argument("--symbols",default="XAUUSD,BTCUSD,EURUSD,GBPUSD,USDJPY"); ap.add_argument("--quick",action="store_true"); ap.add_argument("--skip-lgbm",action="store_true")
    a=ap.parse_args(); symbols=a.symbols.split(","); t0=time.time()
    log("STAGE 1: data + features"); 
    with Pool(min(4,len(symbols))) as pool: pool.starmap(prep,[(s,a.quick) for s in symbols])
    log(f"STAGE 2: genetic alpha search pop={a.pop} gens={a.gens} (search period only)")
    with Pool(min(4,len(symbols))) as pool: out=pool.map(gp_search,[(s,a.pop,a.gens,100+i) for i,s in enumerate(symbols)])
    gp_results={s:r for s,r,_ in out}; n_trials=sum(n for _,_,n in out); log(f"  total unique formulas evaluated: {n_trials:,}")
    log("STAGE 3: holdout evaluation, deflated Sharpe, PBO")
    lines,alphas_md,survivors,trades=evaluate(symbols,gp_results,n_trials)
    if not a.skip_lgbm:
        log("STAGE 4: LightGBM walk-forward (train 12 months, test next month, rolling)")
        with Pool(min(4,len(symbols))) as pool: lg=pool.map(lgbm_walkforward,symbols)
        lines+=["## LightGBM walk-forward (all features, monthly retrain, out-of-sample only)","","| symbol | OOS rank IC | IC by year | directional acc | trades @z>1 | Sharpe @z>1 | Sharpe @z>1.5 | Sharpe @z>2 | Sharpe @z>2.5 (trades) | top features |","|---|---|---|---|---|---|---|---|---|---|"]
        for r in lg:
            sw=r["sweep"]; lines.append(f"| {r['sym']} | {r['ic']:+.4f} | {' '.join(f'{y}:{v:+.3f}' for y,v in r['ic_years'])} | {r['acc']*100:.1f}% | {sw[1.0][0]} | {sw[1.0][1]:.2f} | {sw[1.5][1]:.2f} | {sw[2.0][1]:.2f} | {sw[2.5][1]:.2f} ({sw[2.5][0]}) | {', '.join(f'{n}' for n,_ in r['top'][:5])} |")
        lines.append("")
    log("STAGE 5: prop-firm 30-day evaluation simulation on holdout survivors")
    if trades:
        allpnl=pd.concat(trades.values()).sort_index()
        # risk 1% of equity per trade with a 1.5-ATR stop => pnl fraction = pnl_atr_units * sqrt(H) / 1.5 * 1%
        frac=allpnl*math.sqrt(H)/1.5*0.01; daily=frac.groupby(frac.index.normalize()).sum()
        idx=pd.date_range(daily.index.min(),daily.index.max(),freq="D"); daily=daily.reindex(idx).fillna(0.0)
        for risk in (0.5,1.0,2.0):
            pr,nw=prop_sim(daily*risk); lines.append(f"- risk {risk:.1f}% per trade: pass rate {pr*100:.1f}% over {nw} rolling 30-day windows (target 10%, daily cap 5%, total cap 10%)")
        lines.append(f"- survivors used: {sum(len(v) for v in survivors.values())} across {len(survivors)} symbols; holdout trades {len(allpnl)}; mean net per trade {allpnl.mean():+.3f} ATR-units; combined annualised Sharpe {sharpe(allpnl.values,len(allpnl)/max(1e-9,(allpnl.index[-1]-allpnl.index[0]).days/365.25)):.2f}")
    else:
        lines.append("- **No alpha survived the holdout + deflated-Sharpe test. No prop-firm simulation run. This is the honest result.**")
    lines+=["",f"Total runtime {(time.time()-t0)/60:.0f} min."]
    open(os.path.join(OUT,"REPORT.md"),"w").write("\n".join(lines)); open(os.path.join(OUT,"alphas.md"),"w").write("\n".join(alphas_md))
    json.dump({s:[{k:v for k,v in r.items() if k!='tree'} for r in rs[:40]] for s,rs in gp_results.items()},open(os.path.join(OUT,"gp_hall_of_fame.json"),"w"),indent=1)
    log("DONE -> results/REPORT.md, results/alphas.md")
