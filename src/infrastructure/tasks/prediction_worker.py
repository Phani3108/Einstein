"""Prediction worker: Scheduled forecasts and cache updates.

Responsibilities:
  - Pre-compute daily forecasts for active users
  - Update prediction cache with fresh forecasts
  - Track prediction accuracy over time
  - Generate prediction summaries for briefings

Runs as a daily cron job (recommended: 5 AM local time).
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_

from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import (
    Thought,
    ContextEventModel,
    PersonProfileModel,
    ProjectModel,
    User,
)
from src.infrastructure.prediction.forecast_service import (
    ForecastService,
    ForecastConfig,
    get_forecast_service,
)
from src.infrastructure.prediction.time_series_extractor import (
    ActivityExtractor,
    EntityMentionExtractor,
    ConnectionRateExtractor,
    ProfileMetricsExtractor,
)
from src.infrastructure.prediction.forecast_cache import ForecastCache

logger = logging.getLogger(__name__)

MIN_DATA_POINTS = 14
DEFAULT_HORIZON = 7
CACHE_TTL_HOURS = 24


async def run_prediction_job(
    database: Database,
    redis_client: Optional[Any] = None,
    user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Run the prediction job for one or all users.

    Args:
        database: Database connection.
        redis_client: Optional Redis client for caching.
        user_id: Optional specific user to process (all active users if None).

    Returns:
        Job statistics including users processed and forecasts generated.
    """
    start_time = datetime.utcnow()
    stats = {
        "started_at": start_time.isoformat(),
        "users_processed": 0,
        "activity_forecasts": 0,
        "entity_forecasts": 0,
        "relationship_forecasts": 0,
        "graph_forecasts": 0,
        "errors": [],
    }

    use_mock = os.getenv("USE_MOCK_FORECASTS", "true").lower() == "true"
    forecast_service = get_forecast_service(use_mock=use_mock)

    if not forecast_service.initialize():
        stats["errors"].append("Failed to initialize forecast service")
        logger.warning("Forecast service initialization failed, using mock forecasts")

    cache = None
    if redis_client:
        cache = ForecastCache(redis_client, default_ttl_hours=CACHE_TTL_HOURS)

    async with database.session() as session:
        if user_id:
            user_ids = [user_id]
        else:
            result = await session.execute(
                select(User.id).where(User.is_active == True)
            )
            user_ids = [row[0] for row in result.fetchall()]

    for uid in user_ids:
        try:
            user_stats = await _process_user_predictions(
                database=database,
                user_id=uid,
                forecast_service=forecast_service,
                cache=cache,
            )

            stats["users_processed"] += 1
            stats["activity_forecasts"] += user_stats.get("activity", 0)
            stats["entity_forecasts"] += user_stats.get("entities", 0)
            stats["relationship_forecasts"] += user_stats.get("relationships", 0)
            stats["graph_forecasts"] += user_stats.get("graph", 0)

        except Exception as e:
            logger.error(f"Error processing predictions for user {uid}: {e}")
            stats["errors"].append(f"User {uid}: {str(e)}")

    stats["completed_at"] = datetime.utcnow().isoformat()
    stats["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        f"Prediction job completed: {stats['users_processed']} users, "
        f"{stats['activity_forecasts']} activity forecasts, "
        f"{stats['entity_forecasts']} entity forecasts"
    )

    return stats


