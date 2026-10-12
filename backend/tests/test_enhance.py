"""Enhancement steps on a SYNTHETIC degraded page (generated text, uneven light, a stain, a tilt)."""

import cv2
import numpy as np
import pytest

from georevive.rescue import enhance as E


def synthetic_page(angle: float = 0.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    h, w = 900, 700
    img = np.full((h, w, 3), 235, np.uint8)
    for i in range(18):
        cv2.putText(
            img,
            "SYNTHETIC quartz reef 12 dwt per ton",
            (40, 60 + i * 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (25, 25, 25),
            2,
            cv2.LINE_AA,
        )
    # uneven illumination: dark towards bottom-right
    yy, xx = np.mgrid[0:h, 0:w]
    light = 1.0 - 0.45 * (xx / w) * (yy / h)
    img = (img.astype(np.float32) * light[..., None]).astype(np.uint8)
    # brown stain (low blue)
    cv2.circle(img, (450, 300), 90, (60, 120, 170), -1)
    img = cv2.GaussianBlur(img, (0, 0), 1.0)
    img = np.clip(img + rng.normal(0, 6, img.shape), 0, 255).astype(np.uint8)
    if angle:
        img = E.rotate(img, angle)
    return img


def test_stain_reduction_lifts_stain():
    img = synthetic_page()
    gray_plain = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out = E.stain_reduction(img)
    # inside the stain (away from text lines) the output is brighter than plain greyscale
    assert out[300, 450] > gray_plain[300, 450] + 20


@pytest.mark.parametrize("angle", [3.0, -2.0])
def test_deskew_estimates_angle(angle):
    img = synthetic_page(angle=angle)
    gray = E.stain_reduction(img)
    est = E.estimate_skew(gray)
    assert est == pytest.approx(-angle, abs=0.5)


def test_illumination_correction_improves_uniformity():
    gray = E.stain_reduction(synthetic_page())
    before = E.quality(gray)["uniformity"]
    after = E.quality(E.illumination_correction(gray))["uniformity"]
    assert after > before


def test_binarize_is_binary():
    gray = E.clahe(E.illumination_correction(E.stain_reduction(synthetic_page())))
    b = E.binarize(gray)
    assert set(np.unique(b)) <= {0, 255}
    assert 0.02 < (b == 0).mean() < 0.5  # some ink, mostly paper


def test_pipeline_saves_every_step_and_keeps_original(tmp_path):
    img = synthetic_page(angle=2.0)
    copy = img.copy()
    res = E.enhance(img, tmp_path)
    assert [s["name"] for s in res.steps] == E.STEP_ORDER
    for s in res.steps:
        assert s["path"].exists()
    assert (tmp_path / "params.json").exists()
    assert np.array_equal(img, copy), "original image must not be modified"
    q0 = E.quality(cv2.cvtColor(copy, cv2.COLOR_BGR2GRAY))
    q1 = E.quality(res.final_gray)
    assert q1["overall"] > q0["overall"]
