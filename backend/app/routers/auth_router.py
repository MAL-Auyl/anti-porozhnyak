from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session as DBSession

from app.auth import SESSION_COOKIE_NAME
from app.database import get_db
from app.models.models import Session as SessionModel
from app.models.models import User
from app.schemas.schemas import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

ROLES = {"sender", "carrier", "dispatcher"}


@router.post("/login", response_model=UserOut)
def login_as_role(body: UserCreate, response: Response, db: DBSession = Depends(get_db)):
    """"Login as <role>" button. Creates a fresh user + session, no password.

    Deliberate MVP tradeoff (plan.md, cut list) — but binds the session
    cookie server-side so the acting user can't be spoofed via devtools.
    """
    if body.role not in ROLES:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"role must be one of {ROLES}")

    user = User(name=body.name, role=body.role)
    db.add(user)
    db.flush()

    session = SessionModel(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(user)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    return user
