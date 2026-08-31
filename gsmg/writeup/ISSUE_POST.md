# Verification pass: three "solved" claims tested and failed, the blob-typo question settled, and one confirmed unexplained signal

This is a verification contribution, not a solution claim. Everything below is
reproducible; tooling is linked at the end. Where this work merely reproduces what
the README and earlier issues already established, it says so.

---

## 1. The blob transcription question is settled

Issue #17 quotes the SalPhaseIon blob one way; issue #108 asserts the *live page*
contains two typos. A capture of the live page taken 2026-08-31 settles it:

```
live page (2026-08-31) : U2FsdGVkX186tYU0hVJBXXUnBUO7C0+X4KUWnWkCvoZSxbRD3wNsGWVHefvdrd9z…
issue #108 "corrected" : identical
issue #17              : differs at positions 4, 18, 51
```

Decoded:

| source | header | salt |
|---|---|---|
| live page | `Salted__` | `3ab585348552415d` |
| issue #17 | `Salded__` | `3ab585348554415d` |

Issue #17's transcription does not produce a valid OpenSSL header. **The live page
is correct as-is.** There are no typos on the page to fix; the error was in the old
transcription.

Worth flagging because anyone sweeping against #17's string is sweeping the wrong
ciphertext.

## 2. A note on the blob's reconstruction

The 128-character base64 blob is **not** a verbatim substring of the page. The
page's base64 run is interrupted:

```
[895:959]  U2FsdGVkX186tYU0hVJBXXUnBUO7C0+X4KUWnWkCvoZSxbRD3wNsGWVHefvdrd9z   64 chars
[959:999]  abbaabababbabbbaabbbabaaabbaabababbbaaba                           40 chars -> "enter"
[999:1064] QvX0t8v3jPB4okpspxebRi6sE1BMl5HI8Rku+KejUqTvdWOX6nQjSpepXwGuN/jJs  65 chars
```

Reaching 128 characters requires deleting the embedded `enter` run and dropping a
trailing `s`. Since `a` and `b` are valid base64 characters, "the `enter` run is not
part of the ciphertext" is an assumption, not an observation.

There are exactly **two** structurally valid 128-character reconstructions (an
OpenSSL blob needs its base64 length to be a multiple of 64):

| variant | bytes | salt | ciphertext |
|---|---|---|---|
| A — deletes `enter` (the one everyone uses) | 96 | `3ab585348552415d` | 80 |
| B — keeps `enter` | 96 | `3ab585348552415d` | 80 |

Both carry the `Salted__` header; their ciphertexts diverge from byte 48. I have not
seen variant B raised in the issues I have read, though I have not read all of them.
It has been swept here alongside A — negative — but it belongs on the board.

## 3. Three "solved" claims, tested

All three fail the same question: **does a derived key control a funded address?**

| claim | verdict | basis |
|---|---|---|
| #69 / #80 — Half & Better Half | false | derived addresses are empty; #106's PKCS7-overfit analysis is correct |
| #108 — two typos, full decrypt | false | see below |
| #109 / `kaibuzz0/Gsmg.io-solution` | false | see below |

**#108.** Its password does decrypt variant A under EVP-BytesToKey/MD5, and the 79
output bytes match its published `K_C1`/`K_C2`/`E_C` exactly. It is still a false
positive:

```
printable fraction : 38.0%     random bytes expect 37.1%
distinct bytes     : 72 / 79   consistent with noise
PKCS7 pad          : 1         occurs by chance once in 256
```

Neither `K_C1` nor `K_C2`, nor their XOR, modular sum, or either SHA-256
concatenation, derives to `1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe` or
`17ucy1K9ZUAaoY6JVtM932W9jUp5LXfyHa` under compressed or uncompressed encoding.
`K_C1`'s public key does not match the public key exposed on-chain by the
2024-04-24 spend. The `K_C1 / K_C2 / E_C` labelling is a 32+32+15 slicing of random
bytes.

**#109.** The linked repository claims a hidden PBKDF1→PBKDF2 "trap" and gives
per-phase passwords. Its claimed phase-2 password
(`thekeymakertheveninbarrowmatrixoverlordcxb7chancellor`) produces **no valid
decryption** of the real phase-2 blob — tried as a literal and as its SHA-256 hex,
under EVP-SHA256, EVP-MD5, and PBKDF2-HMAC-SHA256/SHA1 at 1000, 2048 and 10000
iterations. The real password, `sha256("causality")`, decrypts cleanly under
EVP-SHA256 at 98% printable to the known plaintext. The repository also names the
wrong host (`gang.io`) and describes itself as reconstructed from memory. Its KDF
premise is wrong: the chain uses OpenSSL `EVP_BytesToKey` throughout, verified by
decrypting phases 2, 3 and 3.2 with their real passwords.

