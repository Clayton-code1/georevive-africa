from __future__ import annotations

import os

import requests

from ..base import Connector, ValidationError

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
URS = "urs.earthdata.nasa.gov"
HOW = (
    "1. Create a free NASA Earthdata account at https://urs.earthdata.nasa.gov/users/new\n"
    "2. In Earthdata, approve the 'LP DAAC Data Pool' application (Profile > Applications > Authorized Apps).\n"
    "3. Add EARTHDATA_USERNAME and EARTHDATA_PASSWORD to the .env file in the GeoRevive folder.\n"
    "4. Re-run:  .\\.venv\\Scripts\\python.exe -m georevive.ingest --source aster"
)


class _EarthdataSession(requests.Session):
    """Keeps credentials only for the Earthdata login host across redirects (NASA's documented pattern)."""

    def rebuild_auth(self, prepared_request, response):  # noqa: D401
        headers = prepared_request.headers
        url = prepared_request.url or ""
        if "Authorization" in headers:
            orig = requests.utils.urlparse(response.request.url).hostname
            redir = requests.utils.urlparse(url).hostname
            if orig != redir and redir != URS and orig != URS:
                del headers["Authorization"]


class AsterConnector(Connector):
    id = "aster"
    name = "ASTER Global Emissivity Dataset (AG100 v003) / ASTER L1T"
    publisher = "NASA / METI, distributed by NASA LP DAAC (Earthdata)"
    url = "https://lpdaac.usgs.gov/products/ag100v003/"
    licence = "NASA Earthdata: no restrictions on use, citation requested; requires free Earthdata login"
    licence_url = "https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance"
    attribution = "ASTER GED courtesy of NASA/METI/AIST/Japan Spacesystems and U.S./Japan ASTER Science Team"
    note = "Optional. Thermal-infrared emissivity (silica, carbonate) and SWIR bands for improved mineral mapping."
    usage = "Optional extra evidence layers (not required for the demo)."
    optional = True

    def fetch(self) -> None:
        o = self.outcome
        user, pw = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
        if not user or not pw:
            o.status = "needs_credentials"
            o.error = "No Earthdata credentials in .env (EARTHDATA_USERNAME / EARTHDATA_PASSWORD)."
            o.how_to_obtain = HOW
            self.http.note(self.url, "not attempted: needs Earthdata login")
            return
        w, s, e, n = self.bbox
        q = f"{CMR}?short_name=AG100&version=003&bounding_box={w},{s},{e},{n}&page_size=20"
        res = self.http.get_json(q)
        entries = res.get("feed", {}).get("entry", [])
        links = []
        for ent in entries:
            for lk in ent.get("links", []):
                h = lk.get("href", "")
                if h.endswith((".h5", ".hdf", ".tif")) and "data#" in lk.get("rel", ""):
                    links.append(h)
        if not links:
            o.status = "failed"
            o.error = "CMR returned no AG100 granules for the pilot area."
            return
        sess = _EarthdataSession()
        sess.auth = (user, pw)
        sess.headers["User-Agent"] = self.http.ua
        files = []
        for h in links[:4]:
            dest = self.raw_dir / h.rsplit("/", 1)[-1]
            if not dest.exists() or self.force:
                r = sess.get(h, timeout=300, stream=True)
                self.http.note(h, f"HTTP {r.status_code}")
                if r.status_code == 401:
                    o.status = "needs_credentials"
                    o.error = "Earthdata rejected the credentials (HTTP 401)."
                    o.how_to_obtain = HOW
                    return
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
            files.append((dest, h))
        o.files = files
        o.record_count = len(files)
        o.status = "downloaded"
        o.note_extra = f"{len(files)} AG100 granule(s) downloaded."

    def validate(self) -> None:
        for p, _ in self.outcome.files:
            if p.stat().st_size < 1000:
                raise ValidationError(f"{p.name} is too small to be a valid granule")
