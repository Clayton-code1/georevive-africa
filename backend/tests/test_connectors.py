"""validate() and pure helpers of every connector, using SYNTHETIC fixtures (no network)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from georevive.ingest.base import ValidationError
from tests.synthetic import SYNTHETIC_TAG, mrds_zip, pdf_with_text, square, write_geojson


class FakeHttp:
    """Stands in for PoliteHttp so tests never touch the network."""

    ua = "test"
    log: list = []

    def robots_allowed(self, url):
        return True

    def note(self, url, result):
        self.log.append({"url": url, "result": result})

    def get(self, url, **kw):  # pragma: no cover - should not be called
        raise AssertionError("network access in a unit test")


@pytest.fixture()
def settings(temp_root):
    from georevive.config import get_settings

    return get_settings()


def make(cls, settings):
    return cls(settings, http=FakeHttp())


# --- geoBoundaries ---------------------------------------------------------------
def test_geoboundaries_validate(settings):
    from georevive.ingest.connectors.geoboundaries import GeoBoundariesConnector

    c = make(GeoBoundariesConnector, settings)
    for lvl in c.LEVELS:
        write_geojson(
            c.raw_dir / f"geoBoundaries-ZWE-{lvl}.geojson",
            [
                {
                    "type": "Feature",
                    "properties": {"shapeName": f"SYNTHETIC {lvl}", "shapeID": "x"},
                    "geometry": square(31.0, -17.9),
                }
            ],
        )
    c.validate()
    write_geojson(
        c.raw_dir / "geoBoundaries-ZWE-ADM2.geojson",
        [{"type": "Feature", "properties": {"name": "no shapeName"}, "geometry": square(31.0, -17.9)}],
    )
    with pytest.raises(ValidationError):
        c.validate()


# --- OSM -------------------------------------------------------------------------
def test_osm_validate_and_frames(settings):
    from georevive.ingest.connectors.osm import OsmConnector, overpass_query

    c = make(OsmConnector, settings)
    data = {
        "note": SYNTHETIC_TAG,
        "elements": [
            {"type": "node", "id": 1, "lat": -17.8, "lon": 31.05, "tags": {"place": "town", "name": "SYNTHETIC town"}},
            {
                "type": "way",
                "id": 2,
                "tags": {"highway": "primary", "name": "SYNTHETIC road"},
                "geometry": [{"lat": -17.8, "lon": 31.0}, {"lat": -17.7, "lon": 31.1}],
            },
            {"type": "node", "id": 3, "lat": -17.75, "lon": 31.2, "tags": {"man_made": "mineshaft"}},
        ],
    }
    (c.raw_dir / "overpass.json").write_text(json.dumps(data), encoding="utf-8")
    c.validate()
    roads, rivers, places, mines = OsmConnector.to_frames(data)
    assert len(roads) == 1 and rivers is None and len(places) == 1 and len(mines) == 1
    (c.raw_dir / "overpass.json").write_text(json.dumps({"elements": []}), encoding="utf-8")
    with pytest.raises(ValidationError):
        c.validate()
    q = overpass_query((30.75, -18.05, 31.5, -17.55), "roads")
    assert "-18.05,30.75,-17.55,31.5" in q and "highway" in q and "waterway" not in q


# --- MRDS ------------------------------------------------------------------------
def test_mrds_validate(settings):
    from georevive.ingest.connectors.usgs_mrds import UsgsMrdsConnector, is_commodity

    c = make(UsgsMrdsConnector, settings)
    mrds_zip(c.raw_dir / "mrds-csv.zip")
    c.validate()
    mrds_zip(c.raw_dir / "mrds-csv.zip", drop_column="latitude")
    with pytest.raises(ValidationError):
        c.validate()
    mrds_zip(c.raw_dir / "mrds-csv.zip", rows=10)
    with pytest.raises(ValidationError):
        c.validate()
    assert is_commodity({"commod1": "Copper", "commod2": "Gold, Silver"}, "gold")
    assert not is_commodity({"commod1": "Copper"}, "gold")


def test_mrds_process_counts(settings):
    from georevive.ingest.connectors.usgs_mrds import UsgsMrdsConnector

    c = make(UsgsMrdsConnector, settings)
    mrds_zip(c.raw_dir / "mrds-csv.zip", rows=1200)
    c.process()
    d = c.outcome.details
    assert d["zimbabwe_records"] == 400
    assert d["zimbabwe_gold_records"] == 200
    assert 0 < d["pilot_records"] <= 400


# --- USGS Africa -----------------------------------------------------------------
def test_usgs_africa_validate(settings):
    import geopandas as gpd
    from shapely.geometry import Point

    from georevive.ingest.connectors.usgs_africa import UsgsAfricaMineralsConnector

    c = make(UsgsAfricaMineralsConnector, settings)
    with pytest.raises(ValidationError):
        c.validate()
    out = c.raw_dir / "unzipped"
    out.mkdir(parents=True)
    gpd.GeoDataFrame(
        {"Country": ["Zimbabwe"], "DsgName": [SYNTHETIC_TAG]}, geometry=[Point(31.1, -17.8)], crs="EPSG:4326"
    ).to_file(out / "Mineral_Facilities.shp")
    import zipfile

    with zipfile.ZipFile(c.raw_dir / "package.zip", "w") as z:
        z.writestr("readme.txt", SYNTHETIC_TAG)
    c.validate()


# --- Sentinel-2 ------------------------------------------------------------------
def _write_stack(c, grid, median: float = 0.15):
    rng = np.random.default_rng(1)
    bands = [
        np.full(grid.shape, median, dtype="float32") + rng.normal(0, 0.01, grid.shape).astype("float32")
        for _ in range(7)
    ]
    bands.append(np.full(grid.shape, 4, dtype="float32"))  # SCL = vegetation class (valid)
    c._write_stack(np.stack(bands), grid, c.raw_dir / "s2_bands.tif")


def test_sentinel2_validate_and_indices(settings):
    from georevive.ingest.connectors.sentinel2 import Sentinel2Connector, alteration_indices, choose_scene_group
    from georevive.ingest.process import pilot_grid

    c = make(Sentinel2Connector, settings)
    grid = pilot_grid((31.0, -17.9, 31.05, -17.85), "EPSG:32736", 100)
    _write_stack(c, grid)
    c.validate()
    _write_stack(c, grid, median=50.0)
    with pytest.raises(ValidationError):
        c.validate()
    b = {k: np.array([0.1], dtype="float32") for k in ("B02", "B03", "B04", "B08", "B8A", "B11", "B12")}
    b["B04"] = np.array([0.2], dtype="float32")
    idx = alteration_indices(b)
    assert idx["iron_oxide"][0] == pytest.approx(2.0, rel=1e-4)
    assert idx["clay"][0] == pytest.approx(1.0, rel=1e-4)
    assert idx["ferrous"][0] == pytest.approx(1.0 + 0.5, rel=1e-4)
    items = [
        {
            "id": "a",
            "properties": {"datetime": "2025-08-01T08:00:00Z", "eo:cloud_cover": 5},
            "geometry": square(30.0, -19.0, 2.0),
        },
        {
            "id": "b",
            "properties": {"datetime": "2025-08-11T08:00:00Z", "eo:cloud_cover": 1},
            "geometry": square(30.0, -19.0, 0.5),
        },  # low cloud but does not cover the bbox
    ]
    best = choose_scene_group(items, (30.75, -18.05, 31.5, -17.55))
    assert best is not None and best[1] == "2025-08-01"


# --- Copernicus DEM --------------------------------------------------------------
def test_dem_tiles_and_validate(settings):
    from georevive.ingest.connectors.cop_dem import CopDemConnector, slope_degrees, tiles_for_bbox
    from georevive.ingest.process import pilot_grid, write_cog

    t = tiles_for_bbox((30.75, -18.05, 31.5, -17.55))
    assert "Copernicus_DSM_COG_10_S18_00_E030_00_DEM" in t and "Copernicus_DSM_COG_10_S19_00_E031_00_DEM" in t
    assert len(t) == 4
    c = make(CopDemConnector, settings)
    grid = pilot_grid((31.0, -17.9, 31.05, -17.85), "EPSG:32736", 30)
    dem = np.full(grid.shape, 1450.0, dtype="float32")
    write_cog(dem, grid, c.raw_dir / "dem_30m.tif")
    c.validate()
    write_cog(np.full(grid.shape, 9000.0, dtype="float32"), grid, c.raw_dir / "dem_30m.tif")
    with pytest.raises(ValidationError):
        c.validate()
    # a 45-degree plane: rises 30 m per 30 m cell
    plane = np.tile(np.arange(10, dtype="float32") * 30, (10, 1))
    assert np.allclose(slope_degrees(plane, 30)[2:-2, 2:-2], 45.0, atol=0.5)


# --- ASTER -----------------------------------------------------------------------
def test_aster_needs_credentials(settings, monkeypatch):
    from georevive.ingest.connectors.aster import AsterConnector

    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    c = make(AsterConnector, settings)
    c.fetch()
    assert c.outcome.status == "needs_credentials"
    assert "urs.earthdata.nasa.gov" in c.outcome.how_to_obtain


# --- BGS -------------------------------------------------------------------------
def test_bgs_report_validate(settings):
    from georevive.ingest.connectors.bgs_harare import BgsHarareReportConnector

    c = make(BgsHarareReportConnector, settings)
    pdf_with_text(c.inbox() / "OR26047.pdf", 6, "Digitisation of the Harare map.")
    c.validate()
    pdf_with_text(c.inbox() / "OR26047.pdf", 6, "Some other report.")
    with pytest.raises(ValidationError):
        c.validate()


def test_bgs_map_validate(settings):
    import geopandas as gpd
    from shapely.geometry import LineString, shape

    from georevive.ingest.connectors.bgs_harare import BgsHarareMapConnector

    c = make(BgsHarareMapConnector, settings)
    c.fetch()
    assert c.outcome.status == "needs_manual_request"
    assert "enquiries@bgs.ac.uk" in c.outcome.how_to_obtain
    g = c.inbox() / "synthetic.gpkg"
    gpd.GeoDataFrame({"LEX_RCS": ["SYN-GRST"]}, geometry=[shape(square(31.0, -17.9))], crs="EPSG:4326").to_file(
        g, layer="bedrock_polygons"
    )
    with pytest.raises(ValidationError):
        c.validate()
    gpd.GeoDataFrame(
        {"TYPE": ["fault"]}, geometry=[LineString([(31.0, -17.9), (31.1, -17.8)])], crs="EPSG:4326"
    ).to_file(g, layer="faults")
    c.validate()


# --- Regional geology ------------------------------------------------------------
def test_regional_geology_validate(settings):
    from georevive.ingest.connectors.regional_geology import RegionalGeologyConnector

    c = make(RegionalGeologyConnector, settings)
    write_geojson(
        c.raw_dir / "macrostrat_small.geojson",
        [
            {
                "type": "Feature",
                "properties": {"map_id": 1, "lith": "volcanic-sedimentary"},
                "geometry": square(31.0, -17.9),
            }
        ],
    )
    c.validate()
    write_geojson(
        c.raw_dir / "macrostrat_small.geojson",
        [{"type": "Feature", "properties": {"map_id": 1}, "geometry": square(31.0, -17.9)}],
    )
    with pytest.raises(ValidationError):
        c.validate()


# --- Historical scans ------------------------------------------------------------
def test_internet_archive_rules_and_validate(settings):
    from georevive.ingest.connectors.historical_scans import InternetArchiveConnector, is_open_item, is_relevant

    assert is_open_item({"possible-copyright-status": "NOT_IN_COPYRIGHT"})[0]
    assert is_open_item({"licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/"})[0]
    assert not is_open_item({"licenseurl": ""})[0]
    assert is_relevant("The gold mines of the world ... Rhodesia ...")
    assert not is_relevant("Pre-historic Mesopotamia")
    c = make(InternetArchiveConnector, settings)
    pdf_with_text(c.raw_dir / "syn" / "syn.pdf", 2, "Rhodesia gold.")
    c.write_manifest({"downloaded": [{"identifier": "syn", "pdf": "syn/syn.pdf"}]})
    c.validate()


def test_manual_request_connectors(settings):
    from georevive.ingest.connectors.historical_scans import HathiTrustConnector, ZgsBulletinsConnector

    for cls in (HathiTrustConnector, ZgsBulletinsConnector):
        c = make(cls, settings)
        c.fetch()
        assert c.outcome.status == "needs_manual_request"
        assert c.outcome.how_to_obtain


def test_georoc_needs_credentials(settings, monkeypatch):
    from georevive.ingest.connectors.geochem import GeorocConnector

    monkeypatch.delenv("GEOROC_API_KEY", raising=False)
    c = make(GeorocConnector, settings)
    c.fetch()
    assert c.outcome.status == "needs_credentials"


def test_earthchem_validate(settings):
    from georevive.ingest.connectors.geochem import EarthChemConnector

    c = make(EarthChemConnector, settings)
    (c.raw_dir / "earthchem_pilot.json").write_text(json.dumps([{"note": SYNTHETIC_TAG}]), encoding="utf-8")
    c.validate()


# --- Inbox -----------------------------------------------------------------------
def test_inbox_registration(settings, db):
    from georevive.ingest.connectors.inbox import missing_fields, register_inbox_file, write_meta
    from georevive.models import Source

    p = settings.path("inbox_dir") / "synthetic_scan.png"
    p.write_bytes(b"SYNTHETIC")
    sid = register_inbox_file(db, p, None)
    assert db.get(Source, sid).status == "needs_manual_request"
    meta = {"source_name": "SYNTHETIC scan", "publisher": "Test", "licence": "CC BY 4.0", "permission": "yes"}
    assert missing_fields(meta) == []
    write_meta(p, meta)
    register_inbox_file(db, p, meta)
    src = db.get(Source, sid)
    assert src.status == "downloaded" and src.licence == "CC BY 4.0"
    assert len(src.files) == 2  # file + sidecar, both checksummed


# --- Base: failures are recorded, never invented ---------------------------------
def test_failed_fetch_is_recorded(settings, db):
    from georevive.ingest.base import Connector
    from georevive.models import Source

    class Boom(Connector):
        id = "boom"
        name = "SYNTHETIC failing source"
        publisher = "Test"
        url = "https://example.invalid"

        def fetch(self):
            raise ConnectionError("simulated outage")

        def validate(self):
            pass

    Boom(settings, http=FakeHttp()).run(db)
    src = db.get(Source, "boom")
    assert src.status == "failed"
    assert "simulated outage" in src.error
    assert src.record_count is None and src.layers == []


# --- ESA WorldCover --------------------------------------------------------------
def test_worldcover_tiles_and_validate(settings):
    from georevive.ingest.connectors.worldcover import WorldCoverConnector, tile_names
    from georevive.ingest.process import pilot_grid, write_cog

    assert tile_names((30.75, -18.05, 31.5, -17.55)) == ["S21E030", "S18E030"]
    c = make(WorldCoverConnector, settings)
    grid = pilot_grid((31.0, -17.9, 31.05, -17.85), "EPSG:32736", 30)
    lc = np.full(grid.shape, 30, dtype="float32")  # SYNTHETIC: all grassland
    lc[:5, :5] = 50
    write_cog(lc, grid, c.raw_dir / "worldcover_30m.tif")
    c.validate()
    lc[0, 0] = 7  # not a WorldCover class
    write_cog(lc, grid, c.raw_dir / "worldcover_30m.tif")
    with pytest.raises(ValidationError):
        c.validate()


def test_sentinel2_boa_offset_rules():
    from georevive.ingest.connectors.sentinel2 import boa_offset

    rb = {"scale": 0.0001, "offset": -0.1}
    # Earth Search v1: offset already removed from the DNs, even though raster:bands lists -0.1
    assert boa_offset("earth-search", {"properties": {"earthsearch:boa_offset_applied": True}}, rb) == 0.0
    assert boa_offset("earth-search", {"properties": {}}, rb) == -0.1
    assert boa_offset("planetary", {"properties": {"s2:processing_baseline": "05.10"}}, {}) == -0.1
    assert boa_offset("planetary", {"properties": {"s2:processing_baseline": "03.01"}}, {}) == 0.0
