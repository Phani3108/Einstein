#!/usr/bin/env python3
"""
Verification script for API documentation and OpenAPI specification implementation.

This script verifies that task 14 has been completed successfully by checking:
1. API documentation components are properly implemented
2. OpenAPI specification is comprehensive
3. Request/response validation is working
4. API versioning is implemented
5. Interactive documentation is available
"""

import sys
import traceback
from typing import Dict, Any, List


def test_documentation_components():
    """Test that documentation components are properly implemented."""
    print("Testing documentation components...")
    
    try:
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
        
        # Test examples structure
        examples = get_openapi_examples()
        assert isinstance(examples, dict)
        assert "thoughts" in examples
        assert "search" in examples
        assert "timeline" in examples
        assert "admin" in examples
        
        # Test security schemes
        security = get_security_schemes()
        assert "BearerAuth" in security
        assert security["BearerAuth"]["type"] == "http"
        assert security["BearerAuth"]["scheme"] == "bearer"
        
        # Test common parameters
        params = get_common_parameters()
        assert "PaginationSkip" in params
        assert "PaginationLimit" in params
        
        print("✅ Documentation components are properly implemented")
        return True
        
    except Exception as e:
        print(f"❌ Documentation components test failed: {e}")
        traceback.print_exc()
        return False


def test_api_versioning():
    """Test that API versioning is properly implemented."""
    print("Testing API versioning...")
    
    try:
        from src.api.versioning import (
            APIVersion,
            VersionInfo,
            get_api_version_header,
            validate_api_version,
            APIVersioningStrategy
        )
        
        # Test version enum
        assert APIVersion.V1 == "v1"
        
        # Test version info
        assert VersionInfo.CURRENT_VERSION == APIVersion.V1
        assert VersionInfo.is_supported(APIVersion.V1)
        
        # Test version headers
        headers = get_api_version_header()
        assert "X-API-Version" in headers
        assert headers["X-API-Version"] == "v1"
        
        # Test version validation
        assert validate_api_version("v1") is True
        assert validate_api_version("invalid") is False
        
        # Test path extraction
        assert APIVersioningStrategy.get_version_from_path("/api/v1/thoughts") == "v1"
        
        print("✅ API versioning is properly implemented")
        return True
        
    except Exception as e:
        print(f"❌ API versioning test failed: {e}")
        traceback.print_exc()
        return False


def test_request_response_validation():
    """Test that request/response validation is working."""
    print("Testing request/response validation...")
    
    try:
        from src.api.models.thought_models import CreateThoughtRequest, GeoLocationRequest, WeatherDataRequest
        from pydantic import ValidationError
        
        # Test valid thought request
        valid_request = CreateThoughtRequest(
            content="This is a valid thought content."
        )
        assert valid_request.content == "This is a valid thought content."
        
        # Test invalid content (should raise ValidationError)
        try:
            CreateThoughtRequest(content="")
            assert False, "Should have raised ValidationError for empty content"
        except ValidationError:
            pass  # Expected
        
        # Test valid location
        valid_location = GeoLocationRequest(
            latitude=40.7128,
            longitude=-74.0060,
            name="New York City"
        )
        assert valid_location.latitude == 40.7128
        
        # Test invalid latitude (should raise ValidationError)
        try:
            GeoLocationRequest(latitude=91.0, longitude=0.0)
            assert False, "Should have raised ValidationError for invalid latitude"
        except ValidationError:
            pass  # Expected
        
        # Test valid weather
        valid_weather = WeatherDataRequest(
            temperature=22.5,
            condition="sunny",
            humidity=65.0
        )
        assert valid_weather.temperature == 22.5
        
        print("✅ Request/response validation is working properly")
        return True
        
    except Exception as e:
        print(f"❌ Request/response validation test failed: {e}")
        traceback.print_exc()
        return False


