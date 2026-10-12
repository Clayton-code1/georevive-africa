"""Scan enhancement for faded, stained and unevenly lit pages.

Steps (each saved as a PNG with its parameters so the run can be reproduced):
  1. stain_reduction   colour page -> grey using the channel least affected by yellow/brown stains
  2. deskew            estimate text-line angle and rotate
  3. denoise           non-local means
  4. illumination      divide by a large-scale background estimate (flat-field correction)
  5. clahe             contrast-limited adaptive histogram equalisation
  6. binarize          Sauvola local threshold (input for OCR)
The original image is never modified.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "stain_reduction": {"method": "max_rgb_channel_blend", "weight_max": 0.7},
    "deskew": {"max_angle_deg": 10.0},
    "denoise": {"h": 7, "template_window": 7, "search_window": 21},
    "illumination": {"background_kernel_frac": 0.04, "method": "morphological_close_then_divide"},
    "clahe": {"clip_limit": 2.0, "tile_grid": 8},
    "binarize": {"method": "sauvola", "window": 31, "k": 0.2},
}
STEP_ORDER = list(DEFAULT_PARAMS)


@dataclass
class EnhanceResult:
    steps: list[dict[str, Any]] = field(default_factory=list)  # [{name, path, params, info}]
    final_gray: np.ndarray | None = None  # after clahe (for display / RapidOCR)
    binary: np.ndarray | None = None  # for Tesseract
    angle: float = 0.0


def load_image(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)  # works with non-ASCII Windows paths
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot read image {path}")
    return img


def save_png(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("PNG encoding failed")
    buf.tofile(str(path))


# --- individual steps -------------------------------------------------------------
def stain_reduction(bgr: np.ndarray, weight_max: float = 0.7, **_: Any) -> np.ndarray:
    """Yellow/brown foxing absorbs blue light; ink is dark in every channel. Taking the per-pixel
    maximum of the colour channels lifts stains towards the paper tone while keeping ink dark."""
    if bgr.ndim == 2:
        return bgr.copy()
    mx = bgr.max(axis=2).astype(np.float32)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    out = weight_max * mx + (1 - weight_max) * gray
    return np.clip(out, 0, 255).astype(np.uint8)


def estimate_skew(gray: np.ndarray, max_angle_deg: float = 10.0) -> float:
    """Angle (degrees, counter-clockwise positive) that makes text lines horizontal.
    Uses a projection-profile search, which is robust for printed text pages."""
    small = gray
    scale = 1.0
    if max(gray.shape) > 1600:
        scale = 1600 / max(gray.shape)
        small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    inv = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    h, w = inv.shape
    center = (w / 2, h / 2)

    def score(angle: float) -> float:
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rot = cv2.warpAffine(inv, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        prof = rot.sum(axis=1, dtype=np.float64)
        return float(np.var(prof))

    best = 0.0
    best_s = score(0.0)
    for step in (1.0, 0.25, 0.05):
        lo, hi = (
            best - (max_angle_deg if step == 1.0 else step * 4),
            best + (max_angle_deg if step == 1.0 else step * 4),
        )
        for a in np.arange(lo, hi + 1e-9, step):
            s = score(float(a))
            if s > best_s:
                best, best_s = float(a), s
    return round(best, 2)


def rotate(img: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.01:
        return img.copy()
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    border = int(np.median(img)) if img.ndim == 2 else tuple(int(v) for v in np.median(img.reshape(-1, 3), axis=0))
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=border)


def denoise(gray: np.ndarray, h: int = 7, template_window: int = 7, search_window: int = 21, **_: Any) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, None, h=h, templateWindowSize=template_window, searchWindowSize=search_window)


def background(gray: np.ndarray, kernel_frac: float = 0.04) -> np.ndarray:
    k = max(15, int(round(max(gray.shape) * kernel_frac)) | 1)
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, se)  # removes dark text, keeps paper/illumination
    return cv2.GaussianBlur(bg, (0, 0), k / 3)


def illumination_correction(gray: np.ndarray, background_kernel_frac: float = 0.04, **_: Any) -> np.ndarray:
    """Flat-field correction: divide by the estimated background so uneven lighting and
    faded areas become an even white page."""
    bg = background(gray, background_kernel_frac).astype(np.float32)
    out = gray.astype(np.float32) / np.maximum(bg, 1.0) * 235.0
    return np.clip(out, 0, 255).astype(np.uint8)


def clahe(gray: np.ndarray, clip_limit: float = 2.0, tile_grid: int = 8, **_: Any) -> np.ndarray:
    c = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    return c.apply(gray)


def binarize(gray: np.ndarray, window: int = 31, k: float = 0.2, **_: Any) -> np.ndarray:
    from skimage.filters import threshold_sauvola

    window = window | 1
    t = threshold_sauvola(gray, window_size=window, k=k)
    return np.where(gray > t, 255, 0).astype(np.uint8)


# --- quality ----------------------------------------------------------------------
def quality(gray: np.ndarray) -> dict[str, float]:
    """Simple, explainable legibility indicators (0-100 overall).

    contrast   - local ink-to-paper contrast: how much darker the text is than the paper around it (0-1)
    uniformity - evenness of the paper/lighting across the page (1 = evenly lit)
    noise      - speckle on the paper (grey levels; lower is better)
    sharpness  - Laplacian variance (reported for information; noise also raises it)
    """
    g = gray.astype(np.float32)
    bg = background(gray, 0.04).astype(np.float32)
    darker = np.clip(bg - g, 0, None)  # positive where ink sits on paper
    thr = np.percentile(darker, 97)
    ink = darker[darker >= thr]
    contrast = float(ink.mean() / 255.0) if ink.size else 0.0
    uniformity = float(max(0.0, 1.0 - bg.std() / max(bg.mean(), 1.0) * 4))
    paper = darker < 8
    noise = float((g - bg)[paper].std()) if paper.any() else 0.0
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    overall = 100 * (0.4 * min(contrast / 0.6, 1.0) + 0.4 * uniformity + 0.2 * (1 - min(noise / 30.0, 1.0)))
    return {
        "contrast": round(contrast, 3),
        "uniformity": round(uniformity, 3),
        "noise": round(noise, 2),
        "sharpness": round(sharp, 1),
        "overall": round(overall, 1),
    }


# --- pipeline ----------------------------------------------------------------------
def enhance(img: np.ndarray, out_dir: Path, params: dict[str, dict[str, Any]] | None = None) -> EnhanceResult:
    p = {k: {**v, **((params or {}).get(k) or {})} for k, v in DEFAULT_PARAMS.items()}
    out_dir.mkdir(parents=True, exist_ok=True)
    res = EnhanceResult()

    def record(i: int, name: str, arr: np.ndarray, info: dict[str, Any] | None = None) -> None:
        path = out_dir / f"{i:02d}_{name}.png"
        save_png(path, arr)
        res.steps.append({"name": name, "path": path, "params": p.get(name, {}), "info": info or {}})

    gray = stain_reduction(img, **p["stain_reduction"])
    record(1, "stain_reduction", gray)
    angle = estimate_skew(gray, p["deskew"]["max_angle_deg"])
    gray = rotate(gray, angle)
    res.angle = angle
    record(2, "deskew", gray, {"angle_deg": angle})
    gray = denoise(gray, **p["denoise"])
    record(3, "denoise", gray)
    gray = illumination_correction(gray, **p["illumination"])
    record(4, "illumination", gray)
    gray = clahe(gray, **p["clahe"])
    record(5, "clahe", gray)
    res.final_gray = gray
    binary = binarize(gray, **p["binarize"])
    record(6, "binarize", binary)
    res.binary = binary
    (out_dir / "params.json").write_text(
        json.dumps({"order": STEP_ORDER, "params": p, "deskew_angle": angle}, indent=2), encoding="utf-8"
    )
    return res
