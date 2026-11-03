"""Lay out a generated town where Project Zomboid's Workshop uploader looks.

The upload itself is the player's: Project Zomboid > Workshop > Create and
Upload, then pick the folder this writes.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from .installer import MARKER
from .model import Town

REMINDER = ("This map shows a real place, including homes, schools and places of "
            "worship. Publish it only if you are comfortable sharing that.")
PREVIEW_SIZE = (256, 256)


def workshop_root() -> Path:
    return Path(os.environ.get("USERPROFILE", Path.home())) / "Zomboid" / "Workshop"


def prepare(town: Town, workshop_root: Path) -> Path:
    folder = Path(workshop_root) / town.mod_id
    contents = folder / "Contents" / "mods" / town.mod_id
    if (folder / "Contents").exists():
        shutil.rmtree(folder / "Contents")
    shutil.copytree(town.mod_dir, contents, ignore=shutil.ignore_patterns(MARKER))
    _write_preview(town, folder / "preview.png")

    lines = ["version=1"]
    if town.workshop_id:
        lines.append(f"id={town.workshop_id}")
    lines += [f"title={town.title}",
              f"description=Real-world map of {town.title} generated with Portal and KnoxMap.",
              "description=Map data © OpenStreetMap contributors (ODbL).",
              "tags=Build 42;Map",
              "visibility=unlisted"]
    (folder / "workshop.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder


def _write_preview(town: Town, path: Path) -> None:
    if town.preview and Path(town.preview).exists():
        with Image.open(town.preview) as im:
            ImageOps.fit(im.convert("RGB"), PREVIEW_SIZE).save(path)
        return
    im = Image.new("RGB", PREVIEW_SIZE, (34, 40, 34))
    ImageDraw.Draw(im).text((12, 118), town.title[:36], fill=(220, 220, 200))
    im.save(path)
