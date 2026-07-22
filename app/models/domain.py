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
    raw_fields: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


class Recommendation(BaseModel):
    plant_id: str
    plant_name: str
    verdict: TruthValue
    score: float
    reasons: list[Evidence]
    conflicts: list[Evidence] = Field(default_factory=list)


class AdviceResult(BaseModel):
    question: str
    intent: str
    recommendations: list[Recommendation]
    unknown: list[Recommendation] = Field(default_factory=list)
    excluded: list[Recommendation] = Field(default_factory=list)
    answer: str
