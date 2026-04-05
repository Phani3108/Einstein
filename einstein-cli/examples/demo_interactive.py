#!/usr/bin/env python3
"""Demo script showing interactive mode functionality."""

import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from einstein_cli.interactive import InteractiveSession
from einstein_cli.config import ConfigManager
from einstein_cli.cached_api import CachedAPIClient
from einstein_cli.output import OutputFormatter
from einstein_cli.auth import AuthManager
from einstein_cli.api import ThoughtData, SearchResult
from rich.console import Console


async def demo_interactive_session():
    """Demonstrate interactive session functionality."""
    print("🧠 Einstein CLI Interactive Mode Demo\n")
    
    # Create console
    console = Console()
    
    # Create mock components
    config = Mock(spec=ConfigManager)
    config.get.return_value = True  # Cache enabled
    
    auth_manager = Mock(spec=AuthManager)
    auth_manager.is_authenticated.return_value = True
    
    # Create mock API responses
    sample_thoughts = [
        ThoughtData(
            id="thought-1",
            content="Had a great coffee meeting with the team today. We discussed the new AI project and everyone seems excited about the possibilities.",
            user_id="demo-user",
            timestamp=datetime.now(),
            metadata={"mood": "excited", "tags": ["work", "AI", "team"]}
        ),
        ThoughtData(
            id="thought-2", 
            content="Feeling a bit overwhelmed with all the new technologies to learn. Need to prioritize and focus on one thing at a time.",
            user_id="demo-user",
            timestamp=datetime.now(),
            metadata={"mood": "anxious", "tags": ["learning", "technology"]}
        ),
        ThoughtData(
            id="thought-3",
            content="Beautiful sunset today. Sometimes it's important to step back and appreciate the simple things in life.",
            user_id="demo-user", 
            timestamp=datetime.now(),
            metadata={"mood": "grateful", "tags": ["nature", "mindfulness"]}
        )
    ]
    
    cached_api = Mock(spec=CachedAPIClient)
    
    # Mock API methods
    cached_api.create_thought = AsyncMock(side_effect=lambda content, **kwargs: ThoughtData(
        id=f"new-{len(sample_thoughts) + 1}",
        content=content,
        user_id="demo-user",
        timestamp=datetime.now(),
        metadata=kwargs.get("metadata", {})
    ))
    
    cached_api.search_thoughts = AsyncMock(return_value=SearchResult(
        thoughts=[t for t in sample_thoughts if "coffee" in t.content.lower()],
        total=1,
        query="coffee",
        execution_time=0.15,
        filters_applied=None
    ))
    
    cached_api.get_thoughts = AsyncMock(return_value=sample_thoughts)
    
    cached_api.get_thought = AsyncMock(side_effect=lambda id: next(
        (t for t in sample_thoughts if t.id == id), None
    ))
    
    cached_api.delete_thought = AsyncMock(return_value=True)
    
    cached_api.get_stats = AsyncMock(return_value={
        "total_thoughts": len(sample_thoughts),
        "cached_thoughts": len(sample_thoughts),
        "pending_sync": 0,
        "offline_mode": False,
        "cache_enabled": True
    })
    
    cached_api.sync = AsyncMock(return_value={"synced": 0, "conflicts": 0})
    
    output = OutputFormatter(console, json_mode=False)
    
    # Create interactive session
    session = InteractiveSession(config, cached_api, output, auth_manager, console)
    
    # Demo various commands
    console.print("\n[bold blue]🎯 Demo: Interactive Session Commands[/bold blue]\n")
    
    # Demo 1: Show welcome and help
    console.print("[dim]>>> Starting interactive session...[/dim]")
    session._show_welcome()
    
    console.print("\n[dim]>>> help[/dim]")
    await session._handle_help([])
    
    # Demo 2: Add a thought
    console.print("\n[dim]>>> add: Just had an amazing idea for improving our search algorithm![/dim]")
    await session._handle_add(["Just had an amazing idea for improving our search algorithm!"])
    
    # Demo 3: Search thoughts
    console.print("\n[dim]>>> search: coffee[/dim]")
    await session._handle_search(["coffee"])
    
    # Demo 4: List thoughts
    console.print("\n[dim]>>> list 2[/dim]")
    await session._handle_list(["2"])
    
    # Demo 5: Show specific thought
    console.print("\n[dim]>>> show thought-1[/dim]")
    await session._handle_show(["thought-1"])
    
    # Demo 6: Show stats
    console.print("\n[dim]>>> stats[/dim]")
    await session._handle_stats([])
    
    # Demo 7: Show config
    console.print("\n[dim]>>> config[/dim]")
    await session._handle_config([])
    
    # Demo 8: Show history
    console.print("\n[dim]>>> history[/dim]")
    # Simulate some history
    session.history = [
        "add: First thought",
        "search: coffee",
        "list 5",
        "help"
    ]
    await session._handle_history([])
    
    # Demo 9: Show goodbye
    console.print("\n[dim]>>> exit[/dim]")
    session._show_goodbye()
    
    console.print("\n[green]✨ Demo completed! The interactive mode provides:[/green]")
    console.print("• [cyan]Natural command syntax with colon notation[/cyan]")
    console.print("• [cyan]Rich formatting and beautiful output[/cyan]") 
    console.print("• [cyan]Command history and help system[/cyan]")
    console.print("• [cyan]Authentication awareness[/cyan]")
    console.print("• [cyan]Graceful error handling[/cyan]")
    console.print("• [cyan]Session management[/cyan]")


def demo_command_parsing():
    """Demonstrate command parsing capabilities."""
    print("\n🔍 Command Parsing Demo\n")
    
    console = Console()
    
    # Create mock session
    session = InteractiveSession(Mock(), Mock(), Mock(), Mock(), console)
    
    # Test various input formats
    test_inputs = [
        "add: Had a great meeting today",
        "search: coffee meetings",
        "list 10",
        "show abc123",
        "help",
        "h",  # alias
        "ls",  # alias for list
        "exit",
        "quit",
    ]
    
    console.print("[bold]Command Parsing Examples:[/bold]\n")
    
    for input_str in test_inputs:
        # Parse command manually to show the logic
        parts = input_str.split() if ":" not in input_str else [input_str.split(":")[0].strip()]
        command = parts[0].lower()
        args = parts[1:] if ":" not in input_str else [input_str.split(":", 1)[1].strip()] if ":" in input_str else []
        
        # Handle colon syntax
        if ":" in input_str:
            colon_index = input_str.find(":")
            potential_command = input_str[:colon_index].strip().lower()
            if potential_command in ["add", "search"]:
                command = potential_command
                content = input_str[colon_index + 1:].strip()
                args = [content] if content else []
        
        # Handle aliases
        original_command = command
        command = session.aliases.get(command, command)
        
        alias_note = f" (alias for {command})" if original_command != command else ""
        args_display = f" with args: {args}" if args else ""
        
        console.print(f"[dim]'{input_str}'[/dim] → [cyan]{command}[/cyan]{alias_note}{args_display}")


def main():
    """Run the demo."""
    try:
        asyncio.run(demo_interactive_session())
        demo_command_parsing()
        
        print("\n[bold green]🎉 Interactive mode demo completed successfully![/bold green]")
        print("\nTo try it yourself, run: [cyan]einstein interactive[/cyan]")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)