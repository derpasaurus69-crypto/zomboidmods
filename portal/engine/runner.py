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
import finish  # noqa: E402
from protocol import encode, overall_pct  # noqa: E402

KNOXMAP = Path(os.environ.get("KNOXMAP_DIR", r"D:\modding\pz-portal-engine\knoxmap"))
HOST = {"Host": "127.0.0.1"}  # KnoxMap refuses any other Host
# Only used if KnoxMap ever packages a mod without its own ATTRIBUTION.txt.
ATTRIBUTION = ("Map data (c) OpenStreetMap contributors, available under the Open Database License "
               "(ODbL): https://www.openstreetmap.org/copyright\n"
               "Generated with KnoxMap by euclid80tr (https://github.com/spytheeuclidean-a11y/knoxmap).\n"
               "Thanks to The Indie Stone for creating Project Zomboid. This is an unofficial fan "
               "production for non-commercial purposes, not made or endorsed by The Indie Stone.\n")

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
    body = {**area_body(plan), "metersPerTile": 1, "mapName": name}
    if plan.get("fill_gaps"):
        body["settings"] = {"fill_gaps": 1}
    call(client, "POST", "/api/generate", body)
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
    result = finish_mod(OUTPUT_DIR / name, mod_root, _extras, plan, preview, title)
    if preview and Path(preview).exists():
        shutil.copyfile(preview, staging / f"{name}.preview.png")
        preview = str(staging / f"{name}.preview.png")
    progress("package", 1, "Done")
    return {"mod_dir": str(mod_root), "preview": preview, **result}


def _projector(project: Path):
    """KnoxMap's own projection for this map (maps are turned, so not plain degrees)."""
    from generator.rendering.projection import Projector
    info = json.loads((project / f"{project.name}_info.json").read_text(encoding="utf-8"))
    b, mpt = info["bbox"], float(info.get("meters_per_tile") or 1)
    return Projector.build(b["south"], b["west"], b["north"], b["east"], mpt, info.get("rotation", 0.0))


def _step(what: str, fn, *a):
    """Portal's own touches never cost the map: log and carry on."""
    try:
        return fn(*a)
    except Exception as exc:  # noqa: BLE001
        print(f"Portal: {what} skipped: {exc!r}", file=sys.stderr)
        return None


def _spawns(project: Path, mod_root: Path, extras, plan: dict) -> dict:
    if any(Path(e).name == "spawnpoints.lua" for e in extras or ()):
        return {}  # the project brought its own spawns
    from tools import make_map_mod
    target = next(mod_root.glob("common/media/maps/*/spawnpoints.lua"), None)
    if target is None:
        return {}
    ox, oy = make_map_mod._world_origin_tiles(str(project))
    spots = make_map_mod._spawn_tiles(str(project), limit=10 ** 6)
    place, spawn = plan["place"], plan.get("spawn")
    pr = _projector(project)
    mpt = pr.meters_per_tile
    cx, cy = pr.to_px(place["lat"], place["lon"])
    if spawn:
        sx, sy = pr.to_px(spawn["lat"], spawn["lon"])
        if 0 <= sx < pr.width and 0 <= sy < pr.height:
            x, y = finish.nearest_spot(spots, (sx, sy), mpt)
            finish.write_spawnpoints(target, [(x + ox, y + oy)])
            return {"spawn": {"x": x + ox, "y": y + oy, "at": "address"}}
        print(f"Portal: spawn address {spawn} is outside the map", file=sys.stderr)
    if not spots:
        return {}
    points = [(x + ox, y + oy) for x, y in finish.pick_spawns(spots, (cx, cy), mpt)]
    finish.write_spawnpoints(target, points)
    return {"spawn": {"x": points[0][0], "y": points[0][1], "at": "centre"}}


def finish_mod(project: Path, mod_root: Path, extras, plan: dict, preview, title: str) -> dict:
    """Poster, spawn picture and central spawns, on top of what KnoxMap packaged."""
    _step("poster", finish.add_poster, mod_root, preview, title)
    _step("spawn picture", _spawn_picture, Path(project), mod_root, title)
    sources = _extra_buildings(Path(project)) if plan.get("fill_gaps") else []
    if sources:
        _step("credits", finish.credit_extra_buildings, mod_root, sources)
    result = _step("spawn points", _spawns, Path(project), mod_root, extras, plan) or {}
    return {**result, "extra_buildings": sources}


def _extra_buildings(project: Path) -> list[str]:
    """Which footprint sources KnoxMap filled gaps from (it caches each beside the map)."""
    return [s for s in ("microsoft", "overture") if (project / f"{project.name}_{s}.json.gz").exists()]


def _spawn_picture(project: Path, mod_root: Path, title: str) -> None:
    from tools import make_map_mod
    origin = make_map_mod._world_origin_tiles(str(project))
    for map_dir in mod_root.glob("common/media/maps/*"):
        bounds = finish.frame_spawn_picture(map_dir, origin)
        if bounds:
            finish.write_spawn_picture_lua(mod_root, mod_root.name, map_dir.name, title, bounds)


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
