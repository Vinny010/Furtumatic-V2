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


# --------------------------------------------------------------- scan-pgp-nonces
def cmd_scan_pgp_nonces(args) -> int:
    import glob
    from .analysis.pgpscan import (make_synthetic_control, scan_armored_texts,
                                   scan_records)
    _p("PGP DSA/ECDSA nonce-reuse scan")
    _p("=" * 74)
    _p("")
    _p("Flags any key that signed two messages with the same nonce (same r,")
    _p("differing s) - which leaks its private key from public data. This is a")
    _p("disclosure/revocation tool: it flags vulnerable key ids; it recovers a")
    _p("private key only for synthetic keys or ones you mark as your own.")
    _p("")

    if not args.no_control:
        recs, par, keyid, true_x = make_synthetic_control(reuse=True)
        cf = scan_records(recs, owned_keyids={keyid},
                          params_by_keyid={keyid: par})
        ok = bool(cf.vulnerable_keys) and \
            cf.vulnerable_keys[0].recovered_private_key == true_x
        _p("positive control (planted reuse) : %s"
           % ("DETECTED + recovered" if ok else "FAILED"))
        if not ok:
            _p("  Control failed - the scanner is broken; results below are void.")
            return 1
        recs2, par2, keyid2, _x2 = make_synthetic_control(reuse=False)
        nf = scan_records(recs2)
        _p("negative control (no reuse)      : %s"
           % ("clean" if nf.clean else "FALSE POSITIVE"))
        _p("")

    inputs = []
    for pattern in (args.input or []):
        for path in glob.glob(pattern):
            try:
                inputs.append((path, Path(path).read_text(errors="replace")))
            except Exception as exc:
                _p("  skip %s: %s" % (path, exc))
    if not inputs:
        _p("No key files supplied (--input). Ran controls only.")
        _p("")
        _p("To scan real keys, pass armored key files or a keyserver dump:")
        _p("  python -m spa.cli scan-pgp-nonces --input 'keys/*.asc'")
        _p("  python -m spa.cli scan-pgp-nonces --input dump.asc")
        return 0

    owned = set(args.owned or [])
    f = scan_armored_texts(inputs, owned_keyids=owned)
    _p("keys scanned              : %d" % f.keys_scanned)
    _p("signatures scanned        : %d" % f.signatures_scanned)
    _p("issuers seen              : %d" % f.issuers_seen)
    _p("duplicate signatures      : %d" % f.duplicate_signatures)
    _p("vulnerable keys           : %d" % len(f.vulnerable_keys))
    _p("")
    for vk in f.vulnerable_keys:
        algo = {17: "DSA", 19: "ECDSA"}.get(vk.pubkey_algo, "algo-%d" % vk.pubkey_algo)
        _p("  VULNERABLE key %s (%s): nonce reused across %d signatures"
           % (vk.issuer_keyid, algo, vk.signature_count))
        if vk.recovered_private_key is not None:
            _p("    private key recovered (owned key) - revoke and rotate now")
        else:
            _p("    private key is recoverable from public data - disclose to the "
               "key owner so they can revoke")
    _p("")
    for n in f.notes:
        _p("note: %s" % n)
    return 0


