"""Unified logging configuration and LLM call logging."""

import json
import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Custom theme for colored logging
LOGGING_THEME = Theme(
    {
        "trace": "dim cyan",
        "debug": "dim blue",
        "info": "green",
        "warning": "yellow",
        "error": "red bold",
        "critical": "red bold reverse",
    }
)

console = Console(theme=LOGGING_THEME)


def load_config():
    """Load configuration from config.yaml."""
    import yaml

    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def should_use_colors():
    """Check if colors should be used based on config and terminal."""
    config = load_config()
    output_config = config.get("output", {})
    colors = output_config.get("colors", True)
    if not colors:
        return False
    # Auto-detect terminal capabilities
    return console.color_system is not None


def is_logging_enabled():
    """Check if logging is enabled based on config."""
    config = load_config()
    output_config = config.get("output", {})
    return output_config.get("logging", True)


def setup_logging(verbose: bool = False, use_colors: bool = True):
    """Configure basic logging for the application."""
    # Check if logging is disabled in config
    if not is_logging_enabled():
        # Disable all logging by setting level to CRITICAL+1 (effectively off)
        logging.disable(logging.CRITICAL)
        return

    level = logging.DEBUG if verbose else logging.INFO

    if use_colors and should_use_colors():
        # Use Rich handler for colored console output
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_level=True,
            show_path=verbose,
            markup=True,
        )
        logging.basicConfig(
            level=level,
            handlers=[rich_handler],
            force=True,
        )
    else:
        # Plain text logging
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Silence chatty libraries
    logging.getLogger("pydantic").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def log_llm_call(
    agent_name: str,
    model: str,
    input_data: dict,
    output_data: dict,
    success: bool,
    error: str | None = None,
):
    """Log LLM call details to a JSONL file."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "model": model,
        "input": input_data,
        "output": output_data,
        "success": success,
        "error": error,
    }

    log_file = log_dir / f"llm_calls_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
