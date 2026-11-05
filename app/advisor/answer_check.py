"""Checks a model answer against the local facts before anything is shown.

A contradiction vetoes. A missing fact usually does not: the rules know less
than the free description texts, which the model has read. Growing sites are
the exception, because the model infers them from plant height or fruit size
(seen in the live test), while the catalogue names them explicitly when known.
See docs/ARCHITECTURE.md.
"""
import re

from app.advisor.local_selection import (
    REASONS, asks_only_existence, local_checks, validate_expression,
)
from app.ai.dialogue_models import Expression

IDENTITY_FIELDS = {"Name", "Name_für_Katalog", "Kategorie"}
TECHNICAL_NOTE = re.compile(r"\s*\([^()]*\b[a-z]+\.[a-z_]+\b[^()]*\)")
SITE_WORDS = {
    "site.container": re.compile(r"balkon|\btopf|\btöpf|kübel|\bkasten", re.I),
    "site.greenhouse_or_roof": re.compile(r"gewächshaus|unter\s+dach", re.I),
    "site.uncovered": re.compile(r"ohne\s+(?:regenschutz|dach)", re.I),
    "site.outdoor": re.compile(r"freiland", re.I),
}
REFUSAL = re.compile(r"\b(?:nicht|nie|kein\w*|ohne)\b", re.I)


def is_open(node):
    return node.op == "unresolved" or (node.op == "any" and any(c.op == "unresolved" for c in node.children))


def pin_site(condition):
    """Holds an unmapped site condition to its fact (seen twice in live tests)."""
    if not is_open(condition.expression):
        return condition
    named = [key for key, words in SITE_WORDS.items() if words.search(condition.text)]
    if len(named) != 1 or REFUSAL.search(SITE_WORDS[named[0]].sub("", condition.text)):
        return condition
    return condition.model_copy(update={"expression": Expression(
        op="predicate", text=condition.text, property_id=named[0], comparator="eq",
        value=True, unit=None, children=[])})


def checkable(conditions, registry):
    """Returns the required conditions to check and how many could not be checked."""
    usable, skipped = [], 0
    for condition in conditions:
        if condition.kind != "condition" or condition.importance != "required":
            continue
        condition = pin_site(condition)
        try:
            validate_expression(condition.expression, registry)
        except ValueError:
            skipped += 1
            continue
        if asks_only_existence(condition.expression):
            skipped += 1
            continue
        usable.append(condition)
    return usable, skipped


def contradictions(conditions, prepared, registry):
    vetoes = []
    for check in local_checks(prepared, conditions, registry):
        if check["status"] == "no":
            evidence = "; ".join(f'{s["field"]}: {s["text"]}' for s in check["sources"])
            vetoes.append(dict(criterion=readable(check["criterion"]), importance=check["importance"],
                               kind=check["kind"], status="no", sources=check["sources"],
                               reason=f"Der Katalog widerspricht: {evidence}"))
    return vetoes


def lacks_site_evidence(node, result):
    if node.op == "predicate":
        return (node.property_id.startswith("site.") and result["status"] == "unknown"
                and result["reason"] == REASONS["evidence_missing"])
    if node.op == "all":
        return any(map(lacks_site_evidence, node.children, result["children"]))
    return False


def unproven_sites(conditions, prepared, registry):
    return [check["criterion"] for condition, check in zip(conditions, local_checks(prepared, conditions, registry))
            if lacks_site_evidence(condition.expression, check["expression_result"])]


def readable(text):
    return TECHNICAL_NOTE.sub("", text).strip()


def identity_only(sources):
    return all(source["field"] in IDENTITY_FIELDS for source in sources)


def names_any(text, names):
    folded = text.casefold()
    return any(re.search(rf"(?<!\w){re.escape(name.casefold())}(?!\w)", folded) for name in names)
