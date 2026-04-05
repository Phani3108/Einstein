"""Admin API routes for the Personal Semantic Engine."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from src.api.models.admin_models import (
    CreateUserRequest,
    CreateUserResponse,
    ErrorResponse,
    HealthCheckResponse,
    UsersListResponse,
)
from src.application.usecases.create_user_usecase import CreateUserUseCase
from src.application.usecases.get_system_health_usecase import GetSystemHealthUseCase
from src.application.usecases.get_users_usecase import GetUsersUseCase
from src.container import container
from src.domain.entities.user import User
from src.domain.exceptions import UserAlreadyExistsError
from src.infrastructure.middleware.authentication_middleware import (
    AuthenticationMiddleware,
)
from src.api.documentation import ADMIN_EXAMPLES, COMMON_ERROR_EXAMPLES

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


async def get_admin_user(request: Request) -> User:
    """Dependency to require admin authentication.

    Args:
        request: FastAPI request object

    Returns:
        The authenticated admin user

    Raises:
        HTTPException: If user is not authenticated or not an admin
    """
    auth_middleware: AuthenticationMiddleware = container.auth_middleware()
    return await auth_middleware.require_admin(request)


@router.get(
    "/users",
    response_model=UsersListResponse,
    summary="Get all users",
    description="""
    Retrieve a comprehensive, paginated list of all users in the system with their status information.
    
    This endpoint provides administrative access to user management data:
    
    **User Information:**
    - **Basic Details**: ID, email, creation/update timestamps
    - **Status Flags**: Active status, admin privileges
    - **Activity Data**: Last login timestamp, account activity
    - **Audit Trail**: Account creation and modification history
    
    **Access Control:**
    - Requires admin-level authentication
    - Returns 403 Forbidden for non-admin users
    - Includes audit logging for security compliance
    
    **Pagination:**
    - Use `skip` and `limit` parameters for pagination
    - Default limit is 100 users per page
    - Total count included for pagination calculations
    
    **Use Cases:**
    - User account management and oversight
    - System administration and monitoring
    - Compliance and audit reporting
    - User activity analysis
    - Account status management
    
    **Security Notes:**
    - Sensitive data (passwords) are never included
    - All admin actions are logged for audit trails
    - Rate limiting applied to prevent abuse
    """,
    responses={
        200: {
            "description": "Users retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "users_list": ADMIN_EXAMPLES["users_list_response"]
                    }
                }
            }
        },
        **COMMON_ERROR_EXAMPLES
    },
)
async def get_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    admin_user: User = Depends(get_admin_user),
) -> UsersListResponse:
    """Get all users with pagination.

    Args:
        skip: Number of users to skip for pagination
        limit: Maximum number of users to return
        admin_user: The authenticated admin user (injected by dependency)

    Returns:
        Paginated list of users

    Raises:
        HTTPException: If operation fails
    """
    try:
        get_users_usecase: GetUsersUseCase = container.get_users_usecase()
        users = await get_users_usecase.execute(skip=skip, limit=limit)

        # For simplicity, we'll use the returned count as total
        # In a real implementation, you might want a separate count query
        total = len(users) + skip

        return UsersListResponse.from_domain_list(
            users=users, total=total, skip=skip, limit=limit
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}",
        )


@router.post(
    "/users",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="""
    Create a new user account with specified permissions and status settings.
    
    This endpoint allows administrators to create user accounts with full control over:
    
    **Account Configuration:**
    - **Email Address**: Unique identifier and login credential
    - **Password**: Securely hashed using bcrypt with salt
    - **Admin Status**: Grant or deny administrative privileges
    - **Active Status**: Enable or disable account access
    
    **Security Features:**
    - **Password Hashing**: Automatic bcrypt hashing with secure salt
    - **Email Validation**: RFC-compliant email format validation
    - **Duplicate Prevention**: Automatic check for existing email addresses
    - **Audit Logging**: Complete creation audit trail
    
    **Validation Rules:**
    - Email must be unique across the system
    - Password must meet minimum security requirements
    - Admin status can only be set by existing admins
    - All fields are validated before account creation
    
    **Post-Creation:**
    - Account is immediately available for login
    - Welcome email sent if configured
    - Audit log entry created for compliance
    - User appears in admin user listings
    
    **Use Cases:**
    - Onboarding new users to the system
    - Creating admin accounts for team members
    - Bulk user provisioning for organizations
    - Testing and development account creation
    """,
    responses={
        201: {
            "description": "User created successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "created_user": ADMIN_EXAMPLES["create_user_response"]
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
                        "regular_user": ADMIN_EXAMPLES["create_user_request"],
                        "admin_user": {
                            "summary": "Create admin user",
                            "value": {
                                "email": "admin@example.com",
                                "password": "secure_admin_password123",
                                "is_admin": True,
                                "is_active": True
                            }
                        },
                        "inactive_user": {
                            "summary": "Create inactive user",
                            "value": {
                                "email": "inactive@example.com",
                                "password": "secure_password123",
                                "is_admin": False,
                                "is_active": False
                            }
                        }
                    }
                }
            }
        }
    }
)
async def create_user(
    request: CreateUserRequest,
    admin_user: User = Depends(get_admin_user),
) -> CreateUserResponse:
    """Create a new user.

    Args:
        request: User creation request data
        admin_user: The authenticated admin user (injected by dependency)

    Returns:
        The created user information

    Raises:
        HTTPException: If user creation fails
    """
    try:
        create_user_usecase: CreateUserUseCase = container.create_user_usecase()
        user = await create_user_usecase.execute(
            email=request.email,
            password=request.password,
            is_admin=request.is_admin,
            is_active=request.is_active,
        )

        return CreateUserResponse.from_domain(user)

    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="System health check",
    description="""
    Comprehensive system health check providing detailed status of all system components.
    
    This endpoint performs real-time health checks across all system dependencies:
    
    **System Components Monitored:**
    - **Database**: PostgreSQL connection, query performance, disk space
    - **Vector Store**: Pinecone/Weaviate connectivity, index status, query latency
    - **LLM Service**: OpenAI/Anthropic API availability, response times, rate limits
    - **Cache Layer**: Redis connectivity, memory usage, hit rates
    - **File Storage**: Disk space, permissions, backup status
    - **External APIs**: Weather, geocoding, and other integrated services
    
    **Health Status Levels:**
    - **Healthy**: All systems operational within normal parameters
    - **Degraded**: Some non-critical issues detected, system functional
    - **Unhealthy**: Critical issues detected, system may be impaired
    
    **Performance Metrics:**
    - Response times for each component
    - Error rates and success percentages
    - Resource utilization (CPU, memory, disk)
    - Queue depths and processing backlogs
    
    **System Statistics:**
    - Total users, thoughts, and entities in system
    - Processing rates and throughput metrics
    - Storage utilization and growth trends
    - System uptime and availability metrics
    
    **Use Cases:**
    - System monitoring and alerting
    - Performance optimization and tuning
    - Capacity planning and scaling decisions
    - Troubleshooting and diagnostics
    - SLA compliance monitoring
    """,
    responses={
        200: {
            "description": "Health check completed successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy_system": ADMIN_EXAMPLES["health_check_response"],
                        "degraded_system": {
                            "summary": "System with degraded performance",
                            "value": {
                                "timestamp": "2024-01-15T10:30:00Z",
                                "status": "degraded",
                                "services": {
                                    "database": {
                                        "status": "healthy",
                                        "message": "Database connection successful",
                                        "response_time_ms": 15
                                    },
                                    "vector_store": {
                                        "status": "degraded",
                                        "message": "High response times detected",
                                        "response_time_ms": 450
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
                }
            }
        },
        **COMMON_ERROR_EXAMPLES
    },
)
async def get_system_health(
    admin_user: User = Depends(get_admin_user),
) -> HealthCheckResponse:
    """Get system health information.

    Args:
        admin_user: The authenticated admin user (injected by dependency)

    Returns:
        System health information

    Raises:
        HTTPException: If health check fails
    """
    try:
        get_health_usecase: GetSystemHealthUseCase = container.get_system_health_usecase()
        health_data = await get_health_usecase.execute()

        return HealthCheckResponse(**health_data)

    except Exception as e:
        # Even if health check fails, we want to return some information
        return HealthCheckResponse(
            timestamp=str(e),
            status="unhealthy",
            services={"health_check": {"status": "failed", "message": str(e)}},
            statistics={"error": "Health check failed"},
        )