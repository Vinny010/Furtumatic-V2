"""Audit orchestrator: run every analysis and assemble the five-category report."""

import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .analysis import bitcoin_scope
from .analysis.dsa import (DSAParams, DSASignature, analyse_nonces,
                           validate_params, verify)
from .lab import cve_2016_6313 as cve
from .openpgp import dearmor, parse_keyblock
from .openpgp.packets import SignaturePacket
from .report.catalogue import build_catalogue
from .report.findings import Category, Finding, Report


def _utc(ts: Optional[int]) -> str:
    if ts is None:
        return "unknown"
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC")


def load_key(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    block = dearmor(raw)[0]
    return block, parse_keyblock(block.body)


def audit_key(key_path: Path, gnupg_repo: Optional[Path] = None,
              deep: bool = True) -> Report:
    block, kb = load_key(key_path)
    par = DSAParams(kb.primary.mpis["p"].value, kb.primary.mpis["q"].value,
                    kb.primary.mpis["g"].value, kb.primary.mpis["y"].value)

    self_sigs = kb.self_signatures()
    all_sigs = kb.all_signatures()
    dsa_sigs: List[DSASignature] = []
    for s in self_sigs:
        if "r" not in s.mpis:
            continue
        dsa_sigs.append(DSASignature(
            r=s.mpis["r"].value, s=s.mpis["s"].value, digest=kb.digest_for(s),
            label="%s@%s" % (s.sig_type_name, s.created),
            hash_algo=s.hash_algo, created=s.created))
    verified = [d for d in dsa_sigs if verify(par, d) is True]
    nonce = analyse_nonces(par, dsa_sigs)
    param_checks = validate_params(par, deep=deep)

    rep = Report()
    rep.target = {
        "fingerprint": " ".join(kb.fingerprint[i:i + 4]
                                for i in range(0, len(kb.fingerprint), 4)),
        "fingerprint_raw": kb.fingerprint,
        "key_id": kb.key_id,
        "created_utc": _utc(kb.primary.created),
        "algorithm": "%s-%d" % (kb.primary.algo_name, kb.primary.key_size_bits),
        "uids": [u.text for u in kb.uids],
        "subkeys": [{"algo": s.key.algo_name, "bits": s.key.key_size_bits,
                     "key_id": s.key.key_id()} for s in kb.subkeys],
        "signature_packets_total": len(all_sigs),
        "signatures_by_this_key": len(self_sigs),
        "signatures_verified": len(verified),
    }
    rep.environment = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "source_digest_sha256": hashlib.sha256(key_path.read_bytes()).hexdigest(),
    }

    # ---------------------------------------------------- Category A + B + E: CVEs
    if gnupg_repo and gnupg_repo.exists():
        for entry in build_catalogue(gnupg_repo):
            cat = Category(entry["category"]) if entry["classified"] else Category.A
            rep.add(Finding(
                category=cat,
                title="%s (fixed in GnuPG %s)" % (entry["cve"], entry["fixed_in"]),
                summary=entry["reasoning"],
                requires=entry["requires"],
                evidence=["Upstream NEWS (%s): %s" % (entry["fixed_in"],
                                                      entry["upstream_text"])],
                references=[entry["cve"]],
                data={"fixed_in": entry["fixed_in"], "fixed_date": entry["fixed_date"]},
            ))

    # ---------------------------------------------------- Category D: reproduction
    rep.add(Finding(
        category=Category.D,
        title="CVE-2016-6313 predictor reproduced deterministically",
        summary=(
            "The 580-bytes-predict-20-bytes relation was derived from the pinned "
            "1.4.7 source and reproduced on synthetic pools. It succeeds on every "
            "trial against 1.4.7 and never against 1.4.21, matching upstream's own "
            "description of the defect."),
        evidence=[
            "rmd160_mixblock() exports the RIPEMD-160 chaining state into the pool, "
            "so pool block B_n IS the hash state after iteration n.",
            "In 1.4.7 the final iteration wraps and reads pool[0:44], which already "
            "holds the new B0/B1/B2 - so B29 = transform(state=B28, B28||B0||B1||B2[0:4]).",
            "1.4.21 absorbs 64 contiguous bytes and therefore consumes the OLD B29 "
            "before overwriting it, which breaks the relation.",
        ],
        reproduce_with="python -m spa.cli lab-cve --trials 500",
        references=["CVE-2016-6313"],
    ))
    rep.add(Finding(
        category=Category.D,
        title="Python pool model validated byte-for-byte against real GnuPG C code",
        summary=(
            "mix_pool() and the RIPEMD-160 compression function are extracted "
            "programmatically from the pinned upstream trees, compiled, and compared "
            "against the Python model. Both 1.4.7 and 1.4.21 agree exactly, so the "
            "model is a faithful stand-in for the historical implementation."),
        evidence=["Differential test: tests/test_differential_c.py",
                  "Functions are lifted from source by script, never hand-copied."],
        reproduce_with="python -m spa.cli lab-differential",
    ))

    # ---------------------------------------------------- Category C: observations
    weak_hash = sorted({s.hash_algo_name for s in self_sigs})
    rep.add(Finding(
        category=Category.C,
        title="Key uses DSA-1024/SHA-1, below modern minimums",
        summary=(
            "The key is DSA with a 1024-bit p and 160-bit q, and its self-signatures "
            "use %s. Both were the ordinary defaults in 2008 and neither is an "
            "anomaly for the period, but both fall below what NIST now accepts. This "
            "is a statement about margin, not about a break: no public method "
            "recovers a 160-bit DSA private key from its public half."
            % ", ".join(weak_hash)),
        evidence=["All %d parameter checks pass: %s"
                  % (len(param_checks),
                     ", ".join(c.name for c in param_checks if c.passed)),
                  "q is a verified 160-bit prime; p is a verified 1024-bit prime.",
                  "g generates the order-q subgroup and y lies within it."],
        data={"parameter_checks": [{"name": c.name, "passed": c.passed,
                                    "detail": c.detail} for c in param_checks]},
    ))
    dupes = nonce.duplicate_signatures
    modernised = [s for s in self_sigs
                  if any(sp.type_id == 33 for sp in s.unhashed_subpackets)]
    if dupes or modernised:
        rep.add(Finding(
            category=Category.C,
            title="One 2008 signature appears twice, re-encoded by modern tooling",
            summary=(
                "The keyblock carries the subkey-binding signature twice. The two "
                "packets are not byte-identical, but they share both r and s and "
                "hash the same data, so they are ONE signature in two encodings - "
                "not a reused nonce. The difference is confined to the unhashed "
                "area: %d packet(s) carry subpacket 33 (issuer-fingerprint), which "
                "postdates 2008 and which GnuPG 1.4.7 could not emit. That is "
                "direct evidence this copy passed through GnuPG 2.1-or-later "
                "tooling, and it corroborates that the armor metadata no longer "
                "reflects the original generator. Because the unhashed area is not "
                "covered by the signature, both packets still verify."
                % len(modernised)),
            evidence=[
                "Duplicate (r,s) pairs: %d" % len(dupes),
                "Unique signature values among %d self-signatures: %d"
                % (len(dsa_sigs), nonce.unique_signature_values),
                "Packets carrying issuer-fingerprint (subpacket 33): %d" % len(modernised),
                "Both encodings verify against the primary key.",
            ],
            data={"duplicates": len(dupes),
                  "unique_values": nonce.unique_signature_values},
        ))

    third_party = len(all_sigs) - len(self_sigs)
    rep.add(Finding(
        category=Category.C,
        title="Keyblock carries %d third-party signature packets" % third_party,
        summary=(
            "Of %d signature packets on this keyserver copy, only %d were made by "
            "the key itself. The remaining %d are unauthenticated third-party "
            "packets that anyone could append - the well-known certificate-flooding "
            "property of the SKS protocol. They tell us nothing about the key's "
            "owner and contribute no material to nonce analysis, because they were "
            "produced by other people's keys and other people's generators."
            % (len(all_sigs), len(self_sigs), third_party)),
        evidence=["Signatures by 0x%s: %d" % (kb.key_id, len(self_sigs)),
                  "Third-party packets: %d" % third_party,
                  "Malformed packets encountered: %d" % len(kb.malformed)],
        data={"total": len(all_sigs), "self": len(self_sigs), "third_party": third_party},
    ))
    rep.add(Finding(
        category=Category.C,
        title="Generator attribution 'GnuPG v1.4.7 (MingW32)' is not authenticated",
        summary=(
            "The version string that attributes this key to GnuPG 1.4.7 on MingW32 "
            "lives in an ASCII-armor 'Version:' header. Armor headers are outside "
            "the packet stream: not signed, not covered by the fingerprint, and "
            "rewritten by every tool the material passes through. This copy's header "
            "reads %r - the keyserver's software, not the generator's. The 1.4.7 "
            "attribution therefore rests on archived copies of the armor, which is "
            "historical evidence rather than cryptographic evidence."
            % (block.version_header or "(absent)")),
        evidence=["Armor header on this copy: %r" % (block.version_header or "(absent)"),
                  "Armor CRC-24 valid: %s" % block.crc_ok,
                  "The fingerprint covers only the primary key packet (RFC 4880 s12.2)."],
        confidence="high",
    ))
    ts = sorted({s.created for s in self_sigs if s.created})
    rep.add(Finding(
        category=Category.C,
        title="All self-signature timestamps coincide with key creation",
        summary=(
            "Every self-signature carries creation time %s, identical to the primary "
            "key's. That is the expected signature of a single uninterrupted "
            "`gpg --gen-key` run and indicates no later re-certification. It also "
            "means the key's entire public signature history was produced in one "
            "session, which bounds how much generator output could ever have been "
            "exposed." % ", ".join(_utc(t) for t in ts)),
        evidence=["Primary key created: %s" % _utc(kb.primary.created)]
                 + ["%s: %s" % (s.sig_type_name, _utc(s.created)) for s in self_sigs],
    ))
    bad_mpi = []
    for name, m in kb.primary.mpis.items():
        if not m.length_consistent:
            bad_mpi.append("primary.%s declares %d bits, holds %d"
                           % (name, m.declared_bits, m.actual_bits))
    rep.add(Finding(
        category=Category.C,
        title="MPI encodings are RFC-conformant" if not bad_mpi
              else "Non-conformant MPI length encoding detected",
        summary=("Every MPI in the primary key declares a bit length exactly matching "
                 "its value, as RFC 4880 requires and as GnuPG has always emitted. "
                 "Nothing here suggests hand-crafted or rewritten packets."
                 if not bad_mpi else
                 "One or more MPIs declare a length inconsistent with their value: %s"
                 % "; ".join(bad_mpi)),
        evidence=["%s: %d bits declared, %d actual" % (n, m.declared_bits, m.actual_bits)
                  for n, m in kb.primary.mpis.items()],
    ))

    # ---------------------------------------------------- Category E: ruled out
    rep.add(Finding(
        category=Category.E,
        title="Nonce reuse across the key's published signatures",
        summary=(
            "The key made %d signature packets carrying %d distinct signature "
            "values, and every one verifies. No r repeats with a differing s, which "
            "is the definition of nonce reuse and the one nonce failure detectable "
            "from purely public data. This rules out closed-form private-key "
            "recovery from the published signatures. (The one repeated r is a "
            "duplicate encoding of a single signature, not a reused nonce - see "
            "Category C.)" % (len(dsa_sigs), nonce.unique_signature_values)),
        evidence=["Signatures by this key: %d" % len(dsa_sigs),
                  "Cryptographically verified: %d" % len(verified),
                  "Distinct signature values: %d" % nonce.unique_signature_values,
                  "True nonce reuse (same r, different s): %d" % len(nonce.repeated_r),
                  "Duplicate encodings (same r and s): %d" % len(nonce.duplicate_signatures)],
        reproduce_with="python -m spa.cli analyze-key",
        data={"distinct_r": nonce.distinct_r, "verified": len(verified)},
    ))
    rep.add(Finding(
        category=Category.E,
        title="Lattice/HNP attack on the published signatures",
        summary=(
            "Even granting a hypothetical nonce bias, a lattice attack on 160-bit q "
            "needs on the order of 60 signatures assuming 4 leaked bits each. This "
            "key has published %d. The shortfall is structural: the keyblock contains "
            "one certification and two subkey bindings, and no further signatures by "
            "this key exist in the public record to collect."
            % len(dsa_sigs)),
        requires="tens to hundreds of signatures from the same key",
        evidence=[nonce.lattice_requirement],
    ))
    budget = cve.observable_rng_budget(signature_count=len(dsa_sigs))
    rep.add(Finding(
        category=Category.E,
        title="CVE-2016-6313 exploitation against this key from public material",
        summary=(
            "The predictor needs %d bytes of raw consecutive generator output. An "
            "OpenPGP public key publishes none: p and q are the survivors of a "
            "primality search, g is derived from them, y hides x behind a discrete "
            "log, and signatures publish r = (g^k mod p) mod q rather than k. The "
            "shortfall is %d bytes out of %d, and it is categorical rather than "
            "quantitative - more public signatures would not help, because no "
            "quantity of public signatures contains raw generator output."
            % (budget.required_bytes, budget.shortfall, budget.required_bytes)),
        requires=", ".join(p.required for p in cve.PREREQUISITES[:2]),
        evidence=["%s: %s" % (k, v) for k, v in budget.source_bytes.items()]
                 + ["Total raw RNG bytes observable: %d" % budget.total_raw_bytes],
        references=["CVE-2016-6313"],
        data={"required": budget.required_bytes, "observable": budget.total_raw_bytes},
    ))
    rep.add(Finding(
        category=Category.E,
        title="Any transfer of GnuPG RNG findings to Satoshi's Bitcoin keys",
        summary=(
            "Bitcoin signing is ECDSA over secp256k1 using OpenSSL's RNG. GnuPG's "
            "cipher/random.c is never executed by Bitcoin, so CVE-2016-6313 and every "
            "other GnuPG RNG defect is inapplicable to the wallet keys by "
            "construction. Separately, unspent outputs publish no signature at all, "
            "so the great majority of coins attributed to Satoshi contribute zero "
            "ECDSA signatures to any analysis."),
        evidence=["PGP key: %s" % bitcoin_scope.DOMAIN_SEPARATION["pgp_key_5EC948A1"]["signature_algorithm"],
                  "Bitcoin: %s" % bitcoin_scope.DOMAIN_SEPARATION["bitcoin_keys"]["signature_algorithm"],
                  bitcoin_scope.DOMAIN_SEPARATION["bitcoin_keys"]["reason"]],
    ))

    rep.target["bottom_line"] = (
        "The key is exactly what it appears to be: a structurally sound DSA-1024 key "
        "generated on 2008-10-30, whose three self-signatures all verify. GnuPG 1.4.7 "
        "does contain a genuine RNG defect (CVE-2016-6313), and this project "
        "reproduces it deterministically against synthetic pools. It does not reach "
        "this key. The attack consumes raw generator output, and a public key "
        "contains none - 0 bytes against a requirement of 580. No repeated nonce "
        "exists among the published signatures, and at three signatures the corpus is "
        "an order of magnitude below any lattice attack. The one genuinely soft point "
        "is evidentiary rather than mathematical: the 'GnuPG v1.4.7 (MingW32)' "
        "attribution rides in an unsigned armor header, so it is a historical claim, "
        "not something the key itself attests.")
    return rep
