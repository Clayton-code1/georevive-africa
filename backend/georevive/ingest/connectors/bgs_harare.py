from __future__ import annotations

import html
import re

from ..base import Connector, LayerSpec, ValidationError
from ..process import clip_to_bbox, write_vector

NORA_RECORD = "https://nora.nerc.ac.uk/id/eprint/541846/"
NORA_PDF = "https://nora.nerc.ac.uk/id/eprint/541846/1/OR26047.pdf"
NORA_POLICY = "https://nora.nerc.ac.uk/policies.html"
CITATION = (
    "Jansen, M.N.; Reeves, T.; Krabbendam, M.; Piper, S.; Brauns, B. 2026. Digitisation of the 1:100k scale "
    "geological map of Harare, Zimbabwe. Nottingham, UK, British Geological Survey, 23pp. (OR/26/047)"
)

BGS_CONTACT = (
    "The digitised map (GeoPackage) is described in BGS report OR/26/047 but is not offered for public download.\n"
    "1. Email BGS Enquiries: enquiries@bgs.ac.uk (cc the report authors via BGS: M.N. Jansen, T. Reeves, "
    "M. Krabbendam, S. Piper, B. Brauns). Quote 'OR/26/047 Harare 1:100k GeoPackage'.\n"
    "2. The map was digitised for the Zimbabwe Geological Survey (ZGS), which owns the original map: ask ZGS "
    "(Ministry of Mines and Mining Development, Harare) for permission to use the digital version for this prototype.\n"
    "3. State the purpose (UNDP/timbuktoo pre-incubation prototype, non-commercial) and ask for the licence terms in writing.\n"
    "4. When received, save the .gpkg file into data/inbox/bgs/ and re-run: "
    ".\\.venv\\Scripts\\python.exe -m georevive.ingest --source bgs_harare_map"
)
REPORT_HOW = (
    "NORA's policy allows single copies for research/educational/not-for-profit use but forbids robot harvesting, "
    "so GeoRevive does not download the PDF automatically.\n"
    f"1. Open {NORA_RECORD} in a browser and download OR26047.pdf.\n"
    "2. Save it as data/inbox/bgs/OR26047.pdf\n"
    "3. Re-run: .\\.venv\\Scripts\\python.exe -m georevive.ingest --source bgs_or26047_report"
)

DEG_PAT = re.compile(r"(\d{1,2})\s*°\s*(\d{1,2})?\s*['′]?\s*([NSEW])")


class _BgsInbox:
    def inbox(self):
        p = self.s.path("inbox_dir") / "bgs"  # type: ignore[attr-defined]
        p.mkdir(parents=True, exist_ok=True)
        return p


class BgsHarareReportConnector(_BgsInbox, Connector):
    id = "bgs_or26047_report"
    name = "BGS report OR/26/047 - Digitisation of the 1:100k geological map of Harare"
    publisher = "British Geological Survey (UKRI), for the Zimbabwe Geological Survey"
    url = NORA_RECORD
    licence = (
        "NORA access policy: single copy for personal research/study, educational or not-for-profit use with "
        "full citation; no robot harvesting; no commercial sale. © UKRI"
    )
    licence_url = NORA_POLICY
    attribution = CITATION
    note = (
        "23-page report describing the digitised Harare 1:100k map (ZGS Bulletin No. 94): GeoPackage layers for "
        "bedrock polygons, boundaries, faults and seed points, with LEX-RCS unit codes."
    )
    usage = "Documents the pilot-area map; used to confirm the sheet extent and unit codes. Not redistributed."

    def fetch(self) -> None:
        o = self.outcome
        # Metadata page only (metadata reuse is permitted non-commercially with a link to the record)
        r = self.http.get(NORA_RECORD)
        meta = {}
        if r.status_code == 200:
            t = re.search(r"<title>(.*?)</title>", r.text, re.S)
            meta["page_title"] = html.unescape(t.group(1).strip()) if t else None
            meta["gpkg_links_on_page"] = re.findall(r'href="([^"]+\.gpkg)"', r.text)
            meta["pdf_link_listed"] = NORA_PDF in r.text
        o.details = {"nora_metadata": meta, "citation": CITATION}
        pdf = self.inbox() / "OR26047.pdf"
        if pdf.exists():
            o.files = [(pdf, NORA_PDF)]
            o.status = "downloaded"
            o.note_extra = "PDF supplied manually by the team (browser download, per NORA policy)."
        else:
            o.status = "needs_manual_request"
            o.error = "Report PDF not fetched automatically: NORA forbids robot harvesting of full-text items."
            o.how_to_obtain = REPORT_HOW

    def validate(self) -> None:
        import fitz

        pdf = self.inbox() / "OR26047.pdf"
        with fitz.open(pdf) as doc:
            if doc.page_count < 5:
                raise ValidationError(f"expected ~23 pages, found {doc.page_count}")
            text = " ".join(doc[i].get_text() for i in range(min(4, doc.page_count)))
        if "Harare" not in text:
            raise ValidationError("PDF does not mention Harare on its first pages - wrong file?")

    def process(self) -> None:
        import fitz

        o = self.outcome
        with fitz.open(self.inbox() / "OR26047.pdf") as doc:
            o.record_count = doc.page_count
            text = "\n".join(p.get_text() for p in doc)
        coords = DEG_PAT.findall(text)
        o.details["coordinate_mentions"] = ["{}°{}'{}".format(*c) for c in coords[:40]]
        o.details["mentions_bulletin_94"] = "94" in text and "Bulletin" in text


