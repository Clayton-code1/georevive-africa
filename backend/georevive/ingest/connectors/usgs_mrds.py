from __future__ import annotations

import zipfile

from ..base import Connector, LayerSpec, ValidationError
from ..http import RobotsDisallowed
from ..process import clip_to_bbox, write_vector

CSV_ZIP = "https://mrdata.usgs.gov/mrds/mrds-csv.zip"
MANUAL_HOW = (
    "MRDS is public domain, but its website forbids automated downloads. A person can download it:\n"
    "1. In a browser, open https://mrdata.usgs.gov/mrds/ and, under Downloads, click 'mrds-csv.zip' "
    "(CSV, about 23 MB).\n"
    "2. Save the file as data\\inbox\\usgs\\mrds-csv.zip (inside the GeoRevive folder).\n"
    "3. Re-run: .\\.venv\\Scripts\\python.exe -m georevive.ingest --source usgs_mrds"
)
REQUIRED = {"dep_id", "site_name", "latitude", "longitude", "country", "commod1", "dev_stat"}


def is_commodity(row, commodity: str) -> bool:
    c = commodity.lower()
    for k in ("commod1", "commod2", "commod3"):
        v = row.get(k)
        if isinstance(v, str) and c in v.lower():
            return True
    return False


class UsgsMrdsConnector(Connector):
    id = "usgs_mrds"
    name = "USGS Mineral Resources Data System (MRDS) - Zimbabwe"
    publisher = "U.S. Geological Survey"
    url = "https://mrdata.usgs.gov/mrds/"
    licence = "Public domain (U.S. Government work)"
    licence_url = "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits"
    attribution = "Mineral occurrences: USGS MRDS (Mason & Arndt 1996; McFaul et al. 2000)"
    note = (
        "Known mineral occurrences, prospects and mines (points). USGS stopped systematic updates in 2011, "
        "so records reflect historical compilations and locations can be approximate."
    )
    usage = (
        "Known gold occurrences are the training positives for the data-driven model and the validation set "
        "for both models (never an input feature)."
    )

    def fetch(self) -> None:
        o = self.outcome
        dest = self.raw_dir / "mrds-csv.zip"
        manual = self.manual_dir("usgs") / "mrds-csv.zip"
        o.url = CSV_ZIP
        if manual.exists():
            self.adopt_manual(manual, dest)
            self.http.note(CSV_ZIP, "supplied manually (browser download) in data/inbox/usgs/")
            o.note_extra = (
                "Downloaded by a team member in a browser (mrdata.usgs.gov robots.txt forbids automated download)."
            )
        elif not dest.exists():
            try:
                self.http.download(CSV_ZIP, dest, force=self.force, max_bytes=200_000_000)
            except RobotsDisallowed:
                o.status = "needs_manual_request"
                o.error = (
                    "mrdata.usgs.gov/robots.txt disallows all automated agents (User-agent: * / Disallow: /), "
                    "so GeoRevive does not download MRDS by script."
                )
                o.how_to_obtain = MANUAL_HOW
                return
        o.files = [(dest, CSV_ZIP)]
        o.status = "downloaded"

    def _read(self):
        import pandas as pd

        with zipfile.ZipFile(self.raw_dir / "mrds-csv.zip") as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValidationError("mrds-csv.zip contains no CSV file")
            with z.open(names[0]) as f:
                return pd.read_csv(f, dtype=str, low_memory=False, encoding="latin-1")

    def validate(self) -> None:
        df = self._read()
        missing = REQUIRED - set(df.columns)
        if missing:
            raise ValidationError(f"MRDS CSV is missing expected columns: {sorted(missing)}")
        if len(df) < 1000:
            raise ValidationError(f"MRDS CSV has only {len(df)} rows; expected the global database")

    def process(self) -> None:
        import geopandas as gpd
        import pandas as pd

        o = self.outcome
        df = self._read()
        zw = df[df["country"].fillna("").str.strip().str.lower() == "zimbabwe"].copy()
        zw["latitude"] = pd.to_numeric(zw["latitude"], errors="coerce")
        zw["longitude"] = pd.to_numeric(zw["longitude"], errors="coerce")
        zw = zw.dropna(subset=["latitude", "longitude"])
        commodity = self.s.section("prospectivity").get("commodity", "gold")
        zw["is_gold"] = zw.apply(lambda r: is_commodity(r, commodity), axis=1)
        keep = [
            "dep_id",
            "mrds_id",
            "site_name",
            "latitude",
            "longitude",
            "commod1",
            "commod2",
            "commod3",
            "dev_stat",
            "oper_type",
            "dep_type",
            "ore",
            "work_type",
            "hrock_type",
            "hrock_unit",
            "structure",
            "alteratn",
            "url",
            "is_gold",
        ]
        keep = [c for c in keep if c in zw.columns]
        gdf = gpd.GeoDataFrame(zw[keep], geometry=gpd.points_from_xy(zw["longitude"], zw["latitude"]), crs="EPSG:4326")
        gdf["is_gold"] = gdf["is_gold"].astype(int)
        n_zw = write_vector(gdf, self.gpkg, "mrds_zimbabwe")
        pilot = clip_to_bbox(gdf, self.bbox)
        n_pilot = write_vector(pilot, self.gpkg, "mrds_occurrences")
        n_gold_zw = int(gdf["is_gold"].sum())
        n_gold_pilot = int(pilot["is_gold"].sum()) if len(pilot) else 0
        o.record_count = n_zw
        o.bbox = [round(v, 4) for v in gdf.total_bounds.tolist()] if n_zw else None
        o.details = {
            "global_rows": int(len(df)),
            "zimbabwe_records": n_zw,
            "zimbabwe_gold_records": n_gold_zw,
            "pilot_records": n_pilot,
            "pilot_gold_records": n_gold_pilot,
            "dev_stat_pilot": pilot["dev_stat"].value_counts().to_dict() if len(pilot) else {},
        }
        o.note_extra = (
            f"Zimbabwe: {n_zw} records ({n_gold_zw} list {commodity}). Pilot area: {n_pilot} records "
            f"({n_gold_pilot} {commodity})."
        )
        o.layers.append(
            LayerSpec(
                id="mrds_occurrences",
                name="Known mineral occurrences (USGS MRDS)",
                kind="vector",
                group="occurrences",
                gpkg_table="mrds_occurrences",
                geometry_type="Point",
                feature_count=n_pilot,
                attribution=self.attribution,
                style={
                    "type": "circle",
                    "color": "#B7791F",
                    "radius": 5,
                    "stroke": "#1E3A5F",
                    "highlight_field": "is_gold",
                },
                legend={
                    "type": "categorical",
                    "items": [
                        {"label": f"{commodity.title()} listed", "color": "#B7791F"},
                        {"label": "Other commodities", "color": "#9ca3af"},
                    ],
                },
                description=f"{n_pilot} MRDS records in the pilot area, {n_gold_pilot} listing {commodity}.",
            )
        )
