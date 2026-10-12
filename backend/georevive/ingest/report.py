"""Data Report: reports/DATA_SOURCES.md, reports/data_sources.json, and a terminal summary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import get_settings
from ..registry import all_sources, source_to_dict

STATUS_LABEL = {
    "downloaded": "Downloaded",
    "partial": "Partial",
    "failed": "Failed",
    "needs_manual_request": "Needs manual request",
    "needs_credentials": "Needs credentials",
}


def _size(d: dict) -> str:
    parts = []
    if d.get("record_count") is not None:
        parts.append(f"{d['record_count']:,} records")
    if d.get("raster_size"):
        parts.append(d["raster_size"])
    return "; ".join(parts) or "-"


def _md_escape(s: str | None) -> str:
    return (s or "-").replace("|", "\\|").replace("\n", " ")


def build_markdown(sources: list[dict], generated: str, pilot_name: str, bbox: list[float]) -> str:
    L: list[str] = []
    L.append("# GeoRevive Africa - Data Sources Report")
    L.append("")
    L.append(f"_Generated automatically on {generated} by `python -m georevive.ingest`. Do not edit by hand._")
    L.append("")
    L.append(f"**Pilot area:** {pilot_name} - bounding box (lon/lat) `{bbox}`")
    L.append("")
    L.append(
        "Rules: only open or published data we are allowed to access; robots.txt, licences and rate limits are "
        "respected; nothing is invented. A failed source stays failed - no gap is filled with made-up records."
    )
    L.append("")
    L.append(
        "**Raw data is not redistributed.** The GeoRevive repository contains code, configuration, documentation and "
        "generated reports only. No downloaded dataset, derived data layer or scanned document is included. Each "
        "dataset stays under its publisher's licence (listed below). To reproduce the data, run "
        "`python -m georevive.ingest --all`, which downloads open data from the original publishers and records "
        "checksums so you can confirm you have the same files."
    )
    L.append("")
    counts: dict[str, int] = {}
    for d in sources:
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    L.append("## Summary")
    L.append("")
    L.append(" · ".join(f"**{STATUS_LABEL.get(k, k)}:** {v}" for k, v in sorted(counts.items())))
    L.append("")
    L.append("| Source | What was obtained | URL | Licence | Accessed (UTC) | Records / raster | Status |")
    L.append("|---|---|---|---|---|---|---|")
    for d in sources:
        obtained = ", ".join(layer["name"] for layer in d["layers"]) or (
            f"{len(d['files'])} file(s)" if d["files"] else "nothing"
        )
        L.append(
            f"| {_md_escape(d['name'])} | {_md_escape(obtained)} | {d['url']} | {_md_escape(d['licence'])} | "
            f"{(d['accessed_at'] or '-')[:16].replace('T', ' ')} | {_md_escape(_size(d))} | "
            f"{STATUS_LABEL.get(d['status'], d['status'])} |"
        )
    L.append("")

    failed = [d for d in sources if d["status"] in ("failed", "partial")]
    L.append("## What failed and why")
    L.append("")
    if not failed:
        L.append("Nothing failed.")
    for d in failed:
        L.append(f"- **{d['name']}** ({STATUS_LABEL[d['status']]}): {d['error'] or 'see details'}")
        if d.get("how_to_obtain"):
            L.append(f"  - What to do: {d['how_to_obtain'].replace(chr(10), ' ')}")
    L.append("")

    action = [d for d in sources if d["status"] in ("needs_manual_request", "needs_credentials")]
    L.append("## Needs a manual request or credentials - and how to get it")
    L.append("")
    if not action:
        L.append("Nothing outstanding.")
    for d in action:
        L.append(f"### {d['name']}")
        L.append("")
        L.append(f"- Status: **{STATUS_LABEL[d['status']]}**")
        L.append(f"- Publisher: {d['publisher']}")
        L.append(f"- Where: {d['url']}")
        if d.get("error"):
            L.append(f"- Why: {d['error']}")
        if d.get("how_to_obtain"):
            L.append("- How to obtain:")
            L.append("")
            for line in d["how_to_obtain"].splitlines():
                L.append(f"    {line}")
        L.append("")

    tbc = [d for d in sources if "to confirm" in (d["licence"] or "").lower()]
    L.append("## Licence terms marked 'to confirm' (check by hand)")
    L.append("")
    if not tbc:
        L.append("None.")
    for d in tbc:
        L.append(f"- **{d['name']}** - {d['licence']}")
    L.append("")

    L.append("## Details per source")
    L.append("")
    for d in sources:
        L.append(f"### {d['name']}")
        L.append("")
        L.append(f"- **ID:** `{d['id']}` · **Status:** {STATUS_LABEL.get(d['status'], d['status'])}")
        L.append(f"- **Publisher:** {d['publisher']}")
        L.append(f"- **URL:** {d['url']}")
        L.append(f"- **Licence / terms:** {d['licence']}" + (f" ({d['licence_url']})" if d.get("licence_url") else ""))
        if d.get("attribution"):
            L.append(f"- **Attribution:** {d['attribution']}")
        L.append(f"- **Accessed:** {d['accessed_at']}")
        L.append(f"- **Coverage (bbox):** {d['bbox'] or '-'}")
        L.append(f"- **Records / raster size:** {_size(d)}")
        L.append(f"- **What it is:** {d['note']}")
        L.append(f"- **How GeoRevive uses it:** {d['usage']}")
        if d.get("error"):
            L.append(f"- **Problem:** {d['error']}")
        if d["files"]:
            L.append("- **Files (SHA-256):**")
            for f in d["files"]:
                L.append(f"    - `{f['path']}` ({f['bytes']:,} bytes) `{f['sha256']}`")
        if d.get("urls_tried"):
            L.append("- **URLs tried:**")
            for u in d["urls_tried"][-12:]:
                L.append(f"    - {u['url']} -> {u['result']}")
        L.append("")
    return "\n".join(L)


def generate(db: Session) -> tuple[Path, Path]:
    s = get_settings()
    out = s.path("reports_dir")
    out.mkdir(parents=True, exist_ok=True)
    srcs = [source_to_dict(x) for x in all_sources(db)]
    for d in srcs:
        d.get("details", {}).pop("traceback", None)
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    md = build_markdown(srcs, generated, s.pilot_name, list(s.bbox))
    md_path = out / "DATA_SOURCES.md"
    md_path.write_text(md, encoding="utf-8")
    js_path = out / "data_sources.json"
    js_path.write_text(
        json.dumps(
            {"generated": generated, "pilot_area": {"name": s.pilot_name, "bbox": list(s.bbox)}, "sources": srcs},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return md_path, js_path


def terminal_summary(db: Session) -> str:
    rows = [source_to_dict(x, include_files=False) for x in all_sources(db)]
    w = max(len(r["id"]) for r in rows) if rows else 10
    lines = ["", "GeoRevive data ingestion - summary", "=" * 78]
    for r in rows:
        lines.append(f"{r['id']:<{w}}  {STATUS_LABEL.get(r['status'], r['status']):<22} {_size(r)}")
    lines.append("=" * 78)
    act = [r for r in rows if r["status"] in ("failed", "needs_manual_request", "needs_credentials", "partial")]
    if act:
        lines.append("Needs attention:")
        for r in act:
            lines.append(f"  - {r['id']}: {(r['error'] or '')[:110]}")
    lines.append("Full report: reports/DATA_SOURCES.md  (and the Data Sources page in the app)")
    return "\n".join(lines)
