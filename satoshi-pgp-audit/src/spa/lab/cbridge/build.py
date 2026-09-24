"""Assemble and compile the differential harness from pinned GnuPG source.

Produces one binary per GnuPG version, each containing that version's genuine
mix_pool() and RIPEMD-160 compression function.
"""

import subprocess
import sys
from pathlib import Path

from .extract import extract_from_file

HERE = Path(__file__).parent
RMD_FUNCS = ["rmd160_init", "transform", "rmd160_mixblock"]
RANDOM_FUNCS = ["mix_pool"]


def generate_source(gnupg_tree: Path) -> str:
    """Build a single translation unit: shim + extracted upstream functions + main."""
    rmd = gnupg_tree / "cipher" / "rmd160.c"
    rnd = gnupg_tree / "cipher" / "random.c"
    if not rmd.exists() or not rnd.exists():
        raise FileNotFoundError("expected GnuPG source tree at %s" % gnupg_tree)
    parts = [
        '#include "shim.h"',
        "/* ==== extracted verbatim from cipher/rmd160.c ==== */",
        "static void transform( RMD160_CONTEXT *hd, byte *data );",
        extract_from_file(rmd, RMD_FUNCS),
        "/* ==== extracted verbatim from cipher/random.c ==== */",
        extract_from_file(rnd, RANDOM_FUNCS),
        "/* ==== harness ==== */",
        (HERE / "harness_main.c").read_text(),
    ]
    return "\n\n".join(parts)


def build(gnupg_tree: Path, out_binary: Path, cc: str = "cc") -> Path:
    src = generate_source(gnupg_tree)
    gen = out_binary.with_suffix(".gen.c")
    gen.parent.mkdir(parents=True, exist_ok=True)
    gen.write_text(src)
    cmd = [cc, "-O2", "-std=gnu89", "-w", "-I", str(HERE), str(gen), "-o", str(out_binary)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("compile failed:\n%s\n%s" % (" ".join(cmd), proc.stderr))
    return out_binary


def run_mix(binary: Path, pool: bytes, rounds: int = 1) -> bytes:
    if len(pool) != 600:
        raise ValueError("pool must be 600 bytes")
    proc = subprocess.run([str(binary), str(rounds)], input=pool,
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError("harness failed: %s" % proc.stderr.decode())
    return proc.stdout


if __name__ == "__main__":  # pragma: no cover
    tree, out = Path(sys.argv[1]), Path(sys.argv[2])
    print("built", build(tree, out))
