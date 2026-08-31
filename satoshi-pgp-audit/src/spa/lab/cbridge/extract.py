"""Extract exact function bodies from pinned GnuPG source.

Functions are lifted programmatically rather than copied by hand, so the C compiled
into the differential harness is byte-identical to the pinned upstream tree. If
upstream ever changed, the extraction would change with it and the test would fail
loudly instead of silently comparing against a stale hand-copy.
"""

import re
from pathlib import Path
from typing import List


class ExtractionError(RuntimeError):
    pass


def extract_function(source: str, name: str) -> str:
    """Return the full text of a K&R/ANSI C function definition named ``name``.

    GnuPG 1.4.x puts the return type on its own line, so the function name starts a
    line. We anchor on that, then brace-match to the closing brace.
    """
    pattern = re.compile(r"^%s\s*\(" % re.escape(name), re.MULTILINE)
    m = pattern.search(source)
    if not m:
        raise ExtractionError("function %r not found" % name)
    # Walk backwards over the return type / storage class lines.
    start = m.start()
    lines_before = source[:start].rstrip("\n").split("\n")
    prefix: List[str] = []
    for line in reversed(lines_before):
        st = line.strip()
        if not st or st.endswith((";", "}", "*/")) or st.startswith(("#", "/*")):
            break
        prefix.insert(0, line)
        if st in ("static void", "void", "static", "static int", "int"):
            break
    body_start = source.index("{", m.end() - 1)
    depth = 0
    i = body_start
    in_line_comment = in_block_comment = in_string = in_char = False
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
        elif in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_string:
            if ch == "\\":
                i += 1
            elif ch == '"':
                in_string = False
        elif in_char:
            if ch == "\\":
                i += 1
            elif ch == "'":
                in_char = False
        elif ch == "/" and nxt == "/":
            in_line_comment = True
            i += 1
        elif ch == "/" and nxt == "*":
            in_block_comment = True
            i += 1
        elif ch == '"':
            in_string = True
        elif ch == "'":
            in_char = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "\n".join(prefix + [source[start:i + 1]])
        i += 1
    raise ExtractionError("unbalanced braces while extracting %r" % name)


def extract_from_file(path: Path, names: List[str]) -> str:
    src = path.read_text(encoding="utf-8", errors="replace")
    return "\n\n".join(extract_function(src, n) for n in names)
