"""Offline geocoding of rescued facts.

* coordinates in the text -> used directly (certain if both lat and lon are given)
* "12 miles north-east of Salisbury" -> place lookup + distance/bearing offset (approximate, flagged)
* mine / farm names -> gazetteer of OSM places and USGS MRDS site names (flagged unless one exact match)
* other facts (assays, rock units...) on the same or adjacent line as a located fact inherit its
  location, flagged as uncertain
"""

from __future__ import annotations

import difflib
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .extract import Fact

# Colonial-era names that appear in historical bulletins -> current names (renamed 1982 onwards)
HISTORICAL_NAMES = {
    "salisbury": "harare",
    "umtali": "mutare",
    "gwelo": "gweru",
    "fort victoria": "masvingo",
    "hartley": "chegutu",
    "sinoia": "chinhoyi",
    "gatooma": "kadoma",
    "que que": "kwekwe",
    "marandellas": "marondera",
    "enkeldoorn": "chivhu",
    "mazoe": "mazowe",
    "umvukwes": "mvurwi",
    "selukwe": "shurugwi",
    "shabani": "zvishavane",
    "wankie": "hwange",
    "melsetter": "chimanimani",
    "inyanga": "nyanga",
    "rusape": "rusape",
    "bindura": "bindura",
    "shamva": "shamva",
    "goromonzi": "goromonzi",
    "arcturus": "arcturus",
    "darwendale": "darwendale",
    "norton": "norton",
    "ruwa": "ruwa",
    "chitungwiza": "chitungwiza",
    "epworth": "epworth",
}


@dataclass
class Place:
    name: str
    lon: float
    lat: float
    kind: str  # osm:<class> | mrds
    ref: str


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", s.lower()).strip()


@lru_cache(maxsize=4)
def load_gazetteer(gpkg_path: str, mtime: float) -> list[Place]:
    import pyogrio

    out: list[Place] = []
    p = Path(gpkg_path)
    if not p.exists():
        return out
    layers = {n for n, _ in pyogrio.list_layers(p)}
    if "osm_places" in layers:
        df = pyogrio.read_dataframe(p, layer="osm_places")
        for _, r in df.iterrows():
            if r.get("name"):
                out.append(
                    Place(str(r["name"]), r.geometry.x, r.geometry.y, f"osm:{r.get('class')}", str(r.get("osm_id")))
                )
    if "mrds_zimbabwe" in layers:
        df = pyogrio.read_dataframe(p, layer="mrds_zimbabwe")
        for _, r in df.iterrows():
            if r.get("site_name"):
                out.append(Place(str(r["site_name"]), r.geometry.x, r.geometry.y, "mrds", str(r.get("dep_id"))))
    return out


def gazetteer(gpkg: Path) -> list[Place]:
    return load_gazetteer(str(gpkg), gpkg.stat().st_mtime if gpkg.exists() else 0.0)


def lookup(name: str, places: list[Place], prefer: str | None = None) -> tuple[Place | None, str, bool]:
    """Returns (place, method, certain)."""
    n = norm(name)
    n = HISTORICAL_NAMES.get(n, n)
    exact = [p for p in places if norm(p.name) == n]
    if prefer:
        pref = [p for p in exact if p.kind.startswith(prefer)]
        exact = pref or exact
    if len(exact) == 1:
        return exact[0], f"gazetteer exact ({exact[0].kind})", True
    if len(exact) > 1:
        return exact[0], f"gazetteer: {len(exact)} places share this name - first used", False
    names = {norm(p.name): p for p in places}
    close = difflib.get_close_matches(n, list(names), n=1, cutoff=0.88)
    if close:
        p = names[close[0]]
        return p, f"gazetteer fuzzy match '{p.name}' ({p.kind})", False
    return None, "not found in gazetteer", False


def offset(lon: float, lat: float, km: float, bearing_deg: float) -> tuple[float, float]:
    R = 6371.0
    br = math.radians(bearing_deg)
    la1, lo1 = math.radians(lat), math.radians(lon)
    la2 = math.asin(math.sin(la1) * math.cos(km / R) + math.cos(la1) * math.sin(km / R) * math.cos(br))
    lo2 = lo1 + math.atan2(
        math.sin(br) * math.sin(km / R) * math.cos(la1), math.cos(km / R) - math.sin(la1) * math.sin(la2)
    )
    return math.degrees(lo2), math.degrees(la2)


@dataclass
class Located:
    lon: float | None
    lat: float | None
    method: str
    uncertain: bool


def geocode_facts(facts: list[Fact], places: list[Place], line_of: dict[int, int]) -> list[Located]:
    """line_of: fact index -> OCR line number (for proximity inheritance)."""
    res: list[Located] = [Located(None, None, "not located", True) for _ in facts]
    for i, f in enumerate(facts):
        nz = f.normalized
        if f.type == "coordinate" and "lat" in nz and "lon" in nz:
            res[i] = Located(nz["lon"], nz["lat"], "coordinates stated in the text", False)
        elif f.type == "location_desc":
            p, how, _ = lookup(nz.get("place", ""), places, prefer="osm")
            if p:
                lon, lat = offset(p.lon, p.lat, nz["distance_km"], nz["bearing_deg"])
                res[i] = Located(
                    lon,
                    lat,
                    f"{nz['distance_km']:.1f} km at {nz['bearing_deg']:.0f}° from {p.name} ({how}); approximate",
                    True,
                )
            else:
                res[i] = Located(None, None, f"reference place '{nz.get('place')}' {how}", True)
        elif f.type in ("mine", "farm"):
            p, how, certain = lookup(nz.get("name", ""), places, prefer="mrds" if f.type == "mine" else "osm")
            if p is None and f.type == "mine":
                p, how, certain = lookup(f.value, places, prefer="mrds")
            if p:
                res[i] = Located(p.lon, p.lat, how, not certain)
            else:
                res[i] = Located(None, None, how, True)
    # inherit from the nearest located fact on the same or adjacent line
    located = [(i, line_of.get(i, -99)) for i, r in enumerate(res) if r.lon is not None]
    for i, r in enumerate(res):
        if r.lon is not None:
            continue
        li = line_of.get(i, -99)
        best = None
        for j, lj in located:
            d = abs(lj - li)
            if d <= 1 and (best is None or d < best[0] or (d == best[0] and abs(j - i) < abs(best[1] - i))):
                best = (d, j)
        if best:
            src = res[best[1]]
            res[i] = Located(
                src.lon,
                src.lat,
                f"inherited from nearby '{facts[best[1]].value}' "
                f"({'same line' if best[0] == 0 else 'adjacent line'}); uncertain",
                True,
            )
    return res
