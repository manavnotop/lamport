"""File operations for reading and writing project files."""

import shutil
from pathlib import Path


class FileOps:
    """Utility class for file operations with security and atomic writes."""

    def __init__(self, base_path: Path):
        """Initialize with base path for file operations."""
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, rel_path: str) -> Path:
        """Resolve path with traversal protection."""
        path = (self.base_path / rel_path).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise ValueError(f"Path traversal detected: {rel_path}")
        return path

    def write_files(self, files: dict[str, str]) -> None:
        """Write multiple files atomically.

        Args:
            files: Dictionary mapping relative paths to file contents
        """
        for rel_path, content in files.items():
            file_path = self._resolve(rel_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write with temp file
            tmp = file_path.with_suffix(file_path.suffix + ".tmp")
            tmp.write_text(content, encoding="utf-8", newline="\n")
            try:
                tmp.replace(file_path)
            except OSError:
                # Windows fallback: file might be open
                shutil.move(str(tmp), str(file_path))

    def read_file(self, rel_path: str) -> str:
        """Read a file from the project directory.

        Args:
            rel_path: Relative path from base directory

        Returns:
            File contents as string
        """
        file_path = self._resolve(rel_path)
        return file_path.read_text(encoding="utf-8")

    def read_all_files(self) -> dict[str, str]:
        """Read all project files efficiently.

        Returns:
            Dictionary mapping relative paths to file contents
        """
        files = {}
        # Only scan relevant file types
        for pattern in ["*.toml", "*.rs", "*.ts", "*.json"]:
            for path in self.base_path.rglob(pattern):
                if path.is_file():
                    rel_path = str(path.relative_to(self.base_path))
                    files[rel_path] = path.read_text(encoding="utf-8")
        return files

    def apply_patches(self, patches: dict[str, str]) -> None:
        """Apply file patches atomically.

        Args:
            patches: Dictionary mapping relative paths to new content
        """
        for rel_path, content in patches.items():
            file_path = self._resolve(rel_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = file_path.with_suffix(file_path.suffix + ".tmp")
            tmp.write_text(content, encoding="utf-8", newline="\n")
            try:
                tmp.replace(file_path)
            except OSError:
                # Windows fallback: file might be open
                shutil.move(str(tmp), str(file_path))

    def get_project_structure(self) -> dict[str, dict]:
        """Get the project structure as a nested dictionary.

        Returns:
            Nested dictionary representing file structure
        """
        structure: dict[str, dict] = {}
        for path in sorted(self.base_path.rglob("*")):
            if path.is_file():
                parts = path.relative_to(self.base_path).parts
                current = structure
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                # Add file info
                current[parts[-1]] = {"type": "file", "size": path.stat().st_size}
        return structure

    def cleanup(self) -> None:
        """Remove the project directory and all contents."""
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
