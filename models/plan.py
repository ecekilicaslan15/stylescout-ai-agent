from dataclasses import dataclass, field


@dataclass
class Plan:
    intent: str = "outfit_request"
    event: str = "daily"
    style: str = "casual"
    colors: list[str] = field(default_factory=list)
    disliked_items: list[str] = field(default_factory=list)
    city: str | None = None
    date: str | None = None
