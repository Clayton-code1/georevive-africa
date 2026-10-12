"""Lineage helpers: every derived output carries a list of entries that resolve to a
registered source (and, for rescued facts, a page and a bounding box)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .models import Layer, Source


def source_ref(src: Source) -> dict[str, Any]:
    return {
        "kind": "source",
        "source_id": src.id,
        "name": src.name,
        "publisher": src.publisher,
        "url": src.url,
        "licence": src.licence,
        "accessed_at": src.accessed_at.isoformat() if src.accessed_at else None,
    }


def layer_ref(layer: Layer) -> dict[str, Any]:
    return {"kind": "layer", "layer_id": layer.id, "name": layer.name, "source_id": layer.source_id}


def page_ref(document_id: str, page_no: int, bbox: list[int] | None = None) -> dict[str, Any]:
    return {"kind": "page", "document_id": document_id, "page_no": page_no, "bbox": bbox}


def resolve(db: Session, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand layer references into their source references, de-duplicated."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(e: dict[str, Any]) -> None:
        key = repr(sorted(e.items()))
        if key not in seen:
            seen.add(key)
            out.append(e)

    for e in entries:
        if e.get("kind") != "source":
            add(e)
        if e.get("kind") == "layer":
            layer = db.get(Layer, e["layer_id"])
            if layer is not None:
                add(source_ref(layer.source))
                for d in layer.derived_from or []:
                    if d.get("kind") == "source":
                        s = db.get(Source, d["source_id"])
                        if s is not None:
                            add(source_ref(s))
        elif e.get("kind") == "source":
            s = db.get(Source, e["source_id"])
            add(source_ref(s) if s is not None else e)
    return out
