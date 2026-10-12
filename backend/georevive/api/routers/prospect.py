"""Prospectivity: evidence, editable weights, model runs, targets, cell explanations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import DISCLAIMER, audit
from ...db import get_db
from ...models import ModelRun, ModelWeights
from ...prospect import engine
from ...prospect.evidence import EVIDENCE_INFO, stack_summary
from ...prospect.fuzzy import DEFAULT_WEIGHTS, MEMBERSHIP
from ...registry import abspath
from ..deps import CurrentUser, require

router = APIRouter(prefix="/api/prospect", tags=["prospect"])


def current_weights(db: Session, commodity: str = "gold") -> tuple[dict[str, float], dict | None]:
    row = db.scalar(select(ModelWeights).where(ModelWeights.commodity == commodity).order_by(ModelWeights.id.desc()))
    if row is None:
        return dict(DEFAULT_WEIGHTS), None
    return dict(row.weights), {"username": row.username, "at": row.created_at.isoformat(), "comment": row.comment}


def run_out(run: ModelRun, with_targets: bool = True) -> dict:
    d = {
        "id": run.id,
        "commodity": run.commodity,
        "method": run.method,
        "weights": run.weights,
        "features": run.features,
        "metrics": run.metrics,
        "username": run.username,
        "created_at": run.created_at.isoformat(),
        "overlay_bounds": run.overlay_bounds,
        "disclaimer": DISCLAIMER,
    }
    if with_targets:
        d["targets"] = [
            {
                "rank": t.rank,
                "lon": t.lon,
                "lat": t.lat,
                "score": t.score,
                "polygon": t.polygon,
                "contributions": t.contributions,
                "context": t.context,
                "explanation": t.explanation,
                "id": t.id,
            }
            for t in sorted(run.targets, key=lambda t: t.rank)
        ]
    return d


@router.get("/config")
def config(db: Session = Depends(get_db), _u: CurrentUser = Depends(require("model.view"))) -> dict:
    st = engine.get_stack()
    w, meta = current_weights(db)
    return {
        "evidence": stack_summary(st),
        "weights": w,
        "default_weights": DEFAULT_WEIGHTS,
        "weights_last_edited": meta,
        "memberships": {k: v["text"] for k, v in MEMBERSHIP.items()},
        "labels": {k: v["label"] for k, v in EVIDENCE_INFO.items()},
        "methods": [
            {
                "id": "fuzzy",
                "label": "Knowledge-driven (fuzzy logic)",
                "description": "Geologist-set weights; not trained on occurrences.",
            },
            {
                "id": "logistic",
                "label": "Data-driven: logistic regression",
                "description": "Trained on known occurrences vs random background; spatial cross-validation.",
            },
            {
                "id": "gbm",
                "label": "Data-driven: gradient boosting + SHAP",
                "description": "Non-linear comparison model; explanations by SHAP values.",
            },
        ],
        "disclaimer": DISCLAIMER,
    }


class WeightsIn(BaseModel):
    weights: dict[str, float]
    comment: str = ""


@router.put("/weights")
def set_weights(
    body: WeightsIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require("model.edit_weights"))
) -> dict:
    bad = [k for k in body.weights if k not in EVIDENCE_INFO]
    if bad:
        raise HTTPException(400, f"Unknown evidence layers: {bad}")
    if any(v < 0 or v > 1 for v in body.weights.values()):
        raise HTTPException(400, "Weights must be between 0 and 1.")
    if sum(body.weights.values()) <= 0:
        raise HTTPException(400, "At least one weight must be above zero.")
    old, _ = current_weights(db)
    db.add(ModelWeights(commodity="gold", weights=body.weights, username=user.username, comment=body.comment))
    audit.log(
        db,
        user.username,
        user.role,
        "weights_edit",
        "model_weights",
        "gold",
        {"before": old, "after": body.weights, "comment": body.comment},
    )
    return {"weights": body.weights}


class RunIn(BaseModel):
    method: str = "fuzzy"
    commodity: str = "gold"


@router.post("/run")
def run(body: RunIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require("model.run"))) -> dict:
    w, _ = current_weights(db, body.commodity)
    try:
        r = engine.run_model(db, body.method, user.username, weights=w, commodity=body.commodity)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(400, str(e)) from e
    audit.log(
        db, user.username, user.role, "model_run", "model_run", r.id, {"method": r.method, "auc": r.metrics.get("auc")}
    )
    db.refresh(r)
    return run_out(r)


@router.get("/runs")
def runs(db: Session = Depends(get_db), _u: CurrentUser = Depends(require("model.view"))) -> dict:
    rs = db.scalars(select(ModelRun).order_by(ModelRun.id.desc()).limit(50)).all()
    return {"runs": [run_out(r, with_targets=False) for r in rs]}


@router.get("/runs/latest")
def latest(
    method: str | None = None, db: Session = Depends(get_db), _u: CurrentUser = Depends(require("model.view"))
) -> dict:
    q = select(ModelRun).order_by(ModelRun.id.desc())
    if method:
        q = q.where(ModelRun.method == method)
    r = db.scalar(q)
    if r is None:
        raise HTTPException(404, "No model run yet.")
    return run_out(r)


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(require("model.view"))) -> dict:
    r = db.get(ModelRun, run_id)
    if r is None:
        raise HTTPException(404, "Run not found.")
    audit.log(db, user.username, user.role, "view", "model_run", run_id)
    return run_out(r)


@router.get("/runs/{run_id}/overlay.png")
def overlay(run_id: int, db: Session = Depends(get_db), _u: CurrentUser = Depends(require("model.view"))):
    r = db.get(ModelRun, run_id)
    if r is None or not r.overlay_png:
        raise HTTPException(404, "Run not found.")
    return FileResponse(abspath(r.overlay_png), media_type="image/png")


@router.get("/runs/{run_id}/cell")
def cell(
    run_id: int, lon: float, lat: float, db: Session = Depends(get_db), _u: CurrentUser = Depends(require("model.view"))
) -> dict:
    """Explain the score of any cell (click on the heat map)."""
    import numpy as np
    from pyproj import Transformer

    from ...ingest.process import read_raster
    from ...prospect import explain

    r = db.get(ModelRun, run_id)
    if r is None:
        raise HTTPException(404, "Run not found.")
    st = engine.get_stack()
    g = st.grid
    x, y = Transformer.from_crs("EPSG:4326", g.crs, always_xy=True).transform(lon, lat)
    cx, cy = ~g.transform * (x, y)
    row, col = int(np.floor(cy)), int(np.floor(cx))
    if not (0 <= row < g.height and 0 <= col < g.width):
        raise HTTPException(400, "Outside the pilot area.")
    score_grid, _ = read_raster(abspath(r.grid_path))
    sc = float(score_grid[row, col])
    if not np.isfinite(sc):
        return {"score": None, "explanation": "No score here (insufficient evidence data).", "contributions": []}
    contrib = engine.explain_cell(r, st, row, col)
    occ = engine.occurrences(r.commodity)
    occ_xy = np.array([[p.x, p.y] for p in occ.geometry]) if occ is not None and len(occ) else np.zeros((0, 2))
    ctx = engine._context(g, row, col, occ_xy, 5000)
    pct = float((score_grid[np.isfinite(score_grid)] <= sc).mean() * 100)
    return {
        "score": round(sc, 1),
        "percentile": round(pct, 1),
        "contributions": contrib,
        "context": ctx,
        "explanation": explain.sentence(contrib, ctx),
    }
