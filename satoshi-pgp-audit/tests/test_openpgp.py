"""RFC 4880 parsing, against the real pinned key."""
import pytest

from spa.openpgp import dearmor, parse_keyblock, parse_packets
from spa.openpgp.mpi import encode_mpi, read_mpi
from spa.openpgp.packets import MalformedPacket, PublicKeyPacket, SignaturePacket

from conftest import SATOSHI_FPR


def test_fingerprint_recomputed_from_packets(keyblock):
    """The trust anchor: derived locally, not taken from the keyserver."""
    assert keyblock.fingerprint == SATOSHI_FPR


def test_key_id_is_fingerprint_suffix(keyblock):
    assert keyblock.key_id == SATOSHI_FPR[-16:]
    assert keyblock.key_id.endswith("5EC948A1")


def test_primary_key_shape(keyblock):
    k = keyblock.primary
    assert k.version == 4
    assert k.algo == 17 and k.algo_name == "DSA"
    assert k.key_size_bits == 1024
    assert k.mpis["q"].declared_bits == 160
    assert k.created == 1225390759  # 2008-10-30T18:19:19Z


def test_elgamal_subkey(keyblock):
    assert len(keyblock.subkeys) == 1
    sub = keyblock.subkeys[0].key
    assert sub.algo == 16
    assert sub.key_size_bits == 2048


def test_all_packets_parse_without_error(keyblock):
    """A keyserver blob is adversarial input; nothing may be silently dropped."""
    assert keyblock.malformed == []
    assert len(keyblock.all_packets) == 228  # 1 pub + 1 uid + 1 sub + 225 sigs


def test_third_party_signatures_dominate(keyblock):
    """Only signatures by the key itself carry its nonces."""
    total = len(keyblock.all_signatures())
    mine = len(keyblock.self_signatures())
    assert total == 225
    assert mine == 3
    assert total - mine == 222


def test_signed_digest_reconstruction(keyblock):
    """left16 is a cleartext prefix of the digest - a free integrity check."""
    for sig in keyblock.self_signatures():
        assert keyblock.digest_matches_left16(sig) is True


def test_mpi_lengths_are_conformant(keyblock):
    for name, mpi in keyblock.primary.mpis.items():
        assert mpi.length_consistent, "%s declares a non-exact bit length" % name


def test_mpi_roundtrip():
    for value in (0x01, 0xFF, 0xDEADBEEF, 1 << 1023):
        mpi, off = read_mpi(encode_mpi(value), 0)
        assert mpi.value == value
        assert off == len(encode_mpi(value))


def test_armor_version_header_is_not_the_generator(key_path):
    """The 'GnuPG v1.4.7 (MingW32)' claim lives here - and is not authenticated."""
    block = dearmor(key_path.read_text())[0]
    assert block.crc_ok is True
    # This copy came through a keyserver, which rewrote the header.
    assert block.version_header is not None
    assert "GnuPG" not in block.version_header


def test_malformed_input_does_not_raise():
    """One corrupt packet must not hide the rest."""
    packets = parse_packets(b"\xc6\x03\x01\x02")  # declares 3 bytes, supplies 2
    assert any(isinstance(p, MalformedPacket) for p in packets)


def test_truncated_mpi_raises():
    with pytest.raises(ValueError):
        read_mpi(b"\x04\x00", 0)  # declares 4 bits, supplies no body
