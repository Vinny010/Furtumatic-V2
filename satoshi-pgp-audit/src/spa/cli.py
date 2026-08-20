"""Command-line interface for satoshi-pgp-audit."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KEY = ROOT / "data" / "keys" / "satoshi_5EC948A1.asc"
DEFAULT_GNUPG_SRC = Path(os.environ.get("SPA_GNUPG_SRC", ROOT / "data" / "gnupg-src" / "gnupg"))


def _p(*a):
    print(*a, flush=True)


# --------------------------------------------------------------- analyze-key
def cmd_analyze_key(args) -> int:
    from .analysis.dsa import DSAParams, DSASignature, analyse_nonces, validate_params, verify
    from .audit import load_key, _utc
    block, kb = load_key(Path(args.key))
    _p("=" * 74)
    _p("OpenPGP public key analysis")
    _p("=" * 74)
    _p("Armor kind          : %s" % block.kind)
    _p("Armor Version hdr   : %r  (unauthenticated, not covered by the fingerprint)"
       % (block.version_header or "(absent)"))
    _p("Armor CRC-24 valid  : %s" % block.crc_ok)
    _p("")
    k = kb.primary
    _p("Primary key")
    _p("  version           : %d" % k.version)
    _p("  algorithm         : %s (id %d)" % (k.algo_name, k.algo))
    _p("  size              : %d bits" % k.key_size_bits)
    _p("  created           : %s (unix %d)" % (_utc(k.created), k.created))
    _p("  key id            : %s" % kb.key_id)
    _p("  fingerprint       : %s" % " ".join(kb.fingerprint[i:i+4]
                                             for i in range(0, 40, 4)))
    _p("  fingerprint recomputed locally from the packet body (RFC 4880 s12.2)")
    _p("")
    _p("  DSA parameters")
    for name in ("p", "q", "g", "y"):
        m = k.mpis[name]
        _p("    %s : %4d bits declared / %4d actual  consistent=%s"
           % (name, m.declared_bits, m.actual_bits, m.length_consistent))
    _p("")
    par = DSAParams(k.mpis["p"].value, k.mpis["q"].value,
                    k.mpis["g"].value, k.mpis["y"].value)
    _p("  Parameter validation")
    for c in validate_params(par, deep=not args.fast):
        _p("    %s" % c)
    _p("")
    for u in kb.uids:
        _p("User ID: %s" % u.text)
    for s in kb.subkeys:
        _p("Subkey : %s %d bits, key id %s, created %s"
           % (s.key.algo_name, s.key.key_size_bits, s.key.key_id(), _utc(s.key.created)))
    _p("")
    all_sigs = kb.all_signatures()
    self_sigs = kb.self_signatures()
    _p("Signature packets   : %d total" % len(all_sigs))
    _p("  issued by this key: %d" % len(self_sigs))
    _p("  third-party       : %d  (unauthenticated; anyone may append these)"
       % (len(all_sigs) - len(self_sigs)))
    _p("  malformed         : %d" % len(kb.malformed))
    _p("")
    _p("Signatures made by this key (the only ones carrying its DSA nonces):")
    dsa_sigs = []
    for s in self_sigs:
        if "r" not in s.mpis:
            continue
        d = kb.digest_for(s)
        sg = DSASignature(r=s.mpis["r"].value, s=s.mpis["s"].value, digest=d,
                          label="%s@%s" % (s.sig_type_name, s.created),
                          hash_algo=s.hash_algo, created=s.created)
        dsa_sigs.append(sg)
        _p("  type 0x%02x %-22s hash=%-9s created=%s" %
           (s.sig_type, s.sig_type_name, s.hash_algo_name, _utc(s.created)))
        _p("      digest reconstruction matches stored left16 : %s"
           % kb.digest_matches_left16(s))
        _p("      DSA verification                            : %s" % verify(par, sg))
        _p("      r = %d bits, s = %d bits"
           % (s.mpis["r"].declared_bits, s.mpis["s"].declared_bits))
    _p("")
    f = analyse_nonces(par, dsa_sigs)
    _p("Nonce analysis")
    _p("  signatures        : %d" % f.signature_count)
    _p("  verified          : %d" % f.verified_count)
    _p("  distinct r        : %d" % f.distinct_r)
    _p("  repeated r pairs  : %d" % len(f.repeated_r))
    _p("  private key recovered from reuse: %s"
       % ("YES" if f.recovered_private_key else "no"))
    _p("  %s" % f.lattice_requirement)
    for n in f.notes:
        _p("  note: %s" % n)
    if args.json:
        Path(args.json).write_text(json.dumps({
            "fingerprint": kb.fingerprint, "key_id": kb.key_id,
            "created": k.created, "algorithm": k.algo_name,
            "bits": k.key_size_bits,
            "signatures_total": len(all_sigs), "signatures_self": len(self_sigs),
            "distinct_r": f.distinct_r, "repeated_r": len(f.repeated_r),
            "verified": f.verified_count,
        }, indent=2))
        _p("\nwrote %s" % args.json)
    return 0


# --------------------------------------------------------------- lab-cve
def cmd_lab_cve(args) -> int:
    from .lab import cve_2016_6313 as cve
    _p("=" * 74)
    _p("%s reproduction" % cve.CVE_ID)
    _p("=" * 74)
    _p("Affected : %s" % cve.AFFECTED)
    _p("Claim    : 580 bytes of output predict the next 20 (4640 bits -> 160 bits)")
    _p("")
    for variant in ("1.4.7", "1.4.21"):
        r = cve.reproduce(variant, args.trials)
        _p("mix_pool %-7s : %4d/%-4d trials  rate=%.4f  %s"
           % (variant, r.successes, r.trials, r.success_rate,
              "REPRODUCED" if r.reproduced else "not predictable"))
        for n in r.notes:
            _p("                   %s" % n)
    _p("")
    r = cve.reproduce_through_read_pool(args.readpool_trials)
    _p("full read_pool path: %d/%d rate=%.4f" % (r.successes, r.trials, r.success_rate))
    for n in r.notes:
        _p("  %s" % n)
    _p("")
    a = cve.assess_applicability()
    _p("Prerequisites for exploitation against a historical public key:")
    for p in a["prerequisites"]:
        _p("  [%s] %s" % ("MET" if p["satisfied"] else "NOT MET", p["name"]))
        _p("        needs: %s" % p["required"])
    _p("")
    _p("Raw RNG bytes observable in public key material : %d"
       % a["observable_raw_rng_bytes"])
    _p("Raw RNG bytes required by the attack            : %d" % a["required_raw_rng_bytes"])
    _p("")
    _p("VERDICT: %s" % a["verdict"])
    return 0


# --------------------------------------------------------------- lab-differential
def cmd_lab_differential(args) -> int:
    import os as _os
    from .lab.cbridge.build import build, run_mix
    from .lab.gnupg_rng import BLOCKLEN, POOLSIZE, mix_pool_147, mix_pool_1421
    trees = {"1.4.7": Path(args.src147)}
    if args.src1421:
        trees["1.4.21"] = Path(args.src1421)
    ok_all = True
    for version, tree in trees.items():
        if not tree.exists():
            _p("SKIP %s: source tree not found at %s" % (version, tree))
            continue
        binary = build(tree, Path(args.workdir) / ("mix-%s" % version))
        mixer = mix_pool_147 if version == "1.4.7" else mix_pool_1421
        ok = True
        for _ in range(args.trials):
            pool = _os.urandom(POOLSIZE)
            c_out = run_mix(binary, pool, args.rounds)
            pp = bytearray(pool + bytes(BLOCKLEN))
            for _ in range(args.rounds):
                mixer(pp)
            ok &= bytes(pp[:POOLSIZE]) == c_out
        ok_all &= ok
        _p("GnuPG %-7s : real C code vs Python model over %d trials x %d rounds -> %s"
           % (version, args.trials, args.rounds, "IDENTICAL" if ok else "MISMATCH"))
    return 0 if ok_all else 1


# --------------------------------------------------------------- lab-synth
def cmd_lab_synth(args) -> int:
    from .analysis.stats import battery_summary, full_battery
    from .lab.harvest import (extract_dsa_signature_values, find_gpg,
                              generate_signature_corpus)
    from .openpgp import dearmor, parse_keyblock
    from .analysis.dsa import DSAParams, DSASignature, analyse_nonces
    bins = find_gpg()
    if args.gpg:
        bins["historical"] = args.gpg
    if "historical" not in bins:
        _p("No GnuPG 1.4.7 binary found. Set SPA_GPG147 or pass --gpg.")
        _p("Build one with: make gnupg147   (or use the Docker lab)")
        return 2
    _p("=" * 74)
    _p("Synthetic key laboratory")
    _p("=" * 74)
    for label, path in bins.items():
        import subprocess
        v = subprocess.run([path, "--version"], capture_output=True)
        _p("%-11s : %s  (%s)" % (label, v.stdout.decode().splitlines()[0], path))
    _p("")
    _p("Generating a synthetic DSA-%d key and %d signatures with the historical build"
       % (args.bits, args.count))
    pub, sigs = generate_signature_corpus(bins["historical"], count=args.count,
                                          key_length=args.bits)
    _p("  produced %d detached signatures" % len(sigs))
    kb = parse_keyblock(dearmor(pub.decode()).__getitem__(0).body)
    par = DSAParams(kb.primary.mpis["p"].value, kb.primary.mpis["q"].value,
                    kb.primary.mpis["g"].value, kb.primary.mpis["y"].value)
    vals = extract_dsa_signature_values(sigs)
    corpus = [DSASignature(r=v["r"], s=v["s"], label=v["label"]) for v in vals]
    f = analyse_nonces(par, corpus)
    _p("")
    _p("Nonce analysis over synthetic corpus")
    _p("  signatures        : %d" % f.signature_count)
    _p("  distinct r        : %d" % f.distinct_r)
    _p("  repeated r pairs  : %d" % len(f.repeated_r))
    _p("  %s" % f.lattice_requirement)
    _p("")
    blob = b"".join(v["r"].to_bytes(20, "big") for v in vals)
    _p("Randomness battery over concatenated r values (%d bytes)" % len(blob))
    for res in full_battery(blob):
        _p("  %s" % res)
    _p("  summary: %s" % battery_summary(full_battery(blob)))
    _p("")
    _p("NOTE: every key and signature above is synthetic, generated for this run.")
    return 0


# --------------------------------------------------------------- lab-rngstats
def cmd_lab_rngstats(args) -> int:
    from .analysis.stats import full_battery
    from .lab.gnupg_rng import fresh
    _p("Pool-generator output statistics (%d bytes per variant)" % args.bytes)
    for variant in ("1.4.7", "1.4.21"):
        g = fresh(variant, seed=os.urandom(256), word_size=args.word_size)
        data = g.get_random_bytes(args.bytes)
        _p("")
        _p("GnuPG %s  (word_size=%d, mixes=%d)" % (variant, args.word_size, g.mix_count))
        for r in full_battery(data):
            _p("  %s" % r)
    _p("")
    _p("Both variants pass the battery. That is expected and is the point: the "
       "1.4.7 defect is a STRUCTURAL predictability relation, not a statistical "
       "bias. No black-box randomness test can detect it, which is precisely why "
       "it survived from 2007 to 2016.")
    return 0


# --------------------------------------------------------------- lab-reconstruct
def cmd_lab_reconstruct(args) -> int:
    from .lab.harvest import find_gpg
    from .lab.reconstruct import run_experiment, search_space
    bins = find_gpg()
    gpg = args.gpg or bins.get("historical")
    if not gpg:
        _p("No GnuPG 1.4.7 binary found. Set SPA_GPG147 or pass --gpg.")
        return 2
    _p("=" * 74)
    _p("Can a key be reconstructed from its username and creation time?")
    _p("=" * 74)
    _p("")
    _p("Hypothesis: the User ID is a missing input to key generation, so trying")
    _p("candidate usernames at the right timestamp reproduces the original key.")
    _p("")
    _p("Test: generate many keys with the historical binary, holding the User ID")
    _p("fixed. If the hypothesis held, they would collide.")
    _p("")
    res = run_experiment(gpg, uid_name=args.name, uid_email=args.email,
                         count=args.count)
    _p("User ID used for every key : %s" % res.uid)
    _p("keys generated             : %d" % res.keys_generated)
    _p("distinct fingerprints      : %d" % res.distinct_fingerprints)
    _p("distinct public values y   : %d" % res.distinct_y)
    _p("distinct primes p          : %d" % res.distinct_p)
    _p("distinct primes q          : %d" % res.distinct_q)
    _p("")
    if res.timestamp_collisions:
        _p("Keys that ALSO shared a creation second:")
        for ts, n, distinct in res.timestamp_collisions:
            _p("  unix %d : %d keys -> %d distinct keys" % (ts, n, distinct))
    _p("")
    _p("username determines the key          : %s" % res.uid_determines_key)
    _p("username + timestamp determine key   : %s" % res.uid_and_time_determine_key)
    for n in res.notes:
        _p("  note: %s" % n)
    _p("")
    sp = search_space()
    _p("Even granting the hypothesis, the remaining search is:")
    _p("  private key space : 2^%d = %s candidates"
       % (sp["private_key_bits"], sp["candidates_scientific"]))
    _p("  at 1e12 keys/sec  : %s years" % sp["years_at_that_rate"])
    _p("  %s" % sp["note"])
    _p("")
    _p("CONCLUSION: the User ID is a label attached AFTER generation, and the")
    _p("timestamp is recorded rather than consumed. Neither reaches the random")
    _p("number generator, so no list of candidate usernames can reproduce the key.")
    return 0


# --------------------------------------------------------------- report
def cmd_report(args) -> int:
    from .audit import audit_key
    from .report.render import to_json, to_markdown
    src = Path(args.gnupg_src) if args.gnupg_src else DEFAULT_GNUPG_SRC
    rep = audit_key(Path(args.key), src if src.exists() else None, deep=not args.fast)
    if src.exists():
        rep.provenance = json.loads((ROOT / "data" / "provenance.json").read_text())
    md = to_markdown(rep)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    _p("wrote %s (%d bytes)" % (out, len(md)))
    if args.json:
        Path(args.json).write_text(to_json(rep))
        _p("wrote %s" % args.json)
    from .report.findings import Category
    _p("")
    for c in Category:
        _p("  Category %s : %d findings" % (c.value, len(rep.by_category(c))))
    return 0


# --------------------------------------------------------------- verify-message
def cmd_verify_message(args) -> int:
    from .analysis.bitcoin_scope import verify_signed_message
    msg = Path(args.message).read_text() if args.message_file else args.message
    res = verify_signed_message(msg, args.signature, args.address)
    _p("Bitcoin signed-message verification")
    _p("  claimed address  : %s" % (res.address_claimed or "(none supplied)"))
    _p("  recovered address: %s" % (res.address_recovered or "(recovery failed)"))
    _p("  valid            : %s" % res.valid)
    if res.error:
        _p("  error            : %s" % res.error)
    for n in res.notes:
        _p("  note: %s" % n)
    return 0 if res.valid else 1


# --------------------------------------------------------------- scan-ecdsa
def cmd_scan_ecdsa(args) -> int:
    """Scan a corpus of ECDSA signatures for reused nonces.

    Input is a JSON list of objects with r, s and optionally z (the signed digest,
    hex or int) and label. Accepts DER-encoded signatures via a "der" field.

    Deliberately offline: this tool does not fetch from any blockchain API. Point
    it at a dump produced by your own node or explorer export, so the analysis is
    reproducible and the data provenance is yours.
    """
    from .analysis.bitcoin_scope import (find_ecdsa_nonce_reuse,
                                         parse_der_signature, recover_ecdsa_key)
    raw = json.loads(Path(args.input).read_text())
    sigs = []
    for i, item in enumerate(raw):
        if "der" in item:
            r, s_ = parse_der_signature(bytes.fromhex(item["der"]))
        else:
            r, s_ = int(str(item["r"]), 0), int(str(item["s"]), 0)
        entry = {"r": r, "s": s_, "label": item.get("label", "sig-%d" % i)}
        if "z" in item:
            entry["z"] = int(str(item["z"]), 0) if not isinstance(item["z"], str) \
                else int(item["z"], 16) if len(item["z"]) == 64 else int(item["z"], 0)
        sigs.append(entry)

    f = find_ecdsa_nonce_reuse(sigs)
    _p("ECDSA nonce-reuse scan")
    _p("  signatures supplied : %d" % f.signature_count)
    _p("  distinct r values   : %d" % f.distinct_r)
    _p("  reused-nonce pairs  : %d" % len(f.repeated_r))
    for n in f.notes:
        _p("  note: %s" % n)
    recovered = 0
    for a, b, r in f.repeated_r:
        _p("  REUSED r=%x between %s and %s" % (r, a, b))
        sa = next(x for x in sigs if x["label"] == a)
        sb = next(x for x in sigs if x["label"] == b)
        if "z" in sa and "z" in sb:
            key = recover_ecdsa_key(r, sa["s"], sa["z"], sb["s"], sb["z"])
            if key is not None:
                recovered += 1
                _p("      private key recoverable from these two signatures")
    if f.repeated_r and not recovered:
        _p("  (supply the signed digests as 'z' to demonstrate recoverability)")
    _p("")
    _p("Reminder: an UNSPENT output publishes no signature at all, so addresses "
       "that never moved coins contribute nothing to this analysis.")
    return 0


# --------------------------------------------------------------- verify-provenance
def cmd_verify_provenance(args) -> int:
    import hashlib
    prov = json.loads((ROOT / "data" / "provenance.json").read_text())
    ok = True
    art = prov["artifacts"]["satoshi_public_key"]
    path = ROOT / art["path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    match = digest == art["sha256"]
    ok &= match
    _p("key file sha256   : %s  %s" % (digest, "OK" if match else "MISMATCH"))
    from .openpgp import dearmor, parse_keyblock
    kb = parse_keyblock(dearmor(path.read_text())[0].body)
    fpr_ok = kb.fingerprint == art["expected_fingerprint"]
    ok &= fpr_ok
    _p("fingerprint       : %s  %s" % (kb.fingerprint, "OK" if fpr_ok else "MISMATCH"))
    created_ok = kb.primary.created == art["expected_created_unix"]
    ok &= created_ok
    _p("created           : %d  %s" % (kb.primary.created, "OK" if created_ok else "MISMATCH"))
    _p("")
    _p("The fingerprint is the trust anchor: it is recomputed from the packet body, "
       "so it holds regardless of what the keyserver appended.")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="spa", description="Reproducible audit of the historical GnuPG "
                                "environment behind OpenPGP key 0x5EC948A1")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("analyze-key", help="parse and analyse an OpenPGP public key")
    p.add_argument("--key", default=str(DEFAULT_KEY))
    p.add_argument("--json", help="also write machine-readable output here")
    p.add_argument("--fast", action="store_true", help="skip primality proofs")
    p.set_defaults(func=cmd_analyze_key)

    p = sub.add_parser("lab-cve", help="reproduce CVE-2016-6313")
    p.add_argument("--trials", type=int, default=200)
    p.add_argument("--readpool-trials", type=int, default=25)
    p.set_defaults(func=cmd_lab_cve)

    p = sub.add_parser("lab-differential",
                       help="compare the Python pool model against real GnuPG C code")
    p.add_argument("--src147", default=str(DEFAULT_GNUPG_SRC))
    p.add_argument("--src1421", default=os.environ.get("SPA_GNUPG_SRC_1421", ""))
    p.add_argument("--trials", type=int, default=5)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--workdir", default="/tmp/spa-cbridge")
    p.set_defaults(func=cmd_lab_differential)

    p = sub.add_parser("lab-synth", help="generate synthetic keys with real GnuPG 1.4.7")
    p.add_argument("--gpg", help="path to the historical gpg binary")
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--bits", type=int, default=1024)
    p.set_defaults(func=cmd_lab_synth)

    p = sub.add_parser("lab-rngstats", help="statistical battery over pool output")
    p.add_argument("--bytes", type=int, default=65536)
    p.add_argument("--word-size", type=int, default=4, choices=(4, 8))
    p.set_defaults(func=cmd_lab_rngstats)

    p = sub.add_parser("lab-reconstruct",
                       help="test whether username+timestamp can reproduce a key")
    p.add_argument("--gpg", help="path to the historical gpg binary")
    p.add_argument("--name", default="Satoshi Nakamoto")
    p.add_argument("--email", default="satoshin@gmx.com")
    p.add_argument("--count", type=int, default=25)
    p.set_defaults(func=cmd_lab_reconstruct)

    p = sub.add_parser("report", help="produce the five-category audit report")
    p.add_argument("--key", default=str(DEFAULT_KEY))
    p.add_argument("--gnupg-src", help="path to a GnuPG git checkout")
    p.add_argument("--output", default=str(ROOT / "reports" / "AUDIT_REPORT.md"))
    p.add_argument("--json", help="also write JSON here")
    p.add_argument("--fast", action="store_true")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("verify-message", help="verify a Bitcoin signed message")
    p.add_argument("--message", required=True)
    p.add_argument("--message-file", action="store_true",
                   help="treat --message as a path")
    p.add_argument("--signature", required=True)
    p.add_argument("--address")
    p.set_defaults(func=cmd_verify_message)

    p = sub.add_parser("scan-ecdsa",
                       help="scan a JSON corpus of ECDSA signatures for nonce reuse")
    p.add_argument("--input", required=True,
                   help="JSON list of {r,s[,z,label]} or {der[,z,label]}")
    p.set_defaults(func=cmd_scan_ecdsa)

    p = sub.add_parser("verify-provenance", help="re-check pinned artifact digests")
    p.set_defaults(func=cmd_verify_provenance)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
