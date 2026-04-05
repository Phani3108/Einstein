"""Main entry point for the Personal Semantic Engine."""

import logging
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from src.api.app import app
from src.container import container


def configure_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def load_config() -> None:
    """Load configuration from environment variables."""
    # Load .env file if it exists
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)

    # Configure container
    container.config.from_dict(
        {
            "db": {
                "connection_string": os.getenv(
                    "DATABASE_URL",
                    "postgresql+asyncpg://postgres:postgres@localhost:5432/einstein",
                ),
            },
            "api": {
                "host": os.getenv("API_HOST", "0.0.0.0"),
                "port": int(os.getenv("API_PORT", "8000")),
            },
            "security": {
                "secret_key": os.getenv("SECRET_KEY", "insecure-secret-key"),
                "algorithm": os.getenv("ALGORITHM", "HS256"),
                "access_token_expire_minutes": int(
                    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
                ),
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
            },
            "pinecone": {
                "api_key": os.getenv("PINECONE_API_KEY", ""),
                "environment": os.getenv("PINECONE_ENVIRONMENT", ""),
                "index_name": os.getenv("PINECONE_INDEX", "einstein"),
            },
        }
    )


def main() -> None:
    """Run the application."""
    configure_logging()
    load_config()

    host = container.config.api.host()
    port = container.config.api.port()

    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
