"""Test plan items:
- integration: race on ACCEPTED (2 clients, 1 load)
- unit + UI: empty matching result
"""


def _login(client, name, role):
    resp = client.post("/auth/login", json={"name": name, "role": role})
    assert resp.status_code == 200
    return resp.json()


def test_empty_matching_result_returns_explicit_reason(client):
    carrier = _login(client, "Ерлан", "carrier")
    vehicle = client.post(
        "/vehicles",
        json={
            "vehicle_type": "тент",
            "capacity_tons": 8,
            "origin": "beyneu",
            "destination": "aktau",
            "departure_time": "2026-08-19T10:00:00Z",
        },
    ).json()

    resp = client.get(f"/vehicles/{vehicle['id']}/matches")
    assert resp.status_code == 200
    body = resp.json()
    assert body["matches"] == []
    assert body["empty_state"] is not None
    assert "trips_in_database" in body["empty_state"]


def test_duplicate_match_rows_rejected_at_db_level(client):
    """Regression for a /review finding: find_matches_for_vehicle did
    check-then-insert on (vehicle_id, load_id) with no DB constraint —
    concurrent pollers (two open tabs) could both pass the existence check
    before either committed, producing duplicate Match rows. This pins the
    UniqueConstraint that closes the gap."""
    from sqlalchemy.exc import IntegrityError

    from app.models.models import Match

    sender = _login(client, "Стройбаза", "sender")
    load = client.post(
        "/loads",
        json={
            "origin": "aktau",
            "destination": "shetpe",
            "cargo_type": "кирпич",
            "cargo_category": "стройматериалы",
            "weight_tons": 5,
            "required_vehicle": "тент",
            "pickup_time": "2026-08-19T08:00:00Z",
            "price_kzt": 45000,
        },
    ).json()
    carrier = _login(client, "Ерлан", "carrier")
    vehicle = client.post(
        "/vehicles",
        json={
            "vehicle_type": "тент",
            "capacity_tons": 8,
            "origin": "aktau",
            "destination": "shetpe",
            "departure_time": "2026-08-19T08:30:00Z",
        },
    ).json()

    db = client.db_session_factory()
    try:
        db.add(Match(vehicle_id=vehicle["id"], load_id=load["id"], score=50, detour_km=0, coverage_pct=0, empty_km_saved=0, fuel_saved_l=0, fuel_saved_kzt=0))
        db.commit()

        db.add(Match(vehicle_id=vehicle["id"], load_id=load["id"], score=60, detour_km=0, coverage_pct=0, empty_km_saved=0, fuel_saved_l=0, fuel_saved_kzt=0))
        try:
            db.commit()
            assert False, "expected IntegrityError — unique constraint should reject the duplicate"
        except IntegrityError:
            db.rollback()
    finally:
        db.close()


def test_load_created_from_llm_parse_draft_actually_matches(client):
    """End-to-end regression for the /qa-found bug: a load created from the
    LLM parser's draft (origin/destination as location names from the
    LLM's perspective) must produce ids that the matching engine can use —
    previously this crashed distance_km() with 'No route data between
    aktau and Актау' the moment a carrier searched for matches."""
    sender = _login(client, "Стройбаза", "sender")
    parsed = client.post("/loads/parse", json={"text": "нужно завтра из Актау в Шетпе отвезти 5 тонн кирпича, машина с тентом"}).json()
    assert parsed["ok"] is True
    draft = parsed["draft"]

    load = client.post(
        "/loads",
        json={
            "origin": draft["origin"],
            "destination": draft["destination"],
            "cargo_type": draft["cargo"],
            "cargo_category": draft["cargo_category"],
            "weight_tons": draft["weight_tons"],
            "required_vehicle": draft["vehicle_type"],
            "pickup_time": "2026-08-19T08:00:00Z",
            "price_kzt": 45000,
        },
    )
    assert load.status_code == 200

    carrier = _login(client, "Ерлан", "carrier")
    vehicle = client.post(
        "/vehicles",
        json={
            "vehicle_type": draft["vehicle_type"],
            "capacity_tons": 8,
            "origin": draft["origin"],
            "destination": draft["destination"],
            "departure_time": "2026-08-19T08:30:00Z",
        },
    ).json()

    matches = client.get(f"/vehicles/{vehicle['id']}/matches")
    assert matches.status_code == 200  # previously 500 — matching crashed on unresolved location names
    assert matches.json()["matches"], "expected a match for a direct-route load created via the parser"


def test_second_carrier_gets_409_on_already_accepted_load(client):
    sender = _login(client, "Стройбаза", "sender")
    load = client.post(
        "/loads",
        json={
            "origin": "aktau",
            "destination": "shetpe",
            "cargo_type": "кирпич",
            "cargo_category": "стройматериалы",
            "weight_tons": 5,
            "required_vehicle": "тент",
            "pickup_time": "2026-08-19T08:00:00Z",
            "price_kzt": 45000,
        },
    ).json()

    carrier1 = _login(client, "Перевозчик 1", "carrier")
    vehicle1 = client.post(
        "/vehicles",
        json={
            "vehicle_type": "тент",
            "capacity_tons": 8,
            "origin": "aktau",
            "destination": "shetpe",
            "departure_time": "2026-08-19T08:30:00Z",
        },
    ).json()
    matches1 = client.get(f"/vehicles/{vehicle1['id']}/matches").json()
    assert matches1["matches"], "expected at least one match for a direct-route vehicle"
    match_id = matches1["matches"][0]["id"]

    # First accept succeeds
    r1 = client.post(f"/matches/{match_id}/accept")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ACCEPTED"

    # Second accept on the same match (simulating a near-simultaneous second
    # carrier who polled before the first accept landed) must be rejected,
    # not silently overwrite.
    r2 = client.post(f"/matches/{match_id}/accept")
    assert r2.status_code == 409
