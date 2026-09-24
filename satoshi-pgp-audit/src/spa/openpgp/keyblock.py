"""Assemble a flat packet stream into a transferable public key (RFC 4880 s11.1),
and reconstruct the exact byte strings that each signature commits to.

Reconstructing the signed preimage is what makes the DSA analysis possible: a
signature gives (r, s), but the nonce relation k = s^-1 (h + x*r) mod q also needs h,
and h is only obtainable by rebuilding the hashed data exactly as the signer did.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import constants as C
from .packets import (MalformedPacket, Packet, PublicKeyPacket, SignaturePacket,
                      UserAttributePacket, UserIDPacket, parse_packets)

_HASH_CTOR = {1: hashlib.md5, 2: hashlib.sha1, 3: None, 8: hashlib.sha256,
              9: hashlib.sha384, 10: hashlib.sha512, 11: hashlib.sha224}


def _hasher(algo: int):
    if algo == 3:  # RIPEMD-160 - not guaranteed present in hashlib builds
        try:
            return hashlib.new("ripemd160")
        except (ValueError, TypeError):
            from ..lab.rmd160 import RMD160Hashlib
            return RMD160Hashlib()
    ctor = _HASH_CTOR.get(algo)
    if ctor is None:
        raise ValueError("unsupported hash algorithm %d" % algo)
    return ctor()


def _key_hash_prefix(key: PublicKeyPacket) -> bytes:
    body = key._v4_key_body() if key.version == 4 else key.body
    return b"\x99" + len(body).to_bytes(2, "big") + body


@dataclass
class Certification:
    """One signature together with the object it was made over."""
    sig: SignaturePacket
    target_kind: str                 # 'uid' | 'uattr' | 'subkey' | 'direct'
    target_index: int
    target_repr: str

    @property
    def is_self_sig_by_keyid(self) -> bool:
        return self._issuer_matches

    _issuer_matches: bool = False


@dataclass
class SubKey:
    key: PublicKeyPacket
    signatures: List[SignaturePacket] = field(default_factory=list)


@dataclass
class UserID:
    packet: Packet
    text: str
    signatures: List[SignaturePacket] = field(default_factory=list)


@dataclass
class KeyBlock:
    primary: PublicKeyPacket
    uids: List[UserID] = field(default_factory=list)
    subkeys: List[SubKey] = field(default_factory=list)
    direct_signatures: List[SignaturePacket] = field(default_factory=list)
    malformed: List[MalformedPacket] = field(default_factory=list)
    all_packets: List[Packet] = field(default_factory=list)

    # ---- identity -------------------------------------------------------
    @property
    def fingerprint(self) -> str:
        return self.primary.fingerprint()

    @property
    def key_id(self) -> str:
        return self.primary.key_id()

    def all_signatures(self) -> List[SignaturePacket]:
        out = list(self.direct_signatures)
        for u in self.uids:
            out.extend(u.signatures)
        for s in self.subkeys:
            out.extend(s.signatures)
        return out

    def self_signatures(self) -> List[SignaturePacket]:
        """Signatures whose issuer key id equals this key's.

        This is an *unauthenticated* filter based on the issuer subpacket; a signature
        only becomes a verified self-signature once it passes DSA verification against
        the primary key. spa.analysis.dsa performs that step.
        """
        kid = self.key_id
        return [s for s in self.all_signatures() if s.issuer_key_id == kid]

    # ---- signed-preimage reconstruction ---------------------------------
    def signed_data(self, sig: SignaturePacket) -> Optional[bytes]:
        """Rebuild the byte string this signature commits to, or None if the
        signature type is not one made over material in this keyblock."""
        prefix = _key_hash_prefix(self.primary)
        st = sig.sig_type
        if st in (0x10, 0x11, 0x12, 0x13, 0x30):  # certifications over a user id
            target = self._target_for(sig)
            if target is None:
                return None
            if isinstance(target, UserID):
                data = target.packet.body
                if sig.version == 4:
                    mid = b"\xb4" + len(data).to_bytes(4, "big") + data
                else:
                    mid = data
            else:  # user attribute
                data = target.body
                mid = b"\xd1" + len(data).to_bytes(4, "big") + data
            return prefix + mid + sig.trailer()
        if st in (0x18, 0x28, 0x19):  # subkey binding / revocation / primary binding
            sub = self._subkey_for(sig)
            if sub is None:
                return None
            return prefix + _key_hash_prefix(sub.key) + sig.trailer()
        if st in (0x1F, 0x20):  # direct key signature / key revocation
            return prefix + sig.trailer()
        return None

    def _target_for(self, sig: SignaturePacket):
        for u in self.uids:
            if sig in u.signatures:
                return u
        for p in self.all_packets:
            if isinstance(p, UserAttributePacket):
                return p
        return None

    def _subkey_for(self, sig: SignaturePacket) -> Optional[SubKey]:
        for s in self.subkeys:
            if sig in s.signatures:
                return s
        return None

    def digest_for(self, sig: SignaturePacket) -> Optional[bytes]:
        """The full message digest this signature was computed over."""
        data = self.signed_data(sig)
        if data is None:
            return None
        try:
            h = _hasher(sig.hash_algo)
        except ValueError:
            return None
        h.update(data)
        return h.digest()

    def digest_matches_left16(self, sig: SignaturePacket) -> Optional[bool]:
        """Cheap integrity check: OpenPGP stores the top 2 bytes of the digest in
        cleartext, so a reconstruction error is caught without any public-key math."""
        d = self.digest_for(sig)
        if d is None:
            return None
        return d[:2] == sig.hash_left16


def parse_keyblock(data: bytes) -> KeyBlock:
    packets = parse_packets(data)
    primary = None
    for p in packets:
        if isinstance(p, PublicKeyPacket) and p.tag == 6:
            primary = p
            break
    if primary is None:
        raise ValueError("no primary public-key packet found")

    kb = KeyBlock(primary=primary, all_packets=packets)
    context = "direct"
    cur_uid: Optional[UserID] = None
    cur_sub: Optional[SubKey] = None
    for p in packets:
        if isinstance(p, MalformedPacket):
            kb.malformed.append(p)
        elif isinstance(p, PublicKeyPacket) and p.tag == 6:
            context = "direct"
        elif isinstance(p, PublicKeyPacket) and p.tag == 14:
            cur_sub = SubKey(key=p)
            kb.subkeys.append(cur_sub)
            context = "subkey"
        elif isinstance(p, UserIDPacket):
            cur_uid = UserID(packet=p, text=p.text)
            kb.uids.append(cur_uid)
            context = "uid"
        elif isinstance(p, UserAttributePacket):
            cur_uid = UserID(packet=p, text="<user attribute: %d bytes image>" % p.image_bytes)
            kb.uids.append(cur_uid)
            context = "uid"
        elif isinstance(p, SignaturePacket):
            if context == "uid" and cur_uid is not None:
                cur_uid.signatures.append(p)
            elif context == "subkey" and cur_sub is not None:
                cur_sub.signatures.append(p)
            else:
                kb.direct_signatures.append(p)
    return kb
