"""Portal's hands inside KnoxMap. Runs under KnoxMap's own venv Python:

    <knoxmap>/.venv/Scripts/python.exe -u runner.py <command> '<json args>'

Drives KnoxMap's Flask app in-process (test client: no server, no window) in
the order its own window does, and prints one JSON event per stdout line.
Everything KnoxMap prints itself goes to stderr, so stdout stays clean.

Commands: check, search, estimate, generate. See protocol.py for events.
"""
from __future__ import annotations

import contextlib
import json
import math
import os
import shutil
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from protocol import encode, overall_pct  # noqa: E402

KNOXMAP = Path(os.environ.get("KNOXMAP_DIR", r"D:\modding\pz-portal-engine\knoxmap"))
HOST = {"Host": "127.0.0.1"}  # KnoxMap refuses any other Host
ATTRIBUTION = "Map data (c) OpenStreetMap contributors, available under the ODbL.\n"

_out = sys.stdout


def emit(**event) -> None:
    _out.write(encode(event) + "\n")
    _out.flush()


def progress(step: str, fraction: float, message: str = "") -> None:
    emit(event="progress", step=step, pct=round(overall_pct(step, fraction), 1), message=message)


class Failed(Exception):
    pass


def knoxmap():
    os.chdir(KNOXMAP)
    sys.path.insert(0, str(KNOXMAP))
    with contextlib.redirect_stdout(sys.stderr):
        from app import app
    return app.test_client()


def call(client, method: str, path: str, body: dict | None = None) -> dict:
    with contextlib.redirect_stdout(sys.stderr):
        r = client.post(path, json=body or {}, headers=HOST) if method == "POST" \
            else client.get(path, headers=HOST)
    data = r.get_json(silent=True) or {}
    if r.status_code >= 400:
        raise Failed(data.get("error") or f"{path} answered {r.status_code}")
    return data


# ---- commands ---------------------------------------------------------------

def cmd_check(_args: dict) -> dict:
    sys.path.insert(0, str(KNOXMAP))
    import knoxlog
    import knoxpaths
    game = knoxpaths.pz_install_dir()
    return {"version": knoxlog.version(), "game": str(game) if game else None,
            "build42": bool(game and knoxpaths.is_build42(game))}


def cmd_search(args: dict) -> dict:
    client = knoxmap()
    from urllib.parse import quote
    return {"results": call(client, "GET", f"/api/search?q={quote(args['q'])}").get("results", [])}


def _square(lat: float, lon: float, side_km: float) -> dict:
    half_lat = (side_km / 2) / 111.32
    half_lon = (side_km / 2) / (111.32 * math.cos(math.radians(lat)))
    return {"south": lat - half_lat, "north": lat + half_lat,
            "west": lon - half_lon, "east": lon + half_lon}


def area_body(plan: dict) -> dict:
    place = plan["place"]
    box = _square(place["lat"], place["lon"], plan["side_km"])
    if plan["preset"] == "town" and place.get("outline"):
        from shapely.geometry import box as shp_box, mapping, shape
        clipped = shape(place["outline"]).intersection(
            shp_box(box["west"], box["south"], box["east"], box["north"]))
        if not clipped.is_empty:
            return {"shape": mapping(clipped)}
    return box


def cmd_estimate(args: dict) -> dict:
    knoxmap()
    from web.checks import _beyond_this_pc, _too_big_for_memory
    side_tiles = args["plan"]["side_km"] * 1000
    return {"tight": _too_big_for_memory(side_tiles, side_tiles),
            "impossible": _beyond_this_pc(side_tiles, side_tiles)}


def _poll_buildings(client, name: str, done: threading.Event) -> None:
    while not done.wait(1.0):
        p = call(client, "GET", f"/api/progress?map={name}")
        if p.get("stage") == "buildings" and p.get("fraction") is not None:
            progress("buildings", float(p["fraction"]), p.get("note") or "")


def cmd_generate(args: dict) -> dict:
    plan, name, title = args["plan"], args["map_name"], args["title"]
    staging = Path(args["staging_dir"])
    client = knoxmap()

    progress("generate", 0, "Downloading the map data")
    call(client, "POST", "/api/generate", {**area_body(plan), "metersPerTile": 1, "mapName": name})
    progress("generate", 1, "Map data ready")

    progress("buildings", 0, "Laying out buildings")
    done = threading.Event()
    watcher = threading.Thread(target=_poll_buildings, args=(client, name, done), daemon=True)
    watcher.start()
    try:
        b = call(client, "POST", "/api/buildings", {"mapName": name})
    finally:
        done.set()
    progress("buildings", 1, f"{b.get('count', 0)} buildings")

    progress("compile", 0, "Compiling")
    call(client, "POST", "/api/compile", {"mapName": name})
    while True:
        s = call(client, "GET", f"/api/compile-status?map={name}")
        expected = s.get("expected") or 0
        if expected:
            progress("compile", s.get("cells", 0) / expected, f"cells {s.get('cells', 0)}/{expected}")
        if s.get("state") in ("done", "error", "stopped"):
            break
        time.sleep(5)
    if s.get("state") != "done" or s.get("failed"):
        raise Failed(f"Compile ended '{s.get('state')}': {s.get('error') or s.get('failed')}")

    preview = None
    progress("pictures", 0, "Drawing the preview")
    try:
        call(client, "POST", "/api/pictures", {"mapName": name})
        while (p := call(client, "GET", f"/api/pictures-status?map={name}")).get("state") == "running":
            time.sleep(2)
        if p.get("files"):
            preview = str(KNOXMAP / p["files"][0].lstrip("/"))
    except Failed:
        pass  # a missing preview never stops a map
    progress("pictures", 1, "")

    progress("package", 0, "Packaging the mod")
    from tools import make_map_mod
    from web.common import OUTPUT_DIR
    staging.mkdir(parents=True, exist_ok=True)
    with contextlib.redirect_stdout(sys.stderr):
        mod_root, _cells, _extras = make_map_mod.package(
            str(OUTPUT_DIR / name), title, name, mods_dir=str(staging))
    mod_root = Path(mod_root)
    if not (mod_root / "ATTRIBUTION.txt").exists():
        (mod_root / "ATTRIBUTION.txt").write_text(ATTRIBUTION, encoding="utf-8")
    if preview and Path(preview).exists():
        shutil.copyfile(preview, staging / f"{name}.preview.png")
        preview = str(staging / f"{name}.preview.png")
    progress("package", 1, "Done")
    return {"mod_dir": str(mod_root), "preview": preview}


COMMANDS = {"check": cmd_check, "search": cmd_search, "estimate": cmd_estimate,
            "generate": cmd_generate}


def main(argv: list[str]) -> int:
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        command = COMMANDS[argv[1]]
        args = json.loads(argv[2]) if len(argv) > 2 else {}
        result = command(args)
    except Exception as exc:  # noqa: BLE001 - every failure is reported as an event
        emit(event="error", message=str(exc) or type(exc).__name__)
        return 1
    emit(event="result", **result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
