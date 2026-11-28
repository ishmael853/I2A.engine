from pathlib import Path

from i2a.development.backup_manager import BackupManager
from i2a.development.retention_approval import BackupRetentionApproval


class BackupRetentionExecutor:
    """Safely removes expired backups after explicit approval."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.backup_manager = BackupManager(workspace_path)
        self.workspace = self.backup_manager.workspace

    def execute(self, approval: BackupRetentionApproval) -> dict:
        """Execute an approved backup retention proposal."""

        if not isinstance(approval, BackupRetentionApproval):
            raise TypeError(
                "Execute a BackupRetentionApproval object."
            )

        if approval.status != BackupRetentionApproval.APPROVED:
            raise ValueError(
                "Backup retention requires explicit approval."
            )

        if Path(approval.proposal.workspace).resolve() != self.workspace:
            raise ValueError(
                "Retention proposal belongs to a different workspace."
            )

        results = {
            "successful": [],
            "failed": [],
        }

        for relative_path in approval.proposal.backups:
            try:
                backup_path = self._validate_backup_path(
                    relative_path
                )

                checksum_path = backup_path.with_name(
                    f"{backup_path.name}.sha256"
                )

                metadata_path = backup_path.with_name(
                    f"{backup_path.name}.metadata.json"
                )

                self._validate_sidecar_path(checksum_path)
                self._validate_sidecar_path(metadata_path)

                self.backup_manager.verify_backup(
                    Path(relative_path)
                )

                checksum_path.unlink()
                metadata_path.unlink()
                backup_path.unlink()

                results["successful"].append(relative_path)

            except (OSError, ValueError) as error:
                results["failed"].append({
                    "path": relative_path,
                    "reason": str(error),
                })
        return results

    def _validate_backup_path(
            self,
            relative_path: str,
    ) -> Path:
        """Validate a backup path before removal."""

        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Invalid backup path.")

        relative = Path(relative_path)

        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Unsafe backup path.")

        if not relative.name.endswith(".i2a-backup"):
            raise ValueError("Only backup files can be removed.")

        current = self.workspace

        for part in relative.parts:
            current = current / part

            if current.is_symlink():
                raise ValueError("Symbolic links are not allowed.")

        resolved = (self.workspace / relative).resolve()

        if not resolved.is_relative_to(self.workspace):
            raise ValueError("Backup path escapes the workspace.")

        if not resolved.is_file():
            raise FileNotFoundError("Backup file does not exist.")

        return resolved

    def _validate_sidecar_path(self, path: Path) -> Path:
        """Validate a checksum or metadata sidecar before removal."""

        current = self.workspace

        try:
            relative = path.relative_to(self.workspace)
        except ValueError:
            raise ValueError(
                "Sidecar path escapes the workspace."
            )

        for part in relative.parts:
            current = current / part

            if current.is_symlink():
                raise ValueError(
                    "Symbolic links are not allowed."
                )

        resolved = path.resolve()

        if not resolved.is_relative_to(self.workspace):
            raise ValueError(
                "Sidecar path escapes the workspace."
            )

        if not resolved.is_file():
            raise FileNotFoundError(
                "Backup sidecar file does not exist."
            )

        return resolved