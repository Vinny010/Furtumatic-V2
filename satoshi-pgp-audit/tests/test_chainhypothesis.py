"""Deterministic key-chain detector: controls and negative behaviour."""

import secrets

from spa.analysis import bitcoin_scope as bs
from spa.analysis.chainhypothesis import make_control_chain
from spa.analysis.chainhypothesis import test_chain as run_chain_test


def test_positive_control_hash_chain_is_detected():
    """A planted SHA256(prev_pub) chain must be found - else the negative on real
    data means nothing."""
    chain = make_control_chain(length=30)
    f = run_chain_test(chain, sample=29)
    held = [r for r in f.results if r.holds]
    assert f.any_chain_holds is True
    assert any("SHA256(prev_pub_compressed)" in r.name for r in held)


def test_independent_random_keys_show_no_chain():
    """The negative control: unrelated keys must trigger no rule."""
    pts = [bs.point_mul(secrets.randbelow(bs.N - 1) + 1) for _ in range(60)]
    f = run_chain_test(pts, sample=59)
    assert f.any_chain_holds is False


def test_multiplicative_chain_is_detected():
    """next_pub = 3 * prev_pub must be caught by the multiplicative family."""
    d0 = secrets.randbelow(bs.N - 1) + 1
    priv = d0
    pts = []
    for _ in range(20):
        pts.append(bs.point_mul(priv))
        priv = (priv * 3) % bs.N
    f = run_chain_test(pts, sample=19, multiplicative_scalars=[3])
    assert any(r.holds and "3 * prev_pub" in r.name for r in f.results)


def test_a_single_broken_link_prevents_a_hold():
    """A rule holds only if EVERY sampled pair matches - one break disqualifies it."""
    chain = make_control_chain(length=30)
    # Corrupt one key in the middle.
    chain[15] = bs.point_mul(secrets.randbelow(bs.N - 1) + 1)
    f = run_chain_test(chain, sample=29)
    assert f.any_chain_holds is False


def test_short_input_is_handled():
    f = run_chain_test([bs.point_mul(1)], sample=10)
    assert f.any_chain_holds is False
