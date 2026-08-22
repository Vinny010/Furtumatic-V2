# 24/7 Bitcoin-Puzzle Kangaroo — deployment guide

A practical setup for running a Kangaroo search on a Windows desktop around the
clock, with a live progress window, crash-safe resume, and auto-restart.

**Scope:** the *public* Bitcoin Puzzle (an intended, funded challenge). Needs an
**exposed public key** — Kangaroo cannot run from an address alone. Realistic only
as part of a **pool** for high puzzles; a single desktop's expected time is
enormous (see `spa.cli kangaroo --estimate`). Point your rig at the honest numbers,
not a dream.

## The two engines (don't mix them up)

| | Reference engine (this repo) | Real engine (for the 24/7 run) |
|---|---|---|
| What | `spa.lab.kangaroo`, pure Python | JeanLucPons **Kangaroo** (CUDA) |
| Speed | ~4e4 steps/s | ~1e9–1e10 steps/s on a GPU |
| Role | correctness, sharding, verify, GUI feed | the actual heavy lifting |

Same *algorithm*; the CUDA build just runs it on your GPU ~25,000× faster. Use the
CUDA build for the real search; use this repo to plan, shard, verify, and display.

## Step 1 — validate the target before spending a watt

```
python -m spa.cli kangaroo --bits 135 --estimate       # honest cost/time
```
Get #135's real exposed pubkey, then confirm it's on-curve and in range with
`spa.lab.kangaroo.verify_solution` / `bitcoin_scope.parse_uncompressed_pubkey`
before committing GPU time.

## Step 2 — pick your slice (pool coordination)

If you're in a pool, take a disjoint shard so no one overlaps:
```
python -m spa.cli kangaroo --bits 135 --shard 1000:7   # worker 7 of 1000
```

## Step 3 — run the CUDA engine with checkpointing + auto-restart

Edit paths in `tools/run_kangaroo.bat`, then run it. It launches JLP Kangaroo with:
- `-w work.kcp -wi 300` — save work every 5 minutes
- `-i work.kcp` — resume from it after a crash/reboot
and **auto-restarts** on exit, stopping only when a key is found.

Put a shortcut to the .bat in `shell:startup` so it survives reboots.

## Step 4 — the progress window

Point the GUI at the status file:
```
python tools/progress_gui.py --status status.json
```
It shows rate, distinguished points, % of expected work, ETA, and a **SOLVED**
banner. (For the reference engine, `solve_checkpointed(..., status_path="status.json")`
writes that file directly. For JLP Kangaroo, parse its console/work-file stats into
the same JSON shape — a ~20-line adapter.)

## Step 5 — verify any hit before you celebrate

Never trust a raw "found" line. Confirm it:
```python
from spa.lab.kangaroo import verify_solution
verify_solution(pubkey, found_key, expected_address="1...")   # {'verified': True}
```

## Crash-safety, proven

The reference engine's checkpointing is tested (`tests/test_kangaroo_checkpoint.py`):
a run capped mid-way (standing in for a crash) reloads and still finds the key, and
the checkpoint is written atomically (`.tmp` + `os.replace`) so a crash *during* a
save can't corrupt it. JLP Kangaroo's `-w/-wi/-i` gives the same guarantee for the
CUDA run.

## Honest expectations

- One desktop on #135: expected **thousands of years** (`--estimate`). The point of
  running is to contribute to a **pool** and earn a proportional share if it lands.
- Electricity is a real, guaranteed cost; the prize is a long-odds maybe. Only
  commit power you can afford to spend either way.
- This is the *only* legitimate, consented target class. Do not repoint any of this
  at wallets that aren't part of the puzzle — those belong to real people.
