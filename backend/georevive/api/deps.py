"""FastAPI dependencies: current user and permission checks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import can, decode_token


@dataclass
class CurrentUser:
    id: int
    username: str
    display_name: str
    role: str
    organisation: str


def _token_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    # Allow ?token= for direct file links (downloads, images) opened in a new tab.
    return request.query_params.get("token")


def current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please sign in again.") from e
    user = db.scalar(select(User).where(User.username == payload.get("sub")))
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown or inactive user.")
    return CurrentUser(user.id, user.username, user.display_name, user.role, user.organisation)


def require_token(permission: str) -> Callable[..., dict]:
    """Permission check from the signed token alone, with NO database session. Used by the demo
    reset/scenario endpoints, which replace the database file (Windows cannot replace an open file)."""

    def dep(request: Request) -> dict:
        token = _token_from_request(request)
        if not token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
        try:
            payload = decode_token(token)
        except jwt.PyJWTError as e:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please sign in again.") from e
        if not can(payload.get("role", ""), permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role cannot do this ({permission}).")
        return {"username": payload["sub"], "role": payload["role"]}

    return dep


def require_any(*permissions: str) -> Callable[..., CurrentUser]:
    def dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if not any(can(user.role, p) for p in permissions):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role ({user.role}) cannot do this.")
        return user

    return dep


def require(permission: str) -> Callable[..., CurrentUser]:
    def dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if not can(user.role, permission):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Your role ({user.role}) does not have permission for this action ({permission}).",
            )
        return user

    return dep
