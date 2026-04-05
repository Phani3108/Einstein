#!/usr/bin/env python3
"""
Integration test script for Einstein CLI against a running server.

This script demonstrates how to test the CLI against an actual Einstein server.
Make sure you have a Einstein server running on localhost:8001 before running this script.

Usage:
    python test_cli_integration.py

Requirements:
    - Einstein server running on http://localhost:8001
    - Valid user account (test@example.com / password123)
"""

import subprocess
import sys
import json
from typing import List, Dict, Any


class CLITester:
    """Helper class for testing CLI commands."""
    
    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
        self.base_cmd = ["poetry", "run", "einstein", "--api-url", api_url]
    
    def run_command(self, args: List[str], input_data: str = None) -> Dict[str, Any]:
        """Run a CLI command and return the result."""
        cmd = self.base_cmd + args
        
        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def test_server_connectivity(self) -> bool:
        """Test if the server is reachable."""
        print(f"🔍 Testing connectivity to {self.api_url}...")
        
        # Try to get auth status (should work even without authentication)
        result = self.run_command(["auth", "status"])
        
        if result["success"]:
            print("✅ Server is reachable")
            return True
        else:
            print(f"❌ Server not reachable: {result['stderr']}")
            return False
    
    def test_authentication(self, email: str, password: str) -> bool:
        """Test authentication flow."""
        print(f"🔐 Testing authentication for {email}...")
        
        # Test login
        login_input = f"{email}\n{password}\n"
        result = self.run_command(["auth", "login"], login_input)
        
        if result["success"]:
            print("✅ Login successful")
            
            # Test auth status
            status_result = self.run_command(["auth", "status"])
            if status_result["success"] and "Authenticated" in status_result["stdout"]:
                print("✅ Authentication status confirmed")
                return True
            else:
                print("❌ Authentication status check failed")
                return False
        else:
            print(f"❌ Login failed: {result['stderr']}")
            return False
    
    def test_thought_operations(self) -> bool:
        """Test thought CRUD operations."""
        print("💭 Testing thought operations...")
        
        # Test adding a thought
        test_content = "This is a test thought from CLI integration test"
        result = self.run_command([
            "thoughts", "add", test_content,
            "--mood", "excited",
            "--tags", "test,cli",
            "--meta", "source=integration_test"
        ])
        
        if not result["success"]:
            print(f"❌ Failed to add thought: {result['stderr']}")
            return False
        
        print("✅ Thought added successfully")
        
        # Extract thought ID from output (assuming it's in the format "Thought created with ID: abc123")
        thought_id = None
        if "Thought created with ID:" in result["stdout"]:
            thought_id = result["stdout"].split("Thought created with ID:")[1].strip().split()[0]
        
        # Test listing thoughts
        list_result = self.run_command(["thoughts", "list", "--limit", "5"])
        if list_result["success"]:
            print("✅ Thought list retrieved successfully")
        else:
            print(f"❌ Failed to list thoughts: {list_result['stderr']}")
            return False
        
        # Test showing specific thought (if we got an ID)
        if thought_id:
            show_result = self.run_command(["thoughts", "show", thought_id])
            if show_result["success"]:
                print(f"✅ Thought {thought_id} retrieved successfully")
            else:
                print(f"❌ Failed to show thought {thought_id}: {show_result['stderr']}")
        
        return True
    
    def test_json_output(self) -> bool:
        """Test JSON output mode."""
        print("📄 Testing JSON output mode...")
        
        # Test JSON auth status
        result = self.run_command(["--json", "auth", "status"])
        if result["success"]:
            try:
                json.loads(result["stdout"])
                print("✅ JSON auth status works")
            except json.JSONDecodeError:
                print("❌ Invalid JSON in auth status output")
                return False
        else:
            print(f"❌ JSON auth status failed: {result['stderr']}")
            return False
        
        # Test JSON version
        version_result = self.run_command(["--json", "version"])
        if version_result["success"]:
            try:
                version_data = json.loads(version_result["stdout"])
                if "version" in version_data:
                    print(f"✅ JSON version works: {version_data['version']}")
                else:
                    print("❌ Version data missing from JSON output")
                    return False
            except json.JSONDecodeError:
                print("❌ Invalid JSON in version output")
                return False
        else:
            print(f"❌ JSON version failed: {version_result['stderr']}")
            return False
        
        return True
    
    def test_logout(self) -> bool:
        """Test logout functionality."""
        print("🚪 Testing logout...")
        
        result = self.run_command(["auth", "logout"])
        if result["success"]:
            print("✅ Logout successful")
            
            # Verify we're no longer authenticated
            status_result = self.run_command(["auth", "status"])
            if "Not authenticated" in status_result["stdout"]:
                print("✅ Logout confirmed")
                return True
            else:
                print("❌ Still appears to be authenticated after logout")
                return False
        else:
            print(f"❌ Logout failed: {result['stderr']}")
            return False


def main():
    """Run the integration tests."""
    print("🚀 Starting Einstein CLI Integration Tests")
    print("=" * 50)
    
    # Configuration
    api_url = "http://localhost:8001"
    test_email = "test@example.com"
    test_password = "password123"
    
    tester = CLITester(api_url)
    
    # Run tests
    tests = [
        ("Server Connectivity", tester.test_server_connectivity),
        ("JSON Output", tester.test_json_output),
        ("Authentication", lambda: tester.test_authentication(test_email, test_password)),
        ("Thought Operations", tester.test_thought_operations),
        ("Logout", tester.test_logout),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! CLI is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()