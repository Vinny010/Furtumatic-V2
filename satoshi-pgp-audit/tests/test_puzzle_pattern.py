"""Hot-zone detector: uniform solved keys => no bias; a planted cluster => flagged."""
import os

import pytest

from spa.analysis.puzzle_pattern import (analyse, load_solved, position)

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA = os.path.join(ROOT, "data", "puzzle_solved.json")


def test_position_normalises_to_unit_interval():
    assert position(8, 128) == 0.0          # bottom of #8 range (2^7)
    assert position(8, 255) == pytest.approx(0.9922, abs=1e-3)  # near top
    assert 0.0 <= position(72, (1 << 71) + 5) < 1.0


def test_position_rejects_key_outside_its_range():
    with pytest.raises(ValueError):
        position(8, 300)                     # 300 >= 2^8, not in #8 range


def test_uniform_positions_are_not_flagged():
    # 100 keys spread evenly across each range -> chi2 small -> no hot zone.
    solved = {}
    for i in range(100):
        n = 20 + i
        lo = 1 << (n - 1)
        solved[n] = lo + int((i / 100.0) * lo)   # position marches 0..1 evenly
    f = analyse(solved)
    assert f.biased is False
    assert f.hot_zone is None


def test_planted_cluster_is_detected():
    # All keys jammed into the bottom 10% of their ranges -> strong bias.
    solved = {}
    for i in range(100):
        n = 20 + i
        lo = 1 << (n - 1)
        solved[n] = lo + int(0.02 * lo)          # every key at position ~0.02
    f = analyse(solved)
    assert f.biased is True
    assert f.hot_zone == (0.0, 0.1)              # detector points at the real band


def test_small_sample_warns_about_low_power():
    f = analyse({1: 1, 2: 3, 3: 7})
    assert any("too few" in n for n in f.notes)


def test_shipped_data_keys_all_lie_in_range():
    solved = load_solved(DATA)
    for n, k in solved.items():
        assert (1 << (n - 1)) <= k < (1 << n), "puzzle #%d key out of range" % n
    # And the analyser runs on it without raising.
    f = analyse(solved)
    assert f.n == len(solved)