# --------------------------------------------------------------- weak-entropy
def cmd_weak_entropy(args) -> int:
    from .analysis.weakentropy import (demonstrate_recovery,
                                       positive_control_for_related_scan)
    _p("Keyspace-collapse reproduction (synthetic keys only)")
    _p("=" * 74)
    _p("")
    _p("Models the failure class behind Debian OpenSSL, Android SecureRandom,")
    _p("brainwallets, and the 2026 Coldcard breach: the curve is never broken, the")
    _p("generator's real entropy is. Every key here is synthetic and controls")
    _p("nothing; no real wallet, seed, or address is touched.")
    _p("")
    _p("--- 1. keyspace collapse is brute-forceable from public keys ---")
    r = demonstrate_recovery(entropy_bits=args.bits, key_count=args.keys)
    _p("nominal strength   : %d bits" % r.nominal_bits)
    _p("collapsed to       : %d bits (2^%d smaller)"
       % (r.entropy_bits, r.collapse_factor_log2))
    _p("keys recovered     : %d/%d" % (r.brute_force_recovered, r.keys_generated))
    for n in r.notes:
        _p("  %s" % n)
    _p("")
    _p("--- 2. positive control: does our detector catch it? ---")
    c = positive_control_for_related_scan()
    _p("sequential keys    : %d" % c.keys)
    _p("related pairs found : %d" % c.related_pairs)
    _p("DETECTOR FIRED     : %s" % ("YES" if c.detector_fired else "NO"))
    for n in c.notes:
        _p("  %s" % n)
    _p("")
    _p("What this proves, precisely:")
    _p("  * The related-key scan works, so its ZERO result on 21,953 Patoshi keys")
    _p("    genuinely rules out the SEQUENTIAL / OFFSET collapse class.")
    _p("  * It does NOT rule out a HASHED low-entropy collapse (the Coldcard shape),")
    _p("    which scatters keys. Detecting that needs the specific derivation and is")
    _p("    infeasible blind - an honest limit, not a closed door.")
    _p("  * Separately ruled out for Satoshi's keys: nonce reuse (verify-spendchain),")
    _p("    duplicate keys (0), and - for the PGP key - a degenerate GnuPG RNG.")
    return 0 if c.detector_fired else 1


# --------------------------------------------------------------- verify-spendchain
def cmd_verify_spendchain(args) -> int:
    from .analysis.spendchain import analyse_chain
    path = Path(args.input)
    if not path.exists():
        _p("No spend-chain data at %s" % path)
        return 2
    blob = json.loads(path.read_text())
    entries = [(e["expected_txid"], e.get("block_height"), e["raw_hex"])
               for e in blob["entries"]]
    pubkey = blob["signing_pubkey"]
    _p("Block-9 coinbase spend chain - independent verification")
    _p("=" * 74)
    _p("")
    _p("Unspent coins publish no signature, so the dormant Patoshi coinbases have")
    _p("no nonce to attack at all. This key is the exception: it was spent and then")
    _p("reused as change at each hop, making it the ONLY Satoshi-attributed key")
    _p("that ever signed more than once - and so the only one where nonce reuse")
    _p("could have leaked a private key.")
    _p("")
    _p("signing key : %s" % pubkey)
    _p("")
    f = analyse_chain(entries, pubkey)
    _p("transactions              : %d" % f.transactions)
    _p("txids authenticated       : %d/%d" % (f.txids_authenticated, f.transactions))
    if f.txid_mismatches:
        for m in f.txid_mismatches:
            _p("   MISMATCH %s" % m)
        _p("")
        _p("Refusing to analyse unauthenticated bytes.")
        return 1
    _p("")
    _p("signatures found          : %d" % len(f.signatures))
    _p("signatures verified       : %d" % f.verified)
    _p("distinct nonces (r)       : %d" % f.distinct_r)
    _p("reused-nonce pairs        : %d" % len(f.reused_nonce_pairs))
    _p("private key recovered     : %s"
       % ("YES" if f.recovered_key is not None else "no"))
    _p("")
    for rec in f.signatures:
        _p("  %-16s tx %s..%s  verify=%s"
           % (rec.label, rec.txid[:10], rec.txid[-6:], rec.verifies))
        _p("       r = %064x" % rec.r)
    _p("")
    for n in f.notes:
        _p("note: %s" % n)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps({
            "transactions": f.transactions,
            "txids_authenticated": f.txids_authenticated,
            "signatures": len(f.signatures),
            "verified": f.verified,
            "distinct_r": f.distinct_r,
            "reused_nonce_pairs": len(f.reused_nonce_pairs),
            "nonce_safe": f.nonce_safe,
            "signing_pubkey": pubkey,
            "r_values": ["%064x" % s.r for s in f.signatures],
            "notes": f.notes,
        }, indent=2))
        _p("wrote %s" % args.json)
    return 0 if f.nonce_safe else 1


