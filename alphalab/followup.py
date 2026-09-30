# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "pandas>=2.0", "pyarrow>=14", "scipy>=1.10", "lightgbm>=4.0", "scikit-learn>=1.3"]
# ///
"""Follow-up to the main run: (1) horizon sweep for the LightGBM model (does a longer hold beat costs?),
(2) the machine-found 'Asian-session mean reversion' candidate evaluated properly on every pair's holdout."""
import os, sys, json, math, time, numpy as np, pandas as pd
from multiprocessing import Pool
from scipy.stats import spearmanr
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import alphalab as A
def horizon_job(args):
    sym,h=args; import lightgbm as lgb
    F=pd.read_parquet(os.path.join(A.CACHE,f"{sym}_F.parquet")); b=A.load_symbol(sym).reindex(F.index); cost=pd.read_parquet(os.path.join(A.CACHE,f"{sym}_cost.parquet"))["cost"]
    c=b.close; atr=F["atr_pct"]; y=np.log(c.shift(-h)/c)/(atr*math.sqrt(h)+1e-12); cost_atr=cost/(atr*math.sqrt(h)+1e-12); X=F.fillna(0.0)
    months=pd.period_range(F.index[0],F.index[-1],freq="M"); preds=pd.Series(np.nan,index=F.index)
    for i in range(12,len(months)):
        tr=(F.index>=months[i-12].start_time)&(F.index<(months[i].start_time-pd.Timedelta(minutes=15*2*h))); te=(F.index>=months[i].start_time)&(F.index<months[i].end_time)
        if tr.sum()<5000 or te.sum()<100: continue
        ok=np.isfinite(y.values)&tr
        m=lgb.LGBMRegressor(n_estimators=200,learning_rate=0.03,num_leaves=15,min_child_samples=200,subsample=0.7,subsample_freq=1,colsample_bytree=0.7,reg_lambda=5.0,verbose=-1,n_jobs=1)
        m.fit(X[ok],y[ok]); preds[te]=m.predict(X[te])
    mk=preds.notna()&y.notna(); ic=float(spearmanr(preds[mk],y[mk]).correlation); out={"sym":sym,"h":h,"ic":ic,"acc":float((np.sign(preds[mk])==np.sign(y[mk])).mean())}
    yrs=(F.index.year*2+(F.index.month>6)).values; ics=A.ic_by_year(preds.values,y.values,yrs); out["ic_min_halfyear"]=float(ics.min()) if len(ics) else float("nan"); out["ic_pos_frac"]=float((ics>0).mean()) if len(ics) else float("nan")
    for thr in (1.0,2.0,2.5,3.0):
        pnl,idx=A.backtest(preds.fillna(0).values,y.values,cost_atr.values,zwin=500,thr=thr,h=h)
        tpy=len(pnl)/max(1e-9,(F.index[-1]-F.index[0]).days/365.25); out[f"sr@{thr}"]=(int(len(pnl)),float(A.sharpe(pnl,1)*math.sqrt(max(tpy,1))) if len(pnl)>10 else 0.0,float(pnl.mean()) if len(pnl) else 0.0)
    rb=[]
    for sd in range(3):
        rp,ri=A.backtest(np.random.default_rng(sd).standard_normal(len(y)),y.values,cost_atr.values,zwin=500,thr=1.0,h=h); tpy=len(rp)/max(1e-9,(F.index[-1]-F.index[0]).days/365.25); rb.append(A.sharpe(rp,1)*math.sqrt(max(tpy,1)))
    out["random_sr"]=float(np.mean(rb)); return out
