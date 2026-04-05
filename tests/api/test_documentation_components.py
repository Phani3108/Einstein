"""Tests for API documentation components without full app setup."""

import pytest
from src.api.documentation import (
    get_openapi_examples,
    get_security_schemes,
    get_common_parameters,
    THOUGHTS_EXAMPLES,
    SEARCH_EXAMPLES,
    TIMELINE_EXAMPLES,
    ADMIN_EXAMPLES,
    COMMON_ERROR_EXAMPLES
)
from src.api.versioning import (
    APIVersion,
    VersionInfo,
    get_api_version_header,
    validate_api_version,
    APIVersioningStrategy,
    is_feature_enabled
)


class TestDocumentationExamples:
    """Test documentation examples structure."""

    def test_get_openapi_examples_structure(self):
        """Test that OpenAPI examples have correct structure."""
        examples = get_openapi_examples()
        
        assert isinstance(examples, dict)
        assert "thoughts" in examples
        assert "search" in examples
        assert "timeline" in examples
        assert "admin" in examples
        assert "common_errors" in examples

    def test_thoughts_examples_content(self):
        """Test thoughts examples contain required fields."""
        assert "create_thought_request" in THOUGHTS_EXAMPLES
        assert "create_thought_response" in THOUGHTS_EXAMPLES
        assert "thoughts_list_response" in THOUGHTS_EXAMPLES
        
        # Check request example structure
        request_example = THOUGHTS_EXAMPLES["create_thought_request"]["value"]
        assert "content" in request_example
        assert "metadata" in request_example
        assert "timestamp" in request_example
        
        # Check response example structure
        response_example = THOUGHTS_EXAMPLES["create_thought_response"]["value"]
        assert "id" in response_example
        assert "content" in response_example
        assert "semantic_entries" in response_example
        assert isinstance(response_example["semantic_entries"], list)

    def test_search_examples_content(self):
        """Test search examples contain required fields."""
        assert "search_request" in SEARCH_EXAMPLES
        assert "search_response" in SEARCH_EXAMPLES
        
        # Check request example structure
        request_example = SEARCH_EXAMPLES["search_request"]["value"]
        assert "query_text" in request_example
        assert "date_range" in request_example
        assert "entity_filter" in request_example
        
        # Check response example structure
        response_example = SEARCH_EXAMPLES["search_response"]["value"]
        assert "results" in response_example
        assert "total_count" in response_example
        assert "search_time_ms" in response_example

    def test_timeline_examples_content(self):
        """Test timeline examples contain required fields."""
        assert "timeline_response" in TIMELINE_EXAMPLES
        assert "timeline_summary_response" in TIMELINE_EXAMPLES
        
        # Check timeline response structure
        timeline_example = TIMELINE_EXAMPLES["timeline_response"]["value"]
        assert "entries" in timeline_example
        assert "total_count" in timeline_example
        assert "page" in timeline_example
        
        # Check summary response structure
        summary_example = TIMELINE_EXAMPLES["timeline_summary_response"]["value"]
        assert "total_entries" in summary_example
        assert "entity_counts" in summary_example
        assert "date_range" in summary_example

    def test_admin_examples_content(self):
        """Test admin examples contain required fields."""
        assert "create_user_request" in ADMIN_EXAMPLES
        assert "create_user_response" in ADMIN_EXAMPLES
        assert "users_list_response" in ADMIN_EXAMPLES
        assert "health_check_response" in ADMIN_EXAMPLES
        
        # Check user creation request
        user_request = ADMIN_EXAMPLES["create_user_request"]["value"]
        assert "email" in user_request
        assert "password" in user_request
        assert "is_admin" in user_request
        
        # Check health check response
        health_response = ADMIN_EXAMPLES["health_check_response"]["value"]
        assert "status" in health_response
        assert "services" in health_response
        assert "statistics" in health_response

    def test_common_error_examples(self):
        """Test common error examples are properly structured."""
        assert "400" in COMMON_ERROR_EXAMPLES
        assert "401" in COMMON_ERROR_EXAMPLES
        assert "403" in COMMON_ERROR_EXAMPLES
        assert "404" in COMMON_ERROR_EXAMPLES
        assert "422" in COMMON_ERROR_EXAMPLES
        assert "429" in COMMON_ERROR_EXAMPLES
        assert "500" in COMMON_ERROR_EXAMPLES
        
        # Check error structure
        error_400 = COMMON_ERROR_EXAMPLES["400"]
        assert "description" in error_400
        assert "content" in error_400
        assert "application/json" in error_400["content"]


