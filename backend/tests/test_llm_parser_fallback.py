"""Test plan item: unit + manual — LLM malformed JSON -> fallback form.

No network calls here: exercises the validation path directly with
hand-crafted "LLM output" dicts, since the failure mode under test is
validation-after-the-call, not the call itself.
"""

from app.services.llm_parser import (
    CARGO_CATEGORIES,
    DEMO_PHRASE,
    ParsedLoadDraft,
    ParseResult,
    _validate_locations,
    parse_load_request,
    parse_load_request_cached,
)
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


def test_validate_locations_normalizes_names_to_ids():
    """The LLM is prompted to return human names ('Актау'); this must
    convert them to slug ids ('aktau') in-place so vehicles/loads/the
    distance matrix agree on identity. Root cause of the /qa crash:
    'No route data between aktau and Актау'."""
    fields = {"origin": "Актау", "destination": "Шетпе"}
    errors = []
    _validate_locations(fields, errors)
    assert errors == []
    assert fields["origin"] == "aktau"
    assert fields["destination"] == "shetpe"


def test_validate_locations_rejects_unknown_name():
    fields = {"origin": "Нью-Йорк", "destination": "Шетпе"}
    errors = []
    _validate_locations(fields, errors)
    assert len(errors) == 1
    assert "origin" in errors[0]


def test_prefers_gemini_when_both_keys_present(monkeypatch):
    """Gemini's free tier makes it the safer default for a live demo — a
    paid Anthropic key might not be funded/available on defense day."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")

    calls = []
    monkeypatch.setattr("app.services.llm_parser._call_gemini", lambda text, system: calls.append("gemini") or '{"origin":"Актау"}')
    monkeypatch.setattr("app.services.llm_parser._call_anthropic", lambda text, system: calls.append("anthropic") or '{"origin":"Актау"}')

    parse_load_request("что угодно")
    assert calls == ["gemini"]


def test_falls_back_to_anthropic_when_no_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")

    calls = []
    monkeypatch.setattr("app.services.llm_parser._call_anthropic", lambda text, system: calls.append("anthropic") or '{"origin":"Актау"}')

    parse_load_request("что угодно")
    assert calls == ["anthropic"]


def test_no_keys_returns_graceful_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = parse_load_request("что угодно")
    assert result.ok is False
    assert "GEMINI_API_KEY" in result.errors[0]


def test_gemini_markdown_fence_stripped(monkeypatch):
    """Gemini sometimes wraps JSON in ```json fences despite instructions
    not to — must not break parsing."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    fenced = '```json\n{"origin":"Актау","destination":"Шетпе","cargo":"кирпич","cargo_category":"стройматериалы","weight_tons":5,"vehicle_type":"тент","date":"2026-08-20"}\n```'
    monkeypatch.setattr("app.services.llm_parser._call_gemini", lambda text, system: fenced)

    result = parse_load_request("нужно завтра из Актау в Шетпе 5 тонн кирпича")
    assert result.ok is True
    assert result.draft.origin == "aktau"


def test_known_cargo_categories_cover_return_flow_use_case():
    for expected in ("возвратная тара", "оборудование", "вторсырьё", "лом"):
        assert expected in CARGO_CATEGORIES


def test_demo_phrase_hits_cache_without_calling_llm(monkeypatch):
    """The exact rehearsed demo phrase must never touch the network — this
    is the whole point of caching it (premortem: live LLM call on stage is
    a failure point). Also covers a real bug found on review: comparing a
    .lower()'d input against a mixed-case DEMO_PHRASE never matched."""

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("live LLM should not be called for the cached demo phrase")

    monkeypatch.setattr("app.services.llm_parser.parse_load_request", _fail_if_called)

    result = parse_load_request_cached(DEMO_PHRASE)
    assert result.ok is True
    # Regression: DEMO_CACHED_RESULT originally hardcoded display names
    # ("Актау"/"Шетпе") instead of location ids ("aktau"/"shetpe"). The
    # frontend's <select> matches by id, so a name silently fell back to
    # the first option — found via /qa: both "Откуда" and "Куда" showed
    # "Актау" selected because "Шетпе" matched no option value.
    from app.services.geo import load_locations

    known_ids = set(load_locations().keys())
    assert result.draft.origin in known_ids, f"{result.draft.origin!r} is not a location id"
    assert result.draft.destination in known_ids, f"{result.draft.destination!r} is not a location id"
    assert result.draft.origin != result.draft.destination
    assert result.draft.origin == "aktau"
    assert result.draft.destination == "shetpe"

    # Case-insensitivity: judges/team may retype with different casing.
    result_upper = parse_load_request_cached(DEMO_PHRASE.upper())
    assert result_upper.ok is True
