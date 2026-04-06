"""Base action interface and registry for outbound actions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAction(ABC):
    """Abstract base for every outbound action (create event, draft email, etc.)."""

    action_type: str
    provider: str
    requires_confirmation: bool = True

    @abstractmethod
    async def preview(self, params: dict) -> dict:
        """Return a preview of what the action will do without executing it.

        Args:
            params: Action-specific parameters.

        Returns:
            A dict describing the proposed action (title, body, recipients, etc.).
        """

    @abstractmethod
    async def execute(self, params: dict, credentials: dict) -> dict:
        """Execute the action and return the result.

        Args:
            params: Action-specific parameters.
            credentials: OAuth tokens / API keys needed for the provider.

        Returns:
            A dict with the result (created ID, status, etc.).
        """


class ActionRegistry:
    """Singleton registry that maps action types to action instances."""

    _actions: Dict[str, BaseAction] = {}

    @classmethod
    def register(cls, action: BaseAction):
        """Register an action instance by its ``action_type``."""
        cls._actions[action.action_type] = action

    @classmethod
    def get(cls, action_type: str) -> Optional[BaseAction]:
        """Look up an action by type name."""
        return cls._actions.get(action_type)

    @classmethod
    def all(cls) -> Dict[str, BaseAction]:
        """Return a copy of all registered actions."""
        return dict(cls._actions)
