"""Protection for web operation. Locally only the response headers apply."""
from __future__ import annotations

import base64
import binascii
import secrets
from collections import defaultdict, deque
from datetime import date
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.config import Settings

PUBLIC_PATHS = {"/healthz"}
DOCUMENTATION_PATHS = ("/docs", "/redoc")
IMAGE_PATH = "/static/images/"
FAILED_LOGINS_PER_MINUTE = 10
HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    # Prepared for the planned voice input; only this application may ask.
    "Permissions-Policy": "microphone=(self)",
}
CONTENT_POLICY = ("default-src 'self'; base-uri 'none'; form-action 'self'; "
                  "frame-ancestors 'none'")


class RateLimiter:
    """Sliding window per client; this project runs as a single process."""

    def __init__(self, limit: int, window: float = 60.0) -> None:
        self.limit, self.window = limit, window
        self.calls: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client: str) -> bool:
        now = monotonic()
        if len(self.calls) > 10_000:
            self.calls = defaultdict(deque, {key: calls for key, calls in self.calls.items()
                                             if calls and now - calls[-1] <= self.window})
        calls = self.calls[client]
        while calls and now - calls[0] > self.window:
            calls.popleft()
        if len(calls) >= self.limit:
            return False
        calls.append(now)
        return True


class DailyBudget:
    """Upper bound for API calls per calendar day across all clients.

    The password is shared, so the limit per client alone caps no costs.
    Counted in memory: a restart begins a new day's budget.
    """

    def __init__(self, limit: int, today=date.today) -> None:
        self.limit, self.today = limit, today
        self.day, self.used = today(), 0

    def allow(self) -> bool:
        day = self.today()
        if day != self.day:
            self.day, self.used = day, 0
        if self.used >= self.limit:
            return False
        self.used += 1
        return True


def password_matches(header: str | None, password: str) -> bool:
    scheme, _, value = (header or "").partition(" ")
    if scheme.casefold() != "basic":
        return False
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    return secrets.compare_digest(decoded.partition(":")[2].encode(), password.encode())


def install_guards(app: FastAPI, settings: Settings) -> None:
    limiter = RateLimiter(settings.requests_per_minute)
    # Counted apart, so wrong passwords never use up the requests of signed-in visitors.
    failures = RateLimiter(FAILED_LOGINS_PER_MINUTE)
    budget = DailyBudget(settings.requests_per_day)

    def refused(request: Request) -> Response | None:
        if not settings.production:
            return None
        client = request.client.host if request.client else "unbekannt"
        too_many = JSONResponse({"detail": "Zu viele Anfragen. Bitte kurz warten."}, status_code=429)
        path = request.url.path
        if path not in PUBLIC_PATHS and not password_matches(
                request.headers.get("authorization"), settings.access_password):
            if not failures.allow(client):
                return too_many
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="KI-Sister"'})
        if path.startswith("/api/"):
            if not limiter.allow(client):
                return too_many
            if not budget.allow():
                return JSONResponse({"detail": "Für heute sind alle Anfragen aufgebraucht. "
                                               "Morgen geht es weiter."}, status_code=429)
        return None

    @app.middleware("http")
    async def guard(request: Request, call_next):
        response = refused(request) or await call_next(request)
        response.headers.update(HEADERS)
        if not request.url.path.startswith(DOCUMENTATION_PATHS):
            response.headers["Content-Security-Policy"] = CONTENT_POLICY
        if request.url.path.startswith(IMAGE_PATH) and response.status_code == 200:
            response.headers["Cache-Control"] = "private, max-age=86400"
        if settings.production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response
