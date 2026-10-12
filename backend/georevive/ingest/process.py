"""Spatial processing shared by connectors: pilot grid, clipping, GeoPackage and COG
writing, and PNG overlays for the web map (rendered in Web Mercator so they line up
exactly with MapLibre)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.TIF,.tiff,.jp2,.vrt")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "3")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")


@dataclass
class Grid:
    crs: str
    transform: Any  # affine.Affine
    width: int
    height: int

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def res(self) -> float:
        return float(self.transform.a)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        from rasterio.transform import array_bounds

        w, s, e, n = array_bounds(self.height, self.width, self.transform)
        return (w, s, e, n)

    def to_profile(self, dtype: str = "float32", nodata: float | None = np.nan) -> dict[str, Any]:
        return {
            "driver": "GTiff",
            "crs": self.crs,
            "transform": self.transform,
            "width": self.width,
            "height": self.height,
            "count": 1,
            "dtype": dtype,
            "nodata": nodata,
        }

    def cell_centers(self) -> tuple[np.ndarray, np.ndarray]:
        cols, rows = np.meshgrid(np.arange(self.width), np.arange(self.height))
        xs = self.transform.c + (cols + 0.5) * self.transform.a
        ys = self.transform.f + (rows + 0.5) * self.transform.e
        return xs, ys


def pilot_grid(bbox: tuple[float, float, float, float], crs: str, res: float) -> Grid:
    """A north-up grid in `crs` covering the lon/lat bbox, snapped to `res` metres."""
    from pyproj import Transformer
    from rasterio.transform import from_origin

    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = [], []
    w, s, e, n = bbox
    for lon in np.linspace(w, e, 21):
        for lat in (s, n):
            x, y = t.transform(lon, lat)
            xs.append(x)
            ys.append(y)
    for lat in np.linspace(s, n, 21):
        for lon in (w, e):
            x, y = t.transform(lon, lat)
            xs.append(x)
            ys.append(y)
    minx = np.floor(min(xs) / res) * res
    maxx = np.ceil(max(xs) / res) * res
    miny = np.floor(min(ys) / res) * res
    maxy = np.ceil(max(ys) / res) * res
    width = int(round((maxx - minx) / res))
    height = int(round((maxy - miny) / res))
    return Grid(crs=crs, transform=from_origin(minx, maxy, res, res), width=width, height=height)


def bbox_polygon(bbox: tuple[float, float, float, float]):
    from shapely.geometry import box

    return box(*bbox)


# --- vectors -------------------------------------------------------------------
def clip_to_bbox(gdf, bbox: tuple[float, float, float, float], clip: bool = True):
    """Reproject to EPSG:4326 and keep features intersecting the bbox (optionally cut)."""
    import geopandas as gpd

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.to_crs("EPSG:4326")
    poly = bbox_polygon(bbox)
    sub = gdf[gdf.intersects(poly)].copy()
    if clip and len(sub):
        sub = gpd.clip(sub, poly)
        sub = sub[~sub.geometry.is_empty]
    return sub


def write_vector(gdf, gpkg: Path, table: str) -> int:
    import pyogrio

    gpkg.parent.mkdir(parents=True, exist_ok=True)
    gdf = gdf.to_crs("EPSG:4326") if gdf.crs is not None else gdf.set_crs("EPSG:4326")
    # GeoPackage columns must be simple types
    for c in gdf.columns:
        if c != "geometry" and gdf[c].dtype == object:
            gdf[c] = gdf[c].map(lambda v: v if v is None or isinstance(v, str | int | float) else str(v))
    pyogrio.write_dataframe(gdf, gpkg, layer=table, driver="GPKG", append=False)
    return len(gdf)


def read_vector(gpkg: Path, table: str):
    import geopandas as gpd

    return gpd.read_file(gpkg, layer=table)


def gpkg_tables(gpkg: Path) -> list[str]:
    import pyogrio

    if not gpkg.exists():
        return []
    return [name for name, _ in pyogrio.list_layers(gpkg)]


# --- rasters -------------------------------------------------------------------
def warp_to_grid(
    src_path: str,
    grid: Grid,
    band: int = 1,
    resampling: str = "bilinear",
    src_nodata: float | None = None,
    dst_dtype: str = "float32",
) -> np.ndarray:
    """Read (local file or /vsicurl/ URL) and warp one band onto the grid.

    For cloud-optimised GeoTIFFs this opens the coarsest internal overview that is still at least as
    fine as the target grid, so only the bytes needed are downloaded (the warper does not do this
    by itself)."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    rs = getattr(Resampling, resampling)
    open_kw: dict[str, Any] = {}
    with rasterio.open(src_path) as probe:
        native = abs(probe.transform.a)
        factors = probe.overviews(band) or []
        from pyproj import CRS

        same_units = (
            CRS.from_user_input(probe.crs).axis_info[0].unit_name
            == CRS.from_user_input(grid.crs).axis_info[0].unit_name
        )
        if same_units and factors:
            usable = [i for i, f in enumerate(factors) if native * f <= grid.res * 1.01]
            if usable:
                open_kw["overview_level"] = usable[-1]
    with rasterio.open(src_path, **open_kw) as src:
        nod = src_nodata if src_nodata is not None else src.nodata
        with WarpedVRT(
            src,
            crs=grid.crs,
            transform=grid.transform,
            width=grid.width,
            height=grid.height,
            resampling=rs,
            src_nodata=nod,
            nodata=np.nan if dst_dtype.startswith("float") else 0,
            dtype=dst_dtype,
        ) as vrt:
            arr = vrt.read(band)
    return arr


