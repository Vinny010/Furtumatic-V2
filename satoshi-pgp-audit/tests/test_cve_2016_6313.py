"""CVE-2016-6313: the defect must reproduce on 1.4.7 and be absent from 1.4.21."""
import os

import pytest

from spa.lab import cve_2016_6313 as cve
from spa.lab.gnupg_rng import (BLOCKLEN, POOLSIZE, GnuPGRandom, fresh,
                               mix_pool_147, mix_pool_1421)


def test_predictor_always_succeeds_on_1_4_7():
    """Deterministic identity, not a statistical tendency: expected rate is 1.0."""
    r = cve.reproduce("1.4.7", trials=100)
    assert r.successes == 100
    assert r.reproduced is True


def test_predictor_never_succeeds_on_1_4_21():
    """Negative control - proves the predictor tests the defect, not the harness."""
    r = cve.reproduce("1.4.21", trials=100)
    assert r.successes == 0


def test_defect_survives_the_full_read_pool_path():
    """The weakness must be visible in real generator output, not just mix_pool."""
    r = cve.reproduce_through_read_pool(trials=10)
    assert r.successes == 10


def test_predicted_quantities_match_the_advisory():
    assert cve.PREDICTED_BITS == 160
    assert cve.REQUIRED_PRIOR_BITS == 4640
    assert cve.REQUIRED_PRIOR_BITS // 8 == 580
    assert 580 + 20 == POOLSIZE // 1 - 0  # 600-byte pool: 580 known + 20 predicted


def test_prediction_needs_only_public_bytes():
    pool = bytearray(os.urandom(POOLSIZE) + bytes(BLOCKLEN))
    mix_pool_147(pool)
    mixed = bytes(pool[:POOLSIZE])
    # Deliberately pass ONLY the first 580 bytes.
    assert cve.predict_final_block(mixed[:580]) == mixed[580:600]


def test_predict_rejects_short_input():
    with pytest.raises(ValueError):
        cve.predict_final_block(b"\x00" * 100)


# ---- prerequisite accounting ----
def test_public_key_yields_zero_raw_rng_bytes():
    b = cve.observable_rng_budget(signature_count=3)
    assert b.total_raw_bytes == 0
    assert b.shortfall == 580
    assert b.sufficient is False


def test_more_signatures_do_not_help():
    """The shortfall is categorical: public signatures contain no raw RNG output."""
    few = cve.observable_rng_budget(signature_count=3)
    many = cve.observable_rng_budget(signature_count=100000)
    assert few.total_raw_bytes == many.total_raw_bytes == 0


def test_secret_key_would_expose_some_but_not_enough():
    """Even a leaked secret key packet supplies only salt+IV - far below 580."""
    b = cve.observable_rng_budget(signature_count=3, has_secret_key=True)
    assert 0 < b.total_raw_bytes < 580
    assert b.sufficient is False


def test_no_prerequisite_is_met_by_public_material():
    a = cve.assess_applicability()
    assert a["software_is_affected"] is True
    assert a["defect_is_real_and_reproduced"] is True
    assert a["prerequisites_satisfied"] is False


# ---- pool model behaviour ----
def test_pool_is_deterministic_given_a_seed():
    a = fresh("1.4.7", seed=b"A" * 64).get_random_bytes(600)
    b = fresh("1.4.7", seed=b"A" * 64).get_random_bytes(600)
    assert a == b


def test_variants_produce_different_output():
    a = fresh("1.4.7", seed=b"A" * 64).get_random_bytes(600)
    b = fresh("1.4.21", seed=b"A" * 64).get_random_bytes(600)
    assert a != b


def test_word_size_changes_output():
    """MingW32 (4-byte ulong) and 64-bit Unix (8-byte) diverge - the historical
    target build matters for any faithful reproduction."""
    a = fresh("1.4.7", seed=b"A" * 64, word_size=4).get_random_bytes(600)
    b = fresh("1.4.7", seed=b"A" * 64, word_size=8).get_random_bytes(600)
    assert a != b


def test_unseeded_pool_refuses_to_emit():
    g = GnuPGRandom(variant="1.4.7")
    with pytest.raises(RuntimeError):
        g.read_pool(16)


def test_mix_pool_is_not_identity():
    pool = bytearray(os.urandom(POOLSIZE) + bytes(BLOCKLEN))
    before = bytes(pool[:POOLSIZE])
    mix_pool_147(pool)
    assert bytes(pool[:POOLSIZE]) != before


def test_version_comparison_is_numeric_not_lexical():
    """Regression guard: '1.4.7' < '1.4.21' is False as strings but True as
    versions. Getting this wrong reports the vulnerable release as safe."""
    from spa.lab.cve_2016_6313 import _version_lt
    assert _version_lt("1.4.7", "1.4.21") is True
    assert _version_lt("1.4.21", "1.4.21") is False
    assert _version_lt("1.4.22", "1.4.21") is False
    assert _version_lt("1.4.6", "1.4.21") is True
    assert cve.assess_applicability("1.4.7")["software_is_affected"] is True
    assert cve.assess_applicability("1.4.21")["software_is_affected"] is False
    assert cve.assess_applicability("1.4.23")["software_is_affected"] is False
