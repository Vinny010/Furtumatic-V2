"""Detect short-key-ID collisions - keys deliberately crafted to share a famous
32-bit (or 64-bit) key id despite being different keys.

A PGP "short key id" is the low 32 bits of the fingerprint; the "long key id" is
the low 64 bits. Neither identifies a key uniquely: 32 bits is ~4 billion, grindable
on a GPU in hours, so an attacker can manufacture a key whose short id matches any
famous key's. The 2014 "Evil32" project did this for the entire PGP strong set. Even
64-bit long ids have been collided. ONLY the full 160-bit fingerprint is safe.

Given a keyring, this flags any set of DISTINCT keys sharing a short (or long) id,
and specifically calls out collisions with a watched id such as Satoshi's 5EC948A1.
It is the direct check for the impersonation keyrings that cluster forged UIDs and
colliding ids around a real key.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _norm(hexid: str) -> str:
    return "".join(hexid.split()).upper().replace("0X", "")


@dataclass
class KeyEntry:
    label: str
    key_id: str          # 64-bit long id or full fingerprint, hex (spaces ok)
    uid: Optional[str] = None

    @property
    def norm(self) -> str:
        return _norm(self.key_id)

    @property
    def short_id(self) -> str:
        return self.norm[-8:]

    @property
    def long_id(self) -> str:
        return self.norm[-16:]


@dataclass
class CollisionFindings:
    keys: int = 0
    short_collisions: Dict[str, List[str]] = field(default_factory=dict)
    long_collisions: Dict[str, List[str]] = field(default_factory=dict)
    watched_hits: Dict[str, List[str]] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    @property
    def has_collision(self) -> bool:
        return bool(self.short_collisions or self.long_collisions)


def find_collisions(entries: List[KeyEntry],
                    watched_short_ids: Optional[List[str]] = None) -> CollisionFindings:
    """Flag distinct keys that share a short/long id, and any that collide with a
    watched short id (e.g. a famous key's)."""
    f = CollisionFindings(keys=len(entries))
    watched = {_norm(w)[-8:] for w in (watched_short_ids or [])}

    by_short: Dict[str, List[KeyEntry]] = defaultdict(list)
    by_long: Dict[str, List[KeyEntry]] = defaultdict(list)
    for e in entries:
        by_short[e.short_id].append(e)
        by_long[e.long_id].append(e)

    for sid, group in by_short.items():
        distinct = {e.long_id for e in group}
        if len(distinct) > 1:                       # different keys, same short id
            f.short_collisions[sid] = [e.label for e in group]
        if sid in watched:
            f.watched_hits[sid] = [e.label for e in group]

    for lid, group in by_long.items():
        distinct = {e.norm for e in group}
        if len(distinct) > 1:
            f.long_collisions[lid] = [e.label for e in group]

    if f.short_collisions:
        f.notes.append(
            "%d short-id collision group(s): distinct keys share a 32-bit key id. "
            "This is cheap to forge (~4e9, GPU-hours) and is why short ids must "
            "never identify a key - use the full 160-bit fingerprint."
            % len(f.short_collisions))
    if f.watched_hits:
        for sid, labels in f.watched_hits.items():
            if len(labels) > 1:
                f.notes.append(
                    "WATCHED id %s is shared by %d keys %s - at most one is genuine; "
                    "the rest are short-id forgeries." % (sid, len(labels), labels))
    if not f.has_collision:
        f.notes.append("No short- or long-id collisions among the supplied keys.")
    return f
