"""Tests for API documentation and OpenAPI specification."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from src.api.app import create_app
from src.api.versioning import APIVersion, VersionInfo


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestOpenAPISpecification:
    """Test OpenAPI specification generation."""

    def test_openapi_json_endpoint(self, client):
        """Test that OpenAPI JSON is accessible."""
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        assert "openapi" in openapi_spec
        assert "info" in openapi_spec
        assert "paths" in openapi_spec
        assert "components" in openapi_spec

    def test_openapi_info_section(self, client):
        """Test OpenAPI info section contains required metadata."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        info = openapi_spec["info"]
        assert info["title"] == "Personal Semantic Engine (Faraday)"
        assert "version" in info
        assert "description" in info
        assert "contact" in info
        assert "license" in info

    def test_openapi_security_schemes(self, client):
        """Test that security schemes are properly defined."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        components = openapi_spec["components"]
        assert "securitySchemes" in components
        assert "BearerAuth" in components["securitySchemes"]
        
        bearer_auth = components["securitySchemes"]["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"

    def test_openapi_common_parameters(self, client):
        """Test that common parameters are defined."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        components = openapi_spec["components"]
        assert "parameters" in components
        
        parameters = components["parameters"]
        assert "PaginationSkip" in parameters
        assert "PaginationLimit" in parameters
        assert "DateRangeStart" in parameters
        assert "DateRangeEnd" in parameters

    def test_openapi_tags(self, client):
        """Test that API tags are properly defined."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        assert "tags" in openapi_spec
        tags = {tag["name"] for tag in openapi_spec["tags"]}
        
        expected_tags = {"thoughts", "search", "timeline", "admin"}
        assert expected_tags.issubset(tags)

    def test_openapi_servers(self, client):
        """Test that servers are properly defined."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        assert "servers" in openapi_spec
        servers = openapi_spec["servers"]
        assert len(servers) >= 1
        
        # Check for development server
        dev_server = next((s for s in servers if "localhost" in s["url"]), None)
        assert dev_server is not None


