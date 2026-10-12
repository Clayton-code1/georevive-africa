from __future__ import annotations

import math

import numpy as np

from ..base import Connector, LayerSpec, ValidationError
from ..process import (
    Grid,
    merge_max_valid,
    pilot_grid,
    raster_size_str,
    read_raster,
    render_overlay,
    warp_to_grid,
    write_cog,
)

BUCKET = "https://copernicus-dem-30m.s3.amazonaws.com"


def tile_name(lat_floor: int, lon_floor: int) -> str:
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat_floor):02d}_00_{ew}{abs(lon_floor):03d}_00_DEM"


def tiles_for_bbox(bbox: tuple[float, float, float, float]) -> list[str]:
    w, s, e, n = bbox
    out = []
    for lat in range(math.floor(s), math.floor(n - 1e-9) + 1):
        for lon in range(math.floor(w), math.floor(e - 1e-9) + 1):
            out.append(tile_name(lat, lon))
    return out


def slope_degrees(dem: np.ndarray, res: float) -> np.ndarray:
    gy, gx = np.gradient(dem, res)
    return np.degrees(np.arctan(np.hypot(gx, gy))).astype("float32")


def hillshade(dem: np.ndarray, res: float, azimuth: float = 315, altitude: float = 45) -> np.ndarray:
    gy, gx = np.gradient(dem, res)
    slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = np.radians(360 - azimuth + 90), np.radians(altitude)
    hs = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
    return np.clip(hs, 0, 1).astype("float32")


def roughness_tri(dem: np.ndarray) -> np.ndarray:
    """Terrain Ruggedness Index: mean absolute difference to the 8 neighbours."""
    p = np.pad(dem, 1, mode="edge")
    acc = np.zeros_like(dem, dtype="float32")
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            acc += np.abs(p[1 + dy : 1 + dy + dem.shape[0], 1 + dx : 1 + dx + dem.shape[1]] - dem)
    return acc / 8


class CopDemConnector(Connector):
    id = "copernicus_dem_glo30"
    name = "Copernicus DEM GLO-30 (30 m digital surface model)"
    publisher = "European Space Agency / Airbus (Copernicus programme), via AWS Open Data"
    url = BUCKET + "/readme.html"
    licence = "Copernicus DEM licence: free of charge, worldwide, for any lawful use, with attribution"
    licence_url = "https://spacedata.copernicus.eu/documents/20123/122407/GEO1988-CopernicusDEM-SPE-002_ProductHandbook_I5.0+%281%29.pdf"
    attribution = (
        "Copernicus DEM © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, "
        "provided under COPERNICUS by the European Union and ESA"
    )
    note = "Elevation (surface model) at ~30 m, reprojected to UTM 36S."
    usage = "Hillshade base map (works offline); slope and terrain roughness evidence layers; lineament support."

    def fetch(self) -> None:
        o = self.outcome
        res = float(self.s.section("ingest").get("dem", {}).get("resolution_m", 30))
        dest = self.raw_dir / "dem_30m.tif"
        names = tiles_for_bbox(self.bbox)
        urls = [f"{BUCKET}/{n}/{n}.tif" for n in names]
        if not dest.exists() or self.force:
            grid = pilot_grid(self.bbox, self.s.working_crs, res)
            parts = []
            for u in urls:
                if not self.http.robots_allowed(u):
                    raise RuntimeError(f"robots.txt disallows {u}")
                parts.append(warp_to_grid("/vsicurl/" + u, grid))
                self.http.note(u, "read window")
            dem = merge_max_valid(parts)
            write_cog(dem, grid, dest, tags={"tiles": ",".join(names)})
        else:
            self.http.note(urls[0], "cached: dem_30m.tif")
        self.write_manifest({"tiles": names, "urls": urls, "resolution_m": res})
        o.files = [(dest, urls[0]), (self.manifest_path(), None)]
        o.details = {"tiles": names}
        o.status = "downloaded"
        o.bbox = list(self.bbox)

    def validate(self) -> None:
        dem, _ = read_raster(self.raw_dir / "dem_30m.tif")
        v = dem[np.isfinite(dem)]
        if v.size < 0.9 * dem.size:
            raise ValidationError(f"DEM covers only {v.size / dem.size:.0%} of the pilot area")
        if not (200 < float(np.median(v)) < 2500):
            raise ValidationError(f"median elevation {float(np.median(v)):.0f} m is implausible for the pilot area")

    def process(self) -> None:
        o = self.outcome
        dem, grid = read_raster(self.raw_dir / "dem_30m.tif")
        res = grid.res
        filled = np.where(np.isfinite(dem), dem, np.nanmean(dem)).astype("float32")
        derived = {
            "dem_elevation": (dem, "Elevation (m)", "terrain", None),
            "dem_slope": (slope_degrees(filled, res), "Slope (degrees)", "magma_r", None),
            "dem_roughness": (roughness_tri(filled), "Terrain roughness (TRI, m)", "cividis", None),
            # 3x vertical exaggeration: the craton is low-relief, so plain hillshade reads as flat grey
            "dem_hillshade": (hillshade(filled * 3.0, res), "Hillshade (base map)", "gray", (0.0, 1.0)),
        }
        out = self.processed_dir / "rasters"
        for lid, (arr, name, cmap, rng) in derived.items():
            arr = arr.astype("float32")
            arr[~np.isfinite(dem)] = np.nan
            path = write_cog(arr, grid, out / f"{lid}.tif")
            png = self.overlay_dir / f"{lid}.png"
            bounds, legend = render_overlay(
                arr,
                grid,
                png,
                cmap=cmap,
                vmin=rng[0] if rng else None,
                vmax=rng[1] if rng else None,
                alpha=1.0 if lid == "dem_hillshade" else 0.8,
            )
            o.layers.append(
                LayerSpec(
                    id=lid,
                    name=name,
                    kind="raster",
                    group="base" if lid == "dem_hillshade" else "terrain",
                    raster_path=path,
                    overlay_png=png,
                    overlay_bounds=bounds,
                    legend=legend,
                    attribution="Copernicus DEM GLO-30 © DLR/Airbus, provided under COPERNICUS by EU and ESA",
                    description=f"{name} derived from Copernicus DEM GLO-30.",
                )
            )
        o.raster_size = raster_size_str(grid)
        v = dem[np.isfinite(dem)]
        o.note_extra = f"Elevation range {v.min():.0f}-{v.max():.0f} m."


def grid_of(path) -> Grid:
    return read_raster(path)[1]
