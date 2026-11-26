from dataclasses import dataclass, field


@dataclass
class BackupHealthReport:
    """Summarizes the health of I2A development backups."""

    workspace: str
    total_backups: int = 0
    valid_backups: int = 0
    invalid_backups: int = 0
    backups_without_checksums: list[str] = field(
        default_factory=list
    )
    checksums_without_backups: list[str] = field(
        default_factory=list
    )

    @property
    def healthy(self) -> bool:
        """Return whether all discovered backups are healthy."""

        return (
            self.invalid_backups == 0
            and not self.backups_without_checksums
            and not self.checksums_without_backups
        )

    def to_dict(self) -> dict:
        """Return the health report as a dictionary."""

        return {
            "workspace": self.workspace,
            "total_backups": self.total_backups,
            "valid_backups": self.valid_backups,
            "invalid_backups": self.invalid_backups,
            "backups_without_checksums": (
                self.backups_without_checksums.copy()
            ),
            "checksums_without_backups": (
                self.checksums_without_backups.copy()
            ),
            "healthy": self.healthy,
        }