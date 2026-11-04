# Accurate (slower) generation mode

I checked the most important claims against the code: `knoxbuild/settings.py:164-207` (how `from_dict` reads settings, including the old-format rewrite), `settings.py:212-279` (allowed ranges and presets), `C:\Users\Dean\pz-portal\portal\engine\runner.py:94-130` and `C:\Users\Dean\pz-portal\portal\model.py:8-50`. Everything else comes from the research you passed in. Unless a Portal path is given, line numbers are in `D:\modding\pz-portal-engine\knoxmap`.

**Main finding:** most of the inaccuracy in today's maps comes from guessed building kinds and heights, not from streets. In Bardstown, 1296 of 3012 buildings (43%) became blocks of flats 3-6 storeys high. All of them were plain `building=yes` with no height recorded (placements.csv; `build.py:372-376`). This happens because `apartment_footprint=150` is counted in tiles, so at 1 m per tile an ordinary American house qualifies (`build.py:1743`). Accurate mode should mostly use real footprint and height data and stop inventing flats. It should only lightly change roads, which you already like.

---

## 1) Settings Portal should send

Put them all in the `/api/generate` body. `/api/generate` saves them to settings.json (`web/generation.py:149-150`), and `/api/buildings` reads that file back (`generation.py:408`, `mapfiles.py:23-27`), so they only need sending once.

**Normal mode needs a fix too, not just Accurate.** If a request contains `straight_roads` (or `square_buildings`) but no `building_alignment`, `from_dict` replaces the alignment. With `straight_roads >= 1` it becomes `"rectangle"`, which reduces every building to a box (`settings.py:194-206`). Any Portal mode that sends `straight_roads` must also send `building_alignment`.

```python
ACCURATE_BASE = {
    "fill_gaps": 1,
    "fill_frontage": 0,
    "true_map": 1,
    "min_size": 3,
    "max_size": 250,
    "max_levels": 12,
    "height_mix": "auto",
    "building_alignment": "rectilinear",
    "straight_roads": 3,
    "align_streets": 1,
    "rotate_degrees": 0.0,
    "arch_style": "auto",
    "tree_density": 1.0,
    "forest_density": 1.0,
}
# Building-style guess, chosen by region (see below)
ACCURATE_NORTH_AMERICA = {"apartment_footprint": 600, "apartment_chance": 0.1}
ACCURATE_EUROPE_TURKEY = {"apartment_footprint": 150, "apartment_chance": 0.55}  # same as today's default
```

| Setting | Value | Why |
|---|---|---|
| `fill_gaps` | 1 (allowed 0-1, default 0, `settings.py:86,220`) | Adds real Microsoft ML footprints, with heights, where OSM has none. This is the only source of measured heights. Schuylkill got 57.7% of building heights from data this way; Bardstown, built without it, got 0% (knoxmap.log:336, 611-613). |
| `fill_frontage` | 0 (0-1, default 0) | It makes up buildings with no data behind them (`infill.py:1-25`). That is the opposite of accurate, so it stays off. |
| `true_map` | 1 (0-1, default 1) | Builds every mapped building. 0 thins out about half the houses (`build.py:1577-1611`). Sent explicitly so it cannot drift. |
| `min_size` | 3 (3-40, default 3) | Keeps every footprint that can hold a room (`footprint.py:404-405`). |
| `max_size` | 250 (8-250, default 200) | Places large landmarks whole more often instead of cutting them into units (`build.py:267-285`). The game's file reader allows up to 300 (`settings.py:223-224`). |
| `max_levels` | 12 (1-31, default 6) | The cap also cuts down recorded heights (`build.py:438,446`). 12 matches the highest guess in the tables (`regional.py:186-187`). See risk R3 for why it is not 31. |
| `height_mix` | `auto` (auto/low/middle/tall/even, default auto) | Only shapes guessed heights; recorded heights are never changed (`settings.py:142-143`). Try `low` as an A/B variant. |
| `building_alignment` | `rectilinear` (real/smart/rectilinear/rectangle, default rectilinear) | Keeps the true outline (L-shapes, notches) and squares it to the tile grid. **`real` is left out on purpose:** off-grid walls come out as jagged staircases and rooms become irregular, which looks worse in Project Zomboid. Sending it explicitly avoids the rewrite described above. |
| `straight_roads` | 3 (0-3, default 1) | Roads use the game's 16 directions and stay within 6 tiles of their real line in town and 40 out of town, and junctions move at most 15 tiles (`snap.py:113,137`). Mode 1 straightens roads with a weak hold and drags everything within 30 tiles along with them (`octilinear.py:9-19,41-43`). **This is the one choice the A/B test must confirm.** See R1. |
| `align_streets` / `rotate_degrees` | 1 / 0.0 (defaults) | Rotating the whole map as one piece keeps every shape and distance (`generation.py:256-262`). |
| `arch_style` | `auto` (default) | Picks regional building styles from building names; forcing a style is less accurate. |
| `tree_density` / `forest_density` | 1.0 (0-3, default 1.0) | Trees as mapped. Any other value adds or removes trees with no data behind it. This is also why the whole `suburb` preset is not sent: it sets `tree_density` to 1.3 and `max_levels` to 2 (`settings.py:263-266`). |
| `apartment_footprint` / `apartment_chance` (North America) | 600 / 0.1 (16-4000 / 0.0-1.0, default 150 / 0.55) | Same values as the suburb preset. This stops ordinary US houses turning into 3-6 storey flats (`build.py:372-388`). The code comments call the default "what a European or Turkish town centre looks like" (`settings.py:267`). |
| Same pair (Europe/Turkey) | 150 / 0.55 | The defaults were tuned on Turkish data (`build.py:347-352`). |

