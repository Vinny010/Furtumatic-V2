"""Independent verification of the block-9 spend chain.

These tests re-derive everything from raw bytes with this project's own code: its
own transaction parser, its own SIGHASH_ALL reconstruction, its own secp256k1. If
any of that were wrong, the signatures would not verify.
"""

import json
import secrets
from pathlib import Path

import pytest

from spa.analysis import bitcoin_scope as bs
from spa.analysis.spendchain import (analyse_chain, extract_signature, parse_tx,
                                     p2pk_subscript, sighash_all, txid_of)

ROOT = Path(__file__).resolve().parents[1]
CHAIN_FILE = ROOT / "data" / "block9_spend_chain.json"

# The first Bitcoin transaction ever made (Satoshi -> Hal Finney, 2009-01-12).
FIRST_TX = "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16"


@pytest.fixture(scope="module")
def chain():
    if not CHAIN_FILE.exists():
        pytest.skip("spend chain data not present")
    return json.loads(CHAIN_FILE.read_text())


@pytest.fixture(scope="module")
def entries(chain):
    return [(e["expected_txid"], e.get("block_height"), e["raw_hex"])
            for e in chain["entries"]]


# ---------------------------------------------------------------- primitives
def test_txid_of_reproduces_the_first_bitcoin_transaction(entries):
    """The strongest possible authentication: the bytes hash to a famous constant."""
    raw = bytes.fromhex(entries[0][2])
    assert txid_of(raw) == FIRST_TX


def test_parse_then_serialize_is_lossless(entries):
    """If the parser drops or reorders anything, the round trip breaks - and so
    would every digest built on top of it."""
    for _label, _height, raw_hex in entries:
        raw = bytes.fromhex(raw_hex)
        assert parse_tx(raw).serialize() == raw


def test_first_tx_structure(entries):
    tx = parse_tx(bytes.fromhex(entries[0][2]))
    assert len(tx.vin) == 1
    assert len(tx.vout) == 2
    # 10 BTC to Hal Finney, 40 BTC back to the block-9 key as change.
    assert tx.vout[0].value == 10_00000000
    assert tx.vout[1].value == 40_00000000


def test_extract_signature_from_p2pk_scriptsig(entries):
    tx = parse_tx(bytes.fromhex(entries[0][2]))
    sig = extract_signature(tx.vin[0].script_sig)
    assert sig is not None
    r, s, hashtype = sig
    assert hashtype == 1                      # SIGHASH_ALL
    assert 0 < r < bs.N and 0 < s < bs.N


def test_p2pk_subscript_shape(chain):
    sub = p2pk_subscript(chain["signing_pubkey"])
    assert sub[0] == 65 and sub[-1] == 0xAC and len(sub) == 67


# ---------------------------------------------------------------- verification
def test_every_signature_verifies(chain, entries):
    """The headline: all five signatures verify against the block-9 key."""
    f = analyse_chain(entries, chain["signing_pubkey"])
    assert f.transactions == 5
    assert f.txids_authenticated == 5
    assert len(f.signatures) == 5
    assert f.verified == 5
    assert all(s.verifies is True for s in f.signatures)


def test_no_nonce_reuse_in_satoshis_only_signing_key(chain, entries):
    """The decisive on-chain result for coin recovery."""
    f = analyse_chain(entries, chain["signing_pubkey"])
    assert f.distinct_r == 5
    assert f.reused_nonce_pairs == []
    assert f.recovered_key is None
    assert f.nonce_safe is True


def test_signing_key_is_derived_not_asserted(chain, entries):
    """The key is recoverable from the chain's own change output, so the analysis
    does not depend on the data source naming it correctly."""
    tx = parse_tx(bytes.fromhex(entries[0][2]))
    spk = tx.vout[1].script_pubkey
    assert spk[1:-1].hex() == chain["signing_pubkey"]


def test_sighash_is_reconstructed_correctly(chain, entries):
    """A wrong digest cannot produce a verifying signature, so this is implied by
    the verification test - but assert it directly against a tampered subscript."""
    pub = bs.parse_uncompressed_pubkey(chain["signing_pubkey"])
    tx = parse_tx(bytes.fromhex(entries[0][2]))
    r, s, _ = extract_signature(tx.vin[0].script_sig)
    good = sighash_all(tx, 0, p2pk_subscript(chain["signing_pubkey"]))
    assert bs.ecdsa_verify(pub, good, r, s) is True
    bad = sighash_all(tx, 0, b"\x00" * 67)
    assert bs.ecdsa_verify(pub, bad, r, s) is False


# ---------------------------------------------------------------- controls
def test_tampered_bytes_are_rejected(chain, entries):
    """Flip one bit and the txid check must catch it - otherwise the whole
    'self-authenticating' claim is worthless."""
    label, height, raw_hex = entries[0]
    tampered = bytearray(bytes.fromhex(raw_hex))
    tampered[-5] ^= 0x01
    f = analyse_chain([(label, height, tampered.hex())], chain["signing_pubkey"])
    assert f.txid_mismatches
    assert f.authenticated is False
    assert any("MISMATCH" in n for n in f.notes)


def test_nonce_reuse_would_be_detected():
    """Positive control: the detector must fire on a genuinely reused nonce.

    Built from synthetic keys, never from real material.
    """
    from spa.analysis.bitcoin_scope import recover_ecdsa_key
    priv = secrets.randbelow(bs.N - 1) + 1
    k = secrets.randbelow(bs.N - 1) + 1
    r = bs.point_mul(k)[0] % bs.N
    import hashlib
    z1 = int.from_bytes(hashlib.sha256(b"one").digest(), "big")
    z2 = int.from_bytes(hashlib.sha256(b"two").digest(), "big")
    s1 = (pow(k, -1, bs.N) * (z1 + r * priv)) % bs.N
    s2 = (pow(k, -1, bs.N) * (z2 + r * priv)) % bs.N
    assert recover_ecdsa_key(r, s1, z1, s2, z2) == priv
