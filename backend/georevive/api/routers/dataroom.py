"""Secure data room: share datasets with named users, watermarked downloads, full audit trail."""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import audit
from ...config import get_settings
from ...db import get_db
from ...models import AuditLog, Layer, Share, User
from ...registry import abspath
from ...reports.watermark import bundle, stamp, watermark_geojson, watermark_png
from ...security import can
from ..deps import CurrentUser, require
from .layers import layer_to_dict, visible_layer_ids

router = APIRouter(prefix="/api/dataroom", tags=["dataroom"])

OPEN_LICENCE = re.compile(
    r"public domain|cc[ -]by|odbl|creative commons|copernicus|free of charge|free, full and open|"
    r"no restrictions",
    re.I,
)
RESTRICTED = re.compile(r"to confirm|permission required|not publicly|no robot|not redistribut|personal research", re.I)


def licence_check(licence: str) -> dict:
    if RESTRICTED.search(licence or ""):
        return {
            "ok": False,
            "reason": "Licence restricts or has not confirmed redistribution - confirm before sharing.",
        }
    if OPEN_LICENCE.search(licence or ""):
        return {"ok": True, "reason": "Open licence - share with attribution."}
    return {"ok": False, "reason": "Licence unclear - confirm before sharing."}


def dataset_out(db: Session, layer: Layer, user: CurrentUser) -> dict:
    d = layer_to_dict(layer)
    d["licence_check"] = licence_check(layer.source.licence)
    if can(user.role, "dataroom.share"):
        shares = db.scalars(select(Share).where(Share.layer_id == layer.id)).all()
        d["shares"] = [
            {
                "id": s.id,
                "username": db.get(User, s.user_id).username,
                "note": s.note,
                "created_at": s.created_at.isoformat(),
            }
            for s in shares
        ]
    d["formats"] = (
        (["geojson", "csv"] if layer.kind == "vector" else [])
        + (["png"] if layer.overlay_png else [])
        + (["tif"] if layer.raster_path else [])
    )
    return d


@router.get("/datasets")
def datasets(db: Session = Depends(get_db), user: CurrentUser = Depends(require("dataroom.view"))) -> dict:
    vis = visible_layer_ids(db, user)
    layers = db.scalars(select(Layer).order_by(Layer.group, Layer.name)).all()
    if vis is not None:
        layers = [x for x in layers if x.id in vis]
    audit.log(db, user.username, user.role, "view", "dataroom", "datasets", {"count": len(layers)})
    return {"datasets": [dataset_out(db, x, user) for x in layers]}


@router.get("/users")
def users(db: Session = Depends(get_db), _u: CurrentUser = Depends(require("dataroom.share"))) -> dict:
    us = db.scalars(select(User).where(User.active.is_(True)).order_by(User.id)).all()
    return {
        "users": [
            {"username": u.username, "display_name": u.display_name, "role": u.role, "organisation": u.organisation}
            for u in us
        ]
    }


class ShareIn(BaseModel):
    layer_id: str
    username: str
    note: str = ""
    acknowledge_licence: bool = False


@router.post("/shares")
def share(body: ShareIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require("dataroom.share"))) -> dict:
    layer = db.get(Layer, body.layer_id)
    target = db.scalar(select(User).where(User.username == body.username))
    if layer is None or target is None:
        raise HTTPException(404, "Dataset or user not found.")
    lc = licence_check(layer.source.licence)
    if not lc["ok"] and not body.acknowledge_licence:
        raise HTTPException(409, f"{lc['reason']} Licence: {layer.source.licence}")
    if db.scalar(select(Share).where(Share.layer_id == layer.id, Share.user_id == target.id)):
        raise HTTPException(409, "Already shared with this user.")
    s = Share(layer_id=layer.id, user_id=target.id, granted_by=user.id, note=body.note)
    db.add(s)
    db.flush()
    audit.log(
        db,
        user.username,
        user.role,
        "share",
        "layer",
        layer.id,
        {"with": target.username, "note": body.note, "licence_acknowledged": body.acknowledge_licence},
    )
    return {"id": s.id}


@router.delete("/shares/{share_id}")
def unshare(
    share_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(require("dataroom.share"))
) -> dict:
    s = db.get(Share, share_id)
    if s is None:
        raise HTTPException(404, "Share not found.")
    target = db.get(User, s.user_id)
    audit.log(
        db, user.username, user.role, "unshare", "layer", s.layer_id, {"with": target.username if target else None}
    )
    db.delete(s)
    return {"ok": True}


@router.get("/datasets/{layer_id}/download")
def download(
    layer_id: str,
    format: str = "geojson",
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require("dataroom.download")),
) -> Response:
    vis = visible_layer_ids(db, user)
    layer = db.get(Layer, layer_id)
    if layer is None or (vis is not None and layer_id not in vis):
        raise HTTPException(404, "Dataset not found or not shared with you.")
    mark = stamp(user.username, user.organisation)
    src = layer.source
    licence_note = (
        f"Dataset: {layer.name}\nSource: {src.name}\nPublisher: {src.publisher}\nURL: {src.url}\n"
        f"Licence / terms: {src.licence}\nAttribution: {layer.attribution}\n"
        f"Accessed: {src.accessed_at}\nShared through the GeoRevive data room. {mark}"
    )
    files: dict[str, bytes] = {}
    if format in ("geojson", "csv") and layer.kind == "vector":
        from ...ingest.process import read_vector

        gdf = read_vector(get_settings().path("gpkg"), layer.gpkg_table).to_crs("EPSG:4326")
        if format == "geojson":
            files[f"{layer.id}.geojson"] = json.dumps(
                watermark_geojson(json.loads(gdf.to_json(drop_id=True)), mark)
            ).encode()
        else:
            df = gdf.assign(
                lon=gdf.geometry.representative_point().x, lat=gdf.geometry.representative_point().y, _watermark=mark
            ).drop(columns="geometry")
            files[f"{layer.id}.csv"] = ("# " + mark + "\n" + df.to_csv(index=False)).encode("utf-8")
    elif format == "png" and layer.overlay_png:
        files[f"{layer.id}.png"] = watermark_png(abspath(layer.overlay_png), mark)
    elif format == "tif" and layer.raster_path:
        import rasterio
        from rasterio.io import MemoryFile

        with rasterio.open(abspath(layer.raster_path)) as srcr:
            prof = srcr.profile
            arr = srcr.read()
            with MemoryFile() as mem:
                with mem.open(**{**prof, "driver": "GTiff"}) as dst:
                    dst.write(arr)
                    dst.update_tags(WATERMARK=mark, SOURCE=src.name, LICENCE=src.licence)
                files[f"{layer.id}.tif"] = mem.read()
    else:
        raise HTTPException(400, "Format not available for this dataset.")
    data = bundle(files, mark, licence_note)
    audit.log(db, user.username, user.role, "download", "layer", layer.id, {"format": format, "watermark": mark})
    fn = f"{layer.id}_{user.username}.zip"
    return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@router.get("/activity")
def activity(db: Session = Depends(get_db), _u: CurrentUser = Depends(require("audit.view"))) -> dict:
    rows = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.action.in_(("view", "download", "share", "unshare")),
            AuditLog.object_type.in_(("layer", "dataroom")),
        )
        .order_by(AuditLog.id.desc())
        .limit(100)
    ).all()
    return {
        "entries": [
            {
                "at": r.at.isoformat(),
                "username": r.username,
                "role": r.role,
                "action": r.action,
                "object_id": r.object_id,
                "details": r.details,
            }
            for r in rows
        ]
    }
