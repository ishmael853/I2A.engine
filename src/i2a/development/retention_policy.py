from dataclasses import dataclass


@dataclass
class BackupRetentionPolicy:
    """Define how long I2A backups should be retained."""

    max_age_days: int = 30

    def __post_init__(self) -> None:
        if isinstance(self.max_age_days, bool) or not isinstance(
            self.max_age_days, int
        ):
            raise TypeError(
                "Maximum backup age must be an interger."
            )

        if self.max_age_days < 1:
            raise ValueError(
                "Maximum backup age must be at least one day."
            )

    def to_dict(self) -> dict:
        """Return the retention policy as a dictonary."""

        return {
            "max_age_days": self.max_age_days,
        }