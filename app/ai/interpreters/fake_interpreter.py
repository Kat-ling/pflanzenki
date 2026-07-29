from __future__ import annotations

from app.ai.query_models import (
    ParsedQuery,
    PlantFeature,
    PlantRequirement,
    RequirementImportance,
    RequirementValue,
)


class FakeQueryInterpreter:
    """
    Lokaler Interpreter ohne externe API.

    Er ist nur für Entwicklung und automatisierte Tests gedacht.
    """

    def interpret(self, question: str) -> ParsedQuery:
        cleaned_question = question.strip()

        if not cleaned_question:
            raise ValueError(
                "Die Kundenfrage darf nicht leer sein."
            )

        normalized = cleaned_question.lower()
        requirements: list[PlantRequirement] = []

        category = ""

        if "tomate" in normalized:
            category = "Tomate"

        if any(
            phrase in normalized
            for phrase in (
                "ohne dach",
                "ohne regenschutz",
                "ungeschützt",
                "ungeschuetzt",
                "freiland",
            )
        ):
            requirements.append(
                PlantRequirement(
                    feature=PlantFeature.OUTDOOR_UNCOVERED,
                    value=RequirementValue.YES,
                    importance=RequirementImportance.REQUIRED,
                    reason=(
                        "Ein ungeschützter Standort im Freiland "
                        "wird genannt."
                    ),
                )
            )

        if "balkon" in normalized:
            requirements.append(
                PlantRequirement(
                    feature=PlantFeature.BALCONY,
                    value=RequirementValue.YES,
                    importance=RequirementImportance.REQUIRED,
                    reason="In der Frage wird ein Balkon genannt.",
                )
            )

        if any(
            phrase in normalized
            for phrase in (
                "gewächshaus",
                "gewaechshaus",
                "folientunnel",
                "unter dach",
            )
        ):
            requirements.append(
                PlantRequirement(
                    feature=PlantFeature.GREENHOUSE,
                    value=RequirementValue.YES,
                    importance=RequirementImportance.REQUIRED,
                    reason="Ein geschützter Anbau wird genannt.",
                )
            )

        if "süß" in normalized or "suess" in normalized:
            requirements.append(
                PlantRequirement(
                    feature=PlantFeature.SWEET,
                    value=RequirementValue.YES,
                    importance=RequirementImportance.PREFERRED,
                    reason="Ein süßer Geschmack wird gewünscht.",
                )
            )

        if (
            "pflegeleicht" in normalized
            or "unkompliziert" in normalized
            or "anfänger" in normalized
        ):
            requirements.append(
                PlantRequirement(
                    feature=PlantFeature.EASY_CARE,
                    value=RequirementValue.YES,
                    importance=RequirementImportance.PREFERRED,
                    reason=(
                        "Eine pflegeleichte oder für Anfänger "
                        "geeignete Pflanze wird gewünscht."
                    ),
                )
            )

        follow_up_question = ""

        if category and not requirements:
            follow_up_question = (
                "Wo soll die Pflanze wachsen: im Freiland, "
                "im Gewächshaus oder auf dem Balkon?"
            )

        return ParsedQuery(
            original_question=cleaned_question,
            category=category,
            requirements=requirements,
            follow_up_question=follow_up_question,
            unsupported_requests=[],
        )
