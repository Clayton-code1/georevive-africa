"""Knowledge-driven model: fuzzy memberships combined by a weighted fuzzy sum (weighted mean).
Memberships and weights are deliberately simple so a geologist can read and edit them."""

from __future__ import annotations

from typing import Any

import numpy as np

# Defaults for orogenic gold in Archaean greenstone belts. The Geoscience Lead should review these.
DEFAULT_WEIGHTS: dict[str, float] = {
    "dist_fault": 0.25,
    "host_rock": 0.25,
    "dist_granite_contact": 0.15,
    "iron_oxide": 0.10,
    "clay": 0.10,
    "ferrous": 0.05,
    "slope": 0.05,
    "roughness": 0.05,
}

MEMBERSHIP: dict[str, dict[str, Any]] = {
    # decreasing with distance: mu = 1 / (1 + (d / d50)^k)
    "dist_fault": {
        "kind": "distance",
        "d50": 1500.0,
        "k": 2.0,
        "text": "Closer to a fault or shear zone is more favourable (half-way at 1.5 km).",
    },
    "dist_granite_contact": {
        "kind": "distance",
        "d50": 3000.0,
        "k": 2.0,
        "text": "Closer to a granite-greenstone contact is more favourable (half-way at 3 km).",
    },
    "host_rock": {
        "kind": "direct",
        "text": "Greenstone / mafic-ultramafic = 1.0, granite-gneiss = 0.35, other/cover = 0.1.",
    },
    # increasing with percentile: logistic centred on the 80th percentile
    "iron_oxide": {
        "kind": "percentile",
        "p50": 0.8,
        "s": 0.07,
        "text": "Higher iron-oxide index (top 20%) is favourable.",
    },
    "clay": {
        "kind": "percentile",
        "p50": 0.8,
        "s": 0.07,
        "text": "Higher clay/hydroxyl index (top 20%) is favourable.",
    },
    "ferrous": {"kind": "percentile", "p50": 0.8, "s": 0.07, "text": "Higher ferrous-iron index is favourable."},
    # terrain: gentle preference for moderate relief (subcropping resistant reefs / ridges)
    "slope": {
        "kind": "band",
        "lo": 2.0,
        "hi": 15.0,
        "text": "Moderate slopes (2-15°) slightly favoured; flat cover or steep scarps less so.",
    },
    "roughness": {
        "kind": "percentile_raw",
        "p50": 0.6,
        "s": 0.15,
        "text": "Rougher ground (outcrop) slightly favoured.",
    },
}


def membership(name: str, a: np.ndarray) -> np.ndarray:
    m = MEMBERSHIP[name]
    with np.errstate(invalid="ignore", over="ignore"):
        if m["kind"] == "distance":
            return (1.0 / (1.0 + (a / m["d50"]) ** m["k"])).astype("float32")
        if m["kind"] == "direct":
            return a.astype("float32")
        if m["kind"] == "percentile":
            return (1.0 / (1.0 + np.exp(-(a - m["p50"]) / m["s"]))).astype("float32")
        if m["kind"] == "percentile_raw":
            from .evidence import percentile_rank

            p = percentile_rank(a)
            return (1.0 / (1.0 + np.exp(-(p - m["p50"]) / m["s"]))).astype("float32")
        if m["kind"] == "band":
            lo, hi = m["lo"], m["hi"]
            mu = np.where(a < lo, 0.4 + 0.6 * a / lo, np.where(a <= hi, 1.0, np.maximum(0.2, 1 - (a - hi) / 20)))
            return mu.astype("float32")
    raise ValueError(name)


def normalise_weights(weights: dict[str, float], available: list[str]) -> dict[str, float]:
    w = {k: max(0.0, float(weights.get(k, 0.0))) for k in available}
    tot = sum(w.values())
    if tot <= 0:
        raise ValueError("All weights are zero.")
    return {k: v / tot for k, v in w.items()}


def fuzzy_score(layers: dict[str, np.ndarray], weights: dict[str, float]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Weighted mean of memberships. Cells missing a layer use the remaining layers (weights renormalised
    per cell). Returns (score 0-1, per-layer membership)."""
    names = [k for k in layers if weights.get(k, 0) > 0]
    w = normalise_weights(weights, names)
    mus = {k: membership(k, layers[k]) for k in names}
    num = np.zeros(next(iter(layers.values())).shape, dtype="float32")
    den = np.zeros_like(num)
    for k in names:
        valid = np.isfinite(mus[k])
        num += np.where(valid, w[k] * mus[k], 0)
        den += np.where(valid, w[k], 0)
    score = np.where(den > 0.5, num / np.maximum(den, 1e-9), np.nan).astype("float32")
    return score, mus
