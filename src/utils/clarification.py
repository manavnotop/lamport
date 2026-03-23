"""Interactive clarification utilities for vague specifications."""

import json

from rich.console import Console

from src.schemas.models import ClarifiedSpec, TokenType


def needs_clarification(spec: str, test_mode: bool = False) -> tuple[bool, str | None]:
    """Ask LLM if the spec needs clarification.

    Args:
        spec: The user's specification string
        test_mode: If True, skip LLM call and return False

    Returns:
        Tuple of (needs_clarification, reason)
    """
    if test_mode:
        return False, None

    try:
        from src.utils.llm_utils import get_langchain_llm
    except ImportError:
        return False, None

    system_prompt = (
        "Analyze this smart contract specification. "
        "Determine if we need more information from the user before generating code.\n\n"
        "Return JSON with:\n"
        '- "needs_clarification": true if the spec is vague or missing key details\n'
        '- "reason": a friendly message explaining what info is needed\n\n'
        "Be conservative - if spec mentions specific operations (mint, burn, transfer) "
        "and features (mintable, burnable), return false. "
        "Only return true if the spec is genuinely vague."
    )

    try:
        llm = get_langchain_llm(model="google/gemini-2.5-pro", temperature=0.1)
        from langchain_core.messages import HumanMessage

        response = llm.invoke([HumanMessage(content=f"{system_prompt}\n\nSpecification: {spec}")])
        content = response.content if hasattr(response, "content") else str(response)

        # Try to extract JSON from the response
        data = json.loads(content)
        return data.get("needs_clarification", False), data.get("reason")
    except (json.JSONDecodeError, AttributeError, KeyError):
        return False, None


def ask_clarification(console: Console, spec: str) -> ClarifiedSpec:
    """Ask clarifying questions using Rich console.

    Args:
        console: Rich Console instance
        spec: Original specification string

    Returns:
        ClarifiedSpec with user answers
    """
    clarified = ClarifiedSpec()

    console.print("\n[bold cyan]Let me clarify a few things:[/bold cyan]\n")

    # Question 1: Token type
    console.print("[yellow]1.[/yellow] What type of program is this?")
    console.print("   [dim]0[/dim] - Fungible token")
    console.print("   [dim]1[/dim] - Non-fungible token (NFT)")
    console.print("   [dim]2[/dim] - Semi-fungible token")
    console.print("   [dim]3[/dim] - Custom program (counter, escrow, vault, etc.)")

    choice = console.input("Select [0-3] or press Enter to skip: ").strip()
    if choice == "0":
        clarified.token_type = TokenType.FUNGIBLE
    elif choice == "1":
        clarified.token_type = TokenType.NON_FUNGIBLE
    elif choice == "2":
        clarified.token_type = TokenType.SEMI_FUNGIBLE
    elif choice == "3":
        clarified.token_type = TokenType.CUSTOM

    # Question 2: Operations
    console.print("\n[yellow]2.[/yellow] What operations do you need?")
    console.print("   [dim]comma-separated[/dim] e.g., mint, burn, transfer, initialize, increment")
    ops_input = console.input("Operations (or Enter to skip): ").strip()
    if ops_input:
        clarified.operations = [op.strip() for op in ops_input.split(",") if op.strip()]

    # Question 3: Features
    console.print("\n[yellow]3.[/yellow] Any special features?")
    console.print("   [dim]comma-separated[/dim] e.g., mintable, burnable, pausable, ownable")
    features_input = console.input("Features (or Enter to skip): ").strip()
    if features_input:
        clarified.features = [f.strip() for f in features_input.split(",") if f.strip()]

    # Question 4: Initial supply (for fungible tokens)
    if clarified.token_type == TokenType.FUNGIBLE:
        console.print("\n[yellow]4.[/yellow] Initial supply (for fungible tokens):")
        supply_input = console.input("Initial supply or Enter to skip: ").strip()
        if supply_input and supply_input.isdigit():
            clarified.initial_supply = int(supply_input)

    return clarified


def enrich_spec(spec: str, clarified: ClarifiedSpec) -> str:
    """Merge clarification into a rich natural language spec.

    Args:
        spec: Original specification string
        clarified: ClarifiedSpec with user answers

    Returns:
        Enriched specification string
    """
    parts = [spec]

    if clarified.token_type:
        parts.append(f"This is a {clarified.token_type.value} token/contract.")

    if clarified.operations:
        ops = ", ".join(clarified.operations)
        parts.append(f"Required operations: {ops}.")

    if clarified.features:
        features = ", ".join(clarified.features)
        parts.append(f"Features: {features}.")

    if clarified.initial_supply is not None:
        parts.append(f"Initial supply: {clarified.initial_supply}.")

    return " ".join(parts)