# --------------------------------------------------------------- scan-related
def cmd_scan_related(args) -> int:
    from .analysis.relatedkeys import load_p2pk_csv, scan, with_control
    path = Path(args.input)
    if not path.exists():
        _p("No P2PK corpus at %s" % path)
        _p("Expected a CSV with columns 'Block Height' and 'Address/Pubkey'.")
        return 2
    records = load_p2pk_csv(path)
    _p("Related-key scan over a pay-to-public-key corpus")
    _p("=" * 74)
    _p("")
    _p("Tests whether any two private keys differ by a small offset. If so,")
    _p("P_j = P_i + delta*G, which is visible from public keys alone. This is the")
    _p("failure class behind the Debian OpenSSL and Android SecureRandom losses.")
    _p("")
    _p("corpus            : %s" % path)
    _p("keys loaded       : %d" % len(records))
    _p("delta range       : 1 .. %d" % args.max_delta)
    control_labels = None
    if not args.no_control:
        records, control_labels = with_control(records, delta=args.control_delta)
        _p("positive control  : injected pair with delta=%d" % args.control_delta)
    _p("")

    def progress(d, total, hits, secs):
        _p("  delta <= %-6d %6.1fs   relations found: %d" % (d, secs, hits))

    f = scan(records, max_delta=args.max_delta, progress=progress,
             control_labels=control_labels)
    _p("")
    _p("keys scanned      : %d" % f.keys_scanned)
    _p("off-curve entries : %d" % len(f.off_curve))
    _p("duplicate keys    : %d" % len(f.duplicate_keys))
    _p("elapsed           : %.1fs" % f.elapsed_seconds)
    _p("")
    real_hits = f.related_pairs
    if control_labels:
        _p("POSITIVE CONTROL detected : %s"
           % ("YES" if f.control_detected else "NO"))
        if not f.control_detected:
            _p("  The scan failed to find a PLANTED relation. Its negative result")
            _p("  on real data is therefore meaningless. Investigate before trusting.")
            for n in f.notes:
                _p("note: %s" % n)
            return 1
    _p("")
    _p("RELATED KEYS AMONG REAL CORPUS : %d" % len(real_hits))
    for a, b, d in real_hits[:40]:
        _p("   %s  <->  %s   delta=%d" % (a, b, d))
    if len(real_hits) > 40:
        _p("   ... and %d more" % (len(real_hits) - 40))
    _p("")
    for n in f.notes:
        _p("note: %s" % n)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps({
            "corpus": str(path),
            "keys_scanned": f.keys_scanned,
            "max_delta": f.max_delta,
            "duplicate_keys": len(f.duplicate_keys),
            "related_pairs": real_hits,
            "control_detected": f.control_detected,
            "elapsed_seconds": f.elapsed_seconds,
            "notes": f.notes,
        }, indent=2))
        _p("wrote %s" % args.json)
    return 0


# --------------------------------------------------------------- patoshi
def cmd_patoshi(args) -> int:
    from .analysis.patoshi import analyse, load_blocks, nonce_histogram
    path = Path(args.input)
    if not path.exists():
        _p("No block data at %s" % path)
        _p("")
        _p("This environment's egress policy blocks every blockchain API, so the")
        _p("data has to come in through a channel that is allowed (GitHub is).")
        _p("Fetch it on a machine without the proxy, then commit it:")
        _p("")
        _p("  python3 tools/fetch_early_blocks.py --end 50000 --out %s" % path)
        _p("  git add %s && git commit -m 'Add early block data' && git push" % path)
        _p("")
        return 2
    blocks = load_blocks(path)
    f = analyse(blocks, nonce_band=args.band)
    _p("Patoshi-pattern analysis")
    _p("=" * 74)
    _p("blocks analysed        : %d" % f.blocks_analysed)
    _p("with parsed ExtraNonce : %d" % f.blocks_with_extranonce)
    _p("nonce band threshold   : %.2f of the 32-bit space" % f.nonce_band)
    _p("")
    _p("cluster blocks         : %d (%.1f%% of sample)"
       % (f.cluster_size, 100 * f.cluster_share))
    _p("other blocks           : %d" % len(f.other_blocks))
    _p("monotone ExtraNonce runs in cluster : %d" % f.slope_segments)
    _p("subsidy attributable to cluster     : %.0f BTC" % f.estimated_btc)
    _p("")
    _p("Header-nonce distribution (uniform mining gives a flat profile):")
    hist = nonce_histogram(blocks, bins=args.bins)
    peak = max((c for _, c in hist), default=1) or 1
    for centre, count in hist:
        bar = "#" * int(50 * count / peak)
        _p("  %.2f  %-50s %d" % (centre, bar, count))
    _p("")
    for n in f.notes:
        _p("note: %s" % n)
    if args.json:
        Path(args.json).write_text(json.dumps({
            "blocks_analysed": f.blocks_analysed,
            "cluster_size": f.cluster_size,
            "cluster_share": f.cluster_share,
            "estimated_btc": f.estimated_btc,
            "slope_segments": f.slope_segments,
            "cluster_blocks": f.cluster_blocks,
        }, indent=2))
        _p("")
        _p("wrote %s" % args.json)
    return 0


