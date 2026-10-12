"""Offline map snapshot for reports (matplotlib), drawn only from local, registered layers."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..config import get_settings
from ..ingest.process import gpkg_tables, read_raster, read_vector


def snapshot(
    polygon_geojson: dict, out_png: Path, run_grid: Path | None = None, pad_m: float = 2500, title: str = ""
) -> list[str]:
    """Render a map around the claim. Returns the attributions of what was drawn."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import shape

    s = get_settings()
    crs = s.working_crs
    gpkg = s.path("gpkg")
    tables = set(gpkg_tables(gpkg))
    import geopandas as gpd

    claim = gpd.GeoSeries([shape(polygon_geojson)], crs="EPSG:4326").to_crs(crs)
    x0, y0, x1, y1 = claim.total_bounds
    pad = max(pad_m, (x1 - x0), (y1 - y0))
    ext = (x0 - pad, x1 + pad, y0 - pad, y1 + pad)
    fig, ax = plt.subplots(figsize=(6.6, 5.2), dpi=150)
    ax.set_facecolor("#efe9dc")
    attributions: list[str] = []

    hs = s.path("processed_dir") / "rasters" / "dem_hillshade.tif"
    if hs.exists():
        arr, g = read_raster(hs)
        w, so, e, n = g.bounds
        ax.imshow(arr, cmap="gray", extent=(w, e, so, n), vmin=0, vmax=1, alpha=0.55, zorder=1)
        attributions.append("Hillshade: Copernicus DEM GLO-30 © DLR/Airbus (EU/ESA)")
    geo_table = "geology" if "geology" in tables else ("regional_geology" if "regional_geology" in tables else None)
    if geo_table:
        gdf = read_vector(gpkg, geo_table).to_crs(crs).cx[ext[0] : ext[1], ext[2] : ext[3]]
        if len(gdf):
            from ..prospect.evidence import classify_unit

            txt = gdf.drop(columns="geometry").astype(str).agg(" ".join, axis=1)
            cls = txt.map(classify_unit)
            colours = cls.map({2: "#2f855a", 1: "#e8a0a0", 0: "#d6cfc0"})
            gdf.plot(ax=ax, color=colours, alpha=0.35, edgecolor="#4b5563", linewidth=0.3, zorder=2)
            attributions.append(
                "Geology: BGS/ZGS 1:100k" if geo_table == "geology" else "Geology: CGMW-BRGM 1:10M via Macrostrat"
            )
    if run_grid is not None and run_grid.exists():
        arr, g = read_raster(run_grid)
        w, so, e, n = g.bounds
        ax.imshow(
            np.ma.masked_invalid(arr), cmap="YlOrRd", extent=(w, e, so, n), vmin=0, vmax=100, alpha=0.45, zorder=3
        )
        attributions.append("Prospectivity: GeoRevive prototype model")
    if "faults" in tables:
        read_vector(gpkg, "faults").to_crs(crs).cx[ext[0] : ext[1], ext[2] : ext[3]].plot(
            ax=ax, color="#b91c1c", linewidth=1, zorder=4
        )
    if "osm_roads" in tables:
        r = read_vector(gpkg, "osm_roads").to_crs(crs).cx[ext[0] : ext[1], ext[2] : ext[3]]
        if len(r):
            r.plot(ax=ax, color="#7c4a1e", linewidth=0.8, zorder=4)
            attributions.append("Roads: © OpenStreetMap contributors (ODbL)")
    if "osm_rivers" in tables:
        r = read_vector(gpkg, "osm_rivers").to_crs(crs).cx[ext[0] : ext[1], ext[2] : ext[3]]
        if len(r):
            r.plot(ax=ax, color="#2b7bb9", linewidth=0.6, zorder=4)
    if "mrds_occurrences" in tables:
        o = read_vector(gpkg, "mrds_occurrences").to_crs(crs).cx[ext[0] : ext[1], ext[2] : ext[3]]
        if len(o):
            gold = o[o.get("is_gold", 0).astype(int) == 1] if "is_gold" in o.columns else o
            other = o.drop(gold.index)
            other.plot(ax=ax, color="#9ca3af", markersize=14, edgecolor="white", linewidth=0.5, zorder=5)
            gold.plot(ax=ax, color="#B7791F", markersize=22, edgecolor="#1E3A5F", linewidth=0.6, zorder=5)
            attributions.append("Occurrences: USGS MRDS (public domain)")
    claim.boundary.plot(ax=ax, color="#1E3A5F", linewidth=2.2, zorder=6)
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    # scale bar (1 km or 2 km) and north arrow
    span = ext[1] - ext[0]
    sb = 1000 if span < 8000 else 2000
    bx, by = ext[0] + span * 0.05, ext[2] + (ext[3] - ext[2]) * 0.05
    ax.plot([bx, bx + sb], [by, by], color="black", linewidth=3, zorder=7)
    ax.text(bx + sb / 2, by + (ext[3] - ext[2]) * 0.02, f"{sb // 1000} km", ha="center", fontsize=7, zorder=7)
    ax.annotate("N", xy=(0.95, 0.93), xycoords="axes fraction", ha="center", fontsize=10, fontweight="bold")
    ax.annotate(
        "",
        xy=(0.95, 0.92),
        xytext=(0.95, 0.84),
        xycoords="axes fraction",
        arrowprops={"arrowstyle": "-|>", "color": "black"},
    )
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    handles = [
        Line2D([0], [0], color="#1E3A5F", lw=2.2, label="Claim"),
        Patch(color="#2f855a", alpha=0.4, label="Greenstone / mafic host"),
        Patch(color="#e8a0a0", alpha=0.4, label="Granite / gneiss"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#B7791F",
            markeredgecolor="#1E3A5F",
            markersize=6,
            label="Known gold occurrence",
        ),
        Line2D([0], [0], color="#7c4a1e", lw=1, label="Road"),
    ]
    if "faults" in tables:
        handles.append(Line2D([0], [0], color="#b91c1c", lw=1, label="Fault"))
    ax.legend(handles=handles, loc="lower right", fontsize=6, framealpha=0.85)
    if title:
        ax.set_title(title, fontsize=9)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)
    return attributions
