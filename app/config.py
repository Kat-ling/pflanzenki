"""Settings for both operating modes: local on the own computer, later on the web."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

ENVIRONMENTS = {"local", "production"}


@dataclass(frozen=True)
class Settings:
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000
    access_password: str = ""
    requests_per_minute: int = 20
    requests_per_day: int = 300
    trusted_proxies: str = ""

    @property
    def production(self) -> bool:
        return self.environment == "production"

    def validate(self) -> None:
        if self.environment not in ENVIRONMENTS:
            raise ValueError("APP_ENV muss local oder production sein.")
        if self.production and not self.access_password:
            raise ValueError("Für den Webbetrieb muss APP_ACCESS_PASSWORD gesetzt sein.")


def load_settings() -> Settings:
    load_dotenv()
    environment = os.getenv("APP_ENV", "local").strip().casefold()
    return Settings(
        environment=environment,
        host=os.getenv("HOST") or ("0.0.0.0" if environment == "production" else "127.0.0.1"),
        port=int(os.getenv("PORT") or 8000),
        access_password=os.getenv("APP_ACCESS_PASSWORD", ""),
        requests_per_minute=int(os.getenv("APP_REQUESTS_PER_MINUTE") or 20),
        requests_per_day=int(os.getenv("APP_REQUESTS_PER_DAY") or 300),
        trusted_proxies=os.getenv("APP_TRUSTED_PROXIES", "").strip(),
    )
