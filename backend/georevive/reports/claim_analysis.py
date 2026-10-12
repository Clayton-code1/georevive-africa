"""Everything a claim check report says about a polygon, computed from registered layers only."""

from __future__ import annotations

from typing import Any

import numpy as np
from shapely.geometry import Point, shape
from shapely.ops import transform as stransform
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import DISCLAIMER
from ..config import get_settings
from ..ingest.process import gpkg_tables, read_raster, read_vector
from ..lineage import source_ref
from ..models import Layer, ModelRun
from ..registry import abspath

NEAR_KM = 5.0


def _txt(v: Any, default: str = "") -> str:
    """Text value or default (pandas gives NaN, which is truthy, for missing names)."""
    if v is None or (isinstance(v, float) and v != v) or str(v).strip().lower() in ("", "nan", "none"):
        return default
    return str(v)


def _to_utm(geom, crs: str):
    from pyproj import Transformer

    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    return stransform(lambda x, y, z=None: t.transform(x, y), geom)


def square_around(lon: float, lat: float, side_m: float, crs: str) -> dict[str, Any]:
    from pyproj import Transformer
    from shapely.geometry import box, mapping

    fwd = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    inv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    x, y = fwd.transform(lon, lat)
    h = side_m / 2
    poly = stransform(lambda xx, yy, z=None: inv.transform(xx, yy), box(x - h, y - h, x + h, y + h))
    return mapping(poly)


def validate_polygon(geojson: dict[str, Any]):
    g = shape(geojson)
    if g.geom_type not in ("Polygon", "MultiPolygon") or g.is_empty:
        raise ValueError("The claim must be a polygon.")
    if not g.is_valid:
        g = g.buffer(0)
    s = get_settings()
    from shapely.geometry import box

    if not g.intersects(box(*s.bbox)):
        raise ValueError("The claim is outside the pilot area. GeoRevive only has data for the pilot area so far.")
    area_ha = _to_utm(g, s.working_crs).area / 10_000
    if area_ha > 5000:
        raise ValueError(f"The polygon is {area_ha:,.0f} ha - too large for a claim check (max 5,000 ha).")
    return g


def _raster_stats(path, geom_utm) -> dict[str, float] | None:
    from rasterio.features import geometry_mask

    if not path.exists():
        return None
    arr, g = read_raster(path)
    m = ~geometry_mask([geom_utm], out_shape=arr.shape, transform=g.transform, all_touched=True)
    v = arr[m & np.isfinite(arr)]
    if v.size == 0:
        return {"n": 0}
    allv = arr[np.isfinite(arr)]
    mean = float(v.mean())
    return {
        "n": int(v.size),
        "mean": mean,
        "min": float(v.min()),
        "max": float(v.max()),
        "area_percentile": float((allv <= mean).mean() * 100),
        "valid_fraction": float(v.size / max(1, m.sum())),
    }


