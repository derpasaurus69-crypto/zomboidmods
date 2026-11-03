import re

from portal.ids import mod_id, place_key, slug, title
from portal.model import Place


def test_slug_ascii_folds_and_joins():
    assert slug("Ürgüp") == "urgup"
    assert slug("St. Louis  Park") == "st_louis_park"
    assert slug("Zürich") == "zurich"


def test_mod_id_uses_first_and_region_parts():
    p = Place("Bardstown", "Bardstown, Nelson County, Kentucky, United States",
              37.8, -85.4, (0, 0, 0, 0), "town", None)
    assert mod_id(p, "downtown") == "portal_bardstown_kentucky_downtown"


def test_mod_id_short_display_name():
    p = Place("Monaco", "Monaco", 43.7, 7.4, (0, 0, 0, 0), "country", None)
    assert mod_id(p, "town") == "portal_monaco_town"


def test_mod_id_max_60_and_charset():
    p = Place("x" * 80, ("x" * 80) + ", Y, Z", 0, 0, (0, 0, 0, 0), "", None)
    m = mod_id(p, "city_core")
    assert len(m) <= 60
    assert re.fullmatch(r"[a-z0-9_]+", m)
    assert m.startswith("portal_") and m.endswith("_city_core")


def test_non_ascii_place_gives_ascii_id():
    p = Place("Ürgüp", "Ürgüp, Nevşehir, İç Anadolu Bölgesi, Türkiye",
              38.6, 34.9, (0, 0, 0, 0), "town", None)
    assert mod_id(p, "town") == "portal_urgup_ic_anadolu_bolgesi_town"


def test_postcode_is_not_the_region():
    p = Place("Ürgüp", "Ürgüp, Nevşehir, Central Anatolia Region, 50400, Turkey",
              38.6, 34.9, (0, 0, 0, 0), "administrative", None)
    assert mod_id(p, "downtown") == "portal_urgup_central_anatolia_region_downtown"
    assert title(p) == "Ürgüp, Central Anatolia Region"


def test_us_zip_is_not_the_region():
    p = Place("Bardstown", "Bardstown, Nelson County, Kentucky, 40004, United States",
              37.8, -85.4, (0, 0, 0, 0), "town", None)
    assert title(p) == "Bardstown, Kentucky"


def test_place_key_is_slug_of_display_name():
    p = Place("Monaco", "Monaco", 43.7, 7.4, (0, 0, 0, 0), "country", None)
    assert place_key(p) == "monaco"


def test_place_from_knoxmap():
    d = {"name": "Bardstown", "display_name": "Bardstown, Kentucky",
         "lat": 37.8, "lon": -85.4, "bbox": [37.7, -85.5, 37.9, -85.3],
         "category": "boundary", "type": "administrative", "outline": None}
    p = Place.from_knoxmap(d)
    assert p.bbox == (37.7, -85.5, 37.9, -85.3)
    assert p.kind == "administrative"
