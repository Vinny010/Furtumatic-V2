"""Patoshi-pattern analysis over early Bitcoin block data.

BACKGROUND
----------
Sergio Demian Lerner's 2013 analysis remains the most productive piece of Satoshi
forensics anyone has done, and notably it is a NONCE analysis - just not a
cryptographic one. Plotting the coinbase ExtraNonce against block height across the
first eighteen months reveals that blocks separate into distinct rising lines. One
of those lines is far denser than the rest: a single entity, running a particular
multi-machine setup, mining a large share of all early blocks.

Two structural facts make the pattern visible:

1. **Restricted nonce range.** The dominant miner's software searched only part of
   the 32-bit header nonce space before giving up and bumping the ExtraNonce, so its
   blocks cluster in a band that other miners' blocks do not respect.

2. **ExtraNonce slope.** Because that miner incremented ExtraNonce in its own
   sequence, its blocks trace a line through (height, extranonce) space, distinct
   from the lines traced by other miners.

WHAT THIS MODULE DOES AND DOES NOT CLAIM
----------------------------------------
It measures both signals and reports the clustering. It does NOT assert that any
cluster is Satoshi - that is an attribution question, and this project makes no
identity claims anywhere. The output is "these blocks share a mining fingerprint",
which is a statement about software behaviour, not about a person.

The detector is validated against SYNTHETIC block data carrying a deliberately
injected two-miner pattern (see tests/test_patoshi.py), so it is known to work
before it ever touches real data - the same positive-control discipline used for
the nonce and RNG detectors elsewhere in this project.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# The header nonce is 32-bit. The historically reported restriction is that the
# dominant early miner searched only the low portion of that space.
NONCE_MAX = 1 << 32
DEFAULT_NONCE_BAND = 0.45   # fraction of the nonce space the cluster occupies


@dataclass
class Block:
    height: int
    timestamp: int
    nonce: int
    extranonce: Optional[int] = None
    coinbase_scriptsig: str = ""
    coinbase_address: str = ""

    @property
    def nonce_fraction(self) -> float:
        return self.nonce / NONCE_MAX


def parse_extranonce(scriptsig_hex: str) -> Optional[int]:
    """Extract the ExtraNonce from an early coinbase scriptSig.

    Satoshi-era coinbase scriptSigs are two pushes:

        <push len><nBits bytes><push len><extranonce bytes>

    Both pushes are little-endian. Later blocks add arbitrary miner tags and this
    layout stops holding, which is why the function returns None rather than
    guessing when the shape does not match.
    """
    try:
        raw = bytes.fromhex(scriptsig_hex.strip())
    except (ValueError, AttributeError):
        return None
    if len(raw) < 3:
        return None
    len1 = raw[0]
    if len1 == 0 or len1 > 8 or 1 + len1 >= len(raw):
        return None
    idx = 1 + len1
    len2 = raw[idx]
    if len2 == 0 or len2 > 8 or idx + 1 + len2 > len(raw):
        return None
    return int.from_bytes(raw[idx + 1: idx + 1 + len2], "little")


def load_blocks(path: Path) -> List[Block]:
    """Load the CSV produced by tools/fetch_early_blocks.py."""
    out: List[Block] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                scriptsig = row.get("coinbase_scriptsig", "") or ""
                out.append(Block(
                    height=int(row["height"]),
                    timestamp=int(row["timestamp"]) if row.get("timestamp") else 0,
                    nonce=int(row["nonce"]) if row.get("nonce") else 0,
                    extranonce=parse_extranonce(scriptsig),
                    coinbase_scriptsig=scriptsig,
                    coinbase_address=row.get("coinbase_address", "") or ""))
            except (KeyError, ValueError):
                continue
    out.sort(key=lambda b: b.height)
    return out


@dataclass
class PatoshiFindings:
    blocks_analysed: int = 0
    blocks_with_extranonce: int = 0
    cluster_blocks: List[int] = field(default_factory=list)
    other_blocks: List[int] = field(default_factory=list)
    nonce_band: float = DEFAULT_NONCE_BAND
    cluster_share: float = 0.0
    estimated_btc: float = 0.0
    slope_segments: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def cluster_size(self) -> int:
        return len(self.cluster_blocks)


def _block_reward(height: int) -> float:
    """Bitcoin subsidy at a given height (50 BTC, halving every 210,000)."""
    return 50.0 / (2 ** (height // 210_000))


def analyse(blocks: Iterable[Block], nonce_band: float = DEFAULT_NONCE_BAND
            ) -> PatoshiFindings:
    """Separate blocks by mining fingerprint using the two structural signals.

    Signal 1 (nonce band): blocks whose header nonce falls in the low band are
    candidates for the restricted-search miner.

    Signal 2 (ExtraNonce monotonicity): within the candidates, ExtraNonce should
    advance in runs rather than jump randomly. Counting the monotone runs gives a
    measure of how coherent the cluster is - a genuine single miner produces long
    runs, while a random subset of blocks produces many short ones.
    """
    blocks = list(blocks)
    f = PatoshiFindings(blocks_analysed=len(blocks), nonce_band=nonce_band)
    if not blocks:
        f.notes.append("No blocks supplied.")
        return f

    f.blocks_with_extranonce = sum(1 for b in blocks if b.extranonce is not None)

    for b in blocks:
        if b.nonce_fraction < nonce_band:
            f.cluster_blocks.append(b.height)
        else:
            f.other_blocks.append(b.height)

    f.cluster_share = len(f.cluster_blocks) / len(blocks)
    f.estimated_btc = sum(_block_reward(h) for h in f.cluster_blocks)

    # Count monotone ExtraNonce runs within the cluster.
    cluster = [b for b in blocks
               if b.height in set(f.cluster_blocks) and b.extranonce is not None]
    runs, prev = 0, None
    for b in cluster:
        if prev is None or b.extranonce < prev:
            runs += 1
        prev = b.extranonce
    f.slope_segments = runs

    if f.blocks_with_extranonce == 0:
        f.notes.append(
            "No ExtraNonce could be parsed. Either the data lacks coinbase "
            "scriptSigs, or these blocks postdate the era when the two-push "
            "layout held.")
    expected = nonce_band  # share expected if nonces were uniform
    if f.cluster_share > expected * 1.25:
        f.notes.append(
            "Cluster holds %.1f%% of blocks against %.1f%% expected under a uniform "
            "nonce distribution - consistent with a miner whose software searched "
            "only part of the nonce space."
            % (100 * f.cluster_share, 100 * expected))
    elif f.cluster_share < expected * 0.75:
        f.notes.append(
            "Cluster is SMALLER than uniform expectation (%.1f%% vs %.1f%%). The "
            "band threshold is probably wrong for this data range."
            % (100 * f.cluster_share, 100 * expected))
    else:
        f.notes.append(
            "Cluster share (%.1f%%) is close to the uniform expectation (%.1f%%), "
            "so the nonce band alone does not separate miners in this sample."
            % (100 * f.cluster_share, 100 * expected))
    f.notes.append(
        "A cluster is a MINING FINGERPRINT - shared software behaviour. It carries "
        "no identity claim about who operated the software.")
    return f


def nonce_histogram(blocks: Iterable[Block], bins: int = 20) -> List[Tuple[float, int]]:
    """Distribution of header nonces across the 32-bit space.

    Under honest uniform mining every bin holds roughly the same count. A sharp
    drop past some fraction is the restricted-search signature.
    """
    counts = [0] * bins
    total = 0
    for b in blocks:
        idx = min(int(b.nonce_fraction * bins), bins - 1)
        counts[idx] += 1
        total += 1
    return [((i + 0.5) / bins, c) for i, c in enumerate(counts)]
