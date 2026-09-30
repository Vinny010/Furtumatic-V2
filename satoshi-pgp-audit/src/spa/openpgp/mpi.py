"""Multiprecision integers (RFC 4880 s3.2).

An MPI is a 2-byte big-endian *bit* count followed by ceil(bits/8) bytes. The audit
cares about the declared bit length as well as the value, because a declared length
that disagrees with the true length of the integer is itself an anomaly worth
reporting (it is one of the few ways a malformed or hand-crafted packet betrays
itself).
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class MPI:
    value: int
    declared_bits: int
    encoded_len: int

    @property
    def actual_bits(self) -> int:
        return self.value.bit_length()

    @property
    def length_consistent(self) -> bool:
        """True when the declared bit count matches the integer's real bit length.

        RFC 4880 requires the declared length to be exact (no leading zero bits).
        GnuPG has always emitted exact lengths, so a mismatch here means the packet
        did not come from a conforming implementation.
        """
        return self.declared_bits == self.actual_bits

    def to_bytes(self, length: int) -> bytes:
        return self.value.to_bytes(length, "big")

    def __repr__(self) -> str:
        return "MPI(%d bits, 0x%x)" % (self.declared_bits, self.value)


def read_mpi(data: bytes, offset: int) -> Tuple[MPI, int]:
    """Read one MPI at ``offset``; return (mpi, new_offset)."""
    if offset + 2 > len(data):
        raise ValueError("truncated MPI header at offset %d" % offset)
    bits = int.from_bytes(data[offset:offset + 2], "big")
    nbytes = (bits + 7) // 8
    start = offset + 2
    end = start + nbytes
    if end > len(data):
        raise ValueError("truncated MPI body at offset %d (need %d bytes)" % (offset, nbytes))
    value = int.from_bytes(data[start:end], "big") if nbytes else 0
    return MPI(value=value, declared_bits=bits, encoded_len=2 + nbytes), end


def encode_mpi(value: int) -> bytes:
    """Inverse of read_mpi, used to rebuild fingerprint preimages."""
    bits = value.bit_length()
    nbytes = (bits + 7) // 8
    return bits.to_bytes(2, "big") + value.to_bytes(nbytes, "big")