def test_enhanced_api_routes():
    """Test that API routes have been enhanced with comprehensive documentation."""
    print("Testing enhanced API routes...")
    
    try:
        # Import route modules to check they exist and are properly structured
        from src.api.routes import thoughts, search, timeline, admin
        
        # Check that documentation examples are imported
        assert hasattr(thoughts, 'THOUGHTS_EXAMPLES')
        assert hasattr(search, 'SEARCH_EXAMPLES')
        assert hasattr(timeline, 'TIMELINE_EXAMPLES')
        assert hasattr(admin, 'ADMIN_EXAMPLES')
        
        print("✅ API routes are enhanced with comprehensive documentation")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced API routes test failed: {e}")
        traceback.print_exc()
        return False


def test_interactive_documentation():
    """Test that interactive documentation components exist."""
    print("Testing interactive documentation...")
    
    try:
        import os
        
        # Check that custom docs template exists
        docs_template_path = "src/api/templates/docs.html"
        assert os.path.exists(docs_template_path), f"Custom docs template not found at {docs_template_path}"
        
        # Check template content
        with open(docs_template_path, 'r') as f:
            content = f.read()
            assert "Personal Semantic Engine API" in content
            assert "swagger-ui" in content
            assert "custom-header" in content
        
        # Check that versioning middleware exists
        versioning_middleware_path = "src/infrastructure/middleware/versioning_middleware.py"
        assert os.path.exists(versioning_middleware_path), f"Versioning middleware not found at {versioning_middleware_path}"
        
        print("✅ Interactive documentation components are properly implemented")
        return True
        
    except Exception as e:
        print(f"❌ Interactive documentation test failed: {e}")
        traceback.print_exc()
        return False


def test_openapi_specification_quality():
    """Test the quality and completeness of OpenAPI specification components."""
    print("Testing OpenAPI specification quality...")
    
    try:
        from src.api.documentation import THOUGHTS_EXAMPLES, SEARCH_EXAMPLES, COMMON_ERROR_EXAMPLES
        
        # Test thought examples completeness
        thought_example = THOUGHTS_EXAMPLES["create_thought_request"]["value"]
        assert len(thought_example["content"]) > 50, "Thought example content should be substantial"
        assert "metadata" in thought_example
        assert "location" in thought_example["metadata"]
        assert "weather" in thought_example["metadata"]
        
        # Test search examples completeness
        search_example = SEARCH_EXAMPLES["search_request"]["value"]
        assert len(search_example["query_text"]) > 10, "Search query should be meaningful"
        assert "entity_filter" in search_example
        assert "date_range" in search_example
        
        # Test error examples consistency
        for status_code, error_spec in COMMON_ERROR_EXAMPLES.items():
            assert "description" in error_spec
            assert "content" in error_spec
            assert "application/json" in error_spec["content"]
            
            example = error_spec["content"]["application/json"]["example"]
            assert "error" in example
            assert "timestamp" in example
        
        print("✅ OpenAPI specification quality is high")
        return True
        
    except Exception as e:
        print(f"❌ OpenAPI specification quality test failed: {e}")
        traceback.print_exc()
        return False


def run_all_tests() -> bool:
    """Run all verification tests."""
    print("🚀 Starting API Documentation Implementation Verification")
    print("=" * 60)
    
    tests = [
        test_documentation_components,
        test_api_versioning,
        test_request_response_validation,
        test_enhanced_api_routes,
        test_interactive_documentation,
        test_openapi_specification_quality,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            traceback.print_exc()
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Task 14 implementation is complete.")
        print("\n✅ API Documentation and OpenAPI Specification Features:")
        print("   • Comprehensive OpenAPI/Swagger documentation")
        print("   • Detailed API examples with realistic data")
        print("   • Request/response schema validation")
        print("   • API versioning strategy implementation")
        print("   • Interactive documentation interface")
        print("   • Security schemes and common parameters")
        print("   • Enhanced endpoint descriptions")
        print("   • Error handling documentation")
        print("   • Custom Swagger UI with branding")
        print("   • Version headers middleware")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)