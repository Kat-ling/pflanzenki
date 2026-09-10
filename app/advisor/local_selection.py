"""Pure local three-valued evaluation. No model/network dependency."""
from functools import lru_cache
import json
import math
from pathlib import Path

from app.ai.dialogue_models import Expression
from app.importer.catalogue_facts import (
    DEFAULT_REGISTRY, SCHEMA_VERSION, EXTRACTOR_VERSION, build_bundle, digest, source_is_valid,
)
from app.models.catalogue_facts import FactBundle

SIDECAR = Path(__file__).resolve().parents[2] / "data/normalized/catalogue_facts.json"
REASONS = {
    "evidence_missing": "Woas I ned. Für dieses Kriterium fehlt ein eindeutiger Beleg.",
    "mapping_unresolved": "Woas I ned. Dieses Kriterium lässt sich noch nicht sicher lokal zuordnen.",
    "qualified": "Woas I ned. Die Beschreibung enthält Einschränkungen oder noch nicht eindeutig auswertbare Angaben.",
    "conflict": "Woas I ned. Die Quellen widersprechen sich.",
    "invalid_source": "Woas I ned. Die gespeicherte Quelle stimmt nicht mit dem Original überein.",
}


def combine(op, values):
    if op == "not":
        return {"yes": "no", "no": "yes", "unknown": "unknown"}[values[0]]
    if op == "all":
        return "no" if "no" in values else "unknown" if "unknown" in values else "yes"
    return "yes" if "yes" in values else "unknown" if "unknown" in values else "no"


def validate_expression(node, registry):
    for child in node.children:
        validate_expression(child, registry)
    if node.op != "predicate":
        return
    definition = registry.get(node.property_id)
    if definition is None:
        return  # An unknown property never disappears; it evaluates to UNKNOWN.
    if node.comparator == "exists":
        if node.unit is not None:
            raise ValueError("Informationsabfrage darf keine Vergleichseinheit enthalten.")
        return
    kind = definition.value_type
    if kind == "boolean" and (type(node.value) is not bool or node.comparator != "eq" or node.unit is not None):
        raise ValueError("Wahrheitswerte erfordern eq und true/false ohne Einheit.")
    if kind == "text" and (not isinstance(node.value, str) or node.comparator != "eq" or node.unit is not None):
        raise ValueError("Texte erfordern einen Textvergleich ohne Einheit.")
    if kind == "number":
        if type(node.value) not in {int, float} or not math.isfinite(node.value):
            raise ValueError("Zahlenvergleich benötigt eine endliche Zahl.")
        units = {"cm": {"cm", "m"}, "g": {"g", "kg"}}
        if node.unit not in units.get(definition.unit, {definition.unit}):
            raise ValueError("Einheit und Eigenschaft passen nicht zusammen.")


def numeric_status(fact, node):
    factor = {("m", "cm"): 100, ("kg", "g"): 1000}.get((node.unit, fact.unit), 1)
    target = node.value * factor
    low = float(fact.value)
    high = fact.value_max if fact.semantics == "range" else low
    if fact.semantics == "upper_bound":
        low = 0.0  # Physical quantities in the current registry are nonnegative.
    if high is None or low > high:
        return "unknown"
    op = node.comparator
    if op == "lte":
        return "yes" if high <= target else "no" if low > target else "unknown"
    if op == "lt":
        return "yes" if high < target else "no" if low >= target else "unknown"
    if op == "gte":
        return "yes" if low >= target else "no" if high < target else "unknown"
    if op == "gt":
        return "yes" if low > target else "no" if high <= target else "unknown"
    return "yes" if low == high == target else "no" if target < low or target > high else "unknown"


