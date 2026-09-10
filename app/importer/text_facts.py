"""Conservative versioned text rules with full sentence context.

These are extraction rules, not a list of allowed customer questions. Unparsed
mentions become ambiguous evidence instead of silently endorsing a checkbox.
"""
import re

from app.models.catalogue_facts import CatalogueFact, PropertyDefinition, SourceReference

# property -> (description, relevance pattern, positive pattern, negative pattern)
BOOLEAN_RULES = {
    "site.outdoor": ("für Freiland geeignet, keine Aussage über Regenschutz",
        r"freiland|feiland", r"(?:für\s+(?:(?:das|den)\s+)?(?:frei|fei)land(?:anbau|kultur)?|anbau\s+im\s+freiland\b|im\s+freiland\s+(?:kultiviert|angebaut|gezogen|gute\s+erträge)|gedeiht[^.!?;]{0,40}\bim\s+freiland\b|freiland(?:kultur)?\s+geeignet|freilandgeeignet|freiland[- ]?(?:salat)?gurke)",
        r"nicht\s+(?:für\s+)?(?:(?:das|den)\s+)?freiland(?:anbau|kultur)?(?:\s+geeignet)?"),
    "site.uncovered": ("Anbau ausdrücklich ohne Dach/Regenschutz",
        r"regenschutz|dach|ungeschützt|regen\s+schützen",
        r"ohne\s+(?:ein\s+)?(?:dach|regenschutz)|kein(?:en)?\s+regenschutz\s+(?:nötig|erforderlich)|ungeschützt\w*\s+freiland",
        r"nicht\s+ohne\s+(?:dach|regenschutz)|(?:nur\s+)?mit\s+regenschutz|regenschutz\s+(?:ist\s+)?(?:erforderlich|notwendig)|vor\s+regen\s+schützen"),
    "site.container": ("für Topf oder Kübel/Balkonkultur geeignet",
        r"topf|töpf|kübel|balkon|ampel", r"(?:für|in)\s+(?:den\s+|die\s+)?(?:topf|töpfe|kübel|balkon|kästen\s+und\s+töpfe)|topfkultur|kübelkultur|balkongeeignet",
        r"nicht\s+(?:für\s+)?(?:den\s+)?(?:topf|kübel|balkon)"),
    "taste.sweet": ("süßer Geschmack", r"süß|süss",
        r"\bsüß(?:e[nrms]?|lich\w*|fruchtig\w*|esten)?\b|\bsüss\w*",
        r"\bnicht\s+(?:mehr\s+)?süß\w*|\bnicht\s+(?:mehr\s+)?süss\w*"),
    "taste.spicy": ("scharfer Geschmack (nicht scharf: eq false)", r"scharf|schärfe|feurig|mild",
        r"\bscharf\w*|\bfeurig\w*|\b(?:leichte[rn]?|mittlere[rn]?|starke[rn]?)\s+schärfe|\bschärfe\s+[1-9]\d*\b",
        r"\bnicht\s+scharf\w*|\bmild\w*|\b(?:ohne|keine)\s+schärfe|\bschärfe\s+0\b"),
    "fruit.large": ("ausdrücklich große Früchte, keine abgeleitete Grammgrenze",
        r"(?:klein|groß|normalgroß)\w*[^.!?;]{0,45}(?:frücht|tomaten)|früchte\s+(?:sind\s+)?(?:groß|klein)", r"\bgroß(?:e[nrms]?)?\b[^.!?;]{0,45}\b(?:früchte[n]?|tomaten)\b|früchte\s+(?:sind\s+)?groß\b",
        r"\b(?:klein(?:e[nrms]?)?|normalgroß\w*)\b[^.!?;]{0,35}\bfrüchte[n]?\b"),
    "fruit.small": ("ausdrücklich kleine Früchte, kein Rückschluss aus Sortentyp",
        r"(?:klein|groß|normalgroß)\w*[^.!?;]{0,45}(?:frücht|tomaten)|früchte\s+(?:sind\s+)?(?:groß|klein)", r"\bklein(?:e[nrms]?)?\b[^.!?;]{0,35}\bfrüchte[n]?\b|früchte\s+(?:sind\s+)?klein\b",
        r"\bgroß(?:e[nrms]?)?\b[^.!?;]{0,45}\bfrüchte[n]?\b"),
    "care.no_pruning": ("muss nicht ausgegeizt werden", r"ausge(?:ge)?iz",
        r"\b(?:nicht|kein\w*)\s+ausge(?:ge)?iz\w*|ausgeizen\s+(?:ist\s+)?nicht\s+(?:nötig|erforderlich)",
        r"\b(?:muss|muß|sollte)\s+(?:unbedingt\s+)?ausgegeizt\s+werden|ausgeizen\s+(?:ist\s+)?(?:nötig|erforderlich)"),
    "use.pickling": ("zum Einlegen geeignet", r"einleg|eingeleg",
        r"(?:zum|für\s+das)\s+einlegen|einlegegurke|\beingelegt\s+werden", r"nicht\s+zum\s+einlegen|nicht\s+eingelegt\s+werden"),
    "site.greenhouse_or_roof": ("für Gewächshaus oder Anbau unter Dach",
        r"gewächshaus|folientunnel|dach", r"(?:für|im)\s+(?:das\s+)?(?:gewächshaus|folientunnel)|unter\s+dach",
        r"nicht\s+für\s+(?:das\s+)?gewächshaus"),
    "site.protected": ("geschützter Standort",
        r"geschützt|regenschutz", r"geschützt\w*\s+standort|regenschutz\s+(?:erforderlich|notwendig)",
        r"nicht\s+für\s+(?:einen\s+)?geschützten\s+standort"),
    "site.warm": ("warmer Standort",
        r"warm|wärme", r"warm\w*\s+standort|wärmebedürftig", r"nicht\s+für\s+(?:einen\s+)?warmen\s+standort"),
    "care.drought_tolerant": ("trockenheitsverträglich",
        r"trocken|wasser", r"\btrockenheitsverträglich\w*|\btrockenheitstolerant\w*",
        r"nicht\s+trockenheitsverträglich\w*|nicht\s+trockenheitstolerant\w*"),
    "plant.climbing": ("rankend",
        r"rank|kletter", r"\brankend\w*|\bkletternd\w*", r"nicht\s+rankend\w*|nicht\s+kletternd\w*"),
    "plant.overwinterable": ("überwinterbar",
        r"überwinter|mehrjähr", r"\büberwinterbar\w*", r"nicht\s+überwinterbar\w*"),
    "plant.winter_hardy": ("winterhart im Freien",
        r"winterhart|frost", r"\bwinterhart\w*", r"nicht\s+winterhart\w*"),
    "plant.robust_or_resistant": ("allgemeine Robustheit, keine bestimmte Resistenz",
        r"robust|resisten|toleran", r"\brobust\w*|\bresistent\w*", r"nicht\s+robust\w*|nicht\s+resistent\w*"),
    "fruit.thin_skin": ("ausdrücklich dünne Fruchtschale",
        r"schale|schalig", r"\bdünn\w*\s+schale|\bdünnschalig\w*", r"\bdick\w*\s+schale|\bdickschalig\w*|nicht\s+dünnschalig\w*"),
}

