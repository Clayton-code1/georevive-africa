"""Run a prospectivity model, validate it honestly, rank targets and store everything with lineage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sqlalchemy.orm import Session

from .. import DISCLAIMER
from ..config import get_settings
from ..ingest.process import Grid, gpkg_tables, read_vector, render_overlay, write_cog
from ..models import ModelRun, Target
from ..registry import rel, upsert_layer, upsert_source
from . import explain
from .evidence import EvidenceStack, build_stack, occurrences, stack_summary
from .fuzzy import DEFAULT_WEIGHTS, MEMBERSHIP, fuzzy_score, normalise_weights
from .metrics import area_under_src, auc, captured_at, success_rate_curve
from .spatial_cv import spatial_folds

METHODS = ("fuzzy", "logistic", "gbm")
MIN_POSITIVES = 8
_STACK_CACHE: dict[str, EvidenceStack] = {}


def run_dir() -> Path:
    p = get_settings().path("processed_dir") / "prospect"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_stack(refresh: bool = False) -> EvidenceStack:
    gpkg = get_settings().path("gpkg")
    key = f"{gpkg}:{gpkg.stat().st_mtime if gpkg.exists() else 0}"
    if refresh or key not in _STACK_CACHE:
        _STACK_CACHE.clear()
        _STACK_CACHE[key] = build_stack()
    return _STACK_CACHE[key]


def occurrence_cells(grid: Grid, gdf) -> tuple[np.ndarray, np.ndarray]:
    if gdf is None or len(gdf) == 0:
        return np.array([], int), np.array([], int)
    inv = ~grid.transform
    rows, cols = [], []
    for g in gdf.geometry:
        cx, cy = inv * (g.x, g.y)
        r, c = int(np.floor(cy)), int(np.floor(cx))
        if 0 <= r < grid.height and 0 <= c < grid.width:
            rows.append(r)
            cols.append(c)
    return np.array(rows, int), np.array(cols, int)


def feature_matrix(st: EvidenceStack, names: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """X for all cells (n_cells x n_features) with NaNs filled by the median; valid mask per cell."""
    X = np.stack([st.layers[k].ravel() for k in names], axis=1).astype("float64")
    finite = np.isfinite(X)
    valid = finite.mean(axis=1) >= 0.6
    if st.exclude is not None:
        valid &= ~st.exclude.ravel()
    med = np.nanmedian(np.where(finite, X, np.nan), axis=0)
    X = np.where(finite, X, med)
    return X, valid


def _context(grid: Grid, r: int, c: int, occ_xy: np.ndarray, radius_m: float) -> dict[str, Any]:
    x, y = grid.transform * (c + 0.5, r + 0.5)
    ctx: dict[str, Any] = {"radius_km": radius_m / 1000}
    if len(occ_xy):
        d = np.hypot(occ_xy[:, 0] - x, occ_xy[:, 1] - y)
        ctx["known_within_km"] = int((d <= radius_m).sum())
        ctx["nearest_known_km"] = round(float(d.min()) / 1000, 2)
    else:
        ctx["known_within_km"] = 0
    return ctx


def cell_polygon(grid: Grid, r: int, c: int) -> tuple[dict[str, Any], float, float]:
    from pyproj import Transformer
    from shapely.geometry import box, mapping
    from shapely.ops import transform as stransform

    x0, y0 = grid.transform * (c, r + 1)
    x1, y1 = grid.transform * (c + 1, r)
    t = Transformer.from_crs(grid.crs, "EPSG:4326", always_xy=True)
    poly = stransform(lambda xx, yy, z=None: t.transform(xx, yy), box(x0, y0, x1, y1))
    cx, cy = t.transform((x0 + x1) / 2, (y0 + y1) / 2)
    return mapping(poly), cx, cy


def pick_targets(score: np.ndarray, grid: Grid, n: int = 10, min_sep_m: float = 1500) -> list[tuple[int, int]]:
    order = np.argsort(np.where(np.isfinite(score), score, -np.inf).ravel())[::-1]
    picked: list[tuple[int, int]] = []
    sep = min_sep_m / grid.res
    for idx in order:
        r, c = divmod(int(idx), grid.width)
        if not np.isfinite(score[r, c]):
            break
        if all((r - pr) ** 2 + (c - pc) ** 2 >= sep**2 for pr, pc in picked):
            picked.append((r, c))
        if len(picked) >= n:
            break
    return picked


def _district_lookup():
    gpkg = get_settings().path("gpkg")
    if "admin_adm2" not in gpkg_tables(gpkg):
        return None
    return read_vector(gpkg, "admin_adm2")


def run_model(
    db: Session, method: str, username: str, weights: dict[str, float] | None = None, commodity: str = "gold"
) -> ModelRun:
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    s = get_settings()
    pcfg = s.section("prospectivity")
    st = get_stack()
    names = st.names
    if not names:
        raise RuntimeError("No evidence layers are available - run ingestion first.")
    grid = st.grid
    occ = occurrences(commodity)
    orow, ocol = occurrence_cells(grid, occ)
    occ_xy = np.array([[g.x, g.y] for g in occ.geometry]) if occ is not None and len(occ) else np.zeros((0, 2))
    n_pos = len(np.unique(orow * grid.width + ocol)) if len(orow) else 0
    xs, ys = grid.cell_centers()
    metrics: dict[str, Any] = {
        "commodity": commodity,
        "n_known_occurrences": int(len(occ_xy)),
        "n_positive_cells": int(n_pos),
        "evidence": stack_summary(st),
        "disclaimer": DISCLAIMER,
    }
    limitations: list[str] = [
        "Known occurrences (USGS MRDS) are historical compilations with approximate locations; many deposits are "
        "missing and absence of a record does not mean absence of gold.",
        "Background points are a random sample of the area, not confirmed barren ground.",
    ]
    limitations += [f"{k}: {v}" for k, v in st.notes.items()]
    limitations += [f"Not used ({k}): {v}" for k, v in st.unavailable.items()]
    if st.exclude_note:
        limitations.append(st.exclude_note)
    artefacts: dict[str, Any] = {"names": names}
    w_used: dict[str, float] = {}

    if method == "fuzzy":
        w_used = normalise_weights(
            weights or DEFAULT_WEIGHTS, [k for k in names if (weights or DEFAULT_WEIGHTS).get(k, 0) > 0]
        )
        score, mus = fuzzy_score(st.layers, w_used)
        if st.exclude is not None:
            score[st.exclude] = np.nan  # built-up / water: no score, never a target
        mean_mu = {k: float(np.nanmean(mus[k])) for k in mus}
        artefacts.update({"kind": "fuzzy", "weights": w_used, "mean_mu": mean_mu})
        metrics["validation"] = (
            "Knowledge-driven model (not trained on occurrences): validated directly against all known occurrences."
        )
        valid = np.isfinite(score)
        bg = score[valid]
        if n_pos:
            metrics["auc"] = auc(score[orow, ocol], bg)
        metrics["success_rate"] = success_rate_curve(score, orow, ocol)
    else:
        X, valid_cells = feature_matrix(st, names)
        flat_pos = np.unique(orow * grid.width + ocol) if len(orow) else np.array([], int)
        if n_pos < MIN_POSITIVES:
            raise RuntimeError(
                f"Only {n_pos} known {commodity} occurrence cells in the pilot area - too few to train "
                f"a data-driven model honestly (minimum {MIN_POSITIVES}). Use the knowledge-driven model."
            )
        rng = np.random.default_rng(7)
        # background: random valid cells farther than the exclusion distance from any occurrence
        excl = float(pcfg.get("background_exclusion_m", 1000))
        cand = np.where(valid_cells)[0]
        cx, cy = xs.ravel()[cand], ys.ravel()[cand]
        from scipy.spatial import cKDTree

        tree = cKDTree(occ_xy)
        dmin, _ = tree.query(np.c_[cx, cy])
        cand = cand[dmin > excl]
        n_bg = min(int(pcfg.get("random_background_points", 2000)), len(cand))
        bg_idx = rng.choice(cand, n_bg, replace=False)
        idx = np.concatenate([flat_pos, bg_idx])
        yv = np.concatenate([np.ones(len(flat_pos)), np.zeros(len(bg_idx))])
        Xs = X[idx]
        model, mu, sd = _fit(method, Xs, yv)
        # spatial CV
        folds = spatial_folds(
            xs.ravel()[idx],
            ys.ravel()[idx],
            yv,
            float(pcfg.get("spatial_cv_block_m", 5000)),
            int(pcfg.get("spatial_cv_folds", 5)),
        )
        fold_aucs, oof_rank = [], []
        all_valid = np.where(valid_cells)[0]
        for tr, te in folds:
            if yv[tr].sum() < 3 or yv[te].sum() < 1 or (1 - yv[te]).sum() < 1:
                continue
            m_f, mu_f, sd_f = _fit(method, Xs[tr], yv[tr])
            p_te = _predict(method, m_f, mu_f, sd_f, Xs[te])
            a = auc(p_te[yv[te] == 1], p_te[yv[te] == 0])
            if a is not None:
                fold_aucs.append(a)
            # rank of held-out positives within the whole area (for an out-of-fold success-rate curve)
            p_all = _predict(method, m_f, mu_f, sd_f, X[all_valid])
            sorted_all = np.sort(p_all)
            for p in p_te[yv[te] == 1]:
                oof_rank.append(1 - np.searchsorted(sorted_all, p) / len(sorted_all))
        metrics["validation"] = (
            f"Spatial block cross-validation ({len(folds)} folds, "
            f"{pcfg.get('spatial_cv_block_m', 5000) / 1000:g} km blocks)."
        )
        metrics["fold_aucs"] = [round(a, 3) for a in fold_aucs]
        metrics["auc"] = float(np.mean(fold_aucs)) if fold_aucs else None
        if oof_rank:
            oof = np.array(oof_rank)
            metrics["success_rate"] = [
                {"area": round(a, 4), "captured": round(float((oof <= a).mean()), 4)} for a in np.linspace(0, 1, 51)
            ]
        else:
            metrics["success_rate"] = []
        metrics["n_background"] = int(n_bg)
        prob = np.full(grid.height * grid.width, np.nan, dtype="float32")
        prob[all_valid] = _predict(method, model, mu, sd, X[all_valid])
        score = prob.reshape(grid.shape)
        if st.exclude is not None:
            score[st.exclude] = np.nan
        artefacts.update(
            {"kind": method, "mu": mu.tolist(), "sd": sd.tolist(), "X_mean": X[all_valid].mean(axis=0).tolist()}
        )
        joblib.dump(model, run_dir() / f"model_{method}.joblib")
        if method == "logistic":
            metrics["coefficients"] = {k: round(float(c), 4) for k, c in zip(names, model.coef_[0], strict=True)}
        limitations.append(
            f"Trained on {n_pos} occurrence cells: with so few positives the model can learn local "
            "accidents of the data; treat its ranking as a second opinion to the knowledge-driven model."
        )
    metrics["auc_note"] = (
        ("AUC 0.5 = no better than random, 1.0 = perfect. Computed on held-out spatial blocks for data-driven models.")
        if method != "fuzzy"
        else ("AUC compares known-occurrence cells with all other cells.")
    )
    metrics["captured_top10pct"] = captured_at(metrics.get("success_rate", []), 0.10)
    metrics["captured_top20pct"] = captured_at(metrics.get("success_rate", []), 0.20)
    metrics["area_under_success_curve"] = area_under_src(metrics.get("success_rate", []))
    metrics["limitations"] = limitations

    # rescale to 0-100 for display
    vals = score[np.isfinite(score)]
    lo, hi = (float(vals.min()), float(vals.max())) if vals.size else (0.0, 1.0)
    disp = ((score - lo) / (hi - lo + 1e-12) * 100).astype("float32")

    run = ModelRun(
        commodity=commodity,
        method=method,
        weights=w_used,
        features=[{"evidence": k, "layers": st.lineage.get(k, [])} for k in names],
        metrics=metrics,
        username=username,
    )
    db.add(run)
    db.flush()
    tif = write_cog(disp, grid, run_dir() / f"run_{run.id}.tif")
    png = run_dir() / f"run_{run.id}.png"
    bounds, legend = render_overlay(disp, grid, png, cmap="YlOrRd", vmin=0, vmax=100, alpha=0.75)
    legend["note"] = "Relative prospectivity (0 = lowest in area, 100 = highest)"
    run.grid_path, run.overlay_png, run.overlay_bounds = rel(tif), rel(png), bounds
    (run_dir() / f"run_{run.id}_artefacts.json").write_text(json.dumps(artefacts, default=float), encoding="utf-8")
    np.savez_compressed(run_dir() / f"run_{run.id}_stack.npz", **{k: st.layers[k] for k in names})

    # targets
    radius = float(pcfg.get("context_radius_m", 5000))
    districts = _district_lookup()
    for rank, (r, c) in enumerate(pick_targets(disp, grid), start=1):
        contrib = explain_cell(run, st, r, c)
        poly, lon, lat = cell_polygon(grid, r, c)
        ctx = _context(grid, r, c, occ_xy, radius)
        if districts is not None:
            from shapely.geometry import Point

            hit = districts[districts.contains(Point(lon, lat))]
            ctx["district"] = str(hit.iloc[0]["shapeName"]) if len(hit) else None
        db.add(
            Target(
                run_id=run.id,
                rank=rank,
                cell_row=r,
                cell_col=c,
                lon=lon,
                lat=lat,
                polygon=poly,
                score=round(float(disp[r, c]), 1),
                contributions=contrib,
                context=ctx,
                explanation=explain.sentence(contrib, ctx),
            )
        )
    _register_layer(db, run, legend, st)
    db.flush()
    try:
        from . import modelcard

        db.refresh(run)
        modelcard.write(run)
    except Exception:  # the model card is documentation; never fail a run because of it
        pass
    return run


def _fit(method: str, X: np.ndarray, y: np.ndarray):
    mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-9
    Z = (X - mu) / sd
    if method == "logistic":
        from sklearn.linear_model import LogisticRegression

        m = LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000)
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier

        m = HistGradientBoostingClassifier(
            max_depth=3,
            max_iter=150,
            learning_rate=0.08,
            l2_regularization=1.0,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=0,
        )
    m.fit(Z, y)
    return m, mu, sd


def _predict(method: str, m, mu, sd, X: np.ndarray) -> np.ndarray:
    return m.predict_proba((X - mu) / sd)[:, 1]


def load_artefacts(run: ModelRun) -> dict[str, Any]:
    return json.loads((run_dir() / f"run_{run.id}_artefacts.json").read_text(encoding="utf-8"))


def explain_cell(run: ModelRun, st: EvidenceStack, r: int, c: int) -> list[dict[str, Any]]:
    art = load_artefacts(run) if (run_dir() / f"run_{run.id}_artefacts.json").exists() else None
    names = st.names
    if run.method == "fuzzy":
        from .fuzzy import membership

        w = run.weights or (art or {}).get("weights", {})
        mean_mu = (art or {}).get("mean_mu") or {k: float(np.nanmean(membership(k, st.layers[k]))) for k in w}
        keys = [k for k in w if k in st.layers]
        vals = []
        for k in keys:
            mu = membership(k, st.layers[k][r : r + 1, c : c + 1])[0, 0]
            vals.append(w[k] * (mu - mean_mu[k]) if np.isfinite(mu) else np.nan)
        return explain.contributions_list(keys, np.array(vals), st, r, c, w)
    assert art is not None
    x = np.array([st.layers[k][r, c] for k in names], dtype="float64")
    xm = np.array(art["X_mean"])
    x = np.where(np.isfinite(x), x, xm)
    mu, sd = np.array(art["mu"]), np.array(art["sd"])
    model = joblib.load(run_dir() / f"model_{run.method}.joblib")
    z = (x - mu) / sd
    zbar = (xm - mu) / sd
    if run.method == "logistic":
        vals = model.coef_[0] * (z - zbar)
    else:
        import shap

        expl = shap.TreeExplainer(model)
        vals = np.asarray(expl.shap_values(z.reshape(1, -1))).reshape(-1)[-len(names) :]
    return explain.contributions_list(names, vals, st, r, c)


def _register_layer(db: Session, run: ModelRun, legend: dict, st: EvidenceStack) -> None:
    from ..models import Layer

    feature_layers = sorted({lid for v in st.lineage.values() for lid in v})
    srcs = sorted({db.get(Layer, lid).source_id for lid in feature_layers if db.get(Layer, lid) is not None})
    from ..models import Source

    upstream = sorted({db.get(Source, s).licence for s in srcs if db.get(Source, s) is not None})
    upsert_source(
        db,
        "georevive_prospectivity",
        name="GeoRevive prospectivity model outputs",
        publisher="GeoRevive team (derived)",
        url="/prospectivity",
        licence="Derived output; inherits the terms of its inputs: " + " | ".join(upstream),
        status="downloaded",
        note="Prospectivity scores and ranked targets computed by GeoRevive.",
        usage="Prospectivity heat map, target list and claim-check reports.",
        details={"latest_run": run.id, "derived_from_sources": srcs},
    )
    upsert_layer(
        db,
        f"prospectivity_{run.commodity}",
        source_id="georevive_prospectivity",
        name=f"Prospectivity - {run.commodity} ({run.method}, run {run.id})",
        group="prospectivity",
        kind="raster",
        raster_path=run.grid_path,
        overlay_png=run.overlay_png,
        overlay_bounds=run.overlay_bounds,
        legend=legend,
        attribution="Prospectivity: GeoRevive prototype model (requires field verification)",
        description=DISCLAIMER,
        derived_from=[{"kind": "source", "source_id": s} for s in srcs]
        + [{"kind": "layer", "layer_id": lid} for lid in feature_layers],
    )


def membership_doc() -> dict[str, Any]:
    return {k: v["text"] for k, v in MEMBERSHIP.items()}
