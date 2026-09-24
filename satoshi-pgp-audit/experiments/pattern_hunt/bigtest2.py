# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "scikit-learn>=1.3", "scipy>=1.10"]
# ///
"""BIG TEST 2: 10,000,000 consecutive keys in the puzzle-#71 range + 30,000 random 71-bit keys.
New feature family (hex digits, byte sums, mod-prime residues, popcount, leading zeros) + raw-bit sweep
+ random-split ML + planted 0.5% leak control + true-random control."""
import hashlib, os, sys, time, secrets
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ec_lib import add, mul, Gx, Gy
G=(Gx,Gy); PRIMES=[3,5,7,11,13,17,19,23,29,31]
def h160(x,y):
    comp=(b'\x02' if y%2==0 else b'\x03')+x.to_bytes(32,'big'); return hashlib.new('ripemd160',hashlib.sha256(comp).digest()).digest()
def chain(args):
    k0,n=args; P=mul(k0,G); H=bytearray(); XM=np.zeros((n,len(PRIMES)),np.uint8); HM=np.zeros((n,len(PRIMES)),np.uint8); XP=np.zeros(n,np.uint8)
    for i in range(n):
        h=h160(*P); H+=h; hi=int.from_bytes(h,'big'); x=P[0]
        for j,p in enumerate(PRIMES): XM[i,j]=x%p; HM[i,j]=hi%p
        XP[i]=bin(x).count('1'); P=add(P,G)
    return bytes(H),XM,HM,XP
def randkeys(args):
    n,seed=args; rng=np.random.default_rng(seed); out=[]
    for _ in range(n):
        k=(1<<70)|int(rng.integers(0,1<<62))<<8|int(rng.integers(0,256)); Q=mul(k,G); out.append((k.to_bytes(9,'big'),h160(*Q),Q[0]))
    return out
