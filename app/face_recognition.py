"""Haversine distance and face-verify stub."""

import math
from typing import Optional, Tuple


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def verify_face_stub(image_bytes: Optional[bytes]) -> Tuple[bool, str]:
    """Placeholder for OpenCV / deep model integration; always succeeds in demo."""
    if image_bytes is None or len(image_bytes) < 10:
        return False, "empty_image"
    return True, "demo_match"