def asia_job(sym):
    F=pd.read_parquet(os.path.join(A.CACHE,f"{sym}_F.parquet")); T=pd.read_parquet(os.path.join(A.CACHE,f"{sym}_T.parquet")); meta=json.load(open(os.path.join(A.CACHE,f"{sym}_meta.json"))); cost=pd.read_parquet(os.path.join(A.CACHE,f"{sym}_cost.parquet"))["cost"]
    hold=F.index>=pd.Timestamp(meta["holdout_start"]); res=[]
    for h in (4,8,16):
        y=T[f"y{h}"].values if f"y{h}" in T else None
        if y is None: continue
        cost_atr=(cost.values/(F["atr_pct"].values*math.sqrt(h)+1e-12))
        for name,alpha in (("-z20 in Asia",np.where(F.asia.values==1,-F.z_20.values,0.0)),("-rsi14 in Asia",np.where(F.asia.values==1,-F.rsi14.values,0.0)),("-z20 all sessions",-F.z_20.values),("-z20 in London",np.where(F.london.values==1,-F.z_20.values,0.0))):
            yrs=(F.index.year*2+(F.index.month>6)).values
            ic_s=A.ic_by_year(alpha[~hold],y[~hold],yrs[~hold]); ic_h=A.ic_by_year(alpha[hold],y[hold],yrs[hold])
            a2=np.where(alpha==0,np.nan,alpha)   # only take trades inside the session
            pnl,idx=A.backtest(np.nan_to_num(a2,nan=0.0),y,cost_atr,zwin=500,thr=1.0,h=h); hm=idx>=np.argmax(hold); ph=pnl[hm]
            tpy=len(ph)/max(1e-9,(F.index[hold][-1]-F.index[hold][0]).days/365.25); sr=A.sharpe(ph,1)*math.sqrt(max(tpy,1)) if len(ph)>10 else 0.0
            res.append({"sym":sym,"h":h,"rule":name,"search_ic":float(ic_s.mean()) if len(ic_s) else float("nan"),"hold_ic":float(ic_h.mean()) if len(ic_h) else float("nan"),"hold_ic_min":float(ic_h.min()) if len(ic_h) else float("nan"),"hold_trades":int(len(ph)),"hold_sr":float(sr),"gross_per_trade":float((ph+cost_atr[idx[hm]]).mean()) if len(ph) else 0.0,"net_per_trade":float(ph.mean()) if len(ph) else 0.0})
    return res
if __name__=="__main__":
    t0=time.time(); syms=["XAUUSD","BTCUSD","EURUSD","GBPUSD","USDJPY"]
    A.log("follow-up A: Asian-session mean-reversion candidate on all pairs")
    with Pool(4) as p: asia=sum(p.map(asia_job,syms),[])
    A.log("follow-up B: LightGBM horizon sweep h=16,32,96 (4h, 8h, 1 day)")
    jobs=[(s,h) for h in (16,32,96) for s in syms]
    with Pool(4) as p: hz=p.map(horizon_job,jobs)
    L=["# Follow-up results","","## A. 'Asian-session mean reversion' (machine-found on GBPUSD) evaluated on every pair, holdout only","","| symbol | h | rule | search IC | holdout IC (min half-yr) | holdout trades | holdout Sharpe | gross/trade (ATR) | net/trade (ATR) |","|---|---|---|---|---|---|---|---|---|"]
    for r in asia: L.append(f"| {r['sym']} | {r['h']} | {r['rule']} | {r['search_ic']:+.3f} | {r['hold_ic']:+.3f} ({r['hold_ic_min']:+.3f}) | {r['hold_trades']} | {r['hold_sr']:.2f} | {r['gross_per_trade']:+.3f} | {r['net_per_trade']:+.3f} |")
    L+=["","## B. LightGBM walk-forward, longer horizons (does holding longer beat costs?)","","| symbol | h (bars) | OOS IC | half-years positive | min half-yr IC | acc | trades@z>1 / Sharpe | @z>2 | @z>2.5 | @z>3 | random baseline Sharpe |","|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(hz,key=lambda r:(r['sym'],r['h'])): L.append(f"| {r['sym']} | {r['h']} | {r['ic']:+.4f} | {r['ic_pos_frac']*100:.0f}% | {r['ic_min_halfyear']:+.3f} | {r['acc']*100:.1f}% | {r['sr@1.0'][0]} / {r['sr@1.0'][1]:.2f} | {r['sr@2.0'][0]} / {r['sr@2.0'][1]:.2f} | {r['sr@2.5'][0]} / {r['sr@2.5'][1]:.2f} | {r['sr@3.0'][0]} / {r['sr@3.0'][1]:.2f} | {r['random_sr']:.2f} |")
    L.append(f"\nRuntime {(time.time()-t0)/60:.0f} min."); open(os.path.join(A.OUT,"FOLLOWUP.md"),"w").write("\n".join(L)); A.log("DONE -> results/FOLLOWUP.md")
