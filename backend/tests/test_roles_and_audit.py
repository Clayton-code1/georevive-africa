from georevive.security import PERMISSIONS, can, hash_password, verify_password


def test_permission_matrix_roles():
    # Investor: only the data room and the (shared-only) map
    assert can("investor", "dataroom.view")
    assert can("investor", "dataroom.download")
    assert not can("investor", "sources.view")
    assert not can("investor", "facts.review")
    assert not can("investor", "model.run")
    # Miner: claim reports only
    miner_perms = {p for p, roles in PERMISSIONS.items() if "miner" in roles}
    assert miner_perms == {"claims.create"}
    # Geologist reviews facts and edits weights, but cannot share or read the audit log
    assert can("geologist", "facts.review")
    assert can("geologist", "model.edit_weights")
    assert not can("geologist", "dataroom.share")
    assert not can("geologist", "audit.view")
    # Analyst cannot review facts or edit weights
    assert not can("analyst", "facts.review")
    assert not can("analyst", "model.edit_weights")
    # Admin has everything
    assert all(can("admin", p) for p in PERMISSIONS)


def test_password_hashing():
    h = hash_password("s3cret")
    assert h != "s3cret"
    assert verify_password("s3cret", h)
    assert not verify_password("wrong", h)


def test_login_and_me(client, auth):
    h = auth("geologist")
    r = client.get("/api/auth/me", headers=h)
    assert r.status_code == 200
    assert r.json()["role"] == "geologist"
    bad = client.post("/api/auth/login", json={"username": "geologist", "password": "nope"})
    assert bad.status_code == 401


def test_unauthenticated_and_forbidden(client, auth):
    assert client.get("/api/sources").status_code == 401
    assert client.get("/api/sources", headers=auth("investor")).status_code == 403
    assert client.get("/api/sources", headers=auth("miner")).status_code == 403
    assert client.get("/api/sources", headers=auth("analyst")).status_code == 200
    assert client.get("/api/audit", headers=auth("geologist")).status_code == 403


def test_audit_log_records_logins_and_views(client, auth):
    h = auth("analyst")
    client.get("/api/sources", headers=h)
    entries = client.get("/api/audit", headers=auth("admin")).json()["entries"]
    actions = [(e["username"], e["action"]) for e in entries]
    assert ("analyst", "login") in actions
    assert ("analyst", "view") in actions


def test_demo_quick_login_local_only(client):
    r = client.get("/api/auth/demo-accounts")
    assert r.status_code == 200 and r.json()["enabled"] is True
    r = client.post("/api/auth/demo-login", json={"username": "miner"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "miner"


def test_unknown_audit_action_rejected(db):
    import pytest

    from georevive import audit

    with pytest.raises(ValueError):
        audit.log(db, "x", "admin", "hack", "thing", 1)
