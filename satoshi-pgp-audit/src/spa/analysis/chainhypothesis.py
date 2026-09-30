"""Test whether an ordered set of public keys was DETERMINISTICALLY CHAINED.

THE HYPOTHESIS
--------------
"Satoshi did not store 22,000 keys; each wallet derived the next, so he only had to
remember the first." If true, there is a public rule d_{n+1} = f(key_n) linking each
private key to the one before it. Any such rule leaves a signature in the PUBLIC
keys, detectable with no private data:

    next_priv = H(prev_pub)   =>   H(prev_pub) * G  ==  next_pub        (hash chain)
    next_priv = prev_x mod N  =>   (prev_pub.x)  * G  ==  next_pub        (x-as-key)
    next_priv = c * prev_priv =>   c * prev_pub      ==  next_pub        (multiplicative)
    next_priv = prev_priv + c =>   prev_pub + c*G    ==  next_pub        (additive)

The additive case is already covered by spa.analysis.relatedkeys (delta scan, 0 hits
to 2048). This module tests the hash-chain, x-as-key, and multiplicative families -
the literal "each wallet unlocks the next" constructions.

WHY IT IS CHEAP TO SETTLE
-------------------------
A deterministic chain rule must hold for EVERY consecutive pair. So it is enough to
test the rule on the first N ordered pairs: if it fails on even one, it is not a
global chain. That turns a 22k-key question into a few-hundred-operation check. A
rule that matches every sampled pair is then escalated to the full set.

EXPECTED RESULT: no rule holds. Bitcoin 0.1 drew each key from OpenSSL's RNG and
stored them all in wallet.dat; there was no derivation chain. But this converts that
historical fact into a measurement over the actual keys.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from . import bitcoin_scope as bs

Point = Tuple[int, int]


def _sha256(b: bytes) -> int:
    return int.from_bytes(hashlib.sha256(b).digest(), "big")


def _hash256(b: bytes) -> int:
    return int.from_bytes(hashlib.sha256(hashlib.sha256(b).digest()).digest(), "big")


def _compressed(pt: Point) -> bytes:
    x, y = pt
    return bytes([2 + (y & 1)]) + x.to_bytes(32, "big")


def _uncompressed(pt: Point) -> bytes:
    x, y = pt
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


# Each rule maps a previous public point to a CANDIDATE next private scalar.
# All are computable from public data alone.
def _rules():
    rules: List[Tuple[str, Callable[[Point], int]]] = [
        ("next_priv = SHA256(prev_pub_compressed)",
         lambda p: _sha256(_compressed(p)) % bs.N),
        ("next_priv = SHA256(prev_pub_uncompressed)",
         lambda p: _sha256(_uncompressed(p)) % bs.N),
        ("next_priv = SHA256(prev_pub.x)",
         lambda p: _sha256(p[0].to_bytes(32, "big")) % bs.N),
        ("next_priv = HASH256(prev_pub_compressed)",
         lambda p: _hash256(_compressed(p)) % bs.N),
        ("next_priv = prev_pub.x mod N",
         lambda p: p[0] % bs.N),
    ]
    return rules


@dataclass
class ChainRuleResult:
    name: str
    pairs_tested: int
    pairs_matched: int
    holds: bool
    kind: str = "hash/scalar"


@dataclass
class ChainFindings:
    keys: int = 0
    pairs_sampled: int = 0
    results: List[ChainRuleResult] = field(default_factory=list)
    multiplicative_tested: List[int] = field(default_factory=list)
    control_rule_detected: Optional[bool] = None
    notes: List[str] = field(default_factory=list)

    @property
    def any_chain_holds(self) -> bool:
        return any(r.holds for r in self.results)


def test_chain(pubkeys: List[Point], sample: int = 200,
               multiplicative_scalars: Optional[List[int]] = None) -> ChainFindings:
    """Test deterministic-chain rules over an ORDERED list of public keys.

    ``pubkeys`` must already be in the order the chain would follow (e.g. by block
    height). A rule 'holds' only if it matches EVERY sampled consecutive pair.
    """
    f = ChainFindings(keys=len(pubkeys))
    if len(pubkeys) < 2:
        f.notes.append("Need at least two ordered keys.")
        return f
    n_pairs = min(sample, len(pubkeys) - 1)
    f.pairs_sampled = n_pairs

    # Hash / x-as-key rules.
    for name, rule in _rules():
        matched = 0
        for i in range(n_pairs):
            prev, nxt = pubkeys[i], pubkeys[i + 1]
            try:
                cand = rule(prev)
                if cand and bs.point_mul(cand) == nxt:
                    matched += 1
                else:
                    break        # a global chain must match every pair; stop early
            except Exception:
                break
        f.results.append(ChainRuleResult(
            name=name, pairs_tested=i + 1 if n_pairs else 0,
            pairs_matched=matched, holds=(matched == n_pairs and n_pairs > 0)))

    # Multiplicative rules: next_pub == c * prev_pub for a fixed small c.
    scalars = multiplicative_scalars or [2, 3, 5, 7, 11, 13, 257, 65537]
    for c in scalars:
        matched = 0
        for i in range(n_pairs):
            prev, nxt = pubkeys[i], pubkeys[i + 1]
            try:
                if bs.point_mul(c, prev) == nxt:
                    matched += 1
                else:
                    break
            except Exception:
                break
        f.multiplicative_tested.append(c)
        f.results.append(ChainRuleResult(
            name="next_pub = %d * prev_pub" % c, pairs_tested=i + 1 if n_pairs else 0,
            pairs_matched=matched, holds=(matched == n_pairs and n_pairs > 0),
            kind="multiplicative"))

    if f.any_chain_holds:
        f.notes.append(
            "A deterministic chain rule matched every sampled pair. Escalate to the "
            "full key set to confirm - if it holds throughout, the keys ARE chained "
            "and each private key is derivable from the first.")
    else:
        f.notes.append(
            "No tested chain rule holds. The keys are not linked by hash-of-previous, "
            "x-as-next-key, or small multiplicative derivation. Combined with the "
            "additive scan (0 relations to delta 2048), the common 'each wallet "
            "unlocks the next' constructions are ruled out - consistent with Bitcoin "
            "0.1 drawing each key independently from the RNG and storing them all.")
    return f


def make_control_chain(length: int = 50, rule_index: int = 0) -> List[Point]:
    """Build a synthetic chain where next_priv = SHA256(prev_pub_compressed).

    The tester MUST detect this, or its negative on real data is meaningless.
    """
    import secrets
    d0 = secrets.randbelow(bs.N - 1) + 1
    priv = d0
    pubs: List[Point] = []
    for _ in range(length):
        pt = bs.point_mul(priv)
        pubs.append(pt)
        priv = _sha256(_compressed(pt)) % bs.N or 1
    return pubs
