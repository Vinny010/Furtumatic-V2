# Threat model

## What an analyst actually has in 2026

| Artefact | Available? | Contains raw RNG output? |
|---|---|---|
| Public key packet (p, q, g, y) | yes | no - primality search output and a discrete log |
| User ID packet | yes | no |
| Elgamal subkey | yes | no |
| 3 self-signatures (2 distinct values) | yes | no - `r = (g^k mod p) mod q`, never `k` |
| 222 third-party signatures | yes | no - and made by other people's generators |
| Secret key packet | **no** | would contain an 8-byte S2K salt + IV |
| Generator's memory / pool state | **no** | this is what the CVE needs |
| Machine, OS entropy sources, timing | **no** | gone since 2008 |

Total raw generator output recoverable from the public record: **0 bytes.**
CVE-2016-6313 requires **580**.

## Why "just get more signatures" does not help

The shortfall is categorical, not quantitative. Every published OpenPGP value is
the image of generator output under a one-way or search process:

- `q`, `p` - survivors of a primality search over many discarded candidates
- `g` - derived deterministically from `p` and `q`
- `y = g^x mod p` - `x` behind a discrete log
- `r = (g^k mod p) mod q` - `k` behind a discrete log, then reduced

None of these is raw RNG output, at any quantity. A million public signatures still
yield zero bytes of the 580 required.

## What would change the conclusion

Stated plainly, so the claim is falsifiable:

1. **The secret key packet becoming public.** Supplies an S2K salt and IV that *are*
   raw generator output - still only ~16 bytes of 580, but non-zero, and it would
   move the finding from category E to category B.
2. **A memory image or core dump** of the generating machine. This is the actual
   precondition, and it is what "requires internal state" means.
3. **Nonce reuse in signatures not yet examined.** Ruled out only for the three
   signatures on this keyblock. Supply more signatures by this key and the tool
   re-tests them.
4. **A mathematical advance against DSA-1024/SHA-1.** Currently ~2^80 by Pollard
   rho on the 160-bit subgroup - about 10^24 operations, which no amount of hardware
   reaches.

## Out of scope by construction

- **Bitcoin keys.** ECDSA over secp256k1 via OpenSSL. GnuPG's `cipher/random.c` is
  never executed by Bitcoin, so no GnuPG RNG finding transfers. Separately, unspent
  outputs publish no signature at all, so most coins attributed to Satoshi
  contribute zero ECDSA signatures to any analysis.
- **Identity attribution.** Not a cryptographic question. The project makes no claim
  about who controlled any key.
- **Any real private key.** No recovery is attempted against real material.
