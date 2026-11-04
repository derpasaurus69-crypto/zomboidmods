# New York City in Project Zomboid with Portal: blueprint

Figures marked *(est.)* are estimates. The measured figures come from this PC:
- Compile speed is 0.1 min per compiled cell plus 2 min (`portal/planner.py:13-17`).
- Bardstown town is 169 cells and 185 MB.
- The PC has 31.9 GiB of RAM (about 12 GiB free when checked) and 20 threads.

Compiled-cell counts use Portal's formula `ceil(km*1000/256)+1` per side (`planner.py:34-35`).

## 1. What exists today

| Item | Status |
|---|---|
| Midtown Manhattan `city_core` (5 km, 441 compiled cells) | Being generated now. `output/portal_manhattan_new_york_city_core/settings.json` has `align_streets 1` (the map rotates about 29°), `max_levels 6` and `straight_roads 1`. |
| OSM data | `osm_source` is `auto`, so it reads the Geofabrik `us-northeast.osm.pbf` extract (`generator/osm.py:116-127`). A 1.34 GB `.part` was in `knoxmap/cache/extracts` when checked, and the extract is reused for 14 days. NYC footprints were imported into OSM. In the 5 km Midtown box, 92% of the 15,247 buildings have `height` and 12% have `building:levels` (Overpass, 2026-11-03). `fill_gaps` is not needed. |
| Placement | **It will collide.** KnoxMap does try to put each new map on free cells (`world.py:104-145`, 2-cell gap at `world.py:40`). But the installed-map regex at `world.py:91`, `.*_(\d+)_(\d+)\.lotheader`, needs a prefix, and B42 writes bare names like `82_0.lotheader`, so nothing matches. Every Portal map lands at source cell 70,0 (tile 21,000, compiled cell 82). All 4 installed Portal mods start at 82_0, Midtown will too, and `README.md:89-90` already says to enable only one at a time. |
| Height | Storeys are `floor((height − min_height)/3 m)`. `building:levels` wins when present. The result is clamped to `max_levels` (`build.py:420-447`), which is 6 here, so the Midtown towers come out at 6 storeys. Portal only sends `fill_gaps` (`runner.py:128-129`), so it cannot change `max_levels` today. |

## 2. Hard limits

| Limit | Number | Source |
|---|---|---|
| WorldEd bitmap cap | 2^28 = 268M px. That is at most 54×54 source cells of 300 tiles (16.2 km square, 262M px). | `tools/compile_map.py:344-354` |
| Render RAM | tiles² × 80 B + 150 MB. Refused above total RAM: side over about 20.7k tiles. "Tight" warning above 0.8 × free RAM: side over about 11.3k tiles with about 13 GB free. Free RAM, not total, is the practical limit. | `web/checks.py:172-236` |
| Rust compiler (knoxlots, no bitmap cap) | Not built. `cargo` is not on PATH. | `rust/knoxlots/Cargo.toml` |
| Placement range | Source cells 0..400 (`MAX_CELL`). NYC's bbox is about 47 × 49 km, which is about 158 × 164 source cells, so it fits. | `placement.py:45,117` |
| Joining separate projects | Two projects that each ship every compiled cell of their frame can only abut where lcm(300, 256) = 19,200 tiles, which is over the WorldEd cap. The only way round this is to overlap the projects and keep only the cells each one owns (§3). | `placement.py:23-24, 826-831` |
| Frame | The frame is sized from the **unrotated** lat/lon box and rounded up to 300 tiles. Rotation turns the contents inside the same frame and does not make it smaller. | `projection.py:44-60` |
| Packaging | `package()` copies **every** compiled cell of a project into one map folder. | `tools/make_map_mod.py:820-849` |
| Storeys | `max_levels` is 1..31 (B42 has levels up to 31, and the roof takes one). | `settings.py:106,239` |
| Rotation | `rotate_degrees` is −45..45. | `settings.py:228` |
| Game heap | `-Xmx3072m` by default. | `ProjectZomboid64.json` |
| Saves | Each save stores the world size. Changing the set of installed maps breaks existing saves. | `IsoMetaGrid` string "map_meta.bin world size … does not match" |
| Scale | Vanilla B42 is 4,065 cells and 4.3 GB. NYC land is about 11,900 cells *(est.)*, about 3× vanilla. The largest known community map, Project Russia, is about 4,900 B42 cells. | local count; nexusmods.com/projectzomboid/mods/139 |

One NYC map at 1 m/tile needs 47k × 49k × 80 B, about 185 GB of render RAM *(est.)*. `_beyond_this_pc` refuses it, so the city has to be split.

## 3. The plan

### Global frame
- **One projection.** All of NYC (lon −74.26 to −73.70) is in UTM 18N, EPSG:32618 (`projection.py:42-43`).
- **One rotation.** Every tile that has to join another gets `align_streets 0` and the same explicit `rotate_degrees` (do not use a measured angle).
  - **Use 0° for v1.** With a shared non-zero angle, every tile's centre has to sit on the rotated lattice, which needs a projector patch. The cost of 0° is staircased Manhattan avenues.
  - A standalone Manhattan mod may keep its own about 29°. See Phase 1.
