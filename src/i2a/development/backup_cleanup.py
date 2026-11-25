from dataclasses import dataclass, field
from pathlib import Path

from i2a.development.backup_manager import BackupManager


@dataclass
class BackupCleanupProposal:
    """Describes backup files proposed for cleanup."""

    workspace: str
    files: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "workspace": self.workspace,
            "files": self.files.copy(),
            "reasons": self.reasons.copy(),
        }


class BackupCleanupApproval:
    """Manages approval decisions for backup cleanup."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    def __init__(self, proposal: BackupCleanupProposal) -> None:
        if not isinstance(proposal, BackupCleanupProposal):
            raise TypeError(
                "Expected a BackupCleanupProposal object."
            )

        self.proposal = proposal
        self.status = self.PENDING

    def approve(self) -> None:
        """Approve a pending cleanup proposal."""

        if self.status != self.PENDING:
            raise ValueError(
                "Only pending proposals can be approved."
            )

        self.status = self.APPROVED

    def reject(self) -> None:
        """Reject a pending cleanup proposal."""

        if self.status != self.PENDING:
            raise ValueError(
                "Only pending proposals can be rejected."
            )

        self.status = self.REJECTED

    def to_dict(self) -> dict:
        """Return the proposal and its approval status."""

        return {
            "status": self.status,
            "proposal": self.proposal.to_dict(),
        }


class BackupCleanupManager:
    """Prepare safe cleanup proposals for orphaned backup files."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.backup_manager = BackupManager(workspace_path)
        self.workspace = self.backup_manager.workspace

    def create_proposal(self) -> BackupCleanupProposal:
        """Create a proposal for orphaned backup files."""

        orphaned_files = self.backup_manager.find_orphaned_files()

        proposal = BackupCleanupProposal(
            workspace=str(self.workspace)
        )

        for item in orphaned_files:
            if item["type"] != "checksum_without_backup":
                continue

            proposal.files.append(item["path"])
            proposal.reasons.append(
                "Checksum has no matching backup file."
            )

        return proposal