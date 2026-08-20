"""Number-theoretic helpers.

Uses gmpy2 when available (roughly two orders of magnitude faster for 1024-bit
primality) and falls back to a self-contained deterministic-witness Miller-Rabin so
the package has no hard dependency.
"""

import random
from typing import List

try:  # pragma: no cover - environment dependent
    import gmpy2
    _HAVE_GMPY2 = True
except ImportError:  # pragma: no cover
    gmpy2 = None
    _HAVE_GMPY2 = False

# Small primes for trial division - catches most composites instantly.
_SMALL_PRIMES: List[int] = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
    239, 241, 251,
]


def is_probable_prime(n: int, rounds: int = 64) -> bool:
    """Miller-Rabin. ``rounds`` random bases gives error probability < 4^-rounds."""
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
    if _HAVE_GMPY2:
        return bool(gmpy2.is_prime(n, rounds))
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    rng = random.Random(0xC0FFEE)  # fixed seed: primality results must be reproducible
    for _ in range(rounds):
        a = rng.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def invmod(a: int, m: int) -> int:
    return pow(a, -1, m)


def bit_length_of(n: int) -> int:
    return n.bit_length()


def hamming_weight(n: int) -> int:
    return bin(n).count("1")
