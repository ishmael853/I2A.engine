from pathlib import Path

from i2a.development.backup_cleanup import BackupCleanupApproval
from i2a.development.backup_manager import BackupManager


class BackupCleanupExecutor:
    """Safely removes approved orphaned checksum files."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.backup_manager = BackupManager(workspace_path)
        self.workspace = self.backup_manager.workspace

    def execute(self, approval: BackupCleanupApproval) -> dict:
        """Execute an approved backupcleanup proposal."""

        if not isinstance(approval, BackupCleanupApproval):
            raise TypeError(
                "Execute a BackupCleanupApproval object."
            )

        if approval.status != BackupCleanupApproval.APPROVED:
            raise ValueError(
                "Backup cleanup requires explicit approval."
            )

        if Path(approval.proposal.workspace).resolve() != self.workspace:
            raise ValueError(
                "Cleanup proposal belongs to a different workspace."
            )

        results = {
            "successful": [],
            "failed": [],
        }

        for relative_path in approval.proposal.files:
            try:
                path = self._validate_checksum_path(relative_path)

                backup_path = Path(
                    str(path)[:-len(".sha256")]
                )

                if backup_path.is_file():
                    raise ValueError(
                        "Checksum still has a matching backup file."
                    )

                path.unlink()

                results["successful"].append(relative_path)

            except (OSError, ValueError) as error:
                results["failed"].append({
                    "path": relative_path,
                    "reason": str(error),
                })

        return results

    def _validate_checksum_path(self, relative_path: str) -> Path:
        """Validate a proposed checksum path before deletion."""

        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Invalid cleanup path.")

        relative = Path(relative_path)

        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Unsafe cleanup path.")

        if relative.suffix != ".sha256":
            raise ValueError("Only checksum files can be removed.")

        target = self.workspace / relative
        current = self.workspace

        for part in relative.parts:
            current = current / part

            if current.is_symlink():
                raise ValueError("Symbolic links are not allowed.")

        resolved = target.resolve()

        if not resolved.is_relative_to(self.workspace):
            raise ValueError("cleanup path escapes the workspace.")

        if not resolved.is_file():
            raise ValueError("Checksum file does not exist.")

        return resolved