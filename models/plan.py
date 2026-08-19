from dataclasses import asdict, dataclass, field

from models.styling_mode import StylingMode


@dataclass
class Plan:
    intent: str = "outfit_request"
    event: str = "daily"
    style: str = "casual"
    colors: list[str] = field(default_factory=list)
    disliked_items: list[str] = field(default_factory=list)
    city: str | None = None
    date: str | None = None
    allow_external: bool = False
    wardrobe_optional: bool = False

    def apply_styling_mode(self, mode: StylingMode) -> "Plan":
        """Set mode-specific composition policy on this plan."""
        if mode == StylingMode.MY_WARDROBE:
            self.allow_external = False
            self.wardrobe_optional = False
        elif mode == StylingMode.WARDROBE_PLUS_AI:
            self.allow_external = True
            self.wardrobe_optional = False
        elif mode == StylingMode.AI_INSPIRATION:
            self.allow_external = True
            self.wardrobe_optional = True
        return self


def plan_to_dict(plan: Plan) -> dict:
    """Convert a Plan dataclass to a plain dict for agent routing."""
    return asdict(plan)


def plan_from_dict(data: dict) -> Plan:
    """Build a Plan dataclass from a plain dict."""
    return Plan(
        intent=data.get("intent", "outfit_request"),
        event=data.get("event", "daily"),
        style=data.get("style", "casual"),
        colors=list(data.get("colors", [])),
        disliked_items=list(data.get("disliked_items", [])),
        city=data.get("city"),
        date=data.get("date"),
        allow_external=data.get("allow_external", False),
        wardrobe_optional=data.get("wardrobe_optional", False),
    )
