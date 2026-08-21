"""Network-scale PGP nonce-reuse scanner: controls and real-corpus behaviour."""

from pathlib import Path

import pytest

from spa.analysis.pgpscan import (make_synthetic_control, scan_armored_texts,
                                  scan_records)

ROOT = Path(__file__).resolve().parents[1]
KEY = ROOT / "data" / "keys" / "satoshi_5EC948A1.asc"


def test_positive_control_detects_and_recovers():
    recs, par, keyid, true_x = make_synthetic_control(reuse=True)
    f = scan_records(recs, owned_keyids={keyid}, params_by_keyid={keyid: par})
    assert len(f.vulnerable_keys) == 1
    assert f.vulnerable_keys[0].recovered_private_key == true_x


def test_negative_control_stays_clean():
    recs, _par, _keyid, _x = make_synthetic_control(reuse=False)
    f = scan_records(recs)
    assert f.clean
    assert f.vulnerable_keys == []


def test_recovery_withheld_for_unowned_keys():
    """A vulnerable third-party key must be FLAGGED but not have its key computed."""
    recs, par, keyid, _x = make_synthetic_control(reuse=True)
    f = scan_records(recs, owned_keyids=set(), params_by_keyid={keyid: par})
    assert len(f.vulnerable_keys) == 1
    assert f.vulnerable_keys[0].recovered_private_key is None
    assert f.vulnerable_keys[0].owned is False


def test_duplicate_signature_is_not_flagged_as_reuse():
    """Same r AND same s is one signature twice - harmless, must not be a finding."""
    recs, _par, keyid, _x = make_synthetic_control(reuse=True)
    dup = recs[0]
    f = scan_records([dup, dup])
    assert f.clean
    assert f.duplicate_signatures == 1


@pytest.mark.skipif(not KEY.exists(), reason="pinned key absent")
def test_satoshi_keyblock_has_no_nonce_reuse():
    text = KEY.read_text(errors="replace")
    f = scan_armored_texts([("satoshi", text)])
    # The keyblock carries many third-party DSA signatures; scan them all.
    assert f.signatures_scanned > 0
    assert f.issuers_seen > 1
    assert f.vulnerable_keys == []
    # The known duplicate subkey-binding signature is a duplicate, not reuse.
    assert f.duplicate_signatures >= 1
