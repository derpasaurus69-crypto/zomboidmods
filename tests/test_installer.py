import json

import pytest

from portal.installer import MARKER, ForeignModError, install, staging_dir

MOD = "portal_bardstown_kentucky_downtown"


def staged(mods, files=("mod.info", "ATTRIBUTION.txt")):
    d = staging_dir(mods) / MOD
    d.mkdir(parents=True)
    for f in files:
        (d / f).write_text(f, encoding="utf-8")
    return d


def test_staging_is_inside_mods(tmp_path):
    assert staging_dir(tmp_path) == tmp_path / ".portal-staging"


def test_install_moves_staged_and_writes_marker(tmp_path):
    src = staged(tmp_path)
    out = install(src, tmp_path)
    assert out == tmp_path / MOD
    assert (out / "mod.info").exists() and not src.exists()
    assert json.loads((out / MARKER).read_text(encoding="utf-8"))["mod_id"] == MOD


def test_reinstall_replaces_portal_mod(tmp_path):
    install(staged(tmp_path, ("mod.info", "ATTRIBUTION.txt", "old.lotpack")), tmp_path)
    out = install(staged(tmp_path), tmp_path)
    assert not (out / "old.lotpack").exists()
    assert (out / "mod.info").exists()
    assert not (tmp_path / (MOD + ".old")).exists()


def test_refuses_foreign_mod(tmp_path):
    foreign = tmp_path / MOD
    foreign.mkdir()
    (foreign / "theirs.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(ForeignModError):
        install(staged(tmp_path), tmp_path)
    assert (foreign / "theirs.txt").read_text(encoding="utf-8") == "keep me"


def test_requires_attribution(tmp_path):
    with pytest.raises(ValueError):
        install(staged(tmp_path, ("mod.info",)), tmp_path)
