"""Portal's few settings, in %LOCALAPPDATA%/Portal/settings.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "knoxmap_dir": None,  # found on first run (find_knoxmap), or set on Portal's page
    "allow_untested_engine": False,
    "pz_install": None,  # only needed when KnoxMap cannot find the game itself
}


def default_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Portal" / "settings.json"


def is_knoxmap(folder: str | Path | None) -> bool:
    """A KnoxMap folder that has been through its Setup (it made the .venv)."""
    return bool(folder) and (Path(folder) / "app.py").is_file() and \
        (Path(folder) / ".venv" / "Scripts" / "python.exe").is_file()


def find_knoxmap(roots: list[Path] | None = None) -> str | None:
    """Look where people usually unpack or clone KnoxMap, one level deep."""
    if roots is None:
        home = Path.home()
        roots = [home, home / "Documents", home / "Desktop", home / "Downloads",
                 *(Path(f"{d}:\\") for d in "CDEFG"), *(Path(f"{d}:\\modding") for d in "CDEFG")]
    for root in roots:
        try:
            folders = sorted(p for p in Path(root).iterdir() if p.is_dir())
        except OSError:
            continue
        # knoxmap, knoxmap-main, and a knoxmap inside a project folder
        candidates = [p for p in folders if "knoxmap" in p.name.lower()]
        candidates += [p / "knoxmap" for p in folders]
        for candidate in candidates:
            if is_knoxmap(candidate):
                return str(candidate)
    return None


def load(path: Path | None = None) -> dict:
    path = Path(path or default_path())
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    values = {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}
    if not values["knoxmap_dir"]:
        values["knoxmap_dir"] = find_knoxmap()
        if values["knoxmap_dir"]:
            save(values, path)
    return values


def save(values: dict, path: Path | None = None) -> None:
    path = Path(path or default_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: values[k] for k in DEFAULTS if k in values}, indent=2),
                    encoding="utf-8")
