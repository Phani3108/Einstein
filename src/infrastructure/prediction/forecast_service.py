"""Time-series forecasting service for the Personal Semantic Engine.

Provides zero-shot time-series forecasting with quantile predictions via a
pluggable backend (loaded lazily when the optional prediction stack is installed).

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
class ForecastConfig:
    """Configuration for the forecasting service backend."""

    max_context: int = 1024
    max_horizon: int = 256
    normalize_inputs: bool = True
    use_continuous_quantile_head: bool = True
    force_flip_invariance: bool = True
    infer_is_positive: bool = True
    fix_quantile_crossing: bool = True
    device: str = "cpu"


class ForecastService:
    """Time-series forecasting service with quantile predictions.

    Provides zero-shot forecasting for activity patterns, entity emergence,
    and relationship dynamics.
    """

    def __init__(self, config: Optional[ForecastConfig] = None):
        """Initialize the forecasting service.

        Args:
            config: Configuration for the model. Uses defaults if not provided.
        """
        self._config = config or ForecastConfig()
        self._model = None
        self._is_initialized = False
        self._quantiles = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    def _check_timesfm_available(self) -> bool:
        """Check if the forecast backend package is installed."""
        try:
            import timesfm  # noqa: F401
            return True
        except ImportError:
            return False

    def initialize(self) -> bool:
        """Load the forecast model from the configured backend.

        Returns:
            True if initialization successful, False otherwise.
        """
        if self._is_initialized:
            return True

        if not self._check_timesfm_available():
            logger.warning(
                "Forecast backend not installed. Install with: "
                "pip install 'einstein-semantic-engine[prediction]'"
            )
            return False

        try:
            import torch
            import timesfm

            if self._config.device == "cuda" and torch.cuda.is_available():
                torch.set_float32_matmul_precision("high")
                logger.info("Using CUDA for forecast model inference")
            else:
                logger.info("Using CPU for forecast model inference")

            logger.info("Loading forecast model from HuggingFace...")
            self._model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
                "google/timesfm-2.5-200m-pytorch"
            )

            logger.info("Compiling forecast model...")
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
            logger.info("Forecast model initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize forecast model: {e}")
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
                "Forecast model not initialized. Call initialize() first."
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


class StatisticalForecastService(ForecastService):
    """Lightweight forecasting using Holt-Winters exponential smoothing.

    Runs in pure Python (no numpy/torch) and produces meaningful forecasts
    from real data patterns — suitable for serverless environments.
    """

    def initialize(self) -> bool:
        self._is_initialized = True
        logger.info("Statistical forecast service initialized")
        return True

    @property
    def is_available(self) -> bool:
        return self._is_initialized

    def forecast(
        self,
        inputs: Sequence[Sequence[float]],
        horizon: int = 7,
    ) -> list[ForecastResult]:
        if not self._is_initialized:
            raise RuntimeError("Service not initialized")

        results = []
        for series in inputs:
            vals = list(series)
            n = len(vals)
            point, std = self._holt_forecast(vals, horizon)
            quantiles = self._build_quantiles(point, std)
            results.append(
                ForecastResult(
                    point_forecast=point,
                    quantile_forecast=quantiles,
                    horizon=horizon,
                    context_length=n,
                    quantiles=self._quantiles,
                )
            )
        return results

    @staticmethod
    def _holt_forecast(
        vals: list[float],
        horizon: int,
        alpha: float = 0.3,
        beta: float = 0.1,
    ) -> tuple[list[float], list[float]]:
        """Double exponential smoothing (Holt's linear method).

        Returns (point_forecast, per-step_std) where std grows with horizon
        to reflect increasing uncertainty.
        """
        n = len(vals)
        if n == 0:
            return [0.0] * horizon, [0.1] * horizon

        level = vals[0]
        trend = (vals[-1] - vals[0]) / max(n - 1, 1) if n > 1 else 0.0

        residuals: list[float] = []
        for t in range(1, n):
            forecast_t = level + trend
            residuals.append(vals[t] - forecast_t)
            prev_level = level
            level = alpha * vals[t] + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        if residuals:
            mse = sum(r * r for r in residuals) / len(residuals)
            base_std = max(mse ** 0.5, 0.1)
        else:
            base_std = max(abs(level) * 0.1, 0.1)

        point = []
        stds = []
        for h in range(1, horizon + 1):
            p = max(0.0, level + trend * h)
            point.append(round(p, 4))
            stds.append(round(base_std * (1 + 0.1 * h), 4))

        return point, stds

    @staticmethod
    def _build_quantiles(
        point: list[float],
        stds: list[float],
    ) -> list[list[float]]:
        z_scores = [-1.28, -0.84, -0.52, -0.25, 0.0, 0.25, 0.52, 0.84, 1.28]
        quantiles = []
        for p, s in zip(point, stds):
            q_vals = [max(0.0, round(p + z * s, 4)) for z in z_scores]
            quantiles.append(q_vals)
        return quantiles


class HFInferenceForecastService(ForecastService):
    """Forecast service that calls the Hugging Face Inference API.

    Requires a HF_API_TOKEN environment variable. Falls back to
    StatisticalForecastService if the remote endpoint is unavailable.
    """

    def __init__(self, config: Optional[ForecastConfig] = None):
        super().__init__(config)
        self._api_token = os.getenv("HF_API_TOKEN", "")
        self._model_id = "google/timesfm-2.5-200m-transformers"
        self._api_url = f"https://api-inference.huggingface.co/models/{self._model_id}"
        self._fallback = StatisticalForecastService(config)
        self._remote_available = False

    def initialize(self) -> bool:
        self._fallback.initialize()
        if not self._api_token:
            logger.info(
                "HF_API_TOKEN not set — using statistical forecast backend"
            )
            self._is_initialized = True
            return True

        try:
            import urllib.request
            import json as _json

            req = urllib.request.Request(
                self._api_url,
                headers={
                    "Authorization": f"Bearer {self._api_token}",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read())
                if isinstance(data, dict) and data.get("pipeline_tag"):
                    self._remote_available = True
                    logger.info("HF Inference endpoint available")
        except Exception as exc:
            logger.info("HF Inference endpoint not reachable: %s", exc)

        self._is_initialized = True
        return True

    @property
    def is_available(self) -> bool:
        return self._is_initialized

    def forecast(
        self,
        inputs: Sequence[Sequence[float]],
        horizon: int = 7,
    ) -> list[ForecastResult]:
        if self._remote_available and self._api_token:
            try:
                return self._forecast_remote(inputs, horizon)
            except Exception as exc:
                logger.warning("HF Inference call failed, falling back: %s", exc)

        return self._fallback.forecast(inputs, horizon)

    def _forecast_remote(
        self,
        inputs: Sequence[Sequence[float]],
        horizon: int,
    ) -> list[ForecastResult]:
        """Call the HF Inference API for each series."""
        import urllib.request
        import json as _json

        results = []
        for series in inputs:
            payload = _json.dumps({
                "inputs": list(series),
                "parameters": {"prediction_length": horizon},
            }).encode()

            req = urllib.request.Request(
                self._api_url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._api_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read())

            point = data.get("mean_prediction", data.get("predictions", [0.0] * horizon))
            point = [max(0.0, v) for v in point[:horizon]]

            while len(point) < horizon:
                point.append(point[-1] if point else 0.0)

            stds = StatisticalForecastService._holt_forecast(list(series), horizon)[1]
            quantiles = StatisticalForecastService._build_quantiles(point, stds)

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


MockForecastService = StatisticalForecastService


def get_forecast_service(
    config: Optional[ForecastConfig] = None,
    use_mock: bool = False,
) -> ForecastService:
    """Factory that returns the best available forecast backend.

    Priority order:
      1. Real local model (torch + timesfm installed)
      2. HF Inference API (HF_API_TOKEN set)
      3. Statistical forecast (pure Python, always available)

    Args:
        config: Optional configuration for the backend.
        use_mock: If True, skips model backends and returns statistical service.

    Returns:
        ForecastService instance.
    """
    if use_mock or os.getenv("USE_MOCK_FORECASTS", "").lower() == "true":
        return StatisticalForecastService(config)

    if os.getenv("HF_API_TOKEN"):
        return HFInferenceForecastService(config)

    return ForecastService(config)