TEXT_REGISTRY = [PropertyDefinition(property_id=key, field="Beschreibung", value_type="boolean",
                                    semantics=definition[0])
                 for key, definition in BOOLEAN_RULES.items()]
TEXT_REGISTRY += [PropertyDefinition(property_id="fruit.mass", field="Beschreibung", value_type="number",
                                     semantics="fruit_mass", unit="g", minimum=0.0)]

# If such a qualifier occurs anywhere in a relevant sentence, avoid extracting
# an unconditional fact. Negative rules handle their explicit negations below.
QUALIFIER = re.compile(r"\b(?:bedingt|teilweise|eventuell|vielleicht|meist\w*|manchmal|durchschnitt\w*|typisch\w*|normalerweise|oft|eher|relativ|kaum|weniger|mäßig|sofern|wenn|falls|solange|vorausgesetzt|außer|aber|jedoch|nur|nicht|kein\w*|nie|niemals|genug|ungeeignet)\b", re.I)
NUMBER = r"\d+(?:[,.]\d+)?"


def sentences(text):
    # Do not split decimal dots. Retain original offsets and punctuation.
    for match in re.finditer(r"(?:\d\.\d|[^.!?\n]|\.(?=\d))*[.!?\n]?", text):
        if match.group().strip():
            yield match


def clauses(text):
    """Split explicit topic changes, not comma-separated adjective lists.

Offsets still refer to the original field. Complete original fields are shown.
"""
    boundary = re.compile(r"[,;]\s*(?=(?:sie\b|die\s+pflanze|wird\b|muß\b|muss\b|regenschutz\b|ertragreich\b|anbau\b))|\bsondern\s+", re.I)
    for sentence in sentences(text):
        if re.search(r"\b(?:wenn|sofern|falls|solange|vorausgesetzt|außer)\b", sentence.group(), re.I):
            yield sentence.start(), sentence.end()
            continue
        start = sentence.start()
        for delimiter in boundary.finditer(sentence.group()):
            end = sentence.start() + delimiter.start()
            if text[start:end].strip():
                yield start, end
            start = sentence.start() + delimiter.end()
        if text[start:sentence.end()].strip():
            yield start, sentence.end()


