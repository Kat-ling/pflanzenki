"""Finds variety names that speech recognition or typing got slightly wrong.

Compares spelling and sound against the catalogue without any model call. A clear
match is taken over, a doubtful one is asked about, anything else stays untouched:
a wrong name taken over silently would be worse than a question.
The thresholds are provisional, see docs/ARCHITECTURE.md.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache

from app.advisor.retrieval import STOP, base_name

CLEAR = .9
CLEAR_LEAD = .15
CLEAR_MIN_LETTERS = 6
DOUBTFUL = .75
MIN_LETTERS = 5
OPTION_RANGE = .1
MAX_OPTIONS = 3
LONGEST_SPAN = 5
MAX_COMPARED_SPANS = 60
WORD = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*")
VOWELS = "aeijouy"


@dataclass
class NameCheck:
    text: str
    changed: bool = False
    spoken: str = ""
    choices: list = field(default_factory=list)


def fold(text):
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def letters(text):
    return re.sub(r"[^a-z0-9]", "", fold(text))


def cologne_code(letter, before, after):
    if letter in VOWELS:
        return "0"
    if letter == "h":
        return ""
    if letter == "p":
        return "3" if after == "h" else "1"
    if letter in "dt":
        return "8" if after and after in "csz" else "2"
    if letter == "c":
        if not before:
            return "4" if after and after in "ahkloqrux" else "8"
        return "4" if after and after in "ahkoqux" and before not in "sz" else "8"
    if letter == "x":
        return "8" if before and before in "ckq" else "48"
    for code, group in (("1", "b"), ("3", "fvw"), ("4", "gkq"), ("5", "l"), ("6", "mn"), ("7", "r")):
        if letter in group:
            return code
    return "8"


def cologne(text):
    """Kölner Phonetik: German words that sound alike get the same digits."""
    word = re.sub(r"[^a-z]", "", fold(text))
    codes = "".join(cologne_code(c, word[i - 1:i], word[i + 1:i + 2]) for i, c in enumerate(word))
    merged = re.sub(r"(.)\1+", r"\1", codes)
    return merged[:1] + merged[1:].replace("0", "")


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


@lru_cache(maxsize=2)
def vocabulary(joined_names, catalogue_text):
    names = joined_names.split("\n")
    return ([(name, letters(name), cologne(name)) for name in names],
            {letters(name): name for name in names},
            {letters(word.group()) for word in WORD.finditer(catalogue_text)} | {letters(w) for w in STOP})


def catalogue_vocabulary(plants):
    names = "\n".join(sorted({base_name(p.name) for p in plants if p.name.strip()}))
    # Ordinary words come from the catalogue itself, so a new species brings its own terms.
    prose = " ".join(f"{p.category or ''} {p.description} {' '.join(map(str, p.raw_fields))}" for p in plants)
    return vocabulary(names, prose)


def rated_names(heard, entries):
    code = cologne(heard)
    rated = [(.6 * similarity(heard, spelled) + .4 * similarity(code, sound), name)
             for name, spelled, sound in entries
             if len(spelled) >= MIN_LETTERS and .5 <= len(heard) / len(spelled) <= 2]
    return sorted(rated, reverse=True)


def find_hits(text, entries, exact, ordinary):
    words = list(WORD.finditer(text))
    hits, compared = [], 0
    for first in range(len(words)):
        for last in range(first, min(first + LONGEST_SPAN, len(words))):
            part = words[first:last + 1]
            start, end = part[0].start(), part[-1].end()
            heard = letters(text[start:end])
            if heard in exact:
                hits.append((1.0, end - start, start, end, [(1.0, exact[heard])]))
                continue
            if (len(heard) < MIN_LETTERS or fold(part[0].group()) in STOP or fold(part[-1].group()) in STOP
                    or all(letters(w.group()) in ordinary for w in part)
                    or compared >= MAX_COMPARED_SPANS):
                continue
            compared += 1
            rated = rated_names(heard, entries)
            if rated and rated[0][0] >= DOUBTFUL:
                hits.append((rated[0][0], end - start, start, end, rated))
    return hits


def separate(hits):
    kept = []
    for hit in sorted(hits, key=lambda h: (-h[0], -h[1])):
        if all(hit[3] <= other[2] or hit[2] >= other[3] for other in kept):
            kept.append(hit)
    return sorted(kept, key=lambda h: h[2])


def is_clear(hit):
    score, _, start, end, rated = hit
    if score == 1.0:
        return True
    lead = score - rated[1][0] if len(rated) > 1 else 1
    return score >= CLEAR and lead >= CLEAR_LEAD and len(letters(rated[0][1])) >= CLEAR_MIN_LETTERS


def rebuilt(text, replacements):
    for start, end, name in sorted(replacements, reverse=True):
        text = text[:start] + name + text[end:]
    return text


def check_names(text, plants):
    entries, exact, ordinary = catalogue_vocabulary(plants)
    hits = separate(find_hits(text, entries, exact, ordinary))
    clear = [(hit[2], hit[3], hit[4][0][1]) for hit in hits if is_clear(hit)]
    corrected = rebuilt(text, clear)
    check = NameCheck(corrected, changed=fold(corrected) != fold(text))
    doubtful = next((hit for hit in hits if not is_clear(hit)), None)
    if doubtful:
        score, _, start, end, rated = doubtful
        options = [name for value, name in rated[:MAX_OPTIONS] if value >= max(DOUBTFUL, score - OPTION_RANGE)]
        check.spoken = text[start:end]
        check.choices = [dict(label=name, question=rebuilt(text, [*clear, (start, end, name)])) for name in options]
    return check


def name_question(question, check):
    labels = [choice["label"] for choice in check.choices]
    listed = ", ".join(labels[:-1]) + " oder " + labels[-1] if len(labels) > 1 else labels[0]
    return dict(question=question, intent="name_check", answer=f"Meintest du {listed}?", recommendations=[],
                unknown=[], excluded=[], criteria=[], warnings=[], name_choices=check.choices)
