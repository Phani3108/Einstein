"""OpenAI embedding service implementation."""

import os
import time
from typing import List

import openai
from openai import AsyncOpenAI

from src.domain.exceptions import EmbeddingError
from src.domain.services.embedding_service import EmbeddingService
from src.infrastructure.logging import LoggerMixin, log_function_call, log_external_api_call
from src.infrastructure.retry import embedding_retry


class OpenAIEmbeddingService(EmbeddingService, LoggerMixin):
    """Implementation of EmbeddingService using OpenAI's embeddings API."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "text-embedding-ada-002",
        batch_size: int = 100,
    ):
        """Initialize the OpenAI embedding service.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: The embedding model to use
            batch_size: Maximum number of texts to embed in a single API call
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.batch_size = batch_size
        
        if self.api_key and self.api_key != "your-openai-api-key-here":
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.logger.warning("OpenAI API key not provided, running in mock mode")
            self.client = None
        
        self.logger.info(
            "OpenAI embedding service initialized",
            extra={
                "model": self.model,
                "batch_size": self.batch_size,
            }
        )

    @embedding_retry
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a vector embedding for the given text.

        Args:
            text: The text to generate an embedding for

        Returns:
            A vector embedding representing the text

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text.strip():
            raise EmbeddingError("Cannot generate embedding for empty text")

        args = {"text_length": len(text)}
        start_time = time.time()
        
        try:
            self.logger.debug(
                "Generating single embedding",
                extra={
                    "text_length": len(text),
                    "model": self.model,
                }
            )
            
            if not self.client:
                # Return a mock embedding for development
                import hashlib
                import struct
                hash_obj = hashlib.md5(text.encode())
                # Create a deterministic 1536-dimensional vector (OpenAI's embedding size)
                mock_embedding = []
                for i in range(1536):
                    # Use hash to create deterministic values
                    hash_bytes = hashlib.md5(f"{text}_{i}".encode()).digest()
                    value = struct.unpack('f', hash_bytes[:4])[0]
                    # Normalize to [-1, 1] range
                    mock_embedding.append(max(-1.0, min(1.0, value)))
                return mock_embedding
                
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            
            embedding = response.data[0].embedding
            duration = time.time() - start_time
            
            self.logger.info(
                "Single embedding generated successfully",
                extra={
                    "text_length": len(text),
                    "embedding_dimensions": len(embedding),
                    "duration_seconds": duration,
                }
            )
            
            log_external_api_call(
                service="openai",
                endpoint="/embeddings",
                method="POST",
                status_code=200,
                duration=duration,
            )
            log_function_call("generate_embedding", args, embedding)
            
            return embedding
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                "Single embedding generation failed",
                extra={
                    "text_length": len(text),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration,
                },
                exc_info=True,
            )
            
            log_external_api_call(
                service="openai",
                endpoint="/embeddings",
                method="POST",
                duration=duration,
                error=e,
            )
            log_function_call("generate_embedding", args, error=e)
            
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

    @embedding_retry
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for multiple texts.

        Args:
            texts: The texts to generate embeddings for

        Returns:
            A list of vector embeddings representing the texts

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [text for text in texts if text.strip()]
        if not valid_texts:
            raise EmbeddingError("Cannot generate embeddings for empty texts")

        args = {
            "text_count": len(valid_texts),
            "total_length": sum(len(text) for text in valid_texts),
        }
        start_time = time.time()
        
        try:
            self.logger.info(
                "Generating batch embeddings",
                extra={
                    "text_count": len(valid_texts),
                    "batch_size": self.batch_size,
                    "model": self.model,
                }
            )
            
            # Process in batches to avoid API limits
            results = []
            for i in range(0, len(valid_texts), self.batch_size):
                batch = valid_texts[i : i + self.batch_size]
                batch_start = time.time()
                
                if not self.client:
                    # Generate mock embeddings for development
                    import hashlib
                    import struct
                    batch_embeddings = []
                    for text in batch:
                        mock_embedding = []
                        for j in range(1536):
                            hash_bytes = hashlib.md5(f"{text}_{j}".encode()).digest()
                            value = struct.unpack('f', hash_bytes[:4])[0]
                            mock_embedding.append(max(-1.0, min(1.0, value)))
                        batch_embeddings.append(mock_embedding)
                    results.extend(batch_embeddings)
                else:
                    response = await self.client.embeddings.create(
                        model=self.model,
                        input=batch,
                    )
                    
                    # Sort by index to maintain original order
                    sorted_embeddings = sorted(response.data, key=lambda x: x.index)
                    batch_embeddings = [item.embedding for item in sorted_embeddings]
                    results.extend(batch_embeddings)
                
                batch_duration = time.time() - batch_start
                self.logger.debug(
                    "Batch embedding completed",
                    extra={
                        "batch_index": i // self.batch_size,
                        "batch_size": len(batch),
                        "duration_seconds": batch_duration,
                    }
                )
                
                log_external_api_call(
                    service="openai",
                    endpoint="/embeddings",
                    method="POST",
                    status_code=200,
                    duration=batch_duration,
                )
            
            duration = time.time() - start_time
            self.logger.info(
                "Batch embeddings generated successfully",
                extra={
                    "text_count": len(valid_texts),
                    "embedding_dimensions": len(results[0]) if results else 0,
                    "total_duration_seconds": duration,
                }
            )
            
            log_function_call("generate_embeddings", args, results)
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                "Batch embedding generation failed",
                extra={
                    "text_count": len(valid_texts),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration,
                },
                exc_info=True,
            )
            
            log_external_api_call(
                service="openai",
                endpoint="/embeddings",
                method="POST",
                duration=duration,
                error=e,
            )
            log_function_call("generate_embeddings", args, error=e)
            
            raise EmbeddingError(f"Failed to generate embeddings: {str(e)}")
