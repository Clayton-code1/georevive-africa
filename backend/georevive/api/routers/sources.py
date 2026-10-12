from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ... import audit
from ...config import get_settings
from ...db import get_db
from ...models import Source
from ...registry import all_sources, source_to_dict
from ..deps import CurrentUser, require

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("")
def list_sources(db: Session = Depends(get_db), user: CurrentUser = Depends(require("sources.view"))) -> dict:
    srcs = all_sources(db)
    counts: dict[str, int] = {}
    for s in srcs:
        counts[s.status] = counts.get(s.status, 0) + 1
    audit.log(db, user.username, user.role, "view", "source_registry", "all")
    return {"sources": [source_to_dict(s) for s in srcs], "status_counts": counts}


@router.get("/report/markdown", response_class=PlainTextResponse)
def report_markdown(db: Session = Depends(get_db), user: CurrentUser = Depends(require("sources.view"))) -> str:
    p = get_settings().path("reports_dir") / "DATA_SOURCES.md"
    if not p.exists():
        raise HTTPException(404, "The Data Report has not been generated yet. Run ingestion first.")
    audit.log(db, user.username, user.role, "view", "data_report", "DATA_SOURCES.md")
    return p.read_text(encoding="utf-8")


@router.get("/{source_id}")
def get_source(
    source_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require("sources.view"))
) -> dict:
    s = db.get(Source, source_id)
    if s is None:
        raise HTTPException(404, "Source not found.")
    audit.log(db, user.username, user.role, "view", "source", source_id)
    return source_to_dict(s)
