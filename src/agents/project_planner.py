"""Project Planner Agent - generates Anchor project scaffold using LangChain."""

import json

from src.agents.base import LLMOnlyAgent
from src.schemas.models import ProjectFiles

SYSTEM_PROMPT = """You are an expert Solana smart contract Rust developer. The Anchor project
has already been initialized with `anchor init`. Your job is to write the contract code
and tests.

Output a JSON object with a "files" array. Each file has:
- path: relative file path (e.g., "programs/project_name/src/lib.rs")
- content: complete file contents

Project structure:
- programs/{project_name}/src/lib.rs - Main program file (MODIFY THIS)
- programs/{project_name}/src/instructions/*.rs - Additional instruction files (OPTIONAL)
- programs/{project_name}/src/accounts.rs - Account structs (OPTIONAL)
- programs/{project_name}/src/errors.rs - Custom errors (OPTIONAL)
- tests/{project_name}.ts - Integration tests (CREATE THIS)

Requirements:
1. Replace the default lib.rs with complete contract code
2. Include declare_id!() with the program ID
3. Implement all instruction handlers in #[program] module
4. Create #[derive(Accounts)] structs for each instruction
5. Write integration tests in TypeScript using @coral-xyz/anchor

Split code into proper files for maintainability.
"""


class ProjectPlanner(LLMOnlyAgent):
    """Agent that generates Anchor project structure using LangChain."""

    @property
    def agent_name(self):
        return "project_planner"

    def _create_executor(self):
        """Create structured LLM for JSON output."""
        return self.llm.with_structured_output(ProjectFiles)

    def _get_system_prompt(self):
        return SYSTEM_PROMPT

    def _format_state_for_agent(self, state: dict) -> str:
        """Format the token spec for the agent."""
        token_spec = state.get("interpreted_spec", {})
        project_name = state.get("project_name", "my_token")
        spec_text = json.dumps(token_spec, indent=2)
        return f"Write contract code for project '{project_name}':\n\n{spec_text}"

    def _format_agent_result(self, state: dict, result: ProjectFiles) -> dict:
        """Format the structured response."""
        if result and result.files:
            # Convert list of ProjectFile to dict[str, str]
            files_dict = {f.path: f.content for f in result.files}
            return {
                **state,
                "files": files_dict,
                "current_step": "code_generator",
            }

        return {
            **state,
            "error_message": "Failed to generate project files",
            "current_step": "project_planner",
        }
