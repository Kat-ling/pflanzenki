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


def test_filter_tags_create_general_feature_evidence():
    plant = row_to_plant({
        "Name": "Gurke A",
        "Kategorie": "Gurke",
        "Beschreibung": "Eine gute Sorte.",
        "Filter_Tags": "Gurke; Balkon; robust; früh",
    })

    features = {item.feature for item in plant.evidence}
    assert {"balcony", "robust", "early"} <= features


def test_unchecked_positive_field_remains_unknown():
    plant = row_to_plant({
        "Name": "Gurke A",
        "Freiland": "No",
        "Balkon / Topf": "No",
        "Robust/Resistent": "No",
    })

    assert not plant.evidence


def test_positive_checkbox_and_color_are_imported():
    plant = row_to_plant({
        "Name": "Paprika A",
        "Balkon / Topf": "Yes",
        "Fruchtfarbe": "gelb",
    })

    features = {item.feature for item in plant.evidence}
    assert {"balcony", "yellow"} <= features


def test_multiple_image_names_are_preserved():
    plant = row_to_plant({
        "Name": "Johannisbeertomate",
        "Bild": "rot.jpeg, orange.jpg",
    })

    assert plant.image_filenames == ["rot.jpeg", "orange.jpg"]


def test_pear_shape_is_read_from_description():
    plant = row_to_plant({
        "Name": "Birnentomate",
        "Beschreibung": "Kleine, birnenförmige Früchte.",
    })

    assert any(
        item.feature == "pear_shaped"
        for item in plant.evidence
    )
