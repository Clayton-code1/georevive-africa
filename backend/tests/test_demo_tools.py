"""Presenter tools through the API: reset restores the clean state; only the admin may use them."""

from georevive.demo import snapshots


def test_reset_via_api_restores_clean_state(client, auth):
    snapshots.save("clean", "SYNTHETIC test")
    adm = auth("admin")
    # create some demo data after the clean snapshot
    from georevive.db import session_scope
    from georevive.models import ClaimReport

    with session_scope() as db:
        db.add(ClaimReport(username="miner", name="SYNTHETIC", polygon={}, summary={}, pdf_path=""))
    assert client.post("/api/demo/reset", headers=auth("geologist")).status_code == 403
    r = client.post("/api/demo/reset", headers=adm)
    assert r.status_code == 200, r.text  # must work while the app is running (Windows file locks)
    with session_scope() as db:
        assert db.query(ClaimReport).count() == 0
    entries = client.get("/api/audit", headers=auth("admin")).json()["entries"]
    assert any(e["action"] == "reset" for e in entries)


def test_scenario_without_snapshot_reports_clearly(client, auth):
    r = client.post("/api/demo/reset", headers=auth("admin"))
    assert r.status_code == 409 and "Run ingestion first" in r.json()["detail"]