class TestSecuritySchemes:
    """Test security scheme definitions."""

    def test_get_security_schemes_structure(self):
        """Test security schemes have correct structure."""
        schemes = get_security_schemes()
        
        assert isinstance(schemes, dict)
        assert "BearerAuth" in schemes
        
        bearer_auth = schemes["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"
        assert "description" in bearer_auth


class TestCommonParameters:
    """Test common parameter definitions."""

    def test_get_common_parameters_structure(self):
        """Test common parameters have correct structure."""
        params = get_common_parameters()
        
        assert isinstance(params, dict)
        assert "PaginationSkip" in params
        assert "PaginationLimit" in params
        assert "DateRangeStart" in params
        assert "DateRangeEnd" in params
        
        # Check parameter structure
        skip_param = params["PaginationSkip"]
        assert skip_param["name"] == "skip"
        assert skip_param["in"] == "query"
        assert "description" in skip_param
        assert "schema" in skip_param
        
        # Check schema structure
        skip_schema = skip_param["schema"]
        assert skip_schema["type"] == "integer"
        assert skip_schema["minimum"] == 0
        assert skip_schema["default"] == 0


class TestAPIVersioning:
    """Test API versioning utilities."""

    def test_api_version_enum(self):
        """Test API version enum values."""
        assert APIVersion.V1 == "v1"
        assert APIVersion.V1.value == "v1"

    def test_version_info_current_version(self):
        """Test version info current version."""
        assert VersionInfo.CURRENT_VERSION == APIVersion.V1
        assert VersionInfo.get_latest_version() == APIVersion.V1

    def test_version_info_supported_versions(self):
        """Test version info supported versions."""
        assert APIVersion.V1 in VersionInfo.SUPPORTED_VERSIONS
        assert VersionInfo.is_supported(APIVersion.V1) is True

    def test_version_info_metadata(self):
        """Test version info metadata structure."""
        v1_info = VersionInfo.get_version_info(APIVersion.V1)
        
        assert "version" in v1_info
        assert "release_date" in v1_info
        assert "status" in v1_info
        assert "description" in v1_info
        assert "features" in v1_info
        assert "breaking_changes" in v1_info
        assert "deprecations" in v1_info
        
        assert isinstance(v1_info["features"], list)
        assert len(v1_info["features"]) > 0

    def test_get_api_version_header(self):
        """Test API version header generation."""
        headers = get_api_version_header()
        
        assert isinstance(headers, dict)
        assert "X-API-Version" in headers
        assert "X-API-Supported-Versions" in headers
        assert headers["X-API-Version"] == "v1"

    def test_validate_api_version(self):
        """Test API version validation."""
        assert validate_api_version("v1") is True
        assert validate_api_version("v2") is False
        assert validate_api_version("invalid") is False
        assert validate_api_version("") is False

    def test_versioning_strategy_path_extraction(self):
        """Test version extraction from URL paths."""
        assert APIVersioningStrategy.get_version_from_path("/api/v1/thoughts") == "v1"
        assert APIVersioningStrategy.get_version_from_path("/api/v2/search") == "v2"
        assert APIVersioningStrategy.get_version_from_path("/thoughts") == ""
        assert APIVersioningStrategy.get_version_from_path("/api/thoughts") == ""
        assert APIVersioningStrategy.get_version_from_path("") == ""

    def test_versioning_strategy_path_building(self):
        """Test versioned path building."""
        path = APIVersioningStrategy.build_versioned_path(APIVersion.V1, "thoughts")
        assert path == "/api/v1/thoughts"
        
        path = APIVersioningStrategy.build_versioned_path(APIVersion.V1, "/thoughts")
        assert path == "/api/v1/thoughts"

    def test_feature_flags(self):
        """Test feature flag functionality."""
        assert is_feature_enabled(APIVersion.V1, "entity_extraction") is True
        assert is_feature_enabled(APIVersion.V1, "semantic_search") is True
        assert is_feature_enabled(APIVersion.V1, "nonexistent_feature") is False


class TestRequestResponseValidation:
    """Test request and response validation models."""

    def test_thought_request_validation(self):
        """Test thought request model validation."""
        from src.api.models.thought_models import CreateThoughtRequest
        from pydantic import ValidationError
        
        # Valid request
        valid_data = {
            "content": "This is a valid thought content."
        }
        request = CreateThoughtRequest(**valid_data)
        assert request.content == "This is a valid thought content."

        # Test content validation - empty string
        with pytest.raises(ValidationError):
            CreateThoughtRequest(content="")

        # Test content validation - too short
        with pytest.raises(ValidationError):
            CreateThoughtRequest(content="Hi")

    def test_location_request_validation(self):
        """Test location request model validation."""
        from src.api.models.thought_models import GeoLocationRequest
        
        # Valid location
        valid_location = GeoLocationRequest(
            latitude=40.7128,
            longitude=-74.0060,
            name="New York City"
        )
        assert valid_location.latitude == 40.7128
        assert valid_location.longitude == -74.0060

        # Test latitude bounds
        with pytest.raises(ValueError):
            GeoLocationRequest(latitude=91.0, longitude=0.0)

        with pytest.raises(ValueError):
            GeoLocationRequest(latitude=-91.0, longitude=0.0)

        # Test longitude bounds
        with pytest.raises(ValueError):
            GeoLocationRequest(latitude=0.0, longitude=181.0)

        with pytest.raises(ValueError):
            GeoLocationRequest(latitude=0.0, longitude=-181.0)

    def test_weather_request_validation(self):
        """Test weather request model validation."""
        from src.api.models.thought_models import WeatherDataRequest
        
        # Valid weather data
        valid_weather = WeatherDataRequest(
            temperature=22.5,
            condition="sunny",
            humidity=65.0
        )
        assert valid_weather.temperature == 22.5
        assert valid_weather.condition == "sunny"
        assert valid_weather.humidity == 65.0

        # Test temperature bounds
        with pytest.raises(ValueError):
            WeatherDataRequest(temperature=-60.0)

        with pytest.raises(ValueError):
            WeatherDataRequest(temperature=70.0)

        # Test humidity bounds
        with pytest.raises(ValueError):
            WeatherDataRequest(humidity=-10.0)

        with pytest.raises(ValueError):
            WeatherDataRequest(humidity=150.0)


class TestDocumentationQuality:
    """Test documentation content quality."""

    def test_example_completeness(self):
        """Test that examples are complete and realistic."""
        # Check thought creation example
        thought_example = THOUGHTS_EXAMPLES["create_thought_request"]["value"]
        assert len(thought_example["content"]) > 50  # Substantial content
        assert "metadata" in thought_example
        assert "location" in thought_example["metadata"]
        assert "weather" in thought_example["metadata"]
        assert "tags" in thought_example["metadata"]

        # Check search example
        search_example = SEARCH_EXAMPLES["search_request"]["value"]
        assert len(search_example["query_text"]) > 10  # Meaningful query
        assert "entity_filter" in search_example
        assert "date_range" in search_example

    def test_response_example_realism(self):
        """Test that response examples are realistic."""
        # Check thought response
        response_example = THOUGHTS_EXAMPLES["create_thought_response"]["value"]
        assert len(response_example["semantic_entries"]) > 0
        
        # Check semantic entry structure
        semantic_entry = response_example["semantic_entries"][0]
        assert "entity_type" in semantic_entry
        assert "entity_value" in semantic_entry
        assert "confidence" in semantic_entry
        assert 0 <= semantic_entry["confidence"] <= 1

        # Check search response
        search_response = SEARCH_EXAMPLES["search_response"]["value"]
        assert len(search_response["results"]) > 0
        
        # Check search result structure
        search_result = search_response["results"][0]
        assert "score" in search_result
        assert "rank" in search_result
        assert "matches" in search_result

    def test_error_example_consistency(self):
        """Test that error examples are consistent."""
        for status_code, error_spec in COMMON_ERROR_EXAMPLES.items():
            assert "description" in error_spec
            assert "content" in error_spec
            assert "application/json" in error_spec["content"]
            
            example = error_spec["content"]["application/json"]["example"]
            assert "error" in example
            assert "timestamp" in example
            # Detail is optional but should be string if present
            if "detail" in example:
                assert isinstance(example["detail"], str)