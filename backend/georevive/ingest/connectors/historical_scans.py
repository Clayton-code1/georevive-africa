from __future__ import annotations

import json
import re
from urllib.parse import quote

from ..base import Connector, ValidationError

IA_SEARCH = "https://archive.org/advancedsearch.php"
IA_META = "https://archive.org/metadata/{id}"
IA_DL = "https://archive.org/download/{id}/{name}"
QUERIES = [
    "(title:(Rhodesia) AND (title:(geology) OR title:(geological) OR title:(gold) OR title:(mineral) OR "
    "title:(mines) OR subject:(geology))) AND mediatype:texts",
    '("Geological Survey" AND (Rhodesia OR Zimbabwe OR Mashonaland)) AND mediatype:texts',
    '(subject:("Geology -- Zimbabwe") OR subject:("Geology -- Rhodesia") OR subject:("Mines and mineral resources -- Zimbabwe")) AND mediatype:texts',
]
MAX_PDF_BYTES = 90_000_000


def is_open_item(doc: dict) -> tuple[bool, str]:
    """Only items Internet Archive flags as public domain / not in copyright, or under an open licence."""
    lic = str(doc.get("licenseurl") or "")
    pcs = str(doc.get("possible-copyright-status") or "")
    rights = str(doc.get("rights") or "")
    if re.search(r"publicdomain|creativecommons\.org/(licenses/by|publicdomain)", lic, re.I):
        return True, lic
    if re.search(r"not[_ ]in[_ ]copyright|public domain|no known copyright", pcs + " " + rights, re.I):
        return True, (pcs or rights)
    return False, lic or pcs or rights or "no rights statement"


def is_relevant(title: str) -> bool:
    return bool(re.search(r"rhodesia|zimbabwe|mashonaland|matabeleland", title, re.I)) and bool(
        re.search(r"geolog|gold|mine|mineral|natural resources", title, re.I)
    )


class InternetArchiveConnector(Connector):
    id = "internet_archive_scans"
    name = "Historical geological publications on Internet Archive (public-domain items only)"
    publisher = "Internet Archive (digitised by contributing libraries)"
    url = "https://archive.org/"
    licence = "Per item: only items flagged public domain / not in copyright are downloaded (see details)"
    licence_url = "https://archive.org/about/terms.php"
    attribution = "Scans courtesy of the Internet Archive and contributing libraries"
    note = "Scanned historical texts about Rhodesian/Zimbabwean geology, gold mines and mineral resources."
    usage = "Test documents for the data-rescue pipeline (enhancement, OCR, fact extraction, accuracy check)."

    def fetch(self) -> None:
        o = self.outcome
        max_items = int(self.s.section("ingest").get("historical_scans", {}).get("max_items", 5))
        found: dict[str, dict] = {}
        for q in QUERIES:
            url = (
                f"{IA_SEARCH}?q={quote(q)}&fl[]=identifier&fl[]=title&fl[]=date&fl[]=licenseurl"
                f"&fl[]=possible-copyright-status&fl[]=rights&fl[]=collection&rows=100&output=json"
            )
            try:
                docs = self.http.get_json(url).get("response", {}).get("docs", [])
            except Exception as e:
                o.details.setdefault("search_errors", []).append(str(e)[:200])
                continue
            for d in docs:
                found.setdefault(d["identifier"], d)
        candidates, rejected = [], []
        for ident, d in found.items():
            title = str(d.get("title", ""))
            if not is_relevant(title):
                continue
            ok, why = is_open_item(d)
            (candidates if ok else rejected).append(
                {"identifier": ident, "title": title, "date": d.get("date"), "rights": why}
            )
        o.details["candidates_open"] = candidates
        o.details["not_downloaded_rights_unclear"] = rejected
        files = []
        downloaded = []
        for c in candidates[:max_items]:
            try:
                meta = self.http.get_json(IA_META.format(id=c["identifier"]))
            except Exception as e:
                c["error"] = str(e)[:200]
                continue
            pdfs = [f for f in meta.get("files", []) if str(f.get("name", "")).lower().endswith(".pdf")]
            pdfs.sort(key=lambda f: int(f.get("size") or 1e12))
            if not pdfs:
                c["error"] = "no PDF file in item"
                continue
            f = pdfs[0]
            if int(f.get("size") or 0) > MAX_PDF_BYTES:
                c["error"] = f"PDF too large ({int(f['size']) / 1e6:.0f} MB)"
                continue
            dl = IA_DL.format(id=c["identifier"], name=quote(f["name"]))
            dest = self.raw_dir / c["identifier"] / f["name"]
            try:
                self.http.download(dl, dest, force=self.force, max_bytes=MAX_PDF_BYTES)
            except Exception as e:
                c["error"] = str(e)[:200]
                continue
            (dest.parent / "item_metadata.json").write_text(
                json.dumps(meta.get("metadata", {}), indent=2), encoding="utf-8"
            )
            files += [(dest, dl), (dest.parent / "item_metadata.json", IA_META.format(id=c["identifier"]))]
            c["pdf"] = dest.relative_to(self.raw_dir).as_posix()
            downloaded.append(c)
        self.write_manifest({"downloaded": downloaded})
        o.files = files + [(self.manifest_path(), None)]
        o.details["downloaded"] = downloaded
        o.record_count = len(downloaded)
        if downloaded:
            o.status = "downloaded" if len(downloaded) == len(candidates[:max_items]) else "partial"
            o.note_extra = "Items: " + "; ".join(
                f"{d['title'][:70]} ({str(d.get('date', ''))[:4]})" for d in downloaded
            )
        else:
            o.status = "failed"
            o.error = "No relevant item with an explicit public-domain or open-licence flag could be downloaded."

    def validate(self) -> None:
        import fitz

        for d in self.read_manifest().get("downloaded", []):
            p = self.raw_dir / d["pdf"]
            with fitz.open(p) as doc:
                if doc.page_count == 0:
                    raise ValidationError(f"{p.name} has no pages")
                d["pages"] = doc.page_count

    def process(self) -> None:
        import fitz

        m = self.read_manifest()
        for d in m.get("downloaded", []):
            with fitz.open(self.raw_dir / d["pdf"]) as doc:
                d["pages"] = doc.page_count
        self.write_manifest(m)
        self.outcome.details["downloaded"] = m.get("downloaded", [])
        self.outcome.raster_size = f"{sum(d.get('pages', 0) for d in m.get('downloaded', []))} scanned pages"


