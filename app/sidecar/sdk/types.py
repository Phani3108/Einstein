"""Einstein SDK — shared type definitions."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Note:
    id: str
    file_path: str
    title: str
    content: str
    frontmatter: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    outgoing_links: list[str] = field(default_factory=list)


@dataclass
class Entity:
    entity_type: str
    entity_value: str
    confidence: float = 0.0


@dataclass
class Tag:
    tag: str
    count: int = 0


@dataclass
class GraphNode:
    id: str
    label: str
    node_type: str = "note"
    file_path: Optional[str] = None


@dataclass
class GraphEdge:
    source: str
    target: str
    label: str = ""
    edge_type: str = "wikilink"


@dataclass
class GraphData:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