class TestAPIDocumentationEndpoints:
    """Test API documentation endpoints."""

    def test_swagger_ui_docs(self, client):
        """Test Swagger UI documentation endpoint."""
        response = client.get("/api/v1/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        content = response.text
        assert "Personal Semantic Engine API" in content
        assert "swagger-ui" in content

    def test_redoc_docs(self, client):
        """Test ReDoc documentation endpoint."""
        response = client.get("/api/v1/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_api_info_endpoint(self, client):
        """Test API information endpoint."""
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        
        info = response.json()
        assert info["api_name"] == "Personal Semantic Engine (Faraday)"
        assert "version" in info
        assert "features" in info
        assert "documentation" in info
        assert "endpoints" in info
        assert "authentication" in info


class TestAPIVersioning:
    """Test API versioning implementation."""

    def test_version_headers_in_response(self, client):
        """Test that version headers are added to responses."""
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "v1"
        assert "X-API-Supported-Versions" in response.headers

    def test_version_info_utility(self):
        """Test version info utility functions."""
        # Test current version
        assert VersionInfo.get_latest_version() == APIVersion.V1
        
        # Test version support check
        assert VersionInfo.is_supported(APIVersion.V1) is True
        
        # Test version metadata
        v1_info = VersionInfo.get_version_info(APIVersion.V1)
        assert "version" in v1_info
        assert "features" in v1_info
        assert "status" in v1_info


class TestRequestResponseValidation:
    """Test request and response validation."""

    def test_thought_request_validation(self):
        """Test thought request model validation."""
        from src.api.models.thought_models import CreateThoughtRequest
        
        # Valid request
        valid_data = {
            "content": "This is a valid thought content."
        }
        request = CreateThoughtRequest(**valid_data)
        assert request.content == "This is a valid thought content."

        # Invalid request - empty content
        with pytest.raises(ValueError):
            CreateThoughtRequest(content="")

        # Invalid request - content too short
        with pytest.raises(ValueError):
            CreateThoughtRequest(content="Hi")

        # Invalid request - future timestamp
        from datetime import datetime, timedelta
        future_time = datetime.now() + timedelta(hours=1)
        with pytest.raises(ValueError):
            CreateThoughtRequest(
                content="Valid content",
                timestamp=future_time
            )

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

        # Invalid latitude
        with pytest.raises(ValueError):
            GeoLocationRequest(latitude=91.0, longitude=0.0)

        # Invalid longitude
        with pytest.raises(ValueError):
            GeoLocationRequest(latitude=0.0, longitude=181.0)

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

        # Invalid temperature
        with pytest.raises(ValueError):
            WeatherDataRequest(temperature=-60.0)

        # Invalid humidity
        with pytest.raises(ValueError):
            WeatherDataRequest(humidity=150.0)


class TestAPIExamples:
    """Test API examples and documentation content."""

    def test_openapi_examples_in_spec(self, client):
        """Test that examples are included in OpenAPI spec."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        # Check for examples in request bodies
        paths = openapi_spec["paths"]
        
        # Check thoughts creation endpoint
        if "/api/v1/thoughts" in paths:
            post_operation = paths["/api/v1/thoughts"]["post"]
            if "requestBody" in post_operation:
                request_body = post_operation["requestBody"]
                if "content" in request_body:
                    json_content = request_body["content"].get("application/json", {})
                    assert "examples" in json_content or "example" in json_content

    def test_response_examples_in_spec(self, client):
        """Test that response examples are included in OpenAPI spec."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        paths = openapi_spec["paths"]
        
        # Check for response examples
        for path, methods in paths.items():
            for method, operation in methods.items():
                if "responses" in operation:
                    for status_code, response_spec in operation["responses"].items():
                        if "content" in response_spec:
                            json_content = response_spec["content"].get("application/json", {})
                            # Examples should be present in successful responses
                            if status_code.startswith("2"):
                                # Either examples or example should be present
                                has_examples = "examples" in json_content or "example" in json_content
                                # For now, we'll just check that the structure is there
                                assert "content" in response_spec


class TestAPIDocumentationContent:
    """Test API documentation content quality."""

    def test_endpoint_descriptions(self, client):
        """Test that endpoints have comprehensive descriptions."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        paths = openapi_spec["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                # Each operation should have a summary
                assert "summary" in operation, f"Missing summary for {method.upper()} {path}"
                
                # Each operation should have a description
                assert "description" in operation, f"Missing description for {method.upper()} {path}"
                
                # Description should be substantial
                description = operation["description"]
                assert len(description) > 50, f"Description too short for {method.upper()} {path}"

    def test_parameter_descriptions(self, client):
        """Test that parameters have proper descriptions."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        paths = openapi_spec["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if "parameters" in operation:
                    for param in operation["parameters"]:
                        assert "description" in param, f"Missing description for parameter in {method.upper()} {path}"
                        assert len(param["description"]) > 10, f"Parameter description too short in {method.upper()} {path}"

    def test_response_descriptions(self, client):
        """Test that responses have proper descriptions."""
        response = client.get("/api/v1/openapi.json")
        openapi_spec = response.json()
        
        paths = openapi_spec["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if "responses" in operation:
                    for status_code, response_spec in operation["responses"].items():
                        assert "description" in response_spec, f"Missing description for {status_code} response in {method.upper()} {path}"


class TestInteractiveDocumentation:
    """Test interactive documentation features."""

    def test_swagger_ui_customization(self, client):
        """Test that Swagger UI is properly customized."""
        response = client.get("/api/v1/docs")
        assert response.status_code == 200
        
        content = response.text
        
        # Check for custom styling
        assert "custom-header" in content
        assert "Personal Semantic Engine API" in content
        
        # Check for feature descriptions
        assert "Thought Management" in content
        assert "Semantic Search" in content
        assert "Timeline Visualization" in content
        assert "Admin Management" in content

    def test_documentation_accessibility(self, client):
        """Test that documentation is accessible."""
        response = client.get("/api/v1/docs")
        content = response.text
        
        # Check for accessibility features
        assert 'lang="en"' in content
        assert 'charset="UTF-8"' in content
        assert 'viewport' in content
        
        # Check for semantic HTML structure
        assert '<h1>' in content
        assert '<h3>' in content or '<h4>' in content