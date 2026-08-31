# 24/7 sequential brute-force of Bitcoin Puzzle #72 — deploy guide

A solo, crash-safe setup for scanning an **address-only** puzzle (no exposed
public key) on a Windows desktop, with a live progress window and resume.

**Why #72 and not #135/#140:** the high puzzles have *exposed public keys*, so a
Kangaroo *farm* sweeps them the moment they're viable (120→125→130→135, same
operator). #72 has **no exposed pubkey** → Kangaroo is impossible for *everyone*,
so the farm's whole advantage evaporates and a solo rig is on equal footing. The
cost is that brute force is O(range) with no √ shortcut.

**Honest odds (don't skip this):** #72 is 2⁷¹ keys wide. At ~1.7 Gkey/s a full
sweep is **~44,000 years**; every ~1e12 keys (~10 min) is a **~1-in-2.4-billion**
lottery ticket that could hit on day one or never. Run it as a lottery. Only
commit power you're happy to spend either way. `python -m spa.cli sweep --bits 72`
prints these numbers.

## The two halves (don't mix them up)

| | Reference (this repo) | Real engine (the 24/7 run) |
|---|---|---|
| What | `spa.lab.sweep`, pure Python | **Rotor-CUDA** (or BitCrack), CUDA |
| Speed | ~1e4 keys/s | ~1e9 keys/s on your GPU |
| Role | plan, checkpoint format, **verify**, GUI feed | the actual key crunching |

## Step 1 — sanity-check the target and the odds
```
python -m spa.cli sweep --bits 72
```
Confirms the range `800…000 : fff…fff`, the address, and the honest ETA.

## Step 2 — run the real engine with auto-resume
Edit the paths and flags in `tools/run_rotor_sweep.bat` (Rotor-CUDA exe, address,
block size), then run it. It:
- keeps a **cursor file** = the next unscanned key (the whole resume state),
- scans one block per Rotor-CUDA launch (`-range start:end`),
- advances the cursor atomically (temp file + move) so a crash/reboot resumes,
- stops when a key is written to `found72.txt` or the range is exhausted.

Put a shortcut to the .bat in `shell:startup` so it survives reboots.

**Sequential, bottom-to-top:** the key is uniform in the range, so every ordering
has identical odds and sequential has the simplest resume (one number). There is
no "hot zone" to aim at — `spa.analysis.puzzle_pattern` (if you run it on the
solved keys) shows the positions are statistically uniform.

## Step 3 — progress window
```
python tools/progress_gui.py --status status.json
```
Shows target, keys scanned, cursor, % of range, rate, and an **honest** ETA
(remaining ÷ rate — not the Kangaroo √ formula). For Rotor-CUDA, write a ~15-line
adapter that parses its console output into the same status JSON shape that
`spa.lab.sweep.Sweep.write_status` emits (keys `mode`, `label`, `keys_scanned`,
`cursor_hex`, `percent`, `rate_per_sec`, `eta`, `solved`, `private_key_hex`,
`updated`).

## Step 4 — verify any hit before you celebrate
Never trust a raw "found" line. Confirm the private key derives the address:
```python
from spa.lab.sweep import verify_key, address_to_h160
verify_key(found_key_int, address_to_h160("1JTK7s9YVYywfm5XUH7RNhHJH1LshCaRFR"))
# -> True
```

## Crash-safety, proven
`tests/test_sweep.py` stops a sweep mid-range (standing in for a crash), reloads
the checkpoint, and confirms it continues from the saved cursor and still finds a
planted key — and that the checkpoint is written atomically so a crash *during* a
save can't corrupt it.

## Scope
The **public** Bitcoin Puzzle only — funded addresses created to be searched.
Do not point any of this at an address that isn't part of the puzzle; those
belong to real people.
