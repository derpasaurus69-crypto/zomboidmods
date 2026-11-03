"""The only Portal code that starts KnoxMap or reads what it says."""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

from ..model import AreaPlan, EngineStatus, Place, Progress
from .protocol import decode

RUNNER = Path(__file__).with_name("runner.py")
TESTED_VERSIONS = frozenset({"1.8.4"})
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class EngineError(Exception):
    pass


class EngineCancelled(EngineError):
    pass


class EngineAdapter:
    def __init__(self, knoxmap_dir: Path, tested_versions: frozenset[str] = TESTED_VERSIONS,
                 allow_untested: bool = False, python: Path | None = None,
                 runner: Path | None = None, pz_install: str | None = None) -> None:
        self.knoxmap_dir = Path(knoxmap_dir)
        self.tested_versions = tested_versions
        self.allow_untested = allow_untested
        self.python = Path(python) if python else self.knoxmap_dir / ".venv" / "Scripts" / "python.exe"
        self.runner = Path(runner or RUNNER)
        self.pz_install = pz_install
        self.last_result: dict = {}

    # ---- the process ----------------------------------------------------------

    def _start(self, command: str, args: dict, stderr) -> subprocess.Popen:
        env = {**os.environ, "PYTHONUTF8": "1", "KNOXMAP_DIR": str(self.knoxmap_dir)}
        if self.pz_install:
            env["PZ_INSTALL"] = self.pz_install
        return subprocess.Popen([str(self.python), "-u", str(self.runner), command, json.dumps(args)],
                                stdout=subprocess.PIPE, stderr=stderr, env=env,
                                text=True, encoding="utf-8", errors="replace",
                                creationflags=NO_WINDOW)

    def _events(self, proc: subprocess.Popen, cancel: threading.Event | None) -> Iterator[dict]:
        lines: queue.Queue[str | None] = queue.Queue()

        def read() -> None:
            for line in proc.stdout:
                lines.put(line)
            lines.put(None)

        threading.Thread(target=read, daemon=True).start()
        while True:
            if cancel is not None and cancel.is_set():
                kill_tree(proc)
                raise EngineCancelled("Cancelled.")
            try:
                line = lines.get(timeout=0.2)
            except queue.Empty:
                continue
            if line is None:
                break
            event = decode(line.strip())
            if event is not None:
                yield event
        proc.wait()

    def _call(self, command: str, args: dict) -> dict:
        if not self.python.exists():
            raise EngineError(self._missing())
        proc = self._start(command, args, subprocess.DEVNULL)
        for event in self._events(proc, None):
            if event["event"] == "error":
                raise EngineError(event["message"])
            if event["event"] == "result":
                return event
        raise EngineError(f"KnoxMap stopped without an answer to '{command}'.")

    def _missing(self) -> str:
        return (f"KnoxMap was not found at {self.knoxmap_dir}. Install KnoxMap "
                "(github.com/spytheeuclidean-a11y/knoxmap) and run its Setup, then "
                "point Portal at its folder in Settings.")

    # ---- what Portal asks for --------------------------------------------------

    def check(self) -> EngineStatus:
        if not self.python.exists():
            return EngineStatus(False, None, self._missing())
        try:
            r = self._call("check", {})
        except EngineError as exc:
            return EngineStatus(False, None, str(exc))
        version = r.get("version")
        if not r.get("build42"):
            return EngineStatus(False, version, "Project Zomboid is not on Build 42. In Steam: "
                                "Properties > Betas, pick the Build 42 branch, let it update.")
        if version not in self.tested_versions and not self.allow_untested:
            return EngineStatus(False, version,
                                f"KnoxMap {version} has not been tested with Portal. "
                                f"Supported: {', '.join(sorted(self.tested_versions))}.")
        return EngineStatus(True, version, None)

    def search(self, q: str) -> list[Place]:
        return [Place.from_knoxmap(d) for d in self._call("search", {"q": q}).get("results", [])]

    def estimate(self, plan: AreaPlan) -> dict:
        r = self._call("estimate", {"plan": plan.to_dict()})
        return {"tight": r.get("tight"), "impossible": r.get("impossible")}

    def generate(self, plan: AreaPlan, map_name: str, staging_dir: Path, title: str,
                 cancel: threading.Event) -> Iterator[Progress]:
        status = self.check()
        if not status.ok:
            raise EngineError(status.problem)
        staging_dir = Path(staging_dir)
        staging_dir.mkdir(parents=True, exist_ok=True)
        self.last_result = {}
        with open(staging_dir / f"{map_name}.engine.log", "w", encoding="utf-8") as log:
            proc = self._start("generate", {"plan": plan.to_dict(), "map_name": map_name,
                                            "staging_dir": str(staging_dir), "title": title}, log)
            try:
                for event in self._events(proc, cancel):
                    if event["event"] == "progress":
                        yield Progress(event["step"], float(event["pct"]), event.get("message", ""))
                    elif event["event"] == "error":
                        raise EngineError(event["message"])
                    elif event["event"] == "result":
                        self.last_result = event
            except EngineCancelled:
                shutil.rmtree(staging_dir / map_name, ignore_errors=True)
                raise
        if not self.last_result:
            raise EngineError("KnoxMap stopped before the map was finished; see the engine log.")


def kill_tree(proc: subprocess.Popen) -> None:
    """KnoxMap's compile runs PZWorldEd_cli.exe children: take them all."""
    if proc.poll() is None:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, creationflags=NO_WINDOW)
        proc.wait(timeout=10)
