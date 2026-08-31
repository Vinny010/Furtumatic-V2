#!/usr/bin/env python3
"""Reproduce the Cosmic Duality ("Dualite") chain end to end from the page capture.

    page -> base64 blob -> XOR-chain key -> AES-256-CBC/MD5 -> 1327-byte plaintext
         -> 103x103 bit matrix -> row/column sums -> base-38 -> Half + Better half

Doubles as a certification vector: every step has a published value to check
against, so a failure here means the toolchain is wrong, not the puzzle.

Requires: pycryptodome, ecdsa, base58
"""
import base64
import hashlib
import re
import sys

import base58
import ecdsa
from Crypto.Cipher import AES

TOKENS = ["matrixsumlist", "enter", "lastwordsbeforearchichoice", "thispassword",
          "matrixsumlist", "yourlastcommand", "secondanswer"]
KEY_HEX = "a795de117e472590e572dc193130c763e3fb555ee5db9d34494e156152e50735"
PLAIN_SHA = "4f7a1e4efe4bf6c5581e32505c019657cb7b030e90232d33f011aca6a5e9c081"
EXPECT = {
    "Half":        ("1JG648yaB7Wp2dpUfcZoRSD4q35oq47vCu", "15E3pcDDXSKhvi3CLVhRTHEgd8dbVKvSZg"),
    "Better half": ("145ZQ9siLrsXBKf465wjdyQYAP5dRwhRhQ", "1FhbJnrdq1FmeiXrpTqnpQ8jvYV7naze96"),
}
N = 103


def bytes_to_key(pw, salt, md5=True):
    h = hashlib.md5 if md5 else hashlib.sha256
    out, prev = b"", b""
    while len(out) < 48:
        prev = h(prev + pw + salt).digest()
        out += prev
    return out[:32], out[32:48]


def address(priv, compressed=True):
    sk = ecdsa.SigningKey.from_string(priv, curve=ecdsa.SECP256k1)
    p = sk.get_verifying_key().pubkey.point
    pub = (bytes([2 + (p.y() & 1)]) + p.x().to_bytes(32, "big") if compressed
           else b"\x04" + p.x().to_bytes(32, "big") + p.y().to_bytes(32, "big"))
    h160 = hashlib.new("ripemd160", hashlib.sha256(pub).digest()).digest()
    return base58.b58encode_check(b"\x00" + h160).decode()


def main(path):
    html = open(path, encoding="utf-8", errors="ignore").read()
    dualite = re.sub(r"\s+", "", re.findall(r"<textarea[^>]*>(.*?)</textarea>", html, re.S)[1])
    raw = base64.b64decode(dualite)
    ok = True

    key = bytes(32)
    for t in TOKENS:
        key = bytes(a ^ b for a, b in zip(key, hashlib.sha256(t.encode()).digest()))
    print(f"XOR-chain key   : {key.hex()}  {'OK' if key.hex()==KEY_HEX else 'FAIL'}")
    ok &= key.hex() == KEY_HEX

    k, iv = bytes_to_key(key, raw[8:16], md5=True)
    pt = AES.new(k, AES.MODE_CBC, iv).decrypt(raw[16:])
    pt = pt[:-pt[-1]]
    got = hashlib.sha256(pt).hexdigest()
    print(f"plaintext       : {len(pt)} bytes, sha256 {got[:16]}…  "
          f"{'OK' if got==PLAIN_SHA else 'FAIL'}")
    ok &= got == PLAIN_SHA

    bits = "".join(f"{b:08b}" for b in pt)
    M = [[int(bits[r * N + c]) for c in range(N)] for r in range(N)]
    rs = [sum(row) for row in M]
    cs = [sum(M[r][c] for r in range(N)) for c in range(N)]
    sec = "".join(chr((rs[i] + cs[(i + 7) % N]) & 0xFF) for i in range(N))
    print(f"secondary       : {len(sec)} chars, ords {min(map(ord,sec))}..{max(map(ord,sec))}, "
          f"{len(set(sec))} distinct")

    val = 0
    for ch in sec:
        val = val * 38 + (ord(ch) - 80)
    data = val.to_bytes(68, "big")

    for name, priv in (("Half", data[:32]), ("Better half", data[32:64])):
        c, u = address(priv, True), address(priv, False)
        ec, eu = EXPECT[name]
        print(f"{name:15s} : {c}  {'OK' if c==ec else 'FAIL'}")
        print(f"{'':15s}   {u}  {'OK' if u==eu else 'FAIL'}")
        ok &= c == ec and u == eu

    print(f"trailing 4 bytes: {data[64:].hex()}")
    print("\nALL CHECKS PASS" if ok else "\nFAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "gsmg/data/salphaseion_page.mhtml"))
