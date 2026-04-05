#!/usr/bin/env python3
"""Test the sync command functionality."""

import sys
sys.path.insert(0, 'src')

import tempfile
from pathlib import Path
from click.testing import CliRunner

from einstein_cli.main import cli


def test_sync_command():
    """Test the sync command."""
    print("🧪 Testing sync command...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        runner = CliRunner()
        
        # Test sync mode command
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'sync', 'mode'
        ])
        
        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.output}")
        
        # Should show current mode (online by default)
        assert result.exit_code == 0
        assert "online" in result.output.lower()
        
        # Test cache stats
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'sync', 'cache'
        ])
        
        print(f"Cache command exit code: {result.exit_code}")
        print(f"Cache output: {result.output}")
        
        # Should show cache statistics
        assert result.exit_code == 0
        assert "Cache Statistics" in result.output
        
        print("✅ Sync command working")


def test_offline_mode_switch():
    """Test switching to offline mode."""
    print("🧪 Testing offline mode switch...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        runner = CliRunner()
        
        # Switch to offline mode
        result = runner.invoke(cli, [
            '--config', str(config_dir / "config.toml"),
            'sync', 'mode', '--offline'
        ])
        
        print(f"Offline switch exit code: {result.exit_code}")
        print(f"Offline switch output: {result.output}")
        
        assert result.exit_code == 0
        assert "offline" in result.output.lower()
        
        print("✅ Offline mode switch working")


if __name__ == "__main__":
    try:
        test_sync_command()
        test_offline_mode_switch()
        print("\n🎉 All sync command tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)