"""Application wiring; product routes are added in A1/A2."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.db import DEFAULT_DATABASE_PATH

APP_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    secret = os.environ.get("SESSION_SECRET", "")

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if not secret.strip():
            raise RuntimeError("Set SESSION_SECRET before starting the application.")
        yield

    application = FastAPI(title="Bookstore", lifespan=lifespan)
    application.state.database_path = Path(
        os.environ.get("DATABASE_PATH", str(DEFAULT_DATABASE_PATH))
    )
    application.state.templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
    application.add_middleware(SessionMiddleware, secret_key=secret, same_site="lax")
    # An empty static mount returns 404 before B0 supplies its assets. Merely
    # setting check_dir=False would still fail check_config on the first request.
    static_directory = APP_DIR / "static"
    application.mount(
        "/static",
        StaticFiles(directory=str(static_directory) if static_directory.is_dir() else None),
        name="static",
    )
    return application


app = create_app()
