"""Address-based range brute force (BitCrack-style) for the Bitcoin Puzzle.

Unlike Kangaroo, this needs ONLY the address (hash160) - no public key. It walks
candidate private keys across a range, derives each address, and compares. That is
the only method for puzzles whose pubkey is NOT exposed.

The trade-off is fundamental: brute force is O(range) with NO square-root shortcut
(that shortcut requires the pubkey). So a range Kangaroo would clear in sqrt(W)
steps costs the full W here. It is the right (only) tool when the pubkey is hidden,
and it is hopeless above ~2^50 on modest hardware - the honest reason the low
unsolved puzzles (#67-69) are farm-scale despite being "low".

Each step is one point addition (P(d+1)=P(d)+G) plus a hash - same per-step cost as
Kangaroo, but you must take W steps instead of sqrt(W).
"""

import hashlib
from dataclasses import dataclass, field
from typing import Optional, Set

from ..analysis import bitcoin_scope as bs

G = (bs.GX, bs.GY)


def _h160(point, compressed: bool) -> bytes:
    x, y = point
    if compressed:
        ser = bytes([2 + (y & 1)]) + x.to_bytes(32, "big")
    else:
        ser = b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")
    return hashlib.new("ripemd160", hashlib.sha256(ser).digest()).digest()


@dataclass
class BruteResult:
    solved: bool
    private_key: Optional[int] = None
    scanned: int = 0
    notes: list = field(default_factory=list)


def scan_range(target_h160: bytes, a: int, b: int,
               both_forms: bool = True, max_scan: Optional[int] = None) -> BruteResult:
    """Search [a, b) for a key whose address hash matches target_h160.

    Checks compressed and (optionally) uncompressed forms each step.
    """
    P = bs.point_mul(a)
    limit = b - a if max_scan is None else min(b - a, max_scan)
    for i in range(limit):
        if _h160(P, True) == target_h160:
            return BruteResult(True, a + i, i + 1, ["matched compressed"])
        if both_forms and _h160(P, False) == target_h160:
            return BruteResult(True, a + i, i + 1, ["matched uncompressed"])
        P = bs.point_add(P, G)
    return BruteResult(False, None, limit,
                       ["no match in %d candidates (range O(W), no shortcut)" % limit])


def demo(bits: int = 20, seed: int = 7) -> BruteResult:
    """Plant a key in [2^(bits-1), 2^bits), derive its address, brute-force it back."""
    import random
    rng = random.Random(seed)
    a, b = 1 << (bits - 1), 1 << bits
    x = rng.randrange(a, b)
    target = _h160(bs.point_mul(x), True)
    r = scan_range(target, a, b)
    r.notes.append("planted x=%d recovered=%s match=%s" % (x, r.private_key, r.private_key == x))
    return r
