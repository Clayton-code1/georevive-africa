"""FastAPI application. Serves the API and (when built) the React frontend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import ensure_dirs, get_settings
from ..db import init_db, session_scope
from ..seed import seed_users
from .routers import audit_log, auth, claims, dataroom, demo, layers, meta, prospect, rescue, sources


def startup() -> None:
    s = get_settings()
    ensure_dirs(s)
    init_db()
    with session_scope() as db:
        seed_users(db)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    startup()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="GeoRevive Africa API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for r in (auth, meta, sources, layers, rescue, prospect, claims, dataroom, demo, audit_log):
        app.include_router(r.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    dist = get_settings().root / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(404, "Not found")
            candidate = dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
