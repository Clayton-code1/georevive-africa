"""Spatial block cross-validation: cells are grouped into square blocks, and whole blocks are held
out together, so a model is never tested on points right next to its training points."""

from __future__ import annotations

import numpy as np


def block_ids(x: np.ndarray, y: np.ndarray, block_m: float) -> np.ndarray:
    bx = np.floor(x / block_m).astype(np.int64)
    by = np.floor(y / block_m).astype(np.int64)
    return bx * 1_000_003 + by


def spatial_folds(
    x: np.ndarray, y: np.ndarray, labels: np.ndarray, block_m: float, n_folds: int, seed: int = 42
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Assign blocks to folds so positives are spread across folds as evenly as possible.
    Returns [(train_idx, test_idx)]. No block appears in both train and test of the same fold."""
    blocks = block_ids(x, y, block_m)
    uniq = np.unique(blocks)
    rng = np.random.default_rng(seed)
    pos_per_block = {b: int(labels[blocks == b].sum()) for b in uniq}
    # greedy: blocks with most positives first, each to the fold with the fewest positives so far
    order = sorted(uniq, key=lambda b: (-pos_per_block[b], rng.random()))
    fold_pos = np.zeros(n_folds)
    fold_n = np.zeros(n_folds)
    assign: dict[int, int] = {}
    for b in order:
        if pos_per_block[b] > 0:
            f = int(np.lexsort((fold_n, fold_pos))[0])
        else:
            f = int(np.argmin(fold_n))
        assign[b] = f
        fold_pos[f] += pos_per_block[b]
        fold_n[f] += int((blocks == b).sum())
    fold_of = np.array([assign[b] for b in blocks])
    out = []
    for f in range(n_folds):
        test = np.where(fold_of == f)[0]
        train = np.where(fold_of != f)[0]
        if len(test) and len(train):
            out.append((train, test))
    return out