def merge_max_valid(arrays: list[np.ndarray]) -> np.ndarray:
    """Combine several warped arrays covering parts of the grid (first valid wins)."""
    out = np.full(arrays[0].shape, np.nan, dtype="float32")
    for a in arrays:
        m = np.isnan(out) & np.isfinite(a)
        out[m] = a[m]
    return out


def write_cog(
    arr: np.ndarray, grid: Grid, path: Path, nodata: float | None = np.nan, tags: dict[str, str] | None = None
) -> Path:
    import rasterio.shutil
    from rasterio.io import MemoryFile

    path.parent.mkdir(parents=True, exist_ok=True)
    prof = grid.to_profile(dtype=str(arr.dtype), nodata=nodata)
    with MemoryFile() as mem:
        with mem.open(**prof) as tmp:
            tmp.write(arr, 1)
            if tags:
                tmp.update_tags(**tags)
        with mem.open() as src:
            cog_prof = {"driver": "COG", "compress": "DEFLATE", "overview_resampling": "average"}
            rasterio.shutil.copy(src, path, **cog_prof)
    return path


def read_raster(path: Path) -> tuple[np.ndarray, Grid]:
    import rasterio

    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        if src.nodata is not None and not np.isnan(src.nodata):
            arr[arr == src.nodata] = np.nan
        g = Grid(crs=src.crs.to_string(), transform=src.transform, width=src.width, height=src.height)
    return arr, g


def raster_size_str(grid: Grid, bands: int = 1) -> str:
    return f"{grid.width} x {grid.height} px @ {grid.res:.0f} m ({bands} band{'s' if bands > 1 else ''})"


def render_overlay(
    arr: np.ndarray,
    grid: Grid,
    png: Path,
    cmap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
    pct: tuple[float, float] = (2, 98),
    alpha: float = 0.85,
    categorical: dict[int, str] | None = None,
    alpha_ramp: bool = False,
) -> tuple[list[float], dict]:
    """Render a single-band array to an RGBA PNG in EPSG:3857. Returns ([w, s, e, n] lon/lat, legend)."""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import colormaps
    from matplotlib.colors import to_rgba
    from PIL import Image
    from pyproj import Transformer
    from rasterio.enums import Resampling
    from rasterio.warp import calculate_default_transform, reproject

    w, s, e, n = grid.bounds
    dst_crs = "EPSG:3857"
    tr, dw, dh = calculate_default_transform(grid.crs, dst_crs, grid.width, grid.height, w, s, e, n)
    dst = np.full((dh, dw), np.nan, dtype="float32")
    reproject(
        arr.astype("float32"),
        dst,
        src_transform=grid.transform,
        src_crs=grid.crs,
        dst_transform=tr,
        dst_crs=dst_crs,
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.nearest if categorical else Resampling.bilinear,
    )
    valid = np.isfinite(dst)
    rgba = np.zeros((dh, dw, 4), dtype="uint8")
    legend: dict[str, Any]
    if categorical:
        for val, color in categorical.items():
            m = valid & (np.round(dst) == val)
            rgba[m] = (np.array(to_rgba(color)) * 255).astype("uint8")
            rgba[m, 3] = int(alpha * 255)
        legend = {"type": "categorical", "items": [{"value": k, "color": v} for k, v in categorical.items()]}
    else:
        vals = dst[valid]
        lo = vmin if vmin is not None else (float(np.percentile(vals, pct[0])) if vals.size else 0.0)
        hi = vmax if vmax is not None else (float(np.percentile(vals, pct[1])) if vals.size else 1.0)
        if hi <= lo:
            hi = lo + 1e-6
        norm = np.clip((dst - lo) / (hi - lo), 0, 1)
        cm = colormaps[cmap]
        colored = (cm(np.nan_to_num(norm)) * 255).astype("uint8")
        rgba[..., :3] = colored[..., :3]
        if alpha_ramp:  # low values fade out so the base map shows through; highs stand out
            a = np.clip(np.nan_to_num(norm) * 1.4 - 0.2, 0, 1) * alpha * 255
            rgba[..., 3] = np.where(valid, a, 0).astype("uint8")
        else:
            rgba[..., 3] = np.where(valid, int(alpha * 255), 0)
        stops = [cm(x) for x in np.linspace(0, 1, 6)]
        legend = {
            "type": "continuous",
            "min": lo,
            "max": hi,
            "colors": ["#" + "".join(f"{int(c * 255):02x}" for c in st[:3]) for st in stops],
        }
    png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(png, optimize=True)
    # bounds of the mercator image back to lon/lat
    t = Transformer.from_crs(dst_crs, "EPSG:4326", always_xy=True)
    x0, y1 = tr.c, tr.f
    x1, y0 = tr.c + tr.a * dw, tr.f + tr.e * dh
    lon0, lat0 = t.transform(x0, y0)
    lon1, lat1 = t.transform(x1, y1)
    return [lon0, lat0, lon1, lat1], legend
