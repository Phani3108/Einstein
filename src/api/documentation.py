"""API documentation examples and schemas for OpenAPI specification."""

from typing import Any, Dict

# Common response examples
COMMON_ERROR_EXAMPLES = {
    "400": {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "error": "Invalid input",
                    "detail": "The provided data is invalid or malformed",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    },
    "401": {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {
                    "error": "Authentication required",
                    "detail": "Valid JWT token required in Authorization header",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    },
    "403": {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "example": {
                    "error": "Access denied",
                    "detail": "Insufficient permissions to access this resource",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    },
    "404": {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {
                    "error": "Resource not found",
                    "detail": "The requested resource does not exist",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    },
    "422": {
        "description": "Unprocessable Entity",
        "content": {
            "application/json": {
                "example": {
                    "error": "Processing failed",
                    "detail": "The request was valid but could not be processed",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    },
    "429": {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {
                    "error": "Rate limit exceeded",
                    "detail": "Too many requests. Please try again later",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    },
    "500": {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    }
}

# Thoughts API examples
THOUGHTS_EXAMPLES = {
    "create_thought_request": {
        "summary": "Create a thought with metadata",
        "value": {
            "content": "Had a great meeting with Sarah at the coffee shop downtown. We discussed the new project proposal and I'm feeling optimistic about the collaboration.",
            "metadata": {
                "location": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "name": "Downtown Coffee Shop"
                },
                "weather": {
                    "temperature": 22.5,
                    "condition": "sunny",
                    "humidity": 65.0
                },
                "mood": "optimistic",
                "tags": ["work", "meeting", "collaboration"],
                "custom": {
                    "project": "new-proposal",
                    "priority": "high"
                }
            },
            "timestamp": "2024-01-15T14:30:00Z"
        }
    },
    "create_thought_response": {
        "summary": "Created thought with extracted entities",
        "value": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Had a great meeting with Sarah at the coffee shop downtown. We discussed the new project proposal and I'm feeling optimistic about the collaboration.",
            "timestamp": "2024-01-15T14:30:00Z",
            "metadata": {
                "location": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "name": "Downtown Coffee Shop"
                },
                "weather": {
                    "temperature": 22.5,
                    "condition": "sunny",
                    "humidity": 65.0
                },
                "mood": "optimistic",
                "tags": ["work", "meeting", "collaboration"],
                "custom": {
                    "project": "new-proposal",
                    "priority": "high"
                }
            },
            "semantic_entries": [
                {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "entity_type": "person",
                    "entity_value": "Sarah",
                    "confidence": 0.95,
                    "context": "Had a great meeting with Sarah at the coffee shop",
                    "extracted_at": "2024-01-15T14:30:05Z"
                },
                {
                    "id": "660e8400-e29b-41d4-a716-446655440002",
                    "entity_type": "location",
                    "entity_value": "coffee shop downtown",
                    "confidence": 0.88,
                    "context": "meeting with Sarah at the coffee shop downtown",
                    "extracted_at": "2024-01-15T14:30:05Z"
                },
                {
                    "id": "660e8400-e29b-41d4-a716-446655440003",
                    "entity_type": "emotion",
                    "entity_value": "optimistic",
                    "confidence": 0.92,
                    "context": "I'm feeling optimistic about the collaboration",
                    "extracted_at": "2024-01-15T14:30:05Z"
                },
                {
                    "id": "660e8400-e29b-41d4-a716-446655440004",
                    "entity_type": "activity",
                    "entity_value": "meeting",
                    "confidence": 0.98,
                    "context": "Had a great meeting with Sarah",
                    "extracted_at": "2024-01-15T14:30:05Z"
                }
            ],
            "created_at": "2024-01-15T14:30:00Z",
            "updated_at": "2024-01-15T14:30:00Z"
        }
    },
    "thoughts_list_response": {
        "summary": "Paginated list of user thoughts",
        "value": {
            "thoughts": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "content": "Had a great meeting with Sarah at the coffee shop downtown.",
                    "timestamp": "2024-01-15T14:30:00Z",
                    "metadata": {
                        "location": {
                            "latitude": 40.7128,
                            "longitude": -74.0060,
                            "name": "Downtown Coffee Shop"
                        },
                        "mood": "optimistic",
                        "tags": ["work", "meeting"]
                    },
                    "semantic_entries": [
                        {
                            "id": "660e8400-e29b-41d4-a716-446655440001",
                            "entity_type": "person",
                            "entity_value": "Sarah",
                            "confidence": 0.95,
                            "context": "Had a great meeting with Sarah",
                            "extracted_at": "2024-01-15T14:30:05Z"
                        }
                    ],
                    "created_at": "2024-01-15T14:30:00Z",
                    "updated_at": "2024-01-15T14:30:00Z"
                }
            ],
            "total": 1,
            "skip": 0,
            "limit": 100
        }
    }
}

# Search API examples
SEARCH_EXAMPLES = {
    "search_request": {
        "summary": "Semantic search with filters",
        "value": {
            "query_text": "meetings with Sarah about projects",
            "date_range": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z"
            },
            "entity_filter": {
                "entity_types": ["person", "activity"],
                "entity_values": ["Sarah", "meeting"]
            },
            "sort_options": {
                "sort_by": "relevance",
                "sort_order": "desc"
            },
            "pagination": {
                "page": 1,
                "page_size": 10
            },
            "include_raw_content": True,
            "highlight_matches": True
        }
    },
    "search_response": {
        "summary": "Search results with ranking and highlighting",
        "value": {
            "results": [
                {
                    "thought": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "content": "Had a great meeting with Sarah at the coffee shop downtown.",
                        "timestamp": "2024-01-15T14:30:00Z",
                        "metadata": {
                            "mood": "optimistic",
                            "tags": ["work", "meeting"]
                        },
                        "semantic_entries": [],
                        "created_at": "2024-01-15T14:30:00Z",
                        "updated_at": "2024-01-15T14:30:00Z"
                    },
                    "matching_entities": [
                        {
                            "id": "660e8400-e29b-41d4-a716-446655440001",
                            "entity_type": "person",
                            "entity_value": "Sarah",
                            "confidence": 0.95,
                            "context": "Had a great meeting with Sarah",
                            "extracted_at": "2024-01-15T14:30:05Z"
                        }
                    ],
                    "matches": [
                        {
                            "field": "content",
                            "text": "meeting with Sarah",
                            "start_position": 15,
                            "end_position": 33,
                            "highlight": "Had a great <mark>meeting with Sarah</mark> at the coffee shop"
                        }
                    ],
                    "score": {
                        "semantic_similarity": 0.89,
                        "keyword_match": 0.75,
                        "recency_score": 0.95,
                        "confidence_score": 0.92,
                        "final_score": 0.88
                    },
                    "rank": 1
                }
            ],
            "total_count": 1,
            "page": 1,
            "page_size": 10,
            "query_text": "meetings with Sarah about projects",
            "search_time_ms": 45,
            "suggestions": ["meeting with Sarah", "project discussion", "collaboration"]
        }
    }
}

