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
TIER1_INTERVAL = 60       # Every minute
TIER2_INTERVAL = 300      # Every 5 minutes
CONNECTION_INTERVAL = 300  # Every 5 minutes
INSIGHT_INTERVAL = 86400   # Daily


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
            logger.info("Worker started")

        @staticmethod
        async def on_shutdown(ctx):
            logger.info("Worker shutting down")

        functions = []  # Populated below
        cron_jobs = []

        # Import tasks
        from src.infrastructure.tasks.tier1_worker import tier1_task
        from src.infrastructure.tasks.tier2_worker import tier2_task
        from src.infrastructure.tasks.connection_worker import connection_task
        from src.infrastructure.tasks.insight_worker import insight_task

        functions = [tier1_task, tier2_task, connection_task, insight_task]

        cron_jobs = [
            cron(tier1_task, minute={0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59}),  # Every minute
            cron(tier2_task, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),  # Every 5 min
            cron(connection_task, minute={2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57}),  # Every 5 min, offset
            cron(insight_task, hour=7, minute=0),  # Daily at 7 AM
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

    database, embedding_service, llm_service = _create_services()
    ctx = {
        "database": database,
        "embedding_service": embedding_service,
        "llm_service": llm_service,
    }

    logger.info("Starting standalone worker loop")

    last_tier1 = datetime.min
    last_tier2 = datetime.min
    last_connection = datetime.min
    last_insight = datetime.min

    while True:
        now = datetime.now()

        try:
            # Tier 1: embeddings (every minute)
            if (now - last_tier1).total_seconds() >= TIER1_INTERVAL:
                result = await tier1_task(ctx)
                if result:
                    logger.info("Tier 1 processed %d events", result)
                last_tier1 = now

            # Tier 2: LLM enrichment (every 5 minutes)
            if (now - last_tier2).total_seconds() >= TIER2_INTERVAL:
                result = await tier2_task(ctx)
                if result:
                    logger.info("Tier 2 processed %d events", result)
                last_tier2 = now

            # Connection discovery (every 5 minutes)
            if (now - last_connection).total_seconds() >= CONNECTION_INTERVAL:
                result = await connection_task(ctx)
                if result:
                    logger.info("Connection discovery: %d new connections", result)
                last_connection = now

            # Insight generation (daily)
            if (now - last_insight).total_seconds() >= INSIGHT_INTERVAL:
                result = await insight_task(ctx)
                logger.info("Insight generation complete: %s", result)
                last_insight = now

        except Exception as e:
            logger.error("Worker loop error: %s", e, exc_info=True)

        await asyncio.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    asyncio.run(run_standalone())
