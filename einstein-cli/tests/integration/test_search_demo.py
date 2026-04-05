#!/usr/bin/env python3
"""Demo script showing search functionality."""

import asyncio
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from einstein_cli.api import SearchResult, ThoughtData
from einstein_cli.output import OutputFormatter
from einstein_cli.commands.search import parse_date_filter


def create_sample_thoughts():
    """Create sample thoughts for demonstration."""
    base_time = datetime.now()
    
    return [
        ThoughtData(
            id="thought1",
            content="Had an amazing coffee meeting with Sarah today. We discussed the new AI project and potential machine learning applications. Very excited about the possibilities!",
            user_id="user1",
            timestamp=base_time,
            metadata={"mood": "excited", "tags": ["work", "meeting", "ai", "ml"]},
            relevance_score=0.95,
        ),
        ThoughtData(
            id="thought2",
            content="Coffee break with the development team was productive. We brainstormed ideas for improving our search algorithms and discussed the latest research papers.",
            user_id="user1",
            timestamp=base_time - timedelta(hours=2),
            metadata={"mood": "neutral", "tags": ["team", "algorithms", "research"]},
            relevance_score=0.87,
        ),
        ThoughtData(
            id="thought3",
            content="Feeling frustrated with the current project timeline. The machine learning model isn't performing as expected and we need to revisit our approach.",
            user_id="user1",
            timestamp=base_time - timedelta(days=1),
            metadata={"mood": "frustrated", "tags": ["work", "ml", "project"]},
            relevance_score=0.82,
        ),
        ThoughtData(
            id="thought4",
            content="Great collaboration session with the design team. We aligned on the user interface for the new semantic search feature. Looking forward to implementation!",
            user_id="user1",
            timestamp=base_time - timedelta(days=2),
            metadata={"mood": "happy", "tags": ["collaboration", "design", "ui"]},
            relevance_score=0.78,
        ),
        ThoughtData(
            id="thought5",
            content="Attended a fascinating conference talk about natural language processing. The speaker shared insights about transformer models and their applications in search.",
            user_id="user1",
            timestamp=base_time - timedelta(days=7),
            metadata={"mood": "curious", "tags": ["conference", "nlp", "transformers"]},
            relevance_score=0.75,
        ),
    ]


def demo_search_results():
    """Demonstrate search result formatting."""
    console = Console()
    output_formatter = OutputFormatter(console, json_mode=False)
    
    print("\n" + "="*80)
    console.print(Panel.fit("🔍 Einstein CLI Search Functionality Demo", style="bold blue"))
    print("="*80)
    
    # Demo 1: Basic search
    console.print("\n[bold green]Demo 1: Basic Search Results[/bold green]")
    console.print("[dim]Query: 'coffee meetings AI'[/dim]\n")
    
    thoughts = create_sample_thoughts()[:3]  # First 3 thoughts
    search_result = SearchResult(
        thoughts=thoughts,
        total=3,
        query="coffee meetings AI",
        execution_time=0.45,
    )
    
    output_formatter.format_search_results(search_result)
    
    # Demo 2: Filtered search
    console.print("\n[bold green]Demo 2: Filtered Search (mood=excited, tags=work,ai)[/bold green]")
    console.print("[dim]Query: 'AI project' --mood excited --tags work,ai[/dim]\n")
    
    filtered_thoughts = [thoughts[0]]  # Only the excited thought
    filtered_result = SearchResult(
        thoughts=filtered_thoughts,
        total=1,
        query="AI project",
        execution_time=0.32,
    )
    
    output_formatter.format_search_results(filtered_result)
    
    # Demo 3: Date-filtered search
    console.print("\n[bold green]Demo 3: Date-Filtered Search (since=7d)[/bold green]")
    console.print("[dim]Query: 'machine learning' --since 7d[/dim]\n")
    
    recent_thoughts = thoughts[:4]  # Thoughts from last week
    date_filtered_result = SearchResult(
        thoughts=recent_thoughts,
        total=4,
        query="machine learning",
        execution_time=0.38,
    )
    
    output_formatter.format_search_results(date_filtered_result)
    
    # Demo 4: High relevance search
    console.print("\n[bold green]Demo 4: High Relevance Search (min-score=0.8)[/bold green]")
    console.print("[dim]Query: 'collaboration' --min-score 0.8[/dim]\n")
    
    high_relevance_thoughts = [t for t in thoughts if t.relevance_score >= 0.8]
    high_relevance_result = SearchResult(
        thoughts=high_relevance_thoughts,
        total=len(high_relevance_thoughts),
        query="collaboration",
        execution_time=0.28,
    )
    
    output_formatter.format_search_results(high_relevance_result)
    
    # Demo 5: No results
    console.print("\n[bold green]Demo 5: No Results Found[/bold green]")
    console.print("[dim]Query: 'quantum computing'[/dim]\n")
    
    no_results = SearchResult(
        thoughts=[],
        total=0,
        query="quantum computing",
        execution_time=0.15,
    )
    
    output_formatter.format_search_results(no_results)


def demo_date_parsing():
    """Demonstrate date parsing functionality."""
    console = Console()
    
    console.print("\n[bold green]Date Parsing Examples[/bold green]")
    
    date_examples = [
        "today",
        "yesterday", 
        "7d",
        "2w",
        "2024-01-15",
        "2024-12-25 14:30:00"
    ]
    
    for date_str in date_examples:
        try:
            parsed_date = parse_date_filter(date_str)
            console.print(f"[cyan]'{date_str}'[/cyan] → {parsed_date.strftime('%Y-%m-%d %H:%M:%S')}")
        except ValueError as e:
            console.print(f"[red]'{date_str}'[/red] → Error: {e}")


def demo_json_output():
    """Demonstrate JSON output mode."""
    console = Console()
    output_formatter = OutputFormatter(console, json_mode=True)
    
    console.print("\n[bold green]JSON Output Mode[/bold green]")
    console.print("[dim]Same search results in JSON format for scripting:[/dim]\n")
    
    thoughts = create_sample_thoughts()[:2]
    search_result = SearchResult(
        thoughts=thoughts,
        total=2,
        query="coffee meetings",
        execution_time=0.45,
    )
    
    output_formatter.format_search_results(search_result)


def main():
    """Run all demos."""
    demo_search_results()
    demo_date_parsing()
    demo_json_output()
    
    console = Console()
    console.print("\n" + "="*80)
    console.print(Panel.fit("✅ Search functionality demo completed!", style="bold green"))
    console.print("="*80)
    
    # Show usage examples
    console.print("\n[bold blue]Usage Examples:[/bold blue]")
    examples = [
        'einstein search "coffee meetings"',
        'einstein search "AI projects" --limit 10',
        'einstein search "work discussions" --mood excited --tags work',
        'einstein search "collaboration ideas" --since 7d --until today',
        'einstein search "machine learning" --min-score 0.8 --sort date',
        'einstein search "research papers" --json  # For scripting',
    ]
    
    for example in examples:
        console.print(f"  [cyan]{example}[/cyan]")
    
    console.print("\n[dim]Note: This demo shows the output formatting. In actual usage, the search command would connect to your Einstein API server.[/dim]")


if __name__ == "__main__":
    main()