"""Free-language criteria: new catalogue properties require no enum changes."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Expression(BaseModel):
    """Small typed tree. All fields required for Responses strict JSON schema."""
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    op: Literal["all", "any", "not", "predicate", "unresolved"]
    text: str = Field(min_length=1, max_length=1000)
    property_id: str
    comparator: Literal["eq", "lt", "lte", "gt", "gte", "exists"]
    value: bool | float | str | None
    unit: str | None
    children: list["Expression"] = Field(max_length=20)

    @model_validator(mode="after")
    def shape(self):
        if self.op in {"all", "any", "not"}:
            if not self.children or (self.op == "not" and len(self.children) != 1):
                raise ValueError("Ungültige logische Verknüpfung.")
            if self.property_id or self.value is not None or self.unit is not None or self.comparator != "eq":
                raise ValueError("Verknüpfungen dürfen keine versteckten Bedingungen enthalten.")
        elif self.children:
            raise ValueError("Einzelkriterien dürfen keine Kinder enthalten.")
        if self.op == "predicate":
            if not self.property_id:
                raise ValueError("Eigenschaft fehlt.")
            if (self.comparator == "exists") != (self.value is None):
                raise ValueError("Vergleichswert fehlt oder ist bei exists unzulässig.")
        if self.op == "unresolved" and (self.property_id or self.value is not None or self.unit is not None or self.comparator != "eq"):
            raise ValueError("Unaufgelöster Wunsch darf keine vermeintliche Zuordnung enthalten.")
        return self


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class Criterion(StrictModel):
    text: str = Field(min_length=1, max_length=1000)
    importance: Literal["required", "preferred"]
    kind: Literal["condition", "information"]
    expression: Expression


class DialoguePlan(StrictModel):
    intent: Literal["recommendation", "information", "comparison", "catalog"]
    categories: list[str]
    plant_names: list[str]
    criteria: list[Criterion] = Field(max_length=20)
    follow_up_question: str
    unsupported_requests: list[str]

    @model_validator(mode="after")
    def bounded_expression(self):
        def measure(node, depth=1):
            if depth > 6:
                raise ValueError("Suchauftrag zu tief verschachtelt. Bitte vereinfachen.")
            return (1 if not node.children else 0) + sum(measure(c, depth + 1) for c in node.children)
        if sum(measure(c.expression) for c in self.criteria) > 20:
            raise ValueError("Mehr als 20 Einzelbedingungen. Bitte vereinfachen.")
        return self


class Citation(StrictModel):
    field: str
    quote: str


class Assessment(StrictModel):
    criterion_index: int
    status: Literal["yes", "no", "unknown"]
    citations: list[Citation]


class PlantAssessment(StrictModel):
    plant_id: str
    assessments: list[Assessment]


class AssessmentBatch(StrictModel):
    plants: list[PlantAssessment]
