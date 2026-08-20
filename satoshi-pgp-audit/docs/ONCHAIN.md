# On-chain analysis: what public keys can and cannot reveal

## Why early Bitcoin blocks are analytically special

Early coinbase outputs paid to a **raw public key** (`p2pk`), not to a hash of one.
That single fact is what makes real cryptographic analysis possible on this corpus:

| Output type | What is published | Analysis possible? |
|---|---|---|
| `p2pk` (2009-2010 coinbases) | the **full public key** | yes - full EC arithmetic |
| `p2pkh` (modern) | `HASH160(pubkey)` only | no, until the coins move |

Satoshi-era coins are overwhelmingly **unspent**, so they publish no *signature* -
which kills every nonce-based attack. But because they are `p2pk`, they do publish
the *public key*. That leaves exactly one meaningful test available, and this
project runs it.

## The test: related private keys

If a generator ever produced keys related by a small additive offset - sequential
keys, an incrementing counter, a stuck-then-nudged RNG, a partially reset seed -
that relation passes straight through to the public keys:

```
d_j = d_i + delta      =>      P_j = P_i + delta*G
```

No private data is required to detect it. Scan small `delta`, look for collisions.
A single hit would prove the generator defective and mean the two private keys
stand or fall together.

This is not a hypothetical failure class. It is what made **Debian's OpenSSL keys**
(CVE-2008-0166) and the **2013 Android SecureRandom wallets** recoverable. It is
also rarely tested on historical corpora, because it needs full public keys and most
analysts only have addresses.

## Making it tractable

Naive pairwise comparison is O(n²) - about 480 million point operations for a 22k
corpus. Instead the scan advances the **entire corpus** by `delta*G` in one column
and tests membership, which is O(n · delta_max).

The remaining cost is one modular inversion per point per delta. That is the
bottleneck, so the implementation uses **Montgomery's batch-inversion trick**: a
whole column is inverted with *one* inversion plus 3n multiplications. That is the
difference between a scan that finishes in seconds and one that does not finish.

```bash
python -m spa.cli scan-related --input <p2pk.csv> --max-delta 2048
```

## Results on the Patoshi corpus

Corpus: 21,953 `p2pk` coinbase outputs, blocks 3-49,973
(`bensig/patoshi-addresses` @ `414637c`, SHA-256 recorded in `data/provenance.json`).

**Verified locally before any analysis** - third-party data is not taken on faith:

| Check | Result |
|---|---|
| Entries parsed | 21,953 |
| Valid secp256k1 points | **21,953 / 21,953** |
| Rejected / off-curve | **0** |
| Duplicate public keys | **0** |
| Distinct block heights | 21,953 |

**Scan result:**

| Measure | Result |
|---|---|
| Positive control (planted `delta=7` pair) | **detected** |
| Duplicate keys in corpus | **0** |
| Related-key pairs in corpus (delta <= 2048) | **0** |

The positive control matters more than the headline. A scanner that has never been
shown to find a relation cannot be trusted to report the absence of one, so a
synthetic pair with a known offset is injected into every run and the result is
discarded as meaningless if that pair is not recovered.

**Interpretation.** Zero relations across 21,953 keys and 2,048 offsets rules out sequential, incrementing and
small-offset key generation across the entire corpus. That is a whole class of
generator defect excluded by measurement rather than left assumed. It is consistent
with the early client drawing each coinbase key independently from OpenSSL's RNG,
and it is a genuine negative result rather than an absence of effort.

## The decisive test: did Satoshi's key ever reuse a nonce?

Nonce reuse is the one ECDSA failure that leaks a private key from public data:

```
k = (z1 - z2) / (s1 - s2)      d = (s1*k - z1) / r
```

For the ~1.1M BTC of dormant Patoshi coinbases the question is moot - those keys
never signed at all, so no nonce exists to attack. Their attack surface is empty,
not merely hard.

There is exactly one exception. The **block-9 coinbase key** was spent, and then
reused as the change key at each hop down a short chain starting with the famous
2009-01-12 transfer to Hal Finney. That makes it the only Satoshi-attributed key
that ever signed more than once, and so the only place this attack could ever have
applied.

```bash
python -m spa.cli verify-spendchain
```

**Everything is re-derived locally** - this project's own transaction parser, its
own SIGHASH_ALL reconstruction, its own secp256k1:

| Check | Result |
|---|---|
| Transactions | 5 |
| Txids authenticated locally (double-SHA-256) | **5 / 5** |
| Signatures found | 5 |
| Signatures verifying against the key | **5 / 5** |
| Distinct nonces (`r`) | **5** |
| Reused-nonce pairs | **0** |
| Private key recovered | **no** |

The authentication step is what removes the need to trust the data's source: a
Bitcoin txid *is* the double-SHA-256 of the raw bytes, so bytes that hash to
`f4184fc596403b9d...` are the first Bitcoin transaction, whoever handed them over.
A test flips one bit and confirms the check catches it.

**Result: five signatures, five distinct nonces.** The one Satoshi key that ever
signed repeatedly did so safely. The closed-form nonce attack - the mechanism behind
the real Android-2013 thefts - does not apply to it.

## What this does NOT establish

- **Not an identity claim.** The corpus is labelled "Patoshi" by convention. That
  attribution originates in Lerner's 2013 ExtraNonce analysis and is a *historical*
  inference, not a cryptographic fact. Everything here is stated about *this
  corpus*, never about a named person.
- **Not a completeness claim.** The scan covers `delta <= max_delta`. Relations at
  larger offsets, multiplicative relations, or structure inside the private keys
  that does not manifest as a small additive offset would not be caught.
- **Not a path to any private key.** A negative result closes a door. It does not
  open one.

## Relationship to the PGP side of this project

None, cryptographically - and that separation is enforced in code
(`spa.analysis.bitcoin_scope.DOMAIN_SEPARATION`). The PGP key is DSA generated by
GnuPG; Bitcoin keys are ECDSA generated by OpenSSL. No GnuPG RNG finding,
CVE-2016-6313 included, can propagate across that boundary. The two analyses share
an owner and a repository, nothing more.
