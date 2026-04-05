"""Timeline API routes for the Personal Semantic Engine."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.api.models.timeline_models import (
    RelatedEntriesResponse,
    TimelineRequest,
    TimelineResponse,
    TimelineSummaryResponse,
)
from src.api.models.thought_models import ErrorResponse
from src.application.usecases.get_timeline_usecase import GetTimelineUseCase
from src.domain.entities.enums import EntityType
from src.domain.entities.timeline import DateRange
from src.domain.entities.user import User
from src.domain.exceptions import TimelineError, TimelineQueryError
from src.infrastructure.middleware.authentication_middleware import (
    AuthenticationMiddleware,
)
from src.api.documentation import TIMELINE_EXAMPLES, COMMON_ERROR_EXAMPLES


def create_timeline_router(
    get_timeline_usecase: GetTimelineUseCase,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    """Create the timeline API router.

    Args:
        get_timeline_usecase: Use case for timeline operations
        auth_middleware: Authentication middleware

    Returns:
        Configured APIRouter for timeline operations
    """
    router = APIRouter(prefix="/api/v1/timeline", tags=["timeline"])

    async def get_current_user(request: Request) -> User:
        """Dependency to get the current authenticated user."""
        return await auth_middleware.require_authentication(request)

    @router.get(
        "",
        response_model=TimelineResponse,
        summary="Get chronological timeline",
        description="""
        Retrieve a chronological timeline of user's thoughts and activities with entity relationships.
        
        This endpoint provides a time-ordered view of personal data with intelligent grouping:
        
        **Timeline Features:**
        - **Chronological Ordering**: Thoughts sorted by timestamp (newest or oldest first)
        - **Entity Relationships**: Visual connections between related entities
        - **Smart Grouping**: Related entries grouped by time proximity and shared entities
        - **Multi-source Integration**: Combines thoughts with future external data sources
        - **Interactive Elements**: Entities are clickable for further exploration
        
        **Filtering Capabilities:**
        - **Date Range**: Filter by specific time periods
        - **Entity Types**: Show only entries with specific entity types
        - **Data Sources**: Filter by data source (thoughts, future integrations)
        - **Tags**: Filter by user-defined tags
        - **Custom Metadata**: Filter by custom fields
        
        **Grouping Logic:**
        - Entries within 1 hour with shared entities are grouped
        - Location-based grouping for co-located activities
        - Topic-based grouping using semantic similarity
        - User can enable/disable grouping via parameters
        
        **Performance:**
        - Lazy loading for large timelines
        - Efficient pagination with cursor-based navigation
        - Cached results for frequently accessed ranges
        """,
        responses={
            200: {
                "description": "Timeline retrieved successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "timeline": TIMELINE_EXAMPLES["timeline_response"]
                        }
                    }
                }
            },
            **COMMON_ERROR_EXAMPLES
        },
    )
    async def get_timeline(
        start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
        end_date: Optional[str] = Query(None, description="End date (ISO format)"),
        entity_types: List[EntityType] = Query([], description="Filter by entity types"),
        data_sources: List[str] = Query([], description="Filter by data sources"),
        tags: List[str] = Query([], description="Filter by tags"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
        sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
        include_groups: bool = Query(False, description="Include grouped entries"),
        include_summary: bool = Query(False, description="Include timeline summary"),
        current_user: User = Depends(get_current_user),
    ) -> TimelineResponse:
        """Get user's timeline with optional filtering and pagination.

        This endpoint returns a chronological view of the user's thoughts and
        extracted entities, with support for date range filtering, entity type
        filtering, and pagination.

        Args:
            start_date: Optional start date for filtering (ISO format)
            end_date: Optional end date for filtering (ISO format)
            entity_types: Optional list of entity types to filter by
            data_sources: Optional list of data sources to filter by
            tags: Optional list of tags to filter by
            page: Page number for pagination
            page_size: Number of items per page
            sort_order: Sort order ("asc" or "desc")
            include_groups: Whether to include grouped entries
            include_summary: Whether to include timeline summary
            current_user: The authenticated user

        Returns:
            Timeline response with entries and metadata

        Raises:
            HTTPException: If timeline retrieval fails
        """
        try:
            # Parse date range if provided
            date_range = None
            if start_date or end_date:
                from datetime import datetime
                
                parsed_start = None
                parsed_end = None
                
                if start_date:
                    try:
                        parsed_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid start_date format. Use ISO format."
                        )
                
                if end_date:
                    try:
                        parsed_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid end_date format. Use ISO format."
                        )
                
                date_range = DateRange(
                    start_date=parsed_start,
                    end_date=parsed_end
                )

            # Execute timeline retrieval
            timeline_response = await get_timeline_usecase.execute(
                user_id=current_user.id,
                date_range=date_range,
                entity_types=entity_types if entity_types else None,
                data_sources=data_sources if data_sources else None,
                tags=tags if tags else None,
                page=page,
                page_size=page_size,
                sort_order=sort_order,
            )

            return TimelineResponse.from_domain(timeline_response)

        except TimelineQueryError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Timeline query parsing failed: {str(e)}",
            )
        except TimelineError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Timeline retrieval failed: {str(e)}",
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
        "/summary",
        response_model=TimelineSummaryResponse,
        summary="Get timeline summary statistics",
        description="""
        Generate comprehensive summary statistics and insights about user's timeline data.
        
        This endpoint provides analytical insights into personal data patterns:
        
        **Summary Statistics:**
        - **Total Entries**: Count of all timeline entries
        - **Date Range**: Earliest and latest entry timestamps
        - **Entity Counts**: Breakdown by entity type (people, places, activities)
        - **Activity Patterns**: Most active time periods and days
        - **Top Entities**: Most frequently mentioned people, places, activities
        
        **Analytical Insights:**
        - **Temporal Patterns**: Peak activity hours and days
        - **Entity Relationships**: Most connected entities
        - **Content Trends**: Evolving topics and interests over time
        - **Mood Analysis**: Emotional patterns and trends
        - **Location Analysis**: Most visited places and travel patterns
        
        **Use Cases:**
        - Personal analytics dashboard
        - Data visualization preparation
        - Habit and pattern recognition
        - Goal tracking and progress monitoring
        - Life logging insights
        
        **Performance:**
        - Summary data is pre-computed and cached
        - Updates incrementally as new data is added
        - Fast response times for dashboard displays
        """,
        responses={
            200: {
                "description": "Timeline summary generated successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "summary": TIMELINE_EXAMPLES["timeline_summary_response"]
                        }
                    }
                }
            },
            **COMMON_ERROR_EXAMPLES
        },
    )
    async def get_timeline_summary(
        current_user: User = Depends(get_current_user),
    ) -> TimelineSummaryResponse:
        """Get timeline summary statistics for the user.

        This endpoint provides summary statistics about the user's timeline,
        including total entries, date range, entity counts, and activity patterns.

        Args:
            current_user: The authenticated user

        Returns:
            Timeline summary with statistics

        Raises:
            HTTPException: If summary generation fails
        """
        try:
            summary = await get_timeline_usecase.get_summary(current_user.id)
            return TimelineSummaryResponse.from_domain(summary)

        except TimelineError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Timeline summary generation failed: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    @router.get(
        "/entries/{entry_id}/related",
        response_model=RelatedEntriesResponse,
        summary="Get related timeline entries",
        description="""
        Find and return timeline entries that are related to a specific entry through various relationships.
        
        This endpoint discovers connections between timeline entries using multiple relationship types:
        
        **Relationship Types:**
        - **Entity Overlap**: Entries sharing common entities (people, places, activities)
        - **Temporal Proximity**: Entries close in time (within hours or days)
        - **Semantic Similarity**: Entries with similar content or themes
        - **Location Proximity**: Entries from nearby geographic locations
        - **Causal Relationships**: Entries that reference or follow up on others
        
        **Discovery Algorithm:**
        1. **Entity Analysis**: Find entries with shared entities
        2. **Temporal Analysis**: Identify time-clustered entries
        3. **Semantic Analysis**: Use embeddings to find similar content
        4. **Geographic Analysis**: Match location metadata
        5. **Reference Analysis**: Detect explicit references between entries
        6. **Scoring**: Rank relationships by strength and relevance
        
        **Relationship Scoring:**
        - Entity overlap: High weight for shared people/places
        - Temporal proximity: Decay function based on time distance
        - Semantic similarity: Vector cosine similarity
        - Location proximity: Geographic distance calculation
        - User interaction: Boost for frequently accessed relationships
        
        **Use Cases:**
        - Content exploration and discovery
        - Relationship visualization
        - Context understanding
        - Memory assistance and recall
        - Pattern recognition in personal data
        """,
        responses={
            200: {
                "description": "Related entries found successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "related_entries": {
                                "summary": "Related timeline entries",
                                "value": {
                                    "entry_id": "770e8400-e29b-41d4-a716-446655440000",
                                    "related_entries": [
                                        {
                                            "id": "770e8400-e29b-41d4-a716-446655440001",
                                            "thought": {
                                                "id": "550e8400-e29b-41d4-a716-446655440001",
                                                "content": "Follow-up meeting with Sarah scheduled for next week to finalize the project details.",
                                                "timestamp": "2024-01-16T09:00:00Z",
                                                "metadata": {
                                                    "tags": ["work", "follow-up"],
                                                    "mood": "focused"
                                                },
                                                "semantic_entries": [],
                                                "created_at": "2024-01-16T09:00:00Z",
                                                "updated_at": "2024-01-16T09:00:00Z"
                                            },
                                            "timestamp": "2024-01-16T09:00:00Z",
                                            "entities": [],
                                            "connections": [],
                                            "grouped_with": [],
                                            "data_source": "thought"
                                        }
                                    ],
                                    "total_count": 1
                                }
                            }
                        }
                    }
                }
            },
            **COMMON_ERROR_EXAMPLES
        },
    )
    async def get_related_entries(
        entry_id: str,
        limit: int = Query(10, ge=1, le=50, description="Maximum number of related entries"),
        current_user: User = Depends(get_current_user),
    ) -> RelatedEntriesResponse:
        """Get entries related to a specific timeline entry.

        This endpoint finds and returns timeline entries that are related to
        the specified entry based on shared entities, temporal proximity,
        and semantic similarity.

        Args:
            entry_id: ID of the entry to find relations for
            limit: Maximum number of related entries to return
            current_user: The authenticated user

        Returns:
            Related entries response

        Raises:
            HTTPException: If related entries retrieval fails
        """
        try:
            related_entries = await get_timeline_usecase.get_related_entries(
                entry_id=entry_id,
                user_id=current_user.id,
                limit=limit,
            )

            from src.api.models.timeline_models import TimelineEntryResponse
            
            return RelatedEntriesResponse(
                entry_id=entry_id,
                related_entries=[
                    TimelineEntryResponse.from_domain(entry)
                    for entry in related_entries
                ],
                total_count=len(related_entries),
            )

        except TimelineQueryError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except TimelineError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Related entries retrieval failed: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    return router