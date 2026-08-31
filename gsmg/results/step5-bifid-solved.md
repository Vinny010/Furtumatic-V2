# Step 5 — the Bifid segment, correctly decoded

Date: 2026-08-31

## Correction to step 3

Step 3 decoded the 570-character segment with a **3×3** square over `a-i` and
reported a 256-symbol object over 8 letters, calling the write-up's "23-letter
alphabet" an error. **That was my mistake, not theirs.** The write-up was right and
my square was wrong.

The 3×3 reading does produce exactly 256 symbols after dropping `i`, which is what
misled me — but I had already measured that 29,808 of the 362,880 possible 3×3
squares do the same, so hitting 256 was ~8% likely by chance and was never evidence.
The object it produced could not contain an `O` and could not spell `BTCSEED`.
Both should have been treated as disqualifying rather than as errors in the source.

## What the puzzle's own hint said

The author's second published hint reads:

> Roses are White but often Red.
> **Yellow has a number and so does Blue.**
> Go back to the first puzzle piece without further ado.
> It might have shown you only one door, beware that the rabbits nest may contain
> a whole lot more.

Counted from the authoritative `puzzle.png`: **15 blue cells, 9 yellow cells**.
Under a1z26 that is **O = 15** and **I = 9** — precisely the two letters this stage
removes. The hint names them.

For `I` and `O` to occur at all, the Bifid output must be over A-Z. So the square is
**5×5**, not 3×3; the ciphertext simply happens to use only 9 of the 25 letters.

## The decode

```
square      : DBIFH  CEGAK  LMNOP  QRSTU  VWXYZ      (key DBIFHCEG, J omitted)
plaintext   : 570 letters, starts 'BTCSEED'          OK
odd stream  : 285 -> remove I,O -> 256               OK
alphabet    : ABCDEFGHKLMNPQRSTUVWXYZ (23 letters)   OK
```

Every documented property now reproduces: the `BTCSEED` prefix, the 256 symbols,
and the 23-letter alphabet. `data/object256.txt` holds the object and
`data/bifid_plaintext.txt` the full 570-letter plaintext.

```
TSEDMKAHSHKDSKVXPHRQEDBNSDPGPNNSSGDLNMUUQADLZLMFFSWKYUWASWNMDARPGQGSNSLTSAPUSPRAN
KSDNEKKTLRNNCGLNUSGSNUFDAKNSSSRSBLRVDCGSVVDMPSGLGAWYAPGNYBGLRBRGBMRNGTDNFLPNRBBNR
RMLSALNQHQGXGFUEAATNGELELMKDBAMRMCMSGBMTLMDMMPSNSYNSBBNNCUECGMEUNELLAPPMXXRGBMNRD
CWAHTQPFHGXPL
```

## The even-parity stream is an artifact, not an object

An earlier version of this file called the even-parity stream "an object the
write-up does not mention" and logged it as an untouched lead. That was wrong,
and the reason is worth recording.

The 9 ciphertext letters `a-i` occupy only **rows 0 and 1** of the 5x5 square:

```
   D B I F H        A=(1,3)  B=(0,1)  C=(1,0)  D=(0,0)  E=(1,1)
   C E G A K        F=(0,3)  G=(1,2)  H=(0,4)  I=(0,2)
   L M N O P
   Q R S T U        rows used: {0,1}      cols used: {0,1,2,3,4}
   V W X Y Z
```

Bifid decryption builds `S = r0,c0,r1,c1,...` and reads
`plain[i] = square[S[i]][S[570+i]]`. Since 570 is even, for **even** `i` both
`S[i]` and `S[570+i]` are *row* values, which can only be 0 or 1. The four
reachable cells are (0,0)=D, (0,1)=B, (1,0)=C, (1,1)=E — so the even stream is
*forced* to `{B,C,D,E}` by the ciphertext alphabet. It carries no information.

For **odd** `i` both are *column* values in 0..4, so all 25 letters are reachable.
That is why the payload is the odd-position stream, and why the write-ups take it.

Treating the even stream as data was a false lead. Read as 2 bits per symbol under
all 24 letter-to-value assignments, both directions, it yields ~46% printable bytes
— indistinguishable from random, exactly as this analysis predicts.
