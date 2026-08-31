# Step 2 — sweep of live-page material

Date: 2026-08-31

## What changed since step 1

The final page was captured (`data/salphaseion_page.mhtml`), so candidates are now
built from the page's own objects rather than from documentation prose.

`tools/parse_page.py` re-derives every published decoding from the capture alone,
and all of them reproduce: the 1075-token count, `matrixsumlist`, `enter`,
`lastwordsbeforearchichoice`, `thispassword`, and the blob's shape and salt.

## Method

`tools/gen2.py` builds candidates from:

1. the page's verbatim objects — the 91-token prefix, the 570-char Bifid segment,
   the 130-char mixed region, the 180-char blob region, both base64 halves, and the
   whole stream
2. the page's own decoded vocabulary, including `shabef`/`sha256`, `anstoo`,
   `ourfirsthintisyourlastcommand`
3. permutations and concatenations of that vocabulary, 2 to 4 deep
4. the page's own transform applied to each segment: `abcdefghio` -> `1234567890`,
   read as a decimal number, shifted to base 16, read as hex ASCII
5. SHA-256 and MD5 digests of everything above, since `password = sha256(X)` allows
   X to itself be a digest
6. XOR chains over token digests, 2 to 5 deep — the construction the author
   demonstrably used for the Dualite blob
7. every candidate also reversed, per the `esrever` hint

## Result

```
step 2 alone      772,842 candidates   1,545,684 trials    6,050 survivors   0 printable
step 1 + step 2 3,838,457 candidates   7,676,914 trials   30,233 survivors   0 printable
```

**Negative.** Highest printable ratio remains 40.5%, consistent with random bytes.

## What this changes

The page capture resolved the provenance caveat: the blob is confirmed to match the
community transcription. It also exposed something the transcription hides — the
128-character blob is a **reconstruction**, not a page substring. Two edits are
needed to reach it: deleting the 40-character `enter` run embedded inside the
ciphertext, and dropping a trailing `s`.

Since `a` and `b` are valid base64 characters, "the `enter` run is not part of the
blob" is an assumption, not an observation. Every sweep to date, here and in the
community's work, has been run against that one reconstruction. Alternative
reconstructions are cheap to test and, as far as the published record goes, untested.

## Still open

The 570-char Bifid segment is the largest object on the page and has not been
decoded here. Its published reduction (odd-position stream, I and O removed, 256
symbols over a 23-letter alphabet) is where ~335.7M of the community's candidates
went, all negative.
