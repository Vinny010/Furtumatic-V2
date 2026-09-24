"""The username-reconstruction hypothesis, tested rather than dismissed."""
import pytest

from spa.lab.reconstruct import run_experiment, search_space


def test_search_space_is_astronomical():
    s = search_space()
    assert s["private_key_bits"] == 160
    assert s["candidates"] == 1 << 160
    assert float(s["years_at_that_rate"]) > 1e20


def test_fixed_username_does_not_fix_the_key(gpg147):
    """The decisive experiment: identical User ID, entirely different keys.

    Enough keys are generated that several land in the same creation second, so
    the stronger claim - that User ID PLUS timestamp determines the key - is
    tested too, not just the weak one.
    """
    res = run_experiment(gpg147, count=14)
    assert res.keys_generated >= 10
    assert res.distinct_fingerprints == res.keys_generated
    assert res.uid_determines_key is False
    # Domain parameters are regenerated per key as well.
    assert res.distinct_p == res.keys_generated
    assert res.distinct_q == res.keys_generated


def test_same_username_and_same_second_still_differ(gpg147):
    res = run_experiment(gpg147, count=14)
    if not res.timestamp_collisions:
        pytest.skip("no two keys landed in the same second on this host")
    assert res.uid_and_time_determine_key is False
    for _ts, count, distinct in res.timestamp_collisions:
        assert distinct == count, "keys sharing UID and creation second collided"
