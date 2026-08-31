# Step 7 — the phase 3.2 cipher block

Date: 2026-08-31

## The object

Sitting between the Architect's speech and a 155-digit decimal string in the
decrypted phase 3.2 plaintext is a **1,539-byte block over exactly 26 distinct
byte values**:

```
%  ,  /  :  >  ?  [  _  `  À  Á  Â  Ã  Å  Ç  È  É  Ê  Ë  Ì  Í  Î  Ï  Ñ  ö  ø
```

Twenty-six symbols is a one-to-one alphabet for A-Z. Stored as
`data/phase32_cipher_block.txt`.

## Key length is 15

Index of coincidence over the block, by candidate key length:

```
L= 1  0.0406      L=10  0.0487      L=20  0.0483
L= 3  0.0442      L=12  0.0448      L=25  0.0475
L= 5  0.0482      L=15  0.0645  <-  L=30  0.0654  (multiple of 15)
```

English prose sits at 0.0667 and random at 0.0385. **L = 15** is the period; the
L = 30 peak is its multiple. This is decisive — the block is a polyalphabetic
cipher of period 15 over English plaintext, which matches the write-ups' claim
that a Beaufort cipher is involved.

## The alphabet is permuted

Mapping the 26 symbols to A-Z in byte order and solving each column by
chi-squared against English frequencies gives, for Beaufort and Vigenère
respectively:

```
key RQELATPCBQAGIHJ  ->  WBDQBTISCRMGOLHDBBECUDFCWHBUFKCWDIXECFAEE...
key LLPDWEWZVSLHMBU  ->  KEMSDWLLEHDTIVIDEOECVQYECIYCBFEJMAHLRYGUL...
```

Neither is English. So the symbol-to-letter table is **not** byte order — there is
an unknown alphabet permutation composed with the period-15 cipher. The IoC
result is unaffected by this, since IoC is invariant under any fixed permutation
of the alphabet, which is why the period is trustworthy while the naive decode is
not.

## Attack in progress

Simulated annealing over the 26! alphabet permutations, with the 15 key letters
re-solved by chi-squared at every step and the candidate plaintext scored by an
English trigram model built from the stage plaintexts and community documentation
already held locally. Both Beaufort and Vigenère orientations, multiple restarts.

This is the standard attack for a polyalphabetic cipher with an unknown alphabet,
and 1,539 characters at period 15 gives roughly 103 characters per column — ample
for column-wise frequency solving once the permutation is right.

## Period confirmed twice, independently

Kasiski examination backs the index-of-coincidence result. Of 127 repeated
trigrams giving 184 inter-repeat distances, the factor 15 divides 117 of them —
and the other frequent factors (3, 5, 30) are its divisors and multiple:

```
factor 3 -> 145    factor 5 -> 124    factor 15 -> 117    factor 30 -> 58
```

Period 15 is not in doubt.

## The alphabet really is permuted

Mutual index of coincidence between column 0 and each other column, scanning all
26 relative shifts, produces a sharp peak in only **4 of 15** columns (ratio of
best to second-best above 1.15). If the symbol-to-letter table were byte order,
every column would peak sharply. It does not, so the table is a non-order-
preserving permutation.

## The plaintext is not English

This is the useful negative. Calibrating the trigram scorer on 1,539-letter
samples:

| text | score per letter |
|---|---|
| real English (the phase 3 plaintext) | **-2.722** |
| uniform random letters | **-3.980** |
| best the annealer reaches, 25+ restarts, both orientations | **-3.774** |

The scorer separates English from random by 1.258 per letter, so it is perfectly
capable of recognising English at this length. The search plateaus at 0.206 above
random — about 16% of the way — and independent restarts with completely different
keys and permutations converge to the same plateau (-5809, -5808, -5808, -5790).
That is the signature of no English signal to find, not of a search that needs
more time.

**Conclusion: this block is a period-15 polyalphabetic cipher over a plaintext that
is not English text.** Its plaintext is most likely a further encoded layer —
another symbol alphabet, base64, or digits — consistent with the puzzle's own claim
of stacked ciphers.

This matters for anyone continuing: attacking this block with an English-language
solver cannot work, and the published description of a "Beaufort-decoded speech"
does not apply to this object. The readable Architect speech is already in
cleartext at the top of the phase 3.2 plaintext; it was never inside this block.
