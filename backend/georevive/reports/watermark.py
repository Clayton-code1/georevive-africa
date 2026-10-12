"""Watermark every download with the user and the time."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def stamp(username: str, organisation: str = "") -> str:
    t = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    who = f"{username}" + (f" ({organisation})" if organisation else "")
    return f"GeoRevive - downloaded by {who} on {t} - do not redistribute"


def watermark_pdf(src: Path, text: str) -> bytes:
    import fitz

    with fitz.open(src) as doc:
        for page in doc:
            r = page.rect
            page.insert_text(
                (r.width * 0.12, r.height * 0.62),
                text,
                fontsize=11,
                rotate=0,
                color=(0.72, 0.47, 0.12),
                fill_opacity=0.35,
                stroke_opacity=0.35,
                morph=(fitz.Point(r.width / 2, r.height / 2), fitz.Matrix(-30)),
            )
            page.insert_text((24, r.height - 10), text, fontsize=6.5, color=(0.4, 0.4, 0.4))
        doc.set_metadata({**doc.metadata, "keywords": text, "subject": text})
        return doc.tobytes(garbage=3, deflate=True)


def watermark_png(src: Path, text: str) -> bytes:
    from PIL import Image, ImageDraw

    im = Image.open(src).convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    step = max(120, im.size[1] // 6)
    for y in range(20, im.size[1], step):
        d.text((10, y), text, fill=(30, 58, 95, 150))
    out = Image.alpha_composite(im, overlay)
    buf = io.BytesIO()
    out.save(buf, format="PNG", pnginfo=_pnginfo(text))
    return buf.getvalue()


def _pnginfo(text: str):
    from PIL.PngImagePlugin import PngInfo

    p = PngInfo()
    p.add_text("Watermark", text)
    return p


def watermark_geojson(fc: dict[str, Any], text: str) -> dict[str, Any]:
    fc = dict(fc)
    fc["watermark"] = text
    feats = []
    for f in fc.get("features", []):
        f = dict(f)
        f["properties"] = {**(f.get("properties") or {}), "_watermark": text}
        feats.append(f)
    fc["features"] = feats
    return fc


def bundle(files: dict[str, bytes], text: str, licence_note: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
        z.writestr("WATERMARK.txt", text + "\n")
        z.writestr("LICENCE_AND_SOURCE.txt", licence_note + "\n")
        z.writestr("manifest.json", json.dumps({"watermark": text, "files": list(files)}, indent=2))
    return buf.getvalue()
