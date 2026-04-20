from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="IT Asset Management MVP (Web)")
    app.include_router(router)

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app


app = create_app()
