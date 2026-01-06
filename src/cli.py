"""CLI entry point for Lamport - AI-powered Solana smart contract generator."""

import asyncio
import shutil
from collections.abc import Callable
from pathlib import Path

import typer
from rich.box import DOUBLE, ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from src.config import require_api_key
from src.graph.workflow import run_workflow
from src.schemas.models import GraphState
from src.utils.logging import load_config, setup_logging

app = typer.Typer(
    name="lamport",
    help="AI-powered Solana smart contract generator using Anchor/Rust",
    add_completion=False,
)

console = Console()

# ASCII Art Branding
ASCII_ART = """[bold cyan]
██╗      █████╗ ███╗   ███╗██████╗  ██████╗ ██████╗ ████████╗
██║     ██╔══██╗████╗ ████║██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝
██║     ███████║██╔████╔██║██████╔╝██║   ██║██████╔╝   ██║
██║     ██╔══██║██║╚██╔╝██║██╔═══╝ ██║   ██║██╔══██╗   ██║
███████╗██║  ██║██║ ╚═╝ ██║██║     ╚██████╔╝██║  ██║   ██║
╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝[/bold cyan]"""


def should_show_ascii_art() -> bool:
    """Check if ASCII art should be shown based on config."""
    config = load_config()
    output_config = config.get("output", {})
    return output_config.get("ascii_art", True)


def _print_welcome() -> None:
    """Print welcome screen with ASCII art."""
    if should_show_ascii_art():
        console.print(ASCII_ART)
        console.print()

    welcome_text = Text.from_markup(
        "AI-Powered Solana Smart Contract Generator\n\n"
        "Enter a description of the contract you want to generate.\n"
        "Type [bold orange3]quit[/bold orange3] or [bold orange3]exit[/bold orange3] to leave.",
        style="white",
    )

    console.print(
        Panel.fit(welcome_text, title="Welcome", box=ROUNDED, style=Style(color="orange3"))
    )


def _print_start_header(spec: str, project_name: str | None, test_mode: bool) -> None:
    """Print the start header with generation info."""
    test_mode_text = (
        "[bold magenta]Yes[/bold magenta]" if test_mode else "[bold green]No[/bold green]"
    )

    header_text = Text.from_markup(
        "Solana Smart Contract Generator\n"
        f"[dim]Generating:[/dim] [bold cyan]{spec}[/bold cyan]\n"
        f"[dim]Project:[/dim] [bold cyan]{project_name or 'Unnamed'}[/bold cyan]\n"
        f"[dim]Test mode:[/dim] {test_mode_text}",
        style="white",
    )

    console.print(Panel.fit(header_text, title="Start", box=ROUNDED, style=Style(color="orange3")))


def _on_event(event: str) -> None:
    """Handle workflow events and display progress with beautiful formatting."""
    # Mapping for simple string events with rich formatting
    event_map = {
        "workflow:start": ("Starting workflow...", "dim"),
        "workflow:success": ("Build successful!", "green bold"),
        "workflow:failed": ("Build failed - check logs for details", "yellow bold"),
        "agent:Spec Interpreter:start": ("Spec Interpreter", "cyan bold"),
        "agent:Spec Interpreter:end": ("Spec Interpreter", "green bold"),
        "agent:Project Planner:start": ("Project Planner", "cyan bold"),
        "agent:Project Planner:end": ("Project Planner", "green bold"),
        "agent:Code Generator:start": ("Code Generator", "cyan bold"),
        "agent:Code Generator:end": ("Code Generator", "green bold"),
        "agent:Static Validator:start": ("Static Validator", "cyan bold"),
        "agent:Static Validator:end": ("Static Validator", "green bold"),
        "agent:Debugger:start": ("Debugger", "cyan bold"),
        "agent:Debugger:end": ("Debugger", "green bold"),
        "build:start": ("Building contract...", "cyan bold"),
        "build:success": ("Build successful!", "green bold"),
        "build:failed": ("Build failed", "red bold"),
        "validation:start": ("Running validation...", "cyan bold"),
        "validation:success": ("Validation passed", "green bold"),
        "validation:failed": ("Validation failed", "red bold"),
    }

    if event in event_map:
        msg, style = event_map[event]
        console.print(f"[{style}]{msg}[/{style}]")
        return

    # Handle parameterized events
    if event.startswith("llm:"):
        _, type, agent = event.split(":")
        msg = "Calling LLM" if type == "start" else "LLM call completed"
        console.print(f"    [dim]{msg} ({agent})...[/dim]")

    elif event.startswith("file:write:"):
        path = event.split(":", 2)[2]
        console.print(f"    [dim]→[/dim] [cyan]Creating[/cyan] [white]{path}[/white]")

    elif event.startswith("file:created:"):
        parts = event.split(":", 3)
        path = parts[2]
        size = parts[3] if len(parts) > 3 else ""
        console.print(f"    [green]✓[/green] Created: [cyan]{path}[/cyan] [dim]{size}[/dim]")


def _generate_contract(
    spec: str,
    output: Path,
    verbose: bool = False,
    test_mode: bool = False,
    project_name: str | None = None,
    on_event: Callable[[str], None] | None = None,
) -> GraphState:
    """Generate a Solana smart contract from specification.

    Args:
        spec: Natural language specification for the contract
        output: Output directory for generated project
        verbose: Show verbose output
        test_mode: Use mock LLM for testing (no API calls)
        project_name: Project name for anchor init
        on_event: Optional callback for progress events

    Returns:
        Final workflow state
    """
    # Setup logging first
    setup_logging(verbose=verbose)

    # Check for API key (skip in test mode)
    if not test_mode:
        try:
            require_api_key()
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e

    # Check prerequisites
    if not shutil.which("cargo"):
        console.print("[red]Error: cargo not found. Please install Rust toolchain.[/red]")
        raise typer.Exit(1)

    _print_start_header(spec, project_name, test_mode)

    async def run():
        return await run_workflow(
            spec, on_event=on_event, test_mode=test_mode, project_name=project_name
        )

    state = asyncio.run(run())

    return state


