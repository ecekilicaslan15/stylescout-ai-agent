import json

from models.plan import Plan, plan_from_dict
from models.styling_mode import DEFAULT_STYLING_MODE, StylingMode
from agents.planners.base import Planner
from services.llm_client import ask_llm

PLAN_SYSTEM_PROMPT = """You extract a structured outfit plan from a user request.
Reply with a single JSON object only. No markdown, no commentary.
Keys:
- intent: one of outfit_request, outfit_request_with_memory_update, memory_update
- event: one of daily, office, wedding, party
- style: one of casual, elegant, minimal, comfortable, sporty
- colors: array of color names (black, white, beige, navy, blue, gray, pink, red)
- disliked_items: array of clothing names the user does not want
- city: city name or null
- date: "today", "tomorrow", or null
Do not include allow_external or wardrobe_optional."""

KNOWN_INTENTS = {
    "outfit_request",
    "outfit_request_with_memory_update",
    "memory_update",
    "inline_edit",
    "sewing_request",
    "trend_request",
    "shopping_request",
}


class LLMPlanError(ValueError):
    """Raised when the LLM response cannot be parsed into a Plan."""


class LLMPlanner(Planner):
    """
    OpenRouter-backed planner: natural language in, structured ``Plan`` out.

    The orchestrator, StylistAgent, and OutfitValidator stay unchanged because
    they only consume ``Plan`` objects / composed outfits. Set ``USE_LLM=true``
    in the environment to route requests here instead of ``RuleBasedPlanner``.
    """

    def plan(self, user_input: str, mode: StylingMode = DEFAULT_STYLING_MODE) -> Plan:
        raw = ask_llm(
            user_input,
            system_prompt=PLAN_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=300,
        )
        payload = _parse_plan_payload(raw)
        plan = plan_from_dict(payload)
        return plan.apply_styling_mode(mode)


def _parse_plan_payload(text: str) -> dict:
    """Parse LLM text into Plan fields. Does not repair invalid JSON."""
    if not isinstance(text, str) or not text.strip():
        raise LLMPlanError("LLM response was empty")

    data = _load_json_object(text)
    intent = data.get("intent", "outfit_request")
    if intent not in KNOWN_INTENTS:
        intent = "outfit_request"

    return {
        "intent": intent,
        "event": _optional_str(data.get("event")) or "daily",
        "style": _optional_str(data.get("style")) or "casual",
        "colors": _as_str_list(data.get("colors"), field="colors"),
        "disliked_items": _as_str_list(data.get("disliked_items"), field="disliked_items"),
        "city": _optional_str(data.get("city")),
        "date": _optional_str(data.get("date")),
    }


def _load_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            raise LLMPlanError("LLM response was not valid JSON") from None
        try:
            data = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMPlanError("LLM response was not valid JSON") from exc

    if not isinstance(data, dict):
        raise LLMPlanError("LLM JSON root must be an object")
    return data


def _as_str_list(value, *, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raise LLMPlanError(f"LLM field {field} must be a list of strings")


def _optional_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
