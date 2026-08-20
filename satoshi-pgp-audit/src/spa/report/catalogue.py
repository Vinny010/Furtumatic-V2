"""Vulnerability catalogue for GnuPG 1.4.7, derived from upstream's own NEWS file.

The list of defects present in 1.4.7 is not asserted from memory. It is computed:
every CVE mentioned in a NEWS entry for a release LATER than 1.4.7 is, by
construction, a defect that 1.4.7 still contained. That makes the catalogue
reproducible from the pinned source tree and immune to recall error.

The applicability analysis (does this defect touch a DSA key studied from its public
half in 2026?) is necessarily editorial, so it is kept in a separate table with
explicit reasoning, and anything not covered is emitted as UNCLASSIFIED rather than
guessed at.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}")
VERSION_RE = re.compile(r"^Noteworthy changes in version ([0-9.]+)\s*\(([0-9-]+)\)")


def _version_tuple(v: str):
    return tuple(int(x) for x in v.split("."))


@dataclass
class CatalogueEntry:
    cve: str
    fixed_in: str
    fixed_date: str
    upstream_text: str
    present_in_1_4_7: bool = True


def parse_news(news_text: str, baseline: str = "1.4.7") -> List[CatalogueEntry]:
    """Extract CVEs from NEWS entries for releases newer than ``baseline``."""
    entries: List[CatalogueEntry] = []
    cur_ver: Optional[str] = None
    cur_date = ""
    buf: List[str] = []

    def flush():
        if cur_ver is None:
            return
        try:
            newer = _version_tuple(cur_ver) > _version_tuple(baseline)
        except ValueError:
            return
        if not newer:
            return
        text = "\n".join(buf)
        for para in re.split(r"\n\s*\n", text):
            for cve in dict.fromkeys(CVE_RE.findall(para)):
                entries.append(CatalogueEntry(
                    cve=cve, fixed_in=cur_ver, fixed_date=cur_date,
                    upstream_text=" ".join(para.split())))

    for line in news_text.splitlines():
        m = VERSION_RE.match(line)
        if m:
            flush()
            cur_ver, cur_date, buf = m.group(1), m.group(2), []
        else:
            buf.append(line)
    flush()
    # De-duplicate, keeping the earliest fix.
    seen: Dict[str, CatalogueEntry] = {}
    for e in entries:
        if e.cve not in seen or _version_tuple(e.fixed_in) < _version_tuple(seen[e.cve].fixed_in):
            seen[e.cve] = e
    return sorted(seen.values(), key=lambda e: _version_tuple(e.fixed_in))


def news_from_git(repo: Path, tag: str = "gnupg-1.4.23") -> str:
    proc = subprocess.run(["git", "-C", str(repo), "show", "%s:NEWS" % tag],
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError("git show failed: %s" % proc.stderr.decode()[:300])
    return proc.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------- applicability
@dataclass
class Applicability:
    affects_dsa_keygen: bool
    affects_this_key: bool
    requires: str
    reasoning: str
    category: str          # one of the five report categories (see findings.py)


# Keyed reasoning. Every judgement states the requirement that decides it.
APPLICABILITY: Dict[str, Applicability] = {
    "CVE-2016-6313": Applicability(
        affects_dsa_keygen=True, affects_this_key=False,
        requires="580 consecutive bytes of raw RNG output from one mixed pool",
        reasoning=(
            "The defect is in the code path that produces every random value GnuPG "
            "generates, so software built from 1.4.7 is unambiguously affected and "
            "this project reproduces the predictor deterministically. Exploitation "
            "against this key is a separate question and fails on prerequisites: an "
            "OpenPGP public key publishes no raw generator output, so the attacker "
            "starts from 0 of the required 580 bytes."),
        category="B"),
    "CVE-2017-7526": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="local flush+reload cache observation during RSA secret-key use",
        reasoning=(
            "Scoped to RSA sliding-window exponentiation. The key under study is DSA "
            "with an Elgamal subkey and performs no RSA secret-key operation, so the "
            "vulnerable code is never reached."),
        category="E"),
    "CVE-2013-4242": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="co-resident process performing flush+reload during RSA operations",
        reasoning="RSA-specific side channel; not reachable for a DSA/Elgamal key.",
        category="E"),
    "CVE-2013-4576": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="acoustic emanations captured near the machine during RSA decryption",
        reasoning=(
            "RSA-specific, and requires physical presence at the machine in 2008. "
            "Neither condition can be met retrospectively from public key material."),
        category="E"),
    "CVE-2014-3591": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="RF side-channel observation during Elgamal decryption on the "
                 "original hardware",
        reasoning=(
            "This one does touch the right algorithm - the key carries a 2048-bit "
            "Elgamal encryption subkey, and 1.4.7 predates ciphertext blinding. But "
            "it is a physical side channel requiring proximity to the machine while "
            "it decrypts. That observation window closed in 2008 and left no public "
            "residue."),
        category="B"),
    "CVE-2015-0837": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="last-level cache observation from a co-located process",
        reasoning=(
            "Data-dependent timing in modular exponentiation. Applies to the "
            "software, but needs a co-resident attacker process at the time of the "
            "secret-key operation. No public artefact records such observations."),
        category="B"),
    "CVE-2014-4617": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="the victim parses an attacker-supplied compressed packet",
        reasoning=(
            "Denial of service in the decompressor. Present in 1.4.7 and therefore a "
            "genuine defect of the historical software, but it cannot disclose key "
            "material or influence key generation."),
        category="A"),
    "CVE-2013-4402": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="the victim parses a crafted nested compressed packet",
        reasoning="Parser resource exhaustion. No confidentiality impact on keys.",
        category="A"),
    "CVE-2018-12020": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="the victim displays verbose output for an attacker-supplied file",
        reasoning=(
            "'SigSpoof' - unsanitised filename in diagnostic output can fake a "
            "verification result in a terminal. Affects how signatures are PRESENTED, "
            "never how they are generated. Worth noting for anyone assessing archived "
            "screenshots of signature verification as evidence."),
        category="A"),
    "CVE-2008-1530": Applicability(
        affects_dsa_keygen=False, affects_this_key=False,
        requires="the victim imports a crafted key",
        reasoning="Import-path defect; no impact on the generation of this key.",
        category="A"),
}


def build_catalogue(repo: Path, tag: str = "gnupg-1.4.23",
                    baseline: str = "1.4.7") -> List[Dict]:
    """Full catalogue: upstream facts joined to applicability judgements."""
    out: List[Dict] = []
    for e in parse_news(news_from_git(repo, tag), baseline):
        app = APPLICABILITY.get(e.cve)
        out.append({
            "cve": e.cve,
            "fixed_in": e.fixed_in,
            "fixed_date": e.fixed_date,
            "present_in_1_4_7": True,
            "upstream_text": e.upstream_text,
            "classified": app is not None,
            "category": app.category if app else "UNCLASSIFIED",
            "requires": app.requires if app else "",
            "reasoning": app.reasoning if app else
                         "Not yet classified by this project. Present in 1.4.7 per "
                         "upstream NEWS; applicability to this key needs review.",
            "affects_dsa_keygen": app.affects_dsa_keygen if app else None,
        })
    return out
