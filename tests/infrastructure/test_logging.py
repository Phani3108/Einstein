"""Tests for logging functionality."""

import json
import logging
import pytest
from io import StringIO
from unittest.mock import Mock, patch

from src.infrastructure.logging import (
    StructuredFormatter,
    RequestContextFilter,
    setup_logging,
    get_logger,
    LoggerMixin,
    log_function_call,
    log_external_api_call,
    log_database_operation,
)


class TestStructuredFormatter:
    """Test StructuredFormatter class."""
    
    def test_structured_formatter_adds_fields(self):
        """Test that structured formatter adds required fields."""
        formatter = StructuredFormatter()
        
        # Create a log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test",
            level=logging.INFO,
            fn="test.py",
            lno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        # Format the record
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        # Check required fields
        assert "timestamp" in log_data
        assert log_data["service"] == "personal-semantic-engine"
        assert log_data["version"] == "0.1.0"
        assert log_data["level"] == "INFO"
        assert log_data["module"] == "test"
        assert "function" in log_data  # Function name might be None in some cases
        assert log_data["line"] == 10
        assert "thread_id" in log_data
        assert "thread_name" in log_data
        assert "process_id" in log_data
        assert log_data["message"] == "Test message"


class TestRequestContextFilter:
    """Test RequestContextFilter class."""
    
    def test_request_context_filter_adds_defaults(self):
        """Test that request context filter adds default values."""
        filter_obj = RequestContextFilter()
        
        # Create a log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test",
            level=logging.INFO,
            fn="test.py",
            lno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        # Apply filter
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.request_id is None
        assert record.user_id is None
        assert record.correlation_id is None
    
    def test_request_context_filter_preserves_existing(self):
        """Test that request context filter preserves existing values."""
        filter_obj = RequestContextFilter()
        
        # Create a log record with existing context
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test",
            level=logging.INFO,
            fn="test.py",
            lno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.request_id = "test-123"
        record.user_id = "user-456"
        
        # Apply filter
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.request_id == "test-123"
        assert record.user_id == "user-456"
        assert record.correlation_id is None


class TestSetupLogging:
    """Test setup_logging function."""
    
    @patch('logging.config.dictConfig')
    def test_setup_logging_default_config(self, mock_dict_config):
        """Test setup_logging with default configuration."""
        setup_logging()
        
        # Verify dictConfig was called
        mock_dict_config.assert_called_once()
        config = mock_dict_config.call_args[0][0]
        
        # Check basic configuration
        assert config["version"] == 1
        assert config["disable_existing_loggers"] is False
        assert "json" in config["formatters"]
        assert "console" in config["handlers"]
        assert "request_context" in config["filters"]
    
    @patch('logging.config.dictConfig')
    def test_setup_logging_with_file_logging(self, mock_dict_config):
        """Test setup_logging with file logging enabled."""
        setup_logging(
            level="DEBUG",
            format_type="text",
            enable_console=True,
            enable_file=True,
            log_file="/tmp/test.log",
        )
        
        mock_dict_config.assert_called_once()
        config = mock_dict_config.call_args[0][0]
        
        # Check file handler is included
        assert "file" in config["handlers"]
        assert config["handlers"]["file"]["filename"] == "/tmp/test.log"
        assert config["handlers"]["file"]["level"] == "DEBUG"


class TestGetLogger:
    """Test get_logger function."""
    
    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test.module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"


class TestLoggerMixin:
    """Test LoggerMixin class."""
    
    def test_logger_mixin_provides_logger(self):
        """Test that LoggerMixin provides a logger property."""
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        logger = instance.logger
        
        assert isinstance(logger, logging.Logger)
        assert logger.name.endswith("TestClass")


class TestLogFunctionCall:
    """Test log_function_call function."""
    
    @patch('src.infrastructure.logging.get_logger')
    def test_log_function_call_success(self, mock_get_logger):
        """Test logging successful function call."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_function_call(
            func_name="test_function",
            args={"param1": "value1"},
            result="success",
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Function call completed" in call_args[0][0]
        assert call_args[1]["extra"]["function"] == "test_function"
        assert call_args[1]["extra"]["arguments"] == {"param1": "value1"}
        assert call_args[1]["extra"]["result_type"] == "str"
    
    @patch('src.infrastructure.logging.get_logger')
    def test_log_function_call_error(self, mock_get_logger):
        """Test logging failed function call."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        error = ValueError("Test error")
        log_function_call(
            func_name="test_function",
            args={"param1": "value1"},
            error=error,
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Function call failed" in call_args[0][0]
        assert call_args[1]["extra"]["function"] == "test_function"
        assert call_args[1]["extra"]["error"] == "Test error"
        assert call_args[1]["extra"]["error_type"] == "ValueError"
        assert call_args[1]["exc_info"] is True


class TestLogExternalApiCall:
    """Test log_external_api_call function."""
    
    @patch('src.infrastructure.logging.get_logger')
    def test_log_external_api_call_success(self, mock_get_logger):
        """Test logging successful external API call."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_external_api_call(
            service="openai",
            endpoint="/embeddings",
            method="POST",
            status_code=200,
            duration=1.5,
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "External API call completed" in call_args[0][0]
        assert call_args[1]["extra"]["external_service"] == "openai"
        assert call_args[1]["extra"]["endpoint"] == "/embeddings"
        assert call_args[1]["extra"]["method"] == "POST"
        assert call_args[1]["extra"]["status_code"] == 200
        assert call_args[1]["extra"]["duration_seconds"] == 1.5
    
    @patch('src.infrastructure.logging.get_logger')
    def test_log_external_api_call_error(self, mock_get_logger):
        """Test logging failed external API call."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        error = ConnectionError("Connection failed")
        log_external_api_call(
            service="pinecone",
            endpoint="/query",
            method="POST",
            error=error,
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "External API call failed" in call_args[0][0]
        assert call_args[1]["extra"]["external_service"] == "pinecone"
        assert call_args[1]["extra"]["error"] == "Connection failed"
        assert call_args[1]["extra"]["error_type"] == "ConnectionError"
        assert call_args[1]["exc_info"] is True


class TestLogDatabaseOperation:
    """Test log_database_operation function."""
    
    @patch('src.infrastructure.logging.get_logger')
    def test_log_database_operation_success(self, mock_get_logger):
        """Test logging successful database operation."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_database_operation(
            operation="SELECT",
            table="thoughts",
            duration=0.5,
            rows_affected=10,
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Database operation completed" in call_args[0][0]
        assert call_args[1]["extra"]["database_operation"] == "SELECT"
        assert call_args[1]["extra"]["table"] == "thoughts"
        assert call_args[1]["extra"]["duration_seconds"] == 0.5
        assert call_args[1]["extra"]["rows_affected"] == 10
    
    @patch('src.infrastructure.logging.get_logger')
    def test_log_database_operation_error(self, mock_get_logger):
        """Test logging failed database operation."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        error = Exception("Database connection failed")
        log_database_operation(
            operation="INSERT",
            table="users",
            error=error,
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Database operation failed" in call_args[0][0]
        assert call_args[1]["extra"]["database_operation"] == "INSERT"
        assert call_args[1]["extra"]["table"] == "users"
        assert call_args[1]["extra"]["error"] == "Database connection failed"
        assert call_args[1]["extra"]["error_type"] == "Exception"
        assert call_args[1]["exc_info"] is True