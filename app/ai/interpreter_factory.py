from __future__ import annotations

import os

from dotenv import load_dotenv

from app.ai.query_interpreter import QueryInterpreter
from app.ai.interpreters.fake_interpreter import FakeQueryInterpreter


def create_query_interpreter() -> QueryInterpreter:
    load_dotenv()

    provider = os.getenv(
        "QUERY_INTERPRETER_PROVIDER",
        "openai",
    ).strip().casefold()

    if provider == "fake":
        return FakeQueryInterpreter()

    if provider == "openai":
        from app.ai.interpreters.openai_interpreter import (
            OpenAIQueryInterpreter,
        )

        return OpenAIQueryInterpreter()

    raise ValueError(
        "Unbekannter Query-Interpreter-Anbieter: "
        f"{provider!r}. "
        "Erlaubt sind derzeit: fake, openai."
    )
