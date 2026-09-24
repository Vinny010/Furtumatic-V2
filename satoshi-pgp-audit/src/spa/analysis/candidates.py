"""Derive Bitcoin address candidates from values ALREADY PUBLIC in the PGP key.

WHY A MOTIVATED SET, NOT A SEARCH
---------------------------------
Scanning arbitrary private keys is pointless arithmetic: with 2^256 candidates, any
list of a few hundred has a hit probability near 10^-74. The only version of this
idea with non-negligible odds uses a MOTIVATED candidate set - values a human might
plausibly have reused or derived a key from, drawn from a tiny identifiable subset
rather than uniformly from the space.

That failure mode is real and documented:

  * Brainwallets (private key = SHA-256 of a passphrase) were swept systematically
    and drained.
  * Keys from Debian's OpenSSL defect (CVE-2008-0166) were enumerated outright,
    because seeding had collapsed to the process id - 32,768 possibilities.
  * The 2013 Android SecureRandom failure produced repeated ECDSA nonces on mainnet
    and cost people real coins.

In every case the keyspace collapsed to something searchable for a specific,
identifiable reason. So the narrow question worth testing here is: did anyone derive
a Bitcoin key from a value published in THIS PGP key - the fingerprint, a signature
component, q, or an obvious hash of the identity string? That is a few dozen
candidates and costs milliseconds.

EXPECTED RESULT: no hits. This is documented as a lottery ticket. Its value is that
it is cheap and falsifiable, so the question is closed by measurement instead of
being left open on speculation. A negative result here is the useful outcome: it
removes the last "but what if they reused something obvious" objection.

SCOPE
-----
This module DERIVES and REPORTS addresses. It queries no blockchain and constructs
no transaction. A private key that controls funds belongs to whoever generated it;
finding one confers no entitlement to spend it. Weak-key research is published
because DISCLOSURE, not spending, is the legitimate outcome.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import bitcoin_scope as bs


@dataclass
class Candidate:
    label: str
    rationale: str
    private_key: int
    addresses: Dict[str, str] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return 0 < self.private_key < bs.N


def _mk(label: str, rationale: str, value: int) -> Optional[Candidate]:
    """Build one candidate, deriving both address encodings in use in 2009-2011."""
    value %= bs.N
    if value == 0:
        return None
    c = Candidate(label=label, rationale=rationale, private_key=value)
    pub = bs.point_mul(value)
    if pub is None:
        return None
    # Uncompressed was the only form Bitcoin used in 2009; compressed arrived later.
    # Both are derived because a candidate could have been imported at any time.
    c.addresses["uncompressed"] = bs.pubkey_to_address(pub, False)
    c.addresses["compressed"] = bs.pubkey_to_address(pub, True)
    return c


def _sha(data: bytes) -> int:
    return int.from_bytes(hashlib.sha256(data).digest(), "big")


def derive_candidates(keyblock, signatures=None) -> List[Candidate]:
    """Enumerate motivated candidates from a parsed OpenPGP keyblock.

    Every candidate carries a stated rationale. A derivation without one is just a
    random number and does not belong in this list - that discipline is what keeps
    the set motivated rather than a disguised blind search.
    """
    out: List[Optional[Candidate]] = []
    fpr_hex = keyblock.fingerprint
    fpr_bytes = bytes.fromhex(fpr_hex)
    m = keyblock.primary.mpis

    # --- the fingerprint: the most identity-like public value on the key ---
    out.append(_mk("fingerprint:zero-extended",
                   "20-byte fingerprint zero-extended to a 32-byte key",
                   int.from_bytes(fpr_bytes, "big")))
    out.append(_mk("fingerprint:high-bytes",
                   "fingerprint placed in the high bytes, low bytes zero-filled",
                   int.from_bytes(fpr_bytes + b"\x00" * 12, "big")))
    out.append(_mk("fingerprint:sha256-raw",
                   "SHA-256 of the raw fingerprint bytes", _sha(fpr_bytes)))
    out.append(_mk("fingerprint:sha256-hex-upper",
                   "SHA-256 of the uppercase hex fingerprint string",
                   _sha(fpr_hex.encode())))
    out.append(_mk("fingerprint:sha256-hex-lower",
                   "SHA-256 of the lowercase hex fingerprint string",
                   _sha(fpr_hex.lower().encode())))
    spaced = " ".join(fpr_hex[i:i + 4] for i in range(0, 40, 4))
    out.append(_mk("fingerprint:sha256-spaced",
                   "SHA-256 of the fingerprint as it is normally displayed",
                   _sha(spaced.encode())))

    # --- DSA domain parameters and the public value ---
    out.append(_mk("dsa:q", "the 160-bit prime q used directly as a key",
                   m["q"].value))
    out.append(_mk("dsa:sha256-q", "SHA-256 of q's big-endian bytes",
                   _sha(m["q"].value.to_bytes(20, "big"))))
    out.append(_mk("dsa:y-reduced", "public value y reduced mod the secp256k1 order",
                   m["y"].value))
    out.append(_mk("dsa:sha256-y", "SHA-256 of y's big-endian bytes",
                   _sha(m["y"].value.to_bytes(128, "big"))))

    # --- identity strings: the classic brainwallet construction ---
    for uid in keyblock.uids:
        out.append(_mk("brainwallet:uid",
                       "SHA-256 of the full User ID string %r - the classic "
                       "brainwallet construction" % uid.text,
                       _sha(uid.text.encode())))
        if "<" in uid.text and ">" in uid.text:
            name = uid.text.split("<")[0].strip()
            email = uid.text.split("<")[1].rstrip(">").strip()
            out.append(_mk("brainwallet:name",
                           "SHA-256 of the name portion alone (%r)" % name,
                           _sha(name.encode())))
            out.append(_mk("brainwallet:email",
                           "SHA-256 of the email portion alone (%r)" % email,
                           _sha(email.encode())))

    # --- key id and creation timestamp ---
    out.append(_mk("keyid:sha256", "SHA-256 of the 8-byte key id",
                   _sha(bytes.fromhex(keyblock.key_id))))
    out.append(_mk("created:integer", "the creation timestamp used as an integer",
                   keyblock.primary.created))
    out.append(_mk("created:sha256",
                   "SHA-256 of the creation timestamp in decimal ASCII",
                   _sha(str(keyblock.primary.created).encode())))

    # --- signature components: the only per-signature randomness ever published ---
    for i, sig in enumerate(signatures or []):
        if "r" not in sig.mpis:
            continue
        r, s = sig.mpis["r"].value, sig.mpis["s"].value
        out.append(_mk("sig%d:r" % i,
                       "signature r used directly. r is derived from the DSA nonce, "
                       "so this tests whether a nonce-derived value was ever reused "
                       "as a Bitcoin key", r))
        out.append(_mk("sig%d:s" % i, "signature s used directly", s))
        out.append(_mk("sig%d:sha256-rs" % i, "SHA-256 of r concatenated with s",
                       _sha(r.to_bytes(20, "big") + s.to_bytes(20, "big"))))

    # --- the public-key packet as a whole ---
    out.append(_mk("keypacket:sha256",
                   "SHA-256 of the v4 public-key packet body",
                   _sha(keyblock.primary._v4_key_body())))

    seen = set()
    result: List[Candidate] = []
    for c in out:
        if c is None or not c.valid or c.private_key in seen:
            continue
        seen.add(c.private_key)
        result.append(c)
    return result
