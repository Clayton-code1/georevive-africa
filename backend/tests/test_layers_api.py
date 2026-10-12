import geopandas as gpd
from shapely.geometry import Point

from georevive.ingest.process import write_vector
from georevive.models import Share, User
from georevive.registry import upsert_layer, upsert_source


def _seed_layer(temp_root):
    from georevive.config import get_settings
    from georevive.db import session_scope

    gpkg = get_settings().path("gpkg")
    gdf = gpd.GeoDataFrame({"name": ["SYNTHETIC point"]}, geometry=[Point(31.1, -17.8)], crs="EPSG:4326")
    write_vector(gdf, gpkg, "syn_points")
    with session_scope() as db:
        upsert_source(
            db,
            "syn_src",
            name="SYNTHETIC source",
            publisher="Test",
            url="https://example.org",
            licence="CC BY 4.0",
            status="downloaded",
        )
        upsert_layer(
            db,
            "syn_points",
            source_id="syn_src",
            name="SYNTHETIC points",
            kind="vector",
            gpkg_table="syn_points",
            attribution="Test",
            group="occurrences",
        )


def test_layers_visibility_and_geojson(client, auth, temp_root):
    _seed_layer(temp_root)
    r = client.get("/api/layers", headers=auth("analyst"))
    assert r.status_code == 200
    assert [x["id"] for x in r.json()["layers"]] == ["syn_points"]
    gj = client.get("/api/layers/syn_points/geojson", headers=auth("analyst")).json()
    assert gj["features"][0]["properties"]["name"] == "SYNTHETIC point"
    lin = client.get("/api/layers/syn_points/lineage", headers=auth("analyst")).json()
    assert any(e.get("url") == "https://example.org" for e in lin["lineage"])

    # Investor: nothing until shared
    inv = auth("investor")
    assert client.get("/api/layers", headers=inv).json()["layers"] == []
    assert client.get("/api/layers/syn_points/geojson", headers=inv).status_code == 404
    from sqlalchemy import select

    from georevive.db import session_scope

    with session_scope() as db:
        uid = db.scalar(select(User.id).where(User.username == "investor"))
        aid = db.scalar(select(User.id).where(User.username == "admin"))
        db.add(Share(layer_id="syn_points", user_id=uid, granted_by=aid))
    assert [x["id"] for x in client.get("/api/layers", headers=inv).json()["layers"]] == ["syn_points"]
    # Miner: only base-map/context layers (for drawing claims), not occurrence data
    r = client.get("/api/layers", headers=auth("miner"))
    assert r.status_code == 200 and r.json()["layers"] == []
