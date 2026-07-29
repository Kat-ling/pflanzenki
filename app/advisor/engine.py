from __future__ import annotations

from app.ai.query_models import (
    ParsedQuery,
    PlantRequirement,
    RequirementImportance,
    RequirementValue,
)

from app.models.domain import (
    AdviceResult,
    ConfidenceLevel,
    Plant,
    Recommendation,
    SourceType,
    TruthValue,
)


SOURCE_PRIORITY = {
    SourceType.DESCRIPTION: 3,
    SourceType.STRUCTURED_FIELD: 2,
    SourceType.DERIVED: 1,
}


def confidence_from_result(
    verdict: TruthValue,
    score: float,
) -> ConfidenceLevel:
    """
    Übersetzt den internen Score in eine verständliche Konfidenz.

    Der Score ist keine statistische Wahrscheinlichkeit. Er dient nur zur
    Sortierung und zur Einschätzung der Belegstärke.
    """
    if verdict == TruthValue.UNKNOWN:
        return ConfidenceLevel.UNKNOWN

    absolute_score = abs(score)

    if absolute_score >= 110:
        return ConfidenceLevel.HIGH

    if absolute_score >= 100:
        return ConfidenceLevel.MEDIUM

    return ConfidenceLevel.LOW


def resolve_feature(plant: Plant, feature: str) -> Recommendation:
    """
    Ermittelt die Bewertung einer Pflanze für ein bestimmtes Merkmal.

    Priorität:
    1. Beschreibung
    2. strukturiertes Feld
    3. abgeleitete Information

    Innerhalb derselben Quellenart gewinnt der Beleg mit der höheren
    Sicherheit.
    """
    items = [
        evidence
        for evidence in plant.evidence
        if evidence.feature == feature
    ]

    if not items:
        return Recommendation(
            plant_id=plant.id,
            plant_name=plant.name,
            description=plant.description,
            verdict=TruthValue.UNKNOWN,
            score=0,
            reasons=[],
            conflicts=[],
            confidence=ConfidenceLevel.UNKNOWN,
        )

    ranked = sorted(
        items,
        key=lambda evidence: (
            SOURCE_PRIORITY[evidence.source],
            evidence.confidence,
        ),
        reverse=True,
    )

    winner = ranked[0]

    conflicts = [
        evidence
        for evidence in ranked[1:]
        if evidence.value != winner.value
    ]

    base_score = {
        TruthValue.YES: 100,
        TruthValue.NO: -100,
        TruthValue.UNKNOWN: 0,
    }[winner.value]

    source_bonus = SOURCE_PRIORITY[winner.source]
    confidence_bonus = winner.confidence * 10

    # Widersprüche ändern nicht die Entscheidung:
    # Die Beschreibung behält weiterhin Vorrang.
    # Sie senken lediglich die Konfidenz und die Sortierposition.
    conflict_penalty = len(conflicts) * 10

    if winner.value == TruthValue.YES:
        score = (
            base_score
            + confidence_bonus
            + source_bonus
            - conflict_penalty
        )
    elif winner.value == TruthValue.NO:
        score = (
            base_score
            - confidence_bonus
            - source_bonus
            + conflict_penalty
        )
    else:
        score = 0

    return Recommendation(
        plant_id=plant.id,
        plant_name=plant.name,
        description=plant.description,
        verdict=winner.value,
        score=score,
        reasons=[winner],
        conflicts=conflicts,
        confidence=confidence_from_result(
            verdict=winner.value,
            score=score,
        ),
    )


def requirement_matches(
    verdict: TruthValue,
    expected_value: RequirementValue,
) -> bool:
    """
    Prüft, ob die Pflanzeneigenschaft der Kundenanforderung entspricht.

    Beispiel:
    - Kunde möchte süß: expected_value=yes
    - Pflanze ist süß: verdict=yes
    - Ergebnis: passend

    Auch negative Anforderungen werden unterstützt:
    - Kunde möchte nicht süß: expected_value=no
    - Pflanze ist nicht süß: verdict=no
    - Ergebnis: passend
    """
    if verdict == TruthValue.UNKNOWN:
        return False

    if expected_value == RequirementValue.YES:
        return verdict == TruthValue.YES

    return verdict == TruthValue.NO


