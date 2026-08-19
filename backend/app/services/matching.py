"""Corridor matching: shared route-metrics function + scoring formula.

Per plan.md ("Ключевое архитектурное решение"): vehicle route is a single
(origin, destination) pair, not a multi-stop chain. Detour is computed via
an insertion heuristic against the 10-node distance matrix in geo.py.

`compute_route_metrics` is the single source of truth for detour/coverage
numbers — reused by scoring (this module), economics.py, and the API's
"Почему этот груз?" breakdown, so the numbers can never diverge between
screens (Eng review finding — this exact divergence sank a prior hackathon
demo for this team).
"""

from dataclasses import dataclass

from app.services.geo import distance_km

# Region is small (10 nodes, largest pairwise distance well under 200km).
# A detour above this is treated as effectively "off corridor".
MAX_ACCEPTABLE_DETOUR_KM = 60.0

# Loads/vehicles more than this many hours apart are penalized on time fit.
TIME_WINDOW_TOLERANCE_HOURS = 6.0


@dataclass(frozen=True)
class RouteMetrics:
    dist_ab: float  # vehicle's own planned distance, A -> B
    dist_ac: float  # empty leg: vehicle origin -> load pickup
    dist_cd: float  # loaded leg: load pickup -> load dropoff
    dist_db: float  # empty leg: load dropoff -> vehicle destination
    detour_km: float
    coverage_pct: float


def compute_route_metrics(
    vehicle_origin: str,
    vehicle_destination: str,
    load_origin: str,
    load_destination: str,
) -> RouteMetrics:
    """Detour/coverage for inserting a load (C->D) into a vehicle route (A->B).

    Edge case (Eng review): vehicle_origin == vehicle_destination means the
    vehicle has no baseline route to compare against — dist_ab is 0, so a
    coverage ratio would be 0/0. Guarded as its own branch, not folded into
    the general formula: coverage is defined as 0 (nothing is "covered" of a
    zero-length route), detour is the full round-trip cost of serving the
    load standalone.
    """
    a, b, c, d = vehicle_origin, vehicle_destination, load_origin, load_destination
    dist_ab = distance_km(a, b)

    if a == b:
        dist_ac = distance_km(a, c)
        dist_cd = distance_km(c, d)
        dist_db = distance_km(d, b)
        detour_km = dist_ac + dist_cd + dist_db
        return RouteMetrics(
            dist_ab=0.0,
            dist_ac=dist_ac,
            dist_cd=dist_cd,
            dist_db=dist_db,
            detour_km=detour_km,
            coverage_pct=0.0,
        )

    dist_ac = distance_km(a, c)
    dist_cd = distance_km(c, d)
    dist_db = distance_km(d, b)

    # Extra distance driven vs. going straight A -> B. When D == B this
    # collapses to plan.md's documented single-point formula:
    #   detour = dist(A,C) + dist(C,B) - dist(A,B)
    detour_km = max(0.0, dist_ac + dist_cd + dist_db - dist_ab)
    coverage_pct = max(0.0, min(100.0, 100.0 * dist_cd / dist_ab))

    return RouteMetrics(
        dist_ab=dist_ab,
        dist_ac=dist_ac,
        dist_cd=dist_cd,
        dist_db=dist_db,
        detour_km=detour_km,
        coverage_pct=coverage_pct,
    )


@dataclass(frozen=True)
class ScoreBreakdown:
    coverage_score: float
    detour_score: float
    compatibility_score: float
    time_window_score: float
    economic_score: float
    total: float


def score_match(
    metrics: RouteMetrics,
    vehicle_type: str,
    required_vehicle: str,
    departure_time_hours_offset: float,
    pickup_time_hours_offset: float,
    empty_km_saved: float,
) -> ScoreBreakdown:
    """Weighted score per plan.md:
    40% route coverage, 25% detour, 20% vehicle/cargo compatibility,
    10% time window, 5% economic effect.
    """
    coverage_score = metrics.coverage_pct

    detour_score = max(0.0, 100.0 * (1 - metrics.detour_km / MAX_ACCEPTABLE_DETOUR_KM))

    compatibility_score = 100.0 if vehicle_type == required_vehicle else 0.0

    hours_apart = abs(departure_time_hours_offset - pickup_time_hours_offset)
    time_window_score = max(0.0, 100.0 * (1 - hours_apart / TIME_WINDOW_TOLERANCE_HOURS))

    economic_score = (
        max(0.0, min(100.0, 100.0 * empty_km_saved / metrics.dist_ab))
        if metrics.dist_ab > 0
        else 0.0
    )

    total = (
        0.40 * coverage_score
        + 0.25 * detour_score
        + 0.20 * compatibility_score
        + 0.10 * time_window_score
        + 0.05 * economic_score
    )

    return ScoreBreakdown(
        coverage_score=coverage_score,
        detour_score=detour_score,
        compatibility_score=compatibility_score,
        time_window_score=time_window_score,
        economic_score=economic_score,
        total=round(total, 1),
    )
