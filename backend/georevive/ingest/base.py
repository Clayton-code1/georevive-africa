"""Common connector interface: fetch() -> validate() -> process() -> register().

Rules enforced here:
* a failure is recorded with its reason, never replaced by made-up data;
* every downloaded file is checksummed (SHA-256) in the Source Registry;
* re-running is safe: downloads are cached and registry rows are upserted.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Layer
from ..registry import rel, set_files, upsert_layer, upsert_source
from .http import PoliteHttp, RobotsDisallowed


class ValidationError(Exception):
    pass


@dataclass
class LayerSpec:
    id: str
    name: str
    kind: str  # vector | raster
    group: str
    attribution: str
    gpkg_table: str | None = None
    raster_path: Path | None = None
    overlay_png: Path | None = None
    overlay_bounds: list[float] | None = None
    geometry_type: str | None = None
    feature_count: int | None = None
    legend: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    derived_from: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Outcome:
    status: str = "failed"
    files: list[tuple[Path, str | None]] = field(default_factory=list)
    record_count: int | None = None
    raster_size: str | None = None
    bbox: list[float] | None = None
    error: str | None = None
    how_to_obtain: str | None = None
    note_extra: str = ""
    licence: str | None = None  # override when the source itself reports its licence
    licence_url: str | None = None
    url: str | None = None  # override with the URL actually used
    details: dict[str, Any] = field(default_factory=dict)
    layers: list[LayerSpec] = field(default_factory=list)


class Connector:
    # --- metadata (override in subclasses) ---
    id: ClassVar[str] = ""
    name: ClassVar[str] = ""
    publisher: ClassVar[str] = ""
    url: ClassVar[str] = ""
    licence: ClassVar[str] = "licence to confirm"
    licence_url: ClassVar[str | None] = None
    attribution: ClassVar[str] = ""
    note: ClassVar[str] = ""
    usage: ClassVar[str] = ""
    optional: ClassVar[bool] = False

    def __init__(self, settings: Settings, http: PoliteHttp | None = None, force: bool = False) -> None:
        self.s = settings
        ing = settings.section("ingest")
        self.http = http or PoliteHttp(
            ing.get("user_agent", "GeoRevive"),
            ing.get("request_timeout_s", 60),
            ing.get("min_seconds_between_requests", 1.0),
        )
        self.force = force
        self.outcome = Outcome()

    # --- paths ---
    @property
    def raw_dir(self) -> Path:
        p = self.s.path("raw_dir") / self.id
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def processed_dir(self) -> Path:
        return self.s.path("processed_dir")

    @property
    def overlay_dir(self) -> Path:
        p = self.processed_dir / "overlays"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def gpkg(self) -> Path:
        return self.s.path("gpkg")

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return self.s.bbox

    def manifest_path(self) -> Path:
        return self.raw_dir / "manifest.json"

    def write_manifest(self, data: dict[str, Any]) -> None:
        self.manifest_path().write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def read_manifest(self) -> dict[str, Any]:
        p = self.manifest_path()
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def manual_dir(self, sub: str) -> Path:
        """data/inbox/<sub>/ - where the team drops files that may only be downloaded by a person
        (e.g. robots.txt forbids automated access, or a bot-protection wall)."""
        p = self.s.path("inbox_dir") / sub
        p.mkdir(parents=True, exist_ok=True)
        return p

    def adopt_manual(self, src: Path, dest: Path) -> Path:
        """Copy a manually downloaded file into raw_dir (idempotent)."""
        import shutil

        if not dest.exists() or dest.stat().st_size != src.stat().st_size or self.force:
            shutil.copy2(src, dest)
        return dest

    # --- the interface ---
    def fetch(self) -> None:
        """Download (or locate cached) raw files into raw_dir and fill self.outcome."""
        raise NotImplementedError

    def validate(self) -> None:
        """Check the raw files are what we expect. Raise ValidationError on problems."""
        raise NotImplementedError

    def process(self) -> None:
        """Clip/reproject into the pilot GeoPackage / COGs and describe layers."""

    def register(self, db: Session) -> None:
        o = self.outcome
        from ..models import Source

        # 'Accessed' is when the data was actually fetched: a re-run that only reprocessed cached files keeps
        # the earlier access time (and the earlier URL log).
        prev = db.get(Source, self.id)
        log = self.http.log[-40:]
        only_cache = bool(log) and all(e["result"].startswith(("cached", "repaired")) for e in log)
        accessed = prev.accessed_at if (only_cache and prev is not None and prev.accessed_at) else datetime.now(UTC)
        if only_cache and prev is not None and prev.urls_tried:
            log = prev.urls_tried
        src = upsert_source(
            db,
            self.id,
            name=self.name,
            publisher=self.publisher,
            url=o.url or self.url,
            urls_tried=log,
            licence=o.licence or self.licence,
            licence_url=o.licence_url or self.licence_url,
            attribution=self.attribution,
            accessed_at=accessed,
            bbox=o.bbox,
            record_count=o.record_count,
            raster_size=o.raster_size,
            status=o.status,
            note=(self.note + (" " + o.note_extra if o.note_extra else "")).strip(),
            usage=self.usage,
            error=o.error,
            how_to_obtain=o.how_to_obtain,
            details=o.details,
        )
        set_files(db, src, o.files)
        keep = {spec.id for spec in o.layers}
        for layer in list(src.layers):
            if layer.id not in keep:
                db.delete(layer)
        for spec in o.layers:
            upsert_layer(
                db,
                spec.id,
                source_id=self.id,
                name=spec.name,
                group=spec.group,
                kind=spec.kind,
                gpkg_table=spec.gpkg_table,
                raster_path=rel(spec.raster_path) if spec.raster_path else None,
                overlay_png=rel(spec.overlay_png) if spec.overlay_png else None,
                overlay_bounds=spec.overlay_bounds,
                geometry_type=spec.geometry_type,
                feature_count=spec.feature_count,
                attribution=spec.attribution,
                legend=spec.legend,
                style=spec.style,
                description=spec.description,
                derived_from=[{"kind": "source", "source_id": self.id}] + spec.derived_from,
            )
        db.flush()

    def run(self, db: Session) -> Outcome:
        """Fetch, validate, process and register; failures are recorded, not raised."""
        try:
            self.fetch()
            if self.outcome.status in ("downloaded", "partial"):
                self.validate()
                self.process()
        except RobotsDisallowed as e:
            self.outcome.status = "failed"
            self.outcome.error = f"Not fetched: {e}. GeoRevive never scrapes sites that forbid it."
        except ValidationError as e:
            self.outcome.status = "failed"
            self.outcome.error = f"Downloaded but failed validation: {e}"
        except Exception as e:  # record and continue with the other sources
            self.outcome.status = "failed" if not self.outcome.layers else "partial"
            self.outcome.error = f"{type(e).__name__}: {e}"[:1500]
            self.outcome.details["traceback"] = traceback.format_exc()[-3000:]
        self.register(db)
        return self.outcome


def existing_layers(db: Session) -> dict[str, Layer]:
    return {layer.id: layer for layer in db.query(Layer).all()}
