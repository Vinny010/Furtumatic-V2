"""Detect RELATED private keys from public keys alone.

THE IDEA
--------
If a key generator ever produced private keys that are related by a small additive
offset - sequential keys, an incrementing counter, a stuck-then-nudged RNG, a
partially-reset seed - that relation survives untouched into the public keys:

    d_j = d_i + delta   =>   P_j = P_i + delta*G

So the relation is detectable with NO private data whatsoever. Given a corpus of
public keys, scan small delta and look for collisions. If a hit is found, the
private keys of BOTH keys collapse the moment either one is known, and more
importantly the generator is proven defective.

This is the strongest offline test available on a pay-to-public-key corpus, and it
is the reason early P2PK outputs are analytically valuable: they publish the FULL
public key on-chain rather than a hash of it, so the arithmetic above is possible.
Modern P2PKH addresses expose only HASH160(pubkey), which destroys this structure
and makes the test impossible until the coins move.

WHY IT IS WORTH RUNNING
-----------------------
Related-key generation is a real, repeatedly observed failure class - it is what
made the Debian OpenSSL keys (CVE-2008-0166) and the 2013 Android SecureRandom
wallets recoverable. It is also, unlike nonce reuse, rarely tested on historical
corpora, because it needs full public keys and most analysts only have addresses.

EXPECTED RESULT: no hits. A negative result is a genuine finding: it rules out a
whole class of generator defect across the corpus, rather than leaving it assumed.

COST
----
Naive pair comparison is O(n^2) - 480 million operations for a 22k corpus. This
implementation is O(n * delta_max) using Montgomery's batch-inversion trick, which
inverts a whole column with ONE modular inversion instead of n. That turns the scan
from hours into seconds.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import bitcoin_scope as bs

P = bs.P
Point = Tuple[int, int]


@dataclass
class KeyRecord:
    label: str
    point: Point
    height: Optional[int] = None


@dataclass
class RelatedKeyFindings:
    keys_scanned: int = 0
    max_delta: int = 0
    duplicate_keys: List[Tuple[str, str]] = field(default_factory=list)
    related_pairs: List[Tuple[str, str, int]] = field(default_factory=list)
    off_curve: List[str] = field(default_factory=list)
    control_detected: Optional[bool] = None
    elapsed_seconds: float = 0.0
    notes: List[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.related_pairs and not self.duplicate_keys


def batch_invert(values: Sequence[int], modulus: int = P) -> List[int]:
    """Montgomery's trick: invert n field elements with ONE modular inversion.

    Builds running products, inverts the total once, then walks backwards peeling
    off each element. Costs 3n multiplications and 1 inversion instead of n
    inversions - the difference between a scan that finishes and one that does not.
    """
    if not values:
        return []
    prefix = [1] * (len(values) + 1)
    for i, v in enumerate(values):
        prefix[i + 1] = prefix[i] * v % modulus
    inv = pow(prefix[-1], -1, modulus)
    out = [0] * len(values)
    for i in range(len(values) - 1, -1, -1):
        out[i] = prefix[i] * inv % modulus
        inv = inv * values[i] % modulus
    return out


def is_on_curve(point: Point) -> bool:
    x, y = point
    return (y * y - (x * x * x + bs.B)) % P == 0


def parse_uncompressed(hex_str: str) -> Optional[Point]:
    h = (hex_str or "").strip()
    if not h.startswith("04") or len(h) != 130:
        return None
    try:
        return (int(h[2:66], 16), int(h[66:], 16))
    except ValueError:
        return None


def load_p2pk_csv(path: Path, pubkey_field: str = "Address/Pubkey",
                  height_field: str = "Block Height") -> List[KeyRecord]:
    """Load a CSV of P2PK outputs (height, full uncompressed public key)."""
    out: List[KeyRecord] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            pt = parse_uncompressed(row.get(pubkey_field, ""))
            if pt is None:
                continue
            try:
                height = int(row[height_field])
            except (KeyError, ValueError):
                height = None
            out.append(KeyRecord(label="block-%s" % height, point=pt, height=height))
    return out


def scan(records: Iterable[KeyRecord], max_delta: int = 512,
         progress=None, control_labels: Optional[Sequence[str]] = None
         ) -> RelatedKeyFindings:
    """Scan for duplicate and small-offset related keys.

    For each delta in 1..max_delta the whole corpus is advanced by delta*G in one
    batch-inverted column, then tested for membership against the corpus.

    ``control_labels`` names an injected positive-control pair so it is excluded
    from the verdict - otherwise the control's own hit would be reported as a
    finding about the real corpus.
    """
    import time

    records = [r for r in records]
    f = RelatedKeyFindings(keys_scanned=len(records), max_delta=max_delta)
    t0 = time.time()

    valid: List[KeyRecord] = []
    for r in records:
        if is_on_curve(r.point):
            valid.append(r)
        else:
            f.off_curve.append(r.label)

    # Duplicate detection first - a repeated public key means a repeated private key.
    seen: Dict[Point, str] = {}
    for r in valid:
        if r.point in seen:
            f.duplicate_keys.append((seen[r.point], r.label))
        else:
            seen[r.point] = r.label

    index: Dict[int, List[int]] = {}
    for i, r in enumerate(valid):
        index.setdefault(r.point[0], []).append(i)

    for delta in range(1, max_delta + 1):
        q = bs.point_mul(delta)
        if q is None:
            continue
        xq, yq = q
        dens: List[int] = []
        idxs: List[int] = []
        for i, r in enumerate(valid):
            dx = (r.point[0] - xq) % P
            if dx == 0:
                continue          # P_i == +/-Q; not a pairwise relation
            dens.append(dx)
            idxs.append(i)
        invs = batch_invert(dens)
        for k, i in enumerate(idxs):
            x, y = valid[i].point
            lam = (y - yq) * invs[k] % P
            xr = (lam * lam - x - xq) % P
            for j in index.get(xr, ()):
                if j != i:
                    f.related_pairs.append((valid[i].label, valid[j].label, delta))
        if progress and delta % max(1, max_delta // 8) == 0:
            progress(delta, max_delta, len(f.related_pairs), time.time() - t0)

    f.elapsed_seconds = time.time() - t0
    if f.off_curve:
        f.notes.append("%d entries were not valid curve points and were skipped."
                       % len(f.off_curve))

    # Separate the injected control from genuine corpus findings before judging.
    ctrl = set(control_labels or ())
    if ctrl:
        f.control_detected = any(set(pair[:2]) == ctrl for pair in f.related_pairs)
        f.related_pairs = [p for p in f.related_pairs if set(p[:2]) != ctrl]
        f.duplicate_keys = [p for p in f.duplicate_keys if set(p) != ctrl]
        if not f.control_detected:
            f.notes.append(
                "POSITIVE CONTROL NOT DETECTED. The scan failed to find a planted "
                "relation, so its negative result on real data carries no weight.")
            return f

    if f.clean:
        f.notes.append(
            "No duplicate keys and no related keys within delta <= %d. This rules "
            "out sequential, incrementing and small-offset key generation across "
            "the corpus - a whole class of generator defect, excluded by "
            "measurement rather than assumption." % max_delta)
    else:
        f.notes.append(
            "RELATION FOUND. Any such pair means the generator was defective, and "
            "the private keys of both stand or fall together. Verify independently "
            "before drawing conclusions.")
    return f


def with_control(records: List[KeyRecord], delta: int = 7
                 ) -> Tuple[List[KeyRecord], Tuple[str, str]]:
    """Append a synthetic pair whose private keys differ by exactly ``delta``.

    A scan that cannot find a planted relation cannot be trusted to report the
    absence of a real one. The control uses a freshly generated random key and is
    labelled so it can never be mistaken for corpus data.
    """
    import secrets
    d0 = secrets.randbelow(bs.N - 2) + 1
    a = KeyRecord(label="CONTROL-a", point=bs.point_mul(d0))
    b = KeyRecord(label="CONTROL-b", point=bs.point_mul(d0 + delta))
    return records + [a, b], ("CONTROL-a", "CONTROL-b")
