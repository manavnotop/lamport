"""CLI entry point for Solana smart contract generator."""

import asyncio
import shutil
from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import require_api_key
from src.graph.workflow import run_workflow
from src.schemas.models import GraphState
from src.utils.logging import setup_logging

app = typer.Typer(
    name="solana-contractor",
    help="AI-powered Solana smart contract generator using Anchor/Rust",
    add_completion=False,
)

console = Console()


def _on_event(event: str) -> None:
    """Handle workflow events and display progress."""
    # Mapping for simple string events
    event_map = {
        "workflow:start": "[dim]Starting workflow...[/dim]",
        "workflow:success": "[green]✓ Build successful![/green]",
        "workflow:failed": "[yellow]⚠ Build failed - check logs for details[/yellow]",
        "agent:Spec Interpreter:start": "  [cyan]→[/cyan] [bold]Spec Interpreter[/bold]",
        "agent:Spec Interpreter:end": "  [green]✓[/green] [bold]Spec Interpreter[/bold]",
        "agent:Project Planner:start": "  [cyan]→[/cyan] [bold]Project Planner[/bold]",
        "agent:Project Planner:end": "  [green]✓[/green] [bold]Project Planner[/bold]",
        "agent:Code Generator:start": "  [cyan]→[/cyan] [bold]Code Generator[/bold]",
        "agent:Code Generator:end": "  [green]✓[/green] [bold]Code Generator[/bold]",
        "agent:Static Validator:start": "  [cyan]→[/cyan] [bold]Static Validator[/bold]",
        "agent:Static Validator:end": "  [green]✓[/green] [bold]Static Validator[/bold]",
        "agent:Debugger:start": "  [cyan]→[/cyan] [bold]Debugger[/bold]",
        "agent:Debugger:end": "  [green]✓[/green] [bold]Debugger[/bold]",
        "build:start": "  [cyan]→[/cyan] [bold]Building contract...[/bold]",
        "build:success": "  [green]✓[/green] [bold]Build successful![/bold]",
        "build:failed": "  [yellow]✗[/yellow] [bold]Build failed[/bold]",
        "validation:start": "  [cyan]→[/cyan] [bold]Running validation...[/bold]",
        "validation:success": "  [green]✓[/green] [bold]Validation passed[/bold]",
        "validation:failed": "  [yellow]✗[/yellow] [bold]Validation failed[/bold]",
    }

    if event in event_map:
        console.print(event_map[event])
        return

    # Handle parameterized events
    if event.startswith("llm:"):
        _, type, agent = event.split(":")
        msg = "Calling LLM" if type == "start" else "LLM call completed"
        console.print(f"    [dim]{msg} ({agent})...[/dim]")

    elif event.startswith("file:write:"):
        path = event.split(":", 2)[2]
        console.print(f"    [dim]Creating: {path}[/dim]")

    elif event.startswith("file:created:"):
        parts = event.split(":", 3)
        path = parts[2]
        size = parts[3] if len(parts) > 3 else ""
        console.print(f"    [green]✓[/green] Created: {path} [dim]{size}[/dim]")


def _generate_contract(
    spec: str,
    output: Path,
    verbose: bool = False,
    test_mode: bool = False,
    on_event: Callable[[str], None] | None = None,
) -> GraphState:
    """Generate a Solana smart contract from specification.

    Args:
        spec: Natural language specification for the contract
        output: Output directory for generated project
        verbose: Show verbose output
        test_mode: Use mock LLM for testing (no API calls)
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

    console.print(
        Panel.fit(
            "[bold blue]Solana Smart Contract Generator[/bold blue]\n"
            f"[dim]Generating: {spec}[/dim]\n"
            f"[dim]Test mode: {'Yes' if test_mode else 'No'}[/dim]",
            title="Start",
        )
    )

    async def run():
        return await run_workflow(spec, on_event=on_event, test_mode=test_mode)

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
        solana-contractor "create a mintable token called MyToken with symbol MYT"

    Test mode:
        solana-contractor "create a token" --test
    """
    state = _generate_contract(spec, output, verbose, test_mode, on_event=_on_event)
    _display_results(state, output, verbose)


def run_interactive():
    """Start interactive REPL mode for generating contracts."""
    console.print(
        Panel.fit(
            "[bold blue]Solana Smart Contract Generator[/bold blue]\n\n"
            "Enter a description of the contract you want to generate.\n"
            "Type [cyan]quit[/cyan] or [cyan]exit[/cyan] to leave.",
            title="Welcome",
        )
    )

    while True:
        prompt = console.input("\n[bold cyan]What should I build?[/bold cyan] ")

        if prompt.lower() in ("quit", "exit", "q"):
            console.print("[yellow]Goodbye![/yellow]")
            break

        if not prompt.strip():
            continue

        try:
            state = _generate_contract(
                prompt, Path("."), verbose=False, test_mode=False, on_event=_on_event
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
    """Display workflow results.

    Args:
        state: Final workflow state
        output: Output directory
        verbose: Show verbose output
    """
    if state.build_success:
        console.print(
            Panel.fit(
                f"[bold green]Success![/bold green]\n\n"
                f"Project: [cyan]{state.project_name}[/cyan]\n"
                f"Artifact: [cyan]{state.final_artifact or 'N/A'}[/cyan]\n"
                f"Output: [cyan]{output}[/cyan]",
                title="Build Successful",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[bold yellow]Build Failed[/bold yellow]\n\n"
                f"Output directory: [cyan]{output}[/cyan]\n"
                f"Files generated: {len(state.files)}",
                title="Partial Result",
            )
        )

        if state.error_message:
            console.print(f"\n[red]Error: {state.error_message}[/red]")

    # Show file structure
    if state.files:
        table = Table(title="Generated Files")
        table.add_column("Path", style="cyan")
        table.add_column("Size", justify="right", style="green")

        for path in sorted(state.files.keys()):
            size = len(state.files[path])
            table.add_row(path, f"{size} bytes")

        console.print(table)

    # Show errors if verbose or failed
    if verbose and state.validation_errors:
        console.print("\n[yellow]Validation Errors:[/yellow]")
        for error in state.validation_errors[:10]:
            console.print(f"  - {error}")

    if verbose and state.build_logs:
        console.print("\n[yellow]Build Logs:[/yellow]")
        console.print(state.build_logs)


@app.command()
def check() -> None:
    """Check system prerequisites."""
    console.print(Panel.fit("[bold]Prerequisites Check[/bold]"))

    checks = [
        ("cargo", shutil.which("cargo")),
        ("rustc", shutil.which("rustc")),
        ("anchor", shutil.which("anchor")),
        ("OPENROUTER_API_KEY", "OPENROUTER_API_KEY" in __import__("os").environ),
    ]

    table = Table()
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="green")

    all_ok = True
    for name, found in checks:
        status = "[green]✓ Found[/green]" if found else "[red]✗ Not Found[/red]"
        table.add_row(name, status)
        if not found:
            all_ok = False

    console.print(table)

    if all_ok:
        console.print("\n[green]All prerequisites met![/green]")
    else:
        console.print(
            "\n[yellow]Some tools are missing. Install them for full functionality.[/yellow]"
        )


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
