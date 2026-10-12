from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from ..base import Connector, LayerSpec, ValidationError
from ..process import (
    bbox_polygon,
    merge_max_valid,
    pilot_grid,
    raster_size_str,
    read_raster,
    render_overlay,
    warp_to_grid,
    write_cog,
)

# Common band names -> asset keys per catalogue
ASSETS = {
    "earth-search": {
        "B02": "blue",
        "B03": "green",
        "B04": "red",
        "B08": "nir",
        "B8A": "nir08",
        "B11": "swir16",
        "B12": "swir22",
        "SCL": "scl",
    },
    "planetary": {b: b for b in ("B02", "B03", "B04", "B08", "B8A", "B11", "B12", "SCL")},
}
REFL_BANDS = ["B02", "B03", "B04", "B08", "B8A", "B11", "B12"]
SCL_BAD = (0, 1, 3, 6, 8, 9, 10, 11)  # nodata, saturated, cloud shadow, water, cloud med/high, cirrus, snow
NDVI_VEG = 0.45


def boa_offset(kind: str, item: dict, raster_band: dict) -> float:
    """Additive reflectance offset to apply after scaling.

    Processing baseline >= 04.00 adds +1000 DN to L2A data (offset -0.1 after scaling). Earth Search v1
    COGs already have it removed ('earthsearch:boa_offset_applied': true) yet still list offset -0.1 in
    raster:bands - applying it again would make dark targets negative and break the band ratios."""
    props = item.get("properties", {})
    if props.get("earthsearch:boa_offset_applied"):
        return 0.0
    if kind == "planetary":
        return -0.1 if props.get("s2:processing_baseline", "00.00") >= "04.00" else 0.0
    return float(raster_band.get("offset", 0.0))


def catalogue_kind(url: str) -> str:
    return "planetary" if "planetarycomputer" in url else "earth-search"


