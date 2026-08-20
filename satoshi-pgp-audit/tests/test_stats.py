"""Calibration of the randomness battery: it must pass good input and fail bad."""
import os

from spa.analysis.stats import (ALPHA, battery_summary, byte_chi_square,
                                full_battery, igamc, monobit)


def test_igamc_boundaries():
    assert igamc(1.0, 0.0) == 1.0
    assert 0.0 <= igamc(10.0, 5.0) <= 1.0


def test_battery_passes_good_randomness():
    results = full_battery(os.urandom(65536))
    summary = battery_summary(results)
    # Each test has a 1% false-positive rate at alpha=0.01; allow one.
    assert summary["failed"] <= 1, [str(r) for r in results]


def test_battery_detects_a_stuck_high_bit():
    """Every byte masked to 7 bits - a bias no real generator would show."""
    biased = bytes(b & 0x7F for b in os.urandom(65536))
    summary = battery_summary(full_battery(biased))
    assert summary["failed"] >= 5


def test_battery_detects_constant_output():
    results = full_battery(b"\xaa" * 65536)
    assert battery_summary(results)["failed"] >= 3


def test_small_inputs_are_skipped_not_guessed():
    """Three DSA signatures are ~120 bytes. The battery must decline to opine."""
    results = full_battery(os.urandom(120))
    assert battery_summary(results)["skipped"] >= 1
    assert byte_chi_square(os.urandom(120)).p_value is None


def test_monobit_on_all_ones():
    r = monobit(b"\xff" * 1000)
    assert r.passed is False and r.p_value < ALPHA
