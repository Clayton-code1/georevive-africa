from __future__ import annotations

import json
import zipfile

import numpy as np

from ..base import Connector, LayerSpec, ValidationError
from ..process import clip_to_bbox, write_vector

MACROSTRAT = "https://macrostrat.org/api/v2/geologic_units/map"
GEO7_ITEM = "https://www.sciencebase.gov/catalog/item/60d0ff26d34e86b938aab404?format=json"
GEO7_PAGE = "https://www.sciencebase.gov/catalog/item/60d0ff26d34e86b938aab404"
ONEGEOLOGY_PORTAL = "https://portal.onegeology.org/"

# Colours for broad lithology classes (used on the map legend)
LITH_COLOURS = {
    "volcanic-sedimentary": "#2f855a",
    "volcanic-sedimentary and plutonic": "#8fbf7f",
    "plutonic and metamorphic": "#e8a0a0",
    "plutonic": "#e8a0a0",
    "crystalline metamorphic rocks": "#b794c4",
    "metamorphic": "#b794c4",
    "sedimentary": "#e9d8a6",
}


class RegionalGeologyConnector(Connector):
    id = "regional_geology"
    name = "Regional geology - CGMW-BRGM 1:10M Geological Map of Africa (via Macrostrat API)"
    publisher = "Macrostrat (University of Wisconsin-Madison); map source CGMW-BRGM (Thiéblemont ed.)"
    url = MACROSTRAT
    licence = "CC BY 4.0 as stated by the Macrostrat API; underlying CGMW-BRGM map - licence to confirm with CGMW"
    licence_url = "https://macrostrat.org/"
    attribution = "Regional geology: Macrostrat (CC BY 4.0) / CGMW-BRGM 1:10M Geological Map of Africa"
    note = "Very small-scale (1:10 million) lithology/age polygons; separates Archean volcano-sedimentary belts from granitoids."
    usage = (
        "Regional context outside the pilot sheet, and a coarse fallback host-rock layer if the BGS 1:100k "
        "geology is not available. Far too coarse for target-scale decisions."
    )
    N_LON, N_LAT = 9, 7

    def fetch(self) -> None:
        o = self.outcome
        dest = self.raw_dir / "macrostrat_small.geojson"
        if dest.exists() and not self.force:
            self.http.note(MACROSTRAT, "cached: macrostrat_small.geojson")
        else:
            w, s, e, n = self.bbox
            feats: dict[int, dict] = {}
            for lat in np.linspace(s, n, self.N_LAT):
                for lon in np.linspace(w, e, self.N_LON):
                    url = f"{MACROSTRAT}?lat={lat:.4f}&lng={lon:.4f}&scale=small&format=geojson"
                    r = self.http.get(url)
                    if r.status_code != 200:
                        continue
                    for f in r.json().get("success", {}).get("data", {}).get("features", []) or []:
                        feats[f["properties"]["map_id"]] = f
            if not feats:
                raise RuntimeError("Macrostrat returned no polygons for the pilot area")
            dest.write_text(
                json.dumps({"type": "FeatureCollection", "features": list(feats.values())}), encoding="utf-8"
            )
        o.files = [(dest, MACROSTRAT + "?scale=small")]
        o.status = "downloaded"

    def validate(self) -> None:
        import geopandas as gpd

        gdf = gpd.read_file(self.raw_dir / "macrostrat_small.geojson")
        if len(gdf) == 0 or "lith" not in gdf.columns:
            raise ValidationError("no polygons with a 'lith' attribute")

    def process(self) -> None:
        import geopandas as gpd

        o = self.outcome
        gdf = gpd.read_file(self.raw_dir / "macrostrat_small.geojson").set_crs("EPSG:4326", allow_override=True)
        cols = [c for c in ("map_id", "name", "lith", "best_int_name", "t_age", "b_age", "color") if c in gdf.columns]
        gdf = gdf[cols + ["geometry"]]
        gdf["source_ref"] = "Thiéblemont (ed.) CGMW-BRGM 1:10M Geological Map of Africa, via Macrostrat"
        clipped = clip_to_bbox(gdf, self.bbox)
        n = write_vector(clipped, self.gpkg, "regional_geology")
        o.record_count = n
        o.bbox = list(self.bbox)
        liths = sorted(set(clipped["lith"].dropna()))
        o.details = {"lithologies": liths, "polygons_total": int(len(gdf))}
        o.layers.append(
            LayerSpec(
                id="regional_geology",
                name="Regional geology (1:10M, CGMW-BRGM)",
                kind="vector",
                group="geology",
                gpkg_table="regional_geology",
                geometry_type="Polygon",
                feature_count=n,
                attribution=self.attribution,
                style={"type": "fill", "field": "lith", "colors": LITH_COLOURS, "default": "#d6cfc0", "opacity": 0.45},
                legend={
                    "type": "categorical",
                    "items": [{"label": k, "color": LITH_COLOURS.get(k, "#d6cfc0")} for k in liths],
                },
                description="Very small-scale regional geology; use for context only.",
            )
        )


