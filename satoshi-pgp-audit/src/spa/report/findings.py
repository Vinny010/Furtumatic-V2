"""The five evidentiary categories, and the rules that keep them separate.

The whole point of the report is that these five buckets never blur into each other.
"A defect exists in this software" and "this key is compromised" are different
claims with different evidence, and most public confusion about historical crypto
comes from collapsing them.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Category(str, Enum):
    A = "A"   # definitely applies to the historical software
    B = "B"   # theoretically applies, requires unavailable state or observations
    C = "C"   # anomaly actually visible in the public key/signatures
    D = "D"   # reproduced successfully with synthetic keys
    E = "E"   # conclusively ruled out


CATEGORY_TITLES = {
    Category.A: "Vulnerabilities that definitely apply to the historical software",
    Category.B: "Vulnerabilities that theoretically apply but require internal state "
                "or observations that do not exist publicly",
    Category.C: "Anomalies actually visible in the public key and signatures",
    Category.D: "Findings reproduced successfully with synthetic keys",
    Category.E: "Conclusively ruled out",
}

CATEGORY_MEANING = {
    Category.A: "The defect is present in code built from GnuPG 1.4.7. This is a "
                "statement about the SOFTWARE, and carries no implication that any "
                "particular key is affected.",
    Category.B: "The mechanism is real, but exploiting it needs something that was "
                "never published and cannot be recovered now - internal generator "
                "state, a co-located process, or physical proximity in 2008.",
    Category.C: "Something measurable in the published material. Listed whether or "
                "not it is security-relevant, with its significance stated.",
    Category.D: "Demonstrated end-to-end in this repository against keys and pools "
                "created for the experiment. Includes a reproduction command.",
    Category.E: "Excluded by evidence, not by assumption. Each entry names the fact "
                "that excludes it.",
}


@dataclass
class Finding:
    category: Category
    title: str
    summary: str
    evidence: List[str] = field(default_factory=list)
    requires: str = ""
    reproduce_with: str = ""
    references: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "category_title": CATEGORY_TITLES[self.category],
            "title": self.title,
            "summary": self.summary,
            "evidence": self.evidence,
            "requires": self.requires,
            "reproduce_with": self.reproduce_with,
            "references": self.references,
            "confidence": self.confidence,
            "data": self.data,
        }


@dataclass
class Report:
    target: Dict[str, Any] = field(default_factory=dict)
    findings: List[Finding] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)

    def by_category(self, cat: Category) -> List[Finding]:
        return [f for f in self.findings if f.category == cat]

    def add(self, f: Finding) -> None:
        self.findings.append(f)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "provenance": self.provenance,
            "environment": self.environment,
            "categories": {
                c.value: {
                    "title": CATEGORY_TITLES[c],
                    "meaning": CATEGORY_MEANING[c],
                    "findings": [f.to_dict() for f in self.by_category(c)],
                } for c in Category
            },
            "counts": {c.value: len(self.by_category(c)) for c in Category},
        }
