"""Kangaroo coordination features: sharding, benchmark, solution verification."""
import secrets

import pytest

from spa.analysis import bitcoin_scope as bs
from spa.lab.kangaroo import benchmark, shard_bounds, verify_solution


def test_shards_are_disjoint_and_cover_the_range():
    a, b = 1 << 40, 1 << 41
    n = 37
    bounds = [shard_bounds(a, b, n, i) for i in range(n)]
    # contiguous, non-overlapping, and covering exactly [a, b)
    assert bounds[0][0] == a
    assert bounds[-1][1] == b
    for i in range(1, n):
        assert bounds[i][0] == bounds[i - 1][1]   # no gap, no overlap


def test_every_key_lands_in_exactly_one_shard():
    a, b = 1 << 20, 1 << 21
    n = 50
    bounds = [shard_bounds(a, b, n, i) for i in range(n)]
    for _ in range(200):
        k = secrets.randbelow(b - a) + a
        hits = [1 for lo, hi in bounds if lo <= k < hi]
        assert sum(hits) == 1


def test_shard_id_out_of_range_rejected():
    with pytest.raises(ValueError):
        shard_bounds(0, 100, 10, 10)


def test_verify_accepts_correct_key_and_rejects_wrong():
    x = secrets.randbelow(bs.N - 1) + 1
    P = bs.point_mul(x)
    good = verify_solution(P, x)
    assert good["verified"] is True
    bad = verify_solution(P, x + 1)
    assert bad["verified"] is False


def test_verify_checks_address_when_given():
    x = secrets.randbelow(bs.N - 1) + 1
    P = bs.point_mul(x)
    addr = bs.pubkey_to_address(P, False)
    out = verify_solution(P, x, expected_address=addr)
    assert out["address_matches"] is True and out["verified"] is True
    out2 = verify_solution(P, x, expected_address="1WrongAddressXXXXXXXXXXXXXXXXXXXXX")
    assert out2["address_matches"] is False


def test_benchmark_returns_positive_rate():
    assert benchmark(seconds=0.2) > 0
