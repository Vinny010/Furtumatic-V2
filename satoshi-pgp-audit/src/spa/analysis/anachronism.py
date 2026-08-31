"""Detect backdated OpenPGP keys via algorithm/creation-date anachronism.

A key's creation timestamp is a self-declared field set at generation time - the
signer types any date they wish. It is trivially forgeable and covered only by the
key's own self-signature, which the forger also controls. So a claimed creation date
is never evidence on its own.

But it is FALSIFIABLE. A key cannot have been created before the algorithm it uses
existed. If a key claims a 2008 creation date yet uses EdDSA - an algorithm whose
OpenPGP codepoint did not exist until 2014 - the date is provably false. This is a
hard, checkable contradiction, not a probabilistic argument.

This module encodes the earliest date each public-key and hash algorithm could
appear in a conforming OpenPGP key, and flags any key whose claimed creation date
predates its own algorithms. It is the direct tool for vetting "I am Satoshi"
key claims, which almost always rest on a recent key wearing an old date.

Dates below are the earliest an OpenPGP implementation could plausibly EMIT the
algorithm (standard finalised and shipping software available), deliberately
generous - a flag here means the key predates even that lenient bound.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# RFC 4880 / 6637 / draft-koch-eddsa public-key algorithm ids -> (name, earliest year).
# "Earliest year" = when a conforming OpenPGP key could first use it.
PUBKEY_ALGO_INTRO = {
    1:  ("RSA (Encrypt or Sign)", 1998),   # RSA in OpenPGP since PGP 5 / RFC 2440
    2:  ("RSA Encrypt-Only", 1998),
    3:  ("RSA Sign-Only", 1998),
    16: ("Elgamal (Encrypt-Only)", 1998),
    17: ("DSA", 1998),
    18: ("ECDH", 2012),                     # RFC 6637
    19: ("ECDSA", 2012),                    # RFC 6637
    20: ("Elgamal (Encrypt or Sign)", 1998),
    22: ("EdDSA (Ed25519)", 2014),          # GnuPG 2.1.0, Nov 2014; RFC 8032 in 2017
}

# Hash algorithm ids -> (name, earliest year usable in OpenPGP).
HASH_ALGO_INTRO = {
    1:  ("MD5", 1998),
    2:  ("SHA-1", 1998),
    3:  ("RIPEMD-160", 1998),
    8:  ("SHA-256", 2004),                  # SHA-2 family standardised 2001-2004
    9:  ("SHA-384", 2004),
    10: ("SHA-512", 2004),
    11: ("SHA-224", 2004),
}

# secp256k1 as an OpenPGP curve is even later than generic ECC, but generic ECDSA
# already covers the year bound, so the algorithm id suffices.


@dataclass
class Anachronism:
    kind: str            # 'pubkey-algo' | 'hash-algo'
    detail: str
    claimed_year: int
    earliest_year: int

    @property
    def years_early(self) -> int:
        return self.earliest_year - self.claimed_year


@dataclass
class KeyClaim:
    """The minimal facts needed to vet a backdating claim."""
    label: str
    claimed_created_year: int
    pubkey_algo: int
    hash_algos: List[int] = field(default_factory=list)
    fingerprint: Optional[str] = None
    uid: Optional[str] = None


@dataclass
class AnachronismFindings:
    label: str
    claimed_created_year: int
    anachronisms: List[Anachronism] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def backdated(self) -> bool:
        return bool(self.anachronisms)


def check_claim(claim: KeyClaim) -> AnachronismFindings:
    f = AnachronismFindings(label=claim.label,
                            claimed_created_year=claim.claimed_created_year)

    name, intro = PUBKEY_ALGO_INTRO.get(claim.pubkey_algo,
                                        ("algo-%d" % claim.pubkey_algo, None))
    if intro is not None and claim.claimed_created_year < intro:
        f.anachronisms.append(Anachronism(
            kind="pubkey-algo",
            detail="key uses %s, which no OpenPGP implementation could emit before "
                   "%d" % (name, intro),
            claimed_year=claim.claimed_created_year, earliest_year=intro))

    for h in claim.hash_algos:
        hname, hintro = HASH_ALGO_INTRO.get(h, ("hash-%d" % h, None))
        if hintro is not None and claim.claimed_created_year < hintro:
            f.anachronisms.append(Anachronism(
                kind="hash-algo",
                detail="a self-signature uses %s, unavailable before %d"
                       % (hname, hintro),
                claimed_year=claim.claimed_created_year, earliest_year=hintro))

    if f.backdated:
        worst = max(f.anachronisms, key=lambda a: a.years_early)
        f.notes.append(
            "BACKDATED: the claimed creation year %d is impossible - %s. The "
            "creation timestamp is a self-declared field and is provably false here."
            % (claim.claimed_created_year, worst.detail))
        f.notes.append(
            "A forgeable date plus a free-text UID is not evidence of authorship. "
            "Only a signature from the genuine historical key would be.")
    else:
        f.notes.append(
            "No algorithm anachronism: the claimed date is at least consistent with "
            "the algorithms used. That is necessary, NOT sufficient - it does not "
            "confirm the date, and it says nothing about identity.")
    return f


# ---- keyring-level checking ---------------------------------------------------
@dataclass
class KeyringVerdict:
    label: str
    claimed_year: int
    algo_known: bool
    verdict: str        # 'BACKDATED' | 'CONSISTENT' | 'UNVERIFIED'
    findings: Optional[AnachronismFindings] = None
    key_id: str = ""
    detail: str = ""


def check_keyring(entries: List[dict]) -> List[KeyringVerdict]:
    """Vet a whole transcribed keyring.

    Entries without an observed algorithm are reported UNVERIFIED - never flagged -
    because backdating cannot be proven from a name and date alone. Only an
    algorithm/date contradiction yields BACKDATED.
    """
    out: List[KeyringVerdict] = []
    for e in entries:
        year = e.get("claimed_created_year")
        algo = e.get("pubkey_algo")
        kid = e.get("key_id") or e.get("key_id_partial") or ""
        if algo is None or year is None:
            out.append(KeyringVerdict(
                label=e.get("label", "?"), claimed_year=year or 0,
                algo_known=False, verdict="UNVERIFIED", key_id=kid,
                detail="algorithm not observed; backdating cannot be proven or "
                       "ruled out from the available data"))
            continue
        claim = KeyClaim(label=e.get("label", "?"), claimed_created_year=year,
                         pubkey_algo=algo, hash_algos=e.get("hash_algos", []),
                         fingerprint=e.get("fingerprint"), uid=e.get("uid"))
        f = check_claim(claim)
        verdict = "BACKDATED" if f.backdated else "CONSISTENT"
        detail = (max(f.anachronisms, key=lambda a: a.years_early).detail
                  if f.backdated else "algorithm consistent with claimed date "
                  "(does not confirm the date or identity)")
        out.append(KeyringVerdict(
            label=claim.label, claimed_year=year, algo_known=True,
            verdict=verdict, findings=f, key_id=kid, detail=detail))
    return out
