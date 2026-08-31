#!/usr/bin/env python3
"""Decode the 570-character Bifid segment.

    segment [195:765], 570 symbols drawn from a-i
      -> Bifid decrypt, 5x5 square keyed DBIFHCEG over the J-omitted alphabet,
         period = full segment length
      -> 570 letters over A-Z, beginning BTCSEED
      -> odd-position stream (285) with I and O removed -> exactly 256 symbols
         over 23 letters

Why 5x5 and not 3x3: the puzzle's own hint says "Yellow has a number and so
does Blue". In the 14x14 image there are 9 yellow and 15 blue cells, and
a1z26 gives I = 9 and O = 15 -- the two letters this stage removes. For I and
O to be present at all, the Bifid output must be over A-Z, so the square is
5x5. The ciphertext happens to use only 9 of the 25 letters.

A 3x3 square over a-i also yields exactly 256 symbols after dropping 'i', but
that is a coincidence: 29,808 of the 362,880 possible 3x3 squares do, and none
can produce BTCSEED or contain an O.
"""
import sys

ALPHA = "ABCDEFGHIKLMNOPQRSTUVWXYZ"     # J omitted
KEY = "DBIFHCEG"


def square(key=KEY, alphabet=ALPHA):
    sq = []
    for ch in key + alphabet:
        if ch in alphabet and ch not in sq:
            sq.append(ch)
    return sq


def bifid_decrypt(ct, sq, n=5):
    pos = {ch: (i // n, i % n) for i, ch in enumerate(sq)}
    N = len(ct)
    stream = []
    for ch in ct:
        r, c = pos[ch]
        stream += [r, c]
    rows, cols = stream[:N], stream[N:]
    return "".join(sq[rows[i] * n + cols[i]] for i in range(N))


def main(path):
    seg = open(path).read().strip()[195:765].upper()
    sq = square()
    print("square      : " + "  ".join("".join(sq[i * 5:(i + 1) * 5]) for i in range(5)))
    out = bifid_decrypt(seg, sq)
    print(f"plaintext   : {len(out)} letters, starts {out[:7]!r} "
          f"{'OK' if out.startswith('BTCSEED') else 'FAIL'}")
    odd, even = out[1::2], out[0::2]
    obj = odd.replace("I", "").replace("O", "")
    print(f"odd stream  : {len(odd)} -> remove I,O -> {len(obj)} "
          f"{'OK' if len(obj)==256 else 'FAIL'}")
    print(f"alphabet    : {''.join(sorted(set(obj)))} ({len(set(obj))} letters)")
    print(f"even stream : {len(even)} symbols over {''.join(sorted(set(even)))} "
          f"({len(set(even))} letters)")
    print(f"\n{obj}")
    return 0 if out.startswith("BTCSEED") and len(obj) == 256 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "gsmg/data/salphaseion_stream.txt"))
