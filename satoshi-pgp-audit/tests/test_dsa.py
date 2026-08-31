"""DSA parameter validation, verification, and nonce attacks."""
import hashlib

import pytest

from spa.analysis.dsa import (DSAParams, DSASignature, analyse_nonces,
                              digest_to_int, recover_x_from_shared_nonce,
                              validate_params, verify)
from spa.analysis.numbertheory import is_probable_prime


@pytest.fixture(scope="module")
def satoshi_params(keyblock):
    m = keyblock.primary.mpis
    return DSAParams(m["p"].value, m["q"].value, m["g"].value, m["y"].value)


@pytest.fixture(scope="module")
def satoshi_sigs(keyblock, satoshi_params):
    out = []
    for s in keyblock.self_signatures():
        out.append(DSASignature(r=s.mpis["r"].value, s=s.mpis["s"].value,
                                digest=keyblock.digest_for(s),
                                label="%s@%s" % (s.sig_type_name, s.created)))
    return out


def test_every_parameter_check_passes(satoshi_params):
    checks = validate_params(satoshi_params, deep=True)
    failures = [c for c in checks if c.passed is False]
    assert failures == [], "structural defect in the published key: %s" % failures


def test_p_and_q_are_prime(satoshi_params):
    assert is_probable_prime(satoshi_params.q)
    assert is_probable_prime(satoshi_params.p)
    assert (satoshi_params.p - 1) % satoshi_params.q == 0


def test_subgroup_membership(satoshi_params):
    p, q, g, y = (satoshi_params.p, satoshi_params.q,
                  satoshi_params.g, satoshi_params.y)
    assert pow(g, q, p) == 1
    assert pow(y, q, p) == 1


def test_all_self_signatures_verify(satoshi_sigs, satoshi_params):
    """If these failed, the keyserver copy would be corrupt or forged."""
    assert len(satoshi_sigs) == 3
    for sig in satoshi_sigs:
        assert verify(satoshi_params, sig) is True, sig.label


def test_no_nonce_reuse_in_published_signatures(satoshi_sigs, satoshi_params):
    """No r repeats with a DIFFERING s, so no nonce was reused."""
    f = analyse_nonces(satoshi_params, satoshi_sigs)
    assert f.repeated_r == []
    assert f.recovered_private_key is None


def test_duplicate_subkey_binding_is_not_nonce_reuse(satoshi_sigs, satoshi_params):
    """The keyblock carries one subkey-binding signature twice, in two packet
    encodings. Both share r AND s, so it is a duplicate rather than a reused
    nonce. Conflating the two would raise a false alarm on this key."""
    f = analyse_nonces(satoshi_params, satoshi_sigs)
    assert len(f.duplicate_signatures) == 1
    assert f.unique_signature_values == 2
    assert f.distinct_r == 2


def test_corpus_far_below_lattice_threshold(satoshi_sigs, satoshi_params):
    f = analyse_nonces(satoshi_params, satoshi_sigs)
    assert f.lattice_feasible is False


# ---- positive control: the attack DOES work when the nonce actually repeats ----
@pytest.fixture(scope="module")
def synthetic_key(keyblock):
    """Reuse the real key's DOMAIN parameters (public, standard) with a private
    exponent generated here. The private key is synthetic; nothing real is used."""
    import secrets
    m = keyblock.primary.mpis
    p, q, g = m["p"].value, m["q"].value, m["g"].value
    x = secrets.randbelow(q - 1) + 1
    return DSAParams(p, q, g, pow(g, x, p)), x


def _sign(par, x, k, msg):
    d = hashlib.sha1(msg).digest()
    h = digest_to_int(d, par.q)
    r = pow(par.g, k, par.p) % par.q
    s = (pow(k, -1, par.q) * (h + x * r)) % par.q
    return DSASignature(r=r, s=s, digest=d, label=msg.decode())


def test_synthetic_signatures_verify(synthetic_key):
    import secrets
    par, x = synthetic_key
    sig = _sign(par, x, secrets.randbelow(par.q - 1) + 1, b"hello")
    assert verify(par, sig) is True


def test_nonce_reuse_recovers_private_key(synthetic_key):
    """Positive control - proves the detector is not vacuously passing."""
    import secrets
    par, x = synthetic_key
    k = secrets.randbelow(par.q - 1) + 1
    a = _sign(par, x, k, b"first message")
    b = _sign(par, x, k, b"second message")
    assert a.r == b.r
    assert recover_x_from_shared_nonce(par, a, b) == x
    f = analyse_nonces(par, [a, b])
    assert len(f.repeated_r) == 1
    assert f.recovered_private_key == x


def test_verify_rejects_out_of_range(synthetic_key):
    par, _ = synthetic_key
    bad = DSASignature(r=0, s=1, digest=hashlib.sha1(b"x").digest())
    assert verify(par, bad) is False
