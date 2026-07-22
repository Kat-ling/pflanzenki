from __future__ import annotations

import re
from dataclasses import dataclass
from app.models.domain import Evidence, SourceType, TruthValue


@dataclass(frozen=True)
class PhraseRule:
    pattern: str
    value: TruthValue
    confidence: float = 0.95


# Reihenfolge ist wichtig: spezifische negative Aussagen zuerst.
OUTDOOR_UNCOVERED_RULES = [
    PhraseRule(r"\bnicht\s+(?:für\s+)?(?:den\s+)?ungeschützten?\s+freiland", TruthValue.NO),
    PhraseRule(r"\bnur\s+(?:mit|unter)\s+regenschutz", TruthValue.NO),
    PhraseRule(r"\bregenschutz\s+(?:ist\s+)?(?:notwendig|erforderlich|empfohlen)", TruthValue.NO, 0.9),
    PhraseRule(r"\bvor\s+regen\s+schützen", TruthValue.NO),
    PhraseRule(r"\bgeschützter\s+standort", TruthValue.NO, 0.8),
    PhraseRule(r"\bunter\s+dach", TruthValue.NO, 0.85),
    PhraseRule(r"\bungeschützt(?:es|en|er)?\s+freiland", TruthValue.YES),
    PhraseRule(r"\bohne\s+(?:ein\s+)?dach", TruthValue.YES),
    PhraseRule(r"\bohne\s+regenschutz", TruthValue.YES),
    PhraseRule(r"\bfreilandgeeignet", TruthValue.YES),
    PhraseRule(r"\bfreiland\s+(?:geeignet|möglich|problemlos)", TruthValue.YES),
    PhraseRule(r"\bregenfest", TruthValue.YES, 0.9),
    PhraseRule(r"\bregentolerant", TruthValue.YES, 0.9),
]


def extract_outdoor_uncovered_evidence(description: str) -> list[Evidence]:
    text = " ".join((description or "").lower().split())
    evidence: list[Evidence] = []
    for rule in OUTDOOR_UNCOVERED_RULES:
        match = re.search(rule.pattern, text, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 55)
            end = min(len(text), match.end() + 55)
            evidence.append(Evidence(
                feature="outdoor_uncovered",
                value=rule.value,
                source=SourceType.DESCRIPTION,
                quote=text[start:end].strip(),
                confidence=rule.confidence,
            ))
    return evidence
