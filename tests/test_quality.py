import pytest

from portal import ids, planner, quality
from portal.model import Place


def place(display_name="Bardstown, Nelson County, Kentucky, 40004, United States"):
    return Place(name="Bardstown", display_name=display_name, lat=37.8, lon=-85.47,
                 bbox=(37.7, -85.5, 37.9, -85.4), kind="town", outline=None)


def test_standard_keeps_knoxmaps_defaults():
    assert quality.engine_settings("standard", place()) is None
    assert quality.engine_settings("standard", place(), fill_gaps=True) == {"fill_gaps": 1}


def test_accurate_uses_real_data_and_american_houses_in_the_us():
    s = quality.engine_settings("accurate", place())
    assert s["fill_gaps"] == 1 and s["fill_frontage"] == 0 and s["true_map"] == 1
    assert s["max_levels"] == 12 and s["straight_roads"] == 3
    assert s["apartment_footprint"] == 600 and s["apartment_chance"] == 0.1


def test_accurate_always_sends_building_alignment_with_straight_roads():
    # KnoxMap turns straight_roads>=1 without building_alignment into plain boxes.
    s = quality.engine_settings("accurate", place())
    assert s["building_alignment"] == "rectilinear"


def test_building_style_from_the_country_or_chosen():
    turkey = place("Ürgüp, Nevşehir, İç Anadolu Bölgesi, 50400, Türkiye")
    assert quality.engine_settings("accurate", turkey)["apartment_chance"] == 0.55
    assert quality.engine_settings("accurate", turkey, style="american")["apartment_chance"] == 0.1
    assert quality.engine_settings("accurate", place(), style="european")["apartment_footprint"] == 150


def test_unknown_mode_or_style_is_refused():
    with pytest.raises(ValueError):
        quality.engine_settings("ultra", place())
    with pytest.raises(ValueError):
        quality.engine_settings("accurate", place(), style="martian")


def test_accurate_plan_takes_longer_and_always_fills_gaps():
    standard = planner.plan(place(), "town")
    accurate = planner.plan(place(), "town", mode="accurate")
    assert standard.est_minutes == 19 and standard.settings is None and not standard.fill_gaps
    # 169 cells: 29 min as before plus about half a minute a cell routing real roads
    assert accurate.est_minutes == 29 + 84 and accurate.fill_gaps and accurate.settings["max_levels"] == 12


def test_accurate_can_keep_standard_roads_to_save_time():
    quick = planner.plan(place(), "town", mode="accurate", true_roads=False)
    assert quick.settings["straight_roads"] == 1 and quick.settings["building_alignment"] == "rectilinear"
    assert quick.est_minutes == 29


def test_an_accurate_build_is_its_own_mod():
    p = place()
    assert ids.mod_id(p, "town") == "portal_bardstown_kentucky_town"
    assert ids.mod_id(p, "town", "accurate") == "portal_bardstown_kentucky_town_accurate"
    assert ids.title(p, "town", "accurate") == "Bardstown, Kentucky (Town, accurate)"