if __name__=='__main__':
    t0=time.time(); N=10_000_000; W=os.cpu_count() or 4; per=N//W
    k0=(1<<70)+secrets.randbelow((1<<70)-N-1)
    with Pool(W) as pool: parts=pool.map(chain,[(k0+j*per,per) for j in range(W)])
    N=per*W; H=np.frombuffer(b''.join(p[0] for p in parts),np.uint8).reshape(N,20); XM=np.vstack([p[1] for p in parts]); HM=np.vstack([p[2] for p in parts]); XP=np.concatenate([p[3] for p in parts])
    print(f"consecutive: {N:,} keys from 2^70+{k0-(1<<70)} on {W} cores in {time.time()-t0:.0f}s",flush=True)
    t1=time.time(); NR=30_000
    with Pool(W) as pool: rp=pool.map(randkeys,[(NR//W,s) for s in range(W)])
    rk=[r for part in rp for r in part]; KR=np.frombuffer(b''.join(r[0] for r in rk),np.uint8).reshape(-1,9); HR=np.frombuffer(b''.join(r[1] for r in rk),np.uint8).reshape(-1,20)
    XRM=np.array([[r[2]%p for p in PRIMES] for r in rk],np.uint8); NR=len(rk)
    print(f"random: {NR:,} full 71-bit keys in {time.time()-t1:.0f}s",flush=True)
    idx=np.arange(N,dtype=np.uint32); KB=np.unpackbits(idx.astype('>u4').view(np.uint8).reshape(N,4),axis=1)  # 32 bits of i
    vary=KB.std(0)>0; KB=KB[:,vary]; nk=KB.shape[1]; print(f"key bits that vary in the consecutive set: {nk}",flush=True)
    # ---------- 1. raw-bit correlation sweep, chunked ----------
    S_kh=np.zeros((nk,160)); S_k=KB.sum(0).astype(float); S_h=np.zeros(160); C=500_000
    for s in range(0,N,C):
        hb=np.unpackbits(H[s:s+C],axis=1).astype(np.float32); kb=KB[s:s+C].astype(np.float32); S_kh+=kb.T@hb; S_h+=hb.sum(0)
    pk=S_k/N; ph=S_h/N; cov=S_kh/N-np.outer(pk,ph); corr=cov/np.sqrt(np.outer(pk*(1-pk),ph*(1-ph))+1e-12); z=corr*np.sqrt(N)
    print(f"\n== 1. RAW-BIT SWEEP (10M keys): {z.size:,} tests | max |z| {np.abs(z).max():.2f} | beyond 5 sigma: {(np.abs(z)>5).sum()} (chance ~{z.size*5.7e-7:.3f}) | 5-sigma floor = {5/np.sqrt(N)*100:.3f}% bias",flush=True)
    # ---------- 2. feature family: chi-square independence vs each key bit ----------
    from scipy.stats import chi2_contingency
    def chi(feat,name,nvals):
        worst=(1.0,None)
        for b in range(nk):
            ct=np.bincount(feat.astype(np.int64)*2+KB[:,b],minlength=nvals*2).reshape(nvals,2).astype(float); ct=ct[ct.sum(1)>0]
            if ct.shape[0]<2: continue
            p=chi2_contingency(ct,correction=False)[1]
            if p<worst[0]: worst=(p,b)
        return worst
    tests=[]; hexd=np.concatenate([H>>4,H&15],axis=1)   # 40 hex digits of the address
    for d in range(40): tests.append((f"address hex digit {d}",)+chi(hexd[:,d],'',16))
    tests.append(("address byte-sum mod 256",)+chi((H.astype(np.uint32).sum(1)%256).astype(np.int64),'',256))
    tests.append(("address popcount",)+chi(np.unpackbits(H,axis=1).sum(1).astype(np.int64),'',161))
    lz=np.argmax(np.unpackbits(H,axis=1)==1,axis=1); tests.append(("address leading zeros",)+chi(lz.astype(np.int64),'',161))
    tests.append(("pubkey-X popcount",)+chi(XP.astype(np.int64),'',257))
    for j,p in enumerate(PRIMES): tests.append((f"address mod {p}",)+chi(HM[:,j].astype(np.int64),'',p)); tests.append((f"pubkey-X mod {p}",)+chi(XM[:,j].astype(np.int64),'',p))
    total=len(tests)*nk; bonf=0.05/total; flagged=[(n,p) for n,p,b in tests if p<bonf]
    print(f"\n== 2. FEATURE FAMILY (10M keys): {len(tests)} features x {nk} key bits = {total:,} tests | Bonferroni p < {bonf:.1e} | flagged: {len(flagged)}",flush=True)
    for n,p,b in sorted(tests,key=lambda t:t[1])[:5]: print(f"   smallest p: {n:28s} p={p:.3g}  (chance-level for {total:,} tests ~{1/total:.1e})",flush=True)
    # random keys: address mod p vs TOP key bits (which half/quarter of #71 range)
    KRb=np.unpackbits(KR,axis=1); top=KRb[:,72-70]  # bit 2^69 = which half of the range
    HRi=np.array([int.from_bytes(bytes(r),'big') for r in HR]); print("   random keys — address mod p vs 'which half of range':", ", ".join(f"mod {p}: p={chi2_contingency(np.histogram2d(HRi%p,top,bins=[p,2])[0]+1e-9,correction=False)[1]:.2f}" for p in PRIMES[:5]),flush=True)
    # ---------- 3. ML, random split ----------
    from sklearn.ensemble import HistGradientBoostingClassifier
    rng=np.random.default_rng(1); sub=rng.choice(N,2_000_000,replace=False); Hs=np.unpackbits(H[sub],axis=1); Ks=KB[sub]; tr=1_500_000
    print("\n== 3. ML, RANDOM SPLIT (2M subsample: 1.5M train / 0.5M test) ==",flush=True)
    def ml(Xf,y,label,n_tr):
        clf=HistGradientBoostingClassifier(max_iter=150); clf.fit(Xf[:n_tr],y[:n_tr]); acc=clf.score(Xf[n_tr:],y[n_tr:]); m=len(y)-n_tr
        print(f"   {label}: {acc*100:.2f}%  (coin-flip 50.00 +- {196*np.sqrt(.25/m):.2f}%)",flush=True); return acc
    for b,name in ((nk-1,'2^0'),(nk-9,'2^8'),(nk-17,'2^16'),(0,f'2^{nk-1} (top varying bit)')): ml(Hs,Ks[:,b],f"predict key bit {name} from 160 address bits",tr)
    ml(np.concatenate([hexd[sub],HM[sub],XM[sub],XP[sub,None]],axis=1),Ks[:,nk-1],"predict key bit 2^0 from the FEATURE FAMILY (hex digits, residues, popcount)",tr)
    HRb=np.unpackbits(HR,axis=1); ml(HRb,top,"random keys: predict WHICH HALF of #71 range from address (22.5k/7.5k)",22_500)
    ml(np.concatenate([XRM,np.concatenate([HR>>4,HR&15],axis=1)],axis=1),top,"random keys: which half, from feature family",22_500)
    # ---------- 4. controls ----------
    print("\n== 4. CONTROLS ==",flush=True)
    leak=Hs.copy(); f=rng.random(len(sub))<0.01; leak[:,7]=np.where(f,Ks[:,nk-1],leak[:,7])   # 0.5% net bias
    kb=Ks[:,nk-1].astype(float); hb=leak[:,7].astype(float); zc=np.corrcoef(kb,hb)[0,1]*np.sqrt(len(sub))
    print(f"   planted 0.5% leak (2M keys): correlation z = {zc:.1f} sigma",flush=True); ml(leak,Ks[:,nk-1],"   planted: predict key bit 2^0",tr)
    rnd=np.unpackbits(np.frombuffer(os.urandom(len(sub)*20),np.uint8).reshape(-1,20),axis=1); zr=np.abs(np.corrcoef(kb,rnd[:,7].astype(float))[0,1])*np.sqrt(len(sub))
    print(f"   true-random bytes: correlation z = {zr:.1f} sigma",flush=True); ml(rnd,Ks[:,nk-1],"   random: predict key bit 2^0",tr)
    print(f"\ntotal {time.time()-t0:.0f}s",flush=True)
