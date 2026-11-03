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


def frame_spawn_picture(map_dir: Path, origin: tuple[int, int]) -> tuple[int, int, int, int] | None:
    """Put the spawn picture at the town's world tiles and point the picker at it.

    The picture's bounds must be where the town really is, so it can sit
    beside vanilla Knox County's (see spawn_picture_lua). origin is the map's
    world tile origin; writing it every time also repairs a picture an older
    Portal moved to 0,0. Returns the world bounds.
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
    ox, oy = origin
    if (x0, y0) != (ox, oy):
        new_txt = "\n".join(f"bounds={ox} {oy} {ox + w} {oy + h}" if ln.startswith("bounds=") else ln
                            for ln in lines) + "\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            for info, data in entries:
                z.writestr(info, new_txt.encode("utf-8") if info.filename == "pyramid.txt" else data)
        pyramid.write_bytes(buf.getvalue())
    zoom = round(math.log2(EARTH_M / max(w, h, 1)), 1)
    _rewrite_info(map_dir / "map.info", ZOOM_KEYS,
                  [f"zoomX={ox + w // 2}", f"zoomY={oy + h // 2}", f"zoomS={zoom}"])
    return ox, oy, ox + w, oy + h


def _lua_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


SPAWN_PICTURE_LUA = """\
-- Written by Portal for {title}.
-- The New Game spawn screen draws only one map picture: the last region's,
-- which is vanilla Knox County's. This adds this town's picture beside it,
-- at the town's real place, and widens the frame so both fit.
PortalSpawnPictures = PortalSpawnPictures or {{}}
PortalSpawnPictures[{map_dir}] = {{ maxX = {max_x}, maxY = {max_y} }}

local function patch()
    if not (MapSpawnSelect and MapSpawnSelectImage) or MapSpawnSelect.portalPatched then return end
    MapSpawnSelect.portalPatched = true

    local fillList = MapSpawnSelect.fillList
    function MapSpawnSelect:fillList()
        fillList(self)
        local panel = self.mapPanel
        panel.portalMaxX, panel.portalMaxY = nil, nil
        for _, v in ipairs(self:getSpawnRegions() or {{}}) do
            local pic = PortalSpawnPictures[v.name]
            local info = pic and getMapInfo(v.name)
            local file = info and info.spawnSelectImagePyramid
            if file then
                if not panel.pyramidFileName then
                    panel:setImagePyramid(file)
                elseif file ~= panel.pyramidFileName then
                    panel.mapAPI:addImagePyramid(file)
                end
                panel.portalMaxX = math.max(panel.portalMaxX or 0, pic.maxX)
                panel.portalMaxY = math.max(panel.portalMaxY or 0, pic.maxY)
            end
        end
    end

    local prerender = MapSpawnSelectImage.prerender
    function MapSpawnSelectImage:prerender()
        local framing = self.pyramidFileName and not self.hasResetView and self:getWidth() >= 1
        prerender(self)
        if not (framing and self.hasResetView and self.portalMaxX) then return end
        local api = self.mapAPI
        api:setBoundsInSquares(0, 0,
            math.max(api:getImagePyramidWidthInSquares(self.pyramidFileName), self.portalMaxX),
            math.max(api:getImagePyramidHeightInSquares(self.pyramidFileName), self.portalMaxY))
        api:resetView()
        local list = self.parent and self.parent.listbox
        local item = list and list.items[list.selected] and list.items[list.selected].item
        if item and item.zoomS and item.zoomS ~= 0 then
            api:centerOn(item.zoomX, item.zoomY)
            api:setZoom(item.zoomS)
        end
    end
end

patch()
Events.OnGameBoot.Add(patch)
"""


def write_spawn_picture_lua(mod_root: Path, mod_id: str, map_dir_name: str, title: str,
                            bounds: tuple[int, int, int, int]) -> Path:
    path = Path(mod_root) / "common" / "media" / "lua" / "client" / "Portal" / f"{mod_id}_SpawnPicture.lua"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SPAWN_PICTURE_LUA.format(title=title.replace("\n", " "), map_dir=_lua_str(map_dir_name),
                                             max_x=bounds[2], max_y=bounds[3]), encoding="utf-8")
    return path


EXTRA_CREDITS = {  # same wording as portal.model.EXTRA_BUILDING_CREDITS
    "microsoft": "Some building footprints from Microsoft Global ML Building Footprints, "
                 "available under the ODbL: https://github.com/microsoft/GlobalMLBuildingFootprints",
    "overture": "Some building footprints © Overture Maps Foundation, available under the ODbL: "
                "https://overturemaps.org",
}


def credit_extra_buildings(mod_root: Path, sources: list[str]) -> None:
    """Gaps filled from another source need their own credit beside OpenStreetMap's."""
    path = Path(mod_root) / "ATTRIBUTION.txt"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [EXTRA_CREDITS[s] for s in sources if s in EXTRA_CREDITS and EXTRA_CREDITS[s] not in text]
    if lines:
        path.write_text(text.rstrip("\n") + "\n\nMORE BUILDINGS\n" + "\n".join(lines) + "\n",
                        encoding="utf-8")


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
