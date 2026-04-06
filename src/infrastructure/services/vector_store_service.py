"""Pinecone vector store service implementation."""

import os
import time
from typing import Dict, List, Optional
from uuid import UUID

from pinecone import Pinecone

from src.domain.entities.enums import EntityType
from src.domain.exceptions import VectorStoreError
from src.domain.services.vector_store_service import (
    VectorSearchResult as BaseVectorSearchResult,
)
from src.domain.services.vector_store_service import VectorStoreService
from src.infrastructure.logging import LoggerMixin, log_function_call, log_external_api_call
from src.infrastructure.retry import vector_store_retry


class VectorSearchResult(BaseVectorSearchResult):
    """Result of a vector search operation."""

    def __init__(self, id: str, score: float, metadata: Dict[str, str]):
        """Initialize a vector search result.

        Args:
            id: The unique identifier of the vector
            score: The similarity score (0-1)
            metadata: Additional metadata associated with the vector
        """
        self.id = id
        self.score = score
        self.metadata = metadata


class PineconeVectorStore(VectorStoreService, LoggerMixin):
    """Implementation of VectorStoreService using Pinecone."""

    def __init__(
        self,
        api_key: str = None,
        host: str = None,
        environment: str = None,  # Keep for backward compatibility
        index_name: str = "einstein",
        namespace: str = "default",
        dimension: int = 1536,  # Default for text-embedding-ada-002
    ):
        """Initialize the Pinecone vector store.

        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            host: Pinecone host URL for serverless (defaults to PINECONE_HOST env var)
            environment: Pinecone environment (legacy, for backward compatibility)
            index_name: Name of the Pinecone index
            namespace: Default namespace for vectors
            dimension: Dimension of the vectors (1536 for OpenAI ada-002)
        """
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            self.logger.warning("Pinecone API key not set — vector store disabled. Semantic search will be unavailable.")
            self.index = None
            self.host = None
            self.environment = None
            self.index_name = index_name
            self.namespace = namespace
            self.dimension = dimension
            return

        self.host = host or os.getenv("PINECONE_HOST")
        self.environment = environment or os.getenv("PINECONE_ENVIRONMENT")  # Keep for backward compatibility
        self.index_name = index_name
        self.namespace = namespace
        self.dimension = dimension

        # Initialize Pinecone only if credentials are provided
        if self.api_key and self.api_key != "your-pinecone-api-key-here":
            try:
                # Modern Pinecone client (v3+) - use index name directly
                pc = Pinecone(api_key=self.api_key)
                self.index = pc.Index(self.index_name)
                
                self.logger.info(
                    "Pinecone vector store initialized successfully",
                    extra={
                        "index_name": self.index_name,
                        "host": self.host,
                        "namespace": self.namespace,
                        "dimension": self.dimension,
                    }
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize Pinecone: {e}")
                self.index = None
        else:
            self.logger.warning(
                "Pinecone credentials not provided, running in mock mode",
                extra={
                    "api_key_provided": bool(self.api_key and self.api_key != "your-pinecone-api-key-here"),
                }
            )
            self.index = None
        
        self.logger.info(
            "Pinecone vector store initialized",
            extra={
                "index_name": self.index_name,
                "namespace": self.namespace,
                "dimension": self.dimension,
                "environment": self.environment,
            }
        )



    @vector_store_retry
    async def store_vector(
        self, id: str, vector: List[float], metadata: Dict[str, str]
    ) -> None:
        """Store a vector in the vector database.

        Args:
            id: Unique identifier for the vector
            vector: The vector to store
            metadata: Additional metadata to store with the vector

        Raises:
            VectorStoreError: If storage fails
        """
        if self.index is None:
            return
        args = {
            "vector_id": id,
            "vector_dimension": len(vector),
            "metadata_keys": list(metadata.keys()),
        }
        start_time = time.time()
        
        try:
            self.logger.debug(
                "Storing vector",
                extra={
                    "vector_id": id,
                    "vector_dimension": len(vector),
                    "metadata": metadata,
                    "namespace": self.namespace,
                }
            )
            
            if self.index:
                self.index.upsert(
                    vectors=[{"id": id, "values": vector, "metadata": metadata}],
                    namespace=self.namespace,
                )
            else:
                self.logger.warning("Vector store not initialized, skipping storage")
            
            duration = time.time() - start_time
            self.logger.info(
                "Vector stored successfully",
                extra={
                    "vector_id": id,
                    "duration_seconds": duration,
                }
            )
            
            log_external_api_call(
                service="pinecone",
                endpoint="/vectors/upsert",
                method="POST",
                status_code=200,
                duration=duration,
            )
            log_function_call("store_vector", args)
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                "Vector storage failed",
                extra={
                    "vector_id": id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration,
                },
                exc_info=True,
            )
            
            log_external_api_call(
                service="pinecone",
                endpoint="/vectors/upsert",
                method="POST",
                duration=duration,
                error=e,
            )
            log_function_call("store_vector", args, error=e)
            
            raise VectorStoreError(f"Failed to store vector: {str(e)}")

    @vector_store_retry
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        entity_type: Optional[EntityType] = None,
        user_id: Optional[UUID] = None,
    ) -> List[VectorSearchResult]:
        """Search for similar vectors.

        Args:
            query_vector: The vector to search for
            top_k: Maximum number of results to return
            entity_type: Optional filter by entity type
            user_id: Optional filter by user ID

        Returns:
            A list of search results ordered by similarity

        Raises:
            VectorStoreError: If search fails
        """
        if self.index is None:
            return []
        args = {
            "query_dimension": len(query_vector),
            "top_k": top_k,
            "entity_type": entity_type.value if entity_type else None,
            "user_id": str(user_id) if user_id else None,
        }
        start_time = time.time()
        
        try:
            # Build filter if needed
            filter_dict = {}
            if entity_type:
                filter_dict["entity_type"] = entity_type.value
            if user_id:
                filter_dict["user_id"] = str(user_id)

            self.logger.debug(
                "Searching vectors",
                extra={
                    "top_k": top_k,
                    "filter": filter_dict,
                    "namespace": self.namespace,
                }
            )

            # Execute search
            if not self.index:
                self.logger.warning("Vector store not initialized, returning empty results")
                return []
                
            response = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=self.namespace,
                filter=filter_dict if filter_dict else None,
                include_metadata=True,
            )

            # Convert to domain objects
            results = []
            for match in response.matches:
                result = VectorSearchResult(
                    id=match.id, score=match.score, metadata=match.metadata
                )
                results.append(result)

            duration = time.time() - start_time
            self.logger.info(
                "Vector search completed",
                extra={
                    "results_count": len(results),
                    "top_score": results[0].score if results else 0,
                    "duration_seconds": duration,
                }
            )
            
            log_external_api_call(
                service="pinecone",
                endpoint="/query",
                method="POST",
                status_code=200,
                duration=duration,
            )
            log_function_call("search", args, results)

            return results
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                "Vector search failed",
                extra={
                    "top_k": top_k,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration,
                },
                exc_info=True,
            )
            
            log_external_api_call(
                service="pinecone",
                endpoint="/query",
                method="POST",
                duration=duration,
                error=e,
            )
            log_function_call("search", args, error=e)
            
            raise VectorStoreError(f"Failed to search vectors: {str(e)}")

    async def delete_vectors(self, ids: List[str]) -> None:
        """Delete vectors from the vector database.

        Args:
            ids: List of vector IDs to delete

        Raises:
            VectorStoreError: If deletion fails
        """
        if self.index is None:
            return
        try:
            self.index.delete(ids=ids, namespace=self.namespace)
        except Exception as e:
            raise VectorStoreError(f"Failed to delete vectors: {str(e)}")
