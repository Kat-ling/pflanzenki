"""Reproduce the offline before/after report; never invokes a model.

Run from the project root: python -B tests/run_catalogue_acceptance.py
The baseline was captured before editing the extraction rules and is immutable.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from catalogue_acceptance_cases import CASES
from app.advisor.local_selection import evaluate
from app.ai.dialogue_models import Expression
from app.importer.catalogue_facts import build_bundle
from app.repository import load_plants


def main():
    plants = load_plants()
    bundle = build_bundle(plants)
    by_name = {p.name: (p, f) for p, f in zip(plants, bundle.plants)}
    registry = {d.property_id: d for d in bundle.registry}
    baseline = json.loads((ROOT / "docs/CATALOGUE_ACCEPTANCE_BASELINE.json").read_text(encoding="utf-8"))
    if baseline["catalogue_revision"] != bundle.catalogue_revision:
        raise ValueError("Katalog geändert: Erwartungen und Baseline müssen neu fachlich geprüft werden.")
    expressions = {case[0]: Expression.model_validate(case[2]) for case in CASES}
    for row in baseline["results"]:
        plant, prepared = by_name[row["plant"]]
        if row["quote"] not in plant.description:
            raise ValueError("Originalquelle geändert: " + plant.name)
        row["after"] = evaluate(expressions[row["case"]], prepared, registry)["status"]
    rows = baseline["results"]
    baseline["extractor_version"] = bundle.extractor_version
    (ROOT / "docs/CATALOGUE_ACCEPTANCE_RESULTS.json").write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    before = sum(r["before"] == r["expected"] for r in rows)
    after = sum(r["after"] == r["expected"] for r in rows)
    lines = [
        "# Fachlicher Offline-Abgleich", "", "Stand: 10. September 2026.", "",
        f"20 Kundenfragen, {len(rows)} manuell anhand der Originaltexte festgelegte Frage-Pflanzen-Paare.",
        f"Übereinstimmung vor den Korrekturen: **{before}/{len(rows)}**; danach: **{after}/{len(rows)}**.", "",
        "Dies ist eine gezielt ausgewählte Entwicklungsstichprobe, keine vollständige Trefferliste",
        "für alle 249 Pflanzen und keine unabhängige Qualitätsquote. Die erwarteten Bewertungen",
        "wurden vor den Regeländerungen aus den Katalogtexten festgelegt; dieselben Fälle wurden",
        "anschließend zur Fehlerkorrektur verwendet. Die Übersetzung der Fragen in Ausdrücke ist",
        "hier manuell vorgegeben. Die Qualität der Modellinterpretation wird damit nicht getestet.", "",
        "Der Ausgangsstand hatte 20 übersehene Belege/Gegenbelege (UNKNOWN statt YES/NO) und",
        "einen falschen positiven Treffer: weiße Blüten wurden als weiße Früchte gewertet.", "",
        "## Korrekturen", "",
        "- Themenwechsel innerhalb langer Sätze trennen; Adjektivlisten und bedingte Sätze zusammenlassen.",
        "- Eigenständige Pflege-Negationen blockieren keine Geschmacksangaben mehr.",
        "- Ohne/keine Schärfe, nicht mehr süß, leichte/mittlere Schärfe korrekt zuordnen.",
        "- Topf-Plurale, Freiland-Anbauformulierungen und eingelegt werden erkennen.",
        "- Neue Eigenschaft dünne Fruchtschale mit Originalquellen ergänzen.",
        "- Blüten-/Blattfarben nicht als Fruchtfarbe übernehmen; warme Überwinterung nicht mit Winterhärte vermischen.", "",
        "Außerhalb der 44 Paare wurden veränderte boolesche Entscheidungen im gesamten Katalog",
        "durchgesehen. Dabei wurde eine zwischenzeitlich zu breite Freiland-Regel korrigiert:",
        "Zebrino (Versuch noch offen), Little Brinjal (geschützt im Freiland) und Blaukönigin",
        "(zeitweise Folienbedeckung) sind keine Belege für uneingeschränkten Freilandanbau.",
        "Diese drei Originalfälle und 18 synthetische Negations-/Bedingungsfälle haben eigene Regressionstests.", "",
        "## Einzelbewertungen", "", "YES = belegt, NO = widerlegt, UNKNOWN = Woas I ned.", "",
        "| Fall | Frage | Sorte | Erwartet | Vorher | Nachher | Begründung |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(r[k]).replace("|", "\\|") for k in
                                      ["case", "question", "plant", "expected", "before", "after", "reason"]) + " |")
    lines += ["", "## Vollständige Originalbeschreibungen der Stichprobe", "",
              "Quelle: data/normalized/plants.json; keine ergänzten Pflanzeninformationen.",
              "Katalogrevision: `" + bundle.catalogue_revision + "`.", ""]
    for name in dict.fromkeys(r["plant"] for r in rows):
        plant = by_name[name][0]
        lines += ["### " + name, "", plant.description, ""]
        for field in ["Fruchtfarbe", "Schärfegrad MAX", "Wuchshöhe_bis_cm"]:
            value = plant.raw_fields.get(field)
            if value is not None and str(value).strip():
                lines += [f"- Originalfeld {field}: {value}"]
        lines.append("")
    lines += ["## Grenzen und Reproduktion", "",
              "Weiter offen sind beliebige neue Eigenschaften und Formulierungen, bedingte bzw.",
              "ungefähre Zahlenangaben und differenzierte Erntezeiträume. Diese Fälle dürfen weiter",
              "UNKNOWN bleiben. Keine unbelegten Empfehlungen und kein automatischer Modell-Fallback.", "",
              "`python -B tests/run_catalogue_acceptance.py` erzeugt diesen Bericht neu.",
              "`python -B -m pytest -p no:cacheprovider` prüft die Regressionen.",
              "Es wurden keine kostenpflichtigen PflanzenKI-Aufrufe durchgeführt.", ""]
    (ROOT / "docs/CATALOGUE_ACCEPTANCE_REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Offline-Abgleich: vorher {before}/{len(rows)}, jetzt {after}/{len(rows)}")


if __name__ == "__main__":
    main()
