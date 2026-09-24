"""ASCII armor handling (RFC 4880 s6).

Deliberately does NOT use the stdlib-adjacent shortcuts, because one of the audit
questions is about the armor *headers* themselves - specifically the ``Version:``
header, which is where the "GnuPG v1.4.7 (MingW32)" attribution lives. That header is
not covered by any signature and not part of the key's fingerprint, so it must be
surfaced as separate, explicitly unauthenticated metadata rather than silently dropped.
"""

import base64
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_BEGIN = re.compile(r"^-----BEGIN PGP ([A-Z0-9 ,]+)-----\s*$")
_END = re.compile(r"^-----END PGP ([A-Z0-9 ,]+)-----\s*$")
_HEADER = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s?(.*)$")

CRC24_INIT = 0x0B704CE
CRC24_POLY = 0x1864CFB


class ArmorError(ValueError):
    pass


def crc24(data: bytes) -> int:
    """RFC 4880 s6.1 reference CRC-24."""
    crc = CRC24_INIT
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= CRC24_POLY
    return crc & 0xFFFFFF


@dataclass
class ArmoredBlock:
    kind: str
    body: bytes
    headers: Dict[str, str] = field(default_factory=dict)
    crc_present: bool = False
    crc_ok: Optional[bool] = None

    @property
    def version_header(self) -> Optional[str]:
        """The unauthenticated producer string, if the armor carried one.

        Returns None for material that has passed through a keyserver, which rewrites
        this header to its own software name.
        """
        for k, v in self.headers.items():
            if k.lower() == "version":
                return v
        return None


def dearmor(text: str) -> List[ArmoredBlock]:
    """Extract every armored block in ``text``.

    Returns blocks in document order. A block with a corrupt CRC is still returned,
    with ``crc_ok=False``, so the caller can decide - an audit tool that silently drops
    malformed input is worse than useless.
    """
    blocks: List[ArmoredBlock] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _BEGIN.match(lines[i])
        if not m:
            i += 1
            continue
        kind = m.group(1)
        i += 1
        headers: Dict[str, str] = {}
        # Armor headers run until the first blank line.
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                break
            hm = _HEADER.match(line)
            if not hm:
                break
            headers[hm.group(1)] = hm.group(2).strip()
            i += 1
        b64_parts: List[str] = []
        crc_b64: Optional[str] = None
        closed = False
        while i < len(lines):
            line = lines[i].strip()
            if _END.match(lines[i]):
                closed = True
                i += 1
                break
            if line.startswith("="):
                crc_b64 = line[1:]
            elif line:
                b64_parts.append(line)
            i += 1
        if not closed:
            raise ArmorError("unterminated armor block: %s" % kind)
        try:
            body = base64.b64decode("".join(b64_parts), validate=True)
        except Exception as exc:
            raise ArmorError("bad base64 in %s block: %s" % (kind, exc)) from exc
        crc_ok = None
        if crc_b64:
            try:
                raw = base64.b64decode(crc_b64 + "==", validate=False)[:3]
                declared = int.from_bytes(raw, "big")
                crc_ok = declared == crc24(body)
            except Exception:
                crc_ok = False
        blocks.append(ArmoredBlock(kind=kind, body=body, headers=headers,
                                   crc_present=crc_b64 is not None, crc_ok=crc_ok))
    if not blocks:
        raise ArmorError("no PGP armor found")
    return blocks
