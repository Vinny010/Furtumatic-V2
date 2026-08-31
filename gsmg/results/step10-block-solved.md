# Step 10 — RETRACTED: the phase 3.2 block was already solved publicly

Date: 2026-08-31

## Retraction

An earlier version of this file claimed the 1,539-symbol block had been decoded
here for the first time, and that "no community write-up contains this
plaintext." **Both claims were false.**

`puzzlehunt/gsmgio-5btc-puzzle`'s README contains the block's complete plaintext,
its letter-form transcription, and its key, at lines 292-320. That file was on
disk throughout this work and was used as training data for the solver's trigram
model.

## What actually happened

The annealer reconstructed text that was present in its own language model. That
is why the fit degraded outside the region the model had memorised: fitting column
maps on the first half and applying them to the second half scored -3.575/char
against -2.593 for English and -3.886 for random, only about a third of the way.
A genuine solve generalises; this did not.

The "new findings" reported from the decode were misreadings of already-published
text:

| reported here | actually published |
|---|---|
| "wordfording might be required" | "**brute forcing** might be required" |
| "reinserting the prime basis" | "reinserting the prime **basics**" |
| "a wise [ ] move hinted at" | "a **wiseman above** hinted at" |
| "us [bufs] at GSMG" | "us **guys** at GSMG" |
| "Ciao [mella] o" | "Ciao **bella** o" |

None of these were discoveries.

## The actual solution, verified here

```
symbols : %  ,  /  :  >  ?  [  _  `  À  Á  Â  Ã  Å  Ç  È  É  Ê  Ë  Ì  Í  Î  Ï  Ñ  ö  ø
letters : l  k  a  z  n  o  c  m  y  d  e  b  f  g  h  t  q  r  s  x  u  v  w  i  j  p

then Beaufort with key THEMATRIXHASYOU (15 letters)
-> YOURLIFEISTHESUMOFAREMAINDEROFANUNBALANCEDEQUATIONINHERENTTOTHEPROGRAMMINGOFTHISPUZZLE...
```

Verified: the published letter-string is 1,539 characters and maps one-to-one onto
this block's symbols; the Beaufort decrypt reproduces the published plaintext.

## What does survive from this work

Two results here were derived independently of the published material and remain
correct:

1. **The period is 15.** Index of coincidence (0.0645 against 0.0667 for English)
   and Kasiski (factor 15 dividing 117 of 184 inter-repeat distances). Recovered
   before any contact with the published key — and the published key,
   `THEMATRIXHASYOU`, is exactly 15 letters.
2. **The symbol-to-letter table is not byte order.** Confirmed against the real
   mapping above, which is a scrambled alphabet.

The step-7 conclusion that the plaintext "is not English" was also wrong, and the
step-7 diagnosis of *why* the first solver failed (chi-squared key re-solving makes
the objective discontinuous) was right — but the fix was not "15 independent
alphabets". The single-permuted-alphabet model in `tools/quagmire.c` was already
adequate to express the true solution; the search simply never reached it.

## Lesson recorded

The language model used to score a cipher solve must be verified free of the target
text. It was not, and a contaminated model turned a reconstruction into an apparent
discovery.
