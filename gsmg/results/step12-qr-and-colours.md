# Step 12 — the QR code and the coloured squares

Date: 2026-08-31

## The QR carries nothing hidden

Decoded from `puzzle.png`'s banner:

```
https://www.blockchain.com/btc/address/1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe
```

Tested for tampering three ways:

1. **Structure.** Perspective-warped to its module grid at version 4 (33x33). The
   top-left finder pattern matches the textbook pattern **49/49**. Against a clean
   re-encoding, **0 of 267** function modules differ (finders, separators, timing,
   alignment, format). The skeleton is untouched.
2. **Format bits.** Read directly from the image: **EC level L, mask 2**, and both
   redundant copies are bitwise identical. No inconsistency.
3. **Error-correction capacity.** Version 4-L carries 16 EC codewords, correcting at
   most 8 symbol errors — roughly 64 modules. The data region differs from a clean
   re-encoding by **344 modules (41.8%, near random)**. Since the QR decodes
   cleanly, 344 flipped modules is impossible: error correction could never repair
   five times its own capacity. Those differences are therefore a **different
   bitstream**, not flips — consistent with the ECI header OpenCV warns about on
   decode.

**Colour check:** the QR region contains **8 distinct colours, all greyscale, zero
non-greyscale pixels.** No coloured modules, unlike the grid above it.

Conclusion: the QR is an ordinary, untampered QR of the prize address URL.

## The coloured squares and the rabbit are deliberate — and already accounted for

The author's 2023 hint (issue #106) names them: *"yellow blue primes matrix sumlist
lastwordsbeforearchichoice yinyang."*

Established here from the authoritative image:

- **24 coloured cells, 15 blue and 9 yellow.** Every one sits at spiral index
  ≡ 7 (mod 8) — the least-significant bit of a character. One per character, all 24
  characters covered, none doubled.
- Read in spiral order with blue=1, yellow=0, the colour bits are **byte-identical**
  to the LSBs of `gsmg.io/theseedisplanted`. They are byte-boundary markers whose
  values are fully determined by the plaintext.
- **15 and 9** give **O** and **I** under a1z26 — exactly the two Base58-ambiguous
  letters removed at the SalPhaseIon stage.
- **The rabbit** occupies the 2x2 spiral centre, the only 4 cells of 196 carrying no
  data. A stray 74 yellow pixels in cell (6,6) were checked and are a one-pixel
  antialiasing bleed along the border with cell (5,6), which is 97% yellow.

## "primes" and "yinyang" remain unexplained

Tested against the grid: characters at prime indices, blue/yellow index sets
intersected with primes, the colour-bit string, and combinations with the page
vocabulary — 1,188 candidates against both blob variants.

```
variant A   1,188 candidates   9,504 trials   0 printable
variant B   1,188 candidates   9,504 trials   0 printable
```

Negative. Of the author's seven hint words, five now have a demonstrated function
(`yellow`, `blue`, `matrix`, `sumlist`, `lastwordsbeforearchichoice`); `primes` and
`yinyang` do not.

## Clarification: the big coloured square is not a QR code

Worth stating plainly, because the two squares on the page are easily conflated:

- **The large 14x14 coloured grid** at the top of `gsmg.io/puzzle` is *not* a QR
  code. It has no finder patterns, no timing patterns, and 14x14 is not a valid QR
  size (QR versions are 21, 25, 29, ... modules). It is the puzzle's own bit-grid,
  and it decodes to `gsmg.io/theseedisplanted`.
- **The small black-and-white square** in the banner below it *is* a real QR, and
  carries only the prize-address URL, as established above.

The QR analysis in this file applies to the second one.

## The four-colour reading of the grid — tested

The grid was previously only ever read at **one bit per cell** (blue folded into
black, yellow into white), giving 196 bits — less than the 256 a private key needs.
Read instead as **four colours = two bits per cell**, it yields:

```
196 cells x 2 bits = 392 bits = 49 bytes    (a key needs 32)
```

That is enough to hold a key, so it is worth testing directly. Swept:

- all **24** assignments of the four colours to the values 0-3
- **7** reading orders: spiral clockwise and counter-clockwise, inward and outward,
  row-major, column-major, boustrophedon
- both bit directions, and every byte-aligned 256-bit window in the 392-bit stream

```
6,048 windows derived to compressed and uncompressed P2PKH addresses -> 0 matches
4,320 distinct 32-byte values swept as blob passwords, four password modes,
      against both final blob variants and the phase 3.2 tail blob -> 0 printable
```

Negative. The grid does not hold a private key under any two-bit reading tested,
which is consistent with the 24 coloured cells being byte-boundary markers whose
values are already determined by the plaintext.

## Tested: is the grid the inner part of a QR with the finders missing?

The hypothesis is well-formed and the arithmetic is suggestive: a version-1 QR is
21x21, its three finder patterns occupy rows 0-6 and cols 0-6, and the remaining
contiguous square is rows 7-20 x cols 7-20 — **exactly 14x14**, the grid's size.

Tested three ways.

**1. Format-bit validation.** If the grid were that quadrant, specific grid cells
would land on format-information bits, which are BCH(15,5)-encoded and therefore
self-validating. Under every colour-to-bit mapping, the implied format word is not
one of the 32 valid codes:

```
blue=black,yellow=white : 111010111011111   invalid
blue=white,yellow=black : 111000111011101   invalid
only K black            : 111000111011101   invalid
```

**2. Full reconstruction and decode.** Built complete 21x21 QRs with standard
finders, separators, timing patterns and dark module, placed the grid in rows 7-20
x cols 7-20, and wrote each of the 32 valid format codes into both format
positions. Across 4 colour mappings x 4 rotations x 2 flips x 32 format codes:

```
1,024 full-QR reconstructions attempted -> 0 successful decodes
```

**3. Finder search.** The best 7x7 match to a finder pattern anywhere in the grid
scores **32/49**. A real finder scores 49/49; random noise averages 24-25. There is
no finder pattern present, whole or partial.

**Structural argument.** A QR's data region is never a contiguous square — in every
version the three finders sit at three corners, leaving an L-shaped data area. The
only 14x14 contiguous square in a version-1 QR is the one tested.

**Decisive argument.** The grid is already fully accounted for. 192 of its 196 cells
spell `gsmg.io/theseedisplanted` as 8-bit ASCII read in a counter-clockwise spiral,
and the 4 remaining cells are the all-white centre where the rabbit is drawn. There
are no unexplained bits left over to be QR codewords.

Conclusion: the grid is not a QR code, complete or partial. It is a bit-grid whose
content is known and whose capacity is fully consumed.