**Choosing the region.** Portal's `Place` record has no country code (`model.py:8-15`), so `runner.py` would have to read the last part of `display_name`: "United States", "Canada" or "Australia" gives the North American values, anything else gives the European ones. Add a small override in the panel ("Building style: American / European"), because guessing from the name can fail.

**Left out on purpose:**
- `room_solver`: needs OR-Tools, which is not in KnoxMap's environment, so turning it on does nothing (`room_solver.py:2146-2150`). It would only change interiors anyway, not the map.
- `m2_per_person`, `spawn_density`, `zombies_per_resident`, `parking_density`, basement settings, `guaranteed_rifle`, `seed`: these affect gameplay, not geography.
- `room_size`, `neighbourhood_tiles`, `style_oddity`, `vanilla_tiles`: purely cosmetic guesses, and there is no data to make them more accurate.
- `square_buildings`: has no effect with `rectilinear`, and sending it would trigger the alignment rewrite.
- `metersPerTile`: stays at 1. A value of 0.5 means about 4x the memory and time (`generation.py:94-97`).

**Portal code changes this needs:**
- `runner.py:127-129`: send the merged settings dict whenever the mode is Accurate.
- Accurate must also set `plan.fill_gaps=True`. Otherwise the Microsoft/Overture credit lines are lost, because `runner.py:234` only adds them when `plan.get("fill_gaps")` is set.
- Add a `mode` field to `AreaPlan` (`model.py:41-50`) and a checkbox in `portal.js:101`.
- Optional: raise `est_minutes` for Accurate.

---

## 2) What Portal cannot reach without changing KnoxMap

| Gap | KnoxMap change needed | What it would improve |
|---|---|---|
| Heights from Overture or Microsoft for buildings OSM already has (fill_gaps only adds missing ones: `overture.py:250-297`, `msbuildings.py:146-148`) | A new pass that copies height and floor count onto overlapping OSM buildings that have no height, plus duckdb installed | **High.** Bardstown's 2549 OSM buildings have 0 heights today. |
| Real building kinds (Microsoft rows have no class: `overture.py:228-229`) | Read Overture `class` and `subtype` for every building, not only as a fallback when Microsoft fails (`generation.py:214-227`) | High for kinds. 97% or more of US buildings are generic `yes` today. |
| Shops and businesses beyond OSM (OSM has about 200 per town) | Fetch Overture places and pass them through the existing building-use code (`build.py:1712-1726`) | Medium to high for interiors and loot. |
| Material and roof shape tags (passed through but never read: `rendering/buildings.py:156-161`) | Map material to `style_named` (`build.py:616-643`) and roof shape to flat or pitched in buildroofs.py | Low. Bardstown has 0 such tags. |
| Sidewalk and road-surface tags on drivable roads (`widths.py:62-104`, `osm.py:1299-1331`) | Handle `sidewalk=no/left/right` and gravel or dirt on all road classes | Moderate for rural Kentucky. |
| Lone mapped trees | Uncomment `osm.py:382-388` and bump FILTERS_VERSION | Low in towns, higher in cities. |
| More land types: golf courses, nature reserves, farmland relations, ditches; `recreation_ground` is handled but never fetched (a bug, `osm.py:1365`) | Widen the fetch filters and classification (`osm.py:358-476,1341-1343`) | Moderate for ground cover. |
| Microsoft confidence filter | Filter on confidence in msbuildings.py | Small: fewer phantom sheds. |
| Paper map (worldmap) detail | Fixed constants in `worldmap.py:65-90` | Cosmetic. |
| Overture fallback and room solver | Install `duckdb` and `ortools` into knoxmap\.venv (environment only, no code change) | Overture is a fallback only; the room solver improves interiors only. |
| Stale cached OSM data (the per-map cache never expires: `osm.py:1080-1118`) | Add an age check | Avoided from Portal by using a new `mapName` for every Accurate run. |

Upstream bug, not fixable here: the `building` column in placements.csv is wrong for every row (`build.py:1934-1971`, `btag` is not carried through). Count from `_buildings.geojson` instead.

---

## 3) Expected time and size cost

