"""Validation metrics: ROC AUC and the success-rate curve (share of known occurrences captured vs
share of the area ranked as most prospective)."""

from __future__ import annotations

import numpy as np


def auc(scores_pos: np.ndarray, scores_neg: np.ndarray) -> float | None:
    """Mann-Whitney AUC: probability a random occurrence cell outranks a random background cell."""
    p = scores_pos[np.isfinite(scores_pos)]
    n = scores_neg[np.isfinite(scores_neg)]
    if len(p) == 0 or len(n) == 0:
        return None
    from scipy.stats import rankdata

    ranks = rankdata(np.concatenate([p, n]))  # average ranks for ties
    r_pos = ranks[: len(p)].sum()
    return float((r_pos - len(p) * (len(p) + 1) / 2) / (len(p) * len(n)))


def success_rate_curve(
    score_grid: np.ndarray, occ_rows: np.ndarray, occ_cols: np.ndarray, steps: int = 50
) -> list[dict[str, float]]:
    """For each area fraction a (highest-scoring cells first), fraction of occurrences inside."""
    valid = np.isfinite(score_grid)
    vals = score_grid[valid]
    if vals.size == 0 or len(occ_rows) == 0:
        return []
    occ_scores = score_grid[occ_rows, occ_cols]
    occ_scores = occ_scores[np.isfinite(occ_scores)]
    sorted_desc = np.sort(vals)[::-1]
    out = []
    for i in range(steps + 1):
        a = i / steps
        if a == 0:
            out.append({"area": 0.0, "captured": 0.0})
            continue
        k = max(1, int(round(a * len(sorted_desc))))
        thr = sorted_desc[k - 1]
        out.append(
            {"area": round(a, 4), "captured": round(float((occ_scores >= thr).mean()), 4) if len(occ_scores) else 0.0}
        )
    return out


def area_under_src(curve: list[dict[str, float]]) -> float | None:
    if not curve:
        return None
    a = np.array([c["area"] for c in curve])
    c = np.array([c["captured"] for c in curve])
    return float(np.trapezoid(c, a)) if hasattr(np, "trapezoid") else float(np.trapz(c, a))


def captured_at(curve: list[dict[str, float]], area: float) -> float | None:
    if not curve:
        return None
    best = min(curve, key=lambda c: abs(c["area"] - area))
    return best["captured"]
