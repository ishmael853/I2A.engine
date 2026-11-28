from i2a.development.retention_proposal import BackupRetentionProposal


class BackupRetentionApproval:
    """Manages approval decisions for backup retention."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    def __init__(self, proposal: BackupRetentionProposal) -> None:
        if not isinstance(proposal, BackupRetentionProposal):
            raise TypeError("Expected a BackupRetentionProposal object.")

        self.proposal = proposal
        self.status = self.PENDING

    def approve(self) -> None:
        """Approve a pending retention proposal."""

        if self.status != self.PENDING:
            raise ValueError("Only pending proposals can be approved.")

        self.status = self.APPROVED

    def reject(self) -> None:
        """Reject a pending retention proposal."""

        if self.status != self.PENDING:
            raise ValueError("Only pending proposals can be rejected.")

        self.status = self.REJECTED

    def to_dict(self) -> dict:
        """Return the proposal and its approval status."""

        return {
            "status": self.status,
            "proposal": self.proposal.to_dict(),
        }
