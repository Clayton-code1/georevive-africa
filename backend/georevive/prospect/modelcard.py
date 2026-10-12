"""docs/model-card.md - regenerated after every model run with the real metrics of that run."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .. import DISCLAIMER
from ..config import get_settings
from .fuzzy import DEFAULT_WEIGHTS, MEMBERSHIP

STATIC_TOP = """# Model card: GeoRevive gold prospectivity (prototype)

_Regenerated automatically after each model run. Last update: {now}._

> **{disclaimer}**

## Purpose
GeoRevive ranks 250 m grid cells in the pilot area ({pilot}) by how favourable they look for **orogenic gold in
Archaean greenstone belts**. The ranking supports discussion and planning of field checks. It is **not** a resource
estimate and not investment advice.

## Users
Geologists and analysts (main users), small-scale miners (through the plain-language claim check report), and
investors (shared results only).

## Models
1. **Knowledge-driven (default): fuzzy logic.** Each evidence layer becomes a 0-1 *membership* using a simple,
   published-style rule (table below). The score is the weighted mean of the memberships. The weights come from the
   Geoscience Lead, who can edit them in the app; every change is logged. This model is **not trained on known occurrences**.
2. **Data-driven: logistic regression.** Trained on known gold occurrence cells (USGS MRDS) against random background
   cells kept at least 1 km away from any occurrence. Inputs are standardised, and the coefficients explain the model directly.
3. **Data-driven: gradient boosting with SHAP explanations.** A non-linear comparison model.

**Known occurrences are never an input feature.** They are used only as training labels (models 2 and 3) and to
validate all three models.

## Evidence layers and memberships
| Evidence | Membership rule | Default weight |
|---|---|---|
{membership_rows}

## Validation method
- **Spatial block cross-validation** for the data-driven models: cells are grouped into square blocks
  ({block_km:g} km), and whole blocks are held out together, so a model is never scored on cells next to its training
  cells. This avoids the over-optimistic results of random splits.
- **AUC** = the probability that a random known-occurrence cell scores higher than a random background cell
  (0.5 = no skill, 1.0 = perfect).
- **Success-rate curve** = the share of known occurrences that fall inside the top X% of the area. For the data-driven
  models it is computed out-of-fold.
"""

STATIC_BOTTOM = """
## Limitations (read these first)
- **Labels are incomplete and biased.** MRDS is a historical compilation (no systematic updates since 2011). Many
  workings are missing, locations can be off by hundreds of metres, and recorded sites cluster near roads and old
  mining centres. Background cells are not confirmed barren.
- **Few positives.** One map sheet holds few recorded gold sites, so the data-driven models can learn local accidents
  of the data. Treat them as a second opinion to the knowledge-driven model.
- **Input quality limits the output.** If the BGS/ZGS 1:100k geology and fault layers are not available, the app falls
  back to a 1:10 million regional map and automatically interpreted DEM lineaments. Both are far too coarse for
  target-scale decisions, and the app says so in every explanation.
- **Satellite band ratios are indirect.** Iron-oxide and clay indices respond to soils, laterite, bare ground and
  burnt areas as well as to hydrothermal alteration. Cloud, water and dense vegetation are masked out.
- **Spatial autocorrelation.** Even with block cross-validation, the metrics describe this area and these labels.
  They do not transfer elsewhere.
- **Not field-verified.** No target has been checked on the ground.

## Ethical and safety considerations
- Results can influence where people dig. Claim reports therefore state in plain language that the score is a hint,
  not proof. They tell users to check claim status with the Provincial Mining Director and to get a geologist's
  site visit, and they warn against entering old workings.
- Explanations are shown for every target, so users can see *why* a cell scored high and challenge it.

## How to reproduce
```powershell
.\\.venv\\Scripts\\python.exe -m georevive.ingest --all
# then in the app: Prospectivity > choose a method > Run model for gold
```
Every run stores its weights, its evidence-layer lineage, its metrics and a score GeoTIFF
(`data/processed/prospect/run_<id>.tif`).
"""


def _membership_rows(weights: dict[str, float]) -> str:
    from .evidence import EVIDENCE_INFO

    rows = []
    for k, v in MEMBERSHIP.items():
        rows.append(f"| {EVIDENCE_INFO[k]['label']} | {v['text']} | {weights.get(k, DEFAULT_WEIGHTS.get(k, 0)):.2f} |")
    return "\n".join(rows)


def write(run: Any | None = None) -> None:
    s = get_settings()
    p = s.section("prospectivity")
    w = (run.weights if run is not None and run.weights else DEFAULT_WEIGHTS) or DEFAULT_WEIGHTS
    text = STATIC_TOP.format(
        now=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        disclaimer=DISCLAIMER,
        pilot=s.pilot_name,
        membership_rows=_membership_rows(w),
        block_km=float(p.get("spatial_cv_block_m", 5000)) / 1000,
    )
    if run is not None:
        m = run.metrics
        ev = m.get("evidence", {})
        lines = ["", f"## Latest run (run {run.id}, {run.method}, {run.created_at:%Y-%m-%d %H:%M} UTC)", ""]
        lines.append(
            f"- Known gold occurrences in the pilot area: **{m.get('n_known_occurrences')}** "
            f"({m.get('n_positive_cells')} grid cells)"
        )
        auc = m.get("auc")
        lines.append(f"- AUC: **{auc:.3f}**" if auc is not None else "- AUC: not available")
        if m.get("fold_aucs"):
            lines.append(f"- AUC per spatial fold: {', '.join(str(a) for a in m['fold_aucs'])}")
        for k, lab in (("captured_top10pct", "10%"), ("captured_top20pct", "20%")):
            if m.get(k) is not None:
                lines.append(f"- Share of known occurrences in the top {lab} of the area: **{m[k] * 100:.0f}%**")
        lines.append(f"- Validation: {m.get('validation')}")
        lines.append("- Evidence used: " + ", ".join(a["label"] for a in ev.get("available", [])))
        for u in ev.get("unavailable", []):
            lines.append(f"- Not used - {u['label']}: {u['reason']}")
        if m.get("coefficients"):
            lines.append(
                "- Logistic coefficients (standardised): "
                + ", ".join(f"{k} {v:+.2f}" for k, v in m["coefficients"].items())
            )
        lines.append("")
        lines.append("Run-specific limitations:")
        lines += [f"- {x}" for x in m.get("limitations", [])]
        text += "\n".join(lines) + "\n"
    else:
        text += "\n## Latest run\nNo model has been run yet.\n"
    text += STATIC_BOTTOM
    out = s.path("docs_dir") / "model-card.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    from sqlalchemy import select

    from ..db import session_scope
    from ..models import ModelRun

    with session_scope() as db:
        write(db.scalar(select(ModelRun).order_by(ModelRun.id.desc())))
    print("Wrote docs/model-card.md")
