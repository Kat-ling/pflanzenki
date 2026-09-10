from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.ai.query_interpreter import QueryInterpreterError
from app.ai.query_models import ParsedQuery, QueryIntent
from app.feature_catalog import FEATURE_DESCRIPTIONS, PlantFeature
from app.repository import load_categories


SYSTEM_INSTRUCTIONS = """
Du bist der Query Interpreter eines Pflanzenberaters.

Übersetze freie deutschsprachige Kundenfragen ausschließlich in das
vorgegebene strukturierte Format. Du empfiehlst selbst keine Pflanzen,
erfindest keine Eigenschaften und greifst nicht auf konkrete Pflanzendaten zu.

Intents:
- recommendation: Der Kunde sucht geeignete Pflanzen oder Sorten.
- information: Der Kunde fragt nach einer ausdrücklich genannten Sorte.
- comparison: Der Kunde möchte ausdrücklich genannte Sorten vergleichen.
- catalog: Der Kunde fragt, welche Pflanzen oder Sorten einer Kategorie im
  Katalog vorhanden sind, ohne weitere Eignungskriterien zu nennen.

Regeln:
1. Verwende als category genau eine passende Singularform aus der Liste der
   verfügbaren Kategorien. Bleibe leer, wenn keine Kategorie genannt oder
   sicher ableitbar ist. Eine leere Kategorie erlaubt eine katalogweite Suche.
2. plant_names enthält nur ausdrücklich genannte Sorten- oder Pflanzennamen.
   Kategorien wie Tomate oder Gurke sind keine plant_names.
3. Standort- und Platzgrenzen sind normalerweise required. Geschmack,
   Farbe, Ertrag und ähnliche Wünsche sind normalerweise preferred.
4. Verneinungen werden mit value=no erfasst. "Nicht scharf" ist spicy=no;
   es ist nicht automatisch mild=yes.
5. Leite nur Anforderungen ab, die in der Frage tatsächlich enthalten sind.
6. Eine Rückfrage ist nur nötig, wenn eine Empfehlung ohne sie beliebig wäre.
   Wenn bereits mindestens ein brauchbares Kriterium genannt ist, frage nicht
   vorsorglich nach weiteren Wünschen.
7. Formuliere höchstens eine kurze Rückfrage.
8. Nicht abbildbare Wünsche kommen in unsupported_requests.
9. Fragen wie "Welche Zucchini-Sorten gibt es?" oder "Habt ihr Auberginen?"
   erhalten intent=catalog, die passende category und keine erfundenen
   requirements.
10. reason darf niemals leer sein.
11. Antworte ausschließlich im vorgegebenen strukturierten Format.
""".strip()


def build_instructions(categories: list[str]) -> str:
    category_text = ", ".join(categories) if categories else "keine geladen"
    features = "\n".join(
        f"- {feature.value}: {FEATURE_DESCRIPTIONS[feature]}"
        for feature in PlantFeature
    )
    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"Verfügbare Kategorien:\n{category_text}\n\n"
        f"Bekannte Merkmale:\n{features}"
    )


QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {
            "type": "string",
            "enum": [intent.value for intent in QueryIntent],
        },
        "category": {"type": "string"},
        "plant_names": {
            "type": "array",
            "items": {"type": "string"},
        },
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "feature": {
                        "type": "string",
                        "enum": [feature.value for feature in PlantFeature],
                    },
                    "value": {
                        "type": "string",
                        "enum": ["yes", "no"],
                    },
                    "importance": {
                        "type": "string",
                        "enum": ["required", "preferred"],
                    },
                    "reason": {"type": "string"},
                },
                "required": [
                    "feature",
                    "value",
                    "importance",
                    "reason",
                ],
            },
        },
        "follow_up_question": {"type": "string"},
        "unsupported_requests": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "intent",
        "category",
        "plant_names",
        "requirements",
        "follow_up_question",
        "unsupported_requests",
    ],
}


class OpenAIQueryInterpreter:
    def __init__(
        self,
        client: OpenAI | None = None,
        model: str | None = None,
        categories: list[str] | None = None,
    ) -> None:
        if client is None and not os.getenv("OPENAI_API_KEY"):
            raise QueryInterpreterError(
                "OPENAI_API_KEY ist nicht konfiguriert. "
                "Lege den Schlüssel in der Umgebungsvariable oder "
                "in der lokalen .env-Datei ab."
            )

        self.client = client or OpenAI(timeout=30.0, max_retries=0)
        self.model = (
            model
            or os.getenv("OPENAI_QUERY_MODEL")
            or "gpt-5-mini"
        )
        self.categories = categories if categories is not None else load_categories()

    def interpret(self, question: str) -> ParsedQuery:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("Die Kundenfrage darf nicht leer sein.")

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=build_instructions(self.categories),
                input=cleaned_question,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "parsed_plant_query",
                        "description": (
                            "Strukturierte Anforderungen aus einer "
                            "Kundenfrage an einen Pflanzenberater."
                        ),
                        "schema": QUERY_SCHEMA,
                        "strict": True,
                    }
                },
            )
        except Exception as exc:
            raise QueryInterpreterError(
                "Die KI-Anfrage konnte nicht ausgeführt werden."
            ) from exc

        if not response.output_text:
            raise QueryInterpreterError(
                "Das KI-Modell hat keine auswertbare Antwort geliefert."
            )

        try:
            raw_result = json.loads(response.output_text)
        except json.JSONDecodeError as exc:
            raise QueryInterpreterError(
                "Die KI-Antwort war kein gültiges JSON."
            ) from exc

        raw_result["original_question"] = cleaned_question
        try:
            return ParsedQuery.model_validate(raw_result)
        except ValidationError as exc:
            raise QueryInterpreterError(
                "Die KI-Antwort entsprach nicht dem erwarteten Schema."
            ) from exc
