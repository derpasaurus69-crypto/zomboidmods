"""Portal's window: a page on localhost, and the API it calls."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from . import ids, planner, publisher
from .engine.adapter import EngineAdapter, EngineError
from .jobs import Busy, JobRunner
from .library import TownLibrary
from .model import Place

LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}
PRESET_ORDER = list(planner.PRESETS)


def create_app(adapter: EngineAdapter, library: TownLibrary, mods_dir: Path,
               workshop_root: Path | None = None, launcher=None) -> Flask:
    app = Flask(__name__)
    jobs = JobRunner(adapter, library, mods_dir)
    app.config["jobs"] = jobs
    workshop_root = Path(workshop_root or publisher.workshop_root())
    launch = launcher or (lambda: os.startfile("steam://rungameid/108600"))

    @app.before_request
    def local_only():
        # Same rule as KnoxMap: a page elsewhere pointing a hostname at us is refused.
        if request.host.rsplit(":", 1)[0] not in LOCAL_HOSTS:
            return jsonify({"error": "Portal only answers this PC."}), 403

    def plan_from_body():
        body = request.get_json(silent=True) or {}
        return planner.plan(Place.from_dict(body["place"]), body["preset"])

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/engine")
    def engine():
        s = adapter.check()
        return jsonify({"ok": s.ok, "version": s.version, "problem": s.problem})

    @app.get("/api/search")
    def search():
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"results": []})
        try:
            return jsonify({"results": [p.to_dict() for p in adapter.search(q)]})
        except EngineError as exc:
            return jsonify({"error": str(exc)}), 502

    @app.post("/api/plan")
    def plan():
        p = plan_from_body()
        try:
            estimate = adapter.estimate(p)
        except EngineError as exc:
            estimate = {"tight": None, "impossible": None, "error": str(exc)}
        mod = ids.mod_id(p.place, p.preset)
        return jsonify({"plan": p.to_dict(), "mod_id": mod, "title": ids.title(p.place),
                        "estimate": estimate, "existing": library.get(mod) is not None})

    @app.post("/api/generate")
    def generate():
        p = plan_from_body()
        impossible = adapter.estimate(p).get("impossible")
        if impossible:
            i = PRESET_ORDER.index(p.preset)
            smaller = f" Try the {PRESET_ORDER[i - 1].replace('_', ' ')} size." if i else ""
            return jsonify({"error": impossible + smaller}), 400
        try:
            return jsonify({"mod_id": jobs.start(p)})
        except Busy as exc:
            return jsonify({"error": str(exc)}), 409

    @app.get("/api/job")
    def job():
        return jsonify(jobs.status())

    @app.post("/api/cancel")
    def cancel():
        jobs.cancel()
        return jsonify({"ok": True})

    @app.get("/api/towns")
    def towns():
        return jsonify({"towns": [t.to_dict() for t in library.list()]})

    @app.post("/api/publish")
    def publish():
        town = library.get((request.get_json(silent=True) or {}).get("mod_id", ""))
        if town is None:
            return jsonify({"error": "Unknown town."}), 404
        folder = publisher.prepare(town, workshop_root)
        return jsonify({"folder": str(folder), "reminder": publisher.REMINDER})

    @app.post("/api/launch")
    def launch_game():
        launch()
        return jsonify({"ok": True})

    return app
