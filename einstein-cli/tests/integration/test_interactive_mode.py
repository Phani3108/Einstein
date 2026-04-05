#!/usr/bin/env python3
"""Test script for interactive mode functionality."""

import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from einstein_cli.interactive import InteractiveSession
from einstein_cli.config import ConfigManager
from einstein_cli.cached_api import CachedAPIClient
from einstein_cli.output import OutputFormatter
from einstein_cli.auth import AuthManager
from einstein_cli.api import ThoughtData, SearchResult
from rich.console import Console
from datetime import datetime


def test_interactive_session_creation():
    """Test that InteractiveSession can be created successfully."""
    print("Testing InteractiveSession creation...")
    
    # Create mock dependencies
    console = Console()
    config = Mock(spec=ConfigManager)
    cached_api = Mock(spec=CachedAPIClient)
    output = Mock(spec=OutputFormatter)
    auth_manager = Mock(spec=AuthManager)
    
    # Create session
    session = InteractiveSession(config, cached_api, output, auth_manager, console)
    
    # Verify session was created
    assert session is not None
    assert session.config == config
    assert session.cached_api == cached_api
    assert session.output == output
    assert session.auth_manager == auth_manager
    assert session.console == console
    assert session.running is True
    assert len(session.history) == 0
    
    print("✓ InteractiveSession creation test passed")


def test_command_registry():
    """Test that all expected commands are registered."""
    print("Testing command registry...")
    
    # Create mock dependencies
    console = Console()
    config = Mock(spec=ConfigManager)
    cached_api = Mock(spec=CachedAPIClient)
    output = Mock(spec=OutputFormatter)
    auth_manager = Mock(spec=AuthManager)
    
    # Create session
    session = InteractiveSession(config, cached_api, output, auth_manager, console)
    
    # Check that all expected commands are registered
    expected_commands = [
        "add", "search", "list", "show", "delete", "sync", 
        "stats", "config", "help", "history", "clear", "exit", "quit"
    ]
    
    for cmd in expected_commands:
        assert cmd in session.commands, f"Command '{cmd}' not found in registry"
    
    # Check aliases
    assert "h" in session.aliases
    assert "q" in session.aliases
    assert "ls" in session.aliases
    assert "rm" in session.aliases
    assert "?" in session.aliases
    
    print("✓ Command registry test passed")


async def test_command_parsing():
    """Test command parsing functionality."""
    print("Testing command parsing...")
    
    # Create mock dependencies
    console = Console()
    config = Mock(spec=ConfigManager)
    cached_api = Mock(spec=CachedAPIClient)
    output = Mock(spec=OutputFormatter)
    auth_manager = Mock(spec=AuthManager)
    
    # Mock authentication
    auth_manager.is_authenticated.return_value = True
    
    # Mock API responses
    cached_api.create_thought = AsyncMock(return_value={
        "id": "test-123",
        "content": "Test thought",
        "timestamp": datetime.now()
    })
    
    cached_api.search_thoughts = AsyncMock(return_value={
        "results": [],
        "total": 0,
        "query": "test"
    })
    
    # Create session
    session = InteractiveSession(config, cached_api, output, auth_manager, console)
    
    # Test different command formats
    test_cases = [
        ("add test thought", "add", ["test", "thought"]),
        ("add: test thought with colon", "add", ["test thought with colon"]),
        ("search: coffee meetings", "search", ["coffee meetings"]),
        ("list 5", "list", ["5"]),
        ("help", "help", []),
        ("h", "help", []),  # Test alias
        ("exit", "exit", []),
    ]
    
    # Mock the command handlers to avoid actual execution
    for cmd_name in session.commands:
        session.commands[cmd_name] = AsyncMock()
    
    for input_str, expected_cmd, expected_args in test_cases:
        # Reset the mock
        for cmd_name in session.commands:
            session.commands[cmd_name].reset_mock()
        
        # Execute command
        await session._execute_command(input_str)
        
        # Check that the correct command was called
        if expected_cmd in session.commands:
            session.commands[expected_cmd].assert_called_once_with(expected_args)
    
    print("✓ Command parsing test passed")


