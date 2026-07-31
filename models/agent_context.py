from dataclasses import dataclass, field
from typing import Any

from models.styling_mode import DEFAULT_STYLING_MODE, StylingMode
from wardrobe.wardrobe_repository import WardrobeRepository


@dataclass
class AgentContext:
    user_input: str
    mode: StylingMode = DEFAULT_STYLING_MODE
    plan: Any = None
    memory: dict = field(default_factory=dict)
    current_outfit: list = field(default_factory=list)
    selected_item: dict | None = None
    wardrobe: list = field(default_factory=list)
    conversation_history: list = field(default_factory=list)
    wardrobe_repository: WardrobeRepository | None = None
