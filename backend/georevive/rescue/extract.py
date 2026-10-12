"""Offline, rule-based fact extraction from OCR words.

Every fact keeps: type, value, units, normalised value, page bounding box (union of the words it
came from), confidence, method (the rule that fired) and the line of text it came from."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .ocr import Word

DICT_DIR = Path(__file__).parent / "dictionaries"

# Unit conversions to grams per metric tonne. Historical Rhodesian gold grades are usually quoted
# in pennyweights (dwt) per short ton (2000 lb); we record that assumption on each fact.
DWT_G = 1.55517384
OZT_G = 31.1034768
SHORT_TON_T = 0.90718474
LONG_TON_T = 1.0160469

STOP_NAMES = {
    "the",
    "this",
    "that",
    "a",
    "an",
    "of",
    "in",
    "on",
    "at",
    "and",
    "or",
    "no",
    "old",
    "main",
    "new",
    "its",
    "his",
    "their",
    "which",
    "where",
    "these",
    "those",
    "such",
    "same",
    "each",
    "one",
    "two",
    "some",
    "any",
    "all",
    "other",
    "small",
    "large",
    "near",
    "from",
    "for",
    "by",
    "with",
    "between",
}


@dataclass
class Fact:
    type: str
    value: str
    units: str | None
    normalized: dict[str, Any]
    bbox: list[int]
    confidence: float
    method: str
    context: str
    span: tuple[int, int] = (0, 0)
    word_idx: list[int] = field(default_factory=list)


@dataclass
class PageText:
    text: str
    spans: list[tuple[int, int, int]]  # (start, end, word index)
    words: list[Word]
    lines: dict[int, tuple[int, int]]  # line -> (start, end)


def build_text(words: list[Word]) -> PageText:
    order = sorted(range(len(words)), key=lambda i: (words[i].line, words[i].x))
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    lines: dict[int, tuple[int, int]] = {}
    pos = 0
    cur_line = None
    line_start = 0
    for i in order:
        w = words[i]
        if cur_line is not None and w.line != cur_line:
            lines[cur_line] = (line_start, pos)
            parts.append("\n")
            pos += 1
            line_start = pos
        elif cur_line is not None:
            parts.append(" ")
            pos += 1
        if cur_line is None:
            line_start = pos
        cur_line = w.line
        spans.append((pos, pos + len(w.text), i))
        parts.append(w.text)
        pos += len(w.text)
    if cur_line is not None:
        lines[cur_line] = (line_start, pos)
    return PageText("".join(parts), spans, words, lines)


def _words_in(pt: PageText, start: int, end: int) -> list[int]:
    return [wi for s, e, wi in pt.spans if s < end and e > start]


def _bbox(words: list[Word], idx: list[int]) -> list[int]:
    if not idx:
        return [0, 0, 0, 0]
    x0 = min(words[i].x for i in idx)
    y0 = min(words[i].y for i in idx)
    x1 = max(words[i].x + words[i].w for i in idx)
    y1 = max(words[i].y + words[i].h for i in idx)
    return [x0, y0, x1 - x0, y1 - y0]


def _context(pt: PageText, start: int, end: int) -> str:
    # the full line(s) the match sits on, joined across a line break
    s = pt.text.rfind("\n", 0, start) + 1
    e = pt.text.find("\n", end)
    return pt.text[s : (e if e != -1 else len(pt.text))].replace("\n", " ")[:300]


# --- dictionaries ------------------------------------------------------------------
@lru_cache(maxsize=1)
def dictionaries() -> dict[str, list[tuple[str, str, str, re.Pattern]]]:
    """type -> [(canonical, variant, class, compiled pattern)], longest variants first."""
    rocks = yaml.safe_load((DICT_DIR / "rock_units.yaml").read_text(encoding="utf-8"))
    mins = yaml.safe_load((DICT_DIR / "minerals.yaml").read_text(encoding="utf-8"))
    out: dict[str, list[tuple[str, str, str, re.Pattern]]] = {}

    def pat(v: str) -> re.Pattern:
        esc = re.escape(v).replace(r"\ ", r"[\s-]+").replace(r"\-", r"[\s-]?")
        flags = 0 if (len(v) <= 2 and v[:1].isupper()) else re.IGNORECASE
        return re.compile(rf"(?<![A-Za-z]){esc}(?![A-Za-z])", flags)

    entries = []
    for canon, d in (rocks.get("stratigraphic") or {}).items():
        for v in d["variants"]:
            entries.append(("rock_unit", canon, v, d.get("class", "other"), "dict:stratigraphic"))
    for canon, d in (rocks.get("lithology") or {}).items():
        for v in d["variants"]:
            entries.append(("lithology", canon, v, d.get("class", "other"), "dict:lithology"))
    for canon, vs in (mins.get("commodities") or {}).items():
        for v in vs:
            entries.append(("commodity", canon, v, "commodity", "dict:commodity"))
    for canon, vs in (mins.get("minerals") or {}).items():
        for v in vs:
            entries.append(("mineral", canon, v, "mineral", "dict:mineral"))
    for canon, vs in (mins.get("structures") or {}).items():
        for v in vs:
            entries.append(("structure", canon, v, "structure", "dict:structure"))
    entries.sort(key=lambda e: -len(e[2]))
    for typ, canon, v, cls, method in entries:
        out.setdefault(typ, []).append((canon, v, cls + "|" + method, pat(v)))
    return out


def rock_class(canonical: str) -> str | None:
    for typ in ("rock_unit", "lithology"):
        for canon, _v, clsm, _p in dictionaries().get(typ, []):
            if canon == canonical:
                return clsm.split("|")[0]
    return None


# --- regular expressions ----------------------------------------------------------------
NUM = r"\d+(?:[.,·]\d+)?"
ASSAY_RE = re.compile(
    rf"(?P<val>{NUM})\s*(?P<unit>"
    r"g\s*/\s*t(?:onne)?|g\.?\s*per\s*(?:metric\s+)?t(?:on(?:ne)?)?\.?|grams?\s+per\s+(?:metric\s+)?ton(?:ne)?"
    r"|dwts?\.?\s*(?:per|/|a)\s*(?:short\s+|long\s+)?ton\.?|dwts?\.?(?![a-z])"
    r"|oz\.?\s*(?:per|/|a)\s*(?:short\s+|long\s+)?ton\.?|oz\s*/\s*t(?![a-z])"
    r"|ppm|ppb|per\s*cent\.?|%)",
    re.IGNORECASE,
)
DEG = r"[°º˚o*]"
DMS_RE = re.compile(
    rf"(?P<d>\d{{1,3}})\s*{DEG}\s*(?:(?P<m>\d{{1,2}}(?:\.\d+)?)\s*['’′`]?\s*)?(?:(?P<s>\d{{1,2}}(?:\.\d+)?)\s*[\"”″]\s*)?"
    r"(?P<h>[NSEW])\b\.?"
)
DEC_RE = re.compile(r"(?P<v>-?\d{1,3}\.\d{3,})\s*°?\s*(?P<h>[NSEW])\b")
SHEET_RE = re.compile(r"\b(?P<lat>1[5-9]|2[0-2])(?P<lon>2[5-9]|3[0-3])\s?(?P<q>[A-D])\s?(?P<s>[1-4])\b")
GRIDREF_RE = re.compile(r"\b(?:grid\s+ref(?:erence)?\.?|G\.?R\.?)\s*(?P<v>\d{6,10})\b", re.IGNORECASE)
NAME = r"(?:[A-Z][a-zA-Z'’]+(?:-[A-Z][a-zA-Z'’]+)?|Mc[A-Z][a-z]+)"
# names stay on one line ([ \t], not \s): a heading's last word must not join the next line's name
FARM_RE = re.compile(rf"\b(?P<name>{NAME}(?:[ \t]+{NAME}){{0,2}})[ \t]+(?P<kind>Farm|Estate|Ranch)\b")
# "farm Appingadam" (name after the word, common in old reports)
FARM_AFTER_RE = re.compile(rf"\b(?P<kind>[Ff]arm)[ \t]+(?P<name>{NAME}(?:[ \t]+{NAME})?)")
# "The Ayrshire mine" - historical texts often write 'mine' in lower case
MINE_RE = re.compile(
    rf"\b(?P<name>{NAME}(?:[ \t]+{NAME}){{0,2}})[ \t]+(?P<kind>[Mm]ines?|Claims?|Block|Reef|Workings|Prospect)\b"
)
# Lists of mine names: "Among these mines are Rezende, Bartissol, Grand Reef and Quagga."
_LNAME = rf"{NAME}(?:[ \t]+{NAME}){{0,2}}"
MINE_LIST_RE = re.compile(
    rf"\b(?:such\s+mines\s+as|mines\s+(?:are|were|include|including|such\s+as)|properties\s+(?:are|include))\s*:?\s+"
    rf"(?P<list>(?:the\s+)?{_LNAME}(?:\s*,\s*(?:and\s+)?(?:the\s+)?{_LNAME}|\s+and\s+(?:the\s+)?{_LNAME}){{1,15}})"
)
NOT_MINE_NAMES = {
    "gold",
    "copper",
    "chrome",
    "big",
    "rich",
    "deep",
    "great",
    "little",
    "ancient",
    "native",
    "rhodesian",
    "company",
    "government",
    "british",
}
DRILL_RE = re.compile(
    r"\b(?P<kind>DDH|BH|RC|PDH|bore[- ]?hole|drill[- ]?hole)\s*(?:No\.?|number)?\s*(?P<id>[A-Z]{0,3}[-/]?\d{1,4}[A-Z]?)\b",
    re.IGNORECASE,
)
DEPTH_RE = re.compile(rf"\b(?:at|to|depth\s+of)\s+(?P<v>{NUM})\s*(?P<u>ft|feet|foot|m|metres|meters)\b", re.IGNORECASE)
DIRS = r"north(?:[- ]?(?:east|west))?|south(?:[- ]?(?:east|west))?|east|west|N\.?\s?N?[EW]?\.?|S\.?\s?S?[EW]?\.?|[NS]\.?[EW]\.?|E\.?|W\.?"
LOCDESC_RE = re.compile(
    rf"(?P<dist>{NUM})\s*(?P<u>miles?|mi\.|km|kilometres?|kilometers?)\s+(?P<dir>{DIRS})\s+(?:of|from)\s+"
    rf"(?P<place>{NAME}(?:\s+{NAME}){{0,2}})",
    re.IGNORECASE,
)

BEARINGS = {
    "n": 0,
    "north": 0,
    "nne": 22.5,
    "ne": 45,
    "northeast": 45,
    "north-east": 45,
    "ene": 67.5,
    "e": 90,
    "east": 90,
    "ese": 112.5,
    "se": 135,
    "southeast": 135,
    "south-east": 135,
    "sse": 157.5,
    "s": 180,
    "south": 180,
    "ssw": 202.5,
    "sw": 225,
    "southwest": 225,
    "south-west": 225,
    "wsw": 247.5,
    "w": 270,
    "west": 270,
    "wnw": 292.5,
    "nw": 315,
    "northwest": 315,
    "north-west": 315,
    "nnw": 337.5,
}


def bearing_of(d: str) -> float | None:
    k = re.sub(r"[.\s]", "", d.lower())
    k = k.replace("northeast", "ne").replace("northwest", "nw").replace("southeast", "se").replace("southwest", "sw")
    k = (
        k.replace("north-east", "ne")
        .replace("north-west", "nw")
        .replace("south-east", "se")
        .replace("south-west", "sw")
    )
    return BEARINGS.get(k)


def _num(s: str) -> float:
    return float(s.replace(",", ".").replace("·", "."))


def normalise_assay(val: str, unit: str) -> dict[str, Any]:
    v = _num(val)
    u = re.sub(r"\s+", " ", unit.lower()).strip(" .")
    long_ton = "long" in u
    ton_t = LONG_TON_T if long_ton else SHORT_TON_T
    if u.startswith("dwt"):
        return {
            "value": v,
            "unit": "dwt/ton",
            "g_per_t": round(v * DWT_G / ton_t, 3),
            "assumption": "pennyweights per " + ("long ton (2240 lb)" if long_ton else "short ton (2000 lb)"),
        }
    if u.startswith("oz"):
        return {
            "value": v,
            "unit": "oz/ton",
            "g_per_t": round(v * OZT_G / ton_t, 3),
            "assumption": "troy ounces per " + ("long ton" if long_ton else "short ton (2000 lb)"),
        }
    if u.startswith("g") or "gram" in u:
        return {"value": v, "unit": "g/t", "g_per_t": v}
    if u == "ppm":
        return {"value": v, "unit": "ppm", "g_per_t": v}
    if u == "ppb":
        return {"value": v, "unit": "ppb", "g_per_t": round(v / 1000, 4)}
    return {"value": v, "unit": "%"}


def dms_to_dd(d: str, m: str | None, s: str | None, h: str) -> float:
    dd = float(d) + (float(m) / 60 if m else 0) + (float(s) / 3600 if s else 0)
    return -dd if h.upper() in ("S", "W") else dd


# Words are matched case-insensitively; element symbols only with exact case ("As" is also an English word).
GRADE_COMMODITY_RE = re.compile(
    r"\b(?:(?i:gold|copper|nickel|antimony|chrom\w*|zinc|lead|arsenic|tungsten|lithium|tin)"
    r"|Au|Cu|Ni|Sb|Cr2O3|Zn|Pb|WO3|Li2O|Sn)\b"
)


class Extractor:
    def __init__(self) -> None:
        self.dicts = dictionaries()

    def extract(self, words: list[Word]) -> list[Fact]:
        pt = build_text(words)
        facts: list[Fact] = []
        taken: list[tuple[int, int]] = []

        def overlaps(a: int, b: int) -> bool:
            return any(a < e and b > s for s, e in taken)

        def add(typ, value, units, norm, start, end, base_conf, method, reserve=True):
            idx = _words_in(pt, start, end)
            if not idx:
                return
            ocr = sum(words[i].conf for i in idx) / len(idx)
            conf = round(max(0.05, min(0.99, base_conf * (0.5 + 0.5 * ocr))), 3)
            facts.append(
                Fact(
                    typ,
                    value,
                    units,
                    norm,
                    _bbox(words, idx),
                    conf,
                    method,
                    _context(pt, start, end),
                    (start, end),
                    idx,
                )
            )
            if reserve:
                taken.append((start, end))

        t = pt.text
        # Coordinates: DMS pairs (lat + lon) first, then single values
        dms = list(DMS_RE.finditer(t))
        used = set()
        for i, m in enumerate(dms):
            if i in used:
                continue
            h = m.group("h").upper()
            nxt = dms[i + 1] if i + 1 < len(dms) else None
            if (
                nxt
                and nxt.start() - m.end() < 25
                and {h, nxt.group("h").upper()} & {"N", "S"}
                and {h, nxt.group("h").upper()} & {"E", "W"}
            ):
                a = dms_to_dd(m["d"], m["m"], m["s"], h)
                b = dms_to_dd(nxt["d"], nxt["m"], nxt["s"], nxt.group("h"))
                lat, lon = (a, b) if h in "NS" else (b, a)
                if abs(lat) <= 90 and abs(lon) <= 180:
                    add(
                        "coordinate",
                        t[m.start() : nxt.end()],
                        "deg",
                        {"lat": round(lat, 6), "lon": round(lon, 6)},
                        m.start(),
                        nxt.end(),
                        0.92,
                        "regex:dms_pair",
                    )
                used.update({i, i + 1})
            else:
                v = dms_to_dd(m["d"], m["m"], m["s"], h)
                key = "lat" if h in "NS" else "lon"
                if (key == "lat" and abs(v) <= 90) or (key == "lon" and abs(v) <= 180):
                    add(
                        "coordinate", m.group(0), "deg", {key: round(v, 6)}, m.start(), m.end(), 0.7, "regex:dms_single"
                    )
        for m in DEC_RE.finditer(t):
            if overlaps(m.start(), m.end()):
                continue
            v = _num(m["v"]) * (-1 if m["h"].upper() in "SW" else 1)
            add(
                "coordinate",
                m.group(0),
                "deg",
                {"lat" if m["h"].upper() in "NS" else "lon": v},
                m.start(),
                m.end(),
                0.75,
                "regex:decimal_deg",
            )
        for m in SHEET_RE.finditer(t):
            if overlaps(m.start(), m.end()):
                continue
            add(
                "grid_ref",
                m.group(0).replace(" ", ""),
                None,
                {"sheet": f"{m['lat']}{m['lon']}{m['q']}{m['s']}", "system": "Zimbabwe 1:50 000 sheet index"},
                m.start(),
                m.end(),
                0.7,
                "regex:zw_sheet",
            )
        for m in GRIDREF_RE.finditer(t):
            add("grid_ref", m["v"], None, {"grid_ref": m["v"]}, m.start(), m.end(), 0.8, "regex:grid_reference")

        # Assays: grades with units
        for m in ASSAY_RE.finditer(t):
            if overlaps(m.start(), m.end()):
                continue
            unit = m["unit"]
            norm = normalise_assay(m["val"], unit)
            pre = t[max(0, m.start() - 40) : m.start()]
            post = t[m.end() : m.end() + 25]
            el = GRADE_COMMODITY_RE.search(pre + " " + post)
            if norm["unit"] == "%" and not el:
                continue  # a bare percentage is not an assay
            if norm["unit"] == "%" and re.match(r"\s*(?:of|was|were|is|are)\b", post):
                continue  # "99 per cent of which were pegged..." is a proportion, not a grade
            if el:
                norm["element"] = el.group(0)
            base = 0.9 if norm["unit"] in ("g/t", "dwt/ton", "oz/ton") else 0.75
            add(
                "assay",
                m.group(0).strip(),
                norm["unit"],
                norm,
                m.start(),
                m.end(),
                base,
                f"regex:assay_{norm['unit'].replace('/', '_per_')}",
            )

        for m in LOCDESC_RE.finditer(t):
            b = bearing_of(m["dir"])
            if b is None:
                continue
            dist = _num(m["dist"])
            km = dist * 1.609344 if m["u"].lower().startswith("mi") else dist
            add(
                "location_desc",
                m.group(0),
                "km",
                {"distance_km": round(km, 3), "bearing_deg": b, "place": m["place"].strip()},
                m.start(),
                m.end(),
                0.8,
                "regex:distance_bearing_place",
            )

        for m in DRILL_RE.finditer(t):
            if overlaps(m.start(), m.end()):
                continue
            norm: dict[str, Any] = {"hole_type": m["kind"], "hole_id": m["id"]}
            d = DEPTH_RE.search(t, m.end(), m.end() + 60)
            end = m.end()
            if d:
                dv = _num(d["v"])
                norm["depth_m"] = round(dv * 0.3048, 2) if d["u"].lower().startswith(("f",)) else dv
                end = d.end()
            add("drillhole", t[m.start() : end], None, norm, m.start(), end, 0.75, "regex:drillhole")

        def clean_name(raw: str) -> list[str]:
            toks = raw.split()
            # keep only the words after the last stop word ("DATA The Jumbo" -> "Jumbo")
            stops = [i for i, tok in enumerate(toks) if tok.lower() in STOP_NAMES]
            if stops:
                toks = toks[stops[-1] + 1 :]
            if len(toks) == 1 and toks[0].lower() in NOT_MINE_NAMES:
                return []
            return toks

        for rx, typ, method in ((MINE_RE, "mine", "regex:named_mine"), (FARM_RE, "farm", "regex:named_farm")):
            for m in rx.finditer(t):
                toks = clean_name(m["name"])
                if not toks:
                    continue
                name = " ".join(toks)
                start = m.start("name") + m.group("name").find(toks[0])
                if overlaps(start, m.end()):
                    continue
                kind = m["kind"].capitalize() if typ == "mine" else m["kind"]
                add(typ, f"{name} {kind}", None, {"name": name, "kind": kind}, start, m.end(), 0.78, method)
        for m in FARM_AFTER_RE.finditer(t):
            toks = clean_name(m["name"])
            if toks and not overlaps(m.start(), m.end()):
                name = " ".join(toks)
                add(
                    "farm",
                    f"{name} Farm",
                    None,
                    {"name": name, "kind": "Farm"},
                    m.start(),
                    m.end(),
                    0.72,
                    "regex:farm_then_name",
                )
        for m in MINE_LIST_RE.finditer(t):
            base = m.start("list")
            for nm in re.finditer(_LNAME, m["list"]):
                toks = clean_name(nm.group(0))
                if not toks:
                    continue
                s0, s1 = base + nm.start(), base + nm.end()
                if overlaps(s0, s1):
                    continue
                name = " ".join(toks)
                add(
                    "mine",
                    f"{name} (mine, from a list)",
                    None,
                    {"name": name, "kind": "Mine"},
                    s0,
                    s1,
                    0.62,
                    "regex:mine_name_list",
                )

        # Dictionary terms (rock units first: longer, more specific)
        for typ in ("rock_unit", "lithology", "commodity", "mineral", "structure"):
            for canon, _variant, clsm, rx in self.dicts.get(typ, []):
                cls, method = clsm.split("|")
                for m in rx.finditer(t):
                    if overlaps(m.start(), m.end()):
                        continue
                    base = {"rock_unit": 0.9, "lithology": 0.72, "commodity": 0.82, "mineral": 0.7, "structure": 0.62}[
                        typ
                    ]
                    out_typ = "fault" if (typ == "structure" and canon in ("fault", "shear zone")) else typ
                    add(out_typ, canon, None, {"matched": m.group(0), "class": cls}, m.start(), m.end(), base, method)
        facts.sort(key=lambda f: f.span[0])
        return facts


def page_text(words: list[Word]) -> str:
    return build_text(words).text
