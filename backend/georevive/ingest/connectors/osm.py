from __future__ import annotations

import json

from ..base import Connector, LayerSpec, ValidationError
from ..process import write_vector

# Public Overpass instances whose robots.txt permits /api/ (checked again on every run).
# overpass-api.de is NOT used: its robots.txt has "Disallow: /api/".
OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
GEOFABRIK_PBF = "https://download.geofabrik.de/africa/zimbabwe-latest.osm.pbf"
PLACE_CLASSES = {"city", "town", "suburb", "village", "hamlet", "locality", "farm", "isolated_dwelling"}
MAX_PBF = 300_000_000

ROAD_CLASSES = "motorway|trunk|primary|secondary|tertiary|unclassified|motorway_link|trunk_link|primary_link"


PARTS = {
    "roads": ['way["highway"~"^({roads})$"]({b});'],
    "waterways": ['way["waterway"~"^(river|stream)$"]({b});'],
    "places": ['node["place"~"^(city|town|suburb|village|hamlet|locality|farm|isolated_dwelling)$"]({b});'],
    "mines": [
        'node["landuse"="quarry"]({b});',
        'way["landuse"="quarry"]({b});',
        'node["man_made"~"^(mineshaft|adit)$"]({b});',
        'node["historic"="mine"]({b});',
    ],
}


def overpass_query(bbox: tuple[float, float, float, float], part: str | None = None) -> str:
    """One query per feature group keeps each request small for the public Overpass servers."""
    w, s, e, n = bbox
    b = f"{s},{w},{n},{e}"
    parts = [part] if part else list(PARTS)
    stmts = "\n  ".join(st.format(b=b, roads=ROAD_CLASSES) for p in parts for st in PARTS[p])
    return f"[out:json][timeout:120];\n(\n  {stmts}\n);\nout geom tags;\n"


