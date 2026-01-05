"""Project Planner Agent - generates Anchor project scaffold using LangChain."""

import json

from src.agents.base import BaseAgent
from src.schemas.models import TokenSpec

SYSTEM_PROMPT = """You are a Solana smart contract architect. Your job is to design a proper
Anchor project structure.

Project structure requirements:
1. Standard Anchor layout - program files go in src/ directory at project root
2. Separate files for each instruction (lib.rs, mod.rs, instructions/)
3. Cargo.toml at project root
4. Anchor.toml configuration at the root (will be placed in workspace root)
5. tests/ directory for integration tests

For each Rust file, generate complete, compilable code following:
- Anchor 0.30.x idioms
- Proper module organization (lib.rs exports modules)
- Each instruction in its own file under instructions/
- All necessary use statements and imports
- Error definitions if needed

Output format - return a JSON object mapping relative paths to complete file contents.
Anchor.toml should be at the root level (key: "Anchor.toml").
All other program files (Cargo.toml, src/, tests/) should use relative paths.
Example:
```json
{
    "files": {
        "Anchor.toml": "...",
        "Cargo.toml": "...",
        "src/lib.rs": "...",
        "src/instructions/mod.rs": "...",
        "src/instructions/mint.rs": "...",
        "tests/my_token.ts": "..."
    }
}
```
"""


class ProjectPlanner(BaseAgent):
    """Agent that generates Anchor project structure using LangChain."""

    @property
    def agent_name(self):
        return "project_planner"

    def _get_tools(self):
        """No file tools - agent returns files in state."""
        return []

    def _get_system_prompt(self):
        return SYSTEM_PROMPT

    def _format_state_for_agent(self, state: dict) -> str:
        """Format the token spec for the agent."""
        token_spec = state.get("interpreted_spec", {})
        spec_text = json.dumps(token_spec, indent=2)
        return f"Create Anchor project structure for:\n\n{spec_text}"

    def _format_agent_result(self, state: dict, result: dict) -> dict:
        """Extract the project structure from agent output."""
        output = self._extract_output_from_result(result)
        files = self._extract_files_from_output(output)

        if files or state.get("files"):
            files = files or state.get("files", {})
            return {
                **state,
                "files": files,
                "project_name": self._extract_project_name(files),
                "current_step": "code_generator",
            }

        return {
            **state,
            "error_message": f"Failed to extract project structure: {output}",
            "current_step": "project_planner",
        }

    def _extract_project_name(self, files: dict) -> str:
        """Extract project name from files dictionary."""
        for path in files:
            if path == "Anchor.toml":
                content = files[path]
                if "[cluster]" in content or "[provider]" in content:
                    for p in files:
                        if p.startswith("programs/") and "/src" in p:
                            parts = p.split("/")
                            if len(parts) >= 2:
                                return parts[1]
            if "programs/" in path:
                parts = path.split("/")
                if len(parts) >= 2:
                    return parts[1]

        return "my-project"
