"""Claim report generation, watermarking and data-room permissions on the SYNTHETIC world."""

import io
import zipfile

import pytest


@pytest.fixture()
def world(temp_root):
    from georevive.config import get_settings
    from tests.synthetic_world import build

    return build(get_settings())


def test_claim_report_pdf(world, client, auth):
    import fitz

    h = auth("analyst")
    assert client.post("/api/prospect/run", json={"method": "fuzzy"}, headers=h).status_code == 200
    r = client.post(
        "/api/claims",
        json={"name": "SYNTHETIC claim", "lon": 31.15, "lat": -17.775, "side_m": 600},
        headers=auth("miner"),
    )
    assert r.status_code == 200, r.text
    rep = r.json()
    s = rep["summary"]
    assert s["district"] == "SYNTHETIC District B"
    assert s["geology"][0]["class"].startswith("favourable")
    assert s["occurrences"], "nearby synthetic occurrences should be listed"
    assert s["prospectivity"]["mean"] is not None
    pdf = client.get(f"/api/claims/{rep['id']}/pdf", headers=auth("miner"))
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    with fitz.open(stream=pdf.content, filetype="pdf") as doc:
        text = "".join(p.get_text() for p in doc)
    for must in (
        "Claim Check",
        "field verification",
        "Data sources and licences",
        "downloaded by miner",
        "SYNTHETIC District B",
        "Technical appendix",
    ):
        assert must in text, must
    # another miner-level user cannot fetch someone else's report; the analyst did not create it
    assert client.get(f"/api/claims/{rep['id']}/pdf", headers=auth("analyst")).status_code == 404


def test_claim_outside_pilot_rejected(world, client, auth):
    r = client.post("/api/claims", json={"lon": 10.0, "lat": 10.0}, headers=auth("miner"))
    assert r.status_code == 400 and "outside the pilot area" in r.json()["detail"]


def test_dataroom_share_watermark_and_audit(world, client, auth):
    adm, inv = auth("admin"), auth("investor")
    assert client.get("/api/dataroom/datasets", headers=inv).json()["datasets"] == []
    # investor cannot share; geologist cannot share
    assert (
        client.post(
            "/api/dataroom/shares", json={"layer_id": "faults", "username": "investor"}, headers=inv
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/dataroom/shares", json={"layer_id": "faults", "username": "investor"}, headers=auth("geologist")
        ).status_code
        == 403
    )
    r = client.post("/api/dataroom/shares", json={"layer_id": "mrds_occurrences", "username": "investor"}, headers=adm)
    assert r.status_code == 200, r.text
    ds = client.get("/api/dataroom/datasets", headers=inv).json()["datasets"]
    assert [d["id"] for d in ds] == ["mrds_occurrences"]
    # not shared -> not downloadable
    assert client.get("/api/dataroom/datasets/faults/download?format=geojson", headers=inv).status_code == 404
    dl = client.get("/api/dataroom/datasets/mrds_occurrences/download?format=geojson", headers=inv)
    assert dl.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(dl.content))
    assert "WATERMARK.txt" in z.namelist() and "LICENCE_AND_SOURCE.txt" in z.namelist()
    wm = z.read("WATERMARK.txt").decode()
    assert "investor" in wm and "UTC" in wm
    assert b"_watermark" in z.read("mrds_occurrences.geojson")
    log = client.get("/api/audit", headers=adm).json()["entries"]
    acts = [(e["username"], e["action"], e["object_id"]) for e in log]
    assert ("investor", "download", "mrds_occurrences") in acts
    assert ("admin", "share", "mrds_occurrences") in acts
    assert any(u == "investor" and a == "view" for u, a, _ in acts)


def test_sharing_unclear_licence_needs_acknowledgement(world, client, auth, db):
    from georevive.models import Source

    src = db.get(Source, "syn_world")
    src.licence = "licence to confirm"
    db.commit()
    adm = auth("admin")
    r = client.post("/api/dataroom/shares", json={"layer_id": "faults", "username": "investor"}, headers=adm)
    assert r.status_code == 409
    r = client.post(
        "/api/dataroom/shares",
        json={"layer_id": "faults", "username": "investor", "acknowledge_licence": True},
        headers=adm,
    )
    assert r.status_code == 200


def test_weights_edit_permission(world, client, auth):
    body = {"weights": {"dist_fault": 0.5, "host_rock": 0.5}, "comment": "SYNTHETIC test"}
    assert client.put("/api/prospect/weights", json=body, headers=auth("analyst")).status_code == 403
    assert client.put("/api/prospect/weights", json=body, headers=auth("geologist")).status_code == 200
    cfg = client.get("/api/prospect/config", headers=auth("analyst")).json()
    assert cfg["weights"] == body["weights"] and cfg["weights_last_edited"]["username"] == "geologist"
    assert client.post("/api/prospect/run", json={"method": "fuzzy"}, headers=auth("miner")).status_code == 403
