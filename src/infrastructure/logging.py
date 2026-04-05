"""Structured logging configuration for the Personal Semantic Engine."""

import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record.
        
        Args:
            log_record: Log record dictionary to modify
            record: Original log record
            message_dict: Message dictionary
        """
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add service information
        log_record['service'] = 'personal-semantic-engine'
        log_record['version'] = '0.1.0'
        
        # Add level name
        log_record['level'] = record.levelname
        
        # Add module and function information
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add thread information
        log_record['thread_id'] = record.thread
        log_record['thread_name'] = record.threadName
        
        # Add process information
        log_record['process_id'] = record.process


class RequestContextFilter(logging.Filter):
    """Filter to add request context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record.
        
        Args:
            record: Log record to modify
            
        Returns:
            bool: Always True to allow the record
        """
        # Add request context if available
        # This would be set by middleware in a real application
        if not hasattr(record, 'request_id'):
            record.request_id = None
        if not hasattr(record, 'user_id'):
            record.user_id = None
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = None
            
        return True


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    enable_console: bool = True,
    enable_file: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """Set up structured logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ('json' or 'text')
        enable_console: Enable console logging
        enable_file: Enable file logging
        log_file: Log file path (required if enable_file is True)
    """
    # Define formatters
    formatters = {
        'json': {
            '()': StructuredFormatter,
            'format': '%(timestamp)s %(level)s %(name)s %(message)s',
        },
        'text': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    }
    
    # Define handlers
    handlers = {}
    
    if enable_console:
        handlers['console'] = {
            'class': 'logging.StreamHandler',
            'level': level,
            'formatter': format_type,
            'stream': sys.stdout,
            'filters': ['request_context'],
        }
    
    if enable_file and log_file:
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': level,
            'formatter': format_type,
            'filename': log_file,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'filters': ['request_context'],
        }
    
    # Define filters
    filters = {
        'request_context': {
            '()': RequestContextFilter,
        },
    }
    
    # Define loggers
    loggers = {
        '': {  # Root logger
            'level': level,
            'handlers': list(handlers.keys()),
            'propagate': False,
        },
        'src': {  # Application logger
            'level': level,
            'handlers': list(handlers.keys()),
            'propagate': False,
        },
        'uvicorn': {
            'level': 'INFO',
            'handlers': list(handlers.keys()),
            'propagate': False,
        },
        'uvicorn.access': {
            'level': 'INFO',
            'handlers': list(handlers.keys()),
            'propagate': False,
        },
        'sqlalchemy.engine': {
            'level': 'WARNING',
            'handlers': list(handlers.keys()),
            'propagate': False,
        },
    }
    
    # Configure logging
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'filters': filters,
        'handlers': handlers,
        'loggers': loggers,
    }
    
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Configured logger
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class.
        
        Returns:
            logging.Logger: Class-specific logger
        """
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")


def log_function_call(func_name: str, args: Dict[str, Any], result: Any = None, error: Exception = None) -> None:
    """Log function call with arguments and result.
    
    Args:
        func_name: Function name
        args: Function arguments
        result: Function result (if successful)
        error: Exception (if failed)
    """
    logger = get_logger(__name__)
    
    log_data = {
        'function': func_name,
        'arguments': args,
    }
    
    if error:
        log_data['error'] = str(error)
        log_data['error_type'] = type(error).__name__
        logger.error("Function call failed", extra=log_data, exc_info=True)
    else:
        if result is not None:
            log_data['result_type'] = type(result).__name__
            # Don't log the full result to avoid sensitive data
            if hasattr(result, '__len__'):
                log_data['result_length'] = len(result)
        logger.info("Function call completed", extra=log_data)


def log_external_api_call(
    service: str,
    endpoint: str,
    method: str,
    status_code: Optional[int] = None,
    duration: Optional[float] = None,
    error: Optional[Exception] = None,
) -> None:
    """Log external API call.
    
    Args:
        service: External service name
        endpoint: API endpoint
        method: HTTP method
        status_code: HTTP status code
        duration: Request duration in seconds
        error: Exception if call failed
    """
    logger = get_logger(__name__)
    
    log_data = {
        'external_service': service,
        'endpoint': endpoint,
        'method': method,
    }
    
    if status_code:
        log_data['status_code'] = status_code
    if duration:
        log_data['duration_seconds'] = duration
    
    if error:
        log_data['error'] = str(error)
        log_data['error_type'] = type(error).__name__
        logger.error("External API call failed", extra=log_data, exc_info=True)
    else:
        logger.info("External API call completed", extra=log_data)


def log_database_operation(
    operation: str,
    table: str,
    duration: Optional[float] = None,
    rows_affected: Optional[int] = None,
    error: Optional[Exception] = None,
) -> None:
    """Log database operation.
    
    Args:
        operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        duration: Operation duration in seconds
        rows_affected: Number of rows affected
        error: Exception if operation failed
    """
    logger = get_logger(__name__)
    
    log_data = {
        'database_operation': operation,
        'table': table,
    }
    
    if duration:
        log_data['duration_seconds'] = duration
    if rows_affected is not None:
        log_data['rows_affected'] = rows_affected
    
    if error:
        log_data['error'] = str(error)
        log_data['error_type'] = type(error).__name__
        logger.error("Database operation failed", extra=log_data, exc_info=True)
    else:
        logger.info("Database operation completed", extra=log_data)