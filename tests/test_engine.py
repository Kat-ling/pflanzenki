from app.advisor.engine import advise_outdoor_uncovered, resolve_feature
from app.importer.csv_importer import row_to_plant
from app.models.domain import SourceType, TruthValue


def test_description_wins_over_conflicting_structured_field():
    plant = row_to_plant({
        "Sorte": "Widerspruch", "Regenschutz": "ja",
        "Beschreibung": "Diese Sorte wächst im ungeschützten Freiland problemlos."
    })
    result = resolve_feature(plant, "outdoor_uncovered")
    assert result.verdict == TruthValue.YES
    assert result.reasons[0].source == SourceType.DESCRIPTION
    assert result.conflicts


def test_unknown_is_not_excluded():
    plant = row_to_plant({"Sorte": "Unklar", "Regenschutz": "", "Beschreibung": "Sehr süß."})
    result = advise_outdoor_uncovered([plant], "Was geht ohne Dach?")
    assert not result.excluded
    assert len(result.unknown) == 1


def test_explicit_negative_description_excludes():
    plant = row_to_plant({
        "Sorte": "Geschützt", "Regenschutz": "",
        "Beschreibung": "Regenschutz ist notwendig."
    })
    result = advise_outdoor_uncovered([plant], "Was geht ohne Dach?")
    assert len(result.excluded) == 1
