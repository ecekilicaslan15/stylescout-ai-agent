from models.plan import Plan
from models.styling_mode import StylingMode
from agents.planners.base import Planner
from agents.detectors.color_detector import detect_colors
from agents.detectors.date_detector import detect_date
from agents.detectors.dislike_detector import detect_disliked_items
from agents.detectors.event_detector import detect_event
from agents.detectors.intent_detector import detect_intent
from agents.detectors.location_detector import detect_city
from agents.detectors.style_detector import detect_style


class RuleBasedPlanner(Planner):
    """
    Rule-based planner: composes lightweight detector functions.

    Each detector is a focused, testable unit that extracts one slice of
    meaning from the user's text (intent, event, style, etc.). This planner
    orchestrates them and assembles the final ``Plan``.

    When to use
    -----------
    Default choice while LLM integration is not yet enabled. Fast, deterministic,
    and requires no external API calls.
    """

    def plan(self, user_input: str, mode: StylingMode | None = None) -> Plan:
        # TODO: mode policy will move into planner in a dedicated follow-up ticket (see DECISIONS.md correction row)
        text = user_input.lower()
        plan = Plan()

        plan.event = detect_event(text)
        plan.style = detect_style(text)
        plan.colors = detect_colors(text)
        plan.city = detect_city(text)
        plan.date = detect_date(text)
        plan.disliked_items = detect_disliked_items(text)
        plan.intent = detect_intent(text)

        return plan
