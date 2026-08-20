"""secp256k1 correctness and the PGP/Bitcoin domain boundary."""
import hashlib
import secrets

from spa.analysis import bitcoin_scope as bs


def test_generator_point():
    assert bs.point_mul(1) == (bs.GX, bs.GY)


def test_known_address_vector():
    """Public test vector: private key 1. Validates the whole encoding stack -
    point math, SHA-256, RIPEMD-160 and Base58Check - in one shot.
    This is a TEST VECTOR, not an address attributed to anyone."""
    assert bs.pubkey_to_address(bs.point_mul(1), False) == "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm"


def test_point_arithmetic_identities():
    p = bs.point_mul(secrets.randbelow(bs.N - 1) + 1)
    assert bs.point_add(p, None) == p
    assert bs.point_add(None, p) == p
    assert bs.point_mul(bs.N, p) is None          # order of the group
    assert bs.point_add(p, (p[0], bs.P - p[1])) is None   # P + (-P) = infinity


def test_ecdsa_sign_verify_roundtrip():
    priv = secrets.randbelow(bs.N - 1) + 1
    pub = bs.point_mul(priv)
    z = hashlib.sha256(b"lab message").digest()
    k = secrets.randbelow(bs.N - 1) + 1
    r = bs.point_mul(k)[0] % bs.N
    s = (pow(k, -1, bs.N) * (int.from_bytes(z, "big") + r * priv)) % bs.N
    assert bs.ecdsa_verify(pub, z, r, s) is True
    assert bs.ecdsa_verify(pub, hashlib.sha256(b"other").digest(), r, s) is False


def test_ecdsa_nonce_reuse_recovers_key():
    """Positive control for the on-chain nonce-reuse detector."""
    priv = secrets.randbelow(bs.N - 1) + 1
    k = secrets.randbelow(bs.N - 1) + 1
    r = bs.point_mul(k)[0] % bs.N
    z1 = int.from_bytes(hashlib.sha256(b"a").digest(), "big")
    z2 = int.from_bytes(hashlib.sha256(b"b").digest(), "big")
    s1 = (pow(k, -1, bs.N) * (z1 + r * priv)) % bs.N
    s2 = (pow(k, -1, bs.N) * (z2 + r * priv)) % bs.N
    assert bs.recover_ecdsa_key(r, s1, z1, s2, z2) == priv


def test_nonce_reuse_detector():
    sigs = [{"r": 5, "s": 1, "label": "a"}, {"r": 5, "s": 2, "label": "b"},
            {"r": 9, "s": 3, "label": "c"}]
    f = bs.find_ecdsa_nonce_reuse(sigs)
    assert len(f.repeated_r) == 1
    assert f.distinct_r == 2


def test_signed_message_roundtrip():
    """Sign a message the way a wallet does, then verify + recover the address."""
    import base64
    priv = secrets.randbelow(bs.N - 1) + 1
    pub = bs.point_mul(priv)
    msg = "synthetic lab message"
    z = bs.message_hash(msg)
    k = secrets.randbelow(bs.N - 1) + 1
    R = bs.point_mul(k)
    r = R[0] % bs.N
    s = (pow(k, -1, bs.N) * (int.from_bytes(z, "big") + r * priv)) % bs.N
    if s > bs.N // 2:                      # low-s normalisation flips recid parity
        s = bs.N - s
        R = (R[0], bs.P - R[1])
    addr = bs.pubkey_to_address(pub, True)
    for recid in range(4):                 # find the matching recovery id
        header = 27 + recid + 4            # +4 => compressed
        sig = base64.b64encode(bytes([header]) + r.to_bytes(32, "big")
                               + s.to_bytes(32, "big")).decode()
        res = bs.verify_signed_message(msg, sig, addr)
        if res.valid:
            return
    raise AssertionError("no recovery id produced a valid signature")


def test_bad_signature_is_rejected():
    res = bs.verify_signed_message("hello", "bm90IGEgc2ln", "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm")
    assert res.valid is False
    assert res.error


def test_domain_separation_is_explicit():
    """A GnuPG RNG finding must never be applicable to Bitcoin keys."""
    d = bs.DOMAIN_SEPARATION
    assert d["pgp_key_5EC948A1"]["cve_2016_6313_applicable"] is True
    assert d["bitcoin_keys"]["cve_2016_6313_applicable"] is False
    assert "ECDSA" in d["bitcoin_keys"]["signature_algorithm"]
    assert "DSA" in d["pgp_key_5EC948A1"]["signature_algorithm"]
