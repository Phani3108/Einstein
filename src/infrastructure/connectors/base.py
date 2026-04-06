"""Base connector interface for all third-party integrations."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID


class ContextEventIn:
    """Universal event schema that all connectors produce."""

    def __init__(
        self,
        source: str,
        source_id: Optional[str],
        event_type: str,
        content: Optional[str],
        structured_data: Dict[str, Any],
        timestamp: datetime,
        extracted_people: List[str] = None,
        extracted_entities: Optional[Dict[str, Any]] = None,
        tier0_at: Optional[datetime] = None,
    ):
        self.source = source
        self.source_id = source_id
        self.event_type = event_type
        self.content = content
        self.structured_data = structured_data
        self.timestamp = timestamp
        self.extracted_people = extracted_people or []
        self.extracted_entities = extracted_entities
        self.tier0_at = tier0_at

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class BaseConnector(ABC):
    """Abstract base for every source connector (Gmail, Slack, Jira, etc.)."""

    source_name: str
    auth_type: str  # "oauth2", "api_key", "webhook", "bot_token"

    @abstractmethod
    async def fetch_events(
        self, user_id: UUID, since: datetime, credentials: dict
    ) -> List[ContextEventIn]:
        """Poll for new events since last sync."""

    async def handle_webhook(
        self, payload: dict, headers: dict
    ) -> List[ContextEventIn]:
        """Convert inbound webhook payload into ContextEvents. Override if webhook-capable."""
        raise NotImplementedError(
            f"{self.source_name} does not support webhooks"
        )

    def verify_webhook(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """Verify webhook signature. Override per provider."""
        return True
