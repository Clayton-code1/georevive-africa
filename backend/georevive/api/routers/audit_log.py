from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import get_db
from ...models import AuditLog
from ..deps import CurrentUser, require

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require("audit.view")),
    action: str | None = None,
    username: str | None = None,
    limit: int = Query(200, le=2000),
) -> dict:
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if action:
        q = q.where(AuditLog.action == action)
    if username:
        q = q.where(AuditLog.username == username)
    rows = db.scalars(q).all()
    return {
        "entries": [
            {
                "id": r.id,
                "at": r.at.isoformat(),
                "username": r.username,
                "role": r.role,
                "action": r.action,
                "object_type": r.object_type,
                "object_id": r.object_id,
                "details": r.details,
            }
            for r in rows
        ]
    }
