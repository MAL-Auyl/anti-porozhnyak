from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.models import Load, Match, Vehicle
from app.schemas.schemas import EmptyStateReason, MatchExplanation, MatchOut
from app.services.economics import compute_economics
from app.services.matching import MAX_ACCEPTABLE_DETOUR_KM, compute_route_metrics, score_match

router = APIRouter(tags=["matches"])

MIN_SCORE_TO_SURFACE = 30.0  # below this, not worth showing as a suggestion


def _hours_offset(dt: datetime) -> float:
    epoch = datetime(2026, 8, 19, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - epoch).total_seconds() / 3600.0


@router.get("/vehicles/{vehicle_id}/matches")
def find_matches_for_vehicle(vehicle_id: str, db: DBSession = Depends(get_db)):
    """Computes + persists matches for a vehicle against all OPEN loads.

    Persisting to the `matches` table (not just returning computed JSON) is
    intentional per plan.md: "matches должна реально существовать в БД — на
    защите это доказательство, что матчинг не анимация на фронте."

    Empty result is a realistic, expected outcome given the region's cargo
    asymmetry (Design review) — returns an explicit reason, not just [].
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Машина не найдена")

    open_loads = db.query(Load).filter(Load.status == "OPEN").all()
    total_trips = db.query(Load).count()

    scored: list[tuple[Load, float, dict]] = []
    for load in open_loads:
        metrics = compute_route_metrics(vehicle.origin, vehicle.destination, load.origin, load.destination)
        econ = compute_economics(metrics)
        breakdown = score_match(
            metrics=metrics,
            vehicle_type=vehicle.vehicle_type,
            required_vehicle=load.required_vehicle,
            departure_time_hours_offset=_hours_offset(vehicle.departure_time),
            pickup_time_hours_offset=_hours_offset(load.pickup_time),
            empty_km_saved=econ.empty_km_saved,
        )
        # Hard corridor gate: coverage_pct is a length ratio (dist_cd/dist_ab)
        # with no notion of direction, so a load whose own leg happens to be
        # long can hit 100% coverage while requiring a huge, unrelated detour
        # (found via live smoke test: 389-996km detours scoring 60+ because
        # coverage/compatibility/time still summed to a lot). "Лежит внутри
        # коридора" must be a gate, not just a soft-weighted component.
        if metrics.detour_km > MAX_ACCEPTABLE_DETOUR_KM:
            continue
        if breakdown.total >= MIN_SCORE_TO_SURFACE:
            scored.append((load, breakdown.total, {"metrics": metrics, "econ": econ, "breakdown": breakdown}))

    scored.sort(key=lambda t: t[1], reverse=True)

    if not scored:
        return {
            "matches": [],
            "empty_state": EmptyStateReason(
                message=(
                    "Подходящий груз пока не найден. Это ожидаемо при "
                    "асимметричном грузопотоке региона — попробуйте позже "
                    "или измените маршрут."
                ),
                trips_in_database=total_trips,
            ),
        }

    results = []
    for load, score, data in scored[:5]:
        existing = (
            db.query(Match)
            .filter(Match.vehicle_id == vehicle_id, Match.load_id == load.id)
            .first()
        )
        if existing is None:
            existing = Match(vehicle_id=vehicle_id, load_id=load.id)
            db.add(existing)

        existing.score = score
        existing.detour_km = round(data["metrics"].detour_km, 1)
        existing.coverage_pct = round(data["metrics"].coverage_pct, 1)
        existing.empty_km_saved = data["econ"].empty_km_saved
        existing.fuel_saved_l = data["econ"].fuel_saved_l
        existing.fuel_saved_kzt = data["econ"].fuel_saved_kzt
        db.flush()
        results.append(existing)

    db.commit()
    for r in results:
        db.refresh(r)

    return {"matches": [MatchOut.model_validate(r) for r in results], "empty_state": None}


@router.get("/matches/{match_id}/explain", response_model=MatchExplanation)
def explain_match(match_id: str, db: DBSession = Depends(get_db)):
    """"Почему этот груз?" breakdown — recomputed from the same
    compute_route_metrics() call that produced the persisted Match row, so
    numbers can never diverge."""
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Совпадение не найдено")
    vehicle = db.get(Vehicle, match.vehicle_id)
    load = db.get(Load, match.load_id)

    metrics = compute_route_metrics(vehicle.origin, vehicle.destination, load.origin, load.destination)
    econ = compute_economics(metrics)
    breakdown = score_match(
        metrics=metrics,
        vehicle_type=vehicle.vehicle_type,
        required_vehicle=load.required_vehicle,
        departure_time_hours_offset=_hours_offset(vehicle.departure_time),
        pickup_time_hours_offset=_hours_offset(load.pickup_time),
        empty_km_saved=econ.empty_km_saved,
    )
    return MatchExplanation(
        coverage_pct=round(metrics.coverage_pct, 1),
        detour_km=round(metrics.detour_km, 1),
        compatibility_ok=vehicle.vehicle_type == load.required_vehicle,
        time_window_ok=breakdown.time_window_score >= 50,
        score_breakdown=breakdown.__dict__,
    )


@router.post("/matches/{match_id}/accept", response_model=MatchOut)
def accept_match(match_id: str, db: DBSession = Depends(get_db)):
    """Atomic accept (Eng review — race condition fix).

    Two carriers polling every 2s could both see status=OPEN and both click
    accept. This uses an UPDATE ... WHERE status='OPEN' guard and checks
    affected row count instead of read-then-write, so only one wins; the
    second gets an explicit 409, not a silent overwrite.
    """
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Совпадение не найдено")

    result = db.execute(
        text("UPDATE loads SET status = 'ACCEPTED' WHERE id = :load_id AND status = 'OPEN'"),
        {"load_id": match.load_id},
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Этот груз уже взят другим перевозчиком")

    match.status = "ACCEPTED"
    vehicle = db.get(Vehicle, match.vehicle_id)
    vehicle.status = "MATCHED"
    db.commit()
    db.refresh(match)
    return match


@router.get("/matches", response_model=list[MatchOut])
def list_all_matches(db: DBSession = Depends(get_db)):
    """Dispatcher view — read-only list of all matches + statuses, same
    polling model as everything else (Design review: closes requirement 05,
    'диспетчер отслеживает')."""
    return db.query(Match).order_by(Match.created_at.desc()).all()
