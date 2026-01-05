"""Unified logging configuration and LLM call logging."""

import json
import logging
from datetime import datetime
from pathlib import Path


# Base logging config
def setup_logging(verbose: bool = False):
    """Configure basic logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
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
