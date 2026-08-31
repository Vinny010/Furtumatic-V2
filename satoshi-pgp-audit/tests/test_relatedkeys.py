"""Related-key scanner: positive controls, negative controls, and the maths.

A scanner that reports "nothing found" is worthless unless it has been shown to
find something. Every test here either plants a relation and demands it be found,
or plants nothing and demands silence.
"""

import secrets

import pytest

from spa.analysis import bitcoin_scope as bs
from spa.analysis.relatedkeys import (KeyRecord, batch_invert, is_on_curve,
                                      parse_uncompressed, scan, with_control)


def _rec(label, d):
    return KeyRecord(label=label, point=bs.point_mul(d))


# ---------------------------------------------------------------- primitives
def test_batch_invert_matches_individual_inversion():
    vals = [secrets.randbelow(bs.P - 1) + 1 for _ in range(64)]
    got = batch_invert(vals)
    for v, g in zip(vals, got):
        assert v * g % bs.P == 1


def test_batch_invert_empty():
    assert batch_invert([]) == []


def test_on_curve_accepts_generator_and_rejects_junk():
    assert is_on_curve((bs.GX, bs.GY))
    assert not is_on_curve((bs.GX, bs.GY + 1))


def test_parse_uncompressed():
    x, y = bs.GX, bs.GY
    h = "04" + "%064x" % x + "%064x" % y
    assert parse_uncompressed(h) == (x, y)
    assert parse_uncompressed("") is None
    assert parse_uncompressed("02" + "%064x" % x) is None      # compressed
    assert parse_uncompressed("04ff") is None                  # too short


# ---------------------------------------------------------------- detection
def test_finds_a_planted_sequential_pair():
    """The core capability: d and d+1 must be caught."""
    d = secrets.randbelow(bs.N - 10) + 1
    records = [_rec("a", d), _rec("b", d + 1), _rec("c", secrets.randbelow(bs.N - 1) + 1)]
    f = scan(records, max_delta=4)
    pairs = {(min(a, b), max(a, b), delta) for a, b, delta in f.related_pairs}
    assert ("a", "b", 1) in pairs


@pytest.mark.parametrize("delta", [1, 2, 7, 31, 64])
def test_finds_relations_at_various_offsets(delta):
    d = secrets.randbelow(bs.N - 1000) + 1
    records = [_rec("lo", d), _rec("hi", d + delta)]
    f = scan(records, max_delta=64)
    assert any(dd == delta for _, _, dd in f.related_pairs)


def test_detects_duplicate_keys():
    d = secrets.randbelow(bs.N - 1) + 1
    f = scan([_rec("one", d), _rec("two", d)], max_delta=2)
    assert len(f.duplicate_keys) == 1


def test_negative_control_random_keys_yield_nothing():
    """Independent random keys must produce no relations. If this ever fires,
    the scanner has a false-positive path and every negative result is suspect."""
    records = [_rec("k%d" % i, secrets.randbelow(bs.N - 1) + 1) for i in range(60)]
    f = scan(records, max_delta=64)
    assert f.related_pairs == []
    assert f.duplicate_keys == []
    assert f.clean is True


def test_relation_beyond_range_is_not_found():
    """Bounded search must stay bounded - no wrap-around false positives."""
    d = secrets.randbelow(bs.N - 10000) + 1
    f = scan([_rec("a", d), _rec("b", d + 500)], max_delta=16)
    assert f.related_pairs == []


def test_off_curve_entries_are_reported_not_crashed_on():
    bad = KeyRecord(label="bad", point=(bs.GX, bs.GY + 1))
    f = scan([bad, _rec("ok", 12345)], max_delta=4)
    assert f.off_curve == ["bad"]


# ---------------------------------------------------------------- control wiring
def test_with_control_injects_a_findable_pair():
    records = [_rec("k%d" % i, secrets.randbelow(bs.N - 1) + 1) for i in range(20)]
    augmented, labels = with_control(records, delta=7)
    assert len(augmented) == len(records) + 2
    f = scan(augmented, max_delta=16, control_labels=labels)
    assert f.control_detected is True
    # The control must be excluded from the corpus verdict.
    assert f.related_pairs == []
    assert f.clean is True


def test_control_excluded_from_verdict_but_real_hit_survives():
    """A genuine relation must still be reported alongside a passing control."""
    d = secrets.randbelow(bs.N - 1000) + 1
    records = [_rec("real-a", d), _rec("real-b", d + 3)]
    augmented, labels = with_control(records, delta=7)
    f = scan(augmented, max_delta=16, control_labels=labels)
    assert f.control_detected is True
    assert len(f.related_pairs) >= 1
    assert all(set(p[:2]) != set(labels) for p in f.related_pairs)
    assert f.clean is False


def test_failed_control_invalidates_the_result():
    """If the control is not found, the scan must say so rather than report clean."""
    records = [_rec("k%d" % i, secrets.randbelow(bs.N - 1) + 1) for i in range(10)]
    augmented, labels = with_control(records, delta=100)
    f = scan(augmented, max_delta=4, control_labels=labels)   # too small to find it
    assert f.control_detected is False
    assert any("CONTROL NOT DETECTED" in n for n in f.notes)
