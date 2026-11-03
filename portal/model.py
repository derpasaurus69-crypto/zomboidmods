"""The records Portal passes between its parts."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Place:
    name: str
    display_name: str
    lat: float
    lon: float
    bbox: tuple[float, float, float, float]  # south, west, north, east
    kind: str
    outline: dict | None  # GeoJSON Polygon/MultiPolygon, when the search has one

    @classmethod
    def from_knoxmap(cls, d: dict) -> "Place":
        return cls(name=d.get("name") or "", display_name=d.get("display_name") or "",
                   lat=float(d["lat"]), lon=float(d["lon"]),
                   bbox=tuple(float(v) for v in d["bbox"]),
                   kind=d.get("type") or d.get("category") or "",
                   outline=d.get("outline"))

    def to_dict(self) -> dict:
        return {**asdict(self), "bbox": list(self.bbox)}

    @classmethod
    def from_dict(cls, d: dict) -> "Place":
        return cls(**{**d, "bbox": tuple(d["bbox"])})


@dataclass(frozen=True)
class AreaPlan:
    place: Place
    preset: str
    side_km: float
    cells: int
    est_minutes: int
    spawn: dict | None = None  # {"lat", "lon", "label"}: start here instead of near the centre

    def to_dict(self) -> dict:
        return {**asdict(self), "place": self.place.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "AreaPlan":
        return cls(**{**d, "place": Place.from_dict(d["place"])})


@dataclass(frozen=True)
class Progress:
    step: str
    pct: float
    message: str


@dataclass(frozen=True)
class EngineStatus:
    ok: bool
    version: str | None
    problem: str | None


@dataclass
class Town:
    mod_id: str
    title: str
    place_key: str
    preset: str
    engine_version: str
    mod_dir: str
    preview: str | None
    workshop_id: str | None
    created: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Town":
        return cls(**d)
