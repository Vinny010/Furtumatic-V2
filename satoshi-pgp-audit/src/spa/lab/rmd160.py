"""RIPEMD-160, plus the exact ``rmd160_mixblock`` primitive from GnuPG 1.4.7.

Why reimplement a hash that hashlib may already provide: GnuPG's entropy pool does
not call a normal hash API. cipher/rmd160.c exposes

    void rmd160_mixblock (RMD160_CONTEXT *hd, char *buffer)
    {
        transform (hd, buffer);          /* absorb 64 bytes, NO padding, NO length */
        /* then overwrite buffer[0..19] with the raw chaining variables h0..h4,
           little-endian */
    }

That is a raw compression-function call with the chaining state exported in the
clear. It is not RIPEMD-160 of anything - there is no padding and no length suffix,
and the state persists across calls. Modelling mix_pool() faithfully therefore
requires the compression function itself, which no standard API exposes.

Cross-checked against the RIPEMD-160 test vectors in tests/test_rmd160.py.
"""

import struct
from typing import List

_IV = (0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0)

# Message word order, left and right lines (from the RIPEMD-160 specification).
_RL = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14, 11, 8,
    3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12,
    1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15, 14, 5, 6, 2,
    4, 0, 5, 9, 7, 12, 2, 10, 14, 1, 3, 8, 11, 6, 15, 13,
]
_RR = [
    5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12,
    6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9, 1, 2,
    15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13,
    8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9, 7, 10, 14,
    12, 15, 10, 4, 1, 5, 8, 7, 6, 2, 13, 14, 0, 3, 9, 11,
]
_SL = [
    11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8,
    7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7, 13, 12,
    11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5,
    11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5, 6, 8, 6, 5, 12,
    9, 15, 5, 11, 6, 8, 13, 12, 5, 12, 13, 14, 11, 8, 5, 6,
]
_SR = [
    8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6,
    9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15, 13, 11,
    9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5,
    15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12, 9, 12, 5, 15, 8,
    8, 5, 12, 9, 12, 5, 14, 6, 8, 13, 6, 5, 15, 13, 11, 11,
]
_KL = [0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E]
_KR = [0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0x00000000]

_MASK = 0xFFFFFFFF


def _rol(x: int, n: int) -> int:
    x &= _MASK
    return ((x << n) | (x >> (32 - n))) & _MASK


def _f(j: int, x: int, y: int, z: int) -> int:
    if j < 16:
        return x ^ y ^ z
    if j < 32:
        return (x & y) | (~x & _MASK & z)
    if j < 48:
        return (x | (~y & _MASK)) ^ z
    if j < 64:
        return (x & z) | (y & (~z & _MASK))
    return x ^ (y | (~z & _MASK))


class RMD160Context:
    """Mirrors GnuPG's RMD160_CONTEXT: chaining variables plus a byte counter."""

    __slots__ = ("h", "nblocks", "buf")

    def __init__(self) -> None:
        self.h: List[int] = list(_IV)
        self.nblocks = 0
        self.buf = b""

    def copy(self) -> "RMD160Context":
        c = RMD160Context()
        c.h = list(self.h)
        c.nblocks = self.nblocks
        c.buf = self.buf
        return c


def transform(ctx: RMD160Context, block: bytes) -> None:
    """The RIPEMD-160 compression function applied to one 64-byte block."""
    if len(block) != 64:
        raise ValueError("transform needs exactly 64 bytes, got %d" % len(block))
    x = list(struct.unpack("<16I", block))
    al, bl, cl, dl, el = ctx.h
    ar, br, cr, dr, er = ctx.h
    for j in range(80):
        rnd = j // 16
        t = (al + _f(j, bl, cl, dl) + x[_RL[j]] + _KL[rnd]) & _MASK
        t = (_rol(t, _SL[j]) + el) & _MASK
        al, bl, cl, dl, el = el, t, bl, _rol(cl, 10), dl
        t = (ar + _f(79 - j, br, cr, dr) + x[_RR[j]] + _KR[rnd]) & _MASK
        t = (_rol(t, _SR[j]) + er) & _MASK
        ar, br, cr, dr, er = er, t, br, _rol(cr, 10), dr
    h = ctx.h
    t = (h[1] + cl + dr) & _MASK
    h[1] = (h[2] + dl + er) & _MASK
    h[2] = (h[3] + el + ar) & _MASK
    h[3] = (h[4] + al + br) & _MASK
    h[4] = (h[0] + bl + cr) & _MASK
    h[0] = t
    ctx.nblocks += 1


def mixblock(ctx: RMD160Context, buffer: bytearray) -> None:
    """GnuPG cipher/rmd160.c :: rmd160_mixblock.

    Absorbs ``buffer`` (64 bytes) into the persistent chaining state, then writes the
    five chaining variables back over the first 20 bytes of ``buffer``, little-endian.
    Mutates ``buffer`` in place, exactly as the C code does.
    """
    transform(ctx, bytes(buffer[:64]))
    buffer[0:20] = struct.pack("<5I", *ctx.h)


def rmd160(data: bytes) -> bytes:
    """Standard RIPEMD-160, used to validate ``transform`` against test vectors."""
    ctx = RMD160Context()
    n = len(data)
    i = 0
    while n - i >= 64:
        transform(ctx, data[i:i + 64])
        i += 64
    tail = bytearray(data[i:])
    bitlen = n * 8
    tail.append(0x80)
    while len(tail) % 64 != 56:
        tail.append(0)
    tail += struct.pack("<Q", bitlen)
    for j in range(0, len(tail), 64):
        transform(ctx, bytes(tail[j:j + 64]))
    return struct.pack("<5I", *ctx.h)


class RMD160Hashlib:
    """Minimal hashlib-compatible shim, for builds without OpenSSL RIPEMD-160."""

    name = "ripemd160"
    digest_size = 20
    block_size = 64

    def __init__(self, data: bytes = b"") -> None:
        self._data = bytearray(data)

    def update(self, data: bytes) -> None:
        self._data += data

    def digest(self) -> bytes:
        return rmd160(bytes(self._data))

    def hexdigest(self) -> str:
        return self.digest().hex()

    def copy(self) -> "RMD160Hashlib":
        return RMD160Hashlib(bytes(self._data))
