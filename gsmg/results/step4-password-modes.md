# Step 4 — password modes, and the subset-XOR space

Date: 2026-08-31

## An assumption nobody had tested

Every sweep of the small blob — the community's and my steps 1-3 — assumed

```
password = sha256(X).hexdigest()      a 64-character ASCII string
```

But the **only known-good password on this page** does not look like that. The
Dualite blob's password is the XOR chain of seven token digests, fed to
EVP_BytesToKey as **32 raw bytes**:

```
password = bytes.fromhex("a795de117e472590e572dc193130c763e3fb555ee5db9d34494e156152e50735")
```

Raw, not hex text. So the assumed form was never validated against the one example
the page actually gives us.

`tools/gate3.c` therefore tries four password forms per candidate, times two
digests — eight trials each:

| mode | password |
|---|---|
| `sha256hex` | `sha256(X)` as 64-char hex text (the assumed form) |
| `sha256raw` | `sha256(X)` as 32 raw bytes |
| `literal` | X itself |
| `hexdecode` | `bytes.fromhex(X)` when X is a hex string — the Dualite form |

Each mode is self-tested against a synthetic blob built to need exactly that mode,
with an instruction-shaped plaintext. All four are caught.

## A second correction: XOR cancels

The published token list for the Dualite key is seven long, with `matrixsumlist`
appearing twice. XOR is self-inverse, so it cancels itself:

```
XOR of the 5 non-repeated tokens == the published 7-token chain    (verified)
```

The construction is therefore over **subsets**, not sequences. Order is irrelevant
and repeats are noise. That collapses what looked like a permutation space into
`2^n` subsets — for a 24-token page vocabulary, 16,777,216 candidates, which is
fully enumerable.

`tools/xorgen.c` walks that space by Gray code, flipping one digest per step.
Positive control: the enumeration provably contains the published Dualite key, so
it covers the one construction the author is known to have used.

## Results

Full corpus (4,149,522 candidates: documentation, page material, all 9! Bifid
outputs, mask candidates) under all four modes:

```
variant A   4,149,522 candidates   24,897,132 trials   98,095 survivors   0 printable
variant B   4,149,522 candidates   24,897,132 trials   97,301 survivors   0 printable
```

Subset-XOR space (2^24) against both variants: see the sweep log; the run is
recorded in this file's companion commit.

Negative so far. What it buys is that the password *form* is no longer an
untested assumption — all four plausible forms are now covered, including the only
one the page demonstrates.
