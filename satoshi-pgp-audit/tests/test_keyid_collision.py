"""Short-key-id collision detection over a Satoshi-impersonation keyring."""
import json
from pathlib import Path

from spa.analysis.keyid_collision import KeyEntry, find_collisions

ROOT = Path(__file__).resolve().parents[1]
KEYRING = ROOT / "data" / "impersonation_keyring.json"


def test_detects_5ec948a1_short_id_collision():
    blob = json.loads(KEYRING.read_text())
    entries = [KeyEntry(label=e["label"], key_id=e["key_id"]) for e in blob["entries"]]
    f = find_collisions(entries, watched_short_ids=blob["watched_short_ids"])
    assert "5EC948A1" in f.short_collisions
    # Exactly three keys carry Satoshi's short id; two are forgeries.
    assert len(f.short_collisions["5EC948A1"]) == 3
    assert "5EC948A1" in f.watched_hits


def test_distinct_keys_no_false_collision():
    """Keys with different short ids must not be flagged."""
    entries = [KeyEntry("a", "1111111122223333"),
               KeyEntry("b", "444444445555AAAA")]
    f = find_collisions(entries)
    assert f.has_collision is False


def test_same_key_listed_twice_is_not_a_collision():
    """A duplicate of the SAME key (identical id) is not a collision of distinct keys."""
    entries = [KeyEntry("a", "18C09E865EC948A1"), KeyEntry("a-copy", "18C09E865EC948A1")]
    f = find_collisions(entries)
    assert "5EC948A1" not in f.short_collisions


def test_long_id_collision_flagged():
    entries = [KeyEntry("a", "AAAABBBB5EC948A1"), KeyEntry("b", "CCCCDDDD5EC948A1"),
               KeyEntry("c", "FFFF00005EC948A1")]
    f = find_collisions(entries)
    # all share the short id
    assert "5EC948A1" in f.short_collisions
