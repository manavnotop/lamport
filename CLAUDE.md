# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**smart-contractor** is an AI CLI tool that generates Solana smart contracts from natural language specifications using the Anchor Framework. It uses a multi-agent LangGraph pipeline to interpret specs, plan project structure, generate Rust/Anchor code, and validate/build the contract.

## Development Commands

```bash
# Install dependencies
make install          # uv sync

# Linting and formatting
make lint             # ruff check + ruff format --check
make fix              # ruff check --select I --fix + ruff format

# Run tests
uv run pytest

# Run CLI
solana-contractor generate "create a mintable token called MyToken"
solana-contractor generate "create a token" --test  # test mode (MockLLM, no API calls)
solana-contractor check        # verify prerequisites (cargo, rustc, anchor)
make run                      # run interactive mode
```

## Architecture

### Multi-Agent LangGraph Pipeline

```
User Spec → spec_interpreter → project_planner → code_generator → static_validator → build_contract
                                                   ↑                           |
                                                   |------Debugger <-----------|
                                                   |             |
                                                   └─────Abort ←─┘
```

**Agents** (`src/agents/`):
- `spec_interpreter.py`: LLM-only agent converting natural language → structured `TokenSpec`
- `project_planner.py`: Creates Anchor project scaffold (Anchor.toml, programs/*/Cargo.toml, lib.rs)
- `code_generator.py`: Generates Rust instruction handlers (Anchor 0.30.x, JSON output)
- `debugger.py`: Fixes build/validation errors (one retry max)
- `base.py`: Abstract `BaseAgent` and `LLMOnlyAgent` with LangChain integration, ReAct agent executor, and output parsing helpers

**Graph** (`src/graph/workflow.py`): LangGraph `StateGraph` with conditional edges for branching on validation/build results. Projects are output to `contracts/<name>_<timestamp>/`. Control fields (`user_spec`, `retry_count`, `project_root`, etc.) are protected from LLM injection via `_safe_merge()`.

**Schemas** (`src/schemas/models.py`):
- `GraphState`: Pydantic model for workflow state
- `TokenSpec`: Structured token specification from natural language
- `ContractFeature`: Enum of supported features (mintable, burnable, etc.)
- `ProjectFileSpec` / `DebuggerPatch`: File operation models

**Utilities** (`src/utils/`):
- `llm_utils.py`: OpenRouter HTTP client, `create_agent_executor` (ReAct agent), `MockLLM` for testing
- `builder.py`: Cargo/Anchor build utilities (`cargo check-sbf`, `anchor build`)
- `file_ops.py`: File read/write with path normalization
- `logging.py`: Structured workflow event logging

**Validators** (`src/validators/static_validator.py`): Runs rust syntax checks, Anchor structure validation, `cargo check --target sbf-solana-solana`.

## Configuration

Environment variables (prefix: `SOLANA_AGENT_`):
- `OPENROUTER_API_KEY` - Required for LLM calls
- `MODEL_*` - Configure per-agent models (defaults use Google Gemini 2.5 Pro and Claude Sonnet 4)

## Code Style

- Python 3.13+, Ruff for linting/formatting (see `ruff.toml`)
- Line length: 100, double quotes
