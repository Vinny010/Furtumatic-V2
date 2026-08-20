# satoshi-pgp-audit

A reproducible research tool that examines the public OpenPGP key
`DE4E FCA3 E1AB 9E41 CE96 CECB 18C0 9E86 5EC9 48A1` (key id `0x5EC948A1`, created
2008-10-30) and the historical GnuPG environment that public sources associate with
it, in order to answer one narrow question honestly:

> Could a known weakness in GnuPG 1.4.7 - its RNG in particular - have affected this
> key, and is there enough surviving public material for that weakness to be
> *observable*?

**Answer: no, and the reason is worth stating precisely.** CVE-2016-6313 is real,
it is present in 1.4.7, and this project reproduces it deterministically from first
principles. It does not reach this key. The attack consumes **580 bytes of raw
generator output**; an OpenPGP public key publishes **0**. The gap is categorical,
not quantitative - more signatures would not help, because no quantity of public
signatures contains raw generator output.

## What it establishes

Verified locally, reproducibly, from pinned artefacts:

| Claim | Result |
|---|---|
| Fingerprint recomputed from packet bytes | matches `DE4E…48A1` |
| DSA parameter validation (10 FIPS 186 checks) | all pass; `p`, `q` prime, `g` order `q`, `y` in subgroup |
| Signatures made by this key | **3 packets / 2 distinct values**, all verify |
| Nonce reuse among them | none (the one repeated `r` is a duplicate encoding) |
| Lattice/HNP feasibility | needs ~60 signatures; 2 exist |
| CVE-2016-6313 on 1.4.7 | **reproduced, 500/500** |
| Same predictor on 1.4.21 | **0/500** (negative control) |
| Python pool model vs real GnuPG C | **byte-identical**, both versions |
| Raw RNG output in public material | **0 bytes** of the 580 required |

## Quick start

```bash
make setup              # clone GnuPG at the pinned commit and verify its tree hash
make native-gnupg147    # build the genuine 1.4.7 binary (or: make docker-build)
make all                # full pipeline + report + tests
```

Individual stages:

```bash
python -m spa.cli verify-provenance   # re-check pinned digests and the fingerprint
python -m spa.cli analyze-key         # Part 1: parse and analyse the public key
python -m spa.cli lab-cve             # reproduce CVE-2016-6313
python -m spa.cli lab-differential    # Python model vs real GnuPG C code
python -m spa.cli lab-synth           # Part 2: synthetic keys via real GnuPG 1.4.7
python -m spa.cli lab-rngstats        # statistical battery over pool output
python -m spa.cli report              # the five-category report
```

The report lands in `reports/AUDIT_REPORT.md`, split into the five required
categories: **A** defects definitely in the historical software, **B** defects that
apply only given state nobody has, **C** anomalies actually visible in the public
material, **D** findings reproduced with synthetic keys, **E** what is conclusively
ruled out.

## How CVE-2016-6313 actually works

Worth spelling out, because "GnuPG had an RNG bug" is usually where the explanation
stops.

GnuPG's pool is 600 bytes seen as 30 blocks of 20, mixed by chaining **one**
RIPEMD-160 state across 30 compression calls. The load-bearing detail is in
`cipher/rmd160.c`:

```c
rmd160_mixblock (RMD160_CONTEXT *hd, char *buffer) {
    transform (hd, buffer);              /* absorb 64 bytes, no padding */
    *(u32*)p = hd->h0; ... hd->h4;       /* chaining state written back out */
}
```

`mix_pool()` copies those 20 bytes into the pool. So **pool block `B_n` *is* the
RIPEMD-160 chaining state after iteration `n`** - an observer of the pool is an
observer of the hash state. Nothing needs inverting.

In 1.4.7 the final iteration wraps and reads its 44 tail bytes from `pool[0:44]`,
which by then already holds the **new** `B0`, `B1`, `B2`. Its head is the new `B28`.
So every input to iteration 29 already appeared earlier in the same output:

```
B29 = transform( state = B28,  block = B28 || B0 || B1 || B2[0:4] )
```

One compression call over public data: 580 known bytes yield the remaining 20.
That is exactly upstream's own description - *"an attacker who obtains 580 bytes
from the standard RNG can trivially predict the next 20 bytes"*.

1.4.21 fixed it by absorbing 64 **contiguous** bytes starting at the block being
replaced, so iteration 29 consumes the **old** `B29` before overwriting it. That
value never appears in the output, and the relation breaks.

Note what this means: the defect is **structural, not statistical**. Output from
1.4.7 passes the full NIST battery - as this repo demonstrates - which is precisely
why it survived from 2007 to 2016. No black-box randomness test can find it.

## Why it cannot touch this key

Every published OpenPGP value is the image of generator output under a one-way or
search process:

- `p`, `q` - survivors of a primality search over many discarded candidates
- `g` - derived deterministically from `p` and `q`
- `y = g^x mod p` - `x` hidden behind a discrete log
- `r = (g^k mod p) mod q` - `k` hidden behind a discrete log, then reduced

None is raw RNG output. See `docs/THREAT_MODEL.md` for the full accounting and for
the explicit list of what *would* change the conclusion.

## Reproducibility

