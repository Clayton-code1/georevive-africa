"""Turn per-cell feature contributions into plain-language sentences with real values."""

from __future__ import annotations

from typing import Any

import numpy as np

from .evidence import EVIDENCE_INFO, EvidenceStack


def describe(name: str, st: EvidenceStack, r: int, c: int) -> str:
    raw = st.raw.get(name)
    v = float(raw[r, c]) if raw is not None and np.isfinite(raw[r, c]) else None
    if v is None:
        return f"no {EVIDENCE_INFO[name]['label'].lower()} data here"
    if name == "dist_fault":
        what = (
            "an interpreted DEM lineament (unverified)"
            if "lineament" in (st.notes.get(name) or "")
            else "a mapped fault or shear zone"
        )
        return f"within 100 m of {what}" if v < 100 else f"{v / 1000:.1f} km from {what}"
    if name == "dist_granite_contact":
        if v < 100:
            return "within 100 m of a granite-greenstone contact"
        return f"{v / 1000:.1f} km from a granite-greenstone contact"
    if name == "host_rock":
        unit = ""
        if st.unit_names is not None and st.unit_names[r, c]:
            unit = f" ({st.unit_names[r, c]})"
        coarse = " - from the 1:10M regional map" if "regional" in (st.notes.get(name) or "") else ""
        if v == 2:
            return f"greenstone / mafic-ultramafic host rock{unit}{coarse}"
        if v == 1:
            return f"granite or gneiss{unit} (less favourable host){coarse}"
        return f"cover or other rocks{unit} (unfavourable){coarse}"
    if name in ("iron_oxide", "clay", "ferrous"):
        label = {"iron_oxide": "iron-oxide", "clay": "clay/hydroxyl alteration", "ferrous": "ferrous-iron"}[name]
        p = st.layers[name][r, c]
        if not np.isfinite(p):
            return f"{label} index masked (cloud, water or dense vegetation)"
        top = 100 - p * 100
        if top <= 50:
            return f"{label} index in the top {max(1, round(top))}% of the area"
        return f"{label} index below the area median"
    if name == "slope":
        return f"slope {v:.0f}°"
    if name == "roughness":
        return f"terrain roughness {v:.1f} m"
    return f"{name} = {v:.3g}"


def contributions_list(
    names: list[str], contrib: np.ndarray, st: EvidenceStack, r: int, c: int, weights: dict[str, float] | None = None
) -> list[dict[str, Any]]:
    out = []
    for k, val in zip(names, contrib, strict=True):
        if not np.isfinite(val):
            continue
        out.append(
            {
                "feature": k,
                "label": EVIDENCE_INFO[k]["label"],
                "contribution": round(float(val), 4),
                "text": describe(k, st, r, c),
                "weight": None if weights is None else round(weights.get(k, 0), 3),
            }
        )
    out.sort(key=lambda d: -d["contribution"])
    return out


def sentence(contribs: list[dict[str, Any]], context: dict[str, Any], max_items: int = 4) -> str:
    pos = [d["text"] for d in contribs if d["contribution"] > 0][:max_items]
    parts = pos or ["no single factor stands out; the score reflects several moderate factors"]
    ctx = []
    n = context.get("known_within_km")
    if n is not None:
        ctx.append(
            f"{n} known gold occurrence{'s' if n != 1 else ''} within {context.get('radius_km', 5):g} km "
            "(context only - not used in the score)"
        )
    return "; ".join(parts) + (". " + "; ".join(ctx) if ctx else "") + "."
