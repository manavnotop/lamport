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
make fix              # ruff check --fix + ruff format

# Run tests
uv run pytest

# Run CLI
solana-contractor generate "create a mintable token called MyToken"
solana-contractor check        # verify prerequisites (cargo, rustc, anchor)
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

**Agents** (`agents/`):
- `spec_interpreter.py`: Converts natural language → structured `TokenSpec`
- `project_planner.py`: Creates Anchor project scaffold (Cargo.toml, Anchor.toml, lib.rs)
- `code_generator.py`: Generates Rust instruction handlers (Anchor 0.30.x)
- `debugger.py`: Fixes build/validation errors (one retry)

**Graph** (`graph/workflow.py`): LangGraph workflow orchestration defining the pipeline above.

**Schemas** (`schemas/`):
- `state.py`: GraphState Pydantic model (workflow state)
- `contracts.py`: TokenSpec, ProjectStructure, DebuggerResult

**Utilities** (`utils/`):
- `llm.py`: OpenRouter HTTPX client wrapper
- `builder.py`: Cargo/Anchor build utilities
- `file_ops.py`: File read/write operations

**Validators** (`validators/static_validator.py`): Runs rustfmt, cargo check, and structure validation.

## Configuration

Environment variables (prefix: `SOLANA_AGENT_`):
- `OPENROUTER_API_KEY` - Required for LLM calls
- `MODEL_*` - Configure per-agent models (defaults use Google Gemini 2.5 Pro and Claude Sonnet 4)

## Code Style

- Python 3.13+, Ruff for linting/formatting (see `ruff.toml`)
- Line length: 100, double quotes
