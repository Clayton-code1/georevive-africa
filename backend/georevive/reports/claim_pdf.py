"""Claim check report (PDF): plain language for small-scale miners, optional technical appendix."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SLATE = colors.HexColor("#1E3A5F")
OCHRE = colors.HexColor("#B7791F")
SAND = colors.HexColor("#F7F3EA")
LINE = colors.HexColor("#DDD3BC")


def _styles():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5, leading=13, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("t", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=SLATE),
        "h2": ParagraphStyle(
            "h2",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=SLATE,
            spaceBefore=8,
            spaceAfter=3,
        ),
        "body": base,
        "small": ParagraphStyle("s", parent=base, fontSize=7.5, leading=10, textColor=colors.HexColor("#4b5563")),
        "disc": ParagraphStyle(
            "d",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#7a4f10"),
            backColor=colors.HexColor("#f6ead2"),
            borderPadding=6,
            borderColor=OCHRE,
            borderWidth=0.8,
        ),
    }


def _table(rows: list[list[Any]], widths: list[float], header: bool = True) -> Table:
    st = _styles()
    data = [
        [Paragraph(str(c), st["small"] if header and i == 0 else st["body"]) for c in r] for i, r in enumerate(rows)
    ]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), SAND)]
    t.setStyle(TableStyle(style))
    return t


def _verdict(a: dict[str, Any]) -> str:
    p = a.get("prospectivity") or {}
    pct = p.get("area_percentile")
    host = any("favourable" in u["class"] for u in a.get("geology", []))
    occ = [o for o in a.get("occurrences", []) if "gold" in (o.get("commod1", "") + o.get("commod2", "")).lower()]
    parts = []
    if pct is not None:
        level = "higher than most" if pct >= 75 else "about average" if pct >= 40 else "lower than most"
        parts.append(
            f"The GeoRevive model scores this area <b>{level}</b> of the pilot area "
            f"(average score higher than {pct:.0f}% of the area)."
        )
    parts.append(
        "The claim lies on rocks that commonly host gold in Zimbabwe (greenstone)."
        if host
        else "The available geology map does not show greenstone (the usual gold host rock) under this claim."
    )
    if occ:
        parts.append(
            f"There {'is' if len(occ) == 1 else 'are'} {len(occ)} recorded gold occurrence"
            f"{'' if len(occ) == 1 else 's'} within {5} km (nearest {occ[0]['dist_km']:.1f} km)."
        )
    else:
        parts.append(
            "No recorded gold occurrence lies within 5 km in the USGS database (this does not mean there is no gold)."
        )
    return " ".join(parts)


def build_pdf(a: dict[str, Any], map_png: Path, out: Path, prepared_for: str, technical: bool = True) -> Path:
    st = _styles()
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Claim check - {a['name']}",
        author="GeoRevive Africa",
    )
    W = A4[0] - 32 * mm
    now = datetime.now(UTC).strftime("%d %B %Y %H:%M UTC")
    E: list[Any] = []
    E.append(Paragraph("GeoRevive <font color='#B7791F'>Claim Check</font>", st["title"]))
    E.append(Paragraph(f"<b>{a['name']}</b> · prepared {now} for {prepared_for}", st["body"]))
    E.append(Spacer(1, 4))
    E.append(
        Paragraph(
            a["disclaimer"] + " This report is a desk study from open data. It is not a mineral resource "
            "estimate, not a legal title search, and not a guarantee of gold.",
            st["disc"],
        )
    )
    E.append(Spacer(1, 6))

    # 1. Summary
    E.append(Paragraph("1. In short", st["h2"]))
    E.append(Paragraph(_verdict(a), st["body"]))

    # 2. Location
    E.append(Paragraph("2. Where is the claim?", st["h2"]))
    lon, lat = a["centroid"]
    rows = [
        ["Item", "Value"],
        ["Centre (latitude, longitude)", f"{lat:.5f}, {lon:.5f} (WGS84)"],
        ["Area", f"{a['area_ha']:,.1f} hectares"],
        ["District / province", f"{a.get('district') or '-'} / {a.get('province') or '-'}"],
    ]
    if a.get("nearest_town"):
        t = a["nearest_town"]
        rows.append(["Nearest town or village", f"{t['name']} ({t['class']}), {t['km']} km"])
    if a.get("nearest_road"):
        r = a["nearest_road"]
        rows.append(["Nearest road", f"{r['name']} ({r['class']}), {r['km']} km"])
    E.append(_table(rows, [W * 0.35, W * 0.65]))
    E.append(Spacer(1, 4))
    if map_png.exists():
        E.append(Image(str(map_png), width=W * 0.9, height=W * 0.9 * 5.2 / 6.6))
        E.append(
            Paragraph(
                "Map: claim outline in dark blue; prospectivity shading yellow (low) to red (high). "
                + "; ".join(a.get("map_attributions", [])),
                st["small"],
            )
        )

    # 3. Geology
    E.append(Paragraph("3. What rocks are there?", st["h2"]))
    if a.get("geology"):
        E.append(Paragraph(f"From the geology map at {a.get('geology_scale')}:", st["body"]))
        E.append(
            _table(
                [["Rock unit", "What it means for gold", "Share of claim"]]
                + [[u["unit"], u["class"], f"{u['share_pct']}%"] for u in a["geology"][:8]],
                [W * 0.45, W * 0.38, W * 0.17],
            )
        )
        if "regional" in (a.get("geology_scale") or ""):
            E.append(
                Paragraph(
                    "Note: only a very coarse regional geology map was available for this report. "
                    "A geologist should check the 1:100 000 map (ZGS Bulletin 94).",
                    st["small"],
                )
            )
    else:
        E.append(Paragraph("No geology map is available for this location yet.", st["body"]))
    nf = a.get("nearest_fault_km")
    E.append(
        Paragraph(
            f"Nearest mapped fault or shear zone: {nf} km." if nf is not None else f"Faults: {a.get('fault_source')}.",
            st["body"],
        )
    )

    # 4. Known occurrences
    E.append(Paragraph("4. Known mineral occurrences nearby (within 5 km)", st["h2"]))
    occ = a.get("occurrences", [])
    if occ:
        E.append(
            _table(
                [["Name", "Commodity", "Status", "Distance"]]
                + [
                    [
                        o["name"],
                        ", ".join(x for x in (o.get("commod1"), o.get("commod2")) if x),
                        o.get("dev_stat", "-"),
                        f"{o['dist_km']} km",
                    ]
                    for o in occ[:12]
                ],
                [W * 0.38, W * 0.27, W * 0.2, W * 0.15],
            )
        )
    else:
        E.append(Paragraph("None recorded in USGS MRDS within 5 km.", st["body"]))
    if a.get("rescued_facts"):
        E.append(Paragraph("Facts rescued from historical documents (geologist-approved) nearby:", st["body"]))
        E.append(
            _table(
                [["Fact", "Type", "Document (page)", "Distance"]]
                + [
                    [
                        f["name"],
                        f.get("type", ""),
                        f"{f.get('document', '')} (p.{f.get('page_no', '')})",
                        f"{f['dist_km']} km",
                    ]
                    for f in a["rescued_facts"][:10]
                ],
                [W * 0.35, W * 0.15, W * 0.35, W * 0.15],
            )
        )

    # 5. Satellite indicators
    E.append(Paragraph("5. What do satellites show?", st["h2"]))
    ind = a.get("indicators", {})
    rows = [["Indicator", "Claim average", "Compared with the whole area"]]
    for lid in ("s2_iron_oxide", "s2_clay", "s2_ferrous", "dem_elevation", "dem_slope"):
        v = ind.get(lid)
        if not v or not v.get("n"):
            continue
        cmp_ = f"higher than {v['area_percentile']:.0f}% of the area" if lid.startswith("s2") else ""
        if lid.startswith("s2") and v.get("valid_fraction", 1) < 0.5:
            cmp_ += " (much of the claim masked by vegetation, water or cloud)"
        rows.append([v["label"], f"{v['mean']:.3g}", cmp_])
    if len(rows) > 1:
        E.append(_table(rows, [W * 0.35, W * 0.2, W * 0.45]))
        E.append(
            Paragraph(
                "Iron-oxide and clay indices can point to rocks altered by hot fluids, which sometimes "
                "accompany gold. They are also raised by soils, laterite and bare ground, so they are hints, "
                "not proof.",
                st["small"],
            )
        )
    else:
        E.append(Paragraph("No satellite indicators are available for this location.", st["body"]))

    # 6. Prospectivity
    E.append(Paragraph("6. Prospectivity score and why", st["h2"]))
    p = a.get("prospectivity")
    if p and p.get("n"):
        E.append(
            Paragraph(
                f"Average score inside the claim: <b>{p['mean']:.0f} / 100</b> (best cell {p['max']:.0f}). "
                f"Model: {p['method']} (run {p['run_id']}).",
                st["body"],
            )
        )
        bc = p.get("best_cell")
        if bc:
            E.append(
                Paragraph("<b>Why the best part of the claim scores as it does:</b> " + bc["explanation"], st["body"])
            )
    else:
        E.append(Paragraph("No prospectivity model has been run yet.", st["body"]))

    # 7. Next steps
    E.append(Paragraph("7. What to do next", st["h2"]))
    for s_ in (
        "Check that the ground is open and register any claim with the Provincial Mining Director's office "
        "(Ministry of Mines and Mining Development). This report does not check claim ownership.",
        "Ask a qualified geologist to visit the site, map the rocks and take samples for laboratory assay.",
        "Work safely: never enter old shafts or workings; follow mine safety and environmental rules.",
        "Use this report only as a starting point for discussion.",
    ):
        E.append(Paragraph("• " + s_, st["body"]))

    # 8. Sources
    E.append(Paragraph("8. Data sources and licences", st["h2"]))
    E.append(
        _table(
            [["Dataset", "Publisher", "Licence / terms", "Accessed"]]
            + [
                [s_["name"], s_.get("publisher", ""), s_.get("licence", ""), (s_.get("accessed_at") or "")[:10]]
                for s_ in a.get("sources", [])
            ],
            [W * 0.34, W * 0.22, W * 0.32, W * 0.12],
        )
    )
    E.append(
        Paragraph(
            "Attributions: " + "; ".join(sorted({s_.get("attribution") or "" for s_ in a.get("sources", [])} - {""})),
            st["small"],
        )
    )

    if technical:
        E.append(PageBreak())
        E.append(Paragraph("Technical appendix", st["h2"]))
        if p and p.get("best_cell"):
            E.append(
                Paragraph(
                    "Feature contributions for the highest-scoring cell (relative to the area average):", st["body"]
                )
            )
            E.append(
                _table(
                    [["Evidence", "Value here", "Contribution"]]
                    + [[c["label"], c["text"], f"{c['contribution']:+.3f}"] for c in p["best_cell"]["contributions"]],
                    [W * 0.38, W * 0.44, W * 0.18],
                )
            )
        if p:
            auc = p.get("auc")
            E.append(
                Paragraph(
                    f"Model validation AUC: {auc:.2f}." if auc is not None else "Model validation AUC: not available.",
                    st["body"],
                )
            )
            lim = p.get("limitations") or []
            if lim:
                E.append(
                    KeepTogether(
                        [Paragraph("Model limitations:", st["body"])] + [Paragraph("• " + x, st["small"]) for x in lim]
                    )
                )
        E.append(Paragraph("Claim polygon (GeoJSON, WGS84): " + str(a["polygon"])[:1500], st["small"]))
        E.append(Paragraph("Layers used: " + ", ".join(a.get("layers_used", [])), st["small"]))

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(
            16 * mm,
            9 * mm,
            "GeoRevive Africa - prototype claim check. Requires field verification. Not investment advice.",
        )
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Page {_doc.page}")
        canvas.restoreState()

    doc.build(E, onFirstPage=footer, onLaterPages=footer)
    return out
