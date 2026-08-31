# Kangaroo feasibility — what a known public key buys

Date: 2026-08-31

## The public key of the funded address is exposed

`1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe` has spent twice (2020-05-11, 2024-04-24), so
its uncompressed public key is on-chain:

```
04f4d1bbd91e65e2a019566a17574e97dae908b784b388891848007e4f55d5a46
49c73d25fc5ed8fd7227cab0be4e576c0c6404db5aa546286563e4be12bf33559
```

Verified here: HASH160 + Base58Check on those bytes reproduces
`1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe` exactly.

`17ucy1K9ZUAaoY6JVtM932W9jUp5LXfyHa` (3.7505531 BTC) has **never spent**, so its
public key is unknown and no discrete-log method applies to it at all. Only the
1.2563451 BTC address is reachable this way.

## What we do NOT have

"Half" and "Better half" are **two complete 256-bit private keys** for two other,
empty addresses. They are not fragments of either funded address's key. We hold no
bits — first half, second half or otherwise — of the key behind
`1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe`.

## What Kangaroo would cost if we did

Pollard's Kangaroo solves the discrete log inside a known interval of width W in
about `2*sqrt(W)` group operations. At an assumed 1.5e9 ops/sec for one RTX 3090:

| known bits | interval | kangaroo ops | one 3090 |
|---|---|---|---|
| 216 | 2^40 | 2.1e6 | instant |
| 196 | 2^60 | 2.2e9 | 1.4 seconds |
| 176 | 2^80 | 2.2e12 | 24 minutes |
| 156 | 2^100 | 2.3e15 | 17 days |
| 136 | 2^120 | 2.3e18 | 49 years |
| 128 | 2^128 | 3.7e19 | 779 years |
| 96 | 2^160 | 2.4e24 | 5.1e7 years |

Brute force over 2^128 without Kangaroo, same hardware: 7.2e21 years. So Kangaroo
is worth a factor of ~10^19 — and half a key is *still* 779 years on one card.

Either half works, not just the leading one. With high bits known the interval is
contiguous and Kangaroo applies directly. With the low `m` bits known,
`k = L + 2^m*x`, so solving `P - L*G = x*(2^m*G)` recovers `x` over an interval of
`2^(256-m)` against the base point `2^m*G`.

## Why this matters

The exposed public key changes what the puzzle's answer has to contain. It does
**not** need to hand over a key. It only needs to bound the key to an interval:

- an answer narrowing the key to **2^80 or less** finishes on a single 3090 in
  under half an hour
- **2^60 or less** finishes in about a second

That is a far weaker requirement than "the plaintext is the private key", and it
fits the blob's measured 64-79 byte plaintext comfortably — a range specifier, an
offset and a width, or a base point plus a bound.

It also fits the author's demonstrated style. Every solved step of this puzzle ends
in a coordinate or a base change rather than a value: the Dualite chain reaches its
keys through 103x103 row/column sums and a base-38 decode, and the z-segments decode
by reading digits as decimal and shifting to base 16.

So the search should not assume the blob contains a key. A short interval
specification is both sufficient and more consistent with everything else on the
page.
