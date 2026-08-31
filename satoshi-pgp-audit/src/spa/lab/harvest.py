"""Drive a real GnuPG binary to produce synthetic keys and signatures.

Every key produced here is created for the experiment and belongs to nobody. That
is a hard scope rule of the project: exploit validation runs exclusively against
synthetic material, never against Satoshi's key or any other real key.

The harness is version-agnostic - point it at the historical 1.4.7 build or at a
modern gpg, and compare. That comparison is the point: a defect claim is only
credible if the same measurement applied to a known-good implementation behaves
differently.
"""

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BATCH_TEMPLATE = """Key-Type: {key_type}
Key-Length: {key_length}
{subkey_block}Name-Real: {name}
Name-Email: {email}
Expire-Date: 0
%commit
"""


@dataclass
class GeneratedKey:
    index: int
    armored_public: bytes
    key_id: str
    fingerprint: str
    generation_seconds: float


@dataclass
class HarvestResult:
    gpg_path: str
    gpg_version: str
    keys: List[GeneratedKey] = field(default_factory=list)
    signatures: List[bytes] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class GPGRunner:
    """A disposable GNUPGHOME wrapped around one gpg binary."""

    def __init__(self, gpg_path: str, home: Optional[Path] = None) -> None:
        self.gpg_path = str(gpg_path)
        self._tmp = home is None
        self.home = Path(home) if home else Path(tempfile.mkdtemp(prefix="spa-gpg-"))
        self.home.mkdir(parents=True, exist_ok=True)
        os.chmod(self.home, 0o700)

    def close(self) -> None:
        if self._tmp and self.home.exists():
            shutil.rmtree(self.home, ignore_errors=True)

    def __enter__(self) -> "GPGRunner":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def run(self, args: List[str], stdin: bytes = b"",
            timeout: int = 300) -> subprocess.CompletedProcess:
        cmd = [self.gpg_path, "--homedir", str(self.home), "--batch", "--yes"] + args
        return subprocess.run(cmd, input=stdin, capture_output=True, timeout=timeout)

    def version(self) -> str:
        out = subprocess.run([self.gpg_path, "--version"], capture_output=True)
        first = out.stdout.decode("utf-8", "replace").splitlines()
        return first[0].strip() if first else "unknown"

    def is_v1(self) -> bool:
        return "(GnuPG) 1." in self.version()


def generate_keys(gpg_path: str, count: int = 10, key_type: str = "DSA",
                  key_length: int = 1024, subkey: Optional[Tuple[str, int]] = ("ELG-E", 2048),
                  timeout: int = 300) -> HarvestResult:
    """Generate ``count`` synthetic keys with the given gpg binary.

    Defaults mirror the historical profile under study: DSA-1024 primary with a
    2048-bit Elgamal encryption subkey, which is what key 0x5EC948A1 is.
    """
    import time
    runner = GPGRunner(gpg_path)
    res = HarvestResult(gpg_path=str(gpg_path), gpg_version=runner.version())
    sub_block = ""
    if subkey:
        sub_block = "Subkey-Type: %s\nSubkey-Length: %d\n" % subkey
    try:
        for i in range(count):
            batch = BATCH_TEMPLATE.format(
                key_type=key_type, key_length=key_length, subkey_block=sub_block,
                name="SYNTHETIC LAB KEY %04d" % i,
                email="synthetic-%04d@lab.invalid" % i)
            bf = runner.home / ("batch-%04d.txt" % i)
            bf.write_text(batch)
            t0 = time.time()
            proc = runner.run(["--gen-key", str(bf)], timeout=timeout)
            dt = time.time() - t0
            if proc.returncode != 0:
                res.errors.append("key %d: %s" % (i, proc.stderr.decode("utf-8", "replace")[-300:]))
                continue
            listing = runner.run(["--list-keys", "--with-colons", "--fingerprint"])
            fprs = re.findall(r"^fpr:::::::::([0-9A-F]+):",
                              listing.stdout.decode("utf-8", "replace"), re.M)
            if not fprs:
                res.errors.append("key %d: no fingerprint in listing" % i)
                continue
            fpr = fprs[-2] if len(fprs) >= 2 else fprs[-1]
            exported = runner.run(["--armor", "--export", fpr])
            res.keys.append(GeneratedKey(index=i, armored_public=exported.stdout,
                                         key_id=fpr[-16:], fingerprint=fpr,
                                         generation_seconds=dt))
    finally:
        runner.close()
    return res