@app.command()
def generate(
    spec: str = typer.Argument(
        ...,
        help="Natural language specification for the contract",
    ),
    output: Path = typer.Option(  # noqa: B008
        "./generated",
        "-o",
        "--output",
        help="Output directory for generated project",
    ),
    name: str = typer.Option(
        None,
        "-n",
        "--name",
        help="Project name for anchor init",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Show verbose output",
    ),
    test_mode: bool = typer.Option(
        False,
        "-t",
        "--test",
        help="Use mock LLM (no API calls)",
    ),
) -> None:
    """Generate a Solana smart contract from natural language specification.

    Example:
        lamport "create a mintable token called MyToken with symbol MYT" --name my_token

    Test mode:
        lamport "create a token" --test --name my_token
    """
    state = _generate_contract(
        spec, output, verbose, test_mode, project_name=name, on_event=_on_event
    )
    _display_results(state, output, verbose)


def run_interactive():
    """Start interactive REPL mode for generating contracts."""
    _print_welcome()

    while True:
        # Ask for project name first
        project_name = console.input(
            "\n[bold cyan]Project name (for anchor init):[/bold cyan] "
        ).strip()

        if project_name.lower() in ("quit", "exit", "q"):
            console.print("[yellow]Goodbye![/yellow]")
            break

        if not project_name:
            console.print("[yellow]Please enter a project name.[/yellow]")
            continue

        # Ask for the contract specification
        prompt = console.input(f"[bold cyan]What should I build for '{project_name}'?[/bold cyan] ")

        if prompt.lower() in ("quit", "exit", "q"):
            console.print("[yellow]Goodbye![/yellow]")
            break

        if not prompt.strip():
            continue

        try:
            state = _generate_contract(
                prompt,
                Path("."),
                verbose=False,
                test_mode=False,
                project_name=project_name,
                on_event=_on_event,
            )

            # Use project_root from state (set by workflow in contracts/<name>/)
            if state.project_root:
                project_path = Path(state.project_root)
                _display_results(state, project_path, verbose=False)
            else:
                console.print("[red]Error: No project_root in state[/red]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def _display_results(state: GraphState, output: Path, verbose: bool) -> None:
    """Display workflow results with beautiful formatting.

    Args:
        state: Final workflow state
        output: Output directory
        verbose: Show verbose output
    """
    if state.build_success:
        # Success panel with green styling
        console.print(
            Panel.fit(
                Text.assemble(
                    ("✓ ", "green bold"),
                    ("Build Successful!\n\n", "bold green"),
                    ("Project: ", "dim"),
                    (state.project_name or "N/A", "cyan bold"),
                    ("\nOutput: ", "dim"),
                    (str(output), "cyan"),
                ),
                title="[bold green]Success[/bold green]",
                box=ROUNDED,
                style=Style(color="green"),
            )
        )
    else:
        # Failure panel with yellow styling
        console.print(
            Panel.fit(
                Text.assemble(
                    ("⚠ ", "yellow bold"),
                    ("Build Failed\n\n", "bold yellow"),
                    ("Output directory: ", "dim"),
                    (str(output), "cyan"),
                    ("\nFiles generated: ", "dim"),
                    (str(len(state.files)), "yellow"),
                ),
                title="[bold yellow]Partial Result[/bold yellow]",
                box=ROUNDED,
                style=Style(color="yellow"),
            )
        )

        if state.error_message:
            console.print(f"\n[red]Error: {state.error_message}[/red]")

    # Show file structure with styled table
    if state.files:
        table = Table(
            title="[bold]Generated Files[/bold]",
            box=DOUBLE,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Path", style="cyan")
        table.add_column("Size", justify="right", style="green")

        for path in sorted(state.files.keys()):
            size = len(state.files[path])
            table.add_row(path, f"{size} bytes")

        console.print(table)

    # Show errors if verbose or failed
    if verbose and state.validation_errors:
        console.print("\n[bold yellow]Validation Errors:[/bold yellow]")
        for error in state.validation_errors[:10]:
            console.print(f"  - {error}")

    if verbose and state.build_logs:
        console.print("\n[bold yellow]Build Logs:[/bold yellow]")
        console.print(state.build_logs)


@app.command()
def check() -> None:
    """Check system prerequisites."""
    console.print(
        Panel.fit(
            "[bold]Prerequisites Check[/bold]",
            title="System Check",
            box=ROUNDED,
        )
    )

    checks = [
        ("cargo", shutil.which("cargo")),
        ("rustc", shutil.which("rustc")),
        ("anchor", shutil.which("anchor")),
        ("OPENROUTER_API_KEY", "OPENROUTER_API_KEY" in __import__("os").environ),
    ]

    table = Table(box=ROUNDED)
    table.add_column("Tool", style="bold cyan")
    table.add_column("Status", style="green")

    all_ok = True
    for name, found in checks:
        status = "[green]✓ Found[/green]" if found else "[red]✗ Not Found[/red]"
        table.add_row(name, status)
        if not found:
            all_ok = False

    console.print(table)

    if all_ok:
        console.print("\n[bold green]All prerequisites met![/bold green]")
    else:
        console.print(
            "\n[bold yellow]Some tools are missing. "
            "Install them for full functionality.[/bold yellow]"
        )


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
