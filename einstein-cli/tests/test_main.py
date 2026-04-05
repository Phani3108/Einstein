"""Tests for main CLI entry point."""

import pytest
from click.testing import CliRunner

from einstein_cli.main import cli


def test_cli_help():
    """Test that CLI shows help message."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Einstein Personal Semantic Engine CLI" in result.output
    assert "auth" in result.output
    assert "config" in result.output
    assert "thoughts" in result.output


def test_version_command():
    """Test version command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])

    assert result.exit_code == 0
    assert "Einstein CLI version" in result.output


def test_version_command_json():
    """Test version command with JSON output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "version"])

    assert result.exit_code == 0
    assert '"version"' in result.output


def test_auth_group_exists():
    """Test that auth command group is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "--help"])

    assert result.exit_code == 0
    assert "Authentication commands" in result.output


def test_config_group_exists():
    """Test that config command group is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])

    assert result.exit_code == 0
    assert "Configuration management commands" in result.output


def test_thoughts_group_exists():
    """Test that thoughts command group is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["thoughts", "--help"])

    assert result.exit_code == 0
    assert "Thought management commands" in result.output