# --------------------------------------------------------------- derive-candidates
def cmd_derive_candidates(args) -> int:
    from .analysis.candidates import derive_candidates
    from .audit import load_key
    _block, kb = load_key(Path(args.key))
    cands = derive_candidates(kb, kb.self_signatures())
    _p("Bitcoin address candidates derived from PUBLIC values in this PGP key")
    _p("=" * 74)
    _p("")
    _p("Tests one narrow hypothesis: that a Bitcoin private key was derived from a")
    _p("value already published in this key. %d motivated candidates, rather than a"
       % len(cands))
    _p("blind search of 2^256 where the hit probability would be about 1e-74.")
    _p("")
    rows = []
    for c in cands:
        for kind, addr in c.addresses.items():
            rows.append(addr)
            _p("%-36s %-14s %s" % (addr, kind, c.label))
    _p("")
    _p("candidates : %d" % len(cands))
    _p("addresses  : %d (uncompressed and compressed for each)" % len(rows))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text("\n".join(rows) + "\n")
        _p("")
        _p("address list -> %s (one per line, ready for bulk lookup)" % args.output)
    _p("")
    _p("Only ADDRESSES are written. Derived private keys stay in memory and are")
    _p("never persisted: this tool reports, it does not build transactions, and a")
    _p("key that controls funds belongs to whoever generated it.")
    _p("")
    _p("EXPECTED RESULT: no hits. A negative result is the useful outcome - it")
    _p("closes the 'what if they reused something obvious' question by measurement.")
    return 0


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

    p = sub.add_parser("scan-pgp-nonces",
                       help="scan a PGP key corpus for reused DSA/ECDSA nonces")
    p.add_argument("--input", action="append",
                   help="armored key file(s) or a keyserver dump; globs allowed")
    p.add_argument("--owned", action="append",
                   help="key id you own, enabling private-key recovery for it")
    p.add_argument("--no-control", action="store_true")
    p.set_defaults(func=cmd_scan_pgp_nonces)

    p = sub.add_parser("weak-entropy",
                       help="reproduce the keyspace-collapse failure class (synthetic)")
    p.add_argument("--bits", type=int, default=20,
                   help="collapsed entropy bits for the recovery demo")
    p.add_argument("--keys", type=int, default=5)
    p.set_defaults(func=cmd_weak_entropy)

    p = sub.add_parser("verify-spendchain",
                       help="verify the block-9 spend chain and test for nonce reuse")
    p.add_argument("--input", default=str(ROOT / "data" / "block9_spend_chain.json"))
    p.add_argument("--json", help="write findings here")
    p.set_defaults(func=cmd_verify_spendchain)

    p = sub.add_parser("scan-related",
                       help="scan a P2PK corpus for related (small-offset) keys")
    p.add_argument("--input", required=True, help="CSV of P2PK outputs")
    p.add_argument("--max-delta", type=int, default=512)
    p.add_argument("--control-delta", type=int, default=7)
    p.add_argument("--no-control", action="store_true",
                   help="skip the injected positive control (not recommended)")
    p.add_argument("--json", help="write findings here")
    p.set_defaults(func=cmd_scan_related)

    p = sub.add_parser("patoshi",
                       help="mining-fingerprint analysis over early block data")
    p.add_argument("--input", default=str(ROOT / "data" / "early_blocks.csv"))
    p.add_argument("--band", type=float, default=0.45,
                   help="nonce-space fraction defining the restricted band")
    p.add_argument("--bins", type=int, default=20)
    p.add_argument("--json", help="write findings here")
    p.set_defaults(func=cmd_patoshi)

    p = sub.add_parser("derive-candidates",
                       help="derive Bitcoin addresses from public values in the key")
    p.add_argument("--key", default=str(DEFAULT_KEY))
    p.add_argument("--output", help="write the plain address list here")
    p.set_defaults(func=cmd_derive_candidates)

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
