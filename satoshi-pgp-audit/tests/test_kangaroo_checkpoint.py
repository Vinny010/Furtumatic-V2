"""Checkpoint/resume: a paused (or crashed) run must resume and still solve."""
import json
import os
import random

from spa.analysis import bitcoin_scope as bs
from spa.lab.kangaroo import solve_checkpointed


def test_pause_then_resume_solves(tmp_path):
    cp = str(tmp_path / "work.json")
    st = str(tmp_path / "status.json")
    rng = random.Random(9)
    a, b = 1 << 26, 1 << 27
    x = rng.randrange(a, b)
    Q = bs.point_mul(x)

    # First run: capped low to force a PAUSE (stands in for a crash), state saved.
    r1 = solve_checkpointed(Q, a, b, cp, save_every=2000, max_ops=6000, status_path=st)
    assert r1.solved is False
    assert os.path.exists(cp) and os.path.exists(st)
    ops_after_pause = json.load(open(st))["ops"]
    assert ops_after_pause > 0

    # Resume: no max_ops, must continue from checkpoint and solve.
    r2 = solve_checkpointed(Q, a, b, cp, save_every=2000, status_path=st)
    assert r2.solved is True
    assert r2.private_key == x
    assert r2.notes[0] == "resumed from checkpoint"


def test_status_file_is_valid_json(tmp_path):
    cp = str(tmp_path / "w.json")
    st = str(tmp_path / "s.json")
    x = 12345678
    Q = bs.point_mul(x)
    solve_checkpointed(Q, 1 << 23, 1 << 24, cp, save_every=1000,
                       max_ops=3000, status_path=st)
    s = json.load(open(st))
    for k in ("ops", "rate_per_sec", "percent_of_expected", "distinguished_points"):
        assert k in s


def test_checkpoint_write_is_atomic(tmp_path):
    """The .tmp+replace pattern means the live file is never half-written."""
    cp = str(tmp_path / "w.json")
    Q = bs.point_mul(999983)
    solve_checkpointed(Q, 1 << 20, 1 << 21, cp, save_every=500, max_ops=1500)
    # File must be complete, parseable JSON with the expected keys.
    st = json.load(open(cp))
    assert {"tame_pt", "wild_pt", "tame_sc", "wild_sc", "ops"} <= set(st)