async def test_add_command():
    """Test the add command functionality."""
    print("Testing add command...")
    
    # Create mock dependencies
    console = Console()
    config = Mock(spec=ConfigManager)
    cached_api = Mock(spec=CachedAPIClient)
    output = Mock(spec=OutputFormatter)
    auth_manager = Mock(spec=AuthManager)
    
    # Mock authentication
    auth_manager.is_authenticated.return_value = True
    
    # Mock API response
    test_thought = {
        "id": "test-123",
        "content": "Test thought content",
        "timestamp": datetime.now()
    }
    cached_api.create_thought = AsyncMock(return_value=test_thought)
    
    # Create session
    session = InteractiveSession(config, cached_api, output, auth_manager, console)
    
    # Test add command
    await session._handle_add(["Test", "thought", "content"])
    
    # Verify API was called
    cached_api.create_thought.assert_called_once_with("Test thought content")
    
    print("✓ Add command test passed")


async def test_search_command():
    """Test the search command functionality."""
    print("Testing search command...")
    
    # Create mock dependencies
    console = Console()
    config = Mock(spec=ConfigManager)
    cached_api = Mock(spec=CachedAPIClient)
    output = Mock(spec=OutputFormatter)
    auth_manager = Mock(spec=AuthManager)
    
    # Mock authentication
    auth_manager.is_authenticated.return_value = True
    
    # Mock API response
    search_results = {
        "results": [
            {
                "id": "test-123",
                "content": "Coffee meeting with team",
                "timestamp": datetime.now(),
                "relevance_score": 0.95
            }
        ],
        "total": 1,
        "query": "coffee"
    }
    cached_api.search_thoughts = AsyncMock(return_value=search_results)
    
    # Create session
    session = InteractiveSession(config, cached_api, output, auth_manager, console)
    
    # Test search command
    await session._handle_search(["coffee", "meetings"])
    
    # Verify API was called
    cached_api.search_thoughts.assert_called_once_with("coffee meetings", limit=5)
    
    # Verify output formatter was called
    output.format_search_results.assert_called_once_with(search_results)
    
    print("✓ Search command test passed")


async def test_authentication_check():
    """Test that commands properly check authentication."""
    print("Testing authentication checks...")
    
    # Create mock dependencies
    console = Console()
    config = Mock(spec=ConfigManager)
    cached_api = Mock(spec=CachedAPIClient)
    output = Mock(spec=OutputFormatter)
    auth_manager = Mock(spec=AuthManager)
    
    # Mock NOT authenticated
    auth_manager.is_authenticated.return_value = False
    
    # Create session
    session = InteractiveSession(config, cached_api, output, auth_manager, console)
    
    # Test commands that require authentication with arguments (to avoid prompts)
    test_cases = [
        ("add", ["test content"]),
        ("search", ["test query"]),
        ("list", []),
        ("show", ["test-id"]),
        ("sync", []),
        ("stats", []),
    ]
    
    for cmd_name, args in test_cases:
        handler = session.commands[cmd_name]
        
        # Mock console.print to capture output
        with patch.object(session.console, 'print') as mock_print:
            await handler(args)
            
            # Check that authentication warning was printed
            mock_print.assert_called()
            call_args = mock_print.call_args[0][0]
            assert "login first" in call_args.lower()
    
    # Test delete command separately since it has different flow
    with patch.object(session.console, 'print') as mock_print:
        with patch('einstein_cli.interactive.Prompt.ask', return_value='y'):
            await session._handle_delete(["test-id"])
        
        # Should have multiple print calls, find the auth one
        auth_message_found = False
        for call in mock_print.call_args_list:
            call_args = call[0][0]
            if "login first" in call_args.lower():
                auth_message_found = True
                break
        assert auth_message_found, "Authentication message not found in delete command output"
    
    print("✓ Authentication check test passed")


def test_cli_integration():
    """Test that interactive command is properly integrated with main CLI."""
    print("Testing CLI integration...")
    
    # Import the main CLI
    from einstein_cli.main import cli
    
    # Check that interactive command is registered
    assert "interactive" in [cmd.name for cmd in cli.commands.values()]
    
    print("✓ CLI integration test passed")


async def main():
    """Run all tests."""
    print("🧪 Testing Einstein CLI Interactive Mode\n")
    
    try:
        # Run tests
        test_interactive_session_creation()
        test_command_registry()
        await test_command_parsing()
        await test_add_command()
        await test_search_command()
        await test_authentication_check()
        test_cli_integration()
        
        print("\n✅ All interactive mode tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)