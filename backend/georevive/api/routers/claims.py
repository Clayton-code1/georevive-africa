"""Claim check reports: polygon or coordinates in, plain-language PDF out (watermarked on download)."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import audit
from ...config import get_settings
from ...db import get_db
from ...models import ClaimReport, ModelRun
from ...registry import abspath, rel
from ...reports import claim_analysis
from ...reports.claim_pdf import build_pdf
from ...reports.mapsnap import snapshot
from ...reports.watermark import stamp, watermark_pdf
from ...security import can
from ..deps import CurrentUser, require

router = APIRouter(prefix="/api/claims", tags=["claims"])


class ClaimIn(BaseModel):
    name: str = "Claim"
    polygon: dict[str, Any] | None = None
    lon: float | None = None
    lat: float | None = None
    side_m: float = 500.0  # used with lon/lat: a square claim of this side length
    technical: bool = True


def report_out(c: ClaimReport) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "username": c.username,
        "created_at": c.created_at.isoformat(),
        "polygon": c.polygon,
        "summary": c.summary,
        "run_id": c.run_id,
    }


@router.post("")
def create(body: ClaimIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require("claims.create"))) -> dict:
    s = get_settings()
    if body.polygon is None:
        if body.lon is None or body.lat is None:
            raise HTTPException(400, "Give a polygon, or a latitude and longitude.")
        if not (10 <= body.side_m <= 5000):
            raise HTTPException(400, "Square side must be between 10 m and 5 km.")
        poly = claim_analysis.square_around(body.lon, body.lat, body.side_m, s.working_crs)
    else:
        poly = body.polygon.get("geometry", body.polygon)
    name = re.sub(r"[^\w\s.-]", "", body.name).strip()[:80] or "Claim"
    try:
        a = claim_analysis.analyse(db, poly, name)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    run = db.scalar(select(ModelRun).order_by(ModelRun.id.desc()))
    rep = ClaimReport(
        username=user.username, name=name, polygon=poly, run_id=run.id if run else None, summary={}, pdf_path=""
    )
    db.add(rep)
    db.flush()
    out_dir = s.path("reports_dir") / "generated"
    png = out_dir / f"claim_{rep.id}_map.png"
    a["map_attributions"] = snapshot(poly, png, abspath(run.grid_path) if run and run.grid_path else None, title=name)
    pdf = build_pdf(
        a,
        png,
        out_dir / f"claim_{rep.id}.pdf",
        prepared_for=f"{user.display_name} ({user.username})",
        technical=body.technical,
    )
    rep.pdf_path = rel(pdf)
    rep.summary = {
        k: a.get(k)
        for k in (
            "area_ha",
            "district",
            "province",
            "centroid",
            "geology",
            "geology_scale",
            "nearest_fault_km",
            "nearest_road",
            "nearest_town",
            "indicators",
            "sources",
            "layers_used",
        )
    }
    rep.summary["occurrences"] = a.get("occurrences", [])[:20]
    p = a.get("prospectivity") or {}
    rep.summary["prospectivity"] = {k: p.get(k) for k in ("run_id", "method", "mean", "max", "area_percentile", "auc")}
    if p.get("best_cell"):
        rep.summary["prospectivity"]["explanation"] = p["best_cell"]["explanation"]
    audit.log(
        db, user.username, user.role, "claim_report", "claim_report", rep.id, {"name": name, "area_ha": a["area_ha"]}
    )
    db.flush()
    return report_out(rep)


@router.get("")
def list_reports(db: Session = Depends(get_db), user: CurrentUser = Depends(require("claims.create"))) -> dict:
    q = select(ClaimReport).order_by(ClaimReport.id.desc()).limit(100)
    if not can(user.role, "audit.view"):
        q = q.where(ClaimReport.username == user.username)  # users see their own reports; admin sees all
    return {"reports": [report_out(c) for c in db.scalars(q)]}


@router.get("/{report_id}/pdf")
def download(report_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(require("claims.create"))):
    c = db.get(ClaimReport, report_id)
    if c is None or (c.username != user.username and not can(user.role, "audit.view")):
        raise HTTPException(404, "Report not found.")
    data = watermark_pdf(abspath(c.pdf_path), stamp(user.username, user.organisation))
    audit.log(db, user.username, user.role, "download", "claim_report", report_id, {"watermarked": True})
    fn = re.sub(r"\W+", "_", c.name) + f"_claim_check_{report_id}.pdf"
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{fn}"'})
