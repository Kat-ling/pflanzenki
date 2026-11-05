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
    message.textContent = (role === "user" ? "Du: " : "KI-Sister: ") + text;
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
