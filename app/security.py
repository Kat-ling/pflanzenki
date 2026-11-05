"""Protection for web operation. Locally only the response headers apply."""
from __future__ import annotations

import base64
import binascii
import secrets
from collections import defaultdict, deque
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.config import Settings

PUBLIC_PATHS = {"/healthz"}
DOCUMENTATION_PATHS = ("/docs", "/redoc")
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
        calls = self.calls[client]
        while calls and now - calls[0] > self.window:
            calls.popleft()
        if len(calls) >= self.limit:
            return False
        calls.append(now)
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

    def refused(request: Request) -> Response | None:
        if not settings.production:
            return None
        client = request.client.host if request.client else "unbekannt"
        too_many = JSONResponse({"detail": "Zu viele Anfragen. Bitte kurz warten."}, status_code=429)
        path = request.url.path
        if path not in PUBLIC_PATHS and not password_matches(
                request.headers.get("authorization"), settings.access_password):
            if not limiter.allow(client):
                return too_many
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="KI-Sister"'})
        if path.startswith("/api/") and not limiter.allow(client):
            return too_many
        return None

    @app.middleware("http")
    async def guard(request: Request, call_next):
        response = refused(request) or await call_next(request)
        response.headers.update(HEADERS)
        if not request.url.path.startswith(DOCUMENTATION_PATHS):
            response.headers["Content-Security-Policy"] = CONTENT_POLICY
        if settings.production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response
