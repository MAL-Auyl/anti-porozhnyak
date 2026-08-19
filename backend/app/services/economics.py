"""Fuel-only economics. Per plan.md: amortization/time are text-only, never
folded into the headline number. Every number here is a "demo assumption"
and must be labeled as such in the UI.
"""

from dataclasses import dataclass

from app.services.matching import RouteMetrics

VEHICLE_CONSUMPTION_L_PER_100KM = 30.0
DIESEL_PRICE_KZT_PER_L = 300.0  # demo assumption


@dataclass(frozen=True)
class EconomicsResult:
    empty_km_before: float
    empty_km_after: float
    empty_km_saved: float
    fuel_saved_l: float
    fuel_saved_kzt: float


def compute_economics(metrics: RouteMetrics) -> EconomicsResult:
    empty_before = metrics.dist_ab
    empty_after = max(0.0, metrics.dist_ac + metrics.dist_db)
    empty_saved = max(0.0, empty_before - empty_after)

    fuel_saved_l = empty_saved * VEHICLE_CONSUMPTION_L_PER_100KM / 100.0
    fuel_saved_kzt = fuel_saved_l * DIESEL_PRICE_KZT_PER_L

    return EconomicsResult(
        empty_km_before=round(empty_before, 1),
        empty_km_after=round(empty_after, 1),
        empty_km_saved=round(empty_saved, 1),
        fuel_saved_l=round(fuel_saved_l, 1),
        fuel_saved_kzt=round(fuel_saved_kzt, 0),
    )


# Return-leg tariff assumption (CEO review, refined by team):
# tariff = 40% of a comparable dedicated forward trip; paid by the sender
# of the return cargo. Demo assumption — not validated by a survey.
RETURN_TARIFF_RATE = 0.40


def suggested_return_price_kzt(forward_price_kzt: float) -> float:
    return round(forward_price_kzt * RETURN_TARIFF_RATE, 0)
