"""Data rescue: upload scans (with provenance), view enhancement steps, facts and the review queue."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ... import audit
from ...config import get_settings
from ...db import get_db
from ...ingest.connectors.inbox import DOC_EXT, register_inbox_file, write_meta
from ...models import Document, Fact, FactReview, Page, Source
from ...registry import abspath, source_to_dict
from ...rescue import pipeline
from ...rescue.samples import list_samples, sample_path
from ..deps import CurrentUser, require

router = APIRouter(prefix="/api/rescue", tags=["rescue"])
MAX_UPLOAD = 60 * 1024 * 1024
MAX_SYNC_PAGES = 5


def parse_pages(spec: str, n: int) -> list[int]:
    out: set[int] = set()
    for part in (spec or "1").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    pages = sorted(p for p in out if 1 <= p <= n)
    if not pages:
        raise HTTPException(400, f"No valid page numbers (document has {n} page(s)).")
    if len(pages) > MAX_SYNC_PAGES:
        raise HTTPException(400, f"Please process at most {MAX_SYNC_PAGES} pages at a time.")
    return pages


def fact_out(f: Fact) -> dict:
    return {
        "id": f.id,
        "page_id": f.page_id,
        "type": f.type,
        "value": f.value,
        "units": f.units,
        "normalized": f.normalized,
        "context": f.context,
        "bbox": f.bbox,
        "confidence": f.confidence,
        "method": f.method,
        "lon": f.lon,
        "lat": f.lat,
        "geocode_method": f.geocode_method,
        "location_uncertain": f.location_uncertain,
        "status": f.status,
        "reviews": [
            {
                "username": r.username,
                "action": r.action,
                "at": r.at.isoformat(),
                "comment": r.comment,
                "before": r.before,
                "after": r.after,
            }
            for r in f.reviews
        ],
    }


def page_out(p: Page, with_facts: bool = True) -> dict:
    d = {
        "id": p.id,
        "document_id": p.document_id,
        "page_no": p.page_no,
        "width": p.width,
        "height": p.height,
        "processed": p.processed,
        "ocr_engine": p.ocr_engine,
        "quality_before": p.quality_before,
        "quality_after": p.quality_after,
        "steps": [{"name": s["name"], "params": s["params"], "info": s.get("info", {})} for s in (p.steps or [])],
        "fact_counts": {
            st: sum(1 for f in p.facts if f.status == st) for st in ("pending", "approved", "edited", "rejected")
        },
    }
    if with_facts:
        d["facts"] = [fact_out(f) for f in sorted(p.facts, key=lambda f: (f.bbox[1], f.bbox[0]))]
        d["ocr_text"] = p.ocr_text
    return d


def doc_out(db: Session, d: Document) -> dict:
    src = db.get(Source, d.source_id)
    return {
        "id": d.id,
        "title": d.title,
        "original_filename": d.original_filename,
        "page_count": d.page_count,
        "uploaded_by": d.uploaded_by,
        "created_at": d.created_at.isoformat(),
        "sha256": d.sha256,
        "source": source_to_dict(src, include_files=False) if src else None,
        "pages": [page_out(p, with_facts=False) for p in sorted(d.pages, key=lambda p: p.page_no)],
    }


def _process(db: Session, doc: Document, pages: list[int]) -> None:
    for n in pages:
        pg = pipeline.get_or_create_page(db, doc, n)
        try:
            pipeline.process_page(db, pg)
        except RuntimeError as e:
            raise HTTPException(500, str(e)) from e


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    source_name: str = Form(...),
    publisher: str = Form(...),
    licence: str = Form(...),
    permission: str = Form(...),
    url: str = Form(""),
    notes: str = Form(""),
    pages: str = Form("1"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require("rescue.upload")),
) -> dict:
    if permission.strip().lower() not in ("yes", "y", "true"):
        raise HTTPException(
            400, "GeoRevive only processes documents we have permission to use. Confirm permission before uploading."
        )
    name = Path(file.filename or "upload").name
    ext = Path(name).suffix.lower()
    if ext not in DOC_EXT:
        raise HTTPException(400, f"Unsupported file type {ext}. Use PDF, PNG, JPG or TIFF.")
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File is larger than 60 MB.")
    if not data:
        raise HTTPException(400, "The file is empty.")
    inbox = get_settings().path("inbox_dir")
    inbox.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem)[:80] + ext
    dest = inbox / safe
    dest.write_bytes(data)
    meta = {
        "source_name": source_name.strip(),
        "publisher": publisher.strip(),
        "url": url.strip(),
        "licence": licence.strip(),
        "permission": "yes",
        "notes": notes.strip(),
        "uploaded_by": user.username,
        "uploaded_at": datetime.now(UTC).isoformat(),
    }
    write_meta(dest, meta)
    sid = register_inbox_file(db, dest, meta)
    doc = pipeline.create_document(db, dest, sid, source_name.strip() or name, user.username)
    pg = parse_pages(pages, doc.page_count)
    audit.log(db, user.username, user.role, "upload", "document", doc.id, {"file": safe, "pages": pg})
    _process(db, doc, pg)
    return doc_out(db, doc)


@router.get("/samples")
def samples(_user: CurrentUser = Depends(require("rescue.view"))) -> dict:
    return {"samples": list_samples()}


@router.get("/samples/{sample_id}/file")
def sample_file(sample_id: str, _user: CurrentUser = Depends(require("rescue.view"))) -> FileResponse:
    p = sample_path(sample_id)
    if p is None:
        raise HTTPException(404, "Sample not found.")
    return FileResponse(p, media_type="image/png", filename=p.name)


@router.post("/samples/{sample_id}/load")
def load_sample(
    sample_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require("rescue.upload"))
) -> dict:
    s = next((x for x in list_samples() if x["id"] == sample_id), None)
    p = sample_path(sample_id)
    if s is None or p is None:
        raise HTTPException(404, "Sample not found.")
    if db.get(Source, s["source_id"]) is None:
        raise HTTPException(409, "The sample's source is not in the registry - run ingestion first.")
    doc = pipeline.create_document(db, p, s["source_id"], s["title"], user.username)
    audit.log(db, user.username, user.role, "upload", "document", doc.id, {"sample": sample_id})
    _process(db, doc, [1])
    return doc_out(db, doc)


@router.get("/documents")
def documents(db: Session = Depends(get_db), _user: CurrentUser = Depends(require("rescue.view"))) -> dict:
    docs = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return {"documents": [doc_out(db, d) for d in docs]}


@router.get("/documents/{doc_id}")
def document(doc_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require("rescue.view"))) -> dict:
    d = db.get(Document, doc_id)
    if d is None:
        raise HTTPException(404, "Document not found.")
    audit.log(db, user.username, user.role, "view", "document", doc_id)
    return doc_out(db, d)


@router.post("/documents/{doc_id}/pages/{page_no}/process")
def process(
    doc_id: str, page_no: int, db: Session = Depends(get_db), _user: CurrentUser = Depends(require("rescue.upload"))
) -> dict:
    d = db.get(Document, doc_id)
    if d is None:
        raise HTTPException(404, "Document not found.")
    if not 1 <= page_no <= d.page_count:
        raise HTTPException(400, "Page out of range.")
    _process(db, d, [page_no])
    pg = db.scalar(select(Page).where(Page.document_id == doc_id, Page.page_no == page_no))
    return page_out(pg)


@router.get("/pages/{page_id}")
def page(page_id: int, db: Session = Depends(get_db), _user: CurrentUser = Depends(require("rescue.view"))) -> dict:
    p = db.get(Page, page_id)
    if p is None:
        raise HTTPException(404, "Page not found.")
    out = page_out(p)
    out["document"] = {"id": p.document.id, "title": p.document.title, "page_count": p.document.page_count}
    src = db.get(Source, p.document.source_id)
    out["source"] = source_to_dict(src, include_files=False) if src else None
    return out


@router.get("/pages/{page_id}/image/{step}")
def page_image(
    page_id: int, step: str, db: Session = Depends(get_db), _user: CurrentUser = Depends(require("rescue.view"))
) -> FileResponse:
    p = db.get(Page, page_id)
    if p is None:
        raise HTTPException(404, "Page not found.")
    if step == "original":
        path = p.original_image
    else:
        path = next((s["path"] for s in (p.steps or []) if s["name"] == step), None)
    if not path or not abspath(path).exists():
        raise HTTPException(404, "Image not available.")
    return FileResponse(abspath(path), media_type="image/png")


class ReviewIn(BaseModel):
    action: str  # approve | reject | edit
    value: str | None = None
    units: str | None = None
    type: str | None = None
    lon: float | None = None
    lat: float | None = None
    comment: str = ""


EDITABLE = ("value", "units", "type", "lon", "lat")


@router.post("/facts/{fact_id}/review")
def review(
    fact_id: int, body: ReviewIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require("facts.review"))
) -> dict:
    f = db.get(Fact, fact_id)
    if f is None:
        raise HTTPException(404, "Fact not found.")
    if body.action not in ("approve", "reject", "edit"):
        raise HTTPException(400, "action must be approve, reject or edit")
    before = {k: getattr(f, k) for k in EDITABLE + ("status", "location_uncertain")}
    if body.action == "edit":
        changed = False
        for k in EDITABLE:
            v = getattr(body, k)
            if v is not None and v != getattr(f, k):
                setattr(f, k, v)
                changed = True
        if body.lon is not None and body.lat is not None:
            f.geocode_method = f"set by {user.username} during review"
            f.location_uncertain = False
        if not changed:
            raise HTTPException(400, "Nothing to change.")
        f.status = "edited"
    else:
        f.status = "approved" if body.action == "approve" else "rejected"
    after = {k: getattr(f, k) for k in EDITABLE + ("status", "location_uncertain")}
    db.add(
        FactReview(
            fact_id=f.id, username=user.username, action=body.action, before=before, after=after, comment=body.comment
        )
    )
    audit.log(db, user.username, user.role, body.action, "fact", f.id, {"value": f.value, "type": f.type})
    db.flush()
    pipeline.rebuild_rescued_layer(db)
    db.refresh(f)
    return fact_out(f)


@router.get("/queue")
def queue(db: Session = Depends(get_db), _user: CurrentUser = Depends(require("rescue.view"))) -> dict:
    rows = db.execute(
        select(Fact, Page, Document)
        .join(Page, Fact.page_id == Page.id)
        .join(Document, Page.document_id == Document.id)
        .where(Fact.status == "pending")
        .order_by(Document.created_at.desc(), Page.page_no, Fact.id)
        .limit(500)
    ).all()
    counts = dict(db.execute(select(Fact.status, func.count()).group_by(Fact.status)).all())
    return {
        "counts": counts,
        "facts": [
            {**fact_out(f), "document_id": d.id, "document_title": d.title, "page_no": p.page_no} for f, p, d in rows
        ],
    }
