from __future__ import annotations

import math

import numpy as np

from ..base import Connector, LayerSpec, ValidationError
from ..process import pilot_grid, raster_size_str, read_raster, render_overlay, warp_to_grid, write_cog

BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
CLASSES = {
    10: ("Tree cover", "#006400"),
    20: ("Shrubland", "#ffbb22"),
    30: ("Grassland", "#ffff4c"),
    40: ("Cropland", "#f096ff"),
    50: ("Built-up", "#fa0000"),
    60: ("Bare / sparse vegetation", "#b4b4b4"),
    70: ("Snow and ice", "#f0f0f0"),
    80: ("Permanent water", "#0064c8"),
    90: ("Herbaceous wetland", "#0096a0"),
    95: ("Mangroves", "#00cf75"),
    100: ("Moss and lichen", "#fae6a0"),
}


def tile_names(bbox: tuple[float, float, float, float]) -> list[str]:
    """WorldCover tiles are 3x3 degrees, named by their south-west corner."""
    w, s, e, n = bbox
    out = []
    for lat in range(int(math.floor(s / 3) * 3), int(math.floor((n - 1e-9) / 3) * 3) + 1, 3):
        for lon in range(int(math.floor(w / 3) * 3), int(math.floor((e - 1e-9) / 3) * 3) + 1, 3):
            out.append(f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}{'E' if lon >= 0 else 'W'}{abs(lon):03d}")
    return out


class WorldCoverConnector(Connector):
    id = "esa_worldcover"
    name = "ESA WorldCover 2021 v200 (10 m land cover)"
    publisher = "European Space Agency (ESA WorldCover consortium), via AWS Open Data"
    url = "https://esa-worldcover.org/"
    licence = "CC BY 4.0"
    licence_url = "https://creativecommons.org/licenses/by/4.0/"
    attribution = "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021)"
    note = "Global land-cover classes (tree, shrub, grass, crop, built-up, bare, water...) at 10 m for 2021."
    usage = (
        "Masks built-up areas and water so that roofs, roads and bare urban soil are not mistaken for "
        "alteration, and so that no target is placed in a town."
    )

    def fetch(self) -> None:
        o = self.outcome
        dest = self.raw_dir / "worldcover_30m.tif"
        tiles = tile_names(self.bbox)
        urls = [BASE.format(tile=t) for t in tiles]
        if not dest.exists() or self.force:
            grid = pilot_grid(self.bbox, self.s.working_crs, 30)
            parts = []
            for u in urls:
                if not self.http.robots_allowed(u):
                    raise RuntimeError(f"robots.txt disallows {u}")
                a = warp_to_grid("/vsicurl/" + u, grid, resampling="nearest", src_nodata=0)
                parts.append(a)
                self.http.note(u, "read window")
            out = np.full(grid.shape, np.nan, dtype="float32")
            for a in parts:
                m = np.isnan(out) & np.isfinite(a) & (a > 0)
                out[m] = a[m]
            write_cog(out, grid, dest, tags={"tiles": ",".join(tiles)})
        else:
            self.http.note(urls[0], "cached: worldcover_30m.tif")
        self.write_manifest({"tiles": tiles, "urls": urls})
        o.files = [(dest, urls[0]), (self.manifest_path(), None)]
        o.details = {"tiles": tiles}
        o.url = urls[0]
        o.status = "downloaded"
        o.bbox = list(self.bbox)

    def validate(self) -> None:
        a, _ = read_raster(self.raw_dir / "worldcover_30m.tif")
        v = a[np.isfinite(a)]
        if v.size < 0.9 * a.size:
            raise ValidationError(f"land cover covers only {v.size / a.size:.0%} of the pilot area")
        if not set(np.unique(v).astype(int)) <= set(CLASSES):
            raise ValidationError("unexpected land-cover class codes")

    def process(self) -> None:
        o = self.outcome
        a, grid = read_raster(self.raw_dir / "worldcover_30m.tif")
        path = write_cog(a, grid, self.processed_dir / "rasters" / "landcover.tif")
        png = self.overlay_dir / "landcover.png"
        present = sorted(int(c) for c in np.unique(a[np.isfinite(a)]))
        bounds, _ = render_overlay(a, grid, png, categorical={c: CLASSES[c][1] for c in present}, alpha=0.7)
        legend = {"type": "categorical", "items": [{"label": CLASSES[c][0], "color": CLASSES[c][1]} for c in present]}
        counts = {CLASSES[c][0]: round(float((a == c).mean() * 100), 1) for c in present}
        o.details["class_percent"] = counts
        o.note_extra = f"Built-up {counts.get('Built-up', 0)}% of the pilot area."
        o.raster_size = raster_size_str(grid)
        o.layers.append(
            LayerSpec(
                id="landcover",
                name="Land cover (ESA WorldCover 2021)",
                kind="raster",
                group="context",
                raster_path=path,
                overlay_png=png,
                overlay_bounds=bounds,
                legend=legend,
                attribution=self.attribution,
                description="Land cover; built-up and water are excluded from satellite alteration indices and targets.",
            )
        )
