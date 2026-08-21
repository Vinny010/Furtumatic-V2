"""Backdating detection via algorithm/creation-date anachronism."""

from spa.analysis.anachronism import KeyClaim, check_claim


def test_ed25519_key_claiming_2008_is_flagged():
    """The decisive case: EdDSA (algo 22) could not exist in 2008."""
    f = check_claim(KeyClaim(label="fake", claimed_created_year=2008, pubkey_algo=22))
    assert f.backdated is True
    assert any(a.kind == "pubkey-algo" for a in f.anachronisms)
    assert any("BACKDATED" in n for n in f.notes)


def test_real_dsa_key_is_not_flagged():
    """DSA in 2008 is entirely period-correct."""
    f = check_claim(KeyClaim(label="real", claimed_created_year=2008,
                             pubkey_algo=17, hash_algos=[2]))
    assert f.backdated is False


def test_modern_eddsa_key_is_not_flagged():
    f = check_claim(KeyClaim(label="james", claimed_created_year=2024, pubkey_algo=22))
    assert f.backdated is False


def test_ecdsa_before_2012_is_flagged():
    f = check_claim(KeyClaim(label="x", claimed_created_year=2009, pubkey_algo=19))
    assert f.backdated is True


def test_sha256_selfsig_before_2004_is_flagged():
    f = check_claim(KeyClaim(label="x", claimed_created_year=2000,
                             pubkey_algo=17, hash_algos=[8]))
    assert f.backdated is True
    assert any(a.kind == "hash-algo" for a in f.anachronisms)


def test_years_early_is_reported():
    f = check_claim(KeyClaim(label="x", claimed_created_year=2008, pubkey_algo=22))
    assert f.anachronisms[0].years_early == 6


def test_clean_key_note_disclaims_identity():
    """A non-anachronistic date must NOT be presented as confirming anything."""
    f = check_claim(KeyClaim(label="x", claimed_created_year=2008, pubkey_algo=17))
    assert any("necessary, NOT sufficient" in n for n in f.notes)
    assert any("identity" in n.lower() for n in f.notes)
