"""Touches Portal adds to a mod after KnoxMap packages it.

Plain files only (no KnoxMap imports), so the runner can call these and the
tests can check them on a fake mod folder. Each one can be run again safely.
"""
from __future__ import annotations

import io
import math
import zipfile
from pathlib import Path

POSTER_SIZE = 512
INFO_KEYS = ("poster=", "icon=", "category=")
ZOOM_KEYS = ("zoomX=", "zoomY=", "zoomS=")
PYRAMID = "spawnSelectImagePyramid.zip"
EARTH_M = 40075016.69  # MapProjection: zoom z shows EARTH_M / 2**z squares


def _rewrite_info(path: Path, drop: tuple[str, ...], add: list[str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [ln for ln in lines if ln.strip() and not ln.startswith(drop)]
    path.write_text("\n".join(kept + add) + "\n", encoding="utf-8")


def _card(title: str):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (POSTER_SIZE, POSTER_SIZE), (38, 44, 38))
    ImageDraw.Draw(img).text((24, POSTER_SIZE // 2), title, fill=(230, 230, 220))
    return img


def add_poster(mod_root: Path, preview: str | None, title: str) -> None:
    """A square poster beside each mod.info, which the Mods list shows.

    B42 reads <mod>/42/mod.info, then common/; poster= is looked up in 42/ and
    then common/. category=map gives the list its map icon.
    """
    from PIL import Image, ImageOps
    mod_root = Path(mod_root)
    try:
        img = ImageOps.fit(Image.open(preview).convert("RGB"), (POSTER_SIZE, POSTER_SIZE))
    except Exception:  # noqa: BLE001 - no preview or a damaged one: a plain card
        img = _card(title)
    for folder in ("common", "42"):
        if (mod_root / folder).is_dir():
            img.save(mod_root / folder / "poster.png")
    for info in (mod_root / "mod.info", mod_root / "common" / "mod.info", mod_root / "42" / "mod.info"):
        if info.exists():
            _rewrite_info(info, INFO_KEYS, ["poster=poster.png", "category=map"])


def frame_spawn_picture(map_dir: Path) -> tuple[int, int] | None:
    """Make the New Game spawn picture show up.

    The picker always frames 0..width of the picture and clips it to that
    frame, but KnoxMap writes the picture at the town's world tiles, so it is
    clipped away. Move it to start at 0,0 and centre the picker on it with
    zoomX/zoomY/zoomS. Spawning uses spawnpoints.lua, so nothing else moves.
    """
    map_dir = Path(map_dir)
    pyramid = map_dir / PYRAMID
    if not pyramid.exists():
        return None
    with zipfile.ZipFile(pyramid) as z:
        entries = [(i, z.read(i)) for i in z.infolist()]
    txt = next(data for i, data in entries if i.filename == "pyramid.txt").decode("utf-8")
    lines = txt.splitlines()
    x0, y0, x1, y1 = (int(float(v)) for v in
                      next(ln for ln in lines if ln.startswith("bounds=")).split("=", 1)[1].split())
    w, h = x1 - x0, y1 - y0
    if (x0, y0) != (0, 0):
        new_txt = "\n".join(f"bounds=0 0 {w} {h}" if ln.startswith("bounds=") else ln
                            for ln in lines) + "\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            for info, data in entries:
                z.writestr(info, new_txt.encode("utf-8") if info.filename == "pyramid.txt" else data)
        pyramid.write_bytes(buf.getvalue())
    zoom = round(math.log2(EARTH_M / max(w, h, 1)), 1)
    _rewrite_info(map_dir / "map.info", ZOOM_KEYS,
                  [f"zoomX={w // 2}", f"zoomY={h // 2}", f"zoomS={zoom}"])
    return w, h


def pick_spawns(spots: list[tuple[int, int]], centre: tuple[float, float], metres_per_tile: float = 1,
                count: int = 8, radius_m: float = 400, spacing_m: float = 25) -> list[tuple[int, int]]:
    """Homes near the centre, nearest first, not all on one block.

    The game picks one of these at random, and the spawn picture centres on the
    first, so the most central home goes first.
    """
    cx, cy = centre
    radius, spacing = radius_m / metres_per_tile, spacing_m / metres_per_tile
    by_distance = sorted(spots, key=lambda s: (s[0] - cx) ** 2 + (s[1] - cy) ** 2)
    kept: list[tuple[int, int]] = []
    for s in by_distance:
        if len(kept) == count or math.dist(s, centre) > radius:
            break
        if all(math.dist(s, k) >= spacing for k in kept):
            kept.append(s)
    for s in by_distance:  # too few inside the radius: take the nearest anyway
        if len(kept) == count:
            break
        if s not in kept:
            kept.append(s)
    return kept


def nearest_spot(spots: list[tuple[int, int]], point: tuple[float, float], metres_per_tile: float = 1,
                 within_m: float = 30) -> tuple[int, int]:
    """The home floor tile at an address, or the address itself if no home is that close."""
    best = min(spots, key=lambda s: math.dist(s, point), default=None)
    if best is not None and math.dist(best, point) * metres_per_tile <= within_m:
        return best
    return round(point[0]), round(point[1])


def write_spawnpoints(path: Path, points: list[tuple[int, int]]) -> None:
    """The same shape KnoxMap writes. Every profession falls back to unemployed."""
    rows = ",\n".join(f"      {{ posX = {x}, posY = {y}, posZ = 0 }}" for x, y in points)
    Path(path).write_text("function SpawnPoints()\n  return {\n    unemployed = {\n"
                          f"{rows}\n    }}\n  }}\nend\n", encoding="utf-8")
