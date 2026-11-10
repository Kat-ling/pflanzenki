"""Start with `python -m app`; every setting comes from the environment or .env."""
import os

import uvicorn

from app.config import load_settings


def main() -> None:
    settings = load_settings()
    settings.validate()
    if not os.getenv("OPENAI_API_KEY"):
        print("Hinweis: OPENAI_API_KEY fehlt. Die Beratung meldet dann einen Fehler.")
    if settings.production and not settings.trusted_proxies:
        print("Hinweis: APP_TRUSTED_PROXIES fehlt. Hinter einem Proxy teilen sich dann "
              "alle Besucher ein gemeinsames Anfragelimit.")
    print(f"KI-Sister läuft auf http://{settings.host}:{settings.port}")
    # Without the proxy's address uvicorn only trusts 127.0.0.1 and every
    # visitor would appear under the proxy's own address.
    uvicorn.run("app.main:app", host=settings.host, port=settings.port,
                proxy_headers=settings.production,
                forwarded_allow_ips=settings.trusted_proxies or None)


if __name__ == "__main__":
    main()
