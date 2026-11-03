"""Turn a place and a size preset into a concrete area and an estimate."""
from __future__ import annotations

import math

from .model import AreaPlan, Place

# Side of the square, in km, at 1 m a tile.
PRESETS: dict[str, float] = {"downtown": 1.0, "town": 3.0, "city_core": 5.0}

CELL_METERS = 256  # a Build 42 cell is 256 x 256 tiles

# Measured on Dean's PC, 2026-11-03: Bardstown downtown 25 cells in 3.2 min,
# Bardstown town 169 cells in 16.3 min. The OpenStreetMap download varies a lot
# by region (Urgup downtown spent 9 of its 11.5 min downloading).
MINUTES_PER_CELL = 0.1
BASE_MINUTES = 2


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance; plenty for 'is this address on the map'."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def plan(place: Place, preset: str) -> AreaPlan:
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}; choose one of {', '.join(PRESETS)}.")
    side_km = PRESETS[preset]
    # A square never lines up with the cell grid, so it overlaps one more
    # cell each way. An outline that clips the square only lowers this.
    per_side = math.ceil(side_km * 1000 / CELL_METERS) + 1
    cells = per_side ** 2
    return AreaPlan(place=place, preset=preset, side_km=side_km, cells=cells,
                    est_minutes=math.ceil(cells * MINUTES_PER_CELL) + BASE_MINUTES)
