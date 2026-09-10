"""Source-verified import facts; source validity is not semantic approval."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PropertyDefinition(StrictModel):
    property_id: str
    field: str
    value_type: Literal["boolean", "number", "text"]
    semantics: str
    unit: str | None = None
    positive_only: bool = False
    minimum: float | None = None
    maximum: float | None = None


class SourceReference(StrictModel):
    field: str
    field_hash: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str


class CatalogueFact(StrictModel):
    fact_id: str
    plant_id: str
    property_id: str
    value: bool | float | str
    unit: str | None
    semantics: str
    value_max: float | None = None
    source: SourceReference
    origin: Literal["structured_field", "description_rule"] = "structured_field"
    source_verified: bool = True
    # Must not be promoted based only on an exact quote. Descriptions can
    # qualify or contradict structured fields; the next evaluator checks this.
    semantic_status: Literal["unreviewed", "rule_checked", "ambiguous"] = "unreviewed"


class ImportIssue(StrictModel):
    field: str
    reason: Literal["missing", "unchecked_positive", "placeholder_zero", "invalid_value"]


class PreparedPlant(StrictModel):
    plant_id: str
    content_hash: str
    facts: list[CatalogueFact]
    issues: list[ImportIssue]
    # Lossless local text corpus, including fields without an extraction rule.
    source_fields: dict[str, str]


class FactBundle(StrictModel):
    schema_version: str
    extractor_version: str
    registry_hash: str
    catalogue_revision: str
    registry: list[PropertyDefinition]
    plants: list[PreparedPlant]
