"""Map layers: list, GeoJSON for vectors, PNG overlays for rasters, feature lineage.
Investors only see layers shared with them in the data room."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import audit
from ...config import get_settings
from ...db import get_db
from ...lineage import resolve, source_ref
from ...models import Layer, Share
from ...registry import abspath
from ...security import can
from ..deps import CurrentUser, require_any

router = APIRouter(prefix="/api/layers", tags=["layers"])
MAP_ACCESS = require_any("map.view", "claims.create")
# Miners (claim reports only) see just the base map and context layers
MINER_GROUPS = ("base", "context")


def visible_layer_ids(db: Session, user: CurrentUser) -> set[str] | None:
    """None = all layers; otherwise the set of layer ids shared with this user."""
    if can(user.role, "layers.view_all"):
        return None
    if not can(user.role, "map.view"):  # miner: base map for drawing claims only
        return set(db.scalars(select(Layer.id).where(Layer.group.in_(MINER_GROUPS))))
    return set(db.scalars(select(Share.layer_id).where(Share.user_id == user.id)))


def get_visible_layer(db: Session, user: CurrentUser, layer_id: str) -> Layer:
    layer = db.get(Layer, layer_id)
    vis = visible_layer_ids(db, user)
    if layer is None or (vis is not None and layer_id not in vis):
        raise HTTPException(404, "Layer not found or not shared with you.")
    return layer


def layer_to_dict(layer: Layer) -> dict:
    return {
        "id": layer.id,
        "name": layer.name,
        "group": layer.group,
        "kind": layer.kind,
        "geometry_type": layer.geometry_type,
        "feature_count": layer.feature_count,
        "attribution": layer.attribution,
        "legend": layer.legend,
        "style": layer.style,
        "description": layer.description,
        "overlay_bounds": layer.overlay_bounds,
        "has_overlay": bool(layer.overlay_png),
        "source": source_ref(layer.source),
        "source_status": layer.source.status,
        "created_at": layer.created_at.isoformat() if layer.created_at else None,
    }


@router.get("")
def list_layers(db: Session = Depends(get_db), user: CurrentUser = Depends(MAP_ACCESS)) -> dict:
    vis = visible_layer_ids(db, user)
    layers = db.scalars(select(Layer).order_by(Layer.group, Layer.name)).all()
    if vis is not None:
        layers = [x for x in layers if x.id in vis]
    s = get_settings()
    return {"layers": [layer_to_dict(x) for x in layers], "bbox": list(s.bbox), "pilot_name": s.pilot_name}


@router.get("/{layer_id}/geojson")
def layer_geojson(
    layer_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(MAP_ACCESS)
) -> JSONResponse:
    layer = get_visible_layer(db, user, layer_id)
    if layer.kind != "vector" or not layer.gpkg_table:
        raise HTTPException(400, "Not a vector layer.")
    from ...ingest.process import read_vector

    gdf = read_vector(get_settings().path("gpkg"), layer.gpkg_table)
    gdf = gdf.to_crs("EPSG:4326")
    gdf["_fid"] = range(len(gdf))
    audit.log(db, user.username, user.role, "view", "layer", layer_id)
    return JSONResponse(json.loads(gdf.to_json(drop_id=True)))


@router.get("/{layer_id}/overlay.png")
def layer_overlay(
    layer_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(MAP_ACCESS)
) -> FileResponse:
    layer = get_visible_layer(db, user, layer_id)
    if not layer.overlay_png:
        raise HTTPException(400, "Layer has no image overlay.")
    p = abspath(layer.overlay_png)
    if not p.exists():
        raise HTTPException(404, "Overlay file missing - re-run ingestion.")
    return FileResponse(p, media_type="image/png")


@router.get("/{layer_id}/value")
def layer_value(
    layer_id: str, lon: float, lat: float, db: Session = Depends(get_db), user: CurrentUser = Depends(MAP_ACCESS)
) -> dict:
    """Sample a raster layer at a point (for the map's click panel)."""
    layer = get_visible_layer(db, user, layer_id)
    if layer.kind != "raster" or not layer.raster_path:
        raise HTTPException(400, "Not a value raster.")
    import math

    import rasterio
    from pyproj import Transformer

    with rasterio.open(abspath(layer.raster_path)) as src:
        x, y = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform(lon, lat)
        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return {"value": None, "label": "Outside the layer"}
        v = float(src.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
    if math.isnan(v):
        return {"value": None, "label": "No data here (masked: cloud, water or dense vegetation)"}
    legend = layer.legend or {}
    pct = ""
    if legend.get("type") == "continuous" and legend.get("max") is not None:
        lo, hi = legend["min"], legend["max"]
        pct = f" ({'above' if v > hi else 'below' if v < lo else 'within'} the displayed range {lo:.3g}-{hi:.3g})"
    return {"value": v, "label": f"{v:.4g}{pct}"}


@router.get("/{layer_id}/lineage")
def layer_lineage(layer_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(MAP_ACCESS)) -> dict:
    layer = get_visible_layer(db, user, layer_id)
    return {"layer": layer_to_dict(layer), "lineage": resolve(db, [{"kind": "layer", "layer_id": layer.id}])}
