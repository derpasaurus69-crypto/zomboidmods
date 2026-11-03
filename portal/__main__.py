"""python -m portal: start Portal on http://127.0.0.1:8765 and open it."""
from __future__ import annotations

import os
import threading
import webbrowser

from . import settings
from .engine.adapter import EngineAdapter
from .installer import zomboid_mods_dir
from .library import TownLibrary
from .web import create_app

PORT = 8765


def main() -> None:
    s = settings.load()
    adapter = EngineAdapter(s["knoxmap_dir"], allow_untested=s["allow_untested_engine"],
                            pz_install=s["pz_install"])
    app = create_app(adapter, TownLibrary(), zomboid_mods_dir(), settings_path=settings.default_path())
    if not os.environ.get("PORTAL_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/")).start()
    app.run(host="127.0.0.1", port=PORT, threaded=True)


if __name__ == "__main__":
    main()