- **One lattice.** Every tile's frame snaps to a citywide 300 m UTM grid anchored at the NW corner of NYC's bbox. This needs change #3.
- **NYC world origin.** Source cell **(90, 0)** is tile 27,000, which is inside compiled cell 105. That clears the existing Portal maps, which reach compiled x 94 (Bardstown town). NYC then spans about source x 90..248 and y 0..164 *(est.)*, within `MAX_CELL` 400.
- **Each tile's origin.** `cell_x = 90 + (min_x_m − X0)/300` and `cell_y = (Ytop − max_y_m)/300`. Portal writes it to each tile's `placement.json` with `placement.save` before `/api/buildings`.
- **Cell ownership.** A citywide map from each 256-tile compiled cell to the tile that ships it, with seams along rivers or wide streets where possible.
  - Frames of neighbouring tiles overlap, so **every** tile, including borough "islands", must ship only the cells it owns.
  - The lat/lon boxes overlap a lot. Manhattan's box takes in parts of Brooklyn, Queens, the Bronx and New Jersey.
  - Outside a drawn shape the ground is painted grass, and that grass would overwrite a neighbour's real cells.
- **Naming.** `portal_nyc_<borough>_<n>`, for example `portal_nyc_mn_1`.

### Standard tile
- 10.2 km square: 34×34 source cells, 10,200 tiles a side, 104M px.
- About 8.5 GB of render RAM *(est.)*, which keeps it under the "tight" warning when about 13 GB is free.
- 41×41 = 1,681 compiled cells to compile, about 2.8 h *(est., lower bound for dense blocks)*. With 300-tile overlap, roughly 1,500 of those cells are kept.

### How tiles join
- **Borough mods with gaps (fewest code changes).**
  - Borough maps sit at their real lattice positions. Each ships only owned cells, cut back from water edges so at least one compiled cell of water or gap is left between mods.
  - Rivers separate most boroughs, so the gap reads as water. `placement.link_design` (`placement.py:760-823`) can draw link roads across it.
  - This still needs changes #1, #3 and #6. It does **not** work today.
- **Seamless joins (prototype first).** Tiles overlap by up to 300 tiles, and each keeps only its owned cells. These can be one mod or several mods on the same lattice.
  - This is needed where boroughs share a land border (Brooklyn/Queens) and wherever a borough is bigger than one tile.
  - Expect mismatched halves and doubled walls where a building crosses a seam (`footprint.py:375-388`).
  - Whether `straight_roads` snapping puts a street in the same place on both sides is untested.

### Phases

Tile counts use the 10.2 km standard tile. The borough sizes are lat/lon extents *(est.)*.

| Phase | Scope | Tiles | Compiled cells *(est., box)* | Compile *(est.)* | Mod size *(est.)* |
|---|---|---|---|---|---|
| 0 | Midtown 5 km (running) | 1 | 441 | 46 min + download, lower bound | 0.5-1.1 GB |
| 1 | Manhattan, one project. Lat/lon box about 9.6 × 20.4 km padded north–south to about 21.9 km (210M px, about 16.9 GB RAM, "tight": close other apps). Island outline as the shape. | 1 | ~3,300 | ~5.5 h | 1.5-4 GB (most cells water or off-island) |
| 2 | Bronx (~14.5 × 14.5 km) | 4 (or 1 "tight" 15 km project) | ~3,400 | ~5.7 h | 3.5-8.5 GB |
| 3 | Brooklyn (~18 × 19 km) | 4 | ~5,300 | ~9 h | 5.5-13 GB |
| 4 | Queens (~22 × 30 km) | 9 | ~10,000 | ~17 h | 11-25 GB |
| 5 | Staten Island (~17 × 17 km) | 4 | ~4,600 | ~7.7 h | 5-11 GB |
| **Total** | Five boroughs | **~22** | ~11,900 land / ~26,600 box | **~20-45 h** | **~13-38 GB** |

Phase 1 notes:
- About 29° of rotation turns the 21.6 km island to run up the tiles. The unpadded 20.4 km frame would clip about 0.6 km off the Battery and Inwood tips (inferred from `projection.py:44-70`, not tested). Either pad the box or use 0°.
- A "21.6 × 4.8 km rotated frame" (about 1,700 cells) is **not possible** without patching `Projector.build` to size the frame after rotation.
- A Manhattan built at its own angle cannot later share seams with 0° borough tiles. It can only meet them across water gaps.

Disk:
- Each project's output in `knoxmap/output` on D: is unmeasured. Plan on about 2× the mod size *(est.)*, plus the shared extract (1.34 GB or more).
- Run tiles one at a time and clean up intermediate files after packaging.
- Packaging copies into staging first (`runner.py:171-174`), then into `Zomboid/mods` on C:, so C: needs about 2× the mod size free while installing.