def extract_description(plant_id, fields):
    from app.importer.catalogue_facts import digest
    facts = []
    # Aliases are original field names, never synthesized source names.
    for field in ("Beschreibung", "Rohbeschreibung", "Description", "Text"):
        text = fields.get(field, "")
        for start, end in clauses(text):
            sentence = text[start:end]
            source = SourceReference(field=field, field_hash=digest(text), start=start,
                                     end=end, quote=sentence)

            def add(key, value, status, unit=None, semantics="boolean", value_max=None):
                facts.append(CatalogueFact(
                    fact_id=digest([plant_id, key, source.model_dump(), value, value_max, status]),
                    plant_id=plant_id, property_id=key, value=value, value_max=value_max,
                    unit=unit, semantics=semantics, source=source, origin="description_rule",
                    semantic_status=status,
                ))

            for key, (_, relevant, positive, negative) in BOOLEAN_RULES.items():
                if not re.search(relevant, sentence, re.I):
                    continue
                negative_matches = list(re.finditer(negative, sentence, re.I))
                # A negative phrase must not also contribute its positive substring.
                remaining = sentence
                for neg in reversed(negative_matches):
                    remaining = remaining[:neg.start()] + " " * len(neg.group()) + remaining[neg.end():]
                pos = bool(re.search(positive, remaining, re.I))
                neg = bool(negative_matches)
                qualifier_context = re.sub(positive, " ", remaining, flags=re.I)
                if key == "site.outdoor":
                    if re.search(r"geschützt|folienbedeckung|versuch|würde", sentence, re.I):
                        qualifier_context += " bedingt"
                    qualifier_context = re.sub(r"\bnur\s+(?=für\b)", "", qualifier_context, flags=re.I)
                    # The positive phrase was removed above; only a leading
                    # exclusivity word may remain: "Nur für das Freiland geeignet".
                    if re.match(r"\s*nur\s+für\b", sentence, re.I):
                        qualifier_context = re.sub(r"^\s*nur\b", "", qualifier_context, flags=re.I)
                if key == "taste.sweet" and neg:
                    qualifier_context = re.sub(r"\baber\b", "", qualifier_context, flags=re.I)
                if key == "use.pickling":
                    qualifier_context = re.sub(r"\brelativ\s+robust\w*", "", qualifier_context, flags=re.I)
                numeric_size = key in {"fruit.large", "fruit.small"} and re.search(r"\d\s*(?:cm|mm)\s+groß", sentence, re.I)
                if (pos and neg) or numeric_size or QUALIFIER.search(qualifier_context) or not (pos or neg):
                    add(key, "unparsed or qualified", "ambiguous")
                else:
                    add(key, pos, "rule_checked")

            colors = list(re.finditer(r"\b(rot|gelb|orange|grün|violett|schwarz|weiß|rosa)(?:e[nrms]?)?\b", sentence, re.I))
            if colors and re.search(r"frücht|frucht|tomaten|blätt|blüte|stiel|stängel", sentence, re.I):
                if QUALIFIER.search(sentence) or re.search(r"blätt|blüte|stiel|stängel|unreif|halbreif", sentence, re.I):
                    add("fruit.color", "unparsed or qualified", "ambiguous", semantics="text_membership")
                else:
                    for color in colors:
                        add("fruit.color", color[1].casefold(), "rule_checked", semantics="text_membership")

            # Numeric phrases: explicit object and unit only. Approximate/conditional
            # statements are retained but are not certified numeric bounds.
            for key, relevance, pattern, expected_unit in [
                ("plant.height", r"hoch|höhe|wuchs", rf"(?:bis\s+(?:zu\s+)?)?({NUMBER})(?:\s*[-–]\s*({NUMBER}))?\s*(cm|m)\s+hoch", "cm"),
                ("fruit.mass", rf"gewicht|(?:frucht|früchte)[^.!?]*{NUMBER}\s*(?:kg|g)\b", rf"(?:bis\s+(?:zu\s+)?)?({NUMBER})(?:\s*[-–]\s*({NUMBER}))?\s*(kg|g)\b", "g"),
            ]:
                if not re.search(relevance, sentence, re.I):
                    continue
                found = list(re.finditer(pattern, sentence, re.I))
                wrong_object = (key == "fruit.mass" and not re.search(r"frucht|früchte", sentence, re.I)
                                or key == "plant.height" and re.search(r"frucht|früchte", sentence, re.I)
                                and not re.search(r"pflanze|wuchs|sorte|wird", sentence, re.I))
                if len(found) != 1 or wrong_object or QUALIFIER.search(sentence) or re.search(r"\b(?:ca|etwa|ungefähr|mindestens|maximal|höchstens|über|unter|ab|mehr)\b", sentence, re.I):
                    add(key, "unparsed or qualified", "ambiguous", unit=expected_unit)
                    continue
                for number in found:
                    factor = 100 if number[3].casefold() == "m" else 1000 if number[3].casefold() == "kg" else 1
                    low = float(number[1].replace(",", ".")) * factor
                    high = float(number[2].replace(",", ".")) * factor if number[2] else None
                    semantics = "range" if high is not None else "upper_bound" if re.search(r"\bbis\b", number[0], re.I) else "exact"
                    if low <= 0 or (high is not None and high < low):
                        add(key, "invalid range", "ambiguous", unit=expected_unit)
                    else:
                        add(key, low, "rule_checked", expected_unit, semantics, high)
            # Calendar statements need season/range parsing before they can
            # override structured harvest months. Retain them as blockers.
            if re.search(r"ernte|ertrag|reif", sentence, re.I):
                for key in ("harvest.start_month", "harvest.end_month"):
                    add(key, "unparsed harvest context", "ambiguous", semantics="calendar_month")
    return facts