def analyse(db: Session, geojson: dict[str, Any], name: str) -> dict[str, Any]:
    s = get_settings()
    gpkg = s.path("gpkg")
    tables = set(gpkg_tables(gpkg))
    g = validate_polygon(geojson)
    gu = _to_utm(g, s.working_crs)
    c = g.centroid
    used_layers: set[str] = set()
    out: dict[str, Any] = {
        "name": name,
        "polygon": geojson,
        "centroid": [c.x, c.y],
        "area_ha": round(gu.area / 10_000, 2),
        "disclaimer": DISCLAIMER,
    }

    # location
    for lvl, key in (("admin_adm2", "district"), ("admin_adm1", "province")):
        if lvl in tables:
            gdf = read_vector(gpkg, lvl)
            hit = gdf[gdf.intersects(Point(c.x, c.y))]
            out[key] = str(hit.iloc[0]["shapeName"]) if len(hit) else None
            used_layers.add(lvl)

    def near(table: str, name_col: str | list[str], extra: list[str], km: float = NEAR_KM) -> list[dict[str, Any]]:
        gdf = read_vector(gpkg, table).to_crs(s.working_crs)
        if isinstance(name_col, list):
            name_col = next((c for c in name_col if c in gdf.columns), name_col[0])
        d = gdf.distance(gu)
        gdf = gdf.assign(dist_km=(d / 1000).round(2))
        sub = gdf[gdf["dist_km"] <= km].sort_values("dist_km")
        used_layers.add(table)
        rows = []
        for _, r in sub.iterrows():
            row = {"name": _txt(r.get(name_col), "unnamed"), "dist_km": float(r["dist_km"])}
            for e in extra:
                if e in r and r[e] is not None and str(r[e]) not in ("nan", "None"):
                    row[e] = str(r[e])
            rows.append(row)
        return rows

    # geology
    geo_table = "geology" if "geology" in tables else ("regional_geology" if "regional_geology" in tables else None)
    out["geology_scale"] = (
        "1:100 000 (BGS/ZGS)" if geo_table == "geology" else ("1:10 000 000 regional (coarse)" if geo_table else None)
    )
    units = []
    if geo_table:
        gdf = read_vector(gpkg, geo_table).to_crs(s.working_crs)
        inter = gdf[gdf.intersects(gu)]
        label_col = next(
            (x for x in ("LEX_D", "LEX_RCS_D", "RCS_D", "name", "lith", "LEX_RCS") if x in gdf.columns), None
        )
        from ..prospect.evidence import classify_unit

        for _, r in inter.iterrows():
            a = r.geometry.intersection(gu).area
            lab = str(r.get(label_col) or "") if label_col else ""
            if not lab and "lith" in r:
                lab = str(r["lith"])
            text = " ".join(str(v) for k, v in r.items() if k != "geometry")
            cls = {
                2: "favourable host rock (greenstone / mafic-ultramafic)",
                1: "granite / gneiss",
                0: "other / cover",
            }[classify_unit(text)]
            units.append({"unit": lab or "unnamed unit", "class": cls, "share_pct": round(a / gu.area * 100, 1)})
        units.sort(key=lambda u: -u["share_pct"])
        used_layers.add(geo_table)
    out["geology"] = units

    # structures
    if "faults" in tables:
        f = read_vector(gpkg, "faults").to_crs(s.working_crs)
        out["nearest_fault_km"] = round(float(f.distance(gu).min()) / 1000, 2) if len(f) else None
        out["fault_source"] = "mapped faults (BGS/ZGS 1:100k)"
        used_layers.add("faults")
    else:
        out["nearest_fault_km"] = None
        out["fault_source"] = "no mapped fault layer available"

    # occurrences
    out["occurrences"] = (
        near("mrds_occurrences", "site_name", ["commod1", "commod2", "dev_stat"])
        if "mrds_occurrences" in tables
        else []
    )
    out["usgs_sites"] = (
        near(
            "usgs_africa_sites",
            ["dsg_name", "featurenam", "feature_name", "name", "site_name"],
            ["commodity", "ds_commodity", "dsg_comm", "status", "dsg_status"],
        )
        if "usgs_africa_sites" in tables
        else []
    )
    out["rescued_facts"] = (
        near("rescued_facts", "value", ["type", "document", "page_no", "source_name"])
        if "rescued_facts" in tables
        else []
    )
    out["mine_features"] = near("osm_mine_features", "name", ["class"], km=2) if "osm_mine_features" in tables else []

    # access
    if "osm_roads" in tables:
        r = read_vector(gpkg, "osm_roads").to_crs(s.working_crs)
        if len(r):
            d = r.distance(gu)
            i = int(d.values.argmin())
            out["nearest_road"] = {
                "km": round(float(d.iloc[i]) / 1000, 2),
                "name": _txt(r.iloc[i].get("name"), _txt(r.iloc[i].get("ref"), "unnamed road")),
                "class": str(r.iloc[i].get("class")),
            }
        used_layers.add("osm_roads")
    if "osm_places" in tables:
        p = read_vector(gpkg, "osm_places").to_crs(s.working_crs)
        p = p[p["class"].isin(["city", "town", "village"])]
        if len(p):
            d = p.distance(gu)
            i = int(d.values.argmin())
            out["nearest_town"] = {
                "km": round(float(d.iloc[i]) / 1000, 1),
                "name": str(p.iloc[i]["name"]),
                "class": str(p.iloc[i]["class"]),
            }
        used_layers.add("osm_places")

    # satellite and terrain
    rasters = s.path("processed_dir") / "rasters"
    ind = {}
    for lid, label in (
        ("s2_iron_oxide", "Iron-oxide index"),
        ("s2_clay", "Clay / hydroxyl index"),
        ("s2_ferrous", "Ferrous-iron index"),
        ("dem_elevation", "Elevation (m)"),
        ("dem_slope", "Slope (degrees)"),
    ):
        st = _raster_stats(rasters / f"{lid}.tif", gu)
        if st is not None:
            ind[lid] = {"label": label, **st}
            used_layers.add(lid)
    out["indicators"] = ind

    # prospectivity (latest run)
    run = db.scalar(select(ModelRun).order_by(ModelRun.id.desc()))
    if run and run.grid_path:
        st = _raster_stats(abspath(run.grid_path), gu)
        out["prospectivity"] = {
            "run_id": run.id,
            "method": run.method,
            "created_at": run.created_at.isoformat(),
            "auc": run.metrics.get("auc"),
            **(st or {}),
        }
        # explanation of the best cell in the polygon
        from rasterio.features import geometry_mask

        from ..prospect import engine, explain

        arr, grid = read_raster(abspath(run.grid_path))
        m = ~geometry_mask([gu], out_shape=arr.shape, transform=grid.transform, all_touched=True) & np.isfinite(arr)
        if m.any():
            idx = np.argmax(np.where(m, arr, -np.inf))
            r_, c_ = divmod(int(idx), grid.width)
            stack = engine.get_stack()
            contrib = engine.explain_cell(run, stack, r_, c_)
            occ = engine.occurrences(run.commodity)
            occ_xy = np.array([[p.x, p.y] for p in occ.geometry]) if occ is not None and len(occ) else np.zeros((0, 2))
            ctx = engine._context(grid, r_, c_, occ_xy, NEAR_KM * 1000)
            out["prospectivity"]["best_cell"] = {
                "score": round(float(arr[r_, c_]), 1),
                "contributions": contrib,
                "explanation": explain.sentence(contrib, ctx),
            }
            out["prospectivity"]["limitations"] = run.metrics.get("limitations", [])
        used_layers.add(f"prospectivity_{run.commodity}")
    else:
        out["prospectivity"] = None

    # sources with licences
    srcs = {}
    for lid in sorted(used_layers):
        layer = db.get(Layer, lid)
        if layer is not None:
            ref = source_ref(layer.source)
            ref["attribution"] = layer.attribution
            srcs[layer.source_id] = ref
            for d in layer.derived_from or []:
                if d.get("kind") == "source" and d["source_id"] not in srcs:
                    from ..models import Source

                    so = db.get(Source, d["source_id"])
                    if so is not None:
                        srcs[so.id] = source_ref(so) | {"attribution": so.attribution}
    out["sources"] = list(srcs.values())
    out["layers_used"] = sorted(used_layers)
    return out
