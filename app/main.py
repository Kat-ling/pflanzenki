from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.advisor.engine import advise
from app.repository import load_plants

from app.ai.interpreter_factory import create_query_interpreter
from app.ai.query_interpreter import QueryInterpreterError
from app.ai.query_models import ParsedQuery

app = FastAPI(
    title="PflanzenKI MVP",
    version="0.2.0",
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)

class InterpretRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>PflanzenKI MVP</title>

    <style>
        :root {
            font-family: system-ui, sans-serif;
            line-height: 1.5;
        }

        body {
            max-width: 820px;
            margin: 3rem auto;
            padding: 0 1rem 3rem;
        }

        h1 {
            margin-bottom: 0.5rem;
        }

        .example {
            margin-bottom: 1rem;
        }

        textarea {
            width: 100%;
            min-height: 110px;
            box-sizing: border-box;
            padding: 0.9rem;
            border: 1px solid #888;
            border-radius: 4px;
            font: inherit;
            resize: vertical;
        }

        button {
            margin-top: 0.8rem;
            padding: 0.75rem 1.2rem;
            border: 1px solid #777;
            border-radius: 4px;
            font: inherit;
            cursor: pointer;
        }

        button:disabled {
            cursor: wait;
            opacity: 0.65;
        }

        #status {
            margin-top: 1.2rem;
        }

        .summary {
            margin-top: 1.2rem;
            padding: 1rem;
            background: #f4f4f4;
            border-radius: 4px;
        }

        .recommendations {
            display: grid;
            gap: 1rem;
            margin-top: 1rem;
        }

        .plant-card {
            padding: 1.1rem;
            border: 1px solid #ccc;
            border-radius: 7px;
            background: white;
        }

        .plant-card h2 {
            margin: 0 0 0.8rem;
            font-size: 1.25rem;
        }

        .section-title {
            margin: 0.8rem 0 0.35rem;
            font-weight: 650;
        }

        .evidence {
            margin: 0.4rem 0;
            padding-left: 1.4rem;
        }

        .evidence li {
            margin-bottom: 0.4rem;
        }

        .quote {
            font-style: italic;
        }

        .metadata {
            margin-top: 0.9rem;
            display: grid;
            gap: 0.25rem;
        }

        .conflict {
            margin-top: 0.8rem;
            padding: 0.7rem;
            background: #fff4e5;
            border-radius: 4px;
        }

        .error {
            margin-top: 1rem;
            padding: 1rem;
            background: #ffe8e8;
            border-radius: 4px;
        }
    </style>
</head>

<body>
    <h1>PflanzenKI MVP v0.2</h1>

    <p class="example">
        Beispiel: Welche Tomaten eignen sich draußen ohne Dach?
    </p>

    <textarea id="question">Welche Tomaten eignen sich draußen ohne Dach?</textarea>

    <button id="ask-button" type="button">
        Fragen
    </button>

    <div id="status" aria-live="polite"></div>
    <div id="result"></div>

    <script>
        const questionInput =
            document.getElementById("question");

        const askButton =
            document.getElementById("ask-button");

        const statusOutput =
            document.getElementById("status");

        const resultOutput =
            document.getElementById("result");


        function sourceLabel(evidence) {
            if (evidence.source === "description") {
                return "Beschreibung";
            }

            if (evidence.source === "structured_field") {
                if (evidence.field_name) {
                    return (
                        "Strukturiertes Feld: " +
                        evidence.field_name
                    );
                }

                return "Strukturiertes Feld";
            }

            if (evidence.source === "derived") {
                return "Abgeleitete Information";
            }

            return "Unbekannte Quelle";
        }


        function confidenceLabel(confidence) {
            const labels = {
                high: "Hoch",
                medium: "Mittel",
                low: "Gering",
                unknown: "Unbekannt"
            };

            return labels[confidence] ?? "Unbekannt";
        }


        function createEvidenceItem(evidence) {
            const item = document.createElement("li");

            const source = document.createElement("strong");
            source.textContent = sourceLabel(evidence) + ": ";

            item.appendChild(source);

            const quote = document.createElement("span");
            quote.className = "quote";

            if (evidence.quote) {
                quote.textContent = "„" + evidence.quote + "“";
            } else {
                quote.textContent =
                    "Positiver Beleg in den Pflanzendaten";
            }

            item.appendChild(quote);

            return item;
        }


        function createPlantCard(recommendation) {
            const card = document.createElement("article");
            card.className = "plant-card";

            const heading = document.createElement("h2");
            heading.textContent = recommendation.plant_name;
            card.appendChild(heading);

            const description = document.createElement("p");

            if (recommendation.description) {
                description.textContent = recommendation.description;
            } else {
                description.textContent =
                    "Für diese Pflanze ist noch keine Beschreibung vorhanden.";
            }

            card.appendChild(description);

            return card;
        }


        function renderResult(data) {
            resultOutput.replaceChildren();

            const summary = document.createElement("div");
            summary.className = "summary";
            summary.textContent = data.answer;
            resultOutput.appendChild(summary);

            if (!data.recommendations.length) {
                return;
            }

            const recommendations =
                document.createElement("section");

            recommendations.className = "recommendations";

            for (
                const recommendation
                of data.recommendations
            ) {
                recommendations.appendChild(
                    createPlantCard(recommendation)
                );
            }

            resultOutput.appendChild(recommendations);
        }


        async function askQuestion() {
            const question = questionInput.value.trim();

            if (!question) {
                statusOutput.textContent =
                    "Bitte gib zuerst eine Frage ein.";

                resultOutput.replaceChildren();
                return;
            }

            askButton.disabled = true;
            statusOutput.textContent =
                "Antwort wird erstellt …";

            resultOutput.replaceChildren();

            try {
                const response = await fetch("/api/ask", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        question: question
                    })
                });

                if (!response.ok) {
                    const errorText = await response.text();

                    throw new Error(
                        "Serverfehler " +
                        response.status +
                        ": " +
                        errorText
                    );
                }

                const data = await response.json();

                statusOutput.textContent = "";
                renderResult(data);
            } catch (error) {
                console.error(
                    "Fehler beim Senden der Frage:",
                    error
                );

                statusOutput.textContent = "";

                const errorBox =
                    document.createElement("div");

                errorBox.className = "error";
                errorBox.textContent =
                    "Die Anfrage konnte nicht verarbeitet " +
                    "werden: " +
                    error.message;

                resultOutput.replaceChildren(errorBox);
            } finally {
                askButton.disabled = false;
            }
        }


        askButton.addEventListener(
            "click",
            askQuestion
        );


        questionInput.addEventListener(
            "keydown",
            function (event) {
                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {
                    event.preventDefault();
                    askQuestion();
                }
            }
        );
    </script>
</body>
</html>"""


@app.post("/api/ask")
def ask(payload: AskRequest):
    try:
        interpreter = create_query_interpreter()
        parsed_query = interpreter.interpret(payload.question)

        return advise(
            plants=load_plants(),
            query=parsed_query,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except QueryInterpreterError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/interpret",
    response_model=ParsedQuery,
)
def interpret_question(
    payload: InterpretRequest,
) -> ParsedQuery:
    try:
        interpreter = create_query_interpreter()

        return interpreter.interpret(
            payload.question
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except QueryInterpreterError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc