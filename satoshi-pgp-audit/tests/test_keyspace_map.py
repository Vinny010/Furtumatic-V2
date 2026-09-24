"""Keyspace distribution: healthy RNG is uniform and era-independent;
only broken seeding leaves detectable structure."""

from spa.lab.keyspace_map import era_is_irrelevant_for_healthy, profile_models


def test_healthy_is_uniform_full_range_no_collisions():
    p = profile_models(count=20000)["healthy (well-seeded, any era)"]
    assert p.collisions == 0
    assert p.uniform_full_range is True
    assert p.buckets_occupied > 250          # ~all 256 top-bit buckets occupied


def test_old_vs_new_healthy_is_not_a_real_axis():
    """Two independent well-seeded generators are statistically indistinguishable."""
    assert era_is_irrelevant_for_healthy(count=20000) is True


def test_whitened_weak_collides_but_stays_scattered():
    """Low entropy + hashing = few distinct values, but NOT a contiguous region."""
    p = profile_models(count=50000, weak_bits=16)["whitened-weak (Debian shape)"]
    assert p.collisions > 0                   # birthday collisions from a 2^16 seed
    assert p.buckets_occupied > 250           # still scattered across the whole space


def test_raw_band_is_the_only_region_case():
    """A naive counter/timestamp key (no whitening) is the only model that lands in
    a contiguous keyspace region - and it needs no hashing at all."""
    p = profile_models(count=20000, band_bits=40)["raw-band (naive counter/time)"]
    assert p.buckets_occupied == 1
    assert p.fraction_in_bottom_256th == 1.0


def test_determinism():
    a = profile_models(count=5000, seed=7)["healthy (well-seeded, any era)"]
    b = profile_models(count=5000, seed=7)["healthy (well-seeded, any era)"]
    assert a.distinct == b.distinct and a.buckets_occupied == b.buckets_occupied
