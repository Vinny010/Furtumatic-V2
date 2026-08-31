# blob.b64

The small OpenSSL `Salted__` AES-256-CBC blob published on the puzzle's final
(SalPhaseIon / Cosmic Duality) page.

Decodes to 96 bytes: 8-byte header `Salted__`, 8-byte salt `3ab585348552415d`,
80 bytes of ciphertext.

**Source:** the `BLOB_B64` constant in `tools/oracle.py` of
`floflo777/open-crypto-puzzles`, which states it is transcribed from the live page.

**Not independently verified against the live page.** `gsmg.io` is unreachable from
the environment this was assembled in. The shape and salt match the values documented
in two separate community repositories, but a direct capture of
`https://gsmg.io/89727c598b9cd1cf8873f27cb7057f050645ddb6a7a157a110239ac0152f6a32`
should be diffed against this file before any result derived from it is trusted.

That URL is derived, and verified here, as
`sha256("GSMGIO5BTCPUZZLECHALLENGE1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe")`.
