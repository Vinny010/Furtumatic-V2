# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "scikit-learn>=1.3", "scipy>=1.10", "coincurve>=19"]
# ///
"""BIG TEST 3 — 1,000,000,000 keys in the puzzle-#71 range, streaming, compiled secp256k1.
100,000 chains x 10,000 consecutive keys, each chain starting uniformly at random in [2^70, 2^71)."""
import os
for _v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[_v]='1'
import hashlib, sys, time
import numpy as np
from multiprocessing import Pool
CHAIN=10_000; NCH=100_000; SUB_EVERY=500; CHUNK=100_000
def worker(args):
    wid,nchains,seed=args
    from coincurve import PublicKey
    rng=np.random.default_rng(seed); one=(1).to_bytes(32,'big'); lo=1<<70
    S_kh=np.zeros((70,160)); S_k=np.zeros(70); S_h=np.zeros(160); S_hh=np.zeros((160,160)); N=0
    lat2=np.zeros(65536,np.int64); lat3=np.zeros(1<<24,np.int64); byteh=np.zeros(256,np.int64); pairh=np.zeros(65536,np.int64)
    runsh=np.zeros(161,np.int64); hamh=np.zeros(161,np.int64); hexc=np.zeros((40,8,32),np.int64); SEL=[0,1,2,3,66,67,68,69]  # top-4 and low-4 key bits (of the 70)
    subK=[]; subH=[]; KB=np.zeros((CHUNK,9),np.uint8); HB=np.zeros((CHUNK,20),np.uint8); fill=0; t0=time.time(); done=0
    def flush(n):
        nonlocal S_kh,S_k,S_h,S_hh,N,lat2,lat3,byteh,pairh,runsh,hamh,hexc
        kb=np.unpackbits(KB[:n],axis=1)[:,2:72].astype(np.float32); hb=np.unpackbits(HB[:n],axis=1).astype(np.float32)
        S_kh+=kb.T@hb; S_k+=kb.sum(0); S_h+=hb.sum(0); S_hh+=hb.T@hb; N+=n
        b0=HB[:n,0].astype(np.int64); lat2+=np.bincount(b0[:-1]*256+b0[1:],minlength=65536); lat3+=np.bincount((b0[:-2]<<16)|(b0[1:-1]<<8)|b0[2:],minlength=1<<24)
        byteh+=np.bincount(HB[:n].ravel(),minlength=256); h16=HB[:n,:20].reshape(n,10,2); pairh+=np.bincount(((h16[:,:,0].astype(np.int64)<<8)|h16[:,:,1]).ravel(),minlength=65536)
        hbi=hb.astype(np.uint8); runsh+=np.bincount((hbi[:,1:]!=hbi[:,:-1]).sum(1),minlength=161); hamh+=np.bincount(np.unpackbits(HB[:n-1]^HB[1:n],axis=1).sum(1),minlength=161)
        hexd=np.concatenate([HB[:n]>>4,HB[:n]&15],axis=1).astype(np.int64); kbi=kb.astype(np.int64)
        ks=kbi[:,SEL]; off=np.arange(8)*32
        for d in range(40): hexc[d]+=np.bincount((off+hexd[:,d:d+1]*2+ks).ravel(),minlength=256).reshape(8,32)
    for c in range(nchains):
        k=lo+int(rng.integers(0,(1<<62)))*256+int(rng.integers(0,256)); k=min(k,(1<<71)-CHAIN-1)
        P=PublicKey.from_secret(k.to_bytes(32,'big'))
        for i in range(CHAIN):
            h=hashlib.new('ripemd160',hashlib.sha256(P.format(compressed=True)).digest()).digest()
            KB[fill]=np.frombuffer((k+i).to_bytes(9,'big'),np.uint8); HB[fill]=np.frombuffer(h,np.uint8); fill+=1
            if (c*CHAIN+i)%SUB_EVERY==0: subK.append((k+i).to_bytes(9,'big')); subH.append(h)
            if fill==CHUNK: flush(fill); fill=0
            P=P.add(one)
        done+=CHAIN
        if c%2500==2499: print(f"  worker {wid}: {done:,} keys, {done/(time.time()-t0):,.0f} keys/s",flush=True)
    if fill: flush(fill)
    return dict(S_kh=S_kh,S_k=S_k,S_h=S_h,S_hh=S_hh,N=N,lat2=lat2,lat3=lat3,byteh=byteh,pairh=pairh,runsh=runsh,hamh=hamh,hexc=hexc,
                subK=b''.join(subK),subH=b''.join(subH))
