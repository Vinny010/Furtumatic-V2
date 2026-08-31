# Step 8 — the VIC straddling checkerboard, recovered

Date: 2026-08-31

## The object

Below the cipher block in the phase 3.2 plaintext sits a **149-digit** decimal
string, quoted by neither community write-up. It is stored as
`data/phase32_vic_digits.txt`.

It is not a1z26 — the greedy parse has **zero** valid readings. It is not the
author's decimal-to-base-16 trick either; that yields non-ASCII.

## It is VIC ciphertext, and the board is recoverable

The community publishes the VIC plaintext but not the key. The lengths give the
key away:

```
plaintext  91 letters
ciphertext 149 digits
=> 33 single-digit letters + 58 double-digit = 149      exact
```

That is a straddling checkerboard. With both plaintext and ciphertext in hand the
board is solvable directly: for each ordered pair of escape digits, parse the
ciphertext and keep the pairs whose code-to-letter map is one-to-one and
consistent across all 91 positions. Exactly one board survives (twice, once per
escape ordering).

```
      0 1 2 3 4 5 6 7 8 9
      F . U B . C D O R A        escapes: 1 and 4
  1   . L E T H I N G K Y
  4   M V P S . . . . . .
```

Decoding the 149 digits under it reproduces the published plaintext byte for byte:

```
INCASEYOUMANAGETOCRACKTHISTHEPRIVATEKEYSBELONGTOHALFANDBETTERHALFANDTHEYALSONEEDFUNDSTOLIVE
```

`tools/vic.py` does this from the digit string alone.

## The page states the board in prose

Immediately above the digits, the phase 3.2 plaintext reads:

> "Raising the stakes without extra chances of winning. A **fubcd**-king &
> **oracle**-queen, **thingky mvps**, on a sad board but as wide as the first one
> seen."

Against the recovered board:

| phrase | board |
|---|---|
| `fubcd` | F U B C D — digits 0, 2, 3, 5, 6 |
| `oracle` | O R A at 7, 8, 9 then L E at 11, 12 |
| `thingky` | T H I N G K Y — digits 13 through 19 |
| `mvps` | M V P S — digits 40 through 43 |

The sentence is the key, written out. That confirms the board independently of the
plaintext-crib derivation, and it means the board is *intended* to be readable
material rather than a byproduct.

## Board letters in digit order

```
FUBCDORA ? LETHINGKY MVPS
```

Twenty-one letters placed. Seven slots stay empty (10, and 44 through 49) because
the 91-letter plaintext never uses J, Q, W, X or Z; they cannot be recovered from
this ciphertext. Note the tail `M V P S` is not alphabetical, so the board is a
fully mixed key, not a keyword followed by the remaining alphabet in order.

## Swept

Candidates from the board and its prose — the board string, all 120 fillings of the
five unused letters into the seven empty slots, the named phrases, the decoded
message, concatenations and digests: 12,625 candidates, four password modes, both
blob variants.

```
variant A   12,625 candidates   101,000 trials   332 survivors   0 printable
variant B   12,625 candidates   101,000 trials   338 survivors   0 printable
```

Negative. A 2^26 subset-XOR enumeration adding the new board tokens to the page
vocabulary is running separately.
