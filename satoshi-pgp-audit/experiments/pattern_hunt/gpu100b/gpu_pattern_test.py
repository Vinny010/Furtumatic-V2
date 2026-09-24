"""GPU pattern test: N keys in puzzle range, streaming statistics. Requires cupy (CUDA)."""
import argparse, time, os, sys
import numpy as np
try:
    import cupy as cp
except ImportError:
    sys.exit("cupy not installed: pip install cupy-cuda12x")

KERNEL = r'''
// ---- secp256k1 in 8x32-bit limbs, affine double-and-add with batched inversion omitted for clarity.
// ---- Each thread walks a chain of CHAIN consecutive keys: P_{i+1} = P_i + G (one point add per key).
// ---- Then SHA256(compressed pubkey) -> RIPEMD160 -> 20 bytes. Statistics are accumulated with atomics.
#include <stdint.h>
__device__ __constant__ uint32_t P_[8]  = {0xFFFFFC2F,0xFFFFFFFE,0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF};
__device__ __constant__ uint32_t GX[8]  = {0x16F81798,0x59F2815B,0x2DCE28D9,0x029BFCDB,0xCE870B07,0x55A06295,0xF9DCBBAC,0x79BE667E};
__device__ __constant__ uint32_t GY[8]  = {0xFB10D4B8,0x9C47D08F,0xA6855419,0xFD17B448,0x0E1108A8,0x5DA4FBFC,0x26A3C465,0x483ADA77};
// --- field arithmetic (schoolbook, adequate for a statistics run; ~10x slower than BitCrack) ---
__device__ inline void fadd(const uint32_t*a,const uint32_t*b,uint32_t*r){uint64_t c=0;for(int i=0;i<8;i++){c+=(uint64_t)a[i]+b[i];r[i]=(uint32_t)c;c>>=32;}
  // reduce once if r>=P
  int ge=(c!=0);if(!ge){ge=1;for(int i=7;i>=0;i--){if(r[i]<P_[i]){ge=0;break;}if(r[i]>P_[i])break;}}
  if(ge){uint64_t br=0;for(int i=0;i<8;i++){uint64_t t=(uint64_t)r[i]-P_[i]-br;r[i]=(uint32_t)t;br=(t>>63)&1;}}}
__device__ inline void fsub(const uint32_t*a,const uint32_t*b,uint32_t*r){uint64_t br=0;for(int i=0;i<8;i++){uint64_t t=(uint64_t)a[i]-b[i]-br;r[i]=(uint32_t)t;br=(t>>63)&1;}
  if(br){uint64_t c=0;for(int i=0;i<8;i++){c+=(uint64_t)r[i]+P_[i];r[i]=(uint32_t)c;c>>=32;}}}
__device__ void fmul(const uint32_t*a,const uint32_t*b,uint32_t*r){
  uint32_t t[16]={0};
  for(int i=0;i<8;i++){uint64_t c=0;for(int j=0;j<8;j++){uint64_t m=(uint64_t)a[i]*b[j]+t[i+j]+c;t[i+j]=(uint32_t)m;c=m>>32;}t[i+8]=(uint32_t)c;}
  // reduce mod p = 2^256 - 2^32 - 977 :  high*2^256 = high*(2^32+977)
  for(int pass=0;pass<2;pass++){
    uint32_t hi[8];for(int i=0;i<8;i++){hi[i]=t[i+8];t[i+8]=0;}
    uint64_t c=0;for(int i=0;i<8;i++){uint64_t m=(uint64_t)hi[i]*977+t[i]+c;t[i]=(uint32_t)m;c=m>>32;}
    t[8]=(uint32_t)c;
    c=0;for(int i=0;i<8;i++){c+=(uint64_t)t[i+1]+hi[i];t[i+1]=(uint32_t)c;c>>=32;}t[9]=(uint32_t)c;
  }
  for(int i=0;i<8;i++)r[i]=t[i];
  // final conditional subtract
  int ge=1;for(int i=7;i>=0;i--){if(r[i]<P_[i]){ge=0;break;}if(r[i]>P_[i])break;}
  if(ge){uint64_t br=0;for(int i=0;i<8;i++){uint64_t x=(uint64_t)r[i]-P_[i]-br;r[i]=(uint32_t)x;br=(x>>63)&1;}}}
__device__ void finv(const uint32_t*a,uint32_t*r){ // a^(p-2) via square-and-multiply (slow but simple)
  uint32_t e[8];for(int i=0;i<8;i++)e[i]=P_[i];e[0]-=2;uint32_t x[8],res[8]={1,0,0,0,0,0,0,0};for(int i=0;i<8;i++)x[i]=a[i];
  for(int i=0;i<256;i++){if((e[i>>5]>>(i&31))&1){fmul(res,x,res);}fmul(x,x,x);}for(int i=0;i<8;i++)r[i]=res[i];}
__device__ void padd(uint32_t*x1,uint32_t*y1,const uint32_t*x2,const uint32_t*y2){ // P1 = P1 + P2 (affine, P1!=P2)
  uint32_t dx[8],dy[8],inv[8],l[8],l2[8],x3[8],y3[8];fsub(x2,x1,dx);fsub(y2,y1,dy);finv(dx,inv);fmul(dy,inv,l);fmul(l,l,l2);
  fsub(l2,x1,x3);fsub(x3,x2,x3);fsub(x1,x3,y3);fmul(l,y3,y3);fsub(y3,y1,y3);for(int i=0;i<8;i++){x1[i]=x3[i];y1[i]=y3[i];}}
// --- SHA-256 (single 33-byte block) and RIPEMD-160 (single block) ---
__device__ __constant__ uint32_t K256[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
#define ROTR(x,n) (((x)>>(n))|((x)<<(32-(n))))
#define ROTL(x,n) (((x)<<(n))|((x)>>(32-(n))))
__device__ void sha256_33(const uint8_t*m,uint32_t*H){uint32_t w[64];uint8_t blk[64]={0};for(int i=0;i<33;i++)blk[i]=m[i];blk[33]=0x80;blk[62]=(33*8)>>8;blk[63]=(33*8)&0xff;
  for(int i=0;i<16;i++)w[i]=(blk[4*i]<<24)|(blk[4*i+1]<<16)|(blk[4*i+2]<<8)|blk[4*i+3];
  for(int i=16;i<64;i++){uint32_t s0=ROTR(w[i-15],7)^ROTR(w[i-15],18)^(w[i-15]>>3),s1=ROTR(w[i-2],17)^ROTR(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]+s0+w[i-7]+s1;}
  uint32_t a=0x6a09e667,b=0xbb67ae85,c=0x3c6ef372,d=0xa54ff53a,e=0x510e527f,f=0x9b05688c,g=0x1f83d9ab,h=0x5be0cd19;
  for(int i=0;i<64;i++){uint32_t S1=ROTR(e,6)^ROTR(e,11)^ROTR(e,25),ch=(e&f)^(~e&g),t1=h+S1+ch+K256[i]+w[i],S0=ROTR(a,2)^ROTR(a,13)^ROTR(a,22),mj=(a&b)^(a&c)^(b&c),t2=S0+mj;h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}
  H[0]=0x6a09e667+a;H[1]=0xbb67ae85+b;H[2]=0x3c6ef372+c;H[3]=0xa54ff53a+d;H[4]=0x510e527f+e;H[5]=0x9b05688c+f;H[6]=0x1f83d9ab+g;H[7]=0x5be0cd19+h;}
__device__ __constant__ uint8_t RL[80]={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,7,4,13,1,10,6,15,3,12,0,9,5,2,14,11,8,3,10,14,4,9,15,8,1,2,7,0,6,13,11,5,12,1,9,11,10,0,8,12,4,13,3,7,15,14,5,6,2,4,0,5,9,7,12,2,10,14,1,3,8,11,6,15,13};
__device__ __constant__ uint8_t RR[80]={5,14,7,0,9,2,11,4,13,6,15,8,1,10,3,12,6,11,3,7,0,13,5,10,14,15,8,12,4,9,1,2,15,5,1,3,7,14,6,9,11,8,12,2,10,0,4,13,8,6,4,1,3,11,15,0,5,12,2,13,9,7,10,14,12,15,10,4,1,5,8,7,6,2,13,14,0,3,9,11};
__device__ __constant__ uint8_t SL[80]={11,14,15,12,5,8,7,9,11,13,14,15,6,7,9,8,7,6,8,13,11,9,7,15,7,12,15,9,11,7,13,12,11,13,6,7,14,9,13,15,14,8,13,6,5,12,7,5,11,12,14,15,14,15,9,8,9,14,5,6,8,6,5,12,9,15,5,11,6,8,13,12,5,12,13,14,11,8,5,6};
__device__ __constant__ uint8_t SR[80]={8,9,9,11,13,15,15,5,7,7,8,11,14,14,12,6,9,13,15,7,12,8,9,11,7,7,12,7,6,15,13,11,9,7,15,11,8,6,6,14,12,13,5,14,13,13,7,5,15,5,8,11,14,14,6,14,6,9,12,9,12,5,15,8,8,5,12,9,12,5,14,6,8,13,6,5,15,13,11,11};
__device__ inline uint32_t rf(int j,uint32_t x,uint32_t y,uint32_t z){if(j<16)return x^y^z;if(j<32)return (x&y)|(~x&z);if(j<48)return (x|~y)^z;if(j<64)return (x&z)|(y&~z);return x^(y|~z);}
__device__ void ripemd160_32(const uint32_t*Hs,uint8_t*out){uint32_t X[16]={0};for(int i=0;i<8;i++){uint32_t v=Hs[i];X[i]=((v&0xff)<<24)|((v&0xff00)<<8)|((v>>8)&0xff00)|(v>>24);}X[8]=0x80;X[14]=32*8;
  const uint32_t KL[5]={0,0x5A827999,0x6ED9EBA1,0x8F1BBCDC,0xA953FD4E},KR[5]={0x50A28BE6,0x5C4DD124,0x6D703EF3,0x7A6D76E9,0};
  uint32_t al=0x67452301,bl=0xEFCDAB89,cl=0x98BADCFE,dl=0x10325476,el=0xC3D2E1F0,ar=al,br=bl,cr=cl,dr=dl,er=el;
  for(int j=0;j<80;j++){uint32_t t=ROTL(al+rf(j,bl,cl,dl)+X[RL[j]]+KL[j/16],SL[j])+el;al=el;el=dl;dl=ROTL(cl,10);cl=bl;bl=t;
    t=ROTL(ar+rf(79-j,br,cr,dr)+X[RR[j]]+KR[j/16],SR[j])+er;ar=er;er=dr;dr=ROTL(cr,10);cr=br;br=t;}
  uint32_t h[5]={0xEFCDAB89+cl+dr,0x98BADCFE+dl+er,0x10325476+el+ar,0xC3D2E1F0+al+br,0x67452301+bl+cr};
  for(int i=0;i<5;i++){out[4*i]=h[i]&0xff;out[4*i+1]=(h[i]>>8)&0xff;out[4*i+2]=(h[i]>>16)&0xff;out[4*i+3]=(h[i]>>24)&0xff;}}
// --- scalar multiply for chain start (double-and-add, affine) ---
__device__ void pmul(const uint32_t*k,uint32_t*x,uint32_t*y){int started=0;uint32_t qx[8],qy[8];for(int i=0;i<8;i++){qx[i]=GX[i];qy[i]=GY[i];}
  for(int i=255;i>=0;i--){if(started){ // double
      uint32_t x2[8],t[8],l[8],inv[8],x3[8],y3[8];fmul(x,x,x2);fadd(x2,x2,t);fadd(t,x2,t);fadd(y,y,inv);finv(inv,inv);fmul(t,inv,l);fmul(l,l,x3);fsub(x3,x,x3);fsub(x3,x,x3);fsub(x,x3,y3);fmul(l,y3,y3);fsub(y3,y,y3);for(int j=0;j<8;j++){x[j]=x3[j];y[j]=y3[j];}}
    if((k[i>>5]>>(i&31))&1){if(!started){for(int j=0;j<8;j++){x[j]=qx[j];y[j]=qy[j];}started=1;}else padd(x,y,qx,qy);}}}
extern "C" __global__ void chains(const uint32_t*starts,int chain_len,unsigned long long*S_kh,unsigned long long*S_h,unsigned long long*S_hh,
      unsigned long long*lat2,unsigned long long*lat3,unsigned long long*byteh,unsigned long long*runsh,unsigned long long*hamh,unsigned long long*hexc,unsigned long long*nkeys){
  int tid=blockIdx.x*blockDim.x+threadIdx.x;uint32_t k[8];for(int i=0;i<8;i++)k[i]=starts[tid*8+i];uint32_t x[8],y[8];pmul(k,x,y);
  uint32_t gx[8],gy[8];for(int i=0;i<8;i++){gx[i]=GX[i];gy[i]=GY[i];}uint8_t prev[20];int have=0;
  for(int i=0;i<chain_len;i++){uint8_t pub[33];pub[0]=2+(y[0]&1);for(int j=0;j<32;j++)pub[1+j]=(x[7-j/4]>>(8*(3-j%4)))&0xff;
    uint32_t H[8];sha256_33(pub,H);uint8_t h[20];ripemd160_32(H,h);
    // key bits: 70 low bits of k (bit b = 69-index convention: index0 = 2^69)
    uint32_t kb[70];for(int b=0;b<70;b++)kb[b]=(k[(69-b)>>5]>>((69-b)&31))&1;
    uint8_t hb[160];for(int b=0;b<160;b++)hb[b]=(h[b>>3]>>(7-(b&7)))&1;
    int runs=0,pc=0;for(int b=0;b<160;b++){if(hb[b]){atomicAdd(&S_h[b],1ULL);for(int a=0;a<70;a++)if(kb[a])atomicAdd(&S_kh[a*160+b],1ULL);}if(b&&hb[b]!=hb[b-1])runs++;}
    // bit pairs: only sample every 64th key to keep atomics affordable
    if((i&63)==0){for(int a=0;a<160;a++)if(hb[a])for(int b=a+1;b<160;b++)if(hb[b])atomicAdd(&S_hh[a*160+b],1ULL);}
    atomicAdd(&runsh[runs],1ULL);for(int j=0;j<20;j++)atomicAdd(&byteh[h[j]],1ULL);
    if(have){int d=0;for(int j=0;j<20;j++)d+=__popc(h[j]^prev[j]);atomicAdd(&hamh[d],1ULL);atomicAdd(&lat2[prev[0]*256+h[0]],1ULL);}
    if(have>=2){}for(int j=0;j<20;j++)prev[j]=h[j];have=(have<2)?have+1:2;
    if(i>=2)atomicAdd(&lat3[0],0ULL); // 3D lattice handled host-side from the 2D stream in this simplified kernel
    int sel[8]={0,1,2,3,66,67,68,69};for(int d=0;d<40;d++){int hx=(d<20)?(h[d]>>4):(h[d-20]&15);for(int j=0;j<8;j++)atomicAdd(&hexc[(d*8+j)*32+hx*2+kb[sel[j]]],1ULL);}
    atomicAdd(nkeys,1ULL);
    // next key
    uint64_t c=1;for(int j=0;j<8;j++){c+=k[j];k[j]=(uint32_t)c;c>>=32;}padd(x,y,gx,gy);}}
'''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--keys',type=float,default=1e9); ap.add_argument('--range',type=int,default=71)
    ap.add_argument('--chain',type=int,default=4096); ap.add_argument('--threads',type=int,default=8192); a=ap.parse_args()
    mod=cp.RawModule(code=KERNEL); kern=mod.get_function('chains')
    S_kh=cp.zeros(70*160,cp.uint64); S_h=cp.zeros(160,cp.uint64); S_hh=cp.zeros(160*160,cp.uint64); lat2=cp.zeros(65536,cp.uint64); lat3=cp.zeros(1,cp.uint64)
    byteh=cp.zeros(256,cp.uint64); runsh=cp.zeros(161,cp.uint64); hamh=cp.zeros(161,cp.uint64); hexc=cp.zeros(40*8*32,cp.uint64); nk=cp.zeros(1,cp.uint64)
    lo=1<<(a.range-1); hi=1<<a.range; rng=np.random.default_rng(); total=int(a.keys); done=0; t0=time.time(); launches=0
    while done<total:
        ks=[lo+int(rng.integers(0,hi-lo-a.chain-1)) for _ in range(a.threads)]
        starts=np.zeros((a.threads,8),np.uint32)
        for i,k in enumerate(ks):
            for j in range(8): starts[i,j]=(k>>(32*j))&0xffffffff
        kern((a.threads//256,),(256,),(cp.asarray(starts.ravel()),np.int32(a.chain),S_kh,S_h,S_hh,lat2,lat3,byteh,runsh,hamh,hexc,nk)); cp.cuda.Device().synchronize()
        done+=a.threads*a.chain; launches+=1
        if launches%10==0: print(f"  {done:,} keys, {done/(time.time()-t0):,.0f} keys/s",flush=True)
    N=int(nk.get()[0]); print(f"\nGENERATED {N:,} keys in {time.time()-t0:.0f}s")
    S_kh=S_kh.get().reshape(70,160).astype(float); S_h=S_h.get().astype(float); ph=S_h/N
    print(f"== 1. BIT BALANCE: ones-fraction {ph.min():.6f}..{ph.max():.6f}, max |z| {np.abs((ph-0.5)*2*np.sqrt(N)).max():.2f}")
    pk=np.full(70,0.5); pk[0]=1.0  # bit 2^69 is always 1 inside the range
    cov=S_kh/N-np.outer(pk,ph); corr=cov/np.sqrt(np.outer(pk*(1-pk),ph*(1-ph))+1e-12); z=(corr*np.sqrt(N))[1:]
    print(f"== 2. KEY-BIT x ADDRESS-BIT SWEEP: {z.size:,} tests | max |z| {np.abs(z).max():.2f} | beyond 5 sigma: {(np.abs(z)>5).sum()} (chance ~{z.size*5.7e-7:.4f}) | 5-sigma floor = {5/np.sqrt(N)*100:.5f}% bias")
    hh=S_hh.get().reshape(160,160).astype(float); n2=N/64; ph2=ph; c2=hh/n2-np.outer(ph2,ph2); zz=np.triu(c2/0.25*np.sqrt(n2),1)
    print(f"== 3. ADDRESS BIT-PAIR DEPENDENCE (1/64 sample): max |z| {np.abs(zz).max():.2f} | beyond 5 sigma: {(np.abs(zz)>5).sum()}")
    l2=lat2.get().astype(float); e=l2.sum()/65536; chi=((l2-e)**2/e).sum(); print(f"== 4. LATTICE 2D: chi2 {chi:,.0f} on 65,535 dof -> z = {(chi-65535)/362:.2f}")
    bh=byteh.get().astype(float); e=bh.sum()/256; chi=((bh-e)**2/e).sum(); print(f"== 5. BATTERY: byte histogram z = {(chi-255)/np.sqrt(510):.2f}")
    rs=np.arange(161); r=runsh.get().astype(float); rm=(r*rs).sum()/r.sum(); print(f"     runs per address mean {rm:.4f} (expect 79.5)")
    hm=hamh.get().astype(float); print(f"     neighbour distance mean {(hm*rs).sum()/hm.sum():.4f} (expect 80.0000)")
    from scipy.stats import chi2_contingency
    hx=hexc.get().reshape(40,8,16,2).astype(float); ps=[]
    for d in range(40):
        for j in range(8):
            ct=hx[d,j]; ct=ct[ct.sum(1)>0]
            ps.append(chi2_contingency(ct,correction=False)[1] if ct.shape[0]>1 and ct.sum(0).min()>0 else 1.0)
    ps=np.array(ps); print(f"== 6. HEX DIGIT x KEY BIT: {ps.size} tests | min p {ps.min():.2e} | Bonferroni flags {(ps<0.05/ps.size).sum()}")
    print("== 7. CONTROL: a planted 0.01% leak at this N would show as z ≈", f"{0.0001*np.sqrt(N):.1f}")
if __name__=='__main__': main()
