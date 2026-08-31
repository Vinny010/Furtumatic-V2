#!/usr/bin/env python3
"""Recover the straddling checkerboard behind the phase 3.2 digit string.

The 149-digit string in the phase 3.2 plaintext is VIC ciphertext. Its plaintext
is the message the community published, 91 letters. A straddling checkerboard
encodes 91 letters as 149 digits when 33 of them are single-digit, which the
lengths confirm exactly.

Given both plaintext and ciphertext, the board is recoverable: try each ordered
pair of escape digits, parse the ciphertext under it, and keep the pairs whose
code-to-letter mapping is one-to-one and consistent across all 91 positions.
Exactly one board survives.
"""
import itertools
import sys

PT = ("INCASEYOUMANAGETOCRACKTHISTHEPRIVATEKEYSBELONGTO"
      "HALFANDBETTERHALFANDTHEYALSONEEDFUNDSTOLIVE")


def solve(digits, plaintext=PT):
    for e1, e2 in itertools.permutations(range(10), 2):
        esc = {str(e1), str(e2)}
        codes, i = [], 0
        while i < len(digits):
            if digits[i] in esc:
                if i + 1 >= len(digits):
                    codes = None
                    break
                codes.append(digits[i:i + 2]); i += 2
            else:
                codes.append(digits[i]); i += 1
        if not codes or len(codes) != len(plaintext):
            continue
        c2l, l2c = {}, {}
        for c, l in zip(codes, plaintext):
            if c2l.get(c, l) != l or l2c.get(l, c) != c:
                break
            c2l[c], l2c[l] = l, c
        else:
            return (e1, e2), c2l
    return None, None


def main(path):
    digits = open(path).read().strip()
    print(f"ciphertext: {len(digits)} digits, plaintext: {len(PT)} letters")
    single = 2 * len(PT) - len(digits)
    print(f"implies {single} single-digit and {len(PT)-single} double-digit letters")

    esc, board = solve(digits)
    if not board:
        print("no consistent board")
        return 1
    print(f"\nescape digits: {esc[0]} and {esc[1]}\n")
    print("      " + " ".join(str(i) for i in range(10)))
    print("      " + " ".join(board.get(str(k), ".") for k in range(10)))
    for e in esc:
        print(f"  {e}   " + " ".join(board.get(f"{e}{k}", ".") for k in range(10)))

    out, i = "", 0
    while i < len(digits):
        c = digits[i:i + 2] if digits[i] in {str(esc[0]), str(esc[1])} else digits[i]
        out += board.get(c, "?"); i += len(c)
    print(f"\ndecoded: {out}")
    print(f"matches published plaintext: {out == PT}")
    return 0 if out == PT else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "gsmg/data/phase32_vic_digits.txt"))