## 4. Changes needed in Portal and KnoxMap

| # | Change | Where |
|---|---|---|
| 1 | **Own origin per map.** Preferred: Portal calls `placement.save(OUTPUT_DIR/name, (X,Y))` before `/api/buildings`, with no KnoxMap fork. Optional: fix the regex to accept bare names (`placement.py:188` `CELL_NAME` already does), and scan `Zomboid/Workshop` and staging as well as `mods`. | `runner.py:121-183`; `knoxbuild/world.py:91` |
| 2 | **Fixed rotation.** Send `{"align_streets":0,"rotate_degrees":θ}`. Today only `fill_gaps` is sent. | `runner.py:128-129` |
| 3 | **Shared frame.** Patch `Projector.build` in-process so `min_x_m` and `min_y_m` snap to the city lattice. A tile is then given as a lattice rectangle, not a lat/lon box. | `generator/rendering/projection.py:37-74` |
| 4 | **NYC preset.** `nyc_tile` (10.2 km). Pass `max_levels` through (12-20 suggested, 31 is the ceiling), keep `fill_gaps` off and `osm_source` on `auto`/extract. | `portal/planner.py`; `knoxbuild/settings.py:239,262-280` |
| 5 | **Batch runner.** A `nyc_tiles.json` manifest (origins, ownership map, frozen boundaries) and a `portal nyc` command. It runs one tile at a time, can resume, logs minutes and MB per cell, and cleans up. | new, in `portal/engine/runner.py` |
| 6 | **Ownership-filtered packaging.** Ship only owned cells, and merge spawnpoints, `objects.lua`, `worldmap.xml` and `streets.xml`. Every multi-tile or adjacent mod needs this. | `tools/make_map_mod.py:820-849` (copies all cells today) |
| 7 | **Optional: build knoxlots (Rust).** Removes the 268M-px cap. Install `cargo`. Untested on merged projects. | `rust/knoxlots` |

## 5. Gameplay concerns

- **Skyscrapers.**
  - At 31 storeys, the Empire State Building (about 381 m, about 127 storeys) loses about 75% of its height.
  - Every storey is fully furnished. Office cores are only used for `civic` buildings of 12+ storeys whose short side is at least 14 tiles (`tower.py:13-30`).
  - Build time and MB per cell grow with storey count, so treat 12-20 as the practical setting.
- **Big footprints.** Footprints over `max_size` (200 tiles) are cut into adjoining units (`settings.py:100-104`). Examples are the Javits Center and Penn Station/MSG.
- **Bridges and tunnels.**
  - A bridge that crosses only water becomes a flat road at ground level (`structures.py:1-20`).
  - Tunnel and underground features are dropped (`osm.py:1228-1274`), so the Holland and Lincoln tunnels and the FDR's underground sections disappear.
  - `railway=subway` is not fetched (`osm.py:363-371`), so there is no subway and no elevated 7 line. Piers are kept.
- **Trees.** Mapped tree nodes are not fetched. Central Park's trees come from `tree_density` fill (`osm.py:359-376`).
- **Load time and RAM.** Every installed lotheader's building and room data is loaded at startup. Players will need `-Xmx` around 8-16 GB *(est.)*. Midtown gives the first real data point: the "IsoMetaGrid.Create … finished loading" line in `console.txt`, plus heap use.
- **Multiplayer and saves.** The server and every client need the identical set of mods. Origins, the ownership map and mod boundaries must be frozen before anyone starts a save. A fully explored cell adds about 5.5 MB to a save *(est.)*. Whether Steam Workshop caps item size is unverified.

## 6. Risks and open questions

- **Seams.** Road snapping across a seam is untested and needs a two-tile test.
- **Cell costs.** Compile time and size for all-water or empty cells are unmeasured. Bardstown's rates may overstate water cells and understate dense Midtown.
- **Duplicate cells.** "Whichever the game reads second wins" (`placement.py:829`) is not checked in-game. The ownership filter avoids depending on it.
- **Empty world space.** How B42 handles a world bounding box out to compiled x of about 290 is inferred from constant-pool strings only.
- **Free RAM.** Phase 1 and any project over about 11k tiles a side depend on how much RAM is free at run time, not on the 32 GB total.
- **knoxlots.** Untested on a merged multi-project map.
- **Midtown.** The running Midtown map is expected to land at 82_0 (not yet confirmed).

## 7. Recommended next 3 steps

1. **Before enabling Midtown alongside the other Portal maps,** move it with `placement.move` and recompile. The regex fix alone does not move a map that is already built. Then record its real compile minutes per cell, MB per cell, heap use and load time.
2. **Add changes 1, 2, 3 and 4 to Portal.** Then build two overlapping 1 km tiles in Midtown at 0° with a prototype of change 6, to measure seam quality.
3. **Build Phase 1 (Manhattan, padded box, outline shape) at the NYC lattice position.** Freeze the origin, the ownership map and the borough boundaries in `nyc_tiles.json` before anyone plays on it.

