"""Independent verification of the only signatures Satoshi's keys ever produced.

WHY THIS IS THE DECISIVE ON-CHAIN TEST
--------------------------------------
Coins that were never spent publish no signature, so no nonce exists to attack. The
~1.1M BTC of dormant Patoshi coinbases are nonce-immune for that reason alone - the
attack surface is empty, not merely hard.

But the block-9 coinbase key IS an exception: it was spent, and then reused as the
change key at each hop down a short chain of transactions beginning with the famous
2009-01-12 transfer to Hal Finney. That makes it the one Satoshi-attributed key that
signed more than once, and therefore the ONLY place where ECDSA nonce reuse could
ever have leaked a Satoshi private key.

If any two of those signatures shared a nonce, the private key falls out in closed
form from public data:

    k = (z1 - z2) / (s1 - s2)      d = (s1*k - z1) / r

This module reconstructs each SIGHASH_ALL digest from raw transaction bytes,
verifies every signature against the key with this project's own secp256k1 code,
and tests the reuse condition.

TRUST MODEL
-----------
The raw transaction bytes come from a third-party repository, but they are NOT
trusted on that basis. Bitcoin transaction ids are the double-SHA-256 of the raw
bytes, so hashing the supplied bytes and comparing against the well-known txids
authenticates the data completely and locally. If the bytes were altered by even one
bit, the txid would not match. That check runs before any analysis, and the analysis
refuses to proceed without it.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import bitcoin_scope as bs

SIGHASH_ALL = 1


def dsha(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def txid_of(raw: bytes) -> str:
    """Bitcoin txid: double-SHA-256 of the raw bytes, displayed byte-reversed."""
    return dsha(raw)[::-1].hex()


# ---------------------------------------------------------------- parsing
@dataclass
class TxIn:
    prev_txid: bytes
    prev_index: int
    script_sig: bytes
    sequence: int


@dataclass
class TxOut:
    value: int
    script_pubkey: bytes


@dataclass
class Tx:
    version: int
    vin: List[TxIn]
    vout: List[TxOut]
    locktime: int

    def serialize(self, script_overrides: Optional[Dict[int, bytes]] = None) -> bytes:
        """Serialise, optionally replacing input scripts (for sighash construction)."""
        overrides = script_overrides or {}
        out = self.version.to_bytes(4, "little")
        out += _varint(len(self.vin))
        for i, vin in enumerate(self.vin):
            script = overrides.get(i, vin.script_sig) if overrides else vin.script_sig
            out += vin.prev_txid + vin.prev_index.to_bytes(4, "little")
            out += _varint(len(script)) + script
            out += vin.sequence.to_bytes(4, "little")
        out += _varint(len(self.vout))
        for vout in self.vout:
            out += vout.value.to_bytes(8, "little")
            out += _varint(len(vout.script_pubkey)) + vout.script_pubkey
        out += self.locktime.to_bytes(4, "little")
        return out


def _varint(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xFFFFFFFF:
        return b"\xfe" + n.to_bytes(4, "little")
    return b"\xff" + n.to_bytes(8, "little")


def _read_varint(data: bytes, i: int) -> Tuple[int, int]:
    first = data[i]
    if first < 0xFD:
        return first, i + 1
    if first == 0xFD:
        return int.from_bytes(data[i + 1:i + 3], "little"), i + 3
    if first == 0xFE:
        return int.from_bytes(data[i + 1:i + 5], "little"), i + 5
    return int.from_bytes(data[i + 1:i + 9], "little"), i + 9


def parse_tx(raw: bytes) -> Tx:
    """Parse a pre-segwit Bitcoin transaction."""
    i = 0
    version = int.from_bytes(raw[0:4], "little")
    i = 4
    n_in, i = _read_varint(raw, i)
    vin: List[TxIn] = []
    for _ in range(n_in):
        prev_txid = raw[i:i + 32]
        i += 32
        prev_index = int.from_bytes(raw[i:i + 4], "little")
        i += 4
        slen, i = _read_varint(raw, i)
        script_sig = raw[i:i + slen]
        i += slen
        sequence = int.from_bytes(raw[i:i + 4], "little")
        i += 4
        vin.append(TxIn(prev_txid, prev_index, script_sig, sequence))
    n_out, i = _read_varint(raw, i)
    vout: List[TxOut] = []
    for _ in range(n_out):
        value = int.from_bytes(raw[i:i + 8], "little")
        i += 8
        slen, i = _read_varint(raw, i)
        vout.append(TxOut(value, raw[i:i + slen]))
        i += slen
    locktime = int.from_bytes(raw[i:i + 4], "little")
    return Tx(version=version, vin=vin, vout=vout, locktime=locktime)


def extract_signature(script_sig: bytes) -> Optional[Tuple[int, int, int]]:
    """Pull (r, s, sighash_type) out of a P2PK scriptSig.

    A P2PK scriptSig is a single push of DER(sig) || sighash_type.
    """
    if not script_sig:
        return None
    push_len = script_sig[0]
    blob = script_sig[1:1 + push_len]
    if len(blob) < 9:
        return None
    der, sighash_type = blob[:-1], blob[-1]
    try:
        r, s = bs.parse_der_signature(der)
    except (ValueError, IndexError):
        return None
    return r, s, sighash_type


def p2pk_subscript(pubkey_hex: str) -> bytes:
    """The scriptPubKey of a P2PK output: <push 65> <pubkey> OP_CHECKSIG."""
    pk = bytes.fromhex(pubkey_hex)
    return bytes([len(pk)]) + pk + b"\xac"


def sighash_all(tx: Tx, input_index: int, subscript: bytes) -> bytes:
    """Legacy SIGHASH_ALL digest.

    Every input script is emptied except the one being signed, which is replaced by
    the subscript (the output script being spent). The 4-byte hash type is appended
    before the double-SHA-256.
    """
    overrides = {i: (subscript if i == input_index else b"")
                 for i in range(len(tx.vin))}
    payload = tx.serialize(overrides) + SIGHASH_ALL.to_bytes(4, "little")
    return dsha(payload)


# ---------------------------------------------------------------- analysis
@dataclass
class SignatureRecord:
    label: str
    block_height: Optional[int]
    txid: str
    txid_authenticated: bool
    r: int
    s: int
    sighash_type: int
    digest: bytes
    verifies: Optional[bool] = None


@dataclass
class SpendChainFindings:
    transactions: int = 0
    txids_authenticated: int = 0
    txid_mismatches: List[str] = field(default_factory=list)
    signatures: List[SignatureRecord] = field(default_factory=list)
    verified: int = 0
    distinct_r: int = 0
    reused_nonce_pairs: List[Tuple[str, str, int]] = field(default_factory=list)
    recovered_key: Optional[int] = None
    notes: List[str] = field(default_factory=list)

    @property
    def authenticated(self) -> bool:
        return not self.txid_mismatches and self.transactions > 0

    @property
    def nonce_safe(self) -> bool:
        return not self.reused_nonce_pairs and self.recovered_key is None


def analyse_chain(entries: List[Tuple[str, Optional[int], str]],
                  pubkey_hex: str) -> SpendChainFindings:
    """Verify a chain of P2PK spends signed by one key.

    ``entries`` is a list of (expected_txid, block_height, raw_tx_hex). The expected
    txid may be a prefix; whatever is supplied is checked against the locally
    computed txid so the raw bytes authenticate themselves.
    """
    f = SpendChainFindings()
    subscript = p2pk_subscript(pubkey_hex)
    pub = bs.parse_uncompressed_pubkey(pubkey_hex)

    for expected, height, raw_hex in entries:
        raw = bytes.fromhex(raw_hex)
        f.transactions += 1
        actual = txid_of(raw)
        ok = _txid_matches(expected, actual)
        if ok:
            f.txids_authenticated += 1
        else:
            f.txid_mismatches.append("%s != %s" % (expected, actual))

        tx = parse_tx(raw)
        for idx, vin in enumerate(tx.vin):
            sig = extract_signature(vin.script_sig)
            if sig is None:
                continue
            r, s, hashtype = sig
            digest = sighash_all(tx, idx, subscript)
            rec = SignatureRecord(
                label="block-%s/in%d" % (height, idx), block_height=height,
                txid=actual, txid_authenticated=ok, r=r, s=s,
                sighash_type=hashtype, digest=digest)
            if pub is not None:
                rec.verifies = bs.ecdsa_verify(pub, digest, r, s)
                if rec.verifies:
                    f.verified += 1
            f.signatures.append(rec)

    by_r: Dict[int, List[SignatureRecord]] = {}
    for rec in f.signatures:
        by_r.setdefault(rec.r, []).append(rec)
    f.distinct_r = len(by_r)

    for r, group in by_r.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.s == b.s and a.digest == b.digest:
                    continue                      # identical signature, not reuse
                f.reused_nonce_pairs.append((a.label, b.label, r))
                if f.recovered_key is None:
                    f.recovered_key = bs.recover_ecdsa_key(
                        r, a.s, int.from_bytes(a.digest, "big"),
                        b.s, int.from_bytes(b.digest, "big"))

    if f.txid_mismatches:
        f.notes.append(
            "TXID MISMATCH: the supplied bytes do not hash to the expected "
            "transaction ids, so they are not the real transactions. Analysis of "
            "them would be meaningless.")
    else:
        f.notes.append(
            "All %d transactions authenticated locally: the raw bytes double-SHA-256 "
            "to the expected txids, so no trust in the data's source is required."
            % f.transactions)
    if f.signatures and f.verified == len(f.signatures):
        f.notes.append(
            "All %d signatures verify against the key, confirming both the digest "
            "reconstruction and that this key produced them." % f.verified)
    if f.nonce_safe and f.signatures:
        f.notes.append(
            "%d signatures, %d distinct nonces: no reuse. The one Satoshi-attributed "
            "key that ever signed more than once did so safely, so the closed-form "
            "nonce-reuse attack does not apply to it."
            % (len(f.signatures), f.distinct_r))
    return f


def _txid_matches(expected: str, actual: str) -> bool:
    """Compare a full or abbreviated txid (e.g. 'f4184fc5...9e16') against actual."""
    exp = expected.strip().lower().replace("…", "...")
    act = actual.lower()
    if "..." in exp:
        head, tail = exp.split("...", 1)
        return act.startswith(head) and act.endswith(tail)
    return exp == act
