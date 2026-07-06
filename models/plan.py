from dataclasses import asdict, dataclass, field


@dataclass
class Plan:
    intent: str = "outfit_request"
    event: str = "daily"
    style: str = "casual"
    colors: list[str] = field(default_factory=list)
    disliked_items: list[str] = field(default_factory=list)
    city: str | None = None
    date: str | None = None


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
    )
