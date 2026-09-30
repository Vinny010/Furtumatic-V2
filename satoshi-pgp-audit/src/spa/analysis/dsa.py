"""DSA parameter validation, signature verification, and nonce-relation analysis.

The nonce relation that matters for every practical DSA break is

    k = s^-1 * (h + x*r)  mod q

An attacker who learns k for one signature recovers the private key immediately:

    x = r^-1 * (s*k - h)  mod q

So every DSA attack reduces to learning something about k. The three routes are:
  1. k repeated across two signatures  -> r repeats -> x recoverable in closed form.
  2. k partially known / biased        -> lattice (hidden number problem), needs MANY
                                          signatures (tens for a few bits of bias).
  3. k fully predictable from RNG state-> requires the generator's internal state.

This module measures which of those routes the available public material could even
in principle support, rather than assuming any of them.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .numbertheory import invmod, is_probable_prime


@dataclass
class DSAParams:
    p: int
    q: int
    g: int
    y: int

    @property
    def p_bits(self) -> int:
        return self.p.bit_length()

    @property
    def q_bits(self) -> int:
        return self.q.bit_length()


@dataclass
class ParamCheck:
    name: str
    passed: Optional[bool]
    detail: str

    def __str__(self) -> str:
        mark = {True: "PASS", False: "FAIL", None: "SKIP"}[self.passed]
        return "[%s] %-28s %s" % (mark, self.name, self.detail)


def validate_params(par: DSAParams, deep: bool = True) -> List[ParamCheck]:
    """Structural validation of a DSA public key.

    A maliciously or incompetently generated DSA key betrays itself here: a composite
    q, a g that does not generate the order-q subgroup, or a y outside that subgroup
    would all be immediately disqualifying. FIPS 186 requires every one of these.
    """
    checks: List[ParamCheck] = []
    checks.append(ParamCheck("p size", par.p_bits in (512, 768, 1024, 2048, 3072),
                             "p is %d bits" % par.p_bits))
    checks.append(ParamCheck("q size", par.q_bits in (160, 224, 256),
                             "q is %d bits" % par.q_bits))
    checks.append(ParamCheck("q divides p-1", (par.p - 1) % par.q == 0,
                             "q | (p-1)" if (par.p - 1) % par.q == 0
                             else "q does NOT divide p-1 - key is structurally invalid"))
    checks.append(ParamCheck("g range", 1 < par.g < par.p,
                             "1 < g < p" if 1 < par.g < par.p else "g out of range"))
    checks.append(ParamCheck("y range", 1 < par.y < par.p,
                             "1 < y < p" if 1 < par.y < par.p else "y out of range"))
    g_order_ok = pow(par.g, par.q, par.p) == 1
    checks.append(ParamCheck("g has order q", g_order_ok,
                             "g^q = 1 mod p" if g_order_ok
                             else "g^q != 1 - g does not generate the order-q subgroup"))
    y_sub_ok = pow(par.y, par.q, par.p) == 1
    checks.append(ParamCheck("y in subgroup", y_sub_ok,
                             "y^q = 1 mod p" if y_sub_ok
                             else "y^q != 1 - public key is outside the order-q subgroup"))
    checks.append(ParamCheck("g != 1", par.g != 1, "g is not the identity"))
    if deep:
        q_prime = is_probable_prime(par.q)
        checks.append(ParamCheck("q is prime", q_prime,
                                 "Miller-Rabin, 64 rounds" if q_prime
                                 else "q is COMPOSITE - catastrophic"))
        p_prime = is_probable_prime(par.p)
        checks.append(ParamCheck("p is prime", p_prime,
                                 "Miller-Rabin, 64 rounds" if p_prime
                                 else "p is COMPOSITE - catastrophic"))
    else:
        checks.append(ParamCheck("q is prime", None, "deep checks disabled"))
        checks.append(ParamCheck("p is prime", None, "deep checks disabled"))
    return checks


def digest_to_int(digest: bytes, q: int) -> int:
    """FIPS 186 / RFC 4880 truncation: use the leftmost min(qlen, hashlen) bits."""
    qlen = q.bit_length()
    h = int.from_bytes(digest, "big")
    excess = len(digest) * 8 - qlen
    if excess > 0:
        h >>= excess
    return h


@dataclass
class DSASignature:
    r: int
    s: int
    digest: Optional[bytes] = None
    label: str = ""
    hash_algo: int = 2
    created: Optional[int] = None

    def h(self, q: int) -> Optional[int]:
        if self.digest is None:
            return None
        return digest_to_int(self.digest, q)


def verify(par: DSAParams, sig: DSASignature) -> Optional[bool]:
    """Standard DSA verification. Returns None when the digest is unavailable."""
    if sig.digest is None:
        return None
    if not (0 < sig.r < par.q and 0 < sig.s < par.q):
        return False
    h = sig.h(par.q)
    try:
        w = invmod(sig.s, par.q)
    except ValueError:
        return False
    u1 = (h * w) % par.q
    u2 = (sig.r * w) % par.q
    v = ((pow(par.g, u1, par.p) * pow(par.y, u2, par.p)) % par.p) % par.q
    return v == sig.r


def recover_x_from_shared_nonce(par: DSAParams, a: DSASignature,
                                b: DSASignature) -> Optional[int]:
    """Closed-form private key recovery when two signatures reused k.

    Detected by r_a == r_b (r = (g^k mod p) mod q depends only on k).
        k = (h_a - h_b) / (s_a - s_b)  mod q
        x = (s_a*k - h_a) / r          mod q
    """
    if a.r != b.r or a.digest is None or b.digest is None:
        return None
    q = par.q
    ha, hb = a.h(q), b.h(q)
    ds = (a.s - b.s) % q
    if ds == 0:
        return None
    k = ((ha - hb) * invmod(ds, q)) % q
    try:
        x = ((a.s * k - ha) * invmod(a.r, q)) % q
    except ValueError:
        return None
    return x if pow(par.g, x, par.p) == par.y else None


@dataclass
class NonceFindings:
    signature_count: int
    verified_count: int
    distinct_r: int
    #: (label_a, label_b, r) where r repeats with DIFFERENT s - genuine nonce reuse.
    repeated_r: List[Tuple[str, str, int]] = field(default_factory=list)
    #: (label_a, label_b, r) where BOTH r and s match - the same signature value
    #: appearing twice, which is a packet-level duplicate, not a nonce failure.
    duplicate_signatures: List[Tuple[str, str, int]] = field(default_factory=list)
    unique_signature_values: int = 0
    recovered_private_key: Optional[int] = None
    msb_zero_counts: Dict[int, int] = field(default_factory=dict)
    lattice_feasible: bool = False
    lattice_requirement: str = ""
    notes: List[str] = field(default_factory=list)


# Empirical thresholds from the HNP/lattice literature (Howgrave-Graham & Smart;
# Nguyen & Shparlinski). These are the number of signatures needed for a lattice
# attack on 160-bit q given a known number of leaked nonce bits.
LATTICE_SIGS_NEEDED = {1: 1000, 2: 200, 3: 100, 4: 60, 5: 40, 8: 25, 16: 12}


def analyse_nonces(par: DSAParams, sigs: List[DSASignature]) -> NonceFindings:
    """Assess every practical nonce-based attack route against the given corpus."""
    f = NonceFindings(signature_count=len(sigs), verified_count=0, distinct_r=0)
    by_r: Dict[int, List[DSASignature]] = {}
    for s in sigs:
        if verify(par, s):
            f.verified_count += 1
        by_r.setdefault(s.r, []).append(s)
    f.distinct_r = len(by_r)

    # A repeated r means one of two very different things, and conflating them
    # produces a false "nonce reuse" alarm on any keyserver copy that carries the
    # same signature twice (which is common - see docs/METHODOLOGY.md):
    #
    #   same r, same s      -> the SAME signature value, re-encoded. Harmless.
    #   same r, different s -> the same nonce used for two different messages.
    #                          Private key recoverable in closed form.
    for r, group in by_r.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.s == b.s:
                    f.duplicate_signatures.append((a.label, b.label, r))
                    continue
                f.repeated_r.append((a.label, b.label, r))
                if f.recovered_private_key is None:
                    x = recover_x_from_shared_nonce(par, a, b)
                    if x is not None:
                        f.recovered_private_key = x
    f.unique_signature_values = len({(s.r, s.s) for s in sigs})

    # Nonce-bias probe: r is (g^k mod p) mod q, so r is NOT k and its distribution is
    # uniform in [1,q) even for biased k. The only bias visible without x is in the
    # *statistical* distribution of r over many signatures. Recorded for completeness
    # and for use on synthetic corpora where k is known.
    qbits = par.q.bit_length()
    for lead in (1, 2, 3, 4, 8):
        f.msb_zero_counts[lead] = sum(1 for s in sigs
                                      if s.r.bit_length() <= qbits - lead)

    needed = LATTICE_SIGS_NEEDED[4]
    f.lattice_feasible = len(sigs) >= needed
    f.lattice_requirement = (
        "A lattice/HNP attack against %d-bit q needs on the order of %d signatures "
        "even assuming 4 leaked nonce bits per signature; %d are available."
        % (qbits, needed, len(sigs)))
    if len(sigs) < 3:
        f.notes.append(
            "Corpus too small for any statistical statement about nonce quality.")
    if f.duplicate_signatures:
        f.notes.append(
            "%d signature pair(s) share both r and s. These are the same signature "
            "value carried in more than one packet encoding, NOT nonce reuse; the "
            "signed digest is identical, so no new information is exposed."
            % len(f.duplicate_signatures))
    if not f.repeated_r:
        f.notes.append(
            "No repeated nonce across the corpus: r never repeats with a differing "
            "s, so closed-form key recovery is ruled out for exactly these "
            "signatures (it says nothing about signatures not in the corpus).")
    return f
