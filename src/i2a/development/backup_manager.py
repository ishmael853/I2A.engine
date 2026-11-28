import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from i2a.development.backup_health import BackupHealthReport

class BackupManager:
    """Manages I2A development backup files."""

    BACKUP_SUFFIX = ".i2a-backup"
    CHECKSUM_SUFFIX = ".sha256"

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace = Path(workspace_path).expanduser().resolve()

        if not self.workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {self.workspace}"
            )

        if not self.workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace must be a directory: {self.workspace}"
            )

    def _resolve_path(self, file_path: str | Path) -> Path:
        """Resolve a path and ensure it stays inside the workspace."""

        path = Path(file_path)

        if path.is_absolute():
            raise ValueError("Absolute paths are not allowed.")

        if ".." in path.parts:
            raise ValueError("Path traversal is not allowed.")

        target = self.workspace / path

        current = self.workspace

        for part in path.parts:
            current = current / part

            if current.is_symlink():
                raise ValueError(
                    "Symbolic links are not allowed."
                )

        resolved = target.resolve()

        if not resolved.is_relative_to(self.workspace):
            raise ValueError(
                "Path escapes the selected workspace."
            )

        return resolved

    def list_backups(self) -> list[Path]:
        """Find all I2A backup files inside the workspace."""

        backups = []

        for backup_path in self.workspace.rglob("*"):
            if backup_path.is_symlink():
                continue

            if not backup_path.is_file():
                continue


            if backup_path.name.endswith(self.BACKUP_SUFFIX):
                backups.append(
                    backup_path.relative_to(self.workspace)
                )

        return sorted(backups)

    def _checksum_path(self, backup_path: Path) -> Path:
        """Return the checksum sidecar path for a backup."""

        return backup_path.with_name(
            f"{backup_path.name}{self.CHECKSUM_SUFFIX}"
        )

    def verify_backup(self, file_path: str | Path) -> dict:
        """Verify a backup using its stored SHA-256 checksum."""

        backup_path = self._resolve_path(file_path)
        checksum_path = self._checksum_path(backup_path)

        if not backup_path.name.endswith(self.BACKUP_SUFFIX):
            raise ValueError(
                "The selected file is not an I2A backup."
            )

        if checksum_path.is_symlink():
            raise ValueError(
                "Symbolic link checksum files are not allowed."
            )

        if not backup_path.is_file():
            raise FileNotFoundError(
                f"Backup file is missing: {backup_path}"
            )

        if not checksum_path.is_file():
            raise FileNotFoundError(
                f"Backup checksum is missing: {checksum_path}"
            )


        checksum = hashlib.sha256()

        with backup_path.open("rb") as file:
            for chunk in iter(
                lambda: file.read(65536),
                b"",
            ):
                checksum.update(chunk)

        expected = checksum_path.read_text(
            encoding="utf-8"
        ).strip().lower()

        actual = checksum.hexdigest()

        if (
            len(expected) != 64
            or any(
                character not in "0123456789abcdef"
                for character in expected
            )
        ):
            raise OSError(
                f"Invalid backup checksum: {checksum_path}"
            )

        if actual != expected:
            raise OSError(
                f"Backup integrity verification failed: {backup_path}"
            )

        return {
            "backup": str(backup_path),
            "checksum": actual,
            "valid": True
        }

    def inspect_backups(self) -> list[dict]:
        """Inspect every discovered backup and reports its integrity."""

        report = []

        for backup_path in self.list_backups():
            try:
                result = self.verify_backup(backup_path)
                report.append({
                    "backup": str(backup_path),
                    "status": "valid",
                    "checksum": result["checksum"],
                })

            except (OSError, ValueError) as error:
                report.append({
                    "backup": str(backup_path),
                    "status": "invalid",
                    "error": str(error),
                })

        return report

    def find_orphaned_files(self) -> list[dict]:
        """Find backup files and checksum files without matching partners."""

        orphaned = []

        for backup_path in self.list_backups():
            absolute_backup_path = self._resolve_path(backup_path)
            checksum_path = self._checksum_path(absolute_backup_path)

            if not checksum_path.is_file():
                orphaned.append({
                    "path": str(backup_path),
                    "type": "backup_without_checksum",
                })

        for checksum_path in self.workspace.rglob("*"):
            if checksum_path.is_symlink():
                continue

            if not checksum_path.is_file():
                continue


            if not checksum_path.name.endswith(
                f"{self.BACKUP_SUFFIX}{self.CHECKSUM_SUFFIX}"
            ):
                continue

            backup_path = checksum_path.with_name(
                checksum_path.name[
                    :-len(self.CHECKSUM_SUFFIX)
                ]
            )

            if not backup_path.is_file():
                orphaned.append({
                    "path": str(
                        checksum_path.relative_to(self.workspace)
                    ),
                    "type": "checksum_without_backup",
                })

        return orphaned

    def get_backup_ages(self) -> list[dict]:
        """Return the age and creation timestamp of each backup."""

        now = datetime.now(timezone.utc)
        results = []

        for backup_path in self.list_backups():
            absolute_backup_path = self._resolve_path(backup_path)

            metadata_path = absolute_backup_path.with_name(
                f"{absolute_backup_path.name}.metadata.json"
            )

            if metadata_path.is_symlink():
                results.append({
                    "backup": str(backup_path),
                    "status": "invalid",
                    "error": "Symbolic link metadata is not allowed.",
                })
                continue

            if not metadata_path.is_file():
                results.append({
                    "backup": str(backup_path),
                    "status": "missing_metadata",
                })
                continue

            try:
                metadata = json.loads(
                    metadata_path.read_text(encoding="utf-8")
                )

                created_at = datetime.fromisoformat(
                    metadata["created_at"]
                )

                if created_at.tzinfo is None:
                    raise ValueError(
                        "Backup creation timestamp must include a timezone."
                    )

                age_seconds = (
                    now - created_at.astimezone(timezone.utc)
                ).total_seconds()

                if age_seconds < 0:
                    raise ValueError(
                        "Backup creation timestamp is in the future."
                    )

                results.append({
                    "backup": str(backup_path),
                    "status": "valid",
                    "created_at": created_at.isoformat(),
                    "age_seconds": age_seconds,
                })

            except (
                OSError,
                ValueError,
                TypeError,
                KeyError,
            ) as error:
                results.append({
                    "backup": str(backup_path),
                    "status": "invalid",
                    "error": str(error),
                })

        return results

    def find_expired_backup(
            self,
            max_age_days: int,
    ) -> list[dict]:
        """Find backups that exceed the configured retention period."""

        if isinstance(max_age_days, bool) or not isinstance(
            max_age_days, int
        ):
            raise TypeError(
                "Maximum backup age must be an integer."
            )

        if max_age_days < 1:
            raise ValueError(
                "Maximum backup age must be atleast one day."
            )

        expired = []
        maximum_age_seconds = max_age_days * 24 * 60 * 60

        for item in self.get_backup_ages():
            if item["status"] != "valid":
                continue

            if item["age_seconds"] > maximum_age_seconds:
                expired.append(item)

        return expired

    def create_health_report(self) -> BackupHealthReport:
        """Create a summary of backup health."""

        inspections = self.inspect_backups()
        orphaned_files = self.find_orphaned_files()

        valid_backups = sum(
            item["status"] == "valid"
            for item in inspections
        )

        invalid_backups = sum(
            item["status"] == "invalid"
            for item in inspections
        )

        backups_without_checksums = [
            item["path"]
            for item in orphaned_files
            if item["type"] == "backup_without_checksum"
        ]

        checksums_without_backups = [
            item["path"]
            for item in orphaned_files
            if item["type"] == "checksum_without_backup"
        ]

        return BackupHealthReport(
            workspace=str(self.workspace),
            total_backups=len(inspections),
            valid_backups=valid_backups,
            invalid_backups=invalid_backups,
            backups_without_checksums=backups_without_checksums,
            checksums_without_backups=checksums_without_backups,
        )
