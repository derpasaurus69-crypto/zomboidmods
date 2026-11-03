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
    assert ls == ["version=1",
                  "title=Bardstown, Kentucky",
                  "description=Real-world map of Bardstown, Kentucky generated with Portal and KnoxMap.",
                  "description=Map data © OpenStreetMap contributors (ODbL).",
                  "tags=Build 42;Map",
                  "visibility=unlisted"]


def test_workshop_id_written_when_known(tmp_path):
    ls = lines(prepare(installed(tmp_path, workshop_id="3912345678"), tmp_path / "Workshop"))
    assert ls[1] == "id=3912345678"


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
