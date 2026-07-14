from abc import ABC, abstractmethod

from models.agent_context import AgentContext
from models.agent_response import AgentResponse


class BaseAgent(ABC):
    """Base class for all StyleScout agents."""

    name: str
    description: str

    @abstractmethod
    def can_handle(self, plan: dict) -> bool:
        """Return True when this agent should handle the given plan."""

    @abstractmethod
    def run(
        self,
        user_input: str,
        plan: dict,
        context: AgentContext | dict | None = None,
    ) -> AgentResponse:
        """
        Execute agent logic.

        Returns an ``AgentResponse`` whose ``data`` dict may include keys
        such as ``outfit`` and ``memory``.
        """
