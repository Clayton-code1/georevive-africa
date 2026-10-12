from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import audit
from ...config import get_settings
from ...db import get_db
from ...models import User
from ...security import ROLE_LABELS, create_token, permissions_for, verify_password
from ..deps import CurrentUser, current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


class LoginIn(BaseModel):
    username: str
    password: str


class DemoLoginIn(BaseModel):
    username: str


def _user_out(u: User | CurrentUser) -> dict:
    return {
        "username": u.username,
        "display_name": u.display_name,
        "role": u.role,
        "role_label": ROLE_LABELS.get(u.role, u.role),
        "organisation": u.organisation,
        "permissions": permissions_for(u.role),
    }


def _issue(db: Session, user: User, method: str) -> dict:
    audit.log(db, user.username, user.role, "login", "user", user.username, {"method": method})
    return {"token": create_token(user.username, user.role), "user": _user_out(user)}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect username or password.")
    return _issue(db, user, "password")


def quick_login_enabled() -> bool:
    return bool(get_settings().section("security").get("demo_quick_login", False))


@router.get("/demo-accounts")
def demo_accounts(request: Request, db: Session = Depends(get_db)) -> dict:
    host = request.client.host if request.client else ""
    enabled = quick_login_enabled() and host in LOCAL_HOSTS
    users = db.scalars(select(User).where(User.active.is_(True)).order_by(User.id)).all() if enabled else []
    return {"enabled": enabled, "accounts": [_user_out(u) for u in users]}


@router.post("/demo-login")
def demo_login(body: DemoLoginIn, request: Request, db: Session = Depends(get_db)) -> dict:
    host = request.client.host if request.client else ""
    if not quick_login_enabled() or host not in LOCAL_HOSTS:
        raise HTTPException(403, "One-click demo sign-in is disabled. Use your username and password.")
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not user.active:
        raise HTTPException(404, "Unknown demo account.")
    return _issue(db, user, "demo_quick_login")


@router.get("/me")
def me(user: CurrentUser = Depends(current_user)) -> dict:
    return _user_out(user)
