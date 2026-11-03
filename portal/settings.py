"""Portal's few settings, in %LOCALAPPDATA%/Portal/settings.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "knoxmap_dir": r"D:\modding\pz-portal-engine\knoxmap",
    "allow_untested_engine": False,
    "pz_install": None,  # only needed when KnoxMap cannot find the game itself
}


def default_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Portal" / "settings.json"


def load(path: Path | None = None) -> dict:
    path = Path(path or default_path())
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}


def save(values: dict, path: Path | None = None) -> None:
    path = Path(path or default_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: values[k] for k in DEFAULTS if k in values}, indent=2),
                    encoding="utf-8")
