"""Sequential range sweep for an address-only Bitcoin Puzzle (e.g. #72).

This is the *planner + bookkeeping + verify* half of a 24/7 brute-force run. The
actual key crunching is done by a CUDA engine (Rotor-CUDA / BitCrack) at GPU
speed; this module hands that engine one contiguous block at a time, records how
far we've got in a crash-safe checkpoint (a single cursor integer), writes a
status file for the progress window, and verifies any claimed hit before you
trust it.

Why sequential and not "random"? For a key drawn uniformly in the range, every
ordering has identical odds, and sequential has the simplest possible resume: one
number, "scanned up to here". Random ordering buys no extra probability (see
spa.analysis.puzzle_pattern for the measured proof that the solved keys are
uniform, i.e. there is no hot zone to aim at).

Scope: the PUBLIC Bitcoin Puzzle only - an intended, funded challenge whose
addresses were created to be searched. These puzzles have NO exposed public key,
so Kangaroo cannot run and brute force is the only method; that also means a solo
rig is not structurally behind a Kangaroo farm here. Do not point this at any
address that is not part of the puzzle.

Honest odds: #72 is a 2^71-wide range. At ~1.7e9 keys/s a full sweep is ~44,000
years; each 1e12 keys (~10 min) is a ~1-in-2.4-billion lottery ticket that could
land on day one or never. Run it as a lottery, not a plan with an ETA.
"""

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Optional, Tuple

from ..analysis import bitcoin_scope as bs
from .bruteforce import BruteResult, _h160, scan_range

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s: str) -> bytes:
    """Decode a Base58 string to raw bytes (leading '1' -> leading 0x00)."""
    num = 0
    for ch in s:
        idx = _B58.find(ch)
        if idx < 0:
            raise ValueError("invalid base58 character %r" % ch)
        num = num * 58 + idx
    body = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    n_pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * n_pad + body


def address_to_h160(addr: str) -> bytes:
    """Base58Check-decode a P2PKH address to its 20-byte hash160 (checksum verified)."""
    raw = b58decode(addr)
    if len(raw) != 25:
        raise ValueError("address does not decode to 25 bytes: %s" % addr)
    payload, checksum = raw[:21], raw[21:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != checksum:
        raise ValueError("bad Base58Check checksum for %s" % addr)
    if payload[0] != 0x00:
        raise ValueError("not a version-0 P2PKH address: %s" % addr)
    return payload[1:]


def verify_key(priv: int, target_h160: bytes) -> bool:
    """True iff `priv` derives an address (compressed or uncompressed) matching target."""
    if priv <= 0 or priv >= bs.N:
        return False
    P = bs.point_mul(priv)
    return _h160(P, True) == target_h160 or _h160(P, False) == target_h160


def _fmt_duration(secs: float) -> str:
    if secs < 0:
        return "—"
    yr = secs / 3.156e7
    if yr >= 1:
        return "%.2e years" % yr
    days = secs / 86400
    if days >= 1:
        return "%.1f days" % days
    return "%.0f s" % secs


@dataclass
class Sweep:
    """A resumable sequential sweep of [lo, hi) in fixed-size blocks.

    `cursor` is the next unscanned key: the entire crash-safe state in one int.
    """
    lo: int
    hi: int
    block: int
    target_h160_hex: str
    label: str = ""
    cursor: Optional[int] = None
    keys_scanned: int = 0
    solved: bool = False
    private_key: Optional[int] = None
    started: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.cursor is None:
            self.cursor = self.lo
        if not (0 <= self.lo < self.hi):
            raise ValueError("require 0 <= lo < hi")
        if self.block <= 0:
            raise ValueError("block size must be positive")

    @property
    def target_h160(self) -> bytes:
        return bytes.fromhex(self.target_h160_hex)

    @property
    def width(self) -> int:
        return self.hi - self.lo

    @property
    def done(self) -> bool:
        return self.solved or self.cursor >= self.hi

    def fraction(self) -> float:
        return min((self.cursor - self.lo) / self.width, 1.0)

    def next_block(self) -> Optional[Tuple[int, int]]:
        """Return the next [start, end) block and advance the cursor, or None if done."""
        if self.cursor >= self.hi:
            return None
        start = self.cursor
        end = min(start + self.block, self.hi)
        self.cursor = end
        self.keys_scanned += end - start
        return (start, end)

    # ----------------------------------------------------------- persistence
    def save(self, path: str) -> None:
        """Atomically write the checkpoint (.tmp + os.replace so a crash can't corrupt it)."""
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(asdict(self), fh)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: str) -> "Sweep":
        with open(path) as fh:
            d = json.load(fh)
        return cls(**d)

    def write_status(self, path: str, rate_per_sec: float = 0.0) -> None:
        """Write a status JSON the progress GUI reads."""
        remaining = max(self.hi - self.cursor, 0)
        eta = _fmt_duration(remaining / rate_per_sec) if rate_per_sec > 0 else "—"
        status = {
            "label": self.label,
            "mode": "brute-force sweep (sequential)",
            "keys_scanned": self.keys_scanned,
            "cursor_hex": "%x" % self.cursor,
            "percent": self.fraction() * 100.0,
            "rate_per_sec": rate_per_sec,
            "eta": eta,
            "solved": self.solved,
            "private_key_hex": ("%x" % self.private_key) if self.private_key else None,
            "updated": time.time(),
        }
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(status, fh)
        os.replace(tmp, path)


