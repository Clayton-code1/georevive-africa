"""Manual inbox (data/inbox/): PDFs and scans the team obtains from the Geological Survey, libraries
or its own scanning. Each file needs its provenance: a sidecar <file>.source.yaml with the fields
below (the upload screen writes it for you; the CLI asks when run interactively)."""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from ...registry import set_files, upsert_source
from ..base import Connector, Outcome

DOC_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
REQUIRED_FIELDS = ("source_name", "publisher", "licence", "permission")
FIELD_PROMPTS = {
    "source_name": "Title of the document or map",
    "publisher": "Publisher / holder (e.g. Zimbabwe Geological Survey)",
    "url": "Where it came from (URL or library/shelf reference)",
    "licence": "Licence or terms (e.g. public domain, CC BY 4.0, 'permission from ZGS by email 2026-10-01')",
    "permission": "Do we have permission to use it in GeoRevive? (yes/no)",
    "notes": "Notes (optional)",
}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:50] or "file"


def sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".source.yaml")


def read_meta(path: Path) -> dict[str, Any] | None:
    sc = sidecar(path)
    if not sc.exists():
        return None
    return yaml.safe_load(sc.read_text(encoding="utf-8")) or {}


def write_meta(path: Path, meta: dict[str, Any]) -> None:
    sidecar(path).write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8")


def missing_fields(meta: dict[str, Any] | None) -> list[str]:
    if not meta:
        return list(REQUIRED_FIELDS)
    return [f for f in REQUIRED_FIELDS if not str(meta.get(f, "")).strip()]


def inbox_source_id(path: Path) -> str:
    return "inbox_" + slug(path.stem)


def register_inbox_file(db: Session, path: Path, meta: dict[str, Any] | None) -> str:
    """Create/refresh the Source Registry row for one inbox file. Returns its source id."""
    sid = inbox_source_id(path)
    miss = missing_fields(meta)
    perm = str((meta or {}).get("permission", "")).strip().lower()
    if miss:
        status, error = "needs_manual_request", f"Provenance details missing: {', '.join(miss)}."
    elif perm not in ("yes", "y", "true"):
        status, error = "needs_manual_request", "Permission to use this file has not been confirmed."
    else:
        status, error = "downloaded", None
    meta = meta or {}
    src = upsert_source(
        db,
        sid,
        name=meta.get("source_name") or path.name,
        publisher=meta.get("publisher") or "unknown (provide details)",
        url=meta.get("url") or f"data/inbox/{path.name}",
        licence=meta.get("licence") or "licence to confirm",
        accessed_at=datetime.fromtimestamp(path.stat().st_mtime, UTC),
        status=status,
        error=error,
        note=meta.get("notes") or "Document added through the manual inbox.",
        usage="Data-rescue document (enhancement, OCR, fact extraction).",
        how_to_obtain=None
        if status == "downloaded"
        else "Enter the source, publisher, licence and permission on the Data Rescue upload screen, or edit "
        f"{sidecar(path).name} next to the file and re-run ingestion with --source inbox.",
        is_inbox=True,
        record_count=None,
        details={"uploaded_by": meta.get("uploaded_by"), "permission": meta.get("permission")},
    )
    set_files(db, src, [(path, meta.get("url"))] + ([(sidecar(path), None)] if sidecar(path).exists() else []))
    return sid


class InboxConnector(Connector):
    id = "inbox"
    name = "Manual inbox (data/inbox/)"
    publisher = "GeoRevive team"
    url = "data/inbox/"
    licence = "Per file (entered on upload)"
    note = "Documents and scans added by the team."
    usage = "Data rescue."

    def files(self) -> list[Path]:
        root = self.s.path("inbox_dir")
        root.mkdir(parents=True, exist_ok=True)
        return sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in DOC_EXT)

    def fetch(self) -> None:  # pragma: no cover - not used (run() is overridden)
        pass

    def validate(self) -> None:
        for p in self.files():
            if p.stat().st_size == 0:
                raise ValueError(f"{p.name} is empty")

    def run(self, db: Session) -> Outcome:
        o = self.outcome
        files = self.files()
        interactive = sys.stdin is not None and sys.stdin.isatty()
        done, pending = [], []
        for p in files:
            meta = read_meta(p)
            if missing_fields(meta) and interactive:
                print(f"\nInbox file: {p.name} - please enter its provenance (press Enter to skip a field)")
                meta = dict(meta or {})
                for k, prompt in FIELD_PROMPTS.items():
                    if not str(meta.get(k, "")).strip():
                        meta[k] = input(f"  {prompt}: ").strip()
                write_meta(p, meta)
            sid = register_inbox_file(db, p, meta)
            (done if not missing_fields(meta) else pending).append(sid)
        o.status = "downloaded"
        o.record_count = len(files)
        o.details = {"registered": done, "missing_details": pending}
        o.note_extra = f"{len(files)} file(s) in the inbox; {len(pending)} still need source/licence details."
        # summary row for the inbox itself
        upsert_source(
            db,
            self.id,
            name=self.name,
            publisher=self.publisher,
            url=self.url,
            licence=self.licence,
            status="downloaded",
            record_count=len(files),
            note=(self.note + " " + o.note_extra).strip(),
            usage=self.usage,
            details=o.details,
            accessed_at=datetime.now(UTC),
            is_inbox=True,
            error=None,
        )
        return o
