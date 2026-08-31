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
