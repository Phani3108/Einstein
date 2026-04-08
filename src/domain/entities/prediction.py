"""Prediction domain entities for the Personal Semantic Engine.

These entities represent forecasts and predictions about knowledge graph
evolution, activity patterns, entity emergence, and relationship dynamics.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PredictionType(str, Enum):
    """Types of predictions supported by the system."""

    ACTIVITY = "activity"
    ENTITY_EMERGENCE = "entity_emergence"
    RELATIONSHIP = "relationship"
    GRAPH_EVOLUTION = "graph_evolution"


class TrendDirection(str, Enum):
    """Direction of a predicted trend."""

    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


class ConfidenceLevel(str, Enum):
    """Confidence level for a prediction."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PredictionResult(BaseModel):
    """Base result from a time-series forecast."""

    point_forecast: List[float]
    lower_bound: List[float]
    upper_bound: List[float]
    median: List[float]
    horizon: int
    context_length: int
    quantiles: List[float] = Field(
        default_factory=lambda: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    )
    forecast_timestamps: List[datetime] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = True

    def get_forecast_for_day(self, day_offset: int) -> Optional[Dict[str, float]]:
        """Get forecast values for a specific day offset."""
        if day_offset < 0 or day_offset >= self.horizon:
            return None
        return {
            "point": self.point_forecast[day_offset],
            "lower": self.lower_bound[day_offset],
            "upper": self.upper_bound[day_offset],
            "median": self.median[day_offset],
        }


class ActivityForecast(BaseModel):
    """Forecast of user activity levels (thoughts, events, interactions)."""

    id: UUID
    user_id: UUID
    prediction_type: PredictionType = PredictionType.ACTIVITY
    forecast_result: PredictionResult
    granularity: str = "day"

    total_predicted: float
    average_daily: float
    peak_day_offset: int
    trend_direction: TrendDirection
    confidence_level: ConfidenceLevel

    include_thoughts: bool = True
    include_events: bool = True
    source_breakdown: Optional[Dict[str, List[float]]] = None

    insights: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    class Config:
        frozen = True

    @property
    def forecast_summary(self) -> str:
        """Generate a human-readable forecast summary."""
        direction_text = {
            TrendDirection.RISING: "increasing",
            TrendDirection.DECLINING: "decreasing",
            TrendDirection.STABLE: "stable",
            TrendDirection.VOLATILE: "variable",
        }
        return (
            f"Activity is predicted to be {direction_text[self.trend_direction]} "
            f"over the next {self.forecast_result.horizon} days, "
            f"with an average of {self.average_daily:.1f} items per day."
        )


class EntityTrend(BaseModel):
    """Predicted trend for an entity's relevance and mention frequency."""

    id: UUID
    user_id: UUID
    prediction_type: PredictionType = PredictionType.ENTITY_EMERGENCE
    entity_type: str
    entity_value: str
    forecast_result: PredictionResult
    granularity: str = "day"

    current_mentions: int
    predicted_mentions: int
    growth_rate: float
    trend_direction: TrendDirection
    confidence_level: ConfidenceLevel

    is_emerging: bool
    is_fading: bool
    emergence_score: float

    related_entities: List[str] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = True

    @property
    def trend_summary(self) -> str:
        """Generate a human-readable trend summary."""
        if self.is_emerging:
            return f"'{self.entity_value}' is an emerging topic with {self.growth_rate:.0%} growth"
        elif self.is_fading:
            return f"'{self.entity_value}' is fading with {abs(self.growth_rate):.0%} decline"
        else:
            return f"'{self.entity_value}' is stable with {self.current_mentions} recent mentions"


