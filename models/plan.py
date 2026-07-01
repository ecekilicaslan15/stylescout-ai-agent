from dataclasses import dataclass, field


@dataclass
class Plan:
    event: str = "daily"
    style: str = "casual"
    colors: list[str] = field(default_factory=list)
    city: str | None = None
    date: str | None = None
