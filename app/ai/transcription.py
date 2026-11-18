"""Speech to text. The audio is passed on and never stored, the text never logged."""
import json
import logging
import os
import re
from time import monotonic

from dotenv import load_dotenv
from openai import OpenAI

from app.advisor.retrieval import base_name
from app.ai.query_interpreter import QueryInterpreterError

logger = logging.getLogger("uvicorn.error.pflanzenki.requests")
MAX_AUDIO_BYTES = 5_000_000
AUDIO_TYPES = {"audio/webm": "webm", "audio/mp4": "mp4", "audio/mpeg": "mp3", "audio/wav": "wav",
               "audio/x-wav": "wav"}


def keywords(plants):
    # The service refuses the whole request if a keyword holds one of these characters.
    return sorted({re.sub(r"[<>\r\n]", "", base_name(p.name)).strip() for p in plants if p.name.strip()})


def transcribe(audio, content_type, plants, client=None):
    kind = (content_type or "").partition(";")[0].strip().casefold()
    if not audio or kind not in AUDIO_TYPES:
        raise ValueError("Diese Aufnahme kann nicht verarbeitet werden.")
    load_dotenv()
    model = os.getenv("OPENAI_TRANSCRIBE_MODEL") or "gpt-transcribe"
    started, error_class = monotonic(), None
    try:
        service = client or OpenAI(timeout=30.0, max_retries=0)
        reply = service.audio.transcriptions.create(
            model=model, file=(f"aufnahme.{AUDIO_TYPES[kind]}", audio, kind), languages=["de"],
            keywords=keywords(plants))
    except Exception as exc:
        error_class = type(exc).__name__
        raise QueryInterpreterError(
            "Die Spracherkennung konnte nicht abgeschlossen werden. "
            "Bitte Verbindung und API-Konfiguration prüfen und erneut versuchen."
        ) from exc
    finally:
        logger.info(json.dumps({"model": model, "audio_bytes": len(audio), "api_calls": 1,
                                "duration_ms": round((monotonic() - started) * 1000),
                                "error_class": error_class}))
    return reply.text.strip()
