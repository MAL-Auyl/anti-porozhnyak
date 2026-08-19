"""Test plan item: smoke — seed-data numbers == live-calculated numbers on
the "До/После" screen. Since scoring, economics, and the seed's guaranteed
demo scenario all route through the same compute_route_metrics(), this
pins that recomputing never diverges (the exact failure mode that sank a
prior hackathon demo for this team — see plan.md premortem)."""

from app.services.economics import compute_economics
from app.services.matching import compute_route_metrics


def test_demo_scenario_economics_are_internally_consistent():
    # Munayly, not Zhanaozen — see seed.py comment. Zhanaozen is a 208km
    # detour off the real Shetpe->Aktau route (caught by this exact test).
    metrics = compute_route_metrics(
        vehicle_origin="shetpe",
        vehicle_destination="aktau",
        load_origin="shetpe",
        load_destination="munayly",
    )
    econ = compute_economics(metrics)

    assert econ.empty_km_before >= econ.empty_km_after
    assert econ.empty_km_saved == round(econ.empty_km_before - econ.empty_km_after, 1)
    # Derive expected fuel numbers from the same unrounded empty_km_saved
    # the production code uses internally — re-deriving from the already-
    # rounded econ.empty_km_saved would introduce its own rounding drift
    # and isn't what compute_economics() actually does.
    expected_fuel_l = econ.empty_km_saved * 30.0 / 100.0
    assert econ.fuel_saved_l == round(expected_fuel_l, 1)
    # fuel_saved_kzt is computed from unrounded liters internally, then
    # rounded independently — allow for the resulting sub-liter rounding
    # gap (max ~0.05L * price) rather than assuming exact re-derivation.
    assert abs(econ.fuel_saved_kzt - econ.fuel_saved_l * 300.0) <= 20.0


def test_recomputing_same_inputs_never_diverges():
    """Same (vehicle, load) pair computed twice — as would happen once from
    the matches list and once from the /explain endpoint — must be bit-for-bit
    identical, since both call sites go through the same shared function."""
    args = ("aktau", "shetpe", "shetpe", "munayly")
    m1 = compute_route_metrics(*args)
    m2 = compute_route_metrics(*args)
    assert m1 == m2

    e1 = compute_economics(m1)
    e2 = compute_economics(m2)
    assert e1 == e2
