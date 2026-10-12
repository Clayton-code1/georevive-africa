"""Evidence layers on the prospectivity grid (EPSG:32736, default 250 m cells).

Each evidence layer records which registered layers it came from (lineage). Layers that cannot be
built from the data actually obtained are reported as unavailable, never filled in.

Known occurrences are NOT evidence: they are only used for training labels (data-driven model),
validation, and context in the explanations.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..config import get_settings
from ..ingest.process import Grid, gpkg_tables, pilot_grid, read_raster, read_vector

EVIDENCE_INFO: dict[str, dict[str, str]] = {
    "dist_fault": {"label": "Distance to faults / shear zones", "unit": "m"},
    "host_rock": {"label": "Favourable host rock (greenstone, mafic-ultramafic, BIF)", "unit": "class"},
    "dist_granite_contact": {"label": "Distance to granite-greenstone contact", "unit": "m"},
    "iron_oxide": {"label": "Sentinel-2 iron-oxide index (percentile)", "unit": "pct"},
    "clay": {"label": "Sentinel-2 clay / hydroxyl index (percentile)", "unit": "pct"},
    "ferrous": {"label": "Sentinel-2 ferrous-iron index (percentile)", "unit": "pct"},
    "slope": {"label": "Slope", "unit": "deg"},
    "roughness": {"label": "Terrain roughness (TRI)", "unit": "m"},
}

# lithology words -> class (for unit descriptions/codes in geology attribute tables)
HOST_PAT = re.compile(
    r"greenstone|basalt|andesit|dacit|komati|ultramaf|ultrabas|serpentin|talc|amphibol|gabbr|"
    r"diorit|banded iron|ironstone|\bbif\b|schist|greywacke|volcanic|volcano|metavolc|chlorit|"
    r"bulawayan|shamvaian|sebakwian|mafic",
    re.I,
)
GRANITE_PAT = re.compile(
    r"granit|tonalit|gneiss|trondhjem|granodior|adamell|plutonic|chilimanzi|sesombi|"
    r"wedza|rhodesdale|migmatit",
    re.I,
)
COVER_PAT = re.compile(r"alluv|kalahari|laterit|sand|karoo|karroo|superficial|regolith", re.I)


def classify_unit(text: str) -> int:
    """2 = favourable host, 1 = granite/gneiss, 0 = cover/other."""
    if not text:
        return 0
    if COVER_PAT.search(text) and not HOST_PAT.search(text):
        return 0
    if HOST_PAT.search(text):
        return 2
    if GRANITE_PAT.search(text):
        return 1
    return 0


@dataclass
class EvidenceStack:
    grid: Grid
    layers: dict[str, np.ndarray] = field(default_factory=dict)
    lineage: dict[str, list[str]] = field(default_factory=dict)  # evidence -> layer ids
    notes: dict[str, str] = field(default_factory=dict)
    unavailable: dict[str, str] = field(default_factory=dict)
    raw: dict[str, np.ndarray] = field(default_factory=dict)  # un-normalised values for explanations
    unit_names: np.ndarray | None = None  # geology unit label per cell (object array)
    exclude: np.ndarray | None = None  # cells that cannot be targets (built-up or water), from land cover
    exclude_note: str = ""

    @property
    def names(self) -> list[str]:
        return list(self.layers)


def evidence_dir() -> Path:
    p = get_settings().path("processed_dir") / "evidence"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _rasterize(gdf, grid: Grid, values, fill=0, dtype="int16") -> np.ndarray:
    from rasterio.features import rasterize

    shapes = ((g, v) for g, v in zip(gdf.geometry, values, strict=True) if g is not None and not g.is_empty)
    return rasterize(shapes, out_shape=grid.shape, transform=grid.transform, fill=fill, dtype=dtype, all_touched=False)


def distance_to(mask: np.ndarray, res: float) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt

    if not mask.any():
        return np.full(mask.shape, np.nan, dtype="float32")
    return (distance_transform_edt(~mask) * res).astype("float32")


def lines_mask(gdf, grid: Grid) -> np.ndarray:
    from rasterio.features import rasterize

    shapes = [(g, 1) for g in gdf.geometry if g is not None and not g.is_empty]
    if not shapes:
        return np.zeros(grid.shape, bool)
    return rasterize(
        shapes, out_shape=grid.shape, transform=grid.transform, fill=0, dtype="uint8", all_touched=True
    ).astype(bool)


def resample_raster(path: Path, grid: Grid) -> np.ndarray:
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    arr, g = read_raster(path)
    dst = np.full(grid.shape, np.nan, dtype="float32")
    reproject(
        arr,
        dst,
        src_transform=g.transform,
        src_crs=g.crs,
        dst_transform=grid.transform,
        dst_crs=grid.crs,
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.average,
    )
    return dst


def class_fraction(path: Path, grid: Grid, classes: tuple[int, ...]) -> np.ndarray:
    """Fraction of each grid cell covered by the given land-cover classes."""
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    arr, g = read_raster(path)
    m = np.where(np.isfinite(arr), np.isin(arr, classes).astype("float32"), np.nan).astype("float32")
    dst = np.full(grid.shape, np.nan, dtype="float32")
    reproject(
        m,
        dst,
        src_transform=g.transform,
        src_crs=g.crs,
        dst_transform=grid.transform,
        dst_crs=grid.crs,
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.average,
    )
    return np.nan_to_num(dst, nan=0.0)


def percentile_rank(a: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan, dtype="float32")
    m = np.isfinite(a)
    if m.sum() < 10:
        return out
    v = a[m]
    order = v.argsort().argsort()
    out[m] = (order / (len(v) - 1)).astype("float32")
    return out


def dem_lineaments(grid: Grid, rasters: Path, min_len_m: float = 2000) -> tuple[np.ndarray, int] | None:
    """Automatic lineament interpretation from the DEM hillshade (edges + Hough segments).
    Used ONLY as a clearly labelled fallback when no mapped faults are available."""
    import cv2

    hs_path = rasters / "dem_hillshade.tif"
    if not hs_path.exists():
        return None
    hs, g = read_raster(hs_path)
    img = np.nan_to_num(hs, nan=float(np.nanmean(hs)))
    img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (0, 0), 3)
    edges = cv2.Canny(img, 30, 90)
    min_px = int(min_len_m / g.res)
    segs = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=min_px, maxLineGap=int(min_px / 6))
    if segs is None:
        return None
    from shapely.geometry import LineString

    lines = []
    for x0, y0, x1, y1 in np.asarray(segs).reshape(-1, 4):  # OpenCV 4: (N,1,4), OpenCV 5: (N,4)
        p0 = g.transform * (float(x0) + 0.5, float(y0) + 0.5)
        p1 = g.transform * (float(x1) + 0.5, float(y1) + 0.5)
        lines.append(LineString([p0, p1]))
    import geopandas as gpd

    gdf = gpd.GeoDataFrame(geometry=lines, crs=g.crs)
    return lines_mask(gdf, grid), len(lines)


def build_stack(force: bool = False) -> EvidenceStack:
    s = get_settings()
    pcfg = s.section("prospectivity")
    grid = pilot_grid(s.bbox, s.working_crs, float(pcfg.get("cell_size_m", 250)))
    gpkg = s.path("gpkg")
    rasters = s.path("processed_dir") / "rasters"
    tables = set(gpkg_tables(gpkg))
    st = EvidenceStack(grid=grid)

    # --- land cover: built-up and water cells are excluded (roofs and bare urban soil mimic alteration)
    lc_path = rasters / "landcover.tif"
    if lc_path.exists():
        builtup = class_fraction(lc_path, grid, (50,))
        water = class_fraction(lc_path, grid, (80,))
        st.exclude = (builtup > 0.3) | (water > 0.5)
        st.exclude_note = (
            f"{st.exclude.mean() * 100:.1f}% of cells are built-up or water (ESA WorldCover) and are "
            "excluded from alteration indices and targets."
        )
        st.lineage["exclusion_mask"] = ["landcover"]

    # --- geology: host rock + granite contacts
    geo_table = "geology" if "geology" in tables else ("regional_geology" if "regional_geology" in tables else None)
    if geo_table:
        gdf = read_vector(gpkg, geo_table).to_crs(grid.crs)
        text_cols = [
            c
            for c in gdf.columns
            if c != "geometry" and (gdf[c].dtype == object or str(gdf[c].dtype) in ("str", "string"))
        ]
        desc = gdf[text_cols].astype(str).agg(" ".join, axis=1) if text_cols else gdf.index.astype(str)
        cls = desc.map(classify_unit).astype(int).values
        cls_grid = _rasterize(gdf, grid, cls, fill=-1)
        label_col = next(
            (c for c in ("LEX_D", "LEX_RCS_D", "RCS_D", "name", "lith", "LEX_RCS") if c in gdf.columns), None
        )
        if label_col:
            idx_grid = _rasterize(gdf, grid, np.arange(len(gdf)), fill=-1, dtype="int32")
            labels = np.array([str(v) for v in gdf[label_col].values] + [""], dtype=object)
            st.unit_names = labels[idx_grid]
        host = np.where(cls_grid == 2, 1.0, np.where(cls_grid == 1, 0.35, np.where(cls_grid == 0, 0.1, np.nan)))
        st.layers["host_rock"] = host.astype("float32")
        st.raw["host_rock"] = cls_grid.astype("float32")
        st.lineage["host_rock"] = [geo_table]
        if geo_table == "regional_geology":
            st.notes["host_rock"] = (
                "From the 1:10 million CGMW-BRGM regional map (coarse) because the BGS 1:100k "
                "geology is not yet available."
            )
        # contacts: host cells adjacent to granite cells
        from scipy.ndimage import binary_dilation

        hostm, granm = cls_grid == 2, cls_grid == 1
        contact = binary_dilation(hostm) & granm | binary_dilation(granm) & hostm
        if contact.any():
            st.raw["dist_granite_contact"] = distance_to(contact, grid.res)
            st.layers["dist_granite_contact"] = st.raw["dist_granite_contact"]
            st.lineage["dist_granite_contact"] = [geo_table]
        else:
            st.unavailable["dist_granite_contact"] = "No granite-greenstone contact in the available geology."
    else:
        st.unavailable["host_rock"] = "No geology layer available."
        st.unavailable["dist_granite_contact"] = "No geology layer available."

    # --- faults
    if "faults" in tables:
        f = read_vector(gpkg, "faults").to_crs(grid.crs)
        st.raw["dist_fault"] = distance_to(lines_mask(f, grid), grid.res)
        st.layers["dist_fault"] = st.raw["dist_fault"]
        st.lineage["dist_fault"] = ["faults"]
    else:
        lin = dem_lineaments(grid, rasters)
        if lin is not None:
            mask, n = lin
            st.raw["dist_fault"] = distance_to(mask, grid.res)
            st.layers["dist_fault"] = st.raw["dist_fault"]
            st.lineage["dist_fault"] = ["dem_hillshade"]
            st.notes["dist_fault"] = (
                f"No mapped faults available: uses {n} automatically interpreted DEM lineaments "
                "(unverified - may include roads, rivers or artefacts)."
            )
        else:
            st.unavailable["dist_fault"] = "No fault layer and no DEM to interpret lineaments."

    # --- Sentinel-2 indices
    for key in ("iron_oxide", "clay", "ferrous"):
        p = rasters / f"s2_{key}.tif"
        if p.exists():
            v = resample_raster(p, grid)
            if st.exclude is not None:
                v[st.exclude] = np.nan  # urban roofs/soil and water are not alteration
            st.raw[key] = v
            st.layers[key] = percentile_rank(v)
            st.lineage[key] = [f"s2_{key}"]
        else:
            st.unavailable[key] = "Sentinel-2 scene not available."

    # --- terrain
    for key, lid in (("slope", "dem_slope"), ("roughness", "dem_roughness")):
        p = rasters / f"{lid}.tif"
        if p.exists():
            v = resample_raster(p, grid)
            st.raw[key] = v
            st.layers[key] = v
            st.lineage[key] = [lid]
        else:
            st.unavailable[key] = "DEM not available."
    return st


def occurrences(commodity: str = "gold"):
    """Known occurrences of the commodity in the pilot area (USGS MRDS), in the grid CRS."""
    s = get_settings()
    gpkg = s.path("gpkg")
    if "mrds_occurrences" not in gpkg_tables(gpkg):
        return None
    gdf = read_vector(gpkg, "mrds_occurrences")
    if "is_gold" in gdf.columns and commodity == "gold":
        gdf = gdf[gdf["is_gold"].astype(int) == 1]
    else:
        cols = [c for c in ("commod1", "commod2", "commod3") if c in gdf.columns]
        m = np.zeros(len(gdf), bool)
        for c in cols:
            m |= gdf[c].fillna("").str.lower().str.contains(commodity)
        gdf = gdf[m]
    return gdf.to_crs(s.working_crs)


def save_stack_meta(st: EvidenceStack) -> None:
    meta = {
        "layers": st.names,
        "lineage": st.lineage,
        "notes": st.notes,
        "unavailable": st.unavailable,
        "grid": {
            "crs": st.grid.crs,
            "transform": list(st.grid.transform)[:6],
            "width": st.grid.width,
            "height": st.grid.height,
        },
    }
    (evidence_dir() / "stack.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def stack_summary(st: EvidenceStack) -> dict[str, Any]:
    return {
        "available": [
            {"id": k, **EVIDENCE_INFO[k], "from_layers": st.lineage.get(k, []), "note": st.notes.get(k)}
            for k in st.names
        ],
        "unavailable": [{"id": k, **EVIDENCE_INFO[k], "reason": v} for k, v in st.unavailable.items()],
        "grid": {"cell_size_m": st.grid.res, "width": st.grid.width, "height": st.grid.height, "crs": st.grid.crs},
    }
