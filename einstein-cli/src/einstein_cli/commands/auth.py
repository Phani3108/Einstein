"""Authentication commands for Einstein CLI."""

import click
import asyncio
from typing import Optional

from einstein_cli.api import APIClient, AuthenticationError, NetworkError
from einstein_cli.auth import AuthManager
from einstein_cli.output import OutputFormatter


@click.group(name="auth")
def auth_group() -> None:
    """Authentication commands."""
    pass


@auth_group.command()
@click.option("--email", prompt=True, help="Email address")
@click.option("--password", prompt=True, hide_input=True, help="Password")
@click.pass_context
def login(ctx: click.Context, email: str, password: str) -> None:
    """Login to Einstein server."""
    api_client: APIClient = ctx.obj["api_client"]
    output: OutputFormatter = ctx.obj["output"]

    async def do_login():
        try:
            async with api_client:
                token = await api_client.authenticate(email, password)
                output.format_success(f"Successfully logged in as {email}")

        except AuthenticationError as e:
            output.format_error(str(e), "Authentication Error")
            ctx.exit(1)
        except NetworkError as e:
            output.format_error(str(e), "Network Error")
            ctx.exit(1)
        except Exception as e:
            output.format_error(f"Unexpected error: {e}", "Error")
            ctx.exit(1)

    asyncio.run(do_login())


@auth_group.command()
@click.pass_context
def logout(ctx: click.Context) -> None:
    """Logout from Einstein server."""
    auth_manager: AuthManager = ctx.obj["auth_manager"]
    output: OutputFormatter = ctx.obj["output"]

    if not auth_manager.is_authenticated():
        output.format_error("You are not currently logged in.", "Authentication Error")
        ctx.exit(1)

    auth_manager.clear_token()
    output.format_success("Successfully logged out")


@auth_group.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show authentication status."""
    auth_manager: AuthManager = ctx.obj["auth_manager"]
    output: OutputFormatter = ctx.obj["output"]

    if auth_manager.is_authenticated():
        token_info = auth_manager.get_token_info()
        if output.json_mode:
            click.echo(click.get_text_stream("stdout").write(str(token_info)))
        else:
            output.console.print("[green]✅ Authenticated[/green]")
            if token_info and "expires_in_seconds" in token_info:
                expires_in = token_info["expires_in_seconds"]
                if expires_in > 0:
                    hours = expires_in // 3600
                    minutes = (expires_in % 3600) // 60
                    output.console.print(f"Token expires in: {hours}h {minutes}m")
    else:
        if output.json_mode:
            click.echo('{"authenticated": false}')
        else:
            output.console.print("[red]❌ Not authenticated[/red]")
            output.console.print("Run 'einstein auth login' to authenticate")
