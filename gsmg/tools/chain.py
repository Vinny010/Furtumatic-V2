#!/usr/bin/env python3
"""Walk the stage chain from the page captures, decrypting each blob in turn.

    phase 2   password sha256("causality")
    phase 3   password sha256(parts 1..7 concatenated)
    phase 3.2 password sha256("jacquefresco...uncertaintyprinciple")

Each step's password is verified against its published digest before use, so a
failure here means a capture or a password is wrong, not the puzzle.
"""
import base64
import hashlib
import re
import sys

from Crypto.Cipher import AES

PARTS = [
    "causality", "Safenet", "Luna", "HSM", "11110",
    "0x736B6E616220726F662074756F6C69616220646E6F63657320666F206B6E697262206E6F"
    "20726F6C6C65636E61684320393030322F6E614A2F33302073656D695420656854",
    "B5KR/1r5B/2R5/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 b - - 0 1",
]
EXPECT = {
    "phase 2":   "eb3efb5151e6255994711fe8f2264427ceeebf88109e1d7fad5b0a8b6d07e5bf",
    "phase 3":   "1a57c572caf3cf722e41f5f9cf99ffacff06728a43032dd44c481c77d2ec30d5",
    "phase 3.2": "250f37726d6862939f723edc4f993fde9d33c6004aab4f2203d9ee489d61ce4c",
}


def bytes_to_key(pw, salt, md5=False):
    h = hashlib.md5 if md5 else hashlib.sha256
    out, prev = b"", b""
    while len(out) < 48:
        prev = h(prev + pw + salt).digest()
        out += prev
    return out[:32], out[32:48]


def decrypt(raw, pw):
    if raw[:8] != b"Salted__":
        return None, None
    for md5 in (False, True):
        k, iv = bytes_to_key(pw, raw[8:16], md5)
        pt = AES.new(k, AES.MODE_CBC, iv).decrypt(raw[16:])
        p = pt[-1]
        if 1 <= p <= 16 and pt[-p:] == bytes([p]) * p:
            return pt[:-p], "md5" if md5 else "sha256"
    return None, None


def step(name, raw, password, out_path):
    digest = hashlib.sha256(password.encode()).hexdigest()
    ok = digest == EXPECT[name]
    print(f"{name:10s} password sha256 {digest[:16]}…  {'OK' if ok else 'MISMATCH'}")
    body, dg = decrypt(raw, digest.encode())
    if body is None:
        print(f"{'':10s} DECRYPT FAILED")
        return None
    print(f"{'':10s} {len(raw)} bytes -> {len(body)} bytes plaintext (EVP digest {dg})")
    open(out_path, "wb").write(body)
    return body


def main(path):
    html = open(path, encoding="utf-8", errors="ignore").read()
    areas = re.findall(r"<textarea[^>]*>(.*?)</textarea>", html, re.S)
    blobs = [base64.b64decode(re.sub(r"\s+", "", a)) for a in areas]
    print(f"captured {len(blobs)} blobs from {path}\n")

    step("phase 2", blobs[0], "causality", "gsmg/data/phase2_plain.txt")
    b3 = step("phase 3", blobs[1], "".join(PARTS), "gsmg/data/phase3_plain.txt")
    if b3 is None:
        return 1
    m = re.search(rb"(U2FsdGVkX1[A-Za-z0-9+/=\s]+)", b3)
    step("phase 3.2", base64.b64decode(re.sub(rb"\s+", b"", m.group(1))),
         "jacquefrescogiveitjustonesecondheisenbergsuncertaintyprinciple",
         "gsmg/data/phase32_plain.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "gsmg/data/page_phase2_phase3.mhtml"))
