"""Code Generator Agent - writes Rust instruction handlers using LangChain."""

import json

from src.agents.base import BaseAgent
from src.schemas.models import TokenSpec

SYSTEM_PROMPT = """You are an expert Solana smart contract Rust developer specializing in
Anchor 0.30.x.

Your task is to write complete, production-ready Rust code for Solana programs.

Requirements:
1. Follow Anchor 0.30.x idioms and best practices
2. Use modern Rust (2021 edition)
3. Implement proper error handling
4. Include all necessary imports and use statements
5. Add inline documentation for complex logic
6. Use proper error types with human-readable messages

For each instruction handler:
- Create context struct with required accounts
- Define instruction data struct with Anchor derive
- Implement the handler function with proper access control
- Include precondition checks with appropriate errors

Ensure the code compiles and follows Rust conventions:
- Proper formatting (4 spaces)
- Use of Result types for fallible operations
- Event emission for important state changes
- Security checks (owner checks, signer verification)

Output format - return a JSON object mapping relative file paths to complete file contents.
All paths should be relative to the project root (e.g., "src/lib.rs", "src/instructions/mint.rs").
Example output:
```json
{
    "files": {
        "src/lib.rs": "...",
        "src/instructions/mod.rs": "...",
        "src/instructions/mint.rs": "..."
    }
}
```
"""


class CodeGenerator(BaseAgent):
    """Agent that generates Rust instruction implementations using LangChain."""

    @property
    def agent_name(self):
        return "code_generator"

    def _get_tools(self):
        """No file tools - agent returns files in state."""
        return []

    def _get_system_prompt(self):
        return SYSTEM_PROMPT

    def _format_state_for_agent(self, state: dict) -> str:
        """Format the token spec and existing files for the agent."""
        token_spec = state.get("interpreted_spec", {})
        existing_files = state.get("files", {})

        files_summary = "\n".join(f"- {path}" for path in existing_files)

        return f"""Generate Rust instruction implementations for:

Token: {token_spec.get("name", "Unknown")} ({token_spec.get("symbol", "UNK")})
Features: {token_spec.get("features", [])}

Existing files:
{files_summary}

Write complete Rust code for all instruction handlers. Return a JSON object with files mapping."""

    def _format_agent_result(self, state: dict, result: dict) -> dict:
        """Extract the generated code from agent output."""
        output = self._extract_output_from_result(result)
        files = self._extract_files_from_output(output)

        if files:
            updated_files = {**state.get("files", {}), **files}
            return {
                **state,
                "files": updated_files,
                "current_step": "static_validator",
            }

        return {
            **state,
            "error_message": f"Failed to extract generated code: {output}",
            "current_step": "code_generator",
        }
