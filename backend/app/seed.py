"""Seed 40 trips with realistic asymmetry, including a guaranteed dataset
for the exact 60-second demo scenario (plan.md: "Пустая база на демо убивает
проект" — never rely on random generation for the pitch moment).

Run: python -m app.seed  (from backend/, with DATABASE_URL set)
"""

import random
from datetime import datetime, timedelta, timezone

from app.database import Base, SessionLocal, engine
from app.models.models import Load, User, Vehicle
from app.services.geo import load_locations

random.seed(42)  # deterministic seed for reproducible demo runs

VILLAGES = ["zhanaozen", "fort-shevchenko", "kuryk", "beyneu", "shetpe", "munayly", "tauchik", "sayotes", "akshukur"]
HUB = "aktau"

FORWARD_CATEGORIES = ["стройматериалы", "продукты", "fmcg"]
RETURN_CATEGORIES = ["возвратная тара", "оборудование", "вторсырьё", "лом"]
VEHICLE_TYPES = ["тент", "борт", "рефрижератор"]

DAY0 = datetime(2026, 8, 19, 6, 0, tzinfo=timezone.utc)


def rand_time(base: datetime, spread_hours: int = 30) -> datetime:
    return base + timedelta(hours=random.uniform(0, spread_hours))


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Load).count() > 0:
            print("Seed skipped — loads already exist")
            return

        sender = User(name="Стройбаза Актау", role="sender")
        retailer = User(name="Ритейлер Актау", role="sender")
        carrier_demo = User(name="Ерлан (демо-перевозчик)", role="carrier")
        db.add_all([sender, retailer, carrier_demo])
        db.flush()

        other_senders = [User(name=f"Отправитель {i}", role="sender") for i in range(1, 6)]
        other_carriers = [User(name=f"Перевозчик {i}", role="carrier") for i in range(1, 8)]
        db.add_all(other_senders + other_carriers)
        db.flush()

        # --- Guaranteed demo dataset ---------------------------------
        demo_forward_load = Load(
            sender_id=sender.id,
            origin=HUB,
            destination="shetpe",
            cargo_type="кирпич",
            cargo_category="стройматериалы",
            weight_tons=5,
            required_vehicle="тент",
            pickup_time=DAY0 + timedelta(hours=1),
            price_kzt=45000,
            status="OPEN",
        )
        db.add(demo_forward_load)

        # 3 candidate vehicles heading the same forward direction, so the
        # demo's "found 3 vehicles" step is deterministic.
        for i, carrier in enumerate(other_carriers[:3]):
            db.add(
                Vehicle(
                    owner_id=carrier.id,
                    vehicle_type="тент",
                    capacity_tons=8,
                    origin=HUB,
                    destination="shetpe",
                    departure_time=DAY0 + timedelta(hours=1 + i),
                    status="AVAILABLE",
                )
            )

        # The demo carrier's return leg: Shetpe -> Aktau, posted right after
        # delivery so the "search for return load" step has a vehicle to match.
        demo_return_vehicle = Vehicle(
            owner_id=carrier_demo.id,
            vehicle_type="тент",
            capacity_tons=8,
            origin="shetpe",
            destination=HUB,
            departure_time=DAY0 + timedelta(hours=6),
            status="AVAILABLE",
        )
        db.add(demo_return_vehicle)

        # Two return-cargo candidates so "Найдено 2" is deterministic. The
        # better one is on-corridor for real: Munayly sits ~3km detour off
        # the Shetpe->Aktau route (verified against data/routes.json).
        # PROJECT_CONTEXT.md's original demo narrative used Zhanaozen, but
        # with real coordinates that's a 208km detour, not "on the way" —
        # corrected here so the "До/После" numbers are honest, not fabricated.
        db.add(
            Load(
                sender_id=retailer.id,
                origin="shetpe",
                destination="munayly",
                cargo_type="пластиковая тара",
                cargo_category="возвратная тара",
                weight_tons=2,
                required_vehicle="тент",
                pickup_time=DAY0 + timedelta(hours=6, minutes=30),
                price_kzt=18000,  # ~40% of a comparable dedicated forward trip
                status="OPEN",
            )
        )
        db.add(
            Load(
                sender_id=retailer.id,
                origin="munayly",
                destination=HUB,
                cargo_type="металлолом",
                cargo_category="лом",
                weight_tons=3,
                required_vehicle="борт",  # deliberately worse compatibility fit
                pickup_time=DAY0 + timedelta(hours=8),
                price_kzt=12000,
                status="OPEN",
            )
        )

        # --- Bulk asymmetric seed (~34 more trips) ---------------------
        for i in range(20):
            village = random.choice(VILLAGES)
            db.add(
                Load(
                    sender_id=random.choice(other_senders).id,
                    origin=HUB,
                    destination=village,
                    cargo_type=random.choice(["продукты", "стройматериалы", "бытовая химия", "вода"]),
                    cargo_category=random.choice(FORWARD_CATEGORIES),
                    weight_tons=round(random.uniform(2, 10), 1),
                    required_vehicle=random.choice(VEHICLE_TYPES),
                    pickup_time=rand_time(DAY0),
                    price_kzt=round(random.uniform(25000, 70000), -3),
                    status="OPEN",
                )
            )
            db.add(
                Vehicle(
                    owner_id=random.choice(other_carriers).id,
                    vehicle_type=random.choice(VEHICLE_TYPES),
                    capacity_tons=round(random.uniform(5, 12), 1),
                    origin=HUB,
                    destination=village,
                    departure_time=rand_time(DAY0),
                    status="AVAILABLE",
                )
            )

        for i in range(14):
            village = random.choice(VILLAGES)
            # Found via /qa: random destination could equal origin, producing
            # a nonsensical "Акшукур -> Акшукур" 0km load surfaced in the
            # carrier's match list. Exclude the origin from the candidates.
            destination = random.choice([v for v in VILLAGES + [HUB] if v != village])
            db.add(
                Load(
                    sender_id=random.choice(other_senders).id,
                    origin=village,
                    destination=destination,
                    cargo_type=random.choice(["тара", "поддоны", "металлолом", "б/у оборудование"]),
                    cargo_category=random.choice(RETURN_CATEGORIES),
                    weight_tons=round(random.uniform(0.5, 4), 1),
                    required_vehicle=random.choice(VEHICLE_TYPES),
                    pickup_time=rand_time(DAY0),
                    price_kzt=round(random.uniform(8000, 25000), -3),
                    status="OPEN",
                )
            )

        db.commit()
        total_loads = db.query(Load).count()
        total_vehicles = db.query(Vehicle).count()
        print(f"Seeded {total_loads} loads, {total_vehicles} vehicles")
    finally:
        db.close()


if __name__ == "__main__":
    run()
