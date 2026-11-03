import json

from portal import settings


def knoxmap(folder):
    (folder / ".venv" / "Scripts").mkdir(parents=True)
    (folder / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
    (folder / "app.py").write_text("")
    return folder


def test_finds_a_downloaded_or_nested_knoxmap(tmp_path):
    assert settings.find_knoxmap([tmp_path]) is None
    nested = knoxmap(tmp_path / "pz-tools" / "knoxmap")
    assert settings.find_knoxmap([tmp_path]) == str(nested)
    unzipped = knoxmap(tmp_path / "KnoxMap-main")
    assert settings.find_knoxmap([tmp_path]) == str(unzipped)


def test_knoxmap_without_setup_does_not_count(tmp_path):
    (tmp_path / "knoxmap").mkdir()
    (tmp_path / "knoxmap" / "app.py").write_text("")
    assert settings.find_knoxmap([tmp_path]) is None
    assert settings.find_knoxmap([tmp_path / "missing"]) is None


def test_saved_folder_wins_and_unknown_keys_are_dropped(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"knoxmap_dir": "X:\\knox", "junk": 1}))
    values = settings.load(path)
    assert values["knoxmap_dir"] == "X:\\knox" and "junk" not in values
