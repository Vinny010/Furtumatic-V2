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


def test_keyring_check_over_transcribed_vertisan_ring():
    """The three keys whose algorithm was actually observed are all provably
    backdated; the rest are honestly UNVERIFIED, never falsely flagged."""
    import json
    from pathlib import Path
    from spa.analysis.anachronism import check_keyring
    path = Path(__file__).resolve().parents[1] / "data" / "vertisan_keyring.json"
    entries = json.loads(path.read_text())["entries"]
    verdicts = check_keyring(entries)
    backdated = [v for v in verdicts if v.verdict == "BACKDATED"]
    unverified = [v for v in verdicts if v.verdict == "UNVERIFIED"]
    # EdDSA primary, ECDH subkey, EdDSA "BitCoin Email" - all impossible in 2008.
    assert len(backdated) == 3
    assert {v.key_id for v in backdated} == {
        "7EEDA8009DFEF627", "2D49A7A3753FE656", "4444921F9B0D536B"}
    # Entries with no observed algorithm must not be flagged.
    assert len(unverified) == 5
    assert all(not v.algo_known for v in unverified)


def test_keyring_never_flags_unknown_algorithm():
    from spa.analysis.anachronism import check_keyring
    v = check_keyring([{"label": "x", "claimed_created_year": 2008,
                        "pubkey_algo": None}])
    assert v[0].verdict == "UNVERIFIED"
