import math
import zipfile

from PIL import Image

from portal.engine import finish


def fake_mod(tmp_path):
    mod = tmp_path / "portal_x_town"
    for folder in ("", "common", "42"):
        (mod / folder).mkdir(parents=True, exist_ok=True)
        (mod / folder / "mod.info").write_text("name=X\r\nid=portal_x_town\r\ndescription=X\r\n")
    map_dir = mod / "common" / "media" / "maps" / "X"
    map_dir.mkdir(parents=True)
    (map_dir / "map.info").write_text("title=X\nlots=Muldraugh, KY\nfixed2x=true\n")
    with zipfile.ZipFile(map_dir / finish.PYRAMID, "w", zipfile.ZIP_STORED) as z:
        z.writestr("pyramid.txt", "VERSION=1\nbounds=21000 0 24300 3300\nimageSize=3300 3300\n"
                                  "minFilter=linear\nmagFilter=linear\n")
        z.writestr("0/tile0x0.png", b"png-bytes")
    return mod, map_dir


def test_poster_is_square_and_named_once_in_every_mod_info(tmp_path):
    mod, _ = fake_mod(tmp_path)
    preview = tmp_path / "preview.png"
    Image.new("RGB", (900, 600), (10, 20, 30)).save(preview)
    finish.add_poster(mod, str(preview), "X")
    finish.add_poster(mod, str(preview), "X")  # again: no duplicate lines
    for folder in ("common", "42"):
        assert Image.open(mod / folder / "poster.png").size == (512, 512)
    for info in (mod / "mod.info", mod / "common" / "mod.info", mod / "42" / "mod.info"):
        lines = info.read_text().splitlines()
        assert lines.count("poster=poster.png") == 1
        assert lines.count("category=map") == 1
        assert "id=portal_x_town" in lines


def test_poster_without_a_preview_is_a_plain_card(tmp_path):
    mod, _ = fake_mod(tmp_path)
    finish.add_poster(mod, None, "X")
    finish.add_poster(mod, str(tmp_path / "missing.png"), "X")
    assert Image.open(mod / "common" / "poster.png").size == (512, 512)


def pyramid_txt(map_dir):
    with zipfile.ZipFile(map_dir / finish.PYRAMID) as z:
        assert z.read("0/tile0x0.png") == b"png-bytes"
        assert all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist())
        return z.read("pyramid.txt").decode()


def test_spawn_picture_stays_at_the_towns_world_tiles_and_gets_a_zoom(tmp_path):
    _, map_dir = fake_mod(tmp_path)
    assert finish.frame_spawn_picture(map_dir, (21000, 0)) == (21000, 0, 24300, 3300)
    assert finish.frame_spawn_picture(map_dir, (21000, 0)) == (21000, 0, 24300, 3300)  # again
    txt = pyramid_txt(map_dir)
    assert "bounds=21000 0 24300 3300" in txt and "imageSize=3300 3300" in txt
    info = (map_dir / "map.info").read_text().splitlines()
    assert info.count("zoomX=22650") == 1 and info.count("zoomY=1650") == 1
    assert info.count("zoomS=13.6") == 1
    assert "lots=Muldraugh, KY" in info


def test_spawn_picture_moved_to_0_0_by_an_older_portal_is_put_back(tmp_path):
    _, map_dir = fake_mod(tmp_path)
    finish.frame_spawn_picture(map_dir, (0, 0))
    assert "bounds=0 0 3300 3300" in pyramid_txt(map_dir)
    finish.frame_spawn_picture(map_dir, (21000, 0))
    assert "bounds=21000 0 24300 3300" in pyramid_txt(map_dir)


def test_no_spawn_picture_is_left_alone(tmp_path):
    (tmp_path / "map.info").write_text("title=X\n")
    assert finish.frame_spawn_picture(tmp_path, (21000, 0)) is None
    assert (tmp_path / "map.info").read_text() == "title=X\n"


def test_spawn_picture_lua_registers_the_town_and_patches_once(tmp_path):
    mod, _ = fake_mod(tmp_path)
    path = finish.write_spawn_picture_lua(mod, "portal_x_town", 'Schuylkill Haven, "PA" Town',
                                          "X (Town)", (21000, 0, 23700, 3000))
    assert path == mod / "common" / "media" / "lua" / "client" / "Portal" / "portal_x_town_SpawnPicture.lua"
    lua = path.read_text()
    assert 'PortalSpawnPictures["Schuylkill Haven, \\"PA\\" Town"] = { maxX = 23700, maxY = 3000 }' in lua
    assert "MapSpawnSelect.portalPatched = true" in lua
    assert lua.count("{") == lua.count("}") and lua.count("(") == lua.count(")")
    assert "Events.OnGameBoot.Add(patch)" in lua


def test_spawns_are_near_the_centre_nearest_first_and_spaced():
    centre = (1650, 1650)
    homes = [(1650 + dx, 1650 + dy) for dx in range(-1500, 1501, 10) for dy in (-1500, 0, 1500)]
    picked = finish.pick_spawns(homes, centre)
    assert len(picked) == 8
    assert picked[0] == (1650, 1650)
    assert all(math.dist(p, centre) <= 400 for p in picked)
    assert all(math.dist(a, b) >= 25 for i, a in enumerate(picked) for b in picked[i + 1:])


def test_spawns_top_up_when_few_homes_are_central():
    homes = [(0, 0), (3000, 3000), (3100, 3000)]
    assert finish.pick_spawns(homes, (1650, 1650), count=2) == [(3000, 3000), (3100, 3000)]
    assert finish.pick_spawns([], (1650, 1650)) == []


def test_spawn_at_an_address_uses_the_house_floor_or_the_spot_itself():
    homes = [(100, 100), (500, 500)]
    assert finish.nearest_spot(homes, (110.4, 95.2)) == (100, 100)
    assert finish.nearest_spot(homes, (300.4, 300.6)) == (300, 301)
    assert finish.nearest_spot([], (7.4, 8.6)) == (7, 9)


def test_spawnpoints_file_has_knoxmaps_shape(tmp_path):
    path = tmp_path / "spawnpoints.lua"
    finish.write_spawnpoints(path, [(22650, 1650), (22700, 1600)])
    assert path.read_text() == (
        "function SpawnPoints()\n  return {\n    unemployed = {\n"
        "      { posX = 22650, posY = 1650, posZ = 0 },\n"
        "      { posX = 22700, posY = 1600, posZ = 0 }\n"
        "    }\n  }\nend\n")


def test_gap_filled_buildings_are_credited_once(tmp_path):
    from portal.model import EXTRA_BUILDING_CREDITS
    assert finish.EXTRA_CREDITS == EXTRA_BUILDING_CREDITS  # the runner cannot import portal.model
    mod, _ = fake_mod(tmp_path)
    (mod / "ATTRIBUTION.txt").write_text("Map data (c) OpenStreetMap contributors\n", encoding="utf-8")
    finish.credit_extra_buildings(mod, ["microsoft"])
    finish.credit_extra_buildings(mod, ["microsoft"])
    text = (mod / "ATTRIBUTION.txt").read_text(encoding="utf-8")
    assert text.startswith("Map data (c) OpenStreetMap contributors")
    assert text.count("Microsoft Global ML Building Footprints") == 1 and "ODbL" in text