- **Key material** pinned by SHA-256 in `data/provenance.json`, and anchored by a
  fingerprint recomputed from the packet body - so appended keyserver spam cannot
  affect it.
- **GnuPG source** pinned by git tag, commit *and tree* hash
  (`gnupg-1.4.7` @ `7cb81bb`, tree `c9cb62c`, authored 2007-03-05). Pinning by tree
  hash is stronger than a tarball checksum: it is content-addressed over every file.
- **The C under test is extracted from that tree by script**, never hand-copied, so
  an upstream change breaks the test rather than silently comparing to a stale copy.
- **Docker** builds the historical toolchain from the pinned commit and refuses to
  proceed if the hashes disagree.

## Scope and ethics

- Exploit validation runs **only** against synthetic keys generated for the
  experiment. No recovery is attempted against any real key.
- The project makes **no identity claim** about who controlled any key, and ships no
  address attributions - that is a historical question, not a cryptographic one.
- Bitcoin keys are **out of scope by construction**: ECDSA/secp256k1 via OpenSSL
  never executes GnuPG's `cipher/random.c`, so no finding here transfers to them.
  `spa.analysis.bitcoin_scope` enforces that boundary and provides a signed-message
  verifier for material you supply.

## Can the key be rebuilt from a username and a timestamp?

No - and not for want of compute. The User ID is a *label attached after*
generation, and the creation timestamp is *recorded, not consumed*; neither reaches
the RNG. Generating 26 keys with the genuine 1.4.7 binary while holding the User ID
fixed at `Satoshi Nakamoto <satoshin@gmx.com>` produced 26 entirely different keys,
including five groups that shared a creation second and still collided zero times.

The idea does describe a real class of failure - Debian's OpenSSL defect
(CVE-2008-0166) reduced seeding to the process ID, 32,768 possibilities, and those
keys genuinely were enumerated. That was OpenSSL, not GnuPG, and 1.4.7 has no
equivalent collapse. See `docs/RECONSTRUCTION.md`.

## On-chain: the one test the data actually supports

Satoshi-era coins are unspent, so they publish no signature - every nonce attack is
dead on arrival. But early coinbases are `p2pk`, so they DO publish full public
keys. That allows exactly one real test: are any two private keys related by a
small offset (`P_j = P_i + delta*G`)? That is the failure class behind the Debian
OpenSSL and Android SecureRandom losses, and it is rarely tested on historical
corpora because it needs full public keys rather than addresses.

Run over 21,953 `p2pk` coinbase outputs (blocks 3-49,973), with every entry first
verified locally as a genuine curve point (21,953/21,953 on curve, 0 duplicates):

| Measure | Result |
|---|---|
| Positive control (planted `delta=7`) | **detected** |
| Related-key pairs, `delta <= 2048` | **0** |
| Duplicate public keys | **0** |

And the decisive one - **did Satoshi's key ever reuse a nonce?** The dormant
coinbases never signed, so they have no nonce to attack. The block-9 key is the sole
exception: spent, then reused as change down a five-transaction chain beginning with
the 2009-01-12 transfer to Hal Finney. Re-derived here with this project's own
parser, sighash reconstruction and secp256k1:

| Check | Result |
|---|---|
| Txids authenticated locally | **5 / 5** |
| Signatures verifying | **5 / 5** |
| Distinct nonces | **5** |
| Reused-nonce pairs | **0** |

The bytes authenticate themselves - a txid *is* the double-SHA-256 of the raw
transaction, so no trust in the data's source is required.

Both classes of generator defect, excluded by measurement. See `docs/ONCHAIN.md`.

## One honest caveat

The attribution *"GnuPG v1.4.7 (MingW32)"* comes from an ASCII-armor `Version:`
header. Armor headers are outside the packet stream: unsigned, not covered by the
fingerprint, and rewritten by every tool the material passes through. The copy
analysed here reads `Hockeypuck 2.2`. Independently, one signature packet carries
subpacket 33 (issuer-fingerprint), which postdates 2008 and which 1.4.7 could not
emit - direct evidence this copy passed through modern tooling.

So the generator attribution is a **historical** claim from archived copies, not
something the key itself attests. Every conclusion depending on it is reported
conditionally. This is the softest link in the chain, and it is evidentiary rather
than mathematical.

## Layout

```
src/spa/openpgp/   RFC 4880 parsing - parses, never judges
src/spa/analysis/  DSA validation, nonce analysis, NIST battery, Bitcoin boundary
src/spa/lab/       RIPEMD-160, the 1.4.7/1.4.21 pool models, CVE reproduction,
                   the C bridge, and the synthetic-key harness
src/spa/report/    five-category findings engine
docker/            pinned historical build + analysis image
docs/              METHODOLOGY.md, THREAT_MODEL.md, RECONSTRUCTION.md, ONCHAIN.md
tests/             75 tests, including the differential against real GnuPG C
```

## Requirements

Python 3.8+. No mandatory third-party dependency - the OpenPGP parser, DSA and
secp256k1 arithmetic, RIPEMD-160 and the statistical battery are all implemented in
the package, so the audit is itself auditable. `gmpy2` is optional and speeds up
primality proofs. The lab additionally needs a C toolchain and autotools (or Docker).