async def _process_user_predictions(
    database: Database,
    user_id: UUID,
    forecast_service: ForecastService,
    cache: Optional[ForecastCache],
) -> Dict[str, int]:
    """Process all prediction types for a single user.

    Returns:
        Dict with counts of forecasts generated per type.
    """
    stats = {"activity": 0, "entities": 0, "relationships": 0, "graph": 0}

    async with database.session() as session:
        activity_extractor = ActivityExtractor(session)
        entity_extractor = EntityMentionExtractor(session)
        connection_extractor = ConnectionRateExtractor(session)
        profile_extractor = ProfileMetricsExtractor(session)

        start_date = datetime.utcnow() - timedelta(days=90)

        activity_series = await activity_extractor.extract(
            user_id=user_id,
            start_date=start_date,
        )

        if activity_series.length >= MIN_DATA_POINTS:
            try:
                forecast = forecast_service.forecast_activity(
                    daily_counts=activity_series.values,
                    horizon=DEFAULT_HORIZON,
                )

                if cache:
                    await cache.set(
                        user_id=str(user_id),
                        forecast_type="activity",
                        data={
                            "point_forecast": forecast.point_forecast,
                            "lower_bound": forecast.lower_bound,
                            "upper_bound": forecast.upper_bound,
                            "horizon": forecast.horizon,
                            "context_length": forecast.context_length,
                            "generated_at": datetime.utcnow().isoformat(),
                        },
                    )

                stats["activity"] = 1
                logger.debug(f"Generated activity forecast for user {user_id}")

            except Exception as e:
                logger.warning(f"Activity forecast failed for {user_id}: {e}")

        entity_series_dict = await entity_extractor.extract_top_entities(
            user_id=user_id,
            start_date=start_date,
            top_n=10,
        )

        valid_entities = {
            k: v for k, v in entity_series_dict.items()
            if v.length >= MIN_DATA_POINTS and sum(v.values) > 0
        }

        if valid_entities:
            try:
                forecasts = forecast_service.forecast_batch(
                    {k: v.values for k, v in valid_entities.items()},
                    horizon=DEFAULT_HORIZON,
                )

                if cache:
                    entity_data = {
                        key: {
                            "point_forecast": forecast.point_forecast,
                            "growth_rate": _calculate_growth_rate(
                                valid_entities[key].values, forecast.point_forecast
                            ),
                        }
                        for key, forecast in forecasts.items()
                    }
                    await cache.set(
                        user_id=str(user_id),
                        forecast_type="entities",
                        data=entity_data,
                    )

                stats["entities"] = len(forecasts)
                logger.debug(
                    f"Generated {len(forecasts)} entity forecasts for user {user_id}"
                )

            except Exception as e:
                logger.warning(f"Entity forecasts failed for {user_id}: {e}")

        connection_series = await connection_extractor.extract(
            user_id=user_id,
            start_date=start_date,
        )

        if connection_series.length >= MIN_DATA_POINTS:
            try:
                forecast = forecast_service.forecast_single(
                    connection_series.values,
                    horizon=DEFAULT_HORIZON,
                )

                if cache:
                    await cache.set(
                        user_id=str(user_id),
                        forecast_type="graph",
                        data={
                            "connection_forecast": forecast.point_forecast,
                            "total_predicted": sum(forecast.point_forecast),
                            "generated_at": datetime.utcnow().isoformat(),
                        },
                    )

                stats["graph"] = 1
                logger.debug(f"Generated graph forecast for user {user_id}")

            except Exception as e:
                logger.warning(f"Graph forecast failed for {user_id}: {e}")

        at_risk = await profile_extractor.get_dormancy_at_risk(
            user_id=user_id,
            dormancy_threshold_days=21,
        )

        if at_risk and cache:
            await cache.set(
                user_id=str(user_id),
                forecast_type="relationships",
                data={
                    "at_risk_count": len(at_risk),
                    "at_risk": at_risk[:10],
                    "generated_at": datetime.utcnow().isoformat(),
                },
            )
            stats["relationships"] = len(at_risk)

    return stats


def _calculate_growth_rate(historical: List[float], forecast: List[float]) -> float:
    """Calculate growth rate between recent history and forecast."""
    if not historical or not forecast:
        return 0.0

    recent = sum(historical[-7:]) if len(historical) >= 7 else sum(historical)
    predicted = sum(forecast)

    if recent == 0:
        return 1.0 if predicted > 0 else 0.0

    return (predicted - recent) / recent


async def get_cached_predictions(
    redis_client: Any,
    user_id: UUID,
) -> Dict[str, Any]:
    """Retrieve all cached predictions for a user.

    Args:
        redis_client: Redis client.
        user_id: User identifier.

    Returns:
        Dict with all cached predictions by type.
    """
    cache = ForecastCache(redis_client)
    return await cache.get_all_user_forecasts(str(user_id))


async def invalidate_user_predictions(
    redis_client: Any,
    user_id: UUID,
    forecast_type: Optional[str] = None,
) -> int:
    """Invalidate cached predictions for a user.

    Args:
        redis_client: Redis client.
        user_id: User identifier.
        forecast_type: Optional specific type to invalidate.

    Returns:
        Number of cache entries invalidated.
    """
    cache = ForecastCache(redis_client)
    return await cache.invalidate(
        user_id=str(user_id),
        forecast_type=forecast_type,
    )


