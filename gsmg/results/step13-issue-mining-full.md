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

## Full-image colour audit — the marker is the only one

Every one of the 196 cells was checked for its exact modal RGB, to test whether the
`(254,254,254)` cell is part of a broader hidden layer.

```
cells whose modal colour is NOT canonical : 1
   cell(row 7, col 4)  modal RGB (254,254,254)  purity 100.0%
```

Every other cell is a flat, exact member of {black, white, blue, yellow}. The only
cells with mixed pixels are (6,6)-(8,9), which is the rabbit's black line art drawn
over white.

So there is **no LSB or palette-based hidden layer**. There is exactly one
deliberately marked cell, at full purity, off by one unit in each channel.

That matches the author's 2023 hint — *"we wont give away the password its in front
of your eyes but youre not seeing it"* — with unusual precision: a one-unit RGB
offset is invisible to the eye but unambiguous in the data.

## The marker as an index — tested

Used the marker's several readings (spiral index 163, character 20, bit 3,
row-major 102, row 7, col 4) as offsets into every major recovered object — the
256-symbol object, the 570-character Bifid plaintext, the 1075-token stream, and the
1327-byte Cosmic Duality plaintext — taking substrings of length 8, 16, 20, 32 and
64, and every-nth-character readings, plus digests of all.

```
960 candidates x 3 blobs = 23,040 trials   0 printable
```

Negative.

## What is genuinely unexplained, after this pass

1. **The `(254,254,254)` marker at cell (7,4)** — deliberate, invisible, confirmed
   at 100% purity, matching the author's own description of the hidden password
   hint. Its meaning is unknown.
2. **`primes` and `yinyang`** — two of the seven words in the author's 2023 hint
   with no demonstrated function.

Everything else published about this puzzle is either reproduced in this repository
or shown to be false.
