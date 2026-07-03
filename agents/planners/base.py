from abc import ABC, abstractmethod

from models.plan import Plan


class Planner(ABC):
    """
    Base interface for all planner implementations.

    Any planner must take user input and return a Plan object.
    """

    @abstractmethod
    def plan(self, user_input: str) -> Plan:
        pass
