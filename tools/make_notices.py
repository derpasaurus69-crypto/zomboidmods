"""Write THIRD_PARTY_NOTICES.md from the licences of what Portal.exe bundles.

Run with Portal's own venv before each release: .venv\\Scripts\\python tools\\make_notices.py
"""
from __future__ import annotations

import importlib.metadata as md
import sys
from pathlib import Path

BUNDLED = ["flask", "werkzeug", "jinja2", "markupsafe", "itsdangerous", "click", "blinker",
           "colorama", "pillow"]
FENCE = "`" * 3


def licence_texts(dist: md.Distribution) -> list[str]:
    names = [f for f in dist.files or [] if any(k in str(f).lower() for k in ("licen", "copying"))]
    paths = [Path(dist.locate_file(f)) for f in names]
    return [p.read_text(encoding="utf-8", errors="replace").strip() for p in paths if p.is_file()]


def main() -> None:
    out = ["# Third-party notices", "",
           "Portal.exe is built with PyInstaller and bundles the Python runtime and the",
           "libraries below. Their licences are reproduced here as they require.",
           "PyInstaller is GPL-2.0-or-later with an exception that allows bundling",
           "programs under other licences.", "",
           "Portal does not bundle KnoxMap, Project Zomboid files or OpenStreetMap data.", ""]
    py = Path(sys.base_prefix) / "LICENSE.txt"
    out += [f"## Python {sys.version.split()[0]} (PSF License)", "", FENCE,
            py.read_text(encoding="utf-8", errors="replace").strip(), FENCE, ""]
    for name in BUNDLED:
        dist = md.distribution(name)
        texts = licence_texts(dist)
        if not texts:
            raise SystemExit(f"No licence file found for {name}")
        out += [f"## {dist.metadata['Name']} {dist.version}", "", FENCE, "\n\n".join(texts), FENCE, ""]
    Path(__file__).resolve().parent.parent.joinpath("THIRD_PARTY_NOTICES.md").write_text(
        "\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
