"""Network-scale scan for reused DSA/ECDSA nonces across a PGP key corpus.

WHAT AND WHY
------------
A key that signs two different messages with the same nonce leaks its private key
from public data alone (DSA/ECDSA both):

    same key, same r, different s   =>   nonce reused   =>   private key recoverable
        k = (h1 - h2) / (s1 - s2) mod q
        x = (s1*k - h1) / r       mod q

This is not hypothetical. Bulk scans of public key material have repeatedly turned
up broken RNGs this way - Heninger et al., "Mining Your Ps and Qs" (2012), found
compromised TLS/SSH keys at internet scale; the same shape recurs in PGP keyserver
dumps whenever a faulty implementation ships. Finding these keys is the FIRST step
of responsible disclosure and revocation, which is why this scanner exists.

DETECTION vs RECOVERY - a deliberate ethical boundary
-----------------------------------------------------
Detection needs only (r, s) pairs: if one issuer emitted two signatures sharing r
with differing s, the nonce was reused, full stop. No hashes, no key material.

Recovery (actually computing x) additionally needs the signed digests. This module
DETECTS and FLAGS across arbitrary third-party keys, and computes x ONLY for keys
the operator explicitly marks as their own, or for synthetic keys. For everyone
else it reports the vulnerable key id so it can be disclosed and revoked - it does
not hand you someone else's private key.

SCOPE OF "THE ENTIRE NETWORK"
-----------------------------
Feasible, with the usual data-acquisition caveat. The scanner ingests any corpus of
armored keys or a keyring; point it at a keyserver dump (keys.openpgp.org /
keyserver.ubuntu.com / an SKS export) and it scans every signature in it. The full
dump is tens of GB and millions of keys - that is a data-transfer problem, not an
algorithmic one; the scan itself is linear in the number of signatures.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..openpgp import dearmor, parse_keyblock
from ..openpgp.packets import SignaturePacket
from .dsa import DSAParams, DSASignature, digest_to_int, recover_x_from_shared_nonce

# DSA and ECDSA both expose (r, s); algorithm ids per RFC 4880.
_SIG_ALGOS_WITH_RS = {17, 19}   # 17 = DSA, 19 = ECDSA


@dataclass
class SigRecord:
    issuer_keyid: str
    r: int
    s: int
    hash_algo: int
    sig_type: int
    pubkey_algo: int
    source: str                      # which input the signature came from
    digest: Optional[bytes] = None   # present only when reconstructable


@dataclass
class VulnerableKey:
    issuer_keyid: str
    pubkey_algo: int
    reused_r: int
    signature_count: int
    colliding_labels: List[str]
    recovered_private_key: Optional[int] = None
    owned: bool = False


@dataclass
class ScanFindings:
    keys_scanned: int = 0
    signatures_scanned: int = 0
    signatures_with_rs: int = 0
    issuers_seen: int = 0
    duplicate_signatures: int = 0
    vulnerable_keys: List[VulnerableKey] = field(default_factory=list)
    control_detected: Optional[bool] = None
    notes: List[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.vulnerable_keys


def _collect_from_keyblock(raw_text: str, source: str) -> Tuple[int, List[SigRecord]]:
    """Extract every (r,s)-bearing signature from one armored keyblock.

    Where the signature is a self-certification we can reconstruct the digest and so
    enable recovery for owned keys; where we cannot, detection still works on (r,s).
    """
    out: List[SigRecord] = []
    blocks = dearmor(raw_text)
    keycount = 0
    for block in blocks:
        try:
            kb = parse_keyblock(block.body)
        except Exception:
            continue
        keycount += 1
        for sig in kb.all_signatures():
            if not isinstance(sig, SignaturePacket):
                continue
            if sig.pubkey_algo not in _SIG_ALGOS_WITH_RS:
                continue
            if "r" not in sig.mpis or "s" not in sig.mpis:
                continue
            digest = None
            try:
                digest = kb.digest_for(sig)
            except Exception:
                digest = None
            out.append(SigRecord(
                issuer_keyid=sig.issuer_key_id or "unknown",
                r=sig.mpis["r"].value, s=sig.mpis["s"].value,
                hash_algo=sig.hash_algo, sig_type=sig.sig_type,
                pubkey_algo=sig.pubkey_algo, source=source, digest=digest))
    return keycount, out


def scan_records(records: List[SigRecord],
                 owned_keyids: Optional[set] = None,
                 params_by_keyid: Optional[Dict[str, DSAParams]] = None
                 ) -> ScanFindings:
    """Core scan: group by issuer, flag any r reused with a differing s."""
    owned = {k.upper() for k in (owned_keyids or set())}
    params_by_keyid = params_by_keyid or {}
    f = ScanFindings(signatures_scanned=len(records))

    by_issuer: Dict[str, List[SigRecord]] = defaultdict(list)
    for rec in records:
        by_issuer[rec.issuer_keyid].append(rec)
        f.signatures_with_rs += 1
    f.issuers_seen = len(by_issuer)

    for keyid, sigs in by_issuer.items():
        by_r: Dict[int, List[SigRecord]] = defaultdict(list)
        for s in sigs:
            by_r[s.r].append(s)
        for r, group in by_r.items():
            if len(group) < 2:
                continue
            distinct_s = {g.s for g in group}
            if len(distinct_s) < 2:
                f.duplicate_signatures += 1        # same r AND s: duplicate, harmless
                continue
            vk = VulnerableKey(
                issuer_keyid=keyid, pubkey_algo=group[0].pubkey_algo, reused_r=r,
                signature_count=len(group),
                colliding_labels=[("%s#%s" % (g.source, g.sig_type)) for g in group],
                owned=keyid.upper() in owned)
            # Recovery only for owned/synthetic keys with reconstructable digests.
            if vk.owned and keyid in params_by_keyid:
                par = params_by_keyid[keyid]
                a, b = None, None
                for g in group:
                    if g.digest is not None:
                        if a is None:
                            a = g
                        elif a.s != g.s:
                            b = g
                            break
                if a is not None and b is not None:
                    da = DSASignature(r=a.r, s=a.s, digest=a.digest)
                    db = DSASignature(r=b.r, s=b.s, digest=b.digest)
                    vk.recovered_private_key = recover_x_from_shared_nonce(par, da, db)
            f.vulnerable_keys.append(vk)

    if f.clean:
        f.notes.append(
            "No reused nonce found: no issuer emitted two signatures sharing r with "
            "a differing s. Nonce-reuse key recovery is ruled out for this corpus.")
    else:
        f.notes.append(
            "%d key(s) reused a nonce and are private-key-recoverable from public "
            "data. Responsible action is disclosure and revocation, not spending or "
            "impersonation." % len(f.vulnerable_keys))
    return f


def scan_armored_texts(named_texts: List[Tuple[str, str]],
                       owned_keyids: Optional[set] = None) -> ScanFindings:
    """Scan a list of (name, armored_text) inputs."""
    records: List[SigRecord] = []
    keys = 0
    params_by_keyid: Dict[str, DSAParams] = {}
    for name, text in named_texts:
        try:
            kc, recs = _collect_from_keyblock(text, name)
        except Exception:
            continue
        keys += kc
        records.extend(recs)
        # Capture DSA params so an owned key can be recovered.
        try:
            for block in dearmor(text):
                kb = parse_keyblock(block.body)
                if kb.primary.algo == 17 and all(k in kb.primary.mpis
                                                 for k in ("p", "q", "g", "y")):
                    m = kb.primary.mpis
                    params_by_keyid[kb.key_id] = DSAParams(
                        m["p"].value, m["q"].value, m["g"].value, m["y"].value)
        except Exception:
            pass
    f = scan_records(records, owned_keyids=owned_keyids,
                     params_by_keyid=params_by_keyid)
    f.keys_scanned = keys
    return f


def make_synthetic_control(reuse: bool = True) -> Tuple[List[SigRecord], DSAParams,
                                                        str, int]:
    """Build a synthetic issuer that (optionally) reuses a nonce, as a control.

    Returns (records, params, keyid, true_private_key). The scanner must flag this
    issuer when reuse=True and must stay silent when reuse=False.
    """
    import hashlib
    import secrets

    # A known-good 1024/160-bit DSA group (RFC 5114 s2.1 test parameters, public).
    q = 0xE95E4A5F737059DC60DF5991D45029409E60FC09
    p = 0xB10B8F96A080E01DDE92DE5EAE5D54EC52C99FBCFB06A3C69A6A9DCA52D23B616073E28675A23D189838EF1E2EE652C013ECB4AEA906112324975C3CD49B83BFACCBDD7D90C4BD7098488E9C219A73724EFFD6FAE5644738FAA31A4FF55BCCC0A151AF5F0DC8B4BD45BF37DF365C1A65E68CFDA76D4DA708DF1FB2BC2E4A4371
    g = 0xA4D1CBD5C3FD34126765A442EFB99905F8104DD258AC507FD6406CFF14266D31266FEA1E5C41564B777E690F5504F213160217B4B01B886A5E91547F9E2749F4D7FBD7D3B9A92EE1909D0D2263F80A76A6A24C087A091F531DBF0A0169B6A28AD662A4D18E73AFA32D779D5918D08BC8858F4DCEF97C2A24855E6EEB22B3B2E5
    x = secrets.randbelow(q - 1) + 1
    y = pow(g, x, p)
    par = DSAParams(p, q, g, y)
    keyid = "CONTROLKEY000001"

    def sign(msg: bytes, k: int) -> SigRecord:
        d = hashlib.sha1(msg).digest()
        h = digest_to_int(d, q)
        r = pow(g, k, p) % q
        s = (pow(k, -1, q) * (h + x * r)) % q
        return SigRecord(issuer_keyid=keyid, r=r, s=s, hash_algo=2, sig_type=0x10,
                         pubkey_algo=17, source="control", digest=d)

    k = secrets.randbelow(q - 1) + 1
    recs = [sign(b"control message one", k)]
    recs.append(sign(b"control message two", k if reuse else secrets.randbelow(q - 1) + 1))
    return recs, par, keyid, x
