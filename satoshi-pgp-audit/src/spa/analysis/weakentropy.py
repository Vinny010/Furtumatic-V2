"""Reproduce the keyspace-collapse failure class - on synthetic keys only.

WHAT THIS MODELS
----------------
Every real-world theft of Bitcoin that did NOT break the elliptic curve broke the
RANDOM NUMBER GENERATOR instead, collapsing the private-key space to something
searchable:

    Debian OpenSSL (CVE-2008-0166)  entropy -> process id      ~2^15
    Android SecureRandom (2013)     repeated ECDSA nonces        n/a (reuse)
    Brainwallets                    key = SHA256(passphrase)    small dictionary
    Coldcard firmware (2021-2026)   seed <- device serial       ~2^40

They share one shape: the effective key is drawn from a small, enumerable set
because the generator's real entropy is far below its nominal strength. This module
reproduces that shape generically and abstractly.

DELIBERATELY GENERIC, DELIBERATELY SYNTHETIC
--------------------------------------------
The entropy source here is an opaque low-bit integer, NOT a reconstruction of any
vendor's specific seed-derivation path. That is a safety choice, not a shortcut:

  * It captures every collapse listed above with one abstraction, so the science is
    complete.
  * It cannot be pointed at real deployed devices. Reproducing a live product's
    exact KDF while that product is being actively drained would be building a
    targeting tool, not studying a defect.

Every key produced here is generated inside this process for this experiment and
controls nothing. No real wallet, seed, or address is touched, derived, or scanned.

WHY IT EARNS ITS PLACE
----------------------
It is the POSITIVE CONTROL the on-chain analysis was missing. A related-key scan
that only ever returns "nothing found" could be broken. Here we generate keys with
a KNOWN collapse, show the same detectors used on the Patoshi corpus light up, and
then note that the Patoshi corpus does NOT - which is what makes that negative
result trustworthy rather than vacuous.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import bitcoin_scope as bs


@dataclass
class CollapseResult:
    entropy_bits: int
    keys_generated: int
    brute_force_attempted: bool
    brute_force_recovered: int
    brute_force_budget: int
    nominal_bits: int = 256
    notes: List[str] = field(default_factory=list)

    @property
    def collapse_factor_log2(self) -> int:
        return self.nominal_bits - self.entropy_bits


def _priv_from_weak_source(source_value: int, salt: bytes = b"spa-synthetic") -> int:
    """Map a low-entropy integer to a private key, as a collapsed generator would.

    The hashing here mirrors how a real weak generator still runs its limited
    entropy through a KDF - the output looks like a 256-bit key, but only spans as
    many distinct values as the input did. That is the whole trap: the key LOOKS
    full-strength and passes casual inspection.
    """
    digest = hashlib.sha256(salt + source_value.to_bytes(8, "big")).digest()
    return (int.from_bytes(digest, "big") % (bs.N - 1)) + 1


def generate_collapsed_keys(entropy_bits: int, count: int,
                            seed_offset: int = 0) -> List[Tuple[int, Tuple[int, int]]]:
    """Generate ``count`` keys whose private keys are drawn from a 2^entropy_bits set.

    Returns (private_key, public_point) pairs. Private keys are returned ONLY because
    this is a controlled synthetic experiment demonstrating recoverability; nothing
    here corresponds to a real key.
    """
    space = 1 << entropy_bits
    out: List[Tuple[int, Tuple[int, int]]] = []
    for i in range(count):
        source = (seed_offset + i) % space
        d = _priv_from_weak_source(source)
        out.append((d, bs.point_mul(d)))
    return out


def demonstrate_recovery(entropy_bits: int = 20, key_count: int = 5,
                         budget: Optional[int] = None) -> CollapseResult:
    """Show that a collapsed keyspace is brute-forceable from public keys alone.

    Builds a table of the whole (small) entropy space, then recovers the private
    keys of synthetic targets by lookup. Kept to modest ``entropy_bits`` so it runs
    in seconds - the point is the MECHANISM, and it scales exactly as 2^bits.

    The real Coldcard collapse was ~40 bits: a trillion candidates, hours on a GPU.
    We demonstrate at ~20 bits (a million) so it finishes instantly, and report how
    the cost scales.
    """
    space = 1 << entropy_bits
    if budget is None:
        budget = space
    targets = generate_collapsed_keys(entropy_bits, key_count, seed_offset=space // 3)
    target_pubs = {pt: d for d, pt in targets}

    recovered = 0
    scanned = 0
    for source in range(min(space, budget)):
        scanned += 1
        d = _priv_from_weak_source(source)
        pt = bs.point_mul(d)
        if pt in target_pubs:
            assert d == target_pubs[pt]      # recovered key matches by construction
            recovered += 1
            if recovered == len(targets):
                break

    res = CollapseResult(
        entropy_bits=entropy_bits, keys_generated=key_count,
        brute_force_attempted=True, brute_force_recovered=recovered,
        brute_force_budget=budget)
    res.notes.append(
        "Recovered %d/%d synthetic private keys by enumerating a %d-bit space "
        "(%d candidates scanned). The elliptic curve was never attacked - only the "
        "generator's real entropy." % (recovered, key_count, entropy_bits, scanned))
    res.notes.append(
        "Cost scales as 2^bits: this %d-bit demo is ~%d candidates; the real "
        "Coldcard collapse to ~40 bits is ~1.1e12, hours on commodity hardware; a "
        "healthy 256-bit key is ~1.2e77, physically impossible."
        % (entropy_bits, space))
    return res


@dataclass
class DetectorControl:
    entropy_bits: int
    keys: int
    duplicate_keys: int
    related_pairs: int
    max_delta: int
    detector_fired: bool
    notes: List[str] = field(default_factory=list)


def positive_control_for_related_scan(keys: int = 50, spacing: int = 3,
                                      max_delta: int = 64) -> DetectorControl:
    """Prove the related-key scanner fires on the collapse shape it targets.

    IMPORTANT DISTINCTION. There are two keyspace-collapse shapes, and the
    related-key scan only covers one of them:

      * SEQUENTIAL / OFFSET collapse - a counter, an incrementing seed, a
        stuck-then-nudged RNG. Private keys land CLOSE together, so P_j = P_i +
        delta*G with small delta. THIS is what the related-key scan detects, and
        this control reproduces it: keys d, d+spacing, d+2*spacing, ...

      * HASHED low-entropy collapse - key = KDF(small_input), as in brainwallets and
        the Coldcard serial-derived seed. The KDF SCATTERS the keys across the whole
        range, so no small-delta relation survives. The related-key scan is BLIND to
        this; the detector for it is enumeration of the specific derivation
        (demonstrate_recovery), which requires knowing or guessing the KDF and its
        input space.

    So the Patoshi negative from the related-key scan rules out the SEQUENTIAL class
    only. Ruling out the hashed class is not possible from public keys without a
    candidate derivation to test - stated plainly in the notes rather than papered
    over.
    """
    import secrets

    from .relatedkeys import KeyRecord, scan

    d0 = secrets.randbelow(bs.N - keys * spacing - 1) + 1
    records = [KeyRecord(label="seq-%d" % i, point=bs.point_mul(d0 + i * spacing))
               for i in range(keys)]
    f = scan(records, max_delta=max_delta)
    fired = bool(f.duplicate_keys or f.related_pairs)
    ctrl = DetectorControl(
        entropy_bits=0, keys=keys,
        duplicate_keys=len(f.duplicate_keys), related_pairs=len(f.related_pairs),
        max_delta=max_delta, detector_fired=fired)
    if fired:
        ctrl.notes.append(
            "Detector fired on sequential keys (%d related pairs at spacing %d). "
            "The same scan returned ZERO on the 21,953 Patoshi keys, so that "
            "negative is a real measurement of the SEQUENTIAL/OFFSET class - not a "
            "broken scan." % (len(f.related_pairs), spacing))
    else:
        ctrl.notes.append(
            "Detector did NOT fire on a known sequential keyspace. It is broken, "
            "and any negative it produced must be discarded.")
    ctrl.notes.append(
        "SCOPE LIMIT: this rules out the sequential/offset collapse only. A hashed "
        "low-entropy collapse (brainwallet / Coldcard-serial shape) scatters keys "
        "and would NOT show here; detecting that needs enumeration of the specific "
        "derivation, which is infeasible blind and out of scope for real keys.")
    return ctrl
