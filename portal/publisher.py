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


def description(title: str) -> list[str]:
    """Credits every published town needs (ODbL, KnoxMap's terms, TIS Modding Policy)."""
    return [f"Real-world map of {title}, generated with Portal and KnoxMap.",
            "Buildings follow OpenStreetMap; everything inside them is invented.",
            "",
            "Map data © OpenStreetMap contributors, available under the ODbL: "
            "https://www.openstreetmap.org/copyright",
            "Built with KnoxMap by euclid80tr (github.com/spytheeuclidean-a11y/knoxmap), "
            "based on Knoxify by arytek.",
            "Unofficial fan production for non-commercial purposes, not affiliated with "
            "or endorsed by The Indie Stone. Thanks to The Indie Stone for creating Project Zomboid."]


def _read_existing(path: Path) -> tuple[str | None, list[str]]:
    """The Workshop id the game wrote back after an upload, and the player's own description."""
    if not path.exists():
        return None, []
    lines = path.read_text(encoding="utf-8").splitlines()
    ids = [ln[3:].strip() for ln in lines if ln.startswith("id=") and ln[3:].strip()]
    return (ids[0] if ids else None), [ln[12:] for ln in lines if ln.startswith("description=")]


def prepare(town: Town, workshop_root: Path) -> Path:
    folder = Path(workshop_root) / town.mod_id
    contents = folder / "Contents" / "mods" / town.mod_id
    if (folder / "Contents").exists():
        shutil.rmtree(folder / "Contents")
    shutil.copytree(town.mod_dir, contents, ignore=shutil.ignore_patterns(MARKER))
    _write_preview(town, folder / "preview.png")

    # Publishing again must keep the id, or the next upload makes a second item.
    old_id, old_description = _read_existing(folder / "workshop.txt")
    workshop_id = old_id or town.workshop_id
    lines = ["version=1"]
    if workshop_id:
        lines.append(f"id={workshop_id}")
    lines.append(f"title={town.title}")
    lines += [f"description={d}" for d in (old_description or description(town.title))]
    lines += ["tags=Build 42;Map", "visibility=unlisted"]
    (folder / "workshop.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder


def _write_preview(town: Town, path: Path) -> None:
    if town.preview and Path(town.preview).exists():
        try:
            with Image.open(town.preview) as im:
                ImageOps.fit(im.convert("RGB"), PREVIEW_SIZE).save(path)
            return
        except OSError:
            pass  # a damaged picture gets the plain card below
    im = Image.new("RGB", PREVIEW_SIZE, (34, 40, 34))
    ImageDraw.Draw(im).text((12, 118), town.title[:36], fill=(220, 220, 200))
    im.save(path)
