# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "scipy>=1.10", "coincurve>=19"]
# ///
"""HOT-ZONE SEARCH: automated discovery of functions f(public value) that predict where the secret k lies.
Stage A: a library of hand-built number-theoretic features (residues, power-residue symbols, bits, hashes) on
         Q, 2Q, 3Q, Q+G, Q-G, lambda*Q.
Stage B: random formula search - thousands of machine-generated expression trees over the coordinates.
Both stages are scored against targets: k mod 2/3/4/5, which half / quarter / decile of the interval.
POSITIVE CONTROL: the multiplicative group mod a Mersenne prime, where power-residue symbols provably leak k mod m.
TEST: secp256k1 with k uniform in a 64-bit interval (structure is the same as puzzle ranges).
Every reported p-value is Bonferroni-corrected across ALL tests in the run, and confirmed out-of-sample."""
import os, sys, time, hashlib, random
import numpy as np
from multiprocessing import Pool
from scipy.stats import chi2_contingency
N_A=int(sys.argv[1]) if len(sys.argv)>1 else 400_000
N_B=int(sys.argv[2]) if len(sys.argv)>2 else 150_000
N_FORMULAS=int(sys.argv[3]) if len(sys.argv)>3 else 3000
SEED=11
# ---------------- groups ----------------
P=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
BETA=0x7ae96a2b657c07106e64479eac3434e99cf0497512f58995c1396c28719501ee
MP=(1<<61)-1  # Mersenne prime; MP-1 = 2*3^2*5^2*7*11*13*31*41*61*151*331*1321
MG=37         # generator candidate for Z_MP^* (checked below)
def is_generator(g,p,factors):
    return all(pow(g,(p-1)//q,p)!=1 for q in factors)
MP_FACTORS=[2,3,5,7,11,13,31,41,61,151,331,1321]
assert is_generator(MG,MP,MP_FACTORS)
def gen_curve(args):
    seed,n,lo,width=args
    from coincurve import PublicKey
    rng=random.Random(seed); out=[]
    for _ in range(n):
        k=lo+rng.getrandbits(width)
        raw=PublicKey.from_secret(k.to_bytes(32,'big')).format(compressed=False)
        out.append((k,int.from_bytes(raw[1:33],'big'),int.from_bytes(raw[33:65],'big')))
    return out
def gen_mult(args):
    seed,n,lo,width=args
    rng=random.Random(seed); out=[]
    for _ in range(n):
        k=lo+rng.getrandbits(width); v=pow(MG,k,MP); out.append((k,v,(v*MG)%MP))
    return out
# ---------------- feature library (stage A) ----------------
def ec_add(x1,y1,x2,y2):
    if x1==x2: 
        l=(3*x1*x1)*pow(2*y1,-1,P)%P
    else:
        l=(y2-y1)*pow(x2-x1,-1,P)%P
    x3=(l*l-x1-x2)%P; return x3,(l*(x1-x3)-y1)%P
GX=0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY=0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
def curve_points(x,y):
    x2,y2=ec_add(x,y,x,y); x3,y3=ec_add(x2,y2,x,y); xp,yp=ec_add(x,y,GX,GY); xm,ym=ec_add(x,y,GX,(P-GY)%P)
    return {'Q':(x,y),'2Q':(x2,y2),'3Q':(x3,y3),'Q+G':(xp,yp),'Q-G':(xm,ym),'lQ':((BETA*x)%P,y)}
def value_feats(v,p,pfactors,tag):
    f={}
    for m in (2,3,4,5,7,8,11,13): f[f'{tag} mod {m}']=v%m
    for q in pfactors[:6]: f[f'{tag}^((p-1)/{q})']=pow(v,(p-1)//q,p)%1000  # power-residue symbol (bucketed)
    f[f'{tag}>p/2']=int(v>p//2); f[f'{tag} popcount%2']=bin(v).count('1')&1
    f[f'{tag} bits 0-3']=v&15; f[f'{tag} top 4 bits']=v>>(p.bit_length()-4)
    h=hashlib.sha256(v.to_bytes(32,'big')).digest(); f[f'sha256({tag}) byte0']=h[0]%16
    return f
P_FACTORS=[2,3,7,13441]  # small factors of P-1 for secp256k1 field
def feats_curve(row):
    k,x,y=row; f={}
    for name,(px,py) in curve_points(x,y).items():
        f.update(value_feats(px,P,P_FACTORS,f'x({name})')); 
        if name in('Q','2Q'): f.update(value_feats(py,P,P_FACTORS,f'y({name})'))
    f['legendre(x(Q)+1)']=pow(x+1,(P-1)//2,P)%1000; f['legendre(x(Q)*x(2Q))']=pow((x*f_x2(x,y))%P,(P-1)//2,P)%1000
    return f
def f_x2(x,y): return ec_add(x,y,x,y)[0]
def feats_mult(row):
    k,v,vg=row; f={}
    f.update(value_feats(v,MP,MP_FACTORS,'v')); f.update(value_feats(vg,MP,MP_FACTORS,'v*g')); f.update(value_feats((v*v)%MP,MP,MP_FACTORS,'v^2'))
    return f
def targets(k,lo,width):
    pos=(k-lo)/(1<<width)
    return {'k mod 2':k%2,'k mod 3':k%3,'k mod 4':k%4,'k mod 5':k%5,'which half':int(pos>=0.5),'which quarter':int(pos*4),'which decile':int(pos*10)}
def _featchunk(args):
    fn,chunk=args; f=feats_curve if fn=='c' else feats_mult; return [f(r) for r in chunk]
def build(rows,featfn,lo,width):
    W=os.cpu_count() or 4; fn='c' if featfn is feats_curve else 'm'; cs=(len(rows)+W-1)//W
    with Pool(W) as pool: F=sum(pool.map(_featchunk,[(fn,rows[i:i+cs]) for i in range(0,len(rows),cs)]),[])
    T=[targets(r[0],lo,width) for r in rows]
    keys=list(F[0].keys()); tk=list(T[0].keys())
    FA={k:np.array([f[k] for f in F]) for k in keys}; TA={k:np.array([t[k] for t in T]) for k in tk}
    return FA,TA
def score(FA,TA,label):
    n=len(next(iter(TA.values()))); tr=n//2; res=[]
    for fk,fv in FA.items():
        for tk,tv in TA.items():
            def pv(sl):
                ct=np.zeros((int(fv.max())+1,int(tv.max())+1)); np.add.at(ct,(fv[sl],tv[sl]),1); ct=ct[ct.sum(1)>0][:,ct.sum(0)>0]
                if ct.shape[0]<2 or ct.shape[1]<2: return 1.0,0.0
                chi,p,_,_=chi2_contingency(ct,correction=False); v=np.sqrt(chi/(ct.sum()*(min(ct.shape)-1)))  # Cramer's V = effect size
                return p,v
            p1,v1=pv(slice(0,tr)); p2,v2=pv(slice(tr,n)); res.append((p1,p2,v1,v2,fk,tk))
    ntests=len(res); alpha=0.05/ntests
    hits=[r for r in res if r[0]<alpha and r[1]<alpha]
    res.sort(key=lambda r:r[0])
    print(f"\n[{label}] {len(FA)} features x {len(TA)} targets = {ntests:,} tests, N={n:,} (half train / half confirm), Bonferroni alpha={alpha:.1e}")
    print(f"   CONFIRMED HOT-ZONE FUNCTIONS (significant in BOTH halves): {len(hits)}")
    for p1,p2,v1,v2,fk,tk in sorted(hits,key=lambda r:-r[2])[:12]:
        print(f"     {fk:28s} -> {tk:14s}  effect (Cramer's V) {v1:.3f} / {v2:.3f}   p={p1:.1e} / {p2:.1e}")
    print(f"   best non-confirmed candidates (should look like chance):")
    for p1,p2,v1,v2,fk,tk in [r for r in res if r not in hits][:4]:
        print(f"     {fk:28s} -> {tk:14s}  V {v1:.4f} / {v2:.4f}   p={p1:.2e} / {p2:.2e}")
    return hits
# ---------------- random formula search (stage B) ----------------
OPS=['add','mul','sub','inv','sq','neg','cx','cy','xy','pw']
def rand_formula(rng,depth=0):
    if depth>=3 or rng.random()<0.3: return rng.choice(['x','y','x2','y2','xp','xl','c'])
    op=rng.choice(OPS)
    if op in('inv','sq','neg','pw'): return (op,rand_formula(rng,depth+1))
    return (op,rand_formula(rng,depth+1),rand_formula(rng,depth+1))
def ev(f,env,p):
    if isinstance(f,str): return env[f]
    op=f[0]
    if op=='inv': a=ev(f[1],env,p); return pow(a,-1,p) if a%p else 0
    if op=='sq': return ev(f[1],env,p)**2%p
    if op=='neg': return (-ev(f[1],env,p))%p
    if op=='pw': return pow(ev(f[1],env,p),(p-1)//2,p)  # Legendre-type symbol as a value
    a=ev(f[1],env,p); b=ev(f[2],env,p)
    if op=='add': return (a+b)%p
    if op=='sub': return (a-b)%p
    if op in('mul','xy','cx','cy'): return (a*b)%p
    return (a+b)%p
def fstr(f):
    if isinstance(f,str): return f
    if len(f)==2: return f"{f[0]}({fstr(f[1])})"
    return f"({fstr(f[1])} {f[0]} {fstr(f[2])})"
def formula_outputs(f,rows,p,envfn):
    out=[]
    for r in rows:
        v=ev(f,envfn(r),p); out.append(v)
    return out
def bucket(vals,p):
    a=np.array([v%64 for v in vals]); b=np.array([int(v>p//2) for v in vals]); c=np.array([v%3 for v in vals]); d=np.array([v%5 for v in vals])
    return {'mod64':a,'top':b,'mod3':c,'mod5':d}
def env_curve(r):
    k,x,y=r; x2,y2=ec_add(x,y,x,y); xp,yp=ec_add(x,y,GX,GY)
    return {'x':x,'y':y,'x2':x2,'y2':y2,'xp':xp,'xl':(BETA*x)%P,'c':7}
def env_mult(r):
    k,v,vg=r; return {'x':v,'y':vg,'x2':(v*v)%MP,'y2':(vg*vg)%MP,'xp':(v*MG*MG)%MP,'xl':pow(v,3,MP),'c':MG}
_G={}
def _fworker(args):
    wid,formulas,p,which,rows,TA=args
    envfn=env_curve if which=='c' else env_mult; envs=[envfn(r) for r in rows]; n=len(rows); tr=n//2; out=[]; t0=time.time()
    for i,f in enumerate(formulas):
        vals=[ev(f,e,p) for e in envs]; B=bucket(vals,p)
        for bk,bv in B.items():
            for tk,tv in TA.items():
                def pv(sl):
                    ct=np.zeros((int(bv.max())+1,int(tv.max())+1)); np.add.at(ct,(bv[sl],tv[sl]),1); ct=ct[ct.sum(1)>0][:,ct.sum(0)>0]
                    if ct.shape[0]<2 or ct.shape[1]<2: return 1.0,0.0
                    chi,pp,_,_=chi2_contingency(ct,correction=False); return pp,np.sqrt(chi/(ct.sum()*(min(ct.shape)-1)))
                p1,v1=pv(slice(0,tr)); p2,v2=pv(slice(tr,n)); out.append((p1,p2,v1,v2,fstr(f)+f' [{bk}]',tk))
        if wid==0 and (i+1)%100==0: print(f"   ...worker0 {i+1}/{len(formulas)} formulas, {time.time()-t0:.0f}s",flush=True)
    return out
def formula_stage(rows,p,envfn,TA,label,nformulas,seed):
    rng=random.Random(seed); n=len(rows); which='c' if envfn is env_curve else 'm'
    formulas=[rand_formula(rng) for _ in range(nformulas)]; W=os.cpu_count() or 4
    with Pool(W) as pool: results=sum(pool.map(_fworker,[(w,formulas[w::W],p,which,rows,TA) for w in range(W)]),[])
    tests=len(results); alpha=0.05/tests; hits=[r for r in results if r[0]<alpha and r[1]<alpha]; results.sort(key=lambda r:r[0])
    print(f"\n[{label}] FORMULA SEARCH: {nformulas:,} machine-generated formulas, {tests:,} tests, N={n:,}, Bonferroni alpha={alpha:.1e}")
    print(f"   CONFIRMED HOT-ZONE FORMULAS (both halves): {len(hits)}")
    for p1,p2,v1,v2,fk,tk in sorted(hits,key=lambda r:-r[2])[:10]: print(f"     {fk[:60]:60s} -> {tk:14s} V {v1:.3f}/{v2:.3f}")
    print(f"   best non-confirmed (chance-level expected):")
    for p1,p2,v1,v2,fk,tk in [r for r in results if r not in hits][:3]: print(f"     {fk[:60]:60s} -> {tk:14s} V {v1:.4f}/{v2:.4f} p={p1:.1e}/{p2:.1e}")
    return hits
if __name__=='__main__':
    t0=time.time(); W=os.cpu_count() or 4
    lo_c=1<<70; width_c=64          # k in [2^70, 2^70+2^64): a 64-bit interval, like a puzzle range slice
    lo_m=1<<40; width_m=20          # k in a 2^20 interval of Z_MP^*
    with Pool(W) as pool:
        rows_c=sum(pool.map(gen_curve,[(SEED*10+w,N_A//W,lo_c,width_c) for w in range(W)]),[])
        rows_m=sum(pool.map(gen_mult,[(SEED*20+w,N_A//W,lo_m,width_m) for w in range(W)]),[])
    print(f"generated {len(rows_c):,} secp256k1 samples and {len(rows_m):,} multiplicative-group samples in {time.time()-t0:.0f}s",flush=True)
    print("\n================ STAGE A: number-theoretic feature library ================")
    FA_m,TA_m=build(rows_m,feats_mult,lo_m,width_m); hits_m=score(FA_m,TA_m,"POSITIVE CONTROL  Z_p^*  (leaks MUST be found)")
    FA_c,TA_c=build(rows_c,feats_curve,lo_c,width_c); hits_c=score(FA_c,TA_c,"secp256k1")
    print("\n================ STAGE B: random formula search ================",flush=True)
    sub_m=rows_m[:N_B]; sub_c=rows_c[:N_B]
    TB_m={k:v[:N_B] for k,v in TA_m.items()}; TB_c={k:v[:N_B] for k,v in TA_c.items()}
    fh_m=formula_stage(sub_m,MP,env_mult,TB_m,"POSITIVE CONTROL  Z_p^*",N_FORMULAS,SEED+1)
    fh_c=formula_stage(sub_c,P,env_curve,TB_c,"secp256k1",N_FORMULAS,SEED+2)
    print(f"\n================ SUMMARY ================")
    print(f"control group : {len(hits_m)} library hits, {len(fh_m)} formula hits  (expected: many - leaks exist by theorem)")
    print(f"secp256k1     : {len(hits_c)} library hits, {len(fh_c)} formula hits  (any confirmed hit here is a discovery)")
    print(f"total {time.time()-t0:.0f}s")
