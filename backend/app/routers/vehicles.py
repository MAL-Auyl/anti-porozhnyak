from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.auth import get_current_user
from app.database import get_db
from app.models.models import User, Vehicle
from app.schemas.schemas import VehicleCreate, VehicleOut

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("", response_model=VehicleOut)
def create_vehicle(
    body: VehicleCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    vehicle = Vehicle(owner_id=user.id, **body.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleOut])
def list_vehicles(db: DBSession = Depends(get_db)):
    return db.query(Vehicle).order_by(Vehicle.created_at.desc()).all()


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: str, db: DBSession = Depends(get_db)):
    from fastapi import HTTPException

    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Машина не найдена")
    return vehicle
