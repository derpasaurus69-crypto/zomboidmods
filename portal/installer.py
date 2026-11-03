"""Put a finished mod into Zomboid/mods in one step, or not at all."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

MARKER = ".portal.json"


class ForeignModError(Exception):
    """A mod Portal did not make already has this folder name."""


def zomboid_mods_dir() -> Path:
    return Path(os.environ.get("USERPROFILE", Path.home())) / "Zomboid" / "mods"


def staging_dir(mods_dir: Path) -> Path:
    # Same drive as the mods folder, so the final move is a rename, not a copy.
    return Path(mods_dir) / ".portal-staging"


def install(staged_mod: Path, mods_dir: Path) -> Path:
    staged_mod, mods_dir = Path(staged_mod), Path(mods_dir)
    if not (staged_mod / "ATTRIBUTION.txt").exists():
        raise ValueError(f"{staged_mod.name} has no ATTRIBUTION.txt; OpenStreetMap credit is required.")
    target = mods_dir / staged_mod.name
    if target.exists() and not (target / MARKER).exists():
        raise ForeignModError(f"{target} belongs to another mod; Portal will not replace it.")
    (staged_mod / MARKER).write_text(json.dumps({"mod_id": staged_mod.name}), encoding="utf-8")

    old = target.with_name(target.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if target.exists():
        os.replace(target, old)
    try:
        os.replace(staged_mod, target)
    except OSError:
        if old.exists():
            os.replace(old, target)
        raise
    if old.exists():
        shutil.rmtree(old, ignore_errors=True)
    return target
