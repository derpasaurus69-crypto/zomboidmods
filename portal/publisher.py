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


def description(title: str, extra_credits: list[str] = ()) -> list[str]:
    """Credits every published town needs (ODbL, KnoxMap's terms, TIS Modding Policy)."""
    return [f"Real-world map of {title}, generated with Portal and KnoxMap.",
            "Streets and buildings follow real map data; everything inside the buildings is invented.",
            "",
            "Map data © OpenStreetMap contributors, available under the ODbL: "
            "https://www.openstreetmap.org/copyright",
            *extra_credits,
            "Built with KnoxMap by euclid80tr (github.com/spytheeuclidean-a11y/knoxmap), "
            "based on Knoxify by arytek.",
            "Unofficial fan production for non-commercial purposes, not affiliated with "
            "or endorsed by The Indie Stone. Thanks to The Indie Stone for creating Project Zomboid."]


def _read_existing(path: Path) -> dict[str, list[str]]:
    """What the last upload left: the id the game wrote back, and the player's own
    title, description, tags and visibility."""
    found: dict[str, list[str]] = {}
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = ln.partition("=")
            if sep and key in ("id", "title", "description", "tags", "visibility"):
                found.setdefault(key, []).append(value)
    return found


def prepare(town: Town, workshop_root: Path) -> Path:
    folder = Path(workshop_root) / town.mod_id
    contents = folder / "Contents" / "mods" / town.mod_id
    if (folder / "Contents").exists():
        shutil.rmtree(folder / "Contents")
    shutil.copytree(town.mod_dir, contents, ignore=shutil.ignore_patterns(MARKER))
    _write_preview(town, folder / "preview.png")

    # Publishing again must keep the id, or the next upload makes a second item,
    # and must keep what the player chose (a public item stays public).
    old = _read_existing(folder / "workshop.txt")
    workshop_id = next((v.strip() for v in old.get("id", []) if v.strip()), None) or town.workshop_id
    lines = ["version=1"]
    if workshop_id:
        lines.append(f"id={workshop_id}")
    lines.append(f"title={old.get('title', [town.title])[0]}")
    lines += [f"description={d}" for d in (old.get("description") or description(town.title, town.credits))]
    lines += [f"tags={old.get('tags', ['Build 42;Map'])[0]}",
              f"visibility={old.get('visibility', ['unlisted'])[0]}"]
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
