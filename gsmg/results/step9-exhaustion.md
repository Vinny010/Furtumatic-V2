# Step 9 — the subset-XOR space is exhausted

Date: 2026-08-31

## The 2^26 sweep, both blob variants

Every subset of a 26-token vocabulary — the seven proven page tokens, the VIC board
words recovered in step 8, and the stage vocabulary — XOR-chained over their SHA-256
digests, against both blob reconstructions under four password modes:

```
variant A   67,108,863 candidates   536,870,904 trials   2,104,556 survivors   0 printable
variant B   67,108,863 candidates   536,870,904 trials   2,106,605 survivors   0 printable
```

Negative. The enumeration provably contains the real Dualite key as a positive
control, so the space and the machinery are both sound.

**The XOR-subset construction is now exhausted** for every vocabulary that can be
assembled from the pages held here. Repeating it with more tokens is not a
different experiment.

## Running total

```
steps 1-2   documentation + live page material          ~4.6M candidates
step 3      all 9! Bifid square orderings                362,880
step 3b     2^23 masks over the 256-symbol object     16,777,216
step 4b     2^24 subset XOR                           16,777,215
step 8      VIC board and its prose                       12,625
step 8b     2^26 subset XOR, both variants           134,217,726
step 9      all corpora vs the phase 3.2 tail blob      4,181,110
                                                    ---------------
                                                    ~1.7 billion trials
                                                    0 printable plaintexts
```

## The one object left uncracked

The phase 3.2 plaintext ends with a further OpenSSL blob, stored as
`data/phase32_tail_blob.b64`:

```
96 bytes, Salted__, salt b45a5e3d827593ca, 80 bytes of ciphertext
```

Same shape as the final gate — which by the same arithmetic means its plaintext is
64 to 79 bytes, too large for a bare key.

Neither community write-up documents anything past phase 3.2. They reached the
final page by hashing the first puzzle's text, so this blob, and the white rabbit
and Architect Choice pages behind it, are undocumented territory rather than solved
ground.

All corpora assembled so far were swept against it: 4,181,110 candidates,
33,448,880 trials, 0 printable. The 2^26 subset enumeration against it is running
separately.

## The riddle attached to it

The text immediately above the blob is its password clue:

> "Raising the stakes without extra chances of winning. A fubcd-king &
> oracle-queen, thingky mvps, on a sad board but as wide as the first one seen."

Step 8 established that `fubcd`, `thingky` and `mvps` name the VIC checkerboard
rows. The Architect's line further up, "One for one, four for one", names its escape
digits — 1 and 4. So this sentence's cipher content is already spent on the VIC
stage, and whatever answers *this* blob is a second reading of the same words, or
something not yet identified. Every literal phrase and word window from the page is
already in the swept corpora.
