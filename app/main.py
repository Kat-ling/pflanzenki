from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from app.advisor.engine import advise
from app.repository import load_plants

from app.ai.interpreter_factory import create_query_interpreter
from app.ai.query_interpreter import QueryInterpreterError
from app.ai.dialogue_models import ChatMessage, DialoguePlan

app = FastAPI(
    title="KI-Birgit MVP",
    version="0.5.0",
)

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)
    previous_plan: DialoguePlan | None = None
    visible_plant_ids: list[str] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def check_history_size(self):
        if sum(len(m.content) for m in self.history) > 120000:
            raise ValueError("Das Gespräch ist zu lang. Bitte eine neue Beratung beginnen.")
        return self

class InterpretRequest(AskRequest):
    pass


def visible_plants(payload: AskRequest, plants):
    by_id = {p.id: p for p in plants}
    ids = payload.visible_plant_ids
    if len(set(ids)) != len(ids) or any(key not in by_id for key in ids):
        raise ValueError("Die angezeigten Sorten passen nicht mehr zum Katalog. Bitte eine neue Beratung beginnen.")
    return [{"plant_id": key, "name": by_id[key].name} for key in ids]

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

    <title>KI-Birgit</title>

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
            display: grid;
            grid-template-columns: minmax(180px, 230px) minmax(0, 1fr);
            gap: 1.2rem;
            align-items: start;
        }

        .plant-card--without-image {
            display: block;
        }

        .plant-card h2 {
            margin: 0 0 0.8rem;
            font-size: 1.25rem;
        }

        .plant-image-frame {
            width: 100%;
            aspect-ratio: 4 / 3;
            overflow: hidden;
            border: 1px solid #e0e3da;
            border-radius: 7px;
            background: #f2f4ee;
        }

        .plant-image {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .plant-content {
            min-width: 0;
            overflow-wrap: anywhere;
        }

        .plant-content p, .quote, .summary, .chat-message {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }

        .chat-message {
            padding: 0.8rem 1rem;
            margin: 0.7rem 0;
            border-left: 3px solid #668454;
            background: #f2f4ee;
        }

        .criterion-check {
            padding: 0.6rem 0;
            border-top: 1px solid #e1e1e1;
        }

        details {
            margin-top: 0.7rem;
        }

        summary {
            cursor: pointer;
        }

        .composer {
            margin-top: 1.5rem;
        }

        #question-label {
            display: block;
            font-weight: 650;
            margin-bottom: 0.5rem;
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

        @media (max-width: 560px) {
            body {
                margin-top: 1.5rem;
            }

            .plant-card {
                grid-template-columns: 1fr;
            }

            .plant-image-frame {
                max-width: 420px;
                margin: 0 auto;
            }
        }
    </style>
</head>

<body>
    <h1>KI-Birgit MVP v0.5</h1>

    <p class="example">
        Frag nach passenden Pflanzen, Sorten oder Eigenschaften.
    </p>

    <div id="conversation" role="log" aria-live="polite" aria-label="Gesprächsverlauf"></div>
    <div id="result"></div>

    <div class="composer">
    <label id="question-label" for="question">Deine Frage</label>
    <textarea
        id="question"
        maxlength="1000"
        aria-describedby="input-help"
        placeholder="Was möchtest du über deine Pflanzen wissen?"
    ></textarea>

    <button id="ask-button" type="button">
        Senden
    </button>
    <button id="reset-button" type="button">Neue Beratung</button>
    <p id="input-help">Hier kannst du auch Rückfragen beantworten oder Wünsche ergänzen.
    Enter sendet, Shift+Enter macht einen Zeilenumbruch. Der Verlauf bleibt nur in diesem geöffneten Tab.</p>
    </div>

    <div id="status" aria-live="polite"></div>

    <script>
        const questionInput =
            document.getElementById("question");

        const askButton =
            document.getElementById("ask-button");

        const statusOutput =
            document.getElementById("status");

        const resultOutput =
            document.getElementById("result");
        const conversationOutput = document.getElementById("conversation");
        const resetButton = document.getElementById("reset-button");
        const questionLabel = document.getElementById("question-label");
        let history = [];
        let shownNames = [];
        let lastReply = "";
        let previousPlan = null;
        let shownIds = [];

        function showMessage(role, text) {
            const message = document.createElement("div");
            message.className = "chat-message";
            message.textContent = (role === "user" ? "Du: " : "KI-Birgit: ") + text;
            conversationOutput.appendChild(message);
        }


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

            const content = document.createElement("div");
            content.className = "plant-content";

            const heading = document.createElement("h2");
            heading.textContent = recommendation.plant_name;

            if (recommendation.image_filenames.length) {
                const imageFrame = document.createElement("div");
                imageFrame.className = "plant-image-frame";

                const plantImage = document.createElement("img");
                plantImage.className = "plant-image";
                plantImage.loading = "lazy";
                plantImage.alt =
                    "Foto von " + recommendation.plant_name;
                plantImage.src =
                    "/static/images/" +
                    encodeURIComponent(
                        recommendation.image_filenames[0]
                    );
                plantImage.addEventListener(
                    "error",
                    () => {
                        imageFrame.remove();
                        card.classList.add(
                            "plant-card--without-image"
                        );
                    }
                );
                imageFrame.appendChild(plantImage);
                card.appendChild(imageFrame);
            } else {
                card.classList.add("plant-card--without-image");
            }

            content.appendChild(heading);

            if (recommendation.plant_category) {
                const category = document.createElement("p");
                category.className = "metadata";
                category.textContent =
                    "Kategorie: " + recommendation.plant_category;
                content.appendChild(category);
            }

            const description = document.createElement("p");

            if (recommendation.description) {
                description.textContent = recommendation.description;
            } else {
                description.textContent =
                    "Für diese Pflanze ist noch keine Beschreibung vorhanden.";
            }

            content.appendChild(description);

            if (recommendation.reasons.length) {
                const reasonTitle = document.createElement("p");
                reasonTitle.className = "section-title";
                reasonTitle.textContent = "Warum passend";
                content.appendChild(reasonTitle);

                const evidenceList = document.createElement("ul");
                evidenceList.className = "evidence";
                for (const evidence of recommendation.reasons) {
                    evidenceList.appendChild(
                        createEvidenceItem(evidence)
                    );
                }
                content.appendChild(evidenceList);
            }

            for (const check of recommendation.checks ?? []) {
                const section = document.createElement("div");
                section.className = "criterion-check";
                const label = document.createElement("strong");
                label.textContent = check.criterion
                    .replace(/\s*\((?:Quellen?\s*:?\s*)?s\d+(?:\s*[,;]\s*s\d+)*\s*\)/gi, "")
                    .trim();
                section.appendChild(label);
                if (check.reason) {
                    const explanation = document.createElement("p");
                    explanation.textContent = check.reason;
                    section.appendChild(explanation);
                }
                content.appendChild(section);
            }

            if (recommendation.catalogue_fields) {
                const details = document.createElement("details");
                const title = document.createElement("summary");
                title.textContent = "Alle Katalogangaben anzeigen";
                details.appendChild(title);
                for (const [field, value] of Object.entries(recommendation.catalogue_fields)) {
                    const line = document.createElement("p");
                    const label = document.createElement("strong");
                    label.textContent = field + ": ";
                    line.append(label, document.createTextNode(String(value)));
                    details.appendChild(line);
                }
                content.appendChild(details);
            }

            card.appendChild(content);

            return card;
        }


        function renderResult(data) {
            resultOutput.replaceChildren();
            shownNames = [];
            shownIds = [];

            for (const warning of data.warnings ?? []) {
                const notice = document.createElement("p");
                notice.className = "conflict";
                notice.textContent = warning;
                resultOutput.appendChild(notice);
            }

            renderCards(data.recommendations, resultOutput,
                data.intent === "catalog" ? 6 : 3, true);
            for (const [key, label] of [
                ["unknown", "Keine Empfehlung: fehlende oder unklare Belege"],
                ["excluded", "Keine Empfehlung: widersprechende Angaben"]
            ]) {
                if (!data[key]?.length) continue;
                const details = document.createElement("details");
                const title = document.createElement("summary");
                title.textContent = label + " (" + data[key].length + ")";
                details.appendChild(title);
                let loaded = false;
                details.addEventListener("toggle", () => {
                    if (details.open && !loaded) {
                        loaded = true;
                        renderCards(data[key], details, 3, false);
                    }
                });
                resultOutput.appendChild(details);
            }
        }

        function renderCards(items, target, pageSize, trackNames) {
            if (!items?.length) return;
            const recommendations =
                document.createElement("section");
            recommendations.className = "recommendations";
            target.appendChild(recommendations);
            const more = document.createElement("button");
            more.type = "button";
            let count = 0;
            function nextPage() {
                const next = items.slice(count, count + pageSize);
                for (const item of next) {
                    recommendations.appendChild(createPlantCard(item));
                    if (trackNames) shownNames.push(item.plant_name);
                    if (trackNames && item.plant_id) shownIds.push(item.plant_id);
                }
                count += next.length;
                more.textContent = "Weitere anzeigen (" + (items.length - count) + ")";
                more.hidden = count >= items.length;
            }
            more.addEventListener("click", nextPage);
            target.appendChild(more);
            nextPage();
        }


        async function askQuestion() {
            if (askButton.disabled) return;
            const question = questionInput.value.trim();

            if (!question) {
                statusOutput.textContent =
                    "Bitte gib zuerst eine Frage ein.";

                return;
            }

            if (history.length >= 40) {
                statusOutput.textContent = "Dieses Gespräch ist voll. Bitte mit ‚Neue Beratung‘ neu beginnen; es wird kein Verlauf stillschweigend abgeschnitten.";
                return;
            }

            askButton.disabled = true;
            resetButton.disabled = true;
            questionInput.disabled = true;
            statusOutput.textContent =
                "Katalog und Kombination werden geprüft. Das kann einen Moment dauern …";

            const requestHistory = history.map(message => ({...message}));
            if (requestHistory.length && shownNames.length) {
                requestHistory[requestHistory.length - 1].content =
                    lastReply + " Angezeigte passende Sorten in Reihenfolge: " + shownNames.join(", ");
            }

            try {
                const response = await fetch("/api/ask", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        question: question,
                        history: requestHistory,
                        previous_plan: previousPlan,
                        visible_plant_ids: shownIds
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    const errorText = typeof errorData.detail === "string"
                        ? errorData.detail : "Die Anfrage konnte nicht verarbeitet werden. Bitte Eingabe und Gesprächslänge prüfen.";

                    throw new Error(
                        "Serverfehler " +
                        response.status +
                        ": " +
                        errorText
                    );
                }

                const data = await response.json();
                previousPlan = data.plan ?? null;

                statusOutput.textContent = "";
                history = requestHistory;
                history.push({role: "user", content: question});
                const criteriaText = data.criteria?.length
                    ? " Aktuelle Kriterien: " + data.criteria.map(c => c.text).join("; ") : "";
                lastReply = data.answer + criteriaText;
                history.push({role: "assistant", content: lastReply});
                showMessage("user", question);
                showMessage("assistant", data.answer);
                renderResult(data);
                questionInput.value = "";
                const followUp = data.intent === "follow_up";
                questionLabel.textContent = followUp
                    ? "Deine Antwort auf die Rückfrage" : "Nachfrage oder weiterer Wunsch";
                questionInput.placeholder = followUp
                    ? "Antworte hier – deine bisherige Frage bleibt erhalten."
                    : "Du kannst die Auswahl hier verfeinern oder eine neue Frage stellen.";
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

                statusOutput.replaceChildren(errorBox);
            } finally {
                askButton.disabled = false;
                resetButton.disabled = false;
                questionInput.disabled = false;
                questionInput.focus();
            }
        }


        askButton.addEventListener(
            "click",
            askQuestion
        );

        resetButton.addEventListener("click", () => {
            history = [];
            shownNames = [];
            lastReply = "";
            previousPlan = null;
            shownIds = [];
            conversationOutput.replaceChildren();
            resultOutput.replaceChildren();
            statusOutput.replaceChildren();
            questionInput.value = "";
            questionLabel.textContent = "Deine Frage";
            questionInput.placeholder = "Was möchtest du über deine Pflanzen wissen?";
            questionInput.focus();
        });


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
        from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
        if isinstance(interpreter, OpenAIQueryInterpreter):
            from app.ai.catalogue_answer import consult
            plants = load_plants()
            return consult(interpreter, plants, payload.question, payload.history,
                           payload.previous_plan, visible_plants(payload, plants))
        if payload.history:
            raise ValueError(
                "Der lokale Fake-Interpreter unterstützt keine Gespräche. "
                "Bitte QUERY_INTERPRETER_PROVIDER=openai verwenden oder eine neue Beratung beginnen."
            )
        parsed_query = interpreter.interpret(payload.question)

        result = advise(
            plants=load_plants(),
            query=parsed_query,
        )
        return {**result.model_dump(), "warnings": [
            "Lokaler Testmodus: nur feste Merkmale, keine freie Gesprächsauswertung. "
            "Für natürliche Beratung QUERY_INTERPRETER_PROVIDER=openai verwenden."
        ]}

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
)
def interpret_question(
    payload: InterpretRequest,
):
    try:
        interpreter = create_query_interpreter()
        from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
        if isinstance(interpreter, OpenAIQueryInterpreter):
            from app.ai.catalogue_dialogue import interpret_dialogue
            plants = load_plants()
            return interpret_dialogue(interpreter, plants, payload.question, payload.history,
                                      payload.previous_plan, visible_plants(payload, plants))
        if payload.history:
            raise ValueError("Gesprächskontext erfordert QUERY_INTERPRETER_PROVIDER=openai.")

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