# Timeline API examples
TIMELINE_EXAMPLES = {
    "timeline_response": {
        "summary": "Timeline with chronological entries",
        "value": {
            "entries": [
                {
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "thought": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "content": "Had a great meeting with Sarah at the coffee shop downtown.",
                        "timestamp": "2024-01-15T14:30:00Z",
                        "metadata": {
                            "mood": "optimistic",
                            "tags": ["work", "meeting"]
                        },
                        "semantic_entries": [],
                        "created_at": "2024-01-15T14:30:00Z",
                        "updated_at": "2024-01-15T14:30:00Z"
                    },
                    "timestamp": "2024-01-15T14:30:00Z",
                    "entities": [
                        {
                            "id": "660e8400-e29b-41d4-a716-446655440001",
                            "entity_type": "person",
                            "entity_value": "Sarah",
                            "confidence": 0.95,
                            "context": "Had a great meeting with Sarah",
                            "extracted_at": "2024-01-15T14:30:05Z"
                        }
                    ],
                    "connections": [
                        {
                            "entity_id": "660e8400-e29b-41d4-a716-446655440001",
                            "entity_type": "person",
                            "entity_value": "Sarah",
                            "confidence": 0.95,
                            "relationship_type": "mentioned_with"
                        }
                    ],
                    "grouped_with": [],
                    "data_source": "thought"
                }
            ],
            "groups": [],
            "total_count": 1,
            "page": 1,
            "page_size": 20,
            "has_next": False,
            "has_previous": False,
            "summary": None
        }
    },
    "timeline_summary_response": {
        "summary": "Timeline summary statistics",
        "value": {
            "total_entries": 150,
            "date_range": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z"
            },
            "entity_counts": {
                "person": 45,
                "location": 32,
                "activity": 67,
                "emotion": 28,
                "organization": 15
            },
            "most_active_periods": [
                {
                    "period": "2024-01-15",
                    "count": "12"
                },
                {
                    "period": "2024-01-22",
                    "count": "8"
                }
            ],
            "top_entities": [
                {
                    "entity": "Sarah",
                    "count": "15"
                },
                {
                    "entity": "work",
                    "count": "23"
                }
            ]
        }
    }
}

