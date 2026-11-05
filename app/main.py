from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from app.advisor.engine import advise
from app.config import Settings, load_settings
from app.repository import load_plants
from app.security import install_guards

from app.ai.interpreter_factory import create_query_interpreter
from app.ai.query_interpreter import QueryInterpreterError
from app.ai.dialogue_models import ChatMessage, DialoguePlan

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)
    previous_plan: DialoguePlan | None = None
    visible_plant_ids: list[str] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def check_history_size(self):
        if sum(len(m.content) for m in self.history) > 120000:
            raise ValueError("Das Gespräch ist zu lang. Bitte eine neue Beratung beginnen.")
        return self

class InterpretRequest(AskRequest):
    pass


def visible_plants(payload: AskRequest, plants):
    by_id = {p.id: p for p in plants}
    ids = payload.visible_plant_ids
    if len(set(ids)) != len(ids) or any(key not in by_id for key in ids):
        raise ValueError("Die angezeigten Sorten passen nicht mehr zum Katalog. Bitte eine neue Beratung beginnen.")
    return [{"plant_id": key, "name": by_id[key].name} for key in ids]

@router.get("/", response_class=FileResponse, include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/healthz")
def health() -> dict[str, str]:
    if not load_plants():
        raise HTTPException(status_code=503, detail="Katalog ist leer.")
    return {"status": "ok"}


@router.post("/api/ask")
def ask(payload: AskRequest):
    try:
        interpreter = create_query_interpreter()
        from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
        if isinstance(interpreter, OpenAIQueryInterpreter):
            from app.ai.catalogue_answer import consult
            plants = load_plants()
            return consult(interpreter, plants, payload.question, payload.history,
                           payload.previous_plan, visible_plants(payload, plants))
        if payload.history:
            raise ValueError(
                "Der lokale Fake-Interpreter unterstützt keine Gespräche. "
                "Bitte QUERY_INTERPRETER_PROVIDER=openai verwenden oder eine neue Beratung beginnen."
            )
        parsed_query = interpreter.interpret(payload.question)

        result = advise(
            plants=load_plants(),
            query=parsed_query,
        )
        return {**result.model_dump(), "warnings": [
            "Lokaler Testmodus: nur feste Merkmale, keine freie Gesprächsauswertung. "
            "Für natürliche Beratung QUERY_INTERPRETER_PROVIDER=openai verwenden."
        ]}

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except QueryInterpreterError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@router.post(
    "/api/interpret",
)
def interpret_question(
    payload: InterpretRequest,
):
    try:
        interpreter = create_query_interpreter()
        from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
        if isinstance(interpreter, OpenAIQueryInterpreter):
            from app.ai.catalogue_dialogue import interpret_dialogue
            plants = load_plants()
            return interpret_dialogue(interpreter, plants, payload.question, payload.history,
                                      payload.previous_plan, visible_plants(payload, plants))
        if payload.history:
            raise ValueError("Gesprächskontext erfordert QUERY_INTERPRETER_PROVIDER=openai.")

        return interpreter.interpret(
            payload.question
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except QueryInterpreterError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    settings.validate()
    documentation = {"docs_url": None, "redoc_url": None, "openapi_url": None} if settings.production else {}
    application = FastAPI(title="KI-Sister", version="0.6.0", **documentation)
    install_guards(application, settings)
    application.include_router(router)
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return application


app = create_app()
