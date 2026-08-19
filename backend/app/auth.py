"""Minimal server-issued session binding (Eng review finding).

Not full auth — the plan explicitly cuts SMS/OTP registration in favor of a
"login as role" button. Without any server-side binding, a user could PATCH
any resource as any user_id via devtools during the demo. This gives just
enough binding to prevent that trivial spoof: on role selection, the server
issues a session token tied to the created user_id and sets it as an
httpOnly cookie. Every mutating endpoint resolves the acting user from this
cookie instead of trusting a client-supplied user_id.
"""

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.models import Session as SessionModel
from app.models.models import User

SESSION_COOKIE_NAME = "porozhnyak_session"


def get_current_user(
    porozhnyak_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: DBSession = Depends(get_db),
) -> User:
    if not porozhnyak_session:
        raise HTTPException(status_code=401, detail="Не авторизован — войдите как роль")
    session = db.get(SessionModel, porozhnyak_session)
    if session is None:
        raise HTTPException(status_code=401, detail="Сессия недействительна")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user
