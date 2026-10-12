"""A small SYNTHETIC 'world' inside the pilot bbox for engine, report and end-to-end tests.

All names carry the word SYNTHETIC. This module only writes into the temporary test root."""

from __future__ import annotations

import numpy as np

from .synthetic import SYNTHETIC_TAG


def build(settings) -> dict:
    import geopandas as gpd
    from shapely.geometry import LineString, Point, box

    from georevive.db import session_scope
    from georevive.ingest.process import pilot_grid, render_overlay, write_cog, write_vector
    from georevive.registry import rel, upsert_layer, upsert_source

    gpkg = settings.path("gpkg")
    w, s, e, n = settings.bbox
    rng = np.random.default_rng(3)

    belt = box(31.0, -17.86, 31.3, -17.70)
    geology = gpd.GeoDataFrame(
        {"LEX_D": ["SYNTHETIC greenstone (basalt, banded ironstone)", "SYNTHETIC granite gneiss"]},
        geometry=[belt, box(w, s, e, n).difference(belt)],
        crs="EPSG:4326",
    )
    faults = gpd.GeoDataFrame(
        {"TYPE": ["SYNTHETIC shear zone", "SYNTHETIC fault"]},
        geometry=[LineString([(31.0, -17.78), (31.3, -17.77)]), LineString([(31.1, -17.9), (31.2, -17.65)])],
        crs="EPSG:4326",
    )
    pts, names, gold = [], [], []
    for i in range(24):
        lon = rng.uniform(31.02, 31.28)
        lat = -17.775 + rng.normal(0, 0.012)
        pts.append(Point(lon, lat))
        names.append(f"SYNTHETIC gold site {i}")
        gold.append(1)
    pts.append(Point(31.15, -17.772))
    names.append("Jumbo")
    gold.append(1)
    for i in range(5):
        pts.append(Point(rng.uniform(w + 0.05, e - 0.05), rng.uniform(s + 0.05, n - 0.05)))
        names.append(f"SYNTHETIC copper site {i}")
        gold.append(0)
    occ = gpd.GeoDataFrame(
        {
            "dep_id": [str(i) for i in range(len(pts))],
            "site_name": names,
            "commod1": ["Gold" if g else "Copper" for g in gold],
            "dev_stat": "SYNTHETIC",
            "is_gold": gold,
        },
        geometry=pts,
        crs="EPSG:4326",
    )
    districts = gpd.GeoDataFrame(
        {"shapeName": ["SYNTHETIC District A", "SYNTHETIC District B"], "shapeID": ["a", "b"]},
        geometry=[box(w, s, 31.1, n), box(31.1, s, e, n)],
        crs="EPSG:4326",
    )
    roads = gpd.GeoDataFrame(
        {"name": ["SYNTHETIC road"], "class": ["primary"], "osm_id": ["way/1"]},
        geometry=[LineString([(30.9, -17.83), (31.4, -17.72)])],
        crs="EPSG:4326",
    )
    places = gpd.GeoDataFrame(
        {"name": ["Harare", "SYNTHETIC village"], "class": ["city", "village"], "osm_id": ["n/1", "n/2"]},
        geometry=[Point(31.05, -17.83), Point(31.2, -17.75)],
        crs="EPSG:4326",
    )
    vectors = {
        "geology": (geology, "geology", "Polygon", {"type": "fill", "field": "LEX_D"}),
        "faults": (faults, "structure", "LineString", {"type": "line", "color": "#b91c1c"}),
        "mrds_occurrences": (occ, "occurrences", "Point", {"type": "circle", "highlight_field": "is_gold"}),
        "mrds_zimbabwe": (occ, None, "Point", {}),
        "admin_adm2": (districts, "base", "Polygon", {"type": "line"}),
        "admin_adm1": (districts.assign(shapeName="SYNTHETIC Province"), None, "Polygon", {}),
        "osm_roads": (roads, "context", "LineString", {"type": "line"}),
        "osm_places": (places, "context", "Point", {"type": "circle"}),
    }
    for table, (gdf, *_rest) in vectors.items():
        write_vector(gdf, gpkg, table)

    # rasters on a coarse grid
    grid = pilot_grid(settings.bbox, settings.working_crs, 200)
    xs, ys = grid.cell_centers()
    from pyproj import Transformer

    lon, lat = Transformer.from_crs(settings.working_crs, "EPSG:4326", always_xy=True).transform(xs, ys)
    inbelt = (lon > 31.0) & (lon < 31.3) & (lat > -17.86) & (lat < -17.70)
    noise = rng.normal(0, 0.05, grid.shape).astype("float32")
    rdir = settings.path("processed_dir") / "rasters"
    rasters = {
        "dem_hillshade": (0.6 + noise).clip(0, 1),
        "dem_elevation": (1450 + 30 * np.sin(xs / 3000) + noise * 10).astype("float32"),
        "dem_slope": (5 + 3 * np.abs(noise) * 20).astype("float32"),
        "dem_roughness": (2 + np.abs(noise) * 10).astype("float32"),
        "s2_iron_oxide": (1.2 + 0.3 * inbelt + noise).astype("float32"),
        "s2_clay": (1.1 + 0.2 * inbelt + noise).astype("float32"),
        "s2_ferrous": (1.5 + 0.1 * inbelt + noise).astype("float32"),
    }
    with session_scope() as db:
        upsert_source(
            db,
            "syn_world",
            name="SYNTHETIC test world",
            publisher="tests",
            url="https://example.org/synthetic",
            licence="CC BY 4.0 (synthetic test data)",
            status="downloaded",
            note=SYNTHETIC_TAG,
        )
        for table, (gdf, group, gtype, style) in vectors.items():
            if group:
                upsert_layer(
                    db,
                    table,
                    source_id="syn_world",
                    name=f"SYNTHETIC {table}",
                    kind="vector",
                    group=group,
                    gpkg_table=table,
                    geometry_type=gtype,
                    feature_count=len(gdf),
                    attribution="SYNTHETIC",
                    style=style,
                )
        for lid, arr in rasters.items():
            path = write_cog(arr.astype("float32"), grid, rdir / f"{lid}.tif")
            png = settings.path("processed_dir") / "overlays" / f"{lid}.png"
            bounds, legend = render_overlay(arr.astype("float32"), grid, png)
            upsert_layer(
                db,
                lid,
                source_id="syn_world",
                name=f"SYNTHETIC {lid}",
                kind="raster",
                group="base" if lid == "dem_hillshade" else ("satellite" if lid.startswith("s2") else "terrain"),
                raster_path=rel(path),
                overlay_png=rel(png),
                overlay_bounds=bounds,
                legend=legend,
                attribution="SYNTHETIC",
            )
    from georevive.prospect import engine

    engine._STACK_CACHE.clear()
    return {"n_gold": int(sum(gold))}
