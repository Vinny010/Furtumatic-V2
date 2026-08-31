# GSMG.IO 5 BTC puzzle — working notes and tooling

Independent re-analysis of the GSMG.IO puzzle. Everything here was reproduced from
primary material; nothing is taken on trust from a summary.

Prize addresses (both funded and unspent as of 2026-08-16, per the community
ledger — not verified here, since blockchain explorers are unreachable from the
environment this was built in):

| address | balance |
|---|---|
| `1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe` | 1.2563451 BTC |
| `17ucy1K9ZUAaoY6JVtM932W9jUp5LXfyHa` | 3.7505531 BTC |

## Stage 1 — fully accounted for

`tools/decode_grid.py` decodes the 14x14 grid at `gsmg.io/puzzle` straight from a
screenshot. Parameters were recovered by brute force over 96 read-order and
bit-mapping combinations, not copied from the published answer:

- counter-clockwise spiral, inward, from top-left
- black = 1, white = 0, blue = 1, yellow = 0
- 8-bit ASCII, 24 characters = 192 cells

Result: `gsmg.io/theseedisplanted`, exact.

### What the coloured squares are

All 24 coloured cells fall on spiral index = 7 (mod 8) — the least-significant bit
of a character. One per character, all 24 characters covered, none doubled. Read in
spiral order, blue = 1 and yellow = 0 gives:

```
colour bits : 111101110011110110010010
char LSBs   : 111101110011110110010010   <- identical
```

They are **byte-boundary markers**, confirming the 8-bit chunking and the spiral
path. Their values are fully determined by the plaintext, so they carry no
independent payload. Treating the 24 coloured cells as a separate 24-bit ciphertext
is chasing a value already known.

The 2x2 spiral centre (rows 6-7, cols 6-7) is all white and carries no data; the
white rabbit is drawn there. Sample cells by **median**, not mean — the rabbit's
line art skews the mean and flips cell (7,6).

## The final gate

`data/blob.b64` is the small blob: 96 bytes, `Salted__`, salt `3ab585348552415d`,
80 bytes of ciphertext.

**80 bytes of ciphertext means the plaintext is 64-79 bytes.** A raw 32-byte private
key encrypts to 48 bytes of ciphertext, and a 51-52 character WIF key to 64. Neither
fits. Whatever is behind this blob is not a bare private key — it is 64-79 bytes of
something else.

That matches how the puzzle's other blob resolved. The large "Dualite" blob is
already decrypted; its key is the XOR chain of the SHA-256 digests of seven tokens
(`matrixsumlist`, `enter`, `lastwordsbeforearchichoice`, `thispassword`,
`matrixsumlist`, `yourlastcommand`, `secondanswer`), verified here to reproduce
`a795de117e472590e572dc193130c763e3fb555ee5db9d34494e156152e50735` byte-exact. Its
1327-byte plaintext is not a key either: it folds into a 103x103 bit matrix and is
read out through row and column sums with an offset of 7, then base-38 decoded, to
reach the "Half" and "Better half" key material. The payload is a structure to be
navigated, not a key to be lifted. The small blob should be expected to behave the
same way.

(Those Half / Better half keys are public and their addresses were empty on
2026-08-19, so that chain does not pay out. The money is behind the small blob.)

## tools/gate.c — the oracle

```
candidate X -> sha256(X) hex -> EVP_BytesToKey{sha256, md5} -> AES-256-CBC
            -> PKCS7 check on the LAST BLOCK ONLY (1 AES block, not 5)
            -> on pass: full decrypt, print the plaintext
```

The difference from the community oracle is the last line. That one validates PKCS7,
then tries 4 readings of the plaintext as a 32-byte private key, and prints
`NO MATCH` otherwise — so a correct password whose plaintext is an instruction, an
offset or a coordinate is reported as a miss and **never shown**. Given the shape of
the Dualite plaintext, that is the likely shape of the answer.

Build and run:

```sh
gcc -O3 -march=native -o gate gsmg/tools/gate.c -lcrypto -Wno-deprecated-declarations
base64 -d gsmg/data/blob.b64 > blob.bin
python3 gsmg/tools/gen.py | ./gate survivors.log
```

Certification:

- **Derivation**: the phase-2 blob, password `sha256("causality")`, decrypts under
  EVP_BytesToKey/SHA-256 to its known plaintext at 100% printable; under MD5 the
  padding is invalid at 35% printable. Note the puzzle mixes digests — phases 2-3 use
  SHA-256, Cosmic Duality uses MD5 — so the oracle tries both on every candidate.
- **End to end**: a synthetic blob built with a known password and an
  *instruction-shaped* 64-byte plaintext is recovered correctly, confirming the
  oracle catches exactly the case the community oracle drops.

Measured: **482,000 candidates/sec/core**, both digests per candidate. PKCS7 survivor
rate 0.395%, matching the theoretical 1/256. Requiring all 64-79 plaintext bytes to
be printable reduces random false positives to roughly 10^-27, so survivors are
inspectable by hand.

The crypto is free. This is a candidate-generation problem, not a compute problem.

## Results

See `results/step1.md`.