async def generate_prediction_briefing(
    database: Database,
    user_id: UUID,
    redis_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generate a prediction briefing for morning/weekly insights.

    This can be integrated with the insight_worker's briefing generation.

    Args:
        database: Database connection.
        user_id: User identifier.
        redis_client: Optional Redis client for cached predictions.

    Returns:
        Dict with prediction highlights for briefing.
    """
    briefing = {
        "has_predictions": False,
        "activity_outlook": None,
        "emerging_topics": [],
        "relationships_at_risk": [],
        "graph_growth": None,
    }

    if redis_client:
        cached = await get_cached_predictions(redis_client, user_id)

        if "activity" in cached:
            data = cached["activity"].get("data", {})
            point = data.get("point_forecast", [])
            if point:
                avg = sum(point) / len(point)
                briefing["activity_outlook"] = {
                    "average_daily": round(avg, 1),
                    "horizon_days": len(point),
                    "trend": "increasing" if point[-1] > point[0] else "decreasing",
                }
                briefing["has_predictions"] = True

        if "entities" in cached:
            data = cached["entities"].get("data", {})
            emerging = [
                {"entity": k, "growth_rate": v.get("growth_rate", 0)}
                for k, v in data.items()
                if isinstance(v, dict) and v.get("growth_rate", 0) > 0.2
            ]
            briefing["emerging_topics"] = sorted(
                emerging, key=lambda x: x["growth_rate"], reverse=True
            )[:3]
            if emerging:
                briefing["has_predictions"] = True

        if "relationships" in cached:
            data = cached["relationships"].get("data", {})
            at_risk = data.get("at_risk", [])
            if at_risk:
                briefing["relationships_at_risk"] = [
                    {"name": r["name"], "days_until_dormant": r["days_until_dormant"]}
                    for r in at_risk[:3]
                ]
                briefing["has_predictions"] = True

        if "graph" in cached:
            data = cached["graph"].get("data", {})
            total = data.get("total_predicted", 0)
            if total > 0:
                briefing["graph_growth"] = {
                    "predicted_connections": round(total, 1),
                    "horizon_days": DEFAULT_HORIZON,
                }
                briefing["has_predictions"] = True

    if not briefing["has_predictions"]:
        async with database.session() as session:
            profile_extractor = ProfileMetricsExtractor(session)
            at_risk = await profile_extractor.get_dormancy_at_risk(
                user_id=user_id,
                dormancy_threshold_days=21,
            )

            if at_risk:
                briefing["relationships_at_risk"] = [
                    {"name": r["name"], "days_until_dormant": r["days_until_dormant"]}
                    for r in at_risk[:3]
                ]
                briefing["has_predictions"] = True

    return briefing


async def track_prediction_accuracy(
    database: Database,
    user_id: UUID,
    prediction_type: str,
    predicted_values: List[float],
    actual_values: List[float],
) -> Dict[str, float]:
    """Track and store prediction accuracy metrics.

    Computes MAPE (Mean Absolute Percentage Error) and coverage metrics.

    Args:
        database: Database connection.
        user_id: User identifier.
        prediction_type: Type of prediction (activity, entity, etc.).
        predicted_values: Predicted values from past forecast.
        actual_values: Actual observed values.

    Returns:
        Dict with accuracy metrics.
    """
    if len(predicted_values) != len(actual_values):
        min_len = min(len(predicted_values), len(actual_values))
        predicted_values = predicted_values[:min_len]
        actual_values = actual_values[:min_len]

    if not predicted_values:
        return {"error": "No values to compare"}

    errors = []
    for pred, actual in zip(predicted_values, actual_values):
        if actual != 0:
            errors.append(abs(pred - actual) / abs(actual))
        elif pred == 0:
            errors.append(0.0)
        else:
            errors.append(1.0)

    mape = sum(errors) / len(errors) if errors else 0.0

    mae = sum(abs(p - a) for p, a in zip(predicted_values, actual_values)) / len(
        predicted_values
    )

    metrics = {
        "mape": round(mape, 4),
        "mae": round(mae, 4),
        "accuracy": round(1 - min(mape, 1.0), 4),
        "sample_size": len(predicted_values),
        "prediction_type": prediction_type,
        "computed_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Prediction accuracy for {user_id}/{prediction_type}: "
        f"MAPE={mape:.2%}, Accuracy={metrics['accuracy']:.2%}"
    )

    return metrics
