"""Thought management commands for Einstein CLI."""

import click
import asyncio
from typing import Optional, List

from einstein_cli.api import APIClient, APIError, AuthenticationError, NetworkError
from einstein_cli.cached_api import CachedAPIClient
from einstein_cli.auth import AuthManager
from einstein_cli.output import OutputFormatter


@click.group(name="thoughts", invoke_without_command=True)
@click.pass_context
def thoughts_group(ctx: click.Context) -> None:
    """Thought management commands."""
    if ctx.invoked_subcommand is None:
        # If no subcommand, show help
        click.echo(ctx.get_help())


@thoughts_group.command()
@click.argument("content")
@click.option("--mood", help="Mood associated with the thought")
@click.option("--tags", help="Comma-separated tags")
@click.option("--meta", multiple=True, help="Metadata in key=value format")
@click.pass_context
def add(
    ctx: click.Context,
    content: str,
    mood: Optional[str],
    tags: Optional[str],
    meta: List[str],
) -> None:
    """Add a new thought.

    Examples:
        einstein thoughts add "Had a great meeting today"
        einstein thoughts add "Working on AI project" --mood excited --tags work,ai
        einstein thoughts add "Coffee break" --meta location=office --meta duration=15min
    """
    # Use cached API client if available, otherwise fall back to regular API client
    cached_api: Optional[CachedAPIClient] = ctx.obj.get("cached_api")
    api_client: APIClient = ctx.obj["api_client"]
    auth_manager: AuthManager = ctx.obj["auth_manager"]
    output: OutputFormatter = ctx.obj["output"]

    # Check authentication (skip for offline mode)
    if cached_api and cached_api.is_offline:
        # In offline mode, we can create thoughts without authentication
        pass
    elif not auth_manager.is_authenticated():
        output.format_error(
            "You must be logged in to add thoughts. Run 'einstein auth login'",
            "Authentication Error",
        )
        ctx.exit(1)

    # Build metadata
    metadata = {}

    if mood:
        metadata["mood"] = mood

    if tags:
        metadata["tags"] = [tag.strip() for tag in tags.split(",")]

    # Parse additional metadata from --meta options
    for meta_item in meta:
        if "=" in meta_item:
            key, value = meta_item.split("=", 1)
            metadata[key.strip()] = value.strip()
        else:
            output.format_error(
                f"Invalid metadata format: {meta_item}. Use key=value format.",
                "Validation Error",
            )
            ctx.exit(1)

    async def do_add():
        try:
            # Use cached API client if available
            client = cached_api if cached_api else api_client
            
            if cached_api:
                # Cached API client doesn't need context manager
                thought = await client.create_thought(
                    content, metadata if metadata else None
                )
            else:
                # Regular API client needs context manager
                async with api_client:
                    thought = await api_client.create_thought(
                        content, metadata if metadata else None
                    )
            
            output.format_success(f"Thought created with ID: {thought.id}")
            
            # Show offline indicator if in offline mode
            if cached_api and cached_api.is_offline:
                output.console.print("📴 Created offline - will sync when online", style="yellow")

            if not output.json_mode:
                output.console.print()
                output.format_thought(thought)

        except AuthenticationError as e:
            output.format_error(str(e), "Authentication Error")
            ctx.exit(1)
        except NetworkError as e:
            if cached_api:
                output.format_error(f"{e} - Switched to offline mode", "Network Error")
            else:
                output.format_error(str(e), "Network Error")
                ctx.exit(1)
        except APIError as e:
            output.format_error(str(e), "API Error")
            ctx.exit(1)
        except Exception as e:
            output.format_error(f"Unexpected error: {e}", "Error")
            ctx.exit(1)

    asyncio.run(do_add())


@thoughts_group.command()
@click.option("--limit", default=20, help="Maximum number of thoughts to show")
@click.option("--mood", help="Filter by mood")
@click.option("--tags", help="Filter by tags (comma-separated)")
@click.pass_context
def list(
    ctx: click.Context, limit: int, mood: Optional[str], tags: Optional[str]
) -> None:
    """List recent thoughts.

    Examples:
        einstein thoughts list
        einstein thoughts list --limit 10
        einstein thoughts list --mood happy
        einstein thoughts list --tags work,meeting
    """
    # Use cached API client if available, otherwise fall back to regular API client
    cached_api: Optional[CachedAPIClient] = ctx.obj.get("cached_api")
    api_client: APIClient = ctx.obj["api_client"]
    auth_manager: AuthManager = ctx.obj["auth_manager"]
    output: OutputFormatter = ctx.obj["output"]

    # Check authentication (skip for offline mode)
    if cached_api and cached_api.is_offline:
        # In offline mode, we can list cached thoughts without authentication
        pass
    elif not auth_manager.is_authenticated():
        output.format_error(
            "You must be logged in to list thoughts. Run 'einstein auth login'",
            "Authentication Error",
        )
        ctx.exit(1)

    # Build filters
    filters = {}
    if mood:
        filters["mood"] = mood
    if tags:
        filters["tags"] = tags

    async def do_list():
        try:
            # Use cached API client if available
            client = cached_api if cached_api else api_client
            
            if cached_api:
                # Cached API client doesn't need context manager
                thoughts = await client.get_thoughts(
                    limit=limit, filters=filters if filters else None
                )
            else:
                # Regular API client needs context manager
                async with api_client:
                    thoughts = await api_client.get_thoughts(
                        limit=limit, filters=filters if filters else None
                    )
            
            title = "Recent Thoughts"
            if cached_api and cached_api.is_offline:
                title += " (Cached)"
            
            output.format_thought_list(thoughts, title)

        except AuthenticationError as e:
            output.format_error(str(e), "Authentication Error")
            ctx.exit(1)
        except NetworkError as e:
            if cached_api:
                output.format_error(f"{e} - Showing cached thoughts", "Network Error")
                # Try to show cached thoughts
                try:
                    thoughts = await cached_api.get_thoughts(limit=limit)
                    output.format_thought_list(thoughts, "Recent Thoughts (Cached)")
                except Exception:
                    ctx.exit(1)
            else:
                output.format_error(str(e), "Network Error")
                ctx.exit(1)
        except APIError as e:
            output.format_error(str(e), "API Error")
            ctx.exit(1)
        except Exception as e:
            output.format_error(f"Unexpected error: {e}", "Error")
            ctx.exit(1)

    asyncio.run(do_list())


