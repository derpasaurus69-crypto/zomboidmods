"""One generation at a time, run on a thread the web page polls."""
from __future__ import annotations

import shutil
import threading
from datetime import datetime
from pathlib import Path

from . import ids, installer
from .engine.adapter import EngineAdapter, EngineCancelled, EngineError
from .library import TownLibrary
from .model import AreaPlan, Town


class Busy(Exception):
    pass


class JobRunner:
    def __init__(self, adapter: EngineAdapter, library: TownLibrary, mods_dir: Path) -> None:
        self.adapter, self.library, self.mods_dir = adapter, library, Path(mods_dir)
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._status: dict = {"state": "idle", "pct": 0, "step": "", "message": "", "mod_id": None}

    def status(self) -> dict:
        with self._lock:
            return dict(self._status)

    def _set(self, **fields) -> None:
        with self._lock:
            self._status.update(fields)

    def start(self, plan: AreaPlan) -> str:
        with self._lock:
            if self._status["state"] == "running":
                raise Busy("A map is already being made.")
            mod = ids.mod_id(plan.place, plan.preset)
            self._status = {"state": "running", "pct": 0, "step": "", "message": "Starting",
                            "mod_id": mod}
        self._cancel.clear()
        threading.Thread(target=self._run, args=(plan, mod), daemon=True).start()
        return mod

    def cancel(self) -> None:
        self._cancel.set()

    def wait(self, timeout: float = 60) -> dict:
        """For tests and the command line: block until the job is not running."""
        import time
        end = time.time() + timeout
        while self.status()["state"] == "running" and time.time() < end:
            time.sleep(0.1)
        return self.status()

    def _keep(self, path: str | None, kind: str, name: str) -> str | None:
        """Move a file out of staging into Portal's own folder, beside the library."""
        if not path or not Path(path).exists():
            return None
        folder = self.library.path.parent / kind
        folder.mkdir(parents=True, exist_ok=True)
        return str(shutil.move(path, folder / name))

    def _run(self, plan: AreaPlan, mod: str) -> None:
        name = ids.title(plan.place, plan.preset)
        try:
            for p in self.adapter.generate(plan, mod, installer.staging_dir(self.mods_dir),
                                           name, self._cancel):
                self._set(pct=p.pct, step=p.step, message=p.message)
            result = self.adapter.last_result
            target = installer.install(Path(result["mod_dir"]), self.mods_dir)
            preview = self._keep(result.get("preview"), "previews", f"{mod}.png")
            self._keep(str(installer.staging_dir(self.mods_dir) / f"{mod}.engine.log"),
                       "logs", f"{mod}.engine.log")
            self.library.put(Town(mod_id=mod, title=name, place_key=ids.place_key(plan.place),
                                  preset=plan.preset,
                                  engine_version=self.adapter.check().version or "",
                                  mod_dir=str(target), preview=preview,
                                  workshop_id=getattr(self.library.get(mod), "workshop_id", None),
                                  created=datetime.now().isoformat(timespec="seconds"),
                                  extra_buildings=tuple(result.get("extra_buildings") or ())))
            self._set(state="done", pct=100, message="Installed")
        except EngineCancelled:
            self._set(state="cancelled", message="Cancelled")
        except (EngineError, installer.ForeignModError, ValueError, OSError) as exc:
            self._set(state="error", message=str(exc))
