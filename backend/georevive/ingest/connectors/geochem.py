from __future__ import annotations

import os
import re

from ..base import Connector, LayerSpec, ValidationError
from ..process import write_vector

EARTHCHEM_REST = "https://ecp.iedadata.org/restsearchservice"
BGS_GEOCHEM_DGU = (
    "https://www.data.gov.uk/dataset/756d6426-d52d-492a-a263-599ad1caa123/zimbabwe-regional-geochemical-survey"
)
BGS_GEOCHEM_PAGE = (
    "https://www.bgs.ac.uk/geology-projects/applied-geochemistry/international-geochemistry-cd-rom/"
    "zimbabwe-regional-geochemical-survey/"
)


class EarthChemConnector(Connector):
    id = "earthchem"
    name = "EarthChem Portal - rock geochemistry samples in the pilot area"
    publisher = "EarthChem / IEDA (Lamont-Doherty Earth Observatory)"
    url = "https://www.earthchem.org/"
    licence = "CC BY 4.0 for EarthChem Library data (per-dataset; licence to confirm per sample source)"
    licence_url = "https://www.earthchem.org/about/policies/"
    attribution = "Geochemistry: EarthChem Portal (and original publications)"
    note = "Published whole-rock and mineral analyses with coordinates."
    usage = "Optional context layer (sample locations and Au/As/Cu values where reported)."
    optional = True

    def fetch(self) -> None:
        o = self.outcome
        w, s, e, n = self.bbox
        url = (
            f"{EARTHCHEM_REST}?outputtype=json&searchtype=rowdata&standarditems=yes&westlongitude={w}"
            f"&eastlongitude={e}&southlatitude={s}&northlatitude={n}"
        )
        try:
            r = self.http.get(url, timeout=90)
        except Exception as ex:
            o.status = "failed"
            o.error = f"EarthChem REST search unreachable: {type(ex).__name__}: {ex}"[:400]
            o.how_to_obtain = (
                "Use the EarthChem Portal web search (https://portal.earthchem.org/) with the pilot "
                "bounding box, export CSV, and drop it into data/inbox/ with the citation details."
            )
            return
        if r.status_code != 200 or not r.text.strip().startswith(("[", "{")):
            o.status = "failed"
            o.error = f"EarthChem REST search returned HTTP {r.status_code} (service may be retired)."
            o.how_to_obtain = (
                "Use the EarthChem Portal web search (https://portal.earthchem.org/) with the pilot "
                "bounding box, export CSV, and drop it into data/inbox/ with the citation details."
            )
            return
        dest = self.raw_dir / "earthchem_pilot.json"
        dest.write_bytes(r.content)
        o.files = [(dest, url)]
        o.status = "downloaded"

    def validate(self) -> None:
        import json

        data = json.loads((self.raw_dir / "earthchem_pilot.json").read_text(encoding="utf-8"))
        if not isinstance(data, list | dict):
            raise ValidationError("unexpected JSON structure")

    def process(self) -> None:
        import json

        import geopandas as gpd
        import pandas as pd

        o = self.outcome
        data = json.loads((self.raw_dir / "earthchem_pilot.json").read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("data", [])
        df = pd.DataFrame(rows)
        o.record_count = len(df)
        if not len(df):
            o.note_extra = "Zero samples found in the pilot area."
            return
        lat = next((c for c in df.columns if c.lower() == "latitude"), None)
        lon = next((c for c in df.columns if c.lower() == "longitude"), None)
        if lat is None or lon is None:
            o.note_extra = "Samples returned without coordinate columns."
            return
        df[lat] = pd.to_numeric(df[lat], errors="coerce")
        df[lon] = pd.to_numeric(df[lon], errors="coerce")
        df = df.dropna(subset=[lat, lon])
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs="EPSG:4326")
        n = write_vector(gdf, self.gpkg, "geochem_samples")
        o.layers.append(
            LayerSpec(
                id="geochem_samples",
                name="Geochemistry samples (EarthChem)",
                kind="vector",
                group="context",
                gpkg_table="geochem_samples",
                geometry_type="Point",
                feature_count=n,
                attribution=self.attribution,
                style={"type": "circle", "color": "#0f766e", "radius": 3},
            )
        )


class GeorocConnector(Connector):
    id = "georoc"
    name = "GEOROC - Geochemistry of Rocks of the Oceans and Continents"
    publisher = "DIGIS project, University of Göttingen"
    url = "https://georoc.eu/"
    licence = "CC BY-SA 4.0 for GEOROC compilations (licence to confirm)"
    note = "Global compilation of published rock geochemistry."
    usage = "Optional context: published analyses of Harare greenstone belt rocks, if any."
    optional = True

    def fetch(self) -> None:
        o = self.outcome
        if not os.environ.get("GEOROC_API_KEY"):
            o.status = "needs_credentials"
            o.error = "The GEOROC API requires an API key issued by the DIGIS GEOROC team."
            o.how_to_obtain = (
                "1. Request an API key from the DIGIS GEOROC team (contact via https://georoc.eu/).\n"
                "2. Or use the GEOROC web interface to search by coordinates (the pilot bounding box), download "
                "the CSV, and drop it into data/inbox/ with the citation details."
            )
            return
        o.status = "needs_manual_request"
        o.error = "GEOROC_API_KEY is set, but automated GEOROC queries are not implemented in this prototype."
        o.how_to_obtain = "Download a CSV from the GEOROC web interface and add it through data/inbox/."

    def validate(self) -> None:
        pass


class BgsZimGeochemConnector(Connector):
    id = "bgs_zimbabwe_geochem"
    name = "Zimbabwe Regional Geochemical Survey (1982-86) - BGS international geochemistry CD-ROM"
    publisher = "British Geological Survey / Zimbabwe Geological Survey"
    url = BGS_GEOCHEM_PAGE
    licence = "licence to confirm with BGS"
    note = "Regional stream-sediment geochemistry survey covering parts of Zimbabwe including the Harare area."
    usage = "Potential geochemical evidence layer (e.g. Au, As pathfinders) once obtained."
    optional = True

    def fetch(self) -> None:
        o = self.outcome
        links = []
        try:
            r = self.http.get(BGS_GEOCHEM_DGU)
            if r.status_code == 200:
                links = re.findall(r'href="(https?://[^"]+\.(?:zip|csv|xlsx?))"', r.text)
        except Exception as e:
            o.details["data_gov_uk_error"] = str(e)[:200]
        o.details["download_links_found"] = links
        o.status = "needs_manual_request"
        o.error = (
            "Distributed by BGS on request (international geochemistry CD-ROM); no open download link found."
            if not links
            else "Download links found but licence terms must be confirmed before use."
        )
        o.how_to_obtain = (
            f"1. See {BGS_GEOCHEM_PAGE}\n"
            "2. Email enquiries@bgs.ac.uk asking for the Zimbabwe Regional Geochemical Survey data covering the "
            "Harare sheet, its licence terms and any charges.\n"
            "3. Save the files into data/inbox/ and enter the licence details when prompted."
        )

    def validate(self) -> None:
        pass
