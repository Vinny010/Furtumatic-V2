"""RFC 4880 registry values.

Kept as plain dicts rather than enums so that unknown/reserved values coming out of a
1000-signature keyserver blob degrade to "unknown (N)" instead of raising.
"""

# RFC 4880 s4.3
PACKET_TAGS = {
    0: "reserved", 1: "public-key-encrypted-session-key", 2: "signature",
    3: "symmetric-key-encrypted-session-key", 4: "one-pass-signature",
    5: "secret-key", 6: "public-key", 7: "secret-subkey", 8: "compressed-data",
    9: "symmetrically-encrypted-data", 10: "marker", 11: "literal-data",
    12: "trust", 13: "user-id", 14: "public-subkey", 17: "user-attribute",
    18: "sym-encrypted-integrity-protected-data", 19: "modification-detection-code",
}

# RFC 4880 s9.1
PUBKEY_ALGOS = {
    1: "RSA (Encrypt or Sign)", 2: "RSA Encrypt-Only", 3: "RSA Sign-Only",
    16: "Elgamal (Encrypt-Only)", 17: "DSA", 18: "ECDH", 19: "ECDSA",
    20: "Elgamal (Encrypt or Sign)", 22: "EdDSA",
}

# RFC 4880 s9.4
HASH_ALGOS = {
    1: "MD5", 2: "SHA1", 3: "RIPEMD160", 8: "SHA256", 9: "SHA384",
    10: "SHA512", 11: "SHA224",
}

# Digest length in bytes, used to sanity-check DSA truncation behaviour.
HASH_LEN = {1: 16, 2: 20, 3: 20, 8: 32, 9: 48, 10: 64, 11: 28}

# RFC 4880 s9.2
SYM_ALGOS = {
    0: "Plaintext", 1: "IDEA", 2: "TripleDES", 3: "CAST5", 4: "Blowfish",
    7: "AES128", 8: "AES192", 9: "AES256", 10: "Twofish256",
}

COMPRESSION_ALGOS = {0: "Uncompressed", 1: "ZIP", 2: "ZLIB", 3: "BZip2"}

# RFC 4880 s5.2.1
SIG_TYPES = {
    0x00: "binary document", 0x01: "canonical text document",
    0x02: "standalone", 0x10: "generic certification",
    0x11: "persona certification", 0x12: "casual certification",
    0x13: "positive certification", 0x18: "subkey binding",
    0x19: "primary key binding", 0x1F: "direct key",
    0x20: "key revocation", 0x28: "subkey revocation",
    0x30: "certification revocation", 0x40: "timestamp",
    0x50: "third-party confirmation",
}

# RFC 4880 s5.2.3.1
SIG_SUBPACKET_TYPES = {
    2: "signature-creation-time", 3: "signature-expiration-time",
    4: "exportable-certification", 5: "trust-signature", 6: "regular-expression",
    7: "revocable", 9: "key-expiration-time", 11: "preferred-symmetric-algorithms",
    12: "revocation-key", 16: "issuer-key-id", 20: "notation-data",
    21: "preferred-hash-algorithms", 22: "preferred-compression-algorithms",
    23: "key-server-preferences", 24: "preferred-key-server",
    25: "primary-user-id", 26: "policy-uri", 27: "key-flags",
    28: "signer-user-id", 29: "reason-for-revocation", 30: "features",
    31: "signature-target", 32: "embedded-signature",
    33: "issuer-fingerprint",
}

# RFC 4880 s5.2.3.21
KEY_FLAGS = {
    0x01: "certify", 0x02: "sign", 0x04: "encrypt-communications",
    0x08: "encrypt-storage", 0x10: "split-key", 0x20: "authenticate",
    0x80: "group-key",
}

# Signature classes whose issuer must be the key itself for the signature to be a
# self-signature. These are the only signatures on a keyblock that were produced by
# the *subject's* private key, and therefore the only ones carrying the subject's
# DSA nonces. Everything else on a keyserver blob is third-party material.
SELF_SIG_CLASSES = {0x10, 0x11, 0x12, 0x13, 0x18, 0x19, 0x1F, 0x20, 0x28}


def name_for(table, value, prefix="unknown"):
    """Never raise on an unregistered value - keyserver blobs are full of them."""
    return table.get(value, "%s (%d)" % (prefix, value))
