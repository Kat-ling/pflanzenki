"""Bounded local candidate search, never a botanical truth filter."""
import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

STOP = set("""ich du mir mich wir uns welche welchen welcher welches gibt ist sind haben hat suche
bitte und oder mit ohne der die das ein eine einer einen für fürs von in im auf den dem es nun doch
lieber als nach was wie wann wo kann könnte soll sollte passt noch mehr nicht sehr auch etwas gern
gerne möchte hätte brauche bräuchte also halt mal äh ähm hallo weitere weiteren andere anderen
""".split())
SYNONYMS = Path(__file__).resolve().parents[2] / "data" / "search_synonyms.json"
YES_VALUES = {"yes", "true", "ja", "checked"}
MORE_RESULTS = re.compile(r"\b(?:weitere\w*|noch mehr|noch andere|andere\w*|sonst noch)\b", re.I)

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


def base_name(name):
    """Notes in brackets belong to the catalogue, not to the variety's name."""
    return re.sub(r"\s*\([^()]*\)", "", name).strip() or name.strip()


@lru_cache(maxsize=1)
def synonym_groups():
    if not SYNONYMS.exists():
        return ()
    return tuple(tuple(group) for group in json.loads(SYNONYMS.read_text(encoding="utf-8"))["groups"])


def compound_heads(categories):
    """German compounds end in their head: Salattomate is a tomato, not a salad."""
    stems = {(c.casefold().rstrip("e") if len(c) > 4 else c.casefold()): c.casefold()[:5]
             for c in categories if c}
    if not stems:
        return None
    alternatives = "|".join(sorted(map(re.escape, stems), key=len, reverse=True))
    return re.compile("(" + alternatives + r")\w{0,3}$"), stems


def terms(text, heads=None):
    words = re.findall(r"[a-zäöüß0-9]+", text.casefold())
    result = {w[:5] for w in words if len(w) > 2 and w not in STOP}
    for word in words:
        match = heads[0].search(word) if heads else None
        if match:
            result.add(heads[1][match.group(1)])
    # Retrieval expansion only: these words do not certify matching properties.
    for group in synonym_groups():
        if any(w.startswith(member) for w in words for member in group):
            result.update(member[:5] for member in group)
    return result


def compound_modifiers(text, heads):
    """In Salattomate, Salat only qualifies the head and asks for no salad."""
    if not heads:
        return set()
    words = re.findall(r"[a-zäöüß0-9]+", text.casefold())
    return {w[:5] for w in words if (match := heads[0].search(w)) and match.start() > 0}


def searchable_text(fields):
    """A ticked checkbox says Yes; only its field name carries the meaning."""
    ticked = [key for key, value in fields.items() if value.strip().casefold() in YES_VALUES]
    return " ".join([*fields.values(), *ticked])


def records(plants):
    return [{"plant_id": p.id, "fields": {"Name": p.name, "Kategorie": p.category or "",
             "Beschreibung": p.description,
             **{str(k): str(v) for k, v in p.raw_fields.items()
                if v is not None and str(v).strip() and k not in {"Name", "Kategorie", "Beschreibung", "Bild"}}}}
            for p in plants]


@lru_cache(maxsize=2)
def index(serialized):
    rows = json.loads(serialized)
    heads = compound_heads({row["fields"]["Kategorie"] for row in rows})
    documents = [terms(searchable_text(row["fields"]), heads) for row in rows]
    frequencies = Counter(t for document in documents for t in document)
    return rows, documents, frequencies, heads


def retrieve(plants, question, history, visible=(), limit=24, budget=28000):
    rows, documents, frequencies, heads = index(json.dumps(records(plants), ensure_ascii=False))
    current = terms(question, heads)
    questions = [m.content for m in history if m.role == "user"]
    prior = terms(" ".join(questions), heads)
    latest = terms(questions[-1], heads) if questions else set()
    categories = {term for row in rows for term in terms(row["fields"]["Kategorie"])}
    # A follow-up continues the most recent topic, not everything said so far.
    topic = set()
    if not current & categories:
        topic_question = next((q for q in reversed(questions) if terms(q, heads) & categories), None)
        if topic_question:
            prior = terms(topic_question, heads)
            topic = prior & categories
    visible_ids = {p["plant_id"] for p in visible}
    asked_categories = current - compound_modifiers(question, heads)
    wants_more = bool(MORE_RESULTS.search(question))
    scored = []
    height_query = bool(re.search(r"niedrig|wuchshöhe|klein\w*\s+(?:pflanz|wuchs)|kompakt", question, re.I))
    if not height_query and history:
        height_query = bool(re.search(r"niedrig|wuchshöhe", history[-1].content, re.I))
    normalized_question = " ".join(re.findall(r"\w+", question.casefold()))
    for row, document in zip(rows, documents):
        if wants_more and row["plant_id"] in visible_ids:
            continue
        score = sum((3 if t in current else 1.5 if t in latest else .3) * math.log(1 + len(rows) / frequencies[t])
                    for t in document & (current | prior))
        name = base_name(row["fields"]["Name"]).casefold()
        category = terms(row["fields"]["Kategorie"])
        if category & asked_categories:
            score += 20
        elif category & topic:
            score += 25
        if f' {" ".join(re.findall(r"\w+", name))} ' in f" {normalized_question} ":
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
