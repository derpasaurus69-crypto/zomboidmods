"""Stands in for runner.py in tests. FAKE_MODE picks the behaviour."""
import json
import os
import subprocess
import sys
import time

mode = os.environ.get("FAKE_MODE", "ok")
command = sys.argv[1]


def emit(**e):
    print(json.dumps(e), flush=True)


if command == "check":
    if mode == "old":
        emit(event="result", version="1.7.0", game="D:/PZ", build42=True)
    elif mode == "b41":
        emit(event="result", version="1.8.4", game="D:/PZ", build42=False)
    else:
        emit(event="result", version="1.8.4", game="D:/PZ", build42=True)
elif command == "search":
    if mode == "noresults":
        emit(event="result", results=[])
    elif mode == "fail":
        emit(event="error", message="Search failed: no network")
        sys.exit(1)
    elif "Far Street" in json.loads(sys.argv[2])["q"]:
        emit(event="result", results=[{"name": "1", "display_name": "1, Far Street, Elsewhere",
                                       "lat": 37.9, "lon": -85.4, "bbox": [37.9, -85.4, 37.9, -85.4],
                                       "type": "house", "outline": None}])
    elif "Example Road" in json.loads(sys.argv[2])["q"]:
        emit(event="result", results=[{"name": "12", "display_name": "12, Example Road, Bardstown",
                                       "lat": 37.802, "lon": -85.401, "bbox": [37.802, -85.401, 37.802, -85.401],
                                       "type": "house", "outline": None}])
    else:
        emit(event="result", results=[{"name": "Bardstown", "display_name": "Bardstown, Kentucky, United States",
                                       "lat": 37.8, "lon": -85.4, "bbox": [37.7, -85.5, 37.9, -85.3],
                                       "type": "town", "outline": None}])
elif command == "estimate":
    emit(event="result", tight=None, impossible="Too big for this PC" if mode == "impossible" else None)
elif command == "generate":
    args = json.loads(sys.argv[2])
    if mode == "noise":
        print("wrote 854 .tbx files", flush=True)
    for step, pct in (("generate", 0), ("buildings", 30), ("compile", 60)):
        emit(event="progress", step=step, pct=pct, message=step)
        if mode == "noise":
            print("some KnoxMap chatter", flush=True)
    if mode == "fail":
        emit(event="error", message="Compile ended 'error': cell 3_4")
        sys.exit(1)
    if mode == "hang":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
        with open(os.environ["FAKE_CHILD_PID_FILE"], "w") as f:
            f.write(str(child.pid))
        time.sleep(600)
    mod = os.path.join(args["staging_dir"], args["map_name"])
    os.makedirs(mod, exist_ok=True)
    # KnoxMap names the mod (and its map folder) after the title it is given.
    with open(os.path.join(mod, "mod.info"), "w", encoding="utf-8") as f:
        f.write(f"name={args['title']}\nid={args['map_name']}\n")
    with open(os.path.join(mod, "ATTRIBUTION.txt"), "w") as f:
        f.write("ATTRIBUTION.txt")
    with open(os.path.join(mod, "plan.json"), "w") as f:  # so tests can see what was asked
        json.dump(args["plan"], f)
    preview = os.path.join(args["staging_dir"], args["map_name"] + ".preview.png")
    with open(preview, "wb") as f:
        f.write(b"\x89PNG fake")
    emit(event="progress", step="package", pct=100, message="Done")
    emit(event="result", mod_dir=mod, preview=preview)
