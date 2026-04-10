"""Prediction module for the Personal Semantic Engine.

This package provides time-series forecasting to predict knowledge graph evolution,
entity emergence, relationship dynamics, and activity patterns.

All imports are lazy to avoid pulling in optional dependencies (numpy, torch,
and related packages) at module load time — critical for serverless environments
like Vercel where only base dependencies are installed.
"""


def __getattr__(name: str):
    """Lazy-load prediction classes on first access."""
    if name == "ForecastService":
        from .forecast_service import ForecastService
        return ForecastService
    if name == "StatisticalForecastService":
        from .forecast_service import StatisticalForecastService
        return StatisticalForecastService
    if name == "HFInferenceForecastService":
        from .forecast_service import HFInferenceForecastService
        return HFInferenceForecastService
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
    "ForecastService",
    "StatisticalForecastService",
    "HFInferenceForecastService",
    "TimeSeriesExtractor",
    "ActivityExtractor",
    "EntityMentionExtractor",
    "ConnectionRateExtractor",
    "ProfileMetricsExtractor",
    "ForecastCache",
]
