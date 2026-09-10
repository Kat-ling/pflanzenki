from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.feature_catalog import PlantFeature


class RequirementValue(str, Enum):
    YES = "yes"
    NO = "no"


class RequirementImportance(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class QueryIntent(str, Enum):
    RECOMMENDATION = "recommendation"
    INFORMATION = "information"
    COMPARISON = "comparison"
    CATALOG = "catalog"


class PlantRequirement(BaseModel):
    feature: PlantFeature
    value: RequirementValue
    importance: RequirementImportance
    reason: str = Field(
        default="Aus der Kundenfrage abgeleitet.",
        description=(
            "Kurze Begründung, aus welcher Aussage der Kundenfrage "
            "diese Anforderung abgeleitet wurde."
        ),
    )


class ParsedQuery(BaseModel):
    original_question: str

    intent: QueryIntent = QueryIntent.RECOMMENDATION

    category: str = Field(
        default="",
        description=(
            "Gesuchte Pflanzenkategorie, beispielsweise Tomate, Chili, "
            "Gurke oder Zucchini. Leer, wenn nicht erkennbar."
        ),
    )

    plant_names: list[str] = Field(
        default_factory=list,
        description=(
            "Explizit genannte Sorten- oder Pflanzennamen. Keine Namen "
            "aus der Frage erfinden."
        ),
    )

    requirements: list[PlantRequirement] = Field(
        default_factory=list
    )

    follow_up_question: str = Field(
        default="",
        description=(
            "Eine einzige notwendige Rückfrage. Leer, wenn keine "
            "Rückfrage erforderlich ist."
        ),
    )

    unsupported_requests: list[str] = Field(
        default_factory=list,
        description=(
            "Wünsche, die nicht auf ein bekanntes Merkmal abgebildet "
            "werden konnten."
        ),
    )

    @model_validator(mode="after")
    def remove_duplicate_requirements(self) -> "ParsedQuery":
        unique: dict[
            tuple[PlantFeature, RequirementValue],
            PlantRequirement,
        ] = {}

        for requirement in self.requirements:
            if not requirement.reason.strip():
                requirement.reason = "Aus der Kundenfrage abgeleitet."
            key = (
                requirement.feature,
                requirement.value,
            )

            existing = unique.get(key)

            if existing is None:
                unique[key] = requirement
                continue

            if (
                existing.importance
                == RequirementImportance.PREFERRED
                and requirement.importance
                == RequirementImportance.REQUIRED
            ):
                unique[key] = requirement

        self.requirements = list(unique.values())
        self.plant_names = list(dict.fromkeys(
            name.strip()
            for name in self.plant_names
            if name.strip()
        ))
        return self
