from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    name: str
    role: str  # sender | carrier | dispatcher


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    role: str


class VehicleCreate(BaseModel):
    vehicle_type: str
    capacity_tons: float
    origin: str
    destination: str
    departure_time: datetime


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    owner_id: str
    vehicle_type: str
    capacity_tons: float
    origin: str
    destination: str
    departure_time: datetime
    status: str


class LoadCreate(BaseModel):
    origin: str
    destination: str
    cargo_type: str
    cargo_category: str
    weight_tons: float
    required_vehicle: str
    pickup_time: datetime
    price_kzt: float


class LoadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    sender_id: str
    origin: str
    destination: str
    cargo_type: str
    cargo_category: str
    weight_tons: float
    required_vehicle: str
    pickup_time: datetime
    price_kzt: float
    status: str


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    vehicle_id: str
    load_id: str
    score: float
    detour_km: float
    coverage_pct: float
    empty_km_saved: float
    fuel_saved_l: float
    fuel_saved_kzt: float
    status: str


class MatchExplanation(BaseModel):
    """The "Почему этот груз?" breakdown — same numbers as MatchOut,
    computed from the same compute_route_metrics() call, never re-derived."""

    coverage_pct: float
    detour_km: float
    compatibility_ok: bool
    time_window_ok: bool
    score_breakdown: dict


class ParseRequest(BaseModel):
    text: str


class EmptyStateReason(BaseModel):
    """Explicit empty-match explanation (Design review: not an edge case,
    a realistic outcome given the region's cargo-flow asymmetry)."""

    message: str
    trips_in_database: int
