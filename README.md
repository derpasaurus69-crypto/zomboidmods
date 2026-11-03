# Portal

Type a real place, play it in Project Zomboid (Build 42).

Portal is a small, free, unofficial Windows app. Search a town, pick a size
and press **Generate & Play**. When it finishes, the town is installed as a
map mod with real streets, real street names and furnished buildings. That
takes a few minutes for a small area and 10 to 16 minutes for a whole town on
the developer's PC. You can also choose to start at a street address, and Portal can lay
the town out for the Steam Workshop uploader.

Portal does the searching, the size presets, the spawn points and the
packaging. The map itself is built by
[KnoxMap](https://github.com/spytheeuclidean-a11y/knoxmap) by euclid80tr,
which turns OpenStreetMap data into a compiled PZ map. Portal does not include
KnoxMap. You install it yourself, once, and Portal calls it.

**Status:** early release (0.1.0). Two generated towns have been played
in-game, in singleplayer on one Windows PC: Bardstown, Kentucky and
Schuylkill Haven, Pennsylvania, both at the Town size. Multiplayer, the City
core size and most places in the world have not been tested. How good a map
is depends on how well the place is mapped in OpenStreetMap.

## Needs

- Windows (Portal is Windows only)
- Project Zomboid on Build 42
- KnoxMap 1.8.x (tested with 1.8.4), installed separately

## Install

1. Install Project Zomboid on Steam and switch it to **Build 42**
   (Properties > Betas).
2. Install KnoxMap from
   [its GitHub page](https://github.com/spytheeuclidean-a11y/knoxmap) and
   run its `Setup.bat`, following KnoxMap's own instructions. You only do
   this once. Portal works with KnoxMap 1.8.x. If KnoxMap has moved on to a
   newer series, Portal says so; you can install 1.8.4 from KnoxMap's
   releases page, or set `allow_untested_engine` to `true` in
   `%LOCALAPPDATA%\Portal\settings.json` to try the newer one.
3. Download `Portal.exe` from the [releases page](https://github.com/derpasaurus69-crypto/zomboidmods/releases) and
   run it. It opens in your browser at <http://127.0.0.1:8765/>.

Portal looks for KnoxMap in your home, Documents, Desktop and Downloads
folders and at the top of each drive. If it does not find it, the page asks
for the folder.

The exe is not code-signed, so Windows SmartScreen may show "Windows
protected your PC". Click **More info**, then **Run anyway**. Some antivirus
tools flag unsigned Python apps. The source is in this repo if you would
rather build it yourself.

## Sizes

| Preset | Area | Compiled cells | Time on the dev PC |
|---|---|---|---|
| Downtown | 1 km² | 25 | about 3 to 12 min, mostly downloading map data |
| Town | up to a 3 km square, clipped to the real outline | up to 169 | 10 to 16 min |
| City core | 5 km square | up to 441 | not tested yet, needs a strong PC |

A Downtown map is about 30 MB, and a Town 110 to 185 MB.

## Options

- **Start at an address.** Type a street address in the town. Portal finds
  it and makes it the only spawn point: inside the house there when the map
  has a home within about 30 m, otherwise on the spot itself. If the address
  is clearly outside the chosen size, Portal says so before it starts; one
  near the very edge may fall back to the normal spawns. Without an address
  you start in one of eight homes near the centre.
- **Add buildings OpenStreetMap is missing.** Some towns have few buildings
  mapped. This fills the gaps from Microsoft's building footprints (or
  Overture Maps), and Portal adds their credit to the mod. It is slower, and
  on a well-mapped town it mostly adds sheds, so use it when a town looks
  empty. Schuylkill Haven went from 157 buildings to 2,421 with it.

## After generating

1. Launch Project Zomboid and enable the town under **Mods**.
2. Start a **New Game** and choose the town as the spawn region. A map can
   only be added to a new world, so it will not show up in an existing save.

Two Portal towns sit at the same place in the world, so enable only one at a
time.

## Real places

Portal builds real towns. Streets, place names and public buildings come
from OpenStreetMap, which anyone can look at. Everything inside the buildings
is invented by the generator. Portal shows a reminder before you publish a
town. If you used **Start at an address**, think about whose address that is
before you share the map, because a map that starts at someone's home is
more personal than a map of a whole town.

## Publishing a town you made

**Publish to Workshop...** writes `%USERPROFILE%\Zomboid\Workshop\<mod id>`
with `workshop.txt` (unlisted by default), `preview.png` and the mod. Upload
it from the game: **Workshop > Create and update items**. The description
Portal writes already has the credits below. Publishing the same town again
keeps its Workshop id and what you put in `workshop.txt` (title,
description, tags, visibility), so the next upload updates the item instead
of making a new one. Edit the description in `workshop.txt` rather than on
the Steam page, or the next update will put the file's text back.

If you share a town, on the Workshop or anywhere else:

- keep `ATTRIBUTION.txt` in the mod;
- on the page, credit "Map data © OpenStreetMap contributors, available
  under the ODbL" with a link to https://www.openstreetmap.org/copyright,
  and credit KnoxMap by euclid80tr;
- if you used **Add buildings OpenStreetMap is missing**, credit that source
  too (Portal puts the line in `ATTRIBUTION.txt` and the description);
- do not sell it, and do not call it official.

These come from KnoxMap's terms, OpenStreetMap's attribution guidelines and
The Indie Stone's
[Modding Policy](https://projectzomboid.com/blog/modding-policy/).
Publishing a mod grants The Indie Stone a licence to use it with the game.
The town you publish is yours. Portal does not add its own links to it.

## Credits

- **KnoxMap** by euclid80tr, [github.com/spytheeuclidean-a11y/knoxmap](https://github.com/spytheeuclidean-a11y/knoxmap).
  It does the map building. Portal is a front end for it.
- **Knoxify** by arytek, the project KnoxMap is built on.
- **Map data** © [OpenStreetMap](https://www.openstreetmap.org/copyright)
  contributors, available under the Open Database License (ODbL). Towns made
  with gap filling also use
  [Microsoft Global ML Building Footprints](https://github.com/microsoft/GlobalMLBuildingFootprints)
  or [Overture Maps](https://overturemaps.org) data, also under the ODbL.
- Thanks to The Indie Stone for creating Project Zomboid
  (https://projectzomboid.com/), which made this possible. This is an
  unofficial fan production for non-commercial purposes made under the Indie
  Stone Terms (https://projectzomboid.com/blog/support/terms-conditions/).

Portal is unofficial. It is not made, endorsed or supported by The Indie
Stone, or by KnoxMap's author. Project Zomboid is a trademark of The Indie
Stone. Please do not contact The Indie Stone or KnoxMap's author about
problems with Portal.

## Licences

- Portal's own code is under the [MIT licence](LICENSE).
- `Portal.exe` bundles Python (PSF licence), Flask, Werkzeug, Jinja2,
  MarkupSafe, itsdangerous, click and colorama (BSD-3-Clause), blinker (MIT)
  and Pillow (MIT-CMU). Their notices are in
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- KnoxMap is not included. Its own terms are in its
  [LICENSES.md](https://github.com/spytheeuclidean-a11y/knoxmap/blob/main/LICENSES.md).
  Part of KnoxMap comes from Knoxify, which has no published licence. That is
  why Portal links to KnoxMap instead of shipping it.
- Maps you generate contain OpenStreetMap data under the ODbL. See
  `ATTRIBUTION.txt` in each mod.

## Support

Portal and every map it makes are free. Nothing is locked, early-access or
donor-only. If you'd like to support Portal's development, you can
[buy me a coffee](https://buymeacoffee.com/derpasauruo). Tips go to Portal
(by Dean) only, not to KnoxMap, euclid80tr or The Indie Stone.

## Developing

```bash
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
.venv\Scripts\python -m portal
```

Settings live in `%LOCALAPPDATA%\Portal\settings.json` (`knoxmap_dir`,
`allow_untested_engine`, `pz_install`).

Tests:

```bash
.venv\Scripts\python -m pytest
```

The slow test against the real KnoxMap (needs the game and network):

```bash
.venv\Scripts\python -m pytest -m engine
```

Release build:

```bash
.venv\Scripts\python tools\make_notices.py
.venv\Scripts\pyinstaller Portal.spec
```