class RelationshipPrediction(BaseModel):
    """Prediction about relationship dynamics with a person or project."""

    id: UUID
    user_id: UUID
    prediction_type: PredictionType = PredictionType.RELATIONSHIP
    target_type: str  # 'person' or 'project'
    target_id: UUID
    target_name: str
    forecast_result: PredictionResult
    granularity: str = "day"

    current_interaction_rate: float
    predicted_interaction_rate: float
    days_since_last_interaction: int
    predicted_next_interaction_day: Optional[int] = None

    dormancy_risk: float
    predicted_dormancy_days: Optional[int] = None
    trend_direction: TrendDirection
    confidence_level: ConfidenceLevel

    follow_up_urgency: str = "normal"
    recommended_action: Optional[str] = None
    insights: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = True

    @property
    def dormancy_warning(self) -> Optional[str]:
        """Generate a dormancy warning if applicable."""
        if self.dormancy_risk > 0.7:
            return (
                f"High risk of losing touch with {self.target_name}. "
                f"Consider reaching out within {self.predicted_dormancy_days or 7} days."
            )
        elif self.dormancy_risk > 0.4:
            return f"{self.target_name} may become dormant soon. A follow-up might be helpful."
        return None


class GraphEvolutionForecast(BaseModel):
    """Forecast of overall knowledge graph growth and evolution."""

    id: UUID
    user_id: UUID
    prediction_type: PredictionType = PredictionType.GRAPH_EVOLUTION

    node_count_forecast: PredictionResult
    edge_count_forecast: PredictionResult
    granularity: str = "day"

    current_node_count: int
    current_edge_count: int
    predicted_node_growth: float
    predicted_edge_growth: float

    connection_rate_forecast: PredictionResult
    cluster_formation_likelihood: float
    graph_density_trend: TrendDirection

    emerging_clusters: List[Dict[str, Any]] = Field(default_factory=list)
    growth_drivers: List[str] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = True

    @property
    def growth_summary(self) -> str:
        """Generate a human-readable growth summary."""
        return (
            f"Your knowledge graph is projected to grow by "
            f"{self.predicted_node_growth:.0%} in nodes and "
            f"{self.predicted_edge_growth:.0%} in connections "
            f"over the next {self.node_count_forecast.horizon} days."
        )


class PredictionBatch(BaseModel):
    """A batch of predictions for a user."""

    user_id: UUID
    activity_forecast: Optional[ActivityForecast] = None
    entity_trends: List[EntityTrend] = Field(default_factory=list)
    relationship_predictions: List[RelationshipPrediction] = Field(default_factory=list)
    graph_evolution: Optional[GraphEvolutionForecast] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = True

    @property
    def has_predictions(self) -> bool:
        """Check if any predictions are available."""
        return (
            self.activity_forecast is not None
            or len(self.entity_trends) > 0
            or len(self.relationship_predictions) > 0
            or self.graph_evolution is not None
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all predictions."""
        summary = {"generated_at": self.generated_at.isoformat()}

        if self.activity_forecast:
            summary["activity"] = {
                "trend": self.activity_forecast.trend_direction.value,
                "average_daily": self.activity_forecast.average_daily,
                "summary": self.activity_forecast.forecast_summary,
            }

        if self.entity_trends:
            emerging = [e for e in self.entity_trends if e.is_emerging]
            fading = [e for e in self.entity_trends if e.is_fading]
            summary["entities"] = {
                "total_tracked": len(self.entity_trends),
                "emerging_count": len(emerging),
                "fading_count": len(fading),
                "top_emerging": [e.entity_value for e in emerging[:3]],
            }

        if self.relationship_predictions:
            at_risk = [r for r in self.relationship_predictions if r.dormancy_risk > 0.5]
            summary["relationships"] = {
                "total_tracked": len(self.relationship_predictions),
                "at_risk_count": len(at_risk),
                "at_risk_names": [r.target_name for r in at_risk[:3]],
            }

        if self.graph_evolution:
            summary["graph"] = {
                "node_growth": self.graph_evolution.predicted_node_growth,
                "edge_growth": self.graph_evolution.predicted_edge_growth,
                "summary": self.graph_evolution.growth_summary,
            }

        return summary
