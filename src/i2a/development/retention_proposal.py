from dataclasses import dataclass, field


@dataclass
class BackupRetentionProposal:
    """Describes backups that exceed the retention period."""

    workspace: str
    max_age_days: int
    backups: list[str] = field(default_factory=list)
    ages_days: list[float] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return the retention proposal as a dictionary."""

        return {
            "workspace": self.workspace,
            "max_age_days": self.max_age_days,
            "backups": self.backups.copy(),
            "ages_days": self.ages_days.copy(),
            "reasons": self.reasons.copy(),
        }
