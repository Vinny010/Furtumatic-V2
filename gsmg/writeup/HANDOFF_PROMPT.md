# GSMG.IO 5 BTC puzzle — handoff brief

Paste this whole thing as your prompt. It is a state dump so you do not repeat
~2.5 billion candidate trials that already came back negative.

---

I am working on the GSMG.IO 5 BTC puzzle (published 2019, still unsolved). Below is
verified state. Everything marked VERIFIED was independently reproduced from primary
sources — do not re-derive it, build on it. Everything marked NEGATIVE has been
exhaustively swept — do not repeat it. Tell me if you find an error in any of it.

## The prize

```
1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe   1.2563451 BTC   HAS SPENT (pubkey exposed)
17ucy1K9ZUAaoY6JVtM932W9jUp5LXfyHa   3.7505531 BTC   never spent
```

VERIFIED — the first address's uncompressed public key, recovered from its
2024-04-24 spend, hashes to that address exactly:

```
04f4d1bbd91e65e2a019566a17574e97dae908b784b388891848007e4f55d5a46
49c73d25fc5ed8fd7227cab0be4e576c0c6404db5aa546286563e4be12bf33559
```

CONSEQUENCE: the puzzle's answer does not need to be a private key — it only needs
to BOUND one. With Pollard's Kangaroo on one consumer GPU, an interval of 2^80
resolves in ~30 minutes, 2^60 in ~1 second, 2^140 in ~50,000 years. The second
address has no exposed pubkey, so no discrete-log method reaches it.

## The chain, all VERIFIED by decryption

