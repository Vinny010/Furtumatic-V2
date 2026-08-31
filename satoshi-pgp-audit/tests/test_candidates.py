"""Candidate derivation: every candidate must be motivated, valid and reproducible."""

import hashlib

from spa.analysis import bitcoin_scope as bs
from spa.analysis.candidates import derive_candidates


def test_candidates_are_derived_from_the_real_key(keyblock):
    cands = derive_candidates(keyblock, keyblock.self_signatures())
    assert len(cands) >= 20


def test_every_candidate_states_a_rationale(keyblock):
    """A derivation without a reason is a random number, not a candidate. This
    discipline is what stops the set becoming a disguised blind search."""
    for c in derive_candidates(keyblock, keyblock.self_signatures()):
        assert c.rationale.strip(), c.label
        assert len(c.rationale) > 15


def test_every_candidate_is_a_valid_secp256k1_key(keyblock):
    for c in derive_candidates(keyblock, keyblock.self_signatures()):
        assert 0 < c.private_key < bs.N, c.label


def test_both_address_encodings_present(keyblock):
    for c in derive_candidates(keyblock, keyblock.self_signatures()):
        assert set(c.addresses) == {"uncompressed", "compressed"}
        for addr in c.addresses.values():
            assert addr.startswith("1")
            assert 26 <= len(addr) <= 35


def test_candidates_are_deduplicated(keyblock):
    cands = derive_candidates(keyblock, keyblock.self_signatures())
    keys = [c.private_key for c in cands]
    assert len(keys) == len(set(keys))


def test_derivation_is_deterministic(keyblock):
    """The same key must always yield the same address list, or the negative
    result would not be reproducible by anyone else."""
    a = derive_candidates(keyblock, keyblock.self_signatures())
    b = derive_candidates(keyblock, keyblock.self_signatures())
    assert [c.addresses for c in a] == [c.addresses for c in b]


def test_brainwallet_derivation_matches_the_standard_construction(keyblock):
    """Spot-check one candidate against the construction it claims to implement:
    a brainwallet is literally SHA-256 of the passphrase."""
    cands = {c.label: c for c in derive_candidates(keyblock, keyblock.self_signatures())}
    uid = keyblock.uids[0].text
    expected = int.from_bytes(hashlib.sha256(uid.encode()).digest(), "big") % bs.N
    assert cands["brainwallet:uid"].private_key == expected


def test_fingerprint_candidate_matches_the_fingerprint(keyblock):
    cands = {c.label: c for c in derive_candidates(keyblock, keyblock.self_signatures())}
    expected = int.from_bytes(bytes.fromhex(keyblock.fingerprint), "big")
    assert cands["fingerprint:zero-extended"].private_key == expected
