"""
Embedding adapter — abstracts over multiple embedding providers.
Supports OpenAI (cloud) and Ollama (local) embeddings.
"""

import os
import logging
import hashlib
import struct
from typing import Optional

LOG = logging.getLogger("einstein-sidecar")

LLM_PROVIDER = os.environ.get("EINSTEIN_LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EINSTEIN_EMBEDDING_MODEL", "text-embedding-3-small")
OLLAMA_EMBED_MODEL = os.environ.get("EINSTEIN_OLLAMA_EMBED_MODEL", "nomic-embed-text")


def _deterministic_embedding(text: str, dim: int = 384) -> list[float]:
    """Generate a deterministic mock embedding from text hash (for offline fallback)."""
    h = hashlib.sha256(text.encode()).digest()
    # Expand hash to fill dimension
    repeated = h * ((dim * 4 // len(h)) + 1)
    values = struct.unpack(f"{dim}f", repeated[: dim * 4])
    # Normalize
    norm = max(sum(v * v for v in values) ** 0.5, 1e-10)
    return [v / norm for v in values]


async def get_embedding(text: str) -> list[float]:
    """Get embedding for a single text using the configured provider."""
    embeddings = await get_embeddings([text])
    return embeddings[0]


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts using the configured provider."""
    if not texts:
        return []

    if LLM_PROVIDER == "ollama":
        return await _ollama_embeddings(texts)
    else:
        return await _openai_embeddings(texts)


async def _openai_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using OpenAI API."""
    try:
        from openai import AsyncOpenAI

        if not OPENAI_API_KEY:
            LOG.warning("No OpenAI API key, using mock embeddings")
            return [_deterministic_embedding(t) for t in texts]

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        # Process in batches of 100
        all_embeddings = []
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            response = await client.embeddings.create(
                model=EMBEDDING_MODEL, input=batch
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings
    except ImportError:
        LOG.warning("openai not installed, using mock embeddings")
        return [_deterministic_embedding(t) for t in texts]
    except Exception as e:
        LOG.error(f"OpenAI embedding error: {e}")
        return [_deterministic_embedding(t) for t in texts]


async def _ollama_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using Ollama local model."""
    try:
        import httpx

        embeddings = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/embeddings",
                    json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
                )
                if response.status_code == 200:
                    data = response.json()
                    embeddings.append(data.get("embedding", _deterministic_embedding(text)))
                else:
                    LOG.warning(f"Ollama embedding failed ({response.status_code}), using mock")
                    embeddings.append(_deterministic_embedding(text))
        return embeddings
    except ImportError:
        LOG.warning("httpx not installed, using mock embeddings")
        return [_deterministic_embedding(t) for t in texts]
    except Exception as e:
        LOG.error(f"Ollama embedding error: {e}")
        return [_deterministic_embedding(t) for t in texts]


def get_embedding_dimension() -> int:
    """Return the expected embedding dimension for the current provider."""
    if LLM_PROVIDER == "ollama":
        return 768  # nomic-embed-text
    else:
        return 1536  # text-embedding-3-small


def get_provider_info() -> dict:
    """Return info about the current embedding provider."""
    return {
        "provider": LLM_PROVIDER,
        "model": OLLAMA_EMBED_MODEL if LLM_PROVIDER == "ollama" else EMBEDDING_MODEL,
        "dimension": get_embedding_dimension(),
    }
