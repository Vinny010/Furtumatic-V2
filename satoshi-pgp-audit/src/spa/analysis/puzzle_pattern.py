"""Test whether solved Bitcoin-Puzzle keys reveal a 'hot zone' to aim at.

The claim worth checking: do the already-solved puzzle private keys cluster in
some fraction of their range, so we could bias a brute-force sweep of an unsolved
one (e.g. #72) toward the likely region?

Method: each puzzle #n has its key in [2^(n-1), 2^n). Normalise every solved key
to a position in [0, 1):

    position = (key - 2^(n-1)) / 2^(n-1)

0.0 = bottom of that puzzle's range, ~1.0 = top. If the positions cluster, a hot
zone exists and #72's key is probably in the same band. If they're uniform, there
is NO exploitable zone and every equal slice of #72 is equally likely - so plain
sequential scanning is as good as anything.

The near-certain result (creator stated the keys are random; every serious check
agrees) is UNIFORM: no hot zone. This module lets you verify that on the real
data yourself rather than taking anyone's word - and the tests include a control
that plants a real cluster to prove the detector fires when a bias exists.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List

# chi-square 0.05 critical value, 9 degrees of freedom (10 deciles - 1).
CHI2_CRIT_9DF_05 = 16.919
MIN_MEANINGFUL_N = 40


def position(n: int, key: int) -> float:
    """Normalised position of a puzzle-#n key within its range, in [0, 1)."""
    lo, hi = 1 << (n - 1), 1 << n
    if not (lo <= key < hi):
        raise ValueError("key 0x%x is not in puzzle #%d range [2^%d, 2^%d)"
                         % (key, n, n - 1, n))
    return (key - lo) / (hi - lo)


@dataclass
class PatternFindings:
    n: int
    mean: float
    deciles: List[int]
    chi_square: float
    biased: bool
    notes: List[str] = field(default_factory=list)

    @property
    def hot_zone(self):
        """If biased, the [start,end) decile band with the most hits; else None."""
        if not self.biased:
            return None
        top = max(range(10), key=lambda i: self.deciles[i])
        return (top / 10.0, (top + 1) / 10.0)


def analyse(solved: Dict[int, int]) -> PatternFindings:
    """Normalise solved keys and test their positions for uniformity (10 deciles)."""
    positions = [position(n, k) for n, k in solved.items()]
    n = len(positions)
    mean = sum(positions) / n if n else 0.0
    deciles = [0] * 10
    for p in positions:
        deciles[min(int(p * 10), 9)] += 1

    notes: List[str] = []
    if n < MIN_MEANINGFUL_N:
        notes.append("only %d samples - too few for a strong test; need ~%d+. "
                     "Paste the full solved list into data/puzzle_solved.json."
                     % (n, MIN_MEANINGFUL_N))
    expected = n / 10.0
    chi2 = sum((o - expected) ** 2 / expected for o in deciles) if expected else 0.0
    biased = chi2 > CHI2_CRIT_9DF_05

    if biased:
        notes.append("positions NOT uniform (chi2=%.2f > %.2f): a real bias exists."
                     % (chi2, CHI2_CRIT_9DF_05))
    else:
        notes.append("positions consistent with uniform (chi2=%.2f <= %.2f): "
                     "no hot zone - every slice of an unsolved range is equally likely."
                     % (chi2, CHI2_CRIT_9DF_05))
    notes.append("mean position %.4f (uniform expects 0.5)." % mean)
    return PatternFindings(n=n, mean=mean, deciles=deciles, chi_square=chi2,
                           biased=biased, notes=notes)


def load_solved(path: str = None) -> Dict[int, int]:
    """Load {puzzle_number: private_key_int} from data/puzzle_solved.json."""
    if path is None:
        here = os.path.dirname(__file__)
        path = os.path.join(here, "..", "..", "..", "data", "puzzle_solved.json")
    with open(path) as fh:
        raw = json.load(fh)
    return {int(k): int(v, 16) if isinstance(v, str) else int(v)
            for k, v in raw["solved"].items()}
