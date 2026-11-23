
from pathlib import Path, PurePosixPath, PureWindowsPath

from i2a.development.approval import ProposalApproval
from i2a.development.proposal_validator import ProposalValidator


class FileChangeExecutor:
    """Applies approved file changes inside a selected workspace."""

    def __init__(
        self,
        validator: ProposalValidator | None = None,
    ) -> None:
        self.validator = validator or ProposalValidator()

    def _resolve_target(
        self,
        workspace: Path,
        file_path: str,
    ) -> Path:
        """Resolve a file path and ensure it stays inside the workspace."""

        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError("File path cannot be empty.")

        normalized = file_path.replace("\\", "/")
        relative_path = PurePosixPath(normalized)
        windows_path = PureWindowsPath(file_path)

        if (
            relative_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or ".." in relative_path.parts
        ):
            raise ValueError("Unsafe file path.")

        if not relative_path.parts:
            raise ValueError("Invalid file path.")

        target = workspace.joinpath(*relative_path.parts)

        current = workspace

        for part in relative_path.parts:
            current = current / part

            if current.is_symlink():
                raise ValueError(
                    "Symbolic links are not allowed in file paths."
                )

        resolved = target.resolve()

        if not resolved.is_relative_to(workspace):
            raise ValueError(
                "File path escapes the selected workspace."
            )

        return resolved

    def execute(
        self,
        approval: ProposalApproval,
        workspace_path: str | Path,
    ) -> dict:
        """Apply a previously approved development proposal."""

        if not isinstance(approval, ProposalApproval):
            raise TypeError(
                "Expected a ProposalApproval object."
            )

        if approval.status != ProposalApproval.APPROVED:
            raise PermissionError(
                "The development proposal has not been approved."
            )

        self.validator.validate(approval.proposal)

        workspace = Path(workspace_path).expanduser().resolve()

        if not workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace must be a directory: {workspace}"
            )

        operations = []

        # Validate every target before changing any files.
        for change in approval.proposal.changes:
            target = self._resolve_target(
                workspace,
                change.file_path,
            )

            if not target.parent.is_dir():
                raise FileNotFoundError(
                    f"Parent directory does not exist: {target.parent}"
                )

            if change.operation == "create":
                if target.exists():
                    raise FileExistsError(
                        f"File already exists: {target}"
                    )

            elif change.operation == "modify":
                if not target.is_file():
                    raise FileNotFoundError(
                        f"File to modify does not exist: {target}"
                    )

            operations.append((change, target))

        results = []

        for change, target in operations:
            try:
                if change.operation == "create":
                    with target.open(
                        "x",
                        encoding="utf-8",
                        newline="",
                    ) as file:
                        file.write(change.content)

                else:
                    target.write_text(
                        change.content,
                        encoding="utf-8",
                    )

                results.append({
                    "file_path": change.file_path,
                    "operation": change.operation,
                    "status": "success",
                })

            except OSError as error:
                results.append({
                    "file_path": change.file_path,
                    "operation": change.operation,
                    "status": "failed",
                    "error": str(error),
                })

        return {
            "project_name": approval.proposal.project_name,
            "workspace": str(workspace),
            "results": results,
        }
