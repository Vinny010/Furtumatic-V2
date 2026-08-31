#!/usr/bin/env python3
"""Decode the GSMG.IO stage-1 14x14 grid from a screenshot of gsmg.io/puzzle.

Reading order : counter-clockwise spiral, inward, from top-left
Bit mapping   : black = 1, white = 0, blue = 1, yellow = 0
Chunking      : 8-bit ASCII -> 24 chars -> "gsmg.io/theseedisplanted"

The 24 coloured cells all land on spiral index = 7 (mod 8), i.e. the
least-significant bit of each character: they are byte-boundary markers whose
values are fully determined by the plaintext, not an independent payload.
The 2x2 spiral centre carries no data and is where the white rabbit is drawn.
"""
import sys
import numpy as np
from PIL import Image

N = 14


def classify(px):
    r, g, b = px
    if b > 110 and b > r + 40 and b > g + 40:
        return "U"  # blue
    if r > 170 and g > 150 and b < 120:
        return "Y"  # yellow
    return "1" if r + g + b > 450 else "0"  # white / black


def find_grid(a):
    """Locate the grid: full image width, bounded below by the red rule."""
    for y in range(a.shape[0] // 2, a.shape[0]):
        r, g, b = a[y].mean(axis=0)
        if r > 120 and g < 80 and b < 80:
            return y - a.shape[1], a.shape[1] / N
    raise SystemExit("could not locate the red rule under the grid")


def extract(path):
    a = np.array(Image.open(path).convert("RGB")).astype(int)
    top, cell = find_grid(a)
    grid = []
    for row in range(N):
        line = []
        for col in range(N):
            cy = int(top + (row + 0.5) * cell)
            cx = int((col + 0.5) * cell)
            patch = a[cy - 30:cy + 31, cx - 30:cx + 31].reshape(-1, 3)
            # median, not mean: the rabbit's line art skews the mean
            line.append(classify(np.median(patch, axis=0)))
        grid.append(line)
    return grid


def spiral():
    t, b, l, r = 0, N - 1, 0, N - 1
    out = []
    while t <= b and l <= r:
        for i in range(t, b + 1):
            out.append((i, l))
        for i in range(l + 1, r + 1):
            out.append((b, i))
        if l < r:
            for i in range(b - 1, t - 1, -1):
                out.append((i, r))
        if t < b:
            for i in range(r - 1, l, -1):
                out.append((t, i))
        t, b, l, r = t + 1, b - 1, l + 1, r - 1
    return out


def main(path):
    grid = extract(path)
    print("\n".join("".join(r) for r in grid), "\n")
    order = spiral()
    seq = [grid[r][c] for r, c in order]
    bits = [{"1": "0", "0": "1", "U": "1", "Y": "0"}[ch] for ch in seq]
    text = "".join(chr(int("".join(bits[i:i + 8]), 2)) for i in range(0, 192, 8))
    print("decoded :", repr(text))
    print("residual:", seq[192:], "(spiral centre, no data)")

    coloured = [(i, ch) for i, ch in enumerate(seq) if ch in "UY"]
    print("coloured cells:", len(coloured))
    print("all on bit 7 of a byte:", all(i % 8 == 7 for i, _ in coloured))
    colour = "".join("1" if ch == "U" else "0" for _, ch in coloured)
    lsb = "".join(str(ord(c) & 1) for c in text)
    print("colour bits :", colour)
    print("char LSBs   :", lsb)
    print("identical   :", colour == lsb)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "puzzle.png")
