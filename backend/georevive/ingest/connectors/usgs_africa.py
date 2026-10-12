from __future__ import annotations

import re
import zipfile
from pathlib import Path

from ..base import Connector, LayerSpec, ValidationError
from ..process import clip_to_bbox, write_vector

ITEM_ID = "607611a9d34e018b3201cbbf"
ITEM_URL = f"https://www.sciencebase.gov/catalog/item/{ITEM_ID}"
ITEM_JSON = f"https://www.sciencebase.gov/catalog/item/{ITEM_ID}?format=json"
CHILDREN_JSON = f"https://www.sciencebase.gov/catalog/items?parentId={ITEM_ID}&format=json&fields=title,files&max=50"
MAX_BYTES = 600_000_000
# layers that describe mineral sites (others - roads, power, ports - are not needed here)
SITE_PAT = re.compile(r"(minfac|mineral|facilit|explor|occurr|deposit|mine)", re.I)


def _files_of(item: dict) -> list[dict]:
    out = []
    for f in item.get("files", []) or []:
        out.append({"name": f.get("name"), "url": f.get("downloadUri") or f.get("url"), "size": f.get("size")})
    return out


class UsgsAfricaMineralsConnector(Connector):
    id = "usgs_africa_minerals"
    name = "USGS Compilation of Geospatial Data for the Mineral Industries and Related Infrastructure of Africa"
    publisher = "U.S. Geological Survey, National Minerals Information Center"
    url = ITEM_URL
    licence = (
        "Public domain (U.S. Government work); some layers compiled from third-party sources - check layer metadata"
    )
    licence_url = "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits"
    attribution = "Mineral facilities: USGS NMIC Africa geospatial compilation (2021)"
    note = "Mineral production/processing facilities and exploration/development sites in Africa (reference year 2018)."
    usage = "Additional known sites for validation and context; points inside the pilot area are shown on the map."

    def fetch(self) -> None:
        o = self.outcome
        manual = sorted(self.manual_dir("usgs/africa").glob("*.zip"))
        if manual:
            dest = self.adopt_manual(manual[0], self.raw_dir / manual[0].name)
            self.http.note(ITEM_URL, f"supplied manually (browser download): {manual[0].name}")
            o.files = [(dest, ITEM_URL)]
            o.status = "downloaded"
            o.note_extra = "Downloaded by a team member in a browser (ScienceBase blocks automated clients)."
            return
        if list(self.raw_dir.glob("*.zip")):
            o.files = [(z, ITEM_URL) for z in sorted(self.raw_dir.glob("*.zip"))]
            o.status = "downloaded"
            return
        r = self.http.get(ITEM_JSON)
        if r.status_code == 403:
            o.status = "needs_manual_request"
            o.error = (
                "ScienceBase answered HTTP 403 to an automated request (bot protection). GeoRevive does not "
                "bypass access controls."
            )
            o.how_to_obtain = (
                "The data are public domain and free to download by a person:\n"
                f"1. In a browser, open {ITEM_URL}\n"
                "2. Download the geodatabase / shapefile .zip listed under 'Attached Files' (or in the child items).\n"
                "3. Save it into data\\inbox\\usgs\\africa\\ (inside the GeoRevive folder).\n"
                "4. Re-run: .\\.venv\\Scripts\\python.exe -m georevive.ingest --source usgs_africa_minerals"
            )
            return
        r.raise_for_status()
        item = r.json()
        files = _files_of(item)
        try:
            kids = self.http.get_json(CHILDREN_JSON).get("items", [])
        except Exception:
            kids = []
        for k in kids:
            files += _files_of(k)
        o.details["files_listed"] = files
        zips = [f for f in files if f["name"] and f["name"].lower().endswith(".zip") and f["url"]]
        if not zips:
            o.status = "failed"
            o.error = "The ScienceBase record lists no downloadable .zip data files."
            return
        # prefer geodatabase / shapefile packages, smallest first
        zips.sort(key=lambda f: (0 if re.search(r"gdb|shp|shape", f["name"], re.I) else 1, f["size"] or 1e12))
        chosen = zips[0]
        if chosen["size"] and chosen["size"] > MAX_BYTES:
            o.status = "needs_manual_request"
            o.error = f"Data package {chosen['name']} is {chosen['size'] / 1e6:.0f} MB, above the automatic limit."
            o.how_to_obtain = f"Download {chosen['name']} manually from {ITEM_URL} and place it in {self.raw_dir}."
            return
        dest = self.raw_dir / chosen["name"]
        self.http.download(chosen["url"], dest, force=self.force, max_bytes=MAX_BYTES)
        o.files = [(dest, chosen["url"])]
        o.status = "downloaded"

    def _dataset_path(self) -> Path:
        zips = sorted(self.raw_dir.glob("*.zip"))
        if not zips:
            raise ValidationError("no zip downloaded")
        z = zips[0]
        out = self.raw_dir / "unzipped"
        if not out.exists():
            with zipfile.ZipFile(z) as zf:
                zf.extractall(out)
        gdbs = list(out.rglob("*.gdb"))
        if gdbs:
            return gdbs[0]
        shps = list(out.rglob("*.shp"))
        if shps:
            return shps[0].parent
        raise ValidationError("zip contains neither a .gdb nor shapefiles")

    def _site_layers(self) -> list[tuple[Path, str]]:
        import pyogrio

        ds = self._dataset_path()
        layers = []
        if ds.suffix.lower() == ".gdb":
            for name, gtype in pyogrio.list_layers(ds):
                if gtype and "point" in str(gtype).lower() and SITE_PAT.search(name):
                    layers.append((ds, name))
        else:
            for shp in ds.glob("*.shp"):
                if SITE_PAT.search(shp.stem):
                    layers.append((shp, shp.stem))
        return layers

    def validate(self) -> None:
        if not self._site_layers():
            raise ValidationError("no mineral-site point layers found in the package")

    def process(self) -> None:
        import geopandas as gpd

        o = self.outcome
        total_zw = 0
        counts = {}
        frames = []
        for path, layer in self._site_layers():
            gdf = gpd.read_file(path, layer=layer) if path.suffix.lower() == ".gdb" else gpd.read_file(path)
            ccol = next((c for c in gdf.columns if c.lower() in ("country", "country_name", "cntry_name")), None)
            if ccol is not None:
                gdf = gdf[gdf[ccol].astype(str).str.lower().str.contains("zimbabwe")]
            else:
                gdf = clip_to_bbox(gdf, (25.2, -22.5, 33.1, -15.6), clip=False)
            counts[layer] = int(len(gdf))
            total_zw += len(gdf)
            if len(gdf):
                gdf = gdf.to_crs("EPSG:4326")
                gdf["dataset_layer"] = layer
                frames.append(gdf)
        o.record_count = total_zw
        o.details["zimbabwe_counts_by_layer"] = counts
        if not frames:
            o.note_extra = "No Zimbabwe records found in the mineral-site layers."
            return
        import pandas as pd

        allz = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
        # keep a compact, readable set of columns
        cols = [
            c
            for c in allz.columns
            if c.lower()
            in (
                "dsg_name",
                "featurenam",
                "feature_name",
                "name",
                "site_name",
                "commodity",
                "ds_commodity",
                "dsg_comm",
                "operatetyp",
                "op_type",
                "status",
                "dsg_status",
                "country",
                "dataset_layer",
                "geometry",
            )
        ]
        allz = allz[cols] if "geometry" in cols else allz
        write_vector(allz, self.gpkg, "usgs_africa_sites_zimbabwe")
        pilot = clip_to_bbox(allz, self.bbox)
        n = write_vector(pilot, self.gpkg, "usgs_africa_sites") if len(pilot) else 0
        o.details["pilot_records"] = n
        o.note_extra = f"Zimbabwe: {total_zw} site records; pilot area: {n}."
        if n:
            o.layers.append(
                LayerSpec(
                    id="usgs_africa_sites",
                    name="Mineral facilities and exploration sites (USGS Africa)",
                    kind="vector",
                    group="occurrences",
                    gpkg_table="usgs_africa_sites",
                    geometry_type="Point",
                    feature_count=n,
                    attribution=self.attribution,
                    style={"type": "circle", "color": "#7c2d12", "radius": 5},
                    description=f"{n} USGS Africa compilation sites in the pilot area.",
                )
            )
