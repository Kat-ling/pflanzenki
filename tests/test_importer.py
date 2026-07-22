from app.importer.csv_importer import row_to_plant
from app.models.domain import SourceType, TruthValue


def test_empty_checkbox_is_unknown_not_negative():
    plant = row_to_plant({"Sorte": "A", "Regenschutz": "", "Beschreibung": "Leckere Sorte."})
    assert not [e for e in plant.evidence if e.feature == "outdoor_uncovered"]


def test_description_is_always_read():
    plant = row_to_plant({
        "Sorte": "A", "Regenschutz": "",
        "Beschreibung": "Kann problemlos ohne Regenschutz angebaut werden."
    })
    assert any(e.value == TruthValue.YES and e.source == SourceType.DESCRIPTION for e in plant.evidence)