def run_local(sweep: Sweep, checkpoint_path: Optional[str] = None,
              status_path: Optional[str] = None, max_blocks: Optional[int] = None,
              both_forms: bool = True) -> BruteResult:
    """CPU reference sweep: scan block-by-block with the pure-Python engine.

    This is the SLOW correctness/reference path (used by tests and for small
    ranges). The real 24/7 run uses Rotor-CUDA on the GPU driven by the same
    cursor concept (see tools/run_rotor_sweep.bat). Checkpoint is saved after
    every block so a stop/crash resumes from `sweep.load(...)`.
    """
    blocks = 0
    while True:
        blk = sweep.next_block()
        if blk is None:
            break
        a, b = blk
        r = scan_range(sweep.target_h160, a, b, both_forms=both_forms)
        if r.solved:
            sweep.solved = True
            sweep.private_key = r.private_key
            if checkpoint_path:
                sweep.save(checkpoint_path)
            if status_path:
                sweep.write_status(status_path)
            r.notes.append("verify=%s" % verify_key(r.private_key, sweep.target_h160))
            return r
        if checkpoint_path:
            sweep.save(checkpoint_path)
        if status_path:
            sweep.write_status(status_path)
        blocks += 1
        if max_blocks is not None and blocks >= max_blocks:
            break
    return BruteResult(False, None, sweep.keys_scanned,
                       ["no match yet; cursor at 0x%x (%.6f%% of range)"
                        % (sweep.cursor, sweep.fraction() * 100.0)])


# ----------------------------------------------------------------- puzzles
def puzzle_range(bits: int) -> Tuple[int, int]:
    """[2^(bits-1), 2^bits) - the interval puzzle #bits lives in."""
    return (1 << (bits - 1), 1 << bits)


def plan(bits: int, address: str, rate_per_sec: float = 1.7e9,
         ticket: int = 10 ** 12) -> dict:
    """Honest cost/odds for a solo sweep - no hype."""
    lo, hi = puzzle_range(bits)
    width = hi - lo
    full_secs = width / rate_per_sec
    return {
        "puzzle": bits,
        "address": address,
        "range_hex": "%x:%x" % (lo, hi - 1),
        "keys": width,
        "rate_per_sec": rate_per_sec,
        "full_sweep": _fmt_duration(full_secs),
        "ticket_keys": ticket,
        "seconds_per_ticket": ticket / rate_per_sec,
        "odds_per_ticket": "1 in %.3g" % (width / ticket),
    }


def load_puzzle(bits: int, block: int = 1 << 20, puzzles_path: Optional[str] = None) -> Sweep:
    """Build a Sweep for a puzzle number from data/puzzles.json."""
    if puzzles_path is None:
        here = os.path.dirname(__file__)
        puzzles_path = os.path.join(here, "..", "..", "..", "data", "puzzles.json")
    with open(puzzles_path) as fh:
        cfg = json.load(fh)
    entry = cfg["puzzles"][str(bits)]
    lo, hi = puzzle_range(bits)
    return Sweep(lo=lo, hi=hi, block=block,
                 target_h160_hex=address_to_h160(entry["address"]).hex(),
                 label="puzzle #%d (%s)" % (bits, entry["address"]))


def demo(bits: int = 20, seed: int = 7, block: int = 1 << 10) -> BruteResult:
    """Plant a key in [2^(bits-1), 2^bits), then sweep sequentially and recover it."""
    import random
    rng = random.Random(seed)
    lo, hi = puzzle_range(bits)
    x = rng.randrange(lo, hi)
    target = _h160(bs.point_mul(x), True)
    sweep = Sweep(lo=lo, hi=hi, block=block, target_h160_hex=target.hex(),
                  label="demo #%d" % bits)
    r = run_local(sweep)
    r.notes.append("planted x=%d recovered=%s" % (x, r.private_key))
    return r
