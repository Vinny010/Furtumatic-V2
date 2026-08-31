# Step 3 — the Bifid segment and the 256-symbol object

Date: 2026-08-31

## Reproduced

`tools/bifid.py` derives the 256-symbol object from the page capture:

```
square      : d b i / f h c / e g a
bifid output: 570 symbols over abcdefghi
odd stream  : 285 -> remove i/o -> 256 OK
alphabet    : abcdefgh (8 letters)
```

The key `DBIFHCEG` is exactly the set {b..i}, so appending `a` completes the
9-letter alphabet `a-i` — which is why the square is 3×3 and why the segment's
alphabet is what it is. Bifid decryption with period = full length, then the
odd-position stream with `i` removed, lands on exactly 256 symbols. The object is
stored as `data/object256.txt`.

## Two corrections to the published description

The write-up describes this object as "256 characters over a **23-letter
alphabet**", explained as a 25-letter Polybius square minus the Base58-ambiguous
`I` and `O`. That is wrong. The square is 3×3 over 9 letters, not 5×5 over 25, and
the object uses **8** distinct letters (`a-h`). The only removed letter is `i`;
there is no `o` in the stream at all.

This is the second error found in that account — it also states the Dualite
secondary string has "exactly 38 distinct symbols" when it has 29 (see
`capture-verification.md`). The mechanism it describes is right; its stated
alphabet sizes are not.

The claim that the Bifid decoding "starts with the plaintext `BTCSEED`" also does
not reproduce. The output starts `cieaadddacafgbai…`, over `a-i`. A 9-letter
alphabet cannot spell `BTCSEED` — `T` and `S` are not in it — so `BTCSEED` must come
from a further step the write-up does not document, or the claim is mistaken.

## Swept

**All 9! square orderings.** Every one of the 362,880 possible 3×3 squares was
Bifid-decrypted and its full output, odd stream and even stream emitted, with and
without `i` — 362,880 distinct candidates after dedup — then run against both blob
variants:

```
vs variant A   362,880 candidates   725,760 trials   2,830 survivors   0 printable
vs variant B   362,880 candidates   725,760 trials   2,989 survivors   0 printable
```

Also noted: 29,808 of the 362,880 squares yield a 256-symbol reduction, so "it
reduces to 256" is not by itself evidence that a square is the right one. The
documented square is one of them.

**All 256 letter-to-bit masks.** With 8 letters and 256 symbols, a mask assigning
each letter one bit produces exactly 256 bits = a 32-byte key. All 256 masks × both
directions were derived to compressed and uncompressed P2PKH addresses:

```
masks tested 508, skipped (outside curve order) 4
direct-key hits: NONE
```

and the same candidates as blob passwords, both variants: 0 printable.

This reproduces the community's negative result on the mask route independently,
and extends it to the AES-blob route, which they did not test.

## Running total

```
step 1   documentation prose        3,065,615
step 2   live-page material           772,842
step 2b  both corpora vs variant B  3,838,457
step 3   all 9! Bifid outputs x 2 blobs 725,760
step 3b  256-symbol mask candidates      2,044
                                    ------------
                                    ~12.2M trials, 0 printable plaintexts
```
