"""Phase 0 spike: type a place name, get an installed PZ map mod, via KnoxMap.

Throwaway prototype of Portal's EngineAdapter. Drives KnoxMap's own Flask API
in-process (test client, no server, no window), in the order its UI does:
search -> generate -> buildings -> compile -> install.

Run with KnoxMap's own venv python, from anywhere:

    D:/modding/pz-portal-engine/knoxmap/.venv/Scripts/python.exe spike/drive_knoxmap.py "Bardstown, Kentucky" --km 1.0
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time

KNOXMAP = os.environ.get("KNOXMAP_DIR", r"D:\modding\pz-portal-engine\knoxmap")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def box_around(lat: float, lon: float, km: float) -> dict:
    half_lat = (km / 2) / 111.32
    half_lon = (km / 2) / (111.32 * math.cos(math.radians(lat)))
    return {"south": lat - half_lat, "north": lat + half_lat,
            "west": lon - half_lon, "east": lon + half_lon}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("place")
    ap.add_argument("--km", type=float, default=1.0, help="side of the square, km")
    ap.add_argument("--pick", type=int, default=0, help="which search result")
    ap.add_argument("--skip-to", choices=["buildings", "compile", "install"])
    args = ap.parse_args()

    os.chdir(KNOXMAP)
    sys.path.insert(0, KNOXMAP)
    os.environ.setdefault("PYTHONUTF8", "1")
    from app import app  # KnoxMap's Flask app

    c = app.test_client()
    base = {"Host": "127.0.0.1"}

    def post(path: str, body: dict) -> dict:
        r = c.post(path, json=body, headers=base)
        data = r.get_json(silent=True) or {}
        if r.status_code >= 400:
            raise SystemExit(f"{path} -> {r.status_code}: {data.get('error') or r.data[:400]}")
        return data

    def get(path: str) -> dict:
        r = c.get(path, headers=base)
        return r.get_json(silent=True) or {}

    slug = re.sub(r"[^a-z0-9]+", "_", args.place.lower()).strip("_")
    map_name = f"portal_{slug}_downtown"
    t0 = time.time()

    if not args.skip_to:
        log(f"search: {args.place}")
        res = get(f"/api/search?q={args.place}").get("results") or []
        if not res:
            raise SystemExit("no search results")
        for i, r in enumerate(res[:5]):
            log(f"  [{i}] {json.dumps(r)[:200]}")
        pick = res[args.pick]
        lat, lon = float(pick["lat"]), float(pick["lon"])
        bbox = box_around(lat, lon, args.km)
        log(f"generate {map_name}: {args.km} km square at {lat:.5f},{lon:.5f}")
        g = post("/api/generate", {**bbox, "metersPerTile": 1, "mapName": map_name})
        log(f"  generate -> {json.dumps(g)[:600]}")

    if args.skip_to in (None, "buildings"):
        log("buildings")
        b = post("/api/buildings", {"mapName": map_name})
        log(f"  buildings -> {json.dumps(b)[:600]}")

    if args.skip_to in (None, "buildings", "compile"):
        log("compile")
        post("/api/compile", {"mapName": map_name})
        last = None
        while True:
            s = get(f"/api/compile-status?map={map_name}")
            line = f"{s.get('state')} cells {s.get('cells')}/{s.get('expected')} tmx {s.get('tmx')}"
            if line != last:
                log(f"  {line}")
                last = line
            if s.get("state") in ("done", "error", "stopped", "idle"):
                break
            time.sleep(5)
        if s.get("state") != "done":
            raise SystemExit(f"compile ended {s.get('state')}: {s.get('error')} failed={s.get('failed')}")

    log("install")
    i = post("/api/install", {"mapName": map_name, "modId": map_name,
                              "title": f"{args.place} (Portal spike)"})
    log(f"  install -> {json.dumps(i)}")
    log(f"done in {(time.time() - t0) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
