"""Spec Interpreter Agent - converts natural language to structured TokenSpec using LangChain."""

import json
import re

from src.agents.base import LLMOnlyAgent
from src.schemas.models import TokenSpec

SYSTEM_PROMPT = """You are a Solana smart contract specification interpreter.
Your job is to convert natural language specifications into a structured TokenSpec.

Supported features:
- mintable: Token can be minted by owner
- burnable: Token can be burned by holder
- transferable: Token can be transferred between accounts
- freezable: Owner can freeze accounts
- revokable: Owner can revoke (blacklist) accounts
- pausable: Owner can pause all transfers
- capped: Token has maximum supply
- ownable: Has ownership management
- access_control: Has role-based access control

Output format: JSON only, no markdown, matching this schema:
{
    "name": "Token Name",
    "symbol": "SYM",
    "description": "Optional description",
    "decimals": 9,
    "features": ["mintable", "transferable", ...],
    "initial_supply": null or number
}

If a feature requires minting and no initial_supply is specified, set initial_supply to null.
If features are unclear from the spec, make reasonable assumptions and document them in description.
"""


class SpecInterpreter(LLMOnlyAgent):
    """Agent that interprets natural language specifications using LangChain."""

    def __init__(self, test_mode: bool = False):
        """Initialize SpecInterpreter agent.

        Args:
            test_mode: If True, use mock LLM for testing
        """
        super().__init__()
        self.test_mode = test_mode
        if test_mode:
            from src.utils.llm_utils import MockLLM

            self.llm = MockLLM(model="mock-spec-interpreter")

    @property
    def agent_name(self) -> str:
        return "spec_interpreter"

    def _get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def _format_state_for_agent(self, state: dict) -> str:
        """Extract user spec from state for the agent."""
        user_spec = state.get("user_spec", "")
        if not user_spec:
            return "Error: No user specification provided"
        return f"Interpret this specification:\n\n{user_spec}"

    def _extract_state_from_response(self, state: dict, response: str) -> dict:
        """Parse the LLM response and extract TokenSpec."""
        try:
            # Clean up response if it has markdown formatting
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()

            data = json.loads(clean_response)
            token_spec = TokenSpec(**data)

            # Generate project_name from token name
            name = re.sub(r"[^a-z0-9]+", "_", token_spec.name.lower()).strip("_")[:32]
            if not name:
                name = "solana_contract"

            return {
                **state,
                "interpreted_spec": token_spec.model_dump(),
                "project_name": name,
                "current_step": "project_planner",
            }
        except (json.JSONDecodeError, ValueError) as e:
            return {
                **state,
                "error_message": f"Failed to parse spec interpretation: {e}\nRaw: {response}",
                "current_step": "spec_interpreter",
            }
