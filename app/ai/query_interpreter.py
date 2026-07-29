from __future__ import annotations

from typing import Protocol

from app.ai.query_models import ParsedQuery


class QueryInterpreterError(RuntimeError):
    """Fehler beim Interpretieren einer Kundenfrage."""


class QueryInterpreter(Protocol):
    """Gemeinsame Schnittstelle für alle Query Interpreter."""

    def interpret(self, question: str) -> ParsedQuery:
        """Übersetzt eine Kundenfrage in strukturierte Anforderungen."""
        ...
