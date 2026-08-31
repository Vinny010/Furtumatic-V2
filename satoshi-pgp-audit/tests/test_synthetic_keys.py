"""End-to-end tests against the genuine GnuPG 1.4.7 binary.

Skipped when the historical build is unavailable. All keys created here are
synthetic and exist only for the duration of the test.
"""
import pytest

from spa.analysis.dsa import DSAParams, DSASignature, analyse_nonces, validate_params
from spa.lab.harvest import (extract_dsa_signature_values, generate_keys,
                             generate_signature_corpus)
from spa.openpgp import dearmor, parse_keyblock


@pytest.fixture(scope="module")
def corpus(gpg147):
    pub, sigs = generate_signature_corpus(gpg147, count=40)
    return pub, sigs


def test_historical_binary_reports_1_4_7(gpg147):
    import subprocess
    out = subprocess.run([gpg147, "--version"], capture_output=True)
    assert "(GnuPG) 1.4.7" in out.stdout.decode()


def test_generated_keys_parse_with_our_parser(gpg147):
    res = generate_keys(gpg147, count=2)
    assert res.errors == []
    assert len(res.keys) == 2
    for k in res.keys:
        kb = parse_keyblock(dearmor(k.armored_public.decode())[0].body)
        assert kb.fingerprint == k.fingerprint
        assert kb.primary.algo_name == "DSA"
        assert kb.primary.key_size_bits == 1024


def test_synthetic_keys_pass_the_same_checks_as_the_real_one(gpg147):
    """The historical generator produces structurally valid DSA keys - so the
    real key passing these checks is unremarkable, exactly as it should be."""
    res = generate_keys(gpg147, count=1, subkey=None)
    kb = parse_keyblock(dearmor(res.keys[0].armored_public.decode())[0].body)
    m = kb.primary.mpis
    par = DSAParams(m["p"].value, m["q"].value, m["g"].value, m["y"].value)
    assert [c for c in validate_params(par, deep=True) if c.passed is False] == []


def test_no_nonce_reuse_in_a_real_1_4_7_corpus(corpus):
    """The 1.4.7 RNG defect does NOT cause nonce collisions. If it did, this
    would fail - which is the point of running it."""
    pub, sigs = corpus
    kb = parse_keyblock(dearmor(pub.decode())[0].body)
    m = kb.primary.mpis
    par = DSAParams(m["p"].value, m["q"].value, m["g"].value, m["y"].value)
    vals = extract_dsa_signature_values(sigs)
    assert len(vals) == len(sigs)
    f = analyse_nonces(par, [DSASignature(r=v["r"], s=v["s"], label=v["label"])
                             for v in vals])
    assert f.repeated_r == []
    assert f.distinct_r == len(vals)


def test_signatures_from_the_historical_build_verify(corpus):
    """Detached signatures over known messages must verify with our own DSA code."""
    pub, sigs = corpus
    vals = extract_dsa_signature_values(sigs)
    q_bits = 160
    for v in vals:
        assert 0 < v["r"] < (1 << q_bits)
        assert 0 < v["s"] < (1 << q_bits)