class OsmConnector(Connector):
    id = "osm"
    name = "OpenStreetMap - roads, places, rivers and mapped mine features"
    publisher = "OpenStreetMap contributors (via Overpass API)"
    url = OVERPASS_URLS[0]
    licence = "Open Database Licence (ODbL) 1.0"
    licence_url = "https://www.openstreetmap.org/copyright"
    attribution = "© OpenStreetMap contributors (ODbL)"
    note = "Roads, towns/villages/farms/localities, rivers and streams, and mapped quarries/mine shafts."
    usage = "Access and context on the map and in claim reports; place and farm names for offline geocoding of rescued facts."

    def fetch(self) -> None:
        o = self.outcome
        import time

        dest = self.raw_dir / "overpass.json"
        pbf = self.raw_dir / "zimbabwe-latest.osm.pbf"
        if dest.exists() and not self.force:
            self.http.note(self.url, "cached: overpass.json")
        elif pbf.exists() and not self.force:
            # a Geofabrik extract is already on disk: build every feature group from it (one clear provenance)
            self.http.note(GEOFABRIK_PBF, "cached: zimbabwe-latest.osm.pbf")
            els = self._from_geofabrik(set(PARTS))
            dest.write_text(
                json.dumps({"elements": els, "failed_parts": {}, "sources_used": {p: GEOFABRIK_PBF for p in PARTS}}),
                encoding="utf-8",
            )
        else:
            elements: dict[tuple, dict] = {}
            failed: dict[str, str] = {}
            used: dict[str, str] = {}  # feature group -> where it came from (provenance)
            for part in PARTS:
                q = overpass_query(self.bbox, part)
                (self.raw_dir / f"query_{part}.overpassql").write_text(q, encoding="utf-8")
                err = None
                for attempt in range(2 * len(OVERPASS_URLS)):
                    url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
                    try:
                        r = self.http.post(url, data={"data": q}, timeout=180)
                        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
                            for el in r.json().get("elements", []):
                                elements[(el["type"], el["id"])] = el
                            used[part] = url
                            err = None
                            break
                        err = f"HTTP {r.status_code}"
                    except Exception as e:  # try again / next mirror
                        err = f"{type(e).__name__}: {e}"[:200]
                    time.sleep(15 * (attempt + 1))  # Overpass asks clients to back off when busy
                if err:
                    failed[part] = err
            if failed:
                try:  # fallback: the Geofabrik Zimbabwe extract, read for the pilot bbox only
                    for el in self._from_geofabrik(set(failed)):
                        elements[(el["type"], el["id"])] = el
                    used.update({p: GEOFABRIK_PBF for p in failed})
                    failed = {}
                except Exception as e:
                    failed["geofabrik_fallback"] = f"{type(e).__name__}: {e}"[:200]
            if not elements:
                raise RuntimeError(f"All OpenStreetMap requests failed: {failed}")
            dest.write_text(
                json.dumps({"elements": list(elements.values()), "failed_parts": failed, "sources_used": used}),
                encoding="utf-8",
            )
        data = json.loads(dest.read_text(encoding="utf-8"))
        failed = data.get("failed_parts", {})
        used = data.get("sources_used", {})
        o.details["sources_used"] = used
        o.url = GEOFABRIK_PBF if GEOFABRIK_PBF in used.values() else (next(iter(used.values()), None) or self.url)
        if used:
            o.note_extra = "Feature groups from: " + "; ".join(f"{k}: {v}" for k, v in used.items())
        o.files = [(dest, o.url or self.url)] + [(p, None) for p in sorted(self.raw_dir.glob("query_*.overpassql"))]
        o.status = "partial" if failed else "downloaded"
        if failed:
            o.error = f"Some feature groups could not be downloaded: {failed}. Re-run --source osm --force later."
        o.bbox = list(self.bbox)

    def _from_geofabrik(self, parts: set[str]) -> list[dict]:
        """Read the requested feature groups from the Geofabrik .osm.pbf (GDAL OSM driver), converted to
        Overpass-style elements so the rest of the connector is unchanged."""
        import pyogrio

        pbf = self.raw_dir / "zimbabwe-latest.osm.pbf"
        self.http.download(GEOFABRIK_PBF, pbf, max_bytes=MAX_PBF)
        out: list[dict] = []
        want_lines = parts & {"roads", "waterways"}
        want_points = parts & {"places", "mines"}
        road_set = set(ROAD_CLASSES.split("|"))
        if want_lines:
            df = pyogrio.read_dataframe(pbf, layer="lines", bbox=self.bbox)
            for i, r in df.iterrows():
                tags = {}
                if "roads" in parts and r.get("highway") in road_set:
                    tags = {"highway": r["highway"], "name": r.get("name")}
                elif "waterways" in parts and r.get("waterway") in ("river", "stream"):
                    tags = {"waterway": r["waterway"], "name": r.get("name")}
                if tags:
                    coords = list(r.geometry.coords)
                    out.append(
                        {
                            "type": "way",
                            "id": int(r.get("osm_id") or i),
                            "tags": tags,
                            "geometry": [{"lon": x, "lat": y} for x, y in coords],
                        }
                    )
        if want_points:
            df = pyogrio.read_dataframe(pbf, layer="points", bbox=self.bbox)
            for i, r in df.iterrows():
                other = str(r.get("other_tags") or "")
                tags = {}
                man_made = str(r.get("man_made") or "")  # GDAL's default osmconf gives man_made its own column
                if "places" in parts and r.get("place") in PLACE_CLASSES:  # same classes as the Overpass query
                    tags = {"place": r["place"], "name": r.get("name")}
                elif "mines" in parts and (
                    man_made in ("mineshaft", "adit")
                    or '"man_made"=>"mineshaft"' in other
                    or '"historic"=>"mine"' in other
                    or '"landuse"=>"quarry"' in other
                ):
                    kind = man_made or ("mine" if '"historic"=>"mine"' in other else "quarry")
                    tags = {
                        "man_made": kind if kind in ("mineshaft", "adit") else None,
                        "historic": "mine" if kind == "mine" else None,
                        "landuse": "quarry" if kind == "quarry" else None,
                        "name": r.get("name"),
                    }
                if tags:
                    out.append(
                        {
                            "type": "node",
                            "id": int(r.get("osm_id") or i),
                            "lon": r.geometry.x,
                            "lat": r.geometry.y,
                            "tags": {k: v for k, v in tags.items() if v},
                        }
                    )
        if "mines" in parts:  # quarries are usually mapped as areas -> GDAL 'multipolygons' layer
            df = pyogrio.read_dataframe(pbf, layer="multipolygons", bbox=self.bbox)
            if "landuse" in df.columns:
                for i, r in df[df["landuse"] == "quarry"].iterrows():
                    pt = r.geometry.representative_point()
                    oid = r.get("osm_way_id") or r.get("osm_id") or i
                    out.append(
                        {
                            "type": "way",
                            "id": int(oid),
                            "tags": {"landuse": "quarry", "name": r.get("name")},
                            "geometry": [{"lon": x, "lat": y} for x, y in r.geometry.exterior.coords]
                            if r.geometry.geom_type == "Polygon"
                            else [{"lon": pt.x, "lat": pt.y}] * 4,
                        }
                    )
        return out

    def validate(self) -> None:
        p = self.raw_dir / "overpass.json"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValidationError(f"overpass.json is not valid JSON: {e}") from e
        if "elements" not in data:
            raise ValidationError("Overpass response has no 'elements'")
        if not data["elements"]:
            raise ValidationError("Overpass returned zero features for the pilot area")

    @staticmethod
    def to_frames(data: dict):
        import geopandas as gpd
        from shapely.geometry import LineString, Point, Polygon

        roads, rivers, places, mines = [], [], [], []
        for el in data["elements"]:
            tags = el.get("tags", {})
            if el["type"] == "node":
                geom = Point(el["lon"], el["lat"])
            elif el["type"] == "way" and el.get("geometry"):
                coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
                if len(coords) < 2:
                    continue
                closed = coords[0] == coords[-1] and len(coords) >= 4
                geom = Polygon(coords) if closed and tags.get("landuse") == "quarry" else LineString(coords)
            else:
                continue
            row = {"osm_id": f"{el['type']}/{el['id']}", "name": tags.get("name"), "geometry": geom}
            if "highway" in tags:
                roads.append({**row, "class": tags["highway"], "ref": tags.get("ref"), "surface": tags.get("surface")})
            elif "waterway" in tags:
                rivers.append({**row, "class": tags["waterway"]})
            elif "place" in tags:
                places.append({**row, "class": tags["place"]})
            else:
                kind = tags.get("man_made") or ("quarry" if tags.get("landuse") == "quarry" else tags.get("historic"))
                mines.append({**row, "class": kind, "resource": tags.get("resource")})

        def mk(rows):
            return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326") if rows else None

        return mk(roads), mk(rivers), mk(places), mk(mines)

    def process(self) -> None:
        import geopandas as gpd

        o = self.outcome
        data = json.loads((self.raw_dir / "overpass.json").read_text(encoding="utf-8"))
        roads, rivers, places, mines = self.to_frames(data)
        total = 0
        specs = [
            ("osm_roads", "Roads", roads, "LineString", {"type": "line", "color": "#a0785a", "width": 0.6}),
            (
                "osm_rivers",
                "Rivers and streams",
                rivers,
                "LineString",
                {"type": "line", "color": "#2b7bb9", "width": 1},
            ),
            (
                "osm_places",
                "Towns, villages and farms",
                places,
                "Point",
                {"type": "circle", "color": "#1E3A5F", "radius": 3, "label": "name"},
            ),
            (
                "osm_mine_features",
                "Mapped quarries and mine shafts (OSM)",
                mines,
                "Point",
                {"type": "circle", "color": "#6b21a8", "radius": 3},
            ),
        ]
        for table, name, gdf, gtype, style in specs:
            if gdf is None or len(gdf) == 0:
                continue
            if table == "osm_mine_features":
                gdf = gdf.copy()
                gdf["geometry"] = gdf.geometry.representative_point()
            n = write_vector(gpd.GeoDataFrame(gdf, crs="EPSG:4326"), self.gpkg, table)
            total += n
            o.layers.append(
                LayerSpec(
                    id=table,
                    name=name,
                    kind="vector",
                    group="context",
                    gpkg_table=table,
                    geometry_type=gtype,
                    feature_count=n,
                    attribution=self.attribution,
                    style=style,
                    description=f"{name} from OpenStreetMap; {n} features.",
                )
            )
        o.record_count = total
        o.details = {"counts": {s[0]: (0 if s[2] is None else len(s[2])) for s in specs}}
