# Step 13 — mining the issue tracker properly

Date: 2026-08-31

Step 11 read only the first page of issues. There are 100+. This is the fuller pass.

## The blob "typo" question — RESOLVED

Issue #17 (an early transcription) quotes the SalPhaseIon blob as:

```
U2FsZGVkX186tYU0hVRBXXUnBUO7C0+X4KUWnWkCvoZSxbRD3wNkGWVHefvdrd9z...
```

Issue #108 later claims the *live page* has two typos at positions 18 and 51.

Both are settled by the live capture in `data/salphaseion_page.mhtml`:

```
live page (2026-08-31) : U2FsdGVkX186tYU0hVJBXXUnBUO7C0+X4KUWnWkCvoZSxbRD3wNsGWVHefvdrd9z...
issue #108 "corrected" : identical
issue #17              : differs at positions 4, 18, 51
```

Decoding each:

| source | header | salt |
|---|---|---|
| live page | `Salted__` | `3ab585348552415d` |
| issue #17 | `Salded__` | `3ab585348554415d` |

Issue #17's transcription is corrupt — it does not even produce a valid OpenSSL
header. The live page is correct, and matches what #108 calls the corrected form.
**The ciphertext swept throughout this repo is the right one**, verified against the
page itself.

## Issue #14 — the anomalous white square. CONFIRMED.

Reports that one white square differs: RGB `(254,254,254)` where every other white
square is `(255,255,255)`, and that the rabbit is looking directly at it.

Confirmed here from `puzzle.png`. Exactly **5,625 pixels** carry `(254,254,254)` —
precisely one 75x75 cell — at:

```
grid cell     : row 7, col 4  (0-indexed)
spiral index  : 163
character     : index 20, bit 3
character is  : 'n'  (0x6e = 01101110), and bit 3 is 0
```

A one-unit RGB offset over exactly one cell is not compression noise or
antialiasing; it is deliberate. The rabbit's gaze corroborates it.

Note this is **not** in the 2x2 spiral centre — all four centre cells are plain
`(255,255,255)`. So the marker is a distinct signal from the rabbit's own position.

Flipping the marked bit gives `gsmg.io/theseedispla~ted`, which is not meaningful,
so the marker is unlikely to be a bit-correction instruction.

Swept as key material — the coordinates (7,4), the spiral index 163, the character
and bit indices, the RGB values, the flipped message, and combinations with the page
vocabulary, plus digests: 2,010 candidates against all three blobs.

```
blob A / blob B / phase 3.2 tail   2,010 candidates each   0 printable
```

Negative. **The marker's meaning remains unexplained** — it is the clearest
unexplained deliberate signal found in this work.

## Other issues surveyed

| issue | content | value |
|---|---|---|
| #68 | gap analysis; XOR-chain key and Cosmic Duality chain, 22,748 combinations tried | corroborates this repo's reproduction; notes a "chain4" 1151-byte output partitioning at byte 246 |
| #72 | full Cosmic Duality derivation: XOR chain, 103x103 matrix, base-38, Half/Better Half | matches `tools/dualite_chain.py` exactly |
| #79 | the Half and Better Half private keys and their four addresses | matches this repo's independent derivation |
| #18 | JFK executive orders, EO 11110 | already in the README chain |
| #19 | someone selling a "clue" for $1000 | no content |
| #99 | blocked at address extraction from the 1327-byte plaintext | same wall |
| #107 | independent progress log | same wall |

## Standing

The unexplained signals are now: the `(254,254,254)` marker at cell (7,4), and the
author's hint words `primes` and `yinyang`. Everything else on the published board
is either reproduced here or shown false.
