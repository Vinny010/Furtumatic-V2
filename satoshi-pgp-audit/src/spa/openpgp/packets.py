"""OpenPGP packet parsing (RFC 4880 s4, s5.2, s5.5).

Design rule for this module: parse everything, judge nothing, and never discard a
packet because it looks wrong. A keyserver copy of a famous key is an adversarial
input - anyone may append arbitrary signature packets to it - so the parser records
malformed packets as ``MalformedPacket`` and keeps going.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import constants as C
from .mpi import MPI, encode_mpi, read_mpi
from .subpackets import SubPacket, parse_subpackets

# Number of MPIs in a public key, by algorithm (RFC 4880 s5.5.2).
PUBKEY_MPI_COUNT = {1: 2, 2: 2, 3: 2, 16: 3, 17: 4, 20: 3}
PUBKEY_MPI_NAMES = {
    1: ("n", "e"), 2: ("n", "e"), 3: ("n", "e"),
    16: ("p", "g", "y"), 20: ("p", "g", "y"),
    17: ("p", "q", "g", "y"),
}
# Number of MPIs in a signature, by algorithm (RFC 4880 s5.2.2).
SIG_MPI_COUNT = {1: 1, 2: 1, 3: 1, 16: 2, 17: 2, 19: 2, 20: 2, 22: 2}
SIG_MPI_NAMES = {1: ("s",), 2: ("s",), 3: ("s",), 17: ("r", "s"),
                 19: ("r", "s"), 20: ("r", "s"), 22: ("r", "s"), 16: ("r", "s")}


@dataclass
class Packet:
    tag: int
    body: bytes
    offset: int
    header_len: int
    new_format: bool
    partial: bool = False

    @property
    def tag_name(self) -> str:
        return C.name_for(C.PACKET_TAGS, self.tag, "unknown-tag")

    @property
    def total_len(self) -> int:
        return self.header_len + len(self.body)


@dataclass
class MalformedPacket(Packet):
    error: str = ""


@dataclass
class PublicKeyPacket(Packet):
    version: int = 0
    created: int = 0
    validity_days: Optional[int] = None   # v3 only
    algo: int = 0
    mpis: Dict[str, MPI] = field(default_factory=dict)
    is_subkey: bool = False

    @property
    def algo_name(self) -> str:
        return C.name_for(C.PUBKEY_ALGOS, self.algo)

    @property
    def key_size_bits(self) -> int:
        """Nominal key size: modulus for RSA, p for DSA/Elgamal."""
        if self.algo in (1, 2, 3):
            return self.mpis["n"].declared_bits if "n" in self.mpis else 0
        return self.mpis["p"].declared_bits if "p" in self.mpis else 0

    def fingerprint_preimage(self) -> bytes:
        """RFC 4880 s12.2 - the exact byte string hashed to form the fingerprint."""
        if self.version == 4:
            body = self._v4_key_body()
            return b"\x99" + len(body).to_bytes(2, "big") + body
        if self.version == 3:
            # v3 fingerprints hash only the MPI bodies of n and e, without lengths.
            out = b""
            for name in PUBKEY_MPI_NAMES.get(self.algo, ()):  # pragma: no cover
                mpi = self.mpis[name]
                out += mpi.value.to_bytes((mpi.declared_bits + 7) // 8, "big")
            return out
        raise ValueError("unsupported key version %d" % self.version)

    def _v4_key_body(self) -> bytes:
        out = bytes([self.version]) + self.created.to_bytes(4, "big") + bytes([self.algo])
        for name in PUBKEY_MPI_NAMES.get(self.algo, ()):
            out += encode_mpi(self.mpis[name].value)
        return out

    def fingerprint(self) -> str:
        pre = self.fingerprint_preimage()
        digest = hashlib.sha1(pre).digest() if self.version == 4 else hashlib.md5(pre).digest()
        return digest.hex().upper()

    def key_id(self) -> str:
        if self.version == 4:
            return self.fingerprint()[-16:]
        n = self.mpis.get("n")
        if n is None:
            return ""
        return ("%x" % n.value).upper()[-16:]


@dataclass
class SignaturePacket(Packet):
    version: int = 0
    sig_type: int = 0
    pubkey_algo: int = 0
    hash_algo: int = 0
    created: Optional[int] = None          # v3: header field; v4: subpacket 2
    issuer_key_id: Optional[str] = None
    hashed_subpackets: List[SubPacket] = field(default_factory=list)
    unhashed_subpackets: List[SubPacket] = field(default_factory=list)
    hash_left16: bytes = b""
    mpis: Dict[str, MPI] = field(default_factory=dict)
    hashed_area: bytes = b""               # exact bytes covered by the signature

    @property
    def sig_type_name(self) -> str:
        return C.name_for(C.SIG_TYPES, self.sig_type, "unknown-sigtype")

    @property
    def hash_algo_name(self) -> str:
        return C.name_for(C.HASH_ALGOS, self.hash_algo)

    @property
    def pubkey_algo_name(self) -> str:
        return C.name_for(C.PUBKEY_ALGOS, self.pubkey_algo)

    def trailer(self) -> bytes:
        """The bytes of this signature packet that are themselves hashed (s5.2.4)."""
        if self.version == 4:
            head = (bytes([4, self.sig_type, self.pubkey_algo, self.hash_algo])
                    + len(self.hashed_area).to_bytes(2, "big") + self.hashed_area)
            return head + b"\x04\xff" + len(head).to_bytes(4, "big")
        if self.version == 3:
            return bytes([self.sig_type]) + (self.created or 0).to_bytes(4, "big")
        raise ValueError("unsupported signature version %d" % self.version)

    def subpacket(self, type_id: int, hashed_only: bool = True) -> Optional[SubPacket]:
        for sp in self.hashed_subpackets:
            if sp.type_id == type_id:
                return sp
        if not hashed_only:
            for sp in self.unhashed_subpackets:
                if sp.type_id == type_id:
                    return sp
        return None


@dataclass
class UserIDPacket(Packet):
    text: str = ""


@dataclass
class UserAttributePacket(Packet):
    subpacket_count: int = 0
    image_bytes: int = 0


def _read_header(data: bytes, i: int) -> Tuple[int, int, int, bool, bool]:
    """Return (tag, body_len, header_len, new_format, indeterminate)."""
    ctb = data[i]
    if not ctb & 0x80:
        raise ValueError("invalid packet header at offset %d (ctb=0x%02x)" % (i, ctb))
    if ctb & 0x40:  # new format (RFC 4880 s4.2.2)
        tag = ctb & 0x3F
        first = data[i + 1]
        if first < 192:
            return tag, first, 2, True, False
        if first < 224:
            return tag, ((first - 192) << 8) + data[i + 2] + 192, 3, True, False
        if first == 255:
            return tag, int.from_bytes(data[i + 2:i + 6], "big"), 6, True, False
        # Partial body length - only legal for data packets, never on a keyblock.
        return tag, 1 << (first & 0x1F), 2, True, True
    # Old format (RFC 4880 s4.2.1)
    tag = (ctb >> 2) & 0x0F
    ltype = ctb & 0x03
    if ltype == 0:
        return tag, data[i + 1], 2, False, False
    if ltype == 1:
        return tag, int.from_bytes(data[i + 1:i + 3], "big"), 3, False, False
    if ltype == 2:
        return tag, int.from_bytes(data[i + 1:i + 5], "big"), 5, False, False
    return tag, len(data) - i - 1, 1, False, True  # indeterminate length


def _parse_public_key(pkt: Packet) -> Packet:
    d = pkt.body
    version = d[0]
    created = int.from_bytes(d[1:5], "big")
    off = 5
    validity = None
    if version == 3:
        validity = int.from_bytes(d[5:7], "big")
        off = 7
    algo = d[off]
    off += 1
    mpis: Dict[str, MPI] = {}
    for name in PUBKEY_MPI_NAMES.get(algo, ()):
        mpi, off = read_mpi(d, off)
        mpis[name] = mpi
    return PublicKeyPacket(tag=pkt.tag, body=pkt.body, offset=pkt.offset,
                           header_len=pkt.header_len, new_format=pkt.new_format,
                           version=version, created=created, validity_days=validity,
                           algo=algo, mpis=mpis, is_subkey=pkt.tag == 14)


def _parse_signature(pkt: Packet) -> Packet:
    d = pkt.body
    version = d[0]
    if version in (2, 3):
        # v3: [ver][hashed material len=5][sigtype][created:4][keyid:8][pk][hash][left16]
        sig_type = d[2]
        created = int.from_bytes(d[3:7], "big")
        issuer = d[7:15].hex().upper()
        pubkey_algo, hash_algo = d[15], d[16]
        left16 = d[17:19]
        off = 19
        hashed_area = b""
        hashed_sp: List[SubPacket] = []
        unhashed_sp: List[SubPacket] = []
    elif version == 4:
        sig_type, pubkey_algo, hash_algo = d[1], d[2], d[3]
        hlen = int.from_bytes(d[4:6], "big")
        hashed_area = d[6:6 + hlen]
        hashed_sp = parse_subpackets(hashed_area, True, 6)
        off = 6 + hlen
        ulen = int.from_bytes(d[off:off + 2], "big")
        unhashed_area = d[off + 2:off + 2 + ulen]
        unhashed_sp = parse_subpackets(unhashed_area, False, off + 2)
        off += 2 + ulen
        left16 = d[off:off + 2]
        off += 2
        created = None
        issuer = None
        for sp in hashed_sp:
            if sp.type_id == 2 and created is None:
                created = int.from_bytes(sp.data, "big")
        for sp in list(hashed_sp) + list(unhashed_sp):
            if sp.type_id == 16 and issuer is None:
                issuer = sp.data.hex().upper()
            elif sp.type_id == 33 and issuer is None and len(sp.data) >= 21:
                issuer = sp.data[1:].hex().upper()[-16:]
    else:
        raise ValueError("unsupported signature version %d" % version)

    mpis: Dict[str, MPI] = {}
    for name in SIG_MPI_NAMES.get(pubkey_algo, ()):
        mpi, off = read_mpi(d, off)
        mpis[name] = mpi
    return SignaturePacket(
        tag=pkt.tag, body=pkt.body, offset=pkt.offset, header_len=pkt.header_len,
        new_format=pkt.new_format, version=version, sig_type=sig_type,
        pubkey_algo=pubkey_algo, hash_algo=hash_algo, created=created,
        issuer_key_id=issuer, hashed_subpackets=hashed_sp,
        unhashed_subpackets=unhashed_sp, hash_left16=left16, mpis=mpis,
        hashed_area=hashed_area)


def _parse_user_attribute(pkt: Packet) -> Packet:
    subs = parse_subpackets(pkt.body, False)
    img = sum(len(s.data) for s in subs if s.type_id == 1)
    return UserAttributePacket(tag=pkt.tag, body=pkt.body, offset=pkt.offset,
                               header_len=pkt.header_len, new_format=pkt.new_format,
                               subpacket_count=len(subs), image_bytes=img)


_DISPATCH = {
    2: _parse_signature,
    6: _parse_public_key,
    14: _parse_public_key,
    17: _parse_user_attribute,
}


def parse_packets(data: bytes) -> List[Packet]:
    """Parse a packet stream. Malformed packets become MalformedPacket, never an
    exception - the audit needs to see them, and a raise would let one spam packet
    hide the other 224."""
    out: List[Packet] = []
    i = 0
    n = len(data)
    while i < n:
        try:
            tag, blen, hlen, newfmt, indet = _read_header(data, i)
        except (ValueError, IndexError) as exc:
            out.append(MalformedPacket(tag=-1, body=data[i:], offset=i, header_len=0,
                                       new_format=False, error=str(exc)))
            break
        body = data[i + hlen:i + hlen + blen]
        base = Packet(tag=tag, body=body, offset=i, header_len=hlen,
                      new_format=newfmt, partial=indet)
        if len(body) < blen:
            out.append(MalformedPacket(tag=tag, body=body, offset=i, header_len=hlen,
                                       new_format=newfmt,
                                       error="truncated body: declared %d, got %d"
                                             % (blen, len(body))))
            break
        if tag == 13:
            out.append(UserIDPacket(tag=tag, body=body, offset=i, header_len=hlen,
                                    new_format=newfmt,
                                    text=body.decode("utf-8", "replace")))
        elif tag in _DISPATCH:
            try:
                out.append(_DISPATCH[tag](base))
            except Exception as exc:
                out.append(MalformedPacket(tag=tag, body=body, offset=i,
                                           header_len=hlen, new_format=newfmt,
                                           error="%s: %s" % (type(exc).__name__, exc)))
        else:
            out.append(base)
        i += hlen + blen
    return out
