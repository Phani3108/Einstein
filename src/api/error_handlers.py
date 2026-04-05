"""Error handling and response formatting for the API layer."""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.domain.exceptions import (
    AuthenticationError,
    DomainError,
    EmbeddingError,
    EntityExtractionError,
    InvalidTokenError,
    SearchError,
    SearchIndexError,
    SearchQueryError,
    SearchRankingError,
    ThoughtNotFoundError,
    TimelineError,
    TimelineGroupingError,
    TimelineQueryError,
    TokenError,
    UserAlreadyExistsError,
    UserManagementError,
    UserNotFoundError,
    UserRegistrationError,
    VectorStoreError,
)

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    
    error: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: Optional[Any] = None,
        request_id: Optional[str] = None,
        status_code: int = 500,
    ) -> "ErrorResponse":
        """Create a standardized error response.
        
        Args:
            code: Error code identifier
            message: Human-readable error message
            details: Additional error details
            request_id: Unique request identifier
            status_code: HTTP status code
            
        Returns:
            ErrorResponse: Formatted error response
        """
        return cls(
            error={
                "code": code,
                "message": message,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id or str(uuid4()),
                "status_code": status_code,
            }
        )


class ErrorHandler:
    """Centralized error handling and response formatting."""
    
    # Map domain exceptions to HTTP status codes
    EXCEPTION_STATUS_MAP = {
        # Authentication/Authorization errors
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        InvalidTokenError: status.HTTP_401_UNAUTHORIZED,
        TokenError: status.HTTP_401_UNAUTHORIZED,
        
        # Not found errors
        ThoughtNotFoundError: status.HTTP_404_NOT_FOUND,
        UserNotFoundError: status.HTTP_404_NOT_FOUND,
        
        # Validation/Bad request errors
        SearchQueryError: status.HTTP_400_BAD_REQUEST,
        TimelineQueryError: status.HTTP_400_BAD_REQUEST,
        UserAlreadyExistsError: status.HTTP_409_CONFLICT,
        UserRegistrationError: status.HTTP_400_BAD_REQUEST,
        
        # Processing errors
        EntityExtractionError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        EmbeddingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        VectorStoreError: status.HTTP_503_SERVICE_UNAVAILABLE,
        SearchError: status.HTTP_503_SERVICE_UNAVAILABLE,
        SearchIndexError: status.HTTP_503_SERVICE_UNAVAILABLE,
        SearchRankingError: status.HTTP_503_SERVICE_UNAVAILABLE,
        TimelineError: status.HTTP_503_SERVICE_UNAVAILABLE,
        TimelineGroupingError: status.HTTP_503_SERVICE_UNAVAILABLE,
        UserManagementError: status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    
    # Map HTTP status codes to error codes
    STATUS_CODE_MAP = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "UNPROCESSABLE_ENTITY",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    
    @classmethod
    def get_status_code(cls, exception: Exception) -> int:
        """Get HTTP status code for exception.
        
        Args:
            exception: Exception to map
            
        Returns:
            int: HTTP status code
        """
        return cls.EXCEPTION_STATUS_MAP.get(
            type(exception), 
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    @classmethod
    def get_error_code(cls, status_code: int) -> str:
        """Get error code for HTTP status code.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            str: Error code
        """
        return cls.STATUS_CODE_MAP.get(status_code, "UNKNOWN_ERROR")
    
    @classmethod
    def format_domain_exception(
        cls, 
        exception: DomainError, 
        request_id: Optional[str] = None
    ) -> tuple[ErrorResponse, int]:
        """Format domain exception as error response.
        
        Args:
            exception: Domain exception to format
            request_id: Unique request identifier
            
        Returns:
            tuple: Error response and HTTP status code
        """
        status_code = cls.get_status_code(exception)
        error_code = cls.get_error_code(status_code)
        
        # Extract additional details from specific exceptions
        details = None
        if hasattr(exception, 'thought_id'):
            details = {"thought_id": str(exception.thought_id)}
        elif hasattr(exception, 'user_id'):
            details = {"user_id": str(exception.user_id)}
        elif hasattr(exception, 'email'):
            details = {"email": exception.email}
        
        error_response = ErrorResponse.create(
            code=error_code,
            message=str(exception),
            details=details,
            request_id=request_id,
            status_code=status_code,
        )
        
        return error_response, status_code
    
    @classmethod
    def format_http_exception(
        cls, 
        exception: HTTPException, 
        request_id: Optional[str] = None
    ) -> tuple[ErrorResponse, int]:
        """Format HTTP exception as error response.
        
        Args:
            exception: HTTP exception to format
            request_id: Unique request identifier
            
        Returns:
            tuple: Error response and HTTP status code
        """
        error_code = cls.get_error_code(exception.status_code)
        
        error_response = ErrorResponse.create(
            code=error_code,
            message=exception.detail,
            details=getattr(exception, 'details', None),
            request_id=request_id,
            status_code=exception.status_code,
        )
        
        return error_response, exception.status_code
    
    @classmethod
    def format_validation_exception(
        cls, 
        exception: Exception, 
        request_id: Optional[str] = None
    ) -> tuple[ErrorResponse, int]:
        """Format validation exception as error response.
        
        Args:
            exception: Validation exception to format
            request_id: Unique request identifier
            
        Returns:
            tuple: Error response and HTTP status code
        """
        # Handle Pydantic validation errors
        if hasattr(exception, 'errors'):
            details = [
                ErrorDetail(
                    field=".".join(str(loc) for loc in error.get("loc", [])),
                    message=error.get("msg", "Validation error"),
                    code=error.get("type", "validation_error"),
                ).dict()
                for error in exception.errors()
            ]
        else:
            details = None
        
        error_response = ErrorResponse.create(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=details,
            request_id=request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        
        return error_response, status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @classmethod
    def format_generic_exception(
        cls, 
        exception: Exception, 
        request_id: Optional[str] = None
    ) -> tuple[ErrorResponse, int]:
        """Format generic exception as error response.
        
        Args:
            exception: Generic exception to format
            request_id: Unique request identifier
            
        Returns:
            tuple: Error response and HTTP status code
        """
        error_response = ErrorResponse.create(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            details={"exception_type": type(exception).__name__},
            request_id=request_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        
        return error_response, status.HTTP_500_INTERNAL_SERVER_ERROR


async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle domain exceptions.
    
    Args:
        request: FastAPI request object
        exc: Domain exception
        
    Returns:
        JSONResponse: Formatted error response
    """
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the error with context
    logger.error(
        "Domain exception occurred",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )
    
    error_response, status_code = ErrorHandler.format_domain_exception(exc, request_id)
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
        
    Returns:
        JSONResponse: Formatted error response
    """
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the error with context
    logger.warning(
        "HTTP exception occurred",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    error_response, status_code = ErrorHandler.format_http_exception(exc, request_id)
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict(),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle validation exceptions.
    
    Args:
        request: FastAPI request object
        exc: Validation exception
        
    Returns:
        JSONResponse: Formatted error response
    """
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the error with context
    logger.warning(
        "Validation exception occurred",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    error_response, status_code = ErrorHandler.format_validation_exception(exc, request_id)
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic exceptions.
    
    Args:
        request: FastAPI request object
        exc: Generic exception
        
    Returns:
        JSONResponse: Formatted error response
    """
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the error with full traceback
    logger.error(
        "Unhandled exception occurred",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )
    
    error_response, status_code = ErrorHandler.format_generic_exception(exc, request_id)
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict(),
    )