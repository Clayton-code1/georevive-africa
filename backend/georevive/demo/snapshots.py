"""Demo state snapshots.

* clean    - the state right after ingestion (no documents, model runs, claims or shares)
* complete - the finished end state of the master demo path (fallback if something fails live)

A snapshot is a copy of the database, the GeoPackage and the folders holding derived outputs.
Raw downloads are never touched."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from ..config import get_settings
from ..db import reset_engine

NAMES = ("clean", "complete")


def _items() -> dict[str, Path]:
    s = get_settings()
    return {
        "app.db": s.path("database"),
        "pilot.gpkg": s.path("gpkg"),
        "rescue": s.path("rescue_dir"),
        "prospect": s.path("processed_dir") / "prospect",
        "generated": s.path("reports_dir") / "generated",
        "inbox": s.path("inbox_dir"),
    }


def snap_dir(name: str) -> Path:
    return get_settings().path("snapshots_dir") / name


def exists(name: str) -> bool:
    return (snap_dir(name) / "snapshot.json").exists()


def info(name: str) -> dict | None:
    p = snap_dir(name) / "snapshot.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _copy(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=False)
    elif src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _rm(p: Path) -> None:
    if p.is_dir():

        def onerr(func, path, _exc):  # read-only originals in rescue/ (Windows)
            import os
            import stat

            os.chmod(path, stat.S_IWRITE)
            func(path)

        shutil.rmtree(p, onerror=onerr)
    elif p.exists():
        p.unlink()


def save(name: str, note: str = "") -> Path:
    assert name in NAMES
    from ..db import get_engine

    eng = get_engine()
    with eng.connect() as c:  # flush WAL into the main db file before copying
        c.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    d = snap_dir(name)
    if d.exists():
        _rm(d)
    d.mkdir(parents=True)
    for key, src in _items().items():
        _copy(src, d / key)
    (d / "snapshot.json").write_text(
        json.dumps({"name": name, "created": datetime.now(UTC).isoformat(), "note": note}), encoding="utf-8"
    )
    return d


def restore(name: str) -> None:
    if not exists(name):
        raise FileNotFoundError(
            f"No '{name}' snapshot. "
            + ("Run ingestion first." if name == "clean" else "Run: python -m georevive.demo build-scenario")
        )
    d = snap_dir(name)
    reset_engine()
    for key, dst in _items().items():
        for suffix in ("-wal", "-shm"):
            side = dst.with_name(dst.name + suffix)
            if side.exists():
                side.unlink()
        if dst.exists():
            _rm(dst)
        src = d / key
        if src.exists():
            _copy(src, dst)
        elif key not in ("app.db", "pilot.gpkg"):
            dst.mkdir(parents=True, exist_ok=True)
    from ..prospect import engine

    engine._STACK_CACHE.clear()
