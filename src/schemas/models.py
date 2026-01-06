"""Unified Pydantic models for the Solana smart contractor."""

from collections.abc import Callable
from enum import Enum

from pydantic import BaseModel, Field

# Constants
MAX_RETRIES = 1


class ContractFeature(str, Enum):
    """Supported contract features."""

    MINTABLE = "mintable"
    BURNABLE = "burnable"
    TRANSFERABLE = "transferable"
    FREEZABLE = "freezable"
    REVOKABLE = "revokable"
    PAUSABLE = "pausable"
    CAPPED = "capped"
    OWNABLE = "ownable"
    ACCESS_CONTROL = "access_control"
    INITIAL_SUPPLY = "initial_supply"


class TokenSpec(BaseModel):
    """Specification for a token contract."""

    name: str = Field(..., description="Full name of the token")
    symbol: str = Field(..., description="Token symbol (3-6 chars)")
    description: str | None = Field(default=None, description="Token description")
    decimals: int = Field(default=9, ge=0, le=9, description="Decimal places")
    features: list[ContractFeature] = Field(default_factory=list, description="List of features")
    initial_supply: int | None = Field(default=None, ge=0)

    class Config:
        use_enum_values = True


class GraphState(BaseModel):
    """State for the LangGraph workflow."""

    user_spec: str = Field(..., description="Original user specification")
    project_name: str | None = Field(default=None, description="Project name for anchor init")
    on_event: Callable[[str], None] | None = Field(default=None)
    interpreted_spec: TokenSpec | None = Field(default=None)
    files: dict[str, str] = Field(default_factory=dict)
    validation_passed: bool = Field(default=False)
    validation_errors: list[str] = Field(default_factory=list)
    build_success: bool = Field(default=False)
    build_logs: str | None = Field(default=None)
    final_artifact: str | None = Field(default=None)
    fix_attempted: bool = Field(default=False)
    retry_count: int = Field(default=0)
    project_root: str | None = Field(default=None)
    error_message: str | None = Field(default=None)
    test_mode: bool = Field(default=False)

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "GraphState":
        return cls(**data)


class ProjectFileSpec(BaseModel):
    """Specification for a project file."""

    path: str = Field(..., description="Relative path")
    content: str = Field(..., description="File contents")
    description: str | None = Field(default=None)


class DebuggerPatch(BaseModel):
    """Patch specification from debugger agent."""

    path: str = Field(..., description="File path")
    content: str = Field(..., description="New file content")
    reason: str | None = Field(default=None, description="Why this patch is needed")


class ProjectFile(BaseModel):
    """A single file in the project."""

    path: str = Field(..., description="Relative file path")
    content: str = Field(..., description="File contents")


class ProjectFiles(BaseModel):
    """Structured output for file generation from LLM."""

    files: list[ProjectFile] = Field(..., description="List of generated project files")
