"""Configuration settings for the Solana smart contract generator.

Loads settings from config.yaml and .env file.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from os import getenv
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env file first so env vars can override
load_dotenv()

CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"


@dataclass
class Settings:
    """Application settings loaded from config.yaml and .env."""

    # OpenRouter API key (loaded from environment)
    openrouter_api_key: str | None = field(default=None)

    # Model Configuration (cost-aware routing)
    model_spec_interpreter: str = field(default="google/gemini-2.5-pro")
    model_project_planner: str = field(default="google/gemini-2.5-pro")
    model_file_planner: str = field(default="google/gemini-2.5-pro")
    model_code_generator: str = field(default="anthropic/claude-sonnet-4-20250514")
    model_debugger: str = field(default="anthropic/claude-opus-4-20250514")

    # Build Configuration
    anchor_sbf_root: str | None = field(default=None)


def _load_config_from_yaml() -> dict:
    """Load configuration from config.yaml file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def _merge_settings(yaml_config: dict) -> Settings:
    """Merge YAML config with defaults, prioritizing YAML values."""
    defaults = Settings()

    # Parse models section
    models = yaml_config.get("models", {})
    build = yaml_config.get("build", {})

    return Settings(
        openrouter_api_key=getenv("OPENROUTER_API_KEY"),
        model_spec_interpreter=models.get("spec_interpreter", defaults.model_spec_interpreter),
        model_project_planner=models.get("project_planner", defaults.model_project_planner),
        model_file_planner=models.get("file_planner", defaults.model_file_planner),
        model_code_generator=models.get("code_generator", defaults.model_code_generator),
        model_debugger=models.get("debugger", defaults.model_debugger),
        anchor_sbf_root=build.get("anchor_sbf_root", defaults.anchor_sbf_root),
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance loaded from config.yaml."""
    yaml_config = _load_config_from_yaml()
    return _merge_settings(yaml_config)


def require_api_key() -> str:
    """Get API key or raise error if not set."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not set in .env file. "
            "Please copy .env.example to .env and add your API key."
        )
    return settings.openrouter_api_key
