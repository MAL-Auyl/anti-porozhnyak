import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # sender | carrier | dispatcher
    created_at = Column(DateTime(timezone=True), default=_now)


class Session(Base):
    """Minimal server-issued session binding a token to a user_id.

    Not full auth — prevents trivial user_id spoofing via devtools during
    the demo (Eng review finding). Token is set as an httpOnly cookie.
    """

    __tablename__ = "sessions"

    token = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String, primary_key=True, default=_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    vehicle_type = Column(String, nullable=False)  # тент | борт | рефрижератор ...
    capacity_tons = Column(Float, nullable=False)
    origin = Column(String, nullable=False)  # location id
    destination = Column(String, nullable=False)  # location id
    departure_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="AVAILABLE")  # AVAILABLE | MATCHED | IN_TRANSIT
    created_at = Column(DateTime(timezone=True), default=_now)

    owner = relationship("User")


class Load(Base):
    __tablename__ = "loads"

    id = Column(String, primary_key=True, default=_uuid)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    origin = Column(String, nullable=False)  # location id
    destination = Column(String, nullable=False)  # location id
    cargo_type = Column(String, nullable=False)  # free text, e.g. "кирпич"
    cargo_category = Column(String, nullable=False)
    # стройматериалы | продукты | fmcg | возвратная тара | оборудование | вторсырьё | лом
    weight_tons = Column(Float, nullable=False)
    required_vehicle = Column(String, nullable=False)  # vehicle_type needed
    pickup_time = Column(DateTime(timezone=True), nullable=False)
    price_kzt = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="OPEN")  # OPEN → ACCEPTED → IN_TRANSIT → DELIVERED
    created_at = Column(DateTime(timezone=True), default=_now)

    sender = relationship("User")


class Match(Base):
    __tablename__ = "matches"

    id = Column(String, primary_key=True, default=_uuid)
    vehicle_id = Column(String, ForeignKey("vehicles.id"), nullable=False)
    load_id = Column(String, ForeignKey("loads.id"), nullable=False)
    score = Column(Float, nullable=False)
    detour_km = Column(Float, nullable=False)
    coverage_pct = Column(Float, nullable=False)
    empty_km_before = Column(Float, nullable=False, default=0.0)
    empty_km_after = Column(Float, nullable=False, default=0.0)
    empty_km_saved = Column(Float, nullable=False)
    fuel_saved_l = Column(Float, nullable=False)
    fuel_saved_kzt = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="PROPOSED")  # PROPOSED | ACCEPTED | REJECTED
    created_at = Column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        # /review finding: find_matches_for_vehicle did check-then-insert on
        # (vehicle_id, load_id) with no DB-level guard — concurrent polling
        # requests (e.g. two open tabs) could each pass the "does it exist?"
        # check before either commits, producing duplicate Match rows.
        UniqueConstraint("vehicle_id", "load_id", name="uq_match_vehicle_load"),
    )

    vehicle = relationship("Vehicle")
    load = relationship("Load")