class HathiTrustConnector(Connector):
    id = "hathitrust_scans"
    name = "HathiTrust Digital Library - Southern Rhodesia Geological Survey bulletins"
    publisher = "HathiTrust"
    url = (
        "https://catalog.hathitrust.org/Search/Home?lookfor=%22Southern%20Rhodesia%22%20%22Geological%20Survey%22"
        "&type=all"
    )
    licence = "Per volume; full view only for public-domain volumes; automated bulk download not permitted"
    licence_url = "https://www.hathitrust.org/the-collection/terms-conditions/acceptable-use-policy/"
    note = "Catalogue of digitised Southern Rhodesia / Rhodesia Geological Survey bulletins and short reports."
    usage = "Candidate test documents for data rescue, to be downloaded manually page by page where full view."

    def fetch(self) -> None:
        o = self.outcome
        allowed = self.http.robots_allowed(self.url)
        o.details["robots_allows_catalogue_search"] = allowed
        o.status = "needs_manual_request"
        o.error = (
            "HathiTrust's acceptable-use policy does not allow automated bulk downloading; GeoRevive does not "
            "scrape it."
        )
        o.how_to_obtain = (
            f"1. Open {self.url} and tick 'Full view only'.\n"
            "2. For each public-domain bulletin, use 'Download > This page (PDF)' for the pages you need "
            "(e.g. pages describing gold deposits, with assay tables).\n"
            "3. Save the PDFs into data/inbox/ and record the HathiTrust URL and rights statement when the app asks.\n"
            "4. Volumes in 'Limited (search only)' need a request to the holding library or the Zimbabwe Geological Survey."
        )

    def validate(self) -> None:
        pass


class ZgsBulletinsConnector(Connector):
    id = "zgs_bulletins"
    name = "Zimbabwe Geological Survey Bulletin No. 94 and related short reports (paper)"
    publisher = "Zimbabwe Geological Survey"
    url = "https://www.bgs.ac.uk/"
    licence = "© Zimbabwe Geological Survey - permission required"
    note = "The explanatory bulletin for the Harare 1:100 000 sheet and older reports on the Harare greenstone belt."
    usage = "Primary documents for data rescue of the pilot area once scanned with permission."

    def fetch(self) -> None:
        o = self.outcome
        o.status = "needs_manual_request"
        o.error = "No openly downloadable digital copy was found."
        o.how_to_obtain = (
            "1. Zimbabwe Geological Survey (Ministry of Mines and Mining Development, Harare): request a copy of "
            "Bulletin No. 94 and permission to scan selected pages for this prototype. Confirm current contact "
            "details through the Ministry.\n"
            "2. BGS library (enquiries@bgs.ac.uk) holds many ZGS bulletins and may advise on access.\n"
            "3. University of Zimbabwe Geology Department library may hold copies.\n"
            "4. Scan at 300-400 dpi, save into data/inbox/ and enter the source and permission details when uploading."
        )

    def validate(self) -> None:
        pass
