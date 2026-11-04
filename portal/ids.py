"""Stable, ASCII-only names for generated towns."""
from __future__ import annotations

import re
import unicodedata

from .model import Place

MAX_MOD_ID = 60  # KnoxMap cuts mod ids to 60 characters
PREFIX = "portal_"


def slug(text: str) -> str:
    # "İ" decomposes to "I" + a dot above, so folding first keeps it an "i".
    folded = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", ascii_only.lower()).strip("_")


def place_key(place: Place) -> str:
    return slug(place.display_name)


def _name_and_region(place: Place) -> list[str]:
    parts = [p.strip() for p in place.display_name.split(",") if p.strip()]
    # Postcodes ("50400", "40004") sit before the country in some results.
    parts = parts[:1] + [p for p in parts[1:] if not any(c.isdigit() for c in p)]
    words = [parts[0] if parts else place.name]
    if len(parts) >= 3:
        words.append(parts[-2])  # the state or region, before the country
    return words


PRESET_LABELS = {"downtown": "Downtown", "town": "Town", "city_core": "City core"}


def title(place: Place, preset: str | None = None, mode: str = "standard") -> str:
    """'Bardstown, Kentucky (Town)': what players see, in the place's own spelling.

    KnoxMap names the mod and its map folder after this, so each size of a
    place needs its own: two mods with one map folder collide in the game.
    An accurate build is its own mod too, so it never replaces a standard one.
    """
    name = ", ".join(_name_and_region(place))
    if not preset:
        return name
    label = PRESET_LABELS[preset] + (", accurate" if mode == "accurate" else "")
    return f"{name} ({label})"


def mod_id(place: Place, preset: str, mode: str = "standard") -> str:
    words = _name_and_region(place)
    middle = "_".join(s for s in (slug(w) for w in words) if s) or "place"
    suffix = f"_{preset}" + ("_accurate" if mode == "accurate" else "")
    room = MAX_MOD_ID - len(PREFIX) - len(suffix)
    return PREFIX + middle[:room].rstrip("_") + suffix
