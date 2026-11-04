"""Standard or Accurate generation: which KnoxMap settings Portal sends.

Standard leaves KnoxMap's defaults alone (plus fill_gaps when asked). Accurate
uses real data wherever KnoxMap has it and stops inventing what it would
otherwise guess. Reasons and line references: docs/accurate-mode.md.
"""
from __future__ import annotations

from .model import Place

MODES = ("standard", "accurate")
STYLES = ("auto", "american", "european")

# Same as KnoxMap's own defaults except where the data can do better.
ACCURATE = {
    "fill_gaps": 1,          # real Microsoft/Overture footprints, with heights, where OSM has none
    "fill_frontage": 0,      # never invent buildings along streets
    "true_map": 1,           # every mapped building, none thinned out
    "min_size": 3,
    "max_size": 250,         # big landmarks whole more often instead of cut into units
    "max_levels": 12,        # don't cut surveyed heights at 6; 31 lets one bad reading tower
    "height_mix": "auto",
    "building_alignment": "rectilinear",  # true outline, squared to the grid; always sent,
    "straight_roads": 3,     # or KnoxMap turns straight_roads>=1 into "rectangle" boxes
    "align_streets": 1,
    "rotate_degrees": 0.0,
    "arch_style": "auto",
    "tree_density": 1.0,
    "forest_density": 1.0,
}

# KnoxMap's flats guess is tuned on European/Turkish town centres: at 1 m a
# tile a 150 m2 American house qualifies. 43% of Bardstown became 3-6 storey
# flats that way. These are KnoxMap's own "suburb" values for the guess only.
BUILDING_STYLE = {
    "american": {"apartment_footprint": 600, "apartment_chance": 0.1},
    "european": {"apartment_footprint": 150, "apartment_chance": 0.55},
}
AMERICAN_COUNTRIES = ("united states", "canada", "australia", "new zealand")

# Accurate spends more time downloading footprints and laying out buildings.
TIME_FACTOR = {"standard": 1.0, "accurate": 1.5}
# Routing every road along its real line (straight_roads 3) is the slow part:
# Bardstown town (169 cells) spent 84 of its 95 minutes on it, 2026-11-04.
TRUE_ROADS_MINUTES_PER_CELL = 0.5


def style_for(place: Place, style: str = "auto") -> str:
    if style in BUILDING_STYLE:
        return style
    country = place.display_name.rsplit(",", 1)[-1].strip().lower()
    return "american" if country in AMERICAN_COUNTRIES else "european"


def engine_settings(mode: str, place: Place, style: str = "auto", fill_gaps: bool = False,
                    true_roads: bool = True) -> dict | None:
    """The settings dict for /api/generate, or None to keep KnoxMap's defaults.

    true_roads=False keeps Standard's straightened roads (straight_roads 1)
    in an Accurate build, which saves most of its time.
    """
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode!r}; choose one of {', '.join(MODES)}.")
    if style not in STYLES:
        raise ValueError(f"Unknown building style {style!r}; choose one of {', '.join(STYLES)}.")
    if mode == "accurate":
        roads = {} if true_roads else {"straight_roads": 1}
        return {**ACCURATE, **BUILDING_STYLE[style_for(place, style)], **roads}
    return {"fill_gaps": 1} if fill_gaps else None


def extra_minutes(settings: dict | None, cells: int) -> int:
    return round(cells * TRUE_ROADS_MINUTES_PER_CELL) if settings and settings.get("straight_roads") == 3 else 0
