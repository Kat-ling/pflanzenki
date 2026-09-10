from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TruthValue(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    DESCRIPTION = "description"
    STRUCTURED_FIELD = "structured_field"
    DERIVED = "derived"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Evidence(BaseModel):
    feature: str
    value: TruthValue
    source: SourceType
    quote: str | None = None
    field_name: str | None = None
    confidence: float = Field(ge=0, le=1)


class Plant(BaseModel):
    id: str
    name: str
    category: str | None = None
    description: str = ""
    image_filenames: list[str] = Field(default_factory=list)
    raw_fields: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


class Recommendation(BaseModel):
    plant_id: str
    plant_name: str
    plant_category: str = ""
    description: str = ""
    image_filenames: list[str] = Field(default_factory=list)
    verdict: TruthValue
    score: float

    # Belege, auf denen die Entscheidung beruht
    reasons: list[Evidence] = Field(default_factory=list)

    # Belege, die der Entscheidung widersprechen
    conflicts: list[Evidence] = Field(default_factory=list)

    # Verständliche Ableitung aus dem internen Score
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN


class AdviceResult(BaseModel):
    question: str
    intent: str
    recommendations: list[Recommendation]
    unknown: list[Recommendation] = Field(default_factory=list)
    excluded: list[Recommendation] = Field(default_factory=list)
    answer: str
