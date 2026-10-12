"""SYNTHETIC test fixtures. These are invented values used ONLY by automated tests.
They are never written to the real data/ folder and never shown in the app."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np

SYNTHETIC_TAG = "SYNTHETIC - test fixture, not real data"


def square(lon: float, lat: float, d: float = 0.05) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[lon, lat], [lon + d, lat], [lon + d, lat + d], [lon, lat + d], [lon, lat]]],
    }


def write_geojson(path: Path, features: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "name": SYNTHETIC_TAG, "features": features}), encoding="utf-8"
    )
    return path


def mrds_zip(path: Path, rows: int = 1200, drop_column: str | None = None) -> Path:
    cols = [
        "dep_id",
        "mrds_id",
        "site_name",
        "latitude",
        "longitude",
        "country",
        "commod1",
        "commod2",
        "commod3",
        "dev_stat",
        "url",
    ]
    if drop_column:
        cols.remove(drop_column)
    buf = io.StringIO()
    buf.write(",".join(cols) + "\n")
    rng = np.random.default_rng(0)
    for i in range(rows):
        zw = i % 3 == 0
        vals = {
            "dep_id": str(i),
            "mrds_id": f"SYN{i}",
            "site_name": f"SYNTHETIC site {i}",
            "latitude": f"{-17.8 + rng.uniform(-0.2, 0.2):.4f}" if zw else "45.0",
            "longitude": f"{31.1 + rng.uniform(-0.3, 0.3):.4f}" if zw else "-100.0",
            "country": "Zimbabwe" if zw else "United States",
            "commod1": "Gold" if i % 2 == 0 else "Copper",
            "commod2": "",
            "commod3": "",
            "dev_stat": "Past Producer",
            "url": "",
        }
        buf.write(",".join(vals[c] for c in cols) + "\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mrds.csv", buf.getvalue())
    return path


def pdf_with_text(path: Path, pages: int, text: str) -> Path:
    import fitz

    doc = fitz.open()
    for i in range(pages):
        p = doc.new_page()
        p.insert_text((72, 72), f"{SYNTHETIC_TAG}. {text} Page {i + 1}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path