| stage | password | KDF |
|---|---|---|
| stage 1 | 14x14 grid, ccw spiral, black=1/white=0, blue=black, yellow=white, 8-bit ASCII -> `gsmg.io/theseedisplanted` | — |
| stage 2 | `theflowerblossomsthroughwhatseemstobeaconcretesurface` | — |
| phase 2 | `sha256("causality")` | EVP_BytesToKey/SHA-256 |
| phase 3 | `sha256(` 7 parts concatenated `)` = `1a57c572caf3cf722e41f5f9cf99ffacff06728a43032dd44c481c77d2ec30d5` | EVP_BytesToKey/SHA-256 |
| phase 3.2 | `sha256("jacquefrescogiveitjustonesecondheisenbergsuncertaintyprinciple")` | EVP_BytesToKey/SHA-256 |
| phase 3.2 block | scrambled alphabet then Beaufort, key `THEMATRIXHASYOU` | — |
| VIC digits | straddling checkerboard, alphabet `FUBCDORA.LETHINGKYMVPS.JQZXW`, escapes 1 and 4 | — |
| Cosmic Duality | XOR of sha256 of 7 tokens = `a795de117e472590e572dc193130c763e3fb555ee5db9d34494e156152e50735`, used as 32 RAW BYTES | EVP_BytesToKey/**MD5** |

The 7 phase-3 parts: `causality`, `Safenet`, `Luna`, `HSM`, `11110`,
`0x736B6E616220726F662074756F6C69616220646E6F63657320666F206B6E697262206E6F20726F6C6C65636E61684320393030322F6E614A2F33302073656D695420656854`,
`B5KR/1r5B/2R5/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 b - - 0 1`

The 7 Cosmic Duality tokens: `matrixsumlist`, `enter`,
`lastwordsbeforearchichoice`, `thispassword`, `matrixsumlist`, `yourlastcommand`,
`secondanswer`. NOTE: `matrixsumlist` appears twice and XOR is self-inverse, so it
cancels — the effective set is 5 tokens.

NOTE THE DIGEST SPLIT: the chain uses EVP_BytesToKey/SHA-256, but Cosmic Duality
uses EVP_BytesToKey/**MD5**. Any sweep must try both.

## Cosmic Duality resolves fully — and pays nothing

VERIFIED end to end: 1327-byte plaintext (sha256
`4f7a1e4efe4bf6c5581e32505c019657cb7b030e90232d33f011aca6a5e9c081`) -> bitstream ->
103x103 matrix -> `secondary[i] = chr((row_sums[i] + col_sums[(i+7) % 103]) & 0xFF)`
-> 103 chars, ordinals 80..117 -> base-38 -> 68 bytes = Half(32) + Better half(32)
+ 4 trailing (`fc0c1b02`).

```
Half        1JG648yaB7Wp2dpUfcZoRSD4q35oq47vCu / 15E3pcDDXSKhvi3CLVhRTHEgd8dbVKvSZg
Better half 145ZQ9siLrsXBKf465wjdyQYAP5dRwhRhQ / 1FhbJnrdq1FmeiXrpTqnpQ8jvYV7naze96
```

All four are EMPTY. This branch is a dead end for the money. The trailing bytes
`fc0c1b02` as signed integers give X=-4, H=12, Y=27, Q=2, resolving the phase-2
riddle table `# X 2 S H 4 Y 0 Q B 15 #` (with known S=32, B=-16) to
`-4, 2, 32, 12, 4, 27, 0, 2, -16, 15`. Swept as key material — negative.

## THE ACTUAL GATE — unsolved

A 96-byte OpenSSL blob on the final page. Two structurally valid reconstructions
exist (an OpenSSL blob needs base64 length divisible by 64; the page's base64 run is
interrupted by a 40-char `a`/`b` run that decodes to the word "enter"):

```
A (deletes "enter"):
U2FsdGVkX186tYU0hVJBXXUnBUO7C0+X4KUWnWkCvoZSxbRD3wNsGWVHefvdrd9zQvX0t8v3jPB4okpspxebRi6sE1BMl5HI8Rku+KejUqTvdWOX6nQjSpepXwGuN/jJ

B (keeps "enter"):
U2FsdGVkX186tYU0hVJBXXUnBUO7C0+X4KUWnWkCvoZSxbRD3wNsGWVHefvdrd9zabbaabababbabbbaabbbabaaabbaabababbbaabaQvX0t8v3jPB4okpspxebRi6s
```

Both: `Salted__`, salt `3ab585348552415d`, 80 bytes ciphertext.

VERIFIED CONSTRAINT: 80 bytes of AES-CBC ciphertext with PKCS7 means the plaintext
is **64 to 79 bytes**. A raw 32-byte key encrypts to 48 bytes; a 51-52 char WIF key
to 64. **Neither fits.** So the plaintext is not a bare private key — it is 64-79
bytes of something else. Combined with the exposed pubkey, a range specifier or
offset would suffice.

There is a second unsolved blob at the end of phase 3.2's plaintext: 96 bytes, salt
`b45a5e3d827593ca`, 80 bytes ciphertext — same shape.

## The one unexplained signal

In `puzzle.png`, exactly ONE of the 196 grid cells deviates from the palette:

```
cell (row 7, col 4)   RGB (254,254,254) instead of (255,255,255)   purity 100%
spiral index 163  =  character 20, bit 3  =  the letter 'n'
```

Every other cell is a flat exact member of {black, white, blue, yellow}. There is no
other LSB or palette steganography in the image. The pixel-art rabbit is looking
directly at this cell. The author's 2023 hint (bit-reversed ASCII, from issue #106)
reads: *"yellow blue primes matrix sumlist lastwordsbeforearchichoice yinyang"* and
*"we wont give away the password its in front of your eyes but youre not seeing it."*
A one-unit RGB offset is invisible to the eye and unambiguous in the data.

MEANING UNKNOWN. This is the most promising open lead.

Also unexplained: the hint words `primes` and `yinyang`.

## NEGATIVE — do not repeat

~2.5 billion trials against both blob variants, four password forms (`sha256` as hex
text, `sha256` as raw bytes, the literal candidate, and hex-decoded candidate) and
both EVP digests:

- every subset XOR of a 26-token vocabulary (2^26), with the known Cosmic Duality
  key present as a positive control
- concatenations WITH REPETITION, lengths 1-5, 20-token vocabulary
- all 2^23 letter-to-bit masks over the 256-symbol object
- all 9! Bifid square orderings and their parity streams
- the author's hint vocabulary, the grid colour counts (15 blue, 9 yellow -> O and I
  under a1z26, the two letters removed at SalPhaseIon), prime sequences
- the resolved phase-2 table
- the 14x14 grid read at 2 bits per cell (392 bits — enough for a key) across 24
  colour assignments, 7 reading orders, both directions, every byte-aligned 256-bit
  window, derived to compressed and uncompressed addresses
- the marker's readings as indices into every recovered object

ALSO RULED OUT:
- The grid is not a partial QR code. A v1 QR is 21x21 with finders in rows/cols 0-6,
  leaving exactly 14x14 — but format bits in that alignment are not valid BCH under
  any colour mapping, 1,024 full reconstructions yield 0 decodes, the best 7x7 finder
  match anywhere scores 32/49 (real = 49/49), and the grid's capacity is fully
  consumed by the URL with only 4 white cells spare.
- The banner QR is an ordinary untampered QR of the prize-address URL.
- Three claimed solutions (issues #69/#80, #108, #109) all fail the same test: no
  derived key controls a funded address. #108's 79-byte output is statistically
  random (38.0% printable vs 37.1% expected; PKCS7 pad of 1 occurs 1-in-256).

## What I want from you

1. Any error in the above.
2. Any meaning for the (254,254,254) marker at cell (7,4).
3. Any meaning for `primes` and `yinyang`.
4. A candidate-generation idea structurally different from what is listed as
   negative — the password is 64-79 bytes of plaintext and may specify a keyspace
   interval rather than a key.

Do not give me a "solution" without deriving a key and checking it against the two
addresses above. Three published claims have already failed that test.
