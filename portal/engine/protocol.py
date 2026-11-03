"""What Portal and its KnoxMap runner say to each other: one JSON object a line.

Standard library only: the runner imports this from inside KnoxMap's venv.
"""
from __future__ import annotations

import json

# Share of the whole job each KnoxMap step stands for, in the order they run.
STEP_RANGES: dict[str, tuple[float, float]] = {
    "generate": (0, 15),
    "buildings": (15, 45),
    "compile": (45, 90),
    "pictures": (90, 95),
    "package": (95, 100),
}


def overall_pct(step: str, fraction: float) -> float:
    lo, hi = STEP_RANGES[step]
    return lo + (hi - lo) * min(1.0, max(0.0, fraction))


def encode(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False)


def decode(line: str) -> dict | None:
    """An event, or None for anything else KnoxMap printed."""
    try:
        value = json.loads(line)
    except ValueError:
        return None
    return value if isinstance(value, dict) and "event" in value else None
