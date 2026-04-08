"""Prediction module for the Personal Semantic Engine.

This package provides time-series forecasting capabilities using Google's TimesFM
foundation model to predict knowledge graph evolution, entity emergence,
relationship dynamics, and activity patterns.

All imports are lazy to avoid pulling in optional dependencies (numpy, torch,
timesfm) at module load time — critical for serverless environments like Vercel
where only base dependencies are installed.
"""


def __getattr__(name: str):
    """Lazy-load prediction classes on first access."""
    if name == "TimesFMService":
        from .timesfm_service import TimesFMService
        return TimesFMService
    if name == "TimeSeriesExtractor":
        from .time_series_extractor import TimeSeriesExtractor
        return TimeSeriesExtractor
    if name == "ActivityExtractor":
        from .time_series_extractor import ActivityExtractor
        return ActivityExtractor
    if name == "EntityMentionExtractor":
        from .time_series_extractor import EntityMentionExtractor
        return EntityMentionExtractor
    if name == "ConnectionRateExtractor":
        from .time_series_extractor import ConnectionRateExtractor
        return ConnectionRateExtractor
    if name == "ProfileMetricsExtractor":
        from .time_series_extractor import ProfileMetricsExtractor
        return ProfileMetricsExtractor
    if name == "ForecastCache":
        from .forecast_cache import ForecastCache
        return ForecastCache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "TimesFMService",
    "TimeSeriesExtractor",
    "ActivityExtractor",
    "EntityMentionExtractor",
    "ConnectionRateExtractor",
    "ProfileMetricsExtractor",
    "ForecastCache",
]
