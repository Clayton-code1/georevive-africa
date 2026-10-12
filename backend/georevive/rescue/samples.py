"""Demo sample pages: single pages rendered from openly licensed documents already in the
Source Registry (e.g. public-domain Internet Archive items). Each sample keeps its provenance.

Build them after ingestion with:  python -m georevive.rescue.samples
The page choices live in config.yaml under rescue.sample_pages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ..config import get_settings


def samples_dir() -> Path:
    p = get_settings().path("data_dir") / "samples"
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_samples() -> list[dict[str, Any]]:
    f = samples_dir() / "samples.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))


def sample_path(sample_id: str) -> Path | None:
    for s in list_samples():
        if s["id"] == sample_id:
            p = samples_dir() / s["file"]
            return p if p.exists() else None
    return None


def build() -> list[dict[str, Any]]:
    from ..db import session_scope
    from ..models import Source
    from ..registry import abspath
    from .enhance import save_png
    from .pipeline import render_page

    cfg = get_settings().section("rescue").get("sample_pages", []) or []
    out = []
    with session_scope() as db:
        for c in cfg:
            src = db.get(Source, c["source_id"])
            if src is None or src.status not in ("downloaded", "partial"):
                print(f"skip {c['id']}: source {c['source_id']} not downloaded")
                continue
            pdf = next((f for f in src.files if f.path.lower().endswith(".pdf") and c["match"] in f.path), None)
            if pdf is None:
                print(f"skip {c['id']}: no PDF matching '{c['match']}' in {c['source_id']}")
                continue
            img = render_page(abspath(pdf.path), int(c["page"]))
            fn = f"{c['id']}.png"
            save_png(samples_dir() / fn, img)
            meta = {
                "id": c["id"],
                "title": c["title"],
                "file": fn,
                "source_id": src.id,
                "source_name": src.name,
                "document_file": pdf.path,
                "page": int(c["page"]),
                "licence": c.get("licence", src.licence),
                "url": c.get("url", pdf.url),
                "description": c.get("description", ""),
                "width": int(img.shape[1]),
                "height": int(img.shape[0]),
            }
            out.append(meta)
            print(f"sample {c['id']}: {c['title']} (page {c['page']})")
    (samples_dir() / "samples.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    build()
    sys.exit(0)