if __name__=='__main__':
    t0=time.time(); W=os.cpu_count() or 4
    with Pool(W) as pool: parts=pool.map(worker,[(w,NCH//W,1000+w) for w in range(W)])
    A={k:sum(p[k] for p in parts) for k in ('S_kh','S_k','S_h','S_hh','N','lat2','lat3','byteh','pairh','runsh','hamh','hexc')}
    N=A['N']; print(f"\nGENERATED {N:,} keys in {time.time()-t0:.0f}s ({N/(time.time()-t0):,.0f} keys/s)",flush=True)
    pk=A['S_k']/N; ph=A['S_h']/N
    # 1 balance
    zb=(ph-0.5)*2*np.sqrt(N); print(f"\n== 1. BIT BALANCE: address bits ones-fraction {ph.min():.5f}..{ph.max():.5f}, max |z| {np.abs(zb).max():.2f}")
    # 2 key-bit x address-bit sweep, all 70 key bits
    cov=A['S_kh']/N-np.outer(pk,ph); corr=cov/np.sqrt(np.outer(pk*(1-pk),ph*(1-ph))+1e-12); z=corr*np.sqrt(N)
    print(f"== 2. KEY-BIT x ADDRESS-BIT SWEEP: {z.size:,} tests | max |z| {np.abs(z).max():.2f} | beyond 5 sigma: {(np.abs(z)>5).sum()} (chance ~{z.size*5.7e-7:.4f}) | 5-sigma floor = {5/np.sqrt(N)*100:.4f}% bias")
    top=np.abs(z[:8]).max(); print(f"     top-8 key bits (which half/quarter/eighth... of range) vs address: max |z| {top:.2f}")
    # 3 second-order address-bit dependence
    covh=A['S_hh']/N-np.outer(ph,ph); ch=covh/np.sqrt(np.outer(ph*(1-ph),ph*(1-ph))+1e-12); np.fill_diagonal(ch,0); zh=ch*np.sqrt(N)
    print(f"== 3. ADDRESS BIT-PAIR DEPENDENCE: {160*159//2:,} pairs | max |z| {np.abs(zh).max():.2f} | beyond 5 sigma: {(np.abs(np.triu(zh,1))>5).sum()}")
    # 4 lattice tests
    from scipy.stats import chisquare
    l2=A['lat2']; e2=l2.sum()/65536; chi2_2=((l2-e2)**2/e2).sum(); print(f"== 4. LATTICE: 2D (byte0 k, byte0 k+1): chi2 {chi2_2:,.0f} on 65,535 dof (expect ~65,535 +- 362) -> z = {(chi2_2-65535)/362:.2f}")
    l3=A['lat3']; e3=l3.sum()/len(l3); chi2_3=((l3-e3)**2/e3).sum(); dof=len(l3)-1; print(f"     3D (256^3 cells, ~{e3:.0f} per cell): chi2 {chi2_3:,.0f} on {dof:,} dof -> z = {(chi2_3-dof)/np.sqrt(2*dof):.2f}; empty cells {int((l3==0).sum())} (expect ~{len(l3)*np.exp(-e3):.0f})")
    # 5 NIST-style battery
    bh=A['byteh']; eb=bh.sum()/256; cb=((bh-eb)**2/eb).sum(); ph16=A['pairh']; ep=ph16.sum()/65536; cp=((ph16-ep)**2/ep).sum()
    print(f"== 5. BATTERY: byte histogram chi2 {cb:.1f} on 255 dof (z={(cb-255)/np.sqrt(510):.2f}); 16-bit pair chi2 {cp:,.0f} on 65,535 dof (z={(cp-65535)/362:.2f})")
    r=A['runsh']; rs=np.arange(161); rm=(r*rs).sum()/r.sum(); rv=(r*(rs-rm)**2).sum()/r.sum(); print(f"     runs per address: mean {rm:.3f} (expect 79.5), std {np.sqrt(rv):.3f} (expect 6.30)")
    hm=A['hamh']; hmn=(hm*rs).sum()/hm.sum(); hsd=np.sqrt((hm*(rs-hmn)**2).sum()/hm.sum()); print(f"     neighbour address distance k,k+1: mean {hmn:.3f} (expect 80.000), std {hsd:.3f} (expect 6.325)")
    # 6 hex digit x key bit chi-square
    from scipy.stats import chi2_contingency
    ps=[]
    for d in range(40):
        for j in range(8):
            ct=A['hexc'][d,j].reshape(16,2).astype(float); ct=ct[ct.sum(1)>0]; ps.append(chi2_contingency(ct,correction=False)[1] if ct.shape[0]>1 else 1.0)
    ps=np.array(ps); print(f"== 6. HEX DIGIT x KEY BIT (top-4 & low-4 key bits): {ps.size} tests | min p {ps.min():.2e} (chance-level minimum ~{1/ps.size:.1e}) | Bonferroni flags {(ps<0.05/ps.size).sum()}")
    # 7 ML on the subsample
    from sklearn.ensemble import HistGradientBoostingClassifier
    subK=np.frombuffer(b''.join(p['subK'] for p in parts),np.uint8).reshape(-1,9); subH=np.frombuffer(b''.join(p['subH'] for p in parts),np.uint8).reshape(-1,20)
    idx=np.random.default_rng(7).permutation(len(subK)); subK,subH=subK[idx],subH[idx]; kb=np.unpackbits(subK,axis=1)[:,2:72]; hb=np.unpackbits(subH,axis=1); n=len(kb); tr=int(n*0.75)
    print(f"== 7. ML (random split, {n:,} subsample: {tr:,} train / {n-tr:,} test) ==")
    def ml(X,y,label,classes=2):
        clf=HistGradientBoostingClassifier(max_iter=150); clf.fit(X[:tr],y[:tr]); acc=clf.score(X[tr:],y[tr:]); base=max(np.bincount(y[tr:]))/(n-tr)
        print(f"     {label}: {acc*100:.2f}%  (majority-class baseline {base*100:.2f}%, +-{196*np.sqrt(base*(1-base)/(n-tr)):.2f}%)",flush=True)
    ml(hb,kb[:,0],"which HALF of #71 range (key bit 2^69) from 160 address bits")
    ml(hb,kb[:,0]*2+kb[:,1],"which QUARTER (top 2 key bits), 4-class")
    ml(hb,kb[:,69],"lowest key bit 2^0")
    ml(hb,kb[:,35],"middle key bit 2^34")
    # 8 controls
    print("== 8. CONTROLS ==")
    leak=hb.copy(); f=np.random.default_rng(3).random(n)<0.01; leak[:,7]=np.where(f,kb[:,0],leak[:,7]); zc=np.corrcoef(kb[:,0].astype(float),leak[:,7].astype(float))[0,1]*np.sqrt(n)
    print(f"     planted 0.5% leak on the subsample: z = {zc:.1f} sigma"); ml(leak,kb[:,0],"     planted: which half")
    rnd=np.unpackbits(np.frombuffer(os.urandom(n*20),np.uint8).reshape(n,20),axis=1); print(f"     random bytes: z = {abs(np.corrcoef(kb[:,0].astype(float),rnd[:,7].astype(float))[0,1])*np.sqrt(n):.1f} sigma"); ml(rnd,kb[:,0],"     random: which half")
    print(f"\ntotal {time.time()-t0:.0f}s",flush=True)
