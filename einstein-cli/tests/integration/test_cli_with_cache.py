#!/usr/bin/env python3
"""Test CLI commands with caching functionality."""

import sys
sys.path.insert(0, 'src')

import tempfile
import json
from pathlib import Path
from click.testing import CliRunner

from einstein_cli.main import cli


def test_offline_thought_creation():
    """Test creating thoughts in offline mode."""
    print("🧪 Testing offline thought creation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        runner = CliRunner()
        
        # Switch to offline mode first
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'sync', 'mode', '--offline'
        ])
        assert result.exit_code == 0
        
        # Create a thought in offline mode
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'thoughts', 'add', 'This is an offline thought'
        ])
        
        print(f"Add thought exit code: {result.exit_code}")
        print(f"Add thought output: {result.output}")
        
        # Should succeed even without authentication in offline mode
        assert result.exit_code == 0
        assert "Thought created" in result.output
        assert "offline" in result.output.lower()
        
        # Check cache stats - should have 1 pending operation
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'sync', 'cache'
        ])
        
        assert result.exit_code == 0
        assert "Pending Operations" in result.output
        # Should show 1 pending operation
        
        print("✅ Offline thought creation working")


def test_cached_thought_listing():
    """Test listing cached thoughts."""
    print("🧪 Testing cached thought listing...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        runner = CliRunner()
        
        # Switch to offline mode
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'sync', 'mode', '--offline'
        ])
        assert result.exit_code == 0
        
        # Create a few thoughts
        for i in range(3):
            result = runner.invoke(cli, [
                '--config', str(config_dir / "config.toml"),
                'thoughts', 'add', f'Offline thought {i+1}'
            ])
            assert result.exit_code == 0
        
        # List thoughts - should show cached thoughts
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'thoughts', 'list'
        ])
        
        print(f"List thoughts exit code: {result.exit_code}")
        print(f"List thoughts output: {result.output}")
        
        assert result.exit_code == 0
        assert "Cached" in result.output  # Should indicate cached results
        
        print("✅ Cached thought listing working")


def test_offline_search():
    """Test searching in offline mode."""
    print("🧪 Testing offline search...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        runner = CliRunner()
        
        # Switch to offline mode
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'sync', 'mode', '--offline'
        ])
        assert result.exit_code == 0
        
        # Create some thoughts with searchable content
        thoughts = [
            "I love coffee in the morning",
            "Working on machine learning project",
            "Coffee break with the team"
        ]
        
        for thought in thoughts:
            result = runner.invoke(cli, [
                '--config', str(config_dir / "config.toml"),
                'thoughts', 'add', thought
            ])
            assert result.exit_code == 0
        
        # Search for "coffee" - should find cached thoughts
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'search', 'coffee'
        ])
        
        print(f"Search exit code: {result.exit_code}")
        print(f"Search output: {result.output}")
        
        assert result.exit_code == 0
        assert "offline" in result.output.lower() or "cached" in result.output.lower()
        
        print("✅ Offline search working")


def test_json_output_with_cache():
    """Test JSON output works with caching."""
    print("🧪 Testing JSON output with cache...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        runner = CliRunner()
        
        # Switch to offline mode
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'sync', 'mode', '--offline'
        ])
        assert result.exit_code == 0
        
        # Create a thought
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'thoughts', 'add', 'Test thought for JSON'
        ])
        assert result.exit_code == 0
        
        # List thoughts with JSON output
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            '--json',
            'thoughts', 'list'
        ])
        
        print(f"JSON list exit code: {result.exit_code}")
        print(f"JSON list output: {result.output}")
        
        assert result.exit_code == 0
        
        # Should be valid JSON
        try:
            json.loads(result.output)
            print("✅ JSON output valid")
        except json.JSONDecodeError:
            print("❌ Invalid JSON output")
            raise
        
        print("✅ JSON output with cache working")


if __name__ == "__main__":
    try:
        test_offline_thought_creation()
        test_cached_thought_listing()
        test_offline_search()
        test_json_output_with_cache()
        print("\n🎉 All CLI cache tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)