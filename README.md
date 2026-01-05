# Solana Smart Contractor

AI-powered tool for generating Solana smart contracts using Anchor and Rust.

## Features
- Natural language to contract specification translation.
- Automated Anchor project scaffolding.
- Production-ready Rust code generation.
- Integrated validation and build verification.
- Debugger agent for automated error fixing.

## Prerequisites
- [Rust & Cargo](https://rustup.rs/)
- [Anchor Version 0.30+](https://www.anchor-lang.com/docs/installation)
- OpenRouter API Key

## Setup
1. Clone the repository.
2. Install dependencies: `uv sync` or `pip install -e .`
3. Configure environment: `cp .env.example .env` (add your API key).

## Usage
### CLI Mode
```bash
solana-contractor generate "create a mintable token called MyToken"
```

### Interactive Mode
```bash
python src/main.py
```

### System Check
```bash
solana-contractor check
```
