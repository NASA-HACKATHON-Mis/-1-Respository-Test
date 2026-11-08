"""Application wiring and catalog routes; purchase routes arrive in A2."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.db import DEFAULT_DATABASE_PATH
from app.routers.catalog import render, router
from starlette.exceptions import HTTPException

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
    application.include_router(router)

    @application.exception_handler(HTTPException)
    async def http_error(request, exc):
        return render(request, 'error.html', {
            'status_code': exc.status_code, 'message': str(exc.detail),
        }, exc.status_code)
    # Frontend-owned directories may not exist until B0 lands.
    application.mount(
        "/static", StaticFiles(directory=str(APP_DIR / "static"), check_dir=False), name="static"
    )
    return application


app = create_app()
