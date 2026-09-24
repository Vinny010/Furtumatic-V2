import hashlib, json
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
def inv(a): return pow(a, P-2, P)
def add(A,B):
    if A is None: return B
    if B is None: return A
    (x1,y1),(x2,y2)=A,B
    if x1==x2 and (y1+y2)%P==0: return None
    m = (3*x1*x1)*inv(2*y1)%P if A==B else (y2-y1)*inv(x2-x1)%P
    x3=(m*m-x1-x2)%P; return (x3,(m*(x1-x3)-y1)%P)
def mul(k,Pt):
    R=None
    while k:
        if k&1: R=add(R,Pt)
        Pt=add(Pt,Pt); k>>=1
    return R
# RIPEMD-160 (pure python; hashlib may lack it)
def ripemd160(msg):
    try: return hashlib.new('ripemd160', msg).digest()
    except Exception: pass
    import struct
    def rol(x,n): return ((x<<n)|(x>>(32-n)))&0xffffffff
    r=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,7,4,13,1,10,6,15,3,12,0,9,5,2,14,11,8,3,10,14,4,9,15,8,1,2,7,0,6,13,11,5,12,1,9,11,10,0,8,12,4,13,3,7,15,14,5,6,2,4,0,5,9,7,12,2,10,14,1,3,8,11,6,15,13]
    rr=[5,14,7,0,9,2,11,4,13,6,15,8,1,10,3,12,6,11,3,7,0,13,5,10,14,15,8,12,4,9,1,2,15,5,1,3,7,14,6,9,11,8,12,2,10,0,4,13,8,6,4,1,3,11,15,0,5,12,2,13,9,7,10,14,12,15,10,4,1,5,8,7,6,2,13,14,0,3,9,11]
    s=[11,14,15,12,5,8,7,9,11,13,14,15,6,7,9,8,7,6,8,13,11,9,7,15,7,12,15,9,11,7,13,12,11,13,6,7,14,9,13,15,14,8,13,6,5,12,7,5,11,12,14,15,14,15,9,8,9,14,5,6,8,6,5,12,9,15,5,11,6,8,13,12,5,12,13,14,11,8,5,6]
    ss=[8,9,9,11,13,15,15,5,7,7,8,11,14,14,12,6,9,13,15,7,12,8,9,11,7,7,12,7,6,15,13,11,9,7,15,11,8,6,6,14,12,13,5,14,13,13,7,5,15,5,8,11,14,14,6,14,6,9,12,9,12,5,15,8,8,5,12,9,12,5,14,6,8,13,6,5,15,13,11,11]
    K=[0,0x5a827999,0x6ed9eba1,0x8f1bbcdc,0xa953fd4e]; KK=[0x50a28be6,0x5c4dd124,0x6d703ef3,0x7a6d76e9,0]
    def f(j,x,y,z):
        if j<16: return x^y^z
        if j<32: return (x&y)|(~x&z)
        if j<48: return (x|~y)^z
        if j<64: return (x&z)|(y&~z)
        return x^(y|~z)
    h=[0x67452301,0xefcdab89,0x98badcfe,0x10325476,0xc3d2e1f0]
    ml=len(msg); msg+=b'\x80'; msg+=b'\x00'*((56-len(msg)%64)%64); msg+=struct.pack('<Q',ml*8)
    for off in range(0,len(msg),64):
        X=list(struct.unpack('<16I',msg[off:off+64]))
        a,b,c,d,e=h; aa,bb,cc,dd,ee=h
        for j in range(80):
            t=(rol((a+f(j,b,c,d)+X[r[j]]+K[j//16])&0xffffffff,s[j])+e)&0xffffffff
            a,e,d,c,b=e,d,rol(c,10),b,t
            t=(rol((aa+f(79-j,bb,cc,dd)+X[rr[j]]+KK[j//16])&0xffffffff,ss[j])+ee)&0xffffffff
            aa,ee,dd,cc,bb=ee,dd,rol(cc,10),bb,t
        t=(h[1]+c+dd)&0xffffffff
        h=[t,(h[2]+d+ee)&0xffffffff,(h[3]+e+aa)&0xffffffff,(h[4]+a+bb)&0xffffffff,(h[0]+b+cc)&0xffffffff]
    return struct.pack('<5I',*h)
B58='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def b58check(payload):
    d=payload+hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    n=int.from_bytes(d,'big'); s=''
    while n: n,rem=divmod(n,58); s=B58[rem]+s
    return '1'*(len(d)-len(d.lstrip(b'\0')))+s
def record(k):
    x,y=mul(k,(Gx,Gy))
    comp=(b'\x02' if y%2==0 else b'\x03')+x.to_bytes(32,'big')
    addr=b58check(b'\x00'+ripemd160(hashlib.sha256(comp).digest()))
    return dict(k=k,pub=comp.hex(),x=x/2**256,y=y/2**256,addr=addr)
