"""Start with `python -m app`; every setting comes from the environment or .env."""
import os

import uvicorn

from app.config import load_settings


def main() -> None:
    settings = load_settings()
    settings.validate()
    if not os.getenv("OPENAI_API_KEY"):
        print("Hinweis: OPENAI_API_KEY fehlt. Die Beratung meldet dann einen Fehler.")
    print(f"KI-Sister läuft auf http://{settings.host}:{settings.port}")
    uvicorn.run("app.main:app", host=settings.host, port=settings.port,
                proxy_headers=settings.production)


if __name__ == "__main__":
    main()
