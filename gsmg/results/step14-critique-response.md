# Step 14 — acting on an external critique

Date: 2026-08-31

A second model reviewed this work. Its verifiable claims were checked; the work it
proposed was carried out. Both outcomes are recorded here.

## Its claims, verified

| claim | result |
|---|---|
| `dbbi` (stream[0:91]) has IoC 0.1509 vs 0.1111 for uniform-9 | **correct** — measured 0.1509 |
| `faed` (the 570-char segment) is flat, ~0.118 | **correct** — measured 0.1181 |
| 91 = 7 x 13 | correct |
| `dbbi`'s first-appearance order gives the Bifid key `DBIFHCEGA` | **correct** |
| the 14x14 grid is 86 black / 86 white | **correct — and this repo had it wrong** |

Two of these are corrections to my own work.

**The grid is 86/86, not 87/85.** Earlier extraction here reported 87 black and 85
white. Re-measuring by modal colour over an inset region, and mapping the
`(254,254,254)` marker to white, gives exactly 86/86 — a perfect balance. That makes
`yinyang` in the author's hint *descriptive of the grid* rather than a word to be
guessed. The earlier miscount came from median-sampling a patch that the rabbit's
line art intruded on.

**`dbbi` generates its own Bifid key.** Reading the 91-token prefix and taking each
symbol at first appearance yields `D B I F H C E G A` — precisely the keyed square
that turns the 570-char segment into `BTCSEED…`. The prefix was treated here as
unanalysed; it is in fact self-keying. This is elegant and was missed.

## The proposed work, carried out — both negative

**1. `matrixsumlist` on the 7x13 table.** `dbbi` mapped a=1..i=9 and folded both
ways:

```
7x13   row sums  [55, 65, 68, 60, 49, 63, 62]
       col sums  [28, 38, 42, 37, 24, 33, 15, 34, 35, 39, 26, 33, 38]
13x7   row sums  [27, 30, 32, 43, 30, 44, 29, 28, 26, 37, 28, 43, 25]
       col sums  [69, 58, 49, 59, 53, 74, 60]
       total     422
```

Swept: every concatenation and reversal, mod-26 letter renderings, raw-byte hex,
prime-index cell sums, the puzzle's own decimal->base-16->ASCII shift, and the
Dualite readout rule `row[i] + col[(i+k) mod n]` for k = 0..7 in both orientations.
None of the base-16 shifts produce ASCII. 8,976 candidates against three blobs:
**0 printable**.

**2. The grid re-read from the marked cell.** A spiral originating at (7,4) walking
outward, under four bit-plane assignments including the two complementary yin/yang
splits (`K+U` vs `W+Y`, and `K+Y` vs `W+U`), their XOR, and the yin/yang position
lists. No readable output; 87 candidates, **0 printable**.

## What could not be verified

The critique cites a fourth "URL-path blob" with salt `74c974e3f92e64b5`. That salt
appears in nothing held here. The four blobs in this repository are:

```
final blob A / B   3ab585348552415d
phase 3.2 tail     b45a5e3d827593ca
Cosmic Duality     2d3f6fe06dc950e6
```

Unverified, and it should not be built on until someone produces the ciphertext.

The strategic argument also rests on second-hand Telegram quotes which the critique
itself flags as unverified. Its central claim — that `yinyang` is the output of an
unreached offline phase rather than a guessable string — is plausible and would
explain the uniform failure of every hash-a-wordlist approach. But note where it
lands: if that phase is a page never archived, then **the required data is not in
hand**, which is the same conclusion reached independently here, stated with more
confidence than the evidence supports.

## Standing after this pass

The critique's diagnosis of *why* the sweeps failed is better than mine was: the
search space was not merely large, it was defined to be empty by the author. Its two
factual corrections are accepted and recorded. Its proposed experiments are now run,
and both are negative — so the live space is narrower still, not wider.

---

# Second critique pass — corrections and results

## The "104" claim is wrong, and the correction strengthens the prime reading

The follow-up argues the author's quoted *"104 is the fefefe square"* disagrees with
this repo's (7,4), implying the marked cell is really (7,5).

The pixel measurement is unambiguous and settles it:

```
254-valued block : x 300-374, y 525-599, exactly 5,625 px
col 4 spans      : x 299.4 .. 374.3
col 5 spans      : x 374.3 .. 449.1
=> the block occupies col 4. It is cell (row 7, col 4).
```

Its indices:

```
row-major 0-based : 102        row-major 1-based : 103   PRIME
spiral index      : 163  PRIME
```

