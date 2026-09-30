"""Differential test: the Python model vs the genuine GnuPG C implementation.

This is the test that licenses every other claim in the project. If the model and
the historical C code ever diverge, no conclusion drawn from the model stands.
"""
import os
from pathlib import Path

import pytest

from spa.lab.cbridge.build import build, generate_source, run_mix
from spa.lab.cbridge.extract import ExtractionError, extract_function
from spa.lab.gnupg_rng import BLOCKLEN, POOLSIZE, mix_pool_147, mix_pool_1421


@pytest.fixture(scope="module")
def binary_147(gnupg_src, tmp_path_factory):
    return build(gnupg_src, tmp_path_factory.mktemp("c147") / "mix147")


@pytest.fixture(scope="module")
def binary_1421(gnupg_src_1421, tmp_path_factory):
    return build(gnupg_src_1421, tmp_path_factory.mktemp("c1421") / "mix1421")


def _compare(binary, mixer, rounds, trials=5):
    for _ in range(trials):
        pool = os.urandom(POOLSIZE)
        c_out = run_mix(binary, pool, rounds)
        py = bytearray(pool + bytes(BLOCKLEN))
        for _ in range(rounds):
            mixer(py)
        assert bytes(py[:POOLSIZE]) == c_out


def test_python_matches_real_c_147_single_round(binary_147):
    _compare(binary_147, mix_pool_147, rounds=1)


def test_python_matches_real_c_147_many_rounds(binary_147):
    """Divergence would compound across rounds, so this is the stronger check."""
    _compare(binary_147, mix_pool_147, rounds=10, trials=3)


def test_python_matches_real_c_1421(binary_1421):
    _compare(binary_1421, mix_pool_1421, rounds=5, trials=3)


def test_the_two_c_implementations_actually_differ(binary_147, binary_1421):
    """Guards against both binaries accidentally being the same build."""
    pool = os.urandom(POOLSIZE)
    assert run_mix(binary_147, pool, 1) != run_mix(binary_1421, pool, 1)


def test_all_zero_pool_edge_case(binary_147):
    """A degenerate pool still has to agree exactly."""
    c_out = run_mix(binary_147, b"\x00" * POOLSIZE, 1)
    py = bytearray(b"\x00" * POOLSIZE + bytes(BLOCKLEN))
    mix_pool_147(py)
    assert bytes(py[:POOLSIZE]) == c_out


def test_extracted_source_is_from_upstream(gnupg_src):
    """The C under test must be lifted from the pinned tree, not hand-copied."""
    src = generate_source(gnupg_src)
    assert "mix_pool" in src and "rmd160_mixblock" in src
    # The 1.4.7 signature of the defect: the tail read skips DIGESTLEN bytes.
    assert "memcpy(hashbuf+DIGESTLEN, p+DIGESTLEN, BLOCKLEN-DIGESTLEN);" in src


def test_extractor_reports_missing_functions(gnupg_src):
    text = (gnupg_src / "cipher" / "random.c").read_text(errors="replace")
    with pytest.raises(ExtractionError):
        extract_function(text, "no_such_function_anywhere")