def evaluate(node, prepared, registry):
    if node.children:
        children = [evaluate(c, prepared, registry) for c in node.children]
        status = combine(node.op, [c["status"] for c in children])
        sources = []
        for c in children:
            for source in c["sources"]:
                if source not in sources:
                    sources.append(source)
        return dict(text=node.text, status=status, sources=sources, children=children,
                    reason="" if status != "unknown" else REASONS["evidence_missing"])
    result = dict(text=node.text, status="unknown", sources=[], children=[], reason="")
    if node.op == "unresolved" or node.property_id not in registry:
        return {**result, "reason": REASONS["mapping_unresolved"]}
    facts = [f for f in prepared.facts if f.property_id == node.property_id]
    # A numerical heat statement also answers spicy=true/false, but positive
    # maximum heat alone cannot prove that every fruit is hot.
    if node.property_id == "taste.spicy" and not facts:
        facts = [f for f in prepared.facts if f.property_id == "fruit.heat" and f.value == 0]
    descriptions = [f for f in facts if f.origin == "description_rule"]
    selected = descriptions or facts
    if not selected:
        return {**result, "reason": REASONS["evidence_missing"]}
    if any(not source_is_valid(f.source, prepared.source_fields) for f in selected):
        return {**result, "reason": REASONS["invalid_source"]}
    sources = []
    for f in selected:
        source = {"field": f.source.field, "text": prepared.source_fields[f.source.field]}
        if source not in sources:
            sources.append(source)
    result["sources"] = sources
    if any(f.semantic_status == "ambiguous" for f in selected):
        return {**result, "reason": REASONS["qualified"]}
    if len({f.value for f in selected if type(f.value) is bool}) > 1:
        return {**result, "reason": REASONS["conflict"]}
    if len({f.value for f in selected if type(f.value) is float and f.semantics == "exact"}) > 1:
        return {**result, "reason": REASONS["conflict"]}
    statuses = []
    for fact in selected:
        if node.comparator == "exists":
            statuses.append("yes")
        elif fact.property_id == "fruit.heat" and node.property_id == "taste.spicy":
            statuses.append("yes" if node.value is False else "no")
        elif type(fact.value) is bool:
            statuses.append("yes" if fact.value == node.value else "no")
        elif type(fact.value) in {float, int}:
            statuses.append(numeric_status(fact, node))
        else:
            # A different color is not an explicit negation: fruit can be multicolored.
            statuses.append("yes" if str(fact.value).strip().casefold() == str(node.value).strip().casefold() else "unknown")
    if "yes" in statuses and "no" in statuses:
        return {**result, "reason": REASONS["conflict"]}
    status = "yes" if "yes" in statuses else "no" if "no" in statuses else "unknown"
    return {**result, "status": status, "reason": "" if status != "unknown" else REASONS["evidence_missing"]}


@lru_cache(maxsize=2)
def _prepared_catalogue(serialized, sidecar_bytes):
    from app.models.domain import Plant
    plants = [Plant.model_validate(p) for p in json.loads(serialized)]
    expected_revision = digest([p.model_dump(mode="json") for p in plants])
    if sidecar_bytes:
        try:
            bundle = FactBundle.model_validate_json(sidecar_bytes)
            if (bundle.catalogue_revision == expected_revision
                    and bundle.schema_version == SCHEMA_VERSION
                    and bundle.extractor_version == EXTRACTOR_VERSION
                    and bundle.registry_hash == digest([d.model_dump() for d in DEFAULT_REGISTRY])
                    and bundle.registry == DEFAULT_REGISTRY
                    and [p.plant_id for p in bundle.plants] == [p.id for p in plants]
                    and all(p.content_hash == digest(original.model_dump(mode="json"))
                            and p.source_fields == {str(k): str(v) for k, v in original.raw_fields.items()
                                                   if v is not None and str(v).strip()}
                            and all(source_is_valid(f.source, p.source_fields) for f in p.facts)
                            for p, original in zip(bundle.plants, plants))):
                return bundle
        except (ValueError, TypeError):
            pass
    # Missing/stale sidecars are rebuilt locally, never via the model. No request-time writes.
    return build_bundle(plants)


def prepare_catalogue(plants):
    serialized = json.dumps([p.model_dump(mode="json") for p in plants], ensure_ascii=False, sort_keys=True)
    try:
        data = SIDECAR.read_bytes()
    except OSError:
        data = b""
    return _prepared_catalogue(serialized, data)


def local_checks(prepared, criteria, registry):
    checks = []
    for criterion in criteria:
        result = evaluate(criterion.expression, prepared, registry)
        checks.append(dict(criterion=criterion.text, importance=criterion.importance,
                           kind=criterion.kind, **{k: result[k] for k in ("status", "sources", "reason")},
                           expression_result=result))
    return checks
