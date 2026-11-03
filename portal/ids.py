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
    words = [parts[0] if parts else place.name]
    if len(parts) >= 3:
        words.append(parts[-2])  # the state or region, before the country
    return words


def title(place: Place) -> str:
    """'Bardstown, Kentucky': what players see, in the place's own spelling."""
    return ", ".join(_name_and_region(place))


def mod_id(place: Place, preset: str) -> str:
    words = _name_and_region(place)
    middle = "_".join(s for s in (slug(w) for w in words) if s) or "place"
    suffix = f"_{preset}"
    room = MAX_MOD_ID - len(PREFIX) - len(suffix)
    return PREFIX + middle[:room].rstrip("_") + suffix
