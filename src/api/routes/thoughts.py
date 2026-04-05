"""Thought management API routes."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.api.models.thought_models import (
    CreateThoughtRequest,
    ErrorResponse,
    ThoughtListResponse,
    ThoughtResponse,
    UpdateThoughtRequest,
)
from src.application.usecases.create_thought_usecase import CreateThoughtUseCase
from src.application.usecases.delete_thought_usecase import DeleteThoughtUseCase
from src.application.usecases.get_thought_by_id_usecase import GetThoughtByIdUseCase
from src.application.usecases.get_thoughts_usecase import GetThoughtsUseCase
from src.application.usecases.update_thought_usecase import UpdateThoughtUseCase
from src.domain.entities.user import User
from src.domain.exceptions import EntityExtractionError, ThoughtNotFoundError
from src.infrastructure.middleware.authentication_middleware import (
    AuthenticationMiddleware,
)
from src.api.documentation import THOUGHTS_EXAMPLES, COMMON_ERROR_EXAMPLES


def create_thoughts_router(
    create_thought_usecase: CreateThoughtUseCase,
    get_thoughts_usecase: GetThoughtsUseCase,
    get_thought_by_id_usecase: GetThoughtByIdUseCase,
    update_thought_usecase: UpdateThoughtUseCase,
    delete_thought_usecase: DeleteThoughtUseCase,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    """Create the thoughts API router.

    Args:
        create_thought_usecase: Use case for creating thoughts
        get_thoughts_usecase: Use case for getting thoughts
        get_thought_by_id_usecase: Use case for getting thought by ID
        update_thought_usecase: Use case for updating thoughts
        delete_thought_usecase: Use case for deleting thoughts
        auth_middleware: Authentication middleware

    Returns:
        Configured APIRouter for thoughts
    """
    router = APIRouter(prefix="/api/v1/thoughts", tags=["thoughts"])

    async def get_current_user(request: Request) -> User:
        """Dependency to get the current authenticated user."""
        return await auth_middleware.require_authentication(request)

    @router.post(
        "",
        response_model=ThoughtResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new thought",
        description="""
        Create a new thought entry with automatic entity extraction and metadata capture.
        
        This endpoint processes plain English text to extract semantic entities such as:
        - **People**: Names and references to individuals
        - **Locations**: Places, addresses, and geographic references  
        - **Activities**: Actions, events, and behaviors
        - **Emotions**: Feelings and emotional states
        - **Dates**: Temporal references and time expressions
        - **Organizations**: Companies, institutions, and groups
        
        The system also captures optional metadata including location coordinates,
        weather conditions, mood, tags, and custom fields for enhanced context.
        
        **Processing Pipeline:**
        1. Content validation and sanitization
        2. LLM-based entity extraction with confidence scoring
        3. Metadata enrichment and validation
        4. Vector embedding generation for semantic search
        5. Storage in both relational and vector databases
        """,
        responses={
            201: {
                "description": "Thought created successfully with extracted entities",
                "content": {
                    "application/json": {
                        "examples": {
                            "successful_creation": THOUGHTS_EXAMPLES["create_thought_response"]
                        }
                    }
                }
            },
            **COMMON_ERROR_EXAMPLES
        },
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {
                            "with_metadata": THOUGHTS_EXAMPLES["create_thought_request"],
                            "simple_thought": {
                                "summary": "Simple thought without metadata",
                                "value": {
                                    "content": "Just finished reading a great book about artificial intelligence."
                                }
                            }
                        }
                    }
                }
            }
        }
    )
    async def create_thought(
        request: CreateThoughtRequest,
        current_user: User = Depends(get_current_user),
    ) -> ThoughtResponse:
        """Create a new thought with metadata capture.

        Args:
            request: The thought creation request
            current_user: The authenticated user

        Returns:
            The created thought with extracted semantic entries

        Raises:
            HTTPException: If creation fails
        """
        try:
            metadata = request.metadata.to_domain() if request.metadata else None
            
            thought = await create_thought_usecase.execute(
                user_id=current_user.id,
                content=request.content,
                metadata=metadata,
                timestamp=request.timestamp,
            )
            
            return ThoughtResponse.from_domain(thought)
            
        except EntityExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Entity extraction failed: {str(e)}",
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    @router.get(
        "",
        response_model=ThoughtListResponse,
        summary="Get user's thoughts",
        description="""
        Retrieve a paginated list of the authenticated user's thoughts with their semantic entries.
        
        This endpoint returns thoughts in reverse chronological order (newest first) by default.
        Each thought includes:
        - Original content and timestamp
        - Extracted semantic entities with confidence scores
        - Metadata (location, weather, mood, tags, custom fields)
        - Creation and modification timestamps
        
        **Pagination:**
        - Use `skip` parameter to offset results for pagination
        - Use `limit` parameter to control page size (max 100)
        - Response includes total count for pagination calculations
        
        **Performance Notes:**
        - Results are cached for frequently accessed pages
        - Large result sets are automatically paginated
        - Consider using search endpoints for filtered queries
        """,
        responses={
            200: {
                "description": "Thoughts retrieved successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "thoughts_list": THOUGHTS_EXAMPLES["thoughts_list_response"]
                        }
                    }
                }
            },
            **COMMON_ERROR_EXAMPLES
        },
    )
    async def get_thoughts(
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_user),
    ) -> ThoughtListResponse:
        """Get user's thoughts with pagination.

        Args:
            skip: Number of thoughts to skip for pagination
            limit: Maximum number of thoughts to return
            current_user: The authenticated user

        Returns:
            Paginated list of user's thoughts

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            thoughts = await get_thoughts_usecase.execute(
                user_id=current_user.id,
                skip=skip,
                limit=limit,
            )
            
            # For now, we'll use the length of returned thoughts as total
            # In a real implementation, you'd want a separate count query
            total = len(thoughts)
            
            return ThoughtListResponse.from_domain_list(
                thoughts=thoughts,
                total=total,
                skip=skip,
                limit=limit,
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    @router.get(
        "/{thought_id}",
        response_model=ThoughtResponse,
        summary="Get a specific thought",
        description="""
        Retrieve a specific thought by its unique identifier with complete entity details.
        
        This endpoint returns the full thought record including:
        - Complete content and metadata
        - All extracted semantic entities with context
        - Confidence scores for each entity
        - Relationship information between entities
        - Complete audit trail (created/updated timestamps)
        
        **Access Control:**
        - Users can only access their own thoughts
        - Admin users can access any thought
        - Returns 403 Forbidden for unauthorized access attempts
        
        **Use Cases:**
        - Detailed thought inspection and analysis
        - Entity relationship exploration
        - Content editing preparation
        - Audit and debugging purposes
        """,
        responses={
            200: {
                "description": "Thought retrieved successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "thought_detail": THOUGHTS_EXAMPLES["create_thought_response"]
                        }
                    }
                }
            },
            **COMMON_ERROR_EXAMPLES
        },
    )
    async def get_thought(
        thought_id: UUID,
        current_user: User = Depends(get_current_user),
    ) -> ThoughtResponse:
        """Get a specific thought by ID with entity details.

        Args:
            thought_id: The ID of the thought to retrieve
            current_user: The authenticated user

        Returns:
            The requested thought with semantic entries

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            thought = await get_thought_by_id_usecase.execute(
                thought_id=thought_id,
                user_id=current_user.id,
            )
            
            return ThoughtResponse.from_domain(thought)
            
        except ThoughtNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thought not found",
            )
        except ValueError as e:
            if "permission" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    @router.put(
        "/{thought_id}",
        response_model=ThoughtResponse,
        summary="Update a thought",
        description="""
        Update an existing thought with automatic re-processing of entities and metadata.
        
        When a thought is updated, the system performs complete re-analysis:
        - **Content Re-processing**: New entity extraction if content changed
        - **Metadata Updates**: Merge new metadata with existing data
        - **Vector Re-indexing**: Update semantic search embeddings
        - **Relationship Updates**: Recalculate entity relationships
        - **Audit Trail**: Maintain complete change history
        
        **Update Behavior:**
        - Partial updates supported (only provide fields to change)
        - Null values remove existing data
        - Entity extraction runs on content changes
        - Metadata is merged, not replaced entirely
        - Original timestamp preserved, updated_at modified
        
        **Performance Impact:**
        - Content changes trigger LLM processing (2-5 seconds)
        - Metadata-only updates are near-instantaneous
        - Vector re-indexing happens asynchronously
        """,
        responses={
            200: {
                "description": "Thought updated successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "updated_thought": THOUGHTS_EXAMPLES["create_thought_response"]
                        }
                    }
                }
            },
            **COMMON_ERROR_EXAMPLES
        },
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {
                            "content_update": {
                                "summary": "Update thought content",
                                "value": {
                                    "content": "Had an amazing meeting with Sarah at the new coffee shop downtown. We discussed the project proposal in detail and I'm very excited about our collaboration."
                                }
                            },
                            "metadata_update": {
                                "summary": "Update only metadata",
                                "value": {
                                    "metadata": {
                                        "mood": "excited",
                                        "tags": ["work", "meeting", "collaboration", "project"],
                                        "custom": {
                                            "follow_up": "scheduled",
                                            "priority": "high"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    )
    async def update_thought(
        thought_id: UUID,
        request: UpdateThoughtRequest,
        current_user: User = Depends(get_current_user),
    ) -> ThoughtResponse:
        """Update a thought with re-processing of entities.

        Args:
            thought_id: The ID of the thought to update
            request: The thought update request
            current_user: The authenticated user

        Returns:
            The updated thought with re-processed semantic entries

        Raises:
            HTTPException: If update fails
        """
        try:
            metadata = request.metadata.to_domain() if request.metadata else None
            
            thought = await update_thought_usecase.execute(
                thought_id=thought_id,
                user_id=current_user.id,
                content=request.content,
                metadata=metadata,
            )
            
            return ThoughtResponse.from_domain(thought)
            
        except ThoughtNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thought not found",
            )
        except EntityExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Entity extraction failed: {str(e)}",
            )
        except ValueError as e:
            if "permission" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    @router.delete(
        "/{thought_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Delete a thought",
        description="""
        Permanently delete a thought and all its associated data.
        
        This operation performs complete cleanup:
        - **Thought Record**: Remove from primary database
        - **Semantic Entities**: Delete all extracted entities
        - **Vector Embeddings**: Remove from semantic search index
        - **Relationships**: Clean up entity relationship mappings
        - **Timeline Entries**: Remove from chronological views
        - **Search Index**: Update full-text search indices
        
        **Important Notes:**
        - This operation is **irreversible**
        - All associated data is permanently deleted
        - Search results will no longer include this thought
        - Timeline views will be updated automatically
        - Related entity counts will be recalculated
        
        **Access Control:**
        - Users can only delete their own thoughts
        - Admin users can delete any thought
        - Returns 403 Forbidden for unauthorized attempts
        
        **Performance:**
        - Deletion is processed asynchronously
        - Search indices updated in background
        - Returns immediately after database deletion
        """,
        responses={
            204: {
                "description": "Thought deleted successfully"
            },
            **COMMON_ERROR_EXAMPLES
        },
    )
    async def delete_thought(
        thought_id: UUID,
        current_user: User = Depends(get_current_user),
    ) -> None:
        """Delete a thought and its related entities.

        Args:
            thought_id: The ID of the thought to delete
            current_user: The authenticated user

        Raises:
            HTTPException: If deletion fails
        """
        try:
            await delete_thought_usecase.execute(
                thought_id=thought_id,
                user_id=current_user.id,
            )
            
        except ThoughtNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thought not found",
            )
        except ValueError as e:
            if "permission" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    return router