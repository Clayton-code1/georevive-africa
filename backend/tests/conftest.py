"""Test fixtures. Every test runs in an isolated temporary project root, so tests
never touch the real data/ folder or database."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_PASSWORDS = {
    "GEOREVIVE_ADMIN_PASSWORD": "test-admin-pw",
    "GEOREVIVE_GEOLOGIST_PASSWORD": "test-geo-pw",
    "GEOREVIVE_ANALYST_PASSWORD": "test-analyst-pw",
    "GEOREVIVE_INVESTOR_PASSWORD": "test-investor-pw",
    "GEOREVIVE_MINER_PASSWORD": "test-miner-pw",
}


def _reset_caches() -> None:
    from georevive.config import get_settings
    from georevive.db import reset_engine

    reset_engine()
    get_settings.cache_clear()


@pytest.fixture()
def temp_root(tmp_path, monkeypatch) -> Path:
    shutil.copy(REPO_ROOT / "config.yaml", tmp_path / "config.yaml")
    monkeypatch.setenv("GEOREVIVE_ROOT", str(tmp_path))
    monkeypatch.delenv("GEOREVIVE_CONFIG", raising=False)
    monkeypatch.setenv("GEOREVIVE_SECRET_KEY", "test-secret-key-not-for-production-0123456789")
    for k, v in TEST_PASSWORDS.items():
        monkeypatch.setenv(k, v)
    _reset_caches()
    from georevive.config import ensure_dirs, get_settings
    from georevive.db import init_db

    ensure_dirs(get_settings())
    init_db()
    yield tmp_path
    _reset_caches()


@pytest.fixture()
def db(temp_root):
    from georevive.db import session_scope

    with session_scope() as s:
        yield s


@pytest.fixture()
def client(temp_root):
    from fastapi.testclient import TestClient

    from georevive.api.app import create_app

    with TestClient(create_app()) as c:
        yield c


def login(client, username: str) -> dict:
    pw = TEST_PASSWORDS[f"GEOREVIVE_{username.upper()}_PASSWORD"]
    r = client.post("/api/auth/login", json={"username": username, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture()
def auth(client):
    return lambda username: login(client, username)
