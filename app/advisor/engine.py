from __future__ import annotations

from app.models.domain import (
    AdviceResult, Evidence, Plant, Recommendation, SourceType, TruthValue
)


SOURCE_PRIORITY = {
    SourceType.DESCRIPTION: 3,
    SourceType.STRUCTURED_FIELD: 2,
    SourceType.DERIVED: 1,
}


def resolve_feature(plant: Plant, feature: str) -> Recommendation:
    items = [e for e in plant.evidence if e.feature == feature]
    if not items:
        return Recommendation(
            plant_id=plant.id, plant_name=plant.name,
            verdict=TruthValue.UNKNOWN, score=0, reasons=[]
        )

    # Beschreibung hat Vorrang. Innerhalb gleicher Quelle gewinnt höhere Sicherheit.
    ranked = sorted(items, key=lambda e: (SOURCE_PRIORITY[e.source], e.confidence), reverse=True)
    winner = ranked[0]
    conflicts = [e for e in ranked[1:] if e.value != winner.value]

    base_score = {TruthValue.YES: 100, TruthValue.NO: -100, TruthValue.UNKNOWN: 0}[winner.value]
    score = base_score + winner.confidence * 10 + SOURCE_PRIORITY[winner.source]
    return Recommendation(
        plant_id=plant.id,
        plant_name=plant.name,
        verdict=winner.value,
        score=score,
        reasons=[winner],
        conflicts=conflicts,
    )


def advise_outdoor_uncovered(plants: list[Plant], question: str) -> AdviceResult:
    resolved = [resolve_feature(p, "outdoor_uncovered") for p in plants]
    yes = sorted((r for r in resolved if r.verdict == TruthValue.YES), key=lambda r: r.score, reverse=True)
    unknown = [r for r in resolved if r.verdict == TruthValue.UNKNOWN]
    no = [r for r in resolved if r.verdict == TruthValue.NO]

    selected = yes[:3]
    if selected:
        names = ", ".join(r.plant_name for r in selected)
        answer = f"Für einen Standort ohne Dach passen nach den vorhandenen Angaben am besten: {names}."
    else:
        answer = (
            "Für einen Standort ohne Dach gibt es in den vorhandenen Daten keinen eindeutig "
            "positiven Beleg. Fehlende Angaben werden nicht als ungeeignet bewertet."
        )

    return AdviceResult(
        question=question,
        intent="outdoor_uncovered",
        recommendations=selected,
        unknown=unknown,
        excluded=no,
        answer=answer,
    )


def advise(plants: list[Plant], question: str) -> AdviceResult:
    q = question.lower()
    if any(term in q for term in ("ohne dach", "ohne regenschutz", "ungeschützt", "freiland")):
        return advise_outdoor_uncovered(plants, question)
    return AdviceResult(
        question=question,
        intent="unknown",
        recommendations=[],
        answer="Diese Frage ist im MVP noch nicht implementiert.",
    )
