"""Unified LLM utilities for LangChain and Mock providers."""

from src.config import get_settings


def get_langchain_llm(
    model: str | None = None,
    temperature: float = 0.1,
):
    """Get a LangChain-compatible LLM for OpenRouter."""
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    api_key = settings.openrouter_api_key

    return ChatOpenAI(
        model=model or "google/gemini-2.5-pro",
        temperature=temperature,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/solana-agent/cli",
            "X-Title": "Solana Smart Contract Generator",
        },
    )


def create_agent_executor(llm, tools, system_prompt: str):
    """Create a LangGraph prebuilt ReAct agent."""
    from langgraph.prebuilt import create_react_agent

    return create_react_agent(llm, tools, prompt=system_prompt)


class MockLLM:
    """Mock LLM for testing without API calls."""

    def __init__(self, model: str = "mock"):
        self.model = model

    def invoke(self, messages):
        from langchain_core.messages import AIMessage

        # Simple rule-based mock responses
        content = "mock response"
        for msg in messages:
            msg_content = msg.content if hasattr(msg, "content") else str(msg)
            if "TokenSpec" in msg_content or "Interpret this" in msg_content:
                content = '{"name": "Mock Token", "symbol": "MCK", "decimals": 9, "features": ["mintable"]}'
            elif "Anchor project structure" in msg_content:
                content = '{"files": {"Anchor.toml": "[workspace]", "src/lib.rs": "// mock"}}'

        return AIMessage(content=content)

    async def ainvoke(self, messages):
        return self.invoke(messages)
