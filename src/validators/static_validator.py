import re
from pathlib import Path

from src.utils.builder import Builder


class StaticValidator:
    """Static validation for Rust/Anchor smart contracts.

    Runs non-LLM checks: rustfmt, cargo check, etc.
    """

    def __init__(self, project_path: Path):
        """Initialize with project path.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path)
        self.builder = Builder(project_path)
        self.errors: list[str] = []

    def validate_rust_syntax(self, files: dict) -> bool:
        """Basic Rust syntax validation without compiler.

        Args:
            files: Dictionary of file path -> content

        Returns:
            True if syntax appears valid
        """
        rust_files = {k: v for k, v in files.items() if k.endswith(".rs")}

        for path, content in rust_files.items():
            # Check for common syntax issues
            if content.count("{") != content.count("}"):
                self.errors.append(f"{path}: Mismatched braces")
            if content.count("(") != content.count(")"):
                self.errors.append(f"{path}: Mismatched parentheses")
            if content.count("[") != content.count("]"):
                self.errors.append(f"{path}: Mismatched brackets")

            # Check for use statements
            if (
                "use anchor_lang" not in content
                and "use solana_program" not in content
                and not content.strip().startswith("//")
            ):
                self.errors.append(f"{path}: Missing anchor_lang or solana_program import")

        return len(self.errors) == 0

    def validate_anchor_structure(self, files: dict) -> bool:
        """Validate Anchor project structure.

        Args:
            files: Dictionary of file path -> content

        Returns:
            True if structure is valid
        """
        file_paths = list(files.keys())

        # Check for Anchor.toml
        has_anchor_toml = any("Anchor.toml" in p for p in file_paths)
        if not has_anchor_toml:
            self.errors.append("Missing Anchor.toml configuration")

        # Check for programs directory
        has_programs = any("programs" in p for p in file_paths)
        if not has_programs:
            self.errors.append("Missing programs/ directory")

        # Check for lib.rs
        has_lib_rs = any("lib.rs" in p for p in file_paths)
        if not has_lib_rs:
            self.errors.append("Missing programs/*/src/lib.rs")

        return len(self.errors) == 0

    def validate_cargo_toml(self, files: dict) -> bool:
        """Validate Cargo.toml files have proper SBF configuration.

        Args:
            files: Dictionary of file path -> content

        Returns:
            True if Cargo.toml is valid
        """
        cargo_files = {k: v for k, v in files.items() if k.endswith("Cargo.toml")}

        for path, content in cargo_files.items():
            # Check for required SBF configuration
            if "[dependencies]" not in content and "[lib]" not in content:
                self.errors.append(f"{path}: Missing expected sections")

            # Check for anchor-lang dependency
            if (
                "anchor-lang" not in content and "programs" in path  # Only check program Cargo.toml
            ):
                self.errors.append(f"{path}: Missing anchor-lang dependency")

        return len(self.errors) == 0

    def run_cargo_check(self) -> tuple[bool, str]:
        """Run cargo check --target sbf-solana-solana.

        Returns:
            Tuple of (success, output)
        """
        return self.builder.cargo_check_sbf()

    async def validate(self, files: dict) -> dict:
        """Run all static validation.

        Args:
            files: Dictionary of file path -> content

        Returns:
            Validation result dictionary
        """
        self.errors = []

        # Run local syntax checks
        self.validate_rust_syntax(files)
        self.validate_anchor_structure(files)
        self.validate_cargo_toml(files)

        # If we have errors from local checks, return early
        if self.errors:
            return {
                "passed": False,
                "errors": self.errors,
                "logs": "",
            }

        # Run cargo check for actual compilation verification
        success, output = self.run_cargo_check()

        if not success:
            # Parse and filter useful error messages
            error_lines = self._parse_errors(output)
            return {
                "passed": False,
                "errors": error_lines,
                "logs": output,
            }

        return {
            "passed": True,
            "errors": [],
            "logs": output,
        }

    def _parse_errors(self, output: str) -> list[str]:
        """Parse compiler output for error messages.

        Args:
            output: Compiler output

        Returns:
            List of error messages
        """
        errors = []

        # Match common error patterns
        error_patterns = [
            r"error\[([^\]]+)\]: ([^\n]+)",
            r"error: ([^\n]+)",
            r"--> ([^\n]+)",
        ]

        for line in output.split("\n"):
            for pattern in error_patterns:
                match = re.search(pattern, line)
                if match:
                    errors.append(line.strip())
                    break

        return errors[:20]  # Limit to 20 most relevant errors

    async def run(self, state: dict) -> dict:
        """Run static validation on project files.

        Args:
            state: Current workflow state (must contain 'files')

        Returns:
            Updated state with validation results
        """
        files = state.get("files", {})
        if not files:
            return {
                **state,
                "validation_passed": False,
                "validation_errors": ["No files to validate"],
                "current_step": "static_validator",
            }

        result = await self.validate(files)

        return {
            **state,
            "validation_passed": result["passed"],
            "validation_errors": result["errors"],
            "build_logs": result.get("logs", ""),
            "current_step": "build_contract" if result["passed"] else "debugger",
        }