@thoughts_group.command()
@click.argument("thought_id")
@click.pass_context
def show(ctx: click.Context, thought_id: str) -> None:
    """Show detailed information about a specific thought.

    Examples:
        einstein thoughts show abc12345
    """
    # Use cached API client if available, otherwise fall back to regular API client
    cached_api: Optional[CachedAPIClient] = ctx.obj.get("cached_api")
    api_client: APIClient = ctx.obj["api_client"]
    auth_manager: AuthManager = ctx.obj["auth_manager"]
    output: OutputFormatter = ctx.obj["output"]

    # Check authentication (skip for offline mode)
    if cached_api and cached_api.is_offline:
        # In offline mode, we can show cached thoughts without authentication
        pass
    elif not auth_manager.is_authenticated():
        output.format_error(
            "You must be logged in to view thoughts. Run 'einstein auth login'",
            "Authentication Error",
        )
        ctx.exit(1)

    async def do_show():
        try:
            # Use cached API client if available
            client = cached_api if cached_api else api_client
            
            if cached_api:
                # Cached API client doesn't need context manager
                thought = await client.get_thought_by_id(thought_id)
            else:
                # Regular API client needs context manager
                async with api_client:
                    thought = await api_client.get_thought_by_id(thought_id)
            
            output.format_thought(thought, show_full=True)
            
            # Show cache indicator if from cache
            if cached_api and cached_api.is_offline:
                output.console.print("📴 Showing cached version", style="yellow")

        except AuthenticationError as e:
            output.format_error(str(e), "Authentication Error")
            ctx.exit(1)
        except NetworkError as e:
            if cached_api:
                output.format_error(f"{e} - Trying cached version", "Network Error")
                try:
                    thought = await cached_api.get_thought_by_id(thought_id)
                    output.format_thought(thought, show_full=True)
                    output.console.print("📴 Showing cached version", style="yellow")
                except Exception:
                    ctx.exit(1)
            else:
                output.format_error(str(e), "Network Error")
                ctx.exit(1)
        except APIError as e:
            output.format_error(str(e), "API Error")
            ctx.exit(1)
        except Exception as e:
            output.format_error(f"Unexpected error: {e}", "Error")
            ctx.exit(1)

    asyncio.run(do_show())


@thoughts_group.command()
@click.argument("thought_id")
@click.confirmation_option(prompt="Are you sure you want to delete this thought?")
@click.pass_context
def delete(ctx: click.Context, thought_id: str) -> None:
    """Delete a thought by ID.

    Examples:
        einstein thoughts delete abc12345
    """
    # Use cached API client if available, otherwise fall back to regular API client
    cached_api: Optional[CachedAPIClient] = ctx.obj.get("cached_api")
    api_client: APIClient = ctx.obj["api_client"]
    auth_manager: AuthManager = ctx.obj["auth_manager"]
    output: OutputFormatter = ctx.obj["output"]

    # Check authentication (skip for offline mode)
    if cached_api and cached_api.is_offline:
        # In offline mode, we can delete thoughts without authentication
        pass
    elif not auth_manager.is_authenticated():
        output.format_error(
            "You must be logged in to delete thoughts. Run 'einstein auth login'",
            "Authentication Error",
        )
        ctx.exit(1)

    async def do_delete():
        try:
            # Use cached API client if available
            client = cached_api if cached_api else api_client
            
            if cached_api:
                # Cached API client doesn't need context manager
                success = await client.delete_thought(thought_id)
            else:
                # Regular API client needs context manager
                async with api_client:
                    success = await api_client.delete_thought(thought_id)
            
            if success:
                output.format_success(f"Thought {thought_id} deleted successfully")
                
                # Show offline indicator if in offline mode
                if cached_api and cached_api.is_offline:
                    output.console.print("📴 Deleted offline - will sync when online", style="yellow")

        except AuthenticationError as e:
            output.format_error(str(e), "Authentication Error")
            ctx.exit(1)
        except NetworkError as e:
            if cached_api:
                output.format_error(f"{e} - Switched to offline mode", "Network Error")
            else:
                output.format_error(str(e), "Network Error")
                ctx.exit(1)
        except APIError as e:
            output.format_error(str(e), "API Error")
            ctx.exit(1)
        except Exception as e:
            output.format_error(f"Unexpected error: {e}", "Error")
            ctx.exit(1)

    asyncio.run(do_delete())
