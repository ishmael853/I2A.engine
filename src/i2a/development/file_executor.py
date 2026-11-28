import hashlib
import os
import shutil
import tempfile
import json
from datetime import datetime, timezone
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

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate the SHA-256 checksum of a file."""

        checksum = hashlib.sha256()

        with file_path.open("rb") as file:
            for chunk in iter(
                lambda: file.read(65536),
                b"",
            ):
                checksum.update(chunk)

        return checksum.hexdigest()


    def _checksum_path(self, backup_path: Path) -> Path:
        """Return the path used to store a backup checksum."""

        return backup_path.with_name(
            f"{backup_path.name}.sha256"
        )

    def _verify_backup(self, backup_path: Path) -> None:
        """Verify a backup against its stored SHA-256 checksum."""

        checksum_path = self._checksum_path(backup_path)

        if not backup_path.is_file():
            raise FileNotFoundError(
                f"Backup file is missing: {backup_path}"
            )

        if not checksum_path.is_file():
            raise FileNotFoundError(
                f"Backup checksum is missing: {checksum_path}"
            )

        expected_checksum = checksum_path.read_text(
            encoding="utf-8"
        ).strip()

        if len(expected_checksum) != 64:
            raise OSError(
                f"Invalid backup checksum: {checksum_path}"
            )

        if any(
            character not in "0123456789abcdef"
            for character in expected_checksum.lower()
        ):
            raise OSError(
                f"Invalid backup checksum: {checksum_path}"
            )

        actual_checksum = self._calculate_checksum(backup_path)

        if actual_checksum != expected_checksum:
            raise OSError(
                f"Backup integrity verification failed: {backup_path}"
            )


    def _create_backup(self, target: Path) -> Path:
        """Create a backup and store its checksum and creation time."""

        backup_path = target.with_name(
            f"{target.name}.i2a-backup"
        )

        checksum_path = self._checksum_path(backup_path)

        metadata_path = backup_path.with_name(
            f"{backup_path.name}.metadata.json"
        )

        if backup_path.exists():
            raise FileExistsError(
                f"Backup already exists: {backup_path}"
            )

        if checksum_path.exists():
            raise FileExistsError(
                f"Backup checksum already exists: {checksum_path}"
            )

        if metadata_path.exists():
            raise FileExistsError(
                f"Backup metadata already exists: {metadata_path}"
            )

        shutil.copy2(target, backup_path)

        try:
            checksum = self._calculate_checksum(backup_path)

            checksum_path.write_text(
                checksum,
                encoding="utf-8",
            )

            metadata = {
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            metadata_path.write_text(
                json.dumps(metadata, indent=4),
                encoding="utf-8",
            )

        except OSError:
            backup_path.unlink(missing_ok=True)
            checksum_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)
            raise

        return backup_path

    # TRANSACTION STYLE ROLLBACK
    # restore modified files from their backups
    # remove files created by the failed transaction
    # report which operations were rolled back 
    # preserve backups for recovery

    def _restore_backup(self, target: Path, backup: Path) -> None:
        """Restore a file from its backup."""

        self._verify_backup(backup)

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}",
                suffix=".i2a-restore",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)

                with backup.open("rb") as backup_files:
                    shutil.copyfileobj(backup_files, temporary_file)

                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            shutil.copystat(backup, temporary_path)
            os.replace(temporary_path, target)

        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _rollback_operations(self, completed_operations: list) -> list:
        """Reverse previously completed file operations."""

        errors = []

        for change, target, backup_path in reversed(
            completed_operations
        ):
            try:
                if change.operation == "create":
                    if target.exists():
                        target.unlink()

                elif backup_path is not None:
                    if not backup_path.exists():
                        raise FileNotFoundError(
                            f"Backup file is missing: {backup_path}"
                        )

                    self._restore_backup(target, backup_path)

            except OSError as error:
                errors.append({
                    "file_path": change.file_path,
                    "error": str(error),
                })

        return errors

    def _atomic_write(self, target: Path, content: str) -> None:
        """Write content safely using a temporary file."""

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".i2a-tmp",
                delete=False
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, target)

        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

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

                backup_path = target.with_name(
                    f"{target.name}.i2a-backup"
                )

                if backup_path.exists():
                    raise FileExistsError(
                        f"Backup already exists: {backup_path}"
                    )

            operations.append((change, target))

        results = []
        completed_operations = []

        for change, target in operations:
            backup_path = None
            created_target = False

            try:
                if change.operation == "create":
                    file = target.open(
                        "x",
                        encoding="utf-8",
                        newline="",
                    )
                    created_target = True

                    with file:
                        file.write(change.content)

                else:
                    backup_path = self._create_backup(target)
                    self._atomic_write(target, change.content)

                completed_operations.append(
                    (change, target, backup_path)
                )

                results.append({
                    "file_path": change.file_path,
                    "operation": change.operation,
                    "status": "success",
                })

            except OSError as error:

                rollback_errors = []

                if created_target and target.exists():
                    try:
                        target.unlink()
                    except OSError as cleanup_error:
                        rollback_errors.append({
                            "file_path": change.file_path,
                            "error": str(cleanup_error),
                        })

                rollback_errors.extend(
                    self._rollback_operations(completed_operations)
                )

                for result in results:
                    if result["status"] == "success":
                        result["status"] = "rolled_back"

                for rollback_error in rollback_errors:
                    for result in results:
                        if (
                            result["file_path"] == rollback_error["file_path"]
                            and result["status"] == "rolled_back"
                        ):
                            result["status"] = "rollback_failed"
                            break

                results.append({
                    "file_path": change.file_path,
                    "operation": change.operation,
                    "status": "failed",
                    "error": str(error),
                })

                for rollback_error in rollback_errors:
                    results.append({
                        "file_path": rollback_error["file_path"],
                        "operation": "rollback",
                        "status": "rollback_failed",
                        "error": rollback_error["error"],
                    })

                    break

        return {
            "project_name": approval.proposal.project_name,
            "workspace": str(workspace),
            "results": results,
        }