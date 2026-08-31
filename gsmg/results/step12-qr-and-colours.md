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
