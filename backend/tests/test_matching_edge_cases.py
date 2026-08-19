"""Test plan item: unit — detour when origin==destination (Eng review guard)."""

from app.services.matching import compute_route_metrics


def test_detour_when_vehicle_origin_equals_destination():
    metrics = compute_route_metrics(
        vehicle_origin="aktau",
        vehicle_destination="aktau",
        load_origin="shetpe",
        load_destination="zhanaozen",
    )
    assert metrics.dist_ab == 0.0
    assert metrics.coverage_pct == 0.0  # explicit guard, not 0/0
    assert metrics.detour_km > 0


def test_detour_positive_and_coverage_bounded_normal_case():
    metrics = compute_route_metrics(
        vehicle_origin="aktau",
        vehicle_destination="shetpe",
        load_origin="shetpe",
        load_destination="zhanaozen",
    )
    assert metrics.detour_km >= 0
    assert 0 <= metrics.coverage_pct <= 100


def test_detour_matches_plan_formula_when_load_destination_equals_vehicle_destination():
    """When D == B, the generalized formula must collapse to plan.md's
    documented single-point insertion formula: dist(A,C)+dist(C,B)-dist(A,B)."""
    from app.services.geo import distance_km

    a, b, c = "aktau", "shetpe", "munayly"
    metrics = compute_route_metrics(a, b, c, b)
    expected = max(0.0, distance_km(a, c) + distance_km(c, b) - distance_km(a, b))
    assert abs(metrics.detour_km - expected) < 1e-6