## 4. Issue #14 confirmed and quantified — the only unexplained signal left

#14 noted years ago that one white square is `(254,254,254)` instead of
`(255,255,255)`, with the rabbit looking at it. Confirmed, and worth stating
precisely because it appears to be the **only** anomaly in the image:

Every one of the 196 cells was checked for its exact modal RGB.

```
cells whose modal colour is NOT canonical : exactly 1
   cell (row 7, col 4)   modal RGB (254,254,254)   purity 100.0%
```

Every other cell is a flat, exact member of {black, white, blue, yellow}. The only
cells with mixed pixels are (6,6)–(8,9) — the rabbit's line art. **There is no LSB
or palette steganography anywhere else in the image.**

The marked cell resolves to:

```
grid cell    : row 7, col 4
spiral index : 163
character    : index 20, bit 3   ->  the letter 'n' in gsmg.io/theseedisplanted
```

It is *not* in the 2×2 spiral centre (all four of those are plain `(255,255,255)`),
so it is a distinct signal from the rabbit's own position. Flipping the marked bit
gives `gsmg.io/theseedispla~ted`, which is not meaningful — so it is unlikely to be
a bit-correction instruction.

Note the fit with the author's 2023 hint reported in #106: *"we wont give away the
password its in front of your eyes but youre not seeing it."* A one-unit RGB offset
is invisible to the eye and unambiguous in the data.

**Its meaning is unknown.** It was tested as an index (spiral 163, char 20, bit 3,
row-major 102, row 7, col 4) into the 256-symbol object, the 570-character Bifid
plaintext, the 1075-token stream and the 1327-byte Cosmic Duality plaintext, taking
substrings and every-nth readings plus digests — negative.

## 5. Negative space, so it is not re-walked

Roughly 2.5 billion candidate trials against both blob variants, four password
forms (`sha256` hex, `sha256` raw bytes, the literal candidate, and hex-decoded
candidate) and both EVP digests. All negative. Covered:

- every subset XOR of a 26-token page vocabulary (2^26), with the published Cosmic
  Duality key present as a positive control
- concatenations **with repetition**, lengths 1–5, over a 20-token vocabulary —
  note that permutation-based generation cannot produce a repeated token, and the
  #108 password shape repeats `matrixsumlist`
- all 2^23 letter-to-bit masks over the 256-symbol object
- all 9! Bifid square orderings and their parity streams
- the author's 2023 hint vocabulary (`yellow`, `blue`, `primes`, `yinyang`, the
  grid counts 15 and 9, prime sequences)
- the resolved phase-2 table from #103 (independently corroborated: the Cosmic
  Duality trailing bytes are `fc0c1b02`)
- the four-colour reading of the 14×14 grid at two bits per cell — 392 bits, enough
  to hold a key — across 24 colour assignments, 7 reading orders, both directions,
  every byte-aligned 256-bit window

## 6. The grid is not a partial QR code

Raised occasionally, so: a version-1 QR is 21×21 and its finders occupy rows 0–6 and
cols 0–6, leaving exactly 14×14 — which is suggestive. It was tested. Format bits in
that alignment are not valid BCH codes under any colour mapping; 1,024 full 21×21
reconstructions (4 colour mappings × 4 rotations × 2 flips × 32 format codes)
produced zero decodes; the best 7×7 finder match anywhere in the grid scores 32/49
against 49/49 for a real finder. Decisively, the grid's capacity is already fully
consumed — 192 of 196 cells spell `gsmg.io/theseedisplanted`, the other 4 being the
white centre — leaving no bits to be QR codewords.

The small black-and-white QR in the banner is an ordinary QR of the prize-address
URL, verified untampered (0/267 function modules differ from a clean re-encoding;
the data-region difference of 344 modules far exceeds what EC-L could repair, so it
is an ECI-headered bitstream, not flips).

## 7. On the exposed public key

`1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe` has spent, so its uncompressed public key is
on-chain and verified to hash to that address. This changes what the answer needs to
contain: it does **not** need to be a private key, only to *bound* one. With
Pollard's Kangaroo on a single consumer GPU, an interval of 2^80 resolves in about
half an hour and 2^60 in about a second. `17ucy1K9ZUAaoY6JVtM932W9jUp5LXfyHa` has
never spent, so no discrete-log method reaches it.

---

## Tooling

All of the above is reproducible. The oracle differs from the published checker in
one respect that matters: on a PKCS7 pass it **prints the plaintext** rather than
discarding it when it fails to reduce to a key. A correct password whose plaintext
is an instruction, an offset, or a range specifier would be reported as `NO MATCH`
by a key-matching checker.

Happy to share any of it. The most useful pieces are probably the debunking test
(derive-and-compare-address, which settles a claim in seconds) and the note that the
live page needs no correction.
