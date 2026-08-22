"""Pollard's Kangaroo (lambda method) for the interval ECDLP on secp256k1.

Purpose: solve the PUBLIC Bitcoin Puzzle challenge (github.com/.../1000-bitcoin
puzzle), where keys are deliberately placed in a KNOWN range [2^(n-1), 2^n) and the
public key is exposed. This is a legal, intended challenge. The solver needs the
exposed public key; it cannot run from an address (hash) alone.

No twist beats the proven sqrt(W) lower bound (Shoup, generic groups). The real
speed comes from engineering:
  * distinguished points (store ~1/2^dp of positions, collide herds cheaply)
  * a precomputed jump table (each step is ONE point addition)
  * (extensible) the negation map and secp256k1 endomorphism for constant-factor gains

Expected work ~ 2*sqrt(W) group operations. Feasible on one machine up to ~2^50-ish;
beyond that it is a distributed effort (this engine is written to shard cleanly).
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from ..analysis import bitcoin_scope as bs

Point = Tuple[int, int]
G = (bs.GX, bs.GY)


@dataclass
class KangarooResult:
    solved: bool
    private_key: Optional[int] = None
    operations: int = 0
    distinguished_points: int = 0
    interval_bits: int = 0
    notes: list = field(default_factory=list)


def _jump_index(P: Point, njumps: int) -> int:
    # Deterministic pseudo-random jump selector from the point's x-coordinate.
    return P[0] % njumps


def solve_interval(Q: Point, a: int, b: int, dp_bits: Optional[int] = None,
                   max_ops: Optional[int] = None, seed: int = 1) -> KangarooResult:
    """Find x in [a, b] with x*G == Q, using tame+wild kangaroos.

    Works in offset space: solve x' = x - a in [0, W], where Q' = Q - a*G.
    """
    W = b - a
    if W <= 0:
        return KangarooResult(False, notes=["empty interval"])
    wbits = W.bit_length()
    res = KangarooResult(False, interval_bits=wbits)

    # Jump table: distances 2^0..2^(m-1), mean ~ sqrt(W)/2 -> m ~ wbits/2.
    m = max(2, wbits // 2 + 2)
    dists = [1 << i for i in range(m)]
    jumpP = [bs.point_mul(d) for d in dists]     # precomputed d_i * G

    if dp_bits is None:                          # ~ enough DPs to collide
        dp_bits = max(1, wbits // 2 - 5)
    dp_mask = (1 << dp_bits) - 1
    if max_ops is None:
        max_ops = 16 * int((1 << (wbits // 2)) + 1)   # generous ceiling

    # Q' = Q - a*G  (shift interval to [0, W])
    aG = bs.point_mul(a % bs.N)
    Qs = bs.point_add(Q, (aG[0], (-aG[1]) % bs.P)) if a else Q

    # Two herds: tame starts mid-interval at a known scalar; wild starts at Q'.
    tame_pt = bs.point_mul(W // 2)
    tame_sc = W // 2
    wild_pt = Qs
    wild_sc = 0

    # DP tables: point -> scalar, per herd.
    tame_dp: Dict[Point, int] = {}
    wild_dp: Dict[Point, int] = {}

    ops = 0
    while ops < max_ops:
        # advance tame
        i = _jump_index(tame_pt, m)
        tame_pt = bs.point_add(tame_pt, jumpP[i])
        tame_sc += dists[i]
        ops += 1
        if tame_pt is not None and (tame_pt[0] & dp_mask) == 0:
            res.distinguished_points += 1
            tame_dp[tame_pt] = tame_sc
            if tame_pt in wild_dp:
                xoff = tame_sc - wild_dp[tame_pt]
                x = (a + xoff) % bs.N
                if bs.point_mul(x) == Q:
                    res.solved = True; res.private_key = x; res.operations = ops
                    return res

        # advance wild
        j = _jump_index(wild_pt, m)
        wild_pt = bs.point_add(wild_pt, jumpP[j])
        wild_sc += dists[j]
        ops += 1
        if wild_pt is not None and (wild_pt[0] & dp_mask) == 0:
            res.distinguished_points += 1
            wild_dp[wild_pt] = wild_sc
            if wild_pt in tame_dp:
                xoff = tame_dp[wild_pt] - wild_sc
                x = (a + xoff) % bs.N
                if bs.point_mul(x) == Q:
                    res.solved = True; res.private_key = x; res.operations = ops
                    return res

    res.operations = ops
    res.notes.append("no collision within max_ops=%d (raise it or dp_bits)" % max_ops)
    return res


def estimate_cost(puzzle_bits: int, constant: float = 2.0):
    """Honest expected cost for a Bitcoin-puzzle-style interval.

    Puzzle #n has its key in [2^(n-1), 2^n), so the interval width is 2^(n-1) and
    Kangaroo expected work is ~constant * sqrt(width). Returns expected ops and
    wall-clock at several real-world rates. No optimization changes the exponent;
    the constant (~2.0 plain, ~1.6 with best multi-herd + negation) is the only
    lever software gives you.
    """
    import math
    width_bits = puzzle_bits - 1
    ops = constant * (2 ** (width_bits / 2))
    rates = {
        "pure-Python engine (~4e4 ops/s)": 4e4,
        "one high-end GPU (~1e9 ops/s)": 1e9,
        "256-GPU farm (~2.5e11 ops/s)": 2.5e11,
        "10,000-GPU farm (~1e13 ops/s)": 1e13,
    }
    year = 3.156e7
    out = {"puzzle": puzzle_bits, "expected_ops": ops,
           "expected_ops_log2": math.log2(ops), "times": {}}
    for name, r in rates.items():
        secs = ops / r
        out["times"][name] = ("%.1f days" % (secs / 86400) if secs < year
                              else "%.2e years" % (secs / year))
    return out


def demo(bits: int = 32, seed: int = 12345) -> KangarooResult:
    """Plant a random key in [2^(bits-1), 2^bits) and recover it - a real solve."""
    import random
    rng = random.Random(seed)
    a = 1 << (bits - 1)
    b = 1 << bits
    x = rng.randrange(a, b)
    Q = bs.point_mul(x)
    res = solve_interval(Q, a, b)
    res.notes.append("planted x=%d  recovered=%s  match=%s"
                     % (x, res.private_key, res.private_key == x))
    return res
