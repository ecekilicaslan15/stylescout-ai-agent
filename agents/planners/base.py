from abc import ABC, abstractmethod

from models.plan import Plan
from models.styling_mode import StylingMode


class Planner(ABC):
    """
    Base interface for all planner implementations.

    Any planner must take user input and return a Plan object.
    """

    @abstractmethod
    def plan(self, user_input: str, mode: StylingMode | None = None) -> Plan:
        pass
