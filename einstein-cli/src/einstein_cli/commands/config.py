"""Configuration commands for Einstein CLI."""

import click
import json
from typing import Optional

from einstein_cli.config import ConfigManager
from einstein_cli.output import OutputFormatter


@click.group(name="config")
def config_group() -> None:
    """Configuration management commands."""
    pass


@config_group.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value.

    Examples:
        einstein config set api.url http://localhost:8001
        einstein config set output.colors true
        einstein config set cache.enabled false
        einstein config set api.timeout 60
    """
    config: ConfigManager = ctx.obj["config"]
    output: OutputFormatter = ctx.obj["output"]

    try:
        # Try to parse value as JSON for complex types (booleans, numbers, etc.)
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # If not valid JSON, treat as string
            parsed_value = value

        config.set(key, parsed_value)
        output.format_success(f"Configuration updated: {key} = {parsed_value}")

    except ValueError as e:
        output.format_error(f"Invalid configuration: {e}", "Configuration Error")
        ctx.exit(1)
    except Exception as e:
        output.format_error(f"Failed to set configuration: {e}", "Configuration Error")
        ctx.exit(1)


@config_group.command()
@click.argument("key", required=False)
@click.pass_context
def get(ctx: click.Context, key: Optional[str]) -> None:
    """Get a configuration value or show all configuration.

    Examples:
        einstein config get api.url
        einstein config get
    """
    config: ConfigManager = ctx.obj["config"]
    output: OutputFormatter = ctx.obj["output"]

    if key:
        # Get specific key
        value = config.get(key)
        if value is None:
            output.format_error(
                f"Configuration key '{key}' not found", "Configuration Error"
            )
            ctx.exit(1)

        if output.json_mode:
            result = {key: value}
            click.echo(json.dumps(result, indent=2))
        else:
            output.console.print(f"[cyan]{key}[/cyan] = [white]{value}[/white]")
    else:
        # Show all configuration
        all_config = config.show()
        if output.json_mode:
            click.echo(json.dumps(all_config, indent=2))
        else:
            output.console.print("[bold blue]Current Configuration:[/bold blue]\n")
            _print_config_tree(output, all_config)


@config_group.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """Show all configuration values."""
    # Delegate to get command with no key
    ctx.invoke(get, key=None)


@config_group.command()
@click.confirmation_option(
    prompt="Are you sure you want to reset all configuration to defaults?"
)
@click.pass_context
def reset(ctx: click.Context) -> None:
    """Reset configuration to defaults."""
    config: ConfigManager = ctx.obj["config"]
    output: OutputFormatter = ctx.obj["output"]

    try:
        config.reset()
        output.format_success("Configuration reset to defaults")
    except Exception as e:
        output.format_error(
            f"Failed to reset configuration: {e}", "Configuration Error"
        )
        ctx.exit(1)


@config_group.command()
@click.pass_context
def path(ctx: click.Context) -> None:
    """Show the path to the configuration file."""
    config: ConfigManager = ctx.obj["config"]
    output: OutputFormatter = ctx.obj["output"]

    config_path = config.get_config_path()

    if output.json_mode:
        result = {"config_path": str(config_path)}
        click.echo(json.dumps(result, indent=2))
    else:
        output.console.print(f"Configuration file: [cyan]{config_path}[/cyan]")
        if config_path.exists():
            output.console.print("[green]✓[/green] File exists")
        else:
            output.console.print(
                "[yellow]⚠[/yellow] File will be created on first configuration change"
            )


def _print_config_tree(
    output: OutputFormatter, config_dict: dict, prefix: str = ""
) -> None:
    """Recursively print configuration as a tree structure.

    Args:
        output: Output formatter instance
        config_dict: Configuration dictionary to print
        prefix: Current prefix for nested keys
    """
    for key, value in config_dict.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            output.console.print(f"[bold cyan]{full_key}[/bold cyan]:")
            _print_config_tree(output, value, full_key)
        else:
            output.console.print(f"  [cyan]{full_key}[/cyan] = [white]{value}[/white]")
