# Page capture and derived data

## salphaseion_page.mhtml

MHTML capture of the puzzle's final page,
`https://gsmg.io/89727c598b9cd1cf8873f27cb7057f050645ddb6a7a157a110239ac0152f6a32`,
taken 2026-08-31. That URL is derived and verified as
`sha256("GSMGIO5BTCPUZZLECHALLENGE1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe")`.

The page is two `<textarea>` elements under the headings "SalPhaseIon" and
"Cosmic Duality", plus a stylesheet. Nothing else.

`tools/parse_page.py` re-derives every published decoding from this capture alone.
All checks pass:

```
body tokens              : 1075  OK
a/b run [91:195]         : 'matrixsumlist'  OK
a/b run [959:999]        : 'enter'  OK
z-segment (63 chars)     : 'lastwordsbeforearchichoice'  OK
z-segment (29 chars)     : 'thispassword'  OK
small blob               : 96 bytes, Salted__, salt 3ab585348552415d, ct 80
Dualite blob             : 1344 bytes, salt 2d3f6fe06dc950e6
```

## blob.b64 — verified, with a caveat worth knowing

The small blob **matches** the transcription published in
`floflo777/open-crypto-puzzles`, byte for byte. The earlier caveat is resolved.

But it is **not a verbatim substring of the page**. The page's base64 run is
interrupted:

```
[895:959]  U2FsdGVkX186tYU0hVJBXXUnBUO7C0+X4KUWnWkCvoZSxbRD3wNsGWVHefvdrd9z   64 chars
[959:999]  abbaabababbabbbaabbbabaaabbaabababbbaaba                           40 chars -> "enter"
[999:1064] QvX0t8v3jPB4okpspxebRi6sE1BMl5HI8Rku+KejUqTvdWOX6nQjSpepXwGuN/jJs  65 chars
[1064:]    habefanstoo
```

Reaching 128 base64 characters requires two edits: **delete the 40-character
`enter` run sitting inside the ciphertext**, and **drop the trailing `s` of the
second part** (that `s` starts `shabefanstoo`). Both are load-bearing assumptions
inherited from the community reconstruction, not facts about the page.

`a` and `b` are themselves valid base64 characters, so the `enter` run is not
self-evidently foreign to the blob. Alternative reconstructions have not been
swept.

## salphaseion_stream.txt

The 1075-token body with whitespace stripped. Structure:

| range | len | content |
|---|---|---|
| 0-91 | 91 | a-i tokens |
| 91-195 | 104 | binary -> `matrixsumlist` |
| 195-765 | 570 | the Bifid segment (keyed square `DBIFHCEG`, period 570) |
| 765-895 | 130 | z-delimited digit segments + `ourfirsthintisyourlastcommand` |
| 895-1075 | 180 | base64 blob with `enter` embedded, then `habefanstoo` |

`shabef` appears twice and is the page's own hint: under a=1..z=26 it reads
`sha256` (b=2, e=5, f=6). The final `shabefanstoo` is `sha256` + `anstoo`.

## dualite.b64

The large "Cosmic Duality" blob: 1344 bytes, salt `2d3f6fe06dc950e6`. Already
decrypted by the community; its password is the XOR chain of the SHA-256 digests
of seven tokens, verified in this repo to reproduce
`a795de117e472590e572dc193130c763e3fb555ee5db9d34494e156152e50735` byte-exact.
