# Methodology

## The distinction the whole project turns on

Three claims get conflated in public discussion of historical cryptography:

1. *This software had a defect.*
2. *This key was produced by that software.*
3. *This key is therefore breakable.*

(1) does not imply (3). It implies (3) only if the defect's exploitation
prerequisites are met by material that actually exists. Most of this project is the
machinery for checking that middle step honestly, and the five report categories
exist so a finding can never drift from one claim to another.

## Evidence rules

**The fingerprint is the only trust anchor.** A keyserver copy of a famous key is
adversarial input: the SKS protocol lets anyone append signature packets, and this
key carries 222 of them from other people. Everything the project asserts about the
key derives from the primary key packet, whose SHA-1 fingerprint is recomputed
locally and compared against the published value. Appended packets cannot change it.

**Armor headers are not evidence.** The `Version:` header carrying
`GnuPG v1.4.7 (MingW32)` sits outside the packet stream: unsigned, not covered by
the fingerprint, and rewritten by every tool the material passes through. The copy
analysed here reads `Hockeypuck 2.2`. The 1.4.7 attribution is a *historical* claim
from archived copies, not a cryptographic one, and every conclusion depending on it
is reported conditionally.

**Parse everything; discard nothing.** A parser that drops malformed packets lets
one spam packet hide the other 224. Malformed packets are recorded as
`MalformedPacket` and reported.

**Negative controls are mandatory.** Every detector is exercised against a case
where it must fire:

| Detector | Negative control |
|---|---|
| CVE-2016-6313 predictor | must fail on 1.4.21 (0/100) |
| Nonce-reuse detector | must recover the key from a deliberately reused nonce |
| Statistical battery | must fail biased input, pass `os.urandom` |
| Pool model | must match real GnuPG C byte-for-byte |

A detector that only ever reports "clean" is indistinguishable from one that is
broken.

## A trap worth naming: repeated r is not always nonce reuse

Satoshi's keyblock contains one repeated `r`. A naive nonce-reuse detector reports
that as catastrophic. It is not.

The subkey-binding signature appears **twice**, in two different packet encodings
that share both `r` and `s`. It is one signature carried twice, not one nonce used
twice. The packets differ only in their *unhashed* area, where one carries
subpacket 33 (issuer-fingerprint) - a field that postdates 2008 and that GnuPG 1.4.7
could not emit. The unhashed area is not covered by the signature, so both verify.

The correct rule:

- same `r`, same `s` -> duplicate encoding. Harmless.
- same `r`, different `s` -> genuine nonce reuse. Private key recoverable.

`analyse_nonces()` separates these. Conflating them produces a false alarm on this
key, and probably on any well-known key that has been re-exported by modern tooling.

## Why the model is trusted

`spa.lab.gnupg_rng` is a Python reimplementation, and a reimplementation is worth
nothing unless it is checked. `tests/test_differential_c.py` extracts `mix_pool()`
and the RIPEMD-160 compression function *programmatically* from the pinned upstream
trees, compiles them, and compares against the Python model over random pools and
repeated rounds. Both 1.4.7 and 1.4.21 agree exactly. The extraction is scripted
rather than hand-copied so that a change upstream breaks the test instead of
silently comparing against a stale copy.

## Scope limits

- Exploit validation runs **only** against synthetic keys created for the experiment.
- No attempt is made, anywhere, to recover any real private key.
- Entropy *gathering* (`rndw32.c`, `rndlinux.c`) is not modelled: it is OS- and
  hardware-specific, unreproducible 18 years later, and irrelevant to the mixing
  defect. Seed material is injected explicitly so experiments stay controlled.
- Statistical tests are reported with their power. On ~120 bytes of signature
  material they have essentially none, and the battery declines to produce a
  p-value rather than manufacturing one.
