"""Prediction API routes.

Time-series forecasting for knowledge graph evolution, activity patterns,
entity emergence, and relationship dynamics.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.domain.entities.prediction import (
    ConfidenceLevel,
    PredictionResult,
    TrendDirection,
)
from src.domain.entities.user import User
from src.infrastructure.database.connection import Database
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.infrastructure.prediction.forecast_service import (
    ForecastService,
    ForecastConfig,
    get_forecast_service,
    ForecastResult,
)
from src.infrastructure.prediction.time_series_extractor import (
    ActivityExtractor,
    EntityMentionExtractor,
    ConnectionRateExtractor,
    ProfileMetricsExtractor,
)


class ActivityForecastRequest(BaseModel):
    horizon: int = Field(default=7, ge=1, le=30, description="Days to forecast")
    granularity: str = Field(default="day", description="Time bucket size")
    include_thoughts: bool = True
    include_events: bool = True
    lookback_days: int = Field(default=90, ge=30, le=365)


class ActivityForecastResponse(BaseModel):
    prediction_type: str = "activity"
    horizon: int
    granularity: str
    total_predicted: float
    average_daily: float
    trend_direction: str
    confidence_level: str
    point_forecast: List[float]
    lower_bound: List[float]
    upper_bound: List[float]
    forecast_dates: List[str]
    insights: List[str]
    generated_at: str


class EntityTrendRequest(BaseModel):
    entity_type: Optional[str] = None
    entity_value: Optional[str] = None
    top_n: int = Field(default=10, ge=1, le=50)
    horizon: int = Field(default=14, ge=1, le=30)
    lookback_days: int = Field(default=90, ge=30, le=365)


class EntityTrendResponse(BaseModel):
    entity_type: str
    entity_value: str
    current_mentions: int
    predicted_mentions: int
    growth_rate: float
    trend_direction: str
    is_emerging: bool
    is_fading: bool
    emergence_score: float
    point_forecast: List[float]
    insights: List[str]


class RelationshipForecastRequest(BaseModel):
    target_type: Optional[str] = Field(
        default=None, description="'person' or 'project'"
    )
    target_id: Optional[str] = None
    horizon: int = Field(default=14, ge=1, le=30)
    lookback_days: int = Field(default=90, ge=30, le=365)


class RelationshipForecastResponse(BaseModel):
    target_type: str
    target_id: str
    target_name: str
    days_since_last_interaction: int
    predicted_next_interaction_day: Optional[int]
    dormancy_risk: float
    trend_direction: str
    follow_up_urgency: str
    recommended_action: Optional[str]
    point_forecast: List[float]
    insights: List[str]


class GraphEvolutionRequest(BaseModel):
    horizon: int = Field(default=14, ge=1, le=30)
    lookback_days: int = Field(default=90, ge=30, le=365)


class GraphEvolutionResponse(BaseModel):
    current_node_count: int
    current_edge_count: int
    predicted_node_growth: float
    predicted_edge_growth: float
    graph_density_trend: str
    cluster_formation_likelihood: float
    node_forecast: List[float]
    edge_forecast: List[float]
    growth_drivers: List[str]
    insights: List[str]


class PredictionSummaryResponse(BaseModel):
    user_id: str
    has_predictions: bool
    activity_summary: Optional[Dict[str, Any]]
    entity_summary: Optional[Dict[str, Any]]
    relationship_summary: Optional[Dict[str, Any]]
    graph_summary: Optional[Dict[str, Any]]
    generated_at: str


class DormancyRiskResponse(BaseModel):
    type: str
    id: str
    name: str
    dormancy_days: int
    days_until_dormant: int
    risk_level: str
    last_activity: Optional[str]


def _determine_trend_direction(values: List[float]) -> TrendDirection:
    """Determine trend direction from forecast values."""
    if len(values) < 2:
        return TrendDirection.STABLE

    first_half = sum(values[: len(values) // 2]) / max(1, len(values) // 2)
    second_half = sum(values[len(values) // 2 :]) / max(1, len(values) - len(values) // 2)

    change_rate = (second_half - first_half) / max(first_half, 0.1)

    if change_rate > 0.15:
        return TrendDirection.RISING
    elif change_rate < -0.15:
        return TrendDirection.DECLINING
    elif abs(change_rate) > 0.05:
        return TrendDirection.VOLATILE
    return TrendDirection.STABLE


def _determine_confidence(context_length: int, variance: float) -> ConfidenceLevel:
    """Determine confidence level based on data quality."""
    if context_length >= 60 and variance < 0.5:
        return ConfidenceLevel.HIGH
    elif context_length >= 30:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _forecast_result_to_prediction(
    forecast: ForecastResult,
    start_date: datetime,
) -> PredictionResult:
    """Convert ForecastResult to domain PredictionResult."""
    forecast_dates = [
        start_date + timedelta(days=i) for i in range(forecast.horizon)
    ]

    return PredictionResult(
        point_forecast=forecast.point_forecast,
        lower_bound=forecast.lower_bound,
        upper_bound=forecast.upper_bound,
        median=forecast.median,
        horizon=forecast.horizon,
        context_length=forecast.context_length,
        quantiles=forecast.quantiles,
        forecast_timestamps=forecast_dates,
        generated_at=datetime.utcnow(),
    )


def create_predictions_router(
    database: Database,
    auth_middleware: AuthenticationMiddleware,
    forecast_config: Optional[ForecastConfig] = None,
    use_mock: bool = False,
) -> APIRouter:
    """Create the predictions router with dependency injection.

    Args:
        database: Database connection for time series extraction.
        auth_middleware: Authentication middleware.
        forecast_config: Optional forecast service configuration.
        use_mock: If True, use mock forecasting service for testing.

    Returns:
        Configured APIRouter for prediction endpoints.
    """
    router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])

    forecast_service = get_forecast_service(forecast_config, use_mock=use_mock)

    @router.on_event("startup")
    async def initialize_forecast_service():
        """Initialize forecast model on startup."""
        if not forecast_service.initialize():
            import logging
            logging.warning(
                "Forecast service not initialized. Prediction endpoints will use mock forecasts."
            )

    @router.get("/status")
    async def get_prediction_status(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Check if prediction service is available."""
        return {
            "service": "predictions",
            "forecast_available": forecast_service.is_available,
            "model": "forecast-v2.5" if forecast_service.is_available else "Mock",
            "user_id": str(user.id),
        }

    @router.post("/activity/forecast", response_model=ActivityForecastResponse)
    async def forecast_activity(
        request: ActivityForecastRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Forecast user activity levels (thoughts, events, interactions).

        Returns predicted activity counts for the next N days with confidence bounds.
        """
        if not forecast_service.is_available:
            forecast_service.initialize()

        async with database.session() as session:
            extractor = ActivityExtractor(session)
            start_date = datetime.utcnow() - timedelta(days=request.lookback_days)

            series = await extractor.extract(
                user_id=user.id,
                start_date=start_date,
                granularity=request.granularity,
                include_thoughts=request.include_thoughts,
                include_events=request.include_events,
            )

        if series.length < 7:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data: only {series.length} data points. Need at least 7.",
            )

        forecast = forecast_service.forecast_activity(
            daily_counts=series.values,
            horizon=request.horizon,
        )

        trend = _determine_trend_direction(forecast.point_forecast)
        total_predicted = sum(forecast.point_forecast)
        average_daily = total_predicted / request.horizon

        variance = sum(
            (v - average_daily) ** 2 for v in forecast.point_forecast
        ) / request.horizon
        confidence = _determine_confidence(series.length, variance)

        forecast_dates = [
            (datetime.utcnow() + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(request.horizon)
        ]

        insights = []
        if trend == TrendDirection.RISING:
            peak_idx = forecast.point_forecast.index(max(forecast.point_forecast))
            insights.append(f"Activity is predicted to increase, peaking on day {peak_idx + 1}")
        elif trend == TrendDirection.DECLINING:
            insights.append("Activity is predicted to decrease over the forecast period")
        if average_daily > sum(series.values[-7:]) / 7 * 1.2:
            insights.append("Expect a busier period than recent history")
        elif average_daily < sum(series.values[-7:]) / 7 * 0.8:
            insights.append("Expect a quieter period than recent history")

        return ActivityForecastResponse(
            prediction_type="activity",
            horizon=request.horizon,
            granularity=request.granularity,
            total_predicted=round(total_predicted, 1),
            average_daily=round(average_daily, 2),
            trend_direction=trend.value,
            confidence_level=confidence.value,
            point_forecast=[round(v, 2) for v in forecast.point_forecast],
            lower_bound=[round(v, 2) for v in forecast.lower_bound],
            upper_bound=[round(v, 2) for v in forecast.upper_bound],
            forecast_dates=forecast_dates,
            insights=insights,
            generated_at=datetime.utcnow().isoformat(),
        )

    @router.post("/entities/emerging", response_model=List[EntityTrendResponse])
    async def get_emerging_entities(
        request: EntityTrendRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Predict which entities will grow or decline in importance.

        Returns forecasts for top entities showing their predicted trajectory.
        """
        if not forecast_service.is_available:
            forecast_service.initialize()

        async with database.session() as session:
            extractor = EntityMentionExtractor(session)
            start_date = datetime.utcnow() - timedelta(days=request.lookback_days)

            if request.entity_value:
                series_dict = {
                    request.entity_value: await extractor.extract(
                        user_id=user.id,
                        start_date=start_date,
                        entity_type=request.entity_type,
                        entity_value=request.entity_value,
                    )
                }
            else:
                series_dict = await extractor.extract_top_entities(
                    user_id=user.id,
                    start_date=start_date,
                    entity_type=request.entity_type,
                    top_n=request.top_n,
                )

        if not series_dict:
            return []

        valid_series = {
            k: v for k, v in series_dict.items() if v.length >= 7 and sum(v.values) > 0
        }

        if not valid_series:
            return []

        forecasts = forecast_service.forecast_batch(
            {k: v.values for k, v in valid_series.items()},
            horizon=request.horizon,
        )

        results = []
        for key, series in valid_series.items():
            forecast = forecasts[key]
            parts = key.split(":", 1)
            entity_type = parts[0] if len(parts) > 1 else "unknown"
            entity_value = parts[1] if len(parts) > 1 else key

            current_mentions = int(sum(series.values[-14:]))
            predicted_mentions = int(sum(forecast.point_forecast))

            if current_mentions > 0:
                growth_rate = (predicted_mentions - current_mentions) / current_mentions
            else:
                growth_rate = 1.0 if predicted_mentions > 0 else 0.0

            trend = _determine_trend_direction(forecast.point_forecast)
            is_emerging = growth_rate > 0.2 and trend == TrendDirection.RISING
            is_fading = growth_rate < -0.2 and trend == TrendDirection.DECLINING
            emergence_score = min(1.0, max(0.0, growth_rate + 0.5))

            insights = []
            if is_emerging:
                insights.append(f"'{entity_value}' is gaining traction with {growth_rate:.0%} growth")
            elif is_fading:
                insights.append(f"'{entity_value}' is declining with {abs(growth_rate):.0%} decrease")

            results.append(
                EntityTrendResponse(
                    entity_type=entity_type,
                    entity_value=entity_value,
                    current_mentions=current_mentions,
                    predicted_mentions=predicted_mentions,
                    growth_rate=round(growth_rate, 3),
                    trend_direction=trend.value,
                    is_emerging=is_emerging,
                    is_fading=is_fading,
                    emergence_score=round(emergence_score, 3),
                    point_forecast=[round(v, 2) for v in forecast.point_forecast],
                    insights=insights,
                )
            )

        results.sort(key=lambda x: abs(x.growth_rate), reverse=True)
        return results

    @router.post("/relationships/forecast", response_model=List[RelationshipForecastResponse])
    async def forecast_relationships(
        request: RelationshipForecastRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Predict interaction patterns with people and projects.

        Returns dormancy risk scores and predicted next interaction timing.
        """
        if not forecast_service.is_available:
            forecast_service.initialize()

        async with database.session() as session:
            profile_extractor = ProfileMetricsExtractor(session)

            at_risk = await profile_extractor.get_dormancy_at_risk(
                user_id=user.id,
                dormancy_threshold_days=21,
            )

            if request.target_type:
                at_risk = [r for r in at_risk if r["type"] == request.target_type]
            if request.target_id:
                at_risk = [r for r in at_risk if r["id"] == request.target_id]

        results = []
        for entity in at_risk[:20]:
            dormancy_days = entity["dormancy_days"]
            days_until_dormant = entity["days_until_dormant"]

            dormancy_risk = min(1.0, dormancy_days / 21)

            if dormancy_risk > 0.7:
                follow_up_urgency = "high"
                recommended_action = f"Reach out to {entity['name']} within {days_until_dormant} days"
            elif dormancy_risk > 0.4:
                follow_up_urgency = "medium"
                recommended_action = f"Consider reconnecting with {entity['name']}"
            else:
                follow_up_urgency = "normal"
                recommended_action = None

            trend = TrendDirection.DECLINING if dormancy_risk > 0.5 else TrendDirection.STABLE

            mock_forecast = [
                max(0, 1 - dormancy_risk - 0.05 * i) for i in range(request.horizon)
            ]

            insights = []
            if dormancy_risk > 0.7:
                insights.append(f"High risk of losing touch with {entity['name']}")
            if dormancy_days > 14:
                insights.append(f"No interaction for {dormancy_days} days")

            results.append(
                RelationshipForecastResponse(
                    target_type=entity["type"],
                    target_id=entity["id"],
                    target_name=entity["name"],
                    days_since_last_interaction=dormancy_days,
                    predicted_next_interaction_day=days_until_dormant if dormancy_risk < 0.8 else None,
                    dormancy_risk=round(dormancy_risk, 3),
                    trend_direction=trend.value,
                    follow_up_urgency=follow_up_urgency,
                    recommended_action=recommended_action,
                    point_forecast=[round(v, 3) for v in mock_forecast],
                    insights=insights,
                )
            )

        results.sort(key=lambda x: x.dormancy_risk, reverse=True)
        return results

    @router.post("/graph/evolution", response_model=GraphEvolutionResponse)
    async def forecast_graph_evolution(
        request: GraphEvolutionRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Predict overall knowledge graph growth and structure changes.

        Returns forecasts for node/edge counts and cluster formation likelihood.
        """
        if not forecast_service.is_available:
            forecast_service.initialize()

        async with database.session() as session:
            activity_extractor = ActivityExtractor(session)
            connection_extractor = ConnectionRateExtractor(session)

            start_date = datetime.utcnow() - timedelta(days=request.lookback_days)

            activity_series = await activity_extractor.extract(
                user_id=user.id,
                start_date=start_date,
            )

            connection_series = await connection_extractor.extract(
                user_id=user.id,
                start_date=start_date,
            )

        current_node_count = int(sum(activity_series.values))
        current_edge_count = int(sum(connection_series.values))

        if activity_series.length >= 7:
            node_forecast = forecast_service.forecast_single(
                activity_series.values, horizon=request.horizon
            )
            predicted_nodes = sum(node_forecast.point_forecast)
            node_forecast_values = node_forecast.point_forecast
        else:
            avg = sum(activity_series.values[-7:]) / max(1, min(7, activity_series.length))
            node_forecast_values = [avg] * request.horizon
            predicted_nodes = avg * request.horizon

        if connection_series.length >= 7:
            edge_forecast = forecast_service.forecast_single(
                connection_series.values, horizon=request.horizon
            )
            predicted_edges = sum(edge_forecast.point_forecast)
            edge_forecast_values = edge_forecast.point_forecast
        else:
            avg = sum(connection_series.values[-7:]) / max(1, min(7, connection_series.length))
            edge_forecast_values = [avg] * request.horizon
            predicted_edges = avg * request.horizon

        recent_nodes = sum(activity_series.values[-request.horizon:])
        recent_edges = sum(connection_series.values[-request.horizon:])

        predicted_node_growth = (
            (predicted_nodes - recent_nodes) / max(recent_nodes, 1)
            if recent_nodes > 0
            else 0.0
        )
        predicted_edge_growth = (
            (predicted_edges - recent_edges) / max(recent_edges, 1)
            if recent_edges > 0
            else 0.0
        )

        node_trend = _determine_trend_direction(node_forecast_values)
        edge_trend = _determine_trend_direction(edge_forecast_values)

        if edge_trend == TrendDirection.RISING and predicted_edge_growth > 0.2:
            cluster_likelihood = 0.8
            density_trend = TrendDirection.RISING
        elif edge_trend == TrendDirection.DECLINING:
            cluster_likelihood = 0.2
            density_trend = TrendDirection.DECLINING
        else:
            cluster_likelihood = 0.5
            density_trend = TrendDirection.STABLE

        growth_drivers = []
        if node_trend == TrendDirection.RISING:
            growth_drivers.append("Increasing thought and event capture rate")
        if edge_trend == TrendDirection.RISING:
            growth_drivers.append("Growing connection discovery rate")
        if predicted_edge_growth > predicted_node_growth:
            growth_drivers.append("Graph becoming more interconnected")

        insights = []
        insights.append(
            f"Knowledge graph projected to grow by {predicted_node_growth:.0%} in nodes"
        )
        if cluster_likelihood > 0.6:
            insights.append("High likelihood of new topic clusters forming")
        if predicted_edge_growth > predicted_node_growth:
            insights.append("Connection density is increasing")

        return GraphEvolutionResponse(
            current_node_count=current_node_count,
            current_edge_count=current_edge_count,
            predicted_node_growth=round(predicted_node_growth, 3),
            predicted_edge_growth=round(predicted_edge_growth, 3),
            graph_density_trend=density_trend.value,
            cluster_formation_likelihood=round(cluster_likelihood, 3),
            node_forecast=[round(v, 2) for v in node_forecast_values],
            edge_forecast=[round(v, 2) for v in edge_forecast_values],
            growth_drivers=growth_drivers,
            insights=insights,
        )

    @router.get("/summary", response_model=PredictionSummaryResponse)
    async def get_prediction_summary(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a summary of all prediction types for the user.

        Provides a quick overview without generating full forecasts.
        """
        from sqlalchemy import func as sa_func, select as sa_select

        async with database.session() as session:
            activity_extractor = ActivityExtractor(session)
            entity_extractor = EntityMentionExtractor(session)
            connection_extractor = ConnectionRateExtractor(session)
            profile_extractor = ProfileMetricsExtractor(session)

            start_date = datetime.utcnow() - timedelta(days=30)

            activity = await activity_extractor.extract(
                user_id=user.id,
                start_date=start_date,
            )

            at_risk = await profile_extractor.get_dormancy_at_risk(
                user_id=user.id,
                dormancy_threshold_days=21,
            )

            entity_summary = None
            try:
                entity_series = await entity_extractor.extract_top_entities(
                    user_id=user.id,
                    start_date=start_date,
                    top_n=10,
                )
                if entity_series:
                    emerging = []
                    fading = []
                    for key, series in entity_series.items():
                        if series.length < 14:
                            continue
                        recent = sum(series.values[-7:])
                        prev = sum(series.values[-14:-7])
                        if prev > 0 and (recent - prev) / prev > 0.2:
                            emerging.append(key)
                        elif prev > 0 and (recent - prev) / prev < -0.2:
                            fading.append(key)

                    entity_summary = {
                        "total_tracked": len(entity_series),
                        "emerging_count": len(emerging),
                        "fading_count": len(fading),
                        "top_emerging": emerging[:3],
                    }
            except Exception:
                pass

            graph_summary = None
            try:
                connection_series = await connection_extractor.extract(
                    user_id=user.id,
                    start_date=start_date,
                )
                if activity.length >= 14 and connection_series.length >= 14:
                    recent_nodes = sum(activity.values[-7:])
                    prev_nodes = sum(activity.values[-14:-7])
                    recent_edges = sum(connection_series.values[-7:])
                    prev_edges = sum(connection_series.values[-14:-7])

                    node_growth = (
                        (recent_nodes - prev_nodes) / max(prev_nodes, 1)
                        if prev_nodes > 0
                        else 0.0
                    )
                    edge_growth = (
                        (recent_edges - prev_edges) / max(prev_edges, 1)
                        if prev_edges > 0
                        else 0.0
                    )
                    if edge_growth > 0.1:
                        density = "rising"
                    elif edge_growth < -0.1:
                        density = "declining"
                    else:
                        density = "stable"

                    graph_summary = {
                        "predicted_node_growth": round(node_growth, 3),
                        "predicted_edge_growth": round(edge_growth, 3),
                        "density_trend": density,
                    }
            except Exception:
                pass

        has_data = activity.length > 0

        activity_summary = None
        if activity.length >= 7:
            recent_avg = sum(activity.values[-7:]) / 7
            prev_avg = sum(activity.values[-14:-7]) / 7 if activity.length >= 14 else recent_avg
            change = (recent_avg - prev_avg) / max(prev_avg, 0.1)

            activity_summary = {
                "recent_average": round(recent_avg, 2),
                "change_from_previous": round(change, 3),
                "data_points": activity.length,
                "trend": "increasing" if change > 0.1 else "decreasing" if change < -0.1 else "stable",
            }

        relationship_summary = None
        if at_risk:
            people_at_risk = [r for r in at_risk if r["type"] == "person"]
            projects_at_risk = [r for r in at_risk if r["type"] == "project"]

            relationship_summary = {
                "people_at_risk": len(people_at_risk),
                "projects_at_risk": len(projects_at_risk),
                "most_urgent": at_risk[0]["name"] if at_risk else None,
                "urgent_days_left": at_risk[0]["days_until_dormant"] if at_risk else None,
            }

        return PredictionSummaryResponse(
            user_id=str(user.id),
            has_predictions=has_data,
            activity_summary=activity_summary,
            entity_summary=entity_summary,
            relationship_summary=relationship_summary,
            graph_summary=graph_summary,
            generated_at=datetime.utcnow().isoformat(),
        )

    @router.get("/dormancy-risk", response_model=List[DormancyRiskResponse])
    async def get_dormancy_risk(
        limit: int = Query(default=10, ge=1, le=50),
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get people and projects at risk of becoming dormant.

        Ordered by urgency (days until dormant).
        """
        async with database.session() as session:
            extractor = ProfileMetricsExtractor(session)
            at_risk = await extractor.get_dormancy_at_risk(
                user_id=user.id,
                dormancy_threshold_days=21,
            )

        results = []
        for entity in at_risk[:limit]:
            days_until = entity["days_until_dormant"]
            if days_until <= 3:
                risk_level = "critical"
            elif days_until <= 7:
                risk_level = "high"
            else:
                risk_level = "medium"

            last_activity = entity.get("last_seen") or entity.get("last_activity_at")

            results.append(
                DormancyRiskResponse(
                    type=entity["type"],
                    id=entity["id"],
                    name=entity["name"],
                    dormancy_days=entity["dormancy_days"],
                    days_until_dormant=days_until,
                    risk_level=risk_level,
                    last_activity=last_activity,
                )
            )

        return results

    @router.get("/accuracy")
    async def get_forecast_accuracy(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Compute retrospective accuracy by comparing last week's forecast vs actuals."""
        async with database.session() as session:
            extractor = ActivityExtractor(session)

            start_date = datetime.utcnow() - timedelta(days=21)
            series = await extractor.extract(
                user_id=user.id,
                start_date=start_date,
            )

        if series.length < 14:
            return {
                "available": False,
                "message": "Not enough historical data for accuracy measurement",
            }

        training = series.values[:-7]
        actuals = series.values[-7:]

        if not forecast_service.is_available:
            forecast_service.initialize()

        try:
            forecast = forecast_service.forecast_activity(
                daily_counts=training,
                horizon=7,
            )
            predicted = forecast.point_forecast
        except Exception:
            return {"available": False, "message": "Forecast generation failed"}

        errors = []
        for pred, actual in zip(predicted, actuals):
            if actual != 0:
                errors.append(abs(pred - actual) / abs(actual))
            elif pred == 0:
                errors.append(0.0)
            else:
                errors.append(1.0)

        mape = sum(errors) / len(errors) if errors else 0.0
        mae = sum(abs(p - a) for p, a in zip(predicted, actuals)) / len(actuals)
        accuracy = round(1 - min(mape, 1.0), 4)

        within_band = 0
        for i, actual in enumerate(actuals):
            lower = forecast.lower_bound[i] if i < len(forecast.lower_bound) else 0
            upper = forecast.upper_bound[i] if i < len(forecast.upper_bound) else float("inf")
            if lower <= actual <= upper:
                within_band += 1
        coverage = round(within_band / len(actuals), 4)

        return {
            "available": True,
            "accuracy": accuracy,
            "mape": round(mape, 4),
            "mae": round(mae, 4),
            "coverage": coverage,
            "sample_days": len(actuals),
            "computed_at": datetime.utcnow().isoformat(),
        }

    return router