def generate_signature_corpus(gpg_path: str, count: int = 200,
                              key_length: int = 1024,
                              timeout: int = 300) -> Tuple[bytes, List[bytes]]:
    """Create ONE synthetic DSA key, then sign ``count`` distinct messages with it.

    This is the corpus that makes nonce analysis meaningful. Satoshi's public key
    carries three signatures; here we can produce hundreds from a key whose private
    half we own, which is the only ethical and legal way to test nonce attacks.

    Returns (armored_public_key, [detached_signature_bytes, ...]).
    """
    runner = GPGRunner(gpg_path)
    try:
        batch = BATCH_TEMPLATE.format(
            key_type="DSA", key_length=key_length, subkey_block="",
            name="SYNTHETIC SIGNING KEY", email="synthetic-signer@lab.invalid")
        bf = runner.home / "batch.txt"
        bf.write_text(batch)
        proc = runner.run(["--gen-key", str(bf)], timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError("key generation failed: %s"
                               % proc.stderr.decode("utf-8", "replace")[-500:])
        listing = runner.run(["--list-keys", "--with-colons", "--fingerprint"])
        fprs = re.findall(r"^fpr:::::::::([0-9A-F]+):",
                          listing.stdout.decode("utf-8", "replace"), re.M)
        fpr = fprs[0]
        pub = runner.run(["--armor", "--export", fpr]).stdout
        sigs: List[bytes] = []
        for i in range(count):
            msg = ("synthetic lab message %06d - unique content %s"
                   % (i, os.urandom(8).hex())).encode()
            out = runner.run(["--detach-sign", "--digest-algo", "SHA1",
                              "--local-user", fpr, "--output", "-"], stdin=msg)
            if out.returncode == 0 and out.stdout:
                sigs.append(out.stdout)
        return pub, sigs
    finally:
        runner.close()


def extract_dsa_signature_values(sig_packets: List[bytes]) -> List[Dict]:
    """Pull (r, s) out of detached signature packets using the project's parser."""
    from ..openpgp.packets import SignaturePacket, parse_packets
    out: List[Dict] = []
    for i, raw in enumerate(sig_packets):
        for p in parse_packets(raw):
            if isinstance(p, SignaturePacket) and "r" in p.mpis:
                out.append({"index": i, "r": p.mpis["r"].value,
                            "s": p.mpis["s"].value,
                            "r_bits": p.mpis["r"].declared_bits,
                            "s_bits": p.mpis["s"].declared_bits,
                            "label": "synthetic-%04d" % i})
    return out


def find_gpg(candidates: Optional[List[str]] = None) -> Dict[str, str]:
    """Locate available gpg binaries: the historical build and a modern reference."""
    found: Dict[str, str] = {}
    env_hist = os.environ.get("SPA_GPG147")
    if env_hist and Path(env_hist).exists():
        found["historical"] = env_hist
    for name in (candidates or ["gpg", "gpg2", "gpg1"]):
        path = shutil.which(name)
        if path:
            ver = subprocess.run([path, "--version"], capture_output=True)
            first = ver.stdout.decode("utf-8", "replace").splitlines()[0]
            if "(GnuPG) 1.4.7" in first and "historical" not in found:
                found["historical"] = path
            elif "modern" not in found and "(GnuPG) 2." in first:
                found["modern"] = path
    return found
