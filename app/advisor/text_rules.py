from __future__ import annotations

import re
from dataclasses import dataclass

from app.feature_catalog import PlantFeature
from app.models.domain import Evidence, SourceType, TruthValue


@dataclass(frozen=True)
class PhraseRule:
    feature: PlantFeature
    pattern: str
    value: TruthValue = TruthValue.YES
    confidence: float = 0.92


# Spezifische Gegenbelege stehen vor allgemeineren positiven Aussagen.
PHRASE_RULES = [
    PhraseRule(
        PlantFeature.OUTDOOR_UNCOVERED,
        r"\bnicht\s+(?:für\s+)?(?:den\s+)?ungeschützten?\s+freiland",
        TruthValue.NO,
        0.97,
    ),
    PhraseRule(
        PlantFeature.OUTDOOR_UNCOVERED,
        r"\bregenschutz\s+(?:ist\s+)?(?:notwendig|erforderlich|empfohlen)",
        TruthValue.NO,
        0.95,
    ),
    PhraseRule(
        PlantFeature.OUTDOOR_UNCOVERED,
        r"\b(?:nur\s+)?(?:mit|unter)\s+regenschutz|\bvor\s+regen\s+schützen",
        TruthValue.NO,
        0.95,
    ),
    PhraseRule(
        PlantFeature.GREENHOUSE,
        r"\bregenschutz\s+(?:ist\s+)?(?:notwendig|erforderlich|empfohlen)|\bgeschützter\s+standort",
        confidence=0.9,
    ),
    PhraseRule(
        PlantFeature.OUTDOOR_UNCOVERED,
        r"\bungeschützt(?:es|en|er)?\s+freiland|\bohne\s+(?:ein\s+)?dach|\bohne\s+regenschutz|\bfreilandgeeignet|\bfreiland\s+(?:geeignet|möglich|problemlos)|\bregen(?:fest|tolerant)",
        confidence=0.95,
    ),
    PhraseRule(PlantFeature.BALCONY, r"\b(?:balkon|terrasse|topf|kübel)(?:geeignet)?\b"),
    PhraseRule(PlantFeature.GREENHOUSE, r"\b(?:gewächshaus|folientunnel|unter\s+dach)\b"),
    PhraseRule(PlantFeature.SWEET, r"\b(?:süß|süss|süßlich)\w*\b"),
    PhraseRule(PlantFeature.AROMATIC, r"\b(?:aromatisch|würzig|intensives?\s+aroma)\w*\b"),
    PhraseRule(PlantFeature.MILD, r"\b(?:mild|nicht\s+scharf)\w*\b"),
    PhraseRule(PlantFeature.SPICY, r"\b(?:scharf|feurig)\w*\b"),
    PhraseRule(PlantFeature.EASY_CARE, r"\b(?:pflegeleicht|unkompliziert|anfänger(?:geeignet)?)\w*\b"),
    PhraseRule(PlantFeature.EARLY, r"\b(?:früh|frühreif|frühe\s+ernte)\w*\b"),
    PhraseRule(PlantFeature.LATE, r"\b(?:spät|spätreif|späte\s+ernte)\w*\b"),
    PhraseRule(PlantFeature.SAUCE, r"\b(?:soße|sosse|sauce|passata|einkochen)\w*\b"),
    PhraseRule(PlantFeature.FRESH_EATING, r"\b(?:frischverzehr|rohkost|naschen|snack)\w*\b"),
    PhraseRule(PlantFeature.DRYING, r"\b(?:trocknen|dörren)\w*\b"),
    PhraseRule(PlantFeature.ROBUST, r"\b(?:robust|resistent|widerstandsfähig|tolerant)\w*\b"),
    PhraseRule(PlantFeature.HIGH_YIELD, r"\b(?:ertragreich|hoher\s+ertrag|reichtragend)\w*\b"),
    PhraseRule(PlantFeature.SMALL_FRUIT, r"\b(?:kleine?\s+früchte|cocktail|snack|kirsch)\w*\b"),
    PhraseRule(PlantFeature.COMPACT, r"\b(?:kompakt|kleinbleibend|buschig|niedrig)\w*\b"),
    PhraseRule(PlantFeature.TALL, r"\b(?:hochwachsend|hoch\s+wachsend|bis\s+zu\s+[2-9](?:[,.]\d+)?\s*m)\b"),
    PhraseRule(PlantFeature.CLIMBING, r"\b(?:rankend|kletternd|stangenform|stangenbohne)\w*\b"),
    PhraseRule(PlantFeature.NO_PRUNING, r"\b(?:nicht|kein)\w*\s+ausgeiz\w*\b"),
    PhraseRule(PlantFeature.WARM_LOCATION, r"\b(?:warmer|wärmebedürftig)\w*\s+standort\b"),
    PhraseRule(PlantFeature.DROUGHT_TOLERANT, r"\b(?:trockenheitsverträglich|trockenheitstolerant|wenig\s+wasser)\w*\b"),
    PhraseRule(PlantFeature.SUNNY, r"\b(?:sonnig|volle\s+sonne)\w*\b"),
    PhraseRule(PlantFeature.PARTIAL_SHADE, r"\bhalbschatt\w*\b"),
    PhraseRule(PlantFeature.STORABLE, r"\b(?:lagerfähig|haltbar|gut\s+lagern)\w*\b"),
    PhraseRule(PlantFeature.OVERWINTERABLE, r"\b(?:überwinterbar|mehrjährig)\w*\b"),
    PhraseRule(PlantFeature.WINTER_HARDY, r"\bwinterhart\w*\b"),
    PhraseRule(
        PlantFeature.PEAR_SHAPED,
        r"\b(?:birnenförmig|birnenfoermig|birnenartig|birnenform|birnchenform)\w*\b",
    ),
]


def extract_text_evidence(description: str) -> list[Evidence]:
    text = " ".join((description or "").casefold().split())
    evidence: list[Evidence] = []

    for rule in PHRASE_RULES:
        match = re.search(rule.pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        evidence.append(Evidence(
            feature=rule.feature.value,
            value=rule.value,
            source=SourceType.DESCRIPTION,
            quote=description,
            confidence=rule.confidence,
        ))

    return evidence


def extract_outdoor_uncovered_evidence(description: str) -> list[Evidence]:
    """Abwärtskompatibler Helfer für bestehende Tests und Aufrufer."""
    return [
        item
        for item in extract_text_evidence(description)
        if item.feature == PlantFeature.OUTDOOR_UNCOVERED.value
    ]
