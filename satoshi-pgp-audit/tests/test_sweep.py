"""Sequential sweep: address decode, cursor bookkeeping, crash-safe resume, verify."""
import json
import os

import pytest

from spa.lab.sweep import (Sweep, address_to_h160, b58decode, demo, load_puzzle,
                           plan, puzzle_range, run_local, verify_key)
from spa.analysis import bitcoin_scope as bs
from spa.lab.bruteforce import _h160

ROOT = os.path.dirname(os.path.dirname(__file__))
PUZZLES = os.path.join(ROOT, "data", "puzzles.json")


def test_base58check_roundtrip_known_address():
    # #72 address decodes to exactly 20 bytes with a valid checksum.
    h = address_to_h160("1JTK7s9YVYywfm5XUH7RNhHJH1LshCaRFR")
    assert len(h) == 20


def test_base58check_rejects_corrupted_address():
    with pytest.raises(ValueError):
        address_to_h160("1JTK7s9YVYywfm5XUH7RNhHJH1LshCaRFX")  # last char flipped


def test_leading_ones_become_zero_bytes():
    # A version-0 P2PKH address starts with '1' -> leading 0x00 byte preserved.
    raw = b58decode("1JTK7s9YVYywfm5XUH7RNhHJH1LshCaRFR")
    assert raw[0] == 0x00


def test_blocks_tile_the_range_exactly():
    s = Sweep(lo=100, hi=250, block=40, target_h160_hex="00" * 20)
    seen = []
    while True:
        blk = s.next_block()
        if blk is None:
            break
        seen.append(blk)
    assert seen[0] == (100, 140)
    assert seen[-1][1] == 250                      # last block clamps to hi
    assert sum(b - a for a, b in seen) == 150      # full width, no gaps/overlap
    assert s.keys_scanned == 150
    assert s.done


def test_puzzle_range_math():
    assert puzzle_range(72) == (1 << 71, 1 << 72)


def test_demo_recovers_planted_key_sequentially():
    r = demo(bits=16, seed=3)
    assert r.solved and r.private_key is not None
    assert "verify=True" in " ".join(r.notes)


def test_checkpoint_resume_finds_key_after_simulated_crash(tmp_path):
    """Sweep a small range, stop after 2 blocks (a 'crash'), reload, finish."""
    import random
    lo, hi = puzzle_range(14)
    x = random.Random(11).randrange(lo, hi)
    target = _h160(bs.point_mul(x), True).hex()
    cp = str(tmp_path / "cp.json")

    s1 = Sweep(lo=lo, hi=hi, block=256, target_h160_hex=target, label="resume-test")
    r1 = run_local(s1, checkpoint_path=cp, max_blocks=2)
    # Either we got unlucky-lucky and found it in the first 2 blocks, or we paused.
    if not r1.solved:
        cursor_before = Sweep.load(cp).cursor
        assert cursor_before > lo
        s2 = Sweep.load(cp)                         # resume from disk
        r2 = run_local(s2, checkpoint_path=cp)
        assert r2.solved and r2.private_key == x
        assert s2.cursor >= cursor_before          # continued, didn't restart


def test_verify_key_true_and_false():
    x = 123456789
    target = _h160(bs.point_mul(x), True)
    assert verify_key(x, target) is True
    assert verify_key(x + 1, target) is False
    assert verify_key(0, target) is False          # out of range rejected


def test_status_file_is_valid_json_with_honest_eta(tmp_path):
    s = Sweep(lo=1 << 71, hi=1 << 72, block=1 << 40, target_h160_hex="00" * 20,
              label="#72")
    s.next_block()
    sp = str(tmp_path / "status.json")
    s.write_status(sp, rate_per_sec=1.7e9)
    st = json.loads(open(sp).read())
    assert st["mode"].startswith("brute-force")
    assert st["percent"] >= 0.0
    assert "years" in st["eta"] or "days" in st["eta"]  # honest, not "soon"
    assert st["solved"] is False


def test_plan_reports_astronomical_but_honest_numbers():
    p = plan(72, "1JTK7s9YVYywfm5XUH7RNhHJH1LshCaRFR")
    assert p["keys"] == (1 << 72) - (1 << 71)
    assert "years" in p["full_sweep"]              # a solo #72 sweep is ~44,000 yr
    assert p["odds_per_ticket"].startswith("1 in")


def test_load_puzzle_72_from_data():
    s = load_puzzle(72, puzzles_path=PUZZLES)
    assert s.lo == (1 << 71) and s.hi == (1 << 72)
    assert len(s.target_h160) == 20


def test_puzzles_json_addresses_all_valid():
    cfg = json.loads(open(PUZZLES).read())
    for bits, entry in cfg["puzzles"].items():
        assert len(address_to_h160(entry["address"])) == 20, bits
