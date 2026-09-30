# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "scikit-learn>=1.3"]
# ///
"""
BIG TEST: does the key -> pubkey -> address mapping leak anything about the key?
  * 1,000,000 consecutive keys inside the puzzle-#71 range (2^70 + offset + i)
  * 20,000 fully random 71-bit keys (all 71 key bits vary)
For every key: X coordinate of k*G (256 bits) and hash160 of the compressed pubkey (160 bits) — the address.
Tests:
  1. bit balance: every output bit ~50% ones?
  2. ALL key-bit x output-bit correlations (thousands of pairs), Bonferroni at 5 sigma
  3. gradient-boosted classifier: can ANY combination of 160 address bits predict a key bit, out of sample?
  4. neighbour test: hash160 distance between key k and k+1 (should be ~80 +- 6.3 bits)
  5. CONTROL: the same pipeline on data with a planted 1% leak (must be caught) and on true-random bytes (must not)
"""
import hashlib, os, sys, time, secrets, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ec_lib import add, mul, Gx, Gy, ripemd160
try:
    hashlib.new('ripemd160', b''); RMD = lambda b: hashlib.new('ripemd160', b).digest()
except Exception:
    RMD = ripemd160
def h160(x, y):
    comp = (b'\x02' if y % 2 == 0 else b'\x03') + x.to_bytes(32, 'big')
    return RMD(hashlib.sha256(comp).digest())

t0 = time.time()
N = 1_000_000
k0 = (1 << 70) + secrets.randbelow((1 << 70) - N - 1)          # random spot inside #71's range
P = mul(k0, (Gx, Gy)); G = (Gx, Gy)
X = np.zeros((N, 32), np.uint8); H = np.zeros((N, 20), np.uint8); K = np.zeros(N, np.uint64)
for i in range(N):
    X[i] = np.frombuffer(P[0].to_bytes(32, 'big'), np.uint8); H[i] = np.frombuffer(h160(*P), np.uint8); K[i] = i   # low bits of k vary
    P = add(P, G)
print(f"consecutive set: {N:,} keys from k0=2^70+{k0-(1<<70)} in {time.time()-t0:.0f}s", flush=True)

t1 = time.time(); NR = 20_000
XR = np.zeros((NR, 32), np.uint8); HR = np.zeros((NR, 20), np.uint8); KR = np.zeros((NR, 9), np.uint8)
for i in range(NR):
    k = (1 << 70) | secrets.randbelow(1 << 70); Q = mul(k, G)
    XR[i] = np.frombuffer(Q[0].to_bytes(32, 'big'), np.uint8); HR[i] = np.frombuffer(h160(*Q), np.uint8); KR[i] = np.frombuffer(k.to_bytes(9, 'big'), np.uint8)
print(f"random set: {NR:,} full 71-bit keys in {time.time()-t1:.0f}s", flush=True)

bits = lambda A: np.unpackbits(A, axis=1)
def corr_scan(kb, ob, label):
    """z-scores of every key-bit x output-bit correlation; Bonferroni at 5 sigma."""
    kb = kb.astype(np.float32); ob = ob.astype(np.float32); n = len(kb)
    keep = kb.std(0) > 0; kb = kb[:, keep]                      # only key bits that actually vary
    kc = kb - kb.mean(0); oc = ob - ob.mean(0)
    corr = (kc.T @ oc) / (n * kb.std(0)[:, None] * (ob.std(0)[None, :] + 1e-9))
    z = corr * np.sqrt(n); tests = z.size
    print(f"  {label}: {tests:,} key-bit x output-bit tests | max |z| = {np.abs(z).max():.2f} | "
          f"pairs beyond 5 sigma: {(np.abs(z) > 5).sum()}  (pure chance expects ~{tests*5.7e-7:.3f})")
    return np.abs(z).max()
def balance(ob, label):
    p = ob.mean(0); z = (p - 0.5) * 2 * np.sqrt(len(ob))
    print(f"  {label}: {ob.shape[1]} output bits, ones-fraction {p.min():.4f}..{p.max():.4f}, max |z| = {np.abs(z).max():.2f}")
def ml(features, target, label, n_train):
    from sklearn.ensemble import HistGradientBoostingClassifier
    clf = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.1)
    clf.fit(features[:n_train], target[:n_train]); acc = clf.score(features[n_train:], target[n_train:])
    m = len(target) - n_train; ci = 1.96 * np.sqrt(0.25 / m)
    print(f"  {label}: out-of-sample accuracy {acc*100:.2f}%  (coin-flip = 50.00% +- {ci*100:.2f}%)")
    return acc

print("\n== 1. BIT BALANCE ==")
Hb, Xb = bits(H), bits(X); balance(Hb, "address bits (1M keys)"); balance(Xb, "pubkey-X bits (1M keys)")
print("\n== 2. CORRELATION SWEEP ==")
Kb = bits(K.astype('>u8').view(np.uint8).reshape(N, 8))       # 64 bits of i, only low 20 vary
corr_scan(Kb, Hb, "consecutive keys -> address"); corr_scan(Kb, Xb, "consecutive keys -> pubkey X")
KRb = bits(KR); corr_scan(KRb, bits(HR), "random 71-bit keys -> address"); corr_scan(KRb, bits(XR), "random 71-bit keys -> pubkey X")
print("\n== 3. CAN A MODEL PREDICT KEY BITS FROM THE ADDRESS? ==")
for b in (63, 58, 50, 44):   # bit positions in the 64-bit i: 63 = lowest, 44 = 2^19
    ml(Hb, Kb[:, b], f"predict key bit 2^{63-b} from 160 address bits (700k train / 300k test)", 700_000)
KRbits = bits(KR); ml(bits(HR), KRbits[:, 72 - 71 + 1], "predict TOP key bit (which half of #71 range) from address, random keys", 15_000)
ml(bits(HR), KRbits[:, -1], "predict LOWEST key bit from address, random keys", 15_000)
print("\n== 4. NEIGHBOUR TEST ==")
d = (Hb[1:] != Hb[:-1]).sum(1); print(f"  hash160 distance between key k and k+1: mean {d.mean():.2f} bits, std {d.std():.2f}  (independent hashes: 80.00, 6.32)")
print("\n== 5. CONTROLS ==")
leak = Hb.copy(); flip = np.random.rand(N) < 0.02                    # planted: 1% net bias of address bit 7 toward key bit 0
leak[:, 7] = np.where(flip, Kb[:, 63], leak[:, 7])
print("  planted 1%-bias leak (address bit 7 <- key bit 2^0 on 2% of keys):"); corr_scan(Kb, leak, "  planted")
ml(leak, Kb[:, 63], "  planted: predict key bit 2^0", 700_000)
rnd = np.unpackbits(np.frombuffer(os.urandom(N * 20), np.uint8).reshape(N, 20), axis=1)
print("  true-random bytes (no relation to keys):"); corr_scan(Kb, rnd, "  random"); ml(rnd, Kb[:, 63], "  random: predict key bit 2^0", 700_000)
print(f"\ntotal {time.time()-t0:.0f}s")
