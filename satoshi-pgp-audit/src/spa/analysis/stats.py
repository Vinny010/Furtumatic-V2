"""Randomness test battery (NIST SP 800-22 subset), dependency-free.

Implemented without scipy so the container stays small and the results stay
bit-reproducible across machines. The incomplete gamma function is the Numerical
Recipes series/continued-fraction pair.

A warning that the report layer enforces: these tests have essentially no power on
the amount of data recoverable from a public key. Three DSA signatures carry ~120
bytes of signature material. Every test here needs kilobytes before a low p-value
means anything. They exist to characterise SYNTHETIC generator output, where we can
produce megabytes on demand.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

_MAXIT = 300
_EPS = 3.0e-12
_FPMIN = 1.0e-300


def _gser(a: float, x: float) -> float:
    ap, s, d = a, 1.0 / a, 1.0 / a
    for _ in range(_MAXIT):
        ap += 1.0
        d *= x / ap
        s += d
        if abs(d) < abs(s) * _EPS:
            break
    return s * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gcf(a: float, x: float) -> float:
    b, c, d = x + 1.0 - a, 1.0 / _FPMIN, 1.0 / (x + 1.0 - a)
    h = d
    for i in range(1, _MAXIT + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = b + an / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def igamc(a: float, x: float) -> float:
    """Regularised upper incomplete gamma Q(a,x). Chi-square p-value = igamc(df/2, X/2)."""
    if x < 0 or a <= 0:
        return 0.0
    if x == 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gser(a, x)
    return _gcf(a, x)


@dataclass
class TestResult:
    name: str
    p_value: Optional[float]
    statistic: Optional[float]
    passed: Optional[bool]
    detail: str = ""

    def __str__(self) -> str:
        if self.p_value is None:
            return "[SKIP] %-24s %s" % (self.name, self.detail)
        return "[%s] %-24s p=%.6f  %s" % (
            "PASS" if self.passed else "FAIL", self.name, self.p_value, self.detail)


def _bits(data: bytes) -> List[int]:
    out: List[int] = []
    for byte in data:
        for i in range(7, -1, -1):
            out.append((byte >> i) & 1)
    return out


ALPHA = 0.01  # NIST default significance level


def monobit(data: bytes) -> TestResult:
    b = _bits(data)
    n = len(b)
    if n < 100:
        return TestResult("monobit", None, None, None, "need >= 100 bits, have %d" % n)
    s = sum(1 if x else -1 for x in b)
    sobs = abs(s) / math.sqrt(n)
    p = math.erfc(sobs / math.sqrt(2))
    return TestResult("monobit", p, sobs, p >= ALPHA,
                      "ones=%d zeros=%d" % (sum(b), n - sum(b)))


def block_frequency(data: bytes, block_size: int = 128) -> TestResult:
    b = _bits(data)
    n = len(b)
    nblocks = n // block_size
    if nblocks < 1:
        return TestResult("block-frequency", None, None, None,
                          "need >= %d bits" % block_size)
    total = 0.0
    for i in range(nblocks):
        pi = sum(b[i * block_size:(i + 1) * block_size]) / block_size
        total += (pi - 0.5) ** 2
    chi = 4.0 * block_size * total
    p = igamc(nblocks / 2.0, chi / 2.0)
    return TestResult("block-frequency", p, chi, p >= ALPHA,
                      "%d blocks of %d bits" % (nblocks, block_size))


def runs(data: bytes) -> TestResult:
    b = _bits(data)
    n = len(b)
    if n < 100:
        return TestResult("runs", None, None, None, "need >= 100 bits")
    pi = sum(b) / n
    if abs(pi - 0.5) >= 2.0 / math.sqrt(n):
        return TestResult("runs", 0.0, None, False,
                          "monobit precondition failed (pi=%.4f)" % pi)
    v = 1 + sum(1 for i in range(n - 1) if b[i] != b[i + 1])
    num = abs(v - 2.0 * n * pi * (1 - pi))
    den = 2.0 * math.sqrt(2.0 * n) * pi * (1 - pi)
    p = math.erfc(num / den)
    return TestResult("runs", p, float(v), p >= ALPHA, "%d runs" % v)


def longest_run_of_ones(data: bytes) -> TestResult:
    b = _bits(data)
    n = len(b)
    if n < 128:
        return TestResult("longest-run", None, None, None, "need >= 128 bits")
    if n < 6272:
        m, k, nblk = 8, 3, 16
        v_lo, probs = 1, [0.2148, 0.3672, 0.2305, 0.1875]
    elif n < 750000:
        m, k, nblk = 128, 5, 49
        v_lo, probs = 4, [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]
    else:
        m, k, nblk = 10000, 6, 75
        v_lo, probs = 10, [0.0882, 0.2092, 0.2483, 0.1933, 0.1208, 0.0675, 0.0727]
    counts = [0] * (k + 1)
    for i in range(nblk):
        blk = b[i * m:(i + 1) * m]
        best = cur = 0
        for bit in blk:
            cur = cur + 1 if bit else 0
            best = max(best, cur)
        idx = min(max(best - v_lo, 0), k)
        counts[idx] += 1
    chi = sum((counts[i] - nblk * probs[i]) ** 2 / (nblk * probs[i])
              for i in range(k + 1))
    p = igamc(k / 2.0, chi / 2.0)
    return TestResult("longest-run", p, chi, p >= ALPHA, "M=%d N=%d" % (m, nblk))


def cumulative_sums(data: bytes, forward: bool = True) -> TestResult:
    b = _bits(data)
    n = len(b)
    if n < 100:
        return TestResult("cusum", None, None, None, "need >= 100 bits")
    x = [1 if v else -1 for v in b]
    if not forward:
        x = x[::-1]
    running = 0
    z = 0
    for v in x:
        running += v
        z = max(z, abs(running))
    if z == 0:
        return TestResult("cusum", 1.0, 0.0, True, "degenerate")
    total = 0.0
    lo = int((-n / z + 1) // 4)
    hi = int((n / z - 1) // 4)
    for k in range(lo, hi + 1):
        total += (_phi((4 * k + 1) * z / math.sqrt(n))
                  - _phi((4 * k - 1) * z / math.sqrt(n)))
    lo2 = int((-n / z - 3) // 4)
    total2 = 0.0
    for k in range(lo2, hi + 1):
        total2 += (_phi((4 * k + 3) * z / math.sqrt(n))
                   - _phi((4 * k + 1) * z / math.sqrt(n)))
    p = 1.0 - total + total2
    p = min(max(p, 0.0), 1.0)
    return TestResult("cusum-%s" % ("fwd" if forward else "rev"), p, float(z),
                      p >= ALPHA, "max excursion %d" % z)


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def approximate_entropy(data: bytes, m: int = 2) -> TestResult:
    b = _bits(data)
    n = len(b)
    if n < 100:
        return TestResult("approx-entropy", None, None, None, "need >= 100 bits")
    phis = []
    for mm in (m, m + 1):
        if mm == 0:
            phis.append(0.0)
            continue
        counts: Dict[int, int] = {}
        ext = b + b[:mm - 1]
        for i in range(n):
            key = 0
            for j in range(mm):
                key = (key << 1) | ext[i + j]
            counts[key] = counts.get(key, 0) + 1
        phis.append(sum((c / n) * math.log(c / n) for c in counts.values()))
    apen = phis[0] - phis[1]
    chi = 2.0 * n * (math.log(2) - apen)
    p = igamc(2 ** (m - 1), chi / 2.0)
    return TestResult("approx-entropy", p, chi, p >= ALPHA, "m=%d" % m)


def byte_chi_square(data: bytes) -> TestResult:
    """Uniformity of byte values - catches gross structural bias fast."""
    n = len(data)
    if n < 2560:
        return TestResult("byte-chi2", None, None, None,
                          "need >= 2560 bytes for 10/bin, have %d" % n)
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    exp = n / 256.0
    chi = sum((c - exp) ** 2 / exp for c in counts)
    p = igamc(255 / 2.0, chi / 2.0)
    return TestResult("byte-chi2", p, chi, p >= ALPHA, "%d bytes" % n)


def full_battery(data: bytes) -> List[TestResult]:
    return [monobit(data), block_frequency(data), runs(data),
            longest_run_of_ones(data), cumulative_sums(data, True),
            cumulative_sums(data, False), approximate_entropy(data),
            byte_chi_square(data)]


def battery_summary(results: Sequence[TestResult]) -> Dict[str, int]:
    return {
        "run": sum(1 for r in results if r.p_value is not None),
        "passed": sum(1 for r in results if r.passed is True),
        "failed": sum(1 for r in results if r.passed is False),
        "skipped": sum(1 for r in results if r.passed is None),
    }
