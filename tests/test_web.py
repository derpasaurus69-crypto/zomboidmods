import json
import sys
import time
from pathlib import Path

import pytest

from portal.engine.adapter import EngineAdapter
from portal.library import TownLibrary
from portal.publisher import REMINDER
from portal.web import create_app

FAKE = Path(__file__).parent / "fake_engine.py"
PLACE = {"name": "Bardstown", "display_name": "Bardstown, Kentucky, United States",
         "lat": 37.8, "lon": -85.4, "bbox": [37.7, -85.5, 37.9, -85.3], "kind": "town",
         "outline": None}
LOCAL = {"Host": "127.0.0.1:8765"}


@pytest.fixture
def env(tmp_path, monkeypatch):
    def make(mode="ok"):
        monkeypatch.setenv("FAKE_MODE", mode)
        knox = tmp_path / "knoxmap"
        (knox / ".venv" / "Scripts").mkdir(parents=True, exist_ok=True)
        adapter = EngineAdapter(knox, python=Path(sys.executable), runner=FAKE)
        launched = []
        app = create_app(adapter, TownLibrary(tmp_path / "library.json"), tmp_path / "mods",
                         tmp_path / "Workshop", launcher=lambda: launched.append(True),
                         settings_path=tmp_path / "settings.json")
        return app.test_client(), app, launched
    return make


def get(c, path):
    return c.get(path, headers=LOCAL)


def post(c, path, body):
    return c.post(path, json=body, headers=LOCAL)


def wait_done(c):
    for _ in range(300):
        s = get(c, "/api/job").get_json()
        if s["state"] != "running":
            return s
        time.sleep(0.05)
    raise AssertionError("job never finished")


def test_page_serves(env):
    c, _, _ = env()
    r = get(c, "/")
    assert r.status_code == 200 and b"Generate &amp; Play" in r.data


