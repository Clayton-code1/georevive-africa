"""End-to-end master demonstration path through the API, on cached SYNTHETIC data, offline.

Data Sources -> Data rescue (upload, enhance, OCR, facts, review) -> Map (rescued facts) ->
Prospectivity -> Claim check PDF -> Data room (share, investor view, watermarked download) -> Audit log."""

import io
import time
import zipfile

import cv2
import numpy as np
import pytest

LINES = [
    "SYNTHETIC TEST PAGE - NOT REAL DATA",
    "The Jumbo Mine lies in Bulawayan greenstone",
    "on a quartz reef along a shear zone.",
    "Grades of 12 dwt per ton were recorded.",
]


def synthetic_scan() -> bytes:
    h, w = 900, 1500
    img = np.full((h, w, 3), 236, np.uint8)
    for i, t in enumerate(LINES):
        cv2.putText(img, t, (60, 140 + i * 110), cv2.FONT_HERSHEY_DUPLEX, 1.5, (30, 30, 30), 3, cv2.LINE_AA)
    yy, xx = np.mgrid[0:h, 0:w]
    img = (img * (1 - 0.35 * (xx / w))[..., None]).astype(np.uint8)  # uneven lighting
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


@pytest.fixture()
def world(temp_root):
    from georevive.config import get_settings
    from tests.synthetic_world import build

    return build(get_settings())


def test_master_path(world, client, auth):
    t0 = time.time()
    adm, geo, inv, miner = auth("admin"), auth("geologist"), auth("investor"), auth("miner")

    # 1. Data Sources
    src = client.get("/api/sources", headers=adm).json()
    assert any(s["id"] == "syn_world" for s in src["sources"])

    # 2. Data rescue: upload with provenance; enhancement + OCR + extraction
    files = {"file": ("synthetic_scan.png", synthetic_scan(), "image/png")}
    form = {"source_name": "SYNTHETIC scan", "publisher": "tests", "licence": "CC BY 4.0", "permission": "yes"}
    r = client.post("/api/rescue/upload", data={**form, "permission": "no"}, files=files, headers=geo)
    assert r.status_code == 400  # no permission -> refused
    r = client.post("/api/rescue/upload", data=form, files=files, headers=geo)
    assert r.status_code == 200, r.text
    doc = r.json()
    page_id = doc["pages"][0]["id"]
    page = client.get(f"/api/rescue/pages/{page_id}", headers=geo).json()
    assert [s["name"] for s in page["steps"]][3] == "illumination"
    assert page["quality_after"]["uniformity"] > page["quality_before"]["uniformity"]
    types = {f["type"] for f in page["facts"]}
    assert {"mine", "assay"} <= types, f"facts found: {[(f['type'], f['value']) for f in page['facts']]}"
    for step in ("original", "illumination", "binarize"):
        assert client.get(f"/api/rescue/pages/{page_id}/image/{step}", headers=geo).status_code == 200
    # the uploaded document is registered in the Source Registry with its licence
    sid = doc["source"]["id"]
    assert client.get(f"/api/sources/{sid}", headers=adm).json()["licence"] == "CC BY 4.0"

    # review: analyst cannot, geologist can; only approved facts reach the geodatabase
    mine = next(f for f in page["facts"] if f["type"] == "mine")
    assert mine["lon"] is not None, (mine["value"], mine["geocode_method"])
    assay = next(f for f in page["facts"] if f["type"] == "assay")
    assert (
        client.post(
            f"/api/rescue/facts/{mine['id']}/review", json={"action": "approve"}, headers=auth("analyst")
        ).status_code
        == 403
    )
    layers = {x["id"]: x for x in client.get("/api/layers", headers=geo).json()["layers"]}
    assert "rescued_facts" not in layers or layers["rescued_facts"]["feature_count"] == 0
    assert (
        client.post(f"/api/rescue/facts/{mine['id']}/review", json={"action": "approve"}, headers=geo).json()["status"]
        == "approved"
    )
    edited = client.post(
        f"/api/rescue/facts/{assay['id']}/review",
        json={"action": "edit", "value": "12 dwt per ton (checked)", "comment": "SYNTHETIC"},
        headers=geo,
    )
    assert edited.json()["status"] == "edited" and edited.json()["reviews"][0]["before"]["value"] == assay["value"]

    # 3. Map: the rescued facts layer exists and links back to the page
    gj = client.get("/api/layers/rescued_facts/geojson", headers=geo).json()
    assert gj["features"], "approved, located facts should be on the map"
    props = gj["features"][0]["properties"]
    assert props["document_id"] == doc["id"] and props["page_no"] == 1

    # 4. Prospectivity
    run = client.post("/api/prospect/run", json={"method": "fuzzy"}, headers=geo).json()
    assert len(run["targets"]) == 10 and run["targets"][0]["explanation"]
    cell = client.get(f"/api/prospect/runs/{run['id']}/cell?lon=31.15&lat=-17.775", headers=geo).json()
    assert cell["score"] is not None and cell["contributions"]

    # 5. Claim check report
    t = run["targets"][0]
    rep = client.post(
        "/api/claims", json={"name": "SYNTHETIC claim", "lon": t["lon"], "lat": t["lat"]}, headers=miner
    ).json()
    pdf = client.get(f"/api/claims/{rep['id']}/pdf", headers=miner)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"

    # 6. Data room
    assert (
        client.post(
            "/api/dataroom/shares", json={"layer_id": "prospectivity_gold", "username": "investor"}, headers=adm
        ).status_code
        == 200
    )
    ds = client.get("/api/dataroom/datasets", headers=inv).json()["datasets"]
    assert [d["id"] for d in ds] == ["prospectivity_gold"]
    dl = client.get("/api/dataroom/datasets/prospectivity_gold/download?format=png", headers=inv)
    assert dl.status_code == 200
    assert "investor" in zipfile.ZipFile(io.BytesIO(dl.content)).read("WATERMARK.txt").decode()

    # 7. Audit trail
    acts = {(e["username"], e["action"]) for e in client.get("/api/audit?limit=500", headers=adm).json()["entries"]}
    for need in [
        ("geologist", "upload"),
        ("geologist", "approve"),
        ("geologist", "edit"),
        ("geologist", "model_run"),
        ("miner", "claim_report"),
        ("miner", "download"),
        ("admin", "share"),
        ("investor", "download"),
    ]:
        assert need in acts, need
    assert time.time() - t0 < 240, "master path must complete in under 4 minutes"
