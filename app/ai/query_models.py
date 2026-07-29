from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class RequirementValue(str, Enum):
    YES = "yes"
    NO = "no"


class RequirementImportance(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class PlantFeature(str, Enum):
    OUTDOOR_UNCOVERED = "outdoor_uncovered"
    BALCONY = "balcony"
    GREENHOUSE = "greenhouse"
    SWEET = "sweet"
    AROMATIC = "aromatic"
    EASY_CARE = "easy_care"
    EARLY = "early"
    SAUCE_TOMATO = "sauce_tomato"
    ROBUST = "robust"
    SMALL_FRUIT = "small_fruit"
    WARM_LOCATION = "warm_location"
    DROUGHT_TOLERANT = "drought_tolerant"
    WINTER_HARDY = "winter_hardy"


class PlantRequirement(BaseModel):
    feature: PlantFeature
    value: RequirementValue
    importance: RequirementImportance
    reason: str = Field(
        min_length=1,
        description=(
            "Kurze Begründung, aus welcher Aussage der Kundenfrage "
            "diese Anforderung abgeleitet wurde."
        ),
    )


class ParsedQuery(BaseModel):
    original_question: str

    category: str = Field(
        default="",
        description=(
            "Gesuchte Pflanzenkategorie, beispielsweise Tomate, Chili, "
            "Gurke oder Zucchini. Leer, wenn nicht erkennbar."
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
        return self