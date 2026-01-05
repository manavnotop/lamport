"""Base agent class for LangChain-powered agents."""

import json
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_settings
from src.utils.llm_utils import create_agent_executor, get_langchain_llm
from src.utils.logging import log_llm_call


class BaseAgent(ABC):
    """Base class for LangChain-powered agents.

    Provides a consistent interface for state-based agent execution
    while leveraging LangChain's agent framework with tool calling.
    """

    def __init__(self):
        """Initialize the agent with LLM and tools."""
        self.settings = get_settings()
        self.llm = self._create_llm()
        self.tools = self._get_tools()
        self.executor = self._create_executor()

    @abstractmethod
    def _get_tools(self):
        """Return list of LangChain tools for this agent."""
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    def _create_llm(self):
        """Create the LangChain LLM for this agent."""
        model = getattr(self.settings, f"model_{self.agent_name}", "google/gemini-2.5-pro")
        return get_langchain_llm(model=model, temperature=0.1)

    def _create_executor(self):
        """Create the LangGraph agent executor with tools."""
        return create_agent_executor(
            llm=self.llm,
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
        )

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the agent name for config lookup."""
        pass

    async def run(self, state: dict) -> dict:
        """Run the agent with the current workflow state.

        Args:
            state: Current workflow state dict

        Returns:
            Updated state dict
        """
        # Extract relevant info from state for the agent
        input_text = self._format_state_for_agent(state)
        input_data = {
            "system_prompt": self._get_system_prompt(),
            "user_message": input_text,
        }

        try:
            result = self.executor.invoke({"messages": [{"role": "user", "content": input_text}]})
            agent_result = self._format_agent_result(state, result)

            log_llm_call(
                agent_name=self.agent_name,
                model=getattr(self.settings, f"model_{self.agent_name}", "unknown"),
                input_data=input_data,
                output_data={"content": agent_result.get("agent_output", "")},
                success=True,
            )

            return agent_result
        except Exception as e:
            log_llm_call(
                agent_name=self.agent_name,
                model=getattr(self.settings, f"model_{self.agent_name}", "unknown"),
                input_data=input_data,
                output_data={"error": str(e)},
                success=False,
                error=str(e),
            )
            return {
                **state,
                "error_message": str(e),
                "current_step": self.agent_name,
            }

    def _format_state_for_agent(self, state: dict) -> str:
        """Format the workflow state for the agent's consumption.

        Override in subclasses to provide agent-specific formatting.
        """
        return str(state)

    def _format_agent_result(self, state: dict, result: dict) -> dict:
        """Format the agent result back into workflow state.

        Override in subclasses to extract structured output from agent.
        """
        # Extract output from the last assistant message
        output = self._extract_output_from_result(result)

        return {
            **state,
            "agent_output": output,
            "current_step": self._get_next_step(state),
        }

    def _extract_output_from_result(self, result: dict) -> str:
        """Extract text output from common result formats (LangGraph/Chain)."""
        if "output" in result and result["output"]:
            return result["output"]

        messages = result.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, "content"):
                return msg.content
            elif isinstance(msg, dict) and msg.get("content"):
                return msg["content"]
        return ""

    def _extract_json_from_output(self, output: str) -> dict:
        """Extract JSON from potential markdown blocks in LLM output."""
        try:
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                json_str = output[json_start:json_end].strip()
                return json.loads(json_str)
            elif "{" in output and "}" in output:
                # Direct JSON attempt
                start = output.find("{")
                end = output.rfind("}") + 1
                return json.loads(output[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return {}

    def _extract_files_from_output(self, output: str) -> dict[str, str]:
        """Common helper to extract file map from JSON output."""
        data = self._extract_json_from_output(output)
        if not data:
            return {}

        if "files" in data:
            return data["files"]
        # Handle case where the JSON is the file map directly
        if any(isinstance(v, str) for v in data.values()):
            return data
        return {}

    def _get_next_step(self, state: dict) -> str:
        """Return the next step in the workflow."""
        return self._get_default_next_step()

    def _get_default_next_step(self) -> str:
        """Return the default next step. Override in subclasses."""
        return "complete"


class LLMOnlyAgent(BaseAgent):
    """Base class for agents that don't need tools (just LLM calls).

    Use this for agents like SpecInterpreter that only need to
    generate structured output without file operations.
    """

    def _get_tools(self):
        """No tools needed for LLM-only agents."""
        return []

    def _create_executor(self):
        """Create a simple chain instead of agent executor."""
        return self.llm

    async def run(self, state: dict) -> dict:
        """Run the LLM-only agent."""
        input_text = self._format_state_for_agent(state)

        input_data = {
            "system_prompt": self._get_system_prompt(),
            "user_message": input_text,
        }

        try:
            response = self.executor.invoke(
                [
                    SystemMessage(content=self._get_system_prompt()),
                    HumanMessage(content=input_text),
                ]
            )

            output_data = {
                "content": response.content if hasattr(response, "content") else str(response),
            }

            log_llm_call(
                agent_name=self.agent_name,
                model=self.settings.model_spec_interpreter,
                input_data=input_data,
                output_data=output_data,
                success=True,
            )

            return self._format_agent_result(state, response)
        except Exception as e:
            output_data = {"error": str(e)}
            log_llm_call(
                agent_name=self.agent_name,
                model=self.settings.model_spec_interpreter,
                input_data=input_data,
                output_data=output_data,
                success=False,
                error=str(e),
            )
            return {
                **state,
                "error_message": str(e),
                "current_step": self.agent_name,
            }

    def _format_agent_result(self, state: dict, response) -> dict:
        """Format LLM response into workflow state."""
        content = response.content if hasattr(response, "content") else str(response)
        return self._extract_state_from_response(state, content)

    @abstractmethod
    def _extract_state_from_response(self, state: dict, response: str) -> dict:
        """Extract structured data from LLM response and update state."""
        pass
