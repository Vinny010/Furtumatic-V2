#!/usr/bin/env python3
"""Parse the SalPhaseIon final page and re-derive every published decoding from it.

Usage: parse_page.py [data/salphaseion_page.mhtml]

Verifies, from the page bytes alone:
  * the body is exactly 1075 single-character tokens
  * the two a/b runs decode to "matrixsumlist" and "enter"
  * the two z-delimited segments decode to "lastwordsbeforearchichoice"
    and "thispassword" via abcdefghio->1234567890, read as a decimal
    number, converted to base 16, read as hex ASCII
  * the small AES blob reconstructs to the 128 base64 characters the
    community uses -- which is NOT a verbatim page substring
"""
import re
import sys
import base64

EXPECT = {
    "matrixsumlist": (91, 195),
    "enter": (959, 999),
}


def load(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    areas = re.findall(r"<textarea[^>]*>(.*?)</textarea>", raw, re.S)
    if len(areas) != 2:
        raise SystemExit(f"expected 2 textareas, found {len(areas)}")
    return re.sub(r"\s+", "", areas[0]), re.sub(r"\s+", "", areas[1])


def ab_decode(run):
    bits = run.replace("a", "0").replace("b", "1")
    return "".join(chr(int(bits[i:i + 8], 2)) for i in range(0, len(bits), 8))


def digit_decode(seg):
    digits = seg.translate(str.maketrans("abcdefghio", "1234567890"))
    h = format(int(digits), "x")
    if len(h) % 2:
        h = "0" + h
    return bytes.fromhex(h).decode("ascii")


def main(path):
    stream, dualite = load(path)
    ok = True

    print(f"body tokens              : {len(stream)}  {'OK' if len(stream)==1075 else 'FAIL'}")
    ok &= len(stream) == 1075

    for want, (a, b) in EXPECT.items():
        got = ab_decode(stream[a:b])
        print(f"a/b run [{a}:{b}]{'':<10}: {got!r}  {'OK' if got==want else 'FAIL'}")
        ok &= got == want

    segs = stream[765:895].split("z")
    for seg, want in ((segs[1], "lastwordsbeforearchichoice"), (segs[2], "thispassword")):
        got = digit_decode(seg)
        print(f"z-segment ({len(seg):2d} chars){'':<7}: {got!r}  {'OK' if got==want else 'FAIL'}")
        ok &= got == want

    tail = stream[895:]
    p1, p2 = tail[:64], tail[104:169]
    blob_b64 = p1 + p2[:-1]           # drop the trailing 's', which begins "shabefanstoo"
    raw = base64.b64decode(blob_b64)
    print(f"small blob               : {len(raw)} bytes, {raw[:8].decode()}, "
          f"salt {raw[8:16].hex()}, ct {len(raw)-16}")
    ok &= len(raw) == 96 and raw[:8] == b"Salted__"

    # the community's 128-char blob deletes the embedded "enter" run and the
    # trailing 's'; it is a reconstruction, not a page substring
    print(f"blob is page substring   : {blob_b64 in stream}  (expected False)")

    big = base64.b64decode(dualite)
    print(f"Dualite blob             : {len(big)} bytes, salt {big[8:16].hex()}")

    print("\nALL CHECKS PASS" if ok else "\nFAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "gsmg/data/salphaseion_page.mhtml"))
