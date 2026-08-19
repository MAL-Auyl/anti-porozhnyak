import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth_router, loads, matches, vehicles

app = FastAPI(title="Anti-Порожняк API")

# Bug found by /qa (browser CORS error on every login attempt): `["*"]`
# combined with allow_credentials=True is rejected by the CORS spec once a
# fetch sends credentials (our session cookie always does) — the browser
# refuses the response outright, no request ever reaches auth.py. Must be
# an explicit origin list, not a wildcard, whenever credentials are used.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    *[o for o in os.getenv("FRONTEND_ORIGIN", "").split(",") if o],
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(vehicles.router)
app.include_router(loads.router)
app.include_router(matches.router)


@app.on_event("startup")
def on_startup():
    # Best-effort: in tests the DB dependency is overridden per-request via
    # a separate in-memory engine, so this module-level `engine` (pointing
    # at DATABASE_URL) may not be reachable — that's fine, don't crash boot.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:  # pragma: no cover
        print(f"WARNING: could not create tables on startup: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}
