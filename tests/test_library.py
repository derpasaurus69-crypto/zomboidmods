from portal.library import TownLibrary
from portal.model import Town


def town(mod_id="portal_bardstown_kentucky_downtown", created="2026-11-03T10:00:00", **kw):
    base = dict(mod_id=mod_id, title="Bardstown, Kentucky", place_key="bardstown_kentucky",
                preset="downtown", engine_version="1.8.4", mod_dir="C:/mods/x",
                preview=None, workshop_id=None, created=created)
    base.update(kw)
    return Town(**base)


def test_put_get_round_trip(tmp_path):
    lib = TownLibrary(tmp_path / "library.json")
    t = town(preview="C:/p.png")
    lib.put(t)
    assert TownLibrary(tmp_path / "library.json").get(t.mod_id) == t


def test_put_same_id_keeps_newer(tmp_path):
    lib = TownLibrary(tmp_path / "library.json")
    lib.put(town(title="old"))
    lib.put(town(title="new", created="2026-11-03T11:00:00"))
    assert [t.title for t in lib.list()] == ["new"]


def test_list_newest_first(tmp_path):
    lib = TownLibrary(tmp_path / "library.json")
    lib.put(town("a", created="2026-11-01T00:00:00"))
    lib.put(town("b", created="2026-11-03T00:00:00"))
    lib.put(town("c", created="2026-11-02T00:00:00"))
    assert [t.mod_id for t in lib.list()] == ["b", "c", "a"]


def test_set_workshop_id_persists(tmp_path):
    TownLibrary(tmp_path / "library.json").put(town())
    TownLibrary(tmp_path / "library.json").set_workshop_id(town().mod_id, "3912345678")
    assert TownLibrary(tmp_path / "library.json").get(town().mod_id).workshop_id == "3912345678"


def test_missing_index_is_empty(tmp_path):
    assert TownLibrary(tmp_path / "nope" / "library.json").list() == []


def test_corrupt_index_is_set_aside(tmp_path):
    p = tmp_path / "library.json"
    p.write_text("{not json", encoding="utf-8")
    assert TownLibrary(p).list() == []
    assert (tmp_path / "library.json.bad").exists()
