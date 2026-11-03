import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from portal.engine.adapter import EngineAdapter, EngineCancelled, EngineError
from portal.model import Place
from portal.planner import plan

FAKE = Path(__file__).parent / "fake_engine.py"
PLACE = Place("Bardstown", "Bardstown, Kentucky, United States", 37.8, -85.4,
              (37.7, -85.5, 37.9, -85.3), "town", None)


def adapter(tmp_path, mode, monkeypatch, **kw):
    monkeypatch.setenv("FAKE_MODE", mode)
    knox = tmp_path / "knoxmap"
    (knox / ".venv" / "Scripts").mkdir(parents=True)
    return EngineAdapter(knox, python=Path(sys.executable), runner=FAKE, **kw)


def run(a, tmp_path, cancel=None):
    gen = a.generate(plan(PLACE, "downtown"), "portal_x_downtown", tmp_path / "staging",
                     "X", cancel or threading.Event())
    return list(gen)


def pid_alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True).stdout
    return str(pid) in out


def test_ok_generate(tmp_path, monkeypatch):
    a = adapter(tmp_path, "ok", monkeypatch)
    steps = run(a, tmp_path)
    assert steps[-1].pct == 100
    assert Path(a.last_result["mod_dir"]).name == "portal_x_downtown"


def test_fail_raises_engine_message(tmp_path, monkeypatch):
    a = adapter(tmp_path, "fail", monkeypatch)
    with pytest.raises(EngineError, match="cell 3_4"):
        run(a, tmp_path)


def test_noise_lines_ignored(tmp_path, monkeypatch):
    a = adapter(tmp_path, "noise", monkeypatch)
    assert [p.step for p in run(a, tmp_path)] == ["generate", "buildings", "compile", "package"]


def test_check_ok(tmp_path, monkeypatch):
    s = adapter(tmp_path, "ok", monkeypatch).check()
    assert s.ok and s.version == "1.8.4"


def test_check_old_version(tmp_path, monkeypatch):
    s = adapter(tmp_path, "old", monkeypatch).check()
    assert not s.ok and "1.8.4" in s.problem and "1.7.0" in s.problem


def test_check_build41(tmp_path, monkeypatch):
    s = adapter(tmp_path, "b41", monkeypatch).check()
    assert not s.ok and "Build 42" in s.problem


def test_a_later_release_in_the_tested_series_is_accepted(tmp_path, monkeypatch):
    s = adapter(tmp_path, "newer", monkeypatch).check()
    assert s.ok and s.version == "1.8.9"


def test_generate_refused_on_untested_engine(tmp_path, monkeypatch):
    with pytest.raises(EngineError, match="1.8.4"):
        run(adapter(tmp_path, "old", monkeypatch), tmp_path)


def test_untested_engine_allowed_by_setting(tmp_path, monkeypatch):
    assert run(adapter(tmp_path, "old", monkeypatch, allow_untested=True), tmp_path)[-1].pct == 100


def test_search_no_results(tmp_path, monkeypatch):
    assert adapter(tmp_path, "noresults", monkeypatch).search("Nowhereville") == []


def test_search_returns_places(tmp_path, monkeypatch):
    [p] = adapter(tmp_path, "ok", monkeypatch).search("Bardstown")
    assert p.name == "Bardstown" and p.bbox == (37.7, -85.5, 37.9, -85.3)


def test_search_failure_raises(tmp_path, monkeypatch):
    with pytest.raises(EngineError, match="no network"):
        adapter(tmp_path, "fail", monkeypatch).search("Bardstown")


def test_missing_knoxmap(tmp_path):
    s = EngineAdapter(tmp_path / "nothing-here").check()
    assert not s.ok and "KnoxMap" in s.problem


def test_cancel_kills_process_tree(tmp_path, monkeypatch):
    pid_file = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_CHILD_PID_FILE", str(pid_file))
    a = adapter(tmp_path, "hang", monkeypatch)
    cancel = threading.Event()
    (tmp_path / "staging" / "portal_x_downtown").mkdir(parents=True)

    def cancel_when_child_runs():
        while not pid_file.exists():
            time.sleep(0.1)
        time.sleep(0.3)
        cancel.set()

    threading.Thread(target=cancel_when_child_runs, daemon=True).start()
    started = time.time()
    with pytest.raises(EngineCancelled):
        run(a, tmp_path, cancel)
    assert time.time() - started < 15
    time.sleep(0.5)
    assert not pid_alive(int(pid_file.read_text()))
    assert not (tmp_path / "staging" / "portal_x_downtown").exists()
