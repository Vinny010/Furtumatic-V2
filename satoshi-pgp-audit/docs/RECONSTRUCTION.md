# Can the key be reconstructed from a username and a timestamp?

**No.** Not "computationally hard" - structurally impossible. This document records
the reasoning and the experiment, because it is the most common proposal for
recovering a famous key and deserves a tested answer.

## The hypothesis

> The User ID is a missing input to key generation. Try enough candidate usernames
> at the right creation time and the original key falls out.

## Why it cannot work

**The User ID is not an input.** In OpenPGP a key and the name labelling it are
*separate packets* (RFC 4880 s11.1: public-key packet, then User ID packets, then
signatures). GnuPG generates `p`, `q`, `g` and `x` from the entropy pool **first**,
then attaches whatever name was typed and self-signs the pair. Changing the name
changes the User ID packet and the signature over it. It cannot change a bit of the
key material, because the key already exists by then.

**The timestamp is recorded, not consumed.** It is stamped into the public-key
packet - and so is covered by the fingerprint - but it never reaches the RNG.

**What actually determines the key** is the entropy pool state at that instant. On
the MingW32 build the historical record attributes to this key, `cipher/rndw32.c`
seeds that pool from live machine state:

- mouse cursor position, caret position
- active window, focus window, clipboard owner/viewer handles
- current process/thread handles and ids, desktop and window-station handles
- input-queue status, message position, message time
- `GetTickCount()`, `QueryPerformanceCounter()`
- on NT: the full performance-data set - disk I/O counters, network statistics,
  heap walks, process and thread enumeration

None of that is derivable from a name or a clock reading. It is exactly the
"unavailable internal state" that category B of the audit report describes.

## The experiment

`spa.lab.reconstruct.run_experiment()` generates many keys with the genuine 1.4.7
binary while holding the User ID fixed at `Satoshi Nakamoto <satoshin@gmx.com>`.
Enough keys are produced that several land in the same creation second, which tests
the stronger claim (User ID **plus** timestamp) rather than only the weak one.

```bash
python -m spa.cli lab-reconstruct --count 25
```

Observed result:

| Measure | Result |
|---|---|
| Keys generated, all with the same User ID | 26 |
| Distinct fingerprints | **26** |
| Distinct public values `y` | **26** |
| Distinct primes `p` | **26** |
| Distinct primes `q` | **26** |
| Groups sharing a creation second | 5 |
| Collisions within those groups | **0** |

Four keys generated within the *same second* with the *same username* were four
entirely unrelated keys - different primes, different everything.

## Even granting the hypothesis

If the username somehow narrowed the search, what remains is `x` uniform in
`[1, q-1]` with `q ≈ 2^160`:

- **1.46 × 10^48** candidates
- at an absurdly generous 10^12 candidate keys per second: **4.63 × 10^28 years**

And that is the cost *after* assuming a correct username, a correct timestamp, and
correctly regenerated domain parameters - `p` and `q` are drawn from the same pool
per key, so a candidate must reproduce those before `x` is even reachable. Each
candidate also costs a modular exponentiation to test, so the true rate is many
orders of magnitude below the figure assumed.

## When this idea *would* have worked

The hypothesis is not silly - it describes a real class of failure, and one that
happened. Debian's OpenSSL defect (**CVE-2008-0166**, Sept 2006 - May 2008) stripped
almost all entropy from seeding and left the process ID as the effective input:
32,768 possibilities. Every key generated on an affected system was brute-forceable,
and people performed exactly the kind of enumeration proposed here.

That was **OpenSSL on Debian**, not GnuPG, and GnuPG 1.4.7's pool has no equivalent
collapse. So the productive question is never "which username" but "was the entropy
source degenerate" - and for this software, on this evidence, it was not.
