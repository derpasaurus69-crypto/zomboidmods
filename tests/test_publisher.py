from PIL import Image

from portal.model import Town
from portal.publisher import REMINDER, prepare

MOD = "portal_bardstown_kentucky_downtown"


def installed(tmp_path, preview=None, workshop_id=None):
    mod = tmp_path / "mods" / MOD
    (mod / "common" / "media" / "maps" / "Bardstown").mkdir(parents=True)
    (mod / "mod.info").write_text("id=" + MOD, encoding="utf-8")
    (mod / "ATTRIBUTION.txt").write_text("OSM", encoding="utf-8")
    (mod / ".portal.json").write_text("{}", encoding="utf-8")
    return Town(mod_id=MOD, title="Bardstown, Kentucky", place_key="bardstown_kentucky",
                preset="downtown", engine_version="1.8.4", mod_dir=str(mod),
                preview=preview, workshop_id=workshop_id, created="2026-11-03T10:00:00")


def lines(folder):
    return (folder / "workshop.txt").read_text(encoding="utf-8").splitlines()


def test_layout(tmp_path):
    out = prepare(installed(tmp_path), tmp_path / "Workshop")
    assert out == tmp_path / "Workshop" / MOD
    assert (out / "Contents" / "mods" / MOD / "mod.info").exists()
    assert (out / "Contents" / "mods" / MOD / "ATTRIBUTION.txt").exists()
    assert not (out / "Contents" / "mods" / MOD / ".portal.json").exists()
    with Image.open(out / "preview.png") as im:
        assert im.size == (256, 256)


def test_workshop_txt(tmp_path):
    ls = lines(prepare(installed(tmp_path), tmp_path / "Workshop"))
    assert ls[:2] == ["version=1", "title=Bardstown, Kentucky"]
    assert ls[-2:] == ["tags=Build 42;Map", "visibility=unlisted"]
    text = "\n".join(ls)
    assert "Map data © OpenStreetMap contributors, available under the ODbL" in text
    assert "https://www.openstreetmap.org/copyright" in text
    assert "KnoxMap by euclid80tr" in text and "Knoxify by arytek" in text
    assert "not affiliated with or endorsed by The Indie Stone" in text
    assert "buymeacoffee" not in text  # a player's own town carries no tip link
    assert all(ln.startswith(("version=", "title=", "description=", "tags=", "visibility="))
               for ln in ls)


def test_workshop_id_written_when_known(tmp_path):
    ls = lines(prepare(installed(tmp_path, workshop_id="3912345678"), tmp_path / "Workshop"))
    assert ls[1] == "id=3912345678"


def test_republish_keeps_the_id_and_description_from_the_last_upload(tmp_path):
    town = installed(tmp_path)
    folder = prepare(town, tmp_path / "Workshop")
    # After an upload the game writes the id back; the player may edit the text.
    (folder / "workshop.txt").write_text(
        "version=1\nid=3912345678\ntitle=Bardstown, Kentucky\ndescription=My own words.\n"
        "tags=Build 42;Map\nvisibility=public\n", encoding="utf-8")
    ls = lines(prepare(town, tmp_path / "Workshop"))
    assert ls[1] == "id=3912345678"
    assert [ln for ln in ls if ln.startswith("description=")] == ["description=My own words."]


def test_republish_replaces_contents(tmp_path):
    town = installed(tmp_path)
    out = prepare(town, tmp_path / "Workshop")
    stale = out / "Contents" / "mods" / MOD / "stale.lotpack"
    stale.write_text("x", encoding="utf-8")
    prepare(town, tmp_path / "Workshop")
    assert not stale.exists()


def test_preview_is_cropped_from_town_picture(tmp_path):
    pic = tmp_path / "pic.png"
    Image.new("RGB", (800, 400), "red").save(pic)
    out = prepare(installed(tmp_path, preview=str(pic)), tmp_path / "Workshop")
    with Image.open(out / "preview.png") as im:
        assert im.size == (256, 256) and im.getpixel((128, 128))[:3] == (255, 0, 0)


def test_reminder_text():
    assert REMINDER == ("This map shows a real place, including homes, schools and places of "
                        "worship. Publish it only if you are comfortable sharing that.")
