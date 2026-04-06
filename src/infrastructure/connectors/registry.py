"""Connector registry — central lookup for all registered source connectors."""

from typing import Dict, Optional

from .base import BaseConnector


class ConnectorRegistry:
    """Singleton registry that maps provider names to connector instances."""

    _connectors: Dict[str, BaseConnector] = {}

    @classmethod
    def register(cls, connector: BaseConnector):
        cls._connectors[connector.source_name] = connector

    @classmethod
    def get(cls, source_name: str) -> Optional[BaseConnector]:
        return cls._connectors.get(source_name)

    @classmethod
    def all(cls) -> Dict[str, BaseConnector]:
        return dict(cls._connectors)
