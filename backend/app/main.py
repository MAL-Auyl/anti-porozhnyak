from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth_router, loads, matches, vehicles

app = FastAPI(title="Anti-Порожняк API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon MVP — tighten if time remains
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
