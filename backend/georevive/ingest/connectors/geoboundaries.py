from __future__ import annotations

import json

from ..base import Connector, LayerSpec, ValidationError
from ..process import clip_to_bbox, write_vector

API = "https://www.geoboundaries.org/api/current/gbOpen/{iso}/{level}/"


class GeoBoundariesConnector(Connector):
    id = "geoboundaries"
    name = "geoBoundaries - Zimbabwe administrative boundaries (ADM0-ADM2)"
    publisher = "geoBoundaries (William & Mary geoLab)"
    url = "https://www.geoboundaries.org/"
    licence = "As reported by the geoBoundaries API per level (see details)"
    attribution = "Boundaries: geoBoundaries (Runfola et al. 2020), source ZIMSTAT / OCHA ROSEA"
    note = "Country, province and district boundaries for Zimbabwe."
    usage = "District names in claim reports; plain base map that works offline."
    LEVELS = ("ADM0", "ADM1", "ADM2")

    def fetch(self) -> None:
        o = self.outcome
        files = []
        meta = {}
        for level in self.LEVELS:
            api = API.format(iso=self.s.country_iso3, level=level)
            info = self.http.get_json(api)
            meta[level] = {
                k: info.get(k)
                for k in (
                    "boundaryLicense",
                    "licenseSource",
                    "boundarySource",
                    "boundaryYearRepresented",
                    "admUnitCount",
                    "gjDownloadURL",
                    "boundaryCanonical",
                    "buildDate",
                )
            }
            gj = info["gjDownloadURL"]
            dest = self.raw_dir / f"geoBoundaries-{self.s.country_iso3}-{level}.geojson"
            # GitHub raw files: robots.txt on github.com is for crawlers of HTML pages; raw downloads
            # through the geoBoundaries API are the documented access method.
            self.http.download(gj, dest, force=self.force)
            files.append((dest, gj))
        (self.raw_dir / "api_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        files.append((self.raw_dir / "api_metadata.json", API.format(iso=self.s.country_iso3, level="*")))
        lic = sorted({m["boundaryLicense"] for m in meta.values() if m.get("boundaryLicense")})
        o.licence = "; ".join(lic) if lic else "licence to confirm"
        o.details = {"levels": meta}
        o.files = files
        o.status = "downloaded"
        o.url = API.format(iso=self.s.country_iso3, level="ADM2")

    def validate(self) -> None:
        import geopandas as gpd

        for level in self.LEVELS:
            p = self.raw_dir / f"geoBoundaries-{self.s.country_iso3}-{level}.geojson"
            if not p.exists():
                raise ValidationError(f"{p.name} missing")
            gdf = gpd.read_file(p)
            if len(gdf) == 0:
                raise ValidationError(f"{p.name} has no features")
            if "shapeName" not in gdf.columns:
                raise ValidationError(f"{p.name} has no shapeName column")
            if not gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all():
                raise ValidationError(f"{p.name} contains non-polygon geometries")

    def process(self) -> None:
        import geopandas as gpd

        o = self.outcome
        total = 0
        names = {"ADM0": "Country boundary", "ADM1": "Provinces", "ADM2": "Districts"}
        for level in self.LEVELS:
            gdf = gpd.read_file(self.raw_dir / f"geoBoundaries-{self.s.country_iso3}-{level}.geojson")
            total += len(gdf)
            keep = gdf[["shapeName", "shapeID", "geometry"]].copy()
            if level == "ADM0":
                sub = keep  # whole country for the overview map
            else:
                sub = clip_to_bbox(keep, self.bbox, clip=False)  # whole districts, not cut
            table = f"admin_{level.lower()}"
            n = write_vector(sub, self.gpkg, table)
            o.layers.append(
                LayerSpec(
                    id=table,
                    name=names[level],
                    kind="vector",
                    group="base",
                    gpkg_table=table,
                    geometry_type="Polygon",
                    feature_count=n,
                    attribution=self.attribution,
                    style={
                        "type": "line",
                        "color": "#6b7280" if level != "ADM0" else "#1E3A5F",
                        "width": 2 if level == "ADM0" else 1,
                        "dash": level == "ADM2",
                    },
                    description=f"{names[level]} ({level}); {n} features in or around the pilot area.",
                )
            )
        o.record_count = total
        gdf0 = gpd.read_file(self.raw_dir / f"geoBoundaries-{self.s.country_iso3}-ADM0.geojson")
        o.bbox = [round(v, 4) for v in gdf0.total_bounds.tolist()]
