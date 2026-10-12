"""Spatial CV splits, metrics, memberships and the engine on the SYNTHETIC world."""

import numpy as np
import pytest

from georevive.prospect.metrics import auc, success_rate_curve
from georevive.prospect.spatial_cv import block_ids, spatial_folds


def test_spatial_folds_never_split_a_block():
    rng = np.random.default_rng(0)
    x = rng.uniform(0, 50_000, 3000)
    y = rng.uniform(0, 40_000, 3000)
    labels = (rng.random(3000) < 0.02).astype(int)
    folds = spatial_folds(x, y, labels, block_m=5000, n_folds=5)
    assert len(folds) == 5
    blocks = block_ids(x, y, 5000)
    seen_test = set()
    for train, test in folds:
        assert not set(blocks[train]) & set(blocks[test]), "a block is in both train and test"
        assert len(set(train) & set(test)) == 0
        seen_test |= set(test)
        assert labels[test].sum() >= 1  # positives spread across folds
    assert seen_test == set(range(3000))  # every point is tested exactly once


def test_auc_and_success_curve():
    assert auc(np.array([0.9, 0.8]), np.array([0.1, 0.2, 0.3])) == pytest.approx(1.0)
    assert auc(np.array([0.1]), np.array([0.9])) == pytest.approx(0.0)
    assert auc(np.array([0.5]), np.array([0.5])) == pytest.approx(0.5)
    g = np.arange(100, dtype=float).reshape(10, 10)
    curve = success_rate_curve(g, np.array([9, 9]), np.array([9, 8]))  # the two highest cells
    assert curve[0] == {"area": 0.0, "captured": 0.0}
    top2 = min(curve, key=lambda c: abs(c["area"] - 0.02))
    assert top2["captured"] == 1.0


def test_memberships_monotonic():
    from georevive.prospect.fuzzy import membership

    d = np.array([0, 500, 1500, 5000, 20000], dtype=float)
    m = membership("dist_fault", d)
    assert np.all(np.diff(m) < 0) and m[2] == pytest.approx(0.5)
    p = membership("iron_oxide", np.array([0.1, 0.5, 0.8, 0.99]))
    assert np.all(np.diff(p) > 0) and p[2] == pytest.approx(0.5)


@pytest.fixture()
def world(temp_root):
    from georevive.config import get_settings
    from tests.synthetic_world import build

    return build(get_settings())


def test_evidence_stack_has_no_occurrence_leak(world):
    from georevive.prospect.evidence import build_stack

    st = build_stack()
    assert {"dist_fault", "host_rock", "dist_granite_contact", "iron_oxide", "slope"} <= set(st.names)
    assert not any("occ" in n or "mrds" in n for n in st.names), "occurrences must never be an input feature"
    assert all("mrds" not in lid for v in st.lineage.values() for lid in v)


def test_fuzzy_run_targets_and_explanations(world, db):
    from georevive.prospect import engine

    run = engine.run_model(db, "fuzzy", "test")
    assert len(run.targets) == 10
    t1 = min(run.targets, key=lambda t: t.rank)
    assert t1.score >= max(t.score for t in run.targets) - 1e-6
    assert "km from a mapped fault" in t1.explanation or "host rock" in t1.explanation
    assert "context only" in t1.explanation  # occurrences reported as context, not as a reason
    assert run.metrics["auc"] > 0.7  # synthetic gold sits on the synthetic shear zone
    assert run.metrics["limitations"]


def test_data_driven_runs_with_spatial_cv(world, db):
    from georevive.prospect import engine

    for method in ("logistic", "gbm"):
        run = engine.run_model(db, method, "test")
        assert run.metrics["fold_aucs"], f"{method}: no CV folds evaluated"
        assert 0 <= run.metrics["auc"] <= 1
        assert run.targets and run.targets[0].contributions
