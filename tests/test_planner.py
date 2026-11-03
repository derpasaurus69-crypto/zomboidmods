import math

import pytest

from portal.model import Place
from portal.planner import BASE_MINUTES, MINUTES_PER_CELL, PRESETS, plan

BARDSTOWN = Place("Bardstown", "Bardstown, Nelson County, Kentucky, United States",
                  37.8092, -85.4669, (37.78, -85.50, 37.84, -85.43), "town", None)


def test_presets():
    assert PRESETS == {"downtown": 1.0, "town": 3.0, "city_core": 5.0}


def test_downtown_is_25_cells():
    # 1 km never lines up with the 256 m grid: it overlaps one extra row and column
    assert plan(BARDSTOWN, "downtown").cells == 25


def test_town_is_169_cells_without_outline():
    assert plan(BARDSTOWN, "town").cells == 169


def test_city_core_is_441_cells():
    assert plan(BARDSTOWN, "city_core").cells == 441


def test_estimate_minutes():
    a = plan(BARDSTOWN, "downtown")
    assert a.est_minutes == math.ceil(25 * MINUTES_PER_CELL) + BASE_MINUTES


def test_plan_carries_place_and_side():
    a = plan(BARDSTOWN, "town")
    assert a.place is BARDSTOWN and a.preset == "town" and a.side_km == 3.0


def test_unknown_preset_raises():
    with pytest.raises(ValueError):
        plan(BARDSTOWN, "galaxy")
