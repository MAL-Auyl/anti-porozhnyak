from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.auth import get_current_user
from app.database import get_db
from app.models.models import Load, User
from app.schemas.schemas import LoadCreate, LoadOut, ParseRequest
from app.services.llm_parser import ParseResult, parse_load_request_cached

router = APIRouter(prefix="/loads", tags=["loads"])


@router.post("/parse", response_model=ParseResult)
def parse_load(body: ParseRequest, user: User = Depends(get_current_user)):
    """Free-text -> structured draft. Frontend shows the draft for
    confirmation before POST /loads actually creates it (plan.md: 'Пользователь
    подтверждает -> заявка создана'). Never 500s on bad LLM output — see
    llm_parser.py docstring."""
    return parse_load_request_cached(body.text)


@router.post("", response_model=LoadOut)
def create_load(
    body: LoadCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    load = Load(sender_id=user.id, **body.model_dump())
    db.add(load)
    db.commit()
    db.refresh(load)
    return load


@router.get("", response_model=list[LoadOut])
def list_loads(status: str | None = None, db: DBSession = Depends(get_db)):
    q = db.query(Load)
    if status:
        q = q.filter(Load.status == status)
    return q.order_by(Load.created_at.desc()).all()


@router.get("/{load_id}", response_model=LoadOut)
def get_load(load_id: str, db: DBSession = Depends(get_db)):
    load = db.get(Load, load_id)
    if load is None:
        raise HTTPException(status_code=404, detail="Груз не найден")
    return load


@router.post("/{load_id}/deliver", response_model=LoadOut)
def mark_delivered(load_id: str, db: DBSession = Depends(get_db)):
    """One-click, instant transition (Design review finding — no live
    computation in this call; the "search for return load" step is a
    separate GET /vehicles/{id}/matches call the frontend triggers right
    after, using the cached/instant matching endpoint)."""
    load = db.get(Load, load_id)
    if load is None:
        raise HTTPException(status_code=404, detail="Груз не найден")
    load.status = "DELIVERED"
    db.commit()
    db.refresh(load)
    return load
