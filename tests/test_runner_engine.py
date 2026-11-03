"""The runner against the real KnoxMap: slow, needs PZ installed and network."""
import json
import os
import subprocess
from pathlib import Path

import pytest

KNOXMAP = Path(os.environ.get("KNOXMAP_DIR", r"D:\modding\pz-portal-engine\knoxmap"))
RUNNER = Path(__file__).resolve().parent.parent / "portal" / "engine" / "runner.py"

pytestmark = pytest.mark.engine


def run(command, args, tmp_path):
    env = {**os.environ, "PYTHONUTF8": "1", "KNOXMAP_DIR": str(KNOXMAP)}
    p = subprocess.run([str(KNOXMAP / ".venv" / "Scripts" / "python.exe"), "-u", str(RUNNER),
                        command, json.dumps(args)], capture_output=True, text=True,
                       encoding="utf-8", env=env, timeout=1800)
    (tmp_path / f"{command}.stderr.txt").write_text(p.stderr, encoding="utf-8")
    events = [json.loads(line) for line in p.stdout.splitlines() if line.startswith("{")]
    return p.returncode, events


def test_generate_one_cell(tmp_path):
    place = {"name": "Bardstown", "display_name": "Bardstown, Nelson County, Kentucky, United States",
             "lat": 37.8092, "lon": -85.4669, "bbox": [37.78, -85.50, 37.84, -85.43],
             "kind": "town", "outline": None}
    plan = {"place": place, "preset": "downtown", "side_km": 0.25, "cells": 4, "est_minutes": 2}
    code, events = run("generate", {"plan": plan, "map_name": "portal_enginetest_downtown",
                                    "staging_dir": str(tmp_path / "staging"),
                                    "title": "Portal engine test"}, tmp_path)
    assert code == 0, events[-1:]
    pcts = [e["pct"] for e in events if e["event"] == "progress"]
    assert pcts == sorted(pcts) and pcts[-1] == 100
    mod = Path(events[-1]["mod_dir"])
    assert (mod / "mod.info").exists() or (mod / "42" / "mod.info").exists()
    assert (mod / "ATTRIBUTION.txt").exists()
    names = {p.name for p in mod.rglob("*")}
    assert {"map.info", "spawnpoints.lua"} <= names
    assert any(n.endswith(".lotheader") for n in names)
    assert any(n.endswith(".lotpack") for n in names)