def alteration_indices(b: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Band-ratio indices commonly used for hydrothermal alteration mapping with Sentinel-2.

    iron_oxide = B04/B02 (ferric iron, e.g. hematite/goethite/jarosite)
    ferrous    = B12/B8A + B03/B04 (ferrous iron in silicates/carbonates)
    clay       = B11/B12 (Al-OH / Mg-OH / carbonate absorption near 2.2 um -> clays, sericite)
    ndvi       = (B08-B04)/(B08+B04) used to mask vegetation
    """
    eps = 1e-6
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (b["B08"] - b["B04"]) / (b["B08"] + b["B04"] + eps)
        iron = b["B04"] / (b["B02"] + eps)
        ferrous = b["B12"] / (b["B8A"] + eps) + b["B03"] / (b["B04"] + eps)
        clay = b["B11"] / (b["B12"] + eps)
    return {"ndvi": ndvi, "iron_oxide": iron, "ferrous": ferrous, "clay": clay}


def choose_scene_group(items: list[dict], bbox: tuple[float, float, float, float], min_cover: float = 0.95):
    """Pick the acquisition date whose tiles together cover the bbox, with the lowest mean cloud."""
    from shapely.geometry import shape
    from shapely.ops import unary_union

    target = bbox_polygon(bbox)
    groups: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        groups[it["properties"]["datetime"][:10]].append(it)
    best = None
    for day, its in groups.items():
        cover = unary_union([shape(i["geometry"]) for i in its]).intersection(target).area / target.area
        cloud = float(np.mean([i["properties"].get("eo:cloud_cover", 100) for i in its]))
        if cover < min_cover:
            continue
        key = (cloud, -cover)
        if best is None or key < best[0]:
            best = (key, day, its, cover, cloud)
    return best


class Sentinel2Connector(Connector):
    id = "sentinel2_l2a"
    name = "Copernicus Sentinel-2 Level-2A surface reflectance (dry season scene)"
    publisher = "European Space Agency / European Commission (Copernicus), via open STAC catalogue"
    url = "https://earth-search.aws.element84.com/v1"
    licence = "Copernicus Sentinel data terms: free, full and open access (attribution required)"
    licence_url = "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"
    attribution = "Contains modified Copernicus Sentinel data [year], processed by GeoRevive"
    note = (
        "Bottom-of-atmosphere reflectance (bands B02-B12, SCL) for one low-cloud dry-season date over the pilot area."
    )
    usage = (
        "Band-ratio alteration indices (iron oxide B4/B2, ferrous iron B12/B8A+B3/B4, clay/hydroxyl B11/B12) "
        "with cloud, water and vegetation masks; evidence layers for prospectivity."
    )

    def fetch(self) -> None:
        o = self.outcome
        cfg = self.s.section("ingest").get("sentinel2", {})
        manifest = self.read_manifest()
        stack = self.raw_dir / "s2_bands.tif"
        if stack.exists() and manifest.get("scene_ids") and not self.force:
            self.http.note(manifest.get("stac_url", self.url), "cached: s2_bands.tif")
            self._finish_fetch(manifest)
            return
        from pystac_client import Client

        errors = []
        chosen = None
        for stac_url in cfg.get("stac_urls", [self.url]):
            kind = catalogue_kind(stac_url)
            try:
                client = Client.open(stac_url, headers={"User-Agent": self.http.ua})
                self.http.note(stac_url, "STAC catalogue opened")
            except Exception as e:
                errors.append(f"{stac_url}: {e}")
                self.http.note(stac_url, f"error: {e}"[:200])
                continue
            for window in cfg.get("date_windows", []):
                try:
                    search = client.search(
                        collections=[cfg.get("collection", "sentinel-2-l2a")],
                        bbox=list(self.bbox),
                        datetime=window,
                        query={"eo:cloud_cover": {"lt": cfg.get("max_cloud_pct", 10)}},
                        max_items=400,
                    )
                    items = [i.to_dict() for i in search.items()]
                except Exception as e:
                    errors.append(f"{stac_url} {window}: {e}")
                    continue
                self.http.note(f"{stac_url}/search?datetime={window}", f"{len(items)} items")
                best = choose_scene_group(items, self.bbox)
                if best:
                    chosen = (stac_url, kind, window, best)
                    break
            if chosen:
                break
        if not chosen:
            o.status = "failed"
            o.error = (
                "No low-cloud dry-season scene group covering the pilot area was found. " + "; ".join(errors)[:800]
            )
            return
        stac_url, kind, window, (_, day, its, cover, cloud) = chosen
        token = None
        if kind == "planetary":
            token = self.http.get_json("https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a")[
                "token"
            ]
        res = float(cfg.get("resolution_m", 60))
        grid = pilot_grid(self.bbox, self.s.working_crs, res)
        bands: dict[str, np.ndarray] = {}
        hrefs: dict[str, list[str]] = defaultdict(list)
        for b in REFL_BANDS + ["SCL"]:
            parts = []
            for it in its:
                asset = it["assets"][ASSETS[kind][b]]
                href = asset["href"]
                if not self.http.robots_allowed(href):
                    raise RuntimeError(f"robots.txt disallows {href}")
                url = href + ("?" + token if token else "")
                arr = warp_to_grid(
                    "/vsicurl/" + url, grid, resampling="nearest" if b == "SCL" else "bilinear", src_nodata=0
                )
                if b != "SCL":
                    rb = (asset.get("raster:bands") or [{}])[0]
                    scale = rb.get("scale", 1e-4)
                    offset = boa_offset(kind, it, rb)
                    arr = arr * scale + offset
                parts.append(arr)
                hrefs[b].append(href)
            bands[b] = merge_max_valid(parts)
            self.http.note(hrefs[b][0], f"read window for {b} ({len(parts)} tile(s))")
        stack_arr = np.stack([bands[b] for b in REFL_BANDS + ["SCL"]]).astype("float32")
        self._write_stack(stack_arr, grid, stack)
        for it in its:
            (self.raw_dir / f"{it['id']}.json").write_text(json.dumps(it), encoding="utf-8")
        manifest = {
            "stac_url": stac_url,
            "catalogue": kind,
            "window": window,
            "date": day,
            "scene_ids": [i["id"] for i in its],
            "cloud_cover_mean": cloud,
            "coverage": cover,
            "asset_hrefs": hrefs,
            "resolution_m": res,
            "bands": REFL_BANDS + ["SCL"],
            "offset_fixed": True,
        }
        self.write_manifest(manifest)
        self._finish_fetch(manifest)

    def _write_stack(self, arr: np.ndarray, grid, path) -> None:
        import rasterio

        prof = grid.to_profile(dtype="float32")
        prof.update(count=arr.shape[0], driver="COG", compress="DEFLATE")
        with rasterio.open(path, "w", **prof) as dst:
            dst.write(arr)
            dst.descriptions = tuple(REFL_BANDS + ["SCL"])

    def _repair_double_offset(self, m: dict) -> dict:
        """One-off repair of stacks cached before the offset fix: add back the -0.1 that was applied twice."""
        if m.get("offset_fixed"):
            return m
        items = [json.loads((self.raw_dir / f"{sid}.json").read_text(encoding="utf-8")) for sid in m["scene_ids"]]
        if items and all(i.get("properties", {}).get("earthsearch:boa_offset_applied") for i in items):
            import rasterio

            p = self.raw_dir / "s2_bands.tif"
            with rasterio.open(p) as src:
                arr = src.read().astype("float32")
                from ..process import Grid

                g = Grid(crs=src.crs.to_string(), transform=src.transform, width=src.width, height=src.height)
            arr[: len(REFL_BANDS)] += 0.1
            self._write_stack(arr, g, p)
            self.http.note(m["stac_url"], "repaired cached stack: removed a doubly applied BOA offset")
        m["offset_fixed"] = True
        self.write_manifest(m)
        return m

    def _finish_fetch(self, m: dict) -> None:
        o = self.outcome
        m = self._repair_double_offset(m)
        o.status = "downloaded"
        o.url = m["stac_url"]
        files = [(self.raw_dir / "s2_bands.tif", m["stac_url"]), (self.manifest_path(), None)]
        files += [
            (self.raw_dir / f"{sid}.json", f"{m['stac_url']}/collections/sentinel-2-l2a/items/{sid}")
            for sid in m["scene_ids"]
        ]
        o.files = files
        o.details = {k: m[k] for k in ("scene_ids", "date", "cloud_cover_mean", "coverage", "catalogue", "window")}
        o.note_extra = (
            f"Scene date {m['date']}; scenes: {', '.join(m['scene_ids'])}; mean cloud {m['cloud_cover_mean']:.1f}%."
        )
        o.bbox = list(self.bbox)

    def _bands(self):
        import rasterio

        with rasterio.open(self.raw_dir / "s2_bands.tif") as src:
            arr = src.read().astype("float32")
            from ..process import Grid

            g = Grid(crs=src.crs.to_string(), transform=src.transform, width=src.width, height=src.height)
        return {b: arr[i] for i, b in enumerate(REFL_BANDS + ["SCL"])}, g

    def validate(self) -> None:
        bands, _ = self._bands()
        for b in REFL_BANDS:
            v = bands[b][np.isfinite(bands[b])]
            if v.size == 0:
                raise ValidationError(f"band {b} has no valid pixels")
            med = float(np.median(v))
            if not (0.0 < med < 1.0):  # a negative median reflectance means a scaling/offset error
                raise ValidationError(f"band {b} median reflectance {med:.3f} is outside the plausible range")
        valid = np.isfinite(bands["B04"]).mean()
        if valid < 0.5:
            raise ValidationError(f"only {valid:.0%} of the pilot area has data")

    def process(self) -> None:
        o = self.outcome
        bands, grid = self._bands()
        idx = alteration_indices(bands)
        scl = bands["SCL"]
        bad = np.isin(np.nan_to_num(scl, nan=0).astype(int), SCL_BAD)
        veg = idx["ndvi"] > NDVI_VEG
        out = self.processed_dir / "rasters"
        year = (o.details.get("date") or "")[:4]
        attribution = self.attribution.replace("[year]", year or "")
        specs = [
            ("s2_iron_oxide", "Iron-oxide index (Sentinel-2 B4/B2)", "YlOrRd", True),
            ("s2_ferrous", "Ferrous-iron index (B12/B8A + B3/B4)", "PuRd", True),
            ("s2_clay", "Clay / hydroxyl index (B11/B12)", "BuPu", True),
            ("s2_ndvi", "Vegetation (NDVI)", "Greens", False),
        ]
        for lid, name, cmap, mask_veg in specs:
            key = lid.replace("s2_", "")
            arr = idx[key].astype("float32")
            arr[bad | ~np.isfinite(arr)] = np.nan
            if mask_veg:
                arr[veg] = np.nan
            path = write_cog(
                arr,
                grid,
                out / f"{lid}.tif",
                tags={"source": "Sentinel-2 L2A", "scenes": ",".join(o.details.get("scene_ids", []))},
            )
            png = self.overlay_dir / f"{lid}.png"
            bounds, legend = render_overlay(arr, grid, png, cmap=cmap, alpha_ramp=mask_veg, alpha=0.9)
            legend["note"] = "Masked: cloud, shadow, water" + (", dense vegetation (NDVI>0.45)" if mask_veg else "")
            o.layers.append(
                LayerSpec(
                    id=lid,
                    name=name,
                    kind="raster",
                    group="satellite",
                    raster_path=path,
                    overlay_png=png,
                    overlay_bounds=bounds,
                    legend=legend,
                    attribution=attribution,
                    description=f"{name} from scene(s) {', '.join(o.details.get('scene_ids', []))}.",
                )
            )
        # true colour for context
        rgb = np.dstack([bands["B04"], bands["B03"], bands["B02"]])
        self._true_colour(rgb, grid, o, attribution)
        o.raster_size = raster_size_str(grid, bands=len(REFL_BANDS) + 1)

    def _true_colour(self, rgb, grid, o, attribution) -> None:
        from PIL import Image
        from rasterio.warp import Resampling, calculate_default_transform, reproject

        w, s, e, n = grid.bounds
        tr, dw, dh = calculate_default_transform(grid.crs, "EPSG:3857", grid.width, grid.height, w, s, e, n)
        out = np.zeros((dh, dw, 4), dtype="uint8")
        for i in range(3):
            dst = np.full((dh, dw), np.nan, dtype="float32")
            reproject(
                rgb[..., i],
                dst,
                src_transform=grid.transform,
                src_crs=grid.crs,
                dst_transform=tr,
                dst_crs="EPSG:3857",
                src_nodata=np.nan,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
            v = dst[np.isfinite(dst)]
            lo, hi = (np.percentile(v, 2), np.percentile(v, 98)) if v.size else (0.0, 0.3)
            out[..., i] = (np.clip((np.nan_to_num(dst) - lo) / max(hi - lo, 1e-6), 0, 1) ** (1 / 1.3) * 255).astype(
                "uint8"
            )
            if i == 0:
                out[..., 3] = np.where(np.isfinite(dst), 255, 0)
        png = self.overlay_dir / "s2_true_colour.png"
        Image.fromarray(out, "RGBA").save(png, optimize=True)
        from pyproj import Transformer

        t = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        lon0, lat0 = t.transform(tr.c, tr.f + tr.e * dh)
        lon1, lat1 = t.transform(tr.c + tr.a * dw, tr.f)
        o.layers.append(
            LayerSpec(
                id="s2_true_colour",
                name="Sentinel-2 true colour",
                kind="raster",
                group="satellite",
                overlay_png=png,
                overlay_bounds=[lon0, lat0, lon1, lat1],
                attribution=attribution,
                description="Natural-colour composite (B4, B3, B2).",
            )
        )


def load_index(processed_dir, lid: str):
    return read_raster(processed_dir / "rasters" / f"{lid}.tif")
