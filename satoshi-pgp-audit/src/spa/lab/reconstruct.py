"""Can a historical key be reconstructed from its username and creation time?

This module exists because it is the single most common proposal for "recovering"
a famous key, and it deserves a tested answer rather than a dismissal.

THE HYPOTHESIS
--------------
"The User ID (and/or the creation timestamp) is a missing input to key generation.
Try enough candidate usernames at the right timestamp and the original key falls
out."

THE ANSWER: NO - and not for want of compute.

The User ID is not an input to key generation at any point. In OpenPGP a key is a
*separate packet* from the User ID that labels it (RFC 4880 s11.1: a transferable
public key is a public-key packet, then User ID packets, then signatures). GnuPG
generates p, q, g and x first, from the entropy pool, and only then attaches
whatever name the user typed and self-signs the pair. Changing the name changes the
User ID packet and the self-signature over it; it does not change - and cannot
change - a single bit of the key material.

The creation timestamp is likewise *recorded*, not consumed. It is stamped into the
public-key packet (and therefore covered by the fingerprint), but it never reaches
the random number generator.

What actually determines the key is the entropy pool state at that instant. On the
MingW32 build the record attributes to this key, cipher/rndw32.c seeds that pool
from live machine state - mouse cursor position, caret position, window and process
handles, thread ids, message times, input-queue status, tick count, and on NT the
full performance-data set (disk I/O counters, network statistics, heap and process
walks). None of it is derivable from a name or a clock reading.

WHEN THIS IDEA *WOULD* HAVE WORKED
----------------------------------
The hypothesis is not silly - it describes a real class of failure. Debian's OpenSSL
defect (CVE-2008-0166, Sept 2006 - May 2008) removed almost all entropy from seeding
and left the process ID as the effective input: 32,768 possibilities, so every key
generated on an affected system was brute-forceable, and people did exactly the
kind of enumeration proposed here.

That was OpenSSL on Debian. It was never GnuPG, and 1.4.7's pool has no equivalent
collapse. So the right question is not "which username" but "was the entropy source
degenerate", and for this software the answer is no.

``run_experiment()`` settles it empirically instead of by argument: generate many
keys with the historical binary, holding the User ID fixed, and observe that keys
sharing a User ID *and* a creation second are still entirely unrelated.
"""

import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# DSA-1024 private exponent x is uniform in [1, q-1] with q ~ 2^160.
DSA_PRIVATE_KEY_SPACE_BITS = 160


@dataclass
class ReconstructionResult:
    uid: str
    keys_generated: int
    distinct_fingerprints: int
    distinct_y: int
    distinct_p: int
    distinct_q: int
    timestamp_collisions: List[Tuple[int, int, int]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def uid_determines_key(self) -> bool:
        """True only if a fixed User ID produced a repeated key."""
        return self.distinct_fingerprints < self.keys_generated

    @property
    def uid_and_time_determine_key(self) -> bool:
        """True only if keys sharing a UID and a creation second collided."""
        return any(distinct < count for _, count, distinct in self.timestamp_collisions)


def search_space() -> Dict[str, object]:
    """Size of the brute-force problem, even granting the hypothesis."""
    space = 1 << DSA_PRIVATE_KEY_SPACE_BITS
    per_sec = 10 ** 12          # absurdly generous: 1 trillion candidate keys/sec
    seconds = space / per_sec
    return {
        "private_key_bits": DSA_PRIVATE_KEY_SPACE_BITS,
        "candidates": space,
        "candidates_scientific": "%.2e" % space,
        "assumed_rate_per_second": per_sec,
        "years_at_that_rate": "%.2e" % (seconds / 31_557_600),
        "note": (
            "This is the cost AFTER assuming a correct username, a correct "
            "timestamp, and correctly regenerated domain parameters. Each candidate "
            "also requires a modular exponentiation to test, so the real rate is "
            "many orders of magnitude below the figure assumed here. Additionally p "
            "and q are freshly generated per key from the same pool, so a candidate "
            "must reproduce those too before x is even reachable."),
    }


def run_experiment(gpg_path: str, uid_name: str = "Satoshi Nakamoto",
                   uid_email: str = "satoshin@gmx.com",
                   count: int = 25, key_length: int = 1024,
                   timeout: int = 300) -> ReconstructionResult:
    """Generate ``count`` keys with a FIXED User ID using the historical binary.

    If the User ID were an input to generation, these keys would be identical, or at
    minimum keys sharing a creation second would collide. They do not.
    """
    uid = "%s <%s>" % (uid_name, uid_email)
    batch = ("Key-Type: DSA\nKey-Length: %d\nName-Real: %s\nName-Email: %s\n"
             "Expire-Date: 0\n%%commit\n" % (key_length, uid_name, uid_email))
    from ..openpgp import dearmor, parse_keyblock

    records: List[Tuple[int, str, int, int, int]] = []
    for _ in range(count):
        home = tempfile.mkdtemp(prefix="spa-recon-")
        try:
            os.chmod(home, 0o700)
            bf = os.path.join(home, "batch.txt")
            with open(bf, "w") as fh:
                fh.write(batch)
            base = [gpg_path, "--homedir", home, "--batch", "--yes"]
            if subprocess.run(base + ["--gen-key", bf],
                              capture_output=True, timeout=timeout).returncode != 0:
                continue
            listing = subprocess.run(base + ["--list-keys", "--with-colons",
                                             "--fingerprint"], capture_output=True)
            fprs = re.findall(r"^fpr:::::::::([0-9A-F]+):",
                              listing.stdout.decode("utf-8", "replace"), re.M)
            if not fprs:
                continue
            exported = subprocess.run(base + ["--armor", "--export", fprs[0]],
                                      capture_output=True)
            kb = parse_keyblock(dearmor(exported.stdout.decode())[0].body)
            m = kb.primary.mpis
            records.append((kb.primary.created, kb.fingerprint, m["y"].value,
                            m["p"].value, m["q"].value))
        finally:
            shutil.rmtree(home, ignore_errors=True)

    res = ReconstructionResult(
        uid=uid, keys_generated=len(records),
        distinct_fingerprints=len({r[1] for r in records}),
        distinct_y=len({r[2] for r in records}),
        distinct_p=len({r[3] for r in records}),
        distinct_q=len({r[4] for r in records}))

    for ts, n in Counter(r[0] for r in records).items():
        if n > 1:
            distinct = len({r[1] for r in records if r[0] == ts})
            res.timestamp_collisions.append((ts, n, distinct))

    if not res.uid_determines_key:
        res.notes.append(
            "Every key is distinct despite an identical User ID, including the "
            "domain parameters p and q. The User ID is demonstrably not an input.")
    if res.timestamp_collisions and not res.uid_and_time_determine_key:
        total = sum(n for _, n, _ in res.timestamp_collisions)
        res.notes.append(
            "%d keys shared a creation second with at least one other key while "
            "also sharing the User ID, and every one of them is still a different "
            "key. User ID plus timestamp does not determine the key either." % total)
    if not res.timestamp_collisions:
        res.notes.append(
            "No two keys landed in the same second; raise --count to force "
            "timestamp collisions and test the stronger claim.")
    return res
