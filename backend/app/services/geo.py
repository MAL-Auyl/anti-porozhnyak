"""Static region data: 10 nodes + symmetric distance matrix.

Loaded once at import time from data/locations.json and data/routes.json
(repo root /data). Per plan.md: "матрица расстояний в JSON, не источник
вычислений через PostGIS" — this is intentionally not a DB table.
"""

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@lru_cache(maxsize=1)
def load_locations() -> dict[str, dict]:
    with open(DATA_DIR / "locations.json", encoding="utf-8") as f:
        locs = json.load(f)
    return {loc["id"]: loc for loc in locs}


@lru_cache(maxsize=1)
def _distance_index() -> dict[tuple[str, str], dict]:
    with open(DATA_DIR / "routes.json", encoding="utf-8") as f:
        routes = json.load(f)
    index: dict[tuple[str, str], dict] = {}
    for r in routes:
        index[(r["from"], r["to"])] = r
        index[(r["to"], r["from"])] = r  # matrix is symmetric by construction
    return index


def distance_km(a: str, b: str) -> float:
    """Distance between two location ids. 0 if a == b (same node)."""
    if a == b:
        return 0.0
    route = _distance_index().get((a, b))
    if route is None:
        raise ValueError(f"No route data between '{a}' and '{b}'")
    return route["distance_km"]


def location_name(loc_id: str) -> str:
    loc = load_locations().get(loc_id)
    return loc["name"] if loc else loc_id
