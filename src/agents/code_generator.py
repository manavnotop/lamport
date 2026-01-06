"""Code Generator Agent - writes Rust instruction handlers using LangChain."""

from src.agents.base import LLMOnlyAgent
from src.schemas.models import ProjectFiles

SYSTEM_PROMPT = """You are an expert Solana smart contract Rust developer specializing in
Anchor 0.30.x. The Anchor project is already initialized. Your task is to write
complete, production-ready Rust code for Solana programs.

Output a JSON object with a "files" array. Each file has:
- path: relative file path (e.g., "programs/project/src/lib.rs")
- content: complete file contents

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

Split code into proper files:
- programs/{project}/src/lib.rs - Main module with #[program] and declare_id!
- programs/{project}/src/instructions/*.rs - Each instruction handler
- programs/{project}/src/accounts.rs - Account structs
- programs/{project}/src/errors.rs - Custom error types
- programs/{project}/src/events.rs - Event definitions
"""


class CodeGenerator(LLMOnlyAgent):
    """Agent that generates Rust instruction implementations using LangChain."""

    @property
    def agent_name(self):
        return "code_generator"

    def _create_executor(self):
        """Create structured LLM for JSON output."""
        return self.llm.with_structured_output(ProjectFiles)

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

Write complete Rust code for all instruction handlers. Split into proper files."""

    def _format_agent_result(self, state: dict, result: ProjectFiles) -> dict:
        """Format the structured response."""
        if result and result.files:
            # Convert list of ProjectFile to dict[str, str]
            files_dict = {f.path: f.content for f in result.files}
            updated_files = {**state.get("files", {}), **files_dict}
            return {
                **state,
                "files": updated_files,
                "current_step": "static_validator",
            }

        return {
            **state,
            "error_message": "Failed to generate code",
            "current_step": "code_generator",
        }