**104 is not prime. 103 is.** So if the author's hint word `primes` points at the
marked square's index — which is the follow-up's own argument — then it points at
**103**, the actual cell, not at 104. The quoted "104" is second-hand and either a
relay error or a different indexing convention; it cannot be the prime being
referenced.

## A factual error in the follow-up

It states that cells (7,4) and (7,5) are *"both classified black (1) in decode_grid's
median sample."* They are not:

```
cell(7,3) modal RGB (255,255,255)  white      purity 100.0%
cell(7,4) modal RGB (254,254,254)  white      purity 100.0%
cell(7,5) modal RGB (255,255,255)  white      purity 100.0%
```

Both candidate cells are white at full purity. There is no black/white ambiguity to
exploit between them.

## Verified from the follow-up

```
spiral index 163 is prime          correct
blue slot-sum (1-based)  = 157     correct
yellow slot-sum (1-based) = 143    correct
blue 15 slots, yellow 9 slots      correct
```

## A coincidence worth recording

The number 103 appears three times, and 7 twice:

```
marked cell, 1-based row-major : 103   (prime)
Dualite secondary string length: 103
Dualite matrix dimension       : 103 x 103
Dualite readout offset k       : 7
marked cell row                : 7
```

The Cosmic Duality readout rule is `secondary[i] = row[i] + col[(i+7) % 103]`. The
marked cell's own index is 103 and its row is 7. This may be coincidence — 103 is
forced by the 1327-byte plaintext length, and the marked cell's index is forced by
its position — but the two numbers that define the Dualite readout are exactly the
two that describe the marked cell.

## Work run — negative

Used 102, 103, 104, 163, 42 and 7 as origins into every recovered object (`dbbi` 91,
`faed` 570, the 256-symbol object, the Bifid plaintext, and the 103-char Dualite
secondary): split-and-rotate at the index, delete the index, the character at the
index, windows of 8/16/32/64 from it, and every-nth readings. Plus the slot sums
157/143 and the blue/yellow letter strings.

```
1,455 candidates x 3 blobs x 8 modes = 34,920 trials   0 printable
```

## Standing

The follow-up's framing — that the live space is now small and discrete rather than
a billion-candidate sweep — is right, and its instinct to exploit an indexing
disagreement is the correct shape of move. But the disagreement it identified does
not exist: the pixel data is unambiguous, both candidate cells are white, and the
prime is 103, not 104.

---

# Third pass — index-as-stride

The follow-up correctly noted that using 42 / 104 / 163 as *scissors* (split-at-n)
is a different operator from using them as *index functions* (stride, modulus), and
that the latter was untried. Done.

## Method

Every recovered object — `dbbi` (91), `faed` (570), the 1075-token stream, the Bifid
plaintext (570), the 256-symbol object, and the 103-char Dualite secondary — read as:

- `src[off::stride]` for strides 2-17, 19, 23, 29, 31, 37, 41, 42, 43, 103, 104, 163,
  at offsets 0, 7, and 42/103/163 reduced mod the object length
- residue classes `src[i] for i % p == r`, for p in the primes to 43 and
  r in {0, 42 mod p, 104 mod p, 163 mod p}

Each resulting stream was scored automatically against the English trigram model so
nothing readable could be missed by eye.

## Result — negative

```
best score : -2.315/char   dbbi91[42::9] = "ffcebe"
```

That looks English-adjacent only because it is six characters long, where
per-character scoring is unstable. The top twenty are all 5-14 characters, none are
words, and two caveats apply:

1. **Short-string bias.** A 5-9 character stream over a 9-letter alphabet can score
   near English by chance. Length must be held constant before scores are compared.
2. **Scorer contamination.** The trigram model was built from text that includes the
   puzzle's own a-i streams, so it mildly rewards a-i sequences. Any future scoring
   of a-i material needs a model trained without them.

The only longer high scorer, `bifid570[0::12]`, is the `BCDE` even-parity stream
already shown to be a structural artifact of the ciphertext alphabet, not data.

Oracle: 2,558 candidates x 3 blobs x 8 modes = **61,392 trials, 0 printable**.

## What this closes

42, 104 and 163 as stride or modulus generators over any recovered object do not
emit `yellowblueprimes`, `yinyang`, or any English. Combined with the previous pass,
these numbers are now exhausted as both scissors and index functions.

## Standing

Three passes of increasingly specific, well-motivated hypotheses have each closed
negative. The numbers derived from the marked cell are spent. What has not been
touched remains what it was: a second reading of the picture that produces `yinyang`
as an *output*, which — if it depends on a page that was never archived — is missing
data rather than an unsolved computation.
