from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.ai.query_interpreter import QueryInterpreterError
from app.ai.query_models import ParsedQuery, PlantFeature


SYSTEM_INSTRUCTIONS = """
Du bist der Query Interpreter eines Pflanzenberaters.

Deine einzige Aufgabe ist, eine deutschsprachige Kundenfrage in
strukturierte Anforderungen zu übersetzen.

Du empfiehlst selbst keine Pflanzen.
Du erfindest keine Pflanzeneigenschaften.
Du greifst nicht auf Pflanzendaten zu.

Bekannte Merkmale:

- outdoor_uncovered:
  Anbau draußen ohne Dach oder ohne Regenschutz. Dazu gehören auch
  Aussagen wie: Regen trifft direkt auf die Pflanze, ungeschütztes
  Freiland oder kein Dach vorhanden.

- balcony:
  Geeignet für Balkon, Terrasse, Kübel oder Topf.

- greenhouse:
  Gewächshaus, Folientunnel, unter Dach oder geschützter Anbau.

- sweet:
  Süßer Geschmack.

- aromatic:
  Aromatischer oder besonders intensiver Geschmack.

- easy_care:
  Pflegeleicht, unkompliziert oder für Anfänger geeignet.

- early:
  Frühe Reife oder frühe Ernte.

- sauce_tomato:
  Gewünscht für Soße, Einkochen, Passata oder Verarbeitung.

- robust:
  Robuste, widerstandsfähige oder tolerante Pflanze.

- small_fruit:
  Kleine Früchte, Cocktailtomaten oder Snacktomaten.

- warm_location:
  Warmer Standort oder besonders wärmebedürftig.

- drought_tolerant:
  Trockenheitsverträglich oder geringer Wasserbedarf.

- winter_hardy:
  Winterhart oder mehrjährig im Freien überwinterbar.

Regeln:

1. Unterscheide Pflichtanforderungen von Präferenzen.

2. Ein ausdrücklicher Standort ist normalerweise required.
   Beispiel:
   "für meinen Balkon" bedeutet balcony=yes und required.

3. Geschmackswünsche sind normalerweise preferred.
   Beispiel:
   "gerne süß" bedeutet sweet=yes und preferred.

4. Verneinungen müssen als value=no erfasst werden.
   Beispiel:
   "nicht scharf" darf nicht zu einer positiven Anforderung werden.

5. Erfinde keine Information, die nicht aus der Frage hervorgeht.

6. Stelle nur dann eine Rückfrage, wenn ohne diese Information keine
   sinnvolle Pflanzenauswahl möglich wäre.

7. Formuliere höchstens eine Rückfrage.

8. Eine allgemeine Frage wie
   "Welche Tomate empfiehlst du?"
   benötigt eine Rückfrage zum vorgesehenen Standort.

9. Eine konkrete Frage wie
   "Welche Tomate geht draußen ohne Dach?"
   benötigt keine Rückfrage.

10. Wünsche, die keinem bekannten Merkmal entsprechen, kommen in
    unsupported_requests.

11. category enthält nur die erkennbare Pflanzenkategorie.
    Wenn keine Kategorie erkennbar ist, bleibt category leer.

12. Antworte ausschließlich im vorgegebenen strukturierten Format.
""".strip()


QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "category": {
            "type": "string",
            "description": (
                "Pflanzenkategorie oder leerer String, "
                "wenn keine Kategorie erkannt wurde."
            ),
        },
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "feature": {
                        "type": "string",
                        "enum": [
                            feature.value
                            for feature in PlantFeature
                        ],
                    },
                    "value": {
                        "type": "string",
                        "enum": [
                            "yes",
                            "no",
                        ],
                    },
                    "importance": {
                        "type": "string",
                        "enum": [
                            "required",
                            "preferred",
                        ],
                    },
                    "reason": {
                        "type": "string",
                    },
                },
                "required": [
                    "feature",
                    "value",
                    "importance",
                    "reason",
                ],
            },
        },
        "follow_up_question": {
            "type": "string",
        },
        "unsupported_requests": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "category",
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
    ) -> None:
        if client is None and not os.getenv("OPENAI_API_KEY"):
            raise QueryInterpreterError(
                "OPENAI_API_KEY ist nicht konfiguriert. "
                "Lege den Schlüssel in der Umgebungsvariable oder "
                "in der lokalen .env-Datei ab."
            )

        self.client = client or OpenAI()

        self.model = (
            model
            or os.getenv("OPENAI_QUERY_MODEL")
            or "gpt-5-mini"
        )

    def interpret(self, question: str) -> ParsedQuery:
        cleaned_question = question.strip()

        if not cleaned_question:
            raise ValueError(
                "Die Kundenfrage darf nicht leer sein."
            )

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTIONS,
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
