"""Address-based range brute force: recovers keys from the hash alone (no pubkey)."""
import hashlib
import secrets

from spa.analysis import bitcoin_scope as bs
from spa.lab.bruteforce import demo, scan_range


def _h160(point, compressed=True):
    x, y = point
    ser = (bytes([2 + (y & 1)]) + x.to_bytes(32, "big")) if compressed \
        else b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")
    return hashlib.new("ripemd160", hashlib.sha256(ser).digest()).digest()


def test_finds_key_from_hash_only():
    a, b = 1 << 14, 1 << 15
    x = secrets.randbelow(b - a) + a
    target = _h160(bs.point_mul(x))
    r = scan_range(target, a, b)
    assert r.solved and r.private_key == x


def test_matches_uncompressed_form_too():
    a, b = 1 << 14, 1 << 15
    x = secrets.randbelow(b - a) + a
    target = _h160(bs.point_mul(x), compressed=False)
    r = scan_range(target, a, b, both_forms=True)
    assert r.solved and r.private_key == x


def test_reports_not_found_cleanly():
    a, b = 1 << 14, 1 << 15
    r = scan_range(b"\x00" * 20, a, a + 500)
    assert r.solved is False and r.scanned == 500


def test_demo_recovers_planted_key():
    r = demo(bits=14, seed=3)
    assert r.solved is True
