"""Main CLI entry point using Click framework."""

import click
from rich.console import Console
from typing import Optional

from einstein_cli.config import ConfigManager
from einstein_cli.api import APIClient
from einstein_cli.auth import AuthManager
from einstein_cli.output import OutputFormatter
from einstein_cli.cache import LocalCache
from einstein_cli.cached_api import CachedAPIClient
from einstein_cli.commands.auth import auth_group
from einstein_cli.commands.config import config_group
from einstein_cli.commands.thoughts import thoughts_group
from einstein_cli.commands.search import search_command
from einstein_cli.commands.sync import sync_group
from einstein_cli.commands.help import help_group
from einstein_cli.interactive import interactive


@click.group(invoke_without_command=True)
@click.option(
    "--config", 
    help="Path to custom configuration file (default: platform-specific location)",
    metavar="PATH"
)
@click.option(
    "--api-url", 
    help="Override API server URL from configuration",
    metavar="URL"
)
@click.option(
    "--json", "json_output", 
    is_flag=True, 
    help="Output results in JSON format for scripting"
)
@click.option(
    "--verbose", "-v", 
    is_flag=True, 
    help="Enable verbose output for debugging"
)
@click.option(
    "--no-interactive", 
    is_flag=True, 
    help="Disable automatic interactive mode when no command is given"
)
@click.pass_context
def cli(
    ctx: click.Context,
    config: Optional[str],
    api_url: Optional[str],
    json_output: bool,
    verbose: bool,
    no_interactive: bool,
) -> None:
    """Einstein Personal Semantic Engine CLI

    A powerful command-line interface for managing your thoughts, performing 
    semantic searches, and analyzing your personal knowledge base.

    \b
    QUICK START:
      einstein                          # Start interactive mode
      einstein auth login               # Login to your server
      einstein thoughts add "content"   # Add a new thought
      einstein search "query"           # Search your thoughts
      einstein thoughts list            # List recent thoughts

    \b
    MODES:
      Interactive Mode: Run 'einstein' without commands for a conversational
                       experience with command completion and help.
      
      CLI Mode:        Use specific commands for scripting and automation.

    \b
    EXAMPLES:
      # First-time setup
      einstein config set api.url http://localhost:8001
      einstein auth login
      
      # Daily usage
      einstein thoughts add "Had a great meeting today"
      einstein search "coffee meetings" --limit 10
      einstein thoughts list --mood excited
      
      # Scripting with JSON output
      einstein --json search "AI projects" | jq '.results[].content'

    Use 'einstein COMMAND --help' for detailed help on any command.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Initialize core components
    console = Console()
    config_manager = ConfigManager(config)
    auth_manager = AuthManager(config_manager.config_dir)

    # Use provided API URL or fall back to config
    effective_api_url = api_url or config_manager.get(
        "api.url", "http://localhost:8001"
    )
    api_client = APIClient(effective_api_url, auth_manager)

    # Initialize cache (always enabled for offline support)
    cache = LocalCache(config_manager.config_dir / "cache")
    cached_api = CachedAPIClient(api_client, cache, config_manager)

    output_formatter = OutputFormatter(console, json_output)

    # Store in context for subcommands
    ctx.obj["config"] = config_manager
    ctx.obj["api_client"] = api_client
    ctx.obj["cached_api"] = cached_api
    ctx.obj["cache"] = cache
    ctx.obj["auth_manager"] = auth_manager
    ctx.obj["output"] = output_formatter
    ctx.obj["console"] = console
    ctx.obj["verbose"] = verbose
    
    # Auto-start interactive mode if no subcommand and conditions are met
    if ctx.invoked_subcommand is None:
        # Check if we should auto-start interactive mode
        import sys
        import os
        
        # Check user's preference from config
        auto_interactive_config = config_manager.get("ui.auto_interactive", True)
        
        should_start_interactive = (
            not no_interactive and  # User didn't disable it with flag
            auto_interactive_config and  # User didn't disable it in config
            sys.stdin.isatty() and  # Running in a terminal (not piped)
            sys.stdout.isatty() and  # Output goes to terminal (not redirected)
            not json_output and  # Not requesting JSON output
            "CI" not in os.environ and  # Not running in CI
            "EINSTEIN_NO_INTERACTIVE" not in os.environ  # Environment override
        )
        
        if should_start_interactive:
            # Show a brief hint and start interactive mode
            console.print("[dim]💡 Starting interactive mode. Use --help to see all commands or --no-interactive to disable.[/dim]\n")
            
            # Import and start interactive session
            from einstein_cli.interactive import InteractiveSession
            session = InteractiveSession(config_manager, cached_api, output_formatter, auth_manager, console)
            session.start()
        else:
            # Show help when no command is provided in non-interactive context
            console.print(ctx.get_help())


# Register command groups
cli.add_command(auth_group)
cli.add_command(config_group)
cli.add_command(thoughts_group)
cli.add_command(search_command, name="search")
cli.add_command(sync_group, name="sync")
cli.add_command(help_group)
cli.add_command(interactive)


@cli.command()
@click.option("--detailed", is_flag=True, help="Show detailed version and system information")
@click.pass_context
def version(ctx: click.Context, detailed: bool) -> None:
    """Show version information.
    
    \b
    EXAMPLES:
      einstein version              # Show version number
      einstein version --detailed   # Show detailed system info
      einstein --json version       # JSON format for scripts
    """
    from einstein_cli import __version__
    import sys
    import platform

    output = ctx.obj["output"]
    
    if output.json_mode:
        version_info = {"version": __version__}
        if detailed:
            version_info.update({
                "python_version": sys.version,
                "platform": platform.platform(),
                "architecture": platform.architecture()[0],
                "system": platform.system(),
            })
        click.echo(click.get_text_stream("stdout").write(str(version_info)))
    else:
        output.console.print(f"[bold blue]Einstein CLI[/bold blue] version [green]{__version__}[/green]")
        
        if detailed:
            output.console.print()
            output.console.print("[bold]System Information:[/bold]")
            output.console.print(f"  Python: {sys.version.split()[0]}")
            output.console.print(f"  Platform: {platform.platform()}")
            output.console.print(f"  Architecture: {platform.architecture()[0]}")
            output.console.print(f"  System: {platform.system()}")
            
            # Show configuration location
            config_path = ctx.obj["config"].get_config_path()
            output.console.print(f"  Config: {config_path}")
            
            # Show API connection status
            try:
                auth_manager = ctx.obj["auth_manager"]
                if auth_manager.is_authenticated():
                    api_url = ctx.obj["config"].get("api.url", "http://localhost:8001")
                    output.console.print(f"  API: {api_url} [green](authenticated)[/green]")
                else:
                    output.console.print(f"  API: [yellow](not authenticated)[/yellow]")
            except Exception:
                output.console.print(f"  API: [red](connection error)[/red]")


if __name__ == "__main__":
    cli()
