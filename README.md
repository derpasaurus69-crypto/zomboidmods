# Portal

Type a real place, play it in Project Zomboid (Build 42).

Portal is a small Windows app on top of [KnoxMap](https://github.com/spytheeuclidean-a11y/knoxmap),
which turns OpenStreetMap data into a compiled, furnished PZ map. Portal adds the
Infection Free Zone-style flow: search a place, pick a size, press **Generate & Play**,
and the town is installed as a mod. It also lays out a generated town for the
Steam Workshop uploader.

## Needs

- Project Zomboid on Build 42
- KnoxMap 1.8.4, set up with its own `Setup.bat` (Portal never installs or bundles it)
- Windows

## Run

```bash
.venv\Scripts\python -m portal
```

It opens <http://127.0.0.1:8765/>. Settings live in `%LOCALAPPDATA%\Portal\settings.json`:

| key | default |
|---|---|
| `knoxmap_dir` | `D:\modding\pz-portal-engine\knoxmap` |
| `allow_untested_engine` | `false` |
| `pz_install` | unset (KnoxMap finds the game itself) |

## Sizes

| Preset | Area | Compiled cells | Time on the dev PC |
|---|---|---|---|
| Downtown | 1 km² | 25 | ~3–5 min |
| Town | ~9 km², clipped to the real outline | ≤169 | longer |
| City core | ~25 km² | ≤441 | needs a strong PC |

## After generating

1. Launch Project Zomboid, enable the town under **Mods**.
2. **New Game**, choose the town as the spawn. A map can only be added to a new world.

## Publishing

**Publish to Workshop…** writes `%USERPROFILE%\Zomboid\Workshop\<mod id>` with
`workshop.txt` (unlisted by default), `preview.png` and the mod. Upload it from
Project Zomboid: **Workshop → Create and Upload**.

## Tests

```bash
.venv\Scripts\python -m pytest
```

The slow test against the real KnoxMap (needs the game and network):

```bash
.venv\Scripts\python -m pytest -m engine
```

## Credits

Map data © OpenStreetMap contributors (ODbL). Maps are built by KnoxMap (euclid80tr).
