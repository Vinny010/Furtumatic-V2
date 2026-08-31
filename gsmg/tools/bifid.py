#!/usr/bin/env python3
"""Decode the 570-character Bifid segment and emit the 256-symbol object.

    segment [195:765]  570 symbols over a-i
      -> Bifid decrypt, 3x3 square keyed DBIFHCEG (+ 'a'), period = full length
      -> 570 symbols over a-i
      -> odd-position stream (285)
      -> remove 'i'  ->  exactly 256 symbols over 8 letters (a-h)

DBIFHCEG is exactly {b..i}, so appending 'a' completes the 9-letter alphabet;
that is why the square is 3x3 and why the output alphabet is a-i.
"""
import sys

ALPHA = "abcdefghi"
KEY = "dbifhceg"


def square(key=KEY, alpha=ALPHA):
    sq = []
    for ch in key + alpha:
        if ch not in sq:
            sq.append(ch)
    return sq


def bifid_decrypt(ct, sq):
    pos = {ch: (i // 3, i % 3) for i, ch in enumerate(sq)}
    n = len(ct)
    stream = []
    for ch in ct:
        r, c = pos[ch]
        stream += [r, c]
    rows, cols = stream[:n], stream[n:]
    return "".join(sq[rows[i] * 3 + cols[i]] for i in range(n))


def main(path):
    body = open(path).read().strip()
    seg = body[195:765]
    sq = square()
    print("square      : " + " / ".join(" ".join(sq[i:i + 3]) for i in (0, 3, 6)))
    out = bifid_decrypt(seg, sq)
    print(f"bifid output: {len(out)} symbols over {''.join(sorted(set(out)))}")
    odd = out[1::2]
    obj = odd.replace("i", "").replace("o", "")
    print(f"odd stream  : {len(odd)} -> remove i/o -> {len(obj)} "
          f"{'OK' if len(obj)==256 else 'FAIL'}")
    print(f"alphabet    : {''.join(sorted(set(obj)))} ({len(set(obj))} letters)")
    print(f"\n{obj}")
    return 0 if len(obj) == 256 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "gsmg/data/salphaseion_stream.txt"))
