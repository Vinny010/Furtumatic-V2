"""Patoshi detector, validated against synthetic data with a known injected pattern.

Same discipline as everywhere else in this project: a detector that has only ever
been run on real data of unknown ground truth is indistinguishable from a broken
one. Here the ground truth is constructed, so the detector can be checked before it
is trusted.
"""

import random

from spa.analysis.patoshi import (Block, PatoshiFindings, analyse,
                                  nonce_histogram, parse_extranonce)

NONCE_MAX = 1 << 32


# ---------------------------------------------------------------- scriptSig
def test_parse_real_early_coinbase_layout():
    """Genuine early layout: <push 4><nBits><push 1><extranonce>.

    04 ffff001d 01 04  ->  nBits ffff001d, ExtraNonce 4.
    """
    assert parse_extranonce("04ffff001d0104") == 4


def test_parse_multibyte_extranonce():
    # 04 ffff001d 02 e803  -> little-endian 0x03e8 = 1000
    assert parse_extranonce("04ffff001d02e803") == 1000


def test_parse_rejects_malformed():
    assert parse_extranonce("") is None
    assert parse_extranonce("zz") is None
    assert parse_extranonce("04") is None
    assert parse_extranonce("ff" * 4) is None   # push length out of range


# ---------------------------------------------------------------- detector
def _synthetic(n=2000, cluster_fraction=0.6, band=0.45, seed=7):
    """Build blocks from two miners with KNOWN behaviour.

    Miner A ("restricted"): searches only the low ``band`` of the nonce space and
    advances ExtraNonce monotonically - the Patoshi fingerprint.
    Miner B ("uniform"): uses the whole nonce space with random ExtraNonce.
    """
    rng = random.Random(seed)
    blocks, truth = [], {}
    extranonce = 0
    for h in range(1, n + 1):
        if rng.random() < cluster_fraction:
            nonce = int(rng.uniform(0, band) * NONCE_MAX)
            extranonce += 1
            en = extranonce
            truth[h] = "restricted"
        else:
            nonce = rng.randrange(NONCE_MAX)
            en = rng.randrange(1, 1 << 16)
            truth[h] = "uniform"
        blocks.append(Block(height=h, timestamp=1231006505 + h * 600,
                            nonce=nonce, extranonce=en))
    return blocks, truth


def test_detector_finds_the_injected_cluster():
    blocks, truth = _synthetic()
    f = analyse(blocks)
    assert f.blocks_analysed == len(blocks)
    found = set(f.cluster_blocks)
    restricted = {h for h, kind in truth.items() if kind == "restricted"}
    # Every restricted-miner block is in the low band by construction.
    assert restricted <= found
    # The cluster is enriched well beyond the uniform expectation.
    assert f.cluster_share > f.nonce_band * 1.25


def test_detector_reports_enrichment_note():
    blocks, _ = _synthetic()
    f = analyse(blocks)
    assert any("consistent with a miner" in n for n in f.notes)


def test_negative_control_all_uniform_miners():
    """With no restricted miner, the cluster share must match the band - i.e. the
    detector must NOT invent a pattern."""
    blocks, _ = _synthetic(cluster_fraction=0.0)
    f = analyse(blocks)
    assert abs(f.cluster_share - f.nonce_band) < 0.05
    assert not any("consistent with a miner" in n for n in f.notes)


def test_btc_estimate_uses_the_subsidy_schedule():
    blocks, _ = _synthetic(n=100, cluster_fraction=1.0)
    f = analyse(blocks)
    # All 100 blocks are below height 210000, so the subsidy is 50 BTC each.
    assert f.estimated_btc == 50.0 * f.cluster_size


def test_findings_never_assert_identity():
    """Hard requirement: the tool reports mining fingerprints, not people."""
    blocks, _ = _synthetic(n=200)
    f = analyse(blocks)
    assert any("no identity claim" in n for n in f.notes)
    blob = " ".join(f.notes).lower()
    assert "satoshi is" not in blob and "proves" not in blob


def test_empty_input_is_handled():
    f = analyse([])
    assert isinstance(f, PatoshiFindings)
    assert f.blocks_analysed == 0
    assert f.cluster_size == 0


def test_histogram_is_flat_for_uniform_nonces():
    rng = random.Random(3)
    blocks = [Block(height=i, timestamp=0, nonce=rng.randrange(NONCE_MAX))
              for i in range(6000)]
    hist = nonce_histogram(blocks, bins=10)
    counts = [c for _, c in hist]
    assert len(counts) == 10
    assert max(counts) < min(counts) * 1.6   # roughly flat


def test_histogram_shows_the_restricted_band():
    blocks, _ = _synthetic(n=4000, cluster_fraction=0.85)
    hist = nonce_histogram(blocks, bins=10)
    counts = [c for _, c in hist]
    low = sum(counts[:4])    # bins covering roughly the low 40%
    high = sum(counts[5:])
    assert low > high * 2, "restricted band should dominate the low bins"
