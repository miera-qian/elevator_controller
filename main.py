#!/usr/bin/env python3
"""
Elevator Scheduling Algorithm - Command Line Interface

Run elevator scheduling algorithms with easy command-line control.
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

import algo

app = typer.Typer(
    name="elevator",
    help="Elevator scheduling algorithm runner",
    add_completion=False,
)
console = Console()


def get_available_algorithms() -> list[str]:
    """Get list of available algorithm names"""
    return algo.__all__


def show_algorithms_table():
    """Display a formatted table of available algorithms"""
    table = Table(title="Available Algorithms", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Type", style="yellow")

    algorithms_info = {
        "OptimizedScanAlgorithm": ("Optimized SCAN algorithm with intelligent scoring", "Heuristic"),
        "RLDQNAlgorithm": ("Q-learning reinforcement learning algorithm", "Machine Learning"),
        "HybridScanRLAlgorithm": ("Hybrid SCAN + RL with auto-switching ⭐", "Hybrid"),
    }

    for algo_name in get_available_algorithms():
        info = algorithms_info.get(algo_name, ("Custom algorithm", "Custom"))
        table.add_row(algo_name, info[0], info[1])

    console.print(table)


@app.command()
def list_algorithms():
    """
    List all available algorithms
    """
    show_algorithms_table()


@app.command()
def run(
    algorithm: str = typer.Option(
        "HybridScanRLAlgorithm",
        "--algorithm",
        "-a",
        help="Algorithm to use (use 'list' command to see available algorithms)",
    ),
    server_url: str = typer.Option(
        "http://127.0.0.1:8000",
        "--server",
        "-s",
        help="Elevator simulator server URL",
    ),
    enable_logging: bool = typer.Option(
        True,
        "--logging/--no-logging",
        "-l/-L",
        help="Enable or disable logging output",
    ),
    training_mode: Optional[bool] = typer.Option(
        None,
        "--training/--no-training",
        "-t/-T",
        help="Enable training mode (only for RL-based algorithms)",
    ),
    model_path: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Path to RL model file (only for RL-based algorithms)",
    ),
):
    """
    Run an elevator scheduling algorithm

    Examples:

    \b
    # Run hybrid algorithm (default)
    uv run python main.py run

    \b
    # Run specific algorithm
    uv run python main.py run --algorithm OptimizedScanAlgorithm

    \b
    # Run RL algorithm with training
    uv run python main.py run -a RLDQNAlgorithm --training

    \b
    # Run with custom server URL
    uv run python main.py run --server http://localhost:8080
    """
    # Validate algorithm name
    available_algorithms = get_available_algorithms()
    if algorithm not in available_algorithms:
        console.print(f"[red]Error: Unknown algorithm '{algorithm}'[/red]")
        console.print("\n[yellow]Available algorithms:[/yellow]")
        show_algorithms_table()
        raise typer.Exit(code=1)

    # Import and instantiate the algorithm
    try:
        algorithm_class = getattr(algo, algorithm)
    except AttributeError:
        console.print(f"[red]Error: Failed to load algorithm '{algorithm}'[/red]")
        raise typer.Exit(code=1)

    # Build algorithm parameters
    kwargs = {
        "server_url": server_url,
        "enable_logging": enable_logging,
    }

    # Add RL-specific parameters if applicable
    if "RL" in algorithm or "Hybrid" in algorithm:
        if training_mode is not None:
            kwargs["training_mode"] = training_mode
        if model_path is not None:
            kwargs["model_path"] = model_path

    # Display run information
    console.print("\n[bold green]Starting Elevator Scheduling Algorithm[/bold green]")
    console.print(f"[cyan]Algorithm:[/cyan] {algorithm}")
    console.print(f"[cyan]Server:[/cyan] {server_url}")
    console.print(f"[cyan]Logging:[/cyan] {'Enabled' if enable_logging else 'Disabled'}")

    if "RL" in algorithm or "Hybrid" in algorithm:
        if training_mode is not None:
            console.print(f"[cyan]Training Mode:[/cyan] {'Enabled' if training_mode else 'Disabled'}")
        if model_path:
            console.print(f"[cyan]Model Path:[/cyan] {model_path}")

    console.print("\n[yellow]Press Ctrl+C to stop[/yellow]\n")

    # Create and start algorithm
    try:
        algorithm_instance = algorithm_class(**kwargs)
        algorithm_instance.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(code=0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def info(
    algorithm: str = typer.Argument(..., help="Algorithm name to get info about"),
):
    """
    Show detailed information about a specific algorithm
    """
    available_algorithms = get_available_algorithms()

    if algorithm not in available_algorithms:
        console.print(f"[red]Error: Unknown algorithm '{algorithm}'[/red]")
        console.print("\n[yellow]Available algorithms:[/yellow]")
        show_algorithms_table()
        raise typer.Exit(code=1)

    # Get algorithm class
    try:
        algorithm_class = getattr(algo, algorithm)
    except AttributeError:
        console.print(f"[red]Error: Failed to load algorithm '{algorithm}'[/red]")
        raise typer.Exit(code=1)

    # Display information
    console.print(f"\n[bold green]Algorithm Information: {algorithm}[/bold green]\n")

    # Show docstring
    if algorithm_class.__doc__:
        console.print("[cyan]Description:[/cyan]")
        console.print(algorithm_class.__doc__.strip())

    # Show init signature
    console.print("\n[cyan]Initialization Parameters:[/cyan]")
    import inspect
    sig = inspect.signature(algorithm_class.__init__)

    param_table = Table(show_header=True, header_style="bold magenta")
    param_table.add_column("Parameter", style="cyan")
    param_table.add_column("Default", style="yellow")
    param_table.add_column("Type", style="green")

    for param_name, param in sig.parameters.items():
        if param_name in ['self', 'args', 'kwargs']:
            continue

        default = str(param.default) if param.default != inspect.Parameter.empty else "Required"
        param_type = str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"

        # Clean up type annotations
        param_type = param_type.replace("<class '", "").replace("'>", "")

        param_table.add_row(param_name, default, param_type)

    console.print(param_table)


@app.command()
def version():
    """
    Show version information
    """
    console.print("\n[bold green]Elevator Scheduling Algorithm[/bold green]")
    console.print("[cyan]Version:[/cyan] 0.1.0")
    console.print("[cyan]Algorithms:[/cyan]")
    for algo_name in get_available_algorithms():
        console.print(f"  • {algo_name}")
    console.print()


if __name__ == "__main__":
    app()
