from __future__ import annotations

from fastapi import APIRouter

from ... import DISCLAIMER, __version__
from ...config import get_settings
from ...security import PERMISSIONS, ROLE_LABELS

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("")
def meta() -> dict:
    s = get_settings()
    return {
        "app": "GeoRevive Africa",
        "version": __version__,
        "pilot_area": {"name": s.pilot_name, "bbox": list(s.bbox), "working_crs": s.working_crs},
        "disclaimer": DISCLAIMER,
        "roles": ROLE_LABELS,
        "permissions": {k: sorted(v) for k, v in PERMISSIONS.items()},
    }
