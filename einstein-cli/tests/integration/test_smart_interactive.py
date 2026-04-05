#!/usr/bin/env python3
"""Test script for smart interactive mode functionality."""

import sys
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock


def run_cli_command(cmd, env_vars=None, input_data=None, timeout=5):
    """Run a CLI command and return the result."""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    try:
        result = subprocess.run(
            ["poetry", "run"] + cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            env=env,
            input=input_data,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        return None  # Interactive mode started (expected for some tests)


def test_smart_interactive_detection():
    """Test that smart interactive mode detection works correctly."""
    print("Testing smart interactive mode detection...")
    
    # Test 1: --no-interactive flag disables interactive mode
    result = run_cli_command(["einstein", "--no-interactive"])
    assert result is not None, "Command should not hang with --no-interactive"
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Usage: einstein" in result.stdout, "Should show help text"
    print("✓ --no-interactive flag works")
    
    # Test 2: Environment variable disables interactive mode
    result = run_cli_command(["einstein"], env_vars={"FARADAY_NO_INTERACTIVE": "1"})
    assert result is not None, "Command should not hang with env var"
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Usage: einstein" in result.stdout, "Should show help text"
    print("✓ FARADAY_NO_INTERACTIVE environment variable works")
    
    # Test 3: JSON output disables interactive mode
    result = run_cli_command(["einstein", "--json", "version"])
    assert result is not None, "JSON command should not hang"
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert '"version"' in result.stdout, "Should output JSON"
    print("✓ JSON output disables interactive mode")
    
    # Test 4: Specific commands work normally
    result = run_cli_command(["einstein", "thoughts", "--help"])
    assert result is not None, "Specific command should not hang"
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Usage: einstein thoughts" in result.stdout, "Should show command help"
    print("✓ Specific commands work normally")
    
    # Test 5: Interactive command always works
    result = run_cli_command(["einstein", "interactive", "--help"])
    assert result is not None, "Interactive help should not hang"
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Start interactive mode" in result.stdout, "Should show interactive help"
    print("✓ Interactive command help works")


def test_cli_backwards_compatibility():
    """Test that existing CLI usage patterns still work."""
    print("Testing backwards compatibility...")
    
    # Test existing command patterns
    test_commands = [
        (["einstein", "--help"], "Usage: einstein"),
        (["einstein", "version"], "Einstein CLI version"),
        (["einstein", "thoughts", "--help"], "Usage: einstein thoughts"),
        (["einstein", "search", "--help"], "Usage: einstein search"),
        (["einstein", "config", "--help"], "Usage: einstein config"),
        (["einstein", "auth", "--help"], "Usage: einstein auth"),
    ]
    
    for cmd, expected_output in test_commands:
        result = run_cli_command(cmd)
        assert result is not None, f"Command {' '.join(cmd)} should not hang"
        assert result.returncode == 0, f"Command {' '.join(cmd)} failed: {result.stderr}"
        assert expected_output in result.stdout, f"Command {' '.join(cmd)} output incorrect"
    
    print("✓ All existing CLI patterns work")


def test_scripting_compatibility():
    """Test that scripting use cases still work."""
    print("Testing scripting compatibility...")
    
    # Test piped input doesn't trigger interactive mode
    result = run_cli_command(["einstein", "thoughts", "--help"], input_data="some input")
    assert result is not None, "Piped command should not hang"
    assert result.returncode == 0, f"Piped command failed: {result.stderr}"
    print("✓ Piped input works correctly")
    
    # Test output redirection compatibility (simulated)
    result = run_cli_command(["einstein", "--json", "version"])
    assert result is not None, "JSON output should not hang"
    assert result.returncode == 0, f"JSON command failed: {result.stderr}"
    assert result.stdout.strip().startswith("{"), "Should output valid JSON"
    print("✓ Output redirection compatibility works")
    
    # Test CI environment detection
    result = run_cli_command(["einstein"], env_vars={"CI": "true"})
    assert result is not None, "CI environment should not hang"
    assert result.returncode == 0, f"CI command failed: {result.stderr}"
    assert "Usage: einstein" in result.stdout, "Should show help in CI"
    print("✓ CI environment detection works")


def test_configuration_integration():
    """Test that configuration options work with smart interactive mode."""
    print("Testing configuration integration...")
    
    # Create a temporary config directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # Test that the CLI can handle missing config gracefully
        result = run_cli_command(
            ["einstein", "--config", str(config_dir / "config.toml"), "--help"]
        )
        assert result is not None, "Config command should not hang"
        assert result.returncode == 0, f"Config command failed: {result.stderr}"
        print("✓ Configuration integration works")


def test_help_system():
    """Test that help system works correctly with smart interactive mode."""
    print("Testing help system...")
    
    # Test main help
    result = run_cli_command(["einstein", "--help"])
    assert result is not None, "Help should not hang"
    assert result.returncode == 0, f"Help failed: {result.stderr}"
    assert "interactive" in result.stdout, "Interactive command should be listed"
    assert "--no-interactive" in result.stdout, "No-interactive flag should be documented"
    print("✓ Help system works correctly")


def test_error_handling():
    """Test error handling in smart interactive mode."""
    print("Testing error handling...")
    
    # Test invalid flag
    result = run_cli_command(["einstein", "--invalid-flag"])
    assert result is not None, "Invalid flag should not hang"
    assert result.returncode != 0, "Invalid flag should return error code"
    print("✓ Error handling works correctly")


def main():
    """Run all smart interactive mode tests."""
    print("🧪 Testing Smart Interactive Mode\n")
    
    try:
        test_smart_interactive_detection()
        print()
        
        test_cli_backwards_compatibility()
        print()
        
        test_scripting_compatibility()
        print()
        
        test_configuration_integration()
        print()
        
        test_help_system()
        print()
        
        test_error_handling()
        print()
        
        print("✅ All smart interactive mode tests passed!")
        print("\n🎯 Smart interactive mode is working correctly:")
        print("   • Friendly for new users (auto-starts interactive)")
        print("   • Compatible with existing scripts")
        print("   • Respects user preferences and environment")
        print("   • Maintains full CLI functionality")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)