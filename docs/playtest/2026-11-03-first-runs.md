# First runs — 2026-11-03

KnoxMap 1.8.4, Project Zomboid 42 (Steam build 25485521), Dean's PC.

| Run | How | Cells | Time | Result |
|---|---|---|---|---|
| Bardstown, Kentucky — downtown | spike driver | 25 | 3.2 min | installed, 31 MB; 854 buildings, 113 named streets, 8 spawn points |
| Ürgüp, Central Anatolia Region — downtown | Portal UI, browser | 25 | 11.5 min (9 min OSM download) | installed, 26 MB; Workshop folder prepared |
| Bardstown, Kentucky — town | Portal.exe API | 169 | 16.3 min | installed, 185 MB |

![Bardstown town](bardstown-town.png)

![Ürgüp downtown](urgup-downtown.png)

## Checked

- Dedicated server (`-nosteam`, `Zomboid/Server/portaltest.ini`) booted with the Bardstown
  downtown mod and `Map=Bardstown, Kentucky Portal spike;Muldraugh, KY`: `SERVER STARTED`,
  no SEVERE lines or exceptions. Its log only samples 24 lot loads, so it does not prove
  our cells were read.
- Previews are KnoxMap's render of the compiled lots: real street grid, rail line, campus.

## Not checked yet (needs the game client)

- Spawning into the town from New Game; streets and buildings in place.
- Loot in shops matching their type; world map street names.
- Whether `town` really followed Bardstown's outline (the preview fills the whole square).
- Multiplayer.

## Bugs found and fixed on the way

- Postcodes ("50400") were taken as the region in IDs and titles.
- Previews and engine logs were left in the staging folder.
- A damaged preview image crashed Publish.
