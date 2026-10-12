"""Audit trail: every view, download, approval, edit, share and model run is logged."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .models import AuditLog

ACTIONS = (
    "login",
    "view",
    "download",
    "upload",
    "approve",
    "edit",
    "reject",
    "model_run",
    "weights_edit",
    "share",
    "unshare",
    "claim_report",
    "ingest",
    "reset",
    "scenario",
)


def log(
    db: Session,
    username: str,
    role: str,
    action: str,
    object_type: str,
    object_id: str | int,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    if action not in ACTIONS:
        raise ValueError(f"unknown audit action {action!r}")
    entry = AuditLog(
        username=username,
        role=role,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        details=details or {},
    )
    db.add(entry)
    db.flush()
    return entry
