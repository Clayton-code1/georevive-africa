"""Presenter tools: reset to the clean state and jump to the complete scenario.

These endpoints authenticate from the signed token only (no database session is opened before the
restore), because restoring replaces the database file and Windows cannot replace a file that is open."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ... import audit
from ...db import session_scope
from ...demo import scenario, snapshots
from ..deps import require_token

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/status")
def status(_u: dict = Depends(require_token("demo.control"))) -> dict:
    return {n: snapshots.info(n) for n in snapshots.NAMES}


def _restore(name: str, user: dict, action: str) -> dict:
    try:
        snapshots.restore(name)
    except FileNotFoundError as e:
        raise HTTPException(409, str(e)) from e
    with session_scope() as db:
        audit.log(db, user["username"], user["role"], action, "demo", name)
    return {"ok": True, "state": name}


@router.post("/reset")
def reset(user: dict = Depends(require_token("demo.control"))) -> dict:
    return _restore("clean", user, "reset")


@router.post("/scenario")
def load_scenario(user: dict = Depends(require_token("demo.control"))) -> dict:
    if not snapshots.exists("complete"):
        try:
            scenario.build()
        except Exception as e:
            raise HTTPException(500, f"Could not build the scenario: {e}") from e
    return _restore("complete", user, "scenario")
