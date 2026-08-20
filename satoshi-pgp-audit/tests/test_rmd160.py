"""RIPEMD-160 correctness and GnuPG's non-standard mixblock semantics."""
import struct

import pytest

from spa.lab.rmd160 import RMD160Context, mixblock, rmd160, transform

# Official RIPEMD-160 test vectors.
VECTORS = [
    (b"", "9c1185a5c5e9fc54612808977ee8f548b2258d31"),
    (b"a", "0bdc9d2d256b3ee9daae347be6f4dc835a467ffe"),
    (b"abc", "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc"),
    (b"message digest", "5d0689ef49d2fae572b881b123a85ffa21595f36"),
    (b"abcdefghijklmnopqrstuvwxyz", "f71c27109c692c1b56bbdceb5b9d2865b3708dbc"),
    (b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
     "b0e20b6e3116640286ed3a87a5713079b21f5189"),
    (b"1234567890" * 8, "9b752e45573d4b39f4dbd3323cab82bf63326bfb"),
]


@pytest.mark.parametrize("data,expected", VECTORS)
def test_rmd160_vectors(data, expected):
    assert rmd160(data).hex() == expected


def test_mixblock_exports_chaining_state():
    """The property the whole CVE rests on: mixblock writes the chaining state
    into the caller's buffer, so pool contents ARE hash state."""
    ctx = RMD160Context()
    buf = bytearray(range(64))
    mixblock(ctx, buf)
    assert bytes(buf[:20]) == struct.pack("<5I", *ctx.h)


def test_mixblock_chains_across_calls():
    """State must persist between calls - mix_pool depends on it."""
    ctx = RMD160Context()
    a = bytearray(b"\x00" * 64)
    mixblock(ctx, a)
    first = bytes(a[:20])
    b = bytearray(b"\x00" * 64)
    mixblock(ctx, b)
    assert bytes(b[:20]) != first


def test_transform_rejects_wrong_length():
    with pytest.raises(ValueError):
        transform(RMD160Context(), b"short")
