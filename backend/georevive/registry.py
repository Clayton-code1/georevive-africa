"""Source Registry: provenance record for every dataset GeoRevive uses."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import SOURCE_STATUSES, Layer, Source, SourceFile


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def rel(path: Path) -> str:
    """Path relative to the project root, with forward slashes (portable)."""
    root = get_settings().root
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return Path(path).as_posix()


def abspath(relpath: str) -> Path:
    p = Path(relpath)
    return p if p.is_absolute() else get_settings().root / p


def upsert_source(db: Session, source_id: str, **fields: Any) -> Source:
    status = fields.get("status")
    if status is not None and status not in SOURCE_STATUSES:
        raise ValueError(f"invalid status {status!r}; expected one of {SOURCE_STATUSES}")
    src = db.get(Source, source_id)
    if src is None:
        src = Source(
            id=source_id,
            name=fields.get("name", source_id),
            publisher=fields.get("publisher", ""),
            url=fields.get("url", ""),
        )
        db.add(src)
    for k, v in fields.items():
        setattr(src, k, v)
    if src.accessed_at is None:
        src.accessed_at = datetime.now(UTC)
    db.flush()
    return src


def set_files(db: Session, src: Source, files: list[tuple[Path, str | None]]) -> None:
    """Replace the file list for a source. files: [(path, url)]."""
    src.files.clear()  # delete-orphan cascade removes the old rows
    db.flush()
    for path, url in files:
        path = Path(path)
        if not path.exists():
            continue
        src.files.append(SourceFile(path=rel(path), url=url, sha256=sha256_file(path), bytes=path.stat().st_size))
    db.flush()


def upsert_layer(db: Session, layer_id: str, **fields: Any) -> Layer:
    layer = db.get(Layer, layer_id)
    if layer is None:
        layer = Layer(id=layer_id, **fields)
        db.add(layer)
    else:
        for k, v in fields.items():
            setattr(layer, k, v)
    db.flush()
    return layer


def source_to_dict(src: Source, include_files: bool = True) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": src.id,
        "name": src.name,
        "publisher": src.publisher,
        "url": src.url,
        "urls_tried": src.urls_tried or [],
        "licence": src.licence,
        "licence_url": src.licence_url,
        "attribution": src.attribution,
        "accessed_at": src.accessed_at.isoformat() if src.accessed_at else None,
        "bbox": src.bbox,
        "record_count": src.record_count,
        "raster_size": src.raster_size,
        "status": src.status,
        "note": src.note,
        "usage": src.usage,
        "error": src.error,
        "how_to_obtain": src.how_to_obtain,
        "details": src.details or {},
        "is_inbox": src.is_inbox,
        "layers": [{"id": layer.id, "name": layer.name, "kind": layer.kind} for layer in src.layers],
    }
    if include_files:
        d["files"] = [{"path": f.path, "url": f.url, "sha256": f.sha256, "bytes": f.bytes} for f in src.files]
    return d


def all_sources(db: Session) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.is_inbox, Source.id)))
