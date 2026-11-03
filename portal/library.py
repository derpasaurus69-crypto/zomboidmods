"""The towns Portal has generated, so the same one plays again instantly."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .model import Town


def default_index() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Portal" / "library.json"


class TownLibrary:
    def __init__(self, index_path: Path | None = None) -> None:
        self.path = Path(index_path or default_index())
        self._towns = self._load()

    def _load(self) -> dict[str, Town]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return {d["mod_id"]: Town.from_dict(d) for d in raw["towns"]}
        except (ValueError, KeyError, TypeError):
            # Kept for a bug report rather than thrown away.
            os.replace(self.path, self.path.with_name(self.path.name + ".bad"))
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps({"towns": [t.to_dict() for t in self._towns.values()]},
                                  indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def get(self, mod_id: str) -> Town | None:
        return self._towns.get(mod_id)

    def put(self, town: Town) -> None:
        self._towns[town.mod_id] = town
        self._save()

    def list(self) -> list[Town]:
        return sorted(self._towns.values(), key=lambda t: t.created, reverse=True)

    def set_workshop_id(self, mod_id: str, workshop_id: str) -> None:
        self._towns[mod_id].workshop_id = workshop_id
        self._save()