Baseline for Bardstown with normal settings (knoxmap.log:322-733): generate 61-111 s, buildings 35-76 s, compile about 601 s, pictures 185 s. Compile dominates.

- **fill_gaps:** adds a few minutes on the first run (`settings.py:83-85`) and about 30 MB per Microsoft tile, cached next to the map (`msbuildings.py:13`). In Schuylkill the download took 5 s, but it adds many buildings: 3478 were added there. More buildings means more layout and compile work.
- **straight_roads 3:** "minutes on a town" (`settings.py:49`). Each link search stops at 1.5M states (`snap.py:143`). It runs once at generate time and is saved as `_roadgraph.json`.
- **Apartment fix:** large savings. Bardstown today has about 6,900 storeys across 3012 buildings ({1:889, 2:910, 3:792, 4:312, 5:79, 6:30}). Schuylkill, with Microsoft data and few flats, has about 2,770 storeys across 2421 buildings. Each storey is a full floor of rooms and furniture (`settings.py:233-238`), so fewer flats can more than make up for the extra buildings at compile time.
- **max_levels 12:** only costs time where data records tall buildings.

**Estimate (not measured):** generate goes from about 1-2 min to about 4-8 min. Buildings and compile stay roughly the same or get faster. Total about 1.2-1.5x normal, mostly at the generate step. Disk size should be about the same or smaller, plus the Microsoft cache of about 30 MB or more and the roadgraph JSON. Treat these numbers as hypotheses until the A/B test measures them.

---

## 4) Risks

- **R1, road mode 3 has never been run on a Portal map.** It can produce 2:1 slopes that need the game's matching road templates, take minutes, and could make streets you are happy with look worse. If the A/B test shows any regression, ship Accurate with `straight_roads: 1` and keep `building_alignment` explicit. **Mode 0 (as mapped) is left out:** surveyed diagonals become staircase kerbs, which look bad on the game's tile grid even though positions are truest.
- **R2, `building_alignment: "real"` would look worse** (jagged walls, odd room shapes), which is why it is left out. The alignment rewrite (`settings.py:194-206`) is a silent trap for any future Portal change.
- **R3, Microsoft ML heights are noisy and count as measured.** Any height between 0 and 500 m is accepted (`overture.py:235-243`). With `max_levels` at 31, one wrong 90 m reading in a small town becomes a very tall tower that is slow to build and compile. 12 is the compromise. Raise it to 31 only for big cities with mapped towers.
- **R4, guessing the region from the place name can be wrong** (US territories, Canadian cities with real apartment blocks, Australian city centres). The override in the panel covers this.
- **R5, fill_gaps can add sheds and fake detections** where OSM is already complete (`settings.py:83`). There is no confidence filter, only a 10 m2 minimum (`overture.py:61`).
- **R6, failures fall back to OSM only without an error** (`generation.py:231-233`). Accurate could quietly produce a normal map. Portal should check that `_microsoft.json.gz` exists (it already looks at the caches, `runner.py:234-243`) and warn if it is missing.
- **R7, the town outline clip** (`runner.py:94-103`) discards Microsoft buildings outside the town boundary: in Schuylkill 3478 were added but only 2188 buildings remained after clipping. That is correct for a town map. A "full square" option would be a separate Portal choice.
- **R8, region settings change gameplay:** fewer flats means fewer tall loot buildings. That is accurate for US towns, but users should be told.

---

## 5) A/B test plan

Same place: Bardstown, KY, `town` preset, same box and outline, seed 1. Use a new `mapName` for each run so no cached OSM data is reused.

- **A (normal):** `{fill_gaps: 1}` (or none, matching what users get today)
- **B (Accurate):** the full dict above, with the North American values
- **C (isolates roads):** B but `straight_roads: 1`
- **Optional D:** B with `height_mix: "low"`

**What to compare.** Count from `<map>_buildings.geojson` and placements.csv, never from placements' `building` column.

1. **Buildings:** total count, count added by Microsoft (log "added N"), count dropped as too small or too large.
2. **Kinds:** house, apartment, shop and others. Target: under about 5% apartments in Bardstown, down from 43%.
3. **Storeys:** histogram, share of storeys from data versus guessed (log "heights from OSM"), anything above 6 storeys (check each one against satellite or Street View for R3).
4. **Street geometry, A vs C vs B:** junction positions against OSM (mean and maximum displacement in tiles), ragged staircased edges, kerbs overlapping buildings, and a visual check of 5 streets (main crossroads, a curved road, a diagonal road, a cul-de-sac, a rural road) against satellite imagery.
5. **Footprints:** take 20 random buildings and compare outline and position with satellite. Note any phantom sheds from Microsoft.
6. **Cost:** time for each step (generate, buildings, compile, pictures), output folder size, peak memory.
7. **In game (Dean does this):** walk the same three streets in A and B.

**Pass criteria:**
- B's road quality is equal to or better than A's. Otherwise ship with roads from C.
- Apartment share drops sharply.
- No absurd towers.
- Total time stays at or under 2x normal.
