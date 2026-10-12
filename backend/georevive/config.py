"""Configuration: config.yaml (pilot area, paths, options) plus .env (secrets)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def project_root() -> Path:
    env = os.environ.get("GEOREVIVE_ROOT")
    if env:
        return Path(env).resolve()
    # backend/georevive/config.py -> project root is two levels above backend/
    return Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    root: Path
    raw: dict[str, Any]
    bbox: tuple[float, float, float, float]
    pilot_name: str
    working_crs: str
    country_iso3: str
    country_iso2: str
    paths: dict[str, Path] = field(default_factory=dict)

    def path(self, key: str) -> Path:
        return self.paths[key]

    @property
    def secret_key(self) -> str:
        return os.environ.get("GEOREVIVE_SECRET_KEY", "")

    def section(self, name: str) -> dict[str, Any]:
        return self.raw.get(name, {}) or {}


def load_settings(root: Path | None = None) -> Settings:
    root = root or project_root()
    load_dotenv(root / ".env", override=False)
    cfg_path = Path(os.environ.get("GEOREVIVE_CONFIG", root / "config.yaml"))
    with open(cfg_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    pa = raw["pilot_area"]
    bbox = tuple(float(v) for v in pa["bbox"])
    if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ValueError(f"pilot_area.bbox must be [min_lon, min_lat, max_lon, max_lat], got {bbox}")
    paths = {k: (root / v).resolve() for k, v in (raw.get("paths") or {}).items()}
    return Settings(
        root=root,
        raw=raw,
        bbox=bbox,  # type: ignore[arg-type]
        pilot_name=pa.get("name", "Pilot area"),
        working_crs=pa.get("working_crs", "EPSG:32736"),
        country_iso3=pa.get("country_iso3", "ZWE"),
        country_iso2=pa.get("country_iso2", "ZW"),
        paths=paths,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def ensure_dirs(s: Settings) -> None:
    for key, p in s.paths.items():
        if key in ("database", "gpkg"):
            p.parent.mkdir(parents=True, exist_ok=True)
        else:
            p.mkdir(parents=True, exist_ok=True)
    (s.path("processed_dir") / "overlays").mkdir(parents=True, exist_ok=True)
    (s.path("reports_dir") / "generated").mkdir(parents=True, exist_ok=True)
