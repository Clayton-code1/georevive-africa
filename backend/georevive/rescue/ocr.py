"""OCR with word bounding boxes. Tesseract (if installed) or RapidOCR (pip-only fallback)."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np


@dataclass
class Word:
    text: str
    conf: float  # 0-1
    x: int
    y: int
    w: int
    h: int
    line: int


def tesseract_cmd() -> str | None:
    env = os.environ.get("TESSERACT_CMD")
    if env and Path(env).exists():
        return env
    found = shutil.which("tesseract")
    if found:
        return found
    for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if Path(p).exists():
            return p
    return None


@lru_cache(maxsize=1)
def available_engines() -> tuple[str, ...]:
    out = []
    if tesseract_cmd():
        out.append("tesseract")
    try:
        import rapidocr_onnxruntime  # noqa: F401

        out.append("rapidocr")
    except Exception:
        pass
    return tuple(out)


def choose_engine(preference: str = "auto") -> str:
    eng = available_engines()
    if preference in eng:
        return preference
    if preference not in ("auto", "") and preference not in eng:
        raise RuntimeError(f"OCR engine '{preference}' is not available (installed: {list(eng) or 'none'})")
    if not eng:
        raise RuntimeError(
            "No OCR engine available. Install Tesseract (see README) or `pip install rapidocr-onnxruntime`."
        )
    return eng[0]


def ocr_tesseract(img: np.ndarray, psm: int = 3) -> list[Word]:
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
    d = pytesseract.image_to_data(img, lang="eng", config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    words = []
    line_ids: dict[tuple, int] = {}
    for i, t in enumerate(d["text"]):
        t = (t or "").strip()
        conf = float(d["conf"][i])
        if not t or conf < 0:
            continue
        key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        line = line_ids.setdefault(key, len(line_ids))
        words.append(
            Word(t, conf / 100.0, int(d["left"][i]), int(d["top"][i]), int(d["width"][i]), int(d["height"][i]), line)
        )
    return words


@lru_cache(maxsize=1)
def _rapid():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def ocr_rapid(img: np.ndarray) -> list[Word]:
    """RapidOCR returns text lines with quadrilateral boxes. Split each line into words and give
    each word a proportional share of the line box (by character count)."""
    result, _ = _rapid()(img)
    words: list[Word] = []
    if not result:
        return words
    # sort lines top-to-bottom, then left-to-right
    rows = []
    for box, text, score in result:
        pts = np.array(box, dtype=np.float32)
        x0, y0 = pts[:, 0].min(), pts[:, 1].min()
        x1, y1 = pts[:, 0].max(), pts[:, 1].max()
        rows.append((y0, x0, x1, y1, text, float(score)))
    rows.sort(key=lambda r: (round(r[0] / 12), r[1]))
    for li, (y0, x0, x1, y1, text, score) in enumerate(rows):
        toks = text.split()
        if not toks:
            continue
        total = sum(len(t) for t in toks) + (len(toks) - 1)
        cx = x0
        width = x1 - x0
        for t in toks:
            tw = width * len(t) / max(total, 1)
            words.append(Word(t, score, int(cx), int(y0), max(1, int(tw)), max(1, int(y1 - y0)), li))
            cx += tw + width / max(total, 1)
    return words


def run_ocr(gray: np.ndarray, binary: np.ndarray | None, engine: str) -> list[Word]:
    if engine == "tesseract":
        return ocr_tesseract(binary if binary is not None else gray)
    if engine == "rapidocr":
        return ocr_rapid(gray)
    raise ValueError(engine)


def words_to_text(words: list[Word]) -> str:
    lines: dict[int, list[str]] = {}
    for w in words:
        lines.setdefault(w.line, []).append(w.text)
    return "\n".join(" ".join(v) for _, v in sorted(lines.items()))
