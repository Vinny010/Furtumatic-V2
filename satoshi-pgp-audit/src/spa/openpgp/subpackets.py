"""Signature subpacket parsing (RFC 4880 s5.2.3)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from . import constants as C


@dataclass
class SubPacket:
    type_id: int
    critical: bool
    data: bytes
    hashed: bool
    offset: int

    @property
    def name(self) -> str:
        return C.name_for(C.SIG_SUBPACKET_TYPES, self.type_id, "unknown-subpacket")

    def decode(self) -> Dict[str, Any]:
        """Best-effort structured decode. Unknown types return their raw hex."""
        t, d = self.type_id, self.data
        try:
            if t in (2, 3, 9):  # time values (creation, sig expiry, key expiry)
                return {"seconds": int.from_bytes(d, "big")}
            if t == 16:  # issuer key id
                return {"key_id": d.hex().upper()}
            if t == 33:  # issuer fingerprint
                return {"version": d[0], "fingerprint": d[1:].hex().upper()}
            if t in (4, 7, 25):  # boolean flags
                return {"value": bool(d[0])}
            if t == 11:
                return {"algorithms": [C.name_for(C.SYM_ALGOS, b) for b in d]}
            if t == 21:
                return {"algorithms": [C.name_for(C.HASH_ALGOS, b) for b in d]}
            if t == 22:
                return {"algorithms": [C.name_for(C.COMPRESSION_ALGOS, b) for b in d]}
            if t == 27:  # key flags
                flags = d[0] if d else 0
                return {"raw": flags,
                        "flags": [n for bit, n in C.KEY_FLAGS.items() if flags & bit]}
            if t == 30:
                return {"raw": d[0] if d else 0,
                        "mdc": bool(d and d[0] & 0x01)}
            if t == 23:
                return {"raw": d[0] if d else 0,
                        "no_modify": bool(d and d[0] & 0x80)}
            if t in (6, 24, 26, 28):  # textual
                return {"text": d.decode("utf-8", "replace")}
            if t == 5:  # trust signature
                return {"level": d[0], "amount": d[1]}
            if t == 29:  # reason for revocation
                return {"code": d[0],
                        "reason": d[1:].decode("utf-8", "replace")}
            if t == 20:  # notation
                flags = int.from_bytes(d[0:4], "big")
                nlen = int.from_bytes(d[4:6], "big")
                vlen = int.from_bytes(d[6:8], "big")
                return {"human_readable": bool(flags & 0x80000000),
                        "name": d[8:8 + nlen].decode("utf-8", "replace"),
                        "value": d[8 + nlen:8 + nlen + vlen].decode("utf-8", "replace")}
        except Exception as exc:  # malformed subpacket in keyserver spam
            return {"decode_error": str(exc), "hex": d.hex()}
        return {"hex": d.hex()}


def parse_subpackets(data: bytes, hashed: bool, base_offset: int = 0) -> List[SubPacket]:
    """Parse a subpacket area. Stops cleanly on truncation rather than raising."""
    out: List[SubPacket] = []
    i = 0
    n = len(data)
    while i < n:
        start = i
        first = data[i]
        if first < 192:
            length = first
            i += 1
        elif first < 255:
            if i + 2 > n:
                break
            length = ((first - 192) << 8) + data[i + 1] + 192
            i += 2
        else:
            if i + 5 > n:
                break
            length = int.from_bytes(data[i + 1:i + 5], "big")
            i += 5
        if length == 0 or i + length > n:
            break
        type_octet = data[i]
        body = data[i + 1:i + length]
        out.append(SubPacket(type_id=type_octet & 0x7F,
                             critical=bool(type_octet & 0x80),
                             data=body, hashed=hashed,
                             offset=base_offset + start))
        i += length
    return out
