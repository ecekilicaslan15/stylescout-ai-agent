from models.plan import Plan
from models.styling_mode import StylingMode
from agents.planners.base import Planner


class LLMPlanner(Planner):
    """
    Mock LLM planner for testing the future OpenAI flow without API costs.

    Today this class simulates what an OpenAI-backed planner will do: read
    natural language and return a structured ``Plan``. The orchestrator,
    memory agent, and stylist agent stay unchanged because they only consume
    ``Plan`` objects.

    Set ``USE_LLM = True`` in ``agents/planner.py`` to route requests here
    instead of ``RuleBasedPlanner``.
    """

    def __init__(self) -> None:
        # Future OpenAI integration: create the client once here.
        # Example:
        #   from openai import OpenAI
        #   self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        pass

    def plan(self, user_input: str, mode: StylingMode | None = None) -> Plan:
        """
        Simulate LLM planning with lightweight keyword rules.

        In production, this method will:
        1. Build prompts (system + user messages)
        2. Call OpenAI chat completions with JSON response format
        3. Parse the JSON payload into a ``Plan`` instance
        """
        # TODO: mode policy will move into planner in a dedicated follow-up ticket (see DECISIONS.md correction row)
        text = user_input.lower()

        # Start from defaults — same as what a parsed JSON response would
        # fall back to when the model omits optional fields.
        plan = Plan()

        # Mock extraction: simulates structured fields returned by the LLM.
        if "office" in text or "work" in text:
            plan.event = "office"

        if "wedding" in text:
            plan.event = "wedding"

        if "elegant" in text:
            plan.style = "elegant"

        if "black" in text:
            plan.colors = ["black"]

        # Future OpenAI integration: replace the mock rules above with:
        #   response = self.client.chat.completions.create(...)
        #   raw = json.loads(response.choices[0].message.content)
        #   return Plan(intent=raw.get("intent", "outfit_request"), ...)

        return plan
