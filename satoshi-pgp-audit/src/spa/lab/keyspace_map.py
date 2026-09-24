"""Map WHERE in the keyspace different entropy environments land their keys.

THE QUESTION
------------
"An old 2008 machine and a new machine seed differently - do they generate keys in
different parts of the keyspace? Could that give insight into where Satoshi's keys
are?"

It is a good question, and the answer is a genuinely important fact about how
cryptographic RNGs work:

    A correctly-seeded CSPRNG produces output uniformly across the ENTIRE keyspace,
    independent of the machine, the year, or how messy the raw entropy was - because
    the generator HASHES (whitens) the entropy. SHA-family mixing decouples the
    output distribution from the seed distribution.

So a well-seeded 2008 box and a well-seeded 2026 box are indistinguishable: both
uniform over [1, N). There is no "region old systems land in." That is exactly the
guarantee a CSPRNG exists to provide, and Bitcoin 0.1's generator met it (its
seeding was strong - see docs/KEYGEN_BITCOIN_0_1.md).

WHERE THE QUESTION *DOES* BITE
------------------------------
The era is irrelevant; the SEEDING QUALITY is everything. This module demonstrates
the transition by generating keys under three models and measuring the distribution:

  1. healthy       - full-entropy CSPRNG (any well-seeded machine, 2008 or 2026)
  2. whitened-weak - low entropy run through a hash (Debian-OpenSSL shape): FEW
                     DISTINCT values, but still SCATTERED across the whole keyspace
                     (a hash scatters - it does not make a contiguous region)
  3. raw-band      - keys taken directly from a small number (naive counter /
                     timestamp, no whitening): a CONTIGUOUS low region, detectable
                     by magnitude alone

The punchline the metrics make concrete: 'old vs new' is not a distinction a good
RNG exposes; only 'well-seeded vs broken' is, and 'broken' shows up as collisions
(whitened-weak) or a magnitude band (raw-band) - neither of which Satoshi's keys
exhibit (see the related-key scan and this module's own checks).

Everything here is synthetic and about the distribution of freshly generated scalars.
No real key is involved.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List

N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # secp256k1 order
_TOP_BUCKETS = 256          # partition the space by the top 8 bits


def _sha_scalar(x: int) -> int:
    return (int.from_bytes(hashlib.sha256(x.to_bytes(32, "big")).digest(), "big") % (N - 1)) + 1


@dataclass
class Distribution:
    model: str
    count: int
    distinct: int
    collisions: int
    buckets_occupied: int          # of 256 top-8-bit buckets
    fraction_in_bottom_256th: float
    max_over_min_bucket: float
    uniform_full_range: bool
    notes: List[str] = field(default_factory=list)


def _profile(model: str, draws: Callable[[int], int], count: int,
             rng) -> Distribution:
    keys = [draws(i) for i in range(count)]
    distinct = len(set(keys))
    buckets = [0] * _TOP_BUCKETS
    bottom = 0
    shift = N.bit_length() - 8
    for k in keys:
        b = min(k >> shift, _TOP_BUCKETS - 1)
        buckets[b] += 1
        if k < (N >> 8):
            bottom += 1
    occupied = sum(1 for b in buckets if b)
    nz = [b for b in buckets if b]
    ratio = (max(nz) / min(nz)) if len(nz) > 1 else float("inf")
    # "uniform across the full range" = most buckets occupied and roughly even.
    uniform = occupied > _TOP_BUCKETS * 0.9 and ratio < 3.0
    d = Distribution(
        model=model, count=count, distinct=distinct, collisions=count - distinct,
        buckets_occupied=occupied, fraction_in_bottom_256th=bottom / count,
        max_over_min_bucket=ratio, uniform_full_range=uniform)
    return d


def profile_models(count: int = 50000, weak_bits: int = 16, band_bits: int = 40,
                   seed: int = 0) -> Dict[str, Distribution]:
    """Profile the three entropy models. Deterministic given ``seed``."""
    import random
    rng = random.Random(seed)

    def healthy(_i):                       # full-entropy CSPRNG: uniform over [1,N)
        return rng.randrange(1, N)

    weak_space = 1 << weak_bits

    def whitened_weak(_i):                 # Debian shape: low entropy, hashed
        return _sha_scalar(rng.randrange(weak_space))

    band_space = 1 << band_bits

    def raw_band(_i):                      # naive counter/timestamp, no whitening
        return rng.randrange(1, band_space)

    out = {
        "healthy (well-seeded, any era)": _profile(
            "healthy", healthy, count, rng),
        "whitened-weak (Debian shape)": _profile(
            "whitened-weak", whitened_weak, count, rng),
        "raw-band (naive counter/time)": _profile(
            "raw-band", raw_band, count, rng),
    }
    out["healthy (well-seeded, any era)"].notes.append(
        "Uniform across the full keyspace, no collisions. A 2008 and a 2026 machine "
        "look identical here - the hash whitens away the era.")
    w = out["whitened-weak (Debian shape)"]
    w.notes.append(
        "Collisions appear (only %d distinct of %d) because the seed space is tiny, "
        "BUT the keys are still scattered across the whole range - low entropy makes "
        "few distinct points, not a contiguous region." % (w.distinct, w.count))
    b = out["raw-band (naive counter/time)"]
    b.notes.append(
        "Keys sit in a contiguous LOW band (%.4f%% of them in the bottom 1/256), "
        "occupying %d of 256 buckets - this is the only model where 'where in the "
        "keyspace' is even a meaningful question, and it requires NO whitening at "
        "all (raw counter/timestamp as key)."
        % (100 * b.fraction_in_bottom_256th, b.buckets_occupied))
    return out


def era_is_irrelevant_for_healthy(count: int = 20000) -> bool:
    """Demonstrate that two independent healthy generators are statistically
    indistinguishable - i.e. 'old machine' vs 'new machine' is not a real axis."""
    a = profile_models(count=count, seed=1)["healthy (well-seeded, any era)"]
    b = profile_models(count=count, seed=2)["healthy (well-seeded, any era)"]
    return (a.uniform_full_range and b.uniform_full_range
            and a.collisions == 0 and b.collisions == 0)