def test_knoxmap_folder_can_be_set_from_the_page(env, tmp_path):
    c, app, _ = env()
    knox = tmp_path / "Downloads" / "knoxmap-main"
    (knox / ".venv" / "Scripts").mkdir(parents=True)
    (knox / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
    (knox / "app.py").write_text("")
    r = post(c, "/api/settings", {"knoxmap_dir": f'"{knox}"'})  # pasted with quotes
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert json.loads((tmp_path / "settings.json").read_text())["knoxmap_dir"] == str(knox)


def test_a_folder_that_is_not_knoxmap_is_refused(env, tmp_path):
    c, _, _ = env()
    r = post(c, "/api/settings", {"knoxmap_dir": str(tmp_path)})
    assert r.status_code == 400 and "not a KnoxMap folder" in r.get_json()["error"]
    assert not (tmp_path / "settings.json").exists()


def test_licences_page_has_portals_and_bundled_licences(env):
    c, _, _ = env()
    text = get(c, "/licences").data.decode()
    assert "MIT License" in text and "Copyright (c) 2026 Dean Amato" in text
    assert "## Flask" in text and "## pillow" in text


def test_about_credits_and_tip_link(env):
    c, _, _ = env()
    page = get(c, "/").data.decode()
    assert "Portal 0.1.0" in page
    assert "https://buymeacoffee.com/derpasauruo" in page
    assert "euclid80tr" in page and "arytek" in page
    assert "https://www.openstreetmap.org/copyright" in page
    assert "not affiliated with or endorsed" in page


def test_search_no_results(env):
    c, _, _ = env("noresults")
    r = get(c, "/api/search?q=Nowhereville")
    assert r.status_code == 200 and r.get_json() == {"results": []}


def test_search_failure_is_502_with_message(env):
    c, _, _ = env("fail")
    r = get(c, "/api/search?q=Bardstown")
    assert r.status_code == 502 and "no network" in r.get_json()["error"]


def test_engine_problem_reported(env):
    c, _, _ = env("old")
    e = get(c, "/api/engine").get_json()
    assert e["ok"] is False and "1.8.4" in e["problem"]


def test_generate_installs_and_lists_town(env, tmp_path):
    c, _, _ = env()
    r = post(c, "/api/generate", {"place": PLACE, "preset": "downtown"})
    assert r.status_code == 200
    mod = r.get_json()["mod_id"]
    assert mod == "portal_bardstown_kentucky_downtown"
    assert wait_done(c)["state"] == "done"
    assert (tmp_path / "mods" / mod / "mod.info").exists()
    towns = get(c, "/api/towns").get_json()["towns"]
    assert [t["mod_id"] for t in towns] == [mod]
    assert towns[0]["title"] == "Bardstown, Kentucky (Downtown)"


def test_engine_is_given_a_title_with_the_size(env, tmp_path):
    c, _, _ = env()
    plan = post(c, "/api/plan", {"place": PLACE, "preset": "town"}).get_json()
    assert plan["title"] == "Bardstown, Kentucky (Town)"
    post(c, "/api/generate", {"place": PLACE, "preset": "town"})
    wait_done(c)
    info = tmp_path / "mods" / "portal_bardstown_kentucky_town" / "mod.info"
    assert "name=Bardstown, Kentucky (Town)" in info.read_text(encoding="utf-8")


def test_generate_passes_a_spawn_address_to_the_engine(env, tmp_path):
    c, _, _ = env()
    r = post(c, "/api/generate", {"place": PLACE, "preset": "downtown",
                                  "spawn_address": "12 Example Road"})
    assert r.status_code == 200
    assert wait_done(c)["state"] == "done"
    plan = json.loads((tmp_path / "mods" / r.get_json()["mod_id"] / "plan.json").read_text())
    assert plan["spawn"] == {"lat": 37.802, "lon": -85.401,
                             "label": "12, Example Road, Bardstown"}


def test_generate_without_an_address_spawns_near_the_centre(env, tmp_path):
    c, _, _ = env()
    mod = post(c, "/api/generate", {"place": PLACE, "preset": "downtown", "spawn_address": "  "}
               ).get_json()["mod_id"]
    wait_done(c)
    plan = json.loads((tmp_path / "mods" / mod / "plan.json").read_text())
    assert plan["spawn"] is None and plan["fill_gaps"] is False


def test_fill_gaps_is_passed_to_the_engine(env, tmp_path):
    c, _, _ = env()
    mod = post(c, "/api/generate", {"place": PLACE, "preset": "downtown", "fill_gaps": True}
               ).get_json()["mod_id"]
    wait_done(c)
    assert json.loads((tmp_path / "mods" / mod / "plan.json").read_text())["fill_gaps"] is True


def test_spawn_address_off_the_map_is_refused_before_anything_starts(env):
    c, _, _ = env()
    r = post(c, "/api/generate", {"place": PLACE, "preset": "downtown", "spawn_address": "1 Far Street"})
    assert r.status_code == 400 and "outside the downtown area" in r.get_json()["error"]
    assert get(c, "/api/job").get_json()["state"] == "idle"


def test_spawn_address_not_found(env):
    c, _, _ = env("noresults")
    r = post(c, "/api/generate", {"place": PLACE, "preset": "downtown", "spawn_address": "Nowhere 1"})
    assert r.status_code == 400 and "Could not find" in r.get_json()["error"]


def test_generate_leaves_staging_empty_and_keeps_preview(env, tmp_path):
    c, _, _ = env()
    post(c, "/api/generate", {"place": PLACE, "preset": "downtown"})
    wait_done(c)
    [town] = get(c, "/api/towns").get_json()["towns"]
    assert Path(town["preview"]).parent == tmp_path / "previews"
    assert Path(town["preview"]).exists()
    assert list((tmp_path / "mods" / ".portal-staging").iterdir()) == []
    assert (tmp_path / "logs" / "portal_bardstown_kentucky_downtown.engine.log").exists()


def test_plan_reports_existing_town(env):
    c, _, _ = env()
    post(c, "/api/generate", {"place": PLACE, "preset": "downtown"})
    wait_done(c)
    r = post(c, "/api/plan", {"place": PLACE, "preset": "downtown"}).get_json()
    assert r["existing"] is True and r["plan"]["cells"] == 25


def test_second_generate_while_running_is_409(env, tmp_path, monkeypatch):
    c, _, _ = env("hang")
    monkeypatch.setenv("FAKE_CHILD_PID_FILE", str(tmp_path / "child.pid"))
    assert post(c, "/api/generate", {"place": PLACE, "preset": "downtown"}).status_code == 200
    assert post(c, "/api/generate", {"place": PLACE, "preset": "town"}).status_code == 409
    post(c, "/api/cancel", {})
    assert wait_done(c)["state"] == "cancelled"


def test_impossible_size_is_400_and_names_smaller(env):
    c, _, _ = env("impossible")
    r = post(c, "/api/generate", {"place": PLACE, "preset": "town"})
    assert r.status_code == 400
    assert "Too big for this PC" in r.get_json()["error"] and "downtown" in r.get_json()["error"]


def test_foreign_host_refused(env):
    c, _, _ = env()
    assert c.get("/api/towns", headers={"Host": "evil.example"}).status_code == 403


def test_publish(env, tmp_path):
    c, _, _ = env()
    post(c, "/api/generate", {"place": PLACE, "preset": "downtown"})
    wait_done(c)
    r = post(c, "/api/publish", {"mod_id": "portal_bardstown_kentucky_downtown"}).get_json()
    assert Path(r["folder"]).is_dir() and r["reminder"] == REMINDER


def test_launch(env):
    c, _, launched = env()
    assert post(c, "/api/launch", {}).status_code == 200 and launched == [True]
