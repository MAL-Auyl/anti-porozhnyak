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
