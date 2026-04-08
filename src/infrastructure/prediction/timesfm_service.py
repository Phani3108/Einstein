"""TimesFM service for time-series forecasting.

Wraps Google's TimesFM 2.5 foundation model for zero-shot time-series
forecasting with quantile predictions.

numpy and torch are optional dependencies — imported lazily inside methods
so the module can be loaded in environments (e.g. Vercel) where only the
base dependencies are installed.
"""

from dataclasses import dataclass
from typing import Optional, Sequence
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Result of a time-series forecast."""

    point_forecast: list[float]
    quantile_forecast: list[list[float]]
    horizon: int
    context_length: int
    quantiles: list[float]

    @property
    def lower_bound(self) -> list[float]:
        """10th percentile (lower confidence bound)."""
        return [q[0] for q in self.quantile_forecast]

    @property
    def upper_bound(self) -> list[float]:
        """90th percentile (upper confidence bound)."""
        return [q[-1] for q in self.quantile_forecast]

    @property
    def median(self) -> list[float]:
        """50th percentile (median forecast)."""
        mid_idx = len(self.quantiles) // 2
        return [q[mid_idx] for q in self.quantile_forecast]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "point_forecast": self.point_forecast,
            "quantile_forecast": self.quantile_forecast,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "median": self.median,
            "horizon": self.horizon,
            "context_length": self.context_length,
            "quantiles": self.quantiles,
        }


@dataclass
class TimesFMConfig:
    """Configuration for TimesFM model."""

    max_context: int = 1024
    max_horizon: int = 256
    normalize_inputs: bool = True
    use_continuous_quantile_head: bool = True
    force_flip_invariance: bool = True
    infer_is_positive: bool = True
    fix_quantile_crossing: bool = True
    device: str = "cpu"


class TimesFMService:
    """Service for time-series forecasting using TimesFM 2.5.

    Provides zero-shot forecasting capabilities with quantile predictions
    for activity patterns, entity emergence, and relationship dynamics.
    """

    def __init__(self, config: Optional[TimesFMConfig] = None):
        """Initialize the TimesFM service.

        Args:
            config: Configuration for the model. Uses defaults if not provided.
        """
        self._config = config or TimesFMConfig()
        self._model = None
        self._is_initialized = False
        self._quantiles = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    def _check_timesfm_available(self) -> bool:
        """Check if TimesFM is installed."""
        try:
            import timesfm  # noqa: F401
            return True
        except ImportError:
            return False

    def initialize(self) -> bool:
        """Initialize and load the TimesFM model.

        Returns:
            True if initialization successful, False otherwise.
        """
        if self._is_initialized:
            return True

        if not self._check_timesfm_available():
            logger.warning(
                "TimesFM not installed. Install with: "
                "pip install 'einstein-semantic-engine[prediction]'"
            )
            return False

        try:
            import torch
            import timesfm

            if self._config.device == "cuda" and torch.cuda.is_available():
                torch.set_float32_matmul_precision("high")
                logger.info("Using CUDA for TimesFM inference")
            else:
                logger.info("Using CPU for TimesFM inference")

            logger.info("Loading TimesFM 2.5 model from HuggingFace...")
            self._model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
                "google/timesfm-2.5-200m-pytorch"
            )

            logger.info("Compiling TimesFM model...")
            self._model.compile(
                timesfm.ForecastConfig(
                    max_context=self._config.max_context,
                    max_horizon=self._config.max_horizon,
                    normalize_inputs=self._config.normalize_inputs,
                    use_continuous_quantile_head=self._config.use_continuous_quantile_head,
                    force_flip_invariance=self._config.force_flip_invariance,
                    infer_is_positive=self._config.infer_is_positive,
                    fix_quantile_crossing=self._config.fix_quantile_crossing,
                )
            )

            self._is_initialized = True
            logger.info("TimesFM model initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize TimesFM: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """Check if the service is ready for forecasting."""
        return self._is_initialized and self._model is not None

    def forecast(
        self,
        inputs: Sequence[Sequence[float]],
        horizon: int = 7,
    ) -> list[ForecastResult]:
        """Generate forecasts for one or more time series.

        Args:
            inputs: List of time series (each as a sequence of floats).
            horizon: Number of future time steps to forecast.

        Returns:
            List of ForecastResult objects, one per input series.

        Raises:
            RuntimeError: If model is not initialized.
            ValueError: If inputs are invalid.
        """
        if not self.is_available:
            raise RuntimeError(
                "TimesFM model not initialized. Call initialize() first."
            )

        if not inputs:
            raise ValueError("At least one input series is required")

        import numpy as np

        horizon = min(horizon, self._config.max_horizon)

        np_inputs = [np.array(series, dtype=np.float64) for series in inputs]

        for i, series in enumerate(np_inputs):
            if len(series) < 3:
                raise ValueError(
                    f"Series {i} has only {len(series)} points. "
                    "Minimum 3 points required."
                )

        try:
            point_forecasts, quantile_forecasts = self._model.forecast(
                horizon=horizon,
                inputs=np_inputs,
            )

            results = []
            for i in range(len(inputs)):
                results.append(
                    ForecastResult(
                        point_forecast=point_forecasts[i].tolist(),
                        quantile_forecast=quantile_forecasts[i].tolist(),
                        horizon=horizon,
                        context_length=len(inputs[i]),
                        quantiles=self._quantiles,
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            raise

    def forecast_single(
        self,
        series: Sequence[float],
        horizon: int = 7,
    ) -> ForecastResult:
        """Generate forecast for a single time series.

        Args:
            series: Time series as a sequence of floats.
            horizon: Number of future time steps to forecast.

        Returns:
            ForecastResult for the input series.
        """
        results = self.forecast([series], horizon=horizon)
        return results[0]

    def forecast_activity(
        self,
        daily_counts: Sequence[float],
        horizon: int = 7,
    ) -> ForecastResult:
        """Forecast daily activity levels.

        Specialized method for forecasting thought/event counts.

        Args:
            daily_counts: Historical daily activity counts.
            horizon: Days to forecast ahead.

        Returns:
            ForecastResult with activity predictions.
        """
        return self.forecast_single(daily_counts, horizon=horizon)

    def forecast_entity_trend(
        self,
        mention_counts: Sequence[float],
        horizon: int = 14,
    ) -> ForecastResult:
        """Forecast entity mention trends.

        Args:
            mention_counts: Historical daily mention counts for an entity.
            horizon: Days to forecast ahead.

        Returns:
            ForecastResult with trend predictions.
        """
        return self.forecast_single(mention_counts, horizon=horizon)

    def forecast_batch(
        self,
        series_dict: dict[str, Sequence[float]],
        horizon: int = 7,
    ) -> dict[str, ForecastResult]:
        """Batch forecast multiple named time series.

        Args:
            series_dict: Dictionary mapping series names to their data.
            horizon: Number of future time steps to forecast.

        Returns:
            Dictionary mapping series names to their forecasts.
        """
        names = list(series_dict.keys())
        series_list = list(series_dict.values())

        results = self.forecast(series_list, horizon=horizon)

        return dict(zip(names, results))


class MockTimesFMService(TimesFMService):
    """Mock TimesFM service for testing without the actual model.

    Generates simple trend-based forecasts for testing purposes.
    """

    def initialize(self) -> bool:
        """Initialize mock service (always succeeds)."""
        self._is_initialized = True
        logger.info("Mock TimesFM service initialized")
        return True

    @property
    def is_available(self) -> bool:
        """Mock is always available once initialized."""
        return self._is_initialized

    def forecast(
        self,
        inputs: Sequence[Sequence[float]],
        horizon: int = 7,
    ) -> list[ForecastResult]:
        """Generate mock forecasts based on simple trend extrapolation."""
        if not self._is_initialized:
            raise RuntimeError("Mock service not initialized")

        results = []
        for series in inputs:
            vals = list(series)
            recent = vals[-min(7, len(vals)):]
            mean = sum(recent) / len(recent) if recent else 0.0
            variance = sum((v - mean) ** 2 for v in recent) / len(recent) if recent else 0.0
            std = max(variance ** 0.5, 0.1)

            if len(vals) >= 2:
                trend = (vals[-1] - vals[-2]) / 2
            else:
                trend = 0

            point = []
            for i in range(horizon):
                predicted = mean + trend * i
                predicted = max(0, predicted)
                point.append(predicted)

            quantiles = []
            for i, p in enumerate(point):
                q_vals = [
                    max(0, p - 1.5 * std),
                    max(0, p - 1.0 * std),
                    max(0, p - 0.5 * std),
                    max(0, p - 0.2 * std),
                    p,
                    p + 0.2 * std,
                    p + 0.5 * std,
                    p + 1.0 * std,
                    p + 1.5 * std,
                ]
                quantiles.append(q_vals)

            results.append(
                ForecastResult(
                    point_forecast=point,
                    quantile_forecast=quantiles,
                    horizon=horizon,
                    context_length=len(series),
                    quantiles=self._quantiles,
                )
            )

        return results


def get_timesfm_service(
    config: Optional[TimesFMConfig] = None,
    use_mock: bool = False,
) -> TimesFMService:
    """Factory function to get a TimesFM service instance.

    Args:
        config: Optional configuration for the model.
        use_mock: If True, returns a mock service for testing.

    Returns:
        TimesFMService instance (real or mock).
    """
    if use_mock or os.getenv("USE_MOCK_TIMESFM", "").lower() == "true":
        return MockTimesFMService(config)
    return TimesFMService(config)
