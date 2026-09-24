"""Pollard Kangaroo interval solver: it must actually recover planted keys."""
import secrets

from spa.analysis import bitcoin_scope as bs
from spa.lab.kangaroo import demo, solve_interval


def test_solves_small_interval():
    r = demo(bits=20, seed=1)
    assert r.solved is True


def test_recovers_exact_key_in_range():
    a, b = 1 << 19, 1 << 20
    x = secrets.randbelow(b - a) + a
    Q = bs.point_mul(x)
    r = solve_interval(Q, a, b)
    assert r.solved and r.private_key == x


def test_operations_near_sqrt_bound():
    """Work should be O(sqrt(W)), not O(W) - the whole point of kangaroo."""
    a, b = 1 << 23, 1 << 24
    x = secrets.randbelow(b - a) + a
    r = solve_interval(bs.point_mul(x), a, b)
    assert r.solved
    # W = 2^23; a sqrt-time solve must finish far below that.
    assert r.operations < (1 << 17)


def test_reports_failure_cleanly_when_capped():
    a, b = 1 << 23, 1 << 24
    x = secrets.randbelow(b - a) + a
    r = solve_interval(bs.point_mul(x), a, b, max_ops=50)
    assert r.solved is False
    assert r.notes