class BgsHarareMapConnector(_BgsInbox, Connector):
    id = "bgs_harare_map"
    name = "BGS digital Harare 1:100k geological map (GeoPackage, ZGS Bulletin No. 94)"
    publisher = "British Geological Survey / Zimbabwe Geological Survey"
    url = NORA_RECORD
    licence = "licence to confirm (not publicly released; terms to be agreed with BGS/ZGS)"
    attribution = "Geology: Zimbabwe Geological Survey Bulletin 94 map, digitised by BGS (OR/26/047)"
    note = "Bedrock geology polygons, boundaries and faults with LEX-RCS codes for the pilot sheet."
    usage = (
        "Primary geology for the pilot area: host-rock (greenstone, mafic-ultramafic) and granite-contact "
        "evidence layers; fault/shear-zone distance layer."
    )

    def fetch(self) -> None:
        o = self.outcome
        gpkgs = sorted(self.inbox().glob("*.gpkg"))
        if not gpkgs:
            o.status = "needs_manual_request"
            o.error = "The GeoPackage is not publicly downloadable (no download link on the NORA record)."
            o.how_to_obtain = BGS_CONTACT
            self.http.note(NORA_RECORD, "no public GeoPackage link")
            return
        o.files = [(p, None) for p in gpkgs]
        o.status = "downloaded"
        o.note_extra = "GeoPackage supplied by BGS/ZGS and placed in data/inbox/bgs/."

    def _layers(self):
        import pyogrio

        g = sorted(self.inbox().glob("*.gpkg"))[0]
        return g, pyogrio.list_layers(g)

    def validate(self) -> None:
        _, layers = self._layers()
        types = [str(t).lower() for _, t in layers]
        if not any("polygon" in t for t in types):
            raise ValidationError("GeoPackage has no polygon layer (bedrock geology)")
        if not any("line" in t for t in types):
            raise ValidationError("GeoPackage has no line layer (faults/boundaries)")

    def process(self) -> None:
        import geopandas as gpd

        o = self.outcome
        g, layers = self._layers()
        total = 0
        for name, gtype in layers:
            gt = str(gtype).lower()
            gdf = gpd.read_file(g, layer=name)
            total += len(gdf)
            if "polygon" in gt and not re.search(r"seed", name, re.I):
                table, label, group = "geology", "Bedrock geology (BGS/ZGS 1:100k)", "geology"
                style = {"type": "fill", "field": "auto_lex", "opacity": 0.55}
                gtn = "Polygon"
            elif "line" in gt and re.search(r"fault|shear|lineament", name, re.I):
                table, label, group = "faults", "Faults and shear zones (BGS/ZGS 1:100k)", "structure"
                style = {"type": "line", "color": "#b91c1c", "width": 1.6}
                gtn = "LineString"
            elif "line" in gt:
                table, label, group = "geology_boundaries", "Geological boundaries (1:100k)", "geology"
                style = {"type": "line", "color": "#374151", "width": 0.6}
                gtn = "LineString"
            else:
                continue
            sub = clip_to_bbox(gdf, self.bbox)
            n = write_vector(sub, self.gpkg, table)
            o.layers.append(
                LayerSpec(
                    id=table,
                    name=label,
                    kind="vector",
                    group=group,
                    gpkg_table=table,
                    geometry_type=gtn,
                    feature_count=n,
                    attribution=self.attribution,
                    style=style,
                    description=f"From GeoPackage layer '{name}'.",
                )
            )
        o.record_count = total
        o.details["gpkg_layers"] = [n for n, _ in layers]