class UsgsGeo7Connector(Connector):
    """Tried as a second regional source; recorded honestly whatever the outcome."""

    id = "usgs_geo7_africa"
    name = "USGS Geology of Africa (geo7_2ag, Open-File Report 97-470A)"
    publisher = "U.S. Geological Survey (World Energy Project)"
    url = GEO7_PAGE
    licence = "Public domain (USGS); coastline/boundaries contain ESRI proprietary data - licence to confirm"
    attribution = "Geology of Africa: Persits et al., USGS OFR 97-470A"
    note = "1:5M surficial/bedrock geology of Africa by age."
    usage = "Regional context only."

    def fetch(self) -> None:
        o = self.outcome
        manual = sorted(self.manual_dir("usgs/geo7").glob("*.zip"))
        if manual:
            dest = self.adopt_manual(manual[0], self.raw_dir / manual[0].name)
            o.files = [(dest, GEO7_PAGE)]
            o.status = "downloaded"
            o.note_extra = "Downloaded by a team member in a browser (ScienceBase blocks automated clients)."
            return
        r = self.http.get(GEO7_ITEM)
        if r.status_code == 403:
            o.status = "needs_manual_request"
            o.error = "ScienceBase answered HTTP 403 to an automated request (bot protection); not bypassed."
            o.how_to_obtain = (
                f"Optional (regional context only). In a browser open {GEO7_PAGE}, download the shapefile .zip, save it "
                "into data\\inbox\\usgs\\geo7\\ and re-run --source usgs_geo7_africa."
            )
            return
        r.raise_for_status()
        files = [f for f in r.json().get("files", []) if str(f.get("name", "")).lower().endswith(".zip")]
        if not files:
            o.status = "failed"
            o.error = "ScienceBase record lists no zip files."
            return
        f = sorted(files, key=lambda x: x.get("size") or 1e12)[0]
        dest = self.raw_dir / f["name"]
        self.http.download(f.get("downloadUri") or f.get("url"), dest, force=self.force, max_bytes=200_000_000)
        o.files = [(dest, f.get("downloadUri"))]
        o.status = "downloaded"

    def validate(self) -> None:
        z = next(self.raw_dir.glob("*.zip"), None)
        if z is None or not zipfile.is_zipfile(z):
            raise ValidationError("not a valid zip")

    def process(self) -> None:
        import geopandas as gpd

        o = self.outcome
        z = next(self.raw_dir.glob("*.zip"))
        out = self.raw_dir / "unzipped"
        if not out.exists():
            with zipfile.ZipFile(z) as zf:
                zf.extractall(out)
        shp = next(out.rglob("*.shp"), None)
        if shp is None:
            raise ValidationError("zip has no shapefile")
        clipped = clip_to_bbox(gpd.read_file(shp), self.bbox)
        n = write_vector(clipped, self.gpkg, "usgs_geo7_geology")
        o.record_count = n
        o.layers.append(
            LayerSpec(
                id="usgs_geo7_geology",
                name="Geology of Africa (USGS 1:5M)",
                kind="vector",
                group="geology",
                gpkg_table="usgs_geo7_geology",
                geometry_type="Polygon",
                feature_count=n,
                attribution=self.attribution,
                style={"type": "fill", "color": "#c4b59a", "opacity": 0.35},
            )
        )


class OneGeologyConnector(Connector):
    id = "onegeology"
    name = "OneGeology Portal - geology web map services covering Zimbabwe"
    publisher = "OneGeology (Commission for the Geological Map of the World partnership)"
    url = ONEGEOLOGY_PORTAL
    licence = "Per service (to confirm for any service found)"
    note = "The OneGeology Portal lists geological web map services registered by national surveys."
    usage = "Regional geology context, only if an openly licensed Zimbabwe layer is available."

    def fetch(self) -> None:
        o = self.outcome
        try:
            r = self.http.get(ONEGEOLOGY_PORTAL, timeout=30)
            reachable = f"HTTP {r.status_code}"
        except Exception as e:
            reachable = f"unreachable ({type(e).__name__})"
        o.details = {"portal": reachable}
        o.status = "needs_manual_request"
        o.error = (
            f"Portal {reachable}. OneGeology documents no machine-readable catalogue for automated discovery, "
            "so GeoRevive does not guess service URLs."
        )
        o.how_to_obtain = (
            f"1. Open {ONEGEOLOGY_PORTAL} in a browser and search the layer catalogue for 'Zimbabwe'.\n"
            "2. If a Zimbabwe Geological Survey service is listed, note its WMS address and its terms of use.\n"
            "3. Ask the OneGeology team (https://onegeology.org/) or ZGS to confirm the licence before use.\n"
            "Meanwhile GeoRevive uses the CGMW-BRGM 1:10M regional map via Macrostrat for context."
        )

    def validate(self) -> None:
        pass
