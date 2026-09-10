"""Bounded local candidate search, never a botanical truth filter."""
import json
import math
import re
from collections import Counter
from functools import lru_cache

STOP = set("ich du mir mich welche welchen welcher gibt ist sind haben hat suche bitte und oder mit ohne der die das ein eine einer für von in im den dem es nun doch lieber als nach".split())

# Export bookkeeping and derived search tags are useful locally, not as
# duplicate evidence in every model request. Original cards retain everything.
LOCAL_ONLY = {"Namensbestandteile", "Name_für_Katalog",
              "Filter_Tags", "Abstand_Code", "Abstand_Anzeige", "Ernte_Hinweis"}


def answer_fields(original):
    fields = {k: original[k] for k in ("Name", "Kategorie", "Beschreibung")}
    for key, value in original.items():
        if key in fields or key in LOCAL_ONLY:
            continue
        if value.strip().casefold() in {"no", "false", "nein", "unchecked", "0", "0.0", "0,0"} and key != "Schärfegrad MAX":
            continue
        if len(value) >= 12 and value in original["Beschreibung"]:
            continue
        fields[key] = value
    return fields


def terms(text):
    words = re.findall(r"[a-zäöüß0-9]+", text.casefold())
    result = {w[:5] for w in words if len(w) > 2 and w not in STOP}
    # Retrieval expansion only: these words do not certify matching properties.
    if any("tomat" in w for w in words):
        result.add("tomat")
    if any(w.startswith(("cocktail", "cherry", "kirsch", "klein")) for w in words):
        result.update({"cockt", "cherr", "kirsc", "klein"})
    return result


def records(plants):
    return [{"plant_id": p.id, "fields": {"Name": p.name, "Kategorie": p.category or "",
             "Beschreibung": p.description,
             **{str(k): str(v) for k, v in p.raw_fields.items()
                if v is not None and str(v).strip() and k not in {"Name", "Kategorie", "Beschreibung", "Bild"}}}}
            for p in plants]


@lru_cache(maxsize=2)
def index(serialized):
    rows = json.loads(serialized)
    documents = [terms(" ".join(row["fields"].values())) for row in rows]
    frequencies = Counter(t for document in documents for t in document)
    return rows, documents, frequencies


def retrieve(plants, question, history, visible=(), limit=24, budget=28000):
    rows, documents, frequencies = index(json.dumps(records(plants), ensure_ascii=False))
    current = terms(question)
    prior = terms(" ".join(m.content for m in history if m.role == "user"))
    visible_ids = {p["plant_id"] for p in visible}
    scored = []
    height_query = bool(re.search(r"niedrig|wuchshöhe|klein\w*\s+(?:pflanz|wuchs)|kompakt", question, re.I))
    if not height_query and history:
        height_query = bool(re.search(r"niedrig|wuchshöhe", history[-1].content, re.I))
    normalized_question = " ".join(re.findall(r"\w+", question.casefold()))
    for row, document in zip(rows, documents):
        score = sum((3 if t in current else .3) * math.log(1 + len(rows) / frequencies[t])
                    for t in document & (current | prior))
        name = row["fields"]["Name"].casefold()
        if terms(row["fields"]["Kategorie"]) & current:
            score += 20
        if " ".join(re.findall(r"\w+", name)) in normalized_question:
            score += 100
        if height_query:
            description = row["fields"]["Beschreibung"]
            # Rank actual growth descriptions, never imported numeric columns or
            # bare fruit-size adjectives. This is recall, not a suitability verdict.
            if re.search(r"\d\s*(?:cm|m)\s+(?:hoch|höhe)|niedrig|kompakt\w*\s+(?:busch|pflanz)|klein\w*\s+busch", description, re.I):
                score += 25
        if row["plant_id"] in visible_ids:
            score += 4
        scored.append((score, row))
    scored.sort(key=lambda pair: -pair[0])
    selected, size = [], 2
    for score, row in scored:
        if score <= 0:
            continue
        # Preserve whole source values, never clip a qualifying sentence.
        fields = answer_fields(row["fields"])
        compact = {"plant_id": row["plant_id"], "fields": fields}
        length = len(json.dumps(compact, ensure_ascii=False))
        if size + length > budget:
            continue
        if size + length + 2 > budget:
            continue
        selected.append(compact)
        size += length + 2
        if len(selected) == limit:
            break
    return selected
