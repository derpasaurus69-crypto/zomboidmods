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

# Accurate spends more time downloading footprints and routing roads.
TIME_FACTOR = {"standard": 1.0, "accurate": 1.5}


def style_for(place: Place, style: str = "auto") -> str:
    if style in BUILDING_STYLE:
        return style
    country = place.display_name.rsplit(",", 1)[-1].strip().lower()
    return "american" if country in AMERICAN_COUNTRIES else "european"


def engine_settings(mode: str, place: Place, style: str = "auto", fill_gaps: bool = False) -> dict | None:
    """The settings dict for /api/generate, or None to keep KnoxMap's defaults."""
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode!r}; choose one of {', '.join(MODES)}.")
    if style not in STYLES:
        raise ValueError(f"Unknown building style {style!r}; choose one of {', '.join(STYLES)}.")
    if mode == "accurate":
        return {**ACCURATE, **BUILDING_STYLE[style_for(place, style)]}
    return {"fill_gaps": 1} if fill_gaps else None
