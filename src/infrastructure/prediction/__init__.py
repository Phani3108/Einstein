"""Prediction module for the Personal Semantic Engine.

This package provides time-series forecasting capabilities using Google's TimesFM
foundation model to predict knowledge graph evolution, entity emergence,
relationship dynamics, and activity patterns.
"""

from .timesfm_service import TimesFMService
from .time_series_extractor import (
    TimeSeriesExtractor,
    ActivityExtractor,
    EntityMentionExtractor,
    ConnectionRateExtractor,
    ProfileMetricsExtractor,
)
from .forecast_cache import ForecastCache

__all__ = [
    "TimesFMService",
    "TimeSeriesExtractor",
    "ActivityExtractor",
    "EntityMentionExtractor",
    "ConnectionRateExtractor",
    "ProfileMetricsExtractor",
    "ForecastCache",
]
