"""Faithful model of GnuPG's entropy pool (cipher/random.c), 1.4.7 and 1.4.21.

Line-for-line port of the C, kept deliberately un-Pythonic so it can be diffed
against the original by eye. The two ``mix_pool`` variants are the entire subject of
CVE-2016-6313.

    GnuPG 1.4.7  cipher/random.c  (tag gnupg-1.4.7,  commit 7cb81bb)
    GnuPG 1.4.21 cipher/random.c  (tag gnupg-1.4.21)

THE DIFFERENCE
--------------
Both versions mix a 600-byte pool as 30 blocks of 20 bytes, chaining one persistent
RIPEMD-160 state across all 30 compression calls. Iteration 0 is identical in both.
Iterations 1..29 differ in which 64 bytes get absorbed:

    1.4.7  (buggy)  hashbuf = pool[20(n-1) : 20n]  ||  pool[20n+20 : 20n+64]
                                                       ^^^^^^^^ skips 20 bytes
    1.4.21 (fixed)  hashbuf = pool[20(n-1) : 20(n-1)+64]      (64 contiguous bytes)

In 1.4.7 the 20 bytes at pool[20n:20n+20] - precisely the bytes about to be
overwritten by this iteration - are absent from this iteration's hash input. The
fixed version absorbs a block immediately before replacing it. The consequence is
that the 1.4.7 update function carries less of the old pool forward into each new
block than the design intends, which is what the 160-bits-from-4640-bits result
quantifies.

WORD SIZE MATTERS
-----------------
read_pool() derives the keypool with ``*dp = *sp + ADD_VALUE`` over ``unsigned long``.
That is 4 bytes on the MingW32 build the historical record attributes to this key,
and 8 bytes on a 64-bit Unix build, with a different ADD_VALUE constant. The two
produce DIFFERENT output from identical pool state, so the word size is a required
parameter of any faithful reproduction, not an implementation detail.
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional

from .rmd160 import RMD160Context, mixblock

BLOCKLEN = 64
DIGESTLEN = 20
POOLBLOCKS = 30
POOLSIZE = POOLBLOCKS * DIGESTLEN          # 600
ADD_VALUE_32 = 0xA5A5A5A5
ADD_VALUE_64 = 0xA5A5A5A5A5A5A5A5


def mix_pool_147(pool: bytearray) -> None:
    """GnuPG 1.4.7 mix_pool() - the version carrying CVE-2016-6313.

    ``pool`` must be POOLSIZE+BLOCKLEN bytes; the trailing BLOCKLEN bytes are the
    ``hashbuf`` scratch area, exactly as in the C allocation.
    """
    hb = POOLSIZE                    # offset of hashbuf within the allocation
    md = RMD160Context()
    pend = POOLSIZE

    # memcpy(hashbuf, pend-DIGESTLEN, DIGESTLEN);
    pool[hb:hb + DIGESTLEN] = pool[pend - DIGESTLEN:pend]
    # memcpy(hashbuf+DIGESTLEN, pool, BLOCKLEN-DIGESTLEN);
    pool[hb + DIGESTLEN:hb + BLOCKLEN] = pool[0:BLOCKLEN - DIGESTLEN]
    buf = bytearray(pool[hb:hb + BLOCKLEN])
    mixblock(md, buf)
    pool[hb:hb + BLOCKLEN] = buf
    # memcpy(pool, hashbuf, 20);
    pool[0:DIGESTLEN] = pool[hb:hb + DIGESTLEN]

    p = 0
    for _n in range(1, POOLBLOCKS):
        # memcpy(hashbuf, p, DIGESTLEN);
        pool[hb:hb + DIGESTLEN] = pool[p:p + DIGESTLEN]
        p += DIGESTLEN
        if p + DIGESTLEN + BLOCKLEN < pend:
            # memcpy(hashbuf+DIGESTLEN, p+DIGESTLEN, BLOCKLEN-DIGESTLEN);
            src = p + DIGESTLEN
            pool[hb + DIGESTLEN:hb + BLOCKLEN] = pool[src:src + BLOCKLEN - DIGESTLEN]
        else:
            pp = p + DIGESTLEN
            for i in range(DIGESTLEN, BLOCKLEN):
                if pp >= pend:
                    pp = 0
                pool[hb + i] = pool[pp]
                pp += 1
        buf = bytearray(pool[hb:hb + BLOCKLEN])
        mixblock(md, buf)
        pool[hb:hb + BLOCKLEN] = buf
        # memcpy(p, hashbuf, 20);
        pool[p:p + DIGESTLEN] = pool[hb:hb + DIGESTLEN]


def mix_pool_1421(pool: bytearray) -> None:
    """GnuPG 1.4.21 mix_pool() - the fixed version."""
    hb = POOLSIZE
    md = RMD160Context()
    pend = POOLSIZE

    pool[hb:hb + DIGESTLEN] = pool[pend - DIGESTLEN:pend]
    pool[hb + DIGESTLEN:hb + BLOCKLEN] = pool[0:BLOCKLEN - DIGESTLEN]
    buf = bytearray(pool[hb:hb + BLOCKLEN])
    mixblock(md, buf)
    pool[hb:hb + BLOCKLEN] = buf
    pool[0:DIGESTLEN] = pool[hb:hb + DIGESTLEN]

    p = 0
    for _n in range(1, POOLBLOCKS):
        if p + BLOCKLEN < pend:
            pool[hb:hb + BLOCKLEN] = pool[p:p + BLOCKLEN]
        else:
            pp = p
            for i in range(BLOCKLEN):
                if pp >= pend:
                    pp = 0
                pool[hb + i] = pool[pp]
                pp += 1
        buf = bytearray(pool[hb:hb + BLOCKLEN])
        mixblock(md, buf)
        pool[hb:hb + BLOCKLEN] = buf
        p += DIGESTLEN
        pool[p:p + DIGESTLEN] = pool[hb:hb + DIGESTLEN]


MIXERS = {"1.4.7": mix_pool_147, "1.4.21": mix_pool_1421}


@dataclass
class GnuPGRandom:
    """The pool half of GnuPG's RNG.

    Entropy *gathering* (rndw32.c / rndlinux.c) is deliberately NOT modelled: it is
    OS-specific, unreproducible 18 years later, and irrelevant to the mixing defect.
    Seed material is injected explicitly via add_randomness(), which is what makes
    the experiments controlled.
    """

    variant: str = "1.4.7"
    word_size: int = 4                 # 4 = MingW32/32-bit, 8 = 64-bit Unix
    pool: bytearray = field(default_factory=lambda: bytearray(POOLSIZE + BLOCKLEN))
    keypool: bytearray = field(default_factory=lambda: bytearray(POOLSIZE + BLOCKLEN))
    pool_readpos: int = 0
    pool_writepos: int = 0
    pool_filled: bool = False
    just_mixed: bool = False
    mix_count: int = 0

    def __post_init__(self) -> None:
        if self.variant not in MIXERS:
            raise ValueError("unknown variant %r" % self.variant)
        if self.word_size not in (4, 8):
            raise ValueError("word_size must be 4 or 8")

    @property
    def _mix(self):
        return MIXERS[self.variant]

    def _mix_pool(self, pool: bytearray) -> None:
        self._mix(pool)
        self.mix_count += 1

    # ---- cipher/random.c :: add_randomness ------------------------------
    def add_randomness(self, buf: bytes, source: int = 2) -> None:
        for byte in buf:
            self.pool[self.pool_writepos] ^= byte
            self.pool_writepos += 1
            if self.pool_writepos >= POOLSIZE:
                if source > 1:
                    self.pool_filled = True
                self.pool_writepos = 0
                self._mix_pool(self.pool)
                self.just_mixed = True

    # ---- cipher/random.c :: read_pool -----------------------------------
    def _derive_keypool(self) -> None:
        """for (i=0; i<POOLWORDS; i++) *dp = *sp + ADD_VALUE;

        Native-endian modular addition per machine word, no carry between words.
        """
        ws = self.word_size
        add = ADD_VALUE_32 if ws == 4 else ADD_VALUE_64
        mask = (1 << (ws * 8)) - 1
        fmt = "<I" if ws == 4 else "<Q"
        for off in range(0, POOLSIZE, ws):
            (word,) = struct.unpack_from(fmt, self.pool, off)
            struct.pack_into(fmt, self.keypool, off, (word + add) & mask)

    def read_pool(self, length: int, level: int = 1) -> bytes:
        if length > POOLSIZE:
            raise ValueError("too many random bits requested")
        if not self.pool_filled:
            raise RuntimeError(
                "pool not seeded - call add_randomness() first. GnuPG would block "
                "here gathering OS entropy; the lab requires explicit seeding so "
                "experiments stay reproducible.")
        if level == 0:
            self._derive_keypool()
            self._mix_pool(self.pool)
            self._mix_pool(self.keypool)
            return bytes(self.keypool[:length])

        if not self.just_mixed:
            self._mix_pool(self.pool)
        self.just_mixed = False
        self._derive_keypool()
        self._mix_pool(self.pool)
        self._mix_pool(self.keypool)
        out = bytearray()
        for _ in range(length):
            out.append(self.keypool[self.pool_readpos])
            self.pool_readpos += 1
            if self.pool_readpos >= POOLSIZE:
                self.pool_readpos = 0
        for i in range(POOLSIZE):        # wipememory(keypool, POOLSIZE)
            self.keypool[i] = 0
        return bytes(out)

    def get_random_bytes(self, n: int, level: int = 1) -> bytes:
        out = bytearray()
        while len(out) < n:
            chunk = min(POOLSIZE, n - len(out))
            out += self.read_pool(chunk, level)
        return bytes(out)

    # ---- lab-only introspection -----------------------------------------
    def snapshot_pool(self) -> bytes:
        """Internal pool state.

        NOT available to any attacker who only has a public key. Every experiment
        that calls this is, by construction, in the 'requires internal state'
        evidentiary category.
        """
        return bytes(self.pool[:POOLSIZE])

    def set_pool(self, data: bytes) -> None:
        if len(data) != POOLSIZE:
            raise ValueError("pool must be exactly %d bytes" % POOLSIZE)
        self.pool[:POOLSIZE] = data
        self.pool_filled = True


def fresh(variant: str = "1.4.7", seed: bytes = b"", word_size: int = 4) -> GnuPGRandom:
    """A seeded generator for experiments."""
    g = GnuPGRandom(variant=variant, word_size=word_size)
    if seed:
        g.add_randomness(seed * ((POOLSIZE // max(len(seed), 1)) + 2), source=2)
    return g
