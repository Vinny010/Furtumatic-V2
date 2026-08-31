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
