"""Data-rescue pipeline: document -> page images -> enhancement -> OCR -> facts -> geocoding.
Only geologist-approved facts are written to the geodatabase layer `rescued_facts`."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Document, Fact, OcrWord, Page, Source
from ..registry import abspath, rel, sha256_file, upsert_layer, upsert_source
from . import enhance as enh
from .extract import Extractor
from .geocode import gazetteer, geocode_facts
from .ocr import Word, choose_engine, run_ocr, words_to_text

RENDER_DPI = 200
MAX_SIDE = 3000  # keep page images a manageable size


def doc_dir(doc_id: str) -> Path:
    return get_settings().path("rescue_dir") / doc_id


def make_doc_id(sha: str) -> str:
    return "doc_" + sha[:12]


def page_count(path: Path) -> int:
    if path.suffix.lower() == ".pdf":
        import fitz

        with fitz.open(path) as d:
            return d.page_count
    return 1


def render_page(path: Path, page_no: int) -> np.ndarray:
    """Return a BGR image for a page (1-based) of a PDF, or the image itself."""
    if path.suffix.lower() == ".pdf":
        import fitz

        with fitz.open(path) as d:
            pg = d[page_no - 1]
            zoom = RENDER_DPI / 72
            longest = max(pg.rect.width, pg.rect.height) * zoom
            if longest > MAX_SIDE:
                zoom *= MAX_SIDE / longest
            pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    img = enh.load_image(path)
    h, w = img.shape[:2]
    if max(h, w) > MAX_SIDE:
        s = MAX_SIDE / max(h, w)
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return img


def create_document(db: Session, src_path: Path, source_id: str, title: str, uploaded_by: str) -> Document:
    """Register a document (idempotent by checksum). The original file is copied, made read-only
    and never modified."""
    sha = sha256_file(src_path)
    doc_id = make_doc_id(sha)
    existing = db.get(Document, doc_id)
    if existing:
        return existing
    d = doc_dir(doc_id)
    d.mkdir(parents=True, exist_ok=True)
    orig = d / ("original" + src_path.suffix.lower())
    if not orig.exists():
        shutil.copy2(src_path, orig)
        os.chmod(orig, stat.S_IREAD)
    n = page_count(orig)
    doc = Document(
        id=doc_id,
        source_id=source_id,
        title=title,
        original_filename=src_path.name,
        original_path=rel(orig),
        sha256=sha,
        page_count=n,
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    db.flush()
    return doc


def get_or_create_page(db: Session, doc: Document, page_no: int) -> Page:
    pg = db.scalar(select(Page).where(Page.document_id == doc.id, Page.page_no == page_no))
    if pg:
        return pg
    pdir = doc_dir(doc.id) / f"p{page_no:03d}"
    pdir.mkdir(parents=True, exist_ok=True)
    img = render_page(abspath(doc.original_path), page_no)
    orig = pdir / "00_original.png"
    enh.save_png(orig, img)
    pg = Page(document_id=doc.id, page_no=page_no, original_image=rel(orig), width=img.shape[1], height=img.shape[0])
    db.add(pg)
    db.flush()
    return pg


def process_page(db: Session, page: Page, engine_pref: str | None = None, force: bool = False) -> Page:
    if page.processed and not force:
        return page
    s = get_settings()
    engine = choose_engine(engine_pref or s.section("extraction").get("ocr_engine", "auto"))
    img = enh.load_image(abspath(page.original_image))
    gray0 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    pdir = abspath(page.original_image).parent
    res = enh.enhance(img, pdir)
    page.steps = [
        {"name": st["name"], "path": rel(st["path"]), "params": st["params"], "info": st["info"]} for st in res.steps
    ]
    page.enhanced_image = rel(pdir / "05_clahe.png")
    assert res.final_gray is not None
    page.width, page.height = int(res.final_gray.shape[1]), int(res.final_gray.shape[0])
    q_before = enh.quality(gray0)
    q_after = enh.quality(res.final_gray)

    # OCR runs once, on the enhanced page (a second pass on the original doubled the wait in live demos)
    words = run_ocr(res.final_gray, res.binary, engine)
    q_after["ocr_mean_conf"] = round(float(np.mean([w.conf for w in words])) if words else 0.0, 3)
    q_after["ocr_words"] = len(words)
    page.quality_before, page.quality_after = q_before, q_after
    page.ocr_engine = engine
    page.ocr_text = words_to_text(words)

    for old in list(page.words):
        db.delete(old)
    for old in list(page.facts):
        if old.status == "pending":
            db.delete(old)
    db.flush()
    for i, w in enumerate(words):
        db.add(OcrWord(page_id=page.id, idx=i, text=w.text, conf=w.conf, x=w.x, y=w.y, w=w.w, h=w.h, line=w.line))
    extract_and_store(db, page, words)
    page.processed = True
    db.flush()
    return page


def extract_and_store(db: Session, page: Page, words: list[Word], method_prefix: str = "") -> list[Fact]:
    facts = Extractor().extract(words)
    line_of = {i: (words[f.word_idx[0]].line if f.word_idx else -99) for i, f in enumerate(facts)}
    locs = geocode_facts(facts, gazetteer(get_settings().path("gpkg")), line_of)
    out = []
    for f, loc in zip(facts, locs, strict=True):
        row = Fact(
            page_id=page.id,
            type=f.type,
            value=f.value,
            units=f.units,
            normalized=f.normalized,
            context=f.context,
            bbox=f.bbox,
            confidence=f.confidence,
            method=method_prefix + f.method,
            lon=loc.lon,
            lat=loc.lat,
            geocode_method=loc.method,
            location_uncertain=loc.uncertain,
            status="pending",
        )
        db.add(row)
        out.append(row)
    db.flush()
    return out


# --- geodatabase layer of approved facts -------------------------------------------------
RESCUE_SOURCE_ID = "georevive_rescued_facts"


def ensure_rescue_source(db: Session) -> Source:
    return upsert_source(
        db,
        RESCUE_SOURCE_ID,
        name="GeoRevive data rescue - geologist-approved facts",
        publisher="GeoRevive team (derived from registered documents)",
        url="/rescue",
        licence="Derived data; each fact inherits the licence of its source document (see fact details)",
        status="downloaded",
        note="Facts extracted from scanned documents and approved or corrected by the geologist.",
        usage="Rescued-facts map layer; validation context for prospectivity; claim reports.",
        accessed_at=datetime.now(UTC),
    )


def rebuild_rescued_layer(db: Session) -> int:
    import geopandas as gpd
    from shapely.geometry import Point

    from ..ingest.process import write_vector

    rows = db.execute(
        select(Fact, Page, Document, Source)
        .join(Page, Fact.page_id == Page.id)
        .join(Document, Page.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
        .where(Fact.status.in_(("approved", "edited")), Fact.lon.is_not(None), Fact.lat.is_not(None))
    ).all()
    recs: list[dict[str, Any]] = []
    for f, p, d, s in rows:
        recs.append(
            {
                "fact_id": f.id,
                "type": f.type,
                "value": f.value,
                "units": f.units or "",
                "confidence": f.confidence,
                "method": f.method,
                "location_method": f.geocode_method or "",
                "location_uncertain": int(bool(f.location_uncertain)),
                "document_id": d.id,
                "document": d.title,
                "page_no": p.page_no,
                "source_name": s.name,
                "source_licence": s.licence,
                "geometry": Point(f.lon, f.lat),
            }
        )
    src = ensure_rescue_source(db)
    gpkg = get_settings().path("gpkg")
    gdf = (
        gpd.GeoDataFrame(recs, geometry="geometry", crs="EPSG:4326")
        if recs
        else gpd.GeoDataFrame({"fact_id": [], "type": [], "value": []}, geometry=gpd.GeoSeries([], crs="EPSG:4326"))
    )
    n = write_vector(gdf, gpkg, "rescued_facts")
    src.record_count = n
    upsert_layer(
        db,
        "rescued_facts",
        source_id=src.id,
        name="Rescued facts (geologist-approved)",
        group="rescued",
        kind="vector",
        gpkg_table="rescued_facts",
        geometry_type="Point",
        feature_count=n,
        attribution="Rescued facts: GeoRevive (from registered historical documents)",
        style={"type": "circle", "color": "#0e7490", "radius": 6, "stroke": "#F7F3EA"},
        legend={"type": "categorical", "items": [{"label": "Approved fact (click for page)", "color": "#0e7490"}]},
        description="Facts approved by the geologist; click one to open the original page.",
        derived_from=[{"kind": "source", "source_id": src.id}],
    )
    db.flush()
    return n


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
