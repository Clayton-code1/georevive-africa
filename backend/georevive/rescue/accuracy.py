"""Extraction accuracy on a small hand-labelled set of openly available pages.

Labels live in backend/georevive/rescue/labels/*.json:
{
  "page_image": "data/samples/<id>.png"   (or "pdf": "<registered path>", "page": N),
  "source_id": "...", "title": "...", "licence": "...",
  "labelled_by": "...", "verified_by_geologist": false,
  "facts": [{"type": "mine", "value": "Jumbo Mine"}, {"type": "assay", "value": "12 dwt"}, ...]
}
Run:  python -m georevive.rescue.accuracy   ->  docs/extraction-accuracy.md
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..registry import abspath

LABEL_DIR = Path(__file__).parent / "labels"
# fact types that are compared; others (e.g. 'structure') are reported but not scored
SCORED = (
    "rock_unit",
    "lithology",
    "commodity",
    "mineral",
    "fault",
    "assay",
    "coordinate",
    "grid_ref",
    "location_desc",
    "drillhole",
    "mine",
    "farm",
)


def _num(s: str) -> str:
    m = re.search(r"\d+(?:[.,]\d+)?", s)
    return m.group(0).replace(",", ".") if m else ""


def key_of(typ: str, value: str) -> tuple[str, str]:
    v = value.lower().strip()
    if typ == "assay":
        unit = (
            "dwt"
            if "dwt" in v
            else "oz"
            if "oz" in v
            else "g/t"
            if ("g/t" in v or "gram" in v)
            else "ppm"
            if "ppm" in v
            else "ppb"
            if "ppb" in v
            else "%"
            if ("%" in v or "cent" in v)
            else ""
        )
        return typ, f"{float(_num(v) or 0):g} {unit}"
    if typ in ("mine", "farm"):
        v = re.sub(r"\b(mine|mines|claims?|block|reef|workings|prospect|farm|estate|ranch)\b", "", v)
    if typ == "location_desc":
        places = re.findall(r"(?:of|from)\s+([a-z]+)", v)
        return typ, f"{_num(v)} {places[-1] if places else ''}"
    return typ, re.sub(r"[^a-z0-9]+", " ", v).strip()


def predicted_key(f) -> tuple[str, str]:
    typ = f.type
    if typ in ("mine", "farm"):
        return key_of(typ, f.normalized.get("name", f.value))
    if typ == "assay":
        n = f.normalized
        unit = {"dwt/ton": "dwt", "oz/ton": "oz"}.get(n.get("unit"), n.get("unit", ""))
        return typ, f"{float(n.get('value', 0)):g} {unit}"
    return key_of(typ, f.value)


def evaluate_page(image: Path, labels: list[dict[str, Any]], engine: str | None = None) -> dict[str, Any]:
    from .enhance import enhance, load_image
    from .extract import Extractor
    from .ocr import choose_engine, run_ocr

    eng = choose_engine(engine or get_settings().section("extraction").get("ocr_engine", "auto"))
    img = load_image(image)
    with tempfile.TemporaryDirectory() as td:
        res = enhance(img, Path(td))
    words = run_ocr(res.final_gray, res.binary, eng)
    facts = [f for f in Extractor().extract(words) if f.type in SCORED]
    # Compared as sets of unique facts per page (repeated mentions of the same fact count once)
    pred: dict[str, set] = defaultdict(set)
    for f in facts:
        pred[f.type].add(predicted_key(f))
    gold: dict[str, set] = defaultdict(set)
    for lab in labels:
        if lab["type"] in SCORED:
            gold[lab["type"]].add(key_of(lab["type"], lab["value"]))
    per: dict[str, dict[str, int]] = {}
    for t in set(pred) | set(gold):
        tp = len(pred[t] & gold[t])
        per[t] = {"tp": tp, "fp": len(pred[t]) - tp, "fn": len(gold[t]) - tp}
    return {
        "engine": eng,
        "per_type": per,
        "n_pred": sum(len(v) for v in pred.values()),
        "n_gold": sum(len(v) for v in gold.values()),
        "missed": sorted(k for t in gold for k in gold[t] - pred[t]),
        "spurious": sorted(k for t in pred for k in pred[t] - gold[t]),
    }


def _prf(tp: int, fp: int, fn: int) -> tuple[float | None, float | None, float | None]:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else None
    return p, r, f


def run() -> Path:
    s = get_settings()
    labels = sorted(LABEL_DIR.glob("*.json"))
    rows, totals = [], defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    pages = []
    for lf in labels:
        spec = json.loads(lf.read_text(encoding="utf-8"))
        img = abspath(spec["page_image"])
        if not img.exists():
            pages.append(
                {"label_file": lf.name, "title": spec.get("title"), "status": f"image missing: {spec['page_image']}"}
            )
            continue
        r = evaluate_page(img, spec["facts"])
        for t, c in r["per_type"].items():
            for k in ("tp", "fp", "fn"):
                totals[t][k] += c[k]
        pages.append(
            {
                "label_file": lf.name,
                "title": spec.get("title"),
                "source_id": spec.get("source_id"),
                "licence": spec.get("licence"),
                "labelled_by": spec.get("labelled_by"),
                "verified": spec.get("verified_by_geologist", False),
                "held_out": bool(spec.get("held_out", False)),
                "status": "evaluated",
                **r,
            }
        )
    for t in sorted(totals):
        c = totals[t]
        p, rc, f = _prf(c["tp"], c["fp"], c["fn"])
        rows.append((t, c["tp"], c["fp"], c["fn"], p, rc, f))
    T = {k: sum(c[k] for c in totals.values()) for k in ("tp", "fp", "fn")}
    P, R, F = _prf(T["tp"], T["fp"], T["fn"])

    def pct(x):
        return "-" if x is None else f"{x * 100:.0f}%"

    L = [
        "# Extraction accuracy (rule-based, offline mode)",
        "",
        f"_Generated {datetime.now(UTC):%Y-%m-%d %H:%M UTC} by `python -m georevive.rescue.accuracy`._",
        "",
    ]
    evaluated = [p for p in pages if p["status"] == "evaluated"]
    if not evaluated:
        L += [
            "**No labelled pages could be evaluated yet.** Add label files (see below) for openly available pages,",
            "then re-run. No accuracy figure is claimed until then.",
            "",
        ]
    else:
        L += [
            f"**Overall on {len(evaluated)} labelled page(s), {T['tp'] + T['fn']} labelled facts:** "
            f"precision **{pct(P)}**, recall **{pct(R)}**, F1 **{pct(F)}** "
            f"(OCR engine: {evaluated[0]['engine']}).",
            "",
            "| Fact type | Correct | Spurious | Missed | Precision | Recall | F1 |",
            "|---|---|---|---|---|---|---|",
        ]
        for t, tp, fp, fn, p, rc, f in rows:
            L.append(f"| {t} | {tp} | {fp} | {fn} | {pct(p)} | {pct(rc)} | {pct(f)} |")
        L.append("")
        held = [p for p in evaluated if p.get("held_out")]
        first = s.path("reports_dir") / "extraction_accuracy_heldout_first_run.json"
        if first.exists():  # the frozen first run on held-out pages, before any fix they prompted
            first_pages = [p for p in json.loads(first.read_text(encoding="utf-8"))["pages"] if p.get("held_out")]
            if first_pages:
                held = first_pages
        if held:
            H = {k: sum(c[k] for p in held for c in p["per_type"].values()) for k in ("tp", "fp", "fn")}
            hp, hr, hf = _prf(H["tp"], H["fp"], H["fn"])
            L[4:4] = [
                f"> **Honest figure - held-out page(s) only ({len(held)} page, {H['tp'] + H['fn']} labelled facts, "
                f"first run, before any fix it prompted; never used to tune): precision {pct(hp)}, recall {pct(hr)}, F1 {pct(hf)}.** "
                "Quote this one, with the page count. The overall table below mixes in pages that were used "
                "to improve the rules, so it is optimistic.",
                "",
            ]
    base_p = s.path("reports_dir") / "extraction_accuracy_baseline.json"
    if base_p.exists() and evaluated:
        b = json.loads(base_p.read_text(encoding="utf-8"))["overall"]
        L += [
            "## Important: these pages were also used to improve the rules",
            f"Before any rule changes, the first run on the same pages gave precision **{pct(b['precision'])}**, "
            f"recall **{pct(b['recall'])}**, F1 **{pct(b['f1'])}** (`reports/extraction_accuracy_baseline.json`). "
            "The misses showed generic gaps (lower-case 'mine', 'farm <Name>', lists of mine names, missing common "
            "rock and mineral words), which were then fixed. Because the same pages informed the fixes, the figure "
            "above is **optimistic**. The honest figure to quote is the baseline, until a fresh, held-out set of "
            "labelled pages (ideally ZGS bulletin pages) has been evaluated.",
            "",
        ]
    L += [
        "## How to read this honestly",
        "- The test set is **small** (a handful of pages), so these numbers have wide uncertainty. Quote them as "
        "'on our first labelled pages' and give the page count.",
        "- Facts are compared as unique facts per page (a rock unit mentioned five times counts once). A fact counts as correct only if the type and the normalised value match a label (e.g. assay value and "
        "unit, mine name without 'Mine', canonical rock unit).",
        "- **Precision** = share of extracted facts that are correct; **recall** = share of labelled facts that "
        "were found.",
        "- Labels marked 'verified by geologist: no' were prepared by the build assistant from the page text and "
        "**must be checked by the Geoscience Lead** before the figure is used in the pitch.",
        "- The pages are old public-domain publications; ZGS bulletins of the Harare sheet may behave differently "
        "(different typography, maps, tables).",
        "",
    ]
    L += [
        "## Pages",
        "",
        "| Label file | Page | Source | Labelled by | Verified by geologist | Result |",
        "|---|---|---|---|---|---|",
    ]
    for p in pages:
        res = f"{p['n_gold']} labels, {p['n_pred']} extracted" if p["status"] == "evaluated" else p["status"]
        L.append(
            f"| {p['label_file']} | {p.get('title')} | {p.get('source_id', '-')} | {p.get('labelled_by', '-')} | "
            f"{'yes' if p.get('verified') else 'no'} | {res} |"
        )
    L.append("")
    for p in evaluated:
        if p["missed"] or p["spurious"]:
            L.append(
                f"**{p['label_file']}** - missed: {', '.join(f'{t}:{v}' for t, v in p['missed']) or 'none'}; "
                f"spurious: {', '.join(f'{t}:{v}' for t, v in p['spurious'][:25]) or 'none'}"
            )
            L.append("")
    out = s.path("docs_dir") / "extraction-accuracy.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    (s.path("reports_dir") / "extraction_accuracy.json").write_text(
        json.dumps({"overall": {"precision": P, "recall": R, "f1": F, **T}, "pages": pages}, indent=2, default=str),
        encoding="utf-8",
    )
    return out


if __name__ == "__main__":
    print("Wrote", run())
    sys.exit(0)
