"""LLM parser: unstructured text -> structured load draft.

Per plan.md: the only place AI is used in the MVP. Strict Pydantic
validation runs independently of the LLM output (Eng review — critical
finding: a live judge typing their own phrase at the demo is a likely
scenario, not a hypothetical one). On validation failure the caller gets a
partially-filled draft plus an `errors` list, so the frontend can render a
"please correct manually" form instead of a 500.
"""

import json
import os
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from app.services.geo import load_locations, location_id_by_name

CARGO_CATEGORIES = {
    "стройматериалы",
    "продукты",
    "fmcg",
    "возвратная тара",
    "оборудование",
    "вторсырьё",
    "лом",
}

SYSTEM_PROMPT = """Ты извлекаешь структурированную заявку на грузоперевозку из свободного текста на русском языке.
Известные населённые пункты региона: {locations}.
Категории груза: {categories}.

Верни ТОЛЬКО JSON без пояснений, в формате:
{{"origin": "...", "destination": "...", "cargo": "...", "cargo_category": "...", "weight_tons": <число>, "vehicle_type": "...", "date": "YYYY-MM-DD"}}

origin/destination должны быть названиями из списка населённых пунктов. Если дата не указана явно, используй {default_date} (сегодня)."""


class ParsedLoadDraft(BaseModel):
    origin: str
    destination: str
    cargo: str
    cargo_category: str
    weight_tons: float = Field(gt=0, le=100)
    vehicle_type: str
    date: date


class ParseResult(BaseModel):
    ok: bool
    draft: Optional[ParsedLoadDraft] = None
    raw_fields: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


def _validate_locations(fields: dict, errors: list[str]) -> None:
    """Validates origin/destination are known location names, THEN
    normalizes them to location ids in-place.

    The LLM is prompted to return human names ("Актау") since that's what
    it can reliably produce, but vehicles/routes/the distance matrix all
    key on slug ids ("aktau") — a load left with a name instead of an id
    breaks every downstream distance_km() lookup (found via /qa: crashed
    the matching endpoint with 'No route data between aktau and Актау').
    """
    for key in ("origin", "destination"):
        val = fields.get(key)
        loc_id = location_id_by_name(val) if isinstance(val, str) else None
        if loc_id is None:
            errors.append(f"'{key}' = {val!r} не входит в известные населённые пункты региона")
        else:
            fields[key] = loc_id


def _validate_category(fields: dict, errors: list[str]) -> None:
    if fields.get("cargo_category") not in CARGO_CATEGORIES:
        errors.append(f"'cargo_category' = {fields.get('cargo_category')!r} не входит в известные категории")


def _call_gemini(text: str, system: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        system_instruction=system,
    )
    resp = model.generate_content(text)
    return resp.text.strip()


def _call_anthropic(text: str, system: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": text}],
    )
    return resp.content[0].text.strip()


def parse_load_request(text: str) -> ParseResult:
    """Calls the LLM, then validates independently of what it returned.

    Never raises on malformed LLM output — always returns a ParseResult,
    ok=False with errors populated when validation fails.

    Provider is picked by whichever key is set: GEMINI_API_KEY first
    (generous free tier — safer for a live hackathon demo than a paid,
    possibly-unfunded Anthropic key), falling back to ANTHROPIC_API_KEY.
    """
    if os.getenv("GEMINI_API_KEY"):
        call = _call_gemini
    elif os.getenv("ANTHROPIC_API_KEY"):
        call = _call_anthropic
    else:
        return ParseResult(ok=False, errors=["GEMINI_API_KEY / ANTHROPIC_API_KEY не заданы — парсер недоступен"])

    locations = ", ".join(sorted(loc["name"] for loc in load_locations().values()))
    system = SYSTEM_PROMPT.format(
        locations=locations,
        categories=", ".join(sorted(CARGO_CATEGORIES)),
        default_date=datetime.now().date().isoformat(),
    )

    try:
        raw_text = call(text, system)
    except Exception as e:  # network/API failure — never crash the request
        return ParseResult(ok=False, errors=[f"LLM недоступен: {e}"])

    # Gemini sometimes wraps JSON in ```json fences despite instructions.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`").removeprefix("json").strip()

    try:
        fields = json.loads(raw_text)
    except json.JSONDecodeError:
        return ParseResult(ok=False, errors=["LLM вернул не-JSON ответ"], raw_fields={"raw": raw_text})

    errors: list[str] = []
    _validate_locations(fields, errors)
    _validate_category(fields, errors)

    try:
        draft = ParsedLoadDraft(**fields)
    except ValidationError as e:
        for err in e.errors():
            errors.append(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}")
        return ParseResult(ok=False, draft=None, raw_fields=fields, errors=errors)

    if errors:
        return ParseResult(ok=False, draft=None, raw_fields=fields, errors=errors)

    return ParseResult(ok=True, draft=draft, raw_fields=fields, errors=[])


# Cached response for the exact rehearsed demo phrase — per plan.md's
# premortem finding: never rely on a live LLM call in front of judges for
# the scripted demo moment. Live calls still handle judges typing their own
# text.
DEMO_PHRASE = "нужно завтра из Актау в Шетпе отвезти 5 тонн кирпича, машина с тентом"
DEMO_CACHED_RESULT = ParseResult(
    ok=True,
    draft=ParsedLoadDraft(
        # ids, not display names — this constant bypasses _validate_locations'
        # name->id normalization, and originally still held raw names after
        # that fix landed. Found via /qa: destination select silently fell
        # back to the first option (Актау) because "Шетпе" matched no
        # option value, so the demo's own route showed Aktau -> Aktau.
        origin="aktau",
        destination="shetpe",
        cargo="кирпич",
        cargo_category="стройматериалы",
        weight_tons=5,
        vehicle_type="тент",
        date=date.today(),
    ),
    raw_fields={},
    errors=[],
)


def parse_load_request_cached(text: str) -> ParseResult:
    # Bug found on review: comparing a lowered input against a mixed-case
    # DEMO_PHRASE ("Актау", "Шетпе") never matched. Lower both sides.
    if text.strip().lower() == DEMO_PHRASE.lower():
        return DEMO_CACHED_RESULT
    return parse_load_request(text)
