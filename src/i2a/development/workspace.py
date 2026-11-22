import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WorkspaceFile:
    """Represents a file discovered in a workspace."""

    path: str
    name: str
    extension: str
    size_bytes: int


@dataclass
class WorkspaceAnalysis:
    """Contains information about an analyzed workspace."""

    root: str
    directories: list[str] = field(default_factory=list)
    files: list[WorkspaceFile] = field(default_factory=list)
    excluded_directories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "directories": self.directories,
            "files": [
                {
                    "path": item.path,
                    "name": item.name,
                    "extension": item.extension,
                    "size_bytes": item.size_bytes,
                }
                for item in self.files
            ],
            "excluded_directories": self.excluded_directories,
        }


class WorkspaceAnalyzer:
    """Safely inspects the structure of a selected project workspace."""

    EXCLUDED_DIRECTORIES = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".idea",
        ".vscode",
    }

    MAX_FILES = 5000
    MAX_DEPTH = 15

    def analyze(self, workspace_path: str | Path) -> WorkspaceAnalysis:
        """Analyze a workspace without modifying its contents."""

        root = Path(workspace_path).expanduser().resolve()

        if not root.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {root}"
            )

        if not root.is_dir():
            raise NotADirectoryError(
                f"Workspace must be a directory: {root}"
            )

        analysis = WorkspaceAnalysis(root=str(root))

        for current_path, directories, filenames in os.walk(
            root,
            followlinks=False,
        ):
            current = Path(current_path)
            depth = len(current.relative_to(root).parts)

            if depth >= self.MAX_DEPTH:
                directories.clear()

            excluded = [
                name
                for name in directories
                if name in self.EXCLUDED_DIRECTORIES
                or (current / name).is_symlink()
            ]

            analysis.excluded_directories.extend(
                str(current / name)
                for name in excluded
            )

            directories[:] = [
                name
                for name in directories
                if name not in self.EXCLUDED_DIRECTORIES
                and not (current / name).is_symlink()
            ]

            for directory in directories:
                analysis.directories.append(
                    str(current / directory)
                )

            for filename in filenames:
                file_path = current / filename

                if file_path.is_symlink():
                    continue

                try:
                    size = file_path.stat().st_size
                except OSError:
                    continue

                analysis.files.append(
                    WorkspaceFile(
                        path=str(file_path),
                        name=file_path.name,
                        extension=file_path.suffix.lower(),
                        size_bytes=size,
                    )
                )

                if len(analysis.files) >= self.MAX_FILES:
                    return analysis

        return analysis