def evaluate_plant(
    plant: Plant,
    requirements: list[PlantRequirement],
) -> tuple[Recommendation, bool, bool]:
    """
    Bewertet eine Pflanze gegen alle Anforderungen.

    Rückgabe:
    - zusammengefasste Recommendation
    - hat expliziten Konflikt mit einer Pflichtanforderung
    - hat eine unbekannte Pflichtanforderung
    """
    total_score = 0.0

    reasons = []
    conflicts = []

    required_conflict = False
    required_unknown = False

    matched_count = 0

    for requirement in requirements:
        resolved = resolve_feature(
            plant=plant,
            feature=requirement.feature.value,
        )

        is_required = (
            requirement.importance
            == RequirementImportance.REQUIRED
        )

        if resolved.verdict == TruthValue.UNKNOWN:
            if is_required:
                required_unknown = True

            continue

        matches = requirement_matches(
            verdict=resolved.verdict,
            expected_value=requirement.value,
        )

        evidence_strength = abs(resolved.score)

        if matches:
            matched_count += 1
            reasons.extend(resolved.reasons)

            if is_required:
                total_score += 1000 + evidence_strength
            else:
                total_score += 100 + evidence_strength

            # Quelleninterne Widersprüche bleiben sichtbar.
            conflicts.extend(resolved.conflicts)

        else:
            conflicts.extend(resolved.reasons)
            conflicts.extend(resolved.conflicts)

            if is_required:
                required_conflict = True
                total_score -= 1000 + evidence_strength
            else:
                total_score -= 100 + evidence_strength

    if required_conflict:
        verdict = TruthValue.NO
    elif required_unknown:
        verdict = TruthValue.UNKNOWN
    elif matched_count > 0:
        verdict = TruthValue.YES
    else:
        verdict = TruthValue.UNKNOWN

    if verdict == TruthValue.UNKNOWN:
        confidence = ConfidenceLevel.UNKNOWN
    elif conflicts:
        confidence = ConfidenceLevel.LOW
    elif matched_count >= 2:
        confidence = ConfidenceLevel.HIGH
    else:
        confidence = ConfidenceLevel.MEDIUM

    return (
        Recommendation(
            plant_id=plant.id,
            plant_name=plant.name,
            description=plant.description,
            verdict=verdict,
            score=total_score,
            reasons=reasons,
            conflicts=conflicts,
            confidence=confidence,
        ),
        required_conflict,
        required_unknown,
    )


def advise_requirements(
    plants: list[Plant],
    query: ParsedQuery,
) -> AdviceResult:
    category = query.category.strip().casefold()
    candidates = [
        plant
        for plant in plants
        if (
            not category
            or (plant.category or "").strip().casefold() == category
        )
    ]

    evaluated = [
        evaluate_plant(
            plant=plant,
            requirements=query.requirements,
        )
        for plant in candidates
    ]

    positive = sorted(
        (
            recommendation
            for (
                recommendation,
                required_conflict,
                required_unknown,
            ) in evaluated
            if (
                not required_conflict
                and not required_unknown
                and recommendation.verdict
                == TruthValue.YES
            )
        ),
        key=lambda recommendation: recommendation.score,
        reverse=True,
    )

    unknown = sorted(
        (
            recommendation
            for (
                recommendation,
                required_conflict,
                required_unknown,
            ) in evaluated
            if (
                not required_conflict
                and (
                    required_unknown
                    or recommendation.verdict
                    == TruthValue.UNKNOWN
                )
            )
        ),
        key=lambda recommendation: recommendation.score,
        reverse=True,
    )

    excluded = sorted(
        (
            recommendation
            for (
                recommendation,
                required_conflict,
                required_unknown,
            ) in evaluated
            if required_conflict
        ),
        key=lambda recommendation: recommendation.score,
        reverse=True,
    )

    selected = positive[:3]

    if selected:
        names = ", ".join(
            recommendation.plant_name
            for recommendation in selected
        )

        answer = (
            "Nach den vorhandenen Angaben passen am besten: "
            f"{names}."
        )
    else:
        answer = (
            "In den vorhandenen Pflanzendaten gibt es keine "
            "eindeutig passende Empfehlung. Fehlende Angaben "
            "werden nicht als ungeeignet bewertet."
        )

    intent = ",".join(
        requirement.feature.value
        for requirement in query.requirements
    )

    return AdviceResult(
        question=query.original_question,
        intent=intent or "unknown",
        recommendations=selected,
        unknown=unknown,
        excluded=excluded,
        answer=answer,
    )


def advise(
    plants: list[Plant],
    query: ParsedQuery,
) -> AdviceResult:
    """
    Erstellt eine Beratung aus einer bereits interpretierten Frage.

    Der Advisor verarbeitet ausschließlich strukturierte Anforderungen
    und analysiert keine freie Sprache.
    """
    if query.follow_up_question:
        return AdviceResult(
            question=query.original_question,
            intent="follow_up",
            recommendations=[],
            unknown=[],
            excluded=[],
            answer=query.follow_up_question,
        )

    if not query.requirements:
        return AdviceResult(
            question=query.original_question,
            intent="unknown",
            recommendations=[],
            unknown=[],
            excluded=[],
            answer=(
                "Aus der Frage konnten keine auswertbaren "
                "Anforderungen abgeleitet werden."
            ),
        )

    return advise_requirements(
        plants=plants,
        query=query,
    )
