# Step 1 — sweep of primary-material candidates

Date: 2026-08-31

## Method

`tools/gen.py` builds candidates from primary material only, since the community's
own candidate corpora were never published (only their counts were):

1. curated puzzle vocabulary — stage answers, the seven XOR-chain tokens, decoded
   page strings, prize addresses, the phase-3 composite password
2. every word token from the two community repositories' documentation
3. concatenated word windows (1-6 words) from those documents' prose
4. dynamic construction — permutations of the 19-token core set taken 2, 3, 4 and 5
   at a time, plus 4-combinations (the "concatenations, permutations, chained
   transforms" shape a historical replay never reached)
5. SHA-256 / MD5 hex digests of every core token, since the author demonstrably uses
   digests of tokens as key ingredients
6. every candidate also emitted reversed, per the author's earliest hint "esrever"

Each candidate is tried under **both** digests.

## Result

```
candidates       3,065,615
trials           6,131,230   (both digests)
PKCS7 survivors     24,183   (0.394%, matching random 1/256)
printable hits           0
wall clock            6.4 s
```

**Negative.** Highest printable ratio among survivors was 40.5%, consistent with
random bytes. No candidate produced a plaintext that reads as anything.

Full survivor log is reproducible from the tooling and is not committed.

## What this does and does not rule out

Rules out: the answer being any single token, word window, digest, reversal, or
short concatenation of known puzzle vocabulary drawn from published documentation —
under either digest.

Does not touch: the ~1,017 archived solver scripts' own run-time generation logic
(the highest-ranked open lead), the 1075-token final-page body itself, or the
256-symbol object as a source of candidate strings. All three need material that is
not reachable from this environment.
