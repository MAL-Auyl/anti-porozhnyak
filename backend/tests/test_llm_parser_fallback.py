"""Test plan item: unit + manual — LLM malformed JSON -> fallback form.

No network calls here: exercises the validation path directly with
hand-crafted "LLM output" dicts, since the failure mode under test is
validation-after-the-call, not the call itself.
"""

from app.services.llm_parser import CARGO_CATEGORIES, ParsedLoadDraft
from pydantic import ValidationError


def test_valid_fields_construct_draft():
    fields = {
        "origin": "Актау",
        "destination": "Шетпе",
        "cargo": "кирпич",
        "cargo_category": "стройматериалы",
        "weight_tons": 5,
        "vehicle_type": "тент",
        "date": "2026-08-20",
    }
    draft = ParsedLoadDraft(**fields)
    assert draft.origin == "Актау"
    assert draft.weight_tons == 5


def test_missing_field_raises_validation_error_not_500():
    fields = {
        "origin": "Актау",
        # destination missing — hallucinated/incomplete LLM output
        "cargo": "кирпич",
        "cargo_category": "стройматериалы",
        "weight_tons": 5,
        "vehicle_type": "тент",
        "date": "2026-08-20",
    }
    try:
        ParsedLoadDraft(**fields)
        assert False, "expected ValidationError"
    except ValidationError as e:
        assert any("destination" in str(err["loc"]) for err in e.errors())


def test_wrong_date_format_raises_validation_error():
    fields = {
        "origin": "Актау",
        "destination": "Шетпе",
        "cargo": "кирпич",
        "cargo_category": "стройматериалы",
        "weight_tons": 5,
        "vehicle_type": "тент",
        "date": "завтра",  # LLM returned natural language instead of ISO date
    }
    try:
        ParsedLoadDraft(**fields)
        assert False, "expected ValidationError"
    except ValidationError:
        pass


def test_negative_weight_rejected():
    fields = {
        "origin": "Актау",
        "destination": "Шетпе",
        "cargo": "кирпич",
        "cargo_category": "стройматериалы",
        "weight_tons": -5,  # hallucinated nonsense value
        "vehicle_type": "тент",
        "date": "2026-08-20",
    }
    try:
        ParsedLoadDraft(**fields)
        assert False, "expected ValidationError"
    except ValidationError:
        pass


def test_known_cargo_categories_cover_return_flow_use_case():
    for expected in ("возвратная тара", "оборудование", "вторсырьё", "лом"):
        assert expected in CARGO_CATEGORIES
