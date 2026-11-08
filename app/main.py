"""Application wiring and catalog routes; purchase routes arrive in A2."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
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
        # Asset errors must not depend on frontend HTML templates being present.
        if request.url.path.startswith('/static/'):
            return await http_exception_handler(request, exc)
        return render(request, 'error.html', {
            'status_code': exc.status_code, 'message': str(exc.detail),
        }, exc.status_code)
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