# Admin API examples
ADMIN_EXAMPLES = {
    "create_user_request": {
        "summary": "Create a new user account",
        "value": {
            "email": "newuser@example.com",
            "password": "secure_password123",
            "is_admin": False,
            "is_active": True
        }
    },
    "create_user_response": {
        "summary": "Successfully created user",
        "value": {
            "user": {
                "id": "880e8400-e29b-41d4-a716-446655440000",
                "email": "newuser@example.com",
                "is_active": True,
                "is_admin": False,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "last_login": None
            },
            "message": "User created successfully"
        }
    },
    "users_list_response": {
        "summary": "Paginated list of users",
        "value": {
            "users": [
                {
                    "id": "880e8400-e29b-41d4-a716-446655440000",
                    "email": "user1@example.com",
                    "is_active": True,
                    "is_admin": False,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "last_login": "2024-01-15T09:15:00Z"
                },
                {
                    "id": "880e8400-e29b-41d4-a716-446655440001",
                    "email": "admin@example.com",
                    "is_active": True,
                    "is_admin": True,
                    "created_at": "2024-01-10T08:00:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "last_login": "2024-01-15T10:25:00Z"
                }
            ],
            "total": 2,
            "skip": 0,
            "limit": 100
        }
    },
    "health_check_response": {
        "summary": "System health status",
        "value": {
            "timestamp": "2024-01-15T10:30:00Z",
            "status": "healthy",
            "services": {
                "database": {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "response_time_ms": 15
                },
                "vector_store": {
                    "status": "healthy",
                    "message": "Vector store operational",
                    "response_time_ms": 23
                },
                "llm_service": {
                    "status": "healthy",
                    "message": "LLM service available",
                    "response_time_ms": 120
                }
            },
            "statistics": {
                "total_users": 150,
                "total_thoughts": 2847,
                "total_entities": 8934,
                "system_uptime_hours": 72.5
            }
        }
    }
}

def get_openapi_examples() -> Dict[str, Any]:
    """Get all OpenAPI examples organized by endpoint.
    
    Returns:
        Dictionary containing all API examples
    """
    return {
        "thoughts": THOUGHTS_EXAMPLES,
        "search": SEARCH_EXAMPLES,
        "timeline": TIMELINE_EXAMPLES,
        "admin": ADMIN_EXAMPLES,
        "common_errors": COMMON_ERROR_EXAMPLES,
    }

def get_security_schemes() -> Dict[str, Any]:
    """Get OpenAPI security schemes.
    
    Returns:
        Dictionary containing security scheme definitions
    """
    return {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from authentication endpoint"
        }
    }

def get_common_parameters() -> Dict[str, Any]:
    """Get common parameter definitions for reuse.
    
    Returns:
        Dictionary containing common parameter definitions
    """
    return {
        "PaginationSkip": {
            "name": "skip",
            "in": "query",
            "description": "Number of items to skip for pagination",
            "required": False,
            "schema": {
                "type": "integer",
                "minimum": 0,
                "default": 0
            }
        },
        "PaginationLimit": {
            "name": "limit", 
            "in": "query",
            "description": "Maximum number of items to return",
            "required": False,
            "schema": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "default": 100
            }
        },
        "DateRangeStart": {
            "name": "start_date",
            "in": "query", 
            "description": "Start date for filtering (ISO 8601 format)",
            "required": False,
            "schema": {
                "type": "string",
                "format": "date-time"
            }
        },
        "DateRangeEnd": {
            "name": "end_date",
            "in": "query",
            "description": "End date for filtering (ISO 8601 format)", 
            "required": False,
            "schema": {
                "type": "string",
                "format": "date-time"
            }
        }
    }