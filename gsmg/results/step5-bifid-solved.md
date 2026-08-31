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

## An object the write-up does not mention

Splitting the Bifid plaintext by parity gives two streams. The published account
discusses only the odd one. The **even** stream is 285 symbols over exactly **four**
letters — `B`, `C`, `D`, `E` — which is 2 bits per symbol, 570 bits:

```
BCEDEECEDBCDBCDDBCCCCDCBEBDCDBCDCDCCECDCEBCDCCCEDECEDEDDCBCBBEBBEEEDBCBBCEBEEBBED
DDECCECCCCCBDCCCBEECEECCBBEEEDEDBCDBDECBEBBEDCBCEBEBBCECCCEDEDDDCCEEBECCCDBDDDECC
DCBCCCDBBECEEEEDDDECBCDDBECCEEDCEDCDEEDEDEBCEBECCDECCCCDCCDDBCBBDBDBDEECEBEBCBCCE
DCBCCDCEDBDEBBCCCDDDDCCDDDEDEDBDCCDEDDDDCE
```

A 4-letter alphabet is a strong signal of deliberate encoding — base 4, or two bits
per symbol — and it is a separate object of the same size as the one everyone has
been attacking. It is recorded here as an untouched lead.
