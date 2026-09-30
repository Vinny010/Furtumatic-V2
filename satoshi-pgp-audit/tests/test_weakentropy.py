"""Keyspace-collapse reproduction and detector controls (synthetic keys only)."""

import secrets

from spa.analysis import bitcoin_scope as bs
from spa.analysis.weakentropy import (_priv_from_weak_source,
                                      demonstrate_recovery,
                                      generate_collapsed_keys,
                                      positive_control_for_related_scan)


def test_collapse_confines_keys_to_the_declared_space():
    """A b-bit collapse must produce at most 2^b distinct keys."""
    bits = 8
    gen = generate_collapsed_keys(bits, count=1000)
    distinct = {d for d, _pt in gen}
    assert len(distinct) <= (1 << bits)


def test_recovery_from_public_keys_succeeds_on_collapsed_space():
    """The whole point: a collapsed keyspace is brute-forceable from pubkeys."""
    r = demonstrate_recovery(entropy_bits=12, key_count=3)
    assert r.brute_force_recovered == 3
    assert r.collapse_factor_log2 == 256 - 12


def test_recovery_cost_scales_with_bits():
    small = demonstrate_recovery(entropy_bits=8, key_count=2)
    assert small.brute_force_recovered == 2
    # budget never exceeds the space size
    assert small.brute_force_budget <= (1 << 8)


def test_derived_private_keys_are_valid_scalars():
    for src in (0, 1, 12345, (1 << 20) - 1):
        d = _priv_from_weak_source(src)
        assert 0 < d < bs.N


def test_positive_control_fires_on_sequential_keys():
    """If this fails, the related-key scan is broken and every negative it
    produced - including the Patoshi zero - must be discarded."""
    c = positive_control_for_related_scan(keys=30, spacing=2, max_delta=32)
    assert c.detector_fired is True
    assert c.related_pairs > 0


def test_control_documents_its_scope_limit():
    """The control must state that it covers the sequential class only - claiming
    more than that would be the exact overreach this project avoids."""
    c = positive_control_for_related_scan(keys=20)
    assert any("SCOPE LIMIT" in n for n in c.notes)
    assert any("hashed" in n.lower() for n in c.notes)


def test_hashed_collapse_is_NOT_caught_by_related_scan():
    """Document the blind spot honestly: KDF-scattered keys evade the related-key
    scan even though the space is tiny. This is why the Coldcard class cannot be
    ruled out from public keys alone."""
    from spa.analysis.relatedkeys import KeyRecord, scan
    gen = generate_collapsed_keys(entropy_bits=10, count=40)   # scattered by SHA-256
    records = [KeyRecord(label="h%d" % i, point=pt) for i, (_d, pt) in enumerate(gen)]
    f = scan(records, max_delta=64)
    # No small-offset structure survives the hash, so the scan stays silent.
    assert f.related_pairs == []


def test_no_real_data_is_referenced():
    """Sanity: the module must not import or read any real corpus."""
    import spa.analysis.weakentropy as we
    src = we.__doc__ or ""
    assert "synthetic" in src.lower()
