"""Extraction regexes and dictionaries on SYNTHETIC sentences (no OCR needed)."""

import pytest

from georevive.rescue.extract import Extractor, bearing_of, normalise_assay
from georevive.rescue.geocode import Place, geocode_facts, lookup, offset
from georevive.rescue.ocr import Word


def words_from(lines: list[str], conf: float = 0.95) -> list[Word]:
    out = []
    for li, line in enumerate(lines):
        x = 10
        for tok in line.split():
            w = 12 * len(tok)
            out.append(Word(tok, conf, x, 20 + li * 30, w, 20, li))
            x += w + 10
    return out


def facts_of(lines):
    return Extractor().extract(words_from(lines))


def by_type(facts, t):
    return [f for f in facts if f.type == t]


def test_assay_units_and_normalisation():
    fs = facts_of(
        ["The Arcturus Mine averaged 12 dwt. per ton over 400 ft.", "Channel sample Au 3.5 g/t and 850 ppb Au."]
    )
    a = by_type(fs, "assay")
    units = sorted(f.units for f in a)
    assert units == ["dwt/ton", "g/t", "ppb"]
    dwt = next(f for f in a if f.units == "dwt/ton")
    assert dwt.normalized["g_per_t"] == pytest.approx(12 * 1.55517384 / 0.90718474, rel=1e-3)
    assert "short ton" in dwt.normalized["assumption"]
    assert normalise_assay("1", "oz per ton")["g_per_t"] == pytest.approx(34.2857, rel=1e-3)


def test_bare_percentage_is_not_an_assay():
    fs = facts_of(["About 45 per cent of the output came from the Mazoe valley."])
    assert by_type(fs, "assay") == []
    fs = facts_of(["The ore carries 2.4 per cent copper."])
    assert len(by_type(fs, "assay")) == 1


def test_coordinates_pair_and_sheet():
    fs = facts_of(["The shaft lies at 17° 45' S., 31° 10' E. on sheet 1731C4."])
    c = by_type(fs, "coordinate")
    assert len(c) == 1
    assert c[0].normalized["lat"] == pytest.approx(-17.75) and c[0].normalized["lon"] == pytest.approx(
        31.1667, abs=1e-3
    )
    g = by_type(fs, "grid_ref")
    assert g and g[0].normalized["sheet"] == "1731C4"


def test_names_rock_units_and_structures():
    fs = facts_of(
        [
            "Gold occurs in a quartz reef along a shear zone in Bulawayan greenstone",
            "on Rietfontein Farm near the old Jumbo Mine and the Shamva Mine.",
        ]
    )
    assert any(f.value == "Bulawayan Group" for f in by_type(fs, "rock_unit"))
    assert {f.value for f in by_type(fs, "lithology")} >= {"quartz reef", "greenstone"}
    assert any(f.value == "gold" for f in by_type(fs, "commodity"))
    assert any(f.value == "shear zone" for f in by_type(fs, "fault"))
    mines = {f.normalized["name"] for f in by_type(fs, "mine")}
    assert mines == {"Jumbo", "Shamva"}  # "the old" stripped
    assert [f.normalized["name"] for f in by_type(fs, "farm")] == ["Rietfontein"]


def test_location_description_and_drillhole():
    fs = facts_of(["The workings are 15 miles north-east of Salisbury.", "Borehole No. 3 reached quartz at 120 ft."])
    loc = by_type(fs, "location_desc")
    assert (
        loc
        and loc[0].normalized["bearing_deg"] == 45
        and loc[0].normalized["distance_km"] == pytest.approx(24.14, abs=0.01)
    )
    dh = by_type(fs, "drillhole")
    assert dh and dh[0].normalized["hole_id"] == "3" and dh[0].normalized["depth_m"] == pytest.approx(36.58, abs=0.01)
    assert bearing_of("N.E.") == 45 and bearing_of("south-west") == 225


def test_chemical_symbols_are_case_sensitive():
    fs = facts_of(["As the reef was followed, the grade fell. CU and au should not match; Cu does."])
    vals = [f.normalized.get("matched") for f in by_type(fs, "commodity")]
    assert "Cu" in vals and "CU" not in vals and "au" not in vals


def test_bbox_and_confidence():
    fs = facts_of(["The Arcturus Mine"])
    m = by_type(fs, "mine")[0]
    x, y, w, h = m.bbox
    assert w > 0 and h == 20 and x > 10  # starts at "Arcturus", not "The"
    assert 0 < m.confidence <= 0.99
    low = Extractor().extract(words_from(["The Arcturus Mine"], conf=0.3))
    assert by_type(low, "mine")[0].confidence < m.confidence


def test_geocoding():
    places = [Place("Harare", 31.05, -17.83, "osm:city", "n1"), Place("Arcturus", 31.33, -17.77, "mrds", "10")]
    p, how, certain = lookup("Salisbury", places)
    assert p.name == "Harare" and certain
    fs = facts_of(["The Arcturus Mine is 15 miles north-east of Salisbury and assays 8 dwt per ton."])
    line_of = {i: 0 for i in range(len(fs))}
    locs = geocode_facts(fs, places, line_of)
    by = {f.type: loc for f, loc in zip(fs, locs, strict=True)}
    assert by["mine"].lon == pytest.approx(31.33) and not by["mine"].uncertain
    assert by["location_desc"].uncertain and by["location_desc"].lon > 31.05
    assert by["assay"].lon is not None and by["assay"].uncertain  # inherited from the same line
    lon, lat = offset(31.0, -17.8, 10, 90)
    assert lon > 31.0 and lat == pytest.approx(-17.8, abs=0.01)


def test_historical_name_patterns():
    fs = facts_of(
        [
            "The Ayrshire mine is near Salisbury; molybdenite occurs on the farm Appingadam.",
            "Among these mines are Rezende, Bartissol, Grand Reef, and Sabi Ophir.",
        ]
    )
    mines = {f.normalized["name"] for f in by_type(fs, "mine")}
    assert {"Ayrshire", "Rezende", "Bartissol", "Grand", "Sabi Ophir"} <= mines
    assert [f.normalized["name"] for f in by_type(fs, "farm")] == ["Appingadam"]
    assert any(f.value == "molybdenum" for f in by_type(fs, "commodity"))
    # "& Co." (Company) must not become cobalt, a lone "Gold mine" is not a mine name
    fs = facts_of(["Thacker, Spink and Co. published it.", "Gold mine output rose."])
    assert by_type(fs, "commodity") == [] or all(f.value != "cobalt" for f in by_type(fs, "commodity"))
    assert by_type(fs, "mine") == []
