"""
Einstein SDK

Python SDK for integrating with Einstein knowledge management.
Provides both HTTP client (for running sidecar) and direct SQLite access.

Usage:
    from einstein_sdk import EinsteinClient

    # Direct vault access (no server needed)
    client = EinsteinClient(vault_path="~/my-vault")
    notes = client.search("machine learning")
    note = client.create_note("My Note", "# Content here")

    # Or connect to running sidecar
    client = EinsteinClient(url="http://localhost:9721")
"""

from .client import EinsteinClient
from .types import Note, GraphData, GraphNode, GraphEdge, Entity, Tag

__version__ = "0.1.0"
__all__ = ["EinsteinClient", "Note", "GraphData", "GraphNode", "GraphEdge", "Entity", "Tag"]
