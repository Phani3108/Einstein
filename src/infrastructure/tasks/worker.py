"""arq worker configuration and entry point.

Usage:
  arq src.infrastructure.tasks.worker.WorkerSettings

Or run standalone without arq/Redis:
  python -m src.infrastructure.tasks.worker

The standalone mode runs all tasks in a loop with configurable intervals,
suitable for development or single-user deployment.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

from src.infrastructure.database.connection import Database
from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
from src.infrastructure.llm.llm_service import LLMService
from src.infrastructure.llm.config import LLMConfigLoader

logger = logging.getLogger(__name__)

# Task intervals (seconds)
TIER1_INTERVAL = 60            # Every minute
TIER2_INTERVAL = 300           # Every 5 minutes
CONNECTION_INTERVAL = 300      # Every 5 minutes
INSIGHT_INTERVAL = 86400       # Daily
PREDICTION_INTERVAL = 21600    # 6 hours
NUDGE_INTERVAL = 7200          # 2 hours
FOLLOWUP_INTERVAL = 1800       # 30 minutes
BRIEFING_INTERVAL = 3600       # 1 hour
PATTERN_INTERVAL = 604800      # Weekly


def _create_services():
    """Create shared service instances for workers."""
    database = Database(
        connection_string=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://nyn@localhost:5432/einstein",
        )
    )
    embedding_service = OpenAIEmbeddingService(
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    config_loader = LLMConfigLoader()
    llm_service = LLMService(
        model=os.getenv("LLM_MODEL"),
        config_loader=config_loader,
    )
    return database, embedding_service, llm_service


# --- arq integration (optional) ---

async def _prediction_task_wrapper(ctx):
    """Wrap run_prediction_job to accept ctx dict like other tasks."""
    from src.infrastructure.tasks.prediction_worker import run_prediction_job
    return await run_prediction_job(
        database=ctx["database"],
        redis_client=ctx.get("redis"),
    )


try:
    from arq import cron

    class WorkerSettings:
        """arq worker settings. Used when running: arq src.infrastructure.tasks.worker.WorkerSettings"""

        redis_settings = None  # Will be set from env

        @staticmethod
        async def on_startup(ctx):
            database, embedding_service, llm_service = _create_services()
            ctx["database"] = database
            ctx["embedding_service"] = embedding_service
            ctx["llm_service"] = llm_service
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    import redis.asyncio as aioredis
                    ctx["redis"] = aioredis.from_url(redis_url)
                except Exception as e:
                    logger.warning("Redis not available for workers: %s", e)
            logger.info("Worker started")

        @staticmethod
        async def on_shutdown(ctx):
            logger.info("Worker shutting down")

        from src.infrastructure.tasks.tier1_worker import tier1_task
        from src.infrastructure.tasks.tier2_worker import tier2_task
        from src.infrastructure.tasks.connection_worker import connection_task
        from src.infrastructure.tasks.insight_worker import insight_task
        from src.infrastructure.tasks.nudge_worker import nudge_task
        from src.infrastructure.tasks.followup_detector import followup_detection_task
        from src.infrastructure.tasks.briefing_worker import briefing_task
        from src.infrastructure.tasks.pattern_report_worker import pattern_report_task

        functions = [
            tier1_task, tier2_task, connection_task, insight_task,
            _prediction_task_wrapper,
            nudge_task, followup_detection_task, briefing_task, pattern_report_task,
        ]

        cron_jobs = [
            cron(tier1_task, minute=set(range(60))),
            cron(tier2_task, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
            cron(connection_task, minute={2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57}),
            cron(insight_task, hour=7, minute=0),
            cron(_prediction_task_wrapper, hour={0, 6, 12, 18}, minute=30),
            cron(nudge_task, minute={0, 30}),
            cron(followup_detection_task, minute={15, 45}),
            cron(briefing_task, minute=5),
            cron(pattern_report_task, weekday=6, hour=0, minute=0),
        ]

except ImportError:
    logger.info("arq not installed — standalone worker mode only")
    WorkerSettings = None


# --- Standalone mode (no Redis required) ---

async def run_standalone():
    """Run all workers in a single async loop without arq/Redis.

    Suitable for development and single-user deployment.
    """
    from src.infrastructure.tasks.tier1_worker import tier1_task
    from src.infrastructure.tasks.tier2_worker import tier2_task
    from src.infrastructure.tasks.connection_worker import connection_task
    from src.infrastructure.tasks.insight_worker import insight_task
    from src.infrastructure.tasks.nudge_worker import nudge_task
    from src.infrastructure.tasks.followup_detector import followup_detection_task
    from src.infrastructure.tasks.briefing_worker import briefing_task
    from src.infrastructure.tasks.pattern_report_worker import pattern_report_task

    database, embedding_service, llm_service = _create_services()

    redis_client = None
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(redis_url)
        except Exception as e:
            logger.warning("Redis not available: %s", e)

    ctx = {
        "database": database,
        "embedding_service": embedding_service,
        "llm_service": llm_service,
        "redis": redis_client,
    }

    logger.info("Starting standalone worker loop")

    last_tier1 = datetime.min
    last_tier2 = datetime.min
    last_connection = datetime.min
    last_insight = datetime.min
    last_prediction = datetime.min
    last_nudge = datetime.min
    last_followup = datetime.min
    last_briefing = datetime.min
    last_pattern = datetime.min

    while True:
        now = datetime.now()

        try:
            if (now - last_tier1).total_seconds() >= TIER1_INTERVAL:
                result = await tier1_task(ctx)
                if result:
                    logger.info("Tier 1 processed %d events", result)
                last_tier1 = now

            if (now - last_tier2).total_seconds() >= TIER2_INTERVAL:
                result = await tier2_task(ctx)
                if result:
                    logger.info("Tier 2 processed %d events", result)
                last_tier2 = now

            if (now - last_connection).total_seconds() >= CONNECTION_INTERVAL:
                result = await connection_task(ctx)
                if result:
                    logger.info("Connection discovery: %d new connections", result)
                last_connection = now

            if (now - last_insight).total_seconds() >= INSIGHT_INTERVAL:
                result = await insight_task(ctx)
                logger.info("Insight generation complete: %s", result)
                last_insight = now

            if (now - last_prediction).total_seconds() >= PREDICTION_INTERVAL:
                try:
                    from src.infrastructure.tasks.prediction_worker import run_prediction_job
                    result = await run_prediction_job(database, redis_client)
                    logger.info("Prediction job complete: %s", result)
                except Exception as e:
                    logger.warning("Prediction job skipped: %s", e)
                last_prediction = now

            if (now - last_nudge).total_seconds() >= NUDGE_INTERVAL:
                result = await nudge_task(ctx)
                logger.info("Nudge task: %d nudges generated", len(result) if result else 0)
                last_nudge = now

            if (now - last_followup).total_seconds() >= FOLLOWUP_INTERVAL:
                result = await followup_detection_task(ctx)
                logger.info("Follow-up detection: %d follow-ups", len(result) if result else 0)
                last_followup = now

            if (now - last_briefing).total_seconds() >= BRIEFING_INTERVAL:
                result = await briefing_task(ctx)
                logger.info("Briefing task: %d briefings", len(result) if result else 0)
                last_briefing = now

            if (now - last_pattern).total_seconds() >= PATTERN_INTERVAL:
                result = await pattern_report_task(ctx)
                logger.info("Pattern report: %s", result)
                last_pattern = now

        except Exception as e:
            logger.error("Worker loop error: %s", e, exc_info=True)

        await asyncio.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    asyncio.run(run_standalone())
