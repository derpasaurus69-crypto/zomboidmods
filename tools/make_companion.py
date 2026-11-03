"""Build the Portal companion mod: install it for testing and lay it out for
the Workshop uploader.

    .venv\\Scripts\\python tools\\make_companion.py

Writes the mod.info files and the poster, copies companion/portal_companion to
%USERPROFILE%\\Zomboid\\mods\\portal_companion, and prepares
%USERPROFILE%\\Zomboid\\Workshop\\portal_companion with workshop.txt and
preview.png. A Workshop id the game wrote back after an upload is kept.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "companion" / "portal_companion"
DESCRIPTION = ROOT / "docs" / "release" / "workshop-portal.bbcode"
BACKDROP = ROOT / "docs" / "playtest" / "bardstown-town.png"
MOD_ID = "portal_companion"
TITLE = "Portal (real towns on the main menu)"
MOD_INFO = [
    "name=Portal",
    f"id={MOD_ID}",
    "description=Lists the Portal towns you have installed and shows how to make your own real town "
    "with the free Portal app. Unofficial; maps are built by KnoxMap. Map data (c) OpenStreetMap "
    "contributors (ODbL).",
    "poster=poster.png",
    "category=features",
]


def font(size: int):
    for name in ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def poster(size: int) -> Image.Image:
    """The Bardstown render, darkened, with PORTAL on it."""
    try:
        img = ImageOps.fit(Image.open(BACKDROP).convert("RGB"), (size, size))
    except OSError:
        img = Image.new("RGB", (size, size), (40, 46, 40))
    img = Image.blend(img, Image.new("RGB", img.size, (10, 12, 10)), 0.55)
    draw = ImageDraw.Draw(img)
    big, small = font(size // 6), font(size // 18)
    for text, f, y in (("PORTAL", big, size * 0.36), ("real towns for Project Zomboid", small, size * 0.56)):
        w = draw.textlength(text, font=f)
        draw.text(((size - w) / 2 + 2, y + 2), text, font=f, fill=(0, 0, 0))
        draw.text(((size - w) / 2, y), text, font=f, fill=(235, 235, 220))
    return img


def write_mod_files() -> None:
    info = "\n".join(MOD_INFO) + "\n"
    for folder in (SOURCE, SOURCE / "common", SOURCE / "42"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "mod.info").write_text(info, encoding="utf-8")
    image = poster(512)
    for folder in (SOURCE / "common", SOURCE / "42"):
        image.save(folder / "poster.png")


def install(mods: Path) -> Path:
    target = mods / MOD_ID
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SOURCE, target)
    return target


def prepare_workshop(workshop: Path) -> Path:
    folder = workshop / MOD_ID
    old = (folder / "workshop.txt").read_text(encoding="utf-8").splitlines() \
        if (folder / "workshop.txt").exists() else []
    if (folder / "Contents").exists():
        shutil.rmtree(folder / "Contents")
    shutil.copytree(SOURCE, folder / "Contents" / "mods" / MOD_ID)
    poster(256).save(folder / "preview.png")
    keep = {k: v for k, _, v in (ln.partition("=") for ln in old) if k in ("id", "visibility")}
    lines = ["version=1"] + ([f"id={keep['id']}"] if keep.get("id") else []) + [f"title={TITLE}"]
    lines += [f"description={ln}" for ln in DESCRIPTION.read_text(encoding="utf-8").splitlines()]
    lines += ["tags=Build 42;Misc;Interface", f"visibility={keep.get('visibility', 'unlisted')}"]
    (folder / "workshop.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder


def main() -> None:
    zomboid = Path(os.environ.get("USERPROFILE", Path.home())) / "Zomboid"
    write_mod_files()
    print("installed:", install(zomboid / "mods"))
    print("workshop folder:", prepare_workshop(zomboid / "Workshop"))


if __name__ == "__main__":
    main()
